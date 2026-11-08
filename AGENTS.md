# MS Viewer development

- Python/PyQt6 desktop application. Keep the MeasurementSet reader read-only.
- Use TDD for behavioral changes. Test with actual casacore tables and pytest-qt.
- Run `QT_QPA_PLATFORM=offscreen python -m pytest -q` and `python -m ruff check src tests scripts packaging`.
- Stable scientific identifiers belong in combo itemData; translations must not change numerical behavior.
- Preserve selection/request generation checks and wait for active reads before closing.
- Never write within a signed macOS app bundle. Prepare bundled MS examples in the user data directory.
- Keep source resources independent of the working directory; see resources.py.
- Do not commit environments, MS observation directories, build outputs or temporary logs.
- macOS build: packaging/macos/build.sh; see docs/macos-install.md.
