from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass(frozen=True)
class InstructionFile:
    path: Path
    relative_path: str
    kind: str
    text: str
    broken_symlink: bool = False


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str = "."
    line: int = 1
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass
class ScanResult:
    root: Path
    files: list[InstructionFile] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def sorted_diagnostics(self) -> list[Diagnostic]:
        return sorted(
            self.diagnostics,
            key=lambda item: (
                SEVERITY_ORDER.get(item.severity, 99),
                item.path,
                item.line,
                item.code,
            ),
        )

    def counts(self) -> dict[str, int]:
        counts = {"error": 0, "warning": 0, "info": 0}
        for diagnostic in self.diagnostics:
            counts[diagnostic.severity] = counts.get(diagnostic.severity, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "root": str(self.root),
            "instruction_files": [
                {"path": item.relative_path, "kind": item.kind} for item in self.files
            ],
            "diagnostics": [item.to_dict() for item in self.sorted_diagnostics()],
            "summary": {
                "files": len(self.files),
                **self.counts(),
            },
        }
