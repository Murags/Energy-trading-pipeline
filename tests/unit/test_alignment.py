"""Hourly alignment contracts on small, normalized datasets."""

from datetime import date
import logging

import pandas as pd
import pytest

from energy_trading_pipeline.preprocessing.alignment import align_hourly_data


@pytest.fixture
def prices():
    timestamps = pd.date_range("2023-01-01", periods=72, freq="h", tz="UTC")
    return (
        pd.DataFrame({"timestamp": timestamps, "price_de": range(72)}),
        pd.DataFrame({"timestamp": timestamps, "price_fr": range(100, 172)}),
    )


def test_alignment_joins_by_instant_and_clips_inclusive_dates(prices):
    de, fr = prices
    de = de.iloc[::-1].copy()
    fr["timestamp"] = fr["timestamp"].dt.tz_convert("Europe/Paris")
    weather = pd.DataFrame(
        {"timestamp": de["timestamp"], "temperature_2m_c": de["price_de"] + 10}
    )
    grid = pd.DataFrame(
        {"timestamp": fr["timestamp"], "load_de": fr["price_fr"] * 2}
    )
    originals = [df.copy(deep=True) for df in (de, fr, weather, grid)]

    result, report = align_hourly_data(
        de,
        fr,
        start_date=date(2023, 1, 2),
        end_date="2023-01-03",
        weather=weather,
        grid=grid,
    )

    expected = pd.date_range("2023-01-02", periods=48, freq="h", tz="UTC")
    pd.testing.assert_index_equal(
        pd.DatetimeIndex(result["timestamp"]), expected, check_names=False
    )
    assert result["price_de"].tolist() == list(range(24, 72))
    assert result["price_fr"].tolist() == list(range(124, 172))
    assert result["temperature_2m_c"].tolist() == list(range(34, 82))
    assert result["load_de"].tolist() == list(range(248, 344, 2))
    assert report["output_rows"] == 48
    assert report["retained_columns"] == result.columns.tolist()
    assert report["date_range"] == {
        "start": expected[0].isoformat(),
        "end": expected[-1].isoformat(),
    }
    assert "spread" not in result
    for actual, original in zip((de, fr, weather, grid), originals):
        pd.testing.assert_frame_equal(actual, original)


@pytest.mark.parametrize("market,column", [(0, "price_de"), (1, "price_fr")])
@pytest.mark.parametrize("hour", [0, 12, 23])
def test_required_price_gaps_fail_instead_of_shrinking_or_filling(
    prices, market, column, hour
):
    frames = list(prices)
    frames[market] = frames[market].drop(index=hour)
    with pytest.raises(ValueError, match=f"Missing required hourly values.*{column}"):
        align_hourly_data(*frames, start_date="2023-01-01", end_date="2023-01-01")


@pytest.mark.parametrize("column", ["price_de", "price_fr"])
@pytest.mark.parametrize("absent", [True, False])
def test_required_price_columns_and_values_fail(prices, column, absent):
    frames = list(prices)
    market = 0 if column == "price_de" else 1
    if absent:
        frames[market] = frames[market].drop(columns=column)
    else:
        frames[market].loc[5, column] = float("nan")
    with pytest.raises(ValueError, match=f"Missing required.*{column}"):
        align_hourly_data(*frames, start_date="2023-01-01", end_date="2023-01-01")


def test_missing_optional_sources_warn_and_preserve_all_hours(prices, caplog):
    with caplog.at_level(logging.WARNING):
        result, report = align_hourly_data(
            *prices, start_date="2023-01-01", end_date="2023-01-01"
        )
    assert len(result) == 24
    assert result.columns.tolist() == ["timestamp", "price_de", "price_fr"]
    assert report["missing_optional_sources"] == ["weather", "grid"]
    assert "Optional source unavailable: weather" in caplog.text


def test_incomplete_optional_columns_are_excluded_without_filling(prices, caplog):
    de, fr = prices
    weather = de.rename(columns={"price_de": "temperature_2m_c"}).copy()
    weather["wind_speed_10m_m_s"] = 5.0
    weather.loc[5, "temperature_2m_c"] = float("nan")
    grid = fr.iloc[1:].rename(columns={"price_fr": "load_fr"})
    with caplog.at_level(logging.WARNING):
        result, report = align_hourly_data(
            de,
            fr,
            start_date="2023-01-01",
            end_date="2023-01-01",
            weather=weather,
            grid=grid,
        )
    assert len(result) == 24
    assert result.columns.tolist() == [
        "timestamp",
        "price_de",
        "price_fr",
        "wind_speed_10m_m_s",
    ]
    assert report["excluded_optional_columns"] == ["temperature_2m_c", "load_fr"]
    assert report["missing_counts"]["load_fr"] == 1
    assert "Optional columns excluded" in caplog.text


