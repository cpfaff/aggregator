# Changelog

All notable changes to the aggregator frontend are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
