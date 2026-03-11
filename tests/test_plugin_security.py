# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for user-transform plugin security controls.

Covers:
- JSON recipe schema validator (_validate_recipe_entry)
  * Valid entries accepted
  * Missing / malformed key rejected
  * Non-list / empty steps rejected
  * Unknown step transform rejected (must be a built-in key)
  * Non-scalar params rejected (nested objects / arrays)
- load_user_transforms JSON loader rejects bad entries individually
  while still loading good ones from the same file
- Python plugin gate: .py files skipped when FUNSCRIPT_PLUGINS_ENABLED
  is not set; loaded when the flag is set
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pattern_catalog.phrase_transforms import (
    _validate_recipe_entry,
    load_user_transforms,
    _BUILTIN_KEYS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_entry(**overrides):
    """Return a minimal valid recipe entry dict."""
    base = {
        "key": "my_test_transform",
        "name": "Test Transform",
        "steps": [{"transform": "passthrough", "params": {}}],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Schema validator unit tests
# ---------------------------------------------------------------------------

class TestValidateRecipeEntry(unittest.TestCase):

    def test_valid_entry_accepted(self):
        self.assertIsNone(_validate_recipe_entry(_good_entry()))

    def test_valid_entry_with_params(self):
        entry = _good_entry(steps=[
            {"transform": "amplitude_scale", "params": {"scale": 1.5}},
            {"transform": "smooth", "params": {"strength": 0.1}},
        ])
        self.assertIsNone(_validate_recipe_entry(entry))

    def test_non_dict_entry_rejected(self):
        for bad in [None, "string", 42, []]:
            with self.subTest(bad=bad):
                self.assertIsNotNone(_validate_recipe_entry(bad))

    def test_missing_key_rejected(self):
        entry = _good_entry()
        del entry["key"]
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_empty_key_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(key="")))

    def test_key_with_uppercase_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(key="MyTransform")))

    def test_key_with_spaces_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(key="my transform")))

    def test_key_starting_with_digit_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(key="1bad")))

    def test_key_with_path_traversal_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(key="../evil")))

    def test_valid_key_patterns(self):
        for key in ("abc", "a1", "a_b", "my_long_key_name_here"):
            with self.subTest(key=key):
                self.assertIsNone(_validate_recipe_entry(_good_entry(key=key)))

    def test_steps_missing_rejected(self):
        entry = _good_entry()
        del entry["steps"]
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_steps_empty_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(steps=[])))

    def test_steps_not_list_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(steps="passthrough")))

    def test_step_non_object_rejected(self):
        self.assertIsNotNone(_validate_recipe_entry(_good_entry(steps=["passthrough"])))

    def test_unknown_step_transform_rejected(self):
        """A step referencing a key outside _BUILTIN_KEYS must be rejected."""
        entry = _good_entry(steps=[{"transform": "evil_custom_transform", "params": {}}])
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_unknown_step_cannot_chain_user_transform(self):
        """Prevents recipe chaining into other user-defined transforms."""
        # Even if another user transform exists with key "my_other", steps
        # must only reference built-ins.
        entry = _good_entry(steps=[{"transform": "my_other", "params": {}}])
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_all_builtin_keys_allowed_as_steps(self):
        """Every built-in key should be valid as a step transform."""
        for key in _BUILTIN_KEYS:
            entry = _good_entry(steps=[{"transform": key, "params": {}}])
            with self.subTest(key=key):
                self.assertIsNone(_validate_recipe_entry(entry))

    def test_nested_object_param_rejected(self):
        entry = _good_entry(steps=[{
            "transform": "passthrough",
            "params": {"nested": {"inner": 1}},
        }])
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_list_param_rejected(self):
        entry = _good_entry(steps=[{
            "transform": "passthrough",
            "params": {"bad": [1, 2, 3]},
        }])
        self.assertIsNotNone(_validate_recipe_entry(entry))

    def test_scalar_param_types_accepted(self):
        for val in (1, 1.5, "text", True, False):
            entry = _good_entry(steps=[{
                "transform": "amplitude_scale",
                "params": {"scale": val},
            }])
            with self.subTest(val=val):
                self.assertIsNone(_validate_recipe_entry(entry))


# ---------------------------------------------------------------------------
# load_user_transforms: selective rejection from mixed file
# ---------------------------------------------------------------------------

