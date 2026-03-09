"""CLI tests — invoke each subcommand via subprocess and verify outputs.

Tests run the real CLI entry point so they cover argument parsing,
dispatch, and file I/O without mocking internals.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample.funscript")
CLI = os.path.join(os.path.dirname(__file__), "..", "cli.py")
PYTHON = sys.executable


def run(*args, cwd=None):
    """Run cli.py with *args and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [PYTHON, CLI, *args],
        capture_output=True,
        text=True,
        cwd=cwd or os.path.dirname(CLI),
    )
    return result.returncode, result.stdout, result.stderr


class TestCliAssess(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_assess_exits_zero(self):
        rc, _, _ = run("assess", FIXTURE, "--output", os.path.join(self.tmp, "a.json"))
        self.assertEqual(rc, 0)

    def test_assess_writes_json(self):
        out = os.path.join(self.tmp, "assessment.json")
        run("assess", FIXTURE, "--output", out)
        self.assertTrue(os.path.exists(out))
        with open(out) as f:
            data = json.load(f)
        self.assertIn("phrases", data)
        self.assertIn("meta", data)

    def test_assess_default_output_path(self):
        import shutil
        fixture_copy = os.path.join(self.tmp, "sample.funscript")
        shutil.copy(FIXTURE, fixture_copy)
        rc, _, _ = run("assess", fixture_copy)
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "sample_assessment.json")))

    def test_assess_prints_summary(self):
        out = os.path.join(self.tmp, "a.json")
        _, stdout, _ = run("assess", FIXTURE, "--output", out)
        self.assertIn("BPM", stdout)
        self.assertIn("Phrases", stdout)

    def test_assess_with_analyzer_config(self):
        cfg_path = os.path.join(self.tmp, "analyzer_config.json")
        run("config", "--analyzer", "--output", cfg_path)
        out = os.path.join(self.tmp, "a.json")
        rc, _, _ = run("assess", FIXTURE, "--output", out, "--config", cfg_path)
        self.assertEqual(rc, 0)


