#!/usr/bin/env python3
"""Validate candidate-only player identity public ABI preflight routing."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_private_pod_layout_candidate as private_layout
import check_player_identity_identifier_redaction_evidence as identifier_redaction
import check_player_identity_principal_invalidation_policy as principal_invalidation
from native_prototype_guardrails import without_native_prototype_symbols


SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-abi-preflight-candidate-check.v1"
SURFACE = "obelisk.player_identity.v1"
PREFLIGHT_SCOPE = "candidate_only_public_abi_preflight_not_public"
DEFAULT_MANIFEST = Path("docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json")
DEFAULT_PRIVATE_LAYOUT = Path("docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json")
DEFAULT_IDENTIFIER_REDACTION = Path("docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json")
DEFAULT_PRINCIPAL_INVALIDATION = Path(
    "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json"
)
DEFAULT_PUBLIC_HEADER = Path("include/obelisk/ObeliskApi.h")
REQUIRED_ACCEPTED_INPUTS = {
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation.candidate_policy",
    "abi.public_pod_contract.private_layout_candidate",
}
REQUIRED_BEFORE_PUBLIC_ABI = {
    "runtime.lifecycle_evidence",
    "lifetime.principal_scope",
    "lifetime.invalidation_events",
    "lifetime.reconnect_duplicate_stale_policy",
    "abi.public_pod_contract",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
REQUIRED_DOES_NOT_RESOLVE = {
    "runtime.lifecycle_evidence",
    "abi.public_pod_contract",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "v1_completion",
}
REQUIRED_CAPABILITY_POLICY = {
    "named player identity capability bit remains absent while blocked",
    "capability must be captured in the init-time API table before any future use",
    "missing capability fails closed",
    "later marker or env changes cannot widen a loaded plugin's captured capability",
}
REQUIRED_OWNER_TOKEN_LIFECYCLE = {
    "nonzero plugin_owner_token required",
    "opaque uint64 registration handle returned on success",
    "registration handles are process-local and non-persistent",
    "owner-token unregister required",
    "plugin init failure removes registrations",
    "plugin unload removes registrations and drains in-flight callbacks",
    "callback payload storage is valid only for the callback",
}
REQUIRED_SDK_CONSUMER_CONTRACT = {
    "consumer checks struct_size before reading identity payload or descriptor fields",
    "consumer checks the captured capability bit before registering identity callbacks",
    "consumer requires nonzero plugin_owner_token before owner-token registration",
    "consumer treats callback payload storage as callback-local",
    "consumer treats principal handles as process-local and non-persistent",
    "consumer treats registration handles as process-local and non-persistent",
    "consumer uses owner-token unregister for every successful registration handle",
    "consumer does not use identity for lookup, permissions/admin, commands/replies, persistence, mutation, return override, or send-chat identity",
}
REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE = {
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "public_abi_ready",
    "v1_completion",
}
REQUIRED_NON_CLAIMS = {
    "candidate-only public ABI preflight for offline routing",
    "does not add public header symbols",
    "does not reserve final C symbol names",
    "does not add capability bits",
    "does not add callback ABI",
    "does not promote obelisk.player_identity.v1",
    "does not resolve runtime.lifecycle_evidence",
    "does not resolve abi.public_pod_contract, abi.layout, sdk.consumer, lifecycle.owner_cleanup, or v1_completion",
    "does not promote permissions/admin, command response, commands/replies, lookup, persistence, mutation, return override, or send-chat identity",
}
POSITIVE_CLAIM_VALUES = {
    "accepted",
    "allowed",
    "approved",
    "available",
    "claim_allowed",
    "complete",
    "completed",
    "counted",
    "counts",
    "enabled",
    "green",
    "open",
    "opened",
    "passed",
    "persistent",
    "present",
    "promoted",
    "public",
    "published",
    "ready",
    "release_grade",
    "release_ready",
    "resolved",
    "satisfied",
    "satisfies",
    "stable",
    "stable_ready",
    "stable_sdk",
    "stable_sdk_ready",
    "supported",
    "true",
    "unlocked",
    "yes",
}
PUBLIC_READINESS_FALSE_KEYS = {
    "accepted_for_contract_review",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_lifecycle_evidence_accepted",
    "approved_runtime_evidence_next_blocker",
    "approved_runtime_evidence_routes_to",
    "call_process_event_post_init_ready",
    "call_process_event_shortcut_ready",
    "capability_bits_approved",
    "counts_toward_complete_sdk_claim",
    "counts_toward_sdk_p0_progress",
    "descriptor_ready",
    "event_payload_ready",
    "promotion",
    "promotion_ready",
    "helper_derived_readiness",
    "helper_derived_ready",
    "helper_readiness",
    "helper_ready",
    "identity_persistence_ready",
    "identity_lookup_ready",
    "identity_storage_ready",
    "identity_contract_gate_accepted",
    "identity_contract_gate_acceptance",
    "identity_contract_gate_approval",
    "identity_contract_gate_approved",
    "identity_public_contract_gate_accepted",
    "identity_public_contract_gate_acceptance",
    "identity_public_contract_gate_approval",
    "identity_public_contract_gate_approved",
    "ownership_ready",
    "owner_token_contract_accepted",
    "owner_token_contract_approved",
    "owner_token_lifecycle_accepted",
    "owner_token_planning_accepted",
    "owner_token_identity_ready",
    "owner_token_sdk_consumer_accepted",
    "payload_shape_promoted",
    "payload_shape_public",
    "payload_shape_ready",
    "p0_progress",
    "p0_progress_ready",
    "permissions_admin_ready",
    "permissions_ready",
    "post_init_call_process_event_shortcut",
    "post_init_call_process_event_shortcut_ready",
    "public_abi_contract_decisions_accepted",
    "public_abi_ready",
    "public_api_allowed",
    "public_api_readiness",
    "public_api_ready",
    "public_abi_preflight_accepted",
    "public_abi_preflight_candidate_accepted",
    "public_contract_gate_accepted",
    "public_contract_gate_acceptance",
    "public_contract_gate_approval",
    "public_contract_gate_approved",
    "public_contract_allowed",
    "public_contract_decisions",
    "public_contract_decisions_accepted",
    "public_header_gate_accepted",
    "public_header_gate_acceptance",
    "public_header_gate_approval",
    "public_header_gate_approved",
    "public_header_gate_proposal_accepted",
    "public_header_allowed",
    "public_header_proposal_accepted",
    "public_header_ready",
    "public_identity_ready",
    "public_sdk_ready",
    "public_sdk_v1_completion_claim",
    "public_sdk_v1_completion_ready",
    "runtime_lifecycle_evidence_accepted",
    "runtime_lifecycle_evidence_next_blocker",
    "runtime_lifecycle_evidence_routes_to",
    "production_stable_sdk_claim_allowed",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_progress",
    "sdk_progress_ready",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "support_tier_activation_allowed",
    "support_tier_ready",
    "plugin_hub_publication_allowed",
    "plugin_hub_publication_ready",
    "plugin_hub_readiness_claim_allowed",
    "plugin_hub_ready",
    "ready",
    "route_accepted_as_public_abi",
    "runtime_ready",
    "runtime_ready_alias",
    "runtime_principal_ready",
    "source_ready",
    "v1_completion_claim",
    "v1_completion_evidence",
    "v1_completion_ready",
    "v1_ready",
}
PUBLIC_EMPTY_LIST_KEYS = {
    "callback_abi",
    "callback_names",
    "callback_registrations",
    "callback_symbol_names",
    "callback_symbols",
    "callbacks",
    "capabilities",
    "capability_bits",
    "capability_bit_names",
    "capability_names",
    "header_names",
    "header_paths",
    "header_symbols",
    "headers",
    "broadcast_names",
    "broadcast_symbols",
    "identity_callback_symbols",
    "identity_capability_bit_names",
    "identity_capability_bits",
    "identity_capability_names",
    "identity_capability_symbols",
    "identity_header_symbols",
    "identity_headers",
    "identity_persistence_names",
    "identity_persistence_symbols",
    "identity_storage_names",
    "identity_storage_symbols",
    "lookup_names",
    "lookup_symbols",
    "lookup_storage_names",
    "lookup_storage_symbols",
    "persistence_names",
    "persistence_symbols",
    "persistent_identity_names",
    "persistent_identity_symbols",
    "principal_callback_symbols",
    "principal_capability_bit_names",
    "principal_capability_bits",
    "principal_capability_names",
    "principal_capability_symbols",
    "principal_header_symbols",
    "principal_headers",
    "principal_persistence_names",
    "principal_persistence_symbols",
    "principal_lookup_names",
    "principal_lookup_symbols",
    "principal_storage_names",
    "principal_storage_symbols",
    "rcon_command_names",
    "rcon_command_symbols",
    "rcon_names",
    "rcon_symbols",
    "public_callback_abi",
    "public_callback_abi_now",
    "public_callbacks",
    "public_api_symbols",
    "public_api_symbols_now",
    "public_api_symbol_list",
    "public_capability_bits",
    "public_capability_names",
    "public_capability_bits_now",
    "public_header_names",
    "public_header_paths",
    "public_header_symbols",
    "public_header_symbols_now",
    "public_headers",
    "public_symbol_list",
    "public_symbol_names",
    "public_symbols",
    "resource_handle_names",
    "resource_handle_symbols",
    "resource_mutable_names",
    "resource_mutable_symbols",
    "resource_mutation_names",
    "resource_mutation_symbols",
    "resource_writable_names",
    "resource_writable_symbols",
    "writable_resource_names",
    "writable_resource_symbols",
    "resource_write_names",
    "resource_write_symbols",
    "command_names",
    "command_symbols",
    "commands_names",
    "commands_symbols",
    "command_reply_names",
    "command_reply_symbols",
    "commands_reply_names",
    "commands_reply_symbols",
    "commands_replies_names",
    "commands_replies_symbols",
    "chat_reply_names",
    "chat_reply_symbols",
    "send_chat_names",
    "send_chat_symbols",
    "mutation_names",
    "mutation_symbols",
    "mutable_resource_names",
    "mutable_resource_symbols",
    "return_override_names",
    "return_override_symbols",
    "ownership_names",
    "ownership_symbols",
    "owner_lookup_names",
    "owner_lookup_symbols",
    "access_control_symbols",
    "acl_symbols",
    "auth_symbols",
    "authz_symbols",
    "ban_kick_symbols",
    "moderation_symbols",
    "privilege_symbols",
    "role_symbols",
    "permission_names",
    "permission_symbols",
    "permissions_names",
    "permissions_symbols",
    "object_handle_symbols",
    "resource_id_symbols",
    "resource_reference_symbols",
    "resource_owner_names",
    "resource_owner_symbols",
    "storage_names",
    "storage_symbols",
    "tribe_names",
    "tribe_symbols",
}
FORBIDDEN_LIFECYCLE_CLAIM_KEYS = {
    "bare_unregister_by_id",
    "bare_unregister_by_id_available",
    "bare_unregister_by_id_ready",
    "cross_process_registration",
    "cross_process_registrations",
    "cross_process_registry",
    "ownerless_unregister",
    "ownerless_unregister_allowed",
    "ownerless_unregister_ready",
    "persistent_registration",
    "persistent_registration_handle",
    "persistent_registration_handles",
    "persistent_registry",
    "registration_handle_persistent",
    "registration_handle_survive_restart",
    "registration_handle_survives_restart",
    "registration_handle_valid_after_unload",
    "registration_handles_persistent",
    "registration_handles_restart_stable",
    "registration_handles_survive_restart",
    "registration_handles_survives_restart",
    "registration_handles_valid_after_unload",
    "registrations_persistent",
    "unregister_by_id_available",
    "unregister_by_id_ready",
}
PUBLIC_HEADER_TOKEN_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net|"
    r"player_?(?:handle|data|id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player|"
    r"(?:identity|principal|player|resource|object)_?(?:storage|store|persistence|persistent|registry|database|cache)|"
    r"(?:commands?|command_?reply|commands_?replies|chat_?reply|send_?chat|broadcast|rcon)(?:_?(?:api|abi|surface|event|callback|handler|router|path|symbol|function|support))?|"
    r"resource_?(?:handle|id|ref|reference|token|mutation|mutable|write|update)|"
    r"(?:mutat(?:e|ion)|mutable|writable|writeable|write_?resource|resource_?write|update_?resource|resource_?update)|"
    r"return_?overrides?|object_?(?:handle|id|identity|lookup|resolve|resolver)|"
    r"permissions?|permission_?(?:check|query|cache)|authorization|(?:^|_)authz?(?:_|$)|"
    r"access_?control|acl|roles?|privileges?|moderation|moderator|ban|kick|admin(?:_?(?:command|action))?|"
    r"(?:resource|player|principal|tribe)_?(?:owner|ownership|permission|permissions)|"
    r"owner_?(?:lookup|resolve|resolver|id)|tribe_?(?:id|lookup|resolve|resolver)|"
    r"[A-Za-z0-9_]*(?:OwnerLookup|OwnerResolve|Ownership|Permission|Permissions|Authorization|Authz|"
    r"AccessControl|ACL|Role|Privilege|Moderation|Moderator|Ban|Kick|Admin)[A-Za-z0-9_]*|"
    r"[A-Za-z0-9_]*(?:lookup|resolve)[A-Za-z0-9_]*",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
HEADER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
}
FORBIDDEN_PUBLIC_PAYLOAD_FIELD_RE = re.compile(
    r"(?:storage|store|persistent|persistence|registry|database|cache|lookup|resolve|resolver|"
    r"mutat(?:e|ion)|mutable|writable|writeable|write|update|permission|permissions|authz?|"
    r"access_?control|acl|role|privilege|moderation|ban|kick|admin|command|reply|send_?chat|"
    r"resource_?handle|object_?handle|steam_?id|steamid|eos|unique_?net|tribe|network_?address)",
    re.IGNORECASE,
)
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"excludes?|without|until|missing|blocked|blocker|unavailable|required[_ -]?before|"
    r"must[_ -]?not|no_)\b",
    re.IGNORECASE,
)
PUBLIC_TEXT_OVERCLAIM_PATTERNS = {
    "public_header_ready": re.compile(
        r"\bpublic[-_ ]+header(?:[-_ ]+symbols?)?\s+(?:is\s+|are\s+)?"
        r"(?:allowed|available|ready|exposed|promoted|enabled|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_capability_available": re.compile(
        r"\b(?:public[-_ ]+)?(?:identity[-_ ]+)?capability(?:[-_ ]+bits?)?\s+(?:is\s+|are\s+)?"
        r"(?:available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_callback_abi": re.compile(
        r"\b(?:public[-_ ]+)?callback[-_ ]+abi\s+(?:is\s+)?"
        r"(?:available|ready|exposed|promoted|enabled|supported)",
        re.IGNORECASE,
    ),
    "public_sdk_ready": re.compile(
        r"\bpublic[-_ ]+sdk\s+(?:is\s+)?(?:ready|available|promoted|enabled|complete|supported)",
        re.IGNORECASE,
    ),
    "public_api_ready": re.compile(
        r"\bpublic[-_ ]+api\s+(?:is\s+)?"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "runtime_ready": re.compile(
        r"\bruntime\s+(?:is\s+)?(?:ready|enabled|authorized|available|promoted|supported)",
        re.IGNORECASE,
    ),
    "promotion_ready": re.compile(
        r"\bpromotion\s+(?:is\s+)?(?:ready|authorized|complete|available)",
        re.IGNORECASE,
    ),
    "v1_completion_ready": re.compile(
        r"\bv1(?:[-_ ]+sdk)?[-_ ]+completion\s+(?:is\s+)?(?:ready|complete|available|promoted)",
        re.IGNORECASE,
    ),
    "stable_sdk_ready": re.compile(
        r"\b(?:production[-_ ]+)?stable[-_ ]+(?:sdk|claim|wording)\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|promoted|supported)",
        re.IGNORECASE,
    ),
    "support_tier_ready": re.compile(
        r"\bsupport[-_ ]+tier(?:[-_ ]+activation)?\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|activated|promoted|supported)",
        re.IGNORECASE,
    ),
    "plugin_hub_ready": re.compile(
        r"\b(?:plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:readiness|publication|package|support))?"
        r"\s+(?:is\s+)?(?:allowed|available|ready|enabled|published|promoted|released|supported)",
        re.IGNORECASE,
    ),
    "public_contract_ready": re.compile(
        r"\bpublic[-_ ]+contract\s+(?:is\s+)?(?:allowed|ready|available|promoted|enabled|complete)",
        re.IGNORECASE,
    ),
    "payload_shape_public_contract": re.compile(
        r"\b(?:event[-_ ]+payload|payload[-_ ]+shape|descriptor[-_ ]+shape|"
        r"owner[-_ ]+token[-_ ]+(?:contract|design)|capability[-_ ]+bits?)\b[^\.;]{0,120}\b"
        r"(?:promotes?|proves?|validates?|unlock(?:s|ed)?|opens?|allows?|enables?|"
        r"satisf(?:ies|y)|resolves?|counts?|ready|accepted|approved|public|available|supported)\b"
        r"(?:[^\.;]{0,120}\b(?:public[-_ ]+abi|public[-_ ]+sdk|callback[-_ ]+abi|"
        r"obelisk\.player_identity\.v1|promotion|readiness|capability[-_ ]+bits?))?",
        re.IGNORECASE,
    ),
    "player_identity_promoted": re.compile(r"\b(?:promotes?|promoted)\s+obelisk\.player_identity\.v1\b", re.IGNORECASE),
    "public_capability_symbol": re.compile(
        r"\bOBELISK_API_CAPABILITY_[A-Z0-9_]*"
        r"(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET|AUTH|AUTHZ|ACCESS_CONTROL|ACL|"
        r"ROLE|PRIVILEGE|MODERATION|BAN|KICK|RESOURCE|OBJECT)[A-Z0-9_]*\b"
    ),
    "public_player_header_symbol": re.compile(
        r"\b(?:"
        r"Obelisk[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*|"
        r"Register[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*"
        r")\b"
    ),
    "public_lookup_or_resource_handle_symbol": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*Resource(?:Handle|Id|ID|Ref|Reference|Token|Mutation|Mutable|Write|Update)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Mutate|Write|Update)Resource[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*Object(?:Handle|Id|ID|Identity|Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:player|identity|principal|resource|object)[-_ ]+"
        r"(?:lookup|resolver|resolve|resource[-_ ]+(?:handle|id|ref|reference|token)|object[-_ ]+handle)s?"
        r")\b",
        re.IGNORECASE,
    ),
    "public_mutable_or_return_override_symbol": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Mutation|Mutable|Mutate|ReturnOverride|ReturnOverrides)[A-Za-z0-9_]*|"
        r"(?:mutable|mutating|writable|writeable)[-_ ]+(?:identity|principal|player[-_ ]+identity|resource)|"
        r"(?:identity|principal|player[-_ ]+identity|resource)[-_ ]+(?:mutation|mutable|write|update)|"
        r"(?:mutate|write|update)[-_ ]+(?:identity|principal|resource)|return[-_ ]?overrides?"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|public|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_storage_or_lookup_symbol": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Storage|Store|Persistence|Persistent|Registry|Database|Cache)[A-Za-z0-9_]*|"
        r"(?:identity|principal|player[-_ ]+identity|player[-_ ]+principal|resource|object)"
        r"[-_ ]+(?:storage|store|persistence|persistent|registry|database|cache|lookup|resolver|resolve)|"
        r"(?:storage|store|persistence|persistent|registry|database|cache|lookup|resolver|resolve)"
        r"[-_ ]+(?:identity|principal|player[-_ ]+identity|resource|object)"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|public|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_command_or_reply_symbol": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Command|Commands|Reply|Replies|ChatResponse|SendChat|Broadcast|RCON|Rcon)[A-Za-z0-9_]*|"
        r"(?:commands?|chat[-_ ]+commands?|command[-_ ]+response|chat[-_ ]+response|"
        r"commands?[-_ ]+replies|chat[-_ ]+replies|send[-_ ]+chat|broadcast|rcon(?:[-_ ]+commands?)?)"
        r"[-_ ]+(?:api|abi|surface|event|callback|handler|router|path|symbol|function|support)"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|public|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_ownership_or_permissions_symbol": re.compile(
        r"\b(?:"
        r"Obelisk[A-Za-z0-9_]*(?:Ownership|Permissions?|Authorization|Admin|Authz|AccessControl|ACL|"
        r"Role|Privilege|Moderation|Moderator|Ban|Kick|"
        r"ResourceOwner|PlayerOwner|PrincipalOwner|Tribe)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Authz|Authorize|AccessControl|ACL|Grant|Revoke|Role|Privilege|"
        r"Moderation|Moderator|Ban|Kick)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Check|Has|Query)[A-Za-z0-9_]*Permission[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*"
        r"(?:Owner|Ownership|Permission|Permissions|Authz|Role|Privilege|Admin|Tribe)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:OwnerLookup|OwnerResolve|Ownership|Permission|Permissions|"
        r"Authorization|Authz|AccessControl|ACL|Role|Privilege|Moderation|Moderator|Ban|Kick|Admin|Tribe)[A-Za-z0-9_]*|"
        r"(?:ownership|owner[-_ ]+lookup|resource[-_ ]+owner|player[-_ ]+owner|"
        r"principal[-_ ]+owner|tribe[-_ ]+(?:id|lookup|owner)|permissions?|admin|authorization|"
        r"authz?|access[-_ ]+control|acl|roles?|privileges?|moderation|moderator|ban|kick)"
        r"[-_ ]+(?:api|abi|surface|event|callback|lookup|ready|available|supported|allowed|promoted)"
        r")\b",
        re.IGNORECASE,
    ),
    "contract_review_artifact_public_abi": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"public[-_ ]+headers?|installed[-_ ]+headers?|obelisk[-_ ]*api(?:\.h|[-_ ]+h)?|"
        r"cmake[-_ ]+package|cmake[-_ ]+config|"
        r"obelisk[-_ ]*config(?:\.cmake|[-_ ]+cmake)?|obelisk[-_ ]*targets(?:\.cmake|[-_ ]+cmake)?|"
        r"installed[-_ ]+sdk(?:[-_ ]+consumer(?:[-_ ]+tests?)?|[-_ ]+package[-_ ]+shape)?|"
        r"sdk[-_ ]+consumer[-_ ]+tests?|package[-_ ]+shape|"
        r"plugin[-_ ]+hub(?:[-_ ]+(?:wording|seed|package|support|publication))?|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?)\b[^\.;]{0,100}\b"
        r"(?:promotes?|proves?|validates?|unlock(?:s|ed)?|opens?|allows?|enables?|satisf(?:ies|y)|resolves?|counts?)\b"
        r"(?:[^\.;]{0,100}\b(?:public[-_ ]+abi|public[-_ ]+sdk|public[-_ ]+header|"
        r"capability[-_ ]+bits?|callback[-_ ]+abi|obelisk\.player_identity\.v1|"
        r"runtime[-_ ]+readiness|support[-_ ]+tier|stable[-_ ]+sdk|"
        r"plugin[-_ ]+hub|v1[-_ ]+completion|readiness|promotion))?",
        re.IGNORECASE,
    ),
    "publication_artifact_public_abi_reverse_claim": re.compile(
        r"\b(?:public[-_ ]+abi|public[-_ ]+sdk|public[-_ ]+header|callback[-_ ]+abi|"
        r"runtime[-_ ]+readiness|support[-_ ]+tier|stable[-_ ]+sdk|"
        r"plugin[-_ ]+hub|v1[-_ ]+completion|promotion)\b[^\.;]{0,100}\b"
        r"(?:promotes?|proves?|validates?|unlock(?:s|ed)?|opens?|allows?|enables?|satisf(?:ies|y)|resolves?|counts?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+headers?|installed[-_ ]+headers?|obelisk[-_ ]*api(?:\.h|[-_ ]+h)?|"
        r"cmake[-_ ]+package|cmake[-_ ]+config|"
        r"obelisk[-_ ]*config(?:\.cmake|[-_ ]+cmake)?|obelisk[-_ ]*targets(?:\.cmake|[-_ ]+cmake)?|"
        r"installed[-_ ]+sdk(?:[-_ ]+consumer(?:[-_ ]+tests?)?|[-_ ]+package[-_ ]+shape)?|"
        r"sdk[-_ ]+consumer[-_ ]+tests?|package[-_ ]+shape|"
        r"plugin[-_ ]+hub(?:[-_ ]+(?:wording|seed|package|support|publication))?)\b",
        re.IGNORECASE,
    ),
    "persistent_registration_state": re.compile(
        r"\b(?:persistent|persisted|durable|cross[-_ ]+process|cross[-_ ]+server|"
        r"cluster[-_ ]+shared|global)\b[^\.;]{0,80}\b"
        r"(?:identity[-_ ]+|player[-_ ]+identity[-_ ]+|registration[-_ ]+|callback[-_ ]+|principal[-_ ]+)?"
        r"(?:registr(?:y|ies|ations?)|handles?|ids?)\b",
        re.IGNORECASE,
    ),
    "persisted_registration_handles": re.compile(
        r"\b(?:persisted|persists?|persisting|reused?|shared)\b[^\.;]{0,80}\b"
        r"(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b"
        r"(?:[^\.;]{0,80}\b(?:across|cross[-_ ]+process|processes|servers?|instances?))?",
        re.IGNORECASE,
    ),
    "cross_process_registration_handles": re.compile(
        r"\b(?:registration|principal|callback|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?:cross[-_ ]+process|cross[-_ ]+server|shared\s+across\s+(?:processes|servers?|instances?)|"
        r"shared\s+across\s+ARK\s+server\s+processes|reused?\s+across\s+(?:processes|servers?|instances?)|"
        r"reused?\s+across\s+ARK\s+server\s+processes)\b",
        re.IGNORECASE,
    ),
    "registration_handles_persistent": re.compile(
        r"\b(?:registration|principal|callback|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?<!non-)(?<!non_)(?<!non )(?:persistent|persisted|durable|global)\b",
        re.IGNORECASE,
    ),
    "registration_handles_survive_restart_or_unload": re.compile(
        r"\b(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b[^\.;]{0,80}\b"
        r"(?:survives?|remain(?:s)?\s+valid|valid\s+after|restart[-_ ]+stable)\b[^\.;]{0,80}\b"
        r"(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart)\b|"
        r"\b(?:server[-_ ]+)?(?:restarts?|reloads?|unloads?|dlclose|process[-_ ]+restart)\b[^\.;]{0,80}\b"
        r"(?:preserves?|keeps?|retains?|reuses?)\b[^\.;]{0,80}\b"
        r"(?:registration|principal|callback|owner[-_ ]+token|handles?|ids?)\b",
        re.IGNORECASE,
    ),
    "ownerless_unregister": re.compile(
        r"\b(?:ownerless|owner[-_ ]+less)\b[^\.;]{0,80}\bunregister\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b|"
        r"\bunregister\b[^\.;]{0,80}\bwithout\b[^\.;]{0,40}\bowner[-_ ]+token\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b",
        re.IGNORECASE,
    ),
    "bare_unregister_by_id": re.compile(
        r"\b(?:bare[-_ ]+)?unregister[-_ ]+by[-_ ]+(?:id|handle)\b[^\.;]{0,80}"
        r"\b(?:allowed|ready|available|supported|permitted|exposed|enabled|valid)\b",
        re.IGNORECASE,
    ),
    "source_artifact_ready_alias": re.compile(
        r"\b(?:public[-_ ]+sdk|public[-_ ]+header|public[-_ ]+abi|callback[-_ ]+abi|"
        r"capability[-_ ]+bits?|runtime|promotion|support[-_ ]+tier|stable[-_ ]+sdk|"
        r"plugin[-_ ]+hub|v1[-_ ]+completion)[-_ ]+"
        r"(?:ready|allowed|available|enabled|promoted|complete|exposed)\b",
        re.IGNORECASE,
    ),
    "sdk_p0_progress_claim": re.compile(
        r"\b(?:abi[-_ ]+candidates?|candidate[-_ ]+abi|public[-_ ]+abi[-_ ]+preflight"
        r"(?:[-_ ]+candidate)?|layout[-_ ]+candidate|sdk[-_ ]+consumer[-_ ]+tests?)\b"
        r"[^\.;]{0,120}\b(?:counts?|counting|advances?|contributes?|unlocks?|opens?|"
        r"allows?|satisf(?:ies|y)|resolves?)\b[^\.;]{0,120}\b"
        r"(?:sdk[-_ ]*p0|p0[-_ ]+sdk|p0[-_ ]+progress|sdk[-_ ]+progress|v1[-_ ]+completion)\b|"
        r"\b(?:sdk[-_ ]*p0|p0[-_ ]+sdk|p0[-_ ]+progress|sdk[-_ ]+progress|v1[-_ ]+completion)\b"
        r"[^\.;]{0,120}\b(?:counts?|counting|advances?|contributes?|unlocks?|opens?|"
        r"allows?|satisf(?:ies|y)|resolves?)\b[^\.;]{0,120}\b"
        r"(?:abi[-_ ]+candidates?|candidate[-_ ]+abi|public[-_ ]+abi[-_ ]+preflight"
        r"(?:[-_ ]+candidate)?|layout[-_ ]+candidate|sdk[-_ ]+consumer[-_ ]+tests?)\b",
        re.IGNORECASE,
    ),
    "copied_api_table_escape_hatch": re.compile(
        r"\b(?:copied|captured|cached|stored|saved)[-_ ]+"
        r"(?:obelisk[-_ ]*api|api[-_ ]+table|ObeliskApi)\b[^\.;]{0,120}\b"
        r"(?:allows?|enables?|unlocks?|opens?|supports?|exposes?|bypasses?|widens?|"
        r"keeps?|preserves?|ready|available|valid|escape[-_ ]+hatch|"
        r"CallProcessEvent|call[-_ ]+process[-_ ]+event|capabilit(?:y|ies)|"
        r"public[-_ ]+(?:api|abi|sdk|header)|runtime[-_ ]+ready)",
        re.IGNORECASE,
    ),
    "post_init_call_process_event_shortcut": re.compile(
        r"\b(?:post[-_ ]+init|after[-_ ]+init|callback[-_ ]+time|copied|captured|cached|stored|saved)"
        r"\b[^\.;]{0,120}\b(?:CallProcessEvent|call[-_ ]+process[-_ ]+event)\b"
        r"[^\.;]{0,100}\b(?:shortcut|escape[-_ ]+hatch|allowed|available|ready|enabled|"
        r"exposed|promoted|public|unlocked|supported|valid)\b|"
        r"\b(?:CallProcessEvent|call[-_ ]+process[-_ ]+event)\b[^\.;]{0,100}\b"
        r"(?:post[-_ ]+init|after[-_ ]+init|callback[-_ ]+time)\b[^\.;]{0,100}\b"
        r"(?:shortcut|escape[-_ ]+hatch|allowed|available|ready|enabled|exposed|promoted|"
        r"public|unlocked|supported|valid)\b",
        re.IGNORECASE,
    ),
}
NON_COUNTING_PROVENANCE_CONTEXT_RE = re.compile(
    r"(?:source|sources|source_artifacts|provenance|evidence|accepted_inputs|"
    r"contract_review_inputs_accepted|runtime_bundle)",
    re.IGNORECASE,
)
NON_COUNTING_PROVENANCE_RE = re.compile(
    r"(?:diagnostic|passive|snapshot|request|preflight|window[-_ ]?manifest|receipt|sidecar|"
    r"installed[-_ ]?runtime|broadcast|rcon|"
    r"(?:principal|player)[-_ ]?start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:runtime[-_ ]?)?lifecycle[-_ ]?start[-_ ]?end[-_ ]?(?:evidence|artifact|report|manifest|bundle)?|"
    r"start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:start|end)[-_ ]?only[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"scoped[-_ ]?statement|release[-_ ]?statement|certificate|simulation|simulated|synthetic|"
    r"mock|fixture|partial[-_ ]?runtime|runtime[-_ ]?partial|copied[-_ ]?runtime[-_ ]?"
    r"(?:partial|fixture|mock)|truncated|incomplete|cmake[-_ ]?package|find[-_ ]?package|"
    r"package[-_ ]?shape|installed[-_ ]?sdk|plugin[-_ ]?hub|support[-_ ]?tier|release[-_ ]?support)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--private-pod-layout-candidate", type=Path, default=DEFAULT_PRIVATE_LAYOUT)
    parser.add_argument("--identifier-redaction-evidence", type=Path, default=DEFAULT_IDENTIFIER_REDACTION)
    parser.add_argument("--principal-invalidation-policy", type=Path, default=DEFAULT_PRINCIPAL_INVALIDATION)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(details)
    blockers.append(item)


def string_set(payload: dict[str, Any], key: str) -> set[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(value)


def normalize_contract_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def truthy_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalize_contract_key(value) in POSITIVE_CLAIM_VALUES
    if isinstance(value, list):
        return bool(value)
    if isinstance(value, dict):
        return any(truthy_claim_value(item) for item in value.values())
    return False


PUBLIC_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:public|identity|player_identity|principal|abi|sdk|header|headers|capability|callback|"
    r"payload|payload_shape|event_payload|descriptor|owner_token_contract|capability_bits|"
    r"lookup|resource_handle|resource_id|resource_ref|resource_reference|object_handle|"
    r"storage|persistence|persistent|registry|database|cache|sdk_p0|p0|sdk_progress|"
    r"resource_mutation|resource_mutable|mutable_resource|writable_resource|resource_write|"
    r"mutation|mutable|writable|writeable|return_override|"
    r"commands?|command_reply|commands_replies|chat_reply|send_chat|broadcast|rcon|"
    r"ownership|owner_lookup|resource_owner|permissions?|admin|tribe|"
    r"authz?|access_control|acl|roles?|privileges?|moderation|ban|kick|"
    r"owner_token|contract_review|review_artifact|runtime_evidence|runtime_marker|public_marker|"
    r"copied_api_table|captured_api_table|cached_api_table|stored_api_table|saved_api_table|"
    r"post_init_call_process_event|call_process_event_post_init|"
    r"call_process_event_escape|call_process_event_hatch|call_process_event_shortcut|"
    r"approved_runtime_evidence)"
    r".*(?:ready|readiness|marker|allowed|available|enabled|promot(?:e|es|ed|ion)|unlock(?:s|ed)?|"
    r"open(?:s|ed)?|clear(?:s|ed)?|complete|completion|resolv(?:e|es|ed)|satisf(?:y|ies|ied)|"
    r"claim|progress|counts?|counting|decisions?)",
    re.IGNORECASE,
)
STRUCT_SIZE_OR_LAYOUT_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:struct_?size|pod_?layout|abi_?layout|layout_?abi|fixed_?size|prefix_?compat|"
    r"payload_?shape|event_?payload|descriptor_?shape)"
    r".*(?:ready|readiness|allowed|available|complete|completion|claim|counts?|"
    r"accepted|approved|passed|promot(?:e|es|ed|ion)|resolved?|satisf(?:y|ies|ied)|"
    r"unlock(?:s|ed)?|validat(?:e|es|ed|ion)|verif(?:y|ies|ied))",
    re.IGNORECASE,
)
ROUTE_ACCEPTED_PUBLIC_ALIAS_KEY_RE = re.compile(
    r"(?:route|post_evidence|post_runtime_evidence|runtime_evidence|approved_runtime_evidence)"
    r".*(?:accept(?:ed|ance)?|counts?|counting|as)"
    r".*(?:public|identity|principal|abi|sdk|header|lookup|owner_token|complete|completion|claim)",
    re.IGNORECASE,
)
POST_GATE_READINESS_ALIAS_KEY_RE = re.compile(
    r"(?:runtime_?bundle|approved_?runtime_?bundle|public_?header_?gate|"
    r"header_?promotion_?gate|public_?header_?promotion_?gate)"
    r".*(?:accept(?:ed|ance)?|approv(?:ed|al)?|ready|readiness|available|present|"
    r"provided|review(?:ed)?|validat(?:ed|ion)|complete|completion|"
    r"satisf(?:y|ies|ied)|pass(?:es|ed)?|open(?:s|ed)?|counts?|counting|claim(?:ed)?)",
    re.IGNORECASE,
)
API_TABLE_ESCAPE_ALIAS_KEY_RE = re.compile(
    r"(?:copied|captured|cached|stored|saved)_?(?:obelisk_?api|api_?table)|"
    r"(?:obelisk_?api|api_?table)_?(?:copy|copied|capture|captured|cache|cached|escape|hatch)|"
    r"post_?init_?call_?process_?event|call_?process_?event_?post_?init|"
    r"call_?process_?event_?(?:escape|hatch|shortcut|available|ready|enabled|public|runtime)",
    re.IGNORECASE,
)
PUBLIC_OR_RUNTIME_MARKER_ALIAS_KEY_RE = re.compile(
    r"(?:public|runtime|identity|principal|header|api|abi|sdk|contract).*marker|"
    r"marker.*(?:public|runtime|identity|principal|header|api|abi|sdk|contract)",
    re.IGNORECASE,
)


def is_public_readiness_alias_key(normalized_key: str) -> bool:
    return bool(
        PUBLIC_READINESS_ALIAS_KEY_RE.search(normalized_key)
        or ROUTE_ACCEPTED_PUBLIC_ALIAS_KEY_RE.search(normalized_key)
        or STRUCT_SIZE_OR_LAYOUT_READINESS_ALIAS_KEY_RE.search(normalized_key)
        or POST_GATE_READINESS_ALIAS_KEY_RE.search(normalized_key)
        or API_TABLE_ESCAPE_ALIAS_KEY_RE.search(normalized_key)
        or PUBLIC_OR_RUNTIME_MARKER_ALIAS_KEY_RE.search(normalized_key)
    )


def walk_json(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, item in value.items():
            items.extend(walk_json(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            items.extend(walk_json(item, f"{path}[{index}]"))
    return items


def has_negative_context(value: str, match_start: int) -> bool:
    normalized = value.replace("_", " ")
    clause_start = max(normalized.rfind(";", 0, match_start), normalized.rfind(".", 0, match_start))
    clause_end_candidates = [
        index
        for index in (
            normalized.find(";", match_start),
            normalized.find(".", match_start),
        )
        if index != -1
    ]
    clause_end = min(clause_end_candidates) if clause_end_candidates else len(normalized)
    prefix = normalized[clause_start + 1 : match_start]
    suffix = normalized[match_start:clause_end]
    if re.search(r"(?:^|\b)non[-_ ]*$", prefix, re.IGNORECASE):
        return True
    if NEGATIVE_CONTEXT_RE.search(prefix):
        return True
    return bool(
        re.search(
            r"\b(?:forbidden|unavailable|blocked|redacted|cannot|can't|false)\b|"
            r"\bnot\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def public_text_overclaims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            if normalized_key not in PUBLIC_READINESS_FALSE_KEYS and normalized_key not in PUBLIC_EMPTY_LIST_KEYS:
                claims.extend(public_text_overclaims(str(key), item_path))
            claims.extend(public_text_overclaims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(public_text_overclaims(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                claims.append({"path": path, "term": term, "value": value})
                break
    return claims


def collect_non_counting_provenance_claims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    path_context = NON_COUNTING_PROVENANCE_CONTEXT_RE.search(path) is not None
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            key_context = path_context or NON_COUNTING_PROVENANCE_CONTEXT_RE.search(str(key)) is not None
            if key_context and NON_COUNTING_PROVENANCE_RE.search(str(key)):
                claims.append({"path": item_path, "term": "non_counting_provenance_key", "value": str(key)})
            claims.extend(collect_non_counting_provenance_claims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_non_counting_provenance_claims(item, f"{path}[{index}]"))
    elif isinstance(value, str) and path_context and NON_COUNTING_PROVENANCE_RE.search(value):
        claims.append({"path": path, "term": "non_counting_provenance_value", "value": value})
    return claims


def field_names(layout: dict[str, Any]) -> list[str]:
    fields = layout.get("fields")
    if not isinstance(fields, list):
        return []
    return [str(field.get("name")) for field in fields if isinstance(field, dict)]


def forbidden_payload_fields(shape: dict[str, Any]) -> list[str]:
    fields = shape.get("fields")
    if not isinstance(fields, list):
        return []
    return [
        field
        for field in fields
        if isinstance(field, str) and FORBIDDEN_PUBLIC_PAYLOAD_FIELD_RE.search(field)
    ]


def analyze_sdk_consumer_contract(payload: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    contract = payload.get("sdk_consumer_contract")
    if contract is None:
        required_before_public_abi = string_set(payload, "required_before_public_abi")
        does_not_resolve = string_set(payload, "does_not_resolve")
        owner_token_lifecycle = string_set(payload, "required_owner_token_lifecycle")
        missing_inputs = {
            "required_before_public_abi": sorted({"sdk.consumer", "lifecycle.owner_cleanup"} - required_before_public_abi),
            "does_not_resolve": sorted({"sdk.consumer", "lifecycle.owner_cleanup", "v1_completion"} - does_not_resolve),
            "required_owner_token_lifecycle": sorted(REQUIRED_OWNER_TOKEN_LIFECYCLE - owner_token_lifecycle),
        }
        missing_inputs = {key: value for key, value in missing_inputs.items() if value}
        if missing_inputs:
            add(blockers, "sdk_consumer_contract_derived_inputs_missing", "$.sdk_consumer_contract", missing=missing_inputs)
        return (
            {
                "source": "derived_compatibility_stub",
                "status": "blocked",
                "candidate_only": True,
                "accepted_for_candidate_review": not blockers,
                "accepted_for_contract_review": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "v1_completion_evidence": False,
                "required_behavior": sorted(REQUIRED_SDK_CONSUMER_CONTRACT),
                "owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
                "does_not_resolve": sorted(REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE),
                "public_header_symbols_now": [],
                "public_capability_bits_now": [],
                "public_callback_abi_now": [],
            },
            blockers,
        )

    if not isinstance(contract, dict):
        add(blockers, "sdk_consumer_contract_not_object", "$.sdk_consumer_contract")
        contract = {}
    for key, expected in (("status", "blocked"),):
        if contract.get(key) != expected:
            add(blockers, f"sdk_consumer_contract_{key}_mismatch", f"$.sdk_consumer_contract.{key}", value=contract.get(key))
    if contract.get("candidate_only") is not True:
        add(blockers, "sdk_consumer_contract_candidate_only_not_true", "$.sdk_consumer_contract.candidate_only")
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
    ):
        if contract.get(key) is not False:
            add(blockers, f"sdk_consumer_contract_{key}_not_false", f"$.sdk_consumer_contract.{key}")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if contract.get(key, []) != []:
            add(blockers, f"sdk_consumer_contract_{key}_not_empty", f"$.sdk_consumer_contract.{key}")
    required_behavior = contract.get("required_behavior")
    if not isinstance(required_behavior, list) or not all(isinstance(item, str) for item in required_behavior):
        add(blockers, "sdk_consumer_contract_required_behavior_not_string_list", "$.sdk_consumer_contract.required_behavior")
        required_behavior_set = set()
    else:
        required_behavior_set = set(required_behavior)
    missing_behavior = sorted(REQUIRED_SDK_CONSUMER_CONTRACT - required_behavior_set)
    if missing_behavior:
        add(
            blockers,
            "sdk_consumer_contract_required_behavior_missing",
            "$.sdk_consumer_contract.required_behavior",
            missing=missing_behavior,
        )
    does_not_resolve = contract.get("does_not_resolve")
    if not isinstance(does_not_resolve, list) or not all(isinstance(item, str) for item in does_not_resolve):
        add(blockers, "sdk_consumer_contract_does_not_resolve_not_string_list", "$.sdk_consumer_contract.does_not_resolve")
        does_not_resolve_set = set()
    else:
        does_not_resolve_set = set(does_not_resolve)
    missing_non_resolutions = sorted(REQUIRED_SDK_CONSUMER_DOES_NOT_RESOLVE - does_not_resolve_set)
    if missing_non_resolutions:
        add(
            blockers,
            "sdk_consumer_contract_does_not_resolve_missing",
            "$.sdk_consumer_contract.does_not_resolve",
            missing=missing_non_resolutions,
        )
    return (
        {
            "source": "manifest",
            "status": contract.get("status"),
            "candidate_only": contract.get("candidate_only") is True,
            "accepted_for_candidate_review": not blockers,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "required_behavior": contract.get("required_behavior", []),
            "owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
            "does_not_resolve": contract.get("does_not_resolve", []),
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
        },
        blockers,
    )


def strip_c_comments_and_strings(text: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"'}:
                output.append(" ")
                quote = char
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "code"
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "string":
            if char == "\\" and next_char:
                output.extend((" ", " "))
                index += 2
                continue
            if char == quote:
                output.append(" ")
                index += 1
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
    return "".join(output)


def scan_public_header(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        text = strip_c_comments_and_strings(
            without_native_prototype_symbols(path.read_text(encoding="utf-8"), header_only=True)
        )
    except OSError as exc:
        add(blockers, "public_header_unreadable", "--public-header", path=str(path), error=str(exc))
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in HEADER_ALLOWLIST or token in seen or not PUBLIC_HEADER_TOKEN_RE.search(token):
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    if detected:
        add(blockers, "public_header_identity_or_principal_symbols_detected", "--public-header", detected=detected)
    return {"path": str(path), "readable": True, "detected_player_identity_tokens": detected}


def validate_no_public_overclaim_aliases(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for path, item in walk_json(payload):
        key = path.rsplit(".", 1)[-1]
        if "[" in key:
            continue
        normalized_key = normalize_contract_key(key)
        if normalized_key in PUBLIC_READINESS_FALSE_KEYS and item is not False:
            add(blockers, "public_readiness_claim_not_false", path, value=item)
        elif is_public_readiness_alias_key(normalized_key) and truthy_claim_value(item):
            add(blockers, "public_readiness_claim_not_false", path, value=item)
        if normalized_key in PUBLIC_EMPTY_LIST_KEYS and item != []:
            add(blockers, "public_artifact_claim_not_empty", path, value=item)
        if normalized_key in FORBIDDEN_LIFECYCLE_CLAIM_KEYS and truthy_claim_value(item):
            add(blockers, "lifecycle_registration_claim_not_false", path, value=item)
    text_claims = public_text_overclaims(payload)
    if text_claims:
        add(blockers, "public_text_or_source_overclaim", "$", claims=text_claims)
    provenance_claims = collect_non_counting_provenance_claims(payload)
    if provenance_claims:
        add(blockers, "non_counting_provenance_claimed", "$", claims=provenance_claims)


def validate_manifest(payload: dict[str, Any], private_payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    validate_no_public_overclaim_aliases(payload, blockers)
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", value=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", value=payload.get("surface"))
    for key, expected in (
        ("artifact_status", "candidate_only"),
        ("visibility", "planning_contract"),
        ("status", "blocked"),
    ):
        if payload.get(key) != expected:
            add(blockers, f"{key}_mismatch", f"$.{key}", value=payload.get(key))
    for key in ("candidate_only", "accepted_for_candidate_review"):
        if payload.get(key) is not True:
            add(blockers, f"{key}_not_true", f"$.{key}", value=payload.get(key))
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
    ):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", value=payload.get(key))
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}", value=payload.get(key))

    accepted = payload.get("contract_review_inputs_accepted")
    if not isinstance(accepted, dict):
        add(blockers, "contract_review_inputs_accepted_missing", "$.contract_review_inputs_accepted")
        accepted = {}
    unexpected_inputs = sorted(str(key) for key in set(accepted) - REQUIRED_ACCEPTED_INPUTS)
    if unexpected_inputs:
        add(
            blockers,
            "contract_review_inputs_accepted_unexpected",
            "$.contract_review_inputs_accepted",
            unexpected=unexpected_inputs,
        )
    for key in sorted(REQUIRED_ACCEPTED_INPUTS):
        if accepted.get(key) is not True:
            add(blockers, "contract_review_input_not_true", f"$.contract_review_inputs_accepted.{key}")

    for key, required in (
        ("required_before_public_abi", REQUIRED_BEFORE_PUBLIC_ABI),
        ("does_not_resolve", REQUIRED_DOES_NOT_RESOLVE),
        ("required_capability_policy", REQUIRED_CAPABILITY_POLICY),
        ("required_owner_token_lifecycle", REQUIRED_OWNER_TOKEN_LIFECYCLE),
        ("non_claims", REQUIRED_NON_CLAIMS),
    ):
        missing = sorted(required - string_set(payload, key))
        if missing:
            add(blockers, f"{key}_missing_required", f"$.{key}", missing=missing)
    _sdk_report, sdk_blockers = analyze_sdk_consumer_contract(payload)
    blockers.extend(sdk_blockers)

    event = payload.get("event_payload")
    descriptor = payload.get("descriptor")
    if not isinstance(event, dict):
        add(blockers, "event_payload_missing", "$.event_payload")
        event = {}
    if not isinstance(descriptor, dict):
        add(blockers, "descriptor_missing", "$.descriptor")
        descriptor = {}
    for key, shape in (("event_payload", event), ("descriptor", descriptor)):
        detected = forbidden_payload_fields(shape)
        if detected:
            add(
                blockers,
                "public_payload_shape_forbidden_surface",
                f"$.{key}.fields",
                detected=detected,
            )
    private_event = private_payload.get("event_payload_layout") if isinstance(private_payload, dict) else {}
    private_descriptor = private_payload.get("descriptor_layout") if isinstance(private_payload, dict) else {}
    if event.get("struct_size") != private_event.get("struct_size") or event.get("alignment") != private_event.get("alignment"):
        add(blockers, "event_payload_private_layout_mismatch", "$.event_payload")
    if event.get("fields") != field_names(private_event):
        add(blockers, "event_payload_fields_private_layout_mismatch", "$.event_payload.fields")
    if descriptor.get("struct_size") != private_descriptor.get("struct_size") or descriptor.get("alignment") != private_descriptor.get("alignment"):
        add(blockers, "descriptor_private_layout_mismatch", "$.descriptor")
    if descriptor.get("fields") != field_names(private_descriptor):
        add(blockers, "descriptor_fields_private_layout_mismatch", "$.descriptor.fields")


def validate_claimed_contract_review_inputs(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    redaction_report: dict[str, Any],
    principal_report: dict[str, Any],
    private_layout_report: dict[str, Any],
) -> None:
    accepted = payload.get("contract_review_inputs_accepted")
    if not isinstance(accepted, dict):
        return
    checks = (
        (
            "privacy.identifier_redaction",
            redaction_report.get("accepted_for_contract_review") is True,
            redaction_report.get("blockers", []),
        ),
        (
            "lifetime.generation_scope_invalidation.candidate_policy",
            principal_report.get("ready") is True,
            principal_report.get("blockers", []),
        ),
        (
            "abi.public_pod_contract.private_layout_candidate",
            private_layout_report.get("accepted_for_contract_review") is True,
            private_layout_report.get("blockers", []),
        ),
    )
    for key, accepted_now, input_blockers in checks:
        if accepted.get(key) is True and not accepted_now:
            add(
                blockers,
                "claimed_contract_review_input_not_accepted",
                f"$.contract_review_inputs_accepted.{key}",
                input=key,
                input_blockers=input_blockers,
            )


def build_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    header_scan: dict[str, Any],
    private_layout_report: dict[str, Any],
    redaction_report: dict[str, Any],
    principal_report: dict[str, Any],
) -> dict[str, Any]:
    sdk_consumer_contract, _sdk_blockers = analyze_sdk_consumer_contract(payload)
    preflight_valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE,
        "ready": False,
        "ready_scope": PREFLIGHT_SCOPE,
        "preflight_valid": preflight_valid,
        "preflight_scope": PREFLIGHT_SCOPE,
        "valid": preflight_valid,
        "status": payload.get("status"),
        "candidate_only": payload.get("candidate_only") is True,
        "accepted_for_candidate_review": payload.get("accepted_for_candidate_review") is True and preflight_valid,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "v1_completion_evidence": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "contract_review_inputs_accepted": payload.get("contract_review_inputs_accepted", {}),
        "required_before_public_abi": payload.get("required_before_public_abi", []),
        "does_not_resolve": payload.get("does_not_resolve", []),
        "required_capability_policy": payload.get("required_capability_policy", []),
        "required_owner_token_lifecycle": payload.get("required_owner_token_lifecycle", []),
        "sdk_consumer_contract": sdk_consumer_contract,
        "event_payload": payload.get("event_payload", {}),
        "descriptor": payload.get("descriptor", {}),
        "private_pod_layout_candidate": {
            "accepted_for_contract_review": private_layout_report.get("accepted_for_contract_review") is True,
            "blockers": private_layout_report.get("blockers", []),
        },
        "identifier_redaction_evidence": {
            "accepted_for_contract_review": redaction_report.get("accepted_for_contract_review") is True,
            "blockers": redaction_report.get("blockers", []),
        },
        "principal_invalidation_policy": {
            "ready": principal_report.get("ready") is True,
            "candidate_only": principal_report.get("candidate_only") is True,
            "blockers": principal_report.get("blockers", []),
        },
        "public_header_scan": header_scan,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": payload.get("non_claims", []),
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    try:
        payload = load_json(args.manifest)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"--manifest invalid: {exc}") from exc
    try:
        private_payload = private_layout.load_json(args.private_pod_layout_candidate)
        private_contract = private_layout.load_json(private_layout.DEFAULT_PRIVATE_CONTRACT)
        private_blockers = private_layout.validate_manifest(private_payload, private_contract)
        private_report = private_layout.build_report(private_payload, private_blockers)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        private_payload = {}
        private_report = {"accepted_for_contract_review": False, "blockers": ["private_pod_layout_candidate_unreadable"]}
        add(blockers, "private_pod_layout_candidate_unreadable", "--private-pod-layout-candidate", error=str(exc))
    else:
        if private_blockers:
            add(
                blockers,
                "private_pod_layout_candidate_not_accepted",
                "--private-pod-layout-candidate",
                input_blockers=private_report["blockers"],
            )
    try:
        redaction_payload = identifier_redaction.load_evidence(args.identifier_redaction_evidence)
        redaction_blockers = identifier_redaction.validate_evidence(redaction_payload)
        redaction_report = identifier_redaction.build_report(redaction_payload, redaction_blockers)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        redaction_report = {"accepted_for_contract_review": False, "blockers": ["identifier_redaction_evidence_unreadable"]}
        add(blockers, "identifier_redaction_evidence_unreadable", "--identifier-redaction-evidence", error=str(exc))
    else:
        if redaction_blockers:
            add(
                blockers,
                "identifier_redaction_evidence_not_accepted",
                "--identifier-redaction-evidence",
                input_blockers=redaction_report["blockers"],
            )
    try:
        principal_payload = principal_invalidation.load_json(args.principal_invalidation_policy)
        principal_validation = principal_invalidation.validate_manifest(principal_payload, check_mode="consume")
        principal_report = principal_invalidation.build_report(
            principal_payload,
            principal_validation,
            check_mode="consume",
        )
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        principal_report = {"ready": False, "candidate_only": False, "blockers": ["principal_invalidation_policy_unreadable"]}
        add(blockers, "principal_invalidation_policy_unreadable", "--principal-invalidation-policy", error=str(exc))
    else:
        if principal_validation.blockers:
            add(
                blockers,
                "principal_invalidation_policy_not_accepted",
                "--principal-invalidation-policy",
                input_blockers=principal_report["blockers"],
            )
    header_scan = scan_public_header(args.public_header, blockers)
    validate_manifest(payload, private_payload, blockers)
    validate_claimed_contract_review_inputs(
        payload,
        blockers,
        redaction_report=redaction_report,
        principal_report=principal_report,
        private_layout_report=private_report,
    )
    report = build_report(
        payload,
        blockers,
        header_scan=header_scan,
        private_layout_report=private_report,
        redaction_report=redaction_report,
        principal_report=principal_report,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "player identity public ABI preflight candidate: "
            + ("ok" if report["preflight_valid"] else "blocked")
        )
    return 0 if report["preflight_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
