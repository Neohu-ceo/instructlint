from __future__ import annotations

import fnmatch
import os
import re
from collections import defaultdict
from pathlib import Path

from .discovery import IGNORED_DIRECTORIES, discover_instruction_files
from .frontmatter import parse_frontmatter
from .models import Diagnostic, InstructionFile, ScanResult

DANGEROUS_PATTERNS = (
    (
        "DNG001",
        re.compile(r"\brm\s+-[^\n]*r[^\n]*f\b", re.IGNORECASE),
        "recursive forced deletion",
    ),
    (
        "DNG002",
        re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        "destructive Git reset",
    ),
    (
        "DNG003",
        re.compile(r"\bgit\s+clean\s+-[a-z]*f[a-z]*\b", re.IGNORECASE),
        "destructive Git clean",
    ),
    (
        "DNG004",
        re.compile(r"\bchmod\s+(?:-R\s+)?777\b", re.IGNORECASE),
        "world-writable permissions",
    ),
    (
        "DNG005",
        re.compile(
            r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:ba)?sh\b", re.IGNORECASE
        ),
        "unverified remote script execution",
    ),
)

NEGATION_PREFIX = re.compile(
    r"(?:never|do\s+not|don['’]t|must\s+not|禁止|不得|不要|切勿).{0,24}$",
    re.IGNORECASE,
)

POSITIVE_RULE = re.compile(
    r"\b(?:always|must|shall|required\s+to)\b\s*[:,-]?\s*(.+)$",
    re.IGNORECASE,
)
NEGATIVE_RULE = re.compile(
    r"\b(?:never|do\s+not|don['’]t|must\s+not|shall\s+not|avoid)\b\s*[:,-]?\s*(.+)$",
    re.IGNORECASE,
)
CHINESE_POSITIVE_RULE = re.compile(r"(?:必须|总是|务必)[：:，,]?\s*(.+)$")
CHINESE_NEGATIVE_RULE = re.compile(r"(?:禁止|不得|不要|避免|切勿)[：:，,]?\s*(.+)$")

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
AT_REFERENCE = re.compile(r"(?<![\w@])@([A-Za-z0-9_.\-/]+)")
CODE_PATH = re.compile(r"`([^`\s]+)`")

PACKAGE_COMMANDS = {
    "npm": re.compile(r"\bnpm\s+[A-Za-z][\w-]*\b"),
    "pnpm": re.compile(r"\bpnpm\s+[A-Za-z][\w-]*\b"),
    "yarn": re.compile(r"\byarn(?:\s+[A-Za-z][\w-]*)?\b(?=\s|$|[),;])"),
    "bun": re.compile(r"\bbun\s+[A-Za-z][\w-]*\b"),
}

LOCKFILES = {
    "package-lock.json": "npm",
    "npm-shrinkwrap.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
    "bun.lock": "bun",
    "bun.lockb": "bun",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "please",
    "the",
    "to",
    "when",
    "with",
}


def _diagnostic(
    code: str,
    severity: str,
    message: str,
    instruction: InstructionFile,
    line: int = 1,
    hint: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        path=instruction.relative_path,
        line=max(1, line),
        hint=hint,
    )


def _iter_lines(text: str):
    yield from enumerate(text.splitlines(), start=1)


def _iter_nonfenced_lines(text: str):
    in_fence = False
    for number, line in _iter_lines(text):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield number, line


def _normalise_rule(value: str) -> str:
    value = re.sub(r"[`*_~#.:;,!?()[\]{}\"'，。；：！？（）]", " ", value.lower())
    words = [word for word in value.split() if word not in STOPWORDS]
    return " ".join(words)


def _similar(left: str, right: str) -> bool:
    if not left or not right:
        return False
    if min(len(left), len(right)) < 10:
        return False
    if left == right or (
        min(len(left), len(right)) >= 12 and (left in right or right in left)
    ):
        return True
    left_words, right_words = set(left.split()), set(right.split())
    union = left_words | right_words
    return bool(union) and len(left_words & right_words) / len(union) >= 0.72


