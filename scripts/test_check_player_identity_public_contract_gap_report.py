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
from datetime import datetime, timezone
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

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (  # noqa: E402
    SAFE_OFFLINE_WORKSPACE,
    manifest as approved_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)
from test_check_player_identity_public_contract_decision_record import (  # noqa: E402
    TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL,
    TEST_STRICT_REPORT_SENTINEL,
    accepted_record,
    strict_approved_runtime_check_report_ref,
)


RUNTIME_FIXTURE_SITECUSTOMIZE = """
import check_player_identity_runtime_principal_lifecycle_approved_evidence as _obelisk_approved_evidence
_obelisk_original_accepted_runtime_validate_manifest = _obelisk_approved_evidence.validate_manifest
_obelisk_original_accepted_runtime_build_report = _obelisk_approved_evidence.build_report


class _ObeliskAcceptedRuntimeValidation:
    blockers = []


def _obelisk_accepted_runtime_validate_manifest(payload, *, check_mode, **kwargs):
    return _obelisk_original_accepted_runtime_validate_manifest(
        payload,
        check_mode=check_mode,
        **kwargs,
    )


def _obelisk_accepted_runtime_build_report(payload, validation, *, check_mode):
    return _obelisk_original_accepted_runtime_build_report(
        payload,
        validation,
        check_mode=check_mode,
    )


_obelisk_approved_evidence.validate_manifest = _obelisk_accepted_runtime_validate_manifest
_obelisk_approved_evidence.build_report = _obelisk_accepted_runtime_build_report
"""

