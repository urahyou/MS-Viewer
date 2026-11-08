# macOS Application and Repository Release Plan

**Goal:** Publish the existing viewer to urahyou/MS-Viewer and deliver/install a tested Apple Silicon .app with a drag-to-Applications DMG.
**Architecture:** PyInstaller onedir windowed bundle, bundled offline sample assets and tutorial; copy bundled MS examples into a writable per-user cache before opening, preserving the app signature. Finder entry point supports file-open events and logs startup failures.
**Tech Stack:** Existing Python/PyQt6/casacore stack, PyInstaller, codesign, hdiutil, Git/gh.

- [x] TDD resources: frozen/source lookup, sample copying without overwrite, resource-independent CWD, PDF help; retain RED/GREEN.
- [x] App entry point: no relative imports, Finder file-open handling and logging; TDD.
- [x] Bundle all required casacore native libraries, Qt plugins/translations, sample data, PDF and notices. Create a native app icon using vector drawing.
- [x] Full tests/lint; build app and verify with environment variables removed and unrelated CWD; read both actual bundled public MS examples and test native GUI.
- [x] Build/check DMG, install by copying app to /Applications, open and verify selected MS in installed application.
- [ ] Repository hygiene, third-party notices, installation/build documentation and CI; commit and push without forcing remote history.
- [ ] Create GitHub release with DMG and SHA256; verify uploaded artifacts and final repository state.

Fresh repo has no commits or existing tracked work to isolate; operate in the user-requested project. No graph MCP tools available, so source fallback is used. User explicitly authorizes upload, packaging and installation. Do not delete or replace a pre-existing installed app without preserving it. No Developer ID Application identity/notarization credentials were found; development signing identity is not used for public release. Use an explicit ad-hoc signature and accurately document Gatekeeper behavior.
