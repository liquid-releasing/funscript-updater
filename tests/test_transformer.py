"""Unit tests for suggested_updates/transformer.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import tempfile
import unittest

from assessment.analyzer import FunscriptAnalyzer
from suggested_updates.transformer import FunscriptTransformer
from suggested_updates.config import TransformerConfig

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.funscript")


def _make_transformer(bpm_threshold=120.0):
    """Helper: return a transformer pre-loaded with fixture + assessment."""
    analyzer = FunscriptAnalyzer()
    analyzer.load(FIXTURE)
    assessment = analyzer.analyze()

    cfg = TransformerConfig(bpm_threshold=bpm_threshold)
    transformer = FunscriptTransformer(cfg)
    transformer.load_funscript(FIXTURE)
    transformer.load_assessment(assessment)
    return transformer


class TestFunscriptTransformer(unittest.TestCase):
    def test_load_funscript(self):
        t = _make_transformer()
        self.assertGreater(len(t._actions), 0)

    def test_load_assessment_populates_phrases(self):
        t = _make_transformer()
        self.assertGreater(len(t._phrases), 0)

    def test_overall_bpm_set(self):
        t = _make_transformer()
        self.assertGreater(t._overall_bpm, 0.0)

    def test_transform_returns_actions(self):
        t = _make_transformer()
        actions = t.transform()
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)

    def test_transform_output_positions_in_range(self):
        t = _make_transformer()
        actions = t.transform()
        for a in actions:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_transform_timestamps_non_negative(self):
        t = _make_transformer()
        actions = t.transform()
        for a in actions:
            self.assertGreaterEqual(a["at"], 0)

    def test_save_produces_valid_funscript(self):
        t = _make_transformer()
        t.transform()

        with tempfile.NamedTemporaryFile(suffix=".funscript", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            t.save(tmp_path)
            with open(tmp_path) as f:
                data = json.load(f)
            self.assertIn("actions", data)
            self.assertGreater(len(data["actions"]), 0)
        finally:
            os.unlink(tmp_path)

    def test_get_log_returns_list(self):
        t = _make_transformer()
        t.transform()
        log = t.get_log()
        self.assertIsInstance(log, list)
        self.assertGreater(len(log), 0)

    def test_very_high_threshold_passes_all_through(self):
        """With threshold above any phrase BPM, all positions should match original."""
        t = _make_transformer(bpm_threshold=99999.0)
        import copy
        orig = copy.deepcopy(t._original_actions)
        t.transform()
        for i, a in enumerate(t._actions):
            self.assertEqual(a["pos"], orig[i]["pos"])

    def test_zero_threshold_transforms_all(self):
        """With threshold=0, all phrases qualify for transform; no action is pass-through."""
        t = _make_transformer(bpm_threshold=0.0)
        t.transform()
        log = " ".join(t.get_log())
        self.assertIn("0 actions passed through", log)

    def test_time_scale_applied_globally(self):
        """time_scale != 1.0 should scale all timestamps."""
        import copy
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        assessment = analyzer.analyze()

        cfg = TransformerConfig(bpm_threshold=99999.0, time_scale=2.0)
        t = FunscriptTransformer(cfg)
        t.load_funscript(FIXTURE)
        t.load_assessment(assessment)
        orig = copy.deepcopy(t._original_actions)
        t.transform()

        for i, a in enumerate(t._actions):
            self.assertEqual(a["at"], orig[i]["at"] * 2)


class TestTransformerConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = TransformerConfig()
        self.assertEqual(cfg.bpm_threshold, 120.0)
        self.assertEqual(cfg.amplitude_scale, 2.0)
        self.assertEqual(cfg.time_scale, 1.0)

    def test_config_round_trip(self):
        cfg = TransformerConfig(bpm_threshold=90.0, amplitude_scale=1.5)
        d = cfg.to_dict()
        restored = TransformerConfig.from_dict(d)
        self.assertEqual(restored.bpm_threshold, 90.0)
        self.assertEqual(restored.amplitude_scale, 1.5)

    def test_config_save_load(self):
        cfg = TransformerConfig(lpf_default=0.25)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            cfg.save(tmp_path)
            loaded = TransformerConfig.load(tmp_path)
            self.assertEqual(loaded.lpf_default, 0.25)
        finally:
            os.unlink(tmp_path)

    def test_from_dict_ignores_unknown_keys(self):
        cfg = TransformerConfig.from_dict({"bpm_threshold": 80.0, "unknown_key": "ignored"})
        self.assertEqual(cfg.bpm_threshold, 80.0)


if __name__ == "__main__":
    unittest.main()
