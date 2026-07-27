from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from instructlint.cli import main


class CliTests(unittest.TestCase):
    def test_json_output_and_exit_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "AGENTS.md").write_text(
                "Run rm -rf build.\nRun pytest.\n", encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = main(["scan", directory, "--format", "json"])
            document = json.loads(output.getvalue())
            self.assertEqual(exit_code, 1)
            self.assertEqual(document["summary"]["error"], 1)

    def test_warning_policy_is_configurable(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "AGENTS.md").write_text(
                "Read `missing.md`.\nRun pytest.\n", encoding="utf-8"
            )
            with contextlib.redirect_stdout(io.StringIO()):
                default_exit = main(["scan", directory])
                strict_exit = main(["scan", directory, "--fail-on", "warning"])
            self.assertEqual(default_exit, 0)
            self.assertEqual(strict_exit, 1)


if __name__ == "__main__":
    unittest.main()
