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


def write_lifecycle_snapshot_root(root: Path) -> None:
    target_dir = root / "sha" / "players_lifecycle"
    target_dir.mkdir(parents=True, exist_ok=True)
    for outer, name in (
        ("ShooterGameMode", "HandleNewPlayer"),
        ("ShooterGameMode", "OnLogout"),
    ):
        payload = rename_target(base_snapshot(), outer=outer, name=name)
        write_snapshot(target_dir, payload, f"{outer}.{name}.snapshot.json")


def write_distinct_lifecycle_fixture_root(root: Path) -> None:
    target_dir = root / "7e7ded49e0c6" / "players_lifecycle"
    target_dir.mkdir(parents=True, exist_ok=True)
    source_dir = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots" / "7e7ded49e0c6" / "players_lifecycle"
    for name in ("ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"):
        payload = json.loads((source_dir / f"{name}.snapshot.json").read_text(encoding="utf-8"))
        evidence = payload["evidence"]
        evidence["artifact_kind"] = "offline_core"
        evidence["artifact_sha256"] = "c" * 64
        evidence["capture_id"] = "candidate-lifecycle-core"
        evidence["evidence_pack_id"] = "candidate-lifecycle-pack"
        (target_dir / f"{name}.snapshot.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


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
    def test_target_set_catalog_hygiene_blocks_readiness_and_counting_alias_names(self) -> None:
        issues = compare.target_set_catalog_hygiene_issues(
            target_sets={
                "mission-readiness-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:MissionType.AddPlayerToMission",
                ),
                "players-identity-evidence": (
                    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerListPlayers",
                ),
                "resource-handle-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
                ),
                "runtime-identity-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerKickPlayer",
                ),
                "structure-mutation-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.SetVariant",
                ),
                "item-return-override-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
                ),
                "stable-sdk-intake": (
                    "obelisk.ufunction-chain.snapshot.v1:PrimalItem.AllowRemoteAddToInventory",
                ),
                "transfer-counts-toward-v1": (
                    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerTransferredPlayerConfirmationResult",
                ),
            },
            module_lanes={
                "mission-readiness-intake": "mission",
                "players-identity-evidence": "players_identity",
                "resource-handle-intake": "resource_handle",
                "runtime-identity-intake": "players_identity",
                "structure-mutation-intake": "structures",
                "item-return-override-intake": "items",
                "stable-sdk-intake": "core_gameplay_policy",
                "transfer-counts-toward-v1": "transfer",
            },
            planning_only=frozenset(),
            release_readiness=frozenset(),
            supported_schemas=compare.SUPPORTED_SCHEMAS,
        )

        aliases_by_target = {
            str(issue["target_set"]): set(issue.get("aliases", []))
            for issue in issues
            if issue.get("reason") == "target_set_name_promotion_alias"
        }
        self.assertIn("readiness", aliases_by_target["mission-readiness-intake"])
        self.assertIn("identity_evidence", aliases_by_target["players-identity-evidence"])
        self.assertIn("resource_handle", aliases_by_target["resource-handle-intake"])
        self.assertIn("runtime_identity", aliases_by_target["runtime-identity-intake"])
        self.assertIn("mutation", aliases_by_target["structure-mutation-intake"])
        self.assertIn("return_override", aliases_by_target["item-return-override-intake"])
        self.assertIn("stable_sdk", aliases_by_target["stable-sdk-intake"])
        self.assertIn("counts", aliases_by_target["transfer-counts-toward-v1"])
        self.assertIn("v1", aliases_by_target["transfer-counts-toward-v1"])

    def test_snapshot_claim_scan_blocks_stable_sdk_schema_alias(self) -> None:
        payload = base_snapshot()
        payload["schema_alias"] = "obelisk.stable-sdk-ready.v1"

        _, reasons = compare.comparable_layout(payload, strict_identity_indices=False)

        self.assertIn("forbidden_positive_claim_value:$.schema_alias", reasons)

    def test_lists_named_target_sets_without_snapshot_roots(self) -> None:
        result = run_compare_raw("--list-target-sets", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-snapshot-target-sets.v1")
        self.assertEqual(
            report["catalog_hygiene"],
            {
                "guardrail": "fail_closed_named_target_set_catalog",
                "status": "clean",
                "checked_target_sets": len(compare.TARGET_SETS),
                "checked_schemas": sorted(compare.SUPPORTED_SCHEMAS),
                "issues": [],
            },
        )
        self.assertEqual(report["target_set_revision_schema"], compare.TARGET_SET_REVISION_SCHEMA)
        self.assertEqual(report["target_set_revision_source"], compare.TARGET_SET_REVISION_SOURCE)
        self.assertEqual(report["target_set_revision_target_schema_filter"], "all")
        self.assertEqual(
            report["target_set_revision_source_sha256"],
            compare.target_set_revision_source_sha256(list(compare.TARGET_SETS), schema_filter=None),
        )
        self.assertRegex(report["target_set_revision_source_sha256"], r"^[0-9a-f]{64}$")
        sets = {item["name"]: item["targets"] for item in report["target_sets"]}
        classifications = {item["name"]: item["readiness_classification"] for item in report["target_sets"]}
        lanes = {item["name"]: item["module_lane"] for item in report["target_sets"]}
        release_flags = {item["name"]: item["release_readiness"] for item in report["target_sets"]}
        readiness_scopes = {item["name"]: item["readiness_scope"] for item in report["target_sets"]}
        promotion_flags = {item["name"]: item["promotion_ready"] for item in report["target_sets"]}
        public_sdk_flags = {item["name"]: item["public_sdk_ready"] for item in report["target_sets"]}
        runtime_flags = {item["name"]: item["runtime_ready"] for item in report["target_sets"]}
        second_source_flags = {item["name"]: item["second_source_layout_evidence"] for item in report["target_sets"]}
        self.assertEqual(set(lanes), set(compare.TARGET_SETS))
        self.assertEqual(lanes["chat-message-intake"], "chat")
        self.assertEqual(lanes["command-chat-response-route-planning"], "command_chat_response")
        self.assertEqual(lanes["inventory-custom-filter-array-boundary"], "inventory")
        self.assertEqual(lanes["mission-copied-bool-policy-slice"], "mission")
        self.assertEqual(lanes["players-lifecycle-anchor-candidates"], "players_lifecycle")
        self.assertEqual(lanes["structure-build-policy-offline-intake"], "structures")
        self.assertEqual(lanes["structure-observer-intake"], "structures")
        self.assertEqual(lanes["transfer-scriptstruct"], "transfer")
        self.assertEqual(report["catalog_scope"], "named_target_set_catalog_only")
        self.assertEqual(report["evidence_scope"], "target_set_catalog_only_not_evidence")
        self.assertEqual(report["readiness_effect"], "none")
        self.assertTrue(report["not_second_source"])
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("second_source_layout_evidence", report["does_not_satisfy_readiness"])
        self.assertIn("public_sdk", report["not_promoted_surfaces"])
        self.assertIn("runtime_hooks", report["not_promoted_surfaces"])
        self.assertTrue(
            any(
                "release readiness does not imply public SDK readiness for Mission, Transfer, Structure, Item"
                in claim
                for claim in report["non_claims"]
            ),
            report["non_claims"],
        )
        self.assertFalse(any(promotion_flags.values()))
        self.assertFalse(any(public_sdk_flags.values()))
        self.assertFalse(any(runtime_flags.values()))
        self.assertFalse(any(second_source_flags.values()))
        self.assertIn("minimal-second-source-intake", sets)
        self.assertEqual(classifications["minimal-second-source-intake"], "release_readiness")
        self.assertIs(release_flags["minimal-second-source-intake"], True)
        self.assertEqual(readiness_scopes["minimal-second-source-intake"], "layout_only")
        self.assertEqual(classifications["item-return-only-policy-slice"], "planning_only")
        self.assertIs(release_flags["item-return-only-policy-slice"], False)
        self.assertEqual(readiness_scopes["item-return-only-policy-slice"], "planning_only")
        self.assertEqual(classifications["buff-compact-intake"], "internal_layout_only")
        self.assertIs(release_flags["buff-compact-intake"], False)
        self.assertEqual(readiness_scopes["buff-compact-intake"], "internal_layout_only")
        self.assertEqual(classifications["mission-copied-bool-policy-slice"], "planning_only")
        self.assertIs(release_flags["mission-copied-bool-policy-slice"], False)
        self.assertEqual(readiness_scopes["mission-copied-bool-policy-slice"], "planning_only")
        self.assertEqual(classifications["players-identity-lifecycle-intake"], "planning_only")
        self.assertIs(release_flags["players-identity-lifecycle-intake"], False)
        self.assertEqual(classifications["players-lifecycle-anchor-candidates"], "planning_only")
        self.assertIs(release_flags["players-lifecycle-anchor-candidates"], False)
        self.assertEqual(readiness_scopes["players-lifecycle-anchor-candidates"], "planning_only")
        self.assertEqual(classifications["structure-aggregate-census-planning"], "planning_only")
        self.assertIs(release_flags["structure-aggregate-census-planning"], False)
        self.assertEqual(readiness_scopes["structure-aggregate-census-planning"], "planning_only")
        self.assertEqual(classifications["structure-build-policy-offline-intake"], "planning_only")
        self.assertIs(release_flags["structure-build-policy-offline-intake"], False)
        self.assertEqual(readiness_scopes["structure-build-policy-offline-intake"], "planning_only")
        self.assertEqual(classifications["command-chat-response-route-planning"], "planning_only")
        self.assertIs(release_flags["command-chat-response-route-planning"], False)
        self.assertEqual(readiness_scopes["command-chat-response-route-planning"], "planning_only")
        self.assertEqual(classifications["inventory-custom-filter-array-boundary"], "planning_only")
        self.assertIs(release_flags["inventory-custom-filter-array-boundary"], False)
        self.assertEqual(readiness_scopes["inventory-custom-filter-array-boundary"], "planning_only")
        self.assertEqual(classifications["transfer-baccept-only-policy-slice"], "internal_layout_only")
        self.assertIs(release_flags["transfer-baccept-only-policy-slice"], False)
        self.assertEqual(readiness_scopes["transfer-baccept-only-policy-slice"], "internal_layout_only")
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
            sets["players-lifecycle-anchor-candidates"],
            [
                "obelisk.ufunction-chain.snapshot.v1:GameMode.K2_PostLogin",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnPostLogin__DelegateSignature",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            ],
        )
        lifecycle_entry = next(
            item for item in report["target_sets"] if item["name"] == "players-lifecycle-anchor-candidates"
        )
        lifecycle_policy = lifecycle_entry["lifecycle_source_policy"]
        self.assertEqual(lifecycle_policy["policy_scope"], "source_names_only_not_runtime_evidence")
        self.assertEqual(
            lifecycle_policy["approved_runtime_triplet_source_names"],
            [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(
            lifecycle_policy["guidance_only_non_triplet_source_names"],
            [
                "GameMode.K2_PostLogin",
                "ShooterGameMode.OnPostLogin__DelegateSignature",
                "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            ],
        )
        self.assertEqual(
            lifecycle_policy["runtime_triplet_evidence_status"],
            "approved_source_names_only_runtime_evidence_missing",
        )
        self.assertFalse(lifecycle_policy["approved_runtime_evidence_present"])
        self.assertFalse(lifecycle_policy["runtime_ready"])
        self.assertFalse(lifecycle_policy["public_sdk_ready"])
        self.assertFalse(lifecycle_policy["promotion_ready"])
        lifecycle_roles = {item["target"]: item for item in lifecycle_policy["source_roles"]}
        self.assertTrue(lifecycle_roles["ShooterGameMode.HandleNewPlayer"]["approved_runtime_triplet_source_name"])
        self.assertTrue(lifecycle_roles["ShooterGameMode.HandleNewPlayer"]["static_lifecycle_anchor_source_name"])
        self.assertTrue(lifecycle_roles["ShooterGameMode.OnLogout"]["approved_runtime_triplet_source_name"])
        self.assertTrue(lifecycle_roles["ShooterGameMode.OnLogout"]["static_lifecycle_anchor_source_name"])
        self.assertTrue(lifecycle_roles["ShooterGameMode.CheckJoinInProgress"]["approved_runtime_triplet_source_name"])
        self.assertTrue(lifecycle_roles["ShooterGameMode.CheckJoinInProgress"]["rejected_start_triplet_source_name"])
        self.assertFalse(lifecycle_roles["ShooterGameMode.CheckJoinInProgress"]["static_lifecycle_anchor_source_name"])
        self.assertFalse(lifecycle_roles["GameMode.K2_PostLogin"]["approved_runtime_triplet_source_name"])
        self.assertTrue(lifecycle_roles["GameMode.K2_PostLogin"]["guidance_only_non_triplet_source_name"])
        self.assertTrue(
            lifecycle_roles["GameMode.K2_PostLogin"]["chronology_guidance_only_non_anchor_source_name"]
        )
        self.assertFalse(
            lifecycle_roles["ShooterGameMode.OnPostLogin__DelegateSignature"][
                "approved_runtime_triplet_source_name"
            ]
        )
        self.assertTrue(
            lifecycle_roles["ShooterGameMode.OnPostLogin__DelegateSignature"][
                "delegate_guidance_only_non_triplet_source_name"
            ]
        )
        self.assertIn("approved_runtime_evidence", lifecycle_policy["does_not_satisfy"])
        self.assertIn("public_sdk_readiness", lifecycle_policy["does_not_satisfy"])
        self.assertIn("promotion evidence", " ".join(lifecycle_policy["non_claims"]))
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
        self.assertEqual(
            sets["inventory-custom-filter-array-boundary"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalInventoryComponent.InventoryCustomFilter",
            ],
        )
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
        self.assertEqual(
            sets["structure-build-policy-offline-intake"],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
            ],
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

        text_result = run_compare_raw("--list-target-sets")
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn(
            "target_set_catalog scope=named_target_set_catalog_only "
            "evidence_scope=target_set_catalog_only_not_evidence not_second_source=true "
            "second_source_layout_evidence=false",
            text_result.stdout,
        )
        self.assertIn(
            "minimal-second-source-intake: readiness_classification=release_readiness "
            "release_readiness=true readiness_scope=layout_only promotion_ready=false "
            "public_sdk_ready=false",
            text_result.stdout,
        )
        self.assertIn(
            "mission-copied-bool-policy-slice: readiness_classification=planning_only "
            "release_readiness=false readiness_scope=planning_only promotion_ready=false "
            "public_sdk_ready=false",
            text_result.stdout,
        )
        self.assertIn(
            "lifecycle_source_policy scope=source_names_only_not_runtime_evidence "
            "approved_runtime_triplet_source_names=ShooterGameMode.HandleNewPlayer,ShooterGameMode.CheckJoinInProgress,ShooterGameMode.OnLogout "
            "guidance_only_non_triplet_source_names=GameMode.K2_PostLogin,ShooterGameMode.OnPostLogin__DelegateSignature,ShooterGameMode.OnStartNewPlayer__DelegateSignature "
            "runtime_triplet_evidence_status=approved_source_names_only_runtime_evidence_missing "
            "approved_runtime_evidence_present=false runtime_ready=false public_sdk_ready=false promotion_ready=false",
            text_result.stdout,
        )
        self.assertRegex(text_result.stdout, r"target_set_revision_source_sha256=[0-9a-f]{64}")

    def test_rejects_unknown_or_duplicate_target_set_filters_before_comparison(self) -> None:
        unknown = run_compare_raw("--target-set", "not-a-target-set", "--json")
        duplicate = run_compare_raw(
            "--target-set",
            "minimal-second-source-intake",
            "--target-set",
            "minimal-second-source-intake",
            "--json",
        )

        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn("invalid choice: 'not-a-target-set'", unknown.stderr)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("duplicate target-set filter(s): minimal-second-source-intake", duplicate.stderr)

    def test_target_set_catalog_guardrail_blocks_duplicate_entries(self) -> None:
        target_sets = dict(compare.TARGET_SETS)
        duplicated = target_sets["minimal-second-source-intake"][0]
        target_sets["minimal-second-source-intake"] = (
            *target_sets["minimal-second-source-intake"],
            duplicated,
        )

        with mock.patch.object(compare, "TARGET_SETS", target_sets):
            report = compare.target_set_catalog_hygiene_report()

        self.assertEqual(report["status"], "blocked")
        self.assertIn(
            {
                "target_set": "minimal-second-source-intake",
                "reason": "duplicate_target_set_entries",
                "targets": [duplicated],
                "count": 1,
            },
            report["issues"],
        )

        with mock.patch.object(compare, "TARGET_SETS", target_sets):
            with self.assertRaisesRegex(SystemExit, "duplicate_target_set_entries"):
                compare.reject_target_set_catalog_hygiene_issues()

    def test_target_set_catalog_guardrail_blocks_malformed_schema_entries(self) -> None:
        target_sets = dict(compare.TARGET_SETS)
        target_sets["minimal-second-source-intake"] = (
            "PrimalItem.CanUse",
            "obelisk.unknown.snapshot.v1:PrimalItem.AllowRemoteAddToInventory",
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure",
        )

        with mock.patch.object(compare, "TARGET_SETS", target_sets):
            reasons = {
                issue["reason"]
                for issue in compare.target_set_catalog_hygiene_report()["issues"]
            }

        self.assertIn("target_set_entry_not_schema_qualified", reasons)
        self.assertIn("target_set_entry_unsupported_schema", reasons)
        self.assertIn("target_set_entry_missing_outer_dot_name", reasons)

    def test_target_set_catalog_guardrail_blocks_missing_module_lane_coverage(self) -> None:
        module_lanes = dict(compare.TARGET_SET_MODULE_LANES)
        module_lanes.pop("transfer-scriptstruct")

        with mock.patch.object(compare, "TARGET_SET_MODULE_LANES", module_lanes):
            report = compare.target_set_catalog_hygiene_report()

        self.assertEqual(report["status"], "blocked")
        self.assertIn(
            {"target_set": "transfer-scriptstruct", "reason": "target_set_missing_module_lane"},
            report["issues"],
        )

    def test_target_set_catalog_guardrail_blocks_positive_promotion_alias_names(self) -> None:
        target_sets = dict(compare.TARGET_SETS)
        target_sets["transfer-sdk-ready"] = (
            "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerUploadDino",
        )
        module_lanes = dict(compare.TARGET_SET_MODULE_LANES)
        module_lanes["transfer-sdk-ready"] = "transfer"

        with mock.patch.object(compare, "TARGET_SETS", target_sets), mock.patch.object(
            compare,
            "TARGET_SET_MODULE_LANES",
            module_lanes,
        ):
            report = compare.target_set_catalog_hygiene_report()

        self.assertEqual(report["status"], "blocked")
        self.assertIn(
            {
                "target_set": "transfer-sdk-ready",
                "reason": "target_set_name_promotion_alias",
                "aliases": ["ready", "sdk"],
            },
            report["issues"],
        )

    def test_target_set_catalog_guardrail_blocks_mixed_snapshot_schema_sets(self) -> None:
        target_sets = dict(compare.TARGET_SETS)
        target_sets["transfer-scriptstruct"] = (
            *target_sets["transfer-scriptstruct"],
            "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
        )

        with mock.patch.object(compare, "TARGET_SETS", target_sets):
            report = compare.target_set_catalog_hygiene_report()

        self.assertEqual(report["status"], "blocked")
        self.assertIn(
            {
                "target_set": "transfer-scriptstruct",
                "reason": "target_set_mixed_snapshot_schemas",
                "schemas": [
                    "obelisk.scriptstruct-chain.snapshot.v1",
                    "obelisk.ufunction-chain.snapshot.v1",
                ],
            },
            report["issues"],
        )

    def test_structure_build_policy_targets_stay_candidate_only_with_missing_base_gap(self) -> None:
        result = run_compare_raw("--list-target-sets", "--json")

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        sets = {item["name"]: item["targets"] for item in report["target_sets"]}
        classifications = {item["name"]: item["readiness_classification"] for item in report["target_sets"]}
        release_flags = {item["name"]: item["release_readiness"] for item in report["target_sets"]}
        promotion_flags = {item["name"]: item["promotion_ready"] for item in report["target_sets"]}
        public_sdk_flags = {item["name"]: item["public_sdk_ready"] for item in report["target_sets"]}
        build_policy_targets = {
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
        }
        self.assertEqual(set(sets["structure-build-policy-offline-intake"]), build_policy_targets)
        self.assertEqual(classifications["structure-build-policy-offline-intake"], "planning_only")
        self.assertIs(release_flags["structure-build-policy-offline-intake"], False)
        self.assertIs(promotion_flags["structure-build-policy-offline-intake"], False)
        self.assertIs(public_sdk_flags["structure-build-policy-offline-intake"], False)
        for target_set, targets in sets.items():
            if target_set == "structure-build-policy-offline-intake":
                continue
            with self.subTest(target_set=target_set):
                self.assertTrue(build_policy_targets.isdisjoint(set(targets)))
                self.assertNotIn(
                    "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild",
                    targets,
                )

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
        self.assertIn("planning_layout_only_not_promotion_gate", primal_guidance["why_blocked"])
        self.assertIn("copied_payload_policy_unproven", primal_guidance["why_blocked"])
        self.assertIn("runtime_observation_requires_separate_approval", primal_guidance["why_blocked"])
        self.assertIn("approved non-protected copied/offline core", primal_guidance["next_offline_input"])
        self.assertIn(
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            primal_guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "reuse the accepted planning-layout second-source artifact before starting new extraction work",
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
        self.assertIn("public SDK readiness", primal_guidance["non_claim"])
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
            "why_blocked=planning_layout_only_not_promotion_gate,placement_struct_redaction_policy_unproven",
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
        self.assertEqual(report["evidence_scope"], "offline_guidance_only_not_evidence")
        self.assertEqual(report["readiness_effect"], "none")
        self.assertTrue(report["not_second_source"])
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("second_source_layout_evidence", report["does_not_satisfy_readiness"])
        self.assertEqual(report["target_filters"], ["PrimalStructure.IsAllowedToBuild"])
        self.assertEqual(len(report["targets"]), 1)
        guidance = report["targets"][0]
        self.assertEqual(
            guidance["target"],
            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
        )
        self.assertEqual(guidance["classification"], "second_wave_structure_build_policy_candidate")
        self.assertIn("planning_layout_only_not_promotion_gate", guidance["why_blocked"])
        self.assertIn("runtime_observation_requires_separate_approval", guidance["why_blocked"])
        self.assertIn("approved non-protected copied/offline core", guidance["next_offline_input"])
        self.assertEqual(len(guidance["snapshot_prep_checks"]), 7)
        self.assertIn(
            "reuse the accepted planning-layout second-source artifact before starting new extraction work",
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
        self.assertIn("target_guidance count=3 scope=offline_planning_only", text_result.stdout)
        self.assertIn(
            "evidence_scope=offline_guidance_only_not_evidence not_second_source=true",
            text_result.stdout,
        )
        self.assertIn(
            "target=obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild",
            text_result.stdout,
        )
        self.assertIn("snapshot_prep_checks=7", text_result.stdout)

    def test_player_join_admission_candidate_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target",
            "ShooterGameMode.CheckJoinInProgress",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_filters"], ["ShooterGameMode.CheckJoinInProgress"])
        self.assertEqual(len(report["targets"]), 1)
        guidance = report["targets"][0]
        self.assertEqual(
            guidance["target"],
            "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress",
        )
        self.assertEqual(guidance["classification"], "p0_adjacent_player_join_admission_candidate")
        self.assertIn("candidate_only_layout_evidence", guidance["why_blocked"])
        self.assertIn("not_identity_anchor", guidance["why_blocked"])
        self.assertIn("runtime_ordering_unproven", guidance["why_blocked"])
        self.assertIn("NumParms=3, ParmsSize=17, ReturnValueOffset=0x10", "\n".join(guidance["snapshot_prep_checks"]))
        self.assertIn(
            "bIsFromLogin:BoolProperty@0, NewPlayer:ObjectProperty@8, ReturnValue:BoolProperty@16",
            "\n".join(guidance["snapshot_prep_checks"]),
        )
        self.assertIn("NewPlayer redacted or recognition-only", "\n".join(guidance["snapshot_prep_checks"]))
        self.assertIn("return override", guidance["non_claim"])
        self.assertIn("v1 completion", guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target",
            "ShooterGameMode.CheckJoinInProgress",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=1 scope=offline_planning_only", text_result.stdout)
        self.assertIn("classification=p0_adjacent_player_join_admission_candidate", text_result.stdout)
        self.assertIn("not_identity_anchor", text_result.stdout)

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
        self.assertIn("repo-local fixture readiness", mission["next_offline_input"])
        self.assertIn("tests/fixtures/ufunction_snapshots", mission["next_offline_input"])
        self.assertIn("explicit non-protected --root/--manifest", mission["next_offline_input"])
        self.assertNotIn("/home/flowcommunity-ark/obelisk-artifacts", mission["next_offline_input"])
        self.assertIn(
            "policy_manifest_sha256=f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945",
            mission["next_offline_input"],
        )
        self.assertIn(
            "artifact_pack_manifest_sha256=b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb",
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
        self.assertIn("internal_layout_evidence_only", transfer["why_blocked"])
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

        transfer = guidance["transfer-scriptstruct"]
        self.assertIn("scriptstruct_layout_candidate_only", transfer["why_blocked"])
        self.assertIn("transfer_scriptstruct_payload_decode_blocked", transfer["why_blocked"])
        self.assertIn("item_net_info_excluded", transfer["why_blocked"])
        self.assertIn(
            "keep ItemNetInfo explicitly excluded until a separate transfer payload decoding and ownership policy exists",
            transfer["snapshot_prep_checks"],
        )
        self.assertIn("transfer payload decoding", transfer["non_claim"])
        self.assertIn("v1 completion", transfer["non_claim"])

    def test_all_internal_target_sets_have_non_promotional_guidance(self) -> None:
        missing = sorted(
            target_set
            for target_set in compare.INTERNAL_LAYOUT_ONLY_TARGET_SETS
            if compare.target_set_blocker_guidance(target_set) is None
        )

        self.assertEqual(missing, [])

    def test_buff_compact_guidance_names_exact_layout_readiness_gap(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "buff-compact-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "buff-compact-intake")
        self.assertEqual(guidance["classification"], "internal_buff_layout_only_candidate")
        self.assertIn("missing_distinct_second_source_layout", guidance["why_blocked"])
        self.assertIn("public_buff_sdk_blocked", guidance["why_blocked"])
        self.assertIn("runtime_observation_requires_separate_approval", guidance["why_blocked"])
        self.assertIn(
            "sanitized AllowPostProcessEffect, BPBuffPreventUploading, and BP_OnBuffLifetimeUpdated snapshots",
            guidance["next_offline_input"],
        )
        for required in (
            "compare only AllowPostProcessEffect, BPBuffPreventUploading, and BP_OnBuffLifetimeUpdated",
            "ReturnValue BoolProperty only",
            "zero-param recognition-only layout with no ReturnValue copy",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ):
            self.assertTrue(
                any(required in item for item in guidance["snapshot_prep_checks"]),
                f"missing buff compact guidance term: {required}",
            )
        self.assertIn("Buff SDK", guidance["non_claim"])
        self.assertIn("return override", guidance["non_claim"])
        self.assertIn("public SDK readiness", guidance["non_claim"])

    def test_item_return_target_set_guidance_keeps_non_completion_scope_narrow(self) -> None:
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
        self.assertEqual(guidance["classification"], "internal_gameplay_policy_item_return_only_non_completion")
        self.assertIn("internal_non_completion_side_lane", guidance["why_blocked"])
        self.assertIn("not_release_readiness_target", guidance["why_blocked"])
        self.assertIn("complete_sdk_accounting_blocked", guidance["why_blocked"])
        self.assertIn("p0_dependency_chain_accounting_blocked", guidance["why_blocked"])
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
            "internal copied-scalar planning only",
            "P0 dependency-chain credit",
            "complete-SDK accounting",
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
            "release readiness",
            "P0 dependency-chain",
            "complete-SDK",
        ):
            self.assertIn(blocked, guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "item-return-only-policy-slice",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_set_guidance=1", text_result.stdout)
        self.assertIn("internal_gameplay_policy_item_return_only_non_completion", text_result.stdout)
        self.assertIn("does not promote Items SDK, Inventory SDK", text_result.stdout)

    def test_structure_release_target_set_guidance_blocks_public_sdk_promotion(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "minimal-second-source-intake",
            "--target-set",
            "structure-observer-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(
            report["target_sets"],
            ["minimal-second-source-intake", "structure-observer-intake"],
        )
        guidance = {item["target_set"]: item for item in report["target_set_guidance"]}
        self.assertEqual(set(guidance), {"minimal-second-source-intake", "structure-observer-intake"})

        minimal = guidance["minimal-second-source-intake"]
        self.assertEqual(minimal["classification"], "release_compact_inventory_structure_layout_evidence")
        self.assertIn("compact_layout_evidence_only", minimal["why_blocked"])
        self.assertIn("public_inventory_items_structure_sdks_blocked", minimal["why_blocked"])
        self.assertIn("identity_lookup_resourcehandle_blocked", minimal["why_blocked"])
        self.assertIn("mutation_return_override_blocked", minimal["why_blocked"])
        self.assertIn("CanUse, AllowRemoteAddToInventory", " ".join(minimal["snapshot_prep_checks"]))
        self.assertIn("Inventory SDK", minimal["non_claim"])
        self.assertIn("Items SDK", minimal["non_claim"])
        self.assertIn("StructureEvents", minimal["non_claim"])
        self.assertIn("target-set expansion", minimal["non_claim"])

        structure = guidance["structure-observer-intake"]
        self.assertEqual(structure["classification"], "release_gameplay_policy_structure_observer")
        self.assertIn("structure_observer_layout_evidence_only", structure["why_blocked"])
        self.assertIn("public_structureevents_sdk_blocked", structure["why_blocked"])
        self.assertIn("pincode_player_structure_identity_redaction_required", structure["why_blocked"])
        self.assertIn("runtime_producer_validation_requires_separate_approval", structure["why_blocked"])
        self.assertIn("GameplayPolicyEvent lane", " ".join(structure["snapshot_prep_checks"]))
        self.assertIn("IsAllowedToBuild", " ".join(structure["snapshot_prep_checks"]))
        self.assertIn("public StructureEvents", structure["non_claim"])
        self.assertIn("Structure SDK", structure["non_claim"])
        self.assertIn("runtime validation", structure["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "minimal-second-source-intake",
            "--target-set",
            "structure-observer-intake",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_set_guidance=2", text_result.stdout)
        self.assertIn("release_compact_inventory_structure_layout_evidence", text_result.stdout)
        self.assertIn("release_gameplay_policy_structure_observer", text_result.stdout)
        self.assertIn("does not promote public StructureEvents", text_result.stdout)

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

    def test_player_lifecycle_anchor_candidates_guidance_keeps_all_six_planning_only(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "players-lifecycle-anchor-candidates",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_sets"], ["players-lifecycle-anchor-candidates"])
        self.assertEqual(len(report["targets"]), 1)
        self.assertEqual(
            report["targets"][0]["target"],
            "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress",
        )
        self.assertIn("not_identity_anchor", report["targets"][0]["why_blocked"])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "players-lifecycle-anchor-candidates")
        self.assertEqual(guidance["classification"], "players_lifecycle_anchor_candidates_guidance_only_candidate")
        self.assertIn("planning_guidance_only", guidance["why_blocked"])
        self.assertIn("not_release_readiness_target", guidance["why_blocked"])
        self.assertIn("approved_runtime_evidence_missing", guidance["why_blocked"])
        self.assertIn("runtime_ordering_unproven", guidance["why_blocked"])
        self.assertIn("principal_invalidation_semantics_unproven", guidance["why_blocked"])
        self.assertEqual(
            guidance["approved_triplet_sources"],
            [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(guidance["approved_runtime_triplet_source_names"], guidance["approved_triplet_sources"])
        self.assertEqual(guidance["policy_scope"], "source_names_only_not_runtime_evidence")
        self.assertEqual(
            guidance["runtime_triplet_evidence_status"],
            "approved_source_names_only_runtime_evidence_missing",
        )
        self.assertFalse(guidance["approved_runtime_evidence_present"])
        self.assertFalse(guidance["runtime_ready"])
        self.assertFalse(guidance["public_sdk_ready"])
        self.assertFalse(guidance["promotion_ready"])
        self.assertEqual(
            guidance["static_lifecycle_anchor_sources"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        self.assertEqual(
            guidance["observer_rejected_start_sources"],
            ["ShooterGameMode.CheckJoinInProgress"],
        )
        self.assertEqual(guidance["chronology_only_non_anchor_sources"], ["GameMode.K2_PostLogin"])
        self.assertEqual(guidance["chronology_guidance_only_source_names"], ["GameMode.K2_PostLogin"])
        self.assertEqual(
            guidance["delegate_guidance_only_source_names"],
            [
                "ShooterGameMode.OnPostLogin__DelegateSignature",
                "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            ],
        )
        self.assertEqual(
            guidance["guidance_only_non_triplet_source_names"],
            [
                "GameMode.K2_PostLogin",
                "ShooterGameMode.OnPostLogin__DelegateSignature",
                "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            ],
        )
        self.assertEqual(guidance["all_six_planning_gap_evidence_status"], "non_evidence")
        roles = {item["target"]: item for item in guidance["source_roles"]}
        self.assertTrue(roles["ShooterGameMode.HandleNewPlayer"]["approved_runtime_triplet_source_name"])
        self.assertTrue(roles["ShooterGameMode.HandleNewPlayer"]["static_lifecycle_anchor_source_name"])
        self.assertTrue(roles["ShooterGameMode.CheckJoinInProgress"]["approved_runtime_triplet_source_name"])
        self.assertTrue(roles["ShooterGameMode.CheckJoinInProgress"]["rejected_start_triplet_source_name"])
        self.assertFalse(roles["GameMode.K2_PostLogin"]["approved_runtime_triplet_source_name"])
        self.assertTrue(roles["GameMode.K2_PostLogin"]["chronology_guidance_only_non_anchor_source_name"])
        self.assertFalse(
            roles["ShooterGameMode.OnStartNewPlayer__DelegateSignature"]["approved_runtime_triplet_source_name"]
        )
        self.assertTrue(
            roles["ShooterGameMode.OnStartNewPlayer__DelegateSignature"][
                "delegate_guidance_only_non_triplet_source_name"
            ]
        )
        self.assertIn("approved_runtime_evidence", guidance["does_not_satisfy"])
        self.assertIn("runtime_readiness", guidance["does_not_satisfy"])
        self.assertIn("public SDK readiness", " ".join(guidance["non_claims"]))
        self.assertIn("distinct non-/tmp sanitized planning comparison snapshot root", guidance["next_offline_input"])
        self.assertIn("HandleNewPlayer and ShooterGameMode.OnLogout", guidance["next_offline_input"])
        for target in (
            "GameMode.K2_PostLogin",
            "ShooterGameMode.CheckJoinInProgress",
            "ShooterGameMode.HandleNewPlayer",
            "ShooterGameMode.OnLogout",
            "ShooterGameMode.OnPostLogin__DelegateSignature",
            "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
        ):
            self.assertIn(target, guidance["snapshot_prep_checks"][0])
        self.assertIn(
            "require distinct artifact identity before any all-six planning-layout comparison claim",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "consume an all-six accepted comparison only through --planning-layout-intake or non-promotional readiness reporting; do not label it accepted second-source readiness",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "approved triplet sources are exactly ShooterGameMode.HandleNewPlayer, ShooterGameMode.CheckJoinInProgress, and ShooterGameMode.OnLogout",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "keep GameMode.K2_PostLogin as non-anchor chronology only; property FName mismatch diagnostics must not become triplet source, lifecycle anchor, second-source, runtime, public SDK, release, or v1 evidence",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "do not let all-six planning comparison clear approved_runtime_evidence_missing, public SDK readiness, runtime readiness, release readiness, principal validity, or principal invalidation blockers",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn(
            "do not use this target set for release/readiness or public SDK promotion gates",
            guidance["snapshot_prep_checks"],
        )
        self.assertIn("approved runtime evidence", guidance["non_claim"])
        self.assertIn("public Player SDK", guidance["non_claim"])
        self.assertIn("v1 completion", guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "players-lifecycle-anchor-candidates",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=1 scope=offline_planning_only target_set_guidance=1", text_result.stdout)
        self.assertIn("target_set=players-lifecycle-anchor-candidates", text_result.stdout)
        self.assertIn("approved_runtime_evidence_missing", text_result.stdout)
        self.assertIn(
            "approved_triplet_sources=ShooterGameMode.HandleNewPlayer,ShooterGameMode.CheckJoinInProgress,ShooterGameMode.OnLogout",
            text_result.stdout,
        )
        self.assertIn(
            "approved_runtime_triplet_source_names=ShooterGameMode.HandleNewPlayer,ShooterGameMode.CheckJoinInProgress,ShooterGameMode.OnLogout",
            text_result.stdout,
        )
        self.assertIn(
            "guidance_only_non_triplet_source_names=GameMode.K2_PostLogin,ShooterGameMode.OnPostLogin__DelegateSignature,ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            text_result.stdout,
        )
        self.assertIn("runtime_triplet_evidence_status=approved_source_names_only_runtime_evidence_missing", text_result.stdout)
        self.assertIn("approved_runtime_evidence_present=false", text_result.stdout)
        self.assertIn("all_six_planning_gap_evidence_status=non_evidence", text_result.stdout)
        self.assertIn("does not promote approved runtime evidence", text_result.stdout)

    def test_all_six_lifecycle_planning_gap_artifact_is_source_bound_and_non_promotional(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "docs"
            / "research"
            / "player-identity-planning-sources"
            / "players-lifecycle-anchor-candidates-all-six-planning-gap.json"
        )

        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(
            artifact["schema"],
            "obelisk.players-lifecycle-anchor-candidates-all-six-planning-gap.v1",
        )
        self.assertEqual(artifact["target_set"], "players-lifecycle-anchor-candidates")
        self.assertTrue(artifact["planning_only"])
        self.assertEqual(artifact["readiness_classification"], "planning_only")
        self.assertEqual(len(artifact["base_fixture_targets"]), 6)
        targets = {item["target"]: item for item in artifact["base_fixture_targets"]}
        self.assertEqual(
            set(targets),
            {
                "GameMode.K2_PostLogin",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.OnLogout",
                "ShooterGameMode.OnPostLogin__DelegateSignature",
                "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            },
        )
        self.assertEqual(
            targets["ShooterGameMode.HandleNewPlayer"]["base_fixture_sha256"],
            "a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b",
        )
        self.assertEqual(
            targets["ShooterGameMode.OnLogout"]["base_fixture_sha256"],
            "e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa",
        )
        accepted_durable = sorted(
            target
            for target, item in targets.items()
            if item.get("current_promoted_durable_source_bound_lifecycle_evidence") is True
        )
        self.assertEqual(
            accepted_durable,
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        approved_triplet_sources = sorted(
            target
            for target, item in targets.items()
            if item.get("current_approved_triplet_source") is True
        )
        self.assertEqual(
            approved_triplet_sources,
            [
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertFalse(targets["GameMode.K2_PostLogin"]["current_approved_triplet_source"])
        self.assertTrue(targets["GameMode.K2_PostLogin"]["chronology_only_non_anchor"])
        operational_triplet_sources = artifact["operational_consolidation"]["approved_triplet_sources"]
        self.assertEqual(
            operational_triplet_sources["targets"],
            [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(
            operational_triplet_sources["static_lifecycle_anchor_targets"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        self.assertEqual(
            operational_triplet_sources["observer_rejected_start_targets"],
            ["ShooterGameMode.CheckJoinInProgress"],
        )
        self.assertEqual(
            operational_triplet_sources["chronology_only_non_anchor_targets"],
            ["GameMode.K2_PostLogin"],
        )
        self.assertTrue(operational_triplet_sources["only_these_targets_may_source_approved_triplet_roles"])
        self.assertEqual(
            operational_triplet_sources["k2_postlogin_status"],
            "non_anchor_chronology_only_property_fname_mismatch_rejected",
        )
        self.assertEqual(operational_triplet_sources["all_six_planning_gap_evidence_status"], "non_evidence")
        self.assertEqual(
            operational_triplet_sources["exact_rejected_start_role_policy"],
            {
                "role": "session_start_rejected",
                "status": "exact_role_only",
                "target": "ShooterGameMode.CheckJoinInProgress",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["1", "0"],
                "required_event_boundary": (
                    "post-original copied observer event accepted by analyzer/bundle/approved-checker chain"
                ),
                "disallowed_substitutes": [
                    "ShooterGameMode.HandleNewPlayer rejected-start tuples",
                    "passive snapshots",
                    "diagnostic-only lines",
                ],
            },
        )
        self.assertFalse(artifact["historical_scratch_comparison"]["durable"])
        self.assertEqual(artifact["historical_scratch_comparison"]["accepted_targets"], 6)
        self.assertFalse(artifact["durable_all_six_comparison"]["provided"])
        self.assertFalse(artifact["durable_all_six_comparison"]["accepted"])
        self.assertEqual(
            artifact["durable_all_six_comparison"]["reason"],
            "distinct_non_tmp_candidate_snapshot_root_missing",
        )
        self.assertIn(
            "materialize or recreate the six vanilla candidate snapshots outside /tmp under an approved non-protected offline or repo fixture root",
            artifact["durable_all_six_comparison"]["minimal_patch_needed"],
        )
        self.assertEqual(
            artifact["durable_all_six_comparison"]["evidence_scope_when_materialized"],
            "planning_layout_intake_only_not_second_source",
        )
        self.assertIn(
            "second_source_readiness",
            artifact["durable_all_six_comparison"]["does_not_satisfy"],
        )
        self.assertEqual(
            artifact["current_durable_source_bound_lifecycle_anchor_evidence"]["accepted_targets"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        current_triplet_sources = artifact["current_approved_triplet_sources"]
        self.assertEqual(
            current_triplet_sources["accepted_targets"],
            [
                "ShooterGameMode.HandleNewPlayer",
                "ShooterGameMode.CheckJoinInProgress",
                "ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(
            current_triplet_sources["static_lifecycle_anchor_targets"],
            ["ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"],
        )
        self.assertEqual(current_triplet_sources["observer_rejected_start_targets"], ["ShooterGameMode.CheckJoinInProgress"])
        self.assertEqual(current_triplet_sources["chronology_only_non_anchor_targets"], ["GameMode.K2_PostLogin"])
        self.assertEqual(
            current_triplet_sources["guidance_only_non_triplet_targets"],
            [
                "GameMode.K2_PostLogin",
                "ShooterGameMode.OnPostLogin__DelegateSignature",
                "ShooterGameMode.OnStartNewPlayer__DelegateSignature",
            ],
        )
        self.assertEqual(current_triplet_sources["all_six_planning_gap_evidence_status"], "non_evidence")
        self.assertEqual(
            current_triplet_sources["exact_rejected_start_role_policy"],
            {
                "role": "session_start_rejected",
                "status": "exact_role_only",
                "target": "ShooterGameMode.CheckJoinInProgress",
                "required_copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
                "required_copied_bool_values": ["1", "0"],
                "required_event_boundary": (
                    "post-original copied observer event accepted by analyzer/bundle/approved-checker chain"
                ),
                "disallowed_substitutes": [
                    "ShooterGameMode.HandleNewPlayer rejected-start tuples",
                    "passive snapshots",
                    "diagnostic-only lines",
                ],
            },
        )
        self.assertEqual(
            artifact["promotion_gate"],
            {
                "blockers": [
                    "target_set_not_release_readiness",
                    "approved_runtime_evidence_missing",
                    "distinct_non_tmp_candidate_snapshot_root_missing",
                ],
                "promotion_ready": False,
                "public_sdk_ready": False,
                "ready": False,
                "ready_scope": "planning_only",
                "runtime_ready": False,
            },
        )
        self.assertIn("approved_runtime_evidence_missing", artifact["does_not_satisfy_blockers"])
        self.assertIn("does not clear approved_runtime_evidence_missing", artifact["non_claims"])
        self.assertIn(
            "does not change approved lifecycle triplet sources beyond ShooterGameMode.HandleNewPlayer, ShooterGameMode.CheckJoinInProgress, and ShooterGameMode.OnLogout",
            artifact["non_claims"],
        )
        self.assertIn(
            "does not promote GameMode.K2_PostLogin beyond non-anchor chronology-only diagnostics",
            artifact["non_claims"],
        )

    def test_observed_fname_chain_check_records_ragnarok_handle_new_player_mismatch(self) -> None:
        result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-chain",
            "28418,21314,22968,28516,17724",
            "--observed-fname-chain-occurrences",
            "4",
            "--target-set",
            "players-lifecycle-anchor-candidates",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-observed-fname-chain-check.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["evidence_scope"], "diagnostic_fname_chain_planning_only_not_second_source")
        self.assertEqual(report["artifact_role"], "diagnostic_planning_only_not_second_source_input")
        self.assertEqual(report["layout_evidence_status"], "not_layout_evidence")
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_candidate_snapshot_root"])
        self.assertEqual(report["source_scope"], "sanitized_snapshot_root_only")
        self.assertEqual(report["second_source_status"], "not_applicable")
        self.assertIn(
            "copied_runtime_diagnostic_line_not_distinct_sanitized_snapshot",
            report["second_source_blockers"],
        )
        self.assertIn(
            "observed_fname_indices_only_no_property_names_classes_offsets_sizes_or_bool_metadata",
            report["second_source_blockers"],
        )
        self.assertTrue(report["not_second_source"])
        self.assertEqual(report["diagnostic_observation_count"], 4)
        self.assertEqual(
            report["diagnostic_observation_count_scope"],
            "repeated_runtime_mismatch_count_diagnostic_only",
        )
        self.assertTrue(report["diagnostic_observation_repeated"])
        self.assertEqual(
            report["target"],
            "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
        )
        self.assertEqual(report["target_sets"], ["players-lifecycle-anchor-candidates"])
        self.assertEqual(report["status"], "unresolved_mismatch")
        self.assertEqual(report["readiness_effect"], "none")
        self.assertEqual(report["readiness_classification"], "planning_only")
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["exact_property_chain_match"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(
            report["does_not_satisfy_readiness"],
            [
                "second_source_layout_evidence",
                "runtime_readiness",
                "public_sdk_readiness",
                "release_readiness",
                "v1_completion",
            ],
        )
        self.assertEqual(report["expected_name_indices"], [28411, 21307, 22961, 28509, 17716])
        self.assertEqual(report["observed_name_indices"], [28418, 21314, 22968, 28516, 17724])
        self.assertEqual(report["deltas"], [7, 7, 7, 7, 8])
        self.assertIn("second_source_layout_evidence", report["prohibited_evidence_uses"])
        self.assertIn("candidate_snapshot_root", report["prohibited_evidence_uses"])
        self.assertEqual(report["observed_indices_found_count"], 0)
        self.assertEqual(report["unmatched_observed_name_indices"], [28418, 21314, 22968, 28516, 17724])
        self.assertIn("approved_runtime_evidence_missing", report["blockers"])
        self.assertIn("observed_fname_chain_check_not_promotion_gate", report["blockers"])
        self.assertIn("observed_fname_chain_unresolved", report["blockers"])
        self.assertEqual(
            report["promotion_gate"]["blockers"],
            [
                {"reason": "approved_runtime_evidence_missing", "count": 1},
                {"reason": "observed_fname_chain_check_not_promotion_gate", "count": 1},
                {"reason": "observed_fname_chain_unresolved", "count": 1},
            ],
        )
        self.assertEqual(len(report["property_comparison"]), 5)
        self.assertEqual(report["property_comparison"][0]["property_name"], "NewPlayer")
        self.assertEqual(report["property_comparison"][4]["property_name"], "ReturnValue")
        self.assertEqual(report["target_set_context"][0]["target_set"], "players-lifecycle-anchor-candidates")
        self.assertTrue(report["target_set_context"][0]["contains_target"])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        self.assertIn("approved_runtime_evidence_missing", report["target_set_guidance"][0]["why_blocked"])
        requirement = report["next_offline_artifact_requirement"]
        self.assertEqual(requirement["artifact"], "distinct_sanitized_lifecycle_ufunction_snapshot_root")
        self.assertEqual(requirement["status_needed"], "required_before_deploy_request")
        self.assertEqual(
            requirement["required_targets"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(requirement["comparison_mode"], "semantic_layout_without_strict_identity_indices")
        self.assertIn("evidence.artifact_sha256", requirement["required_identity_fields"])
        self.assertIn("BoolProperty byte/field metadata", requirement["required_shape_fields"])
        self.assertIn("direct or symlink-resolved protected live-server paths", requirement["prohibited_inputs"])
        self.assertIn("broad FName scans", requirement["prohibited_inputs"])
        self.assertIn("broad GObjects scans", requirement["prohibited_inputs"])
        self.assertIn("does not create second-source layout evidence", report["non_claims"])
        self.assertIn("does not accept or reject runtime principal lifecycle evidence", report["non_claims"])

        text_result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-chain",
            "28418,21314,22968,28516,17724",
            "--observed-fname-chain-occurrences",
            "4",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("status=unresolved_mismatch", text_result.stdout)
        self.assertIn("expected=28411,21307,22961,28509,17716", text_result.stdout)
        self.assertIn("observed=28418,21314,22968,28516,17724", text_result.stdout)
        self.assertIn("deltas=7,7,7,7,8", text_result.stdout)
        self.assertIn("layout_evidence_status=not_layout_evidence", text_result.stdout)
        self.assertIn("not_second_source=true", text_result.stdout)
        self.assertIn("can_be_second_source=false", text_result.stdout)
        self.assertIn("promotion_ready=false runtime_ready=false", text_result.stdout)
        self.assertIn("diagnostic_observation_count=4 scope=diagnostic_only", text_result.stdout)
        self.assertIn("next_offline_artifact=distinct_sanitized_lifecycle_ufunction_snapshot_root", text_result.stdout)

    def test_observed_fname_chain_exact_match_still_is_not_second_source(self) -> None:
        result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-chain",
            "28411,21307,22961,28509,17716",
            "--observed-fname-chain-occurrences",
            "2",
            "--target-set",
            "players-lifecycle-anchor-candidates",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "matched_planning_only")
        self.assertTrue(report["exact_property_chain_match"])
        self.assertEqual(report["layout_evidence_status"], "not_layout_evidence")
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_candidate_snapshot_root"])
        self.assertEqual(report["second_source_status"], "not_applicable")
        self.assertTrue(report["not_second_source"])
        self.assertEqual(report["readiness_effect"], "none")
        self.assertEqual(report["readiness_classification"], "planning_only")
        self.assertIn("second_source_layout_evidence", report["does_not_satisfy_readiness"])
        self.assertIn("observed_fname_chain_check_not_promotion_gate", report["blockers"])
        self.assertNotIn("observed_fname_chain_unresolved", report["blockers"])
        self.assertEqual(
            report["promotion_gate"]["blockers"],
            [{"reason": "observed_fname_chain_check_not_promotion_gate", "count": 1}],
        )
        self.assertIn(
            "copied_runtime_diagnostic_line_not_distinct_sanitized_snapshot",
            report["second_source_blockers"],
        )
        self.assertEqual(
            report["next_offline_artifact_requirement"]["required_targets"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
            ],
        )

    def test_observed_fname_chain_check_records_ragnarok_on_logout_mismatch(self) -> None:
        result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-target",
            "ShooterGameMode.OnLogout",
            "--observed-fname-chain",
            "28550",
            "--observed-fname-chain-occurrences",
            "3",
            "--target-set",
            "players-lifecycle-anchor-candidates",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["target"],
            "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
        )
        self.assertEqual(report["status"], "unresolved_mismatch")
        self.assertEqual(report["diagnostic_observation_count"], 3)
        self.assertEqual(
            report["diagnostic_observation_count_scope"],
            "repeated_runtime_mismatch_count_diagnostic_only",
        )
        self.assertTrue(report["diagnostic_observation_repeated"])
        self.assertEqual(report["expected_name_indices"], [28543])
        self.assertEqual(report["observed_name_indices"], [28550])
        self.assertEqual(report["deltas"], [7])
        self.assertEqual(report["readiness_effect"], "none")
        self.assertTrue(report["not_second_source"])
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_second_source_layout_evidence"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("observed_fname_chain_unresolved", report["blockers"])
        self.assertIn("does not create second-source layout evidence", report["non_claims"])

    def test_observed_fname_chain_rejects_non_planning_target_set_context(self) -> None:
        result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-chain",
            "28418,21314,22968,28516,17724",
            "--target-set",
            "minimal-second-source-intake",
            "--json",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "--observed-fname-chain only accepts planning-only target sets: minimal-second-source-intake",
            result.stderr,
        )

    def test_observed_fname_chain_rejects_planning_target_set_that_does_not_contain_target(self) -> None:
        result = run_compare(
            REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            None,
            "--observed-fname-chain",
            "28418,21314,22968,28516,17724",
            "--target-set",
            "structure-aggregate-census-planning",
            "--json",
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "--observed-fname-chain target set(s) do not contain --observed-fname-target: structure-aggregate-census-planning",
            result.stderr,
        )

    def test_handle_new_player_fname_mismatch_artifact_is_unresolved_and_non_promotional(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "docs"
            / "research"
            / "player-identity-planning-sources"
            / "players-lifecycle-handle-new-player-fname-mismatch-ragnarok-20260604.json"
        )

        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

        self.assertEqual(
            artifact["schema"],
            "obelisk.players-lifecycle-handle-new-player-fname-mismatch.v1",
        )
        self.assertEqual(artifact["artifact_status"], "planning_diagnostic_unresolved")
        self.assertTrue(artifact["planning_only"])
        self.assertEqual(artifact["target_set"], "players-lifecycle-anchor-candidates")
        self.assertEqual(artifact["target"], "ShooterGameMode.HandleNewPlayer")
        self.assertEqual(artifact["evidence_scope"], "diagnostic_fname_chain_planning_only_not_second_source")
        self.assertEqual(artifact["artifact_role"], "diagnostic_planning_only_not_second_source_input")
        self.assertEqual(artifact["layout_evidence_status"], "not_layout_evidence")
        self.assertFalse(artifact["second_source_layout_evidence"])
        self.assertFalse(artifact["can_be_used_as_second_source_layout_evidence"])
        self.assertFalse(artifact["can_be_used_as_candidate_snapshot_root"])
        self.assertEqual(artifact["second_source_status"], "not_applicable")
        self.assertTrue(artifact["not_second_source"])
        self.assertEqual(artifact["readiness_effect"], "none")
        self.assertFalse(artifact["promotion_ready"])
        self.assertFalse(artifact["public_sdk_ready"])
        self.assertFalse(artifact["runtime_ready"])
        self.assertEqual(artifact["runtime_snapshot"]["map"], "Ragnarok")
        self.assertEqual(
            artifact["runtime_snapshot"]["snapshot_id"],
            "passive-manual-20260604T085119Z-arkserver+arkserver2-3215640",
        )
        self.assertEqual(artifact["runtime_snapshot"]["captured_at_utc"], "2026-06-04T08:51:19Z")
        self.assertFalse(artifact["runtime_snapshot"]["approved_runtime_evidence"])
        self.assertEqual(artifact["runtime_observation_summary"]["organic_player_snapshots"], 2)
        self.assertTrue(artifact["runtime_observation_summary"]["diagnostic_only"])
        self.assertEqual(artifact["runtime_observation_summary"]["readiness_effect"], "none")
        self.assertEqual(artifact["runtime_observation_summary"]["accepted_count"], 0)
        self.assertEqual(artifact["runtime_observation_summary"]["rejected_count"], 0)
        self.assertEqual(artifact["runtime_observation_summary"]["diagnostic_candidate_count"], 17)
        self.assertEqual(
            artifact["runtime_observation_summary"]["diagnostic_candidate_target_counts"],
            {
                "GameMode.K2_PostLogin": 3,
                "ShooterGameMode.CheckJoinInProgress": 2,
                "ShooterGameMode.HandleNewPlayer": 7,
                "ShooterGameMode.OnLogout": 5,
            },
        )
        self.assertEqual(
            artifact["runtime_observation_summary"]["sibling_map_counts"]["TheIsland"],
            {
                "accepted_count": 0,
                "diagnostic_candidate_count": 0,
                "rejected_count": 0,
            },
        )
        mismatch_counts = {
            item["target"]: item for item in artifact["runtime_observation_summary"]["mismatch_counts"]
        }
        self.assertEqual(mismatch_counts["ShooterGameMode.HandleNewPlayer"]["observed_count"], 4)
        self.assertEqual(mismatch_counts["ShooterGameMode.OnLogout"]["observed_count"], 3)
        self.assertTrue(
            all(item["not_second_source"] for item in artifact["runtime_observation_summary"]["mismatch_counts"])
        )
        self.assertEqual(
            artifact["fixture_expected_name_indices"],
            [28411, 21307, 22961, 28509, 17716],
        )
        self.assertEqual(
            artifact["observed_name_indices"],
            [28418, 21314, 22968, 28516, 17724],
        )
        self.assertEqual(artifact["deltas"], [7, 7, 7, 7, 8])
        self.assertFalse(artifact["exact_property_chain_match"])
        self.assertEqual(artifact["status"], "unresolved_mismatch")
        self.assertEqual(artifact["observed_indices_found_in_committed_sanitized_snapshots"], [])
        self.assertIn(
            "copied_runtime_diagnostic_line_not_distinct_sanitized_snapshot",
            artifact["second_source_blockers"],
        )
        self.assertIn(
            "observed_fname_indices_only_no_property_names_classes_offsets_sizes_or_bool_metadata",
            artifact["second_source_blockers"],
        )
        self.assertIn("second_source_layout_evidence", artifact["prohibited_evidence_uses"])
        self.assertIn("candidate_snapshot_root", artifact["prohibited_evidence_uses"])
        self.assertEqual(
            artifact["does_not_satisfy_readiness"],
            [
                "second_source_layout_evidence",
                "runtime_readiness",
                "public_sdk_readiness",
                "release_readiness",
                "v1_completion",
            ],
        )
        self.assertEqual(artifact["related_observed_fname_mismatches"][0]["target"], "ShooterGameMode.OnLogout")
        self.assertEqual(artifact["related_observed_fname_mismatches"][0]["fixture_expected_name_indices"], [28543])
        self.assertEqual(artifact["related_observed_fname_mismatches"][0]["observed_name_indices"], [28550])
        self.assertEqual(artifact["related_observed_fname_mismatches"][0]["diagnostic_observation_count"], 3)
        self.assertTrue(artifact["related_observed_fname_mismatches"][0]["not_second_source"])
        self.assertIn(
            "search_by_fname_matcher_alone_is_safe",
            {item["hypothesis"] for item in artifact["rejected_hypotheses"]},
        )
        self.assertIn("approved_runtime_evidence_missing", artifact["blockers"])
        self.assertIn("observed_fname_chain_check_not_promotion_gate", artifact["blockers"])
        self.assertFalse(artifact["promotion_gate"]["ready"])
        self.assertFalse(artifact["promotion_gate"]["runtime_ready"])
        self.assertIn("observed_fname_chain_check_not_promotion_gate", artifact["promotion_gate"]["blockers"])
        self.assertIn("second_source_layout_evidence_blocked", artifact["does_not_satisfy_blockers"])
        requirement = artifact["next_offline_artifact_requirement"]
        self.assertEqual(requirement["artifact"], "distinct_sanitized_lifecycle_ufunction_snapshot_root")
        self.assertEqual(requirement["status_needed"], "required_before_deploy_request")
        self.assertEqual(
            requirement["required_targets"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(requirement["comparison_mode"], "semantic_layout_without_strict_identity_indices")
        self.assertIn("evidence.evidence_pack_id", requirement["required_identity_fields"])
        self.assertIn("property order", requirement["required_shape_fields"])
        self.assertIn("direct or symlink-resolved protected live-server paths", requirement["prohibited_inputs"])
        self.assertIn("broad FName scans", requirement["prohibited_inputs"])
        self.assertIn("broad GObjects scans", requirement["prohibited_inputs"])
        self.assertIn("does not create second-source layout evidence", artifact["non_claims"])
        self.assertIn("does not mark anything accepted runtime evidence", artifact["non_claims"])

    def test_lifecycle_snapshot_root_check_accepts_distinct_offline_two_target_root_only_as_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.lifecycle-ufunction-snapshot-root-requirement.v1")
        self.assertEqual(report["artifact"], "distinct_sanitized_lifecycle_ufunction_snapshot_root")
        self.assertEqual(
            report["required_targets"],
            [
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
            ],
        )
        self.assertEqual(
            report["required_identity_fields"],
            [
                "evidence.ark_binary_sha256",
                "evidence.artifact_kind=offline_core",
                "evidence.artifact_sha256",
                "evidence.capture_id",
                "evidence.evidence_pack_id",
            ],
        )
        self.assertEqual(report["comparison_mode"], "semantic_layout_without_strict_identity_indices")
        self.assertTrue(report["offline_requirement"]["satisfied"])
        self.assertEqual(report["offline_requirement"]["status"], "accepted")
        self.assertEqual(report["comparison_counts"], {"accepted": 2, "inconclusive": 0, "rejected": 0})
        self.assertTrue(report["base_root_artifact_identity_consistent"])
        self.assertTrue(report["candidate_root_artifact_identity_consistent"])
        self.assertEqual(
            report["candidate_snapshot_scope"],
            {
                "exact_required_targets": True,
                "required_targets": [
                    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                ],
                "candidate_targets": [
                    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                ],
                "extra_targets": [],
                "missing_targets": [],
                "required_snapshot_filenames": [
                    "ShooterGameMode.HandleNewPlayer.snapshot.json",
                    "ShooterGameMode.OnLogout.snapshot.json",
                ],
                "focused_candidate_root_required": False,
            },
        )
        self.assertFalse(report["approved_runtime_evidence"])
        self.assertEqual(report["approved_runtime_evidence_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(report["layout_only_evidence_satisfies_approved_runtime_evidence"])
        self.assertTrue(report["layout_only_evidence_rejected_for_runtime_readiness"])
        self.assertEqual(report["readiness_effect"], "none")
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_complete"])
        self.assertEqual(
            report["promotion_gate"]["blockers"],
            [
                {"reason": "approved_runtime_evidence_missing", "count": 1},
                {"reason": "lifecycle_snapshot_root_check_not_runtime_evidence", "count": 1},
            ],
        )
        for target_detail in report["target_details"]:
            self.assertEqual(target_detail["status"], "accepted")
            self.assertEqual(target_detail["base_identity"]["artifact_kind"], "offline_core")
            self.assertEqual(target_detail["candidate_identity"]["artifact_kind"], "offline_core")
            self.assertNotEqual(
                target_detail["base_identity"]["artifact_sha256"],
                target_detail["candidate_identity"]["artifact_sha256"],
            )
            self.assertEqual(target_detail["identity_reasons"], [])
        self.assertIn("passive player-principal snapshot manifests", report["prohibited_inputs"])
        self.assertIn("ReflectionScanner analyzer or broad scanner output", report["prohibited_inputs"])
        self.assertIn("layout-only readiness/comparison reports", report["prohibited_inputs"])
        self.assertIn("approved_runtime_evidence", report["does_not_satisfy_readiness"])
        self.assertIn("does not clear approved_runtime_evidence_missing", report["non_claims"])
        self.assertEqual(
            report["next_offline_artifact_requirement"]["comparison_command_template"],
            "python3 scripts/compare_reflection_snapshots.py --base-root "
            "tests/fixtures/ufunction_snapshots --candidate-root "
            "<distinct-sanitized-lifecycle-root> --lifecycle-snapshot-root-check --json",
        )
        self.assertEqual(
            report["next_offline_action"],
            {
                "status": "offline_requirement_satisfied_planning_only",
                "action": "archive_lifecycle_snapshot_root_check_as_planning_layout_evidence",
                "next_blocker": "approved_runtime_evidence_missing",
                "candidate_root_requirements": {
                    "exact_required_targets_only": True,
                    "required_targets": [
                        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                        "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                    ],
                    "required_snapshot_filenames": [
                        "ShooterGameMode.HandleNewPlayer.snapshot.json",
                        "ShooterGameMode.OnLogout.snapshot.json",
                    ],
                    "missing_targets": [],
                    "extra_target_count": 0,
                    "complete_offline_core_identity_required": True,
                    "distinct_from_base_identity_required": True,
                    "broad_root_or_report_input_accepted": False,
                    "runtime_or_public_sdk_readiness_claim": False,
                },
                "runtime_or_public_sdk_readiness_claim": False,
            },
        )

    def test_lifecycle_snapshot_root_check_accepts_distinct_candidate_against_committed_fixture_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_distinct_lifecycle_fixture_root(root / "candidate")

            result = run_compare(
                REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["offline_requirement"]["satisfied"])
        self.assertEqual(report["comparison_counts"], {"accepted": 2, "inconclusive": 0, "rejected": 0})
        self.assertTrue(report["candidate_snapshot_scope"]["exact_required_targets"])
        self.assertEqual(report["candidate_snapshot_scope"]["extra_targets"], [])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["readiness_effect"], "none")
        self.assertEqual(
            report["next_offline_action"]["status"],
            "offline_requirement_satisfied_planning_only",
        )

    def test_lifecycle_snapshot_root_check_text_output_keeps_runtime_blocker_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("lifecycle_snapshot_root_requirement status=accepted satisfied=true", result.stdout)
        self.assertIn("approved_runtime_evidence=false", result.stdout)
        self.assertIn("runtime_ready=false", result.stdout)
        self.assertIn("public_sdk_ready=false", result.stdout)
        self.assertIn("blocker=approved_runtime_evidence_missing", result.stdout)
        self.assertIn("next_offline_action=archive_lifecycle_snapshot_root_check_as_planning_layout_evidence", result.stdout)
        self.assertIn("runtime_or_public_sdk_readiness_claim=false", result.stdout)

    def test_lifecycle_snapshot_root_check_blocks_same_root_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")

            result = run_compare(
                root / "base",
                root / "base",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["offline_requirement"]["satisfied"])
        self.assertEqual(report["offline_requirement"]["status"], "blocked")
        self.assertEqual(report["comparison_counts"], {"accepted": 0, "inconclusive": 2, "rejected": 0})
        self.assertIn(
            {
                "target": "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "reason": "same_evidence_artifact_identity",
            },
            report["offline_requirement"]["blockers"],
        )
        self.assertIn(
            {
                "target": "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                "reason": "same_evidence_artifact_identity",
            },
            report["offline_requirement"]["blockers"],
        )
        self.assertEqual(
            report["next_offline_action"]["action"],
            "create_or_recover_distinct_sanitized_lifecycle_ufunction_snapshot_root",
        )
        self.assertEqual(report["offline_requirement"]["blocker_count"], 3)
        self.assertEqual(
            report["offline_requirement"]["blocker_reason_counts"],
            {
                "required_lifecycle_targets_not_all_accepted": 2,
                "same_evidence_artifact_identity": 2,
            },
        )
        self.assertEqual(report["next_offline_action"]["candidate_root_requirements"]["extra_target_count"], 0)

    def test_lifecycle_snapshot_root_check_blocks_candidate_extra_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")
            extra_payload = rename_target(base_snapshot(), outer="PrimalItem", name="CanUse")
            write_snapshot(
                root / "candidate" / "sha" / "players_lifecycle",
                extra_payload,
                "PrimalItem.CanUse.snapshot.json",
            )

            result = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["offline_requirement"]["satisfied"])
        self.assertFalse(report["candidate_snapshot_scope"]["exact_required_targets"])
        self.assertEqual(
            report["candidate_snapshot_scope"]["extra_targets"],
            ["obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse"],
        )
        self.assertTrue(report["candidate_snapshot_scope"]["focused_candidate_root_required"])
        self.assertEqual(
            report["candidate_snapshot_scope"]["required_snapshot_filenames"],
            [
                "ShooterGameMode.HandleNewPlayer.snapshot.json",
                "ShooterGameMode.OnLogout.snapshot.json",
            ],
        )
        self.assertIn(
            {
                "target": "obelisk.ufunction-chain.snapshot.v1:PrimalItem.CanUse",
                "reason": "candidate_extra_snapshot_target_not_allowed",
            },
            report["offline_requirement"]["blockers"],
        )
        self.assertIn(
            {"reason": "candidate_snapshot_root_not_exact_two_target_scope", "count": 1},
            report["offline_requirement"]["blockers"],
        )
        self.assertEqual(
            report["offline_requirement"]["blocker_reason_counts"]["candidate_snapshot_root_not_exact_two_target_scope"],
            1,
        )
        self.assertEqual(
            report["next_offline_action"]["candidate_root_requirements"]["extra_target_count"],
            1,
        )
        self.assertFalse(
            report["next_offline_action"]["candidate_root_requirements"]["broad_root_or_report_input_accepted"]
        )

    def test_lifecycle_snapshot_root_check_blocks_missing_complete_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")
            candidate_snapshot = (
                root
                / "candidate"
                / "sha"
                / "players_lifecycle"
                / "ShooterGameMode.OnLogout.snapshot.json"
            )
            payload = json.loads(candidate_snapshot.read_text(encoding="utf-8"))
            payload["evidence"].pop("artifact_sha256")  # type: ignore[index]
            payload["evidence"].pop("capture_id")  # type: ignore[index]
            payload["evidence"].pop("evidence_pack_id")  # type: ignore[index]
            candidate_snapshot.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["offline_requirement"]["satisfied"])
        self.assertEqual(report["offline_requirement"]["status"], "blocked")
        blockers = report["offline_requirement"]["blockers"]
        self.assertIn(
            {
                "target": "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
                "reason": "missing_candidate_evidence_artifact_identity",
            },
            blockers,
        )
        target = {
            item["target"]: item
            for item in report["target_details"]
        }["obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout"]
        self.assertIsNone(target["candidate_identity"])
        self.assertIn("candidate:invalid_artifact_sha256", target["identity_reasons"])
        self.assertIn("candidate:invalid_capture_id", target["identity_reasons"])
        self.assertIn("candidate:invalid_evidence_pack_id", target["identity_reasons"])
        self.assertEqual(
            report["promotion_gate"]["blockers"][0]["reason"],
            "lifecycle_snapshot_root_requirement_blocked",
        )

    def test_lifecycle_snapshot_root_check_blocks_missing_candidate_ark_binary_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")
            candidate_snapshot = (
                root
                / "candidate"
                / "sha"
                / "players_lifecycle"
                / "ShooterGameMode.HandleNewPlayer.snapshot.json"
            )
            payload = json.loads(candidate_snapshot.read_text(encoding="utf-8"))
            payload["evidence"].pop("ark_binary_sha256")  # type: ignore[index]
            candidate_snapshot.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 2, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        target = {
            item["target"]: item
            for item in report["target_details"]
        }["obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer"]
        self.assertIsNone(target["candidate_identity"])
        self.assertIn("candidate:missing_ark_binary_sha256", target["identity_reasons"])
        self.assertIn(
            {
                "target": "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
                "reason": "candidate:missing_ark_binary_sha256",
            },
            report["offline_requirement"]["blockers"],
        )

    def test_lifecycle_snapshot_root_check_rejects_protected_candidate_root_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")

            result = run_compare_raw(
                "--base-root",
                str(root / "base"),
                "--candidate-root",
                "/servidor/ark/obelisk/passive-lifecycle-snapshots",
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("--candidate-root must not read from protected live-server path", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_symlinked_json_side_input_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            candidate = root / "candidate"
            candidate.mkdir()
            diagnostic = root / "diagnostic-report.json"
            diagnostic.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.reflection-snapshot-readiness.v1",
                        "evidence_scope": "second_source_layout_evidence_only",
                    }
                ),
                encoding="utf-8",
            )
            (candidate / "linked-report.json").symlink_to(diagnostic)

            result = run_compare(
                root / "base",
                candidate,
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("--candidate-root must not be a symlink", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_json_side_input_symlink_swap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "candidate"
            candidate.mkdir()
            side_input = candidate / "diagnostic-report.json"
            linked_target = root / "linked-diagnostic-report.json"
            side_input.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.reflection-snapshot-readiness.v1",
                        "evidence_scope": "second_source_layout_evidence_only",
                    }
                ),
                encoding="utf-8",
            )
            linked_target.write_text(side_input.read_text(encoding="utf-8"), encoding="utf-8")
            original_reject = compare.protected_paths.reject_symlink_component
            swapped = False

            def race_reject_symlink_component(path: Path, label: str) -> None:
                nonlocal swapped
                original_reject(path, label)
                if path == side_input and not swapped:
                    swapped = True
                    side_input.unlink()
                    side_input.symlink_to(linked_target)

            with mock.patch.object(
                compare.protected_paths,
                "reject_symlink_component",
                side_effect=race_reject_symlink_component,
            ):
                with self.assertRaisesRegex(SystemExit, "--candidate-root must not be a symlink"):
                    compare.reject_forbidden_lifecycle_input_root("--candidate-root", candidate)

    def test_lifecycle_snapshot_root_check_rejects_passive_manifest_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.player-principal-passive-snapshot.v1",
                        "approved_runtime_evidence": False,
                        "ready": False,
                    }
                ),
                encoding="utf-8",
            )

            result = run_compare(
                root / "base",
                candidate,
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("passive_snapshot_manifest_not_sanitized_ufunction_snapshot", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_diagnostic_only_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "diagnostic-report.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.reflection-observed-fname-chain-check.v1",
                        "evidence_scope": "diagnostic_fname_chain_planning_only_not_second_source",
                        "artifact_role": "diagnostic_planning_only_not_second_source_input",
                        "observed_chain_source": "copied_runtime_diagnostic_line",
                        "can_be_used_as_candidate_snapshot_root": False,
                    }
                ),
                encoding="utf-8",
            )

            result = run_compare(
                root / "base",
                candidate,
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_reflectionscanner_output_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "reflectionscanner-report.json").write_text(
                json.dumps(
                    {
                        "evidence_pack": {
                            "status": "research-candidate",
                            "promotion_gate": {
                                "gate_type": "reflectionscanner_evidence_pack_v1",
                                "ready": False,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )

            result = run_compare(
                root / "base",
                candidate,
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("reflectionscanner_output_not_sanitized_lifecycle_snapshot_root", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_layout_only_report_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            candidate = root / "candidate"
            candidate.mkdir()
            (candidate / "layout-report.json").write_text(
                json.dumps(
                    {
                        "schema": "obelisk.reflection-snapshot-readiness.v1",
                        "evidence_scope": "second_source_layout_evidence_only",
                        "promotion_gate": {"ready": False},
                    }
                ),
                encoding="utf-8",
            )

            result = run_compare(
                root / "base",
                candidate,
                "--lifecycle-snapshot-root-check",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("layout_only_report_not_sanitized_lifecycle_snapshot_root", result.stderr)
        self.assertIn("layout_only_evidence_report_not_sanitized_lifecycle_snapshot_root", result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_non_snapshot_side_lanes(self) -> None:
        cases = (
            (
                "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1",
                "no_users_passive_wait_not_sanitized_lifecycle_snapshot_root",
            ),
            (
                "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                "beta_notice_not_sanitized_lifecycle_snapshot_root",
            ),
            (
                "obelisk.installed-sdk-package-shape.v1",
                "package_shape_not_sanitized_lifecycle_snapshot_root",
            ),
            (
                "obelisk.sdk-status-side-lane-summary.v1",
                "sdk_status_side_lane_not_sanitized_lifecycle_snapshot_root",
            ),
            (
                "obelisk.players-identity-first-evidence.v1",
                "first_evidence_planning_artifact_not_sanitized_lifecycle_snapshot_root",
            ),
        )
        for schema, reason in cases:
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                write_lifecycle_snapshot_root(root / "base")
                candidate = root / "candidate"
                candidate.mkdir()
                (candidate / "side-lane.json").write_text(
                    json.dumps({"schema": schema, "ready": True}),
                    encoding="utf-8",
                )

                result = run_compare(
                    root / "base",
                    candidate,
                    "--lifecycle-snapshot-root-check",
                    "--json",
                )

                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn(reason, result.stderr)

    def test_lifecycle_snapshot_root_check_rejects_readiness_and_target_filters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_lifecycle_snapshot_root(root / "base")
            write_lifecycle_snapshot_root(root / "candidate")

            readiness = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--readiness-report",
            )
            filtered = run_compare(
                root / "base",
                root / "candidate",
                "--lifecycle-snapshot-root-check",
                "--target",
                "ShooterGameMode.HandleNewPlayer",
            )

        self.assertEqual(readiness.returncode, 1)
        self.assertIn("--lifecycle-snapshot-root-check is separate from --readiness-report", readiness.stderr)
        self.assertEqual(filtered.returncode, 1)
        self.assertIn("compares the fixed HandleNewPlayer/OnLogout target set", filtered.stderr)

    def test_structure_aggregate_census_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "structure-aggregate-census-planning",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_sets"], ["structure-aggregate-census-planning"])
        self.assertEqual(report["targets"], [])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "structure-aggregate-census-planning")
        self.assertEqual(guidance["classification"], "structure_aggregate_census_guidance_only_candidate")
        self.assertIn("planning_guidance_only", guidance["why_blocked"])
        self.assertIn("not_release_readiness_target", guidance["why_blocked"])
        self.assertIn("public_structureevents_sdk_blocked", guidance["why_blocked"])
        self.assertIn("VerifyPinCode.ReturnValue", " ".join(guidance["snapshot_prep_checks"]))
        self.assertIn("do not use this target set for release/readiness or public SDK promotion gates", guidance["snapshot_prep_checks"])
        self.assertIn("Structure aggregate/census SDK", guidance["non_claim"])
        self.assertIn("public StructureEvents", guidance["non_claim"])
        self.assertIn("release readiness", guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "structure-aggregate-census-planning",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=0 scope=offline_planning_only target_set_guidance=1", text_result.stdout)
        self.assertIn("target_set=structure-aggregate-census-planning", text_result.stdout)
        self.assertIn("structure_aggregate_census_guidance_only_candidate", text_result.stdout)
        self.assertIn("does not promote Structure aggregate/census SDK", text_result.stdout)

    def test_command_chat_response_route_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "command-chat-response-route-planning",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_sets"], ["command-chat-response-route-planning"])
        self.assertEqual(report["targets"], [])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "command-chat-response-route-planning")
        self.assertEqual(guidance["classification"], "command_chat_response_route_guidance_only_candidate")
        self.assertIn("planning_guidance_only", guidance["why_blocked"])
        self.assertIn("not_release_readiness_target", guidance["why_blocked"])
        self.assertIn("public_response_path_blocked", guidance["why_blocked"])
        for required in (
            "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
            "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
            "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
        ):
            self.assertIn(required, guidance["snapshot_prep_checks"])
        self.assertIn("do not use this target set for release/readiness or public SDK promotion gates", guidance["snapshot_prep_checks"])
        self.assertIn("public reply/send-chat ABI", guidance["non_claim"])
        self.assertIn("command router", guidance["non_claim"])
        self.assertIn("release readiness", guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "command-chat-response-route-planning",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=0 scope=offline_planning_only target_set_guidance=1", text_result.stdout)
        self.assertIn("target_set=command-chat-response-route-planning", text_result.stdout)
        self.assertIn("command_chat_response_route_guidance_only_candidate", text_result.stdout)
        self.assertIn("does not promote command/chat response path", text_result.stdout)

    def test_inventory_custom_filter_boundary_guidance_can_be_listed_without_snapshots(self) -> None:
        result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "inventory-custom-filter-array-boundary",
            "--json",
        )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["schema"], "obelisk.reflection-target-guidance.v1")
        self.assertEqual(report["guidance_scope"], "offline_planning_only")
        self.assertEqual(report["target_sets"], ["inventory-custom-filter-array-boundary"])
        self.assertEqual(report["targets"], [])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], "inventory-custom-filter-array-boundary")
        self.assertEqual(guidance["classification"], "inventory_custom_filter_array_boundary_candidate")
        for reason in (
            "planning_guidance_only",
            "non_p0_side_lane",
            "candidate_only_array_boundary_metadata",
            "copied_array_payload_blocked",
            "public_inventory_items_sdk_blocked",
            "identity_lookup_resourcehandle_blocked",
            "v1_completion_blocked",
        ):
            self.assertIn(reason, guidance["why_blocked"])
        for required in (
            "compare only PrimalInventoryComponent.InventoryCustomFilter through --target-set inventory-custom-filter-array-boundary",
            "treat UnfilteredItemsList and FilteredItemsList as reflected TArray parameter-shell boundary metadata only",
            "keep TArray data pointer, count, capacity, element identity, object refs, raw arrays, raw params, AdditionalData, and UE pointers redacted or absent",
            "do not use this target set for P0, release/readiness, public SDK, runtime, or v1 completion gates",
        ):
            self.assertIn(required, guidance["snapshot_prep_checks"])
        self.assertIn("Inventory SDK", guidance["non_claim"])
        self.assertIn("copied array/list payloads", guidance["non_claim"])
        self.assertIn("v1 completion", guidance["non_claim"])

        text_result = run_compare_raw(
            "--list-target-guidance",
            "--target-set",
            "inventory-custom-filter-array-boundary",
        )
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        self.assertIn("target_guidance count=0 scope=offline_planning_only target_set_guidance=1", text_result.stdout)
        self.assertIn("target_set=inventory-custom-filter-array-boundary", text_result.stdout)
        self.assertIn("inventory_custom_filter_array_boundary_candidate", text_result.stdout)
        self.assertIn("does not promote P0 progress", text_result.stdout)

    def test_structure_aggregate_census_note_preserves_default_off_and_pin_exclusion(self) -> None:
        note = REPO_ROOT / "docs" / "research" / "2026-05-31-structure-aggregate-census-v0.md"
        text = note.read_text(encoding="utf-8")

        required_guardrails = [
            "planning-only",
            "default-off",
            "VerifyPinCode.ReturnValue",
            "No result or PIN-derived aggregate",
            "Output window contains only approved counters and capped histograms",
            "disabled gate, missing profile/window/marker, missing SHA, unsupported",
            "Do not use live roots, restarts, ptrace, gcore, markers, `/servidor/ark`",
        ]
        for guardrail in required_guardrails:
            with self.subTest(guardrail=guardrail):
                self.assertIn(guardrail, text)

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

    def test_rejects_snapshot_root_symlink_even_when_resolved_path_is_not_protected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_base = root / "real-base"
            candidate = root / "candidate"
            real_base.mkdir()
            candidate.mkdir()
            linked_base = root / "linked-base"
            linked_base.symlink_to(real_base, target_is_directory=True)

            result = run_compare(linked_base, candidate, "--readiness-report")

        self.assertEqual(result.returncode, 1)
        self.assertIn("--base-root must not be a symlink", result.stderr)

    def test_rejects_direct_snapshot_file_symlink_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_base = root / "real-base"
            candidate = root / "candidate"
            real_base.mkdir()
            candidate.mkdir()
            real_snapshot = write_snapshot(real_base, base_snapshot(), "real.snapshot.json")
            linked_snapshot = root / "linked.snapshot.json"
            linked_snapshot.symlink_to(real_snapshot)

            result = run_compare(linked_snapshot, candidate, "--readiness-report")

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("--base-root must not be a symlink", result.stderr)

    def test_rejects_direct_snapshot_file_symlink_swap_after_precheck(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            snapshot = write_snapshot(root, base_snapshot(), "swap.snapshot.json")
            linked_target = write_snapshot(root, base_snapshot(), "linked-target.snapshot.json")
            original_reject = compare.reject_snapshot_input_path
            swapped = False

            def race_reject_snapshot_input_path(label: str, path: Path) -> None:
                nonlocal swapped
                original_reject(label, path)
                if path == snapshot and not swapped:
                    swapped = True
                    snapshot.unlink()
                    snapshot.symlink_to(linked_target)

            with mock.patch.object(
                compare,
                "reject_snapshot_input_path",
                side_effect=race_reject_snapshot_input_path,
            ):
                with self.assertRaisesRegex(SystemExit, "snapshot must not be a symlink"):
                    compare.load_snapshot(snapshot)

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

    def test_rejects_snapshot_file_symlink_even_when_resolved_path_is_not_protected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            real_snapshot = write_snapshot(base, base_snapshot(), "real.snapshot.json")
            (base / "linked.snapshot.json").symlink_to(real_snapshot)

            result = run_compare(base, candidate, "--readiness-report")

        self.assertEqual(result.returncode, 1)
        self.assertIn("snapshot must not be a symlink", result.stderr)

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

    def test_public_runtime_resourcehandle_identity_and_mutation_claims_block_layout_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            right = deepcopy(left)
            for payload in (left, right):
                payload["public_sdk_ready"] = True
                payload["runtime_status"] = "runtime-ready"
                payload["targets"][0]["resource_handle_ready"] = "enabled"  # type: ignore[index]
                payload["targets"][0]["property_chain"]["properties"][0]["review_note"] = (  # type: ignore[index]
                    "ResourceHandle lookup is ready for object identity and mutation"
                )
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertTrue(any("readiness_alias_overclaim" in reason for reason in reasons), reasons)
        self.assertTrue(any("forbidden_positive_claim_value" in reason for reason in reasons), reasons)

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

    def test_readiness_report_blocks_missing_base_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base" / "sha" / "sdk_inventory"
            base.mkdir(parents=True)
            payload = base_snapshot()
            evidence = payload["evidence"]  # type: ignore[index]
            evidence.pop("artifact_kind", None)
            evidence.pop("artifact_sha256", None)
            evidence.pop("capture_id", None)
            evidence.pop("evidence_pack_id", None)
            write_snapshot(base, payload)

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target",
                "PrimalItem.CanUse",
                "--fail-on-base-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["totals"]["comparable"], 0)
        self.assertEqual(report["totals"]["blocked"], 1)
        detail = report["modules"][0]["target_details"][0]
        self.assertIn("missing_artifact_kind", detail["block_reasons"])
        self.assertIn("missing_artifact_sha256", detail["block_reasons"])
        self.assertIn("missing_capture_id", detail["block_reasons"])
        self.assertIn("missing_evidence_pack_id", detail["block_reasons"])

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

    def test_array_and_struct_properties_require_nested_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            left = base_snapshot()
            left["targets"][0]["property_chain"]["properties"][0]["class_name"] = "ArrayProperty"  # type: ignore[index]
            left["targets"][0]["property_chain"]["properties"][1]["class_name"] = "StructProperty"  # type: ignore[index]
            right = deepcopy(left)
            write_snapshot(base, left)
            write_snapshot(candidate, right)

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertEqual(report["counts"]["inconclusive"], 1)
        reasons = report["results"][0]["reasons"]
        self.assertIn("base:property[0]_array_inner_candidate_missing", reasons)
        self.assertIn("base:property[1]_struct_type_candidate_missing", reasons)
        self.assertIn("candidate:property[0]_array_inner_candidate_missing", reasons)
        self.assertIn("candidate:property[1]_struct_type_candidate_missing", reasons)

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

    def test_nested_property_candidate_requires_identity_fields(self) -> None:
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
                    "name": "InventoryItems",
                    "class_name": "ObjectProperty",
                },
            }
            left["targets"][0]["property_chain"]["properties"][1]["struct_type_candidate"] = {  # type: ignore[index]
                "status": "candidate",
                "reject_reasons": [],
                "membership_status": "candidate-uobject",
                "struct_type": {
                    "object_index": 2001,
                    "name": "ARKTributeDino",
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
        self.assertIn(
            "base:property[0]_array_inner_candidate_inner_property_object_index_missing",
            reasons,
        )
        self.assertIn(
            "base:property[0]_array_inner_candidate_inner_property_name_index_missing",
            reasons,
        )
        self.assertIn(
            "candidate:property[1]_struct_type_candidate_struct_type_class_name_missing",
            reasons,
        )
        self.assertIn(
            "candidate:property[1]_struct_type_candidate_struct_type_name_index_missing",
            reasons,
        )

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

    def test_snapshot_with_unknown_schema_fails_closed_before_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            base.mkdir()
            candidate.mkdir()
            payload = base_snapshot()
            payload["schema"] = "obelisk.unknown.snapshot.v1"
            write_snapshot(base, payload)
            write_snapshot(candidate, base_snapshot())

            result = run_compare(base, candidate, "--json")

        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported snapshot schema", result.stderr)

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
        self.assertIn("approved_runtime_evidence", report["does_not_satisfy_readiness"])
        self.assertIn("public_module_sdk", report["does_not_satisfy_readiness"])
        self.assertIn("resource_handle", report["does_not_satisfy_readiness"])
        self.assertIn("mutation", report["does_not_satisfy_readiness"])
        self.assertIn("return_override", report["does_not_satisfy_readiness"])
        self.assertIn("v1_completion", report["does_not_satisfy_readiness"])
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
        self.assertIn("public_sdk_ready=false runtime_ready=false", result.stdout)
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
        self.assertEqual(report["target_set_coverage"]["status"], "complete")
        self.assertTrue(report["target_set_coverage"]["complete"])
        self.assertEqual(report["target_set_coverage"]["missing_targets"], [])
        self.assertEqual(report["target_set_coverage"]["unexpected_targets"], [])
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
        coverage = report["target_set_coverage"]
        self.assertEqual(coverage["schema"], compare.READINESS_TARGET_SET_COVERAGE_SCHEMA)
        self.assertEqual(coverage["target_sets"], ["minimal-second-source-intake"])
        self.assertEqual(coverage["status"], "complete")
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["target_set_revision_schema"], "obelisk.reflection-target-set-revision.v1")
        self.assertEqual(coverage["target_set_revision_source"], "scripts/reflection_target_sets.py")
        self.assertRegex(coverage["target_set_revision_source_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(coverage["expected_targets"], sorted(compare.TARGET_SETS["minimal-second-source-intake"]))
        self.assertEqual(coverage["observed_targets"], sorted(compare.TARGET_SETS["minimal-second-source-intake"]))
        self.assertEqual(coverage["missing_targets"], [])
        self.assertEqual(coverage["unexpected_targets"], [])

    def test_planning_layout_intake_requires_readiness_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", "structure-aggregate-census-planning")

            result = run_compare(
                root / "base",
                None,
                "--target-set",
                "structure-aggregate-census-planning",
                "--planning-layout-intake",
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("--planning-layout-intake requires --readiness-report", result.stderr)

    def test_planning_layout_intake_rejects_promotion_gate_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", "structure-aggregate-census-planning")
            write_target_set_root(root / "candidate", "structure-aggregate-census-planning")

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                "structure-aggregate-census-planning",
                "--planning-layout-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(
            "--planning-layout-intake is incompatible with --fail-on-readiness-gaps",
            result.stderr,
        )

    def test_planning_layout_intake_accepts_only_planning_target_sets(self) -> None:
        rejected_sets = ("minimal-second-source-intake", "transfer-baccept-only-policy-slice")
        for target_set in rejected_sets:
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
                    "--planning-layout-intake",
                    "--json",
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("--planning-layout-intake only accepts planning-only target sets", result.stderr)

    def test_planning_layout_intake_emits_non_promotion_gate_for_planning_target_set(self) -> None:
        target_set = "structure-aggregate-census-planning"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], len(compare.TARGET_SETS[target_set]))
        self.assertEqual(report["totals"]["second_source_accepted"], len(compare.TARGET_SETS[target_set]))
        self.assertEqual(
            report["planning_layout_gate"],
            {
                "ready": True,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [],
            },
        )
        self.assertIs(report["promotion_gate"]["ready"], False)
        self.assertIs(report["promotion_gate"]["promotion_ready"], False)
        self.assertIn(
            {"reason": "planning_layout_intake_not_promotion_gate", "count": 1},
            report["promotion_gate"]["blockers"],
        )

    def test_planning_layout_intake_without_candidate_root_stays_not_second_source(self) -> None:
        target_set = "structure-aggregate-census-planning"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)

            result = run_compare(
                root / "base",
                None,
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["second_source_status"], "not_applicable_planning_layout_intake")
        self.assertEqual(report["planning_layout_comparison_status"], "missing_candidate_root")
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["second_source_readiness_satisfied"])
        self.assertTrue(report["not_second_source"])
        self.assertEqual(
            report["totals_scope"],
            "planning_layout_comparison_counts_not_second_source_readiness",
        )
        self.assertEqual(
            report["planning_layout_gate"]["blockers"],
            [{"reason": "missing_second_source", "count": len(compare.TARGET_SETS[target_set])}],
        )
        self.assertEqual(
            report["planning_layout_comparison_totals"],
            {
                "accepted": 0,
                "rejected": 0,
                "inconclusive": 0,
                "missing": len(compare.TARGET_SETS[target_set]),
            },
        )
        target_details = [
            detail
            for module in report["modules"]
            for detail in module["target_details"]
        ]
        self.assertEqual(
            {detail["planning_layout_comparison_status"] for detail in target_details},
            {"missing"},
        )
        self.assertEqual(
            {detail["second_source_status"] for detail in target_details},
            {"not_applicable_planning_layout_intake"},
        )

    def test_command_chat_response_planning_intake_emits_redaction_guidance(self) -> None:
        target_set = "command-chat-response-route-planning"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(len(report["target_set_guidance"]), 1)
        checks = report["target_set_guidance"][0]["snapshot_prep_checks"]
        for required in (
            "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
            "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
            "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
        ):
            self.assertIn(required, checks)

    def test_structure_build_policy_planning_intake_stays_non_public_non_runtime(self) -> None:
        target_set = "structure-build-policy-offline-intake"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], 3)
        self.assertEqual(report["totals"]["second_source_accepted"], 3)
        self.assertEqual(
            report["planning_layout_gate"],
            {
                "ready": True,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [],
            },
        )
        self.assertFalse(report["promotion_gate"]["ready"])
        self.assertFalse(report["promotion_gate"]["promotion_ready"])
        self.assertIn(
            {"reason": "planning_layout_intake_not_promotion_gate", "count": 1},
            report["promotion_gate"]["blockers"],
        )

    def test_planning_layout_intake_contract_does_not_change_second_source_promotion_gate(self) -> None:
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
        self.assertIs(report["promotion_gate"]["ready"], True)
        self.assertIs(report["promotion_gate"]["promotion_ready"], False)
        self.assertEqual(report["promotion_gate"]["blockers"], [])

    def test_readiness_report_blocks_overlapping_target_set_promotion_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for target_set in ("minimal-second-source-intake", "structure-observer-intake"):
                write_target_set_root(root / "base", target_set)
                write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                "minimal-second-source-intake",
                "--target-set",
                "structure-observer-intake",
                "--fail-on-readiness-gaps",
                "--json",
            )

        self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "second_source_promotion")
        self.assertEqual(report["totals"]["second_source_accepted"], 8)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "not_ready",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [
                    {
                        "reason": "ambiguous_target_set_coverage",
                        "count": 2,
                        "targets": [
                            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                            "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
                        ],
                    }
                ],
            },
        )
        ambiguity = report["target_set_coverage_ambiguity"]
        self.assertEqual(
            [item["target"] for item in ambiguity],
            [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
            ],
        )
        self.assertEqual(ambiguity[0]["module_lanes"], ["core_gameplay_policy", "structures"])

    def test_assemble_rc_root_rejects_partial_evidence_identity_before_gate_use(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            roots = {
                "minimal": root / "minimal",
                "structure": root / "structure",
                "chat": root / "chat",
            }
            write_target_set_root(roots["minimal"], "minimal-second-source-intake")
            write_target_set_root(roots["structure"], "structure-observer-intake")
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
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_readiness_report_blocks_lifecycle_anchor_candidate_promotion_gate(self) -> None:
        target_set = "players-lifecycle-anchor-candidates"
        with tempfile.TemporaryDirectory() as temp_dir:
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
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )
        self.assertEqual(len(report["target_set_guidance"]), 1)
        self.assertEqual(
            report["target_set_guidance"][0]["target_set"],
            "players-lifecycle-anchor-candidates",
        )
        self.assertIn("approved_runtime_evidence_missing", report["target_set_guidance"][0]["why_blocked"])

    def test_lifecycle_anchor_candidate_planning_intake_stays_non_promotional(self) -> None:
        target_set = "players-lifecycle-anchor-candidates"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )
            text_result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(text_result.returncode, 0, text_result.stderr + text_result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["evidence_scope"], "planning_layout_intake_only_not_second_source")
        self.assertEqual(report["readiness_effect"], "none")
        self.assertEqual(report["second_source_status"], "not_applicable_planning_layout_intake")
        self.assertFalse(report["second_source_layout_evidence"])
        self.assertFalse(report["can_be_used_as_second_source_layout_evidence"])
        self.assertTrue(report["not_second_source"])
        self.assertFalse(report["second_source_readiness_satisfied"])
        self.assertTrue(report["planning_only"])
        self.assertEqual(report["readiness_classification"], "planning_only")
        self.assertIn("second_source_layout_evidence", report["does_not_satisfy_readiness"])
        self.assertEqual(
            report["totals_scope"],
            "planning_layout_comparison_counts_not_second_source_readiness",
        )
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["targets"], 6)
        self.assertEqual(report["totals"]["second_source_accepted"], 6)
        self.assertEqual(
            report["planning_layout_comparison_totals"],
            {"accepted": 6, "rejected": 0, "inconclusive": 0, "missing": 0},
        )
        self.assertEqual(
            report["planning_layout_gate"],
            {
                "ready": True,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [],
            },
        )
        self.assertFalse(report["promotion_gate"]["ready"])
        self.assertFalse(report["promotion_gate"]["promotion_ready"])
        self.assertFalse(report["promotion_gate"]["public_sdk_ready"])
        self.assertFalse(report["promotion_gate"]["runtime_ready"])
        self.assertIn(
            {"reason": "planning_layout_intake_not_promotion_gate", "count": 1},
            report["promotion_gate"]["blockers"],
        )
        self.assertEqual(len(report["target_set_guidance"]), 1)
        self.assertIn("approved_runtime_evidence_missing", report["target_set_guidance"][0]["why_blocked"])
        self.assertEqual(
            {module["second_source_status"] for module in report["modules"]},
            {"not_applicable_planning_layout_intake"},
        )
        self.assertEqual(
            sum(module["planning_layout_comparison"]["accepted"] for module in report["modules"]),
            6,
        )
        target_details = [
            detail
            for module in report["modules"]
            for detail in module["target_details"]
        ]
        self.assertEqual(
            {detail["second_source_status"] for detail in target_details},
            {"not_applicable_planning_layout_intake"},
        )
        self.assertEqual(
            {detail["planning_layout_comparison_status"] for detail in target_details},
            {"accepted"},
        )
        self.assertIn(
            "second_source_status=not_applicable_planning_layout_intake planning_layout=accepted:6",
            text_result.stdout,
        )
        self.assertNotIn("second_source=accepted:6", text_result.stdout)

    def test_planning_layout_intake_accepts_planning_only_layout_without_promotion(self) -> None:
        target_set = "players-identity-lifecycle-intake"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_target_set_root(root / "base", target_set)
            write_target_set_root(root / "candidate", target_set)

            result = run_compare(
                root / "base",
                root / "candidate",
                "--readiness-report",
                "--target-set",
                target_set,
                "--planning-layout-intake",
                "--json",
            )

        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertEqual(report["gate_mode"], "planning_layout_intake")
        self.assertEqual(report["target_sets"], [target_set])
        self.assertEqual(report["totals"]["second_source_accepted"], len(compare.TARGET_SETS[target_set]))
        self.assertEqual(
            report["planning_layout_gate"],
            {
                "ready": True,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [],
            },
        )
        self.assertFalse(report["promotion_gate"]["ready"])
        self.assertFalse(report["promotion_gate"]["promotion_ready"])
        self.assertIn(
            {"reason": "planning_layout_intake_not_promotion_gate", "count": 1},
            report["promotion_gate"]["blockers"],
        )
        self.assertNotIn(
            {"reason": "not_second_source_promotion_gate", "count": 1},
            report["promotion_gate"]["blockers"],
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
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], target_set)
        self.assertEqual(guidance["classification"], "internal_mission_copied_bool_policy_candidate")
        self.assertIn("consume_mode_only", guidance["why_blocked"])
        self.assertIn("promote_mode_blocked", guidance["why_blocked"])
        self.assertIn("Mission SDK", guidance["non_claim"])
        self.assertIn("runtime hooks", guidance["non_claim"])
        self.assertEqual(report["totals"]["targets"], 3)
        self.assertEqual(report["totals"]["second_source_accepted"], 3)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_readiness_report_blocks_item_return_only_policy_slice_p0_completion_gate(self) -> None:
        target_set = "item-return-only-policy-slice"
        with tempfile.TemporaryDirectory() as temp_dir:
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
        self.assertEqual(report["totals"]["targets"], 3)
        self.assertEqual(report["totals"]["second_source_accepted"], 3)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["classification"], "internal_gameplay_policy_item_return_only_non_completion")
        self.assertIn("complete_sdk_accounting_blocked", guidance["why_blocked"])
        self.assertIn("p0_dependency_chain_accounting_blocked", guidance["why_blocked"])
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "planning_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [{"reason": "target_set_not_release_readiness", "count": 1}],
            },
        )

    def test_release_target_set_promotion_blocks_explicit_targets_outside_named_set(self) -> None:
        target_set = "minimal-second-source-intake"
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
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], target_set)
        self.assertEqual(guidance["classification"], "release_compact_inventory_structure_layout_evidence")
        self.assertIn("compact_layout_evidence_only", guidance["why_blocked"])
        self.assertIn("public_inventory_items_structure_sdks_blocked", guidance["why_blocked"])
        self.assertIn("narrower policy target sets", guidance["next_offline_input"])
        self.assertIn("Inventory SDK", guidance["non_claim"])
        self.assertIn("Items SDK", guidance["non_claim"])
        self.assertIn("runtime validation", guidance["non_claim"])
        self.assertEqual(report["totals"]["second_source_accepted"], 5)
        coverage = report["target_set_coverage"]
        self.assertEqual(coverage["status"], "incomplete")
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["missing_targets"], [])
        self.assertEqual(
            coverage["unexpected_targets"],
            ["obelisk.ufunction-chain.snapshot.v1:PrimalItem.CraftBlueprint"],
        )
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "not_ready",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
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
        self.assertEqual(len(report["target_set_guidance"]), 1)
        guidance = report["target_set_guidance"][0]
        self.assertEqual(guidance["target_set"], target_set)
        self.assertEqual(guidance["classification"], "internal_transfer_baccept_policy_candidate")
        self.assertIn("internal_layout_evidence_only", guidance["why_blocked"])
        self.assertIn("policy_slice_evidence_only", guidance["why_blocked"])
        self.assertIn("Transfer SDK", guidance["non_claim"])
        self.assertIn("runtime hooks", guidance["non_claim"])
        self.assertEqual(report["totals"]["targets"], 1)
        self.assertEqual(report["totals"]["second_source_accepted"], 1)
        self.assertEqual(
            report["promotion_gate"],
            {
                "ready": False,
                "ready_scope": "internal_layout_only",
                "layout_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
                        "public_sdk_ready": False,
                        "runtime_ready": False,
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
                "public_sdk_ready": False,
                "runtime_ready": False,
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
        fixture_roots = {
            "obelisk.ufunction-chain.snapshot.v1": REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            "obelisk.scriptstruct-chain.snapshot.v1": REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots",
        }
        known_missing_base_fixture_target_sets = {
            "structure-build-policy-offline-intake",
        }
        self.assertLessEqual(known_missing_base_fixture_target_sets, set(compare.TARGET_SETS))

        for target_set in sorted(set(compare.TARGET_SETS) - known_missing_base_fixture_target_sets):
            with self.subTest(target_set=target_set):
                targets = compare.TARGET_SETS[target_set]
                schemas = {target.partition(":")[0] for target in targets}
                self.assertEqual(1, len(schemas))
                schema = next(iter(schemas))
                base_root = fixture_roots[schema]
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
                expected_targets = len(targets)
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
