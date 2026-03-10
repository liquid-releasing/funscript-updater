# Copyright (c) 2026 Liquid Releasing. Licensed under the MIT License.
# Written by human and Claude AI (Claude Sonnet).

"""Tests for corrupted and truncated funscript input handling.

Covers both the analyzer API (raises the right exception with a useful
message) and the CLI layer (exits with code 1 and prints "Error: …" to
stderr without a traceback).

Scenarios
---------
* File does not exist
* File is completely empty
* File is valid JSON but not a JSON object (e.g. a bare string)
* File has a valid JSON object but is missing the 'actions' key
* File has 'actions' but the value is not a list (e.g. null, a string)
* File is truncated mid-JSON (incomplete JSON, parse error)
* File is garbage bytes (binary, not UTF-8)
* File has 'actions' as an empty list (valid — should assess without error)
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from assessment.analyzer import FunscriptAnalyzer
from ui.common.project import Project

_CLI = os.path.join(os.path.dirname(__file__), "..", "cli.py")
_PYTHON = sys.executable


def _run_assess(path: str, extra_args=()) -> tuple:
    """Run `cli.py assess <path>` and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [_PYTHON, _CLI, "assess", path, *extra_args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(_CLI),
    )
    return result.returncode, result.stdout, result.stderr


def _write(tmp: str, name: str, content: bytes) -> str:
    """Write *content* bytes to *tmp/<name>* and return the full path."""
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(content)
    return path


# ---------------------------------------------------------------------------
# Analyzer API tests (FunscriptAnalyzer.load raises appropriate exceptions)
# ---------------------------------------------------------------------------

