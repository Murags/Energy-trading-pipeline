"""Exercise test selection with the repository config and CI command."""

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_TESTS = """
import pytest

def test_local():
    pass

@pytest.mark.external_api
def test_api():
    pass

@pytest.mark.aws
def test_aws():
    pass

@pytest.mark.slow
def test_slow():
    pass

@pytest.mark.external_api
@pytest.mark.slow
def test_slow_api():
    pass
"""


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ("default", {"test_local"}),
        ("ci", {"test_local"}),
        ("external_api", {"test_api", "test_slow_api"}),
        ("aws", {"test_aws"}),
        ("slow", {"test_slow", "test_slow_api"}),
        ("", {"test_local", "test_api", "test_aws", "test_slow", "test_slow_api"}),
    ],
)
def test_marker_selection(tmp_path: Path, selection: str, expected: set[str]) -> None:
    shutil.copyfile(PROJECT_ROOT / "pyproject.toml", tmp_path / "pyproject.toml")
    sample_path = tmp_path / "test_selection_sample.py"
    sample_path.write_text(SAMPLE_TESTS, encoding="utf-8")
    options = []
    if selection == "ci":
        workflow_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        workflow = yaml.load(workflow_path.read_text(), Loader=yaml.BaseLoader)
        commands = [
            shlex.split(step["run"])
            for step in workflow["jobs"]["test"]["steps"]
            if "run" in step
        ]
        command = next(cmd for cmd in commands if cmd[:3] == ["uv", "run", "pytest"])
        # Clear local selection defaults to verify CI's explicit exclusion itself.
        options = ["-o", "addopts=", *command[3:]]
    elif selection != "default":
        options = ["-m", selection]

    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *options,
            "--strict-markers",
            "-vv",
            "--color=no",
            str(sample_path),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    passed = set(re.findall(r"::(test_\w+) PASSED", result.stdout))
    assert passed == expected, result.stdout
    if len(expected) < 5:
        assert f"{5 - len(expected)} deselected" in result.stdout
