"""Deterministic synthetic visibilities; these are NOT telescope observations."""

from pathlib import Path

import numpy as np
from casacore.tables import default_ms, makearrcoldesc, maketabdesc, table


def create_demo(path) -> Path:
    path = Path(path).expanduser().resolve()
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261107)
    desc = maketabdesc(makearrcoldesc("DATA", 0j, ndim=2, valuetype="complex"))
    nt = 96
    baselines = [(0, 1), (0, 2), (1, 2)]
    configs = [(96, [9, 10, 11, 12]), (48, [9, 12])]
    with default_ms(str(path), desc) as ms:
        ms.addrows(nt * len(baselines) * len(configs))
        ms.putcolkeyword("DATA", "QuantumUnits", ["Jy"])
        row = 0
        for ddid, (nchan, corr) in enumerate(configs):
            x = np.linspace(-1, 1, nchan)
            bandpass = 2 + 1.4 * np.exp(-4 * x**2)
            for ti in range(nt):
                for a1, a2 in baselines:
                    amp = bandpass[:, None] * (1 + 0.15 * np.sin(ti / 12))
                    phase = ti / 13 + x[:, None] * (a2 - a1) * 3
                    vis = np.broadcast_to(amp * np.exp(1j * phase), (nchan, len(corr))).copy()
                    vis += 0.08 * (rng.normal(size=vis.shape) + 1j * rng.normal(size=vis.shape))
                    vis[:, 1:-1] *= 0.12
                    vis[nchan // 3, :] += 4 * (1 + np.sin(ti / 8))  # simulated narrowband RFI
                    flags = rng.random(vis.shape) < 0.025
                    flags[nchan // 2, :] = True
                    for col, value in {
                        "DATA_DESC_ID": ddid,
                        "ANTENNA1": a1,
                        "ANTENNA2": a2,
                        "FIELD_ID": int(ti >= nt // 2),
                        "SCAN_NUMBER": ti // 24 + 1,
                        "TIME": 60600 * 86400.0 + ti * 10.0,
                        "TIME_CENTROID": 60600 * 86400.0 + ti * 10.0,
                        "INTERVAL": 10.0,
                        "EXPOSURE": 10.0,
                        "FLAG_ROW": ti == 20,
                        "DATA": vis.astype(np.complex64),
                        "FLAG": flags,
                        "UVW": np.array([100 * np.cos(ti / 20), 100 * np.sin(ti / 20), 20.0]),
                        "WEIGHT": np.ones(len(corr), np.float32),
                        "SIGMA": np.ones(len(corr), np.float32),
                    }.items():
                        ms.putcell(col, row, value)
                    row += 1

    def sub(name):
        return table(f"{path}::{name}", readonly=False, ack=False)

    with sub("ANTENNA") as t:
        t.addrows(3)
        t.putcol("NAME", ["DEMO-01", "DEMO-02", "DEMO-03"])
        t.putcol(
            "POSITION",
            np.array(
                [
                    [3828763.0, 442449.0, 5064923.0],
                    [3828863.0, 442449.0, 5064923.0],
                    [3828763.0, 442549.0, 5064923.0],
                ]
            ),
        )
    with sub("FIELD") as t:
        t.addrows(2)
        t.putcol("NAME", ["Simulated calibrator", "Simulated target"])
        for row in range(2):
            for col in ("PHASE_DIR", "DELAY_DIR", "REFERENCE_DIR"):
                t.putcell(col, row, np.array([[0.5 + row / 10, 0.8]]))
    with sub("POLARIZATION") as t:
        t.addrows(2)
        for i, (_, corr) in enumerate(configs):
            t.putcell("NUM_CORR", i, len(corr))
            t.putcell("CORR_TYPE", i, corr)
    with sub("SPECTRAL_WINDOW") as t:
        t.addrows(2)
        for ddid, (nchan, _) in enumerate(configs):
            spw = 1 - ddid
            frequencies = np.linspace(1.35e9 + ddid * 0.1e9, 1.40e9 + ddid * 0.1e9, nchan)
            t.putcell("NUM_CHAN", spw, nchan)
            t.putcell("CHAN_FREQ", spw, frequencies)
            t.putcell("CHAN_WIDTH", spw, np.full(nchan, frequencies[1] - frequencies[0]))
            t.putcell("REF_FREQUENCY", spw, frequencies.mean())
    with sub("DATA_DESCRIPTION") as t:
        t.addrows(2)
        t.putcol("SPECTRAL_WINDOW_ID", [1, 0])
        t.putcol("POLARIZATION_ID", [0, 1])
    with sub("OBSERVATION") as t:
        t.addrows(1)
        t.putcell("TELESCOPE_NAME", 0, "SIMULATED DEMO")
    return path
