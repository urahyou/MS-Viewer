"""macOS/Finder integration and persistent diagnostics for the windowed app."""

import logging
import sys

from PyQt6.QtCore import QEvent, QObject

logger = logging.getLogger(__name__)


class FileOpenRouter(QObject):
    def __init__(self, opener, parent=None):
        super().__init__(parent)
        self.opener = opener

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.FileOpen:
            path = event.file() or event.url().toLocalFile()
            if path:
                self.opener(path)
                return True
        return False


def run():
    from .__main__ import main
    from .resources import user_data_directory

    logs = user_data_directory() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=logs / "msviewer.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    def exception_hook(kind, value, traceback):
        logger.critical("Unhandled application error", exc_info=(kind, value, traceback))
        sys.__excepthook__(kind, value, traceback)

    sys.excepthook = exception_hook
    try:
        return main()
    except Exception:
        logger.exception("Application startup failed")
        raise
