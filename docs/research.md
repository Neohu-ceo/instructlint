# Research notes

Research date: 2026-07-27.

## Signals

The project was selected after reviewing fast-growing GitHub developer tools and
the instruction formats they depend on:

- [AGENTS.md](https://github.com/agentsmd/agents.md) established a broadly used,
  nested repository instruction convention.
- [Ruler](https://github.com/intellectronica/ruler) and
  [Rulesync](https://github.com/dyoshikawa/rulesync) show demand for distributing
  one rule source to many coding agents.
- [Microsoft APM](https://github.com/microsoft/apm) treats agent context as a
  packageable development artifact.
- [agent-readiness](https://github.com/kodustech/agent-readiness) shows demand
  for deterministic, local checks around agent-compatible repositories.
- Public requests in
  [agentsmd/agents.md#179](https://github.com/agentsmd/agents.md/issues/179) and
  [anthropics/claude-code#6235](https://github.com/anthropics/claude-code/issues/6235)
  document cross-tool duplication and path-scoped rule inconsistency.
- GitHub's own documentation describes repository-wide, path-specific, and
  nested agent instruction files, making precedence and overlap a practical
  maintenance concern.

## Product gap

Existing tools mostly standardize, generate, synchronize, or broadly score agent
configuration. The missing narrow layer is familiar from every other part of the
developer toolchain: a linter for the instruction artifacts themselves.

InstructLint therefore:

1. Reads existing vendor and open formats without converting them.
2. Finds concrete safety, reference, scope, and contradiction defects.
3. Runs without a model so CI is fast, private, and reproducible.
4. Exports SARIF instead of inventing a separate review surface.

## Originality and license boundary

The implementation is original and uses only Python's standard library at
runtime. Research used public documentation, interfaces, issues, and README
descriptions to identify the problem; no source code was copied from the
referenced projects. InstructLint is released independently under MIT.

## Public-fixture calibration

The 0.1.0 engine was run against five public repositories after every heuristic
was implemented. This was a precision exercise, not a ranking:

| Repository | Instruction files | Error | Warning | Info | Notable result |
| --- | ---: | ---: | ---: | ---: | --- |
| `agentsmd/agents.md` | 1 | 0 | 1 | 0 | pnpm lockfile versus npm command table |
| `tirth8205/code-review-graph` | 11 | 1 | 0 | 6 | approved recursive forced deletion |
| `intellectronica/ruler` | 3 | 0 | 0 | 5 | intentional cross-file duplication |
| `mattpocock/skills` | 43 | 0 | 0 | 2 | clean after Skill target-path calibration |
| `kodustech/agent-readiness` | 0 | 0 | 1 | 0 | no supported instruction artifact |

The first pass produced many false stale-path warnings in reusable Skills,
because those paths belong to the future caller repository. InstructLint now
validates linked bundled resources while treating inline Skill paths and package
commands as caller-workspace examples. It also understands prohibition headings,
ignored generated paths, shorthand file references, and package-manager
alternatives. Fixtures for each refinement are in the test suite.
