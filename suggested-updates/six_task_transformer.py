import json
import math
import copy
import bisect
import os

# ------------------------------------------------------------
# DIRECTORY SETUP
# ------------------------------------------------------------
WORK = r"working_gen"

INPUT = os.path.join(WORK, "input.funscript")

AUTO_WINDOWS_JSON   = os.path.join(WORK, "auto_mode_windows.json")
RAW_WINDOWS_JSON    = os.path.join(WORK, "raw_windows.json")
MANUAL_PERF_JSON    = os.path.join(WORK, "manual_performance.json")
MANUAL_BREAK_JSON   = os.path.join(WORK, "manual_break.json")

CYCLES_JSON         = os.path.join(WORK, "cycle_segments.json")
BEATS_JSON          = os.path.join(WORK, "detected_beats.json")

MERGED_WINDOWS_JSON = os.path.join(WORK, "merged_mode_windows.json")
OUTPUT              = os.path.join(WORK, "final_output.funscript")
LOG_PATH            = os.path.join(WORK, "transform_log.txt")

# ------------------------------------------------------------
# TASK 1 DEFAULT MODE SETTINGS
# ------------------------------------------------------------
TIME_SCALE = 2.0
AMPLITUDE_SCALE = 2.0
LPF_DEFAULT = 0.10

# ------------------------------------------------------------
# TASK 2 PERFORMANCE MODE SETTINGS
# ------------------------------------------------------------
MAX_VELOCITY = 0.32
REVERSAL_SOFTEN = 0.62
HEIGHT_BLEND = 0.75
COMPRESS_BOTTOM = 15
COMPRESS_TOP = 92
LPF_PERFORMANCE = 0.16
TIMING_JITTER_MS = 3

# ------------------------------------------------------------
# TASK 3 BREAK MODE SETTINGS
# ------------------------------------------------------------
BREAK_AMPLITUDE_REDUCE = 0.40
LPF_BREAK = 0.30

# ------------------------------------------------------------
# TASK 5 CYCLE-AWARE DYNAMICS
# ------------------------------------------------------------
CYCLE_DYNAMICS_STRENGTH = 0.10
CYCLE_DYNAMICS_CENTER = 50

# ------------------------------------------------------------
# TASK 6 BEAT-SYNCED ACCENTS
# ------------------------------------------------------------
BEAT_ACCENT_RADIUS_MS = 40
BEAT_ACCENT_AMOUNT = 4

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def parse_timestamp(ts):
    parts = ts.split(":")
    parts = [p.strip() for p in parts]

    if len(parts) == 3:
        h, m, s = parts
    elif len(parts) == 2:
        h = 0
        m, s = parts
    else:
        h = 0
        m = 0
        s = parts[0]

    if "." in s:
        sec, ms = s.split(".")
        ms = int(ms.ljust(3, "0"))
    else:
        sec = s
        ms = 0

    return (
        int(h) * 3600000 +
        int(m) * 60000 +
        int(sec) * 1000 +
        ms
    )

def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end < b_start or a_start > b_end)

def low_pass_filter(values, strengths):
    out = [values[0]]
    for i in range(1, len(values)):
        prev = out[-1]
        curr = values[i]
        strength = strengths[i]
        out.append(prev + (curr - prev) * (1 - strength))
    return out

# ------------------------------------------------------------
# LOG BUFFER
# ------------------------------------------------------------
log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

# ------------------------------------------------------------
# LOAD FUNSCRIPT
# ------------------------------------------------------------
with open(INPUT) as f:
    data = json.load(f)

actions = data["actions"]
original_actions = copy.deepcopy(actions)

# ------------------------------------------------------------
# LOAD AUTO WINDOWS (ms)
# ------------------------------------------------------------
with open(AUTO_WINDOWS_JSON) as f:
    auto = json.load(f)

auto_perf   = [(int(w["start"]), int(w["end"])) for w in auto.get("performance", [])]
auto_break  = [(int(w["start"]), int(w["end"])) for w in auto.get("break", [])]
auto_default = [(int(w["start"]), int(w["end"])) for w in auto.get("default", [])]

log(f"Auto performance windows: {len(auto_perf)}")
log(f"Auto break windows: {len(auto_break)}")
log(f"Auto default windows: {len(auto_default)}")

# ------------------------------------------------------------
# LOAD MANUAL WINDOWS (timestamps) AND CONVERT TO ms
# ------------------------------------------------------------
def load_manual_ts_windows(path, label):
    if not os.path.exists(path):
        log(f"{label}: file not found, treating as empty.")
        return []
    with open(path) as f:
        data = json.load(f)
    out = []
    for w in data:
        start_ms = parse_timestamp(w["start"])
        end_ms = parse_timestamp(w["end"])
        out.append((start_ms, end_ms, w.get("label", "")))
    log(f"{label}: loaded {len(out)} windows.")
    return out

