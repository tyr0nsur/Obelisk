#!/usr/bin/env python3
"""Tests for compare_reflection_inventory_packs.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


class CompareReflectionInventoryPacksTests(unittest.TestCase):
    def write_pack(
        self,
        path: Path,
        *,
        artifact_sha: str,
        capture_id: str,
        evidence_pack_id: str,
        binary_sha: str = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
        functions: list[dict[str, object]] | None = None,
        manifest_updates: dict[str, object] | None = None,
    ) -> None:
        path.mkdir(parents=True)
        manifest: dict[str, object] = {
            "schema": "obelisk.reflection-inventory-pack.v1",
            "status": "candidate-only",
            "promotion_status": "not_promoted_candidate_only",
            "artifact_identity": {
                "artifact_kind": "offline_core",
                "artifact_sha256": artifact_sha,
                "capture_id": capture_id,
                "evidence_pack_id": evidence_pack_id,
            },
            "binary": {"sha256": binary_sha},
            "summary": {
                "fname_root_ready": True,
                "function_count": len(functions or self.default_functions()),
                "target_requested_count": 2,
                "target_matched_count": 2,
                "target_missing_count": 0,
                "target_ambiguous_count": 0,
            },
            "blockers": [],
        }
        if manifest_updates:
            manifest.update(manifest_updates)
        inventory = {
            "status": "offline-inventory",
            "functions": functions or self.default_functions(),
        }
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (path / "ufunction-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")

    def default_functions(self) -> list[dict[str, object]]:
        return [
            {
                "family": "Can",
                "function_flags": "0x54020400",
                "name": "CanUse",
                "num_parms": 2,
                "outer_class_name": "Class",
                "outer_name": "PrimalItem",
                "parms_size": 2,
            },
            {
                "family": "Allow",
                "function_flags": "0x4020400",
                "name": "AllowRemoteAddToInventory",
                "num_parms": 4,
                "outer_class_name": "Class",
                "outer_name": "PrimalItem",
                "parms_size": 18,
            },
        ]

    def run_compare(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "compare_reflection_inventory_packs.py"), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_accepts_distinct_matching_candidate_only_packs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            self.write_pack(base, artifact_sha="1" * 64, capture_id="base", evidence_pack_id="pack-a")
            self.write_pack(candidate, artifact_sha="2" * 64, capture_id="candidate", evidence_pack_id="pack-b")

            result = self.run_compare(
                [
                    "--base-pack",
                    str(base),
                    "--candidate-pack",
                    str(candidate),
                    "--fail-on-gaps",
                    "--json",
                ]
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.reflection-inventory-pack-comparison.v1")
        self.assertEqual(payload["status"], "accepted")
        self.assertEqual(payload["blockers"], [])
        self.assertEqual(payload["function_comparison"]["shared_function_count"], 2)

    def test_rejects_shared_artifact_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            self.write_pack(base, artifact_sha="1" * 64, capture_id="same", evidence_pack_id="pack-a")
            self.write_pack(candidate, artifact_sha="2" * 64, capture_id="same", evidence_pack_id="pack-b")

            result = self.run_compare(
                ["--base-pack", str(base), "--candidate-pack", str(candidate), "--fail-on-gaps", "--json"],
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("artifact_identity_not_distinct_capture_id", payload["blockers"])

    def test_rejects_binary_sha_mismatch_and_public_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            self.write_pack(base, artifact_sha="1" * 64, capture_id="base", evidence_pack_id="pack-a")
            self.write_pack(
                candidate,
                artifact_sha="2" * 64,
                capture_id="candidate",
                evidence_pack_id="pack-b",
                binary_sha="3" * 64,
                manifest_updates={"promotion_status": "promoted"},
            )

            result = self.run_compare(
                ["--base-pack", str(base), "--candidate-pack", str(candidate), "--fail-on-gaps", "--json"],
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("binary_sha256_mismatch", payload["blockers"])
        self.assertIn("candidate: promotion_status_not_candidate_only", payload["blockers"])

    def test_reports_function_changes_and_redaction_extra_keys(self) -> None:
        changed = self.default_functions()
        changed[0] = dict(changed[0])
        changed[0]["parms_size"] = 4
        changed[0]["index"] = 123
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            self.write_pack(base, artifact_sha="1" * 64, capture_id="base", evidence_pack_id="pack-a")
            self.write_pack(candidate, artifact_sha="2" * 64, capture_id="candidate", evidence_pack_id="pack-b", functions=changed)

            result = self.run_compare(
                ["--base-pack", str(base), "--candidate-pack", str(candidate), "--fail-on-gaps", "--json"],
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("candidate inventory: function_row_0_extra_keys", payload["blockers"])
        self.assertIn("changed_function_metadata", payload["blockers"])
        self.assertEqual(payload["function_comparison"]["changed_functions"][0]["target"], "PrimalItem.CanUse")

    def test_reports_added_and_removed_functions(self) -> None:
        candidate_functions = [self.default_functions()[0]]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base = root / "base"
            candidate = root / "candidate"
            self.write_pack(base, artifact_sha="1" * 64, capture_id="base", evidence_pack_id="pack-a")
            self.write_pack(candidate, artifact_sha="2" * 64, capture_id="candidate", evidence_pack_id="pack-b", functions=candidate_functions)

            result = self.run_compare(
                ["--base-pack", str(base), "--candidate-pack", str(candidate), "--fail-on-gaps", "--json"],
                check=False,
            )

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn("missing_functions_in_candidate", payload["blockers"])
        self.assertEqual(
            payload["function_comparison"]["missing_in_candidate"],
            ["PrimalItem.AllowRemoteAddToInventory"],
        )


if __name__ == "__main__":
    unittest.main()
