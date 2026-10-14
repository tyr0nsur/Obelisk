"""Tests for prepare_obelisk_multi_surface_beta_capture_pack.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "prepare_obelisk_multi_surface_beta_capture_pack.py"
READINESS_SCRIPT = SCRIPT_DIR / "check_permissions_admin_public_readiness.py"
RUN_ID = "test-multi-surface-pack"
BROAD_BETA_CAPTURE_WORKSHEET_FILE = "admin-commands-dino-tribe-buff-candidate-worksheet.json"
SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE = "simultaneous-side-lane-candidate-worksheet.json"
SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE = "single-player-full-sequence-candidate-worksheet.json"
EXPECTED_ARTIFACTS = {
    "README.md",
    BROAD_BETA_CAPTURE_WORKSHEET_FILE,
    SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
    SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
    "candidate-artifact-intake.json",
    "checker-command-matrix.json",
    "multi-surface-capture-plan.json",
    "non-claim-manifest.json",
    "operator-runbook.md",
    "permissions-admin-beta-capture-candidates.json",
}
EXPECTED_FILES = EXPECTED_ARTIFACTS | {"manifest.json"}
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


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def run_pack(output_root: Path, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--instance",
            "arkserver",
            "--map",
            "Ragnarok",
            "--output-root",
            str(output_root),
            "--run-id",
            RUN_ID,
            *extra,
        ],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


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


class PrepareMultiSurfaceBetaCapturePackTests(unittest.TestCase):
    def test_writes_candidate_only_pack_with_all_expected_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = json.loads(run_pack(Path(temp_dir), "--json").stdout)
            output_dir = Path(report["output_dir"])

            self.assertEqual(report["schema"], "obelisk.multi-surface-beta-capture-pack.v1")
            self.assertEqual(report["status"], "candidate_capture_pack")
            self.assertEqual(report["run_id"], RUN_ID)
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
                    "source": "operator_cli",
                },
            )
            self.assertEqual(report["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(
                report["plan_target_binding"],
                {
                    "all_artifacts_must_match": True,
                    "binding_id": "instance=arkserver|map=Ragnarok",
                    "instance": "arkserver",
                    "map": "Ragnarok",
                    "mismatched_target_rejects_pack": True,
                    "source": "operator_cli_plan_target",
                },
            )
            self.assertEqual(report["plan_target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(report["approved_runtime_window_binding"]["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertTrue(
                report["approved_runtime_window_binding"]["same_window_as_player_principal_lifecycle"]
            )
            self.assertFalse(report["approved_runtime_window_binding"]["pack_authorizes_window"])
            self.assertFalse(report["approved_runtime_window_binding"]["window_substitution_allowed"])
            self.assertEqual({artifact["name"] for artifact in report["artifacts"]}, EXPECTED_ARTIFACTS)
            for artifact in report["artifacts"]:
                self.assertEqual(artifact["path"], artifact["name"])
                self.assertFalse(Path(artifact["path"]).is_absolute())
            self.assertEqual(set(report["artifact_names"]), EXPECTED_FILES)
            self.assertEqual({path.name for path in output_dir.iterdir()}, EXPECTED_FILES)
            self.assertEqual(
                report["manifest_sha256_kind"],
                "sha256_of_manifest_without_manifest_sha256_field",
            )
            self.assertFalse(report["non_claim_flags"]["counts_as_approved_runtime_evidence"])
            self.assertFalse(report["non_claim_flags"]["counts_as_sdk_progress"])
            self.assertTrue(report["source_metadata_required"])
            self.assertEqual(
                report["source_metadata"]["schema"],
                "obelisk.multi-surface-beta-capture-source-metadata.v1",
            )
            self.assertFalse(report["source_metadata"]["source_ready"])
            self.assertFalse(report["source_metadata"]["source_material_counts_as_evidence"])
            self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
            self.assertEqual(
                report["next_required_artifact"],
                "approved_runtime_principal_lifecycle_evidence_bundle",
            )
            self.assertTrue(report["side_lanes_non_counting_before_player_principal"])
            self.assertTrue(report["checker_matrix_includes_command_templates"])
            self.assertTrue(report["next_action_groups_included"])
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_template"],
                "permissions-admin-beta-capture-candidates.json",
            )
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_schema"],
                "obelisk.permissions-admin-beta-capture-candidates.v1",
            )
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_surfaces"],
                ["admin", "list_player", "kick_path"],
            )
            self.assertEqual(
                report["broad_beta_capture_candidate_worksheet_template"],
                BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(
                report["broad_beta_capture_candidate_worksheet_schema"],
                "obelisk.multi-surface-beta-capture-broad-candidate-worksheet.v1",
            )
            self.assertEqual(
                report["broad_beta_capture_candidate_worksheet_id"],
                "admin_commands_dino_tribe_buff_candidate_worksheet",
            )
            self.assertTrue(report["broad_beta_capture_candidate_worksheet_included"])
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_template"],
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_schema"],
                "obelisk.multi-surface-beta-capture-simultaneous-candidate-worksheet.v1",
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_id"],
                "admin_commands_dino_tribe_buff_inventory_transfer_mission_candidate_worksheet",
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_surfaces"],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
            self.assertTrue(report["simultaneous_beta_capture_candidate_worksheet_included"])
            self.assertEqual(
                report["single_player_parallel_capture_candidate_worksheet_template"],
                SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(
                report["single_player_parallel_capture_candidate_worksheet_schema"],
                "obelisk.multi-surface-beta-capture-single-player-sequence-worksheet.v1",
            )
            self.assertEqual(
                report["single_player_parallel_capture_candidate_worksheet_id"],
                "single_player_player_principal_and_side_lane_candidate_worksheet",
            )
            self.assertEqual(
                report["single_player_parallel_capture_candidate_worksheet_surfaces"],
                SINGLE_PLAYER_ROUTE_SURFACES,
            )
            self.assertTrue(
                report["single_player_parallel_capture_candidate_worksheet_included"]
            )
            self.assertEqual(report["candidate_only_metadata"]["classification"], "candidate_only_non_evidence")
            self.assertTrue(report["candidate_only_metadata"]["non_evidence"])
            self.assertFalse(report["candidate_only_metadata"]["counts_as_runtime_evidence"])
            self.assertFalse(report["candidate_only_metadata"]["downstream_unlock_allowed"])
            self.assertFalse(report["parallel_capture_boundary"]["pack_authorizes_player_backed_window"])
            self.assertFalse(
                report["parallel_capture_boundary"][
                    "side_lane_collection_can_replace_player_principal_evidence"
                ]
            )
            self.assertTrue(
                report["parallel_capture_boundary"][
                    "parallel_with_player_principal_lifecycle_window_planned"
                ]
            )
            self.assertTrue(
                report["parallel_capture_boundary"][
                    "side_surfaces_grouped_as_optional_parallel_candidate_observations"
                ]
            )
            self.assertTrue(
                report["parallel_capture_boundary"][
                    "side_surfaces_non_evidence_until_own_checker_acceptance"
                ]
            )
            self.assertEqual(
                report["player_principal_window_composition"]["side_surface_role"],
                "optional_parallel_candidate_observations",
            )
            self.assertFalse(report["player_principal_window_composition"]["substitution_allowed"])
            self.assertFalse(report["player_principal_window_composition"]["counts_as_sdk_progress"])
            self.assertFalse(report["player_principal_window_composition"]["counts_as_p0_progress"])
            self.assertEqual(
                {
                    surface_id
                    for group in report["next_action_groups"]
                    for surface_id in group["surface_ids"]
                },
                EXPECTED_SURFACES,
            )
            broad_path = report["broad_beta_capture_pack_path"]
            self.assertEqual(broad_path["id"], "admin_commands_dino_tribe_buff_candidate_path")
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
            self.assertFalse(broad_path["counts_as_runtime_evidence"])
            self.assertFalse(broad_path["counts_as_sdk_progress"])
            self.assertFalse(broad_path["runtime_ready"])
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
            self.assertTrue(parallel_matrix["same_approved_runtime_window_required"])
            self.assertTrue(parallel_matrix["exact_target_binding_required"])
            self.assertFalse(parallel_matrix["counts_as_runtime_evidence"])
            self.assertFalse(parallel_matrix["counts_as_sdk_progress"])
            self.assertFalse(parallel_matrix["primary_evidence_substitution_allowed"])
            self.assertNotIn("player_principal_lifecycle", parallel_matrix["surface_ids"])
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
            self.assertTrue(sequence["single_player_route_constraints"]["redacted_metadata_only"])
            self.assertTrue(
                sequence["single_player_route_constraints"][
                    "side_lane_collection_requires_active_player_principal_route"
                ]
            )
            self.assertTrue(sequence["single_player_route_constraints"]["no_discord_required"])
            self.assertFalse(sequence["single_player_route_constraints"]["raw_player_text_retention_allowed"])
            self.assertFalse(sequence["single_player_route_constraints"]["secrets_or_webhook_retention_allowed"])
            self.assertFalse(
                sequence["single_player_route_constraints"][
                    "side_lane_collection_before_primary_route_active_allowed"
                ]
            )
            self.assertFalse(sequence["single_player_route_constraints"]["pack_authorizes_discord"])
            self.assertFalse(sequence["single_player_route_constraints"]["counts_as_sdk_progress"])
            self.assertFalse(sequence["single_player_route_constraints"]["clears_approved_runtime_evidence_missing"])
            self.assertFalse(sequence["pack_authorizes_discord"])
            self.assertFalse(sequence["authorizes_live_log_reads"])
            self.assertFalse(sequence["side_lane_counts_toward_sdk"])
            self.assertEqual(
                [phase["phase_id"] for phase in sequence["phases"]],
                sequence["action_group_ids"],
            )
            self.assertEqual(sequence["text_privacy_boundary"], report["text_privacy_boundary"])
            self.assertFalse(sequence["raw_player_text_retention_allowed"])
            self.assertFalse(sequence["secrets_or_webhook_retention_allowed"])
            self.assertFalse(sequence["clears_approved_runtime_evidence_missing"])
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
                self.assertTrue(phase["no_restart_required"], phase["phase_id"])
                self.assertFalse(phase["raw_player_text_retention_allowed"], phase["phase_id"])
                self.assertFalse(phase["secrets_or_webhook_retention_allowed"], phase["phase_id"])
                self.assertFalse(phase["pack_authorizes_discord"], phase["phase_id"])
                self.assertFalse(phase["authorizes_live_log_reads"], phase["phase_id"])
                self.assertFalse(phase["counts_as_sdk_progress"], phase["phase_id"])
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
                self.assertTrue(phase["checker_commands"], phase["phase_id"])
                for command_row in phase["checker_commands"]:
                    self.assertIn("resolved_checker_command_template", command_row, phase["phase_id"])
                    self.assertEqual(
                        command_row["target_bound_checker_command"]["target_binding_id"],
                        "instance=arkserver|map=Ragnarok",
                        phase["phase_id"],
                    )
                    self.assertFalse(
                        command_row["target_bound_checker_command"][
                            "raw_player_text_retention_allowed"
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
            self.assertTrue(report["target_bound_checker_command_matrix_included"])
            self.assertEqual(command_matrix["id"], "target_bound_offline_checker_command_matrix")
            self.assertEqual(command_matrix["status"], "offline_command_templates_candidate_only")
            self.assertEqual(command_matrix["row_count"], len(EXPECTED_SURFACES))
            self.assertEqual(command_matrix["target_binding_id"], "instance=arkserver|map=Ragnarok")
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
                self.assertEqual(row["operator_next_action"], row["lead_next_action"], row)
                self.assertTrue(row["tester_brief"], row)
            for row in parallel_matrix["surface_rows"]:
                self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok", row["id"])
                self.assertTrue(row["side_lane"], row["id"])
                self.assertTrue(row["exact_approved_runtime_window_required"], row["id"])
                self.assertTrue(row["no_restart_required"], row["id"])
                self.assertTrue(row["tester_actions_do_not_require_restart"], row["id"])
                self.assertFalse(row["restart_required"], row["id"])
                self.assertFalse(row["server_restart_required"], row["id"])
                self.assertFalse(row["counts_as_sdk_progress"], row["id"])
                self.assertFalse(row["counts_as_p0_progress"], row["id"])
                self.assertEqual(row["operator_next_action"], row["lead_next_action"], row["id"])
                self.assertTrue(row["tester_brief"], row["id"])

            plan = json.loads((output_dir / "multi-surface-capture-plan.json").read_text())
            manifest = json.loads((output_dir / "manifest.json").read_text())
            assert_beta_capture_interaction_boundary(
                self,
                manifest["beta_capture_interaction_boundary"],
            )
            self.assertEqual(plan["schema"], "obelisk.multi-surface-beta-capture-plan.v1")
            self.assertEqual(plan["target_binding"]["instance"], "arkserver")
            assert_beta_capture_interaction_boundary(
                self,
                plan["beta_capture_interaction_boundary"],
            )
            self.assertEqual(
                manifest["beta_capture_interaction_boundary"],
                report["beta_capture_interaction_boundary"],
            )
            self.assertEqual(
                plan["beta_capture_interaction_boundary"],
                report["beta_capture_interaction_boundary"],
            )
            self.assertEqual(plan["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(plan["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(plan["approved_runtime_window_binding"], report["approved_runtime_window_binding"])
            self.assertTrue(plan["single_beta_session_intent"])
            self.assertIn("operator_focus", plan["practical_beta_session_objectives"])
            self.assertTrue(plan["artifact_intake_constraints"]["target_binding_must_match_pack_target"])
            self.assertEqual({surface["id"] for surface in plan["capture_surfaces"]}, EXPECTED_SURFACES)
            self.assertEqual(
                [surface["priority"] for surface in plan["capture_surfaces"]],
                list(range(1, len(EXPECTED_SURFACES) + 1)),
            )
            self.assertEqual(
                plan["required_primary_evidence"]["strict_triplet"],
                "HandleNewPlayer(1,1) -> CheckJoinInProgress(1,0) -> matched OnLogout",
            )
            self.assertEqual(plan["candidate_only_metadata"], report["candidate_only_metadata"])
            self.assertEqual(plan["parallel_capture_boundary"], report["parallel_capture_boundary"])
            self.assertEqual(
                plan["player_principal_window_composition"],
                report["player_principal_window_composition"],
            )
            self.assertEqual(plan["next_action_groups"], report["next_action_groups"])
            self.assertEqual(plan["broad_beta_capture_pack_path"], broad_path)
            self.assertEqual(plan["parallel_beta_capture_side_lane_matrix"], parallel_matrix)
            self.assertEqual(plan["single_player_parallel_capture_sequence"], sequence)
            self.assertEqual(plan["target_bound_checker_command_matrix"], command_matrix)
            self.assertEqual(plan["text_privacy_boundary"], report["text_privacy_boundary"])

            worksheet = json.loads(
                (output_dir / BROAD_BETA_CAPTURE_WORKSHEET_FILE).read_text()
            )
            self.assertEqual(
                worksheet["schema"],
                "obelisk.multi-surface-beta-capture-broad-candidate-worksheet.v1",
            )
            self.assertEqual(
                worksheet["id"],
                "admin_commands_dino_tribe_buff_candidate_worksheet",
            )
            self.assertEqual(worksheet["file"], BROAD_BETA_CAPTURE_WORKSHEET_FILE)
            self.assertEqual(worksheet["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(worksheet["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(worksheet["surface_ids"], BROAD_BETA_CAPTURE_SURFACES)
            self.assertEqual(worksheet["action_group_ids"], ["admin_and_command_routes", "world_state_scalar_candidates"])
            self.assertEqual(worksheet["worksheet_row_count"], len(BROAD_BETA_CAPTURE_SURFACES))
            self.assertTrue(worksheet["candidate_only"])
            self.assertTrue(worksheet["non_evidence"])
            self.assertFalse(worksheet["counts_as_approved_runtime_evidence"])
            self.assertFalse(worksheet["counts_as_runtime_evidence"])
            self.assertFalse(worksheet["counts_as_sdk_progress"])
            self.assertFalse(worksheet["clears_approved_runtime_evidence_missing"])
            self.assertFalse(worksheet["authorizes_runtime_capture"])
            self.assertFalse(worksheet["authorizes_discord_send"])
            self.assertEqual(
                [row["surface_id"] for row in worksheet["worksheet_rows"]],
                BROAD_BETA_CAPTURE_SURFACES,
            )
            for row in worksheet["worksheet_rows"]:
                self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok")
                self.assertEqual(row["observation_rows"], [])
                self.assertTrue(row["candidate_only"], row["surface_id"])
                self.assertTrue(row["non_evidence"], row["surface_id"])
                self.assertFalse(row["counts_as_runtime_evidence"], row["surface_id"])
                field_ids = {field["field_id"] for field in row["worksheet_fields"]}
                self.assertIn("approved_window_id", field_ids)
                self.assertIn("observed_at_utc", field_ids)
                self.assertIn("candidate_artifact_path", field_ids)
            self.assertIn(
                "admin_command_family",
                {field["field_id"] for field in worksheet["worksheet_rows"][0]["worksheet_fields"]},
            )
            self.assertIn(
                "status_transition_shape",
                {field["field_id"] for field in worksheet["worksheet_rows"][-1]["worksheet_fields"]},
            )

            simultaneous_worksheet = json.loads(
                (output_dir / SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE).read_text()
            )
            self.assertEqual(
                simultaneous_worksheet["schema"],
                "obelisk.multi-surface-beta-capture-simultaneous-candidate-worksheet.v1",
            )
            self.assertEqual(
                simultaneous_worksheet["id"],
                "admin_commands_dino_tribe_buff_inventory_transfer_mission_candidate_worksheet",
            )
            self.assertEqual(
                simultaneous_worksheet["file"],
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(simultaneous_worksheet["surface_ids"], PARALLEL_BETA_CAPTURE_SURFACES)
            self.assertEqual(
                [row["surface_id"] for row in simultaneous_worksheet["worksheet_rows"]],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
            self.assertEqual(
                simultaneous_worksheet["parallel_beta_capture_matrix_id"],
                "admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates",
            )
            self.assertTrue(simultaneous_worksheet["candidate_only"])
            self.assertTrue(simultaneous_worksheet["non_evidence"])
            self.assertTrue(simultaneous_worksheet["simultaneous_side_lane_rows"])
            self.assertFalse(simultaneous_worksheet["counts_as_runtime_evidence"])
            self.assertFalse(simultaneous_worksheet["counts_as_sdk_progress"])
            mission_row = next(
                row
                for row in simultaneous_worksheet["worksheet_rows"]
                if row["surface_id"] == "mission_copied_bool"
            )
            self.assertEqual(mission_row["observation_rows"], [])
            self.assertIn(
                "mission_context_shape",
                {field["field_id"] for field in mission_row["worksheet_fields"]},
            )
            self.assertFalse(mission_row["counts_as_runtime_evidence"])

            single_player_worksheet = json.loads(
                (output_dir / SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE).read_text()
            )
            self.assertEqual(
                single_player_worksheet["schema"],
                "obelisk.multi-surface-beta-capture-single-player-sequence-worksheet.v1",
            )
            self.assertEqual(
                single_player_worksheet["id"],
                "single_player_player_principal_and_side_lane_candidate_worksheet",
            )
            self.assertEqual(
                single_player_worksheet["file"],
                SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(single_player_worksheet["surface_ids"], SINGLE_PLAYER_ROUTE_SURFACES)
            self.assertEqual(
                [row["surface_id"] for row in single_player_worksheet["worksheet_rows"]],
                SINGLE_PLAYER_ROUTE_SURFACES,
            )
            self.assertEqual(
                single_player_worksheet["single_player_parallel_capture_sequence_id"],
                "single_player_parallel_side_lane_capture_sequence",
            )
            self.assertTrue(single_player_worksheet["single_player_sequence_rows"])
            self.assertTrue(single_player_worksheet["primary_player_principal_row_included"])
            self.assertTrue(single_player_worksheet["side_lane_rows_included"])
            self.assertFalse(single_player_worksheet["counts_as_runtime_evidence"])
            self.assertFalse(single_player_worksheet["counts_as_sdk_progress"])
            primary_row = single_player_worksheet["worksheet_rows"][0]
            self.assertEqual(primary_row["surface_id"], "player_principal_lifecycle")
            self.assertEqual(primary_row["observation_rows"], [])
            primary_field_ids = {
                field["field_id"] for field in primary_row["worksheet_fields"]
            }
            self.assertIn("session_start_observer_role", primary_field_ids)
            self.assertIn("checkjoin_rejected_start_shape", primary_field_ids)
            self.assertIn("session_end_correlation_shape", primary_field_ids)
            self.assertIn(
                "presence_without_lifecycle_start_after_observer_gate",
                primary_field_ids,
            )
            self.assertTrue(primary_row["candidate_only"])
            self.assertFalse(primary_row["counts_as_runtime_evidence"])

            beta_capture = json.loads(
                (output_dir / "permissions-admin-beta-capture-candidates.json").read_text()
            )
            self.assertEqual(
                beta_capture["schema"],
                "obelisk.permissions-admin-beta-capture-candidates.v1",
            )
            self.assertEqual(beta_capture["artifact_kind"], "beta_capture_candidate")
            self.assertEqual(beta_capture["artifact_status"], "candidate_only")
            self.assertTrue(beta_capture["candidate_only"])
            self.assertTrue(beta_capture["debug_only"])
            self.assertTrue(beta_capture["requires_own_checker_acceptance"])
            self.assertTrue(beta_capture["requires_player_principal_triplet"])
            self.assertIn("candidate/debug queue metadata only", beta_capture["non_claim"])
            self.assertIn("do not replace the required player-principal triplet", beta_capture["non_claim"])
            self.assertEqual(
                {candidate["id"] for candidate in beta_capture["candidate_debug_surfaces"]},
                {"admin", "list_player", "kick_path"},
            )
            self.assertEqual(
                {
                    candidate["id"]: candidate["target"]
                    for candidate in beta_capture["candidate_debug_surfaces"]
                },
                {
                    "admin": "permissions_admin_admin_surface",
                    "list_player": "ShooterPlayerController.ServerListPlayers",
                    "kick_path": "ShooterPlayerController.ServerKickPlayer",
                },
            )
            for item in [beta_capture, *beta_capture["candidate_debug_surfaces"]]:
                self.assertEqual(item["artifact_status"], "candidate_only")
                self.assertTrue(item["candidate_only"])
                self.assertTrue(item["debug_only"])
                self.assertTrue(item["requires_own_checker_acceptance"])
                self.assertTrue(item["requires_player_principal_triplet"])
                self.assertFalse(item["approved_runtime_evidence_ready"])
                self.assertFalse(item["counts_as_approved_runtime_evidence"])
                self.assertFalse(item["counts_as_runtime_evidence"])
                self.assertFalse(item["counts_as_sdk_progress"])
                self.assertFalse(item["counts_as_p0_progress"])
                self.assertFalse(item["clears_approved_runtime_evidence_missing"])
                self.assertFalse(item["replaces_player_principal_evidence"])
                self.assertFalse(item["public_sdk_ready"])
                self.assertFalse(item["runtime_ready"])
                self.assertFalse(item["stable_sdk_ready"])
                self.assertEqual(item["p0_progress"], 0)
                self.assertEqual(item["public_sdk_progress"], 0)
                self.assertEqual(item["sdk_progress"], 0)

            readiness = subprocess.run(
                [
                    sys.executable,
                    str(READINESS_SCRIPT),
                    "--json",
                    "--beta-capture-artifact",
                    str(output_dir / "permissions-admin-beta-capture-candidates.json"),
                ],
                check=True,
                cwd=SCRIPT_DIR.parent,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            readiness_report = json.loads(readiness.stdout)
            self.assertTrue(readiness_report["valid"], readiness_report["blockers"])
            self.assertFalse(readiness_report["accepted_for_planning"])
            self.assertEqual(
                readiness_report["beta_capture_artifact_schema"],
                "obelisk.permissions-admin-beta-capture-candidates.v1",
            )
            self.assertEqual(
                readiness_report["beta_capture_candidate_surfaces"],
                ["admin", "kick_path", "list_player"],
            )
            self.assertFalse(readiness_report["public_sdk_ready"])
            self.assertFalse(readiness_report["runtime_ready"])
            self.assertFalse(readiness_report["promotion_ready"])

            intake = json.loads((output_dir / "candidate-artifact-intake.json").read_text())
            self.assertEqual(intake["schema"], "obelisk.multi-surface-beta-capture-artifact-intake.v1")
            self.assertEqual(intake["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(intake["target_binding"], plan["target_binding"])
            self.assertEqual(intake["target_binding_id"], plan["target_binding_id"])
            self.assertTrue(intake["capture_session_constraints"]["single_beta_session_intent"])
            self.assertTrue(intake["capture_session_constraints"]["copy_to_offline_workspace_before_analysis"])
            self.assertTrue(intake["capture_session_constraints"]["do_not_read_live_server_paths_from_pack"])
            self.assertTrue(intake["capture_session_constraints"]["requires_checker_acceptance_before_any_surface_claim"])
            self.assertTrue(intake["capture_session_constraints"]["artifacts_must_keep_target_binding"])
            self.assertTrue(intake["capture_session_constraints"]["artifact_templates_only"])
            self.assertTrue(intake["capture_session_constraints"]["artifact_templates_must_stay_relative"])
            self.assertTrue(intake["capture_session_constraints"]["artifact_templates_must_stay_under_candidate_artifacts"])
            self.assertTrue(intake["capture_session_constraints"]["artifact_templates_must_not_name_live_server_paths"])
            self.assertTrue(intake["capture_session_constraints"]["redaction_required_before_checker_intake"])
            self.assertTrue(
                intake["capture_session_constraints"][
                    "candidate_artifact_presence_never_implies_checker_acceptance"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "candidate_artifact_intake_cannot_replace_primary_runtime_evidence"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "side_lane_artifacts_cannot_substitute_for_player_principal_lifecycle_evidence"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "parallel_with_player_principal_lifecycle_window_planned"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "side_surfaces_grouped_as_optional_parallel_candidate_observations"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "side_surfaces_non_evidence_until_own_checker_acceptance"
                ]
            )
            self.assertTrue(
                intake["capture_session_constraints"][
                    "separate_player_backed_window_approval_required"
                ]
            )
            self.assertTrue(intake["capture_session_constraints"]["same_approved_runtime_window_required"])
            self.assertTrue(
                intake["capture_session_constraints"][
                    "side_lane_artifacts_must_share_player_principal_window"
                ]
            )
            self.assertTrue(intake["capture_session_constraints"]["operator_tester_action_metadata_required"])
            self.assertFalse(intake["capture_session_constraints"]["pack_authorizes_player_backed_window"])
            self.assertFalse(intake["capture_session_constraints"]["pack_authorizes_approved_runtime_window"])
            self.assertTrue(intake["artifact_intake_constraints"]["path_template_only"])
            self.assertTrue(intake["artifact_intake_constraints"]["path_template_must_not_name_live_server_paths"])
            self.assertEqual(intake["candidate_only_metadata"], plan["candidate_only_metadata"])
            self.assertEqual(intake["parallel_capture_boundary"], plan["parallel_capture_boundary"])
            self.assertEqual(
                intake["player_principal_window_composition"],
                plan["player_principal_window_composition"],
            )
            self.assertEqual(intake["next_action_groups"], plan["next_action_groups"])
            self.assertEqual(intake["broad_beta_capture_pack_path"], broad_path)
            self.assertEqual(intake["parallel_beta_capture_side_lane_matrix"], parallel_matrix)
            self.assertEqual(intake["single_player_parallel_capture_sequence"], sequence)
            self.assertEqual(intake["target_bound_checker_command_matrix"], command_matrix)
            self.assertEqual(intake["text_privacy_boundary"], plan["text_privacy_boundary"])
            self.assertEqual({surface["id"] for surface in intake["surfaces"]}, EXPECTED_SURFACES)
            for surface in intake["surfaces"]:
                plan_surface = next(item for item in plan["capture_surfaces"] if item["id"] == surface["id"])
                self.assertEqual(surface["target_binding"], plan_surface["target_binding"])
                self.assertEqual(surface["target_binding_id"], plan_surface["target_binding_id"])
                self.assertEqual(
                    surface["approved_runtime_window_binding"],
                    plan_surface["approved_runtime_window_binding"],
                )
                self.assertEqual(
                    surface["non_substitution_flags"],
                    plan_surface["non_substitution_flags"],
                )
                self.assertEqual(surface["candidate_only_metadata"], plan_surface["candidate_only_metadata"])
                self.assertEqual(surface["parallel_capture_boundary"], plan_surface["parallel_capture_boundary"])
                self.assertEqual(
                    surface["player_principal_window_composition"],
                    plan_surface["player_principal_window_composition"],
                )
                self.assertEqual(surface["composition_role"], plan_surface["composition_role"])
                self.assertEqual(
                    surface["optional_parallel_candidate_observation"],
                    plan_surface["optional_parallel_candidate_observation"],
                )
                self.assertEqual(
                    surface["parallel_with_player_principal_lifecycle_window"],
                    plan_surface["parallel_with_player_principal_lifecycle_window"],
                )
                self.assertEqual(surface["tester_action"], plan_surface["tester_action"])
                self.assertEqual(
                    surface["operator_tester_action_metadata"],
                    plan_surface["operator_tester_action_metadata"],
                )
                self.assertFalse(
                    surface["operator_tester_action_metadata"]["secrets_or_webhook_retention_allowed"],
                    surface["id"],
                )
                self.assertEqual(surface["command"], plan_surface["post_capture_checker_command"])
                self.assertEqual(
                    surface["resolved_checker_command_template"],
                    plan_surface["resolved_checker_command_template"],
                )
                self.assertEqual(
                    surface["checker_command_bindings"],
                    plan_surface["checker_command_bindings"],
                )
                self.assertEqual(
                    surface["target_bound_checker_command"],
                    plan_surface["target_bound_checker_command"],
                )
                self.assertEqual(surface["capture_artifacts"], plan_surface["capture_artifacts"])
                self.assertEqual(surface["required_checker_artifacts"], plan_surface["required_checker_artifacts"])
                self.assertEqual(surface["optional_candidate_artifacts"], plan_surface["optional_candidate_artifacts"])
                self.assertTrue(surface["checker_inputs_satisfied_by_artifacts"])
                self.assertFalse(surface["counts_as_runtime_evidence"], surface["id"])
                self.assertFalse(surface["counts_as_sdk_progress"], surface["id"])

            matrix = json.loads((output_dir / "checker-command-matrix.json").read_text())
            self.assertEqual(matrix["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(matrix["target_binding"], plan["target_binding"])
            self.assertEqual(matrix["target_binding_id"], plan["target_binding_id"])
            self.assertEqual(matrix["approved_runtime_window_binding"], plan["approved_runtime_window_binding"])
            self.assertEqual(matrix["current_route_blocker"], "approved_runtime_evidence_missing")
            self.assertEqual(
                matrix["next_required_artifact"],
                "approved_runtime_principal_lifecycle_evidence_bundle",
            )
            self.assertEqual(matrix["candidate_only_metadata"], plan["candidate_only_metadata"])
            self.assertEqual(matrix["parallel_capture_boundary"], plan["parallel_capture_boundary"])
            self.assertEqual(
                matrix["player_principal_window_composition"],
                plan["player_principal_window_composition"],
            )
            self.assertEqual(matrix["next_action_groups"], plan["next_action_groups"])
            self.assertEqual(matrix["broad_beta_capture_pack_path"], broad_path)
            self.assertEqual(matrix["parallel_beta_capture_side_lane_matrix"], parallel_matrix)
            self.assertEqual(matrix["single_player_parallel_capture_sequence"], sequence)
            self.assertEqual(matrix["target_bound_checker_command_matrix"], command_matrix)
            self.assertEqual(matrix["text_privacy_boundary"], plan["text_privacy_boundary"])
            self.assertEqual({surface["id"] for surface in matrix["surfaces"]}, EXPECTED_SURFACES)
            for surface in matrix["surfaces"]:
                plan_surface = next(item for item in plan["capture_surfaces"] if item["id"] == surface["id"])
                self.assertTrue(surface["candidate_capture_only"], surface["id"])
                self.assertEqual(surface["candidate_only_metadata"], plan_surface["candidate_only_metadata"])
                self.assertEqual(surface["parallel_capture_boundary"], plan_surface["parallel_capture_boundary"])
                self.assertEqual(
                    surface["player_principal_window_composition"],
                    plan_surface["player_principal_window_composition"],
                )
                self.assertEqual(surface["composition_role"], plan_surface["composition_role"])
                self.assertEqual(
                    surface["optional_parallel_candidate_observation"],
                    plan_surface["optional_parallel_candidate_observation"],
                )
                self.assertEqual(
                    surface["parallel_with_player_principal_lifecycle_window"],
                    plan_surface["parallel_with_player_principal_lifecycle_window"],
                )
                self.assertEqual(surface["target_binding"], plan_surface["target_binding"])
                self.assertEqual(surface["target_binding_id"], plan_surface["target_binding_id"])
                self.assertEqual(
                    surface["approved_runtime_window_binding"],
                    plan_surface["approved_runtime_window_binding"],
                )
                self.assertEqual(
                    surface["non_substitution_flags"],
                    plan_surface["non_substitution_flags"],
                )
                self.assertEqual(surface["tester_action"], plan_surface["tester_action"])
                self.assertEqual(
                    surface["operator_tester_action_metadata"],
                    plan_surface["operator_tester_action_metadata"],
                )
                self.assertTrue(surface["requires_checker_acceptance"], surface["id"])
                self.assertTrue(surface["requires_player_principal_triplet"], surface["id"])
                self.assertTrue(surface["blocked_by_player_principal_evidence"], surface["id"])
                self.assertEqual(surface["candidate_classification"], "candidate_only_non_counting")
                self.assertEqual(surface["command"], plan_surface["post_capture_checker_command"])
                self.assertEqual(
                    surface["resolved_checker_command_template"],
                    plan_surface["resolved_checker_command_template"],
                )
                self.assertEqual(
                    surface["checker_command_bindings"],
                    plan_surface["checker_command_bindings"],
                )
                self.assertEqual(
                    surface["target_bound_checker_command"],
                    plan_surface["target_bound_checker_command"],
                )
                self.assertEqual(surface["required_checker_artifacts"], plan_surface["required_checker_artifacts"])
                self.assertEqual(surface["optional_candidate_artifacts"], plan_surface["optional_candidate_artifacts"])
                self.assertTrue(surface["checker_inputs_satisfied_by_artifacts"])
                self.assertEqual(surface["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertEqual(
                    surface["required_runtime_evidence"],
                    "approved_runtime_principal_lifecycle_evidence_bundle",
                )
                self.assertFalse(surface["approved_runtime_evidence_present"], surface["id"])
                self.assertFalse(surface["approved_runtime_evidence_ready"], surface["id"])
                self.assertFalse(surface["replaces_player_principal_triplet"], surface["id"])
                self.assertFalse(surface["counts_as_runtime_evidence"], surface["id"])
                self.assertFalse(surface["clears_approved_runtime_evidence_missing"], surface["id"])

            non_claim = json.loads((output_dir / "non-claim-manifest.json").read_text())
            self.assertEqual(non_claim["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(non_claim["target_binding"], plan["target_binding"])
            self.assertEqual(non_claim["target_binding_id"], plan["target_binding_id"])
            self.assertEqual(non_claim["approved_runtime_window_binding"], plan["approved_runtime_window_binding"])
            self.assertEqual(non_claim["current_route_blocker"], "approved_runtime_evidence_missing")
            self.assertEqual(non_claim["candidate_only_metadata"], plan["candidate_only_metadata"])
            self.assertEqual(non_claim["parallel_capture_boundary"], plan["parallel_capture_boundary"])
            self.assertEqual(
                non_claim["player_principal_window_composition"],
                plan["player_principal_window_composition"],
            )
            self.assertEqual(non_claim["next_action_groups"], plan["next_action_groups"])
            self.assertEqual(non_claim["broad_beta_capture_pack_path"], broad_path)
            self.assertEqual(non_claim["parallel_beta_capture_side_lane_matrix"], parallel_matrix)
            self.assertEqual(non_claim["single_player_parallel_capture_sequence"], sequence)
            self.assertEqual(non_claim["target_bound_checker_command_matrix"], command_matrix)
            self.assertEqual(non_claim["text_privacy_boundary"], plan["text_privacy_boundary"])
            self.assertTrue(non_claim["side_lanes_non_counting_before_player_principal"])
            for item in iter_dicts(non_claim):
                for flag in FALSE_FLAGS:
                    if flag in item:
                        self.assertFalse(item[flag], f"{flag} at {item}")
            for surface in non_claim["surface_non_claims"]:
                expected_side_lane = surface["id"] != "player_principal_lifecycle"
                self.assertEqual(surface["target_binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
                self.assertEqual(
                    surface["approved_runtime_window_binding"],
                    plan["approved_runtime_window_binding"],
                    surface["id"],
                )
                self.assertIsInstance(surface["tester_action"], str, surface["id"])
                self.assertEqual(
                    surface["operator_tester_action_metadata"]["approved_runtime_window_binding"],
                    plan["approved_runtime_window_binding"],
                    surface["id"],
                )
                self.assertFalse(
                    surface["non_substitution_flags"]["primary_evidence_substitution_allowed"],
                    surface["id"],
                )
                self.assertTrue(surface["requires_player_principal_triplet"], surface["id"])
                self.assertTrue(surface["blocked_by_player_principal_evidence"], surface["id"])
                self.assertEqual(surface["side_lane_non_counting"], expected_side_lane, surface["id"])
                self.assertEqual(surface["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertFalse(surface["approved_runtime_evidence_present"], surface["id"])
                self.assertFalse(surface["approved_runtime_evidence_ready"], surface["id"])
                self.assertFalse(surface["approved_runtime_evidence_substitution_allowed"], surface["id"])
                self.assertFalse(surface["primary_evidence_substitution_allowed"], surface["id"])
                self.assertFalse(surface["substitutes_for_player_principal_lifecycle_evidence"], surface["id"])
                self.assertFalse(surface["substitutes_for_player_principal_lifecycle_triplet"], surface["id"])
                self.assertFalse(surface["player_principal_lifecycle_evidence_substitution_allowed"], surface["id"])
                self.assertEqual(
                    surface["player_principal_window_composition"],
                    plan["player_principal_window_composition"],
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

            runbook = (output_dir / "operator-runbook.md").read_text()
            readme = (output_dir / "README.md").read_text()
            self.assertIn("Target: `arkserver` / `Ragnarok`", readme)
            self.assertIn("Target: `arkserver` / `Ragnarok`", runbook)
            self.assertIn("Binding ID: `instance=arkserver|map=Ragnarok`", readme)
            self.assertIn("Binding ID: `instance=arkserver|map=Ragnarok`", runbook)
            self.assertIn("Keep at most two ARK servers running.", runbook)
            self.assertIn("Do not retain raw player text", runbook)
            self.assertIn("Next-action groups:", runbook)
            self.assertIn("inventory_item_candidates", runbook)
            self.assertIn("inventory_action_compact_intake", runbook)
            self.assertIn("item_return_only", runbook)
            self.assertNotIn("structure_census", runbook)
            self.assertIn("mission_copied_bool", runbook)
            self.assertIn("player_principal_lifecycle", runbook)
            self.assertIn("transfer_baccept", runbook)
            self.assertIn("transfer_scriptstruct", runbook)
            self.assertIn("Side-lanes remain non-counting before the player-principal blocker is solved.", runbook)
            self.assertIn("Side-lane groups are optional parallel candidate observations", runbook)
            self.assertIn("separately approved player-principal lifecycle window", runbook)
            self.assertIn("same approved runtime window, instance, and map", runbook)
            self.assertIn("Tester action:", runbook)
            self.assertIn("permissions-admin-beta-capture-candidates.json", runbook)
            self.assertIn("simultaneous-side-lane-candidate-worksheet.json", runbook)
            self.assertIn("Admin/commands/dino/tribe/buff status-only candidate path", runbook)
            self.assertIn("Broad status-only candidate path:", runbook)
            self.assertIn("admin_commands_dino_tribe_buff_candidate_path", runbook)
            self.assertIn(
                "Admin/commands/dino/tribe/buff/inventory/item/transfer/mission parallel candidate matrix",
                runbook,
            )
            self.assertIn("Parallel side-lane candidate matrix:", runbook)
            self.assertIn("Single-player parallel capture sequence:", runbook)
            self.assertIn("Single-player route surfaces:", runbook)
            self.assertIn("Single-player route domains:", runbook)
            self.assertIn("Single-player route excludes:", runbook)
            self.assertIn("Single-player route excludes: none.", runbook)
            self.assertIn("no-restart, no-Discord, non-evidence, non-progress", runbook)
            self.assertIn("cannot clear approved_runtime_evidence_missing", runbook)
            self.assertIn("Target-bound offline checker command matrix", runbook)
            self.assertIn("Target-bound offline checker commands:", runbook)
            self.assertIn("Path arguments point under `candidate-artifacts/`", runbook)
            self.assertIn("Resolved offline command template:", runbook)
            self.assertIn("raw player text retention is not allowed", runbook)
            self.assertIn("Tester actions: do not require or authorize starts, stops, restarts", runbook)
            self.assertIn(
                "admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates",
                runbook,
            )
            self.assertIn("cannot authorize that window or replace player-principal evidence", readme)
            self.assertIn("same approved runtime window, instance, and map", readme)
            self.assertIn("permissions-admin-beta-capture-candidates.json", readme)
            self.assertIn("simultaneous-side-lane-candidate-worksheet.json", readme)
            self.assertIn("Admin/commands/dino/tribe/buff status-only candidate path", readme)
            self.assertIn(
                "Admin/commands/dino/tribe/buff/inventory/item/transfer/mission parallel candidate matrix",
                readme,
            )
            self.assertIn("Single-player parallel capture sequence", readme)
            self.assertIn("Single-player route surfaces:", readme)
            self.assertIn("Single-player route domains:", readme)
            self.assertIn("Single-player route excludes:", readme)
            self.assertIn("Single-player route excludes: none", readme)
            self.assertIn("no-restart, no-Discord", readme)
            self.assertIn("approved_runtime_evidence_missing", readme)
            self.assertIn("Target-bound offline checker command matrix", readme)
            self.assertIn("read-text templates and never live server paths", readme)
            self.assertIn("raw player text retention is not allowed", readme)

    def test_manifest_is_deterministic_across_output_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            left_report = json.loads(run_pack(Path(temp_dir) / "left", "--json").stdout)
            right_report = json.loads(run_pack(Path(temp_dir) / "right", "--json").stdout)
            left_manifest_path = Path(left_report["output_dir"]) / "manifest.json"
            right_manifest_path = Path(right_report["output_dir"]) / "manifest.json"
            left_manifest = json.loads(left_manifest_path.read_text(encoding="utf-8"))
            right_manifest = json.loads(right_manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(left_manifest, right_manifest)
            self.assertEqual(left_report["manifest_sha256"], right_report["manifest_sha256"])
            self.assertNotIn("output_dir", left_manifest)
            for artifact in left_manifest["artifacts"]:
                self.assertEqual(artifact["path"], artifact["name"])
                self.assertFalse(Path(artifact["path"]).is_absolute())

    def test_dry_run_reports_without_writing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            report = json.loads(run_pack(Path(temp_dir), "--dry-run", "--json").stdout)

            self.assertEqual(report["status"], "dry_run_candidate_capture_pack")
            self.assertEqual(report["target"], {"instance": "arkserver", "map": "Ragnarok"})
            assert_beta_capture_interaction_boundary(
                self,
                report["beta_capture_interaction_boundary"],
            )
            self.assertEqual(report["target_binding"]["source"], "operator_cli")
            self.assertEqual(report["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(report["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertTrue(report["target_binding"]["all_artifacts_must_match"])
            self.assertTrue(report["target_binding"]["mismatched_target_rejects_pack"])
            self.assertEqual(report["plan_target_binding"]["source"], "operator_cli_plan_target")
            self.assertEqual(report["plan_target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(report["plan_target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertTrue(report["plan_target_binding"]["mismatched_target_rejects_pack"])
            self.assertEqual(report["approved_runtime_window_binding"]["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertFalse(report["approved_runtime_window_binding"]["pack_authorizes_window"])
            self.assertEqual(report["artifact_names"], sorted(EXPECTED_FILES))
            self.assertFalse((Path(temp_dir) / RUN_ID).exists())
            self.assertFalse(report["non_claim_flags"]["counts_as_approved_runtime_evidence"])
            self.assertTrue(report["side_lanes_non_counting_before_player_principal"])
            self.assertTrue(report["next_action_groups_included"])
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_template"],
                "permissions-admin-beta-capture-candidates.json",
            )
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_schema"],
                "obelisk.permissions-admin-beta-capture-candidates.v1",
            )
            self.assertEqual(
                report["permissions_admin_beta_capture_candidate_surfaces"],
                ["admin", "list_player", "kick_path"],
            )
            self.assertEqual(
                report["broad_beta_capture_candidate_worksheet_template"],
                BROAD_BETA_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(
                report["broad_beta_capture_candidate_worksheet_schema"],
                "obelisk.multi-surface-beta-capture-broad-candidate-worksheet.v1",
            )
            self.assertTrue(report["broad_beta_capture_candidate_worksheet_included"])
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_template"],
                SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE,
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_schema"],
                "obelisk.multi-surface-beta-capture-simultaneous-candidate-worksheet.v1",
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_id"],
                "admin_commands_dino_tribe_buff_inventory_transfer_mission_candidate_worksheet",
            )
            self.assertEqual(
                report["simultaneous_beta_capture_candidate_worksheet_surfaces"],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
            self.assertTrue(report["simultaneous_beta_capture_candidate_worksheet_included"])
            self.assertEqual(
                report["broad_beta_capture_pack_path"]["surface_ids"],
                BROAD_BETA_CAPTURE_SURFACES,
            )
            self.assertFalse(report["broad_beta_capture_pack_path"]["counts_as_runtime_evidence"])
            self.assertFalse(report["broad_beta_capture_pack_path"]["runtime_ready"])
            self.assertEqual(
                report["parallel_beta_capture_side_lane_matrix"]["surface_ids"],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
            self.assertTrue(report["parallel_beta_capture_side_lane_matrix"]["status_only"])
            self.assertTrue(
                report["parallel_beta_capture_side_lane_matrix"][
                    "same_approved_runtime_window_required"
                ]
            )
            self.assertFalse(
                report["parallel_beta_capture_side_lane_matrix"]["counts_as_runtime_evidence"]
            )
            self.assertEqual(report["candidate_only_metadata"]["classification"], "candidate_only_non_evidence")
            self.assertEqual(
                report["single_player_parallel_capture_sequence"]["side_lane_surface_ids"],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
            self.assertEqual(
                report["single_player_parallel_capture_sequence"]["single_player_route_surface_ids"],
                SINGLE_PLAYER_ROUTE_SURFACES,
            )
            self.assertEqual(
                report["single_player_parallel_capture_sequence"]["candidate_domain_ids"],
                SINGLE_PLAYER_ROUTE_DOMAINS,
            )
            self.assertEqual(
                report["single_player_parallel_capture_sequence"]["excluded_surface_ids"],
                [],
            )
            self.assertFalse(
                report["single_player_parallel_capture_sequence"][
                    "single_player_route_constraints"
                ]["pack_authorizes_discord"]
            )
            self.assertFalse(
                report["single_player_parallel_capture_sequence"][
                    "single_player_route_constraints"
                ]["clears_approved_runtime_evidence_missing"]
            )
            self.assertFalse(
                report["single_player_parallel_capture_sequence"][
                    "raw_player_text_retention_allowed"
                ]
            )
            self.assertFalse(
                report["single_player_parallel_capture_sequence"][
                    "secrets_or_webhook_retention_allowed"
                ]
            )
            self.assertEqual(
                report["single_player_parallel_capture_sequence"]["text_privacy_boundary"],
                report["text_privacy_boundary"],
            )
            self.assertTrue(report["target_bound_checker_command_matrix_included"])
            self.assertEqual(
                report["target_bound_checker_command_matrix"]["id"],
                "target_bound_offline_checker_command_matrix",
            )
            self.assertEqual(
                report["target_bound_checker_command_matrix"]["row_count"],
                len(EXPECTED_SURFACES),
            )
            self.assertFalse(
                report["target_bound_checker_command_matrix"][
                    "raw_player_text_retention_allowed"
                ]
            )
            self.assertFalse(
                report["target_bound_checker_command_matrix"][
                    "secrets_or_webhook_retention_allowed"
                ]
            )
            self.assertFalse(
                report["target_bound_checker_command_matrix"]["pack_authorizes_restart"]
            )
            self.assertFalse(
                report["target_bound_checker_command_matrix"][
                    "clears_approved_runtime_evidence_missing"
                ]
            )
            self.assertFalse(report["parallel_capture_boundary"]["pack_authorizes_player_backed_window"])
            self.assertEqual(
                report["player_principal_window_composition"]["side_surface_role"],
                "optional_parallel_candidate_observations",
            )
            self.assertFalse(report["player_principal_window_composition"]["substitution_allowed"])

    def test_rejects_protected_live_server_output_root(self) -> None:
        result = run_pack(Path("/servidor/ark/ShooterGame"), "--json", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output-root must not write under protected server root", result.stderr)

    def test_rejects_existing_non_empty_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / RUN_ID
            output_dir.mkdir()
            (output_dir / "existing.txt").write_text("existing", encoding="utf-8")

            result = run_pack(Path(temp_dir), "--json", check=False)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output directory already exists and is not empty", result.stderr)


if __name__ == "__main__":
    unittest.main()