manual_perf  = load_manual_ts_windows(MANUAL_PERF_JSON,  "Manual performance")
manual_break = load_manual_ts_windows(MANUAL_BREAK_JSON, "Manual break")

# ------------------------------------------------------------
# LOAD RAW WINDOWS (timestamps) AND CONVERT TO ms (Task 4)
# ------------------------------------------------------------
raw_windows_ts = []
if os.path.exists(RAW_WINDOWS_JSON):
    with open(RAW_WINDOWS_JSON) as f:
        raw_data = json.load(f)
    for w in raw_data:
        start_ms = parse_timestamp(w["start"])
        end_ms = parse_timestamp(w["end"])
        raw_windows_ts.append((start_ms, end_ms, w.get("label", "")))
    log(f"Raw windows: loaded {len(raw_windows_ts)} windows.")
else:
    log("Raw windows: file not found, treating as empty.")

RAW_MS = [(s, e) for (s, e, _) in raw_windows_ts]

def in_raw_window(t):
    return any(start <= t <= end for start, end in RAW_MS)

# ------------------------------------------------------------
# MERGE MANUAL + AUTO WINDOWS (manual overrides auto)
# ------------------------------------------------------------
def filter_auto_with_manual(auto_list, manual_list, label):
    """Remove auto windows that overlap any manual window."""
    filtered = []
    removed = []
    for a_start, a_end in auto_list:
        keep = True
        for m_start, m_end, _ in manual_list:
            if overlaps(a_start, a_end, m_start, m_end):
                keep = False
                removed.append((a_start, a_end))
                break
        if keep:
            filtered.append((a_start, a_end))
    log(f"{label}: auto before={len(auto_list)}, after={len(filtered)}, removed={len(removed)}")
    return filtered, removed

auto_perf_filtered, removed_perf = filter_auto_with_manual(auto_perf, manual_perf, "Performance windows")
auto_break_filtered, removed_break = filter_auto_with_manual(auto_break, manual_break, "Break windows")

# Build final performance/break lists: manual (ms) + filtered auto
PERFORMANCE_WINDOWS = []
for s, e, lbl in manual_perf:
    PERFORMANCE_WINDOWS.append((s, e))
for s, e in auto_perf_filtered:
    PERFORMANCE_WINDOWS.append((s, e))

BREAK_WINDOWS = []
for s, e, lbl in manual_break:
    BREAK_WINDOWS.append((s, e))
for s, e in auto_break_filtered:
    BREAK_WINDOWS.append((s, e))

DEFAULT_WINDOWS = auto_default[:]  # unchanged

log(f"Final performance windows: {len(PERFORMANCE_WINDOWS)}")
log(f"Final break windows: {len(BREAK_WINDOWS)}")
log(f"Final default windows: {len(DEFAULT_WINDOWS)}")

# ------------------------------------------------------------
# SAVE MERGED WINDOWS SNAPSHOT (for inspection)
# ------------------------------------------------------------
merged_snapshot = {
    "performance": [{"start": s, "end": e} for (s, e) in PERFORMANCE_WINDOWS],
    "break": [{"start": s, "end": e} for (s, e) in BREAK_WINDOWS],
    "default": [{"start": s, "end": e} for (s, e) in DEFAULT_WINDOWS],
    "raw": [{"start": s, "end": e} for (s, e) in RAW_MS],
}
with open(MERGED_WINDOWS_JSON, "w") as f:
    json.dump(merged_snapshot, f, indent=2)
log(f"Merged windows snapshot written to {MERGED_WINDOWS_JSON}")

# ------------------------------------------------------------
# WINDOW MEMBERSHIP HELPERS
# ------------------------------------------------------------
def in_perf_window(t):
    return any(start <= t <= end for start, end in PERFORMANCE_WINDOWS)

def in_break_window(t):
    return any(start <= t <= end for start, end in BREAK_WINDOWS)

def in_default_window(t):
    return any(start <= t <= end for start, end in DEFAULT_WINDOWS)

# ------------------------------------------------------------
# LOAD CYCLES (Task 5) AND BEATS (Task 6)
# ------------------------------------------------------------
try:
    with open(CYCLES_JSON) as f:
        cycles = json.load(f)
    log(f"Loaded {len(cycles)} cycles.")
except FileNotFoundError:
    cycles = []
    log("No cycle_segments.json found; Task 5 will be inactive.")

try:
    with open(BEATS_JSON) as f:
        beats = json.load(f)
    log(f"Loaded {len(beats)} beats.")
except FileNotFoundError:
    beats = []
    log("No detected_beats.json found; Task 6 will be inactive.")

cycle_ranges = [(c["start"], c["end"]) for c in cycles]
cycle_midpoints = [(c["start"] + c["end"]) / 2 for c in cycles]

beat_times = [b["time"] for b in beats]
beat_times.sort()

