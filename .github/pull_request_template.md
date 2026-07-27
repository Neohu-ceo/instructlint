## What changed

<!-- Keep this focused on behavior, not implementation chronology. -->

## Fixture

<!-- Show the smallest before/after instruction input for a rule change. -->

## Verification

- [ ] `python -m unittest discover -s tests -v`
- [ ] `ruff check src tests`
- [ ] `ruff format --check src tests`
- [ ] `PYTHONPATH=src python -m instructlint scan .`

## Compatibility

- [ ] Diagnostic codes and JSON/SARIF fields remain compatible, or the breaking
      change is documented.
