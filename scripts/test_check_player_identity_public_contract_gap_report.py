#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_gap_report.py."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_contract_gap_report.py"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
PRIVATE_CANDIDATE = REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json"
IDENTIFIER_REDACTION_EVIDENCE = REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json"
PRINCIPAL_INVALIDATION_POLICY = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "players-identity-principal-invalidation-policy.json"
PRIVATE_POD_LAYOUT_CANDIDATE = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "player-identity-private-pod-layout-candidate.json"
PUBLIC_ABI_PREFLIGHT_CANDIDATE = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "player-identity-public-abi-preflight-candidate.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import manifest as approved_manifest  # noqa: E402

SPEC = importlib.util.spec_from_file_location("player_identity_gap_report_checker", SCRIPT)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class PlayerIdentityPublicContractGapReportTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def load_private_candidate(self) -> dict:
        return json.loads(PRIVATE_CANDIDATE.read_text(encoding="utf-8"))

    def load_identifier_redaction_evidence(self) -> dict:
        return json.loads(IDENTIFIER_REDACTION_EVIDENCE.read_text(encoding="utf-8"))

    def load_principal_invalidation_policy(self) -> dict:
        return json.loads(PRINCIPAL_INVALIDATION_POLICY.read_text(encoding="utf-8"))

    def load_private_pod_layout_candidate(self) -> dict:
        return json.loads(PRIVATE_POD_LAYOUT_CANDIDATE.read_text(encoding="utf-8"))

    def load_public_abi_preflight_candidate(self) -> dict:
        return json.loads(PUBLIC_ABI_PREFLIGHT_CANDIDATE.read_text(encoding="utf-8"))

    def player_identity_surface(self, surfaces: dict) -> dict:
        return next(item for item in surfaces["surfaces"] if item["id"] == checker.SURFACE)

    def run_checker(
        self,
        decisions: dict | None = None,
        surfaces: dict | None = None,
        candidate: dict | None = None,
        identifier_redaction_evidence: dict | None = None,
        principal_invalidation_policy: dict | None = None,
        private_pod_layout_candidate: dict | None = None,
        public_abi_preflight_candidate: dict | None = None,
        approved_runtime_evidence: dict | None = None,
        header_text: str | None = None,
        owner_token_sdk_consumer_contract_path: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            decisions_path = root / "decisions.json"
            surfaces_path = root / "surfaces.json"
            candidate_path = root / "private-candidate.json"
            redaction_path = root / "identifier-redaction-evidence.json"
            principal_policy_path = root / "principal-invalidation-policy.json"
            private_pod_layout_path = root / "private-pod-layout-candidate.json"
            public_abi_preflight_path = root / "public-abi-preflight-candidate.json"
            approved_runtime_path = root / "approved-runtime-evidence.json"
            header_path = root / "ObeliskApi.h"

            decisions_path.write_text(json.dumps(decisions if decisions is not None else self.load_decisions()), encoding="utf-8")
            surfaces_path.write_text(json.dumps(surfaces if surfaces is not None else self.load_surfaces()), encoding="utf-8")
            candidate_path.write_text(json.dumps(candidate if candidate is not None else self.load_private_candidate()), encoding="utf-8")
            redaction_path.write_text(
                json.dumps(
                    identifier_redaction_evidence
                    if identifier_redaction_evidence is not None
                    else self.load_identifier_redaction_evidence()
                ),
                encoding="utf-8",
            )
            principal_policy_path.write_text(
                json.dumps(
                    principal_invalidation_policy
                    if principal_invalidation_policy is not None
                    else self.load_principal_invalidation_policy()
                ),
                encoding="utf-8",
            )
            private_pod_layout_path.write_text(
                json.dumps(
                    private_pod_layout_candidate
                    if private_pod_layout_candidate is not None
                    else self.load_private_pod_layout_candidate()
                ),
                encoding="utf-8",
            )
            public_abi_preflight_path.write_text(
                json.dumps(
                    public_abi_preflight_candidate
                    if public_abi_preflight_candidate is not None
                    else self.load_public_abi_preflight_candidate()
                ),
                encoding="utf-8",
            )
            approved_runtime_args = []
            if approved_runtime_evidence is not None:
                approved_runtime_path.write_text(json.dumps(approved_runtime_evidence), encoding="utf-8")
                approved_runtime_args = ["--approved-runtime-evidence", str(approved_runtime_path)]
            header_path.write_text(header_text if header_text is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")
            owner_token_contract_args = []
            if owner_token_sdk_consumer_contract_path is not None:
                owner_token_contract_args = [
                    "--owner-token-sdk-consumer-contract",
                    str(owner_token_sdk_consumer_contract_path),
                ]

            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--surfaces",
                    str(surfaces_path),
                    "--private-candidate-contract",
                    str(candidate_path),
                    "--identifier-redaction-evidence",
                    str(redaction_path),
                    "--principal-invalidation-policy",
                    str(principal_policy_path),
                    "--private-pod-layout-candidate",
                    str(private_pod_layout_path),
                    "--public-abi-preflight-candidate",
                    str(public_abi_preflight_path),
                    *approved_runtime_args,
                    *owner_token_contract_args,
                    "--public-header",
                    str(header_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def run_checker_with_paths(
        self,
        *,
        decisions_path: Path,
        surfaces_path: Path,
        candidate_path: Path,
        redaction_path: Path,
        principal_policy_path: Path,
        private_pod_layout_path: Path,
        header_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--private-candidate-contract",
                str(candidate_path),
                "--identifier-redaction-evidence",
                str(redaction_path),
                "--principal-invalidation-policy",
                str(principal_policy_path),
                "--private-pod-layout-candidate",
                str(private_pod_layout_path),
                "--public-header",
                str(header_path),
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_accepts_current_blocked_state_without_runtime_evidence(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertEqual(report["schema"], checker.SCHEMA)
        self.assertEqual(report["surface"], checker.SURFACE)
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["guardrail_passed"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["primary_offline_gap"], "lifetime.generation_scope_invalidation")
        self.assertEqual(
            report["contract_review_inputs_resolved"],
            [
                "privacy.identifier_redaction",
                "planning.source_bound_committed_manifests",
                "lifetime.generation_scope_invalidation.candidate_policy",
            ],
        )
        self.assertIn("runtime.lifecycle_evidence", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.principal_scope", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.invalidation_events", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.reconnect_duplicate_stale_policy", report["remaining_contract_gate_inputs"])
        self.assertIn("abi.public_pod_contract", report["remaining_contract_gate_inputs"])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        self.assertEqual(
            contract_gate_inputs["runtime.lifecycle_evidence"]["review_inputs_missing"],
            ["runtime.lifecycle_evidence"],
        )
        self.assertEqual(
            contract_gate_inputs["privacy.identifier_redaction"]["review_inputs_resolved"],
            ["privacy.identifier_redaction"],
        )
        self.assertEqual(
            contract_gate_inputs["lifetime.generation_scope_invalidation"]["review_inputs_resolved"],
            ["lifetime.generation_scope_invalidation.candidate_policy"],
        )
        self.assertIn(
            "lifetime.principal_scope",
            contract_gate_inputs["lifetime.generation_scope_invalidation"]["remaining_promotion_inputs"],
        )
        self.assertFalse(contract_gate_inputs["lifetime.generation_scope_invalidation"]["promotion_blocker_resolved"])
        self.assertFalse(contract_gate_inputs["lifetime.generation_scope_invalidation"]["promotion_ready"])
        abi_preflight = report["public_abi_promotion_preflight"]
        self.assertEqual(abi_preflight["status"], "blocked")
        self.assertTrue(abi_preflight["candidate_only"])
        self.assertFalse(abi_preflight["accepted_for_contract_review"])
        self.assertFalse(abi_preflight["promotion_ready"])
        self.assertFalse(abi_preflight["public_sdk_ready"])
        self.assertFalse(abi_preflight["runtime_ready"])
        self.assertFalse(abi_preflight["public_header_allowed"])
        self.assertFalse(abi_preflight["public_abi_ready"])
        self.assertFalse(abi_preflight["v1_completion_evidence"])
        self.assertEqual(abi_preflight["public_header_symbols_now"], [])
        self.assertEqual(abi_preflight["public_capability_bits_now"], [])
        self.assertEqual(abi_preflight["public_callback_abi_now"], [])
        self.assertEqual(
            abi_preflight["contract_review_inputs_accepted"],
            {
                "privacy.identifier_redaction": True,
                "lifetime.generation_scope_invalidation.candidate_policy": True,
                "abi.public_pod_contract.private_layout_candidate": True,
            },
        )
        self.assertIn("runtime.lifecycle_evidence", abi_preflight["required_before_public_abi"])
        self.assertIn("abi.layout", abi_preflight["required_before_public_abi"])
        self.assertIn("sdk.consumer", abi_preflight["required_before_public_abi"])
        self.assertIn("nonzero plugin_owner_token required", abi_preflight["required_owner_token_lifecycle"])
        self.assertIn("missing capability fails closed", abi_preflight["required_capability_policy"])
        self.assertEqual(abi_preflight["sdk_consumer_contract"]["source"], "derived_compatibility_stub")
        self.assertFalse(abi_preflight["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(abi_preflight["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertIn(
            "consumer requires nonzero plugin_owner_token before owner-token registration",
            abi_preflight["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn("lifecycle.owner_cleanup", abi_preflight["sdk_consumer_contract"]["does_not_resolve"])
        self.assertEqual(report["sdk_consumer_contract"], abi_preflight["sdk_consumer_contract"])
        self.assertEqual(report["candidate_owner_token_lifecycle"], abi_preflight["required_owner_token_lifecycle"])
        owner_contract = report["owner_token_sdk_consumer_contract"]
        self.assertEqual(owner_contract["source"], "owner_token_sdk_consumer_contract")
        self.assertFalse(owner_contract["accepted_for_contract_review"])
        self.assertFalse(owner_contract["public_sdk_ready"])
        self.assertFalse(owner_contract["runtime_ready"])
        self.assertIn("v1_completion", abi_preflight["does_not_resolve"])
        self.assertIn("candidate-only public ABI preflight for offline routing", abi_preflight["non_claims"])
        lifetime_action = next(
            action
            for action in report["next_offline_actions"]
            if action["id"] == "lifetime.generation_scope_invalidation"
        )
        self.assertTrue(lifetime_action["candidate_policy_accepted"])
        self.assertEqual(lifetime_action["status"], "blocked")
        self.assertIn(
            "does not resolve the full lifetime/generation/scope blocker",
            lifetime_action["non_claim"],
        )
        self.assertTrue(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertEqual(report["identifier_redaction_evidence"]["resolved_inputs"], ["privacy.identifier_redaction"])
        self.assertFalse(report["identifier_redaction_evidence"]["promotion_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_sdk_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["runtime_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_header_allowed"])
        self.assertTrue(report["principal_invalidation_policy"]["accepted_for_policy_review"])
        self.assertEqual(
            report["principal_invalidation_policy"]["resolved_input"],
            "lifetime.generation_scope_invalidation.candidate_policy",
        )
        self.assertFalse(report["principal_invalidation_policy"]["promotion_ready"])
        self.assertFalse(report["principal_invalidation_policy"]["public_sdk_ready"])
        self.assertFalse(report["principal_invalidation_policy"]["runtime_ready"])
        self.assertFalse(report["principal_invalidation_policy"]["public_header_allowed"])
        self.assertFalse(report["principal_invalidation_policy"]["principal_invalidation_ready"])
        source_verification = report["source_bound_planning_manifest_verification"]
        self.assertTrue(source_verification["provided"])
        self.assertTrue(source_verification["accepted_for_contract_review"])
        self.assertEqual(
            source_verification["resolved_input"],
            "planning.source_bound_committed_manifests",
        )
        self.assertTrue(source_verification["planning_only"])
        self.assertFalse(source_verification["promotion_ready"])
        self.assertFalse(source_verification["public_sdk_ready"])
        self.assertFalse(source_verification["runtime_ready"])
        self.assertFalse(source_verification["public_abi_ready"])
        self.assertFalse(source_verification["v1_completion_ready"])
        self.assertTrue(report["private_pod_layout_candidate"]["accepted_for_contract_review_input"])
        self.assertEqual(
            report["private_pod_layout_candidate"]["review_input"],
            "abi.public_pod_contract.private_layout_candidate",
        )
        self.assertEqual(report["private_pod_layout_candidate"]["event_payload"]["struct_size"], 80)
        self.assertEqual(report["private_pod_layout_candidate"]["descriptor"]["struct_size"], 48)
        self.assertEqual(
            report["private_pod_layout_candidate"]["does_not_resolve"],
            ["abi.public_pod_contract", "abi.layout", "sdk.consumer"],
        )
        self.assertFalse(report["private_pod_layout_candidate"]["promotion_ready"])
        self.assertFalse(report["private_pod_layout_candidate"]["public_sdk_ready"])
        self.assertFalse(report["private_pod_layout_candidate"]["runtime_ready"])
        self.assertFalse(report["private_pod_layout_candidate"]["public_header_allowed"])
        abi_action = next(
            action
            for action in report["next_offline_actions"]
            if action["id"] == "abi.public_pod_contract"
        )
        self.assertTrue(abi_action["private_layout_candidate_accepted"])
        self.assertEqual(abi_action["status"], "blocked")
        self.assertEqual(
            abi_action["does_not_resolve"],
            ["abi.public_pod_contract", "abi.layout", "sdk.consumer", "lifecycle.owner_cleanup"],
        )
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["surface_manifest"]["status"], "planning")
        self.assertEqual(report["surface_manifest"]["public_contract"], [])
        self.assertEqual(
            self.player_identity_surface(self.load_surfaces())["v1_decision_contract"]["decision_manifest"],
            "docs/player_identity_public_contract_decisions.json",
        )
        self.assertEqual(report["public_header_scan"]["detected_player_identity_tokens"], [])
        self.assertEqual(report["blockers"], [])

    def test_consumes_approved_runtime_evidence_as_contract_review_input_only(self) -> None:
        result = self.run_checker(approved_runtime_evidence=approved_manifest())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["guardrail_passed"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["blocked_until"], ["reviewed_identity_public_contract"])
        self.assertIn("runtime.lifecycle_evidence", report["contract_review_inputs_resolved"])
        self.assertNotIn("runtime.lifecycle_evidence", report["remaining_contract_gate_inputs"])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        runtime_input = contract_gate_inputs["runtime.lifecycle_evidence"]
        self.assertEqual(runtime_input["review_inputs_resolved"], ["runtime.lifecycle_evidence"])
        self.assertEqual(runtime_input["review_inputs_missing"], [])
        self.assertFalse(runtime_input["promotion_blocker_resolved"])
        self.assertFalse(runtime_input["promotion_ready"])
        self.assertFalse(runtime_input["public_sdk_ready"])
        self.assertIn(
            "privacy.public_identifier_form",
            contract_gate_inputs["privacy.identifier_redaction"]["remaining_promotion_inputs"],
        )
        self.assertIn(
            "abi.layout",
            contract_gate_inputs["abi.public_pod_contract"]["remaining_promotion_inputs"],
        )
        runtime_report = report["approved_runtime_evidence"]
        self.assertTrue(runtime_report["provided"])
        self.assertTrue(runtime_report["accepted_for_contract_review"])
        self.assertEqual(runtime_report["resolved_input"], "runtime.lifecycle_evidence")
        self.assertEqual(runtime_report["resolved_inputs"], ["runtime.lifecycle_evidence"])
        self.assertEqual(runtime_report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            runtime_report["observed_runtime_cases"],
            [
                "observer_enable",
                "session_start_anchor",
                "session_start_rejected_anchor",
                "session_end_anchor",
            ],
        )
        self.assertEqual(
            runtime_report["consumer_cases"],
            ["malformed_or_unsupported_evidence", "stale_after_logout"],
        )
        self.assertFalse(runtime_report["promotion_ready"])
        self.assertFalse(runtime_report["public_sdk_ready"])
        self.assertFalse(runtime_report["runtime_ready"])
        self.assertFalse(runtime_report["public_header_allowed"])

    def test_rejects_invalid_approved_runtime_evidence_without_routing(self) -> None:
        runtime = approved_manifest()
        runtime["public_sdk_ready"] = True

        result = self.run_checker(approved_runtime_evidence=runtime)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_presence_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_ready_missing", report["blockers"])
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertIn("runtime.lifecycle_evidence", report["remaining_contract_gate_inputs"])
        self.assertNotIn("runtime.lifecycle_evidence", report["contract_review_inputs_resolved"])
        self.assertFalse(report["approved_runtime_evidence"]["accepted_for_contract_review"])

    def test_approved_runtime_evidence_rejects_non_promotional_resolved_inputs(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaim_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "resolved_inputs": [
                    "runtime.lifecycle_evidence",
                    "operator_approval_receipt",
                    "preflight_readiness",
                    "live_ops_sidecar",
                ],
            }

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=overclaim_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_non_promotional_inputs_claimed", reasons)
        self.assertIn("approved_runtime_evidence_resolved_inputs_unexpected", reasons)
        self.assertFalse(runtime_report["accepted_for_contract_review"])

    def test_approved_runtime_evidence_rejects_weak_lifecycle_report_linkage(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def weak_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": [
                    "observer_enable",
                    "session_start_anchor",
                    "session_start_rejected_anchor",
                ],
                "consumer_cases": ["malformed_or_unsupported_evidence"],
                "consumer_boundary_assertions": ["malformed_or_unsupported_evidence"],
            }

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=weak_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_observed_runtime_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_boundary_assertions_mismatch", reasons)
        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])

    def test_approved_runtime_evidence_rejects_v1_completion_overclaim(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaim_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "v1_completion_ready": True,
                "v1_completion_evidence": False,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=overclaim_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertIn("approved_runtime_evidence_readiness_flag_not_false", [blocker["reason"] for blocker in blockers])
        self.assertFalse(runtime_report["accepted_for_contract_review"])

    def test_approved_runtime_evidence_rejects_report_public_readiness_overclaim(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaim_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
                "observed_runtime_cases": [
                    "observer_enable",
                    "session_start_anchor",
                    "session_start_rejected_anchor",
                    "session_end_anchor",
                ],
                "consumer_cases": ["malformed_or_unsupported_evidence", "stale_after_logout"],
                "consumer_boundary_assertions": ["malformed_or_unsupported_evidence", "stale_after_logout"],
                "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
                "claims": {
                    "public_contract_ready": True,
                    "downstream": "identity unlocks permissions now",
                    "summary": "public player identity ready",
                },
            }

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=overclaim_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_report_public_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_not_accepted", reasons)
        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])

    def test_rejects_missing_owner_token_sdk_consumer_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            missing_contract = Path(tempdir) / "missing-owner-token-sdk-consumer.json"

            result = self.run_checker(owner_token_sdk_consumer_contract_path=missing_contract)

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner_token_sdk_consumer_contract_missing", report["blockers"])
        owner_contract = report["owner_token_sdk_consumer_contract"]
        self.assertFalse(owner_contract["provided"])
        self.assertEqual(owner_contract["source"], "missing_owner_token_sdk_consumer_contract")
        self.assertFalse(owner_contract["accepted_for_candidate_review"])
        self.assertFalse(owner_contract["public_sdk_ready"])
        self.assertEqual(owner_contract["blockers"], ["owner_token_sdk_consumer_contract_missing"])

    def test_rejects_readiness_flags_that_become_true(self) -> None:
        decisions = self.load_decisions()
        surfaces = self.load_surfaces()
        candidate = self.load_private_candidate()
        decisions["public_header_allowed"] = True
        decisions["approved_runtime_evidence_intake"]["promotion_ready"] = True
        decisions["identifier_redaction_evidence_intake"]["public_sdk_ready"] = True
        decisions["public_abi_preflight_candidate_intake"]["public_abi_ready"] = True
        decisions["owner_token_sdk_consumer_contract_intake"]["lifecycle_owner_cleanup_ready"] = True
        decisions["contract_gate_inputs"][0]["promotion_blocker_resolved"] = True
        decisions["contract_gate_inputs"][1]["public_sdk_ready"] = True
        decisions["proposed_public_pod_abi_candidate"]["runtime_ready"] = True
        self.player_identity_surface(surfaces)["evidence"]["candidate_policy_artifacts"][0]["public_sdk_ready"] = True
        candidate["runtime_ready"] = True

        result = self.run_checker(decisions=decisions, surfaces=surfaces, candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_public_header_allowed_not_false", report["blockers"])
        self.assertIn("readiness_flag_not_false", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"] if detail["reason"] == "readiness_flag_not_false"}
        self.assertIn("$.approved_runtime_evidence_intake.promotion_ready", labels)
        self.assertIn("$.identifier_redaction_evidence_intake.public_sdk_ready", labels)
        self.assertIn("$.public_abi_preflight_candidate_intake.public_abi_ready", labels)
        self.assertIn("$.owner_token_sdk_consumer_contract_intake.lifecycle_owner_cleanup_ready", labels)
        self.assertIn("$.proposed_public_pod_abi_candidate.runtime_ready", labels)
        self.assertIn("$.evidence.candidate_policy_artifacts[0].public_sdk_ready", labels)
        self.assertIn("$.runtime_ready", labels)
        self.assertIn("decisions_contract_gate_input_flag_not_false", report["blockers"])

    def test_rejects_missing_or_weakened_identifier_redaction_intake(self) -> None:
        decisions = self.load_decisions()
        decisions["identifier_redaction_evidence_intake"]["required_checker"] = "scripts/other.py"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_identifier_redaction_evidence_intake_checker_mismatch", report["blockers"])

        decisions = self.load_decisions()
        decisions.pop("identifier_redaction_evidence_intake")
        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_identifier_redaction_evidence_intake_missing", report["blockers"])

    def test_rejects_missing_or_weakened_approved_runtime_evidence_intake(self) -> None:
        decisions = self.load_decisions()
        decisions["approved_runtime_evidence_intake"]["id"] = "runtime_evidence"
        decisions["approved_runtime_evidence_intake"]["status"] = "accepted"
        decisions["approved_runtime_evidence_intake"]["resolved_input"] = "public.identity"
        decisions["approved_runtime_evidence_intake"]["required_checker"] = "scripts/other.py"
        decisions["approved_runtime_evidence_intake"]["non_claim"] = "promotes player identity"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_approved_runtime_evidence_intake_id_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_status_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_resolved_input_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_checker_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_non_claim_mismatch", report["blockers"])

        decisions = self.load_decisions()
        decisions.pop("approved_runtime_evidence_intake")
        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_approved_runtime_evidence_intake_missing", report["blockers"])

    def test_rejects_missing_or_weakened_public_abi_preflight_intake(self) -> None:
        decisions = self.load_decisions()
        decisions["public_abi_preflight_candidate_intake"]["required_checker"] = "scripts/other.py"
        decisions["public_abi_preflight_candidate_intake"]["default_manifest"] = "docs/research/other.json"
        decisions["public_abi_preflight_candidate_intake"]["non_claim"] = "promotes public ABI"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_public_abi_preflight_candidate_intake_checker_mismatch", report["blockers"])
        self.assertIn("decisions_public_abi_preflight_candidate_intake_default_manifest_mismatch", report["blockers"])
        self.assertIn("decisions_public_abi_preflight_candidate_intake_non_claim_mismatch", report["blockers"])

        decisions = self.load_decisions()
        decisions.pop("public_abi_preflight_candidate_intake")
        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_public_abi_preflight_candidate_intake_missing", report["blockers"])

    def test_rejects_missing_or_weakened_owner_token_sdk_consumer_contract_intake(self) -> None:
        decisions = self.load_decisions()
        decisions["owner_token_sdk_consumer_contract_intake"]["id"] = "owner_token_contract"
        decisions["owner_token_sdk_consumer_contract_intake"]["status"] = "accepted"
        decisions["owner_token_sdk_consumer_contract_intake"]["resolved_input"] = "lifecycle.owner_cleanup"
        decisions["owner_token_sdk_consumer_contract_intake"]["required_checker"] = "scripts/other.py"
        decisions["owner_token_sdk_consumer_contract_intake"]["default_manifest"] = "docs/research/other.json"
        decisions["owner_token_sdk_consumer_contract_intake"]["non_claim"] = "promotes owner cleanup"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_id_mismatch", report["blockers"])
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_status_mismatch", report["blockers"])
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_resolved_input_mismatch", report["blockers"])
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_checker_mismatch", report["blockers"])
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_default_manifest_mismatch", report["blockers"])
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_non_claim_mismatch", report["blockers"])

        decisions = self.load_decisions()
        decisions.pop("owner_token_sdk_consumer_contract_intake")
        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_owner_token_sdk_consumer_contract_intake_missing", report["blockers"])

    def test_rejects_public_abi_preflight_sdk_consumer_overclaim(self) -> None:
        preflight = self.load_public_abi_preflight_candidate()
        preflight["sdk_consumer_contract"] = {
            "status": "blocked",
            "candidate_only": True,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": True,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "required_behavior": [
                "consumer checks the captured capability bit before registering identity callbacks",
            ],
            "does_not_resolve": ["sdk.consumer"],
        }

        result = self.run_checker(public_abi_preflight_candidate=preflight)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn(
            "sdk_consumer_contract_public_sdk_ready_not_false",
            report["public_abi_promotion_preflight"]["blockers"],
        )
        self.assertIn(
            "sdk_consumer_contract_required_behavior_missing",
            report["public_abi_promotion_preflight"]["blockers"],
        )

    def test_sanitizes_public_abi_preflight_helper_overclaims(self) -> None:
        overclaim = {
            "status": "blocked",
            "candidate_only": True,
            "accepted_for_candidate_review": True,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "public_header_allowed": True,
            "public_contract_allowed": True,
            "public_abi_ready": True,
            "v1_completion_evidence": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerIdentityCallback"],
            "sdk_consumer_contract": {
                "accepted_for_contract_review": True,
                "public_sdk_ready": True,
                "public_header_symbols_now": ["RegisterPlayerIdentityCallback"],
            },
            "blockers": [],
        }

        blockers: list[dict] = []
        with mock.patch.object(checker.public_abi_preflight_candidate, "build_report", return_value=overclaim):
            report = checker.validate_public_abi_preflight_candidate(
                PUBLIC_ABI_PREFLIGHT_CANDIDATE,
                PRIVATE_POD_LAYOUT_CANDIDATE,
                PRIVATE_CANDIDATE,
                HEADER,
                blockers,
                {"accepted_for_contract_review": True, "blockers": []},
                {"accepted_for_policy_review": True, "candidate_only": True, "blockers": []},
            )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("nested_readiness_flag_not_false", reasons)
        self.assertIn("nested_public_header_symbols_now_not_empty", reasons)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_contract_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertFalse(report["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertEqual(report["sdk_consumer_contract"]["public_header_symbols_now"], [])

    def test_sanitizes_owner_token_sdk_consumer_helper_overclaims(self) -> None:
        import check_player_identity_owner_token_sdk_consumer_contract as owner_token_checker

        overclaim = {
            "ready": True,
            "accepted_for_candidate_review": True,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "public_header_allowed": True,
            "public_abi_ready": True,
            "v1_completion_evidence": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerIdentityCallback"],
            "sdk_consumer": {
                "public_sdk_ready": True,
                "public_header_symbols_now": ["RegisterPlayerIdentityCallback"],
            },
            "blockers": [],
        }

        blockers: list[dict] = []
        with mock.patch.object(owner_token_checker, "build_report", return_value=overclaim):
            report = checker.validate_owner_token_sdk_consumer_contract(
                checker.DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT,
                PUBLIC_ABI_PREFLIGHT_CANDIDATE,
                HEADER,
                blockers,
                {"sdk_consumer_contract": {}, "required_owner_token_lifecycle": []},
            )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("nested_readiness_flag_not_false", reasons)
        self.assertIn("nested_public_header_symbols_now_not_empty", reasons)
        self.assertTrue(report["provided"])
        self.assertEqual(report["source"], "owner_token_sdk_consumer_contract")
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertFalse(report["sdk_consumer"]["public_sdk_ready"])
        self.assertEqual(report["sdk_consumer"]["public_header_symbols_now"], [])

    def test_rejects_invalid_identifier_redaction_evidence(self) -> None:
        evidence = self.load_identifier_redaction_evidence()
        evidence["promotion_ready"] = True
        evidence["fields"][0]["field_class"] = "recognition-only"

        result = self.run_checker(identifier_redaction_evidence=evidence)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["primary_offline_gap"], "privacy.identifier_redaction")
        self.assertEqual(
            report["contract_review_inputs_resolved"],
            [
                "planning.source_bound_committed_manifests",
                "lifetime.generation_scope_invalidation.candidate_policy",
            ],
        )
        self.assertIn("privacy.identifier_redaction", report["remaining_contract_gate_inputs"])
        self.assertIn("identifier_redaction_evidence_not_accepted", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["identifier_redaction_evidence"]["blockers"])
        self.assertIn("required_identifier_class_not_redacted", report["identifier_redaction_evidence"]["blockers"])

    def test_rejects_invalid_principal_invalidation_policy(self) -> None:
        policy = self.load_principal_invalidation_policy()
        policy["negative_consumer_rules"] = [
            item
            for item in policy["negative_consumer_rules"]
            if item.get("rule") != "fail_closed_on_invalid_or_stale"
        ]

        result = self.run_checker(principal_invalidation_policy=policy)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["primary_offline_gap"], "lifetime.generation_scope_invalidation")
        self.assertEqual(
            report["contract_review_inputs_resolved"],
            ["privacy.identifier_redaction", "planning.source_bound_committed_manifests"],
        )
        lifetime_action = next(
            action
            for action in report["next_offline_actions"]
            if action["id"] == "lifetime.generation_scope_invalidation"
        )
        self.assertFalse(lifetime_action["candidate_policy_accepted"])
        self.assertIn("principal_invalidation_policy_not_accepted", report["blockers"])
        self.assertIn("negative_consumer_rules_missing_required", report["principal_invalidation_policy"]["blockers"])

    def test_rejects_invalid_private_pod_layout_candidate_without_resolving_abi(self) -> None:
        layout = self.load_private_pod_layout_candidate()
        layout["event_payload_layout"]["fields"][2]["offset"] = 16
        layout["promotion_ready"] = True

        result = self.run_checker(private_pod_layout_candidate=layout)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            report["contract_review_inputs_resolved"],
            [
                "privacy.identifier_redaction",
                "planning.source_bound_committed_manifests",
                "lifetime.generation_scope_invalidation.candidate_policy",
            ],
        )
        self.assertIn("abi.public_pod_contract", report["remaining_contract_gate_inputs"])
        self.assertIn("private_pod_layout_candidate_not_accepted", report["blockers"])
        self.assertIn("event_payload_layout_fields_mismatch", report["private_pod_layout_candidate"]["blockers"])
        self.assertFalse(report["private_pod_layout_candidate"]["accepted_for_contract_review_input"])

    def test_rejects_stale_source_bound_planning_manifest_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            planning_dir = Path(tempdir) / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs" / "research" / "player-identity-planning-sources"),
                    str(planning_dir),
                ],
                check=True,
            )
            stale_path = planning_dir / "players-identity-lifecycle-anchor-candidates.json"
            stale = json.loads(stale_path.read_text(encoding="utf-8"))
            stale["candidate_anchors"] = []
            stale_path.write_text(json.dumps(stale), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--planning-sources-dir",
                    str(planning_dir),
                    "--json",
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
        )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_bound_planning_manifest_verification_not_accepted", report["blockers"])
        source_verification = report["source_bound_planning_manifest_verification"]
        self.assertFalse(source_verification["accepted_for_contract_review"])
        source_reasons = [
            blocker["reason"] if isinstance(blocker, dict) else blocker
            for blocker in source_verification["blockers"]
        ]
        self.assertIn(
            "stale_or_mismatched_planning_manifest",
            source_reasons,
        )
        self.assertFalse(source_verification["promotion_ready"])
        self.assertFalse(source_verification["public_sdk_ready"])
        self.assertFalse(source_verification["runtime_ready"])
        self.assertFalse(source_verification["public_abi_ready"])
        self.assertFalse(source_verification["v1_completion_ready"])

    def test_rejects_symlinked_identifier_redaction_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            decisions_path = root / "decisions.json"
            surfaces_path = root / "surfaces.json"
            candidate_path = root / "private-candidate.json"
            evidence_target = root / "identifier-redaction-target.json"
            redaction_link = root / "identifier-redaction-link.json"
            principal_policy_path = root / "principal-invalidation-policy.json"
            private_pod_layout_path = root / "private-pod-layout-candidate.json"
            header_path = root / "ObeliskApi.h"

            decisions_path.write_text(json.dumps(self.load_decisions()), encoding="utf-8")
            surfaces_path.write_text(json.dumps(self.load_surfaces()), encoding="utf-8")
            candidate_path.write_text(json.dumps(self.load_private_candidate()), encoding="utf-8")
            evidence_target.write_text(json.dumps(self.load_identifier_redaction_evidence()), encoding="utf-8")
            principal_policy_path.write_text(json.dumps(self.load_principal_invalidation_policy()), encoding="utf-8")
            private_pod_layout_path.write_text(json.dumps(self.load_private_pod_layout_candidate()), encoding="utf-8")
            redaction_link.symlink_to(evidence_target)
            header_path.write_text(HEADER.read_text(encoding="utf-8"), encoding="utf-8")

            result = self.run_checker_with_paths(
                decisions_path=decisions_path,
                surfaces_path=surfaces_path,
                candidate_path=candidate_path,
                redaction_path=redaction_link,
                principal_policy_path=principal_policy_path,
                private_pod_layout_path=private_pod_layout_path,
                header_path=header_path,
            )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["primary_offline_gap"], "privacy.identifier_redaction")
        self.assertIn("identifier_redaction_evidence_unreadable_or_rejected", report["blockers"])
        self.assertEqual(
            report["identifier_redaction_evidence"]["blockers"],
            ["identifier_redaction_evidence_unreadable_or_rejected"],
        )

    def test_rejects_missing_runtime_and_privacy_promotion_blockers(self) -> None:
        decisions = self.load_decisions()
        decisions["promotion_blockers"] = [
            item
            for item in decisions["promotion_blockers"]
            if item["id"] not in {"runtime.lifecycle_evidence", "privacy.identifier_redaction"}
        ]

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_promotion_blockers_missing", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "decisions_required_promotion_blockers_missing"
        )
        self.assertEqual(["privacy.identifier_redaction", "runtime.lifecycle_evidence"], detail["missing"])

    def test_rejects_missing_privacy_required_before_public_header_items(self) -> None:
        decisions = self.load_decisions()
        decisions["required_before_public_header"] = [
            item
            for item in decisions["required_before_public_header"]
            if item["id"] != "privacy.logging_and_storage_policy"
        ]

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_privacy_public_header_blockers_missing", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "decisions_required_privacy_public_header_blockers_missing"
        )
        self.assertEqual(["privacy.logging_and_storage_policy"], detail["missing"])

    def test_rejects_public_contract_gate_or_runtime_evidence_limit_weakened(self) -> None:
        decisions = self.load_decisions()
        decisions["decision_gate"]["current_decision"] = "runtime evidence accepted; identity can unlock permissions"
        decisions["decision_gate"]["scope"] = "identity runtime route is ready for downstream permissions"
        decisions["decision_gate"]["allowed_now"] = [
            "document blockers",
            "document candidate POD shape",
            "public readiness",
        ]
        decisions["decision_gate"]["forbidden_now"].remove("permission/admin API")
        decisions["forbidden_public_contract"].remove("UE pointers")
        decisions["approved_runtime_evidence_not_sufficient"]["why"].remove(
            "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["minimum_additional_gates"].remove(
            "cross-instance/process-local scope decision resolved"
        )

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "decisions_decision_gate_current_decision_mismatch",
            "decisions_decision_gate_scope_mismatch",
            "decisions_decision_gate_allowed_now_mismatch",
            "decisions_decision_gate_forbidden_now_missing_required",
            "decisions_forbidden_public_contract_missing_required",
            "decisions_approved_runtime_evidence_not_sufficient_why_missing",
            "decisions_approved_runtime_evidence_not_sufficient_minimum_gates_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_privacy_lifecycle_scope_or_downstream_policy_weakened(self) -> None:
        decisions = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        requirements["privacy.public_identifier_form"]["must_not_expose"].remove("SteamID")
        requirements["privacy.public_identifier_form"]["required_properties"].remove(
            "generation-bearing or otherwise invalidation-aware"
        )
        requirements["privacy.redacted_identifier_fields"]["must_redact"].remove("player names")
        requirements["privacy.logging_and_storage_policy"]["default_policy"] = "log player names for moderation"
        requirements["lifetime.principal_scope"]["allowed_scopes"].append("cluster-stable")
        requirements["lifetime.principal_scope"]["forbidden_until_separate_promotion"].remove("cluster-stable")
        requirements["lifetime.principal_scope"]["required_fields"].remove("principal_generation")
        requirements["lifetime.invalidation_events"]["required_behavior"].remove("stale principal fails closed")
        requirements["lifetime.reconnect_duplicate_stale_policy"]["required_policy"].remove(
            "stale handles never resolve to a different player"
        )
        requirements["abi.payload_shape"]["required_properties"].remove("no UE pointers or raw params")
        requirements["abi.capability_bits"]["required_behavior"].remove("missing capability fails closed")
        requirements["abi.owner_token_registration"]["required_behavior"].remove(
            "registration handles are not persisted or shared across server processes"
        )
        requirements["separation.no_commands_permissions_persistence"]["v1_sequence_gate"][1] = (
            "permission query contract may use runtime evidence directly"
        )
        requirements["separation.no_commands_permissions_persistence"]["forbidden_in_identity_contract"].remove(
            "command response API"
        )

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "decisions_privacy_public_identifier_form_missing_forbidden_terms",
            "decisions_privacy_public_identifier_form_missing_required_properties",
            "decisions_privacy_redacted_identifier_fields_missing_redactions",
            "decisions_privacy_logging_storage_default_policy_mismatch",
            "decisions_lifetime_principal_scope_forbidden_scope_allowed",
            "decisions_lifetime_principal_scope_missing_forbidden_scopes",
            "decisions_lifetime_principal_scope_missing_required_fields",
            "decisions_lifetime_invalidation_behavior_missing",
            "decisions_lifetime_reconnect_duplicate_stale_policy_missing",
            "decisions_abi_payload_shape_missing_required_properties",
            "decisions_abi_capability_bits_missing_fail_closed_behavior",
            "decisions_abi_owner_token_registration_missing_fail_closed_behavior",
            "decisions_separation_sequence_gate_mismatch",
            "decisions_separation_forbidden_downstream_surfaces_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_privacy_required_before_public_header_marked_resolved(self) -> None:
        decisions = self.load_decisions()
        for item in decisions["required_before_public_header"]:
            if item["id"] == "privacy.public_identifier_form":
                item["status"] = "resolved"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_privacy_public_header_blocker_not_unresolved", report["blockers"])

    def test_rejects_surface_promotion_or_public_contract(self) -> None:
        surfaces = self.load_surfaces()
        surface = self.player_identity_surface(surfaces)
        surface["status"] = "promoted"
        surface["public_contract"] = ["ObeliskRegisterPlayerIdentityCallback"]
        surfaces["planning_surfaces"].remove(checker.SURFACE)
        surfaces["promoted_surfaces"].append(checker.SURFACE)

        result = self.run_checker(surfaces=surfaces)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("player_identity_surface_status_not_planning", report["blockers"])
        self.assertIn("player_identity_surface_public_contract_not_empty", report["blockers"])
        self.assertIn("player_identity_missing_from_planning_surfaces", report["blockers"])
        self.assertIn("player_identity_in_non_planning_surface_list", report["blockers"])

    def test_rejects_identity_or_principal_symbols_in_public_header(self) -> None:
        header = "\n".join(
            [
                "#pragma once",
                "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)",
                "// ObeliskPlayerPrincipalEvent in a comment is ignored.",
                "static const char* ignored = \"RegisterPlayerIdentity\";",
                "#define OBELISK_API_CAPABILITY_PLAYER_IDENTITY (1ull << 12)",
                "#define OBELISK_API_CAPABILITY_PLAYER_SESSION (1ull << 13)",
                "typedef struct ObeliskPlayerPrincipalEvent { uint64_t principal_handle; } ObeliskPlayerPrincipalEvent;",
                "typedef uint64_t ObeliskPlayerIdentityHandle;",
                "typedef struct ObeliskPlayerSession { uint64_t x; } ObeliskPlayerSession;",
                "typedef void (*ObeliskPlayerCallback)(void* userData);",
                "uint64_t (*RegisterPlayerLifecycleWithOwnerToken)(uint64_t ownerToken);",
                "uint64_t (*RegisterPlayerLogoutWithOwnerToken)(uint64_t ownerToken);",
                "typedef struct ObeliskPlayerConnectEvent { uint64_t x; } ObeliskPlayerConnectEvent;",
                "typedef struct ObeliskPlayerDisconnectEvent { uint64_t x; } ObeliskPlayerDisconnectEvent;",
                "typedef struct ObeliskPlayerJoinEvent { uint64_t x; } ObeliskPlayerJoinEvent;",
                "typedef struct ObeliskPlayerLeaveEvent { uint64_t x; } ObeliskPlayerLeaveEvent;",
            ]
        )

        result = self.run_checker(header_text=header)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_identity_or_principal_symbols_detected")
        detected = {item["token"] for item in detail["detected_tokens"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", detected)
        self.assertIn("ObeliskPlayerPrincipalEvent", detected)
        self.assertIn("principal_handle", detected)
        self.assertIn("ObeliskPlayerIdentityHandle", detected)
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_SESSION", detected)
        self.assertIn("ObeliskPlayerSession", detected)
        self.assertIn("ObeliskPlayerCallback", detected)
        self.assertIn("RegisterPlayerLifecycleWithOwnerToken", detected)
        self.assertIn("RegisterPlayerLogoutWithOwnerToken", detected)
        self.assertIn("ObeliskPlayerConnectEvent", detected)
        self.assertIn("ObeliskPlayerDisconnectEvent", detected)
        self.assertIn("ObeliskPlayerJoinEvent", detected)
        self.assertIn("ObeliskPlayerLeaveEvent", detected)
        self.assertNotIn("OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY", detected)

    def test_rejects_forbidden_positive_identity_exposure_in_private_candidate(self) -> None:
        candidate = self.load_private_candidate()
        candidate["candidate_event_payload_fields_or_equivalent"].extend(
            [
                "steam_id",
                "EOS_account_id",
                "UniqueNetId",
                "PlayerDataID",
                "player_name",
                "tribe_id",
                "IP_address",
                "UE_pointer",
                "FName_index",
                "GObjects_index",
                "ResourceHandle",
                "lookup_handle",
                "persistent_identity",
                "mutation_token",
                "return_override_policy",
            ]
        )

        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_forbidden_public_identity_exposure", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "private_candidate_forbidden_public_identity_exposure")
        terms = {item["term"] for item in detail["exposures"]}
        self.assertEqual(
            terms,
            {
                "steam_id",
                "eos",
                "unique_net_id",
                "player_data_id",
                "player_name",
                "tribe",
                "ip_or_network_address",
                "ue_pointer",
                "fname_gobjects",
                "resource_handle",
                "lookup",
                "persistence",
                "mutation",
                "return_override",
            },
        )

    def test_custom_private_candidate_contract_drift_reaches_nested_layout_and_preflight_checks(self) -> None:
        candidate = self.load_private_candidate()
        candidate["candidate_event_payload_fields_or_equivalent"].append("custom_contract_drift_probe")

        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_pod_layout_candidate_not_accepted", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn(
            "event_layout_private_contract_fields_mismatch",
            report["private_pod_layout_candidate"]["blockers"],
        )
        self.assertIn(
            "private_pod_layout_candidate_not_accepted",
            report["public_abi_promotion_preflight"]["blockers"],
        )

    def test_rejects_positive_identity_exposure_before_later_unrelated_negative_clause(self) -> None:
        candidate = self.load_private_candidate()
        candidate["candidate_event_payload_fields_or_equivalent"].extend(
            [
                "SteamID copied into candidate payload; no lookup API is exposed",
                "PlayerDataID copied into candidate payload; no lookup API is exposed",
            ]
        )

        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_forbidden_public_identity_exposure", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "private_candidate_forbidden_public_identity_exposure")
        terms = {item["term"] for item in detail["exposures"]}
        self.assertIn("steam_id", terms)
        self.assertIn("player_data_id", terms)

    def test_rejects_private_candidate_missing_stale_handle_fail_closed_rule(self) -> None:
        candidate = self.load_private_candidate()
        candidate["candidate_stale_handle_fail_closed_semantics"].remove(
            "stale handles never resolve to a different player"
        )

        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_stale_handle_fail_closed_semantics_missing", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "private_candidate_stale_handle_fail_closed_semantics_missing"
        )
        self.assertIn("stale handles never resolve to a different player", detail["missing"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_forbidden_negative_non_claims_remain_allowed(self) -> None:
        candidate = copy.deepcopy(self.load_private_candidate())

        self.assertEqual(checker.candidate_exposures(candidate), [])
        result = self.run_checker(candidate=candidate)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, report["blocker_details"])
        self.assertEqual(report["blockers"], [])


if __name__ == "__main__":
    unittest.main()
