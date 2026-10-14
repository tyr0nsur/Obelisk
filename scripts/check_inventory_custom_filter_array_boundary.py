#!/usr/bin/env python3
"""Candidate-only boundary checker for InventoryCustomFilter array metadata."""

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
    PLANNING_ONLY_TARGET_SETS,
    RELEASE_READINESS_TARGET_SETS,
    TARGET_SETS,
    schema_target_list,
    side_lane_fail_closed_source_artifact_issues,
    target_set_module_lane,
    target_set_readiness_classification,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component  # noqa: E402


REPORT_SCHEMA = "obelisk.inventory-custom-filter-array-boundary-check.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
PUBLIC_SDK_SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PUBLIC_GAMEPLAY_EVENTS_SCHEMA = "obelisk.public-gameplay-events.v1"
EXPECTED_PUBLIC_JSON_SCHEMAS = {
    "public_sdk_surfaces": PUBLIC_SDK_SURFACES_SCHEMA,
    "public_gameplay_events": PUBLIC_GAMEPLAY_EVENTS_SCHEMA,
}
TARGET_SET = "inventory-custom-filter-array-boundary"
TARGET = "PrimalInventoryComponent.InventoryCustomFilter"
DEFAULT_SNAPSHOT = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "ufunction_snapshots"
    / "7e7ded49e0c6"
    / "sdk_inventory"
    / "PrimalInventoryComponent.InventoryCustomFilter.snapshot.json"
)
DEFAULT_PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PUBLIC_GAMEPLAY_EVENTS = REPO_ROOT / "docs" / "public_gameplay_events.json"
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

