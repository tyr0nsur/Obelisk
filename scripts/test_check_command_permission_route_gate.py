#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate.py"
QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

SPEC = importlib.util.spec_from_file_location("check_command_permission_route_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ROUTE_GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE_GATE)

import build_redacted_ufunction_signatures
from test_check_player_identity_lifecycle_anchor_candidates import accepted_lifecycle_anchor_manifest
from test_check_player_identity_principal_invalidation_policy import manifest as principal_policy_manifest


class CommandPermissionRouteGateTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_identity_lock_mode_requires_default_route_to_stay_unbound(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
        )
        phase = {
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_primary_blocker": "approved_runtime_evidence_missing",
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'approved_runtime_evidence_missing'!='lifecycle_anchor_first_evidence_provenance_unbound'",
            blockers,
        )
        self.assertIn(
            "critical_path_identity_readiness_mode_unexpected_blocker:'approved_runtime_evidence_missing'!='lifecycle_anchor_first_evidence_provenance_unbound'",
            blockers,
        )

    def test_identity_lock_mode_requires_bound_route_to_reach_runtime_blocker(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
        )
        phase = {
            "current_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'lifecycle_anchor_first_evidence_provenance_unbound'!='approved_runtime_evidence_missing'",
            blockers,
        )
        self.assertIn(
            "critical_path_identity_readiness_mode_unexpected_blocker:'lifecycle_anchor_first_evidence_provenance_unbound'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_accepts_current_route_as_planning_only(self) -> None:
        result = self.run_checker("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )
        self.assertEqual(8, len(report["checks"]))
        self.assertEqual(
            {
                "current_surface": "obelisk.player_identity.v1",
                "current_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
                "next_action": "bind_lifecycle_anchor_and_principal_policy_sources",
                "next_after_runtime_evidence": "identity_public_contract_gate_missing",
                "permissions_admin_unlocked": False,
                "command_response_unlocked": False,
                "commands_replies_unlocked": False,
                "source_checker": "check_player_identity_first_evidence_readiness.py",
                "source_checker_exit_code": 1,
                "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
                "source_checker_parse_error": None,
                "source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
                "source_checker_next_blocker": None,
                "source_checker_status": "blocked",
                "source_checker_ready": False,
                "source_checker_accepted_for_internal_planning": False,
                "source_checker_blockers": [
                    "lifecycle_anchor_first_evidence_provenance_unbound",
                    "accepted_lifecycle_anchors_missing",
                ],
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
            },
            report["critical_path_phase"],
        )
        self.assertEqual(
            {
                "locked": True,
                "blocked_until": [
                    "bound_lifecycle_anchor_and_principal_policy_sources",
                    "reviewed_identity_public_contract",
                ],
                "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
            },
            report["route_lock"],
        )
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("player_identity_public_contract_gap", check_names)
        self.assertIn("command_copied_response_intent_lifecycle_planning", check_names)
        commands_replies_check = next(
            check for check in report["checks"] if check["name"] == "commands_replies_public_readiness"
        )
        self.assertIn("--response-path-report", commands_replies_check["argv"])
        self.assertEqual([], report["blockers"])
        for check in report["checks"]:
            self.assertTrue(check["valid"], check)
            self.assertEqual([], check["public_or_runtime_claims"], check)
            self.assertEqual(check["expected_schema"], check["report_schema"], check)

    def test_accepts_bound_player_identity_planning_sources_as_planning_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence()
            first_evidence_path = root / "players-identity-first-evidence.json"
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            bound_dir = root / "bound"
            lifecycle = accepted_lifecycle_anchor_manifest()
            lifecycle["artifact_identity"]["source_artifact_ids"] = first_evidence["artifact_identity"][
                "source_artifact_ids"
            ]
            first_evidence_path.write_text(json.dumps(first_evidence), encoding="utf-8")
            lifecycle_path.write_text(json.dumps(lifecycle), encoding="utf-8")
            principal_path.write_text(json.dumps(principal_policy_manifest()), encoding="utf-8")
            binder = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "bind_player_identity_planning_sources.py"),
                    "--first-evidence",
                    str(first_evidence_path),
                    "--lifecycle-anchor-candidates",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--output-dir",
                    str(bound_dir),
                    "--json",
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, binder.returncode, binder.stderr)

            result = self.run_checker(
                "--lifecycle-anchor-candidates-manifest",
                str(bound_dir / "players-identity-lifecycle-anchor-candidates.json"),
                "--principal-invalidation-policy-manifest",
                str(bound_dir / "players-identity-principal-invalidation-policy.json"),
                "--json",
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
        self.assertEqual([], report["blockers"])
        phase = report["critical_path_phase"]
        self.assertEqual("approved_runtime_evidence_missing", phase["current_blocker"])
        self.assertEqual("approved_runtime_evidence_missing", phase["source_checker_primary_blocker"])
        self.assertEqual("produce_approved_runtime_principal_lifecycle_evidence", phase["next_action"])
        self.assertEqual("identity_public_contract_gate_missing", phase["next_after_runtime_evidence"])
        self.assertFalse(phase["permissions_admin_unlocked"])
        self.assertFalse(phase["command_response_unlocked"])
        self.assertFalse(phase["commands_replies_unlocked"])
        self.assertFalse(phase["promotion_ready"])
        self.assertFalse(phase["public_sdk_ready"])
        self.assertFalse(phase["public_abi_ready"])
        self.assertFalse(phase["runtime_ready"])
        self.assertFalse(phase["source_checker_ready"])
        self.assertFalse(phase["source_checker_accepted_for_internal_planning"])
        self.assertIn("approved_runtime_evidence_missing", phase["source_checker_blockers"])
        self.assertEqual(
            ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
            report["route_lock"]["blocked_until"],
        )
        for check in report["checks"]:
            self.assertTrue(check["valid"], check)
            self.assertEqual([], check["public_or_runtime_claims"], check)

    def test_rejects_partial_bound_player_identity_planning_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lifecycle_path = Path(temp_dir) / "players-identity-lifecycle-anchor-candidates.json"
            lifecycle_path.write_text("{}", encoding="utf-8")
            result = self.run_checker(
                "--lifecycle-anchor-candidates-manifest",
                str(lifecycle_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn(
            "player_identity_first_evidence_readiness: lifecycle/principal planning manifests must be supplied together",
            report["blockers"],
        )

    def test_rejects_broken_query_contract_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            query_contract = Path(tmp) / "permissions_admin_query_failclosed_contract.json"
            payload = json.loads(QUERY_CONTRACT.read_text(encoding="utf-8"))
            payload["schema"] = "wrong-schema"
            query_contract.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(
                "--query-failclosed-artifact",
                str(query_contract),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(report["valid"])
            self.assertFalse(report["accepted_for_planning"])
            self.assertTrue(any("permissions_query_failclosed" in blocker for blocker in report["blockers"]))

    def test_rejects_identity_public_contract_gap_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            decisions = Path(tmp) / "player_identity_public_contract_decisions.json"
            payload = json.loads(IDENTITY_DECISIONS.read_text(encoding="utf-8"))
            payload["public_header_allowed"] = True
            decisions.write_text(json.dumps(payload), encoding="utf-8")

            result = self.run_checker(
                "--player-identity-decisions",
                str(decisions),
                "--json",
                check=False,
            )
            report = json.loads(result.stdout)

            self.assertNotEqual(0, result.returncode)
            self.assertFalse(report["valid"])
            self.assertFalse(report["accepted_for_planning"])
            self.assertTrue(
                any("player_identity_public_contract_gap" in blocker for blocker in report["blockers"])
            )

    def test_critical_path_phase_accepts_allowed_identity_lock_blockers(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "source_checker_primary_blocker": "approved_runtime_evidence_missing",
            "source_checker_exit_code": 1,
            "source_checker_status": "blocked",
            "source_checker_ready": False,
            "source_checker_accepted_for_internal_planning": False,
            "source_checker_blockers": ["approved_runtime_evidence_missing"],
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

        phase["current_blocker"] = "lifecycle_anchor_first_evidence_provenance_unbound"
        phase["source_checker_primary_blocker"] = "lifecycle_anchor_first_evidence_provenance_unbound"
        phase["source_checker_blockers"] = ["lifecycle_anchor_first_evidence_provenance_unbound"]
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

        phase["source_checker_primary_blocker"] = "approved_runtime_evidence_missing"
        phase["current_blocker"] = "identity_public_contract_gate_missing"
        phase["source_checker_primary_blocker"] = "identity_public_contract_gate_missing"
        phase["source_checker_blockers"] = ["identity_public_contract_gate_missing"]
        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))

        phase["current_blocker"] = "identity_public_contract_gate"
        phase["source_checker_primary_blocker"] = "identity_public_contract_gate"
        phase["source_checker_blockers"] = ["identity_public_contract_gate"]
        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIn("critical_path_identity_gate_unexpected_blocker", blockers)

    def test_critical_path_phase_rejects_unlocked_commands_or_unknown_blocker(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "unexpected",
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "source_checker_primary_blocker": "unexpected",
            "source_checker_exit_code": 1,
            "source_checker_status": "blocked",
            "source_checker_ready": False,
            "source_checker_accepted_for_internal_planning": False,
            "source_checker_blockers": ["unexpected"],
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIn("critical_path_identity_gate_unexpected_blocker", blockers)
        self.assertIn("critical_path_commands_replies_unlocked_must_stay_false", blockers)

    def test_critical_path_phase_requires_primary_blocker_in_child_blockers(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_blockers": [],
            "source_checker_exit_code": 1,
            "source_checker_status": "blocked",
            "source_checker_ready": False,
            "source_checker_accepted_for_internal_planning": False,
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)

        self.assertIn("critical_path_identity_readiness_primary_blocker_not_in_blockers", blockers)
        phase.pop("source_checker_blockers")
        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIn("critical_path_identity_readiness_blockers_missing", blockers)

    def test_critical_path_phase_rejects_unparsable_or_schema_drifted_identity_readiness(self) -> None:
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_schema": "wrong-schema",
            "source_checker_parse_error": "stdout_json_decode_error: broken",
            "source_checker_primary_blocker": "approved_runtime_evidence_missing",
            "source_checker_exit_code": 1,
            "source_checker_status": "blocked",
            "source_checker_ready": False,
            "source_checker_accepted_for_internal_planning": False,
            "source_checker_blockers": ["approved_runtime_evidence_missing"],
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)

        self.assertIn("critical_path_identity_readiness_schema_mismatch", blockers)
        self.assertIn("critical_path_identity_readiness_output_invalid", blockers)

    def test_build_critical_path_phase_rejects_missing_identity_readiness_blocker(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                    }
                ),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase()
        finally:
            ROUTE_GATE.subprocess.run = original_run

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIsNone(phase["current_blocker"])
        self.assertIn("critical_path_identity_readiness_blocker_missing", blockers)
        self.assertIn("critical_path_identity_gate_unexpected_blocker", blockers)

    def test_build_critical_path_phase_forwards_bound_identity_artifacts(self) -> None:
        original_run = ROUTE_GATE.subprocess.run
        seen_argv: list[str] = []

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal seen_argv
            seen_argv = list(args[0])
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "primary_blocker": "approved_runtime_evidence_missing",
                        "blockers": ["approved_runtime_evidence_missing"],
                        "status": "blocked",
                        "ready": False,
                        "accepted_for_internal_planning": False,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                    }
                ),
                stderr="",
            )

        args = SimpleNamespace(
            player_identity_artifact_root=Path("/tmp/identity-artifacts"),
            player_identity_snapshot_root=Path("/tmp/identity-snapshots"),
            player_identity_candidate_root=Path("/tmp/identity-candidate"),
            player_identity_lifecycle_anchor_candidates_manifest=Path("/tmp/bound/lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("/tmp/bound/principal.json"),
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=None,
        )
        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase(args)
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertEqual([], ROUTE_GATE.validate_critical_path_phase(phase))
        self.assertEqual("approved_runtime_evidence_missing", phase["current_blocker"])
        self.assertEqual("produce_approved_runtime_principal_lifecycle_evidence", phase["next_action"])
        for flag, expected in (
            ("--artifact-root", "/tmp/identity-artifacts"),
            ("--snapshot-root", "/tmp/identity-snapshots"),
            ("--candidate-root", "/tmp/identity-candidate"),
            ("--lifecycle-anchor-candidates-manifest", "/tmp/bound/lifecycle.json"),
            ("--principal-invalidation-policy-manifest", "/tmp/bound/principal.json"),
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, seen_argv)
                self.assertEqual(expected, seen_argv[seen_argv.index(flag) + 1])

    def test_build_critical_path_phase_rejects_identity_readiness_overclaim_flags(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "primary_blocker": "approved_runtime_evidence_missing",
                        "blockers": ["approved_runtime_evidence_missing"],
                        "status": "blocked",
                        "ready": False,
                        "accepted_for_internal_planning": False,
                        "promotion_ready": True,
                        "public_sdk_ready": True,
                        "public_abi_ready": True,
                        "runtime_ready": True,
                    }
                ),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase()
        finally:
            ROUTE_GATE.subprocess.run = original_run

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertEqual("approved_runtime_evidence_missing", phase["current_blocker"])
        self.assertEqual(4, blockers.count("critical_path_identity_readiness_ready_flag_overclaim"))

    def test_build_critical_path_phase_rejects_identity_ready_overclaim_even_with_current_blocker(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "primary_blocker": "approved_runtime_evidence_missing",
                        "blockers": ["approved_runtime_evidence_missing"],
                        "status": "ready",
                        "ready": True,
                        "accepted_for_internal_planning": True,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                    }
                ),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase()
        finally:
            ROUTE_GATE.subprocess.run = original_run

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        self.assertIn("critical_path_identity_readiness_exit_code_unexpected", blockers)
        self.assertIn("critical_path_identity_readiness_status_unexpected", blockers)
        self.assertGreaterEqual(blockers.count("critical_path_identity_readiness_ready_flag_overclaim"), 2)

    def test_route_check_requires_explicit_valid_true(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps({"schema": "obelisk.player-identity-public-contract-gap-report.v1"}),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("player_identity_public_contract_gap", ["fake-check", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])

    def test_route_check_rejects_child_blockers_even_when_valid_true(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=0,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.command-chat-response-public-readiness-check.v1",
                        "valid": True,
                        "accepted_for_planning": True,
                        "planning_only": True,
                        "blockers": ["masked_dependency_provenance_gap"],
                    }
                ),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("command_chat_response_public_readiness", ["fake-check", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertEqual(["masked_dependency_provenance_gap"], result["blockers"])

    def test_route_rejects_caller_supplied_command_response_readiness_without_root(self) -> None:
        args = SimpleNamespace(
            command_response_root=None,
            command_response_readiness=Path("/tmp/synthetic-readiness.json"),
        )

        blockers = ROUTE_GATE.validate_command_response_readiness_binding(args)

        self.assertEqual(
            ["command_chat_response_public_readiness: caller-supplied readiness requires --command-response-root"],
            blockers,
        )

    def test_route_rejects_command_response_readiness_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "root"
            stale = Path(temp_dir) / "stale"
            root.mkdir()
            stale.mkdir()
            args = SimpleNamespace(
                command_response_root=root,
                command_response_readiness=stale / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME,
            )

            blockers = ROUTE_GATE.validate_command_response_readiness_binding(args)

        self.assertEqual(
            [
                "command_chat_response_public_readiness: caller-supplied readiness is not bound to "
                "--command-response-root"
            ],
            blockers,
        )

    def test_route_accepts_command_response_readiness_bound_to_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "root"
            root.mkdir()
            args = SimpleNamespace(
                command_response_root=root,
                command_response_readiness=root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME,
            )

            blockers = ROUTE_GATE.validate_command_response_readiness_binding(args)

        self.assertEqual([], blockers)

    def test_route_rejects_command_response_child_readiness_context_split_from_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()
            args = SimpleNamespace(
                command_response_root=None,
                command_response_readiness=None,
            )
            payload = {
                "readiness_root": str(expected_root),
                "readiness_path": str(stale_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME),
            }

            blockers = ROUTE_GATE.validate_command_response_child_readiness_context(args, payload)

        self.assertEqual(
            ["command_chat_response_public_readiness: child readiness_path is not bound to readiness_root"],
            blockers,
        )

    def test_route_rejects_command_response_child_readiness_context_mismatching_caller(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()
            args = SimpleNamespace(
                command_response_root=expected_root,
                command_response_readiness=expected_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME,
            )
            payload = {
                "readiness_root": str(stale_root),
                "readiness_path": str(stale_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME),
            }

            blockers = ROUTE_GATE.validate_command_response_child_readiness_context(args, payload)

        self.assertEqual(
            [
                "command_chat_response_public_readiness: child readiness_root does not match caller root",
                "command_chat_response_public_readiness: child readiness_path does not match caller readiness",
            ],
            blockers,
        )

    def test_route_check_rejects_schema_drift_even_when_otherwise_valid(self) -> None:
        original = ROUTE_GATE.run_check

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            result = original(name, argv)
            if name == "permissions_query_failclosed":
                result["report_schema"] = "obelisk.permissions-admin-query-failclosed-contract-check.v999"
                result["valid"] = True
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            player_identity_artifact_root=None,
            player_identity_snapshot_root=None,
            player_identity_candidate_root=None,
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "permissions_query_failclosed: schema mismatch "
            "'obelisk.permissions-admin-query-failclosed-contract-check.v999' != "
            "'obelisk.permissions-admin-query-failclosed-contract-check.v1'",
            report["blockers"],
        )

    def test_route_check_rejects_public_command_reply_alias_claims(self) -> None:
        original = ROUTE_GATE.run_check

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            result = original(name, argv)
            if name == "commands_replies_public_readiness":
                result["valid"] = False
                result["public_or_runtime_claims"] = [
                    "public_command_router_allowed",
                    "public_reply_or_send_chat_abi_allowed",
                ]
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            player_identity_artifact_root=None,
            player_identity_snapshot_root=None,
            player_identity_candidate_root=None,
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "commands_replies_public_readiness: unexpected public/runtime claim: "
            "public_command_router_allowed, public_reply_or_send_chat_abi_allowed",
            report["blockers"],
        )

    def test_collect_public_or_runtime_claims_rejects_runtime_ready_text_variants(self) -> None:
        for text in ("runtime ready", "runtime is ready", "runtime readiness enabled"):
            with self.subTest(text=text):
                claims = ROUTE_GATE.collect_public_or_runtime_claims({"claim": text})
                self.assertEqual(["claim:positive_text_claim"], claims)

    def test_collect_public_or_runtime_claims_accepts_negated_runtime_ready_text(self) -> None:
        for text in ("runtime readiness remains blocked", "runtime ready remains blocked"):
            with self.subTest(text=text):
                claims = ROUTE_GATE.collect_public_or_runtime_claims({"claim": text})
                self.assertEqual([], claims)

    def test_route_check_rejects_child_report_that_drops_planning_only_posture(self) -> None:
        original = ROUTE_GATE.run_check

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            result = original(name, argv)
            if name == "commands_replies_public_readiness":
                result["planning_only"] = False
                result["accepted_for_planning"] = True
                result["valid"] = False
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            player_identity_artifact_root=None,
            player_identity_snapshot_root=None,
            player_identity_candidate_root=None,
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("commands_replies_public_readiness: planning_only must stay true", report["blockers"])
        self.assertIn("commands_replies_public_readiness: invalid route prerequisite", report["blockers"])

    def test_run_check_rejects_planning_only_child_report_posture_drift(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        for planning_only, accepted_for_planning in ((False, True), (True, False)):
            with self.subTest(planning_only=planning_only, accepted_for_planning=accepted_for_planning):

                def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                    report = {
                        "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"],
                        "valid": True,
                        "accepted_for_planning": accepted_for_planning,
                        "planning_only": planning_only,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                    }
                    return subprocess.CompletedProcess(
                        args=[],
                        returncode=0,
                        stdout=json.dumps(report),
                        stderr="",
                    )

                try:
                    ROUTE_GATE.subprocess.run = fake_run
                    result = ROUTE_GATE.run_check("commands_replies_public_readiness", ["unused.py", "--json"])
                finally:
                    ROUTE_GATE.subprocess.run = original_run

                self.assertFalse(result["valid"])
                self.assertEqual(planning_only, result["planning_only"])
                self.assertEqual(accepted_for_planning, result["accepted_for_planning"])
                self.assertEqual([], result["public_or_runtime_claims"])

    def test_run_check_rejects_required_planning_only_child_missing_valid_field(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"],
                "accepted_for_planning": True,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("commands_replies_public_readiness", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertTrue(result["planning_only"])
        self.assertTrue(result["accepted_for_planning"])
        self.assertEqual([], result["public_or_runtime_claims"])

    def test_route_gate_composes_response_path_report_into_commands_replies(self) -> None:
        original = ROUTE_GATE.run_check
        seen_response_path_report = False

        def base_result(name: str, argv: list[str]) -> dict[str, object]:
            return {
                "name": name,
                "argv": argv,
                "exit_code": 0,
                "valid": True,
                "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "planning_only": True,
                "accepted_for_planning": True,
                "public_or_runtime_claims": [],
                "blockers": [],
                "parse_error": None,
                "stderr": "",
                "report_payload": {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                },
            }

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            nonlocal seen_response_path_report
            result = base_result(name, argv)
            if name == "command_chat_response_public_readiness":
                result["report_payload"] = {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "surface": "obelisk.command_chat_response_path.v1",
                    "target_set": "command-chat-response-intake",
                    "target_filters": [
                        "ShooterPlayerController.ServerSendChatMessage",
                        "ShooterPlayerController.ServerChatMessage_Impl",
                    ],
                    "readiness_status": "compared",
                    "decisions_status": "blocked",
                    "blockers": [],
                    "public_readiness_ready": False,
                    "public_header_allowed": False,
                    "promotion_ready": True,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                }
            if name == "commands_replies_public_readiness":
                self.assertIn("--response-path-report", argv)
                report_path = Path(argv[argv.index("--response-path-report") + 1])
                composed = json.loads(report_path.read_text(encoding="utf-8"))
                seen_response_path_report = True
                if composed.get("promotion_ready") is True:
                    result["valid"] = False
                    result["exit_code"] = 1
                    result["blockers"] = ["response_path_report_promotion_ready_not_false"]
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            json=True,
        )
        try:
            ROUTE_GATE.run_check = fake_run_check
            report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertTrue(seen_response_path_report)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("commands_replies_public_readiness: checker exited 1", report["blockers"])
        self.assertIn("commands_replies_public_readiness: invalid route prerequisite", report["blockers"])

    def test_route_gate_rejects_split_command_response_child_context_even_if_children_pass(self) -> None:
        original = ROUTE_GATE.run_check
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            expected_root = base / "expected-root"
            stale_root = base / "stale-root"
            expected_root.mkdir()
            stale_root.mkdir()

            def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
                report_payload = {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                    "blockers": [],
                }
                if name == "command_chat_response_public_readiness":
                    report_payload.update(
                        {
                            "readiness_root": str(expected_root),
                            "readiness_path": str(
                                stale_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME
                            ),
                        }
                    )
                return {
                    "name": name,
                    "argv": argv,
                    "exit_code": 0,
                    "valid": True,
                    "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "planning_only": True,
                    "accepted_for_planning": True,
                    "public_or_runtime_claims": [],
                    "blockers": [],
                    "parse_error": None,
                    "stderr": "",
                    "report_payload": report_payload,
                }

            args = SimpleNamespace(
                query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
                player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
                public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
                player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
                public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
                command_response_root=None,
                command_response_readiness=None,
                player_identity_artifact_root=None,
                player_identity_snapshot_root=None,
                player_identity_candidate_root=None,
                player_identity_lifecycle_anchor_candidates_manifest=None,
                player_identity_principal_invalidation_policy_manifest=None,
                player_identity_runtime_principal_lifecycle_evidence_manifest=None,
                player_identity_approved_runtime_principal_lifecycle_evidence_manifest=None,
                json=True,
            )
            try:
                ROUTE_GATE.run_check = fake_run_check
                report = ROUTE_GATE.build_report(args)
            finally:
                ROUTE_GATE.run_check = original

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "command_chat_response_public_readiness: child readiness_path is not bound to readiness_root",
            report["blockers"],
        )

    def test_route_gate_forwards_shared_surfaces_and_header_to_p0_child_checks(self) -> None:
        args = SimpleNamespace(
            query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
            player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
            public_sdk_surfaces=Path("/tmp/route-surfaces.json"),
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=Path("/tmp/ObeliskApi.h"),
            command_response_root=None,
            command_response_readiness=None,
            json=True,
        )

        by_name = {name: argv for name, argv in ROUTE_GATE.route_checks(args)}
        for name in (
            "player_identity_public_contract_gap",
            "permissions_admin_public_readiness",
            "command_chat_response_public_readiness",
            "commands_replies_public_readiness",
        ):
            with self.subTest(name=name):
                self.assertIn("--surfaces", by_name[name])
                self.assertEqual("/tmp/route-surfaces.json", by_name[name][by_name[name].index("--surfaces") + 1])
                self.assertIn("--public-header", by_name[name])
                self.assertEqual("/tmp/ObeliskApi.h", by_name[name][by_name[name].index("--public-header") + 1])

    def test_route_gate_rejects_fake_public_header_in_downstream_p0_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            header_path = Path(temp_dir) / "ObeliskApi.h"
            header_path.write_text("/* fake clean header */\n", encoding="utf-8")
            result = self.run_checker("--public-header", str(header_path), "--json", check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertFalse(report["valid"])
        self.assertIn("command_chat_response_public_readiness: child blockers not empty", report["blockers"])
        self.assertIn("commands_replies_public_readiness: child blockers not empty", report["blockers"])

        by_name = {check["name"]: check for check in report["checks"]}
        self.assertIn(
            "public_header_path_mismatch",
            by_name["command_chat_response_public_readiness"]["blockers"],
        )
        self.assertIn(
            "public_header_path_mismatch",
            by_name["commands_replies_public_readiness"]["blockers"],
        )

    def test_route_gate_rejects_supplied_surfaces_promoting_commands_replies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            surfaces = json.loads(PUBLIC_SDK_SURFACES.read_text(encoding="utf-8"))
            surfaces["promoted_surfaces"].append("obelisk.commands_replies.v1")
            surfaces["planning_surfaces"] = [
                item for item in surfaces["planning_surfaces"] if item != "obelisk.commands_replies.v1"
            ]
            for surface in surfaces["surfaces"]:
                if surface.get("id") == "obelisk.commands_replies.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "stable"
                    surface["public_contract"] = ["RegisterCommand", "ReplyToCommand"]
                    break
            surfaces_path = root / "public_sdk_surfaces.json"
            surfaces_path.write_text(json.dumps(surfaces), encoding="utf-8")

            result = self.run_checker(
                "--public-sdk-surfaces",
                str(surfaces_path),
                "--json",
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("commands_replies_public_readiness" in blocker for blocker in report["blockers"]),
            report["blockers"],
        )

    def test_run_check_recursively_rejects_subreport_public_alias_and_text_claims(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"],
                "valid": True,
                "nested": {
                    "public_reply_abi_allowed": True,
                    "publicReplyAbiReady": True,
                    "public_send_chat_abi_allowed": "ready",
                    "public-response-path-ready": True,
                    "reply_allowed": 1,
                    "send_chat_allowed": "true",
                    "send chat ready": True,
                    "reply_send_chat_router_claims_allowed": True,
                    "commandRouterAllowed": True,
                    "public_abi_allowed": "ready",
                    "publicAbiReady": True,
                    "runtimeReady": True,
                    "permissions-admin-ready": True,
                    "publicBridgeAbiAllowed": True,
                    "public response abi allowed": True,
                    "authorityClaimSource": "command text",
                    "principal-source": {"source": "operator-config"},
                    "public-reply-api": True,
                    "publicSendChatApi": True,
                    "permissions_admin_ready": True,
                    "notes": [
                        "public ABI is ready",
                        "send-chat ABI is public and ready",
                        "command routing is public and ready",
                        "permissions/admin is public and ready",
                        "replies API is public and ready",
                        "command response path is live",
                        "reply endpoint is live",
                        "send chat API is operational",
                    ],
                },
            }
            return subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(report),
                stderr="",
            )

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("commands_replies_public_readiness", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertIn("nested.public_reply_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.publicReplyAbiReady", result["public_or_runtime_claims"])
        self.assertIn("nested.public_send_chat_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public-response-path-ready", result["public_or_runtime_claims"])
        self.assertIn("nested.reply_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.send_chat_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.send chat ready", result["public_or_runtime_claims"])
        self.assertIn("nested.reply_send_chat_router_claims_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.commandRouterAllowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public_abi_allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.publicAbiReady", result["public_or_runtime_claims"])
        self.assertIn("nested.runtimeReady", result["public_or_runtime_claims"])
        self.assertIn("nested.permissions-admin-ready", result["public_or_runtime_claims"])
        self.assertIn("nested.publicBridgeAbiAllowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public response abi allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.authorityClaimSource", result["public_or_runtime_claims"])
        self.assertIn("nested.principal-source", result["public_or_runtime_claims"])
        self.assertIn("nested.public-reply-api", result["public_or_runtime_claims"])
        self.assertIn("nested.publicSendChatApi", result["public_or_runtime_claims"])
        self.assertIn("nested.permissions_admin_ready", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[0]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[1]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[2]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[3]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[4]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[5]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[6]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[7]:positive_text_claim", result["public_or_runtime_claims"])


if __name__ == "__main__":
    unittest.main()
