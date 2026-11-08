# MS Viewer v0.1

Build a Python 3.11+ / PyQt6 desktop viewer for CASA MeasurementSet v2.
Read-only access; no flag writing. Show MAIN metadata, antennas, fields, DDID → SPW/polarization.
Select field, scan, oriented baseline, DDID, correlation, data column, time and channel range.
Show amplitude/phase/real/imaginary frequency spectrum, time trace, channel-by-row waterfall,
flag fraction, actual channel frequencies and readable observation time. Explicitly label waterfall
row/channel axes so irregular coordinates are never presented as regular physical pixels.
Read visibility data in bounded row/channel slices; cap preview rows and sample across selected rows.
Run opening/reading in workers; reject stale results; defer close until active jobs end.
Report missing columns, empty selections, invalid paths without crashing or destroying prior results.
Download at least two small public MS test datasets with source URLs, SHA256, sizes and provenance;
include a reproducible deterministic synthetic MS for tests/demo, clearly labeled simulated.
Use TDD: observe failing tests before implementation, retain RED/GREEN evidence.
