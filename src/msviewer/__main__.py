"""Desktop entry point; --inspect also works without a display server."""

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only radio astronomy Measurement Set viewer")
    parser.add_argument("path", nargs="?", type=Path, help="Measurement Set directory")
    parser.add_argument(
        "--demo", action="store_true", help="create/open a deterministic simulated MS"
    )
    parser.add_argument("--inspect", action="store_true", help="print metadata as JSON without GUI")
    args = parser.parse_args(argv)
    path = args.path
    try:
        if args.demo:
            from .demo import create_demo

            path = path or Path("data/simulated.ms")
            if not path.exists():
                create_demo(path)
        if args.inspect:
            if path is None:
                parser.error("--inspect requires an MS path or --demo")
            from .reader import inspect_ms

            meta = inspect_ms(path)
            print(
                json.dumps(
                    {
                        "path": str(meta.path),
                        "rows": meta.rows,
                        "telescope": meta.telescope,
                        "antennas": meta.antennas,
                        "fields": meta.fields,
                        "columns": meta.columns,
                        "time_range_mjd_seconds": meta.time_range,
                        "time_scale": meta.time_scale,
                        "ddids": [
                            {
                                "ddid": d.ddid,
                                "spw": d.spw,
                                "polarization": d.polarization,
                                "channels": len(d.frequencies),
                                "correlations": d.correlations,
                            }
                            for d in meta.descriptions
                        ],
                    },
                    indent=2,
                )
            )
            return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    from PyQt6.QtWidgets import QApplication

    from .window import MainWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("MS Viewer")
    app.setOrganizationName("RadioAstronomy")
    window = MainWindow()
    from .desktop import FileOpenRouter

    router = FileOpenRouter(window.open_ms, app)
    app.installEventFilter(router)
    window.show()
    if path is not None:
        window.open_ms(path)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