def cycle_phase_factor(t):
    """0..1, strongest at cycle midpoint."""
    for (start, end), mid in zip(cycle_ranges, cycle_midpoints):
        if start <= t <= end:
            span = end - start
            if span <= 0:
                return 0.0
            x = (t - start) / span
            return 0.5 * (1 - math.cos(2 * math.pi * x))
    return 0.0

def is_near_beat(t):
    if not beat_times:
        return 0
    idx = bisect.bisect_left(beat_times, t)
    candidates = []
    if idx < len(beat_times):
        candidates.append(beat_times[idx])
    if idx > 0:
        candidates.append(beat_times[idx - 1])
    nearest = min(candidates, key=lambda bt: abs(bt - t))
    return 1 if abs(nearest - t) <= BEAT_ACCENT_RADIUS_MS else 0

# ------------------------------------------------------------
# TASK 1 — HALF SPEED (EXCEPT PERFORMANCE WINDOWS)
# ------------------------------------------------------------
for a in actions:
    t = a["at"]
    if not in_perf_window(t):
        a["at"] = int(t * TIME_SCALE)

# ------------------------------------------------------------
# TASK 1 — DOUBLE AMPLITUDE
# ------------------------------------------------------------
for a in actions:
    centered = a["pos"] - 50
    scaled = centered * AMPLITUDE_SCALE
    new_pos = 50 + scaled
    a["pos"] = max(0, min(100, int(new_pos)))

# ------------------------------------------------------------
# TASKS 2–6 — MAIN LOOP
# ------------------------------------------------------------
for i in range(2, len(actions)):
    t = actions[i]["at"]

    # TASK 4 — RAW PRESERVE
    if in_raw_window(t):
        actions[i]["at"] = original_actions[i]["at"]
        actions[i]["pos"] = original_actions[i]["pos"]
        continue

    # TASK 2 — PERFORMANCE MODE
    if in_perf_window(t):
        dt = actions[i]["at"] - actions[i-1]["at"]
        if abs(dt) < TIMING_JITTER_MS:
            actions[i]["at"] = actions[i-1]["at"] + TIMING_JITTER_MS

        p0 = actions[i-1]["pos"]
        p1 = actions[i]["pos"]
        t0 = actions[i-1]["at"]
        t1 = actions[i]["at"]
        dt = max(1, t1 - t0)
        vel = (p1 - p0) / dt

        if abs(vel) > MAX_VELOCITY:
            p1 = p0 + math.copysign(MAX_VELOCITY * dt, vel)
            actions[i]["pos"] = int(p1)

        p_prev2 = actions[i-2]["pos"]
        p_prev = actions[i-1]["pos"]
        p_curr = actions[i]["pos"]

        dir1 = p_prev - p_prev2
        dir2 = p_curr - p_prev

        if dir1 * dir2 < 0:
            softened = p_prev + dir2 * (1 - REVERSAL_SOFTEN)
            blended = softened * (1 - HEIGHT_BLEND) + p_curr * HEIGHT_BLEND
            blended = max(COMPRESS_BOTTOM, min(COMPRESS_TOP, blended))
            actions[i]["pos"] = int(blended)

    # TASK 3 — BREAK MODE
    elif in_break_window(t):
        p = actions[i]["pos"]
        reduced = p + (50 - p) * BREAK_AMPLITUDE_REDUCE
        actions[i]["pos"] = int(reduced)

    # TASK 5 — CYCLE-AWARE DYNAMICS
    factor = cycle_phase_factor(t)
    if factor > 0:
        p = actions[i]["pos"]
        delta = (p - CYCLE_DYNAMICS_CENTER) * CYCLE_DYNAMICS_STRENGTH * factor
        actions[i]["pos"] = max(0, min(100, int(p + delta)))

    # TASK 6 — BEAT ACCENTS
    if is_near_beat(t):
        p = actions[i]["pos"]
        if p >= 50:
            p_acc = p + BEAT_ACCENT_AMOUNT
        else:
            p_acc = p - BEAT_ACCENT_AMOUNT
        actions[i]["pos"] = max(0, min(100, int(p_acc)))

# ------------------------------------------------------------
# FINAL SMOOTHING
# ------------------------------------------------------------
positions = [a["pos"] for a in actions]
strengths = []

for a in actions:
    t = a["at"]
    if in_raw_window(t):
        strengths.append(0.0)
    elif in_perf_window(t):
        strengths.append(LPF_PERFORMANCE)
    elif in_break_window(t):
        strengths.append(LPF_BREAK)
    else:
        strengths.append(LPF_DEFAULT)

smoothed = low_pass_filter(positions, strengths)

for i, p in enumerate(smoothed):
    actions[i]["pos"] = int(p)

# ------------------------------------------------------------
# SAVE OUTPUT + LOG
# ------------------------------------------------------------
with open(OUTPUT, "w") as f:
    json.dump(data, f, indent=2)
log(f"Created final output: {OUTPUT}")

with open(LOG_PATH, "w") as f:
    for line in log_lines:
        f.write(line + "\n")
print(f"Log written to {LOG_PATH}")
