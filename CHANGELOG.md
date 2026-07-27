# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
semantic versioning.

## [Unreleased]

## [0.1.2] - 2026-07-28

### Security

- Pin all upstream GitHub Actions to full, verified commit SHAs.
- Upgrade `actions/checkout` to 7.0.1 and `actions/setup-python` to 7.0.0.
- Add weekly Dependabot monitoring for workflow and root-action dependencies.

## [0.1.1] - 2026-07-27

### Added

- Reusable composite GitHub Action with configurable path, failure threshold,
  output format, file-size limit, and Python version.
- CI coverage that installs and runs the local action against the repository.

## [0.1.0] - 2026-07-27

### Added

- Discovery for major repository instruction formats and Agent Skills.
- Checks for conflicts, stale paths, risky commands, metadata, context size,
  package-manager drift, duplication, and verification guidance.
- Text, JSON, and SARIF output.
- Path-scope explanation for common coding-agent tools.
- Zero-runtime-dependency Python CLI and CI workflow.

[Unreleased]: https://github.com/Neohu-ceo/instructlint/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/Neohu-ceo/instructlint/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Neohu-ceo/instructlint/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Neohu-ceo/instructlint/releases/tag/v0.1.0
