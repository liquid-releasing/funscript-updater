"""
Generate the Big Buck Bunny demo funscripts for FunscriptForge.

Called automatically on first launch if the files are missing.
Safe to re-run — overwrites existing demo files.

Usage:
    python demo/generate_demo.py
"""
import json
import os
import random
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

RAW_PATH    = os.path.join(_HERE, "big_buck_bunny.raw.funscript")
FORGED_PATH = os.path.join(_HERE, "big_buck_bunny.forged.funscript")


def _make_phrase(start_ms, duration_ms, bpm, amplitude, center, noise=5, rng=None):
    if rng is None:
        rng = random
    actions = []
    cycle_ms = 60000 / bpm
    t = start_ms
    phase = 0
    while t < start_ms + duration_ms:
        top = center + amplitude / 2 + rng.uniform(-noise, noise)
        bot = center - amplitude / 2 + rng.uniform(-noise, noise)
        pos = int(round(top)) if phase % 2 == 0 else int(round(bot))
        actions.append({"at": int(t), "pos": max(0, min(100, pos))})
        t += cycle_ms / 2
        phase += 1
    return actions


def generate_raw(path: str) -> None:
    """Generate big_buck_bunny.raw.funscript with all 8 behavioral issues."""
    rng = random.Random(42)

    # (start_ms, duration_ms, bpm, amplitude, center, noise)
    # Big Buck Bunny runtime: 9:56 = 596,000 ms
    segments = [
        (0,       30_000,  45,   30,   50,   8),   # lazy
        (30_000,  20_000,  80,   15,   50,   3),   # giggle
        (50_000,  25_000, 120,   85,   50,   5),   # stingy
        (75_000,  40_000,  95,   20,   72,   5),   # drift (up)
        (115_000, 30_000, 110,   45,   25,   6),   # drift (down)
        (145_000, 60_000, 125,   35,   50,   4),   # plateau
        (205_000, 15_000, 240,   80,   50,   6),   # frantic
        (220_000, 90_000, 118,   75,   50,   2),   # drone
        (310_000, 25_000,  50,   25,   50,   7),   # lazy
        (335_000, 35_000, 130,   90,   50,   5),   # stingy
        (370_000, 20_000,  85,   32,   68,   5),   # half_stroke
        (390_000, 50_000, 105,   60,   50,   6),   # normal
        (440_000, 30_000, 220,   78,   50,   5),   # frantic
        (470_000, 60_000, 115,   40,   50,   3),   # plateau
        (530_000, 40_000,  90,   55,   50,   8),   # normal
        (570_000, 26_000,  60,   35,   50,  10),   # lazy (outro)
    ]

    actions = []
    for seg in segments:
        actions.extend(_make_phrase(*seg, rng=rng))
    actions.sort(key=lambda a: a["at"])
    seen: set = set()
    deduped = [a for a in actions if a["at"] not in seen and not seen.add(a["at"])]

    doc = {"version": "1.0", "inverted": False, "range": 90, "actions": deduped}
    with open(path, "w") as f:
        json.dump(doc, f, indent=2)


def generate_forged(raw_path: str, forged_path: str) -> None:
    """Generate big_buck_bunny.forged.funscript from the raw version."""

    # Assess the raw file to get phrase boundaries
    assessment_path = os.path.join(_ROOT, "output", "bbb_demo.assessment.json")
    os.makedirs(os.path.dirname(assessment_path), exist_ok=True)
    result = subprocess.run(
        [sys.executable, os.path.join(_ROOT, "cli.py"), "assess",
         raw_path, "--output", assessment_path],
        capture_output=True, cwd=_ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Assessment failed: {result.stderr.decode()}")

    with open(raw_path) as f:
        raw = json.load(f)
    with open(assessment_path) as f:
        assessment = json.load(f)

    phrases = assessment["phrases"]
    actions = [dict(a) for a in raw["actions"]]

    def _scale(actions, scale, s, e):
        return [{"at": a["at"], "pos": max(0, min(100, int(round(50 + (a["pos"] - 50) * scale))))}
                if s <= a["at"] < e else dict(a) for a in actions]

    def _recenter(actions, target, s, e):
        ph = [a for a in actions if s <= a["at"] < e]
        if not ph:
            return actions
        mid = (max(a["pos"] for a in ph) + min(a["pos"] for a in ph)) / 2
        off = int(round(target - mid))
        return [{"at": a["at"], "pos": max(0, min(100, a["pos"] + off))}
                if s <= a["at"] < e else dict(a) for a in actions]

    def _smooth(actions, strength, s, e):
        ph = [a for a in actions if s <= a["at"] < e]
        other = [a for a in actions if not (s <= a["at"] < e)]
        sm = []
        for i, a in enumerate(ph):
            if 0 < i < len(ph) - 1:
                b = int(round(a["pos"] * (1 - strength)
                              + (ph[i - 1]["pos"] + ph[i + 1]["pos"]) / 2 * strength))
                sm.append({"at": a["at"], "pos": max(0, min(100, b))})
            else:
                sm.append(dict(a))
        return sorted(other + sm, key=lambda a: a["at"])

    # (phrase_index, fix, arg)
    fixes = [
        (0,  "scale",    1.5),
        (1,  "scale",    2.0),
        (2,  "scale",    0.78),
        (3,  "recenter", 50),
        (4,  "recenter", 50),
        (5,  "scale",    1.45),
        (6,  "scale",    0.6),
        (7,  "smooth",   0.35),
        (8,  "scale",    1.5),
        (9,  "scale",    0.8),
        (10, "recenter", 50),
        (11, "scale",    1.2),
        (12, "scale",    0.55),
        (13, "scale",    1.35),
        (14, "scale",    1.1),
        (15, "scale",    1.1),
    ]

    for (i, kind, arg) in fixes:
        if i >= len(phrases):
            continue
        s, e = phrases[i]["start_ms"], phrases[i]["end_ms"]
        if kind == "scale":
            actions = _scale(actions, arg, s, e)
        elif kind == "recenter":
            actions = _recenter(actions, arg, s, e)
        elif kind == "smooth":
            actions = _smooth(actions, arg, s, e)

    doc = {
        "version": "1.0",
        "inverted": False,
        "range": 90,
        "_forge_log": {
            "version": "0.1.0",
            "source": "big_buck_bunny.raw.funscript",
            "note": "Example forged output — FunscriptForge documentation demo",
        },
        "actions": actions,
    }
    with open(forged_path, "w") as f:
        json.dump(doc, f, indent=2)


def ensure_demo_files() -> None:
    """Generate demo files if either is missing. Called on app startup."""
    if not os.path.isfile(RAW_PATH) or not os.path.isfile(FORGED_PATH):
        generate_raw(RAW_PATH)
        generate_forged(RAW_PATH, FORGED_PATH)


if __name__ == "__main__":
    print("Generating demo funscripts...")
    generate_raw(RAW_PATH)
    print(f"  raw:    {RAW_PATH}")
    generate_forged(RAW_PATH, FORGED_PATH)
    print(f"  forged: {FORGED_PATH}")
    print("Done.")
