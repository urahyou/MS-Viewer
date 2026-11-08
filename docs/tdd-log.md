# TDD development log

Fresh project in the requested directory; no existing Git checkout/worktree to isolate.
No codebase graph tools are available; source fallback applies.
The user requested implementation with TDD; execute in place without a separate plan approval stop.

- Task 1 RED: artifacts/01-processing-red.txt (7 missing-module failures); GREEN: artifacts/02-processing-green.txt (7 passed; bootstrap Python lacked pytest-qt, so a temporary config warning was present).
- Task 2 RED: artifacts/03-reader-red.txt (16 missing-reader failures); GREEN: artifacts/04-reader-green.txt (23 passed, actual casacore MS fixtures, no warnings).
- Apple Silicon dependency install initially failed downloading an unnecessary Qt5/LLVM dependency; retried with a minimal Conda casacore environment plus pip PyQt6, successfully.
- Demo RED: artifacts/05-demo-red.txt (2 missing-module failures); initial implementation exposed casacore nested-list writes, traced to POSITION/phase-direction arrays and changed to NumPy arrays; GREEN artifacts/06-demo-green.txt (25 passed).
- GUI RED: artifacts/07-window-red.txt (8 missing-module failures); GREEN artifacts/08-window-green.txt (8 real Qt integration tests passed).
- Downloader/CLI RED: artifacts/09-datasets-cli-red.txt (11 failed, 2 public-data tests skipped before extraction); GREEN artifacts/10-datasets-cli-green.txt (44 passed, 2 skipped).
- Public sample archives match the upstream pinned Git blob SHA1s as well as recorded SHA256; safe extraction completed. Actual ALMA/BIMA metadata in artifacts/*-metadata.json.
- Full suite after public downloads: artifacts/11-full-suite.txt (46 passed); formatted suite artifacts/12-formatted-suite.txt (46 passed). Lint passes after import/format cleanup and explicit worker exception boundary.
- Independent read-only review used the requesting-code-review skill. Three findings: opening priority, old DDID block rendered using new correlation labels, and unusable metadata replacing previous results. Regression RED artifacts/13-review-regressions-red.txt (3 failed, 9 passed); GREEN artifacts/14-review-regressions-green.txt (50 passed).
- Corrective design: disable/guard old selectors during open; invalidate rendering when selection changes, label retained plots as previous selection; commit new metadata only when usable. All important review findings addressed.
- Visual native-Qt QA rendered simulated (96×96×4), ALMA (23×64×4), BIMA (54×64×1) previews; screenshots in artifacts/*-preview.png. Frequency auto-prefix issue reproduced by test (Frequency kMHz) in artifacts/15-visual-regressions-red.txt; explicitly retain MHz. Added explicit waterfall bounds and scrollable selection controls; artifacts/16-final-suite.txt (52 passed).
- Scientific edge cases RED artifacts/17-phase-undefined-red.txt (2 failed, 7 passed): zero visibilities and exactly opposite phases produced artificial finite phases. Exclude zero visibility phase and mark near-zero resultant circular means undefined.
- Final GREEN artifacts/18-final-suite.txt: 54 passed, 0 skipped, no warnings. artifacts/ruff-final.txt: All checks passed. artifacts/format-final.txt: 17 files already formatted.
- Wheel build succeeded (artifacts/wheel-build.log); inspected archive includes application entry point and pinned sample catalog. Data/venv/build outputs ignored by Git.
- Remaining limits: no TB-scale benchmark, no exhaustive malformed-MS or cross-platform certification, no calibration/weighting/flag writes. Native GUI and dependencies verified on this macOS arm64 host.

## 2026-11-07: 中英文切换
- RED: artifacts/19-language-red.txt — 8 tests fail because switching/persistence is absent.
- GREEN: artifacts/20-language-green.txt — 8 pass; artifacts/21-language-suite.txt — full 62 pass.
- Implemented i18n.py dictionary, exclusive 中文/English menu, real QSettings persistence, stable quantity itemData, source-preserving dynamic statuses, metadata and axes translation without reread/replot.
- Tests isolate real QSettings in temporary INI directories so developer/user preferences are not modified by the suite.
- Independent bounded review approved; independently reran 62 tests. No actionable language-switching findings.
- Native Qt screenshots: artifacts/chinese-preview.png, english-preview.png and chinese-dialog.png. Found two English labels missing in Qt's bundled Chinese catalog; reproduced RED in artifacts/22-dialog-labels-red.txt and supplemented the Qt translator. GREEN: artifacts/23-language-final-tests.txt — 9 language tests pass.
- Final full suite: artifacts/24-language-full-suite.txt — 63 passed, no skips. Ruff and format reports: artifacts/language-ruff.txt, language-format.txt. Wheel rebuilt in artifacts/language-wheel-build.log.

## 2026-11-07: 单通道截图诊断
- Reproduced the user's exact ALMA selection: DDID 2 / SPW 2 / DA41→DV14 / XX / DATA / Imaginary.
- Actual block: 23 rows × 1 channel × 4 correlations, frequency 85290.3049999 MHz; first eight rows fully flagged, first valid sample at +96.192 s. Spectrum mean is 2.12836584e-5, so its absence was a plotting issue, not absence of finite data.
- RED artifacts/25-single-channel-red.txt: four regressions fail for missing visible point, retained old frequency viewport, absent single-channel guidance and language handling.
- Fix: mark isolated finite samples, fit new selections, focus single-frequency x extent, bilingual single-channel titles/hint; no backend numerical changes.
- Native QA then exposed a single-value y range retaining an old large extent. RED artifacts/27-single-value-scale-red.txt; center/pad single-value y bounds and re-enable normal y autorange for multiple finite values.
- GREEN artifacts/28-single-channel-final-suite.txt: 68 passed; Ruff and format checks pass. Native exact-selection evidence: artifacts/single-channel-fixed.png, single-channel-native.log. Updated wheel built successfully.

## 2026-11-08: macOS 打包与仓库发布
- Resources RED artifacts/29-resources-red.txt: 8 failures; GREEN artifacts/30-resources-green.txt: 76 passed.
- Finder router RED artifacts/31-desktop-red.txt: 2 missing-module failures. Qt's native QFileOpenEvent constructor is private; use a protocol test double for that boundary, with Finder launch verified on the built app; external FileOpen delivery remains covered by the protocol boundary test.
- A full-suite attempt once encountered a Qt AxisItem deletion/segfault during offscreen painting. A subsequent verbose full run completed: artifacts/33-source-full-suite.txt, 78 passed. Independent review found no concrete new lifecycle defect. Retain this observation rather than suppressing it.
- Astropy's upstream PyInstaller hook imported optional wcsaxes and triggered pytest.importorskip(matplotlib); custom hook collects runtime modules and data while excluding visualization/tests.
- Independent packaging review found one minor macOS concurrent-copy race (ENOTEMPTY); regression RED artifacts/34-sample-race-red.txt, fix checks both EEXIST/ENOTEMPTY and validates destination. A further offscreen Qt crash occurred in artifacts/35-release-source-suite.txt; the subsequent completed source run is recorded below.
- Public repository, GPL-3.0-only project license and dependency notices prepared; no credentials or signing keys included.
- The native FileOpenEvent test double originally inherited QEvent with the native FileOpen type. Since Qt's constructor is private, changed it to a plain protocol object rather than synthesizing a native event. The current full source run completed 79 tests (artifacts/36-release-source-suite.txt).
- Final PyInstaller bundle: arm64 Mach-O, approximately 239 MB, ad-hoc deep/strict signature verification passes. Clean-environment frozen executable read ALMA from /tmp without activated Conda: artifacts/frozen-alma-inspect.json.
- Native bundle and installed app are verified separately; signing identity is ad-hoc, not the local personal Apple Development certificate.

- Installed-app QA exposed a startup hang: native sampling showed libcrypto opening Conda's absolute build-prefix openssl.cnf while importing hashlib. OPENSSL_CONF=/dev/null isolated the cause. RED artifacts/37-openssl-red.txt; bundled configuration/runtime hook GREEN artifacts/38-openssl-green.txt. Explicit user OPENSSL_CONF overrides remain respected.
- Native offline-demo QA exposed empty subtables after deleting table.lock from staged assets. casacore uses synchronization state in that file; preserve complete sample directories and open only per-user copies. Scientific metadata regression RED artifacts/41-staged-metadata-red.txt (ANTENNA rows 0 versus 3); GREEN artifacts/42-runtime-staging-green.txt.
- Final full source suite artifacts/43-final-release-tests.txt: 82 passed. Ruff and format checks pass in artifacts/44-release-lint.txt.
- Final installed app launched via LaunchServices without environment overrides. Native UI loaded all three offline examples: simulated 576 rows / 3 antennas / 2 DDIDs; ALMA 1,058 / 13 / 2; BIMA 14,985 / 10 / 6. Chinese switching and 21-page bundled guide.pdf opened successfully in the system PDF application (WPS).
- Deep/strict signature verification still passes after sample use, confirming that writable copies leave the signed bundle unchanged. Frozen BIMA inspection also passed from /tmp with Conda/Python/Qt search environment cleared (artifacts/frozen-bima-inspect.json).
- DMG creation and hdiutil checksum verification passed; read-only mount contains the app, Applications symlink and install guide. Mounted app passes codesign deep/strict verification and its executable matches the tested installed build.
