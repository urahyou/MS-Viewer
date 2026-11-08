"""Terrestrial antenna geometry, separate from visibility/uv coordinates."""

import numpy as np
from astropy import units as u
from astropy.coordinates import EarthLocation


def project_antennas(positions):
    """ITRF metres → local ENU metres, retaining original antenna row IDs.

    The first finite, nonzero terrestrial position is the reference. Rotation
    follows ESA Navipedia's ECEF→ENU basis with WGS84 geodetic latitude.
    Unavailable positions remain NaN; lengths should use all three components.
    """
    xyz = np.asarray(positions, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("Invalid antenna position shape")
    valid = np.isfinite(xyz).all(axis=1) & (np.linalg.norm(xyz, axis=1) > 1e6)
    if not valid.any():
        raise ValueError("No usable geocentric antenna positions")
    reference = int(np.flatnonzero(valid)[0])
    origin = xyz[reference]
    location = EarthLocation.from_geocentric(*origin, unit=u.m)
    lon, lat = location.lon.radian, location.lat.radian
    slon, clon, slat, clat = np.sin(lon), np.cos(lon), np.sin(lat), np.cos(lat)
    rotation = np.array(
        [
            [-slon, clon, 0],
            [-slat * clon, -slat * slon, clat],
            [clat * clon, clat * slon, slat],
        ]
    )
    enu = np.full(xyz.shape, np.nan)
    enu[valid] = (xyz[valid] - origin) @ rotation.T
    return enu, reference
