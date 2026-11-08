"""Read-only, bounded MeasurementSet v2 access via python-casacore."""

from pathlib import Path

import numpy as np
from astropy import units as u
from casacore.tables import table

from .model import DataDescription, Metadata, ScanSummary, Selection, VisibilityBlock

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
HISTORY_LIMIT = 128
HISTORY_MESSAGE_LIMIT = 2048


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


def _state_intents(path):
    """Optional STATE records describe intent; field names never imply intent."""
    try:
        with _open(f"{path}::STATE") as state:
            if "OBS_MODE" not in state.colnames():
                return {}
            return {
                row: tuple(
                    sorted(
                        {
                            s.strip()
                            for s in str(state.getcell("OBS_MODE", row)).split(",")
                            if s.strip()
                        }
                    )
                )
                for row in range(state.nrows())
            }
    except (RuntimeError, ValueError, IndexError, KeyError):
        return {}


def _history(path):
    try:
        with _open(f"{path}::HISTORY") as history:
            if "MESSAGE" not in history.colnames():
                return ()
            # Retain the most recent bounded tail, with bounded individual strings.
            start = max(0, history.nrows() - HISTORY_LIMIT)
            return tuple(
                str(history.getcell("MESSAGE", row))[:HISTORY_MESSAGE_LIMIT]
                for row in range(start, history.nrows())
            )
    except (RuntimeError, ValueError, IndexError, KeyError):
        return ()


def inspect_ms(path) -> Metadata:
    path = _path(path)
    try:
        state_intents = _state_intents(path)
        scans = {}
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
                states = (
                    ms.getcol("STATE_ID", start, count)
                    if "STATE_ID" in ms.colnames()
                    else np.full(count, -1)
                )
                for values_row, time, state in zip(values, times, states):
                    ddid, field_id, scan = map(int, values_row[:3])
                    summary = scans.setdefault((scan, field_id), [np.inf, -np.inf, 0, set(), set()])
                    if np.isfinite(time):
                        summary[0] = min(summary[0], float(time))
                        summary[1] = max(summary[1], float(time))
                    summary[2] += 1
                    summary[3].add(ddid)
                    summary[4].update(state_intents.get(int(state), ()))
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
        summaries = tuple(
            ScanSummary(
                scan,
                field_id,
                lo if np.isfinite(lo) else None,
                hi if np.isfinite(hi) else None,
                count,
                tuple(sorted(ddids)),
                tuple(sorted(intents)),
            )
            for (scan, field_id), (lo, hi, count, ddids, intents) in sorted(scans.items())
        )
        field_intents = tuple(
            tuple(
                sorted(
                    {
                        intent
                        for scan in summaries
                        if scan.field == field_id
                        for intent in scan.intents
                    }
                )
            )
            for field_id in range(len(fields))
        )
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
            summaries,
            field_intents,
            _history(path),
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


def _uvw(preview):
    """Read optional UVW without turning invalid/missing coordinates into zero."""
    if "UVW" not in preview.colnames():
        return None
    try:
        units = preview.getcolkeywords("UVW").get("QuantumUnits", [])
        if len(units) == 1:
            units = list(units) * 3
        if len(units) != 3:
            return None
        factors = np.asarray([u.Unit(unit).to(u.m) for unit in units])
        uvw = np.asarray(preview.getcol("UVW"), dtype=float)
        if uvw.shape != (preview.nrows(), 3) or not np.isfinite(uvw).all():
            return None
        return uvw * factors
    except (RuntimeError, ValueError, TypeError, KeyError):
        return None


def _channel_indices(description, selection):
    nchan = len(description.frequencies)
    end = nchan if selection.channel_end is None else selection.channel_end
    if not 0 <= selection.channel_start < end <= nchan:
        raise ValueError(f"Channel bounds must satisfy 0 <= start < end <= {nchan}")
    step = max(1, int(np.ceil((end - selection.channel_start) / selection.max_channels)))
    return np.arange(selection.channel_start, end, step, dtype=np.int64), end, step


