"""phrase_transforms.py — Catalog of per-phrase funscript transforms.

Each PhraseTransform describes one named transform that can be applied to
the actions within a phrase window.  The catalog is used by both the CLI
pipeline and the Streamlit UI phrase-detail panel.

Usage::

    from pattern_catalog.phrase_transforms import TRANSFORM_CATALOG, suggest_transform

    spec = TRANSFORM_CATALOG["amplitude_scale"]
    new_actions = spec.apply(phrase_actions)

    key, params = suggest_transform(phrase_dict, bpm_threshold=120.0)

User extensions
---------------
Two directories in the project root allow users to extend the catalog without
editing this file:

* ``user_transforms/`` — JSON recipe files.  Each file defines one or more
  transforms as an ordered list of existing catalog steps::

      {
        "key": "my_fix",
        "name": "My Fix",
        "description": "Recenter then amplify",
        "steps": [
          {"transform": "recenter",        "params": {"target_center": 50}},
          {"transform": "amplitude_scale", "params": {"scale": 2.5}}
        ]
      }

* ``plugins/`` — Python plugin files.  Each file must expose a module-level
  ``TRANSFORM`` (one ``PhraseTransform`` instance) or ``TRANSFORMS`` (list).
  See ``plugins/example_plugin.py`` for a template.

Both directories are scanned automatically at import time.  Keys must be
unique; user-defined keys that clash with built-ins are skipped with a
warning.
"""

from __future__ import annotations

import copy
import glob
import importlib.util
import json
import math
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from utils import low_pass_filter


# ------------------------------------------------------------------
# Parameter descriptor
# ------------------------------------------------------------------

@dataclass
class TransformParam:
    """Metadata for one tuneable parameter of a transform."""
    label: str
    type: str           # "float" | "int" | "bool"
    default: Any
    min_val: Any = None
    max_val: Any = None
    step: Any = None
    help: str = ""


# ------------------------------------------------------------------
# Transform base
# ------------------------------------------------------------------

@dataclass
class PhraseTransform:
    """A named, parameterised transform that modifies a slice of actions.

    Attributes
    ----------
    key:         Short machine-readable identifier.
    name:        Human-readable display name.
    description: One-sentence explanation of what the transform does.
    params:      Dict of parameter name → TransformParam descriptor.
    structural:  If True, the transform may return a different number of
                 actions with different timestamps (not just modified pos).
                 Callers must replace the phrase slice rather than patching
                 positions in-place.
    """
    key: str
    name: str
    description: str
    params: Dict[str, TransformParam] = field(default_factory=dict)
    structural: bool = False

    def apply(self, actions: list, param_values: Optional[Dict[str, Any]] = None) -> list:
        """Return a new action list with the transform applied.

        Parameters
        ----------
        actions:
            Slice of funscript actions (``[{"at": ms, "pos": 0-100}, …]``).
            The originals are not mutated.
        param_values:
            Override values for any parameter keys.  Missing keys fall back
            to the param's default.
        """
        p = {k: v.default for k, v in self.params.items()}
        if param_values:
            p.update({k: v for k, v in param_values.items() if k in p})
        result = copy.deepcopy(actions)
        return self._transform(result, p)

    def _transform(self, actions: list, p: dict) -> list:
        raise NotImplementedError


# ------------------------------------------------------------------
# Concrete transforms
# ------------------------------------------------------------------

class _Passthrough(PhraseTransform):
    def _transform(self, actions, p):
        return actions


class _AmplitudeScale(PhraseTransform):
    """Scale positions around the midpoint (50)."""
    def _transform(self, actions, p):
        scale = p["scale"]
        for a in actions:
            centered = a["pos"] - 50
            a["pos"] = max(0, min(100, int(50 + centered * scale)))
        return actions


class _Normalize(PhraseTransform):
    """Expand positions to fill the full 0-100 range."""
    def _transform(self, actions, p):
        if not actions:
            return actions
        lo = min(a["pos"] for a in actions)
        hi = max(a["pos"] for a in actions)
        span = hi - lo
        if span == 0:
            return actions
        target_lo = p["target_lo"]
        target_hi = p["target_hi"]
        target_span = target_hi - target_lo
        for a in actions:
            a["pos"] = max(0, min(100, int(target_lo + (a["pos"] - lo) / span * target_span)))
        return actions


class _Smooth(PhraseTransform):
    """Apply a low-pass filter to reduce rapid position changes."""
    def _transform(self, actions, p):
        strength = p["strength"]
        positions = [a["pos"] for a in actions]
        smoothed = low_pass_filter(positions, [strength] * len(positions))
        for a, pos in zip(actions, smoothed):
            a["pos"] = int(pos)
        return actions


class _ClampRange(PhraseTransform):
    """Compress positions into a sub-range (e.g. upper or lower half)."""
    def _transform(self, actions, p):
        lo = p["range_lo"]
        hi = p["range_hi"]
        span = hi - lo
        for a in actions:
            a["pos"] = max(0, min(100, int(lo + a["pos"] / 100.0 * span)))
        return actions


