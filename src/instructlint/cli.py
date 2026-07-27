from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .engine import scan_repository
from .explain import TOOL_KINDS, explain_target
from .models import SEVERITY_ORDER, ScanResult
from .sarif import to_sarif

SYMBOLS = {"error": "✗", "warning": "!", "info": "·"}


def _print_text(result: ScanResult) -> None:
    counts = result.counts()
    print(f"InstructLint {__version__} — {len(result.files)} instruction file(s)")
    for diagnostic in result.sorted_diagnostics():
        symbol = SYMBOLS.get(diagnostic.severity, "-")
        print(
            f"{symbol} {diagnostic.severity.upper():7} {diagnostic.code} "
            f"{diagnostic.path}:{diagnostic.line}  {diagnostic.message}"
        )
        if diagnostic.hint:
            print(f"  ↳ {diagnostic.hint}")
    print(
        f"\n{counts['error']} error(s), {counts['warning']} warning(s), "
        f"{counts['info']} info"
    )


def _exit_code(result: ScanResult, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = SEVERITY_ORDER[fail_on]
    return int(
        any(
            SEVERITY_ORDER.get(item.severity, 99) <= threshold
            for item in result.diagnostics
        )
    )


def _scan(args: argparse.Namespace) -> int:
    result = scan_repository(args.path, max_bytes=args.max_bytes)
    if args.format == "json":
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif args.format == "sarif":
        print(json.dumps(to_sarif(result), ensure_ascii=False, indent=2))
    else:
        _print_text(result)
    return _exit_code(result, args.fail_on)


def _explain(args: argparse.Namespace) -> int:
    root = Path(args.path).expanduser().resolve()
    matches = explain_target(root, args.target, args.tool)
    print(f"Instruction scope for {args.target} ({args.tool})")
    if not matches:
        print("  No supported instruction files found.")
        return 0
    for match in matches:
        symbol = "✓" if match.applies else "–"
        state = "applies" if match.applies else "skipped"
        print(f"{symbol} {match.path} [{match.kind}] — {state}: {match.reason}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="instructlint",
        description="Lint cross-agent repository instructions before agents consume them.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="scan instruction files")
    scan_parser.add_argument("path", nargs="?", default=".")
    scan_parser.add_argument(
        "--format", choices=("text", "json", "sarif"), default="text"
    )
    scan_parser.add_argument(
        "--fail-on",
        choices=("error", "warning", "info", "none"),
        default="error",
        help="minimum severity that returns exit code 1 (default: error)",
    )
    scan_parser.add_argument(
        "--max-bytes",
        type=int,
        default=12_000,
        help="warn when one instruction file exceeds this size",
    )
    scan_parser.set_defaults(handler=_scan)

    explain_parser = subparsers.add_parser(
        "explain", help="show which rules can affect one target file"
    )
    explain_parser.add_argument("target")
    explain_parser.add_argument("--path", default=".", help="repository root")
    explain_parser.add_argument("--tool", choices=tuple(TOOL_KINDS), default="all")
    explain_parser.set_defaults(handler=_explain)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        args = parser.parse_args(["scan", *(argv or [])])
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
