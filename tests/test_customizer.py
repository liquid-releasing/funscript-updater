"""Unit tests for user_customization/customizer.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import tempfile
import unittest

from assessment.analyzer import FunscriptAnalyzer
from pattern_catalog.transformer import FunscriptTransformer
from user_customization.customizer import WindowCustomizer
from user_customization.config import CustomizerConfig

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.funscript")


def _make_transformed_funscript(tmp_path: str) -> str:
    """Run the transformer on the fixture and save to tmp_path."""
    analyzer = FunscriptAnalyzer()
    analyzer.load(FIXTURE)
    assessment = analyzer.analyze()

    transformer = FunscriptTransformer()
    transformer.load_funscript(FIXTURE)
    transformer.load_assessment(assessment)
    transformer.transform()
    transformer.save(tmp_path)
    return tmp_path


def _make_assessment_file(tmp_path: str) -> str:
    analyzer = FunscriptAnalyzer()
    analyzer.load(FIXTURE)
    result = analyzer.analyze()
    result.save(tmp_path)
    return tmp_path


class TestWindowCustomizer(unittest.TestCase):
    def setUp(self):
        self.tmp_funscript = tempfile.NamedTemporaryFile(
            suffix=".funscript", delete=False, mode="w"
        ).name
        self.tmp_assessment = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ).name
        _make_transformed_funscript(self.tmp_funscript)
        _make_assessment_file(self.tmp_assessment)

    def tearDown(self):
        for p in [self.tmp_funscript, self.tmp_assessment]:
            if os.path.exists(p):
                os.unlink(p)

    def test_load_funscript(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        self.assertGreater(len(c._actions), 0)

    def test_load_assessment_from_file(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        self.assertGreater(len(c._cycles), 0)

    def test_customize_returns_actions(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        actions = c.customize()
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)

    def test_customize_positions_in_range(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        actions = c.customize()
        for a in actions:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_save_produces_valid_funscript(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        c.customize()

        out = tempfile.NamedTemporaryFile(suffix=".funscript", delete=False).name
        try:
            c.save(out)
            with open(out) as f:
                data = json.load(f)
            self.assertIn("actions", data)
            self.assertGreater(len(data["actions"]), 0)
        finally:
            os.unlink(out)

    def test_manual_perf_window_loaded(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump([{"start": "00:00:00.500", "end": "00:00:03.000", "label": "test"}], f)
            perf_path = f.name
        try:
            c.load_manual_overrides(perf_path=perf_path)
            self.assertEqual(len(c._perf_windows), 1)
            self.assertEqual(c._perf_windows[0], (500, 3000, {}))
        finally:
            os.unlink(perf_path)

    def test_missing_window_file_treated_as_empty(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        c.load_manual_overrides(perf_path="/nonexistent/path.json")
        self.assertEqual(len(c._perf_windows), 0)

    def test_get_log_returns_list(self):
        c = WindowCustomizer()
        c.load_funscript(self.tmp_funscript)
        c.load_assessment_from_file(self.tmp_assessment)
        c.customize()
        log = c.get_log()
        self.assertIsInstance(log, list)
        self.assertGreater(len(log), 0)


class TestCustomizerConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = CustomizerConfig()
        self.assertEqual(cfg.max_velocity, 0.32)
        self.assertEqual(cfg.beat_accent_radius_ms, 40)

    def test_config_round_trip(self):
        cfg = CustomizerConfig(beat_accent_amount=8)
        d = cfg.to_dict()
        restored = CustomizerConfig.from_dict(d)
        self.assertEqual(restored.beat_accent_amount, 8)

    def test_config_save_load(self):
        cfg = CustomizerConfig(lpf_break=0.5)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            cfg.save(tmp_path)
            loaded = CustomizerConfig.load(tmp_path)
            self.assertEqual(loaded.lpf_break, 0.5)
        finally:
            os.unlink(tmp_path)

    def test_from_dict_ignores_unknown_keys(self):
        cfg = CustomizerConfig.from_dict({"max_velocity": 0.5, "unknown": "ignored"})
        self.assertEqual(cfg.max_velocity, 0.5)


if __name__ == "__main__":
    unittest.main()
