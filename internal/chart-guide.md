# Funscript Forge — How to Read the Chart

The funscript chart is the primary visual interface in every tab. This guide explains what you are looking at and how to interpret what the colors tell you about the script's quality.

---

## Chart axes

| Axis | What it represents |
| --- | --- |
| **X — time** | Milliseconds from the start of the file, displayed as M:SS |
| **Y — position** | Device position 0–100 (0 = fully retracted, 100 = fully extended) |

A dot at coordinates `(30000, 75)` means: *at 30 seconds, move the device to position 75*.

---

## The two color modes

You can toggle between **Velocity** and **Amplitude** in the sidebar. Both modes color the dots (and connecting lines) of the motion trace.

### Velocity mode (default)

Each dot is colored by **how fast the position is changing** at that moment — specifically the absolute value of `Δpos / Δt` in position-units per millisecond, normalized to the fastest point in the visible window.

```
Blue ──────────────────────────────────────────────── Red
Slow                                                  Fast
#1a2fff  →  #00bfff  →  #00e000  →  #ffdd00  →  #ff1a1a
  (blue)      (cyan)     (green)     (yellow)      (red)
```

| Color | Velocity | What it means |
| --- | --- | --- |
| Blue | Very slow | Gentle, minimal movement |
| Cyan | Slow–medium | Easy, comfortable pace |
| Green | Medium | Normal stroking tempo |
| Yellow | Fast | High-energy, demanding |
| Red | Fastest in file | Extreme velocity — peak intensity |

### Amplitude mode

Each dot is colored by **its absolute Y position** — how far extended the device is at that moment.

```
Dark blue ──────────────────────────────────────────── Pink
pos = 0                                             pos = 100
#0d0d2b  →  #4b0082  →  #c71585  →  #ff69b4
 (navy)    (indigo)    (magenta)    (pink)
```

Amplitude mode is useful for spotting drift (motion displaced off-center) and for judging amplitude span.

---

## Why top-to-bottom red is a problem

In velocity mode, **red means maximum speed**. When you see a line segment that drops steeply from a high position (near 100) straight down to a low position (near 0), that segment will be red because:

- The position change is **large** (close to 100 units)
- The time between actions is **short**
- Velocity = Δpos / Δt → large Δpos, small Δt → very high velocity

A near-vertical red line is a *hammer stroke*: the script sends the device from fully extended to fully retracted (or vice versa) as fast as possible with no nuance. This is the signature of the **stingy** tag.

### What it looks like

```
pos
100 ●  ← red dot (device just reached top)
     ╲
      ╲  ← red line (dropping at maximum speed)
       ╲
  0     ● ← red dot (slammed to bottom)
```

The line is not just steep — it's **colored red the entire way down**. Every intermediate interpolated position is reached at extreme velocity.

### Why it matters

1. **Device wear** — hammering between 0 and 100 repeatedly stresses the motor and linear drive mechanism
2. **No perceptible nuance** — at very high speeds the user cannot distinguish one stroke from the next; the sensation collapses into buzzing
3. **Clipping risk** — some devices clamp velocity internally, which can cause the actual motion to lag behind the script, desynchronizing with the video
4. **Comfort** — abrupt extreme strokes are mechanically jarring rather than pleasurable

### What good motion looks like

Good velocity color distribution is **mostly blue/cyan/green** with yellow or red appearing only at genuine peaks (a dramatic acceleration, an emphasis stroke, a climax moment). The transition from one color to the next should be gradual — the trace should breathe.

A well-formed phrase oscillates through the color spectrum smoothly:
```
blue (approach) → green (mid-stroke) → yellow (reversal point) → green → blue
```

Not every stroke needs to be gentle — purposeful red moments are fine and add expressiveness. The problem is when **every** stroke is red with no variation, or when the script is red throughout an entire section.

---

## Phrase bounding boxes

Colored rectangles overlaid on the chart mark phrase boundaries.

| Box color | Meaning |
| --- | --- |
| Orchid / purple border | Normal unselected phrase |
| Gold / yellow border + fill | Currently selected phrase |
| Dimmed purple + grey fill | Unselected phrases when one is active |

Phrase labels (P1, P2, …) appear at the top-left corner of each box. Click anywhere inside a box to select that phrase and open its detail panel.

---

## BPM transition markers

Vertical **tomato-red lines** mark points where tempo changes significantly between consecutive phrases. These are BPM transitions — moments where the script shifts gear. A dense cluster of transitions indicates a very dynamic section; a long stretch with no transitions indicates a sustained uniform tempo (which may be tagged `drone` if it lasts too long).

---

## Large-file rendering

For funscripts with more than 2,500 actions, the full chart switches to a **grey line + colored dots** rendering for performance. When you click a phrase, the selected window is re-rendered with **full velocity color lines** so the active phrase remains visually distinct against the grey background. All other phrases stay grey until you select them.

---

## Annotation bands (Assessment tab only)

The Assessment tab shows additional colored background bands that reveal the full structural hierarchy:

| Color | Level | What it marks |
| --- | --- | --- |
| Cornflower blue | Phase | One directional segment (up, down, or flat) |
| Sea green | Cycle | One complete up+down oscillation |
| Orange | Pattern | All cycles sharing the same direction sequence |
| Orchid | Phrase | A consecutive run of the same pattern |
| Tomato red | Transition | BPM change point (vertical marker) |

Bands are stacked in rows so they don't obscure each other: phases at the bottom, then cycles, patterns, phrases, transitions at the top.

---

## Quick-read summary

| What you see | What it means | What to do |
| --- | --- | --- |
| Long stretches of solid red | Stingy: maximum-velocity hammering | Apply `amplitude_scale` (reduce) or `recenter` |
| Line stays flat near center (low Y variation) | Giggle or plateau | Apply `amplitude_scale` (amplify) |
| Line oscillates but shifted high or low | Drift or half-stroke | Apply `recenter` |
| Uniformly green/blue for many minutes | Drone: no variation | Apply `beat_accent` or split and vary |
| Very fast oscillations with no pauses | Frantic (BPM > 200) | Apply `halve_tempo` |
| Smooth color gradient with varied peaks | Well-formed — no action needed | Use `passthrough` or light `smooth` |
