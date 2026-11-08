import json

import pytest
from PyQt6.QtCore import Qt

from msviewer.reader import inspect_ms


def test_controls_build_grouped_spec_with_original_ids_and_absolute_time(qtbot, tiny_ms):
    from msviewer.query_controls import QueryControls

    controls = QueryControls()
    qtbot.addWidget(controls)
    meta = inspect_ms(tiny_ms)
    controls.set_metadata(meta)
    controls.time_start.setText("10")
    controls.uv_min.setText("20")
    spec = controls.build_spec()
    assert spec.ddids == (0,)
    assert spec.baselines == ((0, 1),)
    assert spec.fields == ()  # Empty checks explicitly mean all, not an arbitrary first field.
    assert spec.time_start == meta.time_range[0] + 10
    assert spec.uv_min == 20
    assert json.loads(controls.parameter_json())["baselines"] == [[0, 1]]


def test_multiple_baselines_and_correlations_are_values_not_translated_text(qtbot, tiny_ms):
    from msviewer.query_controls import QueryControls

    controls = QueryControls()
    qtbot.addWidget(controls)
    controls.set_metadata(inspect_ms(tiny_ms))
    for i in range(controls.baselines.count()):
        controls.baselines.item(i).setCheckState(Qt.CheckState.Checked)
    controls.correlations.item(0).setCheckState(Qt.CheckState.Checked)
    before = controls.build_spec()
    controls.set_language("zh")
    assert controls.build_spec() == before
    assert before.baselines == ((0, 1), (1, 0))
    assert before.correlations == ("XX",)


@pytest.mark.parametrize(
    "field,value", [("time_start", "nan"), ("uv_min", "-1"), ("time_end", "nonsense")]
)
def test_invalid_ranges_are_actionable(qtbot, tiny_ms, field, value):
    from msviewer.query_controls import QueryControls

    controls = QueryControls()
    qtbot.addWidget(controls)
    controls.set_metadata(inspect_ms(tiny_ms))
    getattr(controls, field).setText(value)
    with pytest.raises(ValueError):
        controls.build_spec()


def test_dataset_replacement_resets_ids_and_supports_snapshot_restore(qtbot, tiny_ms):
    from msviewer.query_controls import QueryControls

    controls = QueryControls()
    qtbot.addWidget(controls)
    meta = inspect_ms(tiny_ms)
    controls.set_metadata(meta)
    controls.channel_start.setValue(1)
    state = controls.snapshot()
    controls.set_metadata(meta)
    assert controls.channel_start.value() == 0
    controls.restore(state)
    assert controls.channel_start.value() == 1
