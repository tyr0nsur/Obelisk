#!/usr/bin/env python3
"""Tests for check_permissions_admin_public_readiness.py."""

from __future__ import annotations

import json
import importlib.util
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


class PermissionsAdminPublicReadinessTests(unittest.TestCase):
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

    def test_accepts_candidate_query_failclosed_manifest_and_report_only_as_planning(self) -> None:
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

            report_path = root / "permissions-query-report.json"
            query_report = subprocess.run(
                [sys.executable, str(QUERY_CHECKER), str(manifest_path), "--json"],
                cwd=REPO_ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report_path.write_text(query_report.stdout, encoding="utf-8")
            result = run_checker("--query-failclosed-artifact", str(report_path))
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(report["accepted_for_planning"])
            self.assertEqual(
                report["query_failclosed_artifact_schema"],
                "obelisk.permissions-admin-query-failclosed-contract-check.v1",
            )

    def test_rejects_fabricated_query_failclosed_report_without_contract_fingerprint(self) -> None:
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
        self.assertIn("query_failclosed_report_input_schema_mismatch", report["blockers"])
        self.assertIn("query_failclosed_report_query_fields_mismatch", report["blockers"])
        self.assertIn("query_failclosed_report_fail_closed_cases_mismatch", report["blockers"])

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

    def test_mixed_negation_does_not_hide_positive_runtime_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "permissions/admin remains blocked but runtime ready"}, blockers)

        self.assertEqual(["positive_public_surface_claim"], [item["reason"] for item in blockers])

    def test_negative_runtime_suffix_is_not_positive_claim(self) -> None:
        blockers: list[dict[str, object]] = []
        READINESS.collect_overclaims({"note": "runtime ready remains blocked"}, blockers)

        self.assertEqual([], blockers)

    def test_rejects_camel_hyphen_space_aliases_and_positive_readiness_texts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))
            decisions["alias_claims"] = {
                "publicReplyAbiReady": True,
                "public-response-path-ready": True,
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
                "permissions/admin is public and ready",
                "reply endpoint is live",
                "command response path is live",
            ]
            decisions_path = write_json(root, "decisions.json", decisions)

            result = run_checker("--decisions", str(decisions_path), check=False)
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("pre_runtime_principal_or_authority_claim_source", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])

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

    def test_rejects_promoted_player_identity_with_only_runtime_evidence_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
            for surface in surfaces["surfaces"]:
                if surface["id"] == "obelisk.player_identity.v1":
                    surface["status"] = "promoted"
                    surface["evidence"]["accepted_runtime_evidence"] = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": "identity_public_contract_gate_missing",
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
        self.assertNotIn("player_identity_evidence_not_approved", report["blockers"])
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
                    surface["evidence"]["accepted_runtime_evidence"] = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
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
                    surface["evidence"]["accepted_runtime_evidence"] = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
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
                    surface["evidence"]["accepted_runtime_evidence"] = {
                        "schema": "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1",
                        "result": "approved runtime principal lifecycle evidence",
                        "next_blocker": "identity_public_contract_gate_missing",
                    }
                    surface["evidence"]["sdk_consumer_tests"] = ["tests/sdk_consumer/player_identity_plugin.cpp"]
                    surface["v1_decision_contract"]["current_decision"] = "promoted_public_contract"
                    surface["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"] = False
                    surface["blockers"] = [
                        blocker
                        for blocker in surface["blockers"]
                        if blocker != "No approved runtime principal lifecycle evidence."
                    ]
            surfaces_path = write_json(root, "surfaces.json", surfaces)

            result = run_checker("--surfaces", str(surfaces_path))
            report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertNotIn("player_identity_public_contract_not_promoted", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_query_failclosed_artifact_readiness_overclaim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = {
                "schema": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
                "mode": "consume",
                "ready": True,
                "promotion_ready": True,
                "public_sdk_ready": True,
                "runtime_ready": True,
            }
            artifact_path = write_json(root, "query-report.json", artifact)

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


if __name__ == "__main__":
    unittest.main()
