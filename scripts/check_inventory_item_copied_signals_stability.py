#!/usr/bin/env python3
"""Offline stability guardrail for inventory/item copied public signals."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from plan_obelisk_multi_surface_beta_capture import (  # noqa: E402
    CURRENT_ROUTE_BLOCKER,
    REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
)
from reflection_target_sets import (  # noqa: E402
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    NON_AUTHORIZING_READY_SCOPE,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component  # noqa: E402

DEFAULT_DECISIONS = REPO_ROOT / "docs" / "inventory_item_copied_signals_public_contract_decisions.json"
DEFAULT_PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_GAMEPLAY_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.inventory-item-copied-signals-stability-check.v1"
DECISIONS_SCHEMA = "obelisk.inventory-item-copied-signals-public-contract-decisions.v1"
PUBLIC_SDK_SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PUBLIC_GAMEPLAY_EVENTS_SCHEMA = "obelisk.public-gameplay-events.v1"
NON_COUNTING_ACCOUNTING: dict[str, bool | int] = {
    "approved_runtime_evidence_accepted": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "clears_approved_runtime_evidence_missing": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "side_lane_counts_toward_sdk": False,
    "side_lane_counts_toward_p0": False,
    "sdk_p0_unlock_allowed": False,
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "promotion_ready": False,
    "runtime_ready": False,
    "runtime_capture_ready": False,
    "replaces_player_principal_evidence": False,
    "replaces_player_principal_triplet": False,
    "player_principal_replacement_ready": False,
    "live_ops_ready": False,
    "public_sdk_ready": False,
    "public_module_ready": False,
    "stable_claim_allowed": False,
    "v1_completion_ready": False,
}
READINESS_TRUTHFULNESS_REPORT: dict[str, Any] = {
    "ready_field_semantics": "non_authorizing_guardrail_passed_only",
    "ready_means": (
        "the checked docs/header inputs still match the narrow copied-scalar "
        "GameplayPolicyEvent side lane"
    ),
    "ready_does_not_mean": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
    "public_inventory_sdk_claim_allowed": False,
    "public_items_sdk_claim_allowed": False,
    "public_inventory_sdk_ready": False,
    "runtime_readiness_claim_allowed": False,
    "v1_completion_claim_allowed": False,
    "v1_progress_contribution": 0,
    "current_route_blocker": CURRENT_ROUTE_BLOCKER,
    "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
    "multi_surface_beta_capture_counts_as_approved_runtime_evidence": False,
}
NEXT_BLOCKERS: dict[str, Any] = {
    "player_principal_runtime": {
        "id": CURRENT_ROUTE_BLOCKER,
        "blocked_for_complete_sdk": True,
        "blocked_for_p0_dependency_chain": True,
        "required_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "candidate_beta_capture_plan_counts_as_runtime_evidence": False,
        "candidate_beta_capture_pack_counts_as_runtime_evidence": False,
        "required_future_evidence": [
            "strict approved player-principal lifecycle runtime evidence",
            "checker-accepted HandleNewPlayer/CheckJoinInProgress/OnLogout runtime triplet",
        ],
    },
    "offline": {
        "id": "public_inventory_items_mutation_contract_not_in_scope",
        "blocked_for_current_copied_signal_guardrail": False,
        "blocked_for_public_inventory_sdk": True,
        "current_side_lane_status": "five copied POD scalar observations only",
        "required_future_evidence": [
            "separate narrow copied C ABI for each promoted inventory/item audit unit",
            "rollback, privacy, and abuse controls for grants/removals/progression",
            "append-only ABI layout and SDK consumer tests for any promoted inventory/items surface",
        ],
    },
    "runtime": {
        "id": "object_identity_resource_handle_runtime_evidence_missing",
        "blocked_for_public_inventory_sdk": True,
        "required_future_evidence": [
            "runtime object negative samples",
            "runtime serial reuse/wraparound semantics",
            "callback-scope versus post-callback validity rules",
        ],
        "blocked_claims": [
            "Inventory SDK",
            "Items SDK",
            "lookup",
            "mutation",
            "return override",
            "ResourceHandle",
            "v1 completion",
        ],
    },
}
SURFACE = "obelisk.inventory_item_copied_signals.v1"
GAMEPLAY_POLICY_EVENT_SURFACE = "obelisk.gameplay_policy_event.v1"
GAMEPLAY_POLICY_EVENT = "obelisk.gameplay_policy.v1"
INVENTORY_MUTATION_SURFACE = "obelisk.inventory_items_mutation.v1"
RESOURCE_HANDLE_SURFACE = "obelisk.object_identity_resource_handle.v1"
PROMOTED_EXPERIMENTAL_SURFACE_IDS = (
    GAMEPLAY_POLICY_EVENT_SURFACE,
    "obelisk.chat_message.v1",
    "obelisk.chat.local_routing.v1",
    SURFACE,
)
PROMOTED_EXPERIMENTAL_OUTCOME_STATUS = "unresolved"
PROMOTED_EXPERIMENTAL_COMPLETE_SDK_ACCOUNTING = (
    "fail_closed_until_promoted_excluded_or_post_v1"
)
PROMOTED_EXPERIMENTAL_ALLOWED_RESOLUTIONS = (
    "promote_with_surface_specific_evidence",
    "exclude_from_v1_release_statement",
    "move_to_post_v1",
)
PROMOTED_EXPERIMENTAL_MUST_NOT_UNLOCK = (
    "commands",
    "moderation",
    "identity",
    "lookup",
    "mutation",
    "return override",
    "ResourceHandle",
)
RESOURCE_KIND = "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM"
ALL_INVENTORY_MASK = "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY"
RETURN_VALUE = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE"
REQUESTED_BY_PLAYER = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER"
IGNORE_COOLDOWN = "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN"
EXPECTED_INVENTORY_TARGET_SET = "minimal-second-source-intake"
EXPECTED_ITEM_RETURN_TARGET_SET = "item-return-only-policy-slice"
EXCLUDED_INVENTORY_ACTION_TARGET_SET = "inventory-action-compact-intake"
EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS = (
    EXPECTED_INVENTORY_TARGET_SET,
)
EXPECTED_TARGET_SET_EVIDENCE_SCOPE_TERMS = {
    EXPECTED_INVENTORY_TARGET_SET: (
        "layout-only",
        "no standalone",
        "module-specific",
        "inventory",
    ),
}

EXPECTED_ALLOWED_SIGNALS: tuple[dict[str, Any], ...] = (
    {
        "stable_name": "inventory.remote_add_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_REMOTE_ADD_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_REMOTE_ADD_CHECK",
        "field_mask": [RETURN_VALUE, REQUESTED_BY_PLAYER],
    },
    {
        "stable_name": "inventory.use_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_CHECK",
        "field_mask": [RETURN_VALUE, IGNORE_COOLDOWN],
    },
    {
        "stable_name": "inventory_item.allow_equip_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_ALLOW_EQUIP_ITEM_CHECK",
        "field_mask": [RETURN_VALUE],
    },
    {
        "stable_name": "inventory_item.can_repair_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_CAN_REPAIR_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_CAN_REPAIR_CHECK",
        "field_mask": [RETURN_VALUE],
    },
    {
        "stable_name": "inventory_item.use_onto_item_check",
        "kind": "OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "event_kind_mask": "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_USE_ITEM_ONTO_ITEM_CHECK",
        "field_mask": [RETURN_VALUE],
    },
)
EXPECTED_SIGNAL_BY_KIND = {signal["kind"]: signal for signal in EXPECTED_ALLOWED_SIGNALS}
EXPECTED_SIGNAL_KINDS = frozenset(EXPECTED_SIGNAL_BY_KIND)
EXPECTED_SIGNAL_MASKS = frozenset(signal["event_kind_mask"] for signal in EXPECTED_ALLOWED_SIGNALS)
EXPECTED_SIGNAL_FIELDS = frozenset(
    field for signal in EXPECTED_ALLOWED_SIGNALS for field in signal["field_mask"]
)
EXPECTED_SIGNAL_KIND_VALUES = {
    signal["kind"]: index for index, signal in enumerate(EXPECTED_ALLOWED_SIGNALS, start=7)
}
EXPECTED_SIGNAL_MASK_SHIFTS = {
    signal["event_kind_mask"]: index for index, signal in enumerate(EXPECTED_ALLOWED_SIGNALS, start=6)
}
EXPECTED_FIELD_MASK_SHIFTS = {
    RETURN_VALUE: 0,
    REQUESTED_BY_PLAYER: 4,
    IGNORE_COOLDOWN: 5,
}
EXPECTED_RESOURCE_KIND_VALUES = {
    RESOURCE_KIND: 2,
}
EXPECTED_REQUIRED_FLAGS = frozenset(
    (
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
    )
)
EXPECTED_DECISIONS_PAYLOAD_CONTRACT = "copied POD scalar observation only"
EXPECTED_SURFACE_PAYLOAD_CONTRACT = (
    "copied bool ReturnValue signals only where declared by docs/public_gameplay_events.json",
    "copied bRequestedByPlayer for inventory.remote_add_check",
    "copied bIgnoreCooldown for inventory.use_check",
    "resource_kind remains INVENTORY_ITEM metadata only",
    "post-original observation only; no authority",
)
EXPECTED_PUBLIC_CONTRACT = tuple(
    f"GameplayPolicyEvent {signal['stable_name']}" for signal in EXPECTED_ALLOWED_SIGNALS
)
EXPECTED_HEADER_SYMBOLS = frozenset(
    (
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENTS",
        "OBELISK_API_CAPABILITY_GAMEPLAY_POLICY_EVENT_DESCRIPTORS",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_COPIED_PAYLOAD",
        "OBELISK_GAMEPLAY_POLICY_EVENT_FLAG_INVENTORY_BACKED",
        "OBELISK_GAMEPLAY_POLICY_EVENT_MASK_ALL_INVENTORY",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_RETURN_VALUE",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_REQUESTED_BY_PLAYER",
        "OBELISK_GAMEPLAY_POLICY_FIELD_MASK_IGNORE_COOLDOWN",
        "OBELISK_GAMEPLAY_POLICY_RESOURCE_KIND_INVENTORY_ITEM",
        "ObeliskGameplayPolicyEvent",
        "ObeliskGameplayPolicyEventDescriptor",
        "ObeliskGameplayPolicyEventCallback",
        "RegisterGameplayPolicyEventWithOwnerTokenHandle",
        "UnregisterGameplayPolicyEventWithOwnerToken",
        "DescribeGameplayPolicyEventKind",
    )
    + tuple(EXPECTED_SIGNAL_KINDS)
    + tuple(EXPECTED_SIGNAL_MASKS)
)
REQUIRED_FORBIDDEN_TERMS = frozenset(
    (
        "Inventory SDK",
        "Items SDK",
        "lookup",
        "mutation",
        "return override",
        "ResourceHandle",
        "AdditionalData",
        "ItemNetID identity",
    )
)
PUBLIC_CLAIM_TERMS = frozenset(
    (
        "Inventory SDK",
        "Items SDK",
        "public SDK",
        "runtime support",
        "runtime/v1 support",
        "package shape",
        "Plugin Hub",
        "support tier",
        "umbrella leaf promotion",
        "leaf promotion",
        "v1 support",
        "contributes to public SDK v1",
        "contributes to v1 completion",
        "counts for public SDK v1",
        "counts toward P0 dependency chain claim",
        "counts toward v1 completion",
        "complete SDK claim progress contribution",
        "approved runtime evidence",
        "approved runtime evidence accepted",
        "approved runtime evidence ready",
        "clears approved runtime evidence missing",
        "countsForPublicSdkV1",
        "countsTowardP0DependencyChainClaim",
        "countsTowardV1Completion",
        "complete_sdk_claim_progress_contribution",
        "counts_for_public_sdk_v1",
        "counts_toward_p0_dependency_chain_claim",
        "counts_toward_v1_completion",
        "p0_dependency_chain_claim_progress_contribution",
        "player-principal lifecycle evidence",
        "player principal lifecycle evidence",
        "player-principal runtime evidence",
        "player principal runtime evidence",
        "player-principal triplet",
        "player principal triplet",
        "v1 completion contribution",
        "lookup",
        "mutation",
        "return override",
        "resource handle",
        "ResourceHandle",
        "AdditionalData",
        "ResourceHandle API",
        "AdditionalData API",
        "ArrayProperty",
        "TArray",
        "TArray copy",
        "InventoryCustomFilter",
        "InventoryCustomFilter API",
        "InventoryCustomFilter callback",
        "custom filter",
        "custom-filter",
        "custom filter array",
        "array range",
        "raw array",
        "raw range",
        "copied array",
        "copied list",
        "copied range",
        "exposed range",
        "exposes range",
        "payload range",
        "public array payload",
        "Inventory callback API",
        "InventoryComp",
        "action alias",
        "action aliases",
        "ItemId",
        "ItemID1",
        "ItemNetID identity",
        "ServerRequestInventoryUseItem",
        "ServerRequestInventoryUseItemWithActor",
        "action params",
        "anActor",
        "craft authority",
        "crafting authority",
        "equip authority",
        "item stack identity",
        "owner lookup",
        "ownership lookup",
        "raw params",
        "repair authority",
        "stack identity",
    )
)
PUBLIC_SDK_SURFACES_INVENTORY_SIDE_LANE_TERMS = frozenset(("Inventory SDK", "Items SDK"))
CONTRACT_SCAN_KEYS = frozenset(
    (
        "public_contract",
        "payload_contract",
        "scope",
        "resource_contract",
        "public_fields",
        "descriptor_fields",
        "compatibility_statement",
        "inventory_sdk",
        "item_module_sdk",
        "public_name",
        "release_claim",
        "support_tier",
    )
)
CLAIM_TEXT_SCAN_KEYS = CONTRACT_SCAN_KEYS | frozenset(
    (
        "alias",
        "aliases",
        "artifact_label",
        "artifact_labels",
        "evidence_marker",
        "evidence_markers",
        "claim",
        "claims",
        "description",
        "evidence_summary",
        "replacement_claim",
        "replacement_claims",
        "marker",
        "markers",
        "note",
        "notes",
        "rationale",
        "readiness_alias",
        "readiness_aliases",
        "release_note",
        "report_section",
        "report_sections",
        "review_note",
        "review_notes",
        "source_label",
        "source_labels",
        "source_marker",
        "source_markers",
        "summary",
    )
)
READINESS_TEXT_SCAN_KEYS = CLAIM_TEXT_SCAN_KEYS | frozenset(
    (
        "inventory_sdk_readiness",
        "items_sdk_readiness",
        "promotion_readiness",
        "public_abi_readiness",
        "public_inventory_sdk_readiness",
        "public_items_sdk_readiness",
        "public_sdk_readiness",
        "release_readiness",
        "runtime_readiness",
        "stable_sdk_readiness",
        "v1_completion_readiness",
        "v1_readiness",
        "v1_sdk_readiness",
    )
)
NEGATIVE_KEYS = frozenset(
    (
        "blockers",
        "exclusions",
        "forbidden_terms",
        "guardrails",
        "must_not_unlock",
        "non_claims",
        "not_promoted",
        "redacted_fields",
    )
)
NEGATED_OR_BOUNDARY_RE = re.compile(
    r"\b(?:"
    r"blocked|cannot|does\s+not|do\s+not|excluded|excludes?|future|metadata-only|"
    r"must\s+not|no|not|only|outside|post-v1|prevent|prevents|remain|remains|"
    r"without"
    r")\b",
    re.IGNORECASE,
)
CLAUSE_SPLIT_RE = re.compile(r"[,.;:\n\r]+")
NEGATION_LIST_SCOPE_SPLIT_RE = re.compile(r"[.;:\n\r]+")
POSITIVE_TERM_SUFFIX_RE = re.compile(
    r"^\s+(?:ready|enabled|public|supported|allowed|live|operational|ok|green|"
    r"go|pass(?:ed)?|ship(?:ped)?|done|yes|valid(?:ated)?|verified|unblocked|"
    r"exposes?|provides?)\b",
    re.IGNORECASE,
)
POSITIVE_READINESS_SHORTCUT_WORDS = (
    "ok",
    "green",
    "go",
    "pass",
    "ship",
    "shipped",
    "done",
    "yes",
    "unblocked",
)
POSITIVE_READINESS_SHORTCUT_SUBJECTS = (
    "inventory sdk",
    "items sdk",
    "promotion",
    "public abi",
    "public readiness",
    "public sdk",
    "release",
    "runtime",
    "runtime evidence",
    "source",
    "stable sdk",
    "v1",
    "v1 completion",
    "v1 sdk",
    "package shape",
    "plugin hub",
    "support tier",
    "mutation",
    "return override",
    "resource handle",
)
POSITIVE_READINESS_PHRASES = (
    "inventory sdk ready",
    "inventory sdk readiness",
    "items sdk ready",
    "items sdk readiness",
    "promotion ready",
    "promotion readiness",
    "public abi ready",
    "public abi readiness",
    "public readiness",
    "public sdk ready",
    "public sdk readiness",
    "release ready",
    "release readiness",
    "release-supported",
    "public sdk support",
    "runtime support",
    "runtime/v1 support",
    "package shape passed",
    "package shape ready",
    "package shape readiness",
    "package shape support",
    "plugin hub ready",
    "plugin hub readiness",
    "plugin hub support",
    "support tier active",
    "support tier enabled",
    "support tier ready",
    "support tier supported",
    "umbrella leaf promoted",
    "umbrella leaf promotion",
    "leaf promoted",
    "leaf promotion ready",
    "v1 support",
    "runtime ready",
    "runtime readiness",
    "is stable",
    "stable release",
    "stable sdk ready",
    "stable sdk readiness",
    "approved runtime bundle",
    "approved runtime evidence",
    "approved runtime evidence accepted",
    "approved runtime evidence ready",
    "clears approved runtime evidence missing",
    "contributes to public sdk v1",
    "contributes to v1 completion",
    "counts for public sdk v1",
    "counts toward complete sdk",
    "counts toward complete sdk claim",
    "counts toward p0 dependency chain claim",
    "counts toward v1 completion",
    "complete sdk claim progress contribution",
    "countsForPublicSdkV1",
    "countsTowardCompleteSdkClaim",
    "countsTowardP0DependencyChainClaim",
    "countsTowardV1Completion",
    "complete_sdk_claim_progress_contribution",
    "counts_for_public_sdk_v1",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_v1_completion",
    "p0_dependency_chain_claim_progress_contribution",
    "runtime evidence approved",
    "source approved",
    "mutation ready",
    "mutation support",
    "return override ready",
    "return override support",
    "resource handle ready",
    "resource handle readiness",
    "resource handle support",
    "player-principal lifecycle evidence",
    "player principal lifecycle evidence",
    "player-principal runtime evidence",
    "player principal runtime evidence",
    "player-principal triplet",
    "player principal triplet",
    "replaces player-principal lifecycle evidence",
    "replaces player principal lifecycle evidence",
    "v1 completion",
    "v1 completion contribution",
    "v1 completion ready",
    "v1 completion readiness",
    "v1 ready",
    "v1 readiness",
    "v1 sdk ready",
    "v1 sdk readiness",
)
POSITIVE_READINESS_PHRASES += tuple(
    f"{subject} {shortcut}"
    for subject in POSITIVE_READINESS_SHORTCUT_SUBJECTS
    for shortcut in POSITIVE_READINESS_SHORTCUT_WORDS
)
READINESS_CONTEXT_KEY_RE = re.compile(
    r"(?:public|sdk|api|abi|module|runtime|capture|live[_-]?ops|source|v1|p0|"
    r"complete|completion|stable|promotion|resource[_-]?handle|return[_-]?override|"
    r"identity|lookup|mutation|support|tier|package[_-]?shape|plugin[_-]?hub|"
    r"approved[_-]?runtime|player[_-]?principal|principal[_-]?lifecycle|"
    r"multi[_-]?surface|beta[_-]?capture|capture[_-]?(?:pack|plan|queue)|"
    r"evidence[_-]?bundle|route[_-]?blocker)",
    re.IGNORECASE,
)
SOURCE_READINESS_ALIAS_KEYS = frozenset(
    (
        "source_accepted",
        "source_available",
        "source_label",
        "source_labels",
        "source_marker",
        "source_markers",
        "source_readiness",
        "source_ready",
        "source_stable",
        "source_status",
        "source_support",
        "source_tier",
        "source_validated",
        "source_validation",
    )
)
FORBIDDEN_READINESS_ALIAS_PATH_SUFFIXES = frozenset(
    (
        "artifact_identity_approved",
        "candidate_accepted",
        "consume_gate_ready",
        "inventory_public_contract",
        "package_shape_passed",
        "plugin_hub_ready",
        "public_sdk_enabled",
        "readiness_approved",
        "runtime_validated",
        "side_lane_counts_toward_v1",
        "static_evidence_validated",
        "support_tier_active",
        "target_set_promoted",
        "transfer_runtime_ready",
        "v1_complete",
    )
)
CLAIM_CONTEXT_CONTAINER_KEYS = frozenset(
    (
        "candidate",
        "candidate_surfaces",
        "capture_surfaces",
        "live_ops",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_beta_capture_plan_queue",
        "package_shape",
        "player_principal",
        "plugin_hub",
        "public_module",
        "public_sdk",
        "readiness",
        "required_primary_evidence",
        "route_blocker",
        "runtime_capture",
        "source",
        "support_tier",
        "target_set",
        "v1",
    )
)
CONTEXTUAL_READINESS_STATUS_KEYS = frozenset(
    (
        "accepted",
        "active",
        "approved",
        "complete",
        "enabled",
        "outcome",
        "passed",
        "promoted",
        "readiness",
        "ready",
        "result",
        "stable",
        "state",
        "status",
        "validated",
    )
)
CONTEXTUAL_READINESS_ACCOUNTING_TERMS = (
    "contribution",
    "count",
    "counts",
    "progress",
)
NEUTRAL_TRUE_METADATA_KEYS = frozenset(
    (
        "accepted_for_candidate_review",
        "accepted_for_internal_planning",
        "append_only_abi",
        "capability_gated",
        "candidate_capture_only",
        "candidate_only",
        "candidate_only_mode",
        "consume_only",
        "leaf_split_reviewed",
        "must_remain_without_public_contract_until_promotion",
        "non_counting",
        "no_ue_internals_in_public_abi",
        "not_artifact_gate",
        "offline_only",
        "public_header_allowed",
        "broadcast_before_restart_if_players_connected",
        "keep_servers_running_when_practical",
        "keep_transfer_server_when_practical",
        "must_be_checker_accepted",
        "requires_checker_acceptance",
        "restart_only_for_obelisk_update_or_gate_change",
        "runtime_producer_gate_implemented",
        "second_source_ready",
    )
)
NEUTRAL_TRUE_METADATA_SUFFIXES = (
    "_candidate_only",
    "_consume_only",
    "_non_counting",
    "_not_artifact_gate",
    "_offline_only",
)
NEUTRAL_POSITIVE_METADATA_KEYS = frozenset(
    (
        "bound_target_count",
        "max_ark_servers_running",
        "priority",
        "second_source_accepted",
        "source_binding_count",
        "target_count",
        "v1_dependency_chain_position",
        "required_by_v1_dependency_chain_position",
    )
)
NEUTRAL_POSITIVE_METADATA_SUFFIXES = (
    "_chain_position",
    "_dependency_chain_position",
    "_target_count",
)
POSITIVE_STATUS_SHORTCUT_VALUES = frozenset(
    (
        "done",
        "go",
        "green",
        "live",
        "ok",
        "operational",
        "pass",
        "ship",
        "shipped",
        "unblocked",
        "valid",
        "verified",
        "yes",
    )
)
POSITIVE_STATUS_VALUES = frozenset(
    (
        "accepted",
        "active",
        "approved",
        "available",
        "complete",
        "completed",
        "enabled",
        "passed",
        "promoted",
        "public",
        "public-ready",
        "ready",
        "release-ready",
        "release-supported",
        "runtime",
        "runtime-ready",
        "sdk-ready",
        "stable",
        "stable-ready",
        "supported",
        "validated",
        "v1-ready",
    )
) | POSITIVE_STATUS_SHORTCUT_VALUES
C_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CPP_COMMENT_RE = re.compile(r"//.*")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the inventory/item copied-signal public contract remains narrow."
    )
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    parser.add_argument("--public-sdk-surfaces", type=Path, default=DEFAULT_PUBLIC_SDK_SURFACES)
    parser.add_argument("--public-gameplay-events", type=Path, default=DEFAULT_PUBLIC_GAMEPLAY_EVENTS)
    parser.add_argument("--public-header", type=Path, default=DEFAULT_PUBLIC_HEADER)
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args(argv)


def add(blockers: list[dict[str, Any]], reason: str, label: str, **details: Any) -> None:
    item: dict[str, Any] = {"reason": reason, "path": label}
    item.update(details)
    blockers.append(item)


def load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"--{label}", path=str(path), error=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"--{label}", path=str(path), error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"--{label}", path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"--{label}", path=str(path))
        return None
    return payload


def strip_c_comments(text: str) -> str:
    text = C_COMMENT_RE.sub("", text)
    return CPP_COMMENT_RE.sub("", text)


def normalized_signals(signals: Any) -> list[dict[str, Any]]:
    if not isinstance(signals, list):
        return []
    result: list[dict[str, Any]] = []
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        result.append(
            {
                "stable_name": signal.get("stable_name"),
                "kind": signal.get("kind"),
                "event_kind_mask": signal.get("event_kind_mask"),
                "field_mask": list(signal.get("field_mask") or []),
            }
        )
    return sorted(result, key=lambda item: str(item.get("kind")))


def expected_signals_sorted() -> list[dict[str, Any]]:
    return sorted((dict(signal) for signal in EXPECTED_ALLOWED_SIGNALS), key=lambda item: item["kind"])


def string_values(value: Any, trail: str) -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(trail, value)]
    if isinstance(value, list):
        result: list[tuple[str, str]] = []
        for index, child in enumerate(value):
            result.extend(string_values(child, f"{trail}[{index}]"))
        return result
    if isinstance(value, dict):
        result = []
        for key, child in value.items():
            result.extend(string_values(child, f"{trail}.{key}"))
        return result
    return []


def preceding_clause(text: str, start: int) -> str:
    prefix = text[:start]
    parts = CLAUSE_SPLIT_RE.split(prefix)
    return parts[-1] if parts else prefix


def preceding_negation_list_scope(text: str, start: int) -> str:
    prefix = text[:start]
    parts = NEGATION_LIST_SCOPE_SPLIT_RE.split(prefix)
    return parts[-1] if parts else prefix


def has_positive_term_suffix(text: str, end: int) -> bool:
    return bool(POSITIVE_TERM_SUFFIX_RE.match(text[end:]))


def has_negation_before_match(text: str, start: int) -> bool:
    return bool(
        NEGATED_OR_BOUNDARY_RE.search(preceding_clause(text, start))
        or NEGATED_OR_BOUNDARY_RE.search(preceding_negation_list_scope(text, start))
    )


def is_negated_for_match(text: str, start: int, end: int) -> bool:
    if has_positive_term_suffix(text, end):
        return False
    return has_negation_before_match(text, start)


def flexible_phrase_match(text: str, phrase: str) -> re.Match[str] | None:
    tokens = [token for token in re.split(r"[^A-Za-z0-9]+", phrase) if token]
    if not tokens:
        return None
    pattern = r"(?<![A-Za-z0-9])" + r"[\W_]*".join(re.escape(token) for token in tokens) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, re.IGNORECASE)


def normalized_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def scan_public_claim_terms(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in NEGATIVE_KEYS:
                scan_positive_claim_terms_in_negative_container(child, blockers, child_trail)
                continue
            if key in CLAIM_TEXT_SCAN_KEYS:
                for text_path, text in string_values(child, child_trail):
                    for term in PUBLIC_CLAIM_TERMS:
                        match = flexible_phrase_match(text, term)
                        if not match:
                            continue
                        if is_negated_for_match(text, match.start(), match.end()):
                            continue
                        add(blockers, "public_claim_forbidden_term", text_path, term=term, value=text)
                continue
            scan_public_claim_terms(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_claim_terms(child, blockers, f"{trail}[{index}]")


def scan_positive_claim_terms_in_negative_container(
    value: Any, blockers: list[dict[str, Any]], trail: str
) -> None:
    if isinstance(value, str):
        for phrase in POSITIVE_READINESS_PHRASES:
            match = flexible_phrase_match(value, phrase)
            if not match:
                continue
            if has_negation_before_match(value, match.start()):
                continue
            add(blockers, "readiness_claim_enabled", trail, value=value, term=phrase)
            break
        for term in PUBLIC_CLAIM_TERMS:
            match = flexible_phrase_match(value, term)
            if not match:
                continue
            if not has_positive_term_suffix(value, match.end()):
                continue
            if has_negation_before_match(value, match.start()):
                continue
            add(blockers, "public_claim_forbidden_term", trail, term=term, value=value)
        return
    if isinstance(value, dict):
        for key, child in value.items():
            scan_positive_claim_terms_in_negative_container(child, blockers, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_positive_claim_terms_in_negative_container(child, blockers, f"{trail}[{index}]")


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_progress_claim(value: Any) -> bool:
    if positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip()
    ratio = re.fullmatch(r"([1-9]\d*)\s*/\s*\d+", normalized)
    if ratio:
        return True
    return bool(re.fullmatch(r"[1-9]\d*", normalized))


def positive_status_claim(value: Any) -> bool:
    if value is True or positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    normalized = normalized_claim_key(value).replace("_", "-")
    return normalized in POSITIVE_STATUS_VALUES or normalized.endswith("-ready")


def readiness_context_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    if normalized in {"accepted_for_internal_planning", "accepted_for_candidate_review"}:
        return False
    return bool(READINESS_CONTEXT_KEY_RE.search(normalized))


def stale_readiness_satisfied_alias_key(key: str) -> bool:
    return key == "readiness_satisfied" or key.endswith("_readiness_satisfied")


def neutral_positive_metadata_key(key: str) -> bool:
    if key in NEUTRAL_TRUE_METADATA_KEYS or key in NEUTRAL_POSITIVE_METADATA_KEYS:
        return True
    if any(key.endswith(suffix) for suffix in NEUTRAL_TRUE_METADATA_SUFFIXES):
        return True
    return any(key.endswith(suffix) for suffix in NEUTRAL_POSITIVE_METADATA_SUFFIXES)


def neutral_positive_metadata_path(key: str, trail: str) -> bool:
    return (
        key == "promotion_status"
        and ".required_identity_promotion_certificate.promotion_status" in trail
    )


def normalized_trail_leaf_key(trail: str) -> str:
    leaf = trail.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]$", "", leaf)
    return normalized_claim_key(leaf)


def forbidden_readiness_alias_path(trail: str) -> bool:
    normalized_trail = normalized_claim_key(trail)
    return any(
        normalized_trail == suffix or normalized_trail.endswith(f"_{suffix}")
        for suffix in FORBIDDEN_READINESS_ALIAS_PATH_SUFFIXES
    )


def readiness_accounting_alias_key(key: str) -> bool:
    return any(term in key for term in CONTEXTUAL_READINESS_ACCOUNTING_TERMS)


def propagates_readiness_claim_context(key: str) -> bool:
    return key in CLAIM_CONTEXT_CONTAINER_KEYS or key in SOURCE_READINESS_ALIAS_KEYS


def scan_public_sdk_surfaces_inventory_side_lane_claims(
    value: Any, blockers: list[dict[str, Any]], trail: str = "$"
) -> None:
    if isinstance(value, str):
        for term in PUBLIC_SDK_SURFACES_INVENTORY_SIDE_LANE_TERMS:
            match = flexible_phrase_match(value, term)
            if not match:
                continue
            if is_negated_for_match(value, match.start(), match.end()):
                continue
            add(
                blockers,
                "public_sdk_surfaces_positive_inventory_side_lane_claim",
                trail,
                term=term,
                value=value,
            )
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if key in NEGATIVE_KEYS:
                continue
            scan_public_sdk_surfaces_inventory_side_lane_claims(child, blockers, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_public_sdk_surfaces_inventory_side_lane_claims(child, blockers, f"{trail}[{index}]")


def require_equal(
    mapping: dict[str, Any], key: str, expected: Any, label: str, blockers: list[dict[str, Any]]
) -> None:
    if mapping.get(key) != expected:
        add(blockers, f"{key}_mismatch", f"{label}.{key}", expected=expected, value=mapping.get(key))


def require_false(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) is not False:
        add(blockers, f"{key}_not_false", f"{label}.{key}", value=mapping.get(key))


def require_zero(mapping: dict[str, Any], key: str, label: str, blockers: list[dict[str, Any]]) -> None:
    if mapping.get(key) != 0:
        add(blockers, f"{key}_not_zero", f"{label}.{key}", value=mapping.get(key))


def expected_promoted_experimental_outcome(surface_id: str) -> dict[str, Any]:
    return {
        "surface_id": surface_id,
        "current_status": "promoted-experimental-only",
        "outcome_status": PROMOTED_EXPERIMENTAL_OUTCOME_STATUS,
        "complete_sdk_accounting": PROMOTED_EXPERIMENTAL_COMPLETE_SDK_ACCOUNTING,
        "allowed_resolutions": list(PROMOTED_EXPERIMENTAL_ALLOWED_RESOLUTIONS),
        "v1_completion_evidence": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "v1_completion_ready": False,
        "must_not_unlock": list(PROMOTED_EXPERIMENTAL_MUST_NOT_UNLOCK),
    }


def validate_promoted_experimental_outcome(
    record: Any,
    *,
    surface_id: str,
    label: str,
    blockers: list[dict[str, Any]],
    reason_prefix: str,
) -> None:
    if not isinstance(record, dict):
        add(
            blockers,
            f"{reason_prefix}_missing",
            label,
            expected=expected_promoted_experimental_outcome(surface_id),
            value=record,
        )
        return

    require_equal(record, "surface_id", surface_id, label, blockers)
    require_equal(record, "current_status", "promoted-experimental-only", label, blockers)
    require_equal(
        record,
        "outcome_status",
        PROMOTED_EXPERIMENTAL_OUTCOME_STATUS,
        label,
        blockers,
    )
    require_equal(
        record,
        "complete_sdk_accounting",
        PROMOTED_EXPERIMENTAL_COMPLETE_SDK_ACCOUNTING,
        label,
        blockers,
    )
    for key in (
        "v1_completion_evidence",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain_claim",
        "public_sdk_ready",
        "runtime_ready",
        "stable_claim_allowed",
        "v1_completion_ready",
    ):
        require_false(record, key, label, blockers)
    for key in (
        "complete_sdk_claim_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
    ):
        require_zero(record, key, label, blockers)

    if tuple(record.get("allowed_resolutions") or []) != PROMOTED_EXPERIMENTAL_ALLOWED_RESOLUTIONS:
        add(
            blockers,
            f"{reason_prefix}_allowed_resolutions_mismatch",
            f"{label}.allowed_resolutions",
            expected=list(PROMOTED_EXPERIMENTAL_ALLOWED_RESOLUTIONS),
            value=record.get("allowed_resolutions"),
        )
    must_not_unlock = set(record.get("must_not_unlock") or [])
    missing_must_not_unlock = sorted(set(PROMOTED_EXPERIMENTAL_MUST_NOT_UNLOCK) - must_not_unlock)
    if missing_must_not_unlock:
        add(
            blockers,
            f"{reason_prefix}_must_not_unlock_missing",
            f"{label}.must_not_unlock",
            missing=missing_must_not_unlock,
            value=sorted(must_not_unlock),
        )


def validate_promoted_experimental_surface_outcomes(
    payload: dict[str, Any], blockers: list[dict[str, Any]], label: str
) -> list[str]:
    raw_outcomes = payload.get("promoted_experimental_surface_outcomes")
    if not isinstance(raw_outcomes, list):
        add(
            blockers,
            "public_gameplay_promoted_experimental_outcomes_missing",
            f"{label}.promoted_experimental_surface_outcomes",
            expected=list(PROMOTED_EXPERIMENTAL_SURFACE_IDS),
            value=raw_outcomes,
        )
        return []

    outcomes_by_surface: dict[str, dict[str, Any]] = {}
    duplicate_surfaces: list[str] = []
    unexpected_surfaces: list[str] = []
    for index, record in enumerate(raw_outcomes):
        record_label = f"{label}.promoted_experimental_surface_outcomes[{index}]"
        if not isinstance(record, dict) or not isinstance(record.get("surface_id"), str):
            add(blockers, "public_gameplay_promoted_experimental_outcome_invalid", record_label, value=record)
            continue
        surface_id = record["surface_id"]
        if surface_id in outcomes_by_surface:
            duplicate_surfaces.append(surface_id)
        outcomes_by_surface[surface_id] = record
        if surface_id not in PROMOTED_EXPERIMENTAL_SURFACE_IDS:
            unexpected_surfaces.append(surface_id)

    for surface_id in PROMOTED_EXPERIMENTAL_SURFACE_IDS:
        validate_promoted_experimental_outcome(
            outcomes_by_surface.get(surface_id),
            surface_id=surface_id,
            label=f"{label}.promoted_experimental_surface_outcomes[{surface_id}]",
            blockers=blockers,
            reason_prefix="public_gameplay_promoted_experimental_outcome",
        )
    if duplicate_surfaces:
        add(
            blockers,
            "public_gameplay_promoted_experimental_outcome_duplicate",
            f"{label}.promoted_experimental_surface_outcomes",
            value=sorted(set(duplicate_surfaces)),
        )
    if unexpected_surfaces:
        add(
            blockers,
            "public_gameplay_promoted_experimental_outcome_unexpected",
            f"{label}.promoted_experimental_surface_outcomes",
            value=sorted(set(unexpected_surfaces)),
        )
    return [
        surface_id
        for surface_id in PROMOTED_EXPERIMENTAL_SURFACE_IDS
        if surface_id in outcomes_by_surface
    ]


def find_surface(payload: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    matches = [item for item in surfaces if isinstance(item, dict) and item.get("id") == surface_id]
    return matches[0] if len(matches) == 1 else None


def find_gameplay_policy_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    events = payload.get("promoted_events")
    if not isinstance(events, list):
        return None
    matches = [item for item in events if isinstance(item, dict) and item.get("event_id") == GAMEPLAY_POLICY_EVENT]
    return matches[0] if len(matches) == 1 else None


def target_set_evidence_names(event: dict[str, Any]) -> set[str]:
    return set(target_set_evidence_by_name(event))


def target_set_evidence_by_name(event: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence = event.get("target_set_evidence")
    if not isinstance(evidence, list):
        return {}
    return {
        str(item.get("target_set")): item
        for item in evidence
        if isinstance(item, dict) and item.get("target_set") is not None
    }


def excluded_target_set_names(event: dict[str, Any]) -> set[str]:
    excluded = event.get("excluded_target_sets")
    if not isinstance(excluded, list):
        return set()
    return {
        str(item.get("target_set"))
        for item in excluded
        if isinstance(item, dict) and item.get("target_set") is not None
    }


def find_resource_descriptor(payload: dict[str, Any]) -> dict[str, Any] | None:
    return find_metadata_surface(payload, "obelisk.resource_kind_descriptors.v1")


def find_gameplay_policy_event_descriptor(payload: dict[str, Any]) -> dict[str, Any] | None:
    return find_metadata_surface(payload, "obelisk.gameplay_policy_event_descriptors.v1")


def find_metadata_surface(payload: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = payload.get("metadata_surfaces")
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("surface_id") == surface_id:
            return surface
    return None


def find_inventory_resource_kind(payload: dict[str, Any]) -> dict[str, Any] | None:
    descriptor = find_resource_descriptor(payload)
    if not isinstance(descriptor, dict):
        return None
    resource_kinds = descriptor.get("resource_kinds")
    if not isinstance(resource_kinds, list):
        return None
    for resource_kind in resource_kinds:
        if isinstance(resource_kind, dict) and resource_kind.get("kind") == RESOURCE_KIND:
            return resource_kind
    return None


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.decisions"
    require_equal(payload, "schema", DECISIONS_SCHEMA, label, blockers)
    require_equal(payload, "surface", SURFACE, label, blockers)
    require_equal(payload, "status", "promoted-experimental-only", label, blockers)
    require_equal(payload, "decision", "copied_signal_only", label, blockers)
    require_equal(payload, "public_header_allowed", True, label, blockers)
    if GAMEPLAY_POLICY_EVENT_SURFACE not in set(payload.get("depends_on") or []):
        add(blockers, "decisions_dependency_missing", f"{label}.depends_on", expected=GAMEPLAY_POLICY_EVENT_SURFACE)
    validate_promoted_experimental_outcome(
        payload.get("promoted_experimental_outcome"),
        surface_id=SURFACE,
        label=f"{label}.promoted_experimental_outcome",
        blockers=blockers,
        reason_prefix="decisions_promoted_experimental_outcome",
    )

    actual_signals = normalized_signals(payload.get("allowed_signals"))
    expected = expected_signals_sorted()
    if actual_signals != expected:
        add(blockers, "decisions_allowed_signals_mismatch", f"{label}.allowed_signals", expected=expected, value=actual_signals)

    contract = payload.get("public_contract")
    if not isinstance(contract, dict):
        add(blockers, "decisions_public_contract_missing", f"{label}.public_contract")
    else:
        require_equal(contract, "resource_kind", RESOURCE_KIND, f"{label}.public_contract", blockers)
        require_equal(
            contract,
            "payload_contract",
            EXPECTED_DECISIONS_PAYLOAD_CONTRACT,
            f"{label}.public_contract",
            blockers,
        )
        resource_contract = str(contract.get("resource_contract") or "")
        for term in ("category-only", "no identity", "lookup", "handle"):
            if term not in resource_contract:
                add(
                    blockers,
                    "decisions_resource_contract_guardrail_missing",
                    f"{label}.public_contract.resource_contract",
                    term=term,
                    value=resource_contract,
                )
        if set(contract.get("public_fields") or []) != {
            "abi_version",
            "struct_size",
            "event_kind",
            "resource_kind",
            "flags",
            "field_mask",
            "bool_values",
            "int32_values",
        }:
            add(blockers, "decisions_public_fields_mismatch", f"{label}.public_contract.public_fields")
        actual_flags = set(contract.get("required_flags") or [])
        if actual_flags != EXPECTED_REQUIRED_FLAGS:
            add(
                blockers,
                "decisions_required_flags_mismatch",
                f"{label}.public_contract.required_flags",
                expected=sorted(EXPECTED_REQUIRED_FLAGS),
                value=sorted(actual_flags),
            )

    blocked = payload.get("blocked_public_contract")
    if not isinstance(blocked, dict):
        add(blockers, "decisions_blocked_public_contract_missing", f"{label}.blocked_public_contract")
    else:
        require_false(blocked, "standalone_inventory_sdk_allowed", f"{label}.blocked_public_contract", blockers)
        require_false(blocked, "standalone_items_sdk_allowed", f"{label}.blocked_public_contract", blockers)
        forbidden = set(blocked.get("forbidden_terms") or [])
        missing = sorted(REQUIRED_FORBIDDEN_TERMS - forbidden)
        if missing:
            add(blockers, "decisions_forbidden_terms_missing", f"{label}.blocked_public_contract.forbidden_terms", missing=missing)

    v1_contract = payload.get("v1_completion_contract")
    if not isinstance(v1_contract, dict):
        add(blockers, "decisions_v1_completion_contract_missing", f"{label}.v1_completion_contract")
    else:
        require_equal(
            v1_contract,
            "claim_effect",
            "does_not_complete_v1_sdk",
            f"{label}.v1_completion_contract",
            blockers,
        )

    listed_symbols = set(payload.get("public_header_symbols_now") or [])
    missing_symbols = sorted(EXPECTED_HEADER_SYMBOLS - listed_symbols)
    if missing_symbols:
        add(blockers, "decisions_public_header_symbols_missing", f"{label}.public_header_symbols_now", missing=missing_symbols)

    scan_public_claim_terms(payload, blockers, label)
    scan_readiness_claims(payload, blockers, label)
    return {
        "status": payload.get("status"),
        "allowed_signal_count": len(actual_signals),
        "allowed_kinds": sorted(item["kind"] for item in actual_signals),
    }


def validate_public_gameplay_events(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_gameplay_events"
    require_equal(payload, "schema", PUBLIC_GAMEPLAY_EVENTS_SCHEMA, label, blockers)
    promoted_experimental_outcomes = validate_promoted_experimental_surface_outcomes(
        payload,
        blockers,
        label,
    )

    event = find_gameplay_policy_event(payload)
    if event is None:
        add(blockers, "gameplay_policy_event_missing", f"{label}.promoted_events")
        return {"inventory_event_kinds": [], "promoted_experimental_outcomes": promoted_experimental_outcomes}

    require_equal(event, "v1_sdk_status", "promoted-experimental-only", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_false(event, "v1_completion_evidence", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_equal(event, "payload", "copied POD scalar fields only", f"{label}.{GAMEPLAY_POLICY_EVENT}", blockers)
    require_equal(
        event,
        "inventory_backing_target_set",
        EXPECTED_INVENTORY_TARGET_SET,
        f"{label}.{GAMEPLAY_POLICY_EVENT}",
        blockers,
    )
    require_equal(
        event,
        "item_return_backing_target_set",
        EXPECTED_ITEM_RETURN_TARGET_SET,
        f"{label}.{GAMEPLAY_POLICY_EVENT}",
        blockers,
    )
    target_sets = set(event.get("target_sets") or [])
    missing_target_sets = sorted(set(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS) - target_sets)
    if missing_target_sets:
        add(
            blockers,
            "gameplay_policy_inventory_target_sets_missing",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.target_sets",
            missing=missing_target_sets,
            value=sorted(target_sets),
        )
    evidence_by_target_set = target_set_evidence_by_name(event)
    evidence_target_sets = set(evidence_by_target_set)
    missing_evidence_sets = sorted(set(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS) - evidence_target_sets)
    if missing_evidence_sets:
        add(
            blockers,
            "gameplay_policy_inventory_target_set_evidence_missing",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.target_set_evidence",
            missing=missing_evidence_sets,
            value=sorted(evidence_target_sets),
        )
    for target_set, required_scope_terms in EXPECTED_TARGET_SET_EVIDENCE_SCOPE_TERMS.items():
        evidence = evidence_by_target_set.get(target_set)
        if evidence is None:
            continue
        evidence_label = f"{label}.{GAMEPLAY_POLICY_EVENT}.target_set_evidence[{target_set}]"
        scope = str(evidence.get("scope") or "")
        for term in required_scope_terms:
            if term not in scope:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_scope_guardrail_missing",
                    f"{evidence_label}.scope",
                    target_set=target_set,
                    term=term,
                    value=scope,
                )
        reports = evidence.get("reports")
        if not isinstance(reports, list) or not reports:
            add(
                blockers,
                "gameplay_policy_inventory_target_set_evidence_reports_missing",
                f"{evidence_label}.reports",
                target_set=target_set,
                value=reports,
            )
            continue
        for index, report in enumerate(reports):
            if not isinstance(report, str) or not report:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_report_invalid",
                    f"{evidence_label}.reports[{index}]",
                    target_set=target_set,
                    value=report,
                )
            elif "/servidor/ark" in report:
                add(
                    blockers,
                    "gameplay_policy_inventory_target_set_evidence_report_live_path",
                    f"{evidence_label}.reports[{index}]",
                    target_set=target_set,
                    value=report,
                )
    excluded_target_sets = excluded_target_set_names(event)
    if EXCLUDED_INVENTORY_ACTION_TARGET_SET not in excluded_target_sets:
        add(
            blockers,
            "gameplay_policy_inventory_action_target_set_not_excluded",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.excluded_target_sets",
            expected=EXCLUDED_INVENTORY_ACTION_TARGET_SET,
            value=sorted(excluded_target_sets),
        )
    resource_contract = str(event.get("resource_contract") or "")
    for term in ("kind-only", "no identity", "no lookup", "no persistent handle", "no cross-event correlation"):
        if term not in resource_contract:
            add(
                blockers,
                "gameplay_policy_resource_contract_guardrail_missing",
                f"{label}.{GAMEPLAY_POLICY_EVENT}.resource_contract",
                term=term,
                value=resource_contract,
            )

    event_kinds = event.get("event_kinds")
    if not isinstance(event_kinds, list):
        add(blockers, "gameplay_policy_event_kinds_not_list", f"{label}.{GAMEPLAY_POLICY_EVENT}.event_kinds")
        inventory_events: list[dict[str, Any]] = []
    else:
        inventory_events = [
            item for item in event_kinds if isinstance(item, dict) and item.get("resource_kind") == RESOURCE_KIND
        ]

    actual = normalized_signals(inventory_events)
    expected = expected_signals_sorted()
    if actual != expected:
        add(
            blockers,
            "public_gameplay_inventory_event_kinds_mismatch",
            f"{label}.{GAMEPLAY_POLICY_EVENT}.event_kinds",
            expected=expected,
            value=actual,
        )

    for index, item in enumerate(inventory_events):
        kind = item.get("kind")
        signal = EXPECTED_SIGNAL_BY_KIND.get(str(kind))
        if signal is None:
            continue
        if item.get("stable_name") != signal["stable_name"]:
            add(blockers, "public_gameplay_inventory_stable_name_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        if item.get("event_kind_mask") != signal["event_kind_mask"]:
            add(blockers, "public_gameplay_inventory_event_mask_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        if list(item.get("field_mask") or []) != signal["field_mask"]:
            add(blockers, "public_gameplay_inventory_field_mask_mismatch", f"{label}.event_kinds[{index}]", kind=kind)
        actual_flags = set(item.get("required_flags") or [])
        if actual_flags != EXPECTED_REQUIRED_FLAGS:
            add(
                blockers,
                "public_gameplay_inventory_required_flags_mismatch",
                f"{label}.event_kinds[{index}].required_flags",
                kind=kind,
                expected=sorted(EXPECTED_REQUIRED_FLAGS),
                value=sorted(actual_flags),
            )

    event_descriptor = find_gameplay_policy_event_descriptor(payload)
    if not isinstance(event_descriptor, dict):
        add(blockers, "gameplay_policy_event_descriptor_missing", f"{label}.metadata_surfaces")
    else:
        descriptor_flags = set(event_descriptor.get("flags") or [])
        missing_descriptor_flags = sorted(EXPECTED_REQUIRED_FLAGS - descriptor_flags)
        if missing_descriptor_flags:
            add(
                blockers,
                "gameplay_policy_event_descriptor_required_flags_missing",
                f"{label}.metadata_surfaces.gameplay_policy_event_descriptors.flags",
                missing=missing_descriptor_flags,
            )

    resource_descriptor = find_resource_descriptor(payload)
    if not isinstance(resource_descriptor, dict):
        add(blockers, "resource_descriptor_missing", f"{label}.metadata_surfaces")
    else:
        scope = str(resource_descriptor.get("scope") or "")
        for term in ("metadata-only", "no identity", "no lookup", "no handle", "no cross-event correlation", "no mutation"):
            if term not in scope:
                add(blockers, "resource_descriptor_scope_guardrail_missing", f"{label}.metadata_surfaces.resource_kind.scope", term=term, value=scope)
        flags = set(resource_descriptor.get("flags") or [])
        required_flags = {
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_CATEGORY_ONLY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
            "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
        }
        if not required_flags.issubset(flags):
            add(
                blockers,
                "resource_descriptor_category_only_flags_missing",
                f"{label}.metadata_surfaces.resource_kind.flags",
                missing=sorted(required_flags - flags),
            )

    inventory_kind = find_inventory_resource_kind(payload)
    if not isinstance(inventory_kind, dict):
        add(blockers, "inventory_resource_kind_descriptor_missing", f"{label}.metadata_surfaces.resource_kinds")
    else:
        require_equal(inventory_kind, "stable_name", "inventory_item", f"{label}.resource_kinds.inventory_item", blockers)
        require_equal(inventory_kind, "supported_gameplay_policy_event_mask", ALL_INVENTORY_MASK, f"{label}.resource_kinds.inventory_item", blockers)
        actual_fields = set(inventory_kind.get("supported_gameplay_policy_field_mask") or [])
        if actual_fields != EXPECTED_SIGNAL_FIELDS:
            add(
                blockers,
                "inventory_resource_kind_supported_fields_mismatch",
                f"{label}.resource_kinds.inventory_item.supported_gameplay_policy_field_mask",
                expected=sorted(EXPECTED_SIGNAL_FIELDS),
                value=sorted(actual_fields),
            )

    scan_public_claim_terms(payload, blockers, label)
    scan_readiness_claims(payload, blockers, label)
    return {
        "inventory_event_kinds": sorted(item["kind"] for item in actual if item.get("kind")),
        "promoted_experimental_outcomes": promoted_experimental_outcomes,
    }


def validate_public_sdk_surfaces(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_sdk_surfaces"
    require_equal(payload, "schema", PUBLIC_SDK_SURFACES_SCHEMA, label, blockers)
    require_false(payload, "v1_completion_required", label, blockers)
    stable_contract = payload.get("stable_release_contract")
    if not isinstance(stable_contract, dict):
        add(blockers, "stable_release_contract_missing", f"{label}.stable_release_contract")
    else:
        require_false(stable_contract, "claim_allowed", f"{label}.stable_release_contract", blockers)

    promoted = set(payload.get("promoted_surfaces") or [])
    experimental = set(payload.get("experimental_surfaces") or [])
    if SURFACE in promoted:
        add(blockers, "inventory_copied_surface_in_promoted_surfaces", f"{label}.promoted_surfaces")
    if SURFACE not in experimental:
        add(blockers, "inventory_copied_surface_missing_from_experimental_surfaces", f"{label}.experimental_surfaces")

    surface = find_surface(payload, SURFACE)
    if surface is None:
        add(blockers, "inventory_copied_surface_missing", f"{label}.surfaces")
    else:
        require_equal(surface, "status", "promoted-experimental-only", f"{label}.{SURFACE}", blockers)
        require_equal(surface, "support_tier", "promoted-experimental-only copied-data seed", f"{label}.{SURFACE}", blockers)
        if list(surface.get("public_contract") or []) != list(EXPECTED_PUBLIC_CONTRACT):
            add(
                blockers,
                "inventory_copied_surface_public_contract_mismatch",
                f"{label}.{SURFACE}.public_contract",
                expected=list(EXPECTED_PUBLIC_CONTRACT),
                value=surface.get("public_contract"),
            )
        payload_contract = tuple(surface.get("payload_contract") or [])
        if payload_contract != EXPECTED_SURFACE_PAYLOAD_CONTRACT:
            add(
                blockers,
                "inventory_copied_payload_contract_mismatch",
                f"{label}.{SURFACE}.payload_contract",
                expected=list(EXPECTED_SURFACE_PAYLOAD_CONTRACT),
                value=list(payload_contract),
            )
        exclusions = set(surface.get("exclusions") or [])
        missing = sorted(REQUIRED_FORBIDDEN_TERMS - exclusions)
        if missing:
            add(blockers, "inventory_copied_surface_exclusions_missing", f"{label}.{SURFACE}.exclusions", missing=missing)
        evidence = surface.get("evidence")
        if not isinstance(evidence, dict):
            add(blockers, "inventory_copied_surface_evidence_missing", f"{label}.{SURFACE}.evidence")
        else:
            readiness_target_sets = tuple(evidence.get("release_readiness_target_sets") or [])
            if readiness_target_sets != EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS:
                add(
                    blockers,
                    "inventory_copied_release_readiness_target_sets_mismatch",
                    f"{label}.{SURFACE}.evidence.release_readiness_target_sets",
                    expected=list(EXPECTED_INVENTORY_RELEASE_READINESS_TARGET_SETS),
                    value=list(readiness_target_sets),
                )
        scan_public_claim_terms(surface, blockers, f"{label}.{SURFACE}")

    mutation_surface = find_surface(payload, INVENTORY_MUTATION_SURFACE)
    if mutation_surface is None:
        add(blockers, "inventory_mutation_surface_missing", f"{label}.surfaces")
    else:
        require_equal(mutation_surface, "status", "post-v1", f"{label}.{INVENTORY_MUTATION_SURFACE}", blockers)
        if mutation_surface.get("public_contract") not in ([], None):
            add(
                blockers,
                "inventory_mutation_surface_public_contract_not_empty",
                f"{label}.{INVENTORY_MUTATION_SURFACE}.public_contract",
                value=mutation_surface.get("public_contract"),
            )

    resource_handle_surface = find_surface(payload, RESOURCE_HANDLE_SURFACE)
    if resource_handle_surface is None:
        add(blockers, "resource_handle_surface_missing", f"{label}.surfaces")
    else:
        require_equal(resource_handle_surface, "status", "post-v1", f"{label}.{RESOURCE_HANDLE_SURFACE}", blockers)
        if resource_handle_surface.get("public_contract") not in ([], None):
            add(
                blockers,
                "resource_handle_surface_public_contract_not_empty",
                f"{label}.{RESOURCE_HANDLE_SURFACE}.public_contract",
                value=resource_handle_surface.get("public_contract"),
            )

    scan_public_sdk_surfaces_inventory_side_lane_claims(payload, blockers, label)
    scan_readiness_claims(payload, blockers, label)
    return {"inventory_copied_status": surface.get("status") if isinstance(surface, dict) else None}


def scan_readiness_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    trail: str,
    *,
    claim_context: bool = False,
) -> None:
    forbidden_true_keys = {
        "contributes_to_public_sdk_v1",
        "contributes_to_v1_completion",
        "approved_runtime_evidence_accepted",
        "approved_runtime_evidence_missing_cleared",
        "approved_runtime_evidence_missing_resolved",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "clears_approved_runtime_evidence_missing",
        "complete_sdk_claim_progress_contribution",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_for_public_sdk_v1",
        "counts_toward_sdk",
        "counts_toward_complete_sdk",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain_claim",
        "counts_toward_v1_completion",
        "evidence_bundle_accepted",
        "inventory_sdk_ready",
        "items_sdk_ready",
        "live_ops_ready",
        "promotion_ready",
        "public_abi_ready",
        "public_inventory_sdk_ready",
        "public_items_sdk_ready",
        "public_module_ready",
        "public_sdk_ready",
        "release_ready",
        "release_supported",
        "runtime_capture_ready",
        "runtime_ready",
        "source_accepted",
        "source_readiness",
        "source_ready",
        "source_stable",
        "source_status",
        "stable",
        "stable_claim_allowed",
        "stable_sdk_ready",
        "v1_completion_contribution",
        "v1_completion_ready",
        "v1_ready",
        "v1_sdk_ready",
        "p0_dependency_chain_claim_progress_contribution",
        "player_principal_replacement_ready",
        "replaces_player_principal_evidence",
        "replaces_player_principal_triplet",
        "sdk_accounting_counts_as_completed_surface",
        "p0_accounting_counts_as_promoted_surface",
    }
    forbidden_positive_progress_keys = {
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_claim_progress_ratio",
        "sdk_completion_progress_ratio",
        "p0_dependency_chain_claim_progress_contribution",
        "p0_dependency_chain_claim_progress_ratio",
    }
    readiness_text_keys = forbidden_true_keys | forbidden_positive_progress_keys | READINESS_TEXT_SCAN_KEYS
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if key in NEGATIVE_KEYS:
                continue
            normalized_key = normalized_claim_key(str(key))
            key_is_neutral_metadata = neutral_positive_metadata_key(
                normalized_key
            ) or neutral_positive_metadata_path(normalized_key, child_trail)
            stale_readiness_satisfied_alias = stale_readiness_satisfied_alias_key(normalized_key)
            forbidden_path_alias = forbidden_readiness_alias_path(child_trail)
            direct_claim_context = readiness_context_key(str(key)) or stale_readiness_satisfied_alias or forbidden_path_alias
            child_context = claim_context or direct_claim_context
            if normalized_key in forbidden_true_keys and child is True:
                add(blockers, "readiness_claim_enabled", child_trail)
            elif forbidden_path_alias and positive_status_claim(child):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            elif stale_readiness_satisfied_alias and positive_status_claim(child):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            elif normalized_key in SOURCE_READINESS_ALIAS_KEYS and positive_status_claim(child):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            if normalized_key in SOURCE_READINESS_ALIAS_KEYS and isinstance(child, (dict, list)):
                for text_path, text in string_values(child, child_trail):
                    if positive_status_claim(text):
                        add(blockers, "readiness_claim_enabled", text_path, value=text)
            if (
                normalized_key in forbidden_positive_progress_keys
                and positive_progress_claim(child)
            ):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            if (
                child_context
                and not key_is_neutral_metadata
                and readiness_accounting_alias_key(normalized_key)
                and positive_progress_claim(child)
            ):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            if (
                child_context
                and not key_is_neutral_metadata
                and positive_status_claim(child)
                and (
                    direct_claim_context
                    or normalized_key in CONTEXTUAL_READINESS_STATUS_KEYS
                )
            ):
                add(blockers, "readiness_claim_enabled", child_trail, value=child)
            if key in readiness_text_keys or normalized_key in readiness_text_keys:
                for text_path, text in string_values(child, child_trail):
                    for phrase in POSITIVE_READINESS_PHRASES:
                        match = flexible_phrase_match(text, phrase)
                        if not match:
                            continue
                        if is_negated_for_match(text, match.start(), match.end()):
                            continue
                        if phrase == "release-supported" and key == "support_tier":
                            continue
                        add(blockers, "readiness_claim_enabled", text_path, value=text, term=phrase)
                        break
            scan_readiness_claims(
                child,
                blockers,
                child_trail,
                claim_context=child_context or propagates_readiness_claim_context(normalized_key),
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_readiness_claims(child, blockers, f"{trail}[{index}]", claim_context=claim_context)
    elif claim_context and positive_status_claim(value):
        leaf_key = normalized_trail_leaf_key(trail)
        if not neutral_positive_metadata_key(leaf_key) and not neutral_positive_metadata_path(leaf_key, trail):
            add(blockers, "readiness_claim_enabled", trail, value=value)


def extract_define_symbols(text: str) -> set[str]:
    return set(re.findall(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\b", text, flags=re.MULTILINE))


def extract_define_body(text: str, symbol: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.match(rf"\s*#\s*define\s+{re.escape(symbol)}\b", line):
            continue
        body_lines = [line]
        cursor = index
        while body_lines[-1].rstrip().endswith("\\") and cursor + 1 < len(lines):
            cursor += 1
            body_lines.append(lines[cursor])
        return "\n".join(body_lines)
    return ""


def extract_shift_define_value(text: str, symbol: str) -> int | None:
    body = extract_define_body(text, symbol)
    if not body:
        return None
    match = re.search(
        rf"^\s*#\s*define\s+{re.escape(symbol)}\s+\(?\s*1(?:u|U)?(?:ll|LL|l|L)?\s*<<\s*(\d+)\s*\)?",
        body,
        flags=re.MULTILINE,
    )
    return int(match.group(1)) if match else None


def extract_enum_assignment_value(text: str, symbol: str) -> int | None:
    match = re.search(rf"\b{re.escape(symbol)}\s*=\s*(\d+)\s*,", text)
    return int(match.group(1)) if match else None


def validate_public_header(path: Path, decisions: dict[str, Any] | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    label = "$.public_header"
    try:
        reject_symlink_component(path, "public_header")
        resolved = reject_protected_input_path(path, "public_header")
        raw_text = resolved.read_text(encoding="utf-8")
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", label, path=str(path), error=str(exc))
        return {"inventory_event_kinds": []}
    except OSError as exc:
        add(blockers, "public_header_unreadable", label, path=str(path), error=str(exc))
        return {"inventory_event_kinds": []}

    code = strip_c_comments(raw_text)
    define_symbols = extract_define_symbols(code)
    event_kinds = set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_KIND_INVENTORY_[A-Z0-9_]+)\b", code))
    event_masks = set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_[A-Z0-9_]+)\b", code))

    if event_kinds != EXPECTED_SIGNAL_KINDS:
        add(
            blockers,
            "public_header_inventory_event_kinds_mismatch",
            label,
            expected=sorted(EXPECTED_SIGNAL_KINDS),
            value=sorted(event_kinds),
        )

    if event_masks != set(EXPECTED_SIGNAL_MASKS):
        add(
            blockers,
            "public_header_inventory_event_masks_mismatch",
            label,
            expected=sorted(EXPECTED_SIGNAL_MASKS),
            value=sorted(event_masks),
        )

    all_inventory_body = extract_define_body(code, ALL_INVENTORY_MASK)
    for mask in EXPECTED_SIGNAL_MASKS:
        if mask not in all_inventory_body:
            add(blockers, "public_header_all_inventory_mask_missing_signal", label, mask=mask)
    extra_masks_in_all = sorted(set(re.findall(r"\b(OBELISK_GAMEPLAY_POLICY_EVENT_MASK_INVENTORY_[A-Z0-9_]+)\b", all_inventory_body)) - EXPECTED_SIGNAL_MASKS - {ALL_INVENTORY_MASK})
    if extra_masks_in_all:
        add(blockers, "public_header_all_inventory_mask_extra_signal", label, extra=extra_masks_in_all)

    missing_defines = sorted((EXPECTED_SIGNAL_MASKS | {ALL_INVENTORY_MASK}) - define_symbols)
    if missing_defines:
        add(blockers, "public_header_expected_inventory_mask_defines_missing", label, missing=missing_defines)

    for symbol, expected_value in EXPECTED_SIGNAL_KIND_VALUES.items():
        observed = extract_enum_assignment_value(code, symbol)
        if observed != expected_value:
            add(
                blockers,
                "public_header_inventory_event_kind_value_mismatch",
                label,
                symbol=symbol,
                expected=expected_value,
                value=observed,
            )

    for symbol, expected_shift in EXPECTED_SIGNAL_MASK_SHIFTS.items():
        observed = extract_shift_define_value(code, symbol)
        if observed != expected_shift:
            add(
                blockers,
                "public_header_inventory_event_mask_value_mismatch",
                label,
                symbol=symbol,
                expected_shift=expected_shift,
                value=observed,
            )

    for symbol, expected_shift in EXPECTED_FIELD_MASK_SHIFTS.items():
        observed = extract_shift_define_value(code, symbol)
        if observed != expected_shift:
            add(
                blockers,
                "public_header_inventory_field_mask_value_mismatch",
                label,
                symbol=symbol,
                expected_shift=expected_shift,
                value=observed,
            )

    for symbol, expected_value in EXPECTED_RESOURCE_KIND_VALUES.items():
        observed = extract_enum_assignment_value(code, symbol)
        if observed != expected_value:
            add(
                blockers,
                "public_header_inventory_resource_kind_value_mismatch",
                label,
                symbol=symbol,
                expected=expected_value,
                value=observed,
            )

    for term in REQUIRED_FORBIDDEN_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", code, re.IGNORECASE):
            add(blockers, "public_header_forbidden_inventory_claim_token", label, term=term)

    missing_listed_symbols: list[str] = []
    if decisions is not None:
        for symbol in decisions.get("public_header_symbols_now") or []:
            if not re.search(rf"\b{re.escape(str(symbol))}\b", code):
                missing_listed_symbols.append(str(symbol))
    if missing_listed_symbols:
        add(blockers, "public_header_symbols_now_missing_from_header", label, missing=sorted(missing_listed_symbols))

    return {"inventory_event_kinds": sorted(event_kinds), "inventory_event_masks": sorted(event_masks)}


def build_multi_surface_beta_capture_guardrail() -> dict[str, Any]:
    return {
        "status": "candidate_only_non_counting",
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_first_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "sdk_p0_unlock_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "public_sdk_ready": False,
        "public_module_ready": False,
        "stable_claim_allowed": False,
        "v1_completion_ready": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "non_claim": (
            "candidate multi-surface beta capture pack/plan artifacts are prep only; "
            "they do not satisfy approved player-principal runtime evidence"
        ),
    }


def build_report(
    decisions_path: Path,
    public_sdk_surfaces_path: Path,
    public_gameplay_events_path: Path,
    public_header_path: Path,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    decisions = load_json(decisions_path, "decisions", blockers)
    public_sdk_surfaces = load_json(public_sdk_surfaces_path, "public_sdk_surfaces", blockers)
    public_gameplay_events = load_json(public_gameplay_events_path, "public_gameplay_events", blockers)

    summaries: dict[str, Any] = {}
    if decisions is not None:
        summaries["decisions"] = validate_decisions(decisions, blockers)
    if public_gameplay_events is not None:
        summaries["public_gameplay_events"] = validate_public_gameplay_events(public_gameplay_events, blockers)
    if public_sdk_surfaces is not None:
        summaries["public_sdk_surfaces"] = validate_public_sdk_surfaces(public_sdk_surfaces, blockers)
    summaries["public_header"] = validate_public_header(public_header_path, decisions, blockers)

    non_counting_accounting = dict(NON_COUNTING_ACCOUNTING)
    beta_capture_guardrail = build_multi_surface_beta_capture_guardrail()
    readiness_report = dict(READINESS_TRUTHFULNESS_REPORT)
    readiness_report["input_guardrails_passed"] = not blockers
    promoted_experimental_outcome_gate = {
        "status": "fail_closed_unresolved_promoted_experimental_surfaces",
        "unresolved_surfaces": list(PROMOTED_EXPERIMENTAL_SURFACE_IDS),
        "allowed_resolutions": list(PROMOTED_EXPERIMENTAL_ALLOWED_RESOLUTIONS),
        "complete_sdk_accounting": PROMOTED_EXPERIMENTAL_COMPLETE_SDK_ACCOUNTING,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "stable_claim_allowed": False,
        "v1_completion_ready": False,
        "must_not_unlock": list(PROMOTED_EXPERIMENTAL_MUST_NOT_UNLOCK),
    }
    return {
        "schema": REPORT_SCHEMA,
        "ready": not blockers,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "surface": SURFACE,
        "accepted_for_internal_planning": not blockers,
        "offline_only": True,
        "candidate_only": True,
        "not_artifact_gate": True,
        **non_counting_accounting,
        "promoted_experimental_outcome_gate": promoted_experimental_outcome_gate,
        "multi_surface_beta_capture_guardrail": beta_capture_guardrail,
        "readiness_report": readiness_report,
        "next_blockers": NEXT_BLOCKERS,
        "inputs": {
            "decisions": str(decisions_path),
            "public_sdk_surfaces": str(public_sdk_surfaces_path),
            "public_gameplay_events": str(public_gameplay_events_path),
            "public_header": str(public_header_path),
        },
        "summary": {
            "allowed_signal_count": len(EXPECTED_ALLOWED_SIGNALS),
            "allowed_signal_kinds": sorted(EXPECTED_SIGNAL_KINDS),
            "allowed_signal_masks": sorted(EXPECTED_SIGNAL_MASKS),
            "accepted_for_internal_planning": not blockers,
            "candidate_only": True,
            "offline_only": True,
            "not_artifact_gate": True,
            "ready_scope": NON_AUTHORIZING_READY_SCOPE,
            "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
            "resource_kind_contract": "category-only metadata",
            "current_route_blocker": CURRENT_ROUTE_BLOCKER,
            "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
            "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
            "multi_surface_beta_capture_guardrail": beta_capture_guardrail,
            "promoted_experimental_outcome_gate": promoted_experimental_outcome_gate,
            "readiness_report": readiness_report,
            "next_blockers": NEXT_BLOCKERS,
            **non_counting_accounting,
        },
        "checks": summaries,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = build_report(
        args.decisions,
        args.public_sdk_surfaces,
        args.public_gameplay_events,
        args.public_header,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
