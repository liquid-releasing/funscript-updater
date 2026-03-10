# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for catalog/pattern_catalog.py — persistent cross-funscript catalog."""

import json
import os
import tempfile
import unittest


class TestPatternCatalog(unittest.TestCase):

    def setUp(self):
        self._tmp  = tempfile.mkdtemp()
        self._path = os.path.join(self._tmp, "catalog.json")

    def _make_catalog(self):
        from catalog.pattern_catalog import PatternCatalog
        return PatternCatalog(self._path)

    def _tagged_phrase(self, start=0, end=10_000, tag="stingy", bpm=130.0):
        return {
            "start_ms":      start,
            "end_ms":        end,
            "bpm":           bpm,
            "pattern_label": "up -> down",
            "tags":          [tag],
            "metrics": {
                "mean_pos": 50.0, "span": 80.0,
                "mean_velocity": 0.4, "peak_velocity": 0.5,
                "cv_bpm": 0.05, "duration_ms": end - start,
            },
        }

    def _untagged_phrase(self):
        return {
            "start_ms": 0, "end_ms": 5000, "bpm": 60.0,
            "pattern_label": "up -> down",
            "tags": [], "metrics": {},
        }

    # ------------------------------------------------------------------
    # Empty catalog
    # ------------------------------------------------------------------

    def test_empty_catalog_summary(self):
        cat = self._make_catalog()
        s = cat.summary()
        self.assertEqual(s["funscripts_indexed"], 0)
        self.assertEqual(s["total_tagged_phrases"], 0)
        self.assertEqual(s["tags_found"], [])

    def test_empty_catalog_get_tag_stats(self):
        cat = self._make_catalog()
        self.assertEqual(cat.get_tag_stats(), {})

    def test_empty_catalog_entries(self):
        cat = self._make_catalog()
        self.assertEqual(cat.entries, [])

    # ------------------------------------------------------------------
    # add_assessment
    # ------------------------------------------------------------------

    def test_add_returns_tagged_count(self):
        cat = self._make_catalog()
        n = cat.add_assessment("a.funscript", [self._tagged_phrase(), self._untagged_phrase()])
        self.assertEqual(n, 1)  # only the tagged one

    def test_untagged_phrases_not_stored(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._untagged_phrase()])
        self.assertEqual(cat.summary()["total_tagged_phrases"], 0)

    def test_add_increments_count(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        cat.add_assessment("b.funscript", [self._tagged_phrase(tag="giggle")])
        self.assertEqual(cat.summary()["funscripts_indexed"], 2)
        self.assertEqual(cat.summary()["total_tagged_phrases"], 2)

    def test_re_add_replaces_existing(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        cat.add_assessment("a.funscript", [self._tagged_phrase(), self._tagged_phrase(end=20_000)])
        self.assertEqual(cat.summary()["funscripts_indexed"], 1)
        self.assertEqual(cat.summary()["total_tagged_phrases"], 2)

    def test_duration_ms_stored(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()], duration_ms=60_000)
        self.assertEqual(cat.entries[0]["duration_ms"], 60_000)

    # ------------------------------------------------------------------
    # save / load round-trip
    # ------------------------------------------------------------------

    def test_save_creates_file(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        cat.save()
        self.assertTrue(os.path.exists(self._path))

    def test_save_load_round_trip(self):
        from catalog.pattern_catalog import PatternCatalog
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()], duration_ms=30_000)
        cat.save()
        cat2 = PatternCatalog(self._path)
        self.assertEqual(cat2.summary()["funscripts_indexed"], 1)
        self.assertEqual(cat2.summary()["total_tagged_phrases"], 1)

    def test_corrupted_file_returns_empty(self):
        from catalog.pattern_catalog import PatternCatalog
        with open(self._path, "w") as f:
            f.write("not valid json {{{")
        cat = PatternCatalog(self._path)
        self.assertEqual(cat.summary()["funscripts_indexed"], 0)

    def test_saved_json_has_version(self):
        cat = self._make_catalog()
        cat.save()
        with open(self._path) as f:
            data = json.load(f)
        self.assertIn("version", data)

    # ------------------------------------------------------------------
    # remove
    # ------------------------------------------------------------------

    def test_remove_existing_entry(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        cat.add_assessment("b.funscript", [self._tagged_phrase(tag="giggle")])
        removed = cat.remove("a.funscript")
        self.assertTrue(removed)
        self.assertEqual(cat.summary()["funscripts_indexed"], 1)
        self.assertNotIn("a.funscript", cat.funscript_names)

    def test_remove_nonexistent_returns_false(self):
        cat = self._make_catalog()
        self.assertFalse(cat.remove("nope.funscript"))

    # ------------------------------------------------------------------
    # get_tag_stats
    # ------------------------------------------------------------------

    def test_stats_count_across_funscripts(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [
            self._tagged_phrase(tag="stingy"),
            self._tagged_phrase(end=20_000, tag="stingy"),
        ])
        cat.add_assessment("b.funscript", [self._tagged_phrase(tag="stingy")])
        stats = cat.get_tag_stats()
        self.assertEqual(stats["stingy"]["count"], 3)
        self.assertEqual(stats["stingy"]["funscripts"], 2)

    def test_stats_include_all_required_keys(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        stats = cat.get_tag_stats()
        for key in ("count", "funscripts", "bpm_min", "bpm_max",
                    "span_min", "span_max", "mean_vel_mean", "duration_mean_ms"):
            self.assertIn(key, stats["stingy"], msg=f"Missing key: {key}")

    def test_stats_bpm_range(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [
            self._tagged_phrase(bpm=100.0),
            self._tagged_phrase(end=20_000, bpm=150.0),
        ])
        stats = cat.get_tag_stats()["stingy"]
        self.assertEqual(stats["bpm_min"], 100.0)
        self.assertEqual(stats["bpm_max"], 150.0)

    def test_stats_separate_per_tag(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [
            self._tagged_phrase(tag="stingy"),
            self._tagged_phrase(end=20_000, tag="giggle"),
        ])
        stats = cat.get_tag_stats()
        self.assertIn("stingy", stats)
        self.assertIn("giggle", stats)
        self.assertEqual(stats["stingy"]["count"], 1)
        self.assertEqual(stats["giggle"]["count"], 1)

    # ------------------------------------------------------------------
    # get_phrases_for_tag
    # ------------------------------------------------------------------

    def test_get_phrases_for_tag_filters_correctly(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase(tag="stingy")])
        cat.add_assessment("b.funscript", [self._tagged_phrase(tag="giggle")])
        stingy = cat.get_phrases_for_tag("stingy")
        self.assertEqual(len(stingy), 1)
        self.assertEqual(stingy[0]["_funscript"], "a.funscript")

    def test_get_phrases_for_tag_includes_funscript_key(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        phrases = cat.get_phrases_for_tag("stingy")
        self.assertIn("_funscript", phrases[0])

    def test_get_phrases_for_missing_tag_returns_empty(self):
        cat = self._make_catalog()
        self.assertEqual(cat.get_phrases_for_tag("nonexistent"), [])

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def test_funscript_names_property(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [self._tagged_phrase()])
        cat.add_assessment("b.funscript", [self._tagged_phrase()])
        self.assertCountEqual(cat.funscript_names, ["a.funscript", "b.funscript"])

    def test_summary_tags_found_sorted(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [
            self._tagged_phrase(tag="stingy"),
            self._tagged_phrase(end=20_000, tag="giggle"),
        ])
        s = cat.summary()
        self.assertEqual(s["tags_found"], sorted(s["tags_found"]))

    def test_tag_counts_in_summary(self):
        cat = self._make_catalog()
        cat.add_assessment("a.funscript", [
            self._tagged_phrase(tag="stingy"),
            self._tagged_phrase(end=20_000, tag="stingy"),
        ])
        s = cat.summary()
        self.assertEqual(s["tag_counts"]["stingy"], 2)


if __name__ == "__main__":
    unittest.main()