SPEC = importlib.util.spec_from_file_location("player_identity_gap_report_checker", SCRIPT)
assert SPEC is not None
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class PlayerIdentityPublicContractGapReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._planning_sources_tmp = tempfile.TemporaryDirectory()
        cls.planning_sources_dir = Path(cls._planning_sources_tmp.name) / "planning"
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "build_player_identity_planning_source_manifests.py"),
                "--output-dir",
                str(cls.planning_sources_dir),
            ],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._planning_sources_tmp.cleanup()

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

    @staticmethod
    def runtime_fixture_now_utc() -> datetime:
        return datetime(2026, 6, 1, 12, 16, 0, tzinfo=timezone.utc)

    def player_identity_surface(self, surfaces: dict) -> dict:
        return next(item for item in surfaces["surfaces"] if item["id"] == checker.SURFACE)

    def bound_decision_record(self, approved_runtime_evidence: dict) -> dict:
        record = accepted_record()
        record[TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL] = copy.deepcopy(approved_runtime_evidence)
        record[TEST_STRICT_REPORT_SENTINEL] = None
        record["approved_runtime_evidence_binding"] = (
            checker.public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(
                approved_runtime_evidence
            )
        )
        return record

    def write_identity_contract_record(self, path: Path, record: dict) -> None:
        payload = copy.deepcopy(record)
        runtime_manifest = payload.pop(TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL, None)
        runtime_manifest_path = None
        if runtime_manifest is not None:
            runtime_manifest_path = path.parent / "approved-runtime-principal-lifecycle-evidence.json"
            runtime_manifest_path.write_text(
                json.dumps(runtime_manifest, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            payload[
                checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD
            ] = checker.public_contract_decision_record.approved_runtime_evidence_manifest_ref(
                runtime_manifest_path
            )
        strict_report = payload.pop(TEST_STRICT_REPORT_SENTINEL, None)
        if strict_report is not None:
            report_path = path.parent / "approved-runtime-principal-lifecycle-evidence.check.json"
            report_path.write_text(json.dumps(strict_report, sort_keys=True) + "\n", encoding="utf-8")
            payload["strict_approved_runtime_checker_contract_report"] = (
                strict_approved_runtime_check_report_ref(report_path)
            )
        elif TEST_STRICT_REPORT_SENTINEL in record:
            self.assertIsNotNone(runtime_manifest)
            self.assertIsNotNone(runtime_manifest_path)
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_runtime_evidence, "now_utc", self.runtime_fixture_now_utc),
                mock.patch.object(
                    checker.approved_runtime_evidence,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    [SAFE_OFFLINE_WORKSPACE],
                ),
                mock.patch.object(
                    checker.approved_runtime_evidence.window_manifest_checker,
                    "now_utc",
                    self.runtime_fixture_now_utc,
                ),
                mock.patch.object(
                    checker.approved_runtime_evidence.window_manifest_checker,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    [SAFE_OFFLINE_WORKSPACE],
                ),
            ):
                validation = checker.approved_runtime_evidence.validate_manifest(
                    runtime_manifest,
                    check_mode="consume",
                    input_path=runtime_manifest_path,
                )
                strict_report = checker.approved_runtime_evidence.build_report(
                    runtime_manifest,
                    validation,
                    check_mode="consume",
                )
            report_path = path.parent / "approved-runtime-principal-lifecycle-evidence.check.json"
            report_path.write_text(
                json.dumps(strict_report, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            payload["strict_approved_runtime_checker_contract_report"] = (
                strict_approved_runtime_check_report_ref(report_path)
            )
        path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")

    def assert_post_runtime_gap_summary_closed(self, summary: dict) -> None:
        for key in (
            "permissions_admin_opened",
            "permissions_admin_ready",
            "permissions_admin_public_ready",
            "permissions_admin_unlocked",
            "command_response_ready",
            "command_chat_response_ready",
            "commands_replies_ready",
            "promotion_ready",
            "public_contract_allowed",
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
            "public_sdk_v1_completion_ready",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(post_runtime_gap_false_flag=key):
                self.assertFalse(summary[key])
        self.assertEqual(summary["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(summary["p0_dependency_chain_claim_progress_contribution"], 0)

    def assert_post_runtime_contract_gap_diagnostic_closed(self, diagnostic: dict) -> None:
        self.assertTrue(diagnostic["fail_closed"])
        self.assertEqual(
            diagnostic["only_valid_post_runtime_route"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            diagnostic["blocked_surfaces_must_remain_false"],
            checker.POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_BLOCKED_SURFACES,
        )
        self.assertIn("permissions_admin", diagnostic["blocked_surfaces_must_remain_false"])
        self.assertIn("p0_progress", diagnostic["blocked_surfaces_must_remain_false"])
        for key in (
            "promotion_ready",
            "public_contract_allowed",
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "public_readiness",
            "runtime_ready",
            "runtime_readiness",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
            "complete_sdk_ready",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(post_runtime_contract_gap_false_flag=key):
                self.assertFalse(diagnostic[key])
        self.assertEqual(diagnostic["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(diagnostic["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(
            diagnostic["non_claim"],
            checker.REQUIRED_POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_NON_CLAIM,
        )

    def assert_runtime_contract_currentness_closed(
        self,
        currentness: dict,
        *,
        runtime_accepted: bool | None = None,
        reviewed_record_accepted: bool | None = None,
    ) -> None:
        required = checker.public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC
        for key, expected in required.items():
            with self.subTest(runtime_currentness_key=key):
                self.assertEqual(currentness[key], expected)
        self.assertFalse(currentness["accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"])
        self.assertFalse(currentness["accepted_runtime_evidence_can_replace_reviewed_record"])
        self.assertFalse(currentness["candidate_preflight_review_aliases_count"])
        self.assertFalse(currentness["candidate_preflight_review_aliases_can_clear_gate"])
        self.assertFalse(currentness["candidate_preflight_review_aliases_can_replace_reviewed_record"])
        self.assertFalse(currentness["permissions_admin_unlocked_from_runtime_evidence"])
        self.assertFalse(currentness["command_surface_unlocked_from_runtime_evidence"])
        self.assertEqual(
            currentness["only_next_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        if runtime_accepted is not None:
            self.assertEqual(currentness["runtime_evidence_accepted"], runtime_accepted)
            if runtime_accepted:
                self.assertEqual(currentness["next_blocker"], "identity_public_contract_gate_missing")
        if reviewed_record_accepted is not None:
            self.assertEqual(currentness["reviewed_decision_record_accepted"], reviewed_record_accepted)
        observed = currentness.get("observed")
        if observed is not None:
            self.assertEqual(observed["next_blocker"], "identity_public_contract_gate_missing")
            self.assertFalse(
                observed["accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"]
            )
            self.assertFalse(observed["candidate_preflight_review_aliases_count"])
            self.assertFalse(observed["permissions_admin_unlocked_from_runtime_evidence"])
            self.assertFalse(observed["command_surface_unlocked_from_runtime_evidence"])

    def approved_runtime_fixture_env(
        self,
        approved_runtime_evidence: dict | None,
        fixture_root: Path,
    ) -> dict[str, str]:
        env = {**approved_runtime_safe_test_env(), "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}
        if approved_runtime_evidence is not None:
            pythonpath_entries = [str(fixture_root), str(SCRIPT_DIR)]
            if env.get("PYTHONPATH"):
                pythonpath_entries.append(env["PYTHONPATH"])
            env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        if approved_runtime_evidence is None:
            return env

        source_path = (
            approved_runtime_evidence.get("source_summary", {})
            .get("evidence", {})
            .get("sources", [{}])[0]
            .get("path")
        )
        if not isinstance(source_path, str):
            return env

        path = Path(source_path)
        for candidate in (path, *path.parents):
            if candidate.name.startswith("obelisk-safe-offline-workspace-"):
                env["OBELISK_TEST_APPROVED_OFFLINE_WORKSPACE"] = str(candidate)
                break
        return env

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
        identity_public_contract_decision_record_path: Path | None = None,
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
                (root / "sitecustomize.py").write_text(
                    RUNTIME_FIXTURE_SITECUSTOMIZE,
                    encoding="utf-8",
                )
                approved_runtime_args = ["--approved-runtime-evidence", str(approved_runtime_path)]
            header_path.write_text(header_text if header_text is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")
            owner_token_contract_args = []
            if owner_token_sdk_consumer_contract_path is not None:
                owner_token_contract_args = [
                    "--owner-token-sdk-consumer-contract",
                    str(owner_token_sdk_consumer_contract_path),
                ]
            decision_record_args = []
            if identity_public_contract_decision_record_path is not None:
                decision_record_args = [
                    "--identity-public-contract-decision-record",
                    str(identity_public_contract_decision_record_path),
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
                    "--planning-sources-dir",
                    str(self.planning_sources_dir),
                    *approved_runtime_args,
                    *owner_token_contract_args,
                    *decision_record_args,
                    "--public-header",
                    str(header_path),
                    "--json",
                ],
                cwd=REPO_ROOT,
                env=self.approved_runtime_fixture_env(approved_runtime_evidence, root),
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
            "--planning-sources-dir",
            str(self.planning_sources_dir),
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
        for alias in (
            "identityPublicContractReady",
            "publicIdentityReady",
            "publicPrincipalReady",
            "lookupReady",
            "permissionsReady",
            "commandsReady",
            "stableSdkReady",
            "stableReleaseReady",
            "pluginHubReady",
            "pluginHubPublicationReady",
            "publicationReady",
            "publicationAuthorized",
            "identityHeaderReady",
            "principalLookupReady",
            "identityLookupReady",
            "publicLookupReady",
            "runtimePrincipalReady",
            "realIdentityReady",
            "redactionEvidencePromotesIdentity",
        ):
            self.assertFalse(report["public_contract_gate_aliases"][alias])
        self.assertEqual(
            set(report["public_contract_gate_aliases"]),
            checker.REQUIRED_ALIAS_GUARDRAILS_FALSE,
        )
        for alias, value in report["public_contract_gate_aliases"].items():
            with self.subTest(alias=alias):
                self.assertFalse(value)
        self.assertFalse(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(
            report["identity_public_contract_gate_missing"]["redactionEvidencePromotesIdentity"]
        )
        self.assertIn(
            "runtime principal lifecycle evidence is absent; identity promotion remains blocked "
            "pending accepted runtime lifecycle evidence and reviewed identity-contract evidence",
            report["public_identity_non_promotional_reasons"],
        )
        self.assertTrue(
            any(
                "readiness-alias artifacts cannot resolve runtime.lifecycle_evidence" in reason
                for reason in report["public_identity_non_promotional_reasons"]
            )
        )
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["primary_offline_gap"], "lifetime.generation_scope_invalidation")
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]
        self.assertFalse(post_runtime_gate["active"])
        self.assertEqual(
            post_runtime_gate["id"],
            "identity_public_contract_gate.reviewed_identity_public_contract",
        )
        self.assertEqual(post_runtime_gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assert_runtime_contract_currentness_closed(
            post_runtime_gate["runtime_evidence_contract_review_currentness"]
        )
        self.assert_runtime_contract_currentness_closed(
            report["identity_public_contract_gate_missing"]["runtime_evidence_contract_review_currentness"]
        )
        self.assert_runtime_contract_currentness_closed(
            report["runtime_evidence_contract_review_currentness"],
            runtime_accepted=False,
            reviewed_record_accepted=False,
        )
        self.assertEqual(
            post_runtime_gate["required_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_gate["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        route_check = report["post_approved_runtime_evidence_route_check"]
        self.assertTrue(route_check["gap_report_valid"])
        self.assertFalse(route_check["invalid_gap_report"])
        self.assertFalse(route_check["remaining_route_blocker_is_legitimate"])
        self.assertIsNone(route_check["legitimate_remaining_route_blocker"])
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, post_runtime_gate["required_unresolved_decision_keys"])
                self.assertIn(key, post_runtime_gate["remaining_unresolved_decision_keys"])
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(post_runtime_gate[key])
        self.assertEqual(
            report["contract_review_inputs_resolved"],
            [
                "privacy.identifier_redaction",
                "lifetime.generation_scope_invalidation.candidate_policy",
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
            ],
        )
        self.assertEqual(report["remaining_contract_review_inputs"], ["runtime.lifecycle_evidence"])
        self.assertEqual(
            report["remaining_post_runtime_inputs"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        self.assertIn("runtime.lifecycle_evidence", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.principal_scope", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.invalidation_events", report["remaining_contract_gate_inputs"])
        self.assertIn("lifetime.reconnect_duplicate_stale_policy", report["remaining_contract_gate_inputs"])
        self.assertIn("abi.public_pod_contract", report["remaining_contract_gate_inputs"])
        unresolved_decision_keys = report["unresolved_public_contract_decision_keys"]
        self.assertEqual(
            unresolved_decision_keys,
            [
                item["id"]
                for item in self.load_decisions()["required_before_public_header"]
                if item["status"] == "unresolved"
            ],
        )
        self.assertIn("privacy.public_identifier_form", unresolved_decision_keys)
        self.assertIn("lifetime.principal_scope", unresolved_decision_keys)
        self.assertIn("abi.payload_shape", unresolved_decision_keys)
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
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["provided"])
        self.assertFalse(record["record_valid"])
        self.assertFalse(record["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record["contract_review_only"])
        self.assertFalse(record["accepted_for_contract_review"])
        self.assertEqual(record["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(record["source_artifact_freshness"]["current"])
        self.assertEqual(
            record["source_artifact_freshness"]["mismatches"][0]["label"],
            "public_contract_decisions",
        )
        self.assertIn("source_artifact_hash_mismatch", record["blockers"])
        self.assertIn("approved_runtime_evidence_binding_missing_or_not_object", record["blockers"])
        self.assertEqual(record["resolved_decision_keys"], [])
        self.assertEqual(record["review_inputs_non_counting_until"], "runtime.lifecycle_evidence")
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
        self.assertFalse(source_verification["accepted_for_contract_review"])
        self.assertIsNone(source_verification["resolved_input"])
        self.assertTrue(source_verification["provenance_verified"])
        self.assertTrue(source_verification["provenance_only"])
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

    def test_default_repo_gap_report_keeps_expected_route_with_current_planning_sources(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            cwd=REPO_ROOT,
            env={**os.environ, "OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"},
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["guardrail_passed"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["blockers"], [])
        self.assertNotIn(
            "planning.source_bound_committed_manifests",
            report["contract_review_inputs_resolved"],
        )

        source_verification = report["source_bound_planning_manifest_verification"]
        self.assertTrue(source_verification["provided"])
        self.assertFalse(source_verification["accepted_for_contract_review"])
        self.assertIsNone(source_verification["resolved_input"])
        self.assertTrue(source_verification["provenance_verified"])
        self.assertTrue(source_verification["provenance_only"])
        self.assertTrue(source_verification["planning_only"])
        self.assertFalse(source_verification["default_first_evidence_stale_diagnostic"])
        self.assertIsNone(source_verification["stale_source_artifact_policy"])
        self.assertEqual(source_verification["blockers"], [])
        for key in (
            "promotion_ready",
            "public_sdk_ready",
            "runtime_ready",
            "public_abi_ready",
            "v1_completion_ready",
            "server_operations_authorized",
            "runtime_work_authorized",
        ):
            with self.subTest(key=key):
                self.assertFalse(source_verification[key])

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
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertFalse(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]
        self.assertTrue(post_runtime_gate["active"])
        self.assertEqual(post_runtime_gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assert_runtime_contract_currentness_closed(
            post_runtime_gate["runtime_evidence_contract_review_currentness"]
        )
        self.assert_runtime_contract_currentness_closed(
            report["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=False,
        )
        route_check = report["post_approved_runtime_evidence_route_check"]
        self.assertTrue(route_check["contract_review_input_present"])
        self.assertTrue(route_check["gap_report_valid"])
        self.assertFalse(route_check["invalid_gap_report"])
        self.assertTrue(route_check["remaining_route_blocker_is_legitimate"])
        self.assertEqual(
            route_check["legitimate_remaining_route_blocker"],
            "identity_public_contract_gate_missing",
        )
        for surface in ("permissions_admin", "command_chat", "sdk_readiness", "p0_progress"):
            with self.subTest(surface=surface):
                self.assertIn(surface, route_check["blocked_surfaces_must_remain_false"])
        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertEqual(post_runtime_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            post_runtime_gap["only_valid_post_runtime_route"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(post_runtime_gap["candidate_preflight_review_aliases_count"])
        self.assertTrue(post_runtime_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(
            post_runtime_gap["approved_runtime_evidence_scope"],
            "consume_only_contract_review_input",
        )
        self.assertEqual(post_runtime_gap["approved_runtime_resolved_input"], "runtime.lifecycle_evidence")
        self.assertEqual(
            post_runtime_gap["runtime_bundle_consumed_decision_keys"],
            checker.POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["missing_identity_contract_review_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS
            + checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertNotIn(
            "evidence.complete_non_protected_pack",
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
        )
        self.assertIn(
            "permissions_admin_contract_blocker",
            post_runtime_gap["deferred_downstream_surface_gaps"],
        )
        self.assertNotIn(
            "permissions_admin_contract_blocker",
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
        )
        self.assertIn(
            "permissions_admin",
            post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"],
        )
        self.assert_post_runtime_gap_summary_closed(post_runtime_gap)
        post_runtime_contract_gap = report["post_runtime_contract_gap_diagnostic"]
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["post_runtime_contract_gap_diagnostic"],
            post_runtime_contract_gap,
        )
        self.assertTrue(post_runtime_contract_gap["active"])
        self.assertTrue(post_runtime_contract_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(post_runtime_contract_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_contract_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            post_runtime_contract_gap["reviewed_decision_record_status"],
            "missing_or_not_accepted",
        )
        self.assertEqual(
            post_runtime_contract_gap["immediate_missing_artifacts"],
            ["reviewed_identity_public_contract_decision_record"],
        )
        self.assertEqual(
            post_runtime_contract_gap["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertIn("source_artifact_hash_policy", post_runtime_contract_gap["next_required_artifact"])
        self.assertIn(
            "public_contract_decisions",
            post_runtime_contract_gap["next_required_artifact"]["required_source_artifacts"],
        )
        self.assertEqual(
            post_runtime_contract_gap["missing_identity_contract_review_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_contract_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_contract_gap["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        self.assertIn(
            "approved_runtime_evidence_binding_missing_or_not_object",
            post_runtime_contract_gap["decision_record_blockers"],
        )
        self.assert_post_runtime_contract_gap_diagnostic_closed(post_runtime_contract_gap)
        self.assertEqual(
            set(post_runtime_gate["auditable_inputs"]),
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS,
        )
        self.assertEqual(
            post_runtime_gate["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["next_auditable_blocker"]["id"],
            post_runtime_gate["id"],
        )
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["next_auditable_blocker"][
                "next_required_artifact"
            ],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        public_contract_action = next(
            action
            for action in report["next_offline_actions"]
            if action["id"] == "identity_public_contract_gate_missing"
        )
        self.assertEqual(public_contract_action["status"], "blocked/review-required")
        self.assertTrue(public_contract_action["contract_review_input_present"])
        self.assertNotIn("runtime_lifecycle_evidence_accepted", public_contract_action)
        self.assertEqual(
            public_contract_action["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(
            public_contract_action["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        self.assertFalse(public_contract_action["promotion_ready"])
        self.assertFalse(public_contract_action["public_sdk_ready"])
        self.assertFalse(public_contract_action["runtime_ready"])
        self.assertFalse(public_contract_action["p0_progress_ready"])
        runtime_action = next(
            action
            for action in report["next_offline_actions"]
            if action["id"] == "runtime.lifecycle_evidence"
        )
        self.assertEqual(runtime_action["status"], "accepted_for_contract_review")
        self.assertEqual(runtime_action["resolved_input"], "runtime.lifecycle_evidence")
        self.assertEqual(runtime_action["next_input"], "identity contract review blocker")
        self.assertEqual(report["blocked_until"], ["reviewed_identity_public_contract"])
        self.assertIn(
            "runtime lifecycle evidence intake has consume-only scope; "
            "identity promotion remains blocked pending reviewed identity-contract evidence",
            report["public_identity_non_promotional_reasons"],
        )
        self.assertIn("runtime.lifecycle_evidence", report["contract_review_inputs_resolved"])
        self.assertEqual(report["remaining_contract_review_inputs"], [])
        self.assertEqual(
            report["remaining_post_runtime_inputs"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            self.assertIn(key, post_runtime_gate["remaining_unresolved_decision_keys"])
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
        self.assertIsInstance(runtime_report["approved_runtime_evidence_binding"], dict)
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
        self.assertFalse(runtime_report["public_contract_allowed"])
        self.assertFalse(runtime_report["public_sdk_ready"])
        self.assertFalse(runtime_report["runtime_ready"])
        self.assertFalse(runtime_report["public_api_ready"])
        self.assertFalse(runtime_report["public_abi_ready"])
        self.assertFalse(runtime_report["public_header_allowed"])
        self.assertFalse(runtime_report["lookup_ready"])
        self.assertFalse(runtime_report["permissions_ready"])
        self.assertFalse(runtime_report["commands_ready"])
        self.assertFalse(runtime_report["v1_completion_evidence"])
        self.assertTrue(runtime_report["source_provenance_policy"]["non_promotional_sources_rejected"])
        self.assertEqual(runtime_report["source_provenance_policy"]["findings"], [])
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["provided"])
        self.assertFalse(record["accepted_for_contract_review"])
        self.assertFalse(record["record_valid"])
        self.assertFalse(record["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record["contract_review_only"])
        self.assertFalse(record["identity_contract_gate_complete"])
        self.assertFalse(record["runtime_evidence_binding_valid"])
        self.assertFalse(record["bound_to_accepted_runtime_evidence"])
        self.assertEqual(record["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(record["source_artifact_freshness"]["current"])
        self.assertEqual(
            record["source_artifact_freshness"]["mismatches"][0]["label"],
            "public_contract_decisions",
        )
        self.assertIn("approved_runtime_evidence_binding_missing_or_not_object", record["blockers"])
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_missing_or_not_object",
            record["blockers"],
        )
        self.assertIn("source_artifact_hash_mismatch", record["blockers"])
        self.assertEqual(
            record["resolved_decision_keys"],
            [],
        )

    def test_rejects_stale_identity_decision_record_source_hash_after_runtime_evidence(self) -> None:
        runtime = approved_manifest()
        record = self.bound_decision_record(runtime)
        record["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)

            result = self.run_checker(
                approved_runtime_evidence=runtime,
                identity_public_contract_decision_record_path=record_path,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["record_valid"])
        self.assertFalse(record_report["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record_report["contract_review_only"])
        self.assertEqual(record_report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(record_report["source_artifact_freshness"]["current"])
        self.assertIn("source_artifact_hash_mismatch", record_report["blockers"])
        mismatch = record_report["source_artifact_freshness"]["mismatches"][0]
        self.assertEqual(mismatch["label"], "public_contract_decisions")
        self.assertEqual(mismatch["observed_sha256"], "0" * 64)
        self.assertFalse(mismatch["counts_toward_public_sdk"])
        self.assertFalse(mismatch["counts_toward_p0_dependency_chain_claim"])
        post_runtime_gap = report["post_runtime_contract_gap_diagnostic"]
        self.assertIn("source_artifact_hash_mismatch", post_runtime_gap["decision_record_blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_missing_identity_decision_record_source_hash_after_runtime_evidence(self) -> None:
        runtime = approved_manifest()
        record = self.bound_decision_record(runtime)
        record["source_artifacts"]["owner_token_sdk_consumer_contract"].pop("sha256")
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)

            result = self.run_checker(
                approved_runtime_evidence=runtime,
                identity_public_contract_decision_record_path=record_path,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["record_valid"])
        self.assertFalse(record_report["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record_report["contract_review_only"])
        self.assertEqual(record_report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(record_report["source_artifact_freshness"]["current"])
        self.assertIn("source_artifact_sha256_missing", record_report["blockers"])
        mismatch = record_report["source_artifact_freshness"]["mismatches"][0]
        self.assertEqual(mismatch["reason"], "source_artifact_sha256_missing")
        self.assertEqual(mismatch["label"], "owner_token_sdk_consumer_contract")
        self.assertIsNone(mismatch["observed_sha256"])
        self.assertFalse(mismatch["counts_toward_public_sdk"])
        self.assertFalse(mismatch["counts_toward_p0_dependency_chain_claim"])
        post_runtime_gap = report["post_runtime_contract_gap_diagnostic"]
        self.assertIn("source_artifact_sha256_missing", post_runtime_gap["decision_record_blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_accepts_bound_identity_decision_record_after_runtime_evidence_for_review_only(self) -> None:
        runtime = approved_manifest()
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, self.bound_decision_record(runtime))

            result = self.run_checker(
                approved_runtime_evidence=runtime,
                identity_public_contract_decision_record_path=record_path,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertTrue(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertTrue(report["identity_public_contract_decision_record"]["runtime_evidence_binding_valid"])
        self.assertTrue(report["identity_public_contract_decision_record"]["bound_to_accepted_runtime_evidence"])
        self.assertFalse(report["identity_public_contract_decision_record"]["reviewed_template_only"])
        self.assertTrue(report["identity_public_contract_decision_record"]["strict_accepted_decision_record"])
        self.assertTrue(
            report["identity_public_contract_decision_record"][
                "accepted_post_runtime_decision_record"
            ]
        )
        self.assertTrue(
            report["identity_public_contract_decision_record"][
                "accepted_as_next_identity_contract_input"
            ]
        )
        self.assertFalse(
            report["identity_public_contract_decision_record"][
                "public_header_readiness_from_decision_record"
            ]
        )
        self.assertEqual(
            report["identity_public_contract_decision_record"]["approved_runtime_evidence_binding"],
            report["approved_runtime_evidence"]["approved_runtime_evidence_binding"],
        )
        self.assertTrue(
            post_runtime_gate["accepted_decision_record_as_next_identity_contract_input"]
        )
        self.assertFalse(post_runtime_gate["accepted_decision_record_opens_public_header_gate"])
        self.assertFalse(post_runtime_gate["public_header_readiness_from_decision_record"])
        self.assertEqual(
            post_runtime_gate["next_required_artifact"],
            {
                **checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
                "status": "accepted_for_contract_review",
            },
        )
        self.assertEqual(
            report["remaining_post_runtime_inputs"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS,
        )
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            self.assertNotIn(key, post_runtime_gate["remaining_unresolved_decision_keys"])
        self.assert_runtime_contract_currentness_closed(
            post_runtime_gate["runtime_evidence_contract_review_currentness"]
        )
        self.assertTrue(
            post_runtime_gate["runtime_evidence_contract_review_currentness"]["observed"][
                "runtime_evidence_binding_valid"
            ]
        )
        self.assertTrue(
            post_runtime_gate["runtime_evidence_contract_review_currentness"]["observed"][
                "record_accepted_for_contract_review"
            ]
        )
        identity_record_currentness = report["identity_public_contract_decision_record"][
            "runtime_evidence_contract_review_currentness"
        ]
        self.assert_runtime_contract_currentness_closed(identity_record_currentness)
        self.assertTrue(identity_record_currentness["observed"]["runtime_evidence_binding_valid"])
        self.assertTrue(identity_record_currentness["observed"]["record_accepted_for_contract_review"])
        self.assert_runtime_contract_currentness_closed(
            report["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=True,
        )
        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertTrue(post_runtime_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(post_runtime_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(post_runtime_gap["candidate_preflight_review_aliases_count"])
        self.assertEqual(post_runtime_gap["missing_identity_contract_review_decision_keys"], [])
        self.assertEqual(
            post_runtime_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            self.assertNotIn(key, post_runtime_gap["smallest_remaining_public_identity_decision_keys"])
        self.assertNotIn(
            "permissions_admin_contract_blocker",
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
        )
        self.assert_post_runtime_gap_summary_closed(post_runtime_gap)
        post_runtime_contract_gap = report["post_runtime_contract_gap_diagnostic"]
        self.assertTrue(post_runtime_contract_gap["active"])
        self.assertTrue(post_runtime_contract_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(
            post_runtime_contract_gap["reviewed_decision_record_status"],
            "accepted_for_contract_review",
        )
        self.assertEqual(post_runtime_contract_gap["immediate_missing_artifacts"], [])
        self.assertEqual(post_runtime_contract_gap["missing_identity_contract_review_decision_keys"], [])
        self.assertEqual(
            post_runtime_contract_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_contract_gap["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS,
        )
        self.assert_post_runtime_contract_gap_diagnostic_closed(post_runtime_contract_gap)
        self.assertFalse(post_runtime_gate["identity_contract_gate_complete"])
        for key in (
            "public_header_allowed",
            "public_api_ready",
            "public_abi_ready",
            "public_sdk_ready",
            "runtime_ready",
            "counts_toward_p0_dependency_chain_claim",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_rejects_bound_identity_decision_record_that_does_not_match_accepted_runtime_evidence(self) -> None:
        record_runtime = approved_manifest()
        accepted_runtime = approved_manifest()
        record = self.bound_decision_record(record_runtime)
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)

            result = self.run_checker(
                approved_runtime_evidence=accepted_runtime,
                identity_public_contract_decision_record_path=record_path,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
            report["blockers"],
        )
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertTrue(record_report["runtime_evidence_binding_valid"])
        self.assertFalse(record_report["bound_to_accepted_runtime_evidence"])
        self.assertIn(
            "identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
            record_report["blockers"],
        )
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_bound_identity_decision_record_without_runtime_evidence_is_valid_but_unaccepted(self) -> None:
        runtime = approved_manifest()
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, self.bound_decision_record(runtime))

            result = self.run_checker(identity_public_contract_decision_record_path=record_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertTrue(record_report["record_valid"])
        self.assertTrue(record_report["runtime_evidence_binding_valid"])
        self.assertFalse(record_report["bound_to_accepted_runtime_evidence"])
        self.assertFalse(record_report["reviewed_template_only"])
        self.assertTrue(record_report["strict_accepted_decision_record"])
        self.assertFalse(record_report["accepted_post_runtime_decision_record"])
        self.assertFalse(record_report["accepted_as_next_identity_contract_input"])
        self.assertFalse(record_report["public_header_readiness_from_decision_record"])
        self.assertEqual(record_report["review_inputs_non_counting_until"], "runtime.lifecycle_evidence")
        self.assertEqual(record_report["resolved_decision_keys"], [])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_reviewed_template_only_decision_record_is_non_counting_gap_input(self) -> None:
        runtime = approved_manifest()
        record = self.bound_decision_record(runtime)
        record["accepted_for_contract_review"] = False
        with tempfile.TemporaryDirectory() as tempdir:
            record_path = Path(tempdir) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)

            result = self.run_checker(
                approved_runtime_evidence=runtime,
                identity_public_contract_decision_record_path=record_path,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        record_report = report["identity_public_contract_decision_record"]
        self.assertTrue(record_report["provided"])
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertTrue(record_report["record_valid"])
        self.assertTrue(record_report["hash_bound_to_current_source_artifacts"])
        self.assertTrue(record_report["reviewed_hash_current_contract_review_only"])
        self.assertTrue(record_report["reviewed_template_only"])
        self.assertFalse(record_report["strict_accepted_decision_record"])
        self.assertFalse(record_report["accepted_post_runtime_decision_record"])
        self.assertFalse(record_report["accepted_as_next_identity_contract_input"])
        self.assertFalse(record_report["public_header_readiness_from_decision_record"])
        self.assertEqual(record_report["resolved_decision_keys"], [])
        self.assertIn("accepted_for_contract_review_not_true", record_report["blockers"])
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]
        self.assertFalse(
            post_runtime_gate["accepted_decision_record_as_next_identity_contract_input"]
        )
        self.assertFalse(post_runtime_gate["accepted_decision_record_opens_public_header_gate"])
        self.assertFalse(post_runtime_gate["public_header_readiness_from_decision_record"])
        self.assertFalse(post_runtime_gate["identity_contract_gate_complete"])
        self.assertEqual(post_runtime_gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_passive_or_diagnostic_runtime_sources_at_public_intake(self) -> None:
        runtime = approved_manifest()
        passive_snapshot = (
            "/tmp/obelisk-passive-evidence-snapshots/"
            "passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json"
        )
        runtime["source_summary"]["evidence"]["kind"] = "passive-diagnostic-snapshot"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = passive_snapshot
        runtime["operational_window"]["copied_log"]["path"] = passive_snapshot

        result = self.run_checker(approved_runtime_evidence=runtime)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_non_promotional_sources_claimed", report["blockers"])
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn("runtime.lifecycle_evidence", report["contract_review_inputs_resolved"])
        policy = report["approved_runtime_evidence"]["source_provenance_policy"]
        self.assertTrue(policy["non_promotional_sources_rejected"])
        finding_paths = {item["path"] for item in policy["findings"]}
        self.assertIn("$.source_summary.evidence.kind", finding_paths)
        self.assertIn("$.source_summary.evidence.sources[0].path", finding_paths)
        self.assertIn("$.operational_window.copied_log.path", finding_paths)
        finding_tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("passive", finding_tokens)
        self.assertIn("diagnostic", finding_tokens)

    def test_rejects_public_header_proposal_as_approved_runtime_source(self) -> None:
        runtime = approved_manifest()
        proposal_path = (
            "docs/research/player-identity-planning-sources/"
            "player-identity-public-header-gate-proposal.json"
        )
        runtime["output_artifact_identity"]["evidence_pack_id"] = (
            "player-identity-public-header-gate-proposal"
        )
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = proposal_path
        runtime["operational_window"]["copied_log"]["path"] = proposal_path

        result = self.run_checker(approved_runtime_evidence=runtime)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_non_promotional_sources_claimed", report["blockers"])
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn("runtime.lifecycle_evidence", report["contract_review_inputs_resolved"])
        policy = report["approved_runtime_evidence"]["source_provenance_policy"]
        finding_paths = {item["path"] for item in policy["findings"]}
        self.assertIn("$.output_artifact_identity.evidence_pack_id", finding_paths)
        self.assertIn("$.source_summary.evidence.sources[0].path", finding_paths)
        self.assertIn("$.operational_window.copied_log.path", finding_paths)
        finding_tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("public-header-gate-proposal", finding_tokens)
        self.assertIn("public_header_proposal_artifact", finding_tokens)

    def test_rejects_copied_log_source_kind_alias_without_forbidden_tokens(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["source_summary"]["evidence"]["kind"] = "observer-log-copy"
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_non_promotional_sources_claimed", reasons)
        self.assertIn("approved_runtime_evidence_not_accepted", reasons)
        policy = runtime_report["source_provenance_policy"]
        self.assertEqual(policy["accepted_source_kind"], "runtime-observer-log")
        source_kind_finding = next(
            item
            for item in policy["findings"]
            if item["path"] == "$.source_summary.evidence.kind"
        )
        self.assertEqual(source_kind_finding["value"], "observer-log-copy")
        self.assertEqual(source_kind_finding["expected"], "runtime-observer-log")
        self.assertEqual(source_kind_finding["tokens"], ["source_kind_mismatch"])

    def test_rejects_simulated_or_fixture_runtime_sources_at_public_intake(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-runtime-simulation"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/synthetic-fixture-runtime.log"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/simulated-runtime-fixture.log"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = runtime_report["source_provenance_policy"]
        self.assertIn("simulation", policy["forbidden_source_tokens"])
        self.assertIn("synthetic", policy["forbidden_source_tokens"])
        self.assertIn("fixture", policy["forbidden_source_tokens"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("simulation", tokens)
        self.assertIn("synthetic", tokens)
        self.assertIn("fixture", tokens)

    def test_rejects_partial_copied_runtime_evidence_at_public_intake(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-copied-runtime-partial"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/copied-runtime-observer-log.partial"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/runtime-lifecycle-evidence-truncated.log"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = runtime_report["source_provenance_policy"]
        self.assertIn("partial", policy["forbidden_source_tokens"])
        self.assertIn("truncated", policy["forbidden_source_tokens"])
        self.assertIn("partial_copied_runtime_evidence", policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("partial", tokens)
        self.assertIn("truncated", tokens)
        self.assertIn("partial_copied_runtime_evidence", tokens)

    def test_approved_runtime_report_rejects_identity_decision_record_alias_shortcuts(self) -> None:
        overclaims = checker.approved_runtime_report_overclaims(
            {
                "identityContractDecisionRecordReviewed": True,
                "identityContractDecisionRecordHashCurrent": True,
                "identityContractDecisionRecordContractReviewOnly": True,
                "identityPublicContractDecisionRecordReviewed": True,
                "identityPublicContractRecordReviewed": True,
                "identityPublicContractGateReviewed": True,
                "publicContractGateReviewed": True,
                "reviewedIdentityPublicContract": True,
                "reviewedIdentityPublicContractDecisionRecord": True,
                "hashCurrentIdentityPublicContractDecisionRecord": True,
                "notes": ["identity contract decision record reviewed"],
            }
        )

        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.identityContractDecisionRecordReviewed", paths)
        self.assertIn("$.identityContractDecisionRecordHashCurrent", paths)
        self.assertIn("$.identityContractDecisionRecordContractReviewOnly", paths)
        self.assertIn("$.identityPublicContractDecisionRecordReviewed", paths)
        self.assertIn("$.identityPublicContractRecordReviewed", paths)
        self.assertIn("$.identityPublicContractGateReviewed", paths)
        self.assertIn("$.publicContractGateReviewed", paths)
        self.assertIn("$.reviewedIdentityPublicContract", paths)
        self.assertIn("$.reviewedIdentityPublicContractDecisionRecord", paths)
        self.assertIn("$.hashCurrentIdentityPublicContractDecisionRecord", paths)
        self.assertIn("$.notes[0]", paths)

    def test_approved_runtime_report_allows_safe_diagnostic_fname_mismatch_summary_keys(self) -> None:
        diagnostic_summary = {
            "count": 1,
            "evidence_claim": "none",
            "evidence_classification": "diagnostic_lifecycle_property_fname_mismatch_non_evidence",
            "approved_runtime_evidence": False,
            "runtime_evidence_ready": False,
            "readiness_gate": "none",
            "targets": [
                {
                    "target": "ShooterGameMode.HandleNewPlayer",
                    "count": 1,
                    "pattern_count": 1,
                    "patterns": [
                        {
                            "summary": "expected_28411_observed_28416_21314",
                            "expected_name_index": 28411,
                            "observed_count": 2,
                            "observed_name_indices": [28416, 21314],
                            "observed_name_indices_complete": True,
                            "count": 1,
                            "read_status_counts": {"implausible": 1},
                            "fname_indices": [2170],
                            "first_sequence": 1,
                            "latest_sequence": 1,
                            "latest_occurrence": {
                                "source_index": 0,
                                "line_number": 4,
                                "timestamp_prefix": None,
                            },
                        },
                    ],
                },
            ],
        }

        payload = {
            "source_summary": {
                "modules": {
                    "player_principal_lifecycle": {
                        "diagnostic_lifecycle_property_fname_mismatch_target_summary": diagnostic_summary,
                    },
                },
            },
        }

        self.assertEqual(checker.approved_runtime_report_overclaims(payload), [])
        self.assertEqual(checker.approved_runtime_report_leakages(payload), [])

    def test_approved_runtime_diagnostic_fname_mismatch_summary_does_not_open_public_gate(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "v1_completion_ready": False,
                "v1_completion_evidence": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        module = runtime["source_summary"]["modules"]["player_principal_lifecycle"]
        module["diagnostic_lifecycle_property_fname_mismatch_target_summary"]["targets"] = [
            {
                "target": "ShooterGameMode.HandleNewPlayer",
                "count": 1,
                "pattern_count": 1,
                "patterns": [
                    {
                        "summary": "expected_28411_observed_28416_21314",
                        "expected_name_index": 28411,
                        "observed_count": 2,
                        "observed_name_indices": [28416, 21314],
                        "count": 1,
                        "read_status_counts": {"implausible": 1},
                        "fname_indices": [2170],
                        "latest_sequence": 1,
                    },
                ],
            },
        ]

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertTrue(runtime_report["accepted_for_contract_review"])
        self.assertEqual(runtime_report["resolved_input"], "runtime.lifecycle_evidence")
        self.assertEqual(runtime_report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(runtime_report["public_contract_allowed"])
        self.assertFalse(runtime_report["public_header_allowed"])
        self.assertFalse(runtime_report["public_api_ready"])
        self.assertFalse(runtime_report["public_abi_ready"])
        self.assertFalse(runtime_report["public_sdk_ready"])
        self.assertFalse(runtime_report["runtime_ready"])
        self.assertFalse(runtime_report["v1_completion_evidence"])
        self.assertEqual([blocker["reason"] for blocker in blockers], [])

    def test_approved_runtime_diagnostic_fname_mismatch_summary_rejects_player_or_raw_ue_leakage(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        cases = (
            ("player_name", "SyntheticPlayer"),
            ("raw_ue_pointer", "0x12345678"),
            ("summary", "raw_ue_pointer=0x12345678"),
        )
        for key, value in cases:
            with self.subTest(key=key):
                runtime = approved_manifest()
                module = runtime["source_summary"]["modules"]["player_principal_lifecycle"]
                module["diagnostic_lifecycle_property_fname_mismatch_target_summary"]["targets"] = [
                    {
                        "target": "ShooterGameMode.HandleNewPlayer",
                        key: value,
                    },
                ]
                with tempfile.TemporaryDirectory() as tempdir:
                    runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
                    runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
                    blockers: list[dict] = []
                    with (
                        mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                        mock.patch.object(
                            checker.approved_runtime_evidence,
                            "validate_manifest",
                            side_effect=accepted_validation,
                        ),
                        mock.patch.object(
                            checker.approved_runtime_evidence,
                            "build_report",
                            side_effect=accepted_report,
                        ),
                    ):
                        runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

                reasons = [blocker["reason"] for blocker in blockers]
                self.assertFalse(runtime_report["accepted_for_contract_review"])
                self.assertIn("approved_runtime_evidence_report_player_or_raw_ue_leakage", reasons)
                self.assertIn("approved_runtime_evidence_not_accepted", reasons)
                leakage_detail = next(
                    blocker
                    for blocker in blockers
                    if blocker["reason"] == "approved_runtime_evidence_report_player_or_raw_ue_leakage"
                )
                self.assertIn(
                    f"$.source_summary.modules.player_principal_lifecycle."
                    f"diagnostic_lifecycle_property_fname_mismatch_target_summary.targets[0].{key}",
                    {item["path"] for item in leakage_detail["leakages"]},
                )

    def test_rejects_planning_public_api_ready_source_aliases(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = (
            "public-api-ready-planning-counts-toward-sdk-production-sdk-ready-artifact"
        )
        runtime["source_summary"]["evidence"]["kind"] = (
            "public-api-ready-planning-runtime-work-authorized"
        )
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "public-sdk-ready-identity-lookup-allowed-permissions-admin-unlocked.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "runtime-ready-command-response-unlocked-counts-toward-v1.log"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = runtime_report["source_provenance_policy"]
        self.assertIn("planning_artifact", policy["forbidden_source_aliases"])
        self.assertIn("runtime_readiness_alias", policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("planning_artifact", tokens)
        self.assertIn("public_api_readiness_alias", tokens)
        self.assertIn("public_sdk_readiness_alias", tokens)
        self.assertIn("runtime_readiness_alias", tokens)
        self.assertIn("identity_lookup_readiness_alias", tokens)
        self.assertIn("permissions_admin_unlock_alias", tokens)
        self.assertIn("command_response_unlock_alias", tokens)
        self.assertIn("runtime_authorization_alias", tokens)
        self.assertIn("counts_toward_alias", tokens)
        self.assertIn("production_sdk_readiness_alias", tokens)
        self.assertIn("source_kind_mismatch", tokens)

    def test_approved_runtime_evidence_rejects_extended_monitor_notice_closure_executor_manifest_sources(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-manifest-reference"
        runtime["output_artifact_identity"]["evidence_pack_id"] = (
            "identity-public-contract-accepted-alias"
        )
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "extended-passive-monitor-status-json-package-shape-historical-handoff.txt"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "beta-notice-closure-report-executor-report-public-contract-ready-alias-"
            "copied-log-only-historical-handoff.log"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = runtime_report["source_provenance_policy"]
        for alias in (
            "approved_manifest_reference",
            "beta_notice_material",
            "closure_or_executor_report",
            "copied_log_only_material",
            "generic_public_contract_shortcut_alias",
            "historical_handoff_material",
            "package_shape_material",
            "passive_extended_monitor_material",
            "status_json_material",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        for token in (
            "accepted-alias",
            "approved-manifest",
            "approved_manifest_reference",
            "beta-notice",
            "closure",
            "closure_or_executor_report",
            "copied-log-only",
            "copied_log_only_material",
            "executor",
            "generic_public_contract_shortcut_alias",
            "historical-handoff",
            "historical_handoff_material",
            "package-shape",
            "package_shape_material",
            "passive",
            "passive_extended_monitor_material",
            "ready-alias",
            "status-json",
            "status_json_material",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

    def test_approved_runtime_evidence_rejects_post_runtime_artifact_classes_as_sources(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "generated-runtime-bundle-report"
        runtime["output_artifact_identity"]["evidence_pack_id"] = (
            "post-runtime-identity-contract-checklist-policy-row"
        )
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "scoped-release-statement-8of8-package-shape-row.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "terminal-certificate-evidence-bundle-report-ObeliskConfig.cmake.log"
        )
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = runtime_report["source_provenance_policy"]
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        for token in (
            "8of8",
            "checklist-policy",
            "checklist_policy_row_material",
            "evidence-bundle-report",
            "generated-runtime-bundle-report",
            "generated_runtime_bundle_report_material",
            "package-shape",
            "package_shape_material",
            "scoped-release-statement",
            "scoped_8of8_release_statement_row",
            "terminal-certificate",
            "terminal_certificate_material",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

    def test_approved_runtime_report_rejects_non_promotional_artifact_status_aliases(self) -> None:
        overclaims = checker.approved_runtime_report_overclaims(
            {
                "checklist_policy_row": {"status": "resolved"},
                "scoped_release_statement_8_8_row": {"status": "accepted"},
                "terminal_certificate": {"accepted": True},
                "evidence_bundle_report": {"state": "accepted"},
                "installed_sdk_package_shape": {"status": "accepted"},
                "notes": [
                    "Checklist policy row resolved the identity contract gate.",
                    "Scoped release statement 8/8 row is accepted.",
                    "Terminal certificate resolved identity public contract gate.",
                    "Evidence bundle report accepted as the public route.",
                    "Installed SDK package-shape artifact accepted.",
                ],
            }
        )
        paths = {claim["path"] for claim in overclaims}
        terms_by_path = {(claim["path"], claim["term"]) for claim in overclaims}

        for path in (
            "$.checklist_policy_row",
            "$.scoped_release_statement_8_8_row",
            "$.terminal_certificate",
            "$.evidence_bundle_report",
            "$.installed_sdk_package_shape",
        ):
            with self.subTest(path=path):
                self.assertIn((path, "non_promotional_artifact_status_alias"), terms_by_path)
        for path in (
            "$.notes[0]",
            "$.notes[1]",
            "$.notes[2]",
            "$.notes[3]",
            "$.notes[4]",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_approved_runtime_evidence_alone_does_not_resolve_promotion_blockers(self) -> None:
        result = self.run_checker(approved_runtime_evidence=approved_manifest())
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        unresolved_decision_keys = report["unresolved_public_contract_decision_keys"]
        self.assertIn("privacy.public_identifier_form", unresolved_decision_keys)
        self.assertIn("lifetime.principal_scope", unresolved_decision_keys)
        self.assertIn("abi.payload_shape", unresolved_decision_keys)
        for gate_input in report["contract_gate_inputs"]:
            with self.subTest(input_id=gate_input["id"]):
                self.assertFalse(gate_input["promotion_blocker_resolved"])
                self.assertFalse(gate_input["promotion_ready"])
                self.assertFalse(gate_input["public_sdk_ready"])
                self.assertFalse(gate_input["runtime_ready"])
                self.assertFalse(gate_input["public_header_allowed"])
                self.assertFalse(gate_input["v1_completion_evidence"])

    def test_rejects_invalid_approved_runtime_evidence_without_routing(self) -> None:
        runtime = approved_manifest()
        runtime["public_sdk_ready"] = True

        result = self.run_checker(approved_runtime_evidence=runtime)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn(
            "approved_runtime_evidence_payload_readiness_flag_not_false",
            report["blockers"],
        )
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "approved_runtime_evidence_payload_readiness_flag_not_false"
        )
        self.assertEqual(detail["label"], "--approved-runtime-evidence.public_sdk_ready")
        self.assertTrue(report["runtime_evidence_missing"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(report["identity_public_contract_gate_missing"]["active"])
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
                    "approved_manifest.reference",
                    "beta_notice.runtime",
                    "closure_report.evidence",
                    "diagnostic.gap_report",
                    "executor_report.evidence",
                    "identity_public_contract.accepted_alias",
                    "identity_public_contract.complete_alias",
                    "identity_public_contract.ready_alias",
                    "operator_approval_receipt",
                    "passive.extended_monitor_snapshot",
                    "passive.chat_route",
                    "player_identity.promotion_certificate.stale",
                    "preflight_readiness",
                    "scoped_release_statement.permissions_admin",
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
        non_promotional_detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_non_promotional_inputs_claimed"
        )
        self.assertEqual(
            non_promotional_detail["forbidden"],
            [
                "approved_manifest.reference",
                "beta_notice.runtime",
                "closure_report.evidence",
                "diagnostic.gap_report",
                "executor_report.evidence",
                "identity_public_contract.accepted_alias",
                "identity_public_contract.complete_alias",
                "identity_public_contract.ready_alias",
                "live_ops_sidecar",
                "operator_approval_receipt",
                "passive.chat_route",
                "passive.extended_monitor_snapshot",
                "player_identity.promotion_certificate.stale",
                "preflight_readiness",
                "scoped_release_statement.permissions_admin",
            ],
        )
        self.assertFalse(runtime_report["accepted_for_contract_review"])

    def test_approved_runtime_evidence_rejects_report_not_ready(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def not_ready_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": False,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=not_ready_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertIn(
            "approved_runtime_evidence_report_ready_not_true",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])

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

    def test_approved_runtime_evidence_rejects_status_report_shape_and_raw_acceptance_boolean(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def status_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": "obelisk.sdk-status-report.v1",
                "mode": "status",
                "ready": True,
                "ready_scope": "runtime_status_report",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "resolved_inputs": [checker.APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT],
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "accepted_for_contract_review": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "v1_completion_ready": False,
                "v1_completion_evidence": False,
                "observed_runtime_cases": ["observer_enable", "session_start_anchor"],
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
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=status_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("approved_runtime_evidence_report_schema_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_mode_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_ready_scope_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_observed_runtime_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_boundary_assertions_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_report_false_only_key_not_false", reasons)
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
                "contractReviewed": True,
                "identityContractReady": True,
                "publicApiReady": True,
                "runtimeReadyAlias": "ready",
                "helperDerivedReadiness": "satisfied",
                "publicPrincipalReady": True,
                "principalHandleAbiReady": True,
                "identityHeaderAllowed": True,
                "identityHeaderReady": True,
                "principalLookupReady": True,
                "realIdentityReady": True,
                "redactionEvidencePromotesIdentity": True,
                "claims": {
                    "public_contract_ready": True,
                    "publicSdkReady": True,
                    "publicApiReadiness": True,
                    "public-header-allowed": "ready",
                    "publicHeaderSymbolsNow": ["ObeliskPlayerPrincipalEvent"],
                    "publicApiSymbolsNow": ["RegisterPlayerIdentityApi"],
                    "publicSymbolList": ["RegisterPlayerIdentityApi"],
                    "public": {
                        "sdk": {"ready": True},
                        "header": {"symbols_now": ["ObeliskPlayerPrincipalEvent"]},
                        "capability": {"bits_now": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]},
                    },
                    "downstream": "identity unlocks permissions now",
                    "nested": {"v1CompletionReady": True},
                    "api_summary": "public API readiness is satisfied",
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
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.claims.publicSdkReady", paths)
        self.assertIn("$.claims.publicApiReadiness", paths)
        self.assertIn("$.claims.public-header-allowed", paths)
        self.assertIn("$.claims.publicHeaderSymbolsNow", paths)
        self.assertIn("$.claims.publicApiSymbolsNow", paths)
        self.assertIn("$.claims.publicSymbolList", paths)
        self.assertIn("$.claims.public.sdk.ready", paths)
        self.assertIn("$.claims.public.header.symbols_now", paths)
        self.assertIn("$.claims.public.capability.bits_now", paths)
        self.assertIn("$.claims.api_summary", paths)
        self.assertIn("$.claims.nested.v1CompletionReady", paths)
        self.assertIn("$.contractReviewed", paths)
        self.assertIn("$.identityContractReady", paths)
        self.assertIn("$.publicApiReady", paths)
        self.assertIn("$.runtimeReadyAlias", paths)
        self.assertIn("$.helperDerivedReadiness", paths)
        self.assertIn("$.publicPrincipalReady", paths)
        self.assertIn("$.principalHandleAbiReady", paths)
        self.assertIn("$.identityHeaderAllowed", paths)
        self.assertIn("$.identityHeaderReady", paths)
        self.assertIn("$.principalLookupReady", paths)
        self.assertIn("$.realIdentityReady", paths)
        self.assertIn("$.redactionEvidencePromotesIdentity", paths)
        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIsNone(runtime_report["resolved_input"])
        self.assertEqual(runtime_report["resolved_inputs"], [])

    def test_approved_runtime_payload_rejects_stable_claim_and_downstream_unlocks(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["stable_claim_allowed"] = True
        runtime["nestedUnlocks"] = {
            "permissionsAdminUnlocked": True,
            "commandResponseUnlocked": True,
            "commandsRepliesUnlocked": True,
            "summary": [
                "stable claim is allowed",
                "permissions/admin is unlocked",
                "command response is unlocked",
                "commands/replies are ready",
            ],
        }
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_report_public_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_not_accepted", reasons)
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.stable_claim_allowed", paths)
        self.assertIn("$.nestedUnlocks.permissionsAdminUnlocked", paths)
        self.assertIn("$.nestedUnlocks.commandResponseUnlocked", paths)
        self.assertIn("$.nestedUnlocks.commandsRepliesUnlocked", paths)
        self.assertIn("$.nestedUnlocks.summary[0]", paths)
        self.assertIn("$.nestedUnlocks.summary[1]", paths)
        self.assertIn("$.nestedUnlocks.summary[2]", paths)
        self.assertIn("$.nestedUnlocks.summary[3]", paths)

    def test_approved_runtime_payload_rejects_runtime_authorization_counting_and_production_aliases(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return {
                "schema": checker.approved_runtime_evidence.REPORT_SCHEMA,
                "mode": "consume",
                "ready": True,
                "ready_scope": "runtime_evidence_only",
                "remaining_blockers": [],
                "next_blocker": "identity_public_contract_gate_missing",
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                "resolved_inputs": ["runtime.lifecycle_evidence"],
            }

        runtime = approved_manifest()
        runtime["runtimeWorkAuthorized"] = True
        runtime["runtimeWorkAuthorization"] = "authorized"
        runtime["serverOperationsAuthorized"] = True
        runtime["workspaceWritesAuthorized"] = True
        runtime["liveOpsAuthorized"] = True
        runtime["countsTowardSdk"] = True
        runtime["countsTowardV1"] = True
        runtime["countsTowardPublic"] = True
        runtime["countsTowardRuntime"] = True
        runtime["productionSdkReady"] = True
        runtime["stableSdkClaimAllowed"] = True
        runtime["nestedCountingClaims"] = [
            {"claim": "countsTowardSdk", "value": True},
            {"claim": "runtimeWorkAuthorization", "value": "authorized"},
            {"summary": "runtime work is authorized"},
            {"summary": "counts toward public SDK"},
            {"summary": "production SDK is ready"},
        ]
        with tempfile.TemporaryDirectory() as tempdir:
            runtime_path = Path(tempdir) / "approved-runtime-evidence.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, {"OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES": "1"}),
                mock.patch.object(checker.approved_runtime_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_runtime_evidence, "build_report", side_effect=accepted_report),
            ):
                runtime_report = checker.validate_approved_runtime_evidence(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_report_public_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_not_accepted", reasons)
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        for path in (
            "$.runtimeWorkAuthorized",
            "$.runtimeWorkAuthorization",
            "$.serverOperationsAuthorized",
            "$.workspaceWritesAuthorized",
            "$.liveOpsAuthorized",
            "$.countsTowardSdk",
            "$.countsTowardV1",
            "$.countsTowardPublic",
            "$.countsTowardRuntime",
            "$.productionSdkReady",
            "$.stableSdkClaimAllowed",
            "$.nestedCountingClaims[0]",
            "$.nestedCountingClaims[1]",
            "$.nestedCountingClaims[2].summary",
            "$.nestedCountingClaims[3].summary",
            "$.nestedCountingClaims[4].summary",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

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
        decisions["approved_runtime_evidence_intake"]["public_api_ready"] = True
        decisions["approved_runtime_evidence_intake"]["lookup_ready"] = True
        decisions["approved_runtime_evidence_intake"]["v1_completion_evidence"] = True
        decisions["approved_runtime_evidence_intake"]["p0_progress_ready"] = True
        decisions["approved_runtime_evidence_intake"]["sdk_p0_progress"] = "1/4"
        decisions["identifier_redaction_evidence_intake"]["public_sdk_ready"] = True
        decisions["public_abi_preflight_candidate_intake"]["public_abi_ready"] = True
        decisions["owner_token_sdk_consumer_contract_intake"]["lifecycle_owner_cleanup_ready"] = True
        decisions["contractReviewed"] = True
        decisions["identityContractReady"] = True
        decisions["principalHandleAbiReady"] = True
        decisions["identityHeaderAllowed"] = True
        decisions["alias_guardrails"]["publicPrincipalReady"] = True
        decisions["alias_guardrails"]["identityPublicContractReady"] = True
        decisions["alias_guardrails"]["publicIdentityReady"] = True
        decisions["alias_guardrails"]["publicApiReady"] = True
        decisions["alias_guardrails"]["publicAbiReady"] = True
        decisions["alias_guardrails"]["publicHeaderAllowed"] = True
        decisions["alias_guardrails"]["publicContractReady"] = True
        decisions["alias_guardrails"]["publicSdkReady"] = True
        decisions["alias_guardrails"]["runtimeReady"] = True
        decisions["alias_guardrails"]["lookupReady"] = True
        decisions["alias_guardrails"]["lookupAllowed"] = True
        decisions["alias_guardrails"]["permissionsReady"] = True
        decisions["alias_guardrails"]["permissionsAdminUnlocked"] = True
        decisions["alias_guardrails"]["commandsReady"] = True
        decisions["alias_guardrails"]["commandResponseUnlocked"] = True
        decisions["alias_guardrails"]["commandsRepliesUnlocked"] = True
        decisions["alias_guardrails"]["stableSdkReady"] = True
        decisions["alias_guardrails"]["sdkConsumerReady"] = True
        decisions["alias_guardrails"]["v1CompletionReady"] = True
        decisions["alias_guardrails"]["v1CompletionEvidence"] = True
        decisions["alias_guardrails"]["p0ProgressReady"] = True
        decisions["alias_guardrails"]["sdkP0Progress"] = "1/4"
        decisions["alias_guardrails"]["identityHeaderReady"] = True
        decisions["alias_guardrails"]["principalLookupReady"] = True
        decisions["alias_guardrails"]["identityLookupReady"] = True
        decisions["alias_guardrails"]["publicLookupReady"] = True
        decisions["alias_guardrails"]["runtimePrincipalReady"] = True
        decisions["alias_guardrails"]["realIdentityReady"] = True
        decisions["alias_guardrails"]["redactionEvidencePromotesIdentity"] = True
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
        self.assertIn("$.approved_runtime_evidence_intake.public_api_ready", labels)
        self.assertIn("$.approved_runtime_evidence_intake.lookup_ready", labels)
        self.assertIn("$.approved_runtime_evidence_intake.v1_completion_evidence", labels)
        self.assertIn("$.approved_runtime_evidence_intake.p0_progress_ready", labels)
        self.assertIn("$.approved_runtime_evidence_intake.sdk_p0_progress", labels)
        self.assertIn("$.identifier_redaction_evidence_intake.public_sdk_ready", labels)
        self.assertIn("$.public_abi_preflight_candidate_intake.public_abi_ready", labels)
        self.assertIn("$.owner_token_sdk_consumer_contract_intake.lifecycle_owner_cleanup_ready", labels)
        self.assertIn("$.proposed_public_pod_abi_candidate.runtime_ready", labels)
        self.assertIn("$.evidence.candidate_policy_artifacts[0].public_sdk_ready", labels)
        self.assertIn("$.runtime_ready", labels)
        self.assertIn("$.contractReviewed", labels)
        self.assertIn("$.identityContractReady", labels)
        self.assertIn("$.principalHandleAbiReady", labels)
        self.assertIn("$.identityHeaderAllowed", labels)
        alias_labels = {
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "decisions_alias_guardrail_not_false"
        }
        self.assertIn("$.alias_guardrails.publicPrincipalReady", alias_labels)
        self.assertIn("$.alias_guardrails.identityPublicContractReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicIdentityReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicApiReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicAbiReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicHeaderAllowed", alias_labels)
        self.assertIn("$.alias_guardrails.publicContractReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicSdkReady", alias_labels)
        self.assertIn("$.alias_guardrails.runtimeReady", alias_labels)
        self.assertIn("$.alias_guardrails.lookupReady", alias_labels)
        self.assertIn("$.alias_guardrails.lookupAllowed", alias_labels)
        self.assertIn("$.alias_guardrails.permissionsReady", alias_labels)
        self.assertIn("$.alias_guardrails.permissionsAdminUnlocked", alias_labels)
        self.assertIn("$.alias_guardrails.commandsReady", alias_labels)
        self.assertIn("$.alias_guardrails.commandResponseUnlocked", alias_labels)
        self.assertIn("$.alias_guardrails.commandsRepliesUnlocked", alias_labels)
        self.assertIn("$.alias_guardrails.stableSdkReady", alias_labels)
        self.assertIn("$.alias_guardrails.sdkConsumerReady", alias_labels)
        self.assertIn("$.alias_guardrails.v1CompletionReady", alias_labels)
        self.assertIn("$.alias_guardrails.v1CompletionEvidence", alias_labels)
        self.assertIn("$.alias_guardrails.p0ProgressReady", alias_labels)
        self.assertIn("$.alias_guardrails.sdkP0Progress", alias_labels)
        self.assertIn("$.alias_guardrails.identityHeaderReady", alias_labels)
        self.assertIn("$.alias_guardrails.principalLookupReady", alias_labels)
        self.assertIn("$.alias_guardrails.identityLookupReady", alias_labels)
        self.assertIn("$.alias_guardrails.publicLookupReady", alias_labels)
        self.assertIn("$.alias_guardrails.runtimePrincipalReady", alias_labels)
        self.assertIn("$.alias_guardrails.realIdentityReady", alias_labels)
        self.assertIn("$.alias_guardrails.redactionEvidencePromotesIdentity", alias_labels)
        self.assertIn("decisions_contract_gate_input_flag_not_false", report["blockers"])

    def test_rejects_missing_or_weakened_identifier_redaction_intake(self) -> None:
        decisions = self.load_decisions()
        decisions["identifier_redaction_evidence_intake"]["required_checker"] = "scripts/other.py"

        result = self.run_checker(decisions=decisions, approved_runtime_evidence=approved_manifest())
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
        decisions["approved_runtime_evidence_intake"]["source_provenance_policy"]["accepted_source_kind"] = (
            "passive-snapshot"
        )
        decisions["approved_runtime_evidence_intake"]["source_provenance_policy"][
            "required_output_artifact_hash"
        ] = "diagnostic.report.sha256"
        decisions["approved_runtime_evidence_intake"]["public_api_ready"] = True
        decisions["approved_runtime_evidence_intake"]["lookup_ready"] = True
        decisions["approved_runtime_evidence_intake"]["v1_completion_evidence"] = True

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_approved_runtime_evidence_intake_id_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_status_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_resolved_input_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_checker_mismatch", report["blockers"])
        self.assertIn("decisions_approved_runtime_evidence_intake_non_claim_mismatch", report["blockers"])
        self.assertIn(
            "decisions_approved_runtime_evidence_intake_source_provenance_policy_mismatch",
            report["blockers"],
        )
        readiness_labels = {
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "readiness_flag_not_false"
        }
        self.assertIn("$.approved_runtime_evidence_intake.public_api_ready", readiness_labels)
        self.assertIn("$.approved_runtime_evidence_intake.lookup_ready", readiness_labels)
        self.assertIn("$.approved_runtime_evidence_intake.v1_completion_evidence", readiness_labels)

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

    def test_rejects_public_text_or_source_artifact_overclaims_in_decisions(self) -> None:
        decisions = self.load_decisions()
        decisions["source_artifacts"] = {"public_sdk_alias": "docs/research/public-sdk-ready.json"}
        decisions["review_notes"] = [
            "public header symbols are available",
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY is available",
            "callback ABI exposed for RegisterPlayerIdentity",
            "installed SDK package shape is ready",
            "support tier is ready",
            "Plugin Hub publication is published",
        ]

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.source_artifacts.public_sdk_alias", paths)
        self.assertIn("$.review_notes[0]", paths)
        self.assertIn("$.review_notes[1]", paths)
        self.assertIn("$.review_notes[2]", paths)
        self.assertIn("$.review_notes[3]", paths)
        self.assertIn("$.review_notes[4]", paths)
        self.assertIn("$.review_notes[5]", paths)
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("package_shape_readiness", terms)
        self.assertIn("support_tier_ready", terms)
        self.assertIn("plugin_hub_ready", terms)

    def test_sanitizes_public_abi_preflight_helper_overclaims(self) -> None:
        overclaim = {
            "status": "blocked",
            "candidate_only": True,
            "accepted_for_candidate_review": True,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "runtime_ready_alias": "ready",
            "helper_derived_readiness": "satisfied",
            "public_header_allowed": True,
            "public_contract_allowed": True,
            "public_abi_ready": True,
            "public_api_ready": True,
            "v1_completion_ready": True,
            "v1_completion_evidence": True,
            "public_sdk_v1_completion_claim": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_api_symbols_now": ["RegisterPlayerIdentityApi"],
            "public_symbol_list": ["RegisterPlayerIdentityApi"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerIdentityCallback"],
            "claims": {
                "publicHeaderSymbols": ["ObeliskPlayerPrincipalEvent"],
                "publicSymbolList": ["RegisterPlayerIdentityApi"],
                "capabilityBits": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
                "callbackAbi": ["ObeliskPlayerIdentityCallback"],
            },
            "sdk_consumer_contract": {
                "accepted_for_contract_review": True,
                "public_sdk_ready": True,
                "public_api_ready": True,
                "runtime_ready_alias": "ready",
                "helper_derived_readiness": "satisfied",
                "public_header_symbols_now": ["RegisterPlayerIdentityCallback"],
                "public_symbol_list": ["RegisterPlayerIdentityApi"],
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
        self.assertIn("nested_public_symbol_list_not_empty", reasons)
        self.assertIn("nested_capability_bits_not_empty", reasons)
        self.assertIn("nested_callback_abi_not_empty", reasons)
        self.assertFalse(report["accepted_for_candidate_review"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_contract_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_api_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["claims"]["publicHeaderSymbols"], [])
        self.assertEqual(report["claims"]["capabilityBits"], [])
        self.assertEqual(report["claims"]["callbackAbi"], [])
        self.assertFalse(report["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertFalse(report["sdk_consumer_contract"]["public_api_ready"])
        self.assertEqual(report["sdk_consumer_contract"]["public_header_symbols_now"], [])
        self.assertEqual(report["sdk_consumer_contract"]["public_symbol_list"], [])

    def test_sanitizes_owner_token_sdk_consumer_helper_overclaims(self) -> None:
        import check_player_identity_owner_token_sdk_consumer_contract as owner_token_checker

        overclaim = {
            "ready": True,
            "accepted_for_candidate_review": True,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "runtime_ready_alias": "ready",
            "helper_derived_readiness": "satisfied",
            "public_header_allowed": True,
            "public_abi_ready": True,
            "v1_completion_evidence": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_symbol_list": ["RegisterPlayerIdentityApi"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerIdentityCallback"],
            "sdk_consumer": {
                "public_sdk_ready": True,
                "runtime_ready_alias": "ready",
                "helper_derived_readiness": "satisfied",
                "public_header_symbols_now": ["RegisterPlayerIdentityCallback"],
                "public_symbol_list": ["RegisterPlayerIdentityApi"],
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
        self.assertIn("nested_public_symbol_list_not_empty", reasons)
        self.assertTrue(report["provided"])
        self.assertEqual(report["source"], "owner_token_sdk_consumer_contract")
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["runtime_ready_alias"])
        self.assertFalse(report["helper_derived_readiness"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_symbol_list"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertFalse(report["sdk_consumer"]["public_sdk_ready"])
        self.assertFalse(report["sdk_consumer"]["runtime_ready_alias"])
        self.assertFalse(report["sdk_consumer"]["helper_derived_readiness"])
        self.assertEqual(report["sdk_consumer"]["public_header_symbols_now"], [])
        self.assertEqual(report["sdk_consumer"]["public_symbol_list"], [])

    def test_rejects_identifier_redaction_helper_public_contract_overclaims(self) -> None:
        def accepted_validation(_payload):
            return []

        overclaim_report = {
            "accepted_for_contract_review": True,
            "resolved_inputs": ["privacy.identifier_redaction"],
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "publicIdentityReady": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "claims": {
                "summary": "public player identity ready",
                "lookup": "player lookup is allowed",
                "promotion": "principal is promoted",
                "completion": "complete SDK progress ready",
            },
            "blockers": [],
            "non_claims": [],
        }

        blockers: list[dict] = []
        with (
            mock.patch.object(checker.redaction_checker, "load_evidence", return_value={}),
            mock.patch.object(checker.redaction_checker, "validate_evidence", side_effect=accepted_validation),
            mock.patch.object(checker.redaction_checker, "build_report", return_value=overclaim_report),
        ):
            report = checker.validate_identifier_redaction_evidence(
                IDENTIFIER_REDACTION_EVIDENCE,
                blockers,
            )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("identifier_redaction_evidence_public_contract_overclaim", reasons)
        self.assertIn("identifier_redaction_evidence_not_accepted", reasons)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("public_contract_overclaim", report["blockers"])
        detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "identifier_redaction_evidence_public_contract_overclaim"
        )
        paths = {claim["path"] for claim in detail["overclaims"]}
        self.assertIn("$.publicIdentityReady", paths)
        self.assertIn("$.public_header_symbols_now", paths)
        self.assertIn("$.claims.summary", paths)
        self.assertIn("$.claims.lookup", paths)
        self.assertIn("$.claims.promotion", paths)
        self.assertIn("$.claims.completion", paths)

    def test_rejects_principal_policy_helper_public_contract_overclaims(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        overclaim_report = {
            "ready": True,
            "mode": "consume",
            "candidate_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "principal_invalidation_ready": False,
            "publicAbiReady": True,
            "public_callback_abi_now": ["ObeliskPlayerIdentityCallback"],
            "claims": {
                "summary": "public callback ABI is available",
                "identity": "identity is promoted",
                "sdk": "public SDK ready",
            },
            "principal_fields": [],
            "invalidation_cases": [],
            "negative_consumer_rules": [],
            "blockers": [],
        }

        blockers: list[dict] = []
        with (
            mock.patch.object(checker.principal_invalidation_policy, "load_json", return_value={}),
            mock.patch.object(
                checker.principal_invalidation_policy,
                "validate_manifest",
                side_effect=accepted_validation,
            ),
            mock.patch.object(
                checker.principal_invalidation_policy,
                "build_report",
                return_value=overclaim_report,
            ),
        ):
            report = checker.validate_principal_invalidation_policy(
                PRINCIPAL_INVALIDATION_POLICY,
                blockers,
            )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("principal_invalidation_policy_public_contract_overclaim", reasons)
        self.assertIn("principal_invalidation_policy_not_accepted", reasons)
        self.assertFalse(report["accepted_for_policy_review"])
        self.assertIsNone(report["resolved_input"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn("public_contract_overclaim", report["blockers"])
        detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "principal_invalidation_policy_public_contract_overclaim"
        )
        paths = {claim["path"] for claim in detail["overclaims"]}
        self.assertIn("$.publicAbiReady", paths)
        self.assertIn("$.public_callback_abi_now", paths)
        self.assertIn("$.claims.summary", paths)
        self.assertIn("$.claims.identity", paths)
        self.assertIn("$.claims.sdk", paths)

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
                "lifetime.generation_scope_invalidation.candidate_policy",
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
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
            [
                "privacy.identifier_redaction",
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
            ],
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
                "lifetime.generation_scope_invalidation.candidate_policy",
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
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

    def test_rejects_post_runtime_evidence_gate_weakened(self) -> None:
        decisions = self.load_decisions()
        gate = decisions["post_approved_runtime_evidence_gate"]
        gate["id"] = "public_readiness"
        gate["status"] = "ready"
        gate["active_after_resolved_input"] = "public_sdk_ready"
        gate["next_blocker"] = "public_readiness"
        gate["reported_current_blocker"] = "public_readiness"
        gate["required_unresolved_decision_keys"].remove(
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS[0]
        )
        gate["auditable_inputs"].remove("required_before_public_header")
        gate["next_required_artifact"] = {
            "id": "public_sdk_readiness_certificate",
            "status": "ready",
            "must_resolve_decision_keys": [],
        }
        gate["offline_preparation"]["does_not_unlock_identity_public_contract_gate"] = False
        gate["offline_preparation"]["p0_progress_contribution"] = 1
        gate["public_sdk_ready"] = True
        gate["public_header_allowed"] = True
        gate["public_header_gate_unlocked"] = True
        gate["public_identity_ready"] = True
        gate["permissions_admin_unlocked"] = True
        gate["command_response_unlocked"] = True
        gate["complete_sdk_ready"] = True
        gate["sdk_p0_progress_ready"] = True
        gate["stable_claim_ready"] = True
        gate["plugin_hub_ready"] = True
        gate["publication_ready"] = True
        gate["runtime_capture_authorized"] = True
        gate["non_claim"] = "public SDK readiness is satisfied"

        result = self.run_checker(decisions=decisions, approved_runtime_evidence=approved_manifest())
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        route_check = report["post_approved_runtime_evidence_route_check"]
        self.assertFalse(route_check["gap_report_valid"])
        self.assertTrue(route_check["invalid_gap_report"])
        self.assertFalse(route_check["remaining_route_blocker_is_legitimate"])
        self.assertIsNone(route_check["legitimate_remaining_route_blocker"])
        self.assertEqual(route_check["diagnostic_current_blocker"], "identity_public_contract_gate_missing")
        self.assertIn(
            "decisions_post_approved_runtime_evidence_gate_id_mismatch",
            route_check["invalid_gap_report_blockers"],
        )
        for blocker in (
            "decisions_post_approved_runtime_evidence_gate_id_mismatch",
            "decisions_post_approved_runtime_evidence_gate_status_mismatch",
            "decisions_post_approved_runtime_evidence_gate_active_input_mismatch",
            "decisions_post_approved_runtime_evidence_gate_reported_current_blocker_mismatch",
            "decisions_post_approved_runtime_evidence_gate_next_blocker_mismatch",
            "decisions_post_approved_runtime_evidence_gate_required_decision_keys_mismatch",
            "decisions_post_approved_runtime_evidence_gate_auditable_inputs_mismatch",
            "decisions_post_approved_runtime_evidence_gate_next_required_artifact_mismatch",
            "decisions_post_approved_runtime_evidence_gate_offline_preparation_mismatch",
            "decisions_post_approved_runtime_evidence_gate_non_claim_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        readiness_labels = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "readiness_flag_not_false"
        }
        self.assertIn("$.post_approved_runtime_evidence_gate.public_sdk_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.public_header_allowed", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.public_header_gate_unlocked", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.public_identity_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.permissions_admin_unlocked", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.command_response_unlocked", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.complete_sdk_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.sdk_p0_progress_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.stable_claim_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.plugin_hub_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.publication_ready", readiness_labels)
        self.assertIn("$.post_approved_runtime_evidence_gate.runtime_capture_authorized", readiness_labels)

    def test_rejects_identity_contract_gate_resolution_aliases_in_post_runtime_gate(self) -> None:
        decisions = self.load_decisions()
        gate = decisions["post_approved_runtime_evidence_gate"]
        gate["identityPublicContractGateOpen"] = True
        gate["identityPublicContractGateMissingResolved"] = True
        gate["identityPublicContractGateCleared"] = True
        gate["publicHeaderGateOpen"] = True

        result = self.run_checker(decisions=decisions, approved_runtime_evidence=approved_manifest())
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.post_approved_runtime_evidence_gate.identityPublicContractGateOpen", paths)
        self.assertIn("$.post_approved_runtime_evidence_gate.identityPublicContractGateMissingResolved", paths)
        self.assertIn("$.post_approved_runtime_evidence_gate.identityPublicContractGateCleared", paths)
        self.assertIn("$.post_approved_runtime_evidence_gate.publicHeaderGateOpen", paths)
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        route_check = report["post_approved_runtime_evidence_route_check"]
        self.assertFalse(route_check["gap_report_valid"])
        self.assertTrue(route_check["invalid_gap_report"])
        self.assertFalse(route_check["remaining_route_blocker_is_legitimate"])
        self.assertIsNone(route_check["legitimate_remaining_route_blocker"])
        self.assertIn("public_text_or_source_overclaim", route_check["invalid_gap_report_blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_post_runtime_identity_contract_checklist_rows_marked_resolved_or_counting(self) -> None:
        decisions = self.load_decisions()
        policy = decisions["post_runtime_identity_contract_checklist_policy"]
        policy["status"] = "resolved"
        policy["current_blocker_after_resolved_input"] = "public_header_gate_missing"
        policy["required_item_ids"] = policy["required_item_ids"][:-1]
        policy["must_remain_false"].remove("public_header_allowed")
        policy["per_item_zero_progress_fields"].remove("p0_progress_contribution")
        policy["non_claim"] = "Checklist rows resolve the identity public contract gate."
        item = policy["items"][0]
        item["status"] = "resolved"
        item["counts_as_public_readiness"] = True
        item["counts_toward_public_sdk"] = True
        item["counts_toward_p0_dependency_chain_claim"] = True
        item["p0_progress_contribution"] = 1
        item["complete_sdk_claim_progress_contribution"] = 1
        item["accepted_for_public_header_gate_review"] = True
        item["public_header_allowed"] = True
        item["promotion_ready"] = True
        item["non_claim"] = "Checklist row accepted for public header gate review."

        result = self.run_checker(decisions=decisions, approved_runtime_evidence=approved_manifest())
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "decisions_post_runtime_identity_contract_checklist_status_mismatch",
            "decisions_post_runtime_identity_contract_checklist_current_blocker_mismatch",
            "decisions_post_runtime_identity_contract_checklist_required_item_ids_mismatch",
            "decisions_post_runtime_identity_contract_checklist_item_status_present",
            "decisions_post_runtime_identity_contract_checklist_item_flag_not_false",
            "decisions_post_runtime_identity_contract_checklist_item_progress_not_zero",
            "decisions_post_runtime_identity_contract_checklist_item_non_claim_mismatch",
            "decisions_post_runtime_identity_contract_checklist_must_remain_false_mismatch",
            "decisions_post_runtime_identity_contract_checklist_progress_fields_mismatch",
            "decisions_post_runtime_identity_contract_checklist_non_claim_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        route_check = report["post_approved_runtime_evidence_route_check"]
        self.assertFalse(route_check["gap_report_valid"])
        self.assertFalse(route_check["remaining_route_blocker_is_legitimate"])
        self.assertIsNone(route_check["legitimate_remaining_route_blocker"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

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

    def test_rejects_permissions_admin_query_only_or_certificate_requirement_weakened(self) -> None:
        decisions = self.load_decisions()
        surfaces = self.load_surfaces()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        decisions_query_only = requirements["separation.no_commands_permissions_persistence"][
            "permissions_admin_query_only_planning"
        ]
        decisions_query_only["status"] = "ready"
        decisions_query_only["public_sdk_ready"] = True
        decisions_query_only["required_policy"].remove(
            "permissions/admin remains query-only planning until obelisk.player_identity.v1 is promoted"
        )
        decisions_query_only["forbidden_until_separate_promotion"].remove("admin actions")
        decisions_query_only["non_counting_artifacts"].remove(
            "missing, mismatched, stale, or hash-unbound promotion certificates"
        )
        decisions_certificate = decisions_query_only["required_identity_promotion_certificate"]
        decisions_certificate["surface_id"] = "obelisk.permissions_admin.v1"
        decisions_certificate["v1_dependency_chain_position"] = 2
        decisions_certificate["missing_mismatched_or_stale_certificate_counts"] = True

        permissions_surface = next(
            item for item in surfaces["surfaces"] if item["id"] == "obelisk.permissions_admin.v1"
        )
        surfaces_query_only = permissions_surface["v1_decision_contract"][
            "permissions_admin_query_only_planning"
        ]
        surfaces_query_only["complete_sdk_counting_allowed"] = True
        surfaces_query_only["non_counting_artifacts"].remove(
            "scoped non-complete-SDK release statements or exclusions"
        )
        surfaces_certificate = surfaces_query_only["required_identity_promotion_certificate"]
        surfaces_certificate["schema"] = "obelisk.scoped-release-statement.v1"
        surfaces_certificate["required_reviewed_artifact_hash"] = "diagnostic.report.sha256"

        result = self.run_checker(decisions=decisions, surfaces=surfaces)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "decisions_permissions_admin_query_only_status_mismatch",
            "decisions_permissions_admin_query_only_flag_not_false",
            "decisions_permissions_admin_query_only_policy_missing",
            "decisions_permissions_admin_query_only_forbidden_terms_missing",
            "decisions_permissions_admin_query_only_non_counting_artifacts_missing",
            "decisions_permissions_admin_identity_promotion_certificate_requirement_mismatch",
            "decisions_permissions_admin_identity_promotion_certificate_non_counting_flag_not_false",
            "surfaces_permissions_admin_query_only_flag_not_false",
            "surfaces_permissions_admin_query_only_non_counting_artifacts_missing",
            "surfaces_permissions_admin_identity_promotion_certificate_requirement_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_privacy_required_before_public_header_marked_resolved(self) -> None:
        decisions = self.load_decisions()
        for item in decisions["required_before_public_header"]:
            if item["id"] == "privacy.public_identifier_form":
                item["status"] = "resolved"

        result = self.run_checker(decisions=decisions)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("decisions_required_privacy_public_header_blocker_not_unresolved", report["blockers"])
        self.assertNotIn(
            "privacy.public_identifier_form",
            report["unresolved_public_contract_decision_keys"],
        )
        self.assertIn(
            "privacy.redacted_identifier_fields",
            report["unresolved_public_contract_decision_keys"],
        )

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

    def test_public_text_overclaims_rejects_split_key_value_aliases(self) -> None:
        claims = checker.public_text_overclaims(
            {
                "claims": [
                    {"key": "publicIdentityReady", "value": True},
                    {"key": "runtimePrincipalReady", "value": True},
                    {"key": "publicApiReady", "value": True},
                    {"field": "principalHandleAbiReady", "state": "ready"},
                    {"claim": "identityHeaderAllowed", "enabled": "yes"},
                    {"aliases": ["publicHeaderAllowed", "runtimeEvidenceReady"], "values": ["ready"]},
                    {"key": "publicApiReadiness", "readiness": "satisfied"},
                    {"key": "public_header_symbols_now", "values": ["PrivateOnlySymbol"]},
                    {"key": "publicIdentityReady", "value": False},
                    {"claims": ["publicHeaderAllowed"], "values": ["blocked"]},
                ],
                "public": {
                    "sdk": {"ready": True},
                    "header": {"symbols_now": ["PrivateOnlySymbol"]},
                    "capability": {"bits_now": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]},
                    "callback": {"abi_now": ["ObeliskPlayerPrincipalEventCallback"]},
                },
            }
        )
        paths = {claim["path"] for claim in claims}

        self.assertIn("$.claims[0]", paths)
        self.assertIn("$.claims[1]", paths)
        self.assertIn("$.claims[2]", paths)
        self.assertIn("$.claims[3]", paths)
        self.assertIn("$.claims[4]", paths)
        self.assertIn("$.claims[5]", paths)
        self.assertIn("$.claims[6]", paths)
        self.assertIn("$.claims[7]", paths)
        self.assertNotIn("$.claims[8]", paths)
        self.assertNotIn("$.claims[9]", paths)
        self.assertIn("$.public.sdk.ready", paths)
        self.assertIn("$.public.header.symbols_now", paths)
        self.assertIn("$.public.capability.bits_now", paths)
        self.assertIn("$.public.callback.abi_now", paths)

    def test_public_text_overclaims_rejects_provenance_status_aliases(self) -> None:
        claims = checker.public_text_overclaims(
            {
                "provenance": {
                    "route_snapshot_status": {
                        "source_provenance": "route_snapshot",
                        "status": "accepted",
                    },
                    "accepted_runtime_status": {
                        "source_provenance": "accepted_runtime_evidence_only",
                        "source_status": "ready",
                    },
                    "reviewed_contract_metadata_status": {
                        "source_provenance": "reviewed_hash_current_contract_review_only",
                        "state": "reviewed",
                    },
                    "reviewed_contract_metadata_progress": {
                        "source_provenance": "reviewed_hash_current_contract_review_only",
                        "progress": "1/4",
                    },
                }
            }
        )
        terms_by_path = {(claim["path"], claim["term"]) for claim in claims}

        for path, term in (
            ("$.provenance.route_snapshot_status.status", "non_promotional_provenance_status_alias"),
            (
                "$.provenance.accepted_runtime_status.source_status",
                "non_promotional_provenance_status_alias",
            ),
            (
                "$.provenance.reviewed_contract_metadata_status.state",
                "non_promotional_provenance_status_alias",
            ),
            (
                "$.provenance.reviewed_contract_metadata_progress.progress",
                "non_promotional_provenance_progress_alias",
            ),
        ):
            with self.subTest(path=path, term=term):
                self.assertIn((path, term), terms_by_path)

    def test_public_text_overclaims_rejects_requested_identity_aliases(self) -> None:
        claims = checker.public_text_overclaims(
            {
                "identityPublicContractReady": True,
                "publicIdentityReady": True,
                "lookupReady": True,
                "identityLookupAllowed": True,
                "identityLookupReady": True,
                "publicLookupReady": True,
                "runtimePrincipalReady": True,
                "publicHeaderAllowed": True,
                "permissionsReady": True,
                "permissionsAdminUnlocked": True,
                "commandsReady": True,
                "commandResponseUnlocked": True,
                "commandsRepliesUnlocked": True,
                "runtimeWorkAuthorized": True,
                "runtimeWorkAuthorization": "authorized",
                "serverOperationsAuthorized": True,
                "workspaceWritesAuthorized": True,
                "liveOpsAuthorized": True,
                "countsTowardSdk": True,
                "countsTowardV1": True,
                "countsTowardPublic": True,
                "countsTowardRuntime": True,
                "productionSdkReady": True,
                "stableSdkClaimAllowed": True,
                "stableSdkReady": True,
                "stableReleaseReady": True,
                "stablePublicationAuthorized": True,
                "pluginHubReady": True,
                "pluginHubPublication": True,
                "pluginHubPublicationReady": True,
                "pluginHubPublished": "published",
                "publication": True,
                "publicationAuthorized": True,
                "publicationReady": True,
                "publishedToPluginHub": True,
                "releasePublicationReady": True,
                "identityPublicContractDecisionRecordContractReviewOnly": True,
                "reviewedIdentityPublicContractDecisionRecordContractReviewOnly": True,
                "publicContractDecisionRecordReviewed": True,
                "publicContractDecisionRecordHashCurrent": True,
                "publicContractDecisionRecordContractReviewOnly": True,
                "contractReviewOnly": True,
                "mutationAllowed": True,
                "returnOverrideAllowed": True,
            }
        )
        paths = {claim["path"] for claim in claims}

        for path in (
            "$.identityPublicContractReady",
            "$.publicIdentityReady",
            "$.lookupReady",
            "$.identityLookupAllowed",
            "$.identityLookupReady",
            "$.publicLookupReady",
            "$.runtimePrincipalReady",
            "$.publicHeaderAllowed",
            "$.permissionsReady",
            "$.permissionsAdminUnlocked",
            "$.commandsReady",
            "$.commandResponseUnlocked",
            "$.commandsRepliesUnlocked",
            "$.runtimeWorkAuthorized",
            "$.runtimeWorkAuthorization",
            "$.serverOperationsAuthorized",
            "$.workspaceWritesAuthorized",
            "$.liveOpsAuthorized",
            "$.countsTowardSdk",
            "$.countsTowardV1",
            "$.countsTowardPublic",
            "$.countsTowardRuntime",
            "$.productionSdkReady",
            "$.stableSdkClaimAllowed",
            "$.stableSdkReady",
            "$.stableReleaseReady",
            "$.stablePublicationAuthorized",
            "$.pluginHubReady",
            "$.pluginHubPublication",
            "$.pluginHubPublicationReady",
            "$.pluginHubPublished",
            "$.publication",
            "$.publicationAuthorized",
            "$.publicationReady",
            "$.publishedToPluginHub",
            "$.releasePublicationReady",
            "$.identityPublicContractDecisionRecordContractReviewOnly",
            "$.reviewedIdentityPublicContractDecisionRecordContractReviewOnly",
            "$.publicContractDecisionRecordReviewed",
            "$.publicContractDecisionRecordHashCurrent",
            "$.publicContractDecisionRecordContractReviewOnly",
            "$.contractReviewOnly",
            "$.mutationAllowed",
            "$.returnOverrideAllowed",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_sanitize_non_promotional_report_rejects_split_key_value_aliases(self) -> None:
        blockers: list[dict] = []
        checker.sanitize_non_promotional_report(
            {
                "nested": [
                    {"key": "publicSdkReady", "value": True},
                    {"key": "publicApiReady", "value": True},
                    {"field": "public_header_symbols_now", "state": "ready"},
                    {"field": "public_api_symbols_now", "state": "ready"},
                    {"names": ["publicAbiReady", "runtimeEvidenceReady"], "statuses": ["available"]},
                    {"key": "public_header_symbols_now", "values": ["PrivateOnlySymbol"]},
                    {"key": "publicSdkReady", "value": False},
                    {"names": ["publicAbiReady"], "statuses": ["blocked"]},
                ],
                "public": {
                    "sdk": {"ready": True},
                    "header": {"symbols_now": ["PrivateOnlySymbol"]},
                    "capability": {"bits_now": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]},
                    "callback": {"abi_now": ["ObeliskPlayerPrincipalEventCallback"]},
                },
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        paths = {(item["reason"], item["label"]) for item in blockers}

        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[0]"), paths)
        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[1]"), paths)
        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[2]"), paths)
        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[3]"), paths)
        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[4]"), paths)
        self.assertIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[5]"), paths)
        self.assertNotIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[6]"), paths)
        self.assertNotIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[7]"), paths)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.public.sdk.ready"), paths)
        self.assertIn(("nested_public_header_symbols_now_not_empty", "$.unit_test.public.header.symbols_now"), paths)
        self.assertIn(("nested_public_capability_bits_now_not_empty", "$.unit_test.public.capability.bits_now"), paths)
        self.assertIn(("nested_public_callback_abi_now_not_empty", "$.unit_test.public.callback.abi_now"), paths)

    def test_sanitize_non_promotional_report_rejects_requested_identity_aliases(self) -> None:
        blockers: list[dict] = []
        sanitized = checker.sanitize_non_promotional_report(
            {
                "identityPublicContractReady": True,
                "publicIdentityReady": True,
                "lookupReady": True,
                "identityLookupAllowed": True,
                "identityLookupReady": True,
                "publicLookupReady": True,
                "runtimePrincipalReady": True,
                "publicHeaderAllowed": True,
                "permissionsReady": True,
                "permissionsAdminUnlocked": True,
                "commandsReady": True,
                "commandResponseUnlocked": True,
                "commandsRepliesUnlocked": True,
                "runtimeWorkAuthorized": True,
                "runtimeWorkAuthorization": "authorized",
                "serverOperationsAuthorized": True,
                "workspaceWritesAuthorized": True,
                "liveOpsAuthorized": True,
                "countsTowardSdk": True,
                "countsTowardV1": True,
                "countsTowardPublic": True,
                "countsTowardRuntime": True,
                "productionSdkReady": True,
                "stableSdkClaimAllowed": True,
                "stableSdkReady": True,
                "identityPublicContractDecisionRecordContractReviewOnly": True,
                "reviewedIdentityPublicContractDecisionRecordContractReviewOnly": True,
                "publicContractDecisionRecordReviewed": True,
                "publicContractDecisionRecordHashCurrent": True,
                "publicContractDecisionRecordContractReviewOnly": True,
                "contractReviewOnly": True,
                "mutationAllowed": True,
                "mutationReady": True,
                "returnOverrideAllowed": True,
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        labels = {(item["reason"], item["label"]) for item in blockers}

        for key in (
            "identityPublicContractReady",
            "publicIdentityReady",
            "lookupReady",
            "identityLookupAllowed",
            "identityLookupReady",
            "publicLookupReady",
            "runtimePrincipalReady",
            "publicHeaderAllowed",
            "permissionsReady",
            "permissionsAdminUnlocked",
            "commandsReady",
            "commandResponseUnlocked",
            "commandsRepliesUnlocked",
            "runtimeWorkAuthorized",
            "runtimeWorkAuthorization",
            "serverOperationsAuthorized",
            "workspaceWritesAuthorized",
            "liveOpsAuthorized",
            "countsTowardSdk",
            "countsTowardV1",
            "countsTowardPublic",
            "countsTowardRuntime",
            "productionSdkReady",
            "stableSdkClaimAllowed",
            "stableSdkReady",
            "identityPublicContractDecisionRecordContractReviewOnly",
            "reviewedIdentityPublicContractDecisionRecordContractReviewOnly",
            "publicContractDecisionRecordReviewed",
            "publicContractDecisionRecordHashCurrent",
            "publicContractDecisionRecordContractReviewOnly",
            "contractReviewOnly",
            "mutationAllowed",
            "mutationReady",
            "returnOverrideAllowed",
        ):
            with self.subTest(key=key):
                self.assertFalse(sanitized[key])
                self.assertIn(("nested_readiness_flag_not_false", f"$.unit_test.{key}"), labels)

    def test_sanitize_non_promotional_report_rejects_stable_and_downstream_unlock_aliases(self) -> None:
        blockers: list[dict] = []
        sanitized = checker.sanitize_non_promotional_report(
            {
                "stable_claim_allowed": True,
                "stable_release_ready": True,
                "plugin_hub_publication": True,
                "publication_authorized": True,
                "runtime_ready_alias": "ready",
                "helper_derived_readiness": "satisfied",
                "public_symbol_list": ["RegisterPlayerIdentityApi"],
                "permissionsAdminUnlocked": True,
                "commandResponseUnlocked": True,
                "commandsRepliesUnlocked": True,
                "runtimeWorkAuthorized": True,
                "countsTowardSdk": True,
                "countsTowardV1": True,
                "countsTowardPublic": True,
                "countsTowardRuntime": True,
                "productionSdkReady": True,
                "stableSdkClaimAllowed": True,
                "notes": [
                    "stable claim is allowed",
                    "Plugin Hub publication is published",
                    "publication is authorized",
                    "stable release is ready",
                    "helper-derived readiness is satisfied",
                    "permissions/admin is unlocked",
                    "command response is unlocked",
                    "commands/replies are ready",
                    "runtime work is authorized",
                    "counts toward public SDK",
                    "production SDK is ready",
                ],
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        labels = {(item["reason"], item["label"]) for item in blockers}

        self.assertFalse(sanitized["stable_claim_allowed"])
        self.assertFalse(sanitized["stable_release_ready"])
        self.assertFalse(sanitized["plugin_hub_publication"])
        self.assertFalse(sanitized["publication_authorized"])
        self.assertFalse(sanitized["runtime_ready_alias"])
        self.assertFalse(sanitized["helper_derived_readiness"])
        self.assertEqual(sanitized["public_symbol_list"], [])
        self.assertFalse(sanitized["permissionsAdminUnlocked"])
        self.assertFalse(sanitized["commandResponseUnlocked"])
        self.assertFalse(sanitized["commandsRepliesUnlocked"])
        self.assertFalse(sanitized["runtimeWorkAuthorized"])
        self.assertFalse(sanitized["countsTowardSdk"])
        self.assertFalse(sanitized["countsTowardV1"])
        self.assertFalse(sanitized["countsTowardPublic"])
        self.assertFalse(sanitized["countsTowardRuntime"])
        self.assertFalse(sanitized["productionSdkReady"])
        self.assertFalse(sanitized["stableSdkClaimAllowed"])
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.stable_claim_allowed"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.stable_release_ready"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.plugin_hub_publication"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.publication_authorized"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.runtime_ready_alias"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.helper_derived_readiness"), labels)
        self.assertIn(("nested_public_symbol_list_not_empty", "$.unit_test.public_symbol_list"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.permissionsAdminUnlocked"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.commandResponseUnlocked"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.commandsRepliesUnlocked"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.runtimeWorkAuthorized"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.countsTowardSdk"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.countsTowardV1"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.countsTowardPublic"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.countsTowardRuntime"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.productionSdkReady"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.stableSdkClaimAllowed"), labels)
        for index in range(11):
            self.assertIn(("nested_public_text_overclaim", f"$.unit_test.notes[{index}]"), labels)

    def test_public_text_overclaims_rejects_broad_identity_lookup_wording(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "player identity lookup surface",
                "PlayerIdentityResolver contract",
                "player_lookup_exclusion_review",
                "lookup-by-public-handle remains unavailable unless separately promoted",
            ]
        )
        by_path = {claim["path"]: claim["term"] for claim in claims}

        self.assertEqual(by_path["$[0]"], "broad_identity_lookup_wording")
        self.assertEqual(by_path["$[1]"], "broad_identity_lookup_wording")
        self.assertNotIn("$[2]", by_path)
        self.assertNotIn("$[3]", by_path)


if __name__ == "__main__":
    unittest.main()
