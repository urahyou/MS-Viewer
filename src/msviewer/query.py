"""Read-only, bounded structured queries over independent scientific groups.

Selections use original MS IDs and absolute MS seconds. Baselines are oriented:
(0, 1) does not also select (1, 0), and no conjugation or averaging is applied.
"""

from dataclasses import asdict, dataclass

import numpy as np

from .model import Metadata, Selection, VisibilityBlock
from .reader import (
    META_CHUNK,
    PREVIEW_BYTES,
    _channel_indices,
    _column_sources,
    _open,
    _path,
    _read_preview,
    _uvw,
    _validate,
    inspect_ms,
)

MAX_QUERY_GROUPS = 128


@dataclass(frozen=True)
class SelectionSpec:
    ddids: tuple[int, ...] = ()
    fields: tuple[int, ...] = ()
    scans: tuple[int, ...] = ()
    baselines: tuple[tuple[int, int], ...] = ()
    correlations: tuple[str, ...] = ()
    column: str = "DATA"
    time_start: float | None = None
    time_end: float | None = None
    channel_start: int = 0
    channel_end: int | None = None
    max_rows: int = 1024
    max_channels: int = 2048
    uv_min: float | None = None
    uv_max: float | None = None

    def to_dict(self):
        """Return JSON-ready values, including nested oriented baseline pairs."""

        def normalize(value):
            if isinstance(value, np.generic):
                return value.item()
            if isinstance(value, (list, tuple)):
                return [normalize(item) for item in value]
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            return value

        return normalize(asdict(self))


def _validate_spec(spec):
    _validate(spec)
    for value in (spec.max_rows, spec.max_channels, spec.channel_start, spec.channel_end):
        if value is not None and (
            not isinstance(value, (int, np.integer)) or isinstance(value, bool)
        ):
            raise ValueError("Row/channel limits and bounds must be integers")
    for values in (spec.ddids, spec.fields, spec.scans):
        if any(
            not isinstance(v, (int, np.integer)) or isinstance(v, bool) or v < 0 for v in values
        ):
            raise ValueError("Scientific IDs must be nonnegative integers")
    for pair in spec.baselines:
        if len(pair) != 2 or any(
            not isinstance(v, (int, np.integer)) or isinstance(v, bool) or v < 0 for v in pair
        ):
            raise ValueError("Baselines require pairs of nonnegative antenna IDs")
    for value in (spec.uv_min, spec.uv_max):
        if value is not None and (not np.isfinite(value) or value < 0):
            raise ValueError("UV bounds must be finite nonnegative metres")
    if spec.uv_min is not None and spec.uv_max is not None and spec.uv_min > spec.uv_max:
        raise ValueError("Minimum UV distance must not exceed maximum")


def _condition(group, spec):
    names = ("DATA_DESC_ID", "FIELD_ID", "SCAN_NUMBER", "ANTENNA1", "ANTENNA2")
    conditions = [f"{name} == {int(value)}" for name, value in zip(names, group)]
    for op, value in ((">=", spec.time_start), ("<=", spec.time_end)):
        if value is not None:
            conditions.append(f"TIME {op} {float(value)!r}")
    return " && ".join(conditions)


