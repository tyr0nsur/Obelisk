#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate_bound_identity_sources.py."""

from __future__ import annotations

import json
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_permission_route_gate_bound_identity_sources.py"
PLANNING_SOURCE_ROOT = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_command_permission_route_gate_bound_identity_sources", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CHECKER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CHECKER
SPEC.loader.exec_module(CHECKER)

def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def add_preflight_false_only_flags(payload_text: str) -> str:
    payload = json.loads(payload_text)
    for key in (
        "copied_log_presence_counts_as_approved_runtime_evidence",
        "dry_run_success_counts_as_approved_runtime_evidence",
        "historical_target_names_authorize_runtime",
        "marker_env_readiness_counts_as_approved_runtime_evidence",
        "player_notice_counts_as_approved_runtime_evidence",
        "public_reachability_counts_as_approved_runtime_evidence",
    ):
        payload[key] = False
    return json.dumps(payload, sort_keys=True) + "\n"


def planning_lifecycle_manifest() -> dict:
    return json.loads(
        (PLANNING_SOURCE_ROOT / "players-identity-lifecycle-anchor-candidates.json").read_text(encoding="utf-8")
    )


def planning_principal_manifest() -> dict:
    return json.loads(
        (PLANNING_SOURCE_ROOT / "players-identity-principal-invalidation-policy.json").read_text(encoding="utf-8")
    )


def route_manifest_sources(lifecycle: Path | None = None, principal: Path | None = None) -> dict:
    lifecycle = lifecycle or Path("/tmp/bound/players-identity-lifecycle-anchor-candidates.json")
    principal = principal or Path("/tmp/bound/players-identity-principal-invalidation-policy.json")
    return {
        "mode": "cli_bound",
        "report_available": True,
        "expected_manifests_received": True,
        "manifests": {
            "lifecycle_anchor_candidates": {
                "source": "cli_bound",
                "provided_by_cli": True,
                "expected_path": str(lifecycle),
                "expected_resolved_path": str(lifecycle.resolve()),
                "observed_path": str(lifecycle),
                "observed_resolved_path": str(lifecycle.resolve()),
                "matched": True,
            },
            "principal_invalidation_policy": {
                "source": "cli_bound",
                "provided_by_cli": True,
                "expected_path": str(principal),
                "expected_resolved_path": str(principal.resolve()),
                "observed_path": str(principal),
                "observed_resolved_path": str(principal.resolve()),
                "matched": True,
            },
        },
    }


def locked_downstream_child_checks(blocker: str, *, simulation: bool = False) -> list[dict]:
    checks = []
    for name in (
        "permissions_admin_public_readiness",
        "command_chat_response_public_readiness",
        "commands_replies_public_readiness",
    ):
        check = {
            "name": name,
            "dependency_chain_locked": True,
            "current_route_blocker": blocker,
            "remaining_route_blockers": [blocker],
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "public_or_runtime_accounting_allowed": False,
        }
        if simulation:
            check["present"] = True
        checks.append(check)
    return checks


def approved_runtime_route_diagnosis(path: Path) -> dict:
    return {
        "provided": True,
        "path": str(path.resolve()),
        "report_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "next_blocker": "identity_public_contract_gate_missing",
        "ready": True,
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "counts_toward_complete_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
        "public_or_runtime_accounting_allowed": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "remaining_blockers": [],
        "blockers": [],
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_start_rejected_anchor",
            "session_end_anchor",
        ],
        "consumer_cases": ["malformed_or_unsupported_evidence", "stale_after_logout"],
    }


def approved_runtime_check_report() -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "next_blocker": "identity_public_contract_gate_missing",
        "ready": True,
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "counts_toward_complete_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
        "public_or_runtime_accounting_allowed": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "remaining_blockers": [],
        "blockers": [],
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_start_rejected_anchor",
            "session_end_anchor",
        ],
        "consumer_cases": ["malformed_or_unsupported_evidence", "stale_after_logout"],
    }


def safe_post_evidence_p0_lock_simulation() -> dict:
    return {
        "schema": "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
        "simulation_only": True,
        "approved_runtime_evidence_accepted": True,
        "current_route_blocker": "identity_public_contract_gate_missing",
        "simulated_route_blocker_after_accepted_runtime_evidence": "identity_public_contract_gate_missing",
        "remaining_route_blockers_after_accepted_runtime_evidence": ["identity_public_contract_gate_missing"],
        "blocked_until_after_accepted_runtime_evidence": [
            "reviewed_identity_public_contract",
            "hash_current_identity_public_contract_decision_record",
        ],
        "identity_public_contract_required": True,
        "reviewed_identity_public_contract_required": True,
        "hash_current_identity_public_contract_decision_record_required": True,
        "permissions_admin_unlock_requires_reviewed_hash_current_identity_contract": True,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "permissions_admin_unlocked": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "public_or_runtime_accounting_allowed": False,
        "public_sdk_ready": False,
        "identity_public_contract_decision_record_contract_review_only": False,
        "identity_public_contract_decision_record_hash_current": False,
        "identity_public_contract_decision_record_reviewed": False,
        "reviewed_hash_current_contract_review_only": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "p0_child_checks": locked_downstream_child_checks(
            "identity_public_contract_gate_missing",
            simulation=True,
        ),
    }


def rejected_runtime_check_report(input_schema: str, reason: str) -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        "input_schema": input_schema,
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "ready": False,
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "counts_toward_complete_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
        "public_or_runtime_accounting_allowed": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "remaining_blockers": ["approved_runtime_evidence_not_accepted"],
        "blockers": [reason],
        "next_blocker": "approved_runtime_evidence_not_accepted",
        "observed_runtime_cases": [],
        "consumer_cases": [],
        "non_evidence_reasons": [reason],
    }


