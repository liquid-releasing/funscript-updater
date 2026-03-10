# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Unit tests for ui.streamlit.undo_helpers.

st.session_state is patched with a plain dict-backed stub so these tests
run without a running Streamlit server.
"""

import sys
import types
import unittest
from copy import deepcopy
from unittest.mock import MagicMock, patch

from ui.common.undo_stack import Snapshot, UndoStack


# ---------------------------------------------------------------------------
# Minimal st.session_state stub
# ---------------------------------------------------------------------------

class _SessionState(dict):
    """dict subclass that also supports attribute-style access."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


def _make_st_stub(session_state: _SessionState):
    """Return a minimal streamlit module stub wired to *session_state*."""
    stub = types.ModuleType("streamlit")
    stub.session_state = session_state
    return stub


# ---------------------------------------------------------------------------
# Base test case — patches streamlit before each test
# ---------------------------------------------------------------------------

class _HelpersTestCase(unittest.TestCase):
    """Base class that patches ``streamlit`` with a fresh stub for each test."""

    def setUp(self):
        self.ss = _SessionState()
        self._st_stub = _make_st_stub(self.ss)

        # Patch streamlit in the helpers module
        self._patcher = patch.dict(sys.modules, {"streamlit": self._st_stub})
        self._patcher.start()

        # Re-import so the module picks up the patched st
        import importlib
        import ui.streamlit.undo_helpers as _mod
        importlib.reload(_mod)
        self._mod = _mod

    def tearDown(self):
        self._patcher.stop()

    # Convenience
    def _push(self, label, project=None, pe_state=None):
        self._mod.push_undo(label)

    def _fresh_stack(self) -> UndoStack:
        stack = UndoStack(max_size=50)
        self.ss["undo_stack"] = stack
        return stack


# ---------------------------------------------------------------------------
# push_undo tests
# ---------------------------------------------------------------------------

class TestPushUndo(_HelpersTestCase):

    def test_silently_skips_when_no_stack(self):
        """push_undo does nothing if undo_stack is not in session state."""
        self.ss["project"] = object()
        # Should not raise
        self._mod.push_undo("anything")

    def test_pushes_snapshot_onto_stack(self):
        stack = self._fresh_stack()
        self.ss["project"] = object()
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        self.assertEqual(stack.size, 2)

    def test_snapshot_label_matches(self):
        stack = self._fresh_stack()
        self._mod.push_undo("Edit phrase actions")
        self._mod.push_undo("Add split at 1:23")
        self.assertEqual(stack.undo_label, "Add split at 1:23")

    def test_project_captured_by_reference(self):
        stack = self._fresh_stack()
        proj = object()
        self.ss["project"] = proj
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        snap = stack.undo()
        self.assertIs(snap.project, proj)

    def test_pe_state_captured(self):
        stack = self._fresh_stack()
        self.ss["pe_splits_frantic_0"] = [1000, 2000]
        self.ss["pe_transform_frantic_0"] = {"transform_key": "boost"}
        self.ss["pe_split_transform_frantic_0_1"] = {"transform_key": "edge"}
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        snap = stack.undo()
        self.assertEqual(snap.pe_state["pe_splits_frantic_0"], [1000, 2000])
        self.assertEqual(snap.pe_state["pe_transform_frantic_0"]["transform_key"], "boost")
        self.assertEqual(snap.pe_state["pe_split_transform_frantic_0_1"]["transform_key"], "edge")

    def test_non_pe_keys_not_captured(self):
        stack = self._fresh_stack()
        self.ss["view_state"] = "some_state"
        self.ss["proposed_actions"] = [1, 2, 3]
        self.ss["pe_splits_x_0"] = [500]
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        snap = stack.undo()
        self.assertNotIn("view_state", snap.pe_state)
        self.assertNotIn("proposed_actions", snap.pe_state)
        self.assertIn("pe_splits_x_0", snap.pe_state)

    def test_pe_state_is_deep_copied(self):
        """Mutating session_state after push should not affect the snapshot."""
        stack = self._fresh_stack()
        self.ss["pe_splits_x_0"] = [1000]
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        # Mutate after push
        self.ss["pe_splits_x_0"].append(2000)
        snap = stack.undo()
        self.assertEqual(snap.pe_state["pe_splits_x_0"], [1000])

    def test_none_project_captured(self):
        stack = self._fresh_stack()
        # No "project" key in session_state
        self._mod.push_undo("A")
        self._mod.push_undo("B")
        snap = stack.undo()
        self.assertIsNone(snap.project)


