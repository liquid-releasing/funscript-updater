# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for ui/common/project.py."""

import json
import os
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.common.project import Project
from ui.common.work_items import ItemType, WorkItem

# Path to a small fixture funscript (used by core tests already).
_FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "sample.funscript")


class TestProjectFromFunscript(unittest.TestCase):
    def setUp(self):
        self.project = Project.from_funscript(_FIXTURE)

    def test_is_loaded(self):
        self.assertTrue(self.project.is_loaded)

    def test_name(self):
        self.assertEqual(self.project.name, "sample")

    def test_assessment_not_none(self):
        self.assertIsNotNone(self.project.assessment)

    def test_work_items_created(self):
        # At minimum one work item should exist.
        self.assertGreater(len(self.project.work_items), 0)

    def test_all_items_neutral_initially(self):
        for item in self.project.work_items:
            self.assertEqual(item.item_type, ItemType.NEUTRAL)

    def test_summary_keys(self):
        summary = self.project.summary()
        for key in ("name", "duration", "bpm", "actions", "phases", "cycles", "patterns", "phrases"):
            self.assertIn(key, summary)


class TestProjectItemManagement(unittest.TestCase):
    def setUp(self):
        self.project = Project.from_funscript(_FIXTURE)
        # Pick the first item.
        self.item_id = self.project.work_items[0].id

    def test_set_item_type(self):
        self.project.set_item_type(self.item_id, ItemType.PERFORMANCE)
        item = self.project.get_item(self.item_id)
        self.assertEqual(item.item_type, ItemType.PERFORMANCE)

    def test_update_item_config(self):
        self.project.set_item_type(self.item_id, ItemType.PERFORMANCE)
        self.project.update_item_config(self.item_id, "max_velocity", 0.5)
        item = self.project.get_item(self.item_id)
        self.assertAlmostEqual(item.config["max_velocity"], 0.5)

    def test_update_item_times(self):
        self.project.update_item_times(self.item_id, 1000, 5000)
        item = self.project.get_item(self.item_id)
        self.assertEqual(item.start_ms, 1000)
        self.assertEqual(item.end_ms, 5000)

    def test_remove_item(self):
        count_before = len(self.project.work_items)
        self.project.remove_item(self.item_id)
        self.assertEqual(len(self.project.work_items), count_before - 1)
        self.assertIsNone(self.project.get_item(self.item_id))

    def test_add_item_sorted_by_start(self):
        # Insert an item whose start falls between two known positions.
        early = WorkItem(start_ms=100_000, end_ms=110_000, item_type=ItemType.BREAK)
        late = WorkItem(start_ms=200_000, end_ms=210_000, item_type=ItemType.BREAK)
        mid = WorkItem(start_ms=150_000, end_ms=160_000, item_type=ItemType.PERFORMANCE)
        self.project.add_item(early)
        self.project.add_item(late)
        self.project.add_item(mid)
        starts = [w.start_ms for w in self.project.work_items]
        self.assertEqual(starts, sorted(starts))


class TestProjectWindowExport(unittest.TestCase):
    def setUp(self):
        self.project = Project.from_funscript(_FIXTURE)
        # Manually add typed items so tests don't depend on fixture shape.
        self.project.add_item(WorkItem(start_ms=0, end_ms=2000, item_type=ItemType.PERFORMANCE))
        self.project.add_item(WorkItem(start_ms=2000, end_ms=4000, item_type=ItemType.BREAK))

    def test_performance_windows_populated(self):
        self.assertGreater(len(self.project.performance_windows()), 0)

    def test_break_windows_populated(self):
        self.assertGreater(len(self.project.break_windows()), 0)

    def test_raw_windows_empty(self):
        self.assertEqual(len(self.project.raw_windows()), 0)

    def test_export_writes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = self.project.export_windows(tmp)
            self.assertIn("performance", written)
            self.assertIn("break", written)
            self.assertNotIn("raw", written)
            for path in written.values():
                self.assertTrue(os.path.exists(path))

    def test_export_json_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = self.project.export_windows(tmp)
            for path in written.values():
                with open(path) as f:
                    data = json.load(f)
                self.assertIsInstance(data, list)
                self.assertTrue(all("start" in w and "end" in w for w in data))


class TestProjectPersistence(unittest.TestCase):
    def setUp(self):
        self.project = Project.from_funscript(_FIXTURE)
        if self.project.work_items:
            self.project.set_item_type(self.project.work_items[0].id, ItemType.RAW)

    def test_save_and_reload(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            self.project.export_project(path)
            restored = Project.load_project(path)
            self.assertEqual(restored.funscript_path, self.project.funscript_path)
            self.assertEqual(len(restored.work_items), len(self.project.work_items))
            if restored.work_items:
                self.assertEqual(restored.work_items[0].item_type, ItemType.RAW)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