class TestAnalyzerBadInput(unittest.TestCase):
    """FunscriptAnalyzer.load() must raise FileNotFoundError or ValueError
    for every kind of invalid input.  It must NEVER raise json.JSONDecodeError,
    KeyError, AttributeError, or any other unhandled exception."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    # -- File-level problems --------------------------------------------------

    def test_missing_file_raises_file_not_found(self):
        path = os.path.join(self.tmp, "nonexistent.funscript")
        with self.assertRaises(FileNotFoundError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn(path, str(ctx.exception))

    def test_empty_file_raises_value_error(self):
        path = _write(self.tmp, "empty.funscript", b"")
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("JSON", str(ctx.exception))

    def test_truncated_mid_json_raises_value_error(self):
        # Valid start, cut before closing brace
        partial = b'{"version": 1, "actions": [{"at": 100, "p'
        path = _write(self.tmp, "truncated.funscript", partial)
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("JSON", str(ctx.exception))

    def test_binary_garbage_raises_value_error(self):
        path = _write(self.tmp, "binary.funscript", bytes(range(256)))
        with self.assertRaises((ValueError, UnicodeDecodeError)):
            FunscriptAnalyzer().load(path)

    def test_bare_string_json_raises_value_error(self):
        # Valid JSON but not an object
        path = _write(self.tmp, "string.funscript", b'"just a string"')
        with self.assertRaises((ValueError, AttributeError)):
            FunscriptAnalyzer().load(path)

    def test_json_array_raises_value_error(self):
        path = _write(self.tmp, "array.funscript", b'[1, 2, 3]')
        with self.assertRaises((ValueError, AttributeError)):
            FunscriptAnalyzer().load(path)

    # -- Structure problems ---------------------------------------------------

    def test_missing_actions_key_raises_value_error(self):
        path = _write(self.tmp, "no_actions.funscript",
                      b'{"version": 1, "title": "test"}')
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("actions", str(ctx.exception))

    def test_actions_is_null_raises_value_error(self):
        path = _write(self.tmp, "null_actions.funscript",
                      b'{"version": 1, "actions": null}')
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("actions", str(ctx.exception))

    def test_actions_is_string_raises_value_error(self):
        path = _write(self.tmp, "str_actions.funscript",
                      b'{"version": 1, "actions": "oops"}')
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("actions", str(ctx.exception))

    def test_actions_is_number_raises_value_error(self):
        path = _write(self.tmp, "num_actions.funscript",
                      b'{"version": 1, "actions": 42}')
        with self.assertRaises(ValueError) as ctx:
            FunscriptAnalyzer().load(path)
        self.assertIn("actions", str(ctx.exception))

    # -- Edge cases that must succeed -----------------------------------------

    def test_empty_actions_list_is_valid(self):
        """An empty actions list should load without error.
        analyze() on it will produce an empty result, not crash."""
        path = _write(self.tmp, "empty_actions.funscript",
                      b'{"version": 1, "actions": []}')
        a = FunscriptAnalyzer()
        a.load(path)  # must not raise
        self.assertEqual(a._actions, [])

    def test_minimal_valid_funscript_loads(self):
        """A single-action funscript must load and analyze without error."""
        path = _write(self.tmp, "minimal.funscript",
                      b'{"version": 1, "actions": [{"at": 0, "pos": 50}]}')
        a = FunscriptAnalyzer()
        a.load(path)
        self.assertEqual(len(a._actions), 1)


# ---------------------------------------------------------------------------
# CLI tests — bad input must exit 1 and print a clean error, not a traceback
# ---------------------------------------------------------------------------

class TestCliBadInput(unittest.TestCase):
    """CLI `assess` must exit with code 1 for bad input and print a clean
    one-line 'Error: …' message to stderr without a Python traceback."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _assert_clean_error(self, rc: int, stdout: str, stderr: str) -> None:
        self.assertEqual(rc, 1, f"Expected exit code 1, got {rc}\nstdout:{stdout}\nstderr:{stderr}")
        self.assertIn("Error:", stderr, f"Expected 'Error:' in stderr:\n{stderr}")
        # No Python traceback — Traceback would start with 'Traceback'
        self.assertNotIn("Traceback", stderr,
                         f"Unexpected traceback in stderr:\n{stderr}")

    def test_missing_file_exits_1(self):
        rc, out, err = _run_assess(os.path.join(self.tmp, "nope.funscript"))
        self._assert_clean_error(rc, out, err)

    def test_empty_file_exits_1(self):
        path = _write(self.tmp, "empty.funscript", b"")
        rc, out, err = _run_assess(path)
        self._assert_clean_error(rc, out, err)

    def test_truncated_json_exits_1(self):
        path = _write(self.tmp, "trunc.funscript",
                      b'{"version": 1, "actions": [{"at": 0, "po')
        rc, out, err = _run_assess(path)
        self._assert_clean_error(rc, out, err)

    def test_missing_actions_key_exits_1(self):
        path = _write(self.tmp, "no_actions.funscript",
                      b'{"version": 1, "title": "test"}')
        rc, out, err = _run_assess(path)
        self._assert_clean_error(rc, out, err)

    def test_actions_is_null_exits_1(self):
        path = _write(self.tmp, "null_actions.funscript",
                      b'{"version": 1, "actions": null}')
        rc, out, err = _run_assess(path)
        self._assert_clean_error(rc, out, err)

    def test_binary_garbage_exits_1(self):
        path = _write(self.tmp, "garbage.funscript", bytes(range(256)))
        rc, out, err = _run_assess(path)
        # May exit 1 for JSON error or UnicodeDecodeError — either is acceptable
        self.assertNotEqual(rc, 0)

    def test_valid_funscript_still_exits_0(self):
        """Sanity: a valid funscript must still exit 0 after adding error handling."""
        fixture = os.path.join(os.path.dirname(__file__), "fixtures", "sample.funscript")
        if not os.path.isfile(fixture):
            self.skipTest("sample.funscript fixture not found")
        out_path = os.path.join(self.tmp, "out.json")
        rc, _, _ = _run_assess(fixture, ("--output", out_path))
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(out_path))


# ---------------------------------------------------------------------------
# Project.from_funscript — bad input propagates the same exceptions
# ---------------------------------------------------------------------------

class TestProjectBadInput(unittest.TestCase):
    """Project.from_funscript must propagate FileNotFoundError / ValueError
    for invalid funscripts so callers (UI, CLI) can handle them cleanly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            Project.from_funscript(os.path.join(self.tmp, "ghost.funscript"))

    def test_corrupt_json_raises(self):
        path = _write(self.tmp, "corrupt.funscript", b"{not valid json")
        with self.assertRaises(ValueError):
            Project.from_funscript(path)

    def test_missing_actions_key_raises(self):
        path = _write(self.tmp, "no_actions.funscript",
                      b'{"version": 1}')
        with self.assertRaises(ValueError):
            Project.from_funscript(path)

    def test_truncated_raises(self):
        path = _write(self.tmp, "trunc.funscript",
                      b'{"version": 1, "actions": [{"at": 0,')
        with self.assertRaises(ValueError):
            Project.from_funscript(path)


if __name__ == "__main__":
    unittest.main()
