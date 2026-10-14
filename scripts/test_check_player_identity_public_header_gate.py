#!/usr/bin/env python3
"""Tests for check_player_identity_public_header_gate.py."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_header_gate.py"
PROPOSAL = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-public-header-gate-proposal.json"
)
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_public_header_gate as checker
from test_check_player_identity_public_contract_decision_record import (
    TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL,
    TEST_STRICT_REPORT_SENTINEL,
    accepted_record,
    approved_runtime_evidence_manifest_ref,
    strict_approved_runtime_check_report,
    strict_approved_runtime_check_report_ref,
)
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    manifest as approved_runtime_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)


RUNTIME_FIXTURE_NOW_SITECUSTOMIZE = """
from datetime import datetime, timezone

_OBELISK_RUNTIME_FIXTURE_NOW = datetime(2026, 6, 1, 12, 11, 0, tzinfo=timezone.utc)


def _obelisk_runtime_fixture_now_utc():
    return _OBELISK_RUNTIME_FIXTURE_NOW


import check_player_identity_runtime_principal_lifecycle_window_manifest as _obelisk_window_manifest
import check_player_identity_runtime_principal_lifecycle_approved_evidence as _obelisk_approved_evidence

_obelisk_window_manifest.now_utc = _obelisk_runtime_fixture_now_utc
_obelisk_approved_evidence.now_utc = _obelisk_runtime_fixture_now_utc
_obelisk_approved_evidence.window_manifest_checker.now_utc = _obelisk_runtime_fixture_now_utc


class _ObeliskAcceptedRuntimeValidation:
    blockers = []


def _obelisk_accepted_runtime_validate_manifest(_payload, *, check_mode, input_path=None):
    return _ObeliskAcceptedRuntimeValidation()


def _obelisk_accepted_runtime_build_report(_payload, _validation, *, check_mode):
    return {
        "schema": _obelisk_approved_evidence.REPORT_SCHEMA,
        "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "mode": "consume",
        "ready": True,
        "ready_scope": "runtime_evidence_only",
        "next_blocker": "identity_public_contract_gate_missing",
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
        "resolved_input": "runtime.lifecycle_evidence",
        "resolved_inputs": ["runtime.lifecycle_evidence"],
        "remaining_blockers": [],
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_start_rejected_anchor",
            "session_end_anchor",
        ],
        "required_lifecycle_event_role_triplet": [
            "session_start",
            "session_start_rejected",
            "session_end",
        ],
        "missing_lifecycle_event_roles": [],
        "strict_lifecycle_triplet_selection": {
            "status": "selected",
            "accepted": True,
            "candidate_count": 1,
            "selected_indices": [0, 1, 2],
            "selected_sequences": [1, 2, 3],
            "selected_roles": [
                "session_start",
                "session_start_rejected",
                "session_end",
            ],
            "selected_cases": [],
            "non_counting_context_event_count": 0,
            "non_counting_context_roles": [],
            "candidate_triplets": [],
            "missing_roles": [],
            "blockers": [],
        },
        "strict_lifecycle_triplet_selected": True,
        "strict_lifecycle_triplet_non_counting_context_event_count": 0,
        "strict_lifecycle_triplet_non_counting_context_roles": [],
        "session_end_missing_correlation_diagnostics": None,
        "consumer_cases": [
            "malformed_or_unsupported_evidence",
            "stale_after_logout",
        ],
        "consumer_boundary_assertions": [
            "malformed_or_unsupported_evidence",
            "stale_after_logout",
        ],
        "partial_start_end_present": False,
        "missing_strict_rejected_start": False,
        "strict_rejected_start_expected_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "strict_rejected_start_observed_shape": {
            "shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        },
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_readiness": False,
        "runtime_readiness": False,
        "stable_ready": False,
        "accepted_for_header_gate_review": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_or_runtime_accounting_allowed": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "complete_sdk_allowed": False,
        "complete_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_ready": False,
        "non_evidence_reasons": [],
        "artifact_path_issues": [],
        "blockers": [],
        "blocker_details": [],
        "non_claims": [
            "accepted runtime lifecycle evidence is contract-review input only",
        ],
    }


