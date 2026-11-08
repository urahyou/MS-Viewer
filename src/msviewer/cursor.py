"""Non-interactive linked overlays; all lookups stay within the loaded preview."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QEvent, QObject, Qt


class LinkedCursor(QObject):
    def __init__(self, graphics, spectrum, time, waterfall, image, changed):
        super().__init__(graphics)
        self.spectrum, self.time, self.waterfall = spectrum, time, waterfall
        self.image, self.changed = image, changed
        self.data = None
        self.position = None
        self.spectrum_line = self._line(spectrum, 90)
        self.time_line = self._line(time, 90)
        self.channel_line = self._line(waterfall, 90)
        self.row_line = self._line(waterfall, 0)
        self.lines = (self.spectrum_line, self.time_line, self.channel_line, self.row_line)
        self.spectrum_marker = self._marker(spectrum, "#63dfcf")
        self.time_marker = self._marker(time, "#e6b86a")
        graphics.viewport().installEventFilter(self)
        graphics.scene().sigMouseMoved.connect(self.move)

    @staticmethod
    def _line(plot, angle):
        line = pg.InfiniteLine(
            angle=angle, movable=False, pen=pg.mkPen("#ffffff", width=1, style=Qt.PenStyle.DashLine)
        )
        line.setZValue(30)
        plot.addItem(line, ignoreBounds=True)
        line.hide()
        return line

    @staticmethod
    def _marker(plot, colour):
        marker = pg.ScatterPlotItem(size=10, pen=pg.mkPen("#ffffff"), brush=pg.mkBrush(colour))
        marker.setZValue(31)
        plot.addItem(marker, ignoreBounds=True)
        marker.hide()
        return marker

    def set_data(self, data):
        self.data = data
        self.clear()

    def clear(self):
        self.position = None
        for item in (*self.lines, self.spectrum_marker, self.time_marker):
            item.hide()
        self.changed(None)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Leave:
            self.clear()
        return False

    def move(self, position):
        if self.data is None:
            return
        row, channel = self.position or (None, None)
        if self.waterfall.getViewBox().sceneBoundingRect().contains(position):
            point = self.image.mapFromScene(position)
            row, channel = int(np.floor(point.y())), int(np.floor(point.x()))
            if not (
                0 <= row < self.data.image.shape[0] and 0 <= channel < self.data.image.shape[1]
            ):
                self.clear()
                return
        elif self.spectrum.getViewBox().sceneBoundingRect().contains(position):
            x = self.spectrum.getViewBox().mapSceneToView(position).x()
            channel = int(np.argmin(np.abs(self.data.frequency_mhz - x)))
        elif self.time.getViewBox().sceneBoundingRect().contains(position):
            x = self.time.getViewBox().mapSceneToView(position).x()
            row = int(np.argmin(np.abs(self.data.elapsed_seconds - x)))
        else:
            self.clear()
            return
        if self.position == (row, channel):
            return
        self.position = (row, channel)
        if channel is not None:
            frequency = self.data.frequency_mhz[channel]
            self._show(self.spectrum_line, frequency)
            self._show(self.channel_line, channel + 0.5)
            self._point(self.spectrum_marker, frequency, self.data.spectrum[channel])
        if row is not None:
            elapsed = self.data.elapsed_seconds[row]
            self._show(self.time_line, elapsed)
            self._show(self.row_line, row + 0.5)
            self._point(self.time_marker, elapsed, self.data.time_trace[row])
        self.changed(self.position)

    @staticmethod
    def _show(line, value):
        line.setValue(float(value))
        line.show()

    @staticmethod
    def _point(marker, x, y):
        if np.isfinite(y):
            marker.setData([x], [y])
            marker.show()
        else:
            marker.hide()
