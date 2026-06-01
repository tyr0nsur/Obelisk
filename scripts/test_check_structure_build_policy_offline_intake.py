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
NON_CLAIM = (
    "planning-layout evidence only; does not promote StructureEvents, Structure SDK, "
    "build-policy SDK, enforcement, identity, lookup, mutation, return override, "
    "runtime hooks, or v1 completion"
)


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
            "gate_mode": "planning_layout_intake",
            "second_source_status": "compared",
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

    def manifest_payload(self, readiness: Path, sha256: str) -> dict[str, Any]:
        return {
            "surfaces": [
                {
                    "id": "obelisk.structure_census.v1",
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


if __name__ == "__main__":
    unittest.main()
