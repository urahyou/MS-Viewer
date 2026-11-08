from dataclasses import replace

from msviewer.reader import inspect_ms


def test_overview_does_not_infer_roles_or_calibration_from_names_or_columns(qtbot, tiny_ms):
    from msviewer.overview import OverviewView

    view = OverviewView()
    qtbot.addWidget(view)
    view.set_metadata(inspect_ms(tiny_ms))
    assert view.fields_table.item(0, 1).text() == "Calibrator"
    assert view.fields_table.item(0, 2).text() == "Unknown"
    assert "unknown" in view.calibration_label.text().lower()
    assert "6" in view.summary_label.text()


def test_intent_roles_and_real_ddid_mapping_are_readable(qtbot, tiny_ms):
    from msviewer.overview import OverviewView

    meta = replace(
        inspect_ms(tiny_ms),
        field_intents=(("CALIBRATE_PHASE#ON_SOURCE",), ("OBSERVE_TARGET#ON_SOURCE",)),
    )
    view = OverviewView()
    qtbot.addWidget(view)
    view.set_metadata(meta)
    assert view.fields_table.item(0, 2).text() == "Calibrator"
    assert view.fields_table.item(1, 2).text() == "Science target"
    assert view.spw_table.item(0, 0).text() == "0"
    assert view.spw_table.item(0, 1).text() == "1"
    assert view.spw_table.item(0, 3).text() == "100.000000–102.000000"


def test_overview_translates_without_mutating_scientific_metadata(qtbot, tiny_ms):
    from msviewer.overview import OverviewView

    view = OverviewView()
    qtbot.addWidget(view)
    meta = inspect_ms(tiny_ms)
    view.set_metadata(meta)
    view.set_language("zh")
    assert "校准状态" in view.calibration_label.text()
    assert view.fields_table.item(0, 2).text() == "未知"
    assert view.fields_table.item(0, 1).text() == "Calibrator"
    assert view.metadata is meta


def test_unknown_scan_time_does_not_break_optional_overview(qtbot, tiny_ms):
    from msviewer.model import ScanSummary
    from msviewer.overview import OverviewView

    meta = replace(inspect_ms(tiny_ms), scans=(ScanSummary(9, 0, None, None, 1, (0,), ()),))
    view = OverviewView()
    qtbot.addWidget(view)
    view.set_metadata(meta)
    assert view.scans_table.item(0, 2).text() == "Unknown"
