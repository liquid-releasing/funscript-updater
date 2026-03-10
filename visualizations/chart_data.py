# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""chart_data.py — Pure data computation for funscript visualization.

No UI or matplotlib dependency.  All functions return plain Python
structures (dicts, lists) that the chart widget can consume.

Two display modes
-----------------
velocity
    Each point is coloured by how fast the position is changing
    (pos-units / ms).  Slow = blue, fast = red.  Inspired by
    PythonDancer's intensity heatmap.
amplitude
    Each point is coloured by its absolute position value.
    0 = dark, 100 = bright.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ------------------------------------------------------------------
# Colour helpers
# ------------------------------------------------------------------

# Velocity colour: blue (slow) -> cyan -> green -> yellow -> red (fast)
_VELOCITY_STOPS: List[Tuple[float, str]] = [
    (0.0,  "#1a2fff"),   # blue
    (0.25, "#00bfff"),   # cyan
    (0.5,  "#00e000"),   # green
    (0.75, "#ffdd00"),   # yellow
    (1.0,  "#ff1a1a"),   # red
]

# Amplitude colour: dark blue (low) -> purple -> magenta -> bright (high)
_AMPLITUDE_STOPS: List[Tuple[float, str]] = [
    (0.0,  "#0d0d2b"),
    (0.33, "#4b0082"),
    (0.66, "#c71585"),
    (1.0,  "#ff69b4"),
]

# Assessment type colours for annotation bands
ANNOTATION_COLORS = {
    "phase":      "rgba(100, 149, 237, 0.25)",   # cornflower blue
    "cycle":      "rgba(60,  179, 113, 0.25)",   # medium sea green
    "pattern":    "rgba(255, 165,   0, 0.25)",   # orange
    "phrase":     "rgba(218, 112, 214, 0.25)",   # orchid
    "transition": "rgba(255,  99,  71, 0.60)",   # tomato (transitions are markers)
}


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class PointSeries:
    """Pre-computed data for a single funscript channel.

    Attributes
    ----------
    times_ms:       Action timestamps in milliseconds.
    positions:      Action positions (0–100).
    velocities:     Absolute velocity at each point (pos-units / ms).
    velocity_norm:  Velocity normalised to [0, 1] for colour mapping.
    amplitude_norm: Position normalised to [0, 1].
    colors_velocity:  Hex colour per point (velocity mode).
    colors_amplitude: Hex colour per point (amplitude mode).
    """
    times_ms: List[int] = field(default_factory=list)
    positions: List[float] = field(default_factory=list)
    velocities: List[float] = field(default_factory=list)
    velocity_norm: List[float] = field(default_factory=list)
    amplitude_norm: List[float] = field(default_factory=list)
    colors_velocity: List[str] = field(default_factory=list)
    colors_amplitude: List[str] = field(default_factory=list)


@dataclass
class AnnotationBand:
    """A coloured background band or marker for one assessment item.

    Attributes
    ----------
    kind:       ``"phase"``, ``"cycle"``, ``"pattern"``, ``"phrase"``,
                or ``"transition"``.
    start_ms:   Band start (ms).  For transitions this equals end_ms.
    end_ms:     Band end (ms).
    label:      Human-readable label shown on hover.
    color:      RGBA colour string.
    row:        Vertical stacking row (0 = bottom).  Used so overlapping
                bands of different types don't obscure each other.
    """
    kind: str
    start_ms: int
    end_ms: int
    label: str
    color: str
    row: int = 0
    name: str = ""   # short display label, e.g. "P1" for phrase boxes


# ------------------------------------------------------------------
# Computation
# ------------------------------------------------------------------

def compute_chart_data(actions: List[dict]) -> PointSeries:
    """Compute all display data for a list of funscript actions.

    Parameters
    ----------
    actions:
        List of ``{"at": int, "pos": int}`` dicts.

    Returns
    -------
    PointSeries
        All fields populated and ready for the chart widget.
    """
    if not actions:
        return PointSeries()

    times = [a["at"] for a in actions]
    pos   = [float(a["pos"]) for a in actions]
    n     = len(actions)

    # Velocity: forward difference, first point copies second
    vels: List[float] = [0.0] * n
    for i in range(1, n):
        dt = max(1, times[i] - times[i - 1])
        vels[i] = abs(pos[i] - pos[i - 1]) / dt
    vels[0] = vels[1] if n > 1 else 0.0

    max_vel = max(vels) if max(vels) > 0 else 1.0
    vel_norm = [v / max_vel for v in vels]
    amp_norm = [p / 100.0 for p in pos]

    col_vel = [_interpolate_color(_VELOCITY_STOPS, v) for v in vel_norm]
    col_amp = [_interpolate_color(_AMPLITUDE_STOPS, a) for a in amp_norm]

    return PointSeries(
        times_ms=times,
        positions=pos,
        velocities=vels,
        velocity_norm=vel_norm,
        amplitude_norm=amp_norm,
        colors_velocity=col_vel,
        colors_amplitude=col_amp,
    )