# ---------------------------------------------------------------------------
# apply_snapshot tests
# ---------------------------------------------------------------------------

class TestApplySnapshot(_HelpersTestCase):

    def _make_snapshot(self, project=None, pe_state=None, label="snap"):
        return Snapshot(label=label, project=project, pe_state=pe_state or {})

    def test_project_restored(self):
        proj = object()
        snap = self._make_snapshot(project=proj)
        self._mod.apply_snapshot(snap)
        self.assertIs(self.ss["project"], proj)

    def test_none_project_restored(self):
        self.ss["project"] = object()
        snap = self._make_snapshot(project=None)
        self._mod.apply_snapshot(snap)
        self.assertIsNone(self.ss["project"])

    def test_pe_keys_restored(self):
        snap = self._make_snapshot(
            pe_state={
                "pe_splits_frantic_0": [500, 1000],
                "pe_transform_frantic_0": {"transform_key": "boost"},
            }
        )
        self._mod.apply_snapshot(snap)
        self.assertEqual(self.ss["pe_splits_frantic_0"], [500, 1000])
        self.assertEqual(self.ss["pe_transform_frantic_0"]["transform_key"], "boost")

    def test_existing_pe_keys_removed(self):
        self.ss["pe_splits_old_0"] = [9999]
        self.ss["pe_transform_old_0"] = {"transform_key": "old"}
        snap = self._make_snapshot(pe_state={"pe_splits_new_0": [1]})
        self._mod.apply_snapshot(snap)
        self.assertNotIn("pe_splits_old_0", self.ss)
        self.assertNotIn("pe_transform_old_0", self.ss)
        self.assertIn("pe_splits_new_0", self.ss)

    def test_non_pe_keys_untouched(self):
        self.ss["view_state"] = "keep_me"
        self.ss["proposed_actions"] = [1, 2]
        snap = self._make_snapshot()
        self._mod.apply_snapshot(snap)
        self.assertEqual(self.ss["view_state"], "keep_me")
        self.assertEqual(self.ss["proposed_actions"], [1, 2])

    def test_restored_pe_state_is_deep_copied(self):
        """Mutating the snapshot after apply should not affect session state."""
        pe = {"pe_splits_x_0": [100]}
        snap = self._make_snapshot(pe_state=pe)
        self._mod.apply_snapshot(snap)
        pe["pe_splits_x_0"].append(200)
        self.assertEqual(self.ss["pe_splits_x_0"], [100])

    def test_empty_pe_state_clears_all_pe_keys(self):
        self.ss["pe_splits_x_0"] = [1]
        self.ss["pe_split_transform_x_0_0"] = {"k": "v"}
        snap = self._make_snapshot(pe_state={})
        self._mod.apply_snapshot(snap)
        self.assertNotIn("pe_splits_x_0", self.ss)
        self.assertNotIn("pe_split_transform_x_0_0", self.ss)


# ---------------------------------------------------------------------------
# Round-trip: push then undo then apply
# ---------------------------------------------------------------------------

class TestPushUndoApplyRoundTrip(_HelpersTestCase):

    def test_full_round_trip(self):
        stack = self._fresh_stack()
        proj_a = object()
        proj_b = object()

        # State A
        self.ss["project"] = proj_a
        self.ss["pe_splits_x_0"] = [1000]
        self._mod.push_undo("State A")

        # State B (simulated mutation)
        self.ss["project"] = proj_b
        self.ss["pe_splits_x_0"] = [2000, 3000]
        self._mod.push_undo("State B")

        # Undo back to A
        snap = stack.undo()
        self._mod.apply_snapshot(snap)

        self.assertIs(self.ss["project"], proj_a)
        self.assertEqual(self.ss["pe_splits_x_0"], [1000])

    def test_undo_then_redo_restores_later_state(self):
        stack = self._fresh_stack()
        proj_a = object()
        proj_b = object()

        self.ss["project"] = proj_a
        self.ss["pe_splits_x_0"] = [1000]
        self._mod.push_undo("A")

        self.ss["project"] = proj_b
        self.ss["pe_splits_x_0"] = [2000]
        self._mod.push_undo("B")

        # Undo to A
        snap = stack.undo()
        self._mod.apply_snapshot(snap)

        # Redo back to B
        snap = stack.redo()
        self._mod.apply_snapshot(snap)

        self.assertIs(self.ss["project"], proj_b)
        self.assertEqual(self.ss["pe_splits_x_0"], [2000])


if __name__ == "__main__":
    unittest.main()
