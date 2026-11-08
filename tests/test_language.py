"""Language changes must never reinterpret visibilities, reset filters or trigger I/O."""

import threading

import numpy as np
import pytest
from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QFileDialog, QFormLayout


def make_window(qtbot, path=None):
    from msviewer.window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    if path is not None:
        window.open_ms(path)
        qtbot.waitUntil(lambda: window.block is not None)
    return window


def test_language_menu_switches_empty_window_both_ways(qtbot):
    window = make_window(qtbot)
    window.language_actions["zh"].trigger()
    assert window.open_button.text() == "打开 Measurement Set…"
    assert window.apply_button.text() == "应用筛选"
    assert window.hide_flags.text() == "隐藏已标记样本"
    assert window.time_start.placeholderText() == "起始时间（秒）"
    assert window.tabs.tabText(1) == "MS 元数据"
    assert "只读" in window.status_label.text()
    assert "频谱" == window.spectrum_plot.titleLabel.text
    form = window.selection_panel.findChild(QFormLayout)
    assert form.labelForField(window.baseline_combo).text() == "基线"
    assert window.language_actions["zh"].isChecked()
    window.language_actions["en"].trigger()
    assert window.open_button.text() == "Open Measurement Set…"
    assert window.apply_button.text() == "Apply selection"
    assert window.language_actions["en"].isChecked()


def test_switch_preserves_loaded_selection_data_and_plot_view(qtbot, tiny_ms):
    window = make_window(qtbot, tiny_ms)
    window.field_combo.setCurrentIndex(window.field_combo.findData(1))
    qtbot.waitUntil(lambda: window.block.values.shape[0] == 1)
    window.quantity_combo.setCurrentText("Real")
    block, token = window.block, window._token
    window.spectrum_plot.setXRange(100.4, 101.6, padding=0)
    before_range = window.spectrum_plot.viewRange()
    before_curve = window.spectrum_curve.yData.copy()
    window.set_language("zh")
    assert window.block is block
    assert window._token == token
    assert not window.timer.isActive()
    assert window.field_combo.currentData() == 1
    assert window.quantity_combo.currentData() == "Real"
    assert window.quantity_combo.currentText() == "实部"
    np.testing.assert_array_equal(window.spectrum_curve.yData, before_curve)
    np.testing.assert_allclose(window.spectrum_plot.viewRange(), before_range)
    assert "天线" in window.summary_label.text()
    assert "预览" in window.status_label.text()
    assert "频率" in window.spectrum_plot.getAxis("bottom").label.toPlainText()
    assert "实部" in window.spectrum_plot.getAxis("left").label.toPlainText()
    assert "路径:" in window.metadata_text.toPlainText()
    assert "Calibrator" in window.metadata_text.toPlainText()
    assert window.column_combo.currentText() == "DATA"
    assert window.corr_combo.currentText() == "XX"
    window.set_language("en")
    assert window.quantity_combo.currentText() == "Real"
    assert "Preview" in window.status_label.text()
    assert "Path:" in window.metadata_text.toPlainText()


def test_chinese_quantity_still_uses_stable_processing_identifier(qtbot, tiny_ms):
    window = make_window(qtbot, tiny_ms)
    window.set_language("zh")
    window.quantity_combo.setCurrentIndex(window.quantity_combo.findData("Real"))
    window.hide_flags.setChecked(False)
    np.testing.assert_allclose(window.spectrum_curve.yData, [4, 4, 4])
    window.quantity_combo.setCurrentIndex(window.quantity_combo.findData("Phase"))
    assert window.plot_data.quantity == "Phase"
    assert "相位" in window.time_plot.getAxis("left").label.toPlainText()


def test_language_survives_restart_with_real_settings(qtbot):
    first = make_window(qtbot)
    first.set_language("zh")
    first.close()
    assert QSettings("RadioAstronomy", "MSViewer").value("language") == "zh"
    second = make_window(qtbot)
    assert second.language == "zh"
    assert second.open_button.text() == "打开 Measurement Set…"


def test_errors_retranslate_without_changing_technical_path(qtbot, tmp_path):
    window = make_window(qtbot)
    missing = tmp_path / "not-observation.ms"
    window.open_ms(missing)
    qtbot.waitUntil(lambda: bool(window.last_error))
    window.set_language("zh")
    assert "错误" in window.status_label.text()
    assert "有效的 Measurement Set 目录" in window.status_label.text()
    assert str(missing) in window.status_label.text()
    window.set_language("en")
    assert window.status_label.text().startswith("Error:")


def test_switch_during_read_preserves_previous_selection_warning(qtbot, tiny_ms, monkeypatch):
    import msviewer.window as module

    window = make_window(qtbot, tiny_ms)
    gate, entered = threading.Event(), threading.Event()
    original = module.read_visibility

    def slow(*args):
        entered.set()
        gate.wait(5)
        return original(*args)

    monkeypatch.setattr(module, "read_visibility", slow)
    window.ddid_combo.setCurrentIndex(1)
    qtbot.waitUntil(entered.is_set)
    token = window._token
    try:
        window.set_language("zh")
        assert "上一筛选" in window.spectrum_plot.titleLabel.text
        assert "读取" in window.status_label.text()
        assert window._token == token
    finally:
        gate.set()
    qtbot.waitUntil(lambda: window.block.values.shape == (2, 2, 1))
    assert "预览" in window.status_label.text()
    assert window.plot_data.quantity == "Amplitude"


def test_dialog_caption_and_filter_follow_language(qtbot, tiny_ms, tmp_path, monkeypatch):
    window = make_window(qtbot, tiny_ms)
    window.set_language("zh")
    captions = []

    def open_dialog(parent, caption, *args, **kwargs):
        captions.append(caption)
        return ""

    def save_dialog(parent, caption, directory, file_filter, *args, **kwargs):
        captions.extend([caption, file_filter])
        return str(tmp_path / "export.png"), file_filter

    monkeypatch.setattr(QFileDialog, "getExistingDirectory", open_dialog)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", save_dialog)
    window.choose_ms()
    window.export_png()
    assert captions == ["选择 Measurement Set 目录", "导出可见度图", "PNG 图像 (*.png)"]
    assert (tmp_path / "export.png").is_file()


def test_invalid_saved_language_falls_back_to_english(qtbot):
    settings = QSettings("RadioAstronomy", "MSViewer")
    settings.setValue("language", "invalid")
    window = make_window(qtbot)
    assert window.language == "en"
    with pytest.raises(ValueError):
        window.set_language("invalid")


def test_standard_file_dialog_labels_follow_language(qtbot):
    window = make_window(qtbot)
    window.set_language("zh")
    dialog = QFileDialog(window)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
    qtbot.addWidget(dialog)
    assert dialog.labelText(QFileDialog.DialogLabel.LookIn).replace("&", "") == "查找位置:"
    assert dialog.labelText(QFileDialog.DialogLabel.FileType).replace("&", "") == "文件类型:"
    window.set_language("en")
    english_dialog = QFileDialog(window)
    english_dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
    qtbot.addWidget(english_dialog)
    assert english_dialog.labelText(QFileDialog.DialogLabel.LookIn).replace("&", "") == "Look in:"
