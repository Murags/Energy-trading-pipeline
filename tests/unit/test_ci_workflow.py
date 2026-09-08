"""Contract tests for the fixture-based GitHub Actions workflow."""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_runs_fixture_safe_pytest_on_pushes_and_pull_requests():
    workflow_text = WORKFLOW_PATH.read_text()
    workflow = yaml.load(workflow_text, Loader=yaml.BaseLoader)

    assert set(workflow["on"]) == {"push", "pull_request"}

    test_job = workflow["jobs"]["test"]
    assert test_job["runs-on"] == "ubuntu-latest"

    steps = test_job["steps"]
    used_actions = {step["uses"] for step in steps if "uses" in step}
    run_commands = [step["run"] for step in steps if "run" in step]

    assert "actions/checkout@v4" in used_actions
    assert "astral-sh/setup-uv@v6" in used_actions
    assert "uv sync --extra test --locked" in run_commands
    assert (
        'uv run pytest -q -m "not external_api and not aws and not slow"'
        in run_commands
    )

    forbidden_terms = ("ENTSOE_API_KEY", "AWS_ACCESS_KEY_ID", "2020-2025", "backtest")
    assert not any(term in workflow_text for term in forbidden_terms)
