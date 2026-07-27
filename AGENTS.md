# Agent guidance

InstructLint is a zero-runtime-dependency Python CLI. Keep checks deterministic,
local-first, and conservative about false positives.

## Commands

- Run the tests with `python -m unittest discover -s tests -v`.
- Run the CLI locally with `PYTHONPATH=src python -m instructlint scan .`.
- Build distributions with `python -m build` when the build package is available.

## Boundaries

- Do not add network calls, telemetry, or runtime dependencies without a design
  discussion.
- Every new diagnostic needs a stable code, a focused test, a useful remediation,
  and documentation in `docs/rules.md`.
- Preserve JSON and SARIF output compatibility within a minor release.

## Verification

Before finishing a change, run the full unit-test suite and scan this repository
with InstructLint.
