# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for assessment/classifier.py — behavioral phrase classification."""

import unittest


# ---------------------------------------------------------------------------
# Tag registry
# ---------------------------------------------------------------------------

class TestTagRegistry(unittest.TestCase):

    def test_all_expected_tags_present(self):
        from assessment.classifier import TAGS
        expected = {"stingy", "giggle", "plateau", "drift", "half_stroke",
                    "drone", "lazy", "frantic", "ramp", "ambient"}
        self.assertEqual(set(TAGS.keys()), expected)

    def test_each_tag_has_required_fields(self):
        from assessment.classifier import TAGS
        for key, tag in TAGS.items():
            with self.subTest(tag=key):
                self.assertEqual(tag.key, key)
                self.assertTrue(tag.label)
                self.assertTrue(tag.description)
                self.assertTrue(tag.color)
                self.assertTrue(tag.suggested_transform)
                self.assertTrue(tag.fix_hint)


# ---------------------------------------------------------------------------
# compute_phrase_metrics
# ---------------------------------------------------------------------------

class TestComputePhraseMetrics(unittest.TestCase):

    def _phrase(self, start=0, end=10_000, bpm=120.0):
        return {"start_ms": start, "end_ms": end, "bpm": bpm}

    def test_empty_window_returns_defaults(self):
        from assessment.classifier import compute_phrase_metrics
        m = compute_phrase_metrics(self._phrase(end=1000), [])
        self.assertEqual(m["mean_pos"], 50.0)
        self.assertEqual(m["span"], 0.0)
        self.assertEqual(m["mean_velocity"], 0.0)
        self.assertEqual(m["peak_velocity"], 0.0)
        self.assertEqual(m["duration_ms"], 1000)

    def test_full_range_span(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [{"at": 0, "pos": 0}, {"at": 500, "pos": 100}, {"at": 1000, "pos": 0}]
        m = compute_phrase_metrics(self._phrase(end=1000), actions)
        self.assertEqual(m["span"], 100)

    def test_uniform_positions_zero_span(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [{"at": i * 100, "pos": 50} for i in range(10)]
        m = compute_phrase_metrics(self._phrase(end=900), actions)
        self.assertEqual(m["span"], 0)
        self.assertEqual(m["mean_pos"], 50.0)

    def test_duration_ms_matches_phrase_window(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [{"at": 1000, "pos": 50}, {"at": 5000, "pos": 80}]
        m = compute_phrase_metrics(self._phrase(start=1000, end=5000), actions)
        self.assertEqual(m["duration_ms"], 4000)

    def test_peak_velocity_gte_mean_velocity(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [{"at": i * 100, "pos": i % 2 * 100} for i in range(20)]
        m = compute_phrase_metrics(self._phrase(end=1900), actions)
        self.assertGreaterEqual(m["peak_velocity"], m["mean_velocity"])

    def test_cv_bpm_nonzero_with_varying_cycles(self):
        from assessment.classifier import compute_phrase_metrics
        phrase = {
            "start_ms": 0, "end_ms": 10_000, "bpm": 120.0,
            "_cycles": [{"bpm": 80.0}, {"bpm": 160.0}, {"bpm": 80.0}],
        }
        actions = [{"at": i * 100, "pos": i % 2 * 100} for i in range(100)]
        m = compute_phrase_metrics(phrase, actions)
        self.assertGreater(m["cv_bpm"], 0)

    def test_cv_bpm_zero_without_cycles(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [{"at": i * 100, "pos": i % 2 * 100} for i in range(20)]
        m = compute_phrase_metrics(self._phrase(end=1900), actions)
        self.assertEqual(m["cv_bpm"], 0.0)

    def test_out_of_window_actions_excluded(self):
        from assessment.classifier import compute_phrase_metrics
        actions = [
            {"at": 0,    "pos": 0},    # before window
            {"at": 1000, "pos": 50},   # inside
            {"at": 2000, "pos": 100},  # inside
            {"at": 5000, "pos": 999},  # after window
        ]
        m = compute_phrase_metrics(self._phrase(start=1000, end=2000), actions)
        self.assertEqual(m["span"], 50)


# ---------------------------------------------------------------------------
# classify_phrase
# ---------------------------------------------------------------------------

class TestClassifyPhrase(unittest.TestCase):

    def _classify(self, bpm=120, mean_pos=50, span=80, mean_vel=0.4,
                  cv_bpm=0.05, duration_ms=30_000):
        from assessment.classifier import classify_phrase
        phrase  = {"bpm": bpm}
        metrics = {
            "mean_pos": mean_pos, "span": span,
            "mean_velocity": mean_vel, "peak_velocity": mean_vel,
            "cv_bpm": cv_bpm, "duration_ms": duration_ms,
        }
        return classify_phrase(phrase, metrics)

    # --- stingy ---
    def test_stingy_all_conditions_met(self):
        self.assertIn("stingy", self._classify(bpm=150, span=85, mean_vel=0.45))

    def test_stingy_low_velocity_not_triggered(self):
        self.assertNotIn("stingy", self._classify(bpm=150, span=85, mean_vel=0.20))

    def test_stingy_low_bpm_not_triggered(self):
        self.assertNotIn("stingy", self._classify(bpm=100, span=85, mean_vel=0.45))

    def test_stingy_low_span_not_triggered(self):
        self.assertNotIn("stingy", self._classify(bpm=150, span=60, mean_vel=0.45))

    # --- giggle ---
    def test_giggle_detected(self):
        self.assertIn("giggle", self._classify(span=10, mean_pos=50, mean_vel=0.1, bpm=80))

    def test_giggle_off_centre_not_triggered(self):
        self.assertNotIn("giggle", self._classify(span=10, mean_pos=80, mean_vel=0.1, bpm=80))

    # --- plateau ---
    def test_plateau_detected(self):
        self.assertIn("plateau", self._classify(span=30, mean_pos=50, mean_vel=0.1, bpm=80))

    def test_plateau_not_when_giggle(self):
        # span < 20 triggers giggle first, plateau should be skipped
        tags = self._classify(span=10, mean_pos=50, mean_vel=0.1, bpm=80)
        self.assertIn("giggle", tags)
        self.assertNotIn("plateau", tags)

    # --- drift ---
    def test_drift_high_centre(self):
        self.assertIn("drift", self._classify(mean_pos=80, span=20, bpm=80, mean_vel=0.1))

    def test_drift_low_centre(self):
        self.assertIn("drift", self._classify(mean_pos=20, span=20, bpm=80, mean_vel=0.1))

    def test_drift_near_centre_not_triggered(self):
        self.assertNotIn("drift", self._classify(mean_pos=50, span=20, bpm=80, mean_vel=0.1))

    def test_drift_requires_minimum_span(self):
        # span ≤ 15 should not trigger drift even with extreme mean_pos
        self.assertNotIn("drift", self._classify(mean_pos=5, span=10, bpm=80, mean_vel=0.05))

    # --- half_stroke ---
    def test_half_stroke_upper(self):
        # mean_pos > 62 AND span > 30 AND no drift (drift requires span>15 AND pos>70)
        # mean_pos=65 is above 62 but below 70 so no drift
        self.assertIn("half_stroke", self._classify(mean_pos=65, span=35, bpm=80, mean_vel=0.1))

    def test_half_stroke_suppressed_when_drift(self):
        # mean_pos=80 triggers drift; half_stroke should not also fire
        tags = self._classify(mean_pos=80, span=35, bpm=80, mean_vel=0.1)
        self.assertIn("drift", tags)
        self.assertNotIn("half_stroke", tags)

    # --- drone ---
    def test_drone_long_uniform(self):
        self.assertIn("drone", self._classify(duration_ms=100_000, cv_bpm=0.02))

    def test_drone_short_not_triggered(self):
        self.assertNotIn("drone", self._classify(duration_ms=30_000, cv_bpm=0.02))

    def test_drone_high_cv_not_triggered(self):
        self.assertNotIn("drone", self._classify(duration_ms=100_000, cv_bpm=0.25))

    # --- lazy ---
    def test_lazy_slow_shallow(self):
        self.assertIn("lazy", self._classify(bpm=40, span=30, mean_vel=0.05))

    def test_lazy_fast_not_triggered(self):
        self.assertNotIn("lazy", self._classify(bpm=80, span=30, mean_vel=0.1))

    def test_lazy_deep_span_not_triggered(self):
        self.assertNotIn("lazy", self._classify(bpm=40, span=60, mean_vel=0.05))

    # --- frantic ---
    def test_frantic_above_200(self):
        self.assertIn("frantic", self._classify(bpm=250))

    def test_frantic_at_200_not_triggered(self):
        self.assertNotIn("frantic", self._classify(bpm=200))

    # --- multi-tag and clean ---
    def test_stingy_and_frantic_coexist(self):
        tags = self._classify(bpm=250, span=85, mean_vel=0.45)
        self.assertIn("stingy", tags)
        self.assertIn("frantic", tags)

    def test_clean_phrase_no_tags(self):
        # Well-behaved phrase: mid BPM, full span, centered, moderate velocity, some BPM variation
        tags = self._classify(bpm=120, mean_pos=50, span=80, mean_vel=0.2,
                              cv_bpm=0.20, duration_ms=30_000)
        self.assertEqual(tags, [])


# ---------------------------------------------------------------------------
# annotate_phrases
# ---------------------------------------------------------------------------

class TestAnnotatePhrases(unittest.TestCase):

    def _make_actions(self, start_ms, end_ms, n=20):
        step = max(1, (end_ms - start_ms) // n)
        return [{"at": start_ms + i * step, "pos": i % 2 * 100} for i in range(n)]

    def _phrase(self, start=0, end=10_000, bpm=120.0):
        return {
            "start_ms": start, "end_ms": end, "bpm": bpm,
            "pattern_label": "up -> down", "cycle_count": 10,
            "description": "", "oscillation_count": 10,
        }

    def test_tags_and_metrics_added_in_place(self):
        from assessment.classifier import annotate_phrases
        phrases = [self._phrase()]
        annotate_phrases(phrases, [], self._make_actions(0, 10_000))
        self.assertIn("tags", phrases[0])
        self.assertIn("metrics", phrases[0])

    def test_tags_is_list(self):
        from assessment.classifier import annotate_phrases
        phrases = [self._phrase()]
        annotate_phrases(phrases, [], self._make_actions(0, 10_000))
        self.assertIsInstance(phrases[0]["tags"], list)

    def test_metrics_has_required_keys(self):
        from assessment.classifier import annotate_phrases
        phrases = [self._phrase()]
        annotate_phrases(phrases, [], self._make_actions(0, 10_000))
        m = phrases[0]["metrics"]
        for key in ("mean_pos", "span", "mean_velocity", "peak_velocity", "cv_bpm", "duration_ms"):
            self.assertIn(key, m)

    def test_temp_cycles_key_removed(self):
        from assessment.classifier import annotate_phrases
        phrases = [self._phrase()]
        annotate_phrases(phrases, [], self._make_actions(0, 10_000))
        self.assertNotIn("_cycles", phrases[0])

    def test_multiple_phrases_all_annotated(self):
        from assessment.classifier import annotate_phrases
        phrases = [self._phrase(0, 10_000), self._phrase(10_000, 20_000, bpm=80)]
        actions = self._make_actions(0, 20_000, n=40)
        annotate_phrases(phrases, [], actions)
        for ph in phrases:
            self.assertIn("metrics", ph)
            self.assertIn("tags", ph)

    def test_drone_threshold_applied(self):
        from assessment.classifier import annotate_phrases
        # Long phrase + uniform BPM (no cycles → cv_bpm=0) → drone
        ph = self._phrase(0, 200_000, bpm=80)
        actions = self._make_actions(0, 200_000, n=200)
        annotate_phrases([ph], [], actions, drone_threshold_ms=90_000)
        self.assertIn("drone", ph["tags"])

    def test_cycles_used_for_cv_bpm(self):
        from assessment.classifier import annotate_phrases
        ph = self._phrase(0, 10_000, bpm=120)
        cycles = [
            {"start_ms": 0,    "end_ms": 2000, "bpm": 80.0},
            {"start_ms": 2000, "end_ms": 4000, "bpm": 160.0},
            {"start_ms": 4000, "end_ms": 6000, "bpm": 80.0},
        ]
        actions = self._make_actions(0, 10_000)
        annotate_phrases([ph], cycles, actions)
        # Varying cycle BPMs → cv_bpm > 0
        self.assertGreater(ph["metrics"]["cv_bpm"], 0)


if __name__ == "__main__":
    unittest.main()
