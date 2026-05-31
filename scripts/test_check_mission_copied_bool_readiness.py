#!/usr/bin/env python3
"""Tests for check_mission_copied_bool_readiness.py."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_mission_copied_bool_readiness.py"


class CheckMissionCopiedBoolReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def make_policy(self) -> dict:
        def copied(target: str, field: str, direction: str) -> dict:
            return {
                "array_dim": 1,
                "bool_byte_offset": 0,
                "bool_field_size": 1,
                "byte_mask": "0x01",
                "copied_field": f"{target}.{field}",
                "direction": direction,
                "element_size": 1,
                "evidence_status": "copied-mission-bool-only",
                "field": field,
                "field_mask": "0xff",
                "native_bool": False,
                "property_class": "BoolProperty",
                "target": target,
                "type": "bool",
            }

        return {
            "schema": "obelisk.mission-copied-bool-policy-slice.v1",
            "input_target_set": "mission-compact-intake",
            "output_target_set": "mission-copied-bool-policy-slice",
            "policy_status": "evidence-only",
            "coverage": {
                "status": "complete",
                "input_targets": [
                    "MissionType.AddPlayerToMission",
                    "MissionType.BPAllowPlayerToLeaveMission",
                    "MissionType.BPOnPlayerRemovedFromMission",
                    "MissionType.GetPlayerUsableItems",
                ],
                "copied_targets": [
                    "MissionType.AddPlayerToMission",
                    "MissionType.BPAllowPlayerToLeaveMission",
                    "MissionType.BPOnPlayerRemovedFromMission",
                ],
                "copied_fields": [
                    "MissionType.AddPlayerToMission.bForceAdd",
                    "MissionType.AddPlayerToMission.ReturnValue",
                    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
                    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
                    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
                ],
                "redacted_fields": [
                    "MissionType.AddPlayerToMission.PlayerCharacter",
                    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
                    "MissionType.BPOnPlayerRemovedFromMission.Player",
                    "MissionType.BPOnPlayerRemovedFromMission.Controller",
                    "MissionType.GetPlayerUsableItems.Character",
                    "MissionType.GetPlayerUsableItems.OutItemIDs",
                ],
            },
            "copied_bools": [
                copied("MissionType.AddPlayerToMission", "bForceAdd", "in"),
                copied("MissionType.AddPlayerToMission", "ReturnValue", "return"),
                copied("MissionType.BPAllowPlayerToLeaveMission", "ReturnValue", "return"),
                copied("MissionType.BPOnPlayerRemovedFromMission", "bFromMissionCompleteEvent", "in"),
                copied("MissionType.BPOnPlayerRemovedFromMission", "bLastPhaseSuccess", "in"),
            ],
            "generated_from": {
                "snapshot_schema": "obelisk.ufunction-chain.snapshot.v1",
                "input_snapshots": [
                    {"id": "snapshot-0001", "target": "MissionType.AddPlayerToMission"},
                    {"id": "snapshot-0002", "target": "MissionType.BPAllowPlayerToLeaveMission"},
                    {"id": "snapshot-0003", "target": "MissionType.BPOnPlayerRemovedFromMission"},
                    {"id": "snapshot-0004", "target": "MissionType.GetPlayerUsableItems"},
                ],
            },
            "safety_summary": {
                "artifact_status": "evidence_only",
                "consume_only": True,
                "promotion_ready": False,
                "intended_use": "offline_review_only",
            },
            "non_claims": [
                "does not expose UE pointers, object identity, class identity, raw params, mutation, or return overrides",
                "does not promote public SDK callbacks or public metadata helpers",
                "does not promote runtime hook wiring, dispatcher wiring, mission payload decoding, or public Mission SDK",
                "does not copy player/controller/character object refs, OutItemIDs arrays, mission identity, player identity, or ResourceHandle",
            ],
        }

    def write_pack(self, root: Path, payload: dict | None = None) -> tuple[Path, str]:
        root.mkdir(parents=True, exist_ok=True)
        manifest = root / "mission-copied-bool-policy-slice.json"
        content = json.dumps(payload if payload is not None else self.make_policy(), sort_keys=True).encode("utf-8")
        manifest.write_bytes(content)
        return manifest, hashlib.sha256(content).hexdigest()

    def checker_args(self, root: Path, manifest: Path, sha256: str) -> list[str]:
        return [
            "--root",
            str(root),
            "--manifest",
            str(manifest),
            "--expected-manifest-sha256",
            sha256,
            "--skip-artifact-gates",
        ]

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            result = self.run_checker(*self.checker_args(root, manifest, sha256), "--json")
            payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.mission-copied-bool-readiness-check.v1")
        self.assertEqual(payload["status"], "candidate_ready")
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertEqual(payload["consume_gate"]["status"], "skipped")
        self.assertEqual(payload["promote_gate"]["status"], "skipped")
        self.assertEqual(len(payload["summary"]["input_targets"]), 4)
        self.assertEqual(len(payload["summary"]["copied_targets"]), 3)
        self.assertEqual(len(payload["summary"]["copied_fields"]), 5)
        self.assertEqual(len(payload["summary"]["redacted_fields"]), 6)
        self.assertEqual(payload["summary"]["copied_bool_count"], 5)
        self.assertIn("candidate readiness is internal planning evidence only", " ".join(payload["non_claims"]))

    def test_get_player_usable_items_copied_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["coverage"]["copied_targets"].append("MissionType.GetPlayerUsableItems")
            payload["coverage"]["copied_fields"].append("MissionType.GetPlayerUsableItems.OutItemIDs")
            payload["copied_bools"].append(
                {
                    **payload["copied_bools"][0],
                    "target": "MissionType.GetPlayerUsableItems",
                    "copied_field": "MissionType.GetPlayerUsableItems.OutItemIDs",
                    "field": "OutItemIDs",
                }
            )
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_target_coverage_mismatch", reasons)
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)
        self.assertIn("get_player_usable_items_copied_target_not_allowed", reasons)
        self.assertIn("get_player_usable_items_copied_field_not_allowed", reasons)

    def test_noncanonical_bool_tail_metadata_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["copied_bools"][0]["native_bool"] = True
            payload["copied_bools"][0]["byte_mask"] = "0xff"
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_bool_entry_metadata_mismatch", reasons)

    def test_promote_gate_must_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            payload = self.make_policy()
            payload["non_claims"] = []
            manifest, sha256 = self.write_pack(root, payload)

            result = self.run_checker(*self.checker_args(root, manifest, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("required_non_claim_missing", reasons)
        self.assertIn("required_non_claim_missing", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/mission",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/mission/manifest.json",
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest, sha256 = self.write_pack(root)
            link = Path(temp_dir) / "manifest-link.json"
            link.symlink_to(manifest)
            result = self.run_checker(*self.checker_args(root, link, sha256), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
