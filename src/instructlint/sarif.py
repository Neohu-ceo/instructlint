from __future__ import annotations

from .models import ScanResult


def to_sarif(result: ScanResult) -> dict:
    rules: dict[str, dict] = {}
    sarif_results: list[dict] = []
    level_map = {"error": "error", "warning": "warning", "info": "note"}

    for diagnostic in result.sorted_diagnostics():
        rules.setdefault(
            diagnostic.code,
            {
                "id": diagnostic.code,
                "name": diagnostic.code,
                "shortDescription": {"text": diagnostic.message},
                "help": {"text": diagnostic.hint or diagnostic.message},
            },
        )
        item = {
            "ruleId": diagnostic.code,
            "level": level_map.get(diagnostic.severity, "none"),
            "message": {"text": diagnostic.message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": diagnostic.path},
                        "region": {"startLine": diagnostic.line},
                    }
                }
            ],
        }
        if diagnostic.hint:
            item["properties"] = {"help": diagnostic.hint}
        sarif_results.append(item)

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "InstructLint",
                        "informationUri": "https://github.com/Neohu-ceo/instructlint",
                        "rules": list(rules.values()),
                    }
                },
                "results": sarif_results,
            }
        ],
    }
