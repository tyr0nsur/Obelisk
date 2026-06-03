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


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_transfer_dino_tribe_v1_outcome_accounting.py"
MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ["mission", "transfer", "dino_policy", "tribe_policy", "buff_status"]


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def surface(manifest: dict) -> dict:
    return next(item for item in manifest["surfaces"] if item["id"] == SURFACE_ID)


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
    def run_checker(
        self,
        manifest: dict | None = None,
        statement: str | None = None,
        split_note: str | None = None,
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

    def test_current_manifest_accepts_candidate_only_accounting(self) -> None:
        result = self.run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1")
        self.assertTrue(report["ready"])
        self.assertEqual(report["accounting_route"], "candidate_only")
        self.assertFalse(report["v1_accounted"])
        self.assertTrue(report["candidate_only"])
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
        self.assertTrue(mission["internal_reusable_evidence_only"])
        self.assertFalse(mission["v1_accounted"])
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

    def test_release_statement_rejects_missing_leaf_exclusion(self) -> None:
        statement = excluded_release_statement().replace("buff_status excluded. ", "")
        result = self.run_checker(statement=statement, check=False)
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
        result = self.run_checker(statement=statement, check=False)
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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
            result = self.run_checker(tribe_snapshot_root=missing_root, check=False)
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

    def test_buff_leaf_accounting_fails_closed_when_status_checker_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_root = Path(tmp) / "missing-snapshots"
            result = self.run_checker(buff_snapshot_root=missing_root, check=False)
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

    def test_transfer_candidate_leaf_rejects_ready_and_resource_handle_overclaims(self) -> None:
        manifest = load_manifest()
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
        manifest = load_manifest()
        gameplay = surface(manifest)
        leaf_units = {leaf["id"]: leaf for leaf in gameplay["leaf_decision_units"]}
        leaf_units["buff_status"]["evidence"] = {
            "nested": {
                "counts_toward_complete_sdk_claim": True,
                "stable_claim_allowed": True,
                "complete-sdk-claim-allowed": True,
                "v1_completion_ready": True,
                "promotion_status": "promoted",
            },
            "claim": "This side lane counts toward the complete SDK claim.",
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
                "$.leaf_decision_units[buff_status].evidence.nested.v1_completion_ready",
                "$.leaf_decision_units[buff_status].evidence.nested.promotion_status",
                "$.leaf_decision_units[buff_status].evidence",
            }.issubset(fields)
        )
        claims = {
            item["claim"]
            for item in report["blocker_details"]
            if item["reason"] == "leaf_candidate_ready_overclaim" and "claim" in item
        }
        self.assertIn("counts toward the complete SDK claim", claims)

    def test_candidate_leaf_metadata_rejects_status_support_tier_and_release_overclaims(self) -> None:
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
        gameplay = surface(manifest)
        gameplay["evidence"]["planning_target_sets"].append("mission-public-sdk-runtime-ready")
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
        self.assertIn("$.surface.evidence.source_marker", labels)

    def test_candidate_leaf_rejects_reflection_and_source_marker_promotion_claims(self) -> None:
        manifest = load_manifest()
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
        manifest = load_manifest()
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
        manifest = load_manifest()
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


if __name__ == "__main__":
    unittest.main()
