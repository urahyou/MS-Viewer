# License and third-party notices

MS Viewer is distributed under GPL-3.0-only, compatible with the open-source PyQt6 distribution.
Full project source and build scripts: https://github.com/urahyou/MS-Viewer

The macOS application bundles Python and third-party libraries. Their copyright and license
notices are retained in Contents/Resources/msviewer_resources/licenses, together with a
machine-readable dependency inventory. This does not replace the individual licenses.

- PyQt6: GNU GPL v3 (Riverbank Computing). https://www.riverbankcomputing.com/software/pyqt/intro
- Qt 6: licenses and exception details in the bundled Qt/PyQt6-Qt6 package notices.
- python-casacore / casacore: bundled package and Conda license notices.
- NumPy, Astropy, PyQtGraph, Python and native library notices are included in the inventory.
- PyInstaller has its bootloader distribution exception; see its bundled notice.

The two public MS examples come from the casacore regression test repository at the pinned
commit in src/msviewer/sample_catalog.json. They are not presented as unprocessed science data.
The deterministic synthetic sample and tutorial were created for this project.

This release is ad-hoc signed, not Developer ID signed or Apple-notarized.
