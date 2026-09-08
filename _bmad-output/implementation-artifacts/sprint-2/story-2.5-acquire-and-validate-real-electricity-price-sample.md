---
story_id: "2.5"
title: "Acquire and Validate a Real Electricity Price Sample"
status: "review"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P0"
suggested_sprint: "Sprint 2"
source: "User-approved real-data acquisition follow-up, 2026-09-08"
---

# Story 2.5: Acquire and Validate a Real Electricity Price Sample

## Status

Review

## User Story

As a researcher, I want a real German/French electricity price sample with
verified provenance and licensing so that preprocessing can start with actual
market data and the data-access assumption is tested early.

## Scope

Acquire January 2024 hourly day-ahead prices from Bundesnetzagentur's SMARD
platform, which republishes ENTSO-E data under an explicit CC BY 4.0 licence.
This is a bounded acquisition exercise, not a production API adapter. Existing
ENTSO-E/Open-Meteo interfaces, fixture tests, and experiment defaults stay intact.

## Acceptance Criteria

1. Download real prices for both markets without paid services or credentials.
2. Confirm series identifiers, market names, units, and reuse rights using the
   provider's own catalogue, labels, and licensing page.
3. Preserve original JSON responses with retrieval timestamps, source URLs, and
   SHA-256 checksums under `data/raw/smard/prices/run_YYYYMMDD_HHMMSS/`.
4. Export canonical `timestamp,price_de` and `timestamp,price_fr` CSV files and
   a paired CSV/Parquet sample under `data/processed/run_YYYYMMDD_HHMMSS/`.
5. Validate the half-open UTC window 2024-01-01 through 2024-02-01: 744 unique
   hourly timestamps per market, finite numeric values, no missing hours, no
   duplicate timestamps, and matching timestamps across markets. Fail rather
   than silently filling gaps, averaging duplicates, or dropping invalid prices.
6. Document attribution, German bidding-zone meaning (DE-LU), transformations,
   negative-price handling, and the limitation that this sample does not prove
   complete 2020-2025 coverage or historical publication-time availability.
7. Demonstrate the exported files load through the existing local loader.

## Dependencies

Stories 2.1 and 2.2 are available. Story 2.4 remains an interface-only story.

## Technical Notes

- Official catalogue: `https://www.smard.de/app/chart_configuration/market_data_configuration.json`.
- English labels: `https://www.smard.de/app/assets/translations/lang-en.json`.
- Licensing: `https://www.smard.de/en/datennutzung`.
- Germany/Luxembourg data ID: `4169`; France data ID: `254`.
- Both series use the SMARD `DE` view in their URLs; the data ID identifies the
  market. Never infer the French market from the URL region parameter alone.
- Discover weekly chunks from each series' `index_hour.json`; include the chunk
  containing the start of the requested interval, not just chunks starting in it.
- Use published hourly series, convert epoch milliseconds to UTC, select the
  requested interval, sort, and pair on an exact timestamp match. No imputation,
  currency conversion, forecast features, spread calculation, or model fitting.
- January 2024 avoids the later market-time-unit change and DST transitions;
  neither is validated by this bounded sample.
- Keep live downloads out of pytest and CI. Preserve real data independently of
  the synthetic test fixtures. No new dependency or cloud resource is required.

## Tasks / Subtasks

- [x] Verify official source identity, units, and licence.
- [x] Acquire and preserve both original price series and source evidence.
- [x] Export and validate the canonical one-month sample.
- [x] Document the sample, attribution, checksums, and limitations.

## Dev Agent Record

### Debug Log

- The sandbox could not resolve SMARD; the public download succeeded after
  approved network access. No credentials were used.
- The older table-data endpoint returned HTTP 404. SMARD's current chart code
  and catalogue confirmed the working chart-data endpoint and both market IDs.
- Downloaded 14 source responses: the catalogue, English labels, two weekly
  indices, and five price chunks per market. Preserved the original response
  bytes under `data/raw/smard/prices/run_20260908_150908/`.
- The first CSV round-trip assertion exposed milliseconds versus microseconds
  in pandas datetime dtypes. Rechecked from the cached responses with matching
  timestamp precision; values and timestamps matched without price changes.
- Offline independent verification passed all 14 response checksums and four
  export checksums. All 1,488 prices in the paired CSV exactly match the saved
  JSON values at their UTC timestamps.
- Existing local-loader CSV and Parquet round trips passed. Complete fixture
  regression: `uv run --locked --extra test pytest -q`, 79 passed in 2.27 seconds.
- Temporary one-off tools used `/tmp/acquire_energy_price_sample.py` and
  `/tmp/verify_energy_price_sample.py`; these are not installed pipeline commands.

### Completion Notes

- Acquired the full half-open January 2024 UTC interval for Germany/Luxembourg
  and France: 744 paired rows, zero missing hours/values, and zero duplicates.
- Confirmed day-ahead prices and EUR/MWh units from the provider's own catalogue.
  Retained 16 negative German-price hours and eight negative French-price hours.
- Exported separate market CSVs, paired CSV/Parquet, and detailed metadata.
  Raw snapshot size is 574,005 bytes; exports and metadata total 89,389 bytes.
- Documented CC BY 4.0 attribution to Bundesnetzagentur | SMARD.de, exact date
  boundaries, source URLs, transformations, DE-LU meaning, and research limits.
- Added Story 2.5 to Epic 2 as the user-approved acquisition follow-up before
  Sprint 3. Kept generated snapshots local via Git ignore rules; synthetic
  fixtures and CI remain independent of the downloaded data.
- No dependency, reusable API adapter, model, or cloud infrastructure was added.
  Full historical coverage and publication-time vintages remain unverified.

## File List

- `.gitignore` (modified)
- `_bmad-output/epics.md` (modified)
- `_bmad-output/implementation-artifacts/sprint-2/story-2.5-acquire-and-validate-real-electricity-price-sample.md` (added)
- `docs/data_sources.md` (added)
- `data/raw/smard/prices/run_20260908_150908/` (14 source responses and manifest; generated, Git-ignored)
- `data/processed/run_20260908_150908/price_de.csv` (generated, Git-ignored)
- `data/processed/run_20260908_150908/price_fr.csv` (generated, Git-ignored)
- `data/processed/run_20260908_150908/prices_de_fr.csv` (generated, Git-ignored)
- `data/processed/run_20260908_150908/prices_de_fr.parquet` (generated, Git-ignored)
- `data/processed/run_20260908_150908/metadata.json` (generated, Git-ignored)

## Change Log

- 2026-09-08: Added this bounded real-data acquisition story at the user's request.
- 2026-09-08: Completed the SMARD acquisition and validation; marked for review.
