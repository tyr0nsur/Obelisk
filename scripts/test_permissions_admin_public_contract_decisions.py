#!/usr/bin/env python3
"""Guardrails for the future copied permissions/admin contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_IDS = {
    "dependency.promoted_player_identity",
    "identity.principal_generation_required",
    "identity.principal_scope_compatibility",
    "abi.permission_query_identity_fields",
    "cache.generation_scope_keying",
    "fail_closed.stale_or_scope_mismatch",
    "separation.no_commands_replies_or_admin_mutation",
}

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
    "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
    "OBELISK_PERMISSION_QUERY_ABI_VERSION",
    "ObeliskPermissionQuery",
    "ObeliskPermissionDecision",
    "CheckPermissionWithOwnerToken",
    "RegisterPermission",
    "GrantPermission",
    "RevokePermission",
}


class PermissionsAdminPublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.permissions-admin-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.permissions_admin.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["public_header_allowed"])
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)

    def test_generation_scope_and_cache_contracts_are_machine_readable(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        generation = requirements["identity.principal_generation_required"]
        self.assertIn("principal_handle alone never authorizes", generation["required_behavior"])
        self.assertIn("missing generation fails closed", generation["required_behavior"])
        self.assertIn("generation mismatch returns deny or unknown, never allow", generation["required_behavior"])

        scope = requirements["identity.principal_scope_compatibility"]
        self.assertEqual(set(scope["allowed_initial_scopes"]), {"callback-local", "process-local"})
        self.assertIn("cluster-stable", scope["forbidden_until_separate_promotion"])
        self.assertIn("unsupported principal scope fails closed", scope["required_behavior"])
        self.assertIn("process mismatch fails closed", scope["required_behavior"])

        abi = requirements["abi.permission_query_identity_fields"]
        self.assertEqual(
            set(abi["required_fields_or_equivalent"]),
            {
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "action",
                "action_size",
                "resource_scope",
                "resource_scope_size",
            },
        )
        self.assertIn("owner-token scoped call", abi["required_properties"])
        self.assertIn("no UE pointers or raw params", abi["required_properties"])

        cache = requirements["cache.generation_scope_keying"]
        self.assertIn("principal_generation", cache["required_cache_key_fields"])
        self.assertIn("principal_scope_flags", cache["required_cache_key_fields"])
        self.assertIn("policy_epoch", cache["required_cache_key_fields"])
        self.assertIn("cache disabled unless all key fields are defined", cache["required_behavior"])

    def test_fail_closed_and_scope_separation_remain_explicit(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        fail_closed = requirements["fail_closed.stale_or_scope_mismatch"]
        for condition in (
            "missing principal_generation",
            "mismatched principal_generation",
            "unsupported principal_scope_flags",
            "stale principal",
            "process mismatch",
            "missing plugin owner token",
            "missing capability",
        ):
            self.assertIn(condition, fail_closed["deny_or_unknown_conditions"])
        self.assertIn("unknown authority source", fail_closed["must_never_return_allow_for"])

        separation = requirements["separation.no_commands_replies_or_admin_mutation"]
        for exclusion in ("command router", "replies/send-chat", "ban/kick", "groups/grants", "operator ingress"):
            self.assertIn(exclusion, separation["required_exclusions"])

    def test_public_header_stays_blocked_until_permissions_decisions_resolve(self) -> None:
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

    def test_surface_manifest_requires_generation_scope_and_fail_closed_permissions(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        permissions = by_id["obelisk.permissions_admin.v1"]
        self.assertEqual(permissions["status"], "post-v1")
        self.assertEqual(permissions["public_contract"], [])
        self.assertEqual(permissions["depends_on"], ["obelisk.player_identity.v1"])

        promotion_requires = " ".join(permissions["v1_decision_contract"]["promotion_requires"])
        for term in (
            "principal_generation",
            "principal_scope_flags",
            "stale principal",
            "scope mismatch",
            "query-only fail-closed permission checks",
        ):
            self.assertIn(term, promotion_requires)


if __name__ == "__main__":
    unittest.main()
