"""Bounded, per-sample visibility diagnostics and read-only preview-point Locate.

Only displayed finite preview samples are selectable. Source references remain vectorized;
Python records are materialized only for the capped Locate detail panel.
"""

import numpy as np
import pyqtgraph as pg
from astropy.time import Time
from PyQt6.QtCore import QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

AXES = ("TIME", "FREQ", "CHAN", "AMP", "PHASE", "REAL", "IMAG", "U", "V", "UVDIST")
_AXIS_LABELS = {
    "en": (
        "Elapsed time",
        "Frequency",
        "Original channel",
        "Amplitude",
        "Phase",
        "Real",
        "Imaginary",
        "U",
        "V",
        "UV distance",
    ),
    "zh": ("经过时间", "频率", "原始通道", "振幅", "相位", "实部", "虚部", "U", "V", "UV 距离"),
}
_WORDS = {
    "en": {
        "x": "X axis",
        "y": "Y axis",
        "hide": "Hide flagged",
        "region": "Rectangle",
        "locate": "Locate rectangle",
        "clear": "Clear Locate",
        "reset": "Reset view",
        "empty": "No diagnostic preview · Locate selects displayed preview points only",
        "status": "Preview: {shown:,} displayed / {total:,} source samples · render cap {cap:,}",
        "selected": " · Locate: {total:,} displayed points; {details:,} detail records",
        "scope": " · selection applies only to displayed finite preview points; no flag writes",
        "uv": " · UVW unavailable for {count} group(s)",
        "channel": " · original channel IDs unavailable for {count} group(s)",
        "native": "native units",
        "mixed": "mixed native units",
        "group": "Group",
        "flagged": "Toggle flagged preview samples; stored flags remain unchanged",
        "sampled": " · evenly sampled before flag/finite filtering",
    },
    "zh": {
        "x": "X 轴",
        "y": "Y 轴",
        "hide": "隐藏已标记数据",
        "region": "矩形区域",
        "locate": "定位矩形内数据",
        "clear": "清除定位",
        "reset": "重置视图",
        "empty": "无诊断预览 · 定位仅选择当前显示的预览数据点",
        "status": "预览：显示 {shown:,} / {total:,} 个源样本 · 绘制上限 {cap:,}",
        "selected": " · 定位：{total:,} 个显示点；{details:,} 条详细记录",
        "scope": " · 仅选择当前显示的有限预览点；不写入标记",
        "uv": " · {count} 组缺少 UVW",
        "channel": " · {count} 组缺少原始通道 ID",
        "native": "原始单位",
        "mixed": "混合原始单位",
        "group": "组",
        "flagged": "切换已标记预览数据的显示；不更改存储的标记",
        "sampled": " · 先均匀抽样，再过滤标记及非有限值",
    },
}
_COLORS = ("#52cfb3", "#eeaa57", "#7aa6ff", "#ec7daf", "#b69bef", "#8ccf65", "#62cbdc", "#e47868")


