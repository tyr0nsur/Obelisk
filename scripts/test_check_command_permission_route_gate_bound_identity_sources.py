#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate_bound_identity_sources.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate_bound_identity_sources.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_lifecycle_anchor_candidates import accepted_lifecycle_anchor_manifest
from test_check_player_identity_principal_invalidation_policy import manifest as principal_policy_manifest


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


class CheckCommandPermissionRouteGateBoundIdentitySourcesTests(unittest.TestCase):
    def run_checker(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_transient_bound_route_advances_only_to_runtime_evidence_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
            write_json(principal_path, principal_policy_manifest())

            result = self.run_checker(
                [
                    "--lifecycle-anchor-candidates-manifest",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--json",
                ]
            )

        report = json.loads(result.stdout)
        self.assertEqual(0, result.returncode)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["binding_report"]["ready"])
        self.assertEqual([], report["binding_report"]["blockers"])
        self.assertEqual("approved_runtime_evidence_missing", report["critical_path_phase"]["current_blocker"])
        self.assertEqual(
            ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
            report["route_lock"]["blocked_until"],
        )
        route = report["route_gate"]["report"]
        self.assertTrue(route["valid"])
        self.assertTrue(route["planning_only"])
        self.assertFalse(route["promotion_ready"])
        self.assertFalse(route["public_sdk_ready"])
        self.assertFalse(route["public_abi_ready"])
        self.assertFalse(route["runtime_ready"])
        self.assertFalse(route["public_header_allowed"])
        phase = route["critical_path_phase"]
        self.assertEqual("approved_runtime_evidence_missing", phase["current_blocker"])
        self.assertFalse(phase["permissions_admin_unlocked"])
        self.assertFalse(phase["command_response_unlocked"])
        self.assertFalse(phase["commands_replies_unlocked"])
        self.assertFalse(phase["source_checker_ready"])
        self.assertFalse(phase["source_checker_accepted_for_internal_planning"])
        self.assertIn("no runtime or server operation was performed", report["non_claims"])

    def test_rejects_partial_manifest_inputs_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lifecycle_path = Path(temp_dir) / "players-identity-lifecycle-anchor-candidates.json"
            write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
            result = self.run_checker(
                [
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(2, result.returncode)
        self.assertIn("the following arguments are required", result.stderr)

    def test_rejects_invalid_lifecycle_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            lifecycle = accepted_lifecycle_anchor_manifest()
            lifecycle["public_sdk_ready"] = True
            write_json(lifecycle_path, lifecycle)
            write_json(principal_path, principal_policy_manifest())
            result = self.run_checker(
                [
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("public_sdk_ready_not_false", result.stderr)


if __name__ == "__main__":
    unittest.main()
