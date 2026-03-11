# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Unit tests for ui.common.undo_stack."""

import unittest

from ui.common.undo_stack import Snapshot, UndoStack


def _snap(label: str, project=None, pe_state=None) -> Snapshot:
    return Snapshot(label=label, project=project, pe_state=pe_state or {})


class TestUndoStackBasic(unittest.TestCase):

    def test_empty_stack_cannot_undo_or_redo(self):
        s = UndoStack()
        self.assertFalse(s.can_undo)
        self.assertFalse(s.can_redo)

    def test_single_push_cannot_undo(self):
        s = UndoStack()
        s.push(_snap("A"))
        self.assertFalse(s.can_undo)
        self.assertFalse(s.can_redo)

    def test_two_pushes_can_undo(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        self.assertTrue(s.can_undo)
        self.assertFalse(s.can_redo)

    def test_undo_returns_previous_snapshot(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        snap = s.undo()
        self.assertEqual(snap.label, "A")

    def test_undo_then_redo(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        s.undo()
        self.assertTrue(s.can_redo)
        snap = s.redo()
        self.assertEqual(snap.label, "B")

    def test_undo_on_empty_returns_none(self):
        s = UndoStack()
        self.assertIsNone(s.undo())

    def test_redo_on_empty_returns_none(self):
        s = UndoStack()
        self.assertIsNone(s.redo())

    def test_redo_after_no_undo_returns_none(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        self.assertIsNone(s.redo())


class TestUndoStackLabels(unittest.TestCase):

    def test_undo_label_is_current_snapshot(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        self.assertEqual(s.undo_label, "B")

    def test_redo_label_is_next_snapshot(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        s.push(_snap("C"))
        s.undo()
        self.assertEqual(s.redo_label, "C")

    def test_no_undo_label_when_cannot_undo(self):
        s = UndoStack()
        s.push(_snap("A"))
        self.assertIsNone(s.undo_label)

    def test_no_redo_label_when_cannot_redo(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        self.assertIsNone(s.redo_label)


class TestUndoStackRedoBranchDiscard(unittest.TestCase):

    def test_push_after_undo_discards_redo_branch(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        s.push(_snap("C"))
        s.undo()         # back to B
        s.undo()         # back to A
        s.push(_snap("D"))  # discard B and C
        self.assertFalse(s.can_redo)
        snap = s.undo()
        self.assertEqual(snap.label, "A")

    def test_redo_branch_gone_after_new_push(self):
        s = UndoStack()
        s.push(_snap("A"))
        s.push(_snap("B"))
        s.undo()
        s.push(_snap("C"))
        self.assertEqual(s.size, 2)
        self.assertFalse(s.can_redo)


class TestUndoStackMaxSize(unittest.TestCase):

    def test_max_size_respected(self):
        s = UndoStack(max_size=3)
        for label in ("A", "B", "C", "D"):
            s.push(_snap(label))
        self.assertEqual(s.size, 3)

    def test_oldest_snapshot_dropped(self):
        s = UndoStack(max_size=3)
        for label in ("A", "B", "C", "D"):
            s.push(_snap(label))
        # Stack should be [B, C, D]; undo twice to reach B
        s.undo()         # C
        snap = s.undo()  # B
        self.assertEqual(snap.label, "B")
        self.assertFalse(s.can_undo)  # A was dropped

    def test_max_size_one_never_can_undo(self):
        s = UndoStack(max_size=1)
        s.push(_snap("A"))
        s.push(_snap("B"))
        self.assertFalse(s.can_undo)
        self.assertEqual(s.size, 1)


class TestUndoStackStatePayload(unittest.TestCase):

    def test_project_reference_preserved(self):
        s = UndoStack()
        proj = object()
        s.push(_snap("A", project=proj))
        s.push(_snap("B"))
        snap = s.undo()
        self.assertIs(snap.project, proj)

    def test_pe_state_preserved(self):
        s = UndoStack()
        pe = {"pe_splits_frantic_0": [1000, 2000]}
        s.push(Snapshot(label="A", project=None, pe_state=pe))
        s.push(_snap("B"))
        snap = s.undo()
        self.assertEqual(snap.pe_state, {"pe_splits_frantic_0": [1000, 2000]})

    def test_multiple_undos_traverse_stack(self):
        s = UndoStack()
        for i in range(5):
            s.push(_snap(str(i)))
        labels = []
        while s.can_undo:
            labels.append(s.undo().label)
        self.assertEqual(labels, ["3", "2", "1", "0"])


if __name__ == "__main__":
    unittest.main()
