#!/usr/bin/env python3
"""Validate permissions/admin public readiness remains blocked/planning-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_permissions_admin_query_failclosed_contract as query_failclosed_contract
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DECISIONS = REPO_ROOT / "docs" / "permissions_admin_public_contract_decisions.json"
DEFAULT_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_QUERY_FAILCLOSED_CONTRACT = (
    REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
)
DEFAULT_PUBLIC_HEADER_DECL = "include/obelisk/ObeliskApi.h"

REPORT_SCHEMA = "obelisk.permissions-admin-public-readiness-check.v1"
NEXT_STEPS_SCHEMA = "obelisk.permissions-admin-public-next-steps.v1"
DECISIONS_SCHEMA = "obelisk.permissions-admin-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
QUERY_CONTRACT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract.v1"
QUERY_CONTRACT_REPORT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract-check.v1"
BETA_CAPTURE_CANDIDATES_SCHEMA = "obelisk.permissions-admin-beta-capture-candidates.v1"
SURFACE = "obelisk.permissions_admin.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"
COMMAND_RESPONSE_SURFACE = "obelisk.command_chat_response_path.v1"
COMMANDS_REPLIES_SURFACE = "obelisk.commands_replies.v1"
REQUIRED_P0_CHAIN = [IDENTITY_SURFACE, SURFACE, COMMAND_RESPONSE_SURFACE, COMMANDS_REPLIES_SURFACE]
BLOCKED_BEHIND_SURFACES = [IDENTITY_SURFACE]
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
ALLOWED_ROUTE_BLOCKERS = (
    "approved_runtime_evidence_missing",
    "identity_public_contract_gate_missing",
    "public_header_gate_missing",
)
RUNTIME_EVIDENCE_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
IDENTITY_CONTRACT_ROUTE_BLOCKER = "identity_public_contract_gate_missing"
PUBLIC_HEADER_ROUTE_BLOCKER = "public_header_gate_missing"
POST_IDENTITY_QUERY_ONLY_DIAGNOSTICS_SCHEMA = (
    "obelisk.permissions-admin-post-identity-query-only-diagnostics.v1"
)
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA = "obelisk.player-identity-promotion-certificate.v1"
PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.player-identity-promotion-certificate-build-report.v1"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA = (
    "obelisk.permissions-admin-promotion-certificate.v1"
)
PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA = (
    "obelisk.permissions-admin-promotion-certificate-build-report.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_TEMPLATE_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record-template.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_BUILD_REPORT_SCHEMA = (
    "obelisk.player-identity-public-contract-decision-record-build-report.v1"
)
PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID = "reviewed_identity_public_contract_decision_record"
PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT = "runtime.lifecycle_evidence"
PLAYER_PRINCIPAL_LIFECYCLE_NEXT_ACTION_PLAN_SCHEMA = "obelisk.player-principal-lifecycle-next-action-plan.v1"
PLAYER_PRINCIPAL_LIFECYCLE_RUNTIME_EVIDENCE_STATUS_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
)
APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA = (
    "obelisk.player-identity-public-contract-approved-runtime-evidence-binding.v1"
)
APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE = "reviewed_identity_public_contract_review"
APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT = "runtime.lifecycle_evidence"
APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS = (
    "public_header_api_abi_sdk_runtime_shortcut_allowed",
    "counts_toward_public_sdk",
    "counts_toward_p0_dependency_chain_claim",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "v1_completion_evidence",
)
APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES = {
    "schema": APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
    "accepted_for_contract_review": True,
    "resolved_input": APPROVED_RUNTIME_EVIDENCE_BINDING_RESOLVED_INPUT,
    "next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
    "binding_scope": APPROVED_RUNTIME_EVIDENCE_BINDING_SCOPE,
}
APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS = frozenset(
    {
        *APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES,
        *APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS,
        "non_claim",
    }
)
ACCEPTED_RUNTIME_EVIDENCE_REQUIRED_KEYS = frozenset(
    {
        "schema",
        "result",
        "next_blocker",
        "approved_runtime_evidence_binding_required",
        "approved_runtime_evidence_binding",
    }
)
QUERY_ONLY_ALIAS_ARTIFACTS = frozenset(
    (
        "permission_query_candidate",
        "permission_query_planning",
        "permissions_admin_query_candidate",
        "permissions_admin_query_planning",
        "permissions_query_candidate",
        "permissions_query_planning",
        "query_failclosed_candidate",
        "query_failclosed_planning",
        "query_only_candidate",
        "query_only_diagnostic",
        "query_only_diagnostics",
        "query_only_planning",
        "post_identity_query_only_diagnostics",
    )
)
QUERY_ONLY_CANDIDATE_ALIAS_ARTIFACTS = frozenset(
    (
        "permission_query_candidate",
        "permissions_admin_query_candidate",
        "permissions_query_candidate",
        "query_failclosed_candidate",
        "query_failclosed_planning",
        "query_only_candidate",
    )
)
QUERY_ONLY_READY_ALIAS_CLAIMS = frozenset(
    (
        "permission_query_candidate_ready",
        "permission_query_planning_ready",
        "permissions_admin_query_candidate_ready",
        "permissions_admin_query_planning_ready",
        "permissions_query_candidate_ready",
        "permissions_query_planning_ready",
        "query_failclosed_candidate_ready",
        "query_failclosed_manifest_ready",
        "query_failclosed_planning_ready",
        "query_only_candidate_ready",
        "query_only_planning_ready",
    )
)
QUERY_ONLY_DIAGNOSTIC_FALSE_KEYS = (
    "public_header_allowed",
    "public_abi_ready",
    "public_sdk_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "publication_ready",
    "publication_authorized",
    "promotion_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "public_or_runtime_accounting_allowed",
    "route_ready",
    "public_route_ready",
    "permissions_admin_route_ready",
)
QUERY_ONLY_DIAGNOSTIC_ZERO_KEYS = (
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
)

REQUIRED_DECISION_IDS = frozenset(
    (
        "dependency.promoted_player_identity",
        "identity.principal_generation_required",
        "identity.principal_scope_compatibility",
        "abi.permission_query_identity_fields",
        "cache.generation_scope_keying",
        "policy.authority_provenance_required",
        "abuse.query_rate_limit_and_audit_gate",
        "fail_closed.stale_or_scope_mismatch",
        "separation.no_commands_replies_or_admin_mutation",
    )
)
REQUIRED_FORBIDDEN_PUBLIC_CONTRACT = frozenset(
    (
        "permission groups",
        "admin groups",
        "grant/revoke API",
        "ban/kick API",
        "admin actions",
        "admin mutation",
        "moderation authority",
        "storage/persistence",
        "operator ingress",
        "principal or permission claims from command text",
        "principal or permission claims from operator config",
        "command router",
        "command/chat response path",
        "replies/send-chat",
        "permission cache ABI",
        "allow without provenance",
        "public header symbols",
        "UE pointers",
        "raw params",
        "FName/GObjects indices",
        "ResourceHandle",
        "lookup",
        "mutation",
        "return override",
    )
)
REQUIRED_QUERY_TEXT_FRAGMENTS = frozenset(
    (
        "POD C ABI",
        "abi_version and struct_size front-loaded",
        "owner-token scoped call",
        "owner-token validation happens before policy lookup, cache lookup, rate budget, or allow result",
        "capability gated",
        "query-only result contract only",
        "action bytes are required, copied, and bounded to 128 bytes before allow",
        "resource_scope bytes are optional, copied, and bounded to 256 bytes before allow",
        "no command parser compatibility claim from action or resource_scope bytes",
        "no UTF-8 or text decoding claim before a separate reviewed parser contract",
        "no mutation of permission policy or admin state",
        "no command/reply handles",
        "no UE pointers or raw params",
    )
)
REQUIRED_FAIL_CLOSED_NEVER_ALLOW = frozenset(
    (
        "principal_generation_mismatch",
        "missing principal_handle",
        "missing principal_generation",
        "missing principal_scope_flags",
        "stale principal",
        "scope mismatch",
        "unsupported principal_scope_flags",
        "operator config permission claim",
        "operator-config allow-capability claim",
        "operator-config authority before separate allow-capable promotion",
        "runtime-local authority without runtime-owned provenance",
        "plugin-supplied policy provenance",
        "command text policy provenance claim",
        "operator config policy provenance claim",
        "unknown plugin owner token",
        "unloading plugin owner token",
        "zero plugin owner token",
        "missing plugin owner token",
        "missing capability",
        "rate limit exceeded",
    )
)
REQUIRED_FAIL_CLOSED_DENY_OR_UNKNOWN = frozenset(
    (
        "missing principal_handle",
        "missing principal_generation",
        "missing principal_scope_flags",
        "mismatched principal_generation",
        "unsupported principal_scope_flags",
        "missing_authority_generation",
        "authority_generation_mismatch",
        "command text policy provenance claim",
        "operator config policy provenance claim",
        "missing policy_epoch provenance",
        "policy source generation mismatch",
        "zero plugin owner token",
        "unknown plugin owner token",
        "unloading plugin owner token",
        "missing capability",
        "rate limit exceeded",
    )
)
REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY = (
    "query-only fail-closed permission decision checks over copied principals"
)
REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_ID = "resolve_permissions_admin_query_public_header_gate"
REQUIRED_POST_IDENTITY_FALSE_KEYS = (
    "public_header_allowed",
    "public_abi_ready",
    "public_sdk_ready",
    "runtime_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_ready",
    "stable_release_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_authorized",
    "publication_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "permissions_admin_route_ready",
    "missing_mismatched_or_stale_identity_certificate_counts",
    "identity_alias_or_stale_source_unlock_allowed",
    "identity_decision_record_alone_unlock_allowed",
    "runtime_evidence_alone_unlock_allowed",
)
REQUIRED_POST_IDENTITY_SHORTCUT_ARTIFACTS = frozenset(
    (
        "passive_monitor",
        "passive_snapshot",
        "handoff_notes",
        "compact_context",
        "beta",
        "beta_notice",
        "command_candidate",
        "diagnostic_candidate",
        "diagnostic_drift",
        "discord_notice",
        "discord",
        "discord_sent",
        "active_player_presence",
        "active_players",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_status_snapshot",
        "kick",
        "kick_player",
        "kickplayer",
        "live_posture",
        "live_server_posture",
        "machine_next_actions",
        "next_action_sequence",
        "next_action_report",
        "no_players_status",
        "no_users_passive_wait",
        "no_users_status",
        "notice_send_attestation",
        "p0",
        "package_install",
        "package_shape_metadata",
        "status_report",
        "public_readiness_report",
        "copied_log_only",
        "copied_log_only_artifact",
        "runtime_window_artifact",
        "runtime_window_execution",
        "runtime_window_plan",
        "runtime_evidence_status",
        "runtime_evidence_status_report",
        "package_shape_install",
        "package_shape_support",
        "passive_evidence",
        "passive_summary",
        "player_presence",
        "plugin_hub_planning",
        "plugin_hub_publication",
        "plugin_hub_published",
        "observer_enabled",
        "observer_enablement",
        "publication",
        "release_publication",
        "rcon_command_candidate",
        "rcon_route_candidate",
        "rcon_status",
        "route_candidate",
        "runtime_posture",
        "server_kick_player",
        "server_list_players",
        "server_posture",
        "side_lane_artifact",
        "scoped_release_statement",
        "source_ready",
        "stable_claim",
        "stable_publication",
        "stable_release",
        "static_admin_thunk",
        "static_thunk",
        "support_tier_metadata",
        "terminal_certificate",
        "terminal_status_certificate",
    )
)
POST_IDENTITY_DECISION_COMPAT_SHORTCUT_ARTIFACTS = frozenset(
    (
        "active_player_presence",
        "active_players",
        "diagnostic_drift",
        "live_posture",
        "live_server_posture",
        "observer_enabled",
        "observer_enablement",
        "player_presence",
        "runtime_posture",
        "server_posture",
    )
)
REQUIRED_POST_IDENTITY_DECISION_SHORTCUT_ARTIFACTS = (
    REQUIRED_POST_IDENTITY_SHORTCUT_ARTIFACTS - POST_IDENTITY_DECISION_COMPAT_SHORTCUT_ARTIFACTS
)
REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_NON_CLAIM = (
    "after obelisk.player_identity.v1 is promoted, permissions/admin still has only the "
    "public-header/query gate requirement; this field is planning metadata and grants no "
    "public, runtime, stable, SDK, or P0 progress claim"
)
REQUIRED_DEPENDENCY_BEHAVIOR = frozenset(
    (
        "before player identity is promoted, permissions/admin exposes no public ABI, callbacks, cache ABI, command/reply implication, or header symbols",
        "player identity planning evidence alone cannot enable permissions/admin",
        "runtime principal evidence alone is not public identity promotion",
        "approved runtime principal lifecycle evidence alone cannot enable permissions/admin",
        "identity_public_contract_gate_missing is an identity route blocker only and cannot unlock permissions/admin before a promoted identity public contract and certificate",
        "accepted runtime evidence ready aliases such as acceptedRuntimeEvidenceReady, identityContractReviewed, principalReady, permissionsQueryReady, permissionsUnlocked, permissionHeaderAllowed, and adminAuthorityReady cannot unlock permissions/admin",
        "promoted player identity must include approved runtime principal lifecycle evidence, not only promoted status text",
        "promoted player identity must include a public identity/principal contract with capability, ABI, lifecycle cleanup, and SDK consumer coverage",
        "permissions/admin structured promotion evidence must include a matching player-identity promotion certificate for obelisk.player_identity.v1, first in the ordered P0 dependency chain, bound by reviewed evidence artifact hash",
        "permissions/admin route state cannot advance to public_header_gate_missing until the matching player-identity promotion certificate also proves accepted reviewed identity public contract decision record coverage",
        "review artifacts, passive evidence, diagnostic reports, sidecars, scoped statements, readiness aliases, and route reports cannot satisfy the player-identity promotion certificate required by permissions/admin",
        "activation-precondition reports, notice send attestations, request-check readiness, stale reviewed identity decision records, and route alias reports cannot satisfy the player-identity promotion certificate required by permissions/admin",
        "runtime evidence artifacts, identity public contract decision records, passive monitor snapshots, beta notices, closure reports, executor reports, and generic positive aliases cannot substitute for the current hash-bound player-identity promotion certificate required by permissions/admin",
        "generated, scaffold, placeholder, template, stale, or hash-unbound upstream certificates cannot satisfy the player-identity promotion certificate required by permissions/admin",
        "nested readiness, progress, unlock, route, public, runtime, stable, Plugin Hub, publication, or SDK/P0 accounting aliases remain non-counting until the full hash-bound dependency chain is accepted",
        "runtime-window artifacts, beta/Discord notices, no-users status, package installs, side-lanes, passive evidence, unblocked/allowed aliases, and generic identity-present aliases cannot unlock permissions/admin readiness or route state",
        "partial or contract-review-only identity public contract records cannot promote permissions/admin or count toward SDK/P0",
        "reviewed identity public contract decision records must be hash-bound to the matching promoted identity surface record inside the player-identity promotion certificate before permissions/admin can advance route state",
        "player-identity promotion certificates must explicitly declare required_reviewed_artifact_hash=evidence.reviewed_surface_record_sha256, the matching reviewed_artifact_hash_policy, and missing_mismatched_or_stale_certificate_counts=false before permissions/admin can advance route state",
        "player-identity promotion certificates with a wrong artifact hash, wrong chain position, stale reviewed identity public contract, downstream command/permissions shortcut, or missing certificate binding fail closed and remain non-counting",
        "scoped non-complete-SDK release statements and explicit exclusions are bookkeeping only; they cannot promote permissions/admin, satisfy the player-identity dependency, or count toward SDK/P0",
        "copied admin targets such as ShooterPlayerController.ServerListPlayers and ShooterPlayerController.ServerKickPlayer are admin surface orientation only, not copied player identity/principal semantics",
        "RCON, ListPlayers, Kick, ServerListPlayers, ServerKickPlayer, admin snapshots, static thunk, route candidate, source-ready, status, and command aliases are admin orientation or operational metadata only and cannot unlock permissions/admin public readiness, runtime readiness, route state, or SDK/P0 progress",
        "admin_kind, alias_source, source_alias, status_source, ListPlayers, Kick, RCON, admin snapshots, source-ready, and status alias records require the current hash-bound player-identity promotion certificate before any route, readiness, or SDK/P0 accounting claim; without it they fail closed and remain non-counting",
        "player-identity promotion certificates must carry explicit approved runtime lifecycle, copied principal, public contract/capability/ABI/lifecycle cleanup, SDK consumer, invalidation, and owner-token lifecycle proof fields before permissions/admin can count identity as promoted",
        "promoted player identity must define copied principal semantics for principal_handle, principal_generation, principal_scope_flags, invalidation, and owner-token lifecycle before permissions/admin can count as promoted",
        "promoted player identity must include owner-token cleanup on init failure, plugin unload, and owner-scoped unregister before permissions/admin can count as promoted",
        "permissions/admin cannot infer copied principal semantics from surface status text, runtime evidence text, command text, operator config, or plugin input",
        "runtime observation must establish principal identity before permissions/admin can consume it",
        "operator config enables surfaces or policy inputs only and cannot establish principal identity",
        "command text cannot establish principal identity",
        "after promoted player identity, the exact next permissions/admin requirement is the public-header gate for query-only fail-closed permission decision checks over copied principals",
        "passive monitor, passive summary, beta/Discord notice, no-users status, runtime-window, next-action/status, copied-log-only, package install/shape install/support, Plugin Hub planning, and stable-claim artifacts cannot count as permissions/admin readiness, runtime readiness, public SDK readiness, stable SDK readiness, or P0 progress",
        "handoff notes, compact context, beta notices, passive monitors/summaries, no-users statuses, runtime-window artifacts, package artifacts, Plugin Hub planning, side-lane artifacts, and identity-present aliases cannot advance permissions/admin route state or count toward SDK/P0",
        "identity_public_contract_gate_missing aliases, package-shape/support-tier metadata, terminal certificates, beta notice artifacts, and runtime evidence status reports cannot advance permissions/admin or count toward SDK/P0 without the current hash-bound player-identity promotion certificate",
        "permissions/admin remains post-v1 or excluded until this dependency is promoted or explicitly excluded",
    )
)
REQUIRED_PRINCIPAL_GENERATION_BEHAVIOR = frozenset(
    (
        "principal_handle alone never authorizes",
        "missing principal_handle fails closed",
        "missing generation fails closed",
        "stale generation fails closed",
        "generation mismatch returns deny or unknown, never allow",
    )
)
REQUIRED_PRINCIPAL_SCOPE_ALLOWED_INITIAL = frozenset(("callback-local", "process-local"))
REQUIRED_PRINCIPAL_SCOPE_FORBIDDEN = frozenset(("cluster-stable", "persistent", "cross-map shared"))
REQUIRED_PRINCIPAL_SCOPE_BEHAVIOR = frozenset(
    (
        "missing principal_scope_flags fails closed",
        "unsupported principal scope fails closed",
        "process mismatch fails closed",
        "restart-local or wider scope requires an explicit promoted identity contract",
    )
)
REQUIRED_PERMISSION_QUERY_FIELDS = frozenset(
    (
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
        "plugin_owner_token",
        "action",
        "action_size",
        "resource_scope",
        "resource_scope_size",
        "request_flags",
        "server_process_epoch",
    )
)
REQUIRED_POLICY_PROVENANCE_FIELDS = frozenset(
    (
        "policy_source_id",
        "policy_source_generation",
        "authority_kind",
        "authority_generation",
        "policy_epoch",
    )
)
REQUIRED_CACHE_KEY_FIELD_SEQUENCE = (
    "plugin_owner_token",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "action",
    "resource_scope",
    "policy_epoch",
)
REQUIRED_CACHE_PUBLIC_ABI_BLOCKER = "blocked_until_policy_epoch_generation_and_scope_semantics_are_promoted"
REQUIRED_CACHE_BEHAVIOR = frozenset(
    (
        "no public permission cache ABI until policy_epoch and full generation/scope keying semantics are promoted",
        "cache keys or entries must not cross the public ABI",
        "cache disabled unless all key fields are defined",
        "policy epoch mismatch fails closed",
        "cached allow decisions are invalidated on principal generation change",
        "cached decisions are invalidated on principal_scope_flags change",
        "cached decisions are invalidated on policy_epoch change",
        "cached decisions are invalidated on policy_source_generation change",
        "cached decisions are invalidated on authority_generation change",
        "cached decisions are invalidated on plugin owner cleanup",
        "scope mismatch bypasses cache and fails closed",
        "stale cache entries return deny or unknown, never allow",
    )
)
REQUIRED_RECOGNIZED_AUTHORITY_KINDS = frozenset(("operator-config", "runtime-local"))
REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS = frozenset(("runtime-local",))
REQUIRED_POLICY_AUTHORITY_BEHAVIOR = frozenset(
    (
        "operator-config authority is recognized but not allow-capable until separately promoted",
        "operator-config authority can provide runtime-owned policy inputs only and cannot produce allow",
        "runtime-local authority must be runtime-owned before it can produce allow",
        "runtime-local authority without runtime-owned provenance fails closed",
        "operator-config cannot establish principal identity or permission claims before runtime principal observation",
        "operator-config cannot self-attest allow-capable policy provenance",
        "command text cannot establish policy provenance",
        "permission authority derives only from an established runtime principal plus runtime-owned provenance",
        "policy provenance must be runtime-owned before allow",
        "plugin input cannot self-attest authority provenance",
        "plugin input cannot self-attest policy provenance",
    )
)
REQUIRED_ABUSE_BEHAVIOR = frozenset(
    (
        "permission queries are rate-limited per plugin owner token",
        "permission query budgets and audit counters are invalidated by plugin owner cleanup",
        "burst exhaustion returns deny or unknown, never allow",
        "abuse counters are process-local and owner-scoped",
        "repeated malformed queries are observable through runtime logs or counters",
        "audit records must not expose UE pointers, raw params, or secret policy contents",
        "rate-limit state is not a public cache ABI",
    )
)
REQUIRED_SEPARATION_SEQUENCE_GATE = frozenset(
    (
        "promoted player identity is required before permission checks",
        "query-only permission result provenance is required before command response",
        "command response privacy, generation, and scope policy is required before commands/replies",
        "commands/replies cannot imply permission groups, admin mutation, storage, or operator ingress",
    )
)
REQUIRED_SEPARATION_EXCLUSIONS = frozenset(
    (
        "command router",
        "command/chat response path",
        "replies/send-chat",
        "moderation",
        "ban/kick",
        "admin actions",
        "groups/grants",
        "permission cache ABI",
        "storage/persistence",
        "operator ingress",
    )
)
REQUIRED_PERMISSIONS_ADMIN_FALSE_KEYS = (
    "public_abi",
    "adds_obelisk_api",
    "public_sdk_ready",
    "promotion_ready",
    "runtime_ready",
    "public_header_allowed",
    "v1_completion_evidence",
    "complete_sdk_counting_allowed",
)
REQUIRED_PERMISSIONS_ADMIN_READY_ALIASES = frozenset(
    (
        "promoted",
        "public_ready",
        "public_contract_ready",
        "public_abi_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_evidence",
        "complete_sdk_counting_allowed",
    )
)
REQUIRED_PERMISSIONS_ADMIN_EVIDENCE_TERMS = frozenset(
    (
        "obelisk.player_identity.v1 promoted certificate",
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
        "policy_source_id",
        "policy_source_generation",
        "authority_kind",
        "authority_generation",
        "policy_epoch",
        "fail_closed_missing_or_stale_principal",
        "nonzero plugin_owner_token",
        "append_only_pod_c_abi",
        "sdk_consumer_tests",
    )
)
REQUIRED_PERMISSIONS_NOT_SUFFICIENT_EVIDENCE = frozenset(
    (
        "player identity planning without promoted player identity",
        "permission cache sketches",
        "candidate-only permissions/admin query fail-closed contract",
        "command/reply planning",
        "plugin-local command parser scaffolds",
        "static admin thunk orientation",
        "raw ProcessEvent callbacks",
    )
)
REQUIRED_PERMISSIONS_PROMOTION_REQUIRES = frozenset(
    (
        "promoted copied player identity/principal semantics, including principal_handle, principal_generation, principal_scope_flags, invalidation, and owner-token lifecycle",
        "matching player-identity promotion certificate for obelisk.player_identity.v1, first in v1_required_dependency_chain, bound by reviewed evidence artifact hash and proving promoted copied identity/principal semantics with approved runtime principal lifecycle evidence, public contract/capability/ABI/lifecycle cleanup, SDK consumer coverage, principal_handle, principal_generation, principal_scope_flags, invalidation, and owner-token lifecycle",
        "query-only fail-closed permission checks over copied principals",
        "permission queries include principal_generation and principal_scope_flags or are formally callback-local only",
        "stale principal, scope mismatch, missing generation, missing owner token, zero owner token, unknown owner token, unloading owner token, unknown authority source, and missing policy provenance fail closed",
        "allow decisions carry policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance; allow without provenance is forbidden",
        "authority source, abuse controls, audit, and privacy boundaries",
        "no public permission cache ABI until policy_epoch, generation, and scope keying semantics are separately promoted",
        "no permission groups, admin groups, grant/revoke API, admin actions, moderation actions, mutation authority, command router, command/chat response path, or replies/send-chat implication",
        "append-only POD C ABI design with capability gates, owner-scoped cleanup, and SDK consumer tests",
    )
)
REQUIRED_PERMISSIONS_QUERY_ONLY_POLICY = frozenset(
    (
        "permissions/admin remains query-only planning until obelisk.player_identity.v1 is promoted",
        "the first permissions/admin public slice may only be fail-closed permission queries over copied principals",
        "permission queries must include principal_generation and principal_scope_flags or be formally callback-local only",
        "allow decisions require policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
    )
)
REQUIRED_PERMISSIONS_QUERY_ONLY_FORBIDDEN = frozenset(
    (
        "permission groups",
        "admin groups",
        "grant/revoke API",
        "admin actions",
        "admin mutation",
        "permission cache ABI",
        "storage/persistence",
        "operator ingress",
        "command router",
        "command/chat response path",
        "replies/send-chat",
        "moderation authority",
        "ban/kick API",
        "allow without provenance",
        "public header permission symbols",
    )
)
REQUIRED_PERMISSIONS_NON_COUNTING_ARTIFACTS = frozenset(
    (
        "diagnostic route/gap/readiness reports",
        "passive chat parsing or plugin-local routing artifacts",
        "scoped non-complete-SDK release statements or exclusions",
        "candidate-only permissions/admin query fail-closed contracts",
        "missing, mismatched, stale, or hash-unbound promotion certificates",
    )
)
REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY = {
    "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
    "reviewed_artifact_hash_policy": "must match the reviewed identity surface record hash carried by the certificate",
    "missing_mismatched_or_stale_certificate_counts": False,
}
HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS = frozenset(("path", "sha256"))
HASH_BOUND_ARTIFACT_BINDING_KEYS = frozenset(("path", "sha256", "schema"))
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH = "evidence.reviewed_surface_record_sha256"
REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY = (
    "must match the reviewed surface record hash carried by the certificate"
)
REQUIRED_PERMISSIONS_CERTIFICATE_BINDING_POLICY = {
    "required_reviewed_artifact_hash": REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH,
    "reviewed_artifact_hash_policy": REQUIRED_PROMOTION_CERTIFICATE_REVIEWED_ARTIFACT_HASH_POLICY,
    "missing_mismatched_or_stale_certificate_counts": False,
}
REQUIRED_PERMISSIONS_IDENTITY_CERTIFICATE_FIELDS = {
    "schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
    "surface_id": IDENTITY_SURFACE,
    "promotion_status": "promoted",
    "v1_dependency_chain_position": 1,
    "required_by_surface": SURFACE,
    "required_by_v1_dependency_chain_position": 2,
    **REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
}
REQUIRED_PERMISSIONS_CERTIFICATE_FIELDS = {
    "schema": PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_SCHEMA,
    "surface_id": SURFACE,
    "promotion_status": "promoted",
    "v1_dependency_chain": REQUIRED_P0_CHAIN,
    "v1_dependency_chain_position": 2,
    "required_by_surface": COMMAND_RESPONSE_SURFACE,
    "required_by_v1_dependency_chain_position": 3,
    **REQUIRED_PERMISSIONS_CERTIFICATE_BINDING_POLICY,
}
REQUIRED_PERMISSIONS_CERTIFICATE_POSITION_ALIASES = {
    "chain_position": 2,
    "required_by_chain_position": 3,
}
REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS = frozenset(
    (
        "public_sdk_surfaces",
        "permissions_admin_surface_record_sha256",
        "player_identity_surface_record_sha256",
        "player_identity_promotion_certificate",
        "permissions_admin_public_contract_decisions",
        "permissions_admin_query_failclosed_contract",
        "permissions_admin_public_readiness_report_sha256",
        "query_failclosed_contract_report_sha256",
    )
)
PERMISSIONS_CERTIFICATE_INPUT_ARTIFACT_SCHEMAS = {
    "public_sdk_surfaces": SURFACES_SCHEMA,
    "permissions_admin_public_contract_decisions": DECISIONS_SCHEMA,
    "permissions_admin_query_failclosed_contract": QUERY_CONTRACT_SCHEMA,
}
PERMISSIONS_CERTIFICATE_REPORT_HASH_INPUTS = (
    "permissions_admin_public_readiness_report_sha256",
    "query_failclosed_contract_report_sha256",
)
REQUIRED_CERTIFICATE_PROMOTION_EVIDENCE_KIND = "player_identity_promotion_certificate"
REQUIRED_CERTIFICATE_FALSE_KEYS = (
    "review_artifact_only",
    "contract_review_only",
    "passive_evidence_only",
    "diagnostic_only",
    "candidate_only",
    "readiness_report_only",
    "approved_runtime_evidence_only",
)
REQUIRED_CERTIFICATE_SEMANTIC_PROOFS = frozenset(
    (
        "approved_runtime_principal_lifecycle_evidence",
        "copied_principal_handle_generation_scope_flags",
        "principal_invalidation_semantics",
        "owner_token_lifecycle_cleanup",
        "reviewed_identity_public_contract_decision_record",
        "public_contract_capability_abi_lifecycle",
        "sdk_consumer_coverage",
    )
)
REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS = (
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
)
REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS = {
    "complete_identity_public_contract_reviewed": True,
    "partial_identity_contract": False,
    "hash_current_identity_public_contract_decision_record": True,
    "permissions_admin_unlock_allowed": False,
    "permissions_admin_counting_allowed": False,
    "sdk_or_p0_counting_allowed": False,
}
REQUIRED_PLAYER_IDENTITY_CERTIFICATE_POSITION_ALIASES = {
    "chain_position": 1,
    "required_by_chain_position": 2,
}
REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT = frozenset(
    (
        "capability_gated",
        "append_only_abi",
        "owner_token_handle_registration",
        "owner_scoped_unregister",
        "plugin_owner_cleanup",
        "no_ue_internals_in_public_abi",
    )
)
REQUIRED_IDENTITY_PUBLIC_CONTRACT = frozenset(
    (
        "ObeliskPlayerPrincipalEvent",
        "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
        "UnregisterPlayerPrincipalEventWithOwnerToken",
    )
)
REQUIRED_IDENTITY_CAPABILITIES = frozenset(("OBELISK_API_CAPABILITY_PLAYER_IDENTITY",))
REQUIRED_IDENTITY_PUBLIC_FIELDS = frozenset(
    (
        "principal_handle",
        "principal_generation",
        "principal_scope_flags",
    )
)
REQUIRED_IDENTITY_LIFECYCLE_CONTRACT = frozenset(
    (
        "plugin-owner cleanup",
        "owner-token cleanup on init failure",
        "owner-token cleanup on plugin unload",
        "owner-scoped unregister cleanup",
    )
)
IDENTITY_PROMOTED_DECISION_VALUES = frozenset(
    (
        "promoted",
        "promoted_public_contract",
        "public_contract_promoted",
    )
)
REQUIRED_HEADER_ABSENT_TOKENS = frozenset(
    (
        "OBELISK_API_CAPABILITY_ADMIN",
        "OBELISK_API_CAPABILITY_ADMIN_COMMANDS",
        "OBELISK_API_CAPABILITY_AUTHORIZATION",
        "OBELISK_API_CAPABILITY_AUTH",
        "OBELISK_API_CAPABILITY_AUTHZ",
        "OBELISK_API_CAPABILITY_ACCESS_CONTROL",
        "OBELISK_API_CAPABILITY_ACL",
        "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
        "OBELISK_API_CAPABILITY_PERMISSION_QUERY",
        "OBELISK_API_CAPABILITY_PERMISSIONS",
        "OBELISK_API_CAPABILITY_PLAYER_PERMISSION",
        "OBELISK_API_CAPABILITY_PRINCIPAL_PERMISSION",
        "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
        "OBELISK_API_CAPABILITY_ROLES",
        "OBELISK_API_CAPABILITY_PRIVILEGES",
        "OBELISK_API_CAPABILITY_MODERATION",
        "OBELISK_API_CAPABILITY_BAN",
        "OBELISK_API_CAPABILITY_KICK",
        "OBELISK_ADMIN_ABI_VERSION",
        "OBELISK_AUTH_ABI_VERSION",
        "OBELISK_AUTHZ_ABI_VERSION",
        "OBELISK_ACCESS_CONTROL_ABI_VERSION",
        "OBELISK_ACL_ABI_VERSION",
        "OBELISK_PERMISSION_CACHE_ABI_VERSION",
        "OBELISK_PERMISSION_QUERY_ABI_VERSION",
        "OBELISK_PERMISSION_CHECKS_ABI_VERSION",
        "OBELISK_PERMISSIONS_ABI_VERSION",
        "OBELISK_PLAYER_PERMISSION_ABI_VERSION",
        "OBELISK_PRINCIPAL_PERMISSION_ABI_VERSION",
        "OBELISK_PERMISSIONS_ADMIN_ABI_VERSION",
        "OBELISK_AUTHORIZATION_ABI_VERSION",
        "OBELISK_ADMIN_ACTION_ABI_VERSION",
        "OBELISK_ROLE_ABI_VERSION",
        "OBELISK_ROLES_ABI_VERSION",
        "OBELISK_PRIVILEGE_ABI_VERSION",
        "OBELISK_PRIVILEGES_ABI_VERSION",
        "OBELISK_MODERATION_ABI_VERSION",
        "OBELISK_BAN_ABI_VERSION",
        "OBELISK_KICK_ABI_VERSION",
        "OBELISK_PERMISSION_REASON_FLAGS",
        "OBELISK_PERMISSION_REASON_",
        "OBELISK_ADMIN_REASON_",
        "ObeliskAdminAction",
        "ObeliskAuthorizationDecision",
        "ObeliskAuthorizationReasonFlags",
        "ObeliskPermissionCache",
        "PermissionCache",
        "ObeliskPermissionQuery",
        "PermissionQuery",
        "ObeliskPermissionDecision",
        "PermissionDecision",
        "ObeliskPermissionReasonFlags",
        "PermissionReasonFlags",
        "ReasonFlags",
        "reason_flags",
        "Authorize",
        "AuthorizePermission",
        "CheckPermission",
        "CheckPermissionWithOwnerToken",
        "CheckPermissionCachedWithOwnerToken",
        "RegisterPermission",
        "GrantPermission",
        "RevokePermission",
        "BanPlayer",
        "KickPlayer",
    )
)
REQUIRED_HEADER_ABSENT_PREFIXES = frozenset(
    (
        "OBELISK_PERMISSION_REASON_",
        "OBELISK_ADMIN_REASON_",
    )
)
REQUIRED_HEADER_ABSENT_EXACT_TOKENS = REQUIRED_HEADER_ABSENT_TOKENS - REQUIRED_HEADER_ABSENT_PREFIXES
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}")
ZERO_SHA256 = "0" * 64
QUERY_READY_FALSE_KEYS = (
    "promotion_ready",
    "public_header_allowed",
    "public_cache_abi_allowed",
    "public_sdk_ready",
    "runtime_ready",
)
BETA_CAPTURE_REQUIRED_SURFACES = ("admin", "list_player", "kick_path")
BETA_CAPTURE_SURFACE_TARGETS = {
    "admin": "permissions_admin_admin_surface",
    "list_player": "ShooterPlayerController.ServerListPlayers",
    "kick_path": "ShooterPlayerController.ServerKickPlayer",
}
BETA_CAPTURE_FALSE_KEYS = (
    "accepted_for_planning",
    "accepted_runtime_evidence_ready",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "approved_runtime_principal_lifecycle_evidence",
    "candidate_capture_checker_accepted",
    "clears_approved_runtime_evidence_missing",
    "counts_as_approved_runtime_evidence",
    "counts_as_p0_progress",
    "counts_as_public_readiness",
    "counts_as_runtime_evidence",
    "counts_as_sdk_progress",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "evidence_accepted",
    "evidence_ready",
    "identity_evidence_accepted",
    "identity_runtime_evidence_satisfied",
    "own_checker_accepted",
    "permissions_admin_route_ready",
    "player_identity_evidence_accepted",
    "player_identity_runtime_evidence_ready",
    "player_identity_runtime_evidence_satisfied",
    "player_principal_triplet_satisfied",
    "player_principal_runtime_evidence_satisfied",
    "plugin_hub_publication_ready",
    "plugin_hub_ready",
    "promotion_ready",
    "public_api_ready",
    "public_contract_ready",
    "public_abi_ready",
    "public_header_allowed",
    "public_or_runtime_accounting_allowed",
    "public_ready",
    "public_readiness_ready",
    "public_route_ready",
    "public_sdk_ready",
    "publication_ready",
    "publication_authorized",
    "replaces_player_principal_evidence",
    "route_ready",
    "runtime_capture_authorized",
    "runtime_evidence_accepted",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_evidence_satisfied",
    "runtime_ready",
    "sdk_p0_progress_ready",
    "sdk_progress_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_ready",
    "stable_release_ready",
    "stable_sdk_ready",
    "v1_completion_evidence",
)
BETA_CAPTURE_ZERO_KEYS = (
    "approved_runtime_evidence_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "evidence_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_progress",
    "public_sdk_progress",
    "runtime_evidence_progress_contribution",
    "sdk_progress",
    "sdk_progress_contribution",
)
BETA_CAPTURE_NON_CLAIM = (
    "admin/list-player/kick-path beta captures are candidate/debug queue metadata only; "
    "they do not replace the required player-principal triplet, approved runtime evidence, "
    "public SDK readiness, runtime readiness, stable readiness, SDK/P0 progress, or route progress"
)
FALSE_ONLY_KEYS = frozenset(
    (
        *QUERY_ONLY_READY_ALIAS_CLAIMS,
        "accepted_runtime_evidence_only",
        "accepted_runtime_evidence_only_allowed",
        "accepted_runtime_evidence_only_ready",
        "command_router_allowed",
        "complete_sdk_claim_allowed",
        "complete_sdk_ready",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "full_sdk_claim_allowed",
        "full_sdk_ready",
        "accepted_runtime_evidence_sufficient",
        "accepted_runtime_evidence_sufficient_for_promotion",
        "accepted_runtime_evidence_ready",
        "activation_allowed",
        "activation_authorized",
        "activation_preconditions",
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "activation_preconditions_unlock_allowed",
        "activation_ready",
        "admin_authority_ready",
        "beta_notice",
        "beta_notice_ready",
        "beta_notice_send_unlock_allowed",
        "beta_notice_sent",
        "broadcast_ready",
        "broadcast_status",
        "bridge_claims_allowed",
        "capability_advertised",
        "capability_allowed",
        "capability_ready",
        "compact_context_accepted",
        "compact_context_ready",
        "current_route_blocker_bypassed",
        "dependency_gate_bypass_allowed",
        "dependency_route_bypass_allowed",
        "discord_notice_ready",
        "discord_sent",
        "generic_identity_present",
        "identity_contract_reviewed",
        "identity_observed",
        "identity_present",
        "identity_unblocked",
        "identity_public_contract_allowed",
        "identity_public_contract_gate_missing",
        "identity_public_contract_gate_missing_allows_permission_header",
        "identity_public_contract_gate_missing_allows_permission_query",
        "identity_public_contract_gate_missing_allows_permissions_admin",
        "identity_public_contract_gate_missing_allows_permissions_query",
        "identity_public_contract_gate_missing_allows_public_header",
        "identity_public_contract_gate_missing_unlock_allowed",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "identity_public_contract_ready",
        "identity_public_contract_reviewed",
        "identity_public_contract_decision_record_contract_review_only",
        "identity_public_contract_decision_record_hash_current",
        "identity_public_contract_decision_record_reviewed",
        "identity_evidence_accepted",
        "identity_review_complete",
        "identity_contract_review_complete",
        "live_operations_authorized",
        "live_ops_approval_granted",
        "live_ops_authorization_granted",
        "live_server_authorized",
        "machine_next_actions_ready",
        "next_action_plan_ready",
        "next_action_ready",
        "next_action_sequence_ready",
        "next_action_status_ready",
        "next_actions_ready",
        "notice_ready",
        "notice_sent",
        "notice_status_ready",
        "no_players_status_ready",
        "no_users_passive_wait_ready",
        "no_users_status_ready",
        "operator_approval_granted",
        "package_install_accepted",
        "package_install_ready",
        "package_install_unblocked",
        "p0_completion_ready",
        "p0_dependency_ready",
        "p0_dependency_satisfied",
        "p0_progress_claim_allowed",
        "p0_progress_ready",
        "p0_release_ready",
        "p0_surface_ready",
        "p0",
        "package_shape_support_ready",
        "passive_summary_ready",
        "player_identity_evidence_accepted",
        "player_identity_public_contract_ready",
        "player_identity_promotion_certificate_ready",
        "permission_header_allowed",
        "permission_header_unblocked",
        "permission_ready",
        "permission_cache_abi_allowed",
        "permissions_admin_ready",
        "permissions_admin_unblocked",
        "permissions_query_ready",
        "permissions_query_unblocked",
        "permissions_ready",
        "permissions_unlocked",
        "permissions_unblocked",
        "principal_ready",
        "principal_observed",
        "principal_present",
        "principal_unblocked",
        "production_server_authorized",
        "promotion_certificate_ready",
        "promotion_ready",
        "production_sdk_claim_allowed",
        "production_sdk_ready",
        "public_or_runtime_accounting_allowed",
        "public_abi_allowed",
        "public_abi_ready",
        "public_abi_unlocked",
        "public_admin_mutation_allowed",
        "public_bridge_abi_allowed",
        "public_cache_abi_allowed",
        "public_capability_advertised",
        "public_capability_allowed",
        "public_capability_ready",
        "public_command_reply_allowed",
        "public_command_router_allowed",
        "public_contract_allowed",
        "public_contract_ready",
        "public_contract_reviewed",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_contract_complete",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "public_header_allowed",
        "public_header_ready",
        "public_permission_cache_allowed",
        "public_readiness_next_action_ready",
        "public_readiness_report_ready",
        "public_readiness_ready",
        "public_readiness_status_ready",
        "public_reachability",
        "public_reachability_counts_as_approved_runtime_evidence",
        "public_reachability_ready",
        "public_reachability_satisfies_runtime_evidence",
        "public_reachability_status",
        "public_reachability_unlock_allowed",
        "public_route_gate_ready",
        "public_route_ready",
        "public_route_unblocked",
        "public_reply_abi_allowed",
        "public_reply_abi_ready",
        "public_reply_abi_unlocked",
        "public_reply_api",
        "public_reply_api_unlocked",
        "public_response_abi_allowed",
        "public_response_path_ready",
        "public_reply_or_send_chat_abi_allowed",
        "public_reply_or_send_chat_abi_unlocked",
        "public_response_path_allowed",
        "public_sdk",
        "public_sdk_ready",
        "public_send_chat_abi_allowed",
        "public_send_chat_abi_unlocked",
        "public_send_chat_api",
        "public_send_chat_api_unlocked",
        "command_response_ready",
        "command_response_unlocked",
        "command_chat_response_ready",
        "commands_ready",
        "commands_replies_ready",
        "commands_replies_unlocked",
        "chat_replies_ready",
        "reply_abi_allowed",
        "reply_abi_unlocked",
        "reply_allowed",
        "reply_api_allowed",
        "reply_api_unlocked",
        "reply_unlocked",
        "route_ready",
        "route_gate_ready",
        "route_gate_unlocked",
        "route_readiness_ready",
        "route_unblocked",
        "release_readiness_ready",
        "remaining_route_blockers_bypassed",
        "passive_next_action_accepted",
        "passive_ready",
        "passive_status_ready",
        "request_check",
        "request_check_ready",
        "request_check_unlock_allowed",
        "request_json_check_ready",
        "request_pack",
        "request_pack_ready",
        "request_pack_unlock_allowed",
        "rcon_command_ready",
        "rcon_command_status",
        "rcon_ready",
        "rcon_route_ready",
        "rcon_route_status",
        "rcon_status",
        "runtime_window_artifact_ready",
        "runtime_window_authorized",
        "runtime_window_closure_ready",
        "runtime_window_execution_ready",
        "runtime_window_plan_ready",
        "runtime_window_ready",
        "stable_claim_allowed",
        "stable_claim_ready",
        "stable_claim_supported",
        "stable_publication_authorized",
        "stable_ready",
        "stable_release_ready",
        "stable_sdk_claim_allowed",
        "stable_sdk_ready",
        "stable_release_contract_claim_allowed",
        "scoped_release_statement",
        "scoped_release_statement_ready",
        "scoped_release_statement_counts_toward_completion",
        "scoped_release_statement_counts_toward_complete_sdk_claim",
        "scoped_release_statement_outcomes_satisfy_completion",
        "permissions_admin_route_ready",
        "replies_send_chat_allowed",
        "reply_send_chat_router_claims_allowed",
        "route_accepted",
        "route_accepted_as_permission_query",
        "route_accepted_as_permissions_admin",
        "route_accepted_as_permissions_query",
        "route_accepted_as_public_abi",
        "route_accepted_as_public_header",
        "route_accepted_as_public_sdk",
        "route_accepted_as_runtime",
        "route_accepted_as_stable_claim",
        "route_acceptance_ready",
        "route_blocker_bypass",
        "route_blocker_bypass_allowed",
        "route_blocker_bypass_ready",
        "route_blocker_bypassed",
        "runtime_approval",
        "runtime_approval_granted",
        "runtime_delivery_allowed",
        "runtime_readiness_allowed",
        "runtime_ready",
        "runtime_unblocked",
        "runtime_work_authorized",
        "live_ops_authorized",
        "runtime_capture_authorized",
        "workspace_writes_authorized",
        "reads_live_logs",
        "server_operations_authorized",
        "send_chat_allowed",
        "send_chat_api_allowed",
        "send_chat_api_unlocked",
        "send_chat_abi_unlocked",
        "send_chat_ready",
        "send_chat_unlocked",
        "sdk_p0_progress_claim_allowed",
        "sdk_p0_progress_ready",
        "source_ready",
        "status_ready",
        "status_report_ready",
        "plugin_hub_planning_accepted",
        "plugin_hub_planning_ready",
        "plugin_hub_planning_supported",
        "plugin_hub_package_shape_ready",
        "plugin_hub_publication",
        "plugin_hub_publication_ready",
        "plugin_hub_published",
        "plugin_hub_ready",
        "plugin_hub_support_ready",
        "published_to_plugin_hub",
        "publication",
        "publication_authorized",
        "publication_ready",
        "release_publication_ready",
        "v1_0_stable_ready",
        "v1_completion_evidence",
        "v1_completion_ready",
        "v1_completion_unblocked",
    )
)
POSITIVE_ALIAS_CLAIMS = frozenset(
    (
        *QUERY_ONLY_READY_ALIAS_CLAIMS,
        "accepted_runtime_evidence_only",
        "accepted_runtime_evidence_only_allowed",
        "accepted_runtime_evidence_only_ready",
        "accepted_runtime_evidence_sufficient",
        "accepted_runtime_evidence_sufficient_for_promotion",
        "activation_allowed",
        "activation_authorized",
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "activation_ready",
        "beta_notice_ready",
        "beta_notice_sent",
        "compact_context_accepted",
        "compact_context_ready",
        "current_route_blocker_bypassed",
        "dependency_gate_bypass_allowed",
        "dependency_route_bypass_allowed",
        "discord_notice_ready",
        "discord_sent",
        "generic_identity_present",
        "identity_observed",
        "identity_present",
        "identity_unblocked",
        "identity_public_contract_gate_missing_allows_permission_header",
        "identity_public_contract_gate_missing_allows_permission_query",
        "identity_public_contract_gate_missing_allows_permissions_admin",
        "identity_public_contract_gate_missing_allows_permissions_query",
        "identity_public_contract_gate_missing_allows_public_header",
        "identity_public_contract_gate_missing_unlock_allowed",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "machine_next_actions_ready",
        "live_operations_authorized",
        "live_ops_approval_granted",
        "live_ops_authorization_granted",
        "live_server_authorized",
        "next_action_plan_ready",
        "next_action_ready",
        "next_action_sequence_ready",
        "next_action_status_ready",
        "next_actions_ready",
        "notice_ready",
        "notice_sent",
        "notice_status_ready",
        "no_players_status_ready",
        "no_users_passive_wait_ready",
        "no_users_status_ready",
        "p0_completion_ready",
        "p0_dependency_ready",
        "p0_dependency_satisfied",
        "p0_progress_claim_allowed",
        "p0_progress_ready",
        "p0_release_ready",
        "p0_surface_ready",
        "production_server_authorized",
        "public_readiness_next_action_ready",
        "public_readiness_report_ready",
        "public_readiness_status_ready",
        "public_reachability_ready",
        "public_reachability_unlock_allowed",
        "principal_observed",
        "principal_present",
        "principal_unblocked",
        "public_abi_unlocked",
        "public_reply_abi_unlocked",
        "public_reply_api_unlocked",
        "public_reply_or_send_chat_abi_unlocked",
        "public_send_chat_abi_unlocked",
        "public_send_chat_api_unlocked",
        "remaining_route_blockers_bypassed",
        "passive_next_action_accepted",
        "passive_ready",
        "passive_summary_ready",
        "passive_status_ready",
        "package_shape_support_ready",
        "request_check_ready",
        "request_check_unlock_allowed",
        "request_json_check_ready",
        "request_pack_ready",
        "request_pack_unlock_allowed",
        "reviewed_identity_contract_complete",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "reply_abi_unlocked",
        "reply_api_unlocked",
        "reply_unlocked",
        "route_accepted",
        "route_accepted_as_permission_query",
        "route_accepted_as_permissions_admin",
        "route_accepted_as_permissions_query",
        "route_accepted_as_public_abi",
        "route_accepted_as_public_header",
        "route_accepted_as_public_sdk",
        "route_accepted_as_runtime",
        "route_accepted_as_stable_claim",
        "route_acceptance_ready",
        "route_blocker_bypass_allowed",
        "route_blocker_bypass_ready",
        "route_blocker_bypassed",
        "route_unblocked",
        "runtime_window_artifact_ready",
        "runtime_window_authorized",
        "runtime_window_closure_ready",
        "runtime_window_execution_ready",
        "runtime_window_plan_ready",
        "runtime_window_ready",
        "send_chat_abi_unlocked",
        "send_chat_api_unlocked",
        "send_chat_unlocked",
        "sdk_p0_progress_claim_allowed",
        "sdk_p0_progress_ready",
        "source_ready",
        "status_ready",
        "status_report_ready",
        "plugin_hub_planning_accepted",
        "plugin_hub_planning_ready",
        "plugin_hub_planning_supported",
        "plugin_hub_ready",
        "v1_completion_unblocked",
    )
)
CERTIFICATE_GATED_ALIAS_CLAIMS = frozenset(
    (
        *QUERY_ONLY_READY_ALIAS_CLAIMS,
        "accepted_runtime_evidence_only",
        "accepted_runtime_evidence_sufficient",
        "activation_preconditions_met",
        "activation_preconditions_ready",
        "beta_notice_sent",
        "compact_context_ready",
        "discord_notice_ready",
        "discord_sent",
        "generic_identity_present",
        "identity_observed",
        "identity_present",
        "identity_unblocked",
        "identity_public_contract_gate_missing_allows_permission_header",
        "identity_public_contract_gate_missing_allows_permission_query",
        "identity_public_contract_gate_missing_allows_permissions_admin",
        "identity_public_contract_gate_missing_allows_permissions_query",
        "identity_public_contract_gate_missing_allows_public_header",
        "identity_public_contract_gate_missing_unlock_allowed",
        "public_reachability_ready",
        "public_readiness_ready",
        "public_runtime_readiness_accepted",
        "public_runtime_readiness_ready",
        "public_runtime_ready",
        "request_check_ready",
        "request_pack_ready",
        "route_acceptance_ready",
        "route_accepted",
        "identity_public_contract_gate_accepted",
        "identity_public_contract_gate_passed",
        "identity_public_contract_gate_resolved",
        "machine_next_actions_ready",
        "next_action_plan_ready",
        "next_action_ready",
        "next_action_sequence_ready",
        "next_action_status_ready",
        "next_actions_ready",
        "notice_ready",
        "notice_sent",
        "notice_status_ready",
        "no_players_status_ready",
        "no_users_passive_wait_ready",
        "no_users_status_ready",
        "passive_next_action_accepted",
        "passive_ready",
        "passive_summary_ready",
        "passive_status_ready",
        "principal_observed",
        "principal_present",
        "principal_unblocked",
        "package_shape_support_ready",
        "plugin_hub_planning_ready",
        "public_readiness_next_action_ready",
        "public_readiness_report_ready",
        "public_readiness_ready",
        "public_readiness_status_ready",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_ready",
        "reviewed_player_identity_public_contract",
        "reviewed_player_identity_public_contract_ready",
        "runtime_readiness_accepted",
        "runtime_readiness_ready",
        "runtime_ready",
        "runtime_window_artifact_ready",
        "runtime_window_authorized",
        "runtime_window_closure_ready",
        "runtime_window_execution_ready",
        "runtime_window_plan_ready",
        "runtime_window_ready",
        "route_unblocked",
        "source_ready",
        "status_ready",
        "status_report_ready",
    )
)
IDENTITY_GATE_ALIAS_KEY_TOKENS = frozenset(
    (
        "admin",
        "allow",
        "allowed",
        "allows",
        "authorizes",
        "authorized",
        "bypass",
        "bypassed",
        "bypasses",
        "contract",
        "enable",
        "enabled",
        "enables",
        "header",
        "opened",
        "opens",
        "permission",
        "permission_header",
        "permission_query",
        "permissions",
        "permissions_admin",
        "permissions_query",
        "public",
        "public_header",
        "queries",
        "query",
        "ready",
        "unblock",
        "unblocked",
        "unblocks",
        "unlock",
        "unlocked",
        "unlocks",
    )
)
UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS = (PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,)
SPLIT_CLAIM_NAME_KEYS = frozenset(
    (
        "alias",
        "claim",
        "field",
        "flag",
        "key",
        "name",
        "property",
    )
)
SPLIT_CLAIM_VALUE_KEYS = frozenset(
    (
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "available",
        "claim_state",
        "claim_value",
        "complete",
        "completed",
        "enabled",
        "is_ready",
        "outcome",
        "promoted",
        "public",
        "ready",
        "result",
        "source_accepted",
        "source_outcome",
        "source_ready",
        "source_result",
        "source_state",
        "source_status",
        "source_supported",
        "state",
        "status",
        "unlocked",
        "value",
        "verdict",
    )
)
SOURCE_MARKER_KEYS = frozenset(("source_marker", "source_markers"))
SOURCE_PROVENANCE_CONTEXT_KEYS = frozenset(
    (
        "artifact_provenance",
        "evidence_provenance",
        "metadata_provenance",
        "provenance",
        "provenance_marker",
        "provenance_markers",
        "review_provenance",
        "route_provenance",
        "snapshot_provenance",
        "source_provenance",
        "source_provenances",
    )
)
SOURCE_STATUS_KEYS = frozenset(
    (
        "source_accepted",
        "source_outcome",
        "source_ready",
        "source_result",
        "source_state",
        "source_status",
        "source_supported",
        "state",
        "status",
    )
)
NON_EVIDENCE_ARTIFACT_NAME_KEYS = frozenset(
    (
        "artifact",
        "artifact_class",
        "artifact_kind",
        "artifact_type",
        "class",
        "kind",
        "name",
        "field",
        "claim",
        "key",
    )
)
NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|complete|completed|counts?(?:_towards?|_toward|_as)?|credit|credited|"
    r"evidence|progress|progress_?contribution|readiness|ready|result|state|status|"
    r"supported|verified"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_SCOPE_RE = re.compile(
    r"(?:^|_)(?:"
        r"admin_authority|admin_capture|admin_(?:route_)?snapshot|admin_status_snapshot|admin_target|broadcast|copied_admin_target|"
    r"standing_authority|"
    r"(?:command_principal_authz_response_)?bridge(?:_report)?|"
    r"(?:authz_response|response)_bridge(?:_report)?|"
    r"command_principal_authz_bridge(?:_report)?|"
    r"command(?:_chat)?_response(?:_path)?|command_planning|command_router|command_routing|"
    r"compact_context|"
    r"commands?_repl(?:y|ies)|dependency_chain|"
    r"(?:generic_)?identity_(?:observed|present|ready|unblocked)|"
    r"principal_(?:observed|present|ready|unblocked)|"
    r"(?:machine_)?next_actions?|next_action(?:_(?:plan|sequence|status))?|"
    r"no_(?:users|players)(?:_(?:passive_wait|status|ready|unblocked))?|"
    r"notice(?:_(?:sent|status))?|passive(?:_(?:next_action|status))?|"
    r"permissions?_admin|permissions?_quer(?:y|ies)|permission(?:_header|_query)?|"
    r"public_(?:abi|api|header|readiness|reachability|route|runtime|sdk)|"
    r"plugin_hub(?:_planning|_publication|_published|_support|_package|_package_shape)?|"
    r"(?:public_)?release_publication|publication|published_to_plugin_hub|"
    r"rcon(?:_command)?(?:_candidate|_route|_status)?|"
    r"list_players?|list_player(?:_capture|_candidate)?|kick(?:_player)?|kickplayer|kick_path(?:_capture|_candidate)?|"
    r"server_(?:list_players|kick_player)|static(?:_admin)?_thunk|"
    r"reply(?:_(?:abi|api|endpoint|path))?|replies(?:_(?:abi|api|endpoint|path))?|"
        r"route(?:_(?:accepted|acceptance|gate|readiness|snapshot))?|"
    r"runtime(?:_(?:capture|delivery|readiness|wiring|work))?|runtime_window(?:_(?:artifact|authorized|closure|execution|plan|ready))?|"
    r"send_chat|server_operations|stable_(?:claim|publication|release|sdk)|"
    r"scoped(?:_non_complete)?(?:_v1)?_release_statement(?:_outcomes)?|"
    r"status_report|"
    r"terminal(?:_(?:certificate|status|completion|readiness|report))*|"
    r"support(?:_tier)?(?:_readiness|_report|_package|_package_shape)|"
    r"(?:complete|full|production)_sdk|"
    r"p0(?:_(?:completion|dependency|progress|release|surface|chain))*|"
    r"v1(?:_0)?(?:_(?:api|completion|release|sdk|stable|support))*"
    r")(?:_|$)"
)
BROAD_P0_ALIAS_STATE_RE = re.compile(
    r"(?:^|_)(?:"
    r"accepted|approved|allowed|allows|available|authorized|authorizes|bypassed|bypasses|"
    r"complete|completed|enabled|enables|granted|implemented|live|met|opened|opens|"
    r"observed|passed|present|promoted|public|published|ready|released|resolved|reviewed|satisfied|satisfies|stable|"
    r"sufficient|supported|unblocked|unblocks|unlocked|unlocks|validated|verified"
    r")(?:_|$)"
)
BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"claim_progress|credit|credited|progress|progress_contribution|progress_percent|"
    r"progress_ratio|readiness_credit|sdk_credit|sdk_completion_credit|"
    r"v1_completion_credit|public_sdk_credit|counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
GENERIC_NESTED_READY_OVERCLAIM_KEY_RE = re.compile(
    r"(?:^|_)(?:ready|readiness|unblocked|unlocked|supported|enabled|allowed|"
    r"complete|completion|promoted|promotion)$"
)
PROMOTED_SURFACE_COUNT_ALIAS_KEYS = {
    "promoted_count",
    "promoted_surface_count",
    "promoted_surface_total",
    "promoted_surfaces_count",
    "promoted_surfaces_total",
    "surface_promoted_count",
    "surface_promoted_total",
    "surfaces_promoted_count",
    "surfaces_promoted_total",
    "surface_promotion_count",
    "surface_promotion_total",
    "surfaces_promotion_count",
    "surfaces_promotion_total",
}
EXACT_PROMOTION_CREDIT_ALIAS_KEYS = frozenset(
    (
        "approved_runtime_evidence",
        "beta",
        "complete_sdk",
        "discord",
        "p0",
        "package_shape",
        "passive_snapshot",
        "plugin_hub",
        "public_sdk",
        "runtime_ready",
        "scoped_release_statement",
        "stable_sdk",
        "support_tier",
    )
)
BARE_NON_EVIDENCE_SHORTCUT_KEYS = frozenset(
    (
        "beta",
        "discord",
        "p0",
        "scoped_release_statement",
    )
)
BROAD_P0_ALIAS_EXEMPT_KEYS = frozenset(
    (
        "accepted_for_planning",
        "accepted_runtime_evidence_context",
        "approved_runtime_evidence_present",
        "required_before_public_header",
        "runtime_evidence_ready",
    )
)
NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE = re.compile(
    r"(?:"
    r"(?:accepted_?)?runtime_?simulations?|"
    r"(?:agent_?)?handoff(?:_?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"compact_?contexts?|compact_?summar(?:y|ies)|"
    r"discord_?(?:notice|sent|attestations?)|"
    r"(?:command_?principal_?authz_?response_?|authz_?response_?|response_?)?bridge_?reports?|"
    r"(?:player_?)?notice_?actions?(?:_?reports?)?|"
    r"beta_?notice_?actions?(?:_?reports?)?|"
    r"activation_?preconditions?(?:_?(?:artifacts?|reports?))?|"
    r"precondition_?(?:artifacts?|reports?)|"
    r"public_?contract_?records?(?:_?packages?)?|"
    r"request_?pack(?:_?public_?contract_?record)?|"
    r"support_?tiers?(?:_?(?:readiness|reports?))?|"
    r"support_?tier_?(?:packages?|package_?shapes?)|"
    r"(?:support_?)?package_?shapes?|"
    r"terminal_?(?:certificates?|status|completion|readiness|reports?)|"
        r"command_?planning(?:_?packages?|_?package_?shapes?)?|"
	    r"command_?(?:chat_?)?response_?planning(?:_?packages?)?|"
	    r"copied_?(?:response_?)?intent(?:_?planning)?(?:_?packages?|_?package_?shapes?)?"
	        r"|(?:machine_?)?next_?actions?(?:_?(?:plans?|reports?|sequence|status))?"
	        r"|next_?action(?:_?(?:plans?|reports?|sequence|status))?"
	        r"|no_?(?:users|players)(?:_?(?:passive_?wait|status|detected|present|reports?))?"
	        r"|notice(?:_?(?:actions?|reports?|sent|status))?"
	        r"|passive(?:_?(?:evidence|monitor|next_?action|reports?|snapshot|status|summary))?"
        r"|broadcast_?(?:notices?|status|reports?)"
        r"|public_?readiness(?:_?(?:next_?actions?|reports?|status))?"
        r"|public_?reachability(?:_?(?:checks?|reports?|status))?"
        r"|plugin_?hub(?:_?(?:planning|publication|published|readiness|reports?|support|package|package_?shape))?"
        r"|(?:public_?)?release_?publication|publication|published_?to_?plugin_?hub|stable_?(?:publication|release)"
        r"|rcon_?(?:command_?)?(?:routes?|status|reports?|candidates?)"
        r"|admin_?(?:route_?|status_?)?snapshots?(?:_?(?:status|reports?|candidates?))?"
        r"|(?:server_?)?list_?players?(?:_?(?:status|reports?|candidates?|capture))?"
        r"|(?:server_?)?kick(?:_?players?)?(?:_?(?:status|reports?|candidates?|capture|path))?"
        r"|kick_?path(?:_?(?:status|reports?|candidates?|capture))?"
        r"|static_?(?:admin_?)?thunks?(?:_?(?:status|reports?|candidates?))?"
	        r"|route_?snapshots?(?:_?packages?)?"
	        r"|runtime_?window(?:_?(?:artifacts?|plans?|planners?|execution|executors?|closures?|activation|requests?|manifests?|status|ready))?"
	        r"|side_?lane(?:_?(?:artifacts?|reports?|candidate|candidates))?"
	        r"|status_?reports?"
	    r")"
	)
ADMIN_ROUTE_STATUS_ALIAS_SOURCE_KEYS = frozenset(
    (
        "admin_alias",
        "admin_aliases",
        "admin_kind",
        "admin_kinds",
        "alias_source",
        "alias_sources",
        "principal_source",
        "principal_sources",
        "source_alias",
        "source_aliases",
        "status_alias",
        "status_aliases",
        "status_source",
        "status_sources",
    )
)
ADMIN_ROUTE_STATUS_ALIAS_TERMS = frozenset(
    (
        "admin",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_snapshots",
        "admin_status_snapshot",
        "kick",
        "kick_path",
        "kick_player",
        "kickplayer",
        "list_player",
        "list_players",
        "listplayers",
        "rcon",
        "server_kick_player",
        "server_list_players",
        "serverkickplayer",
        "serverlistplayers",
        "source_ready",
        "static_admin_thunk",
        "static_thunk",
        "status",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = frozenset(
    (
        *ADMIN_ROUTE_STATUS_ALIAS_SOURCE_KEYS,
        "authority_claim_source",
        "admin_source",
        "admin_sources",
        "command",
        "command_candidate",
        "command_candidates",
        "command_source",
        "command_sources",
        "identity_claim_source",
        "permission_principal_source",
        "principal_claim_source",
        "principal_source",
        "route",
        "route_candidate",
        "route_candidates",
        "route_source",
        "route_sources",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = frozenset(
    (
        "approved_runtime_evidence",
        "approved_runtime_principal_lifecycle_evidence",
        "command_text",
        "identity_public_contract",
        "operator_config",
        "reviewed_identity_public_contract",
        "runtime_lifecycle_evidence",
        "runtime_principal_lifecycle_evidence",
        "standing_authority",
    )
)
FORBIDDEN_ADMIN_SOURCE_TERMS = frozenset(
    (
        "command_candidate",
        "diagnostic_drift",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_snapshots",
        "admin_status_snapshot",
        "kick",
        "kick_player",
        "kickplayer",
        "list_players",
        "listplayers",
        "rcon",
        "route_candidate",
        "active_player_presence",
        "active_players",
        "live_posture",
        "live_server_posture",
        "observer_enabled",
        "observer_enablement",
        "player_presence",
        "runtime_posture",
        "server_posture",
        "server_kick_player",
        "server_list_players",
        "serverkickplayer",
        "serverlistplayers",
        "static_admin_thunk",
        "static_thunk",
        "staticadminthunk",
        "staticthunk",
    )
)
NON_PROMOTION_ARTIFACT_SOURCE_KEYS = frozenset(
    (
        *ADMIN_ROUTE_STATUS_ALIAS_SOURCE_KEYS,
        "artifact_class",
        "artifact_kind",
        "artifact_source",
        "evidence_class",
        "evidence_kind",
        "evidence_source",
        "input_kind",
        "input_scope",
        "intake_kind",
        "ready_scope",
        "report_kind",
        "review_scope",
        "admin_source",
        "admin_sources",
        "command",
        "command_candidate",
        "command_candidates",
        "command_source",
        "command_sources",
        "route",
        "route_candidate",
        "route_candidates",
        "route_source",
        "route_sources",
        "source",
        "source_class",
        "source_classes",
        "source_kind",
        "source_path",
        "source_paths",
        "sources",
    )
)
NON_PROMOTION_ARTIFACT_TERMS = frozenset(
    (
        *QUERY_ONLY_CANDIDATE_ALIAS_ARTIFACTS,
        "post_identity_query_only_diagnostics",
        "query_only_diagnostic",
        "query_only_diagnostics",
        "activation_precondition",
        "activation_preconditions",
        "activation_precondition_report",
        "activation_preconditions_report",
        "accepted_runtime_evidence",
        "approved_runtime_evidence",
        "approved_runtime_principal_lifecycle_evidence",
        "beta_notice",
        "candidate_only",
        "checker_report",
        "closure",
        "closure_report",
        "closure_request",
        "closure_output",
        "contract_review_input_only",
        "contract_review_only",
        "compact_context",
        "compact_summary",
        "copied_log",
        "copied_log_only",
        "copied_log_only_artifact",
        "copied_obelisk_log",
        "decision_record",
        "diagnostic",
        "diagnostic_only",
        "diagnostic_drift",
        "discord_notice",
        "discord_sent",
        "discord_attestation",
        "evidence_closure",
        "evidence_closure_report",
        "executor",
        "executor_artifact",
        "executor_report",
        "execution",
        "handoff",
        "handoff_note",
        "handoff_notes",
        "handoff_report",
        "identity_public_contract_decision_record",
        "lifecycle_start_end_evidence",
        "manual_snapshot",
        "active_player_presence",
        "active_players",
        "player_presence",
        "machine_next_action",
        "machine_next_actions",
        "next_action",
        "next_action_plan",
        "next_action_report",
        "next_action_sequence",
        "notice",
        "notice_prep",
        "notice_send",
        "notice_send_attestation",
        "no_players_currently_detected",
        "no_players_status",
        "no_users",
        "no_users_detected",
        "no_users_passive_wait",
        "no_users_status",
        "partial_contract",
        "partial_identity_contract",
        "partial_public_contract",
        "package_install",
        "package_shape",
        "package_shape_metadata",
        "package_shape_install",
        "package_shape_install_success",
        "package_shape_support",
        "package_shape_support_metadata",
        "passive",
        "passive_monitor",
        "passive_summary",
        "passive_summaries",
        "observer_enabled",
        "observer_enablement",
        "passive_snapshot",
        "planning_only",
        "plugin_hub",
        "plugin_hub_planning",
        "preflight",
        "public_readiness",
        "public_readiness_report",
        "preactivation_executor",
        "preactivation_executor_output",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_command_status",
        "rcon",
        "rcon_route",
        "rcon_route_candidate",
        "rcon_status",
        "request_check",
        "readiness_report",
        "receipt",
        "request_pack",
        "review_artifact",
        "review_report",
        "reviewed_decision_record",
        "reviewed_identity_public_contract_decision_record",
        "route_alias",
        "route_candidate",
        "route_candidates",
        "route_gate",
        "route_source",
        "runtime_evidence",
        "runtime_lifecycle_evidence",
        "runtime_principal_lifecycle_evidence",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "runtime_window",
        "runtime_window_activation",
        "runtime_window_artifact",
        "runtime_window_authority_boundary",
        "runtime_window_closure",
        "runtime_window_execution",
        "runtime_window_executor",
        "runtime_window_executor_artifact",
        "runtime_window_executor_closure",
        "runtime_window_plan",
        "runtime_window_post_window_state",
        "runtime_window_request",
        "runtime_window_request_pack",
        "live_posture",
        "live_server_posture",
        "runtime_posture",
        "server_posture",
        "scoped_release_statement",
        "scoped_statement",
        "beta_capture_candidate",
        "beta_capture_candidates",
        "admin_capture_candidate",
        "list_player_capture_candidate",
        "kick_path_capture_candidate",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_status_snapshot",
        "admin_source",
        "admin_target",
        "command_candidate",
        "command_candidates",
        "command_source",
        "copied_admin_target",
        "kick",
        "kick_player",
        "kick_path_candidate",
        "kickplayer",
        "list_player_candidate",
        "listplayers",
        "server_kick_player",
        "serverkickplayer",
        "server_list_players",
        "serverlistplayers",
        "source_ready",
        "static_admin_thunk",
        "static_thunk",
        "staticadminthunk",
        "staticthunk",
        "sidecar",
        "side_lane",
        "side_lane_artifact",
        "side_lane_report",
        "standing_authority",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "status_report",
        "status_shortcut",
        "support_tier",
        "support_tier_metadata",
        "support_tier_readiness",
        "support_tier_report",
        "terminal_certificate",
        "terminal_completion_certificate",
        "terminal_readiness_certificate",
        "terminal_status_certificate",
        "terminal_certificate_report",
        "runtime_evidence_status",
        "runtime_evidence_status_report",
        "beta_notice_artifact",
        "beta_notice_report",
        "beta_notice_status",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
        "window_manifest",
        "window_request_check",
    )
)
SHORTCUT_ARTIFACT_ALIAS_TERMS = frozenset(
    (
        *QUERY_ONLY_CANDIDATE_ALIAS_ARTIFACTS,
        "post_identity_query_only_diagnostics",
        "query_only_diagnostic",
        "query_only_diagnostics",
        "copied_log",
        "copied_log_only",
        "copied_log_only_artifact",
        "copied_obelisk_log",
        "compact_context",
        "compact_summary",
        "diagnostic_drift",
        "handoff",
        "handoff_note",
        "handoff_notes",
        "handoff_report",
        "installed_sdk_package_shape",
        "no_players_status",
        "no_users_passive_wait",
        "no_users_status",
        "active_player_presence",
        "active_players",
        "package_install",
        "package_shape",
        "package_shape_metadata",
        "package_shape_install",
        "package_shape_install_success",
        "package_shape_support",
        "package_shape_support_metadata",
        "passive_summary",
        "passive_summaries",
        "player_presence",
        "observer_enabled",
        "observer_enablement",
        "runtime_window",
        "runtime_window_artifact",
        "runtime_window_closure",
        "runtime_window_execution",
        "runtime_window_plan",
        "runtime_principal_lifecycle_start_end_evidence",
        "runtime_principal_start_end_evidence",
        "rcon_command_candidate",
        "rcon_command_route",
        "rcon_command_status",
        "rcon",
        "rcon_route",
        "rcon_route_candidate",
        "rcon_status",
        "admin_capture_candidate",
        "admin_route_snapshot",
        "admin_snapshot",
        "admin_status_snapshot",
        "admin_target",
        "copied_admin_target",
        "kick",
        "kick_player",
        "kickplayer",
        "kick_path_capture_candidate",
        "kick_path_candidate",
        "list_player_capture_candidate",
        "list_player_candidate",
        "list_players_candidate",
        "server_kick_player",
        "server_list_players",
        "source_ready",
        "static_admin_thunk",
        "static_thunk",
        "route_candidate",
        "route_candidates",
        "command_candidate",
        "command_candidates",
        "command_source",
        "route_source",
        "admin_source",
        "live_posture",
        "live_server_posture",
        "runtime_posture",
        "server_posture",
        "plugin_hub",
        "plugin_hub_planning",
        "plugin_hub_publication",
        "plugin_hub_published",
        "publication",
        "published_to_plugin_hub",
        "release_publication",
        "sdk_package_shape",
        "stable_publication",
        "stable_release",
        "support_tier_metadata",
        "terminal_certificate",
        "terminal_status_certificate",
        "runtime_evidence_status",
        "runtime_evidence_status_report",
        "beta_notice_artifact",
        "side_lane",
        "side_lane_artifact",
        "side_lane_report",
        "standing_authority",
        "start_end_evidence",
        "start_end_only",
        "start_end_only_evidence",
        "transfer_b_accept_candidate",
        "transfer_b_accept_route",
        "transfer_baccept_candidate",
        "transfer_baccept_route",
    )
)
NON_EVIDENCE_ARTIFACT_CONTEXT_VALUE_KEYS = (
    NON_PROMOTION_ARTIFACT_SOURCE_KEYS
    | NON_EVIDENCE_ARTIFACT_NAME_KEYS
    | SOURCE_MARKER_KEYS
    | SOURCE_PROVENANCE_CONTEXT_KEYS
)
NON_EVIDENCE_ARTIFACT_CONTEXT_KEY_TERMS = frozenset(
    (
        *QUERY_ONLY_CANDIDATE_ALIAS_ARTIFACTS,
        "beta_notice",
        "diagnostic_candidate",
        "diagnostic_drift",
        "active_player_presence",
        "active_players",
        "admin_snapshot",
        "admin_status_snapshot",
        "beta",
        "player_presence",
        "discord",
        "observer_enabled",
        "observer_enablement",
        "live_posture",
        "live_server_posture",
        "no_users",
        "no_users_status",
        "package_shape",
        "package_shape_metadata",
        "passive_monitor",
        "runtime_evidence_status",
        "server_posture",
        "support_tier",
        "support_tier_metadata",
        "scoped_release_statement",
        "terminal_certificate",
        "terminal_status_certificate",
        "runtime_posture",
    )
)
FORBIDDEN_CERTIFICATE_REPORT_SCHEMA_REASONS = {
    "obelisk.player-principal-lifecycle-activation-preconditions.v1": (
        "player_identity_promotion_certificate_activation_precondition_report"
    ),
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1": (
        "player_identity_promotion_certificate_notice_send_attestation"
    ),
    "obelisk.player-principal-lifecycle-window-request-check.v1": (
        "player_identity_promotion_certificate_request_check_readiness_report"
    ),
    "obelisk.player-principal-lifecycle-evidence-closure-request.v1": (
        "player_identity_promotion_certificate_request_check_readiness_report"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-plan.v1": (
        "player_identity_promotion_certificate_runtime_window_artifact"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-authority-boundary.v1": (
        "player_identity_promotion_certificate_runtime_window_artifact"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-activation.v1": (
        "player_identity_promotion_certificate_runtime_window_artifact"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-execution.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-executor.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-executor-artifact.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-lifecycle-preactivation-executor-output.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-executor-closure.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1": (
        "player_identity_promotion_certificate_runtime_window_artifact"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-request-pack-reuse.v1": (
        "player_identity_promotion_certificate_runtime_window_artifact"
    ),
    "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1": (
        "player_identity_promotion_certificate_no_users_status"
    ),
    "obelisk.player-principal-lifecycle-ready-log-copy.v1": (
        "player_identity_promotion_certificate_copied_log_only_artifact"
    ),
    "obelisk.installed-sdk-package-shape.v1": (
        "player_identity_promotion_certificate_package_shape_install"
    ),
    "obelisk.installed-sdk-package-shape-support.v1": (
        "player_identity_promotion_certificate_support_tier_metadata"
    ),
    PLAYER_PRINCIPAL_LIFECYCLE_NEXT_ACTION_PLAN_SCHEMA: (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-contract.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-command.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-next-action-runner-operation.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-closure-machine-next-actions.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    "obelisk.player-principal-lifecycle-runtime-evidence-status-machine-next-actions.v1": (
        "player_identity_promotion_certificate_next_action_shortcut"
    ),
    PLAYER_PRINCIPAL_LIFECYCLE_RUNTIME_EVIDENCE_STATUS_SCHEMA: (
        "player_identity_promotion_certificate_status_report"
    ),
    REPORT_SCHEMA: "player_identity_promotion_certificate_public_readiness_report",
    NEXT_STEPS_SCHEMA: "player_identity_promotion_certificate_public_readiness_report",
    "obelisk.promoted-surface-test-execution.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.promoted-surface-test-execution-artifact.v1": (
        "player_identity_promotion_certificate_closure_or_executor_report"
    ),
    "obelisk.player-principal-passive-snapshot.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-snapshot-diff.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-snapshot-latest.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-observer-event-triage.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-actionability.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-target-triplet-candidate-summary.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-wait-metadata.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.passive-monitor-log-metadata.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.passive-organic-player-detection.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-server-activity-summary.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.player-principal-passive-activity-triage.v1": (
        "player_identity_promotion_certificate_passive_monitor_snapshot"
    ),
    "obelisk.command-permission-route-gate-check.v1": (
        "player_identity_promotion_certificate_route_alias_overclaim"
    ),
    BETA_CAPTURE_CANDIDATES_SCHEMA: (
        "player_identity_promotion_certificate_beta_capture_candidate"
    ),
    "obelisk.player-identity-public-contract-decision-record-check.v1": (
        "player_identity_promotion_certificate_decision_record_check_report"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_TEMPLATE_SCHEMA: (
        "player_identity_promotion_certificate_decision_record_template"
    ),
    PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_BUILD_REPORT_SCHEMA: (
        "player_identity_promotion_certificate_decision_record_build_report"
    ),
    PLAYER_IDENTITY_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA: (
        "player_identity_promotion_certificate_build_report_not_certificate"
    ),
    "obelisk.scoped-release-statement-outcomes.v1": (
        "player_identity_promotion_certificate_scoped_release_statement"
    ),
}
CERTIFICATE_ACTIVATION_ATTESTATION_KEYS = frozenset(
    (
        "activation_precondition_ready",
        "activation_preconditions_ready",
        "activation_precondition_met",
        "activation_preconditions_met",
        "counts_as_approved_runtime_evidence",
    )
)
CERTIFICATE_NOTICE_SEND_ATTESTATION_KEYS = frozenset(
    (
        "beta_notice_sent",
        "discord_sent",
        "discord_sent_by_this_report",
        "notice_send_attested",
        "notice_sent",
        "real_notice_send_attested",
    )
)
CERTIFICATE_REQUEST_CHECK_CONTAINER_KEYS = frozenset(
    (
        "request_check",
        "request_check_json",
        "request_pack_check",
        "window_request_check",
    )
)
CERTIFICATE_REQUEST_CHECK_READY_KEYS = frozenset(
    (
        "current_turn_approval_recorded",
        "operator_approval_receipt_verified",
        "request_pack_ready",
    )
)
CERTIFICATE_PARTIAL_IDENTITY_CONTRACT_KEYS = frozenset(
    (
        "partial_contract",
        "partial_contract_review",
        "partial_identity_contract",
        "partial_identity_contract_review",
        "partial_identity_public_contract",
        "partial_public_identity_contract",
    )
)
ADMIN_TARGETS_NOT_IDENTITY_SOURCES = frozenset(
    (
        "ShooterPlayerController.ServerListPlayers",
        "ShooterPlayerController.ServerKickPlayer",
    )
)
CERTIFICATE_COPIED_ADMIN_TARGET_KEYS = frozenset(
    (
        "accepted_admin_targets",
        "admin_target",
        "admin_targets",
        "copied_admin_target",
        "copied_admin_targets",
        "identity_source_target",
        "identity_source_targets",
        "principal_source_target",
        "principal_source_targets",
    )
)
CERTIFICATE_ROUTE_ALIAS_CONTAINER_KEYS = frozenset(
    (
        "post_evidence_p0_lock_simulation",
        "route_aliases",
        "route_blocker_aliases",
        "route_gate",
        "route_gate_report",
        "route_report",
    )
)
CERTIFICATE_ROUTE_ALIAS_OVERCLAIM_KEYS = frozenset(
    (
        "accepted_runtime_evidence_ready",
        "identity_public_contract_gate_missing_after_runtime_evidence",
        "permissions_admin_route_ready",
        "public_abi_gate_missing_after_runtime_evidence",
        "public_api_gate_missing_after_runtime_evidence",
        "public_header_gate_missing_after_runtime_evidence",
        "public_route_ready",
        "public_sdk_readiness_after_runtime_evidence",
        "route_gate_ready",
        "route_gate_unlocked",
        "route_ready",
        "runtime_readiness_after_runtime_evidence",
        "v1_completion_after_runtime_evidence",
    )
)
CERTIFICATE_ROUTE_ALIAS_VALUES = frozenset(
    (
        "identity_public_contract_gate_missing_after_runtime_evidence",
        "public_header_gate_missing",
        "public_header_gate_missing_after_runtime_evidence",
        "public_api_gate_missing",
        "public_api_gate_missing_after_runtime_evidence",
        "public_abi_gate_missing",
        "public_abi_gate_missing_after_runtime_evidence",
        "public_sdk_readiness_after_runtime_evidence",
        "runtime_readiness_after_runtime_evidence",
        "v1_completion_after_runtime_evidence",
    )
)
CERTIFICATE_NEXT_ACTION_SHORTCUT_KEYS = frozenset(
    (
        "activation_next_action_sequence",
        "machine_next_action",
        "machine_next_actions",
        "next_action",
        "next_action_plan",
        "next_action_report",
        "next_action_sequence",
        "next_actions",
        "post_window_next_action_sequence",
        "recommended_next_action",
        "required_next_action",
    )
)
CERTIFICATE_PASSIVE_NOTICE_STATUS_PUBLIC_READINESS_KEYS = frozenset(
    (
        "beta_notice",
        "beta_notice_artifact",
        "beta_notice_status",
        "notice_report",
        "notice_artifact",
        "notice_status",
        "passive_report",
        "passive_status",
        "handoff_notes",
        "public_readiness",
        "public_readiness_report",
        "runtime_evidence_status",
        "runtime_evidence_status_report",
        "side_lane",
        "status_report",
    )
)
CERTIFICATE_SUPPORT_TIER_SHORTCUT_KEYS = frozenset(
    (
        "package_shape_metadata",
        "package_shape_support",
        "package_shape_support_metadata",
        "support_tier",
        "support_tier_metadata",
        "support_tier_readiness",
        "support_tier_report",
    )
)
CERTIFICATE_TERMINAL_CERTIFICATE_KEYS = frozenset(
    (
        "terminal_certificate",
        "terminal_certificate_report",
        "terminal_completion_certificate",
        "terminal_readiness_certificate",
        "terminal_status_certificate",
    )
)
CERTIFICATE_GENERIC_POSITIVE_ALIAS_KEYS = frozenset(
    (
        "accepted",
        "accepted_for_contract_review",
        "accepted_for_planning",
        "approved",
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "claim_progress",
        "complete",
        "completed",
        "counts_as_approved_runtime_evidence",
        "counts_as_evidence",
        "counts_toward_p0",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_sdk",
        "current_turn_approval_recorded",
        "evidence_accepted",
        "evidence_closure_inputs_complete",
        "identity_contract_reviewed",
        "identity_observed",
        "identity_present",
        "identity_review_complete",
        "no_players_status_ready",
        "no_users_passive_wait_ready",
        "no_users_status_ready",
        "principal_observed",
        "principal_present",
        "progress",
        "promotion_ready",
        "public_header_allowed",
        "public_sdk_ready",
        "ready",
        "result",
        "review_status",
        "runtime_evidence_ready",
        "runtime_ready",
        "sdk_progress",
        "status",
        "unblocked",
        "v1_completion_evidence",
    )
)
CERTIFICATE_REVIEWED_TEMPLATE_ONLY_KEYS = frozenset(
    (
        "decision_record_template_only",
        "reviewed_decision_record_template_only",
        "reviewed_identity_contract_template_only",
        "reviewed_identity_public_contract_decision_record_template_only",
        "reviewed_template_only",
        "template_only",
    )
)
CERTIFICATE_GENERATED_OR_TEMPLATE_KEYS = frozenset(
    (
        "autogenerated",
        "auto_generated",
        "generated",
        "generated_artifact",
        "generated_by_template",
        "generated_from_template",
        "generated_only",
        "generated_template",
        "is_generated",
        "is_template",
        "placeholder",
        "placeholder_only",
        "scaffold",
        "scaffold_only",
        "template",
        "template_artifact",
        "template_generated",
        "template_only",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "blockers",
    "blocked",
    "compatibility_statement",
    "decision_required",
    "deny_or_unknown",
    "exclusion",
    "exclusions",
    "fail_closed",
    "forbidden",
    "must_never_return_allow",
    "non_claim",
    "not_sufficient",
    "promotion_requires",
    "required",
    "required_behavior",
    "required_exclusions",
    "required_properties",
    "claim_requires",
    "release_guardrails",
    "stable_release_contract",
    "shortcut_aliases_rejected",
    "shortcut_artifacts_never_count",
    "v1_sequence_gate",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|deny|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+not|need[s]?|never|no|not|"
    r"only|planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(
    r"(?<!\d)\.(?!\d)|[;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported|unresolved|.*\b(?:before|only|never|until|requires?)\b)",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
	    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
	    r"accepted\s+runtime\s+evidence|approved\s+runtime\s+evidence|admin\s+authority|beta|discord|P0|identity\s+(?:public\s+)?contract|identity\s+(?:present|observed)|"
	    r"query[-_ ]?only[-_ ]?diagnostics?|standing\s+authority|"
	    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
	    r"(?:machine[_ -]?)?next[_ -]?actions?(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"next[_ -]?action(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"command[_ -]?candidates?|route[_ -]?candidates?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
	    r"partial\s+identity\s+(?:public\s+)?contract|passive\s+(?:evidence|snapshot)|"
	    r"passive\s+(?:monitor|report|status|summary)|notice\s+(?:action|report|sent|status)|"
        r"no[-_ ]?(?:users|players)(?:[-_ ]?(?:passive[-_ ]?wait|status|detected))?|"
        r"runtime[-_ ]?window(?:[-_ ]?(?:artifact|plan|execution|closure|status))?|"
	    r"scoped\s+(?:non[-_ ]complete\s+)?(?:v1\s+)?release\s+statement|"
    r"copied\s+admin\s+target|RCON(?:\s+(?:command|route|status))?|ListPlayers|Kick|KickPlayer|"
    r"ServerListPlayers|ServerKickPlayer|static\s+(?:admin\s+)?thunks?|source[-_ ]ready|"
    r"player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"admin\s+mutation|command\s*/\s*chat\s+response|command[_ -]?rout(?:e|er|ing)|"
    r"command\s+chat\s+response|command\s+response(?:\s+path)?|commands?\s+repl(?:y|ies)|"
    r"capability\s+bits?|complete\s+sdk|full\s+sdk|permission[_ -]?cache|production\s+sdk|"
    r"public\s+(?:abi|capabilit(?:y|ies)|contract|headers?|sdk)|"
    r"permission\s+headers?|permissions?\s+quer(?:y|ies)|permissions?|principal|"
	    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
	    r"public[_ -]?readiness(?:[_ -]?(?:next[_ -]?action|report|status))?|"
	    r"public\s+route|route|route\s+gate|route\s+readiness|route[_ -]?ready|route[_ -]?snapshots?|"
	    r"Plugin[-_ ]?Hub(?:[-_ ]?(?:publication|published|readiness|planning|support|package|package[-_ ]?shape))?|"
	    r"publication|release\s+publication|public\s+release|release\s+readiness|stable\s+(?:publication|release|sdk)|v1(?:\.0)?\s+stable|v1\s+(?:sdk\s+)?completion|"
	    r"status\s+report|"
    r"permissions?/admin|reply\s+endpoint|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request|endpoint))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?|"
    r"live[_ -]?ops|server\s+operations|runtime\s+capture|workspace\s+writes?|live[_ -]?log(?:\s+reads?)?|"
    r"runtime(?:[_ -]?delivery)?"
    r")\b.{0,100}\b(accepted|advertised|allowed|authorized|available|delivered|enabled|established|live|met|opened|passed|promoted|public|published|reachable|ready|released|reviewed|sent|supported|unblocked|unlocked|verified)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_REVERSED_RE = re.compile(
    r"\b(accepted|advertised|allowed|authorized|available|delivered|enabled|established|live|met|opened|passed|promoted|public|published|reachable|ready|released|reviewed|sent|supported|unblocked|unlocked|verified)\b"
    r".{0,100}\b("
    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
	    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|"
	    r"accepted\s+runtime\s+evidence|approved\s+runtime\s+evidence|admin\s+authority|beta|discord|P0|identity\s+(?:public\s+)?contract|identity\s+(?:present|observed)|"
	    r"query[-_ ]?only[-_ ]?diagnostics?|standing\s+authority|"
	    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
	    r"(?:machine[_ -]?)?next[_ -]?actions?(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"next[_ -]?action(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"command[_ -]?candidates?|route[_ -]?candidates?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
	    r"partial\s+identity\s+(?:public\s+)?contract|passive\s+(?:evidence|snapshot)|"
	    r"passive\s+(?:monitor|report|status|summary)|notice\s+(?:action|report|sent|status)|"
        r"no[-_ ]?(?:users|players)(?:[-_ ]?(?:passive[-_ ]?wait|status|detected))?|"
        r"runtime[-_ ]?window(?:[-_ ]?(?:artifact|plan|execution|closure|status))?|"
	    r"scoped\s+(?:non[-_ ]complete\s+)?(?:v1\s+)?release\s+statement|"
    r"copied\s+admin\s+target|RCON(?:\s+(?:command|route|status))?|ListPlayers|Kick|KickPlayer|"
    r"ServerListPlayers|ServerKickPlayer|static\s+(?:admin\s+)?thunks?|source[-_ ]ready|"
    r"player\s+identity\s+public\s+contract|promotion\s+certificate|"
    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
    r"admin\s+mutation|command\s*/\s*chat\s+response|command[_ -]?rout(?:e|er|ing)|"
    r"command\s+chat\s+response|command\s+response(?:\s+path)?|commands?\s+repl(?:y|ies)|"
    r"capability\s+bits?|complete\s+sdk|full\s+sdk|permission[_ -]?cache|production\s+sdk|"
    r"public\s+(?:abi|capabilit(?:y|ies)|contract|headers?|sdk)|"
    r"permission\s+headers?|permissions?\s+quer(?:y|ies)|permissions?|principal|"
	    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
	    r"public[_ -]?readiness(?:[_ -]?(?:next[_ -]?action|report|status))?|"
	    r"public\s+route|route|route\s+gate|route\s+readiness|route[_ -]?ready|route[_ -]?snapshots?|"
	    r"Plugin[-_ ]?Hub(?:[-_ ]?(?:publication|published|readiness|planning|support|package|package[-_ ]?shape))?|"
	    r"publication|release\s+publication|public\s+release|release\s+readiness|stable\s+(?:publication|release|sdk)|v1(?:\.0)?\s+stable|v1\s+(?:sdk\s+)?completion|"
	    r"status\s+report|"
    r"permissions?/admin|reply\s+endpoint|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request|endpoint))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?|"
    r"live[_ -]?ops|server\s+operations|runtime\s+capture|workspace\s+writes?|live[_ -]?log(?:\s+reads?)?|"
    r"runtime(?:[_ -]?delivery)?"
    r")\b",
    re.IGNORECASE,
)
LOCK_BYPASS_NEGATED_CLAIM_RE = re.compile(
    r"\b(before|blocked|cannot|deny|does\s+not|fail[s-]?closed|forbidden|must|must\s+not|need[s]?|never|no|not|"
    r"planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
ZERO_PROGRESS_CLAIM_RE = re.compile(r"\b0+(?:\.0+)?\s*(?:/|%|percent)\b", re.IGNORECASE)
LOCK_BYPASS_CLAIM_RE = re.compile(
    r"\b("
	    r"accepted\s+runtime\s+evidence\s+(?:only|alone|sufficient)|"
	    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
	    r"(?:machine[_ -]?)?next[_ -]?actions?(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"next[_ -]?action(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|beta|discord|P0|"
    r"query[_ -]?only[_ -]?diagnostics?|standing[_ -]?authority|"
    r"identity[_ -]?(?:present|observed)|principal[_ -]?(?:present|observed)|"
    r"no[_ -]?(?:users|players)(?:[_ -]?(?:passive[_ -]?wait|status|detected))?|"
    r"runtime[_ -]?window(?:[_ -]?(?:artifacts?|plans?|execution|closures?|status))?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"command[_ -]?candidates?|route[_ -]?candidates?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
	    r"partial[_ -]?identity[_ -]?(?:public[_ -]?)?contract|passive[_ -]?(?:evidence|snapshot)|"
	    r"passive[_ -]?(?:monitor|report|status|summary)|notice[_ -]?(?:action|report|sent|status)|"
	    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statement|"
    r"copied[_ -]?admin[_ -]?target|RCON(?:[_ -]?(?:command|route|status))?|ListPlayers|Kick|KickPlayer|"
    r"ServerListPlayers|ServerKickPlayer|static[_ -]?(?:admin[_ -]?)?thunks?|source[-_ ]ready|"
	    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
	    r"public[_ -]?readiness(?:[_ -]?(?:next[_ -]?action|report|status))?|"
	    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
	    r"status[_ -]?reports?|"
	    r"permissions?(?:/admin)?|permission[_ -]?(?:query|header|admin)?|permissions?[_ -]?admin|public[_ -]?headers?|"
    r"route[_ -]?acceptance|route[_ -]?accepted|route[_ -]?blockers?|route[_ -]?bypass|route[_ -]?snapshots?|"
    r"dependency[_ -]?gate|dependency[_ -]?route|p0[_ -]?(?:completion|dependency|progress|release|surface)|"
    r"public[_ -]?runtime[_ -]?readiness|runtime[_ -]?readiness|live[_ -]?(?:ops|operations)|live[_ -]?server|production[_ -]?server"
    r")\b.{0,100}\b("
    r"accept(?:ed|s)?|allow(?:ed|s)?|authoriz(?:ed|es)?|bypass(?:ed|es)?|count(?:ed|s)?|enable(?:d|s)?|"
    r"open(?:ed|s)?|promot(?:ed|es)?|ready|satisf(?:ied|ies)|sufficient|unblock(?:ed|s)?|unlock(?:ed|s)?"
    r")\b",
    re.IGNORECASE,
)
LOCK_BYPASS_CLAIM_REVERSED = re.compile(
    r"\b("
    r"accept(?:ed|s)?|allow(?:ed|s)?|authoriz(?:ed|es)?|bypass(?:ed|es)?|count(?:ed|s)?|enable(?:d|s)?|"
    r"open(?:ed|s)?|promot(?:ed|es)?|ready|satisf(?:ied|ies)|sufficient|unblock(?:ed|s)?|unlock(?:ed|s)?"
    r")\b.{0,100}\b("
	    r"accepted\s+runtime\s+evidence\s+(?:only|alone|sufficient)|"
	    r"(?:agent[_ -]?)?handoff(?:[_ -]?(?:notes?|reports?|summar(?:y|ies)))?|"
	    r"(?:machine[_ -]?)?next[_ -]?actions?(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"next[_ -]?action(?:[_ -]?(?:plans?|reports?|sequence|status))?|"
	    r"activation[_ -]?preconditions?(?:[_ -]?(?:artifacts?|reports?))?|"
    r"(?:beta[_ -]?)?notice[_ -]?actions?(?:[_ -]?reports?)?|beta[_ -]?notices?|discord[_ -]?notices?|beta|discord|P0|"
    r"query[_ -]?only[_ -]?diagnostics?|standing[_ -]?authority|"
    r"identity[_ -]?(?:present|observed)|principal[_ -]?(?:present|observed)|"
    r"no[_ -]?(?:users|players)(?:[_ -]?(?:passive[_ -]?wait|status|detected))?|"
    r"runtime[_ -]?window(?:[_ -]?(?:artifacts?|plans?|execution|closures?|status))?|"
    r"(?:accepted[_ -]?)?runtime[_ -]?simulations?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response[_ -]?|authz[_ -]?response[_ -]?|response[_ -]?)?bridge[_ -]?reports?|"
    r"(?:command[_ -]?principal[_ -]?authz[_ -]?response|authz[_ -]?response|response)[_ -]?bridge|"
    r"precondition[_ -]?(?:artifacts?|reports?)|"
    r"side[_ -]?lane(?:[_ -]?(?:artifacts?|reports?|candidate|candidates))?|"
    r"public[_ -]?contract[_ -]?records?(?:[_ -]?packages?)?|"
    r"support[_ -]?tiers?(?:[_ -]?(?:readiness|reports?))?|"
    r"support[_ -]?tier[_ -]?(?:packages?|package[_ -]?shapes?)|"
    r"(?:support[_ -]?)?package[_ -]?shapes?|"
    r"command[_ -]?candidates?|route[_ -]?candidates?|"
    r"command[_ -]?planning(?:[_ -]?(?:packages?|package[_ -]?shapes?))?|"
    r"command[_ -]?(?:chat[_ -]?)?response[_ -]?planning(?:[_ -]?packages?)?|"
    r"copied[_ -]?(?:response[_ -]?)?intent(?:[_ -]?planning)?(?:[_ -]?packages?|[_ -]?package[_ -]?shapes?)?|"
	    r"partial[_ -]?identity[_ -]?(?:public[_ -]?)?contract|passive[_ -]?(?:evidence|snapshot)|"
	    r"passive[_ -]?(?:monitor|report|status|summary)|notice[_ -]?(?:action|report|sent|status)|"
	    r"scoped[_ -]?(?:non[-_ ]complete[_ -]?)?(?:v1[_ -]?)?release[_ -]?statement|"
    r"copied[_ -]?admin[_ -]?target|RCON(?:[_ -]?(?:command|route|status))?|ListPlayers|Kick|KickPlayer|"
    r"ServerListPlayers|ServerKickPlayer|static[_ -]?(?:admin[_ -]?)?thunks?|source[-_ ]ready|"
	    r"identity[_ -]?public[_ -]?contract[_ -]?gate[_ -]?missing|"
	    r"public[_ -]?readiness(?:[_ -]?(?:next[_ -]?action|report|status))?|"
	    r"public[_ -]?reachability|request[_ -]?checks?|request[_ -]?packs?|"
	    r"status[_ -]?reports?|"
	    r"permissions?(?:/admin)?|permission[_ -]?(?:query|header|admin)?|permissions?[_ -]?admin|public[_ -]?headers?|"
    r"route[_ -]?acceptance|route[_ -]?accepted|route[_ -]?blockers?|route[_ -]?bypass|route[_ -]?snapshots?|"
    r"dependency[_ -]?gate|dependency[_ -]?route|p0[_ -]?(?:completion|dependency|progress|release|surface)|"
    r"public[_ -]?runtime[_ -]?readiness|runtime[_ -]?readiness|live[_ -]?(?:ops|operations)|live[_ -]?server|production[_ -]?server"
    r")\b",
    re.IGNORECASE,
)
SHORTCUT_ARTIFACT_CLAIM_RE = re.compile(
    r"\b("
    r"copied[-_ ]?(?:obelisk[-_ ]?)?log(?:[-_ ]?(?:only|artifacts?|bundles?|copies|metadata))?|"
    r"copied[-_ ]?log[-_ ]?only[-_ ]?artifacts?|"
    r"(?:agent[-_ ]?)?handoff(?:[-_ ]?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"compact[-_ ]?contexts?|compact[-_ ]?summar(?:y|ies)|"
    r"installed[-_ ]?sdk[-_ ]?package[-_ ]?shape|sdk[-_ ]?package[-_ ]?shape|"
    r"query[-_ ]?only[-_ ]?diagnostics?|standing[-_ ]?authority|"
    r"package[-_ ]?shape(?:[-_ ]?(?:checks?|evidence|installs?|install[-_ ]?success|public[-_ ]?package))?|"
    r"package[-_ ]?shape[-_ ]?support|"
    r"support[-_ ]?tier(?:[-_ ]?(?:metadata|readiness|reports?|package[-_ ]?shape|support))?|"
    r"terminal[-_ ]?(?:certificates?|status|completion|readiness|reports?)|"
    r"runtime[-_ ]?evidence[-_ ]?status(?:[-_ ]?reports?)?|"
    r"beta[-_ ]?notice(?:[-_ ]?(?:artifacts?|reports?|status))?|beta|discord|P0|"
    r"package[-_ ]?installs?|install(?:ed)?[-_ ]?sdk(?:[-_ ]?package[-_ ]?shape)?|"
    r"no[-_ ]?(?:users|players)(?:[-_ ]?(?:passive[-_ ]?wait|status|detected))?|"
    r"passive[-_ ]?summar(?:y|ies)|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:artifacts?|plans?|execution|closures?|status))?|"
    r"command[-_ ]?candidates?|route[-_ ]?candidates?|"
    r"RCON(?:[-_ ]?(?:command|route|status|candidates?))?|"
    r"admin[-_ ]?(?:route[-_ ]?|status[-_ ]?)?snapshots?(?:[-_ ]?(?:status|reports?|candidates?))?|"
    r"(?:server[-_ ]?)?list[-_ ]?players?(?:[-_ ]?(?:status|reports?|candidates?|capture))?|"
    r"(?:server[-_ ]?)?kick(?:[-_ ]?players?)?(?:[-_ ]?(?:status|reports?|candidates?|capture|path))?|"
    r"kick[-_ ]?path(?:[-_ ]?(?:status|reports?|candidates?|capture))?|"
    r"static[-_ ]?(?:admin[-_ ]?)?thunks?(?:[-_ ]?(?:status|reports?|candidates?))?|"
    r"source[-_ ]?ready|"
    r"Plugin[-_ ]?Hub(?:[-_ ]?(?:planning|publication|published|readiness|reports?|support|package|package[-_ ]?shape))?|"
    r"(?:public[-_ ]?)?release[-_ ]?publication|publication|published[-_ ]?to[-_ ]?Plugin[-_ ]?Hub|stable[-_ ]?(?:publication|release)|"
    r"side[-_ ]?lane(?:[-_ ]?(?:artifacts?|reports?|candidate|candidates))?"
    r")\b.{0,100}\b("
    r"accept(?:ed|s)?|allow(?:ed|s)?|authoriz(?:ed|es)?|count(?:ed|s)?|credit(?:ed|s)?|enable(?:d|s)?|"
    r"passed|progress|promot(?:ed|es)?|publish(?:ed|es)?|ready|releas(?:ed|es)?|satisf(?:ied|ies)|succeed(?:ed|s)?|success|support(?:ed|s)?|"
    r"unblock(?:ed|s)?|unlock(?:ed|s)?"
    r")\b",
    re.IGNORECASE,
)
SHORTCUT_ARTIFACT_CLAIM_REVERSED = re.compile(
    r"\b("
    r"accept(?:ed|s)?|allow(?:ed|s)?|authoriz(?:ed|es)?|count(?:ed|s)?|credit(?:ed|s)?|enable(?:d|s)?|"
    r"passed|progress|promot(?:ed|es)?|publish(?:ed|es)?|ready|releas(?:ed|es)?|satisf(?:ied|ies)|succeed(?:ed|s)?|success|support(?:ed|s)?|"
    r"unblock(?:ed|s)?|unlock(?:ed|s)?"
    r")\b.{0,100}\b("
    r"copied[-_ ]?(?:obelisk[-_ ]?)?log(?:[-_ ]?(?:only|artifacts?|bundles?|copies|metadata))?|"
    r"copied[-_ ]?log[-_ ]?only[-_ ]?artifacts?|"
    r"(?:agent[-_ ]?)?handoff(?:[-_ ]?(?:notes?|reports?|summar(?:y|ies)))?|"
    r"compact[-_ ]?contexts?|compact[-_ ]?summar(?:y|ies)|"
    r"installed[-_ ]?sdk[-_ ]?package[-_ ]?shape|sdk[-_ ]?package[-_ ]?shape|"
    r"query[-_ ]?only[-_ ]?diagnostics?|standing[-_ ]?authority|"
    r"package[-_ ]?shape(?:[-_ ]?(?:checks?|evidence|installs?|install[-_ ]?success|public[-_ ]?package))?|"
    r"package[-_ ]?shape[-_ ]?support|"
    r"support[-_ ]?tier(?:[-_ ]?(?:metadata|readiness|reports?|package[-_ ]?shape|support))?|"
    r"terminal[-_ ]?(?:certificates?|status|completion|readiness|reports?)|"
    r"runtime[-_ ]?evidence[-_ ]?status(?:[-_ ]?reports?)?|"
    r"beta[-_ ]?notice(?:[-_ ]?(?:artifacts?|reports?|status))?|beta|discord|P0|"
    r"package[-_ ]?installs?|install(?:ed)?[-_ ]?sdk(?:[-_ ]?package[-_ ]?shape)?|"
    r"no[-_ ]?(?:users|players)(?:[-_ ]?(?:passive[-_ ]?wait|status|detected))?|"
    r"passive[-_ ]?summar(?:y|ies)|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:artifacts?|plans?|execution|closures?|status))?|"
    r"command[-_ ]?candidates?|route[-_ ]?candidates?|"
    r"RCON(?:[-_ ]?(?:command|route|status|candidates?))?|"
    r"admin[-_ ]?(?:route[-_ ]?|status[-_ ]?)?snapshots?(?:[-_ ]?(?:status|reports?|candidates?))?|"
    r"(?:server[-_ ]?)?list[-_ ]?players?(?:[-_ ]?(?:status|reports?|candidates?|capture))?|"
    r"(?:server[-_ ]?)?kick(?:[-_ ]?players?)?(?:[-_ ]?(?:status|reports?|candidates?|capture|path))?|"
    r"kick[-_ ]?path(?:[-_ ]?(?:status|reports?|candidates?|capture))?|"
    r"static[-_ ]?(?:admin[-_ ]?)?thunks?(?:[-_ ]?(?:status|reports?|candidates?))?|"
    r"source[-_ ]?ready|"
    r"Plugin[-_ ]?Hub(?:[-_ ]?(?:planning|publication|published|readiness|reports?|support|package|package[-_ ]?shape))?|"
    r"(?:public[-_ ]?)?release[-_ ]?publication|publication|published[-_ ]?to[-_ ]?Plugin[-_ ]?Hub|stable[-_ ]?(?:publication|release)|"
    r"side[-_ ]?lane(?:[-_ ]?(?:artifacts?|reports?|candidate|candidates))?"
    r")\b",
    re.IGNORECASE,
)
NON_CREDIT_TRUE_MARKER_KEYS = frozenset(
    (
        "diagnostic_only",
        "non_authorizing",
        "non_evidence",
    )
)
PUBLIC_ABI_CONTEXT_TERMS = (
    "public_abi",
    "public_api",
    "public_callback_abi",
    "public_header",
    "plugin_abi",
    "sdk_abi",
)
IDENTITY_LOOKUP_HANDLE_TERMS = (
    "identity_handle",
    "identity_handles",
    "identity_lookup",
    "identity_resolver",
    "lookup_handle",
    "lookup_handles",
    "persistent_handle",
    "player_handle",
    "player_handles",
    "player_lookup",
    "player_resolver",
    "principal_lookup",
    "public_handle",
    "public_handles",
    "resolve_identity",
    "resolve_player",
    "resolve_principal",
    "resource_handle",
    "resourcehandle",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        help="Optional candidate-only permissions/admin query manifest.",
    )
    parser.add_argument(
        "--beta-capture-artifact",
        type=Path,
        help="Optional candidate/debug admin/list-player/kick-path beta capture manifest.",
    )
    parser.add_argument(
        "--current-route-blocker",
        choices=ALLOWED_ROUTE_BLOCKERS,
        default=CURRENT_ROUTE_BLOCKER,
        help="Parent identity-route blocker to mirror while this surface remains locked.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", path=str(path), detail=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"$.{label}", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"$.{label}", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"$.{label}", path=str(path))
        return None
    return payload


def normalized_key(key: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_source(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


def is_source_overclaim_key(key_name: str) -> bool:
    return (
        "source_overclaim" in key_name
        or "source_overclaims" in key_name
        or "source_overclaimed" in key_name
    )


def is_source_overclaim_count_key(key_name: str) -> bool:
    return (
        "count" in key_name
        or "flag_count" in key_name
        or "total_flag" in key_name
    )


def zero_source_overclaim_count_value(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value == 0
    if isinstance(value, str):
        return normalized_key(value) in {"0", "0_0", "zero"}
    return False


def contains_source_overclaim_zero_marker(value: Any, *, source_overclaim_context: bool = False) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = normalized_key(key)
            child_context = source_overclaim_context or is_source_overclaim_key(key_name)
            if child_context and is_source_overclaim_count_key(key_name) and zero_source_overclaim_count_value(child):
                return True
            if contains_source_overclaim_zero_marker(child, source_overclaim_context=child_context):
                return True
        return False
    if isinstance(value, list):
        return any(
            contains_source_overclaim_zero_marker(item, source_overclaim_context=source_overclaim_context)
            for item in value
        )
    return False


def source_overclaim_zero_has_positive_status_alias(value: dict[str, Any]) -> bool:
    return any(
        normalized_key(key) in SOURCE_STATUS_KEYS | SPLIT_CLAIM_VALUE_KEYS
        and broad_public_surface_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
    )


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_source(value) in {
            "accepted",
            "allowed",
            "available",
            "authorized",
            "enabled",
            "live",
            "met",
            "operational",
            "passed",
            "observed",
            "present",
            "promoted",
            "public",
            "published",
            "reachable",
            "ready",
            "released",
            "reviewed",
            "sent",
            "supported",
            "true",
            "unblocked",
            "unlocked",
            "verified",
            "yes",
        }
    return False


def contains_forbidden_pre_runtime_claim_source(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_source(value)
        return normalized in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES or any(
            term in normalized for term in FORBIDDEN_ADMIN_SOURCE_TERMS
        )
    if isinstance(value, list):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value.values())
    return False


def contains_non_promotion_artifact_term(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_source(value)
        return normalized in BARE_NON_EVIDENCE_SHORTCUT_KEYS or any(
            term in normalized for term in NON_PROMOTION_ARTIFACT_TERMS
        )
    if isinstance(value, list):
        return any(contains_non_promotion_artifact_term(item) for item in value)
    if isinstance(value, dict):
        return any(contains_non_promotion_artifact_term(item) for item in value.values())
    return False


def contains_admin_route_status_alias_term(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_source(value)
        return any(term in normalized for term in ADMIN_ROUTE_STATUS_ALIAS_TERMS)
    if isinstance(value, list):
        return any(contains_admin_route_status_alias_term(item) for item in value)
    if isinstance(value, dict):
        return any(contains_admin_route_status_alias_term(item) for item in value.values())
    return False


def contains_positive_value(value: Any) -> bool:
    if is_positive_claim_value(value):
        return True
    if isinstance(value, list):
        return any(contains_positive_value(item) for item in value)
    if isinstance(value, dict):
        return any(
            contains_positive_value(item)
            for key, item in value.items()
            if normalized_key(key) not in NON_CREDIT_TRUE_MARKER_KEYS
        )
    return False


def progress_claim_value_is_nonzero(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        normalized_key_value = normalized_key(value)
        if not normalized or normalized_key_value in {
            "0",
            "0_0",
            "0_percent",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
        }:
            return False
        if re.fullmatch(r"0+\s*/\s*[1-9]\d*", normalized):
            return False
        if re.fullmatch(r"0+(?:\.0+)?\s*(?:%|percent)", normalized):
            return False
        return True
    if isinstance(value, list):
        return any(progress_claim_value_is_nonzero(item) for item in value)
    if isinstance(value, dict):
        return any(progress_claim_value_is_nonzero(item) for item in value.values())
    return False


def broad_progress_or_credit_alias_key(key_name: str) -> bool:
    return (
        key_name in {
            "progress",
            "claim_progress",
            "claim_progress_contribution",
            "complete_sdk_claim_progress_contribution",
            "complete_sdk_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
            "public_sdk_progress_contribution",
            "runtime_progress_contribution",
            "v1_completion_contribution",
        }
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or BROAD_P0_PROGRESS_OR_CREDIT_ALIAS_RE.search(key_name) is not None
    )


def shortcut_artifact_alias_key(key_name: str) -> bool:
    return key_name in BARE_NON_EVIDENCE_SHORTCUT_KEYS or any(
        term in key_name for term in SHORTCUT_ARTIFACT_ALIAS_TERMS
    )


def broad_public_surface_alias_key(key_name: str) -> bool:
    if key_name in BROAD_P0_ALIAS_EXEMPT_KEYS:
        return False
    return (
        key_name in EXACT_PROMOTION_CREDIT_ALIAS_KEYS
        or key_name in FALSE_ONLY_KEYS
        or shortcut_artifact_alias_key(key_name)
        or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(key_name) is not None
        or key_name in PROMOTED_SURFACE_COUNT_ALIAS_KEYS
        or (
            BROAD_P0_ALIAS_SCOPE_RE.search(key_name) is not None
            and (
                BROAD_P0_ALIAS_STATE_RE.search(key_name) is not None
                or broad_progress_or_credit_alias_key(key_name)
            )
        )
        or key_name in {"progress", "claim_progress", "claim_progress_contribution"}
    )


def generic_nested_ready_or_progress_alias_key(key_name: str) -> bool:
    if key_name in BROAD_P0_ALIAS_EXEMPT_KEYS or key_name in NON_CREDIT_TRUE_MARKER_KEYS:
        return False
    if any(
        token in key_name
        for token in (
            "blocked_until",
            "forbidden",
            "must_remain",
            "never_count",
            "non_evidence",
            "not_sufficient",
            "rejected",
            "required",
            "requires",
            "shortcut_artifacts",
        )
    ):
        return False
    if key_name.endswith("_count") and key_name not in PROMOTED_SURFACE_COUNT_ALIAS_KEYS:
        return False
    return (
        broad_progress_or_credit_alias_key(key_name)
        or GENERIC_NESTED_READY_OVERCLAIM_KEY_RE.search(key_name) is not None
    )


def broad_public_surface_alias_value_is_positive(key_name: str, value: Any) -> bool:
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    return contains_positive_value(value)


def non_evidence_artifact_context_key(key_name: str) -> bool:
    return (
        "non_evidence_artifacts" in key_name
        or shortcut_artifact_alias_key(key_name)
        or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(key_name) is not None
        or any(term in key_name for term in NON_EVIDENCE_ARTIFACT_CONTEXT_KEY_TERMS)
    )


def non_evidence_artifact_context_value(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_source(value)
        return (
            normalized in BARE_NON_EVIDENCE_SHORTCUT_KEYS
            or
            shortcut_artifact_alias_key(normalized)
            or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(normalized) is not None
            or any(term in normalized for term in NON_PROMOTION_ARTIFACT_TERMS)
        )
    if isinstance(value, list):
        return any(non_evidence_artifact_context_value(item) for item in value)
    if isinstance(value, dict):
        return any(non_evidence_artifact_context_value(item) for item in value.values())
    return False


def dict_declares_non_evidence_artifact_context(value: dict[str, Any]) -> bool:
    return any(
        normalized_key(key) in NON_EVIDENCE_ARTIFACT_CONTEXT_VALUE_KEYS
        and non_evidence_artifact_context_value(child)
        for key, child in value.items()
    )


def dict_declares_admin_route_status_alias_context(value: dict[str, Any]) -> bool:
    return any(
        normalized_key(key) in ADMIN_ROUTE_STATUS_ALIAS_SOURCE_KEYS
        and contains_admin_route_status_alias_term(child)
        for key, child in value.items()
    )


def non_evidence_artifact_claim_name_key(key_name: str) -> bool:
    return key_name in SPLIT_CLAIM_NAME_KEYS or key_name in NON_EVIDENCE_ARTIFACT_NAME_KEYS


def non_evidence_artifact_credit_key(key_name: str) -> bool:
    if key_name in NON_CREDIT_TRUE_MARKER_KEYS:
        return False
    return (
        NON_EVIDENCE_ARTIFACT_CREDIT_KEY_RE.search(key_name) is not None
        or broad_progress_or_credit_alias_key(key_name)
        or shortcut_artifact_alias_key(key_name)
    )


def non_evidence_artifact_credit_value_is_positive(key_name: str, value: Any) -> bool:
    if broad_progress_or_credit_alias_key(key_name) and progress_claim_value_is_nonzero(value):
        return True
    return contains_positive_value(value)


def source_marker_value_is_non_authorizing(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in EXACT_PROMOTION_CREDIT_ALIAS_KEYS
            or
            shortcut_artifact_alias_key(normalized)
            or NON_AUTHORIZING_ROUTE_ALIAS_CONTEXT_RE.search(normalized) is not None
            or alias_requires_upstream_certificates(normalized)
            or identity_gate_alias_requires_upstream(normalized)
            or (
                BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
                and (
                    BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
                    or broad_progress_or_credit_alias_key(normalized)
                )
            )
        )
    if isinstance(value, list):
        return any(source_marker_value_is_non_authorizing(item) for item in value)
    if isinstance(value, dict):
        return any(source_marker_value_is_non_authorizing(item) for item in value.values())
    return False


def source_marker_value_claims_positive_alias(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return (
            normalized in EXACT_PROMOTION_CREDIT_ALIAS_KEYS
            or
            shortcut_artifact_alias_key(normalized)
            or alias_requires_upstream_certificates(normalized)
            or identity_gate_alias_requires_upstream(normalized)
            or (
                BROAD_P0_ALIAS_SCOPE_RE.search(normalized) is not None
                and (
                    BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None
                    or broad_progress_or_credit_alias_key(normalized)
                )
            )
        )
    if isinstance(value, list):
        return any(source_marker_value_claims_positive_alias(item) for item in value)
    if isinstance(value, dict):
        return any(source_marker_value_claims_positive_alias(item) for item in value.values())
    return False


def provenance_value_marks_non_authorizing_context(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        return source_marker_value_is_non_authorizing(value) or any(
            term in normalized
            for term in (
                "accepted_runtime_evidence",
                "approved_runtime_evidence",
                "identity_public_contract_decision_record",
                "public_contract_decision_record",
                "reviewed_hash_current_contract_review_only",
                "reviewed_identity_public_contract",
                "route_snapshot",
            )
        )
    if isinstance(value, list):
        return any(provenance_value_marks_non_authorizing_context(item) for item in value)
    if isinstance(value, dict):
        return any(provenance_value_marks_non_authorizing_context(item) for item in value.values())
    return False


def split_source_marker_status_overclaims(value: dict[str, Any]) -> bool:
    marker_values = [
        child
        for key, child in value.items()
        if normalized_key(key) in SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
    ]
    if not marker_values or not any(provenance_value_marks_non_authorizing_context(item) for item in marker_values):
        return False
    return any(
        broad_public_surface_alias_value_is_positive(normalized_key(key), child)
        for key, child in value.items()
        if normalized_key(key) in SOURCE_STATUS_KEYS
    )


def contains_request_check_readiness(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = normalized_key(key)
            if key_name in CERTIFICATE_REQUEST_CHECK_READY_KEYS and contains_positive_value(child):
                return True
            if key_name == "ready" and is_positive_claim_value(child):
                return True
            if contains_request_check_readiness(child):
                return True
        return False
    if isinstance(value, list):
        return any(contains_request_check_readiness(item) for item in value)
    return False


def contains_route_alias_overclaim(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_source(value) in CERTIFICATE_ROUTE_ALIAS_VALUES
    if isinstance(value, dict):
        for key, child in value.items():
            key_name = normalized_key(key)
            if key_name in CERTIFICATE_ROUTE_ALIAS_OVERCLAIM_KEYS and contains_positive_value(child):
                return True
            if contains_route_alias_overclaim(child):
                return True
        return False
    if isinstance(value, list):
        return any(contains_route_alias_overclaim(item) for item in value)
    return False


def certificate_shortcut_schema_reason(schema: str, trail: str) -> str | None:
    if schema == PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA:
        if trail.endswith(".approved_runtime_evidence"):
            return None
        return "player_identity_promotion_certificate_runtime_evidence_substitute"
    if schema == PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA:
        if trail.endswith(".identity_public_contract_decision_record"):
            return None
        return "player_identity_promotion_certificate_decision_record_substitute"
    normalized_schema = normalized_key(schema)
    if "terminal" in normalized_schema and "certificate" in normalized_schema:
        return "player_identity_promotion_certificate_terminal_certificate"
    if "support_tier" in normalized_schema or "package_shape_support" in normalized_schema:
        return "player_identity_promotion_certificate_support_tier_metadata"
    if "runtime_evidence_status" in normalized_schema:
        return "player_identity_promotion_certificate_status_report"
    if "beta_notice" in normalized_schema:
        return "player_identity_promotion_certificate_notice_send_attestation"
    return FORBIDDEN_CERTIFICATE_REPORT_SCHEMA_REASONS.get(schema)


def certificate_dict_marks_non_promotion_shortcut(value: dict[str, Any], trail: str) -> bool:
    schema = value.get("schema")
    if isinstance(schema, str) and certificate_shortcut_schema_reason(schema, trail) is not None:
        return True
    return any(
        normalized_key(key) in NON_PROMOTION_ARTIFACT_SOURCE_KEYS
        and contains_non_promotion_artifact_term(child)
        for key, child in value.items()
    )


def certificate_shortcut_value_is_positive(value: Any) -> bool:
    if contains_positive_value(value):
        return True
    if isinstance(value, str):
        normalized = normalized_key(value)
        if ZERO_PROGRESS_CLAIM_RE.fullmatch(value.strip()):
            return False
        return BROAD_P0_ALIAS_STATE_RE.search(normalized) is not None and not NEGATED_CLAIM_RE.search(value)
    if isinstance(value, list):
        return any(certificate_shortcut_value_is_positive(item) for item in value)
    if isinstance(value, dict):
        return any(certificate_shortcut_value_is_positive(item) for item in value.values())
    return False


def certificate_generic_positive_alias_key(key_name: str) -> bool:
    return (
        key_name in CERTIFICATE_GENERIC_POSITIVE_ALIAS_KEYS
        or key_name in SOURCE_STATUS_KEYS
        or broad_progress_or_credit_alias_key(key_name)
        or broad_public_surface_alias_key(key_name)
        or key_name.endswith("_ready")
        or key_name.endswith("_accepted")
        or key_name.endswith("_approved")
        or key_name.endswith("_complete")
        or key_name.endswith("_progress")
    )


def contains_admin_target(value: Any) -> bool:
    if isinstance(value, str):
        return value in ADMIN_TARGETS_NOT_IDENTITY_SOURCES
    if isinstance(value, list):
        return any(contains_admin_target(item) for item in value)
    if isinstance(value, dict):
        return any(contains_admin_target(item) for item in value.values())
    return False


def support_tier_value_claims_shortcut(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_key(value)
        if NEGATED_CLAIM_RE.search(value):
            return False
        shortcut_context = any(
            term in normalized
            for term in (
                "beta_notice",
                "identity_public_contract_gate_missing",
                "package_shape",
                "runtime_evidence_status",
                "support_tier",
                "terminal_certificate",
            )
        )
        shortcut_state = any(
            token in normalized
            for token in (
                "accepted",
                "complete",
                "count",
                "credit",
                "promoted",
                "ready",
                "supported",
                "unblocked",
                "unlocked",
            )
        )
        return (
            has_unnegated_certificate_gated_alias_claim(value)
            or has_unnegated_lock_bypass_claim(value)
            or has_unnegated_shortcut_artifact_claim(value)
            or (shortcut_context and shortcut_state)
        )
    if isinstance(value, list):
        return any(support_tier_value_claims_shortcut(item) for item in value)
    if isinstance(value, dict):
        return any(
            (
                normalized_key(key) in CERTIFICATE_SUPPORT_TIER_SHORTCUT_KEYS
                and certificate_shortcut_value_is_positive(child)
            )
            or support_tier_value_claims_shortcut(child)
            for key, child in value.items()
        )
    return False


def collect_forbidden_certificate_attestations(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str,
) -> None:
    if isinstance(value, dict):
        schema = value.get("schema")
        if isinstance(schema, str):
            reason = certificate_shortcut_schema_reason(schema, trail)
            if reason is not None:
                add(blockers, reason, f"{trail}.schema", schema=schema)
        non_promotion_shortcut_context = certificate_dict_marks_non_promotion_shortcut(value, trail)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if (
                non_promotion_shortcut_context
                and certificate_generic_positive_alias_key(key_name)
                and certificate_shortcut_value_is_positive(child)
            ):
                add(
                    blockers,
                    "player_identity_promotion_certificate_generic_positive_alias",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_ACTIVATION_ATTESTATION_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_activation_precondition_report",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_NOTICE_SEND_ATTESTATION_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_notice_send_attestation",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_REQUEST_CHECK_READY_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_request_check_readiness_report",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_REQUEST_CHECK_CONTAINER_KEYS and contains_request_check_readiness(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_request_check_readiness_report",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_PARTIAL_IDENTITY_CONTRACT_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_partial_identity_contract",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_COPIED_ADMIN_TARGET_KEYS and contains_admin_target(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_copied_admin_target",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_ROUTE_ALIAS_OVERCLAIM_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_route_alias_overclaim",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_ROUTE_ALIAS_CONTAINER_KEYS and contains_route_alias_overclaim(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_route_alias_overclaim",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_NEXT_ACTION_SHORTCUT_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_next_action_shortcut",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_PASSIVE_NOTICE_STATUS_PUBLIC_READINESS_KEYS and contains_positive_value(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_public_readiness_shortcut",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_SUPPORT_TIER_SHORTCUT_KEYS and support_tier_value_claims_shortcut(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_support_tier_metadata",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_TERMINAL_CERTIFICATE_KEYS and certificate_shortcut_value_is_positive(child):
                add(
                    blockers,
                    "player_identity_promotion_certificate_terminal_certificate",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_REVIEWED_TEMPLATE_ONLY_KEYS and child is True:
                add(
                    blockers,
                    "player_identity_promotion_certificate_reviewed_template_only",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            if key_name in CERTIFICATE_GENERATED_OR_TEMPLATE_KEYS and child is True:
                add(
                    blockers,
                    "player_identity_promotion_certificate_generated_or_template_artifact",
                    child_trail,
                    field=str(key),
                    value=child,
                )
            collect_forbidden_certificate_attestations(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_forbidden_certificate_attestations(child, blockers, f"{trail}[{index}]")


def collect_non_promotion_artifact_sources(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str,
    reason: str,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                normalized_key(key) in NON_PROMOTION_ARTIFACT_SOURCE_KEYS
                and contains_non_promotion_artifact_term(child)
            ):
                add(blockers, reason, child_trail, field=str(key), value=child)
            collect_non_promotion_artifact_sources(child, blockers, child_trail, reason)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_non_promotion_artifact_sources(child, blockers, f"{trail}[{index}]", reason)


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def is_claim_container_context(trail: str) -> bool:
    segments = (segment.split("[", 1)[0] for segment in trail.split("."))
    return any(
        normalized_key(segment) in {"blocker", "blockers", "block_reasons", "why_blocked"}
        for segment in segments
    )


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def planning_word_is_claim_subject(text: str) -> bool:
    normalized = normalized_key(text)
    return any(
        term in normalized
        for term in (
            "command_planning",
            "command_response_planning",
            "copied_response_intent_planning",
            "plugin_hub_planning",
        )
    )


def negation_is_only_planning_word(text: str, regex: re.Pattern[str]) -> bool:
    matches = list(regex.finditer(text))
    return bool(matches) and planning_word_is_claim_subject(text) and all(
        normalized_key(match.group(0)) == "planning" for match in matches
    )


def remove_non_negating_no_users_phrase(text: str) -> str:
    return re.sub(r"\bno[-_ ]+(?:users|players)\b", "empty_player_status", text, flags=re.IGNORECASE)


def claim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    match_text = remove_non_negating_no_users_phrase(match.group(0))
    if NEGATED_CLAIM_RE.search(match_text) and not negation_is_only_planning_word(match_text, NEGATED_CLAIM_RE):
        return True
    if NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def shortcut_artifact_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if "copied_log_only" not in normalized_key(match.group(0)):
        return claim_match_is_negated(text, match)
    match_text = re.sub(r"copied[-_ ]?log[-_ ]?only", "copied log artifact", match.group(0), flags=re.IGNORECASE)
    if NEGATED_CLAIM_RE.search(match_text) and not negation_is_only_planning_word(match_text, NEGATED_CLAIM_RE):
        return True
    if NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def lock_bypass_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if ZERO_PROGRESS_CLAIM_RE.search(match.group(0)):
        return True
    if "normalized_only_to_identity_public_contract_gate_missing" in normalized_key(match.group(0)):
        return True
    if LOCK_BYPASS_NEGATED_CLAIM_RE.search(match.group(0)) and not negation_is_only_planning_word(
        match.group(0),
        LOCK_BYPASS_NEGATED_CLAIM_RE,
    ):
        return True
    if LOCK_BYPASS_NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def has_unnegated_positive_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_CLAIM_RE, POSITIVE_CLAIM_REVERSED_RE):
            for match in regex.finditer(clause):
                if not claim_match_is_negated(clause, match):
                    return True
    return False


def has_unnegated_lock_bypass_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (LOCK_BYPASS_CLAIM_RE, LOCK_BYPASS_CLAIM_REVERSED):
            for match in regex.finditer(clause):
                if not lock_bypass_match_is_negated(clause, match):
                    return True
    return False


def has_unnegated_shortcut_artifact_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (SHORTCUT_ARTIFACT_CLAIM_RE, SHORTCUT_ARTIFACT_CLAIM_REVERSED):
            for match in regex.finditer(clause):
                if not shortcut_artifact_match_is_negated(clause, match):
                    return True
    return False


def has_unnegated_positive_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if "reviewed_identity_public_contract_decision_record" in normalized:
            continue
        if any(alias in normalized for alias in POSITIVE_ALIAS_CLAIMS):
            return True
    return False


def has_unnegated_certificate_gated_alias_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        if NEGATED_CLAIM_RE.search(clause):
            continue
        normalized = normalized_key(clause)
        if alias_requires_upstream_certificates(normalized) or identity_gate_alias_requires_upstream(normalized):
            return True
    return False


def has_unnegated_public_abi_identity_lookup_handle_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        normalized = normalized_key(clause)
        negated = any(
            match.group(0).casefold() != "before" or "resource_handle" not in normalized
            for match in NEGATED_CLAIM_RE.finditer(clause)
        )
        if negated:
            continue
        if any(term in normalized for term in PUBLIC_ABI_CONTEXT_TERMS) and any(
            term in normalized for term in IDENTITY_LOOKUP_HANDLE_TERMS
        ):
            return True
    return False


def alias_requires_upstream_certificates(normalized: str) -> bool:
    if "reviewed_identity_public_contract_decision_record" in normalized:
        return False
    if "accepted_runtime_evidence" in normalized and any(
        token in normalized for token in ("alone", "only", "sufficient")
    ):
        return True
    return any(alias in normalized for alias in CERTIFICATE_GATED_ALIAS_CLAIMS)


def identity_gate_alias_requires_upstream(normalized: str) -> bool:
    if "identity_public_contract_gate_missing" not in normalized:
        return False
    return any(token in normalized for token in IDENTITY_GATE_ALIAS_KEY_TOKENS)


def add_upstream_certificate_alias_blocker(
    blockers: list[dict[str, Any]],
    label: str,
    *,
    field: str | None = None,
    value: Any = None,
) -> None:
    details: dict[str, Any] = {
        "required_certificate_schemas": list(UPSTREAM_PROMOTION_CERTIFICATE_SCHEMAS),
        "required_certificate_binding": REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
    }
    if field is not None:
        details["field"] = field
    if value is not None:
        details["value"] = value
    add(blockers, "route_or_runtime_readiness_alias_missing_upstream_certificates", label, **details)


def c_identifier_exact_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def c_identifier_prefix_re(prefix: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(prefix)}[A-Za-z0-9_]*")


def approved_runtime_evidence_binding_is_canonical(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if set(value) != APPROVED_RUNTIME_EVIDENCE_BINDING_REQUIRED_KEYS:
        return False
    if any(value.get(key) != expected for key, expected in APPROVED_RUNTIME_EVIDENCE_BINDING_EXPECTED_VALUES.items()):
        return False
    if any(value.get(key) is not False for key in APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS):
        return False
    non_claim = value.get("non_claim")
    return isinstance(non_claim, str) and bool(non_claim.strip())


def accepted_runtime_evidence_record_is_canonical(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == ACCEPTED_RUNTIME_EVIDENCE_REQUIRED_KEYS
        and value.get("schema") == PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA
        and value.get("result") == "approved runtime principal lifecycle evidence"
        and value.get("next_blocker") == IDENTITY_CONTRACT_ROUTE_BLOCKER
        and value.get("approved_runtime_evidence_binding_required") is True
        and approved_runtime_evidence_binding_is_canonical(value.get("approved_runtime_evidence_binding"))
    )


def collect_overclaims(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str = "$",
    *,
    artifact_context: bool = False,
) -> None:
    if isinstance(value, dict):
        if (
            contains_source_overclaim_zero_marker(value)
            and source_overclaim_zero_has_positive_status_alias(value)
        ):
            add(blockers, "source_overclaim_zero_status_alias_overclaim", trail, value=value)
        admin_route_status_alias_context = dict_declares_admin_route_status_alias_context(value)
        current_artifact_context = (
            artifact_context
            or non_evidence_artifact_context_key(normalized_key(trail))
            or dict_declares_non_evidence_artifact_context(value)
            or admin_route_status_alias_context
        )
        source_marker_context = any(
            provenance_value_marks_non_authorizing_context(child)
            for key, child in value.items()
            if normalized_key(key) in SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
        )
        if split_source_marker_status_overclaims(value):
            add(blockers, "public_surface_overclaim", trail, value=value)
        declared_claim_names = [
            str(item)
            for key, item in value.items()
            if (
                normalized_key(key) in SPLIT_CLAIM_NAME_KEYS
                or (current_artifact_context and non_evidence_artifact_claim_name_key(normalized_key(key)))
            )
            and isinstance(item, str)
        ]
        declared_claim_values = [
            item
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        declared_artifact_claim_value_pairs = [
            (normalized_key(key), item)
            for key, item in value.items()
            if normalized_key(key) in SPLIT_CLAIM_VALUE_KEYS
            or non_evidence_artifact_credit_key(normalized_key(key))
        ]
        for claim_name in declared_claim_names:
            claim_key = normalized_key(claim_name)
            positive_claim_value = any(
                broad_public_surface_alias_value_is_positive(claim_key, item)
                for item in declared_claim_values
            )
            artifact_claim_value = any(
                non_evidence_artifact_credit_value_is_positive(value_key, item)
                for value_key, item in declared_artifact_claim_value_pairs
            )
            if (
                current_artifact_context
                and (
                    non_evidence_artifact_credit_key(claim_key)
                    or shortcut_artifact_alias_key(claim_key)
                )
                and artifact_claim_value
            ):
                add(blockers, "non_evidence_artifact_credit_overclaim", trail, field=claim_name, value=value)
            if broad_public_surface_alias_key(claim_key) and positive_claim_value:
                add(blockers, "public_surface_overclaim", trail, field=claim_name, value=value)
            identity_gate_alias = identity_gate_alias_requires_upstream(claim_key)
            if identity_gate_alias and positive_claim_value and not broad_public_surface_alias_key(claim_key):
                add(blockers, "public_surface_overclaim", trail, field=claim_name, value=value)
            if (alias_requires_upstream_certificates(claim_key) or identity_gate_alias) and positive_claim_value:
                add_upstream_certificate_alias_blocker(blockers, trail, field=claim_name, value=value)
            if (
                claim_key in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                and contains_forbidden_pre_runtime_claim_source(declared_claim_values)
            ):
                add(blockers, "pre_runtime_principal_or_authority_claim_source", trail, field=claim_name, value=value)
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name == "accepted_runtime_evidence" and accepted_runtime_evidence_record_is_canonical(child):
                continue
            if key_name == "approved_runtime_evidence_binding_required" and child is True:
                continue
            if (
                key_name == "approved_runtime_evidence_binding"
                and approved_runtime_evidence_binding_is_canonical(child)
            ):
                continue
            child_artifact_context = current_artifact_context or non_evidence_artifact_context_key(key_name)
            child_artifact_positive = non_evidence_artifact_credit_value_is_positive(key_name, child)
            child_positive_claim_value = broad_public_surface_alias_value_is_positive(key_name, child)
            if (
                child_artifact_context
                and "non_evidence_artifacts" not in key_name
                and (non_evidence_artifact_context_key(key_name) or non_evidence_artifact_credit_key(key_name))
                and child_artifact_positive
            ):
                add(blockers, "non_evidence_artifact_credit_overclaim", child_trail, field=str(key), value=child)
            if (
                key_name in SOURCE_MARKER_KEYS | SOURCE_PROVENANCE_CONTEXT_KEYS
                and source_marker_value_claims_positive_alias(child)
            ):
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if key_name in SOURCE_STATUS_KEYS and source_marker_context and child_positive_claim_value:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if (
                admin_route_status_alias_context
                and key_name in SOURCE_STATUS_KEYS | SPLIT_CLAIM_VALUE_KEYS
                and child_positive_claim_value
            ):
                add_upstream_certificate_alias_blocker(blockers, child_trail, field=str(key), value=child)
            if key_name in CERTIFICATE_SUPPORT_TIER_SHORTCUT_KEYS and support_tier_value_claims_shortcut(child):
                add(blockers, "non_evidence_artifact_credit_overclaim", child_trail, field=str(key), value=child)
                add_upstream_certificate_alias_blocker(blockers, child_trail, field=str(key), value=child)
            if key_name in CERTIFICATE_TERMINAL_CERTIFICATE_KEYS and child_positive_claim_value:
                add(blockers, "non_evidence_artifact_credit_overclaim", child_trail, field=str(key), value=child)
                add_upstream_certificate_alias_blocker(blockers, child_trail, field=str(key), value=child)
            if key_name in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            elif broad_public_surface_alias_key(key_name) and child_positive_claim_value:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            elif (
                generic_nested_ready_or_progress_alias_key(key_name)
                and broad_public_surface_alias_value_is_positive(key_name, child)
            ):
                add(blockers, "generic_readiness_or_progress_alias_overclaim", child_trail, field=str(key), value=child)
            identity_gate_alias = identity_gate_alias_requires_upstream(key_name)
            if identity_gate_alias and child_positive_claim_value and not broad_public_surface_alias_key(key_name):
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if (alias_requires_upstream_certificates(key_name) or identity_gate_alias) and child_positive_claim_value:
                add_upstream_certificate_alias_blocker(blockers, child_trail, field=str(key), value=child)
            if (
                key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                and contains_forbidden_pre_runtime_claim_source(child)
            ):
                add(blockers, "pre_runtime_principal_or_authority_claim_source", child_trail, field=str(key), value=child)
            collect_overclaims(child, blockers, child_trail, artifact_context=child_artifact_context)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_overclaims(child, blockers, f"{trail}[{index}]", artifact_context=artifact_context)
        return
    support_tier_trail = trail.endswith(".support_tier")
    if (
        not isinstance(value, str)
        or trail.endswith(".schema")
        or trail.endswith(".surface")
        or trail.endswith(".id")
        or (support_tier_trail and not support_tier_value_claims_shortcut(value))
    ):
        return
    if "non_evidence_artifacts" in normalized_key(trail):
        return
    if has_unnegated_public_abi_identity_lookup_handle_claim(value):
        add(blockers, "public_abi_identity_lookup_handle_claim", trail, value=value)
    if is_negative_context(trail) and not is_claim_container_context(trail):
        return
    if (
        has_unnegated_positive_claim(value)
        or has_unnegated_positive_alias_claim(value)
        or has_unnegated_lock_bypass_claim(value)
        or has_unnegated_shortcut_artifact_claim(value)
    ):
        add(blockers, "positive_public_surface_claim", trail, value=value)
    if has_unnegated_certificate_gated_alias_claim(value) or support_tier_trail:
        add_upstream_certificate_alias_blocker(blockers, trail, value=value)


def declared_header_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def scanned_header_is_repo_path(path: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return True


def validate_public_header_declaration(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    source: str,
    scanned_path: Path,
) -> None:
    declared = payload.get("public_header")
    if declared != DEFAULT_PUBLIC_HEADER_DECL:
        add(
            blockers,
            f"{source}_public_header_mismatch",
            f"$.{source}.public_header",
            expected=DEFAULT_PUBLIC_HEADER_DECL,
            value=declared,
        )
    declared_path = declared_header_path(declared)
    if declared_path is None:
        return
    if scanned_header_is_repo_path(scanned_path) and declared_path.resolve() != scanned_path.expanduser().resolve():
        add(
            blockers,
            f"{source}_public_header_not_scanned_header",
            f"$.{source}.public_header",
            declared=str(declared_path),
            scanned=str(scanned_path),
        )


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]], public_header_path: Path) -> None:
    if payload.get("schema") != DECISIONS_SCHEMA:
        add(blockers, "decisions_schema_mismatch", "$.schema")
    if payload.get("surface") != SURFACE:
        add(blockers, "decisions_surface_mismatch", "$.surface")
    validate_public_header_declaration(payload, blockers, source="decisions", scanned_path=public_header_path)
    if payload.get("status") != "blocked":
        add(blockers, "decisions_status_not_blocked", "$.status")
    for key in ("public_header_allowed", "public_cache_abi_allowed", "allow_without_policy_provenance_allowed"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    if payload.get("public_header_symbols_now") != []:
        add(blockers, "public_header_symbols_now_not_empty", "$.public_header_symbols_now")
    if payload.get("public_permission_cache_contract") != "none":
        add(blockers, "public_permission_cache_contract_not_none", "$.public_permission_cache_contract")
    if payload.get("public_command_reply_contract") != "none":
        add(blockers, "public_command_reply_contract_not_none", "$.public_command_reply_contract")
    if payload.get("public_admin_mutation_contract") != "none":
        add(blockers, "public_admin_mutation_contract_not_none", "$.public_admin_mutation_contract")
    if payload.get("allow_capable_authority_ownership") != "runtime-local/runtime-owned-only":
        add(
            blockers,
            "allow_capable_authority_ownership_not_runtime_local_owned_only",
            "$.allow_capable_authority_ownership",
        )
    if payload.get("operator_config_allow_capable") is not False:
        add(blockers, "operator_config_allow_capable_not_false", "$.operator_config_allow_capable")
    if payload.get("allowed_public_surface_after_player_identity") != [
        REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY
    ]:
        add(
            blockers,
            "allowed_public_surface_after_player_identity_not_exact_query_only",
            "$.allowed_public_surface_after_player_identity",
        )
    post_identity = payload.get("post_identity_next_requirement")
    expected_post_identity = build_post_identity_next_requirement()
    if not isinstance(post_identity, dict):
        add(
            blockers,
            "post_identity_next_requirement_missing",
            "$.post_identity_next_requirement",
        )
    else:
        for key in (
            "id",
            "surface",
            "after_surface",
            "route_blocker_to_use",
            "required_public_surface",
            "required_query_fields",
            "required_policy_provenance_fields",
            "non_claim",
        ):
            if post_identity.get(key) != expected_post_identity[key]:
                add(
                    blockers,
                    "post_identity_next_requirement_mismatch",
                    f"$.post_identity_next_requirement.{key}",
                    expected=expected_post_identity[key],
                    value=post_identity.get(key),
                )
        for key in REQUIRED_POST_IDENTITY_FALSE_KEYS:
            if post_identity.get(key) is not False:
                add(
                    blockers,
                    "post_identity_next_requirement_claim_not_false",
                    f"$.post_identity_next_requirement.{key}",
                    value=post_identity.get(key),
                )
        shortcuts = post_identity.get("shortcut_artifacts_never_count")
        shortcut_set = (
            set(shortcuts)
            if isinstance(shortcuts, list) and all(isinstance(item, str) for item in shortcuts)
            else set()
        )
        if not REQUIRED_POST_IDENTITY_DECISION_SHORTCUT_ARTIFACTS.issubset(shortcut_set):
            add(
                blockers,
                "post_identity_shortcut_artifacts_never_count_missing",
                "$.post_identity_next_requirement.shortcut_artifacts_never_count",
                missing=sorted(REQUIRED_POST_IDENTITY_DECISION_SHORTCUT_ARTIFACTS - shortcut_set),
            )

    forbidden = payload.get("forbidden_public_contract")
    if not isinstance(forbidden, list) or not REQUIRED_FORBIDDEN_PUBLIC_CONTRACT.issubset(set(forbidden)):
        add(blockers, "forbidden_public_contract_missing_required", "$.forbidden_public_contract")

    required = payload.get("required_before_public_header")
    if not isinstance(required, list):
        add(blockers, "required_before_public_header_not_list", "$.required_before_public_header")
        collect_overclaims(payload, blockers, "$.decisions")
        return
    ids = {item.get("id") for item in required if isinstance(item, dict)}
    missing_ids = REQUIRED_DECISION_IDS - ids
    if missing_ids:
        add(blockers, "required_decision_ids_missing", "$.required_before_public_header", missing=sorted(missing_ids))
    by_id = {item.get("id"): item for item in required if isinstance(item, dict)}
    dependency = next(
        (
            item
            for item in required
            if isinstance(item, dict) and item.get("id") == "dependency.promoted_player_identity"
        ),
        None,
    )
    dependency_behavior = dependency.get("required_behavior") if isinstance(dependency, dict) else None
    if not isinstance(dependency_behavior, list) or not REQUIRED_DEPENDENCY_BEHAVIOR.issubset(
        set(dependency_behavior)
    ):
        add(
            blockers,
            "dependency_player_identity_public_contract_requirements_missing",
            "$.required_before_public_header[dependency.promoted_player_identity].required_behavior",
        )
    generation = by_id.get("identity.principal_generation_required")
    generation_behavior = generation.get("required_behavior") if isinstance(generation, dict) else None
    if not isinstance(generation_behavior, list) or not REQUIRED_PRINCIPAL_GENERATION_BEHAVIOR.issubset(
        set(generation_behavior)
    ):
        add(
            blockers,
            "principal_generation_fail_closed_requirements_missing",
            "$.required_before_public_header[identity.principal_generation_required].required_behavior",
        )
    scope = by_id.get("identity.principal_scope_compatibility")
    if not isinstance(scope, dict):
        add(
            blockers,
            "principal_scope_compatibility_requirements_missing",
            "$.required_before_public_header[identity.principal_scope_compatibility]",
        )
    else:
        allowed_scopes = scope.get("allowed_initial_scopes")
        if not isinstance(allowed_scopes, list) or set(allowed_scopes) != REQUIRED_PRINCIPAL_SCOPE_ALLOWED_INITIAL:
            add(
                blockers,
                "principal_scope_allowed_initial_scopes_unexpected",
                "$.required_before_public_header[identity.principal_scope_compatibility].allowed_initial_scopes",
            )
        forbidden_scopes = scope.get("forbidden_until_separate_promotion")
        if not isinstance(forbidden_scopes, list) or not REQUIRED_PRINCIPAL_SCOPE_FORBIDDEN.issubset(
            set(forbidden_scopes)
        ):
            add(
                blockers,
                "principal_scope_forbidden_wider_scopes_missing",
                "$.required_before_public_header[identity.principal_scope_compatibility].forbidden_until_separate_promotion",
            )
        scope_behavior = scope.get("required_behavior")
        if not isinstance(scope_behavior, list) or not REQUIRED_PRINCIPAL_SCOPE_BEHAVIOR.issubset(
            set(scope_behavior)
        ):
            add(
                blockers,
                "principal_scope_fail_closed_requirements_missing",
                "$.required_before_public_header[identity.principal_scope_compatibility].required_behavior",
            )
    abi = by_id.get("abi.permission_query_identity_fields")
    abi_fields = abi.get("required_fields_or_equivalent") if isinstance(abi, dict) else None
    if not isinstance(abi_fields, list) or set(abi_fields) != REQUIRED_PERMISSION_QUERY_FIELDS:
        add(
            blockers,
            "permission_query_identity_fields_unexpected",
            "$.required_before_public_header[abi.permission_query_identity_fields].required_fields_or_equivalent",
        )
    properties = abi.get("required_properties") if isinstance(abi, dict) else None
    if not isinstance(properties, list) or not REQUIRED_QUERY_TEXT_FRAGMENTS.issubset(set(properties)):
        add(blockers, "query_text_boundary_properties_missing", "$.required_before_public_header")
    cache = by_id.get("cache.generation_scope_keying")
    if not isinstance(cache, dict):
        add(
            blockers,
            "cache_generation_scope_keying_missing",
            "$.required_before_public_header[cache.generation_scope_keying]",
        )
    else:
        if cache.get("status") != "unresolved":
            add(
                blockers,
                "cache_generation_scope_keying_status_not_unresolved",
                "$.required_before_public_header[cache.generation_scope_keying].status",
            )
        if cache.get("public_cache_abi") != REQUIRED_CACHE_PUBLIC_ABI_BLOCKER:
            add(
                blockers,
                "cache_public_cache_abi_unblocked",
                "$.required_before_public_header[cache.generation_scope_keying].public_cache_abi",
                expected=REQUIRED_CACHE_PUBLIC_ABI_BLOCKER,
                value=cache.get("public_cache_abi"),
            )
        cache_key_fields = cache.get("required_cache_key_fields")
        if cache_key_fields != list(REQUIRED_CACHE_KEY_FIELD_SEQUENCE):
            add(
                blockers,
                "cache_key_fields_mismatch",
                "$.required_before_public_header[cache.generation_scope_keying].required_cache_key_fields",
                expected=list(REQUIRED_CACHE_KEY_FIELD_SEQUENCE),
                value=cache_key_fields,
            )
        cache_behavior = cache.get("required_behavior")
        if not isinstance(cache_behavior, list) or not REQUIRED_CACHE_BEHAVIOR.issubset(set(cache_behavior)):
            add(
                blockers,
                "cache_generation_scope_invalidation_requirements_missing",
                "$.required_before_public_header[cache.generation_scope_keying].required_behavior",
            )
    policy = by_id.get("policy.authority_provenance_required")
    if not isinstance(policy, dict):
        add(
            blockers,
            "policy_authority_provenance_requirements_missing",
            "$.required_before_public_header[policy.authority_provenance_required]",
        )
    else:
        policy_fields = policy.get("required_fields_or_equivalent")
        if not isinstance(policy_fields, list) or set(policy_fields) != REQUIRED_POLICY_PROVENANCE_FIELDS:
            add(
                blockers,
                "policy_authority_provenance_fields_unexpected",
                "$.required_before_public_header[policy.authority_provenance_required].required_fields_or_equivalent",
            )
        recognized = policy.get("recognized_authority_kinds")
        if not isinstance(recognized, list) or set(recognized) != REQUIRED_RECOGNIZED_AUTHORITY_KINDS:
            add(
                blockers,
                "policy_recognized_authority_kinds_unexpected",
                "$.required_before_public_header[policy.authority_provenance_required].recognized_authority_kinds",
            )
        if string_list_has_duplicates(recognized):
            add(
                blockers,
                "policy_recognized_authority_kinds_duplicate",
                "$.required_before_public_header[policy.authority_provenance_required].recognized_authority_kinds",
            )
        allow_capable = policy.get("allow_capable_authority_kinds")
        if not isinstance(allow_capable, list) or set(allow_capable) != REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS:
            add(
                blockers,
                "policy_allow_capable_authority_kinds_unexpected",
                "$.required_before_public_header[policy.authority_provenance_required].allow_capable_authority_kinds",
            )
        if string_list_has_duplicates(allow_capable):
            add(
                blockers,
                "policy_allow_capable_authority_kinds_duplicate",
                "$.required_before_public_header[policy.authority_provenance_required].allow_capable_authority_kinds",
            )
        if policy.get("allow_capable_authority_ownership") != "runtime-owned":
            add(
                blockers,
                "policy_allow_capable_authority_ownership_not_runtime_owned",
                "$.required_before_public_header[policy.authority_provenance_required].allow_capable_authority_ownership",
            )
        if policy.get("operator_config_allow_capable") is not False:
            add(
                blockers,
                "policy_operator_config_allow_capable_not_false",
                "$.required_before_public_header[policy.authority_provenance_required].operator_config_allow_capable",
            )
        if policy.get("runtime_local_authority_must_be_runtime_owned") is not True:
            add(
                blockers,
                "policy_runtime_local_authority_not_required_runtime_owned",
                "$.required_before_public_header[policy.authority_provenance_required].runtime_local_authority_must_be_runtime_owned",
            )
        authority_behavior = policy.get("required_behavior")
        if not isinstance(authority_behavior, list) or not REQUIRED_POLICY_AUTHORITY_BEHAVIOR.issubset(
            set(authority_behavior)
        ):
            add(
                blockers,
                "policy_authority_fail_closed_requirements_missing",
                "$.required_before_public_header[policy.authority_provenance_required].required_behavior",
            )
    abuse = by_id.get("abuse.query_rate_limit_and_audit_gate")
    abuse_behavior = abuse.get("required_behavior") if isinstance(abuse, dict) else None
    if not isinstance(abuse_behavior, list) or not REQUIRED_ABUSE_BEHAVIOR.issubset(set(abuse_behavior)):
        add(
            blockers,
            "abuse_rate_limit_audit_requirements_missing",
            "$.required_before_public_header[abuse.query_rate_limit_and_audit_gate].required_behavior",
        )
    separation = by_id.get("separation.no_commands_replies_or_admin_mutation")
    if not isinstance(separation, dict):
        add(
            blockers,
            "separation_no_commands_replies_or_admin_mutation_missing",
            "$.required_before_public_header[separation.no_commands_replies_or_admin_mutation]",
        )
    else:
        sequence = separation.get("v1_sequence_gate")
        if not isinstance(sequence, list) or not REQUIRED_SEPARATION_SEQUENCE_GATE.issubset(set(sequence)):
            add(
                blockers,
                "separation_sequence_gate_requirements_missing",
                "$.required_before_public_header[separation.no_commands_replies_or_admin_mutation].v1_sequence_gate",
            )
        exclusions = separation.get("required_exclusions")
        if not isinstance(exclusions, list) or not REQUIRED_SEPARATION_EXCLUSIONS.issubset(set(exclusions)):
            add(
                blockers,
                "separation_required_exclusions_missing",
                "$.required_before_public_header[separation.no_commands_replies_or_admin_mutation].required_exclusions",
            )
    fail_closed = next(
        (
            item
            for item in required
            if isinstance(item, dict) and item.get("id") == "fail_closed.stale_or_scope_mismatch"
        ),
        None,
    )
    if not isinstance(fail_closed, dict):
        collect_overclaims(payload, blockers, "$.decisions")
        return
    never_allow = fail_closed.get("must_never_return_allow_for")
    if not isinstance(never_allow, list) or not REQUIRED_FAIL_CLOSED_NEVER_ALLOW.issubset(set(never_allow)):
        add(
            blockers,
            "fail_closed_never_allow_cases_missing",
            "$.required_before_public_header[fail_closed.stale_or_scope_mismatch].must_never_return_allow_for",
        )
    deny_or_unknown = fail_closed.get("deny_or_unknown_conditions")
    if not isinstance(deny_or_unknown, list) or not REQUIRED_FAIL_CLOSED_DENY_OR_UNKNOWN.issubset(
        set(deny_or_unknown)
    ):
        add(
            blockers,
            "fail_closed_deny_or_unknown_cases_missing",
            "$.required_before_public_header[fail_closed.stale_or_scope_mismatch].deny_or_unknown_conditions",
        )
    collect_overclaims(payload, blockers, "$.decisions")


def validate_string_subset(
    value: Any,
    required: frozenset[str],
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    label: str,
) -> None:
    if not isinstance(value, list) or not required.issubset(set(value)):
        add(blockers, reason, label)


def validate_permissions_admin_manifest_contract(
    permissions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    for key in REQUIRED_PERMISSIONS_ADMIN_FALSE_KEYS:
        if permissions.get(key) is not False:
            add(blockers, f"permissions_admin_{key}_not_false", f"$.surfaces[permissions_admin].{key}")

    aliases = permissions.get("public_ready_aliases")
    if not isinstance(aliases, dict):
        add(blockers, "permissions_admin_public_ready_aliases_missing", "$.surfaces[permissions_admin].public_ready_aliases")
    else:
        alias_keys = {key for key in aliases if isinstance(key, str)}
        missing_aliases = REQUIRED_PERMISSIONS_ADMIN_READY_ALIASES - alias_keys
        if missing_aliases:
            add(
                blockers,
                "permissions_admin_public_ready_aliases_missing_required",
                "$.surfaces[permissions_admin].public_ready_aliases",
                missing=sorted(missing_aliases),
            )
        for key in REQUIRED_PERMISSIONS_ADMIN_READY_ALIASES:
            if aliases.get(key) is not False:
                add(
                    blockers,
                    "permissions_admin_public_ready_alias_not_false",
                    f"$.surfaces[permissions_admin].public_ready_aliases.{key}",
                    value=aliases.get(key),
                )

    validate_string_subset(
        permissions.get("required_evidence_terms"),
        REQUIRED_PERMISSIONS_ADMIN_EVIDENCE_TERMS,
        blockers,
        reason="permissions_admin_required_evidence_terms_missing",
        label="$.surfaces[permissions_admin].required_evidence_terms",
    )


def validate_permissions_admin_decision_contract(
    decision_contract: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    validate_string_subset(
        decision_contract.get("not_sufficient_evidence"),
        REQUIRED_PERMISSIONS_NOT_SUFFICIENT_EVIDENCE,
        blockers,
        reason="permissions_admin_not_sufficient_evidence_missing",
        label="$.surfaces[permissions_admin].v1_decision_contract.not_sufficient_evidence",
    )
    validate_string_subset(
        decision_contract.get("promotion_requires"),
        REQUIRED_PERMISSIONS_PROMOTION_REQUIRES,
        blockers,
        reason="permissions_admin_promotion_requirements_missing",
        label="$.surfaces[permissions_admin].v1_decision_contract.promotion_requires",
    )

    query_only = decision_contract.get("permissions_admin_query_only_planning")
    if not isinstance(query_only, dict):
        add(
            blockers,
            "permissions_admin_query_only_planning_missing",
            "$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning",
        )
        return
    if query_only.get("status") != "blocked/query-only-planning":
        add(
            blockers,
            "permissions_admin_query_only_planning_status_unexpected",
            "$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.status",
            value=query_only.get("status"),
        )
    for key in (
        "public_contract_allowed",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_evidence",
        "complete_sdk_counting_allowed",
    ):
        if query_only.get(key) is not False:
            add(
                blockers,
                f"permissions_admin_query_only_planning_{key}_not_false",
                f"$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.{key}",
                value=query_only.get(key),
            )
    validate_string_subset(
        query_only.get("required_policy"),
        REQUIRED_PERMISSIONS_QUERY_ONLY_POLICY,
        blockers,
        reason="permissions_admin_query_only_policy_missing",
        label="$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.required_policy",
    )
    validate_string_subset(
        query_only.get("forbidden_until_separate_promotion"),
        REQUIRED_PERMISSIONS_QUERY_ONLY_FORBIDDEN,
        blockers,
        reason="permissions_admin_query_only_forbidden_exclusions_missing",
        label="$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.forbidden_until_separate_promotion",
    )
    validate_string_subset(
        query_only.get("non_counting_artifacts"),
        REQUIRED_PERMISSIONS_NON_COUNTING_ARTIFACTS,
        blockers,
        reason="permissions_admin_non_counting_artifacts_missing",
        label="$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.non_counting_artifacts",
    )
    certificate = query_only.get("required_identity_promotion_certificate")
    if not isinstance(certificate, dict):
        add(
            blockers,
            "permissions_admin_required_identity_promotion_certificate_missing",
            "$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.required_identity_promotion_certificate",
        )
        return
    for key, expected in REQUIRED_PERMISSIONS_IDENTITY_CERTIFICATE_FIELDS.items():
        if certificate.get(key) != expected:
            add(
                blockers,
                "permissions_admin_required_identity_promotion_certificate_mismatch",
                f"$.surfaces[permissions_admin].v1_decision_contract.permissions_admin_query_only_planning.required_identity_promotion_certificate.{key}",
                expected=expected,
                value=certificate.get(key),
            )


def certificate_binding_alias_or_inline_key(key_name: str, accepted_key: str) -> bool:
    if key_name == accepted_key:
        return False
    accepted_tokens = accepted_key.split("_")
    if all(token in key_name for token in accepted_tokens):
        return True
    return (
        "promotion_certificate" in key_name
        and any(token in key_name for token in ("alias", "inline", "shortcut"))
    )


def collect_certificate_binding_aliases(
    surface: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    surface_label: str,
    certificate_key: str,
    reason: str,
) -> None:
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict):
        return
    accepted_key = normalized_key(certificate_key)
    for key, value in evidence.items():
        key_name = normalized_key(key)
        if certificate_binding_alias_or_inline_key(key_name, accepted_key):
            add(
                blockers,
                reason,
                f"$.surfaces[{surface_label}].evidence.{key}",
                accepted_binding_key=certificate_key,
                value=value,
            )


def validate_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]], public_header_path: Path) -> None:
    if payload.get("schema") != SURFACES_SCHEMA:
        add(blockers, "surfaces_schema_mismatch", "$.schema")
    validate_public_header_declaration(payload, blockers, source="surfaces", scanned_path=public_header_path)
    if SURFACE in string_set(payload.get("promoted_surfaces")):
        add(blockers, "permissions_admin_listed_as_promoted", "$.promoted_surfaces")
    if SURFACE not in string_set(payload.get("planning_surfaces")):
        add(blockers, "permissions_admin_missing_from_planning_surfaces", "$.planning_surfaces")
    if payload.get("v1_completion_required") is not False:
        add(blockers, "v1_completion_required_not_false", "$.v1_completion_required")
    for key in ("v1_required_dependency_chain", "v1_dependency_sequence"):
        if payload.get(key) != REQUIRED_P0_CHAIN:
            add(blockers, f"{key}_mismatch", f"$.{key}", expected=REQUIRED_P0_CHAIN, value=payload.get(key))
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        add(blockers, "surfaces_not_list", "$.surfaces")
        collect_overclaims(payload, blockers, "$.surfaces")
        return
    by_id = {item.get("id"): item for item in surfaces if isinstance(item, dict)}
    permissions = by_id.get(SURFACE)
    identity = by_id.get(IDENTITY_SURFACE)
    if not isinstance(permissions, dict):
        add(blockers, "permissions_admin_surface_missing", "$.surfaces")
        collect_overclaims(payload, blockers, "$.surfaces")
        return
    validate_permissions_admin_manifest_contract(permissions, blockers)
    collect_certificate_binding_aliases(
        permissions,
        blockers,
        surface_label="permissions_admin",
        certificate_key="permissions_admin_promotion_certificate",
        reason="permissions_admin_promotion_certificate_alias_or_inline_shortcut",
    )
    if not isinstance(identity, dict):
        add(blockers, "player_identity_surface_missing", "$.surfaces")
    else:
        collect_certificate_binding_aliases(
            identity,
            blockers,
            surface_label="player_identity",
            certificate_key="player_identity_promotion_certificate",
            reason="player_identity_promotion_certificate_alias_or_inline_shortcut",
        )
    if permissions.get("status") not in {"planning", "post-v1", "blocked"}:
        add(blockers, "permissions_admin_surface_status_unexpected", "$.surfaces[permissions_admin].status")
    if permissions.get("public_contract") != []:
        add(blockers, "permissions_admin_public_contract_not_empty", "$.surfaces[permissions_admin].public_contract")
    if IDENTITY_SURFACE not in permissions.get("depends_on", []):
        add(blockers, "permissions_admin_missing_player_identity_dependency", "$.surfaces[permissions_admin].depends_on")
    decision_contract = permissions.get("v1_decision_contract")
    if not isinstance(decision_contract, dict):
        add(blockers, "permissions_admin_v1_decision_contract_missing", "$.surfaces[permissions_admin].v1_decision_contract")
    else:
        if decision_contract.get("decision_manifest") != "docs/permissions_admin_public_contract_decisions.json":
            add(blockers, "permissions_admin_decision_manifest_mismatch", "$.surfaces[permissions_admin].v1_decision_contract")
        if decision_contract.get("must_remain_without_public_contract_until_promotion") is not True:
            add(blockers, "permissions_admin_public_contract_gate_missing", "$.surfaces[permissions_admin].v1_decision_contract")
        validate_permissions_admin_decision_contract(decision_contract, blockers)
    if permissions.get("status") == "promoted" and not (isinstance(identity, dict) and identity.get("status") == "promoted"):
        add(blockers, "permissions_admin_promoted_before_player_identity", "$.surfaces[permissions_admin].status")
    if isinstance(identity, dict) and identity.get("status") == "promoted":
        if not player_identity_has_approved_runtime_evidence(identity, blockers):
            add(
                blockers,
                "player_identity_evidence_not_approved",
                "$.surfaces[player_identity].status",
            )
        if not player_identity_has_promoted_public_contract(identity, blockers):
            add(
                blockers,
                "player_identity_public_contract_not_promoted",
                "$.surfaces[player_identity]",
            )
    permissions_evidence = permissions.get("evidence")
    permissions_certificate_present = (
        isinstance(permissions_evidence, dict)
        and "permissions_admin_promotion_certificate" in permissions_evidence
    )
    if (
        permissions_certificate_present
        or permissions.get("status") == "promoted"
        or SURFACE in string_set(payload.get("promoted_surfaces"))
    ):
        if not validate_permissions_admin_promotion_certificate(
            permissions,
            identity if isinstance(identity, dict) else None,
            blockers,
        ):
            add(
                blockers,
                "permissions_admin_promotion_certificate_missing_or_invalid",
                "$.surfaces[permissions_admin].evidence.permissions_admin_promotion_certificate",
            )
    collect_overclaims(payload, blockers, "$.surfaces")


def iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for child in value.values():
            strings.extend(iter_strings(child))
        return strings
    if isinstance(value, list):
        strings = []
        for child in value:
            strings.extend(iter_strings(child))
        return strings
    return []


def player_identity_has_approved_runtime_evidence(
    identity: dict[str, Any],
    blockers: list[dict[str, Any]] | None = None,
) -> bool:
    evidence = identity.get("evidence")
    accepted = evidence.get("accepted_runtime_evidence") if isinstance(evidence, dict) else None
    if not isinstance(accepted, dict):
        return False
    valid = True
    local_blockers: list[dict[str, Any]] = []
    collect_non_promotion_artifact_sources(
        accepted,
        local_blockers,
        "$.surfaces[player_identity].evidence.accepted_runtime_evidence",
        "player_identity_runtime_evidence_non_promotion_artifact_source",
    )
    if local_blockers:
        valid = False
        if blockers is not None:
            blockers.extend(local_blockers)
    if not accepted_runtime_evidence_record_is_canonical(accepted):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_accepted_runtime_evidence_not_canonical",
                "$.surfaces[player_identity].evidence.accepted_runtime_evidence",
                required_schema=PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
                required_next_blocker=IDENTITY_CONTRACT_ROUTE_BLOCKER,
                required_binding_schema=APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
            )
    if not valid:
        return False
    forbidden_terms = (
        "no approved runtime principal lifecycle evidence",
        "approved_runtime_evidence_missing",
    )
    text = "\n".join(iter_strings(identity)).lower()
    return not any(term in text for term in forbidden_terms)


def surface_by_id(payload: dict[str, Any] | None, surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("surfaces") if isinstance(payload, dict) else None
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("id") == surface_id:
            return surface
    return None


def surfaces_have_accepted_runtime_evidence(
    payload: dict[str, Any] | None,
    blockers: list[dict[str, Any]] | None = None,
) -> bool:
    identity = surface_by_id(payload, IDENTITY_SURFACE)
    return isinstance(identity, dict) and player_identity_has_approved_runtime_evidence(identity, blockers)


def surfaces_have_promoted_identity_public_contract(payload: dict[str, Any] | None) -> bool:
    identity = surface_by_id(payload, IDENTITY_SURFACE)
    return (
        isinstance(identity, dict)
        and identity.get("status") == "promoted"
        and player_identity_has_promoted_public_contract(identity)
    )


def validate_route_blocker_order(
    current_route_blocker: str,
    surfaces: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
    *,
    label: str = "$.current_route_blocker",
) -> None:
    accepted_runtime = surfaces_have_accepted_runtime_evidence(surfaces, blockers)
    identity_contract_promoted = surfaces_have_promoted_identity_public_contract(surfaces)
    if current_route_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER:
        if accepted_runtime and not identity_contract_promoted:
            return
        if identity_contract_promoted:
            add(
                blockers,
                "current_route_blocker_stale_after_identity_public_contract_review",
                label,
                value=current_route_blocker,
                expected=PUBLIC_HEADER_ROUTE_BLOCKER,
                required_evidence="matching promoted player-identity certificate/decision with reviewed identity public contract decision record",
            )
            return
        add(
            blockers,
            "current_route_blocker_out_of_order",
            label,
            value=current_route_blocker,
            required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
            required_evidence="accepted_runtime_evidence.next_blocker=identity_public_contract_gate_missing",
        )
        return
    if current_route_blocker == PUBLIC_HEADER_ROUTE_BLOCKER and not identity_contract_promoted:
        add(
            blockers,
            "current_route_blocker_before_identity_public_contract_review",
            label,
            value=current_route_blocker,
            required_predecessor=IDENTITY_CONTRACT_ROUTE_BLOCKER,
            required_evidence="matching promoted player-identity certificate/decision with reviewed identity public contract decision record",
        )
    if current_route_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER and accepted_runtime and not identity_contract_promoted:
        add(
            blockers,
            "current_route_blocker_stale_after_approved_runtime_evidence",
            label,
            value=current_route_blocker,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
            required_evidence="accepted_runtime_evidence.next_blocker=identity_public_contract_gate_missing",
        )
    if current_route_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER and identity_contract_promoted:
        add(
            blockers,
            "current_route_blocker_stale_after_identity_public_contract_review",
            label,
            value=current_route_blocker,
            expected=PUBLIC_HEADER_ROUTE_BLOCKER,
            required_evidence="matching promoted player-identity certificate/decision with reviewed identity public contract decision record",
        )


def validate_accounting_lock_route_order(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    label: str,
    surfaces: dict[str, Any] | None,
) -> None:
    lock = payload.get("accounting_lock")
    if not isinstance(lock, dict):
        return
    lock_blocker = lock.get("current_route_blocker")
    accepted_runtime = surfaces_have_accepted_runtime_evidence(surfaces, blockers)
    identity_contract_promoted = surfaces_have_promoted_identity_public_contract(surfaces)
    if lock_blocker not in ALLOWED_ROUTE_BLOCKERS:
        add(
            blockers,
            "accounting_lock_route_blocker_mismatch",
            f"{label}.accounting_lock.current_route_blocker",
            expected=list(ALLOWED_ROUTE_BLOCKERS),
            value=lock_blocker,
        )
    elif lock_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER and not accepted_runtime:
        add(
            blockers,
            "accounting_lock_route_blocker_out_of_order",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
    elif lock_blocker == IDENTITY_CONTRACT_ROUTE_BLOCKER and identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_route_blocker_stale_after_identity_public_contract_review",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            expected=PUBLIC_HEADER_ROUTE_BLOCKER,
        )
    elif lock_blocker == PUBLIC_HEADER_ROUTE_BLOCKER and not identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_route_blocker_before_identity_public_contract_review",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            required_predecessor=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    elif lock_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER and accepted_runtime and not identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_route_blocker_stale_after_approved_runtime_evidence",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    elif lock_blocker == RUNTIME_EVIDENCE_ROUTE_BLOCKER and identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_route_blocker_stale_after_identity_public_contract_review",
            f"{label}.accounting_lock.current_route_blocker",
            value=lock_blocker,
            expected=PUBLIC_HEADER_ROUTE_BLOCKER,
        )
    remaining = lock.get("remaining_route_blockers")
    if not isinstance(remaining, list):
        add(
            blockers,
            "accounting_lock_remaining_route_blockers_not_list",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
        )
    elif lock_blocker in ALLOWED_ROUTE_BLOCKERS:
        unknown_remaining = [
            item for item in remaining if item not in ALLOWED_ROUTE_BLOCKERS
        ]
        if unknown_remaining:
            add(
                blockers,
                "accounting_lock_remaining_route_blocker_unknown",
                f"{label}.accounting_lock.remaining_route_blockers",
                expected=list(ALLOWED_ROUTE_BLOCKERS),
                value=remaining,
                unknown=unknown_remaining,
            )
        if remaining != [lock_blocker]:
            if not remaining:
                reason = "accounting_lock_remaining_route_blockers_unlock_attempt"
            elif lock_blocker not in remaining:
                reason = "accounting_lock_remaining_route_blockers_missing_current_lock"
            else:
                reason = "accounting_lock_remaining_route_blockers_not_parent_lock_only"
            add(
                blockers,
                reason,
                f"{label}.accounting_lock.remaining_route_blockers",
                expected=[lock_blocker],
                value=remaining,
            )
    if isinstance(remaining, list) and IDENTITY_CONTRACT_ROUTE_BLOCKER in remaining and not accepted_runtime:
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_out_of_order",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            required_predecessor=RUNTIME_EVIDENCE_ROUTE_BLOCKER,
        )
    if isinstance(remaining, list) and IDENTITY_CONTRACT_ROUTE_BLOCKER in remaining and identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_stale_after_identity_public_contract_review",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            expected=PUBLIC_HEADER_ROUTE_BLOCKER,
        )
    if isinstance(remaining, list) and PUBLIC_HEADER_ROUTE_BLOCKER in remaining and not identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_before_identity_public_contract_review",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            required_predecessor=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    if isinstance(remaining, list) and RUNTIME_EVIDENCE_ROUTE_BLOCKER in remaining and accepted_runtime and not identity_contract_promoted:
        add(
            blockers,
            "accounting_lock_remaining_route_blocker_stale_after_approved_runtime_evidence",
            f"{label}.accounting_lock.remaining_route_blockers",
            value=remaining,
            expected=IDENTITY_CONTRACT_ROUTE_BLOCKER,
        )
    if lock.get("dependency_chain_locked") is not True:
        add(
            blockers,
            "accounting_lock_dependency_chain_not_locked",
            f"{label}.accounting_lock.dependency_chain_locked",
            value=lock.get("dependency_chain_locked"),
        )
    for key in (
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "public_or_runtime_accounting_allowed",
    ):
        if key in lock and lock.get(key) is not False:
            add(blockers, f"accounting_lock_{key}_not_false", f"{label}.accounting_lock.{key}", value=lock.get(key))


def string_set(value: Any) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def string_list_has_duplicates(value: Any) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return False
    return len(set(value)) != len(value)


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def repo_relative_path(raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path


def sha256_hex(value: Any, *, allow_zero: bool = False) -> bool:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        return False
    return allow_zero or value.lower() != ZERO_SHA256


def hash_bound_promotion_certificate_binding_keys(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        {normalized_key(key) for key in value}
        == HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS
    )


def normalized_certificate_binding(value: Any) -> dict[str, str] | None:
    if not hash_bound_promotion_certificate_binding_keys(value):
        return None
    relative = repo_relative_path(value.get("path"))
    sha256 = value.get("sha256")
    if relative is None or not sha256_hex(sha256):
        return None
    return {"path": str(relative), "sha256": sha256.lower()}


def hash_bound_certificate_bindings_match(left: Any, right: Any) -> bool:
    left_binding = normalized_certificate_binding(left)
    right_binding = normalized_certificate_binding(right)
    return (
        left_binding is not None
        and right_binding is not None
        and left_binding == right_binding
    )


def canonical_current_certificate_binding(binding: Any, *, label: str) -> dict[str, str] | None:
    normalized = normalized_certificate_binding(binding)
    if normalized is None:
        return None
    path = REPO_ROOT / normalized["path"]
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
    except SystemExit:
        return None
    actual_sha256 = sha256_file(resolved)
    if actual_sha256 != normalized["sha256"]:
        return None
    return {"path": normalized["path"], "sha256": actual_sha256}


def load_hash_bound_promotion_certificate(
    binding: Any,
    *,
    certificate_key: str,
    label: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(binding, dict):
        add(blockers, f"{certificate_key}_missing", label)
        return None
    if not hash_bound_promotion_certificate_binding_keys(binding):
        add(
            blockers,
            f"{certificate_key}_binding_keys_mismatch",
            label,
            expected=sorted(HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS),
            value=sorted(str(key) for key in binding),
        )
        return None
    relative = repo_relative_path(binding.get("path"))
    if relative is None:
        add(blockers, f"{certificate_key}_path_invalid", f"{label}.path", value=binding.get("path"))
        return None
    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, certificate_key)
        resolved_path = reject_protected_input_path(path, certificate_key)
    except SystemExit as exc:
        add(
            blockers,
            f"{certificate_key}_path_rejected",
            f"{label}.path",
            value=str(relative),
            detail=str(exc),
        )
        return None
    if resolved_path.suffix.lower() != ".json" or not resolved_path.is_file():
        add(blockers, f"{certificate_key}_artifact_missing", f"{label}.path", value=str(relative))
        return None
    expected_sha256 = binding.get("sha256")
    if not sha256_hex(expected_sha256):
        add(blockers, f"{certificate_key}_artifact_sha_invalid", f"{label}.sha256", value=expected_sha256)
        return None
    actual_sha256 = sha256_file(resolved_path)
    if actual_sha256 != expected_sha256.lower():
        add(
            blockers,
            f"{certificate_key}_artifact_hash_mismatch",
            f"{label}.sha256",
            expected=expected_sha256.lower(),
            actual=actual_sha256,
        )
        return None
    try:
        certificate = json.loads(resolved_path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{certificate_key}_artifact_unreadable", str(resolved_path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{certificate_key}_artifact_invalid_json", str(resolved_path), detail=str(exc))
        return None
    if not isinstance(certificate, dict):
        add(blockers, f"{certificate_key}_artifact_not_object", str(resolved_path))
        return None
    return certificate


def hash_bound_artifact_binding_for_path(path: Path, *, schema: str) -> dict[str, str] | None:
    try:
        relative = path.relative_to(REPO_ROOT)
    except ValueError:
        return None
    actual_sha256 = sha256_file(path)
    if actual_sha256 is None:
        return None
    return {"path": str(relative), "sha256": actual_sha256, "schema": schema}


def normalized_artifact_binding(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    if {normalized_key(key) for key in value} != HASH_BOUND_ARTIFACT_BINDING_KEYS:
        return None
    relative = repo_relative_path(value.get("path"))
    sha256 = value.get("sha256")
    schema = value.get("schema")
    if relative is None or not sha256_hex(sha256) or not isinstance(schema, str):
        return None
    return {"path": str(relative), "sha256": sha256.lower(), "schema": schema}


def hash_bound_artifact_bindings_match(left: Any, right: Any) -> bool:
    left_binding = normalized_artifact_binding(left)
    right_binding = normalized_artifact_binding(right)
    return (
        left_binding is not None
        and right_binding is not None
        and left_binding == right_binding
    )


def validate_hash_bound_artifact_binding(
    binding: Any,
    *,
    reason_prefix: str,
    label: str,
    blockers: list[dict[str, Any]],
    expected_schema: str,
) -> bool:
    if not isinstance(binding, dict):
        add(blockers, f"{reason_prefix}_binding_missing", label, value=binding)
        return False
    if {normalized_key(key) for key in binding} != HASH_BOUND_ARTIFACT_BINDING_KEYS:
        add(
            blockers,
            f"{reason_prefix}_binding_keys_mismatch",
            label,
            expected=sorted(HASH_BOUND_ARTIFACT_BINDING_KEYS),
            value=sorted(str(key) for key in binding),
        )
        return False
    if binding.get("schema") != expected_schema:
        add(
            blockers,
            f"{reason_prefix}_schema_mismatch",
            f"{label}.schema",
            expected=expected_schema,
            value=binding.get("schema"),
        )
        return False
    relative = repo_relative_path(binding.get("path"))
    if relative is None:
        add(blockers, f"{reason_prefix}_path_invalid", f"{label}.path", value=binding.get("path"))
        return False
    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, reason_prefix)
        resolved_path = reject_protected_input_path(path, reason_prefix)
    except SystemExit as exc:
        add(
            blockers,
            f"{reason_prefix}_path_rejected",
            f"{label}.path",
            value=str(relative),
            detail=str(exc),
        )
        return False
    expected_sha256 = binding.get("sha256")
    if not sha256_hex(expected_sha256):
        add(blockers, f"{reason_prefix}_sha256_invalid", f"{label}.sha256", value=expected_sha256)
        return False
    actual_sha256 = sha256_file(resolved_path)
    if actual_sha256 != expected_sha256.lower():
        add(
            blockers,
            f"{reason_prefix}_sha256_mismatch",
            f"{label}.sha256",
            expected=actual_sha256,
            value=expected_sha256.lower(),
            path=str(relative),
        )
        return False
    return True


def certificate_string_set(value: dict[str, Any], key: str) -> set[str]:
    return string_set(value.get(key))


def validate_identity_public_contract_review_evidence(
    certificate_evidence: dict[str, Any],
    blockers: list[dict[str, Any]] | None,
    label: str,
) -> bool:
    review = certificate_evidence.get("identity_public_contract_decision_record")
    if not isinstance(review, dict):
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_missing",
                f"{label}.artifact.evidence.identity_public_contract_decision_record",
            )
        return False

    valid = True
    expected_fields = {
        "schema": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
        "artifact_id": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
        "surface": IDENTITY_SURFACE,
        "active_after_resolved_input": PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
        "review_status": "reviewed",
        "accepted_for_contract_review": True,
        "next_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
    }
    for key, expected in expected_fields.items():
        if review.get(key) != expected:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_mismatch",
                    f"{label}.artifact.evidence.identity_public_contract_decision_record.{key}",
                    expected=expected,
                    value=review.get(key),
                )

    certificate_surface_hash = certificate_evidence.get("reviewed_surface_record_sha256")
    record_surface_hash = review.get("reviewed_surface_record_sha256")
    if (
        not isinstance(certificate_surface_hash, str)
        or not isinstance(record_surface_hash, str)
        or record_surface_hash.lower() != certificate_surface_hash.lower()
    ):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_surface_hash_mismatch",
                f"{label}.artifact.evidence.identity_public_contract_decision_record.reviewed_surface_record_sha256",
                expected=certificate_surface_hash,
                value=record_surface_hash,
            )

    resolved = review.get("resolved_decision_keys")
    if resolved != list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_keys_mismatch",
                f"{label}.artifact.evidence.identity_public_contract_decision_record.resolved_decision_keys",
                expected=list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS),
                value=resolved,
            )

    for key in REQUIRED_IDENTITY_CONTRACT_REVIEW_FALSE_KEYS:
        if review.get(key) is not False:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_false_flag_not_false",
                    f"{label}.artifact.evidence.identity_public_contract_decision_record.{key}",
                    value=review.get(key),
                )
    for key, expected in REQUIRED_IDENTITY_CONTRACT_REVIEW_EXACT_FIELDS.items():
        if review.get(key) != expected:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_identity_contract_review_completeness_mismatch",
                    f"{label}.artifact.evidence.identity_public_contract_decision_record.{key}",
                    expected=expected,
                    value=review.get(key),
                )
    for key in CERTIFICATE_REVIEWED_TEMPLATE_ONLY_KEYS:
        if review.get(key) is True:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_reviewed_template_only",
                    f"{label}.artifact.evidence.identity_public_contract_decision_record.{key}",
                    value=review.get(key),
                )
    record_sha256 = certificate_evidence.get("identity_public_contract_decision_record_sha256")
    actual_record_sha256 = canonical_json_sha256(review)
    if (
        not isinstance(record_sha256, str)
        or SHA256_RE.fullmatch(record_sha256) is None
        or record_sha256.lower() == ZERO_SHA256
        or record_sha256.lower() != actual_record_sha256
    ):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_identity_contract_review_record_hash_mismatch",
                f"{label}.artifact.evidence.identity_public_contract_decision_record_sha256",
                expected=actual_record_sha256,
                value=record_sha256,
            )
    return valid


def validate_player_identity_certificate_promotion_evidence(
    certificate_evidence: dict[str, Any],
    identity: dict[str, Any],
    blockers: list[dict[str, Any]] | None,
    label: str,
) -> bool:
    valid = True

    local_blockers: list[dict[str, Any]] = []
    collect_non_promotion_artifact_sources(
        certificate_evidence,
        local_blockers,
        f"{label}.artifact.evidence",
        "player_identity_promotion_certificate_non_promotion_artifact_source",
    )
    if local_blockers:
        valid = False
        if blockers is not None:
            blockers.extend(local_blockers)

    if certificate_evidence.get("promotion_evidence_kind") != REQUIRED_CERTIFICATE_PROMOTION_EVIDENCE_KIND:
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_promotion_evidence_kind_mismatch",
                f"{label}.artifact.evidence.promotion_evidence_kind",
                expected=REQUIRED_CERTIFICATE_PROMOTION_EVIDENCE_KIND,
                value=certificate_evidence.get("promotion_evidence_kind"),
            )

    for key in REQUIRED_CERTIFICATE_FALSE_KEYS:
        if certificate_evidence.get(key) is not False:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_non_promotion_flag_not_false",
                    f"{label}.artifact.evidence.{key}",
                    value=certificate_evidence.get(key),
                )

    semantic_proofs = certificate_string_set(certificate_evidence, "semantic_proofs")
    if not REQUIRED_CERTIFICATE_SEMANTIC_PROOFS.issubset(semantic_proofs):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_semantic_proofs_missing",
                f"{label}.artifact.evidence.semantic_proofs",
                missing=sorted(REQUIRED_CERTIFICATE_SEMANTIC_PROOFS - semantic_proofs),
            )

    if not validate_identity_public_contract_review_evidence(certificate_evidence, blockers, label):
        valid = False

    identity_evidence = identity.get("evidence")
    identity_runtime = (
        identity_evidence.get("accepted_runtime_evidence")
        if isinstance(identity_evidence, dict)
        else None
    )
    certificate_runtime = certificate_evidence.get("approved_runtime_evidence")
    runtime_keys = ("schema", "result", "next_blocker")
    if not (
        isinstance(identity_runtime, dict)
        and isinstance(certificate_runtime, dict)
        and all(certificate_runtime.get(key) == identity_runtime.get(key) for key in runtime_keys)
        and certificate_runtime.get("schema") == PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA
        and certificate_runtime.get("result") == "approved runtime principal lifecycle evidence"
        and certificate_runtime.get("next_blocker") == "identity_public_contract_gate_missing"
    ):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_approved_runtime_evidence_mismatch",
                f"{label}.artifact.evidence.approved_runtime_evidence",
            )

    public_contract = certificate_string_set(certificate_evidence, "public_contract")
    identity_public_contract = string_set(identity.get("public_contract"))
    if public_contract != REQUIRED_IDENTITY_PUBLIC_CONTRACT or not public_contract.issubset(identity_public_contract):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_public_contract_semantics_mismatch",
                f"{label}.artifact.evidence.public_contract",
                expected=sorted(REQUIRED_IDENTITY_PUBLIC_CONTRACT),
                value=sorted(public_contract),
            )

    capabilities = certificate_string_set(certificate_evidence, "capabilities")
    identity_capabilities = string_set(identity.get("capabilities"))
    if capabilities != REQUIRED_IDENTITY_CAPABILITIES or not capabilities.issubset(identity_capabilities):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_capability_semantics_mismatch",
                f"{label}.artifact.evidence.capabilities",
                expected=sorted(REQUIRED_IDENTITY_CAPABILITIES),
                value=sorted(capabilities),
            )

    public_fields = certificate_string_set(certificate_evidence, "public_fields")
    identity_public_fields = string_set(identity.get("public_fields"))
    if not REQUIRED_IDENTITY_PUBLIC_FIELDS.issubset(public_fields) or not public_fields.issubset(identity_public_fields):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_public_fields_semantics_mismatch",
                f"{label}.artifact.evidence.public_fields",
                missing=sorted(REQUIRED_IDENTITY_PUBLIC_FIELDS - public_fields),
                value=sorted(public_fields),
            )

    abi_contract = certificate_string_set(certificate_evidence, "abi_contract")
    identity_abi_contract = string_set(identity.get("abi_contract"))
    if not REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT.issubset(abi_contract) or not abi_contract.issubset(identity_abi_contract):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_abi_contract_semantics_mismatch",
                f"{label}.artifact.evidence.abi_contract",
                missing=sorted(REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT - abi_contract),
                value=sorted(abi_contract),
            )

    lifecycle_contract = certificate_string_set(certificate_evidence, "lifecycle_contract")
    identity_lifecycle_contract = string_set(identity.get("lifecycle_contract"))
    if not REQUIRED_IDENTITY_LIFECYCLE_CONTRACT.issubset(lifecycle_contract) or not lifecycle_contract.issubset(
        identity_lifecycle_contract
    ):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_lifecycle_contract_semantics_mismatch",
                f"{label}.artifact.evidence.lifecycle_contract",
                missing=sorted(REQUIRED_IDENTITY_LIFECYCLE_CONTRACT - lifecycle_contract),
                value=sorted(lifecycle_contract),
            )

    certificate_sdk_tests = certificate_string_set(certificate_evidence, "sdk_consumer_tests")
    identity_sdk_tests = set()
    if isinstance(identity_evidence, dict):
        identity_sdk_tests.update(string_set(identity_evidence.get("tests")))
        identity_sdk_tests.update(string_set(identity_evidence.get("sdk_consumer_tests")))
    if not certificate_sdk_tests or not certificate_sdk_tests.issubset(identity_sdk_tests):
        valid = False
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_sdk_consumer_coverage_missing",
                f"{label}.artifact.evidence.sdk_consumer_tests",
                value=sorted(certificate_sdk_tests),
            )

    return valid


def player_identity_has_promotion_certificate(
    identity: dict[str, Any],
    blockers: list[dict[str, Any]] | None = None,
) -> bool:
    label = "$.surfaces[player_identity].evidence.player_identity_promotion_certificate"
    evidence = identity.get("evidence")
    binding = evidence.get("player_identity_promotion_certificate") if isinstance(evidence, dict) else None
    if not isinstance(binding, dict):
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_missing", label)
        return False
    if not hash_bound_promotion_certificate_binding_keys(binding):
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_binding_keys_mismatch",
                label,
                expected=sorted(HASH_BOUND_PROMOTION_CERTIFICATE_BINDING_KEYS),
                value=sorted(str(key) for key in binding),
            )
        return False
    relative = repo_relative_path(binding.get("path"))
    if relative is None:
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_path_invalid", f"{label}.path", value=binding.get("path"))
        return False
    path = REPO_ROOT / relative
    try:
        reject_symlink_component(path, "player_identity_promotion_certificate")
        resolved_path = reject_protected_input_path(path, "player_identity_promotion_certificate")
    except SystemExit as exc:
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_path_rejected",
                f"{label}.path",
                value=str(relative),
                detail=str(exc),
            )
        return False
    if resolved_path.suffix.lower() != ".json" or not resolved_path.is_file():
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_artifact_missing", f"{label}.path", value=str(relative))
        return False
    expected_sha256 = binding.get("sha256")
    if not isinstance(expected_sha256, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_artifact_sha_invalid", f"{label}.sha256", value=expected_sha256)
        return False
    actual_sha256 = sha256_file(resolved_path)
    if actual_sha256 != expected_sha256.lower():
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_artifact_hash_mismatch",
                f"{label}.sha256",
                expected=expected_sha256.lower(),
                actual=actual_sha256,
            )
        return False
    try:
        certificate = json.loads(resolved_path.read_text(encoding="utf-8"))
    except OSError as exc:
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_artifact_unreadable", str(resolved_path), detail=str(exc))
        return False
    except json.JSONDecodeError as exc:
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_artifact_invalid_json", str(resolved_path), detail=str(exc))
        return False
    if not isinstance(certificate, dict):
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_artifact_not_object", str(resolved_path))
        return False
    collector_valid = True
    if blockers is not None:
        previous_blocker_count = len(blockers)
        collect_forbidden_certificate_attestations(
            certificate,
            blockers,
            "$.surfaces[player_identity].evidence.player_identity_promotion_certificate_artifact",
        )
        if len(blockers) != previous_blocker_count:
            collector_valid = False
            previous_blocker_count = len(blockers)
        collect_non_promotion_artifact_sources(
            certificate,
            blockers,
            "$.surfaces[player_identity].evidence.player_identity_promotion_certificate_artifact",
            "player_identity_promotion_certificate_non_promotion_artifact_source",
        )
        if len(blockers) != previous_blocker_count:
            collector_valid = False
            previous_blocker_count = len(blockers)
        collect_overclaims(
            certificate,
            blockers,
            "$.surfaces[player_identity].evidence.player_identity_promotion_certificate_artifact",
        )
        if len(blockers) != previous_blocker_count:
            collector_valid = False
    certificate_evidence = certificate.get("evidence")
    if not isinstance(certificate_evidence, dict):
        if blockers is not None:
            add(blockers, "player_identity_promotion_certificate_evidence_missing", f"{label}.artifact.evidence")
        return False
    reviewed_artifact_hash = certificate_evidence.get("reviewed_artifact_hash")
    if (
        not isinstance(reviewed_artifact_hash, str)
        or SHA256_RE.fullmatch(reviewed_artifact_hash) is None
        or reviewed_artifact_hash.lower() == ZERO_SHA256
    ):
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_reviewed_artifact_hash_invalid",
                f"{label}.artifact.evidence.reviewed_artifact_hash",
                value=reviewed_artifact_hash,
            )
        return False
    reviewed_surface_hash = certificate_evidence.get("reviewed_surface_record_sha256")
    current_surface_hash = player_identity_surface_record_sha256(identity)
    if (
        not isinstance(reviewed_surface_hash, str)
        or reviewed_surface_hash.lower() != current_surface_hash
    ):
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_stale_or_mismatched_upstream_surface",
                f"{label}.artifact.evidence.reviewed_surface_record_sha256",
                expected=current_surface_hash,
                value=reviewed_surface_hash,
            )
            add(
                blockers,
                "player_identity_promotion_certificate_reviewed_surface_record_hash_mismatch",
                f"{label}.artifact.evidence.reviewed_surface_record_sha256",
                expected=current_surface_hash,
                value=reviewed_surface_hash,
            )
        return False
    if reviewed_artifact_hash.lower() != reviewed_surface_hash.lower():
        if blockers is not None:
            add(
                blockers,
                "player_identity_promotion_certificate_hash_unbound",
                f"{label}.artifact.evidence.reviewed_artifact_hash",
                expected=reviewed_surface_hash.lower(),
                value=reviewed_artifact_hash.lower(),
            )
            add(
                blockers,
                "player_identity_promotion_certificate_reviewed_artifact_hash_unbound",
                f"{label}.artifact.evidence.reviewed_artifact_hash",
                expected=reviewed_surface_hash.lower(),
                value=reviewed_artifact_hash.lower(),
            )
        return False
    promotion_evidence_valid = validate_player_identity_certificate_promotion_evidence(
        certificate_evidence,
        identity,
        blockers,
        label,
    )
    valid = collector_valid and promotion_evidence_valid
    expected_fields = {
        "schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "surface_id": IDENTITY_SURFACE,
        "promotion_status": "promoted",
        "v1_dependency_chain": REQUIRED_P0_CHAIN,
        "v1_dependency_chain_position": 1,
        "required_by_surface": SURFACE,
        "required_by_v1_dependency_chain_position": 2,
    }
    reason_by_key = {
        "schema": "player_identity_promotion_certificate_schema_mismatch",
        "surface_id": "player_identity_promotion_certificate_surface_mismatch",
        "promotion_status": "player_identity_promotion_certificate_status_mismatch",
        "v1_dependency_chain": "player_identity_promotion_certificate_dependency_chain_mismatch",
        "v1_dependency_chain_position": "player_identity_promotion_certificate_chain_position_mismatch",
        "required_by_surface": "player_identity_promotion_certificate_required_by_surface_mismatch",
        "required_by_v1_dependency_chain_position": "player_identity_promotion_certificate_required_by_chain_position_mismatch",
    }
    for key, expected in expected_fields.items():
        if certificate.get(key) != expected:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    reason_by_key[key],
                    f"{label}.artifact.{key}",
                    expected=expected,
                    value=certificate.get(key),
                )
    alias_reason_by_key = {
        "chain_position": "player_identity_promotion_certificate_chain_position_alias_mismatch",
        "required_by_chain_position": (
            "player_identity_promotion_certificate_required_by_chain_position_alias_mismatch"
        ),
    }
    for key, expected in REQUIRED_PLAYER_IDENTITY_CERTIFICATE_POSITION_ALIASES.items():
        if certificate.get(key) != expected:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    alias_reason_by_key[key],
                    f"{label}.artifact.{key}",
                    expected=expected,
                    value=certificate.get(key),
                )
    for key, expected in REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY.items():
        if certificate.get(key) != expected:
            valid = False
            if blockers is not None:
                add(
                    blockers,
                    "player_identity_promotion_certificate_binding_policy_mismatch",
                    f"{label}.artifact.{key}",
                    expected=expected,
                    value=certificate.get(key),
                )
    return valid


def player_identity_surface_record_sha256(identity: dict[str, Any]) -> str:
    """Hash the identity surface record without the self-referential certificate binding."""

    sanitized = dict(identity)
    evidence = sanitized.get("evidence")
    if isinstance(evidence, dict):
        sanitized["evidence"] = {
            key: value
            for key, value in evidence.items()
            if key != "player_identity_promotion_certificate"
        }
    data = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def permissions_admin_surface_record_sha256(permissions: dict[str, Any]) -> str:
    """Hash the permissions/admin surface without a self-referential certificate binding."""

    sanitized = dict(permissions)
    evidence = sanitized.get("evidence")
    if isinstance(evidence, dict):
        sanitized["evidence"] = {
            key: value
            for key, value in evidence.items()
            if key != "permissions_admin_promotion_certificate"
        }
    data = json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def current_player_identity_promotion_certificate_binding(
    identity: dict[str, Any] | None,
) -> dict[str, str] | None:
    evidence = identity.get("evidence") if isinstance(identity, dict) else None
    binding = (
        evidence.get("player_identity_promotion_certificate")
        if isinstance(evidence, dict)
        else None
    )
    return canonical_current_certificate_binding(
        binding,
        label="player_identity_promotion_certificate",
    )


def current_query_failclosed_contract_binding() -> dict[str, str] | None:
    return hash_bound_artifact_binding_for_path(
        DEFAULT_QUERY_FAILCLOSED_CONTRACT,
        schema=QUERY_CONTRACT_SCHEMA,
    )


def certificate_payload_marks_permissions_admin_builder_report(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("schema") == PERMISSIONS_ADMIN_PROMOTION_CERTIFICATE_BUILD_REPORT_SCHEMA:
        return True
    normalized_keys = {normalized_key(key) for key in value}
    return bool(
        {
            "certificate_artifact_schema",
            "certificate_path",
            "certificate_sha256",
            "certificate_written",
        }
        & normalized_keys
    )


def validate_permissions_certificate_current_input_bindings(
    certificate_evidence: dict[str, Any],
    *,
    input_bindings: Any,
    permissions: dict[str, Any],
    identity: dict[str, Any] | None,
    label: str,
    blockers: list[dict[str, Any]],
) -> bool:
    valid = True
    expected_surface_hash = permissions_admin_surface_record_sha256(permissions)
    expected_identity_hash = (
        player_identity_surface_record_sha256(identity)
        if isinstance(identity, dict)
        else None
    )
    current_identity_binding = current_player_identity_promotion_certificate_binding(identity)
    current_query_binding = current_query_failclosed_contract_binding()

    if not isinstance(input_bindings, dict):
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_bindings_missing",
            f"{label}.input_bindings",
            value=input_bindings,
        )
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            f"{label}.input_bindings.player_identity_promotion_certificate",
            expected=current_identity_binding,
            value=None,
        )
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_query_failclosed_contract_missing_or_mismatch",
            f"{label}.input_bindings.permissions_admin_query_failclosed_contract",
            expected=current_query_binding,
            value=None,
        )
        return False

    if set(input_bindings) != REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_bindings_keys_mismatch",
            f"{label}.input_bindings",
            expected=sorted(REQUIRED_PERMISSIONS_CERTIFICATE_INPUT_BINDINGS),
            value=sorted(str(key) for key in input_bindings),
        )

    for key, schema in PERMISSIONS_CERTIFICATE_INPUT_ARTIFACT_SCHEMAS.items():
        if not validate_hash_bound_artifact_binding(
            input_bindings.get(key),
            reason_prefix=f"permissions_admin_promotion_certificate_{key}",
            label=f"{label}.input_bindings.{key}",
            blockers=blockers,
            expected_schema=schema,
        ):
            valid = False

    declared_query_binding = input_bindings.get("permissions_admin_query_failclosed_contract")
    if not hash_bound_artifact_bindings_match(declared_query_binding, current_query_binding):
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_query_failclosed_contract_missing_or_mismatch",
            f"{label}.input_bindings.permissions_admin_query_failclosed_contract",
            expected=current_query_binding,
            value=declared_query_binding,
        )

    declared_identity_binding = input_bindings.get("player_identity_promotion_certificate")
    if not hash_bound_certificate_bindings_match(declared_identity_binding, current_identity_binding):
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_current_player_identity_certificate_binding_missing_or_mismatch",
            f"{label}.input_bindings.player_identity_promotion_certificate",
            expected=current_identity_binding,
            value=declared_identity_binding,
        )

    if input_bindings.get("permissions_admin_surface_record_sha256") != expected_surface_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_permissions_surface_record_sha256_mismatch",
            f"{label}.input_bindings.permissions_admin_surface_record_sha256",
            expected=expected_surface_hash,
            value=input_bindings.get("permissions_admin_surface_record_sha256"),
        )
    if input_bindings.get("player_identity_surface_record_sha256") != expected_identity_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_player_identity_surface_record_sha256_mismatch",
            f"{label}.input_bindings.player_identity_surface_record_sha256",
            expected=expected_identity_hash,
            value=input_bindings.get("player_identity_surface_record_sha256"),
        )
    for key in PERMISSIONS_CERTIFICATE_REPORT_HASH_INPUTS:
        if not sha256_hex(input_bindings.get(key)):
            valid = False
            add(
                blockers,
                f"permissions_admin_promotion_certificate_{key}_invalid",
                f"{label}.input_bindings.{key}",
                value=input_bindings.get(key),
            )

    expected_input_binding_sha256 = canonical_json_sha256(input_bindings)
    if certificate_evidence.get("input_binding_sha256") != expected_input_binding_sha256:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_input_binding_sha256_mismatch",
            f"{label}.evidence.input_binding_sha256",
            expected=expected_input_binding_sha256,
            value=certificate_evidence.get("input_binding_sha256"),
        )
    return valid


def validate_permissions_admin_promotion_certificate(
    permissions: dict[str, Any],
    identity: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> bool:
    certificate_key = "permissions_admin_promotion_certificate"
    label = f"$.surfaces[permissions_admin].evidence.{certificate_key}"
    evidence = permissions.get("evidence")
    binding = evidence.get(certificate_key) if isinstance(evidence, dict) else None
    certificate = load_hash_bound_promotion_certificate(
        binding,
        certificate_key=certificate_key,
        label=label,
        blockers=blockers,
    )
    if not isinstance(certificate, dict):
        return False

    valid = True
    if certificate_payload_marks_permissions_admin_builder_report(certificate):
        valid = False
        add(blockers, "permissions_admin_promotion_certificate_build_report_not_certificate", label)

    previous_blocker_count = len(blockers)
    collect_overclaims(
        certificate,
        blockers,
        "$.surfaces[permissions_admin].evidence.permissions_admin_promotion_certificate_artifact",
    )
    if len(blockers) != previous_blocker_count:
        valid = False

    for key, expected in REQUIRED_PERMISSIONS_CERTIFICATE_FIELDS.items():
        if certificate.get(key) != expected:
            valid = False
            add(
                blockers,
                f"permissions_admin_promotion_certificate_{key}_mismatch",
                f"{label}.artifact.{key}",
                expected=expected,
                value=certificate.get(key),
            )
    for key, expected in REQUIRED_PERMISSIONS_CERTIFICATE_POSITION_ALIASES.items():
        if certificate.get(key) != expected:
            valid = False
            add(
                blockers,
                f"permissions_admin_promotion_certificate_{key}_mismatch",
                f"{label}.artifact.{key}",
                expected=expected,
                value=certificate.get(key),
            )

    certificate_evidence = certificate.get("evidence")
    if not isinstance(certificate_evidence, dict):
        add(blockers, "permissions_admin_promotion_certificate_evidence_missing", f"{label}.artifact.evidence")
        return False

    expected_surface_hash = permissions_admin_surface_record_sha256(permissions)
    if certificate_evidence.get("reviewed_surface_record_sha256") != expected_surface_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_surface_record_sha256_mismatch",
            f"{label}.artifact.evidence.reviewed_surface_record_sha256",
            expected=expected_surface_hash,
            value=certificate_evidence.get("reviewed_surface_record_sha256"),
        )
    if certificate_evidence.get("reviewed_artifact_hash") != expected_surface_hash:
        valid = False
        add(
            blockers,
            "permissions_admin_promotion_certificate_reviewed_artifact_hash_mismatch",
            f"{label}.artifact.evidence.reviewed_artifact_hash",
            expected=expected_surface_hash,
            value=certificate_evidence.get("reviewed_artifact_hash"),
        )

    if not validate_permissions_certificate_current_input_bindings(
        certificate_evidence,
        input_bindings=certificate.get("input_bindings"),
        permissions=permissions,
        identity=identity,
        label=f"{label}.artifact",
        blockers=blockers,
    ):
        valid = False
    return valid


def player_identity_has_promoted_public_contract(
    identity: dict[str, Any],
    blockers: list[dict[str, Any]] | None = None,
) -> bool:
    """Require identity's public contract, not just its consume-mode runtime evidence."""

    if not player_identity_has_approved_runtime_evidence(identity):
        return False

    public_contract = string_set(identity.get("public_contract"))
    capabilities = string_set(identity.get("capabilities"))
    abi_contract = string_set(identity.get("abi_contract"))
    lifecycle_contract = string_set(identity.get("lifecycle_contract"))
    public_fields = string_set(identity.get("public_fields"))
    evidence = identity.get("evidence")
    evidence_tests = string_set(evidence.get("tests")) if isinstance(evidence, dict) else set()
    evidence_sdk_consumer_tests = (
        string_set(evidence.get("sdk_consumer_tests")) if isinstance(evidence, dict) else set()
    )
    decision_contract = identity.get("v1_decision_contract")

    if not REQUIRED_IDENTITY_PUBLIC_CONTRACT.issubset(public_contract):
        return False
    if not REQUIRED_IDENTITY_CAPABILITIES.issubset(capabilities):
        return False
    if not REQUIRED_IDENTITY_PUBLIC_ABI_CONTRACT.issubset(abi_contract):
        return False
    if not REQUIRED_IDENTITY_LIFECYCLE_CONTRACT.issubset(lifecycle_contract):
        return False
    if not REQUIRED_IDENTITY_PUBLIC_FIELDS.issubset(public_fields):
        return False
    if not evidence_tests and not evidence_sdk_consumer_tests:
        return False
    if not player_identity_has_promotion_certificate(identity, blockers):
        return False
    if not isinstance(decision_contract, dict):
        return False
    if decision_contract.get("current_decision") not in IDENTITY_PROMOTED_DECISION_VALUES:
        return False
    if decision_contract.get("must_remain_without_public_contract_until_promotion") is True:
        return False
    return True


