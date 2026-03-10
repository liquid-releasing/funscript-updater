# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for the split-segment logic in ui/streamlit/panels/pattern_editor.py.

These tests cover the pure split-management helpers.  Streamlit is mocked so
no running app is required.

Classes
-------
TestSegmentHelpers      — _get_segments, _get_active_seg (no session state writes)
TestTransformState      — _get_seg_transform, _set_seg_transform (session state I/O)
TestAddSplitPoint       — _add_split_point (validation + renumbering)
TestRemoveSplitBoundary — _remove_split_boundary (merging + renumbering)
TestCopyInstanceToAll   — _copy_instance_to_all (proportional split copy)
TestBuildAllTransforms  — _build_all_transforms (multi-segment transform application)
"""

import copy
import os
import sys
import unittest

# ---------------------------------------------------------------------------
# Mock streamlit BEFORE importing the module under test
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock

_SS: dict = {}          # shared session-state dict (reset in setUp)

_st_mock = MagicMock()
_st_mock.fragment = lambda f: f          # @st.fragment → passthrough decorator

# Make session_state proxy through _SS so tests can reset it cleanly
class _SSProxy:
    def get(self, key, default=None):
        return _SS.get(key, default)
    def __getitem__(self, key):
        return _SS[key]
    def __setitem__(self, key, value):
        _SS[key] = value
    def __contains__(self, key):
        return key in _SS
    def __delitem__(self, key):
        del _SS[key]

_st_mock.session_state = _SSProxy()
sys.modules.setdefault("streamlit", _st_mock)

# Project root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui.streamlit.panels.pattern_editor import (   # noqa: E402
    _get_splits,
    _get_segments,
    _get_active_seg,
    _get_seg_transform,
    _set_seg_transform,
    _add_split_point,
    _remove_split_boundary,
    _copy_instance_to_all,
    _build_all_transforms,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cycle(start=0, end=60_000):
    return {"start_ms": start, "end_ms": end}


def _actions(start_ms, end_ms, step_ms=1_000, pos=50):
    """Uniform actions across a window."""
    return [{"at": t, "pos": pos} for t in range(start_ms, end_ms + 1, step_ms)]


def _alternating_actions(start_ms, end_ms, step_ms=1_000):
    """Actions alternating between 0 and 100."""
    result = []
    for i, t in enumerate(range(start_ms, end_ms + 1, step_ms)):
        result.append({"at": t, "pos": 0 if i % 2 == 0 else 100})
    return result


# ---------------------------------------------------------------------------
# TestSegmentHelpers
# ---------------------------------------------------------------------------

class TestSegmentHelpers(unittest.TestCase):

    def setUp(self):
        _SS.clear()

    # _get_segments ---------------------------------------------------------

    def test_no_splits_returns_full_range(self):
        cy  = _cycle(0, 60_000)
        seg = _get_segments("stingy", 0, cy)
        self.assertEqual(seg, [(0, 60_000)])

    def test_one_split_returns_two_segments(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [30_000]
        seg = _get_segments("stingy", 0, cy)
        self.assertEqual(seg, [(0, 30_000), (30_000, 60_000)])

    def test_two_splits_returns_three_segments(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [20_000, 40_000]
        seg = _get_segments("stingy", 0, cy)
        self.assertEqual(seg, [(0, 20_000), (20_000, 40_000), (40_000, 60_000)])

    def test_splits_sorted_regardless_of_insertion_order(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [40_000, 20_000]   # unsorted
        seg = _get_segments("stingy", 0, cy)
        self.assertEqual(seg[0], (0, 20_000))
        self.assertEqual(seg[1], (20_000, 40_000))

    def test_segments_are_contiguous(self):
        cy = _cycle(0, 90_000)
        _SS["pe_splits_stingy_0"] = [30_000, 60_000]
        segs = _get_segments("stingy", 0, cy)
        for j in range(len(segs) - 1):
            self.assertEqual(segs[j][1], segs[j + 1][0])

    # _get_active_seg -------------------------------------------------------

    def test_default_active_seg_is_zero(self):
        self.assertEqual(_get_active_seg("stingy", 0, 3), 0)

    def test_stored_active_seg_returned(self):
        _SS["pe_active_seg_stingy_0"] = 2
        self.assertEqual(_get_active_seg("stingy", 0, 3), 2)

    def test_active_seg_clamped_to_n_segs_minus_one(self):
        _SS["pe_active_seg_stingy_0"] = 99
        self.assertEqual(_get_active_seg("stingy", 0, 3), 2)

    def test_active_seg_clamped_when_n_segs_is_one(self):
        _SS["pe_active_seg_stingy_0"] = 5
        self.assertEqual(_get_active_seg("stingy", 0, 1), 0)


# ---------------------------------------------------------------------------
# TestTransformState
# ---------------------------------------------------------------------------

class TestTransformState(unittest.TestCase):

    def setUp(self):
        _SS.clear()

    def test_get_empty_returns_empty_dict(self):
        self.assertEqual(_get_seg_transform("stingy", 0, 0), {})

    def test_get_falls_back_to_legacy_key_for_seg0(self):
        _SS["pe_transform_stingy_0"] = {"transform_key": "invert", "param_values": {}}
        result = _get_seg_transform("stingy", 0, 0)
        self.assertEqual(result["transform_key"], "invert")

    def test_get_new_key_takes_precedence_over_legacy(self):
        _SS["pe_transform_stingy_0"]         = {"transform_key": "invert", "param_values": {}}
        _SS["pe_split_transform_stingy_0_0"] = {"transform_key": "smooth", "param_values": {}}
        result = _get_seg_transform("stingy", 0, 0)
        self.assertEqual(result["transform_key"], "smooth")

    def test_get_seg1_returns_empty_without_legacy_fallback(self):
        _SS["pe_transform_stingy_0"] = {"transform_key": "invert", "param_values": {}}
        # seg 1 should NOT fall back to legacy key
        self.assertEqual(_get_seg_transform("stingy", 0, 1), {})

    def test_set_writes_new_key(self):
        _set_seg_transform("stingy", 0, 1, {"transform_key": "smooth"})
        self.assertEqual(_SS["pe_split_transform_stingy_0_1"]["transform_key"], "smooth")

    def test_set_seg0_also_writes_legacy_key(self):
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert"})
        self.assertEqual(_SS["pe_transform_stingy_0"]["transform_key"], "invert")

    def test_set_seg1_does_not_touch_legacy_key(self):
        _SS["pe_transform_stingy_0"] = {"transform_key": "original"}
        _set_seg_transform("stingy", 0, 1, {"transform_key": "smooth"})
        self.assertEqual(_SS["pe_transform_stingy_0"]["transform_key"], "original")


# ---------------------------------------------------------------------------
# TestAddSplitPoint
# ---------------------------------------------------------------------------

class TestAddSplitPoint(unittest.TestCase):

    def setUp(self):
        _SS.clear()

    def test_adds_split_to_unsplit_cycle(self):
        cy = _cycle(0, 60_000)
        ok = _add_split_point("stingy", 0, cy, 30_000)
        self.assertTrue(ok)
        self.assertEqual(_get_splits("stingy", 0), [30_000])

    def test_split_at_start_rejected(self):
        cy = _cycle(0, 60_000)
        self.assertFalse(_add_split_point("stingy", 0, cy, 0))

    def test_split_at_end_rejected(self):
        cy = _cycle(0, 60_000)
        self.assertFalse(_add_split_point("stingy", 0, cy, 60_000))

    def test_split_before_start_rejected(self):
        cy = _cycle(10_000, 60_000)
        self.assertFalse(_add_split_point("stingy", 0, cy, 5_000))

    def test_split_after_end_rejected(self):
        cy = _cycle(0, 60_000)
        self.assertFalse(_add_split_point("stingy", 0, cy, 70_000))

    def test_duplicate_split_rejected(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [30_000]
        self.assertFalse(_add_split_point("stingy", 0, cy, 30_000))

    def test_creates_two_segments(self):
        cy = _cycle(0, 60_000)
        _add_split_point("stingy", 0, cy, 30_000)
        segs = _get_segments("stingy", 0, cy)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0], (0, 30_000))
        self.assertEqual(segs[1], (30_000, 60_000))

    def test_right_half_inherits_left_transform(self):
        cy = _cycle(0, 60_000)
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert", "param_values": {}})
        _add_split_point("stingy", 0, cy, 30_000)
        left  = _get_seg_transform("stingy", 0, 0)
        right = _get_seg_transform("stingy", 0, 1)
        self.assertEqual(left["transform_key"],  "invert")
        self.assertEqual(right["transform_key"], "invert")

    def test_subsequent_transforms_renumbered(self):
        """Split inside seg 0 of a 2-segment cycle; seg 1 should shift to seg 2."""
        cy = _cycle(0, 90_000)
        _SS["pe_splits_stingy_0"] = [60_000]
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert"})
        _set_seg_transform("stingy", 0, 1, {"transform_key": "smooth"})
        # Now split seg 0 at 30_000 → segments: [0,30k] [30k,60k] [60k,90k]
        _add_split_point("stingy", 0, cy, 30_000)
        segs = _get_segments("stingy", 0, cy)
        self.assertEqual(len(segs), 3)
        self.assertEqual(_get_seg_transform("stingy", 0, 0)["transform_key"], "invert")
        self.assertEqual(_get_seg_transform("stingy", 0, 1)["transform_key"], "invert")  # inherited
        self.assertEqual(_get_seg_transform("stingy", 0, 2)["transform_key"], "smooth")  # shifted

    def test_multiple_splits_accumulate(self):
        cy = _cycle(0, 90_000)
        _add_split_point("stingy", 0, cy, 30_000)
        _add_split_point("stingy", 0, cy, 60_000)
        self.assertEqual(_get_splits("stingy", 0), [30_000, 60_000])
        self.assertEqual(len(_get_segments("stingy", 0, cy)), 3)


# ---------------------------------------------------------------------------
# TestRemoveSplitBoundary
# ---------------------------------------------------------------------------

class TestRemoveSplitBoundary(unittest.TestCase):

    def setUp(self):
        _SS.clear()

    def test_remove_only_split_restores_single_segment(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [30_000]
        ok = _remove_split_boundary("stingy", 0, cy, 0)
        self.assertTrue(ok)
        self.assertEqual(_get_splits("stingy", 0), [])
        self.assertEqual(_get_segments("stingy", 0, cy), [(0, 60_000)])

    def test_remove_first_boundary_of_three(self):
        cy = _cycle(0, 90_000)
        _SS["pe_splits_stingy_0"] = [30_000, 60_000]
        _remove_split_boundary("stingy", 0, cy, 0)   # remove 30_000
        segs = _get_segments("stingy", 0, cy)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0], (0, 60_000))
        self.assertEqual(segs[1], (60_000, 90_000))

    def test_remove_last_boundary_of_three(self):
        cy = _cycle(0, 90_000)
        _SS["pe_splits_stingy_0"] = [30_000, 60_000]
        _remove_split_boundary("stingy", 0, cy, 1)   # remove 60_000
        segs = _get_segments("stingy", 0, cy)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0], (0, 30_000))
        self.assertEqual(segs[1], (30_000, 90_000))

    def test_merged_segment_keeps_left_transform(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [30_000]
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert"})
        _set_seg_transform("stingy", 0, 1, {"transform_key": "smooth"})
        _remove_split_boundary("stingy", 0, cy, 0)
        merged = _get_seg_transform("stingy", 0, 0)
        self.assertEqual(merged["transform_key"], "invert")

    def test_subsequent_transforms_renumbered_down(self):
        """Remove middle boundary; seg 2 (originally smooth) should become seg 1."""
        cy = _cycle(0, 90_000)
        _SS["pe_splits_stingy_0"] = [30_000, 60_000]
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert"})
        _set_seg_transform("stingy", 0, 1, {"transform_key": "smooth"})
        _set_seg_transform("stingy", 0, 2, {"transform_key": "normalize"})
        _remove_split_boundary("stingy", 0, cy, 0)   # merge seg 0+1
        self.assertEqual(_get_seg_transform("stingy", 0, 0)["transform_key"], "invert")
        self.assertEqual(_get_seg_transform("stingy", 0, 1)["transform_key"], "normalize")

    def test_no_splits_returns_false(self):
        cy = _cycle(0, 60_000)
        self.assertFalse(_remove_split_boundary("stingy", 0, cy, 0))

    def test_invalid_split_idx_returns_false(self):
        cy = _cycle(0, 60_000)
        _SS["pe_splits_stingy_0"] = [30_000]
        self.assertFalse(_remove_split_boundary("stingy", 0, cy, 5))


# ---------------------------------------------------------------------------
# TestCopyInstanceToAll
# ---------------------------------------------------------------------------

class TestCopyInstanceToAll(unittest.TestCase):

    def setUp(self):
        _SS.clear()

    def _set_up_source(self, label, from_i, from_cycle, splits, transforms):
        """Helper: write splits + per-segment transforms for instance from_i."""
        _SS[f"pe_splits_{label}_{from_i}"] = splits
        for seg_idx, tx in enumerate(transforms):
            _set_seg_transform(label, from_i, seg_idx, tx)

    def test_no_splits_copies_transform_only(self):
        from_cy = _cycle(0, 60_000)
        dest_cy = _cycle(60_000, 120_000)
        self._set_up_source("drone", 0, from_cy, [], [{"transform_key": "invert"}])
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        dest_splits = _get_splits("drone", 1)
        self.assertEqual(dest_splits, [])
        self.assertEqual(_get_seg_transform("drone", 1, 0)["transform_key"], "invert")

    def test_splits_copied_proportionally(self):
        # Source: [0, 60_000] with split at 20_000 (1/3 through)
        from_cy = _cycle(0, 60_000)
        dest_cy = _cycle(0, 90_000)     # 1.5× longer
        self._set_up_source(
            "drone", 0, from_cy,
            splits=[20_000],
            transforms=[{"transform_key": "invert"}, {"transform_key": "smooth"}],
        )
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        dest_splits = _get_splits("drone", 1)
        # 1/3 of 90_000 = 30_000
        self.assertEqual(dest_splits, [30_000])

    def test_transforms_copied_to_all_segments(self):
        from_cy = _cycle(0, 60_000)
        dest_cy = _cycle(60_000, 120_000)
        self._set_up_source(
            "drone", 0, from_cy,
            splits=[30_000],
            transforms=[{"transform_key": "invert"}, {"transform_key": "smooth"}],
        )
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        self.assertEqual(_get_seg_transform("drone", 1, 0)["transform_key"], "invert")
        self.assertEqual(_get_seg_transform("drone", 1, 1)["transform_key"], "smooth")

    def test_source_instance_not_modified(self):
        from_cy = _cycle(0, 60_000)
        dest_cy = _cycle(60_000, 120_000)
        _SS["pe_splits_drone_0"] = [30_000]
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        self.assertEqual(_get_splits("drone", 0), [30_000])

    def test_dest_splits_cleared_when_source_has_none(self):
        from_cy = _cycle(0, 60_000)
        dest_cy = _cycle(60_000, 120_000)
        _SS["pe_splits_drone_1"] = [90_000]   # dest already has a split
        self._set_up_source("drone", 0, from_cy, [], [{"transform_key": "invert"}])
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        self.assertEqual(_get_splits("drone", 1), [])

    def test_split_points_clamped_to_dest_bounds(self):
        # Source split very close to end; proportional dest split might exceed bounds
        from_cy = _cycle(0, 100_000)
        dest_cy = _cycle(200_000, 201_000)  # only 1s long
        _SS["pe_splits_drone_0"] = [99_900]   # 99.9% through
        _set_seg_transform("drone", 0, 0, {"transform_key": "invert"})
        _set_seg_transform("drone", 0, 1, {"transform_key": "smooth"})
        _copy_instance_to_all("drone", 0, from_cy, [from_cy, dest_cy])
        dest_splits = _get_splits("drone", 1)
        for sp in dest_splits:
            self.assertGreater(sp, dest_cy["start_ms"])
            self.assertLess(sp, dest_cy["end_ms"])


# ---------------------------------------------------------------------------
# TestBuildAllTransforms
# ---------------------------------------------------------------------------

class TestBuildAllTransforms(unittest.TestCase):
    """_build_all_transforms uses the real TRANSFORM_CATALOG (passthrough + invert)."""

    def setUp(self):
        _SS.clear()

    def _make_actions(self):
        """60 actions: 0–59_000 ms at pos 0 (even indices) / 100 (odd indices)."""
        return [{"at": t * 1_000, "pos": 0 if t % 2 == 0 else 100}
                for t in range(60)]

    def test_no_transforms_returns_unchanged(self):
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        result  = _build_all_transforms(cycles, "stingy", actions)
        self.assertEqual(len(result), len(actions))
        for orig, res in zip(actions, result):
            self.assertEqual(orig["pos"], res["pos"])

    def test_apply_false_skips_instance(self):
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert", "param_values": {}})
        _SS["pe_apply_stingy_0"] = False
        result  = _build_all_transforms(cycles, "stingy", actions)
        # invert should not have fired — positions unchanged
        for orig, res in zip(actions, result):
            self.assertEqual(orig["pos"], res["pos"])

    def test_single_segment_invert_applied(self):
        """invert flips positions around 50: 0→100, 100→0."""
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert", "param_values": {}})
        result  = _build_all_transforms(cycles, "stingy", actions)
        for orig, res in zip(actions, result):
            if orig["at"] <= 59_000:
                self.assertEqual(res["pos"], 100 - orig["pos"])

    def test_passthrough_transform_leaves_positions_unchanged(self):
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        _set_seg_transform("stingy", 0, 0, {"transform_key": "passthrough", "param_values": {}})
        result  = _build_all_transforms(cycles, "stingy", actions)
        for orig, res in zip(actions, result):
            self.assertEqual(orig["pos"], res["pos"])

    def test_two_segments_independent_transforms(self):
        """Seg 0: invert; Seg 1: passthrough.  Only actions in seg 0 should flip."""
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        # Split at 30_000 → seg 0: [0,30k], seg 1: [30k,59k]
        _SS["pe_splits_stingy_0"] = [30_000]
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert",       "param_values": {}})
        _set_seg_transform("stingy", 0, 1, {"transform_key": "passthrough",  "param_values": {}})
        result  = _build_all_transforms(cycles, "stingy", actions)
        for orig, res in zip(actions, result):
            if orig["at"] <= 30_000:
                # invert territory
                self.assertEqual(res["pos"], 100 - orig["pos"])
            else:
                # passthrough territory
                self.assertEqual(res["pos"], orig["pos"])

    def test_multiple_instances_each_transformed(self):
        """Two instances, each with its own invert → both should be flipped."""
        cycles = [_cycle(0, 29_000), _cycle(30_000, 59_000)]
        actions = self._make_actions()
        for i in range(2):
            _set_seg_transform("stingy", i, 0, {"transform_key": "invert", "param_values": {}})
        result = _build_all_transforms(cycles, "stingy", actions)
        for orig, res in zip(actions, result):
            self.assertEqual(res["pos"], 100 - orig["pos"])

    def test_actions_outside_all_cycles_unchanged(self):
        """Actions before cycle 0 and after cycle 0 end should not be touched."""
        cy = _cycle(10_000, 30_000)
        actions = [
            {"at":  5_000, "pos": 25},
            {"at": 15_000, "pos": 25},
            {"at": 35_000, "pos": 25},
        ]
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert", "param_values": {}})
        result = _build_all_transforms([cy], "stingy", actions)
        at_map = {a["at"]: a["pos"] for a in result}
        self.assertEqual(at_map[5_000],  25)   # before cycle — unchanged
        self.assertEqual(at_map[35_000], 25)   # after cycle — unchanged
        self.assertEqual(at_map[15_000], 75)   # inside cycle — inverted (100-25=75)

    def test_result_length_matches_original(self):
        """Non-structural transforms must not change action count."""
        cycles  = [_cycle(0, 59_000)]
        actions = self._make_actions()
        _set_seg_transform("stingy", 0, 0, {"transform_key": "invert", "param_values": {}})
        result  = _build_all_transforms(cycles, "stingy", actions)
        self.assertEqual(len(result), len(actions))


if __name__ == "__main__":
    unittest.main()
