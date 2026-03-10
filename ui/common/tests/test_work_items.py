# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for ui/common/work_items.py."""

import sys
import os
import unittest

# Ensure project root is on the path.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.common.work_items import (
    ItemType,
    WorkItem,
    _BREAK_DEFAULTS,
    _PERF_DEFAULTS,
    items_from_bpm_transitions,
    items_from_phrases,
    items_from_time_windows,
)


class TestItemType(unittest.TestCase):
    def test_values(self):
        self.assertEqual(ItemType.PERFORMANCE.value, "performance")
        self.assertEqual(ItemType.BREAK.value, "break")
        self.assertEqual(ItemType.RAW.value, "raw")
        self.assertEqual(ItemType.NEUTRAL.value, "neutral")

    def test_str_enum(self):
        self.assertEqual(ItemType("performance"), ItemType.PERFORMANCE)


class TestWorkItemDefaults(unittest.TestCase):
    def test_performance_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.PERFORMANCE)
        self.assertEqual(item.config, _PERF_DEFAULTS)

    def test_break_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.BREAK)
        self.assertEqual(item.config, _BREAK_DEFAULTS)

    def test_neutral_empty_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.NEUTRAL)
        self.assertEqual(item.config, {})

    def test_raw_empty_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.RAW)
        self.assertEqual(item.config, {})


class TestWorkItemProperties(unittest.TestCase):
    def setUp(self):
        self.item = WorkItem(start_ms=60_000, end_ms=90_000)

    def test_duration_ms(self):
        self.assertEqual(self.item.duration_ms, 30_000)

    def test_start_ts(self):
        self.assertEqual(self.item.start_ts, "00:01:00.000")

    def test_end_ts(self):
        self.assertEqual(self.item.end_ts, "00:01:30.000")

    def test_duration_ts(self):
        self.assertEqual(self.item.duration_ts, "00:00:30.000")


class TestWorkItemSetType(unittest.TestCase):
    def test_set_type_resets_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.PERFORMANCE)
        item.config["max_velocity"] = 0.99  # override
        item.set_type(ItemType.BREAK)
        self.assertEqual(item.item_type, ItemType.BREAK)
        self.assertEqual(item.config, _BREAK_DEFAULTS)

    def test_set_type_to_neutral_clears_config(self):
        item = WorkItem(start_ms=0, end_ms=1000, item_type=ItemType.PERFORMANCE)
        item.set_type(ItemType.NEUTRAL)
        self.assertEqual(item.config, {})


class TestWorkItemSerialisation(unittest.TestCase):
    def _make(self):
        return WorkItem(
            start_ms=1000,
            end_ms=5000,
            item_type=ItemType.PERFORMANCE,
            label="climax",
            bpm=127.5,
            source="phrase",
        )

    def test_round_trip(self):
        original = self._make()
        restored = WorkItem.from_dict(original.to_dict())
        self.assertEqual(restored.start_ms, original.start_ms)
        self.assertEqual(restored.end_ms, original.end_ms)
        self.assertEqual(restored.item_type, original.item_type)
        self.assertEqual(restored.label, original.label)
        self.assertEqual(restored.bpm, original.bpm)
        self.assertEqual(restored.source, original.source)
        self.assertEqual(restored.config, original.config)

    def test_to_window_dict_has_label(self):
        item = self._make()
        w = item.to_window_dict()
        self.assertEqual(w["start"], "00:00:01.000")
        self.assertEqual(w["end"], "00:00:05.000")
        self.assertEqual(w["label"], "climax")

    def test_to_window_dict_no_label(self):
        item = WorkItem(start_ms=0, end_ms=1000)
        w = item.to_window_dict()
        self.assertNotIn("label", w)


