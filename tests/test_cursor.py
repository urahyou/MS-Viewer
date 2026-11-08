"""Linked cursors use physical coordinates and never replace the preview means."""

import numpy as np
import pytest
from PyQt6.QtCore import QEvent, QPointF
from PyQt6.QtWidgets import QApplication


@pytest.fixture
def window(qtbot, tiny_ms):
    from msviewer.window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.open_ms(tiny_ms)
    qtbot.waitUntil(lambda: window.plot_data is not None)
    qtbot.wait(40)  # Initial status/axis layout is independent of the hover being tested.
    return window


def hover(window, plot, x, y):
    point = plot.getViewBox().mapViewToScene(QPointF(x, y))
    window.graphics.scene().sigMouseMoved.emit(point)


def test_waterfall_links_pixel_centres_to_physical_axes(window):
    hover(window, window.waterfall_plot, 1.2, 2.2)
    assert hasattr(window, "linked_cursor"), "Missing three-plot cursor controller"
    c = window.linked_cursor
    assert c.position == (2, 1)
    assert c.spectrum_line.value() == 101
    assert c.time_line.value() == 20
    assert c.channel_line.value() == 1.5
    assert c.row_line.value() == 2.5
    assert all(line.isVisible() for line in c.lines)
    assert "MS row 0" in window.cursor_label.text()


def test_spectrum_only_selects_frequency_until_time_is_known(window):
    hover(window, window.spectrum_plot, 101.3, 6)
    assert window._cursor_position == (None, 1)
    c = window.linked_cursor
    assert c.spectrum_line.value() == 101
    assert c.channel_line.value() == 1.5
    assert not c.row_line.isVisible() and not c.time_line.isVisible()
    hover(window, window.time_plot, 17, 6)
    assert c.position == (2, 1)
    assert c.time_line.value() == 20


def test_time_selects_nearest_actual_irregular_sample(window):
    from dataclasses import replace

    window.block = replace(window.block, times=np.array([5e9, 5e9 + 2, 5e9 + 100]))
    window._render(reset_view=True)
    hover(window, window.time_plot, 80, 6)
    assert window._cursor_position == (2, None)
    assert window.linked_cursor.row_line.value() == 2.5
    assert window.linked_cursor.time_line.value() == 100
    assert not window.linked_cursor.spectrum_line.isVisible()


def test_hover_changes_neither_means_view_colour_nor_read_requests(window, qtbot):
    curves = [(c.xData.copy(), c.yData.copy()) for c in (window.spectrum_curve, window.time_curve)]
    plots = (window.spectrum_plot, window.time_plot, window.waterfall_plot)
    ranges = [p.viewRange() for p in plots]
    levels = window.colorbar.levels()
    token, plot_data = window._token, window.plot_data
    for x, y in ((0.2, 0.2), (2.8, 2.8), (1.5, 1.5)):
        hover(window, window.waterfall_plot, x, y)
    qtbot.wait(30)
    for c, (x, y) in zip((window.spectrum_curve, window.time_curve), curves):
        np.testing.assert_equal(c.xData, x)
        np.testing.assert_equal(c.yData, y)
    for plot, bounds in zip(plots, ranges):
        np.testing.assert_allclose(plot.viewRange(), bounds)
    assert window.colorbar.levels() == levels
    assert window._token == token and window.plot_data is plot_data
    assert not window.timer.isActive()


def test_flagged_mean_has_no_fabricated_marker(window):
    hover(window, window.waterfall_plot, 1.1, 0.1)
    assert hasattr(window, "linked_cursor"), "Missing linked mean markers"
    c = window.linked_cursor
    assert c.time_line.isVisible() and not c.time_marker.isVisible()
    assert c.spectrum_marker.isVisible()
    x, y = c.spectrum_marker.getData()
    np.testing.assert_allclose(x, [101])
    np.testing.assert_allclose(y, [window.plot_data.spectrum[1]])


@pytest.mark.parametrize("leave_widget", [False, True])
def test_leaving_data_clears_overlays_and_coordinate_readout(window, leave_widget):
    hover(window, window.waterfall_plot, 1.2, 1.2)
    if leave_widget:
        QApplication.sendEvent(window.graphics.viewport(), QEvent(QEvent.Type.Leave))
    else:
        window.graphics.scene().sigMouseMoved.emit(QPointF(-100, -100))
    assert window._cursor_position is None
    assert not any(line.isVisible() for line in window.linked_cursor.lines)
    assert "MS row" not in window.cursor_label.text()


