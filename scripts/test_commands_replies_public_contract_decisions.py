#!/usr/bin/env python3
"""Guardrails for the future copied commands/replies contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "commands_replies_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_IDS = {
    "dependency.promoted_player_identity",
    "dependency.promoted_permissions_admin",
    "dependency.promoted_command_chat_response_path",
    "abi.future_copied_command_payload",
    "abi.no_public_symbols_now",
    "auth.identity_permission_provenance",
    "lifecycle.owner_scoped_registration_cleanup",
    "parser.no_arkapi_copy",
    "abuse.rate_limit_audit_moderation_boundary",
    "separation.no_response_send_reply_moderation",
    "evidence.runtime_sdk_coverage",
    "release.not_sufficient_for_v1",
}

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_COMMANDS_REPLIES",
    "OBELISK_API_CAPABILITY_COMMAND_ROUTER",
    "OBELISK_API_CAPABILITY_CHAT_REPLIES",
    "OBELISK_API_CAPABILITY_SEND_CHAT",
    "OBELISK_COMMANDS_REPLIES_ABI_VERSION",
    "OBELISK_COMMAND_ROUTER_ABI_VERSION",
    "ObeliskCommandRegistration",
    "ObeliskCommandCallback",
    "ObeliskCommandPayload",
    "ObeliskCommandReply",
    "ObeliskChatReply",
    "ObeliskSendChat",
    "RegisterCommandWithOwnerToken",
    "UnregisterCommandWithOwnerToken",
    "ReplyToCommandWithOwnerToken",
    "SendChatWithOwnerToken",
}


class CommandsRepliesPublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.commands-replies-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.commands_replies.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["planning_stage"], "v1_completion_blocker")
        self.assertTrue(payload["not_sufficient_for_v1"])
        self.assertFalse(payload["public_header_allowed"])
        self.assertEqual(payload["public_header_symbols_now"], [])
        self.assertFalse(payload["public_command_router_allowed"])
        self.assertFalse(payload["public_reply_or_send_chat_abi_allowed"])
        self.assertFalse(payload["public_response_path_allowed"])
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)

    def test_dependency_chain_blocks_commands_replies_until_response_path_is_promoted(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        self.assertIn("obelisk.player_identity.v1", requirements["dependency.promoted_player_identity"]["decision_required"])
        self.assertIn("permissions/admin", requirements["dependency.promoted_permissions_admin"]["decision_required"])

        response_path = requirements["dependency.promoted_command_chat_response_path"]
        self.assertEqual(response_path["required_dependency"], "obelisk.command_chat_response_path.v1")
        for behavior in (
            "commands/replies remains blocked while command_chat_response_path is unpromoted or unresolved",
            "passive ChatMessageEvent parsing does not authorize replies",
            "legacy CallProcessEvent debug access does not authorize responses",
            "no response path is public through commands/replies until the response path is separately promoted",
        ):
            self.assertIn(behavior, response_path["required_behavior"])

    def test_future_command_abi_blocks_raw_ue_fstring_and_public_response_paths(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        abi = requirements["abi.future_copied_command_payload"]
        self.assertEqual(
            set(abi["required_fields_or_equivalent"]),
            {
                "abi_version",
                "struct_size",
                "plugin_owner_token",
                "command_handle",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "permission_policy_epoch",
                "command_name_utf8",
                "command_name_size",
                "arguments_utf8",
                "arguments_size",
                "source_kind",
                "delivery_scope",
                "command_flags",
            },
        )
        for property_name in (
            "POD C ABI",
            "append-only layout",
            "owner-token scoped registration",
            "copied UTF-8 input",
            "no raw UE pointers or raw params",
            "no raw FString exposure",
            "no public UFunction or vtable details",
        ):
            self.assertIn(property_name, abi["required_properties"])

        no_symbols = requirements["abi.no_public_symbols_now"]
        for behavior in (
            "public_header_symbols_now remains empty",
            "no commands/replies capability bit is advertised",
            "no public register/unregister command ABI exists",
            "no public reply or send-chat ABI exists",
            "no public command_chat_response_path ABI is exposed through commands/replies",
            "CallProcessEvent is not a public command or reply mechanism",
        ):
            self.assertIn(behavior, no_symbols["required_behavior"])

        for forbidden in (
            "public CallProcessEvent command or reply path",
            "public command_chat_response_path ABI",
            "reply ABI",
            "send-chat ABI",
            "moderation API",
            "raw UE pointers",
            "raw ProcessEvent params",
            "raw FString storage",
            "UObject pointers",
            "UFunction pointers",
        ):
            self.assertIn(forbidden, payload["forbidden_public_contract"])
        for forbidden in (
            "principal or permission claims from command text",
            "principal or permission claims from operator config",
        ):
            self.assertIn(forbidden, payload["forbidden_public_contract"])

    def test_auth_lifecycle_abuse_and_arkapi_boundaries_are_explicit(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        auth = requirements["auth.identity_permission_provenance"]
        for behavior in (
            "missing principal fails closed",
            "missing principal_generation fails closed",
            "stale principal fails closed",
            "unsupported principal_scope_flags fails closed",
            "permission denial or unknown result never dispatches a command",
            "command text remains copied request data only and cannot establish identity, permission authority, or policy provenance",
            "operator config remains policy input only and cannot establish command identity, principal identity, permission authority, or policy provenance",
            "command callbacks cannot self-attest permission authority",
        ):
            self.assertIn(behavior, auth["required_behavior"])

        lifecycle = requirements["lifecycle.owner_scoped_registration_cleanup"]
        for behavior in (
            "command registrations are owner-token scoped",
            "plugin init failure removes all command registrations before dlclose",
            "plugin unload unregisters commands and waits for in-flight callbacks or fails closed without dlclose",
            "self-unregister from a command callback is safe",
            "command callbacks cannot outlive copied payload storage",
        ):
            self.assertIn(behavior, lifecycle["required_behavior"])

        parser = requirements["parser.no_arkapi_copy"]
        for behavior in (
            "no ArkApi or AseApi command parser code is copied",
            "no ArkApi or AseApi constants, schemas, control flow, return semantics, offsets, vtables, or native-call wrappers are copied",
            "plugin-local parser scaffolds remain local helpers and do not become a public SDK router",
            "compatibility naming can inform demand only and cannot substitute for promotion evidence",
        ):
            self.assertIn(behavior, parser["required_behavior"])

        abuse = requirements["abuse.rate_limit_audit_moderation_boundary"]
        for behavior in (
            "command dispatch attempts are rate-limited per plugin owner token and source scope",
            "malformed UTF-8, oversize commands, and unsupported source kinds fail closed",
            "operator controls can disable command dispatch without disabling passive chat intake",
            "moderation, ban, kick, mute, broadcast, scheduled notice, and admin mutation APIs remain separate promotions",
        ):
            self.assertIn(behavior, abuse["required_behavior"])

    def test_evidence_and_release_contract_keep_commands_replies_post_v1(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        evidence = requirements["evidence.runtime_sdk_coverage"]
        self.assertEqual(
            set(evidence["required_evidence"]),
            {
                "promoted player identity evidence",
                "promoted permissions/admin evidence",
                "promoted command_chat_response_path evidence",
                "copied command ABI layout tests",
                "owner-token lifecycle tests",
                "permission fail-closed tests",
                "SDK consumer tests",
                "isolated runtime command dispatch evidence",
                "second-source or independently reviewed command source evidence",
            },
        )
        for insufficient in (
            "passive ChatMessageEvent parsing",
            "plugin-local command parser scaffold",
            "static thunk orientation",
            "legacy CallProcessEvent debug gate",
            "raw ProcessEvent callbacks",
            "ArkApi or AseApi compatibility names",
            "command_chat_response_path planning status",
        ):
            self.assertIn(insufficient, evidence["not_sufficient"])

        release = requirements["release.not_sufficient_for_v1"]
        for behavior in (
            "commands/replies is a blocked v1 completion surface now",
            "commands/replies is not sufficient for a complete v1 SDK claim now",
            "public_contract stays empty while status is blocked or unresolved",
            "v1_completion_required must not change because of this planning contract alone",
        ):
            self.assertIn(behavior, release["required_behavior"])

    def test_public_header_and_surface_manifest_stay_blocked(self) -> None:
        payload = self.load_decisions()
        unresolved = [
            item["id"]
            for item in payload["required_before_public_header"]
            if item.get("status") != "resolved"
        ]
        if unresolved:
            self.assertFalse(payload["public_header_allowed"])

        header = HEADER.read_text(encoding="utf-8")
        for token in FORBIDDEN_HEADER_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, header)

        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        commands = by_id["obelisk.commands_replies.v1"]
        self.assertEqual(commands["status"], "planning")
        self.assertEqual(commands["public_contract"], [])
        self.assertEqual(
            commands["depends_on"],
            [
                "obelisk.player_identity.v1",
                "obelisk.permissions_admin.v1",
                "obelisk.command_chat_response_path.v1",
            ],
        )
        self.assertIn("obelisk.commands_replies.v1", surfaces["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.commands_replies.v1", surfaces["v1_required_dependency_chain"])
        self.assertTrue(commands["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"])
        self.assertEqual(
            commands["v1_decision_contract"]["decision_manifest"],
            "docs/commands_replies_public_contract_decisions.json",
        )
        self.assertEqual(
            commands["v1_decision_contract"]["not_sufficient_evidence"],
            [
                "passive ChatMessageEvent parsing",
                "plugin-local command parser scaffold",
                "static thunk orientation",
                "candidate vtable slots",
                "raw ProcessEvent callbacks",
                "legacy CallProcessEvent debug access",
                "command_chat_response_path planning status",
            ],
        )

        response_path = by_id["obelisk.command_chat_response_path.v1"]
        self.assertEqual(
            response_path["v1_decision_contract"]["not_sufficient_evidence"],
            [
                "static thunk orientation",
                "passive ChatMessageEvent parsing",
                "candidate vtable slots",
                "raw ProcessEvent callbacks",
                "legacy CallProcessEvent debug access",
                "command copied response intent planning vocabulary",
                "command copied response intent lifecycle planning vocabulary",
            ],
        )
        self.assertIn(
            "Static thunk orientation, passive ChatMessageEvent parsing, candidate vtable slots, raw ProcessEvent callbacks, and legacy CallProcessEvent debug access are not public response-path or command/reply promotion evidence.",
            surfaces["release_guardrails"],
        )

    def test_sdk_v1_doc_links_commands_replies_decision_manifest(self) -> None:
        compatibility = (REPO_ROOT / "docs" / "SDK_V1_COMPATIBILITY.md").read_text(encoding="utf-8")

        self.assertIn(
            "[`commands_replies_public_contract_decisions.json`](commands_replies_public_contract_decisions.json)",
            compatibility,
        )
        self.assertIn(
            "passive `ChatMessageEvent` parsing, plugin-local\n"
            "command parser scaffolds, static thunk orientation, raw `ProcessEvent` callbacks,\n"
            "legacy `CallProcessEvent` debug access, and ArkApi/AseApi compatibility names are not\n"
            "sufficient command/reply evidence and cannot be cited as public response evidence",
            compatibility,
        )


if __name__ == "__main__":
    unittest.main()