def validate_header(path: Path, blockers: list[dict[str, Any]]) -> None:
    try:
        reject_symlink_component(path, "public_header")
        resolved = reject_protected_input_path(path, "public_header")
        text = strip_c_comments(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", "$.public_header", path=str(path), detail=str(exc))
        return
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), detail=str(exc))
        return
    present = sorted(
        token
        for token in REQUIRED_HEADER_ABSENT_EXACT_TOKENS
        if c_identifier_exact_re(token).search(text)
    )
    present.extend(
        sorted(
            prefix
            for prefix in REQUIRED_HEADER_ABSENT_PREFIXES
            if c_identifier_prefix_re(prefix).search(text)
        )
    )
    if present:
        add(blockers, "public_header_contains_permissions_admin_symbol", str(path), tokens=present)


def validate_query_artifact(path: Path | None, blockers: list[dict[str, Any]]) -> str | None:
    if path is None:
        return None
    payload = load_json(path, "query_failclosed_artifact", blockers)
    if payload is None:
        return None
    schema = payload.get("schema")
    if schema == QUERY_CONTRACT_REPORT_SCHEMA:
        add(blockers, "query_failclosed_report_not_accepted_as_artifact", str(path))
        return None
    if schema != QUERY_CONTRACT_SCHEMA:
        add(blockers, "query_failclosed_artifact_schema_mismatch", str(path), schema=schema)
        return None
    collect_overclaims(payload, blockers, "$.query_failclosed_artifact")
    for key in QUERY_READY_FALSE_KEYS:
        if payload.get(key) is not False:
            add(blockers, f"query_failclosed_artifact_{key}_not_false", f"{path}:{key}")
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "query_failclosed_manifest_not_candidate_only", f"{path}:artifact_status")
    validation = query_failclosed_contract.validate_manifest(payload, check_mode="consume")
    if validation.blockers:
        add(
            blockers,
            "query_failclosed_manifest_contract_invalid",
            str(path),
            reasons=[blocker["reason"] for blocker in validation.blockers],
        )
    return str(schema)


