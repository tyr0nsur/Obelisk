"""Tests for plan_obelisk_multi_surface_beta_capture.py."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "plan_obelisk_multi_surface_beta_capture.py"
BROAD_BETA_CAPTURE_WORKSHEET_FILE = "admin-commands-dino-tribe-buff-candidate-worksheet.json"
EXPECTED_SURFACES = {
    "player_principal_lifecycle",
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "dino_scalar",
    "tribe_scalar",
    "buff_status",
    "inventory_item_copied_signals",
    "inventory_custom_filter_array_boundary",
    "inventory_action_compact_intake",
    "item_return_only",
    "transfer_baccept",
    "transfer_scriptstruct",
    "mission_copied_bool",
}
BROAD_BETA_CAPTURE_SURFACES = [
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "dino_scalar",
    "tribe_scalar",
    "buff_status",
]
PARALLEL_BETA_CAPTURE_SURFACES = [
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "dino_scalar",
    "tribe_scalar",
    "buff_status",
    "inventory_item_copied_signals",
    "inventory_custom_filter_array_boundary",
    "inventory_action_compact_intake",
    "item_return_only",
    "transfer_baccept",
    "transfer_scriptstruct",
    "mission_copied_bool",
]
SINGLE_PLAYER_ROUTE_SURFACES = [
    "player_principal_lifecycle",
    *PARALLEL_BETA_CAPTURE_SURFACES,
]
SINGLE_PLAYER_ROUTE_DOMAINS = [
    "player_principal",
    "admin",
    "commands",
    "dino",
    "tribe",
    "buff",
    "inventory",
    "item",
    "transfer",
    "mission",
]
BETA_CAPTURE_INTERACTION_BOUNDARY_FALSE_FLAGS = {
    "beta_notices_count_as_approved_runtime_evidence",
    "beta_notices_count_as_runtime_evidence",
    "beta_notices_count_as_sdk_progress",
    "beta_notices_count_as_p0_progress",
    "button_clicks_count_as_approved_runtime_evidence",
    "button_clicks_count_as_runtime_evidence",
    "button_clicks_count_as_sdk_progress",
    "button_clicks_count_as_p0_progress",
    "public_reachability_counts_as_runtime_evidence",
    "public_reachability_counts_as_sdk_progress",
    "multi_surface_plan_counts_as_approved_runtime_evidence",
    "multi_surface_plan_counts_as_sdk_progress",
    "discord_or_beta_interactions_grant_public_sdk_readiness",
    "discord_or_beta_interactions_grant_stable_readiness",
    "discord_or_beta_interactions_authorize_live_actions",
    "discord_or_beta_interactions_approve_live_actions",
    "discord_or_beta_interactions_authorize_discord_send",
    "discord_or_beta_interactions_clear_runtime_evidence_blockers",
}
FALSE_FLAGS = {
    "authorizes_live_log_reads",
    "authorizes_live_operations",
    "authorizes_live_server_access",
    "authorizes_runtime_capture",
    "authorizes_runtime_observer",
    "authorizes_server_restart",
    "authorizes_server_start",
    "authorizes_server_stop",
    "authorizes_marker_or_env_changes",
    "authorizes_player_backed_window",
    "authorizes_discord_send",
    "authorizes_beta_session",
    "authorizes_evidence_window",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_as_p0_progress",
    "clears_approved_runtime_evidence_missing",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
    "v1_completion_ready",
    "plugin_hub_ready",
    "publication_ready",
    "readiness_claim_allowed",
    "downstream_unlock_allowed",
    "passive_capture_counts_as_evidence",
    "stale_artifact_counts_as_evidence",
    "stale_or_passive_alias_substitution_allowed",
    "replaces_player_principal_evidence",
    "replaces_player_principal_triplet",
    "substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_triplet",
    "side_lane_substitutes_for_player_principal_lifecycle_evidence",
    "player_principal_lifecycle_evidence_substitution_allowed",
    "approved_runtime_evidence_substitution_allowed",
    "primary_evidence_substitution_allowed",
    "side_lane_counts_toward_sdk",
    "side_lane_counts_toward_p0",
    "pack_authorizes_player_backed_window",
    "pack_authorizes_runtime_observer",
    "pack_authorizes_marker_or_env_change",
    "pack_authorizes_restart",
    "pack_authorizes_discord",
    "secrets_or_webhook_retention_allowed",
    "side_lane_collection_before_primary_route_active_allowed",
    "side_lane_collection_can_replace_player_principal_evidence",
    "side_lane_collection_counts_before_checker_acceptance",
} | BETA_CAPTURE_INTERACTION_BOUNDARY_FALSE_FLAGS


def run_plan(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--instance",
            "arkserver",
            "--map",
            "Ragnarok",
            *extra,
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def assert_beta_capture_interaction_boundary(
    testcase: unittest.TestCase,
    boundary: dict[str, Any],
) -> None:
    testcase.assertEqual(
        boundary["schema"],
        "obelisk.multi-surface-beta-capture-interaction-boundary.v1",
    )
    testcase.assertEqual(boundary["scope"], "multi_surface_beta_capture_coordination")
    testcase.assertEqual(
        boundary["single_operational_message_style"],
        "single_updated_embed_buttons_operational_message",
    )
    testcase.assertTrue(boundary["accepted_copied_sibling_set_required_before_runtime_claims"])
    testcase.assertTrue(boundary["accepted_copied_sibling_sets_required_for_runtime_evidence"])
    testcase.assertTrue(boundary["beta_notice_is_coordination_only"])
    testcase.assertTrue(boundary["button_clicks_are_coordination_only"])
    testcase.assertTrue(boundary["public_reachability_is_non_evidence"])
    testcase.assertTrue(boundary["multi_surface_capture_plan_is_candidate_only"])
    testcase.assertEqual(set(boundary["non_claim_flags"]), BETA_CAPTURE_INTERACTION_BOUNDARY_FALSE_FLAGS)
    for key in BETA_CAPTURE_INTERACTION_BOUNDARY_FALSE_FLAGS:
        with testcase.subTest(beta_capture_interaction_boundary=key):
            testcase.assertFalse(boundary[key])
            testcase.assertFalse(boundary["non_claim_flags"][key])


class MultiSurfaceBetaCapturePlanTests(unittest.TestCase):
    def test_json_plan_lists_all_candidate_surfaces_without_progress_claims(self) -> None:
        report = json.loads(run_plan("--json").stdout)

        self.assertEqual(report["schema"], "obelisk.multi-surface-beta-capture-plan.v1")
        self.assertEqual(report["status"], "candidate_capture_plan")
        self.assertEqual(report["target"], {"instance": "arkserver", "map": "Ragnarok"})
        assert_beta_capture_interaction_boundary(
            self,
            report["beta_capture_interaction_boundary"],
        )
        self.assertEqual(
            report["target_binding"],
            {
                "all_artifacts_must_match": True,
                "binding_id": "instance=arkserver|map=Ragnarok",
                "instance": "arkserver",
                "map": "Ragnarok",
                "mismatched_target_rejects_pack": True,
                "source": "operator_cli_plan_target",
            },
        )
        self.assertEqual(report["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(report["approved_runtime_window_binding"]["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(
            report["approved_runtime_window_binding"]["window_id_template"],
            "<approved-player-principal-lifecycle-window-id>",
        )
        self.assertTrue(
            report["approved_runtime_window_binding"]["same_window_as_player_principal_lifecycle"]
        )
        self.assertTrue(report["approved_runtime_window_binding"]["candidate_artifacts_must_match_window"])
        self.assertFalse(report["approved_runtime_window_binding"]["pack_authorizes_window"])
        self.assertFalse(report["approved_runtime_window_binding"]["window_substitution_allowed"])
        self.assertTrue(report["single_beta_session_intent"])
        self.assertIn("practical_beta_session_objectives", report)
        self.assertIn("side_lane_collection", report["practical_beta_session_objectives"])
        self.assertIn("same_approved_runtime_window", report["practical_beta_session_objectives"])
        self.assertTrue(report["artifact_intake_constraints"]["target_binding_must_match_pack_target"])
        self.assertTrue(report["artifact_intake_constraints"]["path_template_must_not_name_live_server_paths"])
        self.assertTrue(
            report["artifact_intake_constraints"][
                "candidate_artifact_intake_cannot_replace_primary_runtime_evidence"
            ]
        )
        self.assertTrue(
            report["artifact_intake_constraints"][
                "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence"
            ]
        )
        self.assertEqual(
            report["required_primary_evidence"]["strict_triplet"],
            "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
        )
        self.assertEqual({surface["id"] for surface in report["capture_surfaces"]}, EXPECTED_SURFACES)
        self.assertEqual(
            [surface["priority"] for surface in report["capture_surfaces"]],
            list(range(1, len(EXPECTED_SURFACES) + 1)),
        )
        broad_path = report["broad_beta_capture_pack_path"]
        self.assertEqual(broad_path["id"], "admin_commands_dino_tribe_buff_candidate_path")
        self.assertEqual(broad_path["status"], "status_only_candidate_capture_path")
        self.assertEqual(broad_path["path_status"], "status_only_candidate_non_evidence")
        self.assertEqual(broad_path["surface_ids"], BROAD_BETA_CAPTURE_SURFACES)
        self.assertEqual(
            broad_path["action_group_ids"],
            ["admin_and_command_routes", "world_state_scalar_candidates"],
        )
        self.assertEqual(broad_path["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(
            broad_path["approved_runtime_window_binding"],
            report["approved_runtime_window_binding"],
        )
        self.assertTrue(broad_path["status_only"])
        self.assertTrue(broad_path["candidate_only"])
        self.assertTrue(broad_path["non_evidence"])
        self.assertTrue(broad_path["requires_checker_acceptance"])
        self.assertTrue(broad_path["requires_player_principal_triplet"])
        self.assertFalse(broad_path["counts_as_runtime_evidence"])
        self.assertFalse(broad_path["counts_as_sdk_progress"])
        self.assertFalse(broad_path["runtime_ready"])
        self.assertFalse(broad_path["public_sdk_ready"])
        self.assertIn("does not authorize runtime capture", broad_path["non_claim"])
        self.assertEqual(
            [surface["id"] for surface in broad_path["surfaces"]],
            BROAD_BETA_CAPTURE_SURFACES,
        )
        worksheet_summary = broad_path["worksheet"]
        self.assertEqual(worksheet_summary["id"], "admin_commands_dino_tribe_buff_candidate_worksheet")
        self.assertEqual(worksheet_summary["schema"], "obelisk.multi-surface-beta-capture-broad-candidate-worksheet.v1")
        self.assertEqual(worksheet_summary["file"], BROAD_BETA_CAPTURE_WORKSHEET_FILE)
        self.assertEqual(worksheet_summary["surface_ids"], BROAD_BETA_CAPTURE_SURFACES)
        self.assertEqual(worksheet_summary["row_count"], len(BROAD_BETA_CAPTURE_SURFACES))
        self.assertTrue(worksheet_summary["source_metadata_required"])
        self.assertEqual(
            worksheet_summary["source_metadata"]["schema"],
            "obelisk.multi-surface-beta-capture-source-metadata.v1",
        )
        for key in (
            "candidate_only",
            "non_evidence",
            "same_approved_runtime_window_required",
            "redacted_metadata_only",
            "no_flood",
            "one_request_row_per_surface_per_approved_window",
        ):
            self.assertTrue(worksheet_summary[key], key)
        for key in (
            "source_present",
            "source_material_present",
            "counts_as_runtime_evidence",
            "counts_as_sdk_progress",
            "counts_as_p0_progress",
            "clears_approved_runtime_evidence_missing",
            "source_material_counts_as_evidence",
            "flood_capture_allowed",
            "unbounded_tester_requests_allowed",
            "discord_request_fanout_allowed",
        ):
            self.assertFalse(worksheet_summary[key], key)
        self.assertEqual(
            [row["surface_id"] for row in broad_path["worksheet_rows"]],
            BROAD_BETA_CAPTURE_SURFACES,
        )
        for row in broad_path["worksheet_rows"]:
            self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(row["observation_rows"], [])
            self.assertTrue(row["source_metadata_required"], row["surface_id"])
            self.assertEqual(
                row["source_metadata"]["schema"],
                "obelisk.multi-surface-beta-capture-source-metadata.v1",
            )
            self.assertFalse(row["source_metadata"]["source_ready"], row["surface_id"])
            self.assertFalse(row["source_metadata"]["source_material_counts_as_evidence"], row["surface_id"])
            self.assertTrue(row["candidate_only"], row["surface_id"])
            self.assertTrue(row["non_evidence"], row["surface_id"])
            self.assertFalse(row["counts_as_runtime_evidence"], row["surface_id"])
            self.assertFalse(row["counts_as_sdk_progress"], row["surface_id"])
            self.assertFalse(row["clears_approved_runtime_evidence_missing"], row["surface_id"])
            self.assertIn(
                "approved_window_id",
                {field["field_id"] for field in row["worksheet_fields"]},
            )
        self.assertEqual(
            {
                row["artifact_group"]: row["surface_ids"]
                for row in broad_path["shared_artifact_groups"]
            },
            {
                "commands": ["command_chat_response", "commands_replies"],
                "ufunction_snapshot_root": ["dino_scalar", "tribe_scalar", "buff_status"],
            },
        )
        parallel_matrix = report["parallel_beta_capture_side_lane_matrix"]
        self.assertEqual(
            parallel_matrix["id"],
            "admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates",
        )
        self.assertEqual(parallel_matrix["status"], "status_only_parallel_candidate_capture_matrix")
        self.assertEqual(parallel_matrix["matrix_status"], "status_only_candidate_non_evidence")
        self.assertEqual(parallel_matrix["surface_ids"], PARALLEL_BETA_CAPTURE_SURFACES)
        self.assertEqual(
            parallel_matrix["action_group_ids"],
            [
                "admin_and_command_routes",
                "world_state_scalar_candidates",
                "inventory_item_candidates",
                "transfer_candidates",
                "mission_candidates",
            ],
        )
        self.assertEqual(parallel_matrix["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(
            parallel_matrix["approved_runtime_window_binding"],
            report["approved_runtime_window_binding"],
        )
        self.assertTrue(parallel_matrix["status_only"])
        self.assertTrue(parallel_matrix["optional_parallel_candidate_observations"])
        self.assertTrue(parallel_matrix["same_approved_runtime_window_required"])
        self.assertTrue(parallel_matrix["exact_target_binding_required"])
        self.assertTrue(parallel_matrix["requires_player_principal_triplet"])
        self.assertFalse(parallel_matrix["counts_as_runtime_evidence"])
        self.assertFalse(parallel_matrix["counts_as_sdk_progress"])
        self.assertFalse(parallel_matrix["substitutes_for_player_principal_lifecycle_evidence"])
        self.assertIn("never replaces the required player-principal triplet", parallel_matrix["non_claim"])
        self.assertEqual(
            [row["domain"] for row in parallel_matrix["domain_rows"]],
            [
                "admin",
                "commands",
                "dino",
                "tribe",
                "buff",
                "inventory",
                "item",
                "transfer",
                "mission",
            ],
        )
        self.assertEqual(
            next(row for row in parallel_matrix["domain_rows"] if row["domain"] == "item")[
                "surface_ids"
            ],
            ["item_return_only"],
        )
        self.assertNotIn("structure", [row["domain"] for row in parallel_matrix["domain_rows"]])
        self.assertIn("mission", [row["domain"] for row in parallel_matrix["domain_rows"]])
        self.assertEqual(
            [row["id"] for row in parallel_matrix["surface_rows"]],
            PARALLEL_BETA_CAPTURE_SURFACES,
        )
        self.assertNotIn("player_principal_lifecycle", parallel_matrix["surface_ids"])
        for row in parallel_matrix["domain_rows"] + parallel_matrix["action_group_rows"]:
            self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok", row)
            self.assertEqual(
                row["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                row,
            )
            self.assertTrue(row["exact_approved_runtime_window_required"], row)
            self.assertTrue(row["exact_target_binding_required"], row)
            self.assertTrue(row["no_restart_required"], row)
            self.assertTrue(row["tester_actions_do_not_require_restart"], row)
            self.assertFalse(row["restart_required"], row)
            self.assertFalse(row["server_restart_required"], row)
            self.assertFalse(row["counts_as_p0_progress"], row)
            self.assertFalse(row["primary_evidence_substitution_allowed"], row)
            self.assertIsInstance(row["operator_next_action"], str, row)
            self.assertTrue(row["operator_next_action"], row)
            self.assertEqual(row["operator_next_action"], row["lead_next_action"], row)
            self.assertIsInstance(row["tester_brief"], str, row)
            self.assertTrue(row["tester_brief"], row)
        for row in parallel_matrix["surface_rows"]:
            self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok", row["id"])
            self.assertEqual(
                row["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                row["id"],
            )
            self.assertTrue(row["side_lane"], row["id"])
            self.assertTrue(row["same_approved_runtime_window_required"], row["id"])
            self.assertTrue(row["exact_approved_runtime_window_required"], row["id"])
            self.assertTrue(row["exact_target_binding_required"], row["id"])
            self.assertTrue(row["no_restart_required"], row["id"])
            self.assertTrue(row["tester_actions_do_not_require_restart"], row["id"])
            self.assertFalse(row["restart_required"], row["id"])
            self.assertFalse(row["server_restart_required"], row["id"])
            self.assertFalse(row["counts_as_runtime_evidence"], row["id"])
            self.assertFalse(row["counts_as_p0_progress"], row["id"])
            self.assertFalse(row["primary_evidence_substitution_allowed"], row["id"])
            self.assertEqual(row["operator_next_action"], row["lead_next_action"], row["id"])
            self.assertTrue(row["tester_brief"], row["id"])
        sequence = report["single_player_parallel_capture_sequence"]
        self.assertEqual(sequence["id"], "single_player_parallel_side_lane_capture_sequence")
        self.assertEqual(sequence["status"], "status_only_parallel_candidate_sequence")
        self.assertEqual(sequence["sequence_status"], "status_only_candidate_non_evidence")
        self.assertEqual(sequence["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertEqual(sequence["approved_runtime_window_binding"], report["approved_runtime_window_binding"])
        self.assertEqual(sequence["surface_ids"], SINGLE_PLAYER_ROUTE_SURFACES)
        self.assertEqual(sequence["single_player_route_surface_ids"], SINGLE_PLAYER_ROUTE_SURFACES)
        self.assertEqual(sequence["side_lane_surface_ids"], PARALLEL_BETA_CAPTURE_SURFACES)
        self.assertEqual(sequence["candidate_domain_ids"], SINGLE_PLAYER_ROUTE_DOMAINS)
        self.assertEqual(sequence["excluded_surface_ids"], [])
        self.assertTrue(sequence["single_player_route"])
        self.assertTrue(sequence["single_player_route_constraints"]["primary_player_principal_phase_runs_first"])
        self.assertTrue(
            sequence["single_player_route_constraints"][
                "primary_player_principal_route_must_be_active_before_side_lanes"
            ]
        )
        self.assertTrue(
            sequence["single_player_route_constraints"][
                "side_lane_collection_requires_active_player_principal_route"
            ]
        )
        self.assertTrue(sequence["single_player_route_constraints"]["redacted_metadata_only"])
        self.assertTrue(sequence["single_player_route_constraints"]["no_discord_required"])
        self.assertFalse(sequence["single_player_route_constraints"]["raw_player_text_retention_allowed"])
        self.assertFalse(sequence["single_player_route_constraints"]["secrets_or_webhook_retention_allowed"])
        self.assertFalse(
            sequence["single_player_route_constraints"][
                "side_lane_collection_before_primary_route_active_allowed"
            ]
        )
        self.assertFalse(sequence["single_player_route_constraints"]["pack_authorizes_discord"])
        self.assertFalse(sequence["single_player_route_constraints"]["authorizes_live_log_reads"])
        self.assertFalse(sequence["single_player_route_constraints"]["counts_as_sdk_progress"])
        self.assertFalse(sequence["single_player_route_constraints"]["clears_approved_runtime_evidence_missing"])
        self.assertFalse(sequence["pack_authorizes_discord"])
        self.assertFalse(sequence["authorizes_discord_send"])
        self.assertFalse(sequence["authorizes_live_log_reads"])
        self.assertFalse(sequence["side_lane_collection_can_replace_player_principal_evidence"])
        self.assertEqual(
            sequence["action_group_ids"],
            [
                "primary_player_principal_gate",
                "admin_and_command_routes",
                "world_state_scalar_candidates",
                "inventory_item_candidates",
                "transfer_candidates",
                "mission_candidates",
            ],
        )
        self.assertEqual(
            [phase["phase_id"] for phase in sequence["phases"]],
            sequence["action_group_ids"],
        )
        self.assertTrue(sequence["no_restart_required"])
        self.assertFalse(sequence["restart_required"])
        self.assertFalse(sequence["raw_player_text_retention_allowed"])
        self.assertFalse(sequence["secrets_or_webhook_retention_allowed"])
        self.assertFalse(sequence["clears_approved_runtime_evidence_missing"])
        self.assertIn("no-Discord", sequence["non_claim"])
        self.assertEqual(sequence["text_privacy_boundary"], report["text_privacy_boundary"])
        self.assertIn("raw_player_text", sequence["text_privacy_boundary"]["must_redact"])
        expected_phase_domains = {
            "primary_player_principal_gate": ["player_principal"],
            "admin_and_command_routes": ["admin", "commands"],
            "world_state_scalar_candidates": ["dino", "tribe", "buff"],
            "inventory_item_candidates": ["inventory", "item"],
            "transfer_candidates": ["transfer"],
            "mission_candidates": ["mission"],
        }
        for phase in sequence["phases"]:
            self.assertEqual(phase["target_binding_id"], "instance=arkserver|map=Ragnarok", phase["phase_id"])
            self.assertTrue(phase["operator_action_metadata_explicit"], phase["phase_id"])
            self.assertTrue(phase["single_player_route"], phase["phase_id"])
            self.assertEqual(phase["phase_domain_ids"], expected_phase_domains[phase["phase_id"]], phase["phase_id"])
            self.assertEqual(
                phase["phase_role"],
                (
                    "primary_player_principal_lifecycle"
                    if phase["phase_id"] == "primary_player_principal_gate"
                    else "optional_parallel_candidate_observations"
                ),
                phase["phase_id"],
            )
            self.assertTrue(phase["no_restart_required"], phase["phase_id"])
            self.assertFalse(phase["raw_player_text_retention_allowed"], phase["phase_id"])
            self.assertFalse(phase["secrets_or_webhook_retention_allowed"], phase["phase_id"])
            self.assertFalse(phase["pack_authorizes_discord"], phase["phase_id"])
            self.assertFalse(phase["authorizes_live_log_reads"], phase["phase_id"])
            self.assertFalse(phase["side_lane_counts_toward_sdk"], phase["phase_id"])
            self.assertTrue(phase["single_player_route_constraints"]["redacted_metadata_only"], phase["phase_id"])
            self.assertTrue(
                phase["single_player_route_constraints"][
                    "side_lane_collection_requires_active_player_principal_route"
                ],
                phase["phase_id"],
            )
            self.assertFalse(
                phase["single_player_route_constraints"]["secrets_or_webhook_retention_allowed"],
                phase["phase_id"],
            )
            self.assertFalse(
                phase["single_player_route_constraints"][
                    "side_lane_collection_before_primary_route_active_allowed"
                ],
                phase["phase_id"],
            )
            self.assertFalse(
                phase["single_player_route_constraints"]["clears_approved_runtime_evidence_missing"],
                phase["phase_id"],
            )
            self.assertFalse(phase["counts_as_sdk_progress"], phase["phase_id"])
            self.assertTrue(phase["checker_commands"], phase["phase_id"])
            self.assertTrue(phase["readiness_checker_support"], phase["phase_id"])
            for command_row in phase["checker_commands"]:
                self.assertIn("resolved_checker_command_template", command_row, phase["phase_id"])
                self.assertIn("target_bound_checker_command", command_row, phase["phase_id"])
                self.assertEqual(
                    command_row["target_bound_checker_command"]["target_binding_id"],
                    "instance=arkserver|map=Ragnarok",
                    phase["phase_id"],
                )
                self.assertFalse(
                    command_row["target_bound_checker_command"][
                        "clears_approved_runtime_evidence_missing"
                    ],
                    phase["phase_id"],
                )
                self.assertFalse(
                    command_row["target_bound_checker_command"][
                        "secrets_or_webhook_retention_allowed"
                    ],
                    phase["phase_id"],
                )
        command_matrix = report["target_bound_checker_command_matrix"]
        self.assertEqual(command_matrix["id"], "target_bound_offline_checker_command_matrix")
        self.assertEqual(command_matrix["status"], "offline_command_templates_candidate_only")
        self.assertEqual(command_matrix["row_count"], len(EXPECTED_SURFACES))
        self.assertEqual(command_matrix["target_binding_id"], "instance=arkserver|map=Ragnarok")
        self.assertTrue(command_matrix["all_rows_target_bound"])
        self.assertTrue(command_matrix["all_rows_require_redacted_artifact_copy"])
        self.assertFalse(command_matrix["raw_player_text_retention_allowed"])
        self.assertFalse(command_matrix["secrets_or_webhook_retention_allowed"])
        self.assertFalse(command_matrix["pack_authorizes_restart"])
        self.assertFalse(command_matrix["pack_authorizes_discord"])
        self.assertFalse(command_matrix["clears_approved_runtime_evidence_missing"])
        command_by_id = {row["surface_id"]: row for row in command_matrix["rows"]}
        self.assertEqual(
            command_by_id["transfer_baccept"]["resolved_checker_command_template"],
            [
                "python3",
                "scripts/check_transfer_baccept_readiness.py",
                "--root",
                "candidate-artifacts/transfer_baccept/offline-transfer-baccept-pack-root",
                "--manifest",
                "candidate-artifacts/transfer_baccept/offline-transfer-baccept-policy-slice.json",
                "--expected-manifest-sha256",
                "<read-text:candidate-artifacts/transfer_baccept/offline-transfer-baccept-policy-slice.sha256>",
                "--json",
            ],
        )
        self.assertEqual(
            command_by_id["inventory_item_copied_signals"]["resolved_checker_command_template"],
            command_by_id["inventory_item_copied_signals"]["command"],
        )
        self.assertTrue(report["server_policy"]["keep_servers_running_when_practical"])
        self.assertEqual(report["server_policy"]["max_ark_servers_running"], 2)
        self.assertTrue(report["server_policy"]["no_restart_from_pack"])
        self.assertFalse(report["server_policy"]["pack_authorizes_restart"])
        self.assertFalse(report["server_policy"]["pack_authorizes_live_log_reads"])
        self.assertTrue(report["server_policy"]["maintenance_restarts_out_of_scope"])
        self.assertEqual(report["candidate_only_metadata"]["classification"], "candidate_only_non_evidence")
        self.assertTrue(report["candidate_only_metadata"]["non_evidence"])
        self.assertFalse(report["candidate_only_metadata"]["counts_as_runtime_evidence"])
        self.assertFalse(report["candidate_only_metadata"]["downstream_unlock_allowed"])
        self.assertFalse(report["candidate_only_metadata"]["passive_capture_counts_as_evidence"])
        self.assertEqual(
            report["player_principal_window_composition"],
            {
                "all_artifacts_require_exact_target_binding": True,
                "composes_with_window": "player_principal_lifecycle",
                "counts_as_p0_progress": False,
                "counts_as_sdk_progress": False,
                "primary_player_principal_evidence_remains_required": True,
                "primary_strict_triplet": (
                    "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout"
                ),
                "primary_surface_id": "player_principal_lifecycle",
                "side_surface_role": "optional_parallel_candidate_observations",
                "side_surfaces_non_evidence_until_own_checker_acceptance": True,
                "side_surfaces_optional": True,
                "side_surfaces_parallel_candidate_only": True,
                "side_surfaces_require_own_checker_acceptance": True,
                "substitution_allowed": False,
            },
        )
        self.assertIn("player_principal_window_composition", report["practical_beta_session_objectives"])
        self.assertEqual(
            report["parallel_capture_boundary"],
            {
                "candidate_surface_claims_require_checker_acceptance": True,
                "pack_authorizes_discord": False,
                "pack_authorizes_marker_or_env_change": False,
                "pack_authorizes_player_backed_window": False,
                "pack_authorizes_restart": False,
                "pack_authorizes_runtime_observer": False,
                "parallel_with_player_principal_lifecycle_window_planned": True,
                "separate_player_backed_window_approval_required": True,
                "side_lane_collection_can_replace_player_principal_evidence": False,
                "side_lane_collection_counts_before_checker_acceptance": False,
                "side_surfaces_grouped_as_optional_parallel_candidate_observations": True,
                "side_surfaces_non_evidence_until_own_checker_acceptance": True,
                "target_binding_required_for_all_artifacts": True,
            },
        )
        grouped_surface_ids = [
            surface_id
            for group in report["next_action_groups"]
            for surface_id in group["surface_ids"]
        ]
        self.assertEqual(set(grouped_surface_ids), EXPECTED_SURFACES)
        self.assertEqual(len(grouped_surface_ids), len(EXPECTED_SURFACES))
        self.assertEqual(
            next(group for group in report["next_action_groups"] if group["id"] == "inventory_item_candidates")[
                "surface_ids"
            ],
            [
                "inventory_item_copied_signals",
                "inventory_custom_filter_array_boundary",
                "inventory_action_compact_intake",
                "item_return_only",
            ],
        )
        for group in report["next_action_groups"]:
            self.assertTrue(group["candidate_only"], group["id"])
            self.assertTrue(group["non_evidence"], group["id"])
            self.assertEqual(
                group["non_substitution_flags"]["side_lane_collection_can_replace_player_principal_evidence"],
                False,
                group["id"],
            )
            self.assertIn("beta_session_objective", group, group["id"])
            self.assertFalse(group["counts_as_runtime_evidence"], group["id"])
            self.assertFalse(group["counts_as_sdk_progress"], group["id"])
            self.assertFalse(group["downstream_unlock_allowed"], group["id"])
            self.assertEqual(group["parallel_capture_boundary"], report["parallel_capture_boundary"], group["id"])
            self.assertEqual(
                group["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                group["id"],
            )
            self.assertEqual(
                group["player_principal_window_composition"],
                report["player_principal_window_composition"],
                group["id"],
            )
            self.assertEqual(
                group["operator_tester_action_metadata"]["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                group["id"],
            )
            self.assertTrue(
                group["operator_tester_action_metadata"]["same_approved_runtime_window_required"],
                group["id"],
            )
            self.assertFalse(group["operator_tester_action_metadata"]["substitution_allowed"], group["id"])
            self.assertFalse(group["operator_tester_action_metadata"]["counts_as_sdk_progress"], group["id"])
            expected_optional_group = group["id"] != "primary_player_principal_gate"
            self.assertEqual(group["optional_parallel_candidate_observations"], expected_optional_group, group["id"])
            self.assertEqual(
                group["composition_role"],
                (
                    "optional_parallel_candidate_observations"
                    if expected_optional_group
                    else "primary_player_principal_lifecycle_window"
                ),
                group["id"],
            )
        for surface in report["capture_surfaces"]:
            self.assertTrue(surface["candidate_capture_only"], surface["id"])
            self.assertEqual(surface["candidate_only_metadata"], report["candidate_only_metadata"], surface["id"])
            self.assertEqual(surface["parallel_capture_boundary"], report["parallel_capture_boundary"], surface["id"])
            self.assertEqual(
                surface["player_principal_window_composition"],
                report["player_principal_window_composition"],
                surface["id"],
            )
            self.assertEqual(surface["target_binding"]["instance"], "arkserver", surface["id"])
            self.assertEqual(surface["target_binding"]["map"], "Ragnarok", surface["id"])
            self.assertEqual(surface["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
            self.assertEqual(surface["target_binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
            self.assertTrue(surface["target_binding"]["mismatched_target_rejects_pack"], surface["id"])
            self.assertEqual(
                surface["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                surface["id"],
            )
            self.assertIsInstance(surface["tester_action"], str, surface["id"])
            self.assertTrue(surface["tester_action"], surface["id"])
            self.assertEqual(
                surface["operator_tester_action_metadata"]["approved_runtime_window_binding"],
                report["approved_runtime_window_binding"],
                surface["id"],
            )
            self.assertEqual(
                surface["operator_tester_action_metadata"]["tester_action"],
                surface["tester_action"],
                surface["id"],
            )
            self.assertTrue(
                surface["operator_tester_action_metadata"]["same_approved_runtime_window_required"],
                surface["id"],
            )
            self.assertFalse(
                surface["operator_tester_action_metadata"]["counts_as_p0_progress"],
                surface["id"],
            )
            self.assertFalse(
                surface["operator_tester_action_metadata"]["secrets_or_webhook_retention_allowed"],
                surface["id"],
            )
            self.assertEqual(
                surface["non_substitution_flags"]["substitutes_for_player_principal_lifecycle_evidence"],
                False,
                surface["id"],
            )
            self.assertTrue(surface["requires_checker_acceptance"], surface["id"])
            self.assertTrue(surface["blocked_by_player_principal_evidence"], surface["id"])
            self.assertTrue(surface["requires_player_principal_triplet"], surface["id"])
            self.assertTrue(surface["checker_inputs_satisfied_by_artifacts"], surface["id"])
            self.assertEqual(surface["candidate_classification"], "candidate_only_non_counting")
            self.assertEqual(
                surface["post_capture_checker_command"],
                ["python3", surface["checker"], *surface["checker_args"]],
            )
            self.assertEqual(surface["resolved_checker_command_status"], "offline_command_templates_candidate_only")
            self.assertEqual(
                surface["target_bound_checker_command"]["resolved_checker_command_template"],
                surface["resolved_checker_command_template"],
                surface["id"],
            )
            self.assertEqual(
                surface["target_bound_checker_command"]["target_binding_id"],
                "instance=arkserver|map=Ragnarok",
                surface["id"],
            )
            self.assertFalse(
                surface["target_bound_checker_command"]["raw_player_text_retention_allowed"],
                surface["id"],
            )
            self.assertFalse(
                surface["target_bound_checker_command"]["secrets_or_webhook_retention_allowed"],
                surface["id"],
            )
            self.assertFalse(
                surface["target_bound_checker_command"]["pack_authorizes_restart"],
                surface["id"],
            )
            for binding in surface["checker_command_bindings"]:
                self.assertEqual(binding["target_binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
                self.assertTrue(binding["path_template"].startswith("candidate-artifacts/"), surface["id"])
                self.assertFalse(binding["clears_approved_runtime_evidence_missing"], surface["id"])
            checker_placeholders = {
                part
                for part in surface["post_capture_checker_command"]
                if isinstance(part, str) and part.startswith("<") and part.endswith(">")
            }
            required_inputs = {
                row["checker_input"]
                for row in surface["required_checker_artifacts"]
            }
            self.assertEqual(required_inputs, checker_placeholders, surface["id"])
            for row in surface["required_checker_artifacts"]:
                self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
                self.assertEqual(row["target_binding"], surface["target_binding"], surface["id"])
                self.assertTrue(row["target_binding"]["mismatched_target_rejects_pack"], surface["id"])
            self.assertFalse(surface["replaces_player_principal_triplet"], surface["id"])
            self.assertFalse(surface["substitutes_for_player_principal_lifecycle_evidence"], surface["id"])
            self.assertFalse(surface["substitutes_for_player_principal_lifecycle_triplet"], surface["id"])
            self.assertFalse(surface["player_principal_lifecycle_evidence_substitution_allowed"], surface["id"])
            self.assertFalse(surface["approved_runtime_evidence_substitution_allowed"], surface["id"])
            self.assertFalse(surface["primary_evidence_substitution_allowed"], surface["id"])
            self.assertFalse(surface["approved_runtime_evidence_present"], surface["id"])
            self.assertFalse(surface["approved_runtime_evidence_ready"], surface["id"])
            self.assertEqual(surface["current_route_blocker"], "approved_runtime_evidence_missing")
            self.assertEqual(
                surface["required_runtime_evidence"],
                "approved_runtime_principal_lifecycle_evidence_bundle",
            )
            self.assertIn("checker", surface)
        for surface in report["capture_surfaces"]:
            expected_side_lane = surface["id"] != "player_principal_lifecycle"
            self.assertEqual(surface["side_lane"], expected_side_lane, surface["id"])
            self.assertEqual(surface["side_lane_non_counting"], expected_side_lane, surface["id"])
            self.assertEqual(surface["optional_parallel_candidate_observation"], expected_side_lane, surface["id"])
            self.assertEqual(
                surface["parallel_with_player_principal_lifecycle_window"],
                expected_side_lane,
                surface["id"],
            )
            self.assertEqual(
                surface["composition_role"],
                (
                    "optional_parallel_candidate_observation"
                    if expected_side_lane
                    else "primary_player_principal_lifecycle_window"
                ),
                surface["id"],
            )
            for artifact in surface["capture_artifacts"]:
                self.assertEqual(artifact["target_binding"]["instance"], "arkserver", artifact["id"])
                self.assertEqual(artifact["target_binding"]["map"], "Ragnarok", artifact["id"])
                self.assertEqual(artifact["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok", artifact["id"])
                self.assertTrue(artifact["target_binding"]["mismatched_target_rejects_pack"], artifact["id"])
                self.assertEqual(
                    artifact["approved_runtime_window_binding"],
                    report["approved_runtime_window_binding"],
                    artifact["id"],
                )
                self.assertFalse(
                    artifact["non_substitution_flags"]["side_lane_collection_counts_before_checker_acceptance"],
                    artifact["id"],
                )
                self.assertTrue(artifact["artifact_intake_constraints"]["path_template_only"], artifact["id"])
                self.assertTrue(
                    artifact["artifact_intake_constraints"]["source_material_must_be_copied_to_offline_workspace"],
                    artifact["id"],
                )
                self.assertTrue(artifact["redaction_policy"]["required"], artifact["id"])
                self.assertIn("webhook_urls", artifact["redaction_policy"]["must_redact"], artifact["id"])
                self.assertEqual(artifact["candidate_only_metadata"], report["candidate_only_metadata"], artifact["id"])
                self.assertEqual(artifact["parallel_capture_boundary"], report["parallel_capture_boundary"], artifact["id"])
                self.assertTrue(artifact["path_template"].startswith("candidate-artifacts/"), artifact["id"])
                self.assertNotIn("/servidor/ark", artifact["path_template"], artifact["id"])

        for item in iter_dicts(report):
            for flag in FALSE_FLAGS:
                if flag in item:
                    self.assertFalse(item[flag], f"{flag} at {item}")
        self.assertFalse(report["non_claim_flags"]["counts_as_approved_runtime_evidence"])
        self.assertFalse(report["non_claim_flags"]["counts_as_sdk_progress"])

    def test_human_output_is_candidate_only_and_names_key_surfaces(self) -> None:
        output = run_plan().stdout

        self.assertIn("multi_surface_beta_capture_plan=candidate_only", output)
        self.assertIn("target=arkserver/Ragnarok", output)
        self.assertIn("counts_as_approved_runtime_evidence=false", output)
        self.assertIn("public_sdk_ready=false", output)
        self.assertIn("beta_interactions_approve_live_actions=false", output)
        self.assertIn("beta_interactions_count_as_sdk_progress=false", output)
        self.assertIn("beta_interactions_grant_public_sdk_readiness=false", output)
        self.assertIn("beta_interactions_grant_stable_readiness=false", output)
        self.assertIn("permissions_admin", output)
        self.assertIn("command_chat_response", output)
        self.assertIn("dino_scalar", output)
        self.assertIn("inventory_custom_filter_array_boundary", output)
        self.assertIn("inventory_action_compact_intake", output)
        self.assertIn("item_return_only", output)
        self.assertNotIn("structure_census", output)
        self.assertIn("mission_copied_bool", output)
        self.assertIn("next_action_groups:", output)
        self.assertIn("broad_beta_capture_pack_path=admin_commands_dino_tribe_buff_candidate_path", output)
        self.assertIn(
            "broad_beta_capture_surfaces=permissions_admin,command_chat_response,commands_replies,dino_scalar,tribe_scalar,buff_status",
            output,
        )
        self.assertIn("broad_beta_capture_status=status_only_candidate_non_evidence", output)
        self.assertIn(
            "parallel_beta_capture_matrix=admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates",
            output,
        )
        self.assertIn(
            "parallel_beta_capture_surfaces=permissions_admin,command_chat_response,commands_replies,dino_scalar,tribe_scalar,buff_status,inventory_item_copied_signals,inventory_custom_filter_array_boundary,inventory_action_compact_intake,item_return_only,transfer_baccept,transfer_scriptstruct,mission_copied_bool",
            output,
        )
        self.assertIn("parallel_beta_capture_status=status_only_candidate_non_evidence", output)
        self.assertIn(
            "single_player_parallel_capture_sequence=single_player_parallel_side_lane_capture_sequence",
            output,
        )
        self.assertIn("single_player_parallel_capture_status=status_only_candidate_non_evidence", output)
        self.assertIn(
            "single_player_parallel_capture_surfaces=player_principal_lifecycle,permissions_admin,command_chat_response,commands_replies,dino_scalar,tribe_scalar,buff_status,inventory_item_copied_signals,inventory_custom_filter_array_boundary,inventory_action_compact_intake,item_return_only,transfer_baccept,transfer_scriptstruct,mission_copied_bool",
            output,
        )
        self.assertIn(
            "single_player_parallel_capture_domains=player_principal,admin,commands,dino,tribe,buff,inventory,item,transfer,mission",
            output,
        )
        self.assertIn("single_player_route_excluded_surfaces=none", output)
        self.assertIn("target_bound_checker_command_matrix=target_bound_offline_checker_command_matrix", output)
        self.assertIn("target_bound_checker_command_matrix_status=offline_command_templates_candidate_only", output)
        self.assertIn("raw_player_text_retention_allowed=false", output)
        self.assertIn("secrets_or_webhook_retention_allowed=false", output)
        self.assertIn("single_player_route_redacted_metadata_only=true", output)
        self.assertIn("single_player_route_no_restart=true", output)
        self.assertIn("single_player_route_no_discord=true", output)
        self.assertIn("single_player_route_clears_approved_runtime_evidence_missing=false", output)
        self.assertIn("inventory_item_candidates", output)
        self.assertIn("parallel_with_player_principal_lifecycle_window_planned=true", output)
        self.assertIn("side_surfaces_grouped_as_optional_parallel_candidate_observations=true", output)
        self.assertIn("side_surfaces_non_evidence_until_own_checker_acceptance=true", output)
        self.assertIn("same_approved_runtime_window_required=true", output)
        self.assertIn("pack_authorizes_player_backed_window=false", output)
        self.assertIn("side_lane_collection_can_replace_player_principal_evidence=false", output)
        self.assertIn("tester_brief=", output)
        self.assertIn("tester_action=", output)
        self.assertIn("transfer_baccept", output)
        self.assertIn("transfer_scriptstruct", output)
        self.assertIn("current_route_blocker=approved_runtime_evidence_missing", output)
        self.assertIn(
            "next_required_artifact=approved_runtime_principal_lifecycle_evidence_bundle",
            output,
        )

    def test_checker_commands_use_surface_specific_offline_templates(self) -> None:
        report = json.loads(run_plan("--json").stdout)
        by_id = {surface["id"]: surface for surface in report["capture_surfaces"]}

        self.assertEqual(
            by_id["player_principal_lifecycle"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                "<approved-runtime-principal-lifecycle-evidence-manifest.json>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["inventory_custom_filter_array_boundary"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_inventory_custom_filter_array_boundary.py",
                "--snapshot",
                "<offline-inventory-custom-filter-array-boundary-snapshot.json>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["transfer_baccept"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_transfer_baccept_readiness.py",
                "--root",
                "<offline-transfer-baccept-pack-root>",
                "--manifest",
                "<offline-transfer-baccept-policy-slice.json>",
                "--expected-manifest-sha256",
                "<offline-transfer-baccept-policy-slice-sha256>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["transfer_baccept"]["resolved_checker_command_template"],
            [
                "python3",
                "scripts/check_transfer_baccept_readiness.py",
                "--root",
                "candidate-artifacts/transfer_baccept/offline-transfer-baccept-pack-root",
                "--manifest",
                "candidate-artifacts/transfer_baccept/offline-transfer-baccept-policy-slice.json",
                "--expected-manifest-sha256",
                "<read-text:candidate-artifacts/transfer_baccept/offline-transfer-baccept-policy-slice.sha256>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["transfer_baccept"]["checker_command_bindings"][-1]["argument_resolution"],
            "read_scalar_text_from_path_template",
        )
        self.assertEqual(
            by_id["item_return_only"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_item_return_only_readiness.py",
                "--root",
                "<offline-item-return-only-pack-root>",
                "--manifest",
                "<offline-item-return-only-policy-slice.json>",
                "--expected-manifest-sha256",
                "<offline-item-return-only-policy-slice-sha256>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["inventory_action_compact_intake"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_inventory_action_redacted_observer_gate.py",
                "--snapshot-root",
                "<offline-inventory-action-compact-snapshot-root>",
                "--public-sdk-surfaces",
                "<offline-inventory-action-public-sdk-surfaces.json>",
                "--public-gameplay-events",
                "<offline-inventory-action-public-gameplay-events.json>",
                "--decision-manifest",
                "<offline-inventory-action-decisions.json>",
                "--gate-enabled",
                "--observer-profile",
                "observer-debug",
                "--marker",
                "allow-observer-debug-window",
                "--marker",
                "allow-experimental-observers",
                "--marker",
                "enable-inventory-action-redacted-observer",
                "--marker",
                "enable-process-event-hook",
                "--marker",
                "disable-plugins",
                "--ark-binary-sha256",
                "<supported-ark-binary-sha256>",
                "--fname-index",
                "<inventory-action-target-fname-index>",
                "--dispatch-budget",
                "0",
                "--observation-budget",
                "<bounded-observation-budget-1-to-10>",
                "--json",
            ],
        )
        self.assertEqual(
            {
                row["checker_input"]
                for row in by_id["inventory_action_compact_intake"]["required_checker_artifacts"]
            },
            {
                "<offline-inventory-action-compact-snapshot-root>",
                "<offline-inventory-action-public-sdk-surfaces.json>",
                "<offline-inventory-action-public-gameplay-events.json>",
                "<offline-inventory-action-decisions.json>",
                "<supported-ark-binary-sha256>",
                "<inventory-action-target-fname-index>",
                "<bounded-observation-budget-1-to-10>",
            },
        )
        self.assertEqual(
            by_id["transfer_scriptstruct"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_transfer_scriptstruct_readiness.py",
                "--snapshot-root",
                "<offline-scriptstruct-snapshot-root>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["mission_copied_bool"]["post_capture_checker_command"],
            [
                "python3",
                "scripts/check_mission_copied_bool_readiness.py",
                "--root",
                "<offline-mission-copied-bool-pack-root>",
                "--manifest",
                "<offline-mission-copied-bool-policy-slice.json>",
                "--expected-manifest-sha256",
                "<offline-mission-copied-bool-policy-slice-sha256>",
                "--json",
            ],
        )
        self.assertEqual(
            by_id["mission_copied_bool"]["resolved_checker_command_template"],
            [
                "python3",
                "scripts/check_mission_copied_bool_readiness.py",
                "--root",
                "candidate-artifacts/mission_copied_bool/offline-mission-copied-bool-pack-root",
                "--manifest",
                "candidate-artifacts/mission_copied_bool/offline-mission-copied-bool-policy-slice.json",
                "--expected-manifest-sha256",
                "<read-text:candidate-artifacts/mission_copied_bool/offline-mission-copied-bool-policy-slice.sha256>",
                "--json",
            ],
        )
        self.assertNotIn("structure_census", by_id)
        self.assertIn("mission_copied_bool", by_id)

    def test_rejects_unsafe_target_tokens(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--instance",
                "../arkserver",
                "--map",
                "Ragnarok",
                "--json",
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--instance contains unsafe characters", result.stderr)


if __name__ == "__main__":
    unittest.main()
