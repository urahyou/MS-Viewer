"""Observation dashboard: intentions are evidence, names/columns are not calibration proof."""

import numpy as np
import pyqtgraph as pg
from astropy.time import Time
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .workbench_text import tr


class OverviewView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.metadata = None
        self.language = "en"
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        layout = QVBoxLayout(body)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summary")
        self.calibration_label = QLabel()
        self.calibration_label.setWordWrap(True)
        self.simulation_label = QLabel()
        self.simulation_label.setWordWrap(True)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.calibration_label)
        layout.addWidget(self.simulation_label)
        self.fields_table = self._table(4)
        self.spw_table = self._table(5)
        self.scans_table = self._table(6)
        self.timeline = pg.PlotWidget()
        self.timeline.setMinimumHeight(160)
        self.timeline.setMaximumHeight(240)
        self.scan_note = QLabel()
        self.scan_note.setWordWrap(True)
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMaximumHeight(120)
        self._groups = []
        for title, widget in (
            ("Fields", self.fields_table),
            ("Spectral setup", self.spw_table),
            ("Scan timeline", self.timeline),
            ("Scans", self.scans_table),
            ("History", self.history),
        ):
            box = QGroupBox()
            sub = QVBoxLayout(box)
            sub.addWidget(widget)
            if widget is self.timeline:
                sub.addWidget(self.scan_note)
            self._groups.append((box, title))
            layout.addWidget(box)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.set_language("en")

    @staticmethod
    def _table(columns):
        table = QTableWidget(0, columns)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(100)
        table.setMaximumHeight(220)
        return table

    def _text(self, source, **values):
        return tr(source, self.language, **values)

    def set_metadata(self, metadata):
        self.metadata = metadata
        self._populate()

    def set_language(self, language):
        self.language = language
        for box, title in self._groups:
            box.setTitle(self._text(title))
        for table, headers in (
            (self.fields_table, ["ID", "Name", "Role", "Intents"]),
            (self.spw_table, ["DDID", "SPW", "Channels", "Frequency range (MHz)", "Correlations"]),
            (self.scans_table, ["Scan", "Field", "Start", "End", "Rows", "Intents"]),
        ):
            table.setHorizontalHeaderLabels([self._text(h) for h in headers])
        self.timeline.setLabel(
            "bottom", self._text("Sample-time span (seconds since first MS sample)")
        )
        self._populate()

    @staticmethod
    def _rows(table, rows):
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(value)))

    def _populate(self):
        meta = self.metadata
        self.calibration_label.setText(
            self._text(
                "Calibration status: unknown — verify delivery reports and processing history."
            )
        )
        if meta is None:
            self.summary_label.setText(self._text("No dataset loaded"))
            return
        self.summary_label.setText(
            self._text(
                "{rows:,} rows · {antennas} antennas · {fields} fields · {ddids} DDIDs",
                rows=meta.rows,
                antennas=len(meta.antennas),
                fields=len(meta.fields),
                ddids=len(meta.descriptions),
            )
        )
        simulated = "SIMULATED" in meta.telescope.upper()
        self.simulation_label.setText(
            self._text("Simulated data — for demonstration, not telescope observations.")
            if simulated
            else ""
        )
        field_rows = []
        for i, name in enumerate(meta.fields):
            intents = meta.field_intents[i] if i < len(meta.field_intents) else ()
            target = any("OBSERVE_TARGET" in x.upper() for x in intents)
            calibrator = any("CALIBRATE_" in x.upper() for x in intents)
            role = (
                "Target and calibrator"
                if target and calibrator
                else "Science target"
                if target
                else "Calibrator"
                if calibrator
                else "Unknown"
            )
            field_rows.append(
                (i, name, self._text(role), "; ".join(intents) or self._text("Unknown"))
            )
        self._rows(self.fields_table, field_rows)
        spws = []
        for d in meta.descriptions:
            freq = d.frequencies[np.isfinite(d.frequencies)] / 1e6
            extent = f"{freq.min():.6f}–{freq.max():.6f}" if len(freq) else self._text("Unknown")
            spws.append((d.ddid, d.spw, len(d.frequencies), extent, ", ".join(d.correlations)))
        self._rows(self.spw_table, spws)
        self.timeline.clear()
        scans = meta.scans[:1000]
        origin = meta.time_range[0] if meta.time_range else 0
        rows = []
        for scan in scans:
            valid_time = all(v is not None and np.isfinite(v) for v in (scan.start, scan.end))
            start = (
                Time(scan.start / 86400, format="mjd", scale=meta.time_scale).isot
                if valid_time
                else self._text("Unknown")
            )
            end = (
                Time(scan.end / 86400, format="mjd", scale=meta.time_scale).isot
                if valid_time
                else self._text("Unknown")
            )
            rows.append(
                (
                    scan.scan,
                    scan.field,
                    start,
                    end,
                    scan.rows,
                    "; ".join(scan.intents) or self._text("Unknown"),
                )
            )
            if not valid_time:
                continue
            self.timeline.plot(
                [scan.start - origin, scan.end - origin],
                [scan.field, scan.field],
                pen=pg.mkPen(pg.intColor(scan.field), width=5),
                symbol="o" if scan.start == scan.end else None,
            )
        self._rows(self.scans_table, rows)
        self.timeline.getPlotItem().getAxis("left").setTicks(
            [[(i, f"{i}: {name}") for i, name in enumerate(meta.fields)]]
        )
        self.scan_note.setText(
            self._text(
                "Showing {shown} of {total} scan/field groups; times are sample timestamps, not exposure edges.",
                shown=len(scans),
                total=len(meta.scans),
            )
        )
        self.history.setPlainText(
            "\n".join(meta.history)
            or self._text(
                "No recorded history; absence of history does not establish calibration state."
            )
        )
