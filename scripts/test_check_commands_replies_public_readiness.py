#!/usr/bin/env python3
"""Tests for check_commands_replies_public_readiness.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_commands_replies_public_readiness.py"
DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
RESPONSE_TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
]


class CheckCommandsRepliesPublicReadinessTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def load_surfaces(self) -> dict:
        return json.loads(SURFACES.read_text(encoding="utf-8"))

    def write_inputs(
        self,
        root: Path,
        *,
        decisions: dict | None = None,
        surfaces: dict | None = None,
        header: str | None = None,
    ) -> tuple[Path, Path, Path]:
        decisions_path = root / "commands_replies_public_contract_decisions.json"
        surfaces_path = root / "public_sdk_surfaces.json"
        header_path = root / "ObeliskApi.h"
        decisions_path.write_text(json.dumps(decisions if decisions is not None else self.load_decisions()), encoding="utf-8")
        surfaces_path.write_text(json.dumps(surfaces if surfaces is not None else self.load_surfaces()), encoding="utf-8")
        header_path.write_text(header if header is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")
        return decisions_path, surfaces_path, header_path

    def test_accepts_current_manifests_as_planning_only(self) -> None:
        result = self.run_checker("--json")
        report = json.loads(result.stdout)

        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertTrue(report["planning_only"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_command_router_allowed"])
        self.assertFalse(report["public_reply_or_send_chat_abi_allowed"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )
        self.assertEqual([], report["blockers"])

    def test_rejects_decision_public_symbols_and_allowed_flags(self) -> None:
        decisions = self.load_decisions()
        decisions["public_header_allowed"] = True
        decisions["public_command_router_allowed"] = True
        decisions["public_reply_or_send_chat_abi_allowed"] = True
        decisions["public_header_symbols_now"] = ["RegisterCommandWithOwnerToken"]
        decisions["public_contract"] = ["RegisterCommandWithOwnerToken"]
        decisions["required_before_public_header"][0]["status"] = "resolved"
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_command_router_allowed_not_false", report["blockers"])
        self.assertIn("public_reply_or_send_chat_abi_allowed_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_contract_not_empty", report["blockers"])
        self.assertIn("required_before_public_header_item_not_unresolved", report["blockers"])

    def test_rejects_surface_public_contract_and_dependency_reorder(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        commands = by_id["obelisk.commands_replies.v1"]
        commands["status"] = "promoted"
        commands["public_contract"] = ["ObeliskCommandPayload"]
        commands["depends_on"] = [
            "obelisk.command_chat_response_path.v1",
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
        ]
        surfaces["promoted_surfaces"].append("obelisk.commands_replies.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("commands_replies_listed_as_promoted", report["blockers"])
        self.assertIn("commands_replies_status_mismatch", report["blockers"])
        self.assertIn("commands_replies_public_contract_not_empty", report["blockers"])
        self.assertIn("dependency_chain_depends_on_mismatch", report["blockers"])

    def test_rejects_response_path_planning_evidence_promoted_in_surfaces(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        by_id["obelisk.command_chat_response_path.v1"]["status"] = "promoted"
        surfaces["promoted_surfaces"].append("obelisk.command_chat_response_path.v1")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_planning_evidence_treated_as_promoted", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_rejects_manifest_only_upstream_dependency_promotion(self) -> None:
        cases = (
            ("obelisk.player_identity.v1", "player_identity_evidence_not_approved"),
            ("obelisk.permissions_admin.v1", "permissions_admin_evidence_not_approved"),
            ("obelisk.command_chat_response_path.v1", "command_chat_response_evidence_not_approved"),
        )
        for surface_id, blocker in cases:
            with self.subTest(surface_id=surface_id):
                surfaces = self.load_surfaces()
                by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
                by_id[surface_id]["status"] = "promoted"
                with tempfile.TemporaryDirectory() as temp_dir:
                    decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
                    result = self.run_checker(
                        "--decisions",
                        str(decisions_path),
                        "--surfaces",
                        str(surfaces_path),
                        "--public-header",
                        str(header_path),
                        check=False,
                    )

                report = json.loads(result.stdout)
                self.assertEqual(1, result.returncode)
                self.assertIn(blocker, report["blockers"])

    def test_rejects_promoted_surfaces_manifest_only_upstream_dependencies(self) -> None:
        surfaces = self.load_surfaces()
        surfaces["promoted_surfaces"].extend(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("permissions_admin_manifest_promotion_without_evidence", report["blockers"])
        self.assertIn("command_chat_response_manifest_promotion_without_evidence", report["blockers"])

    def test_rejects_promoted_experimental_upstream_dependency_statuses(self) -> None:
        surfaces = self.load_surfaces()
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        by_id["obelisk.player_identity.v1"]["status"] = "promoted-experimental-only"
        by_id["obelisk.permissions_admin.v1"]["status"] = "promoted-experimental-only"
        by_id["obelisk.command_chat_response_path.v1"]["status"] = "promoted-experimental-only"
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("player_identity_evidence_not_approved", report["blockers"])
        self.assertIn("permissions_admin_evidence_not_approved", report["blockers"])
        self.assertIn("command_chat_response_evidence_not_approved", report["blockers"])

    def test_rejects_dependency_sequence_and_required_chain_drift(self) -> None:
        surfaces = self.load_surfaces()
        surfaces["v1_dependency_sequence"] = [
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.commands_replies.v1",
        ]
        surfaces["v1_required_dependency_chain"] = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), surfaces=surfaces)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("v1_dependency_sequence_mismatch", report["blockers"])
        self.assertIn("dependency_chain_surface_missing_from_required_chain", report["blockers"])

    def test_rejects_public_header_command_reply_and_parser_symbols(self) -> None:
        header = (
            HEADER.read_text(encoding="utf-8")
            + "\n#define OBELISK_API_CAPABILITY_COMMAND_ROUTER (1ull << 50)\n"
            + "typedef struct ObeliskCommandParser { uint32_t struct_size; } ObeliskCommandParser;\n"
            + "typedef void (*ReplyToCommandWithOwnerToken)(uint64_t ownerToken);\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), header=header)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_forbidden_symbols_present", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_forbidden_symbols_present")
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_ROUTER", detail["symbols"])
        self.assertIn("ObeliskCommandParser", detail["symbols"])
        self.assertIn("ReplyToCommandWithOwnerToken", detail["symbols"])

    def test_rejects_positive_command_router_response_and_arkapi_parser_claims(self) -> None:
        decisions = self.load_decisions()
        decisions["claim"] = "command router is public and ready"
        decisions["arkapi_parser_copy_allowed"] = True
        decisions["notes"] = [
            "ArkApi command parser copied and supported",
            "send-chat is available",
            "reply is supported",
            "router is ready",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_surface_overclaim", report["blockers"])
        self.assertIn("positive_public_surface_claim", report["blockers"])

    def test_rejects_missing_runtime_owned_principal_permissions_gate(self) -> None:
        decisions = self.load_decisions()
        gate = decisions["runtime_owned_principal_permissions_gate"]
        gate["runtime_owned_permission_allow_required"] = False
        gate["reply_send_chat_router_claims_allowed"] = True
        gate["required_runtime_owned_inputs"] = [
            item for item in gate["required_runtime_owned_inputs"] if item != "permission_decision"
        ]
        gate["forbidden_authority_sources"] = [
            item for item in gate["forbidden_authority_sources"] if item != "router metadata"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("runtime_owned_principal_permissions_gate_required_true_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_required_false_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_inputs_missing", report["blockers"])
        self.assertIn("runtime_owned_principal_permissions_gate_forbidden_sources_missing", report["blockers"])

    def test_rejects_missing_bridge_principal_fail_closed_auth_behaviors(self) -> None:
        decisions = self.load_decisions()
        auth = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "auth.identity_permission_provenance"
        )
        auth["required_behavior"] = [
            behavior
            for behavior in auth["required_behavior"]
            if behavior
            not in {
                "principal tuple source must be runtime-owned player identity observation before any command payload can consume player identity",
                "principal_handle, principal_generation, and principal_scope_flags must appear together in any future command payload that consumes player identity",
                "plugin-supplied principal tuple fails closed",
                "missing principal_handle fails closed",
                "missing principal_scope_flags fails closed",
                "server process epoch mismatch fails closed",
                "permission allow cannot be consumed without policy provenance",
                "permission allow must come from runtime-owned permissions/admin evaluation for the same principal_handle, principal_generation, and principal_scope_flags tuple",
                "reply requests, send-chat requests, and router metadata cannot establish principal identity, permission authority, or policy provenance",
                "reply/send-chat/router planning cannot consume permission allow until promoted permissions/admin returns allow with runtime-owned policy provenance",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("auth_identity_permission_behavior_missing", report["blockers"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "auth_identity_permission_behavior_missing"
        )
        self.assertIn(
            "principal tuple source must be runtime-owned player identity observation before any command payload can consume player identity",
            detail["missing"],
        )
        self.assertIn("plugin-supplied principal tuple fails closed", detail["missing"])
        self.assertIn("missing principal_handle fails closed", detail["missing"])
        self.assertIn("missing principal_scope_flags fails closed", detail["missing"])
        self.assertIn("server process epoch mismatch fails closed", detail["missing"])
        self.assertIn("permission allow cannot be consumed without policy provenance", detail["missing"])
        self.assertIn(
            "permission allow must come from runtime-owned permissions/admin evaluation for the same principal_handle, principal_generation, and principal_scope_flags tuple",
            detail["missing"],
        )
        self.assertIn(
            "reply requests, send-chat requests, and router metadata cannot establish principal identity, permission authority, or policy provenance",
            detail["missing"],
        )
        self.assertIn(
            "reply/send-chat/router planning cannot consume permission allow until promoted permissions/admin returns allow with runtime-owned policy provenance",
            detail["missing"],
        )

    def test_rejects_missing_lifecycle_and_abuse_contract_guards(self) -> None:
        decisions = self.load_decisions()
        decisions["forbidden_public_contract"] = [
            item
            for item in decisions["forbidden_public_contract"]
            if item != "raw ProcessEvent or legacy CallProcessEvent fallback"
        ]
        lifecycle = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "lifecycle.owner_scoped_registration_cleanup"
        )
        lifecycle["required_behavior"] = [
            item
            for item in lifecycle["required_behavior"]
            if item
            not in {
                "future command router, reply/send path, and response shortcuts require owner-scoped lifecycle and unregister cleanup before public ABI",
                "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy command lifecycle cleanup or dispatch drain",
            }
        ]
        abuse = next(
            item
            for item in decisions["required_before_public_header"]
            if item["id"] == "abuse.rate_limit_audit_moderation_boundary"
        )
        abuse["required_behavior"] = [
            item
            for item in abuse["required_behavior"]
            if item
            != "command router, reply request, send-chat request, raw ProcessEvent, and legacy CallProcessEvent paths cannot bypass rate-limit, abuse, or sanitized audit gates"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("forbidden_public_contract_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_cleanup_behavior_missing", report["blockers"])
        self.assertIn("abuse_rate_limit_audit_behavior_missing", report["blockers"])

    def test_rejects_missing_migration_vocabulary_guardrail(self) -> None:
        decisions = self.load_decisions()
        decisions.pop("migration_vocabulary_not_compatibility", None)
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("migration_vocabulary_not_compatibility_missing", report["blockers"])

    def test_rejects_incomplete_migration_vocabulary_semantics(self) -> None:
        decisions = self.load_decisions()
        migration = decisions["migration_vocabulary_not_compatibility"]
        migration["allowed_terms"].remove("admin-like command")
        migration["recognized_source_kinds"].remove("server_console")
        migration["registration_semantics"].remove(
            "reply/send-chat/router planning must consume only runtime-owned principal and permissions provenance after separate promotion"
        )
        migration["registration_semantics"].remove("permission denial or unknown result never dispatches a command")
        migration["non_compatibility_claims"].remove("no direct plugin portability claim")
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path, surfaces_path, header_path = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(
                "--decisions",
                str(decisions_path),
                "--surfaces",
                str(surfaces_path),
                "--public-header",
                str(header_path),
                check=False,
            )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("migration_vocabulary_allowed_terms_missing", report["blockers"])
        self.assertIn("migration_vocabulary_source_kinds_missing", report["blockers"])
        self.assertIn("migration_vocabulary_registration_semantics_missing", report["blockers"])
        self.assertIn("migration_vocabulary_non_compatibility_missing", report["blockers"])

    def test_accepts_optional_response_path_planning_report_only(self) -> None:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "target_set": "command-chat-response-route-planning",
            "target_filters": RESPONSE_TARGETS,
            "readiness_status": "compared",
            "decisions_status": "blocked",
            "public_readiness_ready": False,
            "public_header_allowed": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "blockers": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "response.json"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), "--json")

        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertTrue(report["accepted_for_planning"])
        self.assertFalse(report["public_readiness_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_optional_response_path_minimal_report_schema(self) -> None:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "public_readiness_ready": False,
            "public_header_allowed": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "response.json"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_not_planning_only", report["blockers"])
        self.assertIn("response_path_report_target_set_mismatch", report["blockers"])
        self.assertIn("response_path_report_target_filters_mismatch", report["blockers"])
        self.assertIn("response_path_report_readiness_status_mismatch", report["blockers"])
        self.assertIn("response_path_report_decisions_status_mismatch", report["blockers"])

    def test_rejects_optional_response_path_minimal_raw_readiness(self) -> None:
        response_readiness = {
            "schema": "obelisk.reflection-snapshot-readiness.v1",
            "planning_layout_gate": {"ready": True},
            "promotion_gate": {"ready": False},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "response-readiness.json"
            report_path.write_text(json.dumps(response_readiness), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("evidence_scope_mismatch", report["blockers"])
        self.assertIn("target_sets_mismatch", report["blockers"])
        self.assertIn("totals_missing", report["blockers"])

    def test_rejects_optional_response_path_report_promoted_overclaim(self) -> None:
        response_report = {
            "schema": "obelisk.command-chat-response-public-readiness-check.v1",
            "valid": True,
            "accepted_for_planning": True,
            "planning_only": True,
            "surface": "obelisk.command_chat_response_path.v1",
            "target_set": "command-chat-response-route-planning",
            "target_filters": RESPONSE_TARGETS,
            "readiness_status": "compared",
            "decisions_status": "blocked",
            "public_readiness_ready": True,
            "public_header_allowed": False,
            "promotion_ready": True,
            "public_sdk_ready": False,
            "public_abi_ready": False,
            "runtime_ready": False,
            "blockers": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report_path = root / "response.json"
            report_path.write_text(json.dumps(response_report), encoding="utf-8")
            result = self.run_checker("--response-path-report", str(report_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("response_path_report_public_readiness_ready_not_false", report["blockers"])
        self.assertIn("response_path_report_promotion_ready_not_false", report["blockers"])
        self.assertIn("public_surface_overclaim", report["blockers"])


if __name__ == "__main__":
    unittest.main()
