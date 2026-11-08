"""Docked workspace coordination and a read-only Locate inspector."""

import csv
import io
import json
from pathlib import Path

import numpy as np
from astropy.time import Time
from PyQt6.QtCore import QSignalBlocker, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .diagnostic import DiagnosticView
from .overview import OverviewView
from .query import read_query
from .query_controls import QueryControls
from .workbench_text import tr


class PointInspector(QWidget):
    activated = pyqtSignal(dict)

    KEYS = (
        "dataset",
        "spw",
        "unit",
        "time_scale",
        "group",
        "row",
        "channel",
        "correlation",
        "ddid",
        "field",
        "scan",
        "antenna1",
        "antenna2",
        "time",
        "frequency",
        "value",
        "flag",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.records = []
        self.total = 0
        self.language = "en"
        self.scales = ()
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.table = QTableWidget(0, 8)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.currentCellChanged.connect(self._current_changed)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMaximumHeight(180)
        self.copy_button = QPushButton()
        self.clear_button = QPushButton()
        self.copy_button.clicked.connect(self.copy)
        self.clear_button.clicked.connect(self.clear)
        for w in (
            self.label,
            self.note,
            self.table,
            self.details,
            self.copy_button,
            self.clear_button,
        ):
            layout.addWidget(w)
        self.set_language("en")

    def set_language(self, language):
        self.language = language
        self.note.setText(
            tr("Locate works on displayed preview samples only; no flags are written.", language)
        )
        self.copy_button.setText(tr("Copy located rows", language))
        self.clear_button.setText(tr("Clear details", language))
        self.set_records(self.records, self.total, self.scales, self.table.currentRow())

    def clear(self):
        self.set_records([], 0)

    def set_records(self, records, total, scales=(), selected_row=0):
        blocker = QSignalBlocker(self.table)
        self.records = list(records)
        self.total = total
        self.scales = scales
        self.label.setText(
            tr(
                "Located {total:,} displayed points; showing {shown:,} records.",
                self.language,
                total=total,
                shown=len(records),
            )
        )
        self.table.setHorizontalHeaderLabels(
            [
                tr(k, self.language)
                for k in (
                    "Row",
                    "Channel",
                    "Correlation",
                    "DDID",
                    "Field",
                    "Baseline",
                    "Frequency (MHz)",
                    "Value",
                )
            ]
        )
        self.table.setRowCount(len(records))
        for i, r in enumerate(records):
            vals = (
                r["row"],
                r["channel"],
                r["correlation"],
                r["ddid"],
                r["field"],
                f"{r['antenna1']} → {r['antenna2']}",
                f"{r['frequency'] / 1e6:.6f}",
                str(r["value"]),
            )
            for j, value in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
            g = r["group"]
            scale = scales[g] if g < len(scales) else None
            stamp = (
                f"{Time(r['time'] / 86400, format='mjd', scale=scale).isot} {scale.upper()}"
                if scale and np.isfinite(r["time"])
                else str(r["time"])
            )
            for j in range(8):
                self.table.item(i, j).setToolTip(
                    f"Scan {r['scan']} · {stamp} · FLAG={r['flag']} · x={r['x']} · y={r['y']}"
                )
        selected_row = min(max(0, selected_row), len(records) - 1)
        if records:
            self.table.setCurrentCell(selected_row, 0)
        del blocker
        self._show_record(selected_row, emit=False)
        self.copy_button.setEnabled(bool(records))
        self.clear_button.setEnabled(bool(records))

    def _current_changed(self, row, *_):
        self._show_record(row, emit=True)

    def _show_record(self, row, *, emit):
        if 0 <= row < len(self.records):
            r = self.records[row]
            scale = r.get("time_scale", "")
            stamp = (
                f"{Time(r['time'] / 86400, format='mjd', scale=scale).isot} {scale.upper()}"
                if scale and np.isfinite(r["time"])
                else str(r["time"])
            )
            self.details.setPlainText(
                f"{r.get('dataset', '')}\n"
                f"DDID {r['ddid']} / SPW {r.get('spw', '?')} · Field {r['field']} · Scan {r['scan']}\n"
                f"Row {r['row']} · Channel {r['channel']} · {r['correlation']}\n"
                f"{stamp}\n{r['frequency'] / 1e6:.6f} MHz\n"
                f"{r['value']} {r.get('unit', '')} · FLAG={r['flag']}\n"
                f"{r['x_axis']}={r['x']} · {r['y_axis']}={r['y']}"
            )
            if emit:
                self.activated.emit(r)
        else:
            self.details.clear()

    def copy(self):
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=self.KEYS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(self.records)
        QApplication.clipboard().setText(buffer.getvalue())


class WorkbenchMixin:
    """Add workspace UI while keeping table access in the existing serialized worker."""

    def _install_workbench(self):
        self._blocks = ()
        self._query_mode = False
        self._workspace_states = {}
        self._last_spec = None
        self._locating = False
        self.theme = "dark"
        root = self.centralWidget()
        layout = root.layout()
        splitter = self.tabs.parentWidget()
        self.selection_modes = QTabWidget()
        self.selection_modes.addTab(self.selection_scroll, "Quick preview")
        self.query_controls = QueryControls()
        grouped_scroll = QScrollArea()
        grouped_scroll.setWidgetResizable(True)
        grouped_scroll.setWidget(self.query_controls)
        grouped_body = QWidget()
        grouped_layout = QVBoxLayout(grouped_body)
        grouped_layout.setContentsMargins(0, 0, 0, 0)
        grouped_layout.addWidget(grouped_scroll, 1)
        # Keep the apply action visible while long scientific filters scroll.
        grouped_layout.addWidget(self.query_controls.read_button)
        grouped_layout.addWidget(self.query_controls.copy_button)
        self.selection_modes.addTab(grouped_body, "Grouped selection")
        # Both children leave the original splitter before it is removed.
        self.tabs.setParent(root)
        layout.replaceWidget(splitter, self.tabs)
        splitter.hide()
        splitter.deleteLater()
        selection_body = QWidget()
        side = QVBoxLayout(selection_body)
        self.dataset_label = QLabel()
        self.dataset_combo = QComboBox()
        self.dataset_combo.setToolTip("Measurement Set paths")
        side.addWidget(self.dataset_label)
        side.addWidget(self.dataset_combo)
        side.addWidget(self.selection_modes, 1)
        self.selection_dock = self._dock(
            "selectionDock", selection_body, Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self.selection_dock.setMinimumWidth(320)
        self.inspector = PointInspector()
        self.inspector_dock = self._dock(
            "inspectorDock", self.inspector, Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.inspector_dock.setMinimumWidth(300)
        self.inspector_dock.hide()
        self.task_log = QPlainTextEdit()
        self.task_log.setReadOnly(True)
        self.task_log.setMaximumBlockCount(1000)
        self.log_dock = self._dock("logDock", self.task_log, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_dock.hide()
        self.overview = OverviewView()
        self.diagnostic = DiagnosticView()
        self.tabs.addTab(self.overview, "Overview")
        self.tabs.addTab(self.diagnostic, "Diagnostic plots")
        focus = QHBoxLayout()
        self.focus_label = QLabel()
        self.focus_combo = QComboBox()
        self.focus_combo.setMinimumWidth(300)
        focus.addWidget(self.focus_label)
        focus.addWidget(self.focus_combo, 1)
        layout.insertLayout(layout.indexOf(self.tabs), focus)
        self.focus_note = QLabel()
        self.focus_note.setWordWrap(True)
        layout.insertWidget(layout.indexOf(self.tabs), self.focus_note)
        self.view_menu = self.menuBar().addMenu("View")
        for dock in (self.selection_dock, self.inspector_dock, self.log_dock):
            self.view_menu.addAction(dock.toggleViewAction())
        self.view_menu.addSeparator()
        self.layout_save_action = self.view_menu.addAction("Save layout", self.save_layout)
        self.layout_reset_action = self.view_menu.addAction("Reset layout", self.reset_layout)
        self.theme_action = QAction("Light theme", self)
        self.theme_action.setCheckable(True)
        self.theme_action.toggled.connect(
            lambda checked: self.set_theme("light" if checked else "dark")
        )
        self.view_menu.addAction(self.theme_action)
        self.dataset_combo.activated.connect(self._open_recent)
        self.query_controls.requested.connect(self.request_query)
        self.query_controls.changed.connect(self._query_changed)
        self.selection_modes.currentChanged.connect(self._change_mode)
        self.focus_combo.currentIndexChanged.connect(self._display_group)
        self.diagnostic.located.connect(self._on_located)
        self.inspector.activated.connect(self._focus_record)
        self.setAcceptDrops(True)
        try:
            recent = json.loads(self.settings.value("recent_paths", "[]"))
        except (TypeError, ValueError):
            recent = []
        if isinstance(recent, list):
            for path in recent[-20:]:
                if isinstance(path, str):
                    self.dataset_combo.addItem(Path(path).name, path)
        self.dataset_combo.setCurrentIndex(-1)
        self.restore_layout()
        self.set_theme(self.settings.value("workbench/theme", "dark"))
        self._workbench_language()

    def _dock(self, name, widget, area):
        dock = QDockWidget(self)
        dock.setObjectName(name)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _workbench_language(self):
        lang = self.language
        for dock, source in (
            (self.selection_dock, "Data & selection"),
            (self.inspector_dock, "Point inspector"),
            (self.log_dock, "Tasks & log"),
        ):
            dock.setWindowTitle(tr(source, lang))
        self.view_menu.setTitle(tr("View", lang))
        self.layout_save_action.setText(tr("Save layout", lang))
        self.layout_reset_action.setText(tr("Reset layout", lang))
        self.theme_action.setText("浅色主题" if lang == "zh" else "Light theme")
        self.dataset_label.setText(tr("Recent datasets", lang))
        self.focus_label.setText(tr("Focus group", lang))
        self.selection_modes.setTabText(0, tr("Quick preview", lang))
        self.selection_modes.setTabText(1, tr("Grouped selection", lang))
        self.tabs.setTabText(self.tabs.indexOf(self.overview), tr("Overview", lang))
        self.tabs.setTabText(self.tabs.indexOf(self.diagnostic), tr("Diagnostic plots", lang))
        self.overview.set_language(lang)
        self.query_controls.set_language(lang)
        self.diagnostic.set_language(lang)
        self.inspector.set_language(lang)
        self._focus_note()

    def _focus_note(self):
        source = (
            "Showing focus group {index}/{total}; diagnostic plots use all loaded groups."
            if self._blocks
            else "No focused group"
        )
        self.focus_note.setText(
            tr(
                source,
                self.language,
                index=self.focus_combo.currentIndex() + 1,
                total=len(self._blocks),
            )
        )

    def _change_mode(self, index):
        self._query_mode = index == 1
        self.timer.stop()
        self._pending = None
        if self.metadata and not self._opening:
            self._token += 1
            self._mark_previous()
            if not self._query_mode:
                self._schedule()
            else:
                self._set_status("Read selected groups")

    def _query_changed(self):
        if self._query_mode and self.metadata is not None and not self._opening:
            self.timer.stop()
            self._pending = None
            self._token += 1
            self._mark_previous()
            self._set_status("Read selected groups")

    def request_query(self):
        if self._opening or self._closing or self.metadata is None:
            return
        self.timer.stop()
        try:
            spec = self.query_controls.build_spec()
        except (ValueError, TypeError) as exc:
            self._error(str(exc))
            return
        self._query_mode = True
        with QSignalBlocker(self.selection_modes):
            self.selection_modes.setCurrentIndex(1)
        self._token += 1
        self._pending = None
        self._mark_previous()
        self._last_spec = spec
        path, meta = self.metadata.path, self.metadata
        self.last_error = ""
        self._set_status("Reading visibility preview…")
        self._submit(self._token, "query", lambda: read_query(path, spec, meta))

    def _receive_blocks(self, blocks):
        self._blocks = tuple(blocks)
        self._selection_current = True
        self.focus_combo.setEnabled(bool(blocks))
        with QSignalBlocker(self.focus_combo):
            self.focus_combo.clear()
            for i, b in enumerate(self._blocks):

                def ids(array):
                    return ",".join(map(str, np.unique(array))) if array is not None else "?"

                title = f"{i + 1}: DDID {b.ddid} · Field {ids(b.field_ids)} · Scan {ids(b.scan_numbers)} · {ids(b.antenna1)} → {ids(b.antenna2)} · {len(b.times)} rows"
                self.focus_combo.addItem(title, i)
        self._display_group(0)
        self.diagnostic.set_blocks(self._blocks)
        self._focus_note()

    def _display_group(self, index):
        if self._opening or not self._selection_current or index < 0 or index >= len(self._blocks):
            return
        if not self._locating:
            self.diagnostic.clear_selection()
        self.block = self._blocks[index]
        labels = self.block.correlation_labels or self._description().correlations
        current = self.corr_combo.currentText()
        with QSignalBlocker(self.corr_combo):
            self.corr_combo.clear()
            for i, label in enumerate(labels):
                self.corr_combo.addItem(label, i)
            self.corr_combo.setCurrentIndex(max(0, self.corr_combo.findText(current)))
        self._selection_current = True
        if self.block.antenna1 is not None and self.block.antenna2 is not None:
            self.antenna_map.set_baseline(
                (int(self.block.antenna1[0]), int(self.block.antenna2[0]))
            )
        self._render(reset_view=True)
        self._focus_note()

    def _on_located(self, records, total):
        if not records:
            self.inspector.clear()
            self.linked_cursor.clear()
            return
        if self._opening or not self._selection_current or not self._blocks:
            self.inspector.clear()
            return
        descriptions = {d.ddid: d for d in self.metadata.descriptions}
        records = [
            dict(
                r,
                dataset=str(self.metadata.path),
                spw=descriptions[r["ddid"]].spw,
                unit=self._blocks[r["group"]].unit,
                time_scale=self._blocks[r["group"]].time_scale,
            )
            for r in records
        ]
        self.inspector.set_records(records, total, tuple(b.time_scale for b in self._blocks))
        self.inspector_dock.show()
        self._focus_record(records[0])

    def _focus_record(self, record):
        if self._opening or not self._selection_current:
            return
        g = record["group"]
        if not 0 <= g < len(self._blocks):
            return
        self._locating = True
        try:
            self.focus_combo.setCurrentIndex(g)
            if self.block is not self._blocks[g]:
                self._display_group(g)
        finally:
            self._locating = False
        with QSignalBlocker(self.corr_combo):
            self.corr_combo.setCurrentIndex(record["correlation_index"])
        self._render()
        rows = np.flatnonzero(self.block.row_ids == record["row"])
        channels = (
            np.flatnonzero(self.block.channel_ids == record["channel"])
            if self.block.channel_ids is not None
            else []
        )
        if len(rows) and len(channels):
            self.linked_cursor.select(int(rows[0]), int(channels[0]))

    def _capture_workspace(self):
        if self.metadata is None or self._opening:
            return
        quick = {
            name: getattr(self, name).currentData()
            for name in (
                "ddid_combo",
                "field_combo",
                "scan_combo",
                "baseline_combo",
                "corr_combo",
                "column_combo",
                "quantity_combo",
            )
        }
        quick.update(
            {
                name: getattr(self, name).value()
                for name in ("channel_start", "channel_end", "max_rows", "max_channels")
            }
        )
        quick.update({name: getattr(self, name).text() for name in ("time_start", "time_end")})
        quick["hide_flags"] = self.hide_flags.isChecked()
        self._workspace_states[str(self.metadata.path)] = {
            "quick": quick,
            "query": self.query_controls.snapshot(),
            "grouped": self._query_mode,
        }

    def _workbench_metadata(self, meta):
        self._blocks = ()
        self.diagnostic.clear()
        self.inspector.clear()
        self.overview.set_metadata(meta)
        with QSignalBlocker(self.query_controls):
            self.query_controls.set_metadata(meta)
        self._query_mode = False
        with QSignalBlocker(self.selection_modes):
            self.selection_modes.setCurrentIndex(0)
        paths = [self.dataset_combo.itemData(i) for i in range(self.dataset_combo.count())]
        path = str(meta.path)
        if path not in paths:
            paths.append(path)
        with QSignalBlocker(self.dataset_combo):
            self.dataset_combo.clear()
            for value in paths[-20:]:
                self.dataset_combo.addItem(Path(value).name, value)
            self.dataset_combo.setCurrentIndex(
                next(
                    i
                    for i in range(self.dataset_combo.count())
                    if self.dataset_combo.itemData(i) == path
                )
            )
        self.settings.setValue("recent_paths", json.dumps(paths[-20:]))
        self.focus_combo.clear()
        self._focus_note()

    def _restore_workspace(self):
        state = self._workspace_states.get(str(self.metadata.path))
        if not state:
            return
        q = state["quick"]

        def choose(name):
            combo = getattr(self, name)
            value = q[name]
            with QSignalBlocker(combo):
                index = next((i for i in range(combo.count()) if combo.itemData(i) == value), 0)
                combo.setCurrentIndex(index)

        choose("ddid_combo")
        self._ddid_changed()
        choose("field_combo")
        self._field_changed()
        choose("scan_combo")
        self._scan_changed()
        for name in ("baseline_combo", "corr_combo", "column_combo", "quantity_combo"):
            choose(name)
        for name in ("channel_start", "channel_end", "max_rows", "max_channels"):
            with QSignalBlocker(getattr(self, name)):
                getattr(self, name).setValue(q[name])
        for name in ("time_start", "time_end"):
            getattr(self, name).setText(q[name])
        with QSignalBlocker(self.hide_flags):
            self.hide_flags.setChecked(q["hide_flags"])
        try:
            with QSignalBlocker(self.query_controls):
                self.query_controls.restore(state["query"])
        except (ValueError, TypeError, KeyError) as exc:
            self._error(str(exc))
        self._query_mode = state["grouped"]
        with QSignalBlocker(self.selection_modes):
            self.selection_modes.setCurrentIndex(int(self._query_mode))
        self._schedule()

    def _open_recent(self, index):
        path = self.dataset_combo.itemData(index)
        if path:
            self.open_ms(path)

    def save_layout(self):
        self.settings.setValue("workbench/layout", self.saveState(2))
        self.settings.sync()

    def restore_layout(self):
        state = self.settings.value("workbench/layout")
        if state is not None:
            self.restoreState(state, 2)

    def reset_layout(self):
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.selection_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.selection_dock.show()
        self.inspector_dock.hide()
        self.log_dock.hide()

    def set_theme(self, theme):
        from .window import STYLE

        theme = theme if theme in ("light", "dark") else "dark"
        self.theme = theme
        with QSignalBlocker(self.theme_action):
            self.theme_action.setChecked(theme == "light")
        style = STYLE
        if theme == "light":
            for old, new in (
                ("#0c1420", "#f3f6fb"),
                ("#131d2b", "#ffffff"),
                ("#dae5f2", "#25344a"),
                ("#f1f6fc", "#142337"),
                ("#91a5ba", "#52657a"),
                ("#1b293b", "#edf2f8"),
                ("#172232", "#e3eaf3"),
                ("#263446", "#ccd6e4"),
                ("#1b3547", "#dce9f2"),
                ("#245067", "#c8dce9"),
                ("#65dbc6", "#087f76"),
            ):
                style = style.replace(old, new)
        self.setStyleSheet(style)
        bg, fg = ("#ffffff", "#25344a") if theme == "light" else ("#131d2b", "#aebdce")
        for view in (
            self.graphics,
            self.antenna_map.view,
            self.overview.timeline,
            self.diagnostic.plot,
        ):
            view.setBackground(bg)
        for plot in (
            self.spectrum_plot,
            self.time_plot,
            self.waterfall_plot,
            self.antenna_map.plot,
            self.overview.timeline.getPlotItem(),
            self.diagnostic.plot.getPlotItem(),
        ):
            for axis in ("bottom", "left"):
                plot.getAxis(axis).setPen(fg)
                plot.getAxis(axis).setTextPen(fg)
            plot.titleLabel.setText(plot.titleLabel.text, color=fg)
        self.diagnostic.legend.setLabelTextColor(fg)
        # LabelItem.setAttr changes defaults only; repaint its existing HTML too.
        for _, label in self.diagnostic.legend.items:
            label.setText(label.text, color=fg)
        highlight = "#9b6200" if theme == "light" else "#fff1a8"
        self.diagnostic.selection_scatter.setPen(highlight, width=2)
        self.diagnostic.roi.setPen(highlight)
        self.settings.setValue("workbench/theme", theme)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.open_ms(urls[0].toLocalFile())
            event.acceptProposedAction()
