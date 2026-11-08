"""A single frequency bin must remain visible and must not imply spectral structure."""

import numpy as np


def load_window(qtbot, tiny_ms):
    from msviewer.window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.open_ms(tiny_ms)
    qtbot.waitUntil(lambda: window.block is not None)
    window.channel_end.setValue(1)
    qtbot.waitUntil(lambda: window.block.values.shape[1] == 1)
    return window


def test_single_channel_spectrum_draws_a_visible_point(qtbot, tiny_ms):
    window = load_window(qtbot, tiny_ms)
    assert np.isfinite(window.spectrum_curve.yData).sum() == 1
    assert window.spectrum_curve.scatter.isVisible()
    assert len(window.spectrum_curve.scatter.points()) == 1


def test_new_single_channel_read_restores_visible_frequency_extent(qtbot, tiny_ms):
    window = load_window(qtbot, tiny_ms)
    window.spectrum_plot.setXRange(50, 60, padding=0)
    window.request_read()
    qtbot.waitUntil(lambda: window._job is None and window._selection_current)
    low, high = window.spectrum_plot.viewRange()[0]
    assert low < 102 < high
    assert high - low < 1


def test_single_channel_explanation_tracks_language_without_rereading(qtbot, tiny_ms):
    window = load_window(qtbot, tiny_ms)
    token = window._token
    window.set_language("zh")
    assert "仅 1 个频率通道" in window.channel_hint.text()
    assert "102.000000 MHz" in window.channel_hint.text()
    assert "单通道" in window.spectrum_plot.titleLabel.text
    assert "同一通道" in window.waterfall_plot.titleLabel.text
    window.set_language("en")
    assert "one frequency channel" in window.channel_hint.text()
    assert window._token == token


def test_multi_channel_data_clears_single_channel_explanation(qtbot, tiny_ms):
    window = load_window(qtbot, tiny_ms)
    window.channel_end.setValue(3)
    qtbot.waitUntil(lambda: window.block.values.shape[1] == 3)
    assert not window.channel_hint.isVisible()


def test_single_value_y_scale_does_not_keep_previous_large_range(qtbot, tiny_ms):
    window = load_window(qtbot, tiny_ms)
    window.spectrum_plot.setYRange(-100, 100, padding=0)
    window.request_read()
    qtbot.waitUntil(lambda: window._job is None and window._selection_current)
    value = float(window.spectrum_curve.yData[0])
    low, high = window.spectrum_plot.viewRange()[1]
    assert np.isclose((low + high) / 2, value)
    assert high - low < abs(value) * 0.5
