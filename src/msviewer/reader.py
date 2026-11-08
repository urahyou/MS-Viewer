"""Read-only, bounded MeasurementSet v2 access via python-casacore."""

from pathlib import Path

import numpy as np
from astropy import units as u
from casacore.tables import table

from .model import DataDescription, Metadata, Selection, VisibilityBlock

DATA_COLUMNS = ("DATA", "CORRECTED_DATA", "MODEL_DATA", "FLOAT_DATA")
CORRELATIONS = (
    "Undefined",
    "I",
    "Q",
    "U",
    "V",
    "RR",
    "RL",
    "LR",
    "LL",
    "XX",
    "XY",
    "YX",
    "YY",
    "RX",
    "RY",
    "LX",
    "LY",
    "XR",
    "XL",
    "YR",
    "YL",
)
META_CHUNK = 65536
PREVIEW_BYTES = 64 * 1024 * 1024


def _open(path):
    return table(str(path), readonly=True, ack=False)


def _path(path):
    path = Path(path).expanduser().resolve()
    if not (path / "table.dat").is_file():
        raise ValueError(f"Not a Measurement Set directory: {path}")
    return path


def _time_scale(ms):
    keywords = ms.getcolkeywords("TIME")
    if keywords.get("QuantumUnits", ["s"])[0] != "s":
        raise ValueError("Unsupported TIME unit: expected seconds since MJD 0")
    measure = keywords.get("MEASINFO", {})
    if "VarRefCol" in measure:
        raise ValueError("Variable TIME reference frames are not supported")
    scale = measure.get("Ref", "UTC").lower()
    if scale not in ("utc", "tai", "tt", "ut1", "tdb", "tcg", "tcb"):
        raise ValueError(f"Unsupported TIME reference: {scale}")
    return scale


def _descriptions(path, ids):
    results = []
    with (
        _open(f"{path}::DATA_DESCRIPTION") as dd,
        _open(f"{path}::SPECTRAL_WINDOW") as spw,
        _open(f"{path}::POLARIZATION") as pol,
    ):
        for i in sorted(ids):
            if not 0 <= i < dd.nrows():
                raise ValueError(f"Invalid DATA_DESC_ID: {i}")
            s = int(dd.getcell("SPECTRAL_WINDOW_ID", i))
            p = int(dd.getcell("POLARIZATION_ID", i))
            frequencies = np.asarray(spw.getcell("CHAN_FREQ", s), dtype=float)
            types = pol.getcell("CORR_TYPE", p)
            correlations = tuple(
                CORRELATIONS[int(c)] if 0 <= c < len(CORRELATIONS) else f"CORR_{c}" for c in types
            )
            results.append(DataDescription(i, s, p, frequencies, correlations))
    return tuple(results)


def _antenna_positions(ant):
    # Optional plotting metadata must never block otherwise readable visibilities.
    if "POSITION" not in ant.colnames():
        return None, "Antenna POSITION column is missing"
    try:
        keywords = ant.getcolkeywords("POSITION")
    except (RuntimeError, ValueError, TypeError):
        return None, "Invalid antenna position metadata"
    if not isinstance(keywords, dict):
        return None, "Invalid antenna position metadata"
    measure = keywords.get("MEASINFO", {})
    if not isinstance(measure, dict):
        return None, "Invalid antenna position metadata"
    frame = str(measure.get("Ref", "Unknown"))
    if frame.upper() != "ITRF" or "VarRefCol" in measure:
        return None, f"Unsupported antenna position reference: {frame}"
    try:
        units = keywords.get("QuantumUnits", [])
        if len(units) == 1:
            units = list(units) * 3
        if len(units) != 3:
            raise ValueError("Three length units are required")
        factors = np.array([u.Unit(unit).to(u.m) for unit in units])
    except (ValueError, TypeError):
        return None, "Unsupported antenna position units"
    positions = np.full((ant.nrows(), 3), np.nan)
    for row in range(ant.nrows()):
        try:
            if ant.iscelldefined("POSITION", row):
                cell = np.asarray(ant.getcell("POSITION", row), dtype=float)
                if cell.shape == (3,):
                    positions[row] = cell * factors
        except (RuntimeError, ValueError, TypeError):
            continue  # Keep a missing endpoint missing, without inventing its location.
    return positions, ""


