"""Exercise individual visibility axes, original identities and real scene Locate."""

from dataclasses import replace

import numpy as np
from PyQt6.QtCore import QPointF, Qt

from msviewer.diagnostic import DiagnosticView
from msviewer.model import VisibilityBlock


def block(**changes):
    original = VisibilityBlock(
        times=np.array([5e9 + 20, 5e9 + 10]),
        frequencies=np.array([120e6, 110e6]),
        values=np.array([[[3 + 4j, 0j], [2 + 0j, 1j]], [[1 + 0j, 2j], [4j, 6j]]]),
        flags=np.array([[[False, False], [True, False]], [[False, False], [False, False]]]),
        row_ids=np.array([8, 3]),
        total_rows=2,
        unit="Jy",
        channel_ids=np.array([7, 11]),
        uvw=np.array([[3.0, 4.0, 0.0], [8.0, 15.0, 0.0]]),
        field_ids=np.array([2, 2]),
        scan_numbers=np.array([9, 9]),
        antenna1=np.array([4, 4]),
        antenna2=np.array([1, 1]),
        ddid=6,
        correlation_labels=("XX", "YY"),
    )
    return replace(original, **changes)


def view(qtbot):
    widget = DiagnosticView()
    qtbot.addWidget(widget)
    widget.resize(900, 600)
    widget.show()
    return widget


def axis(combo, identifier):
    combo.setCurrentIndex(combo.findData(identifier))


def test_samples_are_individual_and_time_has_common_origin(qtbot):
    widget = view(qtbot)
    later = block(
        times=np.array([5e9 + 50]),
        values=np.array([[[10j]]]),
        flags=np.zeros((1, 1, 1), bool),
        frequencies=np.array([90e6]),
        row_ids=np.array([99]),
        channel_ids=np.array([24]),
        uvw=None,
        correlation_labels=("I",),
    )
    widget.set_blocks((block(), later))
    x, y = widget.scatter.getData()
    assert len(x) == 8  # no means; one flagged sample hidden, heterogeneous group retained
    np.testing.assert_array_equal(x, [10, 10, 10, 0, 0, 0, 0, 40])
    np.testing.assert_allclose(y, [5, 0, 1, 1, 2, 4, 6, 10])
    assert widget.plot.getAxis("bottom").labelUnits == "s"
    assert "5000000010" in widget.plot.getAxis("bottom").labelText
    assert len(widget.legend.items) == 2