class TestItemsFromPhrases(unittest.TestCase):
    _PHRASES = [
        {"start_ms": 0, "end_ms": 5000, "bpm": 120.0, "pattern_label": "up → down"},
        {"start_ms": 5000, "end_ms": 10000, "bpm": 60.0, "pattern_label": "up → flat → down"},
    ]

    def test_count(self):
        items = items_from_phrases(self._PHRASES)
        self.assertEqual(len(items), 2)

    def test_fields(self):
        items = items_from_phrases(self._PHRASES)
        self.assertEqual(items[0].start_ms, 0)
        self.assertEqual(items[0].end_ms, 5000)
        self.assertAlmostEqual(items[0].bpm, 120.0)
        self.assertEqual(items[0].source, "phrase")
        self.assertEqual(items[0].item_type, ItemType.NEUTRAL)


class TestItemsFromBpmTransitions(unittest.TestCase):
    _PHRASES = [
        {"start_ms": 0, "end_ms": 5000, "bpm": 120.0, "pattern_label": ""},
        {"start_ms": 5000, "end_ms": 10000, "bpm": 60.0, "pattern_label": ""},
        {"start_ms": 10000, "end_ms": 15000, "bpm": 120.0, "pattern_label": ""},
    ]
    _TRANSITIONS = [
        {"at_ms": 5000},
        {"at_ms": 10000},
    ]

    def test_three_regions(self):
        items = items_from_bpm_transitions(self._TRANSITIONS, self._PHRASES)
        self.assertEqual(len(items), 3)

    def test_region_boundaries(self):
        items = items_from_bpm_transitions(self._TRANSITIONS, self._PHRASES)
        self.assertEqual(items[0].start_ms, 0)
        self.assertEqual(items[0].end_ms, 5000)
        self.assertEqual(items[1].start_ms, 5000)
        self.assertEqual(items[1].end_ms, 10000)
        self.assertEqual(items[2].start_ms, 10000)
        self.assertEqual(items[2].end_ms, 15000)

    def test_source_label(self):
        items = items_from_bpm_transitions(self._TRANSITIONS, self._PHRASES)
        for item in items:
            self.assertEqual(item.source, "bpm_transition")

    def test_empty_transitions_returns_empty(self):
        items = items_from_bpm_transitions([], self._PHRASES)
        self.assertEqual(items, [])


class TestItemsFromTimeWindows(unittest.TestCase):
    def test_even_division(self):
        # 30 minutes split into 5-minute windows → 6 items
        items = items_from_time_windows(30 * 60 * 1000, 5 * 60 * 1000)
        self.assertEqual(len(items), 6)
        self.assertEqual(items[0].start_ms, 0)
        self.assertEqual(items[-1].end_ms, 30 * 60 * 1000)

    def test_uneven_division(self):
        # 11 minutes with 5-minute windows → 3 items (0-5, 5-10, 10-11)
        items = items_from_time_windows(11 * 60 * 1000, 5 * 60 * 1000)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[-1].end_ms, 11 * 60 * 1000)

    def test_windows_are_contiguous(self):
        items = items_from_time_windows(20 * 60 * 1000, 5 * 60 * 1000)
        for i in range(1, len(items)):
            self.assertEqual(items[i].start_ms, items[i - 1].end_ms)

    def test_source_label(self):
        items = items_from_time_windows(10 * 60 * 1000, 5 * 60 * 1000)
        for item in items:
            self.assertEqual(item.source, "time_window")

    def test_bpm_attached(self):
        items = items_from_time_windows(10 * 60 * 1000, 5 * 60 * 1000, bpm=120.0)
        for item in items:
            self.assertAlmostEqual(item.bpm, 120.0)

    def test_type_is_neutral(self):
        items = items_from_time_windows(10 * 60 * 1000, 5 * 60 * 1000)
        for item in items:
            self.assertEqual(item.item_type, ItemType.NEUTRAL)

    def test_zero_duration(self):
        items = items_from_time_windows(0, 5 * 60 * 1000)
        self.assertEqual(items, [])


if __name__ == "__main__":
    unittest.main()
