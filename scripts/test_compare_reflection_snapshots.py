#!/usr/bin/env python3
"""Tests for compare_reflection_snapshots.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import compare_reflection_snapshots as compare

ASSEMBLE_RC_SCRIPT = SCRIPT_DIR / "assemble_rc_ufunction_second_source_root.py"


def base_snapshot() -> dict[str, object]:
    return {
        "schema": "obelisk.ufunction-chain.snapshot.v1",
        "evidence": {
            "ark_binary_sha256": "a" * 64,
            "artifact_kind": "offline_core",
            "artifact_sha256": "1" * 64,
            "capture_id": "primary-core",
            "evidence_pack_id": "primary-pack",
            "generated_by": "scripts/inspect_core_ufunctions.py --snapshot-json",
            "obelisk_commit": "1111111",
            "source": "offline_core",
            "status": "candidate-only",
        },
        "metadata": {"object_count": 1, "max_object_scan": 10},
        "targets": [
            {
                "inspection_mode": "ufunction",
                "status": "candidate",
                "reject_reasons": [],
                "membership": {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"},
                "target": {
                    "kind": "index",
                    "value": 10,
                    "object_index": 10,
                    "name": "CanUse",
                    "name_index": 100,
                    "class_name": "Function",
                    "class_name_index": 200,
                    "class_object_index": 300,
                    "outer_name": "PrimalItem",
                    "outer_name_index": 400,
                    "outer_class_name": "Class",
                    "outer_object_index": 500,
                },
                "num_parms": 2,
                "parms_size": 2,
                "function_flags": "0x204000",
                "return_value_offset": "0x1",
                "property_chain": {
                    "status": "candidate",
                    "reject_reasons": [],
                    "expected_count": 2,
                    "observed_count": 2,
                    "parms_size": 2,
                    "properties": [
                        {
                            "depth": 0,
                            "object_index": 11,
                            "name": "bIgnoreCooldown",
                            "name_index": 101,
                            "class_name": "BoolProperty",
                            "class_name_index": 201,
                            "class_object_index": 301,
                            "offset_internal": 0,
                            "element_size": 1,
                            "array_dim": 1,
                            "property_flags": "0x80",
                            "bool_property_semantics": {
                                "status": "candidate",
                                "reject_reasons": [],
                                "bool_field_size": 1,
                                "bool_byte_offset": 0,
                            },
                            "bool_field_size": 1,
                            "bool_byte_offset": 0,
                            "native_bool": True,
                            "byte_mask": "0xff",
                            "field_mask": "0xff",
                            "status": "candidate",
                            "reject_reasons": [],
                            "membership_status": "candidate-uobject",
                            "class_membership_status": "candidate-uobject",
                            "outer_membership_status": "candidate-uobject",
                        },
                        {
                            "depth": 1,
                            "object_index": 12,
                            "name": "ReturnValue",
                            "name_index": 102,
                            "class_name": "BoolProperty",
                            "class_name_index": 201,
                            "class_object_index": 301,
                            "offset_internal": 1,
                            "element_size": 1,
                            "array_dim": 1,
                            "property_flags": "0x80",
                            "bool_property_semantics": {
                                "status": "candidate",
                                "reject_reasons": [],
                                "bool_field_size": 1,
                                "bool_byte_offset": 0,
                            },
                            "bool_field_size": 1,
                            "bool_byte_offset": 0,
                            "native_bool": True,
                            "byte_mask": "0xff",
                            "field_mask": "0xff",
                            "status": "candidate",
                            "reject_reasons": [],
                            "membership_status": "candidate-uobject",
                            "class_membership_status": "candidate-uobject",
                            "outer_membership_status": "candidate-uobject",
                        },
                    ],
                },
            }
        ],
    }


def scriptstruct_snapshot() -> dict[str, object]:
    payload = deepcopy(base_snapshot())
    payload["schema"] = "obelisk.scriptstruct-chain.snapshot.v1"
    target = payload["targets"][0]  # type: ignore[index]
    target["inspection_mode"] = "script_struct"
    target["target"]["class_name"] = "ScriptStruct"  # type: ignore[index]
    target["target"]["outer_name"] = "PrimalLocalProfile"  # type: ignore[index]
    target["target"]["name"] = "ARKTributeDino"  # type: ignore[index]
    target["properties_size"] = 2  # type: ignore[index]
    target["min_alignment"] = 0  # type: ignore[index]
    target.pop("num_parms", None)  # type: ignore[union-attr]
    target.pop("parms_size", None)  # type: ignore[union-attr]
    target.pop("function_flags", None)  # type: ignore[union-attr]
    target.pop("return_value_offset", None)  # type: ignore[union-attr]
    chain = target["property_chain"]  # type: ignore[index]
    chain["properties_size"] = 2
    chain["expected_count"] = None
    chain.pop("parms_size", None)
    return payload


def write_snapshot(root: Path, payload: dict[str, object], name: str = "PrimalItem.CanUse.snapshot.json") -> Path:
    if "candidate" in root.parts:
        evidence = payload.get("evidence")
        if isinstance(evidence, dict):
            evidence["artifact_kind"] = "offline_core"
            evidence["artifact_sha256"] = "2" * 64
            evidence["capture_id"] = "candidate-core"
            evidence["evidence_pack_id"] = "candidate-pack"
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def rename_target(payload: dict[str, object], *, outer: str, name: str) -> dict[str, object]:
    target = payload["targets"][0]["target"]  # type: ignore[index]
    target["outer_name"] = outer
    target["name"] = name
    return payload


def write_minimal_intake_snapshots(
    base_root: Path,
    candidate_root: Path,
    *,
    mutate_candidate: object | None = None,
) -> None:
    targets = (
        ("sdk_inventory", "PrimalItem", "CanUse"),
        ("sdk_inventory", "PrimalItem", "AllowRemoteAddToInventory"),
        ("sdk_structures", "PrimalStructure", "AllowStructureAccess"),
        ("sdk_structures", "PrimalStructure", "IsAllowedToDemolish"),
    )
    for module, outer, name in targets:
        base_payload = rename_target(base_snapshot(), outer=outer, name=name)
        candidate_payload = deepcopy(base_payload)
        if callable(mutate_candidate):
            mutate_candidate(candidate_payload, outer, name)
        base_dir = base_root / "sha" / module
        candidate_dir = candidate_root / "sha" / module
        base_dir.mkdir(parents=True, exist_ok=True)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        write_snapshot(base_dir, base_payload, f"{outer}.{name}.snapshot.json")
        write_snapshot(candidate_dir, candidate_payload, f"{outer}.{name}.snapshot.json")


def write_target_set_root(root: Path, target_set: str) -> None:
    target_dir = root / "sha" / "sdk_test"
    target_dir.mkdir(parents=True, exist_ok=True)
    for target in compare.TARGET_SETS[target_set]:
        schema, _, short_key = target.partition(":")
        outer, _, name = short_key.partition(".")
        payload = scriptstruct_snapshot() if schema == "obelisk.scriptstruct-chain.snapshot.v1" else base_snapshot()
        payload = rename_target(payload, outer=outer, name=name)
        write_snapshot(target_dir, payload, f"{outer}.{name}.snapshot.json")


def run_compare(base: Path, candidate: Path | None, *extra: str) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "compare_reflection_snapshots.py"),
        "--base-root",
        str(base),
    ]
    if candidate is not None:
        command.extend(["--candidate-root", str(candidate)])
    command.extend(extra)
    return subprocess.run(command, text=True, capture_output=True)


def run_compare_raw(*extra: str) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT_DIR / "compare_reflection_snapshots.py")]
    command.extend(extra)
    return subprocess.run(command, text=True, capture_output=True)


class CompareReflectionSnapshotsTests(unittest.TestCase):
    def test_lists_named_target_sets_without_snapshot_roots(self) -> None:
        result = run_compare_raw("--list-target-sets", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-snapshot-target-sets.v1")
        sets = {item["name"]: item["targets"] for item in report["target_sets"]}
        classifications = {item["name"]: item["readiness_classification"] for item in report["target_sets"]}
        release_flags = {item["name"]: item["release_readiness"] for item in report["target_sets"]}
        self.assertIn("minimal-second-source-intake", sets)
        self.assertEqual(classifications["minimal-second-source-intake"], "release_readiness")
        self.assertIs(release_flags["minimal-second-source-intake"], True)
        self.assertEqual(classifications["buff-compact-intake"], "internal_layout_only")
        self.assertIs(release_flags["buff-compact-intake"], False)
        self.assertEqual(classifications["mission-copied-bool-policy-slice"], "planning_only")
        self.assertIs(release_flags["mission-copied-bool-policy-slice"], False)
        self.assertEqual(classifications["players-identity-lifecycle-intake"], "planning_only")
        self.assertIs(release_flags["players-identity-lifecycle-intake"], False)
        self.assertEqual(classifications["transfer-scriptstruct"], "internal_layout_only")
        self.assertIs(release_flags["transfer-scriptstruct"], False)
        self.assertEqual(
            sets["players-identity-lifecycle-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerListPlayers",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerKickPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerSendChatMessage",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestTribeLog",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.AllowTribeGroupPermission",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.IsInTribe",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveMyTribeOnlineList",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientReceiveActiveMissionTags",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerState.ServerRequestSpawnPointsForDownloadedCharacters",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
            ],
        )
        self.assertEqual(
            sets["structure-nonpin-copied-scalar-policy-slice"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
            ],
        )
        self.assertEqual(
            sets["minimal-second-source-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowRemoteAddToInventory",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
            ],
        )
        self.assertIn("obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse", sets["minimal-second-source-intake"])
        self.assertIn("buff-compact-intake", sets)
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPBuffPreventUploading",
            sets["buff-compact-intake"],
        )
        self.assertEqual(
            sets["buff-breadth-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BuffOverrideInventoryAccessInput",
                "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPCustomAllowAddBuff",
                "obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPPreventAddingOtherBuff",
            ],
        )
        self.assertIn("dino-compact-intake", sets)
        self.assertIn("item-compact-intake", sets)
        self.assertEqual(
            sets["item-compact-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowEquipItem",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanRepair",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CraftBlueprint",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.UseItemOntoItem",
            ],
        )
        self.assertEqual(
            sets["inventory-action-compact-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItem",
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestInventoryUseItemWithActor",
            ],
        )
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:PrimalDinoCharacter.AllowCarryCharacter",
            sets["dino-compact-intake"],
        )
        self.assertIn("transfer-scriptstruct", sets)
        self.assertIn("mission-compact-intake", sets)
        self.assertEqual(
            sets["mission-copied-bool-policy-slice"],
            [
                "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPAllowPlayerToLeaveMission",
                "obelisk.ufunction-chain.snapshot.v1:MissionType.BPOnPlayerRemovedFromMission",
            ],
        )
        self.assertIn("tribe-compact-intake", sets)
        self.assertIn("structure-observer-intake", sets)
        self.assertEqual(
            sets["structure-observer-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.AllowToggleActivation",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.VerifyPinCode",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructureSeating.CanSeat",
            ],
        )
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructureItemContainer.VerifyPinCode",
            sets["structure-observer-intake"],
        )
        self.assertIn("transfer-ufunction-intake", sets)
        self.assertEqual(
            sets["transfer-baccept-only-policy-slice"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerTransferredPlayerConfirmationResult",
            ],
        )
        self.assertIn("obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission", sets["mission-compact-intake"])
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerRequestTribeLog",
            sets["tribe-compact-intake"],
        )
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerUploadDino",
            sets["transfer-ufunction-intake"],
        )

    def test_structure_build_policy_targets_stay_out_of_rc_compact_sets_with_missing_base_gap(self) -> None:
        result = run_compare_raw("--list-target-sets", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        sets = {item["name"]: item["targets"] for item in report["target_sets"]}
        forbidden_targets = {
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild",
        }
        guarded_target_sets = {
            "minimal-second-source-intake",
            "structure-observer-intake",
            "chat-message-intake",
            "buff-compact-intake",
            "dino-compact-intake",
            "item-compact-intake",
            "inventory-action-compact-intake",
            "mission-compact-intake",
            "tribe-compact-intake",
        }
        self.assertTrue(guarded_target_sets.issubset(set(sets)))
        for target_set in guarded_target_sets:
            with self.subTest(target_set=target_set):
                self.assertTrue(forbidden_targets.isdisjoint(set(sets[target_set])))

        result = run_compare_raw(
            "--base-root",
            str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
            "--readiness-report",
            "--target",
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            "--target",
            "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild",
            "--fail-on-base-readiness-gaps",
            "--json",
        )

        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "base_fixture_readiness")
        self.assertEqual(report["totals"]["targets"], 2)
        self.assertEqual(report["totals"]["comparable"], 0)
        self.assertEqual(report["totals"]["blocked"], 2)
        missing_module = next(module for module in report["modules"] if module["module"] == "<missing>")
        self.assertEqual(missing_module["block_reasons"], {"missing_base_snapshot": 2})
        self.assertEqual(
            {detail["target"]: detail["block_reasons"] for detail in missing_module["target_details"]},
            {
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild": ["missing_base_snapshot"],
                "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild": ["missing_base_snapshot"],
            },
        )
        details = {detail["target"]: detail for detail in missing_module["target_details"]}
        primal_guidance = details[
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild"
        ]["guidance"]
        self.assertEqual(primal_guidance["classification"], "second_wave_structure_build_policy_candidate")
        self.assertIn("missing_committed_sanitized_snapshot", primal_guidance["why_blocked"])
        self.assertIn("missing_distinct_second_source_layout", primal_guidance["why_blocked"])
        self.assertIn("approved non-protected copied/offline core", primal_guidance["next_offline_input"])
        self.assertIn(
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            primal_guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "generate one sanitized candidate snapshot for this exact target only before adding any target set",
            primal_guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            primal_guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "keep placement structs, location vectors, player/controller context, object refs, arrays, and raw params redacted or recognition-only",
            primal_guidance["snapshot_prep_checks"],
        )
        self.assertIn("does not promote StructureEvents", primal_guidance["non_claim"])
        self.assertIn(
            "reflected_owner_unproven",
            details["obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild"]["guidance"]["why_blocked"],
        )
        self.assertIn(
            "treat APrimalStructure as an ArkApi dictionary seed until a sanitized snapshot proves the reflected owner",
            details["obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild"]["guidance"][
                "snapshot_prep_checks"
            ],
        )
        self.assertIn(
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            details["obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild"]["guidance"][
                "snapshot_prep_checks"
            ],
        )
        self.assertIs(report["promotion_gate"]["ready"], False)
        self.assertIs(report["promotion_gate"]["layout_ready"], False)
        self.assertIs(report["promotion_gate"]["promotion_ready"], False)
        self.assertEqual(report["promotion_gate"]["ready_scope"], "not_ready")

        text_result = run_compare_raw(
            "--base-root",
            str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
            "--readiness-report",
            "--target",
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("guidance=second_wave_structure_build_policy_candidate", text_result.stdout)
        self.assertIn(
            "why_blocked=missing_committed_sanitized_snapshot,missing_distinct_second_source_layout",
            text_result.stdout,
        )
        self.assertIn("next_offline_input=approved non-protected copied/offline core", text_result.stdout)
        self.assertIn("snapshot_prep_checks=7", text_result.stdout)
        self.assertIn(
            "non_claim=does not promote StructureEvents, build-policy SDK, identity, lookup, mutation",
            text_result.stdout,
        )

    def test_structure_build_policy_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target",
            "PrimalStructure.IsAllowedToBuild",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_filters"], ["PrimalStructure.IsAllowedToBuild"])
        self.assertEqual(len(report["targets"]), 1)
        guidance = report["targets"][0]
        self.assertEqual(
            guidance["target"],
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
        )
        self.assertEqual(guidance["classification"], "second_wave_structure_build_policy_candidate")
        self.assertIn("missing_committed_sanitized_snapshot", guidance["why_blocked"])
        self.assertIn("approved non-protected copied/offline core", guidance["next_offline_input"])
        self.assertEqual(len(guidance["snapshot_prep_checks"]), 7)
        self.assertIn(
            "generate one sanitized candidate snapshot for this exact target only before adding any target set",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "compare only against a distinct sanitized second-source snapshot before any readiness claim",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn("return override", guidance["non_claim"])
        self.assertIn("runtime_hooks", report["not_promoted_surfaces"])

        text_result = run_compare_raw("--list-target-guidance")
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=2 scope=offline_planning_only", text_result.stdout)
        self.assertIn(
            "target=obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild",
            text_result.stdout,
        )
        self.assertIn("snapshot_prep_checks=7", text_result.stdout)

    def test_mission_transfer_target_set_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "mission-copied-bool-policy-slice",
            "--target-set",
            "transfer-baccept-only-policy-slice",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(
            report["target_sets"],
            ["mission-copied-bool-policy-slice", "transfer-baccept-only-policy-slice"],
        )
        self.assertEqual(report["targets"], [])
        guidance = {item["target_set"]: item for item in report["target_set_guidance"]}
        self.assertEqual(
            set(guidance),
            {"mission-copied-bool-policy-slice", "transfer-baccept-only-policy-slice"},
        )
        mission = guidance["mission-copied-bool-policy-slice"]
        self.assertEqual(mission["classification"], "internal_mission_copied_bool_policy_candidate")
        self.assertIn("consume_mode_only", mission["why_blocked"])
        self.assertIn("promote_mode_blocked", mission["why_blocked"])
        self.assertIn("not_release_readiness_target", mission["why_blocked"])
        self.assertIn("public_mission_sdk_blocked", mission["why_blocked"])
        self.assertIn("Mission SDK", mission["non_claim"])
        self.assertIn("mission payload decoding", mission["non_claim"])
        self.assertIn("consume existing offline artifact", mission["next_offline_input"])
        self.assertIn(
            "/home/flowcommunity-ark/obelisk-artifacts/mission-copied-bool-tail-policy-slice-20260530T090211Z/",
            mission["next_offline_input"],
        )
        self.assertIn("pack_sha256=f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945", mission["next_offline_input"])
        self.assertIn(
            "manifest_sha256=b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb",
            mission["next_offline_input"],
        )
        self.assertIn(
            "require AddPlayerToMission, BPAllowPlayerToLeaveMission, and BPOnPlayerRemovedFromMission layouts to be comparable",
            mission["snapshot_prep_checks"],
        )
        self.assertIn(
            "keep GetPlayerUsableItems in mission-compact-intake as recognition-only; do not add it to the copied-bool policy slice",
            mission["snapshot_prep_checks"],
        )
        self.assertIn(
            "keep player/controller/character object refs, item arrays, mission payload identity, and raw params redacted or recognition-only",
            mission["snapshot_prep_checks"],
        )
        self.assertIn(
            "consume-only means offline artifact or sanitized snapshot reads; do not substitute runtime probes, live /servidor/ark inputs, or public SDK layouts",
            mission["snapshot_prep_checks"],
        )
        self.assertIn(
            "do not use this target set for release/readiness or public SDK promotion gates",
            mission["snapshot_prep_checks"],
        )
        transfer = guidance["transfer-baccept-only-policy-slice"]
        self.assertEqual(transfer["classification"], "internal_transfer_baccept_policy_candidate")
        self.assertIn("not_release_readiness_target", transfer["why_blocked"])
        self.assertIn("public_transfer_sdk_blocked", transfer["why_blocked"])
        self.assertIn("Transfer SDK", transfer["non_claim"])
        self.assertIn("transfer payload decoding", transfer["non_claim"])
        self.assertIn(
            "do not use this target set for release/readiness or public SDK promotion gates",
            transfer["snapshot_prep_checks"],
        )
        self.assertIn("public_sdk", report["not_promoted_surfaces"])
        self.assertIn("runtime_hooks", report["not_promoted_surfaces"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "mission-copied-bool-policy-slice",
            "--target-set",
            "transfer-baccept-only-policy-slice",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=0 scope=offline_planning_only target_set_guidance=2", text_result.stdout)
        self.assertIn("target_set=mission-copied-bool-policy-slice", text_result.stdout)
        self.assertIn("target_set=transfer-baccept-only-policy-slice", text_result.stdout)
        self.assertIn("consume_mode_only,promote_mode_blocked,not_release_readiness_target", text_result.stdout)
        self.assertIn("does not promote Mission SDK", text_result.stdout)
        self.assertIn("does not promote Transfer SDK", text_result.stdout)

    def test_internal_transfer_buff_dino_guidance_names_policy_gates(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "transfer-scriptstruct",
            "--target-set",
            "buff-compact-intake",
            "--target-set",
            "dino-compact-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        guidance = {item["target_set"]: item for item in report["target_set_guidance"]}
        self.assertEqual(set(guidance), {"transfer-scriptstruct", "buff-compact-intake", "dino-compact-intake"})
        for target_set, module in (
            ("transfer-scriptstruct", "Transfer"),
            ("buff-compact-intake", "Buff"),
            ("dino-compact-intake", "Dino"),
        ):
            with self.subTest(target_set=target_set):
                item = guidance[target_set]
                self.assertIn("internal_layout_evidence_only", item["why_blocked"])
                self.assertIn("copied_data_policy_unproven", item["why_blocked"])
                self.assertIn("lifecycle_privacy_policy_unproven", item["why_blocked"])
                self.assertIn("promotion_gate_blocked", item["why_blocked"])
                self.assertIn(f"public_{module.lower()}_sdk_blocked", item["why_blocked"])
                self.assertIn(
                    "keep evidence internal until copied-data, lifecycle, privacy, and promotion gates pass",
                    item["snapshot_prep_checks"],
                )
                self.assertIn(f"does not promote {module} SDK", item["non_claim"])

    def test_item_return_target_set_guidance_keeps_release_scope_narrow(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "item-return-only-policy-slice",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["target_sets"], ["item-return-only-policy-slice"])
        self.assertEqual(report["targets"], [])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "item-return-only-policy-slice")
        self.assertEqual(guidance["classification"], "release_gameplay_policy_item_return_only")
        self.assertIn("standalone_items_inventory_sdk_blocked", guidance["why_blocked"])
        self.assertIn("identity_lookup_resourcehandle_blocked", guidance["why_blocked"])
        self.assertIn("mutation_return_override_blocked", guidance["why_blocked"])
        self.assertIn(
            "runtime_producer_validation_requires_separate_approval",
            guidance["why_blocked"],
        )
        for required in (
            "AllowEquipItem",
            "CanRepair",
            "UseItemOntoItem",
            "ReturnValue BoolProperty",
            "GameplayPolicyEvent copied-scalar lane only",
            "runtime producer validation still requires a separate gated debug-window brief",
        ):
            self.assertTrue(
                any(required in item for item in guidance["snapshot_prep_checks"]),
                f"missing guidance term: {required}",
            )
        for blocked in (
            "Items SDK",
            "Inventory SDK",
            "identity",
            "ResourceHandle",
            "mutation",
            "return override",
            "runtime validation",
        ):
            self.assertIn(blocked, guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "item-return-only-policy-slice",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_set_guidance=1", text_result.stdout)
        self.assertIn("release_gameplay_policy_item_return_only", text_result.stdout)
        self.assertIn("does not promote Items SDK, Inventory SDK", text_result.stdout)

    def test_player_identity_lifecycle_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "players-identity-lifecycle-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_sets"], ["players-identity-lifecycle-intake"])
        self.assertEqual(report["targets"], [])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "players-identity-lifecycle-intake")
        self.assertEqual(guidance["classification"], "players_identity_lifecycle_guidance_only_candidate")
        self.assertIn("planning_guidance_only", guidance["why_blocked"])
        self.assertIn("not_release_readiness_target", guidance["why_blocked"])
        self.assertIn("public_player_sdk_blocked", guidance["why_blocked"])
        self.assertIn("public player identity", guidance["non_claim"])
        self.assertIn("release readiness", guidance["non_claim"])
        self.assertIn(
            "do not use this target set for release/readiness or public SDK promotion gates",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn("public_sdk", report["not_promoted_surfaces"])
        self.assertIn("resource_handle", report["not_promoted_surfaces"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "players-identity-lifecycle-intake",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=0 scope=offline_planning_only target_set_guidance=1", text_result.stdout)
        self.assertIn("target_set=players-identity-lifecycle-intake", text_result.stdout)
        self.assertIn("not_release_readiness_target", text_result.stdout)
        self.assertIn("does not promote Player Identity/Lifecycle SDK", text_result.stdout)

    def test_target_set_guidance_rejects_duplicate_target_set_filter(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "mission-copied-bool-policy-slice",
            "--target-set",
            "mission-copied-bool-policy-slice",
            "--json",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "duplicate target-set guidance filter(s): mission-copied-bool-policy-slice",
            result.stderr,
        )

    def test_target_guidance_rejects_duplicate_explicit_target_filter(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target",
            "PrimalStructure.IsAllowedToBuild",
            "--target",
            "PrimalStructure.IsAllowedToBuild",
            "--json",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "duplicate target guidance filter(s): PrimalStructure.IsAllowedToBuild",
            result.stderr,
        )

    def test_structure_build_policy_guidance_rejects_unmatched_explicit_target(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target",
            "PrimalStructure.DoesNotExist",
            "--json",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "target guidance filter did not match known guidance: PrimalStructure.DoesNotExist",
            result.stderr,
        )

    def test_requires_base_root_unless_listing_target_sets(self) -> None:
        result = run_compare_raw("--readiness-report")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--base-root is required unless --list-target-sets or --list-target-guidance is used",
            result.stderr,
        )

    def test_rejects_allow_ark_sha_mismatch_for_promotion_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()

            result = run_compare(
                base,
                candidate,
                "--readiness-report",
                "--fail-on-readiness-gaps",
                "--allow-ark-sha-mismatch",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--allow-ark-sha-mismatch is incompatible with --fail-on-readiness-gaps", result.stderr)

    def test_rejects_snapshot_roots_under_protected_server_path_before_reading(self) -> None:
        result = run_compare_raw(
            "--base-root",
            "/servidor/ark/obelisk/does-not-need-to-exist",
            "--readiness-report",
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--base-root must not read from protected live-server path", result.stderr)

    def test_rejects_snapshot_roots_symlinked_to_protected_server_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            candidate.mkdir()
            base.symlink_to("/servidor/ark", target_is_directory=True)

            result = run_compare(base, candidate, "--readiness-report")

        self.assertEqual(result.returncode, 1)
        self.assertIn("--base-root must not read from protected live-server path", result.stderr)

    def test_rejects_approved_dump_snapshot_root_symlinked_to_protected_server_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir) / "base"
            base.symlink_to("/servidor/ark/obelisk/dumps/second-source/snapshots", target_is_directory=True)
            result = run_compare_raw(
                "--base-root",
                str(base),
                "--readiness-report",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("--base-root must not read from protected live-server path", result.stderr)

    def test_rejects_textually_protected_snapshot_root_even_when_symlink_resolves_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected_real = root / "protected-real"
            protected_link = root / "protected-link"
            outside = root / "outside"
            protected_real.mkdir()
            outside.mkdir()
            protected_link.symlink_to(protected_real, target_is_directory=True)
            outward_link = protected_link / "outward-link"
            outward_link.symlink_to(outside, target_is_directory=True)

            with mock.patch.object(compare, "PROTECTED_SERVER_ROOT", protected_link):
                with self.assertRaisesRegex(SystemExit, "snapshot root must not read"):
                    compare.reject_protected_input_path("snapshot root", outward_link / "snapshots")

    def test_rejects_snapshot_file_symlinked_to_protected_server_path_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            (base / "linked.snapshot.json").symlink_to("/servidor/ark/obelisk/leaked.snapshot.json")

            result = run_compare(base, candidate, "--readiness-report")

        self.assertEqual(result.returncode, 1)
        self.assertIn("snapshot must not read from protected live-server path", result.stderr)

    def test_allows_approved_offline_workspace_snapshot_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)

            with (
                mock.patch.object(compare, "PROTECTED_SERVER_ROOT", protected),
                mock.patch.object(compare, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
            ):
                compare.reject_protected_input_path("--base-root", workspace / "snapshots")

    def test_rejects_textually_protected_workspace_symlink_resolving_outside(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            protected = root / "server-root"
            workspace = protected / "workspace-offline"
            workspace.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            link = workspace / "outward-link"
            link.symlink_to(outside, target_is_directory=True)

            with (
                mock.patch.object(compare, "PROTECTED_SERVER_ROOT", protected),
                mock.patch.object(compare, "APPROVED_OFFLINE_WORKSPACE_ROOTS", (workspace,)),
                self.assertRaisesRegex(SystemExit, "--base-root must not read"),
            ):
                compare.reject_protected_input_path("--base-root", link / "snapshots")

    def test_missing_generated_by_blocks_comparable_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            left["evidence"].pop("generated_by")  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["status"], "inconclusive")
        self.assertIn("base:evidence_generated_by_None", report["results"][0]["reasons"])

    def test_wrong_generated_by_blocks_comparable_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["generated_by"] = "scripts/other.py"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["status"], "inconclusive")
        self.assertIn("candidate:evidence_generated_by_scripts/other.py", report["results"][0]["reasons"])

    def test_accepts_identical_layout_while_ignoring_indices_and_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["obelisk_commit"] = "2222222"  # type: ignore[index]
            right["metadata"]["object_count"] = 999  # type: ignore[index]
            right["targets"][0]["target"]["object_index"] = 999  # type: ignore[index]
            right["targets"][0]["target"]["name_index"] = 999  # type: ignore[index]
            right["targets"][0]["property_chain"]["properties"][0]["object_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 0, "rejected": 0})

    def test_plain_comparison_with_zero_selected_targets_is_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 0, "inconclusive": 0, "rejected": 0})

    def test_strict_identity_indices_rejects_index_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["target"]["name_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--strict-identity-indices", "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)

    def test_rejects_layout_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["property_chain"]["properties"][1]["offset_internal"] = 2  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertIn("offset_internal", report["results"][0]["diffs"][0]["path"])

    def test_rejects_bool_mask_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["property_chain"]["properties"][1]["field_mask"] = "0x01"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertIn("field_mask", report["results"][0]["diffs"][0]["path"])

    def test_missing_bool_mask_markers_blocks_comparison_even_when_both_sides_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                for prop in payload["targets"][0]["property_chain"]["properties"]:  # type: ignore[index]
                    prop.pop("native_bool", None)
                    prop.pop("byte_mask", None)
                    prop.pop("field_mask", None)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_native_bool_missing", reasons)
        self.assertIn("base:property[0]_byte_mask_missing_or_zero", reasons)
        self.assertIn("base:property[0]_field_mask_missing_or_zero", reasons)
        self.assertIn("candidate:property[1]_native_bool_missing", reasons)
        self.assertIn("candidate:property[1]_byte_mask_missing_or_zero", reasons)
        self.assertIn("candidate:property[1]_field_mask_missing_or_zero", reasons)

    def test_marks_missing_or_raw_snapshot_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["targets"][0]["object"] = "0x12345678"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertTrue(any(reason.startswith("candidate:forbidden_key") for reason in report["results"][0]["reasons"]))

    def test_marks_ark_sha_mismatch_inconclusive_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["ark_binary_sha256"] = "b" * 64  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["ark_binary_sha256_mismatch"])

    def test_marks_missing_artifact_identity_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                evidence = payload["evidence"]  # type: ignore[index]
                evidence.pop("artifact_kind", None)
                evidence.pop("artifact_sha256", None)
                evidence.pop("capture_id", None)
                evidence.pop("evidence_pack_id", None)
            write_snapshot(base, left)
            path = candidate / "PrimalItem.CanUse.snapshot.json"
            path.write_text(json.dumps(right, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["results"][0]["reasons"],
            ["missing_base_evidence_artifact_identity", "missing_candidate_evidence_artifact_identity"],
        )

    def test_marks_same_artifact_identity_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            write_snapshot(base, left)
            path = candidate / "PrimalItem.CanUse.snapshot.json"
            path.write_text(json.dumps(right, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["same_evidence_artifact_identity"])

    def test_marks_shared_capture_id_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            evidence = right["evidence"]  # type: ignore[index]
            evidence["artifact_sha256"] = "2" * 64
            evidence["evidence_pack_id"] = "candidate-pack"
            write_snapshot(base, left)
            path = candidate / "PrimalItem.CanUse.snapshot.json"
            path.write_text(json.dumps(right, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["same_evidence_capture_id"])

    def test_marks_shared_evidence_pack_id_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            evidence = right["evidence"]  # type: ignore[index]
            evidence["artifact_sha256"] = "2" * 64
            evidence["capture_id"] = "candidate-core"
            write_snapshot(base, left)
            path = candidate / "PrimalItem.CanUse.snapshot.json"
            path.write_text(json.dumps(right, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["same_evidence_evidence_pack_id"])

    def test_marks_shared_artifact_sha_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            evidence = right["evidence"]  # type: ignore[index]
            evidence["capture_id"] = "candidate-core"
            evidence["evidence_pack_id"] = "candidate-pack"
            write_snapshot(base, left)
            path = candidate / "PrimalItem.CanUse.snapshot.json"
            path.write_text(json.dumps(right, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["results"][0]["reasons"], ["same_evidence_artifact_sha256"])

    def test_marks_non_offline_candidate_evidence_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["source"] = "runtime_probe"  # type: ignore[index]
            right["evidence"]["status"] = "accepted"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("candidate:evidence_source_runtime_probe", report["results"][0]["reasons"])
        self.assertIn("candidate:evidence_status_accepted", report["results"][0]["reasons"])

    def test_marks_malformed_evidence_identity_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "second"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["artifact_kind"] = "runtime_probe"  # type: ignore[index]
            right["evidence"]["artifact_sha256"] = "not-a-sha"  # type: ignore[index]
            right["evidence"]["capture_id"] = "../capture"  # type: ignore[index]
            right["evidence"]["evidence_pack_id"] = "pack/id"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("candidate:invalid_artifact_kind_runtime_probe", report["results"][0]["reasons"])
        self.assertIn("candidate:invalid_artifact_sha256", report["results"][0]["reasons"])
        self.assertIn("candidate:invalid_capture_id", report["results"][0]["reasons"])
        self.assertIn("candidate:invalid_evidence_pack_id", report["results"][0]["reasons"])

    def test_marks_placeholder_evidence_identity_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "second"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            right["evidence"]["artifact_sha256"] = "2" * 64  # type: ignore[index]
            right["evidence"]["capture_id"] = "unspecified-capture"  # type: ignore[index]
            right["evidence"]["evidence_pack_id"] = "static-global-default-pack"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("candidate:invalid_capture_id", report["results"][0]["reasons"])
        self.assertIn("candidate:invalid_evidence_pack_id", report["results"][0]["reasons"])

    def test_marks_malformed_ark_sha_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            left["evidence"]["ark_binary_sha256"] = "not-a-sha"  # type: ignore[index]
            right["evidence"]["ark_binary_sha256"] = "not-a-sha"  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("base:invalid_ark_binary_sha256", report["results"][0]["reasons"])
        self.assertIn("candidate:invalid_ark_binary_sha256", report["results"][0]["reasons"])

    def test_strict_identity_indices_rejects_nested_index_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
                "inner_property": {
                    "object_index": 2000,
                    "name": "InventoryItems",
                    "name_index": 3000,
                    "class_name": "ObjectProperty",
                    "class_name_index": 4000,
                    "class_object_index": 5000,
                },
            }
            right = deepcopy(left)
            right["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"]["inner_property"]["name_index"] = 999  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            loose = run_compare(base, candidate, "--json")
            strict = run_compare(base, candidate, "--strict-identity-indices", "--json")

        self.assertEqual(loose.returncode, 0, loose.stderr + loose.stdout)
        self.assertEqual(strict.returncode, 1)
        report = json.loads(strict.stdout)
        self.assertEqual(report["counts"]["rejected"], 1)
        self.assertIn("array_inner_candidate.inner_property.name_index", report["results"][0]["diffs"][0]["path"])

    def test_rejected_property_blocks_comparison_even_when_both_sides_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                prop = payload["targets"][0]["property_chain"]["properties"][0]  # type: ignore[index]
                prop["status"] = "rejected"
                prop["reject_reasons"] = ["bad_property_candidate"]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("base:property[0]_status_rejected", report["results"][0]["reasons"])
        self.assertIn("candidate:property[0]_has_reject_reasons", report["results"][0]["reasons"])

    def test_rejected_bool_property_semantics_blocks_comparison_even_when_both_sides_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                prop = payload["targets"][0]["property_chain"]["properties"][0]  # type: ignore[index]
                prop["bool_property_semantics"] = {
                    "status": "rejected",
                    "reject_reasons": ["zero_bool_field_mask"],
                }
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_bool_property_semantics_status_rejected", reasons)
        self.assertIn("candidate:property[0]_bool_property_semantics_status_rejected", reasons)

    def test_missing_bool_tail_blocks_comparison_even_when_both_sides_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                prop = payload["targets"][0]["property_chain"]["properties"][0]  # type: ignore[index]
                prop.pop("bool_field_size", None)
                prop["bool_property_semantics"].pop("bool_field_size", None)  # type: ignore[index]
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_bool_field_size_missing", reasons)
        self.assertIn("candidate:property[0]_bool_property_semantics_bool_field_size_missing", reasons)

    def test_weak_property_membership_blocks_comparison_even_when_both_sides_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                prop = payload["targets"][0]["property_chain"]["properties"][0]  # type: ignore[index]
                prop["membership_status"] = "not-in-gobjects"
                prop.pop("class_membership_status", None)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("base:property[0]_membership_status_not-in-gobjects", report["results"][0]["reasons"])
        self.assertIn("candidate:property[0]_class_membership_status_missing", report["results"][0]["reasons"])

    def test_rejected_nested_property_candidate_blocks_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"] = {  # type: ignore[index]
                "status": "rejected",
                "reject_reasons": ["bad_inner_property"],
                "membership_status": "candidate-uobject",
                "inner_property": {
                    "object_index": 2000,
                    "name": "InventoryItems",
                    "name_index": 3000,
                    "class_name": "ObjectProperty",
                    "class_name_index": 4000,
                    "class_object_index": 5000,
                },
            }
            right = deepcopy(left)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        self.assertIn("base:property[0]_array_inner_candidate_status_rejected", report["results"][0]["reasons"])
        self.assertIn("candidate:property[0]_array_inner_candidate_has_reject_reasons", report["results"][0]["reasons"])

    def test_weak_nested_property_membership_blocks_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "not-in-gobjects",
                "inner_property": {
                    "object_index": 2000,
                    "name": "InventoryItems",
                    "name_index": 3000,
                    "class_name": "ObjectProperty",
                    "class_name_index": 4000,
                    "class_object_index": 5000,
                },
            }
            left["targets"][0]["property_chain"]["properties"][1]["struct_type_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "struct_type": {
                    "object_index": 2001,
                    "name": "ARKTributeDino",
                    "name_index": 3001,
                    "class_name": "ScriptStruct",
                    "class_name_index": 4001,
                    "class_object_index": 5001,
                },
            }
            right = deepcopy(left)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_array_inner_candidate_membership_status_not-in-gobjects", reasons)
        self.assertIn("candidate:property[1]_struct_type_candidate_membership_status_missing", reasons)

    def test_nested_property_candidate_requires_identity_object(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["array_inner_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
            }
            left["targets"][0]["property_chain"]["properties"][1]["struct_type_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
            }
            right = deepcopy(left)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_array_inner_candidate_missing_inner_property", reasons)
        self.assertIn("candidate:property[1]_struct_type_candidate_missing_struct_type", reasons)

    def test_target_filter_limits_comparison_to_requested_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            requested_left = base_snapshot()
            requested_right = deepcopy(requested_left)
            ignored_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="AllowPostProcessEffect")
            ignored_right = deepcopy(ignored_left)
            ignored_right["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 99  # type: ignore[index]
            write_snapshot(base, requested_left)
            write_snapshot(candidate, requested_right)
            write_snapshot(base, ignored_left, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(candidate, ignored_right, "PrimalBuff.AllowPostProcessEffect.snapshot.json")

            result = run_compare(base, candidate, "--target", "PrimalItem.CanUse", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 0, "rejected": 0})
        self.assertEqual(report["target_filters"], ["PrimalItem.CanUse"])
        self.assertEqual(report["results"][0]["target"], "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse")

    def test_target_filter_accepts_schema_qualified_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            write_snapshot(base, base_snapshot())
            write_snapshot(candidate, base_snapshot())

            result = run_compare(
                base,
                candidate,
                "--target",
                "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["accepted"], 1)

    def test_target_filter_rejects_unsupported_schema_qualifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            write_snapshot(base, base_snapshot())
            write_snapshot(candidate, base_snapshot())

            result = run_compare(
                base,
                candidate,
                "--target",
                "obelisk.unknown.snapshot.v1:PrimalItem.CanUse",
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported target filter schema: obelisk.unknown.snapshot.v1", result.stderr)

    def test_target_filter_rejects_empty_schema_qualified_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            write_snapshot(base, base_snapshot())
            write_snapshot(candidate, base_snapshot())

            result = run_compare(
                base,
                candidate,
                "--target",
                "obelisk.ufunction-chain.snapshot.v1:",
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema-qualified target filter missing target", result.stderr)

    def test_target_filter_fails_when_no_snapshot_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            write_snapshot(base, base_snapshot())
            write_snapshot(candidate, base_snapshot())

            result = run_compare(base, candidate, "--target", "PrimalBuff.Missing", "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target filter did not match snapshots", result.stderr)

    def test_named_target_set_expands_minimal_second_source_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            targets = [
                ("PrimalItem", "CanUse"),
                ("PrimalItem", "AllowRemoteAddToInventory"),
                ("PrimalStructure", "AllowStructureAccess"),
                ("PrimalStructure", "IsAllowedToDemolish"),
            ]
            ignored_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="AllowPostProcessEffect")
            ignored_right = deepcopy(ignored_left)
            ignored_right["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 99  # type: ignore[index]
            for outer, name in targets:
                payload = rename_target(deepcopy(base_snapshot()), outer=outer, name=name)
                filename = f"{outer}.{name}.snapshot.json"
                write_snapshot(base, payload, filename)
                write_snapshot(candidate, deepcopy(payload), filename)
            write_snapshot(base, ignored_left, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(candidate, ignored_right, "PrimalBuff.AllowPostProcessEffect.snapshot.json")

            result = run_compare(base, candidate, "--target-set", "minimal-second-source-intake", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 4, "inconclusive": 0, "rejected": 0})
        self.assertEqual(report["target_sets"], ["minimal-second-source-intake"])
        self.assertEqual(len(report["target_filters"]), 4)

    def test_named_target_set_reports_missing_schema_qualified_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            payload = rename_target(deepcopy(base_snapshot()), outer="PrimalItem", name="CanUse")
            write_snapshot(base, payload, "PrimalItem.CanUse.snapshot.json")
            write_snapshot(candidate, deepcopy(payload), "PrimalItem.CanUse.snapshot.json")

            result = run_compare(base, candidate, "--target-set", "minimal-second-source-intake", "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 3, "rejected": 0})
        missing = [item for item in report["results"] if item["status"] == "inconclusive"]
        self.assertEqual(len(missing), 3)
        self.assertTrue(
            all(item["reasons"] == ["missing_base_snapshot", "missing_candidate_snapshot"] for item in missing)
        )

    def test_named_target_set_selects_transfer_scriptstructs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            dino = scriptstruct_snapshot()
            player = rename_target(scriptstruct_snapshot(), outer="PrimalLocalProfile", name="ArkTributePlayerData")
            ufunction_same_short_name = rename_target(
                deepcopy(base_snapshot()),
                outer="PrimalLocalProfile",
                name="ARKTributeDino",
            )
            write_snapshot(base, dino, "PrimalLocalProfile.ARKTributeDino.scriptstruct.snapshot.json")
            write_snapshot(candidate, deepcopy(dino), "PrimalLocalProfile.ARKTributeDino.scriptstruct.snapshot.json")
            write_snapshot(base, player, "PrimalLocalProfile.ArkTributePlayerData.scriptstruct.snapshot.json")
            write_snapshot(candidate, deepcopy(player), "PrimalLocalProfile.ArkTributePlayerData.scriptstruct.snapshot.json")
            write_snapshot(base, ufunction_same_short_name, "PrimalLocalProfile.ARKTributeDino.ufunction.snapshot.json")
            write_snapshot(candidate, ufunction_same_short_name, "PrimalLocalProfile.ARKTributeDino.ufunction.snapshot.json")

            result = run_compare(base, candidate, "--target-set", "transfer-scriptstruct", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 2, "inconclusive": 0, "rejected": 0})
        self.assertEqual(report["target_sets"], ["transfer-scriptstruct"])
        self.assertEqual(
            sorted(result["target"] for result in report["results"]),
            [
                "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ARKTributeDino",
                "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData",
            ],
        )

    def test_target_filter_reports_missing_candidate_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="AllowPostProcessEffect")
            write_snapshot(base, left, "PrimalBuff.AllowPostProcessEffect.snapshot.json")

            result = run_compare(base, candidate, "--target", "PrimalBuff.AllowPostProcessEffect", "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 0, "inconclusive": 1, "rejected": 0})
        self.assertEqual(report["results"][0]["reasons"], ["missing_candidate_snapshot"])

    def test_repeated_target_filters_preserve_global_exit_code_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            accepted_left = base_snapshot()
            accepted_right = deepcopy(accepted_left)
            rejected_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="AllowPostProcessEffect")
            rejected_right = deepcopy(rejected_left)
            rejected_right["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 99  # type: ignore[index]
            missing_left = rename_target(deepcopy(base_snapshot()), outer="MissionType", name="AddPlayerToMission")
            write_snapshot(base, accepted_left)
            write_snapshot(candidate, accepted_right)
            write_snapshot(base, rejected_left, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(candidate, rejected_right, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(base, missing_left, "MissionType.AddPlayerToMission.snapshot.json")

            result = run_compare(
                base,
                candidate,
                "--target",
                "PrimalItem.CanUse",
                "--target",
                "PrimalBuff.AllowPostProcessEffect",
                "--target",
                "MissionType.AddPlayerToMission",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 1, "rejected": 1})

    def test_short_target_filter_matches_multiple_schemas(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            ufunction = rename_target(deepcopy(base_snapshot()), outer="SharedOuter", name="SharedName")
            scriptstruct = rename_target(scriptstruct_snapshot(), outer="SharedOuter", name="SharedName")
            write_snapshot(base, ufunction, "SharedOuter.SharedName.ufunction.snapshot.json")
            write_snapshot(candidate, deepcopy(ufunction), "SharedOuter.SharedName.ufunction.snapshot.json")
            write_snapshot(base, scriptstruct, "SharedOuter.SharedName.scriptstruct.snapshot.json")
            write_snapshot(candidate, deepcopy(scriptstruct), "SharedOuter.SharedName.scriptstruct.snapshot.json")

            result = run_compare(base, candidate, "--target", "SharedOuter.SharedName", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 2, "inconclusive": 0, "rejected": 0})
        self.assertEqual(
            sorted(result["target"] for result in report["results"]),
            [
                "obelisk.scriptstruct-chain.snapshot.v1:SharedOuter.SharedName",
                "obelisk.ufunction-chain.snapshot.v1:SharedOuter.SharedName",
            ],
        )

    def test_schema_qualified_target_filter_selects_one_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            ufunction = rename_target(deepcopy(base_snapshot()), outer="SharedOuter", name="SharedName")
            scriptstruct = rename_target(scriptstruct_snapshot(), outer="SharedOuter", name="SharedName")
            write_snapshot(base, ufunction, "SharedOuter.SharedName.ufunction.snapshot.json")
            write_snapshot(candidate, deepcopy(ufunction), "SharedOuter.SharedName.ufunction.snapshot.json")
            write_snapshot(base, scriptstruct, "SharedOuter.SharedName.scriptstruct.snapshot.json")
            write_snapshot(candidate, deepcopy(scriptstruct), "SharedOuter.SharedName.scriptstruct.snapshot.json")

            result = run_compare(
                base,
                candidate,
                "--target",
                "obelisk.scriptstruct-chain.snapshot.v1:SharedOuter.SharedName",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"], {"accepted": 1, "inconclusive": 0, "rejected": 0})
        self.assertEqual(
            report["results"][0]["target"],
            "obelisk.scriptstruct-chain.snapshot.v1:SharedOuter.SharedName",
        )

    def test_readiness_report_summarizes_modules_without_second_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(root / "base", None, "--readiness-report", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-snapshot-readiness.v1")
        self.assertEqual(report["second_source_status"], "missing_candidate_root")
        self.assertEqual(report["gate_mode"], "informational_gap_report")
        self.assertEqual(report["totals"]["targets"], 1)
        self.assertEqual(report["totals"]["comparable"], 1)
        self.assertEqual(report["totals"]["second_source_missing"], 1)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "not_ready",
                "layout_ready": False,
                "promotion_ready": False,
                "blockers": [{"reason": "missing_second_source", "count": 1}],
            },
        )
        self.assertEqual(report["modules"][0]["module"], "sdk_inventory")
        self.assertEqual(report["modules"][0]["schema"], "ufunction")
        self.assertEqual(report["modules"][0]["target_details"][0]["target"],
                         "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse")
        self.assertTrue(report["modules"][0]["target_details"][0]["comparable"])
        self.assertEqual(report["modules"][0]["target_details"][0]["second_source_status"], "missing")

    def test_readiness_text_lists_actionable_missing_second_source_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("gate_mode=informational_gap_report", result.stdout)
        self.assertIn("ufunction:sdk_inventory targets=1 comparable=1", result.stdout)
        self.assertIn("promotion_gate ready=false blockers=missing_second_source:1", result.stdout)
        self.assertIn(
            "target=obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse "
            "comparable=true second_source=missing",
            result.stdout,
        )

    def test_readiness_text_lists_blocked_and_rejected_target_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_buffs"
            candidate = root / "candidate" / "sha" / "sdk_buffs"
            base.mkdir(parents=True)
            candidate.mkdir(parents=True)
            rejected_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="BPBuffPreventUploading")
            rejected_right = deepcopy(rejected_left)
            rejected_right["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 99  # type: ignore[index]
            write_snapshot(base, rejected_left, "PrimalBuff.BPBuffPreventUploading.snapshot.json")
            write_snapshot(candidate, rejected_right, "PrimalBuff.BPBuffPreventUploading.snapshot.json")

            result = run_compare(root / "base", root / "candidate", "--readiness-report")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("second_source=rejected", result.stdout)
        self.assertIn("first_diff=property_chain.properties[0].offset_internal", result.stdout)

    def test_readiness_text_omits_accepted_target_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            candidate = root / "candidate" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            candidate.mkdir(parents=True)
            payload = base_snapshot()
            write_snapshot(base, payload)
            write_snapshot(candidate, deepcopy(payload))

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("second_source=accepted:1", result.stdout)
        self.assertIn("gate_mode=informational_gap_report", result.stdout)
        self.assertIn("promotion_gate ready=false blockers=not_second_source_promotion_gate:1", result.stdout)
        self.assertNotIn("target=obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse", result.stdout)

    def test_readiness_report_blocks_empty_snapshot_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            base.mkdir()

            result = run_compare(base, None, "--readiness-report", "--json")
            failing = run_compare(
                base,
                None,
                "--readiness-report",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["targets"], 0)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "not_ready",
                "layout_ready": False,
                "promotion_ready": False,
                "blockers": [{"reason": "no_targets", "count": 1}],
            },
        )
        self.assertEqual(failing.returncode, 1)

    def test_readiness_report_counts_missing_schema_qualified_target_set_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["targets"], 4)
        self.assertEqual(report["totals"]["comparable"], 1)
        self.assertEqual(report["totals"]["blocked"], 3)
        self.assertIn({"reason": "blocked_base_targets", "count": 3}, report["promotion_gate"]["blockers"])
        self.assertIn({"reason": "missing_second_source", "count": 1}, report["promotion_gate"]["blockers"])
        missing_module = next(module for module in report["modules"] if module["module"] == "<missing>")
        self.assertEqual(missing_module["targets"], 3)
        self.assertEqual(missing_module["block_reasons"], {"missing_base_snapshot": 3})
        self.assertTrue(
            all(detail["second_source_status"] == "not_applicable" for detail in missing_module["target_details"])
        )

    def test_readiness_report_blocks_promotion_gate_without_named_target_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            candidate = root / "candidate" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            candidate.mkdir(parents=True)
            payload = base_snapshot()
            write_snapshot(base, payload)
            write_snapshot(candidate, deepcopy(payload))

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["totals"]["second_source_accepted"], 1)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "layout_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "promotion_requires_target_set", "count": 1}],
            },
        )

    def test_readiness_report_target_set_promotion_exit_zero_when_all_targets_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_minimal_intake_snapshots(root / "base", root / "candidate")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["totals"]["second_source_accepted"], 4)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": True,
                "ready_scope": "layout_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [],
            },
        )
        self.assertEqual(report["evidence_scope"], "second_source_layout_evidence_only")
        self.assertIn("public_sdk", report["not_promoted_surfaces"])
        self.assertIn("inventory_sdk", report["not_promoted_surfaces"])
        self.assertIn("items_sdk", report["not_promoted_surfaces"])
        self.assertIn("resource_handle", report["not_promoted_surfaces"])
        self.assertTrue(
            any("Inventory SDK, Items SDK" in claim for claim in report["non_claims"]),
            report["non_claims"],
        )

    def test_assemble_rc_root_rejects_partial_evidence_identity_before_gate_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            roots = {
                "minimal": root / "minimal",
                "structure": root / "structure",
                "item_return": root / "item_return",
                "chat": root / "chat",
            }
            write_target_set_root(roots["minimal"], "minimal-second-source-intake")
            write_target_set_root(roots["structure"], "structure-observer-intake")
            write_target_set_root(roots["item_return"], "item-return-only-policy-slice")
            write_target_set_root(roots["chat"], "chat-message-intake")
            chat_snapshot = (
                roots["chat"]
                / "sha"
                / "sdk_test"
                / "ShooterPlayerController.ServerSendChatMessage.snapshot.json"
            )
            payload = json.loads(chat_snapshot.read_text(encoding="utf-8"))
            payload["evidence"].pop("evidence_pack_id")  # type: ignore[index]
            chat_snapshot.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            output = root / "rc-root"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ASSEMBLE_RC_SCRIPT),
                    "--minimal-root",
                    str(roots["minimal"]),
                    "--structure-root",
                    str(roots["structure"]),
                    "--item-return-root",
                    str(roots["item_return"]),
                    "--chat-root",
                    str(roots["chat"]),
                    "--output-root",
                    str(output),
                ],
                text=True,
                capture_output=True,
            )
            output_exists = output.exists()

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("incomplete or invalid evidence artifact identity", result.stderr)
        self.assertIn("evidence_pack_id_invalid", result.stderr)
        self.assertFalse(output_exists)

    def test_readiness_report_blocks_player_identity_lifecycle_promotion_gate(self) -> None:
        target_set = "players-identity-lifecycle-intake"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_dir = root / "base" / "sha" / "sdk_players"
            candidate_dir = root / "candidate" / "sha" / "sdk_players"
            base_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)
            for target in compare.TARGET_SETS[target_set]:
                _, _, short_key = target.partition(":")
                outer, _, name = short_key.partition(".")
                base_payload = rename_target(base_snapshot(), outer=outer, name=name)
                candidate_payload = deepcopy(base_payload)
                write_snapshot(base_dir, base_payload, f"{outer}.{name}.snapshot.json")
                write_snapshot(candidate_dir, candidate_payload, f"{outer}.{name}.snapshot.json")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], len(compare.TARGET_SETS[target_set]))
        self.assertEqual(report["totals"]["second_source_accepted"], len(compare.TARGET_SETS[target_set]))
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_readiness_report_blocks_mission_copied_bool_policy_slice_promotion_gate(self) -> None:
        target_set = "mission-copied-bool-policy-slice"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_dir = root / "base" / "sha" / "sdk_missions"
            candidate_dir = root / "candidate" / "sha" / "sdk_missions"
            base_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)
            for target in compare.TARGET_SETS[target_set]:
                _, _, short_key = target.partition(":")
                outer, _, name = short_key.partition(".")
                base_payload = rename_target(base_snapshot(), outer=outer, name=name)
                candidate_payload = deepcopy(base_payload)
                write_snapshot(base_dir, base_payload, f"{outer}.{name}.snapshot.json")
                write_snapshot(candidate_dir, candidate_payload, f"{outer}.{name}.snapshot.json")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], 3)
        self.assertEqual(report["totals"]["second_source_accepted"], 3)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_release_target_set_promotion_blocks_explicit_targets_outside_named_set(self) -> None:
        target_set = "item-return-only-policy-slice"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)
            for side in ("base", "candidate"):
                target_dir = root / side / "sha" / "sdk_test"
                payload = rename_target(base_snapshot(), outer="PrimalItem", name="CraftBlueprint")
                write_snapshot(target_dir, payload, "PrimalItem.CraftBlueprint.snapshot.json")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--target",
                "PrimalItem.CraftBlueprint",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["second_source_accepted"], 4)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "not_ready",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "explicit_target_not_in_named_target_set", "count": 1}],
            },
        )

    def test_readiness_report_blocks_transfer_baccept_policy_slice_promotion_gate(self) -> None:
        target_set = "transfer-baccept-only-policy-slice"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_dir = root / "base" / "sha" / "sdk_transfers"
            candidate_dir = root / "candidate" / "sha" / "sdk_transfers"
            base_dir.mkdir(parents=True)
            candidate_dir.mkdir(parents=True)
            for target in compare.TARGET_SETS[target_set]:
                _, _, short_key = target.partition(":")
                outer, _, name = short_key.partition(".")
                base_payload = rename_target(base_snapshot(), outer=outer, name=name)
                candidate_payload = deepcopy(base_payload)
                write_snapshot(base_dir, base_payload, f"{outer}.{name}.snapshot.json")
                write_snapshot(candidate_dir, candidate_payload, f"{outer}.{name}.snapshot.json")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], 1)
        self.assertEqual(report["totals"]["second_source_accepted"], 1)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_mission_copied_bool_policy_slice_has_local_consume_only_promotion_blocker(self) -> None:
        target_set = "mission-copied-bool-policy-slice"
        report = {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "gate_mode": "second_source_promotion",
            "promotion_gate": {
                "ready": True,
                "ready_scope": "layout_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [],
            },
        }

        with mock.patch.object(compare, "PLANNING_ONLY_TARGET_SETS", frozenset()):
            compare.block_non_release_target_set_promotion(report, [target_set])

        self.assertIn(target_set, compare.MISSION_CONSUME_ONLY_TARGET_SETS)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_readiness_report_blocks_all_internal_target_set_promotion_gates(self) -> None:
        internal_target_sets = sorted(compare.INTERNAL_LAYOUT_ONLY_TARGET_SETS)

        for target_set in internal_target_sets:
            with self.subTest(target_set=target_set), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                write_target_set_root(root / "base", target_set)
                write_target_set_root(root / "candidate", target_set)

                result = run_compare(
                    root / "base",
                    root / "candidate",
                    "--readiness-report",
                    "--target-set",
                    target_set,
                    "--fail-on-readiness-gaps",
                    "--json",
                )

                self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report["gate_mode"], "second_source_promotion")
                self.assertEqual(report["target_sets"], [target_set])
                self.assertEqual(report["totals"]["targets"], len(compare.TARGET_SETS[target_set]))
                self.assertEqual(report["totals"]["second_source_accepted"], len(compare.TARGET_SETS[target_set]))
                expected_scope = (
                    "planning_only"
                    if target_set in (compare.PLANNING_ONLY_TARGET_SETS | compare.MISSION_CONSUME_ONLY_TARGET_SETS)
                    else "internal_layout_only"
                )
                self.assertEqual(
                    report["promotion_gate"],
                    {
                        "ready": False,
                        "ready_scope": expected_scope,
                        "layout_ready": True,
                        "promotion_ready": False,
                        "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
                    },
                )

    def test_internal_general_v1_target_set_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "buff-compact-intake",
            "--target-set",
            "dino-compact-intake",
            "--target-set",
            "mission-compact-intake",
            "--target-set",
            "transfer-ufunction-intake",
            "--target-set",
            "tribe-compact-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        guidance = {item["target_set"]: item for item in report["target_set_guidance"]}
        self.assertEqual(
            set(guidance),
            {
                "buff-compact-intake",
                "dino-compact-intake",
                "mission-compact-intake",
                "transfer-ufunction-intake",
                "tribe-compact-intake",
            },
        )
        self.assertEqual(guidance["buff-compact-intake"]["classification"], "internal_buff_layout_only_candidate")
        self.assertEqual(guidance["dino-compact-intake"]["classification"], "internal_dino_layout_only_candidate")
        self.assertEqual(guidance["mission-compact-intake"]["classification"], "internal_mission_layout_only_candidate")
        self.assertEqual(guidance["transfer-ufunction-intake"]["classification"], "internal_transfer_layout_only_candidate")
        self.assertEqual(guidance["tribe-compact-intake"]["classification"], "internal_tribe_layout_only_candidate")
        for target_set, item in guidance.items():
            with self.subTest(target_set=target_set):
                self.assertIn("internal_layout_evidence_only", item["why_blocked"])
                self.assertIn("not_release_readiness_target", item["why_blocked"])
                self.assertIn("runtime_observation_requires_separate_approval", item["why_blocked"])
                self.assertIn(
                    "do not use this target set for release/readiness or public SDK promotion gates",
                    item["snapshot_prep_checks"],
                )
                self.assertIn("runtime hooks", item["non_claim"])

    def test_readiness_report_target_set_rejected_second_source_exits_one(self) -> None:
        def reject_one(payload: dict[str, object], _outer: str, name: str) -> None:
            if name == "CanUse":
                payload["targets"][0]["property_chain"]["properties"][1]["offset_internal"] = 2  # type: ignore[index]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_minimal_intake_snapshots(root / "base", root / "candidate", mutate_candidate=reject_one)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["second_source_rejected"], 1)
        self.assertIn({"reason": "rejected_second_source", "count": 1}, report["promotion_gate"]["blockers"])

    def test_readiness_report_target_set_inconclusive_second_source_exits_two(self) -> None:
        def make_one_inconclusive(payload: dict[str, object], _outer: str, name: str) -> None:
            if name == "CanUse":
                payload["evidence"]["generated_by"] = "scripts/other.py"  # type: ignore[index]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_minimal_intake_snapshots(root / "base", root / "candidate", mutate_candidate=make_one_inconclusive)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["second_source_inconclusive"], 1)
        self.assertIn({"reason": "inconclusive_second_source", "count": 1}, report["promotion_gate"]["blockers"])

    def test_readiness_report_does_not_mark_informational_report_promotable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            candidate = root / "candidate" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            candidate.mkdir(parents=True)
            payload = base_snapshot()
            write_snapshot(base, payload)
            write_snapshot(candidate, deepcopy(payload))

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "informational_gap_report")
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "layout_only",
                "layout_ready": True,
                "promotion_ready": False,
                "blockers": [{"reason": "not_second_source_promotion_gate", "count": 1}],
            },
        )

    def test_readiness_report_can_fail_on_missing_target_set_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["totals"]["blocked"], 3)

    def test_structure_observer_target_set_matches_committed_base_fixtures(self) -> None:
        result = run_compare_raw(
            "--base-root",
            str(REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"),
            "--readiness-report",
            "--target-set",
            "structure-observer-intake",
            "--fail-on-base-readiness-gaps",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "base_fixture_readiness")
        self.assertEqual(report["totals"]["targets"], 6)
        self.assertEqual(report["totals"]["comparable"], 6)
        self.assertEqual(report["totals"]["blocked"], 0)
        self.assertEqual(report["totals"]["second_source_missing"], 6)

    def test_all_named_target_sets_match_committed_base_fixtures(self) -> None:
        target_sets = {
            "chat-message-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 1),
            "minimal-second-source-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 4),
            "structure-observer-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 6),
            "structure-nonpin-copied-scalar-policy-slice": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 3),
            "buff-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 3),
            "buff-breadth-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 3),
            "dino-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 2),
            "item-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 4),
            "inventory-action-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 2),
            "mission-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 4),
            "tribe-compact-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 5),
            "transfer-ufunction-intake": (REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots", 7),
            "transfer-scriptstruct": (REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots", 2),
        }

        for target_set, (base_root, expected_targets) in target_sets.items():
            with self.subTest(target_set=target_set):
                result = run_compare_raw(
                    "--base-root",
                    str(base_root),
                    "--readiness-report",
                    "--target-set",
                    target_set,
                    "--fail-on-base-readiness-gaps",
                    "--json",
                )

                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                report = json.loads(result.stdout)
                self.assertEqual(report["gate_mode"], "base_fixture_readiness")
                self.assertEqual(report["totals"]["targets"], expected_targets)
                self.assertEqual(report["totals"]["comparable"], expected_targets)
                self.assertEqual(report["totals"]["blocked"], 0)
                self.assertEqual(report["totals"]["second_source_missing"], expected_targets)

    def test_readiness_report_can_fail_on_missing_second_source_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["blocked"], 0)
        self.assertEqual(report["totals"]["second_source_missing"], 1)

    def test_base_readiness_gap_flag_ignores_missing_second_source_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
                "--fail-on-base-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["blocked"], 0)
        self.assertEqual(report["totals"]["second_source_missing"], 1)

    def test_base_readiness_gap_flag_fails_on_missing_base_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            write_snapshot(base, base_snapshot())

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--fail-on-base-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["blocked"], 3)

    def test_readiness_report_supports_scriptstruct_target_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_transfers"
            base.mkdir(parents=True)
            write_snapshot(base, scriptstruct_snapshot(), "PrimalLocalProfile.ARKTributeDino.snapshot.json")

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target",
                "PrimalLocalProfile.ARKTributeDino",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["targets"], 1)
        self.assertEqual(report["modules"][0]["schema"], "scriptstruct")
        self.assertEqual(report["modules"][0]["module"], "sdk_transfers")

    def test_readiness_report_includes_second_source_target_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_buffs"
            candidate = root / "candidate" / "sha" / "sdk_buffs"
            base.mkdir(parents=True)
            candidate.mkdir(parents=True)
            accepted_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="AllowPostProcessEffect")
            accepted_right = deepcopy(accepted_left)
            rejected_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="BPBuffPreventUploading")
            rejected_right = deepcopy(rejected_left)
            rejected_right["targets"][0]["property_chain"]["properties"][0]["offset_internal"] = 99  # type: ignore[index]
            missing_left = rename_target(deepcopy(base_snapshot()), outer="PrimalBuff", name="BP_OnBuffLifetimeUpdated")
            write_snapshot(base, accepted_left, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(candidate, accepted_right, "PrimalBuff.AllowPostProcessEffect.snapshot.json")
            write_snapshot(base, rejected_left, "PrimalBuff.BPBuffPreventUploading.snapshot.json")
            write_snapshot(candidate, rejected_right, "PrimalBuff.BPBuffPreventUploading.snapshot.json")
            write_snapshot(base, missing_left, "PrimalBuff.BP_OnBuffLifetimeUpdated.snapshot.json")

            result = run_compare(root / "base", root / "candidate", "--readiness-report", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        details = {item["target"]: item for item in report["modules"][0]["target_details"]}
        self.assertEqual(
            details["obelisk.ufunction-chain.snapshot.v1:PrimalBuff.AllowPostProcessEffect"]["second_source_status"],
            "accepted",
        )
        rejected_detail = details["obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BPBuffPreventUploading"]
        self.assertEqual(rejected_detail["second_source_status"], "rejected")
        self.assertEqual(rejected_detail["diff_count"], 1)
        self.assertIn("offset_internal", rejected_detail["first_diff"])
        missing_detail = details["obelisk.ufunction-chain.snapshot.v1:PrimalBuff.BP_OnBuffLifetimeUpdated"]
        self.assertEqual(missing_detail["second_source_status"], "inconclusive")
        self.assertEqual(missing_detail["second_source_reasons"], ["missing_candidate_snapshot"])

    def test_compare_mode_requires_candidate_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            base.mkdir()
            write_snapshot(base, base_snapshot())

            result = run_compare(base, None, "--json")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--candidate-root is required", result.stderr)


if __name__ == "__main__":
    unittest.main()
