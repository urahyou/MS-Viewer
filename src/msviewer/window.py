"""PyQt6 visibility explorer, with serialized/coalesced background I/O."""

from pathlib import Path

import numpy as np
import pyqtgraph as pg
from astropy.time import Time
from PyQt6.QtCore import QSettings, QSignalBlocker, Qt, QThreadPool, QTimer, QUrl
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QFontDatabase
from PyQt6.QtWidgets import (
    QAbstractButton,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .cursor import LinkedCursor
from .i18n import CHINESE, error_text, install_qt_language, text
from .model import Selection
from .processing import QUANTITIES, prepare_plot
from .reader import inspect_ms, read_visibility
from .resources import SAMPLE_NAMES, prepare_sample, sample_source, tutorial_path
from .workers import Job

pg.setConfigOptions(
    antialias=False, imageAxisOrder="row-major", background="#131d2b", foreground="#aebdce"
)

STYLE = """
QMainWindow, QWidget { background: #0c1420; color: #dae5f2; font-size: 13px; }
QFrame#panel { background: #131d2b; border: 1px solid #263446; border-radius: 8px; }
QFrame#panel QLabel, QFrame#panel QCheckBox { background: transparent; }
QLabel#brand { font-size: 24px; font-weight: 700; color: #f1f6fc; }
QLabel#muted { color: #91a5ba; }
QLabel#summary { font-size: 15px; color: #65dbc6; padding: 10px; }
QComboBox, QLineEdit, QSpinBox { background: #1b293b; padding: 6px; border: 1px solid #34465c; border-radius: 4px; }
QComboBox QAbstractItemView { background: #1b293b; selection-background-color: #28596a; }
QPushButton { background: #1b3547; border: 1px solid #34556c; border-radius: 5px; padding: 9px 12px; }
QPushButton:hover { background: #245067; }
QPushButton#primary { background: #287f77; color: white; font-weight: bold; }
QPushButton:disabled { color: #667588; background: #172232; }
QTabWidget::pane { border: 1px solid #263446; }
QTabBar::tab { background: #172232; padding: 9px 18px; }
QTabBar::tab:selected { background: #264358; color: #74e4d1; }
QPlainTextEdit { background: #131d2b; border: none; }
QProgressBar { border: none; max-height: 3px; background: #172232; }
QProgressBar::chunk { background: #4acdb5; }
QCheckBox { spacing: 8px; }
"""


def _date(seconds, scale):
    return Time(seconds / 86400, format="mjd", scale=scale).isot


def _fill(combo, pairs, preferred=None):
    blocker = QSignalBlocker(combo)
    combo.clear()
    for label, data in pairs:
        combo.addItem(label, data)
    index = combo.findData(preferred)
    combo.setCurrentIndex(max(0, index))
    del blocker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("RadioAstronomy", "MSViewer")
        self.language = self.settings.value("language", "en")
        if self.language not in ("en", "zh"):
            self.language = "en"
        self._status_source = "Ready · MS data are opened read-only"
        self._status_values = {}
        self._cursor_position = None
        self.metadata = self.block = self.plot_data = None
        self.last_error = ""
        self._token = 0
        self._job = self._pending = None
        self._closing = False
        self._opening = False
        self._selection_current = False
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self.request_read)
        self.setWindowTitle("MS Viewer · Visibility explorer")
        self.resize(1360, 900)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._capture_static_texts()
        self.set_language(self.language, persist=False)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 16, 20, 12)
        heading = QHBoxLayout()
        brand = QLabel("MS VIEWER")
        brand.setObjectName("brand")
        heading.addWidget(brand)
        subtitle = QLabel("RADIO ASTRONOMY  /  VISIBILITY EXPLORER")
        subtitle.setObjectName("muted")
        heading.addWidget(subtitle)
        heading.addStretch()
        self.open_button = QPushButton("Open Measurement Set…")
        self.open_button.setObjectName("primary")
        self.open_button.clicked.connect(self.choose_ms)
        heading.addWidget(self.open_button)
        layout.addLayout(heading)
        self.path_label = QLabel("Open an MS directory to begin · read-only")
        self.path_label.setTextFormat(Qt.TextFormat.PlainText)
        self.path_label.setObjectName("muted")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.path_label)
        self.summary_label = QLabel(
            "Select a public sample from the Samples menu, or open your own MS."
        )
        self.summary_label.setObjectName("summary")
        layout.addWidget(self.summary_label)
        splitter = QSplitter()
        layout.addWidget(splitter, 1)
        panel = QFrame()
        self.selection_panel = panel
        panel.setObjectName("panel")
        panel.setMinimumWidth(345)
        side = QVBoxLayout(panel)
        side.addWidget(QLabel("DATA SELECTION"))
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.ddid_combo = QComboBox()
        self.field_combo = QComboBox()
        self.scan_combo = QComboBox()
        self.baseline_combo = QComboBox()
        self.corr_combo = QComboBox()
        self.column_combo = QComboBox()
        self.quantity_combo = QComboBox()
        for quantity in QUANTITIES:
            self.quantity_combo.addItem(quantity, quantity)
        for label, widget in (
            ("DDID / SPW", self.ddid_combo),
            ("Field", self.field_combo),
            ("Scan", self.scan_combo),
            ("Baseline", self.baseline_combo),
            ("Correlation", self.corr_combo),
            ("Column", self.column_combo),
            ("Quantity", self.quantity_combo),
        ):
            form.addRow(label, widget)
        self.time_start, self.time_end = QLineEdit(), QLineEdit()
        self.time_start.setPlaceholderText("Start (seconds)")
        self.time_end.setPlaceholderText("End (seconds)")
        form.addRow("Time offset ≥", self.time_start)
        form.addRow("Time offset ≤", self.time_end)
        self.channel_start, self.channel_end = QSpinBox(), QSpinBox()
        for spin in (self.channel_start, self.channel_end):
            spin.setRange(0, 10000000)
        form.addRow("Channel start", self.channel_start)
        form.addRow("Channel end <", self.channel_end)
        self.max_rows = QSpinBox()
        self.max_rows.setRange(1, 4096)
        self.max_rows.setValue(1024)
        self.max_channels = QSpinBox()
        self.max_channels.setRange(1, 4096)
        self.max_channels.setValue(2048)
        form.addRow("Preview rows ≤", self.max_rows)
        form.addRow("Preview channels ≤", self.max_channels)
        side.addLayout(form)
        self.hide_flags = QCheckBox("Hide flagged samples")
        self.hide_flags.setChecked(True)
        side.addWidget(self.hide_flags)
        self.apply_button = QPushButton("Apply selection")
        self.apply_button.setObjectName("primary")
        self.apply_button.clicked.connect(self.request_read)
        side.addWidget(self.apply_button)
        note = QLabel(
            "Baselines follow ANTENNA1 → ANTENNA2.\nCurves show unweighted preview means.\nPhase uses a circular mean.\nChannel end is exclusive; indices start at 0."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        side.addWidget(note)
        side.addStretch()
        self.export_button = QPushButton("Export plots as PNG…")
        self.export_button.clicked.connect(self.export_png)
        side.addWidget(self.export_button)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(370)
        splitter.addWidget(scroll)
        tabs = self.tabs = QTabWidget()
        self.graphics = pg.GraphicsLayoutWidget()
        self.spectrum_plot = self.graphics.addPlot(row=0, col=0, title="Frequency spectrum")
        self.time_plot = self.graphics.addPlot(row=0, col=1, title="Time trace")
        self.spectrum_curve = self.spectrum_plot.plot(pen=pg.mkPen("#63dfcf", width=1.5))
        self.time_curve = self.time_plot.plot(pen=pg.mkPen("#e6b86a", width=1.5))
        for plot in (self.spectrum_plot, self.time_plot):
            plot.showGrid(x=True, y=True, alpha=0.15)
        self.spectrum_plot.setLabel("bottom", "Frequency", units="MHz")
        self.spectrum_plot.getAxis("bottom").enableAutoSIPrefix(False)
        self.time_plot.setLabel("bottom", "Seconds since first preview sample")
        self.waterfall_plot = self.graphics.addPlot(
            row=1, col=0, colspan=2, title="Waterfall · hover for physical coordinates"
        )
        self.waterfall_plot.setLabel("bottom", "Preview channel index")
        self.waterfall_plot.setLabel("left", "Preview row index (time sorted)")
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.image_item.setColorMap(pg.colormap.get("viridis"))
        self.waterfall_plot.addItem(self.image_item)
        self.colorbar = pg.ColorBarItem(values=(0, 1), colorMap=pg.colormap.get("viridis"))
        self.colorbar.setImageItem(self.image_item, insert_in=self.waterfall_plot)
        self.graphics.ci.layout.setRowStretchFactor(0, 1)
        self.graphics.ci.layout.setRowStretchFactor(1, 2)
        self.linked_cursor = LinkedCursor(
            self.graphics,
            self.spectrum_plot,
            self.time_plot,
            self.waterfall_plot,
            self.image_item,
            self._cursor_changed,
        )
        tabs.addTab(self.graphics, "Visibilities")
        self.metadata_text = QPlainTextEdit()
        self.metadata_text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.metadata_text.setReadOnly(True)
        tabs.addTab(self.metadata_text, "MS metadata")
        splitter.addWidget(tabs)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([370, 1000])
        self.channel_hint = QLabel()
        self.channel_hint.setWordWrap(True)
        self.channel_hint.setStyleSheet("color: #e6b86a;")
        self.channel_hint.hide()
        layout.addWidget(self.channel_hint)
        self.cursor_label = QLabel(
            "Waterfall axes are sample indices; hover to see frequency, time and original row."
        )
        self.cursor_label.setObjectName("muted")
        self.cursor_label.setWordWrap(True)
        # Reserve two lines so changing hover text never resizes the plot viewports.
        self.cursor_label.setFixedHeight(2 * self.cursor_label.fontMetrics().lineSpacing() + 8)
        layout.addWidget(self.cursor_label)
        self.status_label = QLabel("Ready · MS data are opened read-only")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.menuBar().setNativeMenuBar(False)
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Open MS directory…", self.choose_ms)
        file_menu.addAction("Export plots…", self.export_png)
        samples = self.menuBar().addMenu("Samples")
        for name in SAMPLE_NAMES:
            action = samples.addAction(
                name, lambda checked=False, name=name: self.open_sample(name)
            )
            action.setEnabled((sample_source(name) / "table.dat").is_file())
        help_menu = self.menuBar().addMenu("Help")
        self.tutorial_action = help_menu.addAction(
            "Open illustrated guide (PDF)…", self.open_tutorial
        )
        self.tutorial_action.setEnabled(tutorial_path().is_file())
        language_menu = self.menuBar().addMenu("语言 / Language")
        group = QActionGroup(self)
        group.setExclusive(True)
        self.language_actions = {}
        for code, label in (("zh", "中文"), ("en", "English")):
            action = language_menu.addAction(label)
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, code=code: self.set_language(code))
            self.language_actions[code] = action
        self.ddid_combo.currentIndexChanged.connect(self._ddid_changed)
        self.field_combo.currentIndexChanged.connect(self._field_changed)
        self.scan_combo.currentIndexChanged.connect(self._scan_changed)
        for widget in (self.baseline_combo, self.column_combo):
            widget.currentIndexChanged.connect(self._schedule)
        for widget in (self.channel_start, self.channel_end, self.max_rows, self.max_channels):
            widget.valueChanged.connect(self._schedule)
        for widget in (self.time_start, self.time_end):
            widget.editingFinished.connect(self._schedule)
        self.corr_combo.currentIndexChanged.connect(self._render)
        self.quantity_combo.currentIndexChanged.connect(self._render)
        self.hide_flags.toggled.connect(self._render)
        self.apply_button.setEnabled(False)
        self.export_button.setEnabled(False)

    def choose_ms(self):
        path = QFileDialog.getExistingDirectory(
            self,
            self._text("Choose a Measurement Set directory"),
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self.open_ms(path)

    def open_ms(self, path):
        self._start_open(path, lambda: inspect_ms(path))

    def open_sample(self, name):
        self._start_open(name, lambda: inspect_ms(prepare_sample(name)))

    def open_tutorial(self):
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(tutorial_path()))):
            self._error("Could not open the tutorial")

    def _start_open(self, path, function):
        self.timer.stop()
        self._token += 1
        self._opening = True
        self.linked_cursor.set_data(None)
        self.selection_panel.setEnabled(False)
        self.last_error = ""
        self._set_status("Opening {name}…", name=Path(path).name)
        self._submit(self._token, "open", function)

    def _submit(self, token, kind, function):
        if self._closing:
            return
        if self._job is not None:
            self._pending = (token, kind, function)
            return
        self.progress.show()
        self._job = Job(token, kind, function)
        self._job.signals.finished.connect(self._finished)
        self.pool.start(self._job)

    def _finished(self, token, kind, result, error):
        self._job = None
        if self._closing:
            self._pending = None
            QTimer.singleShot(0, self.close)
            return
        if token == self._token:
            if kind == "open":
                self._opening = False
                self.selection_panel.setEnabled(True)
            if error:
                self._error(error)
            elif kind == "open":
                self._set_metadata(result)
            else:
                self.block = result
                self._selection_current = True
                self._render(reset_view=True)
            if kind == "open" and self._selection_current and self.plot_data is not None:
                # A failed/unusable open retains the previous, still-current preview.
                self.linked_cursor.set_data(self.plot_data)
        # _set_metadata may immediately submit a fresh read.
        if self._job is None and self._pending is not None:
            pending, self._pending = self._pending, None
            self._submit(*pending)
        if self._job is None:
            self.progress.hide()

    def _set_metadata(self, meta):
        if not meta.columns or not meta.descriptions or meta.time_range is None:
            self._error("This MS has no readable visibility data or is empty")
            return
        self.metadata = meta
        self._selection_current = False
        self.block = None
        self.plot_data = None
        self.spectrum_curve.clear()
        self.time_curve.clear()
        self.image_item.clear()
        self.linked_cursor.set_data(None)
        self.path_label.setText(str(meta.path))
        self.setWindowTitle(self._text("{name} · MS Viewer", name=meta.path.name))
        self._cursor_position = None
        self._refresh_metadata_text()
        self._refresh_cursor()
        _fill(
            self.ddid_combo, [(f"DDID {d.ddid} / SPW {d.spw}", d.ddid) for d in meta.descriptions]
        )
        _fill(self.column_combo, [(c, c) for c in meta.columns])
        self.time_start.clear()
        self.time_end.clear()
        self.apply_button.setEnabled(bool(meta.columns and meta.descriptions))
        self._ddid_changed()

    def _description(self):
        return next(
            d for d in self.metadata.descriptions if d.ddid == self.ddid_combo.currentData()
        )

    def _partitions(self):
        return [p for p in self.metadata.partitions if p[0] == self.ddid_combo.currentData()]

    def _ddid_changed(self, *_):
        if not self.metadata or self.ddid_combo.currentData() is None:
            return
        d = self._description()
        _fill(self.corr_combo, [(c, i) for i, c in enumerate(d.correlations)])
        for spin in (self.channel_start, self.channel_end):
            blocker = QSignalBlocker(spin)
            spin.setMaximum(len(d.frequencies))
            spin.setValue(0 if spin is self.channel_start else len(d.frequencies))
            del blocker
        fields = sorted({p[1] for p in self._partitions()})
        _fill(
            self.field_combo,
            [(self._text("All fields"), None)]
            + [(f"{i}: {self.metadata.fields[i]}", i) for i in fields],
        )
        self._field_changed()

    def _field_changed(self, *_):
        if not self.metadata:
            return
        field = self.field_combo.currentData()
        scans = sorted({p[2] for p in self._partitions() if field is None or p[1] == field})
        _fill(self.scan_combo, [(self._text("All scans"), None)] + [(str(i), i) for i in scans])
        self._scan_changed()

    def _scan_changed(self, *_):
        if not self.metadata:
            return
        field, scan = self.field_combo.currentData(), self.scan_combo.currentData()
        baselines = sorted(
            {
                (p[3], p[4])
                for p in self._partitions()
                if (field is None or p[1] == field) and (scan is None or p[2] == scan)
            }
        )
        previous = self.baseline_combo.currentData()
        names = self.metadata.antennas
        _fill(
            self.baseline_combo,
            [(f"{names[a]} → {names[b]}", (a, b)) for a, b in baselines],
            previous,
        )
        self._schedule()

    def _schedule(self, *_):
        if self.metadata and not self._closing and not self._opening:
            self._mark_previous()
            self._token += 1  # Invalidate an in-flight read immediately.
            self._pending = None
            self.timer.start()
            self._set_status("Selection changed · updating preview…")

    def request_read(self, *_):
        if self._opening or self._closing:
            return
        self.timer.stop()
        if self.metadata is None or not self.metadata.columns or not self.metadata.descriptions:
            return
        self._token += 1
        self._pending = None
        self._mark_previous()
        try:
            a1, a2 = self.baseline_combo.currentData()
            origin = self.metadata.time_range[0]
            start = (
                float(self.time_start.text()) + origin if self.time_start.text().strip() else None
            )
            end = float(self.time_end.text()) + origin if self.time_end.text().strip() else None
            selection = Selection(
                self.ddid_combo.currentData(),
                a1,
                a2,
                self.field_combo.currentData(),
                self.scan_combo.currentData(),
                self.column_combo.currentData(),
                start,
                end,
                self.channel_start.value(),
                self.channel_end.value(),
                self.max_rows.value(),
                self.max_channels.value(),
            )
        except (ValueError, TypeError) as exc:
            self._error(f"Invalid selection: {exc}")
            return
        self.last_error = ""
        self._set_status("Reading visibility preview…")
        path = self.metadata.path
        self._submit(self._token, "read", lambda: read_visibility(path, selection))

    def _render(self, *_, reset_view=False):
        if self.block is None or not self._selection_current or self._opening:
            return
        correlation = self.corr_combo.currentData()
        if correlation is None or correlation >= self.block.values.shape[2]:
            return
        plot = prepare_plot(
            self.block, correlation, self.quantity_combo.currentData(), self.hide_flags.isChecked()
        )
        self.plot_data = plot
        for curve, x, y in (
            (self.spectrum_curve, plot.frequency_mhz, plot.spectrum),
            (self.time_curve, plot.elapsed_seconds, plot.time_trace),
        ):
            valid = np.isfinite(y)
            neighbours = np.r_[False, valid[:-1]] | np.r_[valid[1:], False]
            # A line cannot show an isolated point, including points between flagged gaps.
            symbol = "o" if np.any(valid & ~neighbours) else None
            curve.setData(
                x,
                y,
                connect="finite",
                symbol=symbol,
                symbolSize=7,
                symbolPen=None,
                symbolBrush=curve.opts["pen"].color(),
            )
        if reset_view:
            for item in (self.spectrum_plot, self.time_plot):
                item.enableAutoRange(x=True, y=True)
                item.autoRange()
            if len(plot.frequency_mhz) == 1:
                frequency = float(plot.frequency_mhz[0])
                # This is viewport padding around a single sample, not a channel bandwidth.
                padding = max(abs(frequency) * 1e-6, 0.001)
                self.spectrum_plot.setXRange(frequency - padding, frequency + padding, padding=0)
        for item, values in (
            (self.spectrum_plot, plot.spectrum),
            (self.time_plot, plot.time_trace),
        ):
            visible = values[np.isfinite(values)]
            if len(visible) == 1:
                value = float(visible[0])
                padding = max(abs(value) * 0.1, 1e-9)
                item.setYRange(value - padding, value + padding, padding=0)
            else:
                item.enableAutoRange(y=True)
        finite = plot.image[np.isfinite(plot.image)]
        lo, hi = np.percentile(finite, [2, 98]) if finite.size else (0.0, 1.0)
        if plot.quantity == "Phase":
            lo, hi = -180.0, 180.0
        if hi <= lo:
            hi = lo + max(1e-6, abs(lo) * 0.01)
        self.image_item.setImage(
            np.ascontiguousarray(plot.image), autoLevels=False, levels=(float(lo), float(hi))
        )
        self.colorbar.setLevels((float(lo), float(hi)))
        self.waterfall_plot.setAspectLocked(False)
        self.waterfall_plot.setRange(
            xRange=(0, plot.image.shape[1]), yRange=(0, plot.image.shape[0]), padding=0.02
        )
        self._update_plot_labels()
        self._set_status(
            "Preview: {rows:,} / {total:,} selected rows × {channels:,} channels · flagged {flagged:.1%} · means use preview samples; no weights applied · read-only",
            rows=len(self.block.times),
            total=self.block.total_rows,
            channels=len(self.block.frequencies),
            flagged=plot.flag_fraction,
        )
        self.linked_cursor.set_data(plot)
        self.export_button.setEnabled(True)

    def _mark_previous(self):
        """Keep prior results, but never reinterpret them with a new selection."""
        self._selection_current = False
        self.linked_cursor.set_data(None)
        self._update_plot_labels()

    def _cursor_changed(self, position):
        self._cursor_position = position
        self._refresh_cursor()

    def _error(self, text):
        self.last_error = text
        self._set_status("Error: {error}", error=text)

    def export_png(self):
        if self.plot_data is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            self._text("Export visibility plots"),
            "visibilities.png",
            self._text("PNG image (*.png)"),
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if filename and not self.graphics.grab().save(filename, "PNG"):
            self._error("Could not save the plot image")

    def closeEvent(self, event):
        self.timer.stop()
        if self._job is not None:
            self._closing = True
            self._token += 1
            self._pending = None
            self._set_status("Finishing active read before closing…")
            self.setEnabled(False)
            event.ignore()
        else:
            event.accept()

    def _text(self, source, **values):
        return text(source, self.language, **values)

    def _capture_static_texts(self):
        """Capture application-owned source strings once, before the first translation."""
        dynamic = (self.path_label, self.summary_label, self.status_label, self.cursor_label)
        self._text_bindings = []
        for widget in self.findChildren(QLabel) + self.findChildren(QAbstractButton):
            if widget not in dynamic and widget.text() in CHINESE:
                self._text_bindings.append((widget, widget.text()))
        for action in self.findChildren(QAction):
            if action.text() in CHINESE:
                self._text_bindings.append((action, action.text()))
        self._placeholder_bindings = [
            (self.time_start, "Start (seconds)"),
            (self.time_end, "End (seconds)"),
        ]

    def set_language(self, language, *, persist=True):
        if language not in ("en", "zh"):
            raise ValueError(f"Unsupported language: {language}")
        self.language = language
        install_qt_language(language)
        if persist:
            self.settings.setValue("language", language)
            self.settings.sync()
        for widget, source in self._text_bindings:
            widget.setText(self._text(source))
        for widget, source in self._placeholder_bindings:
            widget.setPlaceholderText(self._text(source))
        quantity = self.quantity_combo.currentData()
        _fill(self.quantity_combo, [(self._text(q), q) for q in QUANTITIES], quantity)
        for combo, source in ((self.field_combo, "All fields"), (self.scan_combo, "All scans")):
            if combo.count():
                blocker = QSignalBlocker(combo)
                combo.setItemText(0, self._text(source))
                del blocker
        self.tabs.setTabText(0, self._text("Visibilities"))
        self.tabs.setTabText(1, self._text("MS metadata"))
        self.language_actions[language].setChecked(True)
        self.setWindowTitle(
            self._text("{name} · MS Viewer", name=self.metadata.path.name)
            if self.metadata
            else self._text("MS Viewer · Visibility explorer")
        )
        if self.metadata:
            self._refresh_metadata_text()
        else:
            self.path_label.setText(self._text("Open an MS directory to begin · read-only"))
            self.summary_label.setText(
                self._text("Select a public sample from the Samples menu, or open your own MS.")
            )
        self._update_plot_labels()
        self._refresh_status()
        self._refresh_cursor()

    def _set_status(self, source, **values):
        self._status_source, self._status_values = source, values
        self._refresh_status()

    def _refresh_status(self):
        values = dict(self._status_values)
        if "error" in values:
            values["error"] = error_text(values["error"], self.language)
        self.status_label.setText(self._text(self._status_source, **values))

    def _refresh_metadata_text(self):
        meta = self.metadata
        self.summary_label.setText(
            self._text(
                "{telescope}   /   {rows:,} rows   /   {antennas} antennas   /   {ddids} DDIDs",
                telescope=meta.telescope,
                rows=meta.rows,
                antennas=len(meta.antennas),
                ddids=len(meta.descriptions),
            )
        )
        summary = [
            self._text("Path: {path}", path=meta.path),
            self._text("Telescope: {telescope}", telescope=meta.telescope),
            self._text("Rows: {rows:,}", rows=meta.rows),
            self._text(
                "Data columns: {columns}", columns=", ".join(meta.columns) or self._text("(none)")
            ),
            "",
            self._text("ANTENNAS"),
        ]
        summary += [f"{i}: {name}" for i, name in enumerate(meta.antennas)]
        summary += ["", self._text("FIELDS")] + [
            f"{i}: {name}" for i, name in enumerate(meta.fields)
        ]
        summary += ["", self._text("DATA DESCRIPTIONS")]
        for d in meta.descriptions:
            summary.append(
                self._text(
                    "DDID {ddid} → SPW {spw}, POL {pol}, {channels} channels, {correlations}",
                    ddid=d.ddid,
                    spw=d.spw,
                    pol=d.polarization,
                    channels=len(d.frequencies),
                    correlations=", ".join(d.correlations),
                )
            )
        if meta.time_range:
            summary += [
                "",
                self._text("TIME ({scale}):", scale=meta.time_scale.upper()),
                _date(meta.time_range[0], meta.time_scale),
                _date(meta.time_range[1], meta.time_scale),
            ]
        self.metadata_text.setPlainText("\n".join(summary))

    def _update_plot_labels(self):
        self._update_channel_hint()
        self.spectrum_plot.setLabel("bottom", self._text("Frequency"), units="MHz")
        self.time_plot.setLabel("bottom", self._text("Seconds since first preview sample"))
        self.waterfall_plot.setLabel("bottom", self._text("Preview channel index"))
        self.waterfall_plot.setLabel("left", self._text("Preview row index (time sorted)"))
        if self.plot_data is not None:
            for plot in (self.spectrum_plot, self.time_plot):
                plot.setLabel(
                    "left", self._text(self.plot_data.quantity), units=self.plot_data.unit or None
                )
        if self.block is not None and not self._selection_current:
            for plot, title in (
                (self.spectrum_plot, "Frequency spectrum"),
                (self.time_plot, "Time trace"),
                (self.waterfall_plot, "Waterfall"),
            ):
                plot.setTitle(self._text("{title} · previous selection", title=self._text(title)))
        else:
            if self.block is not None and len(self.block.frequencies) == 1:
                self.spectrum_plot.setTitle(
                    self._text(
                        "Single-channel spectrum · {frequency:.6f} MHz",
                        frequency=self.block.frequencies[0] / 1e6,
                    )
                )
                self.waterfall_plot.setTitle(
                    self._text("Single channel · each row repeats the same channel horizontally")
                )
            else:
                self.spectrum_plot.setTitle(self._text("Frequency spectrum"))
                self.waterfall_plot.setTitle(
                    self._text("Waterfall · hover for physical coordinates")
                )
            self.time_plot.setTitle(
                self._text(
                    "Time trace · {first} {scale}",
                    first=_date(self.block.times[0], self.block.time_scale),
                    scale=self.block.time_scale.upper(),
                )
                if self.block is not None
                else self._text("Time trace")
            )

    def _update_channel_hint(self):
        single = self.block is not None and len(self.block.frequencies) == 1
        self.channel_hint.setVisible(single)
        if single:
            hint = self._text(
                "Only one frequency channel ({frequency:.6f} MHz). Horizontal colour is repeated; use the time trace to inspect variation.",
                frequency=self.block.frequencies[0] / 1e6,
            )
            if not self._selection_current:
                hint = self._text("Previous selection: {hint}", hint=hint)
            self.channel_hint.setText(hint)

    def _refresh_cursor(self):
        if self._cursor_position is None or self.plot_data is None:
            self.cursor_label.setText(
                self._text("Linked cursor: hover over any plot; mean curves stay unchanged.")
            )
            self.cursor_label.setToolTip("")
            return
        row, channel = self._cursor_position
        parts = []
        unit = self.plot_data.unit

        def value_text(value):
            return f"{value:.5g}" if np.isfinite(value) else self._text("hidden / non-finite")

        if channel is not None:
            parts.append(
                self._text(
                    "Preview channel {channel} · {frequency:.6f} MHz",
                    channel=channel,
                    frequency=self.plot_data.frequency_mhz[channel],
                )
            )
        if row is not None:
            parts.append(
                self._text(
                    "MS row {row} · {time} {scale} · +{elapsed:.3f} s",
                    row=self.block.row_ids[row],
                    time=_date(self.block.times[row], self.block.time_scale),
                    scale=self.block.time_scale.upper(),
                    elapsed=self.plot_data.elapsed_seconds[row],
                )
            )
        if row is not None and channel is not None:
            parts.append(
                self._text(
                    "Sample {quantity}: {value} {unit}",
                    quantity=self._text(self.plot_data.quantity),
                    value=value_text(self.plot_data.image[row, channel]),
                    unit=unit,
                )
            )
            if self.block.flags[row, channel, self.corr_combo.currentData()]:
                parts.append(self._text("Flagged"))
        if channel is not None:
            parts.append(
                self._text(
                    "Spectrum mean: {value} {unit}",
                    value=value_text(self.plot_data.spectrum[channel]),
                    unit=unit,
                )
            )
        if row is not None:
            parts.append(
                self._text(
                    "Time mean: {value} {unit}",
                    value=value_text(self.plot_data.time_trace[row]),
                    unit=unit,
                )
            )
        label = "  |  ".join(parts)
        self.cursor_label.setText(label)
        self.cursor_label.setToolTip(label)
