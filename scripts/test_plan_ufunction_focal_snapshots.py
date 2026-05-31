#!/usr/bin/env python3
"""Tests for plan_ufunction_focal_snapshots.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from reflection_target_sets import TARGET_SETS  # noqa: E402

BINARY_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
CORE_SHA = "8" * 64
PLAYER_IDENTITY_TARGET_SET = "players-identity-lifecycle-intake"


class PlanUFunctionFocalSnapshotsTests(unittest.TestCase):
    def default_functions(self) -> list[dict[str, object]]:
        return [
            {
                "family": "Server",
                "function_flags": "0x4020400",
                "name": "ServerChat",
                "num_parms": 2,
                "outer_class_name": "Class",
                "outer_name": "/Script/CoreUObject",
                "parms_size": 32,
            },
            {
                "family": "Server",
                "function_flags": "0x4020400",
                "name": "ServerSendChatMessage",
                "num_parms": 2,
                "outer_class_name": "ShooterPlayerController",
                "outer_name": "ShooterPlayerController",
                "parms_size": 40,
            },
        ]

    def rows_for_target_set(self, target_set: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for qualified in TARGET_SETS[target_set]:
            _, _, target = qualified.partition(":")
            outer, _, name = target.rpartition(".")
            rows.append(
                {
                    "family": "TargetSet",
                    "function_flags": "0x220cc0",
                    "name": name,
                    "num_parms": 0,
                    "outer_class_name": outer,
                    "outer_name": outer,
                    "parms_size": 0,
                }
            )
        return rows

    def write_pack(
        self,
        path: Path,
        *,
        core_path: Path,
        functions: list[dict[str, object]] | None = None,
        manifest_updates: dict[str, object] | None = None,
        identity_updates: dict[str, object] | None = None,
        summary_updates: dict[str, object] | None = None,
        target_sets: list[str] | None = None,
    ) -> None:
        path.mkdir(parents=True)
        identity: dict[str, object] = {
            "artifact_kind": "offline_core",
            "artifact_sha256": CORE_SHA,
            "capture_id": "reviewed-core",
            "evidence_pack_id": "reviewed-pack",
        }
        if identity_updates:
            identity.update(identity_updates)
        rows = functions if functions is not None else self.default_functions()
        summary: dict[str, object] = {
            "fname_root_ready": True,
            "function_count": len(rows),
            "target_requested_count": 0,
            "target_matched_count": 0,
            "target_missing_count": 0,
            "target_ambiguous_count": 0,
        }
        if summary_updates:
            summary.update(summary_updates)
        manifest: dict[str, object] = {
            "schema": "obelisk.reflection-inventory-pack.v1",
            "status": "candidate-only",
            "promotion_status": "not_promoted_candidate_only",
            "artifact_identity": identity,
            "binary": {"sha256": BINARY_SHA},
            "core": {"path": str(core_path), "sha256": CORE_SHA},
            "addresses": {
                "gobjects": "0x595b7e0",
                "fname_root_slot": "0x595c000",
                "fname_table": "0x12340000",
            },
            "inputs": {"max_objects": 1234, "target_sets": target_sets or []},
            "artifacts": {
                "ufunction_inventory": "ufunction-inventory.json",
                "fname_root_validation": "fname-root-validation.json",
            },
            "summary": summary,
            "blockers": [],
        }
        if manifest_updates:
            manifest.update(manifest_updates)
        inventory = {
            "status": "offline-inventory",
            "functions": rows,
        }
        if target_sets:
            inventory["target_set_coverage"] = {
                "target_sets": target_sets,
                "requested_targets": [
                    qualified.partition(":")[2]
                    for target_set in target_sets
                    for qualified in TARGET_SETS[target_set]
                ],
            }
        (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (path / "ufunction-inventory.json").write_text(json.dumps(inventory), encoding="utf-8")

    def run_planner(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "plan_ufunction_focal_snapshots.py"),
                "--evidence-obelisk-commit",
                "reviewed-commit",
                *args,
            ],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_accepts_minimal_pack_and_target_file_without_reading_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            missing_core = root / "reviewed-core-does-not-exist"
            self.write_pack(pack, core_path=missing_core)
            targets = root / "targets.txt"
            targets.write_text(
                "\n".join(
                    [
                        "# reviewed exact focal list",
                        "obelisk.ufunction-chain.snapshot.v1:/Script/CoreUObject.ServerChat",
                        "ShooterPlayerController.ServerSendChatMessage",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_planner(["--inventory-pack", str(pack), "--target-file", str(targets)])

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.ufunction-focal-snapshot-plan.v1")
        self.assertEqual(payload["inventory_source"], "accepted_redacted_inventory_pack")
        self.assertEqual(payload["requested_count"], 2)
        self.assertEqual(payload["planned_command_count"], 2)
        self.assertEqual(payload["blocked_count"], 0)
        self.assertEqual(payload["artifact_identity"]["artifact_sha256"], CORE_SHA)
        self.assertEqual(payload["artifact_identity"]["capture_id"], "reviewed-core")
        self.assertEqual(payload["artifact_identity"]["evidence_pack_id"], "reviewed-pack")
        self.assertEqual(payload["artifact_identity"]["source"], "reflection-inventory-pack")
        self.assertEqual(payload["target_source"]["loaded_target_count"], 2)
        command = payload["snapshot_commands"][0]["argv"]
        self.assertIn("--snapshot-json", command)
        self.assertIn("--max-object-scan", command)
        self.assertIn("1234", command)
        self.assertIn("--evidence-obelisk-commit", command)
        self.assertIn("reviewed-commit", command)
        self.assertNotIn("--target-set", command)
        self.assertIn("Does not reread a core", " ".join(payload["non_claims"]))

    def test_json_out_writes_plan_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(pack, core_path=root / "missing-core")
            output = root / "plan.json"

            result = self.run_planner(
                [
                    "--inventory-pack",
                    str(pack / "manifest.json"),
                    "--target",
                    "/Script/CoreUObject.ServerChat",
                    "--json-out",
                    str(output),
                ]
            )
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.stdout, "")
        self.assertEqual(payload["planned_command_count"], 1)
        self.assertEqual(payload["inventory_pack"]["manifest"], str(pack / "manifest.json"))

    def test_target_set_expands_player_identity_without_reading_core(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            missing_core = root / "reviewed-core-does-not-exist"
            self.write_pack(
                pack,
                core_path=missing_core,
                functions=self.rows_for_target_set(PLAYER_IDENTITY_TARGET_SET),
                target_sets=[PLAYER_IDENTITY_TARGET_SET],
            )

            result = self.run_planner(
                [
                    "--inventory-pack",
                    str(pack),
                    "--target-set",
                    PLAYER_IDENTITY_TARGET_SET,
                ]
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["target_source"]["target_sets"], [PLAYER_IDENTITY_TARGET_SET])
        self.assertEqual(payload["target_source"]["loaded_target_count"], 12)
        self.assertEqual(payload["requested_count"], 12)
        self.assertEqual(payload["planned_command_count"], 12)
        self.assertEqual(payload["blocked_count"], 0)
        planned_targets = {entry["target"] for entry in payload["snapshot_commands"]}
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerListPlayers",
            planned_targets,
        )
        self.assertIn(
            "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ServerKickPlayer",
            planned_targets,
        )
        first_command = payload["snapshot_commands"][0]["argv"]
        self.assertIn("--snapshot-json", first_command)
        self.assertEqual(str(missing_core), payload["core"])

    def test_player_identity_target_set_requires_matching_pack_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(
                pack,
                core_path=root / "missing-core",
                functions=self.rows_for_target_set(PLAYER_IDENTITY_TARGET_SET),
            )

            result = self.run_planner(
                [
                    "--inventory-pack",
                    str(pack),
                    "--target-set",
                    PLAYER_IDENTITY_TARGET_SET,
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inputs.target_sets must include players-identity-lifecycle-intake", result.stderr)

    def test_player_identity_target_set_requires_complete_coverage_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(
                pack,
                core_path=root / "missing-core",
                functions=self.rows_for_target_set(PLAYER_IDENTITY_TARGET_SET),
                target_sets=[PLAYER_IDENTITY_TARGET_SET],
            )
            inventory_path = pack / "ufunction-inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            inventory["target_set_coverage"]["requested_targets"] = [
                "ShooterPlayerController.ServerListPlayers"
            ]
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

            result = self.run_planner(
                [
                    "--inventory-pack",
                    str(pack),
                    "--target-set",
                    PLAYER_IDENTITY_TARGET_SET,
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target_set_coverage.requested_targets must include the complete", result.stderr)

    def test_unknown_target_set_rejects_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(pack, core_path=root / "missing-core")

            result = self.run_planner(
                ["--inventory-pack", str(pack), "--target-set", "not-a-target-set"],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown --target-set: not-a-target-set", result.stderr)

    def test_missing_target_is_candidate_blocked_not_invented(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(pack, core_path=root / "missing-core")

            result = self.run_planner(
                ["--inventory-pack", str(pack), "--target", "PrimalStructure.IsAllowedToBuild"]
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["planned_command_count"], 0)
        self.assertEqual(payload["blocked_count"], 1)
        self.assertEqual(payload["targets"][0]["status"], "blocked")
        self.assertEqual(payload["targets"][0]["blocker"], "missing_inventory_target")
        self.assertEqual(payload["promotion_status"], "not_promoted_candidate_only")

    def test_ambiguous_duplicate_inventory_rows_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            duplicated = [self.default_functions()[0], dict(self.default_functions()[0])]
            self.write_pack(pack, core_path=root / "missing-core", functions=duplicated)

            result = self.run_planner(
                ["--inventory-pack", str(pack), "--target", "/Script/CoreUObject.ServerChat"]
            )

        payload = json.loads(result.stdout)
        self.assertEqual(payload["planned_command_count"], 0)
        self.assertEqual(payload["blocked_count"], 1)
        self.assertEqual(payload["targets"][0]["inventory_status"], "ambiguous")
        self.assertEqual(payload["targets"][0]["blocker"], "ambiguous_inventory_target")

    def test_duplicate_targets_reject_after_schema_normalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(pack, core_path=root / "missing-core")

            result = self.run_planner(
                [
                    "--inventory-pack",
                    str(pack),
                    "--target",
                    "/Script/CoreUObject.ServerChat",
                    "--target",
                    "obelisk.ufunction-chain.snapshot.v1:/Script/CoreUObject.ServerChat",
                ],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate --plan-target: /Script/CoreUObject.ServerChat", result.stderr)

    def test_rejects_unready_pack_or_existing_pack_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            unready = root / "unready"
            blocked = root / "blocked"
            self.write_pack(unready, core_path=root / "missing-core", summary_updates={"fname_root_ready": False})
            self.write_pack(blocked, core_path=root / "missing-core", manifest_updates={"blockers": ["fname_root_not_ready"]})

            unready_result = self.run_planner(
                ["--inventory-pack", str(unready), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )
            blocked_result = self.run_planner(
                ["--inventory-pack", str(blocked), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )

        self.assertNotEqual(unready_result.returncode, 0)
        self.assertIn("summary.fname_root_ready must be true", unready_result.stderr)
        self.assertNotEqual(blocked_result.returncode, 0)
        self.assertIn("blockers must be empty before focal snapshot planning", blocked_result.stderr)

    def test_rejects_incomplete_identity_and_invalid_sha_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            incomplete = root / "incomplete"
            invalid_sha = root / "invalid-sha"
            self.write_pack(
                incomplete,
                core_path=root / "missing-core",
                identity_updates={"evidence_pack_id": ""},
            )
            self.write_pack(
                invalid_sha,
                core_path=root / "missing-core",
                manifest_updates={"binary": {"sha256": "not-a-sha"}},
            )

            incomplete_result = self.run_planner(
                ["--inventory-pack", str(incomplete), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )
            invalid_sha_result = self.run_planner(
                ["--inventory-pack", str(invalid_sha), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )

        self.assertNotEqual(incomplete_result.returncode, 0)
        self.assertIn("artifact_identity.evidence_pack_id must be a non-empty string", incomplete_result.stderr)
        self.assertNotEqual(invalid_sha_result.returncode, 0)
        self.assertIn("binary.sha256 must be a lowercase 64-character SHA256", invalid_sha_result.stderr)

    def test_rejects_protected_core_path_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            self.write_pack(pack, core_path=Path("/servidor/ark/live/core"))

            result = self.run_planner(
                ["--inventory-pack", str(pack), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("core.path must not read from protected server root /servidor/ark", result.stderr)

    def test_rejects_symlinked_pack_and_core_path_components(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            real_pack = root / "real-pack"
            self.write_pack(real_pack, core_path=root / "missing-core")
            pack_link = root / "pack-link"
            pack_link.symlink_to(real_pack, target_is_directory=True)

            core_target = root / "core-target"
            core_target.write_text("not read", encoding="utf-8")
            core_link = root / "core-link"
            core_link.symlink_to(core_target)
            symlink_core_pack = root / "symlink-core-pack"
            self.write_pack(symlink_core_pack, core_path=core_link)

            pack_result = self.run_planner(
                ["--inventory-pack", str(pack_link), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )
            core_result = self.run_planner(
                ["--inventory-pack", str(symlink_core_pack), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )

        self.assertNotEqual(pack_result.returncode, 0)
        self.assertIn("--inventory-pack must not be a symlink", pack_result.stderr)
        self.assertNotEqual(core_result.returncode, 0)
        self.assertIn("core.path must not be a symlink", core_result.stderr)

    def test_rejects_non_redacted_inventory_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pack = root / "pack"
            rows = self.default_functions()
            rows[0] = dict(rows[0])
            rows[0]["address"] = "0xdeadbeef"
            self.write_pack(pack, core_path=root / "missing-core", functions=rows)

            result = self.run_planner(
                ["--inventory-pack", str(pack), "--target", "/Script/CoreUObject.ServerChat"],
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has non-redacted extra keys", result.stderr)


if __name__ == "__main__":
    unittest.main()
