#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
PYTHON_BIN="${MSVIEWER_BUILD_PYTHON:-$PWD/.venv/bin/python}"
"$PYTHON_BIN" -m msviewer.datasets --all
"$PYTHON_BIN" -m msviewer --demo --inspect > /dev/null
"$PYTHON_BIN" packaging/macos/prepare_assets.py
"$PYTHON_BIN" -m PyInstaller --noconfirm packaging/macos/MSViewer.spec
codesign --verify --deep --strict 'dist/MS Viewer.app'
STAGING="$(mktemp -d "$PWD/build/dmg.XXXXXX")"
trap 'rm -rf "$STAGING"' EXIT
ditto 'dist/MS Viewer.app' "$STAGING/MS Viewer.app"
ln -s /Applications "$STAGING/Applications"
cp docs/macos-install.md "$STAGING/安装说明.txt"
hdiutil create -volname 'MS Viewer' -srcfolder "$STAGING" -ov -format UDZO 'dist/MS-Viewer-0.1.0-macOS-arm64.dmg'
(cd dist && shasum -a 256 'MS-Viewer-0.1.0-macOS-arm64.dmg' > SHA256SUMS.txt)
