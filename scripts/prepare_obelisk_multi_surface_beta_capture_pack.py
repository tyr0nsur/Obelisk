#!/usr/bin/env python3
"""Prepare an offline multi-surface beta capture pack.

The pack is a reproducible checklist for a future beta runtime window. This tool writes
only to the requested offline output directory, never touches ARK servers or Discord, and
never claims runtime evidence, SDK progress, public readiness, or stable readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from plan_obelisk_multi_surface_beta_capture import (
    BROAD_BETA_CAPTURE_WORKSHEET_FILE,
    BROAD_BETA_CAPTURE_WORKSHEET_ID,
    BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
    CURRENT_ROUTE_BLOCKER,
    NON_CLAIM_FLAGS,
    REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
    SAFE_MAP_RE,
    SCHEMA as PLAN_SCHEMA,
    SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS,
    SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA,
    SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS,
    SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA,
    STRICT_PLAYER_PRINCIPAL_TRIPLET,
    attach_source_metadata,
    artifact_intake_constraints,
    beta_capture_worksheet_surface_rows,
    beta_capture_interaction_boundary,
    build_plan,
    candidate_only_metadata,
    no_flood_capture_policy,
    lifecycle_correlation_metadata,
    non_substitution_flags,
    parallel_capture_boundary,
    player_principal_window_composition,
    source_metadata_template,
    target_binding,
    target_binding_id,
    validate_token,
)


SCHEMA = "obelisk.multi-surface-beta-capture-pack.v1"
INTAKE_SCHEMA = "obelisk.multi-surface-beta-capture-artifact-intake.v1"
DEFAULT_RUN_ID_PREFIX = "multi-surface-beta-capture"
PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE = "permissions-admin-beta-capture-candidates.json"
PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATES_SCHEMA = (
    "obelisk.permissions-admin-beta-capture-candidates.v1"
)
PERMISSIONS_ADMIN_BETA_CAPTURE_REQUIRED_SURFACES = ("admin", "list_player", "kick_path")
PERMISSIONS_ADMIN_BETA_CAPTURE_SURFACE_TARGETS = {
    "admin": "permissions_admin_admin_surface",
    "list_player": "ShooterPlayerController.ServerListPlayers",
    "kick_path": "ShooterPlayerController.ServerKickPlayer",
}
PERMISSIONS_ADMIN_BETA_CAPTURE_FALSE_KEYS = (
    "accepted_for_planning",
    "accepted_runtime_evidence_ready",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "approved_runtime_principal_lifecycle_evidence",
    "candidate_capture_checker_accepted",
    "clears_approved_runtime_evidence_missing",
    "counts_as_approved_runtime_evidence",
    "counts_as_p0_progress",
    "counts_as_public_readiness",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "evidence_accepted",
    "evidence_ready",
    "identity_evidence_accepted",
    "identity_runtime_evidence_satisfied",
    "own_checker_accepted",
    "permissions_admin_route_ready",
    "player_identity_evidence_accepted",
    "player_identity_runtime_evidence_ready",
    "player_identity_runtime_evidence_satisfied",
    "player_principal_triplet_satisfied",
    "player_principal_runtime_evidence_satisfied",
    "plugin_hub_publication_ready",
    "plugin_hub_ready",
    "promotion_ready",
    "publication_authorized",
    "public_api_ready",
    "public_contract_ready",
    "public_abi_ready",
    "public_header_allowed",
    "public_or_runtime_accounting_allowed",
    "public_ready",
    "public_readiness_ready",
    "public_route_ready",
    "public_sdk_ready",
    "publication_ready",
    "replaces_player_principal_evidence",
    "route_ready",
    "runtime_capture_authorized",
    "runtime_evidence_accepted",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_evidence_satisfied",
    "runtime_ready",
    "sdk_p0_progress_ready",
    "sdk_progress_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_ready",
    "stable_release_ready",
    "stable_sdk_ready",
    "v1_completion_evidence",
)
PERMISSIONS_ADMIN_BETA_CAPTURE_ZERO_KEYS = (
    "approved_runtime_evidence_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "evidence_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_progress",
    "public_sdk_progress",
    "runtime_evidence_progress_contribution",
    "sdk_progress",
    "sdk_progress_contribution",
)
PERMISSIONS_ADMIN_BETA_CAPTURE_NON_CLAIM = (
    "admin/list-player/kick-path beta captures are candidate/debug queue metadata only; "
    "they do not replace the required player-principal triplet, approved runtime evidence, "
    "public SDK readiness, runtime readiness, stable readiness, SDK/P0 progress, or route progress"
)
NON_AUTHORIZATION = (
    "offline candidate capture pack only; this artifact does not authorize Discord, "
    "server operations, marker/env changes, live log reads, starts, restarts, runtime "
    "capture, approved runtime evidence, public SDK readiness, stable SDK readiness, "
    "SDK/P0 progress, Plugin Hub readiness, publication, or release claims"
)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_run_id(instance: str, map_name: str) -> str:
    return f"{DEFAULT_RUN_ID_PREFIX}-{utc_timestamp()}-{instance}-{map_name}"


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_artifact_count(plan: dict[str, Any]) -> int:
    return sum(len(surface["capture_artifacts"]) for surface in plan["capture_surfaces"])


def permissions_admin_beta_capture_false_zero_flags() -> dict[str, bool | int]:
    flags: dict[str, bool | int] = {
        key: False for key in PERMISSIONS_ADMIN_BETA_CAPTURE_FALSE_KEYS
    }
    flags.update({key: 0 for key in PERMISSIONS_ADMIN_BETA_CAPTURE_ZERO_KEYS})
    return flags


def permissions_admin_beta_capture_candidate(surface_id: str) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "id": surface_id,
        "target": PERMISSIONS_ADMIN_BETA_CAPTURE_SURFACE_TARGETS[surface_id],
        "artifact_status": "candidate_only",
        "candidate_only": True,
        "debug_only": True,
        "requires_own_checker_acceptance": True,
        "requires_player_principal_triplet": True,
    }
    candidate.update(permissions_admin_beta_capture_false_zero_flags())
    return candidate


def permissions_admin_beta_capture_candidates() -> dict[str, Any]:
    artifact: dict[str, Any] = {
        "schema": PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATES_SCHEMA,
        "artifact_kind": "beta_capture_candidate",
        "artifact_status": "candidate_only",
        "candidate_only": True,
        "debug_only": True,
        "requires_own_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "non_claim": PERMISSIONS_ADMIN_BETA_CAPTURE_NON_CLAIM,
        "candidate_debug_surfaces": [
            permissions_admin_beta_capture_candidate(surface_id)
            for surface_id in PERMISSIONS_ADMIN_BETA_CAPTURE_REQUIRED_SURFACES
        ],
    }
    artifact.update(permissions_admin_beta_capture_false_zero_flags())
    return artifact


def broad_beta_capture_candidate_worksheet(plan: dict[str, Any]) -> dict[str, Any]:
    broad_path = plan["broad_beta_capture_pack_path"]
    rows = beta_capture_worksheet_surface_rows(plan["capture_surfaces"], plan["target"])
    worksheet = {
        "schema": BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
        "id": BROAD_BETA_CAPTURE_WORKSHEET_ID,
        "file": BROAD_BETA_CAPTURE_WORKSHEET_FILE,
        "artifact_kind": "beta_capture_candidate_worksheet",
        "artifact_status": "candidate_only",
        "status": "candidate_worksheet_template",
        "worksheet_status": "blank_template_for_redacted_metadata",
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "broad_beta_capture_pack_path_id": broad_path["id"],
        "surface_ids": broad_path["surface_ids"],
        "action_group_ids": broad_path["action_group_ids"],
        "surface_count": len(broad_path["surface_ids"]),
        "worksheet_row_count": len(rows),
        "worksheet_rows": rows,
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "beta_capture_interaction_boundary": beta_capture_interaction_boundary(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(plan["target"]),
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "capture_constraints": {
            "same_approved_runtime_window_required": True,
            "exact_target_binding_required": True,
            "lifecycle_correlation_metadata_required": True,
            "lifecycle_correlation_metadata_is_non_evidence": True,
            "copy_to_offline_workspace_before_checker": True,
            "redaction_required_before_checker_intake": True,
            "candidate_artifact_presence_never_implies_checker_acceptance": True,
            "candidate_artifact_intake_cannot_replace_primary_runtime_evidence": True,
            "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence": True,
            "do_not_read_live_server_paths_from_pack": True,
            "do_not_send_discord": True,
            "do_not_restart_servers_from_pack": True,
            "do_not_change_markers_or_env_from_pack": True,
            "artifact_templates_only": True,
            "artifact_templates_must_stay_relative": True,
            "artifact_templates_must_stay_under_candidate_artifacts": True,
            "pack_authorizes_approved_runtime_window": False,
            "pack_authorizes_player_backed_window": False,
        },
        "non_authorization": NON_AUTHORIZATION,
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "source_present": False,
        "source_material_present": False,
        "candidate_only": True,
        "non_evidence": True,
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_discord_send": False,
        "authorizes_server_restart": False,
        "authorizes_marker_or_env_changes": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
    }
    return attach_source_metadata(worksheet, plan["target"])


def simultaneous_beta_capture_candidate_worksheet(plan: dict[str, Any]) -> dict[str, Any]:
    matrix = plan["parallel_beta_capture_side_lane_matrix"]
    rows = beta_capture_worksheet_surface_rows(
        plan["capture_surfaces"],
        plan["target"],
        surface_ids=SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS,
    )
    worksheet = {
        "schema": SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA,
        "id": SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID,
        "file": SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
        "artifact_kind": "simultaneous_beta_capture_candidate_worksheet",
        "artifact_status": "candidate_only",
        "status": "candidate_worksheet_template",
        "worksheet_status": "blank_template_for_redacted_parallel_side_lane_metadata",
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "parallel_beta_capture_matrix_id": matrix["id"],
        "side_lane_capture_queue_id": plan["side_lane_capture_queue"]["id"],
        "surface_ids": list(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS),
        "action_group_ids": list(SIMULTANEOUS_BETA_CAPTURE_ACTION_GROUP_IDS),
        "surface_count": len(SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS),
        "worksheet_row_count": len(rows),
        "worksheet_rows": rows,
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(plan["target"]),
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "capture_constraints": {
            "same_approved_runtime_window_required": True,
            "exact_target_binding_required": True,
            "lifecycle_correlation_metadata_required": True,
            "lifecycle_correlation_metadata_is_non_evidence": True,
            "copy_to_offline_workspace_before_checker": True,
            "redaction_required_before_checker_intake": True,
            "candidate_artifact_presence_never_implies_checker_acceptance": True,
            "candidate_artifact_intake_cannot_replace_primary_runtime_evidence": True,
            "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence": True,
            "do_not_read_live_server_paths_from_pack": True,
            "do_not_send_discord": True,
            "do_not_restart_servers_from_pack": True,
            "do_not_change_markers_or_env_from_pack": True,
            "artifact_templates_only": True,
            "artifact_templates_must_stay_relative": True,
            "artifact_templates_must_stay_under_candidate_artifacts": True,
            "simultaneous_side_lane_rows_are_candidate_only": True,
            "mission_rows_are_copied_bool_candidate_only": True,
            "pack_authorizes_approved_runtime_window": False,
            "pack_authorizes_player_backed_window": False,
        },
        "non_authorization": NON_AUTHORIZATION,
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "source_present": False,
        "source_material_present": False,
        "candidate_only": True,
        "non_evidence": True,
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "simultaneous_side_lane_rows": True,
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_discord_send": False,
        "authorizes_server_restart": False,
        "authorizes_marker_or_env_changes": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
    }
    return attach_source_metadata(worksheet, plan["target"])


def single_player_parallel_capture_candidate_worksheet(plan: dict[str, Any]) -> dict[str, Any]:
    sequence = plan["single_player_parallel_capture_sequence"]
    rows = beta_capture_worksheet_surface_rows(
        plan["capture_surfaces"],
        plan["target"],
        surface_ids=SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS,
    )
    worksheet = {
        "schema": SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA,
        "id": SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID,
        "file": SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
        "artifact_kind": "single_player_parallel_capture_candidate_worksheet",
        "artifact_status": "candidate_only",
        "status": "candidate_worksheet_template",
        "worksheet_status": "blank_template_for_redacted_primary_and_side_lane_metadata",
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "single_player_parallel_capture_sequence_id": sequence["id"],
        "single_player_route_summary": sequence["route_summary"],
        "surface_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
        "action_group_ids": list(SINGLE_PLAYER_PARALLEL_CAPTURE_ACTION_GROUP_IDS),
        "candidate_domain_ids": sequence["candidate_domain_ids"],
        "phase_count": sequence["phase_count"],
        "phase_rows": sequence["phases"],
        "primary_surface_id": "player_principal_lifecycle",
        "primary_row_index": 1,
        "side_lane_surface_ids": sequence["side_lane_surface_ids"],
        "surface_count": len(SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS),
        "worksheet_row_count": len(rows),
        "worksheet_rows": rows,
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": lifecycle_correlation_metadata(plan["target"]),
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "single_player_route_constraints": sequence["single_player_route_constraints"],
        "capture_constraints": {
            "primary_player_principal_phase_required": True,
            "primary_player_principal_phase_runs_first": True,
            "side_lane_phases_optional_after_primary": True,
            "same_approved_runtime_window_required": True,
            "exact_target_binding_required": True,
            "lifecycle_correlation_metadata_required": True,
            "lifecycle_correlation_metadata_is_non_evidence": True,
            "copy_to_offline_workspace_before_checker": True,
            "redaction_required_before_checker_intake": True,
            "candidate_artifact_presence_never_implies_checker_acceptance": True,
            "candidate_artifact_intake_cannot_replace_primary_runtime_evidence": True,
            "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence": True,
            "do_not_read_live_server_paths_from_pack": True,
            "do_not_send_discord": True,
            "do_not_restart_servers_from_pack": True,
            "do_not_change_markers_or_env_from_pack": True,
            "artifact_templates_only": True,
            "artifact_templates_must_stay_relative": True,
            "artifact_templates_must_stay_under_candidate_artifacts": True,
            "single_player_rows_are_candidate_only": True,
            "primary_row_does_not_replace_approved_evidence_checker": True,
            "pack_authorizes_approved_runtime_window": False,
            "pack_authorizes_player_backed_window": False,
        },
        "non_authorization": NON_AUTHORIZATION,
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "source_present": False,
        "source_material_present": False,
        "candidate_only": True,
        "non_evidence": True,
        "no_flood": True,
        "one_request_row_per_surface_per_approved_window": True,
        "single_player_sequence_rows": True,
        "primary_player_principal_row_included": True,
        "side_lane_rows_included": True,
        "correlation_metadata_required": True,
        "correlation_metadata_non_evidence": True,
        "requires_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "blocked_by_player_principal_evidence": True,
        "raw_player_text_retention_allowed": False,
        "raw_player_text_capture_allowed": False,
        "raw_chat_payload_capture_allowed": False,
        "private_player_data_retention_allowed": False,
        "secrets_or_webhook_retention_allowed": False,
        "authorizes_live_log_reads": False,
        "authorizes_runtime_capture": False,
        "authorizes_discord_send": False,
        "authorizes_server_restart": False,
        "authorizes_marker_or_env_changes": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "clears_approved_runtime_evidence_missing": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
    }
    return attach_source_metadata(worksheet, plan["target"])


def render_runbook(plan: dict[str, Any]) -> str:
    target = plan["target"]
    broad_path = plan["broad_beta_capture_pack_path"]
    excluded_surfaces = (
        ", ".join(plan["single_player_parallel_capture_sequence"]["excluded_surface_ids"])
        or "none"
    )
    lines = [
        "# Obelisk Multi-Surface Beta Capture Pack",
        "",
        f"Target: `{target['instance']}` / `{target['map']}`",
        f"Binding ID: `{plan['target_binding_id']}`",
        "",
        "Primary evidence gate:",
        f"- `{STRICT_PLAYER_PRINCIPAL_TRIPLET}`",
        "",
        "Server policy:",
        "- Keep at most two ARK servers running.",
        "- Keep servers running when practical so late testers can still produce logs.",
        "- This pack does not authorize starts, stops, restarts, marker changes, or env changes.",
        "- Any maintenance restart, marker change, env change, or live log read is outside this pack's authority.",
        "",
        "Privacy and claim boundaries:",
        "- Do not retain raw player text, secrets, webhook URLs, or private player data.",
        "- Candidate surfaces are debug material until their own checker accepts them.",
        "- Side-lanes remain non-counting before the player-principal blocker is solved.",
        "- Use one deduped request row per surface per approved window; source_present=false remains metadata, not evidence.",
        "- Side-lane groups are optional parallel candidate observations and stay non-evidence until their own checkers accept copied offline artifacts.",
        "- Use side-lane capture only alongside a separately approved player-principal lifecycle window; it cannot replace the primary triplet.",
        "- Bind every side-lane artifact to the same approved runtime window, instance, and map as the primary player-principal lifecycle evidence.",
        "- Lifecycle correlation metadata: required for side-lane rows; use one redacted side_lane_correlation_id, a primary_lifecycle_phase_anchor, an event-label-only primary_lifecycle_event_reference, an optional integer relative_lifecycle_offset_seconds, and an operator_sequence_index.",
        "- Lifecycle correlation metadata is non-evidence; it must not include raw log lines, player names, platform ids, chat text, IPs, secrets, or webhook URLs.",
        "- This pack does not count as runtime evidence, SDK progress, P0 progress, or readiness.",
        f"- Permissions/admin beta-capture candidate template: `{PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE}`.",
        f"- Broad candidate worksheet template: `{BROAD_BETA_CAPTURE_WORKSHEET_FILE}`.",
        f"- Simultaneous side-lane worksheet template: `{SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE}`.",
        (
            "- Admin/commands/dino/tribe/buff status-only candidate path: "
            f"`{broad_path['id']}`."
        ),
        (
            "- Admin/commands/dino/tribe/buff/inventory/item/transfer/mission parallel candidate matrix: "
            f"`{plan['parallel_beta_capture_side_lane_matrix']['id']}`."
        ),
        (
            "- Single-player parallel capture sequence: "
            f"`{plan['single_player_parallel_capture_sequence']['id']}`."
        ),
        (
            "- Single-player full-sequence worksheet template: "
            f"`{SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE}`."
        ),
        (
            "- Single-player route surfaces: "
            f"{', '.join(plan['single_player_parallel_capture_sequence']['surface_ids'])}."
        ),
        (
            "- Single-player route domains: "
            f"{', '.join(plan['single_player_parallel_capture_sequence']['candidate_domain_ids'])}."
        ),
        (
            "- Single-player route excludes: "
            f"{excluded_surfaces}."
        ),
        "- Single-player sequence phases keep raw player text disabled and redacted metadata only.",
        "- Single-player sequence is no-restart, no-Discord, non-evidence, non-progress, and cannot clear approved_runtime_evidence_missing.",
        (
            "- Target-bound offline checker command matrix: "
            f"`{plan['target_bound_checker_command_matrix']['id']}`."
        ),
        (
            "- Side-lane capture queue: "
            f"`{plan['side_lane_capture_queue']['id']}`."
        ),
        (
            "- Exact capture objectives: "
            f"{plan['exact_capture_objectives']['objective_count']} target-bound rows."
        ),
        "- No-flood policy: batch tester requests by action group and dedupe by approved window, target binding, surface, and side_lane_correlation_id.",
        "- Side-lane queue rows stay blocked by approved_runtime_evidence_missing and non-counting until the primary route and each row's checker accept.",
        "- Command placeholders resolve only to copied offline candidate-artifact templates.",
        "",
        "Broad status-only candidate path:",
        f"- Surfaces: {', '.join(broad_path['surface_ids'])}",
        "- Status: status-only candidate planning, not runtime evidence or readiness.",
        "- Required handling: copy redacted artifacts to an offline workspace before checker intake.",
        "- Correlation: use the same redacted session correlation id and lifecycle phase anchor for admin, commands, dino, tribe, and buff rows that belong to the approved player-principal window.",
        (
            "- Worksheet handling: fill only redacted metadata rows in "
            f"`{BROAD_BETA_CAPTURE_WORKSHEET_FILE}`; leave raw text and private data out."
        ),
        "",
        "Parallel side-lane candidate matrix:",
        f"- Surfaces: {', '.join(plan['parallel_beta_capture_side_lane_matrix']['surface_ids'])}",
        "- Status: status-only candidate planning, not runtime evidence or readiness.",
        "- Required binding: same approved player-principal lifecycle window, instance, and map.",
        "- Required handling: run each surface's own checker before making any surface claim.",
        "- Required correlation: match every side-lane observation to the primary lifecycle window using metadata-only fields, not raw player identity or log text.",
        "- Tester actions: do not require or authorize starts, stops, restarts, marker changes, env changes, live log reads, or Discord sends.",
        (
            "- Simultaneous worksheet: fill one redacted metadata row per side-lane surface in "
            f"`{SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE}`, including mission copied-bool."
        ),
        "",
        "Single-player parallel capture sequence:",
        f"- Phases: {', '.join(plan['single_player_parallel_capture_sequence']['action_group_ids'])}",
        f"- Route surfaces: {', '.join(plan['single_player_parallel_capture_sequence']['surface_ids'])}",
        f"- Route domains: {', '.join(plan['single_player_parallel_capture_sequence']['candidate_domain_ids'])}",
        f"- Excluded surfaces: {excluded_surfaces}",
        "- Status: status-only candidate sequencing, not runtime evidence or readiness.",
        "- Privacy: raw player text retention is not allowed; keep redacted metadata only.",
        "- Safety: no restarts, no Discord sends, no live log reads, no marker/env changes, and no approved_runtime_evidence_missing clearance.",
        (
            "- Worksheet handling: fill the primary player-principal row first, then optional "
            f"side-lane rows in `{SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE}`; "
            "leave raw log lines, chat text, player identity, secrets, and webhook URLs out."
        ),
        "",
        "Target-bound offline checker commands:",
        (
            "- Status: offline command templates only; they do not authorize live reads, "
            "Discord sends, marker/env changes, starts, stops, restarts, or runtime capture."
        ),
        "- Path arguments point under `candidate-artifacts/`; scalar inputs use `<read-text:...>` templates.",
        "",
        "Next-action groups:",
    ]
    for row in plan["target_bound_checker_command_matrix"]["rows"]:
        lines.extend(
            [
                f"- `{row['surface_id']}`",
                f"  - Target binding: `{row['target_binding_id']}`",
                f"  - Command template: `{' '.join(row['resolved_checker_command_template'])}`",
            ]
        )
    for group in plan["next_action_groups"]:
        lines.extend(
            [
                f"- {group['order']}. `{group['id']}`",
                f"  - Lead next action: {group['lead_next_action']}",
                f"  - Tester brief: {group['tester_brief']}",
                f"  - Surfaces: {', '.join(group['surface_ids'])}",
                f"  - Candidate artifact templates: {group['candidate_artifact_count']}",
                f"  - Approved window binding: {group['approved_runtime_window_binding']['target_binding_id']}",
            ]
        )
    lines.extend(
        [
            "",
            "Capture order:",
        ]
    )
    for surface in plan["capture_surfaces"]:
        lines.extend(
            [
                f"- {surface['priority']}. `{surface['id']}`",
                f"  - Objective: {surface['objective']}",
                f"  - Operator action: {surface['operator_action']}",
                f"  - Tester action: {surface['tester_action']}",
                f"  - Checker: `{surface['checker']}`",
                f"  - Offline checker command: `{' '.join(surface['post_capture_checker_command'])}`",
                f"  - Resolved offline command template: `{' '.join(surface['resolved_checker_command_template'])}`",
                f"  - Candidate artifact templates: {surface['candidate_artifact_count']}",
            ]
        )
        for artifact in surface["capture_artifacts"]:
            lines.append(f"    - `{artifact['id']}` -> `{artifact['path_template']}`")
    lines.extend(
        [
            "",
            "Closure:",
            "- Copy runtime material into an approved offline workspace before analysis.",
            "- Run the strict player-principal approved evidence checker first.",
            "- Treat every other surface as non-counting until its checker accepts it.",
        ]
    )
    return "\n".join(lines) + "\n"


def checker_matrix(plan: dict[str, Any]) -> dict[str, Any]:
    matrix = {
        "schema": "obelisk.multi-surface-beta-capture-checker-matrix.v1",
        "status": "candidate_only",
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "primary_checker": plan["required_primary_evidence"],
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": plan["lifecycle_correlation_metadata"],
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups": plan["next_action_groups"],
        "broad_beta_capture_pack_path": plan["broad_beta_capture_pack_path"],
        "parallel_beta_capture_side_lane_matrix": plan["parallel_beta_capture_side_lane_matrix"],
        "single_player_parallel_capture_sequence": plan[
            "single_player_parallel_capture_sequence"
        ],
        "target_bound_checker_command_matrix": plan["target_bound_checker_command_matrix"],
        "side_lane_capture_queue": plan["side_lane_capture_queue"],
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "source_metadata_required": True,
        "source_metadata": source_metadata_template(plan["target"]),
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "surfaces": [
            {
                "id": surface["id"],
                "priority": surface["priority"],
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
                "checker": surface["checker"],
                "objective": surface["objective"],
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "command": surface["post_capture_checker_command"],
                "candidate_artifact_count": surface["candidate_artifact_count"],
                "capture_artifacts": surface["capture_artifacts"],
                "required_checker_artifacts": surface["required_checker_artifacts"],
                "optional_candidate_artifacts": surface["optional_candidate_artifacts"],
                "checker_inputs_satisfied_by_artifacts": surface["checker_inputs_satisfied_by_artifacts"],
                "checker_command_bindings": surface["checker_command_bindings"],
                "resolved_checker_command_template": surface[
                    "resolved_checker_command_template"
                ],
                "resolved_checker_command_status": surface[
                    "resolved_checker_command_status"
                ],
                "target_bound_checker_command": surface[
                    "target_bound_checker_command"
                ],
                "candidate_classification": surface["candidate_classification"],
                "candidate_only_metadata": surface["candidate_only_metadata"],
                "no_flood_capture_policy": surface["no_flood_capture_policy"],
                "parallel_capture_boundary": surface["parallel_capture_boundary"],
                "player_principal_window_composition": surface["player_principal_window_composition"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": surface["correlation_metadata_required"],
                "correlation_metadata_non_evidence": surface[
                    "correlation_metadata_non_evidence"
                ],
                "operator_tester_action_metadata": surface["operator_tester_action_metadata"],
                "composition_role": surface["composition_role"],
                "optional_parallel_candidate_observation": surface[
                    "optional_parallel_candidate_observation"
                ],
                "parallel_with_player_principal_lifecycle_window": surface[
                    "parallel_with_player_principal_lifecycle_window"
                ],
                "non_substitution_flags": surface["non_substitution_flags"],
                "requires_checker_acceptance": True,
                "requires_player_principal_triplet": True,
                "blocked_by_player_principal_evidence": True,
                "candidate_capture_only": True,
                "source_present": False,
                "source_material_present": False,
                "side_lane": surface["side_lane"],
                "side_lane_non_counting": surface["side_lane_non_counting"],
                "current_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "replaces_player_principal_evidence": False,
                "replaces_player_principal_triplet": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_triplet": False,
                "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
                "player_principal_lifecycle_evidence_substitution_allowed": False,
                "approved_runtime_evidence_substitution_allowed": False,
                "primary_evidence_substitution_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "v1_completion_ready": False,
                "post_capture_boundary": (
                    "copy to an offline workspace and run the named checker; do not promote "
                    "candidate logs by presence alone"
                ),
            }
            for surface in plan["capture_surfaces"]
        ],
    }
    return attach_source_metadata(matrix, plan["target"])


def candidate_artifact_intake(plan: dict[str, Any]) -> dict[str, Any]:
    intake = {
        "schema": INTAKE_SCHEMA,
        "status": "candidate_artifact_intake_template",
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "required_primary_evidence": plan["required_primary_evidence"],
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": plan["lifecycle_correlation_metadata"],
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups": plan["next_action_groups"],
        "broad_beta_capture_pack_path": plan["broad_beta_capture_pack_path"],
        "parallel_beta_capture_side_lane_matrix": plan["parallel_beta_capture_side_lane_matrix"],
        "single_player_parallel_capture_sequence": plan[
            "single_player_parallel_capture_sequence"
        ],
        "target_bound_checker_command_matrix": plan["target_bound_checker_command_matrix"],
        "side_lane_capture_queue": plan["side_lane_capture_queue"],
        "candidate_artifact_count": candidate_artifact_count(plan),
        "capture_session_constraints": {
            "single_beta_session_intent": True,
            "copy_to_offline_workspace_before_analysis": True,
            "do_not_read_live_server_paths_from_pack": True,
            "do_not_send_discord": True,
            "do_not_restart_servers_from_pack": True,
            "do_not_change_markers_or_env_from_pack": True,
            "requires_checker_acceptance_before_any_surface_claim": True,
            "side_lanes_non_counting_before_player_principal": True,
            "artifacts_must_keep_target_binding": True,
            "artifact_templates_only": True,
            "artifact_templates_must_stay_relative": True,
            "artifact_templates_must_stay_under_candidate_artifacts": True,
            "artifact_templates_must_not_name_live_server_paths": True,
            "redaction_required_before_checker_intake": True,
            "candidate_artifact_presence_never_implies_checker_acceptance": True,
            "candidate_artifact_intake_cannot_replace_primary_runtime_evidence": True,
            "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence": True,
            "parallel_with_player_principal_lifecycle_window_planned": True,
            "side_surfaces_grouped_as_optional_parallel_candidate_observations": True,
            "side_surfaces_non_evidence_until_own_checker_acceptance": True,
            "same_approved_runtime_window_required": True,
            "side_lane_artifacts_must_share_player_principal_window": True,
            "operator_tester_action_metadata_required": True,
            "lifecycle_correlation_metadata_required": True,
            "lifecycle_correlation_metadata_is_non_evidence": True,
            "no_flood_single_request_row_per_surface": True,
            "operator_request_dedupe_required": True,
            "source_present_false_never_implies_runtime_evidence": True,
            "separate_player_backed_window_approval_required": True,
            "pack_authorizes_player_backed_window": False,
            "pack_authorizes_approved_runtime_window": False,
        },
        "artifact_intake_constraints": artifact_intake_constraints(),
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "source_metadata_required": True,
        "source_metadata": source_metadata_template(plan["target"]),
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "surfaces": [
            {
                "id": surface["id"],
                "priority": surface["priority"],
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
                "checker": surface["checker"],
                "command": surface["post_capture_checker_command"],
                "objective": surface["objective"],
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "candidate_classification": surface["candidate_classification"],
                "candidate_only_metadata": surface["candidate_only_metadata"],
                "no_flood_capture_policy": surface["no_flood_capture_policy"],
                "parallel_capture_boundary": surface["parallel_capture_boundary"],
                "player_principal_window_composition": surface["player_principal_window_composition"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": surface["correlation_metadata_required"],
                "correlation_metadata_non_evidence": surface[
                    "correlation_metadata_non_evidence"
                ],
                "operator_tester_action_metadata": surface["operator_tester_action_metadata"],
                "composition_role": surface["composition_role"],
                "optional_parallel_candidate_observation": surface[
                    "optional_parallel_candidate_observation"
                ],
                "parallel_with_player_principal_lifecycle_window": surface[
                    "parallel_with_player_principal_lifecycle_window"
                ],
                "non_substitution_flags": surface["non_substitution_flags"],
                "candidate_capture_only": True,
                "source_present": False,
                "source_material_present": False,
                "checker_inputs_satisfied_by_artifacts": surface["checker_inputs_satisfied_by_artifacts"],
                "checker_command_bindings": surface["checker_command_bindings"],
                "resolved_checker_command_template": surface[
                    "resolved_checker_command_template"
                ],
                "resolved_checker_command_status": surface[
                    "resolved_checker_command_status"
                ],
                "target_bound_checker_command": surface[
                    "target_bound_checker_command"
                ],
                "blocked_by_player_principal_evidence": True,
                "requires_player_principal_triplet": True,
                "requires_checker_acceptance": True,
                "side_lane": surface["side_lane"],
                "side_lane_non_counting": surface["side_lane_non_counting"],
                "current_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "candidate_artifact_count": surface["candidate_artifact_count"],
                "capture_artifacts": surface["capture_artifacts"],
                "required_checker_artifacts": surface["required_checker_artifacts"],
                "optional_candidate_artifacts": surface["optional_candidate_artifacts"],
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "replaces_player_principal_evidence": False,
                "replaces_player_principal_triplet": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_triplet": False,
                "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
                "player_principal_lifecycle_evidence_substitution_allowed": False,
                "approved_runtime_evidence_substitution_allowed": False,
                "primary_evidence_substitution_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "v1_completion_ready": False,
            }
            for surface in plan["capture_surfaces"]
        ],
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
    }
    return attach_source_metadata(intake, plan["target"])


def non_claim_manifest(plan: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "schema": "obelisk.multi-surface-beta-capture-non-claim-manifest.v1",
        "status": "non_authorizing_candidate_pack",
        "non_authorization": NON_AUTHORIZATION,
        "target": plan["target"],
        "target_binding": plan["target_binding"],
        "target_binding_id": plan["target_binding_id"],
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "required_primary_evidence": plan["required_primary_evidence"],
        "candidate_only_metadata": candidate_only_metadata(),
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": plan["lifecycle_correlation_metadata"],
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups": plan["next_action_groups"],
        "broad_beta_capture_pack_path": plan["broad_beta_capture_pack_path"],
        "parallel_beta_capture_side_lane_matrix": plan["parallel_beta_capture_side_lane_matrix"],
        "single_player_parallel_capture_sequence": plan[
            "single_player_parallel_capture_sequence"
        ],
        "target_bound_checker_command_matrix": plan["target_bound_checker_command_matrix"],
        "side_lane_capture_queue": plan["side_lane_capture_queue"],
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "candidate_artifact_count": candidate_artifact_count(plan),
        "side_lanes_non_counting_before_player_principal": True,
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "surface_non_claims": [
            {
                "id": surface["id"],
                "target_binding": surface["target_binding"],
                "target_binding_id": surface["target_binding_id"],
                "approved_runtime_window_binding": surface["approved_runtime_window_binding"],
                "operator_action": surface["operator_action"],
                "tester_action": surface["tester_action"],
                "candidate_classification": surface["candidate_classification"],
                "candidate_only_metadata": surface["candidate_only_metadata"],
                "no_flood_capture_policy": surface["no_flood_capture_policy"],
                "parallel_capture_boundary": surface["parallel_capture_boundary"],
                "player_principal_window_composition": surface["player_principal_window_composition"],
                "lifecycle_correlation_metadata": surface[
                    "lifecycle_correlation_metadata"
                ],
                "correlation_field_ids": surface["correlation_field_ids"],
                "correlation_metadata_required": surface["correlation_metadata_required"],
                "correlation_metadata_non_evidence": surface[
                    "correlation_metadata_non_evidence"
                ],
                "operator_tester_action_metadata": surface["operator_tester_action_metadata"],
                "composition_role": surface["composition_role"],
                "optional_parallel_candidate_observation": surface[
                    "optional_parallel_candidate_observation"
                ],
                "parallel_with_player_principal_lifecycle_window": surface[
                    "parallel_with_player_principal_lifecycle_window"
                ],
                "non_substitution_flags": surface["non_substitution_flags"],
                "candidate_capture_only": True,
                "source_present": False,
                "source_material_present": False,
                "blocked_by_player_principal_evidence": True,
                "requires_player_principal_triplet": True,
                "requires_checker_acceptance": True,
                "side_lane": surface["side_lane"],
                "side_lane_non_counting": surface["side_lane_non_counting"],
                "current_route_blocker": CURRENT_ROUTE_BLOCKER,
                "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
                "replaces_player_principal_triplet": False,
                "replaces_player_principal_evidence": False,
                "substitutes_for_player_principal_lifecycle_evidence": False,
                "substitutes_for_player_principal_lifecycle_triplet": False,
                "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
                "player_principal_lifecycle_evidence_substitution_allowed": False,
                "approved_runtime_evidence_substitution_allowed": False,
                "primary_evidence_substitution_allowed": False,
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "clears_approved_runtime_evidence_missing": False,
                "source_material_counts_as_evidence": False,
                "flood_capture_allowed": False,
                "unbounded_tester_requests_allowed": False,
                "discord_request_fanout_allowed": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "stable_sdk_ready": False,
                "v1_completion_ready": False,
                "plugin_hub_ready": False,
                "publication_ready": False,
            }
            for surface in plan["capture_surfaces"]
        ],
    }
    return attach_source_metadata(manifest, plan["target"])


def readme(plan: dict[str, Any], manifest_name: str) -> str:
    excluded_surfaces = (
        ", ".join(plan["single_player_parallel_capture_sequence"]["excluded_surface_ids"])
        or "none"
    )
    return (
        "This directory is an offline Obelisk beta capture preparation pack.\n\n"
        f"Plan schema: `{PLAN_SCHEMA}`\n"
        f"Pack manifest: `{manifest_name}`\n"
        f"Target: `{plan['target']['instance']}` / `{plan['target']['map']}`\n"
        f"Binding ID: `{plan['target_binding_id']}`\n"
        f"Primary evidence gate: `{STRICT_PLAYER_PRINCIPAL_TRIPLET}`\n\n"
        "Every candidate artifact must stay bound to the same approved runtime window, "
        "instance, and map as the primary player-principal lifecycle evidence.\n\n"
        "Lifecycle correlation metadata: use the same redacted side_lane_correlation_id, "
        "primary_lifecycle_phase_anchor, event-label-only primary_lifecycle_event_reference, "
        "optional integer relative_lifecycle_offset_seconds, and operator_sequence_index "
        "for side-lane rows in the approved window. This metadata is non-evidence and "
        "must not retain raw log lines, player identity, chat text, secrets, or webhooks.\n\n"
        "Candidate artifact intake template: `candidate-artifact-intake.json`\n\n"
        "Permissions/admin beta-capture candidate template: "
        f"`{PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE}`\n\n"
        "Broad admin/command/dino/tribe/buff candidate worksheet template: "
        f"`{BROAD_BETA_CAPTURE_WORKSHEET_FILE}`\n\n"
        "Simultaneous side-lane candidate worksheet template: "
        f"`{SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE}`\n\n"
        "Single-player full-sequence candidate worksheet template: "
        f"`{SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE}`\n\n"
        "Admin/commands/dino/tribe/buff status-only candidate path: "
        f"`{plan['broad_beta_capture_pack_path']['id']}`\n\n"
        "Admin/commands/dino/tribe/buff/inventory/item/transfer/mission parallel candidate matrix: "
        f"`{plan['parallel_beta_capture_side_lane_matrix']['id']}`\n\n"
        "Single-player parallel capture sequence: "
        f"`{plan['single_player_parallel_capture_sequence']['id']}`\n\n"
        "Single-player route surfaces: "
        f"{', '.join(plan['single_player_parallel_capture_sequence']['surface_ids'])}\n\n"
        "Single-player route domains: "
        f"{', '.join(plan['single_player_parallel_capture_sequence']['candidate_domain_ids'])}\n\n"
        "Single-player route excludes: "
        f"{excluded_surfaces}\n\n"
        "Single-player sequence is redacted metadata only, no-restart, no-Discord, "
        "non-evidence, non-progress, and cannot clear approved_runtime_evidence_missing.\n\n"
        "Target-bound offline checker command matrix: "
        f"`{plan['target_bound_checker_command_matrix']['id']}`\n\n"
        "Side-lane capture queue: "
        f"`{plan['side_lane_capture_queue']['id']}`\n\n"
        "Exact capture objectives are target-bound candidate rows only; "
        "source_present=false and no_flood=true remain non-evidence metadata.\n\n"
        "No-flood policy: batch tester requests by action group and dedupe by "
        "approved window, target binding, surface, and side_lane_correlation_id.\n\n"
        "Side-lane queue rows stay blocked by approved_runtime_evidence_missing and "
        "non-counting until the primary route and each row's checker accept.\n\n"
        "Checker command placeholders resolve only to copied offline candidate-artifact "
        "templates; scalar inputs use read-text templates and never live server paths.\n\n"
        "Concrete beta tester next-action groups are in `operator-runbook.md` and "
        "`checker-command-matrix.json`.\n\n"
        "The pack can prepare optional parallel side-lane capture alongside a separately "
        "approved player-principal lifecycle window, but it cannot authorize that window "
        "or replace player-principal evidence.\n\n"
        "The single-player sequence is redacted metadata only; raw player text retention "
        "is not allowed.\n\n"
        "It is not approved runtime evidence and does not authorize live operations.\n"
    )


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: Any) -> None:
    path.write_bytes(json_bytes(value))


def build_pack(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, bytes | str]]:
    plan_args = argparse.Namespace(instance=args.instance, map=args.map)
    plan = build_plan(plan_args)
    artifact_names = [
        "README.md",
        "candidate-artifact-intake.json",
        "checker-command-matrix.json",
        "manifest.json",
        "multi-surface-capture-plan.json",
        "non-claim-manifest.json",
        "operator-runbook.md",
        BROAD_BETA_CAPTURE_WORKSHEET_FILE,
        SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
        SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
        PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE,
    ]
    pack_metadata = {
        "schema": SCHEMA,
        "status": "candidate_capture_pack",
        "run_id": args.run_id,
        "target": plan["target"],
        "target_binding": target_binding(plan["target"], source="operator_cli"),
        "target_binding_id": target_binding_id(plan["target"]),
        "plan_target_binding": target_binding(plan["target"]),
        "plan_target_binding_id": target_binding_id(plan["target"]),
        "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
        "non_authorization": NON_AUTHORIZATION,
        "primary_evidence_required": plan["required_primary_evidence"],
        "candidate_surface_count": len(plan["capture_surfaces"]),
        "candidate_artifact_count": candidate_artifact_count(plan),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "side_lanes_non_counting_before_player_principal": True,
        "checker_matrix_includes_command_templates": True,
        "no_flood_capture_policy": no_flood_capture_policy(),
        "exact_capture_objectives": plan["exact_capture_objectives"],
        "source_present": False,
        "source_material_present": False,
        "source_material_counts_as_evidence": False,
        "flood_capture_allowed": False,
        "unbounded_tester_requests_allowed": False,
        "discord_request_fanout_allowed": False,
        "candidate_artifact_intake_included": True,
        "permissions_admin_beta_capture_candidate_template": (
            PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE
        ),
        "permissions_admin_beta_capture_candidate_schema": (
            PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATES_SCHEMA
        ),
        "permissions_admin_beta_capture_candidate_surfaces": list(
            PERMISSIONS_ADMIN_BETA_CAPTURE_REQUIRED_SURFACES
        ),
        "broad_beta_capture_candidate_worksheet_template": BROAD_BETA_CAPTURE_WORKSHEET_FILE,
        "broad_beta_capture_candidate_worksheet_schema": BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
        "broad_beta_capture_candidate_worksheet_id": BROAD_BETA_CAPTURE_WORKSHEET_ID,
        "broad_beta_capture_candidate_worksheet_included": True,
        "simultaneous_beta_capture_candidate_worksheet_template": (
            SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE
        ),
        "simultaneous_beta_capture_candidate_worksheet_schema": (
            SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA
        ),
        "simultaneous_beta_capture_candidate_worksheet_id": (
            SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID
        ),
        "simultaneous_beta_capture_candidate_worksheet_surfaces": list(
            SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS
        ),
        "simultaneous_beta_capture_candidate_worksheet_included": True,
        "single_player_parallel_capture_candidate_worksheet_template": (
            SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE
        ),
        "single_player_parallel_capture_candidate_worksheet_schema": (
            SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA
        ),
        "single_player_parallel_capture_candidate_worksheet_id": (
            SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID
        ),
        "single_player_parallel_capture_candidate_worksheet_surfaces": list(
            SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS
        ),
        "single_player_parallel_capture_candidate_worksheet_included": True,
        "candidate_only_metadata": candidate_only_metadata(),
        "beta_capture_interaction_boundary": beta_capture_interaction_boundary(),
        "parallel_capture_boundary": parallel_capture_boundary(),
        "player_principal_window_composition": player_principal_window_composition(),
        "lifecycle_correlation_metadata": plan["lifecycle_correlation_metadata"],
        "text_privacy_boundary": plan["text_privacy_boundary"],
        "non_substitution_flags": non_substitution_flags(),
        "next_action_groups_included": True,
        "next_action_groups": plan["next_action_groups"],
        "broad_beta_capture_pack_path": plan["broad_beta_capture_pack_path"],
        "parallel_beta_capture_side_lane_matrix": plan["parallel_beta_capture_side_lane_matrix"],
        "single_player_parallel_capture_sequence": plan[
            "single_player_parallel_capture_sequence"
        ],
        "target_bound_checker_command_matrix_included": True,
        "target_bound_checker_command_matrix": plan["target_bound_checker_command_matrix"],
        "side_lane_capture_queue_included": True,
        "side_lane_capture_queue": plan["side_lane_capture_queue"],
        "non_claim_flags": dict(NON_CLAIM_FLAGS),
        "artifacts": [],
        "artifact_names": artifact_names,
        "manifest_sha256_kind": "sha256_of_manifest_without_manifest_sha256_field",
    }
    pack_metadata = attach_source_metadata(pack_metadata, plan["target"])
    artifacts: dict[str, bytes | str] = {
        "multi-surface-capture-plan.json": json_bytes(plan),
        "candidate-artifact-intake.json": json_bytes(candidate_artifact_intake(plan)),
        "checker-command-matrix.json": json_bytes(checker_matrix(plan)),
        "non-claim-manifest.json": json_bytes(non_claim_manifest(plan)),
        "operator-runbook.md": render_runbook(plan),
        "README.md": readme(plan, "manifest.json"),
        BROAD_BETA_CAPTURE_WORKSHEET_FILE: json_bytes(
            broad_beta_capture_candidate_worksheet(plan)
        ),
        SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE: json_bytes(
            simultaneous_beta_capture_candidate_worksheet(plan)
        ),
        SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE: json_bytes(
            single_player_parallel_capture_candidate_worksheet(plan)
        ),
        PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE: json_bytes(
            permissions_admin_beta_capture_candidates()
        ),
    }
    artifacts["manifest.json"] = json_bytes(pack_metadata)
    return plan, artifacts


def prepare_output_dir(output_root: Path, run_id: str) -> Path:
    protected_paths.reject_symlink_component(output_root, "--output-root")
    resolved_root = protected_paths.reject_protected_output_path(output_root, "--output-root")
    output_dir = resolved_root / run_id
    protected_paths.reject_symlink_component(output_dir, "output directory")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory already exists and is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_pack(output_dir: Path, artifacts: dict[str, bytes | str]) -> dict[str, Any]:
    written: list[dict[str, Any]] = []
    for name, content in artifacts.items():
        if name == "manifest.json":
            continue
        path = output_dir / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            write_text(path, content)
        written.append(
            {
                "name": name,
                "path": name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(artifacts["manifest.json"])
    manifest["artifacts"] = sorted(written, key=lambda item: item["name"])
    write_json(manifest_path, manifest)
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    write_json(manifest_path, manifest)
    return {**manifest, "output_dir": str(output_dir)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True)
    parser.add_argument("--map", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.instance = validate_token(args.instance, "--instance")
    args.map = validate_token(args.map, "--map", SAFE_MAP_RE)
    if args.run_id is None:
        args.run_id = safe_run_id(args.instance, args.map)
    args.run_id = validate_token(args.run_id, "--run-id")
    return args


def main() -> int:
    args = parse_args()
    plan, artifacts = build_pack(args)
    protected_paths.reject_symlink_component(args.output_root, "--output-root")
    output_root = protected_paths.reject_protected_output_path(args.output_root, "--output-root")
    output_dir = output_root / args.run_id
    if args.dry_run:
        manifest = {
            "schema": SCHEMA,
            "status": "dry_run_candidate_capture_pack",
            "run_id": args.run_id,
            "target": plan["target"],
            "target_binding": target_binding(plan["target"], source="operator_cli"),
            "target_binding_id": target_binding_id(plan["target"]),
            "plan_target_binding": target_binding(plan["target"]),
            "plan_target_binding_id": target_binding_id(plan["target"]),
            "approved_runtime_window_binding": plan["approved_runtime_window_binding"],
            "would_write_dir": str(output_dir),
            "artifact_names": sorted(artifacts),
            "non_authorization": NON_AUTHORIZATION,
            "current_route_blocker": CURRENT_ROUTE_BLOCKER,
            "next_required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
            "candidate_artifact_count": candidate_artifact_count(plan),
            "candidate_artifact_intake_included": True,
            "permissions_admin_beta_capture_candidate_template": (
                PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATE_TEMPLATE
            ),
            "permissions_admin_beta_capture_candidate_schema": (
                PERMISSIONS_ADMIN_BETA_CAPTURE_CANDIDATES_SCHEMA
            ),
            "permissions_admin_beta_capture_candidate_surfaces": list(
                PERMISSIONS_ADMIN_BETA_CAPTURE_REQUIRED_SURFACES
            ),
            "broad_beta_capture_candidate_worksheet_template": BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            "broad_beta_capture_candidate_worksheet_schema": BROAD_BETA_CAPTURE_WORKSHEET_SCHEMA,
            "broad_beta_capture_candidate_worksheet_id": BROAD_BETA_CAPTURE_WORKSHEET_ID,
            "broad_beta_capture_candidate_worksheet_included": True,
            "simultaneous_beta_capture_candidate_worksheet_template": (
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE
            ),
            "simultaneous_beta_capture_candidate_worksheet_schema": (
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_SCHEMA
            ),
            "simultaneous_beta_capture_candidate_worksheet_id": (
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_ID
            ),
            "simultaneous_beta_capture_candidate_worksheet_surfaces": list(
                SIMULTANEOUS_BETA_CAPTURE_SURFACE_IDS
            ),
            "simultaneous_beta_capture_candidate_worksheet_included": True,
            "single_player_parallel_capture_candidate_worksheet_template": (
                SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE
            ),
            "single_player_parallel_capture_candidate_worksheet_schema": (
                SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_SCHEMA
            ),
            "single_player_parallel_capture_candidate_worksheet_id": (
                SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_ID
            ),
            "single_player_parallel_capture_candidate_worksheet_surfaces": list(
                SINGLE_PLAYER_PARALLEL_CAPTURE_SURFACE_IDS
            ),
            "single_player_parallel_capture_candidate_worksheet_included": True,
            "side_lanes_non_counting_before_player_principal": True,
            "no_flood_capture_policy": no_flood_capture_policy(),
            "beta_capture_interaction_boundary": beta_capture_interaction_boundary(),
            "exact_capture_objectives": plan["exact_capture_objectives"],
            "source_present": False,
            "source_material_present": False,
            "source_material_counts_as_evidence": False,
            "flood_capture_allowed": False,
            "unbounded_tester_requests_allowed": False,
            "discord_request_fanout_allowed": False,
            "candidate_only_metadata": candidate_only_metadata(),
            "parallel_capture_boundary": parallel_capture_boundary(),
            "player_principal_window_composition": player_principal_window_composition(),
            "lifecycle_correlation_metadata": plan["lifecycle_correlation_metadata"],
            "text_privacy_boundary": plan["text_privacy_boundary"],
            "non_substitution_flags": non_substitution_flags(),
            "next_action_groups_included": True,
            "next_action_groups": plan["next_action_groups"],
            "broad_beta_capture_pack_path": plan["broad_beta_capture_pack_path"],
            "parallel_beta_capture_side_lane_matrix": plan["parallel_beta_capture_side_lane_matrix"],
            "single_player_parallel_capture_sequence": plan[
                "single_player_parallel_capture_sequence"
            ],
            "target_bound_checker_command_matrix_included": True,
            "target_bound_checker_command_matrix": plan[
                "target_bound_checker_command_matrix"
            ],
            "side_lane_capture_queue_included": True,
            "side_lane_capture_queue": plan["side_lane_capture_queue"],
            "non_claim_flags": dict(NON_CLAIM_FLAGS),
        }
    else:
        manifest = write_pack(prepare_output_dir(args.output_root, args.run_id), artifacts)

    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(f"multi_surface_beta_capture_pack={manifest['status']}")
        print(f"run_id={manifest['run_id']}")
        print(f"target={manifest['target']['instance']}/{manifest['target']['map']}")
        print(f"candidate_artifact_templates={manifest.get('candidate_artifact_count')}")
        if isinstance(manifest.get("single_player_parallel_capture_sequence"), dict):
            print(
                "single_player_parallel_capture_sequence="
                f"{manifest['single_player_parallel_capture_sequence']['id']}"
            )
            print("single_player_parallel_capture_status=status_only_candidate_non_evidence")
        if isinstance(manifest.get("target_bound_checker_command_matrix"), dict):
            print(
                "target_bound_checker_command_matrix="
                f"{manifest['target_bound_checker_command_matrix']['id']}"
            )
            print("target_bound_checker_command_matrix_status=offline_command_templates_candidate_only")
        if isinstance(manifest.get("side_lane_capture_queue"), dict):
            print(f"side_lane_capture_queue={manifest['side_lane_capture_queue']['id']}")
            print("side_lane_capture_queue_status=queued_candidate_observations_non_counting")
        if manifest.get("simultaneous_beta_capture_candidate_worksheet_included") is True:
            print(
                "simultaneous_beta_capture_candidate_worksheet="
                f"{SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE}"
            )
        if manifest.get("single_player_parallel_capture_candidate_worksheet_included") is True:
            print(
                "single_player_parallel_capture_candidate_worksheet="
                f"{SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE}"
            )
        if isinstance(manifest.get("exact_capture_objectives"), dict):
            print(
                "exact_capture_objectives="
                f"{manifest['exact_capture_objectives']['objective_count']}"
            )
        print("no_flood_capture_policy=single_window_no_flood_candidate_capture_policy")
        print("no_flood=true")
        print("source_present=false")
        print("source_metadata_required=true")
        if manifest.get("broad_beta_capture_candidate_worksheet_included") is True:
            print(f"broad_beta_capture_candidate_worksheet={BROAD_BETA_CAPTURE_WORKSHEET_FILE}")
        print("raw_player_text_retention_allowed=false")
        print("secrets_or_webhook_retention_allowed=false")
        print("counts_as_approved_runtime_evidence=false")
        print("counts_as_sdk_progress=false")
        if "output_dir" in manifest:
            print(f"output_dir={manifest['output_dir']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
