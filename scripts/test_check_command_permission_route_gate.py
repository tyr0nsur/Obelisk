#!/usr/bin/env python3
"""Tests for check_command_permission_route_gate.py."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


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
from test_check_player_identity_runtime_principal_lifecycle_approved_evidence import (
    manifest as approved_runtime_principal_lifecycle_manifest,
)


def identity_manifest_sources(
    *,
    mode: str = "repo_local_default",
    lifecycle: Path | None = None,
    principal: Path | None = None,
) -> dict:
    lifecycle_path = lifecycle or ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
    principal_path = principal or ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
    return {
        "mode": mode,
        "report_available": True,
        "expected_manifests_received": True,
        "manifests": {
            "lifecycle_anchor_candidates": {
                "source": mode,
                "provided_by_cli": mode == "cli_bound",
                "expected_path": str(lifecycle_path),
                "expected_resolved_path": str(lifecycle_path.resolve()),
                "observed_path": str(lifecycle_path),
                "observed_resolved_path": str(lifecycle_path.resolve()),
                "matched": True,
            },
            "principal_invalidation_policy": {
                "source": mode,
                "provided_by_cli": mode == "cli_bound",
                "expected_path": str(principal_path),
                "expected_resolved_path": str(principal_path.resolve()),
                "observed_path": str(principal_path),
                "observed_resolved_path": str(principal_path.resolve()),
                "matched": True,
            },
        },
        "non_claim": (
            "manifest source diagnostics bind identity planning inputs only; they do not promote "
            "public identity, permissions, commands, runtime readiness, or SDK completion"
        ),
    }


def approved_runtime_diagnosis(path: Path, *, ready: bool = True) -> dict:
    return {
        "provided": True,
        "path": str(path),
        "report_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1",
        "input_schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "next_blocker": "identity_public_contract_gate_missing" if ready else "approved_runtime_evidence_missing",
        "ready": ready,
        "approved_runtime_evidence_present": ready,
        "runtime_evidence_ready": ready,
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
        "observed_runtime_cases": ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES if ready else [],
        "consumer_cases": ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES if ready else [],
        "remaining_blockers": [] if ready else ["approved_runtime_evidence_missing"],
        "blockers": [] if ready else ["approved_runtime_manifest_not_accepted"],
    }


def hash_bound_player_identity_promotion_certificate_binding(path: Path) -> dict[str, str]:
    reviewed_surface_hash = "1" * 64
    review_record = {
        "schema": ROUTE_GATE.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
        "artifact_id": ROUTE_GATE.PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
        "surface": "obelisk.player_identity.v1",
        "active_after_resolved_input": ROUTE_GATE.PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
        "review_status": "reviewed",
        "accepted_for_contract_review": True,
        "next_blocker": "public_header_gate_missing",
        "reviewed_surface_record_sha256": reviewed_surface_hash,
        "resolved_decision_keys": list(ROUTE_GATE.PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS),
    }
    for key in ROUTE_GATE.PLAYER_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
        review_record[key] = False
    for key, expected in ROUTE_GATE.PLAYER_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS.items():
        review_record[key] = expected
    certificate = {
        "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "surface_id": "obelisk.player_identity.v1",
        "promotion_status": "promoted",
        "v1_dependency_chain": ROUTE_GATE.CANONICAL_V1_DEPENDENCY_SEQUENCE,
        "v1_dependency_chain_position": 1,
        "required_by_surface": "obelisk.permissions_admin.v1",
        "required_by_v1_dependency_chain_position": 2,
        "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
        "reviewed_artifact_hash_policy": (
            "must match the reviewed identity surface record hash carried by the certificate"
        ),
        "missing_mismatched_or_stale_certificate_counts": False,
        "evidence": {
            "reviewed_artifact_hash": reviewed_surface_hash,
            "reviewed_surface_record_sha256": reviewed_surface_hash,
            "promotion_evidence_kind": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_PROMOTION_EVIDENCE_KIND,
            "semantic_proofs": sorted(
                ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIRED_SEMANTIC_PROOFS
            ),
            "identity_public_contract_decision_record": review_record,
            "identity_public_contract_decision_record_sha256": ROUTE_GATE.canonical_json_sha256(
                review_record
            ),
        },
    }
    for key in ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_FALSE_KEYS:
        certificate["evidence"][key] = False
    path.write_text(json.dumps(certificate, sort_keys=True), encoding="utf-8")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def identity_phase(
    blocker: str = "approved_runtime_evidence_missing",
    *,
    approved_runtime_path: Path | None = None,
) -> dict:
    next_action_by_blocker = {
        "lifecycle_anchor_first_evidence_provenance_unbound": "bind_lifecycle_anchor_and_principal_policy_sources",
        "approved_runtime_evidence_missing": "produce_approved_runtime_principal_lifecycle_evidence",
        "identity_public_contract_gate_missing": "review_identity_public_contract_gate",
    }
    approved_runtime_ready = blocker == "identity_public_contract_gate_missing"
    if approved_runtime_path is None:
        approved_runtime_path = Path("/tmp/approved-runtime-principal-lifecycle.json")
    return {
        "current_surface": "obelisk.player_identity.v1",
        "current_blocker": blocker,
        "source_checker_primary_blocker": blocker,
        "source_checker_next_blocker": None,
        "next_action": next_action_by_blocker[blocker],
        "next_after_runtime_evidence": "identity_public_contract_gate_missing",
        "permissions_admin_unlocked": False,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "source_checker": "check_player_identity_first_evidence_readiness.py",
        "source_checker_exit_code": 1,
        "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
        "source_checker_parse_error": None,
        "source_checker_status": "blocked",
        "source_checker_ready": False,
        "source_checker_accepted_for_internal_planning": False,
        "source_checker_blockers": [blocker],
        "source_checker_manifest_sources": identity_manifest_sources(),
        "source_checker_approved_runtime_evidence_manifest": approved_runtime_diagnosis(
            approved_runtime_path,
            ready=approved_runtime_ready,
        ),
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
    }


class CommandPermissionRouteGateTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_post_runtime_child_lock_quarantine_requires_locked_false_non_claiming_child(self) -> None:
        check = {
            "name": "permissions_admin_public_readiness",
            "parse_error": None,
            "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["permissions_admin_public_readiness"],
            "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["permissions_admin_public_readiness"],
            "dependency_chain_locked": True,
            "current_route_blocker": "identity_public_contract_gate_missing",
            "remaining_route_blockers": ["identity_public_contract_gate_missing"],
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "public_or_runtime_accounting_allowed": False,
            "public_or_runtime_claims": [],
            "blockers": sorted(ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_BLOCKERS),
        }

        self.assertTrue(ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(check))

        check["public_or_runtime_claims"] = sorted(
            ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_CLAIMS
        )
        self.assertTrue(ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(check))

        check["public_or_runtime_claims"] = ["public_sdk_ready"]
        self.assertFalse(ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(check))

        check["public_or_runtime_claims"] = []
        check["current_route_blocker"] = "public_header_gate_missing"
        self.assertFalse(ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(check))

        check["name"] = "commands_replies_public_readiness"
        check["report_schema"] = ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"]
        check["expected_schema"] = ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["commands_replies_public_readiness"]
        check["current_route_blocker"] = "identity_public_contract_gate_missing"
        check["blockers"] = sorted(
            ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_BLOCKERS
            | ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_RESPONSE_REPORT_DERIVED_BLOCKERS
        )
        self.assertFalse(ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(check))
        self.assertTrue(
            ROUTE_GATE.locked_child_post_runtime_identity_contract_quarantined(
                check,
                response_path_report_quarantined=True,
            )
        )

    def test_post_runtime_identity_gap_quarantine_requires_exact_contract_lock(self) -> None:
        report = {
            "status": "blocked",
            "current_blocker": "identity_public_contract_gate_missing",
            "next_blocker": "identity_public_contract_gate_missing",
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "runtime_ready": False,
            "v1_completion_evidence": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "identity_public_contract_gate_missing": {"active": True},
            "post_approved_runtime_evidence_gate": {
                "active": True,
                "next_blocker": "identity_public_contract_gate_missing",
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
            },
            "post_approved_runtime_evidence_route_check": {
                "contract_review_input_present": True,
                "gap_report_valid": False,
                "invalid_gap_report": True,
                "diagnostic_current_blocker": "identity_public_contract_gate_missing",
                "diagnostic_next_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blocker_is_legitimate": False,
                "legitimate_remaining_route_blocker": None,
            },
            "post_runtime_public_identity_gap_summary": {
                "active": True,
                "current_blocker": "identity_public_contract_gate_missing",
                "next_blocker": "identity_public_contract_gate_missing",
                "only_valid_post_runtime_route": "identity_public_contract_gate_missing",
                "approved_runtime_bundle_consumed": True,
                "approved_runtime_evidence_scope": "consume_only_contract_review_input",
                "permissions_admin_opened": False,
                "permissions_admin_ready": False,
                "command_chat_response_ready": False,
                "commands_replies_ready": False,
                "promotion_ready": False,
                "public_contract_allowed": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "public_api_ready": False,
                "public_sdk_ready": False,
                "public_readiness": False,
                "runtime_ready": False,
                "runtime_readiness": False,
                "lookup_ready": False,
                "permissions_ready": False,
                "commands_ready": False,
            },
        }
        check = {
            "name": "player_identity_public_contract_gap",
            "parse_error": None,
            "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["player_identity_public_contract_gap"],
            "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["player_identity_public_contract_gap"],
            "public_or_runtime_claims": sorted(
                ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_CLAIMS
            ),
            "blockers": sorted(ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_GAP_CHECK_BLOCKERS),
            "report_payload": report,
        }

        self.assertTrue(ROUTE_GATE.identity_gap_post_runtime_contract_lock_quarantined(check))

        overclaim = copy.deepcopy(check)
        overclaim["public_or_runtime_claims"] = ["public_sdk_ready"]
        self.assertFalse(ROUTE_GATE.identity_gap_post_runtime_contract_lock_quarantined(overclaim))

        wrong_blocker = copy.deepcopy(check)
        wrong_blocker["report_payload"]["current_blocker"] = "approved_runtime_evidence_missing"
        self.assertFalse(ROUTE_GATE.identity_gap_post_runtime_contract_lock_quarantined(wrong_blocker))

        ready_flag = copy.deepcopy(check)
        ready_flag["report_payload"]["post_runtime_public_identity_gap_summary"]["public_sdk_ready"] = True
        self.assertFalse(ROUTE_GATE.identity_gap_post_runtime_contract_lock_quarantined(ready_flag))

    def test_identity_lock_mode_accepts_default_route_at_runtime_evidence_blocker(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
        )
        phase = {
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_primary_blocker": "approved_runtime_evidence_missing",
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertEqual(blockers, [])

    def test_identity_lock_mode_accepts_lifecycle_provenance_route_lock(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
        )
        phase = {
            "current_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertEqual([], blockers)

    def test_lifecycle_provenance_lock_still_rejects_malformed_runtime_evidence_diagnosis(self) -> None:
        approved_runtime = Path("approved-runtime.json")
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )
        phase = {
            "current_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_primary_blocker": "lifecycle_anchor_first_evidence_provenance_unbound",
            "source_checker_approved_runtime_evidence_manifest": {
                **approved_runtime_diagnosis(approved_runtime),
                "report_schema": "old.approved-runtime-check.v0",
                "counts_toward_runtime": True,
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn("critical_path_approved_runtime_evidence_report_schema_mismatch", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_counts_toward_runtime_not_false", blockers)

    def test_identity_lock_rejects_accepted_runtime_diagnosis_with_handoff_or_p0_progress(self) -> None:
        approved_runtime = Path("approved-runtime.json")
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": {
                **approved_runtime_diagnosis(approved_runtime),
                "handoff_notes": {"status": "accepted"},
                "side_lane_artifact": {"progress": "1/4"},
                "p0_dependency_chain_claim_progress_contribution": 1,
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn("critical_path_approved_runtime_evidence_public_or_runtime_claim", blockers)
        self.assertIn(
            "critical_path_approved_runtime_evidence_p0_dependency_chain_claim_progress_contribution_not_zero",
            blockers,
        )
        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_lifecycle_provenance_route_lock_skips_downstream_p0_children(self) -> None:
        args = SimpleNamespace(
            query_failclosed_artifact=QUERY_CONTRACT,
            player_identity_decisions=IDENTITY_DECISIONS,
            public_sdk_surfaces=PUBLIC_SDK_SURFACES,
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
        phase = identity_phase("lifecycle_anchor_first_evidence_provenance_unbound")

        def run_check_with_child_contract(name: str, argv: list[str]) -> dict[str, object]:
            child_blocker = None
            if "--current-route-blocker" in argv:
                child_blocker = argv[argv.index("--current-route-blocker") + 1]
            result: dict[str, object] = {
                "name": name,
                "argv": argv,
                "exit_code": 0,
                "valid": True,
                "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "planning_only": name in ROUTE_GATE.REQUIRED_PLANNING_ONLY_CHECKS,
                "accepted_for_planning": name in ROUTE_GATE.REQUIRED_PLANNING_ONLY_CHECKS,
                "dependency_chain_locked": None,
                "current_route_blocker": None,
                "remaining_route_blockers": None,
                "counts_toward_public_sdk": None,
                "counts_toward_runtime": None,
                "counts_toward_v1_completion": None,
                "public_or_runtime_accounting_allowed": None,
                "public_or_runtime_claims": [],
                "blockers": [],
                "parse_error": None,
                "stderr": "",
                "report_payload": {},
            }
            if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS:
                self.fail(f"upstream lifecycle provenance lock should skip downstream P0 child {name}")
                result.update(
                    {
                        "dependency_chain_locked": True,
                        "current_route_blocker": child_blocker,
                        "remaining_route_blockers": [child_blocker],
                        "counts_toward_public_sdk": False,
                        "counts_toward_runtime": False,
                        "counts_toward_v1_completion": False,
                        "public_or_runtime_accounting_allowed": False,
                    }
                )
            if name == "command_chat_response_public_readiness":
                result["report_payload"] = {
                    "readiness_root": "/tmp",
                    "readiness_path": f"/tmp/{ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME}",
                }
            return result

        with (
            mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=phase),
            mock.patch.object(ROUTE_GATE, "run_check", side_effect=run_check_with_child_contract),
        ):
            report = ROUTE_GATE.build_report(args)

        self.assertTrue(report["valid"])
        self.assertEqual("lifecycle_anchor_first_evidence_provenance_unbound", report["current_route_blocker"])
        self.assertEqual(["lifecycle_anchor_first_evidence_provenance_unbound"], report["remaining_route_blockers"])
        check_names = {check["name"] for check in report["checks"]}
        self.assertNotIn("player_identity_public_contract_gap", check_names)
        self.assertFalse(check_names & ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS)

    def test_identity_lock_mode_allows_approved_runtime_evidence_to_reach_public_contract_gate(self) -> None:
        approved_runtime = Path("approved-runtime.json")
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": approved_runtime_diagnosis(approved_runtime),
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertEqual([], blockers)

    def test_identity_lock_mode_rejects_ready_runtime_diagnosis_not_bound_to_cli_manifest(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("approved-runtime.json"),
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": approved_runtime_diagnosis(
                Path("request-pack-sidecar.json")
            ),
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn("critical_path_approved_runtime_evidence_path_unbound", blockers)
        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_identity_lock_mode_rejects_minimal_stale_ready_runtime_diagnosis(self) -> None:
        approved_runtime = Path("approved-runtime.json")
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": {
                "path": str(approved_runtime),
                "ready": True,
                "approved_runtime_evidence_present": True,
                "runtime_evidence_ready": True,
                "remaining_blockers": [],
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn("critical_path_approved_runtime_evidence_promotion_ready_not_false", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_public_capability_bits_now_not_empty", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_report_schema_mismatch", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_next_blocker_unexpected", blockers)
        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_identity_lock_mode_rejects_stale_runtime_report_shape_with_ready_flags(self) -> None:
        approved_runtime = Path("approved-runtime.json")
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": {
                **approved_runtime_diagnosis(approved_runtime),
                "report_schema": "old.approved-runtime-check.v0",
                "mode": "public-readiness",
                "ready_scope": "public_identity",
                "next_blocker": "permissions_admin_gate_missing",
                "counts_toward_public_sdk": True,
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn("critical_path_approved_runtime_evidence_report_schema_mismatch", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_mode_not_consume", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_ready_scope_not_runtime_evidence_only", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_next_blocker_unexpected", blockers)
        self.assertIn("critical_path_approved_runtime_evidence_counts_toward_public_sdk_not_false", blockers)
        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_identity_lock_mode_keeps_runtime_blocker_for_unaccepted_approved_runtime_argument(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("arbitrary.json"),
        )
        phase = {
            "current_blocker": "approved_runtime_evidence_missing",
            "source_checker_primary_blocker": "approved_runtime_evidence_missing",
            "source_checker_approved_runtime_evidence_manifest": {
                "provided": True,
                "ready": False,
                "approved_runtime_evidence_present": False,
                "runtime_evidence_ready": False,
                "remaining_blockers": ["approved_runtime_evidence_missing"],
                "blockers": ["approved_runtime_manifest_schema_mismatch"],
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertEqual([], blockers)

    def test_identity_lock_mode_rejects_public_contract_gate_without_accepted_runtime_diagnosis(self) -> None:
        args = SimpleNamespace(
            player_identity_lifecycle_anchor_candidates_manifest=Path("bound-lifecycle.json"),
            player_identity_principal_invalidation_policy_manifest=Path("bound-principal.json"),
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("arbitrary.json"),
        )
        phase = {
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_approved_runtime_evidence_manifest": {
                "provided": True,
                "ready": False,
                "approved_runtime_evidence_present": False,
                "runtime_evidence_ready": False,
                "remaining_blockers": ["approved_runtime_evidence_missing"],
            },
        }

        blockers = ROUTE_GATE.validate_identity_lock_mode(args, phase)

        self.assertIn(
            "critical_path_identity_gate_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )
        self.assertIn(
            "critical_path_identity_readiness_mode_unexpected_blocker:'identity_public_contract_gate_missing'!='approved_runtime_evidence_missing'",
            blockers,
        )

    def test_collect_claims_rejects_runtime_evidence_source_aliases(self) -> None:
        payload = {
            "runtime_evidence_source": [
                "window_request",
                {"operator": "operator_approval_request"},
                "observer_window_env",
                "runtime_principal_lifecycle_start_end_evidence",
                "public_readiness",
                "source_marker",
            ]
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(payload, include_text_claims=False)

        self.assertEqual(["runtime_evidence_source"], claims)

    def test_collect_claims_allows_approved_runtime_evidence_blocker_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "first_evidence_boundary": {
                    "approved_runtime_evidence_missing": True,
                },
                "header_gate": {
                    "approved_runtime_evidence_required_before_header_gate": True,
                },
                "approved_runtime_evidence_ready": True,
                "approved_runtime_evidence_accepted": True,
            },
            include_text_claims=False,
        )

        self.assertNotIn("first_evidence_boundary.approved_runtime_evidence_missing", claims)
        self.assertNotIn("header_gate.approved_runtime_evidence_required_before_header_gate", claims)
        self.assertIn("approved_runtime_evidence_ready", claims)
        self.assertIn("approved_runtime_evidence_accepted", claims)

    def test_collect_claims_rejects_notice_status_aliases(self) -> None:
        payload = {
            "playerNoticeActionStatus": "sent",
            "noticeActionResult": "accepted",
            "player_notice": {"deliveryStatus": "delivered"},
            "notice_bundle_accepted": True,
            "approved_runtime_evidence_accepted": True,
            "beta_notice_send_attestation": {
                "mode": "confirmed_send",
                "status": "confirmed_send",
            },
            "beta_notice_sent": True,
            "confirmed_beta_notice_sent": True,
            "approved_bundle_request_accepted": True,
            "approved_runtime_bundle_request_accepted": True,
            "public_reachability": {"status": "reachable"},
            "public_readiness": {"status": "ready"},
            "route_simulation": {"status": "accepted", "progress": "1/12"},
            "post_evidence_identity_lock": {
                "identity_lock_ready": True,
                "p0_dependency_chain_progress_contribution": 1,
            },
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
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            payload,
            include_text_claims=False,
        )

        self.assertEqual(
            [
                "approved_bundle_request_accepted",
                "approved_runtime_bundle_request_accepted",
                "approved_runtime_evidence_accepted",
                "beta_notice_send_attestation.mode",
                "beta_notice_send_attestation.status",
                "beta_notice_sent",
                "confirmed_beta_notice_sent",
                "noticeActionResult",
                "notice_bundle_accepted",
                "playerNoticeActionStatus",
                "player_notice.deliveryStatus",
                "post_evidence_identity_lock.identity_lock_ready",
                "post_evidence_identity_lock.p0_dependency_chain_progress_contribution",
                "public_reachability",
                "public_reachability.status",
                "public_readiness",
                "public_readiness.status",
                "route_simulation.progress",
                "route_simulation.status",
                "source_marker",
                "source_marker_list_pair.source_state",
                "source_marker_pair.status",
                "source_status",
            ],
            claims,
        )

    def test_collect_claims_rejects_provenance_status_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "route_snapshot_provenance": {
                    "source_provenance": "route_snapshot",
                    "status": "accepted",
                },
                "accepted_runtime_evidence_provenance": {
                    "source_provenance": "accepted_runtime_evidence_only",
                    "source_status": "ready",
                },
                "reviewed_contract_metadata_provenance": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
            },
            include_text_claims=False,
        )

        self.assertIn("route_snapshot_provenance.status", claims)
        self.assertIn("accepted_runtime_evidence_provenance.source_status", claims)
        self.assertIn("reviewed_contract_metadata_provenance.state", claims)

    def test_materialized_runtime_evidence_route_context_uses_canonical_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "public-sdk-surfaces-route-context.json"
            path, context, blockers = ROUTE_GATE.materialize_route_context_surfaces(
                PUBLIC_SDK_SURFACES,
                output,
                approved_runtime_evidence_accepted=True,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))

        identity = next(
            surface
            for surface in payload["surfaces"]
            if surface["id"] == "obelisk.player_identity.v1"
        )
        accepted = identity["evidence"]["accepted_runtime_evidence"]
        binding = accepted["approved_runtime_evidence_binding"]

        self.assertEqual([], blockers)
        self.assertTrue(context["accepted_runtime_evidence_context"])
        self.assertEqual(ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA, accepted["schema"])
        self.assertTrue(accepted["approved_runtime_evidence_binding_required"])
        self.assertEqual(ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA, binding["schema"])
        self.assertEqual(
            ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
            binding["resolved_input"],
        )
        self.assertEqual("identity_public_contract_gate_missing", binding["next_blocker"])
        self.assertEqual(
            ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
            binding["binding_scope"],
        )
        for key in ROUTE_GATE.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS:
            self.assertFalse(binding[key], key)
        self.assertEqual(
            [],
            ROUTE_GATE.collect_public_or_runtime_claims(accepted, include_text_claims=True),
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
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_complete_sdk_claim"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(0, report["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertTrue(report["route_blocked"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertTrue(report["route_lock_invariant_valid"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(
            ["approved_runtime_evidence_missing"],
            report["remaining_route_blockers"],
        )
        self.assertEqual(
            "produce_approved_runtime_principal_lifecycle_evidence",
            report["next_route_action"],
        )
        self.assertEqual(
            "identity_public_contract_gate_missing",
            report["next_route_blocker_after_runtime_evidence"],
        )
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )
        self.assertEqual(7, len(report["checks"]))
        self.assertEqual(
            "approved_runtime_evidence_missing",
            report["critical_path_phase"]["current_blocker"],
        )
        self.assertEqual(
            "approved_runtime_evidence_missing",
            report["critical_path_phase"]["source_checker_primary_blocker"],
        )
        self.assertIn(
            "approved_runtime_evidence_missing",
            report["critical_path_phase"]["source_checker_blockers"],
        )
        self.assertEqual(
            {
                "locked": True,
                "invariant_valid": True,
                "blocked_until": [
                    "approved_runtime_principal_lifecycle_evidence",
                    "reviewed_identity_public_contract",
                ],
                "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
            },
            report["route_lock"],
        )
        post_evidence = report["post_evidence_p0_lock_simulation"]
        self.assertEqual(
            "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1",
            post_evidence["schema"],
        )
        self.assertTrue(post_evidence["simulation_only"])
        self.assertFalse(post_evidence["approved_runtime_evidence_accepted"])
        self.assertEqual("approved_runtime_evidence_missing", post_evidence["current_route_blocker"])
        self.assertEqual(
            "identity_public_contract_gate_missing",
            post_evidence["simulated_route_blocker_after_accepted_runtime_evidence"],
        )
        self.assertTrue(post_evidence["identity_public_contract_required"])
        self.assertFalse(post_evidence["permissions_admin_unlocked"])
        self.assertFalse(post_evidence["command_response_unlocked"])
        self.assertFalse(post_evidence["commands_replies_unlocked"])
        self.assertFalse(post_evidence["public_sdk_ready"])
        self.assertFalse(post_evidence["runtime_ready"])
        self.assertFalse(post_evidence["counts_toward_complete_sdk_claim"])
        self.assertFalse(post_evidence["counts_toward_p0_dependency_chain_claim"])
        self.assertEqual(0, post_evidence["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, post_evidence["p0_dependency_chain_claim_progress_contribution"])
        check_names = {check["name"] for check in report["checks"]}
        self.assertIn("command_copied_response_intent_lifecycle_planning", check_names)
        self.assertNotIn("player_identity_public_contract_gap", check_names)
        self.assertTrue(ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS.issubset(check_names))
        self.assertEqual([], report["blockers"])
        for check in report["checks"]:
            self.assertTrue(check["valid"], check)
            self.assertEqual([], check["public_or_runtime_claims"], check)
            self.assertEqual(check["expected_schema"], check["report_schema"], check)

    def test_approved_runtime_evidence_routes_to_identity_public_contract_gate_without_unlocking_p0(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime = Path(temp_dir) / "approved-runtime-principal-lifecycle.json"
            approved_runtime.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                query_failclosed_artifact=QUERY_CONTRACT,
                player_identity_decisions=IDENTITY_DECISIONS,
                public_sdk_surfaces=PUBLIC_SDK_SURFACES,
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
                player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
            )
            phase = {
                "current_surface": "obelisk.player_identity.v1",
                "current_blocker": "identity_public_contract_gate_missing",
                "source_checker_primary_blocker": "identity_public_contract_gate_missing",
                "source_checker_next_blocker": None,
                "next_action": "review_identity_public_contract_gate",
                "next_after_runtime_evidence": "identity_public_contract_gate_missing",
                "permissions_admin_unlocked": False,
                "command_response_unlocked": False,
                "commands_replies_unlocked": False,
                "source_checker": "check_player_identity_first_evidence_readiness.py",
                "source_checker_exit_code": 1,
                "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
                "source_checker_parse_error": None,
                "source_checker_status": "blocked",
                "source_checker_ready": False,
                "source_checker_accepted_for_internal_planning": False,
                "source_checker_blockers": ["identity_public_contract_gate_missing"],
                "source_checker_manifest_sources": identity_manifest_sources(),
                "source_checker_approved_runtime_evidence_manifest": approved_runtime_diagnosis(approved_runtime),
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
            }
            original_run_check = ROUTE_GATE.run_check

            def accept_public_contract_gap(name: str, argv: list[str]) -> dict[str, object]:
                result = original_run_check(name, argv)
                if name == "player_identity_public_contract_gap":
                    result["exit_code"] = 0
                    result["valid"] = True
                    result["blockers"] = []
                return result

            with (
                mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=phase),
                mock.patch.object(ROUTE_GATE, "run_check", side_effect=accept_public_contract_gap),
            ):
                report = ROUTE_GATE.build_report(args)
        phase = report["critical_path_phase"]

        self.assertTrue(report["valid"])
        self.assertTrue(report["planning_only"])
        self.assertEqual([], report["blockers"])
        self.assertTrue(report["route_blocked"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertTrue(report["route_lock_invariant_valid"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertEqual(
            ROUTE_GATE.IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS,
            report["identity_public_contract_decision_record_required"],
        )
        self.assertEqual("identity_public_contract_gate_missing", phase["current_blocker"])
        self.assertEqual("identity_public_contract_gate_missing", phase["source_checker_primary_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], phase["source_checker_blockers"])
        for check_name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS:
            child = next(check for check in report["checks"] if check["name"] == check_name)
            self.assertIn("--current-route-blocker", child["argv"])
            self.assertEqual(
                "identity_public_contract_gate_missing",
                child["argv"][child["argv"].index("--current-route-blocker") + 1],
                child,
            )
            self.assertEqual("identity_public_contract_gate_missing", child["current_route_blocker"], child)
            self.assertEqual(["identity_public_contract_gate_missing"], child["remaining_route_blockers"], child)
            self.assertFalse(child["counts_toward_public_sdk"], child)
            self.assertFalse(child["counts_toward_runtime"], child)
            self.assertFalse(child["counts_toward_v1_completion"], child)
            self.assertFalse(child["public_or_runtime_accounting_allowed"], child)
        self.assertFalse(phase["permissions_admin_unlocked"])
        self.assertFalse(phase["command_response_unlocked"])
        self.assertFalse(phase["commands_replies_unlocked"])
        self.assertFalse(phase["promotion_ready"])
        self.assertFalse(phase["public_sdk_ready"])
        self.assertFalse(phase["public_abi_ready"])
        self.assertFalse(phase["runtime_ready"])
        self.assertEqual(
            {
                "locked": True,
                "invariant_valid": True,
                "blocked_until": ["reviewed_identity_public_contract"],
                "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
            },
            report["route_lock"],
        )
        post_evidence = report["post_evidence_p0_lock_simulation"]
        self.assertTrue(post_evidence["simulation_only"])
        self.assertTrue(post_evidence["approved_runtime_evidence_accepted"])
        self.assertEqual("identity_public_contract_gate_missing", post_evidence["current_route_blocker"])
        self.assertEqual(
            ROUTE_GATE.IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS,
            post_evidence["required_identity_public_contract_decision_record"],
        )
        self.assertEqual(
            ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS,
            post_evidence["required_player_identity_promotion_certificate"],
        )
        self.assertNotIn(
            "promotion_status",
            post_evidence["required_player_identity_promotion_certificate"],
        )
        self.assertIn(
            "promotion_status",
            post_evidence["required_player_identity_promotion_certificate"][
                "required_certificate_fields"
            ],
        )
        self.assertEqual(
            [
                "reviewed_identity_public_contract_decision_record",
                "hash_current_source_artifacts",
                "contract_review_only_scope",
                "hash_bound_player_identity_promotion_certificate",
            ],
            post_evidence["cannot_unlock_without"],
        )
        self.assertFalse(post_evidence["identity_public_contract_decision_record_reviewed"])
        self.assertFalse(post_evidence["identity_public_contract_decision_record_hash_current"])
        self.assertFalse(post_evidence["identity_public_contract_decision_record_contract_review_only"])
        self.assertFalse(post_evidence["reviewed_hash_current_contract_review_only"])
        self.assertFalse(post_evidence["player_identity_promotion_certificate_accepted"])
        self.assertFalse(post_evidence["player_identity_promotion_certificate_hash_bound"])
        self.assertFalse(post_evidence["player_identity_promotion_certificate_promoted"])
        self.assertFalse(post_evidence["permissions_admin_unlock_has_hash_bound_player_identity_promotion_certificate"])
        self.assertEqual(
            "identity_public_contract_gate_missing",
            post_evidence["simulated_route_blocker_after_accepted_runtime_evidence"],
        )
        self.assertTrue(post_evidence["identity_public_contract_required"])
        self.assertFalse(post_evidence["permissions_admin_unlocked"])
        self.assertFalse(post_evidence["command_response_unlocked"])
        self.assertFalse(post_evidence["commands_replies_unlocked"])
        self.assertFalse(post_evidence["identity_evidence_only_unblocks_p0"])
        self.assertFalse(post_evidence["identity_evidence_only_unlocks_permissions_admin"])
        self.assertFalse(post_evidence["identity_evidence_only_unlocks_command_response"])
        self.assertFalse(post_evidence["identity_evidence_only_unlocks_commands_replies"])
        self.assertFalse(post_evidence["promotion_ready"])
        self.assertFalse(post_evidence["public_sdk_ready"])
        self.assertFalse(post_evidence["public_abi_ready"])
        self.assertFalse(post_evidence["runtime_ready"])
        self.assertFalse(post_evidence["stable_claim_allowed"])
        self.assertEqual(0, post_evidence["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, post_evidence["p0_dependency_chain_claim_progress_contribution"])
        self.assertEqual(len(ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS), len(post_evidence["p0_child_checks"]))
        for child in post_evidence["p0_child_checks"]:
            requirement = ROUTE_GATE.POST_EVIDENCE_P0_CHILD_GATE_REQUIREMENTS[child["name"]]
            self.assertTrue(child["present"], child)
            self.assertEqual(requirement["surface"], child["surface"], child)
            self.assertEqual(
                requirement["required_before_unlocking"],
                child["required_before_unlocking"],
                child,
            )
            self.assertTrue(child["own_gate_required"], child)
            self.assertFalse(child["accepted_runtime_identity_evidence_only_unlock_allowed"], child)
            self.assertFalse(child["identity_evidence_shortcut_allowed"], child)
            self.assertEqual("identity_public_contract_gate_missing", child["current_route_blocker"], child)
            self.assertEqual(["identity_public_contract_gate_missing"], child["remaining_route_blockers"], child)
            self.assertTrue(child["dependency_chain_locked"], child)
            self.assertFalse(child["counts_toward_public_sdk"], child)
            self.assertFalse(child["counts_toward_runtime"], child)
            self.assertFalse(child["counts_toward_v1_completion"], child)
            self.assertFalse(child["public_or_runtime_accounting_allowed"], child)

    def test_post_evidence_simulation_expanded_aliases_stay_false_and_zero(self) -> None:
        simulation = ROUTE_GATE.build_post_evidence_p0_lock_simulation(
            critical_path_phase=identity_phase(),
            checks=[],
            approved_runtime_evidence_accepted=False,
        )

        for key in ROUTE_GATE.POST_EVIDENCE_P0_LOCK_FALSE_KEYS:
            with self.subTest(key=key):
                self.assertFalse(simulation[key])
        for key in ROUTE_GATE.POST_EVIDENCE_P0_LOCK_ZERO_KEYS:
            with self.subTest(key=key):
                self.assertEqual(0, simulation[key])

        simulation["live_ops_authorized"] = True
        simulation["counts_toward_complete_sdk_claim_now"] = True
        simulation["identity_public_contract_decision_record_reviewed"] = True
        simulation["identity_public_contract_decision_record_hash_current"] = True
        simulation["identity_public_contract_decision_record_contract_review_only"] = True
        simulation["reviewed_hash_current_contract_review_only"] = True
        simulation["player_identity_promotion_certificate_hash_bound"] = True
        simulation["progress"] = "1/12"
        blockers = ROUTE_GATE.validate_post_evidence_p0_lock_simulation(simulation)

        self.assertIn(
            "post_evidence_p0_lock_simulation_live_ops_authorized_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_counts_toward_complete_sdk_claim_now_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_identity_public_contract_decision_record_reviewed_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_identity_public_contract_decision_record_hash_current_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_identity_public_contract_decision_record_contract_review_only_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_reviewed_hash_current_contract_review_only_not_false",
            blockers,
        )
        self.assertIn(
            "post_evidence_p0_lock_simulation_player_identity_promotion_certificate_hash_bound_not_false",
            blockers,
        )
        self.assertIn("post_evidence_p0_lock_simulation_progress_not_zero", blockers)

        simulation = ROUTE_GATE.build_post_evidence_p0_lock_simulation(
            critical_path_phase=identity_phase("identity_public_contract_gate_missing"),
            checks=[],
            approved_runtime_evidence_accepted=True,
        )
        simulation["required_identity_public_contract_decision_record"] = {
            **ROUTE_GATE.IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_REQUIREMENTS,
            "hash_bound_to_current_source_artifacts": False,
        }
        simulation["required_player_identity_promotion_certificate"] = {
            **ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS,
            "missing_mismatched_or_stale_certificate_counts": True,
        }
        simulation["cannot_unlock_without"] = ["reviewed_identity_public_contract_decision_record"]
        blockers = ROUTE_GATE.validate_post_evidence_p0_lock_simulation(simulation)
        self.assertIn("post_evidence_p0_lock_simulation_decision_record_requirements_mismatch", blockers)
        self.assertIn(
            "post_evidence_p0_lock_simulation_identity_promotion_certificate_requirements_mismatch",
            blockers,
        )
        self.assertIn("post_evidence_p0_lock_simulation_cannot_unlock_without_mismatch", blockers)

    def test_post_evidence_simulation_rejects_child_identity_evidence_shortcut(self) -> None:
        checks = [
            {
                "name": name,
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                "dependency_chain_locked": True,
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
            }
            for name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS
        ]
        simulation = ROUTE_GATE.build_post_evidence_p0_lock_simulation(
            critical_path_phase=identity_phase("identity_public_contract_gate_missing"),
            checks=checks,
            approved_runtime_evidence_accepted=True,
        )
        child = next(
            item
            for item in simulation["p0_child_checks"]
            if item["name"] == "permissions_admin_public_readiness"
        )
        child["required_before_unlocking"] = ["accepted_runtime_identity_evidence"]
        child["own_gate_required"] = False
        child["accepted_runtime_identity_evidence_only_unlock_allowed"] = True
        child["identity_evidence_shortcut_allowed"] = True

        blockers = ROUTE_GATE.validate_post_evidence_p0_lock_simulation(simulation)

        self.assertIn(
            "permissions_admin_public_readiness: post-evidence child required gates mismatch",
            blockers,
        )
        self.assertIn(
            "permissions_admin_public_readiness: post-evidence child own gate must stay required",
            blockers,
        )
        self.assertIn(
            (
                "permissions_admin_public_readiness: post-evidence child "
                "accepted_runtime_identity_evidence_only_unlock_allowed must stay false"
            ),
            blockers,
        )
        self.assertIn(
            "permissions_admin_public_readiness: post-evidence child identity_evidence_shortcut_allowed must stay false",
            blockers,
        )

    def test_route_checks_forwards_approved_runtime_evidence_to_identity_gap_report(self) -> None:
        approved_runtime = Path("approved-runtime-principal-lifecycle.json")
        args = SimpleNamespace(
            query_failclosed_artifact=QUERY_CONTRACT,
            player_identity_decisions=IDENTITY_DECISIONS,
            public_sdk_surfaces=PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )

        checks = dict(
            ROUTE_GATE.route_checks(
                args,
                current_route_blocker="identity_public_contract_gate_missing",
                approved_runtime_evidence_accepted=True,
            )
        )
        argv = checks["player_identity_public_contract_gap"]

        self.assertIn("--approved-runtime-evidence", argv)
        self.assertEqual(
            str(approved_runtime),
            argv[argv.index("--approved-runtime-evidence") + 1],
        )

    def test_route_checks_do_not_forward_runtime_manifest_without_accepted_diagnosis(self) -> None:
        approved_runtime = Path("approved-runtime-looking.json")
        args = SimpleNamespace(
            query_failclosed_artifact=QUERY_CONTRACT,
            player_identity_decisions=IDENTITY_DECISIONS,
            public_sdk_surfaces=PUBLIC_SDK_SURFACES,
            player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
            public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
            command_response_root=None,
            command_response_readiness=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=approved_runtime,
        )

        checks = dict(
            ROUTE_GATE.route_checks(
                args,
                current_route_blocker="identity_public_contract_gate_missing",
            )
        )
        argv = checks["player_identity_public_contract_gap"]

        self.assertNotIn("--approved-runtime-evidence", argv)

    def test_approved_runtime_evidence_rejects_stale_runtime_child_route_locks(self) -> None:
        original_run_check = ROUTE_GATE.run_check

        def identity_contract_child_route_lock(name: str, argv: list[str]) -> dict[str, object]:
            result = original_run_check(name, argv)
            if name == "player_identity_public_contract_gap":
                result["exit_code"] = 0
                result["valid"] = True
                result["blockers"] = []
            if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS:
                result["current_route_blocker"] = "approved_runtime_evidence_missing"
                result["remaining_route_blockers"] = ["approved_runtime_evidence_missing"]
            return result

        args = SimpleNamespace(
            query_failclosed_artifact=QUERY_CONTRACT,
            player_identity_decisions=IDENTITY_DECISIONS,
            public_sdk_surfaces=PUBLIC_SDK_SURFACES,
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
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("approved-runtime.json"),
        )
        phase = {
            "current_surface": "obelisk.player_identity.v1",
            "current_blocker": "identity_public_contract_gate_missing",
            "source_checker_primary_blocker": "identity_public_contract_gate_missing",
            "source_checker_next_blocker": None,
            "next_action": "review_identity_public_contract_gate",
            "next_after_runtime_evidence": "identity_public_contract_gate_missing",
            "permissions_admin_unlocked": False,
            "command_response_unlocked": False,
            "commands_replies_unlocked": False,
            "source_checker": "check_player_identity_first_evidence_readiness.py",
            "source_checker_exit_code": 1,
            "source_checker_schema": "obelisk.player-identity-first-evidence-readiness.v1",
            "source_checker_parse_error": None,
            "source_checker_status": "blocked",
            "source_checker_ready": False,
            "source_checker_accepted_for_internal_planning": False,
            "source_checker_blockers": ["identity_public_contract_gate_missing"],
            "source_checker_manifest_sources": identity_manifest_sources(),
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }

        with (
            mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=phase),
            mock.patch.object(ROUTE_GATE, "run_check", side_effect=identity_contract_child_route_lock),
        ):
            report = ROUTE_GATE.build_report(args)

        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertTrue(report["route_blocked"])
        self.assertFalse(report["route_lock_invariant_valid"])
        self.assertIn(
            "permissions_admin_public_readiness: current_route_blocker drifted from downstream lock",
            report["blockers"],
        )
        self.assertIn(
            "command_chat_response_public_readiness: remaining_route_blockers drifted from downstream lock",
            report["blockers"],
        )
        self.assertIn(
            "commands_replies_public_readiness: current_route_blocker drifted from downstream lock",
            report["blockers"],
        )

    def test_accepts_bound_player_identity_planning_sources_as_planning_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence()
            first_evidence_path = root / "players-identity-first-evidence.json"
            lifecycle_path = root / "players-identity-lifecycle-anchor-candidates.json"
            principal_path = root / "players-identity-principal-invalidation-policy.json"
            bound_dir = root / "bound"
            lifecycle = accepted_lifecycle_anchor_manifest()
            source_artifact_ids = [
                f"artifact_sha256:{first_evidence['artifact_identity']['ark_binary_sha256']}",
                "capture_id:player-lifecycle-candidates",
                "evidence_pack_id:player-lifecycle-pack",
            ]
            first_evidence["artifact_identity"]["obelisk_commit"] = "reviewed-commit"
            first_evidence["artifact_identity"]["source_artifact_ids"] = source_artifact_ids
            lifecycle["artifact_identity"]["source_artifact_ids"] = source_artifact_ids
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
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertTrue(report["route_blocked"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertTrue(report["route_lock_invariant_valid"])
        self.assertEqual("lifecycle_anchor_first_evidence_provenance_unbound", report["current_route_blocker"])
        self.assertEqual(
            ["lifecycle_anchor_first_evidence_provenance_unbound"],
            report["remaining_route_blockers"],
        )
        self.assertEqual([], report["blockers"])
        phase = report["critical_path_phase"]
        self.assertEqual("lifecycle_anchor_first_evidence_provenance_unbound", phase["current_blocker"])
        self.assertEqual(
            "lifecycle_anchor_first_evidence_provenance_unbound",
            phase["source_checker_primary_blocker"],
        )
        self.assertEqual("cli_bound", phase["source_checker_manifest_sources"]["mode"])
        self.assertTrue(phase["source_checker_manifest_sources"]["expected_manifests_received"])
        self.assertEqual("bind_lifecycle_anchor_and_principal_policy_sources", phase["next_action"])
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
        self.assertIn("lifecycle_anchor_first_evidence_provenance_unbound", phase["source_checker_blockers"])
        self.assertEqual(
            ["bound_lifecycle_anchor_and_principal_policy_sources", "reviewed_identity_public_contract"],
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

            args = SimpleNamespace(
                query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
                player_identity_decisions=decisions,
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
                player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path(tmp)
                / "approved-runtime-principal-lifecycle.json",
                json=True,
            )
            args.player_identity_approved_runtime_principal_lifecycle_evidence_manifest.write_text(
                json.dumps(approved_runtime_principal_lifecycle_manifest()),
                encoding="utf-8",
            )
            with mock.patch.object(
                ROUTE_GATE,
                "build_critical_path_phase",
                return_value=identity_phase(
                    "identity_public_contract_gate_missing",
                    approved_runtime_path=args.player_identity_approved_runtime_principal_lifecycle_evidence_manifest,
                ),
            ):
                report = ROUTE_GATE.build_report(args)

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
            "source_checker_manifest_sources": identity_manifest_sources(),
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

    def test_route_lock_blocked_until_deduplicates_public_contract_gate(self) -> None:
        self.assertEqual(
            [
                "bound_lifecycle_anchor_and_principal_policy_sources",
                "reviewed_identity_public_contract",
            ],
            ROUTE_GATE.route_lock_blocked_until("lifecycle_anchor_first_evidence_provenance_unbound"),
        )
        self.assertEqual(
            [
                "approved_runtime_principal_lifecycle_evidence",
                "reviewed_identity_public_contract",
            ],
            ROUTE_GATE.route_lock_blocked_until("approved_runtime_evidence_missing"),
        )
        self.assertEqual(
            ["reviewed_identity_public_contract"],
            ROUTE_GATE.route_lock_blocked_until("identity_public_contract_gate_missing"),
        )

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
            "source_checker_manifest_sources": identity_manifest_sources(),
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
            "source_checker_manifest_sources": identity_manifest_sources(),
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
            "source_checker_manifest_sources": identity_manifest_sources(),
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
                        "lifecycle_anchor_candidates_manifest": "/tmp/bound/lifecycle.json",
                        "principal_invalidation_policy_manifest": "/tmp/bound/principal.json",
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
        self.assertEqual("cli_bound", phase["source_checker_manifest_sources"]["mode"])
        self.assertTrue(phase["source_checker_manifest_sources"]["expected_manifests_received"])
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
                        "lifecycle_anchor_candidates_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
                        ),
                        "principal_invalidation_policy_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
                        ),
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
                        "lifecycle_anchor_candidates_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
                        ),
                        "principal_invalidation_policy_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
                        ),
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

    def test_build_critical_path_phase_rejects_placeholder_identity_approval_source_claims(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "primary_blocker": "identity_public_contract_gate_missing",
                        "blockers": ["identity_public_contract_gate_missing"],
                        "lifecycle_anchor_candidates_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
                        ),
                        "principal_invalidation_policy_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
                        ),
                        "status": "blocked",
                        "ready": False,
                        "accepted_for_internal_planning": False,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "first_evidence": {
                            "approved_runtime_principal_lifecycle_evidence_manifest": {
                                "approved_runtime_evidence_source": "request_pack",
                                "runtime_evidence_source": "placeholder_runtime_evidence",
                                "principal_source": "operator_receipt",
                                "identity_claim_source": "window_manifest",
                                "evidence_source": "planning_artifact",
                            }
                        },
                    }
                ),
                stderr="",
            )

        args = SimpleNamespace(
            player_identity_artifact_root=None,
            player_identity_snapshot_root=None,
            player_identity_candidate_root=None,
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("approved-runtime.json"),
        )
        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase(args)
        finally:
            ROUTE_GATE.subprocess.run = original_run

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        claims = phase["source_checker_public_or_runtime_claims"]
        self.assertIn("critical_path_identity_readiness_public_or_runtime_claim", blockers)
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.approved_runtime_evidence_source",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.runtime_evidence_source",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.principal_source",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.identity_claim_source",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.evidence_source",
            claims,
        )

    def test_build_critical_path_phase_rejects_passive_or_diagnostic_identity_evidence_claims(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args[0],
                returncode=1,
                stdout=json.dumps(
                    {
                        "schema": "obelisk.player-identity-first-evidence-readiness.v1",
                        "primary_blocker": "identity_public_contract_gate_missing",
                        "blockers": ["identity_public_contract_gate_missing"],
                        "lifecycle_anchor_candidates_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
                        ),
                        "principal_invalidation_policy_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
                        ),
                        "status": "blocked",
                        "ready": False,
                        "accepted_for_internal_planning": False,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "first_evidence": {
                            "approved_runtime_principal_lifecycle_evidence_manifest": {
                                "identity_claim_source": "diagnostic_observer_triage",
                                "public_identity_evidence_source_schema": (
                                    "obelisk.player-principal-passive-snapshot.v1"
                                ),
                                "notes": [
                                    "diagnostic observer triage is approved runtime evidence",
                                    "passive snapshot does not count as approved runtime evidence",
                                ],
                            }
                        },
                    }
                ),
                stderr="",
            )

        args = SimpleNamespace(
            player_identity_artifact_root=None,
            player_identity_snapshot_root=None,
            player_identity_candidate_root=None,
            player_identity_lifecycle_anchor_candidates_manifest=None,
            player_identity_principal_invalidation_policy_manifest=None,
            player_identity_runtime_principal_lifecycle_evidence_manifest=None,
            player_identity_approved_runtime_principal_lifecycle_evidence_manifest=Path("approved-runtime.json"),
        )
        try:
            ROUTE_GATE.subprocess.run = fake_run
            phase = ROUTE_GATE.build_critical_path_phase(args)
        finally:
            ROUTE_GATE.subprocess.run = original_run

        blockers = ROUTE_GATE.validate_critical_path_phase(phase)
        claims = phase["source_checker_public_or_runtime_claims"]
        self.assertIn("critical_path_identity_readiness_public_or_runtime_claim", blockers)
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.identity_claim_source",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest."
            "public_identity_evidence_source_schema",
            claims,
        )
        self.assertIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.notes[0]:positive_text_claim",
            claims,
        )
        self.assertNotIn(
            "first_evidence.approved_runtime_principal_lifecycle_evidence_manifest.notes[1]:positive_text_claim",
            claims,
        )

    def test_build_critical_path_phase_rejects_identity_readiness_text_overclaims(self) -> None:
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
                        "lifecycle_anchor_candidates_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES
                        ),
                        "principal_invalidation_policy_manifest": str(
                            ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY
                        ),
                        "status": "blocked",
                        "ready": False,
                        "accepted_for_internal_planning": False,
                        "promotion_ready": False,
                        "public_sdk_ready": False,
                        "public_abi_ready": False,
                        "runtime_ready": False,
                        "route_notes": [
                            "accepted runtime evidence ready",
                            "identity public contract reviewed",
                            "v1 support is ready",
                        ],
                        "cannot_unlock_without": [
                            "reviewed public identity contract",
                        ],
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
        claims = phase["source_checker_public_or_runtime_claims"]
        self.assertIn("critical_path_identity_readiness_public_or_runtime_claim", blockers)
        self.assertIn("route_notes[0]:positive_text_claim", claims)
        self.assertIn("route_notes[1]:positive_text_claim", claims)
        self.assertIn("route_notes[2]:positive_text_claim", claims)
        self.assertNotIn("cannot_unlock_without[0]:positive_text_claim", claims)

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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
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

    def test_collect_public_or_runtime_claims_rejects_route_ready_text_variants(self) -> None:
        for text in ("route ready", "route is ready", "route readiness enabled", "public route is ready"):
            with self.subTest(text=text):
                claims = ROUTE_GATE.collect_public_or_runtime_claims({"claim": text})
                self.assertEqual(["claim:positive_text_claim"], claims)

    def test_collect_public_or_runtime_claims_rejects_public_sdk_v1_text_and_keys(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "notes": [
                    "public SDK is ready",
                    "public header is allowed",
                    "v1 completion is ready",
                    "stable claim is ready",
                    "stable SDK is ready",
                    "complete SDK is ready",
                    "full SDK is supported",
                    "production SDK is supported",
                    "SDK is stable",
                    "API is production ready",
                    "planning-only report says stable SDK is ready",
                    "stable SDK remains blocked",
                    "accepted runtime evidence ready",
                    "approved runtime principal lifecycle evidence ready",
                    "identity public contract reviewed",
                    "public contract gate unlocked",
                    "v1 support is ready",
                    "ready for v1 support",
                ],
                "acceptedRuntimeEvidenceReady": True,
                "approved_runtime_principal_lifecycle_evidence_ready": True,
                "identityPublicContractReviewed": "yes",
                "publicContractGateUnlocked": True,
                "stable_claim_allowed": True,
                "v1_completion_ready": True,
                "v1SupportReady": True,
                "v1_sdk_ready": True,
                "sdkReady": True,
                "publicSdkReady": True,
                "publicHeaderReady": "ready",
                "routeReady": True,
                "route_readiness_ready": True,
                "publicRouteReady": True,
                "permissionsAdminRouteReady": True,
                "complete_sdk_ready": True,
                "complete": True,
                "full_api_supported": True,
                "production_support_ready": True,
                "stable_sdk_allowed": "ready",
                "public_api_allowed": "allowed",
                "counts_toward_public_sdk": True,
                "countsTowardRuntime": True,
                "counts_toward_v1_completion": True,
                "public_or_runtime_accounting_allowed": True,
                "countsTowardSdk": True,
                "counts_as_public_sdk": True,
                "counts_toward_complete_sdk_claim": True,
                "route_gate_non_counting_counts_toward_public_sdk": True,
                "route_gate_public_or_runtime_accounting_allowed": True,
                "dependency_chain_unlocked": True,
            }
        )

        self.assertIn("notes[0]:positive_text_claim", claims)
        self.assertIn("notes[1]:positive_text_claim", claims)
        self.assertIn("notes[2]:positive_text_claim", claims)
        self.assertIn("notes[3]:positive_text_claim", claims)
        self.assertIn("notes[4]:positive_text_claim", claims)
        self.assertIn("notes[5]:positive_text_claim", claims)
        self.assertIn("notes[6]:positive_text_claim", claims)
        self.assertIn("notes[7]:positive_text_claim", claims)
        self.assertIn("notes[8]:positive_text_claim", claims)
        self.assertIn("notes[9]:positive_text_claim", claims)
        self.assertIn("notes[10]:positive_text_claim", claims)
        self.assertNotIn("notes[11]:positive_text_claim", claims)
        self.assertIn("notes[12]:positive_text_claim", claims)
        self.assertIn("notes[13]:positive_text_claim", claims)
        self.assertIn("notes[14]:positive_text_claim", claims)
        self.assertIn("notes[15]:positive_text_claim", claims)
        self.assertIn("notes[16]:positive_text_claim", claims)
        self.assertIn("notes[17]:positive_text_claim", claims)
        self.assertIn("acceptedRuntimeEvidenceReady", claims)
        self.assertIn("approved_runtime_principal_lifecycle_evidence_ready", claims)
        self.assertIn("identityPublicContractReviewed", claims)
        self.assertIn("publicContractGateUnlocked", claims)
        self.assertIn("stable_claim_allowed", claims)
        self.assertIn("v1_completion_ready", claims)
        self.assertIn("v1SupportReady", claims)
        self.assertIn("v1_sdk_ready", claims)
        self.assertIn("sdkReady", claims)
        self.assertIn("publicSdkReady", claims)
        self.assertIn("publicHeaderReady", claims)
        self.assertIn("routeReady", claims)
        self.assertIn("route_readiness_ready", claims)
        self.assertIn("publicRouteReady", claims)
        self.assertIn("permissionsAdminRouteReady", claims)
        self.assertIn("complete_sdk_ready", claims)
        self.assertIn("complete", claims)
        self.assertIn("full_api_supported", claims)
        self.assertIn("production_support_ready", claims)
        self.assertIn("stable_sdk_allowed", claims)
        self.assertIn("public_api_allowed", claims)
        self.assertIn("counts_toward_public_sdk", claims)
        self.assertIn("countsTowardRuntime", claims)
        self.assertIn("counts_toward_v1_completion", claims)
        self.assertIn("public_or_runtime_accounting_allowed", claims)
        self.assertIn("countsTowardSdk", claims)
        self.assertIn("counts_as_public_sdk", claims)
        self.assertIn("counts_toward_complete_sdk_claim", claims)
        self.assertIn("route_gate_non_counting_counts_toward_public_sdk", claims)
        self.assertIn("route_gate_public_or_runtime_accounting_allowed", claims)
        self.assertIn("dependency_chain_unlocked", claims)

    def test_collect_public_or_runtime_claims_allows_requirement_and_negative_guardrails_only(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "post_approved_runtime_evidence_gate": {
                    "offline_preparation": {
                        "must_bind_to_approved_runtime_evidence": True,
                        "does_not_unlock_identity_public_contract_gate": True,
                        "does_not_unlock_public_header_gate": True,
                    }
                },
                "post_identity_query_only_diagnostics": {
                    "diagnostic_only": True,
                    "next_gate": {"requires_public_header_review": True},
                },
                "runtime_work_authorized": True,
                "package_shape_ready": True,
                "public_sdk_ready": True,
            }
        )

        self.assertNotIn(
            "post_approved_runtime_evidence_gate.offline_preparation.must_bind_to_approved_runtime_evidence",
            claims,
        )
        self.assertNotIn(
            "post_approved_runtime_evidence_gate.offline_preparation.does_not_unlock_identity_public_contract_gate",
            claims,
        )
        self.assertNotIn("post_identity_query_only_diagnostics.diagnostic_only", claims)
        self.assertNotIn("post_identity_query_only_diagnostics.next_gate.requires_public_header_review", claims)
        self.assertIn("runtime_work_authorized", claims)
        self.assertIn("package_shape_ready", claims)
        self.assertIn("public_sdk_ready", claims)

    def test_next_action_sequence_allows_planning_text_but_rejects_counting_fields(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "next_action_sequence": [
                    {
                        "description": "public SDK is ready after this planning sequence",
                        "runtimeEvidenceReady": True,
                        "countsAsRuntimeEvidence": True,
                        "countsTowardCompleteSdkClaim": True,
                        "completeSdkClaimProgressContribution": 1,
                        "p0DependencyChainClaimProgressContribution": "1/4",
                        "pluginHubReady": True,
                        "pluginHubPublicationAllowed": True,
                        "publicationAuthorized": True,
                    }
                ]
            }
        )

        self.assertNotIn("next_action_sequence[0].description:positive_text_claim", claims)
        for claim in (
            "next_action_sequence[0].runtimeEvidenceReady",
            "next_action_sequence[0].countsAsRuntimeEvidence",
            "next_action_sequence[0].countsTowardCompleteSdkClaim",
            "next_action_sequence[0].completeSdkClaimProgressContribution",
            "next_action_sequence[0].p0DependencyChainClaimProgressContribution",
            "next_action_sequence[0].pluginHubReady",
            "next_action_sequence[0].pluginHubPublicationAllowed",
            "next_action_sequence[0].publicationAuthorized",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_claims_keeps_planning_acceptance_separate_from_artifact_progress(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "accepted_for_planning": True,
                "planning_acceptance": {
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "public_sdk_ready": False,
                    "p0_dependency_chain_claim_progress_contribution": 0,
                },
                "terminal_certificate_metadata": {
                    "status": "issued",
                    "accepted_for_planning": True,
                },
                "package_shape_evidence": {
                    "status": "accepted",
                    "accepted_for_planning": True,
                },
                "response_planning_report": {
                    "status": "accepted",
                    "accepted_for_planning": True,
                },
                "response_status_report": {"status": "ready"},
                "routeClearedForPublicSendChatAbi": True,
                "scopedStatementReady": True,
                "status_report": {"status": "ready"},
                "child_checker_placeholder": {
                    "status": "placeholder",
                    "accepted_for_planning": True,
                },
                "split": [
                    {"field": "terminalCertificateMetadata", "status": "issued"},
                    {"field": "packageShapeEvidence", "status": "accepted"},
                    {"field": "responsePlanningReport", "status": "accepted"},
                    {"field": "route_cleared", "status": "ready"},
                    {"field": "scoped_statement_counts_toward_completion", "value": True},
                    {"field": "childCheckerPlaceholder", "status": "placeholder"},
                ],
            }
        )

        self.assertNotIn("accepted_for_planning", claims)
        self.assertNotIn("planning_acceptance.accepted_for_planning", claims)
        self.assertNotIn("planning_acceptance.public_sdk_ready", claims)
        self.assertNotIn(
            "planning_acceptance.p0_dependency_chain_claim_progress_contribution",
            claims,
        )
        for claim in (
            "terminal_certificate_metadata",
            "terminal_certificate_metadata.status",
            "package_shape_evidence",
            "package_shape_evidence.status",
            "response_planning_report",
            "response_planning_report.status",
            "response_status_report",
            "response_status_report.status",
            "routeClearedForPublicSendChatAbi",
            "scopedStatementReady",
            "status_report",
            "status_report.status",
            "child_checker_placeholder",
            "child_checker_placeholder.status",
            "split[0]",
            "split[1]",
            "split[2]",
            "split[3]",
            "split[4]",
            "split[5]",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_public_or_runtime_claims_rejects_post_evidence_contract_review_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "post_evidence_p0_lock_simulation": {
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
                    "notes": ["identity contract decision record reviewed"],
                }
            }
        )

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
        self.assertIn("post_evidence_p0_lock_simulation.notes[0]:positive_text_claim", claims)

    def test_collect_public_or_runtime_claims_accepts_post_approved_runtime_route_check_diagnostics(
        self,
    ) -> None:
        diagnostic = {
            "post_approved_runtime_evidence_route_check": {
                "runtime_evidence_accepted": True,
                "gap_report_valid": True,
                "invalid_gap_report": False,
                "invalid_gap_report_blockers": [],
                "diagnostic_current_blocker": "identity_public_contract_gate_missing",
                "diagnostic_next_blocker": "identity_public_contract_gate_missing",
                "legitimate_remaining_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blocker_is_legitimate": True,
                "identity_contract_gate_complete": False,
                "blocked_surfaces_must_remain_false": [
                    "public_identity",
                    "lookup",
                    "public_api",
                    "public_abi",
                    "public_header",
                    "runtime_readiness",
                    "sdk_readiness",
                    "permissions_admin",
                    "command_chat",
                    "v1_completion",
                    "p0_progress",
                ],
                "non_claim": (
                    "identity_public_contract_gate_missing remains the only legitimate route "
                    "blocker after accepted runtime evidence; no downstream surface is unlocked"
                ),
            }
        }

        self.assertEqual([], ROUTE_GATE.collect_public_or_runtime_claims(diagnostic))

        overclaim = copy.deepcopy(diagnostic)
        route_check = overclaim["post_approved_runtime_evidence_route_check"]
        route_check["public_sdk_ready"] = True
        route_check["runtime_ready"] = True
        route_check["p0_dependency_chain_claim_progress_contribution"] = "1/4"

        claims = ROUTE_GATE.collect_public_or_runtime_claims(overclaim)

        self.assertIn("post_approved_runtime_evidence_route_check.public_sdk_ready", claims)
        self.assertIn("post_approved_runtime_evidence_route_check.runtime_ready", claims)
        self.assertIn(
            "post_approved_runtime_evidence_route_check.p0_dependency_chain_claim_progress_contribution",
            claims,
        )

    def test_collect_public_or_runtime_claims_rejects_decision_record_metadata_p0_credit(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
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
                "split_metadata": [
                    {
                        "property": "reviewed_hash_current_contract_review_only",
                        "value": "1/4",
                    },
                    {
                        "property": "reviewed_hash_current_contract_review_only",
                        "value": "p0 ready",
                    },
                    {
                        "property": "reviewed_hash_current_contract_review_only",
                        "value": "reviewed",
                    },
                ],
            },
            include_text_claims=False,
        )

        for claim in (
            "identity_public_contract_decision_record.credit",
            "identity_public_contract_decision_record.readiness_credit",
            "identity_public_contract_decision_record.percent",
            "identity_public_contract_decision_record.p0",
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

    def test_collect_public_or_runtime_claims_accepts_blocked_decision_record_metadata_only(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "first_evidence": {
                    "public_contract_gap_report": {
                        "identity_public_contract_decision_record": {
                            "provided": True,
                            "record_valid": True,
                            "reviewed_hash_current_contract_review_only": True,
                            "accepted_for_contract_review": False,
                            "review_inputs_non_counting_until": "runtime.lifecycle_evidence",
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "runtime_ready": False,
                        }
                    }
                }
            },
            include_text_claims=False,
        )
        self.assertEqual([], claims)

        accepted_claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "identity_public_contract_decision_record": {
                    "reviewed_hash_current_contract_review_only": True,
                    "accepted_for_contract_review": True,
                    "review_inputs_non_counting_until": None,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                }
            },
            include_text_claims=False,
        )
        self.assertIn(
            "identity_public_contract_decision_record.reviewed_hash_current_contract_review_only",
            accepted_claims,
        )

    def test_collect_public_or_runtime_claims_rejects_plain_identity_certificate_status_metadata(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "player_identity_promotion_certificate": {
                    "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "status": "promoted",
                    "hash_bound_to_current_source_artifacts": True,
                    "required_by_surface": "obelisk.permissions_admin.v1",
                },
                "player_identity_public_contract_status": {
                    "status": "reviewed",
                    "artifact_status": "reviewed",
                },
            },
            include_text_claims=False,
        )

        self.assertIn("player_identity_promotion_certificate", claims)
        self.assertIn("player_identity_promotion_certificate.promotion_status", claims)
        self.assertIn("player_identity_promotion_certificate.status", claims)
        self.assertIn("player_identity_promotion_certificate.hash_bound_to_current_source_artifacts", claims)
        self.assertIn("player_identity_public_contract_status.status", claims)

    def test_collect_public_or_runtime_claims_allows_hash_bound_identity_promotion_certificate_binding(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binding = hash_bound_player_identity_promotion_certificate_binding(
                Path(temp_dir) / "player-identity-promotion-certificate.json"
            )
            claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"player_identity_promotion_certificate": binding},
                include_text_claims=False,
            )

        self.assertEqual([], claims)

    def test_collect_public_or_runtime_claims_rejects_unbound_identity_promotion_certificate_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binding = hash_bound_player_identity_promotion_certificate_binding(
                Path(temp_dir) / "player-identity-promotion-certificate.json"
            )
            binding["sha256"] = "f" * 64
            claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"player_identity_promotion_certificate": binding},
                include_text_claims=False,
            )

        self.assertIn("player_identity_promotion_certificate", claims)

    def test_collect_public_or_runtime_claims_rejects_post_runtime_shortcut_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "post_runtime_shortcuts": {
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
            }
        )

        for claim in (
            "post_runtime_shortcuts.contract_reviewed",
            "post_runtime_shortcuts.identity_contract_hash_current",
            "post_runtime_shortcuts.header_shape_valid",
            "post_runtime_shortcuts.p0_unlocked",
            "post_runtime_shortcuts.blocker_resolved",
            "post_runtime_shortcuts.public.surface.status",
            "post_runtime_shortcuts.split[0]",
            "post_runtime_shortcuts.split[1]",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_public_or_runtime_claims_rejects_scoped_release_statement_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
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

    def test_collect_public_or_runtime_claims_rejects_final_authz_response_path_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
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

    def test_collect_public_or_runtime_claims_rejects_package_shape_runtime_simulation_aliases(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "acceptedRuntimeSimulationReady": True,
                "accepted_runtime_simulation": {"status": "accepted"},
                "activation_precondition_report": {"status": "ready"},
                "beta_notice_action_report": {"status": "accepted"},
                "bridge_report": {"progress": "1/4", "status": "ready"},
                "compact_context": {"status": "accepted"},
                "copied_log_only": {"status": "ready"},
                "handoff_notes": {"status": "accepted"},
                "notice_action_report": {"status": "accepted"},
                "passive_summary": {"status": "ready"},
                "precondition_artifact": {"progress": "1/3"},
                "pluginHubPlanningReady": True,
                "plugin_hub_planning": {"status": "ready"},
                "side_lane_artifact": {"progress": "1/4", "status": "ready"},
                "support_tier_report": {"status": "supported"},
                "supportTierReadinessReady": True,
                "supportTierPackageReady": True,
                "package_shape_support": {"status": "supported"},
                "support_tier_package_shape": {"status": "supported"},
                "packageShapeAccepted": True,
                "public_contract_record_package": {"status": "accepted"},
                "request_pack_public_contract_record": {"status": "accepted"},
                "commandPlanningReady": True,
                "command_planning_package": {"status": "ready"},
                "command_response_planning_package": {"status": "ready"},
                "copied_intent_package_shape": {"status": "ready"},
                "route_snapshot": {"status": "accepted"},
                "aliases": [
                    {"field": "bridge_report", "status": "ready"},
                    {"field": "compact_context", "status": "accepted"},
                    {"field": "support_tier_report", "status": "supported"},
                    {"field": "activation_precondition_report", "status": "ready"},
                    {"field": "notice_action_report", "status": "accepted"},
                    {"field": "plugin_hub_planning", "status": "supported"},
                    {"field": "support_tier_package_shape", "status": "supported"},
                    {"field": "accepted_runtime_simulation", "status": "accepted"},
                    {"field": "command_planning_package", "status": "ready"},
                    {"field": "route_snapshot", "status": "ready"},
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
                    "package-shape support is ready",
                    "support tier package shape is supported",
                    "accepted runtime simulation is accepted",
                    "package shape unlocks permissions/admin",
                    "command planning is ready",
                    "route snapshot is accepted",
                    "handoff notes are accepted for permissions/admin",
                    "side-lane artifact unlocks route",
                    "support tier package shape remains blocked",
                    "command planning remains blocked",
                ],
            }
        )

        for claim in (
            "acceptedRuntimeSimulationReady",
            "accepted_runtime_simulation.status",
            "activation_precondition_report.status",
            "beta_notice_action_report.status",
            "bridge_report.progress",
            "bridge_report.status",
            "compact_context",
            "compact_context.status",
            "copied_log_only",
            "copied_log_only.status",
            "handoff_notes.status",
            "notice_action_report.status",
            "passive_summary.status",
            "precondition_artifact.progress",
            "pluginHubPlanningReady",
            "plugin_hub_planning",
            "plugin_hub_planning.status",
            "side_lane_artifact.progress",
            "side_lane_artifact.status",
            "support_tier_report.status",
            "supportTierReadinessReady",
            "supportTierPackageReady",
            "package_shape_support.status",
            "support_tier_package_shape.status",
            "packageShapeAccepted",
            "public_contract_record_package.status",
            "request_pack_public_contract_record.status",
            "commandPlanningReady",
            "command_planning_package.status",
            "command_response_planning_package.status",
            "copied_intent_package_shape.status",
            "route_snapshot.status",
            "aliases[0]",
            "aliases[1]",
            "aliases[2]",
            "aliases[3]",
            "aliases[4]",
            "aliases[5]",
            "aliases[6]",
            "aliases[7]",
            "aliases[8]",
            "aliases[9]",
        ):
            self.assertIn(claim, claims)
        for index in range(16):
            self.assertIn(f"notes[{index}]:positive_text_claim", claims)
        self.assertNotIn("notes[16]:positive_text_claim", claims)
        self.assertNotIn("notes[17]:positive_text_claim", claims)

    def test_collect_public_or_runtime_claims_rejects_downstream_route_shortcut_status_aliases(
        self,
    ) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "identity_public_contract_gate_missing": {
                    "source_ready": True,
                    "ready": True,
                    "status": "ready",
                },
                "public_reachability_status": {"source_ready": True, "status": "reachable"},
                "rcon_status": {"source_ready": True, "status": "ready"},
                "admin_snapshot": {"source_ready": True, "status": "ready"},
                "adminStatusSnapshotReady": True,
                "server_list_players": {"source_ready": True, "status": "ready"},
                "serverKickPlayerReady": True,
                "broadcast_status": {"ready": True, "status": "enabled"},
                "package_support_plugin": {
                    "plugin_hub_support_ready": True,
                    "support_tier_ready": True,
                },
                "split_claims": [
                    {"field": "identity_public_contract_gate_missing", "source_ready": True},
                    {"field": "public_reachability", "ready": True},
                    {"field": "rcon_route", "status": "ready"},
                    {"field": "admin_snapshot", "status": "ready"},
                    {"field": "ServerListPlayers", "status": "ready"},
                    {"field": "ServerKickPlayer", "status": "ready"},
                    {"field": "broadcast_status", "status": "enabled"},
                    {"field": "package_shape_support", "source_ready": True},
                    {"field": "plugin_hub_package_shape", "ready": True},
                ],
            }
        )

        for claim in (
            "identity_public_contract_gate_missing",
            "public_reachability_status",
            "public_reachability_status.source_ready",
            "rcon_status",
            "rcon_status.source_ready",
            "admin_snapshot",
            "admin_snapshot.source_ready",
            "adminStatusSnapshotReady",
            "server_list_players",
            "server_list_players.source_ready",
            "serverKickPlayerReady",
            "broadcast_status",
            "package_support_plugin.plugin_hub_support_ready",
            "package_support_plugin.support_tier_ready",
            "split_claims[0]",
            "split_claims[1]",
            "split_claims[2]",
            "split_claims[3]",
            "split_claims[4]",
            "split_claims[5]",
            "split_claims[6]",
            "split_claims[7]",
            "split_claims[8]",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_public_or_runtime_claims_rejects_multi_surface_pack_route_overclaims(self) -> None:
        safe_claims = ROUTE_GATE.collect_public_or_runtime_claims(
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

        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "multi_surface_beta_capture_pack": {
                    "schema": "obelisk.multi-surface-beta-capture-pack.v1",
                    "status": "candidate_capture_pack",
                    "current_blocker": "cleared",
                    "route_ready": True,
                    "sdk_progress": "1/12",
                    "public_readiness": "ready",
                },
                "multi_surface_beta_capture_plan_queue": {
                    "schema": "obelisk.multi-surface-beta-capture-plan-queue.v1",
                    "status": "ready",
                    "queueStatus": "ready",
                    "approved_runtime_evidence_missing": False,
                    "approvedRuntimeEvidenceMissingCleared": True,
                    "clearsApprovedRuntimeEvidenceMissing": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": [],
                    "completeSdkClaimProgressContribution": "1/12",
                    "p0DependencyChainClaimProgressRatio": "1/4",
                    "candidate_surfaces": [
                        {
                            "surface": "permissions_admin",
                            "captureReady": True,
                            "countsTowardSdk": True,
                            "mutationAuthorityReady": True,
                        }
                    ],
                },
                "source_pair": {
                    "source_provenance": "multi_surface_beta_capture_pack",
                    "source_status": "accepted",
                },
                "split_claims": [
                    {"field": "multiSurfaceBetaCapturePlanQueue", "status": "ready"},
                ],
                "notes": [
                    "multi-surface beta capture pack is ready",
                    "multi-surface beta capture plan clears approved_runtime_evidence_missing",
                    "multi-surface beta capture plan remains candidate-only and non-counting",
                ],
            }
        )

        for claim in (
            "multi_surface_beta_capture_pack.current_blocker",
            "multi_surface_beta_capture_pack.public_readiness",
            "multi_surface_beta_capture_pack.route_ready",
            "multi_surface_beta_capture_pack.sdk_progress",
            "multi_surface_beta_capture_plan_queue.status",
            "multi_surface_beta_capture_plan_queue.queueStatus",
            "multi_surface_beta_capture_plan_queue.approved_runtime_evidence_missing",
            "multi_surface_beta_capture_plan_queue.approvedRuntimeEvidenceMissingCleared",
            "multi_surface_beta_capture_plan_queue.clearsApprovedRuntimeEvidenceMissing",
            "multi_surface_beta_capture_plan_queue.current_route_blocker",
            "multi_surface_beta_capture_plan_queue.remaining_route_blockers",
            "multi_surface_beta_capture_plan_queue.completeSdkClaimProgressContribution",
            "multi_surface_beta_capture_plan_queue.p0DependencyChainClaimProgressRatio",
            "multi_surface_beta_capture_plan_queue.candidate_surfaces[0].captureReady",
            "multi_surface_beta_capture_plan_queue.candidate_surfaces[0].countsTowardSdk",
            "multi_surface_beta_capture_plan_queue.candidate_surfaces[0].mutationAuthorityReady",
            "source_pair.source_status",
            "split_claims[0]",
            "notes[0]:positive_text_claim",
            "notes[1]:positive_text_claim",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)
        self.assertNotIn("multi_surface_beta_capture_pack", claims)
        self.assertNotIn("multi_surface_beta_capture_plan_queue", claims)
        self.assertNotIn("notes[2]:positive_text_claim", claims)

    def test_collect_public_or_runtime_claims_handles_public_identity_non_promotional_reasons(self) -> None:
        safe_claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "public_identity_non_promotional_reasons": [
                    "no public identity is promoted",
                    "public identity remains blocked pending reviewed identity-contract evidence",
                    "identity promotion remains blocked until the public contract gate is reviewed",
                    "header, capability, and callback topics remain closed",
                ]
            }
        )
        self.assertEqual([], safe_claims)

        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "public_identity_non_promotional_reasons": [
                    "public identity is ready",
                    "public player identity is promoted",
                    "identity promotion is ready",
                ],
                "publicIdentityReady": True,
                "playerIdentityPromoted": True,
            }
        )

        self.assertIn("public_identity_non_promotional_reasons[0]:positive_text_claim", claims)
        self.assertIn("public_identity_non_promotional_reasons[1]:positive_text_claim", claims)
        self.assertIn("public_identity_non_promotional_reasons[2]:positive_text_claim", claims)
        self.assertIn("publicIdentityReady", claims)
        self.assertIn("playerIdentityPromoted", claims)

    def test_collect_public_or_runtime_claims_accepts_public_header_contract_scan_diagnostics(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "owner_token_sdk_consumer_contract": {
                    "public_header_contract_scan": {
                        "path": "include/obelisk/ObeliskApi.h",
                        "readable": True,
                        "detected_identity_owner_token_symbols": [],
                        "owner_token_registration_symbols": [],
                        "borrowed_runtime_pointer_exposures": [],
                    }
                }
            }
        )

        self.assertEqual([], claims)

    def test_collect_public_or_runtime_claims_accepts_negated_runtime_ready_text(self) -> None:
        for text in ("runtime readiness remains blocked", "runtime ready remains blocked"):
            with self.subTest(text=text):
                claims = ROUTE_GATE.collect_public_or_runtime_claims({"claim": text})
                self.assertEqual([], claims)

    def test_collect_public_or_runtime_claims_accepts_negated_public_sdk_v1_text(self) -> None:
        for text in (
            "public SDK remains blocked",
            "public header is not allowed",
            "v1 completion remains blocked",
            "stable claim is not allowed",
        ):
            with self.subTest(text=text):
                claims = ROUTE_GATE.collect_public_or_runtime_claims({"claim": text})
                self.assertEqual([], claims)

    def test_collect_public_or_runtime_claims_rejects_runtime_identity_source_claims(self) -> None:
        payload = {
            "nested": {
                "principal_source": "approved_runtime_principal_lifecycle_evidence",
                "identity_claim_source": "runtime_lifecycle_evidence",
                "principal-claim-source": {"source": "runtime-local"},
                "commandPrincipalSource": ["approved runtime evidence"],
                "approved_runtime_evidence_source": "operator_receipt",
                "runtime_evidence_source": "request_pack",
                "evidence_source": "live-validation-sidecar",
                "public_identity_source": "reviewed_identity_public_contract",
                "runtime_identity_source": {"source": "lifecycle-anchor-report"},
                "publicIdentitySource": "players_identity_lifecycle_anchor_candidates",
                "authz_principal_source": "players_identity_runtime_principal_lifecycle_evidence",
                "candidate_source": "runtime_lifecycle_evidence",
            }
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(payload)

        self.assertIn("nested.principal_source", claims)
        self.assertIn("nested.identity_claim_source", claims)
        self.assertIn("nested.principal-claim-source", claims)
        self.assertIn("nested.commandPrincipalSource", claims)
        self.assertIn("nested.approved_runtime_evidence_source", claims)
        self.assertIn("nested.runtime_evidence_source", claims)
        self.assertIn("nested.evidence_source", claims)
        self.assertIn("nested.public_identity_source", claims)
        self.assertIn("nested.runtime_identity_source", claims)
        self.assertIn("nested.publicIdentitySource", claims)
        self.assertIn("nested.authz_principal_source", claims)
        self.assertNotIn("nested.candidate_source", claims)

    def test_collect_public_or_runtime_claims_rejects_passive_or_diagnostic_identity_evidence_aliases(
        self,
    ) -> None:
        payload = {
            "nested": {
                "identity_claim_source": "diagnostic_observer_triage",
                "publicIdentityEvidenceSourceSchema": "obelisk.player-principal-passive-snapshot.v1",
                "principal_evidence_source": "passive_snapshot_diff",
                "evidence_classification": "passive_snapshot_non_evidence",
                "diagnostic_only_non_evidence": True,
                "schema": "obelisk.player-principal-passive-snapshot.v1",
                "drift_summary": {
                    "classification": "diagnostic_only_non_evidence",
                    "source_kind": "passive_snapshot",
                },
                "notes": [
                    "diagnostic observer triage is approved runtime evidence",
                    "approved runtime evidence is derived from passive snapshot diff",
                    "passive snapshot does not count as approved runtime evidence",
                ],
            },
            "split": [
                {
                    "field": "public_identity_evidence_source_schema",
                    "value": "obelisk.player-principal-passive-snapshot-diff.v1",
                },
                {"name": "identity_claim_source", "status": "diagnostic_triage"},
            ],
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(payload)

        self.assertIn("nested.identity_claim_source", claims)
        self.assertIn("nested.publicIdentityEvidenceSourceSchema", claims)
        self.assertIn("nested.principal_evidence_source", claims)
        self.assertIn("nested.evidence_classification", claims)
        self.assertIn("nested.diagnostic_only_non_evidence", claims)
        self.assertIn("nested.drift_summary.classification", claims)
        self.assertIn("nested.drift_summary.source_kind", claims)
        self.assertIn("nested.notes[0]:positive_text_claim", claims)
        self.assertIn("nested.notes[1]:positive_text_claim", claims)
        self.assertNotIn("nested.notes[2]:positive_text_claim", claims)
        self.assertNotIn("nested.schema:positive_text_claim", claims)
        self.assertIn("split[0]", claims)
        self.assertIn("split[1]", claims)

    def test_collect_public_or_runtime_claims_rejects_split_key_value_claims(self) -> None:
        payload = {
            "nested": [
                {"key": "publicSdkReady", "value": True},
                {"field": "public_reply_abi_allowed", "state": "ready"},
                {"name": "identity_claim_source", "value": "runtime_lifecycle_evidence"},
                {"claim": "principal-source", "status": "approved_runtime_principal_lifecycle_evidence"},
                {"name": "sdkReady", "status": "ready"},
                {"field": "complete", "value": True},
                {"flag": "routeGateUnlocked", "enabled": "yes"},
                {"key": "publicSdkReady", "value": False},
                {"field": "identity_claim_source", "value": "unit-test-fixture"},
            ]
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(payload)

        self.assertIn("nested[0]", claims)
        self.assertIn("nested[1]", claims)
        self.assertIn("nested[2]", claims)
        self.assertIn("nested[3]", claims)
        self.assertIn("nested[4]", claims)
        self.assertIn("nested[5]", claims)
        self.assertIn("nested[6]", claims)
        self.assertNotIn("nested[7]", claims)
        self.assertNotIn("nested[8]", claims)

    def test_collect_public_or_runtime_claims_rejects_broad_downstream_aliases_and_progress(self) -> None:
        payload = {
            "nested": {
                "permissionsAdminAccepted": True,
                "commandResponsePromoted": {"status": "ready"},
                "commandsRepliesPublicRuntimeReady": "ready",
                "routeAcceptedAsCommandsRepliesReady": True,
                "publicRuntimeReadinessPromoted": True,
                "v1CompletionProgressContribution": "25%",
                "p0DependencyChainProgressContribution": 1,
                "promotedSurfaceCount": 1,
                "promoted_surfaces_count": "1/4",
                "surfacePromotionCount": 1,
                "promotedSurfaceTotal": 1,
                "promoted_surfaces_total": "1/4",
                "surfacePromotionTotal": 1,
                "promotedSurfaceCountZero": "0/4",
                "promotedSurfaceTotalZero": "0/4",
                "progress": "1/4",
                "zeroProgress": "0%",
                "blockedProgress": "blocked",
                "runtimeEvidenceReady": True,
            },
            "split": [
                {"field": "permissionsAdminPromoted", "status": "promoted"},
                {"name": "commandsRepliesAccepted", "value": {"nested": {"state": "ready"}}},
                {"key": "v1CompletionProgress", "value": "10%"},
                {"claim": "publicSdkReady", "result": "accepted"},
                {"field": "promotedSurfacesCount", "outcome": "approved"},
                {"name": "runtimeReady", "claim_value": "validated"},
                {"property": "countsTowardPublicSdk", "verdict": "yes"},
                {"field": "commandResponsePromoted", "status": "blocked"},
                {"field": "commandsRepliesPromoted", "result": "blocked"},
            ],
        }

        claims = ROUTE_GATE.collect_public_or_runtime_claims(payload)

        self.assertIn("nested.permissionsAdminAccepted", claims)
        self.assertIn("nested.commandResponsePromoted", claims)
        self.assertIn("nested.commandsRepliesPublicRuntimeReady", claims)
        self.assertIn("nested.routeAcceptedAsCommandsRepliesReady", claims)
        self.assertIn("nested.publicRuntimeReadinessPromoted", claims)
        self.assertIn("nested.v1CompletionProgressContribution", claims)
        self.assertIn("nested.p0DependencyChainProgressContribution", claims)
        self.assertIn("nested.promotedSurfaceCount", claims)
        self.assertIn("nested.promoted_surfaces_count", claims)
        self.assertIn("nested.surfacePromotionCount", claims)
        self.assertIn("nested.promotedSurfaceTotal", claims)
        self.assertIn("nested.promoted_surfaces_total", claims)
        self.assertIn("nested.surfacePromotionTotal", claims)
        self.assertIn("nested.progress", claims)
        self.assertIn("split[0]", claims)
        self.assertIn("split[1]", claims)
        self.assertIn("split[2]", claims)
        self.assertIn("split[3]", claims)
        self.assertIn("split[4]", claims)
        self.assertIn("split[5]", claims)
        self.assertIn("split[6]", claims)
        self.assertNotIn("nested.promotedSurfaceCountZero", claims)
        self.assertNotIn("nested.promotedSurfaceTotalZero", claims)
        self.assertNotIn("nested.zeroProgress", claims)
        self.assertNotIn("nested.blockedProgress", claims)
        self.assertNotIn("nested.runtimeEvidenceReady", claims)
        self.assertNotIn("split[7]", claims)
        self.assertNotIn("split[8]", claims)

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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
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
                        "dependency_chain_locked": True,
                        "current_route_blocker": "approved_runtime_evidence_missing",
                        "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                        "counts_toward_public_sdk": False,
                        "counts_toward_runtime": False,
                        "counts_toward_v1_completion": False,
                        "public_or_runtime_accounting_allowed": False,
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

    def test_run_check_rejects_child_downstream_unlock_aliases(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[
                    "command_principal_authz_response_bridge"
                ],
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "dependency_chain_locked": True,
                "current_route_blocker": "approved_runtime_evidence_missing",
                "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "commandResponseUnlocked": True,
                "commandResponseReady": True,
                "commandsRepliesUnlocked": True,
                "commandsRepliesReady": True,
                "responsePathReady": True,
                "bridgeClaimsAllowed": True,
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("command_principal_authz_response_bridge", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertIn("commandResponseUnlocked", result["public_or_runtime_claims"])
        self.assertIn("commandResponseReady", result["public_or_runtime_claims"])
        self.assertIn("commandsRepliesUnlocked", result["public_or_runtime_claims"])
        self.assertIn("commandsRepliesReady", result["public_or_runtime_claims"])
        self.assertIn("responsePathReady", result["public_or_runtime_claims"])
        self.assertIn("bridgeClaimsAllowed", result["public_or_runtime_claims"])

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

    def test_run_check_rejects_child_checker_placeholder_even_when_accepted_for_planning(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[
                    "command_principal_authz_response_bridge"
                ],
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "blockers": [],
                "child_checker_placeholder": {
                    "status": "placeholder",
                    "accepted_for_planning": True,
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                },
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("command_principal_authz_response_bridge", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertTrue(result["accepted_for_planning"])
        self.assertIn("child_checker_placeholder", result["public_or_runtime_claims"])
        self.assertIn("child_checker_placeholder.status", result["public_or_runtime_claims"])

    def test_run_check_rejects_required_locked_child_that_counts_while_identity_blocked(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["permissions_admin_public_readiness"],
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "dependency_chain_locked": False,
                "current_route_blocker": "approved_runtime_evidence_missing",
                "remaining_route_blockers": ["approved_runtime_evidence_missing"],
                "counts_toward_public_sdk": True,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "blockers": [],
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("permissions_admin_public_readiness", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertFalse(result["dependency_chain_locked"])
        self.assertTrue(result["counts_toward_public_sdk"])

    def test_run_check_rejects_permissions_admin_plain_identity_certificate_metadata(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            report = {
                "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["permissions_admin_public_readiness"],
                "valid": True,
                "accepted_for_planning": True,
                "planning_only": True,
                "dependency_chain_locked": True,
                "current_route_blocker": "identity_public_contract_gate_missing",
                "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "public_abi_ready": False,
                "runtime_ready": False,
                "blockers": [],
                "player_identity_promotion_certificate": {
                    "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                    "surface_id": "obelisk.player_identity.v1",
                    "promotion_status": "promoted",
                    "status": "promoted",
                    "hash_bound_to_current_source_artifacts": True,
                    "required_by_surface": "obelisk.permissions_admin.v1",
                },
            }
            return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

        try:
            ROUTE_GATE.subprocess.run = fake_run
            result = ROUTE_GATE.run_check("permissions_admin_public_readiness", ["unused.py", "--json"])
        finally:
            ROUTE_GATE.subprocess.run = original_run

        self.assertFalse(result["valid"])
        self.assertIn("player_identity_promotion_certificate", result["public_or_runtime_claims"])
        self.assertIn(
            "player_identity_promotion_certificate.promotion_status",
            result["public_or_runtime_claims"],
        )

    def test_run_check_allows_permissions_admin_hash_bound_identity_certificate_metadata(self) -> None:
        original_run = ROUTE_GATE.subprocess.run

        with tempfile.TemporaryDirectory() as temp_dir:
            binding = hash_bound_player_identity_promotion_certificate_binding(
                Path(temp_dir) / "player-identity-promotion-certificate.json"
            )

            def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
                report = {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS["permissions_admin_public_readiness"],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "dependency_chain_locked": True,
                    "current_route_blocker": "identity_public_contract_gate_missing",
                    "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                    "blockers": [],
                    "player_identity_promotion_certificate": binding,
                }
                return subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(report), stderr="")

            try:
                ROUTE_GATE.subprocess.run = fake_run
                result = ROUTE_GATE.run_check("permissions_admin_public_readiness", ["unused.py", "--json"])
            finally:
                ROUTE_GATE.subprocess.run = original_run

        self.assertTrue(result["valid"])
        self.assertEqual([], result["public_or_runtime_claims"])

    def test_collect_claims_rejects_certificate_builder_report_shortcuts(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "certificate_builder_report": {
                    "schema": "obelisk.player-identity-promotion-certificate-build-report.v1",
                    "status": "built",
                    "identity_surface_certificate_binding_valid": True,
                    "generated_certificate": {
                        "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "surface_id": "obelisk.player_identity.v1",
                        "promotion_status": "promoted",
                        "hash_bound_to_current_source_artifacts": True,
                    },
                    "generated_certificate_reference": {
                        "path": "/tmp/player-identity-promotion-certificate.json",
                        "sha256": "0" * 64,
                    },
                }
            },
            include_text_claims=False,
        )

        self.assertIn(
            "certificate_builder_report.identity_surface_certificate_binding_valid",
            claims,
        )
        self.assertIn("certificate_builder_report.generated_certificate", claims)
        self.assertIn(
            "certificate_builder_report.generated_certificate.promotion_status",
            claims,
        )
        self.assertIn(
            "certificate_builder_report.generated_certificate.hash_bound_to_current_source_artifacts",
            claims,
        )
        self.assertIn("certificate_builder_report.generated_certificate_reference", claims)
        self.assertNotIn("certificate_builder_report.status", claims)

    def test_collect_claims_rejects_post_runtime_bridge_certificate_reference_shortcuts(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "post_runtime_bridge_report": {
                    "player_identity_certificate_reference": {
                        "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                        "promotion_status": "promoted",
                        "status": "promoted",
                    },
                    "post_identity_bridge": "hash_bound_player_identity_promotion_certificate",
                }
            },
            include_text_claims=False,
        )

        self.assertIn("post_runtime_bridge_report.player_identity_certificate_reference", claims)
        self.assertIn(
            "post_runtime_bridge_report.player_identity_certificate_reference.promotion_status",
            claims,
        )
        self.assertIn(
            "post_runtime_bridge_report.player_identity_certificate_reference.status",
            claims,
        )
        self.assertIn("post_runtime_bridge_report.post_identity_bridge", claims)

    def test_collect_claims_rejects_decision_template_header_status_and_copy_shortcuts(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
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
            },
            include_text_claims=False,
        )

        for claim in (
            "identity_public_contract_decision_record_template",
            "identity_public_contract_decision_record_template.review_status",
            "identity_public_contract_decision_record_template.hash_current",
            "identity_public_contract_decision_record_template.decision_scope",
            "identity_public_contract_decision_record_template.permissions_admin.status",
            "identity_claim_source",
            "source_pair.source_status",
            "status_artifact",
            "status_artifact.status",
            "copy_artifact",
            "copy_artifact.status",
            "copied_runtime_status_report",
            "copied_runtime_status_report.status",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_claims_allows_canonical_hash_bound_identity_certificate_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binding = hash_bound_player_identity_promotion_certificate_binding(
                Path(temp_dir) / "player-identity-promotion-certificate.json"
            )

            claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"player_identity_promotion_certificate": binding},
                include_text_claims=False,
            )

        self.assertEqual([], claims)

    def test_collect_claims_rejects_minimal_identity_certificate_without_review_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            certificate_path = Path(temp_dir) / "player-identity-promotion-certificate.json"
            reviewed_surface_hash = "1" * 64
            certificate = {
                "schema": ROUTE_GATE.PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                "surface_id": "obelisk.player_identity.v1",
                "promotion_status": "promoted",
                "v1_dependency_chain": ROUTE_GATE.CANONICAL_V1_DEPENDENCY_SEQUENCE,
                "v1_dependency_chain_position": 1,
                "required_by_surface": "obelisk.permissions_admin.v1",
                "required_by_v1_dependency_chain_position": 2,
                "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
                "reviewed_artifact_hash_policy": (
                    "must match the reviewed identity surface record hash carried by the certificate"
                ),
                "missing_mismatched_or_stale_certificate_counts": False,
                "evidence": {
                    "reviewed_artifact_hash": reviewed_surface_hash,
                    "reviewed_surface_record_sha256": reviewed_surface_hash,
                },
            }
            certificate_path.write_text(json.dumps(certificate, sort_keys=True), encoding="utf-8")
            binding = {
                "path": str(certificate_path),
                "sha256": hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
            }

            claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"player_identity_promotion_certificate": binding},
                include_text_claims=False,
            )

        self.assertIn("player_identity_promotion_certificate", claims)

    def test_collect_claims_rejects_generated_or_stale_identity_certificate_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            certificate_path = Path(temp_dir) / "player-identity-promotion-certificate.json"
            binding = hash_bound_player_identity_promotion_certificate_binding(certificate_path)

            generated_claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"generated_certificate": binding},
                include_text_claims=False,
            )
            self.assertIn("generated_certificate", generated_claims)

            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["current_reviewed_surface_record_sha256"] = "2" * 64
            certificate_path.write_text(json.dumps(certificate, sort_keys=True), encoding="utf-8")
            stale_binding = {
                "path": str(certificate_path),
                "sha256": hashlib.sha256(certificate_path.read_bytes()).hexdigest(),
            }
            stale_claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {"player_identity_promotion_certificate": stale_binding},
                include_text_claims=False,
            )

        self.assertIn("player_identity_promotion_certificate", stale_claims)

    def test_collect_claims_rejects_downstream_promotion_certificate_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            binding = hash_bound_player_identity_promotion_certificate_binding(
                Path(temp_dir) / "player-identity-promotion-certificate.json"
            )
            claims = ROUTE_GATE.collect_public_or_runtime_claims(
                {
                    "child_report": {
                        "hash_bound_player_identity_promotion_certificate": binding,
                        "hash_bound_permissions_admin_promotion_certificate": binding,
                        "hash_bound_command_chat_response_path_promotion_certificate": binding,
                        "permissions_admin_promotion_certificate": binding,
                        "command_response_promotion_certificate": "promoted",
                        "promotion_certificate_ready": True,
                        "p0_dependency_chain_claim_progress_contribution": 1,
                        "source_kind": "hash_bound_permissions_admin_promotion_certificate",
                        "split": [
                            {
                                "field": "command_response_promotion_certificate",
                                "status": "promoted",
                            },
                            {
                                "name": "hash_bound_command_chat_response_path_promotion_certificate",
                                "value": binding,
                            },
                        ],
                    }
                },
                include_text_claims=False,
            )

        self.assertNotIn(
            "child_report.hash_bound_player_identity_promotion_certificate",
            claims,
        )
        for claim in (
            "child_report.hash_bound_permissions_admin_promotion_certificate",
            "child_report.hash_bound_command_chat_response_path_promotion_certificate",
            "child_report.permissions_admin_promotion_certificate",
            "child_report.command_response_promotion_certificate",
            "child_report.promotion_certificate_ready",
            "child_report.p0_dependency_chain_claim_progress_contribution",
            "child_report.source_kind",
            "child_report.split[0]",
            "child_report.split[1]",
        ):
            with self.subTest(claim=claim):
                self.assertIn(claim, claims)

    def test_collect_claims_allows_blocked_downstream_promotion_certificate_metadata(self) -> None:
        claims = ROUTE_GATE.collect_public_or_runtime_claims(
            {
                "post_evidence_p0_lock_simulation": {
                    "hash_bound_permissions_admin_promotion_certificate": False,
                    "hash_bound_command_chat_response_path_promotion_certificate": False,
                    "permissions_admin_promotion_certificate": False,
                    "command_response_promotion_certificate": "blocked",
                    "promotion_certificate_ready": False,
                    "p0_dependency_chain_claim_progress_contribution": 0,
                    "required_before_unlocking": [
                        "hash_bound_player_identity_promotion_certificate",
                        "permissions_admin_promotion_certificate",
                        "command_chat_response_path_promotion_certificate",
                    ],
                    "requires_hash_bound_permissions_admin_promotion_certificate": True,
                    "does_not_accept_downstream_promotion_certificate_aliases": True,
                    "blockers": [
                        "identity_public_contract_gate_missing",
                        "permissions_admin_promotion_certificate_missing",
                    ],
                    "non_claim": (
                        "downstream promotion certificates remain blocked until the canonical "
                        "upstream identity gate is satisfied"
                    ),
                }
            },
            include_text_claims=True,
        )

        self.assertEqual([], claims)

    def test_route_gate_rejects_child_source_kind_promotion_certificate_shortcut_despite_blockers(
        self,
    ) -> None:
        original = ROUTE_GATE.run_check
        with tempfile.TemporaryDirectory() as temp_dir:
            approved_runtime_path = Path(temp_dir) / "approved-runtime.json"

            def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
                payload: dict[str, object] = {
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
                if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS:
                    payload.update(
                        {
                            "dependency_chain_locked": True,
                            "current_route_blocker": "identity_public_contract_gate_missing",
                            "remaining_route_blockers": ["identity_public_contract_gate_missing"],
                            "counts_toward_public_sdk": False,
                            "counts_toward_runtime": False,
                            "counts_toward_v1_completion": False,
                            "public_or_runtime_accounting_allowed": False,
                        }
                    )
                if name == "permissions_admin_public_readiness":
                    payload.update(
                        {
                            "valid": False,
                            "source_kind": "hash_bound_permissions_admin_promotion_certificate",
                            "hash_bound_permissions_admin_promotion_certificate": False,
                            "promotion_certificate_ready": False,
                            "p0_dependency_chain_claim_progress_contribution": 0,
                            "blockers": sorted(
                                ROUTE_GATE.POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_BLOCKERS
                            ),
                        }
                    )
                claims = ROUTE_GATE.collect_public_or_runtime_claims(payload)
                blockers = payload.get("blockers", [])
                return {
                    "name": name,
                    "argv": argv,
                    "exit_code": 1 if name == "permissions_admin_public_readiness" else 0,
                    "valid": not claims and payload.get("valid") is True and blockers == [],
                    "report_schema": payload["schema"],
                    "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "planning_only": payload.get("planning_only"),
                    "accepted_for_planning": payload.get("accepted_for_planning"),
                    "dependency_chain_locked": payload.get("dependency_chain_locked"),
                    "current_route_blocker": payload.get("current_route_blocker"),
                    "remaining_route_blockers": payload.get("remaining_route_blockers"),
                    "counts_toward_public_sdk": payload.get("counts_toward_public_sdk"),
                    "counts_toward_runtime": payload.get("counts_toward_runtime"),
                    "counts_toward_v1_completion": payload.get("counts_toward_v1_completion"),
                    "public_or_runtime_accounting_allowed": payload.get(
                        "public_or_runtime_accounting_allowed"
                    ),
                    "public_or_runtime_claims": claims,
                    "blockers": blockers,
                    "parse_error": None,
                    "stderr": "",
                    "report_payload": payload,
                }

            args = SimpleNamespace(
                query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
                player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
                public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
                player_identity_private_candidate_contract=(
                    ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE
                ),
                public_header=ROUTE_GATE.DEFAULT_PUBLIC_HEADER,
                command_response_root=None,
                command_response_readiness=None,
                player_identity_artifact_root=None,
                player_identity_snapshot_root=None,
                player_identity_candidate_root=None,
                player_identity_lifecycle_anchor_candidates_manifest=None,
                player_identity_principal_invalidation_policy_manifest=None,
                player_identity_runtime_principal_lifecycle_evidence_manifest=None,
                player_identity_approved_runtime_principal_lifecycle_evidence_manifest=(
                    approved_runtime_path
                ),
                json=True,
            )
            try:
                ROUTE_GATE.run_check = fake_run_check
                with mock.patch.object(
                    ROUTE_GATE,
                    "build_critical_path_phase",
                    return_value=identity_phase(
                        "identity_public_contract_gate_missing",
                        approved_runtime_path=approved_runtime_path,
                    ),
                ):
                    report = ROUTE_GATE.build_report(args)
            finally:
                ROUTE_GATE.run_check = original

        child = next(
            check
            for check in report["checks"]
            if check["name"] == "permissions_admin_public_readiness"
        )
        self.assertFalse(report["valid"])
        self.assertFalse(child["post_runtime_identity_contract_lock_quarantined"])
        self.assertIn("source_kind", child["public_or_runtime_claims"])
        self.assertIn(
            "permissions_admin_public_readiness: child blockers not empty",
            report["blockers"],
        )
        self.assertTrue(
            any(
                blocker.startswith(
                    "permissions_admin_public_readiness: unexpected public/runtime claim: "
                )
                and "source_kind" in blocker
                for blocker in report["blockers"]
            ),
            report["blockers"],
        )

    def test_route_gate_composes_response_path_report_into_commands_replies(self) -> None:
        original = ROUTE_GATE.run_check
        seen_response_path_report = False
        with tempfile.TemporaryDirectory() as temp_dir:
            response_root = Path(temp_dir) / "response-root"
            response_root.mkdir()
            source_paths = {
                "readiness_path": response_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME,
                "decisions_path": response_root / "command_chat_response_public_contract_decisions.json",
                "surfaces_path": response_root / "public_sdk_surfaces.json",
                "public_header_path": response_root / "ObeliskApi.h",
            }
            for key, path in source_paths.items():
                path.write_text(f"{key}\n", encoding="utf-8")
            source_hashes = {
                key: hashlib.sha256(path.read_bytes()).hexdigest()
                for key, path in source_paths.items()
            }

            def base_result(name: str, argv: list[str]) -> dict[str, object]:
                report_payload: dict[str, object] = {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "dependency_chain_locked": name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS,
                    "current_route_blocker": (
                        "approved_runtime_evidence_missing"
                        if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS
                        else None
                    ),
                    "remaining_route_blockers": (
                        ["approved_runtime_evidence_missing"]
                        if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS
                        else None
                    ),
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                    "public_header_allowed": False,
                    "blockers": [],
                }
                return {
                    "name": name,
                    "argv": argv,
                    "exit_code": 0,
                    "valid": True,
                    "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "planning_only": True,
                    "accepted_for_planning": True,
                    "dependency_chain_locked": report_payload["dependency_chain_locked"],
                    "current_route_blocker": report_payload["current_route_blocker"],
                    "remaining_route_blockers": report_payload["remaining_route_blockers"],
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                    "public_or_runtime_claims": [],
                    "blockers": [],
                    "parse_error": None,
                    "stderr": "",
                    "report_payload": report_payload,
                }

            def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
                nonlocal seen_response_path_report
                result = base_result(name, argv)
                if name == "command_chat_response_public_readiness":
                    payload = result["report_payload"]
                    assert isinstance(payload, dict)
                    payload.update(
                        {
                            "surface": "obelisk.command_chat_response_path.v1",
                            "readiness_root": str(response_root),
                            "readiness_path": str(source_paths["readiness_path"]),
                            "decisions_path": str(source_paths["decisions_path"]),
                            "surfaces_path": str(source_paths["surfaces_path"]),
                            "public_header_path": str(source_paths["public_header_path"]),
                            "source_artifact_hashes": source_hashes,
                            "target_set": "command-chat-response-intake",
                            "target_filters": [
                                "ShooterPlayerController.ServerSendChatMessage",
                                "ShooterPlayerController.ServerChatMessage_Impl",
                            ],
                            "readiness_status": "compared",
                            "decisions_status": "blocked",
                            "surfaces_status": "planning",
                            "public_readiness_ready": False,
                            "public_header_allowed": False,
                            "promotion_ready": False,
                            "public_sdk_ready": False,
                            "public_abi_ready": False,
                            "runtime_ready": False,
                        }
                    )
                if name == "commands_replies_public_readiness":
                    self.assertIn("--response-path-report", argv)
                    self.assertIn("--response-path-report-root", argv)
                    self.assertIn("--response-path-root", argv)
                    self.assertIn("--response-path-readiness", argv)
                    report_path = Path(argv[argv.index("--response-path-report") + 1])
                    report_root = Path(argv[argv.index("--response-path-report-root") + 1])
                    self.assertEqual(
                        report_root / ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_REPORT_NAME,
                        report_path,
                    )
                    composed = json.loads(report_path.read_text(encoding="utf-8"))
                    self.assertEqual(source_hashes, composed["source_artifact_hashes"])
                    seen_response_path_report = True
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
                with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
                    report = ROUTE_GATE.build_report(args)
            finally:
                ROUTE_GATE.run_check = original

        self.assertTrue(seen_response_path_report)
        self.assertTrue(report["valid"], report["blockers"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual([], report["blockers"])

    def test_route_gate_does_not_synthesize_response_path_report_from_summary(self) -> None:
        original = ROUTE_GATE.run_check
        commands_replies_received_report = False

        def base_result(name: str, argv: list[str]) -> dict[str, object]:
            locked = name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS
            return {
                "name": name,
                "argv": argv,
                "exit_code": 0,
                "valid": True,
                "report_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "expected_schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                "planning_only": True,
                "accepted_for_planning": True,
                "dependency_chain_locked": locked,
                "current_route_blocker": "approved_runtime_evidence_missing" if locked else None,
                "remaining_route_blockers": ["approved_runtime_evidence_missing"] if locked else None,
                "counts_toward_public_sdk": False,
                "counts_toward_runtime": False,
                "counts_toward_v1_completion": False,
                "public_or_runtime_accounting_allowed": False,
                "public_or_runtime_claims": [],
                "blockers": [],
                "parse_error": None,
                "stderr": "",
                "report_payload": {
                    "schema": ROUTE_GATE.EXPECTED_ROUTE_CHECK_SCHEMAS[name],
                    "valid": True,
                    "accepted_for_planning": True,
                    "planning_only": True,
                    "dependency_chain_locked": locked,
                    "current_route_blocker": "approved_runtime_evidence_missing" if locked else None,
                    "remaining_route_blockers": ["approved_runtime_evidence_missing"] if locked else None,
                    "counts_toward_public_sdk": False,
                    "counts_toward_runtime": False,
                    "counts_toward_v1_completion": False,
                    "public_or_runtime_accounting_allowed": False,
                    "promotion_ready": False,
                    "public_sdk_ready": False,
                    "public_abi_ready": False,
                    "runtime_ready": False,
                    "blockers": [],
                },
            }

        def fake_run_check(name: str, argv: list[str]) -> dict[str, object]:
            nonlocal commands_replies_received_report
            result = base_result(name, argv)
            if name == "command_chat_response_public_readiness":
                payload = result["report_payload"]
                assert isinstance(payload, dict)
                payload.update(
                    {
                        "readiness_root": "/tmp/command-response-summary",
                        "readiness_path": (
                            f"/tmp/command-response-summary/"
                            f"{ROUTE_GATE.COMMAND_RESPONSE_DEFAULT_READINESS_NAME}"
                        ),
                        "public_readiness_ready": False,
                        "public_header_allowed": False,
                    }
                )
            if name == "commands_replies_public_readiness":
                commands_replies_received_report = "--response-path-report" in argv
                result["exit_code"] = 1
                result["valid"] = False
                result["blockers"] = ["response_path_report_required"]
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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
                report = ROUTE_GATE.build_report(args)
        finally:
            ROUTE_GATE.run_check = original

        self.assertFalse(commands_replies_received_report)
        self.assertFalse(report["valid"])
        self.assertIn(
            "command_chat_response_public_readiness: source-artifact paths required before commands/replies handoff",
            report["blockers"],
        )
        self.assertIn(
            "command_chat_response_public_readiness: source-artifact hashes required before commands/replies handoff",
            report["blockers"],
        )
        self.assertIn(
            "commands_replies_public_readiness: missing composed response path report",
            report["blockers"],
        )
        self.assertIn("commands_replies_public_readiness: checker exited 1", report["blockers"])

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
                with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
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

        by_name = {
            name: argv
            for name, argv in ROUTE_GATE.route_checks(
                args,
                current_route_blocker="identity_public_contract_gate_missing",
            )
        }
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
                if name in ROUTE_GATE.REQUIRED_LOCKED_CHILD_CHECKS:
                    self.assertIn("--current-route-blocker", by_name[name])
                    self.assertEqual(
                        "identity_public_contract_gate_missing",
                        by_name[name][by_name[name].index("--current-route-blocker") + 1],
                    )

    def test_route_gate_rejects_fake_public_header_in_downstream_p0_checks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            header_path = Path(temp_dir) / "ObeliskApi.h"
            header_path.write_text("/* fake clean header */\n", encoding="utf-8")
            args = SimpleNamespace(
                query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
                player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
                public_sdk_surfaces=ROUTE_GATE.DEFAULT_PUBLIC_SDK_SURFACES,
                player_identity_private_candidate_contract=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
                public_header=header_path,
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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
                report = ROUTE_GATE.build_report(args)

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
            args = SimpleNamespace(
                query_failclosed_artifact=ROUTE_GATE.DEFAULT_QUERY_CONTRACT,
                player_identity_decisions=ROUTE_GATE.DEFAULT_PLAYER_IDENTITY_DECISIONS,
                public_sdk_surfaces=surfaces_path,
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
            with mock.patch.object(ROUTE_GATE, "build_critical_path_phase", return_value=identity_phase()):
                report = ROUTE_GATE.build_report(args)

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
                    "serverOperationsAuthorized": True,
                    "routeReady": True,
                    "route_readiness_ready": True,
                    "publicRouteReady": True,
                    "permissionsAdminRouteReady": True,
                    "runtime_work_authorized": True,
                    "runtimeApprovalGranted": True,
                    "operator_approval_granted": True,
                    "permissions-admin-ready": True,
                    "publicBridgeAbiAllowed": True,
                    "public response abi allowed": True,
                    "authorityClaimSource": "command text",
                    "principal-source": {"source": "operator-config"},
                    "identity_claim_source": "approved_runtime_principal_lifecycle_evidence",
                    "principalClaimSource": "runtime lifecycle evidence",
                    "public-reply-api": True,
                    "publicSendChatApi": True,
                    "permissions_admin_ready": True,
                    "notes": [
                        "public ABI is ready",
                        "route readiness is ready",
                        "public route is ready",
                        "send-chat ABI is public and ready",
                        "command routing is public and ready",
                        "permissions/admin is public and ready",
                        "replies API is public and ready",
                        "command response path is live",
                        "reply endpoint is live",
                        "send chat API is operational",
                        "stable SDK is ready",
                        "complete SDK is ready",
                        "production SDK is supported",
                        "runtime work is authorized",
                        "server operations are authorized",
                        "operator approval is granted",
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
        self.assertIn("nested.serverOperationsAuthorized", result["public_or_runtime_claims"])
        self.assertIn("nested.routeReady", result["public_or_runtime_claims"])
        self.assertIn("nested.route_readiness_ready", result["public_or_runtime_claims"])
        self.assertIn("nested.publicRouteReady", result["public_or_runtime_claims"])
        self.assertIn("nested.permissionsAdminRouteReady", result["public_or_runtime_claims"])
        self.assertIn("nested.runtime_work_authorized", result["public_or_runtime_claims"])
        self.assertIn("nested.runtimeApprovalGranted", result["public_or_runtime_claims"])
        self.assertIn("nested.operator_approval_granted", result["public_or_runtime_claims"])
        self.assertIn("nested.permissions-admin-ready", result["public_or_runtime_claims"])
        self.assertIn("nested.publicBridgeAbiAllowed", result["public_or_runtime_claims"])
        self.assertIn("nested.public response abi allowed", result["public_or_runtime_claims"])
        self.assertIn("nested.authorityClaimSource", result["public_or_runtime_claims"])
        self.assertIn("nested.principal-source", result["public_or_runtime_claims"])
        self.assertIn("nested.identity_claim_source", result["public_or_runtime_claims"])
        self.assertIn("nested.principalClaimSource", result["public_or_runtime_claims"])
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
        self.assertIn("nested.notes[8]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[9]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[10]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[11]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[12]:positive_text_claim", result["public_or_runtime_claims"])
        self.assertIn("nested.notes[13]:positive_text_claim", result["public_or_runtime_claims"])


if __name__ == "__main__":
    unittest.main()
