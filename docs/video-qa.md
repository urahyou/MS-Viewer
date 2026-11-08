# 原生录像检查（2026-11-08）

用户要求录制真实操作并检查问题。首段录像来自已安装 v0.2.0：180.008 秒、2940×1846 H.264，无麦克风/系统音频。回看了抽帧及原始操作；原始视频、复测视频和测试日志保存在本地忽略目录 artifacts/video，不随 GitHub 源码发布。

## v0.2.1 修复

1. TIME 切到 FREQ 后仍用旧时间轴范围，点落在视野之外。改为自动适配被更改的轴，另一轴的缩放保留；语言/Flag 显示切换不重置范围。
2. MHz 再被加上 k 前缀。明确禁用频率的二次 SI 缩放；PyQtGraph 0.14 的 enableAutoSIPrefix(False) 会用旧范围重算前缀，因此先设置空 SI 启用区间。依赖最低版本与所用公开 API 对齐。新增长时间跨度（2000 秒）回归实际复现过残留 kMHz。
3. 点击另一条 Locate 记录，详情仍显示第一条。改为行选择更新详情、原始通道/相关乘积、数据组、天线和三图光标；不重新读 MS，不清空整个 Locate，翻译保留当前行。

三项均有实际 RED→GREEN 测试。样本仍来自原始 MS ID；未修改可见度数值或 Flag。

## 尚未解决：macOS Qt 无障碍扫描崩溃

首次安装版复测在 20:01:18 触发一次进程 SIGSEGV。系统报告的主线程路径为 libqcocoa → NSAccessibilityAttributeAccessorInfo → accessibilityArrayAttributeCount → AXCopyHierarchy，无 Python 异常。不能据此声称常规操作或辅助功能完全稳定。

观察到的签名与 Qt 官方 [QTBUG-149612](https://qt-project.atlassian.net/browse/QTBUG-149612) 和原始报告 [Codex #41374](https://github.com/openai/codex/issues/41374) 描述的表格辅助功能生命周期问题相符；这是基于栈和上游证据的归因，尚未做禁用扫描的严格 A/B 实验。Qt 公开 issue API 在检查时列出修复版本 6.12.1，released=false；PyPI 可用最新版为 6.12.0。没有禁用辅助功能，也没有为录像临时更改原生库。

安装版再次通过自动化操作复测时，仍触发同类原生崩溃。因此没有把这段标作成功复测，也不把 189 项测试通过等同于安装版稳定。

随后用开发脚本 `scripts/record_native_qa.py` 在原生 Cocoa 窗口中启动当前源码，通过 Qt QTest 键盘/鼠标事件回放真实界面；macOS 按窗口录制画面，不读取辅助功能树。这是开发测试回放，不是人工操作，也不是冻结安装包的稳定性验证。没有重绘或合成界面。52.333 秒原始录像为 artifacts/video/msviewer-0.2.1-qt-replay.mov；分享版为 artifacts/video/02-after-fixes-native-qt-replay.mp4。

回放与抽帧确认频率范围 1346–1404 MHz、相位范围约 ±209 度、点击第三条 Locate 记录后详情更新到原始 row0/channel25/XX，保留 8584 命中/200 条详情、翻译保留选中行、天线图高亮基线 0→1。脚本使用独立 INI 设置，无 MS 写入。结果位于 artifacts/video/native-replay/results.json。该场景通过，不能证明上游崩溃已经解决；当前版本仍是测试版。

最终本地完整测试 189 项通过（28.03 秒，1 个既有模拟时间 ERFA 警告），Ruff 与格式检查通过；Linux CI 42478816830 在 fdfc73f 上通过。三处界面修复已包含在本地安装的 v0.2.1 中。
