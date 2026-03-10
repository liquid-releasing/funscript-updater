# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for the user-transform extension system.

Covers:
- _RecipeTransform: multi-step pipeline, unknown step skipped, structural flag
- load_user_transforms(): JSON recipes, Python plugins, key-clash guard
- Loaded user transforms appear in TRANSFORM_CATALOG after merge
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pattern_catalog.phrase_transforms import (
    TRANSFORM_CATALOG,
    PhraseTransform,
    TransformParam,
    _BUILTIN_KEYS,
    _RecipeTransform,
    load_user_transforms,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_actions(positions):
    return [{"at": i * 100, "pos": p} for i, p in enumerate(positions)]


# ---------------------------------------------------------------------------
# RecipeTransform
# ---------------------------------------------------------------------------

class TestRecipeTransform(unittest.TestCase):

    def test_empty_steps_returns_unchanged(self):
        actions = _make_actions([10, 90, 10, 90])
        recipe = _RecipeTransform(key="r", name="R", description="", steps=[])
        result = recipe.apply(actions)
        self.assertEqual([a["pos"] for a in result], [10, 90, 10, 90])

    def test_single_step_applied(self):
        """A single recenter step should shift midpoint to 50."""
        # positions 10-30 → midpoint 20; recenter to 50 shifts by +30
        actions = _make_actions([10, 30, 10, 30])
        recipe = _RecipeTransform(
            key="r", name="R", description="",
            steps=[{"transform": "recenter", "params": {"target_center": 50}}],
        )
        result = recipe.apply(actions)
        positions = [a["pos"] for a in result]
        self.assertEqual(min(positions), 40)
        self.assertEqual(max(positions), 60)

    def test_two_steps_applied_in_order(self):
        """Recenter then amplitude_scale — verify both are applied."""
        # positions 10-30 centered at 20; recenter → 40-60 centered at 50;
        # amplitude_scale(2.0) → 30-70 centered at 50
        actions = _make_actions([10, 30, 10, 30])
        recipe = _RecipeTransform(
            key="r", name="R", description="",
            steps=[
                {"transform": "recenter",        "params": {"target_center": 50}},
                {"transform": "amplitude_scale", "params": {"scale": 2.0}},
            ],
        )
        result = recipe.apply(actions)
        positions = [a["pos"] for a in result]
        self.assertEqual(min(positions), 30)
        self.assertEqual(max(positions), 70)

    def test_unknown_step_skipped_gracefully(self):
        """An unknown step key should be skipped without raising."""
        actions = _make_actions([20, 80, 20, 80])
        recipe = _RecipeTransform(
            key="r", name="R", description="",
            steps=[
                {"transform": "no_such_transform"},
                {"transform": "passthrough"},
            ],
        )
        result = recipe.apply(actions)
        self.assertEqual([a["pos"] for a in result], [20, 80, 20, 80])

    def test_output_positions_in_range(self):
        actions = _make_actions([0, 100, 0, 100])
        recipe = _RecipeTransform(
            key="r", name="R", description="",
            steps=[{"transform": "amplitude_scale", "params": {"scale": 5.0}}],
        )
        result = recipe.apply(actions)
        for a in result:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_structural_flag_preserved(self):
        recipe = _RecipeTransform(
            key="r", name="R", description="", structural=True, steps=[]
        )
        self.assertTrue(recipe.structural)


# ---------------------------------------------------------------------------
# load_user_transforms — JSON recipes
# ---------------------------------------------------------------------------

class TestLoadRecipes(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write_recipe(self, filename, data):
        path = os.path.join(self.tmp, filename)
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    def test_single_recipe_loaded(self):
        self._write_recipe("my_fix.json", {
            "key": "test_single",
            "name": "Test Single",
            "description": "test",
            "steps": [{"transform": "passthrough"}],
        })
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIn("test_single", result)
        self.assertIsInstance(result["test_single"], _RecipeTransform)

    def test_list_of_recipes_loaded(self):
        self._write_recipe("multi.json", [
            {"key": "test_a", "name": "A", "description": "", "steps": []},
            {"key": "test_b", "name": "B", "description": "", "steps": []},
        ])
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIn("test_a", result)
        self.assertIn("test_b", result)

    def test_builtin_key_clash_skipped(self):
        self._write_recipe("clash.json", {
            "key": "smooth",   # clashes with built-in
            "name": "My Smooth",
            "steps": [],
        })
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertNotIn("smooth", result)

    def test_malformed_json_skipped(self):
        path = os.path.join(self.tmp, "bad.json")
        with open(path, "w") as f:
            f.write("{ not valid json }")
        # Should not raise
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIsInstance(result, dict)

    def test_recipe_apply_works(self):
        self._write_recipe("r.json", {
            "key": "test_recipe_apply",
            "name": "Test Apply",
            "description": "",
            "steps": [{"transform": "smooth", "params": {"strength": 0.1}}],
        })
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        spec = result["test_recipe_apply"]
        actions = _make_actions([10, 90, 10, 90, 10, 90])
        out = spec.apply(actions)
        self.assertEqual(len(out), len(actions))
        for a in out:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)

    def test_structural_flag_from_json(self):
        self._write_recipe("s.json", {
            "key": "test_structural",
            "name": "Structural",
            "description": "",
            "structural": True,
            "steps": [],
        })
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertTrue(result["test_structural"].structural)

    def test_missing_directory_returns_empty(self):
        result = load_user_transforms(
            recipes_dir="/no/such/dir",
            plugins_dir="/no/such/dir",
        )
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# load_user_transforms — Python plugins
# ---------------------------------------------------------------------------

class TestLoadPlugins(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write_plugin(self, filename, code):
        path = os.path.join(self.tmp, filename)
        with open(path, "w") as f:
            f.write(code)
        return path

    def test_single_transform_plugin(self):
        self._write_plugin("myplugin.py", """
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dataclasses import dataclass, field
from pattern_catalog.phrase_transforms import PhraseTransform, TransformParam

@dataclass
class _MyPlugin(PhraseTransform):
    def _transform(self, actions, p):
        return actions

TRANSFORM = _MyPlugin(key="plugin_single", name="Plugin Single", description="test")
""")
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIn("plugin_single", result)
        self.assertIsInstance(result["plugin_single"], PhraseTransform)

    def test_transforms_list_plugin(self):
        self._write_plugin("multi_plugin.py", """
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dataclasses import dataclass
from pattern_catalog.phrase_transforms import PhraseTransform

@dataclass
class _A(PhraseTransform):
    def _transform(self, a, p): return a

@dataclass
class _B(PhraseTransform):
    def _transform(self, a, p): return a

TRANSFORMS = [
    _A(key="plugin_list_a", name="A", description=""),
    _B(key="plugin_list_b", name="B", description=""),
]
""")
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIn("plugin_list_a", result)
        self.assertIn("plugin_list_b", result)

    def test_plugin_builtin_clash_skipped(self):
        self._write_plugin("clash.py", """
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dataclasses import dataclass
from pattern_catalog.phrase_transforms import PhraseTransform

@dataclass
class _Clash(PhraseTransform):
    def _transform(self, a, p): return a

TRANSFORM = _Clash(key="smooth", name="My Smooth", description="")
""")
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertNotIn("smooth", result)

    def test_broken_plugin_skipped(self):
        self._write_plugin("broken.py", "raise RuntimeError('intentional error')")
        # Should not raise
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        self.assertIsInstance(result, dict)

    def test_plugin_apply_works(self):
        self._write_plugin("invert_plugin.py", """
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dataclasses import dataclass
from pattern_catalog.phrase_transforms import PhraseTransform

@dataclass
class _InvertPlugin(PhraseTransform):
    def _transform(self, actions, p):
        for a in actions:
            a["pos"] = 100 - a["pos"]
        return actions

TRANSFORM = _InvertPlugin(key="plugin_invert_test", name="Invert Test", description="")
""")
        result = load_user_transforms(recipes_dir=self.tmp, plugins_dir=self.tmp)
        spec = result["plugin_invert_test"]
        actions = [{"at": 0, "pos": 30}, {"at": 100, "pos": 70}]
        out = spec.apply(actions)
        self.assertEqual(out[0]["pos"], 70)
        self.assertEqual(out[1]["pos"], 30)


# ---------------------------------------------------------------------------
# _BUILTIN_KEYS integrity
# ---------------------------------------------------------------------------

class TestBuiltinKeys(unittest.TestCase):

    def test_builtin_keys_is_frozenset(self):
        self.assertIsInstance(_BUILTIN_KEYS, frozenset)

    def test_builtin_keys_subset_of_catalog(self):
        self.assertTrue(_BUILTIN_KEYS.issubset(set(TRANSFORM_CATALOG.keys())))

    def test_builtin_keys_contains_expected_entries(self):
        for key in ("passthrough", "amplitude_scale", "smooth", "halve_tempo"):
            self.assertIn(key, _BUILTIN_KEYS)


if __name__ == "__main__":
    unittest.main()