class DiagnosticView(QWidget):
    """Independent grouped scatter view; numerical identifiers live in combo itemData."""

    located = pyqtSignal(list, int)
    focused_group = pyqtSignal(int)
    MAX_POINTS = 100_000
    MAX_RECORDS = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.language = "en"
        self.blocks = ()
        self._time_origin = 0.0
        self._source_count = 0
        self._groups = np.empty(0, dtype=np.int64)
        self._flat_indices = np.empty(0, dtype=np.int64)
        self._x = self._y = np.empty(0, dtype=float)
        self.selected_indices = np.empty(0, dtype=np.int64)
        self._selection_total = 0
        self._legend_samples = []
        self.x_combo, self.y_combo = QComboBox(), QComboBox()
        for identifier, label in zip(AXES, _AXIS_LABELS["en"], strict=True):
            self.x_combo.addItem(label, identifier)
            self.y_combo.addItem(label, identifier)
        self.y_combo.setCurrentIndex(AXES.index("AMP"))
        self.hide_flags = QCheckBox()
        self.hide_flags.setChecked(True)
        self.x_label, self.y_label = QLabel(), QLabel()
        self.region_button = QPushButton()
        self.region_button.setCheckable(True)
        self.locate_button = QPushButton()
        self.clear_selection_button = QPushButton()
        self.reset_button = QPushButton()
        controls = QHBoxLayout()
        for widget in (self.x_label, self.x_combo, self.y_label, self.y_combo, self.hide_flags):
            controls.addWidget(widget)
        controls.addStretch()
        actions = QHBoxLayout()
        for widget in (
            self.region_button,
            self.locate_button,
            self.clear_selection_button,
            self.reset_button,
        ):
            actions.addWidget(widget)
        actions.addStretch()
        self.plot = pg.PlotWidget()
        self.plot.setMinimumHeight(180)
        self.legend = self.plot.addLegend(offset=(10, 10))
        self.scatter = pg.ScatterPlotItem(pen=None, size=7, pxMode=True)
        self.selection_scatter = pg.ScatterPlotItem(
            pen=pg.mkPen("#fff1a8", width=2),
            brush=None,
            size=12,
            pxMode=True,
        )
        self.plot.addItem(self.scatter)
        self.plot.addItem(self.selection_scatter)
        self.roi = pg.RectROI((0, 0), (1, 1), pen=pg.mkPen("#fff1a8", width=2))
        self.roi.setZValue(20)
        self.plot.addItem(self.roi)
        self.roi.hide()
        self.plot.getViewBox().disableAutoRange()
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addLayout(controls)
        layout.addLayout(actions)
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.status_label)
        self.x_combo.currentIndexChanged.connect(lambda: self._axis_changed("x"))
        self.y_combo.currentIndexChanged.connect(lambda: self._axis_changed("y"))
        self.hide_flags.toggled.connect(self._rebuild)
        self.region_button.toggled.connect(self._toggle_region)
        self.locate_button.clicked.connect(self.locate_region)
        self.clear_selection_button.clicked.connect(self.clear_selection)
        self.reset_button.clicked.connect(self.reset_view)
        self.scatter.sigClicked.connect(self._clicked)
        self.roi.sigRegionChangeStarted.connect(lambda: self._clear_selection(False))
        self.set_language("en")
        self._update_controls()

    def set_blocks(self, blocks):
        """Replace preview blocks and reset view; discard all previous Locate identities."""
        self.blocks = tuple(blocks)
        origins = []
        for block in self.blocks:
            finite = np.asarray(block.times)[np.isfinite(block.times)]
            if finite.size:
                origins.append(float(finite.min()))
        self._time_origin = min(origins, default=0.0)
        self._source_count = sum(block.values.size for block in self.blocks)
        self._rebuild()
        self.reset_view()

    def clear(self):
        self.set_blocks(())

    def set_language(self, code):
        """Translate chrome only; preserve selected points, ranges and axis identifiers."""
        self.language = code if code in _WORDS else "en"
        words = _WORDS[self.language]
        for combo in (self.x_combo, self.y_combo):
            blocker = QSignalBlocker(combo)
            for index, label in enumerate(_AXIS_LABELS[self.language]):
                combo.setItemText(index, label)
            del blocker
        self.x_label.setText(words["x"])
        self.y_label.setText(words["y"])
        self.hide_flags.setText(words["hide"])
        self.hide_flags.setToolTip(words["flagged"])
        self.region_button.setText(words["region"])
        self.locate_button.setText(words["locate"])
        self.clear_selection_button.setText(words["clear"])
        self.reset_button.setText(words["reset"])
        self._set_axis_labels()
        self._update_legend()
        self._update_status()

    def _axis_values(self, identifier, block, rows, channels, values):
        if identifier == "TIME":
            return np.asarray(block.times)[rows] - self._time_origin
        if identifier == "FREQ":
            return np.asarray(block.frequencies)[channels] / 1e6
        if identifier == "CHAN":
            ids = getattr(block, "channel_ids", None)
            return np.full(len(rows), np.nan) if ids is None else np.asarray(ids)[channels]
        if identifier == "AMP":
            return np.abs(values)
        if identifier == "PHASE":
            phase = np.angle(values, deg=True)
            return np.where(np.abs(values) > 0, phase, np.nan)
        if identifier == "REAL":
            return values.real
        if identifier == "IMAG":
            return values.imag
        uvw = getattr(block, "uvw", None)
        if uvw is None:
            return np.full(len(rows), np.nan)
        uvw = np.asarray(uvw)
        if uvw.shape != (len(block.times), 3):
            return np.full(len(rows), np.nan)
        if identifier == "UVDIST":
            return np.hypot(uvw[rows, 0], uvw[rows, 1])
        return uvw[rows, 0 if identifier == "U" else 1]

    def _rebuild(self, *_):
        self._clear_selection(True)
        count = self._source_count
        # Evenly spaced original flat offsets keep peak work bounded by MAX_POINTS,
        # including when source blocks contain millions of samples.
        samples = (
            np.linspace(0, count - 1, min(count, self.MAX_POINTS), dtype=np.int64)
            if count
            else np.empty(0, dtype=np.int64)
        )
        group_parts, flat_parts, x_parts, y_parts = [], [], [], []
        offset = 0
        x_axis, y_axis = self.x_combo.currentData(), self.y_combo.currentData()
        for group, block in enumerate(self.blocks):
            size = block.values.size
            start, end = np.searchsorted(samples, (offset, offset + size))
            flat = samples[start:end] - offset
            offset += size
            if not flat.size:
                continue
            channels_count, correlations_count = block.values.shape[1:]
            rows = flat // (channels_count * correlations_count)
            channels = flat // correlations_count % channels_count
            correlations = flat % correlations_count
            values = block.values[rows, channels, correlations]
            x = np.asarray(self._axis_values(x_axis, block, rows, channels, values), dtype=float)
            y = np.asarray(self._axis_values(y_axis, block, rows, channels, values), dtype=float)
            valid = (
                np.isfinite(x)
                & np.isfinite(y)
                & np.isfinite(values.real)
                & np.isfinite(values.imag)
            )
            if self.hide_flags.isChecked():
                valid &= ~block.flags[rows, channels, correlations]
            group_parts.append(np.full(np.count_nonzero(valid), group, dtype=np.int64))
            flat_parts.append(flat[valid])
            x_parts.append(x[valid])
            y_parts.append(y[valid])
        self._groups = np.concatenate(group_parts) if group_parts else np.empty(0, np.int64)
        self._flat_indices = np.concatenate(flat_parts) if flat_parts else np.empty(0, np.int64)
        self._x = np.concatenate(x_parts) if x_parts else np.empty(0)
        self._y = np.concatenate(y_parts) if y_parts else np.empty(0)
        brushes = [pg.mkBrush(color) for color in _COLORS]
        self.scatter.setData(
            x=self._x,
            y=self._y,
            data=np.arange(len(self._x)),
            brush=[brushes[group % len(brushes)] for group in self._groups],
        )
        self._set_axis_labels()
        self._update_legend()
        self._update_controls()
        self._update_status()

    def _set_axis_labels(self):
        words = _WORDS[self.language]
        units = {block.unit for block in self.blocks}
        native = next(iter(units)) if len(units) == 1 else words["mixed"]
        if not native:
            native = words["native"]
        scales = {b.time_scale for b in self.blocks}
        scale = next(iter(scales)) if len(scales) == 1 else ""
        origin_title = ""
        for combo, position in ((self.x_combo, "bottom"), (self.y_combo, "left")):
            identifier = combo.currentData()
            label = _AXIS_LABELS[self.language][AXES.index(identifier)]
            unit = {
                "TIME": "s",
                "FREQ": "MHz",
                "CHAN": "",
                "PHASE": "deg",
                "U": "m",
                "V": "m",
                "UVDIST": "m",
            }.get(identifier, native)
            if identifier == "TIME":
                origin = f"{self._time_origin:.9f}".rstrip("0").rstrip(".")
                label += f" (MS TIME − {origin}; {scale.upper() or 'mixed scales'})"
                if scale and np.isfinite(self._time_origin):
                    stamp = Time(self._time_origin / 86400, format="mjd", scale=scale).isot
                    origin_title = f"{stamp} {scale.upper()}"
            self.plot.setLabel(position, label, units=unit)
            # Frequencies are already converted from Hz to MHz above.
            axis = self.plot.getAxis(position)
            axis.setSIPrefixEnableRanges(() if identifier == "FREQ" else None)
            axis.enableAutoSIPrefix(identifier != "FREQ")
        self.plot.setTitle(origin_title)

    @staticmethod
    def _row_identity(block, name, row):
        values = getattr(block, name, None)
        return int(values[row]) if values is not None and row < len(values) else None

    def _update_legend(self):
        # Preserve active LabelItems across translation/axis changes: Linux Qt
        # may still have resize events queued for them. Rebuild only on count changes.
        reuse = len(self.legend.items) == len(self.blocks)
        if not reuse:
            self.legend.clear()
            self._legend_samples = []
        for index, block in enumerate(self.blocks):
            label = f"{_WORDS[self.language]['group']} {index + 1} · DDID {block.ddid}"
            if len(block.row_ids):

                def identities(name, block=block):
                    array = getattr(block, name, None)
                    if array is None:
                        return "?"
                    unique = np.unique(array)
                    prefix = ",".join(str(int(v)) for v in unique[:4])
                    return prefix + ("…" if len(unique) > 4 else "")

                field = identities("field_ids")
                scan = identities("scan_numbers")
                ant1 = identities("antenna1")
                ant2 = identities("antenna2")
                label += f" · F {field} · S {scan} · {ant1}→{ant2}"
            if block.unit:
                label += f" · {block.unit}"
            if reuse:
                self.legend.items[index][1].setText(label, color=self.legend.labelTextColor())
            else:
                item = pg.ScatterPlotItem(pen=None, brush=pg.mkBrush(_COLORS[index % len(_COLORS)]))
                self._legend_samples.append(item)
                self.legend.addItem(item, label)

    def _update_status(self):
        words = _WORDS[self.language]
        if not self.blocks:
            self.status_label.setText(words["empty"])
            return
        status = words["status"].format(
            shown=len(self._x), total=self._source_count, cap=self.MAX_POINTS
        )
        if self._source_count > self.MAX_POINTS:
            status += words["sampled"]
        if self._selection_total:
            status += words["selected"].format(
                total=self._selection_total, details=min(self._selection_total, self.MAX_RECORDS)
            )
        if self.x_combo.currentData() in ("U", "V", "UVDIST") or self.y_combo.currentData() in (
            "U",
            "V",
            "UVDIST",
        ):
            missing = sum(getattr(block, "uvw", None) is None for block in self.blocks)
            if missing:
                status += words["uv"].format(count=missing)
        if "CHAN" in (self.x_combo.currentData(), self.y_combo.currentData()):
            missing = sum(getattr(block, "channel_ids", None) is None for block in self.blocks)
            if missing:
                status += words["channel"].format(count=missing)
        self.status_label.setText(status + words["scope"])

    def _update_controls(self):
        populated = bool(len(self._x))
        self.region_button.setEnabled(populated)
        self.locate_button.setEnabled(populated and self.roi.isVisible())
        self.clear_selection_button.setEnabled(bool(self._selection_total) or self.roi.isVisible())
        self.reset_button.setEnabled(populated)

    def _axis_changed(self, axis):
        """A new coordinate needs a new range; preserve the other axis's zoom."""
        self._rebuild()
        values = self._x if axis == "x" else self._y
        if len(values):
            self.plot.getViewBox().setRange(
                **{f"{axis}Range": (float(values.min()), float(values.max()))}, padding=0.08
            )

    def reset_view(self):
        """Fit both coordinates; translations and flag toggles preserve manual ranges."""
        if len(self._x):
            self.plot.getViewBox().setRange(
                xRange=(float(self._x.min()), float(self._x.max())),
                yRange=(float(self._y.min()), float(self._y.max())),
                padding=0.08,
            )
        self.plot.getViewBox().disableAutoRange()

    def _toggle_region(self, enabled):
        if enabled and len(self._x):
            (xmin, xmax), (ymin, ymax) = self.plot.getViewBox().viewRange()
            self.roi.setPos((xmin + (xmax - xmin) * 0.25, ymin + (ymax - ymin) * 0.25))
            self.roi.setSize(((xmax - xmin) * 0.5, (ymax - ymin) * 0.5))
            self.roi.show()
        else:
            self.roi.hide()
        self._update_controls()

    def _clear_selection(self, hide_region):
        self.selected_indices = np.empty(0, np.int64)
        self._selection_total = 0
        self.selection_scatter.setData(x=[], y=[])
        if hide_region:
            self.roi.hide()
            blocker = QSignalBlocker(self.region_button)
            self.region_button.setChecked(False)
            del blocker
        self.located.emit([], 0)
        self._update_controls()
        self._update_status()

    def clear_selection(self):
        self._clear_selection(True)

    def locate_region(self):
        """Select displayed samples inside the visible, unrotated rectangle (inclusive)."""
        if not self.roi.isVisible():
            return
        position, size = self.roi.pos(), self.roi.size()
        xmin, xmax = sorted((position.x(), position.x() + size.x()))
        ymin, ymax = sorted((position.y(), position.y() + size.y()))
        inside = (self._x >= xmin) & (self._x <= xmax) & (self._y >= ymin) & (self._y <= ymax)
        self.locate_indices(np.flatnonzero(inside))

    def locate_indices(self, indices):
        """Locate displayed point offsets; details are capped, total preserves all hits."""
        indices = np.asarray(indices, dtype=np.int64).ravel()
        indices = np.unique(indices[(indices >= 0) & (indices < len(self._x))])
        self.selected_indices = indices
        self._selection_total = len(indices)
        self.selection_scatter.setData(x=self._x[indices], y=self._y[indices])
        records = self.records_for_indices(indices)
        self.located.emit(records, len(indices))
        if len(indices) and np.unique(self._groups[indices]).size == 1:
            self.focused_group.emit(int(self._groups[indices[0]]))
        self._update_controls()
        self._update_status()

    def records_for_indices(self, indices):
        """Return at most MAX_RECORDS exact identities for displayed point offsets."""
        records = []
        for index in np.asarray(indices, dtype=np.int64).ravel()[: self.MAX_RECORDS]:
            if not 0 <= index < len(self._x):
                continue
            group, flat = int(self._groups[index]), int(self._flat_indices[index])
            block = self.blocks[group]
            _, channels, correlations = block.values.shape
            row = flat // (channels * correlations)
            channel, correlation = flat // correlations % channels, flat % correlations
            channel_ids = getattr(block, "channel_ids", None)
            labels = getattr(block, "correlation_labels", ())
            records.append(
                {
                    "group": group,
                    "row": int(block.row_ids[row]),
                    "channel": int(channel_ids[channel]) if channel_ids is not None else None,
                    "correlation": labels[correlation] if correlation < len(labels) else None,
                    "correlation_index": correlation,
                    "ddid": getattr(block, "ddid", None),
                    "field": self._row_identity(block, "field_ids", row),
                    "scan": self._row_identity(block, "scan_numbers", row),
                    "antenna1": self._row_identity(block, "antenna1", row),
                    "antenna2": self._row_identity(block, "antenna2", row),
                    "time": float(block.times[row]),
                    "frequency": float(block.frequencies[channel]),
                    "value": complex(block.values[row, channel, correlation]),
                    "flag": bool(block.flags[row, channel, correlation]),
                    "x": float(self._x[index]),
                    "y": float(self._y[index]),
                    "x_axis": self.x_combo.currentData(),
                    "y_axis": self.y_combo.currentData(),
                }
            )
        return records

    def _clicked(self, _scatter, points, event):
        self.locate_indices([point.data() for point in points])
        event.accept()
