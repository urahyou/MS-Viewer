# CASA 源码与现代化设计参考

调研日期：2026-11-08。用途：确定 MS Viewer 的功能与架构清单，不实施产品修改。本次是有界源码抽查，不是 CASA 全库审计。仅使用 NRAO 官方仓库、casangi 官方仓库及其随库设计文档；源码内容通过官方 Bitbucket REST raw 和 GitHub raw 读取。

## 证据范围与固定版本

| 仓库 | 本次读取的提交 |
| --- | --- |
| CASAplotms | `21f8f460b94adaf858c56d7c73740bafadf1cee7` |
| casa6 | `90e9d3dae95594cbf9d4641b36e9ffc3bfe67d3e` |
| casatablebrowser | `fa0cac90fa6316f3dc6dfbd3e2012610b47cfe8c` |
| CASAviewer | `e0b61318f1342c67956f87f4aeb7a705fde56246` |
| casangi/casagui | `17786787f288b46766fa8b29ae80f35c3bf4db4c` |

以下“源码事实”仅说明已读文件直接支持的行为或接口；“设计文档”表示目标/原则；“建议”是针对本软件的推导，不声称 CASA 已按同样方式完成。未运行 CASA，也未验证其全部依赖、版本兼容性或功能完整性。

## 八组可追溯参考

### 1. PlotMS：先定义科学参数，再呈现控件

