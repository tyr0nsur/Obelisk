#!/usr/bin/env python3
"""Tests for check_command_principal_authz_response_bridge.py."""

from __future__ import annotations

import hashlib
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        self.assertFalse(report["bridge_claims_allowed"])
        self.assertEqual([], report["public_capability_bits_now"])
        self.assertEqual([], report["public_response_abi_now"])
        self.assertIn("planning-only and non-claim", report["non_claim"])
        self.assertIn("does not count as route acceptance", report["non_claim"])
        self.assertIn("public runtime readiness", report["non_claim"])
        self.assertEqual(
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
                "obelisk.commands_replies.v1",
            ],
            report["dependency_chain"],
        )
        self.assertEqual(
            {
                "bridge_decisions_path": file_sha256(DECISIONS),
                "player_identity_decisions_path": file_sha256(PLAYER_IDENTITY),
                "permissions_admin_decisions_path": file_sha256(PERMISSIONS_ADMIN),
                "command_response_decisions_path": file_sha256(COMMAND_RESPONSE),
                "commands_replies_decisions_path": file_sha256(COMMANDS_REPLIES),
                "public_header_path": file_sha256(HEADER),
            },
            report["source_artifact_hashes"],
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

    def test_rejects_accepted_runtime_alias_and_public_abi_lookup_handle_wording(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["post_evidence_shortcuts"] = {
            "acceptedRuntimeEvidenceReady": True,
            "identityPublicContractGatePassed": True,
        }
        decisions["notes"] = [
            "accepted runtime evidence unlocks public ABI",
            "accepted runtime evidence remains normalized only to identity_public_contract_gate_missing",
            "public ABI exposes player lookup handles before ResourceHandle promotion",
            "public ABI does not expose player lookup handles before ResourceHandle promotion",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("accepted_runtime_evidence_alias_skips_identity_public_contract_gate", report["blockers"])
        self.assertIn("public_abi_identity_lookup_handle_claim", report["blockers"])
        labels = {
            (detail["reason"], detail["label"])
            for detail in report["blocker_details"]
        }
        self.assertIn(
            ("accepted_runtime_evidence_alias_skips_identity_public_contract_gate", "$.decisions.notes[0]"),
            labels,
        )
        self.assertNotIn(
            ("accepted_runtime_evidence_alias_skips_identity_public_contract_gate", "$.decisions.notes[1]"),
            labels,
        )
        self.assertIn(("public_abi_identity_lookup_handle_claim", "$.decisions.notes[2]"), labels)
        self.assertNotIn(("public_abi_identity_lookup_handle_claim", "$.decisions.notes[3]"), labels)

    def test_rejects_ordered_dependency_chain_drift(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["ordered_dependency_chain"] = [
            "obelisk.permissions_admin.v1",
            "obelisk.player_identity.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        decisions["ordering_claims"] = [
            "permissions/admin can open before player identity",
            "command response path is public after permissions/admin only",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("ordered_dependency_chain_mismatch", report["blockers"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_camel_hyphen_space_aliases_and_positive_readiness_texts(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["alias_claims"] = {
            "accountingCredit": "earned",
            "canonical-route-gate-ready": True,
            "publicReplyAbiReady": True,
            "publicHeaderReady": True,
            "public-response-path-ready": True,
            "routeReady": True,
            "sdkCompletionCredit": "claimed",
            "send chat ready": True,
            "publicAbiReady": True,
            "runtimeReady": True,
            "permissions-admin-ready": True,
            "commandRouterAllowed": True,
            "commandRouterReady": True,
            "publicBridgeAbiAllowed": True,
            "public response abi allowed": True,
            "stableClaimAllowed": True,
            "v1SdkComplete": True,
            "authorityClaimSource": "command text",
            "principal-source": {"source": "operator-config"},
        }
        decisions["positive_claims"] = [
            "canonical route gate is ready",
            "SDK completion credit is earned",
            "v1 SDK is complete",
            "public ABI is ready",
            "public header is ready",
            "permissions/admin is public and ready",
            "reply endpoint is live",
            "command response path is live",
            "stable SDK is validated",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("accounting_credit_overclaim", report["blockers"])
        self.assertIn("pre_runtime_principal_or_authority_claim_source", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])

    def test_rejects_bridge_downstream_unlock_and_accounting_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["downstream_unlock_aliases"] = {
            "commandResponseReady": True,
            "commandResponseUnlocked": True,
            "commandResponsePathReady": True,
            "commandsRepliesReady": True,
            "commandsRepliesUnlocked": True,
            "permissionsAdminUnlocked": True,
            "responseReady": True,
            "responsePathReady": True,
            "countsTowardPublicSdk": True,
            "countsTowardRuntime": True,
            "countsTowardV1Completion": True,
            "countsTowardSdk": True,
            "countsTowardCompleteSdk": True,
            "countsTowardCompleteSdkClaim": True,
            "countsAsPublicSdk": True,
            "countsAsRuntime": True,
            "countsAsV1Completion": True,
            "publicOrRuntimeAccountingAllowed": True,
            "runtimeWorkAuthorized": True,
            "serverOperationsAuthorized": True,
            "operatorApprovalGranted": True,
            "runtimeApprovalGranted": True,
            "bridgeClaimsAllowed": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        claim_fields = {
            detail["field"]
            for detail in report["blocker_details"]
            if detail["reason"] == "public_or_runtime_overclaim"
        }
        for field in decisions["downstream_unlock_aliases"]:
            with self.subTest(field=field):
                self.assertIn(field, claim_fields)
        self.assertFalse(report["planning_only"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_bridge_split_accept_promote_and_progress_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["broad_alias_claims"] = {
            "permissionsAdminAccepted": True,
            "commandResponsePromoted": {"status": "ready"},
            "commandsRepliesAccepted": True,
            "routePromoted": True,
            "publicRuntimeReadinessPromoted": True,
            "v1CompletionProgressContribution": "25%",
            "p0DependencyChainProgressContribution": 1,
            "progress": "1/2",
            "progressReady": True,
            "readinessProgress": "1/4",
            "readinessReady": True,
            "acceptedForPlanning": True,
        }
        decisions["split_alias_claims"] = [
            {"field": "permissionsAdminPromoted", "status": "promoted"},
            {"name": "commandResponseAccepted", "value": {"state": "ready"}},
            {"key": "v1CompletionProgress", "value": "10%"},
            {"field": "commandsRepliesAccepted", "status": "blocked"},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("accounting_credit_overclaim", report["blockers"])
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        for label in (
            "$.decisions.broad_alias_claims.permissionsAdminAccepted",
            "$.decisions.broad_alias_claims.commandResponsePromoted",
            "$.decisions.broad_alias_claims.commandsRepliesAccepted",
            "$.decisions.broad_alias_claims.routePromoted",
            "$.decisions.broad_alias_claims.publicRuntimeReadinessPromoted",
            "$.decisions.split_alias_claims[0]",
            "$.decisions.split_alias_claims[1]",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)
        for label in (
            "$.decisions.broad_alias_claims.v1CompletionProgressContribution",
            "$.decisions.broad_alias_claims.p0DependencyChainProgressContribution",
            "$.decisions.broad_alias_claims.progress",
            "$.decisions.split_alias_claims[2]",
        ):
            self.assertIn(("accounting_credit_overclaim", label), details)
        for label in (
            "$.decisions.broad_alias_claims.progressReady",
            "$.decisions.broad_alias_claims.readinessProgress",
            "$.decisions.broad_alias_claims.readinessReady",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)
        self.assertNotIn(
            ("public_or_runtime_overclaim", "$.decisions.broad_alias_claims.acceptedForPlanning"),
            details,
        )
        self.assertNotIn(("public_or_runtime_overclaim", "$.decisions.split_alias_claims[3]"), details)

    def test_rejects_chat_rcon_broadcast_source_ready_and_candidate_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["source_ready_aliases"] = {
            "sourceReady": True,
            "source_status_ready": True,
            "chatReady": True,
            "chatSourceReady": True,
            "rconReady": True,
            "rconSourceReady": True,
            "broadcastReady": True,
            "broadcastSourceReady": True,
            "sendSourceReady": True,
            "sendSourceStatusReady": True,
            "commandCandidateReady": True,
            "commandsRepliesCandidateReady": True,
            "responseBridgeCandidateReady": True,
            "response_bridge_candidate": {
                "status": "ready",
                "p0_dependency_chain_progress_contribution": 1,
            },
            "source_kind_status_probe": {"source_kind": "rcon", "status": "sent"},
            "source_kind_chat_ready_probe": {"source_kind": "chat", "ready": True},
            "reply_channel_status_probe": {"reply_channel": "rcon", "status": "ready"},
            "send_channel_ready_probe": {"send_channel": "server_console", "is_ready": True},
            "status_metadata_probe": {"channel": "broadcast", "status": "delivered"},
            "delivery_source_metadata": {"transport": "send_chat", "source_status": "sent"},
            "transport_result_probe": {"transport": "broadcast", "result": "delivered"},
            "candidate_sources": [
                {"field": "command_candidate", "source_ready": True},
                {"field": "response_bridge_candidate", "status": "ready"},
                {"field": "sendSourceStatusReady", "source_status": "sent"},
                {"authority_claim_source": "rcon_command_candidate"},
                {"principal_source": "send_source"},
            ],
        }
        decisions["source_ready_claims"] = [
            "source-ready command candidate is public",
            "response bridge candidate counts toward SDK/P0 progress",
            "Plugin Hub stable SDK is ready",
            "send source is ready",
            "RCON status metadata is sent",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("accounting_credit_overclaim", report["blockers"])
        self.assertIn("pre_runtime_principal_or_authority_claim_source", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        for field in (
            "sourceReady",
            "source_status_ready",
            "chatReady",
            "chatSourceReady",
            "rconReady",
            "rconSourceReady",
            "broadcastReady",
            "broadcastSourceReady",
            "sendSourceReady",
            "sendSourceStatusReady",
            "commandCandidateReady",
            "commandsRepliesCandidateReady",
            "responseBridgeCandidateReady",
        ):
            self.assertIn(
                ("public_or_runtime_overclaim", f"$.decisions.source_ready_aliases.{field}"),
                details,
            )
        self.assertIn(
            (
                "accounting_credit_overclaim",
                "$.decisions.source_ready_aliases.response_bridge_candidate.p0_dependency_chain_progress_contribution",
            ),
            details,
        )
        for label in (
            "$.decisions.source_ready_aliases.source_kind_status_probe",
            "$.decisions.source_ready_aliases.source_kind_status_probe.status",
            "$.decisions.source_ready_aliases.source_kind_chat_ready_probe",
            "$.decisions.source_ready_aliases.source_kind_chat_ready_probe.ready",
            "$.decisions.source_ready_aliases.reply_channel_status_probe",
            "$.decisions.source_ready_aliases.reply_channel_status_probe.status",
            "$.decisions.source_ready_aliases.send_channel_ready_probe",
            "$.decisions.source_ready_aliases.send_channel_ready_probe.is_ready",
            "$.decisions.source_ready_aliases.status_metadata_probe",
            "$.decisions.source_ready_aliases.status_metadata_probe.status",
            "$.decisions.source_ready_aliases.delivery_source_metadata.source_status",
            "$.decisions.source_ready_aliases.transport_result_probe",
            "$.decisions.source_ready_aliases.transport_result_probe.result",
            "$.decisions.source_ready_aliases.candidate_sources[2]",
            "$.decisions.source_ready_aliases.candidate_sources[2].source_status",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)
        self.assertIn(
            (
                "pre_runtime_principal_or_authority_claim_source",
                "$.decisions.source_ready_aliases.candidate_sources[3].authority_claim_source",
            ),
            details,
        )
        self.assertIn(
            (
                "pre_runtime_principal_or_authority_claim_source",
                "$.decisions.source_ready_aliases.candidate_sources[4].principal_source",
            ),
            details,
        )
        self.assertIn(
            ("positive_public_or_runtime_claim", "$.decisions.source_ready_claims[3]"),
            details,
        )
        self.assertIn(
            ("positive_public_or_runtime_claim", "$.decisions.source_ready_claims[4]"),
            details,
        )

    def test_rejects_bridge_passive_seed_copied_intent_and_split_is_ready_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["response_bridge_aliases"] = {
            "responseBridgeReady": True,
            "passiveEvidenceReady": True,
            "passiveChatEvidenceReady": True,
            "copiedResponseIntentPlanningReady": True,
            "copiedResponseIntentReady": True,
            "localRoutingSeedReady": True,
            "localChatSeedReady": True,
        }
        decisions["split_response_bridge_claims"] = [
            {"name": "responseBridgeReady", "isReady": True},
            {"claim": "passiveEvidenceReady", "result": "accepted"},
            {"field": "copiedResponseIntentPlanningReady", "outcome": "promoted"},
            {"key": "localRoutingSeedReady", "verdict": "ready"},
            {"name": "responseBridgeReady", "isReady": False},
        ]
        decisions["response_bridge_claim_text"] = [
            "response bridge is ready",
            "copied response intent planning is accepted",
            "passive evidence is sufficient",
            "local routing seed is ready",
            "response bridge remains blocked",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        for label in (
            "$.decisions.response_bridge_aliases.responseBridgeReady",
            "$.decisions.response_bridge_aliases.passiveEvidenceReady",
            "$.decisions.response_bridge_aliases.passiveChatEvidenceReady",
            "$.decisions.response_bridge_aliases.copiedResponseIntentPlanningReady",
            "$.decisions.response_bridge_aliases.copiedResponseIntentReady",
            "$.decisions.response_bridge_aliases.localRoutingSeedReady",
            "$.decisions.response_bridge_aliases.localChatSeedReady",
            "$.decisions.split_response_bridge_claims[0]",
            "$.decisions.split_response_bridge_claims[1]",
            "$.decisions.split_response_bridge_claims[2]",
            "$.decisions.split_response_bridge_claims[3]",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)
        self.assertNotIn(("public_or_runtime_overclaim", "$.decisions.split_response_bridge_claims[4]"), details)
        for index in range(4):
            self.assertIn(("positive_public_or_runtime_claim", f"$.decisions.response_bridge_claim_text[{index}]"), details)
        self.assertNotIn(
            ("positive_public_or_runtime_claim", "$.decisions.response_bridge_claim_text[4]"),
            details,
        )

    def test_rejects_nested_positive_claims_even_under_negative_context_keys(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["non_claims"].append("The public bridge ABI is ready and runtime response delivery is enabled.")
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "positive_public_or_runtime_claim")
        self.assertIn("non_claims", detail["label"])

    def test_rejects_non_authorizing_artifact_report_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["non_authorizing_artifact_aliases"] = {
            "activationPreconditionReportReady": True,
            "betaNoticeActionReportReady": True,
            "bridgeReportReady": True,
            "commandPlanningReportReady": True,
            "nextActionRunnerReportReady": True,
            "noticeActionReportReady": True,
            "runtimeStatusArtifactReady": True,
            "sdkStatusReportReady": True,
            "statusArtifactReady": True,
            "packageShapeReportReady": True,
            "packageShapeAccepted": True,
            "packageInstallReady": True,
            "packageShapeInstallReady": True,
            "pluginHubReady": True,
            "pluginHubPlanningSupported": True,
            "sideLaneReady": True,
            "sideLaneArtifactReady": True,
            "supportTierReportReady": True,
            "supportTierReadinessReady": True,
        }
        decisions["non_authorizing_artifact_split_claims"] = [
            {"field": "bridge_report", "status": "ready"},
            {"field": "support_tier_report", "status": "supported"},
            {"field": "activation_precondition_report", "status": "ready"},
            {"field": "next_action_runner_output", "status": "ready"},
            {"field": "notice_action_report", "status": "accepted"},
            {"field": "runtime_status_artifact", "status": "accepted"},
            {"field": "package_shape", "status": "accepted"},
            {"field": "package_install", "status": "accepted"},
            {"field": "package_shape_install", "status": "ready"},
            {"field": "plugin_hub_planning", "status": "supported"},
            {"field": "side_lane_artifact", "status": "ready"},
        ]
        decisions["non_authorizing_source_markers"] = {
            "source_marker": "public_sdk_ready",
            "source_status": "supported",
            "source_marker_pair": {
                "source_marker": "generic_command_planning_package",
                "status": "accepted",
            },
            "runtime_status_source_marker_pair": {
                "source_marker": "runtime_status_artifact",
                "status": "accepted",
            },
            "source_marker_list_pair": {
                "source_markers": ["route_snapshot", "next_action_runner_output"],
                "source_state": "ready",
            },
            "source_provenance_plugin_hub_pair": {
                "source_provenance": "plugin_hub_planning",
                "status": "supported",
            },
            "source_provenance_side_lane_pair": {
                "source_provenance": "side_lane_artifact",
                "state": "ready",
            },
            "source_provenance_package_install_pair": {
                "source_provenance": "package_shape_install",
                "source_status": "accepted",
            },
        }
        decisions["non_authorizing_artifact_claim_text"] = [
            "bridge report is ready",
            "support tier report is supported",
            "activation precondition report is ready",
            "next-action runner output is ready",
            "notice action report is accepted",
            "runtime status artifact is accepted",
            "package shape is accepted",
            "package install is accepted",
            "Plugin Hub planning is supported",
            "side-lane artifact is ready",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        for field in decisions["non_authorizing_artifact_aliases"]:
            self.assertIn(
                ("public_or_runtime_overclaim", f"$.decisions.non_authorizing_artifact_aliases.{field}"),
                details,
            )
        for index in range(len(decisions["non_authorizing_artifact_split_claims"])):
            self.assertIn(
                ("public_or_runtime_overclaim", f"$.decisions.non_authorizing_artifact_split_claims[{index}]"),
                details,
            )
        for index in range(len(decisions["non_authorizing_artifact_claim_text"])):
            self.assertIn(
                ("positive_public_or_runtime_claim", f"$.decisions.non_authorizing_artifact_claim_text[{index}]"),
                details,
            )
        for label in (
            "$.decisions.non_authorizing_source_markers.source_marker",
            "$.decisions.non_authorizing_source_markers.source_status",
            "$.decisions.non_authorizing_source_markers.source_marker_pair",
            "$.decisions.non_authorizing_source_markers.source_marker_pair.status",
            "$.decisions.non_authorizing_source_markers.runtime_status_source_marker_pair",
            "$.decisions.non_authorizing_source_markers.runtime_status_source_marker_pair.status",
            "$.decisions.non_authorizing_source_markers.source_marker_list_pair",
            "$.decisions.non_authorizing_source_markers.source_marker_list_pair.source_state",
            "$.decisions.non_authorizing_source_markers.source_provenance_plugin_hub_pair",
            "$.decisions.non_authorizing_source_markers.source_provenance_plugin_hub_pair.status",
            "$.decisions.non_authorizing_source_markers.source_provenance_side_lane_pair",
            "$.decisions.non_authorizing_source_markers.source_provenance_side_lane_pair.state",
            "$.decisions.non_authorizing_source_markers.source_provenance_package_install_pair",
            "$.decisions.non_authorizing_source_markers.source_provenance_package_install_pair.source_status",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)

    def test_rejects_terminal_certificate_status_package_and_placeholder_shortcuts(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["terminal_status_package_shortcuts"] = {
            "acceptedForPlanning": True,
            "terminalCertificateMetadata": {
                "status": "issued",
                "acceptedForPlanning": True,
            },
            "packageShapeEvidence": {
                "status": "accepted",
                "acceptedForPlanning": True,
            },
            "responsePlanningReport": {
                "status": "accepted",
                "acceptedForPlanning": True,
            },
            "responseStatusReport": {"status": "ready"},
            "finalGateReady": True,
            "authzReady": True,
            "responsePathComplete": True,
            "routeClearedForPublicSendChatAbi": True,
            "scopedStatementReady": True,
            "statusReport": {"status": "ready"},
            "childCheckerPlaceholder": {
                "status": "placeholder",
                "acceptedForPlanning": True,
            },
        }
        decisions["terminal_status_package_split_claims"] = [
            {"field": "terminalCertificateMetadata", "status": "issued"},
            {"field": "packageShapeEvidence", "status": "accepted"},
            {"field": "responsePlanningReport", "status": "accepted"},
            {"field": "finalGateReady", "status": "ready"},
            {"field": "authzReady", "value": True},
            {"field": "responsePathComplete", "state": "complete"},
            {"field": "route_cleared", "status": "ready"},
            {"field": "scoped_statement_counts_toward_completion", "value": True},
            {"field": "childCheckerPlaceholder", "status": "placeholder"},
        ]
        decisions["terminal_status_package_claim_text"] = [
            "terminal certificate metadata is accepted",
            "response planning report is ready",
            "final gate ready now",
            "authz ready now",
            "response path complete now",
            "response path remains blocked until predecessor certificates",
            "route cleared for public send-chat ABI is ready",
            "scoped statement counts toward complete SDK claim",
            "child checker placeholder is accepted",
            "accepted for planning only and non-counting",
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("public_or_runtime_overclaim", report["blockers"])
        self.assertIn("positive_public_or_runtime_claim", report["blockers"])
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        self.assertNotIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.terminal_status_package_shortcuts.acceptedForPlanning",
            ),
            details,
        )
        for label in (
            "$.decisions.terminal_status_package_shortcuts.terminalCertificateMetadata",
            "$.decisions.terminal_status_package_shortcuts.packageShapeEvidence",
            "$.decisions.terminal_status_package_shortcuts.responsePlanningReport",
            "$.decisions.terminal_status_package_shortcuts.responseStatusReport",
            "$.decisions.terminal_status_package_shortcuts.finalGateReady",
            "$.decisions.terminal_status_package_shortcuts.authzReady",
            "$.decisions.terminal_status_package_shortcuts.responsePathComplete",
            "$.decisions.terminal_status_package_shortcuts.routeClearedForPublicSendChatAbi",
            "$.decisions.terminal_status_package_shortcuts.scopedStatementReady",
            "$.decisions.terminal_status_package_shortcuts.statusReport",
            "$.decisions.terminal_status_package_shortcuts.childCheckerPlaceholder",
            "$.decisions.terminal_status_package_split_claims[0]",
            "$.decisions.terminal_status_package_split_claims[1]",
            "$.decisions.terminal_status_package_split_claims[2]",
            "$.decisions.terminal_status_package_split_claims[3]",
            "$.decisions.terminal_status_package_split_claims[4]",
            "$.decisions.terminal_status_package_split_claims[5]",
            "$.decisions.terminal_status_package_split_claims[6]",
            "$.decisions.terminal_status_package_split_claims[7]",
            "$.decisions.terminal_status_package_split_claims[8]",
        ):
            self.assertIn(("public_or_runtime_overclaim", label), details)
        for index in (0, 1, 2, 3, 4, 6, 7, 8):
            self.assertIn(
                (
                    "positive_public_or_runtime_claim",
                    f"$.decisions.terminal_status_package_claim_text[{index}]",
                ),
                details,
            )
        for index in (5, 9):
            self.assertNotIn(
                (
                    "positive_public_or_runtime_claim",
                    f"$.decisions.terminal_status_package_claim_text[{index}]",
                ),
                details,
            )

    def test_accepts_next_blocker_non_claim_wording(self) -> None:
        decisions = self.load_json(DECISIONS)
        player_identity = self.load_json(PLAYER_IDENTITY)
        player_identity["post_approved_runtime_evidence_gate"]["non_claim"] = (
            "After approved runtime lifecycle evidence resolves runtime.lifecycle_evidence, "
            "the next blocker is reviewed_identity_public_contract; this remains an offline "
            "review gate and cannot open public ABI, public headers, callbacks, capability "
            "bits, runtime readiness, SDK readiness, or v1 completion."
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions, player_identity=player_identity)
            result = self.run_checker(*self.checker_args(paths))

        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual([], report["blockers"])

    def test_accepts_requirement_and_negative_guardrails_but_rejects_authorization_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["post_runtime_contract_guardrails"] = {
            "must_bind_to_approved_runtime_evidence": True,
            "does_not_unlock_public_header_gate": True,
            "requires_public_header_review": True,
            "runtime_work_authorized": True,
            "package_shape_ready": True,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        details = {(item["reason"], item["label"]) for item in report["blocker_details"]}
        self.assertNotIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.post_runtime_contract_guardrails.must_bind_to_approved_runtime_evidence",
            ),
            details,
        )
        self.assertNotIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.post_runtime_contract_guardrails.does_not_unlock_public_header_gate",
            ),
            details,
        )
        self.assertNotIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.post_runtime_contract_guardrails.requires_public_header_review",
            ),
            details,
        )
        self.assertIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.post_runtime_contract_guardrails.runtime_work_authorized",
            ),
            details,
        )
        self.assertIn(
            (
                "public_or_runtime_overclaim",
                "$.decisions.post_runtime_contract_guardrails.package_shape_ready",
            ),
            details,
        )

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

    def test_rejects_json_input_under_protected_server_root(self) -> None:
        result = self.run_checker(
            "--decisions",
            "/servidor/ark/command_principal_authz_response_bridge_decisions.json",
            check=False,
        )

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_json_input_symlink_component(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            decisions_path = Path(temp_dir) / "decisions.json"
            decisions_path.write_text(json.dumps(self.load_json(DECISIONS)), encoding="utf-8")
            link_path = Path(temp_dir) / "decisions-link.json"
            link_path.symlink_to(decisions_path)
            result = self.run_checker("--decisions", str(link_path), check=False)

        report = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertIn("decisions_path_rejected", report["blockers"])

    def test_rejects_source_zero_start_end_transfer_and_rcon_shortcut_aliases(self) -> None:
        decisions = self.load_json(DECISIONS)
        decisions["shortcut_alias_probe"] = {
            "source_overclaim_total_flag_count": 0,
            "status": "ready",
            "start_end_only_evidence": {"status": "ready"},
            "transfer_baccept_candidate": {"status": "ready"},
            "rcon_command_candidate": {"status": "ready"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = self.write_inputs(Path(temp_dir), decisions=decisions)
            result = self.run_checker(*self.checker_args(paths), check=False)

        report = json.loads(result.stdout)
        reasons = report["blockers"]

        self.assertEqual(1, result.returncode)
        self.assertIn("source_overclaim_zero_status_alias_overclaim", reasons)
        self.assertIn("public_or_runtime_overclaim", reasons)


if __name__ == "__main__":
    unittest.main()
