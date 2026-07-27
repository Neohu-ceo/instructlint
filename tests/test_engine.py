from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from instructlint.engine import scan_repository
from instructlint.explain import explain_target
from instructlint.sarif import to_sarif


class Repository:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def write(self, relative: str, text: str = "") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def close(self):
        self.temporary.cleanup()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def tearDown(self):
        self.repo.close()

    def codes(self):
        return [item.code for item in scan_repository(self.repo.root).diagnostics]

    def test_reports_repository_without_instructions(self):
        self.assertEqual(self.codes(), ["CTX000"])

    def test_discovers_supported_formats(self):
        self.repo.write("AGENTS.md", "Run pytest before finishing.\n")
        self.repo.write("nested/CLAUDE.md", "Use Python.\n")
        self.repo.write(
            ".cursor/rules/python.mdc",
            '---\nglobs: "**/*.py"\n---\nUse type hints.\n',
        )
        self.repo.write(
            ".github/instructions/web.instructions.md",
            '---\napplyTo: "**/*.ts"\n---\nUse strict mode.\n',
        )
        result = scan_repository(self.repo.root)
        self.assertEqual(len(result.files), 4)
        self.assertNotIn("SCP001", [item.code for item in result.diagnostics])
        self.assertNotIn("SCP002", [item.code for item in result.diagnostics])

    def test_discovers_nested_vendor_directories(self):
        self.repo.write("AGENTS.md", "Run pytest.\n")
        self.repo.write(
            "packages/api/.cursor/rules/python.mdc",
            '---\nglobs: "**/*.py"\n---\nUse type hints.\n',
        )
        result = scan_repository(self.repo.root)
        self.assertIn(
            "packages/api/.cursor/rules/python.mdc",
            [item.relative_path for item in result.files],
        )

    def test_honours_instructlint_ignore(self):
        self.repo.write("AGENTS.md", "Run pytest.\n")
        self.repo.write("fixtures/bad/AGENTS.md", "Run rm -rf build.\n")
        self.repo.write(".instructlintignore", "fixtures/bad/**\n")
        result = scan_repository(self.repo.root)
        self.assertEqual([item.relative_path for item in result.files], ["AGENTS.md"])
        self.assertNotIn("DNG001", [item.code for item in result.diagnostics])

    def test_dangerous_command_but_not_a_prohibition(self):
        self.repo.write(
            "AGENTS.md",
            "Run rm -rf build before packaging.\nNever run git reset --hard.\nRun pytest.\n",
        )
        codes = self.codes()
        self.assertIn("DNG001", codes)
        self.assertNotIn("DNG002", codes)

    def test_dangerous_command_named_under_blocked_heading_is_not_approved(self):
        self.repo.write(
            "AGENTS.md",
            "# Commands that are blocked\n\n- `git reset --hard`\nRun pytest.\n",
        )
        self.assertNotIn("DNG002", self.codes())

    def test_finds_direct_contradiction(self):
        self.repo.write("AGENTS.md", "Always use npm for installs.\nRun npm test.\n")
        self.repo.write("CLAUDE.md", "Never use npm for installs.\n")
        result = scan_repository(self.repo.root)
        conflict = next(item for item in result.diagnostics if item.code == "CNF001")
        self.assertEqual(conflict.severity, "error")
        self.assertIn("CLAUDE.md", conflict.message)

    def test_finds_stale_path_but_accepts_existing_path(self):
        self.repo.write(
            "AGENTS.md",
            "Read `docs/real.md` and `docs/missing.md`.\nRun pytest.\n",
        )
        self.repo.write("docs/real.md", "# Real\n")
        messages = [
            item.message
            for item in scan_repository(self.repo.root).diagnostics
            if item.code == "REF001"
        ]
        self.assertEqual(messages, ["path reference does not exist: docs/missing.md"])

    def test_accepts_unique_shorthand_and_ignored_generated_paths(self):
        self.repo.write(
            "AGENTS.md",
            "Read `parser.py`, `.cache/results.db`, and use `/review`.\nRun pytest.\n",
        )
        self.repo.write("src/tool/parser.py", "")
        self.repo.write(".gitignore", ".cache/\n")
        self.assertNotIn("REF001", self.codes())
        self.assertNotIn("REF002", self.codes())

    def test_skill_code_paths_are_caller_workspace_examples(self):
        self.repo.write("AGENTS.md", "Run pytest.\n")
        self.repo.write(
            "skills/scaffold/SKILL.md",
            "Create `src/new_file.ts` and run bun install in the target project.\n",
        )
        codes = self.codes()
        self.assertNotIn("REF001", codes)
        self.assertNotIn("PKG003", codes)

    def test_skill_literal_links_and_scoped_packages_are_not_local_references(self):
        self.repo.write("AGENTS.md", "Run pytest.\n")
        self.repo.write(
            "skills/scaffold/SKILL.md",
            "Install @total-typescript/shoehorn. Then write "
            "`See [packages](./src/packages/README.md)` in the target repo.\n",
        )
        self.assertNotIn("REF001", self.codes())

    def test_finds_package_manager_drift(self):
        self.repo.write("package-lock.json", json.dumps({"lockfileVersion": 3}))
        self.repo.write("AGENTS.md", "Always run yarn install.\nRun npm test.\n")
        self.assertIn("PKG002", self.codes())

    def test_package_manager_alternatives_and_prohibitions_do_not_warn(self):
        self.repo.write("pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        self.repo.write(
            "AGENTS.md",
            "Use npm run dev, pnpm dev, or yarn dev as appropriate.\n"
            "Do not run npm run build.\nRun pnpm test.\n",
        )
        self.assertNotIn("PKG002", self.codes())

    def test_reports_missing_scoped_metadata(self):
        self.repo.write(
            ".github/instructions/web.instructions.md",
            "Use TypeScript strict mode.\n",
        )
        self.repo.write(".cursor/rules/web.mdc", "Use TypeScript strict mode.\n")
        codes = self.codes()
        self.assertIn("SCP001", codes)
        self.assertIn("SCP002", codes)

    def test_sarif_contains_location_and_rule(self):
        self.repo.write("AGENTS.md", "Run rm -rf build.\nRun pytest.\n")
        document = to_sarif(scan_repository(self.repo.root))
        result = document["runs"][0]["results"][0]
        self.assertEqual(document["version"], "2.1.0")
        self.assertEqual(result["ruleId"], "DNG001")
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "AGENTS.md",
        )

    def test_explain_matches_path_scoped_rule(self):
        self.repo.write("AGENTS.md", "Run pytest.\n")
        self.repo.write(
            ".cursor/rules/python.mdc",
            '---\nglobs:\n  - "src/**/*.py"\n---\nUse type hints.\n',
        )
        self.repo.write(
            ".cursor/rules/web.mdc",
            '---\nglobs: "web/**/*.ts"\n---\nUse strict mode.\n',
        )
        matches = explain_target(self.repo.root, "src/api/client.py", "cursor")
        states = {item.path: item.applies for item in matches}
        self.assertTrue(states["AGENTS.md"])
        self.assertTrue(states[".cursor/rules/python.mdc"])
        self.assertFalse(states[".cursor/rules/web.mdc"])


if __name__ == "__main__":
    unittest.main()