**源码事实：** `PlotMSSelection` 用稳定字段枚举表示 field、spw、timerange、uvrange、antenna、scan、corr、array、observation、intent、feed、msselect；`PlotMSAveraging` 将 channel/time 的开关与数值，以及 scan/field/baseline/antenna/spw/scalar 分别建模。不是靠 GUI 标签决定计算含义。见 [PlotMSSelection.h，第 50–64、120–150 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/PlotMS/PlotMSSelection.h?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[PlotMSAveraging.h，第 37–55、123–150 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/PlotMS/PlotMSAveraging.h?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)。

**建议：** PyQt6 以独立 `SelectionSpec`、`AverageSpec` 保存机器标识、参数和单位，控件只编辑这些值。提供常用选择器和高级表达式两个入口；不能把尚未实现的 CASA 表达式当作完整兼容功能宣传。

### 2. PlotMS：轴、迭代、颜色是相互独立的维度

**源码事实：** `PMS::Axis` 覆盖时间、频率、速度、通道、相关、天线、基线、行、振幅、相位、实虚部、权重、flag 等；`PlotMSIterParam` 独立保存迭代轴、全局缩放和共用坐标轴；Python task 分别调用 `setColorize`、`setPlotMSIterate`，并有单独的 flagged symbol。见 [PlotMSConstants.h，第 109–135 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/PlotMS/PlotMSConstants.h?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[PlotMSIterParam.h，第 62–79 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/PlotMS/PlotMSIterParam.h?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[task_plotms.py，第 663–685、765–819 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/module/private/task_plotms.py?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)。

**建议：** 统一绘图描述，分开 X/Y、数据列、颜色分组、分面/迭代与 flag 显示；不必一次移植所有轴。先实现本软件可准确读取和解释的坐标，并把频率参考系、速度定义、静止频率列为高级科学变换。

### 3. PlotMS：Locate 和 Flag 是不同操作

**源码事实：** `ActionLocate::doFlagOperation` 虽沿用父类方法名，实际调用 `plot->locateRange(...)`；`FlagActionUtil::flagRange/unflagRange` 调用 `plot->flagRange(..., true/false)`；`MSCache::flagToDisk` 是明确的磁盘标记路径。不能因它们共用选区交互而将 locate 与写 flag 混为一谈。见 [ActionLocate.cc，第 45–58 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/Actions/ActionLocate.cc?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[FlagActionUtil.h，第 42–55 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/Actions/FlagActionUtil.h?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[MSCache.cc，`MSCache::flagToDisk`，第 2198 行起](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/Data/MSCache.cc?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)。

**建议：** 当前产品实现框选定位、行/通道/相关回溯、flag 可视化、候选标记清单导出；保持 reader 只读。平均或抽样后的显示点必须能说明对应原始数据范围。真正 flag/unflag 属于另一个执行边界和后续产品决策。

### 4. PlotMS：导出是可配置任务，有完成条件

**源码事实：** `ActionExport::exportText` 提供文本导出路径；图像路径设置 DPI、宽高后交给 `ExportThread`；task 在绘制未完成时等待后才导出。见 [ActionExport.cc，第 70、347–411 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/code/plotms/Actions/ActionExport.cc?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[task_plotms.py，第 915 行附近](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/module/private/task_plotms.py?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)。

**建议：** PNG/CSV 与绘图参数 JSON 一起形成可复查输出；导出注明实际选择、平均、单位、flag 口径、抽样与点数。用户修改参数或读请求被新一代替代后，不应静默导出旧结果。

### 5. Table Browser：页、类型、关键字、数组分别处理

**源码事实：** `TBTable` 提供总行数/已加载行数、页、字段、表关键字、`loadRows(start, number, full, columns, ...)` 和 `loadArray(row,col)`；`TBDataItem::operator<` 按 double/date/float/int 等类型排序，而非统一按字符串排序。它同时具备编辑接口，因此只能借鉴读取模型，不能直接认为整套浏览器只读。见 [TBTable.h，第 172–245、269–282 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casatablebrowser/browse/src/code/casaqt/QtBrowser/TBTable.h?at=fa0cac90fa6316f3dc6dfbd3e2012610b47cfe8c)、[TBDataTab.cc，第 52–100 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casatablebrowser/browse/src/code/casaqt/QtBrowser/TBDataTab.cc?at=fa0cac90fa6316f3dc6dfbd3e2012610b47cfe8c)。

**建议：** PyQt6 用分页/按需加载的 `QAbstractTableModel` 展示 MAIN 与子表；数组单元格先显示 shape/type，点开才加载切片；独立字段/列关键字面板。大表全表排序与过滤应放在后台读取层，不能只对当前页排序却让用户误以为覆盖全表。

### 6. CASAviewer：控制显示的 API 与数据处理分开

**源码事实：** `grpcImageViewer` 暴露 panel、axes、load/reload/unload、colormap、datarange、contourlevels、channel、zoomlevel/zoombox、output、interactivemask 等 RPC。此次只读了声明，不代表验证了每个 RPC 的实现或兼容性。见 [grpcViewerAdaptor.qo.h，第 67、160–259 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaviewer/browse/src/code/display/QtViewer/grpcViewerAdaptor.qo.h?at=e0b61318f1342c67956f87f4aeb7a705fde56246)。

**建议：** 可借鉴色阶、切片、通道播放、区域、显示与导出命令的组件划分。图像立方体/WCS/轮廓是后续独立模块，不应与 MS 可见度 scatter/raster 视图混成一个未经定义的数据模型。

### 7. CASA 的任务/GUI 边界已能在源码中看到

**源码事实：** `plotmstool.py` 用 `Popen` 启动独立 PlotMS 进程，并通过 gRPC stub 调用选择、平均、变换、颜色、保存等；`casa6` 的 `task_flagdata.py` 调用 `agentflagger`，处理 flag backup，且区分 apply 与非 apply 的写标记路径。见 [plotmstool.py，第 134–210、258–266、476–650、930 行起](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/module/private/plotmstool.py?at=21f8f460b94adaf858c56d7c73740bafadf1cee7)、[task_flagdata.py，第 158–160、281–282、327–335 行](https://open-bitbucket.nrao.edu/projects/CASA/repos/casa6/browse/casatasks/src/private/task_flagdata.py?at=90e9d3dae95594cbf9d4641b36e9ffc3bfe67d3e)。

**建议：** 本软件继续直接负责只读表读取与轻量可视化；若以后需要校准、成像、数据重写、科学参考系变换或 flag 落盘，优先做可选 CASA 环境/独立进程适配器，调用公开 task/tool/process API，不在 PyQt 绘图事件里重写科学算法。gRPC 是 CASA 现有实现事实，并不意味着本软件立即需要新增 gRPC 依赖。

### 8. casagui：新方向可借鉴，但仍需区分原型与成熟产品

**源码事实：** 固定提交的 README 自称 pre-alpha/prototype，说明 Qt/DBus→gRPC 的历史与 Bokeh/Python、小组件复用方向。`MsRaster` 的真实 Python 源码已有 `plot`、样式、selection、aggregation、iteration、save 等入口，绘图参数与 selector 控件分开。见 [readme.rst](https://github.com/casangi/casagui/blob/17786787f288b46766fa8b29ae80f35c3bf4db4c/readme.rst)、[_ms_raster.py，第 22–95、95–166、197–214、389–405 行](https://github.com/casangi/casagui/blob/17786787f288b46766fa8b29ae80f35c3bf4db4c/casagui/apps/_ms_raster.py)。

**设计文档：** CASA/Viz Boundary 主张处理逻辑与 GUI 分离，消息/结果可序列化，处理层可单独测试；以 `gclean` 和 `tclean`/`deconvolve` 展示这一边界。远程 kernel 是该设计文档描述的模型，本次没有验证其产品可用性。见 [boundary.rst，第 31–77、88–121 行](https://github.com/casangi/casagui/blob/17786787f288b46766fa8b29ae80f35c3bf4db4c/docs/source/design/boundary.rst)。

**建议：** 保留 PyQt6，在内部做到输入规格、读取/归约、视图组件和任务执行分层；可借鉴可序列化状态、可脚本重放和小组件，不应因“现代化”就立即换成 Bokeh/Electron，或把 casagui 当作完整 PlotMS 替代品。

## 可融合的十项设计清单（本软件建议，尚未实施）

| 优先顺序 | 设计项 | 现代化落点/验收方向 | 来源 |
| --- | --- | --- | --- |
| 1 | 统一选择规格 | 界面选择与参数摘要一致；机器 ID 不随中文/英文切换改变 | 1 |
| 2 | 可解释的轴与数据列 | 振幅/相位/实虚、时间/频率/UV 等按能力逐项开放；单位和原始列明确 | 2 |
| 3 | flag 与权重检查 | flagged/unflagged 分层显示，统计分母、FLAG_ROW 与单点 FLAG 口径明确 | 2、3 |
| 4 | Locate/数据溯源 | 框选后查看原始行、基线、SPW、通道、相关，含平均点来源 | 3 |
| 5 | MAIN/子表浏览 | 分页、列类型与关键字、数组切片；始终只读 | 5 |
| 6 | 平均与抽样的分别建模 | 时间/通道平均先行；向量/标量、flag/weight/缺测策略必须有真实表测试 | 1 |
| 7 | 对比与迭代视图 | 按天线/基线/场/SPW/scan 翻页或分面；共用范围、颜色语义稳定 | 2 |
| 8 | 可重现导出与会话 | 图/数值/参数共同导出，记录抽样；保存与恢复视图状态 | 4、8 |
| 9 | 按结果预算读取 | 读请求与结果一一对应；后台分块、取消/过期请求隔离、缓存按规格失效 | 5、8；具体方案为本项目推导 |
| 10 | 可选科学任务适配器 | 后续调用 CASA tasks/process API，返回日志/结果；不扩大当前只读 reader 权限 | 7、8 |

“旗舰功能全覆盖”不是本轮清单目标。自动 RFI 标记、校准/成像、图像立方体、远程计算、大规模分布式后端应另立阶段；不能从几个接口的存在推断工程量小。

## 许可证事实与复用输入

CASAplotms 的 [src/module/LICENSE.txt](https://open-bitbucket.nrao.edu/projects/CASA/repos/casaplotms/browse/src/module/LICENSE.txt?at=21f8f460b94adaf858c56d7c73740bafadf1cee7) 和 casatablebrowser 的 [src/casatablebrowser/LICENSE.txt](https://open-bitbucket.nrao.edu/projects/CASA/repos/casatablebrowser/browse/src/casatablebrowser/LICENSE.txt?at=fa0cac90fa6316f3dc6dfbd3e2012610b47cfe8c) 是 GNU Library General Public License Version 2 文本；已读 PlotMS 文件头写有 version 2 or later。casagui 根目录 [LICENSE](https://github.com/casangi/casagui/blob/17786787f288b46766fa8b29ae80f35c3bf4db4c/LICENSE) 是 GNU Lesser General Public License Version 2.1 文本。这只是已读文件的事实，不是对所有组件授权或兼容性的结论。若未来直接复制/翻译源码、打包库或带入第三方资源，需要逐项记录原文件、版本、版权与依赖；本轮清单以设计借鉴为主。

## 尚未验证的边界

- 没有运行 CASA GUI、对比科学数值、测试 gRPC 生命周期或安装 CASA 依赖。
- CASAplotms 的 `src` 文件清单、casatablebrowser 文件清单以及 casagui Git tree 本次返回完整；casa6/CASAviewer 根文件列表有后续页，本次只针对上述确切文件读取，不作全仓库负面或完整性判断。
- 未完成 CASAviewer 全部图像渲染、WCS、区域与像素算法追踪；只验证 RPC 声明。未检验 casagui MsRaster 的性能、远程能力、写 flag 能力或生产稳定性。
- 本子任务未探查本地代码图：父任务报告当前工具列表没有 graph MCP 工具，无法给出 project/generation/coverage 声明。本文不对本地实现覆盖率作结论。
