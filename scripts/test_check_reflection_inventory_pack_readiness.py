#!/usr/bin/env python3
"""Tests for check_reflection_inventory_pack_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BINARY_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
CORE_SHA = "8" * 64


class CheckReflectionInventoryPackReadinessTests(unittest.TestCase):
    def default_functions(self) -> list[dict[str, object]]:
        return [
            {
                "family": "Server",
                "function_flags": "0x4020400",
                "name": "ServerListPlayers",
                "num_parms": 0,
                "outer_class_name": "ShooterPlayerController",
                "outer_name": "ShooterPlayerController",
                "parms_size": 0,
            },
            {
                "family": "Server",
                "function_flags": "0x4020400",
                "name": "ServerKickPlayer",
                "num_parms": 2,
                "outer_class_name": "ShooterPlayerController",
                "outer_name": "ShooterPlayerController",
                "parms_size": 32,
            },
        ]

    def write_pack(
        self,
        path: Path,
        *,
        functions: list[dict[str, object]] | None = None,
        manifest_updates: dict[str, object] | None = None,
        write_inventory: bool = True,
    ) -> None:
        path.mkdir(parents=True)
        manifest: dict[str, object] = {
            "schema": "obelisk.reflection-inventory-pack.v1",
            "status": "candidate-only",
            "promotion_status": "not_promoted_candidate_only",
            "artifact_identity": {
                "artifact_kind": "offline_core",
                "artifact_sha256": CORE_SHA,
                "capture_id": "reviewed-core",
                "evidence_pack_id": "reviewed-pack",
            },
            "binary": {"sha256": BINARY_SHA},
            "core": {"path": str(path.parent / "missing-core"), "sha256": CORE_SHA},
            "summary": {"fname_root_ready": True},
            "blockers": [],
            "artifacts": {"ufunction_inventory": "ufunction-inventory.json"},
        }
        if manifest_updates:
            manifest.update(manifest_updates)
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        if write_inventory:
            inventory = {"status": "offline-inventory", "functions": functions or self.default_functions()}
            (path / "ufunction-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")

    def run_checker(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "check_reflection_inventory_pack_readiness.py"), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def reason_codes(self, payload: dict[str, object]) -> set[str]:
        return {str(reason["reason"]) for reason in payload["reasons"]}  # type: ignore[index]

    def test_accepts_pack_with_required_admin_targets_without_reading_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_pack(root / "packs" / "identity")

            result = self.run_checker(["--root", str(root)])

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.reflection-inventory-pack-readiness-check.v1")
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["reasons"], [])
        self.assertIn("ServerListPlayers", " ".join(payload["accepted_pack"]["matched_targets"]))
        self.assertIn("does not read a core", " ".join(payload["non_claims"]))

    def test_missing_pack_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_checker(["--root", temp_dir], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertEqual(self.reason_codes(payload), {"missing_reflection_inventory_pack"})

    def test_schema_mismatch_fails_closed_when_only_non_matching_manifest_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "scriptstruct-pack"
            pack.mkdir()
            (pack / "manifest.json").write_text(
                json.dumps({"schema": "obelisk.scriptstruct-inventory-pack.v1"}),
                encoding="utf-8",
            )

            result = self.run_checker(["--root", str(root)], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(self.reason_codes(payload), {"missing_reflection_inventory_pack", "schema_mismatch"})

    def test_missing_ufunction_inventory_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_pack(root / "pack", write_inventory=False)

            result = self.run_checker(["--root", str(root)], check=False)

        payload = json.loads(result.stdout)
        self.assertIn("missing_ufunction_inventory", self.reason_codes(payload))
        self.assertIsNone(payload["accepted_pack"])

    def test_wrong_scope_and_missing_target_are_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows = self.default_functions()[:1]
            self.write_pack(
                root / "pack",
                functions=rows,
                manifest_updates={"status": "promoted", "blockers": ["not-reviewed"]},
            )

            result = self.run_checker(["--root", str(root)], check=False)

        payload = json.loads(result.stdout)
        codes = self.reason_codes(payload)
        self.assertIn("wrong_target_scope", codes)
        self.assertIn("missing_target", codes)
        missing = [reason for reason in payload["reasons"] if reason["reason"] == "missing_target"]
        self.assertEqual(missing[0]["targets"], ["ShooterPlayerController.ServerKickPlayer"])

    def test_inventory_row_errors_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            row = {f"unexpected_{index:02d}": index for index in range(25)}
            self.write_pack(root / "pack", functions=[row.copy() for _ in range(25)])

            result = self.run_checker(["--root", str(root)], check=False)

        payload = json.loads(result.stdout)
        row_errors = [
            reason
            for reason in payload["reasons"]
            if reason["reason"] == "missing_ufunction_inventory"
            and str(reason.get("detail", "")).startswith("functions[")
        ]
        omitted = [
            reason
            for reason in payload["reasons"]
            if reason["reason"] == "missing_ufunction_inventory"
            and reason.get("detail") == "inventory_row_errors_omitted"
        ]
        self.assertEqual(len(row_errors), 20)
        self.assertEqual(row_errors[0]["extra_keys_count"], 25)
        self.assertEqual(row_errors[0]["omitted_extra_keys_count"], 5)
        self.assertEqual(omitted[0]["omitted_count"], 5)

    def test_protected_root_is_rejected_without_scanning(self) -> None:
        result = self.run_checker(["--root", "/servidor/ark/live"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["manifests_scanned"], 0)
        self.assertEqual(self.reason_codes(payload), {"wrong_target_scope"})


if __name__ == "__main__":
    unittest.main()
