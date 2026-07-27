# Contributing

Thank you for helping make coding-agent instructions safer.

1. Open an issue for new heuristics so false-positive tradeoffs are visible.
2. Add a minimal fixture and a `unittest` regression test.
3. Give every diagnostic a stable code, severity, remediation, and entry in
   `docs/rules.md`.
4. Run:

   ```bash
   python -m unittest discover -s tests -v
   ruff check src tests
   ruff format --check src tests
   PYTHONPATH=src python -m instructlint scan .
   ```

Small, focused pull requests are easiest to review. By contributing, you agree
that your changes are licensed under the MIT License.
