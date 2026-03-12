# FunscriptForge — Glossary of Key Terms

This document defines the vocabulary used throughout the codebase, UI, and documentation.

---

## Core data types

### Funscript

A `.funscript` file is the standard script format used by linear stroker devices (e.g. Handy, OSR2, SR6). It is a JSON file containing a list of **actions** — each action is a `{at, pos}` pair:

- `at` — timestamp in **milliseconds** from the start of the video or audio track
- `pos` — device position in the range **0–100** (0 = fully retracted, 100 = fully extended)

The device interpolates smoothly between consecutive actions. The density, range, and speed of actions determine the physical sensation.

---

### Action

The atomic unit of a funscript. One timestamped position instruction: `{"at": 12345, "pos": 75}`. The device travels to that position by that time, arriving from the previous position in a straight line.

---

### Phase

The smallest structural unit detected by the analyzer. A phase is a **single continuous directional movement** — either:

- **upward** — position increases (stroke going up)
- **downward** — position decreases (stroke going down)
- **flat** — position holds (pause or plateau)

Phases are detected by scanning for changes in motion direction. A typical stroking funscript alternates rapidly: up, down, up, down, …

---

### Cycle

One **complete oscillation**: one upward phase followed by one downward phase (or vice versa). Cycles are the basis for BPM measurement.

- `oscillation_count` — number of up/down pairs in this structural window
- `bpm` — derived from oscillation count ÷ duration × 60,000
- `amplitude_range` — max_pos − min_pos within the cycle's actions

A single loud cycle that spans the full 0–100 range has amplitude_range ≈ 100. A shallow cycle confined to 40–60 has amplitude_range ≈ 20.

---

### Pattern

A **group of cycles with the same direction sequence and similar duration**. The analyzer detects that several consecutive cycles share the same rhythm and labels them as a pattern (e.g. `"up -> down"`, `"up -> down -> up -> down"`). The `pattern_label` is the direction sequence as a string.

Patterns capture the repeating rhythmic motif of a section. Different patterns in the same funscript reflect tempo changes or technique shifts.

---

### Phrase

A **consecutive run of the same pattern** — cycles of a single pattern type that appear without interruption. Each phrase has:

- `start_ms` / `end_ms` — time boundaries
- `bpm` — average BPM across the phrase
- `cycle_count` — how many cycles make up the phrase
- `pattern_label` — the underlying pattern type
- `tags` — behavioral classification (see below)
- `metrics` — computed statistics (mean_pos, span, mean_velocity, etc.)

Phrases are the **unit of editing** in the UI. The Phrase Editor shows one phrase at a time; the Pattern Editor groups all phrases that share a behavioral tag.

---

### BPM Transition

A point in the timeline where tempo changes **significantly** between two consecutive phrases. Stored as:

- `at_ms` — timestamp of the transition (start of the new phrase)
- `from_bpm` / `to_bpm` — the tempo on each side
- `change_pct` — signed percentage change

Transitions are rendered as vertical red markers on the assessment chart, and listed in the BPM Transitions table.

---

### Assessment

The complete structural analysis of one funscript. Running `assess` (CLI) or clicking **Load / Analyse** (UI) produces an **AssessmentResult** containing:

- all phases, cycles, patterns, phrases
- all BPM transitions
- per-phrase behavioral metrics and tags
- file metadata (duration, action count, overall BPM)

The result is saved as a JSON file (e.g. `output/filename.assessment.json`) and loaded automatically by the UI. The assessment is the input to every subsequent editing and export step.

---

### Tag

A **behavioral classification label** assigned to a phrase by the classifier. Tags describe what is *wrong* (or notable) about a phrase's motion characteristics, and each tag maps to a suggested transform. Multiple tags can apply to a single phrase.

| Tag | Condition | Problem |
| --- | --- | --- |
| `stingy` | span > 75, velocity > 0.35, BPM > 120 | Full-range hammering; device-demanding, no nuance |
| `giggle` | span < 20, centered 35–65 | Tiny micro-motion; barely perceptible |
| `plateau` | span 20–40, centered 35–65 | Small flat band; lacks engagement |
| `drift` | mean_pos < 30 or > 70, span > 15 | Motion in the wrong zone; needs recentering |
| `half_stroke` | span > 30, mean_pos < 38 or > 62 | Real motion but confined to one half |
| `drone` | duration > 90 s, BPM variation < 10% | Monotone repetition; fatigue pattern |
| `lazy` | BPM < 60, span < 50 | Slow and shallow; unenergetic |
| `frantic` | BPM > 200 | Near device mechanical limit; likely imperceptible |

Phrases with no tag are considered well-formed and receive auto-suggested transforms in the Export tab based on their metrics.

---

### Transform

A named operation applied to the actions within a phrase window to change their shape or dynamics. The **transform catalog** contains 18 built-in transforms (e.g. `amplitude_scale`, `recenter`, `smooth`, `halve_tempo`, `nudge`, `beat_accent`, `normalize`, `passthrough`). Users can add their own via JSON recipe files (`user_transforms/`) or Python plugins (`plugins/`).

---

### Catalog (Pattern Catalog)

A **persistent JSON file** (`output/pattern_catalog.json`) that accumulates phrase statistics across every funscript you analyse. Each entry records the funscript filename, assessment timestamp, and per-phrase tags and metrics. Over time this builds a dataset of behavioral patterns across your entire library. It can be queried via the `catalog` CLI command.

---

### Export

The act of building the final output funscript. Export aggregates:

1. **Completed transforms** — accepted in the Phrase Editor or Pattern Editor
2. **Recommended transforms** — tag-aware auto-suggestions for untouched phrases (opt-in per row)
3. **Post-processing** — optional blend-seams pass + final smooth pass

The export preview chart shows the proposed result. Every downloaded funscript contains a `_forge_log` key recording what was changed, how, and when.

---

### Seam Blending

A post-processing pass that detects **high-velocity jumps at style boundaries** (where a transformed phrase meets an untransformed one) and applies a bilateral low-pass filter at those seam points only. Normal strokes are left untouched.

---

### Window

A time range defined by the user to mark sections of the funscript for special treatment during the `customize` pipeline step. Windows can be typed as:

- **Performance** — sections to receive expressive, high-energy transforms
- **Break** — sections to soften or silence
- **Raw** — sections to leave as-is (bypass the transformer)
- **Beats** — sections aligned to music beats for rhythmic accents
