"""Grouped structured selections retain actual scientific sample identities."""

import json
from dataclasses import replace

import numpy as np
import pytest
from casacore.tables import makearrcoldesc, maketabdesc, table


def test_query_groups_mixed_shapes_and_retains_identity(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    blocks = read_query(tiny_ms, SelectionSpec())
    assert len(blocks) == 4
    assert sum(len(b.times) for b in blocks) == 6
    assert sum(b.total_rows for b in blocks) == 6
    assert {b.ddid for b in blocks} == {0, 1}
    for b in blocks:
        assert len(set(b.field_ids)) == len(set(b.scan_numbers)) == 1
        assert len(set(zip(b.antenna1, b.antenna2))) == 1
        assert len(b.channel_ids) == len(b.frequencies) == b.values.shape[1]
        assert len(b.correlation_labels) == b.values.shape[2]
    reverse = next(b for b in blocks if b.antenna1[0] == 1)
    np.testing.assert_array_equal(reverse.row_ids, [3])
    assert reverse.values[0, 0, 0] == 6 + 4j


def test_structured_filters_and_original_decimated_channels(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    spec = SelectionSpec(
        ddids=(0,),
        fields=(0,),
        scans=(1,),
        baselines=((0, 1),),
        correlations=("YY",),
        max_channels=2,
        time_end=5e9 + 30,
    )
    (block,) = read_query(tiny_ms, spec)
    np.testing.assert_array_equal(block.row_ids, [1, 0])
    np.testing.assert_array_equal(block.channel_ids, [0, 2])
    assert block.correlation_labels == ("YY",)
    assert block.values.shape == block.flags.shape == (2, 2, 1)
    assert block.flags[0].all()
    assert not block.flags[1].any()
    assert json.loads(json.dumps(spec.to_dict()))["baselines"] == [[0, 1]]


def test_global_row_budget_preserves_all_groups(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    blocks = read_query(tiny_ms, SelectionSpec(max_rows=4))
    assert len(blocks) == 4
    assert sum(len(b.times) for b in blocks) == 4
    assert sum(b.total_rows for b in blocks) == 6
    with pytest.raises(ValueError, match="[Bb]udget|[Ll]imit"):
        read_query(tiny_ms, SelectionSpec(max_rows=3))


def test_explicit_group_and_memory_budgets(tiny_ms, monkeypatch):
    from msviewer import query

    monkeypatch.setattr(query, "MAX_QUERY_GROUPS", 3)
    with pytest.raises(ValueError, match="[Gg]roup"):
        query.read_query(tiny_ms, query.SelectionSpec())
    monkeypatch.setattr(query, "MAX_QUERY_GROUPS", 128)
    monkeypatch.setattr(query, "PREVIEW_BYTES", 1)
    with pytest.raises(ValueError, match="[Bb]udget|[Mm]emory"):
        query.read_query(tiny_ms, query.SelectionSpec())


def test_uv_filter_and_uv_metres(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.putcol(
            "UVW",
            np.asarray(
                [[3, 4, 9], [0, 2, 1], [6, 8, 2], [1, 0, 0], [3, 4, 1], [0, 1, 2]], dtype=float
            ),
        )
        ms.putcolkeyword("UVW", "QuantumUnits", ["km", "km", "km"])
    blocks = read_query(tiny_ms, SelectionSpec(uv_min=4000, uv_max=6000))
    assert {int(row) for b in blocks for row in b.row_ids} == {0, 4}
    np.testing.assert_array_equal(blocks[0].uvw, [[3000, 4000, 9000]])


def test_unavailable_uv_is_not_zero_and_cannot_filter(tiny_ms):
    from msviewer.model import Selection
    from msviewer.query import SelectionSpec, read_query
    from msviewer.reader import read_visibility

    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.removecolkeyword("UVW", "QuantumUnits")
    block = read_visibility(tiny_ms, Selection(0, 0, 1))
    assert block.uvw is None
    with pytest.raises(ValueError, match="UVW|UV"):
        read_query(tiny_ms, SelectionSpec(uv_min=0))
    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.putcol("UVW", np.ones((6, 3)))
        ms.putcolkeyword("UVW", "QuantumUnits", ["s"])
    assert read_visibility(tiny_ms, Selection(0, 0, 1)).uvw is None


def _add_model(path, unit="Jy", malformed=False):
    with table(str(path), readonly=False, ack=False) as ms:
        ms.addcols(maketabdesc(makearrcoldesc("MODEL_DATA", 0j, ndim=2, valuetype="complex")))
        ms.putcolkeyword("MODEL_DATA", "QuantumUnits", [unit])
        for row in range(ms.nrows()):
            values = ms.getcell("DATA", row)
            ms.putcell(
                "MODEL_DATA", row, np.ones((1, 1) if malformed else values.shape, np.complex64)
            )


def test_residuals_subtract_actual_values_and_preserve_flags(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    _add_model(tiny_ms)
    blocks = read_query(
        tiny_ms,
        SelectionSpec(column="DATA-MODEL_DATA", ddids=(0,), fields=(0,), baselines=((0, 1),)),
    )
    (block,) = blocks
    np.testing.assert_array_equal(block.values[:, 0, 0], [3 + 4j, 2 + 4j])
    assert block.flags[0].all()
    assert block.unit == "Jy"


@pytest.mark.parametrize("unit,malformed", [("K", False), ("Jy", True)])
def test_residual_rejects_incompatible_sources(tiny_ms, unit, malformed):
    from msviewer.query import SelectionSpec, read_query

    _add_model(tiny_ms, unit, malformed)
    with pytest.raises(ValueError, match="[Uu]nit|[Ss]hape"):
        read_query(tiny_ms, SelectionSpec(column="DATA-MODEL_DATA", ddids=(0,)))


@pytest.mark.parametrize(
    "changes",
    [
        {"uv_min": -1},
        {"uv_max": float("nan")},
        {"uv_min": 4, "uv_max": 3},
        {"time_start": float("inf")},
        {"max_rows": 0},
        {"max_channels": 0},
        {"channel_start": -1},
        {"column": "DATA; DROP TABLE"},
        {"correlations": ("NOPE",)},
        {"baselines": ((9, 8),)},
        {"ddids": (99,)},
    ],
)
def test_invalid_structured_query_is_actionable(tiny_ms, changes):
    from msviewer.query import SelectionSpec, read_query

    with pytest.raises(ValueError):
        read_query(tiny_ms, replace(SelectionSpec(), **changes))


def test_memory_budget_is_global_across_groups(tiny_ms, monkeypatch):
    from msviewer import query

    # Four one-row groups fit, but their next row would exceed the shared budget.
    monkeypatch.setattr(query, "PREVIEW_BYTES", 2100)
    blocks = query.read_query(tiny_ms, query.SelectionSpec())
    assert len(blocks) == 4
    assert sum(len(b.times) for b in blocks) == 4
    assert sum(b.total_rows for b in blocks) == 6


def test_query_leaves_actual_ms_contents_unchanged(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    def contents():
        return {
            p.relative_to(tiny_ms): p.read_bytes()
            for p in tiny_ms.rglob("*")
            if p.is_file() and p.name != "table.lock"
        }

    before = contents()
    read_query(tiny_ms, SelectionSpec(max_rows=4))
    assert contents() == before


def test_selection_dict_normalizes_numpy_ids():
    from msviewer.query import SelectionSpec

    spec = SelectionSpec(
        ddids=(np.int64(0),), baselines=((np.int32(1), np.int64(0)),), max_rows=np.int64(42)
    )
    assert json.loads(json.dumps(spec.to_dict()))["ddids"] == [0]


def test_channel_range_is_validated_for_every_matching_ddid(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    with pytest.raises(ValueError, match="Channel"):
        read_query(tiny_ms, SelectionSpec(channel_end=3))
    blocks = read_query(tiny_ms, SelectionSpec(ddids=(0,), channel_start=1, channel_end=3))
    for block in blocks:
        np.testing.assert_array_equal(block.channel_ids, [1, 2])


def test_uv_ranges_then_row_cap_sample_matching_rows(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    with table(str(tiny_ms), readonly=False, ack=False) as ms:
        ms.putcol(
            "UVW",
            np.array(
                [[3, 4, 0], [0, 2, 0], [6, 8, 0], [1, 0, 0], [3, 4, 0], [0, 1, 0]], dtype=float
            ),
        )
    blocks = read_query(
        tiny_ms, SelectionSpec(ddids=(0,), baselines=((0, 1),), uv_min=2, uv_max=5, max_rows=1)
    )
    (block,) = blocks
    assert block.total_rows == 2
    np.testing.assert_array_equal(block.row_ids, [1])
    np.testing.assert_array_equal(block.uvw, [[0, 2, 0]])


def test_quick_preview_supports_same_validated_residual_as_grouped_query(tiny_ms):
    from msviewer.model import Selection
    from msviewer.reader import read_visibility

    _add_model(tiny_ms)
    block = read_visibility(tiny_ms, Selection(0, 0, 1, field=0, column="DATA-MODEL_DATA"))
    np.testing.assert_array_equal(block.values[:, 0, 0], [3 + 4j, 2 + 4j])
    assert block.flags[0].all() and block.unit == "Jy"


def test_boolean_baseline_ids_are_rejected(tiny_ms):
    from msviewer.query import SelectionSpec, read_query

    with pytest.raises(ValueError, match="[Bb]aseline"):
        read_query(tiny_ms, SelectionSpec(baselines=((True, False),)))
