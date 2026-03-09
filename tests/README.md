# tests

Unit tests for the core pipeline modules and UI-panel split logic.

394 tests in `tests/` + 60 UI-layer tests in `ui/common/tests/` = **454 total**, all using Python's stdlib `unittest` — no extra dependencies required.

## Running

```bash
# All core tests
python -m unittest discover -s tests -v

# Via CLI shortcut
python cli.py test

# Single module
python -m unittest tests.test_analyzer -v
```

For the UI-layer tests (WorkItem / Project):

```bash
python -m unittest discover -s ui/common/tests -v
```

## Test modules

### `test_analyzer.py` — `FunscriptAnalyzer`

| Class | What it covers |
| --- | --- |
| `TestFunscriptAnalyzer` | Load, analyze, phase/cycle/pattern/phrase detection, timestamp consistency, `phrase_at()`, error on analyze-without-load |
| `TestBpmTransitionDetection` | Threshold at 0 flags all changes; threshold at 9999 flags none; transition field types |
| `TestAssessmentResultSerialization` | `to_dict()` structure, dual ms/ts fields on phases, full save → load round-trip |
| `TestAnalyzerConfig` | Default values, custom threshold |

### `test_transformer.py` — `FunscriptTransformer`

| Class | What it covers |
| --- | --- |
| `TestFunscriptTransformer` | Load, transform output shape, positions in `[0, 100]`, timestamps non-negative, save → valid JSON, log output, pass-through at high threshold, all-transform at zero threshold, time-scale applied globally |
| `TestTransformerConfig` | Default values, dict round-trip, file save/load, unknown keys ignored |

### `test_customizer.py` — `WindowCustomizer`

| Class | What it covers |
| --- | --- |
| `TestWindowCustomizer` | Load funscript + assessment, customize output shape, positions in `[0, 100]`, save → valid JSON, manual performance window loaded correctly, missing window file treated as empty, log output |
| `TestCustomizerConfig` | Default values, dict round-trip, file save/load, unknown keys ignored |

### `test_utils.py` — `utils.py`

| Class | What it covers |
| --- | --- |
| `TestParseTimestamp` | Full `HH:MM:SS.mmm`, `MM:SS.mmm`, `SS.mmm` formats, no-millis, zero, millis padding, whitespace stripping |
| `TestMsToTimestamp` | Basic conversion, zero, negative clamps to zero, one minute, one hour |
| `TestRoundTrip` | `parse_timestamp(ms_to_timestamp(ms)) == ms` for 8 representative values |
| `TestOverlaps` | Overlapping, non-overlapping, touching at endpoint, contained, identical, adjacent |
| `TestLowPassFilter` | Zero strength = pass-through, full strength = locks to first value, output length, empty list, single element |

### `test_cli.py` — CLI subcommands

| Class | What it covers |
| --- | --- |
| `TestCliAssess` | Exit code, output JSON structure, default path, summary output, analyzer config round-trip |
| `TestCliTransform` | Exit code, valid funscript output, positions in range, transformer config flag |
| `TestCliCustomize` | Exit code, valid funscript output, perf window flag, missing window file handled gracefully |
| `TestCliPipeline` | Exit code, all three output files written, positions in range, perf window flag, stage summaries printed |
| `TestCliConfig` | Transformer/customizer/analyzer config dump, config round-trip into transform command |

### `test_classifier.py` — `assessment/classifier.py`

| Class | What it covers |
| --- | --- |
| `TestTagRegistry` | All 8 tags present, each has required fields (key, label, description, color, suggested_transform, fix_hint) |
| `TestComputePhraseMetrics` | Empty window defaults, span, mean_pos, duration_ms, peak_velocity ≥ mean, cv_bpm with/without cycles, out-of-window actions excluded |
| `TestClassifyPhrase` | Each of the 8 tags detected and not detected, multi-tag co-existence, clean phrase produces empty list |
| `TestAnnotatePhrases` | tags/metrics added in-place, `_cycles` temp key removed, multiple phrases, drone threshold respected, cv_bpm computed from cycles |

### `test_pattern_catalog.py` — `catalog/pattern_catalog.py`

| Class | What it covers |
| --- | --- |
| `TestPatternCatalog` | Empty summary, add_assessment (tagged vs untagged, replace, duration stored), save/load round-trip, corrupted file fallback, remove, get_tag_stats (count, funscripts, BPM range, all keys), get_phrases_for_tag (filter, _funscript key), funscript_names, summary tags sorted |

### `test_pattern_editor_splits.py` — Pattern Editor split-segment logic

| Class | What it covers |
| --- | --- |
| `TestSegmentHelpers` | `_get_segments` with 0/1/2 splits, contiguous segments, unsorted input sorted, `_get_active_seg` default + clamping |
| `TestTransformState` | `_get_seg_transform` empty/legacy/new-key fallback, precedence; `_set_seg_transform` new key, legacy key sync for seg 0, no cross-seg contamination |
| `TestAddSplitPoint` | Boundary validation (start/end/before/after/duplicate), 2-segment creation, right-half inherits left transform, subsequent segments renumbered +1, multiple accumulating splits |
| `TestRemoveSplitBoundary` | Only-split removal, first/last boundary removal, merged segment keeps left transform, subsequent segments renumbered -1, no-splits and invalid-index rejection |
| `TestCopyInstanceToAll` | No-splits copies transform only, proportional split scaling, all segment transforms copied, source unchanged, dest splits cleared when source has none, split points clamped to dest bounds |
| `TestBuildAllTransforms` | No transforms → unchanged, Apply=False skips instance, invert applied, passthrough unchanged, two segments with independent transforms, multiple instances each transformed, out-of-cycle actions unchanged, result length preserved |

### `test_integration.py` — full pipeline chain

| Class | What it covers |
| --- | --- |
| `TestAssessTransformCustomizeChain` | Assessment stage, transformer stage, customizer stage, `run_pipeline()` writes all outputs, positions in range, log non-empty, missing assessment error, per-item config carried through to window JSON |

## Fixture

`fixtures/sample.funscript` — a small synthetic funscript used by all modules.
It is intentionally short so tests run in < 0.1 s.

## Test count by module

| Module | Tests |
| --- | --- |
| `test_analyzer.py` | 25 |
| `test_transformer.py` | 15 |
| `test_customizer.py` | 12 |
| `test_utils.py` | 24 |
| `test_classifier.py` | 36 |
| `test_pattern_catalog.py` | 29 |
| `test_pattern_editor_splits.py` | 47 |
| `test_integration.py` | 9 |
| `test_cli.py` | 21 |
| other modules | *(see `tests/` directory)* |
| `ui/common/tests/` | 60 |
| **Total** | **454** |