def inspect_ms(path) -> Metadata:
    path = _path(path)
    try:
        with _open(path) as ms:
            scale = _time_scale(ms)
            columns = tuple(c for c in DATA_COLUMNS if c in ms.colnames())
            partitions = set()
            time_min, time_max = np.inf, -np.inf
            grouping = ("DATA_DESC_ID", "FIELD_ID", "SCAN_NUMBER", "ANTENNA1", "ANTENNA2")
            for start in range(0, ms.nrows(), META_CHUNK):
                count = min(META_CHUNK, ms.nrows() - start)
                values = np.column_stack([ms.getcol(c, start, count) for c in grouping])
                partitions.update(tuple(map(int, row)) for row in np.unique(values, axis=0))
                times = ms.getcol("TIME", start, count)
                finite = times[np.isfinite(times)]
                if len(finite):
                    time_min = min(time_min, float(finite.min()))
                    time_max = max(time_max, float(finite.max()))
            rows = ms.nrows()
        with _open(f"{path}::ANTENNA") as ant, _open(f"{path}::FIELD") as field:
            antennas = tuple(ant.getcol("NAME"))
            positions, position_error = _antenna_positions(ant)
            fields = tuple(field.getcol("NAME"))
        with _open(f"{path}::OBSERVATION") as obs:
            telescope = str(obs.getcell("TELESCOPE_NAME", 0)) if obs.nrows() else "Unknown"
        descriptions = _descriptions(path, {p[0] for p in partitions})
        return Metadata(
            path,
            rows,
            antennas,
            fields,
            descriptions,
            columns,
            tuple(sorted(partitions)),
            (time_min, time_max) if np.isfinite(time_min) else None,
            scale,
            telescope,
            positions,
            position_error,
        )
    except (RuntimeError, IndexError, KeyError) as exc:
        raise ValueError(f"Cannot inspect MS: {exc}") from exc


def _validate(selection):
    s = selection
    if s.max_rows < 1 or s.max_channels < 1:
        raise ValueError("Preview row/channel limits must be positive")
    for value in (s.time_start, s.time_end):
        if value is not None and not np.isfinite(value):
            raise ValueError("Time bounds must be finite")
    if s.time_start is not None and s.time_end is not None and s.time_start > s.time_end:
        raise ValueError("Start time must not exceed end time")


def read_visibility(path, selection: Selection) -> VisibilityBlock:
    path = _path(path)
    s = selection
    _validate(s)
    try:
        description = _descriptions(path, [s.ddid])[0]
        nchan, ncorr = len(description.frequencies), len(description.correlations)
        end = nchan if s.channel_end is None else s.channel_end
        if not 0 <= s.channel_start < end <= nchan:
            raise ValueError(f"Channel bounds must satisfy 0 <= start < end <= {nchan}")
        step = max(1, int(np.ceil((end - s.channel_start) / s.max_channels)))
        channels = np.arange(s.channel_start, end, step)
        conditions = [
            f"DATA_DESC_ID == {int(s.ddid)}",
            f"ANTENNA1 == {int(s.antenna1)}",
            f"ANTENNA2 == {int(s.antenna2)}",
        ]
        for column, value in (
            ("FIELD_ID", s.field),
            ("SCAN_NUMBER", s.scan),
            ("TIME >=", s.time_start),
            ("TIME <=", s.time_end),
        ):
            if value is not None:
                conditions.append(
                    f"{column} {float(value)!r}"
                    if column.startswith("TIME")
                    else f"{column} == {int(value)}"
                )
        with _open(path) as ms:
            if s.column not in DATA_COLUMNS or s.column not in ms.colnames():
                raise ValueError(f"Data column unavailable: {s.column}")
            scale = _time_scale(ms)
            units = ms.getcolkeywords(s.column).get("QuantumUnits", [""])
            with ms.query(" && ".join(conditions), sortlist="TIME") as selected:
                total = selected.nrows()
                if not total:
                    raise ValueError("No rows match this selection")
                cap = min(s.max_rows, max(1, PREVIEW_BYTES // (len(channels) * ncorr * 32)))
                indices = np.linspace(0, total - 1, min(total, cap), dtype=np.int64)
                with selected.selectrows(indices) as preview:
                    # getcolslice uses an INCLUSIVE end, unlike Python slices.
                    blc, trc, inc = [s.channel_start, 0], [end - 1, ncorr - 1], [step, 1]
                    values = preview.getcolslice(s.column, blc, trc, inc)
                    flags = preview.getcolslice("FLAG", blc, trc, inc)
                    flags |= preview.getcol("FLAG_ROW")[:, None, None]
                    if values.shape != (len(indices), len(channels), ncorr):
                        raise ValueError(
                            "Visibility shape does not match SPW/polarization metadata"
                        )
                    return VisibilityBlock(
                        preview.getcol("TIME"),
                        description.frequencies[channels],
                        values,
                        flags,
                        np.asarray(preview.rownumbers(ms)),
                        total,
                        scale,
                        str(units[0]) if len(units) else "",
                    )
    except (RuntimeError, IndexError, KeyError) as exc:
        raise ValueError(f"Cannot read MS selection: {exc}") from exc
