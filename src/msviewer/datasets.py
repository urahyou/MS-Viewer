"""Download pinned, checksummed casacore public test fixtures."""

import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Sample:
    name: str
    url: str
    sha256: str
    size: int
    source: str
    provenance: str


def load_samples() -> tuple[Sample, ...]:
    records = json.loads(files("msviewer").joinpath("sample_catalog.json").read_text())
    return tuple(
        Sample(**{k: v for k, v in record.items() if k != "archive"}) for record in records
    )


def extract_ms(archive, destination, expected_root) -> Path:
    """Only regular files/directories inside the declared MS root are accepted."""
    root = PurePosixPath(expected_root)
    if len(root.parts) != 1 or root.name in ("", ".", "..") or not root.name.endswith(".ms"):
        raise ValueError("Invalid sample root")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / expected_root
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 256 * 1024 * 1024:
            raise ValueError("Sample archive exceeds extraction limits")
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != expected_root
                or "\\" in member.name
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError(f"Unsafe archive member: {member.name}")
        with tempfile.TemporaryDirectory(prefix=".msviewer-", dir=destination) as temporary:
            tar.extractall(temporary, members=members, filter="data")
            extracted = Path(temporary) / expected_root
            if not (extracted / "table.dat").is_file():
                raise ValueError("Archive has no MS table.dat")
            extracted.rename(target)
    return target


def download_sample(sample: Sample, destination) -> Path:
    destination = Path(destination).expanduser().resolve()
    root = PurePosixPath(sample.name)
    if len(root.parts) != 1 or not sample.name.endswith(".ms"):
        raise ValueError("Invalid sample name")
    archives = destination / "archives"
    archives.mkdir(parents=True, exist_ok=True)
    archive = archives / f"{sample.name}.tgz"
    if not archive.exists():
        if not sample.url.startswith("https://") or not 0 < sample.size <= 10_000_000:
            raise ValueError("Only small HTTPS samples are supported")
        request = Request(sample.url, headers={"User-Agent": "radio-msviewer/0.1"})
        with tempfile.NamedTemporaryFile(dir=archives, delete=False) as temp:
            temporary = Path(temp.name)
            try:
                with urlopen(request, timeout=30) as response:
                    received = 0
                    while chunk := response.read(65536):
                        received += len(chunk)
                        if received > sample.size:
                            raise ValueError("Downloaded sample exceeds declared size")
                        temp.write(chunk)
                temp.close()
                _verify(temporary, sample)
                temporary.replace(archive)
            finally:
                temporary.unlink(missing_ok=True)
    _verify(archive, sample)
    target = destination / sample.name
    if not target.exists():
        extract_ms(archive, destination, sample.name)
    if target.is_symlink() or not (target / "table.dat").is_file():
        raise ValueError(f"Existing sample directory is invalid: {target}")
    return target


def _verify(path, sample):
    if path.stat().st_size != sample.size:
        raise ValueError(f"Sample size/checksum mismatch: {path}")
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if digest != sample.sha256:
        raise ValueError(f"Sample checksum mismatch: {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="download both public test datasets")
    parser.add_argument("--destination", type=Path, default=Path("data"))
    args = parser.parse_args(argv)
    if not args.all:
        parser.print_help()
        return 0
    for sample in load_samples():
        path = download_sample(sample, args.destination)
        print(f"{path}  sha256={sample.sha256}")
        shutil.copyfile(
            files("msviewer").joinpath("sample_catalog.json"), args.destination / "sources.json"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