class _Invert(PhraseTransform):
    """Mirror positions around 50 (pos = 100 - pos)."""
    def _transform(self, actions, p):
        for a in actions:
            a["pos"] = 100 - a["pos"]
        return actions


class _BoostEnds(PhraseTransform):
    """Push positions toward the extremes (0 or 100), increasing contrast."""
    def _transform(self, actions, p):
        strength = p["strength"]   # 0.0 = no change, 1.0 = full push to 0/100
        for a in actions:
            pos = a["pos"] / 100.0
            # Sigmoid-like push: values > 0.5 go toward 1, values < 0.5 go toward 0
            if pos >= 0.5:
                pushed = 0.5 + (pos - 0.5) * (1.0 + strength)
            else:
                pushed = 0.5 - (0.5 - pos) * (1.0 + strength)
            a["pos"] = max(0, min(100, int(pushed * 100)))
        return actions


class _Shift(PhraseTransform):
    """Translate all positions by a fixed offset, clamping to 0–100.

    Amplitude span is preserved unless the shifted range hits a boundary.
    Use a positive offset to shift motion upward (more intense), negative
    to shift downward (gentler).
    """
    def _transform(self, actions, p):
        offset = p["offset"]
        for a in actions:
            a["pos"] = max(0, min(100, int(a["pos"] + offset)))
        return actions


class _Recenter(PhraseTransform):
    """Shift all positions so that the phrase midpoint lands at *target_center*.

    The midpoint is computed as (min + max) / 2 of the phrase.  All positions
    are translated by the same amount so the amplitude span is unchanged,
    clamped to 0–100 if the shifted range would exceed the boundaries.
    """
    def _transform(self, actions, p):
        if not actions:
            return actions
        target = p["target_center"]
        lo = min(a["pos"] for a in actions)
        hi = max(a["pos"] for a in actions)
        current_center = (lo + hi) / 2.0
        offset = target - current_center
        for a in actions:
            a["pos"] = max(0, min(100, int(round(a["pos"] + offset))))
        return actions


class _Break(PhraseTransform):
    """Amplitude reduction toward centre followed by smoothing — for rest/break sections.

    Mirrors the ``TASK 3 BREAK MODE`` from ``six_task_transformer.py``:

    1. **Amplitude reduce** — each position is pulled toward 50 (the centre)
       by ``reduce`` fraction:
       ``new_pos = pos + (50 - pos) * reduce``
       Equivalent to ``amplitude_scale`` with ``scale = 1 - reduce``, but
       expressed as a fractional pull toward centre so the default (0.40)
       reads naturally as "reduce to 60% of full stroke".

    2. **LPF smoothing** — a low-pass filter (``lpf_strength``) is applied
       after the amplitude step to soften any remaining rapid movements.

    Default values match the original ``BREAK_AMPLITUDE_REDUCE = 0.40`` and
    ``LPF_BREAK = 0.30`` constants.
    """

    def _transform(self, actions, p):
        reduce      = p["reduce"]
        lpf_strength = p["lpf_strength"]

        # Pass 1: pull positions toward centre (50)
        for a in actions:
            a["pos"] = int(a["pos"] + (50 - a["pos"]) * reduce)

        # Pass 2: LPF smoothing
        if lpf_strength > 0.0:
            positions = [a["pos"] for a in actions]
            smoothed  = low_pass_filter(positions, [lpf_strength] * len(positions))
            for a, pos in zip(actions, smoothed):
                a["pos"] = int(pos)

        return actions


