# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""End-to-end integration test: assess → transform → customize chain.

Uses the same sample.funscript fixture as the unit tests.
"""

import json
import os
import sys
import tempfile
import unittest

# Allow imports from the project root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from assessment.analyzer import FunscriptAnalyzer, AnalyzerConfig
from pattern_catalog import FunscriptTransformer, TransformerConfig
from user_customization import WindowCustomizer, CustomizerConfig
from ui.common.project import Project
from ui.common.pipeline import run_pipeline, run_pipeline_in_memory
from ui.common.work_items import ItemType

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.funscript")


class TestAssessTransformCustomizeChain(unittest.TestCase):
    """Verify that the three stages chain correctly without errors."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _tmp(self, filename):
        return os.path.join(self.tmp, filename)

    # ------------------------------------------------------------------
    # Stage 1 — Assessment
    # ------------------------------------------------------------------

    def test_assessment_produces_result(self):
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        result = analyzer.analyze()
        self.assertIsNotNone(result)
        self.assertGreater(result.bpm, 0)
        self.assertGreater(len(result.phases), 0)

    def test_assessment_save_load_round_trip(self):
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        result = analyzer.analyze()
        path = self._tmp("assessment.json")
        result.save(path)
        self.assertTrue(os.path.exists(path))
        loaded = type(result).load(path)
        self.assertAlmostEqual(loaded.bpm, result.bpm, places=2)

    # ------------------------------------------------------------------
    # Stage 2 — Transform
    # ------------------------------------------------------------------

    def test_transform_produces_valid_funscript(self):
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        assessment = analyzer.analyze()

        transformer = FunscriptTransformer()
        transformer.load_funscript(FIXTURE)
        transformer.load_assessment(assessment)
        transformer.transform()

        out = self._tmp("transformed.funscript")
        transformer.save(out)
        self.assertTrue(os.path.exists(out))

        with open(out) as f:
            data = json.load(f)
        actions = data["actions"]
        self.assertGreater(len(actions), 0)
        for a in actions:
            self.assertIn("at", a)
            self.assertIn("pos", a)
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    # ------------------------------------------------------------------
    # Stage 3 — Customize
    # ------------------------------------------------------------------

    def test_customize_produces_valid_funscript(self):
        # Stage 1
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        assessment = analyzer.analyze()

        # Stage 2
        transformer = FunscriptTransformer()
        transformer.load_funscript(FIXTURE)
        transformer.load_assessment(assessment)
        transformer.transform()
        transformed = self._tmp("transformed.funscript")
        transformer.save(transformed)

        # Stage 3
        customizer = WindowCustomizer()
        customizer.load_funscript(transformed)
        customizer.load_assessment(assessment)
        customizer.customize()
        out = self._tmp("customized.funscript")
        customizer.save(out)
        self.assertTrue(os.path.exists(out))

        with open(out) as f:
            data = json.load(f)
        actions = data["actions"]
        self.assertGreater(len(actions), 0)
        for a in actions:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    # ------------------------------------------------------------------
    # Full chain via run_pipeline
    # ------------------------------------------------------------------

    def test_run_pipeline_writes_all_outputs(self):
        project = Project.from_funscript(FIXTURE)
        # Tag first item as performance so window export produces a file.
        if project.work_items:
            project.set_item_type(project.work_items[0].id, ItemType.PERFORMANCE)

        result = run_pipeline(project, output_dir=self.tmp)

        self.assertTrue(os.path.exists(result.transformed_path))
        self.assertTrue(os.path.exists(result.customized_path))
        self.assertIsNotNone(result.assessment_path)
        self.assertTrue(os.path.exists(result.assessment_path))

    def test_run_pipeline_output_positions_in_range(self):
        project = Project.from_funscript(FIXTURE)
        result = run_pipeline(project, output_dir=self.tmp)

        with open(result.customized_path) as f:
            data = json.load(f)
        for a in data["actions"]:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_run_pipeline_log_not_empty(self):
        project = Project.from_funscript(FIXTURE)
        result = run_pipeline(project, output_dir=self.tmp)
        self.assertGreater(len(result.log), 0)

    def test_run_pipeline_no_assessment_raises(self):
        project = Project(funscript_path=FIXTURE)  # no assessment
        with self.assertRaises(RuntimeError):
            run_pipeline(project, output_dir=self.tmp)

    def test_run_pipeline_per_item_config_carried_through(self):
        """Performance window config overrides reach the customizer JSON."""
        project = Project.from_funscript(FIXTURE)
        if not project.work_items:
            self.skipTest("No work items — fixture too short")

        item = project.work_items[0]
        project.set_item_type(item.id, ItemType.PERFORMANCE)
        project.update_item_config(item.id, "max_velocity", 0.10)

        result = run_pipeline(project, output_dir=self.tmp)

        # The exported performance window file must carry the config override.
        perf_path = result.window_paths.get("performance")
        self.assertIsNotNone(perf_path)
        with open(perf_path) as f:
            windows = json.load(f)
        self.assertEqual(len(windows), 1)
        self.assertIn("config", windows[0])
        self.assertAlmostEqual(windows[0]["config"]["max_velocity"], 0.10)


