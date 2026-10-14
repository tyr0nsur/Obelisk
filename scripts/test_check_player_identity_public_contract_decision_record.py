#!/usr/bin/env python3
"""Tests for check_player_identity_public_contract_decision_record.py."""

from __future__ import annotations

import copy
import hashlib
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
CHECKER = SCRIPT_DIR / "check_player_identity_public_contract_decision_record.py"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (  # noqa: E402
    SAFE_OFFLINE_WORKSPACE,
    manifest as approved_runtime_manifest,
    safe_test_env as approved_runtime_safe_test_env,
)

os.environ.update(approved_runtime_safe_test_env())

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_checker  # noqa: E402
import check_player_identity_public_contract_decision_record as checker  # noqa: E402
REQUIRED_KEYS = [
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
]
TOP_LEVEL_NON_CLAIMS = [
    "This record does not add public header symbols.",
    "This record does not promote obelisk.player_identity.v1.",
    "This record does not expose player lookup.",
    "This record does not promote permissions/admin.",
    "This record does not promote command/chat response or commands/replies.",
    "This record does not treat accepted runtime evidence as a reviewed public identity contract.",
    "This record does not treat runtime-window planning, beta notices, package-shape/support-tier artifacts, no-users status, passive/runtime-presence artifacts, or generic approval aliases as public contract progress.",
    "This record does not authorize storage, persistence, mutation, return override, runtime readiness, SDK readiness, or v1 completion.",
    "This record does not authorize live operations, runtime capture, live-log reads, marker/env changes, or workspace writes.",
]
DECISION_NON_CLAIMS = [
    "contract review only",
    "no public header symbols",
    "no lookup, persistence, permissions, commands, mutation, or return override",
]
SOURCE_ARTIFACT_HASH_POLICY = (
    "All source artifact paths and sha256 values must match the current repo-local planning artifacts; "
    "stale, mismatched, missing, notice-only, diagnostic-only, passive/runtime-presence, "
    "no-users, request/preflight/runtime-window-planning, receipt/sidecar, scoped-statement, "
    "certificate, status-json, source-overclaim-zero, copied-log-only, package-shape/support-tier, "
    "historical-handoff, public-header, public-API, or public-ABI shortcut artifacts are non-counting and cannot "
    "advance beyond reviewed identity public contract review."
)
SOURCE_ARTIFACTS = {
    "public_contract_decisions": {
        "path": "docs/player_identity_public_contract_decisions.json",
        "role": "post_runtime_identity_contract_gate_policy",
    },
    "public_abi_preflight_candidate": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "player-identity-public-abi-preflight-candidate.json"
        ),
        "role": "candidate_only_public_abi_review_input",
    },
    "owner_token_sdk_consumer_contract": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "player-identity-owner-token-sdk-consumer-contract.json"
        ),
        "role": "candidate_only_owner_token_lifecycle_review_input",
    },
    "principal_invalidation_policy": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "players-identity-principal-invalidation-policy.json"
        ),
        "role": "candidate_only_principal_lifetime_review_input",
    },
}
TEST_STRICT_REPORT_SENTINEL = "_test_strict_approved_runtime_checker_contract_report"
TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL = "_test_approved_runtime_evidence_manifest"


def strict_approved_runtime_check_report(**overrides: object) -> dict:
    report = {
        "schema": checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "input_schema": checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "mode": "consume",
        "ready": True,
        "ready_scope": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "complete_sdk_allowed": False,
        "complete_sdk_ready": False,
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "remaining_blockers": [],
        "next_blocker": "identity_public_contract_gate_missing",
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
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
        "consumer_cases": [],
        "consumer_boundary_assertions": [],
        "partial_start_end_present": False,
        "missing_strict_rejected_start": False,
        "strict_rejected_start_expected_shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        "strict_rejected_start_observed_shape": {
            "shape": "ShooterGameMode.CheckJoinInProgress(1,0)",
        },
        "non_evidence_reasons": [],
        "artifact_path_issues": [],
        "blockers": [],
        "blocker_details": [],
        "non_claims": [
            "runtime evidence acceptance does not promote public SDK identity, permissions, commands, lookup, mutation, or v1 readiness",
        ],
    }
    report.update(overrides)
    return report


def strict_approved_runtime_check_report_ref(path: Path) -> dict:
    return {
        "schema": checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_SCHEMA,
        "checker": checker.STRICT_APPROVED_RUNTIME_CHECKER,
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mode": "consume",
        "required_report_schema": checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "non_claim": checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_NON_CLAIM,
    }


def approved_runtime_evidence_manifest_ref(path: Path) -> dict:
    return checker.approved_runtime_evidence_manifest_ref(path)


def runtime_fixture_now_utc() -> datetime:
    return datetime(2026, 6, 1, 12, 16, 0, tzinfo=timezone.utc)


def generated_strict_report_for_manifest(manifest_payload: dict, manifest_path: Path) -> dict:
    with (
        mock.patch.dict(os.environ, approved_runtime_safe_test_env()),
        mock.patch.object(approved_runtime_checker, "now_utc", runtime_fixture_now_utc),
        mock.patch.object(
            approved_runtime_checker,
            "APPROVED_OFFLINE_WORKSPACE_ROOTS",
            [SAFE_OFFLINE_WORKSPACE],
        ),
        mock.patch.object(
            approved_runtime_checker.window_manifest_checker,
            "now_utc",
            runtime_fixture_now_utc,
        ),
        mock.patch.object(
            approved_runtime_checker.window_manifest_checker,
            "APPROVED_OFFLINE_WORKSPACE_ROOTS",
            [SAFE_OFFLINE_WORKSPACE],
        ),
    ):
        validation = approved_runtime_checker.validate_manifest(
            manifest_payload,
            check_mode="consume",
            input_path=manifest_path,
        )
        return approved_runtime_checker.build_report(
            manifest_payload,
            validation,
            check_mode="consume",
        )


def approved_runtime_evidence_binding(**overrides: object) -> dict:
    binding = {
        "schema": checker.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
        "accepted_for_contract_review": True,
        "resolved_input": "runtime.lifecycle_evidence",
        "next_blocker": "identity_public_contract_gate_missing",
        "artifact_kind": checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "evidence_pack_id": "player-principal-lifecycle-20260601T120000Z-player-principal-lifecycle",
        "artifact_sha256": "a" * 64,
        "source_kind": checker.APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
        "source_path": (
            "/tmp/obelisk-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/Obelisk.log"
        ),
        "source_sha256": "b" * 64,
        "copied_log_path": (
            "/tmp/obelisk-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/Obelisk.log"
        ),
        "copied_log_sha256": "b" * 64,
        "binding_scope": "reviewed_identity_public_contract_review",
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
        "non_claim": checker.APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
    }
    binding.update(overrides)
    return binding