def validate_beta_capture_flags(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    label: str,
    reason_prefix: str,
) -> None:
    for key in BETA_CAPTURE_FALSE_KEYS:
        if payload.get(key) is not False:
            add(blockers, f"{reason_prefix}_{key}_not_false", f"{label}:{key}")
    for key in BETA_CAPTURE_ZERO_KEYS:
        if payload.get(key) != 0:
            add(blockers, f"{reason_prefix}_{key}_not_zero", f"{label}:{key}")


def validate_beta_capture_artifact(
    path: Path | None,
    blockers: list[dict[str, Any]],
) -> tuple[str | None, list[str]]:
    if path is None:
        return None, []
    payload = load_json(path, "beta_capture_artifact", blockers)
    if payload is None:
        return None, []
    schema = payload.get("schema")
    if schema != BETA_CAPTURE_CANDIDATES_SCHEMA:
        add(blockers, "beta_capture_artifact_schema_mismatch", str(path), schema=schema)
        return None, []

    collect_overclaims(payload, blockers, "$.beta_capture_artifact")
    validate_beta_capture_flags(
        payload,
        blockers,
        str(path),
        "beta_capture_artifact",
    )
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "beta_capture_artifact_status_not_candidate_only", f"{path}:artifact_status")
    if payload.get("candidate_only") is not True:
        add(blockers, "beta_capture_artifact_candidate_only_not_true", f"{path}:candidate_only")
    if payload.get("debug_only") is not True:
        add(blockers, "beta_capture_artifact_debug_only_not_true", f"{path}:debug_only")
    if payload.get("requires_own_checker_acceptance") is not True:
        add(
            blockers,
            "beta_capture_artifact_requires_own_checker_acceptance_not_true",
            f"{path}:requires_own_checker_acceptance",
        )
    if payload.get("requires_player_principal_triplet") is not True:
        add(
            blockers,
            "beta_capture_artifact_requires_player_principal_triplet_not_true",
            f"{path}:requires_player_principal_triplet",
        )
    if payload.get("non_claim") != BETA_CAPTURE_NON_CLAIM:
        add(blockers, "beta_capture_artifact_non_claim_mismatch", f"{path}:non_claim")

    candidates = payload.get("candidate_debug_surfaces")
    if not isinstance(candidates, list) or not candidates:
        add(blockers, "beta_capture_candidate_debug_surfaces_missing", f"{path}:candidate_debug_surfaces")
        return str(schema), []

    observed: list[str] = []
    seen: set[str] = set()
    required = set(BETA_CAPTURE_REQUIRED_SURFACES)
    for index, candidate in enumerate(candidates):
        candidate_label = f"{path}:candidate_debug_surfaces[{index}]"
        if not isinstance(candidate, dict):
            add(blockers, "beta_capture_candidate_not_object", candidate_label)
            continue
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str):
            add(blockers, "beta_capture_candidate_surface_id_missing", f"{candidate_label}:id")
            continue
        observed.append(candidate_id)
        if candidate_id in seen:
            add(blockers, "beta_capture_candidate_surface_duplicate", f"{candidate_label}:id", value=candidate_id)
        seen.add(candidate_id)
        if candidate_id not in required:
            add(blockers, "beta_capture_candidate_surface_unknown", f"{candidate_label}:id", value=candidate_id)
            continue

        expected_target = BETA_CAPTURE_SURFACE_TARGETS[candidate_id]
        if candidate.get("target") != expected_target:
            add(
                blockers,
                "beta_capture_candidate_target_mismatch",
                f"{candidate_label}:target",
                expected=expected_target,
                value=candidate.get("target"),
            )
        validate_beta_capture_flags(
            candidate,
            blockers,
            candidate_label,
            "beta_capture_candidate",
        )
        if candidate.get("artifact_status") != "candidate_only":
            add(blockers, "beta_capture_candidate_status_not_candidate_only", f"{candidate_label}:artifact_status")
        if candidate.get("candidate_only") is not True:
            add(blockers, "beta_capture_candidate_candidate_only_not_true", f"{candidate_label}:candidate_only")
        if candidate.get("debug_only") is not True:
            add(blockers, "beta_capture_candidate_debug_only_not_true", f"{candidate_label}:debug_only")
        if candidate.get("requires_own_checker_acceptance") is not True:
            add(
                blockers,
                "beta_capture_candidate_requires_own_checker_acceptance_not_true",
                f"{candidate_label}:requires_own_checker_acceptance",
            )
        if candidate.get("requires_player_principal_triplet") is not True:
            add(
                blockers,
                "beta_capture_candidate_requires_player_principal_triplet_not_true",
                f"{candidate_label}:requires_player_principal_triplet",
            )

    missing = sorted(required - seen)
    if missing:
        add(blockers, "beta_capture_required_surfaces_missing", f"{path}:candidate_debug_surfaces", missing=missing)
    return str(schema), sorted(observed)


