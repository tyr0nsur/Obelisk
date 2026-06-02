#!/usr/bin/env python3
"""Validate permissions/admin public readiness remains blocked/planning-only."""

from __future__ import annotations

import argparse
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
DEFAULT_PUBLIC_HEADER_DECL = "include/obelisk/ObeliskApi.h"

REPORT_SCHEMA = "obelisk.permissions-admin-public-readiness-check.v1"
DECISIONS_SCHEMA = "obelisk.permissions-admin-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
QUERY_CONTRACT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract.v1"
QUERY_CONTRACT_REPORT_SCHEMA = "obelisk.permissions-admin-query-failclosed-contract-check.v1"
SURFACE = "obelisk.permissions_admin.v1"
IDENTITY_SURFACE = "obelisk.player_identity.v1"
COMMAND_RESPONSE_SURFACE = "obelisk.command_chat_response_path.v1"
COMMANDS_REPLIES_SURFACE = "obelisk.commands_replies.v1"
REQUIRED_P0_CHAIN = [IDENTITY_SURFACE, SURFACE, COMMAND_RESPONSE_SURFACE, COMMANDS_REPLIES_SURFACE]

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
REQUIRED_DEPENDENCY_BEHAVIOR = frozenset(
    (
        "before player identity is promoted, permissions/admin exposes no public ABI, callbacks, cache ABI, command/reply implication, or header symbols",
        "player identity planning evidence alone cannot enable permissions/admin",
        "runtime principal evidence alone is not public identity promotion",
        "approved runtime principal lifecycle evidence alone cannot enable permissions/admin",
        "promoted player identity must include approved runtime principal lifecycle evidence, not only promoted status text",
        "promoted player identity must include a public identity/principal contract with capability, ABI, lifecycle cleanup, and SDK consumer coverage",
        "promoted player identity must define copied principal semantics for principal_handle, principal_generation, principal_scope_flags, invalidation, and owner-token lifecycle before permissions/admin can count as promoted",
        "promoted player identity must include owner-token cleanup on init failure, plugin unload, and owner-scoped unregister before permissions/admin can count as promoted",
        "permissions/admin cannot infer copied principal semantics from surface status text, runtime evidence text, command text, operator config, or plugin input",
        "runtime observation must establish principal identity before permissions/admin can consume it",
        "operator config enables surfaces or policy inputs only and cannot establish principal identity",
        "command text cannot establish principal identity",
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
        "action",
        "action_size",
        "resource_scope",
        "resource_scope_size",
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
        "OBELISK_API_CAPABILITY_AUTHORIZATION",
        "OBELISK_API_CAPABILITY_PERMISSION_CHECKS",
        "OBELISK_API_CAPABILITY_PERMISSIONS_ADMIN",
        "OBELISK_PERMISSION_CACHE_ABI_VERSION",
        "OBELISK_PERMISSION_QUERY_ABI_VERSION",
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
QUERY_READY_FALSE_KEYS = (
    "promotion_ready",
    "public_header_allowed",
    "public_cache_abi_allowed",
    "public_sdk_ready",
    "runtime_ready",
)
FALSE_ONLY_KEYS = frozenset(
    (
        "command_router_allowed",
        "permission_cache_abi_allowed",
        "public_abi_allowed",
        "public_abi_ready",
        "public_admin_mutation_allowed",
        "public_bridge_abi_allowed",
        "public_cache_abi_allowed",
        "public_command_reply_allowed",
        "public_command_router_allowed",
        "public_header_allowed",
        "public_header_ready",
        "public_permission_cache_allowed",
        "public_reply_abi_ready",
        "public_response_abi_allowed",
        "public_response_path_ready",
        "public_reply_or_send_chat_abi_allowed",
        "public_response_path_allowed",
        "public_sdk_ready",
        "replies_send_chat_allowed",
        "reply_send_chat_router_claims_allowed",
        "runtime_delivery_allowed",
        "runtime_ready",
        "send_chat_allowed",
        "send_chat_ready",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = frozenset(
    (
        "authority_claim_source",
        "principal_source",
    )
)
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = frozenset(("command_text", "operator_config"))
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
    "release_guardrails",
    "v1_sequence_gate",
)
NEGATED_CLAIM_RE = re.compile(
    r"\b(blocked|cannot|deny|does\s+not|fail[s-]?closed|forbidden|future|must|must\s+not|never|no|not|"
    r"only|planning|post-v1|require[sd]?|unresolved|until|without)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(r"[.;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported|unresolved|.*\b(?:before|only|never|until|requires?)\b)",
    re.IGNORECASE,
)
POSITIVE_CLAIM_RE = re.compile(
    r"\b("
    r"admin\s+mutation|command\s*/\s*chat\s+response|command[_ -]?rout(?:e|er|ing)|"
    r"command\s+response\s+path|"
    r"permission[_ -]?cache|public\s+(?:abi|headers?|sdk)|"
    r"permissions?/admin|reply\s+endpoint|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request|endpoint))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?|"
    r"runtime(?:[_ -]?delivery)?"
    r")\b.{0,100}\b(allowed|available|delivered|enabled|established|live|promoted|public|ready|supported)\b",
    re.IGNORECASE,
)
POSITIVE_CLAIM_REVERSED_RE = re.compile(
    r"\b(allowed|available|delivered|enabled|established|live|promoted|public|ready|supported)\b"
    r".{0,100}\b("
    r"admin\s+mutation|command\s*/\s*chat\s+response|command[_ -]?rout(?:e|er|ing)|"
    r"command\s+response\s+path|"
    r"permission[_ -]?cache|public\s+(?:abi|headers?|sdk)|"
    r"permissions?/admin|reply\s+endpoint|"
    r"repl(?:y|ies)(?:[_ -]?(?:abi|api|path|request|endpoint))?|send[_ -]?chat(?:[_ -]?(?:abi|api|path|request))?|"
    r"runtime(?:[_ -]?delivery)?"
    r")\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--surfaces", type=Path, default=DEFAULT_SURFACES)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        help="Optional candidate-only permissions/admin query manifest or checker report.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def normalized_key(key: Any) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_source(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")


def contains_forbidden_pre_runtime_claim_source(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_source(value) in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES
    if isinstance(value, list):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value)
    if isinstance(value, dict):
        return any(contains_forbidden_pre_runtime_claim_source(item) for item in value.values())
    return False


def is_negative_context(trail: str) -> bool:
    lowered = trail.casefold()
    return any(token in lowered for token in NEGATIVE_CONTEXT_TOKENS)


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//.*", "", text)


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def claim_match_is_negated(text: str, match: re.Match[str]) -> bool:
    if NEGATED_CLAIM_RE.search(match.group(0)):
        return True
    if NEGATED_CLAIM_RE.search(preceding_claim_scope(text, match.start())):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def has_unnegated_positive_claim(text: str) -> bool:
    for clause in CLAIM_SCOPE_SPLIT_RE.split(text):
        for regex in (POSITIVE_CLAIM_RE, POSITIVE_CLAIM_REVERSED_RE):
            for match in regex.finditer(clause):
                if not claim_match_is_negated(clause, match):
                    return True
    return False


def c_identifier_exact_re(token: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(token)}(?![A-Za-z0-9_])")


def c_identifier_prefix_re(prefix: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9_]){re.escape(prefix)}[A-Za-z0-9_]*")


def collect_overclaims(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_name = normalized_key(key)
            if key_name in FALSE_ONLY_KEYS and child is not False:
                add(blockers, "public_surface_overclaim", child_trail, field=str(key), value=child)
            if (
                key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS
                and contains_forbidden_pre_runtime_claim_source(child)
            ):
                add(blockers, "pre_runtime_principal_or_authority_claim_source", child_trail, field=str(key), value=child)
            collect_overclaims(child, blockers, child_trail)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            collect_overclaims(child, blockers, f"{trail}[{index}]")
        return
    if (
        not isinstance(value, str)
        or is_negative_context(trail)
        or trail.endswith(".schema")
        or trail.endswith(".surface")
        or trail.endswith(".id")
    ):
        return
    if has_unnegated_positive_claim(value):
        add(blockers, "positive_public_surface_claim", trail, value=value)


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
        allow_capable = policy.get("allow_capable_authority_kinds")
        if not isinstance(allow_capable, list) or set(allow_capable) != REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS:
            add(
                blockers,
                "policy_allow_capable_authority_kinds_unexpected",
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
    if not isinstance(identity, dict):
        add(blockers, "player_identity_surface_missing", "$.surfaces")
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
    if permissions.get("status") == "promoted" and not (isinstance(identity, dict) and identity.get("status") == "promoted"):
        add(blockers, "permissions_admin_promoted_before_player_identity", "$.surfaces[permissions_admin].status")
    if isinstance(identity, dict) and identity.get("status") == "promoted":
        if not player_identity_has_approved_runtime_evidence(identity):
            add(
                blockers,
                "player_identity_evidence_not_approved",
                "$.surfaces[player_identity].status",
            )
        if not player_identity_has_promoted_public_contract(identity):
            add(
                blockers,
                "player_identity_public_contract_not_promoted",
                "$.surfaces[player_identity]",
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


def player_identity_has_approved_runtime_evidence(identity: dict[str, Any]) -> bool:
    evidence = identity.get("evidence")
    accepted = evidence.get("accepted_runtime_evidence") if isinstance(evidence, dict) else None
    if not isinstance(accepted, dict):
        return False
    if accepted.get("schema") != "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1":
        return False
    if accepted.get("result") != "approved runtime principal lifecycle evidence":
        return False
    if accepted.get("next_blocker") != "identity_public_contract_gate_missing":
        return False
    forbidden_terms = (
        "no approved runtime principal lifecycle evidence",
        "approved_runtime_evidence_missing",
    )
    text = "\n".join(iter_strings(identity)).lower()
    return not any(term in text for term in forbidden_terms)


def string_set(value: Any) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def player_identity_has_promoted_public_contract(identity: dict[str, Any]) -> bool:
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
    payload = load_json(path)
    schema = payload.get("schema")
    if schema not in {QUERY_CONTRACT_SCHEMA, QUERY_CONTRACT_REPORT_SCHEMA}:
        add(blockers, "query_failclosed_artifact_schema_mismatch", str(path), schema=schema)
        return None
    for key in QUERY_READY_FALSE_KEYS:
        if payload.get(key) is not False:
            add(blockers, f"query_failclosed_artifact_{key}_not_false", f"{path}:{key}")
    if schema == QUERY_CONTRACT_REPORT_SCHEMA:
        if payload.get("mode") != "consume":
            add(blockers, "query_failclosed_report_mode_not_consume", f"{path}:mode")
        if payload.get("ready") is not True:
            add(blockers, "query_failclosed_report_not_ready_for_consume", f"{path}:ready")
        expected_report_fields = {
            "input_schema": QUERY_CONTRACT_SCHEMA,
            "query_fields": list(query_failclosed_contract.REQUIRED_QUERY_FIELD_SEQUENCE),
            "decision_fields": sorted(query_failclosed_contract.REQUIRED_DECISION_FIELDS),
            "decisions": list(query_failclosed_contract.REQUIRED_DECISION_SEQUENCE),
            "provenance_fields": sorted(query_failclosed_contract.REQUIRED_PROVENANCE_FIELDS),
            "recognized_authority_kinds": sorted(query_failclosed_contract.REQUIRED_RECOGNIZED_AUTHORITY_KINDS),
            "allow_capable_authority_kinds": sorted(query_failclosed_contract.REQUIRED_ALLOW_CAPABLE_AUTHORITY_KINDS),
            "fail_closed_cases": list(query_failclosed_contract.REQUIRED_FAIL_CLOSED_CASE_SEQUENCE),
        }
        for key, expected in expected_report_fields.items():
            if payload.get(key) != expected:
                add(
                    blockers,
                    f"query_failclosed_report_{key}_mismatch",
                    f"{path}:{key}",
                    expected=expected,
                    value=payload.get(key),
                )
    else:
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


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(args.decisions)
    surfaces = load_json(args.surfaces)
    validate_decisions(decisions, blockers, args.public_header)
    validate_surfaces(surfaces, blockers, args.public_header)
    validate_header(args.public_header, blockers)
    query_artifact_schema = validate_query_artifact(args.query_failclosed_artifact, blockers)
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "valid": not blockers,
        "accepted_for_planning": not blockers and query_artifact_schema is not None,
        "planning_only": True,
        "promotion_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "dependency": IDENTITY_SURFACE,
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
