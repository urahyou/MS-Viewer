"""Data contracts shared by the reader, numerical processing and GUI."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class VisibilityBlock:
    times: np.ndarray
    frequencies: np.ndarray
    values: np.ndarray
    flags: np.ndarray
    row_ids: np.ndarray
    total_rows: int
    time_scale: str = "utc"
    unit: str = ""
    channel_ids: np.ndarray | None = None
    uvw: np.ndarray | None = None  # Per row, three Cartesian coordinates in metres.
    field_ids: np.ndarray | None = None
    scan_numbers: np.ndarray | None = None
    antenna1: np.ndarray | None = None
    antenna2: np.ndarray | None = None
    ddid: int | None = None
    correlation_labels: tuple[str, ...] = ()


@dataclass(frozen=True)
class Selection:
    ddid: int
    antenna1: int
    antenna2: int
    field: int | None = None
    scan: int | None = None
    column: str = "DATA"
    time_start: float | None = None
    time_end: float | None = None
    channel_start: int = 0
    channel_end: int | None = None  # exclusive
    max_rows: int = 1024
    max_channels: int = 2048


@dataclass(frozen=True)
class DataDescription:
    ddid: int
    spw: int
    polarization: int
    frequencies: np.ndarray
    correlations: tuple[str, ...]


@dataclass(frozen=True)
class ScanSummary:
    scan: int
    field: int
    start: float | None
    end: float | None
    rows: int
    ddids: tuple[int, ...]
    intents: tuple[str, ...]


@dataclass(frozen=True)
class Metadata:
    path: Path
    rows: int
    antennas: tuple[str, ...]
    fields: tuple[str, ...]
    descriptions: tuple[DataDescription, ...]
    columns: tuple[str, ...]
    partitions: tuple[tuple[int, int, int, int, int], ...]  # ddid, field, scan, ant1, ant2
    time_range: tuple[float, float] | None
    time_scale: str
    telescope: str
    antenna_positions: np.ndarray | None = None  # ITRF Cartesian metres, original IDs
    antenna_position_error: str = ""
    scans: tuple[ScanSummary, ...] = ()
    field_intents: tuple[tuple[str, ...], ...] = ()
    history: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlotData:
    frequency_mhz: np.ndarray
    elapsed_seconds: np.ndarray
    spectrum: np.ndarray
    time_trace: np.ndarray
    image: np.ndarray
    flag_fraction: float
    quantity: str
    unit: str
