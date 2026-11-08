"""Exercise real Qt workers and plots, including error and thread lifetime behavior."""

import threading

import numpy as np
from PyQt6.QtCore import Qt


def open_window(qtbot, path):
    from msviewer.window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.open_ms(path)
    qtbot.waitUntil(lambda: window.block is not None, timeout=15000)
    return window


def test_open_real_ms_populates_metadata_and_plots(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    assert window.metadata.rows == 6
    assert window.ddid_combo.count() == 2
    assert window.corr_combo.currentText() == "XX"
    assert "SPW 1" in window.ddid_combo.currentText()
    np.testing.assert_array_equal(window.spectrum_curve.xData, [102, 101, 100])
    # First time is row-flagged; remaining amplitudes are 5 and sqrt(41).
    np.testing.assert_allclose(
        window.spectrum_curve.yData, [(5 + np.sqrt(41)) / 2, np.sqrt(41), (5 + np.sqrt(41)) / 2]
    )
    assert window.image_item.image.shape == (3, 3)
    assert "preview" in window.status_label.text().lower()


def test_ddid_changes_polarizations_and_data_shape(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    window.ddid_combo.setCurrentIndex(1)
    qtbot.waitUntil(lambda: window.block is not None and window.block.values.shape == (2, 2, 1))
    assert window.corr_combo.currentText() == "I"
    np.testing.assert_array_equal(window.spectrum_curve.xData, [80, 81])


def test_quantity_and_flag_toggle_update_actual_curves(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    window.quantity_combo.setCurrentText("Real")
    window.hide_flags.setChecked(False)
    np.testing.assert_allclose(window.spectrum_curve.yData, [4, 4, 4])


def test_field_and_channel_filters_apply(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    window.field_combo.setCurrentIndex(window.field_combo.findData(1))
    window.channel_start.setValue(1)
    window.channel_end.setValue(3)
    qtbot.mouseClick(window.apply_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.block is not None and window.block.values.shape == (1, 2, 2))
    np.testing.assert_array_equal(window.spectrum_curve.xData, [101, 100])


def test_invalid_open_keeps_previous_dataset(qtbot, tiny_ms, tmp_path):
    window = open_window(qtbot, tiny_ms)
    original = window.metadata
    window.open_ms(tmp_path / "missing.ms")
    qtbot.waitUntil(lambda: bool(window.last_error))
    assert window.metadata is original
    assert "Measurement Set" in window.last_error
    assert window.spectrum_curve.xData is not None


def test_invalid_time_input_is_shown_without_crashing(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    window.time_start.setText("oops")
    qtbot.mouseClick(window.apply_button, Qt.MouseButton.LeftButton)
    assert window.last_error
    assert window.block is not None


def test_stale_open_result_is_discarded(qtbot, tiny_ms, tmp_path, monkeypatch):
    import msviewer.window as module

    gate = threading.Event()
    entered = threading.Event()
    original = module.inspect_ms

    def slow(path):
        entered.set()
        gate.wait(5)
        return original(path)

    monkeypatch.setattr(module, "inspect_ms", slow)
    window = module.MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.open_ms(tiny_ms)
    qtbot.waitUntil(entered.is_set)
    window.open_ms(tmp_path / "missing.ms")
    gate.set()
    qtbot.waitUntil(lambda: bool(window.last_error))
    assert window.metadata is None
    assert window.block is None


def test_close_waits_for_active_read(qtbot, tiny_ms, monkeypatch):
    import msviewer.window as module

    window = open_window(qtbot, tiny_ms)
    gate = threading.Event()
    entered = threading.Event()
    original = module.read_visibility

    def slow(*args):
        entered.set()
        gate.wait(5)
        return original(*args)

    monkeypatch.setattr(module, "read_visibility", slow)
    window.request_read()
    qtbot.waitUntil(entered.is_set)
    window.close()
    assert window.isVisible()
    gate.set()
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=10000)


def test_selection_changes_cannot_cancel_opening_another_dataset(
    qtbot, tiny_ms, tmp_path, monkeypatch
):
    import shutil

    import msviewer.window as module

    second = tmp_path / "second.ms"
    shutil.copytree(tiny_ms, second)
    window = open_window(qtbot, tiny_ms)
    gate, entered = threading.Event(), threading.Event()
    original = module.inspect_ms

    def slow(path):
        entered.set()
        gate.wait(5)
        return original(path)

    monkeypatch.setattr(module, "inspect_ms", slow)
    window.open_ms(second)
    qtbot.waitUntil(entered.is_set)
    window.max_rows.setValue(2)  # programmatic signals must also respect open priority
    qtbot.wait(250)
    gate.set()
    qtbot.waitUntil(lambda: window._job is None and not window.timer.isActive())
    assert window.metadata.path == second.resolve()
    assert window.block is not None


def test_new_correlation_never_renders_old_ddid_block(qtbot, tiny_ms, monkeypatch):
    import msviewer.window as module

    window = open_window(qtbot, tiny_ms)
    original_curve = window.spectrum_curve.yData.copy()
    gate, entered = threading.Event(), threading.Event()
    original = module.read_visibility

    def slow(*args):
        entered.set()
        gate.wait(5)
        return original(*args)

    monkeypatch.setattr(module, "read_visibility", slow)
    window.ddid_combo.setCurrentIndex(1)
    qtbot.waitUntil(entered.is_set)
    window.quantity_combo.setCurrentText("Real")
    # DDID1 is Stokes I; old DDID0's XX must not be rendered under this label.
    np.testing.assert_allclose(window.spectrum_curve.yData, original_curve)
    assert "previous selection" in window.spectrum_plot.titleLabel.text.lower()
    gate.set()
    qtbot.waitUntil(lambda: window.block.values.shape == (2, 2, 1))
    np.testing.assert_array_equal(window.spectrum_curve.yData, [7.5, 7.5])


import pytest


@pytest.mark.parametrize("kind", ["empty", "missing_column"])
def test_unusable_ms_preserves_previous_dataset_and_plot(qtbot, tiny_ms, tmp_path, kind):
    import shutil

    from casacore.tables import table

    window = open_window(qtbot, tiny_ms)
    original_meta, original_block = window.metadata, window.block
    original_curve = window.spectrum_curve.yData.copy()
    bad = tmp_path / f"{kind}.ms"
    shutil.copytree(tiny_ms, bad)
    with table(str(bad), readonly=False, ack=False) as t:
        if kind == "empty":
            t.removerows(list(range(t.nrows())))
        else:
            t.removecols("DATA")
    window.open_ms(bad)
    qtbot.waitUntil(lambda: bool(window.last_error))
    assert window.metadata is original_meta
    assert window.block is original_block
    np.testing.assert_allclose(window.spectrum_curve.yData, original_curve)


def test_waterfall_uses_available_plot_extent(qtbot, tiny_ms):
    window = open_window(qtbot, tiny_ms)
    x_range, y_range = window.waterfall_plot.viewRange()
    assert x_range[1] - x_range[0] < 3.5
    assert y_range[1] - y_range[0] < 3.5


def test_frequency_axis_keeps_mhz_units_at_ghz_frequencies(qtbot, tiny_ms):
    from casacore.tables import table

    with table(str(tiny_ms / "SPECTRAL_WINDOW"), readonly=False, ack=False) as t:
        t.putcell("CHAN_FREQ", 1, np.array([1.4e9, 1.35e9, 1.3e9]))
    window = open_window(qtbot, tiny_ms)
    qtbot.wait(50)
    np.testing.assert_array_equal(window.spectrum_curve.xData, [1400, 1350, 1300])
    assert window.spectrum_plot.getAxis("bottom").label.toPlainText() == "Frequency (MHz)"