class _Performance(PhraseTransform):
    """Velocity-capped, reversal-softened stroke shaping for intense phrases.

    Applies three successive passes (all positional — timestamps unchanged):

    1. **Velocity cap** — if the position change per millisecond between
       consecutive actions exceeds ``max_velocity``, the target position is
       pulled back toward the previous position so the cap is just met.

    2. **Reversal softening** — at each direction change (sign flip in the
       per-action velocity), the new position is blended:
       ``softened = prev + Δ × (1 − reversal_soften)``
       then further blended toward the original target:
       ``blended = softened × (1 − height_blend) + target × height_blend``
       This rounds off the hard edges at stroke reversals.

    3. **Range compress + LPF** — positions are clamped to
       ``[range_lo, range_hi]`` and a light low-pass filter (``lpf_strength``)
       is applied to smooth any remaining jitter.

    Default values match the ``TASK 2 PERFORMANCE MODE`` settings from the
    original ``six_task_transformer.py``.
    """

    def _transform(self, actions, p):
        if len(actions) < 3:
            return actions

        max_vel      = p["max_velocity"]
        rev_soften   = p["reversal_soften"]
        height_blend = p["height_blend"]
        range_lo     = p["range_lo"]
        range_hi     = p["range_hi"]
        lpf_strength = p["lpf_strength"]

        # --- Pass 1: velocity cap ---
        for i in range(1, len(actions)):
            p0 = actions[i - 1]["pos"]
            p1 = actions[i]["pos"]
            t0 = actions[i - 1]["at"]
            t1 = actions[i]["at"]
            dt = max(1, t1 - t0)
            vel = (p1 - p0) / dt
            if abs(vel) > max_vel:
                capped = p0 + math.copysign(max_vel * dt, vel)
                actions[i]["pos"] = max(range_lo, min(range_hi, int(capped)))

        # --- Pass 2: reversal softening ---
        for i in range(2, len(actions)):
            p_prev2 = actions[i - 2]["pos"]
            p_prev  = actions[i - 1]["pos"]
            p_curr  = actions[i]["pos"]
            dir1 = p_prev - p_prev2
            dir2 = p_curr - p_prev
            if dir1 * dir2 < 0:  # direction change
                softened = p_prev + dir2 * (1.0 - rev_soften)
                blended  = softened * (1.0 - height_blend) + p_curr * height_blend
                blended  = max(range_lo, min(range_hi, blended))
                actions[i]["pos"] = int(blended)

        # --- Pass 3: range compress + LPF ---
        for a in actions:
            a["pos"] = max(range_lo, min(range_hi, a["pos"]))

        if lpf_strength > 0.0:
            positions = [a["pos"] for a in actions]
            smoothed  = low_pass_filter(positions, [lpf_strength] * len(positions))
            for a, pos in zip(actions, smoothed):
                a["pos"] = max(range_lo, min(range_hi, int(pos)))

        return actions


class _ThreeOne(PhraseTransform):
    """Three strokes then one flat hold, repeating across the phrase.

    Groups detected beats (extrema) into blocks of four:
    - Beats 1–3: strokes, amplitude-scaled around the group's centre.
    - Beat 4: flat hold — every action in that time window is set to
              the group's centre position (midpoint of min/max).

    The centre is recalculated per 4-beat group so it tracks local
    signal changes rather than the global phrase midpoint.  A partial
    last group (fewer than 4 remaining beats) is left unchanged.

    Optional ``range_lo`` / ``range_hi`` caps hard-limit the output
    positions after scaling; the centre itself is also clamped.
    """

    def _transform(self, actions, p):
        if len(actions) < 4:
            return actions

        amp_scale = p["amplitude_scale"]
        range_lo  = p["range_lo"]
        range_hi  = p["range_hi"]

        extrema_idx = _find_extrema(actions, min_prominence=10)
        n_ext = len(extrema_idx)

        i = 0  # index into extrema_idx for the current group's first beat
        while i + 3 < n_ext:
            # Centre of this 4-beat group
            group_pos = [actions[extrema_idx[i + k]]["pos"] for k in range(4)]
            lo = min(group_pos)
            hi = max(group_pos)
            center = (lo + hi) / 2.0
            center_int = max(range_lo, min(range_hi, int(round(center))))

            for beat_num in range(4):
                beat_idx = i + beat_num
                a_start = extrema_idx[beat_idx]
                a_end = (extrema_idx[beat_idx + 1]
                         if beat_idx + 1 < n_ext else len(actions))

                if beat_num < 3:
                    # Amplitude-scale strokes around the group centre
                    for k in range(a_start, a_end):
                        orig = actions[k]["pos"]
                        new_pos = center + (orig - center) * amp_scale
                        actions[k]["pos"] = max(range_lo, min(range_hi,
                                                               int(round(new_pos))))
                else:
                    # Flat hold at centre for the 4th beat
                    for k in range(a_start, a_end):
                        actions[k]["pos"] = center_int

            i += 4

        # Final pass: apply range cap to ALL actions (including partial groups)
        if range_lo > 0 or range_hi < 100:
            for a in actions:
                a["pos"] = max(range_lo, min(range_hi, a["pos"]))

        return actions


# ------------------------------------------------------------------
# Helpers for structural transforms
# ------------------------------------------------------------------

def _find_extrema(actions: list, min_prominence: int = 10) -> list:
    """Return indices of local peaks and troughs in *actions*.

    Always includes index 0 and len(actions)-1 so phrase boundaries are
    preserved.  A point qualifies only if it differs from both neighbours
    by at least *min_prominence* (filters noise).
    """
    n = len(actions)
    if n < 3:
        return list(range(n))

    indices = [0]
    for i in range(1, n - 1):
        prev_pos = actions[i - 1]["pos"]
        curr_pos = actions[i]["pos"]
        next_pos = actions[i + 1]["pos"]
        is_peak   = curr_pos >= prev_pos and curr_pos >= next_pos
        is_trough = curr_pos <= prev_pos and curr_pos <= next_pos
        if is_peak or is_trough:
            prominence = min(abs(curr_pos - prev_pos), abs(curr_pos - next_pos))
            if prominence >= min_prominence:
                # Skip flat plateaux: don't add if same pos as previous extremum
                if actions[indices[-1]]["pos"] != curr_pos:
                    indices.append(i)
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices


