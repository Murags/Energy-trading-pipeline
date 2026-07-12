"""Unit tests for run ID and timestamp helpers."""

from datetime import datetime

from energy_trading_pipeline.utils.time import RUN_ID_FORMAT, generate_run_id


def test_generate_run_id_formats_given_timestamp():
    run_id = generate_run_id(now=datetime(2026, 7, 12, 21, 5, 9))

    assert run_id == "run_20260712_210509"


def test_generate_run_id_matches_run_id_format_pattern():
    run_id = generate_run_id(now=datetime(2023, 1, 1, 0, 0, 0))

    assert datetime.strptime(run_id, RUN_ID_FORMAT).strftime(RUN_ID_FORMAT) == run_id


def test_generate_run_id_defaults_to_current_time():
    before = datetime.now()
    run_id = generate_run_id()
    after = datetime.now()

    parsed = datetime.strptime(run_id, RUN_ID_FORMAT)

    assert before.replace(microsecond=0) <= parsed <= after.replace(microsecond=0)
