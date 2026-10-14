#!/usr/bin/env python3
"""Tests for assemble_rc_ufunction_second_source_root.py."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import validate_offline_artifact_gate as gate  # noqa: E402

SCRIPT = SCRIPT_DIR / "assemble_rc_ufunction_second_source_root.py"
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
SHA_PREFIX = "7e7ded49e0c6"


TARGET_PATHS = {
    "minimal": [
        "sdk_inventory/PrimalItem.CanUse.snapshot.json",
        "sdk_inventory/PrimalItem.AllowRemoteAddToInventory.snapshot.json",
        "sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json",
        "sdk_structures/PrimalStructure.IsAllowedToDemolish.snapshot.json",
    ],
    "structure": [
        "sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json",
        "sdk_structures/PrimalStructure.IsAllowedToDemolish.snapshot.json",
        "sdk_structures/PrimalStructure.SetVariant.snapshot.json",
        "sdk_structures/PrimalStructureItemContainer.AllowToggleActivation.snapshot.json",
        "sdk_structures/PrimalStructureItemContainer.VerifyPinCode.snapshot.json",
        "sdk_structures/PrimalStructureSeating.CanSeat.snapshot.json",
    ],
    "item_return": [
        "sdk_items/PrimalItem.AllowEquipItem.snapshot.json",
        "sdk_items/PrimalItem.CanRepair.snapshot.json",
        "sdk_items/PrimalItem.UseItemOntoItem.snapshot.json",
    ],
    "chat": [
        "sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json",
    ],
}


class AssembleRcUFunctionSecondSourceRootTests(unittest.TestCase):
    def run_builder(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def copy_root(self, target_root: Path, group: str) -> Path:
        root = target_root / group
        for relative in TARGET_PATHS[group]:
            source = FIXTURE_ROOT / SHA_PREFIX / relative
            destination = root / SHA_PREFIX / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        return root

    def gate_args(self, *, root: Path, protected_root: Path, manifest: Path) -> argparse.Namespace:
        return argparse.Namespace(
            root=root,
            protected_root=protected_root,
            manifest=[manifest],
            artifact=[],
            expected_binary_sha256=None,
            mode="consume",
            strict_target_set_coverage=False,
            json=True,
        )

    def test_assembles_minimal_structure_chat_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            output = temp / "rc-root"

            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(output),
            )

            summary = json.loads(result.stdout)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            output_snapshot_count = len(list(output.rglob("*.snapshot.json")))

            self.assertEqual(summary["target_count"], 9)
            self.assertEqual(manifest["target_count"], 9)
            self.assertIs(manifest["path_redacted"], True)
            self.assertEqual(
                manifest["target_sets"],
                [
                    "minimal-second-source-intake",
                    "structure-observer-intake",
                    "chat-message-intake",
                ],
            )
            self.assertEqual(output_snapshot_count, 9)
            manifest_text = json.dumps(manifest, sort_keys=True)
            self.assertNotIn(str(temp), manifest_text)
            self.assertNotIn("/servidor/ark", manifest_text)
            self.assertNotIn("source_root", manifest_text)
            self.assertNotIn("source_path", manifest_text)
            gate_result = gate.build_result(
                self.gate_args(root=temp, protected_root=temp / "protected-server", manifest=output / "manifest.json")
            )
            self.assertEqual(gate_result["status"], "accepted")
            self.assertEqual(gate_result["blockers"], [])
            duplicate_targets = {
                snapshot["target"]: snapshot["source_target_sets"]
                for snapshot in manifest["snapshots"]
                if len(snapshot["source_target_sets"]) > 1
            }
            self.assertEqual(
                set(duplicate_targets),
                {
                    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.AllowStructureAccess",
                    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToDemolish",
                },
            )
            chat_snapshot = next(
                snapshot
                for snapshot in manifest["snapshots"]
                if snapshot["target"].endswith(":ShooterPlayerController.ServerSendChatMessage")
            )
            self.assertEqual(chat_snapshot["evidence"]["capture_id"], "primary_core_20260527T031311Z")
            self.assertEqual(chat_snapshot["evidence"]["evidence_pack_id"], "primary_core_pack_20260527T031311Z")
            self.assertEqual(chat_snapshot["evidence"]["artifact_sha256"], "1c4bf8876706b3af40bd9b73fbeb907a31356e62d6c9ff93aed0158d2cb2fe5e")
            self.assertNotIn("generated_by", chat_snapshot["evidence"])

    def test_rejects_stale_item_return_root_argument(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--item-return-root",
                "/servidor/ark/workspace-offline/item-return-only-policy-slice/ufunction-snapshots",
                "--chat-root",
                str(chat),
                "--output-root",
                str(temp / "rc-root"),
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments: --item-return-root", result.stderr)

    def test_manifest_uses_redacted_evidence_identity_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            chat_snapshot = chat / SHA_PREFIX / "sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json"
            payload = json.loads(chat_snapshot.read_text(encoding="utf-8"))
            payload["evidence"]["core_path"] = "/servidor/ark/ShooterGame/Saved/Crashes/core"
            payload["evidence"]["local_report"] = str(temp / "secret-report.json")
            chat_snapshot.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            output = temp / "rc-root"

            self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(output),
            )

            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            manifest_text = json.dumps(manifest, sort_keys=True)
            self.assertNotIn("/servidor/ark", manifest_text)
            self.assertNotIn(str(temp), manifest_text)
            copied_snapshot = output / SHA_PREFIX / "sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json"
            copied_payload = json.loads(copied_snapshot.read_text(encoding="utf-8"))
            self.assertEqual(copied_payload["evidence"]["core_path"], "/servidor/ark/ShooterGame/Saved/Crashes/core")

    def test_rejects_missing_chat_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = temp / "chat-empty"
            chat.mkdir()
            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(temp / "rc-root"),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ShooterPlayerController.ServerSendChatMessage", result.stderr)

    def test_rejects_divergent_duplicate_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            duplicate = structure / SHA_PREFIX / "sdk_structures/PrimalStructure.AllowStructureAccess.snapshot.json"
            payload = json.loads(duplicate.read_text(encoding="utf-8"))
            payload["metadata"]["object_count"] = 123
            duplicate.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(temp / "rc-root"),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("divergent duplicate snapshot", result.stderr)

    def test_rejects_orphan_snapshot_in_target_set_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            orphan_relative = TARGET_PATHS["item_return"][0]
            orphan_destination = minimal / SHA_PREFIX / orphan_relative
            orphan_destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FIXTURE_ROOT / SHA_PREFIX / orphan_relative, orphan_destination)

            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(temp / "rc-root"),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected snapshot target for minimal-second-source-intake", result.stderr)
        self.assertIn("PrimalItem.AllowEquipItem", result.stderr)

    def test_rejects_symlinked_source_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            minimal = self.copy_root(temp, "minimal")
            structure = self.copy_root(temp, "structure")
            chat = self.copy_root(temp, "chat")
            snapshot = chat / SHA_PREFIX / "sdk_chat/ShooterPlayerController.ServerSendChatMessage.snapshot.json"
            real_snapshot = temp / "real-chat.snapshot.json"
            shutil.move(snapshot, real_snapshot)
            snapshot.symlink_to(real_snapshot)

            result = self.run_builder(
                "--minimal-root",
                str(minimal),
                "--structure-root",
                str(structure),
                "--chat-root",
                str(chat),
                "--output-root",
                str(temp / "rc-root"),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot must not be a symlink", result.stderr)


if __name__ == "__main__":
    unittest.main()
