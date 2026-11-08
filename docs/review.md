# Independent review and corrections

A fresh, read-only reviewer inspected all application modules, tests, packaging, plan and spec.
The initial verdict requested changes despite the original 46 tests passing.

1. P1: old selectors could invalidate a pending open. Added a gated-worker reproduction;
   old selectors are now disabled and read/schedule methods guard open priority.
2. P1: old visibility block could be rendered under new DDID correlation labels. Added a
   gated DDID-change reproduction; rendering only proceeds when the accepted block matches
   the current selection generation. Previous results remain explicitly labeled until replaced.
3. P2: missing visibility columns could clear a previous valid dataset. Added actual MS
   fixtures with removed DATA or zero rows; new metadata is validated before changing UI state.

All findings were fixed via observed RED→GREEN regression tests. No important findings remain
unaddressed from that review. The reviewer did not certify exhaustive casacore memory behavior,
all malformed-MS variants, all dependency/platform versions, or live network provenance.
Those limits are retained in README; no such certification is claimed.

Additional direct visual QA caught MHz auto-prefix presentation and confirmed native rendering
of all three sample datasets. Final suite: 54 passing tests. See docs/tdd-log.md for evidence.

## 中英文切换审查

A separate fresh, read-only reviewer examined i18n.py, language integration in window.py,
settings isolation and language tests. Verdict: approve, no actionable findings. Independently
verified all 62 tests at that stage. Subsequent native dialog QA found missing upstream Qt
labels; added a failing regression and translator supplements. Final suite: 63 passing tests.

## v0.2.0 modern workbench review

Bounded source review includes newly added/untracked modules as well as tracked diffs. Initial approval with one LOW inconsistency: boolean antenna IDs accepted by baseline validation. Fixed via RED→GREEN regression. Parent also reproduced and fixed quick-preview residual rejection and old-focus reactivation after a grouped-filter draft edit; follow-up review found no blocker. Reader remains readonly, grouped queries retain original scientific identities with global budgets, and Locate maps only displayed sampled points. Reviewer inspected artifacts but lacked casacore for independent execution. Parent final suite: 186 passed; Ruff/format clean. Native package QA recorded in docs/tdd-log.md.