class _BlendSeams(PhraseTransform):
    """Smooth sharp transitions where adjacent phrase transforms create abrupt jumps.

    Computes local velocity (|Δpos / Δt| in pos/ms) between consecutive actions.
    Actions near high-velocity jumps receive a stronger LPF blend; low-velocity
    regions are left almost unchanged.  Smoothing concentrates automatically at
    the seams between differently-styled sections without disturbing normal strokes.

    Uses a **bilateral** (forward + backward) LPF so the seam is softened
    symmetrically — approaching actions are blended, not just departing ones.

    When applied via the ``finalize`` command to the full action list, it catches
    both intra-phrase spikes and inter-phrase boundary jumps.  When applied
    phrase-by-phrase via ``phrase-transform --all`` it softens internal spikes only.
    """

    def _transform(self, actions, p):
        if len(actions) < 2:
            return actions

        max_vel      = p["max_velocity"]
        max_strength = p["max_strength"]

        # Velocity at each action (transition INTO this action from the previous one)
        velocities = [0.0]
        for i in range(1, len(actions)):
            dt = max(1, actions[i]["at"] - actions[i - 1]["at"])
            dp = abs(actions[i]["pos"] - actions[i - 1]["pos"])
            velocities.append(dp / dt)
        velocities[0] = velocities[1] if len(actions) > 1 else 0.0

        # Per-action blend strength: proportional to how far velocity exceeds threshold
        strengths = [
            min(1.0, v / max_vel) * max_strength if max_vel > 0 else 0.0
            for v in velocities
        ]

        # Bilateral LPF: average forward and backward passes for symmetric blending
        positions = [a["pos"] for a in actions]
        fwd = low_pass_filter(positions, strengths)
        rev_pos = list(reversed(positions))
        rev_str = list(reversed(strengths))
        bwd = list(reversed(low_pass_filter(rev_pos, rev_str)))
        smoothed = [int((f + b) / 2.0) for f, b in zip(fwd, bwd)]

        for a, pos in zip(actions, smoothed):
            a["pos"] = pos
        return actions


class _BeatAccent(PhraseTransform):
    """Boost positions away from centre at regular beat intervals.

    Detects the funscript's own stroke reversals (extrema) as beats, then
    accents every Nth one — pushing peaks up and troughs down by
    ``accent_amount`` position units.  Any action within ``radius_ms`` of
    an accented beat time receives the same boost.

    Parameters
    ----------
    every_nth : int
        Stride through the detected beat list.  1 = every beat,
        2 = every other, 4 = every 4th, 8 = every 8th, etc.
    accent_amount : int
        How many position units to push away from centre (≥50 → up, <50 → down).
        Matches ``BEAT_ACCENT_AMOUNT = 4`` from *six_task_transformer.py*.
    radius_ms : int
        Time window (±ms) around each accented beat.  Actions within this
        window all receive the boost.  Matches ``BEAT_ACCENT_RADIUS_MS = 40``.
    start_at_ms : int
        Absolute timestamp (ms) of the beat to treat as beat 0.
        0 = use the first detected extremum in the phrase.
        In the UI, hover over the desired first beat and enter its timestamp here.
    max_accents : int
        Maximum number of beats to accent.  0 = no limit (accent until
        the phrase ends).
    """

    def _transform(self, actions, p):
        if not actions:
            return actions

        every_nth    = max(1, int(p["every_nth"]))
        accent_amt   = int(p["accent_amount"])
        radius_ms    = int(p["radius_ms"])
        start_at_ms  = int(p["start_at_ms"])
        max_accents  = int(p["max_accents"])

        # --- detect beats (extrema) ---
        extrema_idx  = _find_extrema(actions, min_prominence=5)
        beat_times   = [actions[i]["at"] for i in extrema_idx]

        if not beat_times:
            return actions

        # --- find starting beat ---
        if start_at_ms > 0:
            # Nearest extremum at or after start_at_ms
            start_beat = next(
                (j for j, bt in enumerate(beat_times) if bt >= start_at_ms), 0
            )
        else:
            start_beat = 0

        # --- collect accented beat times ---
        accented = []
        j = start_beat
        while j < len(beat_times):
            accented.append(beat_times[j])
            j += every_nth
            if max_accents > 0 and len(accented) >= max_accents:
                break

        if not accented:
            return actions

        # --- apply boost to actions near each accented beat ---
        for a in actions:
            t = a["at"]
            if any(abs(t - bt) <= radius_ms for bt in accented):
                pos = a["pos"]
                boost = accent_amt if pos >= 50 else -accent_amt
                a["pos"] = max(0, min(100, pos + boost))

        return actions


