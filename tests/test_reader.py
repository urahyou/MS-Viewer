"""Catch incorrect DDID mapping, full-column reads, slicing, and lost row flags."""

from dataclasses import replace

import numpy as np
import pytest
from casacore.tables import makearrcoldesc, maketabdesc, table

from msviewer.model import Selection


def test_inspect_maps_ddid_through_subtables(tiny_ms):
    from msviewer.reader import inspect_ms

    meta = inspect_ms(tiny_ms)
    assert meta.rows == 6
    assert meta.antennas == ("A", "B")
    assert meta.descriptions[0].spw == 1
    assert meta.descriptions[0].correlations == ("XX", "YY")
    assert meta.descriptions[1].correlations == ("I",)
    np.testing.assert_array_equal(meta.descriptions[0].frequencies, [102e6, 101e6, 100e6])
    assert meta.time_range == (5e9 + 10, 5e9 + 40)
    assert (0, 1, 2, 0, 1) in meta.partitions


def test_reader_sorts_filters_and_combines_flags(tiny_ms):
    from msviewer.reader import read_visibility

    data = read_visibility(tiny_ms, Selection(0, 0, 1, field=0, scan=1))
    assert data.values.shape == (2, 3, 2)
    np.testing.assert_array_equal(data.row_ids, [1, 0])
    np.testing.assert_array_equal(data.times, [5e9 + 10, 5e9 + 30])
    assert data.flags[0].all()
    assert data.flags[1, 1, 0]
    assert not data.flags[1, 0, 0]
    assert data.unit == "Jy"


def test_row_and_channel_caps_sample_across_selection(tiny_ms):
    from msviewer.reader import read_visibility

    data = read_visibility(tiny_ms, Selection(0, 0, 1, max_rows=2, max_channels=2))
    assert data.total_rows == 3
    assert data.values.shape == (2, 2, 2)
    np.testing.assert_array_equal(data.row_ids, [1, 0])
    np.testing.assert_array_equal(data.frequencies, [102e6, 100e6])


def test_channel_and_time_bounds(tiny_ms):
    from msviewer.reader import read_visibility

    data = read_visibility(
        tiny_ms,
        Selection(0, 0, 1, time_start=5e9 + 20, time_end=5e9 + 30, channel_start=1, channel_end=3),
    )
    assert data.values.shape == (2, 2, 2)
    np.testing.assert_array_equal(data.frequencies, [101e6, 100e6])


@pytest.mark.parametrize(
    "changes",
    [
        {"ddid": 99},
        {"antenna2": 99},
        {"column": "MODEL_DATA"},
        {"max_rows": 0},
        {"max_channels": 0},
        {"channel_start": -1},
        {"channel_start": 3},
        {"channel_end": 9},
        {"time_start": float("nan")},
        {"time_start": 5e9 + 50, "time_end": 5e9 + 10},
    ],
)
def test_invalid_or_empty_selection_is_actionable(tiny_ms, changes):
    from msviewer.reader import read_visibility

    with pytest.raises(ValueError):
        read_visibility(tiny_ms, replace(Selection(0, 0, 1), **changes))


def test_invalid_path(tmp_path):
    from msviewer.reader import inspect_ms

    with pytest.raises(ValueError):
        inspect_ms(tmp_path / "missing.ms")


def test_float_data_only_ms_and_original_content_unchanged(tiny_ms):
    from msviewer.reader import inspect_ms, read_visibility

    with table(str(tiny_ms), readonly=False, ack=False) as t:
        t.addcols(maketabdesc(makearrcoldesc("FLOAT_DATA", 0.0, ndim=2)))
        for row in range(t.nrows()):
            t.putcell("FLOAT_DATA", row, t.getcell("DATA", row).real)
        t.removecols("DATA")
    before = {
        p.relative_to(tiny_ms): p.read_bytes()
        for p in tiny_ms.rglob("*")
        if p.is_file() and p.name != "table.lock"
    }
    meta = inspect_ms(tiny_ms)
    assert meta.columns == ("FLOAT_DATA",)
    data = read_visibility(tiny_ms, Selection(1, 0, 1, column="FLOAT_DATA"))
    np.testing.assert_array_equal(data.values[:, :, 0], [[7, 7], [8, 8]])
    after = {
        p.relative_to(tiny_ms): p.read_bytes()
        for p in tiny_ms.rglob("*")
        if p.is_file() and p.name != "table.lock"
    }
    assert before == after
