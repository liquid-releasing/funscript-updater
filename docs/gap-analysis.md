# Funscript Forge — Gap Analysis

Generated from user needs research. Items marked **[GH#N]** have a corresponding
GitHub issue. Items not yet in GitHub are candidates for the next sprint.

---

## Critical — Production Blockers (fix before any public release)

| # | Title | Notes | GitHub |
| --- | --- | --- | --- |
| G01 | Position boundary validation | Transforms could push positions outside 0–100; no validation before export | [#9] |
| G02 | Timestamp continuity check | Out-of-order or duplicate timestamps could corrupt exported funscript | [#10] |
| G03 | Input validation + graceful errors | Malformed funscripts / corrupted JSONs produce raw tracebacks, not user messages | [#11] |
| G04 | Transform parameter logging | Accepted transforms don't record exact parameters; export is non-reproducible | [#12] |
| G05 | Automated quality gate | No check for velocity limit violations or device-safety range breaches after export | [#13] |
| G06 | Progress indicator for large files | No feedback during analysis of long files (VictoriaOaks 1:33); no cancellation | [#14] |
| G07 | Undo / redo for accepted transforms | Accepted transforms cannot be undone within a session without restarting | [#15] |

---

## High — Must have before user-facing launch

| # | Title | Notes | GitHub |
| --- | --- | --- | --- |
| G08 | Browser file upload | Must drop file on disk; no in-browser upload | [#5] |
| G09 | Audio/video sync playback | No way to hear the audio while editing phrase timing | [#6] |
| G10 | UI tab cleanup | Six tabs; Navigator and Work Items overlap with newer panels | [#7] |
| G11 | REST API | No programmatic access; blocks web SaaS | [#8] |
| G12 | Onboarding flow / guided start | Raw six-tab UI with no tutorial for new users | [#16] |
| G13 | Uniform-tempo segmentation | VictoriaOaks produces 1 phrase; no useful work items | [#2] |

---

## Medium — High-value improvements

| # | Title | Notes | GitHub |
| --- | --- | --- | --- |
| G14 | Persistent user preferences | BPM threshold, min phrase length, etc. reset on each session | — |
| G15 | Before/after comparison view | No side-by-side waveform diff inside the app | — |
| G16 | Assessment config persistence from UI | Analyzer settings are session-local; no save/load in UI | — |
| G17 | Inline parameter help text | Sliders lack help text; users must read external docs | — |
| G18 | Keyboard shortcuts | No keyboard navigation for phrase step/apply/export | — |
| G19 | Funscript schema documentation | No JSON Schema; format assumptions undocumented | — |
| G20 | Batch processing CLI | No `batch-assess` or `batch-transform`; one file at a time | — |
| G21 | Project backup / versioning | `output/` files can be overwritten; no snapshot history | — |
| G22 | Validation of manual window defs | Overlapping or out-of-range windows give no warning | — |
| G23 | Transform catalog search/filter | 17 transforms in a single list; no filter by tag or capability | — |

---

## Low — Nice to have

| # | Title | Notes | GitHub |
| --- | --- | --- | --- |
| G24 | Export change summary as shareable report | Change log visible in UI but not exportable as PDF/HTML | — |
| G25 | Shared review / comment threads | No collaboration or phrase annotation for multi-user review | — |
| G26 | Cross-script pattern query | Catalog accumulates stats but isn't queryable by tag + BPM range | — |
| G27 | ML-based transform suggestions | Hard-coded rules; no learning from user acceptance history | — |
| G28 | Import from URL | Can't load funscripts from a URL; local disk only | — |
| G29 | Mobile-responsive UI | Streamlit layout breaks on small screens | — |

---

## Notes

- Items **G01–G07** (production blockers) should be resolved before any public-facing URL
- Items **G08–G13** are already tracked as GitHub issues #2, #5–#8, #16
- Items **G14–G23** are candidates for the next GitHub milestone after Phase 1
- Security gaps (input validation, output validation) overlap with the security analysis — see `security-analysis.md`
