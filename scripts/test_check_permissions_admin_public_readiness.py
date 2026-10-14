#!/usr/bin/env python3
"""Tests for check_permissions_admin_public_readiness.py."""

from __future__ import annotations

import contextlib
import argparse
import hashlib
import json
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_permissions_admin_public_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
AUTHZ_DECISION_MODEL = REPO_ROOT / "core" / "AuthzDecisionModel.h"
QUERY_CHECKER = SCRIPT_DIR / "check_permissions_admin_query_failclosed_contract.py"
CANONICAL_QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT = REPO_ROOT / "tests" / "core"
PERMISSIONS_ADMIN_IDENTITY_TEMP_PREFIX = "PermissionsAdminIdentity"

sys.path.insert(0, str(SCRIPT_DIR))
SPEC = importlib.util.spec_from_file_location("check_permissions_admin_public_readiness", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
READINESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = READINESS
SPEC.loader.exec_module(READINESS)


def run_checker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"checker failed with {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def write_json(root: Path, name: str, payload: dict) -> Path:
    path = root / name
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def bind_json_artifact(path: Path) -> dict[str, str]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def beta_capture_false_flags() -> dict[str, bool | int]:
    flags: dict[str, bool | int] = {key: False for key in READINESS.BETA_CAPTURE_FALSE_KEYS}
    flags.update({key: 0 for key in READINESS.BETA_CAPTURE_ZERO_KEYS})
    return flags


def beta_capture_candidate(surface_id: str) -> dict:
    candidate = {
        "id": surface_id,
        "target": READINESS.BETA_CAPTURE_SURFACE_TARGETS[surface_id],
        "artifact_status": "candidate_only",
        "candidate_only": True,
        "debug_only": True,
        "requires_own_checker_acceptance": True,
        "requires_player_principal_triplet": True,
    }
    candidate.update(beta_capture_false_flags())
    return candidate


def beta_capture_manifest() -> dict:
    manifest = {
        "schema": READINESS.BETA_CAPTURE_CANDIDATES_SCHEMA,
        "artifact_kind": "beta_capture_candidate",
        "artifact_status": "candidate_only",
        "candidate_only": True,
        "debug_only": True,
        "requires_own_checker_acceptance": True,
        "requires_player_principal_triplet": True,
        "non_claim": READINESS.BETA_CAPTURE_NON_CLAIM,
        "candidate_debug_surfaces": [
            beta_capture_candidate(surface_id)
            for surface_id in READINESS.BETA_CAPTURE_REQUIRED_SURFACES
        ],
    }
    manifest.update(beta_capture_false_flags())
    return manifest


def accepted_runtime_evidence_record() -> dict:
    binding = dict(READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES)
    binding.update({key: False for key in READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS})
    binding["non_claim"] = (
        "approved runtime evidence is a contract-review input only and cannot unlock "
        "public header, API, ABI, SDK, runtime, stable, Plugin Hub, publication, or P0 claims"
    )
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "result": "approved runtime principal lifecycle evidence",
        "next_blocker": "identity_public_contract_gate_missing",
        "approved_runtime_evidence_binding_required": True,
        "approved_runtime_evidence_binding": binding,
    }


def minimal_accepted_runtime_evidence_record() -> dict:
    return {
        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
        "result": "approved runtime principal lifecycle evidence",
        "next_blocker": "identity_public_contract_gate_missing",
    }