def sha256_file(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def source_artifacts() -> dict:
    return {
        label: {
            "path": spec["path"],
            "sha256": sha256_file(spec["path"]),
            "role": spec["role"],
            "counting_scope": "reviewed_identity_public_contract_review",
        }
        for label, spec in SOURCE_ARTIFACTS.items()
    }


def accepted_record() -> dict:
    runtime_manifest = approved_runtime_manifest()
    return {
        "schema": "obelisk.player-identity-public-contract-decision-record.v1",
        "artifact_id": "reviewed_identity_public_contract_decision_record",
        "surface": "obelisk.player_identity.v1",
        "active_after_resolved_input": "runtime.lifecycle_evidence",
        "route": {
            "current_route": "approved_runtime_evidence_missing",
            "after_accepted_runtime_evidence_next_blocker": "identity_public_contract_gate_missing",
            "accepted_runtime_lifecycle_evidence_advances_to": "reviewed_identity_public_contract_review",
            "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
        },
        "route_blocker_aliases": {
            "identityPublicContractGateMissingAfterRuntimeEvidence": True,
            "publicHeaderGateMissingAfterRuntimeEvidence": False,
            "publicApiGateMissingAfterRuntimeEvidence": False,
            "publicAbiGateMissingAfterRuntimeEvidence": False,
            "publicSdkReadinessAfterRuntimeEvidence": False,
            "runtimeReadinessAfterRuntimeEvidence": False,
            "v1CompletionAfterRuntimeEvidence": False,
        },
        TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL: runtime_manifest,
        TEST_STRICT_REPORT_SENTINEL: None,
        "approved_runtime_evidence_binding": checker.approved_runtime_evidence_binding_from_manifest(
            runtime_manifest
        ),
        "post_runtime_identity_contract_gate": copy.deepcopy(
            checker.REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE
        ),
        "post_runtime_identity_contract_next_step": copy.deepcopy(checker.REQUIRED_NEXT_STEP_CHECK),
        "runtime_evidence_contract_review_currentness": copy.deepcopy(
            checker.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC
        ),
        "review_status": "reviewed",
        "accepted_for_contract_review": True,
        "source_artifact_hash_policy": SOURCE_ARTIFACT_HASH_POLICY,
        "source_artifacts": source_artifacts(),
        "resolved_decision_keys": REQUIRED_KEYS,
        "decisions": {
            key: {
                "status": "reviewed",
                "resolved": True,
                "scope": "contract_review_only",
                "non_claims": DECISION_NON_CLAIMS,
            }
            for key in REQUIRED_KEYS
        },
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "public_header_ready": False,
        "public_api_allowed": False,
        "public_abi_allowed": False,
        "public_callback_abi_ready": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "accepted_for_header_gate_review": False,
        "accepted_for_public_header_gate_review": False,
        "accepted_for_public_header_review": False,
        "accepted_for_public_api_review": False,
        "accepted_for_public_abi_review": False,
        "public_header_gate_ready": False,
        "public_header_gate_unlocked": False,
        "public_api_gate_ready": False,
        "public_api_gate_unlocked": False,
        "public_abi_gate_ready": False,
        "public_abi_gate_unlocked": False,
        "public_readiness": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "resource_handle_allowed": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "public_sdk_v1_completion_ready": False,
        "public_sdk_v1_completion_claim": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "public_api_symbols_now": [],
        "non_claims": TOP_LEVEL_NON_CLAIMS,
    }


def default_record() -> dict:
    return json.loads((REPO_ROOT / checker.DEFAULT_RECORD).read_text(encoding="utf-8"))


class PlayerIdentityPublicContractDecisionRecordTests(unittest.TestCase):
    def run_checker(self, payload: dict | None = None, *args: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "record.json"
            env = os.environ.copy()
            env.update(approved_runtime_safe_test_env())
            if payload is not None:
                payload_to_write = copy.deepcopy(payload)
                runtime_manifest = payload_to_write.pop(TEST_APPROVED_RUNTIME_MANIFEST_SENTINEL, None)
                runtime_manifest_path = None
                if runtime_manifest is not None:
                    runtime_manifest_path = Path(tmp) / "approved-runtime-principal-lifecycle-evidence.json"
                    runtime_manifest_path.write_text(
                        json.dumps(runtime_manifest, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    payload_to_write[
                        checker.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD
                    ] = approved_runtime_evidence_manifest_ref(runtime_manifest_path)
                strict_report = payload_to_write.pop(TEST_STRICT_REPORT_SENTINEL, None)
                if strict_report is not None:
                    report_path = Path(tmp) / "approved-runtime-principal-lifecycle-evidence.check.json"
                    report_path.write_text(
                        json.dumps(strict_report, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    payload_to_write[
                        "strict_approved_runtime_checker_contract_report"
                    ] = strict_approved_runtime_check_report_ref(report_path)
                elif TEST_STRICT_REPORT_SENTINEL in payload:
                    self.assertIsNotNone(runtime_manifest)
                    self.assertIsNotNone(runtime_manifest_path)
                    generated_report = generated_strict_report_for_manifest(
                        runtime_manifest,
                        runtime_manifest_path,
                    )
                    report_path = Path(tmp) / "approved-runtime-principal-lifecycle-evidence.check.json"
                    report_path.write_text(
                        json.dumps(generated_report, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    payload_to_write[
                        "strict_approved_runtime_checker_contract_report"
                    ] = strict_approved_runtime_check_report_ref(report_path)
                path.write_text(json.dumps(payload_to_write, sort_keys=True) + "\n", encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(CHECKER), "--record", str(path), "--json", *args],
                cwd=SCRIPT_DIR.parents[0],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

    def blocker_aliases(self, report: dict, reason: str) -> set[str]:
        return {
            detail["alias"]
            for detail in report["blocker_details"]
            if detail["reason"] == reason and "alias" in detail
        }

    def test_accepts_reviewed_decision_record_as_contract_review_only(self) -> None:
        payload = accepted_record()
        result = self.run_checker(payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "no_public_or_header_readiness")
        self.assertTrue(report["record_valid"])
        self.assertEqual(report["record_valid_scope"], "reviewed_identity_public_contract_record_only")
        self.assertTrue(report["contract_review_only"])
        self.assertTrue(report["reviewed_hash_current_contract_review_only"])
        self.assertTrue(report["hash_bound_to_current_source_artifacts"])
        self.assertTrue(report["strict_approved_runtime_checker_contract_report_required"])
        self.assertTrue(report["strict_approved_runtime_checker_contract_report_valid"])
        strict_report_ref = report["strict_approved_runtime_checker_contract_report"]
        self.assertEqual(
            strict_report_ref["schema"],
            checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_SCHEMA,
        )
        self.assertEqual(strict_report_ref["checker"], checker.STRICT_APPROVED_RUNTIME_CHECKER)
        self.assertEqual(
            strict_report_ref["required_report_schema"],
            checker.STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        )
        self.assertTrue(report["approved_runtime_evidence_binding_required"])
        self.assertTrue(report["approved_runtime_evidence_manifest_ref_required"])
        self.assertTrue(report["approved_runtime_evidence_manifest_ref_valid"])
        self.assertTrue(report["runtime_evidence_binding_valid"])
        self.assertEqual(
            report["approved_runtime_evidence_binding"],
            payload["approved_runtime_evidence_binding"],
        )
        manifest_ref = report["approved_runtime_evidence_manifest_ref"]
        self.assertEqual(
            manifest_ref["schema"],
            checker.APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_SCHEMA,
        )
        self.assertEqual(manifest_ref["checker"], checker.STRICT_APPROVED_RUNTIME_CHECKER)
        self.assertEqual(
            manifest_ref["required_manifest_schema"],
            checker.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        )
        self.assertEqual(report["source_artifact_freshness"]["status"], "current")
        self.assertTrue(report["source_artifact_freshness"]["current"])
        self.assertEqual(report["source_artifact_freshness"]["required_action"], "none")
        self.assertEqual(
            report["source_artifact_freshness"]["current_route"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["source_artifact_freshness"]["post_runtime_evidence_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["source_artifact_freshness"]["counts_toward_public_sdk"])
        self.assertFalse(
            report["source_artifact_freshness"]["counts_toward_p0_dependency_chain_claim"]
        )
        self.assertEqual(report["source_artifact_freshness"]["mismatches"], [])
        diagnostic = report["runtime_evidence_contract_review_currentness"]
        self.assertEqual(diagnostic["schema"], checker.CURRENTNESS_DIAGNOSTIC_SCHEMA)
        self.assertEqual(
            diagnostic["only_next_blocker_after_accepted_runtime_evidence"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(
            diagnostic["accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"]
        )
        self.assertFalse(diagnostic["candidate_preflight_review_aliases_count"])
        self.assertFalse(diagnostic["permissions_admin_unlocked_from_runtime_evidence"])
        self.assertFalse(diagnostic["command_surface_unlocked_from_runtime_evidence"])
        self.assertTrue(diagnostic["observed"]["source_artifacts_current"])
        self.assertEqual(diagnostic["observed"]["source_artifact_mismatches"], [])
        self.assertEqual(diagnostic["observed"]["source_artifact_required_action"], "none")
        self.assertTrue(
            diagnostic["observed"]["strict_approved_runtime_checker_contract_report_valid"]
        )
        self.assertTrue(diagnostic["observed"]["approved_runtime_evidence_manifest_ref_valid"])
        self.assertTrue(diagnostic["observed"]["runtime_evidence_binding_valid"])
        self.assertTrue(diagnostic["observed"]["record_accepted_for_contract_review"])
        self.assertEqual(
            report["checkable_next_step"]["checker"],
            "scripts/check_player_identity_public_contract_decision_record.py",
        )
        self.assertEqual(
            report["checkable_next_step"]["runtime_evidence_contract_review_currentness"],
            checker.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
        )
        self.assertEqual(
            report["checkable_next_step"]["record_path"],
            "docs/research/player-identity-planning-sources/reviewed-identity-public-contract-decision-record.json",
        )
        self.assertEqual(
            report["checkable_next_step"]["required_record_state"],
            "reviewed_hash_current_contract_review_only",
        )
        self.assertEqual(
            report["checkable_next_step"][
                "required_strict_approved_runtime_checker_contract_report_ref"
            ],
            "$.strict_approved_runtime_checker_contract_report",
        )
        self.assertIn(
            "report file exists, hash matches",
            report["checkable_next_step"][
                "required_strict_approved_runtime_checker_contract_report_state"
            ],
        )
        self.assertEqual(
            report["checkable_next_step"]["required_approved_runtime_evidence_binding_ref"],
            "$.approved_runtime_evidence_binding",
        )
        self.assertEqual(
            report["checkable_next_step"]["required_approved_runtime_evidence_binding_state"],
            "matches accepted runtime.lifecycle_evidence artifact identity and copied runtime-observer log source",
        )
        self.assertEqual(
            report["checkable_next_step"]["post_runtime_identity_contract_gate_ref"],
            "$.post_runtime_identity_contract_gate",
        )
        self.assertEqual(
            report["checkable_next_step"]["accepted_route"]["only_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["before_accepted_runtime_evidence"][
                "current_blocker"
            ],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(
            report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][
                "downstream_p0_or_public_sdk_unlock_allowed"
            ]
        )
        for key in (
            "public_sdk_ready",
            "public_sdk_v1_completion_ready",
            "complete_sdk_ready",
            "stable_ready",
            "stable_claim_allowed",
            "stable_claim_ready",
            "stable_sdk_ready",
            "plugin_hub_ready",
            "plugin_hub_publication_ready",
            "publication_ready",
            "publication_authorized",
            "counts_toward_public_sdk",
            "counts_toward_complete_sdk_claim",
            "permissions_admin_ready",
            "permissions_admin_public_ready",
            "permissions_admin_unlocked",
            "command_response_ready",
            "command_chat_response_ready",
            "commands_replies_ready",
        ):
            with self.subTest(post_runtime_after_accepted_false=key):
                self.assertFalse(
                    report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][key]
                )
        self.assertFalse(
            report["post_runtime_identity_contract_gate"]["before_accepted_runtime_evidence"][
                "record_downstream_p0_or_public_sdk_unlock_allowed"
            ]
        )
        self.assertEqual(report["checkable_next_step"]["source_artifact_freshness"]["status"], "current")
        self.assertFalse(report["checkable_next_step"]["non_claim_flags"]["public_sdk_ready"])
        self.assertFalse(report["checkable_next_step"]["non_claim_flags"]["runtime_ready"])
        self.assertFalse(report["checkable_next_step"]["non_claim_flags"]["p0_progress_ready"])
        self.assertFalse(report["checkable_next_step"]["non_claim_flags"]["plugin_hub_ready"])
        self.assertFalse(report["checkable_next_step"]["non_claim_flags"]["publication_authorized"])
        self.assertTrue(report["accepted_for_contract_review"])
        self.assertEqual(report["current_route"], "approved_runtime_evidence_missing")
        self.assertEqual(report["current_blocker"], "approved_runtime_evidence_missing")
        self.assertEqual(report["post_runtime_evidence_next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(
            report["accepted_runtime_lifecycle_evidence_advances_to"],
            "reviewed_identity_public_contract_review",
        )
        self.assertEqual(report["resolved_decision_keys"], REQUIRED_KEYS)
        for key in (
            "promotion_ready",
            "public_contract_allowed",
            "public_header_allowed",
            "public_header_ready",
            "public_abi_ready",
            "public_abi_allowed",
            "public_api_ready",
            "public_api_allowed",
            "public_sdk_ready",
            "public_readiness",
            "runtime_ready",
            "runtime_readiness",
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
            "permissions_admin_ready",
            "permissions_admin_public_ready",
            "permissions_admin_unlocked",
            "commands_ready",
            "command_response_ready",
            "command_chat_response_ready",
            "commands_replies_ready",
            "resource_handle_ready",
            "resource_handle_supported",
            "resource_handle_allowed",
            "v1_ready",
            "v1_completion_ready",
            "v1_completion_evidence",
            "complete_sdk_ready",
            "live_ops_authorized",
            "server_operations_authorized",
            "workspace_writes_authorized",
            "runtime_capture_authorized",
            "reads_live_logs",
            "public_sdk_v1_completion_ready",
            "public_sdk_v1_completion_claim",
            "accepted_for_header_gate_review",
            "accepted_for_public_header_gate_review",
            "accepted_for_public_header_review",
            "accepted_for_public_api_review",
            "accepted_for_public_abi_review",
            "public_header_gate_ready",
            "public_header_gate_unlocked",
            "public_api_gate_ready",
            "public_api_gate_unlocked",
            "public_abi_gate_ready",
            "public_abi_gate_unlocked",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])

    def test_rejects_missing_runtime_contract_currentness_diagnostic(self) -> None:
        payload = accepted_record()
        payload.pop("runtime_evidence_contract_review_currentness")

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("runtime_evidence_contract_review_currentness_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])

    def test_rejects_runtime_contract_currentness_alias_promotion(self) -> None:
        payload = accepted_record()
        payload["runtime_evidence_contract_review_currentness"][
            "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"
        ] = True
        payload["runtime_evidence_contract_review_currentness"][
            "candidate_preflight_review_aliases_count"
        ] = True
        payload["runtime_evidence_contract_review_currentness"][
            "only_next_blocker_after_accepted_runtime_evidence"
        ] = "public_header_gate_missing"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("runtime_evidence_contract_review_currentness_mismatch", report["blockers"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_default_reviewed_record_is_stale_and_blocked_until_approved_runtime_binding(self) -> None:
        payload = default_record()

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["record_valid"])
        self.assertEqual(report["record_valid_scope"], "reviewed_identity_public_contract_record_only")
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertTrue(report["strict_approved_runtime_checker_contract_report_required"])
        self.assertFalse(report["strict_approved_runtime_checker_contract_report_valid"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(report["source_artifact_freshness"]["current"])
        self.assertIn(
            "Refresh the reviewed decision record's source_artifacts sha256 values",
            report["source_artifact_freshness"]["required_action"],
        )
        self.assertEqual(
            report["source_artifact_freshness"]["current_route"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["source_artifact_freshness"]["post_runtime_evidence_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["source_artifact_freshness"]["counts_toward_public_sdk"])
        self.assertFalse(
            report["source_artifact_freshness"]["counts_toward_p0_dependency_chain_claim"]
        )
        self.assertEqual(
            report["source_artifact_freshness"]["mismatches"][0]["label"],
            "public_contract_decisions",
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifacts_current"
            ]
        )
        self.assertEqual(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifact_mismatches"
            ],
            report["source_artifact_freshness"]["mismatches"],
        )
        self.assertEqual(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifact_required_action"
            ],
            report["source_artifact_freshness"]["required_action"],
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"][
                "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"][
                "candidate_preflight_review_aliases_count"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "strict_approved_runtime_checker_contract_report_valid"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "runtime_evidence_binding_valid"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "record_accepted_for_contract_review"
            ]
        )
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertIsNone(report["accepted_runtime_lifecycle_evidence_advances_to"])
        self.assertEqual(report["resolved_decision_keys"], [])
        self.assertIn("accepted_for_contract_review_not_true", report["blockers"])
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_missing_or_not_object",
            report["blockers"],
        )
        self.assertIn("approved_runtime_evidence_manifest_ref_missing_or_not_object", report["blockers"])
        self.assertIn("approved_runtime_evidence_binding_missing_or_not_object", report["blockers"])
        self.assertIn("source_artifact_hash_mismatch", report["blockers"])
        self.assertNotIn("accepted_for_contract_review_not_boolean", report["blockers"])
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
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_reports_stale_source_hash_mismatches_as_non_counting(self) -> None:
        payload = default_record()
        payload["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertFalse(report["record_valid"])
        self.assertEqual(report["record_valid_scope"], "reviewed_identity_public_contract_record_only")
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertIn(
            "Refresh the reviewed decision record's source_artifacts sha256 values",
            report["source_artifact_freshness"]["required_action"],
        )
        self.assertEqual(
            report["source_artifact_freshness"]["current_route"],
            "approved_runtime_evidence_missing",
        )
        self.assertEqual(
            report["source_artifact_freshness"]["post_runtime_evidence_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["source_artifact_freshness"]["counts_toward_public_sdk"])
        self.assertFalse(
            report["source_artifact_freshness"]["counts_toward_p0_dependency_chain_claim"]
        )
        mismatch = report["source_artifact_freshness"]["mismatches"][0]
        self.assertEqual(mismatch["label"], "public_contract_decisions")
        self.assertEqual(mismatch["path"], "docs/player_identity_public_contract_decisions.json")
        self.assertEqual(
            mismatch["expected_sha256"],
            sha256_file("docs/player_identity_public_contract_decisions.json"),
        )
        self.assertEqual(mismatch["observed_sha256"], "0" * 64)
        self.assertIn(
            "approved_runtime_evidence_missing",
            mismatch["required_action"],
        )
        self.assertEqual(mismatch["current_route"], "approved_runtime_evidence_missing")
        self.assertEqual(
            mismatch["post_runtime_evidence_next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(mismatch["counts_toward_public_sdk"])
        self.assertFalse(mismatch["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"][
                "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"][
                "candidate_preflight_review_aliases_count"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "strict_approved_runtime_checker_contract_report_valid"
            ]
        )
        self.assertFalse(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "runtime_evidence_binding_valid"
            ]
        )
        self.assertEqual(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifact_mismatches"
            ],
            report["source_artifact_freshness"]["mismatches"],
        )
        self.assertEqual(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifact_required_action"
            ],
            report["source_artifact_freshness"]["required_action"],
        )
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertIsNone(report["accepted_runtime_lifecycle_evidence_advances_to"])
        self.assertEqual(report["resolved_decision_keys"], [])
        self.assertIn("source_artifact_hash_mismatch", report["blockers"])
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
        self.assertEqual(report["complete_sdk_claim_progress_contribution"], 0)
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_reports_missing_source_hash_as_non_counting_freshness_mismatch(self) -> None:
        payload = accepted_record()
        payload["source_artifacts"]["owner_token_sdk_consumer_contract"].pop("sha256")

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifact_sha256_missing", report["blockers"])
        self.assertIn("source_artifact_entry_keys_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        mismatch = report["source_artifact_freshness"]["mismatches"][0]
        self.assertEqual(mismatch["reason"], "source_artifact_sha256_missing")
        self.assertEqual(mismatch["label"], "owner_token_sdk_consumer_contract")
        self.assertEqual(
            mismatch["path"],
            (
                "docs/research/player-identity-planning-sources/"
                "player-identity-owner-token-sdk-consumer-contract.json"
            ),
        )
        self.assertEqual(
            mismatch["expected_sha256"],
            sha256_file(
                "docs/research/player-identity-planning-sources/"
                "player-identity-owner-token-sdk-consumer-contract.json"
            ),
        )
        self.assertIsNone(mismatch["observed_sha256"])
        self.assertFalse(mismatch["counts_toward_public_sdk"])
        self.assertFalse(mismatch["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_missing_record(self) -> None:
        result = self.run_checker(None)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("decision_record_missing", report["blockers"])

    def test_rejects_record_without_approved_runtime_evidence_binding(self) -> None:
        payload = accepted_record()
        payload.pop("approved_runtime_evidence_binding")

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_missing_or_not_object", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_bare_runtime_binding_without_strict_checker_contract_report(self) -> None:
        payload = accepted_record()
        payload.pop(TEST_STRICT_REPORT_SENTINEL)

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_missing_or_not_object",
            report["blockers"],
        )
        self.assertFalse(report["strict_approved_runtime_checker_contract_report_valid"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["record_valid"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_status_report_as_strict_checker_contract_report(self) -> None:
        payload = accepted_record()
        payload[TEST_STRICT_REPORT_SENTINEL] = {
            "schema": "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
            "mode": "consume",
            "ready": True,
            "approved": True,
            "approved_runtime_evidence_present": True,
            "runtime_evidence_ready": True,
            "next_blocker": "identity_public_contract_gate_missing",
            "standing_authorization": True,
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_schema_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_input_schema_mismatch",
            report["blockers"],
        )
        self.assertIn(
            "strict_approved_runtime_checker_contract_report_ready_scope_mismatch",
            report["blockers"],
        )
        self.assertFalse(report["strict_approved_runtime_checker_contract_report_valid"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_stale_runtime_evidence_binding_not_matching_manifest(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"]["artifact_sha256"] = "f" * 64
        payload["approved_runtime_evidence_binding"]["source_sha256"] = "e" * 64
        payload["approved_runtime_evidence_binding"]["copied_log_sha256"] = "e" * 64

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_manifest_mismatch", report["blockers"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_strict_runtime_report_for_same_hash_duplicate_manifest_path_drift(self) -> None:
        payload = accepted_record()
        duplicate_manifest = approved_runtime_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            duplicate_manifest_path = Path(tmp) / "approved-runtime-principal-lifecycle-evidence.json"
            duplicate_manifest_path.write_text(
                json.dumps(duplicate_manifest, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            payload[TEST_STRICT_REPORT_SENTINEL] = generated_strict_report_for_manifest(
                duplicate_manifest,
                duplicate_manifest_path,
            )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("strict_approved_runtime_checker_contract_report_runtime_input_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["strict_approved_runtime_checker_contract_report_valid"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_runtime_evidence_binding_stable_plugin_publication_claims(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            stable_sdk_ready=True,
            plugin_hub_ready=True,
            plugin_hub_publication_ready=True,
            publication_authorized=True,
        )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_stable_sdk_ready_not_false", report["blockers"])
        self.assertIn("approved_runtime_evidence_binding_plugin_hub_ready_not_false", report["blockers"])
        self.assertIn(
            "approved_runtime_evidence_binding_plugin_hub_publication_ready_not_false",
            report["blockers"],
        )
        self.assertIn("approved_runtime_evidence_binding_publication_authorized_not_false", report["blockers"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["stable_sdk_ready"])
        self.assertFalse(report["plugin_hub_ready"])
        self.assertFalse(report["publication_authorized"])

    def test_rejects_runtime_evidence_binding_shortcut_artifacts(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            evidence_pack_id="confirmed-beta-notice-status-json-historical-handoff",
            source_path="docs/research/post-reboot-passive-monitor-status.json",
            copied_log_path="docs/research/copied-log-only-package-shape-historical-handoff.txt",
        )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_non_counting_shortcut_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_binding_non_counting_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("confirmed-beta-notice-status-json-historical-handoff", values)
        self.assertIn("docs/research/post-reboot-passive-monitor-status.json", values)
        self.assertIn("docs/research/copied-log-only-package-shape-historical-handoff.txt", values)
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_post_runtime_bridge_or_shutdown_worker_artifacts_as_runtime_binding(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            evidence_pack_id="post-runtime-bridge-build-report",
            source_path="docs/research/shutdown-worker-artifact.json",
            copied_log_path="docs/research/shutdown-worker-artifact.json",
        )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_non_counting_shortcut_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_binding_non_counting_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("post-runtime-bridge-build-report", values)
        self.assertIn("docs/research/shutdown-worker-artifact.json", values)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_start_end_only_runtime_artifacts_as_binding_or_source_shortcut(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            evidence_pack_id="principal-start-end-runtime-evidence",
            source_path="docs/research/runtime-lifecycle-start-end-evidence.json",
            copied_log_path="docs/research/start-end-only-runtime-evidence.log",
        )
        payload["source_artifacts"]["principal_start_end_runtime_evidence"] = {
            "path": "docs/research/principal-start-end-runtime-evidence.json",
            "sha256": "0" * 64,
            "role": "runtime_lifecycle_start_end_evidence",
            "counting_scope": "reviewed_identity_public_contract_review",
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("approved_runtime_evidence_binding_non_counting_shortcut_claimed", report["blockers"])
        self.assertIn("source_artifacts_notice_only_or_non_counting_claimed", report["blockers"])
        binding_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_binding_non_counting_shortcut_claimed"
        )
        binding_values = {claim["value"] for claim in binding_detail["claims"]}
        self.assertIn("principal-start-end-runtime-evidence", binding_values)
        self.assertIn("docs/research/runtime-lifecycle-start-end-evidence.json", binding_values)
        self.assertIn("docs/research/start-end-only-runtime-evidence.log", binding_values)
        source_detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_notice_only_or_non_counting_claimed"
        )
        source_values = {claim["value"] for claim in source_detail["claims"]}
        self.assertIn("principal_start_end_runtime_evidence", source_values)
        self.assertIn("docs/research/principal-start-end-runtime-evidence.json", source_values)
        self.assertIn("runtime_lifecycle_start_end_evidence", source_values)
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_runtime_evidence_binding_public_shortcut_artifacts(self) -> None:
        payload = accepted_record()
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            evidence_pack_id="public-header-api-abi-shortcut-artifact",
            source_path="docs/research/player-identity-public-header-api-abi-shortcut.log",
            copied_log_path="docs/research/player-identity-public-header-api-abi-shortcut.log",
        )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "approved_runtime_evidence_binding_public_header_api_abi_shortcut_claimed",
            report["blockers"],
        )
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_binding_public_header_api_abi_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("public-header-api-abi-shortcut-artifact", values)
        self.assertIn("docs/research/player-identity-public-header-api-abi-shortcut.log", values)
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])

    def test_rejects_public_header_proposal_as_runtime_binding_artifact(self) -> None:
        payload = accepted_record()
        proposal_path = (
            "docs/research/player-identity-planning-sources/"
            "player-identity-public-header-gate-proposal.json"
        )
        payload["approved_runtime_evidence_binding"] = approved_runtime_evidence_binding(
            evidence_pack_id="player-identity-public-header-gate-proposal",
            source_path=proposal_path,
            copied_log_path=proposal_path,
        )

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn(
            "approved_runtime_evidence_binding_public_header_api_abi_shortcut_claimed",
            report["blockers"],
        )
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "approved_runtime_evidence_binding_public_header_api_abi_shortcut_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("player-identity-public-header-gate-proposal", values)
        self.assertIn(proposal_path, values)
        self.assertFalse(report["runtime_evidence_binding_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_missing_review_decision_key(self) -> None:
        payload = accepted_record()
        unexpected_key = "identity_public_contract.unexpected_review_key"
        payload["resolved_decision_keys"] = REQUIRED_KEYS[:-1] + [unexpected_key]
        payload["decisions"].pop(REQUIRED_KEYS[-1])
        payload["decisions"][unexpected_key] = {
            "status": "reviewed",
            "resolved": True,
            "scope": "contract_review_only",
            "non_claims": DECISION_NON_CLAIMS,
        }
        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("resolved_decision_keys_mismatch", report["blockers"])
        self.assertIn("decision_entries_mismatch", report["blockers"])
        for reason in ("resolved_decision_keys_mismatch", "decision_entries_mismatch"):
            with self.subTest(reason=reason):
                detail = next(
                    blocker
                    for blocker in report["blocker_details"]
                    if blocker["reason"] == reason
                )
                self.assertEqual(detail["missing"], [REQUIRED_KEYS[-1]])
                self.assertEqual(detail["unexpected"], [unexpected_key])
                self.assertIn(
                    "accepted runtime.lifecycle_evidence bundle",
                    detail["required_action"],
                )
                self.assertIn("exactly the required reviewed decision keys", detail["required_action"])
                self.assertEqual(detail["next_blocker"], "identity_public_contract_gate_missing")
                self.assertFalse(detail["counts_toward_public_sdk"])
                self.assertFalse(detail["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_next_step_contract_drift(self) -> None:
        payload = accepted_record()
        payload["post_runtime_identity_contract_next_step"]["accepted_route"][
            "only_next_blocker"
        ] = "public_header_gate_missing"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("post_runtime_identity_contract_next_step_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_post_runtime_gate_contract_drift(self) -> None:
        payload = accepted_record()
        payload["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][
            "next_blocker"
        ] = "public_sdk_ready"
        payload["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][
            "downstream_p0_or_public_sdk_unlock_allowed"
        ] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("post_runtime_identity_contract_gate_mismatch", report["blockers"])
        self.assertIn("blocker_id_mismatch", report["blockers"])
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"]["next_blocker"],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(
            report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][
                "downstream_p0_or_public_sdk_unlock_allowed"
            ]
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_post_runtime_gate_permissions_admin_shortcut(self) -> None:
        payload = accepted_record()
        after_runtime = payload["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"]
        after_runtime["next_blocker"] = "permissions_admin"
        after_runtime["only_next_blocker"] = "permissions_admin"
        after_runtime["permissions_admin_ready"] = True
        after_runtime["permissions_admin_unlocked"] = True
        after_runtime["command_chat_response_ready"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("post_runtime_identity_contract_gate_mismatch", report["blockers"])
        self.assertIn("blocker_id_mismatch", report["blockers"])
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertEqual(
            report["post_runtime_identity_contract_gate"]["after_accepted_runtime_evidence"][
                "next_blocker"
            ],
            "identity_public_contract_gate_missing",
        )
        self.assertFalse(report["permissions_admin_ready"])
        self.assertFalse(report["permissions_admin_unlocked"])
        self.assertFalse(report["command_chat_response_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_decision_record_that_is_not_contract_review_only(self) -> None:
        payload = accepted_record()
        payload["decisions"][REQUIRED_KEYS[0]]["scope"] = "public_header_review"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("decision_entry_scope_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])

    def test_accepts_reviewed_hash_current_contract_review_metadata_as_non_readiness(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
        }

        result = self.run_checker(payload)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["record_valid"])
        self.assertTrue(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_reviewed_metadata_when_source_artifact_hash_is_wrong(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
        }
        payload["source_artifacts"]["owner_token_sdk_consumer_contract"]["sha256"] = "f" * 64

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifact_hash_mismatch", report["blockers"])
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")

    def test_rejects_wrong_dependency_chain_position_metadata(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "v1_dependency_chain_position": 2,
            "required_by_v1_dependency_chain_position": 3,
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("dependency_chain_position_claimed_before_promotion", report["blockers"])
        paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "dependency_chain_position_claimed_before_promotion"
        }
        self.assertIn("$.review_metadata.v1_dependency_chain_position", paths)
        self.assertIn("$.review_metadata.required_by_v1_dependency_chain_position", paths)
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_wrong_blocker_id_metadata(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "next_blocker": "public_header_gate_missing",
            "current_blocker": "identity_public_contract_gate_missing",
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("blocker_id_mismatch", report["blockers"])
        observed = {
            blocker["observed"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "blocker_id_mismatch"
        }
        self.assertEqual(observed, {"public_header_gate_missing", "identity_public_contract_gate_missing"})
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_identity_contract_gate_missing_alias_cleared(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "identity_public_contract_gate_missing": False,
            "publicHeaderGateMissingAfterRuntimeEvidence": True,
            "accepted_for_identity_public_contract_gate_review": True,
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("identity_public_contract_gate_missing_alias_not_true", report["blockers"])
        self.assertIn("downstream_gate_missing_alias_not_false", report["blockers"])
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertFalse(report["accepted_for_identity_public_contract_gate_review"])
        self.assertTrue(report["post_runtime_identity_contract_gate_missing"])
        self.assertFalse(report["identity_public_contract_gate_ready"])
        self.assertFalse(report["identity_public_contract_gate_unlocked"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_mixed_decision_scope_aliases(self) -> None:
        payload = accepted_record()
        payload["decisions"][REQUIRED_KEYS[0]]["decision_scope"] = "contract_review_only"
        payload["decisions"][REQUIRED_KEYS[1]]["decision_scope"] = "public_header_review"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("decision_entry_keys_mismatch", report["blockers"])
        self.assertIn("decision_entry_decision_scope_mismatch", report["blockers"])
        mismatch = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "decision_entry_decision_scope_mismatch"
        )
        self.assertEqual(mismatch["observed"], "public_header_review")
        self.assertFalse(report["contract_review_only"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_stale_proposed_header_symbols_in_review_record_metadata(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "proposed_header_symbols": [
                "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
                "RegisterPlayerIdentityEventWithOwnerTokenHandle",
            ],
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("stale_proposed_header_symbols_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "stale_proposed_header_symbols_claimed"
        )
        self.assertEqual(detail["label"], "$.review_metadata.proposed_header_symbols")
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["public_header_symbols_now"], [])

    def test_rejects_public_abi_identity_handle_wording_before_resource_handle(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "public ABI carries principal handles before ResourceHandle promotion",
            "public ABI must not expose principal handles before ResourceHandle promotion",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        claims = {
            claim["path"]: claim["term"]
            for claim in detail["claims"]
            if claim["term"] == "public_abi_identity_handle_before_resource_handle"
        }
        self.assertEqual(claims, {"$.notes[0]": "public_abi_identity_handle_before_resource_handle"})
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["resource_handle_supported"])

    def test_rejects_public_readiness_claims(self) -> None:
        payload = accepted_record()
        payload["public_abi_ready"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
        result = self.run_checker(payload)
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])

    def test_rejects_non_counting_source_artifact_classes(self) -> None:
        payload = accepted_record()
        payload["source_artifacts"]["runtime_fixture_package_support"] = {
            "path": "docs/research/copied-runtime-partial-fixture-package-shape.json",
            "sha256": "0" * 64,
            "role": "support_tier_package_shape_runtime_fixture",
            "counting_scope": "reviewed_identity_public_contract_review",
        }
        payload["source_artifacts"]["passive_extended_monitor_log"] = {
            "path": "docs/research/extended-passive-monitor-snapshot.log",
            "sha256": "0" * 64,
            "role": "passive_extended_monitor_snapshot",
            "counting_scope": "reviewed_identity_public_contract_review",
        }
        payload["source_artifacts"]["beta_notice_closure_executor_report"] = {
            "path": "docs/research/player-principal-beta-notice-closure-executor-report.json",
            "sha256": "0" * 64,
            "role": "beta_notice_closure_executor_report",
            "counting_scope": "reviewed_identity_public_contract_review",
        }
        payload["source_artifacts"]["approved_manifest_ready_alias"] = {
            "path": "docs/research/identity-public-contract-approved-manifest-ready-alias.json",
            "sha256": "0" * 64,
            "role": "approved_manifest_ready_alias_shortcut",
            "counting_scope": "reviewed_identity_public_contract_review",
        }
        payload["source_artifacts"]["historical_status_json_handoff_text"] = {
            "path": "docs/research/historical-handoff-status.json",
            "sha256": "0" * 64,
            "role": "historical_handoff_text",
            "counting_scope": "reviewed_identity_public_contract_review",
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifacts_keys_mismatch", report["blockers"])
        self.assertIn("source_artifacts_notice_only_or_non_counting_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_notice_only_or_non_counting_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("runtime_fixture_package_support", values)
        self.assertIn("docs/research/copied-runtime-partial-fixture-package-shape.json", values)
        self.assertIn("support_tier_package_shape_runtime_fixture", values)
        self.assertIn("passive_extended_monitor_log", values)
        self.assertIn("docs/research/extended-passive-monitor-snapshot.log", values)
        self.assertIn("beta_notice_closure_executor_report", values)
        self.assertIn("docs/research/player-principal-beta-notice-closure-executor-report.json", values)
        self.assertIn("approved_manifest_ready_alias", values)
        self.assertIn("docs/research/identity-public-contract-approved-manifest-ready-alias.json", values)
        self.assertIn("historical_status_json_handoff_text", values)
        self.assertIn("docs/research/historical-handoff-status.json", values)
        self.assertIn("historical_handoff_text", values)
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_focused_non_counting_shortcut_artifact_classes(self) -> None:
        payload = accepted_record()
        shortcuts = {
            "copied_log_only_runtime": (
                "docs/research/copied-log-only-runtime.txt",
                "copied_log_only_runtime",
            ),
            "sidecar_receipt": (
                "docs/research/runtime-window-sidecar-receipt.json",
                "sidecar_receipt",
            ),
            "runtime_window_planning": (
                "docs/research/runtime-window-planning-report.json",
                "runtime_window_planning",
            ),
            "beta_notice": (
                "docs/research/player-principal-beta-notice.json",
                "beta_notice",
            ),
            "passive_monitor": (
                "docs/research/passive-monitor-snapshot.json",
                "passive_monitor",
            ),
            "runtime_presence_snapshot": (
                "docs/research/runtime-presence-snapshot.json",
                "runtime_presence_snapshot",
            ),
            "no_users_status": (
                "docs/research/no-users-status.json",
                "no_users_status",
            ),
            "diagnostic_status_json": (
                "docs/research/diagnostic-status.json",
                "diagnostic_status_json",
            ),
            "package_shape": (
                "docs/research/installed-sdk-package-shape.json",
                "package_shape",
            ),
            "installed_runtime_status_check": (
                "docs/research/installed-runtime-status-check.json",
                "installed_runtime_status_check",
            ),
            "broadcast_status_check": (
                "docs/research/broadcast-status-check.json",
                "broadcast_status_check",
            ),
            "rcon_status_artifact": (
                "docs/research/rcon-status-artifact.json",
                "rcon_status_artifact",
            ),
        }
        for label, (path, role) in shortcuts.items():
            payload["source_artifacts"][label] = {
                "path": path,
                "sha256": "0" * 64,
                "role": role,
                "counting_scope": "reviewed_identity_public_contract_review",
            }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifacts_keys_mismatch", report["blockers"])
        self.assertIn("source_artifacts_notice_only_or_non_counting_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_notice_only_or_non_counting_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        for label, (path, role) in shortcuts.items():
            with self.subTest(label=label):
                self.assertIn(label, values)
                self.assertIn(path, values)
                self.assertIn(role, values)
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_generic_accepted_approved_complete_shortcut_keys(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "accepted": True,
            "approved": True,
            "approvedAlias": True,
            "approval": "public",
            "complete": True,
            "nested": {"completed": True},
            "strings": ["approved=true", "approved_alias=true"],
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("claim_alias_value_present", report["blockers"])
        aliases = self.blocker_aliases(report, "claim_alias_not_false")
        self.assertEqual(
            {"accepted", "approved", "approvedAlias", "approval", "complete", "completed"} & aliases,
            {"accepted", "approved", "approvedAlias", "approval", "complete", "completed"},
        )
        string_aliases = self.blocker_aliases(report, "claim_alias_value_present")
        self.assertEqual({"approved", "approved_alias"} & string_aliases, {"approved", "approved_alias"})
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_package_or_support_text_overclaims(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = [
            "installed SDK package shape is ready",
            "support tier is ready",
            "Plugin Hub publication is published",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("package_shape_readiness", terms)
        self.assertIn("support_tier_ready", terms)
        self.assertIn("plugin_hub_ready", terms)
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_non_counting_operational_artifact_public_readiness_or_p0_text(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = [
            "runtime-window planning report approves public identity readiness",
            "no-users status marks obelisk.player_identity.v1 ready",
            "runtime presence snapshot counts toward P0 dependency chain",
            "passive runtime-presence artifact unlocks public SDK readiness",
            "installed runtime status check unlocks public SDK readiness",
            "broadcast status check counts toward P0 dependency chain",
            "RCON status artifact marks obelisk.player_identity.v1 ready",
            "runtime-window planning does not count toward P0 progress",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
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
        ):
            with self.subTest(path=path):
                self.assertIn("non_counting_artifact_public_readiness_or_p0", terms_by_path[path])
        self.assertNotIn("$.review_notes[7]", terms_by_path)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_live_authorization_claims(self) -> None:
        payload = accepted_record()
        payload["live_ops_authorized"] = True
        payload["server_operations_authorized"] = True
        payload["workspace_writes_authorized"] = True
        payload["runtime_capture_authorized"] = True
        payload["reads_live_logs"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "live_ops_authorized_not_false",
            "server_operations_authorized_not_false",
            "workspace_writes_authorized_not_false",
            "runtime_capture_authorized_not_false",
            "reads_live_logs_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_rejects_promotion_mode(self) -> None:
        result = self.run_checker(accepted_record(), "--promote")
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("promote_blocked_until_public_header_gate", report["blockers"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_public_runtime_and_v1_readiness_alias_claims(self) -> None:
        payload = accepted_record()
        payload["public_readiness"] = True
        payload["runtime_readiness"] = "ready"
        payload["v1_ready"] = True
        payload["v1_completion_ready"] = True
        payload["public_sdk_v1_completion_ready"] = True
        payload["public_sdk_v1_completion_claim"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "public_readiness_not_false",
            "runtime_readiness_not_false",
            "v1_ready_not_false",
            "v1_completion_ready_not_false",
            "public_sdk_v1_completion_ready_not_false",
            "public_sdk_v1_completion_claim_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        self.assertFalse(report["public_readiness"])
        self.assertFalse(report["runtime_readiness"])
        self.assertFalse(report["v1_completion_ready"])

    def test_rejects_p0_progress_and_counting_alias_claims(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = {
            "sdkP0ProgressReady": True,
            "p0Progress": "1/4",
            "split_progress": {"claim": "sdk_p0_progress", "progress": "1/4"},
            "counting": {"claim": "counts_toward_p0_dependency_chain_claim", "status": "satisfied"},
            "summary": "reviewed identity public contract decision record counts toward P0 progress",
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        self.assertEqual(
            {"sdkP0ProgressReady", "p0Progress"} & self.blocker_aliases(report, "claim_alias_not_false"),
            {"sdkP0ProgressReady", "p0Progress"},
        )
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        self.assertIn("sdk_p0_progress", {claim["term"] for claim in detail["claims"]})

    def test_rejects_reviewed_hash_current_metadata_p0_credit_aliases(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
            "credit": 1,
            "percent": "25%",
            "p0": "ready",
            "split": {
                "property": "reviewed_hash_current_contract_review_only",
                "value": "1/4",
            },
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
            and blocker.get("term") == "decision_record_metadata_p0_progress"
        }
        for path in (
            "$.review_metadata.credit",
            "$.review_metadata.percent",
            "$.review_metadata.p0",
            "$.review_metadata.split",
            "$.review_metadata.split.value",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_stale_runtime_evidence_and_p0_shortcut_aliases(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "stale",
            "accepted_runtime_evidence": "accepted",
            "runtimeEvidenceSatisfiesIdentityContractGate": True,
            "sdkP0ProgressReady": True,
            "p0Progress": "25%",
            "nested": {
                "hashCurrentIdentityPublicContractDecisionRecordStale": True,
                "approved_runtime_evidence_only": {"status": "ready"},
                "counts_toward_p0_dependency_chain_claim": True,
            },
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "stale_hash_current_contract_alias_present",
            "runtime_evidence_shortcut_alias_present",
            "p0_progress_alias_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        shortcut_paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] in {
                "stale_hash_current_contract_alias_present",
                "runtime_evidence_shortcut_alias_present",
                "p0_progress_alias_not_false",
            }
        }
        for path in (
            "$.review_metadata.source_artifact_hash_state",
            "$.review_metadata.accepted_runtime_evidence",
            "$.review_metadata.runtimeEvidenceSatisfiesIdentityContractGate",
            "$.review_metadata.sdkP0ProgressReady",
            "$.review_metadata.p0Progress",
            "$.review_metadata.nested.hashCurrentIdentityPublicContractDecisionRecordStale",
            "$.review_metadata.nested.approved_runtime_evidence_only",
            "$.review_metadata.nested.counts_toward_p0_dependency_chain_claim",
        ):
            with self.subTest(path=path):
                self.assertIn(path, shortcut_paths)
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_route_and_hash_current_shortcut_aliases_with_stale_source_hash(self) -> None:
        payload = accepted_record()
        payload["reviewedHashCurrentContractReviewOnly"] = True
        payload["review_metadata"] = {
            "acceptedRoute": "public_header_gate_missing",
            "runtimeEvidenceRoute": "public_sdk_ready",
            "stable_note": "stable SDK is ready",
        }
        payload["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "reviewed_hash_current_contract_review_shortcut_alias_present",
            "route_shortcut_alias_mismatch",
            "source_artifact_hash_mismatch",
            "public_text_or_source_overclaim",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        route_paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "route_shortcut_alias_mismatch"
        }
        self.assertEqual(
            route_paths,
            {"$.review_metadata.acceptedRoute", "$.review_metadata.runtimeEvidenceRoute"},
        )
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["reviewed_hash_current_contract_review_only"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")
        for key in (
            "public_header_allowed",
            "public_sdk_ready",
            "runtime_ready",
            "stable_claim_ready",
            "permissions_ready",
            "commands_ready",
            "p0_progress_ready",
            "sdk_p0_progress_ready",
        ):
            with self.subTest(key=key):
                self.assertFalse(report[key])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_provenance_status_aliases_as_public_contract_shortcuts(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
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
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
            and blocker.get("term") == "non_promotional_provenance_status_alias"
        }
        for path in (
            "$.review_metadata.route_snapshot_status.status",
            "$.review_metadata.accepted_runtime_status.source_status",
            "$.review_metadata.reviewed_contract_metadata_status.state",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_allows_zero_p0_progress_aliases_as_non_claims(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            {"sdkP0Progress": "0/4"},
            {"claim": "sdk_p0_progress", "progress": "0/4"},
            "sdkP0Progress=0/4",
        ]

        result = self.run_checker(payload)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["record_valid"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_allows_zero_reviewed_hash_current_metadata_p0_credit_aliases(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "review_status": "reviewed",
            "source_artifact_hash_state": "current",
            "scope": "contract_review_only",
            "credit": 0,
            "percent": "0%",
            "p0": "0/4",
            "split": {
                "property": "reviewed_hash_current_contract_review_only",
                "value": "0/4",
            },
        }

        result = self.run_checker(payload)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["record_valid"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_source_overclaim_zero_alias_as_contract_review_substitute(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "source_overclaim_total_flag_count": 0,
            "source_overclaim_summary": {
                "total_flag_count": 0,
                "status": "ready",
            },
            "sourceOverclaimZero": True,
        }
        payload["notes"] = [
            "source_overclaim_total_flag_count=0 unlocks public SDK readiness",
            "source_overclaim_total_flag_count=0 is diagnostics-only and non-evidence",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        source_paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
            and blocker.get("term")
            in {"source_overclaim_zero_marker", "source_overclaim_zero_status_alias"}
        }
        for path in (
            "$.review_metadata.source_overclaim_total_flag_count",
            "$.review_metadata.source_overclaim_summary.total_flag_count",
            "$.review_metadata.source_overclaim_summary.status",
            "$.review_metadata.sourceOverclaimZero",
            "$.notes[0]",
            "$.notes[1]",
        ):
            with self.subTest(path=path):
                self.assertIn(path, source_paths)
        text_detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        self.assertIn("non_counting_artifact_public_readiness_or_p0", {claim["term"] for claim in text_detail["claims"]})
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_resource_handle_readiness_alias_claims(self) -> None:
        payload = accepted_record()
        payload["resource_handle_ready"] = True
        payload["resource_handle_supported"] = "ready"
        payload["resource_handle_allowed"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "resource_handle_ready_not_false",
            "resource_handle_supported_not_false",
            "resource_handle_allowed_not_false",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])
        self.assertFalse(report["resource_handle_ready"])
        self.assertFalse(report["resource_handle_supported"])
        self.assertFalse(report["resource_handle_allowed"])

    def test_rejects_nested_dict_and_list_claim_alias_keys(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = {
            "release_statement_refs": [
                {"publicSdkReady": True},
                {"runtimeReady": "true"},
                {"stableClaimAllowed": True},
                {"v1CompletionReady": True},
                {"counts_toward_complete_sdk_claim": True},
            ],
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertGreaterEqual(report["blockers"].count("claim_alias_not_false"), 5)
        self.assertEqual(
            self.blocker_aliases(report, "claim_alias_not_false"),
            {
                "publicSdkReady",
                "runtimeReady",
                "stableClaimAllowed",
                "v1CompletionReady",
                "counts_toward_complete_sdk_claim",
            },
        )

    def test_rejects_downstream_permission_and_command_alias_claims(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = {
            "permissionsAdminUnlocked": True,
            "permissionsAdminReady": True,
            "commandsRepliesUnlocked": True,
            "commandResponseReady": True,
            "nested": [
                "permissionsAdminReady=true",
                "commandsRepliesReady=true",
                "reviewed identity public contract decision record unlocks permissions/admin",
                "commands/replies are ready",
            ],
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("claim_alias_value_present", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        self.assertEqual(
            {
                "permissionsAdminUnlocked",
                "permissionsAdminReady",
                "commandsRepliesUnlocked",
                "commandResponseReady",
            }
            & self.blocker_aliases(report, "claim_alias_not_false"),
            {
                "permissionsAdminUnlocked",
                "permissionsAdminReady",
                "commandsRepliesUnlocked",
                "commandResponseReady",
            },
        )
        self.assertEqual(
            {
                "permissionsAdminReady",
                "commandsRepliesReady",
            }
            & self.blocker_aliases(report, "claim_alias_value_present"),
            {
                "permissionsAdminReady",
                "commandsRepliesReady",
            },
        )
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("contract_review_artifact_downstream_unlocked", terms)
        self.assertIn("commands_ready", terms)

    def test_rejects_source_ready_broadcast_rcon_and_mutable_identity_alias_claims(self) -> None:
        payload = accepted_record()
        payload["review_metadata"] = {
            "principal_start_end_status": {
                "source_provenance": "principal_start_end_runtime_evidence",
                "sourceReady": True,
            },
            "broadcastReady": True,
            "rconReady": True,
            "rconReplyReady": True,
            "packageShapeReady": True,
            "pluginHubReady": True,
            "principalStartEndRuntimeEvidenceReady": True,
            "approvedRuntimePrincipalLifecycleBundleRoutesTo": "permissions/admin",
        }
        payload["review_notes"] = [
            "mutable identity surface is supported",
            "RCON command surface is supported",
            "broadcast command surface is available",
            "after accepted runtime lifecycle evidence next blocker is public_header_gate_missing",
            "approved runtime principal lifecycle bundle routes to complete SDK",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        self.assertEqual(
            {
                "sourceReady",
                "broadcastReady",
                "rconReady",
                "rconReplyReady",
                "packageShapeReady",
                "pluginHubReady",
                "principalStartEndRuntimeEvidenceReady",
                "approvedRuntimePrincipalLifecycleBundleRoutesTo",
            }
            & self.blocker_aliases(report, "claim_alias_not_false"),
            {
                "sourceReady",
                "broadcastReady",
                "rconReady",
                "rconReplyReady",
                "packageShapeReady",
                "pluginHubReady",
                "principalStartEndRuntimeEvidenceReady",
                "approvedRuntimePrincipalLifecycleBundleRoutesTo",
            },
        )
        split_terms = {
            blocker.get("term")
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
        }
        self.assertIn("non_promotional_provenance_status_alias", split_terms)
        text_detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        text_terms = {claim["term"] for claim in text_detail["claims"]}
        self.assertIn("public_mutable_resource_available", text_terms)
        self.assertIn("commands_ready", text_terms)
        self.assertIn("post_runtime_route_shortcut", text_terms)
        self.assertFalse(report["commands_ready"])
        self.assertFalse(report["public_header_allowed"])

    def test_rejects_string_claim_aliases_in_nested_arrays(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "publicSdkReady",
            {
                "release_statement_refs": [
                    "runtimeReady",
                    "stableClaimAllowed",
                    "v1CompletionReady",
                    "promoted=true",
                    "ready=true",
                    "counts_toward_complete_sdk_claim=true",
                ],
            },
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_value_present", report["blockers"])
        self.assertEqual(
            self.blocker_aliases(report, "claim_alias_value_present"),
            {
                "publicSdkReady",
                "runtimeReady",
                "stableClaimAllowed",
                "v1CompletionReady",
                "promoted",
                "ready",
                "counts_toward_complete_sdk_claim",
            },
        )

    def test_rejects_contextual_nested_claim_aliases(self) -> None:
        payload = accepted_record()
        payload["nested_claims"] = {
            "public": {"sdkReady": True},
            "runtime": {"readiness": True},
            "stable": {"claimReady": True},
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertEqual(
            {"sdkReady", "readiness", "claimReady"} & self.blocker_aliases(report, "claim_alias_not_false"),
            {"sdkReady", "readiness", "claimReady"},
        )
        self.assertFalse(report["stable_ready"])
        self.assertFalse(report["stable_claim_allowed"])
        self.assertFalse(report["stable_claim_ready"])

    def test_rejects_split_and_path_nested_claim_aliases(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = {
            "split": [
                {"claim": "public_header", "state": "ready"},
                {"name": "public_abi", "status": "promoted"},
                {"field": "runtime", "value": "authorized"},
                {"property": "identity_public_contract_decision_record", "status": "reviewed"},
                {"claim": "hash_current_identity_public_contract_decision_record", "value": True},
                {"key": "public_header_symbols_now", "values": ["ObeliskPlayerPrincipalEvent"]},
                {"claim": "public_sdk", "status": "blocked"},
            ],
            "nested": {
                "public": {"header": {"state": "ready", "symbols_now": ["ObeliskPlayerPrincipalEvent"]}},
                "stable": {"claim": {"allowed": "yes"}},
            },
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
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
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)
        self.assertNotIn("$.review_notes.split[6]", paths)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["public_header_symbols_now"], [])

    def test_rejects_direct_contract_review_only_and_mutation_alias_claims(self) -> None:
        payload = accepted_record()
        payload.update(
            {
                "identityContractDecisionRecordContractReviewOnly": True,
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
        payload["notes"] = [
            "mutation is allowed",
            "return override is ready",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
        }
        for path in (
            "$.identityContractDecisionRecordContractReviewOnly",
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
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("mutation_allowed", terms)
        self.assertIn("return_override_allowed", terms)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["permissions_ready"])
        self.assertFalse(report["commands_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_identity_public_contract_reviewed_current_alias_claims(self) -> None:
        payload = accepted_record()
        payload.update(
            {
                "identityContractReviewed": True,
                "identityPublicContractReviewed": True,
                "identityPublicContractCurrent": True,
                "identityPublicContractHashCurrent": True,
                "publicIdentityContractReviewed": True,
                "publicIdentityContractHashCurrent": True,
                "reviewedIdentityPublicContractHashCurrent": True,
                "reviewedIdentityPublicContractRecord": True,
            }
        )
        payload["notes"] = [
            "identityPublicContractReviewed=true",
            "identityPublicContractHashCurrent=true",
            "publicIdentityContractReviewed=true",
            "reviewedIdentityPublicContractHashCurrent=true",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("claim_alias_value_present", report["blockers"])
        direct_aliases = self.blocker_aliases(report, "claim_alias_not_false")
        for alias in (
            "identityContractReviewed",
            "identityPublicContractReviewed",
            "identityPublicContractCurrent",
            "identityPublicContractHashCurrent",
            "publicIdentityContractReviewed",
            "publicIdentityContractHashCurrent",
            "reviewedIdentityPublicContractHashCurrent",
            "reviewedIdentityPublicContractRecord",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, direct_aliases)
        string_aliases = self.blocker_aliases(report, "claim_alias_value_present")
        for alias in (
            "identityPublicContractReviewed",
            "identityPublicContractHashCurrent",
            "publicIdentityContractReviewed",
            "reviewedIdentityPublicContractHashCurrent",
        ):
            with self.subTest(string_alias=alias):
                self.assertIn(alias, string_aliases)
        self.assertFalse(report["record_valid"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual(report["next_blocker"], "identity_public_contract_gate_missing")

    def test_rejects_post_runtime_shortcut_aliases_as_public_readiness(self) -> None:
        payload = accepted_record()
        payload["review_notes"] = {
            "identity_contract_hash_current": True,
            "header_shape_valid": True,
            "p0_unlocked": "identity",
            "blocker_resolved": "runtime",
            "public": {"surface": {"status": "accepted"}},
            "strings": [
                "identity_contract_hash_current=true",
                "header_shape_valid=true",
                "p0_unlocked=identity",
                "blocker_resolved=runtime",
            ],
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("claim_alias_not_false", report["blockers"])
        self.assertIn("claim_alias_value_present", report["blockers"])
        self.assertIn("split_or_nested_claim_alias_present", report["blockers"])
        direct_paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "claim_alias_not_false"
        }
        for path in (
            "$.review_notes.identity_contract_hash_current",
            "$.review_notes.header_shape_valid",
            "$.review_notes.p0_unlocked",
            "$.review_notes.blocker_resolved",
        ):
            with self.subTest(path=path):
                self.assertIn(path, direct_paths)
        split_paths = {
            blocker["label"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "split_or_nested_claim_alias_present"
        }
        self.assertIn("$.review_notes.public.surface.status", split_paths)
        string_aliases = {
            blocker["alias"]
            for blocker in report["blocker_details"]
            if blocker["reason"] == "claim_alias_value_present"
        }
        for alias in (
            "identity_contract_hash_current",
            "header_shape_valid",
            "p0_unlocked",
            "blocker_resolved",
        ):
            with self.subTest(alias=alias):
                self.assertIn(alias, string_aliases)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_freeform_public_readiness_text_overclaims(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "public header is ready",
            "runtime lifecycle evidence unlocks public sdk",
            "reviewed_identity_public_contract_decision_record unlocks public header",
            "LookupPlayerPrincipal is available",
            "player identity lookup surface",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertEqual(
            paths,
            {
                "$.notes[0]",
                "$.notes[1]",
                "$.notes[2]",
                "$.notes[3]",
                "$.notes[4]",
            },
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("public_header_ready", terms)
        self.assertIn("contract_review_artifact_public_header", terms)
        self.assertIn("public_lookup_or_resource_handle_available", terms)
        self.assertIn("broad_identity_lookup_wording", terms)

    def test_rejects_runtime_evidence_overclaims_to_public_api_abi_header(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "approved runtime lifecycle evidence advances to public header gate",
            "runtime lifecycle evidence routes to public_api_gate_missing",
            "next blocker public_abi_gate_missing",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("runtime_evidence_public_shortcut", terms)
        self.assertIn("public_route_blocker_shortcut", terms)

    def test_rejects_accepted_runtime_evidence_public_sdk_and_p0_unlock_text(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "accepted runtime evidence unlocks public SDK readiness",
            "accepted runtime lifecycle evidence unlocks downstream P0",
            "runtime lifecycle evidence routes to P0 dependency chain",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("runtime_evidence_public_shortcut", terms)
        self.assertIn("contract_review_artifact_p0_unlock", terms)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_rejects_promotion_like_public_contract_evidence_wording(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "identity_public_contract_gate_missing is resolved, public header is ready",
            "reviewed identity public contract decision record is sufficient evidence for public contract promotion",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertEqual(paths, {"$.notes[0]", "$.notes[1]"})
        terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("public_header_ready", terms)
        self.assertIn("promotion_like_public_contract_evidence", terms)

    def test_rejects_contract_review_metadata_public_readiness_and_p0_unlock_text(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            "reviewed hash-current contract-review-only record marks public header readiness satisfied",
            "contract-review-only record unlocks downstream P0",
            "reviewed identity public contract decision record opens P0 dependency chain",
            "contract-review-only record does not unlock downstream P0",
        ]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "public_text_or_source_overclaim"
        )
        terms_by_path: dict[str, set[str]] = {}
        for claim in detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("contract_review_metadata_public_readiness", terms_by_path["$.notes[0]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$.notes[1]"])
        self.assertIn("contract_review_artifact_p0_unlock", terms_by_path["$.notes[2]"])
        self.assertNotIn("$.notes[3]", terms_by_path)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])

    def test_rejects_stale_or_mismatched_source_artifact_hashes(self) -> None:
        payload = accepted_record()
        payload["source_artifacts"]["public_contract_decisions"]["sha256"] = "0" * 64
        payload["source_artifacts"]["public_abi_preflight_candidate"][
            "path"
        ] = "docs/research/player-identity-planning-sources/player-identity-public-header-gate-proposal.json"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifact_hash_mismatch", report["blockers"])
        self.assertIn("source_artifact_path_mismatch", report["blockers"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "stale_or_mismatched")
        self.assertFalse(report["source_artifact_freshness"]["current"])
        self.assertEqual(
            report["source_artifact_freshness"]["mismatches"],
            [
                {
                    "label": "public_contract_decisions",
                    "path": "docs/player_identity_public_contract_decisions.json",
                    "reason": "source_artifact_hash_mismatch",
                    "expected_sha256": sha256_file("docs/player_identity_public_contract_decisions.json"),
                    "observed_sha256": "0" * 64,
                    "required_action": checker.SOURCE_ARTIFACT_STALE_REQUIRED_ACTION,
                    "current_route": "approved_runtime_evidence_missing",
                    "post_runtime_evidence_next_blocker": "identity_public_contract_gate_missing",
                    "counts_toward_public_sdk": False,
                    "counts_toward_p0_dependency_chain_claim": False,
                }
            ],
        )
        self.assertEqual(
            report["runtime_evidence_contract_review_currentness"]["observed"][
                "source_artifact_mismatches"
            ],
            report["source_artifact_freshness"]["mismatches"],
        )

    def test_rejects_partial_hash_fields_in_source_artifacts(self) -> None:
        payload = accepted_record()
        current = payload["source_artifacts"]["public_contract_decisions"]["sha256"]
        payload["source_artifacts"]["public_contract_decisions"]["sha256_prefix"] = current[:12]

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifact_entry_keys_mismatch", report["blockers"])
        self.assertIn("source_artifact_partial_or_extra_hash_claimed", report["blockers"])
        self.assertFalse(report["hash_bound_to_current_source_artifacts"])
        self.assertEqual(report["source_artifact_freshness"]["status"], "invalid_or_unverified")

    def test_rejects_symlinked_source_artifact_before_hashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "docs" / "player_identity_public_contract_decisions.json"
            source.parent.mkdir(parents=True)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            source.symlink_to(target)
            payload = {
                "source_artifacts": {
                    "public_contract_decisions": {
                        "path": "docs/player_identity_public_contract_decisions.json",
                        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "role": "post_runtime_identity_contract_gate_policy",
                        "counting_scope": "reviewed_identity_public_contract_review",
                    }
                }
            }
            blockers: list[dict] = []
            with (
                mock.patch.object(checker, "REPO_ROOT", root),
                mock.patch.object(
                    checker,
                    "EXPECTED_SOURCE_ARTIFACTS",
                    {
                        "public_contract_decisions": {
                            "path": "docs/player_identity_public_contract_decisions.json",
                            "role": "post_runtime_identity_contract_gate_policy",
                        }
                    },
                ),
            ):
                checker.validate_source_artifacts(payload, blockers)

        self.assertIn("source_artifact_path_rejected", [blocker["reason"] for blocker in blockers])

    def test_rejects_route_blocker_aliases_to_public_header_api_or_abi(self) -> None:
        payload = accepted_record()
        payload["route"]["after_accepted_runtime_evidence_next_blocker"] = "public_header_gate_missing"
        payload["route"]["accepted_runtime_lifecycle_evidence_advances_to"] = "public_api_gate_missing"
        payload["route_blocker_aliases"]["publicHeaderGateMissingAfterRuntimeEvidence"] = True
        payload["route_blocker_aliases"]["publicApiGateMissingAfterRuntimeEvidence"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("route_after_accepted_runtime_evidence_next_blocker_mismatch", report["blockers"])
        self.assertIn("route_accepted_runtime_lifecycle_evidence_advances_to_mismatch", report["blockers"])
        self.assertIn("route_public_header_api_abi_shortcut_claimed", report["blockers"])
        self.assertIn("route_blocker_alias_not_false", report["blockers"])
        alias_labels = {
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "route_blocker_alias_not_false"
        }
        self.assertIn("$.route_blocker_aliases.publicHeaderGateMissingAfterRuntimeEvidence", alias_labels)
        self.assertIn("$.route_blocker_aliases.publicApiGateMissingAfterRuntimeEvidence", alias_labels)

    def test_rejects_extra_route_keys_that_claim_identity_gate_resolution(self) -> None:
        payload = accepted_record()
        payload["route"]["identityPublicContractGateOpen"] = True
        payload["route"]["identityPublicContractGateMissingResolved"] = True
        payload["route"]["publicHeaderGateOpen"] = True

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("route_keys_mismatch", report["blockers"])
        detail = next(
            blocker for blocker in report["blocker_details"] if blocker["reason"] == "route_keys_mismatch"
        )
        self.assertIn("identityPublicContractGateOpen", detail["observed"])
        self.assertIn("identityPublicContractGateMissingResolved", detail["observed"])
        self.assertIn("publicHeaderGateOpen", detail["observed"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_api_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_notice_only_artifacts_as_source_artifacts(self) -> None:
        payload = accepted_record()
        payload["source_artifacts"]["beta_notice"] = {
            "path": "docs/research/player-principal-lifecycle-beta-notice.json",
            "sha256": "1" * 64,
            "role": "notice_only",
            "counting_scope": "reviewed_identity_public_contract_review",
        }

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("source_artifacts_keys_mismatch", report["blockers"])
        self.assertIn("source_artifacts_notice_only_or_non_counting_claimed", report["blockers"])
        detail = next(
            blocker
            for blocker in report["blocker_details"]
            if blocker["reason"] == "source_artifacts_notice_only_or_non_counting_claimed"
        )
        values = {claim["value"] for claim in detail["claims"]}
        self.assertIn("beta_notice", values)
        self.assertIn("docs/research/player-principal-lifecycle-beta-notice.json", values)

    def test_rejects_public_header_api_abi_shortcut_fields_and_sources(self) -> None:
        payload = accepted_record()
        payload["accepted_for_header_gate_review"] = True
        payload["accepted_for_public_api_review"] = True
        payload["public_header_gate_unlocked"] = True
        payload["public_api_gate_ready"] = True
        payload["public_abi_gate_unlocked"] = True
        payload["source_artifacts"]["public_contract_decisions"][
            "path"
        ] = "docs/research/player-identity-planning-sources/player-identity-public-header-gate-proposal.json"

        result = self.run_checker(payload)

        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        for blocker in (
            "accepted_for_header_gate_review_not_false",
            "accepted_for_public_api_review_not_false",
            "public_header_gate_unlocked_not_false",
            "public_api_gate_ready_not_false",
            "public_abi_gate_unlocked_not_false",
            "source_artifacts_public_header_api_abi_shortcut_claimed",
            "source_artifact_path_mismatch",
        ):
            with self.subTest(blocker=blocker):
                self.assertIn(blocker, report["blockers"])

    def test_allows_nested_false_claim_alias_fields_and_strings(self) -> None:
        payload = accepted_record()
        payload["notes"] = [
            {
                "ready": False,
                "publicSdkReady": False,
                "runtimeReady": "false",
                "stableClaimAllowed": False,
                "v1CompletionReady": False,
                "promoted": False,
                "counts_toward_complete_sdk_claim": False,
            },
            "publicSdkReady=false",
            "runtimeReady: false",
            "stableClaimAllowed=false",
            "v1CompletionReady=false",
            "promoted=false",
            "ready=false",
            "counts_toward_complete_sdk_claim=false",
        ]

        result = self.run_checker(payload)

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertTrue(report["record_valid"])

    def test_rejects_public_and_runtime_readiness_modes(self) -> None:
        for flag, blocker in (
            ("--public-readiness", "public_readiness_blocked_until_public_header_gate"),
            ("--runtime-readiness", "runtime_readiness_blocked_until_public_header_gate"),
        ):
            with self.subTest(flag=flag):
                result = self.run_checker(accepted_record(), flag)

                self.assertNotEqual(result.returncode, 0)
                report = json.loads(result.stdout)
                self.assertIn(blocker, report["blockers"])
                self.assertFalse(report["public_readiness"])
                self.assertFalse(report["runtime_readiness"])
                self.assertFalse(report["v1_completion_ready"])


if __name__ == "__main__":
    unittest.main()
