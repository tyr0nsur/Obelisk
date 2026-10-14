#!/usr/bin/env python3
"""Validate the proposal-only player identity public header gate.

This checker prepares the narrow public-header promotion path after
`public_header_gate_missing`. Passing means the proposal is internally coherent and the
current public header has not already exposed the symbols. It is not public header,
runtime, SDK, or v1 completion readiness.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_player_identity_public_contract_decision_record as public_contract_decision_record
import check_player_identity_public_contract_gap_report as public_contract_gap_report
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "obelisk.player-identity-public-header-gate-proposal.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-header-gate-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_PROPOSAL = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-public-header-gate-proposal.json"
)
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_PUBLIC_CONTRACT_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
DEFAULT_REVIEWED_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "reviewed-identity-public-contract-decision-record.json"
)
EXPECTED_CAPABILITY = {
    "name": "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_EVENTS",
    "value": "1ull << 12",
    "append_after": "OBELISK_API_CAPABILITY_TIMERS",
}
EXPECTED_ABI_VERSIONS = [
    "OBELISK_PLAYER_PRINCIPAL_EVENT_ABI_VERSION",
    "OBELISK_PLAYER_PRINCIPAL_DESCRIPTOR_ABI_VERSION",
]
EXPECTED_PUBLIC_CONSTANT_SOURCE = "docs/player_identity_public_contract_decisions.json#proposed_public_pod_abi_candidate"
PUBLIC_CONSTANT_GROUP_SPECS = [
    (
        "event_kind",
        "supported_event_kind_mask",
        "OBELISK_PLAYER_PRINCIPAL_EVENT_KIND_SUPPORTED_MASK",
        [
            ("session_start", "OBELISK_PLAYER_PRINCIPAL_EVENT_KIND_SESSION_START", 0),
            ("session_start_rejected", "OBELISK_PLAYER_PRINCIPAL_EVENT_KIND_SESSION_START_REJECTED", 1),
            ("session_end", "OBELISK_PLAYER_PRINCIPAL_EVENT_KIND_SESSION_END", 2),
        ],
    ),
    (
        "principal_scope_flags",
        "supported_scope_flags",
        "OBELISK_PLAYER_PRINCIPAL_SCOPE_FLAGS_SUPPORTED_MASK",
        [
            ("callback_local", "OBELISK_PLAYER_PRINCIPAL_SCOPE_FLAG_CALLBACK_LOCAL", 0),
            ("process_local", "OBELISK_PLAYER_PRINCIPAL_SCOPE_FLAG_PROCESS_LOCAL", 1),
            ("restart_local_planning_only", "OBELISK_PLAYER_PRINCIPAL_SCOPE_FLAG_RESTART_LOCAL_PLANNING_ONLY", 2),
        ],
    ),
    (
        "principal_state_flags",
        "supported_state_flags",
        "OBELISK_PLAYER_PRINCIPAL_STATE_FLAGS_SUPPORTED_MASK",
        [
            ("candidate_created", "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_CANDIDATE_CREATED", 0),
            ("candidate_invalidated", "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_CANDIDATE_INVALIDATED", 1),
            ("candidate_rejected", "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_CANDIDATE_REJECTED", 2),
            ("stale_generation", "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_STALE_GENERATION", 3),
            ("unsupported_scope", "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_UNSUPPORTED_SCOPE", 4),
        ],
    ),
    (
        "invalidation_reason_flags",
        "supported_invalidation_reason_flags",
        "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASONS_SUPPORTED_MASK",
        [
            ("logout", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_LOGOUT", 0),
            ("disconnect", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_DISCONNECT", 1),
            ("transfer", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_TRANSFER", 2),
            ("reconnect", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_RECONNECT", 3),
            ("duplicate_observation", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_DUPLICATE_OBSERVATION", 4),
            ("server_restart", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_SERVER_RESTART", 5),
            (
                "stale_controller_or_playerstate",
                "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_STALE_CONTROLLER_OR_PLAYERSTATE",
                6,
            ),
            ("failed_evidence_validation", "OBELISK_PLAYER_PRINCIPAL_INVALIDATION_REASON_FAILED_EVIDENCE_VALIDATION", 7),
        ],
    ),
    (
        "contract_flags",
        "contract_flags",
        "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAGS_SUPPORTED_MASK",
        [
            ("copied_payload", "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_COPIED_PAYLOAD", 0),
            (
                "callback_local_payload_lifetime",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_CALLBACK_LOCAL_PAYLOAD_LIFETIME",
                1,
            ),
            (
                "process_local_principal_handle",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_PROCESS_LOCAL_PRINCIPAL_HANDLE",
                2,
            ),
            ("no_lookup", "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_LOOKUP", 3),
            ("no_persistence", "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_PERSISTENCE", 4),
            (
                "no_permissions_or_commands_authority",
                "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_PERMISSIONS_OR_COMMANDS_AUTHORITY",
                5,
            ),
            ("no_mutation", "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_MUTATION", 6),
            ("no_return_override", "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_RETURN_OVERRIDE", 7),
        ],
    ),
]


def constant_mask(bit: int) -> str:
    return f"0x{1 << bit:016x}ull"


def supported_mask(bits: list[int]) -> str:
    value = 0
    for bit in bits:
        value |= 1 << bit
    return f"0x{value:016x}ull"


def expected_public_constants() -> dict[str, Any]:
    groups = []
    for field, descriptor_mask_field, supported_mask_name, constants in PUBLIC_CONSTANT_GROUP_SPECS:
        groups.append(
            {
                "field": field,
                "descriptor_mask_field": descriptor_mask_field,
                "constants": [
                    {
                        "candidate_value": candidate_value,
                        "name": name,
                        "value": f"1ull << {bit}",
                        "mask": constant_mask(bit),
                    }
                    for candidate_value, name, bit in constants
                ],
                "supported_mask": {
                    "name": supported_mask_name,
                    "value": supported_mask([bit for _candidate_value, _name, bit in constants]),
                },
            }
        )
    return {
        "status": "proposal_only_not_public",
        "candidate_vocabulary_source": EXPECTED_PUBLIC_CONSTANT_SOURCE,
        "ordered_groups": groups,
    }


EXPECTED_PUBLIC_CONSTANTS = expected_public_constants()
EXPECTED_EVENT_FIELDS = [
    ("abi_version", "uint32_t", 0, 4),
    ("struct_size", "uint32_t", 4, 4),
    ("event_kind", "uint64_t", 8, 8),
    ("principal_handle", "uint64_t", 16, 8),
    ("principal_generation", "uint64_t", 24, 8),
    ("principal_scope_flags", "uint64_t", 32, 8),
    ("principal_state_flags", "uint64_t", 40, 8),
    ("invalidation_reason_flags", "uint64_t", 48, 8),
    ("event_sequence", "uint64_t", 56, 8),
    ("server_process_epoch", "uint64_t", 64, 8),
    ("reserved", "uint64_t", 72, 8),
]
EXPECTED_DESCRIPTOR_FIELDS = [
    ("abi_version", "uint32_t", 0, 4),
    ("struct_size", "uint32_t", 4, 4),
    ("supported_event_kind_mask", "uint64_t", 8, 8),
    ("supported_scope_flags", "uint64_t", 16, 8),
    ("supported_state_flags", "uint64_t", 24, 8),
    ("supported_invalidation_reason_flags", "uint64_t", 32, 8),
    ("contract_flags", "uint64_t", 40, 8),
]
EXPECTED_STRUCTS = {
    "ObeliskPlayerPrincipalEvent": {
        "size": 80,
        "alignment": 8,
        "fields": EXPECTED_EVENT_FIELDS,
        "reserved_zero_required": True,
    },
    "ObeliskPlayerPrincipalDescriptor": {
        "size": 48,
        "alignment": 8,
        "fields": EXPECTED_DESCRIPTOR_FIELDS,
        "reserved_zero_required": False,
    },
}
EXPECTED_CALLBACK = "ObeliskPlayerPrincipalEventCallback"
EXPECTED_API_SLOTS = [
    "RegisterPlayerPrincipalEventWithOwnerTokenHandle",
    "UnregisterPlayerPrincipalEventWithOwnerToken",
    "DescribePlayerPrincipalEventContract",
]
EXPECTED_API_APPEND_AFTER = "UnregisterTimerWithOwnerToken"
EXPECTED_SOURCE_ARTIFACTS = {
    "public_abi_preflight_candidate": "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json",
    "owner_token_sdk_consumer_contract": "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json",
    "reviewed_identity_public_contract_decision_record": "docs/research/player-identity-planning-sources/reviewed-identity-public-contract-decision-record.json",
}
NON_COUNTING_SOURCE_ARTIFACT_RE = re.compile(
    r"(?:notice|beta[-_ ]?notice|diagnostic|passive|passive[-_ ]?monitor|"
    r"extended[-_ ]?(?:passive[-_ ]?)?monitor|monitor[-_ ]?(?:snapshot|log)|snapshot|"
    r"post[-_ ]?reboot|confirmed[-_ ]?beta[-_ ]?notice|copied[-_ ]?log[-_ ]?only|"
    r"next[-_ ]?actions?|next[-_ ]?action[-_ ]?status|status[-_ ]?report|"
    r"route[-_ ]?status|runtime[-_ ]?status|readiness[-_ ]?status|status[-_ ]?json|status\.json|"
    r"post[-_ ]?runtime[-_ ]?bridge(?:[-_ ]?(?:build|builder|report|artifact|manifest))?|"
    r"bridge[-_ ]?(?:build|builder)[-_ ]?report|shutdown[-_ ]?worker|worker[-_ ]?shutdown|"
    r"shutdown[-_ ]?(?:report|artifact|manifest)|"
    r"installed[-_ ]?runtime[-_ ]?(?:status[-_ ]?)?checks?|"
    r"(?:broadcast|rcon)[-_ ]?status(?:[-_ ]?(?:checks?|reports?|artifacts?))?|"
    r"(?:principal|player)[-_ ]?start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:runtime[-_ ]?)?lifecycle[-_ ]?start[-_ ]?end[-_ ]?(?:evidence|artifact|report|manifest|bundle)?|"
    r"start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:start|end)[-_ ]?only[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"request|preflight|window[-_ ]?manifest|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:plan|planning|request|manifest|execution|executor|status|receipt|sidecar))?|"
    r"receipt|sidecar|closure|closure[-_ ]?report|"
    r"executor|executor[-_ ]?report|approved[-_ ]?(?:alias|manifest)|approval[-_ ]?alias|"
    r"no[-_ ]?(?:users?|players?)|zero[-_ ]?players?|empty[-_ ]?server|"
    r"(?:runtime|player)[-_ ]?presence|presence[-_ ]?(?:snapshot|monitor|status|log)|"
    r"scoped[-_ ]?statement|release[-_ ]?statement|certificate|simulation|simulated|synthetic|"
    r"mock|fixture|partial[-_ ]?runtime|runtime[-_ ]?partial|copied[-_ ]?runtime[-_ ]?"
    r"(?:partial|fixture|mock)|truncated|incomplete|cmake[-_ ]?package|find[-_ ]?package|"
    r"(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?(?:[-_ ]?(?:total[-_ ]?flag[-_ ]?count|"
    r"component[-_ ]?count|summary|diagnostics?|zero))?|"
    r"(?:ready|accepted|complete|completed)[-_ ]?(?:alias|shortcut|artifact|manifest)|"
    r"package[-_ ]?shape|support[-_ ]?package|package[-_ ]?support|package[-_ ]?alias|"
    r"support[-_ ]?alias|installed[-_ ]?sdk|plugin[-_ ]?hub|support[-_ ]?tier|release[-_ ]?support)",
    re.IGNORECASE,
)
PUBLIC_SHORTCUT_SOURCE_ARTIFACT_RE = re.compile(
    r"(?:public[-_ ]?header(?:[-_ ]?(?:gate|proposal|allowed|ready|readiness|shortcut|symbols?))?|"
    r"public[-_ ]?api(?:[-_ ]?(?:gate|allowed|ready|readiness|shortcut))?|"
    r"public[-_ ]?abi(?:[-_ ]?(?:gate|promotion|ready|readiness|shortcut))?|"
    r"public[-_ ]?sdk(?:[-_ ]?(?:ready|readiness|shortcut|completion))?|"
    r"runtime[-_ ]?readiness|header[-_ ]?shape|"
    r"public_header_allowed|public_sdk_ready|runtime_ready)",
    re.IGNORECASE,
)
PUBLIC_CONTRACT_CANDIDATE_KEY = "proposed_public_pod_abi_candidate"
REQUIRED_CONTRACT_EVENT_PAYLOAD_FIELDS = {
    "event_sequence",
    "server_process_epoch",
}
REQUIRED_CONTRACT_DESCRIPTOR_FIELDS = {
    "contract_flags",
}
REQUIRED_EVENT_SEQUENCE_POLICY = {
    "event_sequence is assigned once per copied source lifecycle event",
    "all subscribers to the same source lifecycle event observe the same event_sequence",
    "event_sequence is not a per-plugin delivery counter",
    "event_sequence is process-local and non-persistent",
}
REQUIRED_SERVER_PROCESS_EPOCH_POLICY = {
    "server_process_epoch is process-local and changes across server process lifetimes",
    "server_process_epoch invalidates process-local principal handles after restart",
    "server_process_epoch is not cluster-stable and not persistent",
}
PROMOTION_EVENT_SEQUENCE_POLICY = {
    "event_sequence is nonzero for every delivered player-principal event",
    "event_sequence value 0 is invalid for public-header promotion",
}
PROMOTION_SERVER_PROCESS_EPOCH_POLICY = {
    "server_process_epoch is nonzero for every delivered player-principal event",
    "server_process_epoch value 0 is invalid for public-header promotion",
}
NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW = "public_header_gate_missing"
REVIEWED_IDENTITY_PUBLIC_CONTRACT_SOURCE_ARTIFACT_HASH_POLICY = (
    public_contract_decision_record.SOURCE_ARTIFACT_HASH_POLICY
)
POST_RUNTIME_EVIDENCE_GATE_SOURCE_ARTIFACT_HASH_POLICY = public_contract_decision_record.SOURCE_ARTIFACT_HASH_POLICY
REQUIRED_REVIEWED_IDENTITY_PUBLIC_CONTRACT_SOURCE_ARTIFACTS = {
    "public_contract_decisions": {
        "path": "docs/player_identity_public_contract_decisions.json",
        "role": "post_runtime_identity_contract_gate_policy",
        "counting_scope": "reviewed_identity_public_contract_review",
    },
    "public_abi_preflight_candidate": {
        "path": "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json",
        "role": "candidate_only_public_abi_review_input",
        "counting_scope": "reviewed_identity_public_contract_review",
    },
    "owner_token_sdk_consumer_contract": {
        "path": "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json",
        "role": "candidate_only_owner_token_lifecycle_review_input",
        "counting_scope": "reviewed_identity_public_contract_review",
    },
    "principal_invalidation_policy": {
        "path": "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json",
        "role": "candidate_only_principal_lifetime_review_input",
        "counting_scope": "reviewed_identity_public_contract_review",
    },
}
REQUIRED_POST_RUNTIME_EVIDENCE_BASE_DECISION_KEYS = [
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
]
REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS = [
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
]
REQUIRED_POST_RUNTIME_EVIDENCE_DECISION_KEYS = (
    REQUIRED_POST_RUNTIME_EVIDENCE_BASE_DECISION_KEYS + REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS
)
REQUIRED_POST_RUNTIME_EVIDENCE_AUDIT_INPUTS = {
    "approved_runtime_evidence_intake",
    "approved_runtime_evidence_not_sufficient",
    "contract_gate_inputs",
    "proposed_public_pod_abi_candidate",
    "required_before_public_header",
    "required_tests_before_public_header",
}
REQUIRED_POST_EVIDENCE_NON_COUNTING_ARTIFACT_CLASSES = [
    "post-reboot passive monitor context",
    "passive or extended monitor snapshots/logs",
    "confirmed beta notice JSON",
    "beta notices",
    "next-action/status reports",
    "status JSON artifacts",
    "copied-log-only artifacts",
    "installed runtime, broadcast, or RCON status checks",
    "package-shape artifacts",
    "source-overclaim zero diagnostics",
    "post-runtime bridge build reports or shutdown-worker artifacts",
    "historical handoff text",
    "request/preflight/window manifests",
    "operator receipts or live-ops sidecars",
    "diagnostic-only artifacts",
    "scoped/non-complete release statements",
    "promotion or completion certificates",
    "simulation/mock/fixture artifacts",
]
REQUIRED_PLAYER_IDENTITY_P0_DEPENDENCY_CHAIN = [
    "player_identity",
    "permissions_admin",
    "command_chat_response_path",
    "commands_replies",
]
REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS = [
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_readiness",
    "runtime_readiness",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "counts_toward_public_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "public_sdk_v1_completion_ready",
    "complete_sdk_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "commands_replies_ready",
    "v1_completion_evidence",
]
REQUIRED_NON_COUNTING_CANDIDATE_ALIAS_POLICY = {
    "accepted_for_public_header_gate_review": False,
    "alias_classes": [
        "copied-log candidate aliases",
        "preflight aliases",
        "review-status aliases",
        "live-ops sidecar candidate aliases",
        "beta or confirmed-beta notice candidate aliases",
        "passive or post-reboot passive monitor candidate aliases",
        "diagnostic-only candidate aliases",
    ],
    "can_count_candidate_aliases": False,
    "can_count_preflight_aliases": False,
    "can_count_review_aliases": False,
    "can_replace_reviewed_identity_public_contract_decision_record": False,
    "can_unlock_identity_public_contract_gate_missing": False,
    "can_unlock_public_identity_contract_readiness": False,
    "non_claim": (
        "Candidate, preflight, review-status, copied-log, sidecar, beta, passive, and diagnostic "
        "aliases remain non-counting after accepted runtime evidence; they cannot unlock "
        "identity_public_contract_gate_missing, public identity contract readiness, public header "
        "review, P0 progress, or replace the hash-current reviewed identity public contract "
        "decision record."
    ),
    "p0_progress_contribution": 0,
}
REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT = {
    **public_contract_gap_report.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
    "must_remain_false": REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS,
    "non_counting_artifact_classes": REQUIRED_POST_EVIDENCE_NON_COUNTING_ARTIFACT_CLASSES,
    "non_counting_candidate_alias_policy": REQUIRED_NON_COUNTING_CANDIDATE_ALIAS_POLICY,
    "source_artifact_hash_policy": POST_RUNTIME_EVIDENCE_GATE_SOURCE_ARTIFACT_HASH_POLICY,
}
REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION = {
    "status": "preparable_offline_not_counting",
    "active_after_resolved_input": "runtime.lifecycle_evidence",
    "blocked_until_resolved_input": "runtime.lifecycle_evidence",
    "current_blocker_before_resolved_input": "approved_runtime_evidence_missing",
    "next_blocker_after_resolved_input": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "checkable_artifact": (
        "docs/research/player-identity-planning-sources/"
        "reviewed-identity-public-contract-decision-record.json"
    ),
    "checker": "scripts/check_player_identity_public_contract_decision_record.py",
    "required_review_route": public_contract_decision_record.REVIEW_ROUTE,
    "must_bind_to_approved_runtime_evidence": True,
    "must_bind_current_source_artifacts": True,
    "must_remain_contract_review_only": True,
    "must_resolve_decision_keys": REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
    "must_remain_false": REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS,
    "does_not_unlock_identity_public_contract_gate": True,
    "does_not_unlock_public_header_gate": True,
    "public_header_allowed": False,
    "public_abi_ready": False,
    "public_api_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "v1_completion_evidence": False,
    "p0_progress_contribution": 0,
    "non_claim": (
        "This is offline preparation for the reviewed identity public contract record only; it remains "
        "non-counting until approved runtime lifecycle evidence resolves runtime.lifecycle_evidence and "
        "cannot unlock identity_public_contract_gate_missing, public header/API/ABI/SDK/runtime readiness, "
        "P0 progress, or v1 completion."
    ),
}
REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT = {
    "id": "player_identity_public_header_gate_proposal",
    "status": "candidate_only",
    "checker": "scripts/check_player_identity_public_header_gate.py",
    "must_remain_non_claim": True,
    "public_header_allowed": False,
}
REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_FALSE_FLAGS = (
    "accepted_decision_record_opens_public_header_gate",
    "public_header_readiness_from_decision_record",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "runtime_readiness",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "complete_sdk_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
)
REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_NON_CLAIM = (
    "An accepted strict runtime bundle plus a bound reviewed identity public contract record only "
    "makes the public header gate proposal the next auditable fail-closed artifact; it does not open "
    "the public header/API/ABI, expose callbacks or capability bits, promote the SDK/runtime, unlock "
    "lookup or downstream surfaces, or count toward SDK/P0/v1 completion."
)
REQUIRED_POST_RUNTIME_EVIDENCE_NON_CLAIM = (
    "After approved runtime lifecycle evidence resolves runtime.lifecycle_evidence, the next blocker is "
    "identity_public_contract_gate_missing; this remains an offline reviewed public identity contract gate "
    "and cannot open public identity, lookup, public API/ABI/header, callbacks, capability bits, runtime "
    "readiness, SDK readiness, stable readiness, Plugin Hub readiness, publication, permissions/admin, "
    "command/chat surfaces, or v1 completion."
)
REQUIRED_POST_RUNTIME_EVIDENCE_FALSE_FLAGS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "counts_toward_public_sdk",
    "counts_toward_complete_sdk_claim",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "public_sdk_v1_completion_ready",
    "complete_sdk_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "commands_replies_ready",
    "v1_completion_evidence",
)
POST_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS = (
    "public_contract_allowed",
    "public_readiness",
    "runtime_readiness",
    "public_api_ready",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
    "public_api_gate_ready",
    "public_api_gate_unlocked",
    "public_abi_gate_ready",
    "public_abi_gate_unlocked",
    "identity_public_contract_ready",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_unlocked",
    "public_identity_ready",
    "public_principal_ready",
    "lookup_ready",
    "lookup_allowed",
    "player_lookup_ready",
    "principal_lookup_ready",
    "public_lookup_ready",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "commands_ready",
    "command_response_ready",
    "command_response_unlocked",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "chat_replies_ready",
    "send_chat_ready",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "public_sdk_v1_completion_ready",
    "public_sdk_v1_completion_claim",
    "complete_sdk_ready",
    "complete_sdk_counting_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "resource_handle_ready",
    "resource_handle_supported",
    "resource_handle_allowed",
    "mutation_allowed",
    "mutation_ready",
    "return_override_allowed",
    "return_override_ready",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY = {
    "runtime evidence can prove a candidate lifecycle route was observed; it does not define a stable C ABI",
    "runtime evidence can show login/logout ordering; it does not choose the copied opaque identifier form, generation rules, or scope flags",
    "runtime evidence can show logout observations; it does not prove the private logout correlation contract required before public identity promotion",
    "runtime evidence can support internal lifecycle semantics; it does not prove owner-token registration, unregister, plugin unload cleanup, or in-flight callback drain",
    "runtime evidence does not provide ABI layout tests, SDK consumer tests, or append-only compatibility rules",
    "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics",
    "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES = {
    "privacy and redaction decision resolved",
    "principal lifetime and invalidation decision resolved",
    "private logout correlation contract resolved",
    "cross-instance/process-local scope decision resolved",
    "candidate POD payload and descriptor contract reviewed",
    "named capability and owner-token lifecycle policy reviewed",
    "ABI layout and SDK consumer tests passing",
    "public docs state exact non-claims and downstream dependency order",
}
REQUIRED_APPROVED_RUNTIME_REPORT_OBSERVED_CASES = [
    "observer_enable",
    "session_start_anchor",
    "session_start_rejected_anchor",
    "session_end_anchor",
]
REQUIRED_APPROVED_RUNTIME_REPORT_CONSUMER_CASES = [
    "malformed_or_unsupported_evidence",
    "stale_after_logout",
]
REQUIRED_APPROVED_RUNTIME_REPORT_TRUE_FLAGS = (
    "provided",
    "accepted_for_contract_review",
    "approved_runtime_evidence_present",
    "runtime_evidence_ready",
)
REQUIRED_APPROVED_RUNTIME_REPORT_FALSE_FLAGS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_sdk_ready",
    "runtime_ready",
    "public_api_ready",
    "public_abi_ready",
    "public_header_allowed",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
)
REQUIRED_STRICT_RUNTIME_LIFECYCLE_ROLES = [
    "session_start",
    "session_start_rejected",
    "session_end",
]
REQUIRED_CONTRACT_GATE_INPUTS = {
    "runtime.lifecycle_evidence": {
        "review_inputs": {"runtime.lifecycle_evidence"},
        "remaining_promotion_inputs": set(),
    },
    "privacy.identifier_redaction": {
        "review_inputs": {"privacy.identifier_redaction"},
        "remaining_promotion_inputs": {
            "privacy.public_identifier_form",
            "privacy.redacted_identifier_fields",
            "privacy.logging_and_storage_policy",
        },
    },
    "lifetime.generation_scope_invalidation": {
        "review_inputs": {"lifetime.generation_scope_invalidation.candidate_policy"},
        "remaining_promotion_inputs": {
            "lifetime.principal_scope",
            "lifetime.invalidation_events",
            "lifetime.reconnect_duplicate_stale_policy",
        },
    },
    "abi.public_pod_contract": {
        "review_inputs": {
            "abi.public_pod_contract.private_layout_candidate",
            "abi.public_pod_contract.public_abi_preflight_candidate",
        },
        "remaining_promotion_inputs": {
            "abi.payload_shape",
            "abi.capability_bits",
            "abi.append_only_layout_tests",
            "abi.layout",
            "sdk.consumer",
        },
    },
    "lifecycle.owner_cleanup": {
        "review_inputs": {"lifecycle.owner_cleanup.owner_token_sdk_consumer_contract"},
        "remaining_promotion_inputs": {
            "abi.owner_token_registration",
            "lifecycle.owner_cleanup.runtime_tests",
        },
    },
    "separation.downstream_surfaces": {
        "review_inputs": {"separation.no_commands_permissions_persistence"},
        "remaining_promotion_inputs": {
            "permissions_admin_contract_blocker",
            "command_chat_response_contract_blocker",
            "commands_replies_contract_blocker",
            "player_lookup_exclusion_review",
            "storage_persistence_exclusion_review",
        },
    },
}
POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS = [
    "evidence.complete_non_protected_pack",
    "evidence.accepted_session_start_anchor",
    "evidence.accepted_session_end_anchor",
]
POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS = [
    key
    for key in REQUIRED_POST_RUNTIME_EVIDENCE_BASE_DECISION_KEYS
    if key not in POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS
]
POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACE_GAPS = sorted(
    REQUIRED_CONTRACT_GATE_INPUTS["separation.downstream_surfaces"]["remaining_promotion_inputs"]
)
POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACES = [
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "player_lookup",
    "storage_persistence",
    "public_sdk",
    "stable_sdk",
    "plugin_hub",
    "plugin_hub_publication",
    "publication",
]
APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_FALSE_ALIAS_KEYS = (
    *REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS,
    *POST_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS,
    "public_sdk_readiness",
    "public_header_ready",
    "public_header_readiness",
    "identity_ready",
    "identity_readiness",
    "player_identity_ready",
    "player_identity_readiness",
    "stable_sdk_ready",
    "stable_sdk_readiness",
    "stable_sdk_claim",
    "stable_sdk_claim_allowed",
    "stable_release_contract_claim_allowed",
    "production_sdk_ready",
    "production_sdk_claim_allowed",
    "complete_sdk_readiness",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "plugin_hub_package_ready",
    "plugin_hub_support_ready",
    "support_tier_ready",
    "support_tier_activation_allowed",
    "package_shape_ready",
    "installed_sdk_package_shape_ready",
    "storage_ready",
    "storage_allowed",
    "storage_api_ready",
    "storage_persistence_ready",
    "storage_persistence_allowed",
    "persistence_ready",
    "persistence_allowed",
    "operator_ingress_ready",
    "identity_lookup_ready",
    "identity_lookup_allowed",
    "principal_lookup_allowed",
    "player_lookup_allowed",
    "command_chat_response_ready",
    "command_chat_response_unlocked",
    "p0_ready",
    "p0_sdk_progress_ready",
    "sdk_p0_ready",
)
APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_ZERO_ALIAS_KEYS = (
    "p0_progress",
    "sdk_p0_progress",
    "p0_sdk_progress",
    "complete_sdk_progress",
    "p0_progress_contribution",
    "sdk_p0_progress_contribution",
    "complete_sdk_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
)
APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_FALSE_ALIAS_KEY_SET = frozenset(
    public_contract_decision_record.normalized_alias(key)
    for key in APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_FALSE_ALIAS_KEYS
)
APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_ZERO_ALIAS_KEY_SET = frozenset(
    public_contract_decision_record.normalized_alias(key)
    for key in APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_ZERO_ALIAS_KEYS
)
REQUIRED_CONTRACT_GATE_INPUT_FALSE_FLAGS = (
    "promotion_blocker_resolved",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "v1_completion_evidence",
)
OFF_HEADER_ABI_REQUIRED_FALSE_FLAGS = (
    "public_header_allowed",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
)
OFF_HEADER_ABI_OPTIONAL_FALSE_OR_EMPTY_KEYS = {
    "public_contract_allowed",
    "public_api_ready",
    "public_abi_ready",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "public_capability_bits",
    "public_capability_bits_now",
    "capability_bits",
    "callback_abi",
    "callback_abi_ready",
    "public_callback_abi",
    "public_callbacks",
    "permissions_admin_unlocked",
    "commands_unlocked",
    "commands_replies_unlocked",
    "sdk_p0_progress",
    "p0_progress",
    "sdk_p0_progress_ready",
    "p0_progress_ready",
    "counts_toward_p0_dependency_chain_claim",
}
REQUIRED_BEFORE_PUBLIC_HEADER = {
    "approved_runtime_principal_lifecycle_evidence_bundle",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "public header guardrail update",
    "public SDK completion checker remains non-counting until downstream P0 surfaces are promoted",
}
REQUIRED_FORBIDDEN_SURFACE = {
    "lookup",
    "resolve",
    "permissions/admin",
    "command response",
    "commands/replies",
    "send-chat identity",
    "storage",
    "persistence",
    "mutation",
    "return override",
    "ResourceHandle",
    "SteamID",
    "EOS ID",
    "UniqueNetId",
    "PlayerDataID",
    "player name",
    "tribe id",
    "network address",
    "UE pointer",
    "FName/GObjects indices",
}
REQUIRED_NON_CLAIMS = {
    "proposal-only header gate review input",
    "does not add public header symbols",
    "does not add capability bits",
    "does not expose callbacks",
    "does not promote obelisk.player_identity.v1",
    "does not make public_header_allowed true",
    "does not make public_abi_ready, public_sdk_ready, runtime_ready, permissions_ready, commands_ready, or v1_completion_evidence true",
    "does not treat reviewed contract aliases, runtime-window planning, copied-log/sidecar/beta/passive/runtime-presence/diagnostic artifacts, package-shape/support-tier artifacts, no-users status, generic approval aliases, status reports, or public ABI/header shortcut claims as header gate readiness",
    "does not expose lookup, persistence, permissions/admin, commands/replies, send-chat identity, mutation, return override, ResourceHandle, platform ids, player names, tribe ids, network addresses, UE pointers, FName/GObjects indices, or raw ProcessEvent params",
}
FALSE_FLAGS = (
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
)
EXPECTED_PUBLIC_CONSTANT_SYMBOLS = [
    symbol
    for group in EXPECTED_PUBLIC_CONSTANTS["ordered_groups"]
    for symbol in [
        *[constant["name"] for constant in group["constants"]],
        group["supported_mask"]["name"],
    ]
]
ALLOWED_NEGATIVE_SURFACE_SYMBOLS = {
    "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_LOOKUP",
    "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_MUTATION",
    "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_RETURN_OVERRIDE",
    "OBELISK_PLAYER_PRINCIPAL_CONTRACT_FLAG_NO_PERMISSIONS_OR_COMMANDS_AUTHORITY",
}
ALLOWED_PROPOSAL_ALIAS_SYMBOLS = ALLOWED_NEGATIVE_SURFACE_SYMBOLS | {
    "OBELISK_PLAYER_PRINCIPAL_STATE_FLAG_UNSUPPORTED_SCOPE",
}
FORBIDDEN_SYMBOL_PATTERNS = (
    re.compile(
        r"Lookup|Resolve|Permission|Authz|AccessControl|ACL|Role|Privilege|Moderation|Moderator|"
        r"Ban|Kick|Admin|Command|Reply|SendChat",
        re.IGNORECASE,
    ),
    re.compile(
        r"Resource(?:Handle|Id|ID|Ref|Reference|Token|Mutation|Mutable|Write|Update)|"
        r"(?:Mutate|Write|Update)Resource|ObjectHandle|Steam|EOS|UniqueNet|"
        r"PlayerDataID|Tribe|IPAddress|Network|Mutation|Mutable|ReturnOverrides?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Resource|Player|Principal|Tribe)Owner|Ownership|Owner(?:Lookup|Resolve|Resolver|Id|ID)",
        re.IGNORECASE,
    ),
    re.compile(r"UObject|FName|GObjects|ProcessEvent|Raw", re.IGNORECASE),
    re.compile(r"Ready|Readiness|SDK|Runtime", re.IGNORECASE),
)
PUBLIC_HEADER_TOKEN_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net|"
    r"player_?(?:handle|data|id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player|"
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
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"excludes?|exclusion|without|until|missing|blocked|blocker|unavailable|required[_ -]?before|"
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
        r"\b(?:OBELISK_API_CAPABILITY_[A-Z0-9_]*"
        r"(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET|AUTH|AUTHZ|ACCESS_CONTROL|ACL|"
        r"ROLE|PRIVILEGE|MODERATION|BAN|KICK|RESOURCE|OBJECT)[A-Z0-9_]*|"
        r"(?:public[-_ ]+)?(?:identity[-_ ]+|principal[-_ ]+)?capability(?:[-_ ]+bits?)?)\b"
        r"[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
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
    "stable_claim_ready": re.compile(
        r"\bstable(?:[-_ ]+(?:sdk|public[-_ ]+sdk|claims?|claim))?\s+"
        r"(?:is\s+|are\s+)?(?:allowed|available|ready|enabled|promoted|complete|supported|claimed)",
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
    "public_contract_ready": re.compile(
        r"\bpublic[-_ ]+contract\s+(?:is\s+)?(?:allowed|ready|available|promoted|enabled|complete)",
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
    "package_shape_readiness": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b"
        r"(?:(?!\bor\b)[^\.;]){0,80}\b(?:allowed|available|complete|enabled|open(?:ed|s)?|promoted|"
        r"ready|supported|unlocked|counts?|claim(?:ed)?)\b|"
        r"\binstalled[-_ ]+sdk\s+(?:is\s+|are\s+|now\s+)?"
        r"(?:allowed|available|complete|enabled|promoted|ready|supported|unlocked)\b|"
        r"\b(?:allowed|available|complete|enabled|open(?:ed|s)?|promoted|ready|supported|"
        r"unlocked|counts?|claim(?:ed)?)\s+"
        r"(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b",
        re.IGNORECASE,
    ),
    "promotion_like_public_contract_evidence": re.compile(
        r"\b(?:reviewed[-_ ]+identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?|"
        r"hash[-_ ]+current[-_ ]+contract[-_ ]+review(?:[-_ ]+only)?)\b[^\.;]{0,100}\b"
        r"(?:evidence|proof|basis|sufficient|certif(?:ies|y|ied)|approv(?:es|ed)|validat(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|green[-_ ]?light(?:s|ed))\b[^\.;]{0,100}\b"
        r"(?:public[-_ ]+contract|public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|public[-_ ]+sdk|"
        r"obelisk\.player_identity\.v1|promotion|readiness|runtime[-_ ]+readiness|v1[-_ ]+completion)",
        re.IGNORECASE,
    ),
    "contract_review_metadata_public_readiness": re.compile(
        r"\b(?:reviewed[-_ ]+hash[-_ ]+current[-_ ]+contract[-_ ]+review[-_ ]+only|"
        r"hash[-_ ]+current[-_ ]+(?:identity[-_ ]+)?(?:public[-_ ]+)?contract[-_ ]+"
        r"(?:decision[-_ ]+)?record|contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record)\b[^\.;]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
    "contract_review_artifact_p0_unlock": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?|"
        r"public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|header[-_ ]+shape)\b"
        r"[^\.;]{0,100}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?)\b[^\.;]{0,100}\b"
        r"(?:sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"dependency[-_ ]+chain|complete[-_ ]+sdk[-_ ]+(?:progress|claim)|downstream[-_ ]+p0)\b",
        re.IGNORECASE,
    ),
    "post_runtime_route_shortcut": re.compile(
        r"\b(?:after[-_ ]+)?(?:(?:accepted|approved)(?:[-_ ]+approved)?[-_ ]+runtime"
        r"(?:[-_ ]+(?:principal[-_ ]+)?lifecycle)?[-_ ]+(?:evidence|bundle)|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|"
        r"approved[-_ ]+runtime[-_ ]+principal[-_ ]+lifecycle[-_ ]+bundle)\b"
        r"[^\.;]{0,120}\b(?:advance[sd]?|route[sd]?|next[-_ ]+blocker|unlocks?|"
        r"opens?|allows?|enables?|marks?|sets?|resolves?|satisf(?:ies|y)|complete[sd]?)\b"
        r"[^\.;]{0,120}\b(?:public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|"
        r"public[-_ ]+sdk|public[-_ ]+readiness|runtime[-_ ]+readiness|"
        r"permissions?[/ _-]?admin|permissions?|admin|command[/ _-]?chat[-_ ]+response|"
        r"command[-_ ]+response|commands?[/ _-]?replies|commands?|complete[-_ ]+sdk|"
        r"plugin[-_ ]+hub|pluginhub|package[-_ ]+shape|support[-_ ]+tier|broadcasts?|"
        r"rcon(?:[-_ ]+commands?)?|v1[-_ ]+completion|sdk[/ _-]*p0|"
        r"p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"downstream[-_ ]+p0|public_header_gate_missing|public_api_gate_missing|"
        r"public_abi_gate_missing|permissions_admin|command_chat_response|commands_replies)\b",
        re.IGNORECASE,
    ),
    "non_counting_artifact_public_readiness_or_p0": re.compile(
        r"\b(?:runtime[-_ ]+window(?:[-_ ]+(?:plan|planning|request|manifest|execution|executor|status|receipt|sidecar))?|"
        r"runtime[-_ ]+window|"
        r"post[-_ ]?runtime[-_ ]?bridge(?:[-_ ]?(?:build|builder|report|artifact|manifest))?|"
        r"bridge[-_ ]?(?:build|builder)[-_ ]?report|shutdown[-_ ]?worker|worker[-_ ]?shutdown|"
        r"shutdown[-_ ]?(?:report|artifact|manifest)|"
        r"post[-_ ]+reboot(?:[-_ ]+(?:passive[-_ ]+monitor|context|snapshot|log|artifact|report))?|"
        r"(?:post[-_ ]+reboot[-_ ]+)?passive[-_ ]+monitor(?:[-_ ]+context)?|"
        r"confirmed[-_ ]+beta[-_ ]+notice(?:[-_ ]+json)?|beta[-_ ]+notice(?:[-_ ]+json)?|"
        r"(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?(?:[-_ ]+(?:total[-_ ]+flag[-_ ]+count|"
        r"component[-_ ]+count|summary|diagnostics?|zero))?|source[-_ ]?overclaim[-_ ]?zero|"
        r"package[-_ ]+shape|installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|support[-_ ]+tier(?:[-_ ]+activation)?|"
        r"no[-_ ]+(?:users?|players?)(?:[-_ ]+(?:status|report|snapshot|artifact))?|zero[-_ ]+players?|empty[-_ ]+server|"
        r"(?:runtime|player)[-_ ]+presence(?:[-_ ]+(?:status|report|snapshot|artifact|monitor|log))?|"
        r"presence[-_ ]+(?:snapshot|monitor|status|report|log)|"
        r"(?:principal|player)[-_ ]+start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:runtime[-_ ]+)?lifecycle[-_ ]+start[-_ ]+end(?:[-_ ]+(?:evidence|artifact|report|manifest|bundle))?|"
        r"start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:start|end)[-_ ]+only(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"next[-_ ]+actions?(?:[-_ ]+(?:plan|status|report|artifact))?|"
        r"(?:route|runtime|evidence|identity|lifecycle|public|sdk)[-_ ]+status"
        r"(?:[-_ ]+(?:report|artifact|manifest|notice|snapshot))?|"
        r"installed[-_ ]+runtime[-_ ]+(?:status[-_ ]+)?checks?|"
        r"(?:broadcast|rcon)[-_ ]+status(?:[-_ ]+(?:checks?|reports?|artifacts?))?|"
        r"copied[-_ ]+log[-_ ]+only(?:[-_ ]+(?:artifact|evidence|manifest|report|shortcut))?)\b"
        r"[^.;\n]{0,120}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?|promotes?|approv(?:es|ed)?|"
        r"validates?|ready|readiness|"
        r"complete|progress)\b[^.;\n]{0,120}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"dependency[-_ ]+chain|complete[-_ ]+sdk|runtime[-_ ]+readiness|v1[-_ ]+completion|"
        r"obelisk\.player_identity\.v1)?",
        re.IGNORECASE,
    ),
    "public_identity_promotion_wording": re.compile(
        r"\b(?:promot(?:e|es|ed|ion)|publish(?:es|ed)?|ship(?:s|ped)?|release(?:s|d)?|"
        r"graduate(?:s|d)?|green[-_ ]?light(?:s|ed)?|clear(?:s|ed)?|unblock(?:s|ed)?|"
        r"certif(?:ies|y|ied)|approv(?:es|ed)|validat(?:es|ed))\b[^\.;]{0,100}\b"
        r"(?:obelisk\.player_identity\.v1|public[-_ ]+identity|public[-_ ]+principal|"
        r"public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|public[-_ ]+sdk|"
        r"public[-_ ]+contract|capability[-_ ]+bits?|callback[-_ ]+abi|runtime[-_ ]+readiness|"
        r"permissions?[/ _-]?admin|command[/ _-]?chat|commands?[/ _-]?replies|v1[-_ ]+completion)",
        re.IGNORECASE,
    ),
    "public_player_header_symbol_available": re.compile(
        r"\b(?:"
        r"Obelisk[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*|"
        r"Register[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_lookup_or_resource_handle_available": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*Resource(?:Handle|Id|ID|Ref|Reference|Token|Mutation|Mutable|Write|Update)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Mutate|Write|Update)Resource[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*Object(?:Handle|Id|ID|Identity|Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:player|identity|principal|resource|object)[-_ ]+"
        r"(?:lookup|resolver|resolve|resource[-_ ]+(?:handle|id|ref|reference|token)|object[-_ ]+handle)s?"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_ownership_or_permissions_available": re.compile(
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
        r"[-_ ]+(?:api|abi|surface|event|callback|lookup)"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_abi_identity_handle_before_resource_handle": re.compile(
        r"\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b[^\.;]{0,120}\b"
        r"(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^\.;]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^\.;]{0,80}\bResourceHandle\b|"
        r"\b(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^\.;]{0,120}\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b"
        r"[^\.;]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^\.;]{0,80}\bResourceHandle\b",
        re.IGNORECASE,
    ),
    "broad_identity_lookup_wording": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:public[-_ ]+)?(?:player|identity|principal)[-_ ]+(?:lookup|resolver|resolve|resolution)"
        r"(?:[-_ ]+(?:api|surface|contract|handle|path|symbol|function|capability|support|route))?"
        r")\b",
        re.IGNORECASE,
    ),
    "mutation_allowed": re.compile(
        r"\bmutation\s+(?:is\s+)?"
        r"(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "return_override_allowed": re.compile(
        r"\breturn[-_ ]?override\s+(?:is\s+)?"
        r"(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "public_mutable_resource_available": re.compile(
        r"\b(?:(?:mutable|mutating|writable|writeable)[-_ ]+(?:identity|principal|player[-_ ]+identity|resource)|"
        r"(?:identity|principal|player[-_ ]+identity|resource)[-_ ]+"
        r"(?:mutation|mutable|write|update)|(?:mutate|write|update)[-_ ]+(?:identity|principal|resource))\b"
        r"[^\.;]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "public_command_or_reply_available": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Command|Commands|Reply|Replies|ChatResponse|SendChat|Broadcast|RCON|Rcon)[A-Za-z0-9_]*|"
        r"(?:commands?|chat[-_ ]+commands?|command[-_ ]+response|chat[-_ ]+response|"
        r"commands?[-_ ]+replies|chat[-_ ]+replies|send[-_ ]+chat|broadcast|rcon(?:[-_ ]+commands?)?)"
        r"[-_ ]+(?:api|abi|surface|event|callback|handler|router|path|symbol|function|support)"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|public|supported|unlocked)",
        re.IGNORECASE,
    ),
    "header_shape_public_readiness_shortcut": re.compile(
        r"\b(?:header[-_ ]+shape|public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?)\b[^\.;]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
    "contract_review_artifact_public_header": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?)\b[^\.;]{0,100}\b"
        r"(?:promotes?|unlocks?|opens?|allows?|enables?|satisf(?:ies|y)|resolves?|counts?)\b"
        r"(?:[^\.;]{0,100}\b(?:public[-_ ]+header|public[-_ ]+abi|public[-_ ]+sdk|"
        r"capability[-_ ]+bits?|callback[-_ ]+abi|obelisk\.player_identity\.v1|"
        r"v1[-_ ]+completion|readiness|promotion))?",
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
}
STALE_PROPOSED_HEADER_SYMBOL_RE = re.compile(
    r"\b(?:"
    r"OBELISK_API_CAPABILITY_(?:IDENTITY|IDENTITIES|PRINCIPAL|PRINCIPALS|"
    r"PLAYER_(?:IDENTITY|IDENTITIES|PRINCIPAL|PRINCIPALS|SESSION|LIFECYCLE|LOGIN|LOGOUT))|"
    r"OBELISK_PLAYER_IDENTITY_[A-Z0-9_]*|"
    r"ObeliskPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"ObeliskPlayer(?:Id|ID|Handle)\b|"
    r"RegisterPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"UnregisterPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"DescribePlayer(?:Identity|Session|Lifecycle)[A-Za-z0-9_]*"
    r")\b"
)
UNEXPECTED_READINESS_ALIAS_KEY_RE = re.compile(
    r"ready|readiness|promot|runtime|sdk|completion|counts?_as|counting|open|opened|"
    r"clear|cleared|resolved|satisfied|public_?marker|runtime_?marker|readiness_?marker|"
    r"(?:accepted|approved)?_?runtime_?(?:principal_?)?lifecycle_?bundle_?(?:route|routes_to|next_blocker)|"
    r"runtime_?lifecycle_?evidence_?(?:route|routes_to|next_blocker)",
    re.IGNORECASE,
)
UNEXPECTED_DOWNSTREAM_ALIAS_KEY_RE = re.compile(
    r"lookup|ownership|resource_?owner|resource_?id|resource_?ref|resource_?reference|"
    r"object_?handle|permissions?|authz?|access_?control|acl|roles?|privileges?|"
    r"moderation|ban|kick|admin|commands?|broadcast|rcon|resource_?handle|resource_?mutation|"
    r"mutation|resource_?mutable|mutable|writable|writeable|resource_?write|write_?resource|"
    r"return_?overrides?|tribe",
    re.IGNORECASE,
)
UNEXPECTED_PUBLIC_ARTIFACT_ALIAS_KEY_RE = re.compile(
    r"(?:public|identity|principal|player_?identity|player_?principal)?_?"
    r"capabilit(?:y|ies)(?:_?(?:bit|bits|name|names|symbol|symbols))?|"
    r"(?:public|identity|principal|player_?identity|player_?principal)_?"
    r"(?:header|symbol|symbols|callback|callbacks|api|abi)_?(?:name|names|symbol|symbols|list)?",
    re.IGNORECASE,
)
UNEXPECTED_API_TABLE_ESCAPE_ALIAS_KEY_RE = re.compile(
    r"(?:copied|captured|cached|stored|saved)_?(?:obelisk_?api|api_?table)|"
    r"(?:obelisk_?api|api_?table)_?(?:copy|copied|capture|captured|cache|cached|escape|hatch)|"
    r"call_?process_?event_?(?:escape|hatch|available|ready|enabled|public|runtime)",
    re.IGNORECASE,
)
UNEXPECTED_CONTRACT_REVIEW_ALIAS_KEY_RE = re.compile(
    r"(?:"
    r"identity.*contract.*decision.*record|"
    r"identity.*public.*contract.*record|"
    r"identity.*public.*contract.*gate.*(?:accepted|reviewed|ready|unlocked|open|opened|resolved|cleared|satisfied|complete)|"
    r"identity.*contract.*gate.*(?:accepted|reviewed|ready|unlocked|open|opened|resolved|cleared|satisfied|complete)|"
    r"reviewed.*identity.*(?:public.*)?contract|"
    r"hash.*current.*identity.*contract|"
    r"public.*header.*gate.*(?:accepted|reviewed|ready|unlocked|open|opened|resolved|cleared|satisfied|complete)|"
    r"header.*gate.*(?:accepted|reviewed|ready|unlocked|open|opened|resolved|cleared|satisfied|complete)"
    r")",
    re.IGNORECASE,
)
CLAIM_ALIAS_VALUE_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
CLAIM_ALIAS_VALUE_KEYS = public_contract_decision_record.CLAIM_ALIAS_KEYS | frozenset(
    {
        public_contract_decision_record.normalized_alias(alias)
        for alias in (
            "stable_ready",
            "stable_claim_allowed",
            "stable_claim_ready",
            "public_header_gate_review_ready",
            "header_gate_review_ready",
            "runtime_bundle_ready",
            "public_or_runtime_accounting_allowed",
            "counts_toward_public_sdk",
            "counts_toward_runtime",
            "counts_toward_v1_completion",
            "counts_toward_p0_dependency_chain_claim",
        )
    }
)
ALLOWED_CLAIM_ALIAS_PATHS = {f"$.{key}" for key in FALSE_FLAGS} | {
    "$.accepted_for_header_gate_review",
    "$.required_before_public_header",
}
ALLOWED_CLAIM_ALIAS_PREFIXES = ("$.source_artifacts.",)
CAPABILITY_DEFINE_RE = re.compile(
    r"^#define\s+(OBELISK_API_CAPABILITY_[A-Z0-9_]+)\s+\(?\s*1ull\s*<<\s*(\d+)\s*\)?",
    re.MULTILINE,
)
API_STRUCT_RE = re.compile(r"typedef\s+struct\s+ObeliskApi\s*\{(?P<body>.*?)\}\s*ObeliskApi\s*;", re.DOTALL)
API_FUNCTION_SLOT_RE = re.compile(r"\(\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)")
API_SCALAR_MEMBER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]+\])?\s*$")
CAPABILITY_BIT_RE = re.compile(r"^1ull\s*<<\s*(\d+)$")
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"//.*")
KNOWN_RUNTIME_EVIDENCE_CONTRACT_REVIEW_MARKER_OVERCLAIM_PATHS = {
    "$.source_summary.modules.player_principal_lifecycle.complete_accepted_lifecycle_role_triplet_present",
}
REVIEWED_DECISION_RECORD_TEMPLATE_OR_CERTIFICATE_RE = re.compile(
    r"(?:reviewed[-_ ]?)?(?:identity[-_ ]?public[-_ ]?contract[-_ ]?)?"
    r"(?:decision[-_ ]?)?record[-_ ]?(?:template|sample|example|draft|skeleton)|"
    r"(?:template|sample|example|draft|skeleton)[-_ ]?"
    r"(?:identity[-_ ]?public[-_ ]?contract[-_ ]?)?(?:decision[-_ ]?)?record|"
    r"(?:permissions?|admin|commands?|command[-_ ]?chat|command[-_ ]?response|chat[-_ ]?response|"
    r"commands?[-_ ]?replies|rcon|broadcast)[-_ ]?"
    r"(?:approval|certificate|ready[-_ ]?certificate|completion[-_ ]?certificate)|"
    r"(?:approval|completion|promotion|permission|permissions|command|commands)[-_ ]?"
    r"certificate",
    re.IGNORECASE,
)
REVIEWED_DECISION_RECORD_TEMPLATE_OR_CERTIFICATE_SKIP_PATH_RE = re.compile(
    r"(?:^|\.)(?:non_claim|non_claims|source_artifact_hash_policy)(?:\.|\[|$)"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=DEFAULT_PROPOSAL)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--public-contract-decisions", type=Path, default=DEFAULT_PUBLIC_CONTRACT_DECISIONS)
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        help=(
            "Approved runtime principal lifecycle evidence manifest required before "
            "a header proposal can be accepted for header-gate review."
        ),
    )
    parser.add_argument(
        "--identity-public-contract-decision-record",
        type=Path,
        default=None,
        help=(
            "Hash-bound reviewed identity public-contract decision record required "
            "before a header proposal can be accepted for header-gate review."
        ),
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--promote", action="store_true", help="Fail closed for promotion mode.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public readiness mode.")
    parser.add_argument("--runtime-readiness", action="store_true", help="Fail closed for runtime readiness mode.")
    return parser.parse_args()


def mode(args: argparse.Namespace) -> str:
    selected = [
        name
        for name, enabled in (
            ("promote", args.promote),
            ("public_readiness", args.public_readiness),
            ("runtime_readiness", args.runtime_readiness),
        )
        if enabled
    ]
    if len(selected) > 1:
        raise SystemExit("--promote, --public-readiness, and --runtime-readiness are mutually exclusive")
    return selected[0] if selected else "consume"


def add(blockers: list[dict[str, Any]], reason: str, path: str, **extra: Any) -> None:
    item = {"reason": reason, "path": path}
    item.update(extra)
    blockers.append(item)


def load_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", file=str(path), error=str(exc))
        return None
    except FileNotFoundError:
        add(blockers, f"{label}_missing", f"$.{label}", file=str(path))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"$.{label}", file=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"$.{label}", file=str(path))
        return None
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_public_contract_decisions_hash_current(
    path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    expected = DEFAULT_PUBLIC_CONTRACT_DECISIONS
    try:
        reject_symlink_component(path, "public_contract_decisions")
        resolved = reject_protected_input_path(path, "public_contract_decisions")
    except SystemExit as exc:
        add(blockers, "public_contract_decisions_path_rejected", "$.public_contract_decisions", file=str(path), error=str(exc))
        return
    if not expected.is_file():
        add(
            blockers,
            "public_contract_decisions_current_source_missing",
            "$.public_contract_decisions",
            expected=str(expected),
        )
        return
    if not resolved.is_file():
        return
    current_hash = sha256_file(expected)
    observed_hash = sha256_file(resolved)
    if observed_hash != current_hash:
        add(
            blockers,
            "public_contract_decisions_source_artifact_hash_mismatch",
            "$.public_contract_decisions",
            expected_path=str(expected),
            observed_path=str(resolved),
            expected_sha256=current_hash,
            observed_sha256=observed_hash,
        )


def as_string_set(value: Any) -> set[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return set(value)


def as_string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


def missing_strings(values: list[str], required: set[str]) -> list[str]:
    return sorted(required - set(values))


def expected_capability_bit_index() -> int:
    match = CAPABILITY_BIT_RE.match(EXPECTED_CAPABILITY["value"])
    if match is None:
        raise AssertionError(f"unexpected expected capability value: {EXPECTED_CAPABILITY['value']}")
    return int(match.group(1))


def strip_c_comments(text: str) -> str:
    return LINE_COMMENT_RE.sub("", BLOCK_COMMENT_RE.sub("", text))


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


def api_member_names(body: str) -> list[str]:
    members = []
    for declaration in strip_c_comments(body).split(";"):
        declaration = declaration.strip()
        if not declaration:
            continue
        function_slot = API_FUNCTION_SLOT_RE.search(declaration)
        if function_slot is not None:
            members.append(function_slot.group(1))
            continue
        scalar_member = API_SCALAR_MEMBER_RE.search(declaration)
        if scalar_member is not None:
            members.append(scalar_member.group(1))
    return members


def public_constant_symbol_names(public_constants: Any) -> list[str]:
    symbols: list[str] = []
    if not isinstance(public_constants, dict):
        return symbols
    groups = public_constants.get("ordered_groups")
    if not isinstance(groups, list):
        return symbols
    for group in groups:
        if not isinstance(group, dict):
            continue
        constants = group.get("constants")
        if isinstance(constants, list):
            for constant in constants:
                if isinstance(constant, dict) and isinstance(constant.get("name"), str):
                    symbols.append(constant["name"])
        supported = group.get("supported_mask")
        if isinstance(supported, dict) and isinstance(supported.get("name"), str):
            symbols.append(supported["name"])
    return symbols


def validate_public_constants(proposed: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    public_constants = proposed.get("public_constants")
    if public_constants != EXPECTED_PUBLIC_CONSTANTS:
        add(
            blockers,
            "public_constants_mismatch",
            "$.proposed_header.public_constants",
            expected=EXPECTED_PUBLIC_CONSTANTS,
            observed=public_constants,
        )
    symbols = public_constant_symbol_names(public_constants)
    duplicates = sorted(symbol for symbol, count in Counter(symbols).items() if count > 1)
    if duplicates:
        add(
            blockers,
            "public_constant_name_duplicate",
            "$.proposed_header.public_constants",
            symbols=duplicates,
        )
    prefix_mismatches = sorted(symbol for symbol in symbols if not symbol.startswith("OBELISK_PLAYER_PRINCIPAL_"))
    if prefix_mismatches:
        add(
            blockers,
            "public_constant_name_prefix_mismatch",
            "$.proposed_header.public_constants",
            symbols=prefix_mismatches,
        )
    source_file = EXPECTED_PUBLIC_CONSTANT_SOURCE.split("#", 1)[0]
    if not (REPO_ROOT / source_file).is_file():
        add(blockers, "public_constants_candidate_source_missing", "$.proposed_header.public_constants", file=source_file)


def alias_path_allowed(path: str) -> bool:
    return path in ALLOWED_CLAIM_ALIAS_PATHS or any(
        path.startswith(prefix) for prefix in ALLOWED_CLAIM_ALIAS_PREFIXES
    )


def validate_no_unexpected_claim_aliases(value: Any, blockers: list[dict[str, Any]], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
            if isinstance(key, str) and not alias_path_allowed(child_path):
                normalized_key = public_contract_decision_record.normalized_alias(key)
                if UNEXPECTED_READINESS_ALIAS_KEY_RE.search(key):
                    add(
                        blockers,
                        "unexpected_readiness_claim_alias",
                        child_path,
                        key=key,
                        observed=child,
                    )
                if UNEXPECTED_DOWNSTREAM_ALIAS_KEY_RE.search(key):
                    add(
                        blockers,
                        "unexpected_downstream_claim_alias",
                        child_path,
                        key=key,
                        observed=child,
                    )
                if UNEXPECTED_CONTRACT_REVIEW_ALIAS_KEY_RE.search(key):
                    add(
                        blockers,
                        "unexpected_contract_review_claim_alias",
                        child_path,
                        key=key,
                        observed=child,
                    )
                if (
                    not child_path.startswith("$.proposed_header.")
                    and (
                        UNEXPECTED_PUBLIC_ARTIFACT_ALIAS_KEY_RE.search(key)
                        or UNEXPECTED_PUBLIC_ARTIFACT_ALIAS_KEY_RE.search(normalized_key)
                    )
                    and not is_false_or_empty(child)
                ):
                    add(
                        blockers,
                        "unexpected_public_artifact_claim_alias",
                        child_path,
                        key=key,
                        observed=child,
                    )
                if (
                    UNEXPECTED_API_TABLE_ESCAPE_ALIAS_KEY_RE.search(key)
                    or UNEXPECTED_API_TABLE_ESCAPE_ALIAS_KEY_RE.search(normalized_key)
                ) and not is_false_or_empty(child):
                    add(
                        blockers,
                        "unexpected_api_table_escape_hatch_claim_alias",
                        child_path,
                        key=key,
                        observed=child,
                    )
            validate_no_unexpected_claim_aliases(child, blockers, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_unexpected_claim_aliases(child, blockers, f"{path}[{index}]")


def validate_no_unexpected_claim_alias_values(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str = "$",
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
            validate_no_unexpected_claim_alias_values(child, blockers, child_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_unexpected_claim_alias_values(child, blockers, f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if ".non_claim" in path or ".non_claims" in path:
        return
    for match in CLAIM_ALIAS_VALUE_TOKEN_RE.finditer(value):
        alias = match.group(0)
        normalized = public_contract_decision_record.normalized_alias(alias)
        if normalized not in CLAIM_ALIAS_VALUE_KEYS:
            continue
        if public_contract_decision_record.string_token_explicitly_false(value, match):
            continue
        if (
            normalized in public_contract_decision_record.BROAD_STRING_ALIASES_REQUIRE_TRUE
            and not public_contract_decision_record.string_token_explicitly_true(value, match)
        ):
            continue
        add(blockers, "unexpected_claim_alias_value", path, alias=alias, observed=value)


def validate_no_split_or_nested_claim_aliases(value: Any, blockers: list[dict[str, Any]]) -> None:
    for claim in public_contract_decision_record.claim_alias_overclaims(value):
        if alias_path_allowed(claim["path"]):
            continue
        observed = claim.get("value")
        if (
            claim.get("term") == "split_readiness_alias"
            and isinstance(observed, dict)
            and observed.get("name") in ALLOWED_PROPOSAL_ALIAS_SYMBOLS
        ):
            continue
        add(
            blockers,
            "unexpected_split_or_nested_claim_alias",
            claim["path"],
            term=claim["term"],
            observed=claim["value"],
        )


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
    for negative in NEGATIVE_CONTEXT_RE.finditer(prefix[-120:]):
        if re.search(
            r"\b(?:resolved|accepted|cleared|satisfied|complete|unblocked)\b",
            prefix[-120:][negative.end() :],
            re.IGNORECASE,
        ):
            continue
        return True
    return bool(
        re.search(
            r"\b(?:forbidden|unavailable|blocked|redacted|cannot|can't|false|exclusion)\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def public_text_overclaims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if ".non_claim" in path or ".non_claims" in path:
        return claims
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
            claims.extend(public_text_overclaims(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(public_text_overclaims(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        if path.endswith(".name") and value in ALLOWED_PROPOSAL_ALIAS_SYMBOLS:
            return claims
        for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                claims.append({"path": path, "term": term, "value": value})
                break
    return claims


def validate_no_public_text_overclaims(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    claims = public_text_overclaims(payload)
    if claims:
        add(blockers, "public_text_or_source_overclaim", "$", claims=claims)


def validate_false_flags(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    for key in FALSE_FLAGS:
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}", observed=payload.get(key))


def validate_struct_fields(
    struct: dict[str, Any],
    expected: dict[str, Any],
    blockers: list[dict[str, Any]],
    label: str,
) -> None:
    if struct.get("size") != expected["size"]:
        add(blockers, "struct_size_mismatch", f"{label}.size", expected=expected["size"], observed=struct.get("size"))
    if struct.get("alignment") != expected["alignment"]:
        add(
            blockers,
            "struct_alignment_mismatch",
            f"{label}.alignment",
            expected=expected["alignment"],
            observed=struct.get("alignment"),
        )
    fields = struct.get("fields")
    if not isinstance(fields, list):
        add(blockers, "struct_fields_missing", f"{label}.fields")
        return
    observed = []
    for field in fields:
        if not isinstance(field, dict):
            add(blockers, "struct_field_not_object", f"{label}.fields")
            continue
        observed.append((field.get("name"), field.get("type"), field.get("offset"), field.get("size")))
    if observed != expected["fields"]:
        add(blockers, "struct_fields_mismatch", f"{label}.fields", expected=expected["fields"], observed=observed)
    if expected["reserved_zero_required"]:
        reserved = next((field for field in fields if isinstance(field, dict) and field.get("name") == "reserved"), {})
        if reserved.get("zero_required") is not True:
            add(blockers, "reserved_zero_required_missing", f"{label}.fields.reserved.zero_required")


def validate_proposed_header(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    proposed = payload.get("proposed_header")
    if not isinstance(proposed, dict):
        add(blockers, "proposed_header_missing", "$.proposed_header")
        return []
    if proposed.get("capability_bit") != EXPECTED_CAPABILITY:
        add(
            blockers,
            "capability_bit_mismatch",
            "$.proposed_header.capability_bit",
            expected=EXPECTED_CAPABILITY,
            observed=proposed.get("capability_bit"),
        )
    if proposed.get("abi_versions") != EXPECTED_ABI_VERSIONS:
        add(
            blockers,
            "abi_versions_mismatch",
            "$.proposed_header.abi_versions",
            expected=EXPECTED_ABI_VERSIONS,
            observed=proposed.get("abi_versions"),
        )
    if proposed.get("callback_typedef") != EXPECTED_CALLBACK:
        add(blockers, "callback_typedef_mismatch", "$.proposed_header.callback_typedef")
    if proposed.get("api_slots") != EXPECTED_API_SLOTS:
        add(blockers, "api_slots_mismatch", "$.proposed_header.api_slots", expected=EXPECTED_API_SLOTS)
    if proposed.get("api_slots_append_after") != EXPECTED_API_APPEND_AFTER:
        add(blockers, "api_slots_append_after_mismatch", "$.proposed_header.api_slots_append_after")
    validate_public_constants(proposed, blockers)

    structs = proposed.get("structs")
    by_name: dict[str, dict[str, Any]] = {}
    if isinstance(structs, list):
        observed_struct_names = [item.get("name") if isinstance(item, dict) else None for item in structs]
        expected_struct_names = list(EXPECTED_STRUCTS)
        if observed_struct_names != expected_struct_names:
            add(
                blockers,
                "struct_order_mismatch",
                "$.proposed_header.structs",
                expected=expected_struct_names,
                observed=observed_struct_names,
            )
        by_name = {
            item.get("name"): item
            for item in structs
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
    else:
        add(blockers, "structs_missing", "$.proposed_header.structs")
    for name, expected in EXPECTED_STRUCTS.items():
        if name not in by_name:
            add(blockers, "struct_missing", "$.proposed_header.structs", struct=name)
            continue
        validate_struct_fields(by_name[name], expected, blockers, f"$.proposed_header.structs.{name}")

    observed_symbols = []
    capability = proposed.get("capability_bit")
    if isinstance(capability, dict) and isinstance(capability.get("name"), str):
        observed_symbols.append(capability["name"])
    abi_versions = proposed.get("abi_versions")
    if isinstance(abi_versions, list):
        observed_symbols.extend(item for item in abi_versions if isinstance(item, str))
    observed_symbols.extend(public_constant_symbol_names(proposed.get("public_constants")))
    observed_symbols.extend(name for name in by_name if isinstance(name, str))
    if isinstance(proposed.get("callback_typedef"), str):
        observed_symbols.append(proposed["callback_typedef"])
    api_slots = proposed.get("api_slots")
    if isinstance(api_slots, list):
        observed_symbols.extend(item for item in api_slots if isinstance(item, str))

    for symbol in observed_symbols:
        if STALE_PROPOSED_HEADER_SYMBOL_RE.search(symbol):
            add(
                blockers,
                "proposed_symbol_uses_stale_player_identity_header_symbol",
                "$.proposed_header",
                symbol=symbol,
            )
        if symbol in ALLOWED_NEGATIVE_SURFACE_SYMBOLS:
            continue
        for pattern in FORBIDDEN_SYMBOL_PATTERNS:
            if pattern.search(symbol):
                add(blockers, "proposed_symbol_uses_forbidden_surface", "$.proposed_header", symbol=symbol)
                break
    return [
        EXPECTED_CAPABILITY["name"],
        *EXPECTED_ABI_VERSIONS,
        *EXPECTED_PUBLIC_CONSTANT_SYMBOLS,
        *EXPECTED_STRUCTS,
        EXPECTED_CALLBACK,
        *EXPECTED_API_SLOTS,
    ]


def validate_public_header_append_anchors(text: str, blockers: list[dict[str, Any]]) -> None:
    capabilities = [(name, int(bit)) for name, bit in CAPABILITY_DEFINE_RE.findall(text)]
    if not capabilities:
        add(blockers, "public_header_capabilities_missing", "$.public_header")
    else:
        capability_names = [name for name, _bit in capabilities]
        capability_bits = {bit: name for name, bit in capabilities}
        expected_bit = expected_capability_bit_index()
        if capability_names[-1] != EXPECTED_CAPABILITY["append_after"]:
            add(
                blockers,
                "capability_append_after_not_latest_public_capability",
                "$.public_header",
                expected=EXPECTED_CAPABILITY["append_after"],
                observed=capability_names[-1],
            )
        if capability_bits.get(expected_bit) is not None:
            add(
                blockers,
                "capability_bit_already_used_in_public_header",
                "$.public_header",
                bit=expected_bit,
                symbol=capability_bits[expected_bit],
            )
        max_public_bit = max(bit for _name, bit in capabilities)
        if expected_bit != max_public_bit + 1:
            add(
                blockers,
                "capability_bit_not_next_after_public_header",
                "$.proposed_header.capability_bit.value",
                expected=f"1ull << {max_public_bit + 1}",
                observed=EXPECTED_CAPABILITY["value"],
            )

    api_match = API_STRUCT_RE.search(text)
    if api_match is None:
        add(blockers, "public_header_obelisk_api_struct_missing", "$.public_header")
        return
    api_body = api_match.group("body")
    api_slots = API_FUNCTION_SLOT_RE.findall(api_body)
    if not api_slots:
        add(blockers, "public_header_api_slots_missing", "$.public_header")
        return
    if api_slots[-1] != EXPECTED_API_APPEND_AFTER:
        add(
            blockers,
            "api_append_after_slot_not_latest_public_api_slot",
            "$.public_header.ObeliskApi",
            expected=EXPECTED_API_APPEND_AFTER,
            observed=api_slots[-1],
        )
    api_members = api_member_names(api_body)
    if not api_members:
        add(blockers, "public_header_api_members_missing", "$.public_header")
    elif api_members[-1] != EXPECTED_API_APPEND_AFTER:
        add(
            blockers,
            "api_append_after_slot_not_latest_public_api_member",
            "$.public_header.ObeliskApi",
            expected=EXPECTED_API_APPEND_AFTER,
            observed=api_members[-1],
        )


def validate_public_header_has_no_adjacent_identity_symbols(text: str, blockers: list[dict[str, Any]]) -> None:
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(strip_c_comments_and_strings(text).splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in HEADER_ALLOWLIST or token in seen or not PUBLIC_HEADER_TOKEN_RE.search(token):
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    if detected:
        add(blockers, "public_header_identity_or_principal_symbols_detected", "$.public_header", detected=detected)


def validate_header_has_no_symbols(header_path: Path, symbols: list[str], blockers: list[dict[str, Any]]) -> None:
    try:
        reject_symlink_component(header_path, "public_header")
        resolved = reject_protected_input_path(header_path, "public_header")
        text = resolved.read_text(encoding="utf-8")
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", "$.public_header", file=str(header_path), error=str(exc))
        return
    except FileNotFoundError:
        add(blockers, "public_header_missing", "$.public_header", file=str(header_path))
        return
    leaked = [symbol for symbol in symbols if re.search(rf"\b{re.escape(symbol)}\b", text)]
    if leaked:
        add(blockers, "public_header_already_exposes_proposed_symbols", "$.public_header", symbols=leaked)
    if EXPECTED_API_APPEND_AFTER not in text:
        add(blockers, "append_after_slot_missing_from_public_header", "$.public_header")
    if EXPECTED_CAPABILITY["append_after"] not in text:
        add(blockers, "append_after_capability_missing_from_public_header", "$.public_header")
    validate_public_header_append_anchors(text, blockers)
    validate_public_header_has_no_adjacent_identity_symbols(text, blockers)


def source_artifact_strings(value: Any, path: str = "$.source_artifacts") -> list[dict[str, str]]:
    strings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                strings.append({"path": f"{path}.{key}", "value": key})
            strings.extend(source_artifact_strings(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            strings.extend(source_artifact_strings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        strings.append({"path": path, "value": value})
    return strings


def validate_source_artifacts(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    source_artifacts = payload.get("source_artifacts")
    if source_artifacts != EXPECTED_SOURCE_ARTIFACTS:
        add(
            blockers,
            "source_artifacts_mismatch",
            "$.source_artifacts",
            expected=EXPECTED_SOURCE_ARTIFACTS,
            observed=source_artifacts,
        )
    allowed_source_values = set(EXPECTED_SOURCE_ARTIFACTS) | set(EXPECTED_SOURCE_ARTIFACTS.values())
    non_counting = [
        item
        for item in source_artifact_strings(source_artifacts)
        if item["value"] not in allowed_source_values
        and (
            NON_COUNTING_SOURCE_ARTIFACT_RE.search(item["value"])
            or PUBLIC_SHORTCUT_SOURCE_ARTIFACT_RE.search(item["value"])
        )
    ]
    if non_counting:
        add(
            blockers,
            "source_artifacts_non_counting_or_public_shortcut_claimed",
            "$.source_artifacts",
            claims=non_counting,
        )
    for label, relative in EXPECTED_SOURCE_ARTIFACTS.items():
        if not (REPO_ROOT / relative).is_file():
            add(blockers, "source_artifact_missing", f"$.source_artifacts.{label}", file=relative)


def require_candidate_strings(
    candidate: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    reason: str,
) -> None:
    path = f"$.public_contract_decisions.{PUBLIC_CONTRACT_CANDIDATE_KEY}.{key}"
    values = as_string_list(candidate.get(key))
    if values is None:
        add(blockers, f"{reason}_not_string_list", path)
        return
    missing = missing_strings(values, required)
    if missing:
        add(blockers, reason, path, missing=missing)


def require_string_list_contains(
    container: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    reason: str,
    path: str,
) -> None:
    values = as_string_list(container.get(key))
    if values is None:
        add(blockers, f"{reason}_not_string_list", path)
        return
    missing = missing_strings(values, required)
    if missing:
        add(blockers, reason, path, missing=missing)


def validate_false_flags_at(
    container: dict[str, Any],
    keys: tuple[str, ...],
    blockers: list[dict[str, Any]],
    reason_prefix: str,
    path_prefix: str,
) -> None:
    for key in keys:
        if container.get(key) is not False:
            add(
                blockers,
                f"{reason_prefix}_{key}_not_false",
                f"{path_prefix}.{key}",
                observed=container.get(key),
            )


def is_false_or_empty(value: Any) -> bool:
    return value is False or value == [] or value == {}


def is_false_or_zero(value: Any) -> bool:
    return value is False or value == 0


def approved_runtime_evidence_consume_only_alias_claims(
    value: Any,
    path: str = "$.approved_runtime_evidence",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    false_claims: list[dict[str, Any]] = []
    zero_claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(key, str):
                normalized = public_contract_decision_record.normalized_alias(key)
                if (
                    normalized in APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_FALSE_ALIAS_KEY_SET
                    and not is_false_or_empty(child)
                ):
                    false_claims.append({"path": child_path, "key": key, "observed": child})
                if (
                    normalized in APPROVED_RUNTIME_EVIDENCE_CONSUME_ONLY_ZERO_ALIAS_KEY_SET
                    and not is_false_or_zero(child)
                ):
                    zero_claims.append({"path": child_path, "key": key, "observed": child})
            child_false_claims, child_zero_claims = approved_runtime_evidence_consume_only_alias_claims(
                child,
                child_path,
            )
            false_claims.extend(child_false_claims)
            zero_claims.extend(child_zero_claims)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_false_claims, child_zero_claims = approved_runtime_evidence_consume_only_alias_claims(
                child,
                f"{path}[{index}]",
            )
            false_claims.extend(child_false_claims)
            zero_claims.extend(child_zero_claims)
    return false_claims, zero_claims


def validate_approved_runtime_report_shape_for_header_gate(
    report: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    path = "$.approved_runtime_evidence"
    fixed_values = {
        "resolved_input": "runtime.lifecycle_evidence",
        "resolved_inputs": ["runtime.lifecycle_evidence"],
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "ready_scope": "runtime_evidence_only",
    }
    for key, expected in fixed_values.items():
        if report.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_report_{key}_mismatch_for_header_gate",
                f"{path}.{key}",
                expected=expected,
                observed=report.get(key),
            )
    for key in REQUIRED_APPROVED_RUNTIME_REPORT_TRUE_FLAGS:
        if report.get(key) is not True:
            add(
                blockers,
                f"approved_runtime_evidence_report_{key}_not_true_for_header_gate",
                f"{path}.{key}",
                observed=report.get(key),
            )
    for key in REQUIRED_APPROVED_RUNTIME_REPORT_FALSE_FLAGS:
        if key in report and report.get(key) is not False:
            add(
                blockers,
                f"approved_runtime_evidence_report_{key}_not_false_for_header_gate",
                f"{path}.{key}",
                observed=report.get(key),
            )
    if report.get("observed_runtime_cases") != REQUIRED_APPROVED_RUNTIME_REPORT_OBSERVED_CASES:
        add(
            blockers,
            "approved_runtime_evidence_report_observed_runtime_cases_mismatch_for_header_gate",
            f"{path}.observed_runtime_cases",
            expected=REQUIRED_APPROVED_RUNTIME_REPORT_OBSERVED_CASES,
            observed=report.get("observed_runtime_cases"),
        )
    for key in ("consumer_cases", "consumer_boundary_assertions"):
        if report.get(key) != REQUIRED_APPROVED_RUNTIME_REPORT_CONSUMER_CASES:
            add(
                blockers,
                f"approved_runtime_evidence_report_{key}_mismatch_for_header_gate",
                f"{path}.{key}",
                expected=REQUIRED_APPROVED_RUNTIME_REPORT_CONSUMER_CASES,
                observed=report.get(key),
            )
    if report.get("blockers") != []:
        add(
            blockers,
            "approved_runtime_evidence_report_blockers_not_empty_for_header_gate",
            f"{path}.blockers",
            observed=report.get("blockers"),
        )
    provenance = report.get("source_provenance_policy")
    if not isinstance(provenance, dict):
        add(
            blockers,
            "approved_runtime_evidence_report_source_provenance_policy_missing_for_header_gate",
            f"{path}.source_provenance_policy",
            observed=provenance,
        )
        return
    provenance_expectations = {
        "non_promotional_sources_rejected": True,
        "accepted_source_kind": public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
        "findings": [],
    }
    for key, expected in provenance_expectations.items():
        if provenance.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_report_source_provenance_policy_{key}_mismatch_for_header_gate",
                f"{path}.source_provenance_policy.{key}",
                expected=expected,
                observed=provenance.get(key),
            )


def validate_strict_approved_runtime_checker_report_shape_for_header_gate(
    report: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    path = "$.approved_runtime_evidence.strict_approved_runtime_checker_report"
    fixed_values = {
        "schema": public_contract_decision_record.STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "input_schema": public_contract_decision_record.APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
        "observed_runtime_cases": REQUIRED_APPROVED_RUNTIME_REPORT_OBSERVED_CASES,
        "required_lifecycle_event_role_triplet": REQUIRED_STRICT_RUNTIME_LIFECYCLE_ROLES,
        "consumer_cases": REQUIRED_APPROVED_RUNTIME_REPORT_CONSUMER_CASES,
        "consumer_boundary_assertions": REQUIRED_APPROVED_RUNTIME_REPORT_CONSUMER_CASES,
    }
    for key, expected in fixed_values.items():
        if report.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_strict_checker_report_{key}_mismatch_for_header_gate",
                f"{path}.{key}",
                expected=expected,
                observed=report.get(key),
            )
    for key in public_contract_decision_record.STRICT_APPROVED_RUNTIME_CHECK_REPORT_TRUE_FLAGS:
        if report.get(key) is not True:
            add(
                blockers,
                f"approved_runtime_evidence_strict_checker_report_{key}_not_true_for_header_gate",
                f"{path}.{key}",
                observed=report.get(key),
            )
    for key in public_contract_decision_record.STRICT_APPROVED_RUNTIME_CHECK_REPORT_FALSE_FLAGS:
        if key in report and report.get(key) is not False:
            add(
                blockers,
                f"approved_runtime_evidence_strict_checker_report_{key}_not_false_for_header_gate",
                f"{path}.{key}",
                observed=report.get(key),
            )
    for key in public_contract_decision_record.STRICT_APPROVED_RUNTIME_CHECK_REPORT_EMPTY_LISTS:
        if report.get(key) != []:
            add(
                blockers,
                f"approved_runtime_evidence_strict_checker_report_{key}_not_empty_for_header_gate",
                f"{path}.{key}",
                observed=report.get(key),
            )
    selection = report.get("strict_lifecycle_triplet_selection")
    if not isinstance(selection, dict):
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_report_lifecycle_triplet_selection_missing_for_header_gate",
            f"{path}.strict_lifecycle_triplet_selection",
            observed=selection,
        )
        return
    selection_expectations = {
        "accepted": True,
        "status": "selected",
        "candidate_count": 1,
        "selected_roles": REQUIRED_STRICT_RUNTIME_LIFECYCLE_ROLES,
        "missing_roles": [],
        "blockers": [],
        "non_counting_context_event_count": 0,
        "non_counting_context_roles": [],
    }
    for key, expected in selection_expectations.items():
        if selection.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_strict_checker_report_lifecycle_triplet_{key}_mismatch_for_header_gate",
                f"{path}.strict_lifecycle_triplet_selection.{key}",
                expected=expected,
                observed=selection.get(key),
            )
    selected_sequences = selection.get("selected_sequences")
    if (
        not isinstance(selected_sequences, list)
        or len(selected_sequences) != len(REQUIRED_STRICT_RUNTIME_LIFECYCLE_ROLES)
        or not all(isinstance(item, int) and item > 0 for item in selected_sequences)
    ):
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_report_lifecycle_triplet_sequences_invalid_for_header_gate",
            f"{path}.strict_lifecycle_triplet_selection.selected_sequences",
            observed=selected_sequences,
        )


def validate_strict_approved_runtime_manifest_for_header_gate(
    path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    try:
        payload = public_contract_gap_report.approved_runtime_evidence.load_json(path)
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_manifest_unreadable_for_header_gate",
            "$.approved_runtime_evidence",
            file=str(path),
            error=str(exc),
        )
        return None
    try:
        try:
            validation = public_contract_gap_report.approved_runtime_evidence.validate_manifest(
                payload,
                check_mode="consume",
                input_path=path,
            )
        except TypeError:
            validation = public_contract_gap_report.approved_runtime_evidence.validate_manifest(
                payload,
                check_mode="consume",
            )
        report = public_contract_gap_report.approved_runtime_evidence.build_report(
            payload,
            validation,
            check_mode="consume",
        )
    except SystemExit as exc:
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_failed_for_header_gate",
            "$.approved_runtime_evidence",
            file=str(path),
            error=str(exc),
        )
        return None
    validation_blockers = getattr(validation, "blockers", None)
    if not isinstance(validation_blockers, list):
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_validation_shape_invalid_for_header_gate",
            "$.approved_runtime_evidence",
            observed=validation_blockers,
        )
    elif validation_blockers:
        add(
            blockers,
            "approved_runtime_evidence_strict_checker_not_accepted_for_header_gate",
            "$.approved_runtime_evidence",
            file=str(path),
            strict_checker_blockers=[blocker.get("reason") for blocker in validation_blockers],
        )
    validate_strict_approved_runtime_checker_report_shape_for_header_gate(report, blockers)
    return report


def validate_approved_runtime_evidence_not_sufficient(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    not_sufficient = decisions.get("approved_runtime_evidence_not_sufficient")
    if not isinstance(not_sufficient, dict):
        add(blockers, "approved_runtime_evidence_not_sufficient_missing", "$.public_contract_decisions.approved_runtime_evidence_not_sufficient")
        return
    if not_sufficient.get("decision") != (
        "Approved runtime principal lifecycle evidence would be necessary evidence, but it is not "
        "sufficient to publish obelisk.player_identity.v1."
    ):
        add(
            blockers,
            "approved_runtime_evidence_not_sufficient_decision_mismatch",
            "$.public_contract_decisions.approved_runtime_evidence_not_sufficient.decision",
            observed=not_sufficient.get("decision"),
        )
    require_string_list_contains(
        not_sufficient,
        "why",
        REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY,
        blockers,
        "approved_runtime_evidence_not_sufficient_why_missing",
        "$.public_contract_decisions.approved_runtime_evidence_not_sufficient.why",
    )
    require_string_list_contains(
        not_sufficient,
        "minimum_additional_gates",
        REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES,
        blockers,
        "approved_runtime_evidence_not_sufficient_minimum_gates_missing",
        "$.public_contract_decisions.approved_runtime_evidence_not_sufficient.minimum_additional_gates",
    )


def validate_post_runtime_evidence_gate(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    gate = decisions.get("post_approved_runtime_evidence_gate")
    path = "$.public_contract_decisions.post_approved_runtime_evidence_gate"
    if not isinstance(gate, dict):
        add(blockers, "post_approved_runtime_evidence_gate_missing", path)
        return
    expected_gate_keys = {
        "id",
        "status",
        "active_after_resolved_input",
        "reported_current_blocker",
        "next_blocker",
        "required_unresolved_decision_keys",
        "auditable_inputs",
        "next_required_artifact",
        "offline_preparation",
        "non_claim",
        *REQUIRED_POST_RUNTIME_EVIDENCE_FALSE_FLAGS,
    }
    unexpected_gate_keys = sorted(set(gate) - expected_gate_keys)
    if unexpected_gate_keys:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_unexpected_route_extras",
            path,
            unexpected=unexpected_gate_keys,
        )
    if gate.get("id") != "identity_public_contract_gate.reviewed_identity_public_contract":
        add(blockers, "post_approved_runtime_evidence_gate_id_mismatch", f"{path}.id", observed=gate.get("id"))
    if gate.get("status") != "blocked/review-required":
        add(blockers, "post_approved_runtime_evidence_gate_status_mismatch", f"{path}.status", observed=gate.get("status"))
    if gate.get("active_after_resolved_input") != "runtime.lifecycle_evidence":
        add(
            blockers,
            "post_approved_runtime_evidence_gate_active_input_mismatch",
            f"{path}.active_after_resolved_input",
            observed=gate.get("active_after_resolved_input"),
        )
    for key in ("reported_current_blocker", "next_blocker"):
        if gate.get(key) != NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE:
            add(
                blockers,
                f"post_approved_runtime_evidence_gate_{key}_mismatch",
                f"{path}.{key}",
                expected=NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
                observed=gate.get(key),
            )
    if as_string_list(gate.get("required_unresolved_decision_keys")) != REQUIRED_POST_RUNTIME_EVIDENCE_DECISION_KEYS:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_required_decision_keys_mismatch",
            f"{path}.required_unresolved_decision_keys",
            expected=REQUIRED_POST_RUNTIME_EVIDENCE_DECISION_KEYS,
            observed=gate.get("required_unresolved_decision_keys"),
        )
    auditable_inputs = as_string_set(gate.get("auditable_inputs"))
    if auditable_inputs is None or auditable_inputs != REQUIRED_POST_RUNTIME_EVIDENCE_AUDIT_INPUTS:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_auditable_inputs_mismatch",
            f"{path}.auditable_inputs",
            expected=sorted(REQUIRED_POST_RUNTIME_EVIDENCE_AUDIT_INPUTS),
            observed=gate.get("auditable_inputs"),
        )
    if gate.get("next_required_artifact") != REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_next_required_artifact_mismatch",
            f"{path}.next_required_artifact",
            expected=REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
            observed=gate.get("next_required_artifact"),
        )
    if gate.get("offline_preparation") != REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_offline_preparation_mismatch",
            f"{path}.offline_preparation",
            expected=REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
            observed=gate.get("offline_preparation"),
        )
    validate_false_flags_at(
        gate,
        REQUIRED_POST_RUNTIME_EVIDENCE_FALSE_FLAGS,
        blockers,
        "post_approved_runtime_evidence_gate",
        path,
    )
    validate_false_flags_at(
        gate,
        tuple(key for key in POST_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS if key in gate),
        blockers,
        "post_approved_runtime_evidence_gate",
        path,
    )
    if gate.get("non_claim") != REQUIRED_POST_RUNTIME_EVIDENCE_NON_CLAIM:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_non_claim_mismatch",
            f"{path}.non_claim",
            observed=gate.get("non_claim"),
        )


def validate_contract_gate_inputs(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    inputs = decisions.get("contract_gate_inputs")
    path = "$.public_contract_decisions.contract_gate_inputs"
    if not isinstance(inputs, list):
        add(blockers, "contract_gate_inputs_not_list", path)
        return
    by_id = {
        item.get("id"): item
        for item in inputs
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if set(by_id) != set(REQUIRED_CONTRACT_GATE_INPUTS):
        add(
            blockers,
            "contract_gate_inputs_mismatch",
            path,
            expected=sorted(REQUIRED_CONTRACT_GATE_INPUTS),
            observed=sorted(str(item) for item in by_id),
        )
    for input_id, expected in REQUIRED_CONTRACT_GATE_INPUTS.items():
        item = by_id.get(input_id)
        if not isinstance(item, dict):
            continue
        item_path = f"{path}[{input_id}]"
        if item.get("status") != "unresolved":
            add(blockers, "contract_gate_input_not_unresolved", f"{item_path}.status", id=input_id, observed=item.get("status"))
        review_inputs = as_string_set(item.get("review_inputs"))
        if review_inputs is None or review_inputs != expected["review_inputs"]:
            add(
                blockers,
                "contract_gate_input_review_inputs_mismatch",
                f"{item_path}.review_inputs",
                id=input_id,
                expected=sorted(expected["review_inputs"]),
                observed=item.get("review_inputs"),
            )
        remaining = as_string_set(item.get("remaining_promotion_inputs"))
        if remaining is None or remaining != expected["remaining_promotion_inputs"]:
            add(
                blockers,
                "contract_gate_input_remaining_promotion_inputs_mismatch",
                f"{item_path}.remaining_promotion_inputs",
                id=input_id,
                expected=sorted(expected["remaining_promotion_inputs"]),
                observed=item.get("remaining_promotion_inputs"),
            )
        validate_false_flags_at(
            item,
            REQUIRED_CONTRACT_GATE_INPUT_FALSE_FLAGS,
            blockers,
            "contract_gate_input_flag",
            item_path,
        )


def validate_off_header_abi_candidate(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    candidate = decisions.get(PUBLIC_CONTRACT_CANDIDATE_KEY)
    path = f"$.public_contract_decisions.{PUBLIC_CONTRACT_CANDIDATE_KEY}"
    if not isinstance(candidate, dict):
        return
    if candidate.get("status") != "proposal_only_not_public":
        add(blockers, "off_header_abi_candidate_status_not_proposal_only", f"{path}.status", observed=candidate.get("status"))
    if candidate.get("candidate_only") is not True:
        add(blockers, "off_header_abi_candidate_only_not_true", f"{path}.candidate_only", observed=candidate.get("candidate_only"))
    validate_false_flags_at(
        candidate,
        OFF_HEADER_ABI_REQUIRED_FALSE_FLAGS,
        blockers,
        "off_header_abi_candidate",
        path,
    )
    for key in sorted(OFF_HEADER_ABI_OPTIONAL_FALSE_OR_EMPTY_KEYS):
        if key in candidate and not is_false_or_empty(candidate[key]):
            add(
                blockers,
                "off_header_abi_candidate_public_or_downstream_claim",
                f"{path}.{key}",
                key=key,
                observed=candidate[key],
            )


def validate_contract_decision_semantics(
    public_contract_decisions: Path,
    blockers: list[dict[str, Any]],
    check_mode: str,
) -> None:
    validate_public_contract_decisions_hash_current(public_contract_decisions, blockers)
    decisions = load_json(public_contract_decisions, blockers, "public_contract_decisions")
    if decisions is None:
        return
    validate_approved_runtime_evidence_not_sufficient(decisions, blockers)
    validate_post_runtime_evidence_gate(decisions, blockers)
    validate_contract_gate_inputs(decisions, blockers)
    validate_off_header_abi_candidate(decisions, blockers)
    post_runtime_gate = decisions.get("post_approved_runtime_evidence_gate")
    if isinstance(post_runtime_gate, dict):
        remaining_decision_keys = as_string_list(post_runtime_gate.get("required_unresolved_decision_keys"))
        header_gate_open = (
            post_runtime_gate.get("next_blocker") == NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW
            and remaining_decision_keys == []
        )
        if not header_gate_open:
            add(
                blockers,
                "public_header_gate_blocked_by_identity_public_contract_gate",
                "$.public_contract_decisions.post_approved_runtime_evidence_gate",
                current_blocker=post_runtime_gate.get("next_blocker"),
                remaining_decision_keys=remaining_decision_keys or [],
            )

    candidate = decisions.get(PUBLIC_CONTRACT_CANDIDATE_KEY)
    if not isinstance(candidate, dict):
        add(
            blockers,
            "public_contract_decisions_candidate_missing",
            f"$.public_contract_decisions.{PUBLIC_CONTRACT_CANDIDATE_KEY}",
        )
        return

    require_candidate_strings(
        candidate,
        "candidate_event_payload_fields_or_equivalent",
        REQUIRED_CONTRACT_EVENT_PAYLOAD_FIELDS,
        blockers,
        "contract_candidate_event_payload_fields_missing",
    )
    require_candidate_strings(
        candidate,
        "candidate_descriptor_fields_or_equivalent",
        REQUIRED_CONTRACT_DESCRIPTOR_FIELDS,
        blockers,
        "contract_candidate_descriptor_fields_missing",
    )
    require_candidate_strings(
        candidate,
        "sequence_policy",
        REQUIRED_EVENT_SEQUENCE_POLICY,
        blockers,
        "contract_candidate_event_sequence_policy_missing",
    )
    require_candidate_strings(
        candidate,
        "server_process_epoch_policy",
        REQUIRED_SERVER_PROCESS_EPOCH_POLICY,
        blockers,
        "contract_candidate_server_process_epoch_policy_missing",
    )
    if check_mode != "consume":
        require_candidate_strings(
            candidate,
            "sequence_policy",
            PROMOTION_EVENT_SEQUENCE_POLICY,
            blockers,
            "promotion_event_sequence_nonzero_contract_missing",
        )
        require_candidate_strings(
            candidate,
            "server_process_epoch_policy",
            PROMOTION_SERVER_PROCESS_EPOCH_POLICY,
            blockers,
            "promotion_server_process_epoch_nonzero_contract_missing",
        )


def is_known_runtime_evidence_contract_review_marker_overclaim(blocker: dict[str, Any]) -> bool:
    if blocker.get("reason") != "approved_runtime_evidence_report_public_readiness_overclaim":
        return False
    overclaims = blocker.get("overclaims")
    if not isinstance(overclaims, list) or not overclaims:
        return False
    return all(
        isinstance(claim, dict)
        and claim.get("term") == "readiness_or_authorization_key"
        and claim.get("path") in KNOWN_RUNTIME_EVIDENCE_CONTRACT_REVIEW_MARKER_OVERCLAIM_PATHS
        for claim in overclaims
    )


def effective_runtime_evidence_blockers(
    runtime_blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    known_marker_overclaim = any(
        is_known_runtime_evidence_contract_review_marker_overclaim(blocker)
        for blocker in runtime_blockers
    )
    effective: list[dict[str, Any]] = []
    for blocker in runtime_blockers:
        if is_known_runtime_evidence_contract_review_marker_overclaim(blocker):
            continue
        if (
            known_marker_overclaim
            and blocker.get("reason") == "approved_runtime_evidence_not_accepted"
            and blocker.get("evidence_blockers") == []
        ):
            continue
        effective.append(blocker)
    return effective


def normalize_runtime_evidence_contract_review_report(
    report: dict[str, Any],
    runtime_blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    effective_blockers = effective_runtime_evidence_blockers(runtime_blockers)
    if effective_blockers:
        return report, effective_blockers
    if report.get("accepted_for_contract_review") is True:
        return report, effective_blockers
    if report.get("runtime_evidence_ready") is not True:
        return report, effective_blockers
    if report.get("next_blocker") != NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE:
        return report, effective_blockers
    resolved_inputs = report.get("resolved_inputs")
    if not isinstance(resolved_inputs, list):
        resolved_inputs = []
    normalized_report = {
        **report,
        "accepted_for_contract_review": True,
        "resolved_input": "runtime.lifecycle_evidence",
        "resolved_inputs": sorted(set(resolved_inputs) | {"runtime.lifecycle_evidence"}),
        "blockers": [],
    }
    return normalized_report, effective_blockers


def validate_approved_runtime_evidence_for_header_gate(
    path: Path | None,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    if path is None:
        add(
            blockers,
            "approved_runtime_evidence_required_before_header_gate",
            "$.approved_runtime_evidence",
        )
        return {
            "provided": False,
            "accepted_for_contract_review": False,
            "resolved_input": None,
            "next_blocker": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "blockers": ["approved_runtime_evidence_required_before_header_gate"],
        }

    runtime_blockers: list[dict[str, Any]] = []
    report = public_contract_gap_report.validate_approved_runtime_evidence(path, runtime_blockers)
    report, effective_runtime_blockers = normalize_runtime_evidence_contract_review_report(
        report,
        runtime_blockers,
    )
    header_gate_runtime_contract_blocker_start = len(blockers)
    validate_approved_runtime_report_shape_for_header_gate(report, blockers)
    validate_strict_approved_runtime_manifest_for_header_gate(path, blockers)
    header_gate_runtime_contract_blockers = blockers[header_gate_runtime_contract_blocker_start:]
    resolved_inputs = report.get("resolved_inputs")
    resolved_inputs_valid = (
        isinstance(resolved_inputs, list)
        and all(isinstance(item, str) for item in resolved_inputs)
        and set(resolved_inputs) == {"runtime.lifecycle_evidence"}
    )
    start_end_runtime_scope = (
        report.get("resolved_input") == "runtime.lifecycle_start_end_evidence"
        or report.get("ready_scope") == "principal_start_end_runtime_evidence_only"
    )
    false_alias_claims, zero_alias_claims = approved_runtime_evidence_consume_only_alias_claims(report)
    if false_alias_claims:
        add(
            blockers,
            "approved_runtime_evidence_consume_only_alias_not_false",
            "$.approved_runtime_evidence",
            claims=false_alias_claims,
        )
    if zero_alias_claims:
        add(
            blockers,
            "approved_runtime_evidence_consume_only_progress_not_zero",
            "$.approved_runtime_evidence",
            claims=zero_alias_claims,
        )
    accepted = (
        report.get("accepted_for_contract_review") is True
        and report.get("resolved_input") == "runtime.lifecycle_evidence"
        and resolved_inputs_valid
        and not start_end_runtime_scope
        and not false_alias_claims
        and not zero_alias_claims
        and not header_gate_runtime_contract_blockers
        and report.get("next_blocker") == NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE
        and report.get("promotion_ready") is False
        and report.get("public_sdk_ready") is False
        and report.get("runtime_ready") is False
        and report.get("public_readiness", False) is False
        and report.get("runtime_readiness", False) is False
        and report.get("stable_ready", False) is False
        and report.get("stable_claim_allowed", False) is False
        and report.get("stable_claim_ready", False) is False
        and report.get("accepted_for_header_gate_review", False) is False
        and report.get("counts_toward_public_sdk", False) is False
        and report.get("counts_toward_runtime", False) is False
        and report.get("counts_toward_v1_completion", False) is False
        and report.get("counts_toward_complete_sdk_claim", False) is False
        and report.get("counts_toward_p0_dependency_chain_claim", False) is False
        and report.get("public_or_runtime_accounting_allowed", False) is False
        and report.get("p0_progress_ready", False) is False
        and report.get("sdk_p0_progress_ready", False) is False
        and report.get("complete_sdk_claim_progress_contribution", 0) == 0
        and report.get("p0_dependency_chain_claim_progress_contribution", 0) == 0
        and report.get("public_header_allowed") is False
        and report.get("public_abi_ready") is False
        and report.get("public_api_ready") is False
        and report.get("lookup_ready") is False
        and report.get("permissions_ready") is False
        and report.get("commands_ready") is False
        and report.get("v1_completion_evidence") is False
    )
    if not accepted:
        report = {**report, "accepted_for_contract_review": False}
    if effective_runtime_blockers or not accepted:
        add(
            blockers,
            "approved_runtime_evidence_not_accepted_for_header_gate",
            "$.approved_runtime_evidence",
            file=str(path),
            accepted=accepted,
            runtime_blockers=[blocker["reason"] for blocker in effective_runtime_blockers],
            header_gate_runtime_contract_blockers=[
                blocker["reason"] for blocker in header_gate_runtime_contract_blockers
            ],
            report_blockers=report.get("blockers", []),
            resolved_inputs=resolved_inputs,
            ready_scope=report.get("ready_scope"),
            source_provenance_policy=report.get("source_provenance_policy", {}),
        )
    if accepted:
        try:
            payload = public_contract_gap_report.approved_runtime_evidence.load_json(path)
        except (OSError, json.JSONDecodeError, SystemExit) as exc:
            add(
                blockers,
                "approved_runtime_evidence_binding_unreadable",
                "$.approved_runtime_evidence",
                file=str(path),
                error=str(exc),
            )
        else:
            report = {
                **report,
                "approved_runtime_evidence_binding": (
                    public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(payload)
                ),
            }
    return report


def reviewed_decision_record_template_or_certificate_claims(
    value: Any,
    path: str = "$.identity_public_contract_decision_record",
) -> list[dict[str, str]]:
    if REVIEWED_DECISION_RECORD_TEMPLATE_OR_CERTIFICATE_SKIP_PATH_RE.search(path):
        return []
    claims: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if isinstance(key, str) and REVIEWED_DECISION_RECORD_TEMPLATE_OR_CERTIFICATE_RE.search(key):
                claims.append({"path": child_path, "value": key})
            claims.extend(reviewed_decision_record_template_or_certificate_claims(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            claims.extend(
                reviewed_decision_record_template_or_certificate_claims(
                    child,
                    f"{path}[{index}]",
                )
            )
    elif isinstance(value, str) and REVIEWED_DECISION_RECORD_TEMPLATE_OR_CERTIFICATE_RE.search(value):
        claims.append({"path": path, "value": value})
    return claims


def validate_reviewed_decision_record_header_gate_artifact_claims(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    claims = reviewed_decision_record_template_or_certificate_claims(payload)
    if claims:
        add(
            blockers,
            "reviewed_identity_public_contract_decision_record_template_or_certificate_artifact_claimed",
            "$.identity_public_contract_decision_record",
            claims=claims,
        )


def validate_reviewed_identity_contract_record_for_header_gate(
    path: Path | None,
    blockers: list[dict[str, Any]],
    *,
    runtime_evidence_accepted: bool,
) -> dict[str, Any]:
    if not runtime_evidence_accepted:
        return {
            "provided": path is not None,
            "pending_approved_runtime_evidence": True,
            "accepted_for_contract_review": False,
            "record_valid": False,
            "record_valid_scope": None,
            "ready_scope": None,
            "contract_review_only": False,
            "hash_bound_to_current_source_artifacts": False,
            "reviewed_hash_current_contract_review_only": False,
            "approved_runtime_evidence_binding_required": True,
            "runtime_evidence_binding_valid": False,
            "approved_runtime_evidence_binding": None,
            "resolved_decision_keys": [],
            "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "source_artifact_freshness": {},
            "checkable_next_step": public_contract_decision_record.REQUIRED_NEXT_STEP_CHECK,
            "blockers": [],
        }
    if path is None:
        return {
            "provided": False,
            "accepted_for_contract_review": False,
            "record_valid": False,
            "record_valid_scope": None,
            "ready_scope": None,
            "contract_review_only": False,
            "hash_bound_to_current_source_artifacts": False,
            "reviewed_hash_current_contract_review_only": False,
            "approved_runtime_evidence_binding_required": True,
            "runtime_evidence_binding_valid": False,
            "approved_runtime_evidence_binding": None,
            "resolved_decision_keys": [],
            "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "source_artifact_freshness": {},
            "checkable_next_step": public_contract_decision_record.REQUIRED_NEXT_STEP_CHECK,
            "blockers": [],
        }
    record_blockers: list[dict[str, Any]] = []
    payload = public_contract_decision_record.load_record(path, record_blockers)
    if payload is not None:
        validate_reviewed_decision_record_header_gate_artifact_claims(payload, record_blockers)
        record_blockers.extend(
            public_contract_decision_record.validate_record(payload, check_mode="consume")
        )
    report = public_contract_decision_record.build_report(
        payload,
        record_blockers,
        check_mode="consume",
    )
    accepted = (
        report.get("record_valid") is True
        and report.get("record_valid_scope") == public_contract_decision_record.RECORD_VALID_SCOPE
        and report.get("ready_scope") == public_contract_decision_record.READY_SCOPE
        and report.get("contract_review_only") is True
        and report.get("accepted_for_contract_review") is True
        and report.get("strict_approved_runtime_checker_contract_report_valid") is True
        and isinstance(report.get("strict_approved_runtime_checker_contract_report"), dict)
        and report.get("approved_runtime_evidence_manifest_ref_valid") is True
        and isinstance(report.get("approved_runtime_evidence_manifest_ref"), dict)
        and report.get("hash_bound_to_current_source_artifacts") is True
        and report.get("reviewed_hash_current_contract_review_only") is True
        and report.get("approved_runtime_evidence_binding_required") is True
        and report.get("approved_runtime_evidence_manifest_ref_required") is True
        and report.get("runtime_evidence_binding_valid") is True
        and isinstance(report.get("approved_runtime_evidence_binding"), dict)
        and report.get("accepted_runtime_lifecycle_evidence_advances_to")
        == public_contract_decision_record.REVIEW_ROUTE
        and report.get("current_route") == public_contract_decision_record.CURRENT_ROUTE
        and report.get("current_blocker") == public_contract_decision_record.CURRENT_ROUTE
        and report.get("resolved_decision_keys") == REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS
        and report.get("post_runtime_evidence_next_blocker")
        == NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE
        and report.get("promotion_ready") is False
        and report.get("public_header_allowed") is False
        and report.get("public_abi_ready") is False
        and report.get("public_api_ready") is False
        and report.get("public_sdk_ready") is False
        and report.get("runtime_ready") is False
        and report.get("public_readiness", False) is False
        and report.get("runtime_readiness", False) is False
        and report.get("stable_ready", False) is False
        and report.get("stable_claim_allowed", False) is False
        and report.get("stable_claim_ready", False) is False
        and report.get("counts_toward_public_sdk", False) is False
        and report.get("counts_toward_runtime", False) is False
        and report.get("counts_toward_v1_completion", False) is False
        and report.get("counts_toward_complete_sdk_claim", False) is False
        and report.get("counts_toward_p0_dependency_chain_claim", False) is False
        and report.get("public_or_runtime_accounting_allowed", False) is False
        and report.get("p0_progress_ready", False) is False
        and report.get("sdk_p0_progress_ready", False) is False
        and report.get("complete_sdk_claim_progress_contribution", 0) == 0
        and report.get("p0_dependency_chain_claim_progress_contribution", 0) == 0
        and report.get("lookup_ready") is False
        and report.get("permissions_ready") is False
        and report.get("commands_ready") is False
        and report.get("v1_completion_evidence") is False
    )
    if record_blockers or not accepted:
        add(
            blockers,
            "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
            "$.identity_public_contract_decision_record",
            file=str(path),
            accepted=accepted,
            record_blockers=report.get("blockers", []),
            source_artifact_freshness=report.get("source_artifact_freshness", {}),
        )
    return report


def validate_reviewed_record_bound_to_accepted_runtime_evidence(
    runtime_report: dict[str, Any],
    decision_record_report: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    if runtime_report.get("accepted_for_contract_review") is not True:
        return
    expected = runtime_report.get("approved_runtime_evidence_binding")
    observed = decision_record_report.get("approved_runtime_evidence_binding")
    if not isinstance(expected, dict):
        add(
            blockers,
            "approved_runtime_evidence_binding_missing_from_accepted_runtime_evidence",
            "$.approved_runtime_evidence",
        )
        return
    if not isinstance(observed, dict):
        return
    expected_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
        expected,
        "$.approved_runtime_evidence.approved_runtime_evidence_binding",
    )
    observed_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
        observed,
        "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
    )
    for shortcut_type, claims in expected_shortcuts.items():
        if claims:
            reason_suffix = "public_header_api_abi" if shortcut_type == "public_shortcuts" else shortcut_type
            add(
                blockers,
                f"approved_runtime_evidence_binding_{reason_suffix}_shortcut_not_accepted",
                "$.approved_runtime_evidence.approved_runtime_evidence_binding",
                claims=claims,
            )
    for shortcut_type, claims in observed_shortcuts.items():
        if claims:
            reason_suffix = "public_header_api_abi" if shortcut_type == "public_shortcuts" else shortcut_type
            add(
                blockers,
                f"reviewed_identity_public_contract_decision_record_approved_runtime_evidence_binding_{reason_suffix}_shortcut_not_accepted",
                "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
                claims=claims,
            )
    if any(expected_shortcuts.values()) or any(observed_shortcuts.values()):
        return
    if observed != expected:
        add(
            blockers,
            "reviewed_identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
            "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
            expected=expected,
            observed=observed,
        )


def validate_manifest(
    payload: dict[str, Any],
    public_header: Path,
    public_contract_decisions: Path,
    approved_runtime_evidence: Path | None,
    identity_public_contract_decision_record: Path,
    blockers: list[dict[str, Any]],
    check_mode: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", expected=SCHEMA, observed=payload.get("schema"))
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", expected=SURFACE, observed=payload.get("surface"))
    if payload.get("artifact_status") != "proposal_only":
        add(blockers, "artifact_status_mismatch", "$.artifact_status")
    if payload.get("visibility") != "header_gate_planning_contract":
        add(blockers, "visibility_mismatch", "$.visibility")
    if payload.get("active_after_blocker") != "public_header_gate_missing":
        add(blockers, "active_after_blocker_mismatch", "$.active_after_blocker")
    if payload.get("candidate_only") is not True:
        add(blockers, "candidate_only_not_true", "$.candidate_only")
    if payload.get("accepted_for_header_gate_review") is not True:
        add(blockers, "accepted_for_header_gate_review_not_true", "$.accepted_for_header_gate_review")
    validate_no_unexpected_claim_aliases(payload, blockers)
    validate_no_unexpected_claim_alias_values(payload, blockers)
    validate_no_split_or_nested_claim_aliases(payload, blockers)
    validate_no_public_text_overclaims(payload, blockers)
    validate_false_flags(payload, blockers)
    validate_source_artifacts(payload, blockers)
    required_before = as_string_set(payload.get("required_before_public_header"))
    if required_before is None or not REQUIRED_BEFORE_PUBLIC_HEADER.issubset(required_before):
        add(blockers, "required_before_public_header_missing", "$.required_before_public_header")
    forbidden = as_string_set(payload.get("forbidden_public_surface"))
    if forbidden is None or not REQUIRED_FORBIDDEN_SURFACE.issubset(forbidden):
        add(blockers, "forbidden_public_surface_missing", "$.forbidden_public_surface")
    non_claims = as_string_set(payload.get("non_claims"))
    if non_claims is None or not REQUIRED_NON_CLAIMS.issubset(non_claims):
        add(blockers, "non_claims_missing", "$.non_claims")
    symbols = validate_proposed_header(payload, blockers)
    validate_contract_decision_semantics(public_contract_decisions, blockers, check_mode)
    runtime_report = validate_approved_runtime_evidence_for_header_gate(approved_runtime_evidence, blockers)
    decision_record_report = validate_reviewed_identity_contract_record_for_header_gate(
        identity_public_contract_decision_record,
        blockers,
        runtime_evidence_accepted=runtime_report.get("accepted_for_contract_review") is True,
    )
    validate_reviewed_record_bound_to_accepted_runtime_evidence(runtime_report, decision_record_report, blockers)
    validate_header_has_no_symbols(public_header, symbols, blockers)
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_runtime_bundle_and_header_promotion", "$.accepted_for_header_gate_review")
    return runtime_report, decision_record_report


def post_runtime_public_identity_gap_summary(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    current_blocker: str,
    next_blocker: str,
) -> dict[str, Any]:
    missing_review_keys = (
        []
        if identity_contract_decision_accepted or not runtime_evidence_accepted
        else list(REQUIRED_POST_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS)
    )
    remaining_header_keys = (
        list(POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS)
        if runtime_evidence_accepted
        else []
    )
    remaining_identity_keys = missing_review_keys + remaining_header_keys
    return {
        "active": runtime_evidence_accepted,
        "current_blocker": current_blocker,
        "next_blocker": next_blocker,
        "only_valid_post_runtime_route": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "candidate_preflight_review_aliases_count": False,
        "approved_runtime_bundle_consumed": runtime_evidence_accepted,
        "approved_runtime_evidence_scope": "consume_only_contract_review_input",
        "approved_runtime_resolved_input": "runtime.lifecycle_evidence" if runtime_evidence_accepted else None,
        "runtime_bundle_consumed_decision_keys": (
            list(POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS)
            if runtime_evidence_accepted
            else []
        ),
        "missing_identity_contract_review_decision_keys": missing_review_keys,
        "remaining_public_header_decision_keys": remaining_header_keys,
        "smallest_remaining_public_identity_decision_keys": remaining_identity_keys,
        "deferred_downstream_surface_gaps": POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACE_GAPS,
        "downstream_surfaces_deferred_until_identity_promotion": POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACES,
        "permissions_admin_opened": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "lookup_ready": False,
        "storage_persistence_ready": False,
        "public_sdk_ready": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_readiness": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_ready": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "A checker-accepted approved runtime bundle only consumes the runtime lifecycle evidence "
            "input and routes to identity_public_contract_gate_missing; the remaining keys are public "
            "identity contract/header review gaps and do not open permissions/admin, commands, lookup, "
            "storage, public SDK, stable SDK, Plugin Hub, publication, SDK/P0 progress, runtime readiness, "
            "or v1 completion."
        ),
    }


def public_header_fail_closed_path(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    current_blocker: str,
) -> dict[str, Any]:
    if not runtime_evidence_accepted:
        status = "blocked_until_strict_approved_runtime_evidence"
        next_fail_closed_blocker = "approved_runtime_evidence_missing"
        next_required_artifact: dict[str, Any] | None = None
    elif not identity_contract_decision_accepted:
        status = "blocked_until_reviewed_identity_public_contract_decision_record"
        next_fail_closed_blocker = NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE
        next_required_artifact = REQUIRED_POST_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT
    else:
        status = "candidate_public_header_gate_review_available_fail_closed"
        next_fail_closed_blocker = NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW
        next_required_artifact = REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT

    return {
        "active_after_strict_approved_runtime_evidence": runtime_evidence_accepted,
        "active_after_accepted_reviewed_identity_contract": identity_contract_decision_accepted,
        "status": status,
        "current_blocker": current_blocker,
        "next_fail_closed_blocker": next_fail_closed_blocker,
        "next_required_artifact": next_required_artifact,
        "required_sequence": [
            {
                "id": "approved_runtime_principal_lifecycle_evidence_bundle",
                "status": "accepted" if runtime_evidence_accepted else "missing_or_not_accepted",
                "resolved_input": "runtime.lifecycle_evidence" if runtime_evidence_accepted else None,
                "strict_checker_report_required": True,
            },
            {
                "id": "reviewed_identity_public_contract_decision_record",
                "status": (
                    "accepted_for_contract_review"
                    if identity_contract_decision_accepted
                    else "missing_or_not_accepted"
                    if runtime_evidence_accepted
                    else "blocked_until_strict_runtime_evidence"
                ),
                "must_bind_to_approved_runtime_evidence": True,
                "must_bind_current_source_artifacts": True,
                "accepted_shortcut_aliases": False,
            },
            {
                "id": "player_identity_public_header_gate_proposal",
                "status": (
                    "candidate_only_fail_closed_next_artifact"
                    if identity_contract_decision_accepted
                    else "blocked_until_reviewed_identity_contract"
                ),
                "checker": "scripts/check_player_identity_public_header_gate.py",
                "accepted_for_header_gate_review": False,
                "public_header_allowed": False,
            },
        ],
        "shortcut_aliases_allowed": False,
        "candidate_aliases_count": False,
        "accepted_decision_record_opens_public_header_gate": False,
        "public_header_readiness_from_decision_record": False,
        "public_header_gate_ready": False,
        "public_header_gate_unlocked": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "must_remain_false": list(REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_FALSE_FLAGS),
        "non_claim": REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_NON_CLAIM,
    }


def build_report(
    payload: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
    check_mode: str,
    approved_runtime_evidence_report: dict[str, Any] | None = None,
    identity_contract_decision_record_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    accepted = payload is not None and not blockers
    approved_runtime_evidence_report = approved_runtime_evidence_report or {}
    identity_contract_decision_record_report = identity_contract_decision_record_report or {}
    blocker_reasons = {blocker["reason"] for blocker in blockers}
    identity_contract_gate_blockers = {
        "public_header_gate_blocked_by_identity_public_contract_gate",
        "reviewed_identity_public_contract_decision_record_not_accepted_for_header_gate",
        "reviewed_identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
        "approved_runtime_evidence_binding_missing_from_accepted_runtime_evidence",
    }
    if accepted:
        next_blocker = "runtime_bundle_and_public_header_promotion_missing"
    elif blocker_reasons and blocker_reasons <= identity_contract_gate_blockers:
        next_blocker = NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE
    elif blocker_reasons and blocker_reasons <= {
        "public_header_gate_blocked_by_identity_public_contract_gate",
        "approved_runtime_evidence_required_before_header_gate",
    }:
        next_blocker = "approved_runtime_evidence_required_before_header_gate"
    else:
        next_blocker = "public_header_gate_proposal_invalid"
    runtime_binding = approved_runtime_evidence_report.get("approved_runtime_evidence_binding")
    decision_record_binding = identity_contract_decision_record_report.get("approved_runtime_evidence_binding")
    runtime_binding_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
        runtime_binding,
        "$.approved_runtime_evidence.approved_runtime_evidence_binding",
    )
    decision_record_binding_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
        decision_record_binding,
        "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
    )
    runtime_binding_match = (
        approved_runtime_evidence_report.get("accepted_for_contract_review") is True
        and identity_contract_decision_record_report.get("accepted_for_contract_review") is True
        and isinstance(runtime_binding, dict)
        and decision_record_binding == runtime_binding
        and not any(runtime_binding_shortcuts.values())
        and not any(decision_record_binding_shortcuts.values())
    )
    runtime_evidence_accepted = approved_runtime_evidence_report.get("accepted_for_contract_review") is True
    identity_contract_decision_accepted = (
        identity_contract_decision_record_report.get("accepted_for_contract_review") is True
        and runtime_binding_match
    )
    post_runtime_gap_summary = post_runtime_public_identity_gap_summary(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=next_blocker,
        next_blocker=NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE if runtime_evidence_accepted else next_blocker,
    )
    header_fail_closed_path = public_header_fail_closed_path(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=next_blocker,
    )
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema") if isinstance(payload, dict) else None,
        "surface": SURFACE,
        "mode": check_mode,
        "ready": False,
        "ready_scope": "proposal_only_not_public",
        "planning_only": True,
        "header_gate_review_ready": accepted,
        "accepted_for_header_gate_review": accepted,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_or_runtime_accounting_allowed": False,
        "v1_completion_evidence": False,
        "accepted_runtime_evidence_route_only": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "accepted_for_identity_contract_gate_review": False,
        "accepted_for_identity_public_contract_gate_review": False,
        "accepted_for_public_identity_contract_gate_review": False,
        "identity_public_contract_gate_next_step": identity_contract_decision_record_report.get(
            "checkable_next_step",
            public_contract_decision_record.REQUIRED_NEXT_STEP_CHECK,
        ),
        "post_runtime_identity_contract_gate": {
            "active_after_approved_runtime_evidence": runtime_evidence_accepted,
            "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "post_runtime_identity_contract_gate_missing": True,
            "public_header_fail_closed_path": header_fail_closed_path,
            "runtime_evidence_contract_review_currentness": {
                **public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
                "runtime_evidence_accepted": runtime_evidence_accepted,
                "reviewed_decision_record_accepted": identity_contract_decision_accepted,
                "current_blocker": next_blocker,
                "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
                "candidate_preflight_review_aliases_count": False,
                "permissions_admin_unlocked_from_runtime_evidence": False,
                "command_surface_unlocked_from_runtime_evidence": False,
            },
            "approved_runtime_evidence_scope": "consume_only_contract_review_input",
            "offline_preparation": REQUIRED_POST_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
            "runtime_bundle_consumed_decision_keys": post_runtime_gap_summary[
                "runtime_bundle_consumed_decision_keys"
            ],
            "missing_identity_contract_review_decision_keys": post_runtime_gap_summary[
                "missing_identity_contract_review_decision_keys"
            ],
            "remaining_public_header_decision_keys": post_runtime_gap_summary[
                "remaining_public_header_decision_keys"
            ],
            "smallest_remaining_public_identity_decision_keys": post_runtime_gap_summary[
                "smallest_remaining_public_identity_decision_keys"
            ],
            "requires_reviewed_decision_record": True,
            "requires_binding_to_accepted_runtime_evidence": True,
            "record_bound_to_accepted_runtime_evidence": runtime_binding_match,
            "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
            "accepted_for_identity_contract_gate_review": False,
            "accepted_for_identity_public_contract_gate_review": False,
            "identity_contract_gate_ready": False,
            "identity_contract_gate_unlocked": False,
            "identity_public_contract_gate_ready": False,
            "identity_public_contract_gate_unlocked": False,
            "identity_public_contract_gate_review_ready": False,
            "public_sdk_ready": False,
            "public_sdk_v1_completion_ready": False,
            "complete_sdk_ready": False,
            "counts_toward_public_sdk": False,
            "counts_toward_complete_sdk_claim": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "runtime_ready": False,
            "lookup_ready": False,
            "storage_persistence_ready": False,
            "permissions_admin_ready": False,
            "permissions_admin_public_ready": False,
            "permissions_admin_unlocked": False,
            "command_response_ready": False,
            "command_chat_response_ready": False,
            "commands_replies_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "sdk_p0_progress_ready": False,
            "p0_progress_ready": False,
        },
        "post_runtime_public_identity_gap_summary": post_runtime_gap_summary,
        "post_runtime_public_header_fail_closed_path": header_fail_closed_path,
        "public_header_gate_missing": {
            "active": next_blocker == NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW,
            "fail_closed_path": header_fail_closed_path,
            "next_required_artifact": REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
            "public_header_gate_ready": False,
            "public_header_gate_unlocked": False,
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "complete_sdk_ready": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "non_claim": REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_NON_CLAIM,
        },
        "runtime_evidence_contract_review_currentness": {
            **public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            "runtime_evidence_accepted": runtime_evidence_accepted,
            "reviewed_decision_record_accepted": identity_contract_decision_accepted,
            "current_blocker": next_blocker,
            "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "candidate_preflight_review_aliases_count": False,
            "permissions_admin_unlocked_from_runtime_evidence": False,
            "command_surface_unlocked_from_runtime_evidence": False,
        },
        "off_header_abi_proposal_counts": False,
        "public_capability_bits_now": [],
        "public_callback_abi_ready": False,
        "permissions_admin_unlocked": False,
        "commands_replies_unlocked": False,
        "sdk_p0_progress": False,
        "p0_progress": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "proposed_symbols": [
            EXPECTED_CAPABILITY["name"],
            *EXPECTED_ABI_VERSIONS,
            *EXPECTED_PUBLIC_CONSTANT_SYMBOLS,
            *EXPECTED_STRUCTS,
            EXPECTED_CALLBACK,
            *EXPECTED_API_SLOTS,
        ],
        "next_required_inputs": sorted(REQUIRED_BEFORE_PUBLIC_HEADER),
        "next_blocker": next_blocker,
        "approved_runtime_evidence": {
            "provided": approved_runtime_evidence_report.get("provided") is True,
            "accepted_for_contract_review": approved_runtime_evidence_report.get("accepted_for_contract_review") is True,
            "accepted_for_header_gate_review": False,
            "resolved_input": approved_runtime_evidence_report.get("resolved_input"),
            "next_blocker": approved_runtime_evidence_report.get("next_blocker"),
            "approved_runtime_evidence_binding": runtime_binding,
            "promotion_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "blockers": approved_runtime_evidence_report.get("blockers", []),
        },
        "identity_public_contract_decision_record": {
            "accepted_for_contract_review": (
                identity_contract_decision_record_report.get("accepted_for_contract_review") is True
                and runtime_binding_match
            ),
            "accepted_for_header_gate_review": False,
            "record_valid": identity_contract_decision_record_report.get("record_valid") is True,
            "record_valid_scope": identity_contract_decision_record_report.get("record_valid_scope"),
            "contract_review_only": identity_contract_decision_record_report.get("contract_review_only") is True,
            "hash_bound_to_current_source_artifacts": (
                identity_contract_decision_record_report.get("hash_bound_to_current_source_artifacts") is True
            ),
            "reviewed_hash_current_contract_review_only": (
                identity_contract_decision_record_report.get("reviewed_hash_current_contract_review_only") is True
            ),
            "approved_runtime_evidence_binding_required": (
                identity_contract_decision_record_report.get("approved_runtime_evidence_binding_required") is True
            ),
            "runtime_evidence_binding_valid": (
                identity_contract_decision_record_report.get("runtime_evidence_binding_valid") is True
            ),
            "bound_to_accepted_runtime_evidence": runtime_binding_match,
            "approved_runtime_evidence_binding": decision_record_binding,
            "source_artifact_freshness": identity_contract_decision_record_report.get(
                "source_artifact_freshness",
                {},
            ),
            "runtime_evidence_contract_review_currentness": identity_contract_decision_record_report.get(
                "runtime_evidence_contract_review_currentness",
                public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            ),
            "checkable_next_step": identity_contract_decision_record_report.get(
                "checkable_next_step",
                public_contract_decision_record.REQUIRED_NEXT_STEP_CHECK,
            ),
            "resolved_decision_keys": identity_contract_decision_record_report.get("resolved_decision_keys", []),
            "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "accepted_for_identity_contract_gate_review": False,
            "accepted_for_identity_public_contract_gate_review": False,
            "accepted_for_public_identity_contract_gate_review": False,
            "post_runtime_identity_contract_gate_missing": True,
            "identity_contract_gate_ready": False,
            "identity_contract_gate_unlocked": False,
            "identity_public_contract_gate_ready": False,
            "identity_public_contract_gate_unlocked": False,
            "identity_public_contract_gate_review_ready": False,
            "promotion_ready": False,
            "public_header_gate_ready": False,
            "public_header_gate_unlocked": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "public_or_runtime_accounting_allowed": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "blockers": identity_contract_decision_record_report.get("blockers", []),
            "blocker_details": identity_contract_decision_record_report.get("blocker_details", []),
        },
        "non_claims": sorted(REQUIRED_NON_CLAIMS),
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    blockers: list[dict[str, Any]] = []
    runtime_report: dict[str, Any] = {}
    decision_record_report: dict[str, Any] = {}
    proposal = load_json(args.proposal, blockers, "proposal")
    if proposal is not None:
        runtime_report, decision_record_report = validate_manifest(
            proposal,
            args.public_header,
            args.public_contract_decisions,
            args.approved_runtime_evidence,
            args.identity_public_contract_decision_record,
            blockers,
            check_mode,
        )
    report = build_report(proposal, blockers, check_mode, runtime_report, decision_record_report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['path']}", file=sys.stderr)
    else:
        print("player identity public header gate proposal: ok")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
