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

    def test_privacy_and_lifetime_blockers_have_machine_readable_contracts(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        public_form = requirements["privacy.public_identifier_form"]
        self.assertIn("generation-bearing or otherwise invalidation-aware", public_form["required_properties"])
        for forbidden in ("SteamID", "EOS ID", "PlayerDataID", "player name", "UE pointer", "ResourceHandle"):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, public_form["must_not_expose"])

        redaction = requirements["privacy.redacted_identifier_fields"]
        self.assertEqual(
            set(redaction["allowed_field_classes"]),
            {"copied opaque principal", "recognition-only", "private-redacted", "forbidden"},
        )
        self.assertIn("controller/playerstate object references", redaction["must_redact"])

        logging_policy = requirements["privacy.logging_and_storage_policy"]
        self.assertEqual(logging_policy["default_policy"], "no identity persistence and no raw identity logging")
        self.assertIn("operator ingress/storage surface promotion", logging_policy["requires_before_persistence"])

        scope = requirements["lifetime.principal_scope"]
        self.assertEqual(set(scope["allowed_scopes"]), {"callback-local", "process-local", "restart-local"})
        self.assertIn("cluster-stable", scope["forbidden_until_separate_promotion"])
        self.assertEqual(set(scope["required_fields"]), {"principal_handle", "principal_generation", "scope_flags"})

        invalidation = requirements["lifetime.invalidation_events"]
        self.assertEqual(
            set(invalidation["required_invalidation_events"]),
            {
                "disconnect",
                "logout",
                "transfer",
                "reconnect",
                "duplicate principal observation",
                "server restart",
                "stale controller/playerstate",
                "failed evidence validation",
            },
        )
        self.assertIn("stale principal fails closed", invalidation["required_behavior"])

        stale_policy = requirements["lifetime.reconnect_duplicate_stale_policy"]
        self.assertIn("stale handles never resolve to a different player", stale_policy["required_policy"])
        self.assertIn("lookup-by-public-handle remains unavailable unless separately promoted", stale_policy["required_policy"])

    def test_sequence_gate_keeps_downstream_surfaces_out_of_identity(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }
        separation = requirements["separation.no_commands_permissions_persistence"]

        self.assertEqual(
            separation["v1_sequence_gate"],
            [
                "identity principal contract first",
                "permission query contract only after identity promotion",
                "command response contract only after permission result provenance is promoted",
                "commands/replies only after command response privacy, generation, and scope gates are promoted",
            ],
        )
        for forbidden in (
            "permission query API",
            "permission cache API",
            "command response API",
            "command router",
            "replies/send-chat",
            "admin mutation",
            "storage/persistence",
            "operator ingress",
        ):
            self.assertIn(forbidden, separation["forbidden_in_identity_contract"])

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

    def test_approved_runtime_evidence_intake_is_machine_readable_but_not_promoting(self) -> None:
        payload = self.load_decisions()
        intake = payload["approved_runtime_evidence_intake"]

        self.assertEqual(intake["id"], "approved_runtime_principal_lifecycle_evidence")
        self.assertEqual(intake["status"], "external_manifest_required")
        self.assertEqual(intake["resolved_input"], "runtime.lifecycle_evidence")
        self.assertFalse(intake["promotion_ready"])
        self.assertFalse(intake["public_sdk_ready"])
        self.assertFalse(intake["runtime_ready"])
        self.assertFalse(intake["public_header_allowed"])
        self.assertEqual(
            intake["required_checker"],
            "scripts/check_player_identity_public_contract_readiness.py",
        )

    def test_runtime_evidence_intake_test_is_covered_without_promotion(self) -> None:
        payload = self.load_decisions()
        tests = {
            item["id"]: item
            for item in payload["required_tests_before_public_header"]
        }
        runtime_intake = tests["runtime.evidence_intake"]

        self.assertEqual(runtime_intake["status"], "covered")
        self.assertEqual(runtime_intake["coverage_status"], "contract_review_input_only")
        self.assertFalse(runtime_intake["promotion_ready"])
        self.assertFalse(runtime_intake["public_sdk_ready"])
        self.assertFalse(runtime_intake["runtime_ready"])
        self.assertFalse(runtime_intake["public_header_allowed"])
        self.assertEqual(
            set(runtime_intake["covered_by"]),
            {
                "scripts/check_player_identity_public_contract_readiness.py",
                "scripts/test_check_player_identity_public_contract_readiness.py",
                "scripts/test_player_identity_public_contract_decisions.py",
            },
        )

        for test_id, item in tests.items():
            if test_id != "runtime.evidence_intake":
                with self.subTest(test_id=test_id):
                    self.assertEqual(item["status"], "missing")


if __name__ == "__main__":
    unittest.main()
