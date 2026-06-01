#!/usr/bin/env python3
"""Guardrails for the future copied command/chat response contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
DECISIONS = REPO_ROOT / "docs" / "command_chat_response_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
UFUNCTION_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"

sys.path.insert(0, str(SCRIPT_DIR))
from reflection_target_sets import TARGET_SETS  # noqa: E402

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
    "evidence.response_target_set_snapshot_second_source",
}

RESPONSE_PATH_TARGETS = {
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatDirectMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientServerChatMessage",
    "obelisk.ufunction-chain.snapshot.v1:ShooterPlayerController.ClientChatMessage",
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

    def response_target_sets(self) -> list[str]:
        return [
            name
            for name, targets in TARGET_SETS.items()
            if RESPONSE_PATH_TARGETS.issubset(set(targets))
        ]

    def committed_response_snapshots(self) -> set[str]:
        observed: set[str] = set()
        for target in RESPONSE_PATH_TARGETS:
            schema, _, qualified_name = target.partition(":")
            if any(UFUNCTION_FIXTURES.glob(f"**/{qualified_name}.snapshot.json")):
                observed.add(f"{schema}:{qualified_name}")
        return observed

    def has_accepted_response_second_source(self, evidence: dict, target_sets: list[str]) -> bool:
        accepted = evidence.get("accepted_second_source")
        if evidence.get("status") != "resolved" or not isinstance(accepted, dict):
            return False
        return (
            accepted.get("status") == "accepted"
            and accepted.get("target_set") in target_sets
            and set(accepted.get("targets", [])) == RESPONSE_PATH_TARGETS
        )

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.command-chat-response-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.command_chat_response_path.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["public_header_allowed"])
        self.assertEqual(payload["public_header_symbols_now"], [])
        self.assertFalse(payload["legacy_call_process_event_public_response_allowed"])
        self.assertFalse(payload["minimal_chat_message_event_public_response_allowed"])
        self.assertFalse(payload["raw_process_event_public_response_allowed"])
        self.assertFalse(payload["static_thunk_orientation_public_response_allowed"])
        self.assertFalse(payload["commands_replies_shortcut_public_response_allowed"])
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)
        for forbidden in (
            "principal or permission claims from command text",
            "principal or permission claims from operator config",
            "raw ProcessEvent or legacy CallProcessEvent fallback",
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
            "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish principal identity",
            "commands/replies planning cannot bypass identity promotion",
        ):
            self.assertIn(behavior, identity["required_behavior"])

        permissions = next(
            item
            for item in payload["required_before_public_header"]
            if item["id"] == "dependency.promoted_permissions_admin"
        )
        for behavior in (
            "permissions/admin must be promoted before any reply, send-chat, broadcast, or moderation delivery is public",
            "minimal ChatMessageEvent, raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot establish permissions or admin authority",
            "commands/replies planning cannot bypass permissions/admin promotion",
        ):
            self.assertIn(behavior, permissions["required_behavior"])

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
            "minimal ChatMessageEvent registration does not authorize response delivery",
            "raw ProcessEvent callbacks do not authorize response delivery",
            "static thunk orientation does not authorize response delivery",
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
            "future reply/send-chat/router response paths require owner-scoped lifecycle and unregister cleanup before public ABI",
            "raw ProcessEvent and legacy CallProcessEvent fallback do not satisfy response unregister cleanup or drain",
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
            "reply/send-chat/router response attempts require rate-limit and sanitized audit checks per plugin owner token before delivery",
            "burst exhaustion drops or rejects the response, never bypasses permission checks",
            "raw ProcessEvent and legacy CallProcessEvent fallback cannot bypass response abuse or audit gates",
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
            "minimal ChatMessageEvent callback registration",
            "passive ChatMessageEvent parsing",
            "commands/replies planning status",
            "legacy CallProcessEvent debug gate",
            "raw ProcessEvent callbacks",
        ):
            self.assertIn(insufficient, evidence["not_sufficient"])

    def test_response_path_target_evidence_chain_fails_closed_until_complete(self) -> None:
        payload = self.load_decisions()
        requirements = {item["id"]: item for item in payload["required_before_public_header"]}
        evidence = requirements["evidence.response_target_set_snapshot_second_source"]

        self.assertEqual(evidence["status"], "unresolved")
        self.assertEqual(set(evidence["required_targets"]), RESPONSE_PATH_TARGETS)
        self.assertEqual(
            set(evidence["required_evidence"]),
            {
                "named reflection target set covering all required response-path UFunctions",
                "committed sanitized UFunction snapshots for all required response-path UFunctions",
                "accepted strict second-source comparison for the same named target set and exact targets",
            },
        )
        for insufficient in (
            "static thunk orientation",
            "candidate vtable slots",
            "historical chat FName indices",
            "metadata-only passive chat observations",
            "minimal ChatMessageEvent callback registration",
            "raw ProcessEvent callbacks",
            "legacy CallProcessEvent debug gate",
            "ServerSendChatMessage chat-message-intake evidence",
        ):
            self.assertIn(insufficient, evidence["not_sufficient"])

        missing_evidence = []
        target_sets = self.response_target_sets()
        if not target_sets:
            missing_evidence.append("target-set")
        if self.committed_response_snapshots() != RESPONSE_PATH_TARGETS:
            missing_evidence.append("snapshot")
        if not self.has_accepted_response_second_source(evidence, target_sets):
            missing_evidence.append("second-source")

        if missing_evidence:
            self.assertEqual(payload["status"], "blocked", missing_evidence)
            self.assertFalse(payload["public_header_allowed"], missing_evidence)
            self.assertEqual(payload["public_header_symbols_now"], [], missing_evidence)
        self.assertFalse(payload["legacy_call_process_event_public_response_allowed"], missing_evidence)

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
        self.assertEqual(response_path["status"], "planning")
        self.assertEqual(response_path["public_contract"], [])
        self.assertEqual(
            response_path["depends_on"],
            ["obelisk.player_identity.v1", "obelisk.permissions_admin.v1"],
        )
        self.assertIn("obelisk.command_chat_response_path.v1", surfaces["v1_sdk_completion_blockers"])
        self.assertIn("obelisk.command_chat_response_path.v1", surfaces["v1_required_dependency_chain"])
        self.assertEqual(
            response_path["v1_decision_contract"]["decision_manifest"],
            "docs/command_chat_response_public_contract_decisions.json",
        )
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
                "minimal ChatMessageEvent remains passive input and cannot route replies/send-chat/broadcast/moderation",
                "generic chat routing cannot bypass promoted identity and permissions/admin",
                "chat intake is observation only and cannot become identity, permission, command authority, moderation authority, targeting, or roadmap priority",
                "raw ProcessEvent, legacy CallProcessEvent, and static thunk orientation cannot bypass identity and permissions/admin",
                "commands/replies remains blocked until command_chat_response_path is promoted or explicitly excluded",
            ],
        )
        for exclusion in (
            "command router",
            "command registration API",
            "commands/replies shortcut before identity and permissions/admin",
            "public response path through ChatMessageEvent",
            "public response path through raw ProcessEvent",
            "public response path through generic chat routing",
            "public response path through static thunk orientation",
            "reply/send-chat/broadcast/moderation through legacy CallProcessEvent",
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
