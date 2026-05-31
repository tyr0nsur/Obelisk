#!/usr/bin/env python3
"""Tests for check_structure_census_readiness.py."""

from __future__ import annotations

import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_structure_census_readiness.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
DEFAULT_ROOT = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/structure-aggregate-census-policy-slice-20260531T034715Z"
)
DEFAULT_MANIFEST = DEFAULT_ROOT / "structure-aggregate-census-policy-slice.json"

SPEC = importlib.util.spec_from_file_location("check_structure_census_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


class CheckStructureCensusReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_pack(self, root: Path) -> Path:
        shutil.copytree(DEFAULT_ROOT, root, dirs_exist_ok=True)
        return root / "structure-aggregate-census-policy-slice.json"

    def test_default_pack_is_candidate_ready_but_not_public_or_runtime_ready(self) -> None:
        result = self.run_checker("--json")
        payload = json.loads(result.stdout)

        self.assertEqual(payload["schema"], "obelisk.structure-census-readiness-check.v1")
        self.assertEqual(payload["status"], "candidate_ready")
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["enforcement_ready"])
        self.assertTrue(payload["offline_only"])
        self.assertEqual(payload["consume_gate"]["status"], "accepted")
        self.assertEqual(payload["promote_gate"]["status"], "blocked")
        self.assertEqual(payload["source_isolation"]["status"], "isolated")
        self.assertEqual(payload["target_readiness"]["status"], "second-source-missing")
        self.assertEqual(payload["target_readiness"]["status_counts"], {"second-source-missing": 6})
        self.assertEqual(
            payload["target_readiness"]["allowed_statuses"],
            ["candidate", "fixture-backed", "second-source-missing", "blocked"],
        )
        self.assertEqual(payload["target_readiness"]["second_source"]["status"], "missing")
        for target in payload["target_readiness"]["targets"]:
            self.assertEqual(target["status"], "second-source-missing")
            self.assertTrue(target["candidate"])
            self.assertEqual(target["candidate_status"], "candidate")
            self.assertTrue(target["fixture_backed"])
            self.assertEqual(target["fixture_status"], "fixture-backed")
            self.assertFalse(target["second_source_backed"])
            self.assertEqual(target["second_source_status"], "second-source-missing")
            self.assertEqual(target["blockers"], [])
        self.assertEqual(
            set(payload["promote_gate"]["blocker_reasons"]),
            {
                "promote_mode_manifest_has_non_claims",
                "promote_mode_structure_aggregate_census_policy_slice_consume_only",
            },
        )
        self.assertEqual(len(payload["summary"]["input_targets"]), 6)
        self.assertEqual(len(payload["summary"]["copied_fields"]), 8)
        self.assertEqual(len(payload["summary"]["redacted_fields"]), 5)
        self.assertEqual(len(payload["summary"]["explicitly_excluded_fields"]), 2)
        self.assertIn("candidate readiness is internal planning evidence only", " ".join(payload["non_claims"]))
        self.assertIn("no public StructureEvents", payload["non_claims"])
        self.assertIn("no identity/lookup", payload["non_claims"])
        self.assertIn("no mutation", payload["non_claims"])
        self.assertIn("no return override", payload["non_claims"])
        self.assertIn("no enforcement", payload["non_claims"])
        self.assertEqual(payload["non_claim_matrix"]["public_structure_events"], "not_claimed")
        self.assertEqual(payload["non_claim_matrix"]["identity_lookup"], "not_claimed")
        self.assertEqual(payload["non_claim_matrix"]["enforcement"], "not_claimed")

    def test_source_isolation_blocks_runtime_or_public_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            blocked = root / "hooks" / "ProcessEventHook.cpp"
            blocked.parent.mkdir(parents=True)
            blocked.write_text('#include "core/StructureAggregateCensus.h"\n', encoding="utf-8")
            allowed = root / "core" / "StructureAggregateCensus.cpp"
            allowed.parent.mkdir(parents=True)
            allowed.write_text("StructureAggregateCensus internal implementation\n", encoding="utf-8")

            blockers: list[dict] = []
            result = CHECKER.validate_source_isolation(root, blockers)

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["violations"], ["hooks/ProcessEventHook.cpp"])
        self.assertIn(
            "structure_census_runtime_wiring_detected",
            {blocker["reason"] for blocker in blockers},
        )

    def test_missing_consume_only_flag_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["consume_only"] = False
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("consume_only_not_true", reasons)
        self.assertIn("consume_gate_not_accepted", reasons)

    def test_copied_pin_field_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            coverage = payload["coverage"]
            coverage["copied_fields_permitted"].append(
                "PrimalStructureItemContainer.VerifyPinCode.ReturnValue"
            )
            payload["copied_fields_permitted"].append(
                {
                    **payload["copied_fields_permitted"][0],
                    "copied_field": "PrimalStructureItemContainer.VerifyPinCode.ReturnValue",
                    "target": "PrimalStructureItemContainer.VerifyPinCode",
                    "field": "ReturnValue",
                }
            )
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("copied_field_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_field", reasons)

    def test_promote_gate_must_stay_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["non_claims"] = []
            payload["consume_only"] = False
            payload["safety_summary"]["consume_only"] = False
            payload["safety_summary"]["promotion_ready"] = True
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        reasons = {blocker["reason"] for blocker in report["blockers"]}
        self.assertIn("safety_promotion_ready_not_false", reasons)
        self.assertIn("promote_gate_missing_required_blockers", reasons)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_no_core_surface_claims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["claims"] = {
                "sdk": "StructureEvents SDK is ready",
                "identity": "structure identity and structure lookup are usable",
                "ownership": "structure ownership lookup is accepted",
                "build": "build placement and no-collision policy are ready",
                "mutation": "mutation allowed and return override allowed",
                "runtime": "runtime hooks and ProcessEvent hook wiring are active",
                "enforcement": "enforcement ready",
            }
            payload["non_claims"].append("v1 complete")
            payload["ownership_ready"] = True
            payload["build_placement_policy_ready"] = True
            payload["runtime_hooks_ready"] = True
            payload["enforcement_ready"] = True
            payload["v1_complete"] = True
            manifest.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker("--root", str(root), "--manifest", str(manifest), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        surfaces = {
            blocker["surface"]
            for blocker in report["blockers"]
            if blocker["reason"] == "structure_census_policy_surface_overclaim"
        }
        self.assertIn("public_structureevents_sdk", surfaces)
        self.assertIn("structure_identity", surfaces)
        self.assertIn("structure_lookup", surfaces)
        self.assertIn("structure_ownership", surfaces)
        self.assertIn("build_placement_policy", surfaces)
        self.assertIn("no_collision_policy", surfaces)
        self.assertIn("mutation", surfaces)
        self.assertIn("return_override", surfaces)
        self.assertIn("runtime_hooks", surfaces)
        self.assertIn("enforcement", surfaces)
        self.assertIn("v1_completion", surfaces)
        self.assertIn("ownership_ready", surfaces)
        self.assertIn("build_placement_policy_ready", surfaces)
        self.assertIn("runtime_hooks_ready", surfaces)
        self.assertIn("enforcement_ready", surfaces)
        self.assertIn("v1_complete", surfaces)

    def test_protected_and_symlink_inputs_are_rejected(self) -> None:
        result = self.run_checker(
            "--root",
            "/servidor/ark/obelisk/artifacts/structure",
            "--manifest",
            "/servidor/ark/obelisk/artifacts/structure/manifest.json",
            check=False,
        )
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "pack"
            manifest = self.copy_pack(root)
            link = Path(temp_dir) / "manifest-link.json"
            link.symlink_to(manifest)
            result = self.run_checker("--root", str(root), "--manifest", str(link), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertIn("path_rejected", {blocker["reason"] for blocker in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
