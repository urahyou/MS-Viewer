"""Create offline bundle assets and preserve dependency license notices."""

import importlib.metadata
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "build/macos-assets/msviewer_resources"
DEST.mkdir(parents=True, exist_ok=True)
for name in ("simulated.ms", "mssel_test_small.ms", "mssel_test_small_multifield_spw.ms"):
    source = ROOT / "data" / name
    if not (source / "table.dat").is_file():
        raise SystemExit(
            f"Missing {name}; run python -m msviewer.datasets --all and python -m msviewer --demo --inspect"
        )
    shutil.copytree(source, DEST / "data" / name, dirs_exist_ok=True)
    for lock in (DEST / "data" / name).rglob("table.lock"):
        lock.unlink()  # Recreated in the writable per-user copy, not in the signed bundle.
shutil.copyfile(
    ROOT / "output/pdf/MS查看器与MeasurementSet_天文学家视角入门.pdf", DEST / "guide.pdf"
)
shutil.copyfile(ROOT / "LICENSE", DEST / "LICENSE")
shutil.copyfile(ROOT / "THIRD_PARTY_NOTICES.md", DEST / "THIRD_PARTY_NOTICES.md")
licenses = DEST / "licenses"
licenses.mkdir(exist_ok=True)
inventory = []
for dist in importlib.metadata.distributions():
    name = dist.metadata["Name"]
    inventory.append(
        {
            "name": name,
            "version": dist.version,
            "license": dist.metadata.get("License-Expression") or dist.metadata.get("License", ""),
        }
    )
    for file in dist.files or []:
        if (
            "license" in str(file).lower()
            or Path(file).name.lower().startswith(("copying", "copyright"))
        ) and not str(file).endswith((".py", ".pyc")):
            source = Path(dist.locate_file(file))
            if source.is_file() and source.stat().st_size < 5_000_000:
                target = licenses / "python" / name / str(file).replace("../", "").lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
for record in sorted((Path(sys.prefix) / "conda-meta").glob("*.json")):
    info = json.loads(record.read_text())
    inventory.append(
        {k: info.get(k) for k in ("name", "version", "build", "license", "url", "sha256")}
    )
    cache = Path(info.get("link", {}).get("source", "/nonexistent")) / "info/licenses"
    if cache.is_dir():
        shutil.copytree(cache, licenses / "conda" / info["name"], dirs_exist_ok=True)
(licenses / "inventory.json").write_text(json.dumps(inventory, indent=2, default=str))
print(DEST)