EXPECTED_FUNCTION = {
    "outer_name": "PrimalInventoryComponent",
    "function_name": "InventoryCustomFilter",
    "function_flags": "0xc420c00",
    "num_parms": 2,
    "parms_size": 32,
    "return_value_offset": "0xffff",
}
EXPECTED_PARAMS = (
    {
        "name": "UnfilteredItemsList",
        "class_name": "ArrayProperty",
        "inner_class_name": "ObjectProperty",
        "offset_internal": 0,
        "element_size": 16,
        "array_dim": 1,
        "property_flags": "0x8000382",
    },
    {
        "name": "FilteredItemsList",
        "class_name": "ArrayProperty",
        "inner_class_name": "ObjectProperty",
        "offset_internal": 16,
        "element_size": 16,
        "array_dim": 1,
        "property_flags": "0x380",
    },
)
EXPECTED_ARRAY_BOUNDARIES = (
    {
        "name": "UnfilteredItemsList",
        "offset_internal": 0,
        "element_size": 16,
        "array_dim": 1,
        "end_offset": 16,
    },
    {
        "name": "FilteredItemsList",
        "offset_internal": 16,
        "element_size": 16,
        "array_dim": 1,
        "end_offset": 32,
    },
)
FALSE_READINESS_FLAGS = (
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "approved_runtime_evidence_substitution_allowed",
    "authorizes_discord_send",
    "authorizes_live_log_reads",
    "authorizes_marker_or_env_changes",
    "authorizes_player_backed_window",
    "authorizes_runtime_capture",
    "authorizes_runtime_observer",
    "authorizes_server_restart",
    "clears_approved_runtime_evidence_missing",
    "contributes_to_public_sdk_v1",
    "contributes_to_v1_completion",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_for_p0_dependency_chain",
    "counts_for_public_sdk_v1",
    "side_lane_counts_toward_sdk",
    "side_lane_counts_toward_p0",
    "sdk_p0_unlock_allowed",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk_v1",
    "counts_toward_v1_completion",
    "pack_authorizes_discord",
    "pack_authorizes_marker_or_env_change",
    "pack_authorizes_player_backed_window",
    "pack_authorizes_restart",
    "pack_authorizes_runtime_observer",
    "primary_evidence_substitution_allowed",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "v1_completion_ready",
    "inventory_sdk_ready",
    "items_sdk_ready",
    "live_ops_ready",
    "lookup_ready",
    "player_principal_replacement_ready",
    "complete_sdk_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_contract_ready",
    "public_inventory_sdk_ready",
    "public_module_ready",
    "resource_handle_public_contract_ready",
    "resource_handle_ready",
    "mutation_ready",
    "return_override_ready",
    "runtime_capture_ready",
    "runtime_validated",
    "sdk_runtime_ready",
    "stable_sdk_ready",
    "replaces_player_principal_evidence",
    "replaces_player_principal_triplet",
    "player_principal_lifecycle_evidence_substitution_allowed",
    "side_lane_collection_can_replace_player_principal_evidence",
    "side_lane_collection_counts_before_checker_acceptance",
    "side_lane_substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_evidence",
    "substitutes_for_player_principal_lifecycle_triplet",
)
ZERO_ACCOUNTING_FIELDS = {
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "v1_completion_progress_contribution": 0,
}
READINESS_TRUTHFULNESS_REPORT: dict[str, Any] = {
    "ready_field_semantics": "non_authorizing_candidate_boundary_passed_only",
    "ready_means": (
        "the committed InventoryCustomFilter fixture still proves only redacted "
        "ArrayProperty byte boundaries"
    ),
    "ready_does_not_mean": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
    "public_inventory_sdk_claim_allowed": False,
    "public_items_sdk_claim_allowed": False,
    "array_payload_claim_allowed": False,
    "runtime_readiness_claim_allowed": False,
    "v1_completion_claim_allowed": False,
    "v1_progress_contribution": 0,
    "current_route_blocker": CURRENT_ROUTE_BLOCKER,
    "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
    "multi_surface_beta_capture_counts_as_approved_runtime_evidence": False,
    "primary_evidence_substitution_allowed": False,
    "side_lane_substitution_claim_allowed": False,
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
        "id": "array_payload_intentionally_redacted_boundary_only",
        "blocked_for_public_inventory_sdk": True,
        "current_side_lane_status": (
            "two reflected TArray parameter shells only; data pointer/count/capacity "
            "and element identity are redacted"
        ),
        "required_future_evidence": [
            "separate reflected copied-payload contract if an array surface is ever proposed",
            "proof that raw TArray ranges, AdditionalData, identity, lookup, and ResourceHandle stay hidden",
            "append-only ABI layout and SDK consumer tests for any promoted array payload",
        ],
    },
    "runtime": {
        "id": "runtime_array_lifetime_and_identity_evidence_missing",
        "blocked_for_public_inventory_sdk": True,
        "required_future_evidence": [
            "approved runtime capture for array lifetime/ownership semantics",
            "object identity and ResourceHandle validity/reuse evidence",
            "callback-scope versus post-callback validity rules",
        ],
        "blocked_claims": [
            "Inventory SDK",
            "Items SDK",
            "identity",
            "mutation",
            "return override",
            "ResourceHandle",
            "v1 completion",
        ],
    },
}
FORBIDDEN_TRUE_READY_KEYS = frozenset(
    (
        "array_payload_ready",
        "approved_runtime_evidence_substitution_allowed",
        "authorization_claim_allowed",
        "authorization_ready",
        "authorizes_discord_send",
        "authorizes_live_log_reads",
        "authorizes_marker_or_env_changes",
        "authorizes_player_backed_window",
        "authorizes_runtime_capture",
        "authorizes_runtime_observer",
        "authorizes_server_restart",
        "callback_ready",
        "complete_sdk_counting_allowed",
        "counts_for_p0_dependency_chain",
        "counts_for_public_sdk_v1",
        "countsforpublicsdkv1",
        "countstowardcompletesdk",
        "countstowardcompletesdkclaim",
        "counts_toward_complete_sdk",
        "counts_toward_complete_sdk_claim",
        "counts_toward_v1_completion",
        "countstowardv1completion",
        "contributes_to_public_sdk_v1",
        "contributestopublicsdkv1",
        "contributes_to_v1_completion",
        "contributestov1completion",
        "copied_array_ready",
        "copied_list_ready",
        "inventory_sdk_ready",
        "mutation_ready",
        "package_shape_ready",
        "pack_authorizes_discord",
        "pack_authorizes_marker_or_env_change",
        "pack_authorizes_player_backed_window",
        "pack_authorizes_restart",
        "pack_authorizes_runtime_observer",
        "player_principal_lifecycle_evidence_substitution_allowed",
        "plugin_hub_ready",
        "primary_evidence_substitution_allowed",
        "promotion_ready",
        "public_module_ready",
        "public_api_ready",
        "public_inventory_sdk_ready",
        "public_sdk_ready",
        "resource_handle_ready",
        "return_override_ready",
        "runtime_capture_ready",
        "runtime_ready",
        "live_ops_ready",
        "sdk_ready",
        "source_readiness",
        "source_ready",
        "stable_sdk_ready",
        "side_lane_collection_can_replace_player_principal_evidence",
        "side_lane_collection_counts_before_checker_acceptance",
        "side_lane_substitutes_for_player_principal_lifecycle_evidence",
        "substitutes_for_player_principal_lifecycle_evidence",
        "substitutes_for_player_principal_lifecycle_triplet",
        "v1_completion_contribution",
        "v1completioncontribution",
        "v1_completion_evidence",
        "v1_completion_required",
        "v1_completion_ready",
        "v1_ready",
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
        "side_lane_substitutes_for_player_principal_lifecycle_evidence",
        "static_evidence_validated",
        "substitutes_for_player_principal_lifecycle_evidence",
        "substitutes_for_player_principal_lifecycle_triplet",
        "support_tier_active",
        "target_set_promoted",
        "transfer_runtime_ready",
        "v1_complete",
    )
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
        "true",
        "validated",
        "v1-ready",
    )
) | POSITIVE_STATUS_SHORTCUT_VALUES
CLAIM_CONTEXT_KEY_RE = re.compile(
    r"(?:public|sdk|api|abi|module|runtime|capture|live[_-]?ops|source|v1|p0|"
    r"complete|completion|stable|promotion|resource[_-]?handle|return[_-]?override|"
    r"identity|lookup|mutation|support[_-]?tier|package[_-]?shape|plugin[_-]?hub|"
    r"player[_-]?principal|primary[_-]?evidence|approved[_-]?runtime[_-]?evidence|"
    r"side[_-]?lane|substitut|authoriz)",
    re.IGNORECASE,
)
CONTRACT_KEYS = frozenset(
    (
        "abi_contract",
        "capability",
        "capabilities",
        "descriptor_fields",
        "event_kinds",
        "payload_contract",
        "public_abi",
        "public_api",
        "public_contract",
        "public_fields",
        "resource_contract",
        "sdk_contract",
    )
)
FORBIDDEN_PUBLIC_TOKENS = (
    "PrimalInventoryComponent.InventoryCustomFilter",
    "PrimalInventoryComponent",
    "InventoryCustomFilter",
    "UnfilteredItemsList",
    "FilteredItemsList",
    "inventory-custom-filter-array-boundary",
    "inventory_custom_filter",
    "inventory.custom_filter",
    "inventory custom filter",
)
COPIED_ARRAY_KEY_TOKENS = (
    "copied_array",
    "copied_list",
    "copied_payload",
    "copied_range",
    "copiedrange",
    "copied_ranges",
    "exposed_range",
    "exposedrange",
    "exposes_range",
    "exposesrange",
    "payload_range",
    "payloadrange",
    "payload_ranges",
    "public_payload",
    "tarray_copy",
)
COPIED_ARRAY_STRING_TOKENS = (
    "copied array",
    "copied list",
    "copied tarray",
    "public array payload",
    "tarray copy",
)
FORBIDDEN_SNAPSHOT_EXPOSURE_KEY_TOKENS = (
    "additional_data",
    "additionaldata",
    "raw_array",
    "raw_arrays",
    "raw_param",
    "raw_params",
    "raw_range",
    "raw_ranges",
    "raw_tarray",
    "array_range",
    "arrayrange",
    "array_ranges",
    "data_pointer",
    "data_ptr",
    "exposed_range",
    "exposedrange",
    "exposed_ranges",
    "exposes_range",
    "exposesrange",
    "inventory_handle",
    "inventory_identity",
    "inventoryhandle",
    "item_handle",
    "item_identity",
    "item_id",
    "itemhandle",
    "itemid",
    "itemid1",
    "itemnetid",
    "native_pointer",
    "param_range",
    "paramrange",
    "param_ranges",
    "parameter_range",
    "parameterrange",
    "parameter_ranges",
    "payload_range",
    "payloadrange",
    "payload_ranges",
    "pointer_range",
    "pointerrange",
    "range_data",
    "rangedata",
    "range_pointer",
    "rangepointer",
    "range_start",
    "rangestart",
    "resource_handle",
    "resourcehandle",
    "uobject_pointer",
    "ue_pointer",
)
FORBIDDEN_SNAPSHOT_EXPOSURE_STRING_TOKENS = (
    "AdditionalData",
    "inventory handle",
    "inventory identity",
    "ItemHandle",
    "item handle",
    "item identity",
    "ItemId",
    "ItemID1",
    "ItemNetID",
    "native pointer",
    "parameter range",
    "raw array",
    "raw params",
    "raw range",
    "raw TArray",
    "ResourceHandle",
    "resource handle",
    "lookup",
    "mutation",
    "return override",
    "runtime ready",
    "runtime readiness",
    "TArray pointer",
    "UObject pointer",
    "UE pointer",
    "v1 completion",
    "v1 completion ready",
)
FORBIDDEN_ARRAY_PAYLOAD_BOUNDARY_KEY_TOKENS = (
    "array_capacity",
    "array_count",
    "array_data",
    "array_data_ptr",
    "array_data_pointer",
    "arraydatapointer",
    "array_element_range",
    "arrayelementrange",
    "array_elements",
    "array_max",
    "arraymax",
    "array_num",
    "arraynum",
    "array_payload_boundary",
    "arraypayloadboundary",
    "array_storage",
    "array_typed_range",
    "arraytypedrange",
    "array_value",
    "array_values",
    "arraypayloadvalue",
    "arraypayloadvalues",
    "array_payload_value",
    "array_payload_values",
    "data_address",
    "dataaddress",
    "data_offset",
    "dataoffset",
    "data_ptr",
    "dataptr",
    "data_pointer",
    "datapointer",
    "element_count",
    "elementcount",
    "element_bytes",
    "element_value",
    "element_values",
    "elementbytes",
    "element_range",
    "elementrange",
    "elements_range",
    "elementsrange",
    "elementvalue",
    "elementvalues",
    "first_element",
    "firstelement",
    "max_offset",
    "maxoffset",
    "num_offset",
    "numoffset",
    "tarray_capacity",
    "tarraycapacity",
    "tarray_count",
    "tarraycount",
    "tarray_data",
    "tarraydata",
    "tarray_value",
    "tarray_values",
    "tarrayvalue",
    "tarrayvalues",
    "observed_array_value",
    "observed_array_values",
    "observedarrayvalue",
    "observedarrayvalues",
    "sample_array_value",
    "sample_array_values",
    "samplearrayvalue",
    "samplearrayvalues",
    "tarray_header",
    "tarrayheader",
    "tarray_max",
    "tarraymax",
    "tarray_num",
    "tarraynum",
    "unsafe_array_boundary",
)
FORBIDDEN_ARRAY_PAYLOAD_BOUNDARY_STRING_TOKENS = (
    "array capacity",
    "array count",
    "array data pointer",
    "array element range",
    "array values",
    "array payload boundary",
    "array payload values",
    "array storage",
    "borrowed TArray",
    "element count",
    "element range",
    "element values",
    "observed array values",
    "sample array values",
    "TArray data",
    "TArray header",
    "TArray values",
)
PUBLIC_POSITIVE_CLAIM_TERMS = (
    "AdditionalData",
    "AdditionalData API",
    "contributes to public SDK v1",
    "contributes to v1 completion",
    "counts for public SDK v1",
    "counts toward complete SDK",
    "counts toward v1 completion",
    "countsForPublicSdkV1",
    "countsTowardCompleteSdkClaim",
    "countsTowardV1Completion",
    "counts_for_public_sdk_v1",
    "counts_toward_complete_sdk",
    "counts_toward_v1_completion",
    "identity",
    "Inventory SDK",
    "inventory mutation",
    "Items SDK",
    "ItemId",
    "ItemID1",
    "ItemNetID",
    "package shape",
    "Plugin Hub",
    "ResourceHandle",
    "resource handle",
    "inventory handle",
    "inventory identity",
    "item handle",
    "item identity",
    "item mutation",
    "lookup",
    "mutation",
    "public SDK",
    "raw array",
    "raw params",
    "raw range",
    "return override",
    "runtime support",
    "runtime ready",
    "runtime readiness",
    "runtime/v1 support",
    "support tier",
    "v1 completion contribution",
    "v1 support",
)
PUBLIC_CLAIM_SCAN_KEYS = CONTRACT_KEYS | frozenset(
    (
        "alias",
        "aliases",
        "claim",
        "claims",
        "description",
        "event_contract",
        "note",
        "notes",
        "public_name",
        "readiness",
        "readiness_alias",
        "readiness_aliases",
        "readiness_claim",
        "readiness_claims",
        "release_claim",
        "release_note",
        "report_section",
        "report_sections",
        "resource_contract",
        "review_note",
        "review_notes",
        "scope",
        "source_marker",
        "source_markers",
        "status",
        "summary",
        "support_tier",
    )
)
PUBLIC_CLAIM_CONTEXT_TOKENS = (
    "AdditionalData",
    "FilteredItemsList",
    "Inventory SDK",
    "InventoryCustomFilter",
    "ItemID1",
    "ItemId",
    "ItemNetID",
    "Items SDK",
    "package shape",
    "Plugin Hub",
    "PrimalInventoryComponent",
    "resource handle",
    "support tier",
    "UnfilteredItemsList",
    "inventory",
    "inventory-custom-filter-array-boundary",
    "inventory.custom_filter",
    "inventory_custom_filter",
    "item",
    "raw array",
    "raw params",
    "raw range",
)
PUBLIC_CLAIM_CONTEXT_KEYS = frozenset(
    (
        "category",
        "event_id",
        "id",
        "public_name",
        "stable_name",
        "surface",
        "target_set",
        "target_sets",
    )
)
NEGATIVE_KEYS = frozenset(
    (
        "blockers",
        "exclusions",
        "forbidden_terms",
        "guardrails",
        "must_not_unlock",
        "non_claim",
        "non_claims",
        "not_promoted",
        "redacted_fields",
    )
)
NEGATED_OR_BOUNDARY_RE = re.compile(
    r"\b(?:"
    r"blocked|cannot|candidate-only|does\s+not|do\s+not|excluded|excludes?|"
    r"future|metadata-only|must\s+not|no|non-completion|non-promoting|not|only|"
    r"planning-only|post-v1|prevent|prevents|redacted|remain|remains|without"
    r")\b",
    re.IGNORECASE,
)
CLAUSE_SPLIT_RE = re.compile(r"[,.;:\n\r]+")
NEGATION_LIST_SCOPE_SPLIT_RE = re.compile(r"[.;:\n\r]+")
POSITIVE_TERM_SUFFIX_RE = re.compile(
    r"^\s+(?:api|available|enabled|exposes?|live|operational|promoted|provides?|"
    r"public|ready|readiness|stable|supported|ok|green|go|pass(?:ed)?|"
    r"ship(?:ped)?|done|yes|valid(?:ated)?|verified|unblocked)\b",
    re.IGNORECASE,
)
NEGATIVE_TERM_SUFFIX_RE = re.compile(
    r"^\s+(?:"
    r"is\s+)?(?:blocked|candidate-only|excluded|metadata-only|not\b|redacted|"
    r"remains?\s+(?:blocked|candidate-only|excluded|metadata-only|redacted)|"
    r"stays?\s+(?:blocked|candidate-only|excluded|metadata-only|redacted)|without\b"
    r")",
    re.IGNORECASE,
)
REQUIRED_NON_CLAIM_TOKENS = (
    "non-P0",
    "candidate-only",
    "not an Inventory SDK",
    "no public Inventory/Items SDK",
    "no AdditionalData",
    "no raw arrays",
    "no item identity",
    "no public API",
    "no ResourceHandle",
    "no mutation",
    "no return override",
    "no runtime readiness",
    "no v1 completion",
)
NON_CLAIMS = [
    "non-P0 candidate-only inventory array side-lane audit; no v1 completion or priority promotion",
    "not an Inventory SDK or Items SDK; no public Inventory/Items SDK, no public API, public callback, public ABI, or public payload contract",
    "no AdditionalData exposure, no raw arrays/ranges, no copied array/list payload, and no copied scalars",
    "no item identity, no ResourceHandle, no identity, no lookup, no mutation, no return override, and no runtime readiness",
]
BLOCKED_PROMOTION_CLAIMS = (
    "Inventory SDK",
    "Items SDK",
    "identity",
    "mutation",
    "return override",
    "ResourceHandle",
    "v1 completion",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the committed InventoryCustomFilter ArrayProperty snapshot remains "
            "candidate-only, redacted, non-P0, and non-promoting."
        )
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT, help="Sanitized UFunction snapshot.")
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=DEFAULT_PUBLIC_SDK_SURFACES,
        help="Public SDK surfaces manifest to scan for custom-filter leaks.",
    )
    parser.add_argument(
        "--public-gameplay-events",
        type=Path,
        default=DEFAULT_PUBLIC_GAMEPLAY_EVENTS,
        help="Public gameplay events manifest to scan for custom-filter leaks.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public Obelisk API header to scan for custom-filter symbols.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def read_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", path=str(path), detail=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", path=str(path))
        return None
    return payload


def value_is_present(value: Any) -> bool:
    return value not in (None, False, "", [], {})


def is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def path_label(path: tuple[str, ...]) -> str:
    return ".".join(path) if path else "<root>"


def normalized_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def forbidden_true_ready_key(key: str) -> bool:
    key_lower = key.lower()
    return any(
        alias in FORBIDDEN_TRUE_READY_KEYS
        for alias in (
            key_lower,
            normalized_claim_key(key),
            re.sub(r"[^a-z0-9]+", "", key_lower),
        )
    )


def forbidden_readiness_alias_path(path: tuple[str, ...]) -> bool:
    normalized_path = normalized_claim_key(".".join(path))
    return any(
        normalized_path == suffix or normalized_path.endswith(f"_{suffix}")
        for suffix in FORBIDDEN_READINESS_ALIAS_PATH_SUFFIXES
    )


def is_positive_status_alias(value: str) -> bool:
    normalized = normalized_claim_key(value).replace("_", "-")
    return (
        normalized in POSITIVE_STATUS_VALUES
        or normalized.endswith("-ready")
    )


def is_positive_readiness_alias_value(value: Any) -> bool:
    return value is True or (isinstance(value, str) and is_positive_status_alias(value))


def is_positive_claim_value(value: Any) -> bool:
    return (
        is_positive_readiness_alias_value(value)
        or (isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0)
    )


SOURCE_STATUS_KEYS = frozenset(
    (
        "source_accepted",
        "source_available",
        "source_outcome",
        "source_readiness",
        "source_ready",
        "source_result",
        "source_stable",
        "source_status",
        "source_support",
        "source_tier",
        "source_validated",
        "source_validation",
    )
)
SOURCE_LABEL_KEYS = frozenset(("source_label", "source_labels"))
SOURCE_MARKER_KEYS = frozenset(("source_marker", "source_markers"))
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
CONTEXTUAL_READINESS_CONTAINER_KEYS = frozenset(
    (
        "candidate",
        "package_shape",
        "plugin_hub",
        "public_sdk",
        "readiness",
        "runtime",
        "support_tier",
        "target_set",
        "v1",
    )
)
CONTEXTUAL_STATUS_ALIAS_SUFFIXES = (
    "_outcome",
    "_readiness",
    "_ready",
    "_result",
    "_stable",
    "_status",
    "_support",
    "_tier",
    "_validated",
    "_validation",
)
CONTEXTUAL_STATUS_ALIAS_SUBJECT_RE = re.compile(
    r"(?:public|sdk|runtime|capture|live_?ops|source|v1|p0|complete|completion|"
    r"stable|resource_?handle|return_?override|identity|lookup|mutation|"
    r"support_?tier|package_?shape|plugin_?hub)",
    re.IGNORECASE,
)
CONTEXTUAL_ACCOUNTING_KEY_TERMS = (
    "contribution",
    "count",
    "counts",
    "progress",
)
NEUTRAL_POSITIVE_METADATA_KEYS = frozenset(
    (
        "array_boundary_count",
        "bound_target_count",
        "copied_array_count",
        "copied_list_count",
        "copied_scalar_count",
        "field_count",
        "param_count",
        "redacted_array_count",
        "source_binding_count",
        "target_count",
        "unsafe_array_boundary_count",
    )
)
NEUTRAL_POSITIVE_METADATA_SUFFIXES = (
    "_boundary_count",
    "_field_count",
    "_target_count",
)


def contains_positive_claim_value(value: Any) -> bool:
    if is_positive_claim_value(value):
        return True
    if isinstance(value, dict):
        return any(contains_positive_claim_value(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_positive_claim_value(child) for child in value)
    return False


def claim_context_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    if normalized == "accepted_for_internal_planning":
        return False
    return normalized in CONTEXTUAL_READINESS_CONTAINER_KEYS or bool(CLAIM_CONTEXT_KEY_RE.search(normalized))


def neutral_positive_metadata_key(key: str) -> bool:
    return key in NEUTRAL_POSITIVE_METADATA_KEYS or any(
        key.endswith(suffix) for suffix in NEUTRAL_POSITIVE_METADATA_SUFFIXES
    )


def readiness_accounting_alias_key(key: str) -> bool:
    return any(term in key for term in CONTEXTUAL_ACCOUNTING_KEY_TERMS)


def contextual_status_alias_key(key: str) -> bool:
    if key.startswith("second_source_"):
        return False
    if key in CONTEXTUAL_READINESS_STATUS_KEYS:
        return True
    return bool(CONTEXTUAL_STATUS_ALIAS_SUBJECT_RE.search(key)) and any(
        key.endswith(suffix) for suffix in CONTEXTUAL_STATUS_ALIAS_SUFFIXES
    )


def normalized_text(value: Any) -> str:
    return json.dumps(value, sort_keys=True).lower() if isinstance(value, (dict, list)) else str(value).lower()


def contains_forbidden_public_token(value: Any) -> bool:
    text = normalized_text(value)
    return any(token.lower() in text for token in FORBIDDEN_PUBLIC_TOKENS)


def text_contains_public_claim_context(text: str) -> bool:
    lower = text.lower()
    for token in PUBLIC_CLAIM_CONTEXT_TOKENS:
        token_lower = token.lower()
        if token_lower in {"inventory", "item"}:
            if re.search(rf"(?<![a-z0-9]){re.escape(token_lower)}(?![a-z0-9])", lower):
                return True
            continue
        if token_lower in lower:
            return True
    return False


def contains_public_claim_context(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() not in PUBLIC_CLAIM_CONTEXT_KEYS:
                continue
            if contains_public_claim_context(child):
                return True
        return False
    if isinstance(value, list):
        return any(
            contains_public_claim_context(child)
            for child in value
            if not isinstance(child, (dict, list))
        )
    return text_contains_public_claim_context(str(value))


def term_matches(text: str, term: str) -> list[re.Match[str]]:
    pattern = re.escape(term).replace(r"\ ", r"[\s_/-]+")
    return list(re.finditer(pattern, text, flags=re.IGNORECASE))


def has_positive_term_suffix(text: str, end: int) -> bool:
    return bool(POSITIVE_TERM_SUFFIX_RE.match(text[end : end + 48]))


def has_negative_term_suffix(text: str, end: int) -> bool:
    return bool(NEGATIVE_TERM_SUFFIX_RE.match(text[end : end + 80]))


def is_negated_for_match(text: str, start: int, end: int) -> bool:
    if has_positive_term_suffix(text, end):
        return False
    if has_negative_term_suffix(text, end):
        return True
    clause_start = 0
    for match in NEGATION_LIST_SCOPE_SPLIT_RE.finditer(text[:start]):
        clause_start = match.end()
    clause = text[clause_start:start]
    if NEGATED_OR_BOUNDARY_RE.search(clause):
        return True
    short_clause_start = clause_start
    for match in CLAUSE_SPLIT_RE.finditer(text[:start]):
        short_clause_start = match.end()
    return bool(NEGATED_OR_BOUNDARY_RE.search(text[short_clause_start:start]))


def positive_term_mentions(text: str, terms: tuple[str, ...]) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    for term in terms:
        for match in term_matches(text, term):
            if is_negated_for_match(text, match.start(), match.end()):
                continue
            mentions.append({"term": term, "value": text})
            break
    return mentions


def collect_copied_array_leaks(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    leaks: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = (*path, str(key))
            if any(token in key_text for token in COPIED_ARRAY_KEY_TOKENS) and value_is_present(child):
                leaks.append({"path": path_label(child_path), "value": child})
            leaks.extend(collect_copied_array_leaks(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(collect_copied_array_leaks(child, (*path, str(index))))
    elif isinstance(value, str):
        text = value.lower()
        if any(token in text for token in COPIED_ARRAY_STRING_TOKENS):
            leaks.append({"path": path_label(path), "value": value})
    return leaks


def collect_forbidden_snapshot_exposures(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    exposures: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = (*path, str(key))
            for token in FORBIDDEN_SNAPSHOT_EXPOSURE_KEY_TOKENS:
                if token in key_text and value_is_present(child):
                    exposures.append({"path": path_label(child_path), "term": token, "value": child})
                    break
            exposures.extend(collect_forbidden_snapshot_exposures(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            exposures.extend(collect_forbidden_snapshot_exposures(child, (*path, str(index))))
    elif isinstance(value, str):
        for mention in positive_term_mentions(value, FORBIDDEN_SNAPSHOT_EXPOSURE_STRING_TOKENS):
            exposures.append({"path": path_label(path), **mention})
    return exposures


def collect_forbidden_array_payload_boundaries(value: Any, path: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    boundaries: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            child_path = (*path, str(key))
            for token in FORBIDDEN_ARRAY_PAYLOAD_BOUNDARY_KEY_TOKENS:
                if token in key_text and value_is_present(child):
                    boundaries.append({"path": path_label(child_path), "term": token, "value": child})
                    break
            boundaries.extend(collect_forbidden_array_payload_boundaries(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            boundaries.extend(collect_forbidden_array_payload_boundaries(child, (*path, str(index))))
    elif isinstance(value, str):
        for mention in positive_term_mentions(value, FORBIDDEN_ARRAY_PAYLOAD_BOUNDARY_STRING_TOKENS):
            boundaries.append({"path": path_label(path), **mention})
    return boundaries


def collect_snapshot_readiness_leaks(
    value: Any,
    path: tuple[str, ...] = (),
    *,
    claim_context: bool = False,
) -> list[dict[str, Any]]:
    leaks: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = (*path, str(key))
            key_lower = str(key).lower()
            normalized_key = normalized_claim_key(str(key))
            forbidden_path_alias = forbidden_readiness_alias_path(child_path)
            child_context = claim_context or claim_context_key(str(key)) or forbidden_path_alias
            if (
                forbidden_true_ready_key(str(key)) and is_positive_readiness_alias_value(child)
            ) or (forbidden_path_alias and is_positive_claim_value(child)):
                leaks.append({"path": path_label(child_path), "value": child})
            if normalized_key in SOURCE_STATUS_KEYS and is_positive_claim_value(child):
                leaks.append({"path": path_label(child_path), "value": child})
            if key_lower == "status" and isinstance(child, str) and is_positive_status_alias(child):
                leaks.append({"path": path_label(child_path), "value": child})
            if (
                child_context
                and contextual_status_alias_key(normalized_key)
                and is_positive_claim_value(child)
            ):
                leaks.append({"path": path_label(child_path), "value": child})
            if (
                child_context
                and readiness_accounting_alias_key(normalized_key)
                and not neutral_positive_metadata_key(normalized_key)
                and is_positive_claim_value(child)
            ):
                leaks.append({"path": path_label(child_path), "value": child})
            if child_context and normalized_key in {"accepted", "ready", "stable"} and is_positive_claim_value(child):
                leaks.append({"path": path_label(child_path), "value": child})
            leaks.extend(collect_snapshot_readiness_leaks(child, child_path, claim_context=child_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(collect_snapshot_readiness_leaks(child, (*path, str(index)), claim_context=claim_context))
    elif claim_context and is_positive_readiness_alias_value(value):
        leaks.append({"path": path_label(path), "value": value})
    return leaks


def target_payload(snapshot: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        add(blockers, "snapshot_schema_mismatch", expected=SNAPSHOT_SCHEMA, value=snapshot.get("schema"))
    targets = snapshot.get("targets")
    if not isinstance(targets, list):
        add(blockers, "snapshot_targets_missing")
        return None
    if len(targets) != 1:
        add(blockers, "snapshot_target_count_mismatch", expected=1, value=len(targets))
        return None
    target = targets[0]
    if not isinstance(target, dict):
        add(blockers, "snapshot_target_not_object")
        return None
    return target


def validate_array_param_boundary(
    prop: dict[str, Any],
    expected: dict[str, Any],
    target_parms_size: Any,
    chain_parms_size: Any,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    param = str(expected["name"])
    field = f"{TARGET}.{param}"
    offset = prop.get("offset_internal")
    element_size = prop.get("element_size")
    array_dim = prop.get("array_dim")
    boundary: dict[str, Any] = {
        "field": field,
        "boundary_kind": "reflected_param_tarray_shell_only",
        "offset_internal": offset,
        "element_size": element_size,
        "array_dim": array_dim,
        "end_offset": None,
        "parms_size": target_parms_size,
        "safe": False,
        "redaction": "TArray parameter shell recognized; data pointer/count/capacity and element identity redacted",
    }
    numeric_values = (
        is_plain_int(offset),
        is_plain_int(element_size),
        is_plain_int(array_dim),
        is_plain_int(target_parms_size),
        is_plain_int(chain_parms_size),
    )
    if not all(numeric_values):
        add(
            blockers,
            "array_param_boundary_non_numeric",
            param=param,
            offset_internal=offset,
            element_size=element_size,
            array_dim=array_dim,
            target_parms_size=target_parms_size,
            chain_parms_size=chain_parms_size,
        )
        return boundary

    span_size = element_size * array_dim
    end_offset = offset + span_size
    boundary["end_offset"] = end_offset
    expected_end_offset = int(expected["offset_internal"]) + int(expected["element_size"]) * int(expected["array_dim"])
    exact = (
        offset == expected["offset_internal"]
        and element_size == expected["element_size"]
        and array_dim == expected["array_dim"]
        and end_offset == expected_end_offset
    )
    if not exact:
        add(
            blockers,
            "array_param_boundary_mismatch",
            param=param,
            expected={
                "offset_internal": expected["offset_internal"],
                "element_size": expected["element_size"],
                "array_dim": expected["array_dim"],
                "end_offset": expected_end_offset,
            },
            value={
                "offset_internal": offset,
                "element_size": element_size,
                "array_dim": array_dim,
                "end_offset": end_offset,
            },
        )
    within_params = offset >= 0 and element_size > 0 and array_dim == 1 and end_offset <= target_parms_size
    within_chain = end_offset <= chain_parms_size
    if not within_params or not within_chain:
        add(
            blockers,
            "array_param_boundary_unsafe",
            param=param,
            offset_internal=offset,
            element_size=element_size,
            array_dim=array_dim,
            end_offset=end_offset,
            target_parms_size=target_parms_size,
            chain_parms_size=chain_parms_size,
        )
    boundary["safe"] = exact and within_params and within_chain
    return boundary


def validate_array_boundary_aggregate(
    boundaries: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    numeric_boundaries = [
        boundary
        for boundary in boundaries
        if is_plain_int(boundary.get("offset_internal")) and is_plain_int(boundary.get("end_offset"))
    ]
    sorted_boundaries = sorted(numeric_boundaries, key=lambda item: int(item["offset_internal"]))
    for previous, current in zip(sorted_boundaries, sorted_boundaries[1:]):
        if int(previous["end_offset"]) > int(current["offset_internal"]):
            add(
                blockers,
                "array_param_boundary_overlap",
                previous=previous["field"],
                current=current["field"],
                previous_end_offset=previous["end_offset"],
                current_offset_internal=current["offset_internal"],
            )
    observed = [
        {
            "field": boundary["field"],
            "offset_internal": boundary.get("offset_internal"),
            "element_size": boundary.get("element_size"),
            "array_dim": boundary.get("array_dim"),
            "end_offset": boundary.get("end_offset"),
        }
        for boundary in boundaries
    ]
    expected = [
        {
            "field": f"{TARGET}.{boundary['name']}",
            "offset_internal": boundary["offset_internal"],
            "element_size": boundary["element_size"],
            "array_dim": boundary["array_dim"],
            "end_offset": boundary["end_offset"],
        }
        for boundary in EXPECTED_ARRAY_BOUNDARIES
    ]
    if observed != expected:
        add(blockers, "array_param_boundary_coverage_mismatch", expected=expected, value=observed)


def validate_target_set(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        targets = schema_target_list(TARGET_SET, SNAPSHOT_SCHEMA)
        lane = target_set_module_lane(TARGET_SET)
        classification = target_set_readiness_classification(TARGET_SET)
    except KeyError as exc:
        add(blockers, "target_set_missing", target_set=str(exc))
        return {
            "target_set": TARGET_SET,
            "targets": [],
            "module_lane": None,
            "readiness_classification": None,
            "planning_only": False,
            "release_readiness": False,
        }

    expected = [TARGET]
    if targets != expected:
        add(blockers, "target_set_targets_mismatch", expected=expected, value=targets)
    if TARGET_SET not in TARGET_SETS:
        add(blockers, "target_set_not_declared")
    if TARGET_SET not in PLANNING_ONLY_TARGET_SETS:
        add(blockers, "target_set_not_planning_only", value=sorted(PLANNING_ONLY_TARGET_SETS))
    if TARGET_SET in RELEASE_READINESS_TARGET_SETS:
        add(blockers, "target_set_in_release_readiness")
    if lane != "inventory":
        add(blockers, "target_set_module_lane_mismatch", expected="inventory", value=lane)
    if classification != "planning_only":
        add(blockers, "target_set_readiness_classification_mismatch", expected="planning_only", value=classification)
    return {
        "target_set": TARGET_SET,
        "targets": targets,
        "module_lane": lane,
        "readiness_classification": classification,
        "planning_only": TARGET_SET in PLANNING_ONLY_TARGET_SETS,
        "release_readiness": TARGET_SET in RELEASE_READINESS_TARGET_SETS,
    }


def validate_snapshot_shape(snapshot: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    blockers.extend(
        side_lane_fail_closed_source_artifact_issues(
            snapshot,
            expected_target_sets=(TARGET_SET,),
        )
    )
    target = target_payload(snapshot, blockers)
    evidence = snapshot.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "snapshot_evidence_missing")
        evidence = {}
    for key, expected in (("source", "offline_core"), ("status", "candidate-only")):
        if evidence.get(key) != expected:
            add(blockers, "snapshot_evidence_mismatch", field=key, expected=expected, value=evidence.get(key))
    interpretation = snapshot.get("interpretation")
    if not isinstance(interpretation, dict) or interpretation.get("status") != "candidate-only":
        add(
            blockers,
            "snapshot_interpretation_status_mismatch",
            expected="candidate-only",
            value=interpretation.get("status") if isinstance(interpretation, dict) else None,
        )

    copied_leaks = collect_copied_array_leaks(snapshot)
    for leak in copied_leaks:
        add(blockers, "copied_array_or_list_leak", **leak)
    for exposure in collect_forbidden_snapshot_exposures(snapshot):
        add(blockers, "forbidden_snapshot_exposure", **exposure)
    for boundary in collect_forbidden_array_payload_boundaries(snapshot):
        add(blockers, "forged_array_payload_boundary", **boundary)
    for leak in collect_snapshot_readiness_leaks(snapshot):
        add(blockers, "snapshot_readiness_flag_enabled", **leak)

    summary: dict[str, Any] = {
        "target": TARGET,
        "status": "candidate-only",
        "evidence_identity": {
            key: evidence.get(key)
            for key in (
                "ark_binary_sha256",
                "artifact_sha256",
                "capture_id",
                "evidence_pack_id",
                "source",
                "status",
            )
        },
        "param_count": 0,
        "array_boundary_count": 0,
        "unsafe_array_boundary_count": 0,
        "param_byte_boundaries": [],
        "redacted_array_count": 0,
        "redacted_array_fields": [],
        "array_inner_classes": {},
        "copied_scalar_count": 0,
        "copied_array_count": 0,
        "copied_list_count": 0,
    }
    if target is None:
        return summary

    identity = target.get("target")
    if not isinstance(identity, dict):
        add(blockers, "target_identity_missing")
        identity = {}
    actual_target = f"{identity.get('outer_name')}.{identity.get('name')}"
    if actual_target != TARGET:
        add(blockers, "target_identity_mismatch", expected=TARGET, value=actual_target)
    for field, expected in (
        ("function_flags", EXPECTED_FUNCTION["function_flags"]),
        ("num_parms", EXPECTED_FUNCTION["num_parms"]),
        ("parms_size", EXPECTED_FUNCTION["parms_size"]),
        ("return_value_offset", EXPECTED_FUNCTION["return_value_offset"]),
    ):
        if target.get(field) != expected:
            add(blockers, "function_shape_mismatch", field=field, expected=expected, value=target.get(field))
    if target.get("status") != "candidate":
        add(blockers, "target_status_mismatch", expected="candidate", value=target.get("status"))
    if target.get("reject_reasons") != []:
        add(blockers, "target_reject_reasons_not_empty", value=target.get("reject_reasons"))
    membership = target.get("membership")
    if isinstance(membership, dict):
        for field in ("class", "outer", "target"):
            if membership.get(field) != "candidate-uobject":
                add(blockers, "target_membership_mismatch", field=field, expected="candidate-uobject", value=membership.get(field))

    chain = target.get("property_chain")
    if not isinstance(chain, dict):
        add(blockers, "property_chain_missing")
        return summary
    for field, expected in (
        ("expected_count", 2),
        ("observed_count", 2),
        ("parms_size", 32),
        ("status", "candidate"),
        ("reject_reasons", []),
    ):
        if chain.get(field) != expected:
            add(blockers, "property_chain_shape_mismatch", field=field, expected=expected, value=chain.get(field))
    properties = chain.get("properties")
    if not isinstance(properties, list):
        add(blockers, "properties_missing")
        return summary
    summary["param_count"] = len(properties)
    if len(properties) != len(EXPECTED_PARAMS):
        add(blockers, "param_count_mismatch", expected=len(EXPECTED_PARAMS), value=len(properties))
    for index, prop in enumerate(properties[len(EXPECTED_PARAMS) :], start=len(EXPECTED_PARAMS)):
        if isinstance(prop, dict):
            add(
                blockers,
                "unexpected_extra_param_payload",
                index=index,
                name=prop.get("name"),
                class_name=prop.get("class_name"),
                offset_internal=prop.get("offset_internal"),
            )
        else:
            add(blockers, "unexpected_extra_param_payload", index=index, value=prop)

    observed_boundaries: list[dict[str, Any]] = []
    for index, expected in enumerate(EXPECTED_PARAMS):
        if index >= len(properties) or not isinstance(properties[index], dict):
            add(blockers, "expected_param_missing", index=index, expected=expected["name"])
            continue
        prop = properties[index]
        field_name = f"{TARGET}.{expected['name']}"
        for key in ("name", "class_name", "offset_internal", "element_size", "array_dim", "property_flags"):
            if prop.get(key) != expected[key]:
                add(
                    blockers,
                    "array_param_shape_mismatch",
                    param=expected["name"],
                    field=key,
                    expected=expected[key],
                    value=prop.get(key),
                )
        for key in ("status", "membership_status", "class_membership_status", "outer_membership_status"):
            expected_value = "candidate" if key == "status" else "candidate-uobject"
            if prop.get(key) != expected_value:
                add(blockers, "array_param_membership_mismatch", param=expected["name"], field=key, expected=expected_value, value=prop.get(key))
        if prop.get("reject_reasons") != []:
            add(blockers, "array_param_reject_reasons_not_empty", param=expected["name"], value=prop.get("reject_reasons"))

        boundary = validate_array_param_boundary(prop, expected, target.get("parms_size"), chain.get("parms_size"), blockers)
        observed_boundaries.append(boundary)
        summary["param_byte_boundaries"].append(boundary)

        inner_candidate = prop.get("array_inner_candidate")
        if not isinstance(inner_candidate, dict):
            add(blockers, "array_inner_candidate_missing", param=expected["name"])
            continue
        for key, expected_value in (("status", "candidate"), ("membership_status", "candidate-uobject"), ("reject_reasons", [])):
            if inner_candidate.get(key) != expected_value:
                add(
                    blockers,
                    "array_inner_candidate_shape_mismatch",
                    param=expected["name"],
                    field=key,
                    expected=expected_value,
                    value=inner_candidate.get(key),
                )
        inner = inner_candidate.get("inner_property")
        if not isinstance(inner, dict):
            add(blockers, "array_inner_candidate_missing_inner_property", param=expected["name"])
            continue
        if inner.get("class_name") != expected["inner_class_name"]:
            add(
                blockers,
                "array_inner_class_mismatch",
                param=expected["name"],
                expected=expected["inner_class_name"],
                value=inner.get("class_name"),
            )
        summary["redacted_array_count"] += 1
        summary["redacted_array_fields"].append(
            {
                "field": field_name,
                "source_property_class": prop.get("class_name"),
                "redaction": "ArrayProperty payload redacted; no TArray copy",
                "array_inner": {
                    "source_property_class": inner.get("class_name"),
                    "redaction": "ObjectProperty inner identity redacted; no element identity, lookup, or ResourceHandle",
                },
            }
        )
        inner_class = inner.get("class_name")
        if isinstance(inner_class, str):
            classes = summary["array_inner_classes"]
            classes[inner_class] = classes.get(inner_class, 0) + 1

    if summary["redacted_array_count"] != 2:
        add(blockers, "redacted_array_count_mismatch", expected=2, value=summary["redacted_array_count"])
    if summary["array_inner_classes"] != {"ObjectProperty": 2}:
        add(blockers, "array_inner_classes_mismatch", expected={"ObjectProperty": 2}, value=summary["array_inner_classes"])
    validate_array_boundary_aggregate(observed_boundaries, blockers)
    summary["array_boundary_count"] = len(summary["param_byte_boundaries"])
    summary["unsafe_array_boundary_count"] = sum(
        1 for boundary in summary["param_byte_boundaries"] if not boundary.get("safe")
    )
    return summary


def contract_or_readiness_offenders(
    value: Any,
    path: tuple[str, ...] = (),
    *,
    claim_context: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    contract_offenders: list[dict[str, Any]] = []
    readiness_offenders: list[dict[str, Any]] = []
    if isinstance(value, dict):
        object_mentions_target = contains_forbidden_public_token(value)
        object_mentions_claim_context = (
            claim_context
            or object_mentions_target
            or (bool(path) and contains_public_claim_context(value))
        )
        for key, child in value.items():
            child_path = (*path, str(key))
            key_text = str(key)
            key_lower = key_text.lower()
            normalized_key = normalized_claim_key(key_text)
            forbidden_path_alias = forbidden_readiness_alias_path(child_path)
            child_context = object_mentions_claim_context or claim_context_key(key_text) or forbidden_path_alias
            if key_lower in CONTRACT_KEYS and contains_forbidden_public_token(child) and value_is_present(child):
                contract_offenders.append({"path": path_label(child_path), "value": child})
            if child_context:
                if (
                    forbidden_true_ready_key(key_text) and is_positive_readiness_alias_value(child)
                ) or (forbidden_path_alias and is_positive_claim_value(child)):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
                if normalized_key in SOURCE_STATUS_KEYS and is_positive_claim_value(child):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
                if normalized_key in (SOURCE_LABEL_KEYS | SOURCE_MARKER_KEYS) and contains_positive_claim_value(child):
                    if isinstance(child, list):
                        for index, item in enumerate(child):
                            if contains_positive_claim_value(item):
                                readiness_offenders.append(
                                    {"path": path_label((*child_path, str(index))), "value": item}
                                )
                    else:
                        readiness_offenders.append({"path": path_label(child_path), "value": child})
                if key_lower == "status" and isinstance(child, str) and is_positive_status_alias(child):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
                if (
                    contextual_status_alias_key(normalized_key)
                    and is_positive_claim_value(child)
                ):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
                if (
                    readiness_accounting_alias_key(normalized_key)
                    and not neutral_positive_metadata_key(normalized_key)
                    and is_positive_claim_value(child)
                ):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
                if normalized_key in {"accepted", "ready", "stable"} and is_positive_claim_value(child):
                    readiness_offenders.append({"path": path_label(child_path), "value": child})
            nested_contract, nested_readiness = contract_or_readiness_offenders(
                child,
                child_path,
                claim_context=child_context,
            )
            contract_offenders.extend(nested_contract)
            readiness_offenders.extend(nested_readiness)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            nested_contract, nested_readiness = contract_or_readiness_offenders(
                child,
                (*path, str(index)),
                claim_context=claim_context,
            )
            contract_offenders.extend(nested_contract)
            readiness_offenders.extend(nested_readiness)
    return contract_offenders, readiness_offenders


def collect_positive_public_claims(
    value: Any,
    path: tuple[str, ...] = (),
    scan_context: bool = False,
    relevant_context: bool = False,
) -> list[dict[str, Any]]:
    offenders: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_lower = str(key).lower()
            if key_lower in NEGATIVE_KEYS:
                continue
            child_path = (*path, str(key))
            child_relevant_context = relevant_context or contains_public_claim_context(child)
            child_context = scan_context or (child_relevant_context and key_lower in PUBLIC_CLAIM_SCAN_KEYS)
            offenders.extend(
                collect_positive_public_claims(child, child_path, child_context, child_relevant_context)
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_relevant_context = relevant_context or contains_public_claim_context(child)
            offenders.extend(
                collect_positive_public_claims(child, (*path, str(index)), scan_context, child_relevant_context)
            )
    elif scan_context and isinstance(value, str):
        for mention in positive_term_mentions(value, PUBLIC_POSITIVE_CLAIM_TERMS):
            offenders.append({"path": path_label(path), **mention})
    return offenders


def scan_public_json(path: Path, blockers: list[dict[str, Any]], label: str) -> dict[str, Any]:
    payload = read_json(path, blockers, label)
    if payload is None:
        return {
            "path": str(path),
            "schema": None,
            "contract_offenders": [],
            "readiness_offenders": [],
            "positive_claim_offenders": [],
        }
    expected_schema = EXPECTED_PUBLIC_JSON_SCHEMAS.get(label)
    schema = payload.get("schema")
    if expected_schema is not None and schema != expected_schema:
        add(blockers, f"{label}_schema_mismatch", expected=expected_schema, value=schema)
    contract_offenders, readiness_offenders = contract_or_readiness_offenders(payload)
    positive_claim_offenders = collect_positive_public_claims(payload)
    if contract_offenders:
        add(blockers, "public_contract_leak", source=label, offenders=contract_offenders)
    if readiness_offenders:
        add(blockers, "public_readiness_leak", source=label, offenders=readiness_offenders)
    if positive_claim_offenders:
        add(blockers, "public_positive_claim_leak", source=label, offenders=positive_claim_offenders)
    return {
        "path": str(path),
        "schema": schema,
        "contract_offenders": contract_offenders,
        "readiness_offenders": readiness_offenders,
        "positive_claim_offenders": positive_claim_offenders,
    }


def scan_public_header(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        reject_symlink_component(path, "public_header")
        resolved = reject_protected_input_path(path, "public_header")
        text = resolved.read_text(encoding="utf-8")
    except SystemExit as exc:
        add(blockers, "public_header_path_rejected", path=str(path), detail=str(exc))
        return {"path": str(path), "offenders": [], "positive_claim_offenders": []}
    except OSError as exc:
        add(blockers, "public_header_unreadable", path=str(path), detail=str(exc))
        return {"path": str(path), "offenders": [], "positive_claim_offenders": []}
    lower = text.lower()
    offenders = [token for token in FORBIDDEN_PUBLIC_TOKENS if token.lower() in lower]
    positive_claim_offenders = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not contains_public_claim_context(line):
            continue
        for mention in positive_term_mentions(line, PUBLIC_POSITIVE_CLAIM_TERMS):
            positive_claim_offenders.append({"path": f"public_header:{index}", **mention})
    if offenders:
        add(blockers, "public_header_token_leak", path=str(path), offenders=offenders)
    if positive_claim_offenders:
        add(blockers, "public_positive_claim_leak", source="public_header", offenders=positive_claim_offenders)
    return {"path": str(path), "offenders": offenders, "positive_claim_offenders": positive_claim_offenders}


def build_check(
    *,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    public_sdk_surfaces: Path = DEFAULT_PUBLIC_SDK_SURFACES,
    public_gameplay_events: Path = DEFAULT_PUBLIC_GAMEPLAY_EVENTS,
    public_header: Path = DEFAULT_PUBLIC_HEADER,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    target_set_summary = validate_target_set(blockers)
    snapshot = read_json(snapshot_path, blockers, "snapshot")
    snapshot_summary = validate_snapshot_shape(snapshot, blockers) if snapshot is not None else {}
    public_contract_scan = {
        "public_sdk_surfaces": scan_public_json(public_sdk_surfaces, blockers, "public_sdk_surfaces"),
        "public_gameplay_events": scan_public_json(public_gameplay_events, blockers, "public_gameplay_events"),
        "public_header": scan_public_header(public_header, blockers),
    }
    public_contract_offender_count = (
        len(public_contract_scan["public_sdk_surfaces"]["contract_offenders"])
        + len(public_contract_scan["public_gameplay_events"]["contract_offenders"])
        + len(public_contract_scan["public_header"]["offenders"])
    )
    public_readiness_offender_count = (
        len(public_contract_scan["public_sdk_surfaces"]["readiness_offenders"])
        + len(public_contract_scan["public_gameplay_events"]["readiness_offenders"])
    )
    public_positive_claim_offender_count = (
        len(public_contract_scan["public_sdk_surfaces"]["positive_claim_offenders"])
        + len(public_contract_scan["public_gameplay_events"]["positive_claim_offenders"])
        + len(public_contract_scan["public_header"]["positive_claim_offenders"])
    )
    missing_non_claim_tokens = [token for token in REQUIRED_NON_CLAIM_TOKENS if token not in "\n".join(NON_CLAIMS)]
    if missing_non_claim_tokens:
        add(blockers, "non_claim_tokens_missing", missing=missing_non_claim_tokens)
    ready = not blockers
    forged_array_payload_boundary_count = sum(
        1 for blocker in blockers if blocker.get("reason") == "forged_array_payload_boundary"
    )
    readiness_report = dict(READINESS_TRUTHFULNESS_REPORT)
    readiness_report["input_guardrails_passed"] = ready
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": "accepted_candidate_only_boundary" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "fixture_only": True,
        "candidate_only": True,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "not_artifact_gate": True,
        "priority_class": "non_p0_side_lane",
        "target_set": TARGET_SET,
        "target_set_summary": target_set_summary,
        "snapshot": str(snapshot_path),
        "summary": snapshot_summary,
        "public_contract_scan": public_contract_scan,
        "public_contract_offender_count": public_contract_offender_count,
        "public_readiness_offender_count": public_readiness_offender_count,
        "public_positive_claim_offender_count": public_positive_claim_offender_count,
        "readiness_report": readiness_report,
        "next_blockers": NEXT_BLOCKERS,
        "copied_scalar_count": snapshot_summary.get("copied_scalar_count", 0),
        "copied_array_count": snapshot_summary.get("copied_array_count", 0),
        "copied_list_count": snapshot_summary.get("copied_list_count", 0),
        "array_boundary_count": snapshot_summary.get("array_boundary_count", 0),
        "unsafe_array_boundary_count": snapshot_summary.get("unsafe_array_boundary_count", 0),
        "forged_array_payload_boundary_count": forged_array_payload_boundary_count,
        "public_api_count": public_contract_offender_count,
        "side_lane_accounting": {
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "approved_runtime_evidence_substitution_allowed": False,
            "authorizes_discord_send": False,
            "authorizes_live_log_reads": False,
            "authorizes_marker_or_env_changes": False,
            "authorizes_player_backed_window": False,
            "authorizes_runtime_capture": False,
            "authorizes_runtime_observer": False,
            "authorizes_server_restart": False,
            "clears_approved_runtime_evidence_missing": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_for_p0_dependency_chain": False,
            "counts_for_public_sdk_v1": False,
            "side_lane_counts_toward_sdk": False,
            "side_lane_counts_toward_p0": False,
            "sdk_p0_unlock_allowed": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "counts_toward_v1_completion": False,
            "primary_evidence_substitution_allowed": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "v1_completion_progress_contribution": 0,
            "evidence_use": "offline_fixture_boundary_only",
            "accepted_for_internal_planning": ready,
            "offline_only": True,
            "not_artifact_gate": True,
            "ready_scope": NON_AUTHORIZING_READY_SCOPE,
            "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
            "current_route_blocker": CURRENT_ROUTE_BLOCKER,
            "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
            "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
            "replaces_player_principal_evidence": False,
            "replaces_player_principal_triplet": False,
            "player_principal_lifecycle_evidence_substitution_allowed": False,
            "side_lane_collection_can_replace_player_principal_evidence": False,
            "side_lane_collection_counts_before_checker_acceptance": False,
            "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
            "substitutes_for_player_principal_lifecycle_evidence": False,
            "substitutes_for_player_principal_lifecycle_triplet": False,
            "blocked_promotion_claims": list(BLOCKED_PROMOTION_CLAIMS),
        },
        "blockers": blockers,
        "non_claims": NON_CLAIMS,
    }
    for flag in FALSE_READINESS_FLAGS:
        report[flag] = False
    report.update(ZERO_ACCOUNTING_FIELDS)
    return report


def main() -> int:
    args = parse_args()
    report = build_check(
        snapshot_path=args.snapshot,
        public_sdk_surfaces=args.public_sdk_surfaces,
        public_gameplay_events=args.public_gameplay_events,
        public_header=args.public_header,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