class _HalveTempo(PhraseTransform):
    """Halve the BPM by keeping every other stroke cycle.

    Algorithm:
    1. Detect local extrema (peaks / troughs).
    2. Group as stroke pairs (beat-up + beat-down).
    3. Keep every other pair, discard interleaved pairs.
    4. Retime kept points evenly across the original phrase duration.
    5. Optionally scale amplitude around midpoint (50).

    Result: same phrase duration, same amplitude, ~half the BPM.
    This is a *structural* transform — it returns fewer actions with
    different timestamps, so callers must replace the phrase slice.
    """

    def _transform(self, actions, p):
        if len(actions) < 4:
            return actions  # too short to halve

        amp_scale = p["amplitude_scale"]
        extrema_idx = _find_extrema(actions, min_prominence=10)
        extrema = [(actions[i]["at"], actions[i]["pos"]) for i in extrema_idx]

        # Keep every other pair: keep [0,1], skip [2,3], keep [4,5], …
        kept = []
        i = 0
        while i < len(extrema):
            kept.append(extrema[i])
            if i + 1 < len(extrema):
                kept.append(extrema[i + 1])
            i += 4  # stride 4 = keep pair, skip pair

        # Always preserve last extremum so phrase ends at the right position
        if kept[-1] != extrema[-1]:
            kept.append(extrema[-1])

        if len(kept) < 2:
            return actions

        # Retime evenly across original phrase duration
        t_start  = actions[0]["at"]
        t_end    = actions[-1]["at"]
        duration = t_end - t_start
        n = len(kept)

        new_actions = []
        for j, (_, pos) in enumerate(kept):
            new_at = t_start + round(j / (n - 1) * duration) if n > 1 else t_start
            if amp_scale != 1.0:
                centered = pos - 50
                pos = max(0, min(100, int(50 + centered * amp_scale)))
            new_actions.append({"at": int(new_at), "pos": pos})

        return new_actions


# ------------------------------------------------------------------
# Catalog
# ------------------------------------------------------------------

