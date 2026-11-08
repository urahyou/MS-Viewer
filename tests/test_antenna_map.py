"""Real MS/Qt integration: the baseline IDs control the geometry highlight."""

from dataclasses import replace

import numpy as np
import pytest
from casacore.tables import table


@pytest.fixture
def positioned_ms(tiny_ms):
    with table(str(tiny_ms / "ANTENNA"), readonly=False, ack=False) as t:
        t.addrows(1)
        t.putcol("NAME", ["A", "B", "C"])
        t.putcol("POSITION", np.array([[6378137, 0, 0], [6378137, 100, 0], [6378137, 0, 200.0]]))
    with table(str(tiny_ms), readonly=False, ack=False) as t:
        t.putcell("ANTENNA2", 2, 2)  # Field 1 selects A→C, not A→B.
    return tiny_ms


@pytest.fixture
def window(qtbot, positioned_ms):
    from msviewer.window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    w.open_ms(positioned_ms)
    qtbot.waitUntil(lambda: w.plot_data is not None)
    return w


def test_map_has_named_antennas_equal_scale_and_initial_baseline(window):
    assert hasattr(window, "antenna_map"), "Antenna layout tab is missing"
    m = window.antenna_map
    assert window.tabs.indexOf(m) == 2
    np.testing.assert_allclose(m.enu, [[0, 0, 0], [100, 0, 0], [0, 200, 0]], atol=1e-7)
    assert m.selected_ids == (0, 1)
    assert [p.data() for p in m.highlight.points()] == [0, 1]
    assert [p.brush().color().name() for p in m.highlight.points()] == ["#63dfcf", "#e6b86a"]
    np.testing.assert_allclose(m.baseline_line.xData, [0, 100])
    np.testing.assert_allclose(m.baseline_line.yData, [0, 0])
    assert "A (0)" in m.labels[0].toPlainText()
    assert "C (2)" in m.labels[2].toPlainText()
    assert m.plot.getViewBox().state["aspectLocked"] == 1
    assert "100.000 m" in m.baseline_label.text()


def test_reversed_baseline_swaps_highlight_order_without_changing_view(window):
    assert hasattr(window, "antenna_map"), "Missing baseline-linked map"
    m = window.antenna_map
    before = m.plot.viewRange()
    window.baseline_combo.setCurrentIndex(
        next(
            i
            for i in range(window.baseline_combo.count())
            if window.baseline_combo.itemData(i) == (1, 0)
        )
    )
    assert m.selected_ids == (1, 0)
    np.testing.assert_allclose(m.baseline_line.xData, [100, 0])
    assert "B (1) → A (0)" in m.baseline_label.text()
    np.testing.assert_allclose(m.plot.viewRange(), before)


def test_field_and_ddid_refills_refresh_the_highlight(window, qtbot):
    window.field_combo.setCurrentIndex(window.field_combo.findData(1))
    assert hasattr(window, "antenna_map"), "Missing filtered map updates"
    assert window.antenna_map.selected_ids == (0, 2)
    qtbot.waitUntil(lambda: window._job is None)
    window.ddid_combo.setCurrentIndex(1)
    assert window.antenna_map.selected_ids == (0, 1)


def test_language_switch_preserves_geometry_selection_and_read_generation(window):
    assert hasattr(window, "antenna_map"), "Missing bilingual map"
    m = window.antenna_map
    token = window._token
    xyz = m.enu.copy()
    window.set_language("zh")
    assert window.tabs.tabText(2) == "天线位置"
    assert "三维基线长度" in m.baseline_label.text()
    assert "东" in m.plot.getAxis("bottom").label.toPlainText()
    assert "原点" in m.note_label.text()
    assert window._token == token
    np.testing.assert_allclose(m.enu, xyz)
    assert m.selected_ids == (0, 1)
    window.set_language("en")
    assert "3D baseline length" in m.baseline_label.text()


def test_invalid_positions_do_not_prevent_visibility_or_fake_a_line(window):
    assert hasattr(window, "antenna_map"), "Missing unavailable-position handling"
    m = window.antenna_map
    window._set_metadata(replace(window.metadata, antenna_positions=np.zeros((3, 3))))
    assert m.enu is None and m.selected_ids == ()
    assert m.baseline_line.xData is None or not len(m.baseline_line.xData)
    assert "unavailable" in m.baseline_label.text().lower()
    assert window.apply_button.isEnabled()


def test_missing_endpoint_keeps_valid_antenna_but_draws_no_invented_line(window):
    assert hasattr(window, "antenna_map"), "Missing partial-position handling"
    m = window.antenna_map
    xyz = window.metadata.antenna_positions.copy()
    xyz[1] = np.nan
    m.set_metadata(replace(window.metadata, antenna_positions=xyz))
    m.set_baseline((0, 1))
    assert m.selected_ids == (0,)
    assert m.baseline_line.xData is None or not len(m.baseline_line.xData)
    assert "unavailable" in m.baseline_label.text().lower()


def test_autocorrelation_highlights_one_antenna_with_zero_length(window):
    assert hasattr(window, "antenna_map"), "Missing autocorrelation handling"
    m = window.antenna_map
    m.set_baseline((1, 1))
    assert m.selected_ids == (1,)
    assert "Auto-correlation" in m.baseline_label.text()
    assert "0.000 m" in m.baseline_label.text()


def test_failed_open_restores_retained_dataset_highlight(window, tmp_path, qtbot):
    window.open_ms(tmp_path / "missing.ms")
    assert hasattr(window, "antenna_map"), "Missing map open lifecycle"
    assert window.antenna_map.selected_ids == ()
    qtbot.waitUntil(lambda: bool(window.last_error))
    assert window.antenna_map.selected_ids == (0, 1)


def test_new_dataset_replaces_old_points_and_antenna_names(window, qtbot, tmp_path):
    from msviewer.demo import create_demo

    second = create_demo(tmp_path / "second.ms")
    window.open_ms(second)
    qtbot.waitUntil(lambda: window.metadata.path == second and window._job is None)
    assert hasattr(window, "antenna_map"), "Missing dataset replacement"
    assert "DEMO-01" in window.antenna_map.labels[0].toPlainText()
    assert "A (" not in window.antenna_map.labels[0].toPlainText()
    assert window.antenna_map.selected_ids == window.baseline_combo.currentData()


def test_scan_refill_preserves_selected_baseline_when_still_available(window):
    combo = window.baseline_combo
    combo.setCurrentIndex(next(i for i in range(combo.count()) if combo.itemData(i) == (1, 0)))
    window.scan_combo.setCurrentIndex(window.scan_combo.findData(1))
    assert combo.currentData() == (1, 0)
    assert window.antenna_map.selected_ids == (1, 0)
