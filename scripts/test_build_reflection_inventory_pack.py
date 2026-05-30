#!/usr/bin/env python3
"""Tests for build_reflection_inventory_pack.py."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from test_enumerate_core_uobjects import build_core_fixture  # noqa: E402


class BuildReflectionInventoryPackTests(unittest.TestCase):
    def run_builder(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "build_reflection_inventory_pack.py"), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_builds_redacted_pack_from_direct_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)
            output_dir = root / "pack"

            result = self.run_builder(
                [
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--fname-index",
                    "None=0",
                    "--fname-index",
                    "ServerChat=4",
                    "--ark-binary-sha256",
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    "--include-functions",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            inventory = json.loads((output_dir / "ufunction-inventory.json").read_text(encoding="utf-8"))
            fname = json.loads((output_dir / "fname-root-validation.json").read_text(encoding="utf-8"))

        self.assertEqual(json.loads(result.stdout)["schema"], "obelisk.reflection-inventory-pack.v1")
        self.assertEqual(manifest["status"], "candidate-only")
        self.assertEqual(manifest["promotion_status"], "not_promoted_candidate_only")
        self.assertIn("Does not expose UObject pointers", " ".join(manifest["non_claims"]))
        self.assertTrue(manifest["summary"]["fname_root_ready"])
        self.assertEqual(manifest["summary"]["function_count"], 1)
        self.assertEqual(manifest["summary"]["target_ambiguous_count"], 0)
        self.assertEqual(fname["manifest_readiness"]["exact_match_count"], 2)
        self.assertEqual(inventory["functions"][0]["name"], "ServerChat")
        self.assertEqual(
            set(inventory["functions"][0]),
            {
                "family",
                "function_flags",
                "name",
                "num_parms",
                "outer_class_name",
                "outer_name",
                "parms_size",
            },
        )

    def test_direct_core_requires_explicit_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            build_core_fixture(core)

            result = self.run_builder(
                [
                    "--core",
                    str(core),
                    "--output-dir",
                    str(root / "pack"),
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct --core mode requires explicit --gobjects and --fname-root-slot", result.stderr)

    def test_direct_core_requires_binary_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)

            result = self.run_builder(
                [
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--output-dir",
                    str(root / "pack"),
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct --core mode requires --binary or --ark-binary-sha256", result.stderr)

    def test_direct_core_rejects_invalid_binary_sha(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)

            result = self.run_builder(
                [
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--ark-binary-sha256",
                    "not-a-sha",
                    "--output-dir",
                    str(root / "pack"),
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--ark-binary-sha256 must be a lowercase 64-character SHA256", result.stderr)

    def test_rejects_invalid_param_filters_before_opening_core(self) -> None:
        result = self.run_builder(
            [
                "--core",
                "/tmp/missing-core",
                "--gobjects",
                "0x1",
                "--fname-root-slot",
                "0x2",
                "--ark-binary-sha256",
                "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                "--min-params",
                "3",
                "--max-params",
                "2",
                "--output-dir",
                "/tmp/obelisk-reflection-pack",
            ],
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--min-params must be less than or equal to --max-params", result.stderr)

    def test_rejects_protected_core_and_output_before_opening(self) -> None:
        result = self.run_builder(
            [
                "--core",
                "/servidor/ark/obelisk/dumps/core",
                "--gobjects",
                "0x1",
                "--fname-root-slot",
                "0x2",
                "--output-dir",
                "/tmp/obelisk-reflection-pack",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--core must not read from protected server root /servidor/ark", result.stderr)

        result = self.run_builder(
            [
                "--core",
                "/tmp/missing-core",
                "--gobjects",
                "0x1",
                "--fname-root-slot",
                "0x2",
                "--output-dir",
                "/servidor/ark/obelisk/packs/out",
            ],
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--output-dir must not write under protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_pack_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)
            output_dir = root / "pack"
            output_dir.mkdir()
            (output_dir / "manifest.json").symlink_to(root / "outside-manifest.json")

            result = self.run_builder(
                [
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--fname-index",
                    "None=0",
                    "--ark-binary-sha256",
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    "--output-dir",
                    str(output_dir),
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to overwrite symlinked pack artifact", result.stderr)

    def test_evidence_pack_mode_rejects_overrides_before_hashing_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "pack" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.core-dump-evidence-pack.v1",
                        "binary": {
                            "sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                        },
                        "core": {
                            "path": str(root / "missing-core"),
                            "sha256": "8" * 64,
                        },
                        "evidence_status": {"status": "complete", "gdb_core_failed": False},
                        "fname_root_slots": [{"address": "0x1"}],
                        "gobjects_candidates": [{"address": "0x2"}],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_builder(
                [
                    "--evidence-pack-manifest",
                    str(manifest),
                    "--gobjects",
                    "0x1",
                    "--output-dir",
                    str(root / "out"),
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not pass overrides", result.stderr)
        self.assertNotIn("does not exist", result.stderr)

    def test_evidence_pack_mode_plans_exact_focal_snapshot_without_target_set(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)
            core_sha = hashlib.sha256(core.read_bytes()).hexdigest()
            manifest = root / "pack" / "manifest.json"
            manifest.parent.mkdir()
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.core-dump-evidence-pack.v1",
                        "binary": {
                            "sha256": "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                        },
                        "core": {
                            "path": str(core),
                            "sha256": core_sha,
                        },
                        "evidence_status": {"status": "complete", "gdb_core_failed": False},
                        "fname_root_slots": [{"address": hex(addrs["fname_root_slot"])}],
                        "gobjects_candidates": [{"address": hex(addrs["gobjects"])}],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "out"

            result = self.run_builder(
                [
                    "--evidence-pack-manifest",
                    str(manifest),
                    "--fname-index",
                    "None=0",
                    "--fname-index",
                    "ServerChat=4",
                    "--plan-target",
                    "obelisk.ufunction-chain.snapshot.v1:/Script/CoreUObject.ServerChat",
                    "--output-dir",
                    str(output_dir),
                ]
            )

            stdout_manifest = json.loads(result.stdout)
            inventory = json.loads((output_dir / "ufunction-inventory.json").read_text(encoding="utf-8"))
            written_manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(stdout_manifest["summary"]["function_count"], 1)
        self.assertEqual(written_manifest["inputs"]["plan_targets"], [
            "obelisk.ufunction-chain.snapshot.v1:/Script/CoreUObject.ServerChat"
        ])
        plan = inventory["focal_snapshot_plan"]
        self.assertEqual(plan["schema"], "obelisk.ufunction-focal-snapshot-plan.v1")
        self.assertEqual(plan["planned_command_count"], 1)
        self.assertEqual(plan["blocked_count"], 0)
        target = plan["targets"][0]
        self.assertEqual(target["status"], "planned")
        self.assertEqual(target["promotion_status"], "not_promoted_candidate_only")
        self.assertIn("redacted or recognition-only", " ".join(target["redaction_review"]))
        command = plan["snapshot_commands"][0]["argv"]
        self.assertIn("--snapshot-json", command)
        self.assertIn("--outer-exact", command)
        self.assertIn("/Script/CoreUObject", command)
        self.assertIn("--name-exact", command)
        self.assertIn("ServerChat", command)
        self.assertIn("--evidence-artifact-sha256", command)
        self.assertIn(core_sha, command)
        self.assertNotIn("--target-set", command)

    def test_plan_target_reports_missing_inventory_target_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            core = root / "core"
            addrs = build_core_fixture(core)
            output_dir = root / "out"

            self.run_builder(
                [
                    "--core",
                    str(core),
                    "--gobjects",
                    hex(addrs["gobjects"]),
                    "--fname-root-slot",
                    hex(addrs["fname_root_slot"]),
                    "--fname-index",
                    "None=0",
                    "--ark-binary-sha256",
                    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520",
                    "--plan-target",
                    "PrimalStructure.IsAllowedToBuild",
                    "--output-dir",
                    str(output_dir),
                ]
            )
            inventory = json.loads((output_dir / "ufunction-inventory.json").read_text(encoding="utf-8"))

        plan = inventory["focal_snapshot_plan"]
        self.assertEqual(plan["planned_command_count"], 0)
        self.assertEqual(plan["blocked_count"], 1)
        self.assertEqual(plan["targets"][0]["status"], "blocked")
        self.assertEqual(plan["targets"][0]["blocker"], "missing_inventory_target")
        self.assertEqual(plan["targets"][0]["target"], "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild")


if __name__ == "__main__":
    unittest.main()
