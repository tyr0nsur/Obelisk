#!/usr/bin/env python3
"""Validate approved runtime principal lifecycle observer evidence.

This checker consumes a copied/sanitized `analyze_runtime_observer_log.py` summary plus
fail-closed consumer boundary cases. Acceptance means only that runtime lifecycle evidence
is reviewable for the player-principal lane; it does not promote public identity,
permissions, commands, lookup, mutation, or SDK readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import protected_paths
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
MODULE = "player_principal_lifecycle"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "artifact_status",
        "readiness_classification",
        "approved_runtime_evidence_present",
        "runtime_evidence_ready",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "approval",
        "source_summary",
        "consumer_boundary_cases",
        "privacy_boundary",
        "promotion_gate",
        "non_claims",
    )
)
REQUIRED_CONSUMER_CASES = frozenset(("stale_after_logout", "malformed_or_unsupported_evidence"))
REQUIRED_OBSERVED_EVENT_CASES = (
    {
        "target": "ShooterGameMode.HandleNewPlayer",
        "role": "session_start",
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["1", "1"],
        "principal_action": "candidate_created",
    },
    {
        "target": "ShooterGameMode.HandleNewPlayer",
        "role": "session_start_rejected",
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["0", "1"],
        "principal_action": "none",
    },
    {
        "target": "ShooterGameMode.OnLogout",
        "role": "session_end",
        "copied_bool_fields": [],
        "copied_bool_values": [],
        "principal_action": "candidate_invalidated",
    },
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "approved runtime observer evidence only",
        "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
        "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
        "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
    )
)
FORBIDDEN_KEY_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace)|object[_-]?address)",
    re.IGNORECASE,
)
ALLOWED_FORBIDDEN_KEY_PATHS = (
    "$.schema",
    "$.source_summary.modules.player_principal_lifecycle",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
ALLOWED_FORBIDDEN_LEAF_PATHS = (
    "$.schema",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
ALLOWED_FORBIDDEN_KEY_NAMES = frozenset(
    (
        "player_principal_lifecycle",
        "principal_action",
        "principal_claim",
        "principal_generation_logged",
        "principal_id_logged",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "non_claim",
    "privacy_boundary",
    "redacted",
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    observed_runtime_cases: list[str]
    consumer_cases: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Approved runtime lifecycle evidence manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--promote", action="store_true", help="Fail closed for public promotion checks.")
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


def load_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "manifest")
    path = reject_protected_input_path(path, "manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def source_path_is_copied_or_offline(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected


def detail_values(functions: dict[str, Any], function: str, key: str) -> list[Any]:
    details = functions.get(function, {}).get("details", {})
    value = details.get(key, [])
    return value if isinstance(value, list) else []


def require_values(
    blockers: list[dict[str, Any]],
    functions: dict[str, Any],
    function: str,
    key: str,
    expected: set[Any],
) -> None:
    values = set(detail_values(functions, function, key))
    if not expected.issubset(values):
        add(
            blockers,
            "runtime_summary_detail_values_missing",
            f"$.source_summary.modules.{MODULE}.functions.{function}.details.{key}",
            expected=sorted(expected, key=str),
            observed=sorted(values, key=str),
        )


def case_without_sequence(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": case.get("target"),
        "role": case.get("role"),
        "copied_bool_fields": case.get("copied_bool_fields"),
        "copied_bool_values": case.get("copied_bool_values"),
        "principal_action": case.get("principal_action"),
    }


def validate_observed_event_cases(module: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    cases = module.get("observed_event_cases")
    label = f"$.source_summary.modules.{MODULE}.observed_event_cases"
    if not isinstance(cases, list):
        add(blockers, "runtime_summary_observed_event_cases_missing", label)
        return []

    observed_runtime_cases: list[str] = []
    previous_sequence = 0
    remaining_expected = [dict(case) for case in REQUIRED_OBSERVED_EVENT_CASES]
    case_labels = {
        "session_start": "session_start_anchor",
        "session_start_rejected": "session_start_rejected_anchor",
        "session_end": "session_end_anchor",
    }

    for index, case in enumerate(cases):
        case_label = f"{label}[{index}]"
        if not isinstance(case, dict):
            add(blockers, "runtime_summary_observed_event_case_invalid", case_label)
            continue
        sequence = case.get("sequence")
        if not isinstance(sequence, int) or sequence <= previous_sequence:
            add(blockers, "runtime_summary_observed_event_case_sequence_invalid", f"{case_label}.sequence")
        if isinstance(sequence, int):
            previous_sequence = sequence
        compact_case = case_without_sequence(case)
        if compact_case in remaining_expected:
            remaining_expected.remove(compact_case)
            observed_runtime_cases.append(case_labels[str(compact_case["role"])])

    if remaining_expected:
        add(
            blockers,
            "runtime_summary_required_observed_event_cases_missing",
            label,
            missing=remaining_expected,
        )
    return observed_runtime_cases


def validate_runtime_summary(summary: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(summary, dict):
        add(blockers, "source_summary_missing", "$.source_summary")
        return []
    if summary.get("schema") != SUMMARY_SCHEMA:
        add(blockers, "source_summary_schema_mismatch", "$.source_summary.schema")
    if summary.get("review_scope") != "runtime_observer_evidence_summary":
        add(blockers, "source_summary_review_scope_mismatch", "$.source_summary.review_scope")
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "source_summary_evidence_missing", "$.source_summary.evidence")
    else:
        if evidence.get("kind") != "runtime-observer-log":
            add(blockers, "source_summary_evidence_kind_mismatch", "$.source_summary.evidence.kind")
        if evidence.get("server_paths_allowed") is not False:
            add(blockers, "source_summary_server_paths_allowed", "$.source_summary.evidence.server_paths_allowed")
        if not evidence.get("obelisk_commit"):
            add(blockers, "source_summary_obelisk_commit_missing", "$.source_summary.evidence.obelisk_commit")
        sources = evidence.get("sources")
        if not isinstance(sources, list) or not sources:
            add(blockers, "source_summary_sources_missing", "$.source_summary.evidence.sources")
        else:
            for index, source in enumerate(sources):
                label = f"$.source_summary.evidence.sources[{index}]"
                if not isinstance(source, dict):
                    add(blockers, "source_summary_source_invalid", label)
                    continue
                if not source_path_is_copied_or_offline(source.get("path")):
                    add(blockers, "source_summary_source_path_not_copied_or_offline", f"{label}.path")

    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        add(blockers, "source_summary_runtime_missing", "$.source_summary.runtime")
    else:
        expected_runtime = {
            "loaded_native_ld_preload": True,
            "process_event_candidate_count": 1,
            "process_event_hook_installed": True,
            "process_event_hook_patch_size": 18,
            "reflection_scanner_disabled": True,
            "plugins_disabled": True,
        }
        for key, expected in expected_runtime.items():
            if runtime.get(key) != expected:
                add(blockers, "source_summary_runtime_posture_mismatch", f"$.source_summary.runtime.{key}", expected=expected)

    modules = summary.get("modules")
    if not isinstance(modules, dict) or MODULE not in modules:
        add(blockers, "player_principal_lifecycle_module_missing", "$.source_summary.modules")
        return []
    module_names = set(modules)
    if module_names != {MODULE}:
        add(
            blockers,
            "source_summary_unexpected_modules_present",
            "$.source_summary.modules",
            expected=[MODULE],
            observed=sorted(module_names),
        )
    module = modules[MODULE]
    if not isinstance(module, dict):
        add(blockers, "player_principal_lifecycle_module_invalid", f"$.source_summary.modules.{MODULE}")
        return []
    if module.get("gate_sha256") != [EXPECTED_BINARY_SHA256]:
        add(blockers, "runtime_summary_gate_sha256_mismatch", f"$.source_summary.modules.{MODULE}.gate_sha256")
    if module.get("blockers") != ["runtime_observer_evidence_only"]:
        add(blockers, "runtime_summary_quality_blockers_present", f"$.source_summary.modules.{MODULE}.blockers")
    for key in (
        "malformed_observer_lines",
        "orphan_field_lines",
        "out_of_order_field_lines",
        "field_count_mismatches",
        "sequence_quality_violations",
        "event_before_gate_lines",
    ):
        if module.get(key) != 0:
            add(blockers, "runtime_summary_quality_counter_nonzero", f"$.source_summary.modules.{MODULE}.{key}")
    if module.get("redacted_detail_keys") != {}:
        add(blockers, "runtime_summary_unapproved_detail_keys", f"$.source_summary.modules.{MODULE}.redacted_detail_keys")
    if module.get("accepted_count", 0) < 3:
        add(blockers, "runtime_summary_insufficient_accepted_events", f"$.source_summary.modules.{MODULE}.accepted_count")

    functions = module.get("functions")
    if not isinstance(functions, dict):
        add(blockers, "runtime_summary_functions_missing", f"$.source_summary.modules.{MODULE}.functions")
        return []
    require_values(blockers, functions, "observer_gate", "target_set", {"players-lifecycle-anchor-candidates"})
    require_values(blockers, functions, "observer_gate", "dispatch_limit", {0})
    require_values(blockers, functions, "observer_gate", "delivery_claim", {"none"})
    require_values(blockers, functions, "observer_gate", "principal_claim", {"none"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "role", {"session_start", "session_start_rejected"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "copied_bool_fields", {"bIsFromLogin,ReturnValue"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "copied_bool_values", {"1,1", "0,1"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "redacted_count", {3})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "redacted_fields", {"NewPlayer,PlayerData,PlayerCharacter"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "principal_action", {"candidate_created", "none"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "principal_id_logged", {"false"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "principal_generation_logged", {"false"})
    require_values(blockers, functions, "ShooterGameMode.HandleNewPlayer", "delivery_claim", {"none"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "role", {"session_end"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "copied_bool_fields", {""})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "copied_bool_values", {""})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "redacted_count", {1})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "redacted_fields", {"Exiting"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "principal_action", {"candidate_invalidated"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "principal_id_logged", {"false"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "principal_generation_logged", {"false"})
    require_values(blockers, functions, "ShooterGameMode.OnLogout", "delivery_claim", {"none"})
    return validate_observed_event_cases(module, blockers)


def validate_consumer_boundary(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "consumer_boundary_cases_not_list", "$.consumer_boundary_cases")
        return []
    seen: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.consumer_boundary_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "consumer_boundary_case_invalid", label)
            continue
        name = case.get("case")
        if not isinstance(name, str):
            add(blockers, "consumer_boundary_case_missing", f"{label}.case")
            continue
        seen.append(name)
        if name not in REQUIRED_CONSUMER_CASES:
            add(blockers, "consumer_boundary_case_unexpected", f"{label}.case", case=name)
        if case.get("result") != "fail_closed":
            add(blockers, "consumer_boundary_case_not_fail_closed", f"{label}.result", case=name)
        for key in ("lookup_allowed", "mutation_allowed", "return_override_allowed", "public_sdk_surface"):
            if case.get(key) is not False:
                add(blockers, f"consumer_boundary_{key}_not_false", f"{label}.{key}", case=name)
    missing = REQUIRED_CONSUMER_CASES - set(seen)
    if missing:
        add(blockers, "consumer_boundary_cases_missing", "$.consumer_boundary_cases", missing=sorted(missing))
    return sorted(set(seen))


def validate_privacy(boundary: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(boundary, dict):
        add(blockers, "privacy_boundary_missing", "$.privacy_boundary")
        return
    for key in ("copied_opaque_principal_only", "redacted_runtime_observer", "player_identifiers_logged"):
        expected = False if key == "player_identifiers_logged" else True
        if boundary.get(key) is not expected:
            add(blockers, f"privacy_boundary_{key}_mismatch", f"$.privacy_boundary.{key}")
    for key in ("lookup_allowed", "resource_handle_allowed", "mutation_allowed", "return_override_allowed"):
        if boundary.get(key) is not False:
            add(blockers, f"privacy_boundary_{key}_not_false", f"$.privacy_boundary.{key}")


def validate_approval(approval: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(approval, dict):
        add(blockers, "approval_missing", "$.approval")
        return
    if approval.get("runtime_evidence_reviewed") is not True:
        add(blockers, "approval_runtime_evidence_reviewed_not_true", "$.approval.runtime_evidence_reviewed")
    for key in (
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
        "discord_authorized_by_this_manifest",
    ):
        if approval.get(key) is not False:
            add(blockers, f"approval_{key}_not_false", f"$.approval.{key}")


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    if gate.get("runtime_evidence_ready") is not True:
        add(blockers, "promotion_gate_runtime_evidence_ready_not_true", "$.promotion_gate.runtime_evidence_ready")
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")


def find_forbidden_key(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if any(token in trail for token in NEGATIVE_CONTEXT_TOKENS):
        return None
    if trail in ALLOWED_FORBIDDEN_LEAF_PATHS:
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                child_trail not in ALLOWED_FORBIDDEN_KEY_PATHS
                and str(key) not in ALLOWED_FORBIDDEN_KEY_NAMES
                and FORBIDDEN_KEY_RE.search(str(key))
                and child not in ([], {}, None)
            ):
                return str(key), child_trail
            found = find_forbidden_key(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_key(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and FORBIDDEN_KEY_RE.search(value) and "does not expose" not in value:
        return value, trail
    return None


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [], [])
    missing = REQUIRED_TOP_LEVEL_KEYS - set(payload)
    unexpected = set(payload) - REQUIRED_TOP_LEVEL_KEYS
    if missing:
        add(blockers, "top_level_fields_missing_required", "$", missing=sorted(missing))
    if unexpected:
        add(blockers, "top_level_fields_unexpected", "$", unexpected=sorted(unexpected))
    if payload.get("artifact_status") != "approved_runtime_observer_summary":
        add(blockers, "artifact_status_mismatch", "$.artifact_status")
    if payload.get("readiness_classification") != "runtime_evidence_only":
        add(blockers, "readiness_classification_mismatch", "$.readiness_classification")
    if payload.get("approved_runtime_evidence_present") is not True:
        add(blockers, "approved_runtime_evidence_present_not_true", "$.approved_runtime_evidence_present")
    if payload.get("runtime_evidence_ready") is not True:
        add(blockers, "runtime_evidence_ready_not_true", "$.runtime_evidence_ready")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    validate_approval(payload.get("approval"), blockers)
    observed_runtime_cases = validate_runtime_summary(payload.get("source_summary"), blockers)
    consumer_cases = validate_consumer_boundary(payload.get("consumer_boundary_cases"), blockers)
    validate_privacy(payload.get("privacy_boundary"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")
    forbidden = find_forbidden_key(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_identity_or_ue_internal_leakage", trail, value=value)
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_identity_public_contract_gate", "$.promotion_gate")
    return Validation(blockers, observed_runtime_cases, consumer_cases)


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    readiness_mode_blockers = {
        "promote_blocked_until_identity_public_contract_gate",
        "public_readiness_blocked_until_identity_public_contract_gate",
        "runtime_readiness_blocked_until_identity_public_contract_gate",
    }
    evidence_blockers = [
        blocker
        for blocker in validation.blockers
        if blocker["reason"] not in readiness_mode_blockers
    ]
    evidence_accepted = not evidence_blockers
    accepted = not validation.blockers
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": accepted,
        "approved_runtime_evidence_present": evidence_accepted,
        "runtime_evidence_ready": evidence_accepted,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": [] if accepted else ["approved_runtime_evidence_not_accepted"],
        "observed_runtime_cases": validation.observed_runtime_cases,
        "consumer_cases": validation.consumer_cases,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": [
            "runtime evidence acceptance does not promote public SDK identity, permissions, commands, lookup, mutation, or v1 readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    payload = load_json(args.manifest)
    validation = validate_manifest(payload, check_mode=check_mode)
    report = build_report(payload, validation, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
