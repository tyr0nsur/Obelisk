#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_readiness.py."""

from __future__ import annotations

import copy
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
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_contract_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
REPO_REDACTION_EVIDENCE = (
    REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json"
)
PUBLIC_ABI_PREFLIGHT_CANDIDATE = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-public-abi-preflight-candidate.json"
)
OWNER_TOKEN_SDK_CONSUMER_CONTRACT = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-owner-token-sdk-consumer-contract.json"
)
IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "reviewed-identity-public-contract-decision-record.json"
)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    SAFE_OFFLINE_WORKSPACE,
    manifest as approved_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)
from test_check_player_identity_identifier_redaction_evidence import evidence as redaction_manifest
from test_check_player_identity_public_contract_decision_record import (
    TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL,
    TEST_STRICT_REPORT_SENTINEL,
    accepted_record as reviewed_identity_contract_record,
    strict_approved_runtime_check_report_ref,
)
import check_player_identity_public_contract_readiness as checker


RUNTIME_FIXTURE_NOW_SITECUSTOMIZE = """
from datetime import datetime, timezone

_OBELISK_RUNTIME_FIXTURE_NOW = datetime(2026, 6, 1, 12, 16, 0, tzinfo=timezone.utc)


def _obelisk_runtime_fixture_now_utc():
    return _OBELISK_RUNTIME_FIXTURE_NOW


import check_player_identity_runtime_principal_lifecycle_window_manifest as _obelisk_window_manifest
import check_player_identity_runtime_principal_lifecycle_approved_evidence as _obelisk_approved_evidence

_obelisk_window_manifest.now_utc = _obelisk_runtime_fixture_now_utc
_obelisk_approved_evidence.now_utc = _obelisk_runtime_fixture_now_utc
_obelisk_approved_evidence.window_manifest_checker.now_utc = _obelisk_runtime_fixture_now_utc
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


class PlayerIdentityPublicContractReadinessTests(unittest.TestCase):
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

    def normalize_runtime_manifest_paths(self, runtime: dict) -> dict:
        return copy.deepcopy(runtime)

    @staticmethod
    def runtime_fixture_now_utc() -> datetime:
        return datetime(2026, 6, 1, 12, 16, 0, tzinfo=timezone.utc)

    def identity_public_contract_decision_record_report(
        self,
        record_path: Path,
        blockers: list[dict],
    ) -> dict:
        approved_runtime_checker = checker.public_contract_decision_record.approved_runtime_checker
        with (
            mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
            mock.patch.object(approved_runtime_checker, "now_utc", self.runtime_fixture_now_utc),
            mock.patch.object(
                approved_runtime_checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                [SAFE_OFFLINE_WORKSPACE],
            ),
            mock.patch.object(
                approved_runtime_checker.window_manifest_checker,
                "now_utc",
                self.runtime_fixture_now_utc,
            ),
            mock.patch.object(
                approved_runtime_checker.window_manifest_checker,
                "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                [SAFE_OFFLINE_WORKSPACE],
            ),
        ):
            return checker.identity_public_contract_decision_record_report(record_path, blockers)

    def approved_runtime_fixture_env(self, root: Path) -> dict[str, str]:
        env = approved_runtime_safe_test_env()
        (root / "sitecustomize.py").write_text(RUNTIME_FIXTURE_NOW_SITECUSTOMIZE, encoding="utf-8")
        pythonpath_entries = [str(root), str(SCRIPT_DIR)]
        if env.get("PYTHONPATH"):
            pythonpath_entries.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
        return env

    def run_checker(
        self,
        decisions: dict,
        runtime: dict,
        *args: str,
        redaction: dict | None = None,
        public_abi_preflight_candidate: dict | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            redaction_args = []
            public_abi_preflight_args = []
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(self.normalize_runtime_manifest_paths(runtime)), encoding="utf-8")
            if redaction is not None:
                redaction_path = root / "identifier-redaction.json"
                redaction_path.write_text(json.dumps(redaction), encoding="utf-8")
                redaction_args = ["--identifier-redaction-evidence", str(redaction_path)]
            if public_abi_preflight_candidate is not None:
                public_abi_preflight_path = root / "public-abi-preflight.json"
                public_abi_preflight_path.write_text(json.dumps(public_abi_preflight_candidate), encoding="utf-8")
                public_abi_preflight_args = [
                    "--public-abi-preflight-candidate",
                    str(public_abi_preflight_path),
                ]
            planning_source_args = (
                []
                if "--planning-sources-dir" in args
                else ["--planning-sources-dir", str(self.planning_sources_dir)]
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    *redaction_args,
                    *public_abi_preflight_args,
                    *planning_source_args,
                    "--json",
                    *args,
                ],
                check=False,
                cwd=REPO_ROOT,
                env=self.approved_runtime_fixture_env(root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def public_abi_preflight_candidate(self) -> dict:
        return json.loads(PUBLIC_ABI_PREFLIGHT_CANDIDATE.read_text(encoding="utf-8"))

    def reviewed_identity_contract_record_bound_to_runtime(self, runtime: dict) -> dict:
        record = reviewed_identity_contract_record()
        record[TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL] = copy.deepcopy(runtime)
        record[TEST_STRICT_REPORT_SENTINEL] = None
        record["approved_runtime_evidence_binding"] = (
            checker.public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(runtime)
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
                mock.patch.object(checker.approved_evidence, "now_utc", self.runtime_fixture_now_utc),
                mock.patch.object(
                    checker.approved_evidence,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    [SAFE_OFFLINE_WORKSPACE],
                ),
                mock.patch.object(
                    checker.approved_evidence.window_manifest_checker,
                    "now_utc",
                    self.runtime_fixture_now_utc,
                ),
                mock.patch.object(
                    checker.approved_evidence.window_manifest_checker,
                    "APPROVED_OFFLINE_WORKSPACE_ROOTS",
                    [SAFE_OFFLINE_WORKSPACE],
                ),
            ):
                validation = checker.approved_evidence.validate_manifest(
                    runtime_manifest,
                    check_mode="consume",
                    input_path=runtime_manifest_path,
                )
                strict_report = checker.approved_evidence.build_report(
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

    def accepted_runtime_contract_review_report(self) -> dict:
        return {
            "schema": checker.approved_evidence.REPORT_SCHEMA,
            "mode": "consume",
            "ready": True,
            "ready_scope": checker.REQUIRED_APPROVED_RUNTIME_READY_SCOPE,
            "next_blocker": "identity_public_contract_gate_missing",
            "remaining_blockers": [],
            "resolved_inputs": [checker.REQUIRED_RESOLVED_INPUT],
            "observed_runtime_cases": checker.REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
            "consumer_cases": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
            "consumer_boundary_assertions": checker.REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "public_header_allowed": False,
            "public_api_ready": False,
            "public_abi_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "command_response_ready": False,
            "complete_sdk_ready": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "resource_handle_supported": False,
            "mutation_allowed": False,
            "live_ops_authorized": False,
            "v1_completion_ready": False,
            "v1_completion_evidence": False,
            "public_sdk_v1_completion_claim": False,
        }

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
            "stable_ready",
            "stable_claim_allowed",
            "stable_claim_ready",
            "stable_sdk_ready",
            "plugin_hub_ready",
            "plugin_hub_publication_ready",
            "publication_ready",
            "publication_authorized",
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

    def assert_post_runtime_identity_contract_checklist_closed(self, checklist: dict) -> None:
        self.assertTrue(checklist["present"])
        self.assertTrue(checklist["fail_closed"])
        self.assertEqual(
            checklist["policy"],
            checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY,
        )
        self.assertEqual(
            checklist["only_valid_post_runtime_route"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            checklist["required_item_ids"],
            checker.POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS,
        )
        items = {item["id"]: item for item in checklist["items"]}
        policy_items = {
            item["id"]: item
            for item in checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY["items"]
        }
        for item_id in checker.POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS:
            with self.subTest(checklist_item=item_id):
                self.assertIn(item_id, items)
                item = items[item_id]
                policy_item = policy_items[item_id]
                for field in checker.POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_REQUIRED_ITEM_FIELDS:
                    self.assertIn(field, item)
                self.assertEqual(item["required_next_action"], policy_item["required_next_action"])
                self.assertEqual(item["blocks_until"], policy_item["blocks_until"])
                self.assertEqual(item["review_scope"], policy_item["review_scope"])
                self.assertFalse(item["counts_as_public_readiness"])
                self.assertFalse(item["counts_toward_public_sdk"])
                self.assertFalse(item["counts_toward_runtime"])
                self.assertFalse(item["counts_toward_v1_completion"])
                self.assertFalse(item["counts_toward_complete_sdk_claim"])
                self.assertFalse(item["counts_toward_p0_dependency_chain_claim"])
                self.assertEqual(item["p0_progress_contribution"], 0)
                self.assertEqual(item["complete_sdk_claim_progress_contribution"], 0)
                self.assertFalse(item["accepted_for_public_header_gate_review"])
                self.assertFalse(item["public_header_allowed"])
                self.assertFalse(item["promotion_ready"])
                self.assertFalse(item["public_sdk_ready"])
                self.assertFalse(item["runtime_ready"])
                self.assertFalse(item["v1_completion_evidence"])
                self.assertEqual(
                    item["non_claim"],
                    checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM,
                )
        for key in checker.POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS:
            with self.subTest(post_runtime_identity_checklist_false_flag=key):
                self.assertFalse(checklist[key])
                self.assertIn(key, checklist["must_remain_false"])
        self.assertEqual(checklist["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(checklist["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertEqual(
            checklist["non_claim"],
            checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM,
        )

    def multi_surface_beta_capture_binding(self) -> dict:
        return {
            "schema": checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
            "accepted_for_contract_review": True,
            "resolved_input": checker.REQUIRED_RESOLVED_INPUT,
            "next_blocker": "identity_public_contract_gate_missing",
            "artifact_kind": (
                checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND
            ),
            "evidence_pack_id": "candidate-multi-surface-beta-capture-pack-test",
            "artifact_sha256": "a" * 64,
            "source_kind": checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
            "source_path": "/tmp/obelisk-offline/multi-surface-beta-capture-pack/Obelisk.log",
            "source_sha256": "b" * 64,
            "copied_log_path": "/tmp/obelisk-offline/multi-surface-beta-capture-pack/Obelisk.log",
            "copied_log_sha256": "b" * 64,
            "binding_scope": checker.public_contract_decision_record.REVIEW_ROUTE,
            "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
            "counts_toward_public_sdk": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "v1_completion_evidence": False,
            "non_claim": checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
        }

    def accepted_principal_start_end_runtime_report(self) -> dict:
        return {
            "schema": checker.PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA,
            "ready": True,
            "ready_scope": checker.PRINCIPAL_START_END_READY_SCOPE,
            "accepted_for_contract_review": True,
            "principal_start_end_runtime_evidence_present": True,
            "principal_start_end_runtime_evidence_ready": True,
            "resolved_inputs": [checker.PRINCIPAL_START_END_RESOLVED_INPUT],
            "remaining_runtime_inputs": sorted(checker.PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
            "does_not_resolve": sorted(checker.PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
            "next_review_blocker": checker.PRINCIPAL_START_END_NEXT_REVIEW_BLOCKER,
            "strict_approved_runtime_evidence_blockers": [
                checker.PRINCIPAL_START_END_MISSING_CHECK_JOIN_BLOCKER
            ],
            "approved_runtime_evidence_blockers": [
                checker.PRINCIPAL_START_END_MISSING_CHECK_JOIN_BLOCKER
            ],
            "contract_review_input_counts_as_approved_runtime_evidence": False,
            "diagnostic_coverage": {
                "check_join_in_progress_diagnostic_count": 1,
                "diagnostic_candidates_count_as_evidence": False,
            },
            "approved_runtime_evidence": False,
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_ready": False,
            "stable_claim_allowed": False,
            "publication_authorized": False,
            "blockers": [],
            "non_claims": [
                "principal start/end runtime evidence is not the approved three-role lifecycle evidence bundle",
                "this checker does not promote public identity, lookup, public ABI/header, permissions/admin, commands, runtime readiness, SDK readiness, stable claims, or publication",
            ],
        }

    def accepted_runtime_report_from_simulation(self) -> tuple[dict, list[dict], dict]:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_manifest = approved_manifest()
            runtime_path.write_text(json.dumps(runtime_manifest), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)
        return report, blockers, runtime_manifest

    def test_accepts_runtime_evidence_for_contract_review_only(self) -> None:
        result = self.run_checker(self.decisions(), approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "contract_review_input_only")
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "identity_public_contract_decision_record_missing_or_not_accepted",
            report["blockers"],
        )
        self.assertEqual(
            report["resolved_inputs"],
            [
                "runtime.lifecycle_evidence",
                "privacy.identifier_redaction",
                "lifetime.generation_scope_invalidation.candidate_policy",
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
            ],
        )
        self.assertEqual(report["contract_review_inputs_resolved"], report["resolved_inputs"])
        self.assertEqual(report["remaining_contract_review_inputs"], [])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_contract_allowed"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        for alias in (
            "identityPublicContractReady",
            "publicIdentityReady",
            "publicPrincipalReady",
            "lookupReady",
            "permissionsReady",
            "commandsReady",
            "stableSdkReady",
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
        self.assertFalse(
            report["identity_public_contract_gate_missing"]["redactionEvidencePromotesIdentity"]
        )
        self.assertIn(
            "runtime lifecycle evidence intake has consume-only scope; "
            "identity promotion remains blocked pending reviewed identity-contract evidence",
            report["public_identity_non_promotional_reasons"],
        )
        self.assertTrue(
            any(
                "readiness-alias artifacts cannot resolve runtime.lifecycle_evidence" in reason
                for reason in report["public_identity_non_promotional_reasons"]
            )
        )
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertTrue(report["public_header_scan"]["readable"])
        self.assertEqual(report["public_header_scan"]["detected_player_identity_tokens"], [])
        self.assertEqual(
            report["required_tests_before_public_header"]["covered_for_contract_review_only"],
            ["identity.fail_closed", "runtime.evidence_intake"],
        )
        self.assertIn("abi.layout", report["required_tests_before_public_header"]["remaining_missing"])
        self.assertIn("sdk.consumer", report["required_tests_before_public_header"]["remaining_missing"])
        self.assertNotIn("identity.fail_closed", report["required_tests_before_public_header"]["remaining_missing"])
        self.assertNotIn("runtime.lifecycle_evidence", report["remaining_blockers"])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertNotEqual(report["next_blocker"], "public_readiness")
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]
        self.assertTrue(post_runtime_gate["active"])
        self.assertEqual(
            post_runtime_gate["id"],
            "identity_public_contract_gate.reviewed_identity_public_contract",
        )
        self.assertEqual(post_runtime_gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            post_runtime_gate["required_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_gate["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
        )
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, post_runtime_gate["required_unresolved_decision_keys"])
                self.assertIn(key, post_runtime_gate["remaining_unresolved_decision_keys"])
        self.assertEqual(
            set(post_runtime_gate["auditable_inputs"]),
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS,
        )
        self.assertEqual(
            post_runtime_gate["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(
            post_runtime_gate["offline_preparation"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        self.assertEqual(
            post_runtime_gate["offline_preparation"]["blocked_until_resolved_input"],
            "runtime.lifecycle_evidence",
        )
        self.assertTrue(post_runtime_gate["offline_preparation"]["must_bind_to_approved_runtime_evidence"])
        self.assertTrue(post_runtime_gate["offline_preparation"]["must_bind_current_source_artifacts"])
        self.assertTrue(post_runtime_gate["offline_preparation"]["must_remain_contract_review_only"])
        self.assertTrue(
            post_runtime_gate["offline_preparation"]["does_not_unlock_identity_public_contract_gate"]
        )
        self.assertTrue(post_runtime_gate["offline_preparation"]["does_not_unlock_public_header_gate"])
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(offline_preparation_key=key):
                self.assertFalse(post_runtime_gate["offline_preparation"][key])
        alias_policy = checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY
        self.assertEqual(post_runtime_gate["non_counting_candidate_alias_policy"], alias_policy)
        self.assertEqual(
            post_runtime_gate["next_required_artifact"]["non_counting_candidate_alias_policy"],
            alias_policy,
        )
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["non_counting_candidate_alias_policy"],
            alias_policy,
        )
        for key in (
            "can_count_candidate_aliases",
            "can_count_preflight_aliases",
            "can_count_review_aliases",
            "can_unlock_identity_public_contract_gate_missing",
            "can_unlock_public_identity_contract_readiness",
            "can_replace_reviewed_identity_public_contract_decision_record",
            "accepted_for_public_header_gate_review",
        ):
            with self.subTest(candidate_alias_policy=key):
                self.assertFalse(alias_policy[key])
        self.assertEqual(alias_policy["p0_progress_contribution"], 0)
        self.assertIn("preflight aliases", alias_policy["alias_classes"])
        self.assertIn("review-status aliases", alias_policy["alias_classes"])
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(post_runtime_gate[key])
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
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["next_auditable_blocker"][
                "offline_preparation"
            ],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertEqual(post_runtime_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            post_runtime_gap["only_valid_post_runtime_route"],
            "identity_public_contract_gate_missing",
        )
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
        self.assert_post_runtime_contract_gap_diagnostic_closed(post_runtime_contract_gap)
        self.assertTrue(
            report["approved_runtime_evidence"]["source_provenance_policy"][
                "non_promotional_sources_rejected"
            ]
        )
        for key in (
            "promotion_ready",
            "public_contract_allowed",
            "public_sdk_ready",
            "runtime_ready",
            "public_api_ready",
            "public_abi_ready",
            "public_header_allowed",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(key=key):
                self.assertFalse(report["approved_runtime_evidence"][key])

    def test_simulated_accepted_runtime_evidence_still_requires_decision_record_gate(self) -> None:
        runtime_report, blockers, _runtime_manifest = self.accepted_runtime_report_from_simulation()
        decisions = self.decisions()
        report = checker.build_report(
            decisions,
            runtime_report,
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["identity_public_contract_decision_record_missing_or_not_accepted"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        currentness = report["runtime_evidence_contract_review_currentness"]
        self.assertTrue(currentness["runtime_evidence_accepted"])
        self.assertFalse(currentness["reviewed_decision_record_accepted"])
        self.assertEqual(
            currentness["only_next_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(
            currentness["accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"]
        )
        self.assertFalse(currentness["candidate_preflight_review_aliases_count"])
        self.assertFalse(currentness["permissions_admin_unlocked_from_runtime_evidence"])
        self.assertFalse(currentness["command_surface_unlocked_from_runtime_evidence"])
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertTrue(report["post_approved_runtime_evidence_gate"]["active"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertFalse(report["identity_public_contract_decision_record"]["provided"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        for key in (
            "promotion_ready",
            "public_readiness",
            "public_sdk_ready",
            "runtime_readiness",
            "runtime_ready",
            "v1_ready",
            "v1_completion_ready",
            "v1_completion_evidence",
            "complete_sdk_ready",
            "complete_sdk_counting_allowed",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
            "resource_handle_ready",
            "resource_handle_supported",
            "mutation_allowed",
            "mutation_ready",
            "return_override_allowed",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(report["post_approved_runtime_evidence_gate"][key])
                self.assertFalse(report["approved_runtime_evidence"][key])

    def test_simulated_accepted_runtime_context_only_activates_contract_review_gate(self) -> None:
        runtime_report, blockers, _runtime_manifest = self.accepted_runtime_report_from_simulation()
        report = checker.build_report(
            self.decisions(),
            runtime_report,
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["identity_public_contract_decision_record_missing_or_not_accepted"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["ready_scope"], "contract_review_input_only")
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertTrue(report["post_approved_runtime_evidence_gate"]["active"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        checklist = report["post_runtime_identity_contract_checklist"]
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["post_runtime_identity_contract_checklist"],
            checklist,
        )
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["post_runtime_identity_contract_checklist"],
            checklist,
        )
        self.assertTrue(checklist["active"])
        self.assertEqual(checklist["runtime_evidence_status"], "accepted")
        self.assertEqual(checklist["reviewed_identity_contract_status"], "missing_or_not_accepted")
        self.assertEqual(checklist["approved_runtime_resolved_input"], checker.REQUIRED_RESOLVED_INPUT)
        self.assertEqual(
            checklist["immediate_next_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(
            checklist["missing_review_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
        )
        self.assertEqual(
            checklist["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assert_post_runtime_identity_contract_checklist_closed(checklist)
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertEqual(report["identity_public_contract_decision_record"]["resolved_decision_keys"], [])
        for key in (
            "public_header_allowed",
            "public_api_ready",
            "public_abi_ready",
            "public_sdk_ready",
            "runtime_ready",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
            "live_ops_authorized",
            "server_operations_authorized",
            "workspace_writes_authorized",
            "runtime_capture_authorized",
            "reads_live_logs",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(report["post_approved_runtime_evidence_gate"][key])
                self.assertFalse(report["approved_runtime_evidence"][key])

    def test_post_runtime_identity_contract_checklist_exists_before_runtime_evidence(self) -> None:
        blockers: list[dict] = []
        report = checker.build_report(
            self.decisions(),
            checker.missing_approved_runtime_report(),
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        checklist = report["post_runtime_identity_contract_checklist"]
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["post_runtime_identity_contract_checklist"],
            checklist,
        )
        self.assertFalse(checklist["active"])
        self.assertEqual(checklist["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(checklist["runtime_evidence_status"], "missing_or_not_accepted")
        self.assertEqual(
            checklist["reviewed_identity_contract_status"],
            "blocked_until_approved_runtime_evidence",
        )
        self.assertIsNone(checklist["approved_runtime_resolved_input"])
        self.assertEqual(checklist["missing_review_decision_keys"], [])
        self.assertEqual(checklist["remaining_public_header_decision_keys"], [])
        self.assertEqual(
            checklist["immediate_next_artifact"]["id"],
            "approved_runtime_principal_lifecycle_evidence_bundle",
        )
        self.assert_post_runtime_identity_contract_checklist_closed(checklist)

    def test_principal_start_end_runtime_evidence_stays_non_counting_until_approved_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "principal-start-end-evidence.check.json"
            evidence_path.write_text(
                json.dumps(self.accepted_principal_start_end_runtime_report()),
                encoding="utf-8",
            )
            blockers: list[dict] = []
            start_end_report = checker.principal_start_end_runtime_report(evidence_path, blockers)

        report = checker.build_report(
            self.decisions(),
            checker.missing_approved_runtime_report(),
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
            principal_start_end_runtime_report=start_end_report,
        )

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_missing_or_not_ready"],
        )
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.PRINCIPAL_START_END_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertIn(checker.REQUIRED_RESOLVED_INPUT, report["remaining_contract_review_inputs"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertFalse(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["active"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["offline_preparation"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["offline_preparation"][
                "current_blocker_before_resolved_input"
            ],
            "approved_runtime_evidence_missing",
        )
        self.assertFalse(report["approved_runtime_evidence"]["approved_runtime_evidence_present"])
        self.assertFalse(report["approved_runtime_evidence"]["runtime_evidence_ready"])
        start_end = report["principal_start_end_runtime_evidence"]
        self.assertTrue(start_end["accepted_for_contract_review"])
        self.assertTrue(start_end["principal_start_end_runtime_evidence_present"])
        self.assertEqual(start_end["next_review_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(
            start_end["strict_approved_runtime_evidence_blockers"],
            [checker.PRINCIPAL_START_END_MISSING_CHECK_JOIN_BLOCKER],
        )
        self.assertFalse(start_end["approved_runtime_evidence_present"])
        self.assertFalse(start_end["public_sdk_ready"])
        self.assertFalse(start_end["runtime_ready"])
        runtime_contract_input = report["runtime_contract_input"]
        self.assertFalse(runtime_contract_input["accepted_for_contract_review"])
        self.assertEqual(runtime_contract_input["kind"], "none")
        self.assertIsNone(runtime_contract_input["resolved_input"])
        self.assertTrue(runtime_contract_input["principal_start_end_runtime_evidence_accepted"])
        self.assertFalse(runtime_contract_input["approved_runtime_principal_lifecycle_evidence_bundle_resolved"])
        self.assertTrue(runtime_contract_input["strict_runtime_lifecycle_evidence_still_unresolved"])
        self.assertEqual(
            runtime_contract_input["does_not_resolve"],
            sorted(checker.PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
        )
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        runtime_input = contract_gate_inputs[checker.REQUIRED_RESOLVED_INPUT]
        self.assertEqual(runtime_input["review_inputs_resolved"], [])
        self.assertEqual(runtime_input["review_inputs_missing"], [checker.REQUIRED_RESOLVED_INPUT])
        self.assertEqual(runtime_input["strict_review_inputs_unresolved"], [checker.REQUIRED_RESOLVED_INPUT])
        self.assertEqual(
            runtime_input["non_counting_review_inputs_present"],
            [checker.PRINCIPAL_START_END_RESOLVED_INPUT],
        )
        self.assertIn(checker.REQUIRED_RESOLVED_INPUT, report["remaining_blockers"])

    def test_principal_start_end_runtime_evidence_overclaim_does_not_advance_contract_review(self) -> None:
        bad_report = self.accepted_principal_start_end_runtime_report()
        bad_report["public_sdk_ready"] = True
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "principal-start-end-evidence.check.json"
            evidence_path.write_text(json.dumps(bad_report), encoding="utf-8")
            blockers: list[dict] = []
            start_end_report = checker.principal_start_end_runtime_report(evidence_path, blockers)

        report = checker.build_report(
            self.decisions(),
            checker.missing_approved_runtime_report(),
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
            principal_start_end_runtime_report=start_end_report,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["principal_start_end_runtime_evidence"]["accepted_for_contract_review"])
        self.assertIn("principal_start_end_runtime_evidence_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")

    def test_principal_start_end_runtime_evidence_requires_explicit_checkjoin_blocker(self) -> None:
        bad_report = self.accepted_principal_start_end_runtime_report()
        bad_report["strict_approved_runtime_evidence_blockers"] = []
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "principal-start-end-evidence.check.json"
            evidence_path.write_text(json.dumps(bad_report), encoding="utf-8")
            blockers: list[dict] = []
            start_end_report = checker.principal_start_end_runtime_report(evidence_path, blockers)

        self.assertFalse(start_end_report["accepted_for_contract_review"])
        self.assertIn(
            "principal_start_end_runtime_evidence_missing_explicit_checkjoin_blocker",
            [blocker["reason"] for blocker in blockers],
        )

    def test_cli_keeps_principal_start_end_runtime_evidence_non_counting_without_approved_runtime_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            start_end_path = root / "principal-start-end-evidence.check.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")
            start_end_path.write_text(
                json.dumps(self.accepted_principal_start_end_runtime_report()),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--principal-start-end-runtime-evidence",
                    str(start_end_path),
                    "--planning-sources-dir",
                    str(self.planning_sources_dir),
                    "--json",
                ],
                check=False,
                cwd=REPO_ROOT,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["runtime_contract_input"]["kind"], "none")
        self.assertTrue(report["runtime_contract_input"]["principal_start_end_runtime_evidence_accepted"])
        self.assertNotIn(checker.PRINCIPAL_START_END_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertFalse(report["approved_runtime_evidence"]["approved_runtime_evidence_present"])

    def test_cli_blocks_principal_start_end_with_current_decision_record_until_approved_runtime_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            start_end_path = root / "principal-start-end-evidence.check.json"
            record_path = root / "reviewed-identity-public-contract-decision-record.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")
            start_end_path.write_text(
                json.dumps(self.accepted_principal_start_end_runtime_report()),
                encoding="utf-8",
            )
            self.write_identity_contract_record(record_path, reviewed_identity_contract_record())

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--principal-start-end-runtime-evidence",
                    str(start_end_path),
                    "--identity-public-contract-decision-record",
                    str(record_path),
                    "--planning-sources-dir",
                    str(self.planning_sources_dir),
                    "--json",
                ],
                check=False,
                cwd=REPO_ROOT,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertIn(
            "identity_public_contract_decision_record_approved_runtime_evidence_binding_not_accepted",
            report["blockers"],
        )
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["runtime_contract_input"]["kind"], "none")
        self.assertFalse(report["runtime_contract_input"]["strict_approved_runtime_evidence_accepted"])
        self.assertFalse(
            report["runtime_contract_input"]["approved_runtime_principal_lifecycle_evidence_bundle_resolved"]
        )
        self.assertTrue(report["runtime_contract_input"]["strict_runtime_lifecycle_evidence_still_unresolved"])
        self.assertTrue(report["runtime_contract_input"]["principal_start_end_runtime_evidence_accepted"])
        self.assertNotIn(checker.PRINCIPAL_START_END_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["active"])
        self.assertFalse(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["provided"])
        self.assertTrue(record["record_valid"])
        self.assertTrue(record["hash_bound_to_current_source_artifacts"])
        self.assertTrue(record["reviewed_hash_current_contract_review_only"])
        self.assertFalse(record["accepted_for_contract_review"])
        self.assertFalse(record["approved_runtime_evidence_binding_matches_accepted_runtime_evidence"])
        self.assertEqual(record["approved_runtime_evidence_binding_required_input"], checker.REQUIRED_RESOLVED_INPUT)
        self.assertEqual(record["resolved_decision_keys"], [])
        self.assertEqual(record["review_inputs_non_counting_until"], checker.REQUIRED_RESOLVED_INPUT)
        for key in (
            "promotion_ready",
            "public_sdk_ready",
            "runtime_ready",
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
            "counts_toward_p0_dependency_chain_claim",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_simulated_accepted_runtime_false_promotion_claims_do_not_resolve_runtime_input(self) -> None:
        runtime_report = {
            **self.accepted_runtime_contract_review_report(),
            "accepted_for_contract_review": True,
            "public_api_ready": True,
            "public_header_readiness": "satisfied",
            "lookup_ready": True,
            "permissions_admin_ready": True,
            "command_response_ready": True,
            "complete_sdk_ready": True,
            "p0_progress_ready": True,
            "sdk_p0_progress_ready": True,
            "resource_handle_supported": True,
            "mutation_allowed": True,
            "live_ops_authorized": True,
        }
        blockers: list[dict] = []

        report = checker.build_report(
            self.decisions(),
            runtime_report,
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        for key in (
            "public_api_ready",
            "public_header_readiness",
            "lookup_ready",
            "permissions_admin_ready",
            "command_response_ready",
            "complete_sdk_ready",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
            "resource_handle_supported",
            "mutation_allowed",
            "live_ops_authorized",
        ):
            with self.subTest(key=key):
                self.assertIn(f"approved_runtime_evidence_{key}_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])

    def test_valid_decision_record_does_not_resolve_without_runtime_evidence(self) -> None:
        runtime_report = {
            "accepted_for_contract_review": False,
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        }
        blockers: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, reviewed_identity_contract_record())
            decision_record = self.identity_public_contract_decision_record_report(record_path, blockers)

        self.assertTrue(decision_record["accepted_for_contract_review"])
        report = checker.build_report(
            self.decisions(),
            runtime_report,
            decision_record,
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["provided"])
        self.assertTrue(record["record_valid"])
        self.assertFalse(record["accepted_for_contract_review"])
        self.assertFalse(record["reviewed_template_only"])
        self.assertTrue(record["strict_accepted_decision_record"])
        self.assertFalse(record["accepted_post_runtime_decision_record"])
        self.assertFalse(record["accepted_as_next_identity_contract_input"])
        self.assertFalse(record["public_header_readiness_from_decision_record"])
        self.assertEqual(record["resolved_decision_keys"], [])
        self.assertEqual(record["review_inputs_non_counting_until"], checker.REQUIRED_RESOLVED_INPUT)
        self.assertFalse(record["public_header_allowed"])
        self.assertFalse(record["public_abi_ready"])
        self.assertFalse(record["public_sdk_ready"])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        for item in contract_gate_inputs.values():
            with self.subTest(input_id=item["id"]):
                self.assertEqual(item["review_inputs_resolved"], [])
                self.assertFalse(item["public_header_allowed"])
                self.assertFalse(item["public_sdk_ready"])

    def test_reviewed_template_only_decision_record_remains_non_counting_after_runtime_evidence(self) -> None:
        runtime = approved_manifest()
        record = self.reviewed_identity_contract_record_bound_to_runtime(runtime)
        record["accepted_for_contract_review"] = False
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                runtime,
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIn(
            "identity_public_contract_decision_record_missing_or_not_accepted",
            report["blockers"],
        )
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
        post_runtime_gate = report["post_approved_runtime_evidence_gate"]
        self.assertFalse(
            post_runtime_gate["accepted_decision_record_as_next_identity_contract_input"]
        )
        self.assertFalse(post_runtime_gate["accepted_decision_record_opens_public_header_gate"])
        self.assertFalse(post_runtime_gate["public_header_readiness_from_decision_record"])
        self.assertFalse(post_runtime_gate["identity_contract_gate_complete"])
        self.assertEqual(post_runtime_gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_multi_surface_beta_capture_pack_binding_cannot_satisfy_runtime_or_contract_readiness(self) -> None:
        binding = self.multi_surface_beta_capture_binding()
        runtime_report = {
            **self.accepted_runtime_contract_review_report(),
            "accepted_for_contract_review": True,
            "resolved_inputs": [checker.REQUIRED_RESOLVED_INPUT],
            "approved_runtime_evidence_binding": binding,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "sdk_progress": 0,
        }
        decision_record = {
            "provided": True,
            "accepted_for_contract_review": True,
            "record_valid": True,
            "hash_bound_to_current_source_artifacts": True,
            "contract_review_only": True,
            "reviewed_hash_current_contract_review_only": True,
            "approved_runtime_evidence_binding": binding,
            "resolved_decision_keys": checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
            "blockers": [],
        }
        blockers: list[dict] = []

        report = checker.build_report(
            self.decisions(),
            runtime_report,
            decision_record,
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertIn(
            "approved_runtime_evidence_multi_surface_beta_capture_candidate_artifact_not_counting",
            report["blockers"],
        )
        self.assertIn(
            "identity_public_contract_decision_record_multi_surface_beta_capture_binding_not_counting",
            report["blockers"],
        )
        self.assertIn(
            "identity_public_contract_decision_record_approved_runtime_evidence_binding_not_accepted",
            report["blockers"],
        )
        self.assertFalse(
            report["identity_public_contract_decision_record"][
                "approved_runtime_evidence_binding_matches_accepted_runtime_evidence"
            ]
        )
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["active"])
        for key in (
            "public_sdk_ready",
            "runtime_ready",
            "public_contract_allowed",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
            "counts_toward_p0_dependency_chain_claim",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_post_runtime_gate_route_extras(self) -> None:
        decisions = self.decisions()
        decisions["post_approved_runtime_evidence_gate"]["publicHeaderGateOpen"] = False
        decisions["post_approved_runtime_evidence_gate"]["supportTierReady"] = False

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_approved_runtime_evidence_gate_unexpected_route_extras", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "post_approved_runtime_evidence_gate_unexpected_route_extras"
        )
        self.assertEqual(detail["unexpected"], ["publicHeaderGateOpen", "supportTierReady"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_post_runtime_identity_contract_checklist_policy_drift(self) -> None:
        decisions = self.decisions()
        decisions["post_runtime_identity_contract_checklist_policy"]["items"][0][
            "required_next_action"
        ] = "accept runtime evidence as public SDK readiness"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "post_runtime_identity_contract_checklist_policy_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["accepted_for_contract_review"])
        checklist = report["post_runtime_identity_contract_checklist"]
        self.assertEqual(
            checklist["policy"],
            checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY,
        )
        self.assert_post_runtime_identity_contract_checklist_closed(checklist)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_simulated_accepted_runtime_and_decision_record_still_require_public_header_gate(self) -> None:
        runtime_report, blockers, runtime_manifest = self.accepted_runtime_report_from_simulation()
        with tempfile.TemporaryDirectory() as tmp:
            record = reviewed_identity_contract_record()
            record[TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL] = copy.deepcopy(runtime_manifest)
            record["approved_runtime_evidence_binding"] = runtime_report["approved_runtime_evidence_binding"]
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            decision_record = self.identity_public_contract_decision_record_report(
                record_path,
                blockers,
            )
        decisions = self.decisions()
        report = checker.build_report(
            decisions,
            runtime_report,
            decision_record,
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertEqual(blockers, [])
        self.assertTrue(report["ready"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertTrue(report["identity_public_contract_decision_record"]["provided"])
        self.assertTrue(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertTrue(report["identity_public_contract_decision_record"]["record_valid"])
        self.assertTrue(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertTrue(report["identity_public_contract_decision_record"]["contract_review_only"])
        self.assertFalse(
            report["identity_public_contract_decision_record"][
                "runtime_evidence_contract_review_currentness"
            ]["candidate_preflight_review_aliases_count"]
        )
        self.assertTrue(
            report["identity_public_contract_decision_record"][
                "runtime_evidence_contract_review_currentness"
            ]["observed"]["runtime_evidence_binding_valid"]
        )
        self.assertFalse(
            report["post_approved_runtime_evidence_gate"][
                "runtime_evidence_contract_review_currentness"
            ]["accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"]
        )
        self.assertTrue(
            report["identity_public_contract_decision_record"]["reviewed_hash_current_contract_review_only"]
        )
        self.assertFalse(report["identity_public_contract_decision_record"]["identity_contract_gate_complete"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_required_artifact"]["status"],
            "accepted_for_contract_review",
        )
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["identity_contract_gate_complete"])
        self.assertEqual(
            report["public_header_gate_missing"]["next_required_artifact"],
            checker.REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
        )
        for key in (
            "promotion_ready",
            "public_readiness",
            "public_sdk_ready",
            "runtime_readiness",
            "runtime_ready",
            "v1_ready",
            "v1_completion_ready",
            "v1_completion_evidence",
            "live_ops_authorized",
            "server_operations_authorized",
            "workspace_writes_authorized",
            "runtime_capture_authorized",
            "reads_live_logs",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(report["public_header_gate_missing"][key])
                self.assertFalse(report["identity_public_contract_decision_record"][key])

    def test_build_report_does_not_skip_header_gate_from_unvalidated_resolved_statuses(self) -> None:
        runtime_report, blockers, _runtime_manifest = self.accepted_runtime_report_from_simulation()
        decisions = self.decisions()
        for item in decisions["required_before_public_header"]:
            item["status"] = "resolved"
        decision_record = {
            "provided": True,
            "accepted_for_contract_review": True,
            "record_valid": True,
            "hash_bound_to_current_source_artifacts": True,
            "contract_review_only": True,
            "reviewed_hash_current_contract_review_only": True,
            "approved_runtime_evidence_binding": runtime_report["approved_runtime_evidence_binding"],
            "resolved_decision_keys": checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
            "blockers": [],
        }

        report = checker.build_report(
            decisions,
            runtime_report,
            decision_record,
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertEqual(blockers, [])
        self.assertTrue(report["ready"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["identity_contract_gate_complete"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["remaining_unresolved_decision_keys"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS,
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_build_report_rejects_decision_record_header_gate_shortcut_claims(self) -> None:
        runtime_report, blockers, _runtime_manifest = self.accepted_runtime_report_from_simulation()
        decisions = self.decisions()
        for item in decisions["required_before_public_header"]:
            item["status"] = "resolved"
        decision_record = {
            "provided": True,
            "accepted_for_contract_review": True,
            "record_valid": True,
            "hash_bound_to_current_source_artifacts": True,
            "contract_review_only": True,
            "reviewed_hash_current_contract_review_only": True,
            "approved_runtime_evidence_binding": runtime_report["approved_runtime_evidence_binding"],
            "resolved_decision_keys": checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
            "next_blocker": "public_header_gate_missing",
            "identity_contract_gate_complete": True,
            "accepted_for_public_header_gate_review": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "complete_sdk_claim_progress_contribution": "1/12",
            "p0_dependency_chain_claim_progress_contribution": "1/4",
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "blockers": [],
        }

        report = checker.build_report(
            decisions,
            runtime_report,
            decision_record,
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "identity_public_contract_decision_record_header_gate_shortcut_not_counting",
            report["blockers"],
        )
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "identity_public_contract_decision_record_header_gate_shortcut_not_counting"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.identity_public_contract_decision_record.next_blocker", paths)
        self.assertIn("$.identity_public_contract_decision_record.resolved_decision_keys", paths)
        self.assertIn("$.identity_public_contract_decision_record.identity_contract_gate_complete", paths)
        self.assertIn("$.identity_public_contract_decision_record.accepted_for_public_header_gate_review", paths)
        self.assertIn("$.identity_public_contract_decision_record.public_sdk_ready", paths)
        self.assertIn("$.identity_public_contract_decision_record.runtime_ready", paths)
        self.assertIn("$.identity_public_contract_decision_record.complete_sdk_claim_progress_contribution", paths)
        self.assertIn("$.identity_public_contract_decision_record.p0_dependency_chain_claim_progress_contribution", paths)
        self.assertIn("$.identity_public_contract_decision_record.public_header_symbols_now", paths)
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        path = report["post_runtime_public_header_fail_closed_path"]
        self.assertEqual(report["post_approved_runtime_evidence_gate"]["public_header_fail_closed_path"], path)
        self.assertEqual(report["public_header_gate_missing"]["fail_closed_path"], path)
        self.assertTrue(path["active_after_strict_approved_runtime_evidence"])
        self.assertFalse(path["active_after_accepted_reviewed_identity_contract"])
        self.assertEqual(path["status"], "blocked_until_reviewed_identity_public_contract_decision_record")
        self.assertEqual(path["next_fail_closed_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            path["next_required_artifact"],
            checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(path["required_sequence"][1]["status"], "missing_or_not_accepted")
        self.assertEqual(path["required_sequence"][2]["status"], "blocked_until_reviewed_identity_contract")
        self.assertFalse(path["shortcut_aliases_allowed"])
        self.assertFalse(path["public_header_allowed"])
        self.assertFalse(path["public_sdk_ready"])
        self.assertEqual(path["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["identity_contract_gate_complete"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_accepts_identity_public_contract_decision_record_but_keeps_identity_gate_active(self) -> None:
        runtime = approved_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(
                record_path,
                self.reviewed_identity_contract_record_bound_to_runtime(runtime),
            )
            result = self.run_checker(
                self.decisions(),
                runtime,
                "--identity-public-contract-decision-record",
                str(record_path),
            )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        record = report["identity_public_contract_decision_record"]
        self.assertTrue(record["provided"])
        self.assertTrue(record["accepted_for_contract_review"])
        self.assertTrue(record["record_valid"])
        self.assertTrue(record["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record["reviewed_template_only"])
        self.assertTrue(record["strict_accepted_decision_record"])
        self.assertTrue(record["accepted_post_runtime_decision_record"])
        self.assertTrue(record["accepted_as_next_identity_contract_input"])
        self.assertFalse(record["public_header_readiness_from_decision_record"])
        self.assertFalse(record["identity_contract_gate_complete"])
        self.assertEqual(record["resolved_decision_keys"], checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS)
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            self.assertNotIn(key, report["post_approved_runtime_evidence_gate"]["remaining_unresolved_decision_keys"])
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertTrue(
            report["post_approved_runtime_evidence_gate"][
                "accepted_decision_record_as_next_identity_contract_input"
            ]
        )
        self.assertFalse(
            report["post_approved_runtime_evidence_gate"][
                "accepted_decision_record_opens_public_header_gate"
            ]
        )
        self.assertFalse(
            report["post_approved_runtime_evidence_gate"][
                "public_header_readiness_from_decision_record"
            ]
        )
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["next_required_artifact"]["status"],
            "accepted_for_contract_review",
        )
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["identity_contract_gate_complete"])
        path = report["post_runtime_public_header_fail_closed_path"]
        self.assertEqual(report["post_approved_runtime_evidence_gate"]["public_header_fail_closed_path"], path)
        self.assertEqual(report["public_header_gate_missing"]["fail_closed_path"], path)
        self.assertTrue(path["active_after_strict_approved_runtime_evidence"])
        self.assertTrue(path["active_after_accepted_reviewed_identity_contract"])
        self.assertEqual(path["status"], "candidate_public_header_gate_review_available_fail_closed")
        self.assertEqual(path["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(path["next_fail_closed_blocker"], "public_header_gate_missing")
        self.assertEqual(
            path["next_required_artifact"],
            checker.REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(path["required_sequence"][0]["status"], "accepted")
        self.assertEqual(path["required_sequence"][1]["status"], "accepted_for_contract_review")
        self.assertEqual(path["required_sequence"][2]["status"], "candidate_only_fail_closed_next_artifact")
        self.assertFalse(path["shortcut_aliases_allowed"])
        self.assertFalse(path["accepted_decision_record_opens_public_header_gate"])
        self.assertFalse(path["public_header_readiness_from_decision_record"])
        self.assertFalse(path["public_header_allowed"])
        self.assertFalse(path["public_sdk_ready"])
        self.assertFalse(path["runtime_ready"])
        self.assertEqual(path["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(path["p0_dependency_chain_claim_progress_contribution"], 0)
        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertTrue(post_runtime_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(post_runtime_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_gap["next_blocker"], "identity_public_contract_gate_missing")
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
        checklist = report["post_runtime_identity_contract_checklist"]
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["post_runtime_identity_contract_checklist"],
            checklist,
        )
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["post_runtime_identity_contract_checklist"],
            checklist,
        )
        self.assertTrue(checklist["active"])
        self.assertEqual(checklist["runtime_evidence_status"], "accepted")
        self.assertEqual(checklist["reviewed_identity_contract_status"], "accepted_for_contract_review")
        self.assertEqual(checklist["missing_review_decision_keys"], [])
        self.assertEqual(
            checklist["immediate_next_artifact"],
            checker.REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(
            checklist["after_reviewed_contract_fail_closed_blocker"],
            "public_header_gate_missing",
        )
        self.assert_post_runtime_identity_contract_checklist_closed(checklist)
        header_gate = report["public_header_gate_missing"]
        self.assertFalse(header_gate["active"])
        self.assertEqual(
            header_gate["next_required_artifact"],
            checker.REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertIn(
            "approved runtime principal lifecycle evidence bundle",
            header_gate["cannot_unlock_without"],
        )
        self.assertFalse(header_gate["public_header_allowed"])
        self.assertFalse(header_gate["public_sdk_ready"])
        self.assertFalse(header_gate["v1_completion_evidence"])
        for key in (
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
            "live_ops_authorized",
            "server_operations_authorized",
            "workspace_writes_authorized",
            "runtime_capture_authorized",
            "reads_live_logs",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(record[key])
        self.assertEqual(record["public_header_symbols_now"], [])
        self.assertEqual(record["public_capability_bits_now"], [])
        self.assertEqual(record["public_callback_abi_now"], [])
        self.assertEqual(report["approved_runtime_evidence"]["source_provenance_policy"]["findings"], [])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        runtime_input = contract_gate_inputs["runtime.lifecycle_evidence"]
        self.assertEqual(runtime_input["review_inputs_resolved"], ["runtime.lifecycle_evidence"])
        self.assertEqual(runtime_input["review_inputs_missing"], [])
        self.assertFalse(runtime_input["promotion_blocker_resolved"])
        self.assertFalse(runtime_input["promotion_ready"])
        self.assertFalse(runtime_input["public_sdk_ready"])
        self.assertEqual(
            contract_gate_inputs["privacy.identifier_redaction"]["review_inputs_resolved"],
            ["privacy.identifier_redaction"],
        )
        self.assertEqual(contract_gate_inputs["privacy.identifier_redaction"]["review_inputs_missing"], [])
        self.assertEqual(
            contract_gate_inputs["lifetime.generation_scope_invalidation"]["review_inputs_resolved"],
            ["lifetime.generation_scope_invalidation.candidate_policy"],
        )
        self.assertIn(
            "lifetime.reconnect_duplicate_stale_policy",
            contract_gate_inputs["lifetime.generation_scope_invalidation"]["remaining_promotion_inputs"],
        )
        self.assertEqual(report["blockers"], [])
        self.assertIn(checker.NON_PROMOTIONAL_EVIDENCE_DENIAL, report["non_claims"])
        self.assertTrue(report["identifier_redaction_evidence"]["provided"])
        self.assertTrue(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertTrue(report["principal_invalidation_policy"]["provided"])
        self.assertTrue(report["principal_invalidation_policy"]["accepted_for_policy_review"])
        self.assertEqual(
            report["principal_invalidation_policy"]["resolved_input"],
            "lifetime.generation_scope_invalidation.candidate_policy",
        )
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
        abi_preflight = report["public_abi_preflight_candidate"]
        self.assertTrue(abi_preflight["provided"])
        self.assertEqual(abi_preflight["status"], "blocked")
        self.assertTrue(abi_preflight["candidate_only"])
        self.assertTrue(abi_preflight["accepted_for_candidate_review"])
        self.assertFalse(abi_preflight["accepted_for_contract_review"])
        self.assertFalse(abi_preflight["promotion_ready"])
        self.assertFalse(abi_preflight["public_sdk_ready"])
        self.assertFalse(abi_preflight["runtime_ready"])
        self.assertFalse(abi_preflight["public_header_allowed"])
        self.assertFalse(abi_preflight["public_abi_ready"])
        self.assertFalse(abi_preflight["v1_completion_evidence"])
        self.assertIn("abi.public_pod_contract", abi_preflight["does_not_resolve"])
        self.assertIn("sdk.consumer", abi_preflight["does_not_resolve"])
        self.assertIn("lifecycle.owner_cleanup", abi_preflight["does_not_resolve"])
        self.assertEqual(abi_preflight["public_header_symbols_now"], [])
        self.assertEqual(abi_preflight["public_capability_bits_now"], [])
        self.assertEqual(abi_preflight["public_callback_abi_now"], [])
        self.assertIn("nonzero plugin_owner_token required", abi_preflight["required_owner_token_lifecycle"])
        self.assertIn("missing capability fails closed", abi_preflight["required_capability_policy"])
        self.assertEqual(abi_preflight["sdk_consumer_contract"]["source"], "derived_compatibility_stub")
        self.assertFalse(abi_preflight["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(abi_preflight["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertIn(
            "consumer treats callback payload storage as callback-local",
            abi_preflight["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn("lifecycle.owner_cleanup", abi_preflight["sdk_consumer_contract"]["does_not_resolve"])
        owner_contract = report["owner_token_sdk_consumer_contract"]
        self.assertEqual(owner_contract["source"], "owner_token_sdk_consumer_contract")
        self.assertFalse(owner_contract["ready"])
        self.assertFalse(owner_contract["accepted_for_contract_review"])
        self.assertFalse(owner_contract["public_sdk_ready"])
        self.assertFalse(owner_contract["runtime_ready"])

    def test_accepts_reviewed_contract_review_metadata_without_readiness(self) -> None:
        runtime = approved_manifest()
        record = self.reviewed_identity_contract_record_bound_to_runtime(runtime)
        record["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
        }

        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                runtime,
                "--identity-public-contract-decision-record",
                str(record_path),
            )

        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        record_report = report["identity_public_contract_decision_record"]
        self.assertTrue(record_report["accepted_for_contract_review"])
        self.assertTrue(record_report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(record_report["identity_contract_gate_complete"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_gate_missing"]["active"])
        for key in (
            "promotion_ready",
            "public_header_allowed",
            "public_abi_ready",
            "public_sdk_ready",
            "runtime_ready",
            "v1_completion_evidence",
            "resource_handle_supported",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(record_report[key])

    def test_rejects_identity_public_contract_record_transition_integrity_claims(self) -> None:
        record = reviewed_identity_contract_record()
        record["review_metadata"] = {
            "next_blocker": "public_header_gate_missing",
            "v1_dependency_chain_position": 2,
            "proposed_header_symbols": [
                "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
                "RegisterPlayerIdentityEventWithOwnerTokenHandle",
            ],
        }
        record["notes"] = ["public ABI carries principal handles before ResourceHandle promotion"]

        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        record_report = report["identity_public_contract_decision_record"]
        for blocker in (
            "blocker_id_mismatch",
            "dependency_chain_position_claimed_before_promotion",
            "stale_proposed_header_symbols_claimed",
            "public_text_or_source_overclaim",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, record_report["blockers"])
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["identity_contract_gate_complete"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_hash_unbound_identity_public_contract_decision_record(self) -> None:
        record = reviewed_identity_contract_record()
        record["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertEqual(
            report["identity_public_contract_decision_record"]["source_artifact_freshness"]["status"],
            "stale_or_mismatched",
        )
        self.assertFalse(
            report["identity_public_contract_decision_record"]["source_artifact_freshness"]["current"]
        )
        self.assertIn("source_artifact_hash_mismatch", report["identity_public_contract_decision_record"]["blockers"])
        for key in (
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
            "resource_handle_ready",
            "resource_handle_supported",
            "v1_completion_evidence",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_rejects_identity_public_contract_decision_record_missing_source_hash(self) -> None:
        record = reviewed_identity_contract_record()
        record["source_artifacts"]["owner_token_sdk_consumer_contract"].pop("sha256")
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_gate_missing"]["active"])
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(record_report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertIn("source_artifact_sha256_missing", record_report["blockers"])
        mismatch = record_report["source_artifact_freshness"]["mismatches"][0]
        self.assertEqual(mismatch["reason"], "source_artifact_sha256_missing")
        self.assertEqual(mismatch["label"], "owner_token_sdk_consumer_contract")
        self.assertIsNone(mismatch["observed_sha256"])
        self.assertFalse(mismatch["counts_toward_public_sdk"])
        self.assertFalse(mismatch["counts_toward_p0_dependency_chain_claim"])
        for key in (
            "promotion_ready",
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "resource_handle_ready",
            "resource_handle_supported",
            "v1_completion_evidence",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_rejects_non_contract_review_only_identity_public_contract_decision_record(self) -> None:
        record = reviewed_identity_contract_record()
        record["decisions"][
            "identity_public_contract.reviewed_owner_token_lifecycle"
        ]["scope"] = "public_header_review"
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(record_path, record)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_decision_record_not_accepted", report["blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_gate_missing"]["active"])
        record_report = report["identity_public_contract_decision_record"]
        self.assertTrue(record_report["provided"])
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["contract_review_only"])
        self.assertTrue(record_report["hash_bound_to_current_source_artifacts"])
        self.assertFalse(record_report["reviewed_hash_current_contract_review_only"])
        self.assertIn("decision_entry_scope_mismatch", record_report["blockers"])
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
                self.assertFalse(record_report[key])

    def test_rejects_missing_owner_token_sdk_consumer_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            missing_contract = Path(tempdir) / "missing-owner-token-sdk-consumer.json"

            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--owner-token-sdk-consumer-contract",
                str(missing_contract),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner_token_sdk_consumer_contract_missing", report["blockers"])
        owner_contract = report["owner_token_sdk_consumer_contract"]
        self.assertFalse(owner_contract["provided"])
        self.assertEqual(owner_contract["source"], "missing_owner_token_sdk_consumer_contract")
        self.assertFalse(owner_contract["accepted_for_candidate_review"])
        self.assertFalse(owner_contract["public_sdk_ready"])
        self.assertEqual(owner_contract["blockers"], ["owner_token_sdk_consumer_contract_missing"])

    def test_rejects_passive_or_diagnostic_runtime_sources_at_public_intake(self) -> None:
        runtime = approved_manifest()
        passive_snapshot = (
            "/tmp/obelisk-passive-evidence-snapshots/"
            "passive-manual-20260604T085119Z-arkserver+arkserver2-3215640/manifest.json"
        )
        runtime["source_summary"]["evidence"]["kind"] = "passive-diagnostic-snapshot"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = passive_snapshot
        runtime["operational_window"]["copied_log"]["path"] = passive_snapshot

        result = self.run_checker(self.decisions(), runtime, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_non_promotional_sources_claimed", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
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

        result = self.run_checker(self.decisions(), runtime, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_non_promotional_sources_claimed", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn(checker.REQUIRED_RESOLVED_INPUT, report["resolved_inputs"])
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
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["source_summary"]["evidence"]["kind"] = "observer-log-copy"
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
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
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-runtime-simulation"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/synthetic-fixture-runtime.log"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/simulated-runtime-fixture.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
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
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-copied-runtime-partial"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/copied-runtime-observer-log.partial"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/runtime-lifecycle-evidence-truncated.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        self.assertIn("partial", policy["forbidden_source_tokens"])
        self.assertIn("truncated", policy["forbidden_source_tokens"])
        self.assertIn("partial_copied_runtime_evidence", policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("partial", tokens)
        self.assertIn("truncated", tokens)
        self.assertIn("partial_copied_runtime_evidence", tokens)

    def test_rejects_post_runtime_bridge_or_shutdown_worker_artifacts_at_public_intake(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-post-runtime-bridge-build-report"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/post-runtime-bridge-build-report.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/shutdown-worker-artifact.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        self.assertIn("post_runtime_bridge", policy["forbidden_source_tokens"])
        self.assertIn("shutdown_worker", policy["forbidden_source_tokens"])
        self.assertIn(
            "post_runtime_bridge_or_shutdown_worker_artifact",
            policy["forbidden_source_aliases"],
        )
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("post_runtime_bridge_or_shutdown_worker_artifact", tokens)

    def test_rejects_runtime_live_status_material_at_public_intake(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "installed-runtime-status"
        runtime["output_artifact_identity"]["evidence_pack_id"] = "broadcast-rcon-ok"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/installed-runtime-broadcast-rcon-ok.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/runtime-installed-rcon-ok.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        self.assertIn("installed_runtime", policy["forbidden_source_tokens"])
        self.assertIn("broadcast", policy["forbidden_source_tokens"])
        self.assertIn("rcon", policy["forbidden_source_tokens"])
        self.assertIn("runtime_live_status_material", policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertTrue({"installed_runtime", "installed-runtime"} & tokens)
        self.assertIn("broadcast", tokens)
        self.assertIn("rcon", tokens)
        self.assertIn("runtime_live_status_material", tokens)

    def test_rejects_planning_public_api_ready_source_aliases(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

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
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
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

    def test_rejects_extended_monitor_notice_closure_executor_manifest_source_shortcuts(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "approved-manifest-reference"
        runtime["output_artifact_identity"]["evidence_pack_id"] = (
            "identity-public-contract-accepted-alias"
        )
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/extended-passive-monitor-snapshot.log"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "beta-notice-closure-report-executor-report-public-contract-ready-alias.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        for alias in (
            "approved_manifest_reference",
            "beta_notice_material",
            "closure_or_executor_report",
            "generic_public_contract_shortcut_alias",
            "passive_extended_monitor_material",
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
            "executor",
            "generic_public_contract_shortcut_alias",
            "passive",
            "passive_extended_monitor_material",
            "ready-alias",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

    def test_rejects_post_reboot_confirmed_beta_and_copied_log_only_source_shortcuts(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "confirmed-beta-notice-json"
        runtime["output_artifact_identity"]["evidence_pack_id"] = "post-reboot-passive-monitor-context"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/post-reboot-passive-monitor-context.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/copied-log-only-artifact.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        for alias in (
            "confirmed_beta_notice_material",
            "copied_log_only_artifact",
            "post_reboot_passive_monitor_context",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        for token in (
            "confirmed-beta-notice",
            "confirmed_beta_notice_material",
            "copied-log-only",
            "copied_log_only_artifact",
            "post-reboot",
            "post_reboot_passive_monitor_context",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

    def test_rejects_next_action_plan_and_status_artifact_runtime_source_shortcuts(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = (
            "approved-runtime-evidence-shortcut-status-report"
        )
        runtime["output_artifact_identity"]["evidence_pack_id"] = "next-action-plan"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/plan_player_principal_lifecycle_next_actions.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/"
            "route-status-artifact-runtime-evidence-shortcut.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        for alias in (
            "next_action_plan",
            "runtime_evidence_shortcut",
            "status_artifact",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        for token in (
            "next-action-plan",
            "next_actions",
            "next_action_plan",
            "runtime-evidence-shortcut",
            "runtime_evidence_shortcut",
            "route-status",
            "status-artifact",
            "status-report",
            "status_artifact",
        ):
            with self.subTest(token=token):
                self.assertIn(token, tokens)

    def test_rejects_source_overclaim_zero_runtime_source_shortcut(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["artifact_kind"] = "source-overclaim-total-flag-count-zero"
        runtime["output_artifact_identity"]["evidence_pack_id"] = "source-overclaim-zero-diagnostics"
        runtime["source_summary"]["evidence"]["kind"] = "runtime-observer-log"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/source-overclaim-total-flag-count-zero.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "/tmp/obelisk-safe-offline-workspace/source_overclaim_total_flag_count_0.log"
        )
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        policy = report["source_provenance_policy"]
        self.assertIn("source_overclaim_zero_diagnostic", policy["forbidden_source_aliases"])
        tokens = {token for item in policy["findings"] for token in item["tokens"]}
        self.assertIn("source-overclaim", tokens)
        self.assertIn("source-overclaim-total-flag-count", tokens)
        self.assertIn("source_overclaim_zero_diagnostic", tokens)

    def test_rejects_source_overclaim_zero_manifest_alias_as_contract_review_substitute(self) -> None:
        decisions = self.decisions()
        decisions["source_overclaim_total_flag_count"] = 0
        decisions["source_overclaim_summary"] = {
            "total_flag_count": 0,
            "status": "ready",
        }
        decisions["notes"] = [
            "source_overclaim_total_flag_count=0 unlocks public identity contract readiness",
        ]

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("source_overclaim_zero_marker", terms_by_path["$.source_overclaim_total_flag_count"])
        self.assertIn("source_overclaim_zero_marker", terms_by_path["$.source_overclaim_summary.total_flag_count"])
        self.assertIn("source_overclaim_zero_status_alias", terms_by_path["$.source_overclaim_summary.status"])
        self.assertIn("non_counting_artifact_public_readiness_or_p0", terms_by_path["$.notes[0]"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_next_action_status_and_p0_resolved_input_shortcuts(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def shortcut_resolved_inputs_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["resolved_inputs"] = [
                "runtime.lifecycle_evidence",
                "next_action_plan.runtime",
                "route_status.runtime",
                "status_report.identity",
                "sdk_p0_progress.runtime",
            ]
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(
                    checker.approved_evidence,
                    "build_report",
                    side_effect=shortcut_resolved_inputs_report,
                ),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_non_promotional_inputs_claimed", reasons)
        self.assertIn("approved_runtime_evidence_resolved_inputs_unexpected", reasons)
        detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_non_promotional_inputs_claimed"
        )
        self.assertEqual(
            detail["forbidden"],
            [
                "next_action_plan.runtime",
                "route_status.runtime",
                "sdk_p0_progress.runtime",
                "status_report.identity",
            ],
        )

    def test_accepts_identifier_redaction_evidence_for_contract_review_only(self) -> None:
        result = self.run_checker(
            self.decisions(),
            approved_manifest(),
            redaction=redaction_manifest(),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "identity_public_contract_decision_record_missing_or_not_accepted",
            report["blockers"],
        )
        self.assertEqual(
            report["resolved_inputs"],
            [
                "runtime.lifecycle_evidence",
                "privacy.identifier_redaction",
                "lifetime.generation_scope_invalidation.candidate_policy",
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
                checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
                "separation.no_commands_permissions_persistence",
            ],
        )
        self.assertEqual(report["remaining_contract_review_inputs"], [])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertIn("privacy.identifier_redaction", report["remaining_blockers"])
        self.assertNotIn("runtime.lifecycle_evidence", report["remaining_blockers"])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        self.assertEqual(
            contract_gate_inputs["privacy.identifier_redaction"]["review_inputs_resolved"],
            ["privacy.identifier_redaction"],
        )
        self.assertFalse(contract_gate_inputs["privacy.identifier_redaction"]["promotion_blocker_resolved"])
        self.assertFalse(contract_gate_inputs["privacy.identifier_redaction"]["public_header_allowed"])
        self.assertTrue(report["identifier_redaction_evidence"]["provided"])
        self.assertTrue(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["identifier_redaction_evidence"]["promotion_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_sdk_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["runtime_ready"])
        self.assertFalse(report["identifier_redaction_evidence"]["public_header_allowed"])

    def test_all_current_contract_review_inputs_still_leave_promotion_blockers_closed(self) -> None:
        result = self.run_checker(
            self.decisions(),
            approved_manifest(),
            redaction=redaction_manifest(),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "contract_review_input_only")
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "identity_public_contract_decision_record_missing_or_not_accepted",
            report["blockers"],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_contract_allowed"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")

        self.assertIn("abi.public_pod_contract", report["remaining_blockers"])
        self.assertIn("lifecycle.owner_cleanup", report["remaining_blockers"])
        self.assertIn("separation.downstream_surfaces", report["remaining_blockers"])
        self.assertIn(checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertIn(checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT, report["resolved_inputs"])
        self.assertEqual(report["remaining_contract_review_inputs"], [])

        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        abi_gate = contract_gate_inputs["abi.public_pod_contract"]
        self.assertEqual(
            abi_gate["review_inputs_resolved"],
            [
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
            ],
        )
        self.assertEqual(abi_gate["review_inputs_missing"], [])
        self.assertIn("abi.layout", abi_gate["remaining_promotion_inputs"])
        self.assertIn("sdk.consumer", abi_gate["remaining_promotion_inputs"])
        self.assertFalse(abi_gate["promotion_blocker_resolved"])
        self.assertFalse(abi_gate["promotion_ready"])
        self.assertFalse(abi_gate["public_sdk_ready"])
        self.assertFalse(abi_gate["public_header_allowed"])

        owner_gate = contract_gate_inputs["lifecycle.owner_cleanup"]
        self.assertEqual(
            owner_gate["review_inputs_resolved"],
            [checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT],
        )
        self.assertEqual(owner_gate["review_inputs_missing"], [])
        self.assertIn("lifecycle.owner_cleanup.runtime_tests", owner_gate["remaining_promotion_inputs"])
        self.assertFalse(owner_gate["promotion_blocker_resolved"])
        self.assertFalse(owner_gate["promotion_ready"])
        self.assertFalse(owner_gate["public_sdk_ready"])
        self.assertFalse(owner_gate["public_header_allowed"])

        owner_contract = report["owner_token_sdk_consumer_contract"]
        self.assertFalse(owner_contract["ready"])
        self.assertTrue(owner_contract["accepted_for_candidate_review"])
        self.assertFalse(owner_contract["accepted_for_contract_review"])
        self.assertFalse(owner_contract["promotion_ready"])
        self.assertFalse(owner_contract["public_sdk_ready"])
        self.assertFalse(owner_contract["runtime_ready"])
        self.assertFalse(owner_contract["public_header_allowed"])

    def test_repo_identifier_redaction_evidence_is_non_routing_contract_review_input(self) -> None:
        blockers: list[dict] = []
        report = checker.identifier_redaction_report(REPO_REDACTION_EVIDENCE, blockers)

        self.assertEqual(blockers, [])
        self.assertTrue(report["provided"])
        self.assertTrue(report["ready"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["resolved_inputs"], ["privacy.identifier_redaction"])
        self.assertEqual(report["remaining_blockers"], [])

    def test_rejects_identifier_redaction_evidence_that_overclaims_or_fails_validation(self) -> None:
        redaction = redaction_manifest()
        redaction["public_sdk_ready"] = True
        redaction["redactionEvidencePromotesIdentity"] = True
        redaction["sample_logs"][0]["message"] = "free form sanitized log"

        result = self.run_checker(self.decisions(), approved_manifest(), redaction=redaction, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_not_accepted", report["blockers"])
        self.assertIn("identifier_redaction_evidence_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("identifier_redaction_evidence_public_contract_overclaim", report["blockers"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIn("runtime.lifecycle_evidence", report["resolved_inputs"])
        self.assertNotIn("privacy.identifier_redaction", report["resolved_inputs"])

    def test_rejects_stale_source_bound_planning_manifest_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            planning_dir = root / "planning"
            subprocess.run(
                [
                    "cp",
                    "-a",
                    str(REPO_ROOT / "docs" / "research" / "player-identity-planning-sources"),
                    str(planning_dir),
                ],
                check=True,
            )
            stale_path = planning_dir / "players-identity-principal-invalidation-policy.json"
            stale = json.loads(stale_path.read_text(encoding="utf-8"))
            stale["negative_consumer_rules"] = []
            stale_path.write_text(json.dumps(stale), encoding="utf-8")

            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--planning-sources-dir",
                str(planning_dir),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_bound_planning_manifest_verification_not_accepted", report["blockers"])
        source_verification = report["source_bound_planning_manifest_verification"]
        self.assertFalse(source_verification["accepted_for_contract_review"])
        self.assertFalse(source_verification["promotion_ready"])
        self.assertFalse(source_verification["public_sdk_ready"])
        self.assertFalse(source_verification["runtime_ready"])
        self.assertFalse(source_verification["public_abi_ready"])
        self.assertFalse(source_verification["v1_completion_ready"])

    def test_rejects_stale_first_evidence_source_binding_for_contract_readiness(self) -> None:
        blockers: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            planning_dir = root / "planning"
            subprocess.run(
                ["cp", "-a", str(self.planning_sources_dir), str(planning_dir)],
                check=True,
            )
            stale_path = planning_dir / checker.planning_source_manifests.FIRST_EVIDENCE_OUTPUT_NAME
            stale = json.loads(stale_path.read_text(encoding="utf-8"))
            stale["artifact_status"] = "stale_test_artifact"
            stale_path.write_text(json.dumps(stale), encoding="utf-8")

            source_verification = checker.planning_source_verification_report(
                checker.planning_source_manifests.build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
                planning_dir,
                blockers,
            )

        runtime_report = {
            **self.accepted_runtime_contract_review_report(),
            "accepted_for_contract_review": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
        }
        report = checker.build_report(
            self.decisions(),
            runtime_report,
            checker.identity_public_contract_decision_record_report(None, blockers),
            {"provided": False, "accepted_for_contract_review": False},
            {
                "schema": checker.PRIVATE_CANDIDATE_SCHEMA,
                "artifact_status": "candidate_only",
                "visibility": "private_planning_contract",
                "candidate_only": True,
            },
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
            planning_source_report=source_verification,
        )

        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIn("runtime.lifecycle_evidence", report["resolved_inputs"])
        self.assertNotIn("planning.source_bound_committed_manifests", report["resolved_inputs"])
        self.assertIn("source_bound_planning_manifest_verification_not_accepted", report["blockers"])
        source_verification = report["source_bound_planning_manifest_verification"]
        self.assertFalse(source_verification["accepted_for_contract_review"])
        self.assertIsNone(source_verification["resolved_input"])
        source_blockers = [
            blocker for blocker in source_verification["blockers"] if isinstance(blocker, dict)
        ]
        blocker_reasons = {blocker["reason"] for blocker in source_blockers}
        self.assertIn("stale_or_mismatched_planning_manifest", blocker_reasons)
        self.assertIn("planning_manifest_build_report_output_hash_mismatch", blocker_reasons)
        stale_blockers = [
            blocker for blocker in source_blockers if blocker["reason"] == "stale_or_mismatched_planning_manifest"
        ]
        self.assertEqual(
            {Path(blocker["path"]).name for blocker in stale_blockers},
            {checker.planning_source_manifests.FIRST_EVIDENCE_OUTPUT_NAME},
        )
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

    def test_rejects_public_abi_preflight_sdk_consumer_overclaim(self) -> None:
        preflight = self.public_abi_preflight_candidate()
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

        result = self.run_checker(
            self.decisions(),
            approved_manifest(),
            public_abi_preflight_candidate=preflight,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn(
            "sdk_consumer_contract_public_sdk_ready_not_false",
            report["public_abi_preflight_candidate"]["blockers"],
        )
        self.assertIn(
            "sdk_consumer_contract_required_behavior_missing",
            report["public_abi_preflight_candidate"]["blockers"],
        )

    def test_rejects_identifier_redaction_evidence_route_unlock_claim(self) -> None:
        redaction = redaction_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "identifier-redaction.json"
            path.write_text(json.dumps(redaction), encoding="utf-8")
            blockers: list[dict] = []
            with mock.patch.object(
                checker.identifier_redaction,
                "build_report",
                return_value={
                    "ready": True,
                    "accepted_for_contract_review": True,
                    "resolved_inputs": ["privacy.identifier_redaction"],
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "public_header_allowed": False,
                    "remaining_blockers": [],
                    "next_blocker": "identity_public_contract_gate_missing",
                },
            ):
                report = checker.identifier_redaction_report(path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "identifier_redaction_evidence_route_unlock_claimed",
            [blocker["reason"] for blocker in blockers],
        )

    def test_accepts_candidate_only_pod_abi_shape(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]

        self.assertEqual(candidate["status"], "proposal_only_not_public")
        self.assertTrue(candidate["candidate_only"])
        self.assertFalse(candidate["public_header_allowed"])
        self.assertFalse(candidate["promotion_ready"])
        self.assertFalse(candidate["public_sdk_ready"])
        self.assertFalse(candidate["runtime_ready"])
        self.assertEqual(
            set(candidate["candidate_event_payload_fields_or_equivalent"]),
            {
                "abi_version",
                "struct_size",
                "event_kind",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "principal_state_flags",
                "invalidation_reason_flags",
                "event_sequence",
                "server_process_epoch",
                "reserved",
            },
        )
        self.assertEqual(
            set(candidate["candidate_event_kind_mask"]),
            {"session_start", "session_start_rejected", "session_end"},
        )
        self.assertIn("process_local", candidate["candidate_scope_flags"])
        self.assertIn("stale_generation", candidate["candidate_state_flags"])
        self.assertIn("server_restart", candidate["candidate_invalidation_reason_flags"])
        self.assertIn("no_lookup", candidate["candidate_contract_flags"])
        self.assertIn(
            "event_sequence is assigned once per copied source lifecycle event",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "event_sequence is not a per-plugin delivery counter",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "server_process_epoch invalidates process-local principal handles after restart",
            candidate["server_process_epoch_policy"],
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            report["blockers"],
            ["identity_public_contract_decision_record_missing_or_not_accepted"],
        )
        self.assertEqual(
            report["private_candidate_contract"]["path"],
            "docs/research/2026-06-01-player-identity-private-candidate-contract.json",
        )
        self.assertEqual(report["private_candidate_contract"]["artifact_status"], "candidate_only")
        self.assertEqual(report["private_candidate_contract"]["visibility"], "private_planning_contract")
        self.assertTrue(report["private_candidate_contract"]["candidate_only"])
        self.assertFalse(report["private_candidate_contract"]["public_header_allowed"])

    def test_rejects_private_candidate_contract_path_rerouted_to_public_docs(self) -> None:
        decisions = self.decisions()
        decisions["private_candidate_contract"] = "docs/player_identity_private_candidate_contract.json"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_contract_path_mismatch", report["blockers"])

    def test_rejects_private_candidate_contract_missing_stable_principal_non_claim(self) -> None:
        decisions = self.decisions()
        private_contract = json.loads(
            (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                encoding="utf-8"
            )
        )
        private_contract["non_claims"].remove("This artifact does not claim stable principal identity.")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_path = root / "private-candidate.json"
            private_path.write_text(json.dumps(private_contract), encoding="utf-8")
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--private-candidate-contract",
                    str(private_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_non_claims_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "private_candidate_non_claims_missing"
        )
        self.assertIn("This artifact does not claim stable principal identity.", detail["missing"])

    def test_rejects_private_candidate_contract_missing_stale_handle_fail_closed_rule(self) -> None:
        decisions = self.decisions()
        private_contract = json.loads(
            (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                encoding="utf-8"
            )
        )
        private_contract["candidate_stale_handle_fail_closed_semantics"].remove(
            "stale handles never resolve to a different player"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            private_path = root / "private-candidate.json"
            private_path.write_text(json.dumps(private_contract), encoding="utf-8")
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--private-candidate-contract",
                    str(private_path),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_stale_handle_fail_closed_semantics_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "private_candidate_stale_handle_fail_closed_semantics_missing"
        )
        self.assertIn("stale handles never resolve to a different player", detail["missing"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_blocks_promote_public_and_runtime_modes(self) -> None:
        for flag, blocker in (
            ("--promote", "promote_blocked_until_player_identity_public_contract_promotion"),
            ("--public-readiness", "public_readiness_blocked_until_player_identity_public_contract_promotion"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_player_identity_public_contract_promotion"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(self.decisions(), approved_manifest(), flag, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertIn(
                    "identity_public_contract_decision_record_missing_or_not_accepted",
                    report["blockers"],
                )
                self.assertFalse(report["accepted_for_contract_review"])
                self.assertFalse(report["promotion_ready"])
                self.assertFalse(report["public_sdk_ready"])
                self.assertFalse(report["runtime_ready"])

    def test_rejects_public_abi_openings(self) -> None:
        decisions = self.decisions()
        decisions["public_header_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterPlayerIdentity"]
        decisions["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
        decisions["public_callback_abi_now"] = ["ObeliskPlayerPrincipalCallback"]
        decisions["contract_gate_inputs"][0]["promotion_ready"] = True
        decisions["contract_gate_inputs"][1]["public_header_allowed"] = True
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
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("public_callback_abi_now_not_empty", report["blockers"])
        self.assertIn("contract_gate_input_flag_not_false", report["blockers"])
        self.assertIn("alias_guardrail_not_false", report["blockers"])
        alias_labels = {
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "alias_guardrail_not_false"
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

    def test_rejects_public_text_or_source_artifact_overclaims_in_decisions(self) -> None:
        decisions = self.decisions()
        decisions["source_artifacts"] = {"public_sdk_alias": "docs/research/public-sdk-ready.json"}
        decisions["review_notes"] = [
            "public header symbols are available",
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY is available",
            "callback ABI exposed for RegisterPlayerIdentity",
            "public ABI carries principal handles before ResourceHandle promotion",
            "public ABI must not expose principal handles before ResourceHandle promotion",
            "installed SDK package shape is ready",
            "support tier is ready",
            "Plugin Hub publication is published",
        ]

        result = self.run_checker(decisions, approved_manifest(), check=False)
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
        self.assertIn("$.review_notes[5]", paths)
        self.assertIn("$.review_notes[6]", paths)
        self.assertIn("$.review_notes[7]", paths)
        self.assertNotIn("$.review_notes[4]", paths)
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("package_shape_readiness", terms)
        self.assertIn("support_tier_ready", terms)
        self.assertIn("plugin_hub_ready", terms)
        self.assertIn("public_abi_identity_handle_before_resource_handle", terms)

    def test_rejects_decision_gate_rerouted_to_public_readiness(self) -> None:
        decisions = self.decisions()
        gate = decisions["decision_gate"]
        gate["id"] = "public_readiness"
        gate["status"] = "ready"
        gate["current_decision"] = "approved runtime evidence accepted; next blocker is public readiness"
        gate["allowed_now"].append("public readiness")
        gate["forbidden_now"].remove("player lookup API")

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        for blocker in (
            "decision_gate_id_mismatch",
            "decision_gate_status_mismatch",
            "decision_gate_current_decision_mismatch",
            "decision_gate_allowed_now_mismatch",
            "decision_gate_forbidden_now_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_unmanifested_player_identity_tokens_in_public_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text(
                "\n".join(
                    [
                        "#pragma once",
                        "#define OBELISK_API_CAPABILITY_PLAYER_IDENTITY (1ull << 12)",
                        "typedef struct ObeliskPlayerPrincipalEvent {",
                        "    uint64_t principal_handle;",
                        "} ObeliskPlayerPrincipalEvent;",
                        "typedef uint64_t ObeliskPlayerId;",
                        "typedef uint64_t ObeliskPlayerHandle;",
                        "uint64_t (*RegisterPlayerIdentityEventWithOwnerTokenHandle)(uint64_t ownerToken);",
                        "#define OBELISK_API_CAPABILITY_PLAYER_SESSION (1ull << 13)",
                        "typedef struct ObeliskPlayerSession { uint64_t x; } ObeliskPlayerSession;",
                        "typedef void (*ObeliskPlayerLifecycleCallback)(void* userData);",
                        "uint64_t (*RegisterPlayerLoginWithOwnerToken)(uint64_t ownerToken);",
                        "uint64_t (*RegisterPlayerLogoutWithOwnerToken)(uint64_t ownerToken);",
                        "typedef struct ObeliskPlayerConnectEvent { uint64_t x; } ObeliskPlayerConnectEvent;",
                        "typedef struct ObeliskPlayerDisconnectEvent { uint64_t x; } ObeliskPlayerDisconnectEvent;",
                        "typedef struct ObeliskPlayerJoinEvent { uint64_t x; } ObeliskPlayerJoinEvent;",
                        "typedef struct ObeliskPlayerLeaveEvent { uint64_t x; } ObeliskPlayerLeaveEvent;",
                        "typedef uint64_t ObeliskResourceHandle;",
                        "bool (*LookupPlayerPrincipal)(uint64_t principalHandle, void* out);",
                        "typedef uint64_t ObeliskResourceOwnerHandle;",
                        "bool (*CheckPlayerPermission)(uint64_t principalHandle);",
                        "bool (*ResolveTribeId)(uint64_t playerHandle);",
                        "#define OBELISK_API_CAPABILITY_COMMANDS (1ull << 14)",
                        "typedef void (*ObeliskCommandReplyCallback)(void* userData);",
                        "bool (*SendChatReply)(uint64_t principalHandle);",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(header),
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_header_contains_unmanifested_player_identity_tokens", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "public_header_contains_unmanifested_player_identity_tokens"
        )
        detected = {item["token"] for item in detail["detected_tokens"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", detected)
        self.assertIn("ObeliskPlayerPrincipalEvent", detected)
        self.assertIn("principal_handle", detected)
        self.assertIn("ObeliskPlayerId", detected)
        self.assertIn("ObeliskPlayerHandle", detected)
        self.assertIn("RegisterPlayerIdentityEventWithOwnerTokenHandle", detected)
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_SESSION", detected)
        self.assertIn("ObeliskPlayerSession", detected)
        self.assertIn("ObeliskPlayerLifecycleCallback", detected)
        self.assertIn("RegisterPlayerLoginWithOwnerToken", detected)
        self.assertIn("RegisterPlayerLogoutWithOwnerToken", detected)
        self.assertIn("ObeliskPlayerConnectEvent", detected)
        self.assertIn("ObeliskPlayerDisconnectEvent", detected)
        self.assertIn("ObeliskPlayerJoinEvent", detected)
        self.assertIn("ObeliskPlayerLeaveEvent", detected)
        self.assertIn("ObeliskResourceHandle", detected)
        self.assertIn("LookupPlayerPrincipal", detected)
        self.assertIn("ObeliskResourceOwnerHandle", detected)
        self.assertIn("CheckPlayerPermission", detected)
        self.assertIn("ResolveTribeId", detected)
        self.assertIn("OBELISK_API_CAPABILITY_COMMANDS", detected)
        self.assertIn("ObeliskCommandReplyCallback", detected)
        self.assertIn("SendChatReply", detected)

    def test_public_header_scan_ignores_comments_strings_and_existing_no_identity_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text(
                "\n".join(
                    [
                        "#pragma once",
                        "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY (1ull << 1)",
                        "#define OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP (1ull << 2)",
                        "// ObeliskPlayerPrincipalEvent is not a public symbol here.",
                        "static const char* label = \"RegisterPlayerIdentityEventWithOwnerTokenHandle\";",
                    ]
                ),
                encoding="utf-8",
            )

            detected = checker.public_header_identity_tokens(header)

        self.assertEqual(detected, [])

    def test_rejects_fake_public_header_path_even_without_identity_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            header = Path(tmp) / "ObeliskApi.h"
            header.write_text("/* no player identity ABI */\n", encoding="utf-8")
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(header),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_path_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_public_header_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "ObeliskApi.h"
            target.write_text("/* no player identity ABI */\n", encoding="utf-8")
            link = root / "ObeliskApi-link.h"
            link.symlink_to(target)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--public-header",
                str(link),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_path_rejected", report["blockers"])

    def test_rejects_decisions_symlink_component_with_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            runtime_path = root / "approved-runtime.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            link = root / "decisions-link.json"
            link.symlink_to(decisions_path)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(link),
                    "--approved-runtime-evidence",
                    str(runtime_path),
                    "--json",
                ],
                check=False,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_private_candidate_contract_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "private-candidate.json"
            target.write_text(
                (REPO_ROOT / "docs/research/2026-06-01-player-identity-private-candidate-contract.json").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            link = root / "private-candidate-link.json"
            link.symlink_to(target)
            result = self.run_checker(
                self.decisions(),
                approved_manifest(),
                "--private-candidate-contract",
                str(link),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private_candidate_contract_path_rejected", report["blockers"])

    def test_rejects_candidate_public_promotion_or_runtime_claims(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["status"] = "public"
        candidate["candidate_only"] = False
        candidate["public_header_allowed"] = True
        candidate["promotion_ready"] = True
        candidate["runtime_ready"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_status_not_proposal_only", report["blockers"])
        self.assertIn("candidate_only_not_true", report["blockers"])
        self.assertIn("candidate_public_header_allowed_not_false", report["blockers"])
        self.assertIn("candidate_public_header_allowed_claim_not_false", report["blockers"])
        self.assertIn("candidate_promotion_ready_claim_not_false", report["blockers"])
        self.assertIn("candidate_runtime_ready_claim_not_false", report["blockers"])

    def test_rejects_candidate_missing_required_payload_fields(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_payload_fields_or_equivalent"].remove("reserved")
        candidate["candidate_event_payload_fields_or_equivalent"].remove("principal_generation")

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_event_payload_fields_missing", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_event_payload_fields_missing"
        )
        self.assertEqual(detail["missing"], ["principal_generation", "reserved"])

    def test_rejects_candidate_lookup_persistence_scope_and_private_identity_fields(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_payload_fields_or_equivalent"].extend(
            [
                "lookup_handle",
                "resolve_player_name",
                "get_platform_id",
                "raw_UE_player_pointer",
                "private_identity_token",
                "tribe_id",
                "IP_address",
                "FName_index",
                "GObjects_index",
                "ResourceHandle",
                "persistent_principal_handle",
                "cluster_stable_principal_handle",
                "cross_process_principal_handle",
                "cross_map_principal_handle",
            ]
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_event_payload_fields_forbidden_identity_or_lookup", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_event_payload_fields_forbidden_identity_or_lookup"
        )
        for token in (
            "lookup",
            "resolve",
            "get",
            "raw_ue",
            "private_identity",
            "platform",
            "player_name",
            "tribe",
            "ip",
            "fname_gobjects",
            "resource_handle",
            "persistent",
            "cluster",
            "cross_process",
            "cross_map",
        ):
            with self.subTest(token=token):
                self.assertIn(token, detail["forbidden"])

    def test_rejects_candidate_process_local_non_persistent_requirements_removed(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["required_payload_properties"].remove(
            "principal handles are process-local and non-persistent"
        )
        candidate["candidate_registration_shape_or_equivalent"].remove(
            "registration handles are process-local and non-persistent"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_required_payload_properties_missing", report["blockers"])
        self.assertIn("candidate_owner_token_cleanup_requirements_missing", report["blockers"])
        payload_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_required_payload_properties_missing"
        )
        self.assertIn(
            "principal handles are process-local and non-persistent",
            payload_detail["missing"],
        )
        registration_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_owner_token_cleanup_requirements_missing"
        )
        self.assertIn(
            "registration handles are process-local and non-persistent",
            registration_detail["missing"],
        )

    def test_rejects_candidate_owner_token_cleanup_requirements_removed(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_registration_shape_or_equivalent"] = [
            "event-kind mask required",
            "opaque uint64 registration handle returned on success",
            "callback payload storage is valid only for the callback",
        ]
        candidate["candidate_capability_policy"] = [
            "capability must be captured in the init-time API table",
            "later marker or env changes cannot widen a plugin's captured capability",
        ]

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("candidate_owner_token_cleanup_requirements_missing", report["blockers"])
        self.assertIn("candidate_fail_closed_policy_missing", report["blockers"])
        registration_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_owner_token_cleanup_requirements_missing"
        )
        self.assertIn("nonzero plugin_owner_token required", registration_detail["missing"])
        self.assertIn("plugin init failure removes registrations", registration_detail["missing"])
        self.assertIn("plugin unload removes registrations and drains in-flight callbacks", registration_detail["missing"])
        policy_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "candidate_fail_closed_policy_missing"
        )
        self.assertIn("missing or zero owner token fails closed", policy_detail["missing"])

    def test_rejects_candidate_masks_flags_and_sequence_policy_weakened(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_kind_mask"].remove("session_end")
        candidate["candidate_scope_flags"].remove("process_local")
        candidate["candidate_state_flags"].remove("stale_generation")
        candidate["candidate_invalidation_reason_flags"].remove("server_restart")
        candidate["candidate_contract_flags"].remove("no_lookup")
        candidate["sequence_policy"].remove(
            "event_sequence is not a per-plugin delivery counter"
        )
        candidate["server_process_epoch_policy"].remove(
            "server_process_epoch invalidates process-local principal handles after restart"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "candidate_event_kind_mask_missing",
            "candidate_scope_flags_missing",
            "candidate_state_flags_missing",
            "candidate_invalidation_reason_flags_missing",
            "candidate_contract_flags_missing",
            "candidate_sequence_policy_missing",
            "candidate_server_process_epoch_policy_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_missing_runtime_evidence_or_decision_intake(self) -> None:
        decisions = self.decisions()
        decisions.pop("approved_runtime_evidence_intake")
        runtime = approved_manifest()
        runtime["public_sdk_ready"] = True
        result = self.run_checker(decisions, runtime, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_intake_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_not_accepted", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["active"])
        for key in checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(report["post_approved_runtime_evidence_gate"][key])
        self.assertNotIn("runtime.lifecycle_evidence", report["resolved_inputs"])

    def test_rejects_weakened_approved_runtime_intake_source_policy(self) -> None:
        decisions = self.decisions()
        decisions["approved_runtime_evidence_intake"]["source_provenance_policy"]["accepted_source_kind"] = (
            "passive-snapshot"
        )
        decisions["approved_runtime_evidence_intake"]["source_provenance_policy"][
            "required_output_artifact_hash"
        ] = "diagnostic.report.sha256"
        decisions["approved_runtime_evidence_intake"]["public_api_ready"] = True
        decisions["approved_runtime_evidence_intake"]["lookup_ready"] = True
        decisions["approved_runtime_evidence_intake"]["v1_completion_evidence"] = True
        decisions["approved_runtime_evidence_intake"]["non_claim"] = (
            "A valid approved runtime evidence manifest can resolve only the runtime lifecycle evidence input "
            "for contract review; it does not promote public player identity or open ABI."
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "approved_runtime_evidence_intake_source_provenance_policy_mismatch",
            report["blockers"],
        )
        self.assertIn("approved_runtime_evidence_intake_public_api_ready_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_intake_lookup_ready_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_intake_v1_completion_evidence_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_intake_non_claim_mismatch", report["blockers"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_missing_or_weakened_identifier_redaction_intake(self) -> None:
        decisions = self.decisions()
        decisions["identifier_redaction_evidence_intake"]["public_sdk_ready"] = True
        decisions["identifier_redaction_evidence_intake"]["required_checker"] = "scripts/other.py"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_intake_checker_mismatch", report["blockers"])
        self.assertIn("identifier_redaction_evidence_intake_public_sdk_ready_not_false", report["blockers"])

        decisions = self.decisions()
        decisions.pop("identifier_redaction_evidence_intake")
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_intake_missing", report["blockers"])

    def test_rejects_missing_or_weakened_public_abi_preflight_intake(self) -> None:
        decisions = self.decisions()
        decisions["public_abi_preflight_candidate_intake"]["required_checker"] = "scripts/other.py"
        decisions["public_abi_preflight_candidate_intake"]["default_manifest"] = "docs/research/other.json"
        decisions["public_abi_preflight_candidate_intake"]["non_claim"] = "promotes public ABI"
        decisions["public_abi_preflight_candidate_intake"]["public_abi_ready"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_intake_checker_mismatch", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_intake_default_manifest_mismatch", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_intake_non_claim_mismatch", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_intake_public_abi_ready_not_false", report["blockers"])

        decisions = self.decisions()
        decisions.pop("public_abi_preflight_candidate_intake")
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_intake_missing", report["blockers"])

    def test_rejects_missing_or_weakened_owner_token_sdk_consumer_contract_intake(self) -> None:
        decisions = self.decisions()
        decisions["owner_token_sdk_consumer_contract_intake"]["id"] = "owner_token_contract"
        decisions["owner_token_sdk_consumer_contract_intake"]["status"] = "accepted"
        decisions["owner_token_sdk_consumer_contract_intake"]["resolved_input"] = "lifecycle.owner_cleanup"
        decisions["owner_token_sdk_consumer_contract_intake"]["required_checker"] = "scripts/other.py"
        decisions["owner_token_sdk_consumer_contract_intake"]["default_manifest"] = "docs/research/other.json"
        decisions["owner_token_sdk_consumer_contract_intake"]["non_claim"] = "promotes owner cleanup"
        decisions["owner_token_sdk_consumer_contract_intake"]["lifecycle_owner_cleanup_ready"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner_token_sdk_consumer_contract_intake_id_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_status_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_resolved_input_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_checker_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_default_manifest_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_non_claim_mismatch", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_contract_intake_lifecycle_owner_cleanup_ready_not_false", report["blockers"])

        decisions = self.decisions()
        decisions.pop("owner_token_sdk_consumer_contract_intake")
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owner_token_sdk_consumer_contract_intake_missing", report["blockers"])

    def test_rejects_public_abi_preflight_candidate_overclaim(self) -> None:
        preflight = self.public_abi_preflight_candidate()
        preflight["public_abi_ready"] = True
        preflight["v1_completion_evidence"] = True
        preflight["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]

        result = self.run_checker(
            self.decisions(),
            approved_manifest(),
            public_abi_preflight_candidate=preflight,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["public_abi_preflight_candidate"]["blockers"])
        self.assertIn("v1_completion_evidence_not_false", report["public_abi_preflight_candidate"]["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["public_abi_preflight_candidate"]["blockers"])

    def test_sanitizes_public_abi_preflight_helper_nested_overclaims(self) -> None:
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
                "notes": "public header symbols are available",
            },
            "review_notes": [
                "runtime is ready",
                "helper-derived readiness is satisfied",
                {"claim": "public_header_symbols_now", "values": ["PrivateOnlySymbol"]},
            ],
            "blockers": [],
        }

        blockers: list[dict] = []
        with mock.patch.object(checker.public_abi_preflight_candidate, "build_report", return_value=overclaim):
            report = checker.public_abi_preflight_candidate_report(PUBLIC_ABI_PREFLIGHT_CANDIDATE, HEADER, blockers)

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("nested_readiness_flag_not_false", reasons)
        self.assertIn("nested_public_header_symbols_now_not_empty", reasons)
        self.assertIn("nested_public_symbol_list_not_empty", reasons)
        self.assertIn("nested_capability_bits_not_empty", reasons)
        self.assertIn("nested_callback_abi_not_empty", reasons)
        self.assertIn("nested_public_text_overclaim", reasons)
        self.assertIn("nested_readiness_split_claim_overclaim", reasons)
        self.assertFalse(report["accepted_for_candidate_review"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_api_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertFalse(report["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertFalse(report["sdk_consumer_contract"]["public_api_ready"])
        self.assertEqual(report["sdk_consumer_contract"]["public_header_symbols_now"], [])
        self.assertEqual(report["sdk_consumer_contract"]["public_symbol_list"], [])

    def test_sanitizes_owner_token_sdk_consumer_helper_nested_overclaims(self) -> None:
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
            "v1_completion_ready": True,
            "v1_completion_evidence": True,
            "public_sdk_v1_completion_claim": True,
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
                "notes": "command router is ready",
            },
            "blockers": [],
        }

        blockers: list[dict] = []
        with mock.patch.object(owner_token_checker, "build_report", return_value=overclaim):
            report = checker.owner_token_sdk_consumer_contract_report(
                OWNER_TOKEN_SDK_CONSUMER_CONTRACT,
                PUBLIC_ABI_PREFLIGHT_CANDIDATE,
                HEADER,
                blockers,
                {"sdk_consumer_contract": {}, "required_owner_token_lifecycle": []},
            )

        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("nested_readiness_flag_not_false", reasons)
        self.assertIn("nested_public_header_symbols_now_not_empty", reasons)
        self.assertIn("nested_public_symbol_list_not_empty", reasons)
        self.assertIn("nested_public_text_overclaim", reasons)
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

    def test_approved_runtime_report_must_route_to_identity_public_contract_gate(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def wrong_next_blocker(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["next_blocker"] = "runtime_ready"
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=wrong_next_blocker),
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_next_blocker_mismatch"],
        )

    def test_approved_runtime_report_must_be_ready(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def not_ready_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["ready"] = False
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=not_ready_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertIn(
            "approved_runtime_evidence_report_ready_not_true",
            [blocker["reason"] for blocker in blockers],
        )
        self.assertFalse(report["accepted_for_contract_review"])

    def test_approved_runtime_report_must_not_overclaim_public_readiness(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["public_sdk_ready"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_public_sdk_ready_not_false"],
        )

    def test_approved_runtime_report_rejects_nested_alias_overclaims(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["nestedClaims"] = {
                "publicSdkReady": True,
                "publicApiReady": True,
                "publicPrincipalReady": True,
                "public-header-allowed": "ready",
                "publicHeaderSymbolsNow": ["ObeliskPlayerPrincipalEvent"],
                "publicApiSymbolsNow": ["RegisterPlayerIdentityApi"],
                "publicSymbolList": ["RegisterPlayerIdentityApi"],
                "runtimeReadyAlias": "ready",
                "helperDerivedReadiness": "satisfied",
                "downstream": {
                    "v1CompletionReady": True,
                    "principalLookupReady": True,
                    "runtimePrincipalReady": True,
                    "redactionEvidencePromotesIdentity": True,
                },
                "public": {
                    "sdk": {"ready": True},
                    "header": {"symbols_now": ["ObeliskPlayerPrincipalEvent"]},
                    "capability": {"bits_now": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]},
                },
            }
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertIn(
            "approved_runtime_evidence_report_public_readiness_overclaim",
            [blocker["reason"] for blocker in blockers],
        )
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.nestedClaims.publicSdkReady", paths)
        self.assertIn("$.nestedClaims.publicApiReady", paths)
        self.assertIn("$.nestedClaims.publicPrincipalReady", paths)
        self.assertIn("$.nestedClaims.public-header-allowed", paths)
        self.assertIn("$.nestedClaims.publicHeaderSymbolsNow", paths)
        self.assertIn("$.nestedClaims.publicApiSymbolsNow", paths)
        self.assertIn("$.nestedClaims.publicSymbolList", paths)
        self.assertIn("$.nestedClaims.runtimeReadyAlias", paths)
        self.assertIn("$.nestedClaims.helperDerivedReadiness", paths)
        self.assertIn("$.nestedClaims.downstream.v1CompletionReady", paths)
        self.assertIn("$.nestedClaims.downstream.principalLookupReady", paths)
        self.assertIn("$.nestedClaims.downstream.runtimePrincipalReady", paths)
        self.assertIn("$.nestedClaims.downstream.redactionEvidencePromotesIdentity", paths)
        self.assertIn("$.nestedClaims.public.sdk.ready", paths)
        self.assertIn("$.nestedClaims.public.header.symbols_now", paths)
        self.assertIn("$.nestedClaims.public.capability.bits_now", paths)
        self.assertFalse(report["accepted_for_contract_review"])

    def test_approved_runtime_report_rejects_prose_key_and_split_overclaims(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["reviewNotes"] = [
                "public header symbols are available",
                "public API readiness is satisfied",
                "runtime is ready",
                "opaque principal is promoted",
                "principal generation is ready",
                "privacy and redaction are ready",
                "platform account ids are public",
                "player lookup is available",
                "ResourceHandle is ready",
                "permissions/admin is unlocked",
                "commands/replies are ready",
                "v1 SDK completion is ready",
                {"claim": "public_header_symbols_now", "values": ["PrivateOnlySymbol"]},
                {"name": "ObeliskPlayerPrincipalEvent", "value": True},
            ]
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_report_public_readiness_overclaim",
            [blocker["reason"] for blocker in blockers],
        )
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        terms = {claim["term"] for claim in overclaims}
        for term in (
            "public_header_ready",
            "readiness_noun_overclaim",
            "runtime_ready",
            "opaque_principal_promoted",
            "principal_generation_ready",
            "privacy_redaction_ready",
            "real_identifier_exposed",
            "lookup_ready",
            "resource_handle_supported",
            "permissions_admin_ready",
            "commands_ready",
            "v1_completion_ready",
            "split_readiness_alias",
            "public_player_header_symbol",
        ):
            with self.subTest(term=term):
                self.assertIn(term, terms)

    def test_approved_runtime_report_rejects_readiness_aliases_and_gate_skip(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["nestedReadinessClaims"] = {
                "publicSdkReadiness": True,
                "publicApiReadiness": True,
                "publicAbiReadiness": True,
                "publicHeaderReadiness": "satisfied",
                "runtimeReadiness": "available",
                "runtimeReadyAlias": "ready",
                "publicSymbolList": ["RegisterPlayerIdentityApi"],
                "helperDerivedReadiness": "satisfied",
                "current_blocker": "public_readiness",
            }
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.nestedReadinessClaims.publicSdkReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.publicApiReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.publicAbiReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.publicHeaderReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.runtimeReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.runtimeReadyAlias", paths)
        self.assertIn("$.nestedReadinessClaims.publicSymbolList", paths)
        self.assertIn("$.nestedReadinessClaims.helperDerivedReadiness", paths)
        self.assertIn("$.nestedReadinessClaims.current_blocker", paths)

    def test_approved_runtime_report_rejects_status_report_shape_and_raw_acceptance_boolean(self) -> None:
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
                "resolved_inputs": [checker.REQUIRED_RESOLVED_INPUT],
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "accepted_for_contract_review": True,
                "promotion_ready": False,
                "public_contract_allowed": False,
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

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=status_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        reasons = {blocker["reason"] for blocker in blockers}
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn("approved_runtime_evidence_report_schema_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_mode_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_ready_scope_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_observed_runtime_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_cases_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_consumer_boundary_assertions_mismatch", reasons)
        self.assertIn("approved_runtime_evidence_report_false_only_key_not_false", reasons)

    def test_approved_runtime_payload_rejects_nested_public_readiness_overclaims(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["promotion_gate"]["nested_claims"] = [
            {"claim": "publicAbiReadiness", "readiness": "satisfied"},
            {"summary": "SDK consumer tests are passing"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.promotion_gate.nested_claims[0]", paths)
        self.assertIn("$.promotion_gate.nested_claims[1].summary", paths)

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

    def test_approved_runtime_payload_rejects_stable_claim_and_downstream_unlocks(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

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
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
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
            return self.accepted_runtime_contract_review_report()

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
        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
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

    def test_approved_runtime_report_rejects_p0_resource_handle_and_mutation_flags(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report.update(
                {
                    "public_api_ready": True,
                    "lookup_ready": True,
                    "permissions_admin_ready": True,
                    "command_response_ready": True,
                    "complete_sdk_ready": True,
                    "p0_progress_ready": True,
                    "sdk_p0_progress_ready": True,
                    "resource_handle_supported": True,
                    "mutation_allowed": True,
                    "live_ops_authorized": True,
                }
            )
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        reasons = {blocker["reason"] for blocker in blockers}
        for key in (
            "public_api_ready",
            "lookup_ready",
            "permissions_admin_ready",
            "command_response_ready",
            "complete_sdk_ready",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
            "resource_handle_supported",
            "mutation_allowed",
            "live_ops_authorized",
        ):
            with self.subTest(key=key):
                self.assertIn(f"approved_runtime_evidence_{key}_not_false", reasons)

    def test_approved_runtime_report_must_not_overclaim_public_header_allowed(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["public_header_allowed"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=overclaiming_report),
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            ["approved_runtime_evidence_public_header_allowed_not_false"],
        )

    def test_approved_runtime_report_rejects_recursive_public_contract_overclaim(self) -> None:
        original_build_report = checker.approved_evidence.build_report

        def overclaiming_report(payload, validation, *, check_mode: str):
            report = original_build_report(payload, validation, check_mode=check_mode)
            report["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
            report["contractReviewed"] = True
            report["identityContractReady"] = True
            report["principalHandleAbiReady"] = True
            report["identityHeaderAllowed"] = True
            report["claims"] = {
                "public_contract_ready": True,
                "summary": "public player identity ready",
                "downstream": "identity unlocks permissions now",
            }
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", return_value=mock.Mock(blockers=[])),
                mock.patch.object(
                    checker.approved_evidence,
                    "build_report",
                    side_effect=overclaiming_report,
                ),
            ):
                runtime_report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(runtime_report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_report_public_readiness_overclaim",
            [blocker["reason"] for blocker in blockers],
        )
        overclaims = next(
            blocker["overclaims"]
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        paths = {claim["path"] for claim in overclaims}
        self.assertIn("$.contractReviewed", paths)
        self.assertIn("$.identityContractReady", paths)
        self.assertIn("$.principalHandleAbiReady", paths)
        self.assertIn("$.identityHeaderAllowed", paths)

        report = checker.build_report(
            self.decisions(),
            runtime_report,
            {"accepted_for_contract_review": False, "provided": False},
            {"accepted_for_contract_review": False},
            {},
            {"readable": True, "detected_player_identity_tokens": []},
            blockers,
            "consume",
        )

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn("runtime.lifecycle_evidence", report["resolved_inputs"])

    def test_approved_runtime_report_accumulates_route_and_public_overclaims(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def mismatched_and_overclaiming_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["next_blocker"] = "runtime_ready"
            report["promotion_ready"] = True
            report["runtime_ready"] = True
            report["public_header_allowed"] = True
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(
                    checker.approved_evidence,
                    "build_report",
                    side_effect=mismatched_and_overclaiming_report,
                ),
            ):
                checker.approved_runtime_report(runtime_path, blockers)

        self.assertEqual(
            [blocker["reason"] for blocker in blockers],
            [
                "approved_runtime_evidence_next_blocker_mismatch",
                "approved_runtime_evidence_promotion_ready_not_false",
                "approved_runtime_evidence_runtime_ready_not_false",
                "approved_runtime_evidence_public_header_allowed_not_false",
            ],
        )

    def test_approved_runtime_report_rejects_non_promotional_resolved_inputs(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def non_promotional_inputs_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["resolved_inputs"] = [
                    "runtime.lifecycle_evidence",
                    "approved_manifest.reference",
                    "beta_notice.runtime",
                    "closure_report.evidence",
                    "diagnostic.gap_report",
                    "executor_report.evidence",
                    "identity_public_contract.accepted_alias",
                    "identity_public_contract.complete_alias",
                    "identity_public_contract.ready_alias",
                    "operational.window_manifest",
                    "operator_approval_receipt",
                    "passive.extended_monitor_snapshot",
                    "passive.chat_route",
                    "player_identity.promotion_certificate.stale",
                    "preflight_readiness",
                    "scoped_release_statement.permissions_admin",
                    "live_ops_sidecar",
                    "abi.public_pod_contract.public_abi_preflight_candidate",
                ]
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(
                    checker.approved_evidence,
                    "validate_manifest",
                    side_effect=accepted_validation,
                ),
                mock.patch.object(
                    checker.approved_evidence,
                    "build_report",
                    side_effect=non_promotional_inputs_report,
                ),
            ):
                checker.approved_runtime_report(runtime_path, blockers)

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
                "abi.public_pod_contract.public_abi_preflight_candidate",
                "approved_manifest.reference",
                "beta_notice.runtime",
                "closure_report.evidence",
                "diagnostic.gap_report",
                "executor_report.evidence",
                "identity_public_contract.accepted_alias",
                "identity_public_contract.complete_alias",
                "identity_public_contract.ready_alias",
                "live_ops_sidecar",
                "operational.window_manifest",
                "operator_approval_receipt",
                "passive.chat_route",
                "passive.extended_monitor_snapshot",
                "player_identity.promotion_certificate.stale",
                "preflight_readiness",
                "scoped_release_statement.permissions_admin",
            ],
        )

    def test_approved_runtime_payload_rejects_start_end_only_source_artifacts(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def accepted_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return self.accepted_runtime_contract_review_report()

        runtime = approved_manifest()
        runtime["output_artifact_identity"]["evidence_pack_id"] = "principal-start-end-runtime-evidence"
        runtime["source_summary"]["evidence"]["sources"][0]["path"] = (
            "docs/research/runtime-lifecycle-start-end-evidence.json"
        )
        runtime["operational_window"]["copied_log"]["path"] = (
            "docs/research/start-end-only-runtime-evidence.log"
        )

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=accepted_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            [blocker["reason"] for blocker in blockers],
        )
        detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_non_promotional_sources_claimed"
        )
        values = {source["value"] for source in detail["sources"]}
        self.assertIn("principal-start-end-runtime-evidence", values)
        self.assertIn("docs/research/runtime-lifecycle-start-end-evidence.json", values)
        self.assertIn("docs/research/start-end-only-runtime-evidence.log", values)
        tokens = {token for source in detail["sources"] for token in source["tokens"]}
        self.assertIn("principal_start_end_only_runtime_evidence", tokens)

    def test_approved_runtime_report_rejects_source_ready_start_end_provenance_alias(self) -> None:
        def accepted_validation(_payload, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            return mock.Mock(blockers=[])

        def source_ready_report(_payload, _validation, *, check_mode: str):
            self.assertEqual(check_mode, "consume")
            report = self.accepted_runtime_contract_review_report()
            report["source_ready"] = True
            report["source_provenance"] = {
                "source_provenance": "principal_start_end_runtime_evidence",
                "source_ready": True,
            }
            return report

        with tempfile.TemporaryDirectory() as tmp:
            runtime_path = Path(tmp) / "approved-runtime.json"
            runtime_path.write_text(json.dumps(approved_manifest()), encoding="utf-8")
            blockers: list[dict] = []
            with (
                mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
                mock.patch.object(checker.approved_evidence, "validate_manifest", side_effect=accepted_validation),
                mock.patch.object(checker.approved_evidence, "build_report", side_effect=source_ready_report),
            ):
                report = checker.approved_runtime_report(runtime_path, blockers)

        self.assertFalse(report["accepted_for_contract_review"])
        reasons = [blocker["reason"] for blocker in blockers]
        self.assertIn("approved_runtime_evidence_report_public_readiness_overclaim", reasons)
        self.assertIn("approved_runtime_evidence_source_ready_not_false", reasons)
        overclaim_detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_report_public_readiness_overclaim"
        )
        terms = {claim["term"] for claim in overclaim_detail["overclaims"]}
        self.assertIn("readiness_alias", terms)
        self.assertIn("non_promotional_provenance_status_alias", terms)

    def test_missing_runtime_evidence_path_reports_json_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = root / "decisions.json"
            missing_runtime_path = root / "missing-approved-runtime.json"
            decisions_path.write_text(json.dumps(self.decisions()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--decisions",
                    str(decisions_path),
                    "--approved-runtime-evidence",
                    str(missing_runtime_path),
                    "--json",
                ],
                check=False,
                env=approved_runtime_safe_test_env(),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_unreadable", report["blockers"])
        self.assertIn("approved_runtime_evidence_missing_or_not_ready", report["blockers"])
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_missing")
        self.assertNotIn("runtime.lifecycle_evidence", report["resolved_inputs"])
        contract_gate_inputs = {item["id"]: item for item in report["contract_gate_inputs"]}
        abi_gate = contract_gate_inputs["abi.public_pod_contract"]
        self.assertEqual(abi_gate["review_inputs_resolved"], [])
        self.assertEqual(
            abi_gate["review_inputs_missing"],
            [
                "abi.public_pod_contract.private_layout_candidate",
                checker.REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
            ],
        )
        self.assertEqual(abi_gate["review_inputs_non_counting_until"], checker.REQUIRED_RESOLVED_INPUT)
        owner_gate = contract_gate_inputs["lifecycle.owner_cleanup"]
        self.assertEqual(owner_gate["review_inputs_resolved"], [])
        self.assertEqual(
            owner_gate["review_inputs_missing"],
            [checker.REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT],
        )
        self.assertEqual(owner_gate["review_inputs_non_counting_until"], checker.REQUIRED_RESOLVED_INPUT)
        lifetime_gate = contract_gate_inputs["lifetime.generation_scope_invalidation"]
        self.assertEqual(lifetime_gate["review_inputs_resolved"], [])
        self.assertEqual(lifetime_gate["review_inputs_non_counting_until"], checker.REQUIRED_RESOLVED_INPUT)

    def test_rejects_forbidden_contract_terms_removed(self) -> None:
        decisions = self.decisions()
        decisions["forbidden_public_contract"] = ["lookup"]
        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])

    def test_rejects_runtime_evidence_sufficiency_or_nonclaim_weakened(self) -> None:
        decisions = self.decisions()
        decisions["approved_runtime_evidence_not_sufficient"]["why"].remove(
            "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["why"].remove(
            "runtime evidence can show logout observations; it does not prove the private logout correlation contract required before public identity promotion"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["minimum_additional_gates"].remove(
            "cross-instance/process-local scope decision resolved"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["minimum_additional_gates"].remove(
            "private logout correlation contract resolved"
        )
        decisions["non_claims"].remove(
            "This manifest does not make approved runtime evidence sufficient by itself."
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_not_sufficient_why_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_not_sufficient_minimum_gates_missing", report["blockers"])
        self.assertIn("non_claims_missing_required", report["blockers"])
        why_detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "approved_runtime_evidence_not_sufficient_why_missing"
        )
        self.assertIn(
            "runtime evidence can show logout observations; it does not prove the private logout correlation contract required before public identity promotion",
            why_detail["missing"],
        )
        gates_detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "approved_runtime_evidence_not_sufficient_minimum_gates_missing"
        )
        self.assertIn("private logout correlation contract resolved", gates_detail["missing"])

    def test_rejects_post_runtime_evidence_gate_weakened(self) -> None:
        decisions = self.decisions()
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
        gate["public_sdk_ready"] = True
        gate["public_contract_allowed"] = True
        gate["public_readiness"] = True
        gate["public_header_allowed"] = True
        gate["public_api_ready"] = True
        gate["lookup_ready"] = True
        gate["permissions_ready"] = True
        gate["permissions_admin_unlocked"] = True
        gate["commands_ready"] = True
        gate["command_response_unlocked"] = True
        gate["public_header_gate_unlocked"] = True
        gate["public_identity_ready"] = True
        gate["complete_sdk_ready"] = True
        gate["sdk_p0_progress_ready"] = True
        gate["stable_ready"] = True
        gate["stable_claim_allowed"] = True
        gate["stable_claim_ready"] = True
        gate["stable_sdk_ready"] = True
        gate["plugin_hub_ready"] = True
        gate["plugin_hub_publication_ready"] = True
        gate["publication_ready"] = True
        gate["publication_authorized"] = True
        gate["resource_handle_ready"] = True
        gate["resource_handle_supported"] = True
        gate["runtime_readiness"] = True
        gate["runtime_capture_authorized"] = True
        gate["non_claim"] = "public SDK readiness is satisfied"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "post_approved_runtime_evidence_gate_id_mismatch",
            "post_approved_runtime_evidence_gate_status_mismatch",
            "post_approved_runtime_evidence_gate_active_input_mismatch",
            "post_approved_runtime_evidence_gate_reported_current_blocker_mismatch",
            "post_approved_runtime_evidence_gate_next_blocker_mismatch",
            "post_approved_runtime_evidence_gate_required_decision_keys_mismatch",
            "post_approved_runtime_evidence_gate_auditable_inputs_mismatch",
            "post_approved_runtime_evidence_gate_next_required_artifact_mismatch",
            "post_approved_runtime_evidence_gate_public_sdk_ready_not_false",
            "post_approved_runtime_evidence_gate_public_contract_allowed_not_false",
            "post_approved_runtime_evidence_gate_public_readiness_not_false",
            "post_approved_runtime_evidence_gate_public_header_allowed_not_false",
            "post_approved_runtime_evidence_gate_public_api_ready_not_false",
            "post_approved_runtime_evidence_gate_lookup_ready_not_false",
            "post_approved_runtime_evidence_gate_permissions_ready_not_false",
            "post_approved_runtime_evidence_gate_permissions_admin_unlocked_not_false",
            "post_approved_runtime_evidence_gate_commands_ready_not_false",
            "post_approved_runtime_evidence_gate_command_response_unlocked_not_false",
            "post_approved_runtime_evidence_gate_public_header_gate_unlocked_not_false",
            "post_approved_runtime_evidence_gate_public_identity_ready_not_false",
            "post_approved_runtime_evidence_gate_complete_sdk_ready_not_false",
            "post_approved_runtime_evidence_gate_sdk_p0_progress_ready_not_false",
            "post_approved_runtime_evidence_gate_stable_ready_not_false",
            "post_approved_runtime_evidence_gate_stable_claim_allowed_not_false",
            "post_approved_runtime_evidence_gate_stable_claim_ready_not_false",
            "post_approved_runtime_evidence_gate_stable_sdk_ready_not_false",
            "post_approved_runtime_evidence_gate_plugin_hub_ready_not_false",
            "post_approved_runtime_evidence_gate_plugin_hub_publication_ready_not_false",
            "post_approved_runtime_evidence_gate_publication_ready_not_false",
            "post_approved_runtime_evidence_gate_publication_authorized_not_false",
            "post_approved_runtime_evidence_gate_resource_handle_ready_not_false",
            "post_approved_runtime_evidence_gate_resource_handle_supported_not_false",
            "post_approved_runtime_evidence_gate_runtime_readiness_not_false",
            "post_approved_runtime_evidence_gate_runtime_capture_authorized_not_false",
            "post_approved_runtime_evidence_gate_non_claim_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_post_runtime_candidate_alias_policy_weakened(self) -> None:
        decisions = self.decisions()
        policy = decisions["post_approved_runtime_evidence_gate"]["next_required_artifact"][
            "non_counting_candidate_alias_policy"
        ]
        policy["alias_classes"].remove("diagnostic-only candidate aliases")
        policy["can_unlock_identity_public_contract_gate_missing"] = True
        policy["can_unlock_public_identity_contract_readiness"] = True
        policy["can_replace_reviewed_identity_public_contract_decision_record"] = True
        policy["accepted_for_public_header_gate_review"] = True
        policy["p0_progress_contribution"] = 1

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_approved_runtime_evidence_gate_next_required_artifact_mismatch", report["blockers"])
        self.assertIn(
            "post_approved_runtime_evidence_gate_non_counting_candidate_alias_policy_mismatch",
            report["blockers"],
        )
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        canonical_policy = checker.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY
        self.assertEqual(
            report["post_approved_runtime_evidence_gate"]["non_counting_candidate_alias_policy"],
            canonical_policy,
        )
        self.assertEqual(
            report["identity_public_contract_gate_missing"]["non_counting_candidate_alias_policy"],
            canonical_policy,
        )
        self.assertFalse(canonical_policy["can_unlock_identity_public_contract_gate_missing"])
        self.assertFalse(canonical_policy["can_unlock_public_identity_contract_readiness"])
        self.assertFalse(canonical_policy["can_replace_reviewed_identity_public_contract_decision_record"])
        self.assertFalse(canonical_policy["accepted_for_public_header_gate_review"])
        self.assertEqual(canonical_policy["p0_progress_contribution"], 0)

    def test_rejects_identity_contract_gate_resolution_aliases_in_post_runtime_gate(self) -> None:
        decisions = self.decisions()
        gate = decisions["post_approved_runtime_evidence_gate"]
        gate["identityPublicContractGateOpen"] = True
        gate["identityPublicContractGateMissingResolved"] = True
        gate["identityPublicContractGateCleared"] = True
        gate["publicHeaderGateOpen"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
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
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_resolved_decision_entries_cannot_advance_identity_gate_with_blockers(self) -> None:
        runtime = approved_manifest()
        decisions = self.decisions()
        for item in decisions["required_before_public_header"]:
            item["status"] = "resolved"

        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "reviewed-identity-public-contract-decision-record.json"
            self.write_identity_contract_record(
                record_path,
                self.reviewed_identity_contract_record_bound_to_runtime(runtime),
            )
            result = self.run_checker(
                decisions,
                runtime,
                "--identity-public-contract-decision-record",
                str(record_path),
                check=False,
            )

        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_before_public_header_resolved_without_public_gate", report["blockers"])
        self.assertTrue(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertTrue(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertTrue(report["identity_public_contract_decision_record"]["contract_review_only"])
        self.assertFalse(report["post_approved_runtime_evidence_gate"]["identity_contract_gate_complete"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["identity_public_contract_gate_missing"]["active"])
        self.assertFalse(report["public_header_gate_missing"]["active"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["permissions_ready"])

    def test_rejects_required_before_public_header_contract_weakened(self) -> None:
        decisions = self.decisions()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        requirements["privacy.public_identifier_form"]["must_not_expose"].remove("SteamID")
        requirements["privacy.public_identifier_form"]["required_properties"].remove(
            "generation-bearing or otherwise invalidation-aware"
        )
        requirements["privacy.redacted_identifier_fields"]["must_redact"].remove("platform account ids")
        requirements["privacy.logging_and_storage_policy"]["default_policy"] = "log opaque identity for audit"
        requirements["lifetime.principal_scope"]["allowed_scopes"].append("cluster-stable")
        requirements["lifetime.principal_scope"]["forbidden_until_separate_promotion"].remove("cluster-stable")
        requirements["lifetime.principal_scope"]["required_fields"].remove("principal_generation")
        requirements["lifetime.invalidation_events"]["required_behavior"].remove("stale principal fails closed")
        requirements["lifetime.reconnect_duplicate_stale_policy"]["required_policy"].remove(
            "stale handles never resolve to a different player"
        )
        requirements["abi.capability_bits"]["required_behavior"].remove("missing capability fails closed")
        requirements["abi.owner_token_registration"]["required_behavior"].remove("nonzero plugin_owner_token required")
        requirements["abi.owner_token_registration"]["required_behavior"].remove(
            "registration handles are not persisted or shared across server processes"
        )
        requirements["separation.no_commands_permissions_persistence"]["forbidden_in_identity_contract"].remove(
            "storage/persistence"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "privacy_public_identifier_form_missing_forbidden_terms",
            "privacy_public_identifier_form_missing_required_properties",
            "privacy_redacted_identifier_fields_missing_redactions",
            "privacy_logging_storage_default_policy_mismatch",
            "lifetime_principal_scope_forbidden_scope_allowed",
            "lifetime_principal_scope_missing_forbidden_scopes",
            "lifetime_principal_scope_missing_required_fields",
            "lifetime_invalidation_behavior_missing",
            "lifetime_reconnect_duplicate_stale_policy_missing",
            "abi_capability_bits_missing_fail_closed_behavior",
            "abi_owner_token_registration_missing_fail_closed_behavior",
            "separation_forbidden_downstream_surfaces_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_permissions_admin_query_only_or_certificate_requirement_weakened(self) -> None:
        decisions = self.decisions()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        query_only = requirements["separation.no_commands_permissions_persistence"][
            "permissions_admin_query_only_planning"
        ]
        query_only["status"] = "ready"
        query_only["public_sdk_ready"] = True
        query_only["complete_sdk_counting_allowed"] = True
        query_only["required_policy"].remove(
            "the first permissions/admin public slice may only be fail-closed permission queries over copied principals"
        )
        query_only["forbidden_until_separate_promotion"].remove("permission groups")
        query_only["non_counting_artifacts"].remove(
            "scoped non-complete-SDK release statements or exclusions"
        )
        certificate = query_only["required_identity_promotion_certificate"]
        certificate["surface_id"] = "obelisk.permissions_admin.v1"
        certificate["v1_dependency_chain_position"] = 2
        certificate["required_reviewed_artifact_hash"] = "diagnostic.report.sha256"
        certificate["missing_mismatched_or_stale_certificate_counts"] = True

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "permissions_admin_query_only_status_mismatch",
            "permissions_admin_query_only_flag_not_false",
            "permissions_admin_query_only_policy_missing",
            "permissions_admin_query_only_forbidden_terms_missing",
            "permissions_admin_query_only_non_counting_artifacts_missing",
            "permissions_admin_identity_promotion_certificate_requirement_mismatch",
            "permissions_admin_identity_promotion_certificate_non_counting_flag_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_stale_required_before_public_header_status(self) -> None:
        decisions = self.decisions()
        requirements = {
            item["id"]: item
            for item in decisions["required_before_public_header"]
        }
        requirements["privacy.public_identifier_form"]["status"] = "stale"
        requirements["abi.payload_shape"]["status"] = "candidate_accepted"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        status_blockers = [
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "required_before_public_header_status_mismatch"
        ]
        self.assertEqual(
            [blocker["requirement_id"] for blocker in status_blockers],
            ["privacy.public_identifier_form", "abi.payload_shape"],
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_pre_header_test_overclaims(self) -> None:
        decisions = self.decisions()
        for item in decisions["required_tests_before_public_header"]:
            if item["id"] == "runtime.evidence_intake":
                item["promotion_ready"] = True
            elif item["id"] == "abi.layout":
                item["status"] = "covered"

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_review_input_test_promotion_ready_not_false", report["blockers"])
        self.assertIn("pre_header_test_marked_ready_without_public_gate", report["blockers"])

    def test_rejects_pre_header_required_coverage_weakened(self) -> None:
        decisions = self.decisions()
        tests = {
            item["id"]: item
            for item in decisions["required_tests_before_public_header"]
        }
        tests["sdk.consumer"]["required_coverage"].remove(
            "consumer treats principal handles and registration handles as process-local and non-persistent"
        )
        tests["lifecycle.owner_cleanup"]["required_coverage"].remove(
            "plugin unload drains in-flight callbacks"
        )
        tests["identity.fail_closed"]["required_coverage"].remove(
            "cross-instance or cross-process handle reuse fails closed"
        )
        tests["runtime.evidence_intake"]["required_coverage"].remove(
            "approved runtime evidence cannot set promotion_ready, public_sdk_ready, runtime_ready, public_header_allowed, public_api_ready, public_abi_ready, lookup_ready, permissions_ready, commands_ready, or v1_completion_evidence"
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_test_coverage_missing", report["blockers"])
        coverage_blockers = [
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "required_test_coverage_missing"
        ]
        self.assertEqual(len(coverage_blockers), 4)

    def test_malformed_required_tests_reports_json_blocker(self) -> None:
        decisions = self.decisions()
        decisions["required_tests_before_public_header"] = {}

        result = self.run_checker(decisions, approved_manifest(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_tests_before_public_header_not_list", report["blockers"])
        self.assertIn("required_tests_before_public_header_mismatch", report["blockers"])

    def test_header_still_has_no_player_identity_public_symbols(self) -> None:
        header = HEADER.read_text(encoding="utf-8")
        for token in (
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
            "ObeliskPlayerPrincipal",
            "RegisterPlayerIdentity",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, header)

    def test_public_text_overclaims_rejects_split_key_value_aliases(self) -> None:
        claims = checker.public_text_overclaims(
            {
                "publicSdkReady": {"state": "ready"},
                "publicApiReady": {"state": "ready"},
                "publicAbiReady": {"state": "blocked"},
                "identityPublicContractDecisionRecordContractReviewOnly": True,
                "publicContractDecisionRecordReviewed": True,
                "publicContractDecisionRecordHashCurrent": True,
                "contractReviewOnly": True,
                "mutationAllowed": True,
                "returnOverrideAllowed": True,
                "public_header_symbols_now": {"symbols": ["PrivateOnlySymbol"]},
                "public_api_symbols_now": {"symbols": ["RegisterPlayerIdentityApi"]},
                "public_callback_abi_now": {"symbols": ["blocked"]},
                "public": {
                    "sdk": {"ready": True},
                    "header": {"symbols_now": ["PrivateOnlySymbol"]},
                    "capability": {"bits_now": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]},
                    "callback": {"abi_now": ["ObeliskPlayerPrincipalEventCallback"]},
                },
                "claims": [
                    {"key": "publicIdentityReady", "value": True},
                    {"key": "runtimePrincipalReady", "value": True},
                    {"field": "principalHandleAbiReady", "state": "ready"},
                    {"claim": "identityHeaderAllowed", "enabled": "yes"},
                    {"aliases": ["publicHeaderAllowed", "runtimeEvidenceReady"], "values": ["ready"]},
                    {"key": "publicApiReadiness", "readiness": "satisfied"},
                    {"key": "public_header_symbols_now", "values": ["PrivateOnlySymbol"]},
                    {"key": "publicIdentityReady", "value": False},
                    {"claims": ["publicHeaderAllowed"], "values": ["blocked"]},
                    {"key": "public_header_symbols_now", "values": []},
                    {"key": "public_header_symbols_now", "values": ["blocked"]},
                ]
            }
        )
        paths = {claim["path"] for claim in claims}

        self.assertIn("$.publicSdkReady", paths)
        self.assertIn("$.publicApiReady", paths)
        self.assertNotIn("$.publicAbiReady", paths)
        self.assertIn("$.identityPublicContractDecisionRecordContractReviewOnly", paths)
        self.assertIn("$.publicContractDecisionRecordReviewed", paths)
        self.assertIn("$.publicContractDecisionRecordHashCurrent", paths)
        self.assertIn("$.contractReviewOnly", paths)
        self.assertIn("$.mutationAllowed", paths)
        self.assertIn("$.returnOverrideAllowed", paths)
        self.assertIn("$.public_header_symbols_now", paths)
        self.assertIn("$.public_api_symbols_now", paths)
        self.assertNotIn("$.public_callback_abi_now", paths)
        self.assertIn("$.public.sdk.ready", paths)
        self.assertIn("$.public.header.symbols_now", paths)
        self.assertIn("$.public.capability.bits_now", paths)
        self.assertIn("$.public.callback.abi_now", paths)
        self.assertIn("$.claims[0]", paths)
        self.assertIn("$.claims[1]", paths)
        self.assertIn("$.claims[2]", paths)
        self.assertIn("$.claims[3]", paths)
        self.assertIn("$.claims[4]", paths)
        self.assertIn("$.claims[5]", paths)
        self.assertIn("$.claims[6]", paths)
        self.assertNotIn("$.claims[7]", paths)
        self.assertNotIn("$.claims[8]", paths)
        self.assertNotIn("$.claims[9]", paths)
        self.assertNotIn("$.claims[10]", paths)

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

    def test_public_text_overclaims_rejects_post_runtime_shortcut_aliases(self) -> None:
        claims = checker.public_text_overclaims(
            {
                "contract_reviewed": True,
                "identity_contract_hash_current": True,
                "header_shape_valid": True,
                "p0_unlocked": "identity",
                "blocker_resolved": "runtime",
                "public": {"surface": {"status": "accepted"}},
                "split": [
                    {"claim": "p0_unlocked", "value": "identity"},
                    {"field": "blocker_resolved", "status": "runtime"},
                ],
            }
        )
        paths = {claim["path"] for claim in claims}

        for path in (
            "$.contract_reviewed",
            "$.identity_contract_hash_current",
            "$.header_shape_valid",
            "$.p0_unlocked",
            "$.blocker_resolved",
            "$.public.surface.status",
            "$.split[0]",
            "$.split[1]",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_public_text_overclaims_rejects_non_counting_candidate_alias_unlocks(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "copied-log candidate alias unlocks public identity contract readiness",
                "live-ops sidecar candidate alias opens identity_public_contract_gate_missing",
                "confirmed beta notice candidate alias satisfies public identity contract readiness",
                "passive monitor candidate alias resolves identity_public_contract_gate_missing",
                "diagnostic candidate alias marks obelisk.player_identity.v1 ready",
                "multi-surface beta capture pack satisfies approved_runtime_evidence_binding",
                "multi-surface beta capture plan unlocks public identity contract readiness",
                "multi-surface candidate queue counts toward SDK/P0 progress",
                "beta capture pack marks runtime readiness complete",
                "candidate beta capture prep sets public SDK readiness",
                "multi-surface beta capture pack remains candidate-only and cannot satisfy public SDK readiness",
            ]
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in claims:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])

        for index in range(10):
            path = f"$[{index}]"
            with self.subTest(path=path):
                self.assertIn(
                    "non_counting_artifact_public_readiness_or_p0",
                    terms_by_path[path],
                )
        self.assertNotIn("$[10]", terms_by_path)

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
                "identityPublicContractDecisionRecordContractReviewOnly": True,
                "identityPublicContractCurrent": True,
                "identityPublicContractHashCurrent": True,
                "identityPublicContractReviewed": True,
                "publicIdentityContractHashCurrent": True,
                "publicIdentityContractReviewed": True,
                "reviewedIdentityPublicContractHashCurrent": True,
                "reviewedIdentityPublicContractRecord": True,
                "reviewedIdentityPublicContractDecisionRecordContractReviewOnly": True,
                "publicContractDecisionRecordReviewed": True,
                "publicContractDecisionRecordHashCurrent": True,
                "publicContractDecisionRecordContractReviewOnly": True,
                "contractReviewOnly": True,
                "principalStartEndRuntimeEvidenceReady": True,
                "approvedRuntimePrincipalLifecycleBundleRoutesTo": "permissions/admin",
                "broadcastReady": True,
                "rconReady": True,
                "rconCommandReady": True,
                "rconReplyReady": True,
                "packageShapeReady": True,
                "pluginHubReady": True,
                "completeSdkReady": True,
                "p0ProgressReady": True,
                "sdkP0ProgressReady": True,
                "resourceHandleReady": True,
                "resourceHandleSupported": True,
                "mutationAllowed": True,
                "mutationReady": True,
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
            "$.identityPublicContractCurrent",
            "$.identityPublicContractHashCurrent",
            "$.identityPublicContractReviewed",
            "$.publicIdentityContractHashCurrent",
            "$.publicIdentityContractReviewed",
            "$.reviewedIdentityPublicContractHashCurrent",
            "$.reviewedIdentityPublicContractRecord",
            "$.principalStartEndRuntimeEvidenceReady",
            "$.approvedRuntimePrincipalLifecycleBundleRoutesTo",
            "$.broadcastReady",
            "$.rconReady",
            "$.rconCommandReady",
            "$.rconReplyReady",
            "$.packageShapeReady",
            "$.pluginHubReady",
            "$.completeSdkReady",
            "$.p0ProgressReady",
            "$.sdkP0ProgressReady",
            "$.resourceHandleReady",
            "$.resourceHandleSupported",
            "$.mutationAllowed",
            "$.mutationReady",
            "$.returnOverrideAllowed",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_rejects_identity_public_contract_reviewed_current_aliases_in_decisions(self) -> None:
        decisions = self.decisions()
        decisions.update(
            {
                "identityPublicContractCurrent": True,
                "identityPublicContractHashCurrent": True,
                "identityPublicContractReviewed": True,
                "publicIdentityContractHashCurrent": True,
                "publicIdentityContractReviewed": True,
                "reviewedIdentityPublicContractHashCurrent": True,
                "reviewedIdentityPublicContractRecord": True,
            }
        )

        result = self.run_checker(decisions, approved_manifest(), check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        for path in (
            "$.identityPublicContractCurrent",
            "$.identityPublicContractHashCurrent",
            "$.identityPublicContractReviewed",
            "$.publicIdentityContractHashCurrent",
            "$.publicIdentityContractReviewed",
            "$.reviewedIdentityPublicContractHashCurrent",
            "$.reviewedIdentityPublicContractRecord",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_public_text_overclaims_rejects_readiness_noun_prose_and_public_gate_alias(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "public ABI readiness is satisfied",
                "public API readiness is satisfied",
                "public header readiness is satisfied",
                "SDK consumer tests are passing",
                "runtime readiness is satisfied",
                "SDK/P0 progress is complete",
                "P0 progress is complete",
                "ResourceHandle is ready",
                "mutation is allowed",
                "public_readiness",
                "public readiness is blocked",
            ]
        )
        paths = {claim["path"] for claim in claims}

        self.assertIn("$[0]", paths)
        self.assertIn("$[1]", paths)
        self.assertIn("$[2]", paths)
        self.assertIn("$[3]", paths)
        self.assertIn("$[4]", paths)
        self.assertIn("$[5]", paths)
        self.assertIn("$[6]", paths)
        self.assertIn("$[7]", paths)
        self.assertIn("$[8]", paths)
        self.assertIn("$[9]", paths)
        self.assertNotIn("$[10]", paths)

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

    def test_public_text_overclaims_rejects_contract_review_and_header_shape_shortcuts(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "reviewed hash-current contract-review-only record marks public header readiness satisfied",
                "contract-review-only record unlocks downstream P0",
                "reviewed identity public contract decision record opens P0 dependency chain",
                "proposal-only header gate shape counts toward P0 unlock",
                "public header proposal shape marks public identity ready",
                "contract-review-only record does not unlock downstream P0",
            ]
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in claims:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])

        self.assertIn("contract_review_metadata_public_readiness", terms_by_path["$[0]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$[1]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$[2]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$[3]"])
        self.assertIn("public_identity_ready", terms_by_path["$[4]"])
        self.assertNotIn("$[5]", terms_by_path)

    def test_public_text_overclaims_rejects_after_runtime_route_shortcuts(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "after accepted runtime lifecycle evidence next blocker is public_header_gate_missing",
                "approved runtime principal lifecycle bundle routes to permissions/admin readiness",
                "runtime lifecycle evidence next blocker is command/chat response",
                "approved runtime lifecycle evidence routes to complete SDK",
                "after accepted runtime lifecycle evidence next blocker is identity_public_contract_gate_missing",
                "accepted runtime lifecycle evidence does not route to public_header_gate_missing",
            ]
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in claims:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])

        for path in ("$[0]", "$[1]", "$[2]", "$[3]"):
            with self.subTest(path=path):
                self.assertIn("post_runtime_route_shortcut", terms_by_path[path])
        self.assertNotIn("$[4]", terms_by_path)
        self.assertNotIn("$[5]", terms_by_path)

    def test_public_text_overclaims_rejects_non_counting_operational_artifact_p0_shortcuts(self) -> None:
        claims = checker.public_text_overclaims(
            [
                "post-reboot passive monitor context counts toward P0 dependency chain",
                "confirmed beta notice JSON unlocks public identity readiness",
                "next-action status report contributes to SDK/P0 progress",
                "copied-log-only artifact marks obelisk.player_identity.v1 ready",
                "installed runtime status counts toward P0 dependency chain",
                "broadcast sent OK unlocks commands/replies readiness",
                "RCON OK marks permissions/admin ready",
                "copied-log-only artifact does not count toward P0 progress",
            ]
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in claims:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])

        for path in ("$[0]", "$[1]", "$[2]", "$[3]", "$[4]", "$[5]", "$[6]"):
            with self.subTest(path=path):
                self.assertIn("non_counting_artifact_public_readiness_or_p0", terms_by_path[path])
        self.assertNotIn("$[7]", terms_by_path)

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
                    {"key": "public_header_symbols_now", "values": []},
                    {"key": "public_header_symbols_now", "values": ["blocked"]},
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
        self.assertNotIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[8]"), paths)
        self.assertNotIn(("nested_readiness_split_claim_overclaim", "$.unit_test.nested[9]"), paths)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.public.sdk.ready"), paths)
        self.assertIn(("nested_public_header_symbols_now_not_empty", "$.unit_test.public.header.symbols_now"), paths)
        self.assertIn(("nested_public_capability_bits_now_not_empty", "$.unit_test.public.capability.bits_now"), paths)
        self.assertIn(("nested_public_callback_abi_now_not_empty", "$.unit_test.public.callback.abi_now"), paths)

    def test_sanitize_non_promotional_report_rejects_post_runtime_shortcut_aliases(self) -> None:
        blockers: list[dict] = []
        sanitized = checker.sanitize_non_promotional_report(
            {
                "contract_reviewed": True,
                "identity_contract_hash_current": True,
                "header_shape_valid": True,
                "p0_unlocked": "identity",
                "blocker_resolved": "runtime",
                "public": {"surface": {"status": "accepted"}},
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        labels = {(item["reason"], item["label"]) for item in blockers}

        for key in (
            "contract_reviewed",
            "identity_contract_hash_current",
            "header_shape_valid",
            "p0_unlocked",
            "blocker_resolved",
        ):
            with self.subTest(key=key):
                self.assertFalse(sanitized[key])
                self.assertIn(("nested_readiness_flag_not_false", f"$.unit_test.{key}"), labels)
        self.assertFalse(sanitized["public"]["surface"]["status"])
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.public.surface.status"), labels)

    def test_sanitize_non_promotional_report_rejects_multi_surface_beta_capture_pack_overclaims(self) -> None:
        blockers: list[dict] = []
        sanitized = checker.sanitize_non_promotional_report(
            {
                "multi_surface_beta_capture_pack": {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "status": "ready",
                    "approvedRuntimeEvidenceReady": True,
                    "approvedRuntimeEvidenceBinding": self.multi_surface_beta_capture_binding(),
                    "publicIdentityContractReadiness": "satisfied",
                    "runtimeReady": True,
                    "publicSdkReady": True,
                    "sdkProgress": 1,
                    "sdkP0ProgressReady": True,
                    "p0DependencyChainClaimProgressContribution": "1/4",
                    "candidate_surfaces": [
                        {
                            "surface": "permissions_admin",
                            "status": "candidate_capture_pack",
                            "publicSdkReady": False,
                            "sdkProgress": 0,
                        },
                    ],
                },
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        labels = {(item["reason"], item["label"]) for item in blockers}
        pack = sanitized["multi_surface_beta_capture_pack"]

        self.assertFalse(pack["status"])
        self.assertFalse(pack["approvedRuntimeEvidenceReady"])
        self.assertFalse(pack["approvedRuntimeEvidenceBinding"])
        self.assertFalse(pack["publicIdentityContractReadiness"])
        self.assertFalse(pack["runtimeReady"])
        self.assertFalse(pack["publicSdkReady"])
        self.assertEqual(pack["sdkProgress"], 0)
        self.assertFalse(pack["sdkP0ProgressReady"])
        self.assertEqual(pack["p0DependencyChainClaimProgressContribution"], 0)
        self.assertEqual(pack["candidate_surfaces"][0]["status"], "candidate_capture_pack")
        self.assertEqual(pack["candidate_surfaces"][0]["sdkProgress"], 0)
        for label in (
            "$.unit_test.multi_surface_beta_capture_pack.status",
            "$.unit_test.multi_surface_beta_capture_pack.approvedRuntimeEvidenceReady",
            "$.unit_test.multi_surface_beta_capture_pack.approvedRuntimeEvidenceBinding",
            "$.unit_test.multi_surface_beta_capture_pack.publicIdentityContractReadiness",
            "$.unit_test.multi_surface_beta_capture_pack.runtimeReady",
            "$.unit_test.multi_surface_beta_capture_pack.publicSdkReady",
            "$.unit_test.multi_surface_beta_capture_pack.sdkProgress",
            "$.unit_test.multi_surface_beta_capture_pack.sdkP0ProgressReady",
            "$.unit_test.multi_surface_beta_capture_pack.p0DependencyChainClaimProgressContribution",
        ):
            with self.subTest(label=label):
                self.assertIn(("nested_readiness_flag_not_false", label), labels)
        self.assertNotIn(
            (
                "nested_readiness_flag_not_false",
                "$.unit_test.multi_surface_beta_capture_pack.candidate_surfaces[0].status",
            ),
            labels,
        )

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
                "principalStartEndRuntimeEvidenceReady": True,
                "approvedRuntimePrincipalLifecycleBundleRoutesTo": "permissions/admin",
                "broadcastReady": True,
                "rconReady": True,
                "rconCommandReady": True,
                "rconReplyReady": True,
                "packageShapeReady": True,
                "pluginHubReady": True,
                "completeSdkReady": True,
                "p0ProgressReady": True,
                "sdkP0ProgressReady": True,
                "resourceHandleReady": True,
                "resourceHandleSupported": True,
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
            "principalStartEndRuntimeEvidenceReady",
            "approvedRuntimePrincipalLifecycleBundleRoutesTo",
            "broadcastReady",
            "rconReady",
            "rconCommandReady",
            "rconReplyReady",
            "packageShapeReady",
            "pluginHubReady",
            "completeSdkReady",
            "p0ProgressReady",
            "sdkP0ProgressReady",
            "resourceHandleReady",
            "resourceHandleSupported",
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
                "completeSdkReady": True,
                "p0ProgressReady": True,
                "sdkP0ProgressReady": True,
                "resourceHandleSupported": True,
                "mutationAllowed": True,
                "notes": [
                    "stable claim is allowed",
                    "helper-derived readiness is satisfied",
                    "permissions/admin is unlocked",
                    "command response is unlocked",
                    "commands/replies are ready",
                    "runtime work is authorized",
                    "counts toward public SDK",
                    "production SDK is ready",
                    "SDK/P0 progress is complete",
                    "ResourceHandle is ready",
                    "mutation is allowed",
                ],
            },
            blockers,
            input_label="unit_test",
            path="$.unit_test",
        )
        labels = {(item["reason"], item["label"]) for item in blockers}

        self.assertFalse(sanitized["stable_claim_allowed"])
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
        self.assertFalse(sanitized["completeSdkReady"])
        self.assertFalse(sanitized["p0ProgressReady"])
        self.assertFalse(sanitized["sdkP0ProgressReady"])
        self.assertFalse(sanitized["resourceHandleSupported"])
        self.assertFalse(sanitized["mutationAllowed"])
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.stable_claim_allowed"), labels)
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
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.completeSdkReady"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.p0ProgressReady"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.sdkP0ProgressReady"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.resourceHandleSupported"), labels)
        self.assertIn(("nested_readiness_flag_not_false", "$.unit_test.mutationAllowed"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[0]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[1]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[2]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[3]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[4]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[5]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[6]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[7]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[8]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[9]"), labels)
        self.assertIn(("nested_public_text_overclaim", "$.unit_test.notes[10]"), labels)


if __name__ == "__main__":
    unittest.main()
