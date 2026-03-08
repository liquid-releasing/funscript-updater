"""Tests for ui/common/view_state.py"""

import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from ui.common.view_state import ViewState


class TestViewStateDefaults(unittest.TestCase):
    def test_no_zoom_by_default(self):
        vs = ViewState()
        self.assertFalse(vs.has_zoom())

    def test_no_selection_by_default(self):
        vs = ViewState()
        self.assertFalse(vs.has_selection())

    def test_default_color_mode(self):
        vs = ViewState()
        self.assertEqual(vs.color_mode, "velocity")

    def test_default_annotations(self):
        vs = ViewState()
        self.assertTrue(vs.show_cycles)
        self.assertTrue(vs.show_phrases)
        self.assertTrue(vs.show_transitions)
        self.assertFalse(vs.show_phases)
        self.assertFalse(vs.show_patterns)


class TestViewStateZoom(unittest.TestCase):
    def test_set_zoom(self):
        vs = ViewState()
        vs.set_zoom(1000, 5000)
        self.assertTrue(vs.has_zoom())
        self.assertEqual(vs.zoom_start_ms, 1000)
        self.assertEqual(vs.zoom_end_ms,   5000)

    def test_set_zoom_invalid_ignored(self):
        vs = ViewState()
        vs.set_zoom(5000, 1000)   # start >= end
        self.assertFalse(vs.has_zoom())

    def test_reset_zoom(self):
        vs = ViewState()
        vs.set_zoom(1000, 5000)
        vs.reset_zoom()
        self.assertFalse(vs.has_zoom())


class TestViewStateSelection(unittest.TestCase):
    def test_set_selection(self):
        vs = ViewState()
        vs.set_selection(2000, 4000)
        self.assertTrue(vs.has_selection())
        self.assertEqual(vs.selection_start_ms, 2000)
        self.assertEqual(vs.selection_end_ms,   4000)

    def test_set_selection_expands_zoom(self):
        vs = ViewState()
        vs.set_selection(2000, 4000)
        self.assertIsNotNone(vs.zoom_start_ms)
        self.assertLessEqual(vs.zoom_start_ms, 2000)
        self.assertGreaterEqual(vs.zoom_end_ms, 4000)

    def test_set_selection_invalid_ignored(self):
        vs = ViewState()
        vs.set_selection(4000, 2000)
        self.assertFalse(vs.has_selection())

    def test_clear_selection(self):
        vs = ViewState()
        vs.set_selection(2000, 4000)
        vs.clear_selection()
        self.assertFalse(vs.has_selection())


class TestViewStateEnabledKinds(unittest.TestCase):
    def test_default_enabled_kinds(self):
        vs = ViewState()
        kinds = vs.enabled_kinds()
        self.assertIn("cycle",      kinds)
        self.assertIn("phrase",     kinds)
        self.assertIn("transition", kinds)
        self.assertNotIn("phase",   kinds)
        self.assertNotIn("pattern", kinds)

    def test_toggle_all_on(self):
        vs = ViewState()
        vs.show_phases = vs.show_patterns = True
        kinds = vs.enabled_kinds()
        self.assertEqual(set(kinds), {"phase", "cycle", "pattern", "phrase", "transition"})


class TestViewStateSerialisation(unittest.TestCase):
    def test_round_trip(self):
        vs = ViewState()
        vs.set_zoom(1000, 8000)
        vs.set_selection(2000, 4000)
        vs.color_mode = "amplitude"
        d = vs.to_dict()
        vs2 = ViewState.from_dict(d)
        self.assertEqual(vs2.zoom_start_ms,      vs.zoom_start_ms)
        self.assertEqual(vs2.zoom_end_ms,        vs.zoom_end_ms)
        self.assertEqual(vs2.selection_start_ms, vs.selection_start_ms)
        self.assertEqual(vs2.color_mode,         "amplitude")

    def test_from_dict_ignores_unknown_keys(self):
        d = {"zoom_start_ms": 500, "zoom_end_ms": 1000, "unknown_key": True}
        vs = ViewState.from_dict(d)
        self.assertEqual(vs.zoom_start_ms, 500)


if __name__ == "__main__":
    unittest.main()
