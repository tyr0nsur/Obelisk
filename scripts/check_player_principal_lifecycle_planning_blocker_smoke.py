#!/usr/bin/env python3
"""Smoke-check the player-principal lifecycle planning bundle blocker.

This is an offline guardrail for committed planning-source manifests. It verifies that
candidate lifecycle/principal planning inputs remain internally bound and that the next
blocker is exactly approved_runtime_evidence_missing. It does not accept request packs,
operator receipts, copied logs, or runtime evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    REQUIRED_CONSUMER_CASES,
    REQUIRED_OBSERVED_EVENT_CASES,
)


REPORT_SCHEMA = "obelisk.player-principal-lifecycle-planning-blocker-smoke.v1"
ROUTE_AUDIT_SCHEMA = "obelisk.player-principal-lifecycle-offline-route-audit.v1"
EXPECTED_BLOCKER = "approved_runtime_evidence_missing"
DEFAULT_ROOT = Path("docs/research/player-identity-planning-sources")
REPORT_NAME = "player-identity-planning-source-manifests-report.json"
LIFECYCLE_NAME = "players-identity-lifecycle-anchor-candidates.json"
POLICY_NAME = "players-identity-principal-invalidation-policy.json"
FIRST_EVIDENCE_NAME = "players-identity-first-evidence.json"
EXPECTED_REPORT_SCHEMA = "obelisk.player-identity-planning-source-manifests-build-report.v1"
EXPECTED_LIFECYCLE_SCHEMA = "obelisk.players-identity-lifecycle-anchor-candidates.v1"
EXPECTED_POLICY_SCHEMA = "obelisk.players-identity-principal-invalidation-policy.v1"
EXPECTED_FIRST_EVIDENCE_SCHEMA = "obelisk.players-identity-first-evidence.v1"
EXPECTED_START_TARGETS = ("ShooterGameMode.HandleNewPlayer",)
EXPECTED_END_TARGETS = ("ShooterGameMode.OnLogout",)
NO_RUNTIME_NON_CLAIM = "no runtime or server operation was performed"
NO_PUBLIC_SDK_NON_CLAIM = "no public SDK, public ABI, release, or v1 completion readiness is claimed"
APPROVED_MANIFEST_CHECKER = "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
APPROVED_MANIFEST_BUILDER = "scripts/build_player_identity_runtime_principal_lifecycle_approved_manifest.py"
PLAYER_PRESENCE_SAFETY_SCHEMA = "obelisk.player-principal-lifecycle-player-presence-safety.v1"
PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION = (
    "player-presence safety checklist only; request pack acceptance does not authorize player "
    "queries, RCON/admin-console broadcasts, server operations, marker/env changes, restart, "
    "runtime capture, approved runtime evidence, public readiness, or SDK completion"
)
PLAYER_PRESENCE_SAFETY_KEYS = (
    "schema",
    "target",
    "restart_expectation",
    "connected_player_check_required_before_restart",
    "rcon_broadcast_required_if_players_connected",
    "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected",
    "passive_wait_preferred_after_activation",
    "linuxgsm_monitor_forbidden",
    "player_check_or_broadcast_authorized_by_request_pack",
    "non_authorization",
)


def route_audit_summary() -> dict[str, Any]:
    return {
        "schema": ROUTE_AUDIT_SCHEMA,
        "status": "route_blocked_approved_runtime_evidence_missing",
        "current_blocker": EXPECTED_BLOCKER,
        "waiting_for_exact_check_join_in_progress_1_0_is_fastest_valid_route": True,
        "recommended_next_action": (
            "under a separately approved player-backed runtime window, obtain exact "
            "CheckJoinInProgress(1,0) session_start_rejected between accepted "
            "HandleNewPlayer(1,1) session_start and matched OnLogout session_end"
        ),
        "primary_missing_runtime_shape": {
            "role": "session_start_rejected",
            "target": "ShooterGameMode.CheckJoinInProgress",
            "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
            "copied_bool_values": ["1", "0"],
            "principal_action": "none",
            "apply_status": "session_start_rejected_noop",
            "correlation_status": "not_applicable",
        },
        "extra_diagnostic_shape_logging_should_be_primary_next_action": False,
        "different_map_or_tester_flow_should_be_primary_next_action": False,
        "offline_layout_or_static_discovery_should_be_primary_next_action": False,
        "offline_planning_change_needed_for_evidence": False,
        "copied_observation_rejection_is_not_evidence": True,
        "passive_or_diagnostic_material_counts_as_evidence": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_claim_allowed": False,
        "non_authorization": "planning smoke only; this route audit does not authorize runtime work",
    }
POSITIVE_CLAIM_ALIAS_RE = (
    "approvedruntimeevidence",
    "approved_runtime_evidence",
    "approvedruntimeevidencepresent",
    "approved_runtime_evidence_present",
    "approvedruntimeevidenceready",
    "approved_runtime_evidence_ready",
    "authorizesruntimework",
    "authorizes_runtime_work",
    "authorizesserveroperations",
    "authorizes_server_operations",
    "authorizesworkspacewrites",
    "authorizes_workspace_writes",
    "currentturnauthorization",
    "current_turn_authorization",
    "currentturnauthorized",
    "current_turn_authorized",
    "liveopsauthorized",
    "live_ops_authorized",
    "runtimecaptureauthorized",
    "runtime_capture_authorized",
    "workspacewritesauthorized",
    "workspace_writes_authorized",
    "readslivelogs",
    "reads_live_logs",
    "publicsdkready",
    "public_sdk",
    "publicabiready",
    "public_abi",
    "publicheaderallowed",
    "public_header",
    "runtimeready",
    "runtime_ready",
    "runtimeevidenceready",
    "runtime_evidence_ready",
    "runtimeworkauthorized",
    "runtime_work_authorized",
    "serveroperationsauthorized",
    "server_operations_authorized",
    "promotionready",
    "promotion_ready",
    "v1completionready",
    "v1_completion",
    "completesdk",
    "complete_sdk",
    "stableclaimallowed",
    "stable_claim",
    "stablesdk",
    "stable_sdk",
    "passivesnapshotsasevidence",
    "passive_snapshots_as_evidence",
    "passivesnapshotscountasevidence",
    "passive_snapshots_count_as_evidence",
    "passivesnapshotevidenceallowed",
    "passive_snapshot_evidence_allowed",
    "candidatesidecarscountasapprovedruntimeevidence",
    "candidate_sidecars_count_as_approved_runtime_evidence",
    "passivecompletetripletscountasapprovedruntimeevidence",
    "passive_complete_triplets_count_as_approved_runtime_evidence",
    "requestpackpreflightwindowmanifestcountasapprovedruntimeevidence",
    "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence",
    "statusreportpathsauthorizecurrentturn",
    "status_report_paths_authorize_current_turn",
    "statusreportpathscountasapprovedruntimeevidence",
    "status_report_paths_count_as_approved_runtime_evidence",
    "productionready",
    "production_ready",
    "releaseready",
    "release_ready",
    "runtimev1",
    "runtime_v1",
    "countstowardpublicsdk",
    "counts_toward_public_sdk",
    "countstowardsdk",
    "counts_toward_sdk",
    "countstowardruntime",
    "counts_toward_runtime",
    "countstowardv1",
    "counts_toward_v1",
    "countstowardv1completion",
    "counts_toward_v1_completion",
    "countstowardcompletesdkclaimnow",
    "counts_toward_complete_sdk_claim_now",
    "countstowardp0dependencychainclaimnow",
    "counts_toward_p0_dependency_chain_claim_now",
    "requestpackready",
    "request_pack_ready",
    "preflightready",
    "preflight_ready",
    "windowmanifestready",
    "window_manifest_ready",
    "statusreportready",
    "status_report_ready",
)
POSITIVE_CLAIM_TEXT_RE = (
    "approved runtime evidence",
    "approved runtime evidence present",
    "approved runtime evidence ready",
    "runtime evidence ready",
    "runtime ready",
    "runtime work authorized",
    "server operations authorized",
    "public sdk ready",
    "public abi ready",
    "public header allowed",
    "v1 completion ready",
    "complete sdk",
    "sdk complete",
    "stable claim allowed",
    "stable sdk",
    "production ready",
    "release ready",
    "counts toward sdk",
    "counts toward v1",
    "live ops authorized",
    "runtime capture authorized",
    "reads live logs",
    "passive snapshots as evidence",
)
FALSE_CLAIM_KEYS = (
    "runtime_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "public_header_allowed",
    "promotion_ready",
    "v1_completion_ready",
    "stable_claim_allowed",
    "runtime_work_authorized",
    "server_operations_authorized",
    "live_ops_authorized",
    "runtime_capture_authorized",
    "workspace_writes_authorized",
    "reads_live_logs",
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "passive_snapshots_as_evidence",
    "passive_snapshots_count_as_evidence",
    "passive_snapshot_evidence_allowed",
    "candidate_sidecars_count_as_approved_runtime_evidence",
    "passive_complete_triplets_count_as_approved_runtime_evidence",
    "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence",
    "status_report_paths_authorize_current_turn",
    "status_report_paths_count_as_approved_runtime_evidence",
    "request_pack_ready",
    "preflight_ready",
    "window_manifest_ready",
    "status_report_ready",
    "counts_toward_sdk",
    "counts_toward_public_sdk",
    "counts_toward_v1",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim_now",
    "counts_toward_p0_dependency_chain_claim_now",
)
NEGATIVE_CONTEXT_KEYS = frozenset(
    (
        "blocker",
        "blockers",
        "forbidden",
        "missing",
        "non_claim",
        "non_claims",
        "not_sufficient",
        "reject",
        "rejected",
        "remaining_blockers",
    )
)


def required_runtime_event_cases() -> list[dict[str, Any]]:
    cases = [
        {
            "case": "observer_enable",
            "source": "runtime_observer_gate",
            "target_set": "players-lifecycle-anchor-candidates",
            "limit": 10,
            "dispatch_limit": 0,
            "delivery_claim": "none",
            "principal_claim": "none",
        }
    ]
    labels = {
        "session_start": "session_start_anchor",
        "session_start_rejected": "session_start_rejected_anchor",
        "session_end": "session_end_anchor",
    }
    for case in REQUIRED_OBSERVED_EVENT_CASES:
        role = str(case["role"])
        rendered = {"case": labels[role], **case}
        if role == "session_start_rejected":
            rendered["accepted_alternatives"] = [
                {
                    "target": "ShooterGameMode.CheckJoinInProgress",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "0"],
                },
            ]
            rendered["superseded_non_evidence_alternatives"] = [
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": values,
                    "status": "superseded_non_evidence",
                    "reason": "historical HandleNewPlayer rejected-start tuple is ambiguous and no longer satisfies approved runtime evidence",
                }
                for values in (["0", "1"], ["1", "0"], ["0", "0"])
            ]
        cases.append(rendered)
    return cases


def required_consumer_cases() -> list[dict[str, Any]]:
    return [
        {
            "case": case,
            "result": "fail_closed",
            "provenance": "consumer_boundary_assertion_not_runtime_observation",
        }
        for case in sorted(REQUIRED_CONSUMER_CASES)
    ]


@dataclass
class LoadedManifest:
    name: str
    path: Path
    payload: dict[str, Any]
    sha256: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"Planning-source manifest directory. Default: {DEFAULT_ROOT}",
    )
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_manifest(root: Path, name: str, blockers: list[dict[str, Any]]) -> LoadedManifest | None:
    path = root / name
    if path.is_symlink():
        add(blockers, "planning_manifest_symlinked", name, path=str(path))
        return None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        add(blockers, "planning_manifest_unreadable", name, path=str(path), error=str(exc))
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add(blockers, "planning_manifest_json_invalid", name, path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, "planning_manifest_not_object", name, path=str(path))
        return None
    return LoadedManifest(name=name, path=path, payload=payload, sha256=hashlib.sha256(raw).hexdigest())


def bool_false(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]], label: str) -> None:
    if payload.get(key) is not False:
        add(blockers, f"{label}_{key}_not_false", f"{label}.{key}")


def validate_no_readiness_overclaim(payload: dict[str, Any], blockers: list[dict[str, Any]], label: str) -> None:
    for key in FALSE_CLAIM_KEYS:
        if key in payload:
            bool_false(payload, key, blockers, label)


def normalized_claim_key(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def compact_claim_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def has_positive_claim_alias(value: str) -> bool:
    normalized = normalized_claim_key(value)
    compact = compact_claim_key(value)
    return any(alias in normalized or compact_claim_key(alias) in compact for alias in POSITIVE_CLAIM_ALIAS_RE)


def normalized_claim_text(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def is_negative_context(path: tuple[str, ...]) -> bool:
    for part in path:
        normalized = normalized_claim_key(part)
        tokens = set(normalized.split("_"))
        if normalized in NEGATIVE_CONTEXT_KEYS or tokens & NEGATIVE_CONTEXT_KEYS:
            return True
    return False


def validate_no_nested_positive_claims(value: Any, blockers: list[dict[str, Any]], label: str, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = (*path, key_text)
            if has_positive_claim_alias(key_text) and not is_negative_context(child_path):
                if child not in (False, None, [], {}, "false", "False", "not_ready", "blocked", "no", "none"):
                    add(
                        blockers,
                        "planning_manifest_nested_positive_claim",
                        f"{label}.{'.'.join(child_path)}",
                        value=child,
                    )
            validate_no_nested_positive_claims(child, blockers, label, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_nested_positive_claims(child, blockers, label, (*path, str(index)))
    elif isinstance(value, str) and not is_negative_context(path):
        normalized = normalized_claim_text(value)
        if any(alias in normalized for alias in POSITIVE_CLAIM_TEXT_RE):
            add(
                blockers,
                "planning_manifest_text_positive_claim",
                f"{label}.{'.'.join(path)}",
                value=value,
            )


def output_entry(report: dict[str, Any], key: str) -> dict[str, Any] | None:
    outputs = report.get("outputs")
    if not isinstance(outputs, dict):
        return None
    entry = outputs.get(key)
    return entry if isinstance(entry, dict) else None


def source_entry(report: dict[str, Any], key: str) -> dict[str, Any] | None:
    sources = report.get("binding_report", {}).get("sources")
    if not isinstance(sources, dict):
        return None
    entry = sources.get(key)
    return entry if isinstance(entry, dict) else None


def validate_report_binding(
    report: LoadedManifest,
    lifecycle: LoadedManifest,
    policy: LoadedManifest,
    first_evidence: LoadedManifest,
    blockers: list[dict[str, Any]],
) -> None:
    expected = {
        "lifecycle_anchor_candidates": lifecycle,
        "principal_invalidation_policy": policy,
        "first_evidence": first_evidence,
    }
    for key, manifest in expected.items():
        for source_kind, entry in (("outputs", output_entry(report.payload, key)), ("sources", source_entry(report.payload, key))):
            if entry is None:
                add(blockers, f"planning_report_{source_kind}_{key}_missing", f"report.{source_kind}.{key}")
                continue
            if entry.get("schema") != manifest.payload.get("schema"):
                add(
                    blockers,
                    f"planning_report_{source_kind}_{key}_schema_mismatch",
                    f"report.{source_kind}.{key}.schema",
                    expected=manifest.payload.get("schema"),
                    actual=entry.get("schema"),
                )
            if entry.get("sha256") != manifest.sha256:
                add(
                    blockers,
                    f"planning_report_{source_kind}_{key}_sha256_mismatch",
                    f"report.{source_kind}.{key}.sha256",
                    expected=manifest.sha256,
                    actual=entry.get("sha256"),
                )


def validate_lifecycle(lifecycle: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if lifecycle.get("schema") != EXPECTED_LIFECYCLE_SCHEMA:
        add(blockers, "lifecycle_schema_mismatch", "lifecycle.schema", expected=EXPECTED_LIFECYCLE_SCHEMA)
    if lifecycle.get("artifact_status") != "candidate_only":
        add(blockers, "lifecycle_artifact_status_not_candidate_only", "lifecycle.artifact_status")
    if lifecycle.get("readiness_classification") != "planning_only":
        add(blockers, "lifecycle_readiness_not_planning_only", "lifecycle.readiness_classification")
    validate_no_readiness_overclaim(lifecycle, blockers, "lifecycle")
    validate_no_nested_positive_claims(lifecycle, blockers, "lifecycle")
    acceptance = lifecycle.get("lifecycle_acceptance")
    if not isinstance(acceptance, dict):
        add(blockers, "lifecycle_acceptance_missing", "lifecycle.lifecycle_acceptance")
        return
    if tuple(acceptance.get("accepted_start_targets", ())) != EXPECTED_START_TARGETS:
        add(blockers, "lifecycle_start_targets_mismatch", "lifecycle.lifecycle_acceptance.accepted_start_targets")
    if tuple(acceptance.get("accepted_end_targets", ())) != EXPECTED_END_TARGETS:
        add(blockers, "lifecycle_end_targets_mismatch", "lifecycle.lifecycle_acceptance.accepted_end_targets")
    if acceptance.get("session_start_accepted") is not True:
        add(blockers, "lifecycle_session_start_not_accepted_for_planning", "lifecycle.lifecycle_acceptance.session_start_accepted")
    if acceptance.get("session_end_accepted") is not True:
        add(blockers, "lifecycle_session_end_not_accepted_for_planning", "lifecycle.lifecycle_acceptance.session_end_accepted")


def validate_policy(policy: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if policy.get("schema") != EXPECTED_POLICY_SCHEMA:
        add(blockers, "policy_schema_mismatch", "policy.schema", expected=EXPECTED_POLICY_SCHEMA)
    if policy.get("artifact_status") != "candidate_only":
        add(blockers, "policy_artifact_status_not_candidate_only", "policy.artifact_status")
    if policy.get("readiness_classification") != "planning_only":
        add(blockers, "policy_readiness_not_planning_only", "policy.readiness_classification")
    validate_no_readiness_overclaim(policy, blockers, "policy")
    validate_no_nested_positive_claims(policy, blockers, "policy")

    runtime_evidence = policy.get("runtime_evidence")
    if not isinstance(runtime_evidence, dict):
        add(blockers, "policy_runtime_evidence_missing", "policy.runtime_evidence")
    else:
        if runtime_evidence.get("approved") is not False:
            add(blockers, "policy_runtime_evidence_approved_not_false", "policy.runtime_evidence.approved")
        if runtime_evidence.get("status") != "not_approved":
            add(blockers, "policy_runtime_evidence_status_not_not_approved", "policy.runtime_evidence.status")

    gate = policy.get("promotion_gate")
    if not isinstance(gate, dict):
        add(blockers, "policy_promotion_gate_missing", "policy.promotion_gate")
        return
    validate_no_readiness_overclaim(gate, blockers, "policy_promotion_gate")
    blockers_list = gate.get("blockers")
    if not isinstance(blockers_list, list):
        add(blockers, "policy_promotion_gate_blockers_not_list", "policy.promotion_gate.blockers")
    elif blockers_list != [EXPECTED_BLOCKER, "principal_invalidation_semantics_unresolved", "candidate_only_policy"]:
        add(
            blockers,
            "policy_promotion_gate_blockers_mismatch",
            "policy.promotion_gate.blockers",
            expected=[EXPECTED_BLOCKER, "principal_invalidation_semantics_unresolved", "candidate_only_policy"],
            actual=blockers_list,
        )


def validate_first_evidence(first_evidence: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if first_evidence.get("schema") != EXPECTED_FIRST_EVIDENCE_SCHEMA:
        add(blockers, "first_evidence_schema_mismatch", "first_evidence.schema", expected=EXPECTED_FIRST_EVIDENCE_SCHEMA)
    if first_evidence.get("artifact_status") != "candidate_only":
        add(blockers, "first_evidence_artifact_status_not_candidate_only", "first_evidence.artifact_status")
    if first_evidence.get("readiness_classification") != "planning_only":
        add(blockers, "first_evidence_readiness_not_planning_only", "first_evidence.readiness_classification")
    validate_no_readiness_overclaim(first_evidence, blockers, "first_evidence")
    validate_no_nested_positive_claims(first_evidence, blockers, "first_evidence")


def validate_build_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if report.get("schema") != EXPECTED_REPORT_SCHEMA:
        add(blockers, "planning_report_schema_mismatch", "report.schema", expected=EXPECTED_REPORT_SCHEMA)
    if report.get("accepted_for_planning") is not True:
        add(blockers, "planning_report_not_accepted_for_planning", "report.accepted_for_planning")
    if report.get("planning_only") is not True:
        add(blockers, "planning_report_planning_only_not_true", "report.planning_only")
    if report.get("valid") is not True:
        add(blockers, "planning_report_valid_not_true", "report.valid")
    if report.get("blockers") not in ([], None):
        add(blockers, "planning_report_has_blockers", "report.blockers", actual=report.get("blockers"))
    validate_no_readiness_overclaim(report, blockers, "report")
    validate_no_nested_positive_claims(report, blockers, "report")
    non_claims = report.get("non_claims")
    if not isinstance(non_claims, list) or NO_RUNTIME_NON_CLAIM not in non_claims:
        add(blockers, "planning_report_runtime_non_claim_missing", "report.non_claims")
    binding_non_claims = report.get("binding_report", {}).get("non_claims")
    if not isinstance(binding_non_claims, list) or NO_PUBLIC_SDK_NON_CLAIM not in binding_non_claims:
        add(blockers, "planning_report_public_sdk_non_claim_missing", "report.binding_report.non_claims")


def build_report(root: Path, manifests: dict[str, LoadedManifest | None], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    planning_ready = not blockers
    route_audit = route_audit_summary()
    return {
        "schema": REPORT_SCHEMA,
        "ready": planning_ready,
        "planning_sources_ready": planning_ready,
        "offline_only": True,
        "runtime_evidence_ready": False,
        "runtime_evidence_present": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "runtime_work_authorized": False,
        "server_operations_authorized": False,
        "live_ops_authorized": False,
        "runtime_capture_authorized": False,
        "workspace_writes_authorized": False,
        "reads_live_logs": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "passive_snapshots_as_evidence": False,
        "passive_snapshots_count_as_evidence": False,
        "passive_snapshot_evidence_allowed": False,
        "candidate_sidecars_count_as_approved_runtime_evidence": False,
        "passive_complete_triplets_count_as_approved_runtime_evidence": False,
        "request_pack_preflight_window_manifest_count_as_approved_runtime_evidence": False,
        "request_pack_ready": False,
        "preflight_ready": False,
        "window_manifest_ready": False,
        "status_report_ready": False,
        "status_report_paths_authorize_current_turn": False,
        "status_report_paths_count_as_approved_runtime_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_v1": False,
        "counts_toward_v1_completion": False,
        "remaining_blockers": [EXPECTED_BLOCKER],
        "next_blocker": EXPECTED_BLOCKER,
        "route_audit": route_audit,
        "root": str(root),
        "manifests": {
            key: (
                {
                    "path": str(manifest.path),
                    "schema": manifest.payload.get("schema"),
                    "sha256": manifest.sha256,
                }
                if manifest is not None
                else None
            )
            for key, manifest in manifests.items()
        },
        "accepted_start_targets": list(EXPECTED_START_TARGETS) if planning_ready else [],
        "accepted_end_targets": list(EXPECTED_END_TARGETS) if planning_ready else [],
        "approved_manifest_checker": APPROVED_MANIFEST_CHECKER,
        "approved_manifest_builder": APPROVED_MANIFEST_BUILDER,
        "required_runtime_event_cases": required_runtime_event_cases(),
        "required_consumer_cases": required_consumer_cases(),
        "next_runtime_artifact_contract": {
            "required_artifact": "approved_runtime_principal_lifecycle_evidence",
            "required_builder": APPROVED_MANIFEST_BUILDER,
            "required_checker": APPROVED_MANIFEST_CHECKER,
            "required_window_replay": "--post-window-replay",
            "source_summary_module": "player_principal_lifecycle",
            "required_request_sections": [
                "current_turn_approval_scope",
                "passive_wait_boundary",
                "player_notice_action",
                "player_presence_safety",
                "post_window_replay_contract",
            ],
            "player_presence_safety_contract": {
                "schema": PLAYER_PRESENCE_SAFETY_SCHEMA,
                "required": True,
                "source": "window-request.json.player_presence_safety",
                "required_keys": list(PLAYER_PRESENCE_SAFETY_KEYS),
                "restart_expectation_restart_requires": {
                    "connected_player_check_required_before_restart": True,
                    "rcon_broadcast_required_if_players_connected": True,
                    "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": True,
                },
                "passive_wait_preferred_after_activation": True,
                "linuxgsm_monitor_forbidden": True,
                "player_check_or_broadcast_authorized_by_request_pack": False,
                "non_authorization": PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
            },
            "route_audit": route_audit,
            "non_authorization": "planning smoke only; this contract does not authorize runtime work",
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "planning-source smoke only; does not authorize runtime work, server operations, marker/env changes, request approval, or evidence capture",
            "planning-source smoke acceptance is not approved runtime evidence and does not promote public SDK, ABI, identity, lookup, permissions, commands, mutation, return override, or v1 completion",
        ],
    }


def main() -> int:
    args = parse_args()
    root = args.root
    blockers: list[dict[str, Any]] = []
    if root.is_symlink():
        add(blockers, "planning_root_symlinked", "root", path=str(root))
    if not root.is_dir():
        add(blockers, "planning_root_missing", "root", path=str(root))

    manifests = {
        "report": load_manifest(root, REPORT_NAME, blockers),
        "lifecycle_anchor_candidates": load_manifest(root, LIFECYCLE_NAME, blockers),
        "principal_invalidation_policy": load_manifest(root, POLICY_NAME, blockers),
        "first_evidence": load_manifest(root, FIRST_EVIDENCE_NAME, blockers),
    }

    report_manifest = manifests["report"]
    lifecycle_manifest = manifests["lifecycle_anchor_candidates"]
    policy_manifest = manifests["principal_invalidation_policy"]
    first_evidence_manifest = manifests["first_evidence"]

    if report_manifest is not None:
        validate_build_report(report_manifest.payload, blockers)
    if lifecycle_manifest is not None:
        validate_lifecycle(lifecycle_manifest.payload, blockers)
    if policy_manifest is not None:
        validate_policy(policy_manifest.payload, blockers)
    if first_evidence_manifest is not None:
        validate_first_evidence(first_evidence_manifest.payload, blockers)
    if all(manifest is not None for manifest in (report_manifest, lifecycle_manifest, policy_manifest, first_evidence_manifest)):
        validate_report_binding(report_manifest, lifecycle_manifest, policy_manifest, first_evidence_manifest, blockers)

    output = build_report(root, manifests, blockers)
    if args.json:
        print(json.dumps(output, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    else:
        print(f"player_principal_lifecycle_planning_blocker_smoke=ok next_blocker={EXPECTED_BLOCKER}")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
