#!/usr/bin/env python3
"""Validate offline player identity identifier-redaction evidence.

This checker consumes sanitized snapshot manifests only. A passing report is evidence
for contract review, not public ABI readiness or player identity promotion.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.player-identity-identifier-redaction-evidence.v1"
REPORT_SCHEMA = "obelisk.player-identity-identifier-redaction-evidence-check.v1"
RESOLVED_INPUT = "privacy.identifier_redaction"
ALLOWED_FIELD_CLASSES = {
    "copied opaque principal",
    "recognition-only",
    "private-redacted",
    "forbidden",
}
REQUIRED_REDACTED_CLASSES = {"private-redacted", "forbidden"}
REQUIRED_FIELD_CLASSES = {
    "platform account ids",
    "player names",
    "tribe identifiers",
    "network addresses",
    "raw chat text used as identity",
    "controller/playerstate object references",
}
FORBIDDEN_RAW_KEYS = {
    "account_id",
    "address",
    "chat_text",
    "eos_id",
    "ip",
    "object_address",
    "player_data_id",
    "player_name",
    "raw",
    "raw_text",
    "raw_value",
    "steam_id",
    "steamid",
    "tribe_id",
    "unique_net_id",
    "value",
}
FORBIDDEN_RAW_PATTERNS = {
    "steam_id": re.compile(r"\b(?:7656119\d{10}|SteamID|steam_?id)\b", re.IGNORECASE),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ue_pointer": re.compile(r"\b0x[0-9a-f]{8,16}\b", re.IGNORECASE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        help="Sanitized identifier-redaction evidence manifest.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_evidence(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "--evidence")
    resolved = reject_protected_input_path(path, "--evidence")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("--evidence top-level JSON must be an object")
    return payload


def contains_raw_identifier(value: Any) -> list[str]:
    matches: list[str] = []
    if isinstance(value, str):
        for name, pattern in FORBIDDEN_RAW_PATTERNS.items():
            if pattern.search(value):
                matches.append(name)
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_RAW_KEYS:
                matches.append(f"raw_key:{key}")
            matches.extend(contains_raw_identifier(nested))
    if isinstance(value, list):
        for nested in value:
            matches.extend(contains_raw_identifier(nested))
    return sorted(set(matches))


def validate_field(field: Any, index: int, blockers: list[dict[str, Any]]) -> str | None:
    label = f"$.fields[{index}]"
    if not isinstance(field, dict):
        add(blockers, "field_not_object", label)
        return None
    field_name = field.get("name")
    if not isinstance(field_name, str) or not field_name:
        add(blockers, "field_name_missing", f"{label}.name")
    field_class = field.get("field_class")
    if not isinstance(field_class, str):
        add(blockers, "field_class_missing", f"{label}.field_class")
        return None
    if field_class not in ALLOWED_FIELD_CLASSES:
        add(blockers, "field_class_not_allowed", f"{label}.field_class", value=field_class)
    source_class = field.get("source_identifier_class")
    if not isinstance(source_class, str) or source_class not in REQUIRED_FIELD_CLASSES:
        add(blockers, "source_identifier_class_not_allowed", f"{label}.source_identifier_class", value=source_class)
    if field_class in REQUIRED_REDACTED_CLASSES:
        if field.get("redacted") is not True:
            add(blockers, "redacted_field_not_marked_redacted", f"{label}.redacted", field_class=field_class)
        if field.get("raw_value_present") is not False:
            add(blockers, "redacted_field_raw_value_present_not_false", f"{label}.raw_value_present", field_class=field_class)
    raw_matches = contains_raw_identifier(field)
    if raw_matches:
        add(blockers, "field_contains_raw_identifier_material", label, matches=raw_matches)
    return source_class if isinstance(source_class, str) else None


def validate_evidence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", expected=SCHEMA, observed=payload.get("schema"))
    if payload.get("surface") != "obelisk.player_identity.v1":
        add(blockers, "surface_mismatch", "$.surface")
    if payload.get("sanitized") is not True:
        add(blockers, "sanitized_not_true", "$.sanitized")
    if payload.get("source") == "live-server":
        add(blockers, "live_server_source_forbidden", "$.source")
    if payload.get("promotion_ready") is not False:
        add(blockers, "promotion_ready_not_false", "$.promotion_ready")
    if payload.get("public_sdk_ready") is not False:
        add(blockers, "public_sdk_ready_not_false", "$.public_sdk_ready")
    if payload.get("runtime_ready") is not False:
        add(blockers, "runtime_ready_not_false", "$.runtime_ready")
    if payload.get("public_header_allowed") is not False:
        add(blockers, "public_header_allowed_not_false", "$.public_header_allowed")

    fields = payload.get("fields")
    observed_classes: set[str] = set()
    if not isinstance(fields, list) or not fields:
        add(blockers, "fields_missing", "$.fields")
    else:
        for index, field in enumerate(fields):
            source_class = validate_field(field, index, blockers)
            if source_class:
                observed_classes.add(source_class)
    missing_classes = sorted(REQUIRED_FIELD_CLASSES - observed_classes)
    if missing_classes:
        add(blockers, "required_identifier_classes_missing", "$.fields", missing=missing_classes)

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        add(blockers, "policy_missing", "$.policy")
    else:
        if policy.get("default") != "no raw identity logging or persistence":
            add(blockers, "policy_default_mismatch", "$.policy.default")
        if policy.get("persistence_allowed") is not False:
            add(blockers, "policy_persistence_allowed_not_false", "$.policy.persistence_allowed")
        if policy.get("raw_identity_logging_allowed") is not False:
            add(blockers, "policy_raw_identity_logging_allowed_not_false", "$.policy.raw_identity_logging_allowed")

    raw_matches = contains_raw_identifier(payload.get("sample_logs", []))
    if raw_matches:
        add(blockers, "sample_logs_contain_raw_identifier_material", "$.sample_logs", matches=raw_matches)
    return blockers


def build_report(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "surface": payload.get("surface"),
        "ready": ready,
        "accepted_for_contract_review": ready,
        "resolved_inputs": [RESOLVED_INPUT] if ready else [],
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "remaining_blockers": [] if ready else [RESOLVED_INPUT],
        "next_blocker": "identity_public_contract_gate" if ready else "privacy_identifier_redaction_evidence_not_accepted",
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "identifier-redaction evidence does not add public header symbols",
            "identifier-redaction evidence does not promote obelisk.player_identity.v1",
            "identifier-redaction evidence does not authorize runtime, public SDK, lookup, persistence, permissions/admin, command response, or commands/replies",
        ],
    }


def main() -> int:
    args = parse_args()
    payload = load_evidence(args.evidence)
    blockers = validate_evidence(payload)
    report = build_report(payload, blockers)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ready={str(report['ready']).lower()}")
        print(f"next_blocker={report['next_blocker']}")
        if blockers:
            print("blockers=" + ",".join(report["blockers"]))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