def _extract_normative_rules(instruction: InstructionFile):
    rules: list[tuple[str, str, int, str]] = []
    for line_number, raw_line in _iter_nonfenced_lines(instruction.text):
        line = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", raw_line).strip()
        if not line:
            continue
        match = NEGATIVE_RULE.search(line) or CHINESE_NEGATIVE_RULE.search(line)
        if match:
            normalised = _normalise_rule(match.group(1))
            if normalised:
                rules.append(("negative", normalised, line_number, line))
            continue
        match = POSITIVE_RULE.search(line) or CHINESE_POSITIVE_RULE.search(line)
        if match:
            normalised = _normalise_rule(match.group(1))
            if normalised:
                rules.append(("positive", normalised, line_number, line))
    return rules


def _is_path_candidate(value: str) -> bool:
    value = value.strip().split("#", 1)[0]
    if not value or value.startswith(("http://", "https://", "mailto:", "#")):
        return False
    if any(character in value for character in "*?{}<>|"):
        return False
    if value.startswith(("$", "--")) or "://" in value:
        return False
    if re.fullmatch(r"/[A-Za-z0-9_-]+", value):
        return False
    if re.fullmatch(r"\.[A-Za-z0-9]+", value) and value in {
        ".js",
        ".jsx",
        ".py",
        ".rs",
        ".ts",
        ".tsx",
    }:
        return False
    if value in LOCKFILES:
        return False
    if "/" in value:
        first_segment = value.lstrip("./~").split("/", 1)[0]
        if "." in first_segment and not value.startswith((".", "/", "~")):
            return False
    return (
        "/" in value
        or value.startswith(".")
        or value.endswith(
            (
                ".md",
                ".mdc",
                ".json",
                ".toml",
                ".yaml",
                ".yml",
                ".py",
                ".js",
                ".jsx",
                ".ts",
                ".tsx",
                ".go",
                ".rs",
                ".sh",
            )
        )
    )


def _references(line: str, include_code_paths: bool = True):
    seen: set[str] = set()
    prose = re.sub(r"`[^`]*`", "", line)
    for pattern in (MARKDOWN_LINK, AT_REFERENCE):
        for match in pattern.finditer(prose):
            value = match.group(1).strip().strip("'\"").rstrip(".,;:")
            if pattern is AT_REFERENCE and not (
                value.startswith((".", "/"))
                or value.endswith(
                    (
                        ".md",
                        ".mdc",
                        ".json",
                        ".toml",
                        ".yaml",
                        ".yml",
                        ".py",
                        ".js",
                        ".jsx",
                        ".ts",
                        ".tsx",
                    )
                )
            ):
                continue
            if value not in seen and _is_path_candidate(value):
                seen.add(value)
                yield value
    if include_code_paths:
        for match in CODE_PATH.finditer(line):
            value = match.group(1).strip().strip("'\"").rstrip(".,;:")
            if value not in seen and _is_path_candidate(value):
                seen.add(value)
                yield value


def _load_gitignore_patterns(root: Path) -> list[str]:
    path = root / ".gitignore"
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [
        line.strip().lstrip("/")
        for line in lines
        if line.strip()
        and not line.lstrip().startswith(("#", "!"))
        and not line.startswith("\\#")
    ]


def _matches_ignored_path(path: str, patterns: list[str]) -> bool:
    for raw_pattern in patterns:
        pattern = raw_pattern.rstrip("/")
        if (
            fnmatch.fnmatchcase(path, pattern)
            or Path(path).match(pattern)
            or path.startswith(f"{pattern}/")
        ):
            return True
    return False


def _path_index(root: Path) -> set[str]:
    paths: set[str] = set()
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        directory_names[:] = [
            name for name in directory_names if name not in IGNORED_DIRECTORIES
        ]
        current_path = Path(current)
        for name in directory_names:
            paths.add((current_path / name).relative_to(root).as_posix())
        for name in file_names:
            paths.add((current_path / name).relative_to(root).as_posix())
    return paths


