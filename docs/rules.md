# Rule reference

Diagnostic codes are stable within a major version. Errors fail the default CLI
exit policy; warnings and info findings can be promoted with `--fail-on`.

| Code | Severity | Meaning |
| --- | --- | --- |
| `CTX000` | warning | No supported instruction file was found |
| `CTX001` | warning | One instruction file exceeds the context-size threshold |
| `CTX002` | warning | An instruction file is empty |
| `FS001` | error | An instruction symlink has no target |
| `FMT001` | error | Rule frontmatter is malformed or unsupported |
| `SCP001` | warning | A path-specific Copilot file has no `applyTo` |
| `SCP002` | warning | A Cursor rule has no activation metadata |
| `SCP003` | warning | A Copilot custom agent has no required `description` |
| `DNG001` | error | An instruction approves recursive forced deletion |
| `DNG002` | error | An instruction approves `git reset --hard` |
| `DNG003` | error | An instruction approves destructive `git clean` |
| `DNG004` | error | An instruction approves world-writable permissions |
| `DNG005` | error | An instruction pipes an unverified download into a shell |
| `REF001` | warning | A repository-relative path does not exist |
| `REF002` | warning | An instruction contains an absolute filesystem path |
| `CNF001` | error | Positive and negative rules describe the same action |
| `DUP001` | info | A normative rule is copied across multiple files |
| `PKG001` | warning | Multiple JavaScript lockfile families exist at the root |
| `PKG002` | warning | A command disagrees with the root lockfile |
| `PKG003` | warning | Multiple package managers are named without a lockfile |
| `VAL001` | info | Root guidance does not name a verification command |

## Severity philosophy

An error describes a direct safety or consistency failure. A warning describes a
high-confidence portability or maintenance problem. An info diagnostic is a
prompt for maintainers and does not imply that a repository is broken.

InstructLint avoids generic prose scoring. Every finding must point to a location
and offer a concrete remediation.
