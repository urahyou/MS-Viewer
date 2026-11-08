"""Downloaded archives must be reproducible and cannot escape the sample directory."""

import hashlib
import io
import tarfile
from pathlib import Path

import pytest


def archive_at(path, members):
    with tarfile.open(path, "w:gz") as tar:
        for name, content, link in members:
            info = tarfile.TarInfo(name)
            if link:
                info.type = tarfile.SYMTYPE
                info.linkname = link
                tar.addfile(info)
            else:
                data = content.encode()
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))


def test_extract_valid_ms(tmp_path):
    from msviewer.datasets import extract_ms

    archive = tmp_path / "sample.tgz"
    archive_at(archive, [("test.ms/table.dat", "data", None)])
    result = extract_ms(archive, tmp_path / "samples", "test.ms")
    assert (result / "table.dat").read_text() == "data"


@pytest.mark.parametrize(
    "name,link",
    [
        ("../escape", None),
        ("/tmp/escape", None),
        ("test.ms/../../escape", None),
        ("test.ms/link", "/tmp"),
        ("other.ms/table.dat", None),
    ],
)
def test_reject_unsafe_members(tmp_path, name, link):
    from msviewer.datasets import extract_ms

    archive = tmp_path / "bad.tgz"
    archive_at(archive, [(name, "bad", link)])
    destination = tmp_path / "samples"
    with pytest.raises(ValueError):
        extract_ms(archive, destination, "test.ms")
    assert not (destination / "test.ms").exists()
    assert not (tmp_path / "escape").exists()


def test_checksum_failure_never_extracts(tmp_path):
    from msviewer.datasets import Sample, download_sample

    archives = tmp_path / "archives"
    archives.mkdir()
    (archives / "test.ms.tgz").write_bytes(b"corrupt")
    sample = Sample("test.ms", "https://example.invalid/test.tgz", "0" * 64, 7, "", "test")
    with pytest.raises(ValueError, match="checksum"):
        download_sample(sample, tmp_path)
    assert not (tmp_path / "test.ms").exists()


def test_cached_archive_loads_without_network(tmp_path):
    from msviewer.datasets import Sample, download_sample

    archives = tmp_path / "archives"
    archives.mkdir()
    archive = archives / "test.ms.tgz"
    archive_at(archive, [("test.ms/table.dat", "ok", None)])
    data = archive.read_bytes()
    sample = Sample(
        "test.ms",
        "https://example.invalid/test.tgz",
        hashlib.sha256(data).hexdigest(),
        len(data),
        "",
        "test",
    )
    result = download_sample(sample, tmp_path)
    assert (result / "table.dat").read_text() == "ok"


def test_catalog_has_two_pinned_public_samples():
    from msviewer.datasets import load_samples

    samples = load_samples()
    assert len(samples) == 2
    assert all(s.size < 10_000_000 and len(s.sha256) == 64 for s in samples)
    assert all("/a1399b6b99907bd14021920a089403a93c10aba1/" in s.url for s in samples)


@pytest.mark.parametrize("name", ["mssel_test_small.ms", "mssel_test_small_multifield_spw.ms"])
def test_public_ms_can_be_read(name):
    from msviewer.model import Selection
    from msviewer.reader import inspect_ms, read_visibility

    root = Path(__file__).resolve().parents[1] / "data"
    if not (root / name).exists():
        pytest.skip("Run python -m msviewer.datasets --all for public-data integration tests")
    meta = inspect_ms(root / name)
    assert meta.rows > 0 and meta.columns
    ddid, field, scan, a1, a2 = meta.partitions[0]
    block = read_visibility(
        meta.path,
        Selection(ddid, a1, a2, field, scan, column=meta.columns[0], max_rows=8, max_channels=32),
    )
    assert 0 < block.values.shape[0] <= 8
    assert 0 < block.values.shape[1] <= 32
