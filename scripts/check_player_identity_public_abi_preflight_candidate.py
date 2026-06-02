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
import check_player_identity_identifier_redaction_evidence as identifier_redaction
import check_player_identity_principal_invalidation_policy as principal_invalidation


SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_MANIFEST = Path("docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json")
DEFAULT_PRIVATE_LAYOUT = Path("docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json")
DEFAULT_IDENTIFIER_REDACTION = Path("docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json")
DEFAULT_PRINCIPAL_INVALIDATION = Path(
    "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json"
)
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
REQUIRED_SDK_CONSUMER_CONTRACT = {
    "consumer checks struct_size before reading identity payload or descriptor fields",
    "consumer checks the captured capability bit before registering identity callbacks",
    "consumer requires nonzero plugin_owner_token before owner-token registration",
    "consumer treats callback payload storage as callback-local",
    "consumer treats principal handles as process-local and non-persistent",
    "consumer treats registration handles as process-local and non-persistent",
    "consumer uses owner-token unregister for every successful registration handle",
    "consumer does not use identity for lookup, permissions/admin, commands/replies, persistence, mutation, return override, or send-chat identity",
}
REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE = {
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "public_abi_ready",
    "v1_completion",
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
    parser.add_argument("--identifier-redaction-evidence", type=Path, default=DEFAULT_IDENTIFIER_REDACTION)
    parser.add_argument("--principal-invalidation-policy", type=Path, default=DEFAULT_PRINCIPAL_INVALIDATION)
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


def analyze_sdk_consumer_contract(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    contract = payload.get("sdk_consumer_contract")
    if contract is None:
        required_before_public_abi = string_set(payload, "required_before_public_abi")
        does_not_resolve = string_set(payload, "does_not_resolve")
        owner_token_lifecycle = string_set(payload, "required_owner_token_lifecycle")
        missing_inputs = {
            "required_before_public_abi": sorted({"sdk.consumer", "lifecycle.owner_cleanup"} - required_before_public_abi),
            "does_not_resolve": sorted({"sdk.consumer", "lifecycle.owner_cleanup", "v1_completion"} - does_not_resolve),
            "required_owner_token_lifecycle": sorted(REQUIRED_OWNER_TOKEN_LIFECYCLE - owner_token_lifecycle),
        }
        missing_inputs = {key: value for key, value in missing_inputs.items() if value}
        if missing_inputs:
            add(blockers, "sdk_consumer_contract_derived_inputs_missing", "$.sdk_consumer_contract", missing=missing_inputs)
        return (
            {
                "source": "derived_compatibility_stub",
                "status": "blocked",
                "candidate_only": True,
                "accepted_for_candidate_review": not blockers,
                "accepted_for_contract_review": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "v1_completion_evidence": False,
                "required_behavior": sorted(REQUIRED_SDK_CONSUMER_CONTRACT),
                "owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
                "does_not_resolve": sorted(REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE),
                "public_header_symbols_now": [],
                "public_capability_bits_now": [],
                "public_callback_abi_now": [],
            },
            blockers,
        )

    if not isinstance(contract, dict):
        add(blockers, "sdk_consumer_contract_not_object", "$.sdk_consumer_contract")
        contract = {}
    for key, expected in (("status", "blocked"),):
        if contract.get(key) != expected:
            add(blockers, f"sdk_consumer_contract_{key}_mismatch", f"$.sdk_consumer_contract.{key}", value=contract.get(key))
    if contract.get("candidate_only") is not True:
        add(blockers, "sdk_consumer_contract_candidate_only_not_true", "$.sdk_consumer_contract.candidate_only")
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
    ):
        if contract.get(key) is not False:
            add(blockers, f"sdk_consumer_contract_{key}_not_false", f"$.sdk_consumer_contract.{key}")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if contract.get(key, []) != []:
            add(blockers, f"sdk_consumer_contract_{key}_not_empty", f"$.sdk_consumer_contract.{key}")
    required_behavior = contract.get("required_behavior")
    if not isinstance(required_behavior, list) or not all(isinstance(item, str) for item in required_behavior):
        add(blockers, "sdk_consumer_contract_required_behavior_not_string_list", "$.sdk_consumer_contract.required_behavior")
        required_behavior_set = set()
    else:
        required_behavior_set = set(required_behavior)
    missing_behavior = sorted(REQUIRED_SDK_CONSUMER_CONTRACT - required_behavior_set)
    if missing_behavior:
        add(
            blockers,
            "sdk_consumer_contract_required_behavior_missing",
            "$.sdk_consumer_contract.required_behavior",
            missing=missing_behavior,
        )
    does_not_resolve = contract.get("does_not_resolve")
    if not isinstance(does_not_resolve, list) or not all(isinstance(item, str) for item in does_not_resolve):
        add(blockers, "sdk_consumer_contract_does_not_resolve_not_string_list", "$.sdk_consumer_contract.does_not_resolve")
        does_not_resolve_set = set()
    else:
        does_not_resolve_set = set(does_not_resolve)
    missing_non_resolutions = sorted(REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE - does_not_resolve_set)
    if missing_non_resolutions:
        add(
            blockers,
            "sdk_consumer_contract_does_not_resolve_missing",
            "$.sdk_consumer_contract.does_not_resolve",
            missing=missing_non_resolutions,
        )
    return (
        {
            "source": "manifest",
            "status": contract.get("status"),
            "candidate_only": contract.get("candidate_only") is True,
            "accepted_for_candidate_review": not blockers,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "required_behavior": contract.get("required_behavior", []),
            "owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
            "does_not_resolve": contract.get("does_not_resolve", []),
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
        },
        blockers,
    )


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
    _sdk_report, sdk_blockers = analyze_sdk_consumer_contract(payload)
    blockers.extend(sdk_blockers)

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


def validate_claimed_contract_review_inputs(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    redaction_report: dict[str, Any],
    principal_report: dict[str, Any],
    private_layout_report: dict[str, Any],
) -> None:
    accepted = payload.get("contract_review_inputs_accepted")
    if not isinstance(accepted, dict):
        return
    checks = (
        (
            "privacy.identifier_redaction",
            redaction_report.get("accepted_for_contract_review") is True,
            redaction_report.get("blockers", []),
        ),
        (
            "lifetime.generation_scope_invalidation.candidate_policy",
            principal_report.get("ready") is True,
            principal_report.get("blockers", []),
        ),
        (
            "abi.public_pod_contract.private_layout_candidate",
            private_layout_report.get("accepted_for_contract_review") is True,
            private_layout_report.get("blockers", []),
        ),
    )
    for key, accepted_now, input_blockers in checks:
        if accepted.get(key) is True and not accepted_now:
            add(
                blockers,
                "claimed_contract_review_input_not_accepted",
                f"$.contract_review_inputs_accepted.{key}",
                input=key,
                input_blockers=input_blockers,
            )


def build_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    header_scan: dict[str, Any],
    private_layout_report: dict[str, Any],
    redaction_report: dict[str, Any],
    principal_report: dict[str, Any],
) -> dict[str, Any]:
    sdk_consumer_contract, _sdk_blockers = analyze_sdk_consumer_contract(payload)
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
        "required_capability_policy": payload.get("required_capability_policy", []),
        "required_owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
        "sdk_consumer_contract": sdk_consumer_contract,
        "event_payload": payload.get("event_payload", {}),
        "descriptor": payload.get("descriptor", {}),
        "private_pod_layout_candidate": {
            "accepted_for_contract_review": private_layout_report.get("accepted_for_contract_review") is True,
            "blockers": private_layout_report.get("blockers", []),
        },
        "identifier_redaction_evidence": {
            "accepted_for_contract_review": redaction_report.get("accepted_for_contract_review") is True,
            "blockers": redaction_report.get("blockers", []),
        },
        "principal_invalidation_policy": {
            "ready": principal_report.get("ready") is True,
            "candidate_only": principal_report.get("candidate_only") is True,
            "blockers": principal_report.get("blockers", []),
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
            add(
                blockers,
                "private_pod_layout_candidate_not_accepted",
                "--private-pod-layout-candidate",
                input_blockers=private_report["blockers"],
            )
    try:
        redaction_payload = identifier_redaction.load_evidence(args.identifier_redaction_evidence)
        redaction_blockers = identifier_redaction.validate_evidence(redaction_payload)
        redaction_report = identifier_redaction.build_report(redaction_payload, redaction_blockers)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        redaction_report = {"accepted_for_contract_review": False, "blockers": ["identifier_redaction_evidence_unreadable"]}
        add(blockers, "identifier_redaction_evidence_unreadable", "--identifier-redaction-evidence", error=str(exc))
    else:
        if redaction_blockers:
            add(
                blockers,
                "identifier_redaction_evidence_not_accepted",
                "--identifier-redaction-evidence",
                input_blockers=redaction_report["blockers"],
            )
    try:
        principal_payload = principal_invalidation.load_json(args.principal_invalidation_policy)
        principal_validation = principal_invalidation.validate_manifest(principal_payload, check_mode="consume")
        principal_report = principal_invalidation.build_report(
            principal_payload,
            principal_validation,
            check_mode="consume",
        )
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        principal_report = {"ready": False, "candidate_only": False, "blockers": ["principal_invalidation_policy_unreadable"]}
        add(blockers, "principal_invalidation_policy_unreadable", "--principal-invalidation-policy", error=str(exc))
    else:
        if principal_validation.blockers:
            add(
                blockers,
                "principal_invalidation_policy_not_accepted",
                "--principal-invalidation-policy",
                input_blockers=principal_report["blockers"],
            )
    header_scan = scan_public_header(args.public_header, blockers)
    validate_manifest(payload, private_payload, blockers)
    validate_claimed_contract_review_inputs(
        payload,
        blockers,
        redaction_report=redaction_report,
        principal_report=principal_report,
        private_layout_report=private_report,
    )
    report = build_report(
        payload,
        blockers,
        header_scan=header_scan,
        private_layout_report=private_report,
        redaction_report=redaction_report,
        principal_report=principal_report,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("player identity public ABI preflight candidate: " + ("ok" if report["ready"] else "blocked"))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
