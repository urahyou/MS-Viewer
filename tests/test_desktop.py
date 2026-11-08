from PyQt6.QtCore import QEvent


class FileOpenEvent:
    # Qt makes the native QFileOpenEvent constructor private; model its public protocol.
    def __init__(self, path):
        self.path = path

    def type(self):
        return QEvent.Type.FileOpen

    def file(self):
        return self.path


def test_finder_open_event_routes_ms_path(qtbot, tmp_path):
    from msviewer.desktop import FileOpenRouter

    seen = []
    path = tmp_path / "my observation.ms"
    router = FileOpenRouter(seen.append)
    assert router.eventFilter(None, FileOpenEvent(str(path)))
    assert seen == [str(path)]


def test_other_events_are_not_swallowed(qtbot):
    from PyQt6.QtCore import QEvent

    from msviewer.desktop import FileOpenRouter

    router = FileOpenRouter(lambda path: None)
    assert not router.eventFilter(None, QEvent(QEvent.Type.User))
