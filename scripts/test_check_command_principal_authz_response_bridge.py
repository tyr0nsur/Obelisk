#!/usr/bin/env python3
"""Tests for check_command_principal_authz_response_bridge.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_command_principal_authz_response_bridge.py"
DECISIONS = REPO_ROOT / "docs" / "command_principal_authz_response_bridge_decisions.json"
PLAYER_IDENTITY = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
PERMISSIONS_ADMIN = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
COMMAND_RESPONSE = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
COMMANDS_REPLIES = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"


class CheckCommandPrincipalAuthzResponseBridgeTests(unittest.TestCase):
    def run_checker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=REPO_ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def load_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def write_inputs(
        self,
        root: Path,
        *,
        decisions: dict | None = None,
        player_identity: dict | None = None,
        permissions_admin: dict | None = None,
        command_response: dict | None = None,
        commands_replies: dict | None = None,
        header: str | None = None,
    ) -> dict[str, Path]:
        paths = {
            "decisions": root / "command_principal_authz_response_bridge_decisions.json",
            "player_identity": root / "player_identity_public_contract_decisions.json",
            "permissions_admin": root / "permissions_admin_public_contract_decisions.json",
            "command_response": root / "command_chat_response_public_contract_decisions.json",
            "commands_replies": root / "commands_replies_public_contract_decisions.json",
            "header": root / "ObeliskApi.h",
        }
        paths["decisions"].write_text(json.dumps(decisions if decisions is not None else self.load_json(DECISIONS)), encoding="utf-8")
        paths["player_identity"].write_text(
            json.dumps(player_identity if player_identity is not None else self.load_json(PLAYER_IDENTITY)),
            encoding="utf-8",
        )
        paths["permissions_admin"].write_text(
            json.dumps(permissions_admin if permissions_admin is not None else self.load_json(PERMISSIONS_ADMIN)),
            encoding="utf-8",
        )
        paths["command_response"].write_text(
            json.dumps(command_response if command_response is not None else self.load_json(COMMAND_RESPONSE)),
            encoding="utf-8",
        )
        paths["commands_replies"].write_text(
            json.dumps(commands_replies if commands_replies is not None else self.load_json(COMMANDS_REPLIES)),
            encoding="utf-8",
        )
        paths["header"].write_text(header if header is not None else HEADER.read_text(encoding="utf-8"), encoding="utf-8")
        return paths

    def checker_args(self, paths: dict[str, Path]) -> list[str]:
        return [
            "--decisions",
            str(paths["decisions"]),
            "--player-identity",
            str(paths["player_identity"]),
            "--permissions-admin",
            str(paths["permissions_admin"]),
            "--command-response",
            str(paths["command_response"]),
            "--commands-replies",
            str(paths["commands_replies"]),
            "--public-header",
            str(paths["header"]),
        ]

    def replace_string_values(self, value: object, old: str, new: str) -> object:
        if isinstance(value, dict):
            return {key: self.replace_string_values(child, old, new) for key, child in value.items()}
        if isinstance(value, list):
            return [self.replace_string_values(child, old, new) for child in value]
        if isinstance(value, str):
            return value.replace(old, new)
        return value

    def test_accepts_current_bridge_as_planning_only(self) -> None:
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
        self.assertEqual([], report["public_capability_bits_now"])
        self.assertEqual([], report["public_response_abi_now"])
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

    def test_manifest_ties_the_shared_principal_vocabulary_to_fail_closed_conditions(self) -> None:
        payload = self.load_json(DECISIONS)
        self.assertEqual(payload["schema"], "obelisk.command-principal-authz-response-bridge-decisions.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertTrue(payload["planning_only"])
        self.assertFalse(payload["public_header_allowed"])
        self.assertEqual(payload["public_header_symbols_now"], [])
        self.assertEqual(payload["public_capability_bits_now"], [])
        self.assertEqual(payload["public_response_abi_now"], [])

        vocabulary = {item["field"]: item for item in payload["shared_principal_vocabulary"]}
        self.assertEqual(set(vocabulary), {"principal_handle", "principal_generation", "principal_scope_flags"})
        for item in vocabulary.values():
            self.assertTrue(item["fail_closed_when_missing"])

        for condition in (
            "missing principal_handle",
            "missing principal",
            "missing principal_generation",
            "missing principal_scope_flags",
            "command text principal claim",
            "operator config permission claim",
            "missing policy_epoch provenance",
            "plugin-supplied provenance",
            "permission deny result",
            "permission unknown result",
            "rate limit exceeded",
            "malformed UTF-8",
            "minimal ChatMessageEvent response shortcut",
            "raw ProcessEvent response shortcut",
            "legacy CallProcessEvent response shortcut",
            "static thunk orientation response shortcut",
            "commands/replies response shortcut before promoted identity and permissions/admin",
            "missing promoted player identity",
            "missing promoted permissions/admin",
            "missing command_chat_response_path promotion",
            "missing commands_replies promotion",
        ):
            self.assertIn(condition, payload["required_fail_closed_conditions"])

    def test_manifest_defines_planning_only_bridge_ergonomics_flow(self) -> None:
        payload = self.load_json(DECISIONS)
        self.assertEqual(
            [
                "copied chat text",
                "plugin-local parse",
                "copied command payload",
                "permission query",
                "response request",
            ],
            [step["step"] for step in payload["bridge_ergonomics_flow"]],
        )
        flow = {step["step"]: step["required_boundary"] for step in payload["bridge_ergonomics_flow"]}
        self.assertIn("request input only", flow["copied chat text"])
        self.assertIn("private plugin intent only", flow["plugin-local parse"])
        self.assertIn("nonzero plugin_owner_token", flow["copied command payload"])
        self.assertIn("permission_policy_epoch", flow["copied command payload"])
        self.assertIn("fail closed", flow["permission query"])
        self.assertIn("copied intent only", flow["response request"])
        self.assertIn("promoted player identity", flow["response request"])
        self.assertIn("promoted permissions/admin", flow["response request"])
        self.assertIn("command_chat_response_path are separately promoted", flow["response request"])

    def test_manifest_contains_authz_reason_flags_diagnostic_containment(self) -> None:
        payload = self.load_json(DECISIONS)
        diagnostic = payload["candidate_only_diagnostics"]["authz_reason_flags"]

        self.assertEqual("obelisk.permissions_admin.v1", diagnostic["source_surface"])
        self.assertEqual("docs/permissions_admin_query_failclosed_contract.json", diagnostic["source_artifact"])
        self.assertTrue(diagnostic["diagnostic_only"])
        self.assertTrue(diagnostic["candidate_only"])
        for key in (
            "public_header_allowed",
            "public_capability_bit_allowed",
            "public_abi_allowed",
            "response_abi_allowed",
            "command_payload_allowed",
            "response_payload_allowed",
            "server_validation_allowed",
            "authorization_decision_source",
            "changes_allow_deny_unknown",
            "replaces_policy_provenance",
            "permits_dispatch_or_response",
            "plugin_supplied_allowed",
            "command_text_supplied_allowed",
            "operator_config_supplied_allowed",
        ):
            self.assertFalse(diagnostic[key])
        self.assertIn("reason_flags", "\n".join(payload["non_claims"]))
        self.assertIn("dispatch authority", "\n".join(payload["non_claims"]))

    def test_rejects_missing_or_incomplete_bridge_ergonomics_flow(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["bridge_ergonomics_flow"] = [
            step
            for step in decisions["bridge_ergonomics_flow"]
            if step["step"] != "permission query"
        ]
        decisions["bridge_ergonomics_flow"][1]["required_boundary"] = "plugin-local parsing is convenient"
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("bridge_ergonomics_flow_order_mismatch", report["blockers"])
        self.assertIn("bridge_ergonomics_flow_step_missing", report["blockers"])
        self.assertIn("bridge_ergonomics_flow_boundary_incomplete", report["blockers"])

    def test_rejects_authz_reason_flags_as_bridge_payload_or_authority(self) -> None:
        decisions = self.load_json(DECISIONS)
        diagnostic = decisions["candidate_only_diagnostics"]["authz_reason_flags"]
        diagnostic["command_payload_allowed"] = True
        diagnostic["authorization_decision_source"] = True
        diagnostic["permits_dispatch_or_response"] = True
        decisions["required_bridge_behaviors"].append("future command payload includes reason_flags for plugin diagnostics")
        decisions["bridge_ergonomics_flow"][2]["required_boundary"] += " and reason_flags"
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("authz_reason_flags_containment_field_mismatch", report["blockers"])
        self.assertIn("authz_reason_flags_leaked_outside_diagnostic_containment", report["blockers"])

    def test_rejects_missing_authz_reason_flags_diagnostic_containment(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["candidate_only_diagnostics"].pop("authz_reason_flags")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("authz_reason_flags_diagnostic_containment_missing", report["blockers"])

    def test_rejects_bridge_public_runtime_and_abi_overclaims(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["public_header_allowed"] = True
        decisions["promotion_ready"] = True
        decisions["runtime_ready"] = True
        decisions["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE"]
        decisions["public_response_abi_now"] = ["ObeliskCommandChatResponse"]
        decisions["claim"] = "bridge response capability is public and ready"
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("public_response_abi_now_not_empty", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])

    def test_rejects_camel_hyphen_space_aliases_and_positive_readiness_texts(self) -> None:
        decisions = self.load_json(DECISIONS)
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
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("pre_runtime_principal_or_authority_claim_source", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])

    def test_rejects_missing_shared_principal_vocabulary(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["shared_principal_vocabulary"] = [
            item for item in decisions["shared_principal_vocabulary"] if item["field"] != "principal_generation"
        ]
        decisions["required_fail_closed_conditions"].remove("missing principal_generation")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("shared_principal_vocabulary_fields_mismatch", report["blockers"])
        self.assertIn("required_fail_closed_conditions_missing", report["blockers"])

    def test_rejects_source_doc_missing_principal_scope_flags_or_promoted_claim(self) -> None:
        commands_replies = self.load_json(COMMANDS_REPLIES)
        commands_replies["status"] = "promoted"
        commands_replies = self.replace_string_values(commands_replies, "principal_scope_flags", "principal_scope_marker")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), commands_replies=commands_replies)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("source_doc_unexpectedly_promoted", report["blockers"])
        self.assertIn("source_doc_missing_shared_principal_vocabulary", report["blockers"])

    def test_rejects_source_doc_schema_mismatch(self) -> None:
        command_response = self.load_json(COMMAND_RESPONSE)
        command_response["schema"] = "obelisk.permissions-admin-public-contract-decisions.v1"
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), command_response=command_response)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("source_doc_schema_mismatch", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "source_doc_schema_mismatch")
        self.assertEqual("$.command_response.schema", detail["label"])

    def test_rejects_source_doc_public_header_surface_claims(self) -> None:
        permissions_admin = self.load_json(PERMISSIONS_ADMIN)
        permissions_admin.pop("public_header_allowed")
        permissions_admin["public_header_symbols_now"] = ["ObeliskPermissionQuery"]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), permissions_admin=permissions_admin)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("source_doc_public_header_allowed_not_false", report["blockers"])
        self.assertIn("source_doc_public_header_symbols_now_not_empty", report["blockers"])

    def test_rejects_source_doc_public_capability_or_response_abi_claims(self) -> None:
        player_identity = self.load_json(PLAYER_IDENTITY)
        player_identity["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
        command_response = self.load_json(COMMAND_RESPONSE)
        command_response["public_response_abi_now"] = ["ObeliskCommandChatResponse"]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(
                Path(temp_dir),
                player_identity=player_identity,
                command_response=command_response,
            )
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("source_doc_public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("source_doc_public_response_abi_now_not_empty", report["blockers"])

    def test_rejects_public_header_forbidden_tokens(self) -> None:
        header = (
            HEADER.read_text(encoding="utf-8")
            + "\n#define OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE (1ull << 55)\n"
            + "#define OBELISK_API_CAPABILITY_COMMANDS (1ull << 56)\n"
            + "typedef struct ObeliskCommandPrincipalAuthzResponseBridge { uint32_t struct_size; } ObeliskCommandPrincipalAuthzResponseBridge;\n"
            + "typedef struct ObeliskPermissionCache { uint32_t struct_size; } ObeliskPermissionCache;\n"
            + "typedef uint64_t ObeliskPermissionReasonFlags;\n"
            + "#define OBELISK_PERMISSION_REASON_DENY 1u\n"
            + "uint64_t reason_flags;\n"
            + "typedef void (*RegisterCommand)(uint64_t owner_token);\n"
            + "typedef void (*ReplyToCommand)(uint64_t owner_token);\n"
            + "typedef void (*GrantPermission)(uint64_t owner_token);\n"
            + "typedef void (*SendChatWithOwnerToken)(uint64_t owner_token);\n"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), header=header)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_header_forbidden_symbols_present", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_forbidden_symbols_present")
        self.assertIn("OBELISK_API_CAPABILITY_COMMAND_PRINCIPAL_AUTHZ_RESPONSE_BRIDGE", detail["symbols"])
        self.assertIn("OBELISK_API_CAPABILITY_COMMANDS", detail["symbols"])
        self.assertIn("ObeliskCommandPrincipalAuthzResponseBridge", detail["symbols"])
        self.assertIn("ObeliskPermissionCache", detail["symbols"])
        self.assertIn("ObeliskPermissionReasonFlags", detail["symbols"])
        self.assertIn("OBELISK_PERMISSION_REASON_", detail["symbols"])
        self.assertIn("reason_flags", detail["symbols"])
        self.assertIn("RegisterCommand", detail["symbols"])
        self.assertIn("ReplyToCommand", detail["symbols"])
        self.assertIn("GrantPermission", detail["symbols"])
        self.assertIn("SendChatWithOwnerToken", detail["symbols"])

    def test_rejects_source_doc_missing_bridge_specific_fail_closed_semantics(self) -> None:
        permissions_admin = self.load_json(PERMISSIONS_ADMIN)
        permissions_admin = self.replace_string_values(permissions_admin, "policy_epoch", "policy_marker")
        permissions_admin = self.replace_string_values(permissions_admin, "rate limit exceeded", "burst limit tripped")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), permissions_admin=permissions_admin)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("source_doc_missing_bridge_semantics", report["blockers"])
        detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "source_doc_missing_bridge_semantics" and item["label"] == "$.permissions_admin"
        )
        self.assertIn("policy_epoch", detail["missing"])
        self.assertIn("missing policy_epoch provenance fails closed", detail["missing"])
        self.assertIn("rate limit exceeded", detail["missing"])


if __name__ == "__main__":
    unittest.main()
