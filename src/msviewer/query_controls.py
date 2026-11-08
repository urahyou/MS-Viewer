"""Structured multi-group selection, independent of translated labels and plot focus."""

import json

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .query import SelectionSpec
from .workbench_text import tr


class QueryControls(QWidget):
    requested = pyqtSignal()
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.metadata = None
        self.language = "en"
        layout = QVBoxLayout(self)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.form = QFormLayout()
        self._labels = []
        self.ddids, self.fields, self.scans, self.baselines, self.correlations = [
            QListWidget() for _ in range(5)
        ]
        for title, widget in (
            ("DDID / SPW", self.ddids),
            ("Fields", self.fields),
            ("Scans", self.scans),
            ("Baselines", self.baselines),
            ("Correlations", self.correlations),
        ):
            widget.setMaximumHeight(92)
            widget.setMinimumHeight(65)
            self._row(title, widget)
        self.column_combo = QComboBox()
        self._row("Data column", self.column_combo)
        self.time_start, self.time_end, self.uv_min, self.uv_max = [QLineEdit() for _ in range(4)]
        for label, widget in (
            ("Time offset ≥ (s)", self.time_start),
            ("Time offset ≤ (s)", self.time_end),
            ("UV distance ≥ (m)", self.uv_min),
            ("UV distance ≤ (m)", self.uv_max),
        ):
            self._row(label, widget)
        self.channel_start, self.channel_end, self.max_rows, self.max_channels = [
            QSpinBox() for _ in range(4)
        ]
        for widget in (self.channel_start, self.channel_end):
            widget.setRange(0, 10_000_000)
        self.max_rows.setRange(1, 4096)
        self.max_rows.setValue(1024)
        self.max_channels.setRange(1, 4096)
        self.max_channels.setValue(2048)
        for label, widget in (
            ("Channel start", self.channel_start),
            ("Channel end < (0 = all)", self.channel_end),
            ("Preview rows (total)", self.max_rows),
            ("Preview channels ≤", self.max_channels),
        ):
            self._row(label, widget)
        layout.addLayout(self.form)
        self.read_button = QPushButton()
        self.read_button.setObjectName("primary")
        self.copy_button = QPushButton()
        self.read_button.clicked.connect(self.requested)
        self.copy_button.clicked.connect(self._copy)
        layout.addWidget(self.read_button)
        layout.addWidget(self.copy_button)
        layout.addStretch()
        for widget in (self.ddids, self.fields, self.scans, self.baselines, self.correlations):
            widget.itemChanged.connect(lambda *_: self.changed.emit())
        for widget in (self.time_start, self.time_end, self.uv_min, self.uv_max):
            widget.textChanged.connect(lambda *_: self.changed.emit())
        for widget in (self.channel_start, self.channel_end, self.max_rows, self.max_channels):
            widget.valueChanged.connect(lambda *_: self.changed.emit())
        self.column_combo.currentIndexChanged.connect(lambda *_: self.changed.emit())
        self.setEnabled(False)
        self.set_language("en")

    def _row(self, source, widget):
        label = QLabel()
        self._labels.append((label, source))
        self.form.addRow(label, widget)

    def set_language(self, language):
        self.language = language
        self.hint.setText(
            tr(
                "Empty checks mean all. Groups remain separate by DDID, field, scan and oriented baseline.",
                language,
            )
        )
        for label, source in self._labels:
            label.setText(tr(source, language))
        self.read_button.setText(tr("Read selected groups", language))
        self.copy_button.setText(tr("Copy parameters", language))
        for name, source in (
            ("ddids", "DDID links a spectral window (SPW) to its polarization setup."),
            ("fields", "A Field identifies a sky pointing or observing target."),
            (
                "scans",
                "A scan groups integrations during an observing segment; it is not a single row.",
            ),
            ("baselines", "One oriented antenna pair; reverse pairs are kept separate."),
            ("correlations", "Recorded polarization products; XX is not automatically Stokes I."),
            (
                "time_start",
                "Seconds since the earliest TIME in the entire MS; blank means no bound.",
            ),
            ("time_end", "Seconds since the earliest TIME in the entire MS; blank means no bound."),
            ("uv_min", "Projected baseline distance sqrt(u² + v²), in metres, from UVW."),
            ("uv_max", "Projected baseline distance sqrt(u² + v²), in metres, from UVW."),
        ):
            getattr(self, name).setToolTip(tr(source, language))

    @staticmethod
    def _fill(widget, items, selected=()):
        widget.clear()
        for label, value in items:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if value in selected else Qt.CheckState.Unchecked
            )
            widget.addItem(item)

    @staticmethod
    def _checked(widget):
        return tuple(
            widget.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(widget.count())
            if widget.item(i).checkState() == Qt.CheckState.Checked
        )

    def set_metadata(self, meta):
        self.metadata = meta
        self.setEnabled(True)
        first = meta.descriptions[0].ddid
        pair = next(((p[3], p[4]) for p in meta.partitions if p[0] == first), None)
        self._fill(
            self.ddids,
            [(f"DDID {d.ddid} / SPW {d.spw}", d.ddid) for d in meta.descriptions],
            (first,),
        )
        self._fill(self.fields, [(f"{i}: {name}", i) for i, name in enumerate(meta.fields)])
        self._fill(self.scans, [(str(i), i) for i in sorted({p[2] for p in meta.partitions})])
        pairs = sorted({(p[3], p[4]) for p in meta.partitions})
        names = meta.antennas
        self._fill(
            self.baselines,
            [(f"{a}: {names[a]} → {b}: {names[b]}", (a, b)) for a, b in pairs],
            (pair,),
        )
        labels = tuple(dict.fromkeys(c for d in meta.descriptions for c in d.correlations))
        self._fill(self.correlations, [(c, c) for c in labels])
        self.column_combo.clear()
        columns = list(meta.columns)
        if "MODEL_DATA" in columns:
            columns += [f"{c}-MODEL_DATA" for c in ("DATA", "CORRECTED_DATA") if c in meta.columns]
        for c in columns:
            self.column_combo.addItem(c, c)
        for edit in (self.time_start, self.time_end, self.uv_min, self.uv_max):
            edit.clear()
        self.channel_start.setValue(0)
        self.channel_end.setValue(0)
        self.max_rows.setValue(1024)
        self.max_channels.setValue(2048)

    @staticmethod
    def _number(edit, nonnegative=False):
        if not edit.text().strip():
            return None
        value = float(edit.text())
        if not np.isfinite(value) or (nonnegative and value < 0):
            raise ValueError("Bounds must be finite; UV bounds must be nonnegative")
        return value

    def build_spec(self):
        if self.metadata is None:
            raise ValueError("No dataset loaded")
        start, end = self._number(self.time_start), self._number(self.time_end)
        umin, umax = self._number(self.uv_min, True), self._number(self.uv_max, True)
        if start is not None and end is not None and start > end:
            raise ValueError("Start time must not exceed end time")
        if umin is not None and umax is not None and umin > umax:
            raise ValueError("Minimum UV distance must not exceed maximum")
        channel_end = self.channel_end.value() or None
        if channel_end is not None and self.channel_start.value() >= channel_end:
            raise ValueError("Channel end must exceed channel start")
        origin = self.metadata.time_range[0]
        return SelectionSpec(
            ddids=self._checked(self.ddids),
            fields=self._checked(self.fields),
            scans=self._checked(self.scans),
            baselines=self._checked(self.baselines),
            correlations=self._checked(self.correlations),
            column=self.column_combo.currentData(),
            time_start=None if start is None else origin + start,
            time_end=None if end is None else origin + end,
            channel_start=self.channel_start.value(),
            channel_end=channel_end,
            max_rows=self.max_rows.value(),
            max_channels=self.max_channels.value(),
            uv_min=umin,
            uv_max=umax,
        )

    def parameter_json(self):
        return json.dumps(
            self.build_spec().to_dict(), ensure_ascii=False, indent=2, allow_nan=False
        )

    def _copy(self):
        try:
            QApplication.clipboard().setText(self.parameter_json())
        except (ValueError, TypeError) as exc:
            self.hint.setText(str(exc))

    def snapshot(self):
        state = {
            name: list(self._checked(getattr(self, name)))
            for name in ("ddids", "fields", "scans", "baselines", "correlations")
        }
        state.update(
            {
                name: getattr(self, name).text()
                for name in ("time_start", "time_end", "uv_min", "uv_max")
            }
        )
        state.update(
            {
                name: getattr(self, name).value()
                for name in ("channel_start", "channel_end", "max_rows", "max_channels")
            }
        )
        state["column"] = self.column_combo.currentData()
        return state

    def restore(self, state):
        # Validate all saved IDs before changing any checks; an invalid restore must
        # never turn a narrow saved selection into an unchecked (=all) selection.
        checks = {}
        for name in ("ddids", "fields", "scans", "baselines", "correlations"):
            widget = getattr(self, name)
            selected = [tuple(v) if isinstance(v, list) else v for v in state.get(name, [])]
            available = [
                widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(widget.count())
            ]
            if any(value not in available for value in selected):
                raise ValueError("Saved selection contains unavailable identifiers")
            checks[name] = selected
        if state.get("column") not in [
            self.column_combo.itemData(i) for i in range(self.column_combo.count())
        ]:
            raise ValueError("Saved selection contains an unavailable data column")
        for name, selected in checks.items():
            widget = getattr(self, name)
            for i in range(widget.count()):
                widget.item(i).setCheckState(
                    Qt.CheckState.Checked
                    if widget.item(i).data(Qt.ItemDataRole.UserRole) in selected
                    else Qt.CheckState.Unchecked
                )
        for name in ("time_start", "time_end", "uv_min", "uv_max"):
            getattr(self, name).setText(str(state.get(name, "")))
        for name in ("channel_start", "channel_end", "max_rows", "max_channels"):
            if name in state:
                getattr(self, name).setValue(int(state[name]))
        self.column_combo.setCurrentIndex(self.column_combo.findData(state["column"]))