def compute_annotation_bands(assessment_dict: dict) -> List[AnnotationBand]:
    """Build annotation bands from an assessment ``to_dict()`` result.

    Returns bands for phases, cycles, patterns, phrases, and vertical
    markers for BPM transitions.  Each type is assigned a fixed row so
    that overlapping bands of different types stack visibly.
    """
    bands: List[AnnotationBand] = []
    row_map = {"phase": 0, "cycle": 1, "pattern": 2, "phrase": 3, "transition": 4}

    for ph in assessment_dict.get("phases", []):
        bands.append(AnnotationBand(
            kind="phase",
            start_ms=ph["start_ms"], end_ms=ph["end_ms"],
            label=f"Phase: {ph.get('label', '')}",
            color=ANNOTATION_COLORS["phase"],
            row=row_map["phase"],
        ))

    for cy in assessment_dict.get("cycles", []):
        bands.append(AnnotationBand(
            kind="cycle",
            start_ms=cy["start_ms"], end_ms=cy["end_ms"],
            label=f"Cycle: {cy.get('label', '')}",
            color=ANNOTATION_COLORS["cycle"],
            row=row_map["cycle"],
        ))

    for pt in assessment_dict.get("patterns", []):
        for cy in pt.get("cycles", []):
            bands.append(AnnotationBand(
                kind="pattern",
                start_ms=cy["start_ms"], end_ms=cy["end_ms"],
                label=f"Pattern: {pt.get('pattern_label', '')}",
                color=ANNOTATION_COLORS["pattern"],
                row=row_map["pattern"],
            ))

    for i, ph in enumerate(assessment_dict.get("phrases", [])):
        bands.append(AnnotationBand(
            kind="phrase",
            start_ms=ph["start_ms"], end_ms=ph["end_ms"],
            label=f"Phrase ({ph.get('bpm', 0):.0f} BPM): {ph.get('pattern_label', '')}",
            color=ANNOTATION_COLORS["phrase"],
            row=row_map["phrase"],
            name=f"P{i + 1}",
        ))

    for tr in assessment_dict.get("bpm_transitions", []):
        ms = tr["at_ms"]
        bands.append(AnnotationBand(
            kind="transition",
            start_ms=ms, end_ms=ms,
            label=f"BPM transition: {tr.get('from_bpm', 0):.0f} -> {tr.get('to_bpm', 0):.0f}",
            color=ANNOTATION_COLORS["transition"],
            row=row_map["transition"],
        ))

    return bands


def slice_series(series: PointSeries, start_ms: int, end_ms: int) -> PointSeries:
    """Return a new PointSeries containing only points within [start_ms, end_ms]."""
    indices = [
        i for i, t in enumerate(series.times_ms)
        if start_ms <= t <= end_ms
    ]
    if not indices:
        return PointSeries()
    return PointSeries(
        times_ms=       [series.times_ms[i]        for i in indices],
        positions=      [series.positions[i]        for i in indices],
        velocities=     [series.velocities[i]       for i in indices],
        velocity_norm=  [series.velocity_norm[i]    for i in indices],
        amplitude_norm= [series.amplitude_norm[i]   for i in indices],
        colors_velocity=[series.colors_velocity[i]  for i in indices],
        colors_amplitude=[series.colors_amplitude[i] for i in indices],
    )


def slice_bands(bands: List[AnnotationBand], start_ms: int, end_ms: int) -> List[AnnotationBand]:
    """Return bands that overlap [start_ms, end_ms]."""
    return [b for b in bands if b.end_ms >= start_ms and b.start_ms <= end_ms]


# ------------------------------------------------------------------
# Internal colour math
# ------------------------------------------------------------------

def _interpolate_color(stops: List[Tuple[float, str]], t: float) -> str:
    """Interpolate a hex colour from a list of (position, hex) stops."""
    t = max(0.0, min(1.0, t))
    if t <= stops[0][0]:
        return stops[0][1]
    if t >= stops[-1][0]:
        return stops[-1][1]
    for i in range(1, len(stops)):
        p0, c0 = stops[i - 1]
        p1, c1 = stops[i]
        if p0 <= t <= p1:
            frac = (t - p0) / (p1 - p0)
            return _lerp_hex(c0, c1, frac)
    return stops[-1][1]


def _lerp_hex(c0: str, c1: str, t: float) -> str:
    """Linearly interpolate between two hex colours."""
    r0, g0, b0 = _hex_to_rgb(c0)
    r1, g1, b1 = _hex_to_rgb(c1)
    r = int(r0 + (r1 - r0) * t)
    g = int(g0 + (g1 - g0) * t)
    b = int(b0 + (b1 - b0) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