TRANSFORM_CATALOG: Dict[str, PhraseTransform] = {
    t.key: t for t in [
        _Passthrough(
            key="passthrough",
            name="Passthrough",
            description="Keep original positions unchanged.",
        ),
        _AmplitudeScale(
            key="amplitude_scale",
            name="Amplitude Scale",
            description="Scale stroke depth around the midpoint — use >1 to amplify, <1 to reduce.",
            params={
                "scale": TransformParam(
                    label="Scale factor", type="float", default=2.0,
                    min_val=0.1, max_val=5.0, step=0.1,
                    help="1.0 = no change. 2.0 = double stroke depth.",
                ),
            },
        ),
        _Normalize(
            key="normalize",
            name="Normalize Range",
            description="Expand positions to fill a target range (default: full 0–100).",
            params={
                "target_lo": TransformParam(
                    label="Target low", type="int", default=0,
                    min_val=0, max_val=49, step=5,
                ),
                "target_hi": TransformParam(
                    label="Target high", type="int", default=100,
                    min_val=51, max_val=100, step=5,
                ),
            },
        ),
        _Smooth(
            key="smooth",
            name="Smooth",
            description="Apply a low-pass filter to reduce jitter and rapid micro-movements.",
            params={
                "strength": TransformParam(
                    label="Smoothing strength", type="float", default=0.15,
                    min_val=0.01, max_val=0.5, step=0.01,
                    help="Higher = more smoothing. 0.15 is a light touch.",
                ),
            },
        ),
        _ClampRange(
            key="clamp_upper",
            name="Clamp Upper Half",
            description="Compress positions into the upper half (50–100) — keeps motion in the intense zone.",
            params={
                "range_lo": TransformParam(label="Range low",  type="int", default=50, min_val=0,  max_val=60),
                "range_hi": TransformParam(label="Range high", type="int", default=100, min_val=70, max_val=100),
            },
        ),
        _ClampRange(
            key="clamp_lower",
            name="Clamp Lower Half",
            description="Compress positions into the lower half (0–50) — for gentler or break-style sections.",
            params={
                "range_lo": TransformParam(label="Range low",  type="int", default=0, min_val=0,  max_val=30),
                "range_hi": TransformParam(label="Range high", type="int", default=50, min_val=40, max_val=70),
            },
        ),
        _Invert(
            key="invert",
            name="Invert",
            description="Mirror positions around 50 — flips the stroke direction.",
        ),
        _BoostEnds(
            key="boost_contrast",
            name="Boost Contrast",
            description="Push positions toward 0 and 100 to increase the dynamic range.",
            params={
                "strength": TransformParam(
                    label="Strength", type="float", default=0.5,
                    min_val=0.1, max_val=2.0, step=0.1,
                    help="How hard positions are pushed toward the extremes.",
                ),
            },
        ),
        _Shift(
            key="shift",
            name="Shift",
            description="Translate all positions by a fixed offset — moves the center up or down while keeping amplitude.",
            params={
                "offset": TransformParam(
                    label="Offset", type="int", default=0,
                    min_val=-50, max_val=50, step=5,
                    help="Positive = shift upward (more intense), negative = shift downward (gentler).",
                ),
            },
        ),
        _Recenter(
            key="recenter",
            name="Recenter",
            description="Shift all positions so the phrase midpoint lands at a target value — preserves amplitude span.",
            params={
                "target_center": TransformParam(
                    label="Target center", type="int", default=50,
                    min_val=0, max_val=100, step=5,
                    help="Where the midpoint between the phrase's min and max should land (0–100).",
                ),
            },
        ),
        _Break(
            key="break",
            name="Break",
            description="Pull positions toward centre (reduce amplitude) then smooth — for rest or recovery sections.",
            params={
                "reduce": TransformParam(
                    label="Amplitude reduce", type="float", default=0.40,
                    min_val=0.0, max_val=1.0, step=0.05,
                    help="Fraction to pull each position toward centre 50. 0 = no change, 1 = collapse to 50.",
                ),
                "lpf_strength": TransformParam(
                    label="LPF strength", type="float", default=0.30,
                    min_val=0.0, max_val=0.5, step=0.01,
                    help="Low-pass filter strength applied after amplitude reduction. 0 = off.",
                ),
            },
        ),
        _Performance(
            key="performance",
            name="Performance",
            description="Velocity-capped, reversal-softened strokes with range compression — smooths intense phrases for realistic device movement.",
            params={
                "max_velocity": TransformParam(
                    label="Max velocity (pos/ms)", type="float", default=0.32,
                    min_val=0.05, max_val=1.0, step=0.01,
                    help="Maximum position change per millisecond. Lower = slower, gentler movements.",
                ),
                "reversal_soften": TransformParam(
                    label="Reversal soften", type="float", default=0.62,
                    min_val=0.0, max_val=1.0, step=0.05,
                    help="How much to pull back at direction changes. 0 = no change, 1 = hold at reversal point.",
                ),
                "height_blend": TransformParam(
                    label="Height blend", type="float", default=0.75,
                    min_val=0.0, max_val=1.0, step=0.05,
                    help="After softening, blend back toward the original target position. 1.0 = full target.",
                ),
                "range_lo": TransformParam(
                    label="Range low", type="int", default=15,
                    min_val=0, max_val=40, step=5,
                    help="Minimum output position (hard floor).",
                ),
                "range_hi": TransformParam(
                    label="Range high", type="int", default=92,
                    min_val=60, max_val=100, step=5,
                    help="Maximum output position (hard ceiling).",
                ),
                "lpf_strength": TransformParam(
                    label="LPF strength", type="float", default=0.16,
                    min_val=0.0, max_val=0.5, step=0.01,
                    help="Low-pass filter strength applied after shaping. 0 = off.",
                ),
            },
        ),
        _ThreeOne(
            key="three_one",
            name="Three-One Pulse",
            description="Three strokes then one flat hold at the group centre, repeating — creates a 3+1 pulse pattern at the original beat timing.",
            params={
                "amplitude_scale": TransformParam(
                    label="Amplitude scale", type="float", default=1.0,
                    min_val=0.1, max_val=3.0, step=0.1,
                    help="Scale stroke depth around the group centre. 1.0 = unchanged.",
                ),
                "range_lo": TransformParam(
                    label="Range low", type="int", default=0,
                    min_val=0, max_val=49, step=5,
                    help="Hard minimum position after scaling.",
                ),
                "range_hi": TransformParam(
                    label="Range high", type="int", default=100,
                    min_val=51, max_val=100, step=5,
                    help="Hard maximum position after scaling.",
                ),
            },
        ),
        _BlendSeams(
            key="blend_seams",
            name="Blend Seams",
            description="Detect high-velocity transitions between differently-styled sections and smooth them — concentrates blending at seams, leaves normal strokes untouched.",
            params={
                "max_velocity": TransformParam(
                    label="Max velocity (pos/ms)", type="float", default=0.50,
                    min_val=0.05, max_val=2.0, step=0.05,
                    help="Velocity threshold above which full blending is applied. Lower = catch more transitions.",
                ),
                "max_strength": TransformParam(
                    label="Max blend strength", type="float", default=0.70,
                    min_val=0.0, max_val=1.0, step=0.05,
                    help="LPF strength applied at peak-velocity seams. 0 = off, 1 = maximum smoothing.",
                ),
            },
        ),
        _Smooth(
            key="final_smooth",
            name="Final Smooth",
            description="Light global LPF finishing pass — takes off residual harsh edges after all phrase transforms have been applied.",
            params={
                "strength": TransformParam(
                    label="Smoothing strength", type="float", default=0.10,
                    min_val=0.01, max_val=0.5, step=0.01,
                    help="0.10 is a very light pass (matches LPF_DEFAULT from six_task_transformer). Increase for more smoothing.",
                ),
            },
        ),
        _BeatAccent(
            key="beat_accent",
            name="Beat Accent",
            description="Boost positions away from centre at every Nth stroke reversal — adds rhythmic emphasis at regular beat intervals.",
            params={
                "every_nth": TransformParam(
                    label="Every Nth beat", type="int", default=1,
                    min_val=1, max_val=16, step=1,
                    help="1 = every beat, 2 = every other, 4 = every 4th, 8 = every 8th.",
                ),
                "accent_amount": TransformParam(
                    label="Accent amount", type="int", default=4,
                    min_val=1, max_val=30, step=1,
                    help="Position units to boost peaks up / troughs down. Matches BEAT_ACCENT_AMOUNT=4 from six_task_transformer.",
                ),
                "radius_ms": TransformParam(
                    label="Radius (ms)", type="int", default=40,
                    min_val=5, max_val=200, step=5,
                    help="Time window around each accented beat. Actions within ±radius_ms receive the boost.",
                ),
                "start_at_ms": TransformParam(
                    label="Start at (ms)", type="int", default=0,
                    min_val=0, max_val=9999999, step=1,
                    help="Absolute timestamp of beat 0. 0 = first detected stroke reversal in the phrase. In the UI, hover a beat to find its timestamp.",
                ),
                "max_accents": TransformParam(
                    label="Max accents", type="int", default=0,
                    min_val=0, max_val=999, step=1,
                    help="Stop after this many accented beats. 0 = no limit (accent until phrase ends).",
                ),
            },
        ),
        _HalveTempo(
            key="halve_tempo",
            name="Halve Tempo",
            description="Keep every other stroke cycle to halve the BPM over the same phrase duration.",
            structural=True,
            params={
                "amplitude_scale": TransformParam(
                    label="Amplitude scale", type="float", default=1.0,
                    min_val=0.1, max_val=3.0, step=0.1,
                    help="Scale stroke depth around 50 after tempo reduction. 1.0 = unchanged.",
                ),
            },
        ),
    ]
}


