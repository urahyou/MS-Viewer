# Antenna Layout Implementation Plan

> Execute inline with TDD, verification-before-completion and one bounded final code review. User explicitly authorized the feature; prior repository/install authorization continues.

**Goal:** Add a bilingual antenna layout tab linked to the baseline selector, highlighting the selected endpoints and connecting segment.
**Architecture:** Read optional ANTENNA.POSITION metadata in the existing read-only inspection worker. Convert ITRF Cartesian metres into local WGS84 east/north/up at the first valid antenna. A focused AntennaMap widget owns scatter points, labels, selection overlays and explanatory text; MainWindow forwards metadata/baseline/language events.
**Tech Stack:** Existing casacore, NumPy, Astropy, PyQt6/PyQtGraph, pytest-qt.
**Spec:** User request: antenna position map, baseline selection highlights the corresponding two antennas and line. Stable original antenna IDs; no extra MS reads on map redraw; preserve existing visibility selection behavior.

## Constraints / Review focus
- Same scale on east/north axes; explain local projection and reference antenna. Report full 3D chord length, not projected length or uv distance.
- Handle zero/NaN/missing/unsupported-frame positions without breaking visibility viewing; omit unavailable coordinates rather than fabricate them.
- Baseline direction/reversal, auto-correlation, field/scan/DDID refills and data replacement must update/clear correctly.
- Opening/failed open and language switching must preserve dataset identity and existing generation checks; no extra reads for map/translation.
- Default metadata fields retain compatibility; original table data remains unchanged.
- Graph MCP unavailable in this session; source fallback inspected model.py, reader.py, window.py, tests and sample POSITION metadata. Work on codex/antenna-layout in the existing dependency-ready checkout.

## Tasks
- [x] TDD metadata/projection: real casacore position/unit/reference tests; independent equator/non-equator ENU direction/distance tests. RED then GREEN.
- [x] TDD map integration: selected endpoints/line/names, reversal, auto-correlation, equal scale, filtering/language/open-failure/data-replacement and invalid-position behavior. RED then GREEN.
- [x] Full tests/lint and bounded independent review; fix important findings with regression evidence.
- [ ] Build/install v0.1.2 preserving old app; native UI QA, signature and installer validation.
- [ ] Push source and publish versioned DMG/checksum after CI and remote digest verification; retain historical releases.

## Scientific references
- ESA ECEF→ENU basis: https://gssc.esa.int/navipedia/index.php/Transformations_between_ECEF_and_ENU_coordinates
- Astropy WGS84 reference conversion: https://docs.astropy.org/en/stable/api/astropy.coordinates.EarthLocation.html
