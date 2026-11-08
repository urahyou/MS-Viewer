"""UI translations only; MeasurementSet identifiers and numerical data stay unchanged."""

from PyQt6.QtCore import QLibraryInfo, QTranslator
from PyQt6.QtWidgets import QApplication

CHINESE = {
    "Help": "帮助",
    "Open illustrated guide (PDF)…": "打开图解教程（PDF）…",
    "Could not open the tutorial": "无法打开教程",
    "Single-channel spectrum · {frequency:.6f} MHz": "单通道频谱 · {frequency:.6f} MHz",
    "Single channel · each row repeats the same channel horizontally": "单通道 · 每行横向为同一通道",
    "Only one frequency channel ({frequency:.6f} MHz). Horizontal colour is repeated; use the time trace to inspect variation.": "仅 1 个频率通道（{frequency:.6f} MHz）。每行横向颜色重复，建议查看时间曲线了解变化。",
    "Previous selection: {hint}": "上一筛选结果: {hint}",
    "{name} · MS Viewer": "{name} · MS 查看器",
    "MS Viewer · Visibility explorer": "MS 查看器 · 可见度浏览",
    "RADIO ASTRONOMY  /  VISIBILITY EXPLORER": "射电天文  /  可见度浏览器",
    "Open Measurement Set…": "打开 Measurement Set…",
    "Open an MS directory to begin · read-only": "打开 MS 目录开始浏览 · 只读",
    "Select a public sample from the Samples menu, or open your own MS.": "从“样例”菜单选择公开数据，或打开自己的 MS。",
    "DATA SELECTION": "数据筛选",
    "DDID / SPW": "DDID / 频谱窗",
    "Field": "观测目标",
    "Scan": "扫描",
    "Baseline": "基线",
    "Correlation": "相关乘积",
    "Column": "数据列",
    "Quantity": "显示量",
    "Time offset ≥": "时间偏移 ≥",
    "Time offset ≤": "时间偏移 ≤",
    "Channel start": "起始通道",
    "Channel end <": "结束通道 <",
    "Preview rows ≤": "预览行数 ≤",
    "Preview channels ≤": "预览通道数 ≤",
    "Start (seconds)": "起始时间（秒）",
    "End (seconds)": "结束时间（秒）",
    "Hide flagged samples": "隐藏已标记样本",
    "Apply selection": "应用筛选",
    "Baselines follow ANTENNA1 → ANTENNA2.\nCurves show unweighted preview means.\nPhase uses a circular mean.\nChannel end is exclusive; indices start at 0.": "基线方向为 ANTENNA1 → ANTENNA2。\n曲线显示预览样本的非加权平均。\n相位使用圆周平均。\n结束通道不包含在内；编号从 0 开始。",
    "Export plots as PNG…": "导出图像为 PNG…",
    "Frequency spectrum": "频谱",
    "Time trace": "时间曲线",
    "Frequency": "频率",
    "Seconds since first preview sample": "相对首个预览样本的时间（秒）",
    "Waterfall": "瀑布图",
    "Waterfall · hover for physical coordinates": "瀑布图 · 悬停查看实际坐标",
    "Preview channel index": "预览通道索引",
    "Preview row index (time sorted)": "预览行索引（按时间排序）",
    "Visibilities": "可见度",
    "MS metadata": "MS 元数据",
    "Waterfall axes are sample indices; hover to see frequency, time and original row.": "瀑布图坐标为样本索引；悬停查看实际频率、时间与原始行号。",
    "Ready · MS data are opened read-only": "就绪 · MS 数据以只读方式打开",
    "File": "文件",
    "Samples": "样例",
    "Open MS directory…": "打开 MS 目录…",
    "Export plots…": "导出图像…",
    "Choose a Measurement Set directory": "选择 Measurement Set 目录",
    "Export visibility plots": "导出可见度图",
    "PNG image (*.png)": "PNG 图像 (*.png)",
    "Opening {name}…": "正在打开 {name}…",
    "This MS has no readable visibility data or is empty": "此 MS 为空，或没有可读取的可见度数据",
    "{telescope}   /   {rows:,} rows   /   {antennas} antennas   /   {ddids} DDIDs": "{telescope}   /   {rows:,} 行   /   {antennas} 天线   /   {ddids} 个 DDID",
    "Path: {path}": "路径: {path}",
    "Telescope: {telescope}": "望远镜: {telescope}",
    "Rows: {rows:,}": "行数: {rows:,}",
    "Data columns: {columns}": "数据列: {columns}",
    "(none)": "（无）",
    "ANTENNAS": "天线",
    "FIELDS": "观测目标",
    "DATA DESCRIPTIONS": "数据描述",
    "DDID {ddid} → SPW {spw}, POL {pol}, {channels} channels, {correlations}": "DDID {ddid} → 频谱窗 {spw}，偏振配置 {pol}，{channels} 通道，{correlations}",
    "TIME ({scale}):": "时间（{scale}）:",
    "All fields": "全部目标",
    "All scans": "全部扫描",
    "Amplitude": "振幅",
    "Phase": "相位",
    "Real": "实部",
    "Imaginary": "虚部",
    "Selection changed · updating preview…": "筛选已更改 · 正在更新预览…",
    "Reading visibility preview…": "正在读取可见度预览…",
    "Time trace · {first} {scale}": "时间曲线 · {first} {scale}",
    "Preview: {rows:,} / {total:,} selected rows × {channels:,} channels · flagged {flagged:.1%} · means use preview samples; no weights applied · read-only": "预览: {rows:,} / {total:,} 筛选行 × {channels:,} 通道 · 标记比例 {flagged:.1%} · 预览样本的非加权平均 · 只读",
    "{title} · previous selection": "{title} · 上一筛选结果",
    "MS row {row}  |  {time} {scale}  |  {frequency:.6f} MHz  |  {value:.5g} {unit}": "MS 行 {row}  |  {time} {scale}  |  {frequency:.6f} MHz  |  {value:.5g} {unit}",
    "Error: {error}": "错误: {error}",
    "Could not save the plot image": "无法保存图像",
    "Finishing active read before closing…": "正在等待当前读取完成，然后关闭…",
    "Unsupported TIME unit: expected seconds since MJD 0": "不支持的 TIME 单位：应为从 MJD 0 起算的秒数",
    "Variable TIME reference frames are not supported": "暂不支持可变的 TIME 参考系",
    "Preview row/channel limits must be positive": "预览行数和通道数上限必须为正数",
    "Time bounds must be finite": "时间范围必须为有限数值",
    "Start time must not exceed end time": "起始时间不能晚于结束时间",
    "No rows match this selection": "没有符合当前筛选条件的数据行",
    "Visibility shape does not match SPW/polarization metadata": "可见度数据形状与频谱窗/偏振元数据不一致",
}

