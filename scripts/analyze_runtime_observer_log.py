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

import protected_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
LOG_PREFIX = r"(?:\[[^\]]+\]\s+)*"
SAFE_DETAIL_KEYS = {
    "chat": {
        "ServerSendChatMessage": {"send_mode", "send_mode_name", "send_mode_known"},
    },
    "player_principal_lifecycle": {
        "ShooterGameMode.HandleNewPlayer": {
            "copied_bool_fields",
            "copied_bool_values",
            "delivery_claim",
            "post_original",
            "principal_action",
            "principal_generation_logged",
            "principal_id_logged",
            "redacted_count",
            "redacted_fields",
            "role",
        },
        "ShooterGameMode.OnLogout": {
            "copied_bool_fields",
            "copied_bool_values",
            "delivery_claim",
            "post_original",
            "principal_action",
            "principal_generation_logged",
            "principal_id_logged",
            "redacted_count",
            "redacted_fields",
            "role",
        },
    },
    "item_return": {
        "AllowEquipItem": {"callbacks", "field_mask"},
        "CanRepair": {"callbacks", "field_mask"},
        "UseItemOntoItem": {"callbacks", "field_mask"},
    },
}
PROMOTION_ONLY_BLOCKERS = {"runtime_observer_evidence_only"}


GATE_RE = re.compile(
    LOG_PREFIX
    + r"Experimental (?P<module>[A-Za-z0-9_]+) reflection enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{64})\.?"
)
ITEM_RETURN_GATE_RE = re.compile(
    LOG_PREFIX
    + r"Experimental item return event producer enabled for ShooterGameServer "
    r"SHA256 (?P<sha256>[a-fA-F0-9]{64})\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_GATE_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleObserver enabled binary_sha256=(?P<sha256>[a-fA-F0-9]{64}) "
    r"target_set=(?P<target_set>players-lifecycle-anchor-candidates) "
    r"limit=(?P<limit>\d+) dispatch_limit=(?P<dispatch_limit>\d+) "
    r"delivery_claim=(?P<delivery_claim>[^.\s]+) principal_claim=(?P<principal_claim>[^.\s]+)\.?"
)
PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE = re.compile(
    LOG_PREFIX
    + r"PlayerPrincipalLifecycleObserver event sequence=(?P<sequence>\d+) "
    r"role=(?P<role>session_start|session_end|session_start_rejected) "
    r"target=(?P<target>ShooterGameMode\.(?:HandleNewPlayer|OnLogout)) "
    r"post_original=(?P<post_original>true|false) "
    r"copied_bool_fields=(?P<copied_bool_fields>\S*) "
    r"copied_bool_values=(?P<copied_bool_values>\S*) "
    r"redacted_count=(?P<redacted_count>\d+) "
    r"redacted_fields=(?P<redacted_fields>\S*) "
    r"principal_action=(?P<principal_action>candidate_created|candidate_invalidated|none) "
    r"principal_id_logged=(?P<principal_id_logged>true|false) "
    r"principal_generation_logged=(?P<principal_generation_logged>true|false) "
    r"delivery_claim=(?P<delivery_claim>[^.\s]+)\.?"
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
ITEM_RETURN_REJECT_RE = re.compile(
    LOG_PREFIX
    + r"Reflected item return rejected #(?P<sequence>\d+) "
    r"fname_index=(?P<fname_index>-?\d+) reason=(?P<reason>.+)"
)
ITEM_RETURN_DISPATCH_RE = re.compile(
    LOG_PREFIX
    + r"Reflected item return dispatched #(?P<sequence>\d+) "
    r"function=(?P<function>\S+) fname_index=(?P<fname_index>-?\d+) "
    r"callbacks=(?P<callbacks>\d+) field_mask=(?P<field_mask>\S+)"
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
    return protected_paths.is_under_path(path, parent)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


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


PLAYER_PRINCIPAL_FORBIDDEN_CSV_TOKENS = {
    "eosid",
    "fname_index",
    "fnames",
    "gobjects",
    "ipaddress",
    "playerdataid",
    "playerid",
    "playername",
    "raw_params",
    "raw_pointer",
    "resourcehandle",
    "steamid",
    "tribeid",
    "uobject_address",
    "uobjectpointer",
    "uniquenetid",
}


def csv_values(
    value: str,
    *,
    allowed: set[str] | None = None,
    allow_duplicates: bool = False,
) -> list[str] | None:
    if value == "":
        return []
    parts = value.split(",")
    if any(part == "" for part in parts):
        return None
    if not allow_duplicates and len(set(parts)) != len(parts):
        return None
    for part in parts:
        lowered = part.lower()
        if lowered in PLAYER_PRINCIPAL_FORBIDDEN_CSV_TOKENS:
            return None
        if allowed is not None and part not in allowed:
            return None
    return parts


def player_principal_lifecycle_gate_is_safe(match: re.Match[str]) -> bool:
    return (
        match.group("target_set") == "players-lifecycle-anchor-candidates"
        and match.group("dispatch_limit") == "0"
        and match.group("delivery_claim") == "none"
        and match.group("principal_claim") == "none"
    )


def player_principal_lifecycle_event_is_safe(match: re.Match[str]) -> bool:
    target = match.group("target")
    role = match.group("role")
    post_original = match.group("post_original")
    copied_bool_fields = csv_values(
        match.group("copied_bool_fields"),
        allowed={"bIsFromLogin", "ReturnValue"},
    )
    copied_bool_values = csv_values(
        match.group("copied_bool_values"),
        allowed={"0", "1"},
        allow_duplicates=True,
    )
    redacted_count = int(match.group("redacted_count"))
    redacted_fields = csv_values(
        match.group("redacted_fields"),
        allowed={"NewPlayer", "PlayerData", "PlayerCharacter", "Exiting"},
    )
    principal_action = match.group("principal_action")

    if (
        copied_bool_fields is None
        or copied_bool_values is None
        or redacted_fields is None
        or post_original != "true"
        or match.group("principal_id_logged") != "false"
        or match.group("principal_generation_logged") != "false"
        or match.group("delivery_claim") != "none"
    ):
        return False

    if target == "ShooterGameMode.HandleNewPlayer":
        if copied_bool_fields != ["bIsFromLogin", "ReturnValue"]:
            return False
        if len(copied_bool_values) != 2:
            return False
        if redacted_count != 3 or redacted_fields != ["NewPlayer", "PlayerData", "PlayerCharacter"]:
            return False
        is_from_login = copied_bool_values[0]
        return_value = copied_bool_values[1]
        if role == "session_start":
            return principal_action == "candidate_created" and copied_bool_values == ["1", "1"]
        if role == "session_start_rejected":
            return principal_action == "none" and (is_from_login == "0" or return_value == "0")
        return False

    if target == "ShooterGameMode.OnLogout":
        return (
            role == "session_end"
            and copied_bool_fields == []
            and copied_bool_values == []
            and redacted_count == 1
            and redacted_fields == ["Exiting"]
            and principal_action == "candidate_invalidated"
        )

    return False


def module_record() -> dict[str, Any]:
    return {
        "gate_sha256": [],
        "source_indices": [],
        "source_merge_explicit": False,
        "accepted_count": 0,
        "metadata_only_count": 0,
        "rejected_count": 0,
        "functions": {},
        "fields": {},
        "reject_reasons": {},
        "redacted_detail_keys": Counter(),
        "malformed_observer_lines": 0,
        "orphan_field_lines": 0,
        "out_of_order_field_lines": 0,
        "field_count_mismatches": 0,
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
        "fields": {},
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
        "fields": {
            name: normalize_field(field)
            for name, field in sorted(record["fields"].items())
        },
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
    if len(record["source_indices"]) > 1 and not record["source_merge_explicit"]:
        blockers.append("multiple_sources_same_module")
    if (
        record["accepted_count"] == 0
        and record["metadata_only_count"] == 0
        and record["rejected_count"] == 0
    ):
        blockers.append("no_accepted_or_rejected_observer_lines")
    if record["malformed_observer_lines"] > 0:
        blockers.append("malformed_observer_lines")
    if record["orphan_field_lines"] > 0:
        blockers.append("orphan_field_lines")
    if record["out_of_order_field_lines"] > 0:
        blockers.append("out_of_order_field_lines")
    if record["field_count_mismatches"] > 0:
        blockers.append("field_count_mismatch")
    if record["redacted_detail_keys"]:
        blockers.append("redacted_sensitive_or_unapproved_details")
    return blockers


def safe_detail_keys(module: str, function: str) -> set[str]:
    return SAFE_DETAIL_KEYS.get(module, {}).get(function, set())


def add_source_index(record: dict[str, Any], source_index: int) -> None:
    add_unique(record["source_indices"], source_index)


def observer_lines_from_sources(sources: list[list[str]]) -> list[tuple[int, str]]:
    return [
        (source_index, line)
        for source_index, lines in enumerate(sources)
        for line in lines
    ]


def analyze_lines(lines: list[str]) -> dict[str, Any]:
    return analyze_source_lines([lines])


def analyze_source_lines(sources: list[list[str]], *, source_merge_explicit: bool = False) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = defaultdict(module_record)
    runtime = runtime_record()
    active_fields_by_module: dict[tuple[int, str], dict[str, Any]] = {}

    def close_active_context(source_index: int, module: str) -> None:
        key = (source_index, module)
        active = active_fields_by_module.pop(key, None)
        if active and active["remaining"] != 0:
            modules[module]["field_count_mismatches"] += 1

    for source_index, line in observer_lines_from_sources(sources):
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
            close_active_context(source_index, module)
            add_source_index(modules[module], source_index)
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := ITEM_RETURN_GATE_RE.fullmatch(stripped):
            module = "item_return"
            close_active_context(source_index, module)
            add_source_index(modules[module], source_index)
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_unique(modules[module]["gate_sha256"], match.group("sha256").lower())
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_GATE_RE.fullmatch(stripped):
            module = "player_principal_lifecycle"
            close_active_context(source_index, module)
            record = modules[module]
            add_source_index(record, source_index)
            record["source_merge_explicit"] = source_merge_explicit
            if not player_principal_lifecycle_gate_is_safe(match):
                record["malformed_observer_lines"] += 1
                continue
            add_unique(record["gate_sha256"], match.group("sha256").lower())
            gate_function = "observer_gate"
            record["functions"].setdefault(gate_function, function_record())
            for key in ("target_set", "limit", "dispatch_limit", "delivery_claim", "principal_claim"):
                add_unique(record["functions"][gate_function]["details"][key], int_or_text(match.group(key)))
            continue

        if match := PLAYER_PRINCIPAL_LIFECYCLE_EVENT_RE.fullmatch(stripped):
            module = "player_principal_lifecycle"
            function = match.group("target")
            close_active_context(source_index, module)
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            if not player_principal_lifecycle_event_is_safe(match):
                record["malformed_observer_lines"] += 1
                continue
            record["accepted_count"] += 1
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]
            function_data["accepted"] += 1
            allowed_keys = safe_detail_keys(module, function)
            for key in (
                "role",
                "post_original",
                "copied_bool_fields",
                "copied_bool_values",
                "redacted_count",
                "redacted_fields",
                "principal_action",
                "principal_id_logged",
                "principal_generation_logged",
                "delivery_claim",
            ):
                raw_value = match.group(key)
                if key not in allowed_keys:
                    record["redacted_detail_keys"][key] += 1
                    continue
                add_unique(function_data["details"][key], int_or_text(raw_value))
            continue

        if match := PROCESS_EVENT_RE.fullmatch(stripped):
            module = match.group("module")
            function = match.group("function")
            close_active_context(source_index, module)
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
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
            field_count = int(match.group("field_count"))
            add_unique(function_data["field_counts"], field_count)
            if field_count > 0:
                active_fields_by_module[(source_index, module)] = {
                    "function": function,
                    "remaining": field_count,
                }
            continue

        if match := FIELD_RE.fullmatch(stripped):
            module = match.group("module")
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            field = match.group("field")
            fields = record["fields"]
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

            active_key = (source_index, module)
            active_context = active_fields_by_module.get(active_key)
            if not active_context:
                record["orphan_field_lines"] += 1
                continue

            if active_context["remaining"] <= 0:
                record["out_of_order_field_lines"] += 1
                active_fields_by_module.pop(active_key, None)
                continue

            active_function = active_context["function"]
            functions = record["functions"]
            functions.setdefault(active_function, function_record())
            function_fields = functions[active_function]["fields"]
            function_fields.setdefault(field, field_record())
            function_field_data = function_fields[field]
            function_field_data["count"] += 1
            add_unique(function_field_data["offsets"], match.group("offset").lower())
            add_unique(function_field_data["sizes"], int(match.group("size")))
            if "has_range" in extra:
                function_field_data["has_range"][extra["has_range"]] += 1
            if "sensitive" in extra:
                function_field_data["sensitive"][extra["sensitive"]] += 1

            active_context["remaining"] -= 1
            continue

        if match := REJECT_RE.fullmatch(stripped):
            module = match.group("module")
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            record["rejected_count"] += 1
            close_active_context(source_index, module)
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := ITEM_RETURN_REJECT_RE.fullmatch(stripped):
            module = "item_return"
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            record["rejected_count"] += 1
            close_active_context(source_index, module)
            reason = match.group("reason")
            record["reject_reasons"].setdefault(reason, 0)
            record["reject_reasons"][reason] += 1
            continue

        if match := ITEM_RETURN_DISPATCH_RE.fullmatch(stripped):
            module = "item_return"
            function = match.group("function")
            close_active_context(source_index, module)
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            record["accepted_count"] += 1
            functions = record["functions"]
            functions.setdefault(function, function_record())
            function_data = functions[function]
            function_data["accepted"] += 1
            add_unique(function_data["fname_indices"], int(match.group("fname_index")))
            for key in ("callbacks", "field_mask"):
                raw_value = match.group(key)
                if key not in safe_detail_keys(module, function):
                    record["redacted_detail_keys"][key] += 1
                    continue
                add_unique(function_data["details"][key], int_or_text(raw_value))
            continue

        if match := DETAIL_RE.fullmatch(stripped):
            module = match.group("module")
            function = match.group("function")
            if function in {"ProcessEvent", "field", "rejected"}:
                continue
            details = parse_key_values(match.group("rest"))
            if not details:
                continue
            record = modules[module]
            record["source_merge_explicit"] = source_merge_explicit
            add_source_index(record, source_index)
            functions = record["functions"]
            functions.setdefault(function, function_record())
            allowed_keys = safe_detail_keys(module, function)
            for key, raw_value in details.items():
                if key not in allowed_keys:
                    record["redacted_detail_keys"][key] += 1
                    continue
                add_unique(functions[function]["details"][key], int_or_text(raw_value))
            continue

        if "Reflected " in stripped or "Experimental " in stripped or "PlayerPrincipalLifecycleObserver " in stripped:
            match = re.search(r"(?:Reflected|Experimental) (?P<module>[A-Za-z0-9_]+)", stripped)
            module = "player_principal_lifecycle" if "PlayerPrincipalLifecycleObserver " in stripped else (match.group("module") if match else "unknown")
            modules[module]["source_merge_explicit"] = source_merge_explicit
            add_source_index(modules[module], source_index)
            modules[module]["malformed_observer_lines"] += 1

    for source_index, module in list(active_fields_by_module):
        close_active_context(source_index, module)

    normalized_modules: dict[str, Any] = {}
    for module, record in sorted(modules.items()):
        normalized_modules[module] = {
            "gate_sha256": sorted(record["gate_sha256"]),
            "source_indices": sorted(record["source_indices"]),
            "source_merge_explicit": record["source_merge_explicit"],
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
            "orphan_field_lines": record["orphan_field_lines"],
            "out_of_order_field_lines": record["out_of_order_field_lines"],
            "field_count_mismatches": record["field_count_mismatches"],
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
            "such as missing gates, mixed SHA values, multiple unmerged sources, field-count "
            "problems, malformed observer lines, or redacted details."
        ),
    )
    parser.add_argument(
        "--merge-module-sources",
        action="store_true",
        help=(
            "Allow the same observer module to be summarized across multiple copied logs. "
            "Without this flag, multi-source module summaries are quality blockers."
        ),
    )
    parser.add_argument("logs", nargs="+", type=Path, help="Copied/sanitized Obelisk log files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_lines: list[list[str]] = []
    sources: list[dict[str, Any]] = []

    for path in args.logs:
        expanded = path.expanduser()
        status = protected_paths.protected_path_status(
            expanded,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        resolved = status.resolved
        if status.protected and not args.allow_server_path:
            print(
                f"refusing to read live server path without --allow-server-path: {resolved}",
                file=sys.stderr,
            )
            return 2
        if not resolved.is_file():
            print(f"log does not exist: {resolved}", file=sys.stderr)
            return 2
        text = resolved.read_text(encoding="utf-8")
        lines = text.splitlines()
        sources.append(
            {
                "path": str(resolved),
                "sha256": sha256_file(resolved),
                "line_count": len(lines),
            }
        )
        source_lines.append(lines)

    result = analyze_source_lines(source_lines, source_merge_explicit=bool(args.merge_module_sources))
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
