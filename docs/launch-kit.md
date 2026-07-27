# Launch kit

## Repository metadata

Description:

> Lint the instructions that guide your coding agents. Find conflicts, stale
> paths, unsafe commands, scope errors, and context bloat across AGENTS.md,
> CLAUDE.md, Cursor, Copilot, and skills.

Topics:

`agents-md`, `ai-agents`, `claude-code`, `codex`, `copilot`, `cursor`,
`developer-tools`, `linter`, `local-first`, `sarif`

## Version 0.1.0 release

Title:

> InstructLint 0.1.0 — static analysis for agent instructions

Body:

> Coding agents are only as coherent as the instructions we feed them.
> InstructLint is a local, deterministic CLI that finds contradictions, stale
> paths, dangerous commands, missing scope metadata, package-manager drift, and
> context bloat across the major repository instruction formats.
>
> It has zero runtime dependencies, emits text/JSON/SARIF, and includes an
> `explain` command for path scope. This alpha release is looking for real-world
> fixtures and false-positive reports.

## Announcement: English

> I built InstructLint because my repositories had AGENTS.md, CLAUDE.md, Cursor
> rules, Copilot instructions, and skills—but no way to tell when they disagreed.
>
> It is a zero-dependency, local CLI that treats agent instructions like code:
> conflicts, stale references, unsafe commands, scope metadata, duplicate rules,
> and SARIF for CI.
>
> The first release is intentionally small. I would value examples of instruction
> failures from real repositories more than feature requests without fixtures.
> [repository link]

## Announcement: 中文

> 我做了一个开源小工具 InstructLint：把 AI 编程 Agent 的指令文件当代码检查。
>
> 它可以同时扫描 AGENTS.md、CLAUDE.md、Cursor/Copilot 规则和 Skills，发现互相
> 矛盾的要求、失效路径、危险命令、作用域遗漏、包管理器漂移和上下文膨胀。
> 完全本地运行、零运行时依赖，也能输出 JSON/SARIF 接入 CI。
>
> 0.1.0 最需要的不是泛泛的功能建议，而是真实仓库里出现过的错误样例。
> [repository link]

## Ethical distribution plan

1. Publish the release and pin one demo issue containing copy-paste installation.
2. Submit to relevant launch communities only where self-promotion is allowed,
   clearly disclosing authorship.
3. Open useful integrations or documentation pull requests only when they solve
   an upstream problem; never post promotional comments on unrelated issues.
4. Respond to every reproducible false positive with a fixture and release note.
5. Share measurable improvements—precision, rule coverage, CI time—not vanity
   claims.

## First 30 days

- Week 1: collect ten public fixture repositories and label false positives.
- Week 2: publish 0.1.1 with compatibility fixes and a reusable GitHub Action.
- Week 3: write a data-backed “agent instruction failure modes” report.
- Week 4: invite maintainers of adjacent tools to review interoperability docs.

Track unique installers, issue-to-fix time, returning contributors, and release
adoption. Stars are an outcome, not the product metric.
