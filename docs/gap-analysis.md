# Funscript Forge — Gap Analysis

*Last updated 2026-03-10 against `main` (v0.5.0).*

Items marked **[GH#N]** have a corresponding GitHub issue.
Items marked ✅ are resolved in the current codebase.

---

## Production Blockers — All Resolved ✅

| # | Title | Status | GitHub |
| --- | --- | --- | --- |
| G01 | Position boundary validation | ✅ `_clamp_sort_dedup()` clamps every pos to [0, 100] before export | [#9] |
| G02 | Timestamp continuity check | ✅ Same call sorts and deduplicates (last-write wins) | [#10] |
| G03 | Input validation + graceful errors | ✅ Malformed files produce user-facing messages, not tracebacks | [#11] |
| G04 | Transform parameter logging | ✅ `_forge_log` key embedded in every downloaded funscript | [#12] |
| G05 | Automated quality gate | ✅ `_check_quality()` checks velocity (warn > 200, error > 300) and short intervals (warn < 50 ms) | [#13] |
| G06 | Progress indicator for large files | ✅ `progress_callback` streams stage labels in real time during assessment | [#14] |
| G07 | Undo / redo for accepted transforms | ✅ 50-level undo/redo; Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z | [#15] |

---

## High Priority — All Resolved ✅

| # | Title | Status | GitHub |
| --- | --- | --- | --- |
| G08 | Browser file upload | ✅ `st.file_uploader` in web mode; saved to `output/uploads/` | [#5] |
| G09 | Audio/video sync playback | ✅ Phrase-restricted HTML5 player; local streaming + web base64 modes | [#6] |
| G10 | UI tab cleanup | ✅ Reduced from 6 to 4 tabs; brand art and favicon added | [#7] |
| G11 | REST API | Deferred — planned for SaaS phase | [#8] |
| G12 | Onboarding flow / guided start | ✅ Welcome screen with workflow icons, steps, detection table | [#16] |
| G13 | Uniform-tempo segmentation | ✅ `max_phrase_duration_ms` cap forces phrase breaks regardless of structural uniformity | [#2] |

---

## Medium Priority — Open

| # | Title | Notes |
| --- | --- | --- |
| G14 | Persistent user preferences | BPM threshold, min phrase length, etc. reset on each session |
| G15 | Before/after comparison view | Phrase Editor has per-phrase preview; no full-funscript side-by-side diff |
| G16 | Assessment config persistence from UI | Analyzer settings are session-local; no save/load across sessions |
| G17 | Inline parameter help text | Most sliders have `help=` text; coverage is uneven |
| G18 | Keyboard shortcuts | ✅ Ctrl+Z/Y/S implemented; phrase step/apply/export shortcuts not yet added |
| G19 | Funscript schema documentation | No JSON Schema; format assumptions undocumented |
| G20 | Batch processing CLI | No `batch-assess` or `batch-transform`; one file at a time |
| G21 | Project backup / versioning | `output/<name>.project.json` snapshot exists; no automatic history |
| G22 | Validation of manual window defs | Overlapping or out-of-range windows give no warning |
| G23 | Transform catalog search/filter | 17 transforms in a single list; no filter by tag or capability |

---

## Distribution — Partially Done

| # | Title | Notes |
| --- | --- | --- |
| G30 | PyInstaller Windows build pipeline | ✅ `launcher.py`, `funscript_forge.spec`, `build.bat` created; untested against real funscripts |
| G31 | macOS build | ✅ `build.sh` with `.icns` generation via `sips`/`iconutil`; GitHub Actions matrix job created |
| G32 | Writable paths for frozen exe | `output/` must sit next to `sys.executable` in `_MEIPASS`; `cli.py` / `project.py` / `pattern_catalog.py` not yet patched |
| G33 | Windows installer | NSIS or Inno Setup wrapper not yet created |
| G34 | Auto-update mechanism | `check_for_update()` on startup comparing `VERSION` against latest GitHub Release tag |
| G35 | GitHub Release artifact | `VERSION` file + `release.yml` workflow created; release process not fully documented |

---

## Low Priority — Open

| # | Title | Notes |
| --- | --- | --- |
| G24 | Export change summary as shareable report | Change log visible in UI; not exportable as PDF/HTML |
| G25 | Shared review / comment threads | No collaboration or phrase annotation for multi-user review |
| G26 | Cross-script pattern query | Catalog accumulates stats but isn't queryable by tag + BPM range from the UI |
| G27 | ML-based transform suggestions | Hard-coded rules; no learning from user acceptance history |
| G28 | Import from URL | Can't load funscripts from a URL; local disk only |
| G29 | Mobile-responsive UI | Streamlit layout breaks on small screens |

---

## Accessibility — Remaining Deferred Items

| # | Item | Status |
| --- | --- | --- |
| A1 | Audio player `aria-label` on all buttons | ✅ Fixed |
| A2 | Rejected rows semantic marker | ✅ Fixed (`sr-only` prepended) |
| A3 | BPM colour-only gradient | ✅ Fixed (numeric labels on bars) |
| A4 | `label_visibility="collapsed"` audit | ✅ Fixed (all instances removed) |
| A5 | Plotly chart `st.caption()` descriptions | ✅ Fixed |
| A6 | Emoji status indicator text fallbacks | Deferred — AT reads emoji text acceptably |
| A7 | `lang="en"` injection | ✅ Fixed (JS injection in keyboard sentinel) |
| A8 | Keyboard focus in pattern editor fragment | Deferred — needs manual keyboard-only test pass |

---

---

## Robustness & Security — New

| # | Title | File | Priority |
| --- | --- | --- | --- |
| T1 | Path traversal in media server — request path not validated against a base directory | `launcher.py` | Low (local-only binding) |
| T2 | XSS via `unsafe_allow_html=True` — plugin-sourced names rendered unescaped | `export_panel.py` | Low |
| T3 | No debounce on reassessment — rapid slider changes trigger expensive re-analyses | `app.py` | Medium |
| T4 | Silent crash if `pattern_catalog.json` is corrupted on startup | `app.py` | Medium |
| T5 | Uncaught exception in phrase detail if funscript deleted between tab switches | `phrase_detail.py` | Medium |
| T6 | Catalog save failure swallowed silently — user gets no feedback | `app.py` | Low |
| T7 | Work item times not validated (`end_ms < start_ms` accepted) | `ui/common/project.py` | Low–Medium |
| T8 | Division-by-zero masked via `max(1, dur)` — zero-duration cycles not rejected at load | `assessment/analyzer.py` | Low |
| T9 | Bare `except Exception:` clauses swallow MemoryError / KeyboardInterrupt | Multiple files | Low |

---

## UI / UX — New

| # | Title | File | Priority |
| --- | --- | --- | --- |
| UX1 | No confirmation dialog on Download — accidental click discards session | `export_panel.py` | Medium |
| UX2 | No explanation of why a "Recommended" transform disappears when manual is applied | `export_panel.py` | Low |
| UX3 | Assessment details collapsed by default — users miss the "Focus" edit buttons | `app.py` / `viewer.py` | Low |
| UX4 | No warning when a work item window covers the entire funscript duration | `work_items.py` | Medium |
| UX5 | Quality gate errors don't suggest a fix or link to the Transform Catalog | `export_panel.py` | Low |
| UX6 | Undo/redo doesn't cover work item edits (status changes, time ranges) | `undo_stack.py` | Low–Medium |
| UX7 | No unsaved-changes indicator; Save button has no confirmation | `app.py` | Medium |

---

## Functionality — New

| # | Title | File | Priority |
| --- | --- | --- | --- |
| F1 | Analyzer settings (min phrase length, amplitude sensitivity) reset every session | `app.py` | Low |
| F2 | Export produces only standard funscript JSON; no CSV or device-specific format | `export_panel.py` | Low |
| F3 | No full-funscript Before/After comparison in the Export preview | `export_panel.py` | Low–Medium |
| F4 | Transform Catalog has no search or category filter | `transform_catalog.py` | Low |
| F5 | No `batch-assess` / `batch-transform` CLI command; files processed one at a time | `cli.py` | Low |
| F6 | Only Ctrl+Z/Y/S mapped — no shortcuts for Accept, Next phrase, Apply to all | `app.py` | Low |
| F7 | Export change log is embedded in the funscript only; no human-readable report | `export_panel.py` | Low |
| F8 | No Validate button in Work Items tab — overlap and bounds errors surface only at export | `work_items.py` | Medium |
| F9 | App does not remember the last opened file; user must re-navigate on every restart | `app.py` | Low |
| F10 | No formal funscript schema (JSON Schema); format assumptions undocumented | — | Medium |

---

## Notes

- **G01–G13** were the original production blockers and high-priority items from the initial gap analysis. All are resolved except the deferred REST API (G11).
- **G30–G35** are distribution gaps added during the packaging sprint (P7).
- **T1–T9, UX1–UX7, F1–F10** are new gaps identified in the post-P6 codebase review (2026-03-10).
- Security gaps (input validation, output validation) overlap with the original security analysis — G01–G03 covered the primary risks.
- SaaS multi-user items (G11, G25) are explicitly out of scope for the single-user phase.