def test_original_channels_uv_metres_and_phase_zero_mask(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    axis(widget.x_combo, "CHAN")
    np.testing.assert_array_equal(widget.scatter.getData()[0], [7, 7, 11, 7, 7, 11, 11])
    axis(widget.x_combo, "UVDIST")
    np.testing.assert_array_equal(widget.scatter.getData()[0], [5, 5, 5, 17, 17, 17, 17])
    assert widget.plot.getAxis("bottom").labelUnits == "m"
    axis(widget.y_combo, "PHASE")
    assert len(widget.scatter.getData()[0]) == 6  # zero complex phase is unknown
    np.testing.assert_allclose(
        widget.scatter.getData()[1], [np.degrees(np.arctan2(4, 3)), 90, 0, 90, 90, 90]
    )
    assert widget.plot.getAxis("left").labelUnits == "deg"


def test_missing_uv_and_nonfinite_values_do_not_invent_points(qtbot):
    widget = view(qtbot)
    values = block().values.copy()
    values[1, 0, 0] = complex(np.nan, 2)
    widget.set_blocks((block(values=values, uvw=None),))
    assert len(widget.scatter.getData()[0]) == 6
    axis(widget.x_combo, "U")
    assert len(widget.scatter.getData()[0]) == 0
    assert "UVW" in widget.status_label.text()


def test_region_locate_has_exact_original_identity_and_scene_roi(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    captured = []
    widget.located.connect(lambda records, total: captured.append((records, total)))
    qtbot.mouseClick(widget.region_button, Qt.MouseButton.LeftButton)
    assert widget.roi.isVisible()
    assert widget.roi.scene() is widget.plot.scene()
    widget.roi.setPos((9, 4.9))
    widget.roi.setSize((2, 0.2))
    qtbot.mouseClick(widget.locate_button, Qt.MouseButton.LeftButton)
    records, total = captured[-1]
    assert total == len(records) == 1
    record = records[0]
    assert {
        key: record[key]
        for key in (
            "group",
            "row",
            "channel",
            "correlation",
            "ddid",
            "field",
            "scan",
            "antenna1",
            "antenna2",
            "time",
            "frequency",
            "value",
            "flag",
        )
    } == {
        "group": 0,
        "row": 8,
        "channel": 7,
        "correlation": "XX",
        "ddid": 6,
        "field": 2,
        "scan": 9,
        "antenna1": 4,
        "antenna2": 1,
        "time": 5e9 + 20,
        "frequency": 120e6,
        "value": 3 + 4j,
        "flag": False,
    }
    qtbot.mouseClick(widget.clear_selection_button, Qt.MouseButton.LeftButton)
    assert captured[-1] == ([], 0)
    assert not widget.roi.isVisible()


def test_actual_scatter_click_locates_and_focuses_group(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    captured, focused = [], []
    widget.located.connect(lambda records, total: captured.append((records, total)))
    widget.focused_group.connect(focused.append)
    qtbot.wait(30)
    scene_position = widget.plot.getViewBox().mapViewToScene(QPointF(10, 5))
    position = widget.plot.mapFromScene(scene_position)
    qtbot.mouseClick(widget.plot.viewport(), Qt.MouseButton.LeftButton, pos=position)
    assert captured[-1][1] == 1
    assert captured[-1][0][0]["row"] == 8
    assert focused[-1] == 0


def test_axes_data_and_flag_changes_clear_stale_selection(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    captured = []
    widget.located.connect(lambda records, total: captured.append((records, total)))
    widget.locate_indices(np.array([0]))
    assert captured[-1][1] == 1
    axis(widget.x_combo, "FREQ")
    assert captured[-1] == ([], 0)
    widget.locate_indices(np.array([0]))
    widget.hide_flags.setChecked(False)
    assert captured[-1] == ([], 0)
    assert len(widget.scatter.getData()[0]) == 8
    widget.locate_indices(np.array([0]))
    widget.set_blocks((block(),))
    assert captured[-1] == ([], 0)
    widget.clear()
    assert len(widget.scatter.getData()[0]) == 0
    assert not widget.locate_button.isEnabled()


def test_translations_preserve_science_selection_and_user_ranges(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    widget.plot.setRange(xRange=(1, 2), yRange=(3, 4), padding=0)
    widget.locate_indices(np.array([0]))
    before = widget.scatter.getData()
    ranges = widget.plot.getViewBox().viewRange()
    captured = []
    widget.located.connect(lambda *args: captured.append(args))
    widget.set_language("zh")
    assert widget.x_combo.currentData() == "TIME"
    assert widget.y_combo.currentData() == "AMP"
    np.testing.assert_array_equal(widget.scatter.getData(), before)
    np.testing.assert_allclose(widget.plot.getViewBox().viewRange(), ranges)
    assert widget.selected_indices.tolist() == [0]
    assert not captured
    assert "预览" in widget.status_label.text()
    axis(widget.x_combo, "FREQ")
    np.testing.assert_allclose(widget.plot.getViewBox().viewRange(), ranges)


def test_global_sampling_and_record_limits_are_explicit(qtbot):
    widget = view(qtbot)
    widget.MAX_POINTS = 17
    widget.MAX_RECORDS = 3
    big = block(
        times=np.arange(500.0),
        values=np.ones((500, 2, 2), complex),
        flags=np.zeros((500, 2, 2), bool),
        row_ids=np.arange(1000, 1500),
        uvw=None,
    )
    widget.set_blocks((big, big))
    assert len(widget.scatter.getData()[0]) <= 17
    assert len(widget._flat_indices) <= 17
    assert "4,000" in widget.status_label.text()
    assert "17" in widget.status_label.text()
    captured = []
    widget.located.connect(lambda records, total: captured.append((records, total)))
    widget.locate_indices(np.arange(17))
    assert len(captured[-1][0]) == 3
    assert captured[-1][1] == 17
    assert "3" in widget.status_label.text()


def test_real_ms_flags_and_original_preview_rows(qtbot, tiny_ms):
    from msviewer.model import Selection
    from msviewer.reader import read_visibility

    widget = view(qtbot)
    real = read_visibility(tiny_ms, Selection(ddid=0, antenna1=0, antenna2=1))
    widget.set_blocks((real,))
    expected = int(np.count_nonzero(~real.flags))
    assert len(widget.scatter.getData()[0]) == expected
    records = widget.records_for_indices(np.arange(expected))
    assert {record["row"] for record in records} == {0, 2}
    assert all(not record["flag"] for record in records)


def test_frequency_real_imaginary_and_signed_uv_axes(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(uvw=np.array([[-3.0, 4.0, 0.0], [8.0, -15.0, 0.0]])),))
    axis(widget.x_combo, "FREQ")
    axis(widget.y_combo, "REAL")
    np.testing.assert_array_equal(widget.scatter.getData()[0], [120, 120, 110, 120, 120, 110, 110])
    np.testing.assert_array_equal(widget.scatter.getData()[1], [3, 0, 0, 1, 0, 0, 0])
    assert widget.plot.getAxis("bottom").labelUnits == "MHz"
    assert widget.plot.getAxis("left").labelUnits == "Jy"
    axis(widget.x_combo, "U")
    axis(widget.y_combo, "V")
    np.testing.assert_array_equal(widget.scatter.getData()[0], [-3, -3, -3, 8, 8, 8, 8])
    np.testing.assert_array_equal(widget.scatter.getData()[1], [4, 4, 4, -15, -15, -15, -15])
    axis(widget.y_combo, "IMAG")
    np.testing.assert_array_equal(widget.scatter.getData()[1], [4, 0, 1, 0, 2, 4, 6])


def test_unknown_channel_provenance_cannot_become_original_channel(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(channel_ids=None),))
    assert widget.records_for_indices([0])[0]["channel"] is None
    axis(widget.x_combo, "CHAN")
    assert len(widget.scatter.getData()[0]) == 0
    assert "channel IDs unavailable" in widget.status_label.text()


def test_included_flag_locate_and_multigroup_region_details(qtbot):
    widget = view(qtbot)
    widget.hide_flags.setChecked(False)
    widget.set_blocks((block(), block(ddid=7)))
    captured, focused = [], []
    widget.located.connect(lambda records, total: captured.append((records, total)))
    widget.focused_group.connect(focused.append)
    widget.region_button.setChecked(True)
    widget.roi.setPos((-1, -1))
    widget.roi.setSize((20, 20))
    widget.locate_region()
    records, total = captured[-1]
    assert total == len(records) == 16
    assert sum(record["flag"] for record in records) == 2
    assert {record["ddid"] for record in records} == {6, 7}
    assert not focused


def test_time_axis_identifies_reference_time_scale(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(time_scale="tai"),))
    assert "TAI" in widget.plot.getAxis("bottom").labelText
    assert "TAI" in widget.plot.getPlotItem().titleLabel.text


def test_quick_preview_legend_does_not_mislabel_mixed_fields_or_scans(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(field_ids=np.array([2, 3]), scan_numbers=np.array([9, 10])),))
    label = widget.legend.items[0][1].text
    assert "F 2,3" in label and "S 9,10" in label


def test_translation_reuses_active_legend_items_while_layout_events_are_queued(qtbot):
    widget = view(qtbot)
    widget.set_blocks((block(),))
    label = widget.legend.items[0][1]
    widget.resize(650, 420)
    widget.set_language("zh")
    assert widget.legend.items[0][1] is label
    widget.set_language("en")
    assert widget.legend.items[0][1] is label
    qtbot.wait(1)
    assert "Group 1" in label.item.toPlainText()
