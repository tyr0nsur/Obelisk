#!/usr/bin/env python3
"""Summarize gated runtime observer evidence from copied Obelisk logs.

The analyzer is intentionally passive. It reads sanitized or copied logs and turns
module observer lines into structured evidence that can be compared across chat,
inventory, structures, or future reflected modules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


GATE_RE = re.compile(
    r"Experimental (?P<module>[A-Za-z0-9_]+) reflection enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{16,64})"
)
PROCESS_EVENT_RE = re.compile(
    r"Reflected (?P<module>[A-Za-z0-9_]+) ProcessEvent #(?P<sequence>\d+) "
    r"function=(?P<function>\S+) fname_index=(?P<fname_index>-?\d+)"
    r"(?: outer_fname_index=(?P<outer_fname_index>-?\d+))?"
    r"(?: params=(?P<params>0x[0-9a-fA-F]+))? "
    r"fields=(?P<field_count>\d+)"
    r"(?: metadata_only=(?P<metadata_only>true|false))?"
)
FIELD_RE = re.compile(
    r"Reflected (?P<module>[A-Za-z0-9_]+) field (?P<field>\S+) "
    r"offset=(?P<offset>0x[0-9a-fA-F]+) size=(?P<size>\d+) (?P<rest>.*)"
)
REJECT_RE = re.compile(
    r"Reflected (?P<module>[A-Za-z0-9_]+) rejected #(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+)"
    r"(?: function=(?P<function>\S+))? reason=(?P<reason>.+)"
)
DETAIL_RE = re.compile(
    r"Reflected (?P<module>[A-Za-z0-9_]+) (?P<function>\S+) (?P<rest>.+)"
)
KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\S+)")


def bool_from_text(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def parse_key_values(text: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in KEY_VALUE_RE.finditer(text)}


def int_or_text(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def add_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def module_record() -> dict[str, Any]:
    return {
        "gate_sha256": [],
        "accepted_count": 0,
        "metadata_only_count": 0,
        "rejected_count": 0,
        "functions": {},
        "fields": {},
        "reject_reasons": {},
    }


def function_record() -> dict[str, Any]:
    return {
        "accepted": 0,
        "metadata_only": 0,
        "fname_indices": [],
        "outer_fname_indices": [],
        "field_counts": [],
        "details": defaultdict(list),
    }


def field_record() -> dict[str, Any]:
    return {
        "count": 0,
        "offsets": [],
        "sizes": [],
        "has_range": Counter(),
        "sensitive": Counter(),
    }


def normalize_function(record: dict[str, Any]) -> dict[str, Any]:
    details = {
        key: sorted(values, key=lambda item: str(item))
        for key, values in record["details"].items()
    }
    return {
        "accepted": record["accepted"],
        "metadata_only": record["metadata_only"],
        "fname_indices": sorted(record["fname_indices"]),
        "outer_fname_indices": sorted(record["outer_fname_indices"]),
        "field_counts": sorted(record["field_counts"]),
        "details": details,
    }


def normalize_field(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "count": record["count"],
        "offsets": sorted(record["offsets"]),
        "sizes": sorted(record["sizes"]),
        "has_range": dict(sorted(record["has_range"].items())),
        "sensitive": dict(sorted(record["sensitive"].items())),
    }


def analyze_lines(lines: list[str]) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = defaultdict(module_record)

    for line in lines:
        if match := GATE_RE.search(line):
            module = match.group("module")
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := PROCESS_EVENT_RE.search(line):
            module = match.group("module")
            function = match.group("function")
            record = modules[module]
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]

            metadata_only = bool_from_text(match.group("metadata_only"))
            if metadata_only:
                record["metadata_only_count"] += 1
                function_data["metadata_only"] += 1
            else:
                record["accepted_count"] += 1
                function_data["accepted"] += 1

            add_unique(function_data["fname_indices"], int(match.group("fname_index")))
            if match.group("outer_fname_index") is not None:
                add_unique(function_data["outer_fname_indices"], int(match.group("outer_fname_index")))
            add_unique(function_data["field_counts"], int(match.group("field_count")))
            continue

        if match := FIELD_RE.search(line):
            module = match.group("module")
            field = match.group("field")
            fields = modules[module]["fields"]
            fields.setdefault(field, field_record())
            field_data = fields[field]
            field_data["count"] += 1
            add_unique(field_data["offsets"], match.group("offset").lower())
            add_unique(field_data["sizes"], int(match.group("size")))

            extra = parse_key_values(match.group("rest"))
            if "has_range" in extra:
                field_data["has_range"][extra["has_range"]] += 1
            if "sensitive" in extra:
                field_data["sensitive"][extra["sensitive"]] += 1
            continue

        if match := REJECT_RE.search(line):
            module = match.group("module")
            record = modules[module]
            record["rejected_count"] += 1
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := DETAIL_RE.search(line):
            module = match.group("module")
            function = match.group("function")
            if function in {"ProcessEvent", "field", "rejected"}:
                continue
            details = parse_key_values(match.group("rest"))
            if not details:
                continue
            functions = modules[module]["functions"]
            functions.setdefault(function, function_record())
            for key, raw_value in details.items():
                add_unique(functions[function]["details"][key], int_or_text(raw_value))

    normalized_modules: dict[str, Any] = {}
    for module, record in sorted(modules.items()):
        normalized_modules[module] = {
            "gate_sha256": sorted(record["gate_sha256"]),
            "accepted_count": record["accepted_count"],
            "metadata_only_count": record["metadata_only_count"],
            "rejected_count": record["rejected_count"],
            "functions": {
                name: normalize_function(function)
                for name, function in sorted(record["functions"].items())
            },
            "fields": {
                name: normalize_field(field)
                for name, field in sorted(record["fields"].items())
            },
            "reject_reasons": dict(sorted(record["reject_reasons"].items())),
        }

    return {
        "modules": normalized_modules,
        "promotion_gate": {
            "ready": False,
            "blockers": [
                "runtime_observer_evidence_only",
                "requires_isolated_capture_or_second_source_for_promotion",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze copied Obelisk runtime observer log lines into JSON evidence."
    )
    parser.add_argument("logs", nargs="+", type=Path, help="Copied/sanitized Obelisk log files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lines: list[str] = []
    sources: list[str] = []

    for path in args.logs:
        if not path.is_file():
            print(f"log does not exist: {path}", file=sys.stderr)
            return 2
        sources.append(str(path))
        lines.extend(path.read_text(encoding="utf-8").splitlines())

    result = analyze_lines(lines)
    result["sources"] = sources
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
