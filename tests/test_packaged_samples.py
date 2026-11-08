"""Staged casacore tables must retain their scientific metadata after copying."""

import runpy
from pathlib import Path

from casacore.tables import table


def test_staged_sample_retains_all_subtable_rows(tmp_path):
    from msviewer.demo import create_demo

    demo_ms = create_demo(tmp_path / "original.ms")
    script = Path(__file__).resolve().parents[1] / "packaging/macos/prepare_assets.py"
    stage_sample = runpy.run_path(str(script))["stage_sample"]
    destination = tmp_path / "sample.ms"
    stage_sample(demo_ms, destination)
    for name in ("", "ANTENNA", "FIELD", "DATA_DESCRIPTION", "SPECTRAL_WINDOW", "POLARIZATION"):
        with (
            table(str(demo_ms / name), ack=False) as source,
            table(str(destination / name), ack=False) as staged,
        ):
            assert staged.nrows() == source.nrows(), name
