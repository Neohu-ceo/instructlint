from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

from .discovery import discover_instruction_files
from .frontmatter import parse_frontmatter
from .models import InstructionFile


@dataclass(frozen=True)
class Match:
    path: str
    kind: str
    applies: bool
    reason: str


TOOL_KINDS = {
    "all": None,
    "codex": {"agents", "agent", "skill"},
    "claude": {"claude", "skill"},
    "cursor": {"cursor", "agents", "agent"},
    "copilot": {"copilot", "agents"},
    "gemini": {"gemini", "agents", "agent"},
    "windsurf": {"windsurf", "agents", "agent"},
}


def _expand_braces(pattern: str) -> list[str]:
    match = re.search(r"\{([^{}]+)\}", pattern)
    if not match:
        return [pattern]
    values = match.group(1).split(",")
    return [
        candidate
        for value in values
        for candidate in _expand_braces(
            pattern[: match.start()] + value.strip() + pattern[match.end() :]
        )
    ]


def _patterns(metadata: dict) -> list[str]:
    for key in ("applyTo", "globs", "paths"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item) for item in value if str(item)]
    return []


def _glob_matches(target: str, pattern: str) -> bool:
    return any(
        fnmatch.fnmatchcase(target, expanded) or Path(target).match(expanded)
        for expanded in _expand_braces(pattern)
    )


def _ancestor_applies(instruction: InstructionFile, target: str) -> bool:
    parent = Path(instruction.relative_path).parent.as_posix()
    return parent == "." or target == parent or target.startswith(f"{parent}/")


def explain_target(
    root: str | Path, target: str | Path, tool: str = "all"
) -> list[Match]:
    root_path = Path(root).expanduser().resolve()
    target_path = Path(target)
    if target_path.is_absolute():
        try:
            target_relative = target_path.resolve().relative_to(root_path).as_posix()
        except ValueError:
            target_relative = target_path.as_posix()
    else:
        target_relative = target_path.as_posix().lstrip("./")

    allowed = TOOL_KINDS[tool]
    matches: list[Match] = []
    for instruction in discover_instruction_files(root_path):
        if allowed is not None and instruction.kind not in allowed:
            continue
        metadata, _, _, error = parse_frontmatter(instruction.text)
        if error:
            matches.append(
                Match(
                    instruction.relative_path,
                    instruction.kind,
                    False,
                    "invalid frontmatter",
                )
            )
            continue
        patterns = _patterns(metadata)
        if patterns:
            applies = any(
                _glob_matches(target_relative, pattern) for pattern in patterns
            )
            reason = (
                f"matches {', '.join(patterns)}"
                if applies
                else f"does not match {', '.join(patterns)}"
            )
        elif instruction.kind in {"agents", "agent", "claude", "gemini"}:
            applies = _ancestor_applies(instruction, target_relative)
            reason = "ancestor scope" if applies else "outside directory scope"
        elif metadata.get("alwaysApply") is True:
            applies, reason = True, "alwaysApply is true"
        elif instruction.kind == "skill":
            applies, reason = False, "skill loads on demand, not by file path"
        else:
            applies, reason = True, "repository-wide rule"
        matches.append(
            Match(instruction.relative_path, instruction.kind, applies, reason)
        )

    return sorted(
        matches,
        key=lambda item: (
            not item.applies,
            len(Path(item.path).parts),
            item.path,
        ),
    )
