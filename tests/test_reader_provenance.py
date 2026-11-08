"""Optional metadata and per-sample provenance use the MS source IDs."""

import numpy as np
from casacore.tables import table


def test_legacy_reader_appends_original_ids_and_full_labels(tiny_ms):
    from msviewer.model import Selection
    from msviewer.reader import read_visibility

    block = read_visibility(tiny_ms, Selection(0, 0, 1, max_channels=2))
    np.testing.assert_array_equal(block.row_ids, [1, 2, 0])
    np.testing.assert_array_equal(block.channel_ids, [0, 2])
    np.testing.assert_array_equal(block.field_ids, [0, 1, 0])
    np.testing.assert_array_equal(block.scan_numbers, [1, 2, 1])
    np.testing.assert_array_equal(block.antenna1, [0, 0, 0])
    np.testing.assert_array_equal(block.antenna2, [1, 1, 1])
    assert block.correlation_labels == ("XX", "YY")
    assert block.ddid == 0


def test_scan_intents_from_state_and_bounded_history(tiny_ms):
    from msviewer.reader import HISTORY_LIMIT, inspect_ms

    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.putcol("STATE_ID", [0, 0, 1, 0, -1, -1])
    with table(str(tiny_ms / "STATE"), readonly=False, ack=False) as state:
        state.addrows(2)
        state.putcol(
            "OBS_MODE",
            ["CALIBRATE_PHASE#ON_SOURCE,CALIBRATE_BANDPASS#ON_SOURCE", "OBSERVE_TARGET#ON_SOURCE"],
        )
    with table(str(tiny_ms / "HISTORY"), readonly=False, ack=False) as history:
        history.addrows(HISTORY_LIMIT + 3)
        history.putcol("MESSAGE", [f"event {i}" for i in range(history.nrows())])
    meta = inspect_ms(tiny_ms)
    scan = next(s for s in meta.scans if s.scan == 1 and s.field == 0)
    assert scan.rows == 5
    assert scan.ddids == (0, 1)
    assert scan.start == 5e9 + 10 and scan.end == 5e9 + 40
    assert scan.intents == ("CALIBRATE_BANDPASS#ON_SOURCE", "CALIBRATE_PHASE#ON_SOURCE")
    assert meta.field_intents[0] == scan.intents
    assert meta.field_intents[1] == ("OBSERVE_TARGET#ON_SOURCE",)
    assert len(meta.history) == HISTORY_LIMIT
    assert meta.history[-1] == f"event {HISTORY_LIMIT + 2}"


def test_missing_state_and_history_stay_unknown(tiny_ms):
    from msviewer.reader import inspect_ms

    meta = inspect_ms(tiny_ms)
    assert meta.field_intents == ((), ())
    assert all(s.intents == () for s in meta.scans)
    assert meta.history == ()


def test_optional_uv_missing_column_and_partial_cells(tiny_ms):
    from msviewer.model import Selection
    from msviewer.reader import read_visibility

    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.putcell("UVW", 0, [3, float("nan"), 5])
    assert read_visibility(tiny_ms, Selection(0, 0, 1)).uvw is None
    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.removecols("UVW")
    assert read_visibility(tiny_ms, Selection(0, 0, 1)).uvw is None
