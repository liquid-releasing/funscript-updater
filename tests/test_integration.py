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
from ui.common.pipeline import run_pipeline
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


if __name__ == "__main__":
    unittest.main()
