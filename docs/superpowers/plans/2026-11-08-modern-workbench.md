# Modern MS Workbench Implementation Plan

> User approved checklist first delivery M01/M02/M03/M04 common axes/M07. Execute TDD with bounded independent worker domains, parent integration and whole-change review. Existing repository/install authorization remains in effect. Work on codex/modern-workbench in the existing checkout; preserve user's untracked research/checklist documents.

**Goal:** Deliver v0.2.0: dockable bilingual workbench, observation overview, grouped structured selections, customizable per-sample/UV plots and exact preview-point Locate.
**Architecture:** Preserve existing single-baseline preview and compatibility API. Extend immutable contracts with provenance; add bounded grouped query service. New diagnostic component renders individual preview samples with exact identities, separate from existing mean curves. A dockable shell connects overview, grouped controls, focused group, Locate inspector, task log and per-dataset selection restoration.
**Tech stack:** Existing Python/PyQt6/casacore/PyQtGraph/Astropy; no CASA runtime or new scientific dependencies.
**Spec:** docs/casa-modernization-checklist.md M01/M02/M03/M04/M07; source references docs/research/casa-source-reference.md.

## Global constraints
- MS remains read-only. No flag writes, calibration, imaging, CASA expression full-compatibility, averaging implementation or table browser in this first batch.
- Existing single-baseline preview kept, clearly distinguished from grouped per-sample diagnostic view. Different DDID/field/scan/baseline groups remain separate.
- Stable original IDs and physical units survive translations and decimation; signed bundle resources stay immutable.
- Actual background reads remain serialized with generation checks; stale plots may not be used for current Locate.
- No graph MCP available; task-directed source fallback inspected model/reader/processing/window/workers, tests and CASA fixed-source reference note. No graph coverage claims.

## Shared interface contract
- Append defaults to VisibilityBlock: channel_ids, uvw, field_ids, scan_numbers, antenna1, antenna2 (np.ndarray|None), ddid (int|None), correlation_labels (tuple[str,...]). Existing constructors remain valid.
- Append Metadata.scans: tuple[ScanSummary,...], field_intents: tuple[tuple[str,...],...], history: tuple[str,...]. ScanSummary(scan, field, start, end, rows, ddids:tuple[int,...], intents:tuple[str,...]). Optional absent INTENT/history is unknown.
- New query.SelectionSpec(ddids=(), fields=(), scans=(), baselines=(), correlations=(), column='DATA', time_start=None,time_end=None, channel_start=0,channel_end=None,max_rows=1024,max_channels=2048,uv_min=None,uv_max=None). Tuples empty mean all; ranges use absolute MS seconds and original channels with exclusive end; uv in metres. to_dict() returns JSON-ready values.
- query.read_query(path, spec, metadata=None) -> tuple[VisibilityBlock,...], grouped by ddid/field/scan/oriented baseline; true read/subtraction and correlation selection retains aligned identities; enforce global preview row/memory budgets and explicit maximum group error rather than silent omission. COLUMN options include available plain columns plus CORRECTED_DATA-MODEL_DATA / DATA-MODEL_DATA only after unit/shape validation.
- New diagnostic.DiagnosticView(QWidget), set_blocks(blocks), clear(), set_language(code). Widget owns x_combo/y_combo, plot, scatter, status_label and Locate region controls. Signals located(records:list,total:int), focused_group(index:int). records include group,row,channel,correlation,ddid,field,scan,antenna1,antenna2,time,frequency,value/axes/flag. Scatter click/rectangle selection finds only displayed preview points, capped records with total count. Render cap explicit; no averaging or writes. Axes identifiers TIME/FREQ/CHAN/AMP/PHASE/REAL/IMAG/U/V/UVDIST; TIME elapsed from common first sample, UV metres; no invented UV when unavailable.

## Ownership and tasks
- [x] Backend worker: model.py, reader.py, new query.py, tests/test_query.py and metadata/provenance tests. TDD contracts and scientific identity, optional intents/history, memory/ranges/error behavior. Do not touch UI or translations.
- [x] Diagnostic worker: new diagnostic.py, tests/test_diagnostic.py. TDD point axes, mask, mixed shape grouping, original identities, scatter click and region Locate, clear stale data, translation; keep own translation map or callback, do not edit i18n/window/model/reader.
- [x] Parent: new overview.py, query_controls.py, workbench.py (UI state/inspector/helpers), tests; integrate window.py/i18n, modern dockable shell and explicit focus vs group selection state. TDD readable unknown calibration state, bilingual UI, grouping/read/Locate lifecycle and file switching.
- [x] Integrate and run full tests/lint; independently review scientific boundaries and UI lifecycle; fix material issues with regressions.
- [ ] Native UI QA, build/install v0.2.0, preserve previous app; CI, publish source and verified DMG/SHA256. Record changes and limitations accurately.
