#!/usr/bin/env python3
"""Tests for report_obelisk_sdk_status.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import report_obelisk_sdk_status as status_report


SCRIPT = REPO_ROOT / "scripts" / "report_obelisk_sdk_status.py"
PREPARE_MULTI_SURFACE_PACK = (
    REPO_ROOT / "scripts" / "prepare_obelisk_multi_surface_beta_capture_pack.py"
)


class ObeliskSdkStatusReportTests(unittest.TestCase):
    def post_evidence_p0_lock_simulation_payload(self) -> dict[str, object]:
        return {
            "schema": "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
            "simulation_only": True,
            "non_claim": (
                "Accepted runtime principal lifecycle evidence can move only to identity "
                "public contract review; it does not unlock permissions/admin, command "
                "response, commands/replies, runtime readiness, public SDK readiness, "
                "P0 progress, or complete SDK claim progress."
            ),
            "approved_runtime_evidence_accepted": False,
            "current_route_blocker": "approved_runtime_evidence_missing",
            "remaining_route_blockers": ["approved_runtime_evidence_missing"],
            "simulated_route_blocker_after_accepted_runtime_evidence": (
                "identity_public_contract_gate_missing"
            ),
            "identity_public_contract_required": True,
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "public_or_runtime_accounting_allowed": False,
            "stable_claim_allowed": False,
            "p0_child_checks": [
                {
                    "name": "permissions_admin_public_readiness",
                    "present": True,
                    "current_route_blocker": "approved_runtime_evidence_missing",
                    "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                    "dependency_chain_locked": True,
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                },
                {
                    "name": "command_chat_response_public_readiness",
                    "present": True,
                    "current_route_blocker": "approved_runtime_evidence_missing",
                    "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                    "dependency_chain_locked": True,
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                },
            ],
        }

    def public_sdk_payload(self) -> dict[str, object]:
        return {
            "ready": False,
            "status": "blocked",
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "current_route_blocker": "approved_runtime_evidence_missing",
            "remaining_route_blockers": ["approved_runtime_evidence_missing"],
            "complete_sdk_progress_ratio": "0/12",
            "p0_dependency_chain_progress_ratio": "0/4",
            "command_permission_route_gate": {
                "schema": "obelisk.command-permission-route-gate-check.v1",
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "current_route_blocker": "approved_runtime_evidence_missing",
                "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                "current_blocker": "approved_runtime_evidence_missing",
                "route_lock_blocked_until": [
                    "approved_runtime_principal_lifecycle_evidence",
                    "reviewed_identity_public_contract",
                ],
                "approved_runtime_evidence_forwarded": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "post_evidence_p0_lock_simulation": (
                    self.post_evidence_p0_lock_simulation_payload()
                ),
            },
            "fastest_next_sdk_unblock": {
                "schema": "obelisk.public-sdk-v1-fastest-next-unblock.v1",
                "current_route_blocker": "approved_runtime_evidence_missing",
                "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                "unblock_kind": "approved_copied_runtime_principal_lifecycle_evidence",
                "recommended_next_action": "produce approved copied runtime principal lifecycle evidence",
                "required_artifacts": ["approved_runtime_principal_lifecycle_evidence_bundle"],
                "required_event_roles": ["session_start", "session_start_rejected", "session_end"],
                "active_runtime_window_requires_current_turn_scope": True,
                "actionable_paths": {
                    "historical_theisland_candidate_missing_sidecars": {
                        "path_type": "candidate_closure_request_helper",
                        "authorization": "non-authorizing",
                        "authorizes_runtime_work": False,
                        "authorizes_server_operations": False,
                        "authorizes_workspace_writes": False,
                        "reads_live_logs": False,
                        "counts_toward_complete_sdk_claim_now": False,
                        "counts_toward_p0_dependency_chain_claim_now": False,
                        "target": {"instance": "arkserver2", "map": "TheIsland"},
                    },
                    "active_genesis2_passive_missing_roles": {
                        "path_type": "passive_observation_missing_role_triplet",
                        "authorization": "non-authorizing",
                        "authorizes_runtime_work": False,
                        "authorizes_server_operations": False,
                        "authorizes_workspace_writes": False,
                        "reads_live_logs": False,
                        "counts_toward_complete_sdk_claim_now": False,
                        "counts_toward_p0_dependency_chain_claim_now": False,
                        "target": {"instance": "arkserver3", "map": "Genesis2"},
                        "missing_event_roles": ["session_end"],
                    },
                    "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle": {
                        "path_type": "passive_observation_complete_role_triplet_non_evidence",
                        "authorization": "non-authorizing",
                        "authorizes_runtime_work": False,
                        "authorizes_server_work": False,
                        "authorizes_workspace_work": False,
                        "authorizes_server_operations": False,
                        "authorizes_workspace_writes": False,
                        "reads_live_logs": False,
                        "counts_as_approved_runtime_evidence": False,
                        "passive_snapshot_evidence_allowed": False,
                        "counts_toward_complete_sdk_claim_now": False,
                        "counts_toward_p0_dependency_chain_claim_now": False,
                        "target": {"instance": "arkserver", "map": "Ragnarok"},
                        "paths": [
                            "current-docs passive Ragnarok observation scope",
                            "passive_role_triplet:session_start",
                            "passive_role_triplet:session_start_rejected",
                            "passive_role_triplet:session_end",
                            "approved_bundle_missing",
                        ],
                        "requirements": [
                            "treat the documented complete passive Ragnarok triplet as diagnostic/non-evidence only",
                            "produce a copied, reviewed approved runtime principal lifecycle evidence bundle",
                        ],
                        "required_event_roles": [
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        "present_event_roles": [
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        "missing_event_roles": [],
                    },
                    "player_notice_action": {
                        "path_type": "player_notice_action",
                        "authorization": "non-authorizing",
                        "non_authorizing": True,
                        "player_notice_action_required": True,
                        "notice_action_authorized": False,
                        "player_notice_action_authorized": False,
                        "authorizes_discord": False,
                        "discord_authorized": False,
                        "authorizes_runtime_work": False,
                        "authorizes_server_operations": False,
                        "authorizes_workspace_writes": False,
                        "reads_live_logs": False,
                        "notice_sent": False,
                        "notice_dry_run_accepted": False,
                        "notice_bundle_accepted": False,
                        "counts_as_approved_runtime_evidence": False,
                        "counts_toward_complete_sdk_claim_now": False,
                        "counts_toward_p0_dependency_chain_claim_now": False,
                        "complete_sdk_claim_progress_contribution": 0,
                        "p0_dependency_chain_claim_progress_contribution": 0,
                        "paths": [
                            "player_notice_action",
                            "standing-authorized or current-turn approved player notice path required before activation",
                        ],
                        "requirements": [
                            "player-backed evidence windows require a standing-authorized or current-turn approved player_notice_action before activation",
                            "this report does not authorize Discord, beta tester notices, runtime work, server operations, live-log reads, or workspace writes",
                            "notice sent, notice dry-run accepted, and bundle accepted statuses do not satisfy approved runtime evidence or count toward SDK/P0 progress",
                        ],
                        "required_event_roles": [
                            "session_start",
                            "session_start_rejected",
                            "session_end",
                        ],
                        "missing_requirement_key": "player_notice_action",
                    },
                },
            },
        }

    def public_sdk_payload_with_overclaiming_side_lanes(self) -> dict[str, object]:
        public_sdk = self.public_sdk_payload()
        public_sdk.update(
            {
                "transfer_scriptstruct_readiness": {
                    "schema": "obelisk.transfer-scriptstruct-readiness-check.v1",
                    "status": "candidate_only_accepted",
                    "ready": True,
                    "candidate_only": True,
                    "target_set": "transfer-scriptstruct",
                    "live_ops_authorized": True,
                    "workspace_writes_authorized": True,
                    "runtime_capture_authorized": True,
                    "read_live_logs": True,
                    "reads_live_logs": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "counts_toward_complete_sdk_claim": True,
                    "counts_toward_p0_dependency_chain_claim": True,
                    "complete_sdk_claim_progress_contribution": 1,
                    "p0_dependency_chain_claim_progress_contribution": "1/4",
                },
                "buff_status_readiness": {
                    "schema": "obelisk.buff-status-readiness-check.v1",
                    "status": "candidate_ready",
                    "ready": True,
                    "candidate_only": True,
                    "buff_status_candidate_ready": True,
                    "source_manifest": {
                        "schema": "obelisk.ufunction-snapshot-manifest.v1",
                        "source": "offline_core",
                        "status": "candidate-only",
                        "target_count": 4,
                        "bound_target_count": 4,
                    },
                    "summary": {
                        "source_binding_count": 4,
                    },
                    "live_ops_authorized": True,
                    "workspace_writes_authorized": True,
                    "runtime_capture_authorized": True,
                    "read_live_logs": True,
                    "public_sdk_ready": True,
                    "v1_completion_ready": True,
                    "counts_toward_complete_sdk_claim": True,
                    "complete_sdk_claim_progress_contribution": "2/12",
                    "p0_dependency_chain_claim_progress_contribution": 1,
                },
                "dino_scalar_readiness": {
                    "schema": "obelisk.dino-scalar-readiness-check.v1",
                    "status": "candidate_ready",
                    "ready": True,
                    "accepted_for_internal_planning": True,
                    "target_set": "dino-compact-intake",
                    "source_isolation": {
                        "public_or_runtime_dino_wiring_detected": True,
                        "scanned_blocked_source_files": 3,
                    },
                    "live_ops_authorized": True,
                    "workspace_writes_authorized": True,
                    "runtime_capture_authorized": True,
                    "read_live_logs": True,
                    "dino_sdk_ready": True,
                    "public_dino_sdk_ready": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "counts_toward_public_sdk": True,
                    "counts_toward_complete_sdk_claim": True,
                    "complete_sdk_claim_progress_contribution": 1,
                    "p0_dependency_chain_claim_progress_contribution": 1,
                },
                "mission_transfer_dino_tribe_outcome_accounting": {
                    "schema": (
                        "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1"
                    ),
                    "surface": "obelisk.mission_transfer_dino_tribe.v1",
                    "status": "candidate_only",
                    "ready": True,
                    "accounting_route": "manifest_umbrella_excluded",
                    "candidate_only": False,
                    "v1_accounted": True,
                    "required_leaves": [
                        "mission",
                        "transfer",
                        "dino_policy",
                        "tribe_policy",
                        "buff_status",
                    ],
                    "observed_leaves": [
                        "mission",
                        "transfer",
                        "dino_policy",
                        "tribe_policy",
                        "buff_status",
                    ],
                    "missing_leaf_families": [],
                    "live_ops_authorized": True,
                    "workspace_writes_authorized": True,
                    "runtime_capture_authorized": True,
                    "read_live_logs": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "stable_claim_allowed": True,
                    "counts_toward_complete_sdk_claim": True,
                    "counts_toward_p0_dependency_chain_claim": True,
                    "complete_sdk_claim_progress_contribution": 5,
                    "complete_sdk_claim_progress_ratio": "5/12",
                    "p0_dependency_chain_claim_progress_contribution": "4/4",
                    "p0_dependency_chain_claim_progress_percent": 100,
                    "readiness_counts_toward_v1_accounting": True,
                },
            }
        )
        return public_sdk

    def header_gate_payload(self) -> dict[str, object]:
        return {
            "ready": True,
            "next_blocker": "runtime_bundle_and_public_header_promotion_missing",
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "proposed_symbols": ["A", "B"],
            "blockers": [],
        }

    def strict_approved_runtime_checker_contract_payload(self) -> dict[str, object]:
        return {
            "schema": status_report.APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_CHECK_REPORT_SCHEMA,
            "input_schema": status_report.APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_EVIDENCE_SCHEMA,
            "ready": True,
            "ready_scope": status_report.APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_READY_SCOPE,
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_present": True,
            "approved_runtime_evidence_ready": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_allowed": False,
            "complete_sdk_ready": False,
            "next_blocker": status_report.IDENTITY_PUBLIC_CONTRACT_GATE_MISSING_BLOCKER,
            "strict_lifecycle_triplet_selected": True,
            "strict_lifecycle_triplet_selection": {
                "accepted": True,
                "selected_roles": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
                "non_counting_context_event_count": 0,
                "non_counting_context_roles": [],
            },
            "strict_rejected_start_expected_shape": (
                status_report.APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_REJECTED_START_SHAPE
            ),
            "strict_rejected_start_observed_shape": {
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        }

    def closure_payload(self) -> dict[str, object]:
        return {
            "ready": False,
            "status": "non_ready_missing_required_artifacts",
            "evidence_dir": "/servidor/ark/workspace-offline/live-validation-logs/run",
            "missing_required_artifacts": [
                "window-manifest.env",
                "preflight-post.json",
                "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            ],
            "present_siblings": ["Obelisk.log", "window-request.json"],
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "readiness_claims": {
                "public_sdk_ready": False,
                "runtime_ready": False,
            },
        }

    def principal_start_end_runtime_evidence_payload(self) -> dict[str, object]:
        return {
            "schema": status_report.PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA,
            "ready": True,
            "ready_scope": status_report.PRINCIPAL_START_END_READY_SCOPE,
            "accepted_for_contract_review": True,
            "principal_start_end_runtime_evidence_present": True,
            "principal_start_end_runtime_evidence_ready": True,
            "resolved_inputs": [status_report.PRINCIPAL_START_END_RESOLVED_INPUT],
            "remaining_runtime_inputs": [],
            "does_not_resolve": sorted(
                status_report.PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS
            ),
            "next_review_blocker": "identity_public_contract_gate_missing",
            "diagnostic_coverage": {
                "check_join_in_progress_diagnostic_count": 1,
                "diagnostic_candidates_count_as_evidence": False,
            },
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_ready": False,
            "stable_claim_allowed": False,
            "publication_authorized": False,
            "blockers": [],
            "non_claims": [
                "principal start/end runtime evidence is not the approved three-role lifecycle evidence bundle",
                "this checker does not promote public identity, lookup, public ABI/header, permissions/admin, commands, runtime readiness, SDK readiness, stable claims, or publication",
            ],
        }

    def multi_surface_beta_capture_pack_payload(self) -> dict[str, object]:
        return {
            "schema": status_report.MULTI_SURFACE_BETA_CAPTURE_PACK_CHECK_SCHEMA,
            "status": status_report.MULTI_SURFACE_BETA_CAPTURE_PACK_VALIDATED_STATUS,
            "ready": True,
            "ready_scope": status_report.MULTI_SURFACE_BETA_CAPTURE_PACK_READY_SCOPE,
            "pack_root": "/tmp/obelisk-beta-capture-pack/pack-status-test",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "target_binding_id": "instance=arkserver|map=Ragnarok",
            "candidate_surface_count": 15,
            "blockers": [],
            "candidate_only": True,
            "current_route_blocker": "approved_runtime_evidence_missing",
            "next_required_artifact": (
                "approved_runtime_principal_lifecycle_evidence_bundle"
            ),
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_progress": False,
            "counts_as_p0_progress": False,
            "clears_approved_runtime_evidence_missing": False,
            "replaces_player_principal_evidence": False,
            "replaces_player_principal_triplet": False,
            "substitutes_for_player_principal_lifecycle_evidence": False,
            "substitutes_for_player_principal_lifecycle_triplet": False,
            "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
            "player_principal_lifecycle_evidence_substitution_allowed": False,
            "approved_runtime_evidence_substitution_allowed": False,
            "primary_evidence_substitution_allowed": False,
            "side_lane_counts_toward_sdk": False,
            "side_lane_counts_toward_p0": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "publication_ready": False,
            "stable_claim_allowed": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "non_claims": [
                "candidate pack validation is integrity-only planning context",
            ],
        }

    def discord_beta_bridge_config_payload(self) -> dict[str, object]:
        return {
            "schema": status_report.DISCORD_BETA_BRIDGE_CONFIG_CHECK_SCHEMA,
            "valid": True,
            "blockers": [],
            "env_file": "/home/flowcommunity-ark/Obelisk/local/discord-bot.env",
            "token_present": False,
            "token_value_redacted": "<missing>",
            "guild_id": "1032660680668622969",
            "beta_channel_id": "1513238083741683934",
            "event_sink": (
                "/home/flowcommunity-ark/Obelisk/local/discord-beta-bridge/events.jsonl"
            ),
            "event_sink_error": None,
            "discord_py_available": False,
            "discord_py_detail": "ModuleNotFoundError: No module named 'discord'",
            "non_authorization": {
                "authorizes_discord_send": False,
                "authorizes_rcon": False,
                "authorizes_server_start": False,
                "authorizes_server_stop": False,
                "authorizes_server_restart": False,
                "authorizes_marker_or_env_changes": False,
                "authorizes_live_log_reads": False,
                "authorizes_runtime_capture": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "stable_sdk_ready": False,
                "plugin_hub_ready": False,
                "publication_ready": False,
            },
        }

    def runtime_evidence_status_payload(self) -> dict[str, object]:
        target_key = "arkserver3:Genesis2:27017"
        return {
            "schema": status_report.RUNTIME_EVIDENCE_STATUS_SCHEMA,
            "status": "blocked_missing_lifecycle_roles",
            "ready": False,
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "stable_sdk_ready": False,
            "v1_completion_ready": False,
            "closure": {
                "status": "non_ready_missing_required_artifacts_and_lifecycle_roles",
                "ready": False,
                "missing_lifecycle_event_roles": ["session_end"],
                "missing_required_artifacts": [
                    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
                ],
                "missing_copied_lifecycle_event_triplet_labels": [
                    "OnLogout matched"
                ],
            },
            "post_reboot_passive_monitor": {
                "present": True,
                "monitor_latest_tick_utc": "2026-06-07T10:15:00Z",
                "query_status_by_target": {
                    target_key: {
                        "status": "ok",
                        "players_current": 2,
                        "presence_detected": True,
                        "approved_runtime_evidence": False,
                        "counts_as_approved_runtime_evidence": False,
                    }
                },
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            },
            "runtime_player_availability": {
                "classification": "players_detected_operator_context_non_evidence",
                "known_player_counts_by_target": {target_key: 2},
                "targets_with_players_detected": [target_key],
                "players_detected": True,
                "no_players_currently_detected": False,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
            },
            "confirmed_beta_notice": {
                "present": True,
                "completed": True,
                "standing_launch_authority_recorded": True,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
            },
            "copy_ready_log": {
                "present": True,
                "status": "source_log_not_ready",
                "copy_readiness": "not_ready_missing_roles",
                "roles_present": ["session_start", "session_start_rejected"],
                "missing_roles": ["session_end"],
                "active_observer_only_no_role_window": False,
                "copied_source_value": False,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            },
            "operator_action_summary": {
                "run_id": "20260607-runtime-window",
                "status": "blocked_missing_lifecycle_roles",
                "blocking_inputs": {
                    "route_blocker": "approved_runtime_evidence_missing",
                    "missing_lifecycle_event_roles": ["session_end"],
                    "missing_required_artifacts": [
                        "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
                    ],
                    "missing_copied_lifecycle_event_triplet_labels": [
                        "OnLogout matched"
                    ],
                },
                "operator_context_inputs": {
                    "post_reboot_passive_monitor_log_supplied": True,
                    "monitor_latest_tick_utc": "2026-06-07T10:15:00Z",
                    "monitor_query_targets": [target_key],
                    "confirmed_beta_notice_json_supplied": True,
                    "confirmed_beta_notice_completed": True,
                    "copy_ready_json_supplied": True,
                    "copy_ready_status": "source_log_not_ready",
                    "copy_readiness": "not_ready_missing_roles",
                    "copy_ready_missing_roles": ["session_end"],
                    "copy_ready_roles_present": [
                        "session_start",
                        "session_start_rejected",
                    ],
                    "runtime_player_availability": {
                        "classification": "players_detected_operator_context_non_evidence",
                        "known_player_counts_by_target": {target_key: 2},
                        "targets_with_players_detected": [target_key],
                        "players_detected": True,
                        "no_players_currently_detected": False,
                        "approved_runtime_evidence": False,
                        "counts_as_approved_runtime_evidence": False,
                        "runtime_ready": False,
                        "public_sdk_ready": False,
                    },
                    "context_inputs_are_non_evidence": True,
                    "approved_runtime_evidence": False,
                    "counts_as_approved_runtime_evidence": False,
                    "runtime_ready": False,
                    "public_sdk_ready": False,
                },
                "resume_context": {
                    "next_status_input_needed": (
                        "same_run_roles_and_checked_sibling_artifacts"
                    )
                },
            },
            "route_gate": {
                "current_route_blocker": "approved_runtime_evidence_missing",
                "runtime_ready": False,
                "public_sdk_ready": False,
                "promotion_ready": False,
            },
            "first_machine_next_action": {
                "present": True,
                "action": "wait_for_session_end",
                "action_kind": "status_synthesized",
                "command_status": "NOT PROVIDED",
                "exact_command_available": False,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "runtime_ready": False,
                "public_sdk_ready": False,
            },
            "non_claims": [
                "runtime evidence status report only",
                "passive monitor and beta notice context remain non-evidence",
            ],
        }

    def stale_operator_live_diagnostic_blockers_payload(self) -> dict[str, object]:
        stale_blocker = {
            "id": "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
            "blocker": "diagnostic_fname_drift_blocks_accepted_events",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "diagnostic_fname_mismatch_lines_present": True,
            "diagnostic_fname_drift": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
        }
        return {
            "schema": status_report.CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
            "status": "blocked_approved_runtime_evidence_missing",
            "source": "operator_supplied_current_redacted_state",
            "planner_did_not_read_live_logs": True,
            "status_report_only": True,
            "blocker_context_only": True,
            "diagnostic_non_evidence": True,
            "active_ark_server_count": 2,
            "active_server_targets": [{"instance": "arkserver", "map": "Ragnarok"}],
            "current_route_blocker": "approved_runtime_evidence_missing",
            "next_blockers": [stale_blocker],
            "next_blocker_ids": [stale_blocker["id"]],
            "primary_next_blocker": stale_blocker["blocker"],
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
        }

    def promotable_ragnarok_runtime_evidence_status_payload(self) -> dict[str, object]:
        payload = self.runtime_evidence_status_payload()
        stale_blockers = self.stale_operator_live_diagnostic_blockers_payload()
        operator_summary = payload["operator_action_summary"]
        self.assertIsInstance(operator_summary, dict)
        blocking_inputs = operator_summary["blocking_inputs"]
        self.assertIsInstance(blocking_inputs, dict)
        blocking_inputs["current_live_diagnostic_blockers"] = stale_blockers
        payload["current_live_diagnostic_blockers"] = stale_blockers
        payload["current_live_posture"] = {
            "schema": "obelisk.current-live-posture-status.v1",
            "status": "promotable_observer_posture",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "observer_enabled": True,
            "observer_window_promotable": True,
            "plugins_disabled": True,
            "dispatch_limit": 0,
            "log_limit": 10,
            "diagnostic_candidates_enabled": False,
            "diagnostic_env_present": False,
            "player_principal_lifecycle_diagnostic_count": 0,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "counts_toward_sdk": False,
            "counts_toward_p0_dependency_chain": False,
        }
        return payload

    def public_contract_decisions_payload(self) -> dict[str, object]:
        return {
            "private_logout_correlation_internal_blocker": {
                "id": "private_logout_correlation_internal_blocker",
                "status": "blocked/internal-planning",
                "visibility": "internal_non_public_planning_only",
                "current_blocker": "private_logout_correlation_missing",
                "blocks_before_public_identity_promotion": True,
                "required_internal_contract": [
                    "session_end/logout remains unresolved and fail-closed unless a private correlated principal token is present",
                ],
                "forbidden_public_outcomes": [
                    "no public lookup API",
                    "no public identity exposure",
                    "no public ABI readiness",
                    "no public header readiness",
                    "no live authorization",
                ],
                "public_lookup_ready": True,
                "public_abi_ready": True,
                "public_header_ready": True,
                "live_ops_authorized": True,
                "non_claims": [
                    "private logout correlation planning is internal only: no public lookup",
                    "private logout correlation planning is internal only: no identity exposure",
                    "private logout correlation planning is internal only: no ABI/header readiness",
                    "private logout correlation planning is internal only: no live authorization",
                ],
            }
        }

    def test_summary_preserves_blocked_non_claim_state(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            public_contract_decisions=self.public_contract_decisions_payload(),
            closure=self.closure_payload(),
            closure_returncode=1,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(
            report["source_current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["source_remaining_route_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(report["source_overclaimed_route_flags"], [])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        critical_path = report["critical_path_summary"]
        self.assertEqual(
            critical_path["schema"],
            "obelisk.sdk-status-critical-path-summary.v1",
        )
        self.assertTrue(critical_path["status_report_only"])
        self.assertEqual(critical_path["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            critical_path["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            critical_path["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(critical_path["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(critical_path["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(critical_path["approved_runtime_evidence_ready"])
        self.assertFalse(critical_path["public_sdk_ready"])
        self.assertFalse(critical_path["runtime_ready"])
        self.assertFalse(critical_path["stable_claim_allowed"])
        self.assertFalse(critical_path["live_ops_authorized"])
        self.assertEqual(
            critical_path["debug_first_blocker_chain"],
            (
                "approved_runtime_evidence_missing -> approved runtime principal "
                "lifecycle evidence bundle -> identity public contract gate"
            ),
        )
        self.assertIn("Critical-path status only", critical_path["non_claim"])
        stable_blockers = report["stable_sdk_remaining_blockers"]
        self.assertEqual(
            stable_blockers["schema"],
            "obelisk.sdk-status-stable-sdk-remaining-blockers.v1",
        )
        self.assertTrue(stable_blockers["status_report_only"])
        self.assertFalse(stable_blockers["ready"])
        self.assertFalse(stable_blockers["stable_claim_allowed"])
        self.assertFalse(stable_blockers["stable_sdk_ready"])
        self.assertFalse(stable_blockers["runtime_ready"])
        self.assertFalse(stable_blockers["public_sdk_ready"])
        self.assertEqual(stable_blockers["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            stable_blockers["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            stable_blockers["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(stable_blockers["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(stable_blockers["complete_sdk_remaining_for_claim_count"], 12)
        self.assertEqual(stable_blockers["remaining_sdk_blocker_surface_count"], 12)
        self.assertEqual(stable_blockers["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(stable_blockers["p0_dependency_chain_remaining_for_claim_count"], 4)
        self.assertEqual(stable_blockers["remaining_p0_dependency_chain_surface_count"], 4)
        self.assertEqual(stable_blockers["current_p0_surface"], "obelisk.player_identity.v1")
        self.assertEqual(stable_blockers["operator_context_count"], 0)
        self.assertEqual(stable_blockers["operator_context_ids"], [])
        self.assertFalse(stable_blockers["operator_context_counts_as_approved_runtime_evidence"])
        self.assertFalse(stable_blockers["operator_context_counts_as_sdk_progress"])
        self.assertFalse(stable_blockers["operator_context_counts_toward_p0_dependency_chain"])
        self.assertEqual(stable_blockers["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(stable_blockers["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn("Stable SDK remaining-blocker report only", stable_blockers["non_claim"])
        operator_context = report["operator_context_summary"]
        self.assertEqual(
            operator_context["schema"],
            "obelisk.sdk-status-operator-context-summary.v1",
        )
        self.assertEqual(operator_context["context_count"], 0)
        self.assertEqual(operator_context["context_ids"], [])
        self.assertFalse(operator_context["counts_toward_complete_sdk_claim"])
        self.assertEqual(operator_context["complete_sdk_claim_progress_contribution"], 0)
        debug_first = report["debug_first_acceleration"]
        self.assertEqual(
            debug_first["schema"],
            "obelisk.sdk-status-debug-first-acceleration.v1",
        )
        self.assertTrue(debug_first["status_report_only"])
        self.assertTrue(debug_first["debug_first"])
        self.assertEqual(debug_first["status"], "blocked")
        self.assertEqual(
            debug_first["blocker_chain"],
            [
                "approved_runtime_evidence_missing",
                "approved_runtime_principal_lifecycle_evidence_bundle",
                "identity_public_contract_gate_missing",
            ],
        )
        self.assertEqual(
            debug_first["compact_blocker_chain"],
            (
                "approved_runtime_evidence_missing -> approved runtime principal "
                "lifecycle evidence bundle -> identity public contract gate"
            ),
        )
        self.assertEqual(
            debug_first["current_focus"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            debug_first["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            debug_first["next_checker"],
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        )
        self.assertEqual(
            debug_first["expected_next_route_blocker_after_checker_acceptance"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            debug_first["required_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(debug_first["authorization"], "status-only")
        self.assertFalse(debug_first["live_ops_authorized"])
        self.assertFalse(debug_first["runtime_capture_authorized"])
        self.assertFalse(debug_first["workspace_writes_authorized"])
        self.assertFalse(debug_first["reads_live_logs"])
        self.assertFalse(debug_first["approved_runtime_evidence_ready"])
        self.assertFalse(debug_first["public_sdk_ready"])
        self.assertFalse(debug_first["runtime_ready"])
        self.assertFalse(debug_first["stable_claim_allowed"])
        self.assertEqual(debug_first["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(debug_first["p0_dependency_chain_claim_progress_contribution"], 0)
        roadmap = report["p0_offline_roadmap"]
        self.assertEqual(
            roadmap["schema"],
            "obelisk.sdk-status-p0-offline-roadmap.v1",
        )
        self.assertTrue(roadmap["status_report_only"])
        self.assertTrue(roadmap["roadmap_only"])
        self.assertEqual(roadmap["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            roadmap["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(roadmap["after_runtime_evidence"], "identity_public_contract_gate_missing")
        self.assertEqual(
            roadmap["downstream_offline_order"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(
            roadmap["next_offline_surface_after_runtime_evidence"],
            "obelisk.player_identity.v1",
        )
        self.assertEqual(
            roadmap["post_identity_bridge_required_artifact"],
            "hash_bound_player_identity_promotion_certificate",
        )
        self.assertEqual(
            roadmap["post_identity_bridge_required_schema"],
            "obelisk.player-identity-promotion-certificate.v1",
        )
        self.assertEqual(
            roadmap["post_identity_bridge_blocker"],
            "player_identity_promotion_certificate_missing",
        )
        self.assertEqual(
            roadmap["post_identity_bridge_status"],
            "required_after_identity_public_contract_before_permissions_admin",
        )
        self.assertTrue(roadmap["post_identity_bridge_hash_bound"])
        self.assertFalse(roadmap["post_identity_bridge_counts_toward_p0_dependency_chain"])
        self.assertFalse(roadmap["post_identity_bridge_promotion_ready"])
        self.assertEqual(
            roadmap["post_permissions_admin_bridge_required_artifact"],
            "hash_bound_permissions_admin_promotion_certificate",
        )
        self.assertEqual(
            roadmap["post_permissions_admin_bridge_required_schema"],
            "obelisk.permissions-admin-promotion-certificate.v1",
        )
        self.assertFalse(
            roadmap["post_permissions_admin_bridge_counts_toward_p0_dependency_chain"]
        )
        self.assertEqual(
            roadmap["post_command_chat_response_bridge_required_artifact"],
            "hash_bound_command_chat_response_path_promotion_certificate",
        )
        self.assertEqual(
            roadmap["post_command_chat_response_bridge_required_schema"],
            "obelisk.command-chat-response-path-promotion-certificate.v1",
        )
        self.assertFalse(
            roadmap["post_command_chat_response_bridge_counts_toward_p0_dependency_chain"]
        )
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_artifact"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_schema"],
            "obelisk.commands-replies-promotion-certificate.v1",
        )
        self.assertEqual(
            roadmap["commands_replies_final_gate_public_readiness_report_schema"],
            "obelisk.commands-replies-public-readiness-check.v1",
        )
        self.assertEqual(roadmap["commands_replies_final_gate_status"], "missing_non_counting")
        self.assertFalse(roadmap["commands_replies_final_gate_source_present"])
        self.assertFalse(roadmap["commands_replies_final_gate_certificate_present"])
        self.assertFalse(roadmap["commands_replies_final_gate_source_hash_bound"])
        self.assertEqual(
            roadmap["commands_replies_final_gate_missing_required_artifact"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertTrue(roadmap["commands_replies_final_gate_hash_bound"])
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_p0_dependency_chain"]
        )
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_complete_sdk_claim"]
        )
        self.assertFalse(roadmap["commands_replies_final_gate_promotion_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_public_sdk_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_runtime_ready"])
        final_gate = report["commands_replies_final_gate"]
        self.assertEqual(final_gate["status"], "missing_non_counting")
        self.assertTrue(final_gate["status_report_only"])
        self.assertFalse(final_gate["source_present"])
        self.assertFalse(final_gate["certificate_present"])
        self.assertFalse(final_gate["source_hash_bound"])
        self.assertFalse(final_gate["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(final_gate["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(final_gate["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(roadmap["promotion_ready"])
        self.assertEqual(roadmap["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(roadmap["approved_runtime_evidence_ready"])
        self.assertFalse(roadmap["runtime_ready"])
        self.assertFalse(roadmap["public_sdk_ready"])
        self.assertFalse(roadmap["stable_claim_allowed"])
        self.assertFalse(roadmap["authorizes_runtime_work"])
        self.assertFalse(roadmap["authorizes_server_operations"])
        self.assertFalse(roadmap["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(roadmap["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(roadmap["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(
            [step["surface"] for step in roadmap["steps"]],
            [
                "runtime_principal_lifecycle_evidence",
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
        )
        self.assertEqual(roadmap["steps"][0]["status"], "current_blocker")
        self.assertEqual(
            roadmap["steps"][1]["status"],
            "blocked_until_runtime_evidence_checker_acceptance",
        )
        self.assertEqual(
            roadmap["steps"][1]["success_advances_to"],
            "player_identity_promotion_certificate_missing",
        )
        self.assertEqual(
            roadmap["steps"][1]["post_contract_bridge_required_artifact"],
            "hash_bound_player_identity_promotion_certificate",
        )
        self.assertFalse(
            roadmap["steps"][1]["post_contract_bridge_counts_toward_p0_dependency_chain"]
        )
        self.assertEqual(
            roadmap["steps"][2]["status"],
            "blocked_until_hash_bound_player_identity_promotion_certificate",
        )
        self.assertEqual(
            roadmap["steps"][2]["required_upstream_artifact"],
            "hash_bound_player_identity_promotion_certificate",
        )
        self.assertEqual(
            roadmap["steps"][2]["post_contract_bridge_required_artifact"],
            "hash_bound_permissions_admin_promotion_certificate",
        )
        self.assertFalse(
            roadmap["steps"][2]["post_contract_bridge_counts_toward_p0_dependency_chain"]
        )
        self.assertEqual(
            roadmap["steps"][3]["required_upstream_artifact"],
            "hash_bound_permissions_admin_promotion_certificate",
        )
        self.assertEqual(
            roadmap["steps"][3]["post_contract_bridge_required_artifact"],
            "hash_bound_command_chat_response_path_promotion_certificate",
        )
        self.assertFalse(
            roadmap["steps"][3]["post_contract_bridge_counts_toward_p0_dependency_chain"]
        )
        self.assertEqual(
            roadmap["steps"][4]["required_upstream_artifact"],
            "hash_bound_command_chat_response_path_promotion_certificate",
        )
        self.assertIn("P0 roadmap is offline planning/status only", roadmap["non_claim"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["p0_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["total"], 12)
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["sdk_counts"]["remaining_for_claim_count"], 12)
        self.assertEqual(report["p0_counts"]["total"], 4)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["remaining_for_claim_count"], 4)
        self.assertNotIn(
            "v1_sdk_report_sections.active_side_lane_review.remaining_for_claim_count",
            report["non_counting_false_progress_alias_violations"],
        )
        self.assertEqual(len(report["actionable_paths"]), 4)
        self.assertIn("historical_theisland_candidate_missing_sidecars", report["actionable_paths"])
        self.assertIn("active_genesis2_passive_missing_roles", report["action_paths"])
        self.assertIn(
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle",
            report["action_paths"],
        )
        self.assertIn("player_notice_action", report["action_paths"])
        self.assertFalse(
            report["actionable_paths"]["historical_theisland_candidate_missing_sidecars"][
                "authorizes_runtime_work"
            ]
        )
        self.assertFalse(
            report["actionable_paths"]["active_genesis2_passive_missing_roles"][
                "counts_as_approved_runtime_evidence"
            ]
        )
        self.assertEqual(
            report["actionable_paths"]["active_genesis2_passive_missing_roles"]["evidence_status"],
            "diagnostic_passive_non_evidence",
        )
        self.assertEqual(
            report["actionable_paths"]["historical_theisland_candidate_missing_sidecars"][
                "path_status"
            ],
            "historical_theisland_sidecar_closure",
        )
        self.assertEqual(
            report["actionable_paths"]["active_genesis2_passive_missing_roles"]["path_status"],
            "active_genesis2_current_roles_unverified",
        )
        self.assertEqual(
            report["actionable_paths"][
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
            ]["path_status"],
            "active_ragnarok_current_roles_unverified",
        )
        self.assertFalse(
            report["actionable_paths"][
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
            ]["authorizes_server_work"]
        )
        self.assertFalse(
            report["actionable_paths"][
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
            ]["authorizes_workspace_work"]
        )
        self.assertFalse(report["authorizations"]["live_ops_authorized"])
        self.assertFalse(report["authorizations"]["passive_snapshots_count_as_evidence"])
        self.assertFalse(report["approved_in_game_evidence_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        approved_in_game = report["approved_in_game_evidence"]
        self.assertEqual(
            approved_in_game["schema"],
            "obelisk.approved-in-game-evidence-status.v1",
        )
        self.assertFalse(approved_in_game["ready"])
        self.assertFalse(approved_in_game["approved_in_game_ready"])
        self.assertFalse(approved_in_game["approved_in_game_evidence_ready"])
        self.assertFalse(approved_in_game["approved_runtime_evidence"])
        self.assertFalse(approved_in_game["approved_runtime_evidence_ready"])
        self.assertFalse(approved_in_game["evidence_bundle_accepted"])
        self.assertFalse(approved_in_game["complete_lifecycle_event_triplet_approved"])
        self.assertFalse(
            approved_in_game["complete_lifecycle_event_triplet_observed_diagnostic_only"]
        )
        self.assertEqual(
            approved_in_game["diagnostic_complete_triplet_path_ids"],
            [],
        )
        self.assertEqual(
            approved_in_game["missing_role_path_ids"],
            [
                "active_genesis2_passive_missing_roles",
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle",
            ],
        )
        self.assertEqual(
            approved_in_game["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            approved_in_game["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(approved_in_game["current_turn_scope_required"])
        self.assertTrue(approved_in_game["active_runtime_window_requires_standing_or_current_scope"])
        self.assertTrue(approved_in_game["standing_launch_authority_recorded"])
        self.assertTrue(approved_in_game["standing_launch_authority_satisfies_runtime_window_scope"])
        self.assertTrue(
            approved_in_game["runtime_window_can_be_prepared_under_standing_authority"]
        )
        self.assertFalse(
            approved_in_game["runtime_window_preparation_counts_as_approved_runtime_evidence"]
        )
        self.assertFalse(
            approved_in_game["runtime_window_preparation_counts_toward_sdk"]
        )
        self.assertFalse(
            approved_in_game["standing_launch_authority_counts_as_runtime_evidence"]
        )
        self.assertFalse(
            approved_in_game["standing_launch_authority_counts_toward_p0_dependency_chain"]
        )
        self.assertTrue(approved_in_game["player_notice_action_required"])
        self.assertFalse(approved_in_game["live_ops_authorized"])
        self.assertFalse(approved_in_game["runtime_capture_authorized"])
        self.assertFalse(approved_in_game["reads_live_logs"])
        self.assertEqual(approved_in_game["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(approved_in_game["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(
            approved_in_game["blocker_reason"],
            "approved_runtime_principal_lifecycle_evidence_bundle_missing_or_unaccepted",
        )
        self.assertIn(
            "passive triplets",
            approved_in_game["non_claim"],
        )
        post_evidence = report["post_evidence_p0_lock_simulation"]
        self.assertTrue(post_evidence["simulation_only"])
        self.assertTrue(post_evidence["status_report_only"])
        self.assertTrue(post_evidence["source_present"])
        self.assertFalse(post_evidence["approved_runtime_evidence_accepted"])
        self.assertEqual(
            post_evidence["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            post_evidence["simulated_route_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertTrue(post_evidence["identity_public_contract_required"])
        self.assertFalse(post_evidence["public_sdk_ready"])
        self.assertFalse(post_evidence["runtime_ready"])
        self.assertFalse(post_evidence["counts_toward_complete_sdk_claim"])
        self.assertFalse(post_evidence["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(post_evidence["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(post_evidence["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(post_evidence["live_ops_authorized"])
        self.assertFalse(post_evidence["workspace_writes_authorized"])
        self.assertFalse(post_evidence["runtime_capture_authorized"])
        self.assertEqual(
            report["route_gate"]["post_evidence_p0_lock_simulation"],
            post_evidence,
        )
        self.assertFalse(report["route_gate"]["live_ops_authorized"])
        self.assertFalse(report["route_gate"]["workspace_writes_authorized"])
        self.assertFalse(report["route_gate"]["runtime_capture_authorized"])
        self.assertEqual(
            set(report["fastest_next_sdk_unblock"]["action_paths"]),
            {
                "historical_theisland_candidate_missing_sidecars",
                "active_genesis2_passive_missing_roles",
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle",
                "player_notice_action",
            },
        )
        self.assertEqual(
            report["fastest_next_sdk_unblock"]["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(report["fastest_next_sdk_unblock"]["current_turn_scope_required"])
        self.assertTrue(
            report["fastest_next_sdk_unblock"][
                "active_runtime_window_requires_standing_or_current_scope"
            ]
        )
        self.assertTrue(
            report["fastest_next_sdk_unblock"]["standing_launch_authority_recorded"]
        )
        self.assertFalse(
            report["fastest_next_sdk_unblock"][
                "active_runtime_window_requires_current_turn_scope"
            ]
        )
        self.assertIn(
            "recorded standing launch authority",
            report["fastest_next_sdk_unblock"]["current_turn_scope_requirement"],
        )
        self.assertIn(
            "prepare necessary ObeliskSDK runtime windows",
            report["fastest_next_sdk_unblock"]["current_turn_scope_requirement"],
        )
        self.assertIn(
            "exact current-turn operator approval",
            report["fastest_next_sdk_unblock"]["current_turn_scope_requirement"],
        )
        self.assertFalse(report["fastest_next_sdk_unblock"]["live_ops_authorized"])
        self.assertFalse(report["fastest_next_sdk_unblock"]["workspace_writes_authorized"])
        self.assertFalse(report["fastest_next_sdk_unblock"]["runtime_capture_authorized"])
        self.assertTrue(report["fastest_next_sdk_unblock"]["player_notice_action_required"])
        self.assertFalse(report["fastest_next_sdk_unblock"]["discord_authorized"])
        self.assertFalse(report["fastest_next_sdk_unblock"]["reads_live_logs"])
        self.assertFalse(
            report["fastest_next_sdk_unblock"][
                "runtime_window_preparation_counts_as_approved_runtime_evidence"
            ]
        )
        self.assertFalse(
            report["fastest_next_sdk_unblock"]["runtime_window_preparation_counts_toward_sdk"]
        )
        self.assertFalse(
            report["fastest_next_sdk_unblock"][
                "standing_launch_authority_counts_as_runtime_evidence"
            ]
        )
        self.assertFalse(
            report["fastest_next_sdk_unblock"][
                "standing_launch_authority_counts_toward_complete_sdk_claim"
            ]
        )
        self.assertFalse(
            report["fastest_next_sdk_unblock"]["counts_as_approved_runtime_evidence"]
        )
        self.assertFalse(report["header_gate"]["public_header_allowed"])
        self.assertFalse(report["header_gate"]["public_header_ready"])
        self.assertFalse(report["header_gate"]["ready"])
        self.assertEqual(
            report["header_gate"]["ready_scope"],
            "normalized_status_report_only_not_public_header_readiness",
        )
        self.assertTrue(report["header_gate"]["source_ready"])
        self.assertTrue(report["header_gate"]["accepted_for_header_gate_review"])
        private_correlation = report["private_logout_correlation"]
        self.assertTrue(private_correlation["internal_blocker_active"])
        self.assertTrue(private_correlation["blocks_before_public_identity_promotion"])
        self.assertEqual(
            private_correlation["current_blocker"],
            "private_logout_correlation_missing",
        )
        self.assertFalse(private_correlation["public_lookup_allowed"])
        self.assertFalse(private_correlation["public_lookup_ready"])
        self.assertFalse(private_correlation["identity_exposure_allowed"])
        self.assertFalse(private_correlation["public_abi_ready"])
        self.assertFalse(private_correlation["public_header_ready"])
        self.assertFalse(private_correlation["live_authorization_allowed"])
        self.assertFalse(private_correlation["live_ops_authorized"])
        self.assertIn(
            "public_lookup_ready",
            private_correlation["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "live_ops_authorized",
            private_correlation["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn("no public lookup", " ".join(private_correlation["non_claims"]))
        self.assertIn("no identity exposure", " ".join(private_correlation["non_claims"]))
        self.assertIn("no ABI/header readiness", " ".join(private_correlation["non_claims"]))
        self.assertIn("no live authorization", " ".join(private_correlation["non_claims"]))
        self.assertEqual(
            report["internal_blockers"]["private_logout_correlation"]["current_blocker"],
            "private_logout_correlation_missing",
        )
        self.assertFalse(report["closure"]["server_operations_authorized"])
        self.assertFalse(report["closure"]["workspace_writes_authorized"])
        self.assertIn("window-manifest.env", report["closure"]["missing_required_artifacts"])
        self.assertTrue(any("does not authorize" in claim for claim in report["non_claims"]))
        self.assertTrue(any("no public lookup" in claim for claim in report["non_claims"]))
        self.assertTrue(
            any("post_evidence_p0_lock_simulation" in claim for claim in report["non_claims"])
        )

    def test_commands_replies_final_gate_present_context_stays_non_counting(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["commands_replies_promotion_certificate_build_report"] = {
            "schema": "obelisk.commands-replies-promotion-certificate-build-report.v1",
            "status": "built",
            "certificate_artifact_schema": (
                "obelisk.commands-replies-promotion-certificate.v1"
            ),
            "certificate_written": True,
            "certificate_sha256": "a" * 64,
            "certificate_binding": {
                "path": "tests/core/generated-commands-replies-certificate.json",
                "sha256": "a" * 64,
            },
            "commands_replies_public_readiness_valid": True,
            "commands_replies_public_readiness_accepted_for_planning": True,
            "upstream_command_response_promotion_certificate_valid": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        final_gate = report["commands_replies_final_gate"]
        self.assertEqual(final_gate["status"], "present_non_counting")
        self.assertTrue(final_gate["status_report_only"])
        self.assertTrue(final_gate["source_present"])
        self.assertEqual(
            final_gate["source_key"],
            "commands_replies_promotion_certificate_build_report",
        )
        self.assertTrue(final_gate["certificate_present"])
        self.assertTrue(final_gate["certificate_binding_present"])
        self.assertTrue(final_gate["source_hash_bound"])
        self.assertIsNone(final_gate["missing_required_artifact"])
        self.assertFalse(final_gate["promotion_ready"])
        self.assertFalse(final_gate["public_sdk_ready"])
        self.assertFalse(final_gate["runtime_ready"])
        self.assertFalse(final_gate["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(final_gate["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(final_gate["p0_dependency_chain_claim_progress_contribution"], 0)

        roadmap = report["p0_offline_roadmap"]
        self.assertEqual(
            roadmap["commands_replies_final_gate_status"],
            "present_non_counting",
        )
        self.assertTrue(roadmap["commands_replies_final_gate_source_present"])
        self.assertTrue(roadmap["commands_replies_final_gate_certificate_present"])
        self.assertTrue(roadmap["commands_replies_final_gate_source_hash_bound"])
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_p0_dependency_chain"]
        )
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_complete_sdk_claim"]
        )
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        compact = status_report.format_compact_summary(report)
        self.assertIn("commands_replies_final_gate_status=present_non_counting", compact)
        self.assertIn("commands_replies_final_gate_present=true", compact)
        self.assertIn("SDK=0/12", compact)
        self.assertIn("P0=0/4", compact)

    def test_commands_replies_inline_final_gate_payload_is_unbound_context(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["hash_bound_commands_replies_promotion_certificate"] = {
            "schema": "obelisk.commands-replies-promotion-certificate.v1",
            "status": "blocked_public_header_gate_missing",
            "input_bindings": {
                "commands_replies_public_readiness": {
                    "path": "docs/commands-replies-public-readiness.check.json",
                    "sha256": "a" * 64,
                },
            },
            "evidence": {
                "input_binding_sha256": "b" * 64,
            },
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        final_gate = report["commands_replies_final_gate"]
        self.assertEqual(final_gate["status"], "missing_or_unbound_non_counting")
        self.assertTrue(final_gate["source_present"])
        self.assertEqual(
            final_gate["source_key"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertTrue(final_gate["certificate_present"])
        self.assertFalse(final_gate["certificate_binding_present"])
        self.assertFalse(final_gate["source_hash_bound"])
        self.assertFalse(final_gate["hash_bound_requirement_met"])
        self.assertEqual(
            final_gate["missing_required_artifact"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertFalse(final_gate["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(final_gate["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(final_gate["p0_dependency_chain_claim_progress_contribution"], 0)

        roadmap = report["p0_offline_roadmap"]
        self.assertEqual(
            roadmap["commands_replies_final_gate_status"],
            "missing_or_unbound_non_counting",
        )
        self.assertTrue(roadmap["commands_replies_final_gate_source_present"])
        self.assertTrue(roadmap["commands_replies_final_gate_certificate_present"])
        self.assertFalse(roadmap["commands_replies_final_gate_source_hash_bound"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")

    def test_principal_start_end_runtime_evidence_reports_non_counting_milestone(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            principal_start_end_runtime_evidence=(
                self.principal_start_end_runtime_evidence_payload()
            ),
            principal_start_end_runtime_evidence_path=(
                "/tmp/principal-start-end-evidence.check.json"
            ),
            principal_start_end_runtime_evidence_source="provided_report_path",
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(
            report["remaining_route_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(
            report["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            report["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            report["critical_path_summary"]["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["critical_path_summary"]["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["p0_offline_roadmap"]["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["p0_offline_roadmap"]["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["p0_offline_roadmap"]["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )

        start_end = report["principal_start_end_runtime_evidence"]
        self.assertTrue(start_end["source_present"])
        self.assertEqual(start_end["source_kind"], "provided_report_path")
        self.assertTrue(start_end["accepted_for_contract_review"])
        self.assertTrue(start_end["principal_start_end_runtime_evidence_present"])
        self.assertTrue(start_end["principal_start_end_runtime_evidence_ready"])
        self.assertEqual(
            start_end["resolved_inputs"],
            [status_report.PRINCIPAL_START_END_RESOLVED_INPUT],
        )
        self.assertFalse(start_end["approved_runtime_evidence"])
        self.assertFalse(start_end["approved_runtime_evidence_present"])
        self.assertFalse(start_end["approved_runtime_evidence_ready"])
        self.assertFalse(start_end["runtime_ready"])
        self.assertFalse(start_end["public_sdk_ready"])
        self.assertFalse(start_end["stable_claim_allowed"])
        self.assertFalse(start_end["counts_toward_complete_sdk_claim"])
        self.assertFalse(start_end["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(start_end["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(start_end["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(start_end["blockers"], [])
        self.assertEqual(start_end["source_overclaimed_readiness_or_authorization_flags"], [])
        self.assertEqual(start_end["source_overclaimed_progress_flags"], [])
        self.assertEqual(
            report["partial_contract_review_inputs"]["accepted_input_ids"],
            ["principal_start_end_runtime_evidence"],
        )
        self.assertFalse(
            report["partial_contract_review_inputs"]["counts_as_approved_runtime_evidence"]
        )
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)

        text = status_report.format_text(report)
        self.assertIn(
            "principal_start_end_runtime_evidence: source_present=true; "
            "accepted_for_contract_review=true",
            text,
        )
        self.assertIn("approved_runtime_evidence=false", text)
        compact = status_report.format_compact_summary(report)
        self.assertIn(
            "Principal start/end input: source_present=true; "
            "accepted_for_contract_review=true; approved_runtime_evidence=false; "
            "runtime=false; public_sdk=false; SDK_progress=0; P0_progress=0",
            compact,
        )

    def test_principal_start_end_runtime_evidence_overclaims_are_rejected_and_zeroed(self) -> None:
        start_end_payload = self.principal_start_end_runtime_evidence_payload()
        start_end_payload.update(
            {
                "approved_runtime_evidence": True,
                "approved_runtime_evidence_present": True,
                "approved_runtime_evidence_ready": True,
                "counts_as_approved_runtime_evidence": True,
                "runtime_ready": True,
                "public_sdk_ready": True,
                "stable_claim_allowed": True,
                "counts_toward_complete_sdk_claim": True,
                "counts_toward_p0_dependency_chain_claim": True,
                "complete_sdk_claim_progress_contribution": "1/12",
                "p0_dependency_chain_claim_progress_contribution": "1/4",
            }
        )

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            principal_start_end_runtime_evidence=start_end_payload,
            principal_start_end_runtime_evidence_path=(
                "/tmp/principal-start-end-evidence.check.json"
            ),
            principal_start_end_runtime_evidence_source="provided_report_path",
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

        start_end = report["principal_start_end_runtime_evidence"]
        self.assertTrue(start_end["source_present"])
        self.assertFalse(start_end["accepted_for_contract_review"])
        self.assertFalse(start_end["principal_start_end_runtime_evidence_present"])
        self.assertFalse(start_end["principal_start_end_runtime_evidence_ready"])
        self.assertTrue(start_end["source_principal_start_end_runtime_evidence_ready"])
        self.assertEqual(start_end["resolved_inputs"], [])
        self.assertFalse(start_end["approved_runtime_evidence"])
        self.assertFalse(start_end["approved_runtime_evidence_present"])
        self.assertFalse(start_end["approved_runtime_evidence_ready"])
        self.assertFalse(start_end["runtime_ready"])
        self.assertFalse(start_end["public_sdk_ready"])
        self.assertFalse(start_end["stable_claim_allowed"])
        self.assertFalse(start_end["counts_toward_complete_sdk_claim"])
        self.assertFalse(start_end["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(start_end["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(start_end["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "principal_start_end_runtime_evidence_public_sdk_ready_not_false",
            start_end["blockers"],
        )
        self.assertIn(
            "public_sdk_ready",
            start_end["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "runtime_ready",
            start_end["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "approved_runtime_evidence_present",
            start_end["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_contribution",
            start_end["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "p0_dependency_chain_claim_progress_contribution",
            start_end["source_overclaimed_progress_flags"],
        )
        self.assertEqual(report["partial_contract_review_inputs"]["accepted_input_ids"], [])
        self.assertIn(
            "principal_start_end_runtime_evidence",
            report["source_overclaim_summary"]["components"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

    def test_multi_surface_beta_capture_pack_reports_planning_context_only(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            multi_surface_beta_capture_pack=(
                self.multi_surface_beta_capture_pack_payload()
            ),
            multi_surface_beta_capture_pack_path=(
                "/tmp/multi-surface-beta-capture-pack.check.json"
            ),
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

        pack = report["multi_surface_beta_capture_pack"]
        self.assertTrue(pack["source_present"])
        self.assertTrue(pack["source_ready"])
        self.assertTrue(pack["candidate_pack_validated"])
        self.assertEqual(pack["status"], "candidate_pack_validated")
        self.assertEqual(pack["source_status"], "candidate_pack_validated")
        self.assertEqual(
            pack["source_ready_scope"],
            "candidate_capture_pack_integrity_only",
        )
        self.assertEqual(pack["target"], {"instance": "arkserver", "map": "Ragnarok"})
        self.assertEqual(pack["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(pack["candidate_surface_count"], 15)
        self.assertEqual(pack["surface_count"], 15)
        self.assertEqual(
            pack["context"]["status"],
            "candidate_pack_validated",
        )
        self.assertEqual(pack["context"]["target"]["map"], "Ragnarok")
        self.assertEqual(pack["context"]["candidate_surface_count"], 15)
        self.assertFalse(pack["ready"])
        self.assertFalse(pack["approved_runtime_evidence"])
        self.assertFalse(pack["approved_runtime_evidence_present"])
        self.assertFalse(pack["approved_runtime_evidence_ready"])
        self.assertFalse(pack["counts_as_approved_runtime_evidence"])
        self.assertFalse(pack["counts_as_runtime_evidence"])
        self.assertFalse(pack["counts_as_sdk_progress"])
        self.assertFalse(pack["counts_as_p0_progress"])
        self.assertFalse(pack["counts_toward_complete_sdk_claim"])
        self.assertFalse(pack["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(pack["runtime_ready"])
        self.assertFalse(pack["public_sdk_ready"])
        self.assertFalse(pack["stable_claim_allowed"])
        self.assertFalse(pack["stable_sdk_ready"])
        self.assertEqual(pack["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(pack["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(pack["blockers"], [])
        self.assertEqual(pack["source_overclaimed_readiness_or_authorization_flags"], [])
        self.assertEqual(pack["source_overclaimed_progress_flags"], [])
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)

        text = status_report.format_text(report)
        self.assertIn(
            "multi_surface_beta_capture_pack: source_present=true; "
            "candidate_pack_validated=true",
            text,
        )
        self.assertIn("target=arkserver/Ragnarok", text)
        self.assertIn("surface_count=15", text)
        self.assertIn("approved_runtime_evidence=false", text)
        compact = status_report.format_compact_summary(report)
        self.assertIn(
            "Multi-surface beta pack: source_present=true; "
            "candidate_pack_validated=true; source_kind=none; target=arkserver/Ragnarok; "
            "surfaces=15; approved_runtime_evidence=false; runtime=false; "
            "public_sdk=false; stable_sdk=false; SDK_progress=0; P0_progress=0",
            compact,
        )

    def test_multi_surface_beta_capture_pack_overclaims_are_rejected_and_zeroed(self) -> None:
        pack_payload = self.multi_surface_beta_capture_pack_payload()
        pack_payload.update(
            {
                "approved_runtime_evidence_present": True,
                "approved_runtime_evidence_ready": True,
                "counts_as_approved_runtime_evidence": True,
                "runtime_ready": True,
                "public_sdk_ready": True,
                "stable_claim_allowed": True,
                "stable_sdk_ready": True,
                "counts_toward_complete_sdk_claim": True,
                "counts_toward_p0_dependency_chain_claim": True,
                "complete_sdk_claim_progress_contribution": "1/12",
                "p0_dependency_chain_claim_progress_contribution": "1/4",
            }
        )

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            multi_surface_beta_capture_pack=pack_payload,
            multi_surface_beta_capture_pack_path=(
                "/tmp/multi-surface-beta-capture-pack.check.json"
            ),
        )

        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])

        pack = report["multi_surface_beta_capture_pack"]
        self.assertTrue(pack["source_present"])
        self.assertTrue(pack["source_ready"])
        self.assertFalse(pack["candidate_pack_validated"])
        self.assertEqual(pack["status"], "candidate_pack_rejected_for_status_report")
        self.assertIsNone(pack["target"])
        self.assertIsNone(pack["candidate_surface_count"])
        self.assertFalse(pack["ready"])
        self.assertFalse(pack["approved_runtime_evidence_present"])
        self.assertFalse(pack["approved_runtime_evidence_ready"])
        self.assertFalse(pack["counts_as_approved_runtime_evidence"])
        self.assertFalse(pack["runtime_ready"])
        self.assertFalse(pack["public_sdk_ready"])
        self.assertFalse(pack["stable_claim_allowed"])
        self.assertFalse(pack["stable_sdk_ready"])
        self.assertEqual(pack["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(pack["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "multi_surface_beta_capture_pack_public_sdk_ready_not_false",
            pack["blockers"],
        )
        self.assertIn(
            "public_sdk_ready",
            pack["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "runtime_ready",
            pack["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "approved_runtime_evidence_ready",
            pack["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_contribution",
            pack["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "p0_dependency_chain_claim_progress_contribution",
            pack["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "multi_surface_beta_capture_pack",
            report["source_overclaim_summary"]["components"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

    def test_discord_beta_bridge_config_reports_communication_context_only(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            discord_beta_bridge_config=self.discord_beta_bridge_config_payload(),
            discord_beta_bridge_config_path="/tmp/discord-beta-bridge.check.json",
            discord_beta_bridge_config_source="provided_discord_beta_bridge_config_path",
        )

        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

        bridge = report["discord_beta_bridge"]
        self.assertTrue(bridge["source_present"])
        self.assertTrue(bridge["config_valid"])
        self.assertFalse(bridge["token_present"])
        self.assertEqual(bridge["token_value_redacted"], "<missing>")
        self.assertFalse(bridge["discord_py_available"])
        self.assertFalse(bridge["discord_authorized"])
        self.assertFalse(bridge["authorizes_discord_send"])
        self.assertFalse(bridge["counts_as_approved_runtime_evidence"])
        self.assertFalse(bridge["counts_as_sdk_progress"])
        self.assertFalse(bridge["public_sdk_ready"])
        self.assertEqual(bridge["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(bridge["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(bridge["blockers"], [])
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)

        text = status_report.format_text(report)
        self.assertIn("discord_beta_bridge: source_present=true", text)
        self.assertIn("config_valid=true", text)
        self.assertIn("discord_authorized=false", text)
        compact = status_report.format_compact_summary(report)
        self.assertIn(
            "Discord beta bridge: source_present=true; config_valid=true; "
            "token_present=false; discord_py_available=false; "
            "discord_authorized=false; SDK_progress=0; P0_progress=0",
            compact,
        )

    def test_discord_beta_bridge_overclaims_are_rejected_and_counted(self) -> None:
        bridge_payload = self.discord_beta_bridge_config_payload()
        bridge_payload.update(
            {
                "authorizes_discord": True,
                "counts_as_approved_runtime_evidence": True,
                "public_sdk_ready": True,
                "complete_sdk_claim_progress_contribution": 1,
            }
        )
        bridge_payload["non_authorization"]["authorizes_discord_send"] = True

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            discord_beta_bridge_config=bridge_payload,
        )

        bridge = report["discord_beta_bridge"]
        self.assertFalse(bridge["config_valid"])
        self.assertFalse(bridge["authorizes_discord"])
        self.assertFalse(bridge["counts_as_approved_runtime_evidence"])
        self.assertFalse(bridge["public_sdk_ready"])
        self.assertEqual(bridge["complete_sdk_claim_progress_contribution"], 0)
        self.assertIn(
            "discord_beta_bridge_non_authorization_authorizes_discord_send_not_false",
            bridge["blockers"],
        )
        self.assertIn(
            "authorizes_discord",
            bridge["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_contribution",
            bridge["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "discord_beta_bridge",
            report["source_overclaim_summary"]["components"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

    def test_discord_beta_bridge_bot_notice_aliases_are_rejected_and_zero_progress(self) -> None:
        bridge_payload = {
            "schema": "obelisk.discord-beta-bridge-bot-notice.v1",
            "confirmed_send": True,
            "sendPerformed": True,
            "http_status": 200,
            "publicSdkReady": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
            "non_authorization": {
                "authorizes_discord_send": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_sdk_progress": False,
                "counts_as_p0_progress": False,
            },
        }

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            discord_beta_bridge_config=bridge_payload,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])

        bridge = report["discord_beta_bridge"]
        self.assertFalse(bridge["config_valid"])
        self.assertFalse(bridge["discord_authorized"])
        self.assertFalse(bridge["public_sdk_ready"])
        self.assertFalse(bridge["counts_as_approved_runtime_evidence"])
        self.assertEqual(bridge["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(bridge["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "discord_beta_bridge_config_schema_mismatch",
            bridge["blockers"],
        )
        for flag in (
            "confirmed_send",
            "sendPerformed",
            "http_status",
            "publicSdkReady",
        ):
            with self.subTest(flag=flag):
                self.assertIn(
                    flag,
                    bridge["source_overclaimed_readiness_or_authorization_flags"],
                )
        for flag in (
            "completeSdkClaimProgressContribution",
            "p0DependencyChainClaimProgressContribution",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, bridge["source_overclaimed_progress_flags"])
        self.assertIn(
            "discord_beta_bridge",
            report["source_overclaim_summary"]["components"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

    def test_active_monitor_context_aliases_are_overclaims(self) -> None:
        payload = {
            "active_passive_monitor_session": {
                "schema": "obelisk.active-passive-monitor-session.v1",
                "source_kind": "active_passive_monitor",
                "status": "active",
                "publicSdkReady": True,
                "p0DependencyChainReady": True,
                "completeSdkClaimProgressContribution": "1/12",
            }
        }

        readiness, progress = status_report.source_alias_overclaim_paths(
            payload,
            false_keys=set(),
            zero_keys=set(),
            initial_non_counting_context=False,
        )

        self.assertIn("active_passive_monitor_session.publicSdkReady", readiness)
        self.assertIn("active_passive_monitor_session.p0DependencyChainReady", readiness)
        self.assertIn(
            "active_passive_monitor_session.completeSdkClaimProgressContribution",
            progress,
        )

    def test_non_counting_artifacts_cannot_clear_route_blocker_or_progress(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.update(
            {
                "active_monitor_runtime": {
                    "schema": "obelisk.active-monitor-runtime-status.v1",
                    "source_kind": "active_monitor",
                    "routeBlockerCleared": True,
                    "currentRouteBlockerResolved": True,
                    "publicSdkReady": True,
                    "completeSdkClaimProgressContribution": "1/12",
                },
                "discord_beta_bridge_report": {
                    "schema": "obelisk.discord-beta-bridge-report.v1",
                    "source_kind": "discord_beta_bridge_config",
                    "routeLockResolved": True,
                    "countsTowardSdk": True,
                    "p0DependencyChainClaimProgressContribution": "1/4",
                },
                "multi_surface_beta_capture_pack_report": {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "source_kind": "multi_surface_beta_capture_pack",
                    "blockerResolved": True,
                    "sdkRouteBlockerCleared": True,
                    "candidatePackReady": True,
                    "sdkCredits": 1,
                },
                "scoped_release_statement": {
                    "schema": "obelisk.scoped-release-statement-outcomes.v1",
                    "status": "passed",
                    "currentRouteBlockerCleared": True,
                    "releaseStatementCountsTowardCompletion": True,
                    "scopedReleaseStatementClaimProgressContribution": "1/12",
                },
                "side_lane_candidate": {
                    "schema": "obelisk.side-lane-candidate.v1",
                    "source_kind": "side_lane_candidate",
                    "remainingRouteBlockersResolved": True,
                    "sideLaneCountsTowardSdk": True,
                    "progress": "1/12",
                },
                "side_lane_promotion_report": {
                    "schema": "obelisk.side-lane-promotion-report.v1",
                    "source_kind": "side_lane_candidate",
                    "sideLanePromoted": True,
                    "blockerResolved": True,
                    "completeSdkClaimProgressContribution": "1/12",
                },
                "structure_build_policy_offline_intake": {
                    "schema": "obelisk.structure-build-policy-offline-intake-check.v1",
                    "source_kind": "structure_build_policy_offline_intake",
                    "status": "accepted_planning_only",
                    "planning_only": True,
                    "blockers": [],
                    "structureBuildPolicyReady": True,
                    "routeReady": True,
                    "completeSdkClaimProgressContribution": "1/12",
                },
                "active_notice_report": {
                    "schema": "obelisk.active-notice-report.v1",
                    "status": "sent",
                    "activeNoticeAccepted": True,
                    "activeNoticeReady": True,
                    "activeNoticeSent": True,
                    "activeNoticeCountsTowardCompleteSdkClaim": True,
                    "p0DependencyChainClaimProgressContribution": "1/4",
                },
            }
        )

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])

        violations = report["non_counting_false_progress_alias_violations"]
        expected_violations = (
            "active_monitor_runtime.routeBlockerCleared",
            "active_monitor_runtime.currentRouteBlockerResolved",
            "active_monitor_runtime.completeSdkClaimProgressContribution",
            "discord_beta_bridge_report.routeLockResolved",
            "discord_beta_bridge_report.countsTowardSdk",
            "discord_beta_bridge_report.p0DependencyChainClaimProgressContribution",
            "multi_surface_beta_capture_pack_report.blockerResolved",
            "multi_surface_beta_capture_pack_report.sdkRouteBlockerCleared",
            "multi_surface_beta_capture_pack_report.sdkCredits",
            "scoped_release_statement.currentRouteBlockerCleared",
            "scoped_release_statement.releaseStatementCountsTowardCompletion",
            "scoped_release_statement.scopedReleaseStatementClaimProgressContribution",
            "side_lane_candidate.remainingRouteBlockersResolved",
            "side_lane_candidate.sideLaneCountsTowardSdk",
            "side_lane_candidate.progress",
            "side_lane_promotion_report.sideLanePromoted",
            "side_lane_promotion_report.blockerResolved",
            "side_lane_promotion_report.completeSdkClaimProgressContribution",
            "structure_build_policy_offline_intake.structureBuildPolicyReady",
            "structure_build_policy_offline_intake.routeReady",
            "structure_build_policy_offline_intake.completeSdkClaimProgressContribution",
            "active_notice_report.status",
            "active_notice_report.activeNoticeAccepted",
            "active_notice_report.activeNoticeReady",
            "active_notice_report.activeNoticeSent",
            "active_notice_report.activeNoticeCountsTowardCompleteSdkClaim",
            "active_notice_report.p0DependencyChainClaimProgressContribution",
        )
        for path in expected_violations:
            with self.subTest(path=path):
                self.assertIn(path, violations)
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

    def test_side_lane_inputs_preserve_runtime_then_identity_contract_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["installed_sdk_package_shape"] = {
            "schema": "obelisk.installed-sdk-package-shape.v1",
            "status": "package-shape-evidence-only",
            "ready": False,
            "publicSdkReady": False,
            "stableSdkReady": False,
            "completeSdkClaimProgressContribution": 0,
            "p0DependencyChainClaimProgressContribution": 0,
        }
        public_sdk["diagnostic_compact_chain_metadata"] = {
            "schema": "obelisk.diagnostic-compact-chain-metadata.v1",
            "status": "diagnostic_only",
            "compact_blocker_chain": (
                "approved_runtime_evidence_missing -> complete_sdk_ready"
            ),
            "after_runtime_evidence": "complete_sdk_ready",
            "counts_as_approved_runtime_evidence": False,
            "counts_toward_complete_sdk_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
        }
        public_sdk["mission_transfer_dino_tribe_outcome_accounting"] = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "status": "candidate_only",
            "ready": True,
            "source_ready": True,
            "accounting_route": "candidate_only",
            "required_leaves": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "observed_leaves": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "missing_leaf_families": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "public_sdk_ready": False,
            "runtime_ready": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            multi_surface_beta_capture_pack=(
                self.multi_surface_beta_capture_pack_payload()
            ),
            discord_beta_bridge_config=self.discord_beta_bridge_config_payload(),
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(
            report["critical_path_summary"]["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["stable_sdk_remaining_blockers"]["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["post_evidence_p0_lock_simulation"][
                "simulated_route_blocker_after_accepted_runtime_evidence"
            ],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["multi_surface_beta_capture_pack"]["public_sdk_ready"])
        self.assertFalse(report["multi_surface_beta_capture_pack"]["runtime_ready"])
        self.assertFalse(report["discord_beta_bridge"]["discord_authorized"])
        self.assertFalse(report["discord_beta_bridge"]["public_sdk_ready"])
        package_context = {
            context["id"]: context
            for context in report["operator_context_summary"]["contexts"]
        }["package_shape_install"]
        self.assertFalse(package_context["public_sdk_ready"])
        self.assertEqual(package_context["complete_sdk_claim_progress_contribution"], 0)
        side_lane = report["side_lanes"]["mission_transfer_dino_tribe_buff_accounting"]
        self.assertTrue(side_lane["source_present"])
        self.assertTrue(side_lane["source_ready"])
        self.assertFalse(side_lane["public_sdk_ready"])
        self.assertEqual(side_lane["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)

        compact = status_report.format_compact_summary(report)
        self.assertIn("route=approved_runtime_evidence_missing", compact)
        self.assertIn("after_runtime_evidence=identity_public_contract_gate_missing", compact)
        self.assertIn("P0 offline roadmap:", compact)
        self.assertIn("next_runtime=approved_runtime_principal_lifecycle_evidence_bundle", compact)
        self.assertIn("next_offline=obelisk.player_identity.v1", compact)
        self.assertIn(
            "post_identity_bridge=hash_bound_player_identity_promotion_certificate",
            compact,
        )
        self.assertIn(
            "post_permissions_bridge=hash_bound_permissions_admin_promotion_certificate",
            compact,
        )
        self.assertIn(
            "post_command_response_bridge=hash_bound_command_chat_response_path_promotion_certificate",
            compact,
        )
        self.assertIn(
            "commands_replies_final_gate=hash_bound_commands_replies_promotion_certificate",
            compact,
        )
        self.assertIn(
            "commands_replies_final_gate_schema=obelisk.commands-replies-promotion-certificate.v1",
            compact,
        )
        self.assertIn(
            "order=obelisk.player_identity.v1,obelisk.permissions_admin.v1,obelisk.command_chat_response_path.v1,obelisk.commands_replies.v1",
            compact,
        )
        self.assertIn("roadmap_only=true", compact)
        self.assertIn("SDK_progress=0; P0_progress=0", compact)
        self.assertIn("SDK=0/12", compact)
        self.assertIn("P0=0/4", compact)
        self.assertIn("Source overclaims: total=0", compact)
        self.assertNotIn("after_runtime_evidence=complete_sdk_ready", compact)

    def test_runtime_evidence_status_artifact_reports_window_context_only(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            runtime_evidence_status=self.runtime_evidence_status_payload(),
            runtime_evidence_status_path="/tmp/runtime-evidence-status.json",
            runtime_evidence_status_source="provided_runtime_evidence_status_path",
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            report["critical_path_summary"]["after_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["approved_runtime_evidence_ready"])

        window = report["runtime_evidence_window"]
        self.assertTrue(window["source_present"])
        self.assertEqual(window["source_kind"], "provided_runtime_evidence_status_path")
        self.assertEqual(window["source_path"], "/tmp/runtime-evidence-status.json")
        self.assertEqual(window["source_schema"], status_report.RUNTIME_EVIDENCE_STATUS_SCHEMA)
        self.assertEqual(window["status"], "blocked_missing_lifecycle_roles")
        self.assertEqual(window["window_state"], "blocked_missing_lifecycle_roles")
        self.assertEqual(window["route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(window["after_runtime_evidence"], "identity_public_contract_gate_missing")
        self.assertEqual(
            window["next_status_input_needed"],
            "same_run_roles_and_checked_sibling_artifacts",
        )
        self.assertEqual(window["run_id"], "20260607-runtime-window")
        self.assertEqual(window["missing_lifecycle_event_roles"], ["session_end"])
        self.assertIn(
            "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
            window["missing_required_artifacts"],
        )
        self.assertEqual(
            window["missing_copied_lifecycle_event_triplet_labels"],
            ["OnLogout matched"],
        )
        self.assertTrue(window["players_detected"])
        self.assertEqual(window["player_context"], "detected")
        self.assertEqual(
            window["player_availability_classification"],
            "players_detected_operator_context_non_evidence",
        )
        self.assertEqual(window["monitor_latest_tick_utc"], "2026-06-07T10:15:00Z")
        self.assertTrue(window["post_reboot_passive_monitor_log_supplied"])
        self.assertTrue(window["confirmed_beta_notice_json_supplied"])
        self.assertTrue(window["confirmed_beta_notice_completed"])
        self.assertTrue(window["copy_ready_json_supplied"])
        self.assertEqual(window["copy_readiness"], "not_ready_missing_roles")
        self.assertEqual(window["copy_ready_missing_roles"], ["session_end"])
        self.assertFalse(window["approved_runtime_evidence"])
        self.assertFalse(window["approved_runtime_evidence_ready"])
        self.assertFalse(window["runtime_ready"])
        self.assertFalse(window["public_sdk_ready"])
        self.assertFalse(window["stable_sdk_ready"])
        self.assertFalse(window["counts_as_approved_runtime_evidence"])
        self.assertFalse(window["counts_toward_complete_sdk_claim"])
        self.assertFalse(window["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(window["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(window["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(window["source_overclaimed_readiness_or_authorization_flags"], [])
        self.assertEqual(window["source_overclaimed_progress_flags"], [])
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)

        text = status_report.format_text(report)
        self.assertIn(
            "runtime_evidence_window: source_present=true; "
            "status=blocked_missing_lifecycle_roles",
            text,
        )
        self.assertIn("players=detected", text)
        self.assertIn("beta_notice=completed", text)
        self.assertIn("copy_ready=not_ready_missing_roles", text)

        compact = status_report.format_compact_summary(report)
        self.assertIn(
            "Runtime evidence window: source_present=true; "
            "status=blocked_missing_lifecycle_roles; "
            "window_state=blocked_missing_lifecycle_roles; players=detected; "
            "monitor_tick=2026-06-07T10:15:00Z; beta_notice=completed; "
            "copy_ready=not_ready_missing_roles; missing_roles=session_end; "
            "next_input=same_run_roles_and_checked_sibling_artifacts; "
            "approved_runtime_evidence=false; runtime=false; public_sdk=false; "
            "SDK_progress=0; P0_progress=0",
            compact,
        )
        self.assertIn("Source overclaims: total=0", compact)
        self.assertNotIn("runtime=true", compact)
        self.assertNotIn("public_sdk=true", compact)
        self.assertNotIn("stable_sdk_ready=true", compact)

    def test_active_passive_monitor_session_artifact_stays_non_progress(self) -> None:
        runtime_status = self.runtime_evidence_status_payload()
        monitor = runtime_status["post_reboot_passive_monitor"]
        monitor.update(
            {
                "passive_monitor_session": {
                    "pid": 2164533,
                    "ppid": 2164532,
                    "snapshot_output_root": (
                        "/tmp/obelisk-passive-evidence-snapshots/"
                        "20260608T124647Z-player-principal-lifecycle"
                    ),
                    "snapshot_monitor_log": (
                        "/tmp/obelisk_passive_player_monitor_"
                        "20260608T124647Z-player-principal-lifecycle.log"
                    ),
                    "evidence_classification": "passive_monitor_metadata_non_evidence",
                    "approved_runtime_evidence": False,
                    "ready": False,
                },
                "monitor_pid": 2164533,
                "snapshot_output_root": (
                    "/tmp/obelisk-passive-evidence-snapshots/"
                    "20260608T124647Z-player-principal-lifecycle"
                ),
                "snapshot_monitor_log": (
                    "/tmp/obelisk_passive_player_monitor_"
                    "20260608T124647Z-player-principal-lifecycle.log"
                ),
                "ready": True,
                "runtimeReady": True,
                "publicSdkReady": True,
                "completeSdkClaimProgressContribution": 1,
                "p0DependencyChainClaimProgressContribution": 1,
            }
        )

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            runtime_evidence_status=runtime_status,
            runtime_evidence_status_path="/tmp/runtime-evidence-status.json",
            runtime_evidence_status_source="provided_runtime_evidence_status_path",
        )

        window = report["runtime_evidence_window"]
        self.assertTrue(window["post_reboot_passive_monitor_log_supplied"])
        self.assertFalse(window["approved_runtime_evidence"])
        self.assertFalse(window["runtime_ready"])
        self.assertFalse(window["public_sdk_ready"])
        self.assertEqual(window["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(window["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "post_reboot_passive_monitor.ready",
            window["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "post_reboot_passive_monitor.runtimeReady",
            window["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "post_reboot_passive_monitor.publicSdkReady",
            window["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "post_reboot_passive_monitor.completeSdkClaimProgressContribution",
            window["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "post_reboot_passive_monitor.p0DependencyChainClaimProgressContribution",
            window["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "runtime_evidence_window",
            report["source_overclaim_summary"]["components"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")

    def test_promotable_current_posture_suppresses_stale_live_diagnostic_drift(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            runtime_evidence_status=(
                self.promotable_ragnarok_runtime_evidence_status_payload()
            ),
            runtime_evidence_status_path="/tmp/runtime-evidence-status.json",
            runtime_evidence_status_source="provided_runtime_evidence_status_path",
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])

        live_context = report["current_live_diagnostic_blockers"]
        self.assertEqual(
            live_context["status"],
            "current_posture_supersedes_stale_operator_diagnostics",
        )
        self.assertEqual(
            live_context["source_freshness"],
            "stale_operator_supplied_superseded_by_current_posture",
        )
        self.assertTrue(live_context["current_posture_input_present"])
        self.assertTrue(live_context["current_posture_no_diagnostic"])
        self.assertTrue(live_context["stale_operator_supplied_blockers_suppressed"])
        self.assertEqual(live_context["next_blockers"], [])
        self.assertEqual(
            live_context["stale_operator_supplied_next_blocker_ids"],
            ["ragnarok_diagnostic_fname_drift_blocks_accepted_events"],
        )
        posture = live_context["current_posture_summary"]
        self.assertEqual(posture["target"], {"instance": "arkserver", "map": "Ragnarok"})
        self.assertTrue(posture["observer_window_promotable"])
        self.assertFalse(live_context["approved_runtime_evidence"])
        self.assertFalse(live_context["runtime_ready"])
        self.assertFalse(live_context["public_sdk_ready"])
        self.assertEqual(live_context["sdk_progress"], 0)
        self.assertEqual(live_context["p0_progress"], 0)

        compact = status_report.format_compact_summary(report)
        self.assertIn("Stale live diagnostic context:", compact)
        self.assertIn(
            "freshness=stale_operator_supplied_superseded_by_current_posture",
            compact,
        )
        self.assertIn("current_posture_input=true", compact)
        self.assertIn("stale_blockers_suppressed=true", compact)
        self.assertNotIn("Current live diagnostic blockers", compact)
        self.assertNotIn("diagnostic_fname_drift_blocks_accepted_events", compact)
        self.assertNotIn("fname_drift=true", compact)
        self.assertIn("route=approved_runtime_evidence_missing", compact)
        self.assertIn("SDK=0/12", compact)
        self.assertIn("P0=0/4", compact)

    def test_post_evidence_p0_lock_simulation_fields_are_non_claims(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        simulation = report["post_evidence_p0_lock_simulation"]
        self.assertEqual(
            simulation["schema"],
            "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
        )
        self.assertEqual(
            simulation["source_schema"],
            "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
        )
        self.assertTrue(simulation["simulation_only"])
        self.assertFalse(simulation["approved_runtime_evidence_accepted"])
        self.assertEqual(simulation["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            simulation["remaining_route_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(
            simulation["simulated_route_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertTrue(simulation["identity_public_contract_required"])
        for key in status_report.POST_EVIDENCE_P0_LOCK_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(simulation[key])
        for key in status_report.POST_EVIDENCE_P0_LOCK_ZERO_FIELDS:
            with self.subTest(key=key):
                self.assertEqual(simulation[key], 0)
        self.assertEqual(len(simulation["p0_child_checks"]), 2)
        for child in simulation["p0_child_checks"]:
            self.assertTrue(child["dependency_chain_locked"], child)
            for key in status_report.POST_EVIDENCE_P0_CHILD_FALSE_FLAGS:
                with self.subTest(child=child["name"], key=key):
                    self.assertFalse(child[key])

        text = status_report.format_text(report)
        self.assertIn("post_evidence_p0_lock_simulation: simulation_only=true", text)
        self.assertIn(
            "simulated_after_accepted_runtime_evidence=identity_public_contract_gate_missing",
            text,
        )
        self.assertIn("public_sdk_ready=false", text)
        self.assertIn("runtime_ready=false", text)
        self.assertIn("complete_sdk_progress=0; p0_progress=0", text)
        self.assertIn("live_ops_authorized=false", text)
        self.assertIn("workspace_writes_authorized=false", text)
        self.assertIn("runtime_capture_authorized=false", text)
        self.assertNotIn("public_sdk_ready=true", text)
        self.assertNotIn("runtime_ready=true", text)

    def test_post_evidence_p0_lock_simulation_overclaims_do_not_unlock_status(self) -> None:
        public_sdk = self.public_sdk_payload()
        route_gate = public_sdk["command_permission_route_gate"]
        self.assertIsInstance(route_gate, dict)
        simulation = route_gate["post_evidence_p0_lock_simulation"]
        self.assertIsInstance(simulation, dict)
        simulation.update(
            {
                "approved_runtime_evidence_accepted": True,
                "status": ["blocked", "accepted"],
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                "simulated_route_blocker_after_accepted_runtime_evidence": None,
                "permissions_admin_unlocked": True,
                "command_response_unlocked": True,
                "commands_replies_unlocked": True,
                "promotion_ready": True,
                "public_sdk_ready": True,
                "public_abi_ready": True,
                "public_header_allowed": True,
                "runtime_ready": True,
                "counts_toward_complete_sdk_claim": True,
                "counts_toward_p0_dependency_chain_claim": True,
                "complete_sdk_claim_progress_contribution": 1,
                "p0_dependency_chain_claim_progress_contribution": 1,
                "countsTowardCompleteSdkClaimNow": [False, "yes"],
                "completeSdkProgressContribution": ["0/12", "1/12"],
                "live_ops_authorized": True,
                "workspace_writes_authorized": True,
                "runtime_capture_authorized": True,
            }
        )
        child = simulation["p0_child_checks"][0]
        self.assertIsInstance(child, dict)
        child["counts_toward_public_sdk"] = True
        child["public_or_runtime_accounting_allowed"] = True
        child["publicOrRuntimeAccountingAllowed"] = [False, "ready"]
        child["p0DependencyChainClaimProgressContribution"] = ["0/4", "1/4"]

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])

        normalized = report["post_evidence_p0_lock_simulation"]
        self.assertFalse(normalized["approved_runtime_evidence_accepted"])
        self.assertTrue(normalized["source_approved_runtime_evidence_accepted"])
        self.assertEqual(normalized["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            normalized["source_current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            normalized["simulated_route_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(normalized["permissions_admin_unlocked"])
        self.assertFalse(normalized["command_response_unlocked"])
        self.assertFalse(normalized["commands_replies_unlocked"])
        self.assertFalse(normalized["public_sdk_ready"])
        self.assertFalse(normalized["runtime_ready"])
        self.assertFalse(normalized["counts_toward_complete_sdk_claim"])
        self.assertFalse(normalized["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(normalized["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(normalized["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(normalized["live_ops_authorized"])
        self.assertFalse(normalized["workspace_writes_authorized"])
        self.assertFalse(normalized["runtime_capture_authorized"])
        self.assertIn(
            "approved_runtime_evidence_accepted",
            normalized["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "public_sdk_ready",
            normalized["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "runtime_capture_authorized",
            normalized["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "status",
            normalized["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "countsTowardCompleteSdkClaimNow",
            normalized["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_contribution",
            normalized["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "p0_dependency_chain_claim_progress_contribution",
            normalized["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "completeSdkProgressContribution",
            normalized["source_overclaimed_progress_flags"],
        )
        first_child = normalized["p0_child_checks"][0]
        self.assertFalse(first_child["counts_toward_public_sdk"])
        self.assertFalse(first_child["public_or_runtime_accounting_allowed"])
        self.assertIn(
            "counts_toward_public_sdk",
            first_child["source_overclaimed_accounting_flags"],
        )
        self.assertIn(
            "publicOrRuntimeAccountingAllowed",
            first_child["source_overclaimed_accounting_flags"],
        )
        self.assertIn(
            "p0DependencyChainClaimProgressContribution",
            first_child["source_overclaimed_progress_flags"],
        )

    def test_post_evidence_p0_lock_simulation_synthesizes_when_route_gate_strips_source(self) -> None:
        public_sdk = self.public_sdk_payload()
        route_gate = public_sdk["command_permission_route_gate"]
        self.assertIsInstance(route_gate, dict)
        route_gate.pop("post_evidence_p0_lock_simulation")

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        simulation = report["post_evidence_p0_lock_simulation"]
        self.assertFalse(simulation["source_present"])
        self.assertTrue(simulation["simulation_only"])
        self.assertFalse(simulation["approved_runtime_evidence_accepted"])
        self.assertEqual(simulation["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            simulation["simulated_route_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertTrue(simulation["identity_public_contract_required"])
        self.assertFalse(simulation["public_sdk_ready"])
        self.assertFalse(simulation["runtime_ready"])
        self.assertFalse(simulation["live_ops_authorized"])
        self.assertFalse(simulation["workspace_writes_authorized"])
        self.assertFalse(simulation["runtime_capture_authorized"])
        self.assertEqual(simulation["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(simulation["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_approved_runtime_boolean_alias_without_strict_triplet_stays_missing_runtime_evidence(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["approved_runtime_evidence"] = {
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_ready": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
        }

        self.assertFalse(
            status_report.accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        )
        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["remaining_route_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertIn(
            "approved_runtime_principal_lifecycle_evidence_bundle",
            report["fastest_next_sdk_unblock"]["required_artifacts"],
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_public_contract_review_cannot_impersonate_runtime_checker_contract(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["approved_runtime_evidence"] = {
            "schema": "obelisk.player-identity-public-contract-review-artifact.v1",
            "input_schema": "obelisk.player-identity-public-contract-decision.v1",
            "ready": True,
            "ready_scope": "public_contract_review",
            "status": "reviewed",
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_present": True,
            "approved_runtime_evidence_ready": True,
            "runtime_evidence_ready": True,
            "public_contract_review_ready": True,
            "reviewed_public_contract": True,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_allowed": False,
            "complete_sdk_ready": False,
            "next_blocker": "identity_public_contract_gate_missing",
            "strict_lifecycle_triplet_selected": True,
            "strict_lifecycle_triplet_selection": {
                "accepted": True,
                "selected_roles": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
                "non_counting_context_event_count": 0,
                "non_counting_context_roles": [],
            },
            "strict_rejected_start_expected_shape": (
                "ShooterGameMode.CheckJoinInProgress(1,0)"
            ),
            "strict_rejected_start_observed_shape": {
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        }

        self.assertFalse(
            status_report.accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        )
        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertEqual(
            report["post_evidence_p0_lock_simulation"]["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )

    def test_checker_report_contract_advances_only_to_identity_contract_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["approved_runtime_evidence"] = {
            "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
            "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
            "ready": True,
            "ready_scope": "runtime_evidence_only",
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_present": True,
            "approved_runtime_evidence_ready": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
            "runtime_ready": False,
            "stable_claim_allowed": False,
            "complete_sdk_allowed": False,
            "complete_sdk_ready": False,
            "next_blocker": "identity_public_contract_gate_missing",
            "strict_lifecycle_triplet_selected": True,
            "strict_lifecycle_triplet_selection": {
                "accepted": True,
                "selected_roles": ["session_start", "session_start_rejected", "session_end"],
                "non_counting_context_event_count": 0,
                "non_counting_context_roles": [],
            },
            "strict_rejected_start_expected_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
            "strict_rejected_start_observed_shape": {
                "target": "ShooterGameMode.CheckJoinInProgress",
                "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "copied_bool_values": ["1", "0"],
                "apply_status": "session_start_rejected_noop",
                "correlation_status": "not_applicable",
            },
        }

        self.assertTrue(
            status_report.accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        )
        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["remaining_route_blockers"],
            ["identity_public_contract_gate_missing"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(
            report["fastest_next_sdk_unblock"]["unblock_kind"],
            "reviewed_identity_public_contract",
        )
        self.assertEqual(
            report["fastest_next_sdk_unblock"]["required_artifacts"],
            ["reviewed_player_identity_public_contract_decision"],
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])
        approved_in_game = report["approved_in_game_evidence"]
        self.assertFalse(approved_in_game["approved_runtime_evidence"])
        self.assertFalse(approved_in_game["approved_runtime_evidence_ready"])
        self.assertIsNone(approved_in_game["missing_required_artifact"])
        self.assertEqual(
            report["post_evidence_p0_lock_simulation"]["current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["post_evidence_p0_lock_simulation"][
                "simulated_route_blocker_after_accepted_runtime_evidence"
            ],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["post_evidence_p0_lock_simulation"]["public_sdk_ready"])
        self.assertFalse(report["post_evidence_p0_lock_simulation"]["runtime_ready"])
        self.assertFalse(
            report["post_evidence_p0_lock_simulation"][
                "counts_toward_p0_dependency_chain_claim"
            ]
        )

    def test_side_lane_summaries_are_non_authorizing_and_zero_progress(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload_with_overclaiming_side_lanes(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        roadmap = report["p0_offline_roadmap"]
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_artifact"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_schema"],
            "obelisk.commands-replies-promotion-certificate.v1",
        )
        self.assertFalse(roadmap["commands_replies_final_gate_promotion_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_public_sdk_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_runtime_ready"])
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_p0_dependency_chain"]
        )
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_complete_sdk_claim"]
        )

        side_lanes = report["side_lanes"]
        self.assertEqual(report["side_lane_source_overclaim_count"], 4)
        source_overclaims = report["side_lane_source_overclaims"]
        self.assertTrue(source_overclaims["status_report_only"])
        self.assertEqual(source_overclaims["count"], 4)
        self.assertEqual(
            report["side_lane_source_overclaim_authorization_or_claim_flag_count"],
            source_overclaims["authorization_or_claim_flag_count"],
        )
        self.assertEqual(
            report["side_lane_source_overclaim_progress_flag_count"],
            source_overclaims["progress_flag_count"],
        )
        self.assertEqual(
            report["side_lane_source_overclaim_total_flag_count"],
            source_overclaims["total_flag_count"],
        )
        self.assertGreater(
            report["side_lane_source_overclaim_authorization_or_claim_flag_count"],
            0,
        )
        self.assertGreater(report["side_lane_source_overclaim_progress_flag_count"], 0)
        self.assertEqual(
            report["side_lane_source_overclaim_side_lanes"],
            [
                "buff_status",
                "dino_scalar",
                "mission_transfer_dino_tribe_buff_accounting",
                "transfer_scriptstruct",
            ],
        )
        self.assertEqual(
            source_overclaims["side_lane_ids"],
            report["side_lane_source_overclaim_side_lanes"],
        )
        overclaim_summary = report["source_overclaim_summary"]
        self.assertTrue(overclaim_summary["status_report_only"])
        self.assertGreater(overclaim_summary["total_flag_count"], 0)
        self.assertEqual(
            report["source_overclaim_total_flag_count"],
            overclaim_summary["total_flag_count"],
        )
        compact = status_report.format_compact_summary(report)
        self.assertIn(
            "commands_replies_final_gate=hash_bound_commands_replies_promotion_certificate",
            compact,
        )
        self.assertIn("SDK=0/12", compact)
        self.assertIn("P0=0/4", compact)
        self.assertIn(
            f"Source overclaims: total={report['source_overclaim_total_flag_count']}",
            compact,
        )
        self.assertEqual(
            report["source_overclaim_component_count"],
            overclaim_summary["component_count"],
        )
        self.assertIn("side_lanes", overclaim_summary["components"])
        self.assertEqual(
            overclaim_summary["components"]["side_lanes"]["flag_count"],
            source_overclaims["total_flag_count"],
        )
        self.assertIn(
            "authorization_or_claim",
            overclaim_summary["components"]["side_lanes"]["categories"],
        )
        self.assertIn(
            "progress",
            overclaim_summary["components"]["side_lanes"]["categories"],
        )
        self.assertEqual(
            set(source_overclaims["side_lanes"]),
            {
                "transfer_scriptstruct",
                "buff_status",
                "dino_scalar",
                "mission_transfer_dino_tribe_buff_accounting",
            },
        )
        self.assertIn(
            "live_ops_authorized",
            source_overclaims["side_lanes"]["transfer_scriptstruct"]["authorization_or_claim"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_contribution",
            source_overclaims["side_lanes"]["transfer_scriptstruct"]["progress"],
        )
        self.assertEqual(
            set(side_lanes),
            {
                "transfer_scriptstruct",
                "buff_status",
                "dino_scalar",
                "mission_transfer_dino_tribe_buff_accounting",
            },
        )
        for side_lane_id, side_lane in side_lanes.items():
            with self.subTest(side_lane=side_lane_id):
                self.assertTrue(side_lane["source_present"])
                self.assertFalse(side_lane["synthetic_status_only"])
                self.assertTrue(side_lane["status_report_only"])
                self.assertTrue(side_lane["non_claim_side_lane"])
                self.assertFalse(side_lane["ready"])
                self.assertFalse(side_lane["live_ops_authorized"])
                self.assertFalse(side_lane["workspace_writes_authorized"])
                self.assertFalse(side_lane["runtime_capture_authorized"])
                self.assertFalse(side_lane["reads_live_logs"])
                self.assertFalse(side_lane["read_live_logs"])
                self.assertFalse(side_lane["counts_toward_complete_sdk_claim"])
                self.assertFalse(side_lane["counts_toward_p0_dependency_chain_claim"])
                self.assertFalse(side_lane["public_sdk_ready"])
                self.assertFalse(side_lane["runtime_ready"])
                self.assertEqual(side_lane["complete_sdk_claim_progress_contribution"], 0)
                self.assertEqual(side_lane["p0_dependency_chain_claim_progress_contribution"], 0)
                self.assertIn(
                    "live_ops_authorized",
                    side_lane["source_overclaimed_authorization_or_claim_flags"],
                )
                self.assertIn(
                    "read_live_logs",
                    side_lane["source_overclaimed_authorization_or_claim_flags"],
                )
                self.assertIn(
                    "complete_sdk_claim_progress_contribution",
                    side_lane["source_overclaimed_progress_flags"],
                )
                self.assertIn(
                    "p0_dependency_chain_claim_progress_contribution",
                    side_lane["source_overclaimed_progress_flags"],
                )

        buff = side_lanes["buff_status"]
        self.assertEqual(buff["context"]["source_manifest"]["source"], "offline_core")
        self.assertEqual(buff["context"]["source_manifest"]["status"], "candidate-only")
        self.assertEqual(buff["context"]["source_binding_count"], 4)

        accounting = side_lanes["mission_transfer_dino_tribe_buff_accounting"]
        self.assertFalse(accounting["v1_accounted"])
        self.assertEqual(
            accounting["context"]["required_leaves"],
            ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"],
        )
        self.assertEqual(accounting["context"]["accounting_route"], "manifest_umbrella_excluded")
        self.assertIn(
            "readiness_counts_toward_v1_accounting",
            accounting["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "complete_sdk_claim_progress_ratio",
            accounting["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "p0_dependency_chain_claim_progress_percent",
            accounting["source_overclaimed_progress_flags"],
        )

        self.assertFalse(report["authorizations"]["live_ops_authorized"])
        self.assertFalse(report["authorizations"]["workspace_writes_authorized"])
        self.assertFalse(report["authorizations"]["runtime_capture_authorized"])
        self.assertFalse(report["authorizations"]["reads_live_logs"])
        self.assertFalse(report["authorizations"]["read_live_logs"])
        self.assertTrue(
            any("side lanes" in claim and "0 to complete SDK" in claim for claim in report["non_claims"])
        )

        text = status_report.format_text(report)
        self.assertIn("SDK counts: 0/12 promoted_for_claim", text)
        self.assertIn("P0 counts: 0/4 promoted_for_claim", text)
        self.assertIn("non-claim side lanes: 4", text)
        self.assertIn(
            "side-lane source overclaims normalized: 4 "
            "(buff_status,dino_scalar,mission_transfer_dino_tribe_buff_accounting,transfer_scriptstruct); "
            "authorization_or_claim_flags=",
            text,
        )
        self.assertIn("progress_flags=", text)
        self.assertIn("transfer_scriptstruct: label=Transfer ScriptStruct; source_present=true", text)
        self.assertIn(
            "buff_status: label=Buff status manifest/source binding; source_present=true",
            text,
        )
        self.assertIn("dino_scalar: label=Dino scalar; source_present=true", text)
        self.assertIn(
            "mission_transfer_dino_tribe_buff_accounting: "
            "label=Mission/Transfer/Dino/Tribe/Buff accounting; source_present=true",
            text,
        )
        self.assertIn("live_ops=false; workspace=false; runtime_capture=false; read_live_logs=false", text)
        self.assertIn("sdk_progress=0; p0_progress=0", text)
        self.assertIn("source_binding_count=4", text)

    def test_candidate_only_side_lane_ready_does_not_count_as_source_overclaim(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["mission_transfer_dino_tribe_outcome_accounting"] = {
            "schema": "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "status": "candidate_only",
            "ready": True,
            "source_ready": True,
            "accounting_route": "candidate_only",
            "required_leaves": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "observed_leaves": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "missing_leaf_families": [
                "mission",
                "transfer",
                "dino_policy",
                "tribe_policy",
                "buff_status",
            ],
            "public_sdk_ready": False,
            "runtime_ready": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        accounting = report["side_lanes"]["mission_transfer_dino_tribe_buff_accounting"]
        self.assertTrue(accounting["source_present"])
        self.assertTrue(accounting["source_ready"])
        self.assertTrue(accounting["candidate_status_observed"])
        self.assertFalse(accounting["ready"])
        self.assertFalse(accounting["public_sdk_ready"])
        self.assertFalse(accounting["runtime_ready"])
        self.assertEqual(accounting["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(accounting["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertNotIn("source_overclaimed_authorization_or_claim_flags", accounting)
        self.assertNotIn("source_overclaimed_progress_flags", accounting)
        self.assertEqual(report["side_lane_source_overclaim_count"], 0)
        self.assertEqual(report["side_lane_source_overclaim_total_flag_count"], 0)
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")

    def test_source_overclaim_zero_non_claim_language_does_not_count(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["source_overclaim_diagnostics"] = {
            "schema": "obelisk.source-overclaim-diagnostics.v1",
            "status": "non_claim_diagnostics",
            "source_overclaim_total_flag_count": 0,
            "source_overclaim_component_count": 0,
            "non_claim": (
                "source overclaim total is 0; diagnostics only and no SDK/P0 "
                "progress, route blocker clearance, runtime readiness, or public "
                "SDK readiness is granted"
            ),
        }
        public_sdk["structure_build_policy_offline_intake"] = {
            "schema": "obelisk.structure-build-policy-offline-intake-check.v1",
            "status": "accepted_planning_only",
            "ready": True,
            "planning_only": True,
            "blockers": [],
            "structure_build_policy_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertEqual(report["source_overclaim_total_flag_count"], 0)
        self.assertEqual(report["source_overclaim_component_count"], 0)
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertNotIn(
            "structure_build_policy_offline_intake.ready",
            report["non_counting_false_progress_alias_violations"],
        )
        self.assertNotIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )

    def test_missing_side_lane_summaries_are_synthetic_status_only(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        for side_lane_id, side_lane in report["side_lanes"].items():
            with self.subTest(side_lane=side_lane_id):
                self.assertFalse(side_lane["source_present"])
                self.assertTrue(side_lane["synthetic_status_only"])
                self.assertIn("did not run side-lane checkers", side_lane["summary_source"])
                self.assertFalse(side_lane["live_ops_authorized"])
                self.assertFalse(side_lane["workspace_writes_authorized"])
                self.assertFalse(side_lane["runtime_capture_authorized"])
                self.assertFalse(side_lane["read_live_logs"])
                self.assertEqual(side_lane["complete_sdk_claim_progress_contribution"], 0)
                self.assertEqual(side_lane["p0_dependency_chain_claim_progress_contribution"], 0)

        text = status_report.format_text(report)
        self.assertIn("non-claim side lanes: 4", text)
        self.assertNotIn("side-lane source overclaims normalized", text)
        self.assertIn("source_present=false; synthetic_status_only=true", text)

    def test_cli_accepts_precomputed_json_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.sdk-status-report.v1")
        self.assertEqual(len(payload["actionable_paths"]), 4)
        self.assertEqual(payload["sdk_counts"]["total"], 12)
        self.assertEqual(payload["p0_counts"]["total"], 4)
        self.assertFalse(payload["approved_in_game_evidence_ready"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertEqual(
            payload["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            payload["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertIn("fastest_next_sdk_unblock", payload)
        self.assertIn("debug_first_acceleration", payload)
        self.assertEqual(
            payload["debug_first_acceleration"]["compact_blocker_chain"],
            (
                "approved_runtime_evidence_missing -> approved runtime principal "
                "lifecycle evidence bundle -> identity public contract gate"
            ),
        )
        self.assertFalse(payload["debug_first_acceleration"]["live_ops_authorized"])
        self.assertFalse(
            payload["debug_first_acceleration"]["approved_runtime_evidence_ready"]
        )
        self.assertIn("approved_in_game_evidence", payload)
        self.assertFalse(payload["approved_in_game_evidence"]["ready"])
        self.assertFalse(payload["approved_in_game_evidence"]["approved_in_game_ready"])
        self.assertFalse(payload["approved_in_game_evidence"]["approved_in_game_evidence_ready"])
        self.assertFalse(
            payload["approved_in_game_evidence"][
                "complete_lifecycle_event_triplet_observed_diagnostic_only"
            ]
        )
        self.assertEqual(
            payload["approved_in_game_evidence"]["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            payload["fastest_next_sdk_unblock"]["next_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(payload["fastest_next_sdk_unblock"]["current_turn_scope_required"])
        self.assertTrue(
            payload["fastest_next_sdk_unblock"][
                "active_runtime_window_requires_standing_or_current_scope"
            ]
        )
        self.assertTrue(
            payload["fastest_next_sdk_unblock"]["standing_launch_authority_recorded"]
        )
        self.assertFalse(payload["fastest_next_sdk_unblock"]["live_ops_authorized"])
        self.assertFalse(payload["fastest_next_sdk_unblock"]["workspace_writes_authorized"])
        self.assertEqual(payload["closure"]["status"], "non_ready_missing_required_artifacts")
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(
            payload["private_logout_correlation"]["current_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            payload["private_logout_correlation"]["status"],
            "implemented/offline-pending-runtime-evidence",
        )
        self.assertFalse(payload["private_logout_correlation"]["internal_blocker_active"])
        self.assertFalse(payload["private_logout_correlation"]["public_lookup_allowed"])
        self.assertFalse(payload["private_logout_correlation"]["identity_exposure_allowed"])
        self.assertFalse(payload["private_logout_correlation"]["public_abi_ready"])
        self.assertFalse(payload["private_logout_correlation"]["public_header_ready"])
        self.assertFalse(payload["private_logout_correlation"]["live_authorization_allowed"])
        self.assertEqual(
            payload["actionable_paths"][
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
            ]["path_status"],
            "active_ragnarok_current_roles_unverified",
        )

    def test_cli_accepts_principal_start_end_runtime_evidence_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            start_end = root / "principal-start-end-evidence.check.json"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")
            start_end.write_text(
                json.dumps(self.principal_start_end_runtime_evidence_payload()),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--principal-start-end-runtime-evidence",
                    str(start_end),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(payload["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        roadmap = payload["p0_offline_roadmap"]
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_artifact"],
            "hash_bound_commands_replies_promotion_certificate",
        )
        self.assertEqual(
            roadmap["commands_replies_final_gate_required_schema"],
            "obelisk.commands-replies-promotion-certificate.v1",
        )
        self.assertFalse(roadmap["commands_replies_final_gate_promotion_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_public_sdk_ready"])
        self.assertFalse(roadmap["commands_replies_final_gate_runtime_ready"])
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_p0_dependency_chain"]
        )
        self.assertFalse(
            roadmap["commands_replies_final_gate_counts_toward_complete_sdk_claim"]
        )
        start_end_report = payload["principal_start_end_runtime_evidence"]
        self.assertTrue(start_end_report["source_present"])
        self.assertEqual(start_end_report["source_kind"], "provided_report_path")
        self.assertTrue(start_end_report["accepted_for_contract_review"])
        self.assertFalse(start_end_report["approved_runtime_evidence"])
        self.assertFalse(start_end_report["runtime_ready"])
        self.assertFalse(start_end_report["public_sdk_ready"])
        self.assertEqual(start_end_report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(start_end_report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_cli_accepts_runtime_evidence_status_json_context_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            runtime_status = root / "runtime-evidence-status.json"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            runtime_status.write_text(
                json.dumps(self.runtime_evidence_status_payload()),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--runtime-evidence-status-json",
                    str(runtime_status),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(payload["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertEqual(payload["source_overclaim_total_flag_count"], 0)
        window = payload["runtime_evidence_window"]
        self.assertTrue(window["source_present"])
        self.assertEqual(window["source_path"], str(runtime_status))
        self.assertEqual(window["status"], "blocked_missing_lifecycle_roles")
        self.assertEqual(window["player_context"], "detected")
        self.assertTrue(window["confirmed_beta_notice_completed"])
        self.assertFalse(window["approved_runtime_evidence"])
        self.assertFalse(window["runtime_ready"])
        self.assertFalse(window["public_sdk_ready"])
        self.assertEqual(window["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(window["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_cli_accepts_multi_surface_beta_capture_pack_report_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            pack = root / "multi-surface-beta-capture-pack.check.json"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")
            pack.write_text(
                json.dumps(self.multi_surface_beta_capture_pack_payload()),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--multi-surface-beta-capture-pack-json",
                    str(pack),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(payload["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        pack_report = payload["multi_surface_beta_capture_pack"]
        self.assertTrue(pack_report["source_present"])
        self.assertEqual(pack_report["source_path"], str(pack))
        self.assertEqual(pack_report["source_kind"], "provided_checker_report_path")
        self.assertTrue(pack_report["candidate_pack_validated"])
        self.assertEqual(pack_report["status"], "candidate_pack_validated")
        self.assertEqual(pack_report["target"], {"instance": "arkserver", "map": "Ragnarok"})
        self.assertEqual(pack_report["candidate_surface_count"], 15)
        self.assertFalse(pack_report["ready"])
        self.assertFalse(pack_report["approved_runtime_evidence_ready"])
        self.assertFalse(pack_report["runtime_ready"])
        self.assertFalse(pack_report["public_sdk_ready"])
        self.assertFalse(pack_report["stable_sdk_ready"])
        self.assertEqual(pack_report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(pack_report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_cli_accepts_validated_multi_surface_beta_capture_pack_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            output_root = root / "packs"
            run_id = "status-visible-pack"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")

            prepare_result = subprocess.run(
                [
                    sys.executable,
                    str(PREPARE_MULTI_SURFACE_PACK),
                    "--instance",
                    "arkserver",
                    "--map",
                    "Ragnarok",
                    "--output-root",
                    str(output_root),
                    "--run-id",
                    run_id,
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(prepare_result.returncode, 0, prepare_result.stderr)
            prepare_payload = json.loads(prepare_result.stdout)
            pack_dir = Path(prepare_payload["output_dir"])
            expected_candidate_surface_count = prepare_payload["candidate_surface_count"]

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--multi-surface-beta-capture-pack",
                    str(pack_dir),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            compact_result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--multi-surface-beta-capture-pack",
                    str(pack_dir),
                    "--compact",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(compact_result.returncode, 0, compact_result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(payload["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(payload["approved_runtime_evidence_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["stable_claim_allowed"])
        pack_report = payload["multi_surface_beta_capture_pack"]
        self.assertTrue(pack_report["source_present"])
        self.assertEqual(pack_report["source_kind"], "validated_pack_path")
        self.assertEqual(pack_report["source_path"], str(pack_dir))
        self.assertTrue(pack_report["candidate_pack_validated"])
        self.assertEqual(pack_report["status"], "candidate_pack_validated")
        self.assertEqual(pack_report["target"], {"instance": "arkserver", "map": "Ragnarok"})
        self.assertEqual(
            pack_report["candidate_surface_count"],
            expected_candidate_surface_count,
        )
        self.assertFalse(pack_report["ready"])
        self.assertFalse(pack_report["approved_runtime_evidence"])
        self.assertFalse(pack_report["approved_runtime_evidence_ready"])
        self.assertFalse(pack_report["runtime_ready"])
        self.assertFalse(pack_report["public_sdk_ready"])
        self.assertFalse(pack_report["stable_sdk_ready"])
        self.assertFalse(pack_report["counts_toward_complete_sdk_claim"])
        self.assertFalse(pack_report["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(pack_report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(pack_report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(payload["source_overclaim_total_flag_count"], 0)
        expected_compact_pack_line = (
            "Multi-surface beta pack: source_present=true; "
            "candidate_pack_validated=true; source_kind=validated_pack_path; "
            f"target=arkserver/Ragnarok; surfaces={expected_candidate_surface_count}; "
            "approved_runtime_evidence=false; runtime=false; public_sdk=false; "
            "stable_sdk=false; SDK_progress=0; P0_progress=0"
        )
        self.assertIn(
            expected_compact_pack_line,
            compact_result.stdout,
        )
        self.assertIn("SDK=0/12", compact_result.stdout)
        self.assertIn("P0=0/4", compact_result.stdout)

    def test_cli_auto_detects_canonical_principal_start_end_report_in_evidence_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_dir = root / "copied-evidence"
            evidence_dir.mkdir()
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            start_end = (
                evidence_dir
                / status_report.PRINCIPAL_START_END_RUNTIME_EVIDENCE_REPORT_NAME
            )
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")
            start_end.write_text(
                json.dumps(self.principal_start_end_runtime_evidence_payload()),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--evidence-dir",
                    str(evidence_dir),
                    "--json",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        start_end_report = payload["principal_start_end_runtime_evidence"]
        self.assertTrue(start_end_report["source_present"])
        self.assertEqual(start_end_report["source_kind"], "canonical_copied_evidence_path")
        self.assertEqual(start_end_report["source_path"], str(start_end))
        self.assertTrue(start_end_report["accepted_for_contract_review"])
        self.assertEqual(payload["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(payload["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(payload["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["approved_runtime_evidence_ready"])

    def test_compact_output_is_non_claim_and_ci_friendly(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        text = status_report.format_compact_summary(report)

        self.assertIn("status=blocked", text)
        self.assertIn("route=approved_runtime_evidence_missing", text)
        self.assertIn("next=approved_runtime_principal_lifecycle_evidence_bundle", text)
        self.assertIn("missing=approved_runtime_principal_lifecycle_evidence_bundle", text)
        self.assertIn("after_runtime_evidence=identity_public_contract_gate_missing", text)
        self.assertIn("SDK=0/12", text)
        self.assertIn("P0=0/4", text)
        self.assertIn("stable_claim_allowed=false", text)
        self.assertIn("stable_sdk_ready=false", text)
        self.assertIn("runtime=false", text)
        self.assertIn("public_sdk=false", text)
        self.assertIn("approved_runtime_evidence=false", text)
        self.assertIn("approved_in_game=false", text)
        self.assertIn(
            "Debug-first path: approved_runtime_evidence_missing -> "
            "approved runtime principal lifecycle evidence bundle -> "
            "identity public contract gate",
            text,
        )
        self.assertIn(
            "checker=scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            text,
        )
        self.assertIn("roles=session_start,session_start_rejected,session_end", text)
        self.assertIn("authorization=status-only", text)
        self.assertIn(
            "commands_replies_final_gate=hash_bound_commands_replies_promotion_certificate",
            text,
        )
        self.assertIn(
            "commands_replies_final_gate_schema=obelisk.commands-replies-promotion-certificate.v1",
            text,
        )
        self.assertIn("SDK_progress=0; P0_progress=0", text)
        self.assertIn("Source overclaims: total=0", text)
        self.assertIn("side_lanes=0", text)
        self.assertIn("Non-claim: status report only", text)
        self.assertIn("no live-ops authorization", text)
        self.assertIn("no live-ops authorization, runtime evidence", text)
        self.assertNotIn("stable_sdk_ready=true", text)
        self.assertNotIn("public_sdk=true", text)
        self.assertNotIn("runtime=true", text)

    def test_compact_output_labels_default_live_diagnostics_as_stale(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        live_context = report["current_live_diagnostic_blockers"]
        self.assertEqual(live_context["source"], "operator_supplied_current_redacted_state")
        self.assertEqual(live_context["source_freshness"], "stale_operator_supplied")
        self.assertTrue(live_context["stale_operator_supplied_context"])
        self.assertTrue(live_context["stale_operator_supplied_blockers_suppressed"])
        self.assertFalse(live_context["current_posture_input_present"])
        self.assertEqual(live_context["next_blockers"], [])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["approved_runtime_evidence_ready"])

        compact = status_report.format_compact_summary(report)
        self.assertIn("Stale live diagnostic context:", compact)
        self.assertIn("freshness=stale_operator_supplied", compact)
        self.assertIn("stale_blockers_suppressed=true", compact)
        self.assertIn("blockers=suppressed_stale_operator_context", compact)
        self.assertNotIn("Current live diagnostic blockers", compact)
        self.assertNotIn("diagnostic_fname_drift_blocks_accepted_events", compact)
        self.assertNotIn("fname_drift=true", compact)

    def test_cli_accepts_compact_output_with_precomputed_json_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sdk = root / "sdk.json"
            header = root / "header.json"
            closure = root / "closure.json"
            sdk.write_text(json.dumps(self.public_sdk_payload()), encoding="utf-8")
            header.write_text(json.dumps(self.header_gate_payload()), encoding="utf-8")
            closure.write_text(json.dumps(self.closure_payload()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--public-sdk-json",
                    str(sdk),
                    "--header-gate-json",
                    str(header),
                    "--closure-json",
                    str(closure),
                    "--compact",
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Obelisk SDK status: status=blocked", result.stdout)
        self.assertIn("SDK=0/12", result.stdout)
        self.assertIn("P0=0/4", result.stdout)
        self.assertIn(
            "commands_replies_final_gate=hash_bound_commands_replies_promotion_certificate",
            result.stdout,
        )
        self.assertIn(
            "commands_replies_final_gate_schema=obelisk.commands-replies-promotion-certificate.v1",
            result.stdout,
        )
        self.assertIn("Debug-first path: approved_runtime_evidence_missing", result.stdout)
        self.assertIn("identity public contract gate", result.stdout)
        self.assertIn("Non-claim: status report only", result.stdout)
        self.assertNotIn('"schema"', result.stdout)

    def test_text_output_has_no_readiness_claim(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )
        text = status_report.format_text(report)
        self.assertIn("current_route_blocker: approved_runtime_evidence_missing", text)
        self.assertIn("SDK counts: 0/12 promoted_for_claim", text)
        self.assertIn("P0 counts: 0/4 promoted_for_claim", text)
        self.assertIn("public header gate: review_ready=true; public_header_allowed=false", text)
        self.assertIn(
            "approved in-game evidence: ready=false; approved_runtime_evidence=false; "
            "diagnostic_complete_triplet=false; current_turn_scope_required=false; "
            "standing_launch_authority_recorded=true; "
            "next_required_artifact=approved_runtime_principal_lifecycle_evidence_bundle; "
            "blocker_reason=approved_runtime_principal_lifecycle_evidence_bundle_missing_or_unaccepted",
            text,
        )
        self.assertIn(
            "debug-first path: approved_runtime_evidence_missing -> "
            "approved runtime principal lifecycle evidence bundle -> "
            "identity public contract gate",
            text,
        )
        self.assertIn(
            "next_action=produce and checker-accept the copied approved runtime "
            "principal lifecycle evidence bundle",
            text,
        )
        self.assertIn(
            "checker=scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            text,
        )
        self.assertIn("authorization=status-only", text)
        self.assertIn("approved_runtime_evidence_ready=false", text)
        self.assertIn("SDK_progress=0; P0_progress=0", text)
        self.assertIn(
            "next_required_artifact=approved_runtime_principal_lifecycle_evidence_bundle",
            text,
        )
        self.assertIn("current_turn_scope_required=false", text)
        self.assertIn("standing_launch_authority_recorded=true", text)
        self.assertIn(
            "live_ops_authorized=false; workspace_writes_authorized=false; "
            "runtime_capture_authorized=false",
            text,
        )
        self.assertIn(
            "private_logout_correlation: status=blocked/internal-planning; "
            "current_blocker=private_logout_correlation_missing; "
            "internal_blocker_active=true; public_lookup=false; "
            "identity_exposure=false; public_abi_ready=false; "
            "public_header_ready=false; live_authorization=false",
            text,
        )
        self.assertIn("non-authorizing action paths: 4", text)
        self.assertIn("historical_theisland_candidate_missing_sidecars", text)
        self.assertIn("active_genesis2_passive_missing_roles", text)
        self.assertIn(
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle",
            text,
        )
        self.assertIn("player_notice_action", text)
        self.assertIn(
            "historical_theisland_candidate_missing_sidecars: "
            "target=arkserver2/TheIsland; missing_roles=none; "
            "evidence_status=non_evidence_until_approved_bundle_acceptance; "
            "authorization=non-authorizing",
            text,
        )
        self.assertIn(
            "historical_theisland_sidecar_closure; role_source_status=not_provided; "
            "role_source_trusted=false; notice_action_authorized=false; "
            "discord_authorized=false; approved_runtime_evidence=false",
            text,
        )
        self.assertIn(
            "active_genesis2_passive_missing_roles: "
            "target=arkserver3/Genesis2; "
            "missing_roles=session_start,session_start_rejected,session_end; "
            "evidence_status=diagnostic_passive_non_evidence; "
            "authorization=non-authorizing",
            text,
        )
        self.assertIn(
            "active_genesis2_current_roles_unverified",
            text,
        )
        self.assertIn(
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle: "
            "target=arkserver/Ragnarok; "
            "missing_roles=session_start,session_start_rejected,session_end; "
            "evidence_status=diagnostic_passive_non_evidence; "
            "authorization=non-authorizing; "
            "path_status=active_ragnarok_current_roles_unverified; "
            "role_source_status=untrusted_for_current_status; "
            "role_source_trusted=false",
            text,
        )
        self.assertNotIn("approved_bundle_required=true", text)
        self.assertIn(
            "player_notice_action_required=true; notice_action_authorized=false; "
            "discord_authorized=false",
            text,
        )
        self.assertIn(
            "false authorizations: live_ops=false; server_operations=false; "
            "workspace_writes=false; runtime_capture=false; reads_live_logs=false",
            text,
        )
        self.assertIn("player notices, accepted runtime evidence, sidecars", text)
        self.assertIn("non-claim", text)
        self.assertNotIn("stable SDK ready", text)

    def test_private_logout_correlation_defaults_to_internal_non_public_blocker(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        private_correlation = report["private_logout_correlation"]
        self.assertTrue(private_correlation["internal_blocker_active"])
        self.assertTrue(private_correlation["blocks_before_public_identity_promotion"])
        for key in status_report.PRIVATE_LOGOUT_CORRELATION_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(private_correlation[key])
        claims = " ".join(private_correlation["non_claims"])
        self.assertIn("no public lookup", claims)
        self.assertIn("no identity exposure", claims)
        self.assertIn("no ABI/header readiness", claims)
        self.assertIn("no live authorization", claims)

    def test_private_logout_correlation_implemented_offline_still_blocks_public_readiness(self) -> None:
        decisions = {
            "private_logout_correlation_internal_blocker": {
                "id": "private_logout_correlation_internal_blocker",
                "status": "implemented/offline-pending-runtime-evidence",
                "visibility": "internal_non_public_planning_only",
                "current_blocker": "approved_runtime_evidence_missing",
                "internal_blocker_active": False,
                "blocks_before_public_identity_promotion": True,
                "public_lookup_ready": True,
                "public_sdk_ready": True,
                "runtime_ready": True,
                "live_ops_authorized": True,
            }
        }

        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            public_contract_decisions=decisions,
        )

        private_correlation = report["private_logout_correlation"]
        self.assertEqual(
            private_correlation["status"],
            "implemented/offline-pending-runtime-evidence",
        )
        self.assertEqual(
            private_correlation["current_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertFalse(private_correlation["internal_blocker_active"])
        self.assertTrue(private_correlation["blocks_before_public_identity_promotion"])
        for key in status_report.PRIVATE_LOGOUT_CORRELATION_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(private_correlation[key])
        self.assertIn(
            "public_sdk_ready",
            private_correlation["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertIn(
            "runtime_ready",
            private_correlation["source_overclaimed_readiness_or_authorization_flags"],
        )
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_json_summary_preserves_action_path_context_fields(self) -> None:
        report = status_report.summarize(
            public_sdk=self.public_sdk_payload(),
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        historical = report["actionable_paths"]["historical_theisland_candidate_missing_sidecars"]
        active = report["actionable_paths"]["active_genesis2_passive_missing_roles"]
        ragnarok = report["actionable_paths"][
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
        ]
        self.assertEqual(historical["target"], {"instance": "arkserver2", "map": "TheIsland"})
        self.assertEqual(active["target"], {"instance": "arkserver3", "map": "Genesis2"})
        self.assertEqual(
            active["missing_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(active["present_event_roles"], [])
        self.assertEqual(active["source_missing_event_roles"], ["session_end"])
        self.assertEqual(active["role_source_status"], "untrusted_for_current_status")
        self.assertFalse(active["role_source_trusted_for_current_status"])
        self.assertEqual(active["evidence_status"], "diagnostic_passive_non_evidence")
        self.assertEqual(historical["path_status"], "historical_theisland_sidecar_closure")
        self.assertEqual(historical["authorization"], "non-authorizing")
        self.assertEqual(
            historical["evidence_status"],
            "non_evidence_until_approved_bundle_acceptance",
        )
        self.assertFalse(historical["counts_as_approved_runtime_evidence"])
        self.assertFalse(historical["server_operations_authorized"])
        self.assertFalse(historical["workspace_writes_authorized"])
        self.assertIn("non-evidence", historical["non_evidence_reason"])
        self.assertEqual(active["path_status"], "active_genesis2_current_roles_unverified")
        self.assertEqual(
            ragnarok["path_status"],
            "active_ragnarok_current_roles_unverified",
        )
        self.assertEqual(ragnarok["target"], {"instance": "arkserver", "map": "Ragnarok"})
        self.assertEqual(ragnarok["present_event_roles"], [])
        self.assertEqual(
            ragnarok["source_present_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            ragnarok["missing_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(ragnarok["role_source_status"], "untrusted_for_current_status")
        self.assertFalse(ragnarok["role_source_trusted_for_current_status"])
        self.assertNotIn("approved_bundle_required", ragnarok)
        self.assertNotIn("required_next_artifact", ragnarok)
        self.assertFalse(active["authorizes_runtime_work"])
        self.assertFalse(active["authorizes_server_operations"])
        self.assertFalse(active["reads_live_logs"])
        self.assertFalse(ragnarok["authorizes_server_work"])
        self.assertFalse(ragnarok["authorizes_workspace_work"])
        self.assertFalse(ragnarok["counts_as_approved_runtime_evidence"])
        self.assertFalse(ragnarok["passive_snapshot_evidence_allowed"])
        self.assertIn("diagnostic", ragnarok["non_evidence_reason"])

    def test_checked_current_runtime_log_source_can_narrow_missing_roles(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        active = paths["active_genesis2_passive_missing_roles"]
        self.assertIsInstance(active, dict)
        active["current_source"] = "checked_copied_runtime_log_artifact"

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        normalized = report["actionable_paths"]["active_genesis2_passive_missing_roles"]
        self.assertTrue(normalized["role_source_trusted_for_current_status"])
        self.assertEqual(normalized["role_source_status"], "trusted_current_log")
        self.assertEqual(normalized["missing_event_roles"], ["session_end"])
        self.assertEqual(normalized["source_missing_event_roles"], ["session_end"])
        self.assertEqual(normalized["path_status"], "active_genesis2_missing_session_end")
        self.assertEqual(normalized["required_next_event_role"], "session_end")
        self.assertEqual(normalized["present_event_roles"], [])
        self.assertFalse(normalized["counts_as_approved_runtime_evidence"])
        self.assertFalse(normalized["authorizes_runtime_work"])

        text = status_report.format_text(report)
        self.assertIn(
            "active_genesis2_passive_missing_roles: "
            "target=arkserver3/Genesis2; missing_roles=session_end",
            text,
        )
        self.assertIn("role_source_trusted=true", text)

    def test_handoff_docs_source_text_cannot_narrow_current_roles(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        active = paths["active_genesis2_passive_missing_roles"]
        self.assertIsInstance(active, dict)
        active["current_source"] = "handoff docs checked_copied_runtime_log_artifact"

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        normalized = report["actionable_paths"]["active_genesis2_passive_missing_roles"]
        self.assertFalse(normalized["role_source_trusted_for_current_status"])
        self.assertEqual(normalized["role_source_status"], "untrusted_for_current_status")
        self.assertEqual(
            normalized["missing_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(normalized["source_missing_event_roles"], ["session_end"])
        self.assertEqual(normalized["present_event_roles"], [])
        self.assertEqual(normalized["path_status"], "active_genesis2_current_roles_unverified")
        self.assertFalse(normalized["counts_as_approved_runtime_evidence"])
        self.assertFalse(normalized["authorizes_runtime_work"])

    def test_current_fresh_log_without_lifecycle_roles_fails_closed_all_roles(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        active = paths["active_genesis2_passive_missing_roles"]
        self.assertIsInstance(active, dict)
        active.pop("missing_event_roles")
        active["explicit_current_fresh_log_input"] = True
        active["current_source"] = "current_fresh_obelisk_log_input"

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        normalized = report["actionable_paths"]["active_genesis2_passive_missing_roles"]
        self.assertTrue(normalized["role_source_trusted_for_current_status"])
        self.assertEqual(normalized["role_source_status"], "trusted_current_log")
        self.assertEqual(
            normalized["missing_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(normalized.get("source_missing_event_roles"), None)
        self.assertEqual(normalized["present_event_roles"], [])
        self.assertEqual(normalized["path_status"], "active_genesis2_missing_current_roles")
        self.assertEqual(normalized["required_next_event_role"], "session_start")
        self.assertFalse(normalized["approved_bundle_required"])
        self.assertFalse(normalized["counts_as_approved_runtime_evidence"])
        self.assertFalse(normalized["authorizes_runtime_work"])

        approved_in_game = report["approved_in_game_evidence"]
        self.assertIn(
            "active_genesis2_passive_missing_roles",
            approved_in_game["missing_role_path_ids"],
        )
        self.assertFalse(
            approved_in_game["complete_lifecycle_event_triplet_observed_diagnostic_only"]
        )

    def test_complete_passive_ragnarok_triplet_fails_closed_for_any_path_id(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        paths["ragnarok_triplet_from_latest_summary"] = {
            "path_type": "latest_summary_complete_role_triplet",
            "authorization": "live-approved",
            "live_ops_authorized": True,
            "workspace_writes_authorized": True,
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "requirements": [
                "complete passive Ragnarok triplet is present",
                "passive_role_triplet:session_start",
                "passive_role_triplet:session_start_rejected",
                "passive_role_triplet:session_end",
            ],
            "present_event_roles": [
                "session_start",
                "session_start_rejected",
                "session_end",
            ],
            "missing_event_roles": [],
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        ragnarok = report["actionable_paths"]["ragnarok_triplet_from_latest_summary"]
        self.assertEqual(
            ragnarok["path_status"],
            "active_ragnarok_current_roles_unverified",
        )
        self.assertEqual(ragnarok["authorization"], "non-authorizing")
        self.assertEqual(ragnarok["source_authorization"], "live-approved")
        self.assertEqual(ragnarok["evidence_status"], "diagnostic_passive_non_evidence")
        self.assertEqual(ragnarok["present_event_roles"], [])
        self.assertEqual(
            ragnarok["source_present_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(
            ragnarok["missing_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(ragnarok["role_source_status"], "untrusted_for_current_status")
        self.assertFalse(ragnarok["role_source_trusted_for_current_status"])
        self.assertFalse(ragnarok["live_ops_authorized"])
        self.assertFalse(ragnarok["workspace_writes_authorized"])
        self.assertFalse(ragnarok["counts_as_approved_runtime_evidence"])
        self.assertFalse(ragnarok["counts_toward_complete_sdk_claim_now"])
        self.assertFalse(ragnarok["counts_toward_p0_dependency_chain_claim_now"])
        self.assertNotIn("required_next_artifact", ragnarok)
        self.assertIn("diagnostic", ragnarok["non_evidence_reason"])
        self.assertIn("live_ops_authorized", ragnarok["source_overclaimed_authorization_flags"])
        self.assertIn(
            "workspace_writes_authorized",
            ragnarok["source_overclaimed_authorization_flags"],
        )

    def test_action_paths_alias_and_source_overclaims_fail_closed(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest["live_ops_authorized"] = True
        fastest["workspace_writes_authorized"] = True
        fastest["action_paths"] = fastest.pop("actionable_paths")
        paths = fastest["action_paths"]
        self.assertIsInstance(paths, dict)
        paths["active_genesis2_passive_missing_roles"]["authorizes_runtime_work"] = True
        paths["active_genesis2_passive_missing_roles"][
            "counts_toward_complete_sdk_claim_now"
        ] = True
        paths["player_notice_action"]["discord_authorized"] = True
        paths["player_notice_action"]["notice_sent"] = True
        paths["player_notice_action"]["notice_dry_run_accepted"] = True
        paths["player_notice_action"]["notice_bundle_accepted"] = True
        paths["player_notice_action"]["status"] = "sent"
        paths["player_notice_action"]["notice_report"] = {
            "deliveryStatus": "delivered",
            "progress": "1/12",
        }
        paths["player_notice_action"]["public_sdk_ready"] = True

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        path = report["action_paths"]["active_genesis2_passive_missing_roles"]
        self.assertFalse(path["authorizes_runtime_work"])
        self.assertFalse(path["counts_toward_complete_sdk_claim_now"])
        self.assertIn(
            "authorizes_runtime_work",
            path["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "counts_toward_complete_sdk_claim_now",
            path["source_overclaimed_authorization_flags"],
        )
        notice = report["action_paths"]["player_notice_action"]
        self.assertEqual(notice["path_status"], "player_notice_action_required")
        self.assertEqual(
            notice["evidence_status"],
            "player_notice_action_required_non_evidence",
        )
        self.assertFalse(notice["discord_authorized"])
        self.assertFalse(notice["notice_sent"])
        self.assertFalse(notice["notice_dry_run_accepted"])
        self.assertFalse(notice["notice_bundle_accepted"])
        self.assertFalse(notice["public_sdk_ready"])
        self.assertFalse(notice["counts_toward_complete_sdk_claim_now"])
        self.assertEqual(notice["complete_sdk_claim_progress_contribution"], 0)
        self.assertIn("discord_authorized", notice["source_overclaimed_authorization_flags"])
        self.assertIn("notice_sent", notice["source_overclaimed_authorization_flags"])
        self.assertIn(
            "notice_dry_run_accepted",
            notice["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "notice_bundle_accepted",
            notice["source_overclaimed_authorization_flags"],
        )
        self.assertIn("status", notice["source_overclaimed_authorization_flags"])
        self.assertIn(
            "notice_report.deliveryStatus",
            notice["source_overclaimed_authorization_flags"],
        )
        self.assertIn("public_sdk_ready", notice["source_overclaimed_authorization_flags"])
        self.assertIn("notice_report.progress", notice["source_overclaimed_progress_flags"])
        self.assertFalse(report["authorizations"]["server_operations_authorized"])
        self.assertFalse(report["authorizations"]["discord_authorized"])
        self.assertFalse(report["authorizations"]["player_notices_count_as_evidence"])
        fastest_report = report["fastest_next_sdk_unblock"]
        self.assertFalse(fastest_report["live_ops_authorized"])
        self.assertFalse(fastest_report["workspace_writes_authorized"])
        self.assertFalse(fastest_report["discord_authorized"])
        self.assertIn(
            "live_ops_authorized",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "workspace_writes_authorized",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        text = status_report.format_text(report)
        self.assertIn(
            "source_overclaims=authorizes_runtime_work,counts_toward_complete_sdk_claim_now",
            text,
        )
        self.assertIn(
            "player_notice_action_required=true; notice_action_authorized=false; "
            "discord_authorized=false",
            text,
        )

    def test_fastest_next_unblock_alias_smuggling_uses_canonical_route_action(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.update(
            {
                "recommended_next_action": (
                    "restart the server and claim the public stable SDK is ready now"
                ),
                "required_artifacts": ["stable_sdk_release_certificate"],
                "required_actions": ["publish_plugin_hub_package"],
                "required_event_roles": [],
                "next_route_blocker_after_acceptance": "permissions_admin_ready",
                "publicSdkReady": "ready",
                "runtimeReady": True,
                "stableSdkClaimAllowed": "yes",
                "completeSdkClaimProgressContribution": "1/12",
                "routeSnapshot": {
                    "status": "accepted",
                    "routeReady": True,
                    "p0DependencyChainClaimProgressRatio": "1/4",
                },
                "non_claim": "public stable SDK ready after this action",
            }
        )

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        fastest_report = report["fastest_next_sdk_unblock"]
        self.assertEqual(
            fastest_report["recommended_next_action"],
            (
                "produce approved copied runtime principal lifecycle evidence for "
                "obelisk.player_identity.v1 before reviewing public identity, "
                "permissions/admin, command response, or commands/replies ABI"
            ),
        )
        self.assertEqual(
            fastest_report["source_recommended_next_action"],
            "restart the server and claim the public stable SDK is ready now",
        )
        self.assertEqual(
            fastest_report["required_artifacts"][0],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertEqual(
            fastest_report["source_required_artifacts"],
            ["stable_sdk_release_certificate"],
        )
        self.assertEqual(fastest_report["required_actions"], ["player_notice_action"])
        self.assertEqual(
            fastest_report["source_required_actions"],
            ["publish_plugin_hub_package"],
        )
        self.assertEqual(
            fastest_report["next_route_blocker_after_acceptance"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            fastest_report["source_next_route_blocker_after_acceptance"],
            "permissions_admin_ready",
        )
        self.assertFalse(fastest_report["public_sdk_ready"])
        self.assertFalse(fastest_report["runtime_ready"])
        self.assertFalse(fastest_report["stable_claim_allowed"])
        self.assertEqual(fastest_report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(fastest_report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(fastest_report["current_turn_scope_required"])
        self.assertTrue(
            fastest_report["active_runtime_window_requires_standing_or_current_scope"]
        )
        self.assertTrue(fastest_report["standing_launch_authority_recorded"])
        self.assertIn(
            "publicSdkReady",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "runtimeReady",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "stableSdkClaimAllowed",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "routeSnapshot.status",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "routeSnapshot.routeReady",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "completeSdkClaimProgressContribution",
            fastest_report["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "routeSnapshot.p0DependencyChainClaimProgressRatio",
            fastest_report["source_overclaimed_progress_flags"],
        )

        text = status_report.format_text(report)
        self.assertIn(
            "produce approved copied runtime principal lifecycle evidence",
            text,
        )
        self.assertNotIn("restart the server", text)
        self.assertNotIn("public stable SDK ready after this action", text)

    def test_next_action_sequence_is_planning_metadata_only(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["next_action_sequence"] = [
            {
                "description": "publish Plugin Hub after public SDK readiness is ready",
                "runtimeEvidenceReady": True,
                "countsTowardCompleteSdkClaim": True,
                "completeSdkClaimProgressContribution": "1/12",
                "p0DependencyChainClaimProgressContribution": "1/4",
                "pluginHubReady": True,
                "pluginHubPublicationAllowed": True,
                "publicationAuthorized": True,
            }
        ]
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest["next_action_sequence"] = [
            {
                "description": "public SDK ready and Plugin Hub publication ready",
                "approvedRuntimeEvidenceReady": True,
                "runtimeEvidenceReady": True,
                "publicSdkReady": True,
                "countsTowardP0DependencyChainClaim": True,
                "completeSdkClaimProgressContribution": 1,
                "p0DependencyChainClaimProgressContribution": "1/4",
                "pluginHubReady": True,
                "pluginHubReadinessClaimAllowed": True,
                "pluginHubPublicationAllowed": True,
                "publicationAuthorized": True,
            }
        ]

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["approved_runtime_evidence_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["plugin_hub_ready"])
        self.assertFalse(report["plugin_hub_readiness_claim_allowed"])
        self.assertFalse(report["plugin_hub_publication_allowed"])
        self.assertFalse(report["publication_authorized"])

        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("next_action_sequence[0].runtimeEvidenceReady", violations)
        self.assertIn("next_action_sequence[0].pluginHubReady", violations)
        self.assertIn("next_action_sequence[0].publicationAuthorized", violations)
        self.assertIn("next_action_sequence[0].completeSdkClaimProgressContribution", violations)
        self.assertIn(
            "fastest_next_sdk_unblock.next_action_sequence[0].pluginHubReady",
            violations,
        )
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

        fastest_report = report["fastest_next_sdk_unblock"]
        self.assertTrue(fastest_report["next_action_sequence_metadata_only"])
        normalized_step = fastest_report["next_action_sequence"][0]
        self.assertEqual(
            normalized_step["description"],
            "public SDK ready and Plugin Hub publication ready",
        )
        self.assertFalse(normalized_step["approvedRuntimeEvidenceReady"])
        self.assertFalse(normalized_step["runtimeEvidenceReady"])
        self.assertFalse(normalized_step["publicSdkReady"])
        self.assertFalse(normalized_step["countsTowardP0DependencyChainClaim"])
        self.assertEqual(normalized_step["completeSdkClaimProgressContribution"], 0)
        self.assertEqual(normalized_step["p0DependencyChainClaimProgressContribution"], 0)
        self.assertFalse(normalized_step["pluginHubReady"])
        self.assertFalse(normalized_step["pluginHubReadinessClaimAllowed"])
        self.assertFalse(normalized_step["pluginHubPublicationAllowed"])
        self.assertFalse(normalized_step["publicationAuthorized"])
        self.assertFalse(fastest_report["plugin_hub_ready"])
        self.assertFalse(fastest_report["plugin_hub_readiness_claim_allowed"])
        self.assertFalse(fastest_report["plugin_hub_publication_allowed"])
        self.assertFalse(fastest_report["publication_authorized"])
        self.assertIn(
            "next_action_sequence[0].runtimeEvidenceReady",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "next_action_sequence[0].pluginHubReady",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "next_action_sequence[0].publicationAuthorized",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "next_action_sequence[0].completeSdkClaimProgressContribution",
            fastest_report["source_overclaimed_progress_flags"],
        )

        compact = status_report.format_compact_summary(report)
        self.assertIn("route=approved_runtime_evidence_missing", compact)
        self.assertIn("Plugin Hub readiness, publication permission", compact)

    def test_promotion_certificate_builder_report_overclaims_are_diagnosed(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["player_identity_promotion_certificate_build_report"] = {
            "schema": "obelisk.player-identity-promotion-certificate-build-report.v1",
            "status": "built",
            "promotion_status": "promoted",
            "identity_surface_certificate_binding_valid": True,
            "certificate_binding_valid": True,
            "output_certificate": {
                "path": "tests/core/generated-player-identity-certificate.json",
                "sha256": "0" * 64,
            },
            "publicSdkReady": True,
            "runtimeReady": True,
            "sdkProgress": 1,
            "p0Progress": 1,
            "countsTowardV1Completion": True,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn(
            "player_identity_promotion_certificate_build_report.promotion_status",
            violations,
        )
        self.assertIn(
            "player_identity_promotion_certificate_build_report.identity_surface_certificate_binding_valid",
            violations,
        )
        self.assertIn(
            "player_identity_promotion_certificate_build_report.publicSdkReady",
            violations,
        )
        self.assertIn(
            "player_identity_promotion_certificate_build_report.sdkProgress",
            violations,
        )
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

    def test_targeted_action_paths_progress_aliases_are_zeroed(self) -> None:
        public_sdk = self.public_sdk_payload()
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        targeted_path_ids = (
            "historical_theisland_candidate_missing_sidecars",
            "active_genesis2_passive_missing_roles",
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle",
            "player_notice_action",
        )
        for path_id in targeted_path_ids:
            path = paths[path_id]
            self.assertIsInstance(path, dict)
            path["counts_toward_public_sdk"] = True
            path["counts_toward_runtime"] = True
            path["counts_toward_v1_completion"] = True
            path["counts_toward_complete_sdk_claim"] = True
            path["counts_toward_p0_dependency_chain_claim"] = True
            path["public_or_runtime_accounting_allowed"] = True
            path["progress"] = "1/12"
            path["claim_progress_contribution"] = 1
            path["public_sdk_progress_contribution"] = 1
            path["runtime_progress_contribution"] = 1

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        for path_id in targeted_path_ids:
            normalized = report["actionable_paths"][path_id]
            with self.subTest(path_id=path_id):
                self.assertEqual(normalized["authorization"], "non-authorizing")
                self.assertFalse(normalized["counts_toward_public_sdk"])
                self.assertFalse(normalized["counts_toward_runtime"])
                self.assertFalse(normalized["counts_toward_v1_completion"])
                self.assertFalse(normalized["counts_toward_complete_sdk_claim"])
                self.assertFalse(normalized["counts_toward_p0_dependency_chain_claim"])
                self.assertFalse(normalized["public_or_runtime_accounting_allowed"])
                for key in status_report.FAIL_CLOSED_ACTION_ZERO_FIELDS:
                    self.assertEqual(normalized[key], 0, key)
                self.assertIn(
                    "counts_toward_complete_sdk_claim",
                    normalized["source_overclaimed_authorization_flags"],
                )
                self.assertIn("progress", normalized["source_overclaimed_progress_flags"])
                self.assertIn(
                    "public_sdk_progress_contribution",
                    normalized["source_overclaimed_progress_flags"],
                )

        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn(
            "fastest_next_sdk_unblock.actionable_paths.player_notice_action.progress",
            violations,
        )
        self.assertIn(
            (
                "fastest_next_sdk_unblock.actionable_paths."
                "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle."
                "claim_progress_contribution"
            ),
            violations,
        )
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

    def test_readiness_and_evidence_synonym_overclaims_fail_closed(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest["approved_runtime_evidence"] = True
        fastest["runtime_evidence_ready"] = True
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        paths["active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"][
            "approved_runtime_evidence"
        ] = True
        paths["active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"][
            "runtime_evidence_ready"
        ] = True
        paths["active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"][
            "counts_as_runtime_evidence"
        ] = True
        header = self.header_gate_payload()
        header["ready"] = True
        header["promotion_ready"] = True
        header["public_header_allowed"] = True
        header["public_sdk_ready"] = True
        header["runtime_ready"] = True
        closure = self.closure_payload()
        closure["approved_runtime_evidence"] = True
        closure["approved_runtime_evidence_present"] = True
        closure["runtime_evidence_ready"] = True
        closure["readiness_claims"] = {
            "public_sdk_ready": True,
            "runtime_ready": True,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=header,
            header_gate_returncode=0,
            closure=closure,
            closure_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["source_ready"])
        self.assertEqual(report["source_status"], "ready")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertIn("ready", report["source_overclaimed_readiness_flags"])
        self.assertIn("status", report["source_overclaimed_readiness_flags"])
        self.assertIn("public_sdk_ready", report["source_overclaimed_readiness_flags"])
        self.assertIn("runtime_ready", report["source_overclaimed_readiness_flags"])
        self.assertIn("stable_claim_allowed", report["source_overclaimed_readiness_flags"])

        fastest_report = report["fastest_next_sdk_unblock"]
        self.assertFalse(fastest_report["approved_runtime_evidence"])
        self.assertFalse(fastest_report["runtime_evidence_ready"])
        self.assertFalse(fastest_report["counts_as_approved_runtime_evidence"])
        self.assertIn(
            "approved_runtime_evidence",
            fastest_report["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "runtime_evidence_ready",
            fastest_report["source_overclaimed_authorization_flags"],
        )

        ragnarok = report["actionable_paths"][
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
        ]
        self.assertFalse(ragnarok["approved_runtime_evidence"])
        self.assertFalse(ragnarok["runtime_evidence_ready"])
        self.assertFalse(ragnarok["counts_as_runtime_evidence"])
        self.assertFalse(ragnarok["counts_as_approved_runtime_evidence"])
        self.assertIn(
            "approved_runtime_evidence",
            ragnarok["source_overclaimed_authorization_flags"],
        )
        self.assertIn(
            "counts_as_runtime_evidence",
            ragnarok["source_overclaimed_authorization_flags"],
        )

        self.assertFalse(report["header_gate"]["promotion_ready"])
        self.assertFalse(report["header_gate"]["public_header_allowed"])
        self.assertFalse(report["header_gate"]["public_sdk_ready"])
        self.assertFalse(report["header_gate"]["runtime_ready"])
        self.assertTrue(report["header_gate"]["source_promotion_ready"])
        self.assertIn(
            "public_header_allowed",
            report["header_gate"]["source_overclaimed_readiness_flags"],
        )
        self.assertFalse(report["closure"]["approved_runtime_evidence"])
        self.assertFalse(report["closure"]["approved_runtime_evidence_present"])
        self.assertFalse(report["closure"]["runtime_evidence_ready"])
        self.assertIn(
            "approved_runtime_evidence",
            report["closure"]["source_overclaimed_evidence_flags"],
        )
        self.assertIn(
            "runtime_evidence_ready",
            report["closure"]["source_overclaimed_evidence_flags"],
        )
        approved_in_game = report["approved_in_game_evidence"]
        self.assertFalse(approved_in_game["approved_in_game_evidence_ready"])
        self.assertFalse(approved_in_game["approved_runtime_evidence"])
        self.assertFalse(approved_in_game["runtime_evidence_ready"])
        self.assertFalse(approved_in_game["counts_toward_complete_sdk_claim_now"])
        self.assertFalse(
            approved_in_game["complete_lifecycle_event_triplet_observed_diagnostic_only"]
        )
        ragnarok_summary = approved_in_game["path_summaries"][
            "active_ragnarok_passive_complete_triplet_non_evidence_needs_bundle"
        ]
        self.assertFalse(ragnarok_summary["complete_required_role_triplet"])
        self.assertEqual(
            ragnarok_summary["source_present_event_roles"],
            ["session_start", "session_start_rejected", "session_end"],
        )
        self.assertEqual(ragnarok_summary["role_source_status"], "untrusted_for_current_status")
        self.assertFalse(ragnarok_summary["role_source_trusted_for_current_status"])
        self.assertFalse(ragnarok_summary["approved_runtime_evidence"])
        self.assertFalse(ragnarok_summary["counts_as_approved_runtime_evidence"])

        text = status_report.format_text(report)
        self.assertIn(
            "source readiness overclaims normalized false: "
            "ready,public_sdk_ready,runtime_ready,stable_claim_allowed,status",
            text,
        )
        self.assertIn(
            "header source readiness overclaims normalized false: "
            "promotion_ready,public_header_allowed,public_sdk_ready,runtime_ready",
            text,
        )
        self.assertIn(
            "closure source evidence overclaims: "
            "approved_runtime_evidence,approved_runtime_evidence_present,runtime_evidence_ready; "
            "normalized_approved_runtime_evidence=false",
            text,
        )

    def test_string_readiness_status_overclaims_fail_closed(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = "ready"
        public_sdk["status"] = "public-sdk-ready"
        public_sdk["public_sdk_ready"] = "supported"
        public_sdk["runtime_ready"] = "available"
        public_sdk["stable_claim_allowed"] = "allowed"
        public_sdk["stable_sdk_ready"] = "stable-sdk-ready"

        header = self.header_gate_payload()
        header["ready"] = "ready"
        header["promotion_ready"] = "supported"
        header["public_header_allowed"] = "available"
        header["public_abi_ready"] = "passed"
        header["public_sdk_ready"] = "stable-sdk-ready"
        header["runtime_ready"] = "release-ready"

        closure = self.closure_payload()
        closure["ready"] = "ready"
        closure["approved_runtime_evidence"] = "approved"
        closure["runtime_evidence_ready"] = "supported"
        closure["readiness_claims"] = {
            "public_sdk_ready": "supported",
            "runtime_ready": "available",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=header,
            header_gate_returncode=0,
            closure=closure,
            closure_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["source_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertTrue(report["source_stable_sdk_ready"])
        self.assertEqual(
            report["source_overclaimed_readiness_flags"],
            [
                "ready",
                "public_sdk_ready",
                "runtime_ready",
                "stable_claim_allowed",
                "stable_sdk_ready",
                "status",
            ],
        )

        header_report = report["header_gate"]
        self.assertFalse(header_report["ready"])
        self.assertFalse(header_report["promotion_ready"])
        self.assertFalse(header_report["public_header_allowed"])
        self.assertFalse(header_report["public_abi_ready"])
        self.assertFalse(header_report["public_sdk_ready"])
        self.assertFalse(header_report["runtime_ready"])
        self.assertTrue(header_report["source_ready"])
        self.assertTrue(header_report["source_promotion_ready"])
        self.assertTrue(header_report["source_public_header_allowed"])
        self.assertTrue(header_report["source_public_abi_ready"])
        self.assertTrue(header_report["source_public_sdk_ready"])
        self.assertTrue(header_report["source_runtime_ready"])
        self.assertIn("promotion_ready", header_report["source_overclaimed_readiness_flags"])
        self.assertIn("public_header_allowed", header_report["source_overclaimed_readiness_flags"])
        self.assertIn("public_abi_ready", header_report["source_overclaimed_readiness_flags"])
        self.assertIn("public_sdk_ready", header_report["source_overclaimed_readiness_flags"])
        self.assertIn("runtime_ready", header_report["source_overclaimed_readiness_flags"])

        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["input_presence_ready"])
        self.assertFalse(report["closure"]["public_sdk_ready"])
        self.assertFalse(report["closure"]["runtime_ready"])
        self.assertTrue(report["closure"]["source_public_sdk_ready"])
        self.assertTrue(report["closure"]["source_runtime_ready"])
        self.assertIn("approved_runtime_evidence", report["closure"]["source_overclaimed_evidence_flags"])
        self.assertIn("runtime_evidence_ready", report["closure"]["source_overclaimed_evidence_flags"])
        self.assertIn("public_sdk_ready", report["closure"]["source_overclaimed_readiness_flags"])
        self.assertIn("runtime_ready", report["closure"]["source_overclaimed_readiness_flags"])

    def test_status_report_fails_closed_on_inconsistent_readiness_inputs(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = False
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        closure = self.closure_payload()
        closure["ready"] = True
        closure["server_operations_authorized"] = True
        closure["workspace_writes_authorized"] = True
        closure["readiness_claims"] = {
            "public_sdk_ready": True,
            "runtime_ready": True,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
            closure=closure,
            closure_returncode=1,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["closure"]["server_operations_authorized"])
        self.assertFalse(report["closure"]["workspace_writes_authorized"])
        self.assertFalse(report["closure"]["ready"])
        self.assertTrue(report["closure"]["input_presence_ready"])
        self.assertEqual(
            report["closure"]["ready_scope"],
            "normalized_status_report_only_not_public_or_runtime_readiness",
        )
        self.assertTrue(report["closure"]["source_server_operations_authorized"])
        self.assertTrue(report["closure"]["source_workspace_writes_authorized"])
        self.assertFalse(report["closure"]["public_sdk_ready"])
        self.assertFalse(report["closure"]["runtime_ready"])
        self.assertTrue(report["closure"]["source_public_sdk_ready"])
        self.assertTrue(report["closure"]["source_runtime_ready"])
        self.assertEqual(
            report["closure"]["source_overclaimed_readiness_flags"],
            ["public_sdk_ready", "runtime_ready"],
        )
        text = status_report.format_text(report)
        self.assertIn(
            "closure source readiness overclaims: public_sdk_ready,runtime_ready; "
            "normalized_public_sdk_ready=false; normalized_runtime_ready=false",
            text,
        )

    def test_route_blocker_normalizes_bogus_progress_counts_to_zero(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 5
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 7
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "5/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 2
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 2
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "2/4"

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["source_sdk_counts"]["promoted_for_claim_count"], 5)
        self.assertEqual(report["source_p0_counts"]["promoted_for_claim_count"], 2)
        self.assertIn(
            "complete_sdk_blockers_promoted_for_claim_count",
            report["source_overclaimed_count_flags"],
        )
        self.assertIn(
            "p0_dependency_chain_progress_ratio",
            report["source_overclaimed_count_flags"],
        )
        self.assertEqual(
            report["sdk_counts"]["normalized_due_to"],
            ["approved_runtime_evidence_missing"],
        )
        text = status_report.format_text(report)
        self.assertIn("SDK counts: 0/12 promoted_for_claim", text)
        self.assertIn("P0 counts: 0/4 promoted_for_claim", text)
        self.assertIn("source count overclaims normalized to current blocker", text)

    def test_false_progress_aliases_normalize_counts_even_without_route_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        paths["player_notice_action"]["playerNoticeActionStatus"] = "sent"
        public_sdk["passive_latest_summary"] = {
            "schema": "obelisk.player-principal-passive-snapshot-latest.v1",
            "ready": True,
            "countsAsPassiveEvidence": True,
            "passiveSnapshotCountsAsRuntimeEvidence": True,
            "evidenceAccepted": True,
            "tripletValidated": True,
            "sdkClaimCount": 1,
            "complete_sdk_claim_progress_contribution": 1,
        }
        public_sdk["activation_preconditions_report"] = {
            "schema": "obelisk.player-principal-lifecycle-activation-preconditions.v1",
            "ready": True,
            "activation_preconditions_met": True,
            "ready_scope": "offline_pre_activation_consistency_only",
            "counts_toward_sdk": True,
            "counts_toward_p0_dependency_chain": True,
        }
        public_sdk["beta_notice_send_attestation"] = {
            "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
            "ready": True,
            "status": "prepared",
            "mode": "confirmed_send",
            "discord_sent": True,
            "counts_as_approved_runtime_evidence": True,
        }
        public_sdk["request_check_readiness"] = {
            "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
            "ready": True,
            "request_pack_ready": True,
            "route_ready": True,
            "complete_sdk_claim_progress_contribution": "1/12",
        }
        public_sdk["runtime_window_activation"] = {
            "schema": "obelisk.player-principal-lifecycle-runtime-window-activation.v1",
            "status": "prepared",
            "runtimeWindowPrepared": True,
            "runtime_window_authorized": True,
            "runtime_window_activation_ready_under_recorded_standing_launch_authority": True,
            "standing_launch_authority_counts_as_approved_runtime_evidence": True,
        }
        public_sdk["runtime_window_plan_report"] = {
            "schema": "obelisk.player-principal-lifecycle-runtime-window-plan.v1",
            "status": "planned_offline_only",
            "ready": True,
            "runtimeWindowPlanReady": True,
            "approvedRuntimeEvidenceReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["executor_report"] = {
            "status": "executed",
            "ready": True,
            "runtimeWindowExecutorReady": True,
            "countsTowardSdk": True,
            "p0DependencyChainClaimProgressContribution": 1,
        }
        public_sdk["runtime_window_executor_closure_artifact"] = {
            "schema": "obelisk.player-principal-lifecycle-runtime-window-executor-closure.v1",
            "status": "closed",
            "ready": True,
            "closureComplete": True,
            "runtimeWindowClosureReady": True,
            "runtimeWindowExecutorClosureReady": True,
            "countsTowardCompleteSdkClaim": True,
            "sdkCompletionCount": 1,
        }
        public_sdk["evidence_closure_report"] = {
            "status": "closed",
            "ready": True,
            "evidenceClosureReady": True,
            "closureAccepted": True,
            "runtimeEvidenceReady": True,
            "approvedRuntimeEvidencePresent": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["preactivation_report"] = {
            "status": "passed",
            "ready": True,
            "preactivationReady": True,
            "progress": "1/4",
        }
        public_sdk["confirmed_notice_report"] = {
            "schema": "obelisk.player-principal-confirmed-notice-report.v1",
            "status": "confirmed_send",
            "ready": True,
            "deliveryConfirmed": True,
            "noticeConfirmed": True,
            "confirmedNoticeSent": True,
            "countsAsApprovedRuntimeEvidence": True,
            "progress": "1/12",
        }
        public_sdk["approved_runtime_manifest"] = {
            "status": "present",
            "ready": True,
            "approvedRuntimeManifestPresent": True,
            "approvedRuntimeManifestReferenced": True,
            "approvedRuntimeEvidence": True,
            "runtimeEvidenceReady": True,
        }
        public_sdk["public_reachability"] = {
            "schema": "obelisk.player-principal-public-reachability-check.v1",
            "status": "reachable",
            "ready": True,
            "publicReachabilityReady": True,
            "publicReachabilityAccepted": True,
            "publicReachabilityReachable": True,
            "publicReachabilityCountsAsRuntimeEvidence": True,
            "sdkCompletionCount": 1,
            "counts_toward_sdk": True,
        }
        public_sdk["approved_bundle_request"] = {
            "schema": "obelisk.player-identity-approved-bundle-request.v1",
            "status": "accepted",
            "ready": True,
            "approvedBundleRequestReady": True,
        }
        public_sdk["route_bound_identity_source_forwarding"] = {
            "schema": "obelisk.command-permission-route-bound-identity-source-forwarding.v1",
            "status": "accepted",
            "ready": True,
            "routeBoundIdentitySourceForwardingReady": True,
        }
        public_sdk["route_planning_report"] = {
            "schema": "obelisk.command-route-planning-report.v1",
            "state": "completed",
            "ready": True,
            "completeSdkClaimProgressContribution": 1,
        }
        public_sdk["route_simulation"] = {
            "schema": "obelisk.command-permission-route-simulation.v1",
            "simulation_only": True,
            "status": "accepted",
            "counts_toward_v1_completion": True,
        }
        public_sdk["post_evidence_identity_lock"] = {
            "schema": "obelisk.command-permission-route-post-evidence-identity-lock.v1",
            "status": "unlocked",
            "identity_lock_ready": True,
            "p0_dependency_chain_progress_contribution": 1,
        }
        public_sdk["copied_log_only_artifact"] = {
            "schema": "obelisk.player-principal-copied-log-only-artifact.v1",
            "artifact_scope": "copied_log_only",
            "copiedLogOnlyReady": True,
            "copiedLogOnlyStatus": "accepted",
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["accepted_artifact_class_report"] = {
            "schema": "obelisk.accepted-artifact-class.v1",
            "artifact_class": "accepted_artifact_class",
            "status": "accepted",
            "acceptedArtifactClassReady": True,
            "p0DependencyChainClaimProgressContribution": 1,
        }
        public_sdk["binding_required_report"] = {
            "schema": "obelisk.binding-required.v1",
            "binding_required": True,
            "status": "ready",
            "bindingRequiredReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["delegated_route_gate_report"] = {
            "schema": "obelisk.delegated-route-gate-report.v1",
            "status": "ready",
            "ready": True,
            "delegatedRouteGateReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["package_exact_install_report"] = {
            "schema": "obelisk.installed-sdk-package-exact.v1",
            "status": "unblocked",
            "packageExactUnblocked": True,
            "sdkCredits": 1,
        }
        public_sdk["package_non_exact_install_report"] = {
            "schema": "obelisk.installed-sdk-package-non-exact.v1",
            "state": "allowed",
            "packageNonExactAllowed": True,
            "completeSdkCredit": "1/12",
        }
        public_sdk["installed_sdk_package_shape"] = {
            "schema": "obelisk.installed-sdk-package-shape.v1",
            "status": "package-shape-evidence-only",
            "packageAvailable": ["blocked", "published"],
            "abiLayoutReady": True,
            "cmakeConfigReady": True,
            "cmakePackageReady": True,
            "cmakePackagePassed": True,
            "componentsSdkReady": True,
            "installedHeadersReady": True,
            "obeliskConfigCmakeReady": True,
            "obeliskTargetsCmakeReady": True,
            "ownerTokenRegistrationReady": True,
            "ownerTokenSdkConsumerReady": True,
            "packageShapeReady": True,
            "packageShapeV1CompletionReady": True,
            "packageShapeCountsTowardCompletion": True,
            "pluginHubPackagePublished": True,
            "pluginHubCountsTowardV1Completion": True,
            "pluginHubPublicationEnabled": True,
            "pluginHubSeedReady": True,
            "pluginHubSupportTierReady": True,
            "publicHeadersReady": True,
            "publicHeaderAllowed": True,
            "publicHeaderAvailable": True,
            "publicHeadersAvailable": True,
            "publicHeaderValidated": True,
            "installedSdkConsumerTestsReady": True,
            "publicModuleSdkCoverageReady": True,
            "publicModuleSdkCovered": True,
            "publicSdkCoverageReady": True,
            "releaseStatementReady": True,
            "runtimeLiveOpApprovalAllowed": True,
            "runtimeReadinessClaimAllowed": True,
            "scopedReleaseStatementCountsTowardCompleteSdkClaim": True,
            "scopedReleaseStatementReady": True,
            "sdkCoverageComplete": True,
            "structSizeReady": True,
            "structSizeValidated": True,
            "supportTierActivated": True,
            "supportTierAllowed": True,
            "supportTierReady": True,
            "supportTierSupported": True,
            "supportTier": "release-supported",
            "packageShapeStatus": "published",
            "packageExactStatus": "unblocked",
            "packageNonExactAllowed": True,
            "sdkPackageState": "ready",
            "packageExactCredits": "1/12",
            "packageNonExactCredit": 1,
            "pluginHubReady": True,
            "pluginHubCredits": 1,
            "publicPackageReady": True,
            "sdkCompletionCount": 1,
            "p0DependencyChainPromotedForClaimCount": 1,
            "p0DependencyChainReady": True,
            "v1CompletionClaimAllowed": True,
            "promoted_for_claim_count": [0, 1],
            "install": {"status": "ready"},
        }
        public_sdk["scoped_release_statement"] = {
            "schema": "obelisk.scoped-release-statement-outcomes.v1",
            "statementAccepted": True,
            "statementPassed": True,
            "outcomesSatisfied": True,
            "releaseStatementBookkeepingCountsTowardCompletion": True,
            "completionCount": 8,
            "claimCount": 8,
            "promotedCount": 1,
            "completionProgressRatio": "8/8",
        }
        public_sdk["side_lanes"] = {
            "transfer_scriptstruct_readiness": {
                "schema": "obelisk.transfer-scriptstruct-readiness-check.v1",
                "status": "candidate_ready",
                "complete_sdk_claim_progress_ratio": "1/12",
            }
        }
        route_gate = public_sdk["command_permission_route_gate"]
        self.assertIsInstance(route_gate, dict)
        simulation = route_gate["post_evidence_p0_lock_simulation"]
        self.assertIsInstance(simulation, dict)
        simulation["status"] = "accepted"
        simulation["p0_dependency_chain_claim_progress_contribution"] = "1/4"

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertFalse(report["p0_dependency_chain_full_ordered_promotion_observed"])
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["sdk_counts"]["normalized_due_to"],
        )
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn(
            "fastest_next_sdk_unblock.actionable_paths.player_notice_action.playerNoticeActionStatus",
            violations,
        )
        self.assertIn(
            "passive_latest_summary.complete_sdk_claim_progress_contribution",
            violations,
        )
        self.assertIn(
            "activation_preconditions_report.activation_preconditions_met",
            violations,
        )
        self.assertIn("beta_notice_send_attestation.discord_sent", violations)
        self.assertIn("beta_notice_send_attestation.mode", violations)
        self.assertIn("beta_notice_send_attestation.status", violations)
        self.assertIn("request_check_readiness.request_pack_ready", violations)
        self.assertIn("runtime_window_activation.status", violations)
        self.assertIn("runtime_window_activation.runtimeWindowPrepared", violations)
        self.assertIn("runtime_window_activation.runtime_window_authorized", violations)
        self.assertIn(
            "runtime_window_activation.runtime_window_activation_ready_under_recorded_standing_launch_authority",
            violations,
        )
        self.assertIn(
            "runtime_window_activation.standing_launch_authority_counts_as_approved_runtime_evidence",
            violations,
        )
        self.assertIn("runtime_window_plan_report.ready", violations)
        self.assertIn("runtime_window_plan_report.runtimeWindowPlanReady", violations)
        self.assertIn(
            "runtime_window_plan_report.approvedRuntimeEvidenceReady",
            violations,
        )
        self.assertIn(
            "runtime_window_plan_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("executor_report.ready", violations)
        self.assertIn("executor_report.runtimeWindowExecutorReady", violations)
        self.assertIn("executor_report.countsTowardSdk", violations)
        self.assertIn(
            "executor_report.p0DependencyChainClaimProgressContribution",
            violations,
        )
        self.assertIn("runtime_window_executor_closure_artifact.status", violations)
        self.assertIn("runtime_window_executor_closure_artifact.ready", violations)
        self.assertIn("runtime_window_executor_closure_artifact.closureComplete", violations)
        self.assertIn(
            "runtime_window_executor_closure_artifact.runtimeWindowClosureReady",
            violations,
        )
        self.assertIn(
            "runtime_window_executor_closure_artifact.runtimeWindowExecutorClosureReady",
            violations,
        )
        self.assertIn(
            "runtime_window_executor_closure_artifact.countsTowardCompleteSdkClaim",
            violations,
        )
        self.assertIn(
            "runtime_window_executor_closure_artifact.sdkCompletionCount",
            violations,
        )
        self.assertIn("evidence_closure_report.status", violations)
        self.assertIn("evidence_closure_report.ready", violations)
        self.assertIn("evidence_closure_report.evidenceClosureReady", violations)
        self.assertIn("evidence_closure_report.closureAccepted", violations)
        self.assertIn("evidence_closure_report.runtimeEvidenceReady", violations)
        self.assertIn("evidence_closure_report.approvedRuntimeEvidencePresent", violations)
        self.assertIn(
            "evidence_closure_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("preactivation_report.status", violations)
        self.assertIn("preactivation_report.ready", violations)
        self.assertIn("preactivation_report.preactivationReady", violations)
        self.assertIn("preactivation_report.progress", violations)
        self.assertIn("confirmed_notice_report.status", violations)
        self.assertIn("confirmed_notice_report.ready", violations)
        self.assertIn("confirmed_notice_report.deliveryConfirmed", violations)
        self.assertIn("confirmed_notice_report.noticeConfirmed", violations)
        self.assertIn("confirmed_notice_report.confirmedNoticeSent", violations)
        self.assertIn("confirmed_notice_report.countsAsApprovedRuntimeEvidence", violations)
        self.assertIn("confirmed_notice_report.progress", violations)
        self.assertIn("approved_runtime_manifest.status", violations)
        self.assertIn("approved_runtime_manifest.ready", violations)
        self.assertIn("approved_runtime_manifest.approvedRuntimeManifestPresent", violations)
        self.assertIn("approved_runtime_manifest.approvedRuntimeManifestReferenced", violations)
        self.assertIn("approved_runtime_manifest.approvedRuntimeEvidence", violations)
        self.assertIn("approved_runtime_manifest.runtimeEvidenceReady", violations)
        self.assertIn("public_reachability.status", violations)
        self.assertIn("public_reachability.publicReachabilityReady", violations)
        self.assertIn("public_reachability.publicReachabilityAccepted", violations)
        self.assertIn("public_reachability.publicReachabilityReachable", violations)
        self.assertIn(
            "public_reachability.publicReachabilityCountsAsRuntimeEvidence",
            violations,
        )
        self.assertIn("public_reachability.sdkCompletionCount", violations)
        self.assertIn("approved_bundle_request.status", violations)
        self.assertIn("approved_bundle_request.approvedBundleRequestReady", violations)
        self.assertIn("route_bound_identity_source_forwarding.status", violations)
        self.assertIn(
            "route_bound_identity_source_forwarding.routeBoundIdentitySourceForwardingReady",
            violations,
        )
        self.assertIn("route_planning_report.state", violations)
        self.assertIn("route_planning_report.ready", violations)
        self.assertIn(
            "route_planning_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("route_simulation.status", violations)
        self.assertIn("post_evidence_identity_lock.identity_lock_ready", violations)
        self.assertIn("copied_log_only_artifact.copiedLogOnlyReady", violations)
        self.assertIn("copied_log_only_artifact.copiedLogOnlyStatus", violations)
        self.assertIn(
            "copied_log_only_artifact.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("accepted_artifact_class_report.status", violations)
        self.assertIn(
            "accepted_artifact_class_report.acceptedArtifactClassReady",
            violations,
        )
        self.assertIn(
            "accepted_artifact_class_report.p0DependencyChainClaimProgressContribution",
            violations,
        )
        self.assertIn("binding_required_report.status", violations)
        self.assertIn("binding_required_report.bindingRequiredReady", violations)
        self.assertIn(
            "binding_required_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("delegated_route_gate_report.status", violations)
        self.assertIn("delegated_route_gate_report.ready", violations)
        self.assertIn("delegated_route_gate_report.delegatedRouteGateReady", violations)
        self.assertIn(
            "delegated_route_gate_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("package_exact_install_report.status", violations)
        self.assertIn("package_exact_install_report.packageExactUnblocked", violations)
        self.assertIn("package_exact_install_report.sdkCredits", violations)
        self.assertIn("package_non_exact_install_report.state", violations)
        self.assertIn("package_non_exact_install_report.packageNonExactAllowed", violations)
        self.assertIn("package_non_exact_install_report.completeSdkCredit", violations)
        expected_package_aliases = (
            "packageAvailable",
            "abiLayoutReady",
            "cmakeConfigReady",
            "cmakePackageReady",
            "cmakePackagePassed",
            "componentsSdkReady",
            "installedHeadersReady",
            "obeliskConfigCmakeReady",
            "obeliskTargetsCmakeReady",
            "ownerTokenRegistrationReady",
            "ownerTokenSdkConsumerReady",
            "packageShapeReady",
            "packageShapeV1CompletionReady",
            "packageShapeCountsTowardCompletion",
            "pluginHubPackagePublished",
            "pluginHubCountsTowardV1Completion",
            "pluginHubPublicationEnabled",
            "pluginHubSeedReady",
            "pluginHubSupportTierReady",
            "publicHeadersReady",
            "publicHeaderAllowed",
            "publicHeaderAvailable",
            "publicHeadersAvailable",
            "publicHeaderValidated",
            "installedSdkConsumerTestsReady",
            "publicModuleSdkCoverageReady",
            "publicModuleSdkCovered",
            "publicSdkCoverageReady",
            "releaseStatementReady",
            "runtimeLiveOpApprovalAllowed",
            "runtimeReadinessClaimAllowed",
            "scopedReleaseStatementCountsTowardCompleteSdkClaim",
            "scopedReleaseStatementReady",
            "sdkCoverageComplete",
            "structSizeReady",
            "structSizeValidated",
            "supportTierActivated",
            "supportTierAllowed",
            "supportTierReady",
            "supportTierSupported",
            "supportTier",
            "packageShapeStatus",
            "packageExactStatus",
            "packageNonExactAllowed",
            "sdkPackageState",
            "packageExactCredits",
            "packageNonExactCredit",
            "pluginHubReady",
            "pluginHubCredits",
            "publicPackageReady",
            "sdkCompletionCount",
            "p0DependencyChainPromotedForClaimCount",
            "p0DependencyChainReady",
            "v1CompletionClaimAllowed",
        )
        for alias in expected_package_aliases:
            with self.subTest(alias=alias):
                self.assertIn(f"installed_sdk_package_shape.{alias}", violations)
        self.assertIn("installed_sdk_package_shape.promoted_for_claim_count", violations)
        self.assertIn("installed_sdk_package_shape.install.status", violations)
        self.assertIn("passive_latest_summary.countsAsPassiveEvidence", violations)
        self.assertIn(
            "passive_latest_summary.passiveSnapshotCountsAsRuntimeEvidence",
            violations,
        )
        self.assertIn("passive_latest_summary.evidenceAccepted", violations)
        self.assertIn("passive_latest_summary.tripletValidated", violations)
        self.assertIn("passive_latest_summary.sdkClaimCount", violations)
        self.assertIn("scoped_release_statement.statementAccepted", violations)
        self.assertIn("scoped_release_statement.statementPassed", violations)
        self.assertIn("scoped_release_statement.outcomesSatisfied", violations)
        self.assertIn(
            "scoped_release_statement.releaseStatementBookkeepingCountsTowardCompletion",
            violations,
        )
        self.assertIn("scoped_release_statement.completionCount", violations)
        self.assertIn("scoped_release_statement.claimCount", violations)
        self.assertIn("scoped_release_statement.promotedCount", violations)
        self.assertIn("scoped_release_statement.completionProgressRatio", violations)
        self.assertIn("side_lanes.transfer_scriptstruct_readiness.status", violations)
        self.assertIn(
            "side_lanes.transfer_scriptstruct_readiness.complete_sdk_claim_progress_ratio",
            violations,
        )
        self.assertIn(
            "command_permission_route_gate.post_evidence_p0_lock_simulation.p0_dependency_chain_claim_progress_contribution",
            violations,
        )
        text = status_report.format_text(report)
        self.assertIn("non-counting false progress aliases observed", text)
        self.assertIn("ordered_p0_chain_promoted=false", text)

    def test_checkjoininprogress_session_start_rejected_offline_acceptance_stays_missing_runtime_evidence(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["approved_runtime_evidence"] = {
            "source_kind": "checkjoininprogress_offline_acceptance",
            "ready_scope": "offline_session_start_rejected_acceptance",
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_ready": True,
        }
        public_sdk["checkJoinInProgressOfflineAcceptance"] = {
            "source_kind": "ShooterGameMode.CheckJoinInProgress offline acceptance",
            "target_set": "session_start_rejected_candidate_only",
            "status": "candidate_only_accepted",
            "ready": True,
            "publicSdkReady": True,
            "stableClaimAllowed": True,
            "v1CompletionReady": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressRatio": "1/4",
        }

        self.assertFalse(
            status_report.accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        )
        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("checkJoinInProgressOfflineAcceptance.status", violations)
        self.assertIn("checkJoinInProgressOfflineAcceptance.ready", violations)
        self.assertIn(
            "checkJoinInProgressOfflineAcceptance.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn(
            "checkJoinInProgressOfflineAcceptance.p0DependencyChainClaimProgressRatio",
            violations,
        )

    def test_quarantined_runtime_evidence_sources_do_not_unlock_route_or_counts(self) -> None:
        source_cases: dict[str, dict[str, object]] = {
            "active_player_no_accepted_events": {
                "source_kind": "active_player_presence_no_accepted_lifecycle_events",
                "active_player_presence": {
                    "players_detected": True,
                    "accepted_lifecycle_event_count": 0,
                },
                "accepted_event_count": 0,
            },
            "diagnostic_fname_drift": {
                "source_kind": "diagnostic_fname_drift_manifest",
                "diagnostic_fname_drift": True,
                "accepted_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "diagnostic_compact_chain_metadata": {
                "source_kind": "diagnostic_compact_chain_metadata",
                "compact_blocker_chain": (
                    "approved_runtime_evidence_missing -> complete_sdk_ready"
                ),
                "after_runtime_evidence": "complete_sdk_ready",
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "source_bound_drift_manifest": {
                "source_kind": "source_bound_drift_manifest",
                "source_bound_drift_manifest": {
                    "status": "accepted",
                    "public_sdk_ready": True,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "confirmed_beta_notice": {
                "source_kind": "confirmed_beta_notice_report",
                "confirmed_beta_notice_report": {
                    "status": "confirmed_send",
                    "confirmedBetaNoticeSent": True,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "discord_beta_bridge_ready": {
                "source_kind": "discord_beta_bridge_config",
                "discord_beta_bridge_status": "config_valid",
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "player_notice_action": {
                "source_kind": "player_notice_action",
                "player_notice_action": {
                    "status": "sent",
                    "notice_sent": True,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "multi_surface_beta_capture_pack": {
                "source_kind": "multi_surface_beta_capture_pack",
                "multi_surface_beta_capture_pack": {
                    "status": "candidate_pack_validated",
                    "candidate_surface_count": 15,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "package_shape_install": {
                "source_kind": "package_shape_install",
                "installed_sdk_package_shape": {
                    "status": "package-shape-evidence-only",
                    "packageShapeReady": True,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
            "side_lane_candidate": {
                "source_kind": "side_lane_candidate",
                "transfer_scriptstruct_readiness": {
                    "status": "candidate_ready",
                    "ready": True,
                },
                "accepted_lifecycle_events": [
                    "session_start",
                    "session_start_rejected",
                    "session_end",
                ],
            },
        }

        for case_id, source_payload in source_cases.items():
            with self.subTest(case=case_id):
                public_sdk = self.public_sdk_payload()
                public_sdk.pop("current_route_blocker", None)
                public_sdk["remaining_route_blockers"] = []
                public_sdk["ready"] = True
                public_sdk["status"] = "ready"
                public_sdk["public_sdk_ready"] = True
                public_sdk["runtime_ready"] = True
                public_sdk["stable_claim_allowed"] = True
                public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
                public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
                public_sdk["complete_sdk_blocker_total"] = 12
                public_sdk["complete_sdk_progress_ratio"] = "12/12"
                public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
                public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
                public_sdk["p0_dependency_chain_total"] = 4
                public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
                fastest = public_sdk["fastest_next_sdk_unblock"]
                self.assertIsInstance(fastest, dict)
                fastest.pop("current_route_blocker", None)
                fastest["remaining_route_blockers"] = []
                public_sdk["approved_runtime_evidence"] = {
                    **source_payload,
                    "approved_runtime_evidence_accepted": True,
                    "evidence_bundle_accepted": True,
                    "approved_runtime_evidence_ready": True,
                    "approved_runtime_evidence_present": True,
                    "runtime_evidence_ready": True,
                    "public_sdk_ready": True,
                    "runtime_ready": True,
                    "counts_toward_complete_sdk_claim": True,
                    "counts_toward_p0_dependency_chain_claim": True,
                    "complete_sdk_claim_progress_contribution": "1/12",
                    "p0_dependency_chain_claim_progress_contribution": "1/4",
                }

                self.assertFalse(
                    status_report.accepted_approved_runtime_principal_lifecycle_bundle(
                        public_sdk
                    )
                )
                report = status_report.summarize(
                    public_sdk=public_sdk,
                    public_sdk_returncode=0,
                    header_gate=self.header_gate_payload(),
                    header_gate_returncode=0,
                )

                self.assertFalse(report["ready"])
                self.assertEqual(report["status"], "blocked")
                self.assertEqual(
                    report["current_route_blocker"],
                    "approved_runtime_evidence_missing",
                )
                self.assertEqual(
                    report["remaining_route_blockers"],
                    ["approved_runtime_evidence_missing"],
                )
                self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
                self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
                self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
                self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])
                self.assertFalse(report["stable_claim_allowed"])
                self.assertFalse(report["approved_runtime_evidence_ready"])
                self.assertEqual(
                    report["critical_path_summary"]["after_runtime_evidence"],
                    "identity_public_contract_gate_missing",
                )
                self.assertEqual(
                    report["stable_sdk_remaining_blockers"]["after_runtime_evidence"],
                    "identity_public_contract_gate_missing",
                )
                self.assertEqual(
                    report["missing_required_artifact"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                simulation = report["post_evidence_p0_lock_simulation"]
                self.assertEqual(
                    simulation["current_route_blocker"],
                    "approved_runtime_evidence_missing",
                )
                self.assertEqual(
                    simulation[
                        "simulated_route_blocker_after_accepted_runtime_evidence"
                    ],
                    "identity_public_contract_gate_missing",
                )
                self.assertFalse(simulation["permissions_admin_unlocked"])
                self.assertFalse(simulation["command_response_unlocked"])
                self.assertFalse(simulation["commands_replies_unlocked"])
                self.assertFalse(simulation["counts_toward_p0_dependency_chain_claim"])
                self.assertEqual(
                    simulation["p0_dependency_chain_claim_progress_contribution"],
                    0,
                )

    def test_new_non_counting_reports_cannot_clear_runtime_blocker_or_progress(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["current_route_blocker"] = "identity_public_contract_gate_missing"
        public_sdk["remaining_route_blockers"] = [
            "identity_public_contract_gate_missing"
        ]
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest["current_route_blocker"] = "identity_public_contract_gate_missing"
        fastest["remaining_route_blockers"] = [
            "identity_public_contract_gate_missing"
        ]
        public_sdk["static_registration_orientation_report"] = {
            "schema": "obelisk.native-ufunction-registration-static-discovery.v1",
            "status": "accepted",
            "ready": True,
            "staticRegistrationOrientationReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["discord_bot_tester_status_workflow"] = {
            "schema": "obelisk.player-principal-lifecycle-beta-tester-status-workflow.v1",
            "status": "ready",
            "testerStatusWorkflowReady": True,
            "discordBotTesterWorkflowReady": True,
            "countsTowardSdk": True,
            "sdkProgress": 1,
        }
        public_sdk["active_beta_notice_report"] = {
            "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
            "status": "confirmed_send",
            "betaNoticeSent": True,
            "clearsApprovedRuntimeEvidenceMissing": True,
            "p0DependencyChainClaimProgressContribution": "1/4",
        }
        public_sdk["runtime_window_command_plan"] = {
            "schema": "obelisk.player-principal-lifecycle-evidence-command-sequence.v1",
            "status": "planned",
            "ready": True,
            "runtimeWindowCommandPlanReady": True,
            "clearsApprovedRuntimeEvidenceMissing": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["strict_triplet_selector_summary"] = {
            "schema": "obelisk.player-principal-lifecycle-strict-selector-summary.v1",
            "status": "selected",
            "ready": True,
            "strictTripletSelectorReady": True,
            "approvedRuntimeEvidenceAccepted": True,
            "p0Progress": 1,
        }
        public_sdk["runtime_evidence_contract_review_currentness"] = {
            "schema": "obelisk.player-identity-public-contract-currentness-diagnostic.v1",
            "status": "current",
            "ready": True,
            "publicContractCurrentnessReady": True,
            "runtimeEvidenceAccepted": True,
            "p0ProgressContribution": "1/4",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(
            report["current_route_blocker"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["remaining_route_blockers"],
            ["approved_runtime_evidence_missing"],
        )
        self.assertEqual(
            report["source_current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["source_remaining_route_blockers"],
            ["identity_public_contract_gate_missing"],
        )
        self.assertIn("current_route_blocker", report["source_overclaimed_route_flags"])
        self.assertIn("remaining_route_blockers", report["source_overclaimed_route_flags"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertIn(
            "approved_runtime_evidence_missing",
            report["sdk_counts"]["normalized_due_to"],
        )
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        for path in (
            "static_registration_orientation_report.ready",
            "static_registration_orientation_report.staticRegistrationOrientationReady",
            "static_registration_orientation_report.completeSdkClaimProgressContribution",
            "discord_bot_tester_status_workflow.testerStatusWorkflowReady",
            "discord_bot_tester_status_workflow.countsTowardSdk",
            "discord_bot_tester_status_workflow.sdkProgress",
            "active_beta_notice_report.status",
            "active_beta_notice_report.betaNoticeSent",
            "active_beta_notice_report.clearsApprovedRuntimeEvidenceMissing",
            "active_beta_notice_report.p0DependencyChainClaimProgressContribution",
            "runtime_window_command_plan.ready",
            "runtime_window_command_plan.runtimeWindowCommandPlanReady",
            "runtime_window_command_plan.clearsApprovedRuntimeEvidenceMissing",
            "runtime_window_command_plan.completeSdkClaimProgressContribution",
            "strict_triplet_selector_summary.status",
            "strict_triplet_selector_summary.strictTripletSelectorReady",
            "strict_triplet_selector_summary.approvedRuntimeEvidenceAccepted",
            "strict_triplet_selector_summary.p0Progress",
            "runtime_evidence_contract_review_currentness.ready",
            "runtime_evidence_contract_review_currentness.publicContractCurrentnessReady",
            "runtime_evidence_contract_review_currentness.runtimeEvidenceAccepted",
            "runtime_evidence_contract_review_currentness.p0ProgressContribution",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)

        overclaim_summary = report["source_overclaim_summary"]
        self.assertIn("report", overclaim_summary["components"])
        self.assertEqual(
            overclaim_summary["components"]["report"]["categories"]["route"],
            ["current_route_blocker", "remaining_route_blockers"],
        )
        text = status_report.format_text(report)
        self.assertIn(
            "source route overclaims normalized to approved_runtime_evidence_missing",
            text,
        )

    def test_non_claim_context_statuses_do_not_create_source_overclaims(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["installed_sdk_package_shape"] = {
            "schema": "obelisk.installed-sdk-package-shape.v1",
            "status": "package-shape-evidence-only",
            "installed_files": [
                "include/obelisk/ObeliskApi.h",
                "lib/cmake/Obelisk/ObeliskConfig.cmake",
            ],
        }
        public_sdk["post_reboot_passive_monitor"] = {
            "schema": "obelisk.post-reboot-passive-monitor.v1",
            "status": "observed",
            "present": True,
            "monitor_latest_tick_utc": "2026-06-07T10:15:00Z",
        }
        public_sdk["offline_candidate_pack"] = {
            "schema": "obelisk.offline-candidate-pack.v1",
            "status": "candidate_pack_validated",
            "candidate_surface_count": 15,
            "candidate_only": True,
        }
        public_sdk["mission_transfer_dino_tribe_outcome_accounting"] = {
            "schema": (
                "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1"
            ),
            "ready": True,
            "accounting_route": "manifest_umbrella_excluded",
            "surface": "obelisk.mission_transfer_dino_tribe.v1",
            "v1_accounted": True,
            "leaf_outcome_accounting": {
                "v1_accounted": True,
                "leaves": [
                    {
                        "leaf": "mission",
                        "explicit_non_promoted_outcome": True,
                        "v1_accounted": True,
                    }
                ],
            },
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["source_overclaim_total_flag_count"], 0)
        self.assertEqual(report["source_overclaim_component_count"], 0)
        self.assertEqual(report["side_lane_source_overclaim_count"], 0)
        self.assertEqual(report["non_counting_false_progress_alias_violations"], [])

    def test_generic_pack_package_passive_and_standing_aliases_are_non_counting(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        public_sdk["offline_candidate_pack"] = {
            "schema": "obelisk.offline-candidate-pack.v1",
            "status": "ready",
            "candidatePackCountsTowardSdk": True,
            "candidatePackCountsAsRuntimeEvidence": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["passive_monitor_status"] = {
            "schema": "obelisk.passive-monitor-status.v1",
            "status": "ok",
            "passiveMonitorCountsTowardSdk": True,
            "passiveMonitorCountsTowardP0DependencyChain": True,
            "passiveMonitorCountsAsRuntimeEvidence": True,
            "publicSdkReady": True,
        }
        public_sdk["standing_authority_context"] = {
            "schema": "obelisk.standing-authority-context.v1",
            "standingAuthority": True,
            "standingAuthorityReady": True,
            "standingAuthorityCountsAsRuntimeEvidence": True,
            "standingAuthorityCountsTowardSdk": True,
            "standingAuthorityCountsTowardP0DependencyChain": True,
            "standingAuthorityCountsTowardCompleteSdkClaim": True,
        }
        public_sdk["install_package_check"] = {
            "schema": "obelisk.installed-sdk-package-check.v1",
            "findPackageSucceeded": True,
            "componentSdkFound": True,
            "packageInstallSuccess": True,
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )

        violations = report["non_counting_false_progress_alias_violations"]
        for path in (
            "offline_candidate_pack.status",
            "offline_candidate_pack.candidatePackCountsTowardSdk",
            "offline_candidate_pack.candidatePackCountsAsRuntimeEvidence",
            "offline_candidate_pack.completeSdkClaimProgressContribution",
            "passive_monitor_status.status",
            "passive_monitor_status.passiveMonitorCountsTowardSdk",
            "passive_monitor_status.passiveMonitorCountsTowardP0DependencyChain",
            "passive_monitor_status.passiveMonitorCountsAsRuntimeEvidence",
            "passive_monitor_status.publicSdkReady",
            "standing_authority_context.standingAuthority",
            "standing_authority_context.standingAuthorityReady",
            "standing_authority_context.standingAuthorityCountsAsRuntimeEvidence",
            "standing_authority_context.standingAuthorityCountsTowardSdk",
            "standing_authority_context.standingAuthorityCountsTowardP0DependencyChain",
            "standing_authority_context.standingAuthorityCountsTowardCompleteSdkClaim",
            "install_package_check.findPackageSucceeded",
            "install_package_check.componentSdkFound",
            "install_package_check.packageInstallSuccess",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)

    def test_quarantined_new_reports_cannot_impersonate_strict_runtime_checker(self) -> None:
        source_markers: dict[str, dict[str, object]] = {
            "static_registration_orientation": {
                "source_kind": "static_registration_orientation_report",
                "static_registration_orientation_report": {"status": "accepted"},
            },
            "discord_bot_tester_workflow": {
                "source_kind": "discord_bot_tester_status_workflow",
                "tester_status_workflow": {"status": "ready"},
            },
            "beta_notice": {
                "source_kind": "confirmed_beta_notice_report",
                "confirmed_beta_notice_report": {"status": "confirmed_send"},
            },
            "runtime_window_command_plan": {
                "source_kind": "runtime_window_command_plan",
                "runtime_window_command_plan": {"status": "planned"},
            },
            "strict_selector_summary": {
                "source_kind": "strict_lifecycle_triplet_selector_summary",
                "strict_triplet_selector_summary": {"status": "selected"},
            },
            "public_contract_currentness": {
                "source_kind": "runtime_evidence_contract_review_currentness",
                "runtime_evidence_contract_review_currentness": {"status": "current"},
            },
        }

        for case_id, source_marker in source_markers.items():
            with self.subTest(case=case_id):
                public_sdk = self.public_sdk_payload()
                public_sdk.pop("current_route_blocker", None)
                public_sdk["remaining_route_blockers"] = []
                public_sdk["ready"] = True
                public_sdk["status"] = "ready"
                public_sdk["public_sdk_ready"] = True
                public_sdk["runtime_ready"] = True
                public_sdk["stable_claim_allowed"] = True
                public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
                public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
                public_sdk["complete_sdk_blocker_total"] = 12
                public_sdk["complete_sdk_progress_ratio"] = "12/12"
                public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
                public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
                public_sdk["p0_dependency_chain_total"] = 4
                public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
                fastest = public_sdk["fastest_next_sdk_unblock"]
                self.assertIsInstance(fastest, dict)
                fastest.pop("current_route_blocker", None)
                fastest["remaining_route_blockers"] = []
                public_sdk["approved_runtime_evidence"] = {
                    **self.strict_approved_runtime_checker_contract_payload(),
                    **source_marker,
                }

                self.assertFalse(
                    status_report.accepted_approved_runtime_principal_lifecycle_bundle(
                        public_sdk
                    )
                )
                report = status_report.summarize(
                    public_sdk=public_sdk,
                    public_sdk_returncode=0,
                    header_gate=self.header_gate_payload(),
                    header_gate_returncode=0,
                )

                self.assertFalse(report["ready"])
                self.assertEqual(
                    report["current_route_blocker"],
                    "approved_runtime_evidence_missing",
                )
                self.assertEqual(
                    report["remaining_route_blockers"],
                    ["approved_runtime_evidence_missing"],
                )
                self.assertFalse(report["approved_runtime_evidence_ready"])
                self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
                self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
                self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
                self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)

    def test_partial_lifecycle_event_artifact_stays_missing_runtime_evidence(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["approved_runtime_evidence"] = {
            "source_kind": "partial_lifecycle_event_proof",
            "accepted_lifecycle_event_count": 2,
            "approved_runtime_evidence_accepted": True,
            "evidence_bundle_accepted": True,
            "approved_runtime_evidence_ready": True,
        }
        public_sdk["partial_lifecycle_event_proof"] = {
            "schema": "obelisk.partial-lifecycle-event-proof.v1",
            "status": "complete_triplet_present",
            "ready": True,
            "runtimeReady": True,
            "publicSdkReady": True,
            "stableClaimAllowed": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }

        self.assertFalse(
            status_report.accepted_approved_runtime_principal_lifecycle_bundle(public_sdk)
        )
        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("partial_lifecycle_event_proof.status", violations)
        self.assertIn("partial_lifecycle_event_proof.ready", violations)
        self.assertIn("partial_lifecycle_event_proof.runtimeReady", violations)
        self.assertIn("partial_lifecycle_event_proof.publicSdkReady", violations)
        self.assertIn(
            "partial_lifecycle_event_proof.completeSdkClaimProgressContribution",
            violations,
        )

    def test_runtime_live_status_aliases_are_non_counting_overclaims(self) -> None:
        payload = {
            "installedRuntimeStatus": {
                "schema": "obelisk.runtime-live-status.v1",
                "status": "ok",
                "ready": True,
                "runtimeReady": True,
                "countsTowardP0DependencyChain": True,
                "p0DependencyChainClaimProgressContribution": "1/4",
            },
            "broadcastOk": {
                "status": "sent_ok",
                "publicSdkReady": True,
                "completeSdkClaimProgressContribution": "1/12",
            },
            "rconOk": {
                "status": "ok",
                "permissionsReady": True,
                "commandsReady": True,
                "countsTowardCompleteSdkClaim": True,
            },
        }

        violations = status_report.non_counting_false_progress_alias_violations(payload)
        overclaimed_flags, overclaimed_progress = status_report.source_alias_overclaim_paths(
            payload,
            false_keys=set(status_report.FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(status_report.FAIL_CLOSED_ACTION_ZERO_FIELDS),
            initial_non_counting_context=False,
        )
        sanitized = status_report.sanitize_non_counting_alias_payload(
            payload,
            false_keys=set(status_report.FAIL_CLOSED_ACTION_FALSE_FLAGS),
            zero_keys=set(status_report.FAIL_CLOSED_ACTION_ZERO_FIELDS),
            initial_non_counting_context=False,
        )

        for path in (
            "installedRuntimeStatus.status",
            "installedRuntimeStatus.ready",
            "installedRuntimeStatus.runtimeReady",
            "installedRuntimeStatus.countsTowardP0DependencyChain",
            "broadcastOk.status",
            "broadcastOk.publicSdkReady",
            "rconOk.status",
            "rconOk.permissionsReady",
            "rconOk.commandsReady",
            "rconOk.countsTowardCompleteSdkClaim",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)
                self.assertIn(path, overclaimed_flags)

        for path in (
            "installedRuntimeStatus.p0DependencyChainClaimProgressContribution",
            "broadcastOk.completeSdkClaimProgressContribution",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)
                self.assertIn(path, overclaimed_progress)

        self.assertFalse(sanitized["installedRuntimeStatus"]["status"])
        self.assertFalse(sanitized["broadcastOk"]["status"])
        self.assertFalse(sanitized["rconOk"]["permissionsReady"])
        self.assertFalse(sanitized["rconOk"]["commandsReady"])
        self.assertEqual(
            sanitized["installedRuntimeStatus"]["p0DependencyChainClaimProgressContribution"],
            0,
        )
        self.assertEqual(
            sanitized["broadcastOk"]["completeSdkClaimProgressContribution"],
            0,
        )

    def test_operator_monitor_and_confirmed_beta_notice_context_stays_zero_progress(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["post_reboot_monitor_context"] = {
            "schema": "obelisk.player-principal-passive-snapshot-latest.v1",
            "source_kind": "passive_monitor",
            "status": "unblocked",
            "ready": True,
            "countsAsRuntimeEvidence": True,
            "sdkCredits": 1,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }
        public_sdk["confirmed_beta_notice_report"] = {
            "schema": "obelisk.player-principal-confirmed-beta-notice-report.v1",
            "status": "confirmed_send",
            "ready": True,
            "confirmedBetaNoticeSent": True,
            "countsAsApprovedRuntimeEvidence": True,
            "progress": "1/12",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)

        operator_context = report["operator_context_summary"]
        self.assertEqual(operator_context["context_count"], 2)
        self.assertEqual(
            operator_context["context_ids"],
            ["post_reboot_passive_monitor", "confirmed_beta_notice"],
        )
        self.assertFalse(operator_context["counts_as_approved_runtime_evidence"])
        self.assertFalse(operator_context["counts_toward_sdk"])
        self.assertFalse(operator_context["counts_toward_p0_dependency_chain"])
        self.assertFalse(operator_context["counts_toward_complete_sdk_claim"])
        self.assertEqual(operator_context["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(operator_context["p0_dependency_chain_claim_progress_contribution"], 0)

        contexts_by_id = {
            context["id"]: context for context in operator_context["contexts"]
        }
        monitor = contexts_by_id["post_reboot_passive_monitor"]
        self.assertEqual(monitor["source_keys"], ["post_reboot_monitor_context"])
        self.assertTrue(monitor["mentioned_as_operator_context"])
        self.assertFalse(monitor["counts_as_runtime_evidence"])
        self.assertEqual(monitor["complete_sdk_claim_progress_contribution"], 0)
        self.assertIn(
            "post_reboot_monitor_context.countsAsRuntimeEvidence",
            monitor["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "post_reboot_monitor_context.completeSdkClaimProgressContribution",
            monitor["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "post_reboot_monitor_context.p0DependencyChainClaimProgressContribution",
            monitor["source_overclaimed_progress_flags"],
        )

        beta_notice = contexts_by_id["confirmed_beta_notice"]
        self.assertEqual(beta_notice["source_keys"], ["confirmed_beta_notice_report"])
        self.assertFalse(beta_notice["counts_as_approved_runtime_evidence"])
        self.assertFalse(beta_notice["public_sdk_ready"])
        self.assertEqual(beta_notice["v1_completion_contribution"], 0)
        self.assertIn(
            "confirmed_beta_notice_report.confirmedBetaNoticeSent",
            beta_notice["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "confirmed_beta_notice_report.countsAsApprovedRuntimeEvidence",
            beta_notice["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "confirmed_beta_notice_report.progress",
            beta_notice["source_overclaimed_progress_flags"],
        )

        overclaim_summary = report["source_overclaim_summary"]
        self.assertTrue(overclaim_summary["status_report_only"])
        self.assertIn("operator_context", overclaim_summary["components"])
        operator_overclaims = overclaim_summary["components"]["operator_context"]["categories"]
        self.assertIn(
            "post_reboot_passive_monitor.post_reboot_monitor_context.countsAsRuntimeEvidence",
            operator_overclaims["authorization_or_claim"],
        )
        self.assertIn(
            "confirmed_beta_notice.confirmed_beta_notice_report.confirmedBetaNoticeSent",
            operator_overclaims["authorization_or_claim"],
        )
        self.assertIn(
            "post_reboot_passive_monitor.post_reboot_monitor_context.completeSdkClaimProgressContribution",
            operator_overclaims["progress"],
        )
        self.assertIn(
            "confirmed_beta_notice.confirmed_beta_notice_report.progress",
            operator_overclaims["progress"],
        )
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

        stable_blockers = report["stable_sdk_remaining_blockers"]
        self.assertEqual(stable_blockers["operator_context_count"], 2)
        self.assertEqual(
            stable_blockers["operator_context_ids"],
            ["post_reboot_passive_monitor", "confirmed_beta_notice"],
        )
        self.assertFalse(stable_blockers["operator_context_counts_as_approved_runtime_evidence"])
        self.assertFalse(stable_blockers["operator_context_counts_as_sdk_progress"])
        self.assertFalse(stable_blockers["operator_context_counts_toward_p0_dependency_chain"])
        self.assertFalse(stable_blockers["operator_context_counts_toward_complete_sdk_claim"])
        self.assertEqual(stable_blockers["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(stable_blockers["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(stable_blockers["current_p0_surface"], "obelisk.player_identity.v1")

        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("post_reboot_monitor_context.ready", violations)
        self.assertIn("post_reboot_monitor_context.status", violations)
        self.assertIn("post_reboot_monitor_context.countsAsRuntimeEvidence", violations)
        self.assertIn("post_reboot_monitor_context.sdkCredits", violations)
        self.assertIn(
            "post_reboot_monitor_context.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn("confirmed_beta_notice_report.status", violations)
        self.assertIn("confirmed_beta_notice_report.confirmedBetaNoticeSent", violations)
        self.assertIn("confirmed_beta_notice_report.progress", violations)

        text = status_report.format_text(report)
        self.assertIn(
            "operator_context=post_reboot_passive_monitor,confirmed_beta_notice",
            text,
        )
        self.assertIn("operator_context_counts_as_progress=false", text)
        self.assertIn("SDK=0/12; SDK_remaining=12; P0=0/4; P0_remaining=4", text)

    def test_handoff_context_aliases_stay_non_counting(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["handoff_checkpoint"] = {
            "schema": "obelisk.worker-handoff.v1",
            "status": "ready",
            "ready": True,
            "countsTowardSdk": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")

        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("handoff_checkpoint.status", violations)
        self.assertIn("handoff_checkpoint.ready", violations)
        self.assertIn("handoff_checkpoint.countsTowardSdk", violations)
        self.assertIn(
            "handoff_checkpoint.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn(
            "handoff_checkpoint.p0DependencyChainClaimProgressContribution",
            violations,
        )
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

    def test_closed_agent_notes_and_rcon_counts_stay_non_counting(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["closedAgentNotes"] = {
            "schema": "obelisk.closed-agent-notes.v1",
            "status": "ready",
            "ready": True,
            "publicSdkReady": True,
            "runtimeReady": True,
            "stableClaimAllowed": True,
            "pluginHubReady": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }
        public_sdk["rconCounts"] = {
            "schema": "obelisk.rcon-counts.v1",
            "status": "ok",
            "ready": True,
            "rconPlayerCount": 3,
            "publicSdkReady": True,
            "runtimeReady": True,
            "pluginHubReadinessClaimAllowed": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }
        public_sdk["startEndOnlyEvidenceReport"] = {
            "schema": "obelisk.start-end-only-evidence.v1",
            "status": "ready",
            "ready": True,
            "publicSdkReady": True,
            "runtimeReady": True,
            "stableClaimAllowed": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertFalse(report["plugin_hub_ready"])
        self.assertFalse(report["plugin_hub_readiness_claim_allowed"])
        self.assertFalse(report["plugin_hub_publication_allowed"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)

        violations = report["non_counting_false_progress_alias_violations"]
        for path in (
            "closedAgentNotes.status",
            "closedAgentNotes.ready",
            "closedAgentNotes.publicSdkReady",
            "closedAgentNotes.runtimeReady",
            "closedAgentNotes.stableClaimAllowed",
            "closedAgentNotes.pluginHubReady",
            "closedAgentNotes.completeSdkClaimProgressContribution",
            "closedAgentNotes.p0DependencyChainClaimProgressContribution",
            "rconCounts.status",
            "rconCounts.ready",
            "rconCounts.publicSdkReady",
            "rconCounts.runtimeReady",
            "rconCounts.pluginHubReadinessClaimAllowed",
            "rconCounts.completeSdkClaimProgressContribution",
            "rconCounts.p0DependencyChainClaimProgressContribution",
            "startEndOnlyEvidenceReport.status",
            "startEndOnlyEvidenceReport.ready",
            "startEndOnlyEvidenceReport.publicSdkReady",
            "startEndOnlyEvidenceReport.runtimeReady",
            "startEndOnlyEvidenceReport.stableClaimAllowed",
            "startEndOnlyEvidenceReport.completeSdkClaimProgressContribution",
            "startEndOnlyEvidenceReport.p0DependencyChainClaimProgressContribution",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)

        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])
        self.assertGreater(report["source_overclaim_total_flag_count"], 0)

    def test_missing_route_blocker_fails_closed_without_accepted_runtime_bundle(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(
            report["missing_required_artifact"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_non_counting_alias_scanner_distinguishes_negative_and_positive_values(self) -> None:
        negative_payload = {
            "scoped_release_statement": {
                "schema": "obelisk.scoped-release-statement-outcomes.v1",
                "status": "blocked",
                "outcome": "excluded",
                "ready": False,
                "countsTowardP0DependencyChainClaim": "no",
                "releaseStatementBookkeepingCountsTowardCompletion": "false",
                "completeSdkClaimProgressContribution": "0/12",
                "completionProgressRatio": "0/12",
            }
        }
        positive_payload = {
            "scoped_release_statement": {
                "schema": "obelisk.scoped-release-statement-outcomes.v1",
                "status": "blocked",
                "countsTowardP0DependencyChainClaim": ["no", "yes"],
                "releaseStatementBookkeepingCountsTowardCompletion": "counts",
                "completeSdkClaimProgressContribution": ["0/12", "1/12"],
                "bookkeepingOutcomeStatus": "satisfied",
            }
        }

        self.assertEqual(status_report.non_counting_false_progress_alias_violations(negative_payload), [])
        violations = status_report.non_counting_false_progress_alias_violations(positive_payload)
        self.assertIn("scoped_release_statement.countsTowardP0DependencyChainClaim", violations)
        self.assertIn(
            "scoped_release_statement.releaseStatementBookkeepingCountsTowardCompletion",
            violations,
        )
        self.assertIn("scoped_release_statement.completeSdkClaimProgressContribution", violations)
        self.assertIn("scoped_release_statement.bookkeepingOutcomeStatus", violations)

    def test_dict_wrapped_operator_package_shape_aliases_stay_non_counting(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["installed_sdk_package_shape"] = {
            "schema": "obelisk.installed-sdk-package-shape.v1",
            "status": "package-shape-evidence-only",
            "publicSdkReady": {"value": True},
            "stableSdkReady": {"value": "ready"},
            "completeSdkClaimProgressContribution": {"value": "1/12"},
            "p0DependencyChainClaimProgressContribution": {"value": 1},
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=1,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)

        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("installed_sdk_package_shape.publicSdkReady", violations)
        self.assertIn("installed_sdk_package_shape.stableSdkReady", violations)
        self.assertIn(
            "installed_sdk_package_shape.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn(
            "installed_sdk_package_shape.p0DependencyChainClaimProgressContribution",
            violations,
        )
        self.assertIn("non_counting_false_progress_aliases", report["source_overclaimed_count_flags"])

        contexts_by_id = {
            context["id"]: context
            for context in report["operator_context_summary"]["contexts"]
        }
        package_shape = contexts_by_id["package_shape_install"]
        self.assertFalse(package_shape["public_sdk_ready"])
        self.assertFalse(package_shape["stable_claim_allowed"])
        self.assertEqual(package_shape["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(package_shape["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertIn(
            "installed_sdk_package_shape.publicSdkReady",
            package_shape["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "installed_sdk_package_shape.stableSdkReady",
            package_shape["source_overclaimed_authorization_or_claim_flags"],
        )
        self.assertIn(
            "installed_sdk_package_shape.completeSdkClaimProgressContribution",
            package_shape["source_overclaimed_progress_flags"],
        )
        self.assertIn(
            "installed_sdk_package_shape.p0DependencyChainClaimProgressContribution",
            package_shape["source_overclaimed_progress_flags"],
        )

        overclaim_summary = report["source_overclaim_summary"]
        self.assertIn("operator_context", overclaim_summary["components"])
        operator_overclaims = overclaim_summary["components"]["operator_context"]["categories"]
        self.assertIn(
            "package_shape_install.installed_sdk_package_shape.publicSdkReady",
            operator_overclaims["authorization_or_claim"],
        )
        self.assertIn(
            "package_shape_install.installed_sdk_package_shape.stableSdkReady",
            operator_overclaims["authorization_or_claim"],
        )
        self.assertIn(
            "package_shape_install.installed_sdk_package_shape.completeSdkClaimProgressContribution",
            operator_overclaims["progress"],
        )
        self.assertIn(
            "package_shape_install.installed_sdk_package_shape.p0DependencyChainClaimProgressContribution",
            operator_overclaims["progress"],
        )

    def test_offline_hardening_cert_and_debug_boundary_aliases_zero_status_counts(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        public_sdk["offline_hardening_report"] = {
            "schema": "obelisk.sdk-offline-hardening-report.v1",
            "status": "accepted",
            "runtimeReady": True,
            "publicSdkReady": True,
            "stableSdkReady": True,
            "pluginHubReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }
        public_sdk["reviewed_decision_record"] = {
            "schema": "obelisk.player-identity-reviewed-decision-record.v1",
            "status": "reviewed",
            "publicSdkReady": True,
            "p0DependencyChainReady": True,
        }
        public_sdk["generated_cert_report"] = {
            "schema": "obelisk.player-identity-generated-cert-report.v1",
            "certStatus": "generated",
            "stableSdkReady": True,
            "p0DependencyChainClaimProgressContribution": "1/4",
        }
        public_sdk["public_debug_boundary_fix"] = {
            "schema": "obelisk.public-debug-boundary-fix-report.v1",
            "status": "ready",
            "publicDebugBoundaryReady": True,
            "runtimeReady": True,
            "publicSdkReady": True,
            "pluginHubReady": True,
            "completeSdkClaimProgressContribution": "1/12",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        expected_paths = (
            "offline_hardening_report.status",
            "offline_hardening_report.runtimeReady",
            "offline_hardening_report.publicSdkReady",
            "offline_hardening_report.stableSdkReady",
            "offline_hardening_report.pluginHubReady",
            "offline_hardening_report.completeSdkClaimProgressContribution",
            "reviewed_decision_record.status",
            "reviewed_decision_record.publicSdkReady",
            "reviewed_decision_record.p0DependencyChainReady",
            "generated_cert_report.certStatus",
            "generated_cert_report.stableSdkReady",
            "generated_cert_report.p0DependencyChainClaimProgressContribution",
            "public_debug_boundary_fix.status",
            "public_debug_boundary_fix.publicDebugBoundaryReady",
            "public_debug_boundary_fix.runtimeReady",
            "public_debug_boundary_fix.publicSdkReady",
            "public_debug_boundary_fix.pluginHubReady",
            "public_debug_boundary_fix.completeSdkClaimProgressContribution",
        )
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertIn(path, violations)

    def test_terminal_certificate_placeholder_with_zero_source_overclaim_stays_non_counting(
        self,
    ) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        public_sdk["terminalCertificatePlaceholder"] = {
            "schema": "obelisk.commands-replies-terminal-certificate-placeholder.v1",
            "sourceKind": "terminal_certificate_placeholder",
            "status": "generated",
            "certificateStatus": "generated",
            "terminalCertificateReady": True,
            "sourceOverclaimTotal": 0,
            "publicSdkReady": True,
            "runtimeReady": True,
            "stableSdkReady": True,
            "countsTowardCompleteSdkClaim": True,
            "countsTowardP0DependencyChainClaim": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        for path in (
            "terminalCertificatePlaceholder.status",
            "terminalCertificatePlaceholder.certificateStatus",
            "terminalCertificatePlaceholder.terminalCertificateReady",
            "terminalCertificatePlaceholder.publicSdkReady",
            "terminalCertificatePlaceholder.runtimeReady",
            "terminalCertificatePlaceholder.stableSdkReady",
            "terminalCertificatePlaceholder.countsTowardCompleteSdkClaim",
            "terminalCertificatePlaceholder.countsTowardP0DependencyChainClaim",
            "terminalCertificatePlaceholder.completeSdkClaimProgressContribution",
            "terminalCertificatePlaceholder.p0DependencyChainClaimProgressContribution",
        ):
            with self.subTest(path=path):
                self.assertIn(path, violations)
        self.assertNotIn("terminalCertificatePlaceholder.sourceOverclaimTotal", violations)

    def test_nested_action_and_route_snapshot_aliases_zero_status_counts_without_route_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        paths = fastest["actionable_paths"]
        self.assertIsInstance(paths, dict)
        paths["generic_candidate_path"] = {
            "path_type": "candidate_path",
            "nested": {
                "publicSdkStatus": "ready",
                "runtimeReady": True,
                "stableSdkProgress": "1/12",
                "p0DependencyChainClaimProgressRatio": "1/4",
            },
            "routeSnapshot": {
                "status": "accepted",
                "routeSnapshotReady": True,
            },
        }
        public_sdk["route_snapshot"] = {
            "schema": "obelisk.command-permission-route-snapshot.v1",
            "status": "accepted",
            "routeSnapshotReady": True,
            "stableSdkState": "stable",
            "publicRuntimeProgress": "2/12",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        normalized_path = report["actionable_paths"]["generic_candidate_path"]
        self.assertFalse(normalized_path["nested"]["publicSdkStatus"])
        self.assertFalse(normalized_path["nested"]["runtimeReady"])
        self.assertEqual(normalized_path["nested"]["stableSdkProgress"], 0)
        self.assertEqual(normalized_path["nested"]["p0DependencyChainClaimProgressRatio"], 0)
        self.assertFalse(normalized_path["routeSnapshot"]["status"])
        self.assertFalse(normalized_path["routeSnapshot"]["routeSnapshotReady"])
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn(
            "fastest_next_sdk_unblock.actionable_paths.generic_candidate_path.nested.publicSdkStatus",
            violations,
        )
        self.assertIn(
            "fastest_next_sdk_unblock.actionable_paths.generic_candidate_path.nested.stableSdkProgress",
            violations,
        )
        self.assertIn("route_snapshot.routeSnapshotReady", violations)
        self.assertIn("route_snapshot.stableSdkState", violations)
        self.assertIn("route_snapshot.publicRuntimeProgress", violations)
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )

    def test_public_contract_review_artifact_aliases_zero_status_counts_without_route_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        public_sdk["public_contract_review_report"] = {
            "schema": "obelisk.player-identity-public-contract-review-artifact.v1",
            "status": "reviewed",
            "ready": True,
            "acceptedForContractReview": True,
            "contractReviewArtifactReady": True,
            "contractReviewStatus": "reviewed",
            "publicContractAllowed": True,
            "publicContractState": "ready",
            "publicContractReviewReady": True,
            "reviewedPublicContract": True,
            "completeSdkClaimProgressContribution": "1/12",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("public_contract_review_report.status", violations)
        self.assertIn("public_contract_review_report.contractReviewStatus", violations)
        self.assertIn("public_contract_review_report.publicContractState", violations)
        self.assertIn("public_contract_review_report.publicContractReviewReady", violations)
        self.assertIn("public_contract_review_report.reviewedPublicContract", violations)
        self.assertIn(
            "public_contract_review_report.completeSdkClaimProgressContribution",
            violations,
        )

    def test_player_identity_public_header_gate_aliases_zero_status_counts_without_route_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        public_sdk["player_identity_public_header_gate_report"] = {
            "schema": "obelisk.player-identity-public-header-gate-check.v1",
            "status": "ready",
            "ready": True,
            "publicHeaderGateReady": True,
            "publicHeaderAllowed": True,
            "identityPublicContractGateAccepted": True,
            "completeSdkClaimProgressContribution": "1/12",
            "p0DependencyChainClaimProgressContribution": "1/4",
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["source_overclaimed_count_flags"],
        )
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("player_identity_public_header_gate_report.status", violations)
        self.assertIn("player_identity_public_header_gate_report.ready", violations)
        self.assertIn(
            "player_identity_public_header_gate_report.publicHeaderGateReady",
            violations,
        )
        self.assertIn(
            "player_identity_public_header_gate_report.publicHeaderAllowed",
            violations,
        )
        self.assertIn(
            "player_identity_public_header_gate_report.identityPublicContractGateAccepted",
            violations,
        )
        self.assertIn(
            "player_identity_public_header_gate_report.completeSdkClaimProgressContribution",
            violations,
        )
        self.assertIn(
            "player_identity_public_header_gate_report.p0DependencyChainClaimProgressContribution",
            violations,
        )

    def test_internal_module_side_lane_aliases_zero_status_counts_without_route_blocker(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk.pop("current_route_blocker", None)
        public_sdk["remaining_route_blockers"] = []
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest.pop("current_route_blocker", None)
        fastest["remaining_route_blockers"] = []
        public_sdk["side_lanes"] = {
            "mission_leaf_internal_module": {
                "schema": "obelisk.internal-module-readiness.v1",
                "ready_scope": "internal_only",
                "moduleSdkReady": True,
                "publicModuleReady": True,
                "publicModuleSdkReady": True,
            }
        }

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        violations = report["non_counting_false_progress_alias_violations"]
        self.assertIn("side_lanes.mission_leaf_internal_module.moduleSdkReady", violations)
        self.assertIn("side_lanes.mission_leaf_internal_module.publicModuleReady", violations)
        self.assertIn("side_lanes.mission_leaf_internal_module.publicModuleSdkReady", violations)
        self.assertIn(
            "non_counting_false_progress_aliases",
            report["sdk_counts"]["normalized_due_to"],
        )

    def test_non_approved_route_blocker_blocks_public_and_stable_readiness(self) -> None:
        public_sdk = self.public_sdk_payload()
        public_sdk["ready"] = True
        public_sdk["status"] = "ready"
        public_sdk["public_sdk_ready"] = True
        public_sdk["runtime_ready"] = True
        public_sdk["stable_claim_allowed"] = True
        public_sdk["current_route_blocker"] = "identity_public_contract_gate_missing"
        public_sdk["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]
        public_sdk["complete_sdk_blockers_promoted_for_claim_count"] = 12
        public_sdk["complete_sdk_blockers_remaining_for_claim_count"] = 0
        public_sdk["complete_sdk_blocker_total"] = 12
        public_sdk["complete_sdk_progress_ratio"] = "12/12"
        public_sdk["p0_dependency_chain_promoted_for_claim_count"] = 4
        public_sdk["p0_dependency_chain_remaining_for_claim_count"] = 0
        public_sdk["p0_dependency_chain_total"] = 4
        public_sdk["p0_dependency_chain_progress_ratio"] = "4/4"
        fastest = public_sdk["fastest_next_sdk_unblock"]
        self.assertIsInstance(fastest, dict)
        fastest["current_route_blocker"] = "identity_public_contract_gate_missing"
        fastest["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]

        report = status_report.summarize(
            public_sdk=public_sdk,
            public_sdk_returncode=0,
            header_gate=self.header_gate_payload(),
            header_gate_returncode=0,
        )

        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["remaining_route_blockers"], ["approved_runtime_evidence_missing"])
        self.assertEqual(
            report["source_current_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["source_remaining_route_blockers"],
            ["identity_public_contract_gate_missing"],
        )
        self.assertEqual(
            report["source_overclaimed_route_flags"],
            ["current_route_blocker", "remaining_route_blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertEqual(report["complete_sdk_progress_ratio"], "0/12")
        self.assertEqual(report["p0_dependency_chain_progress_ratio"], "0/4")
        self.assertEqual(report["sdk_counts"]["promoted_for_claim_count"], 0)
        self.assertEqual(report["p0_counts"]["promoted_for_claim_count"], 0)
        self.assertIn("ready", report["source_overclaimed_readiness_flags"])
        self.assertIn("stable_claim_allowed", report["source_overclaimed_readiness_flags"])
        self.assertEqual(
            report["p0_counts"]["normalized_due_to"],
            ["approved_runtime_evidence_missing"],
        )


if __name__ == "__main__":
    unittest.main()
