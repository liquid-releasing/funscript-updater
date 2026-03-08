# tests

Unit tests for the core pipeline modules.

85 core tests + 45 UI-layer tests = **130 total**, all using Python's stdlib `unittest` — no extra dependencies required.

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
| `test_integration.py` | 9 |
| `ui/common/tests/` | 45 |
| **Total** | **130** |
