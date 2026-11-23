# Changelog

All notable changes to the aggregator frontend are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [2.5.0] - 2026-11-23

### Added

- **Validation reports units that share a UnitID** — the search index keys
  every unit document on the dataset URN plus the UnitID, so units that reuse a
  UnitID overwrite each other and only one per UnitID is ever searchable, while
  validation reported the archive as valid (dataset #165: 4602 units, 2478
  distinct UnitIDs, 2478 indexed). A new archive-wide check streams every XML
  member, keys units exactly like the harvester (UnitID with ASCII whitespace
  runs collapsed to one space, not stripped) and stores the result under
  `validation_results.archive_checks.duplicate_unit_ids` plus
  `summary.units_not_indexable`. Unreadable members are skipped and counted;
  the check never fails a validation job. The dataset card shows
  "N units share a UnitID" next to the validation result, and the validation
  details list the affected UnitIDs. Archives validated earlier show nothing
  until they are re-validated. (DASS-3961)

### Fixed

- **Backend test job resolves a working SQLAlchemy again** — the job installs
  from `pyproject.toml` without a lock and picked up SQLAlchemy 2.1, which no
  longer installs `greenlet`, so the async engine failed to import. The
  dependency now declares the `asyncio` extra and stays below 2.1, matching the
  2.0.x the images are built from. (DASS-3961)

## [2.4.1] - 2026-09-14

### Fixed

- **The maintenance page no longer breaks open tabs during a deploy** — its nginx
  answered every `/api/*` request with the SPA catch-all, i.e. HTTP 200 and an
  HTML body, and its Traefik router is `PathPrefix(/)` at priority 100 with no
  `/api` exclusion. Because the client only checked `response.ok`, that 200 was
  parsed as JSON and threw `Unexpected token '<', "<!DOCTYPE "... is not valid
  JSON` in every authenticated tab. `/api` now returns a real 503 with an
  RFC 7807 body, which the client already classifies as transient. Latent since
  DASS-3210; not a 2.4.0 regression. (DASS-3814)

### Added

- **`readJson()` in `utils/apiUtils`** — a content-type guard for success-path
  responses, the companion to `parseErrorResponse` for failures. `response.ok`
  is a status check only, so any proxy returning HTML with a 200 could reach
  `JSON.parse`; the raw `SyntaxError` was rendered verbatim into the error
  banner on the Providers, Provider detail and User Management screens. Adopted
  at all 22 success-path parse sites. (DASS-3814)

## [2.4.0] - 2026-09-14

### Fixed

- **Dark theme no longer flashes light on load** — the theme is now resolved and
  stamped on `<html>` by a blocking inline script before first paint, and the
  palette lives in a static `theme.css` instead of being written onto
  `documentElement.style` from a React effect. The effect ran after the first
  paint, so every `var()` was invalid-at-computed-value-time for at least one
  frame and the armed 0.3s transition animated the correction into a visible
  wash. Also fixes the permanently light canvas, overscroll area and scrollbar
  gutter, and the mobile nav panel sliding away on every load below 576px.
  (DASS-3813)

### Added

- **The theme follows the operating system** for visitors who have never used
  the toggle. An explicit choice always wins and is never overridden.
  (DASS-3813)

### Changed

- `styles/globalStyles.js` is now `styles/global.css`, imported from
  `index.js` rather than injected into `<head>` from an effect — which also
  removes the duplicate `<style>` element StrictMode used to produce.
  (DASS-3813)

## [2.2.0] - 2026-06-22

### Added

- **Per-dataset harvest-success indicator on the dataset card** — shows whether a
  dataset's records reached the public Elasticsearch search index (In index ·
  M of N units / Partially / Not yet / Staged / Status unavailable), queried live
  by the aggregator. Closes the loop opened by the harvest-ready flag. (DASS-3612)

## [2.1.0] - 2026-06-22

### Added

- **"Harvest ready" toggle on the dataset edit form** — a data provider can mark
  a dataset as harvest-ready or keep it staged, controlling whether it enters the
  harvester feed. Self-service (no admin required) and defaults to staged for new
  datasets. (DASS-3610)
