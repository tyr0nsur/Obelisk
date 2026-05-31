#!/usr/bin/env python3
"""Guardrails for the future copied player identity contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_IDS = {
    "evidence.complete_non_protected_pack",
    "evidence.accepted_session_start_anchor",
    "evidence.accepted_session_end_anchor",
    "evidence.second_source_anchor_layout",
    "privacy.public_identifier_form",
    "privacy.redacted_identifier_fields",
    "privacy.logging_and_storage_policy",
    "lifetime.principal_scope",
    "lifetime.invalidation_events",
    "lifetime.reconnect_duplicate_stale_policy",
    "abi.payload_shape",
    "abi.capability_bits",
    "abi.owner_token_registration",
    "abi.append_only_layout_tests",
    "separation.no_commands_permissions_persistence",
}

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS",
    "OBELISK_PLAYER_IDENTITY_EVENT_ABI_VERSION",
    "ObeliskPlayerIdentity",
    "ObeliskPlayerPrincipal",
    "ObeliskPlayerId",
    "ObeliskPlayerHandle",
    "RegisterPlayerIdentity",
    "UnregisterPlayerIdentity",
    "DescribePlayerIdentity",
    "ResolvePlayerIdentity",
}


class PlayerIdentityPublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.player-identity-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.player_identity.v1")
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)

    def test_public_header_stays_blocked_until_all_decisions_are_resolved(self) -> None:
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

    def test_surface_manifest_still_has_no_public_identity_contract(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        identity = by_id["obelisk.player_identity.v1"]
        self.assertEqual(identity["status"], "planning")
        self.assertEqual(identity["public_contract"], [])
        self.assertIn("obelisk.player_identity.v1", surfaces["v1_sdk_completion_blockers"])


if __name__ == "__main__":
    unittest.main()
