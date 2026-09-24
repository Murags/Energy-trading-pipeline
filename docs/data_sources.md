# Real Research Datasets

## Full-Year 2024 Weather

At the user's request, ERA5 hourly weather for eight representative German and
French electricity-generation regions was downloaded from Open-Meteo on
2026-09-13 as `run_20260913_132539`.

- [Location-level CSV](../data/processed/run_20260913_132539/weather_2024_locations.csv)
- [Location-level Parquet](../data/processed/run_20260913_132539/weather_2024_locations.parquet)
- [Country-aggregate CSV](../data/processed/run_20260913_132539/weather_2024_country_aggregates.csv)
- [Country-aggregate Parquet](../data/processed/run_20260913_132539/weather_2024_country_aggregates.parquet)
- [Source metadata, weights, and limitations](../data/processed/run_20260913_132539/metadata.json)
- [Verification results](../data/processed/run_20260913_132539/verification.json)
- [Raw Open-Meteo response and manifest](../data/raw/open_meteo/weather/run_20260913_132539/)

The German locations are Oldenburg, Husum, Potsdam, and Nuremberg. The French
locations are Amiens, Reims, Bordeaux, and Toulouse. They represent major wind
and solar regions rather than national capitals. Each location contains
`temperature_2m`, `wind_speed_10m`, `wind_speed_100m`, and
`shortwave_radiation` from the ERA5 reanalysis model. Wind is stored in m/s,
temperature in degrees Celsius, and radiation in W/m2.

The processed files have 8,784 unique UTC timestamps, no missing values, and
exactly match the full-year electricity-price timeline. Country wind and solar
features are weighted using the documented 2024 regional generation/capacity
figures; country temperature is the mean of the four selected points. The raw
request includes one extra UTC day on each boundary and the processed exports
retain only the timestamps present in the electricity-price artifact.

Attribution: **Weather data by Open-Meteo.com**, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Open-Meteo's
[terms](https://open-meteo.com/en/terms) apply.

ERA5 is historical reanalysis, not an archived forecast available to a
day-ahead forecaster. Contemporaneous target-hour weather must not be used
directly in leakage-safe evaluation. Lag these variables or replace them with
properly vintaged day-ahead forecasts before backtesting.

## Full-Year 2024 Electricity Prices

At the user's request, the complete 2024 local-market calendar year was
downloaded on 2026-09-11 as `run_20260911_053845`.

- [Full-year paired CSV](../data/processed/run_20260911_053845/prices_de_fr.csv)
- [Full-year paired Parquet](../data/processed/run_20260911_053845/prices_de_fr.parquet)
- [German prices CSV](../data/processed/run_20260911_053845/price_de.csv)
- [French prices CSV](../data/processed/run_20260911_053845/price_fr.csv)
- [Source metadata and monthly coverage](../data/processed/run_20260911_053845/metadata.json)
- [Independent verification](../data/processed/run_20260911_053845/verification.json)
- [Raw responses and manifest](../data/raw/smard/prices/run_20260911_053845/)

Coverage is January 1, 2024 at 00:00 through January 1, 2025 at 00:00,
end exclusive, in German/French local market time. Stored timestamps are UTC:
`2023-12-31T23:00:00Z` inclusive through `2024-12-31T23:00:00Z` exclusive.
The first timestamp therefore displays a 2023 UTC date while representing the
first delivery hour of 2024 locally. This local-year convention differs from the
original January sample's UTC-month boundaries below.

| Validation / statistic | Germany/Luxembourg | France |
| --- | ---: | ---: |
| Hourly records | 8,784 | 8,784 |
| Missing hours | 0 | 0 |
| Duplicate UTC timestamps | 0 | 0 |
| Missing/non-finite prices | 0 | 0 |
| Negative-price hours | 457 | 352 |
| Minimum EUR/MWh | -135.45 | -87.29 |
| Maximum EUR/MWh | 936.28 | 284.21 |
| Mean EUR/MWh | 78.5120 | 58.0181 |

The paired dataset has 8,784 rows and columns `timestamp,price_de,price_fr`.
It covers all 366 market days: March 31 has 23 hours, October 27 has 25 hours,
and all other days have 24. The two repeated local clock hours in October remain
distinct in UTC. Both markets have exactly the same UTC timestamps.

All 17,568 paired prices were independently checked against the original JSON
values. Checksums passed for 110 source responses (53 weekly price chunks per
market, two indices, the catalogue, and English labels) and four data exports.
The existing local loader passed CSV/Parquet round-trip comparisons. No gaps
were filled and no negative prices or extreme values were removed.

The provider, licence, market identities, and transformations are the same as
documented below. This download proves complete 2024 coverage, not completeness
of other years or publication-time vintages. It precedes the later quarter-hour
market change. The January snapshot remains unchanged, and both snapshots are
stored locally outside Git and CI. No application code or dependency changed.

## January 2024 Sample

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

## January Sample Files

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

## January Acquisition and Checks

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

## January Sample Limitations

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