@pytest.mark.parametrize("source", ["prices_de", "weather"])
@pytest.mark.parametrize(
    "defect,message",
    [
        ("duplicate", "Duplicate timestamps"),
        ("off_hour", "Non-hourly timestamps"),
        ("naive", "timezone-aware"),
        ("null_timestamp", "timestamp contains missing"),
        ("duplicate_columns", "Duplicate column names"),
        ("no_timestamp", "Missing required column: timestamp"),
    ],
)
def test_invalid_source_contract_fails(prices, source, defect, message):
    de, fr = prices
    frame = (
        de.copy()
        if source == "prices_de"
        else de.rename(columns={"price_de": "wind"})
    )
    if defect == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]])
    elif defect == "off_hour":
        frame.loc[0, "timestamp"] += pd.Timedelta(minutes=30)
    elif defect == "naive":
        frame["timestamp"] = frame["timestamp"].dt.tz_localize(None)
    elif defect == "null_timestamp":
        frame.loc[0, "timestamp"] = pd.NaT
    elif defect == "duplicate_columns":
        frame = pd.concat([frame, frame.iloc[:, [1]]], axis=1)
    else:
        frame = frame.drop(columns="timestamp")
    kwargs = {"weather": frame} if source == "weather" else {}
    with pytest.raises(ValueError, match=message):
        align_hourly_data(
            frame if source == "prices_de" else de,
            fr,
            start_date="2023-01-01",
            end_date="2023-01-01",
            **kwargs,
        )


def test_cross_source_column_collisions_fail(prices):
    with pytest.raises(ValueError, match="Overlapping columns.*price_de"):
        align_hourly_data(
            *prices, start_date="2023-01-01", end_date="2023-01-01", weather=prices[0]
        )


@pytest.mark.parametrize(
    "start,end",
    [
        ("2023-01-02", "2023-01-01"),
        ("invalid", "2023-01-01"),
        (None, "2023-01-01"),
        (123, "2023-01-01"),
        ("2023-01-01T12:00:00", "2023-01-02"),
    ],
)
def test_invalid_calendar_date_bounds_fail(prices, start, end):
    with pytest.raises(ValueError, match="date"):
        align_hourly_data(*prices, start_date=start, end_date=end)


def test_dst_repeated_local_hours_remain_distinct():
    timestamps = pd.date_range("2023-10-29", periods=24, freq="h", tz="UTC")
    de = pd.DataFrame(
        {"timestamp": timestamps.tz_convert("Europe/Berlin"), "price_de": range(24)}
    )
    fr = pd.DataFrame({"timestamp": timestamps, "price_fr": range(24)})
    result, _ = align_hourly_data(
        de, fr, start_date="2023-10-29", end_date="2023-10-29"
    )
    assert len(result) == 24
    assert result["timestamp"].is_unique
    assert result["price_de"].tolist() == list(range(24))


@pytest.mark.parametrize("empty", [True, False])
def test_optional_source_without_requested_hours_does_not_shrink_output(prices, empty):
    weather = prices[0].iloc[:0] if empty else prices[0].iloc[24:]
    weather = weather.rename(columns={"price_de": "temperature_2m_c"})
    result, report = align_hourly_data(
        *prices, start_date="2023-01-01", end_date="2023-01-01", weather=weather
    )
    assert len(result) == 24
    assert "temperature_2m_c" not in result
    if empty:
        assert "weather" in report["missing_optional_sources"]
    else:
        assert report["missing_counts"]["temperature_2m_c"] == 24


def test_optional_missingness_outside_alignment_range_does_not_exclude_column(prices):
    weather = prices[0].rename(columns={"price_de": "temperature_2m_c"})
    weather.loc[24, "temperature_2m_c"] = float("nan")
    result, report = align_hourly_data(
        *prices, start_date="2023-01-01", end_date="2023-01-01", weather=weather
    )
    assert result["temperature_2m_c"].tolist() == list(range(24))
    assert report["excluded_optional_columns"] == []


def test_excluded_column_cannot_be_replaced_by_another_source(prices):
    weather = prices[0].iloc[1:].rename(columns={"price_de": "temperature_2m_c"})
    grid = prices[1].rename(columns={"price_fr": "temperature_2m_c"})
    with pytest.raises(ValueError, match="Overlapping columns.*temperature_2m_c"):
        align_hourly_data(
            *prices,
            start_date="2023-01-01",
            end_date="2023-01-01",
            weather=weather,
            grid=grid,
        )


@pytest.mark.parametrize("missing", [None, pd.DataFrame()])
def test_missing_required_source_fails(prices, missing):
    with pytest.raises(ValueError):
        align_hourly_data(
            missing, prices[1], start_date="2023-01-01", end_date="2023-01-01"
        )
