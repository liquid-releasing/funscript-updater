"""Unit tests for utils.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from utils import parse_timestamp, ms_to_timestamp, overlaps, low_pass_filter


class TestParseTimestamp(unittest.TestCase):
    def test_full_format(self):
        self.assertEqual(parse_timestamp("01:02:03.456"), 3_723_456)

    def test_mm_ss_format(self):
        self.assertEqual(parse_timestamp("02:03.456"), 123_456)

    def test_ss_format(self):
        self.assertEqual(parse_timestamp("03.456"), 3_456)

    def test_no_millis(self):
        self.assertEqual(parse_timestamp("00:01:00"), 60_000)

    def test_zero(self):
        self.assertEqual(parse_timestamp("00:00:00.000"), 0)

    def test_millis_padding(self):
        # "1" should be treated as "100" (left-padded to 3 digits)
        self.assertEqual(parse_timestamp("00:00:01.1"), 1_100)

    def test_whitespace_stripped(self):
        self.assertEqual(parse_timestamp("  00:00:05.000  "), 5_000)


class TestMsToTimestamp(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(ms_to_timestamp(3_723_456), "01:02:03.456")

    def test_zero(self):
        self.assertEqual(ms_to_timestamp(0), "00:00:00.000")

    def test_negative_clamps_to_zero(self):
        self.assertEqual(ms_to_timestamp(-100), "00:00:00.000")

    def test_one_minute(self):
        self.assertEqual(ms_to_timestamp(60_000), "00:01:00.000")

    def test_one_hour(self):
        self.assertEqual(ms_to_timestamp(3_600_000), "01:00:00.000")


class TestRoundTrip(unittest.TestCase):
    def test_round_trip_values(self):
        for ms in [0, 1, 999, 1_000, 60_000, 3_600_000, 3_723_456, 7_384_291]:
            with self.subTest(ms=ms):
                self.assertEqual(parse_timestamp(ms_to_timestamp(ms)), ms)


class TestOverlaps(unittest.TestCase):
    def test_overlapping(self):
        self.assertTrue(overlaps(0, 10, 5, 15))

    def test_non_overlapping(self):
        self.assertFalse(overlaps(0, 5, 10, 15))

    def test_touching_at_endpoint(self):
        self.assertTrue(overlaps(0, 5, 5, 10))

    def test_contained(self):
        self.assertTrue(overlaps(2, 4, 0, 10))

    def test_identical(self):
        self.assertTrue(overlaps(5, 10, 5, 10))

    def test_adjacent_no_overlap(self):
        self.assertFalse(overlaps(0, 4, 5, 10))


class TestLowPassFilter(unittest.TestCase):
    def test_passthrough_at_zero_strength(self):
        values = [10, 20, 30, 40]
        strengths = [0.0, 0.0, 0.0, 0.0]
        result = low_pass_filter(values, strengths)
        self.assertEqual(result, values)

    def test_full_smoothing_locks_to_first(self):
        values = [10, 20, 30, 40]
        strengths = [1.0, 1.0, 1.0, 1.0]
        result = low_pass_filter(values, strengths)
        # All values should equal the first (no change propagates)
        self.assertEqual(result, [10, 10, 10, 10])

    def test_output_length_matches_input(self):
        values = [1, 2, 3, 4, 5]
        strengths = [0.5] * 5
        result = low_pass_filter(values, strengths)
        self.assertEqual(len(result), len(values))

    def test_empty(self):
        self.assertEqual(low_pass_filter([], []), [])

    def test_single_element(self):
        self.assertEqual(low_pass_filter([42], [0.5]), [42])


if __name__ == "__main__":
    unittest.main()