def _matching_count(selected, spec):
    """Count matches in bounded scalar/UVW chunks without reading visibilities."""
    if spec.uv_min is None and spec.uv_max is None:
        return selected.nrows()
    count = 0
    chunk = max(1, min(META_CHUNK, PREVIEW_BYTES // 32))
    for start in range(0, selected.nrows(), chunk):
        with selected.selectrows(np.arange(start, min(selected.nrows(), start + chunk))) as part:
            count += int(_uv_mask(part, spec).sum())
    return count


def _uv_mask(part, spec):
    uvw = _uvw(part)
    if uvw is None:
        raise ValueError("UV selection requires available, finite UVW coordinates in length units")
    distance = np.hypot(uvw[:, 0], uvw[:, 1])
    mask = np.ones(part.nrows(), dtype=bool)
    if spec.uv_min is not None:
        mask &= distance >= spec.uv_min
    if spec.uv_max is not None:
        mask &= distance <= spec.uv_max
    return mask


def _preview_indices(selected, spec, total, cap):
    targets = np.linspace(0, total - 1, min(total, cap), dtype=np.int64)
    if spec.uv_min is None and spec.uv_max is None:
        return targets
    # Keep only the bounded preview indices, never a full selection-sized index array.
    result = []
    matched = 0
    chunk = max(1, min(META_CHUNK, PREVIEW_BYTES // 32))
    for start in range(0, selected.nrows(), chunk):
        with selected.selectrows(np.arange(start, min(selected.nrows(), start + chunk))) as part:
            indices = np.flatnonzero(_uv_mask(part, spec))
        lo, hi = np.searchsorted(targets, [matched, matched + len(indices)])
        result.extend(start + indices[targets[lo:hi] - matched])
        matched += len(indices)
    return np.asarray(result, dtype=np.int64)


def _allocations(groups, row_budget):
    """Reserve one sample per group, then distribute remaining capacity globally."""
    totals = np.asarray([g[3] for g in groups], dtype=np.int64)
    costs = np.asarray([g[4] for g in groups], dtype=np.int64)
    fixed = sum(g[5] for g in groups)
    allocations = np.ones(len(groups), dtype=np.int64)
    memory = PREVIEW_BYTES - fixed - int(costs.sum())
    rows = row_budget - len(groups)
    if memory < 0 or rows < 0:
        raise ValueError(
            "Preview row/memory budget cannot retain every group; narrow the selection or increase the row limit"
        )
    remaining = totals - 1
    if remaining.sum():
        fraction = min(1.0, rows / int(remaining.sum()), memory / int(remaining @ costs))
        extra = np.floor(remaining * fraction).astype(np.int64)
        allocations += extra
        rows -= int(extra.sum())
        memory -= int(extra @ costs)
        # Resolve floor remainders deterministically while respecting both budgets.
        for index in np.argsort(costs, kind="stable"):
            extra_count = min(
                int(totals[index] - allocations[index]), rows, memory // int(costs[index])
            )
            allocations[index] += extra_count
            rows -= extra_count
            memory -= extra_count * int(costs[index])
    return allocations


def read_query(
    path, spec: SelectionSpec, metadata: Metadata | None = None
) -> tuple[VisibilityBlock, ...]:
    """Read separate DDID/field/scan/oriented-baseline blocks under global budgets.

    Correlations preserve their source order. Groups without any requested
    correlation are nonmatching. Time and UV endpoints are inclusive; channel end
    is exclusive. The row budget applies across all groups and never drops groups.
    """
    _validate_spec(spec)
    path = _path(path)
    metadata = inspect_ms(path) if metadata is None else metadata
    if metadata.path.resolve() != path:
        raise ValueError("Metadata belongs to a different MeasurementSet")
    descriptions = {d.ddid: d for d in metadata.descriptions}
    groups = []
    try:
        with _open(path) as ms:
            _column_sources(ms, spec.column)
            for group in metadata.partitions:
                ddid, field, scan, ant1, ant2 = group
                if (
                    (spec.ddids and ddid not in spec.ddids)
                    or (spec.fields and field not in spec.fields)
                    or (spec.scans and scan not in spec.scans)
                    or (spec.baselines and (ant1, ant2) not in spec.baselines)
                ):
                    continue
                description = descriptions[ddid]
                correlations = [
                    i
                    for i, label in enumerate(description.correlations)
                    if not spec.correlations or label in spec.correlations
                ]
                if not correlations:
                    continue
                channels, _, _ = _channel_indices(description, spec)
                condition = _condition(group, spec)
                with ms.query(condition, sortlist="TIME") as selected:
                    total = _matching_count(selected, spec)
                if not total:
                    continue
                # Include full source correlations: slicing/subtraction precedes
                # correlation projection. 64 bytes covers complex128 temporaries.
                cost = len(channels) * len(description.correlations) * 64 + 128
                groups.append((group, condition, correlations, total, cost, len(channels) * 16))
                if len(groups) > MAX_QUERY_GROUPS:
                    raise ValueError(
                        f"Selection exceeds maximum group limit ({MAX_QUERY_GROUPS}); narrow the selection"
                    )
            if not groups:
                raise ValueError("No rows/correlations match this selection")
            allocations = _allocations(groups, spec.max_rows)
            blocks = []
            for (group, condition, correlations, total, _, _), cap in zip(groups, allocations):
                ddid, field, scan, ant1, ant2 = group
                selection = Selection(
                    ddid,
                    ant1,
                    ant2,
                    field,
                    scan,
                    spec.column,
                    spec.time_start,
                    spec.time_end,
                    spec.channel_start,
                    spec.channel_end,
                    int(cap),
                    spec.max_channels,
                )
                with ms.query(condition, sortlist="TIME") as selected:
                    indices = _preview_indices(selected, spec, total, int(cap))
                    blocks.append(
                        _read_preview(
                            ms,
                            selected,
                            descriptions[ddid],
                            selection,
                            indices,
                            total,
                            correlations,
                        )
                    )
            return tuple(blocks)
    except (RuntimeError, IndexError, KeyError) as exc:
        raise ValueError(f"Cannot read MS query: {exc}") from exc
