"""Tests for check_obelisk_multi_surface_beta_capture_pack.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PREPARE = SCRIPT_DIR / "prepare_obelisk_multi_surface_beta_capture_pack.py"
CHECK = SCRIPT_DIR / "check_obelisk_multi_surface_beta_capture_pack.py"
RUN_ID = "pack-check-test"
BROAD_BETA_CAPTURE_WORKSHEET_FILE = "admin-commands-dino-tribe-buff-candidate-worksheet.json"
SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE = "simultaneous-side-lane-candidate-worksheet.json"
SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE = "single-player-full-sequence-candidate-worksheet.json"
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


def prepare_pack(output_root: Path) -> Path:
    subprocess.run(
        [
            sys.executable,
            str(PREPARE),
            "--instance",
            "arkserver",
            "--map",
            "Ragnarok",
            "--output-root",
            str(output_root),
            "--run-id",
            RUN_ID,
            "--json",
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return output_root / RUN_ID


def run_check(pack: Path, *extra: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), str(pack), *extra, "--json"],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def refresh_manifest_artifact(pack: Path, artifact_name: str) -> None:
    manifest = read_json(pack / "manifest.json")
    artifact_path = pack / artifact_name
    for artifact in manifest["artifacts"]:
        if artifact["name"] == artifact_name:
            artifact["sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
            artifact["size_bytes"] = artifact_path.stat().st_size
    manifest.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = hashlib.sha256(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    write_json(pack / "manifest.json", manifest)


def refresh_manifest_self(pack: Path, manifest: dict) -> None:
    manifest.pop("manifest_sha256", None)
    manifest["manifest_sha256"] = hashlib.sha256(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    write_json(pack / "manifest.json", manifest)


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


class CheckMultiSurfaceBetaCapturePackTests(unittest.TestCase):
    def test_accepts_generated_candidate_pack_without_progress_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            report = json.loads(run_check(pack).stdout)

            self.assertEqual(report["schema"], "obelisk.multi-surface-beta-capture-pack-check.v1")
            self.assertEqual(report["status"], "candidate_pack_validated")
            self.assertTrue(report["ready"])
            self.assertEqual(report["ready_scope"], "candidate_capture_pack_integrity_only")
            self.assertEqual(report["candidate_surface_count"], len(EXPECTED_SURFACES))
            self.assertEqual(report["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(report["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(report["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok")
            assert_beta_capture_interaction_boundary(
                self,
                report["beta_capture_interaction_boundary"],
            )
            self.assertEqual(report["approved_runtime_window_binding"]["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertTrue(
                report["approved_runtime_window_binding"]["same_window_as_player_principal_lifecycle"]
            )
            self.assertFalse(report["approved_runtime_window_binding"]["pack_authorizes_window"])
            self.assertFalse(report["approved_runtime_window_binding"]["window_substitution_allowed"])
            self.assertEqual(report["blockers"], [])
            self.assertTrue(report["candidate_only"])
            self.assertTrue(report["source_metadata_required"])
            self.assertEqual(
                report["source_metadata"]["schema"],
                "obelisk.multi-surface-beta-capture-source-metadata.v1",
            )
            self.assertFalse(report["source_metadata"]["source_ready"])
            self.assertFalse(report["source_metadata"]["source_material_counts_as_evidence"])
            self.assertEqual(report["candidate_only_metadata"]["classification"], "candidate_only_non_evidence")
            self.assertTrue(report["candidate_only_metadata"]["non_evidence"])
            self.assertFalse(report["candidate_only_metadata"]["counts_as_runtime_evidence"])
            self.assertFalse(report["candidate_only_metadata"]["downstream_unlock_allowed"])
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
            self.assertTrue(
                report["parallel_capture_boundary"]["separate_player_backed_window_approval_required"]
            )
            self.assertFalse(report["parallel_capture_boundary"]["pack_authorizes_player_backed_window"])
            self.assertFalse(
                report["parallel_capture_boundary"][
                    "side_lane_collection_can_replace_player_principal_evidence"
                ]
            )
            self.assertEqual(
                report["player_principal_window_composition"]["side_surface_role"],
                "optional_parallel_candidate_observations",
            )
            self.assertTrue(
                report["player_principal_window_composition"][
                    "side_surfaces_non_evidence_until_own_checker_acceptance"
                ]
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
            self.assertTrue(broad_path["requires_checker_acceptance"])
            self.assertTrue(broad_path["requires_player_principal_triplet"])
            self.assertFalse(broad_path["counts_as_runtime_evidence"])
            self.assertFalse(broad_path["counts_as_sdk_progress"])
            self.assertFalse(broad_path["runtime_ready"])
            self.assertFalse(broad_path["public_sdk_ready"])
            self.assertEqual(
                [surface["id"] for surface in broad_path["surfaces"]],
                BROAD_BETA_CAPTURE_SURFACES,
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
            worksheet = read_json(pack / BROAD_BETA_CAPTURE_WORKSHEET_FILE)
            self.assertEqual(worksheet["surface_ids"], BROAD_BETA_CAPTURE_SURFACES)
            self.assertEqual(worksheet["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(
                [row["surface_id"] for row in worksheet["worksheet_rows"]],
                BROAD_BETA_CAPTURE_SURFACES,
            )
            for row in worksheet["worksheet_rows"]:
                self.assertEqual(row["observation_rows"], [])
                self.assertTrue(row["candidate_only"], row["surface_id"])
                self.assertTrue(row["non_evidence"], row["surface_id"])
                self.assertFalse(row["counts_as_runtime_evidence"], row["surface_id"])
            simultaneous_worksheet = read_json(pack / SIMULTANEOUS_BETA_CAPTURE_WORKSHEET_FILE)
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
            single_player_worksheet = read_json(
                pack / SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE
            )
            self.assertEqual(
                single_player_worksheet["surface_ids"],
                SINGLE_PLAYER_ROUTE_SURFACES,
            )
            self.assertEqual(
                [row["surface_id"] for row in single_player_worksheet["worksheet_rows"]],
                SINGLE_PLAYER_ROUTE_SURFACES,
            )
            self.assertEqual(
                single_player_worksheet["single_player_parallel_capture_sequence_id"],
                "single_player_parallel_side_lane_capture_sequence",
            )
            self.assertTrue(single_player_worksheet["primary_player_principal_row_included"])
            self.assertTrue(single_player_worksheet["side_lane_rows_included"])
            self.assertFalse(single_player_worksheet["counts_as_runtime_evidence"])
            primary_row = single_player_worksheet["worksheet_rows"][0]
            self.assertEqual(primary_row["surface_id"], "player_principal_lifecycle")
            self.assertEqual(primary_row["observation_rows"], [])
            primary_field_ids = {
                field["field_id"] for field in primary_row["worksheet_fields"]
            }
            self.assertIn("session_start_observer_role", primary_field_ids)
            self.assertIn("checkjoin_rejected_start_shape", primary_field_ids)
            self.assertIn("session_end_correlation_shape", primary_field_ids)
            self.assertFalse(primary_row["counts_as_runtime_evidence"])
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
                self.assertFalse(phase["clears_approved_runtime_evidence_missing"], phase["phase_id"])
                self.assertFalse(phase["pack_authorizes_discord"], phase["phase_id"])
                self.assertFalse(phase["authorizes_live_log_reads"], phase["phase_id"])
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
                for command_row in phase["checker_commands"]:
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
                    self.assertFalse(
                        command_row["target_bound_checker_command"]["pack_authorizes_discord"],
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
            self.assertFalse(command_matrix["raw_player_text_capture_allowed"])
            self.assertFalse(command_matrix["secrets_or_webhook_retention_allowed"])
            self.assertFalse(command_matrix["pack_authorizes_restart"])
            self.assertFalse(command_matrix["pack_authorizes_discord"])
            self.assertFalse(command_matrix["counts_as_runtime_evidence"])
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
            self.assertEqual(
                [row["id"] for row in parallel_matrix["surface_rows"]],
                PARALLEL_BETA_CAPTURE_SURFACES,
            )
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
                self.assertTrue(row["side_lane"], row["id"])
                self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok", row["id"])
                self.assertTrue(row["exact_approved_runtime_window_required"], row["id"])
                self.assertTrue(row["no_restart_required"], row["id"])
                self.assertTrue(row["tester_actions_do_not_require_restart"], row["id"])
                self.assertFalse(row["restart_required"], row["id"])
                self.assertFalse(row["server_restart_required"], row["id"])
                self.assertFalse(row["counts_as_sdk_progress"], row["id"])
                self.assertFalse(row["counts_as_p0_progress"], row["id"])
                self.assertEqual(row["operator_next_action"], row["lead_next_action"], row["id"])
                self.assertTrue(row["tester_brief"], row["id"])
            self.assertFalse(report["approved_runtime_evidence_present"])
            self.assertFalse(report["approved_runtime_evidence_ready"])
            self.assertFalse(report["counts_as_approved_runtime_evidence"])
            self.assertFalse(report["counts_as_runtime_evidence"])
            self.assertFalse(report["counts_as_sdk_progress"])
            self.assertFalse(report["counts_as_p0_progress"])
            self.assertFalse(report["replaces_player_principal_evidence"])
            self.assertFalse(report["replaces_player_principal_triplet"])
            self.assertFalse(report["substitutes_for_player_principal_lifecycle_evidence"])
            self.assertFalse(report["substitutes_for_player_principal_lifecycle_triplet"])
            self.assertFalse(report["player_principal_lifecycle_evidence_substitution_allowed"])
            self.assertFalse(report["approved_runtime_evidence_substitution_allowed"])
            self.assertFalse(report["primary_evidence_substitution_allowed"])
            self.assertFalse(report["side_lane_counts_toward_sdk"])
            self.assertFalse(report["side_lane_counts_toward_p0"])
            self.assertFalse(
                report["non_substitution_flags"]["side_lane_collection_can_replace_player_principal_evidence"]
            )
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["stable_sdk_ready"])
            self.assertEqual(report["current_route_blocker"], "approved_runtime_evidence_missing")
            self.assertEqual(
                report["next_required_artifact"],
                "approved_runtime_principal_lifecycle_evidence_bundle",
            )

            plan = read_json(pack / "multi-surface-capture-plan.json")
            manifest = read_json(pack / "manifest.json")
            assert_beta_capture_interaction_boundary(
                self,
                manifest["beta_capture_interaction_boundary"],
            )
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
            self.assertEqual({surface["id"] for surface in plan["capture_surfaces"]}, EXPECTED_SURFACES)
            self.assertEqual(plan["candidate_only_metadata"], report["candidate_only_metadata"])
            self.assertEqual(
                plan["player_principal_window_composition"],
                report["player_principal_window_composition"],
            )
            self.assertEqual(plan["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(plan["approved_runtime_window_binding"], report["approved_runtime_window_binding"])
            self.assertEqual(plan["broad_beta_capture_pack_path"], broad_path)
            self.assertEqual(plan["parallel_beta_capture_side_lane_matrix"], parallel_matrix)
            self.assertEqual(plan["single_player_parallel_capture_sequence"], sequence)
            self.assertEqual(plan["target_bound_checker_command_matrix"], command_matrix)
            self.assertEqual(plan["text_privacy_boundary"], report["text_privacy_boundary"])
            self.assertEqual(
                [surface["priority"] for surface in plan["capture_surfaces"]],
                list(range(1, len(EXPECTED_SURFACES) + 1)),
            )
            for surface in plan["capture_surfaces"]:
                self.assertTrue(surface["requires_player_principal_triplet"], surface["id"])
                self.assertTrue(surface["blocked_by_player_principal_evidence"], surface["id"])
                self.assertEqual(surface["candidate_only_metadata"], plan["candidate_only_metadata"], surface["id"])
                self.assertEqual(surface["parallel_capture_boundary"], plan["parallel_capture_boundary"], surface["id"])
                self.assertEqual(
                    surface["player_principal_window_composition"],
                    plan["player_principal_window_composition"],
                    surface["id"],
                )
                expected_side_lane = surface["id"] != "player_principal_lifecycle"
                self.assertEqual(surface["optional_parallel_candidate_observation"], expected_side_lane, surface["id"])
                self.assertEqual(
                    surface["parallel_with_player_principal_lifecycle_window"],
                    expected_side_lane,
                    surface["id"],
                )
                self.assertEqual(surface["target_binding"]["instance"], "arkserver", surface["id"])
                self.assertEqual(surface["target_binding"]["map"], "Ragnarok", surface["id"])
                self.assertEqual(surface["target_binding"]["binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
                self.assertEqual(surface["target_binding_id"], "instance=arkserver|map=Ragnarok", surface["id"])
                self.assertEqual(
                    surface["approved_runtime_window_binding"],
                    report["approved_runtime_window_binding"],
                    surface["id"],
                )
                self.assertTrue(
                    surface["operator_tester_action_metadata"]["same_approved_runtime_window_required"],
                    surface["id"],
                )
                self.assertEqual(
                    surface["operator_tester_action_metadata"]["tester_action"],
                    surface["tester_action"],
                    surface["id"],
                )
                self.assertFalse(
                    surface["operator_tester_action_metadata"]["substitution_allowed"],
                    surface["id"],
                )
                self.assertTrue(surface["checker_inputs_satisfied_by_artifacts"], surface["id"])
                self.assertEqual(
                    surface["post_capture_checker_command"],
                    ["python3", surface["checker"], *surface["checker_args"]],
                )
                self.assertEqual(surface["current_route_blocker"], "approved_runtime_evidence_missing")
                self.assertFalse(surface["approved_runtime_evidence_present"], surface["id"])
                self.assertFalse(surface["approved_runtime_evidence_ready"], surface["id"])

            matrix = read_json(pack / "checker-command-matrix.json")
            self.assertEqual(matrix["target"], {"instance": "arkserver", "map": "Ragnarok"})
            self.assertEqual(matrix["target_binding_id"], "instance=arkserver|map=Ragnarok")
            self.assertEqual(matrix["target_binding"], plan["target_binding"])
            self.assertEqual(matrix["approved_runtime_window_binding"], plan["approved_runtime_window_binding"])
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
            by_id = {surface["id"]: surface for surface in matrix["surfaces"]}
            self.assertEqual(by_id["player_principal_lifecycle"]["target_binding"]["map"], "Ragnarok")
            self.assertEqual(
                by_id["inventory_custom_filter_array_boundary"]["command"],
                [
                    "python3",
                    "scripts/check_inventory_custom_filter_array_boundary.py",
                    "--snapshot",
                    "<offline-inventory-custom-filter-array-boundary-snapshot.json>",
                    "--json",
                ],
            )
            self.assertEqual(
                {
                    row["checker_input"]
                    for row in by_id["transfer_baccept"]["required_checker_artifacts"]
                },
                {
                    "<offline-transfer-baccept-pack-root>",
                    "<offline-transfer-baccept-policy-slice.json>",
                    "<offline-transfer-baccept-policy-slice-sha256>",
                },
            )
            for row in by_id["transfer_baccept"]["required_checker_artifacts"]:
                self.assertEqual(row["target_binding_id"], "instance=arkserver|map=Ragnarok")
                self.assertEqual(row["target_binding"], by_id["transfer_baccept"]["target_binding"])
                self.assertTrue(row["same_approved_runtime_window_required"])
                self.assertEqual(
                    row["approved_runtime_window_binding"],
                    by_id["transfer_baccept"]["approved_runtime_window_binding"],
                )
                self.assertTrue(row["target_binding"]["mismatched_target_rejects_pack"])
            self.assertEqual(
                by_id["player_principal_lifecycle"]["command"],
                [
                    "python3",
                    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                    "<approved-runtime-principal-lifecycle-evidence-manifest.json>",
                    "--json",
                ],
            )
            self.assertEqual(
                by_id["transfer_baccept"]["command"],
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
                command_by_id["transfer_baccept"]["resolved_checker_command_template"],
            )
            self.assertEqual(
                by_id["transfer_baccept"]["target_bound_checker_command"],
                command_by_id["transfer_baccept"],
            )
            self.assertEqual(
                by_id["item_return_only"]["command"],
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
                by_id["inventory_action_compact_intake"]["command"],
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

    def test_accepts_manifest_path_as_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            report = json.loads(run_check(pack / "manifest.json").stdout)

            self.assertTrue(report["ready"])
            self.assertEqual(report["pack_root"], str(pack))

    def test_rejects_wrong_expected_target_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))

            result = run_check(
                pack,
                "--expected-instance",
                "arkserver",
                "--expected-map",
                "TheIsland",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report["ready"])
            self.assertIn("manifest_target_expected_target_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_sdk_progress"])

    def test_rejects_cross_artifact_target_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            matrix["target"] = {"instance": "arkserver", "map": "TheIsland"}
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("matrix_target_expected_target_mismatch", report["blockers"])
            self.assertIn("matrix_target_mismatch", report["blockers"])

    def test_rejects_candidate_artifact_intake_target_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["target"] = {"instance": "arkserver", "map": "TheIsland"}
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("intake_target_expected_target_mismatch", report["blockers"])
            self.assertIn("intake_target_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_candidate_artifact_intake_side_lane_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "permissions_admin")
            target["counts_as_sdk_progress"] = True
            target["counts_as_runtime_evidence"] = True
            target["substitutes_for_player_principal_lifecycle_evidence"] = True
            intake["capture_session_constraints"]["do_not_send_discord"] = False
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("intake_constraint_not_true", report["blockers"])
            self.assertIn("intake_surface_false_flag_overclaim", report["blockers"])
            self.assertFalse(report["approved_runtime_evidence_ready"])

    def test_rejects_parallel_boundary_authorization_and_substitution_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["parallel_capture_boundary"]["pack_authorizes_player_backed_window"] = True
            intake["player_principal_window_composition"]["substitution_allowed"] = True
            intake["player_principal_window_composition"]["counts_as_sdk_progress"] = True
            intake["capture_session_constraints"]["pack_authorizes_player_backed_window"] = True
            inventory = next(surface for surface in intake["surfaces"] if surface["id"] == "inventory_action_compact_intake")
            inventory["parallel_capture_boundary"]["side_lane_collection_can_replace_player_principal_evidence"] = True
            inventory["player_principal_window_composition"][
                "side_surfaces_non_evidence_until_own_checker_acceptance"
            ] = False
            inventory["optional_parallel_candidate_observation"] = False
            inventory["parallel_with_player_principal_lifecycle_window"] = False
            inventory["packAuthorizesRuntimeObserver"] = True
            inventory["sideLaneCollectionCountsBeforeCheckerAcceptance"] = True
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("parallel_capture_boundary_mismatch", report["blockers"])
            self.assertIn("parallel_capture_boundary_flag_mismatch", report["blockers"])
            self.assertIn("player_principal_window_composition_mismatch", report["blockers"])
            self.assertIn("player_principal_window_composition_false_flag_overclaim", report["blockers"])
            self.assertIn("player_principal_window_composition_true_flag_missing", report["blockers"])
            self.assertIn("surface_optional_parallel_candidate_observation_mismatch", report["blockers"])
            self.assertIn("surface_parallel_with_player_principal_lifecycle_window_mismatch", report["blockers"])
            self.assertIn("intake_constraint_not_false", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["primary_evidence_substitution_allowed"])

    def test_rejects_single_player_sequence_route_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            sequence = plan["single_player_parallel_capture_sequence"]
            sequence["surface_ids"].append("unknown_side_lane")
            sequence["single_player_route_surface_ids"].append("unknown_side_lane")
            sequence["excluded_surface_ids"] = ["mission_copied_bool"]
            sequence["candidate_domain_ids"].append("unknown")
            sequence["single_player_route_constraints"]["pack_authorizes_discord"] = True
            sequence["single_player_route_constraints"][
                "side_lane_collection_before_primary_route_active_allowed"
            ] = True
            sequence["single_player_route_constraints"][
                "clears_approved_runtime_evidence_missing"
            ] = True
            phase = sequence["phases"][1]
            phase["phase_domain_ids"].append("mission")
            phase["pack_authorizes_discord"] = True
            phase["authorizes_live_log_reads"] = True
            phase["single_player_route_constraints"]["authorizes_live_log_reads"] = True
            phase["single_player_route_constraints"][
                "side_lane_collection_before_primary_route_active_allowed"
            ] = True
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("single_player_parallel_capture_sequence_surface_ids_mismatch", report["blockers"])
            self.assertIn("single_player_parallel_capture_sequence_route_surface_ids_mismatch", report["blockers"])
            self.assertIn("single_player_parallel_capture_sequence_excluded_surface_ids_mismatch", report["blockers"])
            self.assertIn("single_player_parallel_capture_sequence_domain_ids_mismatch", report["blockers"])
            self.assertIn("single_player_route_constraints_false_flag_overclaim", report["blockers"])
            self.assertIn("single_player_parallel_capture_sequence_phase_domain_ids_mismatch", report["blockers"])
            self.assertIn("single_player_parallel_capture_sequence_phase_false_flag_overclaim", report["blockers"])
            self.assertIn("single_player_phase_route_constraints_false_flag_overclaim", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["clears_approved_runtime_evidence_missing"])

    def test_rejects_authorization_alias_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["authorizesLiveLogReads"] = True
            intake["authorizesRuntimeCapture"] = True
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "permissions_admin")
            target["authorizesServerRestart"] = True
            target["capture_artifacts"][0]["authorizesDiscordSend"] = True
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn("$intake.authorizesLiveLogReads", flagged_paths)
            self.assertIn("$intake.authorizesRuntimeCapture", flagged_paths)
            self.assertIn("$intake.surfaces[1].authorizesServerRestart", flagged_paths)
            self.assertIn("$intake.surfaces[1].capture_artifacts[0].authorizesDiscordSend", flagged_paths)
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_beta_capture_interaction_boundary_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            boundary = manifest["beta_capture_interaction_boundary"]
            boundary["discord_or_beta_interactions_approve_live_actions"] = True
            boundary["non_claim_flags"]["button_clicks_count_as_sdk_progress"] = True
            refresh_manifest_self(pack, manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("beta_capture_interaction_boundary_mismatch", report["blockers"])
            self.assertIn("beta_capture_interaction_boundary_false_flag_overclaim", report["blockers"])
            self.assertIn(
                "beta_capture_interaction_boundary_non_claim_flag_overclaim",
                report["blockers"],
            )
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn(
                "$manifest.beta_capture_interaction_boundary.discord_or_beta_interactions_approve_live_actions",
                flagged_paths,
            )
            self.assertIn(
                "$manifest.beta_capture_interaction_boundary.non_claim_flags.button_clicks_count_as_sdk_progress",
                flagged_paths,
            )
            self.assertFalse(report["counts_as_sdk_progress"])
            self.assertFalse(report["public_sdk_ready"])

    def test_rejects_retained_webhook_secret_and_raw_text_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            candidate_path = pack / "permissions-admin-beta-capture-candidates.json"
            candidate = read_json(candidate_path)
            candidate["discord_webhook_url"] = "https://discord.com\x2fapi/webhooks/123456789/tokenValue"
            candidate["operator_secret"] = "super-secret-value"
            candidate["raw_player_text_sample"] = "player typed private command text"
            write_json(candidate_path, candidate)
            refresh_manifest_artifact(pack, "permissions-admin-beta-capture-candidates.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("forbidden_retained_discord_webhook_url", report["blockers"])
            self.assertIn("forbidden_retained_sensitive_text_assignment", report["blockers"])
            self.assertIn("forbidden_retained_sensitive_text_value", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "forbidden_retained_sensitive_text_value"
            }
            self.assertIn(
                "$artifact_json.permissions-admin-beta-capture-candidates.json.operator_secret",
                flagged_paths,
            )
            self.assertIn(
                "$artifact_json.permissions-admin-beta-capture-candidates.json.raw_player_text_sample",
                flagged_paths,
            )
            self.assertFalse(report["ready"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_manifest_target_binding_without_mismatch_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            manifest["target_binding"]["mismatched_target_rejects_pack"] = False
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest_target_binding_mismatched_target_rejects_pack_not_true", report["blockers"])
            self.assertFalse(report["runtime_ready"])

    def test_rejects_nondeterministic_manifest_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            manifest["output_dir"] = str(pack)
            manifest["artifacts"][0]["path"] = str(pack / manifest["artifacts"][0]["name"])
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest_output_dir_not_allowed", report["blockers"])
            self.assertIn("manifest_artifact_path_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_target_binding_id_drift_with_same_target_tuple(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            manifest["target_binding"]["binding_id"] = "instance=arkserver|map=TheIsland"
            manifest["target_binding_id"] = "instance=arkserver|map=TheIsland"
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest_target_binding_binding_id_mismatch", report["blockers"])
            self.assertIn("manifest_target_binding_id_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_per_surface_target_binding_id_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            target = next(surface for surface in plan["capture_surfaces"] if surface["id"] == "permissions_admin")
            target["target_binding_id"] = "instance=arkserver|map=TheIsland"
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plan_surface_target_binding_id_mismatch", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "plan_surface_target_binding_id_mismatch"
            }
            self.assertIn("$plan.capture_surfaces[1].target_binding_id", flagged_paths)
            self.assertFalse(report["side_lane_counts_toward_sdk"])

    def test_rejects_surface_and_artifact_target_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            surface = next(item for item in plan["capture_surfaces"] if item["id"] == "dino_scalar")
            surface["target_binding"]["map"] = "TheIsland"
            surface["capture_artifacts"][0]["target_binding"]["instance"] = "other-instance"
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plan_surface_target_binding_expected_target_mismatch", report["blockers"])
            self.assertIn("capture_artifact_target_binding_expected_target_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_target_binding_alias_fields_even_when_canonical_binding_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            surface = next(item for item in intake["surfaces"] if item["id"] == "permissions_admin")
            surface["targetBinding"] = {
                "instance": "arkserver",
                "map": "TheIsland",
                "bindingId": "instance=arkserver|map=TheIsland",
            }
            surface["capture_artifacts"][0]["targetBindingId"] = "instance=arkserver|map=TheIsland"
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("target_binding_alias_not_allowed", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "target_binding_alias_not_allowed"
            }
            self.assertIn("$intake.surfaces[1].targetBinding", flagged_paths)
            self.assertIn("$intake.surfaces[1].targetBinding.bindingId", flagged_paths)
            self.assertIn("$intake.surfaces[1].capture_artifacts[0].targetBindingId", flagged_paths)
            self.assertFalse(report["primary_evidence_substitution_allowed"])

    def test_rejects_approved_runtime_window_binding_id_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            plan["approved_runtime_window_binding"]["target_binding_id"] = "instance=arkserver|map=TheIsland"
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plan_approved_runtime_window_binding_mismatch", report["blockers"])
            self.assertIn("plan_approved_runtime_window_binding_target_binding_id_mismatch", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "plan_approved_runtime_window_binding_target_binding_id_mismatch"
            }
            self.assertIn("$plan.approved_runtime_window_binding.target_binding_id", flagged_paths)
            self.assertFalse(report["counts_as_approved_runtime_evidence"])

    def test_rejects_approved_window_binding_and_action_metadata_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["approved_runtime_window_binding"]["target_binding"]["map"] = "TheIsland"
            intake["approved_runtime_window_binding"]["target_binding_id"] = "instance=arkserver|map=TheIsland"
            intake["capture_session_constraints"]["pack_authorizes_approved_runtime_window"] = True

            target = next(surface for surface in intake["surfaces"] if surface["id"] == "transfer_baccept")
            target["tester_action"] = "use a different unbound transfer path"
            target["approved_runtime_window_binding"]["target_binding"]["instance"] = "other-instance"
            target["operator_tester_action_metadata"]["same_approved_runtime_window_required"] = False
            target["operator_tester_action_metadata"]["tester_action"] = ""
            target["operator_tester_action_metadata"]["packAuthorizesApprovedRuntimeWindow"] = True
            target["capture_artifacts"][0]["approved_runtime_window_binding"]["target_binding_id"] = (
                "instance=arkserver|map=TheIsland"
            )
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("intake_approved_runtime_window_binding_mismatch", report["blockers"])
            self.assertIn("intake_constraint_not_false", report["blockers"])
            self.assertIn("surface_tester_action_binding_mismatch", report["blockers"])
            self.assertIn("surface_approved_runtime_window_binding_mismatch", report["blockers"])
            self.assertIn("surface_operator_tester_action_metadata_mismatch", report["blockers"])
            self.assertIn("surface_operator_tester_action_metadata_true_flag_missing", report["blockers"])
            self.assertIn("surface_operator_tester_action_metadata_text_missing", report["blockers"])
            self.assertIn("capture_artifact_approved_runtime_window_binding_mismatch", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_required_checker_artifact_target_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            target = next(surface for surface in matrix["surfaces"] if surface["id"] == "transfer_baccept")
            target["required_checker_artifacts"][0]["target_binding"]["map"] = "TheIsland"
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("surface_required_checker_artifacts_mismatch", report["blockers"])
            self.assertFalse(report["primary_evidence_substitution_allowed"])

    def test_rejects_required_checker_artifact_matrix_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            target = next(surface for surface in matrix["surfaces"] if surface["id"] == "transfer_baccept")
            target["required_checker_artifacts"] = target["required_checker_artifacts"][:-1]
            target["checker_inputs_satisfied_by_artifacts"] = False
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("surface_required_checker_artifacts_mismatch", report["blockers"])
            self.assertIn("surface_checker_inputs_satisfied_by_artifacts_not_true", report["blockers"])
            self.assertFalse(report["replaces_player_principal_evidence"])

    def test_rejects_target_bound_command_matrix_live_path_and_authorization_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            command_matrix = matrix["target_bound_checker_command_matrix"]
            command_matrix["raw_player_text_retention_allowed"] = True
            command_matrix["secrets_or_webhook_retention_allowed"] = True
            command_matrix["pack_authorizes_restart"] = True
            command_matrix["pack_authorizes_discord"] = True
            command_matrix["clears_approved_runtime_evidence_missing"] = True
            row = next(item for item in command_matrix["rows"] if item["surface_id"] == "transfer_baccept")
            row["resolved_checker_command_template"][3] = "/servidor/ark/ShooterGame/Saved/Logs/Obelisk.log"
            row["raw_player_text_capture_allowed"] = True
            row["secrets_or_webhook_retention_allowed"] = True
            row["pack_authorizes_restart"] = True
            row["pack_authorizes_discord"] = True
            row["clears_approved_runtime_evidence_missing"] = True

            surface = next(item for item in matrix["surfaces"] if item["id"] == "transfer_baccept")
            surface["resolved_checker_command_template"][3] = "/servidor/ark/ShooterGame/Saved/Logs/Obelisk.log"
            surface["target_bound_checker_command"]["secrets_or_webhook_retention_allowed"] = True
            surface["target_bound_checker_command"]["pack_authorizes_discord"] = True
            surface["target_bound_checker_command"]["clears_approved_runtime_evidence_missing"] = True
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("target_bound_checker_command_matrix_mismatch", report["blockers"])
            self.assertIn(
                "target_bound_checker_command_matrix_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "target_bound_checker_command_matrix_row_resolved_checker_command_template_live_path_fragment",
                report["blockers"],
            )
            self.assertIn(
                "target_bound_checker_command_matrix_row_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "matrix_surface_resolved_checker_command_template_mismatch",
                report["blockers"],
            )
            self.assertIn(
                "matrix_surface_resolved_checker_command_template_live_path_fragment",
                report["blockers"],
            )
            self.assertIn(
                "matrix_surface_target_bound_checker_command_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["raw_player_text_retention_allowed"])
            self.assertFalse(report["secrets_or_webhook_retention_allowed"])
            self.assertFalse(report["clears_approved_runtime_evidence_missing"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_candidate_artifact_intake_redaction_and_live_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            surface = next(item for item in intake["surfaces"] if item["id"] == "permissions_admin")
            artifact = surface["capture_artifacts"][0]
            artifact["path_template"] = "candidate-artifacts/servidor/ark/offline-permissions-admin-beta-capture.json"
            artifact["artifact_intake_constraints"]["path_template_must_not_name_live_server_paths"] = False
            artifact["redaction_policy"]["must_redact"] = ["raw_player_text", "secrets", "private_player_data"]
            artifact["redaction_note"] = "do not retain raw player text, secrets, or private player data"
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("capture_artifact_path_template_live_path_fragment", report["blockers"])
            self.assertIn("artifact_intake_constraint_not_true", report["blockers"])
            self.assertIn("redaction_policy_mismatch", report["blockers"])
            self.assertIn("capture_artifact_redaction_note_missing_token", report["blockers"])
            self.assertFalse(report["primary_evidence_substitution_allowed"])

    def test_rejects_candidate_artifact_template_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            surface = next(item for item in intake["surfaces"] if item["id"] == "permissions_admin")
            artifact = surface["capture_artifacts"][0]
            artifact["path_template"] = (
                "candidate-artifacts\\..\\escaped\\offline-permissions-admin-beta-capture.json"
            )
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("capture_artifact_path_template_unsafe", report["blockers"])
            self.assertIn("capture_artifact_path_template_root_mismatch", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "capture_artifact_path_template_unsafe"
            }
            self.assertIn("$intake.surfaces[1].capture_artifacts[0].path_template", flagged_paths)
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_false_progress_and_readiness_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["approvedRuntimeEvidenceReady"] = True
            intake["sideLaneCandidatesClearApprovedRuntimeEvidenceMissing"] = True
            intake["playerPrincipalLifecycleEvidenceSubstitutionAllowed"] = True
            intake["passiveEvidenceReady"] = True
            intake["stale_readiness_accepted"] = "accepted"
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "buff_status")
            target["sdkProgress"] = True
            target["rawPlayerTextRetentionAllowed"] = True
            target["captureReady"] = True
            target["countsTowardSdk"] = True
            target["passive_snapshot_ready"] = True
            target["staleSourceStatus"] = "ready"
            target["targetSetStatus"] = "accepted"
            target["targetSetProgress"] = 1
            target["supportTierReady"] = "release_supported"
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn("$intake.approvedRuntimeEvidenceReady", flagged_paths)
            self.assertIn("$intake.sideLaneCandidatesClearApprovedRuntimeEvidenceMissing", flagged_paths)
            self.assertIn("$intake.playerPrincipalLifecycleEvidenceSubstitutionAllowed", flagged_paths)
            self.assertIn("$intake.passiveEvidenceReady", flagged_paths)
            self.assertIn("$intake.stale_readiness_accepted", flagged_paths)
            self.assertIn("$intake.surfaces[6].sdkProgress", flagged_paths)
            self.assertIn("$intake.surfaces[6].rawPlayerTextRetentionAllowed", flagged_paths)
            self.assertIn("$intake.surfaces[6].captureReady", flagged_paths)
            self.assertIn("$intake.surfaces[6].countsTowardSdk", flagged_paths)
            self.assertIn("$intake.surfaces[6].passive_snapshot_ready", flagged_paths)
            self.assertIn("$intake.surfaces[6].staleSourceStatus", flagged_paths)
            self.assertIn("$intake.surfaces[6].targetSetStatus", flagged_paths)
            self.assertIn("$intake.surfaces[6].targetSetProgress", flagged_paths)
            self.assertIn("$intake.surfaces[6].supportTierReady", flagged_paths)

    def test_rejects_missing_source_metadata_for_candidate_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "dino_scalar")
            target.pop("source_metadata", None)
            target.pop("source_metadata_required", None)
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source_metadata_missing_or_invalid", report["blockers"])
            self.assertIn("source_metadata_required_flag_missing", report["blockers"])

    def test_rejects_source_readiness_alias_as_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "tribe_scalar")
            target["sourceReady"] = True
            target["sourceAccepted"] = True
            target["sourceMaterialCountsAsEvidence"] = True
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn("$intake.surfaces[5].sourceReady", flagged_paths)
            self.assertIn("$intake.surfaces[5].sourceAccepted", flagged_paths)
            self.assertIn("$intake.surfaces[5].sourceMaterialCountsAsEvidence", flagged_paths)
            self.assertFalse(report["counts_as_sdk_progress"])

    def test_rejects_status_aliases_and_textual_readiness_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            intake = read_json(pack / "candidate-artifact-intake.json")
            intake["sdk_status"] = "1/12"
            intake["p0_progress_contribution"] = 1
            target = next(surface for surface in intake["surfaces"] if surface["id"] == "permissions_admin")
            target["approved_runtime_evidence_status"] = "accepted"
            target["runtime_evidence_progress_contribution"] = 1
            target["live_authorization_status"] = "authorized"
            write_json(pack / "candidate-artifact-intake.json", intake)
            refresh_manifest_artifact(pack, "candidate-artifact-intake.json")

            readme = pack / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\nThis candidate pack is public SDK ready and authorizes live log reads.\n",
                encoding="utf-8",
            )
            refresh_manifest_artifact(pack, "README.md")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertIn("promotional_claim_text_overclaim", report["blockers"])
            alias_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn("$intake.sdk_status", alias_paths)
            self.assertIn("$intake.p0_progress_contribution", alias_paths)
            self.assertIn("$intake.surfaces[1].approved_runtime_evidence_status", alias_paths)
            self.assertIn("$intake.surfaces[1].runtime_evidence_progress_contribution", alias_paths)
            self.assertIn("$intake.surfaces[1].live_authorization_status", alias_paths)
            text_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "promotional_claim_text_overclaim"
            }
            self.assertTrue(
                any(path.startswith("$artifact_text.README.md:") for path in text_paths),
                text_paths,
            )
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["authorizes_live_log_reads"])

    def test_rejects_single_player_sequence_clearance_and_raw_text_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            sequence = manifest["single_player_parallel_capture_sequence"]
            sequence["clears_approved_runtime_evidence_missing"] = True
            sequence["raw_player_text_retention_allowed"] = True
            sequence["secrets_or_webhook_retention_allowed"] = True
            sequence["phases"][-1]["clears_approved_runtime_evidence_missing"] = True
            sequence["phases"][-1]["secretsOrWebhookRetentionAllowed"] = True
            sequence["phases"][-1]["rawPlayerTextCaptureAllowed"] = True
            sequence["phases"][-1]["text_privacy_boundary"][
                "raw_player_text_capture_allowed"
            ] = True
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("single_player_parallel_capture_sequence_mismatch", report["blockers"])
            self.assertIn(
                "single_player_parallel_capture_sequence_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "single_player_parallel_capture_sequence_phase_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn("text_privacy_boundary_false_flag_overclaim", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            flagged_paths = {
                item["path"]
                for item in report["blocker_details"]
                if item["reason"] == "false_progress_readiness_flag_overclaim"
            }
            self.assertIn(
                "$manifest.single_player_parallel_capture_sequence.clears_approved_runtime_evidence_missing",
                flagged_paths,
            )
            self.assertIn(
                "$manifest.single_player_parallel_capture_sequence.raw_player_text_retention_allowed",
                flagged_paths,
            )
            self.assertIn(
                "$manifest.single_player_parallel_capture_sequence.secrets_or_webhook_retention_allowed",
                flagged_paths,
            )
            self.assertIn(
                "$manifest.single_player_parallel_capture_sequence.phases[5].secretsOrWebhookRetentionAllowed",
                flagged_paths,
            )
            self.assertIn(
                "$manifest.single_player_parallel_capture_sequence.phases[5].rawPlayerTextCaptureAllowed",
                flagged_paths,
            )
            self.assertFalse(report["clears_approved_runtime_evidence_missing"])

    def test_rejects_text_claim_that_pack_clears_runtime_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            readme = pack / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\nThis candidate pack clears approved_runtime_evidence_missing.\n",
                encoding="utf-8",
            )
            refresh_manifest_artifact(pack, "README.md")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("blocker_clearance_text_overclaim", report["blockers"])
            self.assertFalse(report["clears_approved_runtime_evidence_missing"])

    def test_rejects_primary_evidence_substitution_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            non_claim = read_json(pack / "non-claim-manifest.json")
            target = next(surface for surface in non_claim["surface_non_claims"] if surface["id"] == "player_principal_lifecycle")
            target["primary_evidence_substitution_allowed"] = True
            target["replaces_player_principal_triplet"] = True
            write_json(pack / "non-claim-manifest.json", non_claim)
            refresh_manifest_artifact(pack, "non-claim-manifest.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non_claim_manifest_surface_false_flag_overclaim", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["approved_runtime_evidence_substitution_allowed"])

    def test_rejects_artifact_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            (pack / "operator-runbook.md").write_text("tampered\n", encoding="utf-8")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(report["ready"])
            self.assertIn("manifest_artifact_sha256_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_sdk_progress"])

    def test_rejects_non_claim_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            non_claim = read_json(pack / "non-claim-manifest.json")
            non_claim["surface_non_claims"][0]["counts_as_sdk_progress"] = True
            write_json(pack / "non-claim-manifest.json", non_claim)
            refresh_manifest_artifact(pack, "non-claim-manifest.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non_claim_manifest_surface_false_flag_overclaim", report["blockers"])
            self.assertFalse(report["approved_runtime_evidence_present"])

    def test_rejects_duplicate_manifest_artifact_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            manifest["artifacts"].append(dict(manifest["artifacts"][0]))
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("manifest_artifacts_duplicate_entries", report["blockers"])

    def test_rejects_unexpected_pack_directory_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            (pack / "unexpected-dir").mkdir()

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pack_root_unexpected_entries", report["blockers"])

    def test_rejects_checker_matrix_player_principal_guardrail_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            matrix["surfaces"][0]["requires_player_principal_triplet"] = False
            matrix["surfaces"][1]["command"] = ["python3", "scripts/check_permissions_admin_public_readiness.py"]
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("matrix_surface_required_true_flag_missing", report["blockers"])
            self.assertIn("surface_checker_command_mismatch", report["blockers"])

    def test_rejects_stale_default_only_checker_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            target = next(surface for surface in matrix["surfaces"] if surface["id"] == "transfer_baccept")
            target["command"] = ["python3", "scripts/check_transfer_baccept_readiness.py", "--json"]
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("surface_checker_command_mismatch", report["blockers"])
            self.assertFalse(report["runtime_ready"])

    def test_rejects_duplicate_capture_surface_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            plan["capture_surfaces"].append(dict(plan["capture_surfaces"][0]))
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("plan_capture_surfaces_duplicate_ids", report["blockers"])
            self.assertIn("plan_capture_surfaces_duplicate_priorities", report["blockers"])
            self.assertIn("plan_capture_surfaces_count_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_sdk_progress"])

    def test_rejects_stale_surface_checker_binding_even_when_command_is_self_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            plan = read_json(pack / "multi-surface-capture-plan.json")
            target = next(surface for surface in plan["capture_surfaces"] if surface["id"] == "transfer_baccept")
            target["checker"] = "scripts/check_transfer_scriptstruct_readiness.py"
            target["post_capture_checker_command"] = ["python3", target["checker"], "--json"]
            write_json(pack / "multi-surface-capture-plan.json", plan)
            refresh_manifest_artifact(pack, "multi-surface-capture-plan.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("surface_checker_binding_mismatch", report["blockers"])
            self.assertIn("surface_checker_command_mismatch", report["blockers"])
            self.assertFalse(report["runtime_ready"])

    def test_rejects_candidate_metadata_and_next_action_group_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            matrix = read_json(pack / "checker-command-matrix.json")
            matrix["candidate_only_metadata"]["counts_as_runtime_evidence"] = True
            inventory_group = next(group for group in matrix["next_action_groups"] if group["id"] == "inventory_item_candidates")
            inventory_group["surface_ids"].remove("item_return_only")
            inventory_group["counts_as_sdk_progress"] = True
            write_json(pack / "checker-command-matrix.json", matrix)
            refresh_manifest_artifact(pack, "checker-command-matrix.json")

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("candidate_only_metadata_mismatch", report["blockers"])
            self.assertIn("next_action_groups_mismatch", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_broad_beta_capture_pack_path_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            manifest["broad_beta_capture_pack_path"]["surface_ids"].remove("buff_status")
            manifest["broad_beta_capture_pack_path"]["counts_as_runtime_evidence"] = True
            manifest["broad_beta_capture_pack_path"]["runtime_ready"] = True
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("broad_beta_capture_pack_path_mismatch", report["blockers"])
            self.assertIn("broad_beta_capture_pack_path_surface_ids_mismatch", report["blockers"])
            self.assertIn("broad_beta_capture_pack_path_false_flag_overclaim", report["blockers"])
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_parallel_side_lane_matrix_target_and_status_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            manifest = read_json(pack / "manifest.json")
            matrix = manifest["parallel_beta_capture_side_lane_matrix"]
            matrix["surface_ids"].remove("transfer_scriptstruct")
            matrix["counts_as_sdk_progress"] = True
            matrix["primary_evidence_substitution_allowed"] = True
            matrix["surface_rows"][0]["target_binding"]["map"] = "TheIsland"
            matrix["surface_rows"][0]["target_binding_id"] = "instance=arkserver|map=TheIsland"
            matrix["surface_rows"][0]["counts_as_runtime_evidence"] = True
            matrix["domain_rows"][-1]["counts_as_sdk_progress"] = True
            matrix["domain_rows"][-1]["restart_required"] = True
            matrix["domain_rows"][-1]["lead_next_action"] = ""
            matrix["domain_rows"][-1]["target_binding_id"] = "instance=arkserver|map=TheIsland"
            manifest.pop("manifest_sha256", None)
            manifest["manifest_sha256"] = hashlib.sha256(
                (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
            ).hexdigest()
            write_json(pack / "manifest.json", manifest)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("parallel_beta_capture_side_lane_matrix_mismatch", report["blockers"])
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_surface_ids_mismatch",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_surface_target_binding_expected_target_mismatch",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_surface_target_binding_id_mismatch",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_surface_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_domain_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_domain_text_missing",
                report["blockers"],
            )
            self.assertIn(
                "parallel_beta_capture_side_lane_matrix_domain_target_binding_id_mismatch",
                report["blockers"],
            )
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["counts_as_sdk_progress"])

    def test_rejects_single_player_full_sequence_worksheet_primary_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            worksheet_path = pack / SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE
            worksheet = read_json(worksheet_path)
            primary_row = worksheet["worksheet_rows"][0]
            primary_row["worksheet_fields"] = [
                field
                for field in primary_row["worksheet_fields"]
                if field.get("field_id") != "checkjoin_rejected_start_shape"
            ]
            primary_row["observation_rows"] = [
                {
                    "approved_window_id": "window-1",
                    "checkjoin_rejected_start_shape": "CheckJoinInProgress(1,0)",
                }
            ]
            primary_row["counts_as_runtime_evidence"] = True
            worksheet["authorizes_live_log_reads"] = True
            write_json(worksheet_path, worksheet)
            refresh_manifest_artifact(pack, SINGLE_PLAYER_PARALLEL_CAPTURE_WORKSHEET_FILE)

            result = run_check(pack, check=False)
            report = json.loads(result.stdout)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet_mismatch",
                report["blockers"],
            )
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet_primary_fields_missing",
                report["blockers"],
            )
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet_observation_rows_not_blank",
                report["blockers"],
            )
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet_row_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet_false_flag_overclaim",
                report["blockers"],
            )
            self.assertIn("false_progress_readiness_flag_overclaim", report["blockers"])
            self.assertFalse(report["counts_as_runtime_evidence"])

    def test_rejects_protected_live_server_pack_path(self) -> None:
        result = run_check(Path("/servidor/ark/ShooterGame"), check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pack root must not read from protected server root", result.stderr)

    def test_human_output_is_non_counting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = prepare_pack(Path(temp_dir))
            output = subprocess.run(
                [sys.executable, str(CHECK), str(pack)],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout

            self.assertIn("multi_surface_beta_capture_pack_check=candidate_pack_validated", output)
            self.assertIn("candidate_only=true", output)
            self.assertIn("same_approved_runtime_window_required=true", output)
            self.assertIn(
                "parallel_beta_capture_matrix=admin_commands_dino_tribe_buff_inventory_item_transfer_mission_parallel_candidates",
                output,
            )
            self.assertIn("parallel_beta_capture_status=status_only_candidate_non_evidence", output)
            self.assertIn(
                "simultaneous_beta_capture_candidate_worksheet=simultaneous-side-lane-candidate-worksheet.json",
                output,
            )
            self.assertIn(
                "single_player_parallel_capture_candidate_worksheet=single-player-full-sequence-candidate-worksheet.json",
                output,
            )
            self.assertIn(
                "single_player_parallel_capture_sequence=single_player_parallel_side_lane_capture_sequence",
                output,
            )
            self.assertIn("single_player_parallel_capture_status=status_only_candidate_non_evidence", output)
            self.assertIn("raw_player_text_retention_allowed=false", output)
            self.assertIn("secrets_or_webhook_retention_allowed=false", output)
            self.assertIn("counts_as_approved_runtime_evidence=false", output)
            self.assertIn("counts_as_sdk_progress=false", output)


if __name__ == "__main__":
    unittest.main()
