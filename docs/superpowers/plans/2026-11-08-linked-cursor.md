# Linked Plot Cursor Implementation Plan

> **For agentic workers:** Execute inline with executing-plans and TDD; one fresh read-only review after implementation.

**Goal:** User-approved A: link cursor positions across frequency spectrum, time trace and waterfall without changing mean curves or rereading MS data.
**Architecture:** A small Qt cursor controller owns four noninteractive overlay lines and two mean-curve markers. It maps actual MHz/elapsed seconds to nearest preview indices; the window formats bilingual sample/mean readouts and clears stale cursor state.
**Tech Stack:** Existing Python/PyQt6/PyQtGraph/pytest-qt; no new dependencies.
**Spec:** User's A selection in this conversation: waterfall sets both dimensions, spectrum sets frequency only, time trace sets time only. Current mean curves remain unchanged.

## Global Constraints
- Read-only MS; no new reads, selection tokens or curve data changes on hover.
- Physical coordinates map to preview samples; descending frequencies, irregular times and decimation retain actual MS row IDs.
- Partial cursor dimensions stay unknown until selected, rather than inventing a time/frequency.
- Bilingual labels clearly distinguish a single sample from existing means.
- Work in current clean checkout on codex/linked-cursor to retain its existing Conda/data paths. User authorized this feature and previously authorized repository management and installation; no extra plan approval stop.

## Review Focus
- Single channel/time, descending frequencies and gaps: nearest sample, no divide-by-zero.
- Flagged/NaN points: lines remain, no artificial mean marker or finite hidden value.
- Selection/open/pending changes: clear and disable stale overlays immediately.
- Mouse leaving data regions/widget: clear lines/readout; labels/colourbar do not count as data regions.
- Hover/language switching/zoom: curves, view bounds, colour levels and read request count remain unchanged.

### Task 1: Cursor mapping and overlays
**Files:** Create src/msviewer/cursor.py, tests/test_cursor.py.
**Interfaces:** LinkedCursor(graphics, spectrum, time, waterfall, image, changed); set_data(PlotData|None); move(QPointF); clear(). position is None or (row|None, channel|None). Four lines and two mean markers ignore autorange bounds.
- [x] Write failing real Qt tests for waterfall two-axis linking; frequency/time reverse linking including partial coordinates; nearest descending frequencies/irregular time and pixel centres; finite markers versus flagged means; outside/leave clearing; curve/view/no-read invariants.
- [x] Run tests and retain RED.
- [x] Implement controller and window integration; render/selection/open reset it.
- [x] Run tests to GREEN.

### Task 2: Bilingual readout and lifecycle regressions
**Files:** Modify src/msviewer/window.py, src/msviewer/i18n.py, README.md; tests/test_cursor.py.
**Interfaces:** Window _cursor_position mirrors controller; _refresh_cursor displays known dimensions, sample (if both known), flags and clearly labelled means; uses existing plot data only.
- [x] Add failing tests for Chinese/English readouts, true MS row IDs/channel physical frequency, sample flags, selection invalidation, data replacement and single-bin operation.
- [x] Run RED, implement, run GREEN and full suite/lint.
- [x] Record TDD evidence and one fresh bounded read-only review; address important findings with RED/GREEN.

### Task 3: Deliver installed update
**Files:** Version/build metadata, packaging/macos/build.sh and docs/macos-install.md if releasing a new DMG.
- [x] Build a new app/DMG after tests pass; preserve previously installed app before replacement.
- [x] Verify signature and native linked cursor UI. Update installed application; push source/update release under previous authorization, without replacing historical v0.1.0 artifacts.
- [x] Record evidence and give user direct usage instructions and accurate installer limitations.
