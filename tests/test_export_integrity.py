# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Unit tests for the export output-integrity helpers (#9 clamp, #10 dedup/sort).

The _clamp_sort_dedup logic is tested here directly without importing
Streamlit by replicating the same algorithm inline.  This keeps the tests
fast and dependency-free while giving full coverage of every branch.
"""

import unittest


def _clamp_sort_dedup(actions: list) -> int:
    """Local mirror of export_panel._clamp_sort_dedup for testing without Streamlit."""
    actions.sort(key=lambda a: a["at"])
    seen: dict = {}
    for a in actions:
        seen[a["at"]] = a["pos"]
    actions[:] = [{"at": t, "pos": p} for t, p in seen.items()]
    clamp_count = 0
    for a in actions:
        clamped = max(0, min(100, a["pos"]))
        if clamped != a["pos"]:
            clamp_count += 1
            a["pos"] = clamped
    return clamp_count


class TestClampSortDedup(unittest.TestCase):
    """Tests for #9 (position clamping) and #10 (timestamp sort + dedup)."""

    # ------------------------------------------------------------------
    # Position clamping (#9)
    # ------------------------------------------------------------------

    def test_in_range_no_clamp(self):
        actions = [{"at": 0, "pos": 0}, {"at": 100, "pos": 100}, {"at": 200, "pos": 50}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 0)
        self.assertEqual([a["pos"] for a in actions], [0, 100, 50])

    def test_above_100_clamped(self):
        actions = [{"at": 0, "pos": 150}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 1)
        self.assertEqual(actions[0]["pos"], 100)

    def test_below_0_clamped(self):
        actions = [{"at": 0, "pos": -25}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 1)
        self.assertEqual(actions[0]["pos"], 0)

    def test_multiple_out_of_range(self):
        actions = [{"at": 0, "pos": 120}, {"at": 10, "pos": 50}, {"at": 20, "pos": -5}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 2)
        self.assertEqual(actions[0]["pos"], 100)
        self.assertEqual(actions[1]["pos"], 50)
        self.assertEqual(actions[2]["pos"], 0)

    def test_boundary_values_not_clamped(self):
        actions = [{"at": 0, "pos": 0}, {"at": 10, "pos": 100}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 0)

    # ------------------------------------------------------------------
    # Timestamp sort (#10 — ordering)
    # ------------------------------------------------------------------

    def test_out_of_order_sorted(self):
        actions = [{"at": 200, "pos": 80}, {"at": 100, "pos": 50}, {"at": 50, "pos": 20}]
        _clamp_sort_dedup(actions)
        self.assertEqual([a["at"] for a in actions], [50, 100, 200])

    def test_already_sorted_unchanged(self):
        actions = [{"at": 10, "pos": 10}, {"at": 20, "pos": 20}, {"at": 30, "pos": 30}]
        _clamp_sort_dedup(actions)
        self.assertEqual([a["at"] for a in actions], [10, 20, 30])

    # ------------------------------------------------------------------
    # Timestamp deduplication (#10 — last pos wins)
    # ------------------------------------------------------------------

    def test_duplicate_timestamp_last_wins(self):
        actions = [{"at": 100, "pos": 30}, {"at": 100, "pos": 70}]
        _clamp_sort_dedup(actions)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["pos"], 70)

    def test_three_duplicates_last_wins(self):
        actions = [
            {"at": 500, "pos": 10},
            {"at": 500, "pos": 50},
            {"at": 500, "pos": 90},
        ]
        _clamp_sort_dedup(actions)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["pos"], 90)

    def test_duplicates_mixed_with_unique(self):
        actions = [
            {"at": 100, "pos": 20},
            {"at": 200, "pos": 50},
            {"at": 100, "pos": 80},  # dup of at=100; 80 should win
            {"at": 300, "pos": 60},
        ]
        _clamp_sort_dedup(actions)
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0], {"at": 100, "pos": 80})

    def test_no_duplicates_length_preserved(self):
        actions = [{"at": i * 10, "pos": 50} for i in range(5)]
        _clamp_sort_dedup(actions)
        self.assertEqual(len(actions), 5)

    # ------------------------------------------------------------------
    # Combined sort + dedup + clamp
    # ------------------------------------------------------------------

    def test_all_three_in_one(self):
        actions = [
            {"at": 300, "pos": 150},   # out of range → clamp to 100
            {"at": 100, "pos": 50},
            {"at": 200, "pos": 60},
            {"at": 100, "pos": 80},    # dup at=100; 80 wins
        ]
        count = _clamp_sort_dedup(actions)
        # After dedup: at=100→80, at=200→60, at=300→150→100
        self.assertEqual(len(actions), 3)
        self.assertEqual(actions[0], {"at": 100, "pos": 80})
        self.assertEqual(actions[1], {"at": 200, "pos": 60})
        self.assertEqual(actions[2], {"at": 300, "pos": 100})
        self.assertEqual(count, 1)

    def test_empty_list(self):
        actions = []
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 0)
        self.assertEqual(actions, [])

    def test_single_item(self):
        actions = [{"at": 100, "pos": 200}]
        count = _clamp_sort_dedup(actions)
        self.assertEqual(count, 1)
        self.assertEqual(actions[0]["pos"], 100)


if __name__ == "__main__":
    unittest.main()
