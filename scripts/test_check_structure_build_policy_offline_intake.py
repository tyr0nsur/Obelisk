#!/usr/bin/env python3
"""Tests for check_structure_build_policy_offline_intake.py."""

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
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_structure_build_policy_offline_intake.py"
TARGET_SET = "structure-build-policy-offline-intake"
ARK_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
SNAPSHOT_ADDRESS_POLICY = "absolute core paths and addresses omitted; use full inspector JSON for local evidence review"
BASE_IDENTITY = {
    "artifact_kind": "offline_core",
    "artifact_sha256": "1" * 64,
    "capture_id": "base-capture",
    "evidence_pack_id": "base-pack",
}
CANDIDATE_IDENTITY = {
    "artifact_kind": "offline_core",
    "artifact_sha256": "2" * 64,
    "capture_id": "candidate-capture",
    "evidence_pack_id": "candidate-pack",
}
NON_CLAIM = (
    "planning-layout evidence only; does not promote StructureEvents, Structure SDK, "
    "build-policy SDK, enforcement, identity, lookup, mutation, return override, "
    "runtime hooks, or v1 completion"
)
TARGET_SHAPES: dict[str, dict[str, Any]] = {
    "PrimalStructure.IsAllowedToBuild": {
        "function_flags": "0x4c20400",
        "num_parms": 8,
        "parms_size": 152,
        "properties": [
            ("PC", "ObjectProperty", 0, 8, None),
            ("AtLocation", "StructProperty", 8, 12, "Vector"),
            ("AtRotation", "StructProperty", 20, 12, "Rotator"),
            ("OutPlacementData", "StructProperty", 32, 96, "PlacementData"),
            ("bDontAdjustForMaxRange", "BoolProperty", 128, 1, None),
            ("PlayerViewRotation", "StructProperty", 132, 12, "Rotator"),
            ("bFinalPlacement", "BoolProperty", 144, 1, None),
            ("ReturnValue", "IntProperty", 148, 4, None),
        ],
    },
    "PrimalStructure.BPIsAllowedToBuild": {
        "function_flags": "0xc420c00",
        "num_parms": 3,
        "parms_size": 104,
        "properties": [
            ("OutPlacementData", "StructProperty", 0, 96, "PlacementData"),
            ("CurrentAllowedReason", "IntProperty", 96, 4, None),
            ("ReturnValue", "IntProperty", 100, 4, None),
        ],
    },
    "PrimalStructure.BPIsAllowedToBuildEx": {
        "function_flags": "0xc420c00",
        "num_parms": 6,
        "parms_size": 120,
        "properties": [
            ("OutPlacementData", "StructProperty", 0, 96, "PlacementData"),
            ("CurrentAllowedReason", "IntProperty", 96, 4, None),
            ("PC", "ObjectProperty", 104, 8, None),
            ("bFinalPlacement", "BoolProperty", 112, 1, None),
            ("bChoosingRotation", "BoolProperty", 113, 1, None),
            ("ReturnValue", "IntProperty", 116, 4, None),
        ],
    },
}