class TestCliTransform(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.assessment = os.path.join(self.tmp, "assessment.json")
        run("assess", FIXTURE, "--output", self.assessment)

    def test_transform_exits_zero(self):
        rc, _, _ = run(
            "transform", FIXTURE,
            "--assessment", self.assessment,
            "--output", os.path.join(self.tmp, "t.funscript"),
        )
        self.assertEqual(rc, 0)

    def test_transform_writes_valid_funscript(self):
        out = os.path.join(self.tmp, "transformed.funscript")
        run("transform", FIXTURE, "--assessment", self.assessment, "--output", out)
        self.assertTrue(os.path.exists(out))
        with open(out) as f:
            data = json.load(f)
        self.assertIn("actions", data)
        for a in data["actions"]:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_transform_with_config(self):
        cfg = os.path.join(self.tmp, "tc.json")
        run("config", "--output", cfg)
        out = os.path.join(self.tmp, "t.funscript")
        rc, _, _ = run(
            "transform", FIXTURE,
            "--assessment", self.assessment,
            "--output", out,
            "--config", cfg,
        )
        self.assertEqual(rc, 0)


class TestCliCustomize(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.assessment = os.path.join(self.tmp, "assessment.json")
        run("assess", FIXTURE, "--output", self.assessment)
        self.transformed = os.path.join(self.tmp, "transformed.funscript")
        run("transform", FIXTURE, "--assessment", self.assessment,
            "--output", self.transformed)

    def test_customize_exits_zero(self):
        out = os.path.join(self.tmp, "customized.funscript")
        rc, _, _ = run(
            "customize", self.transformed,
            "--assessment", self.assessment,
            "--output", out,
        )
        self.assertEqual(rc, 0)

    def test_customize_writes_valid_funscript(self):
        out = os.path.join(self.tmp, "customized.funscript")
        run("customize", self.transformed, "--assessment", self.assessment, "--output", out)
        self.assertTrue(os.path.exists(out))
        with open(out) as f:
            data = json.load(f)
        for a in data["actions"]:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_customize_with_perf_window(self):
        perf = os.path.join(self.tmp, "perf.json")
        with open(perf, "w") as f:
            json.dump([{"start": "00:00:00.000", "end": "00:00:04.000"}], f)
        out = os.path.join(self.tmp, "customized.funscript")
        rc, _, _ = run(
            "customize", self.transformed,
            "--assessment", self.assessment,
            "--output", out,
            "--perf", perf,
        )
        self.assertEqual(rc, 0)

    def test_customize_missing_window_files_ok(self):
        """Customizer treats missing optional window files as empty — should not error."""
        out = os.path.join(self.tmp, "customized.funscript")
        rc, _, stderr = run(
            "customize", self.transformed,
            "--assessment", self.assessment,
            "--output", out,
            "--perf", os.path.join(self.tmp, "nonexistent.json"),
        )
        self.assertEqual(rc, 0)


class TestCliPipeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_pipeline_exits_zero(self):
        rc, _, _ = run("pipeline", FIXTURE, "--output-dir", self.tmp)
        self.assertEqual(rc, 0)

    def test_pipeline_writes_all_three_outputs(self):
        run("pipeline", FIXTURE, "--output-dir", self.tmp)
        base = "sample"
        self.assertTrue(os.path.exists(os.path.join(self.tmp, f"{base}.assessment.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, f"{base}.transformed.funscript")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, f"{base}.customized.funscript")))

    def test_pipeline_output_positions_in_range(self):
        run("pipeline", FIXTURE, "--output-dir", self.tmp)
        customized = os.path.join(self.tmp, "sample.customized.funscript")
        with open(customized) as f:
            data = json.load(f)
        for a in data["actions"]:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_pipeline_with_perf_window(self):
        perf = os.path.join(self.tmp, "perf.json")
        with open(perf, "w") as f:
            json.dump([{"start": "00:00:00.000", "end": "00:00:04.000"}], f)
        rc, _, _ = run("pipeline", FIXTURE, "--output-dir", self.tmp, "--perf", perf)
        self.assertEqual(rc, 0)

    def test_pipeline_prints_stage_summaries(self):
        _, stdout, _ = run("pipeline", FIXTURE, "--output-dir", self.tmp)
        self.assertIn("Assessment saved", stdout)
        self.assertIn("Transformed", stdout)
        self.assertIn("Customized", stdout)


class TestCliConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_config_transformer_default(self):
        out = os.path.join(self.tmp, "tc.json")
        rc, _, _ = run("config", "--output", out)
        self.assertEqual(rc, 0)
        with open(out) as f:
            d = json.load(f)
        self.assertIn("bpm_threshold", d)
        self.assertIn("amplitude_scale", d)

    def test_config_customizer(self):
        out = os.path.join(self.tmp, "cc.json")
        rc, _, _ = run("config", "--customizer", "--output", out)
        self.assertEqual(rc, 0)
        with open(out) as f:
            d = json.load(f)
        self.assertIn("max_velocity", d)
        self.assertIn("break_amplitude_reduce", d)

    def test_config_analyzer(self):
        out = os.path.join(self.tmp, "ac.json")
        rc, _, _ = run("config", "--analyzer", "--output", out)
        self.assertEqual(rc, 0)
        with open(out) as f:
            d = json.load(f)
        self.assertIn("min_velocity", d)
        self.assertIn("bpm_change_threshold_pct", d)

    def test_config_round_trip_transformer(self):
        """Config written by CLI can be loaded back and used in transform."""
        cfg = os.path.join(self.tmp, "tc.json")
        run("config", "--output", cfg)
        assessment = os.path.join(self.tmp, "a.json")
        run("assess", FIXTURE, "--output", assessment)
        out = os.path.join(self.tmp, "t.funscript")
        rc, _, _ = run(
            "transform", FIXTURE,
            "--assessment", assessment,
            "--output", out,
            "--config", cfg,
        )
        self.assertEqual(rc, 0)


class TestCliExportPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.assessment = os.path.join(self.tmp, "assessment.json")
        run("assess", FIXTURE, "--output", self.assessment)

    def test_exits_zero(self):
        rc, _, _ = run("export-plan", FIXTURE, "--assessment", self.assessment)
        self.assertEqual(rc, 0)

    def test_prints_table_header(self):
        _, stdout, _ = run("export-plan", FIXTURE, "--assessment", self.assessment)
        self.assertIn("Transform", stdout)
        self.assertIn("Source", stdout)
        self.assertIn("BPM", stdout)

    def test_no_recommended_shows_zero_transforms(self):
        _, stdout, _ = run(
            "export-plan", FIXTURE, "--assessment", self.assessment, "--no-recommended"
        )
        self.assertIn("0 transform", stdout)

    def test_json_format_is_valid(self):
        rc, stdout, _ = run(
            "export-plan", FIXTURE, "--assessment", self.assessment, "--format", "json"
        )
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("phrase", data[0])
            self.assertIn("transform", data[0])
            self.assertIn("bpm", data[0])

    def test_transforms_file_override(self):
        overrides = os.path.join(self.tmp, "overrides.json")
        with open(overrides, "w") as f:
            json.dump({"1": {"transform": "normalize"}}, f)
        _, stdout, _ = run(
            "export-plan", FIXTURE, "--assessment", self.assessment,
            "--no-recommended", "--transforms", overrides,
        )
        self.assertIn("Normalize", stdout)
        self.assertIn("Manual", stdout)

    def test_apply_writes_funscript(self):
        out = os.path.join(self.tmp, "export.funscript")
        rc, _, _ = run(
            "export-plan", FIXTURE, "--assessment", self.assessment,
            "--apply", "--output", out,
        )
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(out))
        with open(out) as f:
            data = json.load(f)
        self.assertIn("actions", data)
        for a in data["actions"]:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_dry_run_writes_no_file(self):
        out = os.path.join(self.tmp, "should_not_exist.funscript")
        rc, stdout, _ = run(
            "export-plan", FIXTURE, "--assessment", self.assessment,
            "--dry-run", "--output", out,
        )
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(out))
        self.assertIn("dry-run", stdout)


if __name__ == "__main__":
    unittest.main()
