#!/usr/bin/env python3
"""Tests for check_mission_transfer_dino_tribe_v1_outcome_accounting.py."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_transfer_dino_tribe_v1_outcome_accounting.py"
MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"]
sys.path.insert(0, str(SCRIPT_DIR))
import build_redacted_scriptstruct_signatures as scriptstruct_build_tool  # noqa: E402
import check_dino_scalar_readiness as dino_scalar_readiness  # noqa: E402
import check_mission_transfer_dino_tribe_v1_outcome_accounting as accounting  # noqa: E402
import check_transfer_scriptstruct_readiness as transfer_scriptstruct_readiness  # noqa: E402


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def surface(manifest: dict) -> dict:
    return next(item for item in manifest["surfaces"] if item["id"] == SURFACE_ID)


def candidate_manifest() -> dict:
    manifest = load_manifest()
    gameplay = surface(manifest)
    gameplay["status"] = "planning"
    for leaf in gameplay["leaf_decision_units"]:
        leaf["status"] = "planning"
    return manifest


def excluded_release_statement() -> str:
    return (
        "Reviewed against docs/public_sdk_surfaces.json.\n"
        f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
        "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
        "No Mission SDK, Transfer SDK, Dino SDK, Tribe SDK, Buff/status SDK, "
        "teleport/spawn API, ownership lookup, ResourceHandle, mutation, return override, "
        "runtime hook, identity, lookup, or cross-map correlation API is included in v1.\n"
    )


def write_promoted_leaf_report(root: Path, leaf_id: str, evidence_kind: str) -> dict[str, str]:
    path = root / f"{leaf_id}-{evidence_kind}.json"
    payload = {
        "schema": f"obelisk.{leaf_id}-{evidence_kind}-promotion-gate.v1",
        "surface": SURFACE_ID,
        "leaf": leaf_id,
        "evidence_kind": evidence_kind,
        "status": "promoted",
        "promotion_ready": True,
        "public_sdk_ready": True,
        "runtime_ready": True,
        "artifact_identity": {
            "kind": evidence_kind,
            "sha256": hashlib.sha256(f"{leaf_id}:{evidence_kind}".encode("utf-8")).hexdigest(),
        },
    }
    if evidence_kind == "second_source_evidence":
        payload["second_source_provenance"] = {
            "source": "synthetic unit-test promoted evidence",
            "binary_sha256": hashlib.sha256(f"{leaf_id}:binary".encode("utf-8")).hexdigest(),
        }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return {"path": str(path.relative_to(REPO_ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


class MissionTransferDinoTribeOutcomeAccountingTests(unittest.TestCase):
    def assert_non_counting_leaf_latch(self, leaf: dict) -> None:
        false_keys = (
            "complete_sdk_ready",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "focused_checker_v1_accounted",
            "p0_dependency_chain_accounted",
            "p0_dependency_chain_ready",
            "public_module_ready",
            "public_or_runtime_accounting_allowed",
            "readiness_counts_toward_v1_accounting",
            "runtime_capture_ready",
            "v1_completion_ready",
            "live_ops_ready",
        )
        for key in false_keys:
            self.assertIn(key, leaf)
            self.assertFalse(leaf[key], key)

        zero_keys = (
            "complete_sdk_claim_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "v1_completion_progress_contribution",
        )
        for key in zero_keys:
            self.assertIn(key, leaf)
            self.assertEqual(0, leaf[key], key)

    def run_checker(
        self,
        manifest: dict | None = None,
        statement: str | None = None,
        split_note: str | None = None,
        mission_root: Path | None = None,
        mission_fixture_boundary_only: bool = False,
        transfer_root: Path | None = None,
        transfer_scriptstruct_snapshot_root: Path | None = None,
        transfer_scriptstruct_report: Path | None = None,
        dino_repo_root: Path | None = None,
        dino_report: Path | None = None,
        dino_snapshot_root: Path | None = None,
        tribe_snapshot_root: Path | None = None,
        buff_snapshot_root: Path | None = None,
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "public_sdk_surfaces.json"
            statement_path = root / "release-statement.md"
            split_note_path = root / "mission-transfer-dino-tribe-v1-split.md"
            manifest_path.write_text(json.dumps(manifest if manifest is not None else load_manifest()), encoding="utf-8")
            split_note_path.write_text(
                split_note if split_note is not None else SPLIT_NOTE.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            args = [
                sys.executable,
                str(SCRIPT),
                "--manifest",
                str(manifest_path),
                "--split-note",
                str(split_note_path),
                "--json",
            ]
            if statement is not None:
                statement_path.write_text(statement, encoding="utf-8")
                args.extend(["--release-statement", str(statement_path)])
            if mission_root is not None:
                args.extend(["--mission-root", str(mission_root)])
            if mission_fixture_boundary_only:
                args.append("--mission-fixture-boundary-only")
            if transfer_root is not None:
                args.extend(["--transfer-root", str(transfer_root)])
            if transfer_scriptstruct_snapshot_root is not None:
                args.extend(["--transfer-scriptstruct-snapshot-root", str(transfer_scriptstruct_snapshot_root)])
            if transfer_scriptstruct_report is not None:
                args.extend(["--transfer-scriptstruct-report", str(transfer_scriptstruct_report)])
            if dino_repo_root is not None:
                args.extend(["--dino-repo-root", str(dino_repo_root)])
            if dino_report is not None:
                args.extend(["--dino-report", str(dino_report)])
            if dino_snapshot_root is not None:
                args.extend(["--dino-snapshot-root", str(dino_snapshot_root)])
            if tribe_snapshot_root is not None:
                args.extend(["--tribe-snapshot-root", str(tribe_snapshot_root)])
            if buff_snapshot_root is not None:
                args.extend(["--buff-snapshot-root", str(buff_snapshot_root)])
            result = subprocess.run(
                args,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_current_manifest_accepts_candidate_only_planning_accounting(self) -> None:
        result = self.run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1")
        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertTrue(report["candidate_only"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(set(report["leaf_statuses"].values()), {"planning"})
        self.assertEqual(report["blockers"], [])
        accounting = report["candidate_only_accounting"]
        self.assertEqual(accounting["result"], "leaf_families_missing_v1_outcomes")
        self.assertTrue(accounting["accepted_for_internal_planning"])
        self.assertEqual(accounting["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(accounting["status_counts"], {"planning": 5})
        self.assertTrue(all(not accounting["leaf_family_gaps"][leaf_id]["v1_accounted"] for leaf_id in REQUIRED_LEAVES))
        self.assertTrue(all(accounting["leaf_family_gaps"][leaf_id]["accounted_by"] is None for leaf_id in REQUIRED_LEAVES))

    def test_candidate_manifest_accepts_candidate_only_accounting(self) -> None:
        result = self.run_checker(manifest=candidate_manifest())
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1")
        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertTrue(report["candidate_only"])
        self.assertFalse(report["complete_sdk_ready"])
        self.assertFalse(report["counts_toward_complete_sdk_claim"])
        self.assertFalse(report["p0_dependency_chain_accounted"])
        self.assertFalse(report["p0_dependency_chain_ready"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertFalse(report["readiness_counts_toward_v1_accounting"])
        self.assertFalse(report["public_module_ready"])
        self.assertFalse(report["runtime_capture_ready"])
        self.assertFalse(report["live_ops_ready"])
        self.assertEqual(report["required_leaves"], REQUIRED_LEAVES)
        self.assertEqual(report["observed_leaves"], REQUIRED_LEAVES)
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(set(report["leaf_statuses"].values()), {"planning"})
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["blockers"], [])

        accounting = report["candidate_only_accounting"]
        self.assertEqual(accounting["result"], "leaf_families_missing_v1_outcomes")
        self.assertTrue(accounting["accepted_for_internal_planning"])
        self.assertEqual(accounting["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(accounting["non_promoted_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(accounting["status_counts"], {"planning": 5})
        self.assertIn("mission-copied-bool-policy-slice", accounting["planning_target_sets"])
        self.assertIn("public_mission_sdk_abi", accounting["leaf_family_gaps"]["mission"]["missing_public_gates"])
        self.assertIn("cross_map_state_correlation", accounting["leaf_family_gaps"]["transfer"]["missing_public_gates"])
        self.assertIn("lookup_ownership_lifetime", accounting["leaf_family_gaps"]["dino_policy"]["missing_public_gates"])
        self.assertIn("privacy_redaction_contract", accounting["leaf_family_gaps"]["tribe_policy"]["missing_public_gates"])
        self.assertIn("buff_class_object_redaction_contract", accounting["leaf_family_gaps"]["buff_status"]["missing_public_gates"])
        self.assertNotIn("buff_leaf_readiness_checker", accounting["leaf_family_gaps"]["buff_status"]["missing_public_gates"])
        self.assertNotIn("refreshed_compact_evidence", accounting["leaf_family_gaps"]["buff_status"]["missing_public_gates"])
        self.assertFalse(accounting["leaf_family_gaps"]["tribe_policy"]["v1_accounted"])
        self.assertFalse(accounting["complete_sdk_ready"])
        self.assertFalse(accounting["counts_toward_complete_sdk_claim"])
        self.assertFalse(accounting["p0_dependency_chain_accounted"])
        self.assertFalse(accounting["p0_dependency_chain_ready"])
        self.assertFalse(accounting["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(accounting["public_or_runtime_accounting_allowed"])
        self.assertTrue(accounting["non_counting_internal_evidence"]["transfer_scriptstruct"]["checker_ready"])
        self.assertTrue(accounting["non_counting_internal_evidence"]["dino_scalar"]["checker_ready"])
        self.assertFalse(accounting["non_counting_internal_evidence"]["transfer_scriptstruct"]["counts_toward_v1_completion"])
        self.assertFalse(accounting["non_counting_internal_evidence"]["dino_scalar"]["counts_toward_complete_sdk_claim"])
        self.assertEqual(accounting["non_counting_internal_evidence"]["transfer_scriptstruct"]["progress_contribution"], 0)
        self.assertEqual(accounting["non_counting_internal_evidence"]["dino_scalar"]["progress_contribution"], 0)
        for leaf_id in REQUIRED_LEAVES:
            self.assertEqual(
                accounting["leaf_family_gaps"][leaf_id]["allowed_v1_outcome"],
                "not counted for v1 by this candidate-only checker; requires explicit leaf exclusion",
            )
            self.assertNotIn("C ABI surface", accounting["leaf_family_gaps"][leaf_id]["allowed_v1_outcome"])
            self.assertNotIn("promoted as", accounting["leaf_family_gaps"][leaf_id]["allowed_v1_outcome"])

        mission = report["mission_leaf_blocker_accounting"]
        self.assertEqual(
            mission["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-mission-leaf-blocker-accounting.v1",
        )
        self.assertEqual(mission["lane"], "mission_copied_bool_policy_slice")
        self.assertEqual(mission["outcome"], "internal_planning_only")
        self.assertTrue(mission["accepted_for_internal_planning"])
        self.assertTrue(mission["consume_only"])
        self.assertTrue(mission["candidate_only"])
        self.assertTrue(mission["internal_reusable_evidence_only"])
        self.assertTrue(mission["not_artifact_gate"])
        self.assertFalse(mission["v1_accounted"])
        self.assertFalse(mission["focused_checker_v1_accounted"])
        self.assertFalse(mission["mission_sdk_ready"])
        self.assertFalse(mission["public_abi_ready"])
        self.assertFalse(mission["public_sdk_ready"])
        self.assertFalse(mission["runtime_observer_approved"])
        self.assertFalse(mission["runtime_ready"])
        self.assertFalse(mission["identity_ready"])
        self.assertFalse(mission["lookup_ready"])
        self.assertFalse(mission["mutation_ready"])
        self.assertFalse(mission["promotion_ready"])
        self.assertFalse(mission["return_override_ready"])
        self.assertFalse(mission["v1_completion"])
        self.assertFalse(mission["complete_sdk_ready"])
        self.assertFalse(mission["counts_toward_complete_sdk_claim"])
        self.assertFalse(mission["p0_dependency_chain_accounted"])
        self.assertFalse(mission["p0_dependency_chain_ready"])
        self.assertFalse(mission["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(mission["readiness_counts_toward_v1_accounting"])
        self.assertEqual(
            mission["focused_checker_report"]["schema"],
            "obelisk.mission-copied-bool-readiness-check.v1",
        )
        self.assertTrue(mission["focused_checker_report"]["checker_ready_observed"])
        self.assertTrue(mission["focused_checker_report"]["accepted_for_internal_planning"])
        self.assertEqual(mission["focused_checker_report"]["blocker_reasons"], [])
        self.assertEqual(mission["blocker_parity"]["focused_checker_blocker_reasons"], [])
        self.assertIsNone(mission["blocker_parity"]["umbrella_blocker_reason"])
        self.assertEqual(mission["missing_required_evidence"], [])
        self.assertEqual(mission["copied_bool_boundary"]["copied_bool_count"], 5)
        self.assertEqual(
            mission["copied_bool_boundary"]["copied_targets"],
            [
                "MissionType.AddPlayerToMission",
                "MissionType.BPAllowPlayerToLeaveMission",
                "MissionType.BPOnPlayerRemovedFromMission",
            ],
        )
        self.assertIn(
            "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
            mission["copied_bool_boundary"]["copied_bool_fields"],
        )
        self.assertEqual(
            mission["redaction_boundary"]["recognition_only_targets"],
            ["MissionType.GetPlayerUsableItems"],
        )
        self.assertIn(
            "MissionType.GetPlayerUsableItems.OutItemIDs",
            mission["redaction_boundary"]["redacted_recognition_fields"],
        )
        self.assertIn("public_mission_sdk_abi", mission["remaining_public_gates"])
        self.assertIn("mission leaf accounting is exactly consume-only internal reusable evidence", mission["non_claims"])
        self.assertIn("P0 dependency-chain", " ".join(mission["non_claims"]))

        transfer = report["transfer_leaf_blocker_accounting"]
        self.assertEqual(
            transfer["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-transfer-leaf-blocker-accounting.v1",
        )
        self.assertEqual(transfer["lane"], "transfer_baccept_only_policy_slice")
        self.assertEqual(transfer["outcome"], "internal_planning_only")
        self.assertTrue(transfer["accepted_for_internal_planning"])
        self.assertTrue(transfer["candidate_only"])
        self.assertTrue(transfer["consume_only"])
        self.assertTrue(transfer["internal_reusable_evidence_only"])
        self.assertTrue(transfer["not_artifact_gate"])
        self.assertFalse(transfer["v1_accounted"])
        self.assertFalse(transfer["focused_checker_v1_accounted"])
        self.assertFalse(transfer["transfer_sdk_ready"])
        self.assertFalse(transfer["public_transfer_sdk_ready"])
        self.assertFalse(transfer["public_abi_ready"])
        self.assertFalse(transfer["public_api_ready"])
        self.assertFalse(transfer["public_sdk_ready"])
        self.assertFalse(transfer["public_header_ready"])
        self.assertFalse(transfer["public_contract_ready"])
        self.assertFalse(transfer["runtime_hook_ready"])
        self.assertFalse(transfer["runtime_hook_wiring_ready"])
        self.assertFalse(transfer["runtime_ready"])
        self.assertFalse(transfer["runtime_validated"])
        self.assertFalse(transfer["identity_ready"])
        self.assertFalse(transfer["ownership_ready"])
        self.assertFalse(transfer["mutation_ready"])
        self.assertFalse(transfer["promotion_ready"])
        self.assertFalse(transfer["return_override_ready"])
        self.assertFalse(transfer["v1_completion"])
        self.assertFalse(transfer["v1_completion_ready"])
        self.assertFalse(transfer["complete_sdk_ready"])
        self.assertFalse(transfer["counts_toward_complete_sdk_claim"])
        self.assertFalse(transfer["p0_dependency_chain_accounted"])
        self.assertFalse(transfer["p0_dependency_chain_ready"])
        self.assertFalse(transfer["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(transfer["counts_toward_public_sdk"])
        self.assertFalse(transfer["counts_toward_runtime"])
        self.assertFalse(transfer["counts_toward_v1_completion"])
        self.assertFalse(transfer["public_or_runtime_accounting_allowed"])
        self.assertEqual(0, transfer["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, transfer["p0_dependency_chain_claim_progress_contribution"])
        self.assertEqual(0, transfer["v1_completion_progress_contribution"])
        self.assertEqual(transfer["focused_checker"], "scripts/check_transfer_baccept_readiness.py")
        self.assertEqual(
            transfer["focused_checker_report"]["schema"],
            "obelisk.transfer-baccept-readiness-check.v1",
        )
        self.assertTrue(transfer["focused_checker_report"]["checker_ready_observed"])
        self.assertTrue(transfer["focused_checker_report"]["accepted_for_internal_planning"])
        self.assertEqual(transfer["focused_checker_report"]["blocker_reasons"], [])
        self.assertEqual(
            transfer["focused_checker_report"]["consume_gate"]["gate_status_observed"],
            "accepted",
        )
        self.assertEqual(
            transfer["focused_checker_report"]["promote_gate"]["gate_status_observed"],
            "blocked",
        )
        self.assertIn(
            "promote_mode_transfer_baccept_policy_slice_evidence_only",
            transfer["focused_checker_report"]["promote_gate"]["blocker_reasons"],
        )
        self.assertEqual(transfer["input_target_set"], "transfer-ufunction-intake")
        self.assertEqual(transfer["output_target_set"], "transfer-baccept-only-policy-slice")
        self.assertEqual(transfer["missing_required_evidence"], [])
        self.assertEqual(transfer["copied_bool_boundary"]["copied_bool_count"], 1)
        self.assertEqual(
            transfer["copied_bool_boundary"]["copied_bool_fields"],
            ["ShooterPlayerController.ServerTransferredPlayerConfirmationResult.bAccept"],
        )
        self.assertIn(
            "ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters.PlayerDataID",
            transfer["redaction_boundary"]["forbidden_fields"],
        )
        self.assertIn("cross_map_state_correlation", transfer["remaining_public_gates"])
        self.assertIn("teleport/spawn authority", " ".join(transfer["redaction_boundary"]["forbidden_promotions"]))
        self.assertEqual(transfer["blocker_parity"]["focused_checker_blocker_reasons"], [])
        self.assertIsNone(transfer["blocker_parity"]["umbrella_blocker_reason"])
        self.assertIn(
            "transfer bAccept readiness does not count toward P0 dependency-chain or complete-SDK accounting",
            transfer["non_claims"],
        )

        transfer_scriptstruct = report["transfer_scriptstruct_leaf_blocker_accounting"]
        self.assertEqual(
            transfer_scriptstruct["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-transfer-scriptstruct-leaf-blocker-accounting.v1",
        )
        self.assertEqual(transfer_scriptstruct["lane"], "transfer_scriptstruct_payload_layout_candidate")
        self.assertEqual(transfer_scriptstruct["outcome"], "internal_planning_only")
        self.assertTrue(transfer_scriptstruct["accepted_for_internal_planning"])
        self.assertTrue(transfer_scriptstruct["candidate_only"])
        self.assertTrue(transfer_scriptstruct["consume_only"])
        self.assertTrue(transfer_scriptstruct["internal_reusable_evidence_only"])
        self.assertFalse(transfer_scriptstruct["v1_accounted"])
        self.assertFalse(transfer_scriptstruct["focused_checker_v1_accounted"])
        self.assertFalse(transfer_scriptstruct["public_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["public_transfer_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["runtime_ready"])
        self.assertFalse(transfer_scriptstruct["promotion_ready"])
        self.assertFalse(transfer_scriptstruct["stable_claim_allowed"])
        self.assertFalse(transfer_scriptstruct["complete_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["counts_toward_complete_sdk_claim"])
        self.assertFalse(transfer_scriptstruct["p0_dependency_chain_ready"])
        self.assertFalse(transfer_scriptstruct["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(transfer_scriptstruct["complete_sdk_progress_contribution"], 0)
        self.assertEqual(transfer_scriptstruct["v1_completion_progress_contribution"], 0)
        self.assertEqual(transfer_scriptstruct["focused_checker"], "scripts/check_transfer_scriptstruct_readiness.py")
        self.assertEqual(
            transfer_scriptstruct["focused_checker_report"]["schema"],
            "obelisk.transfer-scriptstruct-readiness-check.v1",
        )
        self.assertTrue(transfer_scriptstruct["focused_checker_report"]["checker_ready_observed"])
        self.assertEqual(transfer_scriptstruct["focused_checker_report"]["blocker_reasons"], [])
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["target_set"], "transfer-scriptstruct")
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["snapshot_count"], 2)
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["signature_count"], 2)
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["field_count_total"], 21)
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["redacted_payload_field_count"], 21)
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["copied_scalar_count_total"], 0)
        self.assertFalse(transfer_scriptstruct["scriptstruct_boundary"]["payload_decoding_ready"])
        self.assertEqual(transfer_scriptstruct["scriptstruct_boundary"]["bool_tail_field_count"], 3)
        self.assertIn(
            "PrimalLocalProfile.ArkTributePlayerData.bForServerTransfer",
            transfer_scriptstruct["scriptstruct_boundary"]["bool_tail_fields"],
        )
        self.assertEqual(transfer_scriptstruct["redaction_boundary"]["explicitly_excluded"], ["ItemNetInfo"])
        self.assertTrue(transfer_scriptstruct["redaction_boundary"]["item_net_info_excluded"])
        self.assertIn("transfer_payload_decoding", transfer_scriptstruct["redaction_boundary"]["not_promoted_surfaces"])
        self.assertIn("raw UE params", " ".join(transfer_scriptstruct["redaction_boundary"]["forbidden_promotions"]))
        self.assertIn(
            "transfer ScriptStruct readiness does not count toward v1, P0 dependency-chain, runtime, stable, or complete-SDK accounting",
            transfer_scriptstruct["non_claims"],
        )

        dino = report["dino_leaf_blocker_accounting"]
        self.assertEqual(
            dino["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-dino-leaf-blocker-accounting.v1",
        )
        self.assertEqual(dino["lane"], "dino_scalar_boundary_candidate")
        self.assertEqual(dino["outcome"], "internal_planning_only")
        self.assertTrue(dino["accepted_for_internal_planning"])
        self.assertTrue(dino["candidate_only"])
        self.assertTrue(dino["internal_reusable_evidence_only"])
        self.assertFalse(dino["v1_accounted"])
        self.assertFalse(dino["focused_checker_v1_accounted"])
        self.assertFalse(dino["dino_sdk_ready"])
        self.assertFalse(dino["public_dino_sdk_ready"])
        self.assertFalse(dino["public_abi_ready"])
        self.assertFalse(dino["public_sdk_ready"])
        self.assertFalse(dino["runtime_ready"])
        self.assertFalse(dino["identity_ready"])
        self.assertFalse(dino["lookup_ready"])
        self.assertFalse(dino["mutation_ready"])
        self.assertFalse(dino["promotion_ready"])
        self.assertFalse(dino["return_override_ready"])
        self.assertFalse(dino["resource_handle_ready"])
        self.assertFalse(dino["v1_completion_ready"])
        self.assertFalse(dino["p0_dependency_chain_ready"])
        self.assertFalse(dino["stable_claim_allowed"])
        self.assertEqual(dino["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(dino["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(dino["focused_checker"], "scripts/check_dino_scalar_readiness.py")
        self.assertEqual(
            dino["focused_checker_report"]["schema"],
            "obelisk.dino-scalar-readiness-check.v1",
        )
        self.assertTrue(dino["focused_checker_report"]["checker_ready_observed"])
        self.assertEqual(dino["focused_checker_report"]["blocker_reasons"], [])
        self.assertEqual(dino["focused_checker_report"]["source_isolation_status"], "isolated")
        self.assertTrue(dino["scalar_boundary"]["scalar_only_ready"])
        self.assertTrue(dino["scalar_boundary"]["precall_scalar_ready"])
        self.assertFalse(dino["scalar_boundary"]["postcall_return_ready"])
        self.assertEqual(dino["scalar_boundary"]["precall_copied_count"], 4)
        self.assertEqual(dino["scalar_boundary"]["deferred_return_count"], 2)
        self.assertTrue(dino["scalar_boundary"]["return_values_excluded"])
        self.assertIn(
            "PrimalDinoCharacter.AddPassenger.bForcePassenger",
            dino["scalar_boundary"]["precall_copied_fields"],
        )
        self.assertIn(
            "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
            dino["scalar_boundary"]["deferred_return_fields"],
        )
        self.assertIn(
            "PrimalDinoCharacter.AddPassenger.ACharacter",
            dino["redaction_boundary"]["required_redactions"],
        )
        self.assertIn("lookup_ownership_lifetime", dino["remaining_public_gates"])
        self.assertEqual(dino["source_isolation"]["status"], "isolated")
        self.assertIn(
            "dino scalar readiness does not count toward v1, P0 dependency-chain, runtime, stable, or complete-SDK accounting",
            dino["non_claims"],
        )

        tribe = report["tribe_leaf_blocker_accounting"]
        self.assertEqual(
            tribe["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-tribe-leaf-blocker-accounting.v1",
        )
        self.assertEqual(tribe["lane"], "tribe_scalar_boundary_candidate")
        self.assertEqual(tribe["outcome"], "internal_planning_only")
        self.assertTrue(tribe["accepted_for_internal_planning"])
        self.assertTrue(tribe["candidate_only"])
        self.assertTrue(tribe["internal_reusable_evidence_only"])
        self.assertTrue(tribe["not_artifact_gate"])
        self.assertFalse(tribe["v1_accounted"])
        self.assertFalse(tribe["tribe_sdk_ready"])
        self.assertFalse(tribe["public_abi_ready"])
        self.assertFalse(tribe["public_sdk_ready"])
        self.assertFalse(tribe["public_tribe_sdk_ready"])
        self.assertFalse(tribe["runtime_observer_approved"])
        self.assertFalse(tribe["runtime_ready"])
        self.assertFalse(tribe["identity_ready"])
        self.assertFalse(tribe["lookup_ready"])
        self.assertFalse(tribe["mutation_ready"])
        self.assertFalse(tribe["promotion_ready"])
        self.assertFalse(tribe["return_override_ready"])
        self.assertFalse(tribe["resource_handle_ready"])
        self.assertFalse(tribe["v1_completion"])
        self.assert_non_counting_leaf_latch(tribe)
        self.assertEqual(tribe["focused_checker"], "scripts/check_tribe_scalar_boundary_readiness.py")
        self.assertEqual(tribe["input_target_set"], "tribe-compact-intake")
        self.assertEqual(tribe["missing_required_evidence"], [])
        self.assertTrue(tribe["scalar_boundary"]["checker_ready"])
        self.assertTrue(tribe["scalar_boundary"]["tribe_scalar_boundary_ready"])
        self.assertTrue(tribe["scalar_boundary"]["server_request_tribe_log_control_ready"])
        self.assertEqual(tribe["scalar_boundary"]["accepted_scalar_count"], 3)
        self.assertIn(
            "ShooterPlayerController.AllowTribeGroupPermission.TribeGroupPermission",
            tribe["scalar_boundary"]["accepted_scalar_fields"],
        )
        self.assertIn(
            "ShooterPlayerController.AllowTribeGroupPermission.OnObject",
            tribe["redaction_boundary"]["required_redactions"],
        )
        self.assertIn("privacy_redaction_contract", tribe["remaining_public_gates"])
        self.assertIn("permission enforcement contract", " ".join(tribe["redaction_boundary"]["forbidden_promotions"]))
        self.assertIn(
            "tribe leaf accounting does not promote a public Tribe SDK, ABI, callback, descriptor, or v1 completion",
            tribe["non_claims"],
        )

        buff = report["buff_leaf_blocker_accounting"]
        self.assertEqual(
            buff["schema"],
            "obelisk.mission-transfer-dino-tribe-v1-buff-leaf-blocker-accounting.v1",
        )
        self.assertEqual(buff["lane"], "buff_status_scalar_boundary_candidate")
        self.assertEqual(buff["outcome"], "internal_planning_only")
        self.assertTrue(buff["accepted_for_internal_planning"])
        self.assertTrue(buff["candidate_only"])
        self.assertTrue(buff["internal_reusable_evidence_only"])
        self.assertTrue(buff["not_artifact_gate"])
        self.assertFalse(buff["v1_accounted"])
        self.assertFalse(buff["buff_status_sdk_ready"])
        self.assertFalse(buff["public_abi_ready"])
        self.assertFalse(buff["public_sdk_ready"])
        self.assertFalse(buff["public_buff_sdk_ready"])
        self.assertFalse(buff["runtime_observer_approved"])
        self.assertFalse(buff["runtime_ready"])
        self.assertFalse(buff["identity_ready"])
        self.assertFalse(buff["lookup_ready"])
        self.assertFalse(buff["mutation_ready"])
        self.assertFalse(buff["promotion_ready"])
        self.assertFalse(buff["return_override_ready"])
        self.assertFalse(buff["resource_handle_ready"])
        self.assertFalse(buff["v1_completion"])
        self.assertFalse(buff["copied_payload_policy_ready"])
        self.assertFalse(buff["lifecycle_semantics_ready"])
        self.assert_non_counting_leaf_latch(buff)
        self.assertEqual(buff["focused_checker"], "scripts/check_buff_status_readiness.py")
        self.assertEqual(buff["input_target_sets"], ["buff-compact-intake", "buff-breadth-intake"])
        self.assertEqual(buff["missing_required_evidence"], [])
        self.assertTrue(buff["scalar_boundary"]["checker_ready"])
        self.assertTrue(buff["scalar_boundary"]["buff_status_candidate_ready"])
        self.assertTrue(buff["scalar_boundary"]["copied_bool_boundary_ready"])
        self.assertTrue(buff["scalar_boundary"]["class_object_redaction_ready"])
        self.assertTrue(buff["scalar_boundary"]["zero_param_lifecycle_shape_ready"])
        self.assertEqual(buff["scalar_boundary"]["copied_bool_count"], 6)
        self.assertIn(
            "PrimalBuff.BuffOverrideInventoryAccessInput.bInputPressed",
            buff["scalar_boundary"]["copied_bool_fields"],
        )
        self.assertIn(
            "PrimalBuff.BPPreventAddingOtherBuff.anotherBuffClass",
            buff["redaction_boundary"]["required_redactions"],
        )
        self.assertIn("copied_payload_policy", buff["remaining_public_gates"])
        self.assertIn("runtime hook wiring", " ".join(buff["redaction_boundary"]["forbidden_promotions"]))
        self.assertIn(
            "buff/status leaf accounting does not promote a public Buff SDK, ABI, callback, descriptor, or v1 completion",
            buff["non_claims"],
        )

        priority = report["leaf_priority"]
        self.assertEqual(priority["schema"], "obelisk.mission-transfer-dino-tribe-v1-leaf-priority.v1")
        self.assertEqual(priority["recommended_leaf"], "mission")
        self.assertEqual(priority["recommended_scope"], "internal_reusable_evidence_only")
        self.assertEqual(
            [item["leaf"] for item in priority["ranked_leaves"]],
            ["mission", "dino_policy", "transfer", "buff_status", "tribe_policy"],
        )
        self.assertEqual(priority["ranked_leaves"][0]["missing_public_gate_count"], 6)
        buff_priority = next(item for item in priority["ranked_leaves"] if item["leaf"] == "buff_status")
        self.assertNotIn("missing Buff-specific consume/readiness checker", " ".join(buff_priority["blocking_risk"]))
        self.assertIn("focused Buff/status readiness checker", " ".join(buff_priority["reusable_evidence"]))
        self.assertIn("Use the Buff/status checker output", buff_priority["next_v1_reuse_step"])
        transfer_priority = next(item for item in priority["ranked_leaves"] if item["leaf"] == "transfer")
        self.assertIn("candidate-only Transfer ScriptStruct checker", " ".join(transfer_priority["reusable_evidence"]))
        self.assertIn("candidate ScriptStruct layout summary", transfer_priority["next_v1_reuse_step"])
        self.assertFalse(any(item["public_sdk_ready"] for item in priority["ranked_leaves"]))
        self.assertFalse(any(item["runtime_ready"] for item in priority["ranked_leaves"]))
        self.assertFalse(any(item["promotion_ready"] for item in priority["ranked_leaves"]))

    def test_release_statement_accepts_umbrella_excluded_with_all_leaf_exclusions(self) -> None:
        result = self.run_checker(statement=excluded_release_statement())
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "release_statement_umbrella_excluded")
        self.assertTrue(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["release_statement"]["forbidden_claims"], [])
        self.assertTrue(all(report["release_statement"]["leaf_exclusions"].values()))
        self.assertEqual(report["missing_leaf_families"], [])
        self.assertEqual(report["candidate_only_accounting"]["result"], "all_leaf_families_accounted")
        self.assertEqual(
            report["candidate_only_accounting"]["leaf_family_gaps"]["mission"]["accounted_by"],
            "release_statement_leaf_exclusion",
        )

    def test_release_statement_ignores_other_rows_and_negated_readiness_context(self) -> None:
        statement = (
            "Passive snapshots do not count toward this statement, release readiness, "
            "or public SDK readiness.\n"
            "Runtime context does not count toward runtime readiness or public SDK readiness.\n"
            f"- {SURFACE_ID} is explicitly excluded as non-complete.\n"
            "obelisk.object_identity_resource_handle.v1: post-v1 - no object identity, "
            "ResourceHandle, lookup, mutation, or v1 release API is included in v1\n"
            + excluded_release_statement()
        )
        result = self.run_checker(statement=statement)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "release_statement_umbrella_excluded")
        self.assertEqual(report["release_statement"]["forbidden_claims"], [])
        self.assertEqual(report["release_statement"]["ready_claims"], [])

    def test_release_statement_rejects_missing_leaf_exclusion(self) -> None:
        statement = excluded_release_statement().replace("buff_status excluded. ", "")
        result = self.run_checker(
            manifest=candidate_manifest(),
            statement=statement,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_leaf_exclusions_missing", report["blockers"])
        details = [item for item in report["blocker_details"] if item["reason"] == "release_statement_leaf_exclusions_missing"]
        self.assertEqual(details[0]["missing"], ["buff_status"])
        self.assertEqual(report["missing_leaf_families"], ["buff_status"])
        self.assertEqual(
            report["candidate_only_accounting"]["leaf_family_gaps"]["mission"]["accounted_by"],
            "release_statement_leaf_exclusion_pending_acceptance",
        )
        self.assertFalse(report["candidate_only_accounting"]["leaf_family_gaps"]["buff_status"]["v1_accounted"])

    def test_release_statement_does_not_count_generic_buff_identity_exclusion_as_buff_status_leaf(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded. "
            "Buff identity excluded from v1. "
            "No Buff/status SDK, runtime hook, identity, lookup, mutation, return override, or ResourceHandle is included in v1.\n"
        )
        result = self.run_checker(
            manifest=candidate_manifest(),
            statement=statement,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_leaf_exclusions_missing", report["blockers"])
        details = [item for item in report["blocker_details"] if item["reason"] == "release_statement_leaf_exclusions_missing"]
        self.assertEqual(details[0]["missing"], ["buff_status"])
        self.assertFalse(report["release_statement"]["leaf_exclusions"]["buff_status"])
        self.assertFalse(report["candidate_only_accounting"]["leaf_family_gaps"]["buff_status"]["v1_accounted"])

    def test_release_statement_rejects_affirmative_forbidden_claims(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Mission SDK is included in v1. ResourceHandle lookup is available. "
            "The runtime hook supports cross-map correlation.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_claims", report["blockers"])
        claims = report["release_statement"]["forbidden_claims"]
        self.assertIn("Mission SDK", claims)
        self.assertIn("ResourceHandle", claims)
        self.assertIn("runtime hook", claims)
        self.assertIn("cross-map correlation", claims)

    def test_release_statement_rejects_generic_sdk_runtime_v1_readiness_overclaims(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Public SDK is ready. Runtime ready. v1 is complete.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_ready_overclaims", report["blockers"])
        claims = report["release_statement"]["ready_claims"]
        self.assertIn("Public SDK is ready", claims)
        self.assertIn("Runtime ready", claims)
        self.assertIn("v1 is complete", claims)
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_release_statement_rejects_support_tier_release_and_stable_sdk_overclaims(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Support-tier is active. Release readiness is satisfied. Stable SDK is allowed.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_ready_overclaims", report["blockers"])
        claims = report["release_statement"]["ready_claims"]
        self.assertIn("Support-tier is active", claims)
        self.assertIn("Release readiness is satisfied", claims)
        self.assertIn("Stable SDK is allowed", claims)
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_release_statement_rejects_leaf_promotion_wording_without_promoted_evidence(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded and promoted; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded and promoted. "
            "No Mission SDK, Transfer SDK, Dino SDK, Tribe SDK, or Buff/status SDK is included in v1.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_leaf_promotions_without_evidence", report["blockers"])
        details = [
            item
            for item in report["blocker_details"]
            if item["reason"] == "release_statement_leaf_promotions_without_evidence"
        ]
        self.assertEqual(details[0]["leaves"], ["mission", "buff_status"])
        self.assertTrue(report["release_statement"]["leaf_promotions"]["mission"])
        self.assertTrue(report["release_statement"]["leaf_promotions"]["buff_status"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_release_statement_rejects_negated_exclusion_as_affirmative_claim(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission is not excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Mission SDK is not excluded from v1. Runtime hook is not blocked.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_leaf_exclusions_missing", report["blockers"])
        self.assertIn("release_statement_forbidden_claims", report["blockers"])
        details = [item for item in report["blocker_details"] if item["reason"] == "release_statement_leaf_exclusions_missing"]
        self.assertEqual(details[0]["missing"], ["mission"])
        claims = report["release_statement"]["forbidden_claims"]
        self.assertIn("Mission SDK", claims)
        self.assertIn("Runtime hook", claims)
        self.assertFalse(report["release_statement"]["leaf_exclusions"]["mission"])

    def test_excluded_manifest_route_rejects_public_contract(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["status"] = "excluded"
        gameplay["public_contract"] = ["Mission API"]
        for leaf in gameplay["leaf_decision_units"]:
            leaf["status"] = "excluded"
        gameplay["leaf_decision_units"][0]["public_contract"] = ["mission identity lookup"]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("excluded_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("excluded_leaf_public_contract_not_empty", report["blockers"])
        self.assertIn("public_contract_forbidden_claim", report["blockers"])
        self.assertIn("leaf_public_contract_forbidden_claim", report["blockers"])

    def test_manifest_public_contract_rejects_generic_ready_overclaims(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["public_contract"] = ["public SDK is ready"]
        gameplay["leaf_decision_units"][0]["public_contract"] = ["runtime ready", "v1 is complete"]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_contract_ready_overclaim", report["blockers"])
        self.assertIn("leaf_public_contract_ready_overclaim", report["blockers"])
        surface_claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "public_contract_ready_overclaim"
        }
        leaf_claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_public_contract_ready_overclaim"
        }
        self.assertIn("public SDK is ready", surface_claims)
        self.assertIn("runtime ready", leaf_claims)
        self.assertIn("v1 is complete", leaf_claims)

    def test_promoted_leaf_route_is_blocked_even_with_synthetic_evidence(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [write_promoted_leaf_report(evidence_root, leaf["id"], "abi_tests")],
                    "sdk_consumer_tests": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "sdk_consumer_tests")
                    ],
                    "second_source_evidence": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "second_source_evidence")
                    ],
                }

            result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertEqual(report["candidate_only_accounting"]["result"], "leaf_families_missing_v1_outcomes")
        self.assertEqual(report["candidate_only_accounting"]["status_counts"], {"promoted": 5})
        self.assertIn("side_lane_leaf_promotion_not_allowed", report["blockers"])

    def test_future_per_leaf_promoted_route_rejects_placeholder_evidence_paths(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["status"] = "promoted"
        for leaf in gameplay["leaf_decision_units"]:
            leaf["status"] = "promoted"
            leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
            leaf["evidence"] = {
                "promotion_status": "promoted",
                "public_sdk_ready": True,
                "promotion_ready": True,
                "runtime_ready": True,
                "abi_tests": [f"tests/abi/{leaf['id']}_abi_tests.cpp"],
                "sdk_consumer_tests": [f"tests/sdk_consumer/{leaf['id']}_consumer.c"],
                "second_source_evidence": [f"docs/research/{leaf['id']}-accepted-second-source.md"],
            }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertNotEqual(report["accounting_route"], "per_leaf_promoted")
        self.assertIn("promoted_leaf_gate_report_unverified", report["blockers"])

    def test_future_per_leaf_promoted_route_rejects_absolute_evidence_paths(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            report = write_promoted_leaf_report(evidence_root, "mission", "abi_tests")
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [copy.deepcopy(report)],
                    "sdk_consumer_tests": [copy.deepcopy(report)],
                    "second_source_evidence": [copy.deepcopy(report)],
                }
            gameplay["leaf_decision_units"][0]["evidence"]["abi_tests"][0]["path"] = str(evidence_root / "mission-abi_tests.json")

            result = self.run_checker(manifest=manifest, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_evidence_path_not_repo_relative", payload["blockers"])

    def test_future_per_leaf_promoted_route_rejects_symlinked_evidence_report(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [write_promoted_leaf_report(evidence_root, leaf["id"], "abi_tests")],
                    "sdk_consumer_tests": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "sdk_consumer_tests")
                    ],
                    "second_source_evidence": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "second_source_evidence")
                    ],
                }
            mission_entry = gameplay["leaf_decision_units"][0]["evidence"]["abi_tests"][0]
            symlink_path = REPO_ROOT / mission_entry["path"]
            real_path = symlink_path.with_name("mission-abi_tests-real-report.json")
            symlink_path.rename(real_path)
            symlink_path.symlink_to(real_path)

            result = self.run_checker(manifest=manifest, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_evidence_path_rejected", payload["blockers"])

    def test_future_per_leaf_promoted_route_rejects_non_leaf_specific_or_planning_schema_reports(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [write_promoted_leaf_report(evidence_root, leaf["id"], "abi_tests")],
                    "sdk_consumer_tests": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "sdk_consumer_tests")
                    ],
                    "second_source_evidence": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "second_source_evidence")
                    ],
                }
            generic = write_promoted_leaf_report(evidence_root, "mission", "abi_tests")
            generic_path = evidence_root / "mission-abi_tests.json"
            generic_report = json.loads(generic_path.read_text(encoding="utf-8"))
            generic_report["schema"] = "obelisk.mission-planning-readiness.v1"
            generic_path.write_text(json.dumps(generic_report, sort_keys=True), encoding="utf-8")
            generic["sha256"] = hashlib.sha256(generic_path.read_bytes()).hexdigest()
            gameplay["leaf_decision_units"][0]["evidence"]["abi_tests"] = [generic]
            gameplay["leaf_decision_units"][1]["evidence"]["abi_tests"] = [copy.deepcopy(generic)]

            result = self.run_checker(manifest=manifest, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_gate_report_non_promotional_schema", payload["blockers"])
        self.assertIn("promoted_leaf_evidence_path_not_leaf_specific", payload["blockers"])

    def test_future_per_leaf_promoted_route_rejects_approved_bundle_evidence_markers(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["public_contract"] = [f"Copied {leaf['id']} policy event"]
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [write_promoted_leaf_report(evidence_root, leaf["id"], "abi_tests")],
                    "sdk_consumer_tests": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "sdk_consumer_tests")
                    ],
                    "second_source_evidence": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "second_source_evidence")
                    ],
                }
            mission_entry = gameplay["leaf_decision_units"][0]["evidence"]["abi_tests"][0]
            mission_path = REPO_ROOT / mission_entry["path"]
            mission_report = json.loads(mission_path.read_text(encoding="utf-8"))
            mission_report["schema"] = "obelisk.mission-approved-bundle.v1"
            mission_path.write_text(json.dumps(mission_report, sort_keys=True), encoding="utf-8")
            mission_entry["sha256"] = hashlib.sha256(mission_path.read_bytes()).hexdigest()

            transfer_entry = gameplay["leaf_decision_units"][1]["evidence"]["abi_tests"][0]
            transfer_path = REPO_ROOT / transfer_entry["path"]
            renamed_transfer_path = transfer_path.with_name("transfer-approved_bundle-abi_tests.json")
            transfer_path.rename(renamed_transfer_path)
            transfer_entry["path"] = str(renamed_transfer_path.relative_to(REPO_ROOT))
            transfer_entry["sha256"] = hashlib.sha256(renamed_transfer_path.read_bytes()).hexdigest()

            result = self.run_checker(manifest=manifest, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_gate_report_non_promotional_schema", payload["blockers"])
        self.assertIn("promoted_leaf_evidence_path_non_promotional", payload["blockers"])

    def test_future_per_leaf_promoted_route_rejects_missing_or_candidate_evidence(self) -> None:
        evidence_parent = REPO_ROOT / "local" / "mission-transfer-dino-tribe-test-evidence"
        evidence_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=evidence_parent) as temp_dir:
            evidence_root = Path(temp_dir)
            manifest = load_manifest()
            gameplay = surface(manifest)
            gameplay["status"] = "promoted"
            for leaf in gameplay["leaf_decision_units"]:
                leaf["status"] = "promoted"
                leaf["evidence"] = {
                    "promotion_status": "promoted",
                    "public_sdk_ready": True,
                    "promotion_ready": True,
                    "runtime_ready": True,
                    "abi_tests": [write_promoted_leaf_report(evidence_root, leaf["id"], "abi_tests")],
                    "sdk_consumer_tests": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "sdk_consumer_tests")
                    ],
                    "second_source_evidence": [
                        write_promoted_leaf_report(evidence_root, leaf["id"], "second_source_evidence")
                    ],
                }
            gameplay["leaf_decision_units"][0]["evidence"].pop("second_source_evidence")
            gameplay["leaf_decision_units"][1]["evidence"]["notes"] = "candidate-only intake is not promoted"

            result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("promoted_leaf_real_evidence_missing", report["blockers"])
        self.assertIn("promoted_leaf_evidence_contains_candidate_only_markers", report["blockers"])

    def test_manifest_rejects_missing_required_leaf(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["leaf_decision_units"] = [
            leaf for leaf in gameplay["leaf_decision_units"] if leaf["id"] != "tribe_policy"
        ]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_decision_units_mismatch", report["blockers"])

    def test_priority_rejects_stale_leaf_evidence_profile(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["current_evidence"] = ["mission-compact-intake"]

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_priority_required_evidence_missing", report["blockers"])
        details = [item for item in report["blocker_details"] if item["reason"] == "leaf_priority_required_evidence_missing"]
        self.assertEqual(details[0]["leaf"], "mission")
        self.assertEqual(details[0]["missing"], ["mission-copied-bool-policy-slice"])

    def test_mission_leaf_split_note_requires_frozen_field_boundary(self) -> None:
        note = SPLIT_NOTE.read_text(encoding="utf-8").replace(
            "- `MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess`\n",
            "",
        )

        result = self.run_checker(split_note=note, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_leaf_accounting_split_note_token_missing", report["blockers"])
        details = [
            item
            for item in report["blocker_details"]
            if item["reason"] == "mission_leaf_accounting_split_note_token_missing"
        ]
        self.assertEqual(details[0]["token"], "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess")

    def test_mission_candidate_leaf_rejects_ready_overclaim(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {
            "public_sdk_ready": True,
            "nested": {"runtime_ready": True},
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_leaf_candidate_ready_overclaim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "mission_leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            fields,
            {
                "$.leaf_decision_units[mission].evidence.public_sdk_ready",
                "$.leaf_decision_units[mission].evidence.nested.runtime_ready",
            },
        )

    def test_mission_candidate_leaf_rejects_textual_runtime_and_v1_overclaims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {
            "notes": "The copied-bool side lane is runtime ready and v1 complete for mission planning."
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_leaf_candidate_ready_overclaim", report["blockers"])
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "mission_leaf_candidate_ready_overclaim"
        }
        self.assertIn("runtime ready", claims)
        self.assertIn("v1 complete", claims)

    def test_candidate_leaf_allows_negated_textual_readiness_non_claims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {
            "notes": (
                "The copied-bool side lane is not runtime ready. "
                "It does not imply v1 completion and public SDK readiness remains blocked."
            )
        }

        result = self.run_checker(manifest=manifest)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["blockers"], [])

    def test_tribe_leaf_accounting_fails_closed_when_scalar_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-snapshots"
            result = self.run_checker(
                manifest=candidate_manifest(),
                tribe_snapshot_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("tribe_scalar_boundary_checker_blocked", report["blockers"])
        tribe = report["tribe_leaf_blocker_accounting"]
        self.assertEqual(tribe["outcome"], "blocked_accounting")
        self.assertFalse(tribe["accepted_for_internal_planning"])
        self.assertFalse(tribe["v1_accounted"])
        self.assertFalse(tribe["public_sdk_ready"])
        self.assertFalse(tribe["runtime_ready"])
        self.assertFalse(tribe["promotion_ready"])
        self.assert_non_counting_leaf_latch(tribe)

    def test_buff_leaf_accounting_fails_closed_when_status_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-snapshots"
            result = self.run_checker(
                manifest=candidate_manifest(),
                buff_snapshot_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("buff_status_checker_blocked", report["blockers"])
        buff = report["buff_leaf_blocker_accounting"]
        self.assertEqual(buff["outcome"], "blocked_accounting")
        self.assertFalse(buff["accepted_for_internal_planning"])
        self.assertFalse(buff["v1_accounted"])
        self.assertFalse(buff["public_sdk_ready"])
        self.assertFalse(buff["runtime_ready"])
        self.assertFalse(buff["promotion_ready"])
        self.assertFalse(buff["copied_payload_policy_ready"])
        self.assertFalse(buff["lifecycle_semantics_ready"])
        self.assert_non_counting_leaf_latch(buff)

    def test_mission_leaf_accounting_fails_closed_when_focused_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-mission-artifact-root"
            result = self.run_checker(
                manifest=candidate_manifest(),
                mission_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("mission_copied_bool_checker_blocked", report["blockers"])
        mission = report["mission_leaf_blocker_accounting"]
        self.assertEqual(mission["outcome"], "blocked_accounting")
        self.assertFalse(mission["accepted_for_internal_planning"])
        self.assertFalse(mission["v1_accounted"])
        self.assertFalse(mission["focused_checker_v1_accounted"])
        self.assertFalse(mission["public_sdk_ready"])
        self.assertFalse(mission["runtime_ready"])
        self.assertFalse(mission["promotion_ready"])
        self.assertFalse(mission["complete_sdk_ready"])
        self.assertFalse(mission["counts_toward_complete_sdk_claim"])
        self.assertFalse(mission["p0_dependency_chain_ready"])
        self.assertIn("manifest_unreadable", mission["focused_checker_report"]["blocker_reasons"])
        self.assertEqual(
            mission["blocker_parity"]["umbrella_blocker_reason"],
            "mission_copied_bool_checker_blocked_or_not_ready",
        )

    def test_transfer_leaf_accounting_fails_closed_when_baccept_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-transfer-artifact-root"
            result = self.run_checker(
                manifest=candidate_manifest(),
                transfer_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["missing_leaf_families"], REQUIRED_LEAVES)
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("transfer_baccept_checker_blocked", report["blockers"])
        transfer = report["transfer_leaf_blocker_accounting"]
        self.assertEqual(transfer["outcome"], "blocked_accounting")
        self.assertFalse(transfer["accepted_for_internal_planning"])
        self.assertFalse(transfer["v1_accounted"])
        self.assertFalse(transfer["focused_checker_v1_accounted"])
        self.assertFalse(transfer["public_sdk_ready"])
        self.assertFalse(transfer["runtime_ready"])
        self.assertFalse(transfer["promotion_ready"])
        self.assertFalse(transfer["complete_sdk_ready"])
        self.assertFalse(transfer["counts_toward_complete_sdk_claim"])
        self.assertFalse(transfer["p0_dependency_chain_ready"])
        self.assertIn("manifest_unreadable", transfer["focused_checker_report"]["blocker_reasons"])
        self.assertEqual(
            transfer["blocker_parity"]["umbrella_blocker_reason"],
            "transfer_baccept_checker_blocked_or_not_ready",
        )

    def test_transfer_scriptstruct_leaf_accounting_fails_closed_when_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-scriptstruct-snapshots"
            result = self.run_checker(
                manifest=candidate_manifest(),
                transfer_scriptstruct_snapshot_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("transfer_scriptstruct_checker_blocked", report["blockers"])
        transfer_scriptstruct = report["transfer_scriptstruct_leaf_blocker_accounting"]
        self.assertEqual(transfer_scriptstruct["outcome"], "blocked_accounting")
        self.assertFalse(transfer_scriptstruct["accepted_for_internal_planning"])
        self.assertFalse(transfer_scriptstruct["v1_accounted"])
        self.assertFalse(transfer_scriptstruct["public_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["runtime_ready"])
        self.assertFalse(transfer_scriptstruct["promotion_ready"])
        self.assertFalse(transfer_scriptstruct["counts_toward_complete_sdk_claim"])
        self.assertFalse(transfer_scriptstruct["p0_dependency_chain_ready"])
        self.assertEqual(transfer_scriptstruct["v1_completion_progress_contribution"], 0)
        self.assertIn("snapshot_manifest_missing", transfer_scriptstruct["focused_checker_report"]["blocker_reasons"])
        self.assertEqual(
            transfer_scriptstruct["blocker_parity"]["umbrella_blocker_reason"],
            "transfer_scriptstruct_checker_blocked_or_not_ready",
        )

    def test_dino_leaf_accounting_fails_closed_when_scalar_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-dino-snapshots"
            result = self.run_checker(
                manifest=candidate_manifest(),
                dino_snapshot_root=missing_root,
                check=False,
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["candidate_only_accounting"]["accepted_for_internal_planning"])
        self.assertIn("dino_scalar_checker_blocked", report["blockers"])
        dino = report["dino_leaf_blocker_accounting"]
        self.assertEqual(dino["outcome"], "blocked_accounting")
        self.assertFalse(dino["accepted_for_internal_planning"])
        self.assertFalse(dino["v1_accounted"])
        self.assertFalse(dino["public_sdk_ready"])
        self.assertFalse(dino["runtime_ready"])
        self.assertFalse(dino["promotion_ready"])
        self.assertFalse(dino["counts_toward_complete_sdk_claim"])
        self.assertFalse(dino["p0_dependency_chain_ready"])
        self.assertEqual(dino["complete_sdk_claim_progress_contribution"], 0)
        self.assertIn("signature_report_build_failed", dino["focused_checker_report"]["blocker_reasons"])
        self.assertEqual(
            dino["blocker_parity"]["umbrella_blocker_reason"],
            "dino_scalar_checker_blocked_or_not_ready",
        )

    def test_transfer_scriptstruct_source_report_overclaim_fails_umbrella_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = scriptstruct_build_tool.build_report(
                snapshot_root=REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots",
                target_sets=[transfer_scriptstruct_readiness.TARGET_SET],
            )
            report["public_sdk_ready"] = True
            report["complete_sdk_ready"] = True
            report_path = Path(tmp) / "transfer-scriptstruct-source-report.json"
            report_path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")

            result = self.run_checker(transfer_scriptstruct_report=report_path, check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("transfer_scriptstruct_checker_blocked", payload["blockers"])
        transfer_scriptstruct = payload["transfer_scriptstruct_leaf_blocker_accounting"]
        self.assertEqual(transfer_scriptstruct["outcome"], "blocked_accounting")
        self.assertFalse(transfer_scriptstruct["public_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["complete_sdk_ready"])
        self.assertFalse(transfer_scriptstruct["counts_toward_complete_sdk_claim"])
        self.assertIn("readiness_alias_overclaim", transfer_scriptstruct["focused_checker_report"]["blocker_reasons"])

    def test_focused_transfer_scriptstruct_report_rejects_missing_fields_and_completion_counts(self) -> None:
        report = transfer_scriptstruct_readiness.build_report()
        report["summary"] = copy.deepcopy(report["summary"])
        report["summary"].pop("bool_tail_fields")
        report["stable_sdk_ready"] = True
        report["v1_completion_progress_contribution"] = 1
        blockers: list[dict] = []

        accounting.validate_transfer_scriptstruct_report(report, blockers)

        reasons = {item["reason"] for item in blockers}
        self.assertIn("transfer_scriptstruct_bool_tail_fields_mismatch", reasons)
        self.assertIn("transfer_scriptstruct_optional_public_or_completion_claim", reasons)
        self.assertIn("transfer_scriptstruct_optional_progress_contribution_nonzero", reasons)

    def test_focused_dino_report_rejects_missing_fields_and_completion_counts(self) -> None:
        report = dino_scalar_readiness.build_report(REPO_ROOT)
        report["summary"] = copy.deepcopy(report["summary"])
        report["summary"]["precall_copied_fields"] = report["summary"]["precall_copied_fields"][:-1]
        report["complete_sdk_ready"] = True
        report["v1_completion_progress_contribution"] = 1
        blockers: list[dict] = []

        accounting.validate_dino_scalar_report(report, blockers)

        reasons = {item["reason"] for item in blockers}
        self.assertIn("dino_scalar_summary_field_mismatch", reasons)
        self.assertIn("dino_scalar_optional_public_or_completion_claim", reasons)
        self.assertIn("dino_scalar_optional_progress_contribution_nonzero", reasons)

    def test_focused_tribe_and_buff_overclaims_do_not_emit_internal_planning_accounting(self) -> None:
        manifest = load_manifest()
        gameplay = surface(manifest)
        blockers: list[dict] = []
        leaves = accounting.leaf_map(gameplay, blockers)
        leaf_family = accounting.build_leaf_family_accounting(
            gameplay,
            leaves,
            accounting.release_statement_outcome(""),
            "candidate_only",
            blockers,
        )

        tribe_report = accounting.build_tribe_scalar_boundary_report(accounting.DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT)
        tribe_report["public_sdk_ready"] = True
        tribe_report["source_ready"] = True
        tribe_blockers: list[dict] = []
        accounting.validate_tribe_scalar_boundary_report(tribe_report, tribe_blockers)
        tribe_leaf = accounting.build_tribe_leaf_blocker_accounting(leaves, leaf_family, tribe_report)

        tribe_reasons = {item["reason"] for item in tribe_blockers}
        self.assertIn("tribe_scalar_boundary_public_or_runtime_claim", tribe_reasons)
        self.assertIn("tribe_scalar_boundary_optional_public_or_runtime_claim", tribe_reasons)
        self.assertFalse(tribe_leaf["accepted_for_internal_planning"])
        self.assertEqual(tribe_leaf["outcome"], "blocked_accounting")
        self.assertFalse(tribe_leaf["scalar_boundary"]["checker_ready"])
        self.assertFalse(tribe_leaf["scalar_boundary"]["tribe_scalar_boundary_ready"])
        self.assertEqual(tribe_leaf["scalar_boundary"]["accepted_scalar_count"], 0)
        self.assertFalse(tribe_leaf["public_sdk_ready"])
        self.assertFalse(tribe_leaf["runtime_ready"])
        self.assertFalse(tribe_leaf["promotion_ready"])

        buff_report = accounting.build_buff_status_report(accounting.DEFAULT_BUFF_STATUS_SNAPSHOT_ROOT)
        buff_report["public_sdk_ready"] = True
        buff_report["source_ready"] = True
        buff_report["complete_sdk_claim_progress_contribution"] = 1
        buff_blockers: list[dict] = []
        accounting.validate_buff_status_report(buff_report, buff_blockers)
        buff_leaf = accounting.build_buff_leaf_blocker_accounting(leaves, leaf_family, buff_report)

        buff_reasons = {item["reason"] for item in buff_blockers}
        self.assertIn("buff_status_public_or_runtime_claim", buff_reasons)
        self.assertIn("buff_status_optional_public_or_runtime_claim", buff_reasons)
        self.assertIn("buff_status_progress_contribution_nonzero", buff_reasons)
        self.assertFalse(buff_leaf["accepted_for_internal_planning"])
        self.assertEqual(buff_leaf["outcome"], "blocked_accounting")
        self.assertFalse(buff_leaf["scalar_boundary"]["checker_ready"])
        self.assertFalse(buff_leaf["scalar_boundary"]["buff_status_candidate_ready"])
        self.assertEqual(buff_leaf["scalar_boundary"]["copied_bool_count"], 0)
        self.assertFalse(buff_leaf["public_sdk_ready"])
        self.assertFalse(buff_leaf["runtime_ready"])
        self.assertFalse(buff_leaf["promotion_ready"])

    def test_transfer_candidate_leaf_rejects_ready_and_resource_handle_overclaims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["transfer"]["evidence"] = {
            "public_sdk_ready": True,
            "nested": {"runtime_ready": True},
            "claim": "ResourceHandle lookup ready for transfer payloads",
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_evidence_forbidden_claim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            fields,
            {
                "$.leaf_decision_units[transfer].evidence.public_sdk_ready",
                "$.leaf_decision_units[transfer].evidence.nested.runtime_ready",
            },
        )
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_evidence_forbidden_claim"
        }
        self.assertIn("ResourceHandle", claims)
        self.assertIn("lookup", claims)

    def test_candidate_leaf_rejects_nested_secondary_completion_aliases(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "nested": {
                "counts_toward_complete_sdk_claim": True,
                "stable_claim_allowed": True,
                "complete-sdk-claim-allowed": True,
                "countsForPublicSdkV1": True,
                "v1_completion_ready": True,
                "v1CompletionContribution": 1,
                "p0DependencyChainReady": True,
                "countsTowardP0DependencyChainClaim": True,
                "promotion_status": "promoted",
                "public_module": {
                    "status": "accepted",
                    "result": "validated",
                    "outcome": "ready",
                    "progress": 1,
                },
                "runtime_capture": {
                    "outcome": "enabled",
                    "progress": 1,
                },
                "live_ops": {
                    "stable": True,
                },
                "v1_readiness": {
                    "result": "v1-ready",
                },
            },
            "claim": (
                "This side lane counts toward the complete SDK claim, contributes to v1 completion, "
                "and makes the P0 dependency chain ready."
            ),
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim" and "label" in item
        }
        self.assertTrue(
            {
                "$.leaf_decision_units[buff_status].evidence.nested.counts_toward_complete_sdk_claim",
                "$.leaf_decision_units[buff_status].evidence.nested.stable_claim_allowed",
                "$.leaf_decision_units[buff_status].evidence.nested.complete-sdk-claim-allowed",
                "$.leaf_decision_units[buff_status].evidence.nested.countsForPublicSdkV1",
                "$.leaf_decision_units[buff_status].evidence.nested.v1_completion_ready",
                "$.leaf_decision_units[buff_status].evidence.nested.v1CompletionContribution",
                "$.leaf_decision_units[buff_status].evidence.nested.p0DependencyChainReady",
                "$.leaf_decision_units[buff_status].evidence.nested.countsTowardP0DependencyChainClaim",
                "$.leaf_decision_units[buff_status].evidence.nested.promotion_status",
                "$.leaf_decision_units[buff_status].evidence.nested.public_module.status",
                "$.leaf_decision_units[buff_status].evidence.nested.public_module.result",
                "$.leaf_decision_units[buff_status].evidence.nested.public_module.outcome",
                "$.leaf_decision_units[buff_status].evidence.nested.public_module.progress",
                "$.leaf_decision_units[buff_status].evidence.nested.runtime_capture.outcome",
                "$.leaf_decision_units[buff_status].evidence.nested.runtime_capture.progress",
                "$.leaf_decision_units[buff_status].evidence.nested.live_ops.stable",
                "$.leaf_decision_units[buff_status].evidence.nested.v1_readiness.result",
                "$.leaf_decision_units[buff_status].evidence",
            }.issubset(fields)
        )
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim" and "claim" in item
        }
        self.assertIn("counts toward the complete SDK claim", claims)
        self.assertIn("contributes to v1 completion", claims)
        self.assertIn("P0 dependency chain ready", claims)

    def test_candidate_leaf_metadata_rejects_status_support_tier_and_release_overclaims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["transfer"]["status"] = "release_ready"
        leaf_units["transfer"]["support_tier"] = "release-supported"
        leaf_units["transfer"]["release_supported"] = True
        leaf_units["transfer"]["notes"] = (
            "Support-tier is active. Release readiness is satisfied. Stable SDK is allowed."
        )

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_metadata_marker_overclaim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim" and "label" in item
        }
        self.assertIn("$.leaf_decision_units[transfer].status", fields)
        self.assertIn("$.leaf_decision_units[transfer].release_supported", fields)
        marker_fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_metadata_marker_overclaim"
        }
        self.assertIn("$.leaf_decision_units[transfer].status", marker_fields)
        self.assertIn("$.leaf_decision_units[transfer].support_tier", marker_fields)
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim" and "claim" in item
        }
        self.assertIn("Support-tier is active", claims)
        self.assertIn("Release readiness is satisfied", claims)
        self.assertIn("Stable SDK is allowed", claims)

    def test_candidate_leaf_rejects_public_module_alias_true_fields(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["dino_policy"]["evidence"] = {
            "public_module_sdk_ready": True,
            "callback_ready": True,
            "descriptor_ready": True,
            "capability_ready": True,
            "resource_handle_available": True,
            "v1_accounted": True,
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            fields,
            {
                "$.leaf_decision_units[dino_policy].evidence.public_module_sdk_ready",
                "$.leaf_decision_units[dino_policy].evidence.callback_ready",
                "$.leaf_decision_units[dino_policy].evidence.descriptor_ready",
                "$.leaf_decision_units[dino_policy].evidence.capability_ready",
                "$.leaf_decision_units[dino_policy].evidence.resource_handle_available",
                "$.leaf_decision_units[dino_policy].evidence.v1_accounted",
            },
        )

    def test_buff_candidate_leaf_rejects_status_runtime_and_payload_alias_true_fields(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "buff_status_sdk_ready": True,
            "module_sdk_ready": True,
            "runtime_wiring_ready": True,
            "dispatcher_ready": True,
            "copied_payload_policy_ready": True,
            "lifecycle_semantics_ready": True,
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            fields,
            {
                "$.leaf_decision_units[buff_status].evidence.buff_status_sdk_ready",
                "$.leaf_decision_units[buff_status].evidence.module_sdk_ready",
                "$.leaf_decision_units[buff_status].evidence.runtime_wiring_ready",
                "$.leaf_decision_units[buff_status].evidence.dispatcher_ready",
                "$.leaf_decision_units[buff_status].evidence.copied_payload_policy_ready",
                "$.leaf_decision_units[buff_status].evidence.lifecycle_semantics_ready",
            },
        )

    def test_candidate_leaf_rejects_metadata_public_runtime_abi_alias_claims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["allowed_v1_outcome"] = (
            "Public Buff module SDK is available; Buff C ABI callback capability is published; "
            "runtime observer wiring is available; Resource Handle identity is usable; v1 completion follows."
        )

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_metadata_forbidden_claim", report["blockers"])
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_metadata_forbidden_claim"
        }
        self.assertIn("Public Buff module", claims)
        self.assertIn("Buff C ABI", claims)
        self.assertIn("capability is published", claims)
        self.assertIn("runtime observer", claims)
        self.assertIn("Resource Handle", claims)
        self.assertIn("identity", claims)
        self.assertIn("v1 completion", claims)

    def test_candidate_leaf_rejects_surface_level_per_leaf_overclaims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        gameplay["promotion_evidence_by_leaf"] = {
            "mission": {
                "public_sdk_ready": True,
                "nested": {"runtime_ready": True},
            },
            "transfer": {
                "claim": "ResourceHandle lookup ready for transfer payloads",
            },
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("mission_leaf_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_evidence_forbidden_claim", report["blockers"])
        ready_fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "mission_leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            ready_fields,
            {
                "$.promotion_evidence_by_leaf[mission].public_sdk_ready",
                "$.promotion_evidence_by_leaf[mission].nested.runtime_ready",
            },
        )
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_evidence_forbidden_claim"
        }
        self.assertIn("ResourceHandle", claims)
        self.assertIn("lookup", claims)

    def test_candidate_surface_rejects_public_runtime_target_set_markers(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        gameplay["evidence"]["planning_target_sets"].append("mission-public-sdk-runtime-ready")
        gameplay["evidence"]["planning_target_sets"].append("transfer-p0-dependency-chain-ready")
        gameplay["evidence"]["source_marker"] = "approved_runtime_bundle"

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surface_candidate_marker_overclaim", report["blockers"])
        details = [
            item
            for item in report["blocker_details"]
            if item["reason"] == "surface_candidate_marker_overclaim"
        ]
        labels = {item["label"] for item in details}
        self.assertIn("$.surface.evidence.planning_target_sets[8]", labels)
        self.assertIn("$.surface.evidence.planning_target_sets[9]", labels)
        self.assertIn("$.surface.evidence.source_marker", labels)

    def test_candidate_evidence_rejects_side_lane_source_shortcut_artifacts(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        gameplay["evidence"]["source_overclaim_total_flag_count"] = 0
        gameplay["evidence"]["passive_snapshot"] = {
            "status": "passive_snapshot_non_evidence",
            "passive_snapshot_evidence_allowed": False,
        }
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["transfer"]["evidence"] = {
            "source_overclaim_summary": {"total": 0},
            "principal_start_end_runtime_evidence": {
                "ready_scope": "principal_start_end_runtime_evidence_only",
                "principal_start_end_runtime_evidence_ready": False,
                "resolved_inputs": ["runtime.lifecycle_start_end_evidence"],
            },
            "target_set_alias": "transfer-runtime-ready",
            "target_sets": [
                "transfer-ufunction-intake",
                "transfer-baccept-only-policy-slice",
                "transfer-scriptstruct",
            ],
            "targetSetStatus": "accepted",
            "target_set_progress": 1,
            "sourceTargetSetReadiness": "ready",
            "multi_surface_beta_capture_plan_queue": {
                "status": "ready",
                "countsTowardSdk": True,
            },
            "current_route_blocker": "identity_public_contract_gate_missing",
            "clearsApprovedRuntimeEvidenceMissing": "cleared",
            "package_shape": {"passed": True},
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        reasons = {item["reason"] for item in report["blocker_details"]}
        self.assertIn("source_overclaim_zero_not_allowed", reasons)
        self.assertIn("passive_snapshot_source_not_allowed", reasons)
        self.assertIn("copied_start_end_player_evidence_not_allowed", reasons)
        self.assertIn("non_current_target_alias", reasons)
        self.assertIn("positive_status_alias_source_not_allowed", reasons)
        self.assertIn("sdk_p0_progress_source_alias_not_allowed", reasons)
        self.assertIn("approved_runtime_evidence_missing_not_preserved", reasons)
        self.assertIn("approved_runtime_evidence_missing_clearance_not_allowed", reasons)
        self.assertIn("package_shape_source_alias_not_allowed", reasons)
        labels = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"]
            in {"positive_status_alias_source_not_allowed", "sdk_p0_progress_source_alias_not_allowed"}
        }
        self.assertIn("$.leaf_decision_units[transfer].evidence.targetSetStatus", labels)
        self.assertIn("$.leaf_decision_units[transfer].evidence.target_set_progress", labels)
        self.assertIn("$.leaf_decision_units[transfer].evidence.sourceTargetSetReadiness", labels)

    def test_candidate_leaf_rejects_reflection_and_source_marker_promotion_claims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "reflection_evidence": {
                "status": "promoted-runtime-ready",
                "resource_handle_status": "available",
            },
            "source_target_set": "buff-v1-completion",
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_marker_overclaim", report["blockers"])
        details = [
            item
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_marker_overclaim"
        ]
        labels = {item["label"] for item in details}
        self.assertIn("$.leaf_decision_units[buff_status].evidence.reflection_evidence.status", labels)
        self.assertIn(
            "$.leaf_decision_units[buff_status].evidence.reflection_evidence.resource_handle_status",
            labels,
        )
        self.assertIn("$.leaf_decision_units[buff_status].evidence.source_target_set", labels)

    def test_release_statement_rejects_module_sdk_and_header_callback_readiness(self) -> None:
        statement = (
            f"{SURFACE_ID}: excluded - mission excluded; transfer excluded; "
            "dino_policy excluded; tribe_policy excluded; buff_status excluded. "
            "Module SDK is ready. ABI header callbacks are available. "
            "Header callbacks are enabled for copied bool lanes.\n"
        )
        result = self.run_checker(statement=statement, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("release_statement_forbidden_claims", report["blockers"])
        self.assertIn("release_statement_ready_overclaims", report["blockers"])
        self.assertIn("Module SDK", report["release_statement"]["forbidden_claims"])
        self.assertIn("ABI header callbacks", report["release_statement"]["forbidden_claims"])
        self.assertIn("Header callbacks", report["release_statement"]["forbidden_claims"])
        self.assertIn("Module SDK is ready", report["release_statement"]["ready_claims"])
        self.assertIn("ABI header callbacks are available", report["release_statement"]["ready_claims"])
        self.assertIn("Header callbacks are enabled", report["release_statement"]["ready_claims"])

    def test_candidate_evidence_rejects_module_sdk_and_header_callback_readiness(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        gameplay["evidence"]["notes"] = (
            "The copied bool policy slice makes the module SDK available, header callbacks published, "
            "support-tier active, and release readiness satisfied."
        )
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "bool_tail_evidence": (
                "Bool-tail evidence completes the module SDK, ABI header callbacks are ready, "
                "and stable SDK is allowed."
            )
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surface_candidate_evidence_forbidden_claim", report["blockers"])
        self.assertIn("surface_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_evidence_forbidden_claim", report["blockers"])
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] in {"surface_candidate_evidence_forbidden_claim", "leaf_candidate_evidence_forbidden_claim"}
        }
        self.assertIn("module SDK", claims)
        self.assertIn("header callbacks", claims)
        self.assertIn("ABI header callbacks", claims)
        ready_claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] in {"surface_candidate_ready_overclaim", "leaf_candidate_ready_overclaim"}
            and "claim" in item
        }
        self.assertIn("support-tier active", ready_claims)
        self.assertIn("release readiness satisfied", ready_claims)
        self.assertIn("stable SDK is allowed", ready_claims)

    def test_candidate_evidence_allows_negated_module_sdk_and_header_callback_non_claims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {
            "notes": (
                "The copied bool policy slice does not promote a module SDK. "
                "ABI header callbacks remain blocked and no header callbacks are available."
            )
        }

        result = self.run_checker(manifest=manifest)
        report = json.loads(result.stdout)

        self.assertTrue(report["ready"])
        self.assertEqual(report["blockers"], [])

    def test_candidate_text_rejects_public_runtime_policy_and_abi_aliases(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {"notes": "Mission SDK ready for this copied-bool lane."}
        leaf_units["transfer"]["evidence"] = {"notes": "Transfer runtime unlocked for this transfer slice."}
        leaf_units["dino_policy"]["evidence"] = {"notes": "Dino policy unblocked for v1."}
        leaf_units["tribe_policy"]["evidence"] = {"notes": "Tribe policy promoted for v1."}
        leaf_units["buff_status"]["evidence"] = {
            "notes": "Buff status public ABI unlocked; ResourceHandle mutation callback ready."
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("mission_leaf_candidate_evidence_forbidden_claim", report["blockers"])
        self.assertIn("mission_leaf_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_evidence_forbidden_claim", report["blockers"])
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        forbidden_claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"]
            in {
                "mission_leaf_candidate_evidence_forbidden_claim",
                "leaf_candidate_evidence_forbidden_claim",
            }
        }
        ready_claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] in {"mission_leaf_candidate_ready_overclaim", "leaf_candidate_ready_overclaim"}
            and "claim" in item
        }
        for expected in (
            "Mission SDK",
            "Dino policy unblocked",
            "Tribe policy promoted",
            "Buff status public ABI",
            "ResourceHandle",
            "mutation",
            "callback ready",
        ):
            self.assertIn(expected, forbidden_claims)
        for expected in (
            "Mission SDK ready",
            "Transfer runtime unlocked",
            "Buff status public ABI unlocked",
        ):
            self.assertIn(expected, ready_claims)

    def test_candidate_leaf_rejects_camelcase_and_bare_public_runtime_v1_alias_flags(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["mission"]["evidence"] = {"missionSdkReady": True}
        leaf_units["transfer"]["evidence"] = {"transferRuntimeReady": True}
        leaf_units["dino_policy"]["evidence"] = {"dinoPolicyPromoted": True}
        leaf_units["tribe_policy"]["evidence"] = {"tribePolicyStatus": "promoted"}
        leaf_units["buff_status"]["evidence"] = {
            "buffStatusPublicABIReady": True,
            "resourceHandle": True,
            "mutation": True,
            "callback": True,
            "countsTowardCompleteSdkClaim": True,
            "countsForPublicSdkV1": True,
            "v1CompletionContribution": 1,
            "publicSdkProgress": 1,
            "publicSdkCredits": 1,
            "runtimeUnlocked": True,
            "runtimeCapture": {"status": "accepted", "unblocked": True},
            "p0DependencyChainReady": True,
            "countsTowardP0DependencyChainClaim": True,
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("mission_leaf_candidate_ready_overclaim", report["blockers"])
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        ready_fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] in {"mission_leaf_candidate_ready_overclaim", "leaf_candidate_ready_overclaim"}
        }
        self.assertTrue(
            {
                "$.leaf_decision_units[mission].evidence.missionSdkReady",
                "$.leaf_decision_units[transfer].evidence.transferRuntimeReady",
                "$.leaf_decision_units[dino_policy].evidence.dinoPolicyPromoted",
                "$.leaf_decision_units[tribe_policy].evidence.tribePolicyStatus",
                "$.leaf_decision_units[buff_status].evidence.buffStatusPublicABIReady",
                "$.leaf_decision_units[buff_status].evidence.resourceHandle",
                "$.leaf_decision_units[buff_status].evidence.mutation",
                "$.leaf_decision_units[buff_status].evidence.callback",
                "$.leaf_decision_units[buff_status].evidence.countsTowardCompleteSdkClaim",
                "$.leaf_decision_units[buff_status].evidence.countsForPublicSdkV1",
                "$.leaf_decision_units[buff_status].evidence.v1CompletionContribution",
                "$.leaf_decision_units[buff_status].evidence.publicSdkProgress",
                "$.leaf_decision_units[buff_status].evidence.publicSdkCredits",
                "$.leaf_decision_units[buff_status].evidence.runtimeUnlocked",
                "$.leaf_decision_units[buff_status].evidence.runtimeCapture.status",
                "$.leaf_decision_units[buff_status].evidence.runtimeCapture.unblocked",
                "$.leaf_decision_units[buff_status].evidence.p0DependencyChainReady",
                "$.leaf_decision_units[buff_status].evidence.countsTowardP0DependencyChainClaim",
            }.issubset(ready_fields)
        )

    def test_candidate_leaf_rejects_source_ready_split_claims(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["transfer"]["evidence"] = {
            "sourceReady": True,
            "sourceStatus": "accepted",
            "source": {
                "ready": True,
                "status": "accepted",
                "progress": 1,
            },
            "readiness": {"approved": True},
            "v1": {"complete": True},
            "public_sdk": {"enabled": True},
            "runtime": {"validated": True, "unblocked": True},
            "v1_sdk": {"credits": 1},
            "candidate": {"accepted": True},
            "package_shape": {"passed": True},
            "support_tier": {"active": True},
            "plugin_hub": {"ready": True},
            "target_set": {"promoted": True},
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        ready_fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim"
        }
        self.assertIn("$.leaf_decision_units[transfer].evidence.sourceReady", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.sourceStatus", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.source.ready", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.source.status", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.source.progress", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.readiness.approved", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.v1.complete", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.public_sdk.enabled", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.runtime.validated", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.runtime.unblocked", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.v1_sdk.credits", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.candidate.accepted", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.package_shape.passed", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.support_tier.active", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.plugin_hub.ready", ready_fields)
        self.assertIn("$.leaf_decision_units[transfer].evidence.target_set.promoted", ready_fields)

    def test_candidate_leaf_rejects_numeric_credit_progress_aliases(self) -> None:
        manifest = candidate_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "accepted_for_candidate_review": True,
            "consume_only": True,
            "candidate_only": True,
            "completeSdkClaimCredit": 1,
            "publicSdkCredits": 2,
            "v1Credit": 1,
            "p0DependencyChainCredit": 1,
            "publicSdkCount": 1,
            "sdkCount": 1,
            "stableSdkCount": 1,
            "runtimeCount": 1,
            "publicSdkSurfaceCount": 1,
            "completeSdkCount": 1,
            "completeSdkClaimCount": 1,
            "p0DependencyChainCount": 1,
            "completeSdkClaimProgressRatio": "1/12",
            "p0DependencyChainClaimProgressRatio": "1/4",
            "publicSdkProgress": "1/12",
            "v1CompletionProgress": "1/8",
        }

        result = self.run_checker(manifest=manifest, check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("leaf_candidate_ready_overclaim", report["blockers"])
        ready_fields = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim"
        }
        self.assertEqual(
            {
                "$.leaf_decision_units[buff_status].evidence.completeSdkClaimCredit",
                "$.leaf_decision_units[buff_status].evidence.publicSdkCredits",
                "$.leaf_decision_units[buff_status].evidence.v1Credit",
                "$.leaf_decision_units[buff_status].evidence.p0DependencyChainCredit",
                "$.leaf_decision_units[buff_status].evidence.publicSdkCount",
                "$.leaf_decision_units[buff_status].evidence.sdkCount",
                "$.leaf_decision_units[buff_status].evidence.stableSdkCount",
                "$.leaf_decision_units[buff_status].evidence.runtimeCount",
                "$.leaf_decision_units[buff_status].evidence.publicSdkSurfaceCount",
                "$.leaf_decision_units[buff_status].evidence.completeSdkCount",
                "$.leaf_decision_units[buff_status].evidence.completeSdkClaimCount",
                "$.leaf_decision_units[buff_status].evidence.p0DependencyChainCount",
                "$.leaf_decision_units[buff_status].evidence.completeSdkClaimProgressRatio",
                "$.leaf_decision_units[buff_status].evidence.p0DependencyChainClaimProgressRatio",
                "$.leaf_decision_units[buff_status].evidence.publicSdkProgress",
                "$.leaf_decision_units[buff_status].evidence.v1CompletionProgress",
            },
            ready_fields,
        )

    def test_manifest_split_and_release_inputs_reject_protected_paths_before_read(self) -> None:
        missing_path = Path("/tmp/obelisk-side-lane-missing-input.json")

        with mock.patch.object(
            accounting,
            "reject_protected_input_path",
            side_effect=SystemExit("simulated protected input path"),
        ):
            with self.assertRaisesRegex(SystemExit, "simulated protected input path"):
                accounting.load_json(missing_path, "manifest")
            with self.assertRaisesRegex(SystemExit, "simulated protected input path"):
                accounting.read_optional(missing_path, "split_note")
            with self.assertRaisesRegex(SystemExit, "simulated protected input path"):
                accounting.read_optional(missing_path, "release_statement")


if __name__ == "__main__":
    unittest.main()
