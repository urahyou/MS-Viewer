import numpy as np
import pytest
from casacore.tables import table


def test_generated_demo_is_reproducible_multi_shape_ms(tmp_path):
    from msviewer.demo import create_demo
    from msviewer.model import Selection
    from msviewer.reader import inspect_ms, read_visibility

    one = create_demo(tmp_path / "one.ms")
    two = create_demo(tmp_path / "two.ms")
    meta = inspect_ms(one)
    assert meta.telescope == "SIMULATED DEMO"
    assert len(meta.descriptions) == 2
    assert len(meta.antennas) == 3
    a = read_visibility(one, Selection(0, 0, 1))
    b = read_visibility(two, Selection(0, 0, 1))
    assert a.values.shape == (96, 96, 4)
    assert a.flags.any() and not a.flags.all()
    np.testing.assert_array_equal(a.values, b.values)
    with table(str(one / "FIELD"), ack=False) as t:
        assert "Simulated" in t.getcell("NAME", 0)


def test_demo_never_overwrites_existing_directory(tmp_path):
    from msviewer.demo import create_demo

    existing = tmp_path / "mine.ms"
    existing.mkdir()
    (existing / "keep.txt").write_text("keep")
    with pytest.raises(FileExistsError):
        create_demo(existing)
    assert (existing / "keep.txt").read_text() == "keep"