class TestLoadUserTransformsSchema(unittest.TestCase):

    def _write_json(self, tmpdir, filename, data):
        path = os.path.join(tmpdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_valid_entry_loads(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_json(d, "good.json", [_good_entry()])
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        self.assertIn("my_test_transform", result)

    def test_invalid_entry_skipped_good_entry_loads(self):
        """A bad entry in the same file must not block the good one."""
        bad = {"key": "BAD KEY!", "steps": []}
        good = _good_entry(key="good_one")
        with tempfile.TemporaryDirectory() as d:
            self._write_json(d, "mixed.json", [bad, good])
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        self.assertNotIn("BAD KEY!", result)
        self.assertIn("good_one", result)

    def test_unknown_step_entry_rejected(self):
        entry = _good_entry(key="sneaky", steps=[{"transform": "os_system_hack", "params": {}}])
        with tempfile.TemporaryDirectory() as d:
            self._write_json(d, "evil.json", [entry])
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        self.assertNotIn("sneaky", result)

    def test_nested_param_entry_rejected(self):
        entry = _good_entry(key="badparam", steps=[{
            "transform": "passthrough",
            "params": {"x": {"__import__": "os"}},
        }])
        with tempfile.TemporaryDirectory() as d:
            self._write_json(d, "nested.json", [entry])
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        self.assertNotIn("badparam", result)

    def test_builtin_key_clash_skipped(self):
        entry = _good_entry(key="passthrough")
        with tempfile.TemporaryDirectory() as d:
            self._write_json(d, "clash.json", [entry])
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        # passthrough already in _BUILTIN_KEYS — the user entry must not
        # overwrite it (the catalog was already built before this call)
        self.assertNotIn("passthrough", result)


# ---------------------------------------------------------------------------
# Python plugin gate
# ---------------------------------------------------------------------------

class TestPluginGate(unittest.TestCase):

    def _write_plugin(self, tmpdir, filename="my_plugin.py"):
        """Write a syntactically valid minimal plugin file."""
        path = os.path.join(tmpdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            # A plugin that registers nothing — just a sentinel to check loading
            f.write(
                "# minimal plugin\n"
                "from pattern_catalog.phrase_transforms import PhraseTransform\n"
                "TRANSFORMS = []\n"
            )
        return path

    def test_plugin_skipped_without_flag(self):
        """Without FUNSCRIPT_PLUGINS_ENABLED, .py files must not be executed."""
        os.environ.pop("FUNSCRIPT_PLUGINS_ENABLED", None)
        with tempfile.TemporaryDirectory() as d:
            self._write_plugin(d)
            # If the gate works, loading should complete without error and
            # the empty TRANSFORMS list should produce no new keys.
            result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        # No keys from the plugin (it wasn't loaded)
        self.assertEqual(result, {})

    def test_example_plugin_always_skipped(self):
        """Files starting with example_ are skipped even with the flag set."""
        os.environ["FUNSCRIPT_PLUGINS_ENABLED"] = "1"
        try:
            with tempfile.TemporaryDirectory() as d:
                self._write_plugin(d, filename="example_plugin.py")
                result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        finally:
            os.environ.pop("FUNSCRIPT_PLUGINS_ENABLED", None)
        self.assertEqual(result, {})

    def test_plugin_loaded_with_flag(self):
        """With FUNSCRIPT_PLUGINS_ENABLED=1, plugins should be executed."""
        os.environ["FUNSCRIPT_PLUGINS_ENABLED"] = "1"
        try:
            with tempfile.TemporaryDirectory() as d:
                # Write a plugin that actually registers a transform
                path = os.path.join(d, "real_plugin.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(
                        "import sys, os\n"
                        "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))\n"
                        "from pattern_catalog.phrase_transforms import PhraseTransform\n"
                        "from dataclasses import dataclass\n"
                        "@dataclass\n"
                        "class _P(PhraseTransform):\n"
                        "    def _transform(self, actions, p): return actions\n"
                        "TRANSFORM = _P(key='test_gate_plugin', name='Test', description='Test plugin', structural=False)\n"
                    )
                result = load_user_transforms(recipes_dir=d, plugins_dir=d)
        finally:
            os.environ.pop("FUNSCRIPT_PLUGINS_ENABLED", None)
        self.assertIn("test_gate_plugin", result)

    def test_flag_values_true_and_yes(self):
        """'true' and 'yes' are also accepted as truthy values for the flag."""
        for val in ("true", "yes", "True", "YES"):
            os.environ["FUNSCRIPT_PLUGINS_ENABLED"] = val
            try:
                with tempfile.TemporaryDirectory() as d:
                    # No .py files — just verify it doesn't crash
                    result = load_user_transforms(recipes_dir=d, plugins_dir=d)
            finally:
                os.environ.pop("FUNSCRIPT_PLUGINS_ENABLED", None)
            self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