# ------------------------------------------------------------------
# Canonical display order (matches Transform Catalog UI groups)
# ------------------------------------------------------------------

TRANSFORM_ORDER: List[str] = [
    # Passthrough
    "passthrough",
    # Amplitude Shaping
    "amplitude_scale", "normalize", "boost_contrast",
    # Position Adjustment
    "shift", "recenter", "clamp_upper", "clamp_lower", "invert",
    # Smoothing & Filtering
    "smooth", "blend_seams", "final_smooth",
    # Break / Recovery
    "break",
    # Performance / Device Realism
    "performance",
    # Rhythmic Patterns
    "beat_accent", "three_one",
    # Structural — Tempo
    "halve_tempo",
]


# ------------------------------------------------------------------
# Suggestion logic
# ------------------------------------------------------------------

def suggest_transform(phrase: dict, bpm_threshold: float = 120.0):
    """Return ``(catalog_key, param_values)`` for the most appropriate transform.

    Tag-based rules are checked first (priority order); BPM-based fallbacks
    apply only when no recognised tag is present.

    Tag rules:
    1.  transition (pattern_label) → smooth
    2.  frantic   → halve_tempo
    3.  giggle    → amplitude_scale, amplify to peak hi ≈ 65
    4.  plateau   → amplitude_scale, amplify to peak hi ≈ 65
    5.  lazy      → amplitude_scale, amplify to peak hi ≈ 65
    6.  stingy    → amplitude_scale, reduce to peak hi ≈ 65
    7.  drift     → recenter, target_center = 50
    8.  half_stroke → recenter, target_center = 50
    9.  drone     → beat_accent

    BPM fallbacks (no tag match):
    10. bpm < bpm_threshold                 → passthrough
    11. bpm >= bpm_threshold, span < 40     → normalize
    12. bpm >= bpm_threshold                → amplitude_scale

    The amplitude_scale factor for tag-based recommendations is computed from
    the phrase's actual ``mean_pos`` and ``span`` so the output peak position
    lands at ~65.  Users can adjust the value in the UI after the suggestion.
    """
    bpm   = phrase.get("bpm", 0.0)
    label = (phrase.get("pattern_label") or "").lower()
    tags  = phrase.get("tags") or []

    if "transition" in label:
        return ("smooth", {})

    # Helper: compute amplitude_scale factor targeting peak hi = 65
    metrics  = phrase.get("metrics", {})
    span     = metrics.get("span", 0)
    mean_pos = metrics.get("mean_pos", 50)
    hi       = mean_pos + span / 2.0

    def _scale_to_65(clamp_min: float, clamp_max: float) -> dict:
        half_target  = 65.0 - 50.0          # 15 units from midpoint
        half_current = max(hi - 50.0, 1.0)
        scale = round(half_target / half_current, 2)
        scale = max(clamp_min, min(clamp_max, scale))
        return {"scale": scale}

    if "frantic" in tags:
        return ("halve_tempo", {})

    if "giggle" in tags or "plateau" in tags:
        return ("amplitude_scale", _scale_to_65(1.0, 10.0))   # amplify only

    if "lazy" in tags:
        return ("amplitude_scale", _scale_to_65(1.0, 10.0))   # amplify only

    if "stingy" in tags:
        return ("amplitude_scale", _scale_to_65(0.1, 1.0))    # reduce only

    if "drift" in tags or "half_stroke" in tags:
        return ("recenter", {"target_center": 50})

    if "drone" in tags:
        return ("beat_accent", {})

    # BPM-based fallbacks when no tag matched
    if bpm < bpm_threshold:
        return ("passthrough", {})

    amp_span = phrase.get("amplitude_span", 100)  # 0-100; default assumes full range
    if amp_span < 40:
        return ("normalize", {})

    return ("amplitude_scale", {})