class CheckCommandPermissionRouteGateBoundIdentitySourcesTests(unittest.TestCase):
    def run_checker(
        self,
        args: list[str],
        *,
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def build_args(
        self,
        lifecycle_path: Path,
        principal_path: Path,
        *,
        approved_runtime_path: Path | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            snapshot_root=CHECKER.build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
            lifecycle_anchor_candidates=lifecycle_path,
            principal_invalidation_policy=principal_path,
            approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime_path,
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

    def base_route_report(self, *, blocker: str = "approved_runtime_evidence_missing") -> dict:
        blocked_until = (
            ["reviewed_identity_public_contract"]
            if blocker == "identity_public_contract_gate_missing"
            else ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"]
        )
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
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "public_or_runtime_accounting_allowed": False,
            "critical_path_phase": {
                "current_blocker": blocker,
                "source_checker_primary_blocker": blocker,
                "next_after_runtime_evidence": "identity_public_contract_gate_missing",
                "permissions_admin_unlocked": False,
                "command_response_unlocked": False,
                "commands_replies_unlocked": False,
                "source_checker_status": "blocked",
                "source_checker_ready": False,
                "source_checker_accepted_for_internal_planning": False,
                "source_checker_manifest_sources": route_manifest_sources(),
            },
            "route_lock": {
                "locked": True,
                "blocked_until": blocked_until,
            },
            "checks": locked_downstream_child_checks(blocker),
            "blockers": [],
        }

    def run_with_fake_route_report(
        self,
        route_report: dict,
        *,
        approved_runtime_path: Path | None = None,
        canonical_paths: bool = True,
        approved_runtime_check: tuple[bool, dict | None, int, str, str | None] | None = None,
        forwarded_approved_runtime: list[Path | None] | None = None,
    ) -> dict:
        original = CHECKER.run_route_gate
        original_approved_check = CHECKER.check_approved_runtime_evidence_manifest
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
                principal_path = root / "players-identity-principal-invalidation-policy.json"
                write_json(
                    lifecycle_path,
                    planning_lifecycle_manifest(),
                )
                write_json(principal_path, planning_principal_manifest())

                def fake_run_route_gate(*_args: object, **kwargs: object) -> tuple[int, dict, str, None]:
                    approved_runtime_forwarded = kwargs.get("approved_runtime")
                    if forwarded_approved_runtime is not None:
                        forwarded_approved_runtime.append(approved_runtime_forwarded)
                    if canonical_paths:
                        lifecycle_output = Path(kwargs["lifecycle_output"])
                        principal_output = Path(kwargs["principal_output"])
                        sources = route_report["critical_path_phase"].get("source_checker_manifest_sources")
                        if isinstance(sources, dict) and isinstance(sources.get("manifests"), dict):
                            sources["manifests"] = route_manifest_sources(
                                lifecycle=lifecycle_output,
                                principal=principal_output,
                            )["manifests"]
                    if approved_runtime_forwarded is not None and approved_runtime_path:
                        phase = route_report.get("critical_path_phase")
                        if isinstance(phase, dict):
                            phase.setdefault(
                                "source_checker_approved_runtime_evidence_manifest",
                                approved_runtime_route_diagnosis(Path(approved_runtime_forwarded)),
                            )
                    return 0, route_report, "", None

                CHECKER.run_route_gate = fake_run_route_gate
                if approved_runtime_check is not None:
                    CHECKER.check_approved_runtime_evidence_manifest = (
                        lambda *_args, **_kwargs: approved_runtime_check
                    )
                return CHECKER.build_report(
                    self.build_args(
                        lifecycle_path,
                        principal_path,
                        approved_runtime_path=approved_runtime_path,
                    )
                )
        finally:
            CHECKER.run_route_gate = original
            CHECKER.check_approved_runtime_evidence_manifest = original_approved_check

    def test_transient_bound_route_advances_only_to_runtime_evidence_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            write_json(
                lifecycle_path,
                planning_lifecycle_manifest(),
            )
            write_json(principal_path, planning_principal_manifest())

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
        self.assertTrue(report["route_blocked"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertEqual(
            "produce_approved_runtime_principal_lifecycle_evidence",
            report["next_route_action"],
        )
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["binding_report"]["ready"])
        self.assertEqual([], report["binding_report"]["blockers"])
        self.assertTrue(report["lifecycle_snapshot_root_binding"]["ready"])
        self.assertEqual([], report["lifecycle_snapshot_root_binding"]["blockers"])
        self.assertEqual("approved_runtime_evidence_missing", report["critical_path_phase"]["current_blocker"])
        self.assertEqual(
            ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
            report["route_lock"]["blocked_until"],
        )
        route = report["route_gate"]["report"]
        if report["route_gate"]["downstream_lock_failure_quarantined"]:
            self.assertFalse(route["valid"])
            self.assertIn(
                "command_principal_authz_response_bridge: invalid route prerequisite",
                route["blockers"],
            )
        else:
            self.assertTrue(route["valid"])
        self.assertTrue(route["planning_only"])
        self.assertFalse(route["promotion_ready"])
        self.assertFalse(route["public_sdk_ready"])
        self.assertFalse(route["public_abi_ready"])
        self.assertFalse(route["runtime_ready"])
        self.assertFalse(route["public_header_allowed"])
        phase = route["critical_path_phase"]
        self.assertEqual("approved_runtime_evidence_missing", phase["current_blocker"])
        self.assertEqual("cli_bound", phase["source_checker_manifest_sources"]["mode"])
        self.assertTrue(phase["source_checker_manifest_sources"]["expected_manifests_received"])
        self.assertFalse(phase["permissions_admin_unlocked"])
        self.assertFalse(phase["command_response_unlocked"])
        self.assertFalse(phase["commands_replies_unlocked"])
        self.assertFalse(phase["source_checker_ready"])
        self.assertFalse(phase["source_checker_accepted_for_internal_planning"])
        self.assertIn("no runtime or server operation was performed", report["non_claims"])

    def test_bound_route_rejects_contract_blocker_without_explicit_runtime_evidence(self) -> None:
        route_report = self.base_route_report()
        phase = route_report["critical_path_phase"]
        phase["current_blocker"] = "identity_public_contract_gate_missing"
        phase["source_checker_primary_blocker"] = "identity_public_contract_gate_missing"
        route_report["route_lock"]["blocked_until"] = [
            "reviewed_identity_public_contract",
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertIn("route_gate_bound_identity_blocker_unexpected", report["blockers"])
        self.assertIn("route_gate_bound_identity_primary_blocker_unexpected", report["blockers"])
        self.assertIn("route_gate_lock_blocked_until_unexpected", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["critical_path_phase"]["current_blocker"])

    def test_bound_route_rejects_contract_blocker_with_unaccepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            report = self.run_with_fake_route_report(
                self.base_route_report(blocker="identity_public_contract_gate_missing"),
                approved_runtime_path=approved_runtime,
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["server_operations_authorized"])
        self.assertFalse(report["runtime_work_authorized"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("route_gate_bound_identity_blocker_unexpected", report["blockers"])
        self.assertIn("route_gate_bound_identity_primary_blocker_unexpected", report["blockers"])
        self.assertIn("route_gate_lock_blocked_until_unexpected", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])

    def test_bound_route_allows_contract_blocker_with_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            report = self.run_with_fake_route_report(
                self.base_route_report(blocker="identity_public_contract_gate_missing"),
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

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
        self.assertTrue(report["route_blocked"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual("review_identity_public_contract", report["next_route_action"])
        self.assertEqual([], report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["critical_path_phase"]["current_blocker"])
        self.assertEqual(["reviewed_identity_public_contract"], report["route_lock"]["blocked_until"])
        self.assertTrue(report["approved_runtime_evidence_check"]["accepted"])

    def test_bound_route_quarantines_accepted_runtime_parent_lock_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report.update(
                {
                    "valid": False,
                    "accepted_for_planning": False,
                    "route_blocked": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                    "route_lock_invariant_valid": False,
                    "blockers": [
                        (
                            "player_identity_public_contract_gap: unexpected public/runtime claim: "
                            "post_approved_runtime_evidence_route_check, "
                            "post_approved_runtime_evidence_route_check.runtime_evidence_accepted"
                        ),
                        "player_identity_public_contract_gap: invalid route prerequisite",
                        "critical_path_identity_readiness_public_or_runtime_claim",
                    ],
                }
            )
            route_report["route_lock"]["invariant_valid"] = False
            route_report["critical_path_phase"][
                "source_checker_approved_runtime_evidence_manifest"
            ] = approved_runtime_route_diagnosis(approved_runtime)
            route_report["critical_path_phase"]["source_checker_public_or_runtime_claims"] = [
                "first_evidence_boundary.post_runtime_fast_path_inputs.approved_runtime_evidence_ready",
            ]
            route_report["checks"].insert(
                0,
                {
                    "name": "player_identity_public_contract_gap",
                    "valid": False,
                    "public_or_runtime_claims": [
                        "post_approved_runtime_evidence_route_check",
                        "post_approved_runtime_evidence_route_check.runtime_evidence_accepted",
                    ],
                    "blockers": [],
                },
            )

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertTrue(report["valid"], report["blockers"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["route_gate"]["downstream_lock_failure_quarantined"])
        self.assertEqual([], report["route_gate"]["public_or_runtime_claims"])
        self.assertEqual([], report["blockers"])

    def test_bound_route_rejects_extra_parent_lock_public_runtime_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report.update(
                {
                    "valid": False,
                    "accepted_for_planning": False,
                    "route_blocked": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                    "route_lock_invariant_valid": False,
                    "blockers": [
                        (
                            "player_identity_public_contract_gap: unexpected public/runtime claim: "
                            "post_approved_runtime_evidence_route_check, public_sdk_ready"
                        ),
                    ],
                }
            )
            route_report["route_lock"]["invariant_valid"] = False
            route_report["critical_path_phase"][
                "source_checker_approved_runtime_evidence_manifest"
            ] = approved_runtime_route_diagnosis(approved_runtime)
            route_report["critical_path_phase"]["source_checker_public_or_runtime_claims"] = [
                "first_evidence_boundary.post_runtime_fast_path_inputs.approved_runtime_evidence_ready",
            ]
            route_report["checks"].insert(
                0,
                {
                    "name": "player_identity_public_contract_gap",
                    "valid": False,
                    "public_or_runtime_claims": [
                        "post_approved_runtime_evidence_route_check",
                        "public_sdk_ready",
                    ],
                    "blockers": [],
                },
            )

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["route_gate"]["downstream_lock_failure_quarantined"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn(
            "checks[0].public_or_runtime_claims:public_sdk_ready",
            report["route_gate"]["public_or_runtime_claims"],
        )

    def test_bound_route_allows_post_evidence_simulation_only_when_identity_contract_remains_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["post_evidence_p0_lock_simulation"] = safe_post_evidence_p0_lock_simulation()

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertTrue(report["valid"], report["blockers"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["route_gate"]["public_or_runtime_claims"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_bound_route_rejects_post_evidence_simulation_nonzero_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            simulation = safe_post_evidence_p0_lock_simulation()
            simulation["progress"] = "1/4"
            simulation["p0_dependency_chain_progress_contribution"] = 1
            route_report["post_evidence_p0_lock_simulation"] = simulation

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_post_evidence_simulation_contract_requirement_missing", report["blockers"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("post_evidence_p0_lock_simulation.progress", claims)
        self.assertIn("post_evidence_p0_lock_simulation.p0_dependency_chain_progress_contribution", claims)

    def test_bound_route_rejects_post_evidence_simulation_without_hash_current_identity_contract_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            simulation = safe_post_evidence_p0_lock_simulation()
            simulation.pop("hash_current_identity_public_contract_decision_record_required")
            simulation["blocked_until_after_accepted_runtime_evidence"] = [
                "reviewed_identity_public_contract",
            ]
            route_report["post_evidence_p0_lock_simulation"] = simulation

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_post_evidence_simulation_contract_requirement_missing", report["blockers"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn(
            "post_evidence_p0_lock_simulation.approved_runtime_evidence_accepted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_bound_route_rejects_post_runtime_downstream_child_unlock_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            checks = {check["name"]: check for check in route_report["checks"]}
            checks["permissions_admin_public_readiness"]["dependency_chain_locked"] = False
            checks["permissions_admin_public_readiness"]["sidecarAutomationReady"] = True
            checks["command_chat_response_public_readiness"]["current_route_blocker"] = "sidecar_automation_ready"
            checks["command_chat_response_public_readiness"]["remaining_route_blockers"] = []
            checks["command_chat_response_public_readiness"]["passiveWindowReady"] = True
            checks["commands_replies_public_readiness"]["public_or_runtime_accounting_allowed"] = True
            checks["commands_replies_public_readiness"]["betaNoticeReady"] = True

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn(
            "route_gate_permissions_admin_public_readiness_dependency_chain_unlocked",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_command_chat_response_public_readiness_current_blocker_unexpected",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_command_chat_response_public_readiness_remaining_blockers_unexpected",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_commands_replies_public_readiness_public_or_runtime_accounting_allowed_overclaim",
            report["blockers"],
        )
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].sidecarAutomationReady", claims)
        self.assertIn("checks[1].passiveWindowReady", claims)
        self.assertIn("checks[2].betaNoticeReady", claims)

    def test_bound_route_rejects_post_evidence_simulation_missing_child_locks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            simulation = safe_post_evidence_p0_lock_simulation()
            simulation.pop("p0_child_checks")
            route_report["post_evidence_p0_lock_simulation"] = simulation

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_post_evidence_simulation_contract_requirement_missing", report["blockers"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn(
            "post_evidence_p0_lock_simulation.approved_runtime_evidence_accepted",
            report["route_gate"]["public_or_runtime_claims"],
        )

    def test_bound_route_preserves_zero_sdk_and_p0_progress_before_accepted_evidence(self) -> None:
        route_report = self.base_route_report()
        route_report["sdk_progress"] = "1/12"
        route_report["complete_sdk_claim_progress_contribution"] = 1
        route_report["p0_progress"] = "1/4"
        route_report["p0_dependency_chain_claim_progress_contribution"] = 1

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("sdk_progress", claims)
        self.assertIn("complete_sdk_claim_progress_contribution", claims)
        self.assertIn("p0_progress", claims)
        self.assertIn("p0_dependency_chain_claim_progress_contribution", claims)
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])

    def test_cli_accepted_runtime_evidence_moves_only_to_identity_public_contract_gate(self) -> None:
        import check_player_identity_runtime_principal_lifecycle_window_manifest as window_manifest_checker
        import prepare_player_principal_lifecycle_window_request as request_pack_builder
        import test_check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_fixture

        def sha256(path: Path) -> str:
            return hashlib.sha256(path.read_bytes()).hexdigest()

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
                principal_path = root / "players-identity-principal-invalidation-policy.json"
                approved_runtime = root / "approved-runtime-principal-lifecycle.json"
                write_json(lifecycle_path, planning_lifecycle_manifest())
                write_json(principal_path, planning_principal_manifest())

                approved_env = approved_fixture.safe_test_env()
                approved_offline_root = Path(approved_env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"])
                for module in (request_pack_builder, window_manifest_checker):
                    module.APPROVED_OFFLINE_WORKSPACE_ROOTS = (approved_offline_root,)
                    if hasattr(module, "EVIDENCE_ROOT"):
                        module.EVIDENCE_ROOT = approved_offline_root / "live-validation-logs"

                run_id = approved_fixture.RUN_ID
                live_dir = approved_offline_root / "live-validation-logs" / run_id
                live_dir.mkdir(parents=True, exist_ok=True)
                copied_log = live_dir / "Obelisk.log"
                copied_log.write_text(
                    "\n".join(approved_fixture.runtime_log_lines()) + "\n",
                    encoding="utf-8",
                )
                analyzer_result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "analyze_runtime_observer_log.py"),
                        "--obelisk-commit",
                        approved_fixture.TEST_COMMIT,
                        str(copied_log),
                    ],
                    check=True,
                    env=approved_env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                runtime_summary = json.loads(analyzer_result.stdout)

                window_args = SimpleNamespace(
                    instance="arkserver2",
                    map_name="TheIsland",
                    run_id=run_id,
                    binary_sha256=approved_fixture.SHA,
                    server_binary_path=request_pack_builder.EXPECTED_SERVER_BINARY_PATH,
                    obelisk_commit=approved_fixture.TEST_COMMIT,
                    obelisk_build_artifact=None,
                    obelisk_build_artifact_sha256=None,
                    obelisk_build_artifact_label=None,
                    approved_window_start_utc="2026-06-01T12:00:00Z",
                    approved_window_end_utc="2026-06-01T12:15:00Z",
                    restart_expectation="restart",
                    final_posture="stable",
                    diagnostic_candidates=False,
                    diagnostic_candidates_enabled=False,
                    user_policy="no_regular_users",
                    notice_path="not_applicable",
                    rollback_owner="operator",
                )
                with mock.patch.dict(os.environ, approved_env):
                    request_payload = request_pack_builder.request_payload(window_args)
                    observer_env_lines = request_pack_builder.env_lines(window_args)
                    observer_env_file_lines = request_pack_builder.env_file_lines(window_args)
                request_payload["prepared_at_utc"] = "2026-06-01T11:55:00Z"

                observer_env_path = live_dir / "observer-window.env"
                request_path = live_dir / "window-request.json"
                operator_request_path = live_dir / "operator-approval-request.md"
                operator_receipt_path = live_dir / "operator-approval-receipt.json"
                window_manifest_path = live_dir / "window-manifest.env"
                preflight_pre_path = live_dir / "preflight-pre.json"
                preflight_post_path = live_dir / "preflight-post.json"

                observer_env_path.write_text(
                    "\n".join(observer_env_file_lines) + "\n",
                    encoding="utf-8",
                )
                request_path.write_text(json.dumps(request_payload, sort_keys=True) + "\n", encoding="utf-8")
                operator_request_path.write_text(
                    request_pack_builder.markdown_request(
                        request_payload,
                        observer_env_lines,
                    ),
                    encoding="utf-8",
                )
                operator_receipt_path.write_text(
                    json.dumps(
                        request_pack_builder.operator_approval_receipt_payload(
                            request_payload,
                            request_json_path=request_path,
                            request_md_path=operator_request_path,
                            env_path=observer_env_path,
                            operator_approved=True,
                            operator_reference="operator",
                            approved_at_utc="2026-06-01T11:56:00Z",
                        ),
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
                preflight_pre_path.write_text(
                    add_preflight_false_only_flags(
                        approved_fixture.preflight_payload(
                            mode="observer-window",
                            instance="arkserver2",
                            run_id=run_id,
                            map_name="TheIsland",
                            window_manifest_path=window_manifest_path,
                            copied_log_path=copied_log,
                            env_file=observer_env_path,
                            env_sha256=sha256(observer_env_path),
                            checked_at_utc="2026-06-01T12:00:00Z",
                        )
                    ),
                    encoding="utf-8",
                )
                preflight_post_path.write_text(
                    add_preflight_false_only_flags(
                        approved_fixture.preflight_payload(
                            mode="stable",
                            instance="arkserver2",
                            run_id=run_id,
                            map_name="TheIsland",
                            window_manifest_path=window_manifest_path,
                            copied_log_path=copied_log,
                            checked_at_utc="2026-06-01T12:15:00Z",
                        )
                    ),
                    encoding="utf-8",
                )
                window_manifest_path.write_text(
                    "\n".join(
                        [
                            f"run_id={run_id}",
                            f"obelisk_commit={approved_fixture.TEST_COMMIT}",
                            "target=arkserver2/TheIsland",
                            f"approval={request_pack_builder.APPROVAL_TEXT}",
                            "approved_window_start_utc=2026-06-01T12:00:00Z",
                            "approved_window_end_utc=2026-06-01T12:15:00Z",
                            "actual_capture_start_utc=2026-06-01T12:01:00Z",
                            "actual_capture_end_utc=2026-06-01T12:14:00Z",
                            f"copied_log_path={copied_log}",
                            f"copied_log_sha256={sha256(copied_log)}",
                            f"request_pack_path={request_path}",
                            f"request_pack_sha256={sha256(request_path)}",
                            f"observer_env_path={observer_env_path}",
                            f"observer_env_sha256={sha256(observer_env_path)}",
                            f"operator_approval_receipt_path={operator_receipt_path}",
                            f"operator_approval_receipt_sha256={sha256(operator_receipt_path)}",
                            f"preflight_pre_path={preflight_pre_path}",
                            f"preflight_pre_sha256={sha256(preflight_pre_path)}",
                            f"preflight_post_path={preflight_post_path}",
                            f"preflight_post_sha256={sha256(preflight_post_path)}",
                            "pre_posture=stable",
                            "post_posture=stable",
                            "pre_check=passed",
                            "post_check=passed",
                            "rollback_start_utc=2026-06-01T12:14:00Z",
                            "rollback_end_utc=2026-06-01T12:15:00Z",
                            "rollback_completed=true",
                            "rollback_delta=removed_observer_env_and_markers_preserved_disable_plugins",
                            "observer_env_survived=false",
                            "observer_marker_survived=false",
                            "sibling_marker_entries=absent",
                            "sibling_observer_env=absent",
                            "user_policy=no_regular_users",
                            "notice_sent=not_applicable",
                            "log_budget=10",
                            "plugins_disabled=true",
                            "scanner_disabled=true",
                            "dispatch_limit=0",
                            "wrapper_profile=observer-debug",
                            "observer_exclusivity=player_principal_lifecycle_only",
                            "debug_escape_markers=absent",
                            "callback_escape_markers=absent",
                            "native_exec_disabled=true",
                            "ptrace_disabled=true",
                            "single_module_summary=player_principal_lifecycle",
                            "delivery_claim=none",
                            "principal_claim=none",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                old_receipt_bound_request_keys = (
                    window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS
                )
                old_request_pack_top_level_keys = window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS
                try:
                    window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = (
                        old_receipt_bound_request_keys | {"direct_join_plan"}
                    )
                    window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = (
                        old_request_pack_top_level_keys | {"direct_join_plan"}
                    )
                    with mock.patch.dict(os.environ, approved_env):
                        window_fields = window_manifest_checker.load_manifest(window_manifest_path)
                        window_validation = window_manifest_checker.validate_manifest(
                            window_fields,
                            window_manifest_path,
                            post_window_replay=True,
                        )
                        window_report = window_manifest_checker.build_report(
                            window_fields,
                            window_validation,
                            window_manifest_path,
                            post_window_replay=True,
                        )
                finally:
                    window_manifest_checker.EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = (
                        old_receipt_bound_request_keys
                    )
                    window_manifest_checker.EXPECTED_REQUEST_PACK_TOP_LEVEL_KEYS = (
                        old_request_pack_top_level_keys
                    )
                if not window_report["ready"]:
                    self.fail(
                        "window manifest fixture failed\n"
                        f"stdout={json.dumps(window_report, indent=2, sort_keys=True)}\nstderr="
                    )
                operational_window_keys = (
                    "schema",
                    "ready",
                    "operational_window_manifest_ready",
                    "run_id",
                    "obelisk_commit",
                    "approval",
                    "approved_window",
                    "actual_capture",
                    "rollback_window",
                    "target",
                    "manifest",
                    "copied_log",
                    "request_pack",
                    "observer_env",
                    "operator_approval_receipt",
                    "preflight",
                    "posture",
                    "rollback",
                    "log_budget",
                    "claims",
                    "user_policy",
                    "notice_sent",
                    "promotion_ready",
                    "public_header_allowed",
                    "public_abi_ready",
                    "public_sdk_ready",
                    "v1_completion_ready",
                    "runtime_ready",
                    "stable_claim_allowed",
                    "request_pack_counts_as_approved_runtime_evidence",
                    "preflight_counts_as_approved_runtime_evidence",
                    "window_manifest_counts_as_approved_runtime_evidence",
                    "completed_receipt_counts_as_approved_runtime_evidence",
                    "approved_runtime_evidence_present",
                    "approved_runtime_evidence_ready",
                    "non_claims",
                )
                accepted_manifest = approved_fixture.add_output_artifact_identity(
                    {
                        "schema": approved_fixture.APPROVED_SCHEMA,
                        "artifact_status": "approved_runtime_observer_summary",
                        "readiness_classification": "runtime_evidence_only",
                        "approved_runtime_evidence_present": True,
                        "runtime_evidence_ready": True,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_abi_ready": False,
                        "public_sdk_ready": False,
                        "v1_completion_ready": False,
                        "runtime_ready": False,
                        "public_capability_bits_now": [],
                        "public_callback_abi_now": [],
                        "approval": {
                            "runtime_evidence_reviewed": True,
                            "reviewed_by": "runtime-reviewer",
                            "review_note": "consume-only lifecycle evidence reviewed",
                            "runtime_work_authorized_by_this_manifest": False,
                            "server_operations_authorized_by_this_manifest": False,
                            "publication_authorized_by_this_manifest": False,
                            "discord_authorized_by_this_manifest": False,
                        },
                        "operational_window": {
                            key: window_report[key]
                            for key in operational_window_keys
                        },
                        "source_summary": runtime_summary,
                        "consumer_boundary_cases": [
                            {
                                "case": "stale_after_logout",
                                "result": "fail_closed",
                                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                                "runtime_observed": False,
                                "lookup_allowed": False,
                                "mutation_allowed": False,
                                "return_override_allowed": False,
                                "public_sdk_surface": False,
                            },
                            {
                                "case": "malformed_or_unsupported_evidence",
                                "result": "fail_closed",
                                "provenance": "consumer_boundary_assertion_not_runtime_observation",
                                "runtime_observed": False,
                                "lookup_allowed": False,
                                "mutation_allowed": False,
                                "return_override_allowed": False,
                                "public_sdk_surface": False,
                            },
                        ],
                        "privacy_boundary": {
                            "copied_opaque_principal_only": True,
                            "redacted_runtime_observer": True,
                            "player_identifiers_logged": False,
                            "lookup_allowed": False,
                            "resource_handle_allowed": False,
                            "mutation_allowed": False,
                            "return_override_allowed": False,
                        },
                        "promotion_gate": {
                            "runtime_evidence_ready": True,
                            "ready": False,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "runtime_ready": False,
                        },
                        "non_claims": [
                            "approved runtime observer evidence only",
                            (
                                "does not promote public player identity, lookup, permissions, commands, "
                                "moderation, admin authority, mutation, return override, ResourceHandle, "
                                "or v1 SDK readiness"
                            ),
                            (
                                "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, "
                                "FNames, GObjects, raw params, or persistent lookup keys"
                            ),
                            "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
                        ],
                    }
                )
                write_json(approved_runtime, accepted_manifest)

                result = self.run_checker(
                    [
                        "--lifecycle-anchor-candidates-manifest",
                        str(lifecycle_path),
                        "--principal-invalidation-policy",
                        str(principal_path),
                        "--approved-runtime-principal-lifecycle-evidence-manifest",
                        str(approved_runtime),
                        "--json",
                    ],
                    env=approved_env,
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
            self.assertTrue(report["route_blocked"])
            self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
            self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
            self.assertIn(report["next_route_action"], {"review_identity_public_contract", "review_identity_public_contract_gate"})
            self.assertEqual([], report["blockers"])
            self.assertTrue(report["approved_runtime_evidence_check"]["accepted"])
            approved_report = report["approved_runtime_evidence_check"]["report"]
            self.assertEqual(
                "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
                approved_report["schema"],
            )
            self.assertEqual(
                "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                approved_report["input_schema"],
            )
            self.assertEqual("identity_public_contract_gate_missing", approved_report["next_blocker"])
            for key in (
                "promotion_ready",
                "public_header_allowed",
                "public_sdk_ready",
                "public_abi_ready",
                "runtime_ready",
                "v1_completion_ready",
                "counts_toward_public_sdk",
                "counts_toward_runtime",
                "counts_toward_v1_completion",
                "public_or_runtime_accounting_allowed",
            ):
                if key in approved_report:
                    self.assertFalse(approved_report[key], key)

            route = report["route_gate"]["report"]
            if report["route_gate"]["downstream_lock_failure_quarantined"]:
                self.assertFalse(route["valid"])
                self.assertIn(
                    "player_identity_public_contract_gap: invalid route prerequisite",
                    route["blockers"],
                )
                if "commands_replies_public_readiness: invalid route prerequisite" in route["blockers"]:
                    self.assertIn(
                        "command_chat_response_public_readiness: invalid route prerequisite",
                        route["blockers"],
                    )
            else:
                self.assertTrue(route["valid"])
            self.assertTrue(route["planning_only"])
            self.assertTrue(route["route_blocked"])
            self.assertEqual("identity_public_contract_gate_missing", route["current_route_blocker"])
            self.assertEqual(["identity_public_contract_gate_missing"], route["remaining_route_blockers"])
            self.assertEqual(["reviewed_identity_public_contract"], route["route_lock"]["blocked_until"])
            for key in (
                "promotion_ready",
                "public_sdk_ready",
                "public_abi_ready",
                "runtime_ready",
                "public_header_allowed",
                "counts_toward_public_sdk",
                "counts_toward_runtime",
                "counts_toward_v1_completion",
                "public_or_runtime_accounting_allowed",
            ):
                self.assertFalse(route[key], key)

            phase = route["critical_path_phase"]
            self.assertEqual("identity_public_contract_gate_missing", phase["current_blocker"])
            self.assertEqual("identity_public_contract_gate_missing", phase["source_checker_primary_blocker"])
            self.assertFalse(phase["permissions_admin_unlocked"])
            self.assertFalse(phase["command_response_unlocked"])
            self.assertFalse(phase["commands_replies_unlocked"])
            self.assertFalse(report["route_gate"]["public_or_runtime_claims"])

            locked_children = {
                check["name"]: check
                for check in route["checks"]
                if check["name"]
                in {
                    "permissions_admin_public_readiness",
                    "command_chat_response_public_readiness",
                    "commands_replies_public_readiness",
                }
            }
            self.assertEqual(
                {
                    "permissions_admin_public_readiness",
                    "command_chat_response_public_readiness",
                    "commands_replies_public_readiness",
                },
                set(locked_children),
            )
            for check in locked_children.values():
                self.assertTrue(check["dependency_chain_locked"], check["name"])
                self.assertEqual("identity_public_contract_gate_missing", check["current_route_blocker"])
                self.assertEqual(["identity_public_contract_gate_missing"], check["remaining_route_blockers"])
                self.assertFalse(check["counts_toward_public_sdk"], check["name"])
                self.assertFalse(check["counts_toward_runtime"], check["name"])
                self.assertFalse(check["counts_toward_v1_completion"], check["name"])
                self.assertFalse(check["public_or_runtime_accounting_allowed"], check["name"])
        finally:
            approved_fixture.cleanup_live_temp_dirs()

    def test_bound_route_allows_locked_child_runtime_observed_diagnostics_only(self) -> None:
        route_report = {
            "route_blocked": True,
            "current_route_blocker": "identity_public_contract_gate_missing",
            "remaining_route_blockers": ["identity_public_contract_gate_missing"],
            "route_lock": {
                "locked": True,
                "blocked_until": ["reviewed_identity_public_contract"],
            },
            "critical_path_phase": {
                "current_blocker": "identity_public_contract_gate_missing",
                "source_checker_primary_blocker": "identity_public_contract_gate_missing",
                "next_after_runtime_evidence": "identity_public_contract_gate_missing",
                "source_checker_public_or_runtime_claims": [],
                "source_checker_approved_runtime_evidence_manifest": approved_runtime_route_diagnosis(
                    Path("/tmp/approved-runtime-principal-lifecycle.json")
                ),
            },
            "checks": [
                {
                    "name": "player_identity_public_contract_gap",
                    "public_or_runtime_claims": [],
                },
                {
                    "name": "permissions_admin_public_readiness",
                    "public_or_runtime_claims": [
                        "identity_input_diagnostics.accepted_runtime_evidence_observed",
                    ],
                },
            ],
        }

        self.assertTrue(
            CHECKER.bound_route_claim_is_allowed_parent_lock_diagnostic(
                route_report,
                "checks[1].public_or_runtime_claims:identity_input_diagnostics.accepted_runtime_evidence_observed",
            )
        )
        self.assertFalse(
            CHECKER.bound_route_claim_is_allowed_parent_lock_diagnostic(
                route_report,
                "checks[1].public_or_runtime_claims:public_sdk_ready",
            )
        )

    def test_cli_passive_or_diagnostic_runtime_manifests_do_not_advance_route(self) -> None:
        diagnostic_module = {
            "accepted_count": 0,
            "rejected_count": 0,
            "diagnostic_candidate_count": 17,
            "diagnostic_candidate_target_counts": {
                "GameMode.K2_PostLogin": 3,
                "ShooterGameMode.CheckJoinInProgress": 2,
                "ShooterGameMode.HandleNewPlayer": 7,
                "ShooterGameMode.OnLogout": 5,
            },
            "diagnostic_candidate_reason_counts": {
                "lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724": 4,
                "lifecycle_property_FName_mismatch_expected_28543_observed_28550": 3,
            },
            "diagnostic_log_budget_reached": True,
            "diagnostic_log_limits": [10],
            "diagnostic_only_non_evidence": True,
            "observed_event_cases": [],
        }
        cases = (
            (
                "passive-snapshot",
                {
                    "schema": "obelisk.player-principal-passive-snapshot.v1",
                    "approved_runtime_evidence": False,
                    "captured_at_utc": "2026-06-04T08:51:19Z",
                    "evidence_classification": "passive_snapshot_non_evidence",
                    "ready": False,
                    "source_kind": "passive_snapshot",
                    "targets": [
                        {
                            "instance": "arkserver",
                            "map": "Ragnarok",
                            "approved_runtime_evidence": False,
                            "analyzer": {
                                "summary": {
                                    "schema": "obelisk.runtime-observer-log-summary.v1",
                                    "modules": {
                                        "player_principal_lifecycle": diagnostic_module,
                                    },
                                },
                            },
                        }
                    ],
                },
                "passive_snapshot_manifest_is_not_approved_runtime_evidence",
            ),
            (
                "diagnostic-shape",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-evidence.v1",
                    "source_summary": {
                        "modules": {
                            "player_principal_lifecycle": diagnostic_module,
                        },
                    },
                },
                "synthetic_shape_fixture_is_not_approved_runtime_evidence",
            ),
            (
                "passive-snapshot-diff",
                {
                    "schema": "obelisk.player-principal-passive-snapshot-diff.v1",
                    "auto_selected_latest_diff": True,
                    "classification": "diagnostic_only_non_evidence",
                    "approved_runtime_evidence": False,
                    "ready": False,
                    "delta": {
                        "accepted": 0,
                        "diagnostic_candidates": 2,
                        "rejected": 0,
                    },
                    "non_claims": [
                        "passive snapshot diff only",
                        "does not satisfy approved runtime evidence",
                    ],
                },
                "passive_snapshot_diff_is_not_approved_runtime_evidence",
            ),
        )
        for case_name, payload, expected_reason in cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
                    principal_path = root / "players-identity-principal-invalidation-policy.json"
                    approved_runtime = root / f"{case_name}.json"
                    write_json(lifecycle_path, planning_lifecycle_manifest())
                    write_json(principal_path, planning_principal_manifest())
                    write_json(approved_runtime, payload)

                    result = self.run_checker(
                        [
                            "--lifecycle-anchor-candidates-manifest",
                            str(lifecycle_path),
                            "--principal-invalidation-policy",
                            str(principal_path),
                            "--approved-runtime-principal-lifecycle-evidence-manifest",
                            str(approved_runtime),
                            "--json",
                        ],
                        check=False,
                    )
                    report = json.loads(result.stdout)

                self.assertEqual(1, result.returncode)
                self.assertFalse(report["valid"])
                self.assertFalse(report["accepted_for_planning"])
                self.assertTrue(report["planning_only"])
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["public_abi_ready"])
                self.assertFalse(report["runtime_ready"])
                self.assertFalse(report["public_header_allowed"])
                self.assertTrue(report["route_blocked"])
                self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
                self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
                self.assertEqual(
                    "produce_approved_runtime_principal_lifecycle_evidence",
                    report["next_route_action"],
                )
                self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])
                checked_report = report["approved_runtime_evidence_check"]["report"]
                self.assertEqual("approved_runtime_evidence_not_accepted", checked_report["next_blocker"])
                self.assertFalse(checked_report["approved_runtime_evidence_present"])
                self.assertFalse(checked_report["runtime_evidence_ready"])
                self.assertIn(expected_reason, checked_report["blockers"])
                route = report["route_gate"]["report"]
                self.assertEqual("approved_runtime_evidence_missing", route["current_route_blocker"])
                self.assertEqual(["approved_runtime_evidence_missing"], route["remaining_route_blockers"])
                self.assertEqual(
                    ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
                    route["route_lock"]["blocked_until"],
                )
                self.assertFalse(report["route_gate"]["public_or_runtime_claims"])

    def test_bound_route_does_not_forward_named_non_runtime_evidence_artifacts(self) -> None:
        cases = (
            (
                "activation-preconditions",
                "obelisk.player-principal-lifecycle-activation-preconditions.v1",
                "activation_preconditions_are_not_approved_runtime_evidence",
            ),
            (
                "beta-notice",
                "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                "notice_prep_sidecar_not_approved_runtime_evidence",
            ),
            (
                "request-check",
                "obelisk.player-principal-lifecycle-window-request-check.v1",
                "request_check_not_approved_runtime_evidence",
            ),
            (
                "passive-diagnostics",
                "obelisk.player-principal-passive-observer-event-triage.v1",
                "passive_event_triage_sidecar_not_approved_runtime_evidence",
            ),
            (
                "public-reachability",
                "obelisk.player-principal-public-reachability-check.v1",
                "public_reachability_not_approved_runtime_evidence",
            ),
            (
                "decision-record-only",
                "obelisk.player-identity-public-contract-decision-record-check.v1",
                "decision_record_only_not_approved_runtime_evidence",
            ),
        )
        for case_name, input_schema, reason in cases:
            with self.subTest(case=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    approved_runtime = Path(temp_dir) / f"{case_name}.json"
                    write_json(
                        approved_runtime,
                        {
                            "schema": input_schema,
                            "source_kind": case_name,
                            "counts_as_approved_runtime_evidence": False,
                        },
                    )
                    forwarded: list[Path | None] = []
                    report = self.run_with_fake_route_report(
                        self.base_route_report(),
                        approved_runtime_path=approved_runtime,
                        approved_runtime_check=(
                            False,
                            rejected_runtime_check_report(input_schema, reason),
                            1,
                            "",
                            None,
                        ),
                        forwarded_approved_runtime=forwarded,
                    )

                self.assertEqual([None], forwarded)
                self.assertFalse(report["valid"])
                self.assertFalse(report["accepted_for_planning"])
                self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
                self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
                self.assertEqual(
                    "produce_approved_runtime_principal_lifecycle_evidence",
                    report["next_route_action"],
                )
                self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
                self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])
                self.assertFalse(report["approved_runtime_evidence_check"]["forwarded_to_route_gate"])
                self.assertEqual(input_schema, report["approved_runtime_evidence_check"]["report"]["input_schema"])
                self.assertIn(reason, report["approved_runtime_evidence_check"]["report"]["blockers"])
                route = report["route_gate"]["report"]
                self.assertEqual(
                    "approved_runtime_evidence_missing",
                    route["critical_path_phase"]["current_blocker"],
                )
                self.assertEqual(
                    ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"],
                    route["route_lock"]["blocked_until"],
                )

    def test_bound_route_rejects_top_level_route_alias_drift_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["route_blocked"] = False
            route_report["current_route_blocker"] = "public_sdk_ready"
            route_report["remaining_route_blockers"] = []
            route_report["next_route_action"] = "publish_public_sdk"
            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["route_blocked"])
        self.assertEqual("public_sdk_ready", report["current_route_blocker"])
        self.assertEqual([], report["remaining_route_blockers"])
        self.assertIn("route_gate_route_blocked_alias_unexpected", report["blockers"])
        self.assertIn("route_gate_current_route_blocker_alias_unexpected", report["blockers"])
        self.assertIn("route_gate_remaining_route_blockers_alias_unexpected", report["blockers"])
        self.assertIn("route_gate_next_route_action_alias_unexpected", report["blockers"])

    def test_bound_route_revalidates_accepted_runtime_evidence_check_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            runtime_report = approved_runtime_check_report()
            runtime_report.pop("v1_completion_ready")
            report = self.run_with_fake_route_report(
                self.base_route_report(blocker="identity_public_contract_gate_missing"),
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    runtime_report,
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("route_gate_bound_identity_blocker_unexpected", report["blockers"])

    def test_bound_route_rejects_accepted_runtime_evidence_path_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            approved_runtime = root / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            alias_text = str(root / "alias" / ".." / approved_runtime.name)
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["critical_path_phase"]["source_checker_approved_runtime_evidence_manifest"] = {
                **approved_runtime_route_diagnosis(approved_runtime),
                "path": alias_text,
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_approved_runtime_evidence_path_alias", report["blockers"])

    def test_bound_route_rejects_accepted_runtime_evidence_case_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["critical_path_phase"]["source_checker_approved_runtime_evidence_manifest"] = {
                **approved_runtime_route_diagnosis(approved_runtime),
                "observed_runtime_cases": ["observer_enable", "session_start_anchor"],
                "consumer_cases": ["stale_after_logout"],
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_approved_runtime_evidence_not_ready", report["blockers"])
        self.assertIn(
            "route_gate_approved_runtime_evidence_observed_runtime_cases_mismatch",
            report["blockers"],
        )
        self.assertIn("route_gate_approved_runtime_evidence_consumer_cases_mismatch", report["blockers"])

    def test_bound_route_rejects_accepted_runtime_evidence_input_schema_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "passive-snapshot.json"
            diagnostic_module = {
                "accepted_count": 0,
                "rejected_count": 0,
                "blockers": [
                    "runtime_observer_evidence_only",
                    "no_accepted_or_rejected_observer_lines",
                ],
                "diagnostic_candidate_count": 17,
                "diagnostic_candidate_lifecycle_property_fname_mismatches": [
                    {
                        "count": 4,
                        "expected_name_index": 28411,
                        "observed_count": 5,
                        "observed_name_indices": [28418, 21314, 22968, 28516, 17724],
                        "reason_counts": {
                            "lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724": 4,
                        },
                        "summary": "expected_28411_observed_28418_21314_22968_28516_17724",
                    },
                    {
                        "count": 3,
                        "expected_name_index": 28543,
                        "observed_count": 1,
                        "observed_name_indices": [28550],
                        "reason_counts": {
                            "lifecycle_property_FName_mismatch_expected_28543_observed_28550": 3,
                        },
                        "summary": "expected_28543_observed_28550",
                    },
                ],
                "diagnostic_candidate_max_sequence": 10,
                "diagnostic_candidate_read_status_counts": {"implausible": 7},
                "diagnostic_candidate_reason_counts": {
                    "lifecycle_property_FName_mismatch_expected_28411_observed_28418_21314_22968_28516_17724": 4,
                    "lifecycle_property_FName_mismatch_expected_28543_observed_28550": 3,
                },
                "diagnostic_candidate_target_counts": {
                    "GameMode.K2_PostLogin": 3,
                    "ShooterGameMode.CheckJoinInProgress": 2,
                    "ShooterGameMode.HandleNewPlayer": 7,
                    "ShooterGameMode.OnLogout": 5,
                },
                "diagnostic_log_budget_reached": True,
                "diagnostic_log_limits": [10],
                "diagnostic_only_non_evidence": True,
                "evidence_status": "observational",
                "observed_event_cases": [],
                "observer_gate_count": 1,
            }
            write_json(
                approved_runtime,
                {
                    "schema": "obelisk.player-principal-passive-snapshot.v1",
                    "all_logs_copied": True,
                    "approved_runtime_evidence": False,
                    "captured_at_utc": "2026-06-04T08:51:19Z",
                    "evidence_classification": "passive_snapshot_non_evidence",
                    "readiness_gate": "none",
                    "ready": False,
                    "target_count": 2,
                    "targets": [
                        {
                            "instance": "arkserver",
                            "map": "Ragnarok",
                            "ready": False,
                            "approved_runtime_evidence": False,
                            "evidence_classification": "passive_snapshot_non_evidence",
                            "counts": {
                                "accepted": 0,
                                "rejected": 0,
                                "diagnostic_candidates": 17,
                            },
                            "analyzer": {
                                "summary": {
                                    "schema": "obelisk.runtime-observer-log-summary.v1",
                                    "readiness_gate": "none",
                                    "review_scope": "runtime_observer_evidence_summary",
                                    "modules": {
                                        "player_principal_lifecycle": diagnostic_module,
                                    },
                                },
                            },
                        },
                        {
                            "instance": "arkserver2",
                            "map": "TheIsland",
                            "ready": False,
                            "approved_runtime_evidence": False,
                            "evidence_classification": "passive_snapshot_non_evidence",
                            "counts": {
                                "accepted": 0,
                                "rejected": 0,
                                "diagnostic_candidates": 0,
                            },
                        },
                    ],
                },
            )
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["critical_path_phase"]["source_checker_approved_runtime_evidence_manifest"] = {
                **approved_runtime_route_diagnosis(approved_runtime),
                "input_schema": "obelisk.player-principal-passive-snapshot.v1",
                "diagnostic_candidate_count": 17,
                "diagnostic_log_budget_reached": True,
            }
            passive_report = {
                **approved_runtime_check_report(),
                "input_schema": "obelisk.player-principal-passive-snapshot.v1",
                "source_summary": {
                    "modules": {
                        "player_principal_lifecycle": diagnostic_module,
                    },
                },
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    passive_report,
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("route_gate_bound_identity_blocker_unexpected", report["blockers"])
        self.assertEqual(
            17,
            report["approved_runtime_evidence_check"]["report"]["source_summary"][
                "modules"
            ]["player_principal_lifecycle"]["diagnostic_candidate_count"],
        )
        self.assertTrue(
            report["approved_runtime_evidence_check"]["report"]["source_summary"][
                "modules"
            ]["player_principal_lifecycle"]["diagnostic_log_budget_reached"],
        )
        self.assertEqual(
            {
                "GameMode.K2_PostLogin": 3,
                "ShooterGameMode.CheckJoinInProgress": 2,
                "ShooterGameMode.HandleNewPlayer": 7,
                "ShooterGameMode.OnLogout": 5,
            },
            report["approved_runtime_evidence_check"]["report"]["source_summary"][
                "modules"
            ]["player_principal_lifecycle"]["diagnostic_candidate_target_counts"],
        )

    def test_bound_route_rejects_diagnostic_budget_metadata_overclaim_in_runtime_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            runtime_report = {
                **approved_runtime_check_report(),
                "source_summary": {
                    "modules": {
                        "player_principal_lifecycle": {
                            "accepted_count": 0,
                            "rejected_count": 0,
                            "diagnostic_candidate_count": 17,
                            "diagnostic_log_budget_reached": True,
                            "diagnostic_log_limits": [10],
                            "diagnostic_only_non_evidence": True,
                            "diagnostic_budget_pressure": {
                                "captured_at_utc": "2026-06-04T08:51:19Z",
                                "evidence_classification": "passive_snapshot_non_evidence",
                                "notes": [
                                    "public SDK remains blocked; diagnostic budget pressure is non-evidence",
                                ],
                                "stable_claim_allowed": True,
                            },
                        },
                    },
                },
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    runtime_report,
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn(
            "source_summary.modules.player_principal_lifecycle.diagnostic_budget_pressure.stable_claim_allowed",
            report["approved_runtime_evidence_check"]["public_or_runtime_claims"],
        )
        self.assertNotIn(
            "source_summary.modules.player_principal_lifecycle.diagnostic_budget_pressure.notes[0]:positive_text_claim",
            report["approved_runtime_evidence_check"]["public_or_runtime_claims"],
        )

    def test_bound_route_rejects_passive_or_diagnostic_identity_evidence_aliases_in_runtime_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            runtime_report = {
                **approved_runtime_check_report(),
                "identity_claim_source": "diagnostic_observer_triage",
                "public_identity_evidence_source_schema": "obelisk.player-principal-passive-snapshot.v1",
                "notes": [
                    "diagnostic observer triage is approved runtime evidence",
                    "passive snapshot is not approved runtime evidence",
                ],
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    runtime_report,
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn("route_gate_bound_identity_blocker_unexpected", report["blockers"])
        claims = report["approved_runtime_evidence_check"]["public_or_runtime_claims"]
        self.assertIn("identity_claim_source", claims)
        self.assertIn("public_identity_evidence_source_schema", claims)
        self.assertIn("notes[0]:positive_text_claim", claims)
        self.assertNotIn("notes[1]:positive_text_claim", claims)

    def test_bound_route_rejects_handoff_side_lane_or_p0_progress_in_runtime_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            runtime_report = {
                **approved_runtime_check_report(),
                "handoff_notes": {"status": "accepted"},
                "side_lane_artifact": {"progress": "1/4"},
                "p0_dependency_chain_claim_progress_contribution": 1,
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    runtime_report,
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["approved_runtime_evidence_check"]["accepted"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["approved_runtime_evidence_check"]["public_or_runtime_claims"]
        self.assertIn("handoff_notes.status", claims)
        self.assertIn("side_lane_artifact.progress", claims)
        self.assertIn("p0_dependency_chain_claim_progress_contribution", claims)

    def test_bound_route_rejects_route_diagnosis_input_schema_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["critical_path_phase"]["source_checker_approved_runtime_evidence_manifest"] = {
                **approved_runtime_route_diagnosis(approved_runtime),
                "input_schema": "obelisk.player-principal-passive-snapshot.v1",
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_approved_runtime_evidence_not_ready", report["blockers"])
        self.assertIn("route_gate_approved_runtime_evidence_input_schema_mismatch", report["blockers"])

    def test_bound_route_rejects_accepted_runtime_route_gate_v1_and_accounting_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["v1_completion_ready"] = True
            route_report["counts_toward_v1_completion"] = True
            route_report["public_or_runtime_accounting_allowed"] = True
            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_v1_completion_ready_overclaim", report["blockers"])
        self.assertIn("route_gate_counts_toward_v1_completion_overclaim", report["blockers"])
        self.assertIn("route_gate_public_or_runtime_accounting_allowed_overclaim", report["blockers"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])

    def test_bound_route_rejects_accepted_runtime_identity_contract_review_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["post_evidence_p0_lock_simulation"] = {
                "identity_contract_decision_record_reviewed": True,
                "identity_contract_decision_record_hash_current": True,
                "identity_contract_decision_record_contract_review_only": True,
                "identity_public_contract_decision_record_reviewed": True,
                "identity_public_contract_decision_record_hash_current": True,
                "identity_public_contract_decision_record_contract_review_only": True,
                "identity_public_contract_record_reviewed": True,
                "reviewedIdentityPublicContract": True,
                "reviewedIdentityPublicContractDecisionRecord": True,
                "hashCurrentIdentityPublicContractDecisionRecord": True,
                "reviewed_hash_current_contract_review_only": True,
            }
            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("post_evidence_p0_lock_simulation.identity_contract_decision_record_reviewed", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_contract_decision_record_hash_current", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_contract_decision_record_contract_review_only", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_public_contract_decision_record_reviewed", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_public_contract_decision_record_hash_current", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_public_contract_decision_record_contract_review_only", claims)
        self.assertIn("post_evidence_p0_lock_simulation.identity_public_contract_record_reviewed", claims)
        self.assertIn("post_evidence_p0_lock_simulation.reviewedIdentityPublicContract", claims)
        self.assertIn("post_evidence_p0_lock_simulation.reviewedIdentityPublicContractDecisionRecord", claims)
        self.assertIn("post_evidence_p0_lock_simulation.hashCurrentIdentityPublicContractDecisionRecord", claims)
        self.assertIn("post_evidence_p0_lock_simulation.reviewed_hash_current_contract_review_only", claims)

    def test_bound_route_rejects_scoped_release_statement_aliases(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "aliases": {
                    "scopedReleaseStatementReady": True,
                    "scoped_release_statement_counts_toward_complete_sdk_claim": True,
                    "scoped_release_statement_outcomes_satisfy_completion": True,
                },
                "split_claims": [
                    {"claim": "scoped_release_statement_ready", "value": "ready"},
                ],
                "notes": [
                    "scoped release statement unlocks v1 completion",
                    "scoped release statement counts toward public SDK",
                    "scoped release statements cannot unlock P0 progress",
                ],
            }
        )

        self.assertIn("aliases.scopedReleaseStatementReady", claims)
        self.assertIn("aliases.scoped_release_statement_counts_toward_complete_sdk_claim", claims)
        self.assertIn("aliases.scoped_release_statement_outcomes_satisfy_completion", claims)
        self.assertIn("split_claims[0]", claims)
        self.assertIn("notes[0]:positive_text_claim", claims)
        self.assertIn("notes[1]:positive_text_claim", claims)
        self.assertNotIn("notes[2]:positive_text_claim", claims)

    def test_bound_route_rejects_final_authz_response_path_aliases(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "aliases": {
                    "finalGateReady": True,
                    "authzReady": True,
                    "responsePathComplete": True,
                },
                "split_claims": [
                    {"field": "finalGateReady", "status": "ready"},
                    {"field": "authzReady", "value": True},
                    {"field": "responsePathComplete", "state": "complete"},
                ],
                "notes": [
                    "final gate ready now",
                    "authz ready now",
                    "response path complete now",
                    "response path remains blocked until predecessor certificates",
                ],
            }
        )

        for claim in (
            "aliases.finalGateReady",
            "aliases.authzReady",
            "aliases.responsePathComplete",
            "split_claims[0]",
            "split_claims[1]",
            "split_claims[2]",
            "notes[0]:positive_text_claim",
            "notes[1]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("notes[2]:positive_text_claim", claims)
        self.assertNotIn("notes[3]:positive_text_claim", claims)

    def test_bound_route_rejects_command_planning_and_route_snapshot_aliases(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "activation_precondition_report": {"status": "ready"},
                "beta_notice_action_report": {"status": "accepted"},
                "bridge_report": {"progress": "1/4", "status": "ready"},
                "commandPlanningReady": True,
                "command_planning_package": {"status": "ready"},
                "compact_context": {"status": "accepted"},
                "copied_log_only": {"status": "ready"},
                "handoff_notes": {"status": "accepted"},
                "notice_action_report": {"status": "accepted"},
                "package_shape_report": {"status": "ready"},
                "package_shape_support": {"status": "supported"},
                "passive_summary": {"status": "ready"},
                "pluginHubPlanningReady": True,
                "plugin_hub_planning": {"status": "ready"},
                "public_readiness": {"status": "ready"},
                "side_lane_artifact": {"progress": "1/4"},
                "start_end_evidence": {"status": "ready"},
                "support_tier_report": {"status": "supported"},
                "route_snapshot": {"status": "accepted"},
                "source_marker": "public_sdk_ready",
                "source_status": "supported",
                "source_marker_pair": {
                    "source_marker": "generic_command_planning_package",
                    "status": "accepted",
                },
                "source_marker_list_pair": {
                    "source_markers": ["route_snapshot"],
                    "source_state": "ready",
                },
                "source_provenance_route_snapshot": {
                    "source_provenance": "route_snapshot",
                    "status": "accepted",
                },
                "source_provenance_accepted_runtime": {
                    "source_provenance": "accepted_runtime_evidence_only",
                    "source_status": "ready",
                },
                "source_provenance_public_readiness": {
                    "source_provenance": "public_readiness",
                    "status": "ready",
                },
                "source_provenance_start_end": {
                    "source_provenance": "runtime_principal_lifecycle_start_end_evidence",
                    "status": "ready",
                },
                "source_provenance_reviewed_contract_metadata": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
                "aliases": [
                    {"field": "bridge_report", "status": "ready"},
                    {"field": "activation_precondition_report", "status": "ready"},
                    {"field": "support_tier_report", "status": "supported"},
                    {"field": "compact_context", "status": "accepted"},
                    {"field": "plugin_hub_planning", "status": "supported"},
                    {"field": "command_planning_package", "status": "ready"},
                    {"field": "route_snapshot", "status": "ready"},
                    {"field": "public_readiness", "status": "ready"},
                    {"field": "start_end_evidence", "status": "ready"},
                ],
                "notes": [
                    "bridge report is ready",
                    "activation precondition report is ready",
                    "beta notice action report is accepted",
                    "compact context is accepted for permissions/admin",
                    "copied-log-only artifact is ready",
                    "passive summary unlocks route readiness",
                    "Plugin Hub planning is supported",
                    "support tier report is supported",
                    "package shape report is ready",
                    "package-shape support is ready",
                    "command planning is ready",
                    "route snapshot is accepted",
                    "public readiness report is ready",
                    "start-end evidence is ready",
                    "handoff notes are accepted for permissions/admin",
                    "side-lane artifact unlocks route",
                    "command planning remains blocked",
                    "route snapshot remains blocked",
                ],
            }
        )

        for claim in (
            "activation_precondition_report.status",
            "beta_notice_action_report.status",
            "bridge_report.progress",
            "bridge_report.status",
            "commandPlanningReady",
            "command_planning_package",
            "command_planning_package.status",
            "compact_context",
            "compact_context.status",
            "copied_log_only",
            "copied_log_only.status",
            "handoff_notes",
            "handoff_notes.status",
            "notice_action_report.status",
            "package_shape_report.status",
            "package_shape_support.status",
            "passive_summary.status",
            "pluginHubPlanningReady",
            "plugin_hub_planning",
            "plugin_hub_planning.status",
            "public_readiness",
            "public_readiness.status",
            "side_lane_artifact.progress",
            "start_end_evidence",
            "start_end_evidence.status",
            "support_tier_report.status",
            "route_snapshot.status",
            "source_marker",
            "source_marker_list_pair",
            "source_marker_list_pair.source_state",
            "source_marker_pair.status",
            "source_provenance_route_snapshot",
            "source_provenance_route_snapshot.status",
            "source_provenance_accepted_runtime",
            "source_provenance_accepted_runtime.source_status",
            "source_provenance_public_readiness",
            "source_provenance_public_readiness.status",
            "source_provenance_start_end",
            "source_provenance_start_end.status",
            "source_provenance_reviewed_contract_metadata",
            "source_provenance_reviewed_contract_metadata.state",
            "source_status",
            "aliases[0]",
            "aliases[1]",
            "aliases[2]",
            "aliases[3]",
            "aliases[4]",
            "aliases[5]",
            "aliases[6]",
            "aliases[7]",
            "aliases[8]",
            "notes[0]:positive_text_claim",
            "notes[1]:positive_text_claim",
            "notes[2]:positive_text_claim",
            "notes[3]:positive_text_claim",
            "notes[4]:positive_text_claim",
            "notes[5]:positive_text_claim",
            "notes[6]:positive_text_claim",
            "notes[7]:positive_text_claim",
            "notes[8]:positive_text_claim",
            "notes[9]:positive_text_claim",
            "notes[10]:positive_text_claim",
            "notes[11]:positive_text_claim",
            "notes[12]:positive_text_claim",
            "notes[13]:positive_text_claim",
            "notes[14]:positive_text_claim",
            "notes[15]:positive_text_claim",
        ):
            self.assertIn(claim, claims)
        self.assertNotIn("notes[16]:positive_text_claim", claims)
        self.assertNotIn("notes[17]:positive_text_claim", claims)

    def test_bound_route_rejects_multi_surface_pack_route_and_source_overclaims(self) -> None:
        safe_claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "multi_surface_beta_capture_pack": {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "status": "candidate_capture_pack",
                    "candidate_only": True,
                    "requires_checker_acceptance": True,
                    "counts_as_approved_runtime_evidence": False,
                    "counts_as_runtime_evidence": False,
                    "counts_as_sdk_progress": False,
                    "counts_as_p0_progress": False,
                    "approved_runtime_evidence_missing": True,
                    "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                },
                "notes": [
                    "multi-surface beta capture plan remains candidate-only and non-counting",
                ],
            }
        )
        self.assertEqual([], safe_claims)

        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "multi_surface_beta_capture_plan_queue": {
                    "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
                    "status": "ready",
                    "queueStatus": "ready",
                    "approvedRuntimeEvidenceMissingCleared": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": [],
                    "sdk_progress": "1/12",
                    "candidate_surfaces": [
                        {
                            "surface": "commands_replies",
                            "captureReady": True,
                            "countsTowardSdk": True,
                        }
                    ],
                },
                "source_pair": {
                    "source_provenance": "multi_surface_beta_capture_pack",
                    "source_status": "accepted",
                },
                "notes": [
                    "multi-surface beta capture pack is ready",
                    "multi-surface beta capture pack remains candidate-only and non-counting",
                ],
            }
        )

        for claim in (
            "multi_surface_beta_capture_plan_queue.status",
            "multi_surface_beta_capture_plan_queue.queueStatus",
            "multi_surface_beta_capture_plan_queue.approvedRuntimeEvidenceMissingCleared",
            "multi_surface_beta_capture_plan_queue.current_route_blocker",
            "multi_surface_beta_capture_plan_queue.remaining_route_blockers",
            "multi_surface_beta_capture_plan_queue.sdk_progress",
            "multi_surface_beta_capture_plan_queue.candidate_surfaces[0].captureReady",
            "multi_surface_beta_capture_plan_queue.candidate_surfaces[0].countsTowardSdk",
            "source_pair.source_status",
            "notes[0]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("multi_surface_beta_capture_plan_queue", claims)
        self.assertNotIn("notes[1]:positive_text_claim", claims)

    def test_bound_route_rejects_sidecar_passive_diagnostic_beta_and_gate_missing_aliases(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "sidecarAutomationReady": True,
                "sidecar_automation": {"status": "ready"},
                "diagnosticCandidatesReady": True,
                "diagnostic_candidate": {"status": "accepted"},
                "passiveWindowReady": True,
                "passive_window": {"status": "ready"},
                "betaNoticeReady": True,
                "beta_notice": {"status": "sent"},
                "identityPublicContractGateMissing": {"status": "resolved"},
                "identity_public_contract_gate_missing": {"status": "passed"},
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                "source_pairs": [
                    {"source_marker": "sidecar_automation", "source_status": "ready"},
                    {"source_provenance": "diagnostic_candidates", "status": "accepted"},
                    {"source_provenance": "passive_window", "state": "ready"},
                    {"source_marker": "beta_notice", "source_result": "sent"},
                    {"source_marker": "identity_public_contract_gate_missing", "source_state": "ready"},
                ],
                "split_claims": [
                    {"field": "sidecar_automation", "status": "ready"},
                    {"field": "diagnosticCandidatesReady", "status": "ready"},
                    {"field": "passiveWindowReady", "status": "ready"},
                    {"field": "betaNoticeReady", "status": "ready"},
                    {"field": "identity_public_contract_gate_missing", "status": "resolved"},
                ],
                "notes": [
                    "sidecar automation unlocks permissions/admin",
                    "diagnostic candidates unlock command response",
                    "passive window unlocks commands/replies",
                    "beta notice is ready for public route",
                    "identity_public_contract_gate_missing unlocks permissions/admin",
                    "identity_public_contract_gate_missing remains blocked",
                ],
            }
        )

        for claim in (
            "sidecarAutomationReady",
            "sidecar_automation",
            "sidecar_automation.status",
            "diagnosticCandidatesReady",
            "diagnostic_candidate",
            "diagnostic_candidate.status",
            "passiveWindowReady",
            "passive_window",
            "passive_window.status",
            "betaNoticeReady",
            "beta_notice",
            "beta_notice.status",
            "identityPublicContractGateMissing",
            "identity_public_contract_gate_missing",
            "identity_public_contract_gate_missing.status",
            "source_pairs[0]",
            "source_pairs[0].source_marker",
            "source_pairs[0].source_status",
            "source_pairs[1]",
            "source_pairs[1].status",
            "source_pairs[2]",
            "source_pairs[2].state",
            "source_pairs[3]",
            "source_pairs[3].source_result",
            "source_pairs[4]",
            "source_pairs[4].source_state",
            "split_claims[0]",
            "split_claims[1]",
            "split_claims[2]",
            "split_claims[3]",
            "split_claims[4]",
            "notes[0]:positive_text_claim",
            "notes[1]:positive_text_claim",
            "notes[2]:positive_text_claim",
            "notes[3]:positive_text_claim",
            "notes[4]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("current_route_blocker", claims)
        self.assertNotIn("remaining_route_blockers", claims)
        self.assertNotIn("notes[5]:positive_text_claim", claims)

    def test_bound_route_rejects_downstream_status_source_ready_and_plugin_hub_shortcuts(
        self,
    ) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "identity_public_contract_gate_missing": {
                    "source_ready": True,
                    "ready": True,
                    "status": "ready",
                },
                "public_reachability_status": {"source_ready": True, "status": "reachable"},
                "rcon_status": {"source_ready": True, "status": "ready"},
                "broadcast_status": {"ready": True, "status": "enabled"},
                "package_support_plugin": {
                    "plugin_hub_support_ready": True,
                    "support_tier_ready": True,
                },
                "split_claims": [
                    {"field": "identity_public_contract_gate_missing", "source_ready": True},
                    {"field": "public_reachability", "ready": True},
                    {"field": "rcon_route", "status": "ready"},
                    {"field": "broadcast_status", "status": "enabled"},
                    {"field": "package_shape_support", "source_ready": True},
                    {"field": "plugin_hub_package_shape", "ready": True},
                ],
                "notes": [
                    "public reachability status is reachable",
                    "RCON route status is ready",
                    "broadcast status enables command replies",
                    "Plugin Hub support is ready",
                    "identity_public_contract_gate_missing remains blocked",
                ],
            }
        )

        for claim in (
            "identity_public_contract_gate_missing",
            "identity_public_contract_gate_missing.source_ready",
            "identity_public_contract_gate_missing.ready",
            "identity_public_contract_gate_missing.status",
            "public_reachability_status",
            "public_reachability_status.source_ready",
            "rcon_status",
            "rcon_status.source_ready",
            "broadcast_status",
            "package_support_plugin.plugin_hub_support_ready",
            "package_support_plugin.support_tier_ready",
            "split_claims[0]",
            "split_claims[1]",
            "split_claims[2]",
            "split_claims[3]",
            "split_claims[4]",
            "split_claims[5]",
            "notes[1]:positive_text_claim",
            "notes[3]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("notes[0]:positive_text_claim", claims)
        self.assertNotIn("notes[2]:positive_text_claim", claims)
        self.assertNotIn("notes[4]:positive_text_claim", claims)

    def test_bound_route_rejects_nested_identity_contract_record_status_unlocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["identity_public_contract_decision_record"] = {
                "status": "reviewed",
                "hash_current": True,
                "contract_review_only": True,
                "record_valid": True,
                "credit": 1,
                "percent": "25%",
                "p0": "ready",
                "zero_credit": 0,
                "downstream_status": {
                    "permissions_admin": {"status": "unlocked"},
                    "command_response": {"status": "ready"},
                    "commands_replies": {"state": "enabled"},
                    "public_abi": {"status": "available"},
                    "runtime": {"readiness": "ready"},
                    "sdk_completion": {"status": "complete"},
                },
                "non_claim": (
                    "contract-review-only record does not unlock permissions/admin, commands, "
                    "public ABI, runtime, or SDK completion"
                ),
            }
            route_report["required_identity_public_contract_decision_record"] = {
                "review_status": "reviewed",
                "hash_bound_to_current_source_artifacts": True,
                "decision_scope": "contract_review_only",
            }

            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        for claim in (
            "identity_public_contract_decision_record.status",
            "identity_public_contract_decision_record.hash_current",
            "identity_public_contract_decision_record.contract_review_only",
            "identity_public_contract_decision_record.record_valid",
            "identity_public_contract_decision_record.credit",
            "identity_public_contract_decision_record.percent",
            "identity_public_contract_decision_record.p0",
            "identity_public_contract_decision_record.downstream_status.permissions_admin.status",
            "identity_public_contract_decision_record.downstream_status.command_response.status",
            "identity_public_contract_decision_record.downstream_status.commands_replies.state",
            "identity_public_contract_decision_record.downstream_status.public_abi.status",
            "identity_public_contract_decision_record.downstream_status.runtime.readiness",
            "identity_public_contract_decision_record.downstream_status.sdk_completion.status",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("identity_public_contract_decision_record.zero_credit", claims)
        self.assertNotIn(
            "required_identity_public_contract_decision_record.review_status",
            claims,
        )
        self.assertNotIn(
            "required_identity_public_contract_decision_record.hash_bound_to_current_source_artifacts",
            claims,
        )
        self.assertNotIn(
            "required_identity_public_contract_decision_record.decision_scope",
            claims,
        )

    def test_bound_route_claims_reject_decision_record_metadata_p0_credit(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "identity_public_contract_decision_record": {
                    "status": "reviewed_hash_current_contract_review_only",
                    "credit": 1,
                    "readiness_credit": "1/4",
                    "percent": "25%",
                    "p0": "ready",
                    "zero_credit": 0,
                    "zero_percent": "0%",
                    "zero_p0": "0/4",
                },
                "reviewed_hash_current_contract_review_only_metadata": {
                    "credit": "1/4",
                },
                "split_metadata": [
                    {
                        "property": "reviewed_hash_current_contract_review_only",
                        "value": "1/4",
                    },
                    {
                        "property": "reviewed_hash_current_contract_review_only",
                        "value": "p0 ready",
                    },
                ],
            }
        )

        for claim in (
            "identity_public_contract_decision_record.credit",
            "identity_public_contract_decision_record.readiness_credit",
            "identity_public_contract_decision_record.percent",
            "identity_public_contract_decision_record.p0",
            "reviewed_hash_current_contract_review_only_metadata.credit",
            "split_metadata[0]",
            "split_metadata[0].value",
            "split_metadata[1]",
            "split_metadata[1].value",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("identity_public_contract_decision_record.zero_credit", claims)
        self.assertNotIn("identity_public_contract_decision_record.zero_percent", claims)
        self.assertNotIn("identity_public_contract_decision_record.zero_p0", claims)

    def test_bound_route_rejects_manifest_drift_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            route_report["critical_path_phase"]["source_checker_manifest_sources"] = route_manifest_sources(
                lifecycle=Path("/tmp/wrong/players-identity-lifecycle-anchor-candidates.json"),
                principal=Path("/tmp/wrong/players-identity-principal-invalidation-policy.json"),
            )
            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                canonical_paths=False,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn(
            "route_gate_bound_identity_lifecycle_anchor_candidates_canonical_path_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_bound_identity_principal_invalidation_policy_canonical_path_mismatch",
            report["blockers"],
        )

    def test_bound_route_rejects_positive_aliases_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            write_json(approved_runtime, {"schema": "test.approved-runtime"})
            route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
            manifest_sources = route_report["critical_path_phase"]["source_checker_manifest_sources"]
            manifest_sources["acceptedRuntimeEvidenceReady"] = True
            manifest_sources["identityPublicContractReviewed"] = True
            manifest_sources["v1SupportReady"] = True
            manifest_sources["summary"] = "identity public contract reviewed"
            route_report["route_summary"] = "ready for v1 support"
            report = self.run_with_fake_route_report(
                route_report,
                approved_runtime_path=approved_runtime,
                approved_runtime_check=(
                    True,
                    approved_runtime_check_report(),
                    0,
                    "",
                    None,
                ),
            )

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.acceptedRuntimeEvidenceReady",
            claims,
        )
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.identityPublicContractReviewed",
            claims,
        )
        self.assertIn("critical_path_phase.source_checker_manifest_sources.v1SupportReady", claims)
        self.assertIn("route_summary:positive_text_claim", claims)

    def test_rejects_multi_surface_pack_as_bound_identity_source_or_route_progress(self) -> None:
        route_report = self.base_route_report()
        manifest_sources = route_report["critical_path_phase"]["source_checker_manifest_sources"]
        manifest_sources["source_provenance"] = "multi_surface_beta_capture_pack"
        manifest_sources["source_status"] = "accepted"
        manifest_sources["accepted_identity_source"] = {
            "source_marker": "multi_surface_beta_capture_plan_queue",
            "status": "ready",
        }
        route_report["multi_surface_beta_capture_candidate_queue"] = {
            "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
            "status": "ready",
            "queueStatus": "ready",
            "approved_runtime_evidence_missing": False,
            "approvedRuntimeEvidenceMissingCleared": True,
            "current_route_blocker": "identity_public_contract_gate_missing",
            "remaining_route_blockers": [],
            "sdk_progress": "1/12",
            "candidate_surfaces": [
                {
                    "surface": "permissions_admin",
                    "captureReady": True,
                    "countsTowardSdk": True,
                }
            ],
        }
        route_report["route_summary"] = "multi-surface beta capture pack is ready"

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        for claim in (
            "critical_path_phase.source_checker_manifest_sources.source_status",
            "critical_path_phase.source_checker_manifest_sources.accepted_identity_source.status",
            "multi_surface_beta_capture_candidate_queue.status",
            "multi_surface_beta_capture_candidate_queue.queueStatus",
            "multi_surface_beta_capture_candidate_queue.approved_runtime_evidence_missing",
            "multi_surface_beta_capture_candidate_queue.approvedRuntimeEvidenceMissingCleared",
            "multi_surface_beta_capture_candidate_queue.current_route_blocker",
            "multi_surface_beta_capture_candidate_queue.remaining_route_blockers",
            "multi_surface_beta_capture_candidate_queue.sdk_progress",
            "multi_surface_beta_capture_candidate_queue.candidate_surfaces[0].captureReady",
            "multi_surface_beta_capture_candidate_queue.candidate_surfaces[0].countsTowardSdk",
            "route_summary:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_stale_lifecycle_anchor_snapshot_hash_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            lifecycle = planning_lifecycle_manifest()
            lifecycle["candidate_anchors"][0]["evidence"]["source_snapshot_sha256"] = "0" * 64
            write_json(lifecycle_path, lifecycle)
            write_json(principal_path, planning_principal_manifest())

            result = self.run_checker(
                [
                    "--lifecycle-anchor-candidates-manifest",
                    str(lifecycle_path),
                    "--principal-invalidation-policy",
                    str(principal_path),
                    "--json",
                ],
                check=False,
            )

        self.assertEqual(1, result.returncode)
        self.assertIn("snapshot-root provenance", result.stderr)
        self.assertIn("lifecycle_anchor_source_snapshot_root_mismatch", result.stderr)

    def test_rejects_route_gate_valid_true_with_wrong_bound_manifest_canonical_paths(self) -> None:
        route_report = self.base_route_report()
        route_report["critical_path_phase"]["source_checker_manifest_sources"] = route_manifest_sources(
            lifecycle=Path("/tmp/wrong/players-identity-lifecycle-anchor-candidates.json"),
            principal=Path("/tmp/wrong/players-identity-principal-invalidation-policy.json"),
        )

        report = self.run_with_fake_route_report(route_report, canonical_paths=False)

        self.assertFalse(report["valid"])
        self.assertIn(
            "route_gate_bound_identity_lifecycle_anchor_candidates_canonical_path_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "route_gate_bound_identity_principal_invalidation_policy_canonical_path_mismatch",
            report["blockers"],
        )

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
            (
                lambda report: report["critical_path_phase"].update(
                    {"source_checker_manifest_sources": {"mode": "repo_local_default"}}
                ),
                "route_gate_bound_identity_manifest_source_mode_unexpected",
            ),
            (
                lambda report: report["critical_path_phase"]["source_checker_manifest_sources"].update(
                    {"expected_manifests_received": False}
                ),
                "route_gate_bound_identity_expected_manifests_missing",
            ),
            (
                lambda report: report["critical_path_phase"].update(
                    {"next_after_runtime_evidence": "permissions_admin_gate_missing"}
                ),
                "route_gate_next_after_runtime_evidence_unexpected",
            ),
            (
                lambda report: report["critical_path_phase"].update({"permissions_admin_unlocked": True}),
                "route_gate_permissions_admin_unlocked_overclaim",
            ),
            (
                lambda report: report["critical_path_phase"].update({"command_response_unlocked": True}),
                "route_gate_command_response_unlocked_overclaim",
            ),
            (
                lambda report: report["critical_path_phase"].update({"commands_replies_unlocked": True}),
                "route_gate_commands_replies_unlocked_overclaim",
            ),
        )
        for mutate, expected in cases:
            with self.subTest(expected=expected):
                route_report = self.base_route_report()
                mutate(route_report)

                report = self.run_with_fake_route_report(route_report)

                self.assertFalse(report["valid"])
                self.assertIn(expected, report["blockers"])

    def test_rejects_route_gate_valid_true_with_repo_local_default_manifest_detail(self) -> None:
        route_report = self.base_route_report()
        manifest = route_report["critical_path_phase"]["source_checker_manifest_sources"]["manifests"][
            "lifecycle_anchor_candidates"
        ]
        manifest["source"] = "repo_local_default"
        manifest["provided_by_cli"] = False

        report = self.run_with_fake_route_report(route_report, canonical_paths=False)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_bound_identity_lifecycle_anchor_candidates_source_unexpected", report["blockers"])

    def test_rejects_route_gate_valid_true_with_cli_source_but_not_cli_provided(self) -> None:
        route_report = self.base_route_report()
        manifest = route_report["critical_path_phase"]["source_checker_manifest_sources"]["manifests"][
            "principal_invalidation_policy"
        ]
        manifest["provided_by_cli"] = False

        report = self.run_with_fake_route_report(route_report, canonical_paths=False)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_bound_identity_principal_invalidation_policy_not_cli_provided", report["blockers"])

    def test_rejects_nested_route_gate_public_runtime_or_v1_readiness_claims(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "injected_nested_claim",
                "valid": True,
                "nested": {
                    "public_sdk_ready": True,
                    "runtimeReady": True,
                    "sdkReady": True,
                    "complete": True,
                    "v1_completion_ready": True,
                    "countsTowardSdk": True,
                    "route_gate_non_counting_counts_toward_public_sdk": True,
                    "dependency_chain_unlocked": True,
                    "drift_summary": {
                        "classification": "diagnostic_only_non_evidence",
                        "evidence_classification": "passive_snapshot_non_evidence",
                    },
                    "runtime_aliases": {
                        "publicRuntimeReady": {"state": {"ready": True}},
                        "runtimeReadinessAccepted": {"status": {"verified": "yes"}},
                        "permissionsAdminAccepted": True,
                        "commandResponsePromoted": {"status": "ready"},
                        "commandsRepliesAccepted": True,
                        "routePromoted": True,
                        "v1CompletionProgressContribution": "25%",
                        "p0DependencyChainProgressContribution": 1,
                        "progress": "1/2",
                        "runtimeEvidenceReady": True,
                    },
                    "split_aliases": [
                        {
                            "field": "public_runtime_readiness_accepted",
                            "value": {"nested": {"status": "ready"}},
                        },
                        {"field": "permissionsAdminPromoted", "status": "promoted"},
                        {"name": "commandResponseAccepted", "value": {"state": "ready"}},
                        {"key": "v1CompletionProgress", "value": "10%"},
                        {"field": "commandsRepliesAccepted", "status": "blocked"},
                    ],
                },
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn("checks[0].nested.public_sdk_ready", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn("checks[0].nested.runtimeReady", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn("checks[0].nested.sdkReady", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn("checks[0].nested.complete", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn("checks[0].nested.v1_completion_ready", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn("checks[0].nested.countsTowardSdk", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn(
            "checks[0].nested.route_gate_non_counting_counts_toward_public_sdk",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn("checks[0].nested.dependency_chain_unlocked", report["route_gate"]["public_or_runtime_claims"])
        self.assertIn(
            "checks[0].nested.drift_summary.classification",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.drift_summary.evidence_classification",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.publicRuntimeReady",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.runtimeReadinessAccepted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.permissionsAdminAccepted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.commandResponsePromoted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.commandsRepliesAccepted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.routePromoted",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.v1CompletionProgressContribution",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.p0DependencyChainProgressContribution",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.runtime_aliases.progress",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertNotIn(
            "checks[0].nested.runtime_aliases.runtimeEvidenceReady",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.split_aliases[0]",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.split_aliases[1]",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.split_aliases[2]",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertIn(
            "checks[0].nested.split_aliases[3]",
            report["route_gate"]["public_or_runtime_claims"],
        )
        self.assertNotIn(
            "checks[0].nested.split_aliases[4]",
            report["route_gate"]["public_or_runtime_claims"],
        )

    def test_rejects_nested_route_gate_positive_text_claims_outside_non_claims(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "injected_text_claim",
                "valid": True,
                "summary": "player identity public SDK ready after approved runtime evidence",
                "non_claim": "this route lock does not promote public SDK readiness",
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        self.assertIn("checks[0].summary:positive_text_claim", report["route_gate"]["public_or_runtime_claims"])
        self.assertNotIn("checks[0].non_claim:positive_text_claim", report["route_gate"]["public_or_runtime_claims"])

    def test_accepts_negated_public_identity_non_promotional_reasons(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "identity_public_contract_gap",
                "valid": True,
                "public_identity_non_promotional_reasons": [
                    "no public identity is promoted",
                    "public identity remains blocked pending reviewed identity-contract evidence",
                    "identity promotion remains blocked until the public contract gate is reviewed",
                    "header, capability, and callback topics remain closed",
                ],
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertTrue(report["valid"], report["blockers"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["route_gate"]["public_or_runtime_claims"])

    def test_rejects_positive_public_identity_non_promotional_reasons(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "identity_public_contract_gap",
                "valid": True,
                "public_identity_non_promotional_reasons": [
                    "public identity is ready",
                    "public player identity is promoted",
                    "identity promotion is ready",
                    "no public identity is promoted",
                ],
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].public_identity_non_promotional_reasons[0]:positive_text_claim", claims)
        self.assertIn("checks[0].public_identity_non_promotional_reasons[1]:positive_text_claim", claims)
        self.assertIn("checks[0].public_identity_non_promotional_reasons[2]:positive_text_claim", claims)
        self.assertNotIn("checks[0].public_identity_non_promotional_reasons[3]:positive_text_claim", claims)

    def test_nested_route_gate_metadata_schema_paths_do_not_count_as_text_claims(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "metadata_with_schema_ids",
                "valid": True,
                "argv": [
                    "check_commands_replies_public_readiness.py",
                    "--response-path-report",
                    "/tmp/command-chat-response-public-readiness/command-chat-response-public-readiness.json",
                ],
                "expected_schema": "obelisk.command-chat-response-public-readiness-check.v1",
                "report_schema": "obelisk.commands-replies-public-readiness-check.v1",
                "schema": "obelisk.public-sdk-v1-completion-ready-schema-id.v1",
                "input_schema": "obelisk.command-chat-response-public-readiness-check.v1",
                "source_schema": "obelisk.commands-replies-public-readiness-check.v1",
                "schema_ids": [
                    "obelisk.command-chat-response-public-readiness-check.v1",
                    "obelisk.commands-replies-public-readiness-check.v1",
                ],
                "summary": "command response is ready",
                "nested": {"public_sdk_ready": True},
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].summary:positive_text_claim", claims)
        self.assertIn("checks[0].nested.public_sdk_ready", claims)
        self.assertFalse(any(".argv" in claim for claim in claims), claims)
        self.assertFalse(any(".expected_schema" in claim for claim in claims), claims)
        self.assertFalse(any(".report_schema" in claim for claim in claims), claims)
        self.assertFalse(any(".schema" in claim for claim in claims), claims)
        self.assertFalse(any(".input_schema" in claim for claim in claims), claims)
        self.assertFalse(any(".source_schema" in claim for claim in claims), claims)

    def test_rejects_bound_route_stable_claim_and_downstream_unlock_aliases(self) -> None:
        route_report = self.base_route_report()
        route_report["stable_claim_allowed"] = True
        route_report["checks"] = [
            {
                "name": "injected_p0_unlock_claim",
                "valid": True,
                "permissionsAdminUnlocked": True,
                "permissionsAdminReady": True,
                "commandResponseUnlocked": True,
                "commandResponseReady": True,
                "commandResponsePathReady": True,
                "commandsRepliesUnlocked": True,
                "commandsRepliesReady": True,
                "responseReady": True,
                "responsePathReady": True,
                "replyReady": True,
                "replyUnlocked": True,
                "countsTowardPublicSdk": True,
                "countsTowardRuntime": True,
                "countsTowardV1Completion": True,
                "countsTowardCompleteSdk": True,
                "countsTowardCompleteSdkClaim": True,
                "publicOrRuntimeAccountingAllowed": True,
                "summary": [
                    "stable claim is allowed",
                    "permissions/admin is unlocked",
                    "command response is unlocked",
                    "commands/replies are ready",
                    "no commands/replies are ready",
                ],
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("stable_claim_allowed", claims)
        self.assertIn("checks[0].permissionsAdminUnlocked", claims)
        self.assertIn("checks[0].permissionsAdminReady", claims)
        self.assertIn("checks[0].commandResponseUnlocked", claims)
        self.assertIn("checks[0].commandResponseReady", claims)
        self.assertIn("checks[0].commandResponsePathReady", claims)
        self.assertIn("checks[0].commandsRepliesUnlocked", claims)
        self.assertIn("checks[0].commandsRepliesReady", claims)
        self.assertIn("checks[0].responseReady", claims)
        self.assertIn("checks[0].responsePathReady", claims)
        self.assertIn("checks[0].replyReady", claims)
        self.assertIn("checks[0].replyUnlocked", claims)
        self.assertIn("checks[0].countsTowardPublicSdk", claims)
        self.assertIn("checks[0].countsTowardRuntime", claims)
        self.assertIn("checks[0].countsTowardV1Completion", claims)
        self.assertIn("checks[0].countsTowardCompleteSdk", claims)
        self.assertIn("checks[0].countsTowardCompleteSdkClaim", claims)
        self.assertIn("checks[0].publicOrRuntimeAccountingAllowed", claims)
        self.assertIn("checks[0].summary[0]:positive_text_claim", claims)
        self.assertIn("checks[0].summary[1]:positive_text_claim", claims)
        self.assertIn("checks[0].summary[2]:positive_text_claim", claims)
        self.assertIn("checks[0].summary[3]:positive_text_claim", claims)
        self.assertNotIn("checks[0].summary[4]:positive_text_claim", claims)

    def test_rejects_route_accepted_as_public_or_downstream_aliases(self) -> None:
        route_report = self.base_route_report()
        route_report["checks"] = [
            {
                "name": "route_acceptance_aliases",
                "valid": True,
                "accepted_for_planning": True,
                "routeAccepted": True,
                "routeAcceptedAsPublicAbi": True,
                "routeAcceptedAsPublicHeader": True,
                "routeAcceptedAsPublicSdk": True,
                "routeAcceptedAsRuntime": True,
                "routeAcceptedAsV1Completion": True,
                "routeAcceptedAsPermissionsAdmin": True,
                "routeAcceptedAsCommandResponse": True,
                "routeAcceptedAsCommandsReplies": True,
                "routeAcceptedAsStableClaim": True,
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].routeAccepted", claims)
        self.assertNotIn("checks[0].accepted_for_planning", claims)
        self.assertIn("checks[0].routeAcceptedAsPublicAbi", claims)
        self.assertIn("checks[0].routeAcceptedAsPublicHeader", claims)
        self.assertIn("checks[0].routeAcceptedAsPublicSdk", claims)
        self.assertIn("checks[0].routeAcceptedAsRuntime", claims)
        self.assertIn("checks[0].routeAcceptedAsV1Completion", claims)
        self.assertIn("checks[0].routeAcceptedAsPermissionsAdmin", claims)
        self.assertIn("checks[0].routeAcceptedAsCommandResponse", claims)
        self.assertIn("checks[0].routeAcceptedAsCommandsReplies", claims)
        self.assertIn("checks[0].routeAcceptedAsStableClaim", claims)

    def test_rejects_certificate_alias_and_public_abi_lookup_handle_wording(self) -> None:
        route_report = self.base_route_report(blocker="identity_public_contract_gate_missing")
        route_report["checks"] = [
            {
                "name": "identity_certificate_aliases",
                "playerIdentityPromotionCertificateReady": True,
                "acceptedRuntimeEvidenceReady": True,
                "notes": [
                    "public ABI exposes player lookup handles before ResourceHandle promotion",
                    "public ABI does not expose player lookup handles before ResourceHandle promotion",
                ],
            }
        ]

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn("checks[0].playerIdentityPromotionCertificateReady", claims)
        self.assertIn("checks[0].acceptedRuntimeEvidenceReady", claims)
        self.assertIn("checks[0].notes[0]:public_abi_identity_lookup_handle_claim", claims)
        self.assertNotIn("checks[0].notes[1]:public_abi_identity_lookup_handle_claim", claims)

    def test_rejects_bound_route_public_contract_runtime_evidence_and_v1_support_aliases(self) -> None:
        route_report = self.base_route_report()
        manifest_sources = route_report["critical_path_phase"]["source_checker_manifest_sources"]
        manifest_sources["acceptedRuntimeEvidenceReady"] = True
        manifest_sources["identityPublicContractReviewed"] = True
        manifest_sources["v1SupportReady"] = True
        manifest_sources["summary"] = "identity public contract reviewed"
        route_report["route_summary"] = "ready for v1 support"

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.acceptedRuntimeEvidenceReady",
            claims,
        )
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.identityPublicContractReviewed",
            claims,
        )
        self.assertIn("critical_path_phase.source_checker_manifest_sources.v1SupportReady", claims)
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.summary:positive_text_claim",
            claims,
        )
        self.assertIn("route_summary:positive_text_claim", claims)

    def test_rejects_bound_route_decision_template_header_status_and_copy_shortcuts(self) -> None:
        claims = CHECKER.collect_bound_route_public_or_runtime_claims(
            {
                "identity_public_contract_decision_record_template": {
                    "review_status": "reviewed",
                    "hash_current": True,
                    "decision_scope": "contract_review_only",
                    "accepted_for_contract_review": True,
                    "permissions_admin": {"status": "unlocked"},
                },
                "identity_claim_source": "public_header_gate_report",
                "source_pair": {
                    "source_provenance": "public_header_gate_report",
                    "source_status": "ready",
                },
                "status_artifact": {"status": "ready"},
                "copy_artifact": {"status": "accepted"},
                "copied_runtime_status_report": {"status": "ready"},
                "notes": [
                    "public header gate report is ready",
                    "copy artifact unlocks permissions/admin",
                    "status report remains blocked",
                ],
            }
        )

        for claim in (
            "identity_public_contract_decision_record_template",
            "identity_public_contract_decision_record_template.review_status",
            "identity_public_contract_decision_record_template.hash_current",
            "identity_public_contract_decision_record_template.decision_scope",
            "identity_public_contract_decision_record_template.accepted_for_contract_review",
            "identity_public_contract_decision_record_template.permissions_admin.status",
            "identity_claim_source",
            "source_pair",
            "source_pair.source_provenance",
            "source_pair.source_status",
            "status_artifact",
            "status_artifact.status",
            "copy_artifact",
            "copy_artifact.status",
            "copied_runtime_status_report",
            "copied_runtime_status_report.status",
            "notes[0]:positive_text_claim",
            "notes[1]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("notes[2]:positive_text_claim", claims)

    def test_rejects_bound_route_generated_or_stale_identity_certificate_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            certificate_path = Path(temp_dir) / "player-identity-promotion-certificate.json"
            certificate = {
                "schema": CHECKER.route_gate.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                "surface_id": "obelisk.player_identity.v1",
                "promotion_status": "promoted",
                "v1_dependency_chain": CHECKER.route_gate.CANONICAL_V1_DEPENDENCY_SEQUENCE,
                "v1_dependency_chain_position": 1,
                "required_by_surface": "obelisk.permissions_admin.v1",
                "required_by_v1_dependency_chain_position": 2,
                "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
                "reviewed_artifact_hash_policy": (
                    "must match the reviewed identity surface record hash carried by the certificate"
                ),
                "missing_mismatched_or_stale_certificate_counts": False,
                "evidence": {
                    "reviewed_artifact_hash": "1" * 64,
                    "reviewed_surface_record_sha256": "1" * 64,
                },
            }
            write_json(certificate_path, certificate)
            binding = {
                "path": str(certificate_path),
                "sha256": hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
            }
            generated_claims = CHECKER.collect_bound_route_public_or_runtime_claims(
                {"generated_certificate": binding}
            )

            certificate["current_reviewed_surface_record_sha256"] = "2" * 64
            write_json(certificate_path, certificate)
            stale_binding = {
                "path": str(certificate_path),
                "sha256": hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
            }
            stale_claims = CHECKER.collect_bound_route_public_or_runtime_claims(
                {"player_identity_promotion_certificate": stale_binding}
            )

        self.assertIn("generated_certificate", generated_claims)
        self.assertIn("player_identity_promotion_certificate", stale_claims)

    def test_rejects_copied_admin_targets_as_bound_identity_sources(self) -> None:
        route_report = self.base_route_report()
        manifest_sources = route_report["critical_path_phase"]["source_checker_manifest_sources"]
        manifest_sources["accepted_identity_source_targets"] = [
            "ShooterPlayerController.ServerListPlayers",
            "ShooterPlayerController.ServerKickPlayer",
        ]
        route_report["target_set_coverage"] = {
            "expected_targets": [
                "ShooterPlayerController.ServerListPlayers",
                "ShooterPlayerController.ServerKickPlayer",
            ]
        }

        report = self.run_with_fake_route_report(route_report)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("route_gate_public_or_runtime_claims_overclaim", report["blockers"])
        claims = report["route_gate"]["public_or_runtime_claims"]
        self.assertIn(
            "critical_path_phase.source_checker_manifest_sources.accepted_identity_source_targets",
            claims,
        )
        self.assertNotIn("target_set_coverage.expected_targets", claims)
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_partial_manifest_inputs_before_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lifecycle_path = Path(temp_dir) / "players-identity-lifecycle-anchor-candidates.json"
            write_json(lifecycle_path, planning_lifecycle_manifest())
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
            lifecycle = planning_lifecycle_manifest()
            lifecycle["public_sdk_ready"] = True
            write_json(lifecycle_path, lifecycle)
            write_json(principal_path, planning_principal_manifest())
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