def _reference_exists(
    root: Path,
    instruction: InstructionFile,
    reference: str,
    indexed_paths: set[str],
    gitignore_patterns: list[str],
) -> bool:
    clean = reference.split("#", 1)[0].rstrip("/").replace("\\", "/")
    if not clean:
        return True
    path = Path(clean)
    if path.is_absolute():
        return path.exists()
    if (root / path).exists() or (instruction.path.parent / path).exists():
        return True
    if _matches_ignored_path(clean, gitignore_patterns):
        return True
    return any(
        candidate == clean or candidate.endswith(f"/{clean}")
        for candidate in indexed_paths
    )


def _check_file(
    root: Path,
    instruction: InstructionFile,
    max_bytes: int,
    indexed_paths: set[str],
    gitignore_patterns: list[str],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if instruction.broken_symlink:
        return [
            _diagnostic(
                "FS001",
                "error",
                "instruction file is a broken symbolic link",
                instruction,
                hint="Restore its target or replace the link with a valid instruction file.",
            )
        ]

    encoded_size = len(instruction.text.encode("utf-8"))
    line_count = len(instruction.text.splitlines())
    if not instruction.text.strip():
        diagnostics.append(
            _diagnostic(
                "CTX002",
                "warning",
                "instruction file is empty",
                instruction,
                hint="Delete it or add only the guidance this scope needs.",
            )
        )
    if encoded_size > max_bytes or line_count > 240:
        diagnostics.append(
            _diagnostic(
                "CTX001",
                "warning",
                f"instruction context is large ({encoded_size} bytes, {line_count} lines)",
                instruction,
                hint="Move reference material into linked docs and keep high-impact rules here.",
            )
        )

    metadata, _, _, frontmatter_error = parse_frontmatter(instruction.text)
    if frontmatter_error:
        diagnostics.append(
            _diagnostic(
                "FMT001",
                "error",
                frontmatter_error,
                instruction,
                hint="Use simple key/value or list frontmatter enclosed by --- lines.",
            )
        )
    elif instruction.kind == "copilot" and instruction.relative_path.startswith(
        ".github/instructions/"
    ):
        if not metadata.get("applyTo"):
            diagnostics.append(
                _diagnostic(
                    "SCP001",
                    "warning",
                    "path-specific Copilot instruction has no applyTo glob",
                    instruction,
                    hint='Add frontmatter such as applyTo: "**/*.ts".',
                )
            )
    elif instruction.kind == "copilot-agent" and not metadata.get("description"):
        diagnostics.append(
            _diagnostic(
                "SCP003",
                "warning",
                "Copilot custom agent has no required description",
                instruction,
                hint='Add YAML frontmatter such as description: "Reviews API changes".',
            )
        )
    elif instruction.kind == "claude-agent":
        missing_fields = [
            field for field in ("name", "description") if not metadata.get(field)
        ]
        if missing_fields:
            diagnostics.append(
                _diagnostic(
                    "SCP004",
                    "warning",
                    "Claude subagent is missing required frontmatter: "
                    + ", ".join(missing_fields),
                    instruction,
                    hint="Add YAML frontmatter with a unique name and clear description.",
                )
            )
    elif (
        instruction.kind == "cursor"
        and instruction.relative_path.startswith(".cursor/rules/")
        and not any(
            metadata.get(key) for key in ("alwaysApply", "globs", "description")
        )
    ):
        diagnostics.append(
            _diagnostic(
                "SCP002",
                "warning",
                "Cursor rule has no activation metadata",
                instruction,
                hint="Set alwaysApply, globs, or a description in frontmatter.",
            )
        )

    active_heading = ""
    for line_number, line in _iter_lines(instruction.text):
        if line.lstrip().startswith("#"):
            active_heading = line.lstrip("#").strip()
        for code, pattern, description in DANGEROUS_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            prefix = line[: match.start()]
            if NEGATION_PREFIX.search(prefix) or re.search(
                r"\b(?:block(?:ed|s|ing)?|forbid(?:den)?|prohibit(?:ed)?|dangerous)\b|"
                r"(?:阻止|禁止|危险)",
                active_heading,
                re.IGNORECASE,
            ):
                continue
            diagnostics.append(
                _diagnostic(
                    code,
                    "error",
                    f"instruction permits {description}",
                    instruction,
                    line_number,
                    "Replace it with a scoped, recoverable command and explicit safety checks.",
                )
            )

    for line_number, line in _iter_nonfenced_lines(instruction.text):
        for reference in _references(
            line,
            include_code_paths=instruction.kind != "skill",
        ):
            if reference.startswith("~"):
                continue
            if reference.startswith("/"):
                diagnostics.append(
                    _diagnostic(
                        "REF002",
                        "warning",
                        f"machine-specific path reference: {reference}",
                        instruction,
                        line_number,
                        "Use a repository-relative path so the rule works for every contributor.",
                    )
                )
            elif not _reference_exists(
                root,
                instruction,
                reference,
                indexed_paths,
                gitignore_patterns,
            ):
                diagnostics.append(
                    _diagnostic(
                        "REF001",
                        "warning",
                        f"path reference does not exist: {reference}",
                        instruction,
                        line_number,
                        "Fix the path or remove the stale instruction.",
                    )
                )
    return diagnostics


def _check_conflicts(files: list[InstructionFile]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    rules = [
        (instruction, polarity, normalised, line, original)
        for instruction in files
        if not instruction.broken_symlink
        for polarity, normalised, line, original in _extract_normative_rules(
            instruction
        )
    ]
    emitted: set[tuple[str, int, str, int]] = set()
    for index, left in enumerate(rules):
        for right in rules[index + 1 :]:
            left_file, left_polarity, left_rule, left_line, _ = left
            right_file, right_polarity, right_rule, right_line, _ = right
            if left_polarity == right_polarity or not _similar(left_rule, right_rule):
                continue
            key = (
                left_file.relative_path,
                left_line,
                right_file.relative_path,
                right_line,
            )
            if key in emitted:
                continue
            emitted.add(key)
            diagnostics.append(
                _diagnostic(
                    "CNF001",
                    "error",
                    (
                        "contradicts "
                        f"{right_file.relative_path}:{right_line} about “{left_rule}”"
                    ),
                    left_file,
                    left_line,
                    "Keep one scoped source of truth or state explicit precedence.",
                )
            )
    return diagnostics


def _check_duplicates(files: list[InstructionFile]) -> list[Diagnostic]:
    occurrences: dict[str, list[tuple[InstructionFile, int]]] = defaultdict(list)
    for instruction in files:
        if instruction.broken_symlink:
            continue
        for polarity, normalised, line, _ in _extract_normative_rules(instruction):
            if len(normalised) >= 12:
                occurrences[f"{polarity}:{normalised}"].append((instruction, line))

    diagnostics: list[Diagnostic] = []
    for locations in occurrences.values():
        resolved_targets = {str(item.path.resolve()) for item, _ in locations}
        distinct_paths = {item.relative_path for item, _ in locations}
        if len(distinct_paths) < 2 or len(resolved_targets) < 2:
            continue
        first_file, first_line = locations[0]
        others = ", ".join(
            f"{item.relative_path}:{line}" for item, line in locations[1:3]
        )
        diagnostics.append(
            _diagnostic(
                "DUP001",
                "info",
                f"rule is duplicated in {others}",
                first_file,
                first_line,
                "Link or import a canonical rule to prevent future drift.",
            )
        )
    return diagnostics


def _check_package_managers(
    root: Path, files: list[InstructionFile]
) -> list[Diagnostic]:
    lock_managers = {
        manager for filename, manager in LOCKFILES.items() if (root / filename).exists()
    }
    usages: list[tuple[str, InstructionFile, int]] = []
    for instruction in files:
        if instruction.kind == "skill":
            # Skills commonly describe paths and package managers in the
            # repository where they will run, not in the skill's own repository.
            continue
        for line_number, line in _iter_lines(instruction.text):
            plain_line = re.sub(r"[*_`~]", "", line)
            line_matches = {
                manager: pattern.search(plain_line)
                for manager, pattern in PACKAGE_COMMANDS.items()
            }
            present = {manager for manager, match in line_matches.items() if match}
            if len(lock_managers) == 1 and next(iter(lock_managers)) in present:
                # A line that names the canonical manager alongside alternatives
                # is usually compatibility documentation, not conflicting advice.
                continue
            for manager, match in line_matches.items():
                if match:
                    context = plain_line[max(0, match.start() - 32) : match.end() + 64]
                    if re.search(
                        r"(?:do\s+not|don['’]t|never|must\s+not|not\b(?:\W+\w+){0,3}|"
                        r"禁止|不得|不要).{0,32}$",
                        plain_line[max(0, match.start() - 48) : match.start()],
                        re.IGNORECASE,
                    ) or re.search(
                        r"(?:do\s+not|don['’]t|never|must\s+not|not\s+run|"
                        r"禁止|不得|不要)",
                        context[match.end() - max(0, match.start() - 32) :],
                        re.IGNORECASE,
                    ):
                        continue
                    usages.append((manager, instruction, line_number))

    diagnostics: list[Diagnostic] = []
    if len(lock_managers) > 1:
        diagnostics.append(
            Diagnostic(
                code="PKG001",
                severity="warning",
                message=f"multiple JavaScript lockfile families found: {', '.join(sorted(lock_managers))}",
                hint="Keep one canonical lockfile or document why multiple package roots exist.",
            )
        )
    if len(lock_managers) == 1:
        canonical = next(iter(lock_managers))
        emitted: set[tuple[str, str]] = set()
        for manager, instruction, line_number in usages:
            key = (manager, instruction.relative_path)
            if manager != canonical and key not in emitted:
                emitted.add(key)
                diagnostics.append(
                    _diagnostic(
                        "PKG002",
                        "warning",
                        f"instruction uses {manager}, but the root lockfile selects {canonical}",
                        instruction,
                        line_number,
                        f"Use {canonical} commands or document a scoped exception.",
                    )
                )
    elif not lock_managers and len({manager for manager, _, _ in usages}) > 1:
        for manager, instruction, line_number in usages[1:]:
            diagnostics.append(
                _diagnostic(
                    "PKG003",
                    "warning",
                    f"mixed package-manager instructions include {manager} without a lockfile",
                    instruction,
                    line_number,
                    "Choose a canonical package manager and commit its lockfile.",
                )
            )
            break
    return diagnostics


def _check_verification(files: list[InstructionFile]) -> list[Diagnostic]:
    root_guides = [
        item
        for item in files
        if "/" not in item.relative_path
        and item.kind in {"agents", "agent", "claude", "gemini"}
    ]
    if not root_guides:
        return []
    combined = "\n".join(item.text for item in root_guides)
    has_verification = re.search(
        r"(?:\bpytest\b|\bgo\s+test\b|\bcargo\s+test\b|\bnpm\s+test\b|"
        r"\bpnpm\s+test\b|\byarn\s+test\b|\bbun\s+test\b|\bmake\s+(?:test|check)\b|"
        r"\b(?:lint|typecheck|test|测试|验证|检查)\b)",
        combined,
        re.IGNORECASE,
    )
    if has_verification:
        return []
    return [
        _diagnostic(
            "VAL001",
            "info",
            "root guidance does not name a verification command",
            root_guides[0],
            hint="Tell agents exactly how to test or check their changes.",
        )
    ]


def scan_repository(root: str | Path, max_bytes: int = 12_000) -> ScanResult:
    root_path = Path(root).expanduser().resolve()
    files = discover_instruction_files(root_path)
    indexed_paths = _path_index(root_path)
    gitignore_patterns = _load_gitignore_patterns(root_path)
    result = ScanResult(root=root_path, files=files)
    if not files:
        result.diagnostics.append(
            Diagnostic(
                code="CTX000",
                severity="warning",
                message="no supported agent instruction files found",
                hint="Add a concise AGENTS.md with commands, boundaries, and verification steps.",
            )
        )
        return result

    for instruction in files:
        result.diagnostics.extend(
            _check_file(
                root_path,
                instruction,
                max_bytes,
                indexed_paths,
                gitignore_patterns,
            )
        )
    result.diagnostics.extend(_check_conflicts(files))
    result.diagnostics.extend(_check_duplicates(files))
    result.diagnostics.extend(_check_package_managers(root_path, files))
    result.diagnostics.extend(_check_verification(files))
    return result
