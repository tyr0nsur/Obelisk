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
    "no mutation or return override authority",
}
REQUIRED_CANDIDATE_OWNER_TOKEN_REQUIREMENTS = {
    "nonzero plugin_owner_token required",
    "event-kind mask required",
    "opaque uint64 registration handle returned on success",
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
}
PUBLIC_CLAIM_KEYS = ("public_header_allowed", "promotion_ready", "public_sdk_ready", "runtime_ready")


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

    forbidden = decisions.get("forbidden_public_contract")
    if not isinstance(forbidden, list) or not REQUIRED_FORBIDDEN.issubset(set(forbidden)):
        add(blockers, "forbidden_public_contract_missing_required", "$.forbidden_public_contract")

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


def build_report(decisions: dict[str, Any], runtime_report: dict[str, Any], blockers: list[dict[str, Any]], check_mode: str) -> dict[str, Any]:
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
    runtime_report = approved_runtime_report(args.approved_runtime_evidence, blockers)
    report = build_report(decisions, runtime_report, blockers, check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