def reviewed_identity_artifact_hash(identity_surface: dict | None) -> str:
    source = identity_surface if identity_surface is not None else {"surface": "obelisk.player_identity.v1"}
    data = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def write_identity_promotion_certificate(
    root: Path,
    identity_surface: dict | None = None,
    *,
    reviewed_artifact_hash: str | None = None,
) -> dict[str, str]:
    path = root / "player-identity-promotion-certificate.json"
    evidence = {
        "reviewed_artifact_hash": reviewed_artifact_hash
        if reviewed_artifact_hash is not None
        else reviewed_identity_artifact_hash(identity_surface)
    }
    if identity_surface is not None:
        identity_evidence = identity_surface.get("evidence", {})
        accepted_runtime = identity_evidence.get("accepted_runtime_evidence", {})
        evidence["reviewed_surface_record_sha256"] = READINESS.player_identity_surface_record_sha256(
            identity_surface
        )
        evidence["promotion_evidence_kind"] = "player_identity_promotion_certificate"
        evidence["review_artifact_only"] = False
        evidence["contract_review_only"] = False
        evidence["passive_evidence_only"] = False
        evidence["diagnostic_only"] = False
        evidence["candidate_only"] = False
        evidence["readiness_report_only"] = False
        evidence["approved_runtime_evidence_only"] = False
        evidence["approved_runtime_evidence"] = {
            "schema": accepted_runtime.get("schema"),
            "result": accepted_runtime.get("result"),
            "next_blocker": accepted_runtime.get("next_blocker"),
        }
        evidence["public_contract"] = list(identity_surface.get("public_contract", []))
        evidence["capabilities"] = list(identity_surface.get("capabilities", []))
        evidence["public_fields"] = list(identity_surface.get("public_fields", []))
        evidence["abi_contract"] = list(identity_surface.get("abi_contract", []))
        evidence["lifecycle_contract"] = list(identity_surface.get("lifecycle_contract", []))
        evidence["sdk_consumer_tests"] = list(identity_evidence.get("sdk_consumer_tests", []))
        evidence["semantic_proofs"] = [
            "approved_runtime_principal_lifecycle_evidence",
            "copied_principal_handle_generation_scope_flags",
            "principal_invalidation_semantics",
            "owner_token_lifecycle_cleanup",
            "reviewed_identity_public_contract_decision_record",
            "public_contract_capability_abi_lifecycle",
            "sdk_consumer_coverage",
        ]
        evidence["identity_public_contract_decision_record"] = {
            "schema": "obelisk.player-identity-public-contract-decision-record.v1",
            "artifact_id": "reviewed_identity_public_contract_decision_record",
            "surface": "obelisk.player_identity.v1",
            "active_after_resolved_input": "runtime.lifecycle_evidence",
            "review_status": "reviewed",
            "accepted_for_contract_review": True,
            "next_blocker": "public_header_gate_missing",
            "reviewed_surface_record_sha256": evidence["reviewed_surface_record_sha256"],
            "complete_identity_public_contract_reviewed": True,
            "partial_identity_contract": False,
            "hash_current_identity_public_contract_decision_record": True,
            "permissions_admin_unlock_allowed": False,
            "permissions_admin_counting_allowed": False,
            "sdk_or_p0_counting_allowed": False,
            "resolved_decision_keys": [
                "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
                "identity_public_contract.reviewed_owner_token_lifecycle",
                "identity_public_contract.reviewed_process_local_non_persistent_handles",
                "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
            ],
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
        }
        evidence["identity_public_contract_decision_record_sha256"] = READINESS.canonical_json_sha256(
            evidence["identity_public_contract_decision_record"]
        )
    payload = {
        "schema": "obelisk.player-identity-promotion-certificate.v1",
        "surface_id": "obelisk.player_identity.v1",
        "promotion_status": "promoted",
        "v1_dependency_chain": [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ],
        "chain_position": 1,
        "v1_dependency_chain_position": 1,
        "required_by_surface": "obelisk.permissions_admin.v1",
        "required_by_chain_position": 2,
        "required_by_v1_dependency_chain_position": 2,
        "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
        "reviewed_artifact_hash_policy": "must match the reviewed identity surface record hash carried by the certificate",
        "missing_mismatched_or_stale_certificate_counts": False,
        "evidence": evidence,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bind_json_artifact(path)


def write_decisions_with_route_blocker(root: Path, blocker: str) -> Path:
    decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
    decisions["accounting_lock"]["current_route_blocker"] = blocker
    decisions["accounting_lock"]["remaining_route_blockers"] = [blocker]
    return write_json(root, "decisions.json", decisions)


def surfaces_with_accepted_runtime_evidence() -> dict:
    surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
    identity_surface = next(
        surface
        for surface in surfaces["surfaces"]
        if surface["id"] == "obelisk.player_identity.v1"
    )
    identity_surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
    identity_surface["blockers"] = [
        blocker
        for blocker in identity_surface["blockers"]
        if blocker != "No approved runtime principal lifecycle evidence."
    ]
    return surfaces


def bind_mutated_identity_certificate(root: Path, identity_surface: dict, mutator) -> dict[str, str]:
    binding = write_identity_promotion_certificate(root, identity_surface)
    certificate_path = REPO_ROOT / binding["path"]
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    mutator(certificate)
    certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bind_json_artifact(certificate_path)


def promote_identity_surface_for_permissions_tests(surfaces: dict) -> dict:
    identity_surface = next(
        surface
        for surface in surfaces["surfaces"]
        if surface["id"] == "obelisk.player_identity.v1"
    )
    identity_surface["status"] = "promoted"
    identity_surface["support_tier"] = "release-supported copied principal"
    identity_surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
    identity_surface["public_contract"] = [
        "ObeliskPlayerPrincipalEvent",
        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
        "UnregisterPlayerPrincipalEventWithOwnerToken",
    ]
    identity_surface["public_fields"] = [
        "abi_version",
        "struct_size",
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
    ]
    identity_surface["abi_contract"] = [
        "capability_gated",
        "append_only_abi",
        "owner_token_handle_registration",
        "owner_scoped_unregister",
        "plugin_owner_cleanup",
        "no_ue_internals_in_public_abi",
    ]
    identity_surface["lifecycle_contract"] = [
        "plugin-owner cleanup",
        "owner-token cleanup on init failure",
        "owner-token cleanup on plugin unload",
        "owner-scoped unregister cleanup",
    ]
    identity_surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
    identity_surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
    identity_surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
    identity_surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
    identity_surface["blockers"] = [
        blocker
        for blocker in identity_surface["blockers"]
        if blocker != "No approved runtime principal lifecycle evidence."
    ]
    return identity_surface


class PermissionsAdminPublicReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._permissions_admin_identity_tempdirs_before = self.permissions_admin_identity_repo_tempdirs()
        self._generated_permissions_admin_identity_tempdirs: set[Path] = set()

    def tearDown(self) -> None:
        self.assert_no_permissions_admin_identity_repo_tempdir_leaks()

    @staticmethod
    def permissions_admin_identity_repo_tempdirs() -> set[Path]:
        if not PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT.exists():
            return set()
        return {
            path
            for path in PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT.glob(
                f"{PERMISSIONS_ADMIN_IDENTITY_TEMP_PREFIX}*"
            )
            if path.is_dir() and not path.is_symlink()
        }

    def _is_guarded_permissions_admin_identity_tempdir(self, path: Path) -> bool:
        generated = getattr(self, "_generated_permissions_admin_identity_tempdirs", set())
        return (
            path in generated
            and path.parent == PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT
            and path.name.startswith(PERMISSIONS_ADMIN_IDENTITY_TEMP_PREFIX)
            and path.is_dir()
            and not path.is_symlink()
        )

    def assert_no_permissions_admin_identity_repo_tempdir_leaks(self) -> None:
        before = getattr(self, "_permissions_admin_identity_tempdirs_before", set())
        leaked = self.permissions_admin_identity_repo_tempdirs() - before
        generated_leaks = {
            path
            for path in leaked & getattr(self, "_generated_permissions_admin_identity_tempdirs", set())
            if self._is_guarded_permissions_admin_identity_tempdir(path)
        }
        for path in sorted(generated_leaks):
            shutil.rmtree(path)
        leaked = self.permissions_admin_identity_repo_tempdirs() - before
        if leaked:
            self.fail(
                "test leaked permissions/admin repo-local temp dirs in tracked test root: "
                + ", ".join(str(path.relative_to(REPO_ROOT)) for path in sorted(leaked))
            )

    @contextlib.contextmanager
    def permissions_admin_identity_tempdir(self):
        temp_dir = tempfile.TemporaryDirectory(
            dir=PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT,
            prefix=PERMISSIONS_ADMIN_IDENTITY_TEMP_PREFIX,
        )
        path = Path(temp_dir.name)
        self._generated_permissions_admin_identity_tempdirs.add(path)
        try:
            yield path
        finally:
            temp_dir.cleanup()

    def test_permissions_admin_identity_tempdir_helper_is_scoped(self) -> None:
        before = self.permissions_admin_identity_repo_tempdirs()
        with self.permissions_admin_identity_tempdir() as root:
            self.assertEqual(PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT, root.parent)
            self.assertTrue(root.name.startswith(PERMISSIONS_ADMIN_IDENTITY_TEMP_PREFIX))
            self.assertTrue(self._is_guarded_permissions_admin_identity_tempdir(root))
            (root / "artifact.json").write_text("{}", encoding="utf-8")

        self.assertFalse(root.exists())
        self.assertEqual(before, self.permissions_admin_identity_repo_tempdirs())
        self.assertFalse(
            self._is_guarded_permissions_admin_identity_tempdir(
                PERMISSIONS_ADMIN_IDENTITY_TEMP_PARENT / "OtherPrefixDoNotDelete"
            )
        )

    def test_valid_current_permissions_admin_requires_query_artifact_for_planning_acceptance(self) -> None:
        result = run_checker()
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(report["dependency"], "obelisk.player_identity.v1")
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_complete_sdk_claim"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(0, report["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertEqual(
            "obelisk.permissions-admin-public-next-steps.v1",
            report["next_steps"]["schema"],
        )
        self.assertEqual("approved_runtime_evidence_missing", report["next_steps"]["route_blocker_to_use"])
        self.assertFalse(report["next_steps"]["identity_runtime_artifact_observed"])
        self.assertFalse(report["next_steps"]["identity_contract_certificate_observed"])
        self.assertEqual(report["missing_identity_inputs"], report["next_steps"]["missing_identity_inputs"])
        self.assertEqual(
            ["accepted_runtime_principal_lifecycle_evidence"],
            [item["id"] for item in report["missing_identity_inputs"]],
        )
        self.assertFalse(report["identity_input_diagnostics"]["accepted_runtime_evidence_observed"])
        self.assertFalse(report["identity_input_diagnostics"]["identity_public_contract_certificate_observed"])
        self.assertEqual(
            "surfaces[obelisk.player_identity.v1].evidence.accepted_runtime_evidence",
            report["missing_identity_inputs"][0]["attach_to"],
        )
        self.assertFalse(report["missing_identity_inputs"][0]["counts_toward_permissions_admin"])
        self.assertFalse(report["missing_identity_inputs"][0]["permissions_admin_unlock_allowed"])
        self.assertEqual(
            ["produce_approved_runtime_principal_lifecycle_evidence"],
            [step["id"] for step in report["next_steps"]["steps"]],
        )
        post_identity = report["post_identity_next_requirement"]
        self.assertEqual(post_identity, report["next_steps"]["post_identity_next_requirement"])
        self.assertEqual("resolve_permissions_admin_query_public_header_gate", post_identity["id"])
        self.assertEqual("obelisk.player_identity.v1", post_identity["after_surface"])
        self.assertEqual("obelisk.permissions_admin.v1", post_identity["surface"])
        self.assertEqual("public_header_gate_missing", post_identity["route_blocker_to_use"])
        self.assertEqual(
            "query-only fail-closed permission decision checks over copied principals",
            post_identity["required_public_surface"],
        )
        self.assertIn("plugin_owner_token", post_identity["required_query_fields"])
        self.assertIn("request_flags", post_identity["required_query_fields"])
        self.assertIn("server_process_epoch", post_identity["required_query_fields"])
        for key in (
            "public_header_allowed",
            "public_abi_ready",
            "public_sdk_ready",
            "runtime_ready",
            "stable_claim_allowed",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "public_or_runtime_accounting_allowed",
            "permissions_admin_route_ready",
            "missing_mismatched_or_stale_identity_certificate_counts",
            "identity_alias_or_stale_source_unlock_allowed",
            "identity_decision_record_alone_unlock_allowed",
            "runtime_evidence_alone_unlock_allowed",
        ):
            self.assertFalse(post_identity[key])
        self.assertEqual(
            "reviewed_identity_public_contract_decision_record",
            post_identity["required_identity_public_contract_review"]["id"],
        )
        self.assertEqual(
            "hash_bound_player_identity_promotion_certificate",
            post_identity["required_identity_promotion_certificate"]["id"],
        )
        self.assertEqual(
            "evidence.reviewed_surface_record_sha256",
            post_identity["required_identity_promotion_certificate"]["required_reviewed_artifact_hash"],
        )
        self.assertFalse(
            post_identity["required_identity_promotion_certificate"][
                "missing_mismatched_or_stale_certificate_counts"
            ]
        )
        self.assertTrue(
            {
                "passive_monitor",
                "passive_summary",
                "beta_notice",
                "next_action_report",
                "status_report",
                "copied_log_only",
                "copied_log_only_artifact",
                "handoff_notes",
                "kick",
                "kick_player",
                "kickplayer",
                "compact_context",
                "package_shape_install",
                "package_shape_support",
                "plugin_hub_planning",
                "side_lane_artifact",
                "stable_claim",
                "active_player_presence",
                "active_players",
                "admin_route_snapshot",
                "admin_snapshot",
                "admin_status_snapshot",
                "diagnostic_drift",
                "live_posture",
                "live_server_posture",
                "observer_enabled",
                "observer_enablement",
                "player_presence",
                "runtime_posture",
                "server_posture",
            }.issubset(set(post_identity["shortcut_artifacts_never_count"]))
        )
        self.assertEqual(
            post_identity["shortcut_artifacts_never_count"],
            post_identity["non_evidence_artifacts"],
        )
        diagnostics = report["post_identity_query_only_diagnostics"]
        self.assertEqual(diagnostics, report["next_steps"]["post_identity_query_only_diagnostics"])
        self.assertEqual(
            "obelisk.permissions-admin-post-identity-query-only-diagnostics.v1",
            diagnostics["schema"],
        )
        self.assertTrue(diagnostics["diagnostic_only"])
        self.assertTrue(diagnostics["non_evidence"])
        self.assertTrue(diagnostics["non_authorizing"])
        self.assertFalse(diagnostics["identity_public_contract_promoted"])
        self.assertEqual("blocked_until_hash_bound_player_identity_promotion", diagnostics["stage"])
        self.assertEqual("approved_runtime_evidence_missing", diagnostics["route_blocker_to_use"])
        self.assertEqual("public_header_gate_missing", diagnostics["post_identity_route_blocker"])
        self.assertIn("query_only_planning_ready", diagnostics["query_only_ready_aliases_rejected"])
        for key in READINESS.QUERY_ONLY_DIAGNOSTIC_FALSE_KEYS:
            self.assertFalse(diagnostics[key])
        for key in READINESS.QUERY_ONLY_DIAGNOSTIC_ZERO_KEYS:
            self.assertEqual(0, diagnostics[key])

    def test_rejects_identity_contract_route_blocker_before_runtime_evidence(self) -> None:
        result = run_checker(
            "--current-route-blocker",
            "identity_public_contract_gate_missing",
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])

    def test_rejects_identity_contract_route_blocker_with_noncanonical_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity["evidence"]["accepted_runtime_evidence"] = minimal_accepted_runtime_evidence_record()
            identity["blockers"] = [
                blocker
                for blocker in identity["blockers"]
                if blocker != "No approved runtime principal lifecycle evidence."
            ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertIn("player_identity_accepted_runtime_evidence_not_canonical", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_stale_runtime_route_after_accepted_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces_path = write_json(root, "surfaces.json", surfaces_with_accepted_runtime_evidence())

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("current_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn("accounting_lock_route_blocker_stale_after_approved_runtime_evidence", report["blockers"])
        self.assertIn(
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            report["blockers"],
        )
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])

    def test_rejects_public_header_route_blocker_before_identity_contract_review(self) -> None:
        result = run_checker(
            "--current-route-blocker",
            "public_header_gate_missing",
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertIn("current_route_blocker_before_identity_public_contract_review", report["blockers"])
        self.assertEqual("public_header_gate_missing", report["current_route_blocker"])
        self.assertEqual(["public_header_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])

    def test_rejects_accounting_lock_identity_route_before_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = ["identity_public_contract_gate_missing"]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accounting_lock_route_blocker_out_of_order", report["blockers"])
        self.assertIn("accounting_lock_remaining_route_blocker_out_of_order", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_accounting_lock_public_header_route_before_identity_contract_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions_path = write_decisions_with_route_blocker(root, "public_header_gate_missing")

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accounting_lock_route_blocker_before_identity_public_contract_review", report["blockers"])
        self.assertIn("accounting_lock_remaining_route_blocker_before_identity_public_contract_review", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_accepts_candidate_query_failclosed_manifest_only_as_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "permissions-query.json"
            subprocess.run(
                [sys.executable, str(QUERY_CHECKER), "--emit-template", str(manifest_path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            result = run_checker("--query-failclosed-artifact", str(manifest_path))
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(report["accepted_for_planning"])
            self.assertEqual(
                report["query_failclosed_artifact_schema"],
                "obelisk.permissions-admin-query-failclosed-contract.v1",
            )
            self.assertFalse(report["public_sdk_ready"])

    def test_rejects_query_failclosed_checker_report_as_planning_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "permissions-query.json"
            subprocess.run(
                [sys.executable, str(QUERY_CHECKER), "--emit-template", str(manifest_path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report_path = root / "permissions-query-report.json"
            query_report = subprocess.run(
                [sys.executable, str(QUERY_CHECKER), str(manifest_path), "--json"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report_path.write_text(query_report.stdout, encoding="utf-8")
            result = run_checker("--query-failclosed-artifact", str(report_path), check=False)
            report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertFalse(report["accepted_for_planning"])
            self.assertIn("query_failclosed_report_not_accepted_as_artifact", report["blockers"])
            self.assertEqual(
                report["query_failclosed_artifact_schema"],
                None,
            )

    def test_rejects_fabricated_query_failclosed_report_as_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "fake-query-report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "schema": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
                        "mode": "consume",
                        "ready": True,
                        "promotion_ready": False,
                        "public_header_allowed": False,
                        "public_cache_abi_allowed": False,
                        "public_sdk_ready": False,
                        "runtime_ready": False,
                    }
                ),
                encoding="utf-8",
            )

            result = run_checker("--query-failclosed-artifact", str(report_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(1, result.returncode)
        self.assertIn("query_failclosed_report_not_accepted_as_artifact", report["blockers"])

    def test_accepts_canonical_query_failclosed_manifest_as_planning_only(self) -> None:
        result = run_checker("--query-failclosed-artifact", str(CANONICAL_QUERY_CONTRACT))
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertEqual(
            report["query_failclosed_artifact_schema"],
            "obelisk.permissions-admin-query-failclosed-contract.v1",
        )
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertFalse(report["counts_toward_public_sdk"])

    def test_rejects_query_only_planning_candidate_aliases_as_public_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = json.loads(CANONICAL_QUERY_CONTRACT.read_text(encoding="utf-8"))
            artifact["queryOnlyPlanningReady"] = True
            artifact["query_failclosed_candidate"] = {
                "artifact_kind": "query_failclosed_candidate",
                "status": "ready",
                "counts_toward_p0_progress": 1,
            }
            artifact_path = write_json(root, "query-alias-overclaim.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(0, report["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"]}
        self.assertIn("$.query_failclosed_artifact.queryOnlyPlanningReady", labels)
        self.assertIn("$.query_failclosed_artifact.query_failclosed_candidate.status", labels)

    def test_rejects_nested_generic_readiness_progress_aliases_as_public_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = json.loads(CANONICAL_QUERY_CONTRACT.read_text(encoding="utf-8"))
            artifact["offline_planning"] = {
                "nested": {
                    "adminPromotionReady": True,
                    "sdkProgressContribution": 1,
                }
            }
            artifact_path = write_json(root, "query-nested-generic-overclaim.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("generic_readiness_or_progress_alias_overclaim", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"]}
        self.assertIn("$.query_failclosed_artifact.offline_planning.nested.adminPromotionReady", labels)
        self.assertIn("$.query_failclosed_artifact.offline_planning.nested.sdkProgressContribution", labels)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])

    def test_accepts_candidate_only_multi_surface_beta_capture_as_debug_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_path = write_json(root, "beta-capture.json", beta_capture_manifest())

            result = run_checker("--beta-capture-artifact", str(artifact_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertEqual(
            READINESS.BETA_CAPTURE_CANDIDATES_SCHEMA,
            report["beta_capture_artifact_schema"],
        )
        self.assertEqual(
            sorted(READINESS.BETA_CAPTURE_REQUIRED_SURFACES),
            report["beta_capture_candidate_surfaces"],
        )
        self.assertTrue(report["beta_capture_candidate_only"])
        self.assertTrue(report["beta_capture_candidate_prep_visible"])
        self.assertTrue(report["beta_capture_candidate_prep_only"])
        self.assertTrue(report["beta_capture_debug_only"])
        self.assertTrue(report["beta_capture_requires_own_checker_acceptance"])
        self.assertTrue(report["beta_capture_requires_player_principal_triplet"])
        self.assertFalse(report["beta_capture_clears_approved_runtime_evidence_missing"])
        self.assertFalse(report["beta_capture_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["beta_capture_counts_as_runtime_evidence"])
        self.assertFalse(report["beta_capture_counts_as_sdk_progress"])
        self.assertFalse(report["beta_capture_counts_as_p0_progress"])
        self.assertFalse(report["beta_capture_replaces_player_principal_evidence"])
        self.assertFalse(report["beta_capture_counts_toward_public_sdk"])
        self.assertFalse(report["beta_capture_counts_toward_runtime"])
        self.assertFalse(report["beta_capture_counts_toward_v1_completion"])
        self.assertIn("candidate/debug", report["beta_capture_non_claim"])
        self.assertIn("player-principal triplet", report["beta_capture_non_claim"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(
            ["produce_approved_runtime_principal_lifecycle_evidence"],
            [step["id"] for step in report["next_steps"]["steps"]],
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_build_report_allows_internal_namespace_without_optional_capture_artifacts(self) -> None:
        report = READINESS.build_report(
            argparse.Namespace(
                decisions=DECISIONS,
                surfaces=SURFACES,
                public_header=HEADER,
                current_route_blocker="approved_runtime_evidence_missing",
            )
        )

        self.assertTrue(report["valid"], report["blockers"])
        self.assertIsNone(report["query_failclosed_artifact_schema"])
        self.assertIsNone(report["beta_capture_artifact_schema"])
        self.assertFalse(report["beta_capture_candidate_prep_visible"])
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])

    def test_rejects_beta_capture_candidate_overclaims_and_triplet_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = beta_capture_manifest()
            artifact["public_sdk_ready"] = True
            artifact["runtime_ready"] = True
            artifact["counts_toward_public_sdk"] = True
            artifact["replaces_player_principal_evidence"] = True
            artifact["notes"] = [
                "admin/list-player/kick-path beta capture makes public SDK ready"
            ]
            artifact["candidate_debug_surfaces"][1]["requires_player_principal_triplet"] = False
            artifact["candidate_debug_surfaces"][2]["runtime_ready"] = True
            artifact_path = write_json(root, "beta-capture.json", artifact)

            result = run_checker("--beta-capture-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertIn("beta_capture_artifact_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("beta_capture_artifact_runtime_ready_not_false", report["blockers"])
        self.assertIn("beta_capture_artifact_counts_toward_public_sdk_not_false", report["blockers"])
        self.assertIn(
            "beta_capture_artifact_replaces_player_principal_evidence_not_false",
            report["blockers"],
        )
        self.assertIn(
            "beta_capture_candidate_requires_player_principal_triplet_not_true",
            report["blockers"],
        )
        self.assertIn("beta_capture_candidate_runtime_ready_not_false", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertFalse(report["beta_capture_replaces_player_principal_evidence"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_list_player_kick_path_beta_candidates_remain_visible_but_fail_closed_on_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = beta_capture_manifest()
            artifact["candidate_debug_surfaces"][1].update(
                {
                    "approved_runtime_evidence": True,
                    "approved_runtime_evidence_ready": True,
                    "clears_approved_runtime_evidence_missing": True,
                    "counts_as_approved_runtime_evidence": True,
                    "counts_as_runtime_evidence": True,
                    "counts_as_sdk_progress": True,
                    "counts_as_p0_progress": True,
                    "counts_toward_p0": True,
                    "counts_toward_sdk": True,
                    "identity_runtime_evidence_satisfied": True,
                    "player_identity_runtime_evidence_satisfied": True,
                    "public_ready": True,
                    "p0_progress": 1,
                }
            )
            artifact["candidate_debug_surfaces"][2].update(
                {
                    "player_principal_runtime_evidence_satisfied": True,
                    "plugin_hub_ready": True,
                    "publication_ready": True,
                    "stable_sdk_ready": True,
                    "public_sdk_progress": 1,
                    "runtime_evidence_progress_contribution": 1,
                    "sdk_progress": 1,
                }
            )
            artifact_path = write_json(root, "beta-capture.json", artifact)

            result = run_checker("--beta-capture-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        blockers = set(report["blockers"])
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertTrue(report["beta_capture_candidate_prep_visible"])
        self.assertTrue(report["beta_capture_candidate_prep_only"])
        self.assertIn("list_player", report["beta_capture_candidate_surfaces"])
        self.assertIn("kick_path", report["beta_capture_candidate_surfaces"])
        self.assertIn("beta_capture_candidate_approved_runtime_evidence_not_false", blockers)
        self.assertIn(
            "beta_capture_candidate_clears_approved_runtime_evidence_missing_not_false",
            blockers,
        )
        self.assertIn("beta_capture_candidate_counts_as_approved_runtime_evidence_not_false", blockers)
        self.assertIn("beta_capture_candidate_counts_as_runtime_evidence_not_false", blockers)
        self.assertIn("beta_capture_candidate_counts_as_sdk_progress_not_false", blockers)
        self.assertIn("beta_capture_candidate_counts_as_p0_progress_not_false", blockers)
        self.assertIn("beta_capture_candidate_counts_toward_p0_not_false", blockers)
        self.assertIn("beta_capture_candidate_counts_toward_sdk_not_false", blockers)
        self.assertIn("beta_capture_candidate_identity_runtime_evidence_satisfied_not_false", blockers)
        self.assertIn(
            "beta_capture_candidate_player_identity_runtime_evidence_satisfied_not_false",
            blockers,
        )
        self.assertIn(
            "beta_capture_candidate_player_principal_runtime_evidence_satisfied_not_false",
            blockers,
        )
        self.assertIn("beta_capture_candidate_public_ready_not_false", blockers)
        self.assertIn("beta_capture_candidate_plugin_hub_ready_not_false", blockers)
        self.assertIn("beta_capture_candidate_publication_ready_not_false", blockers)
        self.assertIn("beta_capture_candidate_stable_sdk_ready_not_false", blockers)
        self.assertIn("beta_capture_candidate_p0_progress_not_zero", blockers)
        self.assertIn("beta_capture_candidate_public_sdk_progress_not_zero", blockers)
        self.assertIn(
            "beta_capture_candidate_runtime_evidence_progress_contribution_not_zero",
            blockers,
        )
        self.assertIn("beta_capture_candidate_sdk_progress_not_zero", blockers)
        self.assertEqual("approved_runtime_evidence_missing", report["current_route_blocker"])
        self.assertEqual(["approved_runtime_evidence_missing"], report["remaining_route_blockers"])
        self.assertEqual("approved_runtime_evidence_missing", report["next_steps"]["route_blocker_to_use"])
        self.assertFalse(report["next_steps"]["identity_runtime_artifact_observed"])
        self.assertEqual(
            ["produce_approved_runtime_principal_lifecycle_evidence"],
            [step["id"] for step in report["next_steps"]["steps"]],
        )
        self.assertFalse(report["beta_capture_clears_approved_runtime_evidence_missing"])
        self.assertFalse(report["beta_capture_counts_as_approved_runtime_evidence"])
        self.assertFalse(report["beta_capture_counts_as_runtime_evidence"])
        self.assertFalse(report["beta_capture_counts_as_sdk_progress"])
        self.assertFalse(report["beta_capture_counts_as_p0_progress"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_admin_source_status_aliases_without_identity_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"].pop("player_identity_promotion_certificate", None)
            permissions = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.permissions_admin.v1"
            )
            permissions["admin_status_aliases"] = [
                {"admin_kind": "ListPlayers", "status": "ready"},
                {"alias_source": "RCON", "state": "ready"},
                {"source_alias": "ServerKickPlayer", "outcome": "accepted"},
                {"status_source": "admin_snapshot", "status": "ready"},
            ]
            decisions_path = write_decisions_with_route_blocker(
                root,
                "identity_public_contract_gate_missing",
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_missing", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        self.assertIn(
            "route_or_runtime_readiness_alias_missing_upstream_certificates",
            report["blockers"],
        )
        certificate_alias_labels = [
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        ]
        certificate_alias_details = [
            detail
            for detail in report["blocker_details"]
            if detail["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        ]
        for suffix in (
            ".admin_status_aliases[0].status",
            ".admin_status_aliases[1].state",
            ".admin_status_aliases[2].outcome",
            ".admin_status_aliases[3].status",
        ):
            self.assertTrue(
                any(label.endswith(suffix) for label in certificate_alias_labels),
                certificate_alias_labels,
            )
        for detail in certificate_alias_details:
            self.assertEqual(
                READINESS.REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
                detail["required_certificate_binding"],
            )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["p0_progress_ready"])

    def test_rejects_inline_certificate_alias_shortcuts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"].pop("player_identity_promotion_certificate", None)
            identity_surface["evidence"]["inline_player_identity_promotion_certificate"] = {
                "schema": "obelisk.player-identity-promotion-certificate.v1",
                "promotion_status": "promoted",
            }
            permissions = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.permissions_admin.v1"
            )
            permissions.setdefault("evidence", {})[
                "permissionsAdminPromotionCertificateInline"
            ] = {
                "schema": "obelisk.permissions-admin-promotion-certificate.v1",
                "promotion_status": "blocked_public_header_gate_missing",
            }
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "player_identity_promotion_certificate_alias_or_inline_shortcut",
            report["blockers"],
        )
        self.assertIn(
            "permissions_admin_promotion_certificate_alias_or_inline_shortcut",
            report["blockers"],
        )
        self.assertIn("player_identity_promotion_certificate_missing", report["blockers"])
        labels = {detail["label"] for detail in report["blocker_details"]}
        self.assertIn(
            "$.surfaces[player_identity].evidence.inline_player_identity_promotion_certificate",
            labels,
        )
        self.assertIn(
            "$.surfaces[permissions_admin].evidence.permissionsAdminPromotionCertificateInline",
            labels,
        )
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual(report["p0_dependency_chain_claim_progress_contribution"], 0)

    def test_internal_authz_reason_flags_do_not_claim_manifest_bit_compatibility(self) -> None:
        header = AUTHZ_DECISION_MODEL.read_text(encoding="utf-8")

        self.assertIn("Internal diagnostics only", header)
        self.assertIn("not the public/candidate", header)
        self.assertIn("fail_closed_reason_flags artifact contract", header)
        self.assertIn("must not cross the SDK boundary", header)

    def test_rejects_missing_abuse_rate_limit_audit_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            for item in decisions["required_before_public_header"]:
                if item["id"] == "abuse.query_rate_limit_and_audit_gate":
                    item["required_behavior"] = [
                        entry
                        for entry in item["required_behavior"]
                        if entry != "rate-limit state is not a public cache ABI"
                    ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("abuse_rate_limit_audit_requirements_missing", report["blockers"])

    def test_rejects_missing_separation_sequence_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            for item in decisions["required_before_public_header"]:
                if item["id"] == "separation.no_commands_replies_or_admin_mutation":
                    item["v1_sequence_gate"] = [
                        entry
                        for entry in item["v1_sequence_gate"]
                        if entry != "query-only permission result provenance is required before command response"
                    ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("separation_sequence_gate_requirements_missing", report["blockers"])

    def test_rejects_public_contract_and_header_overclaims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_header_allowed"] = True
            decisions["public_cache_abi_allowed"] = True
            decisions["public_header_symbols_now"] = ["ObeliskPermissionQuery", "ObeliskPermissionReasonFlags"]
            decisions_path = write_json(root, "decisions.json", decisions)

            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                HEADER.read_text(encoding="utf-8") +
                "\nstruct ObeliskPermissionQuery {};\n"
                "typedef uint64_t ObeliskPermissionReasonFlags;\n"
                "#define OBELISK_PERMISSION_REASON_DENY 1\n"
                "uint64_t reason_flags;\n"
            )

            result = run_checker("--decisions", str(decisions_path), "--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_cache_abi_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_header_contains_permissions_admin_symbol", report["blockers"])

    def test_public_header_scan_ignores_comments_and_identifier_supersets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                "/* ObeliskPermissionQuery and OBELISK_PERMISSION_REASON_DENY stay blocked. */\n"
                "// RegisterPermission and CheckPermissionWithOwnerToken remain absent.\n"
                "typedef struct MyObeliskPermissionQuerySuffix MyObeliskPermissionQuerySuffix;\n"
                "#define OBELISK_PERMISSION_REASONABLE_NAME 1\n"
                "uint64_t not_reason_flags_or_ReasonFlags_suffix;\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertNotIn("public_header_contains_permissions_admin_symbol", report["blockers"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_public_header_scan_rejects_exact_symbols_and_blocked_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                "typedef struct ObeliskPermissionQuery ObeliskPermissionQuery;\n"
                "#define OBELISK_PERMISSION_REASON_DENY 1\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_permissions_admin_symbol", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "public_header_contains_permissions_admin_symbol"
        )
        self.assertIn("ObeliskPermissionQuery", detail["tokens"])
        self.assertIn("OBELISK_PERMISSION_REASON_", detail["tokens"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_expanded_post_identity_allowed_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["allowed_public_surface_after_player_identity"].append("admin mutation actions")
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "allowed_public_surface_after_player_identity_not_exact_query_only",
            report["blockers"],
        )

    def test_rejects_post_identity_next_requirement_public_runtime_or_stable_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            post_identity = decisions["post_identity_next_requirement"]
            post_identity["runtime_ready"] = True
            post_identity["stable_claim_allowed"] = True
            post_identity["permissions_admin_route_ready"] = True
            post_identity["identity_alias_or_stale_source_unlock_allowed"] = True
            post_identity["missing_mismatched_or_stale_identity_certificate_counts"] = True
            post_identity["route_blocker_to_use"] = "identity_public_contract_gate_missing"
            post_identity["shortcut_artifacts_never_count"] = [
                item
                for item in post_identity["shortcut_artifacts_never_count"]
                if item
                not in {
                    "compact_context",
                    "copied_log_only",
                    "copied_log_only_artifact",
                    "package_shape_install",
                    "package_shape_support",
                    "passive_summary",
                    "plugin_hub_planning",
                }
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("post_identity_next_requirement_mismatch", report["blockers"])
        self.assertIn("post_identity_next_requirement_claim_not_false", report["blockers"])
        self.assertIn("post_identity_shortcut_artifacts_never_count_missing", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_positive_reply_router_public_abi_runtime_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_abi_ready"] = True
            decisions["reply_send_chat_router_claims_allowed"] = True
            decisions["notes"] = [
                "reply API is public and ready",
                "send-chat is available",
                "command router is enabled",
                "runtime delivery is supported",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])

    def test_rejects_public_abi_identity_lookup_handle_wording(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "notes": [
                    "public ABI exposes player lookup handles before ResourceHandle promotion",
                    "public ABI does not expose player lookup handles before ResourceHandle promotion",
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_abi_identity_lookup_handle_claim", "$.notes[0]"), paths)
        self.assertNotIn(("public_abi_identity_lookup_handle_claim", "$.notes[1]"), paths)

    def test_mixed_negation_does_not_hide_positive_runtime_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "permissions/admin remains blocked but runtime ready"}, blockers)

        self.assertEqual(
            [
                "positive_public_surface_claim",
                "route_or_runtime_readiness_alias_missing_upstream_certificates",
            ],
            [item["reason"] for item in blockers],
        )

    def test_negative_runtime_suffix_is_not_positive_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "runtime ready remains blocked"}, blockers)

        self.assertEqual([], blockers)

    def test_blocker_container_does_not_hide_positive_readiness_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "blockers": [
                    "public SDK is ready",
                    "runtime ready remains blocked",
                ],
                "promotion_requires": [
                    "public SDK must be promoted before release",
                ],
            },
            blockers,
        )

        self.assertEqual(
            [("positive_public_surface_claim", "$.blockers[0]")],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_nested_stable_and_v1_completion_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "nested": {
                    "stableClaimAllowed": True,
                    "stableReleaseReady": True,
                    "stablePublicationAuthorized": True,
                    "pluginHubPublication": True,
                    "pluginHubPublished": "published",
                    "publication": True,
                    "publicationAuthorized": True,
                    "releasePublicationReady": True,
                    "v1-completion-ready": True,
                },
                "notes": [
                    "Plugin Hub publication is published",
                    "publication is authorized",
                    "stable release is ready",
                    "release publication is ready",
                    "Plugin Hub is published",
                ],
            },
            blockers,
        )

        reason_labels = [(item["reason"], item["label"]) for item in blockers]
        for label in (
            "$.nested.stableClaimAllowed",
            "$.nested.stableReleaseReady",
            "$.nested.stablePublicationAuthorized",
            "$.nested.pluginHubPublication",
            "$.nested.pluginHubPublished",
            "$.nested.publication",
            "$.nested.publicationAuthorized",
            "$.nested.releasePublicationReady",
            "$.nested.v1-completion-ready",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(5):
            self.assertIn(
                ("positive_public_surface_claim", f"$.notes[{index}]"),
                reason_labels,
            )
        self.assertFalse(
            any(
                item["reason"] == "route_ready"
                or item["reason"] == "permissions_admin_route_ready"
                for item in blockers
            )
        )

    def test_rejects_nested_accounting_and_runtime_authorization_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "counts_toward_public_sdk": True,
                    "counts_toward_runtime": True,
                    "counts_toward_v1_completion": True,
                    "public_or_runtime_accounting_allowed": True,
                    "live_ops_authorized": True,
                    "runtime_work_authorized": True,
                    "runtime_capture_authorized": True,
                    "workspace_writes_authorized": True,
                    "reads_live_logs": True,
                    "server_operations_authorized": True,
                    "commandResponseReady": True,
                    "commandResponseUnlocked": True,
                    "commandChatResponseReady": True,
                    "commandsReady": True,
                    "commandsRepliesReady": True,
                    "commandsRepliesUnlocked": True,
                    "chatRepliesReady": True,
                    "promotedSurfaceCount": 1,
                    "promoted_surfaces_count": "1/4",
                    "surfacePromotionCount": 1,
                    "promotedSurfaceTotal": 1,
                    "promoted_surfaces_total": "1/4",
                    "surfacePromotionTotal": 1,
                    "promotedSurfaceCountZero": "0/4",
                    "promotedSurfaceTotalZero": "0/4",
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.counts_toward_public_sdk"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_runtime"),
                ("public_surface_overclaim", "$.secondary_report.counts_toward_v1_completion"),
                ("public_surface_overclaim", "$.secondary_report.public_or_runtime_accounting_allowed"),
                ("public_surface_overclaim", "$.secondary_report.live_ops_authorized"),
                ("public_surface_overclaim", "$.secondary_report.runtime_work_authorized"),
                ("public_surface_overclaim", "$.secondary_report.runtime_capture_authorized"),
                ("public_surface_overclaim", "$.secondary_report.workspace_writes_authorized"),
                ("public_surface_overclaim", "$.secondary_report.reads_live_logs"),
                ("public_surface_overclaim", "$.secondary_report.server_operations_authorized"),
                ("public_surface_overclaim", "$.secondary_report.commandResponseReady"),
                ("public_surface_overclaim", "$.secondary_report.commandResponseUnlocked"),
                ("public_surface_overclaim", "$.secondary_report.commandChatResponseReady"),
                ("public_surface_overclaim", "$.secondary_report.commandsReady"),
                ("public_surface_overclaim", "$.secondary_report.commandsRepliesReady"),
                ("public_surface_overclaim", "$.secondary_report.commandsRepliesUnlocked"),
                ("public_surface_overclaim", "$.secondary_report.chatRepliesReady"),
                ("public_surface_overclaim", "$.secondary_report.promotedSurfaceCount"),
                ("public_surface_overclaim", "$.secondary_report.promoted_surfaces_count"),
                ("public_surface_overclaim", "$.secondary_report.surfacePromotionCount"),
                ("public_surface_overclaim", "$.secondary_report.promotedSurfaceTotal"),
                ("public_surface_overclaim", "$.secondary_report.promoted_surfaces_total"),
                ("public_surface_overclaim", "$.secondary_report.surfacePromotionTotal"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_broad_accept_promote_and_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "permissionsAdminAccepted": True,
                    "permissionsAdminPromoted": {"status": "ready"},
                    "commandResponsePromoted": True,
                    "commandsRepliesAccepted": "ready",
                    "routePromoted": True,
                    "publicRuntimeReadinessPromoted": True,
                    "v1CompletionProgressContribution": "25%",
                    "p0DependencyChainProgressContribution": 1,
                    "progress": "1/2",
                    "runtimeEvidenceReady": True,
                },
                "split_claims": [
                    {"field": "permissionsAdminAccepted", "status": "accepted"},
                    {"name": "commandResponsePromoted", "value": {"state": "ready"}},
                    {"key": "v1CompletionProgress", "value": "10%"},
                    {"field": "commandsRepliesAccepted", "status": "blocked"},
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.secondary_report.permissionsAdminAccepted",
            "$.secondary_report.permissionsAdminPromoted",
            "$.secondary_report.commandResponsePromoted",
            "$.secondary_report.commandsRepliesAccepted",
            "$.secondary_report.routePromoted",
            "$.secondary_report.publicRuntimeReadinessPromoted",
            "$.secondary_report.v1CompletionProgressContribution",
            "$.secondary_report.p0DependencyChainProgressContribution",
            "$.secondary_report.progress",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        self.assertNotIn(("public_surface_overclaim", "$.secondary_report.runtimeEvidenceReady"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.split_claims[3]"), paths)

    def test_rejects_nested_child_route_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "permissionReady": True,
                    "permissionsAdminReady": True,
                    "permissions-ready": True,
                    "publicSdk": True,
                    "publicReplyApi": True,
                    "replyAllowed": True,
                    "replyApiAllowed": True,
                    "sendChatApiAllowed": True,
                }
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.permissionReady"),
                ("public_surface_overclaim", "$.secondary_report.permissionsAdminReady"),
                ("public_surface_overclaim", "$.secondary_report.permissions-ready"),
                ("public_surface_overclaim", "$.secondary_report.publicSdk"),
                ("public_surface_overclaim", "$.secondary_report.publicReplyApi"),
                ("public_surface_overclaim", "$.secondary_report.replyAllowed"),
                ("public_surface_overclaim", "$.secondary_report.replyApiAllowed"),
                ("public_surface_overclaim", "$.secondary_report.sendChatApiAllowed"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_unlocked_public_abi_reply_send_chat_claim_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "publicAbiUnlocked": True,
                    "publicReplyAbiUnlocked": True,
                    "replyUnlocked": True,
                    "sendChatApiUnlocked": True,
                },
                "claims": [
                    "public_abi_unlocked",
                    "reply_abi_unlocked",
                    "send_chat_api_unlocked",
                    "publicReplyOrSendChatAbiUnlocked",
                    "send_chat_api_unlocked remains blocked",
                ],
            },
            blockers,
        )

        self.assertEqual(4, [item["reason"] for item in blockers].count("public_surface_overclaim"))
        self.assertEqual(4, [item["reason"] for item in blockers].count("positive_public_surface_claim"))
        self.assertNotIn(("positive_public_surface_claim", "$.claims[4]"), [(item["reason"], item["label"]) for item in blockers])

    def test_rejects_post_identity_misleading_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "identityContractReviewed": True,
                    "principalReady": True,
                    "permissionsQueryReady": True,
                    "permissionsUnlocked": True,
                    "permissionHeaderAllowed": True,
                    "adminAuthorityReady": True,
                    "acceptedRuntimeEvidenceReady": True,
                },
                "notes": [
                    "identity contract reviewed",
                    "principal ready",
                    "permissions query ready",
                    "permissions unlocked",
                    "permission header allowed",
                    "admin authority ready",
                    "accepted runtime evidence ready",
                ],
            },
            blockers,
        )

        self.assertEqual(
            [
                ("public_surface_overclaim", "$.secondary_report.identityContractReviewed"),
                ("public_surface_overclaim", "$.secondary_report.principalReady"),
                ("public_surface_overclaim", "$.secondary_report.permissionsQueryReady"),
                ("public_surface_overclaim", "$.secondary_report.permissionsUnlocked"),
                ("public_surface_overclaim", "$.secondary_report.permissionHeaderAllowed"),
                ("public_surface_overclaim", "$.secondary_report.adminAuthorityReady"),
                ("public_surface_overclaim", "$.secondary_report.acceptedRuntimeEvidenceReady"),
                ("positive_public_surface_claim", "$.notes[0]"),
                ("positive_public_surface_claim", "$.notes[1]"),
                ("positive_public_surface_claim", "$.notes[2]"),
                ("positive_public_surface_claim", "$.notes[3]"),
                ("positive_public_surface_claim", "$.notes[4]"),
                ("positive_public_surface_claim", "$.notes[5]"),
                ("positive_public_surface_claim", "$.notes[6]"),
            ],
            [(item["reason"], item["label"]) for item in blockers],
        )

    def test_rejects_identity_contract_capability_certificate_and_route_gate_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "secondary_report": {
                    "identityPublicContractReady": True,
                    "playerIdentityPublicContractReady": True,
                    "playerIdentityPromotionCertificateReady": True,
                    "publicCapabilityAdvertised": True,
                    "publicContractReviewed": True,
                    "routeGateUnlocked": True,
                },
                "claims": [
                    "accepted runtime evidence is accepted",
                    "player identity public contract is ready",
                    "promotion certificate is promoted",
                    "public capability is advertised",
                    "route gate opened for permissions/admin",
                    "ready route gate",
                ],
            },
            blockers,
        )

        self.assertEqual(6, [item["reason"] for item in blockers].count("public_surface_overclaim"))
        self.assertEqual(6, [item["reason"] for item in blockers].count("positive_public_surface_claim"))

    def test_rejects_reviewed_identity_contract_and_runtime_evidence_key_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "reviewedIdentityPublicContract": True,
                    "reviewedIdentityPublicContractReady": True,
                    "reviewedPlayerIdentityPublicContractReady": True,
                    "identityPublicContractGatePassed": True,
                    "identityPublicContractGateResolved": True,
                    "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin": True,
                    "playerIdentityEvidenceAccepted": True,
                    "identityContractReviewComplete": True,
                },
                "split_claims": [
                    {"field": "reviewedIdentityPublicContractReady", "state": "reviewed"},
                    {"claim": "identityPublicContractGatePassed", "value": "passed"},
                    {"name": "playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin", "enabled": "yes"},
                ],
                "notes": [
                    "reviewed identity public contract unlocks permissions/admin",
                    "identity public contract gate passed so permission query ready",
                    "player identity runtime evidence unlocks permissions/admin",
                    "accepted runtime evidence remains normalized only to identity_public_contract_gate_missing",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.aliases.playerIdentityRuntimeEvidenceUnlocksPermissionsAdmin",
            "$.aliases.playerIdentityEvidenceAccepted",
            "$.aliases.identityContractReviewComplete",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
        ):
            self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.aliases.reviewedIdentityPublicContract",
            "$.aliases.reviewedIdentityPublicContractReady",
            "$.aliases.reviewedPlayerIdentityPublicContractReady",
            "$.aliases.identityPublicContractGatePassed",
            "$.aliases.identityPublicContractGateResolved",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.notes[0]",
            "$.notes[1]",
        ):
            self.assertIn(("route_or_runtime_readiness_alias_missing_upstream_certificates", label), paths)
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_rejects_broad_release_sdk_wording_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "release_notes": [
                    "complete SDK is ready",
                    "full SDK is available",
                    "production SDK is supported",
                    "stable SDK is enabled",
                    "v1.0 stable is public",
                    "release readiness is ready",
                    "v1 SDK completion is supported",
                ],
                "aliases": {
                    "completeSdkReady": True,
                    "full-sdk-ready": True,
                    "production sdk ready": True,
                    "stableSdkReady": True,
                    "releaseReadinessReady": True,
                    "v1.0-stable-ready": True,
                },
            },
            blockers,
        )

        reasons = [item["reason"] for item in blockers]
        self.assertEqual(7, reasons.count("positive_public_surface_claim"))
        self.assertEqual(6, reasons.count("public_surface_overclaim"))

    def test_rejects_route_forwarding_identity_gate_and_runtime_alias_overclaims(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "activationPreconditionsMet": True,
                    "betaNoticeSent": True,
                    "discordSent": True,
                    "publicReachabilityReady": True,
                    "requestCheckReady": True,
                    "requestPackReady": True,
                    "acceptedRuntimeEvidenceSufficient": True,
                    "identityPublicContractGateMissingAllowsPermissionsAdmin": True,
                    "identityPublicContractGateMissingAllowsPermissionQuery": True,
                    "routeAccepted": True,
                    "routeAcceptedAsPermissionsAdmin": True,
                    "routeBlockerBypassed": True,
                    "p0ProgressReady": True,
                    "liveOpsApprovalGranted": True,
                },
                "split_claims": [
                    {
                        "field": "identity_public_contract_gate_missing_allows_public_header",
                        "state": "ready",
                    },
                    {"field": "route_acceptance_ready", "state": "ready"},
                ],
                "claims": [
                    "accepted runtime evidence alone is sufficient for permissions/admin",
                    "identity_public_contract_gate_missing unlocks permissions/admin queries",
                    "public reachability is reachable so permissions/admin is ready",
                    "request checks passed make permission query public",
                    "route accepted as permissions/admin ready",
                    "route blocker bypasses are enabled",
                    "identity_public_contract_gate_missing remains blocked until promoted identity contract",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.activationPreconditionsMet",
            "$.aliases.betaNoticeSent",
            "$.aliases.discordSent",
            "$.aliases.publicReachabilityReady",
            "$.aliases.requestCheckReady",
            "$.aliases.requestPackReady",
            "$.aliases.acceptedRuntimeEvidenceSufficient",
            "$.aliases.identityPublicContractGateMissingAllowsPermissionsAdmin",
            "$.aliases.identityPublicContractGateMissingAllowsPermissionQuery",
            "$.aliases.routeAccepted",
            "$.aliases.routeAcceptedAsPermissionsAdmin",
            "$.aliases.routeBlockerBypassed",
            "$.aliases.p0ProgressReady",
            "$.aliases.liveOpsApprovalGranted",
            "$.split_claims[0]",
            "$.split_claims[1]",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(6):
            self.assertIn(("positive_public_surface_claim", f"$.claims[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.claims[6]"), reason_labels)

        certificate_blockers = [
            item
            for item in blockers
            if item["reason"] == "route_or_runtime_readiness_alias_missing_upstream_certificates"
        ]
        certificate_labels = {item["label"] for item in certificate_blockers}
        self.assertTrue(
            {
                "$.aliases.activationPreconditionsMet",
                "$.aliases.publicReachabilityReady",
                "$.aliases.requestCheckReady",
                "$.aliases.acceptedRuntimeEvidenceSufficient",
                "$.aliases.identityPublicContractGateMissingAllowsPermissionsAdmin",
                "$.aliases.routeAccepted",
                "$.aliases.routeAcceptedAsPermissionsAdmin",
                "$.split_claims[0]",
                "$.split_claims[1]",
                "$.claims[0]",
                "$.claims[1]",
                "$.claims[4]",
            }.issubset(certificate_labels)
        )
        for item in certificate_blockers:
            self.assertEqual(
                ["obelisk.player-identity-promotion-certificate.v1"],
                item["required_certificate_schemas"],
            )
            self.assertEqual(["obelisk.player_identity.v1"], item["blocked_behind_surfaces"])

    def test_rejects_nested_runtime_readiness_alias_values(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "publicRuntimeReady": {"state": {"ready": True}},
                    "runtimeReadinessAccepted": {"status": {"verified": "yes"}},
                    "identityPublicContractGateMissingAllowsPermissionsAdmin": {
                        "review": {"ready": True}
                    },
                },
                "split_claims": [
                    {
                        "field": "public_runtime_readiness_accepted",
                        "value": {"nested": {"status": "ready"}},
                    }
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.publicRuntimeReady",
            "$.aliases.runtimeReadinessAccepted",
            "$.aliases.identityPublicContractGateMissingAllowsPermissionsAdmin",
            "$.split_claims[0]",
        ):
            self.assertIn(
                ("route_or_runtime_readiness_alias_missing_upstream_certificates", label),
                paths,
            )
        self.assertIn(
            ("public_surface_overclaim", "$.aliases.identityPublicContractGateMissingAllowsPermissionsAdmin"),
            paths,
        )

    def test_rejects_next_action_passive_notice_status_public_readiness_shortcut_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "nextActionReady": True,
                    "next-action-ready": True,
                    "next_action": {"status": "ready"},
                    "next_actions": [{"status": "ready"}],
                    "machineNextActions": [{"status": "ready"}],
                    "passiveNextActionAccepted": True,
                    "passiveStatusReady": True,
                    "noticeNextActionReady": True,
                    "noticeStatusReady": True,
                    "statusReady": True,
                    "status_report": {"status": "ready"},
                    "publicReadinessNextActionReady": True,
                    "public-readiness-report": {"status": "ready"},
                    "public_readiness_status_ready": True,
                },
                "notes": [
                    "next action is ready",
                    "passive status is ready",
                    "notice status is ready",
                    "status report is accepted",
                    "public readiness is ready",
                    "next action remains blocked",
                    "public readiness remains blocked",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.nextActionReady",
            "$.aliases.next-action-ready",
            "$.aliases.next_action",
            "$.aliases.next_actions",
            "$.aliases.machineNextActions",
            "$.aliases.passiveNextActionAccepted",
            "$.aliases.passiveStatusReady",
            "$.aliases.noticeNextActionReady",
            "$.aliases.noticeStatusReady",
            "$.aliases.statusReady",
            "$.aliases.status_report",
            "$.aliases.publicReadinessNextActionReady",
            "$.aliases.public-readiness-report",
            "$.aliases.public_readiness_status_ready",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(5):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[5]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[6]"), reason_labels)

    def test_rejects_identity_public_contract_review_progress_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "identity_public_contract_decision_record_reviewed": True,
                    "identity_public_contract_decision_record_hash_current": True,
                    "identity_public_contract_decision_record_contract_review_only": True,
                    "reviewed_hash_current_contract_review_only": True,
                },
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.identity_public_contract_decision_record_reviewed",
            "$.aliases.identity_public_contract_decision_record_hash_current",
            "$.aliases.identity_public_contract_decision_record_contract_review_only",
            "$.aliases.reviewed_hash_current_contract_review_only",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)

    def test_rejects_scoped_release_statement_route_credit_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
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
                    "scoped release statements cannot unlock permissions/admin",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.scopedReleaseStatementReady",
            "$.aliases.scoped_release_statement_counts_toward_complete_sdk_claim",
            "$.aliases.scoped_release_statement_outcomes_satisfy_completion",
            "$.split_claims[0]",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        self.assertIn(("positive_public_surface_claim", "$.notes[0]"), reason_labels)
        self.assertIn(("positive_public_surface_claim", "$.notes[1]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[2]"), reason_labels)

    def test_rejects_package_shape_runtime_simulation_and_planning_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "acceptedRuntimeSimulationReady": True,
                "accepted_runtime_simulation": {"status": "accepted"},
                "activation_precondition_report": {"status": "ready"},
                "beta_notice_action_report": {"status": "accepted"},
                "bridgeClaimsAllowed": True,
                "bridge_report": {"progress": "1/4", "status": "ready"},
                "handoffNotesReady": True,
                "handoff_notes": {"status": "accepted"},
                "notice_action_report": {"status": "accepted"},
                "precondition_artifact": {"progress": "1/3"},
                "side_lane_artifact": {"progress": "1/4", "status": "ready"},
                "support_tier_report": {"status": "supported"},
                "supportTierReadinessReady": True,
                "supportTierPackageReady": True,
                "support_tier_package_shape": {"status": "supported"},
                "packageShapeAccepted": True,
                "public_contract_record_package": {"status": "accepted"},
                "request_pack_public_contract_record": {"status": "accepted"},
                "commandPlanningReady": True,
                "command_planning_package": {"status": "ready"},
                "command_response_planning_package": {"status": "ready"},
                "copied_intent_package_shape": {"status": "ready"},
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
                "source_provenance_reviewed_contract_metadata": {
                    "source_provenance": "reviewed_hash_current_contract_review_only",
                    "state": "reviewed",
                },
                "aliases": [
                    {"field": "bridge_report", "status": "ready"},
                    {"field": "support_tier_report", "status": "supported"},
                    {"field": "activation_precondition_report", "status": "ready"},
                    {"field": "notice_action_report", "status": "accepted"},
                    {"field": "support_tier_package_shape", "status": "supported"},
                    {"field": "accepted_runtime_simulation", "status": "accepted"},
                    {"field": "command_planning_package", "status": "ready"},
                    {"field": "route_snapshot", "status": "accepted"},
                ],
                "notes": [
                    "bridge report is ready",
                    "activation precondition report is ready",
                    "beta notice action report is accepted",
                    "support tier report is supported",
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
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.acceptedRuntimeSimulationReady",
            "$.accepted_runtime_simulation",
            "$.activation_precondition_report",
            "$.beta_notice_action_report",
            "$.bridgeClaimsAllowed",
            "$.bridge_report",
            "$.handoffNotesReady",
            "$.handoff_notes",
            "$.notice_action_report",
            "$.precondition_artifact.progress",
            "$.side_lane_artifact.progress",
            "$.support_tier_report",
            "$.supportTierReadinessReady",
            "$.supportTierPackageReady",
            "$.support_tier_package_shape",
            "$.packageShapeAccepted",
            "$.public_contract_record_package",
            "$.request_pack_public_contract_record",
            "$.commandPlanningReady",
            "$.command_planning_package",
            "$.command_response_planning_package",
            "$.copied_intent_package_shape",
            "$.route_snapshot",
            "$.source_marker",
            "$.source_status",
            "$.source_marker_pair",
            "$.source_marker_pair.status",
            "$.source_marker_list_pair",
            "$.source_marker_list_pair.source_state",
            "$.source_provenance_route_snapshot",
            "$.source_provenance_route_snapshot.status",
            "$.source_provenance_accepted_runtime",
            "$.source_provenance_accepted_runtime.source_status",
            "$.source_provenance_reviewed_contract_metadata.state",
            "$.aliases[0]",
            "$.aliases[1]",
            "$.aliases[2]",
            "$.aliases[3]",
            "$.aliases[4]",
            "$.aliases[5]",
            "$.aliases[6]",
            "$.aliases[7]",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(11):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[11]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[12]"), reason_labels)

    def test_rejects_copied_log_only_and_package_shape_install_shortcut_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "compactContextReady": True,
                    "compact_context": {"status": "accepted"},
                    "copiedLogOnlyReady": True,
                    "copied_obelisk_log": {"status": "accepted"},
                    "copied_log_artifact": {"status": "ready"},
                    "packageShapeInstallReady": True,
                    "packageShapeSupportReady": True,
                    "installedSdkPackageShape": {"status": "ready"},
                    "package_shape_install": {"status": "ready"},
                    "package_install": {"counts_toward_public_sdk": True},
                    "passiveSummaryReady": True,
                    "pluginHubPlanningReady": True,
                    "plugin_hub_planning": {"status": "supported"},
                },
                "split_claims": [
                    {"field": "compact_context", "status": "accepted"},
                    {"field": "copied_log_only_artifact", "status": "ready"},
                    {"field": "package_shape_install", "value": "ready"},
                    {"field": "plugin_hub_planning", "status": "supported"},
                ],
                "notes": [
                    "compact context is accepted for permissions/admin",
                    "copied-log-only artifact is ready",
                    "package-shape install success counts toward permissions/admin",
                    "package-shape support is ready",
                    "passive summary unlocks route readiness",
                    "Plugin Hub planning is supported",
                    "installed SDK package shape is supported",
                    "compact context remains blocked",
                    "copied-log-only artifacts remain blocked",
                    "package-shape install success remains blocked",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.compactContextReady",
            "$.aliases.compact_context",
            "$.aliases.copiedLogOnlyReady",
            "$.aliases.copied_obelisk_log",
            "$.aliases.copied_log_artifact",
            "$.aliases.packageShapeInstallReady",
            "$.aliases.packageShapeSupportReady",
            "$.aliases.installedSdkPackageShape",
            "$.aliases.package_shape_install",
            "$.aliases.package_install",
            "$.aliases.passiveSummaryReady",
            "$.aliases.pluginHubPlanningReady",
            "$.aliases.plugin_hub_planning",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(7):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[7]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[8]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[9]"), reason_labels)

    def test_rejects_downstream_route_shortcut_status_and_source_ready_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "identity_public_contract_gate_missing": {
                    "source_ready": True,
                    "ready": True,
                    "status": "ready",
                },
                "public_reachability_status": {"source_ready": True, "status": "reachable"},
                "rcon_status": {"source_ready": True, "status": "ready"},
                "kick": {"source_ready": True, "status": "ready"},
                "server_list_players": {"source_ready": True, "status": "ready"},
                "server_kick_player": {"source_ready": True, "status": "ready"},
                "static_admin_thunk": {"source_ready": True, "status": "ready"},
                "kickReady": True,
                "sourceReady": True,
                "broadcast_status": {"ready": True, "status": "enabled"},
                "package_support_plugin": {
                    "plugin_hub_support_ready": True,
                    "support_tier_ready": True,
                },
                "split_claims": [
                    {"field": "identity_public_contract_gate_missing", "source_ready": True},
                    {"field": "public_reachability", "ready": True},
                    {"field": "rcon_route", "status": "ready"},
                    {"field": "kick", "status": "ready"},
                    {"field": "server_list_players", "source_ready": True},
                    {"field": "server_kick_player", "status": "ready"},
                    {"field": "static_admin_thunk", "source_ready": True},
                    {"field": "broadcast_status", "status": "enabled"},
                    {"field": "package_shape_support", "source_ready": True},
                    {"field": "plugin_hub_package_shape", "ready": True},
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.identity_public_contract_gate_missing",
            "$.public_reachability_status",
            "$.rcon_status",
            "$.kick",
            "$.server_list_players",
            "$.server_kick_player",
            "$.static_admin_thunk",
            "$.kickReady",
            "$.sourceReady",
            "$.broadcast_status",
            "$.package_support_plugin.plugin_hub_support_ready",
            "$.package_support_plugin.support_tier_ready",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.split_claims[2]",
            "$.split_claims[3]",
            "$.split_claims[4]",
            "$.split_claims[5]",
            "$.split_claims[6]",
            "$.split_claims[7]",
            "$.split_claims[8]",
            "$.split_claims[9]",
        ):
            with self.subTest(label=label):
                self.assertIn(("public_surface_overclaim", label), reason_labels)
        for label in (
            "$.public_reachability_status.source_ready",
            "$.rcon_status.source_ready",
            "$.kick.source_ready",
            "$.split_claims[3]",
            "$.server_list_players.source_ready",
            "$.server_kick_player.status",
            "$.static_admin_thunk.source_ready",
            "$.split_claims[4].source_ready",
            "$.split_claims[6].source_ready",
            "$.split_claims[8].source_ready",
        ):
            with self.subTest(label=label):
                self.assertIn(("non_evidence_artifact_credit_overclaim", label), reason_labels)

    def test_rejects_generic_admin_source_status_route_and_command_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": [
                    {"source": "RCON", "status": "ready"},
                    {"source_marker": "RCON", "status": "accepted"},
                    {"route_candidate": {"source": "RCON", "status": "ready"}},
                    {"command": "ShooterPlayerController.ServerListPlayers", "status": "ready"},
                    {
                        "command_candidate": {
                            "target": "ShooterPlayerController.ServerKickPlayer",
                            "state": "supported",
                        }
                    },
                ],
                "principal_source": "ShooterPlayerController.ServerKickPlayer",
                "notes": [
                    "route candidate ready",
                    "command candidate ready",
                    "RCON source ready",
                    "RCON source remains blocked",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases[0].status",
            "$.aliases[1].status",
            "$.aliases[2].route_candidate",
            "$.aliases[2].route_candidate.status",
            "$.aliases[3].status",
            "$.aliases[4].command_candidate",
        ):
            with self.subTest(label=label):
                self.assertIn(("non_evidence_artifact_credit_overclaim", label), reason_labels)
        self.assertIn(
            ("pre_runtime_principal_or_authority_claim_source", "$.principal_source"),
            reason_labels,
        )
        for index in range(3):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), reason_labels)

    def test_non_evidence_artifact_inventory_strings_are_not_credit_but_structured_credit_is_rejected(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "non_evidence_artifacts": [
                    "next-action runner/planner artifacts",
                    "runtime status reports",
                    "package-shape/support-tier artifacts",
                    {"artifact_kind": "status_report", "status": "ready"},
                    {"artifact": "notice_status_artifact", "readiness": "ready"},
                    {"artifact_class": "package_shape", "counts_toward_public_sdk": True},
                ]
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.non_evidence_artifacts[0]",
            "$.non_evidence_artifacts[1]",
            "$.non_evidence_artifacts[2]",
        ):
            self.assertNotIn(("positive_public_surface_claim", label), reason_labels)
        for label in (
            "$.non_evidence_artifacts[3]",
            "$.non_evidence_artifacts[4]",
            "$.non_evidence_artifacts[5]",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), reason_labels)
        self.assertIn(
            ("public_surface_overclaim", "$.non_evidence_artifacts[5].counts_toward_public_sdk"),
            reason_labels,
        )

    def test_rejects_runtime_window_no_users_unblocked_and_identity_present_aliases(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "runtimeWindowPlanReady": True,
                    "runtime_window_artifact": {"status": "unblocked"},
                    "noUsersStatusReady": True,
                    "no_users_status": {"status": "allowed"},
                    "discordNoticeReady": True,
                    "packageInstallUnblocked": True,
                    "identityPresent": True,
                    "principalObserved": True,
                    "permissionsAdminUnblocked": True,
                },
                "split_claims": [
                    {"field": "identity_present", "status": "present"},
                    {"field": "runtime_window_plan", "status": "unblocked"},
                ],
                "source_marker_pair": {
                    "source_marker": "no_users_passive_wait",
                    "status": "allowed",
                },
                "notes": [
                    "runtime window plan is unblocked",
                    "no users status is allowed",
                    "identity present allowed permissions/admin",
                    "permissions/admin is unblocked",
                    "runtime window remains blocked",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.runtimeWindowPlanReady",
            "$.aliases.runtime_window_artifact",
            "$.aliases.noUsersStatusReady",
            "$.aliases.no_users_status",
            "$.aliases.discordNoticeReady",
            "$.aliases.packageInstallUnblocked",
            "$.aliases.identityPresent",
            "$.aliases.principalObserved",
            "$.aliases.permissionsAdminUnblocked",
            "$.split_claims[0]",
            "$.split_claims[1]",
            "$.source_marker_pair",
            "$.source_marker_pair.status",
        ):
            self.assertIn(("public_surface_overclaim", label), reason_labels)
        for index in range(4):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[4]"), reason_labels)

    def test_rejects_camel_hyphen_space_aliases_and_positive_readiness_texts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["alias_claims"] = {
                "publicReplyAbiReady": True,
                "public-response-path-ready": True,
                "routeReady": True,
                "public-route-ready": True,
                "permissionsAdminRouteReady": True,
                "send chat ready": True,
                "publicAbiReady": True,
                "runtimeReady": True,
                "permissions-admin-ready": True,
                "commandRouterAllowed": True,
                "publicBridgeAbiAllowed": True,
                "public response abi allowed": True,
                "authorityClaimSource": "command text",
                "principal-source": {"source": "operator-config"},
            }
            decisions["positive_claims"] = [
                "public ABI is ready",
                "route readiness is ready",
                "permissions/admin route is ready",
                "permissions/admin is public and ready",
                "reply endpoint is live",
                "command response path is live",
                "command response is unlocked",
                "commands replies are ready",
                "live ops authorized",
                "runtime capture is authorized",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("pre_runtime_principal_or_authority_claim_source", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])

    def test_rejects_scope_b_bare_aliases_as_permissions_admin_promotion_credit(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims(
            {
                "aliases": {
                    "ready": True,
                    "runtimeReady": True,
                    "approvedRuntimeEvidence": True,
                    "publicSdk": True,
                    "stableSdk": True,
                    "completeSdk": True,
                    "P0": True,
                    "supportTier": {"status": "supported"},
                    "PluginHub": {"status": "ready"},
                    "packageShape": {"status": "ready"},
                    "beta": {"status": "ready"},
                    "Discord": {"status": "sent"},
                    "passiveSnapshot": {"status": "ready"},
                    "scopedReleaseStatement": True,
                },
                "source_marker_pair": {
                    "source_marker": "beta",
                    "status": "ready",
                },
                "notes": [
                    "P0 is ready",
                    "beta is ready",
                    "Discord is sent",
                    "approved runtime evidence is ready",
                    "scoped release statement remains blocked",
                ],
            },
            blockers,
        )

        reason_labels = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.aliases.ready",
            "$.aliases.runtimeReady",
            "$.aliases.approvedRuntimeEvidence",
            "$.aliases.publicSdk",
            "$.aliases.stableSdk",
            "$.aliases.completeSdk",
            "$.aliases.P0",
            "$.aliases.supportTier",
            "$.aliases.PluginHub",
            "$.aliases.packageShape",
            "$.aliases.beta",
            "$.aliases.Discord",
            "$.aliases.passiveSnapshot",
            "$.aliases.scopedReleaseStatement",
            "$.source_marker_pair",
            "$.source_marker_pair.status",
        ):
            with self.subTest(label=label):
                self.assertTrue(
                    any(item["label"] == label for item in blockers),
                    reason_labels,
                )
        for index in range(4):
            self.assertIn(("positive_public_surface_claim", f"$.notes[{index}]"), reason_labels)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[4]"), reason_labels)

    def test_collect_overclaims_rejects_split_key_value_aliases(self) -> None:
        blockers: list[dict] = []
        READINESS.collect_overclaims(
            {
                "claims": [
                    {"key": "permissionsAdminReady", "value": True},
                    {"field": "public-route-ready", "state": "ready"},
                    {"claim": "identity_claim_source", "value": "runtime_lifecycle_evidence"},
                    {"name": "principal-source", "status": "operator-config"},
                    {"key": "permissionsAdminReady", "value": False},
                ]
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        self.assertIn(("public_surface_overclaim", "$.claims[0]"), paths)
        self.assertIn(("public_surface_overclaim", "$.claims[1]"), paths)
        self.assertIn(("pre_runtime_principal_or_authority_claim_source", "$.claims[2]"), paths)
        self.assertIn(("pre_runtime_principal_or_authority_claim_source", "$.claims[3]"), paths)
        self.assertNotIn(("public_surface_overclaim", "$.claims[4]"), paths)

    def test_rejects_non_evidence_artifact_metadata_credit(self) -> None:
        blockers: list[dict] = []
        READINESS.collect_overclaims(
            {
                "metadata": {
                    "package": {"artifact_class": "package_shape", "status": "ready"},
                    "beta": {"source_kind": "beta_notice", "counts_toward_runtime": True},
                    "passive": {"kind": "passive_monitor", "progress": "1/4"},
                    "no_users": {"artifact_type": "no-users status", "state": "supported"},
                    "diagnostic": {"report_kind": "diagnostic candidate", "readiness": "accepted"},
                    "non_evidence_artifacts": [
                        {"artifact_class": "passive_monitor", "status": False}
                    ],
                }
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.metadata.package.status",
            "$.metadata.beta.counts_toward_runtime",
            "$.metadata.passive.progress",
            "$.metadata.no_users.state",
            "$.metadata.diagnostic.readiness",
        ):
            self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertNotIn(
            ("non_evidence_artifact_credit_overclaim", "$.metadata.non_evidence_artifacts[0].status"),
            paths,
        )

    def test_rejects_query_diagnostics_standing_authority_and_runtime_placeholder_credit(self) -> None:
        blockers: list[dict] = []
        READINESS.collect_overclaims(
            {
                "query_only_diagnostics": {"status": "ready"},
                "post_identity_query_only_diagnostics": {"progress": "1/2"},
                "standingAuthorityReady": True,
                "standing_authority": {"status": "ready"},
                "authority_claim_source": "standing authority",
                "approved_runtime_evidence_placeholder": {"status": "ready"},
                "notes": [
                    "query-only diagnostics are ready",
                    "standing authority is ready",
                    "query-only diagnostics remain non-authorizing",
                    "standing authority remains non-authorizing",
                ],
            },
            blockers,
        )

        paths = {(item["reason"], item["label"]) for item in blockers}
        for label in (
            "$.query_only_diagnostics",
            "$.post_identity_query_only_diagnostics.progress",
            "$.standingAuthorityReady",
            "$.standing_authority",
            "$.approved_runtime_evidence_placeholder",
        ):
            with self.subTest(label=label):
                self.assertIn(("public_surface_overclaim", label), paths)
        for label in (
            "$.query_only_diagnostics.status",
            "$.standing_authority.status",
        ):
            with self.subTest(label=label):
                self.assertIn(("non_evidence_artifact_credit_overclaim", label), paths)
        self.assertIn(
            ("pre_runtime_principal_or_authority_claim_source", "$.authority_claim_source"),
            paths,
        )
        self.assertIn(("positive_public_surface_claim", "$.notes[0]"), paths)
        self.assertIn(("positive_public_surface_claim", "$.notes[1]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[2]"), paths)
        self.assertNotIn(("positive_public_surface_claim", "$.notes[3]"), paths)

    def test_non_evidence_non_authorizing_markers_do_not_create_readiness_credit(self) -> None:
        blockers: list[dict] = []
        READINESS.collect_overclaims(
            {
                "query_only_diagnostics": {
                    "diagnostic_only": True,
                    "non_evidence": True,
                    "non_authorizing": True,
                    "counts_toward_public_sdk": False,
                    "progress": 0,
                },
                "approved_runtime_evidence_placeholder": {
                    "diagnostic_only": True,
                    "non_evidence": True,
                    "non_authorizing": True,
                    "counts_toward_p0_dependency_chain_claim": False,
                    "progress": 0,
                },
                "package_shape": {
                    "diagnostic_only": True,
                    "non_evidence": True,
                    "non_authorizing": True,
                    "counts_toward_public_sdk": False,
                    "progress": 0,
                },
                "beta_notice_action_report": {
                    "diagnostic_only": True,
                    "non_evidence": True,
                    "non_authorizing": True,
                    "counts_toward_runtime": False,
                    "progress": 0,
                },
            },
            blockers,
        )

        self.assertEqual([], blockers)

    def test_rejects_surface_promoted_before_player_identity_or_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.permissions_admin.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = ["ObeliskPermissionQuery"]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_admin_surface_status_unexpected", report["blockers"])
        self.assertIn("permissions_admin_public_contract_not_empty", report["blockers"])
        self.assertIn("permissions_admin_promoted_before_player_identity", report["blockers"])

    def test_rejects_top_level_permissions_admin_promotion_and_sequence_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            surfaces["promoted_surfaces"].append("obelisk.permissions_admin.v1")
            surfaces["planning_surfaces"] = [
                item for item in surfaces["planning_surfaces"] if item != "obelisk.permissions_admin.v1"
            ]
            surfaces["v1_completion_required"] = True
            surfaces["v1_required_dependency_chain"] = [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.commands_replies.v1",
            ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_admin_listed_as_promoted", report["blockers"])
        self.assertIn("permissions_admin_missing_from_planning_surfaces", report["blockers"])
        self.assertIn("v1_completion_required_not_false", report["blockers"])
        self.assertIn("v1_required_dependency_chain_mismatch", report["blockers"])

    def test_rejects_permissions_admin_manifest_status_and_alias_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            permissions = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.permissions_admin.v1"
            )
            permissions["public_abi"] = True
            permissions["complete_sdk_counting_allowed"] = True
            permissions["public_ready_aliases"]["public_ready"] = True
            query_only = permissions["v1_decision_contract"]["permissions_admin_query_only_planning"]
            query_only["status"] = "promoted"
            query_only["public_contract_allowed"] = True
            query_only["complete_sdk_counting_allowed"] = True
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_admin_public_abi_not_false", report["blockers"])
        self.assertIn("permissions_admin_complete_sdk_counting_allowed_not_false", report["blockers"])
        self.assertIn("permissions_admin_public_ready_alias_not_false", report["blockers"])
        self.assertIn("permissions_admin_query_only_planning_status_unexpected", report["blockers"])
        self.assertIn("permissions_admin_query_only_planning_public_contract_allowed_not_false", report["blockers"])
        self.assertIn(
            "permissions_admin_query_only_planning_complete_sdk_counting_allowed_not_false",
            report["blockers"],
        )

    def test_rejects_permissions_admin_future_promotion_requirement_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            permissions = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.permissions_admin.v1"
            )
            decision_contract = permissions["v1_decision_contract"]
            decision_contract["not_sufficient_evidence"].remove(
                "candidate-only permissions/admin query fail-closed contract"
            )
            decision_contract["promotion_requires"] = [
                item
                for item in decision_contract["promotion_requires"]
                if not item.startswith("matching player-identity promotion certificate")
            ]
            query_only = decision_contract["permissions_admin_query_only_planning"]
            query_only["required_policy"].remove(
                "permissions/admin remains query-only planning until obelisk.player_identity.v1 is promoted"
            )
            query_only["forbidden_until_separate_promotion"].remove("replies/send-chat")
            query_only["non_counting_artifacts"].remove(
                "missing, mismatched, stale, or hash-unbound promotion certificates"
            )
            query_only["required_identity_promotion_certificate"]["promotion_status"] = "planning"
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("permissions_admin_not_sufficient_evidence_missing", report["blockers"])
        self.assertIn("permissions_admin_promotion_requirements_missing", report["blockers"])
        self.assertIn("permissions_admin_query_only_policy_missing", report["blockers"])
        self.assertIn("permissions_admin_query_only_forbidden_exclusions_missing", report["blockers"])
        self.assertIn("permissions_admin_non_counting_artifacts_missing", report["blockers"])
        self.assertIn("permissions_admin_required_identity_promotion_certificate_mismatch", report["blockers"])

    def test_rejects_manifest_only_player_identity_promotion_as_upstream_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])

    def test_rejects_missing_player_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            surfaces["surfaces"] = [
                surface for surface in surfaces["surfaces"] if surface["id"] != "obelisk.player_identity.v1"
            ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_surface_missing", report["blockers"])

    def test_rejects_text_only_player_identity_runtime_evidence_spoof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["evidence"]["notes"] = [
                        "approved runtime principal lifecycle evidence",
                        "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "identity_public_contract_gate_missing",
                    ]
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])

    def test_rejects_passive_player_identity_runtime_evidence_as_route_unlock(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"]["accepted_runtime_evidence"]["source_kind"] = "passive-monitor-snapshot"
            identity_surface["evidence"]["accepted_runtime_evidence"]["source_path"] = (
                "docs/research/player-identity-planning-sources/passive-snapshot.json"
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_runtime_evidence_non_promotion_artifact_source", report["blockers"])
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_promoted_player_identity_with_only_runtime_evidence_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["evidence"]["accepted_runtime_evidence"] = minimal_accepted_runtime_evidence_record()
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_accepted_runtime_evidence_not_canonical", report["blockers"])
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_player_identity_runtime_evidence_readiness_overclaim_as_upstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": "identity_public_contract_gate_missing",
                        "promotion_ready": True,
                        "public_sdk_ready": True,
                        "runtime_ready": True,
                    }
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertGreaterEqual(report["blockers"].count("public_surface_overclaim"), 2)
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_promoted_player_identity_without_owner_token_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEvent",
                        "UnregisterPlayerPrincipalEvent",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = ["plugin-owner cleanup"]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_rejects_promoted_player_identity_without_owner_token_cleanup_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = ["plugin-owner cleanup"]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_accepts_promoted_player_identity_only_with_public_contract_promotion(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = None
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
                    identity_surface = surface
            assert identity_surface is not None
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            decisions_path = write_decisions_with_route_blocker(root, "public_header_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "public_header_gate_missing",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertNotIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertEqual("public_header_gate_missing", report["current_route_blocker"])
        self.assertEqual(["public_header_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertEqual("public_header_gate_missing", report["next_steps"]["route_blocker_to_use"])
        self.assertTrue(report["next_steps"]["identity_runtime_artifact_observed"])
        self.assertTrue(report["next_steps"]["identity_contract_certificate_observed"])
        self.assertEqual([], report["missing_identity_inputs"])
        self.assertEqual([], report["next_steps"]["missing_identity_inputs"])
        self.assertTrue(report["identity_input_diagnostics"]["accepted_runtime_evidence_observed"])
        self.assertTrue(report["identity_input_diagnostics"]["identity_public_contract_certificate_observed"])
        self.assertFalse(report["identity_input_diagnostics"]["counts_toward_permissions_admin"])
        self.assertFalse(report["identity_input_diagnostics"]["permissions_admin_unlock_allowed"])
        self.assertEqual(
            ["resolve_permissions_admin_query_public_header_gate"],
            [step["id"] for step in report["next_steps"]["steps"]],
        )
        post_identity = report["post_identity_next_requirement"]
        self.assertEqual("resolve_permissions_admin_query_public_header_gate", post_identity["id"])
        self.assertEqual("public_header_gate_missing", post_identity["route_blocker_to_use"])
        self.assertIn("plugin_owner_token", post_identity["required_query_fields"])
        self.assertIn("request_flags", post_identity["required_query_fields"])
        self.assertIn("server_process_epoch", post_identity["required_query_fields"])
        self.assertEqual(
            "reviewed_identity_public_contract_decision_record",
            post_identity["required_identity_public_contract_review"]["id"],
        )
        self.assertEqual(
            "hash_bound_player_identity_promotion_certificate",
            post_identity["required_identity_promotion_certificate"]["id"],
        )
        self.assertFalse(post_identity["identity_alias_or_stale_source_unlock_allowed"])
        self.assertFalse(post_identity["runtime_evidence_alone_unlock_allowed"])
        self.assertEqual(
            post_identity["shortcut_artifacts_never_count"],
            report["next_steps"]["steps"][0]["forbidden_shortcuts"],
        )
        diagnostics = report["post_identity_query_only_diagnostics"]
        self.assertEqual(diagnostics, report["next_steps"]["post_identity_query_only_diagnostics"])
        self.assertTrue(diagnostics["diagnostic_only"])
        self.assertTrue(diagnostics["non_evidence"])
        self.assertTrue(diagnostics["non_authorizing"])
        self.assertTrue(diagnostics["identity_public_contract_promoted"])
        self.assertEqual("post_identity_public_header_gate", diagnostics["stage"])
        self.assertEqual("public_header_gate_missing", diagnostics["route_blocker_to_use"])
        self.assertFalse(diagnostics["next_gate"]["requires_promoted_identity_first"])
        self.assertTrue(diagnostics["next_gate"]["requires_public_header_review"])
        for key in READINESS.QUERY_ONLY_DIAGNOSTIC_FALSE_KEYS:
            self.assertFalse(diagnostics[key])
        for key in READINESS.QUERY_ONLY_DIAGNOSTIC_ZERO_KEYS:
            self.assertEqual(0, diagnostics[key])
        self.assertFalse(report["next_steps"]["steps"][0]["public_header_allowed"])
        self.assertFalse(report["next_steps"]["steps"][0]["runtime_ready"])
        self.assertFalse(report["next_steps"]["steps"][0]["stable_claim_allowed"])

    def test_rejects_stale_runtime_route_after_identity_contract_review_passes(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "current_route_blocker_stale_after_identity_public_contract_review",
            report["blockers"],
        )
        self.assertIn(
            "accounting_lock_route_blocker_stale_after_identity_public_contract_review",
            report["blockers"],
        )
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_certificate_without_identity_public_contract_review_record(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["evidence"].pop("identity_public_contract_decision_record")
            certificate["evidence"]["semantic_proofs"].remove(
                "reviewed_identity_public_contract_decision_record"
            )
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(certificate_path)
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_identity_contract_review_missing", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_semantic_proofs_missing", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_stale_player_identity_promotion_certificate_surface_hash(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = None
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
                    identity_surface = surface
            assert identity_surface is not None
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            identity_surface["support_tier"] = "release-supported copied principal after certificate"
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_reviewed_surface_record_hash_mismatch", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_rejects_placeholder_player_identity_promotion_certificate_artifact_hash(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = None
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
                    identity_surface = surface
            assert identity_surface is not None
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(
                    root,
                    identity_surface,
                    reviewed_artifact_hash="0" * 64,
                )
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_reviewed_artifact_hash_invalid", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_rejects_mismatched_player_identity_promotion_certificate_artifact_hash(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = None
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
                    identity_surface = surface
            assert identity_surface is not None
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(
                    root,
                    identity_surface,
                    reviewed_artifact_hash="1" * 64,
                )
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_reviewed_artifact_hash_unbound", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_stale_player_identity_promotion_certificate_file_hash(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"]["sha256"] = "f" * 64
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_artifact_hash_mismatch", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_player_identity_promotion_certificate_symlink_artifact(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            link = root / "player-identity-promotion-certificate-link.json"
            link.symlink_to(certificate_path)
            identity_surface["evidence"]["player_identity_promotion_certificate"] = {
                "path": str(link.relative_to(REPO_ROOT)),
                "sha256": binding["sha256"],
            }
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_path_rejected", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_player_identity_promotion_certificate_chain_position_drift(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["v1_dependency_chain"] = [
                "obelisk.permissions_admin.v1",
                "obelisk.player_identity.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ]
            certificate["v1_dependency_chain_position"] = 2
            certificate["required_by_v1_dependency_chain_position"] = 1
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(certificate_path)
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_dependency_chain_mismatch", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_chain_position_mismatch", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_required_by_chain_position_mismatch", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_player_identity_promotion_certificate_chain_position_alias_drift(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["chain_position"] = 2
            certificate["required_by_chain_position"] = 1
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(certificate_path)
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_chain_position_alias_mismatch", report["blockers"])
        self.assertIn(
            "player_identity_promotion_certificate_required_by_chain_position_alias_mismatch",
            report["blockers"],
        )
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_player_identity_promotion_certificate_binding_policy_drift(self) -> None:
        cases = (
            (
                "missing_reviewed_artifact_hash_pointer",
                lambda certificate: certificate.pop("required_reviewed_artifact_hash", None),
            ),
            (
                "weakened_reviewed_artifact_hash_policy",
                lambda certificate: certificate.update(
                    {"reviewed_artifact_hash_policy": "any reviewed identity artifact is accepted"}
                ),
            ),
            (
                "stale_certificate_counts",
                lambda certificate: certificate.update({"missing_mismatched_or_stale_certificate_counts": True}),
            ),
        )
        for name, mutate in cases:
            with self.subTest(name=name), self.permissions_admin_identity_tempdir() as root:
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
                identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                    bind_mutated_identity_certificate(root, identity_surface, mutate)
                )
                decisions_path = write_decisions_with_route_blocker(root, "public_header_gate_missing")
                surfaces_path = write_json(root, "surfaces.json", surfaces)

                result = run_checker(
                    "--decisions",
                    str(decisions_path),
                    "--surfaces",
                    str(surfaces_path),
                    "--current-route-blocker",
                    "public_header_gate_missing",
                    check=False,
                )
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "player_identity_promotion_certificate_binding_policy_mismatch",
                report["blockers"],
            )
            self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
            self.assertEqual("public_header_gate_missing", report["current_route_blocker"])
            self.assertEqual(["public_header_gate_missing"], report["remaining_route_blockers"])
            self.assertFalse(report["route_ready"])
            self.assertFalse(report["permissions_admin_route_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_identity_ready_aliases_as_promotion_certificate_substitute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["public_ready_aliases"] = {
                "public_contract_ready": True,
                "promotion_certificate_ready": True,
            }
            identity_surface["evidence"].pop("player_identity_promotion_certificate", None)
            identity_surface["evidence"]["player_identity_promotion_certificate_ready"] = True
            identity_surface["evidence"]["notes"] = [
                "promotion certificate is promoted",
                "player identity public contract is ready",
            ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_missing", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_identity_contract_route_blocker_and_runtime_evidence_stay_locked_without_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"].pop("player_identity_promotion_certificate", None)
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_missing", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertNotIn("current_route_blocker_mismatch", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_runtime_evidence_context_reaches_identity_gate_but_stays_non_counting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces_path = write_json(root, "surfaces.json", surfaces_with_accepted_runtime_evidence())
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertTrue(report["valid"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertTrue(report["dependency_chain_locked"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])
        self.assertEqual("identity_public_contract_gate_missing", report["next_steps"]["route_blocker_to_use"])
        self.assertTrue(report["next_steps"]["identity_runtime_artifact_observed"])
        self.assertFalse(report["next_steps"]["identity_contract_certificate_observed"])
        self.assertEqual(report["missing_identity_inputs"], report["next_steps"]["missing_identity_inputs"])
        self.assertEqual(
            [
                "reviewed_identity_public_contract_decision_record",
                "hash_bound_player_identity_promotion_certificate",
            ],
            [item["id"] for item in report["missing_identity_inputs"]],
        )
        self.assertTrue(report["identity_input_diagnostics"]["accepted_runtime_evidence_observed"])
        self.assertFalse(report["identity_input_diagnostics"]["identity_public_contract_certificate_observed"])
        self.assertEqual(
            "obelisk.player-identity-public-contract-decision-record.v1",
            report["missing_identity_inputs"][0]["required_schema"],
        )
        self.assertEqual(
            "obelisk.player-identity-promotion-certificate.v1",
            report["missing_identity_inputs"][1]["required_schema"],
        )
        for item in report["missing_identity_inputs"]:
            self.assertFalse(item["counts_toward_permissions_admin"])
            self.assertFalse(item["permissions_admin_unlock_allowed"])
        self.assertEqual(
            [
                "review_identity_public_contract_decision_record",
                "issue_hash_bound_player_identity_promotion_certificate",
                "rerun_permissions_admin_public_readiness_with_public_header_route_blocker",
            ],
            [step["id"] for step in report["next_steps"]["steps"]],
        )
        self.assertEqual(
            "obelisk.player-identity-public-contract-decision-record.v1",
            report["next_steps"]["steps"][0]["required_schema"],
        )
        self.assertEqual(
            "obelisk.player-identity-promotion-certificate.v1",
            report["next_steps"]["steps"][1]["required_schema"],
        )
        self.assertEqual(
            [
                "python3",
                "scripts/check_permissions_admin_public_readiness.py",
                "--json",
                "--current-route-blocker",
                "public_header_gate_missing",
            ],
            report["next_steps"]["steps"][2]["command"],
        )

    def test_runtime_evidence_identity_parent_lock_rejects_remaining_route_unlocks(self) -> None:
        cases = (
            (
                "empty_remaining",
                [],
                ["accounting_lock_remaining_route_blockers_unlock_attempt"],
            ),
            (
                "unknown_child_remaining",
                [
                    "identity_public_contract_gate_missing",
                    "commands_replies_public_contract_gate_missing",
                ],
                [
                    "accounting_lock_remaining_route_blocker_unknown",
                    "accounting_lock_remaining_route_blockers_not_parent_lock_only",
                ],
            ),
            (
                "missing_current_lock",
                ["public_header_gate_missing"],
                [
                    "accounting_lock_remaining_route_blockers_missing_current_lock",
                    "accounting_lock_remaining_route_blocker_before_identity_public_contract_review",
                ],
            ),
        )
        for name, remaining_route_blockers, expected_blockers in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                surfaces_path = write_json(root, "surfaces.json", surfaces_with_accepted_runtime_evidence())
                decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
                decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
                decisions["accounting_lock"]["remaining_route_blockers"] = remaining_route_blockers
                decisions_path = write_json(root, "decisions.json", decisions)

                result = run_checker(
                    "--decisions",
                    str(decisions_path),
                    "--surfaces",
                    str(surfaces_path),
                    "--current-route-blocker",
                    "identity_public_contract_gate_missing",
                    check=False,
                )
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            for blocker in expected_blockers:
                self.assertIn(blocker, report["blockers"])
            self.assertNotIn("current_route_blocker_out_of_order", report["blockers"])
            self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
            self.assertFalse(report["route_ready"])
            self.assertFalse(report["public_route_ready"])
            self.assertFalse(report["permissions_admin_route_ready"])
            self.assertFalse(report["counts_toward_public_sdk"])
            self.assertFalse(report["counts_toward_runtime"])
            self.assertFalse(report["counts_toward_v1_completion"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_runtime_evidence_identity_parent_lock_rejects_permissions_admin_unlock_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces_path = write_json(root, "surfaces.json", surfaces_with_accepted_runtime_evidence())
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions["accounting_lock"]["permissions_admin_route_ready"] = True
            decisions["accounting_lock"]["permissions_unlocked"] = True
            decisions["accounting_lock"]["public_or_runtime_accounting_allowed"] = True
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("accounting_lock_public_or_runtime_accounting_allowed_not_false", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertNotIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_admin_source_candidates_stay_non_counting_at_identity_contract_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces_path = write_json(root, "surfaces.json", surfaces_with_accepted_runtime_evidence())
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["accounting_lock"]["current_route_blocker"] = "identity_public_contract_gate_missing"
            decisions["accounting_lock"]["remaining_route_blockers"] = [
                "identity_public_contract_gate_missing"
            ]
            decisions["admin_source_candidates"] = {
                "rcon_status": {"source_ready": True, "status": "ready"},
                "server_list_players": {"source_ready": True, "status": "ready"},
                "server_kick_player": {"source_ready": True, "status": "ready"},
                "static_admin_thunk": {"source_ready": True, "status": "ready"},
                "listPlayersReady": True,
                "sourceReady": True,
            }
            decisions["admin_source_candidate_notes"] = [
                "RCON route ready does not replace the player identity contract",
                "ListPlayers source-ready unlocks nothing before identity acceptance",
                "static admin thunk ready remains non-counting",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertNotIn("current_route_blocker_out_of_order", report["blockers"])
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(["identity_public_contract_gate_missing"], report["remaining_route_blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_route_ready"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_runtime"])
        self.assertFalse(report["counts_toward_v1_completion"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["p0_progress_ready"])
        self.assertFalse(report["sdk_p0_progress_ready"])
        self.assertEqual(0, report["complete_sdk_claim_progress_contribution"])
        self.assertEqual(0, report["p0_dependency_chain_claim_progress_contribution"])
        self.assertFalse(report["public_or_runtime_accounting_allowed"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_runtime_evidence_artifact_as_identity_promotion_certificate_substitute(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            runtime_artifact = write_json(
                root,
                "runtime-evidence-shortcut.json",
                {
                    "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                    "result": "approved runtime principal lifecycle evidence",
                    "next_blocker": "identity_public_contract_gate_missing",
                    "runtime_ready": True,
                    "status": "approved",
                },
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(runtime_artifact)
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_runtime_evidence_substitute", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_generic_positive_alias", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_identity_decision_record_as_promotion_certificate_substitute(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            decision_record = write_json(
                root,
                "identity-decision-record-shortcut.json",
                {
                    "schema": "obelisk.player-identity-public-contract-decision-record.v1",
                    "artifact_id": "reviewed_identity_public_contract_decision_record",
                    "surface": "obelisk.player_identity.v1",
                    "active_after_resolved_input": "runtime.lifecycle_evidence",
                    "review_status": "reviewed",
                    "accepted_for_contract_review": True,
                    "next_blocker": "public_header_gate_missing",
                    "hash_current_identity_public_contract_decision_record": True,
                },
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(decision_record)
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_decision_record_substitute", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_generic_positive_alias", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_reviewed_template_as_promotion_certificate_substitute(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            template_artifact = write_json(
                root,
                "identity-decision-record-template-shortcut.json",
                {
                    "schema": "obelisk.player-identity-public-contract-decision-record-template.v1",
                    "artifact_id": "reviewed_identity_public_contract_decision_record",
                    "surface": "obelisk.player_identity.v1",
                    "review_status": "reviewed",
                    "reviewed_template_only": True,
                    "accepted_for_contract_review": True,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                },
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_json_artifact(template_artifact)
            )
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_decision_record_template", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_reviewed_template_only", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_generated_certificate_build_report_as_promotion_certificate_substitute(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            build_report = write_json(
                root,
                "player-identity-certificate-build-report.json",
                {
                    "schema": "obelisk.player-identity-promotion-certificate-build-report.v1",
                    "status": "built",
                    "certificate_artifact_schema": "obelisk.player-identity-promotion-certificate.v1",
                    "identity_surface_certificate_binding_valid": True,
                    "ready": False,
                    "promotion_ready": False,
                    "public_header_allowed": False,
                    "public_sdk_ready": False,
                    "runtime_ready": False,
                    "sdk_progress": 0,
                    "p0_progress": 0,
                },
            )
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(build_report)
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_build_report_not_certificate", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_passive_snapshot_and_executor_closure_reports_as_certificate_shortcuts(self) -> None:
        cases = (
            (
                "passive_snapshot",
                {
                    "schema": "obelisk.player-principal-passive-snapshot.v1",
                    "source_kind": "passive_monitor_snapshot",
                    "status": "ready",
                },
                "player_identity_promotion_certificate_passive_monitor_snapshot",
            ),
            (
                "executor_closure",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-window-executor-closure.v1",
                    "source_kind": "runtime_window_executor_closure",
                    "ready": True,
                    "closureComplete": True,
                },
                "player_identity_promotion_certificate_closure_or_executor_report",
            ),
            (
                "runtime_window_plan",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-window-plan.v1",
                    "source_kind": "runtime_window_plan",
                    "runtimeWindowPlanReady": True,
                    "status": "unblocked",
                },
                "player_identity_promotion_certificate_runtime_window_artifact",
            ),
            (
                "no_users_status",
                {
                    "schema": "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1",
                    "source_kind": "no_users_passive_wait",
                    "status": "no_users_passive_wait_recommended",
                    "noUsersStatusReady": True,
                },
                "player_identity_promotion_certificate_no_users_status",
            ),
            (
                "copied_log_only",
                {
                    "schema": "obelisk.player-principal-lifecycle-ready-log-copy.v1",
                    "source_kind": "copied_log_only_artifact",
                    "copy_readiness": {"copied_log_only": True},
                    "status": "ready",
                },
                "player_identity_promotion_certificate_copied_log_only_artifact",
            ),
            (
                "package_shape_install",
                {
                    "schema": "obelisk.installed-sdk-package-shape.v1",
                    "source_kind": "package_shape_install",
                    "install": {"status": "success"},
                    "ready": True,
                },
                "player_identity_promotion_certificate_package_shape_install",
            ),
        )
        for name, artifact, expected_reason in cases:
            with self.subTest(name=name), self.permissions_admin_identity_tempdir() as root:
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

                def mutate(certificate: dict) -> None:
                    certificate["evidence"][name] = artifact

                identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                    bind_mutated_identity_certificate(root, identity_surface, mutate)
                )
                surfaces_path = write_json(root, "surfaces.json", surfaces)

                result = run_checker("--surfaces", str(surfaces_path), check=False)
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertIn(expected_reason, report["blockers"])
            self.assertIn("player_identity_promotion_certificate_non_promotion_artifact_source", report["blockers"])
            self.assertIn("player_identity_promotion_certificate_generic_positive_alias", report["blockers"])
            self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_next_action_status_and_public_readiness_artifacts_as_certificate_shortcuts(self) -> None:
        cases = (
            (
                "next_action_plan",
                {
                    "schema": "obelisk.player-principal-lifecycle-next-action-plan.v1",
                    "status": "next_actions_planned",
                    "next_action_sequence": [{"id": "run_runtime_window", "ready": True}],
                },
                "player_identity_promotion_certificate_next_action_shortcut",
            ),
            (
                "status_report",
                {
                    "schema": "obelisk.player-principal-lifecycle-runtime-evidence-status.v1",
                    "status": "ready",
                    "public_readiness_ready": True,
                },
                "player_identity_promotion_certificate_status_report",
            ),
            (
                "public_readiness_report",
                {
                    "schema": "obelisk.permissions-admin-public-readiness-check.v1",
                    "valid": True,
                    "next_steps": {
                        "schema": "obelisk.permissions-admin-public-next-steps.v1",
                        "public_readiness_status_ready": True,
                    },
                },
                "player_identity_promotion_certificate_public_readiness_report",
            ),
        )
        for name, artifact, expected_reason in cases:
            with self.subTest(name=name), self.permissions_admin_identity_tempdir() as root:
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
                artifact_path = write_json(root, f"{name}.json", artifact)
                identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                    bind_json_artifact(artifact_path)
                )
                surfaces_path = write_json(root, "surfaces.json", surfaces)

                result = run_checker("--surfaces", str(surfaces_path), check=False)
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertIn(expected_reason, report["blockers"])
            self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_activation_precondition_report_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["activation_preconditions"] = {
                    "schema": "obelisk.player-principal-lifecycle-activation-preconditions.v1",
                    "ready": True,
                    "activation_preconditions_met": True,
                    "ready_scope": "offline_pre_activation_consistency_only",
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_activation_precondition_report", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_notice_send_attestation_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["notice_report"] = {
                    "schema": "obelisk.player-principal-lifecycle-beta-notice-prep.v1",
                    "mode": "confirmed_send",
                    "ready": True,
                    "discord_sent": True,
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_notice_send_attestation", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_request_check_readiness_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["request_check"] = {
                    "schema": "obelisk.player-principal-lifecycle-window-request-check.v1",
                    "ready": True,
                    "request_pack_ready": True,
                    "operator_approval_receipt_verified": True,
                    "current_turn_approval_recorded": True,
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_request_check_readiness_report", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_stale_identity_contract_review_record_binding_inside_certificate(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                review = certificate["evidence"]["identity_public_contract_decision_record"]
                review["reviewed_surface_record_sha256"] = "1" * 64
                certificate["evidence"]["identity_public_contract_decision_record_sha256"] = (
                    READINESS.canonical_json_sha256(review)
                )

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "player_identity_promotion_certificate_identity_contract_review_surface_hash_mismatch",
            report["blockers"],
        )
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_template_only_identity_contract_review_record_inside_certificate(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                review = certificate["evidence"]["identity_public_contract_decision_record"]
                review["reviewed_template_only"] = True
                certificate["evidence"]["identity_public_contract_decision_record_sha256"] = (
                    READINESS.canonical_json_sha256(review)
                )

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_reviewed_template_only", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_partial_identity_contract_review_record_inside_certificate(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                review = certificate["evidence"]["identity_public_contract_decision_record"]
                review["complete_identity_public_contract_reviewed"] = False
                review["partial_identity_contract"] = True
                review["hash_current_identity_public_contract_decision_record"] = True
                certificate["evidence"]["identity_public_contract_decision_record_sha256"] = (
                    READINESS.canonical_json_sha256(review)
                )

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_partial_identity_contract", report["blockers"])
        self.assertIn(
            "player_identity_promotion_certificate_identity_contract_review_completeness_mismatch",
            report["blockers"],
        )
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_scoped_release_statement_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["scoped_release_statement"] = {
                    "schema": "obelisk.scoped-release-statement-outcomes.v1",
                    "scoped_release_statement_counts_toward_complete_sdk_claim": False,
                    "counts_toward_p0_dependency_chain_claim": False,
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_scoped_release_statement", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_copied_admin_target_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["copied_admin_target"] = {
                    "source_kind": "copied_admin_target",
                    "target": "ShooterPlayerController.ServerKickPlayer",
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_copied_admin_target", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_non_promotion_artifact_source", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_route_alias_overclaim_as_identity_promotion_certificate_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)

            def mutate(certificate: dict) -> None:
                certificate["evidence"]["route_blocker_aliases"] = {
                    "identityPublicContractGateMissingAfterRuntimeEvidence": True,
                    "publicHeaderGateMissingAfterRuntimeEvidence": False,
                }

            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                bind_mutated_identity_certificate(root, identity_surface, mutate)
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_route_alias_overclaim", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_identity_gate_support_tier_package_shape_alias_after_runtime_evidence(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = surfaces_with_accepted_runtime_evidence()
            identity_surface = next(
                surface
                for surface in surfaces["surfaces"]
                if surface["id"] == "obelisk.player_identity.v1"
            )
            identity_surface["support_tier"] = (
                "identity_public_contract_gate_missing package-shape support ready "
                "unlocks permissions/admin"
            )
            identity_surface["support_tier_metadata"] = {
                "package_shape_support": "supported and ready",
            }
            decisions_path = write_decisions_with_route_blocker(root, "identity_public_contract_gate_missing")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--current-route-blocker",
                "identity_public_contract_gate_missing",
                check=False,
            )
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("route_or_runtime_readiness_alias_missing_upstream_certificates", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertIn("non_evidence_artifact_credit_overclaim", report["blockers"])
        support_tier_labels = [
            detail["label"]
            for detail in report["blocker_details"]
            if detail["reason"] == "non_evidence_artifact_credit_overclaim"
        ]
        self.assertTrue(
            any(label.endswith(".support_tier_metadata") for label in support_tier_labels),
            support_tier_labels,
        )
        self.assertEqual("identity_public_contract_gate_missing", report["current_route_blocker"])
        self.assertEqual(
            [
                "reviewed_identity_public_contract_decision_record",
                "hash_bound_player_identity_promotion_certificate",
            ],
            [item["id"] for item in report["missing_identity_inputs"]],
        )
        self.assertFalse(report["accepted_for_planning"])
        self.assertFalse(report["counts_toward_public_sdk"])
        self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
        self.assertFalse(report["permissions_admin_route_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_terminal_beta_runtime_status_and_support_metadata_inside_identity_certificate(self) -> None:
        cases = (
            (
                "support_tier_metadata",
                lambda certificate: certificate.update(
                    {
                        "support_tier": (
                            "support-tier package-shape ready unlocks permissions/admin "
                            "at identity_public_contract_gate_missing"
                        )
                    }
                ),
                "player_identity_promotion_certificate_support_tier_metadata",
            ),
            (
                "terminal_certificate",
                lambda certificate: certificate.update(
                    {
                        "terminal_certificate": {
                            "schema": "obelisk.player-identity-terminal-certificate.v1",
                            "status": "complete",
                            "route_ready": True,
                        }
                    }
                ),
                "player_identity_promotion_certificate_terminal_certificate",
            ),
            (
                "beta_notice_artifact",
                lambda certificate: certificate["evidence"].update(
                    {
                        "beta_notice_artifact": {
                            "schema": "obelisk.player-principal-lifecycle-beta-notice-artifact.v1",
                            "status": "sent",
                            "discord_sent": True,
                        }
                    }
                ),
                "player_identity_promotion_certificate_notice_send_attestation",
            ),
            (
                "runtime_evidence_status_report",
                lambda certificate: certificate["evidence"].update(
                    {
                        "runtime_evidence_status_report": {
                            "schema": READINESS.PLAYER_PRINCIPAL_LIFECYCLE_RUNTIME_EVIDENCE_STATUS_SCHEMA,
                            "status": "ready",
                            "identity_public_contract_gate_missing_allows_permissions_admin": True,
                        }
                    }
                ),
                "player_identity_promotion_certificate_status_report",
            ),
        )
        for name, mutator, expected_reason in cases:
            with self.subTest(name=name), self.permissions_admin_identity_tempdir() as root:
                surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
                identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
                identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                    bind_mutated_identity_certificate(root, identity_surface, mutator)
                )
                surfaces_path = write_json(root, "surfaces.json", surfaces)

                result = run_checker("--surfaces", str(surfaces_path), check=False)
                report = json.loads(result.stdout)

            self.assertEqual(result.returncode, 1)
            self.assertIn(expected_reason, report["blockers"])
            self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
            self.assertFalse(report["counts_toward_public_sdk"])
            self.assertFalse(report["counts_toward_p0_dependency_chain_claim"])
            self.assertFalse(report["permissions_admin_route_ready"])
            self.assertFalse(report["public_sdk_ready"])
            self.assertFalse(report["runtime_ready"])
            self.assertFalse(report["promotion_ready"])

    def test_rejects_player_identity_promotion_certificate_nested_readiness_overclaim(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = None
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
                    identity_surface = surface
            assert identity_surface is not None
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["nested_claims"] = {
                "publicSdkReady": True,
                "notes": ["permissions/admin is public and ready"],
            }
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(
                certificate_path
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_rejects_review_only_player_identity_promotion_certificate_artifact(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["ready_scope"] = "contract_review_input_only"
            certificate["source_kind"] = "passive-monitor-snapshot"
            certificate["evidence"]["review_artifact_only"] = True
            certificate["evidence"]["contract_review_only"] = True
            certificate["evidence"]["passive_evidence_only"] = True
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(
                certificate_path
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_non_promotion_artifact_source", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_certificate_missing_explicit_copied_principal_semantics(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            binding = write_identity_promotion_certificate(root, identity_surface)
            certificate_path = REPO_ROOT / binding["path"]
            certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
            certificate["evidence"]["semantic_proofs"].remove(
                "copied_principal_handle_generation_scope_flags"
            )
            certificate["evidence"]["public_fields"].remove("principal_generation")
            certificate["evidence"]["sdk_consumer_tests"] = []
            certificate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            identity_surface["evidence"]["player_identity_promotion_certificate"] = bind_json_artifact(
                certificate_path
            )
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_semantic_proofs_missing", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_public_fields_semantics_mismatch", report["blockers"])
        self.assertIn("player_identity_promotion_certificate_sdk_consumer_coverage_missing", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["promotion_ready"])

    def test_rejects_promoted_player_identity_without_promotion_certificate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["support_tier"] = "release-supported copied principal"
                    surface["capabilities"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
                    surface["public_contract"] = [
                        "ObeliskPlayerPrincipalEvent",
                        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
                        "UnregisterPlayerPrincipalEventWithOwnerToken",
                    ]
                    surface["public_fields"] = [
                        "abi_version",
                        "struct_size",
                        "principal_handle",
                        "principal_generation",
                        "principal_scope_flags",
                    ]
                    surface["abi_contract"] = [
                        "capability_gated",
                        "append_only_abi",
                        "owner_token_handle_registration",
                        "owner_scoped_unregister",
                        "plugin_owner_cleanup",
                        "no_ue_internals_in_public_abi",
                    ]
                    surface["lifecycle_contract"] = [
                        "plugin-owner cleanup",
                        "owner-token cleanup on init failure",
                        "owner-token cleanup on plugin unload",
                        "owner-scoped unregister cleanup",
                    ]
                    surface["evidence"]["accepted_runtime_evidence"] = accepted_runtime_evidence_record()
                    surface["evidence"].pop("player_identity_promotion_certificate", None)
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("player_identity_promotion_certificate_missing", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])

    def test_rejects_stale_player_identity_promotion_certificate_binding(self) -> None:
        with self.permissions_admin_identity_tempdir() as root:
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            identity_surface = promote_identity_surface_for_permissions_tests(surfaces)
            identity_surface["evidence"]["player_identity_promotion_certificate"] = (
                write_identity_promotion_certificate(root, identity_surface)
            )
            identity_surface["public_fields"].append("stale_certificate_test_field")
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "player_identity_promotion_certificate_stale_or_mismatched_upstream_surface",
            report["blockers"],
        )
        self.assertIn("player_identity_promotion_certificate_reviewed_surface_record_hash_mismatch", report["blockers"])
        self.assertIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["counts_toward_permissions_admin"])
        self.assertFalse(report["permissions_admin_unlock_allowed"])
        self.assertEqual(report["sdk_progress"], 0)
        self.assertEqual(report["p0_progress"], 0)

    def test_rejects_query_failclosed_artifact_readiness_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = {
                "schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
                "artifact_status": "candidate_only",
                "promotion_ready": True,
                "public_header_allowed": False,
                "public_cache_abi_allowed": False,
                "public_sdk_ready": True,
                "runtime_ready": True,
            }
            artifact_path = write_json(root, "query-manifest.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_artifact_promotion_ready_not_false", report["blockers"])
        self.assertIn("query_failclosed_artifact_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("query_failclosed_artifact_runtime_ready_not_false", report["blockers"])

    def test_rejects_query_failclosed_manifest_that_only_matches_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = {
                "schema": "obelisk.permissions-admin-query-failclosed-contract.v1",
                "artifact_status": "candidate_only",
                "promotion_ready": False,
                "public_header_allowed": False,
                "public_cache_abi_allowed": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
            }
            artifact_path = write_json(root, "query-manifest.json", artifact)

            result = run_checker("--query-failclosed-artifact", str(artifact_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_manifest_contract_invalid", report["blockers"])

    def test_rejects_permission_query_abi_boundary_properties_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            abi = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "abi.permission_query_identity_fields"
            )
            abi["required_properties"].remove("owner-token scoped call")
            abi["required_properties"].remove("no UE pointers or raw params")
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_text_boundary_properties_missing", report["blockers"])

    def test_rejects_owner_token_pre_evaluation_boundary_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            abi = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "abi.permission_query_identity_fields"
            )
            abi["required_properties"].remove(
                "owner-token validation happens before policy lookup, cache lookup, rate budget, or allow result"
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_text_boundary_properties_missing", report["blockers"])

    def test_rejects_missing_generation_mismatch_fail_closed_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            fail_closed = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "fail_closed.stale_or_scope_mismatch"
            )
            fail_closed["must_never_return_allow_for"].remove("principal_generation_mismatch")
            fail_closed["deny_or_unknown_conditions"].remove("mismatched principal_generation")
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_never_allow_cases_missing", report["blockers"])
        self.assertIn("fail_closed_deny_or_unknown_cases_missing", report["blockers"])

    def test_rejects_missing_owner_token_fail_closed_cases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            fail_closed = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "fail_closed.stale_or_scope_mismatch"
            )
            for case in (
                "zero plugin owner token",
                "unknown plugin owner token",
                "unloading plugin owner token",
                "rate limit exceeded",
            ):
                fail_closed["must_never_return_allow_for"].remove(case)
                fail_closed["deny_or_unknown_conditions"].remove(case)
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_never_allow_cases_missing", report["blockers"])
        self.assertIn("fail_closed_deny_or_unknown_cases_missing", report["blockers"])

    def test_rejects_missing_generation_scope_dependency_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            requirements = {
                item["id"]: item
                for item in decisions["required_before_public_header"]
            }
            requirements["identity.principal_generation_required"]["required_behavior"].remove(
                "missing generation fails closed"
            )
            requirements["identity.principal_scope_compatibility"]["required_behavior"].remove(
                "missing principal_scope_flags fails closed"
            )
            requirements["abi.permission_query_identity_fields"]["required_fields_or_equivalent"].remove(
                "principal_scope_flags"
            )
            requirements["abi.permission_query_identity_fields"]["required_fields_or_equivalent"].remove(
                "plugin_owner_token"
            )
            requirements["abi.permission_query_identity_fields"]["required_fields_or_equivalent"].remove(
                "server_process_epoch"
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("principal_generation_fail_closed_requirements_missing", report["blockers"])
        self.assertIn("principal_scope_fail_closed_requirements_missing", report["blockers"])
        self.assertIn("permission_query_identity_fields_unexpected", report["blockers"])

    def test_rejects_operator_config_allow_capable_or_runtime_owned_provenance_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["allow_capable_authority_ownership"] = "operator-config"
            policy = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "policy.authority_provenance_required"
            )
            policy["allow_capable_authority_kinds"].append("operator-config")
            policy["allow_capable_authority_ownership"] = "operator-config"
            policy["operator_config_allow_capable"] = True
            policy["runtime_local_authority_must_be_runtime_owned"] = False
            policy["required_behavior"].remove(
                "operator-config authority can provide runtime-owned policy inputs only and cannot produce allow"
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("allow_capable_authority_ownership_not_runtime_local_owned_only", report["blockers"])
        self.assertIn("policy_allow_capable_authority_kinds_unexpected", report["blockers"])
        self.assertIn("policy_allow_capable_authority_ownership_not_runtime_owned", report["blockers"])
        self.assertIn("policy_operator_config_allow_capable_not_false", report["blockers"])
        self.assertIn("policy_runtime_local_authority_not_required_runtime_owned", report["blockers"])
        self.assertIn("policy_authority_fail_closed_requirements_missing", report["blockers"])

    def test_rejects_duplicate_authority_kind_lists_that_set_match_required_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            policy = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "policy.authority_provenance_required"
            )
            policy["recognized_authority_kinds"] = [
                "operator-config",
                "runtime-local",
                "operator-config",
            ]
            policy["allow_capable_authority_kinds"] = [
                "runtime-local",
                "runtime-local",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("policy_recognized_authority_kinds_duplicate", report["blockers"])
        self.assertIn("policy_allow_capable_authority_kinds_duplicate", report["blockers"])

    def test_rejects_policy_provenance_self_attestation_requirements_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            policy = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "policy.authority_provenance_required"
            )
            for behavior in (
                "operator-config cannot self-attest allow-capable policy provenance",
                "command text cannot establish policy provenance",
                "policy provenance must be runtime-owned before allow",
                "plugin input cannot self-attest policy provenance",
            ):
                policy["required_behavior"].remove(behavior)
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("policy_authority_fail_closed_requirements_missing", report["blockers"])

    def test_rejects_policy_provenance_claim_fail_closed_cases_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            fail_closed = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "fail_closed.stale_or_scope_mismatch"
            )
            for case in (
                "command text policy provenance claim",
                "operator config policy provenance claim",
            ):
                fail_closed["must_never_return_allow_for"].remove(case)
                fail_closed["deny_or_unknown_conditions"].remove(case)
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("fail_closed_never_allow_cases_missing", report["blockers"])
        self.assertIn("fail_closed_deny_or_unknown_cases_missing", report["blockers"])

    def test_rejects_runtime_principal_evidence_as_identity_promotion_dependency_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            dependency = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "dependency.promoted_player_identity"
            )
            dependency["required_behavior"].remove(
                "runtime principal evidence alone is not public identity promotion"
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency_player_identity_public_contract_requirements_missing", report["blockers"])

    def test_rejects_partial_scoped_release_and_admin_target_dependency_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            dependency = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "dependency.promoted_player_identity"
            )
            for behavior in (
                "partial or contract-review-only identity public contract records cannot promote permissions/admin or count toward SDK/P0",
                "scoped non-complete-SDK release statements and explicit exclusions are bookkeeping only; they cannot promote permissions/admin, satisfy the player-identity dependency, or count toward SDK/P0",
                "copied admin targets such as ShooterPlayerController.ServerListPlayers and ShooterPlayerController.ServerKickPlayer are admin surface orientation only, not copied player identity/principal semantics",
            ):
                dependency["required_behavior"].remove(behavior)
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency_player_identity_public_contract_requirements_missing", report["blockers"])

    def test_rejects_missing_owner_token_cleanup_dependency_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            dependency = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "dependency.promoted_player_identity"
            )
            dependency["required_behavior"].remove(
                "promoted player identity must include owner-token cleanup on init failure, plugin unload, and owner-scoped unregister before permissions/admin can count as promoted"
            )
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("dependency_player_identity_public_contract_requirements_missing", report["blockers"])

    def test_rejects_cache_key_field_drift_and_public_cache_abi_unblocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            cache = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "cache.generation_scope_keying"
            )
            cache["status"] = "resolved"
            cache["public_cache_abi"] = "public"
            cache["required_cache_key_fields"] = [
                "plugin_owner_token",
                "principal_handle",
                "principal_generation",
                "action",
                "action",
                "resource_scope",
                "policy_epoch",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("cache_generation_scope_keying_status_not_unresolved", report["blockers"])
        self.assertIn("cache_public_cache_abi_unblocked", report["blockers"])
        self.assertIn("cache_key_fields_mismatch", report["blockers"])

    def test_rejects_missing_cache_generation_scope_invalidation_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            cache = next(
                item
                for item in decisions["required_before_public_header"]
                if item["id"] == "cache.generation_scope_keying"
            )
            for behavior in (
                "cached decisions are invalidated on principal_scope_flags change",
                "cached decisions are invalidated on policy_source_generation change",
                "cached decisions are invalidated on authority_generation change",
                "cached decisions are invalidated on plugin owner cleanup",
                "stale cache entries return deny or unknown, never allow",
            ):
                cache["required_behavior"].remove(behavior)
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("cache_generation_scope_invalidation_requirements_missing", report["blockers"])

    def test_rejects_decisions_public_header_mismatch_with_scanned_public_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["public_header"] = "include/obelisk/OtherApi.h"
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decisions_public_header_mismatch", report["blockers"])
        self.assertIn("decisions_public_header_not_scanned_header", report["blockers"])

    def test_rejects_public_header_alias_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header_path = root / "ObeliskApi.h"
            header_path.write_text(
                "typedef struct PermissionQuery PermissionQuery;\n"
                "typedef uint64_t PermissionReasonFlags;\n"
                "#define OBELISK_API_CAPABILITY_PERMISSION_QUERY 1\n"
                "#define OBELISK_API_CAPABILITY_PERMISSIONS 2\n"
                "#define OBELISK_PERMISSION_CHECKS_ABI_VERSION 1\n"
                "#define OBELISK_PERMISSIONS_ABI_VERSION 1\n"
                "bool CheckPermission(void);\n",
                encoding="utf-8",
            )

            result = run_checker("--public-header", str(header_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_contains_permissions_admin_symbol", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "public_header_contains_permissions_admin_symbol"
        )
        self.assertIn("PermissionQuery", detail["tokens"])
        self.assertIn("PermissionReasonFlags", detail["tokens"])
        self.assertIn("OBELISK_API_CAPABILITY_PERMISSION_QUERY", detail["tokens"])
        self.assertIn("OBELISK_API_CAPABILITY_PERMISSIONS", detail["tokens"])
        self.assertIn("OBELISK_PERMISSION_CHECKS_ABI_VERSION", detail["tokens"])
        self.assertIn("OBELISK_PERMISSIONS_ABI_VERSION", detail["tokens"])
        self.assertIn("CheckPermission", detail["tokens"])

    def test_rejects_public_header_under_protected_server_root(self) -> None:
        result = run_checker(
            "--public-header",
            "/servidor/ark/ObeliskApi.h",
            check=False,
        )
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_path_rejected", report["blockers"])

    def test_rejects_decisions_under_protected_server_root(self) -> None:
        result = run_checker("--decisions", "/servidor/ark/permissions-decisions.json", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_decisions_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "decisions.json"
            target.write_text(DECISIONS.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "decisions-link.json"
            link.symlink_to(target)

            result = run_checker("--decisions", str(link), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_surfaces_under_protected_server_root(self) -> None:
        result = run_checker("--surfaces", "/servidor/ark/public_sdk_surfaces.json", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surfaces_path_rejected", report["blockers"])

    def test_rejects_surfaces_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "surfaces.json"
            target.write_text(SURFACES.read_text(encoding="utf-8"), encoding="utf-8")
            link = root / "surfaces-link.json"
            link.symlink_to(target)

            result = run_checker("--surfaces", str(link), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("surfaces_path_rejected", report["blockers"])

    def test_rejects_query_failclosed_artifact_under_protected_server_root(self) -> None:
        result = run_checker("--query-failclosed-artifact", "/servidor/ark/permissions-query.json", check=False)
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_artifact_path_rejected", report["blockers"])

    def test_rejects_query_failclosed_artifact_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "permissions-query.json"
            subprocess.run(
                [sys.executable, str(QUERY_CHECKER), "--emit-template", str(manifest_path)],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            link = root / "permissions-query-link.json"
            link.symlink_to(manifest_path)

            result = run_checker("--query-failclosed-artifact", str(link), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("query_failclosed_artifact_path_rejected", report["blockers"])

    def test_rejects_public_header_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "ObeliskApi.h"
            target.write_text("/* no permissions/admin public ABI */\n", encoding="utf-8")
            link = root / "ObeliskApiLink.h"
            link.symlink_to(target)

            result = run_checker("--public-header", str(link), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_header_path_rejected", report["blockers"])

    def test_overclaim_scan_rejects_source_zero_start_end_transfer_and_rcon_aliases(self) -> None:
        blockers: list[dict] = []
        payload = {
            "source_overclaim_total_flag_count": 0,
            "status": "ready",
            "start_end_only_evidence": {"status": "ready"},
            "transfer_baccept_candidate": {"status": "ready"},
            "admin_snapshot": {"status": "ready"},
            "adminStatusSnapshotReady": True,
            "rcon_command_candidate": {"status": "ready"},
        }

        READINESS.collect_overclaims(payload, blockers, "$.unit")
        reasons = [blocker["reason"] for blocker in blockers]
        labels = [blocker["label"] for blocker in blockers]

        self.assertIn("source_overclaim_zero_status_alias_overclaim", reasons)
        self.assertIn("non_evidence_artifact_credit_overclaim", reasons)
        self.assertIn("public_surface_overclaim", reasons)
        self.assertIn("$.unit.admin_snapshot", labels)
        self.assertIn("$.unit.adminStatusSnapshotReady", labels)

    def test_canonical_runtime_evidence_binding_is_route_input_not_public_overclaim(self) -> None:
        accepted_runtime = {
            "schema": READINESS.PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
            "result": "approved runtime principal lifecycle evidence",
            "next_blocker": "identity_public_contract_gate_missing",
            "approved_runtime_evidence_binding_required": True,
            "approved_runtime_evidence_binding": {
                "schema": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
                "accepted_for_contract_review": True,
                "resolved_input": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
                "next_blocker": "identity_public_contract_gate_missing",
                "binding_scope": READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
                "non_claim": (
                    "Runtime evidence binding is identity-contract review input only; it is "
                    "not public SDK, runtime, permissions/admin, commands, or P0 progress."
                ),
                **{key: False for key in READINESS.APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS},
            },
        }
        blockers: list[dict] = []

        READINESS.collect_overclaims(
            {"evidence": {"accepted_runtime_evidence": accepted_runtime}},
            blockers,
            "$.surfaces.player_identity",
        )

        self.assertEqual([], blockers)

        accepted_runtime["approved_runtime_evidence_binding"]["public_sdk_ready"] = True
        READINESS.collect_overclaims(
            {"evidence": {"accepted_runtime_evidence": accepted_runtime}},
            blockers,
            "$.surfaces.player_identity",
        )
        self.assertIn("public_surface_overclaim", [blocker["reason"] for blocker in blockers])


if __name__ == "__main__":
    unittest.main()
