"""Tests for pattern_catalog/phrase_transforms.py.

Covers:
- TRANSFORM_CATALOG completeness and structure
- Each transform's apply() output
- suggest_transform() rule logic
- TransformParam dataclass fields
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pattern_catalog.phrase_transforms import (
    TRANSFORM_CATALOG,
    PhraseTransform,
    TransformParam,
    suggest_transform,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _actions(positions):
    """Build a minimal action list from a list of positions (1 ms apart)."""
    return [{"at": i * 10, "pos": p} for i, p in enumerate(positions)]


_EXPECTED_KEYS = {
    "passthrough",
    "amplitude_scale",
    "normalize",
    "smooth",
    "clamp_upper",
    "clamp_lower",
    "invert",
    "boost_contrast",
}

_PHRASE_HIGH_BPM = {"bpm": 150.0, "pattern_label": "regular", "amplitude_span": 80}
_PHRASE_LOW_BPM  = {"bpm":  90.0, "pattern_label": "regular", "amplitude_span": 80}
_PHRASE_NARROW   = {"bpm": 150.0, "pattern_label": "regular", "amplitude_span": 30}
_PHRASE_TRANS    = {"bpm": 130.0, "pattern_label": "transition break",  "amplitude_span": 80}


# ---------------------------------------------------------------------------
# Catalog structure
# ---------------------------------------------------------------------------

class TestCatalogStructure(unittest.TestCase):

    def test_all_expected_keys_present(self):
        self.assertEqual(set(TRANSFORM_CATALOG.keys()), _EXPECTED_KEYS)

    def test_each_entry_is_phrase_transform(self):
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(key=key):
                self.assertIsInstance(spec, PhraseTransform)

    def test_keys_match_spec_key_attr(self):
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(key=key):
                self.assertEqual(spec.key, key)

    def test_each_spec_has_name_and_description(self):
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(key=key):
                self.assertIsInstance(spec.name, str)
                self.assertTrue(spec.name, "name should not be empty")
                self.assertIsInstance(spec.description, str)
                self.assertTrue(spec.description, "description should not be empty")

    def test_params_are_transform_param_instances(self):
        for key, spec in TRANSFORM_CATALOG.items():
            for pname, param in spec.params.items():
                with self.subTest(transform=key, param=pname):
                    self.assertIsInstance(param, TransformParam)
                    self.assertIn(param.type, ("float", "int", "bool"))


# ---------------------------------------------------------------------------
# Individual transform behaviour
# ---------------------------------------------------------------------------

class TestPassthrough(unittest.TestCase):

    def test_returns_unchanged_positions(self):
        actions = _actions([10, 50, 90, 20, 80])
        spec = TRANSFORM_CATALOG["passthrough"]
        result = spec.apply(actions)
        self.assertEqual([a["pos"] for a in result], [10, 50, 90, 20, 80])

    def test_does_not_mutate_input(self):
        actions = _actions([30, 70])
        original = [a["pos"] for a in actions]
        TRANSFORM_CATALOG["passthrough"].apply(actions)
        self.assertEqual([a["pos"] for a in actions], original)


class TestAmplitudeScale(unittest.TestCase):

    def test_scale_1_is_identity(self):
        actions = _actions([10, 50, 90])
        spec = TRANSFORM_CATALOG["amplitude_scale"]
        result = spec.apply(actions, {"scale": 1.0})
        self.assertEqual([a["pos"] for a in result], [10, 50, 90])

    def test_scale_2_doubles_distance_from_center(self):
        # pos=75 → centered=25 → scaled=50 → final=100
        actions = _actions([75])
        result = TRANSFORM_CATALOG["amplitude_scale"].apply(actions, {"scale": 2.0})
        self.assertEqual(result[0]["pos"], 100)

    def test_scale_0_collapses_to_center(self):
        actions = _actions([20, 50, 80])
        result = TRANSFORM_CATALOG["amplitude_scale"].apply(actions, {"scale": 0.0})
        for a in result:
            self.assertEqual(a["pos"], 50)

    def test_positions_clamped_0_to_100(self):
        actions = _actions([5, 95])
        result = TRANSFORM_CATALOG["amplitude_scale"].apply(actions, {"scale": 10.0})
        for a in result:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)


class TestNormalize(unittest.TestCase):

    def test_expands_to_full_range(self):
        actions = _actions([30, 40, 50, 60, 70])
        result = TRANSFORM_CATALOG["normalize"].apply(
            actions, {"target_lo": 0, "target_hi": 100}
        )
        positions = [a["pos"] for a in result]
        self.assertEqual(min(positions), 0)
        self.assertEqual(max(positions), 100)

    def test_flat_input_returns_unchanged(self):
        """All identical positions → no span → no change."""
        actions = _actions([50, 50, 50])
        result = TRANSFORM_CATALOG["normalize"].apply(
            actions, {"target_lo": 0, "target_hi": 100}
        )
        self.assertEqual([a["pos"] for a in result], [50, 50, 50])

    def test_custom_target_range(self):
        actions = _actions([0, 100])
        result = TRANSFORM_CATALOG["normalize"].apply(
            actions, {"target_lo": 20, "target_hi": 80}
        )
        positions = [a["pos"] for a in result]
        self.assertEqual(min(positions), 20)
        self.assertEqual(max(positions), 80)


class TestSmooth(unittest.TestCase):

    def test_returns_same_length(self):
        actions = _actions([10, 90, 10, 90, 10, 90])
        result = TRANSFORM_CATALOG["smooth"].apply(actions, {"strength": 0.15})
        self.assertEqual(len(result), len(actions))

    def test_positions_are_integers(self):
        actions = _actions([10, 90, 10, 90])
        result = TRANSFORM_CATALOG["smooth"].apply(actions, {"strength": 0.15})
        for a in result:
            self.assertIsInstance(a["pos"], int)

    def test_empty_actions(self):
        result = TRANSFORM_CATALOG["smooth"].apply([], {"strength": 0.15})
        self.assertEqual(result, [])


class TestClampRange(unittest.TestCase):

    def test_clamp_upper_keeps_in_range(self):
        actions = _actions([0, 50, 100])
        result = TRANSFORM_CATALOG["clamp_upper"].apply(
            actions, {"range_lo": 50, "range_hi": 100}
        )
        for a in result:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)
        # Lower bound of result should be at or above 50 (for pos=0 input: 50+0*50/100=50)
        self.assertGreaterEqual(result[0]["pos"], 50)

    def test_clamp_lower_keeps_in_range(self):
        actions = _actions([0, 50, 100])
        result = TRANSFORM_CATALOG["clamp_lower"].apply(
            actions, {"range_lo": 0, "range_hi": 50}
        )
        for a in result:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)
        # Upper bound: pos=100 → 0 + 100/100*50 = 50
        self.assertLessEqual(result[-1]["pos"], 50)


class TestInvert(unittest.TestCase):

    def test_flips_around_50(self):
        actions = _actions([0, 25, 50, 75, 100])
        result = TRANSFORM_CATALOG["invert"].apply(actions)
        self.assertEqual([a["pos"] for a in result], [100, 75, 50, 25, 0])

    def test_double_invert_is_identity(self):
        actions = _actions([10, 40, 70])
        once = TRANSFORM_CATALOG["invert"].apply(actions)
        twice = TRANSFORM_CATALOG["invert"].apply(once)
        self.assertEqual([a["pos"] for a in twice], [10, 40, 70])


class TestBoostContrast(unittest.TestCase):

    def test_midpoint_unchanged(self):
        actions = _actions([50])
        result = TRANSFORM_CATALOG["boost_contrast"].apply(actions, {"strength": 1.0})
        self.assertEqual(result[0]["pos"], 50)

    def test_high_position_pushed_higher(self):
        actions = _actions([80])
        result = TRANSFORM_CATALOG["boost_contrast"].apply(actions, {"strength": 0.5})
        self.assertGreater(result[0]["pos"], 80)

    def test_low_position_pushed_lower(self):
        actions = _actions([20])
        result = TRANSFORM_CATALOG["boost_contrast"].apply(actions, {"strength": 0.5})
        self.assertLess(result[0]["pos"], 20)

    def test_positions_clamped(self):
        actions = _actions([5, 95])
        result = TRANSFORM_CATALOG["boost_contrast"].apply(actions, {"strength": 2.0})
        for a in result:
            self.assertGreaterEqual(a["pos"], 0)
            self.assertLessEqual(a["pos"], 100)


# ---------------------------------------------------------------------------
# apply() contract
# ---------------------------------------------------------------------------

class TestApplyContract(unittest.TestCase):

    def test_apply_does_not_mutate_input(self):
        """Every transform must deep-copy before modifying."""
        actions = _actions([20, 50, 80])
        original_positions = [a["pos"] for a in actions]
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(transform=key):
                spec.apply(actions)
                self.assertEqual(
                    [a["pos"] for a in actions],
                    original_positions,
                    f"{key}.apply() mutated input",
                )

    def test_apply_empty_actions(self):
        """Every transform handles an empty list without error."""
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(transform=key):
                result = spec.apply([])
                self.assertIsInstance(result, list)
                self.assertEqual(result, [])

    def test_apply_param_defaults_used_when_param_values_empty(self):
        """apply({}) should not raise — defaults fill in missing keys."""
        actions = _actions([10, 50, 90])
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(transform=key):
                result = spec.apply(actions, {})
                self.assertEqual(len(result), len(actions))

    def test_apply_returns_list(self):
        actions = _actions([25, 75])
        for key, spec in TRANSFORM_CATALOG.items():
            with self.subTest(transform=key):
                result = spec.apply(actions)
                self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# suggest_transform()
# ---------------------------------------------------------------------------

class TestSuggestTransform(unittest.TestCase):

    def test_transition_phrase_suggests_smooth(self):
        self.assertEqual(suggest_transform(_PHRASE_TRANS, 120.0), "smooth")

    def test_low_bpm_suggests_passthrough(self):
        self.assertEqual(suggest_transform(_PHRASE_LOW_BPM, 120.0), "passthrough")

    def test_high_bpm_wide_amp_suggests_amplitude_scale(self):
        self.assertEqual(suggest_transform(_PHRASE_HIGH_BPM, 120.0), "amplitude_scale")

    def test_high_bpm_narrow_amp_suggests_normalize(self):
        self.assertEqual(suggest_transform(_PHRASE_NARROW, 120.0), "normalize")

    def test_bpm_exactly_at_threshold_is_high(self):
        phrase = {"bpm": 120.0, "pattern_label": "", "amplitude_span": 80}
        # bpm < threshold → passthrough; bpm >= threshold → amplitude_scale
        self.assertEqual(suggest_transform(phrase, 120.0), "amplitude_scale")

    def test_bpm_just_below_threshold_is_low(self):
        phrase = {"bpm": 119.9, "pattern_label": "", "amplitude_span": 80}
        self.assertEqual(suggest_transform(phrase, 120.0), "passthrough")

    def test_missing_fields_do_not_raise(self):
        """suggest_transform should not crash if optional fields are absent."""
        result = suggest_transform({}, 120.0)
        self.assertIn(result, TRANSFORM_CATALOG)

    def test_returns_valid_catalog_key(self):
        for phrase in [_PHRASE_HIGH_BPM, _PHRASE_LOW_BPM, _PHRASE_NARROW, _PHRASE_TRANS]:
            result = suggest_transform(phrase, 120.0)
            self.assertIn(result, TRANSFORM_CATALOG, f"suggest_transform returned unknown key: {result!r}")


# ---------------------------------------------------------------------------
# TransformParam
# ---------------------------------------------------------------------------

class TestTransformParam(unittest.TestCase):

    def test_fields_present(self):
        p = TransformParam(
            label="Scale factor", type="float", default=1.0,
            min_val=0.0, max_val=5.0, step=0.1, help="A help string",
        )
        self.assertEqual(p.label, "Scale factor")
        self.assertEqual(p.type, "float")
        self.assertAlmostEqual(p.default, 1.0)
        self.assertAlmostEqual(p.min_val, 0.0)
        self.assertAlmostEqual(p.max_val, 5.0)
        self.assertAlmostEqual(p.step, 0.1)
        self.assertEqual(p.help, "A help string")

    def test_optional_fields_default_to_none_or_empty(self):
        p = TransformParam(label="X", type="int", default=5)
        self.assertIsNone(p.min_val)
        self.assertIsNone(p.max_val)
        self.assertIsNone(p.step)
        self.assertEqual(p.help, "")


if __name__ == "__main__":
    unittest.main()
