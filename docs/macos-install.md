# MS Viewer for macOS

## 安装

1. 下载 MS-Viewer-0.1.2-macOS-arm64.dmg，双击打开。
2. 将 MS Viewer.app 拖到 Applications（应用程序）文件夹。
3. 从“应用程序”打开 MS Viewer；在“样例”中打开模拟、ALMA 或 BIMA 数据。
4. “语言 / Language”切换中英文，“帮助”中可打开内置 PDF 图解教程。

本包包含 Python、PyQt6、casacore 等运行环境，不需要另装 Python 或 Conda。
本次发布仅提供 Apple Silicon（M 系列）版本，实际测试系统为 macOS 27.2。
Intel Mac 和其他 macOS 版本尚未验证；不承诺这个 ARM64 包可在 Intel 上运行。

## 首次打开的系统提示

这是开源测试版，使用 ad-hoc 签名，未取得 Developer ID Application 发行签名，未经过 Apple 公证。
从浏览器下载后，macOS 可能阻止首次运行。只有在你确认下载来源是本仓库的情况下，
才按系统“设置 → 隐私与安全性”中的“仍要打开”流程操作。
官方说明：https://support.apple.com/en-us/102445
不要关闭整个系统的 Gatekeeper。

## 文件位置

- 观测数据：由你选择的原始 .ms 目录；查看器不修改 DATA 或 Flag。
- 内置样例的可写副本：~/Library/Application Support/MS Viewer/samples-v1/
- 启动错误日志：~/Library/Application Support/MS Viewer/logs/msviewer.log
- 语言偏好：Qt 的本机用户设置。

样例采用用户副本以容纳 casacore 的锁文件，避免修改已签名的应用包。
内置 PDF 和原始样例资源均随应用分发。Finder 可以通过“打开方式”把 .ms 交给查看器。
如要打开任意数据，也可在应用中点击“打开 Measurement Set…”选择目录。

## 从源码构建

```bash
conda env create --prefix ./.venv --file environment.yml
.venv/bin/python -m pip install -e '.[dev,macos]'
packaging/macos/build.sh
```

构建需要 Mac Apple Silicon、Apple 命令行工具（codesign/hdiutil）和项目中提供的 PDF。
构建脚本会下载已固定提交并验证 SHA256 的两个小型公开测试 MS，生成模拟 MS 并使用仓库附带的应用图标，
打包运行环境与许可证，然后验证签名并制作 DMG。
PyInstaller 的 Astropy 自定义 hook 用于避免引入不需要的可选绘图与测试模块。
项目以 GPL-3.0-only 发布，第三方许可证见 THIRD_PARTY_NOTICES.md 和应用资源目录。

当前本地 PyInstaller/Conda 构建锁定版本可见 packaging/macos/build-environment.txt。

图标重新生成脚本为 packaging/macos/make_icon.py，需要额外安装 Pillow；普通构建直接使用附带的 .icns，不需要 Pillow。
