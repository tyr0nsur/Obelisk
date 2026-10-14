#!/usr/bin/env python3
"""Guardrails for the future copied permissions/admin contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
NOTE = REPO_ROOT / "docs" / "research" / "2026-05-31-permissions-admin-minimum-post-identity.md"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_IDS = {
    "dependency.promoted_player_identity",
    "identity.principal_generation_required",
    "identity.principal_scope_compatibility",
    "abi.permission_query_identity_fields",
    "cache.generation_scope_keying",
    "policy.authority_provenance_required",
    "abuse.query_rate_limit_and_audit_gate",
    "fail_closed.stale_or_scope_mismatch",
    "separation.no_commands_replies_or_admin_mutation",
}

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_ADMIN",
    "OBELISK_API_CAPABILITY_AUTHORIZATION",
    "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
    "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
    "OBELISK_PERMISSION_CACHE_ABI_VERSION",
    "OBELISK_PERMISSION_QUERY_ABI_VERSION",
    "ObeliskAdminAction",
    "ObeliskAuthorizationDecision",
    "ObeliskPermissionCache",
    "ObeliskPermissionQuery",
    "ObeliskPermissionDecision",
    "AuthorizePermission",
    "CheckPermissionWithOwnerToken",
    "CheckPermissionCachedWithOwnerToken",
    "RegisterPermission",
    "GrantPermission",
    "RevokePermission",
    "BanPlayer",
    "KickPlayer",
}


class PermissionsAdminPublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def load_identity_decisions(self) -> dict:
        return json.loads(IDENTITY_DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.permissions-admin-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.permissions_admin.v1")
        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["public_header_allowed"])
        self.assertEqual(payload["public_header_symbols_now"], [])
        self.assertFalse(payload["public_cache_abi_allowed"])
        self.assertEqual(
            payload["allowed_public_surface_after_player_identity"],
            ["query-only fail-closed permission decision checks over copied principals"],
        )
        post_identity = payload["post_identity_next_requirement"]
        self.assertEqual("public_header_gate_missing", post_identity["route_blocker_to_use"])
        self.assertFalse(post_identity["identity_alias_or_stale_source_unlock_allowed"])
        self.assertFalse(post_identity["runtime_evidence_alone_unlock_allowed"])
        self.assertFalse(payload["allow_without_policy_provenance_allowed"])
        self.assertEqual(payload["public_permission_cache_contract"], "none")
        self.assertEqual(payload["public_command_reply_contract"], "none")
        self.assertEqual(payload["public_admin_mutation_contract"], "none")
        self.assertEqual(payload["allow_capable_authority_ownership"], "runtime-local/runtime-owned-only")
        self.assertFalse(payload["operator_config_allow_capable"])
        for forbidden in (
            "permission groups",
            "admin groups",
            "grant/revoke API",
            "admin actions",
            "admin mutation",
            "permission cache ABI",
            "command/chat response path",
            "replies/send-chat",
            "principal or permission claims from command text",
            "principal or permission claims from operator config",
            "allow without provenance",
            "public header symbols",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, payload["forbidden_public_contract"])
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)

        dependency = next(
            item
            for item in payload["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )
        for behavior in (
            "before player identity is promoted, permissions/admin exposes no public ABI, callbacks, cache ABI, command/reply implication, or header symbols",
            "player identity planning evidence alone cannot enable permissions/admin",
            "RCON, ListPlayers, Kick, ServerListPlayers, ServerKickPlayer, admin snapshots, static thunk, route candidate, source-ready, status, and command aliases are admin orientation or operational metadata only and cannot unlock permissions/admin public readiness, runtime readiness, route state, or SDK/P0 progress",
            "admin_kind, alias_source, source_alias, status_source, ListPlayers, Kick, RCON, admin snapshots, source-ready, and status alias records require the current hash-bound player-identity promotion certificate before any route, readiness, or SDK/P0 accounting claim; without it they fail closed and remain non-counting",
            "runtime observation must establish principal identity before permissions/admin can consume it",
            "operator config enables surfaces or policy inputs only and cannot establish principal identity",
            "command text cannot establish principal identity",
            "permissions/admin remains post-v1 or excluded until this dependency is promoted or explicitly excluded",
        ):
            self.assertIn(behavior, dependency["required_behavior"])

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
                "plugin_owner_token",
                "principal_handle",
                "principal_generation",
                "principal_scope_flags",
                "server_process_epoch",
                "action",
                "action_size",
                "resource_scope",
                "resource_scope_size",
                "request_flags",
            },
        )
        self.assertIn("owner-token scoped call", abi["required_properties"])
        self.assertIn("query-only result contract only", abi["required_properties"])
        self.assertIn("action bytes are required, copied, and bounded to 128 bytes before allow", abi["required_properties"])
        self.assertIn("resource_scope bytes are optional, copied, and bounded to 256 bytes before allow", abi["required_properties"])
        self.assertIn("no command parser compatibility claim from action or resource_scope bytes", abi["required_properties"])
        self.assertIn("no UTF-8 or text decoding claim before a separate reviewed parser contract", abi["required_properties"])
        self.assertIn("no mutation of permission policy or admin state", abi["required_properties"])
        self.assertIn("no command/reply handles", abi["required_properties"])
        self.assertIn("no UE pointers or raw params", abi["required_properties"])

        cache = requirements["cache.generation_scope_keying"]
        self.assertIn("principal_generation", cache["required_cache_key_fields"])
        self.assertIn("principal_scope_flags", cache["required_cache_key_fields"])
        self.assertIn("resource_scope", cache["required_cache_key_fields"])
        self.assertIn("policy_epoch", cache["required_cache_key_fields"])
        self.assertEqual(
            cache["public_cache_abi"],
            "blocked_until_policy_epoch_generation_and_scope_semantics_are_promoted",
        )
        self.assertIn(
            "no public permission cache ABI until policy_epoch and full generation/scope keying semantics are promoted",
            cache["required_behavior"],
        )
        self.assertIn("cache keys or entries must not cross the public ABI", cache["required_behavior"])
        self.assertIn("cache disabled unless all key fields are defined", cache["required_behavior"])

    def test_policy_authority_provenance_and_abuse_gates_are_explicit(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        provenance = requirements["policy.authority_provenance_required"]
        self.assertEqual(
            set(provenance["required_fields_or_equivalent"]),
            {
                "policy_source_id",
                "policy_source_generation",
                "authority_kind",
                "authority_generation",
                "policy_epoch",
            },
        )
        self.assertEqual(set(provenance["allowed_initial_authority_kinds"]), {"operator-config", "runtime-local"})
        self.assertEqual(provenance["allow_capable_authority_ownership"], "runtime-owned")
        self.assertFalse(provenance["operator_config_allow_capable"])
        self.assertTrue(provenance["runtime_local_authority_must_be_runtime_owned"])
        for authority in (
            "plugin-supplied-authority",
            "remote-service-authority",
            "cross-process-shared-authority",
        ):
            self.assertIn(authority, provenance["forbidden_until_separate_promotion"])
        for behavior in (
            "missing policy source fails closed",
            "unknown authority kind fails closed",
            "missing policy_epoch provenance fails closed",
            "policy source generation mismatch fails closed",
            "authority generation mismatch fails closed",
            "allow decisions must carry policy_epoch provenance",
            "allow without policy provenance is forbidden",
            "operator-config authority can provide runtime-owned policy inputs only and cannot produce allow",
            "runtime-local authority must be runtime-owned before it can produce allow",
            "runtime-local authority without runtime-owned provenance fails closed",
            "operator-config cannot establish principal identity or permission claims before runtime principal observation",
            "command text cannot establish principal identity, permission authority, or policy provenance",
            "permission authority derives only from an established runtime principal plus runtime-owned provenance",
            "plugin input cannot self-attest authority provenance",
        ):
            self.assertIn(behavior, provenance["required_behavior"])

        abuse = requirements["abuse.query_rate_limit_and_audit_gate"]
        for behavior in (
            "permission queries are rate-limited per plugin owner token",
            "burst exhaustion returns deny or unknown, never allow",
            "abuse counters are process-local and owner-scoped",
            "repeated malformed queries are observable through runtime logs or counters",
            "audit records must not expose UE pointers, raw params, or secret policy contents",
            "rate-limit state is not a public cache ABI",
        ):
            self.assertIn(behavior, abuse["required_behavior"])

    def test_fail_closed_and_scope_separation_remain_explicit(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        fail_closed = requirements["fail_closed.stale_or_scope_mismatch"]
        for condition in (
            "missing principal_generation",
            "missing runtime principal identity",
            "command text principal claim",
            "operator config principal claim",
            "mismatched principal_generation",
            "unsupported principal_scope_flags",
            "stale principal",
            "process mismatch",
            "unknown policy source",
            "missing policy source provenance",
            "missing policy_epoch provenance",
            "policy source generation mismatch",
            "runtime-local authority without runtime-owned provenance",
            "operator-config authority before separate allow-capable promotion",
            "missing plugin owner token",
            "missing capability",
            "rate limit exceeded",
        ):
            self.assertIn(condition, fail_closed["deny_or_unknown_conditions"])
        self.assertIn("unknown authority source", fail_closed["must_never_return_allow_for"])
        self.assertIn("missing policy source provenance", fail_closed["must_never_return_allow_for"])
        self.assertIn("missing runtime principal identity", fail_closed["must_never_return_allow_for"])
        self.assertIn("command text principal claim", fail_closed["must_never_return_allow_for"])
        self.assertIn("operator config principal claim", fail_closed["must_never_return_allow_for"])
        self.assertIn("allow without policy_epoch provenance", fail_closed["must_never_return_allow_for"])
        self.assertIn(
            "operator-config authority before separate allow-capable promotion",
            fail_closed["must_never_return_allow_for"],
        )
        self.assertIn(
            "runtime-local authority without runtime-owned provenance",
            fail_closed["must_never_return_allow_for"],
        )
        self.assertIn("plugin-supplied provenance", fail_closed["must_never_return_allow_for"])
        self.assertIn("rate limit exceeded", fail_closed["must_never_return_allow_for"])

        separation = requirements["separation.no_commands_replies_or_admin_mutation"]
        self.assertEqual(
            separation["v1_sequence_gate"],
            [
                "promoted player identity is required before permission checks",
                "query-only permission result provenance is required before command response",
                "command response privacy, generation, and scope policy is required before commands/replies",
                "commands/replies cannot imply permission groups, admin mutation, storage, or operator ingress",
            ],
        )
        for exclusion in (
            "command router",
            "command/chat response path",
            "replies/send-chat",
            "ban/kick",
            "admin actions",
            "groups/grants",
            "permission cache ABI",
            "operator ingress",
        ):
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

    def test_permissions_admin_stays_locked_while_player_identity_is_blocked(self) -> None:
        identity = self.load_identity_decisions()
        permissions = self.load_decisions()
        dependency = next(
            item
            for item in permissions["required_before_public_header"]
            if item["id"] == "dependency.promoted_player_identity"
        )

        self.assertEqual(identity["surface"], "obelisk.player_identity.v1")
        self.assertEqual(identity["status"], "blocked")
        self.assertFalse(identity["public_header_allowed"])
        self.assertEqual(identity["public_header_symbols_now"], [])

        self.assertEqual(permissions["surface"], "obelisk.permissions_admin.v1")
        self.assertEqual(permissions["status"], "blocked")
        self.assertFalse(permissions["public_header_allowed"])
        self.assertEqual(permissions["public_header_symbols_now"], [])
        self.assertFalse(permissions["public_cache_abi_allowed"])
        self.assertEqual(permissions["public_permission_cache_contract"], "none")
        self.assertEqual(permissions["public_command_reply_contract"], "none")
        self.assertEqual(permissions["public_admin_mutation_contract"], "none")
        self.assertEqual(dependency["status"], "unresolved")
        self.assertEqual(
            dependency["decision_required"],
            "Promote obelisk.player_identity.v1 before any permission check API is public.",
        )
        self.assertIn(
            "player identity planning evidence alone cannot enable permissions/admin",
            dependency["required_behavior"],
        )

    def test_note_and_decision_manifest_share_minimum_query_field_names(self) -> None:
        payload = self.load_decisions()
        note = NOTE.read_text(encoding="utf-8")
        normalized_note = " ".join(note.split())
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }
        query_fields = requirements["abi.permission_query_identity_fields"]["required_fields_or_equivalent"]
        cache_fields = requirements["cache.generation_scope_keying"]["required_cache_key_fields"]

        for field in query_fields:
            with self.subTest(field=field):
                self.assertIn(field, normalized_note)

        for field in ("principal_generation", "principal_scope_flags", "resource_scope", "policy_epoch"):
            with self.subTest(cache_field=field):
                self.assertIn(field, cache_fields)
                self.assertIn(field, normalized_note)

        self.assertIn("request_flags", query_fields)
        self.assertIn("request_flags", normalized_note)

        self.assertIn("no public permission cache ABI", normalized_note)
        self.assertIn("does not add public headers", normalized_note)
        self.assertIn("public ABI symbols, headers", normalized_note)

    def test_surface_manifest_requires_generation_scope_and_fail_closed_permissions(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        permissions = by_id["obelisk.permissions_admin.v1"]
        self.assertEqual(permissions["status"], "planning")
        self.assertEqual(permissions["public_contract"], [])
        self.assertEqual(permissions["depends_on"], ["obelisk.player_identity.v1"])
        self.assertIn("obelisk.permissions_admin.v1", surfaces["v1_required_dependency_chain"])
        self.assertEqual(
            permissions["v1_decision_contract"]["decision_manifest"],
            "docs/permissions_admin_public_contract_decisions.json",
        )
        for not_sufficient in (
            "player identity planning without promoted player identity",
            "permission cache sketches",
            "command/reply planning",
            "plugin-local command parser scaffolds",
            "static admin thunk orientation",
            "raw ProcessEvent callbacks",
        ):
            self.assertIn(not_sufficient, permissions["v1_decision_contract"]["not_sufficient_evidence"])

        promotion_requires = " ".join(permissions["v1_decision_contract"]["promotion_requires"])
        for term in (
            "principal_generation",
            "principal_scope_flags",
            "stale principal",
            "scope mismatch",
            "query-only fail-closed permission checks",
            "missing policy provenance fail closed",
            "allow without provenance is forbidden",
            "no public permission cache ABI",
            "no permission groups",
            "admin groups",
            "grant/revoke API",
            "admin actions",
            "command/chat response path",
            "replies/send-chat implication",
        ):
            self.assertIn(term, promotion_requires)

    def test_unresolved_pre_header_decisions_are_reflected_in_public_surface_contract(self) -> None:
        decisions = self.load_decisions()
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}
        permissions = by_id["obelisk.permissions_admin.v1"]

        unresolved_ids = {
            item["id"]
            for item in decisions["required_before_public_header"]
            if item.get("status") != "resolved"
        }
        self.assertEqual(unresolved_ids, REQUIRED_IDS)
        self.assertTrue(permissions["v1_decision_contract"]["must_remain_without_public_contract_until_promotion"])
        self.assertEqual(permissions["public_contract"], [])

        surface_contract = " ".join(
            json.dumps(
                {
                    "v1_decision_contract": permissions["v1_decision_contract"],
                    "blockers": permissions["blockers"],
                    "exclusions": permissions["exclusions"],
                },
                sort_keys=True,
            ).split()
        )
        for term in (
            "player identity",
            "principal_generation",
            "principal_scope_flags",
            "stale principal",
            "scope mismatch",
            "unknown authority source",
            "owner token",
            "capability",
            "policy",
            "abuse controls",
            "privacy boundaries",
            "allow without provenance",
            "permission cache ABI",
            "command router",
            "command/chat response path",
            "replies/send-chat",
            "admin actions",
            "admin mutation",
            "ban/kick API",
            "storage/persistence",
            "operator ingress",
            "public header permission symbols",
        ):
            with self.subTest(term=term):
                self.assertIn(term, surface_contract)


if __name__ == "__main__":
    unittest.main()