ERROR_PREFIXES = {
    "Not a Measurement Set directory: ": "不是有效的 Measurement Set 目录: ",
    "Invalid selection: ": "筛选条件无效: ",
    "Cannot inspect MS: ": "无法检查 MS: ",
    "Cannot read MS selection: ": "无法读取筛选后的 MS: ",
    "Unsupported TIME reference: ": "不支持的 TIME 参考系: ",
    "Invalid DATA_DESC_ID: ": "无效的 DATA_DESC_ID: ",
    "Data column unavailable: ": "数据列不可用: ",
    "Channel bounds must satisfy 0 <= start < end <= ": "通道范围必须满足 0 ≤ 起始通道 < 结束通道 ≤ ",
    "could not convert string to float: ": "无法将输入转换为数值: ",
}


def text(source: str, language: str, **values) -> str:
    return (CHINESE.get(source, source) if language == "zh" else source).format(**values)


def error_text(message: str, language: str) -> str:
    if language != "zh":
        return message
    if message in CHINESE:
        return CHINESE[message]
    for prefix, translated in ERROR_PREFIXES.items():
        if message.startswith(prefix):
            return translated + error_text(message[len(prefix) :], language)
    return message  # Preserve third-party diagnostics verbatim.


class _ChineseQtTranslator(QTranslator):
    """Fill gaps in the Chinese catalog shipped with newer Qt releases."""

    def translate(self, context, source_text, disambiguation=None, n=-1):
        supplements = {
            "Look in:": "查找位置:",
            "&Look in:": "查找位置:",
            "Files of type:": "文件类型:",
            "Files of &type:": "文件类型:",
            "Folder": "文件夹",
        }
        if source_text in supplements:
            return supplements[source_text]
        return super().translate(context, source_text, disambiguation, n)


def install_qt_language(language: str):
    """Use Qt's bundled translations for standard dialogs, with one translator per app."""
    app = QApplication.instance()
    translator = getattr(app, "_msviewer_qt_translator", None)
    if translator is None:
        translator = _ChineseQtTranslator(app)
        translator.load(
            "qtbase_zh_CN", QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        )
        app._msviewer_qt_translator = translator
    app.removeTranslator(translator)
    if language == "zh":
        app.installTranslator(translator)
