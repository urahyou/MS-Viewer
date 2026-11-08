"""Locate source/bundled assets and keep mutable MS lock files outside the app bundle."""

import errno
import shutil
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QStandardPaths

SAMPLE_NAMES = ("simulated.ms", "mssel_test_small.ms", "mssel_test_small_multifield_spw.ms")
GUIDE_NAME = "MS查看器与MeasurementSet_天文学家视角入门.pdf"


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "msviewer_resources"
    return Path(__file__).resolve().parents[2]


def user_data_directory() -> Path:
    return (
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation))
        / "MS Viewer"
    )


def sample_source(name: str) -> Path:
    if name not in SAMPLE_NAMES:
        raise ValueError(f"Unknown sample: {name}")
    return resource_root() / "data" / name


def tutorial_path() -> Path:
    if getattr(sys, "frozen", False):
        return resource_root() / "guide.pdf"
    return resource_root() / "output" / "pdf" / GUIDE_NAME


def prepare_sample(name: str) -> Path:
    source = sample_source(name)
    if not (source / "table.dat").is_file():
        raise ValueError(f"Sample is not installed: {name}")
    if not getattr(sys, "frozen", False):
        return source
    parent = user_data_directory() / "samples-v1"
    target = parent / name
    if target.is_symlink():
        raise ValueError(f"Invalid sample location: {target}")
    if target.exists():
        if not (target / "table.dat").is_file():
            raise ValueError(f"Invalid sample location: {target}")
        return target
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prepare-", dir=parent) as temporary:
        copy = Path(temporary) / name
        shutil.copytree(source, copy)
        try:
            copy.rename(target)
        except OSError as exc:
            # Another instance may finish preparing the same sample first.
            if (
                exc.errno not in (errno.EEXIST, errno.ENOTEMPTY)
                or target.is_symlink()
                or not (target / "table.dat").is_file()
            ):
                raise
    return target
