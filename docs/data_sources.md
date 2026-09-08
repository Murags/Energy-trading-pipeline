# Real Electricity Price Sample

## Downloaded Data

On 2026-09-08, a real one-month sample was acquired directly from
Bundesnetzagentur's SMARD website without credentials or paid services.

| Property | Value |
| --- | --- |
| Acquisition ID | `run_20260908_150908` |
| Product | Published hourly day-ahead electricity prices |
| Interval | `2024-01-01T00:00:00Z` inclusive to `2024-02-01T00:00:00Z` exclusive |
| Records | 744 per market; 744 paired rows |
| Units | EUR/MWh |
| `price_de` | Germany/Luxembourg bidding zone (DE-LU), SMARD data ID `4169` |
| `price_fr` | France bidding zone, SMARD data ID `254` |
| Timestamp | Start of the delivery interval, in UTC |
| Provider | Bundesnetzagentur, SMARD.de |
| Upstream source | ENTSO-E, as identified by SMARD |

This is a UTC calendar month. The corresponding Central European Time interval
is January 1 at 01:00 through February 1 at 01:00, excluding the latter endpoint.
It is not exactly the January calendar month in local market time.

## Local Files

The data is stored locally and excluded from Git. It is separate from the
synthetic files under `tests/fixtures/`; CI does not download this sample.

- [German prices CSV](../data/processed/run_20260908_150908/price_de.csv)
- [French prices CSV](../data/processed/run_20260908_150908/price_fr.csv)
- [Paired prices CSV](../data/processed/run_20260908_150908/prices_de_fr.csv)
- [Paired prices Parquet](../data/processed/run_20260908_150908/prices_de_fr.parquet)
- [Metadata and validation results](../data/processed/run_20260908_150908/metadata.json)
- [Original responses and manifest](../data/raw/smard/prices/run_20260908_150908/)

The individual CSV schemas are `timestamp,price_de` and `timestamp,price_fr`.
The paired CSV/Parquet schema is `timestamp,price_de,price_fr`. The existing
`energy_trading_pipeline.data_ingestion.local_loader.load_local_data` reads all
four exports. CSV timestamps are ISO 8601 UTC strings; Parquet preserves a
timezone-aware timestamp column.

## Source and Licence

Attribution: **Bundesnetzagentur | SMARD.de**.

SMARD's [data-use terms](https://www.smard.de/en/datennutzung) license its
downloadable market data under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
The terms allow sharing and adapting the data with attribution. Preserve the
attribution and licence link and identify modifications when publishing the
sample or derived data. SMARD does not guarantee completeness or accuracy.

The source identities and units were checked against SMARD's own
[series catalogue](https://www.smard.de/app/chart_configuration/market_data_configuration.json)
and [English labels](https://www.smard.de/app/assets/translations/lang-en.json),
both retained in the raw snapshot. Both selected modules belong to the
day-ahead-price category and use EUR/MWh.

## Acquisition and Checks

The one-off acquisition downloaded each series' weekly chunk index:

```text
https://www.smard.de/app/chart_data/4169/DE/index_hour.json
https://www.smard.de/app/chart_data/254/DE/index_hour.json
```

For each series, five weekly JSON chunks covering the requested UTC interval
were downloaded. The manifest records every URL, retrieval timestamp, SHA-256
checksum, byte count, and local response path. The `DE` URL component denotes
the SMARD view; the series ID, verified through the catalogue, identifies the
actual price market. The French series must not be relabelled German because
its URL contains `DE`.

To repeat the acquisition, download the source URLs listed in the manifest into
a new snapshot directory. Read each response's `series` pairs as epoch
milliseconds and prices, convert timestamps to UTC, filter the documented
half-open interval, and sort chronologically. Require a complete, unique hourly
index for both series before pairing on timestamps. Preserve a new manifest:
the provider may revise past observations, so a later download may differ.
The existing ENTSO-E/Open-Meteo classes remain placeholders; this exercise did
not add a reusable downloader or scheduled acquisition command.

Only timestamp conversion, interval selection, column renaming, chronological
sorting, exact timestamp pairing, and CSV/Parquet serialization were applied.
No imputation, deduplication, resampling, currency conversion, or price clipping
was performed. Negative prices are retained.

| Check | Germany/Luxembourg | France |
| --- | ---: | ---: |
| Hourly records | 744 | 744 |
| Missing hours | 0 | 0 |
| Duplicate timestamps | 0 | 0 |
| Missing/non-finite prices | 0 | 0 |
| Negative-price hours | 16 | 8 |
| Minimum EUR/MWh | -4.84 | -0.05 |
| Maximum EUR/MWh | 150.09 | 144.11 |

All market timestamps match exactly. CSV and Parquet exports were loaded through
the existing loader and checked against the downloaded values. These are data
quality checks, not forecasting performance results.

## Limitations

- `price_de` represents the joint Germany/Luxembourg bidding zone, not a separate
  Germany-only auction price. Retain this meaning in the academic methodology.
- This is a current historical snapshot, not a publication-time vintage. Source
  response creation timestamps are not evidence of when a price became known
  to a historical forecaster.
- One successful month does not establish complete 2020-2025 availability.
- January 2024 contains no daylight-saving transition and precedes the later
  move to quarter-hour day-ahead market intervals. Wider acquisition must check
  resolution and timezone handling explicitly.
- This sample includes prices only. No spread features, training, backtest,
  weather, load, or generation data were produced.
- The sample is ready for Sprint 3 preprocessing. Its January 2024 dates must be
  used explicitly when configuring a subsequent run; fixture defaults were not
  changed.
