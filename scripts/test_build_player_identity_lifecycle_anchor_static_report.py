#!/usr/bin/env python3
"""Tests for build_player_identity_lifecycle_anchor_static_report.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "build_player_identity_lifecycle_anchor_static_report.py"
SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"


def static_report() -> dict:
    return {
        "schema": "obelisk.player-identity-static-lifecycle-orientation-check.v1",
        "status": "valid",
        "valid": True,
        "accepted_for_orientation": True,
        "accepted_lifecycle_anchors": False,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "binary_sha256": SHA,
        "checked_targets": [
            {
                "target": "ShooterGameMode.HandleNewPlayer",
                "role_hint": "session_start",
                "status": "candidate_orientation_valid",
            },
            {
                "target": "ShooterGameMode.OnLogout",
                "role_hint": "session_end",
                "status": "candidate_orientation_valid",
            },
        ],
        "blockers": [],
    }


class BuildPlayerIdentityLifecycleAnchorStaticReportTests(unittest.TestCase):
    def run_tool(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"tool failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_builds_static_report_from_repo_fixtures_and_static_orientation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_path = root / "static-orientation.json"
            output_path = root / "lifecycle-static-report.json"
            static_path.write_text(json.dumps(static_report()), encoding="utf-8")

            result = self.run_tool(
                [
                    "--static-orientation-report",
                    str(static_path),
                    "--output",
                    str(output_path),
                    "--json",
                ]
            )

            stdout_payload = json.loads(result.stdout)
            output_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(stdout_payload, output_payload)
        self.assertEqual("obelisk.players-identity-lifecycle-anchor-static-report.v1", output_payload["schema"])
        self.assertTrue(output_payload["ready"])
        self.assertTrue(output_payload["accepted_for_lifecycle_anchor_binding"])
        self.assertEqual("static_accepted", output_payload["corroboration_status"])
        self.assertFalse(output_payload["promotion_ready"])
        self.assertFalse(output_payload["public_sdk_ready"])
        self.assertFalse(output_payload["runtime_ready"])
        self.assertFalse(output_payload["server_operations_authorized"])
        self.assertEqual(
            {"ShooterGameMode.HandleNewPlayer", "ShooterGameMode.OnLogout"},
            {target["target"] for target in output_payload["accepted_targets"]},
        )
        self.assertEqual(
            {
                "ShooterGameMode.HandleNewPlayer": "a9b3049dc221f128924ff0c6eb45287bf630dfaea4e4ab33bbf93647a5d3361b",
                "ShooterGameMode.OnLogout": "e79e416a408bbe652a31f58c710cfeb03daa0acf2e0ebef55a7ba61c83a414aa",
            },
            {target["target"]: target["source_snapshot_sha256"] for target in output_payload["accepted_targets"]},
        )
        self.assertEqual(
            [
                "artifact_sha256:62d1768fd5962ee9270641f0a340dc04dc15edde53eacefbf247eff37e5bed78",
                "capture_id:base-identity-core",
                "evidence_pack_id:player-identity-base-core-evidence-pack",
            ],
            output_payload["artifact_identity"]["source_artifact_ids"],
        )
        self.assertIn("does not fabricate runtime evidence", " ".join(output_payload["non_claims"]))

    def test_fails_closed_without_static_evidence(self) -> None:
        result = self.run_tool(["--json"], check=False)
        payload = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertFalse(payload["ready"])
        self.assertFalse(payload["accepted_for_lifecycle_anchor_binding"])
        self.assertIn("static_orientation_report_missing", payload["blockers"])
        self.assertFalse(payload["promotion_ready"])
        self.assertFalse(payload["runtime_ready"])

    def test_rejects_protected_static_orientation_report_path(self) -> None:
        result = self.run_tool(
            ["--static-orientation-report", "/servidor/ark/workspace-offline/static-orientation.json"],
            check=False,
        )

        self.assertEqual(1, result.returncode)
        self.assertIn("must not read from protected server root", result.stderr)

    def test_rejects_static_orientation_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_payload = static_report()
            static_payload["runtime_ready"] = True
            static_path = root / "static-orientation.json"
            static_path.write_text(json.dumps(static_payload), encoding="utf-8")

            result = self.run_tool(["--static-orientation-report", str(static_path), "--json"], check=False)

        payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("static_orientation_runtime_ready_not_false", payload["blockers"])
        self.assertFalse(payload["ready"])


if __name__ == "__main__":
    unittest.main()
