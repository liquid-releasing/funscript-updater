# FunscriptForge

## The professional post-processor for haptic script creators

---

### What it does

FunscriptForge takes a raw `.funscript` file — the motion script that drives a
haptic device in sync with video — and turns it into something that actually
feels good to use.

Raw scripts are often too fast, too shallow, monotonous in the wrong places, or
jarring at scene cuts. FunscriptForge fixes all of that, automatically and
transparently.

---

### Who it's for

- **Script authors** who want to publish polished, professional work
- **Studios and platforms** that generate scripts algorithmically and need a
  quality pass before release
- **Device manufacturers** who want to validate and improve script libraries
- **Haptic experience designers** syncing multi-sensory content (audio, video, touch)
- **Researchers and developers** building haptic content tools

---

### How it works

```text
Your .funscript
      │
      ▼
  Structural analysis
  Detects phases, cycles, patterns, phrases, and BPM transitions —
  the complete motion grammar of your script.
      │
      ▼
  Behavioral classification
  Labels each phrase: stingy, giggle, plateau, drift, half-stroke,
  drone, lazy, or frantic — each with a clear meaning and a fix.
      │
      ▼
  Interactive editing
  A colour-coded chart shows your entire script. Click any phrase to
  open it, choose a transform, tune it with live sliders, and see a
  before/after preview in real time.
      │
      ▼
  Export
  One click builds the improved script with seam blending and a final
  smooth pass. Download it and you're done.
```

---

### Key features

**Structure-aware analysis**
Not just waveform smoothing — FunscriptForge understands the *grammar* of
motion: what's a stroke, what's a phrase, where the tempo changes and why.

**17 precision transforms**
Amplitude scaling, recentering, tempo halving, beat accenting, contrast
boosting, seam blending, and more — each tuned to fix a specific behavioral
pattern.

**Live before/after preview**
See exactly what a transform will do before you accept it. Adjust sliders and
watch the waveform change in real time.

**Phrase split**
Divide a long phrase at any cycle boundary and apply a different transform to
each half. No need to re-export from scratch.

**Pattern Editor**
Fix every "drone" section in your script in one step. Select the tag, apply
the fix, click "Apply to all" — done.

**Smart auto-suggestions**
Not sure what to do with a phrase? FunscriptForge recommends the right
transform based on the behavioral tag and BPM — you review and accept.

**Cross-script catalog**
Accumulates behavioral statistics across all the scripts you process. See at
a glance how your library compares and where the patterns are.

**Audio / video player**
Listen while you edit. A phrase-restricted player streams your media file in
sync with the selected phrase. Click 📌 at any point to set a split boundary
without leaving the keyboard.

**Undo / redo**
50-level undo/redo for accepted transforms. `Ctrl+Z` / `Ctrl+Y` everywhere.

**CLI + UI**
Use the full Streamlit UI for interactive work, or script the entire pipeline
from the command line for batch processing.

---

### What you get

| Before | After |
| --- | --- |
| Monotone high-speed sections | Rhythmic variation with beat accents |
| Tiny centred micro-motions | Full-range normalised strokes |
| Abrupt jumps between scenes | Smooth blended seams |
| Off-centre "half strokes" | Recentered to use the full range |
| Frantic 200+ BPM sections | Halved tempo, still intense but usable |
| Shallow plateau sections | Amplitude-scaled to hit the device's sweet spot |

---

### Technical

- **Open source** — MIT licensed, Python 3.11+
- **Local-first** — runs entirely on your machine; no data leaves your system
- **Extensible** — add custom transforms via JSON recipes or Python plugins
- **Tested** — 698 unit tests covering the full pipeline, smoke tests against real funscripts, and input validation against corrupted/truncated files
- **Fast** — a 10-minute script analyses in under 2 seconds
- **Accessible** — WCAG 2.1 Level AA (screen reader labels, keyboard shortcuts, colour-blind-safe labels)

---

### Get started

```bash
pip install -r requirements.txt
streamlit run ui/streamlit/app.py
```

Opens at `http://localhost:8501`. Drop in a `.funscript` and click Analyse.

---

*FunscriptForge — because good haptics don't happen by accident.*

---

## Haptic experience creation — a step-by-step picture

Creating a great haptic experience used to require hours of manual scripting.
Here is the complete journey — from raw video to a finished multi-sensory script
— and where FunscriptForge fits in.

```text
Step 1 — Generate a raw script
  Tools: PythonDancer, OpenFunscripter, or your own generator
  Input:  video file (MP4/MKV)
  Output: raw .funscript (timestamp + position pairs)
  Issue:  raw scripts are often noisy, shallow, or behaviourally flat

Step 2 — Analyse the motion structure (FunscriptForge)
  Detects: phases → cycles → patterns → phrases → BPM transitions
  Labels:  each phrase with a behavioral tag (stingy, drone, frantic…)
  Output:  assessment JSON — the "grammar" of your script

Step 3 — Edit and transform (FunscriptForge)
  Phrase Editor:  fix individual phrases with live before/after preview
  Pattern Editor: fix every "drone" section in one click
  Transform Catalog: 17 precision transforms — amplitude, tempo, rhythm…
  Output:  improved .funscript

Step 4 — Add audio synchronisation
  Tools: beat-detection (Librosa, BeatNet), cue sheets, chapter markers
  Align: BPM transitions in the script to audio beat grid
  Result: haptic rhythm that tracks the music or audio cues in the video

Step 5 — Route to device(s) (MultiFunPlayer, Restim)
  Linear devices:  .funscript plays directly
  Estim devices:   Restim converts stroke waveform to L/R channel patterns
  Multi-axis:      MultiFunPlayer maps actions across device axes
  Output:  synchronized, multi-sensory playback experience
```

### Where FunscriptForge is uniquely valuable

| Stage | Without Forge | With Forge |
| --- | --- | --- |
| Raw script quality | Flat, noisy, device-straining | Behaviorally classified, range-optimised |
| Scene transitions | Jarring velocity jumps | Smooth blended seams |
| Tempo alignment | Manual BPM annotation | Automatic phrase-level BPM detection |
| Device safety | No velocity validation | Automated quality gate — velocity + short-interval checks |
| Audio sync prep | Manual phrase marking | BPM transitions ready for beat alignment |

FunscriptForge does not play back media or drive devices directly — it is the
quality and structure layer that makes every downstream tool work better.

---

*© 2026 [Liquid Releasing](https://github.com/liquid-releasing). Licensed under the [MIT License](../LICENSE).  Written by human and Claude AI (Claude Sonnet).*