_obelisk_approved_evidence.validate_manifest = _obelisk_accepted_runtime_validate_manifest
_obelisk_approved_evidence.build_report = _obelisk_accepted_runtime_build_report
"""


def accepted_runtime_checker_contract_report() -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "mode": "consume",
        "ready": True,
        "ready_scope": "runtime_evidence_only",
        "next_blocker": "identity_public_contract_gate_missing",
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
        "resolved_input": "runtime.lifecycle_evidence",
        "resolved_inputs": ["runtime.lifecycle_evidence"],
        "remaining_blockers": [],
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_start_rejected_anchor",
            "session_end_anchor",
        ],
        "required_lifecycle_event_role_triplet": [
            "session_start",
            "session_start_rejected",
            "session_end",
        ],
        "missing_lifecycle_event_roles": [],
        "strict_lifecycle_triplet_selection": {
            "status": "selected",
            "accepted": True,
            "candidate_count": 1,
            "selected_indices": [0, 1, 2],
            "selected_sequences": [1, 2, 3],
            "selected_roles": [
                "session_start",
                "session_start_rejected",
                "session_end",
            ],
            "selected_cases": [],
            "non_counting_context_event_count": 0,
            "non_counting_context_roles": [],
            "candidate_triplets": [],
            "missing_roles": [],
            "blockers": [],
        },
        "strict_lifecycle_triplet_selected": True,
        "strict_lifecycle_triplet_non_counting_context_event_count": 0,
        "strict_lifecycle_triplet_non_counting_context_roles": [],
        "session_end_missing_correlation_diagnostics": None,
        "consumer_cases": [
            "malformed_or_unsupported_evidence",
            "stale_after_logout",
        ],
        "consumer_boundary_assertions": [
            "malformed_or_unsupported_evidence",
            "stale_after_logout",
        ],
        "partial_start_end_present": False,
        "missing_strict_rejected_start": False,
        "strict_rejected_start_expected_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "strict_rejected_start_observed_shape": {
            "shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        },
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_readiness": False,
        "runtime_readiness": False,
        "stable_ready": False,
        "accepted_for_header_gate_review": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_or_runtime_accounting_allowed": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "complete_sdk_allowed": False,
        "complete_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_ready": False,
        "non_evidence_reasons": [],
        "artifact_path_issues": [],
        "blockers": [],
        "blocker_details": [],
        "non_claims": [
            "accepted runtime lifecycle evidence is contract-review input only",
        ],
    }


class PlayerIdentityPublicHeaderGateTests(unittest.TestCase):
    def proposal(self) -> dict:
        return json.loads(PROPOSAL.read_text(encoding="utf-8"))

    def decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def record_bound_to(self, approved_runtime_evidence: dict) -> dict:
        record = accepted_record()
        record[TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL] = approved_runtime_evidence
        record["approved_runtime_evidence_binding"] = (
            checker.public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(
                approved_runtime_evidence
            )
        )
        return record

    def accepted_runtime_report(self) -> dict:
        return {
            "provided": True,
            "accepted_for_contract_review": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "resolved_input": "runtime.lifecycle_evidence",
            "resolved_inputs": ["runtime.lifecycle_evidence"],
            "ready_scope": "runtime_evidence_only",
            "next_blocker": checker.NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "observed_runtime_cases": [
                "observer_enable",
                "session_start_anchor",
                "session_start_rejected_anchor",
                "session_end_anchor",
            ],
            "consumer_cases": [
                "malformed_or_unsupported_evidence",
                "stale_after_logout",
            ],
            "consumer_boundary_assertions": [
                "malformed_or_unsupported_evidence",
                "stale_after_logout",
            ],
            "source_provenance_policy": {
                "non_promotional_sources_rejected": True,
                "accepted_source_kind": checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
                "findings": [],
            },
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "accepted_for_header_gate_review": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "blockers": [],
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
            "lookup_ready",
            "storage_persistence_ready",
            "public_sdk_ready",
            "stable_ready",
            "stable_claim_allowed",
            "stable_claim_ready",
            "stable_sdk_ready",
            "plugin_hub_ready",
            "plugin_hub_publication_ready",
            "publication_ready",
            "publication_authorized",
            "promotion_ready",
            "public_contract_allowed",
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_readiness",
            "runtime_ready",
            "runtime_readiness",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
            "public_sdk_v1_completion_ready",
            "complete_sdk_ready",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(summary_key=key):
                self.assertFalse(summary[key])
        self.assertEqual(summary["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(summary["p0_dependency_chain_claim_progress_contribution"], 0)

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
        payload: dict,
        *,
        header_text: str | None = None,
        public_contract_decisions: dict | None = None,
        approved_runtime_evidence: dict | None = None,
        identity_public_contract_decision_record: dict | None = None,
        extra_args: list[str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            proposal_path = root / "proposal.json"
            header_path = root / "ObeliskApi.h"
            decisions_path = root / "player_identity_public_contract_decisions.json"
            approved_runtime_path = root / "approved-runtime-evidence.json"
            decision_record_path = root / "reviewed-identity-public-contract-decision-record.json"
            proposal_path.write_text(json.dumps(payload), encoding="utf-8")
            header_path.write_text(
                header_text if header_text is not None else HEADER.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            args = [
                sys.executable,
                str(SCRIPT),
                "--proposal",
                str(proposal_path),
                "--public-header",
                str(header_path),
                "--json",
                *(extra_args or []),
            ]
            if public_contract_decisions is not None:
                decisions_path.write_text(json.dumps(public_contract_decisions), encoding="utf-8")
                args.extend(["--public-contract-decisions", str(decisions_path)])
            if approved_runtime_evidence is not None:
                approved_runtime_path.write_text(json.dumps(approved_runtime_evidence), encoding="utf-8")
                args.extend(["--approved-runtime-evidence", str(approved_runtime_path)])
            if identity_public_contract_decision_record is not None:
                record_to_write = copy.deepcopy(identity_public_contract_decision_record)
                runtime_manifest = record_to_write.pop(TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL, None)
                runtime_manifest_path = None
                if runtime_manifest is not None:
                    runtime_manifest_path = root / "record-approved-runtime-evidence.json"
                    runtime_manifest_path.write_text(
                        json.dumps(runtime_manifest, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    record_to_write[
                        checker.public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD
                    ] = approved_runtime_evidence_manifest_ref(runtime_manifest_path)
                strict_report_sentinel_present = TEST_STRICT_REPORT_SENTINEL in record_to_write
                strict_report = record_to_write.pop(TEST_STRICT_REPORT_SENTINEL, None)
                if strict_report is None and strict_report_sentinel_present:
                    self.assertIsNotNone(runtime_manifest)
                    self.assertIsNotNone(runtime_manifest_path)
                    strict_report = accepted_runtime_checker_contract_report()
                if strict_report is not None:
                    strict_report_path = root / "record-approved-runtime-evidence.check.json"
                    strict_report_path.write_text(
                        json.dumps(strict_report, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    record_to_write[
                        checker.public_contract_decision_record.STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD
                    ] = strict_approved_runtime_check_report_ref(strict_report_path)
                decision_record_path.write_text(
                    json.dumps(record_to_write),
                    encoding="utf-8",
                )
                args.extend(["--identity-public-contract-decision-record", str(decision_record_path)])
            result = subprocess.run(
                args,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.approved_runtime_fixture_env(root),
            )
        if check and result.returncode != 0:
            self.fail(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_blocks_repo_proposal_while_identity_contract_gate_is_unresolved(self) -> None:
        result = self.run_checker(self.proposal(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertIn("public_header_gate_blocked_by_identity_public_contract_gate", report["blockers"])
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS", report["proposed_symbols"])
        self.assertIn("OBELISK_PLAYER_PRINCIPAL_EVENT_KIND_SESSION_START", report["proposed_symbols"])
        self.assertIn("OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_LOOKUP", report["proposed_symbols"])
        self.assertIn("ObeliskPlayerPrincipalEvent", report["proposed_symbols"])
        self.assertIn("RegisterPlayerPrincipalEventWithOwnerTokenHandle", report["proposed_symbols"])
        self.assertEqual(report["next_blocker"], "approved_runtime_evidence_required_before_header_gate")
        self.assertEqual(report["accepted_runtime_evidence_route_only"], "identity_public_contract_gate_missing")
        self.assertEqual(report["post_runtime_evidence_next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["post_runtime_identity_contract_gate"]["active_after_approved_runtime_evidence"])
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["offline_preparation"],
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["offline_preparation"][
                "does_not_unlock_identity_public_contract_gate"
            ]
        )
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["offline_preparation"][
                "does_not_unlock_public_header_gate"
            ]
        )
        self.assertIn("approved_runtime_evidence_required_before_header_gate", report["blockers"])
        self.assertEqual(
            set(report["blockers"]),
            {
                "public_header_gate_blocked_by_identity_public_contract_gate",
                "approved_runtime_evidence_required_before_header_gate",
            },
        )
        self.assertNotIn("unexpected_claim_alias_value", report["blockers"])
        self.assertNotIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        self.assertNotIn("public_text_or_source_overclaim", report["blockers"])
        self.assertEqual(report["public_capability_bits_now"], [])
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
            "off_header_abi_proposal_counts",
            "public_callback_abi_ready",
            "permissions_admin_unlocked",
            "commands_replies_unlocked",
            "sdk_p0_progress",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        for key in (
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "public_or_runtime_accounting_allowed",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertIn("proposal-only header gate review input", report["non_claims"])

    def test_rejects_public_header_symbols_and_capability_bits_before_promotion(self) -> None:
        header_text = (
            HEADER.read_text(encoding="utf-8")
            + "\n#define OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS (1ull << 12)\n"
            + "typedef void (*ObeliskPlayerPrincipalEventCallback)(void* event, void* user_data);\n"
            + "struct ObeliskApiPlayerPrincipalLeak {\n"
            + "    uint64_t (*RegisterPlayerPrincipalEventWithOwnerTokenHandle)(uint64_t owner_token);\n"
            + "};\n"
        )

        result = self.run_checker(
            self.proposal(),
            header_text=header_text,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_already_exposes_proposed_symbols", report["blockers"])
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        self.assertIn("capability_bit_already_used_in_public_header", report["blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_header_gate_acceptance_requires_runtime_evidence_and_hash_current_review_record(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=self.record_bound_to(runtime_evidence),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "proposal_only_not_public")
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["header_gate_review_ready"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            report["identity_public_contract_gate_next_step"]["accepted_route"]["only_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["identity_public_contract_gate_next_step"]["required_record_state"],
            "reviewed_hash_current_contract_review_only",
        )
        self.assertFalse(report["identity_public_contract_gate_next_step"]["non_claim_flags"]["public_sdk_ready"])
        self.assertFalse(report["identity_public_contract_gate_next_step"]["non_claim_flags"]["runtime_ready"])
        self.assertFalse(report["identity_public_contract_gate_next_step"]["non_claim_flags"]["p0_progress_ready"])
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["approved_runtime_evidence"]["accepted_for_header_gate_review"])
        self.assertEqual(report["approved_runtime_evidence"]["resolved_input"], "runtime.lifecycle_evidence")
        self.assertFalse(report["approved_runtime_evidence"]["stable_claim_ready"])
        self.assertFalse(report["approved_runtime_evidence"]["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["approved_runtime_evidence"]["p0_progress_ready"])
        self.assertFalse(report["approved_runtime_evidence"]["sdk_p0_progress_ready"])
        self.assertEqual(report["approved_runtime_evidence"]["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertTrue(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_header_gate_review"])
        self.assertTrue(report["identity_public_contract_decision_record"]["contract_review_only"])
        self.assertTrue(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertTrue(
            report["identity_public_contract_decision_record"]["reviewed_hash_current_contract_review_only"]
        )
        self.assertTrue(report["identity_public_contract_decision_record"]["runtime_evidence_binding_valid"])
        self.assertTrue(report["identity_public_contract_decision_record"]["bound_to_accepted_runtime_evidence"])
        self.assertEqual(
            report["identity_public_contract_decision_record"]["approved_runtime_evidence_binding"],
            report["approved_runtime_evidence"]["approved_runtime_evidence_binding"],
        )
        self.assertTrue(report["post_runtime_identity_contract_gate"]["requires_reviewed_decision_record"])
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["offline_preparation"],
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["offline_preparation"][
                "must_bind_to_approved_runtime_evidence"
            ]
        )
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["offline_preparation"][
                "must_bind_current_source_artifacts"
            ]
        )
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["offline_preparation"][
                "does_not_unlock_public_header_gate"
            ]
        )
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(offline_preparation_key=key):
                self.assertFalse(report["post_runtime_identity_contract_gate"]["offline_preparation"][key])
        self.assertTrue(
            report["post_runtime_identity_contract_gate"]["requires_binding_to_accepted_runtime_evidence"]
        )
        self.assertTrue(report["post_runtime_identity_contract_gate"]["record_bound_to_accepted_runtime_evidence"])
        self.assertFalse(
            report["post_runtime_identity_contract_gate"]["public_header_api_abi_sdk_runtime_shortcut_allowed"]
        )
        path = report["post_runtime_public_header_fail_closed_path"]
        self.assertEqual(report["post_runtime_identity_contract_gate"]["public_header_fail_closed_path"], path)
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
        self.assert_runtime_contract_currentness_closed(
            report["post_runtime_identity_contract_gate"]["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=True,
        )
        self.assert_runtime_contract_currentness_closed(
            report["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=True,
        )
        identity_record_currentness = report["identity_public_contract_decision_record"][
            "runtime_evidence_contract_review_currentness"
        ]
        self.assert_runtime_contract_currentness_closed(identity_record_currentness)
        self.assertTrue(identity_record_currentness["observed"]["runtime_evidence_binding_valid"])
        self.assertTrue(identity_record_currentness["observed"]["record_accepted_for_contract_review"])
        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertTrue(post_runtime_gap["approved_runtime_bundle_consumed"])
        self.assertEqual(
            post_runtime_gap["approved_runtime_evidence_scope"],
            "consume_only_contract_review_input",
        )
        self.assertEqual(
            post_runtime_gap["runtime_bundle_consumed_decision_keys"],
            checker.POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS,
        )
        self.assertEqual(post_runtime_gap["missing_identity_contract_review_decision_keys"], [])
        self.assertEqual(
            post_runtime_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertFalse(post_runtime_gap["candidate_preflight_review_aliases_count"])
        for key in checker.REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
            self.assertNotIn(key, post_runtime_gap["smallest_remaining_public_identity_decision_keys"])
        self.assertNotIn(
            "permissions_admin_contract_blocker",
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
        )
        self.assertIn("plugin_hub", post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"])
        self.assertIn("stable_sdk", post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"])
        self.assert_post_runtime_gap_summary_closed(post_runtime_gap)
        self.assertEqual(
            report["identity_public_contract_decision_record"]["checkable_next_step"]["required_source_artifact_hash_state"],
            "current",
        )
        self.assertEqual(
            report["identity_public_contract_decision_record"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["identity_public_contract_decision_record"]["public_header_gate_ready"])
        self.assertFalse(report["identity_public_contract_decision_record"]["public_header_gate_unlocked"])
        self.assertFalse(report["identity_public_contract_decision_record"]["stable_claim_ready"])
        self.assertFalse(report["identity_public_contract_decision_record"]["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["identity_public_contract_decision_record"]["p0_progress_ready"])
        self.assertFalse(report["identity_public_contract_decision_record"]["sdk_p0_progress_ready"])
        self.assertEqual(
            report["identity_public_contract_decision_record"]["p0_dependency_chain_claim_progress_contribution"],
            0,
        )
        self.assertIn("public_header_gate_blocked_by_identity_public_contract_gate", report["blockers"])
        self.assertEqual(set(report["blockers"]), {"public_header_gate_blocked_by_identity_public_contract_gate"})
        self.assertNotIn("approved_runtime_evidence_required_before_header_gate", report["blockers"])
        self.assertNotIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
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
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_complete_sdk_claim",
            "counts_toward_p0_dependency_chain_claim",
            "public_or_runtime_accounting_allowed",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_accepted_runtime_evidence_reports_exact_remaining_contract_keys_consume_only(self) -> None:
        runtime_evidence = approved_runtime_manifest()

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["approved_runtime_evidence"]["accepted_for_header_gate_review"])
        self.assertFalse(report["header_gate_review_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(set(report["blockers"]), {"public_header_gate_blocked_by_identity_public_contract_gate"})

        post_runtime_gap = report["post_runtime_public_identity_gap_summary"]
        self.assertTrue(post_runtime_gap["active"])
        self.assertEqual(post_runtime_gap["current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(post_runtime_gap["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            post_runtime_gap["only_valid_post_runtime_route"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(post_runtime_gap["candidate_preflight_review_aliases_count"])
        self.assert_runtime_contract_currentness_closed(
            report["post_runtime_identity_contract_gate"]["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=False,
        )
        self.assert_runtime_contract_currentness_closed(
            report["runtime_evidence_contract_review_currentness"],
            runtime_accepted=True,
            reviewed_record_accepted=False,
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
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["remaining_public_header_decision_keys"],
            checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        self.assertEqual(
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS
            + checker.POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS,
        )
        for consumed_key in checker.POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS:
            self.assertNotIn(consumed_key, post_runtime_gap["smallest_remaining_public_identity_decision_keys"])
        for downstream_key in (
            "permissions_admin_contract_blocker",
            "command_chat_response_contract_blocker",
            "commands_replies_contract_blocker",
            "player_lookup_exclusion_review",
            "storage_persistence_exclusion_review",
        ):
            self.assertIn(downstream_key, post_runtime_gap["deferred_downstream_surface_gaps"])
            self.assertNotIn(downstream_key, post_runtime_gap["smallest_remaining_public_identity_decision_keys"])
        self.assertIn("storage_persistence", post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"])
        self.assertIn("plugin_hub", post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"])
        self.assertIn("stable_sdk", post_runtime_gap["downstream_surfaces_deferred_until_identity_promotion"])
        self.assert_post_runtime_gap_summary_closed(post_runtime_gap)

        post_runtime_gate = report["post_runtime_identity_contract_gate"]
        self.assertEqual(
            post_runtime_gate["smallest_remaining_public_identity_decision_keys"],
            post_runtime_gap["smallest_remaining_public_identity_decision_keys"],
        )
        self.assertEqual(
            post_runtime_gate["offline_preparation"],
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        )
        self.assertEqual(
            post_runtime_gate["offline_preparation"]["next_blocker_after_resolved_input"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(post_runtime_gate["permissions_admin_ready"])
        self.assertFalse(post_runtime_gate["command_chat_response_ready"])
        self.assertFalse(post_runtime_gate["commands_replies_ready"])
        self.assertFalse(post_runtime_gate["lookup_ready"])
        self.assertFalse(post_runtime_gate["storage_persistence_ready"])
        self.assertFalse(post_runtime_gate["stable_ready"])
        self.assertFalse(post_runtime_gate["stable_claim_allowed"])
        self.assertFalse(post_runtime_gate["stable_claim_ready"])
        self.assertFalse(post_runtime_gate["stable_sdk_ready"])
        self.assertFalse(post_runtime_gate["plugin_hub_ready"])
        self.assertFalse(post_runtime_gate["plugin_hub_publication_ready"])
        self.assertFalse(post_runtime_gate["publication_ready"])
        self.assertFalse(post_runtime_gate["publication_authorized"])
        self.assertFalse(post_runtime_gate["sdk_p0_progress_ready"])

    def test_rejects_public_header_proposal_as_runtime_evidence_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        proposal_path = (
            "docs/research/player-identity-planning-sources/"
            "player-identity-public-header-gate-proposal.json"
        )
        runtime_evidence["output_artifact_identity"]["evidence_pack_id"] = (
            "player-identity-public-header-gate-proposal"
        )
        runtime_evidence["source_summary"]["evidence"]["sources"][0]["path"] = proposal_path
        runtime_evidence["operational_window"]["copied_log"]["path"] = proposal_path

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=self.record_bound_to(runtime_evidence),
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["post_runtime_identity_contract_gate"]["active_after_approved_runtime_evidence"])
        self.assertIn("approved_runtime_evidence_not_accepted_for_header_gate", report["blockers"])
        runtime_gate_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_not_accepted_for_header_gate"
        )
        self.assertIn(
            "approved_runtime_evidence_non_promotional_sources_claimed",
            runtime_gate_detail["runtime_blockers"],
        )
        self.assertFalse(report["post_runtime_identity_contract_gate"]["record_bound_to_accepted_runtime_evidence"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_stale_reviewed_contract_record_before_header_gate_review(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        stale_record = self.record_bound_to(runtime_evidence)
        stale_record["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=stale_record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertEqual(
            report["identity_public_contract_decision_record"]["source_artifact_freshness"]["status"],
            "stale_or_mismatched",
        )
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        self.assertIn(
            "source_artifact_hash_mismatch",
            report["identity_public_contract_decision_record"]["blockers"],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_reviewed_record_not_bound_to_accepted_runtime_evidence_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["approved_runtime_evidence_binding"]["artifact_sha256"] = "c" * 64

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
            report["blockers"],
        )
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        self.assertFalse(record_report["runtime_evidence_binding_valid"])
        self.assertFalse(record_report["bound_to_accepted_runtime_evidence"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_reviewed_record_shortcut_aliases_and_stale_source_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["reviewedHashCurrentContractReviewOnly"] = True
        record["review_metadata"] = {
            "acceptedRoute": "public_header_gate_missing",
            "runtimeEvidenceRoute": "public_sdk_ready",
            "stable_note": "stable SDK is ready",
        }
        record["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertEqual(
            report["identity_public_contract_decision_record"]["source_artifact_freshness"]["status"],
            "stale_or_mismatched",
        )
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_blockers = set(report["identity_public_contract_decision_record"]["blockers"])
        for blocker in (
            "reviewed_hash_current_contract_review_shortcut_alias_present",
            "route_shortcut_alias_mismatch",
            "source_artifact_hash_mismatch",
            "public_text_or_source_overclaim",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, record_blockers)
        self.assertEqual(
            report["identity_public_contract_decision_record"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        path = report["post_runtime_public_header_fail_closed_path"]
        self.assertEqual(report["post_runtime_identity_contract_gate"]["public_header_fail_closed_path"], path)
        self.assertEqual(report["public_header_gate_missing"]["fail_closed_path"], path)
        self.assertTrue(path["active_after_strict_approved_runtime_evidence"])
        self.assertFalse(path["active_after_accepted_reviewed_identity_contract"])
        self.assertEqual(path["status"], "blocked_until_reviewed_identity_public_contract_decision_record")
        self.assertEqual(path["next_fail_closed_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            path["next_required_artifact"],
            checker.REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        self.assertEqual(path["required_sequence"][1]["status"], "missing_or_not_accepted")
        self.assertEqual(path["required_sequence"][2]["status"], "blocked_until_reviewed_identity_contract")
        self.assertFalse(path["shortcut_aliases_allowed"])
        self.assertFalse(path["public_header_allowed"])
        self.assertFalse(path["public_sdk_ready"])
        self.assertFalse(path["runtime_ready"])
        self.assertEqual(path["p0_dependency_chain_claim_progress_contribution"], 0)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["stable_claim_ready"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_reviewed_record_stale_runtime_and_p0_aliases_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["review_metadata"] = {
            "source_artifact_hash_state": "stale",
            "accepted_runtime_evidence": "accepted",
            "runtimeEvidenceSatisfiesIdentityContractGate": True,
            "sdkP0ProgressReady": True,
            "p0Progress": "25%",
        }

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_blockers = set(report["identity_public_contract_decision_record"]["blockers"])
        for blocker in (
            "stale_hash_current_contract_alias_present",
            "runtime_evidence_shortcut_alias_present",
            "p0_progress_alias_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, record_blockers)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_reviewed_record_identity_contract_gate_alias_cleared_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["review_metadata"] = {
            "identity_public_contract_gate_missing": False,
            "publicHeaderGateMissingAfterRuntimeEvidence": True,
            "accepted_for_identity_public_contract_gate_review": True,
        }

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_blockers = set(report["identity_public_contract_decision_record"]["blockers"])
        self.assertIn("identity_public_contract_gate_missing_alias_not_true", record_blockers)
        self.assertIn("downstream_gate_missing_alias_not_false", record_blockers)
        self.assertIn("claim_alias_not_false", record_blockers)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["accepted_for_identity_public_contract_gate_review"])
        self.assertTrue(report["post_runtime_identity_contract_gate"]["post_runtime_identity_contract_gate_missing"])
        self.assertFalse(report["post_runtime_identity_contract_gate"]["identity_public_contract_gate_ready"])
        self.assertFalse(report["post_runtime_identity_contract_gate"]["identity_public_contract_gate_unlocked"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_reviewed_record_header_sdk_runtime_alias_flags_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["public_header_allowed"] = True
        record["review_metadata"] = {
            "public_sdk_ready": True,
            "runtime_ready": True,
        }

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        self.assertIn("claim_alias_not_false", report["identity_public_contract_decision_record"]["blockers"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_partial_hash_claims_in_reviewed_contract_record_before_header_gate_review(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        current = record["source_artifacts"]["public_contract_decisions"]["sha256"]
        record["source_artifacts"]["public_contract_decisions"]["sha256_prefix"] = current[:12]

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        self.assertIn(
            "source_artifact_partial_or_extra_hash_claimed",
            report["identity_public_contract_decision_record"]["blockers"],
        )

    def test_rejects_non_contract_review_only_record_before_header_gate_review(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["decisions"][
            "identity_public_contract.reviewed_copied_opaque_principal_pod_abi"
        ]["scope"] = "public_header_review"

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(report["approved_runtime_evidence"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["accepted_for_contract_review"])
        self.assertFalse(report["identity_public_contract_decision_record"]["contract_review_only"])
        self.assertFalse(
            report["identity_public_contract_decision_record"]["reviewed_hash_current_contract_review_only"]
        )
        self.assertTrue(report["identity_public_contract_decision_record"]["hash_bound_to_current_source_artifacts"])
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        self.assertIn(
            "decision_entry_scope_mismatch",
            report["identity_public_contract_decision_record"]["blockers"],
        )
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])

    def test_rejects_reviewed_record_template_or_downstream_certificate_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["review_metadata"] = {
            "artifact_kind": "reviewed identity public contract decision record template",
            "permissions_certificate": "permissions/admin approval certificate",
            "command_response_certificate": "commands replies completion certificate",
        }

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_blockers = set(report["identity_public_contract_decision_record"]["blockers"])
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_template_or_certificate_artifact_claimed",
            record_blockers,
        )
        detail = next(
            blocker
            for blocker in report["identity_public_contract_decision_record"].get("blocker_details", [])
            if blocker["reason"]
            == "reviewed_identity_public_contract_decision_record_template_or_certificate_artifact_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("reviewed identity public contract decision record template", values)
        self.assertIn("permissions_certificate", values)
        self.assertIn("command_response_certificate", values)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])

    def test_accepts_reviewed_contract_review_metadata_but_not_header_readiness(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
        }

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_report = report["identity_public_contract_decision_record"]
        self.assertTrue(record_report["accepted_for_contract_review"])
        self.assertTrue(record_report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(record_report["accepted_for_header_gate_review"])
        self.assertFalse(report["header_gate_review_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_reviewed_record_transition_integrity_claims_before_header_gate(self) -> None:
        runtime_evidence = approved_runtime_manifest()
        record = self.record_bound_to(runtime_evidence)
        record["review_metadata"] = {
            "next_blocker": "public_header_gate_missing",
            "v1_dependency_chain_position": 2,
            "proposed_header_symbols": [
                "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
                "RegisterPlayerIdentityEventWithOwnerTokenHandle",
            ],
        }
        record["notes"] = ["public ABI carries principal handles before ResourceHandle promotion"]

        result = self.run_checker(
            self.proposal(),
            approved_runtime_evidence=runtime_evidence,
            identity_public_contract_decision_record=record,
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            report["blockers"],
        )
        record_report = report["identity_public_contract_decision_record"]
        self.assertFalse(record_report["accepted_for_contract_review"])
        for blocker in (
            "blocker_id_mismatch",
            "dependency_chain_position_claimed_before_promotion",
            "stale_proposed_header_symbols_claimed",
            "public_text_or_source_overclaim",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, record_report["blockers"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])

    def test_promotion_modes_fail_closed(self) -> None:
        for arg, blocker in (
            ("--promote", "promote_blocked_until_runtime_bundle_and_header_promotion"),
            ("--public-readiness", "public_readiness_blocked_until_runtime_bundle_and_header_promotion"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_runtime_bundle_and_header_promotion"),
        ):
            with self.subTest(arg=arg):
                result = self.run_checker(self.proposal(), extra_args=[arg], check=False)
                report = json.loads(result.stdout)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(blocker, report["blockers"])
                self.assertFalse(report["ready"])
                self.assertFalse(report["accepted_for_header_gate_review"])
                for key in checker.FALSE_FLAGS:
                    with self.subTest(arg=arg, key=key):
                        self.assertFalse(report[key])

    def test_promotion_keeps_nonzero_sequence_and_epoch_contract_text(self) -> None:
        result = self.run_checker(self.proposal(), extra_args=["--promote"], check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promote_blocked_until_runtime_bundle_and_header_promotion", report["blockers"])
        self.assertNotIn("promotion_event_sequence_nonzero_contract_missing", report["blockers"])
        self.assertNotIn("promotion_server_process_epoch_nonzero_contract_missing", report["blockers"])
        for key in checker.FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_promotion_rejects_missing_nonzero_sequence_and_epoch_contract_text(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["sequence_policy"].remove(
            "event_sequence is nonzero for every delivered player-principal event"
        )
        candidate["sequence_policy"].remove(
            "event_sequence value 0 is invalid for public-header promotion"
        )
        candidate["server_process_epoch_policy"].remove(
            "server_process_epoch is nonzero for every delivered player-principal event"
        )
        candidate["server_process_epoch_policy"].remove(
            "server_process_epoch value 0 is invalid for public-header promotion"
        )

        result = self.run_checker(
            self.proposal(),
            public_contract_decisions=decisions,
            extra_args=["--promote"],
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promotion_event_sequence_nonzero_contract_missing", report["blockers"])
        self.assertIn("promotion_server_process_epoch_nonzero_contract_missing", report["blockers"])
        sequence_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "promotion_event_sequence_nonzero_contract_missing"
        )
        epoch_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "promotion_server_process_epoch_nonzero_contract_missing"
        )
        self.assertIn(
            "event_sequence is nonzero for every delivered player-principal event",
            sequence_detail["missing"],
        )
        self.assertIn(
            "event_sequence value 0 is invalid for public-header promotion",
            sequence_detail["missing"],
        )
        self.assertIn(
            "server_process_epoch is nonzero for every delivered player-principal event",
            epoch_detail["missing"],
        )
        self.assertIn(
            "server_process_epoch value 0 is invalid for public-header promotion",
            epoch_detail["missing"],
        )
        for key in checker.FALSE_FLAGS:
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_rejects_contract_decision_sequence_epoch_or_descriptor_drift(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["candidate_event_payload_fields_or_equivalent"].remove("event_sequence")
        candidate["candidate_descriptor_fields_or_equivalent"].remove("contract_flags")
        candidate["sequence_policy"].remove("event_sequence is process-local and non-persistent")
        candidate["server_process_epoch_policy"].remove(
            "server_process_epoch invalidates process-local principal handles after restart"
        )

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "contract_candidate_event_payload_fields_missing",
            "contract_candidate_descriptor_fields_missing",
            "contract_candidate_event_sequence_policy_missing",
            "contract_candidate_server_process_epoch_policy_missing",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_runtime_evidence_sufficiency_weakened(self) -> None:
        decisions = self.decisions()
        decisions["approved_runtime_evidence_not_sufficient"]["why"].remove(
            "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims"
        )
        decisions["approved_runtime_evidence_not_sufficient"]["minimum_additional_gates"].remove(
            "named capability and owner-token lifecycle policy reviewed"
        )

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved_runtime_evidence_not_sufficient_why_missing", report["blockers"])
        self.assertIn("approved_runtime_evidence_not_sufficient_minimum_gates_missing", report["blockers"])

    def test_rejects_post_runtime_evidence_gate_public_readiness_claims(self) -> None:
        decisions = self.decisions()
        gate = decisions["post_approved_runtime_evidence_gate"]
        gate["reported_current_blocker"] = "public_header_ready"
        gate["next_blocker"] = "public_header_ready"
        gate["public_header_allowed"] = True
        gate["public_contract_allowed"] = True
        gate["public_readiness"] = True
        gate["public_abi_ready"] = True
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
        gate["resource_handle_ready"] = True
        gate["resource_handle_supported"] = True
        gate["runtime_readiness"] = True
        gate["runtime_capture_authorized"] = True
        gate["v1_completion_evidence"] = True
        gate["non_claim"] = "public header is ready"

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "post_approved_runtime_evidence_gate_reported_current_blocker_mismatch",
            "post_approved_runtime_evidence_gate_next_blocker_mismatch",
            "post_approved_runtime_evidence_gate_public_header_allowed_not_false",
            "post_approved_runtime_evidence_gate_public_contract_allowed_not_false",
            "post_approved_runtime_evidence_gate_public_readiness_not_false",
            "post_approved_runtime_evidence_gate_public_abi_ready_not_false",
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
            "post_approved_runtime_evidence_gate_resource_handle_ready_not_false",
            "post_approved_runtime_evidence_gate_resource_handle_supported_not_false",
            "post_approved_runtime_evidence_gate_runtime_readiness_not_false",
            "post_approved_runtime_evidence_gate_runtime_capture_authorized_not_false",
            "post_approved_runtime_evidence_gate_v1_completion_evidence_not_false",
            "post_approved_runtime_evidence_gate_non_claim_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_contract_gate_inputs_unlocking_public_header_or_p0(self) -> None:
        decisions = self.decisions()
        runtime_input = next(
            item for item in decisions["contract_gate_inputs"] if item["id"] == "runtime.lifecycle_evidence"
        )
        runtime_input["status"] = "resolved"
        runtime_input["remaining_promotion_inputs"] = ["public_header_ready"]
        runtime_input["promotion_ready"] = True
        runtime_input["public_sdk_ready"] = True
        runtime_input["public_header_allowed"] = True
        runtime_input["v1_completion_evidence"] = True

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        for blocker in (
            "contract_gate_input_not_unresolved",
            "contract_gate_input_remaining_promotion_inputs_mismatch",
            "contract_gate_input_flag_promotion_ready_not_false",
            "contract_gate_input_flag_public_sdk_ready_not_false",
            "contract_gate_input_flag_public_header_allowed_not_false",
            "contract_gate_input_flag_v1_completion_evidence_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_off_header_abi_candidate_public_callback_or_downstream_claims(self) -> None:
        decisions = self.decisions()
        candidate = decisions["proposed_public_pod_abi_candidate"]
        candidate["status"] = "public"
        candidate["candidate_only"] = False
        candidate["public_sdk_ready"] = True
        candidate["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS"]
        candidate["callback_abi_ready"] = True
        candidate["permissions_ready"] = True
        candidate["commands_ready"] = True
        candidate["sdk_p0_progress"] = True
        candidate["p0_progress_ready"] = True
        candidate["counts_toward_p0_dependency_chain_claim"] = True

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("off_header_abi_candidate_status_not_proposal_only", report["blockers"])
        self.assertIn("off_header_abi_candidate_only_not_true", report["blockers"])
        self.assertIn("off_header_abi_candidate_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("off_header_abi_candidate_public_or_downstream_claim", report["blockers"])
        claim_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "off_header_abi_candidate_public_or_downstream_claim"
        }
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.public_capability_bits_now", claim_paths)
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.callback_abi_ready", claim_paths)
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.permissions_ready", claim_paths)
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.commands_ready", claim_paths)
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.sdk_p0_progress", claim_paths)
        self.assertIn("$.public_contract_decisions.proposed_public_pod_abi_candidate.p0_progress_ready", claim_paths)
        self.assertIn(
            "$.public_contract_decisions.proposed_public_pod_abi_candidate.counts_toward_p0_dependency_chain_claim",
            claim_paths,
        )

    def test_rejects_stale_public_contract_decisions_source_artifact_hash(self) -> None:
        decisions = self.decisions()
        decisions["ignored_test_note"] = "semantics unchanged stale source artifact"

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_contract_decisions_source_artifact_hash_mismatch", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "public_contract_decisions_source_artifact_hash_mismatch"
        )
        self.assertEqual(detail["expected_path"], str(DECISIONS))
        self.assertNotEqual(detail["expected_sha256"], detail["observed_sha256"])

    def test_rejects_non_counting_source_artifacts_for_header_gate(self) -> None:
        payload = self.proposal()
        payload["source_artifacts"]["support_package_alias"] = (
            "docs/research/plugin-hub-package-shape-support-tier-ready.json"
        )
        payload["source_artifacts"]["runtime_window_planning"] = (
            "docs/research/player-principal-runtime-window-planning-report.json"
        )
        payload["source_artifacts"]["passive_extended_monitor_log"] = (
            "docs/research/extended-passive-monitor-snapshot.log"
        )
        payload["source_artifacts"]["runtime_presence_snapshot"] = (
            "docs/research/runtime-presence-snapshot.json"
        )
        payload["source_artifacts"]["no_users_status"] = "docs/research/no-users-status.json"
        payload["source_artifacts"]["post_reboot_passive_monitor_context"] = (
            "docs/research/player-principal-post-reboot-passive-monitor-context.json"
        )
        payload["source_artifacts"]["confirmed_beta_notice_json"] = (
            "docs/research/player-principal-confirmed-beta-notice.json"
        )
        payload["source_artifacts"]["next_action_status_report"] = (
            "docs/research/player-principal-next-action-status-report.json"
        )
        payload["source_artifacts"]["copied_log_only_artifact"] = (
            "docs/research/player-principal-copied-log-only-artifact.json"
        )
        payload["source_artifacts"]["approved_manifest_ready_alias"] = (
            "docs/research/identity-public-contract-approved-manifest-ready-alias.json"
        )
        payload["source_artifacts"]["principal_start_end_runtime_evidence"] = (
            "docs/research/principal-start-end-runtime-evidence.json"
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_artifacts_mismatch", report["blockers"])
        self.assertIn("source_artifacts_non_counting_or_public_shortcut_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_non_counting_or_public_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("support_package_alias", values)
        self.assertIn("docs/research/plugin-hub-package-shape-support-tier-ready.json", values)
        self.assertIn("runtime_window_planning", values)
        self.assertIn("docs/research/player-principal-runtime-window-planning-report.json", values)
        self.assertIn("passive_extended_monitor_log", values)
        self.assertIn("docs/research/extended-passive-monitor-snapshot.log", values)
        self.assertIn("runtime_presence_snapshot", values)
        self.assertIn("docs/research/runtime-presence-snapshot.json", values)
        self.assertIn("no_users_status", values)
        self.assertIn("docs/research/no-users-status.json", values)
        self.assertIn("post_reboot_passive_monitor_context", values)
        self.assertIn("docs/research/player-principal-post-reboot-passive-monitor-context.json", values)
        self.assertIn("confirmed_beta_notice_json", values)
        self.assertIn("docs/research/player-principal-confirmed-beta-notice.json", values)
        self.assertIn("next_action_status_report", values)
        self.assertIn("docs/research/player-principal-next-action-status-report.json", values)
        self.assertIn("copied_log_only_artifact", values)
        self.assertIn("docs/research/player-principal-copied-log-only-artifact.json", values)
        self.assertIn("approved_manifest_ready_alias", values)
        self.assertIn("docs/research/identity-public-contract-approved-manifest-ready-alias.json", values)
        self.assertIn("principal_start_end_runtime_evidence", values)
        self.assertIn("docs/research/principal-start-end-runtime-evidence.json", values)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_start_end_only_runtime_report_before_header_gate(self) -> None:
        runtime_report = {
            "accepted_for_contract_review": True,
            "resolved_input": "runtime.lifecycle_evidence",
            "resolved_inputs": [
                "runtime.lifecycle_evidence",
                "runtime.lifecycle_start_end_evidence",
            ],
            "ready_scope": "principal_start_end_runtime_evidence_only",
            "next_blocker": checker.NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "accepted_for_header_gate_review": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
        }
        blockers: list[dict] = []

        with mock.patch.object(
            checker.public_contract_gap_report,
            "validate_approved_runtime_evidence",
            return_value=runtime_report,
        ):
            report = checker.validate_approved_runtime_evidence_for_header_gate(
                Path("principal-start-end-runtime-evidence.json"),
                blockers,
            )

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertIn(
            "approved_runtime_evidence_not_accepted_for_header_gate",
            [blocker["reason"] for blocker in blockers],
        )
        detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_not_accepted_for_header_gate"
        )
        self.assertEqual(
            detail["resolved_inputs"],
            ["runtime.lifecycle_evidence", "runtime.lifecycle_start_end_evidence"],
        )
        self.assertEqual(detail["ready_scope"], "principal_start_end_runtime_evidence_only")

    def test_rejects_runtime_report_without_strict_lifecycle_checker_acceptance(self) -> None:
        runtime_report = self.accepted_runtime_report()
        strict_report = strict_approved_runtime_check_report(
            consumer_cases=[
                "malformed_or_unsupported_evidence",
                "stale_after_logout",
            ],
            consumer_boundary_assertions=[
                "malformed_or_unsupported_evidence",
                "stale_after_logout",
            ],
            blocker_details=[],
        )
        strict_report["strict_lifecycle_triplet_selected"] = False
        strict_report["strict_lifecycle_triplet_selection"]["accepted"] = False
        strict_report["strict_lifecycle_triplet_selection"]["blockers"] = [
            "strict_lifecycle_triplet_missing"
        ]
        blockers: list[dict] = []

        class AcceptedValidation:
            blockers: list[dict] = []

        with (
            mock.patch.object(
                checker.public_contract_gap_report,
                "validate_approved_runtime_evidence",
                return_value=runtime_report,
            ),
            mock.patch.object(
                checker.public_contract_gap_report.approved_runtime_evidence,
                "load_json",
                return_value=approved_runtime_manifest(),
            ),
            mock.patch.object(
                checker.public_contract_gap_report.approved_runtime_evidence,
                "validate_manifest",
                return_value=AcceptedValidation(),
            ),
            mock.patch.object(
                checker.public_contract_gap_report.approved_runtime_evidence,
                "build_report",
                return_value=strict_report,
            ),
        ):
            report = checker.validate_approved_runtime_evidence_for_header_gate(
                Path("approved-runtime-evidence.json"),
                blockers,
            )

        self.assertFalse(report["accepted_for_contract_review"])
        blocker_reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn(
            "approved_runtime_evidence_strict_checker_report_strict_lifecycle_triplet_selected_not_true_for_header_gate",
            blocker_reasons,
        )
        self.assertIn(
            "approved_runtime_evidence_strict_checker_report_lifecycle_triplet_accepted_mismatch_for_header_gate",
            blocker_reasons,
        )
        self.assertIn(
            "approved_runtime_evidence_not_accepted_for_header_gate",
            blocker_reasons,
        )

    def test_rejects_accepted_runtime_evidence_report_overclaim_aliases_as_consume_only(self) -> None:
        runtime_report = self.accepted_runtime_report()
        runtime_report["route_aliases"] = {
            "pluginHubReady": True,
            "stableSdkReady": True,
            "storagePersistenceReady": True,
            "permissionsAdminUnlocked": True,
            "commandsRepliesUnlocked": True,
            "lookupAllowed": True,
            "publicSdkReady": True,
            "sdkP0ProgressReady": True,
            "p0DependencyChainClaimProgressContribution": 1,
        }
        blockers: list[dict] = []

        with mock.patch.object(
            checker.public_contract_gap_report,
            "validate_approved_runtime_evidence",
            return_value=runtime_report,
        ):
            report = checker.validate_approved_runtime_evidence_for_header_gate(
                Path("approved-runtime-evidence.json"),
                blockers,
            )

        self.assertFalse(report["accepted_for_contract_review"])
        blocker_reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("approved_runtime_evidence_consume_only_alias_not_false", blocker_reasons)
        self.assertIn("approved_runtime_evidence_consume_only_progress_not_zero", blocker_reasons)
        self.assertIn("approved_runtime_evidence_not_accepted_for_header_gate", blocker_reasons)
        alias_detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_consume_only_alias_not_false"
        )
        alias_paths = {claim["path"] for claim in alias_detail["claims"]}
        for path in (
            "$.approved_runtime_evidence.route_aliases.pluginHubReady",
            "$.approved_runtime_evidence.route_aliases.stableSdkReady",
            "$.approved_runtime_evidence.route_aliases.storagePersistenceReady",
            "$.approved_runtime_evidence.route_aliases.permissionsAdminUnlocked",
            "$.approved_runtime_evidence.route_aliases.commandsRepliesUnlocked",
            "$.approved_runtime_evidence.route_aliases.lookupAllowed",
            "$.approved_runtime_evidence.route_aliases.publicSdkReady",
            "$.approved_runtime_evidence.route_aliases.sdkP0ProgressReady",
        ):
            with self.subTest(path=path):
                self.assertIn(path, alias_paths)
        zero_detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_consume_only_progress_not_zero"
        )
        self.assertEqual(
            {claim["path"] for claim in zero_detail["claims"]},
            {"$.approved_runtime_evidence.route_aliases.p0DependencyChainClaimProgressContribution"},
        )

    def test_rejects_approved_runtime_lifecycle_positive_public_identity_aliases_consume_only(self) -> None:
        runtime_report = self.accepted_runtime_report()
        runtime_report["derived_only_from_approved_runtime_lifecycle_evidence"] = {
            "public_header_ready": True,
            "public_sdk_ready": True,
            "identity_ready": True,
            "sdk_p0_progress_ready": False,
            "p0_dependency_chain_claim_progress_contribution": 0,
        }
        blockers: list[dict] = []

        with mock.patch.object(
            checker.public_contract_gap_report,
            "validate_approved_runtime_evidence",
            return_value=runtime_report,
        ):
            report = checker.validate_approved_runtime_evidence_for_header_gate(
                Path("approved-runtime-evidence.json"),
                blockers,
            )

        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)
        blocker_reasons = {blocker["reason"] for blocker in blockers}
        self.assertIn("approved_runtime_evidence_consume_only_alias_not_false", blocker_reasons)
        self.assertIn("approved_runtime_evidence_not_accepted_for_header_gate", blocker_reasons)
        alias_detail = next(
            blocker
            for blocker in blockers
            if blocker["reason"] == "approved_runtime_evidence_consume_only_alias_not_false"
        )
        alias_paths = {claim["path"] for claim in alias_detail["claims"]}
        for path in (
            "$.approved_runtime_evidence.derived_only_from_approved_runtime_lifecycle_evidence.public_header_ready",
            "$.approved_runtime_evidence.derived_only_from_approved_runtime_lifecycle_evidence.public_sdk_ready",
            "$.approved_runtime_evidence.derived_only_from_approved_runtime_lifecycle_evidence.identity_ready",
        ):
            with self.subTest(path=path):
                self.assertIn(path, alias_paths)

    def test_rejects_public_header_abi_api_source_shortcuts_for_header_gate(self) -> None:
        payload = self.proposal()
        payload["source_artifacts"]["public_abi_preflight_candidate"] = (
            "docs/research/player-identity-public-header-shortcut.json"
        )
        payload["source_artifacts"]["owner_token_sdk_consumer_contract"] = (
            "docs/research/player-identity-public-abi-promotion-shortcut.json"
        )
        payload["source_artifacts"]["reviewed_identity_public_contract_decision_record"] = (
            "docs/research/player-identity-public-api-readiness-status-report.json"
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_artifacts_mismatch", report["blockers"])
        self.assertIn("source_artifacts_non_counting_or_public_shortcut_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_non_counting_or_public_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("docs/research/player-identity-public-header-shortcut.json", values)
        self.assertIn("docs/research/player-identity-public-abi-promotion-shortcut.json", values)
        self.assertIn("docs/research/player-identity-public-api-readiness-status-report.json", values)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_post_runtime_gate_route_extras_for_header_gate(self) -> None:
        decisions = self.decisions()
        decisions["post_approved_runtime_evidence_gate"]["publicHeaderGateOpen"] = False
        decisions["post_approved_runtime_evidence_gate"]["supportTierReady"] = False

        result = self.run_checker(self.proposal(), public_contract_decisions=decisions, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("post_approved_runtime_evidence_gate_unexpected_route_extras", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "post_approved_runtime_evidence_gate_unexpected_route_extras"
        )
        self.assertEqual(detail["unexpected"], ["publicHeaderGateOpen", "supportTierReady"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_overclaim_flags(self) -> None:
        payload = self.proposal()
        payload["public_header_allowed"] = True
        payload["public_abi_ready"] = True
        payload["promotion_ready"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["blockers"])

    def test_rejects_public_header_sdk_runtime_true_flags(self) -> None:
        payload = self.proposal()
        payload["public_header_allowed"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_forbidden_lookup_or_command_symbols(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["api_slots"][0] = "LookupPlayerPrincipalWithOwnerToken"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("api_slots_mismatch", report["blockers"])
        self.assertIn("proposed_symbol_uses_forbidden_surface", report["blockers"])

    def test_allows_only_canonical_negative_lookup_permission_command_symbols(self) -> None:
        result = self.run_checker(self.proposal(), check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_LOOKUP", report["proposed_symbols"])
        self.assertIn(
            "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_PERMISSIONS_OR_COMMANDS_AUTHORITY",
            report["proposed_symbols"],
        )
        self.assertNotIn("proposed_symbol_uses_forbidden_surface", report["blockers"])
        self.assertNotIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        self.assertNotIn("unexpected_claim_alias_value", report["blockers"])
        self.assertNotIn("public_text_or_source_overclaim", report["blockers"])

    def test_rejects_positive_lookup_permission_command_symbol_variants(self) -> None:
        cases = (
            (
                "lookup",
                "no_lookup",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_LOOKUP_READY",
            ),
            (
                "permissions_commands",
                "no_permissions_or_commands_authority",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_PERMISSIONS_OR_COMMANDS_AUTHORITY",
            ),
            (
                "ownership",
                "process_local_principal_handle",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_RESOURCE_OWNERSHIP_READY",
            ),
            (
                "mutation",
                "no_mutation",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_MUTATION_READY",
            ),
            (
                "return_override",
                "no_return_override",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_RETURN_OVERRIDE_READY",
            ),
        )

        for label, candidate_value, symbol in cases:
            with self.subTest(label=label):
                payload = self.proposal()
                contract_group = payload["proposed_header"]["public_constants"]["ordered_groups"][4]
                constant = next(
                    item for item in contract_group["constants"] if item["candidate_value"] == candidate_value
                )
                constant["name"] = symbol

                result = self.run_checker(payload, check=False)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("public_constants_mismatch", report["blockers"])
                self.assertIn("proposed_symbol_uses_forbidden_surface", report["blockers"])
                forbidden_symbols = {
                    blocker["symbol"]
                    for blocker in report["blocker_details"]
                    if blocker["reason"] == "proposed_symbol_uses_forbidden_surface"
                }
                self.assertIn(symbol, forbidden_symbols)
                self.assertFalse(report["lookup_ready"])
                self.assertFalse(report["permissions_ready"])
                self.assertFalse(report["commands_ready"])

    def test_rejects_stale_proposed_header_symbol_names(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["capability_bit"]["name"] = "OBELISK_API_CAPABILITY_PLAYER_IDENTITY"
        payload["proposed_header"]["callback_typedef"] = "ObeliskPlayerIdentityEventCallback"
        payload["proposed_header"]["api_slots"][0] = "RegisterPlayerIdentityEventWithOwnerTokenHandle"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capability_bit_mismatch", report["blockers"])
        self.assertIn("callback_typedef_mismatch", report["blockers"])
        self.assertIn("api_slots_mismatch", report["blockers"])
        self.assertIn("proposed_symbol_uses_stale_player_identity_header_symbol", report["blockers"])
        stale_symbols = {
            blocker["symbol"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "proposed_symbol_uses_stale_player_identity_header_symbol"
        }
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", stale_symbols)
        self.assertIn("ObeliskPlayerIdentityEventCallback", stale_symbols)
        self.assertIn("RegisterPlayerIdentityEventWithOwnerTokenHandle", stale_symbols)
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_public_abi_identity_handle_wording_before_resource_handle(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "public ABI carries principal handles before ResourceHandle promotion",
            "public ABI must not expose principal handles before ResourceHandle promotion",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path = {
            claim["path"]: claim["term"]
            for claim in detail["claims"]
            if claim["term"] == "public_abi_identity_handle_before_resource_handle"
        }
        self.assertEqual(terms_by_path, {"$.review_notes[0]": "public_abi_identity_handle_before_resource_handle"})
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_non_append_only_capability_value(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["capability_bit"]["value"] = "1ull << 11"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capability_bit_mismatch", report["blockers"])

    def test_rejects_non_append_only_capability_anchor(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["capability_bit"]["append_after"] = "OBELISK_API_CAPABILITY_CHAT_EVENTS"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capability_bit_mismatch", report["blockers"])

    def test_rejects_if_public_header_capability_anchor_is_no_longer_latest(self) -> None:
        header_text = HEADER.read_text(encoding="utf-8").replace(
            "#define OBELISK_API_CAPABILITY_TIMERS (1ull << 11)",
            "\n".join(
                [
                    "#define OBELISK_API_CAPABILITY_TIMERS (1ull << 11)",
                    "#define OBELISK_API_CAPABILITY_FUTURE_TEST_ONLY (1ull << 12)",
                ]
            ),
        )

        result = self.run_checker(self.proposal(), header_text=header_text, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("capability_append_after_not_latest_public_capability", report["blockers"])
        self.assertIn("capability_bit_already_used_in_public_header", report["blockers"])
        self.assertIn("capability_bit_not_next_after_public_header", report["blockers"])

    def test_rejects_if_public_header_already_exposes_proposed_symbols(self) -> None:
        header_text = HEADER.read_text(encoding="utf-8") + "\n#define OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS (1ull << 12)\n"

        result = self.run_checker(self.proposal(), header_text=header_text, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_already_exposes_proposed_symbols", report["blockers"])

    def test_rejects_if_public_header_exposes_adjacent_identity_symbols(self) -> None:
        header_text = HEADER.read_text(encoding="utf-8") + "\n".join(
            [
                "",
                "typedef uint64_t ObeliskPrincipalHandle;",
                "uint64_t (*RegisterIdentityEventWithOwnerToken)(uint64_t ownerToken);",
                "bool (*LookupPlayerPrincipal)(uint64_t principalHandle, void* out);",
                "typedef uint64_t ObeliskResourceOwnerHandle;",
                "bool (*CheckPlayerPermission)(uint64_t principalHandle);",
                "bool (*ResolveTribeId)(uint64_t playerHandle);",
                "typedef struct ObeliskMutableResource { uint64_t x; } ObeliskMutableResource;",
                "bool (*MutateResource)(uint64_t resourceToken);",
                "bool (*WriteResource)(uint64_t resourceToken);",
            ]
        )

        result = self.run_checker(self.proposal(), header_text=header_text, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "public_header_identity_or_principal_symbols_detected"
        )
        detected = {item["token"] for item in detail["detected"]}
        self.assertIn("ObeliskPrincipalHandle", detected)
        self.assertIn("RegisterIdentityEventWithOwnerToken", detected)
        self.assertIn("LookupPlayerPrincipal", detected)
        self.assertIn("ObeliskResourceOwnerHandle", detected)
        self.assertIn("CheckPlayerPermission", detected)
        self.assertIn("ResolveTribeId", detected)
        self.assertIn("ObeliskMutableResource", detected)
        self.assertIn("MutateResource", detected)
        self.assertIn("WriteResource", detected)

    def test_rejects_symlinked_inputs_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_proposal = root / "proposal.json"
            real_decisions = root / "player_identity_public_contract_decisions.json"
            real_header = root / "ObeliskApi.h"
            real_proposal.write_text(json.dumps(self.proposal()), encoding="utf-8")
            real_decisions.write_text(json.dumps(self.decisions()), encoding="utf-8")
            real_header.write_text(HEADER.read_text(encoding="utf-8"), encoding="utf-8")

            cases = (
                (
                    "proposal",
                    real_proposal,
                    root / "proposal-link.json",
                    [
                        "--proposal",
                        str(root / "proposal-link.json"),
                        "--public-header",
                        str(real_header),
                        "--public-contract-decisions",
                        str(real_decisions),
                    ],
                    "proposal_path_rejected",
                ),
                (
                    "public_contract_decisions",
                    real_decisions,
                    root / "decisions-link.json",
                    [
                        "--proposal",
                        str(real_proposal),
                        "--public-header",
                        str(real_header),
                        "--public-contract-decisions",
                        str(root / "decisions-link.json"),
                    ],
                    "public_contract_decisions_path_rejected",
                ),
                (
                    "public_header",
                    real_header,
                    root / "header-link.h",
                    [
                        "--proposal",
                        str(real_proposal),
                        "--public-header",
                        str(root / "header-link.h"),
                        "--public-contract-decisions",
                        str(real_decisions),
                    ],
                    "public_header_path_rejected",
                ),
            )

            for label, target, link, args, expected_blocker in cases:
                with self.subTest(label=label):
                    try:
                        link.symlink_to(target)
                    except OSError as exc:
                        self.skipTest(f"symlink creation unavailable: {exc}")

                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), *args, "--json"],
                        check=False,
                        text=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    report = json.loads(result.stdout)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected_blocker, report["blockers"])

    def test_rejects_if_public_header_api_slot_anchor_is_no_longer_latest(self) -> None:
        header_text = HEADER.read_text(encoding="utf-8").replace(
            "    bool (*UnregisterTimerWithOwnerToken)(uint64_t ownerToken, uint64_t timerId);",
            "\n".join(
                [
                    "    bool (*UnregisterTimerWithOwnerToken)(uint64_t ownerToken, uint64_t timerId);",
                    "    bool (*FutureTestOnlyWithOwnerToken)(uint64_t ownerToken);",
                ]
            ),
        )

        result = self.run_checker(self.proposal(), header_text=header_text, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("api_append_after_slot_not_latest_public_api_slot", report["blockers"])

    def test_rejects_if_public_header_api_member_anchor_is_no_longer_latest(self) -> None:
        header_text = HEADER.read_text(encoding="utf-8").replace(
            "    bool (*UnregisterTimerWithOwnerToken)(uint64_t ownerToken, uint64_t timerId);",
            "\n".join(
                [
                    "    bool (*UnregisterTimerWithOwnerToken)(uint64_t ownerToken, uint64_t timerId);",
                    "    uint64_t future_test_only;",
                ]
            ),
        )

        result = self.run_checker(self.proposal(), header_text=header_text, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("api_append_after_slot_not_latest_public_api_member", report["blockers"])

    def test_rejects_reordered_api_slots(self) -> None:
        payload = self.proposal()
        slots = payload["proposed_header"]["api_slots"]
        slots[0], slots[1] = slots[1], slots[0]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("api_slots_mismatch", report["blockers"])

    def test_rejects_missing_public_constant(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["public_constants"]["ordered_groups"][0]["constants"].pop()

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_constants_mismatch", report["blockers"])

    def test_rejects_reordered_public_constants(self) -> None:
        payload = self.proposal()
        constants = payload["proposed_header"]["public_constants"]["ordered_groups"][1]["constants"]
        constants[0], constants[1] = constants[1], constants[0]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_constants_mismatch", report["blockers"])

    def test_rejects_public_constant_value_drift(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["public_constants"]["ordered_groups"][2]["constants"][3]["value"] = "1ull << 4"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_constants_mismatch", report["blockers"])

    def test_rejects_public_constant_duplicate_name(self) -> None:
        payload = self.proposal()
        constants = payload["proposed_header"]["public_constants"]["ordered_groups"][0]["constants"]
        constants[1]["name"] = constants[0]["name"]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_constants_mismatch", report["blockers"])
        self.assertIn("public_constant_name_duplicate", report["blockers"])

    def test_rejects_readiness_alias_claims(self) -> None:
        payload = self.proposal()
        payload["sdk_readiness_alias"] = False
        payload["counts_as_runtime"] = False
        payload["publicHeaderGateReviewed"] = True
        payload["publicHeaderGateOpen"] = True
        payload["identityPublicContractGateOpen"] = True
        payload["identityPublicContractGateResolved"] = True
        payload["identityPublicContractGateCleared"] = True
        payload["identityContractDecisionRecordReviewed"] = True
        payload["reviewedIdentityPublicContract"] = True

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_readiness_claim_alias", report["blockers"])
        self.assertIn("unexpected_contract_review_claim_alias", report["blockers"])
        claim_alias_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_contract_review_claim_alias"
        }
        self.assertIn("$.publicHeaderGateReviewed", claim_alias_paths)
        self.assertIn("$.publicHeaderGateOpen", claim_alias_paths)
        self.assertIn("$.identityPublicContractGateOpen", claim_alias_paths)
        self.assertIn("$.identityPublicContractGateResolved", claim_alias_paths)
        self.assertIn("$.identityPublicContractGateCleared", claim_alias_paths)
        self.assertIn("$.identityContractDecisionRecordReviewed", claim_alias_paths)
        self.assertIn("$.reviewedIdentityPublicContract", claim_alias_paths)

    def test_rejects_nested_string_claim_alias_values(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "publicSdkReady=true",
            {"nested": ["runtimeReady=true", "stableClaimReady=true", "counts_toward_complete_sdk_claim=true"]},
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_claim_alias_value", report["blockers"])
        aliases = {
            blocker["alias"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_claim_alias_value"
        }
        self.assertEqual(
            {"publicSdkReady", "runtimeReady", "stableClaimReady", "counts_toward_complete_sdk_claim"} & aliases,
            {"publicSdkReady", "runtimeReady", "stableClaimReady", "counts_toward_complete_sdk_claim"},
        )
        self.assertFalse(report["stable_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_claim_ready"])

    def test_rejects_split_and_path_nested_claim_aliases(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = {
            "split": [
                {"claim": "public_header", "state": "ready"},
                {"name": "public_abi", "status": "promoted"},
                {"field": "runtime", "value": "authorized"},
                {"property": "identity_public_contract_decision_record", "status": "current"},
                {"claim": "hash_current_identity_public_contract_decision_record", "value": True},
                {"key": "public_header_symbols_now", "values": ["ObeliskPlayerPrincipalEvent"]},
                {"claim": "public_sdk", "status": "blocked"},
            ],
            "nested": {
                "public": {"header": {"state": "ready", "symbols_now": ["ObeliskPlayerPrincipalEvent"]}},
                "stable": {"claim": {"allowed": "yes"}},
                "route_snapshot_provenance": {
                    "source_provenance": "route_snapshot",
                    "status": "accepted",
                },
                "reviewed_contract_metadata_provenance": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
            },
        }

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_split_or_nested_claim_alias"
        }
        for path in (
            "$.review_notes.split[0]",
            "$.review_notes.split[1]",
            "$.review_notes.split[2]",
            "$.review_notes.split[3]",
            "$.review_notes.split[4]",
            "$.review_notes.split[5]",
            "$.review_notes.nested.public.header.state",
            "$.review_notes.nested.public.header.symbols_now",
            "$.review_notes.nested.stable.claim.allowed",
            "$.review_notes.nested.route_snapshot_provenance.status",
            "$.review_notes.nested.reviewed_contract_metadata_provenance.state",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        self.assertNotIn("$.review_notes.split[6]", paths)
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "runtime_ready",
            "stable_ready",
            "stable_claim_allowed",
            "public_sdk_ready",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertEqual(report["public_capability_bits_now"], [])

    def test_rejects_contract_record_and_mutation_aliases_before_header_gate(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = {
            "identityPublicContractDecisionRecordContractReviewOnly": True,
            "reviewedIdentityPublicContractDecisionRecordContractReviewOnly": True,
            "publicContractDecisionRecordReviewed": True,
            "publicContractDecisionRecordHashCurrent": True,
            "publicContractDecisionRecordContractReviewOnly": True,
            "contractReviewOnly": True,
            "mutationAllowed": True,
            "mutableResourceReady": True,
            "returnOverrideAllowed": True,
            "summary": [
                "mutation is allowed",
                "mutable resource API is supported",
                "return override is ready",
            ],
        }

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        self.assertIn("unexpected_downstream_claim_alias", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_split_or_nested_claim_alias"
        }
        for path in (
            "$.review_notes.identityPublicContractDecisionRecordContractReviewOnly",
            "$.review_notes.reviewedIdentityPublicContractDecisionRecordContractReviewOnly",
            "$.review_notes.publicContractDecisionRecordReviewed",
            "$.review_notes.publicContractDecisionRecordHashCurrent",
            "$.review_notes.publicContractDecisionRecordContractReviewOnly",
            "$.review_notes.contractReviewOnly",
            "$.review_notes.mutationAllowed",
            "$.review_notes.returnOverrideAllowed",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        downstream_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_downstream_claim_alias"
        }
        self.assertIn("$.review_notes.mutableResourceReady", downstream_paths)
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "public_api_ready",
            "public_sdk_ready",
            "runtime_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])

    def test_rejects_artifact_marker_downstream_and_api_table_escape_aliases(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = {
            "capabilityNames": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL"],
            "principalCapabilitySymbols": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS"],
            "publicRuntimeMarker": "present",
            "runtimePublicReadinessMarker": True,
            "lookupPlayerPrincipalAvailable": True,
            "permissionsAdminReady": True,
            "adminCommandAliases": ["GrantAdminCommand"],
            "commandReplySymbols": ["ObeliskCommandReply"],
            "resourceHandleSymbols": ["ObeliskResourceHandle"],
            "writableResourceReady": True,
            "writeableResourceSupported": True,
            "returnOverrideSymbols": ["ObeliskReturnOverride"],
            "copiedApiTableEscapeHatch": "available",
            "copied_api_table_runtime_escape": True,
            "strings": [
                "OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS is available",
                "writable resource API is supported",
                "command reply API is supported",
                "copied API table allows CallProcessEvent after init",
                "copied API table does not allow CallProcessEvent after init",
            ],
        }

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_public_artifact_claim_alias", report["blockers"])
        self.assertIn("unexpected_readiness_claim_alias", report["blockers"])
        self.assertIn("unexpected_downstream_claim_alias", report["blockers"])
        self.assertIn("unexpected_api_table_escape_hatch_claim_alias", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])

        artifact_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_public_artifact_claim_alias"
        }
        self.assertIn("$.review_notes.capabilityNames", artifact_paths)
        self.assertIn("$.review_notes.principalCapabilitySymbols", artifact_paths)

        downstream_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_downstream_claim_alias"
        }
        for path in (
            "$.review_notes.lookupPlayerPrincipalAvailable",
            "$.review_notes.permissionsAdminReady",
            "$.review_notes.adminCommandAliases",
            "$.review_notes.commandReplySymbols",
            "$.review_notes.resourceHandleSymbols",
            "$.review_notes.writableResourceReady",
            "$.review_notes.writeableResourceSupported",
            "$.review_notes.returnOverrideSymbols",
        ):
            with self.subTest(path=path):
                self.assertIn(path, downstream_paths)

        api_table_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_api_table_escape_hatch_claim_alias"
        }
        self.assertIn("$.review_notes.copiedApiTableEscapeHatch", api_table_paths)
        self.assertIn("$.review_notes.copied_api_table_runtime_escape", api_table_paths)

        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("public_capability_available", terms_by_path["$.review_notes.strings[0]"])
        self.assertIn("public_mutable_resource_available", terms_by_path["$.review_notes.strings[1]"])
        self.assertIn("public_command_or_reply_available", terms_by_path["$.review_notes.strings[2]"])
        self.assertIn("copied_api_table_escape_hatch", terms_by_path["$.review_notes.strings[3]"])
        self.assertNotIn("$.review_notes.strings[4]", terms_by_path)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_post_runtime_shortcut_aliases_before_header_gate(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = {
            "contract_reviewed": True,
            "identity_contract_hash_current": True,
            "approved": True,
            "approvedAlias": True,
            "approval": "public",
            "header_shape_valid": True,
            "p0_unlocked": "identity",
            "blocker_resolved": "runtime",
            "public": {"surface": {"status": "accepted"}},
            "strings": [
                "approved=true",
                "approved_alias=true",
                "identity_contract_hash_current=true",
                "header_shape_valid=true",
                "p0_unlocked=identity",
                "blocker_resolved=runtime",
            ],
        }

        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        self.assertIn("unexpected_claim_alias_value", report["blockers"])
        paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_split_or_nested_claim_alias"
        }
        for path in (
            "$.review_notes.contract_reviewed",
            "$.review_notes.identity_contract_hash_current",
            "$.review_notes.approved",
            "$.review_notes.approvedAlias",
            "$.review_notes.approval",
            "$.review_notes.header_shape_valid",
            "$.review_notes.p0_unlocked",
            "$.review_notes.blocker_resolved",
            "$.review_notes.public.surface.status",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        aliases = {
            blocker["alias"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_claim_alias_value"
        }
        for alias in (
            "approved",
            "approved_alias",
            "identity_contract_hash_current",
            "header_shape_valid",
            "p0_unlocked",
            "blocker_resolved",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, aliases)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_freeform_public_readiness_text_overclaims(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "public header is ready",
            "approved runtime evidence unlocks public header",
            "reviewed_identity_public_contract_decision_record unlocks public header",
            "LookupPlayerPrincipal is available",
            "player identity lookup surface",
            "ObeliskResourceOwnerHandle is available",
            "CheckPlayerPermission is supported",
            "tribe id lookup is supported",
            "installed SDK package shape is ready",
            "support tier is ready",
            "Plugin Hub publication is published",
            "ObeliskResourceMutation is available",
            "mutable resource API is supported",
            "return override is available",
            "command response API is supported",
            "send-chat command surface is available",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.review_notes[0]", paths)
        self.assertIn("$.review_notes[1]", paths)
        self.assertIn("$.review_notes[2]", paths)
        self.assertIn("$.review_notes[3]", paths)
        self.assertIn("$.review_notes[4]", paths)
        self.assertIn("$.review_notes[5]", paths)
        self.assertIn("$.review_notes[6]", paths)
        self.assertIn("$.review_notes[7]", paths)
        self.assertIn("$.review_notes[8]", paths)
        self.assertIn("$.review_notes[9]", paths)
        self.assertIn("$.review_notes[10]", paths)
        self.assertIn("$.review_notes[11]", paths)
        self.assertIn("$.review_notes[12]", paths)
        self.assertIn("$.review_notes[13]", paths)
        self.assertIn("$.review_notes[14]", paths)
        self.assertIn("$.review_notes[15]", paths)
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("public_header_ready", terms)
        self.assertIn("contract_review_artifact_public_header", terms)
        self.assertIn("public_lookup_or_resource_handle_available", terms)
        self.assertIn("public_ownership_or_permissions_available", terms)
        self.assertIn("broad_identity_lookup_wording", terms)
        self.assertIn("package_shape_readiness", terms)
        self.assertIn("support_tier_ready", terms)
        self.assertIn("plugin_hub_ready", terms)
        self.assertIn("public_mutable_resource_available", terms)
        self.assertIn("return_override_allowed", terms)
        self.assertIn("public_command_or_reply_available", terms)

    def test_rejects_after_runtime_route_shortcuts_before_header_gate(self) -> None:
        payload = self.proposal()
        payload["review_metadata"] = {
            "approvedRuntimePrincipalLifecycleBundleRoutesTo": "permissions/admin",
            "principalStartEndRuntimeEvidenceReady": True,
            "rconReady": True,
            "packageShapeReady": True,
            "pluginHubReady": True,
        }
        payload["review_notes"] = [
            "after accepted runtime lifecycle evidence next blocker is public_header_gate_missing",
            "approved runtime principal lifecycle bundle routes to permissions/admin readiness",
            "runtime lifecycle evidence next blocker is command/chat response",
            "approved runtime lifecycle evidence routes to complete SDK",
            "after accepted runtime lifecycle evidence next blocker is identity_public_contract_gate_missing",
            "accepted runtime lifecycle evidence does not route to public_header_gate_missing",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_readiness_claim_alias", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        alias_paths = {
            blocker["path"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_readiness_claim_alias"
        }
        for path in (
            "$.review_metadata.approvedRuntimePrincipalLifecycleBundleRoutesTo",
            "$.review_metadata.principalStartEndRuntimeEvidenceReady",
            "$.review_metadata.rconReady",
            "$.review_metadata.packageShapeReady",
            "$.review_metadata.pluginHubReady",
        ):
            with self.subTest(path=path):
                self.assertIn(path, alias_paths)
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        for path in (
            "$.review_notes[0]",
            "$.review_notes[1]",
            "$.review_notes[2]",
            "$.review_notes[3]",
        ):
            with self.subTest(path=path):
                self.assertIn("post_runtime_route_shortcut", terms_by_path[path])
        self.assertNotIn("$.review_notes[4]", terms_by_path)
        self.assertNotIn("$.review_notes[5]", terms_by_path)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_promotion_like_public_contract_evidence_wording(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "identity_public_contract_gate_missing is resolved, public header is ready",
            "reviewed identity public contract decision record is sufficient evidence for public contract promotion",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertEqual({"$.review_notes[0]", "$.review_notes[1]"} & paths, {"$.review_notes[0]", "$.review_notes[1]"})
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("public_header_ready", terms)
        self.assertIn("promotion_like_public_contract_evidence", terms)

    def test_rejects_header_shape_contract_review_metadata_and_p0_shortcut_text(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "reviewed hash-current contract-review-only record marks public header readiness satisfied",
            "contract-review-only record unlocks downstream P0",
            "proposal-only header gate shape counts toward P0 unlock",
            "public header proposal shape marks public identity ready",
            "proposal-only header gate shape does not count toward P0 unlock",
        ]

        result = self.run_checker(payload, check=False)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("contract_review_metadata_public_readiness", terms_by_path["$.review_notes[0]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$.review_notes[1]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$.review_notes[2]"])
        self.assertIn("header_shape_public_readiness_shortcut", terms_by_path["$.review_notes[3]"])
        self.assertNotIn("$.review_notes[4]", terms_by_path)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])

    def test_rejects_non_counting_operational_artifact_public_readiness_or_p0_text(self) -> None:
        payload = self.proposal()
        payload["review_notes"] = [
            "runtime-window planning report approves public identity readiness",
            "no-users status marks obelisk.player_identity.v1 ready",
            "runtime presence snapshot counts toward P0 dependency chain",
            "passive runtime-presence artifact unlocks public SDK readiness",
            "post-reboot passive monitor context counts toward P0 dependency chain",
            "confirmed beta notice JSON unlocks public identity readiness",
            "next-action status report contributes to SDK/P0 progress",
            "copied-log-only artifact marks obelisk.player_identity.v1 ready",
            "installed runtime status check unlocks public SDK readiness",
            "broadcast status check counts toward P0 dependency chain",
            "RCON status artifact marks obelisk.player_identity.v1 ready",
            "post-runtime bridge build report unlocks public header readiness",
            "shutdown-worker artifact counts toward SDK/P0 progress",
            "copied-log-only artifact does not count toward P0 progress",
        ]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        for path in (
            "$.review_notes[0]",
            "$.review_notes[1]",
            "$.review_notes[2]",
            "$.review_notes[3]",
            "$.review_notes[4]",
            "$.review_notes[5]",
            "$.review_notes[6]",
            "$.review_notes[7]",
            "$.review_notes[8]",
            "$.review_notes[9]",
            "$.review_notes[10]",
            "$.review_notes[11]",
            "$.review_notes[12]",
        ):
            with self.subTest(path=path):
                self.assertIn("non_counting_artifact_public_readiness_or_p0", terms_by_path[path])
        self.assertNotIn("$.review_notes[13]", terms_by_path)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_source_overclaim_zero_aliases_before_header_gate(self) -> None:
        payload = self.proposal()
        payload["review_metadata"] = {
            "source_overclaim_total_flag_count": 0,
            "source_overclaim_summary": {
                "total_flag_count": 0,
                "status": "ready",
            },
            "sourceOverclaimZero": True,
        }
        payload["review_notes"] = [
            "source-overclaim-zero diagnostic unlocks public header readiness",
        ]
        payload["source_artifacts"]["source_overclaim_zero_status"] = (
            "docs/research/source-overclaim-total-flag-count-zero-status.json"
        )

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unexpected_split_or_nested_claim_alias", report["blockers"])
        self.assertIn("source_artifacts_mismatch", report["blockers"])
        self.assertIn("source_artifacts_non_counting_or_public_shortcut_claimed", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        split_terms = {
            blocker.get("term")
            for blocker in report["blocker_details"]
            if blocker["reason"] == "unexpected_split_or_nested_claim_alias"
        }
        self.assertIn("source_overclaim_zero_marker", split_terms)
        self.assertIn("source_overclaim_zero_status_alias", split_terms)
        source_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_non_counting_or_public_shortcut_claimed"
        )
        values = {claim["value"] for claim in source_detail["claims"]}
        self.assertIn("source_overclaim_zero_status", values)
        self.assertIn("docs/research/source-overclaim-total-flag-count-zero-status.json", values)
        text_detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        self.assertIn("non_counting_artifact_public_readiness_or_p0", {claim["term"] for claim in text_detail["claims"]})
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_installed_runtime_broadcast_rcon_status_source_artifacts(self) -> None:
        payload = self.proposal()
        payload["source_artifacts"]["installed_runtime_status_check"] = (
            "docs/research/installed-runtime-status-check.json"
        )
        payload["source_artifacts"]["broadcast_status_check"] = "docs/research/broadcast-status-check.json"
        payload["source_artifacts"]["rcon_status_artifact"] = "docs/research/rcon-status-artifact.json"

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source_artifacts_mismatch", report["blockers"])
        self.assertIn("source_artifacts_non_counting_or_public_shortcut_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_non_counting_or_public_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        for value in (
            "installed_runtime_status_check",
            "docs/research/installed-runtime-status-check.json",
            "broadcast_status_check",
            "docs/research/broadcast-status-check.json",
            "rcon_status_artifact",
            "docs/research/rcon-status-artifact.json",
        ):
            with self.subTest(value=value):
                self.assertIn(value, values)
        self.assertFalse(report["accepted_for_header_gate_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_layout_drift(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["structs"][0]["fields"][3]["offset"] = 24

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("struct_fields_mismatch", report["blockers"])

    def test_rejects_struct_size_drift(self) -> None:
        payload = self.proposal()
        payload["proposed_header"]["structs"][0]["size"] = 88

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("struct_size_mismatch", report["blockers"])

    def test_rejects_reordered_structs(self) -> None:
        payload = self.proposal()
        structs = payload["proposed_header"]["structs"]
        structs[0], structs[1] = structs[1], structs[0]

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("struct_order_mismatch", report["blockers"])

    def test_rejects_missing_required_non_claim(self) -> None:
        payload = copy.deepcopy(self.proposal())
        payload["non_claims"].remove("does not add public capability bits" if "does not add public capability bits" in payload["non_claims"] else "does not add capability bits")

        result = self.run_checker(payload, check=False)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non_claims_missing", report["blockers"])


if __name__ == "__main__":
    unittest.main()