# ------------------------------------------------------------------
# Recipe transform (user-defined multi-step pipelines)
# ------------------------------------------------------------------

@dataclass
class _RecipeTransform(PhraseTransform):
    """A transform defined as an ordered sequence of existing catalog steps.

    Each step is ``{"transform": <key>, "params": {...}}``.  Steps are
    applied left-to-right; the output of each step is the input of the next.
    Unknown step keys are skipped with a stderr warning.

    Set ``"structural": true`` in the JSON definition if any step produces a
    different number of actions (e.g. ``halve_tempo``).
    """
    steps: List[dict] = field(default_factory=list)

    def _transform(self, actions: list, p: dict) -> list:
        result = actions
        for step in self.steps:
            key  = step.get("transform", "")
            spec = TRANSFORM_CATALOG.get(key)
            if spec is None:
                print(
                    f"[recipe:{self.key}] unknown step transform {key!r} — skipped",
                    file=sys.stderr,
                )
                continue
            result = spec.apply(result, step.get("params") or None)
        return result


# ------------------------------------------------------------------
# User-transform loader (recipes + plugins)
# ------------------------------------------------------------------

def load_user_transforms(
    recipes_dir: Optional[str] = None,
    plugins_dir: Optional[str] = None,
) -> Dict[str, PhraseTransform]:
    """Scan *recipes_dir* and *plugins_dir* and return a dict of user transforms.

    Defaults to ``<project_root>/user_transforms/`` and
    ``<project_root>/plugins/`` relative to this file's package parent.

    Keys that clash with built-in catalog keys are skipped with a warning.
    """
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if recipes_dir is None:
        recipes_dir = os.path.join(_root, "user_transforms")
    if plugins_dir is None:
        plugins_dir = os.path.join(_root, "plugins")

    result: Dict[str, PhraseTransform] = {}

    # ---- JSON recipes ----
    if os.path.isdir(recipes_dir):
        for path in sorted(glob.glob(os.path.join(recipes_dir, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    key = entry.get("key", "")
                    if not key:
                        continue
                    if key in _BUILTIN_KEYS:
                        print(
                            f"[user_transforms] {os.path.basename(path)}: "
                            f"key {key!r} clashes with a built-in — skipped",
                            file=sys.stderr,
                        )
                        continue
                    t = _RecipeTransform(
                        key=key,
                        name=entry.get("name", key),
                        description=entry.get("description", ""),
                        structural=bool(entry.get("structural", False)),
                        steps=entry.get("steps", []),
                    )
                    result[key] = t
            except Exception as exc:
                print(
                    f"[user_transforms] skipping {os.path.basename(path)}: {exc}",
                    file=sys.stderr,
                )

    # ---- Python plugins ----
    if os.path.isdir(plugins_dir):
        for path in sorted(glob.glob(os.path.join(plugins_dir, "*.py"))):
            try:
                spec = importlib.util.spec_from_file_location(
                    f"_plugin_{os.path.splitext(os.path.basename(path))[0]}", path
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)

                candidates: List[PhraseTransform] = []
                if hasattr(mod, "TRANSFORMS"):
                    candidates = list(mod.TRANSFORMS)
                elif hasattr(mod, "TRANSFORM"):
                    candidates = [mod.TRANSFORM]

                for t in candidates:
                    if not isinstance(t, PhraseTransform):
                        continue
                    if t.key in _BUILTIN_KEYS:
                        print(
                            f"[plugins] {os.path.basename(path)}: "
                            f"key {t.key!r} clashes with a built-in — skipped",
                            file=sys.stderr,
                        )
                        continue
                    result[t.key] = t
            except Exception as exc:
                print(
                    f"[plugins] skipping {os.path.basename(path)}: {exc}",
                    file=sys.stderr,
                )

    return result


# ------------------------------------------------------------------
# Freeze built-in keys BEFORE merging user transforms so the
# TRANSFORM_ORDER completeness test only checks built-ins.
# ------------------------------------------------------------------

_BUILTIN_KEYS: frozenset = frozenset(TRANSFORM_CATALOG)

# Merge user-defined transforms (silent no-op when directories are absent)
TRANSFORM_CATALOG.update(load_user_transforms())
