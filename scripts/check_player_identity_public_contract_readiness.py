#!/usr/bin/env python3
"""Validate player identity public-contract review readiness.

This checker joins the approved runtime principal lifecycle evidence with the public
contract decision manifest. Acceptance means the runtime lifecycle blocker is ready for
contract review only; it does not promote public identity or open the SDK ABI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_evidence


DECISION_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-contract-readiness-check.v1"
SURFACE = "obelisk.player_identity.v1"
REQUIRED_INTAKE_ID = "approved_runtime_principal_lifecycle_evidence"
REQUIRED_RESOLVED_INPUT = "runtime.lifecycle_evidence"
REQUIRED_FORBIDDEN = {
    "UE pointers",
    "raw params",
    "FName/GObjects indices",
    "ResourceHandle",
    "pointer-derived identity",
    "lookup",
    "mutation",
    "return override",
}
REQUIRED_BLOCKERS = {
    "runtime.lifecycle_evidence",
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation",
    "abi.public_pod_contract",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
REQUIRED_TESTS_BEFORE_PUBLIC_HEADER = {
    "manifest.guardrails",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "identity.fail_closed",
    "privacy.redaction",
    "runtime.evidence_intake",
}
CONTRACT_REVIEW_INPUT_ONLY_TESTS = {
    "runtime.evidence_intake": {
        "scripts/check_player_identity_public_contract_readiness.py",
        "scripts/test_check_player_identity_public_contract_readiness.py",
        "scripts/test_player_identity_public_contract_decisions.py",
    },
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY = {
    "runtime evidence can prove a candidate lifecycle route was observed; it does not define a stable C ABI",
    "runtime evidence can show login/logout ordering; it does not choose the copied opaque identifier form, generation rules, or scope flags",
    "runtime evidence can support internal lifecycle semantics; it does not prove owner-token registration, unregister, plugin unload cleanup, or in-flight callback drain",
    "runtime evidence does not provide ABI layout tests, SDK consumer tests, or append-only compatibility rules",
    "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics",
    "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES = {
    "privacy and redaction decision resolved",
    "principal lifetime and invalidation decision resolved",
    "cross-instance/process-local scope decision resolved",
    "candidate POD payload and descriptor contract reviewed",
    "named capability and owner-token lifecycle policy reviewed",
    "ABI layout and SDK consumer tests passing",
    "public docs state exact non-claims and downstream dependency order",
}
REQUIRED_NON_CLAIMS = {
    "This manifest does not add public header symbols.",
    "This manifest does not promote obelisk.player_identity.v1.",
    "This manifest does not make approved runtime evidence sufficient by itself.",
    "This manifest does not expose player lookup.",
    "This manifest does not promote permissions/admin.",
    "This manifest does not promote command/chat response or commands/replies.",
    "This manifest does not authorize storage, persistence, cross-process identity, cluster-stable identity, mutation, return override, or send-chat identity.",
}
REQUIRED_TEST_COVERAGE_BY_ID = {
    "manifest.guardrails": {
        "decision gate remains blocked/planning until every blocker is resolved",
        "public_header_allowed remains false while unresolved blockers exist",
        "public_header_symbols_now remains empty",
        "approved runtime evidence is documented as necessary but insufficient",
        "non-claims forbid lookup, permissions/admin, command/chat response, persistence, mutation, and return override",
    },
    "abi.layout": {
        "POD layout size and alignment tests",
        "abi_version and struct_size validation",
        "append-only field offset tests",
        "old-plugin prefix compatibility or explicit major-version rejection",
    },
    "sdk.consumer": {
        "installed SDK consumer compiles against the promoted header",
        "consumer checks struct_size and capability before using identity fields",
        "consumer treats callback payload storage as callback-local",
        "consumer treats principal handles and registration handles as process-local and non-persistent",
    },
    "lifecycle.owner_cleanup": {
        "owner-token registration rejects missing or zero owner tokens",
        "unregister is owner-scoped",
        "init failure removes callbacks before dlclose",
        "plugin unload drains in-flight callbacks",
        "self-unregister from callback is safe",
        "callback exceptions do not cross the C ABI",
    },
    "identity.fail_closed": {
        "stale generation fails closed",
        "unsupported scope fails closed",
        "duplicate principal observation invalidates or quarantines according to policy",
        "reconnect creates a new generation unless continuity is proven",
        "lookup-by-public-handle remains unavailable",
        "cross-instance or cross-process handle reuse fails closed",
    },
    "privacy.redaction": {
        "raw identity-like fields are classified before copying",
        "platform ids, player names, tribe ids, network addresses, and object references are redacted",
        "logs contain only allowed sanitized reason flags and handle presence",
        "no persistence is possible through the identity ABI",
    },
    "runtime.evidence_intake": {
        "approved runtime evidence is checked as an input to promotion",
        "approved runtime evidence alone leaves the public-header gate closed",
        "approved runtime evidence cannot set promotion_ready, public_sdk_ready, runtime_ready, or public_header_allowed",
        "offline fixtures and second-source layout evidence remain separate from runtime lifecycle acceptance",
    },
}
REQUIRED_BEFORE_PUBLIC_HEADER = {
    "evidence.complete_non_protected_pack",
    "evidence.accepted_session_start_anchor",
    "evidence.accepted_session_end_anchor",
    "evidence.second_source_anchor_layout",
    "privacy.public_identifier_form",
    "privacy.redacted_identifier_fields",
    "privacy.logging_and_storage_policy",
    "lifetime.principal_scope",
    "lifetime.invalidation_events",
    "lifetime.reconnect_duplicate_stale_policy",
    "abi.payload_shape",
    "abi.capability_bits",
    "abi.owner_token_registration",
    "abi.append_only_layout_tests",
    "separation.no_commands_permissions_persistence",
}
REQUIRED_PUBLIC_IDENTIFIER_FORBIDDEN = {
    "SteamID",
    "EOS ID",
    "UniqueNetId",
    "PlayerDataID",
    "tribe ID",
    "player name",
    "IP address",
    "UE pointer",
    "FName/GObjects index",
    "ResourceHandle",
}
REQUIRED_PUBLIC_IDENTIFIER_PROPERTIES = {
    "process-local by default",
    "not persistent unless a future storage/ingress contract promotes persistence",
    "generation-bearing or otherwise invalidation-aware",
    "safe to copy across the C ABI as POD",
}
REQUIRED_REDACTION_CLASSES = {
    "copied opaque principal",
    "recognition-only",
    "private-redacted",
    "forbidden",
}
REQUIRED_REDACTED_FIELDS = {
    "platform account ids",
    "player names",
    "tribe identifiers",
    "network addresses",
    "raw chat text used as identity",
    "controller/playerstate object references",
}
REQUIRED_ALLOWED_SCOPES = {"callback-local", "process-local", "restart-local"}
REQUIRED_FORBIDDEN_SCOPES = {"cluster-stable", "persistent", "cross-map shared"}
REQUIRED_SCOPE_FIELDS = {"principal_handle", "principal_generation", "scope_flags"}
REQUIRED_INVALIDATION_EVENTS = {
    "disconnect",
    "logout",
    "transfer",
    "reconnect",
    "duplicate principal observation",
    "server restart",
    "stale controller/playerstate",
    "failed evidence validation",
}
REQUIRED_INVALIDATION_BEHAVIOR = {
    "stale principal fails closed",
    "permission decisions include generation or are callback-local only",
    "commands/replies reject stale principal handles",
}
REQUIRED_STALE_POLICY = {
    "new generation on reconnect unless evidence proves continuity",
    "duplicate observations invalidate or quarantine both principals",
    "stale handles never resolve to a different player",
    "lookup-by-public-handle remains unavailable unless separately promoted",
}
REQUIRED_ABI_PAYLOAD_SHAPE_PROPERTIES = {
    "POD C ABI",
    "append-only after promotion",
    "copied Obelisk-owned storage",
    "callback-local payload lifetime",
    "no UE pointers or raw params",
    "no platform account ids, player names, tribe ids, or network addresses",
    "no lookup, persistence, mutation, or return override",
}
REQUIRED_CAPABILITY_BEHAVIOR = {
    "capability is absent while this gate is blocked/planning",
    "capability is captured in the plugin init-time API table",
    "missing capability fails closed",
    "later env or marker changes cannot widen a loaded plugin's captured capability",
}
REQUIRED_OWNER_TOKEN_BEHAVIOR = {
    "nonzero plugin_owner_token required",
    "registration returns an opaque process-local handle",
    "unregister requires the same owner token",
    "registration handles are not persisted or shared across server processes",
    "init failure and plugin unload remove all owner registrations",
    "cleanup waits for in-flight callbacks except when policy explicitly permits same-callback self-unregister",
}
REQUIRED_ABI_LAYOUT_TESTS = {
    "POD layout size and alignment tests",
    "field offset and append-only compatibility tests",
    "struct_size short-write or rejection tests",
    "capability and owner-token fail-closed tests",
    "installed SDK consumer compile test",
    "callback lifecycle cleanup and drain tests",
}
REQUIRED_SEQUENCE_GATE = [
    "identity principal contract first",
    "permission query contract only after identity promotion",
    "command response contract only after permission result provenance is promoted",
    "commands/replies only after command response privacy, generation, and scope gates are promoted",
]
REQUIRED_SEPARATION_FORBIDDEN = {
    "permission query API",
    "permission cache API",
    "command response API",
    "command router",
    "replies/send-chat",
    "admin mutation",
    "storage/persistence",
    "operator ingress",
}
REQUIRED_CANDIDATE_PAYLOAD_FIELDS = {
    "abi_version",
    "struct_size",
    "event_kind",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "principal_state_flags",
    "invalidation_reason_flags",
    "event_sequence",
    "server_process_epoch",
    "reserved",
}
REQUIRED_CANDIDATE_DESCRIPTOR_FIELDS = {
    "abi_version",
    "struct_size",
    "supported_event_kind_mask",
    "supported_scope_flags",
    "supported_state_flags",
    "supported_invalidation_reason_flags",
    "contract_flags",
}
REQUIRED_CANDIDATE_PAYLOAD_PROPERTIES = {
    "POD C ABI only",
    "front-loaded abi_version and struct_size",
    "append-only fields after promotion",
    "copied Obelisk-owned storage",
    "no UE pointers",
    "no raw ProcessEvent params",
    "no FString or raw string ownership crossing the ABI",
    "no FName/GObjects indices",
    "no platform account ids",
    "no player names",
    "no tribe ids",
    "no network addresses",
    "no lookup handle",
    "principal handles are process-local and non-persistent",
    "no mutation or return override authority",
}
REQUIRED_CANDIDATE_OWNER_TOKEN_REQUIREMENTS = {
    "nonzero plugin_owner_token required",
    "event-kind mask required",
    "opaque uint64 registration handle returned on success",
    "registration handles are process-local and non-persistent",
    "owner-token unregister required",
    "plugin init failure removes registrations",
    "plugin unload removes registrations and drains in-flight callbacks",
    "callback payload storage is valid only for the callback",
}
REQUIRED_CANDIDATE_FAIL_CLOSED_POLICY = {
    "capability must be captured in the init-time API table",
    "missing capability fails closed",
    "missing or zero owner token fails closed",
    "later marker or env changes cannot widen a plugin's captured capability",
}
FORBIDDEN_CANDIDATE_FIELD_PATTERNS = {
    "lookup": re.compile(r"lookup", re.IGNORECASE),
    "resolve": re.compile(r"resolve", re.IGNORECASE),
    "get": re.compile(r"(?:^|[_\W])get(?:$|[_\W])|Get[A-Z_]", re.IGNORECASE),
    "raw_ue": re.compile(r"raw.*ue|ue.*raw", re.IGNORECASE),
    "private_identity": re.compile(r"private.*identity|identity.*private", re.IGNORECASE),
    "platform": re.compile(r"platform", re.IGNORECASE),
    "player_name": re.compile(r"player[_\s-]*names?", re.IGNORECASE),
    "tribe": re.compile(r"tribe", re.IGNORECASE),
    "ip": re.compile(r"\bIP\b|ip[_\s-]*address(?:es)?|network[_\s-]*address(?:es)?", re.IGNORECASE),
    "fname_gobjects": re.compile(r"FName|GObjects", re.IGNORECASE),
    "resource_handle": re.compile(r"ResourceHandle|resource[_\s-]*handle", re.IGNORECASE),
    "persistent": re.compile(r"persist(?:ent|ed|ence)?", re.IGNORECASE),
    "cluster": re.compile(r"cluster", re.IGNORECASE),
    "cross_process": re.compile(r"cross[_\s-]*process", re.IGNORECASE),
    "cross_map": re.compile(r"cross[_\s-]*map", re.IGNORECASE),
}
PUBLIC_CLAIM_KEYS = ("public_header_allowed", "promotion_ready", "public_sdk_ready", "runtime_ready")
PUBLIC_HEADER_IDENTITY_IDENTIFIER_RE = re.compile(
    r"identity|principal|steam_?id|steamid|player_?(?:id|handle|data_?id)|platform.*id|account.*id",
    re.IGNORECASE,
)
PUBLIC_HEADER_IDENTITY_IDENTIFIER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
}
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("docs/player_identity_public_contract_decisions.json"),
        help="Player identity public contract decision manifest.",
    )
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        required=True,
        help="Approved runtime principal lifecycle evidence manifest.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument(
        "--public-header",
        type=Path,
        default=Path("include/obelisk/ObeliskApi.h"),
        help="Public SDK header to scan for player identity/principal tokens.",
    )
    parser.add_argument("--promote", action="store_true", help="Fail closed for promotion checks.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public SDK readiness checks.")
    parser.add_argument("--runtime-readiness", action="store_true", help="Fail closed for runtime readiness checks.")
    return parser.parse_args()


def mode(args: argparse.Namespace) -> str:
    requested = [
        name
        for name, enabled in (
            ("promote", args.promote),
            ("public_readiness", args.public_readiness),
            ("runtime_readiness", args.runtime_readiness),
        )
        if enabled
    ]
    if len(requested) > 1:
        raise SystemExit("--promote, --public-readiness, and --runtime-readiness are mutually exclusive")
    return requested[0] if requested else "consume"


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: top-level JSON must be an object")
    return payload


def approved_runtime_report(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = approved_evidence.load_json(path)
    except (OSError, SystemExit) as exc:
        add(blockers, "approved_runtime_evidence_unreadable", "$.approved_runtime_evidence", error=str(exc))
        return {
            "ready": False,
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "remaining_blockers": ["approved_runtime_evidence_missing"],
        }

    validation = approved_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_evidence.build_report(payload, validation, check_mode="consume")
    if validation.blockers:
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "$.approved_runtime_evidence",
            reasons=[blocker["reason"] for blocker in validation.blockers],
        )
    else:
        if report.get("next_blocker") != "identity_public_contract_gate_missing":
            add(
                blockers,
                "approved_runtime_evidence_next_blocker_mismatch",
                "$.approved_runtime_evidence.next_blocker",
                value=report.get("next_blocker"),
            )
        if report.get("approved_runtime_evidence_present") is not True:
            add(
                blockers,
                "approved_runtime_evidence_presence_missing",
                "$.approved_runtime_evidence.approved_runtime_evidence_present",
            )
        if report.get("runtime_evidence_ready") is not True:
            add(
                blockers,
                "approved_runtime_evidence_runtime_ready_missing",
                "$.approved_runtime_evidence.runtime_evidence_ready",
            )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if key in report and report.get(key) is not False:
            add(blockers, f"approved_runtime_evidence_{key}_not_false", f"$.approved_runtime_evidence.{key}")
    return report


def string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value


def missing_required(observed: list[str] | None, required: set[str]) -> list[str]:
    return sorted(required - set(observed or []))


def forbidden_candidate_strings(values: list[str]) -> dict[str, list[str]]:
    observed: dict[str, list[str]] = {}
    for value in values:
        for token, pattern in FORBIDDEN_CANDIDATE_FIELD_PATTERNS.items():
            if pattern.search(value):
                observed.setdefault(token, []).append(value)
    return observed


def require_string_list_contains(
    item: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    reason: str,
    label: str,
) -> None:
    values = string_list(item.get(key))
    if values is None:
        add(blockers, f"{reason}_not_string_list", label)
        return
    missing = missing_required(values, required)
    if missing:
        add(blockers, reason, label, missing=missing)


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
            if char == "\n":
                output.append("\n")
                state = "code"
            else:
                output.append(" ")
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
                output.extend(("\n" if char == "\n" else " ", "\n" if next_char == "\n" else " "))
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


def public_header_identity_tokens(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = strip_c_comments_and_strings(text)
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in PUBLIC_HEADER_IDENTITY_IDENTIFIER_ALLOWLIST:
                continue
            if not PUBLIC_HEADER_IDENTITY_IDENTIFIER_RE.search(token):
                continue
            if token in seen:
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    return detected


def validate_public_header(decisions: dict[str, Any], path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        detected = public_header_identity_tokens(path)
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), error=str(exc))
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}

    if decisions.get("public_header_symbols_now") == [] and detected:
        add(
            blockers,
            "public_header_contains_unmanifested_player_identity_tokens",
            "$.public_header_symbols_now",
            path=str(path),
            detected_tokens=detected,
        )
    return {"path": str(path), "readable": True, "detected_player_identity_tokens": detected}


def validate_candidate_only_pod_abi(candidate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(candidate, dict):
        add(blockers, "candidate_public_pod_abi_missing", "$.proposed_public_pod_abi_candidate")
        return

    if candidate.get("status") != "proposal_only_not_public":
        add(blockers, "candidate_status_not_proposal_only", "$.proposed_public_pod_abi_candidate.status")
    if candidate.get("candidate_only") is not True:
        add(blockers, "candidate_only_not_true", "$.proposed_public_pod_abi_candidate.candidate_only")
    if candidate.get("public_header_allowed") is not False:
        add(blockers, "candidate_public_header_allowed_not_false", "$.proposed_public_pod_abi_candidate.public_header_allowed")
    for key in PUBLIC_CLAIM_KEYS:
        if key in candidate and candidate.get(key) is not False:
            add(blockers, f"candidate_{key}_claim_not_false", f"$.proposed_public_pod_abi_candidate.{key}")

    payload_properties = string_list(candidate.get("required_payload_properties"))
    if payload_properties is None:
        add(blockers, "candidate_required_payload_properties_not_string_list", "$.proposed_public_pod_abi_candidate.required_payload_properties")
    else:
        missing = missing_required(payload_properties, REQUIRED_CANDIDATE_PAYLOAD_PROPERTIES)
        if missing:
            add(
                blockers,
                "candidate_required_payload_properties_missing",
                "$.proposed_public_pod_abi_candidate.required_payload_properties",
                missing=missing,
            )

    event_fields = string_list(candidate.get("candidate_event_payload_fields_or_equivalent"))
    if event_fields is None:
        add(blockers, "candidate_event_payload_fields_not_string_list", "$.proposed_public_pod_abi_candidate.candidate_event_payload_fields_or_equivalent")
    else:
        missing = missing_required(event_fields, REQUIRED_CANDIDATE_PAYLOAD_FIELDS)
        if missing:
            add(
                blockers,
                "candidate_event_payload_fields_missing",
                "$.proposed_public_pod_abi_candidate.candidate_event_payload_fields_or_equivalent",
                missing=missing,
            )
        forbidden = forbidden_candidate_strings(event_fields)
        if forbidden:
            add(
                blockers,
                "candidate_event_payload_fields_forbidden_identity_or_lookup",
                "$.proposed_public_pod_abi_candidate.candidate_event_payload_fields_or_equivalent",
                forbidden=forbidden,
            )

    descriptor_fields = string_list(candidate.get("candidate_descriptor_fields_or_equivalent"))
    if descriptor_fields is None:
        add(blockers, "candidate_descriptor_fields_not_string_list", "$.proposed_public_pod_abi_candidate.candidate_descriptor_fields_or_equivalent")
    else:
        missing = missing_required(descriptor_fields, REQUIRED_CANDIDATE_DESCRIPTOR_FIELDS)
        if missing:
            add(
                blockers,
                "candidate_descriptor_fields_missing",
                "$.proposed_public_pod_abi_candidate.candidate_descriptor_fields_or_equivalent",
                missing=missing,
            )
        forbidden = forbidden_candidate_strings(descriptor_fields)
        if forbidden:
            add(
                blockers,
                "candidate_descriptor_fields_forbidden_identity_or_lookup",
                "$.proposed_public_pod_abi_candidate.candidate_descriptor_fields_or_equivalent",
                forbidden=forbidden,
            )

    registration = string_list(candidate.get("candidate_registration_shape_or_equivalent"))
    if registration is None:
        add(blockers, "candidate_registration_shape_not_string_list", "$.proposed_public_pod_abi_candidate.candidate_registration_shape_or_equivalent")
    else:
        missing = missing_required(registration, REQUIRED_CANDIDATE_OWNER_TOKEN_REQUIREMENTS)
        if missing:
            add(
                blockers,
                "candidate_owner_token_cleanup_requirements_missing",
                "$.proposed_public_pod_abi_candidate.candidate_registration_shape_or_equivalent",
                missing=missing,
            )

    capability_policy = string_list(candidate.get("candidate_capability_policy"))
    if capability_policy is None:
        add(blockers, "candidate_capability_policy_not_string_list", "$.proposed_public_pod_abi_candidate.candidate_capability_policy")
    else:
        missing = missing_required(capability_policy, REQUIRED_CANDIDATE_FAIL_CLOSED_POLICY)
        if missing:
            add(
                blockers,
                "candidate_fail_closed_policy_missing",
                "$.proposed_public_pod_abi_candidate.candidate_capability_policy",
                missing=missing,
            )


def validate_required_before_public_header(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    requirements = decisions.get("required_before_public_header")
    if not isinstance(requirements, list):
        add(blockers, "required_before_public_header_not_list", "$.required_before_public_header")
        return

    by_id: dict[str, dict[str, Any]] = {}
    observed_ids: set[Any] = set()
    for index, item in enumerate(requirements):
        if not isinstance(item, dict):
            add(blockers, "required_before_public_header_entry_not_object", f"$.required_before_public_header[{index}]")
            continue
        requirement_id = item.get("id")
        observed_ids.add(requirement_id)
        if isinstance(requirement_id, str):
            by_id[requirement_id] = item
        if item.get("status") == "resolved":
            add(blockers, "required_before_public_header_resolved_without_public_gate", f"$.required_before_public_header[{index}]", requirement_id=requirement_id)

    if observed_ids != REQUIRED_BEFORE_PUBLIC_HEADER:
        add(
            blockers,
            "required_before_public_header_mismatch",
            "$.required_before_public_header",
            expected=sorted(REQUIRED_BEFORE_PUBLIC_HEADER),
            observed=sorted(str(item) for item in observed_ids),
        )

    public_form = by_id.get("privacy.public_identifier_form")
    if public_form is not None:
        require_string_list_contains(
            public_form,
            "must_not_expose",
            REQUIRED_PUBLIC_IDENTIFIER_FORBIDDEN,
            blockers,
            "privacy_public_identifier_form_missing_forbidden_terms",
            "$.required_before_public_header[privacy.public_identifier_form].must_not_expose",
        )
        require_string_list_contains(
            public_form,
            "required_properties",
            REQUIRED_PUBLIC_IDENTIFIER_PROPERTIES,
            blockers,
            "privacy_public_identifier_form_missing_required_properties",
            "$.required_before_public_header[privacy.public_identifier_form].required_properties",
        )

    redaction = by_id.get("privacy.redacted_identifier_fields")
    if redaction is not None:
        require_string_list_contains(
            redaction,
            "allowed_field_classes",
            REQUIRED_REDACTION_CLASSES,
            blockers,
            "privacy_redacted_identifier_fields_missing_allowed_classes",
            "$.required_before_public_header[privacy.redacted_identifier_fields].allowed_field_classes",
        )
        require_string_list_contains(
            redaction,
            "must_redact",
            REQUIRED_REDACTED_FIELDS,
            blockers,
            "privacy_redacted_identifier_fields_missing_redactions",
            "$.required_before_public_header[privacy.redacted_identifier_fields].must_redact",
        )

    logging_policy = by_id.get("privacy.logging_and_storage_policy")
    if logging_policy is not None:
        if logging_policy.get("default_policy") != "no identity persistence and no raw identity logging":
            add(blockers, "privacy_logging_storage_default_policy_mismatch", "$.required_before_public_header[privacy.logging_and_storage_policy].default_policy")
        require_string_list_contains(
            logging_policy,
            "requires_before_persistence",
            {
                "operator ingress/storage surface promotion",
                "storage schema and migration policy",
                "secret-safe encoding policy",
                "audit and retention policy",
            },
            blockers,
            "privacy_logging_storage_missing_persistence_gates",
            "$.required_before_public_header[privacy.logging_and_storage_policy].requires_before_persistence",
        )

    scope = by_id.get("lifetime.principal_scope")
    if scope is not None:
        require_string_list_contains(scope, "allowed_scopes", REQUIRED_ALLOWED_SCOPES, blockers, "lifetime_principal_scope_missing_allowed_scopes", "$.required_before_public_header[lifetime.principal_scope].allowed_scopes")
        require_string_list_contains(scope, "forbidden_until_separate_promotion", REQUIRED_FORBIDDEN_SCOPES, blockers, "lifetime_principal_scope_missing_forbidden_scopes", "$.required_before_public_header[lifetime.principal_scope].forbidden_until_separate_promotion")
        require_string_list_contains(scope, "required_fields", REQUIRED_SCOPE_FIELDS, blockers, "lifetime_principal_scope_missing_required_fields", "$.required_before_public_header[lifetime.principal_scope].required_fields")
        allowed_scopes = string_list(scope.get("allowed_scopes"))
        if allowed_scopes is not None:
            forbidden_allowed = sorted(REQUIRED_FORBIDDEN_SCOPES & set(allowed_scopes))
            if forbidden_allowed:
                add(blockers, "lifetime_principal_scope_forbidden_scope_allowed", "$.required_before_public_header[lifetime.principal_scope].allowed_scopes", forbidden=forbidden_allowed)

    invalidation = by_id.get("lifetime.invalidation_events")
    if invalidation is not None:
        require_string_list_contains(invalidation, "required_invalidation_events", REQUIRED_INVALIDATION_EVENTS, blockers, "lifetime_invalidation_events_missing", "$.required_before_public_header[lifetime.invalidation_events].required_invalidation_events")
        require_string_list_contains(invalidation, "required_behavior", REQUIRED_INVALIDATION_BEHAVIOR, blockers, "lifetime_invalidation_behavior_missing", "$.required_before_public_header[lifetime.invalidation_events].required_behavior")

    stale_policy = by_id.get("lifetime.reconnect_duplicate_stale_policy")
    if stale_policy is not None:
        require_string_list_contains(stale_policy, "required_policy", REQUIRED_STALE_POLICY, blockers, "lifetime_reconnect_duplicate_stale_policy_missing", "$.required_before_public_header[lifetime.reconnect_duplicate_stale_policy].required_policy")

    payload_shape = by_id.get("abi.payload_shape")
    if payload_shape is not None:
        require_string_list_contains(payload_shape, "required_fields_or_equivalent", REQUIRED_CANDIDATE_PAYLOAD_FIELDS - {"reserved"}, blockers, "abi_payload_shape_missing_required_fields", "$.required_before_public_header[abi.payload_shape].required_fields_or_equivalent")
        require_string_list_contains(payload_shape, "required_properties", REQUIRED_ABI_PAYLOAD_SHAPE_PROPERTIES, blockers, "abi_payload_shape_missing_required_properties", "$.required_before_public_header[abi.payload_shape].required_properties")

    capability = by_id.get("abi.capability_bits")
    if capability is not None:
        require_string_list_contains(capability, "required_behavior", REQUIRED_CAPABILITY_BEHAVIOR, blockers, "abi_capability_bits_missing_fail_closed_behavior", "$.required_before_public_header[abi.capability_bits].required_behavior")

    owner_token = by_id.get("abi.owner_token_registration")
    if owner_token is not None:
        require_string_list_contains(owner_token, "required_behavior", REQUIRED_OWNER_TOKEN_BEHAVIOR, blockers, "abi_owner_token_registration_missing_fail_closed_behavior", "$.required_before_public_header[abi.owner_token_registration].required_behavior")

    layout_tests = by_id.get("abi.append_only_layout_tests")
    if layout_tests is not None:
        require_string_list_contains(layout_tests, "required_tests", REQUIRED_ABI_LAYOUT_TESTS, blockers, "abi_append_only_layout_tests_missing", "$.required_before_public_header[abi.append_only_layout_tests].required_tests")

    separation = by_id.get("separation.no_commands_permissions_persistence")
    if separation is not None:
        sequence_gate = string_list(separation.get("v1_sequence_gate"))
        if sequence_gate != REQUIRED_SEQUENCE_GATE:
            add(blockers, "separation_sequence_gate_mismatch", "$.required_before_public_header[separation.no_commands_permissions_persistence].v1_sequence_gate")
        require_string_list_contains(separation, "forbidden_in_identity_contract", REQUIRED_SEPARATION_FORBIDDEN, blockers, "separation_forbidden_downstream_surfaces_missing", "$.required_before_public_header[separation.no_commands_permissions_persistence].forbidden_in_identity_contract")


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if decisions.get("schema") != DECISION_SCHEMA:
        add(blockers, "decision_schema_mismatch", "$.schema")
    if decisions.get("surface") != SURFACE:
        add(blockers, "decision_surface_mismatch", "$.surface")
    if decisions.get("status") != "blocked":
        add(blockers, "decision_status_not_blocked", "$.status")
    if decisions.get("planning_stage") != "identity_public_contract_gate":
        add(blockers, "decision_planning_stage_mismatch", "$.planning_stage")
    if decisions.get("public_header_allowed") is not False:
        add(blockers, "public_header_allowed_not_false", "$.public_header_allowed")
    if decisions.get("public_header") != "include/obelisk/ObeliskApi.h":
        add(blockers, "public_header_path_mismatch", "$.public_header")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if decisions.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}")

    intake = decisions.get("approved_runtime_evidence_intake")
    if not isinstance(intake, dict):
        add(blockers, "approved_runtime_evidence_intake_missing", "$.approved_runtime_evidence_intake")
    else:
        if intake.get("id") != REQUIRED_INTAKE_ID:
            add(blockers, "approved_runtime_evidence_intake_id_mismatch", "$.approved_runtime_evidence_intake.id")
        if intake.get("status") != "external_manifest_required":
            add(blockers, "approved_runtime_evidence_intake_status_mismatch", "$.approved_runtime_evidence_intake.status")
        if intake.get("resolved_input") != REQUIRED_RESOLVED_INPUT:
            add(blockers, "approved_runtime_evidence_intake_resolved_input_mismatch", "$.approved_runtime_evidence_intake.resolved_input")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
            if intake.get(key) is not False:
                add(blockers, f"approved_runtime_evidence_intake_{key}_not_false", f"$.approved_runtime_evidence_intake.{key}")

    not_sufficient = decisions.get("approved_runtime_evidence_not_sufficient")
    if not isinstance(not_sufficient, dict):
        add(blockers, "approved_runtime_evidence_not_sufficient_missing", "$.approved_runtime_evidence_not_sufficient")
    else:
        if not_sufficient.get("decision") != "Approved runtime principal lifecycle evidence would be necessary evidence, but it is not sufficient to publish obelisk.player_identity.v1.":
            add(blockers, "approved_runtime_evidence_not_sufficient_decision_mismatch", "$.approved_runtime_evidence_not_sufficient.decision")
        require_string_list_contains(
            not_sufficient,
            "why",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY,
            blockers,
            "approved_runtime_evidence_not_sufficient_why_missing",
            "$.approved_runtime_evidence_not_sufficient.why",
        )
        require_string_list_contains(
            not_sufficient,
            "minimum_additional_gates",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES,
            blockers,
            "approved_runtime_evidence_not_sufficient_minimum_gates_missing",
            "$.approved_runtime_evidence_not_sufficient.minimum_additional_gates",
        )

    forbidden = decisions.get("forbidden_public_contract")
    if not isinstance(forbidden, list) or not REQUIRED_FORBIDDEN.issubset(set(forbidden)):
        add(blockers, "forbidden_public_contract_missing_required", "$.forbidden_public_contract")

    non_claims = decisions.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) for item in non_claims):
        add(blockers, "non_claims_not_string_list", "$.non_claims")
    else:
        missing_non_claims = missing_required(non_claims, REQUIRED_NON_CLAIMS)
        if missing_non_claims:
            add(blockers, "non_claims_missing_required", "$.non_claims", missing=missing_non_claims)

    validate_required_before_public_header(decisions, blockers)
    validate_candidate_only_pod_abi(decisions.get("proposed_public_pod_abi_candidate"), blockers)

    blockers_list = decisions.get("promotion_blockers")
    observed_ids = {
        item.get("id")
        for item in blockers_list
        if isinstance(blockers_list, list) and isinstance(item, dict)
    }
    if observed_ids != REQUIRED_BLOCKERS:
        add(
            blockers,
            "promotion_blockers_mismatch",
            "$.promotion_blockers",
            expected=sorted(REQUIRED_BLOCKERS),
            observed=sorted(str(item) for item in observed_ids),
        )
    if isinstance(blockers_list, list):
        for index, item in enumerate(blockers_list):
            if isinstance(item, dict) and item.get("status") == "resolved":
                add(blockers, "promotion_blocker_resolved_without_public_gate", f"$.promotion_blockers[{index}]")

    required_tests = decisions.get("required_tests_before_public_header")
    observed_test_ids: set[Any] = set()
    if isinstance(required_tests, list):
        observed_test_ids = {
            item.get("id")
            for item in required_tests
            if isinstance(item, dict)
        }
    else:
        add(blockers, "required_tests_before_public_header_not_list", "$.required_tests_before_public_header")
    if observed_test_ids != REQUIRED_TESTS_BEFORE_PUBLIC_HEADER:
        add(
            blockers,
            "required_tests_before_public_header_mismatch",
            "$.required_tests_before_public_header",
            expected=sorted(REQUIRED_TESTS_BEFORE_PUBLIC_HEADER),
            observed=sorted(str(item) for item in observed_test_ids),
        )
    if isinstance(required_tests, list):
        for index, item in enumerate(required_tests):
            if not isinstance(item, dict):
                add(blockers, "required_tests_before_public_header_entry_not_object", f"$.required_tests_before_public_header[{index}]")
                continue
            test_id = item.get("id")
            required_coverage = REQUIRED_TEST_COVERAGE_BY_ID.get(test_id)
            if required_coverage is not None:
                require_string_list_contains(
                    item,
                    "required_coverage",
                    required_coverage,
                    blockers,
                    "required_test_coverage_missing",
                    f"$.required_tests_before_public_header[{index}].required_coverage",
                )
            if test_id in CONTRACT_REVIEW_INPUT_ONLY_TESTS:
                if item.get("status") != "covered":
                    add(blockers, "contract_review_input_test_not_covered", f"$.required_tests_before_public_header[{index}].status", test_id=test_id)
                if item.get("coverage_status") != "contract_review_input_only":
                    add(blockers, "contract_review_input_test_status_mismatch", f"$.required_tests_before_public_header[{index}].coverage_status", test_id=test_id)
                covered_by = set(item.get("covered_by", [])) if isinstance(item.get("covered_by"), list) else set()
                missing_coverage = CONTRACT_REVIEW_INPUT_ONLY_TESTS[test_id] - covered_by
                if missing_coverage:
                    add(
                        blockers,
                        "contract_review_input_test_coverage_missing",
                        f"$.required_tests_before_public_header[{index}].covered_by",
                        test_id=test_id,
                        missing=sorted(missing_coverage),
                    )
                for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
                    if item.get(key) is not False:
                        add(blockers, f"contract_review_input_test_{key}_not_false", f"$.required_tests_before_public_header[{index}].{key}", test_id=test_id)
            elif item.get("status") != "missing":
                add(blockers, "pre_header_test_marked_ready_without_public_gate", f"$.required_tests_before_public_header[{index}].status", test_id=test_id)


def build_report(
    decisions: dict[str, Any],
    runtime_report: dict[str, Any],
    public_header_report: dict[str, Any],
    blockers: list[dict[str, Any]],
    check_mode: str,
) -> dict[str, Any]:
    runtime_ready = (
        runtime_report.get("approved_runtime_evidence_present") is True
        and runtime_report.get("runtime_evidence_ready") is True
        and runtime_report.get("promotion_ready") is False
        and runtime_report.get("public_sdk_ready") is False
        and runtime_report.get("runtime_ready") is False
    )
    if not runtime_ready:
        add(blockers, "approved_runtime_evidence_missing_or_not_ready", "$.approved_runtime_evidence")
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_player_identity_public_contract_promotion", "$.promotion_blockers")

    evidence_blockers = [
        blocker
        for blocker in blockers
        if not blocker["reason"].endswith("_blocked_until_player_identity_public_contract_promotion")
    ]
    accepted_for_contract_review = not evidence_blockers
    return {
        "schema": REPORT_SCHEMA,
        "surface": decisions.get("surface"),
        "mode": check_mode,
        "ready": accepted_for_contract_review and check_mode == "consume",
        "accepted_for_contract_review": accepted_for_contract_review,
        "resolved_inputs": [REQUIRED_RESOLVED_INPUT] if accepted_for_contract_review else [],
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_header_symbols_now": decisions.get("public_header_symbols_now"),
        "public_capability_bits_now": decisions.get("public_capability_bits_now"),
        "public_callback_abi_now": decisions.get("public_callback_abi_now"),
        "public_header_scan": public_header_report,
        "remaining_blockers": [
            blocker["id"]
            for blocker in decisions.get("promotion_blockers", [])
            if isinstance(blocker, dict)
        ],
        "required_tests_before_public_header": {
            "covered_for_contract_review_only": sorted(CONTRACT_REVIEW_INPUT_ONLY_TESTS),
            "remaining_missing": [
                item["id"]
                for item in decisions.get("required_tests_before_public_header", [])
                if isinstance(item, dict) and item.get("status") == "missing"
            ],
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "approved_runtime_evidence": {
            "approved_runtime_evidence_present": runtime_report.get("approved_runtime_evidence_present") is True,
            "runtime_evidence_ready": runtime_report.get("runtime_evidence_ready") is True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": [
            "approved runtime evidence intake does not add public header symbols, capability bits, callbacks, lookup, mutation, return override, or v1 SDK readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    blockers: list[dict[str, Any]] = []
    decisions = load_json(args.decisions, "decisions")
    validate_decisions(decisions, blockers)
    public_header_report = validate_public_header(decisions, args.public_header, blockers)
    runtime_report = approved_runtime_report(args.approved_runtime_evidence, blockers)
    report = build_report(decisions, runtime_report, public_header_report, blockers, check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
