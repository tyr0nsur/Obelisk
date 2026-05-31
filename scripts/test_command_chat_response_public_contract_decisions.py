#!/usr/bin/env python3
"""Guardrails for the future copied command/chat response contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_IDS = {
    "dependency.promoted_player_identity",
    "dependency.promoted_permissions_admin",
    "abi.copied_response_payload",
    "abi.capability_and_owner_token",
    "lifecycle.owner_scoped_unregister_and_drain",
    "privacy.redaction_and_targeting",
    "abuse.rate_limit_and_audit",
    "separation.no_commands_router_or_moderation",
    "evidence.layout_runtime_sdk_coverage",
}

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_COMMAND_CHAT_RESPONSE",
    "OBELISK_API_CAPABILITY_CHAT_REPLIES",
    "OBELISK_API_CAPABILITY_SEND_CHAT",
    "OBELISK_COMMAND_CHAT_RESPONSE_ABI_VERSION",
    "ObeliskCommandChatResponse",
    "ObeliskChatReply",
    "ObeliskSendChat",
    "RegisterCommandChatResponse",
    "SendChatWithOwnerToken",
    "ReplyToChatWithOwnerToken",
}


class CommandChatResponsePublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.command-chat-response-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.command_chat_response_path.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["public_header_allowed"])
        self.assertEqual(payload["public_header_symbols_now"], [])
        self.assertFalse(payload["legacy_call_process_event_public_response_allowed"])
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)
        for forbidden in (
            "principal or permission claims from command text",
            "principal or permission claims from operator config",
        ):
            self.assertIn(forbidden, payload["forbidden_public_contract"])

        identity = next(
            item
            for item in payload["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        for behavior in (
            "runtime observation establishes principal identity before command/chat response can consume it",
            "command text cannot establish principal identity",
            "operator config enables surfaces only and cannot establish principal identity",
            "response delivery never creates identity or permission claims",
        ):
            self.assertIn(behavior, identity["required_behavior"])

    def test_copied_response_abi_blocks_raw_ue_and_legacy_debug_paths(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        response = requirements["abi.copied_response_payload"]
        self.assertEqual(
            set(response["required_fields_or_equivalent"]),
            {
                "abi_version",
                "struct_size",
                "plugin_owner_token",
                "response_handle",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "response_kind",
                "message_utf8",
                "message_size",
                "delivery_scope",
                "delivery_flags",
            },
        )
        for property_name in (
            "POD C ABI",
            "runtime-owned delivery path",
            "no raw UE pointers or raw params",
            "no raw FString exposure",
            "no public UFunction or vtable details",
        ):
            self.assertIn(property_name, response["required_properties"])

        capability = requirements["abi.capability_and_owner_token"]
        for behavior in (
            "missing capability fails closed",
            "missing or zero plugin_owner_token fails closed",
            "captured post-init debug CallProcessEvent tables do not authorize response delivery",
            "all response handles are owner-scoped",
        ):
            self.assertIn(behavior, capability["required_behavior"])

    def test_lifecycle_privacy_and_abuse_gates_are_explicit(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}

        lifecycle = requirements["lifecycle.owner_scoped_unregister_and_drain"]
        for behavior in (
            "owner unregister cancels pending responses for that plugin owner",
            "plugin init failure cleans up registered response handles before dlclose",
            "plugin unload waits for in-flight response callbacks or fails closed without dlclose",
            "response callbacks cannot outlive copied payload storage",
        ):
            self.assertIn(behavior, lifecycle["required_behavior"])

        privacy = requirements["privacy.redaction_and_targeting"]
        for behavior in (
            "stale principal fails closed",
            "missing established runtime principal fails closed",
            "command text principal claims fail closed",
            "operator config principal claims fail closed",
            "principal generation mismatch fails closed",
            "unsupported scope fails closed",
            "private identity fields are not logged",
            "cross-instance routing is forbidden until separately promoted",
        ):
            self.assertIn(behavior, privacy["required_behavior"])

        abuse = requirements["abuse.rate_limit_and_audit"]
        for behavior in (
            "response attempts are rate-limited per plugin owner token",
            "burst exhaustion drops or rejects the response, never bypasses permission checks",
            "malformed UTF-8 or oversize messages fail closed",
            "operator controls can disable response delivery without disabling passive chat intake",
        ):
            self.assertIn(behavior, abuse["required_behavior"])

    def test_static_orientation_and_passive_chat_are_not_sufficient_evidence(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}
        evidence = requirements["evidence.layout_runtime_sdk_coverage"]

        self.assertEqual(
            set(evidence["required_evidence"]),
            {
                "promoted player identity evidence",
                "promoted permissions/admin evidence",
                "copied response ABI layout tests",
                "SDK consumer tests",
                "isolated runtime delivery evidence",
                "second-source or independently reviewed response target evidence",
            },
        )
        for insufficient in (
            "static thunk orientation",
            "candidate vtable slots",
            "passive ChatMessageEvent parsing",
            "legacy CallProcessEvent debug gate",
            "raw ProcessEvent callbacks",
        ):
            self.assertIn(insufficient, evidence["not_sufficient"])

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
        response_path = by_id["obelisk.command_chat_response_path.v1"]
        self.assertEqual(response_path["status"], "post-v1")
        self.assertEqual(response_path["public_contract"], [])
        self.assertEqual(
            response_path["depends_on"],
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
        )
        self.assertIn("obelisk.command_chat_response_path.v1", surfaces["v1_sdk_completion_blockers"])
        self.assertTrue(response_path["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"])

    def test_scope_separation_excludes_command_router_and_moderation(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}
        separation = requirements["separation.no_commands_router_or_moderation"]
        self.assertEqual(
            separation["v1_sequence_gate"],
            [
                "promoted player identity is required before command/chat response principals",
                "promoted query-only permissions/admin is required before directed responses",
                "copied command/chat response semantics may be defined only after identity and permissions/admin promotion",
                "commands/replies remains blocked until command_chat_response_path is promoted or explicitly excluded",
            ],
        )
        for exclusion in (
            "command router",
            "command registration API",
            "console command API",
            "RCON command API",
            "moderation API",
            "ban/kick API",
            "operator ingress",
            "storage/persistence",
        ):
            self.assertIn(exclusion, separation["required_exclusions"])


if __name__ == "__main__":
    unittest.main()
