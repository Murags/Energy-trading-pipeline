"""Offline contracts for optional, artifact-only dashboard containers."""

from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_compose_builds_with_locked_optional_dashboard_dependencies():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())

    assert set(compose["services"]) == {"dashboard"}
    build = compose["services"]["dashboard"]["build"]
    assert build["context"] == "."
    assert build["args"] == {"UV_EXTRA": "dashboard"}


def test_compose_launches_only_streamlit_on_a_local_port():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    service = compose["services"]["dashboard"]

    assert service["command"] == [
        "python", "-m", "streamlit", "run",
        "src/energy_trading_pipeline/dashboard/app.py",
        "--server.address=0.0.0.0", "--server.port=8501",
        "--server.headless=true", "--browser.gatherUsageStats=false",
    ]
    assert service["ports"] == ["127.0.0.1:${DASHBOARD_PORT:-8501}:8501"]
    assert "_stcore/health" in service["healthcheck"]["test"][-1]


def test_compose_mounts_only_exports_read_only_without_credentials():
    compose = yaml.safe_load((PROJECT_ROOT / "docker-compose.yml").read_text())
    service = compose["services"]["dashboard"]

    assert service["volumes"] == [{
        "type": "bind",
        "source": "./reports/dashboard_exports",
        "target": "/app/reports/dashboard_exports",
        "read_only": True,
        "bind": {"create_host_path": False},
    }]
    assert not compose.get("secrets")
    for key in ("env_file", "environment", "secrets", "depends_on"):
        assert key not in service


def test_readme_documents_optional_compose_and_manual_smoke_checks():
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split(
        "### Dashboard with Docker Compose (Optional)\n", 1
    )[1].split("\n## ", 1)[0]

    for command in (
        "mkdir -p reports/dashboard_exports",
        "docker compose config --quiet",
        "docker compose up --build -d --wait",
        "curl --fail http://127.0.0.1:8501/_stcore/health",
        "docker compose exec -T dashboard python -c",
        "docker compose logs dashboard",
        "docker compose down",
    ):
        assert command in section
    for name in ("forecasts", "metrics", "retraining_events", "model_versions"):
        assert f"{name}.parquet" in section
    assert "read-only" in section
    assert "No AWS or API credentials" in section
    assert "DASHBOARD_PORT=8502" in section