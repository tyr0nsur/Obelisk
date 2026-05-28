#!/usr/bin/env python3
"""Summarize gated runtime observer evidence from copied Obelisk logs.

The analyzer is intentionally passive. It reads sanitized or copied logs and turns
module observer lines into structured evidence that can be compared across chat,
inventory, structures, or future reflected modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
LOG_PREFIX = r"(?:\[[^\]]+\]\s+)*"
SAFE_DETAIL_KEYS = {
    "chat": {
        "ServerSendChatMessage": {"send_mode", "send_mode_name", "send_mode_known"},
    },
}
PROMOTION_ONLY_BLOCKERS = {"runtime_observer_evidence_only"}


GATE_RE = re.compile(
    LOG_PREFIX
    + r"Experimental (?P<module>[A-Za-z0-9_]+) reflection enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{64})\.?"
)
PROCESS_EVENT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) ProcessEvent #(?P<sequence>\d+) "
    r"function=(?P<function>\S+) fname_index=(?P<fname_index>-?\d+)"
    r"(?: outer_fname_index=(?P<outer_fname_index>-?\d+))?"
    r"(?: params=(?P<params>0x[0-9a-fA-F]+))? "
    r"fields=(?P<field_count>\d+)"
    r"(?: metadata_only=(?P<metadata_only>true|false))?"
)
FIELD_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) field (?P<field>\S+) "
    r"offset=(?P<offset>0x[0-9a-fA-F]+) size=(?P<size>\d+) (?P<rest>.*)"
)
REJECT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected (?P<module>[A-Za-z0-9_]+) rejected #(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+)"
    r"(?: function=(?P<function>\S+))? reason=(?P<reason>.+)"
)
DETAIL_RE = re.compile(
    LOG_PREFIX + r"Reflected (?P<module>[A-Za-z0-9_]+) (?P<function>\S+) (?P<rest>.+)"
)
KEY_VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\S+)")
RUNTIME_LOADED_RE = re.compile(LOG_PREFIX + r"Obelisk Runtime Loaded Native \(LD_PRELOAD\)")
PROCESS_EVENT_CANDIDATES_RE = re.compile(
    LOG_PREFIX + r"ProcessEvent vtable-derived pattern candidates found: (?P<count>\d+)"
)
PROCESS_EVENT_CANDIDATE_RE = re.compile(
    LOG_PREFIX + r"ProcessEvent candidate\[(?P<index>\d+)\] = (?P<address>0x[0-9a-fA-F]+)"
)
PROCESS_EVENT_FOUND_RE = re.compile(
    LOG_PREFIX + r"Found ProcessEvent at address: (?P<address>0x[0-9a-fA-F]+)"
)
PROCESS_EVENT_HOOK_INSTALLED_RE = re.compile(
    LOG_PREFIX
    + r"ProcessEvent absolute x64 hook installed successfully\. "
    r"patch_size=(?P<patch_size>\d+) trampoline=(?P<trampoline>0x[0-9a-fA-F]+)"
)
REFLECTION_SCANNER_DISABLED_RE = re.compile(
    LOG_PREFIX + r"ReflectionScanner disabled\. Set OBELISK_ENABLE_REFLECTION_SCANNER=1 .*"
)
PLUGINS_DISABLED_RE = re.compile(
    LOG_PREFIX + r"Plugin loading disabled by OBELISK_DISABLE_PLUGINS=1\."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


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
        "redacted_detail_keys": Counter(),
        "malformed_observer_lines": 0,
    }


def runtime_record() -> dict[str, Any]:
    return {
        "loaded_native_ld_preload": False,
        "process_event_candidate_count": None,
        "process_event_candidates": [],
        "process_event_address": None,
        "process_event_hook_installed": False,
        "process_event_hook_patch_size": None,
        "reflection_scanner_disabled": False,
        "plugins_disabled": False,
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


def module_blockers(record: dict[str, Any]) -> list[str]:
    blockers = ["runtime_observer_evidence_only"]
    if len(record["gate_sha256"]) == 0:
        blockers.append("missing_experimental_gate")
    if len(record["gate_sha256"]) > 1:
        blockers.append("mixed_binary_sha256")
    if record["malformed_observer_lines"] > 0:
        blockers.append("malformed_observer_lines")
    if record["redacted_detail_keys"]:
        blockers.append("redacted_sensitive_or_unapproved_details")
    return blockers


def safe_detail_keys(module: str, function: str) -> set[str]:
    return SAFE_DETAIL_KEYS.get(module, {}).get(function, set())


def analyze_lines(lines: list[str]) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = defaultdict(module_record)
    runtime = runtime_record()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if RUNTIME_LOADED_RE.fullmatch(stripped):
            runtime["loaded_native_ld_preload"] = True
            continue

        if match := PROCESS_EVENT_CANDIDATES_RE.fullmatch(stripped):
            runtime["process_event_candidate_count"] = int(match.group("count"))
            continue

        if match := PROCESS_EVENT_CANDIDATE_RE.fullmatch(stripped):
            add_unique(
                runtime["process_event_candidates"],
                {
                    "index": int(match.group("index")),
                    "address": match.group("address").lower(),
                },
            )
            continue

        if match := PROCESS_EVENT_FOUND_RE.fullmatch(stripped):
            runtime["process_event_address"] = match.group("address").lower()
            continue

        if match := PROCESS_EVENT_HOOK_INSTALLED_RE.fullmatch(stripped):
            runtime["process_event_hook_installed"] = True
            runtime["process_event_hook_patch_size"] = int(match.group("patch_size"))
            continue

        if REFLECTION_SCANNER_DISABLED_RE.fullmatch(stripped):
            runtime["reflection_scanner_disabled"] = True
            continue

        if PLUGINS_DISABLED_RE.fullmatch(stripped):
            runtime["plugins_disabled"] = True
            continue

        if match := GATE_RE.fullmatch(stripped):
            module = match.group("module")
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := PROCESS_EVENT_RE.fullmatch(stripped):
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

        if match := FIELD_RE.fullmatch(stripped):
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

        if match := REJECT_RE.fullmatch(stripped):
            module = match.group("module")
            record = modules[module]
            record["rejected_count"] += 1
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := DETAIL_RE.fullmatch(stripped):
            module = match.group("module")
            function = match.group("function")
            if function in {"ProcessEvent", "field", "rejected"}:
                continue
            details = parse_key_values(match.group("rest"))
            if not details:
                continue
            functions = modules[module]["functions"]
            functions.setdefault(function, function_record())
            allowed_keys = safe_detail_keys(module, function)
            for key, raw_value in details.items():
                if key not in allowed_keys:
                    modules[module]["redacted_detail_keys"][key] += 1
                    continue
                add_unique(functions[function]["details"][key], int_or_text(raw_value))
            continue

        if "Reflected " in stripped or "Experimental " in stripped:
            match = re.search(r"(?:Reflected|Experimental) (?P<module>[A-Za-z0-9_]+)", stripped)
            module = match.group("module") if match else "unknown"
            modules[module]["malformed_observer_lines"] += 1

    normalized_modules: dict[str, Any] = {}
    for module, record in sorted(modules.items()):
        normalized_modules[module] = {
            "gate_sha256": sorted(record["gate_sha256"]),
            "accepted_count": record["accepted_count"],
            "metadata_only_count": record["metadata_only_count"],
            "rejected_count": record["rejected_count"],
            "evidence_status": "observational",
            "blockers": module_blockers(record),
            "functions": {
                name: normalize_function(function)
                for name, function in sorted(record["functions"].items())
            },
            "fields": {
                name: normalize_field(field)
                for name, field in sorted(record["fields"].items())
            },
            "reject_reasons": dict(sorted(record["reject_reasons"].items())),
            "redacted_detail_keys": dict(sorted(record["redacted_detail_keys"].items())),
            "malformed_observer_lines": record["malformed_observer_lines"],
        }

    return {
        "schema": "obelisk.runtime-observer-log-summary.v1",
        "review_scope": "runtime_observer_evidence_summary",
        "readiness_gate": "none",
        "runtime": runtime,
        "modules": normalized_modules,
        "promotion_gate": {
            "gate_type": "runtime_observer_observational_only",
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
    parser.add_argument(
        "--allow-server-path",
        action="store_true",
        help=(
            "Allow direct reads below /servidor/ark. Default refuses those paths so runtime "
            "observer analysis stays on copied or sanitized artifacts."
        ),
    )
    parser.add_argument(
        "--obelisk-commit",
        help="Optional Obelisk commit override recorded in the evidence metadata.",
    )
    parser.add_argument(
        "--fail-on-quality-blockers",
        action="store_true",
        help=(
            "Return non-zero when a module has blockers beyond runtime_observer_evidence_only, "
            "such as missing gates, mixed SHA values, malformed observer lines, or redacted details."
        ),
    )
    parser.add_argument("logs", nargs="+", type=Path, help="Copied/sanitized Obelisk log files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lines: list[str] = []
    sources: list[dict[str, Any]] = []

    for path in args.logs:
        resolved = path.resolve()
        if is_relative_to(resolved, SERVER_ROOT) and not args.allow_server_path:
            print(
                f"refusing to read live server path without --allow-server-path: {resolved}",
                file=sys.stderr,
            )
            return 2
        if not resolved.is_file():
            print(f"log does not exist: {resolved}", file=sys.stderr)
            return 2
        text = resolved.read_text(encoding="utf-8")
        sources.append(
            {
                "path": str(resolved),
                "sha256": sha256_file(resolved),
                "line_count": len(text.splitlines()),
            }
        )
        lines.extend(text.splitlines())

    result = analyze_lines(lines)
    result["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": args.obelisk_commit or git_commit(),
        "sources": sources,
        "server_paths_allowed": bool(args.allow_server_path),
    }
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

    if args.fail_on_quality_blockers:
        quality_blockers = []
        if not result["modules"]:
            quality_blockers.append("no_runtime_observer_evidence")
        for module, payload in result["modules"].items():
            blockers = set(payload["blockers"]) - PROMOTION_ONLY_BLOCKERS
            if blockers:
                quality_blockers.append(f"{module}: {', '.join(sorted(blockers))}")
        if quality_blockers:
            print(
                "runtime observer summary has quality blockers: "
                + "; ".join(quality_blockers),
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
