# Build with: .venv/bin/python -m PyInstaller --noconfirm packaging/macos/MSViewer.spec
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files

root=Path(SPECPATH).resolve().parents[1]
assets=root/'build/macos-assets'
casalibs=[(str(path),'.') for path in (Path(sys.prefix)/'lib').glob('libcasa*.dylib')]
a=Analysis(
    [str(root/'packaging/macos/launcher.py')],
    pathex=[str(root/'src')],
    hookspath=[str(root/'packaging/macos/hooks')],
    binaries=casalibs,
    datas=collect_data_files('msviewer')+[(str(assets/'msviewer_resources'),'msviewer_resources'),
        (str(root/'packaging/macos/openssl.cnf'),'.')],
    runtime_hooks=[str(root/'packaging/macos/hooks/runtime_openssl.py')],
    hiddenimports=['casacore.tables','casacore.quanta','PyQt6.QtSvg'],
    excludes=['PyQt5','PySide2','PySide6','tkinter','matplotlib','pytest','IPython','jupyter'],
    noarchive=False,
)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='MS Viewer',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,
        target_arch='arm64',codesign_identity=None,entitlements_file=None)
collect=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='MS Viewer')
app=BUNDLE(collect,name='MS Viewer.app',icon=str(root/'packaging/macos/MSViewer.icns'),
    bundle_identifier='io.github.urahyou.msviewer',
    info_plist={
      'CFBundleDisplayName':'MS Viewer', 'CFBundleShortVersionString':'0.2.0',
      'CFBundleVersion':'4', 'NSHighResolutionCapable':True,
      'NSHumanReadableCopyright':'GPL-3.0-only. Source: github.com/urahyou/MS-Viewer',
      'CFBundleDocumentTypes':[{'CFBundleTypeName':'Measurement Set','CFBundleTypeExtensions':['ms'],
          'CFBundleTypeRole':'Viewer','LSTypeIsPackage':True}],
      'NSDesktopFolderUsageDescription':'读取你选择的 Measurement Set 数据。',
      'NSDocumentsFolderUsageDescription':'读取你选择的 Measurement Set 数据。',
      'NSDownloadsFolderUsageDescription':'读取你选择的 Measurement Set 数据。',
    })
