"""Scientific coordinate conventions and optional MS position metadata."""

import numpy as np
import pytest
from astropy import units as u
from astropy.coordinates import EarthLocation
from casacore.tables import table


def test_ecef_to_enu_has_correct_east_north_up_and_origin():
    from msviewer.geometry import project_antennas

    base = np.array([6378137.0, 0, 0])
    xyz = base + np.array([[0, 0, 0], [0, 100, 0], [0, 0, 200], [5, 0, 0]])
    enu, reference = project_antennas(xyz)
    assert reference == 0
    np.testing.assert_allclose(enu, [[0, 0, 0], [100, 0, 0], [0, 200, 0], [0, 0, 5]], atol=1e-8)


def test_geodetic_basis_at_non_equatorial_location_preserves_3d_distance():
    from msviewer.geometry import project_antennas

    location = EarthLocation.from_geodetic(90 * u.deg, 45 * u.deg, 100 * u.m)
    base = np.array([v.to_value(u.m) for v in location.geocentric])
    s = np.sqrt(0.5)
    east, north, up = np.array([-1, 0, 0]), np.array([0, -s, s]), np.array([0, s, s])
    enu, _ = project_antennas(np.array([base, base + 3 * east + 4 * north + 12 * up]))
    np.testing.assert_allclose(enu[1], [3, 4, 12], atol=1e-7)
    assert np.linalg.norm(enu[1]) == pytest.approx(13)


def test_missing_coordinates_keep_original_ids_and_use_first_valid_reference():
    from msviewer.geometry import project_antennas

    enu, reference = project_antennas(np.array([[0, 0, 0], [6378137, 0, 0], [np.nan, 0, 0]]))
    assert reference == 1
    assert np.isnan(enu[[0, 2]]).all()
    np.testing.assert_equal(enu[1], [0, 0, 0])


def test_all_missing_positions_have_no_fabricated_map():
    from msviewer.geometry import project_antennas

    with pytest.raises(ValueError, match="No usable"):
        project_antennas(np.zeros((2, 3)))


def test_reader_loads_optional_positions_in_metres_without_writing(tiny_ms):
    from msviewer.reader import inspect_ms

    positions = np.array([[6378.137, 0, 0], [6378.137, 0.1, 0]])
    with table(str(tiny_ms / "ANTENNA"), readonly=False, ack=False) as t:
        t.putcol("POSITION", positions)
        t.putcolkeyword("POSITION", "QuantumUnits", ["km", "km", "km"])
    before = {
        str(p): p.read_bytes() for p in tiny_ms.rglob("*") if p.is_file() and p.name != "table.lock"
    }
    meta = inspect_ms(tiny_ms)
    assert hasattr(meta, "antenna_positions"), "Antenna positions are not loaded"
    np.testing.assert_allclose(meta.antenna_positions, positions * 1000)
    assert not meta.antenna_position_error
    after = {
        str(p): p.read_bytes() for p in tiny_ms.rglob("*") if p.is_file() and p.name != "table.lock"
    }
    assert before == after


@pytest.mark.parametrize("change", ["missing", "frame", "units"])
def test_unavailable_position_metadata_keeps_visibilities_readable(tiny_ms, change):
    from msviewer.reader import inspect_ms

    with table(str(tiny_ms / "ANTENNA"), readonly=False, ack=False) as t:
        if change == "missing":
            t.removecols("POSITION")
        elif change == "frame":
            t.putcolkeyword("POSITION", "MEASINFO", {"type": "position", "Ref": "MARS"})
        else:
            t.putcolkeyword("POSITION", "QuantumUnits", ["s", "s", "s"])
    meta = inspect_ms(tiny_ms)
    assert meta.rows == 6 and meta.columns == ("DATA",)
    assert hasattr(meta, "antenna_positions"), "Optional geometry metadata missing"
    assert meta.antenna_positions is None
    assert meta.antenna_position_error


@pytest.mark.parametrize("malformed", ["malformed", 7])
def test_malformed_optional_position_measure_does_not_break_ms_inspection(tiny_ms, malformed):
    from msviewer.reader import inspect_ms, read_visibility
    from msviewer.model import Selection

    with table(str(tiny_ms / "ANTENNA"), readonly=False, ack=False) as t:
        t.removecolkeyword("POSITION", "MEASINFO")
        t.putcolkeyword("POSITION", "MEASINFO", malformed)
    meta = inspect_ms(tiny_ms)
    assert meta.rows == 6
    assert meta.antenna_positions is None
    assert "metadata" in meta.antenna_position_error.lower()
    assert read_visibility(tiny_ms, Selection(0, 0, 1)).values.shape == (3, 3, 2)
