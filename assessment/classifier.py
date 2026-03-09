"""classifier.py — Behavioral classification of funscript phrases.

Each phrase is analysed against a set of metric thresholds to produce a
list of human-readable *behavioral tags* (e.g. "stingy", "giggle",
"drone").  Tags drive the Pattern Editor's filter/batch-fix workflow.

Metrics computed per phrase
---------------------------
mean_pos        : average position across all actions in the phrase window
span            : max_pos - min_pos  (amplitude span)
mean_velocity   : mean |Δpos / Δt|  (pos-units / ms)
peak_velocity   : 90th-percentile velocity (robust to a single spike)
cv_bpm          : coefficient of variation of per-cycle BPM (0 = perfectly
                  uniform; higher = more varied tempo)
duration_ms     : phrase length in milliseconds

Behavioral tags
---------------
stingy      span > 75 AND mean_velocity > 0.35 AND bpm > 120
            — full-range, high-speed, mechanically demanding; no nuance
giggle      span < 20 AND 35 ≤ mean_pos ≤ 65
            — tiny centered micro-motion; barely perceptible
plateau     20 ≤ span < 40 AND 35 ≤ mean_pos ≤ 65
            — slightly wider giggle; still dead-center and flat
drift       mean_pos < 30 OR mean_pos > 70  (and span > 15)
            — motion happening in the wrong zone; needs recentering
half_stroke span > 30 AND (mean_pos < 38 OR mean_pos > 62)
            — real motion but confined to one half of the range
drone       duration_ms > drone_threshold_ms AND cv_bpm < 0.10
            — monotone pattern repeating without variation for too long
lazy        bpm < 60 AND span < 50
            — slow and shallow; unenergetic
frantic     bpm > 200
            — too fast to feel; likely near device mechanical limit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Tag registry
# ---------------------------------------------------------------------------

@dataclass
class BehavioralTag:
    """Metadata for one behavioral classification."""
    key: str
    label: str
    description: str
    color: str          # CSS / plotly RGBA string for UI highlights
    suggested_transform: str  # key into TRANSFORM_CATALOG
    fix_hint: str       # one-line hint shown alongside the transform


TAGS: Dict[str, BehavioralTag] = {
    "stingy": BehavioralTag(
        key="stingy",
        label="Stingy",
        description=(
            "Full-range, high-speed strokes with no nuance — every action "
            "hammers between the extremes at maximum velocity. "
            "Device-demanding with no variation."
        ),
        color="rgba(255,80,80,0.70)",
        suggested_transform="amplitude_scale",
        fix_hint="Reduce amplitude to a device-comfortable range (target hi ≈ 65).",
    ),
    "giggle": BehavioralTag(
        key="giggle",
        label="Giggle",
        description=(
            "Tiny, centered micro-motion — positions stay within a narrow "
            "band around 50. Barely perceptible."
        ),
        color="rgba(80,180,255,0.70)",
        suggested_transform="amplitude_scale",
        fix_hint="Amplify to a usable range (target hi ≈ 65).",
    ),
    "plateau": BehavioralTag(
        key="plateau",
        label="Plateau",
        description=(
            "Small amplitude, dead-center — motion exists but stays in a "
            "flat band around the midpoint. Lacks engagement."
        ),
        color="rgba(120,120,255,0.70)",
        suggested_transform="amplitude_scale",
        fix_hint="Scale amplitude up and boost contrast.",
    ),
    "drift": BehavioralTag(
        key="drift",
        label="Drift",
        description=(
            "Motion happening in the wrong zone — centre of gravity is "
            "displaced above 70 or below 30. Needs recentering."
        ),
        color="rgba(255,180,0,0.70)",
        suggested_transform="recenter",
        fix_hint="Recenter so the midpoint lands near 50.",
    ),
    "half_stroke": BehavioralTag(
        key="half_stroke",
        label="Half Stroke",
        description=(
            "Real stroke amplitude but confined to one half of the range — "
            "upper half (> 60) or lower half (< 40)."
        ),
        color="rgba(255,140,0,0.70)",
        suggested_transform="recenter",
        fix_hint="Recenter to 50 to restore full bilateral motion.",
    ),
    "drone": BehavioralTag(
        key="drone",
        label="Drone",
        description=(
            "Monotone pattern repeating without variation for an extended "
            "period — uniform BPM, no evolution. Fatigue pattern."
        ),
        color="rgba(180,80,255,0.70)",
        suggested_transform="beat_accent",
        fix_hint="Add beat accents or three-one pulse to introduce variation.",
    ),
    "lazy": BehavioralTag(
        key="lazy",
        label="Lazy",
        description=(
            "Slow and shallow — low BPM and small amplitude. "
            "Unenergetic; may need lifting or replacing."
        ),
        color="rgba(100,180,100,0.70)",
        suggested_transform="amplitude_scale",
        fix_hint="Scale amplitude up; consider boosting contrast.",
    ),
    "frantic": BehavioralTag(
        key="frantic",
        label="Frantic",
        description=(
            "BPM exceeds 200 — likely near the device's mechanical limit. "
            "Motion may be imperceptible; consider halving the tempo."
        ),
        color="rgba(255,50,50,0.90)",
        suggested_transform="halve_tempo",
        fix_hint="Halve tempo to bring into a perceptible range.",
    ),
}


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_phrase_metrics(phrase_dict: dict, all_actions: List[dict]) -> dict:
    """Compute additional behavioral metrics for one phrase.

    Parameters
    ----------
    phrase_dict : dict
        A phrase dict as returned by ``Phrase.to_dict()``.
        Must contain ``start_ms``, ``end_ms``, ``bpm``.
    all_actions : list[dict]
        Full list of funscript actions (``{"at": int, "pos": int}``).

    Returns
    -------
    dict
        ``{mean_pos, span, mean_velocity, peak_velocity, cv_bpm,
           duration_ms}``
    """
    start_ms: int = phrase_dict["start_ms"]
    end_ms: int   = phrase_dict["end_ms"]
    duration_ms   = max(1, end_ms - start_ms)

    window = [a for a in all_actions if start_ms <= a["at"] <= end_ms]
    if not window:
        return {
            "mean_pos": 50.0, "span": 0.0,
            "mean_velocity": 0.0, "peak_velocity": 0.0,
            "cv_bpm": 0.0, "duration_ms": duration_ms,
        }

    positions = [a["pos"] for a in window]
    mean_pos  = sum(positions) / len(positions)
    span      = max(positions) - min(positions)

    # Velocity at each action point (|Δpos / Δt|)
    velocities = []
    for i in range(1, len(window)):
        dt = max(1, window[i]["at"] - window[i - 1]["at"])
        dp = abs(window[i]["pos"] - window[i - 1]["pos"])
        velocities.append(dp / dt)
    mean_velocity = sum(velocities) / len(velocities) if velocities else 0.0

    # 90th-percentile velocity (robust peak)
    if velocities:
        sorted_v = sorted(velocities)
        idx90    = max(0, int(len(sorted_v) * 0.90) - 1)
        peak_velocity = sorted_v[idx90]
    else:
        peak_velocity = 0.0

    # BPM coefficient of variation across cycles in this phrase
    # We derive per-cycle BPM from the assessment dict if available,
    # but as a fallback we use the phrase-level bpm with cv_bpm = 0.
    cycles: List[dict] = phrase_dict.get("_cycles", [])
    if len(cycles) >= 2:
        bpms = [c.get("bpm", 0.0) for c in cycles if c.get("bpm", 0.0) > 0]
        if len(bpms) >= 2:
            mean_bpm = sum(bpms) / len(bpms)
            variance = sum((b - mean_bpm) ** 2 for b in bpms) / len(bpms)
            cv_bpm   = (variance ** 0.5) / mean_bpm if mean_bpm > 0 else 0.0
        else:
            cv_bpm = 0.0
    else:
        cv_bpm = 0.0

    return {
        "mean_pos":      round(mean_pos, 1),
        "span":          round(span, 1),
        "mean_velocity": round(mean_velocity, 4),
        "peak_velocity": round(peak_velocity, 4),
        "cv_bpm":        round(cv_bpm, 4),
        "duration_ms":   duration_ms,
    }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_phrase(
    phrase_dict: dict,
    metrics: dict,
    drone_threshold_ms: int = 90_000,
) -> List[str]:
    """Return a list of behavioral tag keys for one phrase.

    Parameters
    ----------
    phrase_dict : dict
        Phrase dict (must contain ``bpm``).
    metrics : dict
        Output of :func:`compute_phrase_metrics`.
    drone_threshold_ms : int
        Phrases longer than this with low BPM variation are tagged "drone".
    """
    tags: List[str] = []

    bpm          = phrase_dict.get("bpm", 0.0)
    mean_pos     = metrics["mean_pos"]
    span         = metrics["span"]
    mean_vel     = metrics["mean_velocity"]
    cv_bpm       = metrics["cv_bpm"]
    duration_ms  = metrics["duration_ms"]

    # stingy: full-range, fast, high-velocity
    if span > 75 and mean_vel > 0.35 and bpm > 120:
        tags.append("stingy")

    # giggle: tiny centered motion
    if span < 20 and 35 <= mean_pos <= 65:
        tags.append("giggle")

    # plateau: small but wider than giggle, still centered
    if 20 <= span < 40 and 35 <= mean_pos <= 65 and "giggle" not in tags:
        tags.append("plateau")

    # drift: centre of gravity in the wrong zone
    if span > 15 and (mean_pos < 30 or mean_pos > 70):
        tags.append("drift")

    # half_stroke: real motion but confined to one side
    if span > 30 and (mean_pos < 38 or mean_pos > 62) and "drift" not in tags:
        tags.append("half_stroke")

    # drone: long + monotone BPM
    if duration_ms > drone_threshold_ms and cv_bpm < 0.10:
        tags.append("drone")

    # lazy: slow and shallow
    if bpm < 60 and span < 50:
        tags.append("lazy")

    # frantic: too fast to feel
    if bpm > 200:
        tags.append("frantic")

    return tags


# ---------------------------------------------------------------------------
# Batch annotation
# ---------------------------------------------------------------------------

def annotate_phrases(
    phrases: List[dict],
    cycles: List[dict],
    all_actions: List[dict],
    drone_threshold_ms: int = 90_000,
) -> None:
    """Mutate each phrase dict in-place: add ``metrics`` and ``tags`` keys.

    Parameters
    ----------
    phrases : list[dict]
        Phrase dicts from ``AssessmentResult.to_dict()["phrases"]``.
    cycles : list[dict]
        All cycle dicts — used to attach per-cycle BPM for cv_bpm.
    all_actions : list[dict]
        Full funscript action list.
    drone_threshold_ms : int
        Passed to :func:`classify_phrase`.
    """
    # Build a lookup: which cycles fall inside each phrase?
    for ph in phrases:
        ph["_cycles"] = [
            c for c in cycles
            if c["start_ms"] >= ph["start_ms"] and c["end_ms"] <= ph["end_ms"]
        ]

    for ph in phrases:
        metrics = compute_phrase_metrics(ph, all_actions)
        tags    = classify_phrase(ph, metrics, drone_threshold_ms)
        ph["metrics"] = metrics
        ph["tags"]    = tags

    # Clean up the temporary key
    for ph in phrases:
        ph.pop("_cycles", None)