def route_blocker_for_identity_stage(surfaces: dict[str, Any] | None) -> str:
    if surfaces_have_promoted_identity_public_contract(surfaces):
        return PUBLIC_HEADER_ROUTE_BLOCKER
    if surfaces_have_accepted_runtime_evidence(surfaces):
        return IDENTITY_CONTRACT_ROUTE_BLOCKER
    return RUNTIME_EVIDENCE_ROUTE_BLOCKER


def build_post_identity_next_requirement() -> dict[str, Any]:
    requirement: dict[str, Any] = {
        "id": REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_ID,
        "surface": SURFACE,
        "after_surface": IDENTITY_SURFACE,
        "route_blocker_to_use": PUBLIC_HEADER_ROUTE_BLOCKER,
        "required_public_surface": REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY,
        "required_query_fields": sorted(REQUIRED_PERMISSION_QUERY_FIELDS),
        "required_policy_provenance_fields": sorted(REQUIRED_POLICY_PROVENANCE_FIELDS),
        "required_identity_public_contract_review": identity_public_contract_review_input(),
        "required_identity_promotion_certificate": identity_promotion_certificate_input(),
        "shortcut_artifacts_never_count": sorted(REQUIRED_POST_IDENTITY_SHORTCUT_ARTIFACTS),
        "non_evidence_artifacts": sorted(REQUIRED_POST_IDENTITY_SHORTCUT_ARTIFACTS),
        "non_claim": REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_NON_CLAIM,
    }
    requirement.update({key: False for key in REQUIRED_POST_IDENTITY_FALSE_KEYS})
    return requirement