def _column_sources(ms, column):
    residuals = {
        "DATA-MODEL_DATA": ("DATA", "MODEL_DATA"),
        "CORRECTED_DATA-MODEL_DATA": ("CORRECTED_DATA", "MODEL_DATA"),
    }
    sources = residuals.get(column, (column,))
    if any(c not in DATA_COLUMNS or c not in ms.colnames() for c in sources):
        raise ValueError(f"Data column unavailable: {column}")
    units = [ms.getcolkeywords(c).get("QuantumUnits", []) for c in sources]
    unit = str(units[0][0]) if len(units[0]) else ""
    if len(sources) == 2 and (not unit or any(list(v) != list(units[0]) for v in units)):
        raise ValueError("Residual source units must be known and match")
    return sources, unit


def _read_preview(ms, selected, description, selection, indices, total, correlations=None):
    channels, end, step = _channel_indices(description, selection)
    ncorr = len(description.correlations)
    sources, unit = _column_sources(ms, selection.column)
    with selected.selectrows(indices) as preview:
        expected = (len(description.frequencies), ncorr)
        # Check the original shapes before slicing, especially before subtraction.
        for column in (*sources, "FLAG"):
            shapes = preview.getcolshapestring(column)
            if isinstance(shapes, str):
                shapes = [shapes]
            for shape in shapes:
                parsed = tuple(int(n.strip()) for n in shape.strip("[]").split(",") if n.strip())
                if parsed != expected:
                    raise ValueError("Visibility shape does not match SPW/polarization metadata")
        blc, trc, inc = [int(channels[0]), 0], [int(end - 1), ncorr - 1], [step, 1]
        values = preview.getcolslice(sources[0], blc, trc, inc)
        if len(sources) == 2:
            values = values - preview.getcolslice(sources[1], blc, trc, inc)
        flags = preview.getcolslice("FLAG", blc, trc, inc)
        flags |= preview.getcol("FLAG_ROW")[:, None, None]
        if values.shape != (len(indices), len(channels), ncorr):
            raise ValueError("Visibility shape does not match SPW/polarization metadata")
        labels = description.correlations
        if correlations is not None:
            values, flags = values[:, :, correlations], flags[:, :, correlations]
            labels = tuple(labels[i] for i in correlations)
        return VisibilityBlock(
            preview.getcol("TIME"),
            description.frequencies[channels],
            values,
            flags,
            np.asarray(preview.rownumbers(ms)),
            total,
            _time_scale(ms),
            unit,
            channels,
            _uvw(preview),
            preview.getcol("FIELD_ID"),
            preview.getcol("SCAN_NUMBER"),
            preview.getcol("ANTENNA1"),
            preview.getcol("ANTENNA2"),
            description.ddid,
            labels,
        )


def read_visibility(path, selection: Selection) -> VisibilityBlock:
    path = _path(path)
    s = selection
    _validate(s)
    try:
        description = _descriptions(path, [s.ddid])[0]
        ncorr = len(description.correlations)
        channels, _, _ = _channel_indices(description, s)
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
            sources, _ = _column_sources(ms, s.column)
            with ms.query(" && ".join(conditions), sortlist="TIME") as selected:
                total = selected.nrows()
                if not total:
                    raise ValueError("No rows match this selection")
                bytes_per_value = 64 if len(sources) > 1 else 32
                cap = min(
                    s.max_rows, max(1, PREVIEW_BYTES // (len(channels) * ncorr * bytes_per_value))
                )
                indices = np.linspace(0, total - 1, min(total, cap), dtype=np.int64)
                return _read_preview(ms, selected, description, s, indices, total)
    except (RuntimeError, IndexError, KeyError) as exc:
        raise ValueError(f"Cannot read MS selection: {exc}") from exc
