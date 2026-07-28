import fnmatch
import os
from pathlib import Path, PurePosixPath

from .models import InstructionFile

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}

ROOT_FILENAMES = {
    "AGENTS.md": "agents",
    "AGENT.md": "agent",
    "CLAUDE.md": "claude",
    "GEMINI.md": "gemini",
    ".cursorrules": "cursor",
    ".windsurfrules": "windsurf",
    ".clinerules": "cline",
}


def _contains_pair(parts: tuple[str, ...], first: str, second: str) -> bool:
    return any(
        parts[index : index + 2] == (first, second)
        for index in range(max(0, len(parts) - 1))
    )


def classify(relative_path: str) -> str | None:
    path = PurePosixPath(relative_path)
    parts = path.parts
    name = path.name

    if name in ROOT_FILENAMES:
        return ROOT_FILENAMES[name]
    if name == "SKILL.md":
        return "skill"
    if name == "copilot-instructions.md" and ".github" in parts:
        return "copilot"
    if _contains_pair(parts, ".github", "instructions") and (
        name.endswith(".instructions.md") or path.suffix == ".md"
    ):
        return "copilot"
    if (
        _contains_pair(parts, ".github", "agents")
        and path.suffix == ".md"
        and name.lower() != "readme.md"
    ):
        return "copilot-agent"
    if (
        _contains_pair(parts, ".claude", "agents")
        and path.suffix == ".md"
        and name.lower() != "readme.md"
    ):
        return "claude-agent"
    if _contains_pair(parts, ".cursor", "rules") and path.suffix in {".md", ".mdc"}:
        return "cursor"
    if _contains_pair(parts, ".windsurf", "rules") and path.suffix == ".md":
        return "windsurf"
    if ".clinerules" in parts and path.suffix == ".md":
        return "cline"
    if _contains_pair(parts, ".roo", "rules") and path.suffix == ".md":
        return "roo"
    if _contains_pair(parts, ".amazonq", "rules") and path.suffix == ".md":
        return "amazonq"
    if _contains_pair(parts, ".aiassistant", "rules") and path.suffix == ".md":
        return "jetbrains"
    return None


def _load_ignore_patterns(root: Path) -> list[str]:
    ignore_file = root / ".instructlintignore"
    if not ignore_file.is_file():
        return []
    try:
        lines = ignore_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [
        line.strip().lstrip("/")
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _is_ignored(relative_path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(relative_path, pattern) or Path(relative_path).match(
            pattern
        ):
            return True
        if pattern.endswith("/**") and relative_path.startswith(
            pattern[:-3].rstrip("/")
        ):
            return True
    return False


def discover_instruction_files(root: Path) -> list[InstructionFile]:
    root = root.resolve()
    discovered: list[InstructionFile] = []
    ignore_patterns = _load_ignore_patterns(root)

    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if name not in IGNORED_DIRECTORIES
            and not _is_ignored(
                (current_path / name).relative_to(root).as_posix(), ignore_patterns
            )
        )
        for file_name in sorted(file_names):
            path = current_path / file_name
            relative_path = path.relative_to(root).as_posix()
            if _is_ignored(relative_path, ignore_patterns):
                continue
            kind = classify(relative_path)
            if kind is None:
                continue
            if path.is_symlink() and not path.exists():
                discovered.append(
                    InstructionFile(
                        path=path,
                        relative_path=relative_path,
                        kind=kind,
                        text="",
                        broken_symlink=True,
                    )
                )
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            discovered.append(
                InstructionFile(
                    path=path,
                    relative_path=relative_path,
                    kind=kind,
                    text=text,
                )
            )
    return discovered