def build_post_identity_query_only_diagnostics(surfaces: dict[str, Any] | None) -> dict[str, Any]:
    identity_promoted = surfaces_have_promoted_identity_public_contract(surfaces)
    route_blocker_to_use = route_blocker_for_identity_stage(surfaces)
    diagnostics: dict[str, Any] = {
        "schema": POST_IDENTITY_QUERY_ONLY_DIAGNOSTICS_SCHEMA,
        "surface": SURFACE,
        "after_surface": IDENTITY_SURFACE,
        "diagnostic_only": True,
        "non_evidence": True,
        "non_authorizing": True,
        "stage": (
            "post_identity_public_header_gate"
            if identity_promoted
            else "blocked_until_hash_bound_player_identity_promotion"
        ),
        "identity_public_contract_promoted": identity_promoted,
        "route_blocker_to_use": route_blocker_to_use,
        "post_identity_route_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
        "required_public_surface_after_identity": REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY,
        "required_query_fields": sorted(REQUIRED_PERMISSION_QUERY_FIELDS),
        "required_policy_provenance_fields": sorted(REQUIRED_POLICY_PROVENANCE_FIELDS),
        "query_only_alias_artifacts_rejected": sorted(QUERY_ONLY_ALIAS_ARTIFACTS),
        "query_only_ready_aliases_rejected": sorted(QUERY_ONLY_READY_ALIAS_CLAIMS),
        "accepted_artifact_status": "candidate_only",
        "accepted_artifact_schema": QUERY_CONTRACT_SCHEMA,
        "next_gate": {
            "id": REQUIRED_POST_IDENTITY_NEXT_REQUIREMENT_ID,
            "route_blocker_to_use": PUBLIC_HEADER_ROUTE_BLOCKER,
            "requires_public_header_review": True,
            "requires_promoted_identity_first": not identity_promoted,
        },
        "non_claim": (
            "post-identity query-only diagnostics are not evidence and are not authorizing; "
            "they do not grant public header, ABI, SDK, runtime, stable, publication, "
            "permissions/admin promotion, route readiness, or P0 progress"
        ),
    }
    diagnostics.update({key: False for key in QUERY_ONLY_DIAGNOSTIC_FALSE_KEYS})
    diagnostics.update({key: 0 for key in QUERY_ONLY_DIAGNOSTIC_ZERO_KEYS})
    return diagnostics