class CheckStructureBuildPolicyOfflineIntakeTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def readiness_payload(self) -> dict[str, Any]:
        return {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "evidence_scope": "second_source_layout_evidence_only",
            "gate_mode": "planning_layout_intake",
            "strict_identity_indices": False,
            "second_source_status": "compared",
            "not_promoted_surfaces": [
                "class_identity",
                "cross_binary_portability",
                "lookup",
                "mutation",
                "object_identity",
                "public_sdk",
                "raw_params",
                "resource_handle",
                "return_override",
                "runtime_hooks",
            ],
            "target_set_guidance": [],
            "target_sets": [TARGET_SET],
            "target_filters": [
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuild",
                "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.BPIsAllowedToBuildEx",
            ],
            "totals": {
                "targets": 3,
                "comparable": 3,
                "second_source_accepted": 3,
                "second_source_rejected": 0,
                "second_source_inconclusive": 0,
                "second_source_missing": 0,
                "blocked": 0,
            },
            "planning_layout_gate": {
                "ready": True,
                "layout_ready": True,
                "ready_scope": "planning_only",
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "blockers": [],
            },
            "promotion_gate": {
                "ready": False,
                "layout_ready": True,
                "promotion_ready": False,
                "ready_scope": "planning_only",
                "blockers": [{"reason": "planning_layout_intake_not_promotion_gate", "count": 1}],
            },
            "non_claims": [
                "accepted second-source readiness is layout evidence only",
                (
                    "does not promote public SDK, Mission SDK, Transfer SDK, Structure SDK, "
                    "StructureEvents, Inventory SDK, Items SDK, object identity, lookup, "
                    "mutation, return override, ResourceHandle, or runtime hooks"
                ),
            ],
        }

    def snapshot_payload(self, qualified_target: str, identity: dict[str, str] | None = None) -> dict[str, Any]:
        outer_name, function_name = qualified_target.split(".", 1)
        shape = TARGET_SHAPES[qualified_target]
        properties = []
        for depth, (name, class_name, offset, element_size, struct_type) in enumerate(shape["properties"]):
            prop: dict[str, Any] = {
                "array_dim": 1,
                "class_membership_status": "candidate-uobject",
                "class_name": class_name,
                "depth": depth,
                "element_size": element_size,
                "membership_status": "candidate-uobject",
                "name": name,
                "offset_internal": offset,
                "outer_membership_status": "candidate-uobject",
                "reject_reasons": [],
                "status": "candidate",
            }
            if class_name == "StructProperty":
                prop["struct_type_candidate"] = {
                    "membership_status": "candidate-uobject",
                    "reject_reasons": [],
                    "status": "candidate",
                    "struct_type": {"class_name": "ScriptStruct", "name": struct_type},
                }
            if class_name == "BoolProperty":
                prop.update(
                    {
                        "bool_byte_offset": 0,
                        "bool_field_size": 1,
                        "bool_property_semantics": {
                            "bool_byte_offset": 0,
                            "bool_field_size": 1,
                            "reject_reasons": [],
                            "status": "candidate",
                        },
                        "native_bool": False,
                    }
                )
            properties.append(prop)
        return {
            "address_policy": SNAPSHOT_ADDRESS_POLICY,
            "schema": "obelisk.ufunction-chain.snapshot.v1",
            "evidence": {
                **(identity if identity is not None else BASE_IDENTITY),
                "ark_binary_sha256": ARK_BINARY_SHA256,
                "generated_by": "scripts/inspect_core_ufunctions.py --snapshot-json",
                "source": "offline_core",
                "status": "candidate-only",
            },
            "interpretation": {"status": "candidate-only"},
            "targets": [
                {
                    "function_flags": shape["function_flags"],
                    "num_parms": shape["num_parms"],
                    "parms_size": shape["parms_size"],
                    "property_chain": {
                        "expected_count": len(properties),
                        "observed_count": len(properties),
                        "parms_size": shape["parms_size"],
                        "properties": properties,
                        "reject_reasons": [],
                        "status": "candidate",
                    },
                    "reject_reasons": [],
                    "status": "candidate",
                    "target": {
                        "class_name": "Function",
                        "name": function_name,
                        "outer_class_name": "Class",
                        "outer_name": outer_name,
                    },
                }
            ],
        }

    def add_snapshot_details(self, root: Path, readiness_payload: dict[str, Any]) -> None:
        if "modules" in readiness_payload:
            return
        base_root = root / "base"
        candidate_root = root / "candidate"
        base_root.mkdir()
        candidate_root.mkdir()
        details = []
        for qualified_target in TARGET_SHAPES:
            snapshot_path = base_root / f"{qualified_target}.snapshot.json"
            candidate_path = candidate_root / f"{qualified_target}.snapshot.json"
            snapshot_path.write_text(
                json.dumps(self.snapshot_payload(qualified_target, BASE_IDENTITY), sort_keys=True),
                encoding="utf-8",
            )
            candidate_path.write_text(
                json.dumps(self.snapshot_payload(qualified_target, CANDIDATE_IDENTITY), sort_keys=True),
                encoding="utf-8",
            )
            details.append(
                {
                    "block_reasons": [],
                    "comparable": True,
                    "path": str(snapshot_path),
                    "second_source_status": "accepted",
                    "target": f"obelisk.ufunction-chain.snapshot.v1:{qualified_target}",
                }
            )
        readiness_payload["modules"] = [
            {
                "block_reasons": {},
                "blocked": 0,
                "comparable": 3,
                "module": "base",
                "schema": "ufunction",
                "second_source": {"accepted": 3, "inconclusive": 0, "missing": 0, "rejected": 0},
                "target_details": details,
                "targets": 3,
            }
        ]

    def manifest_payload(self, readiness: Path, sha256: str) -> dict[str, Any]:
        return {
            "promoted_surfaces": [
                "obelisk.lifecycle_config_logging.v1",
                "obelisk.descriptors.v1",
                "obelisk.process_local_timers.v1",
            ],
            "planning_surfaces": [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
                "obelisk.structure_census.v1",
                "obelisk.mission_transfer_dino_tribe.v1",
            ],
            "surfaces": [
                {
                    "id": "obelisk.structure_census.v1",
                    "category": "structure observer and build policy",
                    "status": "planning",
                    "support_tier": "blocked",
                    "public_contract": [],
                    "evidence": {
                        "offline_readiness_reports": [
                            {
                                "target_set": TARGET_SET,
                                "schema": "obelisk.reflection-snapshot-readiness.v1",
                                "path": str(readiness),
                                "sha256": sha256,
                                "status": "planning-layout-second-source-accepted",
                                "totals": {
                                    "targets": 3,
                                    "comparable": 3,
                                    "second_source_accepted": 3,
                                    "blocked": 0,
                                },
                                "readiness_flags": {
                                    "promotion_ready": False,
                                    "public_sdk_ready": False,
                                    "runtime_ready": False,
                                },
                                "non_claim": NON_CLAIM,
                            }
                        ]
                    },
                    "build_policy_offline_intake_candidate": {
                        "status": "candidate-only",
                        "scope": "offline structure build-policy planning-layout audit only",
                        "target_set": TARGET_SET,
                        "target_count": 3,
                        "target_names_redacted": True,
                        "public_sdk_ready": False,
                        "promotion_ready": False,
                        "runtime_ready": False,
                        "enforcement_ready": False,
                        "must_remain_planning_only": True,
                        "required_boundaries": [
                            "candidate-only",
                            "sanitized UFunction layout comparison only",
                            "no public StructureEvents SDK",
                            "no build-policy SDK or enforcement",
                            "no structure identity or lookup",
                            "no mutation or return override",
                            "public_sdk_ready=false",
                        ],
                    },
                    "v1_decision_contract": {
                        "must_remain_without_public_contract_until_promotion": True,
                    },
                }
            ]
        }

    def write_case(self, root: Path, readiness_payload: dict[str, Any], manifest_payload: dict[str, Any] | None = None) -> tuple[Path, Path]:
        self.add_snapshot_details(root, readiness_payload)
        readiness = root / "readiness.json"
        readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
        sha256 = hashlib.sha256(readiness.read_bytes()).hexdigest()
        manifest = root / "public_sdk_surfaces.json"
        payload = manifest_payload if manifest_payload is not None else self.manifest_payload(readiness, sha256)
        manifest.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return manifest, readiness

    def test_accepts_planning_only_report_without_public_runtime_or_enforcement_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest, _ = self.write_case(Path(temp_dir), self.readiness_payload())
            result = self.run_checker("--manifest", str(manifest), "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.structure-build-policy-offline-intake-check.v1")
        self.assertEqual(payload["status"], "accepted_planning_only")
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_offline_planning"])
        self.assertTrue(payload["planning_only"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])
        self.assertEqual(payload["readiness_flags"]["enforcement_ready"], False)
        self.assertEqual(payload["non_claim_matrix"]["build_policy_sdk"], "not_claimed")
        self.assertEqual(payload["non_claim_matrix"]["enforcement"], "not_claimed")
        self.assertEqual(payload["non_claim_matrix"]["runtime_hooks"], "not_claimed")
        self.assertEqual(payload["blockers"], [])

    def test_manifest_surface_posture_overclaims_fail_closed(self) -> None:
        cases = [
            (
                "promoted_surfaces",
                lambda payload: payload["promoted_surfaces"].append("obelisk.structure_census.v1"),
                "structure_surface_in_promoted_surfaces",
            ),
            (
                "planning_surfaces",
                lambda payload: payload["planning_surfaces"].remove("obelisk.structure_census.v1"),
                "structure_surface_missing_from_planning_surfaces",
            ),
            (
                "status",
                lambda payload: payload["surfaces"][0].__setitem__("status", "promoted"),
                "surface_status_mismatch",
            ),
            (
                "support_tier",
                lambda payload: payload["surfaces"][0].__setitem__("support_tier", "release-supported foundation"),
                "surface_support_tier_mismatch",
            ),
            (
                "public_contract",
                lambda payload: payload["surfaces"][0].__setitem__(
                    "public_contract", ["ObeliskApi.RegisterStructureCensusCallback"]
                ),
                "surface_public_contract_not_empty",
            ),
            (
                "public_abi",
                lambda payload: payload["surfaces"][0].__setitem__("public_abi", "RegisterStructureCensusCallback"),
                "surface_public_abi_not_false",
            ),
            (
                "abi_contract",
                lambda payload: payload["surfaces"][0].__setitem__(
                    "abi_contract", ["append_only_abi"]
                ),
                "surface_abi_contract_not_empty",
            ),
        ]
        for key, mutate, blocker in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    readiness_payload = self.readiness_payload()
                    readiness = root / "readiness.json"
                    readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
                    manifest_payload = self.manifest_payload(
                        readiness,
                        hashlib.sha256(readiness.read_bytes()).hexdigest(),
                    )
                    mutate(manifest_payload)
                    manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                self.assertIn(blocker, {item["reason"] for item in payload["blockers"]})
                self.assertFalse(payload["promotion_ready"])
                self.assertFalse(payload["public_sdk_ready"])
                self.assertFalse(payload["runtime_ready"])
                self.assertFalse(payload["enforcement_ready"])

    def test_manifest_target_status_totals_flags_and_non_claim_drift_fail_closed(self) -> None:
        cases = [
            ("target_set", "wrong-target", "manifest_report_target_set_mismatch"),
            ("status", "public-ready", "manifest_report_status_mismatch"),
            ("totals", {"targets": 4, "comparable": 3, "second_source_accepted": 3, "blocked": 0}, "manifest_report_totals_mismatch"),
            (
                "readiness_flags",
                {"promotion_ready": False, "public_sdk_ready": True, "runtime_ready": False},
                "manifest_report_readiness_flags_mismatch",
            ),
            (
                "non_claim",
                "planning-layout evidence only; does not promote StructureEvents",
                "manifest_report_non_claim_mismatch",
            ),
        ]
        for key, value, blocker in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    readiness_payload = self.readiness_payload()
                    readiness = root / "readiness.json"
                    readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
                    manifest_payload = self.manifest_payload(
                        readiness,
                        hashlib.sha256(readiness.read_bytes()).hexdigest(),
                    )
                    report = manifest_payload["surfaces"][0]["evidence"]["offline_readiness_reports"][0]
                    report[key] = value
                    manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                self.assertIn(blocker, {item["reason"] for item in payload["blockers"]})
                self.assertFalse(payload["public_sdk_ready"])
                self.assertFalse(payload["runtime_ready"])
                self.assertFalse(payload["enforcement_ready"])

    def test_readiness_payload_drift_fails_closed(self) -> None:
        cases = [
            ("target_sets", ["structure-build-policy-public"], "readiness_target_sets_mismatch"),
            ("totals", {"targets": 3, "comparable": 3, "second_source_accepted": 2, "blocked": 0}, "readiness_total_mismatch"),
            ("planning_layout_gate.public_sdk_ready", True, "planning_layout_gate_public_sdk_ready_mismatch"),
            ("promotion_gate.ready", True, "promotion_gate_ready_mismatch"),
        ]
        for dotted_key, value, blocker in cases:
            with self.subTest(key=dotted_key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_payload = self.readiness_payload()
                    target = readiness_payload
                    parts = dotted_key.split(".")
                    for part in parts[:-1]:
                        target = target[part]
                    target[parts[-1]] = value
                    manifest, _ = self.write_case(Path(temp_dir), readiness_payload)
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                self.assertIn(blocker, {item["reason"] for item in payload["blockers"]})
                self.assertFalse(payload["promotion_ready"])
                self.assertFalse(payload["public_sdk_ready"])
                self.assertFalse(payload["runtime_ready"])
                self.assertFalse(payload["enforcement_ready"])

    def test_unknown_nested_readiness_gate_overclaim_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_payload = self.readiness_payload()
            readiness_payload["public_sdk_gate"] = {"ready": True}
            manifest, _ = self.write_case(Path(temp_dir), readiness_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("forbidden_readiness_true", {item["reason"] for item in payload["blockers"]})
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_manifest_extra_promotion_alias_overclaim_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            readiness = root / "readiness.json"
            readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
            manifest_payload = self.manifest_payload(
                readiness,
                hashlib.sha256(readiness.read_bytes()).hexdigest(),
            )
            candidate = manifest_payload["surfaces"][0]["build_policy_offline_intake_candidate"]
            candidate["ready_for_promotion"] = True
            candidate["sdk_ready"] = True
            manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        blockers = {item["path"] for item in payload["blockers"] if item["reason"] == "forbidden_readiness_true"}
        self.assertTrue(any(path.endswith(".ready_for_promotion") for path in blockers))
        self.assertTrue(any(path.endswith(".sdk_ready") for path in blockers))
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_generic_boolean_alias_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            readiness_payload = self.readiness_payload()
            readiness_payload["public_abi_ready"] = True
            readiness_payload["structure_events_ready"] = True
            manifest, _ = self.write_case(Path(temp_dir), readiness_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        blockers = {item["path"] for item in payload["blockers"] if item["reason"] == "forbidden_readiness_true"}
        self.assertTrue(any(path.endswith(".public_abi_ready") for path in blockers))
        self.assertTrue(any(path.endswith(".structure_events_ready") for path in blockers))
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_string_status_alias_overclaims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            readiness_payload["sdk_status"] = "ready"
            readiness_payload["promotion_status"] = "promoted"
            readiness_payload["public_sdk_status"] = "accepted"
            readiness_payload["negative_note"] = "does not promote Structure SDK readiness"
            readiness_payload["boundary"] = "public_sdk_ready=false"
            readiness = root / "readiness.json"
            readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
            manifest_payload = self.manifest_payload(
                readiness,
                hashlib.sha256(readiness.read_bytes()).hexdigest(),
            )
            candidate = manifest_payload["surfaces"][0]["build_policy_offline_intake_candidate"]
            candidate["status"] = "public-ready"
            candidate["notes"] = "Structure SDK ready"
            manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        blockers = [item for item in payload["blockers"] if item["reason"] == "forbidden_string_claim"]
        paths = {item["path"] for item in blockers}
        self.assertTrue(any(path.endswith(".sdk_status") for path in paths))
        self.assertTrue(any(path.endswith(".promotion_status") for path in paths))
        self.assertTrue(any(path.endswith(".public_sdk_status") for path in paths))
        self.assertTrue(any(path.endswith(".status") for path in paths))
        self.assertTrue(any(path.endswith(".notes") for path in paths))
        self.assertFalse(any(path.endswith(".negative_note") for path in paths))
        self.assertFalse(any(path.endswith(".boundary") for path in paths))
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_snapshot_field_shape_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.BPIsAllowedToBuildEx.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["targets"][0]["property_chain"]["properties"][5]["class_name"] = "BoolProperty"
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_property_shape_mismatch", {item["reason"] for item in payload["blockers"]})
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_snapshot_public_payload_claim_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["targets"][0]["property_chain"]["properties"][3]["exposes_public_payload"] = True
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("forbidden_true_claim", {item["reason"] for item in payload["blockers"]})
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["enforcement_ready"])

    def test_readiness_missing_snapshot_detail_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            readiness_payload["modules"] = [
                {
                    "target_details": [
                        {
                            "block_reasons": [],
                            "comparable": True,
                            "path": str(root / "missing.snapshot.json"),
                            "second_source_status": "accepted",
                            "target": "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
                        }
                    ]
                }
            ]
            manifest, _ = self.write_case(root, readiness_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("readiness_target_details_mismatch", {item["reason"] for item in payload["blockers"]})

    def test_manifest_public_payload_claim_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            self.add_snapshot_details(root, readiness_payload)
            readiness = root / "readiness.json"
            readiness.write_text(json.dumps(readiness_payload, sort_keys=True), encoding="utf-8")
            manifest_payload = self.manifest_payload(
                readiness,
                hashlib.sha256(readiness.read_bytes()).hexdigest(),
            )
            manifest_payload["surfaces"][0]["build_policy_offline_intake_candidate"]["public_payload"] = True
            manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        blockers = {item["path"] for item in payload["blockers"] if item["reason"] == "forbidden_true_claim"}
        self.assertTrue(any(path.endswith(".public_payload") for path in blockers))

    def test_runtime_input_keys_fail_closed_even_when_not_ready_claims(self) -> None:
        cases = [
            ("readiness", "runtime_name_indices", {"PrimalStructure": 123}),
            ("readiness", "fname_indices", [123, 456]),
            ("manifest", "dispatch_budget", 1),
            ("manifest", "observation_budget", 1),
            ("snapshot", "hook_enabled", False),
            ("snapshot", "copied_payload", {"ReturnValue": 1}),
            ("snapshot", "return_override", "not_claimed"),
            ("snapshot", "runtimeNameIndices", {"PrimalStructure": 123}),
            ("manifest", "dispatch-budget", 1),
            ("readiness", "observation budget", 1),
        ]
        for location, key, value in cases:
            with self.subTest(location=location, key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    readiness_payload = self.readiness_payload()
                    manifest, _ = self.write_case(root, readiness_payload)
                    if location == "readiness":
                        readiness_payload[key] = value
                        manifest, _ = self.write_case(root, readiness_payload)
                    elif location == "manifest":
                        readiness = root / "readiness.json"
                        manifest_payload = self.manifest_payload(
                            readiness,
                            hashlib.sha256(readiness.read_bytes()).hexdigest(),
                        )
                        manifest_payload["surfaces"][0]["build_policy_offline_intake_candidate"][key] = value
                        manifest, _ = self.write_case(root, readiness_payload, manifest_payload)
                    else:
                        snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
                        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                        snapshot["targets"][0][key] = value
                        snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                blockers = {item["key"] for item in payload["blockers"] if item["reason"] == "forbidden_runtime_input_key"}
                self.assertIn(key, blockers)
                self.assertFalse(payload["promotion_ready"])
                self.assertFalse(payload["public_sdk_ready"])
                self.assertFalse(payload["runtime_ready"])
                self.assertFalse(payload["enforcement_ready"])

    def test_readiness_envelope_drift_fails_closed(self) -> None:
        cases = [
            ("evidence_scope", "runtime_evidence", "readiness_evidence_scope_mismatch"),
            ("strict_identity_indices", True, "readiness_strict_identity_indices_mismatch"),
            ("target_set_guidance", [{"promote": "now"}], "readiness_target_set_guidance_mismatch"),
            (
                "not_promoted_surfaces",
                ["public_sdk", "runtime_hooks"],
                "readiness_not_promoted_surfaces_missing_values",
            ),
        ]
        for key, value, blocker in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    readiness_payload = self.readiness_payload()
                    readiness_payload[key] = value
                    manifest, _ = self.write_case(Path(temp_dir), readiness_payload)
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                self.assertIn(blocker, {item["reason"] for item in payload["blockers"]})

    def test_snapshot_path_must_be_base_sibling_of_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            self.add_snapshot_details(root, readiness_payload)
            detail = readiness_payload["modules"][0]["target_details"][0]
            wrong_dir = root / "other"
            wrong_dir.mkdir()
            wrong_path = wrong_dir / Path(detail["path"]).name
            wrong_path.write_text(Path(detail["path"]).read_text(encoding="utf-8"), encoding="utf-8")
            detail["path"] = str(wrong_path)
            manifest, _ = self.write_case(root, readiness_payload)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("readiness_target_detail_path_mismatch", {item["reason"] for item in payload["blockers"]})

    def test_missing_candidate_snapshot_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            (root / "candidate" / "PrimalStructure.IsAllowedToBuild.snapshot.json").unlink()
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_unreadable", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_identity_must_be_complete_and_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            candidate_path = root / "candidate" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate["evidence"].update(BASE_IDENTITY)
            candidate_path.write_text(json.dumps(candidate, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        reasons = {item["reason"] for item in payload["blockers"]}
        self.assertIn("snapshot_same_evidence_artifact_identity", reasons)
        self.assertIn("snapshot_same_evidence_artifact_sha256", reasons)
        self.assertIn("snapshot_same_evidence_capture_id", reasons)
        self.assertIn("snapshot_same_evidence_evidence_pack_id", reasons)

    def test_snapshot_missing_identity_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.BPIsAllowedToBuild.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            del snapshot["evidence"]["capture_id"]
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_artifact_identity_invalid", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_raw_address_redaction_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["targets"][0]["property_chain"]["properties"][0]["debug_address"] = "0x123456789abcdef0"
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_raw_sanitization_mismatch", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_short_ark_address_redaction_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["targets"][0]["property_chain"]["properties"][0]["native_func"] = "0x1d34e20"
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_raw_sanitization_mismatch", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_redacted_field_exposure_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["targets"][0]["property_chain"]["properties"][1]["exposes_range"] = True
            snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_redacted_field_exposes_range", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_redacted_field_value_bearing_keys_fail_closed(self) -> None:
        cases = [
            ("PrimalStructure.IsAllowedToBuild.snapshot.json", 3, "public_payload", {"x": 1}),
            ("PrimalStructure.BPIsAllowedToBuild.snapshot.json", 1, "range", [96, 100]),
            ("PrimalStructure.BPIsAllowedToBuildEx.snapshot.json", 5, "value", 1),
        ]
        for filename, property_index, key, value in cases:
            with self.subTest(key=key):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    readiness_payload = self.readiness_payload()
                    manifest, _ = self.write_case(root, readiness_payload)
                    snapshot_path = root / "base" / filename
                    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
                    snapshot["targets"][0]["property_chain"]["properties"][property_index][key] = value
                    snapshot_path.write_text(json.dumps(snapshot, sort_keys=True), encoding="utf-8")
                    result = self.run_checker("--manifest", str(manifest), "--json", check=False)

                payload = json.loads(result.stdout)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(payload["ready"])
                self.assertIn("snapshot_field_value_bearing_key", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_base_directory_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            real_base = root / "real-base"
            (root / "base").rename(real_base)
            (root / "base").symlink_to(real_base, target_is_directory=True)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_path_rejected", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_candidate_directory_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            real_candidate = root / "real-candidate"
            (root / "candidate").rename(real_candidate)
            (root / "candidate").symlink_to(real_candidate, target_is_directory=True)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_path_rejected", {item["reason"] for item in payload["blockers"]})

    def test_snapshot_file_symlink_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            readiness_payload = self.readiness_payload()
            manifest, _ = self.write_case(root, readiness_payload)
            snapshot_path = root / "base" / "PrimalStructure.IsAllowedToBuild.snapshot.json"
            real_snapshot = root / "base" / "real.snapshot.json"
            snapshot_path.rename(real_snapshot)
            snapshot_path.symlink_to(real_snapshot)
            result = self.run_checker("--manifest", str(manifest), "--json", check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("snapshot_path_rejected", {item["reason"] for item in payload["blockers"]})

    def test_protected_manifest_path_fails_closed_before_reading(self) -> None:
        result = self.run_checker(
            "--manifest",
            "/servidor/ark/obelisk/structure-build-policy/public_sdk_surfaces.json",
            "--json",
            check=False,
        )

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIn("manifest_path_rejected", {item["reason"] for item in payload["blockers"]})


if __name__ == "__main__":
    unittest.main()
