#!/usr/bin/env python3
"""Validate candidate-only player identity public ABI preflight routing."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_private_pod_layout_candidate as private_layout


SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_MANIFEST = Path("docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json")
DEFAULT_PRIVATE_LAYOUT = Path("docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json")
DEFAULT_PUBLIC_HEADER = Path("include/obelisk/ObeliskApi.h")
REQUIRED_ACCEPTED_INPUTS = {
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation.candidate_policy",
    "abi.public_pod_contract.private_layout_candidate",
}
REQUIRED_BEFORE_PUBLIC_ABI = {
    "runtime.lifecycle_evidence",
    "lifetime.principal_scope",
    "lifetime.invalidation_events",
    "lifetime.reconnect_duplicate_stale_policy",
    "abi.public_pod_contract",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
REQUIRED_DOES_NOT_RESOLVE = {
    "runtime.lifecycle_evidence",
    "abi.public_pod_contract",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "v1_completion",
}
REQUIRED_CAPABILITY_POLICY = {
    "named player identity capability bit remains absent while blocked",
    "capability must be captured in the init-time API table before any future use",
    "missing capability fails closed",
    "later marker or env changes cannot widen a loaded plugin's captured capability",
}
REQUIRED_OWNER_TOKEN_LIFECYCLE = {
    "nonzero plugin_owner_token required",
    "opaque uint64 registration handle returned on success",
    "registration handles are process-local and non-persistent",
    "owner-token unregister required",
    "plugin init failure removes registrations",
    "plugin unload removes registrations and drains in-flight callbacks",
    "callback payload storage is valid only for the callback",
}
REQUIRED_NON_CLAIMS = {
    "candidate-only public ABI preflight for offline routing",
    "does not add public header symbols",
    "does not reserve final C symbol names",
    "does not add capability bits",
    "does not add callback ABI",
    "does not promote obelisk.player_identity.v1",
    "does not resolve runtime.lifecycle_evidence",
    "does not resolve abi.public_pod_contract, abi.layout, sdk.consumer, lifecycle.owner_cleanup, or v1_completion",
    "does not promote permissions/admin, command response, commands/replies, lookup, persistence, mutation, return override, or send-chat identity",
}
PUBLIC_HEADER_TOKEN_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net|player_?(?:handle|data|id)",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
HEADER_ALLOWLIST = {"OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--private-pod-layout-candidate", type=Path, default=DEFAULT_PRIVATE_LAYOUT)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def string_set(payload: dict[str, Any], key: str) -> set[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def field_names(layout: dict[str, Any]) -> list[str]:
    fields = layout.get("fields")
    if not isinstance(fields, list):
        return []
    return [str(field.get("name")) for field in fields if isinstance(field, dict)]


def strip_c_comments_and_strings(text: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"'}:
                output.append(" ")
                quote = char
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "code"
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "string":
            if char == "\\" and next_char:
                output.extend((" ", " "))
                index += 2
                continue
            if char == quote:
                output.append(" ")
                index += 1
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
    return "".join(output)


def scan_public_header(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        text = strip_c_comments_and_strings(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "public_header_unreadable", "--public-header", path=str(path), error=str(exc))
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in HEADER_ALLOWLIST or token in seen or not PUBLIC_HEADER_TOKEN_RE.search(token):
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    if detected:
        add(blockers, "public_header_identity_or_principal_symbols_detected", "--public-header", detected=detected)
    return {"path": str(path), "readable": True, "detected_player_identity_tokens": detected}


def validate_manifest(payload: dict[str, Any], private_payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", value=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", value=payload.get("surface"))
    for key, expected in (
        ("artifact_status", "candidate_only"),
        ("visibility", "planning_contract"),
        ("status", "blocked"),
    ):
        if payload.get(key) != expected:
            add(blockers, f"{key}_mismatch", f"$.{key}", value=payload.get(key))
    for key in ("candidate_only", "accepted_for_candidate_review"):
        if payload.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.{key}", value=payload.get(key))
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", value=payload.get(key))
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", value=payload.get(key))

    accepted = payload.get("contract_review_inputs_accepted")
    if not isinstance(accepted, dict):
        add(blockers, "contract_review_inputs_accepted_missing", "$.contract_review_inputs_accepted")
        accepted = {}
    for key in sorted(REQUIRED_ACCEPTED_INPUTS):
        if accepted.get(key) is not True:
            add(blockers, "contract_review_input_not_true", f"$.contract_review_inputs_accepted.{key}")

    for key, required in (
        ("required_before_public_abi", REQUIRED_BEFORE_PUBLIC_ABI),
        ("does_not_resolve", REQUIRED_DOES_NOT_RESOLVE),
        ("required_capability_policy", REQUIRED_CAPABILITY_POLICY),
        ("required_owner_token_lifecycle", REQUIRED_OWNER_TOKEN_LIFECYCLE),
        ("non_claims", REQUIRED_NON_CLAIMS),
    ):
        missing = sorted(required - string_set(payload, key))
        if missing:
            add(blockers, f"{key}_missing_required", f"$.{key}", missing=missing)

    event = payload.get("event_payload")
    descriptor = payload.get("descriptor")
    if not isinstance(event, dict):
        add(blockers, "event_payload_missing", "$.event_payload")
        event = {}
    if not isinstance(descriptor, dict):
        add(blockers, "descriptor_missing", "$.descriptor")
        descriptor = {}
    private_event = private_payload.get("event_payload_layout") if isinstance(private_payload, dict) else {}
    private_descriptor = private_payload.get("descriptor_layout") if isinstance(private_payload, dict) else {}
    if event.get("struct_size") != private_event.get("struct_size") or event.get("alignment") != private_event.get("alignment"):
        add(blockers, "event_payload_private_layout_mismatch", "$.event_payload")
    if event.get("fields") != field_names(private_event):
        add(blockers, "event_payload_fields_private_layout_mismatch", "$.event_payload.fields")
    if descriptor.get("struct_size") != private_descriptor.get("struct_size") or descriptor.get("alignment") != private_descriptor.get("alignment"):
        add(blockers, "descriptor_private_layout_mismatch", "$.descriptor")
    if descriptor.get("fields") != field_names(private_descriptor):
        add(blockers, "descriptor_fields_private_layout_mismatch", "$.descriptor.fields")


def build_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    header_scan: dict[str, Any],
    private_layout_report: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "ready": not blockers,
        "valid": not blockers,
        "status": payload.get("status"),
        "candidate_only": payload.get("candidate_only") is True,
        "accepted_for_candidate_review": payload.get("accepted_for_candidate_review") is True and not blockers,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "v1_completion_evidence": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "contract_review_inputs_accepted": payload.get("contract_review_inputs_accepted", {}),
        "required_before_public_abi": payload.get("required_before_public_abi", []),
        "does_not_resolve": payload.get("does_not_resolve", []),
        "event_payload": payload.get("event_payload", {}),
        "descriptor": payload.get("descriptor", {}),
        "private_pod_layout_candidate": {
            "accepted_for_contract_review": private_layout_report.get("accepted_for_contract_review") is True,
            "blockers": private_layout_report.get("blockers", []),
        },
        "public_header_scan": header_scan,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": payload.get("non_claims", []),
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    try:
        payload = load_json(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"--manifest invalid: {exc}") from exc
    try:
        private_payload = private_layout.load_json(args.private_pod_layout_candidate)
        private_contract = private_layout.load_json(private_layout.DEFAULT_PRIVATE_CONTRACT)
        private_blockers = private_layout.validate_manifest(private_payload, private_contract)
        private_report = private_layout.build_report(private_payload, private_blockers)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        private_payload = {}
        private_report = {"accepted_for_contract_review": False, "blockers": ["private_pod_layout_candidate_unreadable"]}
        add(blockers, "private_pod_layout_candidate_unreadable", "--private-pod-layout-candidate", error=str(exc))
    else:
        if private_blockers:
            add(blockers, "private_pod_layout_candidate_not_accepted", "--private-pod-layout-candidate", blockers=private_report["blockers"])
    header_scan = scan_public_header(args.public_header, blockers)
    validate_manifest(payload, private_payload, blockers)
    report = build_report(payload, blockers, header_scan=header_scan, private_layout_report=private_report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("player identity public ABI preflight candidate: " + ("ok" if report["ready"] else "blocked"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
