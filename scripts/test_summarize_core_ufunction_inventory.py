#!/usr/bin/env python3
"""Offline tests for summarize_core_ufunction_inventory.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import summarize_core_ufunction_inventory as inventory


class UFunctionInventorySummaryTests(unittest.TestCase):
    def test_function_family_uses_common_unreal_prefixes(self) -> None:
        self.assertEqual(inventory.function_family("ServerSendChatMessage"), "Server")
        self.assertEqual(inventory.function_family("ClientRestart"), "Client")
        self.assertEqual(inventory.function_family("BPOverrideAllowStructureAccess"), "BP")
        self.assertEqual(inventory.function_family("K2_GetActorLocation"), "K2")
        self.assertEqual(inventory.function_family("Destroy"), "Destroy")

    def test_summarize_functions_groups_by_outer_and_family(self) -> None:
        payload = inventory.summarize_functions(
            [
                {
                    "name": "ServerDoThing",
                    "family": "Server",
                    "outer_name": "ShooterPlayerController",
                    "outer_class_name": "Class",
                    "index": 1,
                },
                {
                    "name": "ClientDoThing",
                    "family": "Client",
                    "outer_name": "ShooterPlayerController",
                    "outer_class_name": "Class",
                    "index": 2,
                },
                {
                    "name": "BPGetValue",
                    "family": "BP",
                    "outer_name": "PrimalItem",
                    "outer_class_name": "Class",
                    "index": 3,
                },
            ],
            max_groups=10,
        )

        self.assertEqual(payload["function_count"], 3)
        self.assertEqual(payload["top_outers"][0], {"outer": "ShooterPlayerController", "count": 2})
        self.assertIn({"family": "Server", "count": 1}, payload["top_families"])
        groups = {group["outer"]: group for group in payload["outer_groups"]}
        self.assertEqual(groups["ShooterPlayerController"]["families"], {"Server": 1, "Client": 1})
        self.assertEqual(len(groups["ShooterPlayerController"]["samples"]), 2)

    def test_filter_functions_combines_focus_filters(self) -> None:
        functions = [
            {
                "name": "ServerDoThing",
                "family": "Server",
                "outer_name": "ShooterPlayerController",
                "num_parms": 2,
            },
            {
                "name": "ClientDoThing",
                "family": "Client",
                "outer_name": "ShooterPlayerController",
                "num_parms": 1,
            },
            {
                "name": "ServerDoDinoThing",
                "family": "Server",
                "outer_name": "PrimalDinoCharacter",
                "num_parms": 3,
            },
        ]

        filtered = inventory.filter_functions(
            functions,
            outer_contains="player",
            name_contains="do",
            family="server",
            min_params=2,
            max_params=2,
        )

        self.assertEqual([item["name"] for item in filtered], ["ServerDoThing"])

    def test_filter_functions_rejects_unknown_param_count_when_param_filter_is_set(self) -> None:
        functions = [{"name": "ServerMaybe", "family": "Server", "outer_name": "Controller", "num_parms": None}]

        self.assertEqual(inventory.filter_functions(functions, min_params=1), [])

    def test_target_set_coverage_reports_matched_missing_and_unassigned(self) -> None:
        functions = [
            {
                "name": "CanUse",
                "outer_name": "PrimalItem",
                "family": "Can",
                "index": 1,
            },
            {
                "name": "AllowStructureAccess",
                "outer_name": "PrimalStructure",
                "family": "Allow",
                "index": 2,
            },
            {
                "name": "ServerUnrelated",
                "outer_name": "ShooterPlayerController",
                "family": "Server",
                "index": 3,
            },
        ]

        coverage = inventory.target_set_coverage(
            functions,
            target_sets=["minimal-second-source-intake"],
        )

        self.assertEqual(
            coverage["schema"],
            "obelisk.ufunction-inventory-target-set-coverage.v1",
        )
        self.assertEqual(coverage["requested_count"], 4)
        self.assertEqual(coverage["matched_count"], 2)
        self.assertEqual(coverage["missing_count"], 2)
        self.assertIn("PrimalItem.AllowRemoteAddToInventory", coverage["missing_targets"])
        self.assertIn("PrimalStructure.IsAllowedToDemolish", coverage["missing_targets"])
        self.assertEqual(coverage["matched_targets"]["PrimalItem.CanUse"]["count"], 1)
        self.assertEqual(coverage["ambiguous_count"], 0)
        self.assertEqual(coverage["ambiguous_targets"], [])
        self.assertEqual(coverage["unassigned_function_count"], 1)
        self.assertEqual(coverage["unassigned_samples"][0]["name"], "ServerUnrelated")

    def test_target_set_coverage_reports_ambiguous_matches(self) -> None:
        functions = [
            {"name": "CanUse", "outer_name": "PrimalItem", "family": "Can", "index": 1},
            {"name": "CanUse", "outer_name": "PrimalItem", "family": "Can", "index": 2},
        ]

        coverage = inventory.target_set_coverage(
            functions,
            target_sets=["minimal-second-source-intake"],
        )

        self.assertEqual(coverage["matched_count"], 1)
        self.assertEqual(coverage["ambiguous_count"], 1)
        self.assertEqual(coverage["ambiguous_targets"][0]["target"], "PrimalItem.CanUse")
        self.assertEqual(coverage["ambiguous_targets"][0]["count"], 2)

    def test_target_set_coverage_uses_unfiltered_inventory(self) -> None:
        functions = [
            {
                "name": "CanUse",
                "outer_name": "PrimalItem",
                "family": "Can",
                "index": 1,
            },
            {
                "name": "ServerUnrelated",
                "outer_name": "ShooterPlayerController",
                "family": "Server",
                "index": 2,
            },
        ]

        with (
            mock.patch.object(inventory.uobjects, "CoreMemory") as memory_class,
            mock.patch.object(inventory, "collect_function_inventory", return_value=({}, functions)),
            mock.patch.object(
                sys,
                "argv",
                [
                    "summarize_core_ufunction_inventory.py",
                    "--core",
                    "/tmp/core",
                    "--outer-contains",
                    "ShooterPlayerController",
                    "--target-set",
                    "minimal-second-source-intake",
                    "--json",
                ],
            ),
            mock.patch("builtins.print") as print_mock,
        ):
            memory_class.return_value.close.return_value = None
            self.assertEqual(inventory.main(), 0)

        payload = inventory.json.loads(print_mock.call_args.args[0])
        self.assertEqual(payload["summary"]["function_count"], 1)
        self.assertIn("PrimalItem.CanUse", payload["target_set_coverage"]["matched_targets"])

    def test_cli_rejects_protected_direct_core_path_before_open(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "summarize_core_ufunction_inventory.py"),
                "--core",
                "/servidor/ark/obelisk/dumps/core",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--core must not read from protected server root /servidor/ark", result.stderr)

    def test_cli_rejects_protected_snapshot_manifest_path_before_core_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "summarize_core_ufunction_inventory.py"),
                    "--core",
                    str(root / "missing-core"),
                    "--target-set",
                    "minimal-second-source-intake",
                    "--plan-regeneration",
                    "--snapshot-manifest",
                    "/servidor/ark/obelisk/snapshots/manifest.json",
                    "--json",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--snapshot-manifest must not read from protected server root /servidor/ark", result.stderr)

    def test_cli_rejects_evidence_pack_core_path_under_protected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            (pack / "manifest.json").write_text(
                json.dumps(
                    {
                        "binary": {"sha256": "7" * 64},
                        "core": {
                            "path": "/servidor/ark/obelisk/dumps/core",
                            "sha256": "8" * 64,
                        },
                        "fname_root_slots": [{"address": "0x1"}],
                        "gobjects_candidates": [{"address": "0x2"}],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "summarize_core_ufunction_inventory.py"),
                    "--evidence-pack",
                    str(pack),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence pack core.path must not read from protected server root /servidor/ark", result.stderr)

    def test_cli_allows_paths_that_only_share_protected_prefix_text(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "summarize_core_ufunction_inventory.py"),
                "--core",
                "/servidor/ark-not-live/offline-core",
                "--json",
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/servidor/ark-not-live/offline-core", result.stderr)
        self.assertNotIn("protected server root", result.stderr)

    def test_cli_allows_evidence_pack_paths_that_only_share_protected_prefix_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            pack.mkdir()
            (pack / "manifest.json").write_text(
                json.dumps(
                    {
                        "binary": {
                            "path": "/servidor/ark-not-live/ShooterGameServer",
                            "sha256": "7" * 64,
                        },
                        "core": {
                            "path": "/servidor/ark-not-live/offline-core",
                            "sha256": "8" * 64,
                        },
                        "fname_root_slots": [{"address": "0x1"}],
                        "gobjects_candidates": [{"address": "0x2"}],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "summarize_core_ufunction_inventory.py"),
                    "--evidence-pack",
                    str(pack),
                    "--json",
                ],
                capture_output=True,
                text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("/servidor/ark-not-live/offline-core", result.stderr)
        self.assertNotIn("protected server root", result.stderr)

    def test_regeneration_plan_reports_manifest_present_missing_and_ambiguous_targets(self) -> None:
        functions = [
            {"name": "CanUse", "outer_name": "PrimalItem", "index": 1},
            {"name": "AllowRemoteAddToInventory", "outer_name": "PrimalItem", "index": 2},
            {"name": "AllowRemoteAddToInventory", "outer_name": "PrimalItem", "index": 3},
            {"name": "AllowStructureAccess", "outer_name": "PrimalStructure", "index": 4},
        ]
        manifest = {
            "schema": "obelisk.ufunction-snapshot-manifest.v1",
            "source": "offline_core",
            "status": "candidate-only",
            "targets": [
                {
                    "module": "sdk_inventory",
                    "outer": "PrimalItem",
                    "name": "CanUse",
                    "file": "PrimalItem.CanUse.snapshot.json",
                }
            ],
        }

        plan = inventory.target_set_regeneration_plan(
            functions,
            target_sets=["minimal-second-source-intake"],
            snapshot_manifest=manifest,
            snapshot_manifest_path=Path("manifest.json"),
            core=Path("core"),
            gobjects=0x595B7E0,
            fname_root_slot=0x5956F30,
        )

        targets = {item["target"]: item for item in plan["targets"]}
        self.assertEqual(plan["schema"], "obelisk.ufunction-target-set-regeneration-plan.v1")
        self.assertEqual(plan["promotion_status"], "not_promoted_candidate_only")
        self.assertEqual(targets["PrimalItem.CanUse"]["status"], "planned")
        self.assertEqual(targets["PrimalItem.CanUse"]["manifest_status"], "present")
        command = targets["PrimalItem.CanUse"]["regenerate_command"]
        self.assertIn("--target", command)
        self.assertIn("--gobjects", command)
        self.assertIn("0x595b7e0", command)
        self.assertIn("--fname-root-slot", command)
        self.assertIn("0x5956f30", command)
        self.assertEqual(targets["PrimalItem.AllowRemoteAddToInventory"]["status"], "blocked")
        self.assertEqual(targets["PrimalItem.AllowRemoteAddToInventory"]["blocker"], "ambiguous_inventory_target")
        self.assertEqual(targets["PrimalStructure.AllowStructureAccess"]["status"], "needs_manifest_entry_review")
        self.assertEqual(
            targets["PrimalStructure.AllowStructureAccess"]["candidate_manifest_entry"]["module"],
            "sdk_candidates",
        )
        self.assertEqual(targets["PrimalStructure.IsAllowedToDemolish"]["status"], "blocked")
        self.assertEqual(targets["PrimalStructure.IsAllowedToDemolish"]["blocker"], "missing_inventory_target")

    def test_regeneration_plan_prefers_evidence_pack_manifest_for_commands(self) -> None:
        manifest = {
            "schema": "obelisk.ufunction-snapshot-manifest.v1",
            "source": "offline_core",
            "status": "candidate-only",
            "targets": [
                {
                    "module": "sdk_inventory",
                    "outer": "PrimalItem",
                    "name": "CanUse",
                    "file": "PrimalItem.CanUse.snapshot.json",
                }
            ],
        }

        plan = inventory.target_set_regeneration_plan(
            [{"name": "CanUse", "outer_name": "PrimalItem", "index": 1}],
            target_sets=["minimal-second-source-intake"],
            snapshot_manifest=manifest,
            snapshot_manifest_path=Path("manifest.json"),
            core=Path("core"),
            gobjects=0x595B7E0,
            fname_root_slot=0x5956F30,
            evidence_pack_manifest=Path("pack/manifest.json"),
        )

        command = plan["regenerate_commands"][0]["argv"]
        self.assertIn("--evidence-pack-manifest", command)
        self.assertIn("pack/manifest.json", command)
        self.assertNotIn("--gobjects", command)
        self.assertNotIn("--fname-root-slot", command)
        self.assertEqual(plan["evidence_pack_manifest"], "pack/manifest.json")

    def test_regeneration_plan_rejects_duplicate_manifest_targets(self) -> None:
        manifest = {
            "schema": "obelisk.ufunction-snapshot-manifest.v1",
            "source": "offline_core",
            "status": "candidate-only",
            "targets": [
                {
                    "module": "sdk_inventory",
                    "outer": "PrimalItem",
                    "name": "CanUse",
                    "file": "PrimalItem.CanUse.snapshot.json",
                },
                {
                    "module": "sdk_other",
                    "outer": "PrimalItem",
                    "name": "CanUse",
                    "file": "Duplicate.snapshot.json",
                },
            ],
        }

        with self.assertRaises(SystemExit) as raised:
            inventory.target_set_regeneration_plan(
                [{"name": "CanUse", "outer_name": "PrimalItem", "index": 1}],
                target_sets=["minimal-second-source-intake"],
                snapshot_manifest=manifest,
                snapshot_manifest_path=Path("manifest.json"),
                core=Path("core"),
                gobjects=0x595B7E0,
                fname_root_slot=0x5956F30,
            )

        self.assertIn("duplicate snapshot manifest target: PrimalItem.CanUse", str(raised.exception))

    def test_plan_regeneration_requires_target_set(self) -> None:
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "summarize_core_ufunction_inventory.py",
                    "--core",
                    "/tmp/core",
                    "--plan-regeneration",
                ],
            ),
            self.assertRaises(SystemExit) as raised,
        ):
            inventory.main()

        self.assertIn("--plan-regeneration requires", str(raised.exception))

    def test_plan_regeneration_is_dry_run_and_uses_manifest_state(self) -> None:
        functions = [{"name": "CanUse", "outer_name": "PrimalItem", "index": 1}]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-snapshot-manifest.v1",
                        "source": "offline_core",
                        "status": "candidate-only",
                        "targets": [
                            {
                                "module": "sdk_inventory",
                                "outer": "PrimalItem",
                                "name": "CanUse",
                                "file": "PrimalItem.CanUse.snapshot.json",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with (
                mock.patch.object(inventory.uobjects, "CoreMemory") as memory_class,
                mock.patch.object(inventory, "collect_function_inventory", return_value=({}, functions)),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "summarize_core_ufunction_inventory.py",
                        "--core",
                        str(root / "core"),
                        "--target-set",
                        "minimal-second-source-intake",
                        "--plan-regeneration",
                        "--snapshot-manifest",
                        str(manifest),
                        "--json",
                    ],
                ),
                mock.patch("builtins.print") as print_mock,
            ):
                memory_class.return_value.close.return_value = None
                self.assertEqual(inventory.main(), 0)

            payload = inventory.json.loads(print_mock.call_args.args[0])

        plan = payload["target_set_regeneration_plan"]
        self.assertEqual(plan["schema"], "obelisk.ufunction-target-set-regeneration-plan.v1")
        self.assertEqual(plan["planned_command_count"], 1)
        self.assertEqual(plan["recommendation_count"], 0)
        self.assertEqual(plan["promotion_status"], "not_promoted_candidate_only")
        command = plan["regenerate_commands"][0]["argv"]
        self.assertIn("--gobjects", command)
        self.assertIn("--fname-root-slot", command)

    def test_plan_regeneration_uses_normalized_evidence_pack_manifest_path(self) -> None:
        functions = [{"name": "CanUse", "outer_name": "PrimalItem", "index": 1}]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack_dir = root / "pack"
            pack_dir.mkdir()
            pack_manifest = pack_dir / "manifest.json"
            pack_manifest.write_text(
                json.dumps(
                    {
                        "binary": {"sha256": "7" * 64},
                        "core": {"path": str(root / "core"), "sha256": "8" * 64},
                        "fname_root_slots": [{"address": "0x5956f30"}],
                        "gobjects_candidates": [{"address": "0x595b7e0"}],
                    }
                ),
                encoding="utf-8",
            )
            snapshot_manifest = root / "snapshot-manifest.json"
            snapshot_manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-snapshot-manifest.v1",
                        "source": "offline_core",
                        "status": "candidate-only",
                        "targets": [
                            {
                                "module": "sdk_inventory",
                                "outer": "PrimalItem",
                                "name": "CanUse",
                                "file": "PrimalItem.CanUse.snapshot.json",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            fake_pack = SimpleNamespace(
                manifest_path=pack_manifest,
                core=root / "core",
                gobjects=0x595B7E0,
                fname_root_slot=0x5956F30,
                binary_sha256="7" * 64,
                core_sha256="8" * 64,
            )
            with (
                mock.patch.object(inventory.verifier, "load_evidence_pack", return_value=fake_pack),
                mock.patch.object(inventory.uobjects, "CoreMemory") as memory_class,
                mock.patch.object(inventory, "collect_function_inventory", return_value=({}, functions)),
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "summarize_core_ufunction_inventory.py",
                        "--evidence-pack",
                        str(pack_dir),
                        "--target-set",
                        "minimal-second-source-intake",
                        "--plan-regeneration",
                        "--snapshot-manifest",
                        str(snapshot_manifest),
                        "--json",
                    ],
                ),
                mock.patch("builtins.print") as print_mock,
            ):
                memory_class.return_value.close.return_value = None
                self.assertEqual(inventory.main(), 0)

            payload = inventory.json.loads(print_mock.call_args.args[0])

        plan = payload["target_set_regeneration_plan"]
        command = plan["regenerate_commands"][0]["argv"]
        self.assertIn("--evidence-pack-manifest", command)
        self.assertIn(str(pack_manifest), command)
        self.assertNotEqual(str(pack_dir), command[command.index("--evidence-pack-manifest") + 1])
        self.assertEqual(plan["evidence_pack_manifest"], str(pack_manifest))

    def test_plan_regeneration_rejects_non_candidate_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-snapshot-manifest.v1",
                        "source": "offline_core",
                        "status": "accepted",
                        "targets": [
                            {
                                "module": "sdk_inventory",
                                "outer": "PrimalItem",
                                "name": "CanUse",
                                "file": "PrimalItem.CanUse.snapshot.json",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                inventory.load_snapshot_manifest(manifest)

        self.assertIn("status must be candidate-only", str(raised.exception))

    def test_plan_regeneration_rejects_non_offline_core_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.ufunction-snapshot-manifest.v1",
                        "source": "runtime_log",
                        "status": "candidate-only",
                        "targets": [],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit) as raised:
                inventory.load_snapshot_manifest(manifest)

        self.assertIn("source must be offline_core", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
