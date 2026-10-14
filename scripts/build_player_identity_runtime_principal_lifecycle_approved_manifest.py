#!/usr/bin/env python3
"""Build a consume-only approved player-principal lifecycle evidence manifest.

The input is the copied/offline JSON summary produced by
analyze_runtime_observer_log.py. This helper does not read server logs, does not start
servers, and does not promote public player identity or SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_evidence_checker
import protected_paths
from artifact_identity import canonical_json_bytes
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_TEXT,
    STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
)


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
WINDOW_CHECK_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
EXPECTED_MODULE = "player_principal_lifecycle"
EXPECTED_COPIED_LOG_PATH_STATUS = "approved_offline_workspace"
APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS = (
    approved_evidence_checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS
)
APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION = (
    approved_evidence_checker.APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION
)
APPROVED_OFFLINE_WORKSPACE_ROOTS = protected_paths.approved_offline_workspace_roots()
FORBIDDEN_REVIEW_TEXT_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace)|object[_-]?address)",
    re.IGNORECASE,
)

REQUIRED_NON_CLAIMS = [
    "approved runtime observer evidence only",
    (
        "does not promote public player identity, lookup, permissions, commands, moderation, "
        "admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness"
    ),
    (
        "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, "
        "GObjects, raw params, or persistent lookup keys"
    ),
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
]
NON_EVIDENCE_SOURCE_SCHEMA_BLOCKERS = {
    SCHEMA: "source_summary_approved_runtime_manifest_not_runtime_observer_summary",
    approved_evidence_checker.SHAPE_FIXTURE_SCHEMA: "source_summary_shape_fixture_not_runtime_observer_summary",
    approved_evidence_checker.EXPECTED_REQUEST_SCHEMA: (
        "source_summary_window_request_not_runtime_observer_summary"
    ),
    approved_evidence_checker.EXPECTED_PREFLIGHT_SCHEMA: (
        "source_summary_preflight_not_runtime_observer_summary"
    ),
    approved_evidence_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCHEMA: (
        "source_summary_operator_approval_receipt_not_runtime_observer_summary"
    ),
    approved_evidence_checker.WINDOW_CHECK_SCHEMA: (
        "source_summary_window_manifest_check_not_runtime_observer_summary"
    ),
    approved_evidence_checker.REPORT_SCHEMA: (
        "source_summary_approved_evidence_check_not_runtime_observer_summary"
    ),
    approved_evidence_checker.BUNDLE_PREFLIGHT_SCHEMA: (
        "source_summary_bundle_preflight_not_runtime_observer_summary"
    ),
    approved_evidence_checker.BUNDLE_REPORT_SCHEMA: (
        "source_summary_bundle_report_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1": "source_summary_notice_prep_not_runtime_observer_summary",
    "obelisk.player-principal-lifecycle-evidence-closure-request.v1": (
        "source_summary_closure_request_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-snapshot.v1": "source_summary_passive_snapshot_not_runtime_observer_summary",
    "obelisk.player-principal-passive-snapshot-diff.v1": (
        "source_summary_passive_snapshot_diff_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-snapshot-latest.v1": (
        "source_summary_passive_snapshot_latest_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PASSIVE_SNAPSHOT_ROLLUP_SCHEMA: (
        "source_summary_passive_snapshot_rollup_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-observer-event-triage.v1": (
        "source_summary_passive_event_triage_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PASSIVE_ACTIVITY_TRIAGE_SCHEMA: (
        "source_summary_passive_activity_triage_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-actionability.v1": (
        "source_summary_passive_actionability_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-target-triplet-candidate-summary.v1": (
        "source_summary_passive_target_triplet_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-server-activity-summary.v1": (
        "source_summary_passive_server_activity_not_runtime_observer_summary"
    ),
    "obelisk.player-principal-passive-wait-metadata.v1": (
        "source_summary_passive_wait_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_REACHABILITY_SCHEMA: (
        "source_summary_public_reachability_not_runtime_observer_summary"
    ),
    approved_evidence_checker.SDK_STATUS_REPORT_SCHEMA: (
        "source_summary_sdk_status_report_not_runtime_observer_summary"
    ),
    approved_evidence_checker.SDK_STATUS_SIDE_LANE_SUMMARY_SCHEMA: (
        "source_summary_sdk_status_side_lane_summary_not_runtime_observer_summary"
    ),
    approved_evidence_checker.POST_EVIDENCE_P0_LOCK_SIMULATION_SCHEMA: (
        "source_summary_post_evidence_p0_lock_simulation_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLANNING_BLOCKER_SMOKE_SCHEMA: (
        "source_summary_planning_blocker_smoke_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLANNING_SOURCE_MANIFESTS_BUILD_REPORT_SCHEMA: (
        "source_summary_planning_source_manifests_build_report_not_runtime_observer_summary"
    ),
    approved_evidence_checker.LIFECYCLE_ANCHOR_CANDIDATES_SCHEMA: (
        "source_summary_lifecycle_anchor_candidates_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PRINCIPAL_INVALIDATION_POLICY_SCHEMA: (
        "source_summary_principal_invalidation_policy_not_runtime_observer_summary"
    ),
    approved_evidence_checker.FIRST_EVIDENCE_SCHEMA: (
        "source_summary_first_evidence_planning_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.COMMAND_PERMISSION_ROUTE_GATE_CHECK_SCHEMA: (
        "source_summary_command_permission_route_gate_check_not_runtime_observer_summary"
    ),
    approved_evidence_checker.COMMAND_PERMISSION_ROUTE_BOUND_IDENTITY_SOURCE_FORWARDING_SCHEMA: (
        "source_summary_command_permission_route_bound_identity_source_forwarding_not_runtime_observer_summary"
    ),
    approved_evidence_checker.COMMAND_PERMISSION_ROUTE_SIMULATION_SCHEMA: (
        "source_summary_command_permission_route_simulation_not_runtime_observer_summary"
    ),
    approved_evidence_checker.COMMAND_PERMISSION_ROUTE_POST_EVIDENCE_IDENTITY_LOCK_SCHEMA: (
        "source_summary_command_permission_route_post_evidence_identity_lock_not_runtime_observer_summary"
    ),
    approved_evidence_checker.COMMAND_PERMISSION_ROUTE_SNAPSHOT_SCHEMA: (
        "source_summary_command_permission_route_snapshot_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_SURFACES_SCHEMA: (
        "source_summary_public_sdk_surfaces_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_COMPLETION_READY_SCHEMA_ID_SCHEMA: (
        "source_summary_public_sdk_completion_ready_schema_id_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_COMPLETION_CHECK_SCHEMA: (
        "source_summary_public_sdk_completion_check_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_COMPLETION_SUMMARY_SCHEMA: (
        "source_summary_public_sdk_completion_summary_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_FASTEST_NEXT_UNBLOCK_SCHEMA: (
        "source_summary_public_sdk_fastest_next_unblock_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_PROGRESS_NORMALIZATION_TRACE_SCHEMA: (
        "source_summary_public_sdk_progress_normalization_trace_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PUBLIC_SDK_V1_APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: (
        "source_summary_public_sdk_approved_in_game_evidence_status_not_runtime_observer_summary"
    ),
    approved_evidence_checker.APPROVED_IN_GAME_EVIDENCE_STATUS_SCHEMA: (
        "source_summary_approved_in_game_evidence_status_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISIONS_SCHEMA: (
        "source_summary_contract_review_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA: (
        "source_summary_contract_review_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_CHECK_SCHEMA: (
        "source_summary_contract_review_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_IDENTITY_PUBLIC_CONTRACT_GAP_REPORT_SCHEMA: (
        "source_summary_contract_review_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_IDENTITY_PUBLIC_CONTRACT_READINESS_CHECK_SCHEMA: (
        "source_summary_contract_review_artifact_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_NOTICE_ACTION_SCHEMA: (
        "source_summary_player_notice_action_not_runtime_observer_summary"
    ),
    approved_evidence_checker.GENERIC_PLAYER_NOTICE_ACTION_SCHEMA: (
        "source_summary_player_notice_action_not_runtime_observer_summary"
    ),
    approved_evidence_checker.GUARDED_BETA_NOTICE_ACTION_SCHEMA: (
        "source_summary_guarded_beta_notice_action_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PLAYER_PRESENCE_SAFETY_SCHEMA: (
        "source_summary_player_presence_safety_not_runtime_observer_summary"
    ),
    approved_evidence_checker.ACTIVATION_PRECONDITIONS_SCHEMA: (
        "source_summary_activation_preconditions_not_runtime_observer_summary"
    ),
    approved_evidence_checker.WINDOW_REQUEST_CHECK_SCHEMA: (
        "source_summary_window_request_check_not_runtime_observer_summary"
    ),
    approved_evidence_checker.SCOPED_RELEASE_STATEMENT_OUTCOMES_SCHEMA: (
        "source_summary_scoped_release_statement_not_runtime_observer_summary"
    ),
    approved_evidence_checker.INSTALLED_SDK_PACKAGE_SHAPE_SCHEMA: (
        "source_summary_installed_sdk_package_shape_not_runtime_observer_summary"
    ),
    approved_evidence_checker.INTERNAL_MODULE_READINESS_SCHEMA: (
        "source_summary_internal_module_readiness_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PASSIVE_MONITOR_LOG_METADATA_SCHEMA: (
        "source_summary_passive_monitor_metadata_not_runtime_observer_summary"
    ),
    approved_evidence_checker.PASSIVE_ORGANIC_PLAYER_DETECTION_SCHEMA: (
        "source_summary_passive_organic_player_detection_not_runtime_observer_summary"
    ),
    approved_evidence_checker.READY_LOG_COPY_SCHEMA: (
        "source_summary_ready_log_copy_not_runtime_observer_summary"
    ),
}
SOURCE_SUMMARY_FORBIDDEN_POSITIVE_FLAG_KEYS = frozenset(
    (
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "passive_complete_triplets_count_as_approved_runtime_evidence",
        "passive_complete_triplet_counts_as_evidence",
        "passive_snapshots_as_evidence",
        "passive_snapshots_count_as_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "copy_report_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "request_output_counts_as_approved_runtime_evidence",
        "window_request_counts_as_approved_runtime_evidence",
        "window_request_output_counts_as_approved_runtime_evidence",
        "runtime_window_request_counts_as_approved_runtime_evidence",
        "runtime_window_request_output_counts_as_approved_runtime_evidence",
        "passive_snapshot_rollup_counts_as_approved_runtime_evidence",
        "completion_status_counts_as_approved_runtime_evidence",
        "status_report_counts_as_approved_runtime_evidence",
        "planning_artifact_counts_as_approved_runtime_evidence",
        "planning_snapshot_counts_as_approved_runtime_evidence",
        "activation_preconditions_counts_as_approved_runtime_evidence",
        "player_notice_action_counts_as_approved_runtime_evidence",
        "guarded_beta_notice_action_counts_as_approved_runtime_evidence",
        "public_sdk_ready",
        "source_overclaim_total_flag_count",
        "public_abi_ready",
        "promotion_ready",
        "runtime_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
        "support_package_accepted",
        "support_package_approved",
        "support_package_ready",
        "support_package_supported",
        "package_label_accepted",
        "package_label_approved",
        "package_label_ready",
        "support_label_accepted",
        "support_label_approved",
        "support_label_ready",
    )
)
POSITIVE_TEXT_VALUES = frozenset(
    (
        "1",
        "accepted",
        "allowed",
        "approved",
        "available",
        "complete",
        "completed",
        "enabled",
        "present",
        "promoted",
        "ready",
        "supported",
        "true",
        "yes",
    )
)
OPTIONAL_WINDOW_CHECK_FALSE_FLAGS = frozenset(
    (
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
    )
)
APPROVED_REJECTED_START_TRIPLET_ALTERNATIVE = "check_join_in_progress_rejected_start"
REQUIRED_WINDOW_CHECK_SIBLING_ARTIFACTS = (
    (("manifest",), "window-manifest.env"),
    (("request_pack",), "window-request.json"),
    (("observer_env",), "observer-window.env"),
    (("operator_approval_receipt",), "operator-approval-receipt.json"),
    (("preflight", "pre"), "preflight-pre.json"),
    (("preflight", "post"), "preflight-post.json"),
)
REQUIRED_IMPLICIT_SIBLING_ARTIFACTS = (
    ("operator_approval_request_md", "operator-approval-request.md"),
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def output_artifact_identity(payload: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> dict[str, str]:
    identity_without_hash = {
        "artifact_kind": SCHEMA,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": payload,
    }
    return {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-summary",
        required=True,
        type=Path,
        help="Copied/offline JSON summary produced by analyze_runtime_observer_log.py.",
    )
    parser.add_argument(
        "--window-manifest-check",
        required=True,
        type=Path,
        help="JSON report produced by check_player_identity_runtime_principal_lifecycle_window_manifest.py.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Manifest JSON output path.")
    parser.add_argument(
        "--reviewed-by",
        required=True,
        help="Reviewer token/name recorded under approval.reviewed_by.",
    )
    parser.add_argument(
        "--review-note",
        required=True,
        help="Short review note recorded under approval.review_note.",
    )
    return parser.parse_args()


def load_summary(path: Path) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, "--source-summary")
    resolved = protected_paths.reject_protected_input_path(path, "--source-summary")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{resolved}: source summary does not exist") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: source summary top-level JSON must be an object")
    return payload


def load_window_check(path: Path) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, "--window-manifest-check")
    resolved = protected_paths.reject_protected_input_path(path, "--window-manifest-check")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{resolved}: window manifest check does not exist") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: window manifest check top-level JSON must be an object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reject_if_forbidden_review_text(value: str, label: str) -> None:
    if not value.strip():
        raise SystemExit(f"{label} must not be empty")
    if FORBIDDEN_REVIEW_TEXT_RE.search(value):
        raise SystemExit(f"{label} contains identity/UE-internal terms that would not pass the privacy gate")


def path_is_copied_or_offline(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    return not protected_paths.protected_path_status(
        Path(path_text),
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    ).protected


def path_is_approved_offline_workspace(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text),
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected and status.approved_offline_workspace


def normalized_flag_key(key: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", key)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def positive_flag_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in POSITIVE_TEXT_VALUES
    return False


def iter_json_object_entries(value: Any, path: str = "$") -> list[tuple[str, str, Any]]:
    if isinstance(value, dict):
        entries: list[tuple[str, str, Any]] = []
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            entries.append((child_path, key_text, child))
            entries.extend(iter_json_object_entries(child, child_path))
        return entries
    if isinstance(value, list):
        entries = []
        for index, child in enumerate(value):
            entries.extend(iter_json_object_entries(child, f"{path}[{index}]"))
        return entries
    return []


def validate_source_summary_non_evidence_aliases(summary: dict[str, Any]) -> None:
    schema = summary.get("schema")
    if isinstance(schema, str) and schema != SUMMARY_SCHEMA:
        reason = NON_EVIDENCE_SOURCE_SCHEMA_BLOCKERS.get(schema)
        if reason is None:
            reason = approved_evidence_checker.non_approved_runtime_evidence_schema_alias_reason(schema)
        if reason is not None:
            raise SystemExit(f"--source-summary {reason}")
    if summary.get("ready") is not False:
        raise SystemExit("--source-summary ready must remain false; analyzer summaries are not approval artifacts")
    if summary.get("runtime_evidence_ready") is not False:
        raise SystemExit("--source-summary runtime_evidence_ready must remain false before approved review")
    if summary.get("approved_runtime_evidence") not in (None, False):
        raise SystemExit("--source-summary approved_runtime_evidence must not be true")
    for key_path, key, value in iter_json_object_entries(summary):
        normalized = normalized_flag_key(key)
        if approved_evidence_checker.source_overclaim_alias_key_is_forbidden(key):
            raise SystemExit(
                f"--source-summary {key_path} is a source_overclaim/status alias, not runtime evidence"
            )
        if normalized in SOURCE_SUMMARY_FORBIDDEN_POSITIVE_FLAG_KEYS and positive_flag_value(value):
            raise SystemExit(f"--source-summary {key_path} must not claim approved runtime evidence/readiness")
    positive_claim = approved_evidence_checker.find_positive_capability_claim(summary, "$.source_summary")
    if positive_claim is not None:
        _, claim_path = positive_claim
        if claim_path.startswith("$.source_summary."):
            claim_path = "$." + claim_path.removeprefix("$.source_summary.")
        elif claim_path == "$.source_summary":
            claim_path = "$"
        raise SystemExit(f"--source-summary {claim_path} must not claim readiness/support/package evidence")
    role_alias_claim = approved_evidence_checker.find_lifecycle_role_alias_claim(summary, "$.source_summary")
    if role_alias_claim is not None:
        _, claim_path = role_alias_claim
        if claim_path.startswith("$.source_summary."):
            claim_path = "$." + claim_path.removeprefix("$.source_summary.")
        elif claim_path == "$.source_summary":
            claim_path = "$"
        raise SystemExit(f"--source-summary {claim_path} is a lifecycle role alias, not exact runtime observer evidence")
    promotion_gate = summary.get("promotion_gate")
    if isinstance(promotion_gate, dict):
        for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
            if key in promotion_gate and promotion_gate.get(key) is not False:
                raise SystemExit(f"--source-summary promotion_gate.{key} must remain false")


def validate_source_summary(summary: dict[str, Any]) -> None:
    validate_source_summary_non_evidence_aliases(summary)
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise SystemExit(f"--source-summary schema must be {SUMMARY_SCHEMA}")
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("--source-summary must include evidence object from analyzer")
    if evidence.get("kind") != "runtime-observer-log":
        raise SystemExit("--source-summary evidence.kind must be runtime-observer-log")
    if evidence.get("server_paths_allowed") is not False:
        raise SystemExit("--source-summary must be generated without --allow-server-path")
    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        raise SystemExit("--source-summary must include runtime object")
    if runtime.get("broad_process_event_trace_lines") != 0:
        raise SystemExit("--source-summary must not include broad ProcessEvent detour trace lines")
    sources = evidence.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise SystemExit("--source-summary evidence.sources must contain exactly one copied/offline log")
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not path_is_copied_or_offline(source.get("path")):
            raise SystemExit(
                "--source-summary evidence.sources "
                f"[{index}].path must point to copied/offline evidence, not a protected server path"
            )
        if not path_is_approved_offline_workspace(source.get("path")):
            raise SystemExit(
                "--source-summary evidence.sources "
                f"[{index}].path must point under /servidor/ark/workspace-offline"
            )
    modules = summary.get("modules")
    if not isinstance(modules, dict):
        raise SystemExit("--source-summary must include modules object")
    module_names = set(modules)
    if module_names != {EXPECTED_MODULE}:
        observed = ", ".join(sorted(module_names)) or "<none>"
        raise SystemExit(
            "--source-summary modules must contain only "
            f"{EXPECTED_MODULE}; observed: {observed}"
        )


def validate_check_join_rejected_start_triplet(summary: dict[str, Any]) -> None:
    modules = summary.get("modules")
    module = modules.get(EXPECTED_MODULE) if isinstance(modules, dict) else None
    if not isinstance(module, dict):
        raise SystemExit("--source-summary player_principal_lifecycle module missing")
    if approved_evidence_checker.diagnostic_material_present(module):
        raise SystemExit("--source-summary diagnostic candidates are not approved runtime evidence")
    selection = approved_evidence_checker.strict_lifecycle_triplet_selection(
        module.get("observed_event_cases")
    )
    alternative = approved_evidence_checker.matching_observed_event_alternative(
        module.get("observed_event_cases")
    )
    if (
        not isinstance(alternative, dict)
        or alternative.get("id") != APPROVED_REJECTED_START_TRIPLET_ALTERNATIVE
    ):
        if selection.get("candidate_count") != 0:
            raise SystemExit(
                "--source-summary observed_event_cases must contain exactly one approved "
                "CheckJoinInProgress rejected-start lifecycle triplet"
            )
        raise SystemExit(
            "--source-summary observed_event_cases must match approved "
            "CheckJoinInProgress rejected-start lifecycle triplet"
        )
    if not approved_evidence_checker.strict_lifecycle_triplet_is_exact(selection):
        raise SystemExit(
            "--source-summary observed_event_cases must contain exactly one approved "
            "CheckJoinInProgress rejected-start lifecycle triplet"
        )
    if module.get("complete_lifecycle_event_triplet_candidate_present") is not True:
        raise SystemExit("--source-summary complete lifecycle triplet candidate must be present")
    if module.get("complete_accepted_lifecycle_role_triplet_present") is not True:
        raise SystemExit("--source-summary accepted lifecycle role triplet must be complete")


def window_artifact(window: dict[str, Any], keys: tuple[str, ...], label: str) -> dict[str, Any]:
    value: Any = window
    for key in keys:
        if not isinstance(value, dict):
            raise SystemExit(f"--window-manifest-check {label} must be an object")
        value = value.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"--window-manifest-check {label} must be an object")
    return value


def approved_offline_artifact_path(path_text: Any, label: str) -> Path:
    if not isinstance(path_text, str) or not path_text:
        raise SystemExit(f"--window-manifest-check {label}.path missing")
    path = Path(path_text).expanduser()
    symlink = protected_paths.first_symlink_component(path)
    if symlink is not None:
        raise SystemExit(f"--window-manifest-check {label}.path must not contain a symlink: {symlink}")
    status = protected_paths.protected_path_status(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        raise SystemExit(f"--window-manifest-check {label}.path must not read protected server root: {status.resolved}")
    if not status.approved_offline_workspace:
        raise SystemExit(f"--window-manifest-check {label}.path must be under /servidor/ark/workspace-offline")
    if not status.resolved.is_file():
        raise SystemExit(f"--window-manifest-check {label}.path does not exist: {status.resolved}")
    return status.resolved


def validate_artifact_binding(artifact: dict[str, Any], label: str, expected_path: Path) -> None:
    actual_path = approved_offline_artifact_path(artifact.get("path"), label)
    if actual_path != expected_path.expanduser().resolve():
        raise SystemExit(
            f"--window-manifest-check {label}.path must be the exact sibling artifact "
            f"{expected_path.name}"
        )
    sha256 = artifact.get("sha256")
    if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
        raise SystemExit(f"--window-manifest-check {label}.sha256 must be a lowercase SHA256")
    actual_sha256 = sha256_file(actual_path)
    if sha256 != actual_sha256:
        raise SystemExit(f"--window-manifest-check {label}.sha256 does not match the sibling file")


def validate_window_check_sibling_bindings(window: dict[str, Any], summary: dict[str, Any]) -> None:
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("--source-summary must include evidence.sources[0]")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        raise SystemExit("--window-manifest-check must include copied_log object")
    copied_log = approved_offline_artifact_path(copied.get("path"), "copied_log")
    source_path = Path(str(sources[0].get("path", ""))).expanduser().resolve()
    if copied_log != source_path:
        raise SystemExit("--window-manifest-check copied_log.path must match source summary path")
    validate_artifact_binding(copied, "copied_log", copied_log)
    run_id = window.get("run_id")
    if not isinstance(run_id, str) or copied_log.parent.name != run_id:
        raise SystemExit("--window-manifest-check run_id must match copied log sibling directory")
    if copied_log.parts[-3:] != ("live-validation-logs", run_id, "Obelisk.log"):
        raise SystemExit("--window-manifest-check copied_log.path must be live-validation-logs/<run-id>/Obelisk.log")
    sidecar_dir = copied_log.parent
    for keys, filename in REQUIRED_WINDOW_CHECK_SIBLING_ARTIFACTS:
        label = ".".join(keys)
        validate_artifact_binding(
            window_artifact(window, keys, label),
            label,
            sidecar_dir / filename,
        )
    for label, filename in REQUIRED_IMPLICIT_SIBLING_ARTIFACTS:
        approved_offline_artifact_path(str(sidecar_dir / filename), label)


def validate_window_check(window: dict[str, Any], summary: dict[str, Any]) -> None:
    if window.get("schema") != WINDOW_CHECK_SCHEMA:
        raise SystemExit(f"--window-manifest-check schema must be {WINDOW_CHECK_SCHEMA}")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        raise SystemExit("--window-manifest-check must be ready")
    if window.get("post_window_replay") is not True:
        raise SystemExit("--window-manifest-check must be generated with --post-window-replay")
    for key in (
        "promotion_ready",
        "public_header_allowed",
        "public_abi_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "request_pack_counts_as_approved_runtime_evidence",
        "observer_env_counts_as_approved_runtime_evidence",
        "operator_request_counts_as_approved_runtime_evidence",
        "copied_log_metadata_counts_as_approved_runtime_evidence",
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "bundle_output_counts_as_approved_runtime_evidence",
        "preflight_counts_as_approved_runtime_evidence",
        "window_manifest_counts_as_approved_runtime_evidence",
        "completed_receipt_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
    ):
        if key in OPTIONAL_WINDOW_CHECK_FALSE_FLAGS and key not in window:
            continue
        if window.get(key) is not False:
            raise SystemExit(f"--window-manifest-check {key} must remain false")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        raise SystemExit("--window-manifest-check must include copied_log object")
    manifest = window.get("manifest")
    if not isinstance(manifest, dict) or not manifest.get("path") or not manifest.get("sha256"):
        raise SystemExit("--window-manifest-check must include manifest path and sha256")
    for key in ("request_pack", "observer_env", "preflight"):
        if not isinstance(window.get(key), dict):
            raise SystemExit(f"--window-manifest-check must include {key} object")
    if copied.get("path_status") != EXPECTED_COPIED_LOG_PATH_STATUS:
        raise SystemExit("--window-manifest-check copied_log.path_status must be approved_offline_workspace")
    if not path_is_approved_offline_workspace(copied.get("path")):
        raise SystemExit("--window-manifest-check copied_log.path must point under /servidor/ark/workspace-offline")
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("--source-summary must include evidence.sources[0]")
    source = sources[0]
    if Path(str(copied.get("path", ""))).expanduser().resolve() != Path(str(source.get("path", ""))).expanduser().resolve():
        raise SystemExit("--window-manifest-check copied_log.path must match source summary path")
    if copied.get("sha256") != source.get("sha256"):
        raise SystemExit("--window-manifest-check copied_log.sha256 must match source summary sha256")
    evidence_commit = evidence.get("obelisk_commit") if isinstance(evidence, dict) else None
    if window.get("obelisk_commit") != evidence_commit:
        raise SystemExit("--window-manifest-check obelisk_commit must match source summary obelisk_commit")
    if window.get("approval") not in {
        APPROVAL_TEXT,
        STANDING_LAUNCH_AUTHORITY_APPROVAL_TEXT,
    }:
        raise SystemExit(
            "--window-manifest-check approval must preserve a bound runtime window authority"
        )
    for key in ("approved_window", "actual_capture", "rollback_window"):
        value = window.get(key)
        if not isinstance(value, dict) or not value.get("start_utc") or not value.get("end_utc"):
            raise SystemExit(f"--window-manifest-check must include {key}.start_utc and {key}.end_utc")
    if window.get("notice_sent") not in {"true", "false", "not_applicable"}:
        raise SystemExit("--window-manifest-check notice_sent must be true, false, or not_applicable")
    if window.get("user_policy") == "operator_approved_beta_users" and window.get("notice_sent") != "true":
        raise SystemExit("--window-manifest-check beta user policy requires notice_sent=true")
    if window.get("log_budget") != "10":
        raise SystemExit("--window-manifest-check log_budget must be 10")
    if not isinstance(window.get("non_claims"), list) or len(window["non_claims"]) < 3:
        raise SystemExit("--window-manifest-check must include fixed non_claims")


def build_manifest(
    summary: dict[str, Any],
    window: dict[str, Any],
    *,
    reviewed_by: str,
    review_note: str,
) -> dict[str, Any]:
    manifest = {
        "schema": SCHEMA,
        "artifact_status": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_STATUS,
        "readiness_classification": APPROVED_RUNTIME_EVIDENCE_CLASSIFICATION,
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "approval": {
            "runtime_evidence_reviewed": True,
            "reviewed_by": reviewed_by,
            "review_note": review_note,
            "runtime_work_authorized_by_this_manifest": False,
            "server_operations_authorized_by_this_manifest": False,
            "publication_authorized_by_this_manifest": False,
            "discord_authorized_by_this_manifest": False,
        },
        "operational_window": {
            "schema": window.get("schema"),
            "ready": window.get("ready"),
            "operational_window_manifest_ready": window.get("operational_window_manifest_ready"),
            "run_id": window.get("run_id"),
            "obelisk_commit": window.get("obelisk_commit"),
            "approval": window.get("approval"),
            "approved_window": window.get("approved_window"),
            "actual_capture": window.get("actual_capture"),
            "rollback_window": window.get("rollback_window"),
            "target": window.get("target"),
            "manifest": window.get("manifest"),
            "copied_log": window.get("copied_log"),
            "request_pack": window.get("request_pack"),
            "observer_env": window.get("observer_env"),
            "operator_approval_receipt": window.get("operator_approval_receipt"),
            "preflight": window.get("preflight"),
            "posture": window.get("posture"),
            "rollback": window.get("rollback"),
            "log_budget": window.get("log_budget"),
            "claims": window.get("claims"),
            "user_policy": window.get("user_policy"),
            "notice_sent": window.get("notice_sent"),
            "promotion_ready": window.get("promotion_ready"),
            "public_header_allowed": window.get("public_header_allowed"),
            "public_abi_ready": window.get("public_abi_ready"),
            "public_sdk_ready": window.get("public_sdk_ready"),
            "v1_completion_ready": window.get("v1_completion_ready"),
            "runtime_ready": window.get("runtime_ready"),
            "stable_claim_allowed": window.get("stable_claim_allowed"),
            "request_pack_counts_as_approved_runtime_evidence": window.get(
                "request_pack_counts_as_approved_runtime_evidence"
            ),
            "preflight_counts_as_approved_runtime_evidence": window.get(
                "preflight_counts_as_approved_runtime_evidence"
            ),
            "window_manifest_counts_as_approved_runtime_evidence": window.get(
                "window_manifest_counts_as_approved_runtime_evidence"
            ),
            "completed_receipt_counts_as_approved_runtime_evidence": window.get(
                "completed_receipt_counts_as_approved_runtime_evidence"
            ),
            "approved_runtime_evidence_present": window.get("approved_runtime_evidence_present"),
            "approved_runtime_evidence_ready": window.get("approved_runtime_evidence_ready"),
            "non_claims": window.get("non_claims"),
        },
        "source_summary": summary,
        "consumer_boundary_cases": [
            {
                "case": "stale_after_logout",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "result": "fail_closed",
                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                "runtime_observed": False,
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_runtime_observer": True,
            "player_identifiers_logged": False,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "runtime_evidence_ready": True,
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": REQUIRED_NON_CLAIMS,
    }
    run_id = str(window.get("run_id"))
    manifest["output_artifact_identity"] = output_artifact_identity(
        manifest,
        capture_id=run_id,
        evidence_pack_id=f"player-principal-lifecycle-{run_id}",
    )
    return manifest


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    protected_paths.reject_symlink_component(path, "--output")
    protected_paths.reject_server_root_write_without_opt_in(path, "--output")
    resolved = protected_paths.reject_protected_output_path(
        path,
        "--output",
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd = -1
    temp_name = ""
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{resolved.name}.",
            suffix=".tmp",
            dir=str(resolved.parent),
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(text)
        os.replace(temp_name, resolved)
    finally:
        if fd != -1:
            os.close(fd)
        if temp_name:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def validate_built_manifest_with_consume_checker(manifest: dict[str, Any]) -> None:
    validation = approved_evidence_checker.validate_manifest(manifest, check_mode="consume")
    if validation.blockers:
        summaries: list[str] = []
        for blocker in validation.blockers:
            fields = [str(blocker.get("reason")), str(blocker.get("label"))]
            for key in ("expected", "actual", "path"):
                value = blocker.get(key)
                if isinstance(value, str):
                    fields.append(f"{key}={value}")
            summaries.append(" ".join(fields))
        raise SystemExit(
            "generated approved manifest failed consume checker: "
            + "; ".join(sorted(summaries))
        )


def main() -> int:
    args = parse_args()
    reject_if_forbidden_review_text(args.reviewed_by, "--reviewed-by")
    reject_if_forbidden_review_text(args.review_note, "--review-note")
    summary = load_summary(args.source_summary)
    window = load_window_check(args.window_manifest_check)
    validate_source_summary(summary)
    validate_check_join_rejected_start_triplet(summary)
    validate_window_check(window, summary)
    validate_window_check_sibling_bindings(window, summary)
    manifest = build_manifest(
        summary,
        window,
        reviewed_by=args.reviewed_by.strip(),
        review_note=args.review_note.strip(),
    )
    validate_built_manifest_with_consume_checker(manifest)
    write_json_atomic(args.output, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
