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

后续普通鼠标操作录像使用窗口画面与坐标，避免反复扫描已知会触发该问题的表格辅助功能树。此录像只能验证所演示的常规操作，不能证明上游崩溃已经解决。当前版本仍是测试版。
