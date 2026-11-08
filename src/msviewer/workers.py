"""One-shot jobs; all table handles are created and closed inside the worker."""

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot


class JobSignals(QObject):
    finished = pyqtSignal(int, str, object, str)


class Job(QRunnable):
    def __init__(self, token, kind, function):
        super().__init__()
        self.token, self.kind, self.function = token, kind, function
        self.signals = JobSignals()

    @pyqtSlot()
    def run(self):
        try:
            result, error = self.function(), ""
        except Exception as exc:  # noqa: BLE001 - marshal every worker failure to the GUI
            result, error = None, str(exc) or type(exc).__name__
        self.signals.finished.emit(self.token, self.kind, result, error)