def test_selection_change_clears_and_blocks_old_coordinates(window):
    hover(window, window.waterfall_plot, 1.2, 1.2)
    window.channel_start.setValue(1)
    assert window._cursor_position is None
    hover(window, window.waterfall_plot, 1.2, 1.2)
    assert window._cursor_position is None
    assert not any(line.isVisible() for line in window.linked_cursor.lines)


def test_readout_distinguishes_hidden_sample_from_means_and_translates(window):
    hover(window, window.waterfall_plot, 1.2, 0.2)
    label = window.cursor_label.text()
    assert "Preview channel 1" in label
    assert "101.000000 MHz" in label
    assert "Flagged" in label and "hidden" in label
    assert "Spectrum mean" in label and "Time mean" in label
    assert "Sample Amplitude" in label
    token = window._token
    window.set_language("zh")
    label = window.cursor_label.text()
    assert "预览通道 1" in label and "已标记" in label
    assert "频谱均值" in label and "时间均值" in label and "单样本振幅" in label
    assert window._token == token
    window.set_language("en")
    assert "Sample Amplitude" in window.cursor_label.text()


def test_opening_a_new_ms_immediately_disables_old_cursor(window, tiny_ms, qtbot):
    hover(window, window.waterfall_plot, 1.2, 1.2)
    window.open_ms(tiny_ms)
    assert window._cursor_position is None
    hover(window, window.waterfall_plot, 1.2, 1.2)
    assert window._cursor_position is None
    qtbot.waitUntil(lambda: not window._opening and window._job is None)
    assert window._cursor_position is None


def test_single_channel_single_time_still_links_and_has_finite_markers(window, qtbot):
    window.field_combo.setCurrentIndex(window.field_combo.findData(1))
    window.channel_end.setValue(1)
    qtbot.waitUntil(lambda: window.block.values.shape[:2] == (1, 1))
    hover(window, window.waterfall_plot, 0.5, 0.5)
    assert hasattr(window, "linked_cursor"), "Missing single-bin linked cursor"
    assert window.linked_cursor.position == (0, 0)
    assert window.linked_cursor.spectrum_line.value() == 102
    assert window.linked_cursor.time_line.value() == 0
    assert all(line.isVisible() for line in window.linked_cursor.lines)
    assert window.linked_cursor.time_marker.isVisible()
    assert window.linked_cursor.spectrum_marker.isVisible()


def test_failed_open_restores_cursor_on_retained_dataset(window, tmp_path, qtbot):
    window.open_ms(tmp_path / "missing.ms")
    qtbot.waitUntil(lambda: bool(window.last_error))
    hover(window, window.waterfall_plot, 1.2, 1.2)
    assert window._cursor_position == (1, 1)


def test_actual_scene_zoom_mapping_uses_samples_after_decimation(window, qtbot):
    window.max_rows.setValue(2)
    window.max_channels.setValue(2)
    qtbot.waitUntil(lambda: window.block.values.shape[:2] == (2, 2))
    window.waterfall_plot.setXRange(0.5, 1.9, padding=0)
    window.waterfall_plot.setYRange(0.5, 1.9, padding=0)
    hover(window, window.waterfall_plot, 1.25, 1.25)
    assert window._cursor_position == (1, 1)
    assert window.linked_cursor.spectrum_line.value() == window.block.frequencies[1] / 1e6
    assert f"MS row {window.block.row_ids[1]}" in window.cursor_label.text()


def test_axes_and_colourbar_do_not_count_as_data_regions(window):
    hover(window, window.waterfall_plot, 1.2, 1.2)
    axis_label = window.spectrum_plot.getAxis("bottom").label
    label = axis_label.mapToScene(axis_label.boundingRect().center())
    window.graphics.scene().sigMouseMoved.emit(label)
    assert window._cursor_position is None

    hover(window, window.waterfall_plot, 1.2, 1.2)
    window.graphics.scene().sigMouseMoved.emit(window.colorbar.vb.sceneBoundingRect().center())
    assert window._cursor_position is None


def test_readout_does_not_resize_plots_when_text_wraps(window, qtbot):
    window.resize(980, 800)
    qtbot.wait(40)  # Let the explicit window resize settle before testing mouse movement.
    size = window.graphics.size()
    bounds = [p.viewRange() for p in (window.spectrum_plot, window.time_plot)]
    hover(window, window.waterfall_plot, 1.2, 1.2)
    qtbot.wait(40)
    assert window.graphics.size() == size
    for plot, before in zip((window.spectrum_plot, window.time_plot), bounds):
        np.testing.assert_allclose(plot.viewRange(), before)