def identity_runtime_evidence_input() -> dict[str, Any]:
    return {
        "id": "accepted_runtime_principal_lifecycle_evidence",
        "surface": IDENTITY_SURFACE,
        "required_schema": PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
        "required_result": "approved runtime principal lifecycle evidence",
        "required_next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
        "attach_to": "surfaces[obelisk.player_identity.v1].evidence.accepted_runtime_evidence",
        "counts_toward_permissions_admin": False,
        "permissions_admin_unlock_allowed": False,
    }


def identity_public_contract_review_input() -> dict[str, Any]:
    return {
        "id": "reviewed_identity_public_contract_decision_record",
        "surface": IDENTITY_SURFACE,
        "input_route_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
        "required_schema": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
        "required_artifact_id": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
        "required_active_after_resolved_input": PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
        "required_review_status": "reviewed",
        "required_next_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
        "required_decision_keys": list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS),
        "must_be_hash_bound_inside_promotion_certificate": True,
        "counts_toward_permissions_admin": False,
        "permissions_admin_unlock_allowed": False,
    }


def identity_promotion_certificate_input() -> dict[str, Any]:
    return {
        "id": "hash_bound_player_identity_promotion_certificate",
        "surface": IDENTITY_SURFACE,
        "required_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
        "required_by_surface": SURFACE,
        "required_chain": REQUIRED_P0_CHAIN,
        "required_chain_position": 1,
        "required_by_chain_position": 2,
        **REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
        "required_semantic_proofs": sorted(REQUIRED_CERTIFICATE_SEMANTIC_PROOFS),
        "counts_toward_permissions_admin": False,
        "permissions_admin_unlock_allowed": False,
    }


