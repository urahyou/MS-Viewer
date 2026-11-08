import json

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget


def opened(qtbot, path):
    from msviewer.window import MainWindow

    w = MainWindow()
    qtbot.addWidget(w)
    w.show()
    w.open_ms(path)
    qtbot.waitUntil(lambda: w.plot_data is not None)
    return w


def test_dockable_workbench_keeps_existing_views_and_overview(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    assert isinstance(w.selection_dock, QDockWidget)
    assert isinstance(w.inspector_dock, QDockWidget)
    assert isinstance(w.log_dock, QDockWidget)
    assert w.tabs.tabText(1) == "MS metadata"
    assert w.tabs.indexOf(w.overview) >= 0 and w.tabs.indexOf(w.diagnostic) >= 0
    assert w.overview.metadata is w.metadata
    w.set_language("zh")
    assert w.selection_dock.windowTitle() == "数据与筛选"
    assert w.tabs.tabText(w.tabs.indexOf(w.overview)) == "观测总览"


def test_grouped_read_separates_fields_and_scans_and_locates_original_sample(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.selection_modes.setCurrentIndex(1)
    w.request_query()
    qtbot.waitUntil(lambda: w._job is None and len(w._blocks) == 2)
    assert [b.field_ids[0] for b in w._blocks] == [0, 1]
    assert w.focus_combo.count() == 2
    w.diagnostic.hide_flags.setChecked(False)
    records = w.diagnostic.records_for_indices(np.arange(len(w.diagnostic._x)))
    index = next(
        i
        for i, r in enumerate(records)
        if r["row"] == 2 and r["channel"] == 1 and r["correlation"] == "XX"
    )
    w.diagnostic.locate_indices([index])
    assert w.inspector.records[0]["row"] == 2
    assert w.inspector.records[0]["channel"] == 1
    assert w.block.row_ids[0] == 2
    assert w.linked_cursor.position == (0, 1)
    assert w.antenna_map.baseline == (0, 1)
    assert not w.timer.isActive()


def test_selection_change_disables_locate_until_new_generation(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    assert len(w.diagnostic._x) > 0
    w.channel_start.setValue(1)
    assert not w._selection_current
    assert len(w.diagnostic._x) == 0
    assert not w.inspector.records
    qtbot.waitUntil(lambda: w._selection_current and w._job is None)
    assert all(int(c) >= 1 for c in w.block.channel_ids)


def test_switching_files_restores_each_datasets_quick_selection(qtbot, tiny_ms, tmp_path):
    from msviewer.demo import create_demo

    w = opened(qtbot, tiny_ms)
    w.channel_start.setValue(1)
    qtbot.waitUntil(lambda: w._selection_current and w.block.values.shape[1] == 2)
    second = create_demo(tmp_path / "second.ms")
    w.open_ms(second)
    qtbot.waitUntil(lambda: w.metadata.path == second and w._selection_current and w._job is None)
    assert w.channel_start.value() == 0
    w.open_ms(tiny_ms)
    qtbot.waitUntil(lambda: w.metadata.path == tiny_ms and w._selection_current and w._job is None)
    assert w.channel_start.value() == 1
    assert w.block.values.shape[1] == 2
    assert w.dataset_combo.count() == 2


def test_layout_roundtrip_theme_and_parameter_copy_do_not_read_ms(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    token = w._token
    w.inspector_dock.show()
    w.save_layout()
    w.inspector_dock.hide()
    w.restore_layout()
    assert not w.inspector_dock.isHidden()
    w.set_theme("light")
    assert w.theme == "light"
    w.set_language("zh")
    json.loads(w.query_controls.parameter_json())
    assert w._token == token
    assert not w.timer.isActive()


def test_editing_grouped_draft_invalidates_old_locate_without_starting_a_read(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.selection_modes.setCurrentIndex(1)
    w.request_query()
    qtbot.waitUntil(lambda: w._job is None and w._selection_current)
    assert len(w.diagnostic._x)
    w.query_controls.time_start.setText("10")
    assert not w._selection_current
    assert not len(w.diagnostic._x)
    assert not w.timer.isActive() and w._job is None


def test_point_inspector_includes_spw_dataset_time_and_unit(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.diagnostic.locate_indices([0])
    record = w.inspector.records[0]
    assert record["dataset"] == str(tiny_ms)
    assert record["spw"] == 1 and record["unit"] == "Jy"
    assert "UTC" in w.inspector.details.toPlainText()
    assert str(record["channel"]) in w.inspector.details.toPlainText()


def test_changing_focus_clears_old_locate_details(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.selection_modes.setCurrentIndex(1)
    w.request_query()
    qtbot.waitUntil(lambda: w._job is None and len(w._blocks) == 2)
    w.diagnostic.locate_indices([0])
    assert w.inspector.records
    w.focus_combo.setCurrentIndex(1)
    assert not w.inspector.records
    assert not len(w.diagnostic.selected_indices)


def test_failed_open_keeps_focused_group_antenna_pair(qtbot, tiny_ms, tmp_path):
    w = opened(qtbot, tiny_ms)
    w.selection_modes.setCurrentIndex(1)
    for i in range(w.query_controls.baselines.count()):
        w.query_controls.baselines.item(i).setCheckState(Qt.CheckState.Unchecked)
    w.request_query()
    qtbot.waitUntil(lambda: w._job is None and w._selection_current)
    index = next(i for i, b in enumerate(w._blocks) if int(b.antenna1[0]) == 1)
    w.focus_combo.setCurrentIndex(index)
    assert w.antenna_map.baseline == (1, 0)
    w.open_ms(tmp_path / "missing.ms")
    qtbot.waitUntil(lambda: w._job is None and not w._opening)
    assert w.antenna_map.baseline == (1, 0)
    assert w.focus_combo.currentIndex() == index


def test_theme_and_recent_datasets_survive_new_window(qtbot, tiny_ms):
    from msviewer.window import MainWindow

    w = opened(qtbot, tiny_ms)
    w.set_theme("light")
    w.settings.sync()
    second = MainWindow()
    qtbot.addWidget(second)
    assert second.theme == "light" and second.theme_action.isChecked()
    assert str(tiny_ms) in [
        second.dataset_combo.itemData(i) for i in range(second.dataset_combo.count())
    ]


def test_stale_focus_cannot_reactivate_results_after_grouped_draft_edit(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.selection_modes.setCurrentIndex(1)
    w.request_query()
    qtbot.waitUntil(lambda: w._job is None and len(w._blocks) == 2)
    w.query_controls.time_start.setText("999")
    assert not w._selection_current
    w.focus_combo.setCurrentIndex(1)
    assert not w._selection_current
    assert not w.focus_combo.isEnabled()
    assert w.linked_cursor.position is None


def test_existing_legend_and_time_title_repaint_on_theme_change(qtbot, tiny_ms):
    w = opened(qtbot, tiny_ms)
    w.set_theme("light")
    legend_label = w.diagnostic.legend.items[0][1]
    assert "#25344a" in legend_label.item.toHtml()
    assert "#25344a" in w.diagnostic.plot.getPlotItem().titleLabel.item.toHtml()
    w.set_theme("dark")
    assert "#aebdce" in legend_label.item.toHtml()
    assert "#aebdce" in w.diagnostic.plot.getPlotItem().titleLabel.item.toHtml()
