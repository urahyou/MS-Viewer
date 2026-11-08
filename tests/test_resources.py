import sys
from pathlib import Path

import pytest


def frozen_assets(tmp_path, monkeypatch):
    from msviewer import resources

    bundle = tmp_path / "bundle"
    root = bundle / "msviewer_resources" / "data" / "simulated.ms"
    root.mkdir(parents=True)
    (root / "table.dat").write_bytes(b"example")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(resources, "user_data_directory", lambda: tmp_path / "user")
    return root


def test_source_resource_lookup_ignores_working_directory(tmp_path, monkeypatch):
    from msviewer.resources import sample_source, tutorial_path

    monkeypatch.chdir(tmp_path)
    assert (sample_source("simulated.ms") / "table.dat").is_file()
    assert tutorial_path().is_file()


def test_frozen_sample_copied_to_writable_user_location(tmp_path, monkeypatch):
    from msviewer.resources import prepare_sample

    source = frozen_assets(tmp_path, monkeypatch)
    result = prepare_sample("simulated.ms")
    assert result != source
    assert result.is_relative_to(tmp_path / "user")
    assert (result / "table.dat").read_bytes() == b"example"
    assert (source / "table.dat").read_bytes() == b"example"


def test_existing_user_sample_is_not_overwritten(tmp_path, monkeypatch):
    from msviewer.resources import prepare_sample

    frozen_assets(tmp_path, monkeypatch)
    first = prepare_sample("simulated.ms")
    (first / "table.dat").write_bytes(b"user copy")
    assert prepare_sample("simulated.ms") == first
    assert (first / "table.dat").read_bytes() == b"user copy"


@pytest.mark.parametrize("name", ["../secret", "/tmp/secret", "missing.ms"])
def test_unknown_sample_paths_rejected(name):
    from msviewer.resources import prepare_sample

    with pytest.raises(ValueError):
        prepare_sample(name)


def test_samples_menu_opens_without_source_working_directory(qtbot, tmp_path, monkeypatch):
    from msviewer.window import MainWindow

    monkeypatch.chdir(tmp_path)
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    window.open_sample("simulated.ms")
    qtbot.waitUntil(lambda: window.block is not None, timeout=15000)
    assert window.metadata.telescope == "SIMULATED DEMO"


def test_pdf_help_action_opens_local_file(qtbot, monkeypatch):
    from PyQt6.QtGui import QDesktopServices

    from msviewer.window import MainWindow

    seen = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: seen.append(url) or True)
    window = MainWindow()
    qtbot.addWidget(window)
    window.tutorial_action.trigger()
    assert len(seen) == 1 and Path(seen[0].toLocalFile()).is_file()


def test_simultaneous_sample_preparation_accepts_existing_nonempty_directory(tmp_path, monkeypatch):
    import errno
    import shutil

    from msviewer.resources import prepare_sample

    frozen_assets(tmp_path, monkeypatch)
    original = Path.rename

    def concurrent_copy(path, target):
        if path.name == "simulated.ms" and path.parent.name.startswith(".prepare-"):
            shutil.copytree(path, target)
            raise OSError(errno.ENOTEMPTY, "Directory not empty")
        return original(path, target)

    monkeypatch.setattr(Path, "rename", concurrent_copy)
    result = prepare_sample("simulated.ms")
    assert (result / "table.dat").read_bytes() == b"example"