def build_identity_input_diagnostics(surfaces: dict[str, Any] | None) -> dict[str, Any]:
    runtime_observed = surfaces_have_accepted_runtime_evidence(surfaces)
    certificate_observed = surfaces_have_promoted_identity_public_contract(surfaces)
    if not runtime_observed:
        missing_inputs = [identity_runtime_evidence_input()]
    elif not certificate_observed:
        missing_inputs = [
            identity_public_contract_review_input(),
            identity_promotion_certificate_input(),
        ]
    else:
        missing_inputs = []

    return {
        "surface": IDENTITY_SURFACE,
        "dependency_for_surface": SURFACE,
        "route_blocker_to_use": route_blocker_for_identity_stage(surfaces),
        "accepted_runtime_evidence_observed": runtime_observed,
        "identity_public_contract_certificate_observed": certificate_observed,
        "missing_identity_inputs": missing_inputs,
        "accepted_runtime_evidence_input": identity_runtime_evidence_input(),
        "identity_public_contract_review_input": identity_public_contract_review_input(),
        "identity_promotion_certificate_input": identity_promotion_certificate_input(),
        "counts_toward_permissions_admin": False,
        "permissions_admin_unlock_allowed": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
    }


def build_machine_next_steps(surfaces: dict[str, Any] | None) -> dict[str, Any]:
    identity_diagnostics = build_identity_input_diagnostics(surfaces)
    identity_runtime_observed = identity_diagnostics["accepted_runtime_evidence_observed"]
    identity_certificate_observed = identity_diagnostics["identity_public_contract_certificate_observed"]
    route_blocker_to_use = route_blocker_for_identity_stage(surfaces)
    post_identity_next_requirement = build_post_identity_next_requirement()
    post_identity_query_only_diagnostics = build_post_identity_query_only_diagnostics(surfaces)

    if not identity_runtime_observed:
        steps = [
            {
                "order": 1,
                "id": "produce_approved_runtime_principal_lifecycle_evidence",
                "surface": IDENTITY_SURFACE,
                "required_schema": PLAYER_IDENTITY_APPROVED_RUNTIME_EVIDENCE_SCHEMA,
                "required_result": "approved runtime principal lifecycle evidence",
                "required_next_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
                "attach_to": "surfaces[obelisk.player_identity.v1].evidence.accepted_runtime_evidence",
                "counts_toward_permissions_admin": False,
            }
        ]
    elif not identity_certificate_observed:
        steps = [
            {
                "order": 1,
                "id": "review_identity_public_contract_decision_record",
                "surface": IDENTITY_SURFACE,
                "input_route_blocker": IDENTITY_CONTRACT_ROUTE_BLOCKER,
                "required_schema": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_SCHEMA,
                "required_artifact_id": PLAYER_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD_ID,
                "required_active_after_resolved_input": PLAYER_IDENTITY_PUBLIC_CONTRACT_REVIEW_INPUT,
                "required_review_status": "reviewed",
                "required_next_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
                "required_decision_keys": list(REQUIRED_IDENTITY_PUBLIC_CONTRACT_REVIEW_DECISION_KEYS),
                "counts_toward_permissions_admin": False,
                "permissions_admin_unlock_allowed": False,
            },
            {
                "order": 2,
                "id": "issue_hash_bound_player_identity_promotion_certificate",
                "surface": IDENTITY_SURFACE,
                "required_schema": PLAYER_IDENTITY_PROMOTION_CERTIFICATE_SCHEMA,
                "required_by_surface": SURFACE,
                "required_chain": REQUIRED_P0_CHAIN,
                "required_chain_position": 1,
                "required_by_chain_position": 2,
                **REQUIRED_PLAYER_IDENTITY_CERTIFICATE_BINDING_POLICY,
                "required_semantic_proofs": sorted(REQUIRED_CERTIFICATE_SEMANTIC_PROOFS),
                "counts_toward_permissions_admin": False,
                "permissions_admin_unlock_allowed": False,
            },
            {
                "order": 3,
                "id": "rerun_permissions_admin_public_readiness_with_public_header_route_blocker",
                "command": [
                    "python3",
                    "scripts/check_permissions_admin_public_readiness.py",
                    "--json",
                    "--current-route-blocker",
                    PUBLIC_HEADER_ROUTE_BLOCKER,
                ],
                "expected_current_route_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
                "counts_toward_permissions_admin": False,
                "permissions_admin_unlock_allowed": False,
            },
        ]
    else:
        steps = [
            {
                "order": 1,
                "id": "resolve_permissions_admin_query_public_header_gate",
                "surface": SURFACE,
                "input_route_blocker": PUBLIC_HEADER_ROUTE_BLOCKER,
                "required_public_surface": REQUIRED_ALLOWED_PUBLIC_SURFACE_AFTER_IDENTITY,
                "required_query_fields": sorted(REQUIRED_PERMISSION_QUERY_FIELDS),
                "required_policy_provenance_fields": sorted(REQUIRED_POLICY_PROVENANCE_FIELDS),
                "forbidden_shortcuts": post_identity_next_requirement["shortcut_artifacts_never_count"],
                "counts_toward_permissions_admin": False,
                "permissions_admin_unlock_allowed": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "stable_claim_allowed": False,
            }
        ]

    return {
        "schema": NEXT_STEPS_SCHEMA,
        "route_blocker_to_use": route_blocker_to_use,
        "identity_runtime_artifact_observed": identity_runtime_observed,
        "identity_contract_certificate_observed": identity_certificate_observed,
        "missing_identity_inputs": identity_diagnostics["missing_identity_inputs"],
        "identity_input_diagnostics": identity_diagnostics,
        "blocked_behind_surfaces": BLOCKED_BEHIND_SURFACES,
        "non_claim": (
            "machine next steps are planning metadata only; they do not promote "
            "permissions/admin, authorize runtime work, or count toward public SDK/P0"
        ),
        "post_identity_next_requirement": post_identity_next_requirement,
        "post_identity_query_only_diagnostics": post_identity_query_only_diagnostics,
        "shortcut_aliases_rejected": post_identity_next_requirement["shortcut_artifacts_never_count"],
        "steps": steps,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    current_route_blocker = getattr(args, "current_route_blocker", CURRENT_ROUTE_BLOCKER)
    if current_route_blocker not in ALLOWED_ROUTE_BLOCKERS:
        add(
            blockers,
            "current_route_blocker_mismatch",
            "$.current_route_blocker",
            expected=list(ALLOWED_ROUTE_BLOCKERS),
            value=current_route_blocker,
        )
    decisions = load_json(args.decisions, "decisions", blockers)
    surfaces = load_json(args.surfaces, "surfaces", blockers)
    if decisions is not None:
        validate_decisions(decisions, blockers, args.public_header)
        validate_accounting_lock_route_order(decisions, blockers, label="$.decisions", surfaces=surfaces)
    if surfaces is not None:
        validate_surfaces(surfaces, blockers, args.public_header)
    validate_route_blocker_order(current_route_blocker, surfaces, blockers)
    validate_header(args.public_header, blockers)
    query_artifact_schema = validate_query_artifact(
        getattr(args, "query_failclosed_artifact", None),
        blockers,
    )
    beta_capture_artifact_schema, beta_capture_candidate_surfaces = validate_beta_capture_artifact(
        getattr(args, "beta_capture_artifact", None),
        blockers,
    )
    next_steps = build_machine_next_steps(surfaces)
    post_identity_next_requirement = build_post_identity_next_requirement()
    post_identity_query_only_diagnostics = next_steps["post_identity_query_only_diagnostics"]
    identity_input_diagnostics = next_steps["identity_input_diagnostics"]
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "valid": not blockers,
        "accepted_for_planning": not blockers and query_artifact_schema is not None,
        "planning_only": True,
        "dependency_chain": REQUIRED_P0_CHAIN,
        "dependency_chain_locked": True,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": [current_route_blocker],
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_permissions_admin": False,
        "permissions_admin_unlock_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "sdk_progress": 0,
        "p0_progress": 0,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "public_or_runtime_accounting_allowed": False,
        "route_ready": False,
        "public_route_ready": False,
        "permissions_admin_route_ready": False,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_ready": False,
        "stable_release_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "dependency": IDENTITY_SURFACE,
        "beta_capture_artifact_schema": beta_capture_artifact_schema,
        "beta_capture_candidate_surfaces": beta_capture_candidate_surfaces,
        "beta_capture_candidate_prep_visible": beta_capture_artifact_schema is not None,
        "beta_capture_candidate_prep_only": beta_capture_artifact_schema is not None,
        "beta_capture_candidate_only": beta_capture_artifact_schema is not None,
        "beta_capture_debug_only": beta_capture_artifact_schema is not None,
        "beta_capture_requires_own_checker_acceptance": beta_capture_artifact_schema is not None,
        "beta_capture_requires_player_principal_triplet": beta_capture_artifact_schema is not None,
        "beta_capture_clears_approved_runtime_evidence_missing": False,
        "beta_capture_counts_as_approved_runtime_evidence": False,
        "beta_capture_counts_as_runtime_evidence": False,
        "beta_capture_counts_as_sdk_progress": False,
        "beta_capture_counts_as_p0_progress": False,
        "beta_capture_replaces_player_principal_evidence": False,
        "beta_capture_counts_toward_public_sdk": False,
        "beta_capture_counts_toward_runtime": False,
        "beta_capture_counts_toward_v1_completion": False,
        "beta_capture_non_claim": BETA_CAPTURE_NON_CLAIM if beta_capture_artifact_schema is not None else None,
        "non_claim": (
            "valid planning output does not count permissions/admin while player identity remains blocked "
            f"on {current_route_blocker}"
        ),
        "identity_input_diagnostics": identity_input_diagnostics,
        "missing_identity_inputs": identity_input_diagnostics["missing_identity_inputs"],
        "post_identity_next_requirement": post_identity_next_requirement,
        "post_identity_query_only_diagnostics": post_identity_query_only_diagnostics,
        "next_steps": next_steps,
        "query_failclosed_artifact_schema": query_artifact_schema,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["blockers"]:
        for blocker in report["blocker_details"]:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
