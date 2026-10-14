#!/usr/bin/env python3
"""Tests for check_player_principal_lifecycle_activation_preconditions.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
SCRIPT = SCRIPT_DIR / "check_player_principal_lifecycle_activation_preconditions.py"
BETA_NOTICE_SCRIPT = SCRIPT_DIR / "prepare_player_principal_lifecycle_beta_notice.py"
ROUTE_GATE_SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate.py"
TARGET = {"instance": "arkserver3", "map": "Genesis2"}
DIAGNOSTIC_ENV_LINE = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DIAGNOSTIC_CANDIDATES=1"
ROUTE_SAMPLING_ENV_LINE = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING=1"
ROUTE_SAMPLE_LIMIT_ENV_LINE = "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT=500"

from prepare_player_principal_lifecycle_beta_notice import (  # noqa: E402
    NON_AUTHORIZATION as BETA_NOTICE_NON_AUTHORIZATION,
    NOTICE_ACTION_ARTIFACT_SCHEMA,
    SIDECAR_NON_EVIDENCE_FLAGS,
    active_notice_update_policy,
    beta_tester_status_workflow_plan,
)
from prepare_player_principal_lifecycle_window_request import (  # noqa: E402
    APPROVAL_ATTESTATION_CURRENT_TURN,
    APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SOURCE_CURRENT_TURN,
    APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_SCHEMA,
    APPROVAL_SCOPE_SOURCE_REQUIRED,
    APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY,
    APPROVAL_SCOPE_STATUS,
    APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY,
    AUTHORIZATION_FLAGS,
    CURRENT_TURN_APPROVAL_REQUIRED_FIELDS,
    DEFAULT_APPROVED_WINDOW_SECONDS,
    EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    EXACT_TARGET_SCOPE_SCHEMA,
    DIRECT_JOIN_PLAN_SCHEMA,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    MAX_APPROVED_WINDOW_SECONDS,
    PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
    PASSIVE_WAIT_BOUNDARY_SCHEMA,
    PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    PLAYER_PRESENCE_SAFETY_SCHEMA,
    REQUIRED_ENV,
    SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
    SESSION_START_REJECTED_REQUIRED_CALL,
    SESSION_START_REJECTED_REQUIRED_FUNCTION,
    WINDOW_MARKERS,
    direct_join_plan,
    runtime_triplet_contract,
)


def future_window_context() -> dict[str, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    prepared = now - timedelta(minutes=1)
    start = now + timedelta(minutes=5)
    end = start + timedelta(minutes=15)
    return {
        "prepared_at_utc": prepared.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_utc": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "approval_recorded_at_utc": (prepared + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": start.strftime("%Y%m%dT%H%M%SZ") + "-player-principal-lifecycle",
    }


def expected_env() -> list[str]:
    values = {
        "OBELISK_INSTANCE_ID": TARGET["instance"],
        **REQUIRED_ENV,
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256": EXPECTED_BINARY_SHA256,
    }
    keys = (
        "OBELISK_INSTANCE_ID",
        "OBELISK_ENABLE_PROCESS_EVENT_HOOK",
        "OBELISK_DISABLE_PLUGINS",
        "OBELISK_WRAPPER_PROFILE",
        "OBELISK_ENABLE_PLAYER_PRINCIPAL_LIFECYCLE_OBSERVER",
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_BINARY_SHA256",
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT",
        "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_DISPATCH_LIMIT",
        "OBELISK_PE_TRACE_LIMIT",
    )
    return [f"{key}={values[key]}" for key in keys]


def player_notice_action() -> dict[str, object]:
    return {
        "schema": "obelisk.player-principal-lifecycle-player-notice-action.v1",
        "required": True,
        "notice_path": "discord-beta-testers",
        "approved_notice_path_must_be_named": True,
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "activation_allowed_before_notice_sent": False,
        "evidence_required": "dry_run_output_and_send_confirmation_reference",
        "activation_blocker": "approved_dry_run_checked_beta_testers_notice_sent",
        "non_authorization": PLAYER_NOTICE_ACTION_NON_AUTHORIZATION,
    }


def player_presence_safety() -> dict[str, object]:
    return {
        "schema": PLAYER_PRESENCE_SAFETY_SCHEMA,
        "target": TARGET,
        "restart_expectation": "restart",
        "connected_player_check_required_before_restart": True,
        "rcon_broadcast_required_if_players_connected": True,
        "restart_must_be_cancelled_or_rescheduled_if_players_remain_connected": True,
        "passive_wait_preferred_after_activation": True,
        "linuxgsm_monitor_forbidden": True,
        "player_check_or_broadcast_authorized_by_request_pack": False,
        "non_authorization": PLAYER_PRESENCE_SAFETY_NON_AUTHORIZATION,
    }


def request_payload(ctx: dict[str, str] | None = None) -> dict[str, object]:
    ctx = ctx or future_window_context()
    action = player_notice_action()
    safety = player_presence_safety()
    exact_target_scope = {
        "schema": EXACT_TARGET_SCOPE_SCHEMA,
        "instance": TARGET["instance"],
        "map": TARGET["map"],
        "instance_alias_allowed": False,
        "map_alias_allowed": False,
        "approval_must_name_exact_instance_and_map": True,
        "target_matches_request_target": True,
        "non_authorization": EXACT_TARGET_SCOPE_NON_AUTHORIZATION,
    }
    passive_wait_boundary = {
        "schema": PASSIVE_WAIT_BOUNDARY_SCHEMA,
        "target": TARGET,
        "requested_wait_window_seconds": DEFAULT_APPROVED_WINDOW_SECONDS,
        "max_requested_wait_window_seconds": MAX_APPROVED_WINDOW_SECONDS,
        "requested_wait_window_seconds_checked_only": True,
        "requested_wait_window_authorizes_current_turn_approval": False,
        "requested_wait_window_authorizes_deploy_or_restart": False,
        "requested_wait_window_authorizes_runtime_capture": False,
        "requested_wait_window_counts_as_approved_runtime_evidence": False,
        "wait_only_or_passive_monitor_authorizes_deploy_or_restart": False,
        "passive_monitor_ticks_authorize_runtime_capture": False,
        "player_presence_detection_authorizes_followup": False,
        "snapshots_or_diagnostics_count_as_approved_runtime_evidence": False,
        "active_followup_requires_fresh_exact_current_turn_scope": True,
        "active_followup_requires_recorded_standing_launch_authority": False,
        "non_authorization": PASSIVE_WAIT_BOUNDARY_NON_AUTHORIZATION,
    }
    rollback = {
        "owner": "operator",
        "delta": "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins",
        "marker_state_dir": "/servidor/ark/obelisk/state/instances/arkserver3",
        "stable_marker_paths": {
            "enable_process_event_hook": "/servidor/ark/obelisk/state/instances/arkserver3/enable-process-event-hook",
            "disable_plugins": "/servidor/ark/obelisk/state/instances/arkserver3/disable-plugins",
        },
        "observer_marker_paths": {
            "allow_observer_debug_window": "/servidor/ark/obelisk/state/instances/arkserver3/allow-observer-debug-window",
            "allow_experimental_observers": "/servidor/ark/obelisk/state/instances/arkserver3/allow-experimental-observers",
            "enable_player_principal_lifecycle_observer": "/servidor/ark/obelisk/state/instances/arkserver3/enable-player-principal-lifecycle-observer",
        },
    }
    evidence_paths = {
        "window_request_json": "/tmp/live-validation-logs/window-request.json",
        "observer_window_env": "/tmp/live-validation-logs/observer-window.env",
        "operator_approval_request_md": "/tmp/live-validation-logs/operator-approval-request.md",
        "operator_approval_receipt_json": "/tmp/live-validation-logs/operator-approval-receipt.json",
        "preflight_pre_json": "/tmp/live-validation-logs/preflight-pre.json",
        "preflight_post_json": "/tmp/live-validation-logs/preflight-post.json",
        "window_manifest_env": "/tmp/live-validation-logs/window-manifest.env",
        "copied_obelisk_log": "/tmp/live-validation-logs/Obelisk.log",
    }
    triplet_contract = runtime_triplet_contract()
    payload = {
        "schema": "obelisk.player-principal-lifecycle-window-request.v1",
        "status": "candidate_only_request_pack",
        "prepared_at_utc": ctx["prepared_at_utc"],
        "user_policy": "operator_approved_beta_users",
        "notice_path": "discord-beta-testers",
        "target": TARGET,
        "exact_target_scope": exact_target_scope,
        "run_id": ctx["run_id"],
        "ark_binary_sha256": EXPECTED_BINARY_SHA256,
        "server_binary_path": EXPECTED_SERVER_BINARY_PATH,
        "restart_expectation": "restart",
        "final_posture": "stable",
        "diagnostic_candidates_enabled": False,
        "authorization_flags": dict(AUTHORIZATION_FLAGS),
        "marker_set": list(WINDOW_MARKERS),
        "forbidden_markers": list(FORBIDDEN_MARKERS),
        "approved_window": {
            "start_utc": ctx["start_utc"],
            "end_utc": ctx["end_utc"],
        },
        "runtime_triplet_contract": triplet_contract,
        "passive_wait_boundary": passive_wait_boundary,
        "direct_join_plan": {},
        "player_notice_action": action,
        "player_presence_safety": safety,
        "current_turn_approval_scope": {
            "schema": APPROVAL_SCOPE_SCHEMA,
            "status": APPROVAL_SCOPE_STATUS,
            "source_required": APPROVAL_SCOPE_SOURCE_REQUIRED,
            "standing_approval_allowed": False,
            "request_pack_authorizes_deploy_or_runtime": False,
            "missing_or_ambiguous_scope_blocks_window": True,
            "required_operator_approval_fields": list(CURRENT_TURN_APPROVAL_REQUIRED_FIELDS),
            "required_named_scope": {
                "target": TARGET,
                "exact_target_instance_map": exact_target_scope,
                "marker_env_gates": {
                    "markers": list(WINDOW_MARKERS),
                    "env_snapshot": expected_env(),
                },
                "restart_window": {
                    "start_utc": ctx["start_utc"],
                    "end_utc": ctx["end_utc"],
                    "expectation": "restart",
                },
                "player_notice_action": action,
                "direct_join_plan": {},
                "player_presence_safety": safety,
                "rollback": rollback,
                "evidence_paths": evidence_paths,
                "runtime_triplet_contract": triplet_contract,
                "passive_wait_boundary": passive_wait_boundary,
                "final_posture": "stable",
            },
            "non_authorization": "approval scope checklist only",
        },
    }
    join_plan = direct_join_plan(payload)
    payload["direct_join_plan"] = join_plan
    payload["current_turn_approval_scope"]["required_named_scope"]["direct_join_plan"] = join_plan
    return payload


def standing_request_payload(ctx: dict[str, str] | None = None) -> dict[str, object]:
    request = request_payload(ctx)
    boundary = dict(request["passive_wait_boundary"])
    boundary["active_followup_requires_fresh_exact_current_turn_scope"] = False
    boundary["active_followup_requires_recorded_standing_launch_authority"] = True
    request["passive_wait_boundary"] = boundary
    scope = dict(request["current_turn_approval_scope"])
    scope["status"] = APPROVAL_SCOPE_STATUS_STANDING_LAUNCH_AUTHORITY
    scope["source_required"] = APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
    scope["standing_approval_allowed"] = True
    named_scope = dict(scope["required_named_scope"])
    named_scope["passive_wait_boundary"] = boundary
    scope["required_named_scope"] = named_scope
    request["current_turn_approval_scope"] = scope
    return request


def receipt_approval_time_for_request(request: dict[str, object]) -> str:
    prepared = datetime.fromisoformat(str(request["prepared_at_utc"]).replace("Z", "+00:00")).astimezone(
        timezone.utc
    )
    return (prepared + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ")


def request_uses_standing_launch_authority(request: dict[str, object]) -> bool:
    scope = request.get("current_turn_approval_scope")
    return (
        isinstance(scope, dict)
        and scope.get("source_required") == APPROVAL_SCOPE_SOURCE_REQUIRED_STANDING_LAUNCH_AUTHORITY
    )


def request_check_payload(request: dict[str, object], request_sha256: str) -> dict[str, object]:
    standing_authority = request_uses_standing_launch_authority(request)
    return {
        "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
        "ready": True,
        "request_pack_ready": True,
        "prepared_at_utc": request["prepared_at_utc"],
        "approved_window": request["approved_window"],
        "restart_expectation": request["restart_expectation"],
        "final_posture": request["final_posture"],
        "user_policy": request["user_policy"],
        "notice_path": request["notice_path"],
        "direct_join_plan": request["direct_join_plan"],
        "request_pack_artifacts": {
            "window_request_json": {
                "path": "window-request.json",
                "sha256": request_sha256,
                "size_bytes": 100,
            },
            "observer_window_env": {
                "path": "observer-window.env",
                "sha256": "2" * 64,
                "size_bytes": 100,
            },
            "operator_approval_request_md": {
                "path": "operator-approval-request.md",
                "sha256": "3" * 64,
                "size_bytes": 100,
            },
            "operator_approval_receipt_json": {
                "path": "operator-approval-receipt.json",
                "sha256": "4" * 64,
                "size_bytes": 100,
            },
        },
        "request_pack_digest": {
            "algorithm": "sha256",
            "domain": "obelisk.player-principal-lifecycle.request-pack.v1",
            "sha256": "5" * 64,
        },
        "operator_approval_receipt_completion": {
            "approval_recorded_at_utc": receipt_approval_time_for_request(request),
            "approval_source": APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            if standing_authority
            else "current_turn_operator_message",
            "attestation": APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
            if standing_authority
            else "APPROVE_EXACT_BOUND_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW_ONLY",
        },
        "current_turn_operator_approval_required": not standing_authority,
        "current_turn_approval_recorded": not standing_authority,
        "request_pack_records_current_turn_approval": False,
        "standing_launch_authority_recorded": standing_authority,
        "standing_launch_authority_satisfies_operator_approval": standing_authority,
        "operator_runtime_authority_source": APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
        if standing_authority
        else "current_turn_operator_message",
        "authorization_source": "none_request_pack_check_only",
        "approved_runtime_evidence_source": "none_request_pack_check_only",
        "planning_only": True,
        "operator_approval_receipt_verified": True,
        "target": TARGET,
        "run_id": request["run_id"],
        "current_turn_scope_authorized": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "discord_sent": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "read_live_logs": False,
        "reads_live_logs": False,
        "live_log_reads_authorized": False,
        "live_log_permission_granted": False,
        "publication_authorized": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "request_pack_counts_as_approved_runtime_evidence": False,
        "observer_env_counts_as_approved_runtime_evidence": False,
        "operator_request_counts_as_approved_runtime_evidence": False,
        "copied_log_metadata_counts_as_approved_runtime_evidence": False,
        "bundle_output_counts_as_approved_runtime_evidence": False,
        "preflight_counts_as_approved_runtime_evidence": False,
        "window_manifest_counts_as_approved_runtime_evidence": False,
        "completed_receipt_counts_as_approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "route_ready": False,
        "sdk_accounting_counts_as_completed_surface": False,
        "p0_accounting_counts_as_promoted_surface": False,
        "target": TARGET,
        "run_id": request["run_id"],
    }


def notice_report_payload(
    request_sha256: str,
    request: dict[str, object],
    *,
    request_path: Path | None = None,
    mode: str = "confirmed_send",
) -> dict[str, object]:
    completed = mode == "confirmed_send"
    standing_authority = request_uses_standing_launch_authority(request)
    request_ref = {
        "path": str(request_path) if request_path is not None else "window-request.json",
        "sha256": request_sha256,
    }
    standing_notice_coverage = standing_authority and completed
    guarded_action = {
        "schema": "obelisk.player-principal-lifecycle-guarded-beta-notice-action.v1",
        "mode": mode,
        "request_json": request_ref,
        "target": TARGET,
        "run_id": request["run_id"],
        "notice_path": "discord-beta-testers",
        "player_notice_action": request["player_notice_action"],
        "helper": str(SCRIPT_DIR / "send_discord_embed.py"),
        "helper_returncode": 0,
        "helper_returncode_zero": True,
        "guarded_helper_invocation": completed,
        "confirm_approved_send_arg_used": completed,
        "approval_scope_arg_used": completed,
        "approval_scope": "beta-test" if completed else "dry_run_only",
        "real_beta_test_notice_action_completed": completed,
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "send_performed_by_request_pack": False,
        "request_pack_authorizes_discord": False,
        "authorizes_discord": False,
        "discord_authorized": False,
        "discord_send_authorized": False,
        "discord_authorized_by_this_report": False,
        "current_turn_approval_recorded": False,
        "current_turn_scope_authorized": False,
        "standing_launch_authority_recorded": standing_authority,
        "notice_action_covered_by_standing_launch_authority": standing_notice_coverage,
        "standing_authority_authorizes_discord_send": standing_authority,
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing_authority,
        "authorizes_runtime_work": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_toward_v1_completion": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "non_authorization": BETA_NOTICE_NON_AUTHORIZATION,
    }
    return {
        "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
        "ready": True,
        "mode": mode,
        "request_json": request_ref,
        "target": TARGET,
        "run_id": request["run_id"],
        "notice_path": "discord-beta-testers",
        "player_notice_action": request["player_notice_action"],
        "dry_run_required_before_send": True,
        "real_notice_send_required_before_activation": True,
        "activation_blocker_until_sent": "approved_dry_run_checked_beta_testers_notice_sent",
        "activation_allowed": False,
        "activation_allowed_before_notice_sent": False,
        "activation_preconditions_met": False,
        "authorizes_discord": False,
        "authorizes_runtime_work": False,
        "authorizes_server_operations": False,
        "authorizes_server_work": False,
        "authorizes_workspace_work": False,
        "authorizes_workspace_writes": False,
        "discord_authorized": False,
        "discord_notice_authorized": False,
        "discord_send_authorized": False,
        "discord_sent": mode == "confirmed_send",
        "discord_authorized_by_this_report": False,
        "discord_authorized_by_request": False,
        "current_turn_approval_recorded": False,
        "current_turn_scope_authorized": False,
        "standing_launch_authority_recorded": standing_authority,
        "notice_action_covered_by_standing_launch_authority": standing_notice_coverage,
        "standing_authority_authorizes_discord_send": standing_authority,
        "confirmed_send_requires_separate_explicit_discord_send_approval": not standing_authority,
        "live_ops_authorized": False,
        "live_log_reads_authorized": False,
        "live_log_permission_granted": False,
        "publication_authorized": False,
        "read_live_logs": False,
        "reads_live_logs": False,
        "marker_env_changes_authorized": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "runtime_capture_authorized": False,
        "runtime_window_authorized": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "public_or_runtime_accounting_allowed": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "route_ready": False,
        "runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "runtime_ready": False,
        "sdk_evidence_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "workspace_writes_authorized": False,
        "guarded_beta_notice_action": guarded_action,
        "non_authorization": BETA_NOTICE_NON_AUTHORIZATION,
    }


def direct_bot_notice_stdout_payload(
    request_sha256: str,
    request: dict[str, object],
    *,
    request_path: Path,
) -> dict[str, object]:
    return {
        "schema": "obelisk.discord-beta-bridge-bot-notice.v1",
        "ready": True,
        "sent": True,
        "discord_sent": True,
        "target": TARGET,
        "run_id": request["run_id"],
        "notice_path": "discord-beta-testers",
        "request_json": {
            "path": str(request_path),
            "sha256": request_sha256,
        },
        "active_notice_state_present": True,
        "active_notice_state_required_for_beta_controls": True,
        "active_notice_update_requested": True,
        "operational_message_kind": "single_active_beta_notice",
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "non_authorization": {
            "authorizes_discord_send": False,
            "authorizes_runtime_capture": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "counts_as_readiness": False,
        },
    }


def active_notice_state_payload() -> dict[str, object]:
    return {
        "schema": "obelisk.discord-beta-bridge-active-notice.v1",
        "guild_id": "1032660680668622969",
        "channel_id": "1513238083741683934",
        "message_id": "123456789012345678",
        "operational_message_kind": "single_active_beta_notice",
        "active_notice_state_pointer_only": True,
        "active_notice_state_is_notice_report": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_progress": False,
        "counts_as_p0_progress": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }


def route_gate_payload() -> dict[str, object]:
    return {
        "schema": "obelisk.command-permission-route-gate-check.v1",
        "valid": True,
        "planning_only": True,
        "route_blocked": True,
        "dependency_chain_locked": True,
        "current_route_blocker": "approved_runtime_evidence_missing",
        "remaining_route_blockers": ["approved_runtime_evidence_missing"],
        "next_route_blocker_after_runtime_evidence": "identity_public_contract_gate_missing",
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "route_ready": False,
        "sdk_evidence_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "public_or_runtime_accounting_allowed": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "post_evidence_p0_lock_simulation": {
            "simulation_only": True,
            "approved_runtime_evidence_accepted": False,
            "current_route_blocker": "approved_runtime_evidence_missing",
            "simulated_route_blocker_after_accepted_runtime_evidence": "identity_public_contract_gate_missing",
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        },
    }


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    return path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def notice_sidecar_path(notice_path: Path) -> Path:
    return notice_path.with_suffix(".sidecar.json")


def write_notice_sidecar(notice_path: Path, notice_report: dict[str, object]) -> Path:
    explicit_sidecar = notice_report.get("notice_action_sidecar_json")
    sidecar_path = (
        Path(explicit_sidecar)
        if isinstance(explicit_sidecar, str) and explicit_sidecar
        else notice_sidecar_path(notice_path)
    )
    if not sidecar_path.is_absolute():
        sidecar_path = notice_path.parent / sidecar_path
    sidecar = {
        "schema": NOTICE_ACTION_ARTIFACT_SCHEMA,
        "mode": notice_report.get("mode"),
        "ready": notice_report.get("ready"),
        "target": notice_report.get("target"),
        "run_id": notice_report.get("run_id"),
        "notice_path": notice_report.get("notice_path"),
        "request_json": notice_report.get("request_json"),
        "notice_report_sha256": canonical_json_sha256(notice_report),
        "notice_report": notice_report,
        "artifact_contains_full_sanitized_notice_report": True,
        "sidecar_required_for_confirmed_send_consumption": True,
        "stdout_only_confirmation_accepted": False,
        "secret_or_webhook_output_allowed": False,
        "discord_send_performed_by_artifact_write": False,
        **SIDECAR_NON_EVIDENCE_FLAGS,
        "non_authorization": BETA_NOTICE_NON_AUTHORIZATION,
    }
    return write_json(sidecar_path, sidecar)


def ensure_request_pack_sidecar_files(request_path: Path) -> None:
    defaults = {
        "observer-window.env": "OBELISK_INSTANCE_ID=arkserver3\n",
        "operator-approval-request.md": "operator approval request sidecar\n",
        "operator-approval-receipt.json": "{\"operator_completion\": true}\n",
    }
    for filename, content in defaults.items():
        path = request_path.parent / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")


class CheckPlayerPrincipalLifecycleActivationPreconditionsTests(unittest.TestCase):
    def write_inputs(
        self,
        root: Path,
        request_body: dict[str, object] | None = None,
    ) -> dict[str, Path]:
        request_body = request_body or request_payload()
        request = write_json(root / "window-request.json", request_body)
        request_sha = sha256(request)
        return {
            "request": request,
            "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
            "notice": write_json(root / "notice-report.json", notice_report_payload(request_sha, request_body, request_path=request)),
            "route": write_json(root / "route-gate.json", route_gate_payload()),
        }

    def run_script(
        self,
        paths: dict[str, Path],
        *,
        json_output: bool = True,
        ensure_sidecars: bool = True,
        ensure_notice_sidecar: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        if ensure_sidecars:
            ensure_request_pack_sidecar_files(paths["request"])
        if ensure_notice_sidecar and paths["notice"].exists():
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            if notice.get("mode") == "confirmed_send" or notice.get("discord_sent") is True:
                write_notice_sidecar(paths["notice"], notice)
        argv = [
            sys.executable,
            str(SCRIPT),
            "--request-json",
            str(paths["request"]),
            "--request-check-json",
            str(paths["request_check"]),
            "--notice-report-json",
            str(paths["notice"]),
            "--route-gate-json",
            str(paths["route"]),
        ]
        if json_output:
            argv.append("--json")
        return subprocess.run(
            argv,
            cwd=SCRIPT_DIR.parents[0],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def assert_approved_bundle_requirement(self, requirement: dict[str, object]) -> None:
        self.assertTrue(requirement["accepted_bundle_required_before_any_readiness_or_progress_claim"])
        self.assertFalse(requirement["approved_evidence_bundle_checker_accepted"])
        self.assertEqual(
            requirement["required_lifecycle_event_role_triplet"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            requirement["session_start_rejected"],
            {
                "required_function": SESSION_START_REJECTED_REQUIRED_FUNCTION,
                "required_argument_tuple": SESSION_START_REJECTED_REQUIRED_ARGUMENTS,
                "required_call": SESSION_START_REJECTED_REQUIRED_CALL,
                "required_exact_call": SESSION_START_REJECTED_REQUIRED_CALL,
                "exact_check_join_in_progress_requirement": SESSION_START_REJECTED_REQUIRED_CALL,
                "handle_new_player_rejected_tuple_allowed": False,
                "handle_new_player_rejected_tuple_alternative_allowed": False,
            },
        )
        objectives = requirement["lifecycle_missing_role_objectives"]
        self.assertEqual(
            requirement["session_start_rejected"]["exact_check_join_in_progress_requirement"],
            "CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            objectives["exact_check_join_in_progress_requirement"],
            "CheckJoinInProgress(1,0)",
        )
        self.assertEqual(
            objectives["objective_ids"],
            ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        )
        self.assertFalse(objectives["standing_authority_satisfies_missing_roles"])
        self.assertFalse(objectives["counts_as_approved_runtime_evidence"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_evidence"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_readiness"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_progress"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_authorization"])
        self.assertFalse(requirement["passive_or_no_user_state_counts_as_notice_sent"])

    def assert_no_readiness_evidence_progress_or_broad_discord_claims(
        self,
        report: dict[str, object],
    ) -> None:
        forbidden_false_keys = {
            "accepted_runtime_evidence",
            "accepted_runtime_evidence_ready",
            "activation_authorized_by_this_report",
            "approved_runtime_evidence",
            "approved_runtime_evidence_accepted",
            "approved_runtime_evidence_present",
            "approved_runtime_evidence_ready",
            "authorizes_discord",
            "broad_discord_or_community_notice_allowed",
            "counts_as_approved_runtime_evidence",
            "counts_as_runtime_evidence",
            "counts_as_sdk_evidence",
            "counts_toward_p0_dependency_chain",
            "counts_toward_p0_dependency_chain_claim",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_sdk",
            "counts_toward_v1_completion",
            "discord_authorized",
            "discord_authorized_by_this_report",
            "discord_notice_authorized",
            "discord_send_authorized",
            "grants_readiness_claims",
            "live_ops_authorized",
            "marker_env_changes_authorized",
            "promotion_ready",
            "public_abi_ready",
            "public_or_runtime_accounting_allowed",
            "public_sdk_ready",
            "publication_authorized",
            "route_ready",
            "runtime_activation_authorized",
            "runtime_evidence_present",
            "runtime_evidence_ready",
            "runtime_ready",
            "runtime_window_authorized",
            "sdk_evidence_ready",
            "server_operations_authorized",
            "stable_claim_allowed",
            "standing_authority_authorizes_discord_send",
            "standing_authority_counts_as_approved_runtime_evidence",
            "standing_authority_counts_as_runtime_evidence",
            "standing_authority_counts_as_runtime_progress",
            "standing_authority_counts_as_sdk_evidence",
            "standing_authority_counts_as_sdk_progress",
            "standing_authority_counts_toward_p0_dependency_chain",
            "standing_authority_grants_activation_readiness",
            "standing_authority_grants_public_sdk_readiness",
            "standing_authority_grants_runtime_readiness",
            "standing_debug_authority_counts_as_approved_runtime_evidence",
            "standing_debug_authority_counts_toward_sdk",
            "standing_launch_authority_counts_as_approved_runtime_evidence",
            "standing_launch_authority_counts_toward_sdk",
            "v1_completion_ready",
        }
        forbidden_zero_keys = {
            "claim_progress_contribution",
            "complete_sdk_claim_progress_contribution",
            "complete_sdk_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
            "progress",
            "runtime_progress",
            "sdk_progress",
            "v1_progress",
        }

        def normalized(key: object) -> str:
            text = str(key)
            text = "".join(
                f"_{char.lower()}" if char.isupper() else char
                for char in text
            )
            return "_".join(part for part in text.lower().replace("-", "_").split("_") if part)

        def walk(value: object, path: str = "$") -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    child_path = f"{path}.{key}"
                    normalized_key = normalized(key)
                    if normalized_key in forbidden_false_keys:
                        self.assertFalse(child, child_path)
                    if normalized_key in forbidden_zero_keys:
                        self.assertEqual(child, 0, child_path)
                    walk(child, child_path)
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk(child, f"{path}[{index}]")

        walk(report)

    def test_accepts_only_consistent_confirmed_notice_and_verified_request_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            expected_run_id = request["run_id"]
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["offline_preconditions_consistent"])
        self.assertTrue(report["activation_preconditions_checked"])
        self.assertFalse(report["activation_preconditions_met"])
        self.assertEqual(report["target"], TARGET)
        self.assertEqual(report["run_id"], expected_run_id)
        self.assertEqual(report["direct_join_plan"]["schema"], DIRECT_JOIN_PLAN_SCHEMA)
        self.assertEqual(report["direct_join_plan"]["target"], TARGET)
        self.assertEqual(report["direct_join_plan"]["target_map"], "Genesis2")
        self.assertFalse(report["direct_join_plan"]["fastest_clean_theisland_direct_join"])
        self.assertTrue(report["direct_join_plan"]["direct_join_required"])
        self.assertFalse(report["direct_join_plan"]["cluster_transfer_required"])
        self.assertFalse(report["direct_join_plan"]["extra_transfer_server_required"])
        self.assertFalse(report["direct_join_plan"]["third_ark_server_allowed"])
        self.assertFalse(report["direct_join_plan"]["broad_discord_or_community_notice_allowed"])
        self.assertEqual(report["direct_join_plan"]["organic_wait_window_seconds"], 900)
        self.assertTrue(report["direct_join_plan"]["receipt_before_activation_required"])
        self.assertTrue(report["direct_join_plan"]["post_window_replay_requires_receipt"])
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertFalse(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertTrue(diagnostic_policy["request_explicitly_disabled"])
        self.assertFalse(diagnostic_policy["request_enabled"])
        self.assertEqual(diagnostic_policy["approved_evidence_blockers"], [])
        self.assertEqual(
            report["next_blocker"],
            "fresh_current_turn_operator_authorization_required_before_activation",
        )
        self.assertTrue(report["fresh_current_turn_operator_authorization_required_before_activation"])
        self.assertFalse(report["standing_debug_authority_recorded"])
        self.assertFalse(report["allowed_by_recorded_standing_debug_authority"])
        self.assertTrue(report["still_missing_current_scope"])
        self.assertTrue(report["still_missing_current_turn_scope"])
        self.assertEqual(report["activation_authority_precondition"]["status"], "still_missing_current_scope")
        self.assertFalse(
            report["activation_authority_precondition"]["allowed_by_recorded_standing_debug_authority"]
        )
        self.assertTrue(report["activation_authority_precondition"]["still_missing_current_scope"])
        self.assertFalse(report["activation_allowed"])
        self.assertFalse(report["activation_authorized_by_this_report"])
        self.assertFalse(report["runtime_activation_authorized"])
        self.assertFalse(report["operator_may_activate_by_this_report"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["authorizes_server_operations"])
        self.assertFalse(report["authorizes_discord"])
        self.assertFalse(report["publication_authorized"])
        self.assertFalse(report["live_ops_authorized"])
        self.assertFalse(report["read_live_logs"])
        self.assertFalse(report["live_log_reads_authorized"])
        self.assertFalse(report["live_log_permission_granted"])
        self.assertFalse(report["runtime_capture_authorized"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["current_turn_scope_authorized"])
        self.assertFalse(report["discord_authorized_by_this_report"])
        self.assertFalse(report["discord_send_authorized"])
        self.assertFalse(report["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["sdk_evidence_ready"])
        self.assertTrue(report["prepared_actions_remain_notice_only_or_request_only"])
        self.assertFalse(report["approved_evidence_bundle_checker_accepted"])
        self.assertTrue(report["approved_evidence_bundle_acceptance_required"])
        self.assert_approved_bundle_requirement(report["approved_evidence_bundle_acceptance_requirement"])
        for action in report["activation_next_action_sequence"]:
            self.assertIn(action["prepared_action_mode"], {"notice_only", "request_only"})
            self.assertEqual(action["prepared_action_scope"], "notice_only_or_request_only")
            self.assertTrue(action["notice_only_or_request_only_until_approved_evidence_bundle_accepted"])
            self.assertFalse(action["approved_evidence_bundle_checker_accepted"])
            self.assert_approved_bundle_requirement(action["approved_evidence_bundle_acceptance_requirement"])
        self.assertIn("offline pre-activation consistency check only", report["non_authorization"])

    def test_rejects_diagnostic_candidates_enabled_for_approved_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = request_payload()
            request_body["diagnostic_candidates_enabled"] = True
            named_scope = request_body["current_turn_approval_scope"]["required_named_scope"]
            env_snapshot = named_scope["marker_env_gates"]["env_snapshot"]
            env_snapshot.append(DIAGNOSTIC_ENV_LINE)
            paths = self.write_inputs(root, request_body)
            (paths["request"].parent / "observer-window.env").write_text(
                f"OBELISK_INSTANCE_ID=arkserver3\n{DIAGNOSTIC_ENV_LINE}\n",
                encoding="utf-8",
            )
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["ready"])
        self.assertIn(
            "diagnostic_candidates_for_approved_evidence_window",
            report["blockers"],
        )
        self.assertIn(
            "observer_env_diagnostic_candidates_for_approved_evidence_window",
            report["blockers"],
        )
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertTrue(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertTrue(diagnostic_policy["request_enabled"])
        self.assertFalse(diagnostic_policy["request_explicitly_disabled"])
        self.assertTrue(diagnostic_policy["observer_env_contains_diagnostic_candidates"])
        self.assertFalse(diagnostic_policy["diagnostic_candidate_lines_promotable_for_approved_evidence"])
        self.assertTrue(
            diagnostic_policy["source_log_contains_lifecycle_diagnostic_lines_blocks_approved_evidence"]
        )

    def test_rejects_diagnostic_candidates_not_explicitly_disabled_for_approved_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_body = request_payload()
            del request_body["diagnostic_candidates_enabled"]
            paths = self.write_inputs(Path(tmp), request_body)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["ready"])
        self.assertIn(
            "diagnostic_candidates_not_explicitly_disabled_for_approved_evidence_window",
            report["blockers"],
        )
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertTrue(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertFalse(diagnostic_policy["request_enabled"])
        self.assertFalse(diagnostic_policy["request_explicitly_disabled"])

    def test_rejects_observer_env_diagnostic_candidates_even_when_request_disables(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            (paths["request"].parent / "observer-window.env").write_text(
                f"OBELISK_INSTANCE_ID=arkserver3\n{DIAGNOSTIC_ENV_LINE}\n",
                encoding="utf-8",
            )
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["ready"])
        self.assertIn(
            "observer_env_diagnostic_candidates_for_approved_evidence_window",
            report["blockers"],
        )
        self.assertNotIn(
            "diagnostic_candidates_for_approved_evidence_window",
            report["blockers"],
        )
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertTrue(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertTrue(diagnostic_policy["request_explicitly_disabled"])
        self.assertFalse(diagnostic_policy["request_enabled"])
        self.assertTrue(diagnostic_policy["observer_env_contains_diagnostic_candidates"])

    def test_rejects_observer_env_route_sampling_even_when_request_disables(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            (paths["request"].parent / "observer-window.env").write_text(
                "OBELISK_INSTANCE_ID=arkserver3\n"
                f"{ROUTE_SAMPLING_ENV_LINE}\n"
                f"{ROUTE_SAMPLE_LIMIT_ENV_LINE}\n",
                encoding="utf-8",
            )
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["ready"])
        self.assertIn(
            "observer_env_diagnostic_keys_for_approved_evidence_window",
            report["blockers"],
        )
        self.assertNotIn(
            "observer_env_diagnostic_candidates_for_approved_evidence_window",
            report["blockers"],
        )
        diagnostic_policy = report["diagnostic_candidates_for_approved_evidence"]
        self.assertTrue(diagnostic_policy["approved_evidence_window_rejected"])
        self.assertTrue(diagnostic_policy["request_explicitly_disabled"])
        self.assertFalse(diagnostic_policy["request_enabled"])
        self.assertFalse(diagnostic_policy["observer_env_contains_diagnostic_candidates"])
        self.assertEqual(
            diagnostic_policy["observer_env_diagnostic_keys_present"],
            [
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLE_LIMIT",
                "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_ROUTE_SAMPLING",
            ],
        )
        self.assertFalse(
            diagnostic_policy["diagnostic_route_sample_lines_promotable_for_approved_evidence"]
        )

    def test_rejects_direct_join_plan_that_allows_transfer_or_third_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request_body = request_payload()
            request_body["direct_join_plan"]["cluster_transfer_required"] = True
            request_body["direct_join_plan"]["third_ark_server_allowed"] = True
            request_body["direct_join_plan"]["organic_wait_window_counts_as_approved_runtime_evidence"] = True
            paths = self.write_inputs(Path(tmp), request_body)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(report["ready"])
        self.assertIn("request_direct_join_plan_cluster_transfer_required_not_false", report["blockers"])
        self.assertIn("request_direct_join_plan_third_ark_server_allowed_not_false", report["blockers"])
        self.assertIn(
            "request_direct_join_plan_organic_wait_window_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )
        self.assertIn("request_direct_join_plan_mismatch", report["blockers"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_accepts_confirmed_notice_sidecar_input_when_stdout_report_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            sidecar = write_notice_sidecar(paths["notice"], notice)
            paths["notice"] = sidecar
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["offline_preconditions_consistent"])
        self.assertEqual(report["inputs"]["notice_action_sidecar_json"]["path"], str(sidecar))
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_direct_bot_notice_stdout_as_activation_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            write_json(
                paths["notice"],
                direct_bot_notice_stdout_payload(
                    sha256(paths["request"]),
                    request,
                    request_path=paths["request"],
                ),
            )
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_checked"])
        self.assertFalse(report["activation_preconditions_met"])
        self.assertIn("direct_bot_notice_report_not_activation_notice", report["blockers"])
        self.assertIn("notice_report_schema_mismatch", report["blockers"])
        self.assertIn("beta_notice_action_sidecar_missing", report["blockers"])

    def test_rejects_confirmed_bot_notice_bound_to_wrong_channel_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_sha = sha256(paths["request"])
            notice = notice_report_payload(request_sha, request, request_path=paths["request"])
            guarded = notice["guarded_beta_notice_action"]
            guarded["approval_scope_arg_used"] = False
            guarded["approval_scope"] = "1513238083741683935"
            guarded["bot_notice_helper"] = True
            guarded["bot_channel_id"] = "1513238083741683935"
            guarded["expected_channel_id"] = "1513238083741683935"
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("guarded_beta_notice_action_approval_scope_mismatch", report["blockers"])
        self.assertIn("guarded_beta_notice_action_bot_channel_id_mismatch", report["blockers"])
        self.assertIn("guarded_beta_notice_action_expected_channel_id_mismatch", report["blockers"])

    def test_rejects_active_notice_state_as_activation_notice(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            write_json(paths["notice"], active_notice_state_payload())
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_checked"])
        self.assertFalse(report["activation_preconditions_met"])
        self.assertIn("active_notice_state_not_activation_notice", report["blockers"])
        self.assertIn("notice_report_schema_mismatch", report["blockers"])
        self.assertIn("beta_notice_confirmed_send_required", report["blockers"])

    def test_accepts_standing_launch_authority_as_bound_activation_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(root / "notice-report.json", notice_report_payload(request_sha, request_body, request_path=request_path)),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertEqual(
            report["next_blocker"],
            "offline_preconditions_consistent_recorded_standing_authority_scoped_operations_next",
        )
        self.assertFalse(report["fresh_current_turn_operator_authorization_required_before_activation"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertTrue(report["standing_debug_authority_recorded"])
        self.assertTrue(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertTrue(report["recorded_standing_debug_authority_satisfies_activation_preconditions"])
        self.assertTrue(report["allowed_by_recorded_standing_debug_authority"])
        self.assertFalse(report["standing_authority_preparation_only"])
        self.assertFalse(report["still_missing_current_scope"])
        self.assertFalse(report["still_missing_current_turn_scope"])
        self.assertTrue(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )
        self.assertTrue(
            report["activation_next_action_sequence_consumable_under_recorded_standing_debug_authority"]
        )
        self.assertEqual(report["two_server_cap_policy"]["max_running_ark_servers"], 2)
        self.assertEqual(
            report["lifecycle_missing_role_objectives"]["objective_ids"],
            ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
        )
        self.assertTrue(report["recommended_notice_text"]["recommended_text_already_redacted"])
        self.assertFalse(report["recommended_notice_text"]["raw_player_text_or_identity_allowed"])
        self.assertIn("direct-join", report["recommended_notice_text"]["recommended_discord_text_redacted"])
        self.assertFalse(report["recommended_notice_text"]["broad_discord_or_community_notice_allowed"])
        authority = report["activation_authority_precondition"]
        self.assertEqual(
            authority["status"],
            "offline_preconditions_consistent_recorded_standing_authority_scoped_operations_next",
        )
        self.assertTrue(authority["allowed_by_recorded_standing_debug_authority"])
        self.assertTrue(authority["allowed_by_recorded_standing_launch_authority"])
        self.assertTrue(authority["standing_authority_allowed_for_planning_activation_preconditions"])
        self.assertFalse(authority["standing_authority_preparation_only"])
        self.assertTrue(authority["standing_authority_authorizes_server_restart"])
        self.assertTrue(authority["standing_authority_authorizes_marker_env_changes"])
        self.assertFalse(authority["standing_authority_authorizes_discord_send"])
        self.assertFalse(authority["standing_authority_counts_as_runtime_progress"])
        self.assertFalse(authority["standing_authority_counts_as_sdk_progress"])
        self.assertFalse(authority["standing_authority_grants_runtime_readiness"])
        self.assertFalse(authority["still_missing_current_scope"])
        self.assertFalse(authority["activation_authorized_by_this_report"])
        self.assertFalse(authority["server_operations_authorized"])
        self.assertFalse(authority["runtime_window_authorized"])
        self.assertFalse(authority["counts_as_approved_runtime_evidence"])
        self.assertFalse(authority["counts_toward_sdk"])
        self.assertFalse(authority["grants_readiness_claims"])
        safety = report["standing_debug_authority_safety_limits"]
        self.assertEqual(safety["max_running_ark_servers"], 2)
        self.assertFalse(safety["three_ark_servers_allowed"])
        self.assertTrue(safety["must_confirm_one_instance_off_before_starting_another"])
        self.assertTrue(safety["restart_must_warn_or_reschedule_if_players_connected"])
        self.assertTrue(safety["connected_player_check_required_before_restart"])
        self.assertTrue(safety["rcon_broadcast_required_if_players_connected"])
        self.assertTrue(safety["restart_must_be_cancelled_or_rescheduled_if_players_remain_connected"])
        self.assertFalse(safety["raw_player_text_capture_allowed"])
        self.assertFalse(safety["secret_capture_allowed"])
        self.assertTrue(safety["recommended_text_already_redacted"])
        self.assertFalse(safety["secret_or_webhook_output_allowed"])
        self.assertEqual(safety["two_server_cap_policy"]["max_running_ark_servers"], 2)
        self.assertFalse(safety["approved_runtime_evidence_claim_allowed"])
        self.assertFalse(report["fresh_separate_activation_approval_required"])
        self.assertFalse(report["checker_default_sends_discord"])
        self.assertFalse(report["checker_default_touches_ark"])
        self.assertFalse(report["checker_default_reads_live_logs"])
        self.assertFalse(report["checker_default_edits_markers_or_env"])
        self.assertFalse(report["activation_authorized_by_this_report"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["standing_authority_counts_as_runtime_progress"])
        self.assertFalse(report["standing_authority_counts_as_sdk_progress"])
        self.assertFalse(report["standing_authority_grants_runtime_readiness"])
        self.assertFalse(report["external_execution_authority"]["separate_operator_authorization_required"])
        self.assertFalse(report["external_execution_authority"]["fresh_separate_activation_approval_required"])
        self.assertTrue(
            report["external_execution_authority"][
                "activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"
            ]
        )
        self.assertFalse(report["external_execution_authority"]["checker_default_sends_discord"])
        self.assertFalse(report["external_execution_authority"]["checker_default_touches_ark"])
        self.assertTrue(
            report["external_execution_authority"]["standing_launch_authority_satisfies_active_observation_scope"]
        )
        self.assertTrue(
            report["external_execution_authority"][
                "standing_launch_authority_satisfies_dry_run_notice_preparation_scope"
            ]
        )
        self.assertFalse(report["external_execution_authority"]["standing_authority_authorizes_discord_send"])
        self.assertTrue(report["external_execution_authority"]["standing_authority_authorizes_server_restart"])
        self.assertFalse(
            report["external_execution_authority"]["standing_authority_grants_runtime_readiness"]
        )
        self.assertEqual(
            [item["id"] for item in report["activation_next_action_sequence"]],
            [
                "confirmed_beta_notice_consumed",
                "safe_restart_warn_or_reschedule",
                "active_observation_window",
                "capture_required_sibling_sidecars",
                "restore_stable_posture_and_verify",
            ],
        )
        for action in report["activation_next_action_sequence"]:
            self.assertFalse(action["separate_operator_authorization_required"])
            self.assertFalse(action["fresh_separate_activation_approval_required"])
            self.assertTrue(action["consumable_under_recorded_standing_launch_authority"])
            self.assertTrue(action["allowed_under_recorded_standing_debug_authority"])
            self.assertFalse(action["standing_authority_authorizes_discord_send"])
            self.assertIs(
                action["standing_authority_authorizes_runtime_evidence"],
                action["id"] in {"active_observation_window", "capture_required_sibling_sidecars"},
            )
            self.assertIs(
                action["standing_authority_authorizes_marker_env_changes"],
                action["id"] in {"active_observation_window", "restore_stable_posture_and_verify"},
            )
            self.assertIs(
                action["standing_authority_authorizes_server_restart"],
                action["id"] in {"safe_restart_warn_or_reschedule", "restore_stable_posture_and_verify"},
            )
            self.assertEqual(action["two_server_cap_policy"]["max_running_ark_servers"], 2)
            self.assertEqual(
                action["lifecycle_missing_role_objectives"]["objective_ids"],
                ["session_start", "CheckJoinInProgress(1,0)", "session_end"],
            )
            self.assertIn(action["prepared_action_mode"], {"notice_only", "request_only"})
            self.assertEqual(action["prepared_action_scope"], "notice_only_or_request_only")
            self.assertTrue(action["notice_only_or_request_only_until_approved_evidence_bundle_accepted"])
            self.assertFalse(action["approved_evidence_bundle_checker_accepted"])
            self.assert_approved_bundle_requirement(action["approved_evidence_bundle_acceptance_requirement"])
            self.assertFalse(action["authorized_by_this_report"])
            self.assertFalse(action["server_operations_authorized_by_this_report"])
            self.assertFalse(action["runtime_work_authorized_by_this_report"])
            self.assertFalse(action["marker_env_changes_authorized_by_this_report"])
            self.assertFalse(action["grants_readiness_claims"])
            self.assertFalse(action["ark_touched_by_checker"])
            self.assertFalse(action["counts_as_approved_runtime_evidence"])
            self.assertFalse(action["counts_toward_sdk"])
            self.assertFalse(action["counts_toward_p0_dependency_chain"])
        summary = report["operator_action_summary"]
        self.assertTrue(summary["recorded_standing_debug_authority"]["recorded"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["authorized_by_this_report"])
        self.assertTrue(summary["recorded_standing_debug_authority"]["applies_to_operator_actions_only"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["applies_to_preparation_only"])
        self.assertTrue(summary["recorded_standing_debug_authority"]["standing_authority_authorizes_server_restart"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(summary["recorded_standing_debug_authority"]["grants_readiness_claims"])
        self.assertEqual(
            len(summary["actions_allowed_under_recorded_standing_debug_authority"]),
            5,
        )
        self.assertTrue(
            report["activation_next_action_sequence"][1]["player_presence_safety"][
                "connected_player_check_required_before_restart"
            ]
        )
        self.assertIn(
            "OBELISK_PLAYER_PRINCIPAL_LIFECYCLE_LOG_LIMIT=10",
            report["activation_next_action_sequence"][2]["marker_env_gates"]["env_snapshot"],
        )
        self.assertEqual(
            report["activation_next_action_sequence"][2]["direct_join_plan"],
            request_body["direct_join_plan"],
        )
        self.assertIn(
            "preflight_pre_json",
            report["activation_next_action_sequence"][3]["required_evidence_paths"],
        )
        self.assertIn(
            "copied_obelisk_log",
            report["activation_next_action_sequence"][3]["required_evidence_paths"],
        )
        rendered_actions = json.dumps(report["activation_next_action_sequence"])
        self.assertNotIn("fresh exact operator", rendered_actions)

    def test_accepted_standing_authority_emits_no_readiness_evidence_or_broad_discord_claims(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertTrue(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )
        self.assert_no_readiness_evidence_progress_or_broad_discord_claims(report)

    def test_rejects_standing_authority_with_mismatched_request_check_target_or_window(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            request_check = request_check_payload(request_body, request_sha)
            request_check["target"] = {"instance": "arkserver2", "map": "Ragnarok"}
            request_check["approved_window"] = {
                "start_utc": "2026-12-01T12:00:00Z",
                "end_utc": "2026-12-01T12:15:00Z",
            }
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_target_mismatch", report["blockers"])
        self.assertIn("request_check_approved_window_mismatch", report["blockers"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )

    def test_accepts_standing_launch_authority_with_real_route_gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            route_result = subprocess.run(
                [sys.executable, str(ROUTE_GATE_SCRIPT), "--json"],
                cwd=SCRIPT_DIR.parents[0],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if route_result.returncode != 0:
                route_report = json.loads(route_result.stdout)
                self.assertFalse(route_report.get("approved_runtime_evidence_ready", False))
                self.assertFalse(route_report.get("counts_toward_sdk", False))
                self.assertFalse(route_report.get("public_sdk_ready", False))
                self.assertTrue(route_report.get("blockers"))
                return
            route_path = root / "route-gate.json"
            route_path.write_text(route_result.stdout, encoding="utf-8")
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": route_path,
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertEqual(
            report["next_blocker"],
            "offline_preconditions_consistent_recorded_standing_authority_scoped_operations_next",
        )
        self.assertFalse(report["fresh_current_turn_operator_authorization_required_before_activation"])
        self.assertTrue(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertFalse(report["standing_authority_preparation_only"])
        self.assertFalse(report["activation_authorized_by_this_report"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(
            any(
                blocker.startswith("route_gate_forbidden_authorization_or_evidence_claim:")
                for blocker in report["blockers"]
            )
        )

    def test_accepts_real_standing_beta_notice_report_with_standing_send_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            called = root / "called.json"
            fake_helper = root / "fake_send_helper.py"
            fake_helper.write_text(
                "import json, sys\n"
                "args = sys.argv[1:]\n"
                f"open({str(called)!r}, 'w', encoding='utf-8').write(json.dumps(args))\n"
                "receipt = 'test-confirmed-send-dry-run-receipt'\n"
                "if '--dry-run' in args:\n"
                "    print(json.dumps({\n"
                "        'dry_run_receipt': receipt,\n"
                "        'dry_run_receipt_inputs': {'helper_args': args},\n"
                "        'dry_run_receipt_validated': False,\n"
                "    }))\n"
                "    raise SystemExit(0)\n"
                "supplied = None\n"
                "if '--dry-run-receipt' in args:\n"
                "    index = args.index('--dry-run-receipt')\n"
                "    if index + 1 < len(args):\n"
                "        supplied = args[index + 1]\n"
                "print(json.dumps({\n"
                "    'dry_run_receipt': supplied,\n"
                "    'dry_run_receipt_inputs': {'helper_args': args},\n"
                "    'dry_run_receipt_validated': supplied == receipt,\n"
                "}))\n"
                "raise SystemExit(0 if supplied == receipt else 1)\n",
                encoding="utf-8",
            )
            notice_result = subprocess.run(
                [
                    sys.executable,
                    str(BETA_NOTICE_SCRIPT),
                    "--request-json",
                    str(request_path),
                    "--send-helper",
                    str(fake_helper),
                    "--confirm-approved-send",
                    "--json",
                ],
                cwd=SCRIPT_DIR.parents[0],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(notice_result.returncode, 0, notice_result.stderr)
            notice_report = json.loads(notice_result.stdout)
            helper_payload = {
                "active_notice_state_present": True,
                "discord_sent": True,
                "http_status": 200,
                "status_summary_action_count": 1,
                "status_summary_ephemeral_response_only": True,
                "status_summary_metadata_only": True,
                "status_summary_uses_local_event_sink_only": True,
                "active_notice_reuse_diagnostic": {
                    "active_notice_state_present": True,
                },
                "editable_notice_workflow": {
                    "active_notice_state_present": True,
                },
                "operational_message_policy": {
                    "active_notice_state_present": True,
                    "status_summary_action_count": 1,
                    "status_summary_ephemeral_response_only": True,
                    "status_summary_metadata_only": True,
                    "status_summary_uses_local_event_sink_only": True,
                },
                "tester_status_workflow": {
                    "cluster_transfer_is_coordination_status_only": True,
                    "status_summary_uses_local_event_sink_only": True,
                    "updates_existing_notice_when_state_present": True,
                },
            }
            notice_report["confirmed_send_helper_payload"] = helper_payload
            notice_report["confirmed_send_dry_run_receipt_preflight_payload"] = helper_payload
            notice_path = write_json(root / "notice-report.json", notice_report)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": notice_path,
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)
            helper_args = json.loads(called.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertTrue(report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"])
        self.assertFalse(report["fresh_separate_activation_approval_required"])
        self.assertFalse(report["activation_authorized_by_this_report"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertTrue(notice_report["standing_launch_authority_recorded"])
        self.assertTrue(notice_report["notice_action_covered_by_standing_launch_authority"])
        self.assertTrue(notice_report["standing_authority_authorizes_discord_send"])
        self.assertFalse(
            notice_report["notice_authority_boundary"]["separate_operator_authorization_required_before_confirmed_send"]
        )
        self.assertFalse(notice_report["notice_authority_boundary"]["fresh_separate_notice_approval_required"])
        self.assertFalse(notice_report["default_sends_discord"])
        self.assertFalse(notice_report["default_touches_ark"])
        self.assertIn("--confirm-approved-send", helper_args)
        self.assertIn("--send-beta-notice", helper_args)
        self.assertIn("--with-beta-controls", helper_args)
        self.assertIn("--update-active-notice", helper_args)
        self.assertNotIn("--approval-scope", helper_args)
        self.assertIn("--content", helper_args)

    def test_rejects_request_check_standing_authority_when_request_requires_current_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["standing_launch_authority_recorded"] = True
            request_check["standing_launch_authority_satisfies_operator_approval"] = True
            request_check["operator_runtime_authority_source"] = APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            request_check["current_turn_operator_approval_required"] = False
            request_check["current_turn_approval_recorded"] = False
            request_check["operator_approval_receipt_completion"]["approval_source"] = (
                APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            )
            request_check["operator_approval_receipt_completion"]["attestation"] = (
                APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
            )
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_standing_launch_authority_scope_mismatch", report["blockers"])
        self.assertIn("request_check_standing_launch_authority_recorded_not_false", report["blockers"])
        self.assertIn(
            "request_check_standing_launch_authority_satisfies_operator_approval_not_false",
            report["blockers"],
        )
        self.assertIn("request_check_operator_runtime_authority_source_unexpected_standing", report["blockers"])
        self.assertIn("request_check_operator_approval_receipt_unexpected_standing_source", report["blockers"])
        self.assertFalse(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])

    def test_rejects_standing_request_when_request_check_lacks_standing_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            request_check = request_check_payload(request_body, request_sha)
            request_check["standing_launch_authority_recorded"] = False
            request_check["standing_launch_authority_satisfies_operator_approval"] = False
            request_check["operator_runtime_authority_source"] = APPROVAL_SOURCE_CURRENT_TURN
            request_check["current_turn_operator_approval_required"] = True
            request_check["current_turn_approval_recorded"] = True
            request_check["operator_approval_receipt_completion"]["approval_source"] = APPROVAL_SOURCE_CURRENT_TURN
            request_check["operator_approval_receipt_completion"]["attestation"] = APPROVAL_ATTESTATION_CURRENT_TURN
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_standing_launch_authority_scope_mismatch", report["blockers"])
        self.assertIn("request_check_operator_runtime_authority_source_standing_required", report["blockers"])
        self.assertIn("request_check_operator_approval_receipt_standing_source_required", report["blockers"])
        self.assertFalse(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])

    def test_rejects_standing_request_check_missing_explicit_receipt_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            request_check = request_check_payload(request_body, request_sha)
            request_check["standing_launch_authority_recorded"] = False
            request_check["standing_launch_authority_satisfies_operator_approval"] = True
            request_check["operator_runtime_authority_source"] = APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            request_check["current_turn_operator_approval_required"] = False
            request_check["current_turn_approval_recorded"] = True
            request_check["operator_approval_receipt_completion"]["approval_source"] = (
                APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY
            )
            request_check["operator_approval_receipt_completion"]["attestation"] = (
                APPROVAL_ATTESTATION_STANDING_LAUNCH_AUTHORITY
            )
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_standing_launch_authority_scope_mismatch", report["blockers"])
        self.assertIn("request_check_standing_launch_authority_recorded_not_true", report["blockers"])
        self.assertIn(
            "request_check_current_turn_approval_recorded_not_false_for_standing_authority",
            report["blockers"],
        )
        self.assertFalse(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])

    def test_passive_status_standing_debug_artifact_does_not_authorize_activation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            request_check = request_check_payload(request_body, request_sha)
            request_check["standing_launch_authority_recorded"] = False
            request_check["standing_launch_authority_satisfies_operator_approval"] = False
            request_check["operator_runtime_authority_source"] = APPROVAL_SOURCE_CURRENT_TURN
            request_check["current_turn_operator_approval_required"] = True
            request_check["current_turn_approval_recorded"] = True
            request_check["operator_approval_receipt_completion"]["approval_source"] = APPROVAL_SOURCE_CURRENT_TURN
            request_check["operator_approval_receipt_completion"]["attestation"] = APPROVAL_ATTESTATION_CURRENT_TURN
            request_check["passive_status_authority_snapshot"] = {
                "standing_debug_authority_recorded": True,
                "recorded_standing_debug_authority": {
                    "recorded": True,
                    "authorized_by_this_report": False,
                    "counts_as_approved_runtime_evidence": False,
                    "grants_readiness_claims": False,
                },
                "actions_allowed_under_recorded_standing_debug_authority": [
                    {
                        "action": "continue_exact_player_principal_lifecycle_runtime_observation_for_missing_roles",
                        "allowed_under_recorded_standing_debug_authority": True,
                        "authorized_by_this_report": False,
                        "counts_as_approved_runtime_evidence": False,
                    }
                ],
            }
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_standing_launch_authority_scope_mismatch", report["blockers"])
        self.assertIn(
            "request_check_non_authorizing_passive_status_authority_artifact:$.passive_status_authority_snapshot",
            report["blockers"],
        )
        self.assertFalse(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_debug_authority_recorded"])
        self.assertFalse(report["allowed_by_recorded_standing_debug_authority"])
        self.assertTrue(report["still_missing_current_scope"])
        self.assertEqual(report["activation_authority_precondition"]["status"], "still_missing_current_scope")
        self.assertFalse(
            report["activation_authority_precondition"]["allowed_by_recorded_standing_debug_authority"]
        )
        self.assertTrue(report["activation_authority_precondition"]["still_missing_current_scope"])
        self.assertFalse(report["activation_authorized_by_this_report"])
        self.assertFalse(report["runtime_window_authorized"])
        self.assertFalse(report["server_operations_authorized"])

    def test_rejects_notice_standing_authority_metadata_not_bound_to_request_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["standing_launch_authority_recorded"] = True
            notice["notice_action_covered_by_standing_launch_authority"] = True
            notice["guarded_beta_notice_action"]["standing_launch_authority_recorded"] = True
            notice["guarded_beta_notice_action"]["notice_action_covered_by_standing_launch_authority"] = True
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_standing_launch_authority_recorded_mismatch", report["blockers"])
        self.assertIn("beta_notice_standing_launch_authority_coverage_mismatch", report["blockers"])
        self.assertIn(
            "guarded_beta_notice_action_standing_launch_authority_recorded_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "guarded_beta_notice_action_standing_launch_authority_coverage_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["standing_launch_authority_recorded"])

    def test_non_json_success_output_remains_non_authorizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            result = self.run_script(paths, json_output=False)

        output = result.stdout.strip()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("player_principal_lifecycle_activation_preconditions_ready=true", output)
        self.assertIn("activation_authorized_by_this_report=false", output)
        self.assertIn("server_operations_authorized=false", output)
        self.assertIn("runtime_capture_authorized=false", output)
        self.assertIn("discord_authorized=false", output)
        self.assertIn("counts_toward_sdk=false", output)
        self.assertIn("counts_toward_p0_dependency_chain=false", output)
        self.assertIn("fresh_current_turn_operator_authorization_required_before_activation=true", output)
        self.assertIn("standing_debug_authority_recorded=false", output)
        self.assertIn("allowed_by_recorded_standing_debug_authority=false", output)
        self.assertIn("still_missing_current_scope=true", output)
        self.assertNotIn("activation_preconditions_met=true", output)
        self.assertNotIn("operator_may_activate", output)

    def test_rejects_dry_run_notice_as_activation_precondition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_sha = sha256(paths["request"])
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"], mode="dry_run"))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_confirmed_send_required", report["blockers"])
        self.assertIn("beta_notice_sent_attestation_missing", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_dry_run_notice_for_standing_activation_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(
                        request_sha,
                        request_body,
                        request_path=request_path,
                        mode="dry_run",
                    ),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_confirmed_send_required", report["blockers"])
        self.assertIn("beta_notice_sent_attestation_missing", report["blockers"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )

    def test_rejects_dry_run_notice_that_claims_confirmed_send_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_sha = sha256(paths["request"])
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            notice = notice_report_payload(request_sha, request, request_path=paths["request"], mode="dry_run")
            notice["discord_sent"] = True
            notice["guarded_beta_notice_action"]["real_beta_test_notice_action_completed"] = True
            notice["guarded_beta_notice_action"]["guarded_helper_invocation"] = True
            notice["guarded_beta_notice_action"]["confirm_approved_send_arg_used"] = True
            notice["guarded_beta_notice_action"]["approval_scope_arg_used"] = True
            notice["guarded_beta_notice_action"]["approval_scope"] = "beta-test"
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_confirmed_send_required", report["blockers"])
        self.assertIn("beta_notice_dry_run_discord_sent_not_false", report["blockers"])
        self.assertIn("guarded_beta_notice_action_dry_run_completed_not_false", report["blockers"])
        self.assertIn(
            "guarded_beta_notice_action_dry_run_guarded_helper_invocation_not_false",
            report["blockers"],
        )
        self.assertIn("guarded_beta_notice_action_dry_run_confirm_arg_not_false", report["blockers"])
        self.assertIn("guarded_beta_notice_action_dry_run_approval_scope_arg_not_false", report["blockers"])
        self.assertIn("guarded_beta_notice_action_dry_run_approval_scope_mismatch", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_unverified_operator_approval_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["operator_approval_receipt_verified"] = False
            request_check["current_turn_approval_recorded"] = False
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator_approval_receipt_not_verified", report["blockers"])
        self.assertIn("current_turn_approval_not_recorded", report["blockers"])
        self.assertFalse(report["server_operations_authorized"])

    def test_rejects_request_check_that_claims_authorization_or_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["authorization_source"] = "operator_approval_receipt"
            request_check["approved_runtime_evidence_source"] = "request_pack"
            request_check["request_pack_counts_as_approved_runtime_evidence"] = True
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_authorization_source_mismatch", report["blockers"])
        self.assertIn("request_check_approved_runtime_evidence_source_mismatch", report["blockers"])
        self.assertIn(
            "request_check_request_pack_counts_as_approved_runtime_evidence_not_false",
            report["blockers"],
        )

    def test_rejects_nested_request_check_and_notice_alias_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["status_snapshots"] = [
                {
                    "status": "ready",
                    "sdk_ready": True,
                    "approved": True,
                    "accepted": True,
                    "complete": True,
                    "current_turn_authorized": True,
                }
            ]
            notice = notice_report_payload(sha256(paths["request"]), request, request_path=paths["request"])
            notice["delivery_snapshot"] = {
                "discord_sent_by_this_report": True,
                "activation_authorized_by_this_report": True,
            }
            write_json(paths["request_check"], request_check)
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].status",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].sdk_ready",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].accepted",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].approved",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].complete",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].current_turn_authorized",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.delivery_snapshot.discord_sent_by_this_report",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.delivery_snapshot.activation_authorized_by_this_report",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["runtime_activation_authorized"])

    def test_rejects_camelcase_and_split_claim_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["sdkProgress"] = 1
            request_check["false_only_aliases"] = {
                "runtimeReady": 0,
            }
            notice = notice_report_payload(sha256(paths["request"]), request, request_path=paths["request"])
            notice["delivery_split_claim"] = {
                "field": "runtimeReady",
                "value": "yes",
            }
            notice["delivery_value_less_claim"] = {
                "field": "runtimeReady",
            }
            notice["delivery_false_string_alias"] = {
                "currentTurnScopeAuthorized": "false",
            }
            route = route_gate_payload()
            route["route_split_claim"] = {
                "field": "publicSdkReady",
                "value": "yes",
            }
            route["route_value_less_claim"] = {
                "name": "publicSdkReady",
            }
            route["route_false_only_split_claim"] = {
                "field": "publicSdkReady",
                "value": 0,
            }
            write_json(paths["request_check"], request_check)
            write_json(paths["notice"], notice)
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.sdkProgress",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.false_only_aliases.runtimeReady",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.delivery_split_claim",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.delivery_value_less_claim",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.delivery_false_string_alias.currentTurnScopeAuthorized",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.route_split_claim",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.route_value_less_claim",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.route_false_only_split_claim",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["runtime_activation_authorized"])

    def test_rejects_current_turn_closure_notice_and_live_log_string_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["offline_aliases"] = {
                "closureRequestStatus": "ready",
                "closureRequestProgress": 1,
                "currentTurnScopeAuthorized": "yes",
                "liveLogPermission": "allowed",
                "passiveMonitorStatus": "ready",
                "publicReadiness": True,
            }
            notice = notice_report_payload(sha256(paths["request"]), request, request_path=paths["request"])
            notice["notice_aliases"] = {
                "dryRunNoticeStatus": "ready",
                "sentNoticeRuntimeAuthorization": "approved",
                "liveLogReadPermission": "allowed",
                "noticeStatus": "sent",
                "runtimeStatus": "ready",
            }
            write_json(paths["request_check"], request_check)
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.closureRequestStatus",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.closureRequestProgress",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.currentTurnScopeAuthorized",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.liveLogPermission",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.passiveMonitorStatus",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.offline_aliases.publicReadiness",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.dryRunNoticeStatus",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.sentNoticeRuntimeAuthorization",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.liveLogReadPermission",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.noticeStatus",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.runtimeStatus",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["live_log_reads_authorized"])

    def test_rejects_notice_report_that_authorizes_discord_or_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["authorizes_discord"] = True
            notice["publication_authorized"] = True
            notice["discord_authorized_by_request"] = True
            notice["counts_toward_public_sdk"] = True
            notice["public_abi_ready"] = True
            notice["sdk_evidence_ready"] = True
            notice["marker_env_changes_authorized"] = True
            notice["activation_allowed"] = True
            notice["activation_preconditions_met"] = True
            notice["runtime_window_authorized"] = True
            notice["non_authorization"] = "notice sent means runtime is authorized"
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("notice_report_authorizes_discord_not_false", report["blockers"])
        self.assertIn("notice_report_publication_authorized_not_false", report["blockers"])
        self.assertIn("notice_report_discord_authorized_by_request_not_false", report["blockers"])
        self.assertIn("notice_report_counts_toward_public_sdk_not_false", report["blockers"])
        self.assertIn("notice_report_public_abi_ready_not_false", report["blockers"])
        self.assertIn("notice_report_sdk_evidence_ready_not_false", report["blockers"])
        self.assertIn("notice_report_marker_env_changes_authorized_not_false", report["blockers"])
        self.assertIn("notice_report_activation_allowed_not_false", report["blockers"])
        self.assertIn("notice_report_activation_preconditions_met_not_false", report["blockers"])
        self.assertIn("notice_report_runtime_window_authorized_not_false", report["blockers"])
        self.assertIn("beta_notice_non_authorization_mismatch", report["blockers"])

    def test_rejects_notice_report_bound_to_wrong_notice_path_or_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["notice_path"] = "other-channel"
            notice["player_notice_action"] = dict(notice["player_notice_action"])
            notice["player_notice_action"]["notice_path"] = "other-channel"
            notice["dry_run_required_before_send"] = False
            notice["real_notice_send_required_before_activation"] = False
            notice["activation_blocker_until_sent"] = "notice_not_required"
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_notice_path_mismatch", report["blockers"])
        self.assertIn("beta_notice_player_notice_action_mismatch", report["blockers"])
        self.assertIn("beta_notice_dry_run_required_before_send_not_true", report["blockers"])
        self.assertIn("beta_notice_real_notice_send_required_before_activation_not_true", report["blockers"])
        self.assertIn("beta_notice_activation_blocker_until_sent_mismatch", report["blockers"])

    def test_rejects_notice_report_target_or_run_id_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["target"] = {"instance": "arkserver2", "map": "Ragnarok"}
            notice["run_id"] = "20260605T091000Z-player-principal-lifecycle"
            notice["guarded_beta_notice_action"]["target"] = notice["target"]
            notice["guarded_beta_notice_action"]["run_id"] = notice["run_id"]
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_target_mismatch", report["blockers"])
        self.assertIn("beta_notice_run_id_mismatch", report["blockers"])
        self.assertIn("guarded_beta_notice_action_target_mismatch", report["blockers"])
        self.assertIn("guarded_beta_notice_action_run_id_mismatch", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_notice_delivered_sent_or_accepted_aliases_as_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["notice_delivery_aliases"] = {
                "noticeDelivered": True,
                "playerNoticeDeliveryStatus": "delivered",
                "acceptedNoticeAction": True,
                "noticeSentAsRuntimeEvidence": True,
            }
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_delivery_aliases.noticeDelivered",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_delivery_aliases.playerNoticeDeliveryStatus",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_delivery_aliases.acceptedNoticeAction",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_delivery_aliases.noticeSentAsRuntimeEvidence",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])

    def test_accepts_beta_tester_workflow_metadata_without_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["active_notice_update_policy"] = active_notice_update_policy()
            notice["tester_status_workflow"] = beta_tester_status_workflow_plan()
            notice["dry_run_ready_to_send"] = {
                "active_notice_update_policy": active_notice_update_policy(),
                "tester_status_workflow": beta_tester_status_workflow_plan(),
            }
            notice["next_action_sequence"] = [
                {
                    "id": "send_guarded_beta_notice_with_buttons",
                    "tester_status_workflow": beta_tester_status_workflow_plan(),
                    "counts_as_approved_runtime_evidence": False,
                    "counts_toward_sdk": False,
                    "non_authorization": BETA_NOTICE_NON_AUTHORIZATION,
                }
            ]
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertEqual(report["ready_scope"], "offline_pre_activation_consistency_only")
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_capture_authorized"])
        joined_blockers = "\n".join(report["blockers"])
        self.assertNotIn(
            "accepted_copied_sibling_set_required_before_runtime_claims",
            joined_blockers,
        )
        self.assertNotIn(
            "edit_existing_message_when_active_notice_state_present",
            joined_blockers,
        )

    def test_rejects_runtime_claim_inside_beta_tester_workflow_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            notice["tester_status_workflow"] = beta_tester_status_workflow_plan()
            notice["tester_status_workflow"]["runtimeReady"] = True
            notice["dry_run_ready_to_send"] = {
                "tester_status_workflow": beta_tester_status_workflow_plan(),
            }
            notice["dry_run_ready_to_send"]["tester_status_workflow"][
                "counts_as_approved_runtime_evidence"
            ] = True
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.tester_status_workflow.runtimeReady",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.dry_run_ready_to_send.tester_status_workflow.counts_as_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_route_gate_that_claims_sdk_or_wrong_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route["current_route_blocker"] = "identity_public_contract_gate_missing"
            route["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]
            route["public_sdk_ready"] = True
            route["post_evidence_p0_lock_simulation"]["approved_runtime_evidence_accepted"] = True
            route["post_evidence_p0_lock_simulation"]["counts_toward_complete_sdk_claim"] = True
            route["post_evidence_p0_lock_simulation"]["complete_sdk_claim_progress_contribution"] = 1
            route["status_snapshots"] = [
                {
                    "status": "ready",
                    "accepted": True,
                    "sdk_ready": True,
                    "current_turn_authorized": True,
                }
            ]
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("route_gate_current_blocker_not_runtime_evidence_missing", report["blockers"])
        self.assertIn("route_gate_remaining_blockers_mismatch", report["blockers"])
        self.assertIn("route_gate_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("route_gate_post_evidence_approved_runtime_evidence_accepted_not_false", report["blockers"])
        self.assertIn("route_gate_post_evidence_counts_toward_complete_sdk_claim_not_false", report["blockers"])
        self.assertIn("route_gate_post_evidence_complete_sdk_claim_progress_contribution_not_zero", report["blockers"])
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].status",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].accepted",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].sdk_ready",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.status_snapshots[0].current_turn_authorized",
            report["blockers"],
        )
        self.assertFalse(report["counts_toward_p0_dependency_chain"])

    def test_rejects_route_gate_embedded_authorization_or_runtime_evidence_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route["approved_runtime_evidence_present"] = True
            route["runtime_evidence_ready"] = True
            route["counts_toward_sdk"] = True
            route["stable_claim_allowed"] = True
            route["critical_path_phase"] = {
                "source_checker_approved_runtime_evidence_manifest": {
                    "approved_runtime_evidence_ready": True,
                },
                "live_scope": {
                    "server_operations_authorized": True,
                },
                "complete_sdk_claim_progress_contribution": 1,
            }
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.approved_runtime_evidence_present",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.runtime_evidence_ready",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.counts_toward_sdk",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.stable_claim_allowed",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.critical_path_phase.source_checker_approved_runtime_evidence_manifest.approved_runtime_evidence_ready",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.critical_path_phase.live_scope.server_operations_authorized",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.critical_path_phase.complete_sdk_claim_progress_contribution",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_embedded_exact_copied_triplet_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route["approved_runtime_evidence_candidate"] = {
                "status": "blocked",
                "blockers": ["runtime_summary_complete_lifecycle_event_triplet_missing"],
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
            }
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "route_gate_exact_copied_triplet_blocker_present:"
            "$.approved_runtime_evidence_candidate.blockers[0]",
            report["blockers"],
        )
        self.assertFalse(report["ready"])
        self.assertEqual(report["next_blocker"], "activation_preconditions_missing")
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )

    def test_rejects_start_end_only_runtime_evidence_as_activation_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route["principal_start_end_runtime_evidence"] = {
                "schema": "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1",
                "ready": True,
                "ready_scope": "principal_start_end_runtime_evidence_only",
                "accepted_for_contract_review": True,
                "principal_start_end_runtime_evidence_present": True,
                "principal_start_end_runtime_evidence_ready": True,
                "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
                "approved_runtime_evidence": False,
                "approved_runtime_evidence_present": False,
                "approved_runtime_evidence_ready": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
                "counts_toward_complete_sdk_claim": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "complete_sdk_claim_progress_contribution": 0,
                "p0_dependency_chain_claim_progress_contribution": 0,
                "blockers": [],
            }
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "route_gate_start_end_only_runtime_evidence_not_activation_ready:"
            "$.principal_start_end_runtime_evidence",
            report["blockers"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["counts_toward_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain"])

    def test_rejects_standing_or_current_approval_artifact_evidence_progress_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["standing_launch_authority_receipt"] = {
                "approval_source": APPROVAL_SOURCE_STANDING_LAUNCH_AUTHORITY,
                "approved_runtime_evidence_ready": True,
            }
            request_check["current_turn_operator_approval_artifact"] = {
                "approval_source": APPROVAL_SOURCE_CURRENT_TURN,
                "complete_sdk_progress_contribution": 1,
            }
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "request_check_approval_artifact_claims_evidence_progress_or_readiness:"
            "$.standing_launch_authority_receipt.approved_runtime_evidence_ready",
            report["blockers"],
        )
        self.assertIn(
            "request_check_approval_artifact_claims_evidence_progress_or_readiness:"
            "$.current_turn_operator_approval_artifact.complete_sdk_progress_contribution",
            report["blockers"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["standing_launch_authority_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["standing_launch_authority_counts_toward_sdk"])

    def test_rejects_check_join_in_progress_copied_bool_shape_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route["candidate_copied_runtime_triplet"] = [
                {
                    "role": "session_start",
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                    "copied_bool_values": ["1", "1"],
                },
                {
                    "role": "session_start_rejected",
                    "target": "ShooterGameMode.CheckJoinInProgress",
                    "copied_bool_fields": ["ReturnValue", "bIsFromLogin"],
                    "copied_bool_values": ["1", "0"],
                },
                {
                    "role": "session_end",
                    "target": "ShooterGameMode.OnLogout",
                    "copied_bool_fields": "",
                    "copied_bool_values": "",
                    "correlation_status": "matched",
                },
            ]
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "route_gate_copied_check_join_in_progress_bool_shape_mismatch:"
            "$.candidate_copied_runtime_triplet[1]",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_copied_lifecycle_triplet_shape_mismatch:"
            "$.candidate_copied_runtime_triplet",
            report["blockers"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_route_gate_without_post_evidence_simulation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            route = route_gate_payload()
            route.pop("post_evidence_p0_lock_simulation")
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("route_gate_post_evidence_simulation_missing", report["blockers"])

    def test_rejects_notice_bound_to_different_request_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            notice = notice_report_payload("0" * 64, request, request_path=paths["request"])
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_request_sha256_mismatch", report["blockers"])

    def test_rejects_notice_bound_to_different_request_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            alternate_request = Path(tmp) / "other-window-request.json"
            alternate_request.write_text(paths["request"].read_text(encoding="utf-8"), encoding="utf-8")
            notice = notice_report_payload(
                sha256(paths["request"]),
                request,
                request_path=alternate_request,
            )
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_request_path_mismatch", report["blockers"])

    def test_rejects_notice_bound_to_live_server_request_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            notice = notice_report_payload(
                sha256(paths["request"]),
                request,
                request_path=Path("/servidor/ark/obelisk/window-request.json"),
            )
            write_json(paths["notice"], notice)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_request_path_protected", report["blockers"])
        self.assertIn("beta_notice_request_path_mismatch", report["blockers"])

    def test_rejects_request_check_bound_to_different_request_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_check = json.loads(paths["request_check"].read_text(encoding="utf-8"))
            request_check["request_pack_artifacts"]["window_request_json"]["sha256"] = "0" * 64
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_window_request_json_artifact_sha256_mismatch", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_request_check_missing_completed_receipt_artifact_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_check = json.loads(paths["request_check"].read_text(encoding="utf-8"))
            request_check["request_pack_artifacts"]["operator_approval_receipt_json"] = None
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_operator_approval_receipt_json_artifact_missing", report["blockers"])
        self.assertFalse(report["server_operations_authorized"])

    def test_rejects_confirmed_notice_without_required_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice_sidecar_path(paths["notice"]).unlink(missing_ok=True)
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_action_sidecar_missing", report["blockers"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_standing_authority_when_confirmed_notice_sidecar_is_missing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_action_sidecar_missing", report["blockers"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )

    def test_rejects_standing_authority_when_notice_is_only_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(
                        request_sha,
                        request_body,
                        request_path=request_path,
                        mode="draft",
                    ),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_confirmed_send_required", report["blockers"])
        self.assertIn("beta_notice_sent_attestation_missing", report["blockers"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )

    def test_rejects_confirmed_notice_sidecar_with_stale_request_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            sidecar_path = write_notice_sidecar(paths["notice"], notice)
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["request_json"] = {
                "path": str(Path(tmp) / "stale-window-request.json"),
                "sha256": "0" * 64,
            }
            write_json(sidecar_path, sidecar)
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("beta_notice_action_sidecar_request_json_mismatch", report["blockers"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_confirmed_notice_sidecar_evidence_or_progress_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            notice = json.loads(paths["notice"].read_text(encoding="utf-8"))
            sidecar_path = write_notice_sidecar(paths["notice"], notice)
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["sidecar_counts_as_approved_runtime_evidence"] = True
            sidecar["sidecar_counts_toward_sdk"] = True
            write_json(sidecar_path, sidecar)
            result = self.run_script(paths, ensure_notice_sidecar=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "beta_notice_action_sidecar_sidecar_counts_as_approved_runtime_evidence_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "beta_notice_action_sidecar_sidecar_counts_toward_sdk_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_claimed_request_pack_window_missing_required_sidecar_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            ensure_request_pack_sidecar_files(paths["request"])
            (paths["request"].parent / "observer-window.env").unlink()
            result = self.run_script(paths, ensure_sidecars=False)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_observer_window_env_artifact_file_missing", report["blockers"])
        self.assertFalse(report["ready"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_request_check_artifacts_bound_to_stale_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_check = json.loads(paths["request_check"].read_text(encoding="utf-8"))
            request_check["request_pack_artifacts"]["observer_window_env"]["path"] = "stale/observer-window.env"
            request_check["request_pack_artifacts"]["operator_approval_request_md"]["path"] = (
                "stale/operator-approval-request.md"
            )
            request_check["request_pack_artifacts"]["operator_approval_receipt_json"]["path"] = (
                "stale/operator-approval-receipt.json"
            )
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_observer_window_env_artifact_path_mismatch", report["blockers"])
        self.assertIn("request_check_operator_approval_request_md_artifact_path_mismatch", report["blockers"])
        self.assertIn("request_check_operator_approval_receipt_json_artifact_path_mismatch", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_request_missing_player_presence_safety_even_when_reports_claim_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request.pop("player_presence_safety")
            request["current_turn_approval_scope"]["required_named_scope"].pop("player_presence_safety")
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("player_presence_safety_missing", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_request_scope_missing_bound_player_notice_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request["current_turn_approval_scope"]["required_named_scope"].pop("player_notice_action")
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_current_turn_approval_player_notice_action_mismatch", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_request_target_alias_or_exact_scope_drift_even_when_reports_claim_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request["target"]["instance"] = "public-identity"
            request["target"]["map"] = "sdk-ready"
            request["exact_target_scope"]["instance_alias_allowed"] = True
            request["exact_target_scope"]["map_alias_allowed"] = True
            request["current_turn_approval_scope"]["required_named_scope"]["target"] = request["target"]
            request["current_turn_approval_scope"]["required_named_scope"]["exact_target_instance_map"] = {
                **request["exact_target_scope"],
                "instance": "arkserver3",
                "map": "Genesis2",
            }
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_target_instance_alias_not_exact", report["blockers"])
        self.assertIn("request_target_map_alias_not_exact", report["blockers"])
        self.assertIn("request_exact_target_scope_instance_mismatch", report["blockers"])
        self.assertIn("request_exact_target_scope_map_mismatch", report["blockers"])
        self.assertIn("request_exact_target_scope_instance_alias_allowed_not_false", report["blockers"])
        self.assertIn("request_exact_target_scope_map_alias_allowed_not_false", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_passive_status_and_public_readiness_target_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request["target"]["instance"] = "passive-monitor"
            request["target"]["map"] = "public-readiness"
            request["exact_target_scope"]["instance"] = "passive-monitor"
            request["exact_target_scope"]["map"] = "public-readiness"
            request["current_turn_approval_scope"]["required_named_scope"]["target"] = request["target"]
            request["current_turn_approval_scope"]["required_named_scope"][
                "exact_target_instance_map"
            ] = request["exact_target_scope"]
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_target_instance_alias_not_exact", report["blockers"])
        self.assertIn("request_target_map_alias_not_exact", report["blockers"])
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_no_users_no_testers_and_passive_wait_target_aliases(self) -> None:
        cases = (
            ("no-users", "Genesis2", "request_target_instance_alias_not_exact"),
            ("arkserver3", "no-testers", "request_target_map_alias_not_exact"),
            ("passive-wait", "Genesis2", "request_target_instance_alias_not_exact"),
        )
        for instance, map_name, expected_blocker in cases:
            with self.subTest(instance=instance, map=map_name), tempfile.TemporaryDirectory() as tmp:
                paths = self.write_inputs(Path(tmp))
                request = json.loads(paths["request"].read_text(encoding="utf-8"))
                request["target"]["instance"] = instance
                request["target"]["map"] = map_name
                request["exact_target_scope"]["instance"] = instance
                request["exact_target_scope"]["map"] = map_name
                request["current_turn_approval_scope"]["required_named_scope"]["target"] = request["target"]
                request["current_turn_approval_scope"]["required_named_scope"][
                    "exact_target_instance_map"
                ] = request["exact_target_scope"]
                write_json(paths["request"], request)
                request_sha = sha256(paths["request"])
                write_json(paths["request_check"], request_check_payload(request, request_sha))
                write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
                result = self.run_script(paths)
                report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected_blocker, report["blockers"])
            self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_no_users_no_testers_passive_wait_shortcut_claim_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request_check = request_check_payload(request, sha256(paths["request"]))
            request_check["no_user_aliases"] = {
                "noUsersEvidence": True,
                "noTestersReadiness": "ready",
                "passiveWaitProgress": 1,
            }
            notice = notice_report_payload(sha256(paths["request"]), request, request_path=paths["request"])
            notice["notice_aliases"] = {
                "noUsersNoticeSent": True,
                "noTestersAuthorizationState": "approved",
            }
            route = route_gate_payload()
            route["passive_wait_aliases"] = {
                "passiveWaitEvidence": True,
            }
            write_json(paths["request_check"], request_check)
            write_json(paths["notice"], notice)
            write_json(paths["route"], route)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.no_user_aliases.noUsersEvidence",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.no_user_aliases.noTestersReadiness",
            report["blockers"],
        )
        self.assertIn(
            "request_check_forbidden_authorization_or_evidence_claim:$.no_user_aliases.passiveWaitProgress",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.noUsersNoticeSent",
            report["blockers"],
        )
        self.assertIn(
            "notice_report_forbidden_authorization_or_evidence_claim:$.notice_aliases.noTestersAuthorizationState",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_forbidden_authorization_or_evidence_claim:$.passive_wait_aliases.passiveWaitEvidence",
            report["blockers"],
        )
        self.assertFalse(report["activation_preconditions_met"])

    def test_rejects_player_presence_safety_authorization_or_restart_guard_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            safety = dict(request["player_presence_safety"])
            safety["connected_player_check_required_before_restart"] = False
            safety["player_check_or_broadcast_authorized_by_request_pack"] = True
            request["player_presence_safety"] = safety
            request["current_turn_approval_scope"]["required_named_scope"]["player_presence_safety"] = safety
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "player_presence_safety_connected_player_check_required_before_restart_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "player_presence_safety_player_check_or_broadcast_authorized_by_request_pack_not_false",
            report["blockers"],
        )
        self.assertFalse(report["runtime_window_authorized"])

    def test_rejects_stale_request_window_even_when_reports_claim_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            request["prepared_at_utc"] = "2026-01-01T11:55:00Z"
            request["approved_window"] = {
                "start_utc": "2026-01-01T12:00:00Z",
                "end_utc": "2026-01-01T12:10:00Z",
            }
            request["run_id"] = "20260101T120000Z-player-principal-lifecycle"
            request["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T12:00:00Z",
                "end_utc": "2026-01-01T12:10:00Z",
                "expectation": "restart",
            }
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_approved_window_already_started_or_stale", report["blockers"])
        self.assertIn("request_approved_window_expired", report["blockers"])
        self.assertFalse(report["runtime_window_authorized"])

    def test_rejects_stale_standing_request_window_without_consuming_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request_body = standing_request_payload()
            request_body["prepared_at_utc"] = "2026-01-01T11:55:00Z"
            request_body["approved_window"] = {
                "start_utc": "2026-01-01T12:00:00Z",
                "end_utc": "2026-01-01T12:15:00Z",
            }
            request_body["run_id"] = "20260101T120000Z-player-principal-lifecycle"
            request_body["current_turn_approval_scope"]["required_named_scope"]["restart_window"] = {
                "start_utc": "2026-01-01T12:00:00Z",
                "end_utc": "2026-01-01T12:15:00Z",
                "expectation": "restart",
            }
            request_path = write_json(root / "window-request.json", request_body)
            request_sha = sha256(request_path)
            paths = {
                "request": request_path,
                "request_check": write_json(root / "request-check.json", request_check_payload(request_body, request_sha)),
                "notice": write_json(
                    root / "notice-report.json",
                    notice_report_payload(request_sha, request_body, request_path=request_path),
                ),
                "route": write_json(root / "route-gate.json", route_gate_payload()),
            }
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_approved_window_already_started_or_stale", report["blockers"])
        self.assertIn("request_approved_window_expired", report["blockers"])
        self.assertTrue(report["standing_launch_authority_recorded"])
        self.assertFalse(report["standing_launch_authority_satisfies_activation_authority"])
        self.assertTrue(report["still_missing_current_scope"])
        self.assertFalse(
            report["activation_next_action_sequence_consumable_under_recorded_standing_launch_authority"]
        )
        self.assertFalse(report["standing_authority_authorizes_server_restart"])

    def test_rejects_stale_operator_approval_receipt_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request_check = json.loads(paths["request_check"].read_text(encoding="utf-8"))
            request_check["operator_approval_receipt_completion"][
                "approval_recorded_at_utc"
            ] = "2026-01-01T00:00:00Z"
            write_json(paths["request_check"], request_check)
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_check_operator_approval_receipt_before_request_prepared", report["blockers"])
        self.assertIn("request_check_operator_approval_receipt_too_far_before_window_start", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_forbidden_env_or_marker_scope_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            request = json.loads(paths["request"].read_text(encoding="utf-8"))
            gates = request["current_turn_approval_scope"]["required_named_scope"]["marker_env_gates"]
            gates["env_snapshot"].append("OBELISK_ENABLE_REFLECTION_SCANNER=1")
            gates["markers"] = list(gates["markers"]) + ["enable-reflection-scanner"]
            write_json(paths["request"], request)
            request_sha = sha256(paths["request"])
            write_json(paths["request_check"], request_check_payload(request, request_sha))
            write_json(paths["notice"], notice_report_payload(request_sha, request, request_path=paths["request"]))
            result = self.run_script(paths)
            report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("request_current_turn_approval_markers_mismatch", report["blockers"])
        self.assertIn("request_current_turn_approval_env_exclusivity_mismatch", report["blockers"])
        self.assertIn("request_current_turn_approval_forbidden_env_present", report["blockers"])

    def test_rejects_live_server_request_json_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_inputs(Path(tmp))
            paths["request"] = Path("/servidor/ark/obelisk/window-request.json")
            result = self.run_script(paths)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("protected server root", result.stderr)


if __name__ == "__main__":
    unittest.main()
