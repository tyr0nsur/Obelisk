#!/usr/bin/env python3
"""Tests for reflection scalar candidate summary tooling."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "summarize_reflection_scalar_candidates.py"


def run_summary(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class SummarizeReflectionScalarCandidatesTests(unittest.TestCase):
    def test_mission_target_set_marks_only_bool_fields_as_copied(self) -> None:
        result = run_summary("--target-set", "mission-compact-intake", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema"], "obelisk.reflection-scalar-candidate-summary.v1")
        self.assertEqual(payload["target_count"], 4)
        self.assertEqual(payload["summarized_count"], 4)
        self.assertEqual(payload["missing_targets"], [])

        targets = {target["target"]: target for target in payload["targets"]}
        add_player = targets["MissionType.AddPlayerToMission"]
        self.assertEqual(add_player["function_flags"], "0x4020405")
        self.assertEqual(
            [field["name"] for field in add_player["copied_fields"]],
            ["bForceAdd", "ReturnValue"],
        )
        self.assertEqual(
            [field["name"] for field in add_player["redacted_fields"]],
            ["PlayerCharacter"],
        )

        removed = targets["MissionType.BPOnPlayerRemovedFromMission"]
        self.assertEqual(
            [field["name"] for field in removed["copied_fields"]],
            ["bFromMissionCompleteEvent", "bLastPhaseSuccess"],
        )
        self.assertEqual(
            [field["name"] for field in removed["redacted_fields"]],
            ["Player", "Controller"],
        )

        usable_items = targets["MissionType.GetPlayerUsableItems"]
        self.assertEqual(usable_items["copied_fields"], [])
        self.assertEqual(
            [field["name"] for field in usable_items["redacted_fields"]],
            ["Character", "OutItemIDs"],
        )

    def test_text_output_includes_non_copied_array_reason(self) -> None:
        result = run_summary("--target-set", "mission-compact-intake")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MissionType.GetPlayerUsableItems", result.stdout)
        self.assertIn("redacted OutItemIDs class=ArrayProperty", result.stdout)

    def test_dino_target_set_marks_int32_and_bool_fields_as_copied(self) -> None:
        result = run_summary("--target-set", "dino-compact-intake", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["target_count"], 2)
        self.assertEqual(payload["summarized_count"], 2)
        self.assertEqual(payload["missing_targets"], [])

        targets = {target["target"]: target for target in payload["targets"]}
        add_passenger = targets["PrimalDinoCharacter.AddPassenger"]
        copied = {field["name"]: field["classification"] for field in add_passenger["copied_fields"]}
        self.assertEqual(
            copied,
            {
                "PassengerSeatIndex": "copied_int32",
                "bForcePassenger": "copied_bool",
                "bAllowFlyersAndWaterDinos": "copied_bool",
                "bSkipLineTrace": "copied_bool",
                "ReturnValue": "copied_bool",
            },
        )
        self.assertEqual(
            [field["name"] for field in add_passenger["redacted_fields"]],
            ["ACharacter"],
        )
        self.assertEqual(add_passenger["blocked_fields"], [])

    def test_buff_target_set_redacts_class_properties(self) -> None:
        result = run_summary(
            "--target-set",
            "buff-compact-intake",
            "--target-set",
            "buff-breadth-intake",
            "--json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        payload = json.loads(result.stdout)
        targets = {target["target"]: target for target in payload["targets"]}
        prevent_other = targets["PrimalBuff.BPPreventAddingOtherBuff"]
        self.assertEqual(
            [field["name"] for field in prevent_other["redacted_fields"]],
            ["anotherBuffClass"],
        )
        self.assertEqual(prevent_other["blocked_fields"], [])

    def test_rejects_protected_live_server_snapshot_root(self) -> None:
        result = run_summary(
            "--snapshot-root",
            "/servidor/ark/not-approved/ufunction_snapshots",
            "--target-set",
            "mission-compact-intake",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot root must not read from protected live-server path", result.stderr)

    def test_rejects_symlink_to_protected_live_server_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            link = Path(tmp) / "snapshots"
            link.symlink_to("/servidor/ark/not-approved/ufunction_snapshots")

            result = run_summary(
                "--snapshot-root",
                str(link),
                "--target-set",
                "mission-compact-intake",
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("snapshot root must not read from protected live-server path", result.stderr)


if __name__ == "__main__":
    unittest.main()
