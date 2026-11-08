"""Antenna layout view driven by the current MS and original baseline IDs."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .geometry import project_antennas
from .i18n import error_text, text

FIRST, SECOND, MUTED = "#63dfcf", "#e6b86a", "#91a5ba"


class AntennaMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = "en"
        self.metadata = self.enu = self.reference_id = None
        self.error = ""
        self.baseline = None
        self.selected_ids = ()
        self.labels = {}
        layout = QVBoxLayout(self)
        self.view = pg.PlotWidget()
        self.plot = self.view.getPlotItem()
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        for axis in ("bottom", "left"):
            self.plot.getAxis(axis).enableAutoSIPrefix(False)
        self.antennas = pg.ScatterPlotItem(size=9, brush=MUTED, pen=None)
        self.baseline_line = self.plot.plot(pen=pg.mkPen(SECOND, width=2))
        self.highlight = pg.ScatterPlotItem(size=17, pen=pg.mkPen("#ffffff", width=2))
        self.plot.addItem(self.antennas)
        self.plot.addItem(self.highlight, ignoreBounds=True)
        self.baseline_line.setZValue(10)
        self.highlight.setZValue(11)
        # The selection must not alter the geometry viewport's auto-range.
        self.plot.removeItem(self.baseline_line)
        self.plot.addItem(self.baseline_line, ignoreBounds=True)
        layout.addWidget(self.view, 1)
        self.baseline_label = QLabel()
        self.baseline_label.setTextFormat(Qt.TextFormat.PlainText)
        self.baseline_label.setWordWrap(True)
        self.baseline_label.setFixedHeight(2 * self.baseline_label.fontMetrics().lineSpacing() + 8)
        layout.addWidget(self.baseline_label)
        self.note_label = QLabel()
        self.note_label.setTextFormat(Qt.TextFormat.PlainText)
        self.note_label.setWordWrap(True)
        layout.addWidget(self.note_label)
        self.set_language("en")

    def _text(self, source, **values):
        return text(source, self.language, **values)

    def set_language(self, language):
        self.language = language
        self.plot.setTitle(self._text("Antenna positions"))
        self.plot.setLabel("bottom", self._text("East"), units="m")
        self.plot.setLabel("left", self._text("North"), units="m")
        self._refresh_text()

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.enu = self.reference_id = None
        self.error = metadata.antenna_position_error
        self.baseline = None
        self.selected_ids = ()
        self.highlight.clear()
        self.baseline_line.clear()
        self.antennas.clear()
        for label in self.labels.values():
            self.plot.removeItem(label)
        self.labels.clear()
        if metadata.antenna_positions is not None and not self.error:
            try:
                if len(metadata.antenna_positions) != len(metadata.antennas):
                    raise ValueError("Invalid antenna position shape")
                self.enu, self.reference_id = project_antennas(metadata.antenna_positions)
            except ValueError as exc:
                self.error = str(exc)
        if self.enu is not None:
            ids = np.flatnonzero(np.isfinite(self.enu).all(axis=1))
            self.antennas.setData(x=self.enu[ids, 0], y=self.enu[ids, 1], data=ids)
            for i in ids:
                label = pg.TextItem(f"{metadata.antennas[i]} ({i})", color=MUTED, anchor=(0, 1))
                label.setPos(*self.enu[i, :2])
                self.plot.addItem(label, ignoreBounds=True)
                self.labels[int(i)] = label
            self.plot.enableAutoRange(x=True, y=True)
            self.plot.autoRange(padding=0.15)
        self._refresh_text()

    def set_baseline(self, baseline):
        self.baseline = baseline
        self.selected_ids = ()
        self.highlight.clear()
        self.baseline_line.clear()
        for label in self.labels.values():
            label.setColor(MUTED)
        if self.enu is not None and baseline is not None:
            a, b = baseline
            if not (0 <= a < len(self.enu) and 0 <= b < len(self.enu)):
                self.baseline = None
            else:
                ids = tuple(i for i in dict.fromkeys((a, b)) if i in self.labels)
                self.selected_ids = ids
                self.highlight.setData(
                    spots=[
                        {
                            "pos": self.enu[i, :2],
                            "data": i,
                            "brush": pg.mkBrush(FIRST if i == a else SECOND),
                        }
                        for i in ids
                    ]
                )
                for i in ids:
                    self.labels[i].setColor(FIRST if i == a else SECOND)
                if a in self.labels and b in self.labels:
                    self.baseline_line.setData(self.enu[[a, b], 0], self.enu[[a, b], 1])
        self._refresh_text()

    def _refresh_text(self):
        if self.metadata is None:
            message = self._text("Open an MS to see antenna positions.")
            self.note_label.setText("")
        elif self.enu is None:
            message = self._text(
                "Antenna positions unavailable: {reason}",
                reason=error_text(
                    self.error or "No usable geocentric antenna positions", self.language
                ),
            )
            self.note_label.setText(self._text("Visibility data can still be inspected."))
        else:
            ref = self.reference_id
            self.note_label.setText(
                self._text(
                    "Local east/north projection · origin: {name} ({id}) · {missing} positions unavailable. Colours follow ANTENNA1 → ANTENNA2; length uses all three spatial dimensions.",
                    name=self.metadata.antennas[ref],
                    id=ref,
                    missing=len(self.enu) - len(self.labels),
                )
            )
            if self.baseline is None:
                message = self._text(
                    "Choose a baseline in the left panel to highlight its antennas."
                )
            else:
                a, b = self.baseline
                name = f"{self.metadata.antennas[a]} ({a}) → {self.metadata.antennas[b]} ({b})"
                if a not in self.labels or b not in self.labels:
                    message = self._text(
                        "{baseline} · endpoint position unavailable", baseline=name
                    )
                else:
                    length = float(np.linalg.norm(self.enu[b] - self.enu[a]))
                    source = (
                        "{baseline} · Auto-correlation · 3D baseline length: {length:.3f} m"
                        if a == b
                        else "{baseline} · 3D baseline length: {length:.3f} m"
                    )
                    message = self._text(source, baseline=name, length=length)
        self.baseline_label.setText(message)
        self.baseline_label.setToolTip(message)
