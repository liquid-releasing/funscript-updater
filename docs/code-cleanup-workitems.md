# Code Cleanup & Refactoring Work Items

Generated from static analysis. Items marked ✅ are complete.

---

## HIGH — Fix before production

| ID | File(s) | Problem | Fix |
| --- | --- | --- | --- |
| C01 | `assessment/analyzer.py`, `pattern_catalog/transformer.py`, `user_customization/customizer.py`, `models.py`, `*/config.py` | All JSON file I/O lacks try-except; no FileNotFoundError or JSONDecodeError handling | Wrap all file loads with specific exception handling + user-friendly messages |
| C02 | `ui/streamlit/app.py:205`, `panels/viewer.py:199`, `panels/phrase_detail.py:114,561`, `panels/pattern_editor.py:1005` | `except Exception: pass` silently swallows all errors; impossible to debug | Catch specific exceptions; log + show st.error() |
| C03 | `models.py:255` vs `pattern_catalog/transformer.py:146` | `phrase_at()` duplicated — transformer reimplements logic from AssessmentResult | Delete transformer copy; call `assessment.phrase_at()` |
| C04 | `assessment/analyzer.py:60`, `user_customization/customizer.py:64` | No validation that loaded JSON has required keys; missing "actions" key causes IndexError | Add schema check after load: `if "actions" not in data: raise ValueError(...)` |
| C05 | `user_customization/customizer.py:159` | `actions[i-2]` / `actions[i-1]` access undocumented; fragile if loop index changes | Add assertion `assert i >= 2` + docstring explaining invariant |

---

## MEDIUM — Fix soon

| ID | File(s) | Problem | Fix |
| --- | --- | --- | --- |
| C06 | `user_customization/customizer.py:120–214` | `customize()` is 95 lines doing 6 tasks (raw, perf, break, dynamics, beats, smooth) | Extract `_apply_raw()`, `_apply_performance()`, `_apply_break()`, etc. |
| C07 | `pattern_catalog/transformer.py:48–60`, `user_customization/customizer.py:51–114` | Identical `_log()` / `get_log()` pattern duplicated in both classes | Extract `LoggingMixin` base class |
| C08 | `cli.py:176–222` | Some CLI commands have try-except, others don't; no consistent error strategy | Create `@cli_error_handler` decorator for uniform exit codes + messages |
| C09 | `assessment/analyzer.py:149–276` | Complex return types (`List[Tuple[...]]`) lack type hints | Add type aliases or TypedDicts for internal data structures |
| C10 | `ui/streamlit/panels/work_items.py:18–31` | Three parallel lists for status mapping; fragile to extend | Replace with single dict or dataclass |

---

## LOW — Nice to have

| ID | File(s) | Problem | Fix |
| --- | --- | --- | --- |
| C11 | `cli.py:90–102` | Mixed module-level and function-level imports | Consolidate at module level |
| C12 | `user_customization/customizer.py:147,186` | Magic numbers `2` and `50` inline | Define `WINDOW_START_OFFSET = 2`, `POSITION_CENTER = 50` |
| C13 | Tests | No tests for error paths (malformed JSON, missing keys, file-not-found) | Add error-path test cases for all three pipeline modules |
| C14 | `ui/streamlit/panels/*.py` | Local variables use odd `_proj`, `_cat` prefixes | Rename to full descriptive names |
| C15 | `pattern_catalog/config.py`, `user_customization/config.py`, `AnalyzerConfig` | No `__post_init__` range checks on config values | Add validation: amplitude_scale > 0, bpm_threshold in [40,300], etc. |
| C16 | `cli.py:19` | Comment describes a manual step as if it's automated | Update to clarify which steps are code vs. manual workflow |
| C17 | `ui/streamlit/panels/*.py` | Function parameters missing type hints | Add `WorkItem`, `Project`, `ViewState` type hints throughout |
| C18 | `user_customization/customizer.py:231–257` | `_load_ts_file` assumes "start"/"end" keys; KeyError on bad input | Validate window format; raise descriptive ValueError |

---

## Refactoring session plan

### Session 1 (this session) — HIGH severity
- ✅ C01: Error handling in file I/O
- ✅ C02: Replace silent `except Exception: pass`
- ✅ C03: Remove duplicate `phrase_at()`
- ✅ C04: Input validation on JSON load
- ✅ C05: Document/assert array index invariant

### Session 2 — MEDIUM severity

- ✅ C06: Decompose `customize()`
- ✅ C07: Extract `LoggingMixin`
- ✅ C08: CLI error handler decorator
- ✅ C09: Type hints for complex internals
- ✅ C10: Status mapping cleanup
