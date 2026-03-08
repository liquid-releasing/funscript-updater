"""Tests for visualizations/chart_data.py — pure data computation."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from visualizations.chart_data import (
    AnnotationBand,
    PointSeries,
    _hex_to_rgb,
    _interpolate_color,
    _VELOCITY_STOPS,
    compute_annotation_bands,
    compute_chart_data,
    slice_bands,
    slice_series,
)

_ACTIONS = [
    {"at": 0,    "pos": 10},
    {"at": 100,  "pos": 90},
    {"at": 200,  "pos": 10},
    {"at": 300,  "pos": 90},
    {"at": 400,  "pos": 10},
]

_ASSESSMENT = {
    "phases": [
        {"start_ms": 0, "end_ms": 200, "label": "upward", "start_ts": "00:00:00.000", "end_ts": "00:00:00.200"},
        {"start_ms": 200, "end_ms": 400, "label": "downward", "start_ts": "00:00:00.200", "end_ts": "00:00:00.400"},
    ],
    "cycles": [
        {"start_ms": 0, "end_ms": 400, "label": "up -> down", "oscillation_count": 1,
         "start_ts": "00:00:00.000", "end_ts": "00:00:00.400"},
    ],
    "patterns": [
        {"pattern_label": "pattern A", "avg_duration_ms": 400, "cycle_count": 1,
         "cycles": [{"start_ms": 0, "end_ms": 400, "start_ts": "...", "end_ts": "..."}]},
    ],
    "phrases": [
        {"start_ms": 0, "end_ms": 400, "pattern_label": "pattern A", "bpm": 120.0,
         "cycle_count": 1, "start_ts": "...", "end_ts": "..."},
    ],
    "bpm_transitions": [
        {"at_ms": 200, "from_bpm": 120.0, "to_bpm": 150.0, "change_pct": 25.0,
         "at_ts": "00:00:00.200"},
    ],
}


class TestComputeChartData(unittest.TestCase):
    def test_empty_actions(self):
        result = compute_chart_data([])
        self.assertEqual(result.times_ms, [])
        self.assertEqual(result.positions, [])

    def test_output_lengths(self):
        result = compute_chart_data(_ACTIONS)
        n = len(_ACTIONS)
        self.assertEqual(len(result.times_ms),        n)
        self.assertEqual(len(result.positions),       n)
        self.assertEqual(len(result.velocities),      n)
        self.assertEqual(len(result.velocity_norm),   n)
        self.assertEqual(len(result.amplitude_norm),  n)
        self.assertEqual(len(result.colors_velocity), n)
        self.assertEqual(len(result.colors_amplitude),n)

    def test_times_and_positions_correct(self):
        result = compute_chart_data(_ACTIONS)
        self.assertEqual(result.times_ms, [0, 100, 200, 300, 400])
        self.assertEqual(result.positions, [10.0, 90.0, 10.0, 90.0, 10.0])

    def test_velocity_norm_in_range(self):
        result = compute_chart_data(_ACTIONS)
        for v in result.velocity_norm:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_amplitude_norm_in_range(self):
        result = compute_chart_data(_ACTIONS)
        for a in result.amplitude_norm:
            self.assertGreaterEqual(a, 0.0)
            self.assertLessEqual(a, 1.0)

    def test_colors_are_hex_strings(self):
        result = compute_chart_data(_ACTIONS)
        for c in result.colors_velocity + result.colors_amplitude:
            self.assertTrue(c.startswith("#"), f"Not a hex color: {c}")
            self.assertEqual(len(c), 7)

    def test_single_action(self):
        result = compute_chart_data([{"at": 0, "pos": 50}])
        self.assertEqual(len(result.times_ms), 1)
        self.assertAlmostEqual(result.amplitude_norm[0], 0.5)


class TestSliceSeries(unittest.TestCase):
    def setUp(self):
        self.series = compute_chart_data(_ACTIONS)

    def test_full_range_returns_all(self):
        sliced = slice_series(self.series, 0, 400)
        self.assertEqual(len(sliced.times_ms), 5)

    def test_narrow_range(self):
        sliced = slice_series(self.series, 100, 200)
        self.assertEqual(sliced.times_ms, [100, 200])

    def test_empty_range(self):
        sliced = slice_series(self.series, 500, 600)
        self.assertEqual(sliced.times_ms, [])

    def test_single_point(self):
        sliced = slice_series(self.series, 300, 300)
        self.assertEqual(sliced.times_ms, [300])

    def test_all_fields_sliced(self):
        sliced = slice_series(self.series, 100, 200)
        self.assertEqual(len(sliced.positions),        2)
        self.assertEqual(len(sliced.colors_velocity),  2)
        self.assertEqual(len(sliced.colors_amplitude), 2)


class TestComputeAnnotationBands(unittest.TestCase):
    def test_returns_list(self):
        bands = compute_annotation_bands(_ASSESSMENT)
        self.assertIsInstance(bands, list)

    def test_all_kinds_present(self):
        bands = compute_annotation_bands(_ASSESSMENT)
        kinds = {b.kind for b in bands}
        self.assertIn("phase",      kinds)
        self.assertIn("cycle",      kinds)
        self.assertIn("pattern",    kinds)
        self.assertIn("phrase",     kinds)
        self.assertIn("transition", kinds)

    def test_band_fields(self):
        bands = compute_annotation_bands(_ASSESSMENT)
        for b in bands:
            self.assertIsInstance(b.start_ms, int)
            self.assertIsInstance(b.end_ms,   int)
            self.assertIsInstance(b.label,    str)
            self.assertIsInstance(b.color,    str)

    def test_empty_assessment(self):
        bands = compute_annotation_bands({})
        self.assertEqual(bands, [])

    def test_transition_start_equals_end(self):
        bands = compute_annotation_bands(_ASSESSMENT)
        transitions = [b for b in bands if b.kind == "transition"]
        for t in transitions:
            self.assertEqual(t.start_ms, t.end_ms)


class TestSliceBands(unittest.TestCase):
    def setUp(self):
        self.bands = compute_annotation_bands(_ASSESSMENT)

    def test_full_range_includes_all(self):
        sliced = slice_bands(self.bands, 0, 400)
        self.assertEqual(len(sliced), len(self.bands))

    def test_narrow_range_excludes_non_overlapping(self):
        # Only include bands that overlap [50, 150]
        sliced = slice_bands(self.bands, 50, 150)
        for b in sliced:
            self.assertTrue(b.end_ms >= 50 and b.start_ms <= 150)

    def test_empty_result_for_out_of_range(self):
        sliced = slice_bands(self.bands, 10_000, 20_000)
        self.assertEqual(sliced, [])


class TestColorHelpers(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(_hex_to_rgb("#ff0000"), (255, 0, 0))
        self.assertEqual(_hex_to_rgb("#00ff00"), (0, 255, 0))
        self.assertEqual(_hex_to_rgb("#0000ff"), (0, 0, 255))

    def test_interpolate_at_zero(self):
        c = _interpolate_color(_VELOCITY_STOPS, 0.0)
        self.assertEqual(c, _VELOCITY_STOPS[0][1])

    def test_interpolate_at_one(self):
        c = _interpolate_color(_VELOCITY_STOPS, 1.0)
        self.assertEqual(c, _VELOCITY_STOPS[-1][1])

    def test_interpolate_clamps_below_zero(self):
        c = _interpolate_color(_VELOCITY_STOPS, -0.5)
        self.assertEqual(c, _VELOCITY_STOPS[0][1])

    def test_interpolate_clamps_above_one(self):
        c = _interpolate_color(_VELOCITY_STOPS, 1.5)
        self.assertEqual(c, _VELOCITY_STOPS[-1][1])

    def test_interpolate_midpoint_is_hex(self):
        c = _interpolate_color(_VELOCITY_STOPS, 0.5)
        self.assertTrue(c.startswith("#"))
        self.assertEqual(len(c), 7)


if __name__ == "__main__":
    unittest.main()