class TestRunPipelineInMemory(unittest.TestCase):
    """Tests for run_pipeline_in_memory — in-memory transformer + customizer chain."""

    def _assess(self):
        analyzer = FunscriptAnalyzer()
        analyzer.load(FIXTURE)
        return analyzer.analyze()

    def test_returns_actions_list(self):
        assessment = self._assess()
        actions, log = run_pipeline_in_memory(FIXTURE, assessment)
        self.assertIsInstance(actions, list)
        self.assertGreater(len(actions), 0)

    def test_returns_log_dict(self):
        assessment = self._assess()
        _, log = run_pipeline_in_memory(FIXTURE, assessment)
        self.assertIsInstance(log, dict)
        self.assertIn("transformer", log)
        self.assertIn("customizer_applied", log)
        self.assertIn("windows", log)

    def test_actions_have_required_keys(self):
        assessment = self._assess()
        actions, _ = run_pipeline_in_memory(FIXTURE, assessment)
        for a in actions:
            self.assertIn("at", a)
            self.assertIn("pos", a)

    def test_output_positions_in_range(self):
        assessment = self._assess()
        actions, _ = run_pipeline_in_memory(FIXTURE, assessment)
        for a in actions:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_timestamps_sorted(self):
        assessment = self._assess()
        actions, _ = run_pipeline_in_memory(FIXTURE, assessment)
        timestamps = [a["at"] for a in actions]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_no_duplicate_timestamps(self):
        assessment = self._assess()
        actions, _ = run_pipeline_in_memory(FIXTURE, assessment)
        timestamps = [a["at"] for a in actions]
        self.assertEqual(len(timestamps), len(set(timestamps)))

    def test_custom_transformer_config(self):
        assessment = self._assess()
        tcfg = TransformerConfig(bpm_threshold=200.0, amplitude_scale=1.5)
        actions, log = run_pipeline_in_memory(FIXTURE, assessment, transformer_config=tcfg)
        self.assertGreater(len(actions), 0)
        self.assertEqual(log["transformer"]["bpm_threshold"], 200.0)
        self.assertEqual(log["transformer"]["amplitude_scale"], 1.5)

    def test_customizer_not_applied_without_windows(self):
        assessment = self._assess()
        _, log = run_pipeline_in_memory(FIXTURE, assessment)
        self.assertFalse(log["customizer_applied"])
        self.assertEqual(log["windows"]["performance"], 0)
        self.assertEqual(log["windows"]["break"], 0)
        self.assertEqual(log["windows"]["raw"], 0)

    def test_customizer_applied_with_explicit_config(self):
        assessment = self._assess()
        ccfg = CustomizerConfig()
        _, log = run_pipeline_in_memory(FIXTURE, assessment, customizer_config=ccfg)
        self.assertTrue(log["customizer_applied"])

    def test_performance_windows_counted_in_log(self):
        assessment = self._assess()
        # Build a minimal valid window entry using the first phrase
        from utils import ms_to_timestamp
        ph = assessment.phrases[0]
        windows = [{"start": ms_to_timestamp(ph.start_ms), "end": ms_to_timestamp(ph.end_ms)}]
        actions, log = run_pipeline_in_memory(
            FIXTURE, assessment, performance_windows=windows
        )
        self.assertTrue(log["customizer_applied"])
        self.assertEqual(log["windows"]["performance"], 1)
        self.assertGreater(len(actions), 0)

    def test_via_project_windows(self):
        """run_pipeline_in_memory works with windows from project.performance_windows()."""
        project = Project.from_funscript(FIXTURE)
        if project.work_items:
            project.set_item_type(project.work_items[0].id, ItemType.PERFORMANCE)

        assessment = project.assessment
        actions, log = run_pipeline_in_memory(
            FIXTURE,
            assessment,
            performance_windows=project.performance_windows(),
            break_windows=project.break_windows(),
            raw_windows=project.raw_windows(),
        )
        self.assertGreater(len(actions), 0)
        for a in actions:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)


if __name__ == "__main__":
    unittest.main()
