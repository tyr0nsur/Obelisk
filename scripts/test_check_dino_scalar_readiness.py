#!/usr/bin/env python3
"""Tests for check_dino_scalar_readiness.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_dino_scalar_readiness.py"
sys.path.insert(0, str(SCRIPT_DIR))
import check_dino_scalar_readiness as readiness  # noqa: E402
import build_redacted_ufunction_signatures as build_tool  # noqa: E402


class CheckDinoScalarReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def copy_minimal_repo(self, root: Path) -> Path:
        dst = root / "repo"
        for relative in (
            "ue/DinoReflection.cpp",
            "ue/DinoReflection.h",
            "hooks/ProcessEventDinoReflection.cpp",
            "hooks/ProcessEventDinoReflection.h",
            "tests/core/DinoReflectionTests.cpp",
            "tests/core/ProcessEventDinoReflectionTests.cpp",
            "docs/research/2026-05-31-dino-scalar-policy-planning.md",
            "scripts/reflection_target_sets.py",
        ):
            target = dst / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, target)
        return dst

    def write_report(self, root: Path, payload: dict) -> Path:
        report = root / "dino-report.json"
        report.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return report

    def make_report(self) -> dict:
        return build_tool.build_report(
            snapshot_root=REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots",
            target_sets=["dino-compact-intake"],
        )

    def test_current_tree_is_candidate_ready_but_not_public_runtime_or_v1_ready(self) -> None:
        result = self.run_checker("--json")

        payload = json.loads(result.stdout)
        self.assertEqual("obelisk.dino-scalar-readiness-check.v1", payload["schema"])
        self.assertTrue(payload["ready"])
        self.assertTrue(payload["accepted_for_internal_planning"])
        self.assertTrue(payload["offline_only"])
        self.assertTrue(payload["not_artifact_gate"])
        self.assertFalse(payload["public_sdk_ready"])
        self.assertFalse(payload["public_dino_sdk_ready"])
        self.assertFalse(payload["public_abi_ready"])
        self.assertFalse(payload["runtime_ready"])
        self.assertFalse(payload["identity_ready"])
        self.assertFalse(payload["lookup_ready"])
        self.assertFalse(payload["mutation_ready"])
        self.assertFalse(payload["return_override_ready"])
        self.assertFalse(payload["resource_handle_ready"])
        self.assertFalse(payload["v1_completion_ready"])
        self.assertFalse(payload["promotion_ready"])
        self.assertTrue(payload["scalar_only_ready"])
        self.assertTrue(payload["precall_scalar_ready"])
        self.assertFalse(payload["postcall_return_ready"])
        self.assertEqual(
            {
                "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
                "PrimalDinoCharacter.AddPassenger.bForcePassenger",
                "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
                "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
            },
            set(payload["summary"]["precall_copied_fields"]),
        )
        self.assertEqual(
            {
                "PrimalDinoCharacter.AddPassenger.ReturnValue",
                "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
            },
            set(payload["summary"]["deferred_return_fields"]),
        )
        self.assertEqual("isolated", payload["source_isolation"]["status"])

    def test_detects_public_or_runtime_dino_wiring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self.copy_minimal_repo(Path(temp_dir))
            public_header = repo / "include" / "obelisk" / "ObeliskApi.h"
            public_header.parent.mkdir(parents=True, exist_ok=True)
            public_header.write_text("typedef struct DinoEvent DinoEvent;\n", encoding="utf-8")
            result = self.run_checker("--repo-root", str(repo), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("public_or_runtime_dino_wiring_detected", reasons)
        self.assertFalse(payload["public_dino_sdk_ready"])

    def test_object_ref_in_copied_scalars_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            preflight = report["descriptor_preflight"]
            object_ref = dict(preflight["excluded_object_refs"][0])
            object_ref["copied_field"] = object_ref.pop("excluded_field")
            object_ref["type"] = "redacted_uobject_ref"
            object_ref["direction"] = "in"
            preflight["copied_scalars"].append(object_ref)
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_coverage_mismatch", reasons)
        self.assertIn("forbidden_copied_scalar_field", reasons)

    def test_return_values_cannot_be_promoted_to_precall_or_runtime_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry["copied_field"].endswith(".ReturnValue"):
                    entry["direction"] = "in"
            report["descriptor_preflight"]["public_surface"] = True
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("precall_scalar_coverage_mismatch", reasons)
        self.assertIn("deferred_return_coverage_mismatch", reasons)
        self.assertIn("public_surface_overclaim", reasons)

    def test_bool_shape_native_or_bad_masks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry.get("type") == "bool":
                    entry["native_bool"] = True
                    entry["byte_mask"] = "0xff"
                    break
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("bool_scalar_metadata_mismatch", reasons)

    def test_descriptor_assignment_public_claims_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            preflight = report["descriptor_preflight"]
            preflight["assigned_resource_kind"] = "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_DINO"
            preflight["descriptors"][0]["assigned_event_kind"] = "OBELISK_DINO_EVENT_KIND_ADD_PASSENGER"
            preflight["safety_summary"]["promotion_ready"] = True
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("assigned_resource_or_event_kind", reasons)
        self.assertIn("runtime_public_readiness_overclaim", reasons)

    def test_missing_redacted_object_ref_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["excluded_object_refs"] = report["descriptor_preflight"]["excluded_object_refs"][:1]
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("redacted_object_ref_coverage_mismatch", reasons)

    def test_copied_scalar_source_snapshot_must_be_known(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["copied_scalars"][0]["source_snapshot"] = "snapshot-9999"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_source_snapshot_unknown", reasons)

    def test_report_path_must_not_use_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = self.write_report(root, self.make_report())
            symlink = root / "linked-report.json"
            symlink.symlink_to(report_path)
            result = self.run_checker("--report", str(symlink), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("path_rejected", reasons)

    def test_copied_scalar_source_snapshot_sha_must_match_generated_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["copied_scalars"][0]["source_snapshot_sha256"] = "0" * 64
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("copied_scalar_source_snapshot_sha256_mismatch", reasons)

    def test_excluded_object_ref_source_snapshot_sha_must_be_well_formed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            report["descriptor_preflight"]["excluded_object_refs"][0]["source_snapshot_sha256"] = "not-a-sha"
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("excluded_object_ref_source_snapshot_sha256_malformed", reasons)

    def test_same_target_cannot_mix_source_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = self.make_report()
            snapshots = report["generated_from"]["input_snapshots"]
            second_snapshot = snapshots[1]
            for entry in report["descriptor_preflight"]["copied_scalars"]:
                if entry["copied_field"] == "PrimalDinoCharacter.AddPassenger.bForcePassenger":
                    entry["source_snapshot"] = second_snapshot["id"]
                    entry["source_snapshot_sha256"] = second_snapshot["sha256"]
                    break
            report_path = self.write_report(root, report)
            result = self.run_checker("--report", str(report_path), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("target_source_snapshot_inconsistent", reasons)

    def test_detects_missing_target_set_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = self.copy_minimal_repo(Path(temp_dir))
            target_sets = repo / "scripts" / "reflection_target_sets.py"
            text = target_sets.read_text(encoding="utf-8")
            target_sets.write_text(text.replace("PrimalDinoCharacter.AllowCarryCharacter", "PrimalDinoCharacter.Missing"), encoding="utf-8")
            result = self.run_checker("--repo-root", str(repo), check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        reasons = {blocker["reason"] for blocker in payload["blockers"]}
        self.assertIn("target_set_target_missing", reasons)

    def test_build_report_can_be_called_directly(self) -> None:
        report = readiness.build_report(REPO_ROOT)
        self.assertTrue(report["ready"])
        self.assertEqual("dino-compact-intake", report["target_set"]["target_set"])


if __name__ == "__main__":
    unittest.main()
