#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate_bound_identity_sources.py."""

from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate_bound_identity_sources.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_command_permission_route_gate_bound_identity_sources", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)

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

    def build_args(self, lifecycle_path: Path, principal_path: Path) -> SimpleNamespace:
        return SimpleNamespace(
            snapshot_root=CHECKER.build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
            lifecycle_anchor_candidates=lifecycle_path,
            principal_invalidation_policy=principal_path,
            candidate_root=None,
            artifact_root=None,
            query_failclosed_artifact=CHECKER.route_gate.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=CHECKER.route_gate.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=CHECKER.route_gate.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=CHECKER.route_gate.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=CHECKER.route_gate.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            json=True,
        )

    def base_route_report(self) -> dict:
        return {
            "schema": "obelisk.command-permission-route-gate-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "critical_path_phase": {
                "current_blocker": "approved_runtime_evidence_missing",
                "source_checker_primary_blocker": "approved_runtime_evidence_missing",
                "source_checker_status": "blocked",
                "source_checker_ready": False,
                "source_checker_accepted_for_internal_planning": False,
            },
            "route_lock": {
                "locked": True,
                "blocked_until": [
                    "approved_runtime_principal_lifecycle_evidence",
                    "reviewed_identity_public_contract",
                ],
            },
            "blockers": [],
        }

    def run_with_fake_route_report(self, route_report: dict) -> dict:
        original = CHECKER.run_route_gate
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
                principal_path = root / "players-identity-principal-invalidation-policy.json"
                write_json(lifecycle_path, accepted_lifecycle_anchor_manifest())
                write_json(principal_path, principal_policy_manifest())

                def fake_run_route_gate(*_args: object, **_kwargs: object) -> tuple[int, dict, str, None]:
                    return 0, route_report, "", None

                CHECKER.run_route_gate = fake_run_route_gate
                return CHECKER.build_report(self.build_args(lifecycle_path, principal_path))
        finally:
            CHECKER.run_route_gate = original

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

    def test_rejects_route_gate_valid_true_with_bound_provenance_drift(self) -> None:
        cases = (
            (
                lambda report: report["critical_path_phase"].update(
                    {"source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound"}
                ),
                "route_gate_bound_identity_primary_blocker_unexpected",
            ),
            (
                lambda report: report["critical_path_phase"].update({"source_checker_ready": True}),
                "route_gate_identity_readiness_ready_flag_overclaim",
            ),
            (
                lambda report: report["critical_path_phase"].update({"source_checker_status": "ready"}),
                "route_gate_identity_readiness_status_unexpected",
            ),
            (
                lambda report: report["critical_path_phase"].update(
                    {"source_checker_accepted_for_internal_planning": True}
                ),
                "route_gate_identity_readiness_internal_planning_overclaim",
            ),
            (
                lambda report: report["route_lock"].update({"locked": False}),
                "route_gate_lock_unexpected",
            ),
            (
                lambda report: report["route_lock"].update({"blocked_until": ["reviewed_identity_public_contract"]}),
                "route_gate_lock_blocked_until_unexpected",
            ),
            (
                lambda report: report.update({"blockers": ["critical_path_identity_readiness_ready_flag_overclaim"]}),
                "route_gate_blockers_not_empty",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                route_report = self.base_route_report()
                mutate(route_report)

                report = self.run_with_fake_route_report(route_report)

                self.assertFalse(report["valid"])
                self.assertIn(expected, report["blockers"])

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
