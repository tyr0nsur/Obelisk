#!/usr/bin/env python3
"""Compare sanitized UFunction/ScriptStruct snapshot layouts from two evidence roots."""

from __future__ import annotations

import argparse
import errno
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any
import re

from artifact_identity import ARTIFACT_IDENTITY_KEYS, is_safe_artifact_id, is_sha256
import protected_paths
from reflection_target_sets import (
    INTERNAL_LAYOUT_ONLY_TARGET_SETS,
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    PLANNING_ONLY_TARGET_SETS,
    RELEASE_READINESS_TARGET_SETS,
    TARGET_SETS,
    TARGET_SET_MODULE_LANES,
    TARGET_SET_REVISION_SCHEMA,
    TARGET_SET_REVISION_SOURCE,
    player_lifecycle_anchor_source_policy,
    target_set_catalog_hygiene_issues,
    target_set_module_lane,
    target_set_target_overlaps,
    target_set_readiness_classification,
    target_set_revision_source_sha256,
)


SUPPORTED_SCHEMAS = {
    "obelisk.ufunction-chain.snapshot.v1",
    "obelisk.scriptstruct-chain.snapshot.v1",
}
FORBIDDEN_KEYS = {
    "object",
    "address",
    "first_property",
    "next_field",
    "next_property",
    "pointer_window",
    "integer_window",
    "gobjects",
    "fname_table",
    "chunks",
    "native_func_candidate",
}
ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{8,}")
BOOL_MASK_RE = re.compile(r"^0x[0-9a-fA-F]{1,2}$")
HEX_METADATA_KEYS = {"property_flags", "return_value_offset", "function_flags"}
EVIDENCE_ARTIFACT_IDENTITY_KEYS = ARTIFACT_IDENTITY_KEYS
ALLOWED_ARTIFACT_KINDS = {"offline_core"}
PROTECTED_SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
READINESS_EVIDENCE_SCOPE = "second_source_layout_evidence_only"
READINESS_TARGET_SET_COVERAGE_SCHEMA = "obelisk.reflection-snapshot-readiness-target-set-coverage.v1"
TARGET_SET_CATALOG_GUARDRAIL = "fail_closed_named_target_set_catalog"
TARGET_SET_CATALOG_EVIDENCE_SCOPE = "target_set_catalog_only_not_evidence"
TARGET_GUIDANCE_EVIDENCE_SCOPE = "offline_guidance_only_not_evidence"
PLANNING_LAYOUT_INTAKE_EVIDENCE_SCOPE = "planning_layout_intake_only_not_second_source"
PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS = "not_applicable_planning_layout_intake"
PLANNING_LAYOUT_DOES_NOT_SATISFY = [
    "second_source_layout_evidence",
    *NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    "release_readiness",
]
READINESS_DOES_NOT_SATISFY = [
    "release_readiness",
    *NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
]
READINESS_NOT_PROMOTED_SURFACES = {
    "class_identity",
    "complete_sdk",
    "cross_binary_portability",
    "inventory_identity",
    "inventory_sdk",
    "item_identity",
    "items_sdk",
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "p0_dependency_chain",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
    "v1_completion",
}
READINESS_FALSE_FLAGS = {
    "complete_sdk_ready": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "p0_dependency_chain_ready": False,
    "promotion_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "v1_completion_ready": False,
}
READINESS_ZERO_FIELDS = {
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "v1_completion_progress_contribution": 0,
}
READINESS_NON_CLAIMS = [
    "accepted second-source readiness is layout evidence only",
    (
        "release readiness does not imply public SDK readiness for Mission, Transfer, "
        "Structure, Item, Inventory, or Items modules"
    ),
    (
        "does not promote public SDK, Mission SDK, Transfer SDK, Structure SDK, "
        "StructureEvents, Inventory SDK, Items SDK, object identity, lookup, mutation, "
        "return override, ResourceHandle, runtime hooks, P0 dependency-chain credit, "
        "complete-SDK accounting, or v1 completion"
    ),
]
POSITIVE_STATUS_VALUES = frozenset(
    (
        "accepted",
        "active",
        "available",
        "enabled",
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
)
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:"
    r"^ready$|readiness|"
    r"public_?(?:sdk|api|abi|contract|ready)|"
    r"runtime_?(?:ready|validated|validation|hook|wiring|contract)|"
    r"complete_?sdk|stable_?sdk|p0|v1_?(?:completion|ready)|promotion_?ready|"
    r"(?:route|progress)_?(?:ready|readiness|claim|contribution)|"
    r"resource_?handle|"
    r"(?:object|player|item|inventory|class)?_?identity_?(?:ready|lookup|contract)?|"
    r"lookup_?ready|mutation|return_?override|"
    r"counts_?(?:toward|for)|contributes?_?to"
    r")",
    re.IGNORECASE,
)
CLAIM_SUBJECT_RE = re.compile(
    r"(?:"
    r"public[_\s-]+(?:sdk|api|abi|contract)|"
    r"runtime(?:[_\s-]+(?:hook|validation|wiring|ready|readiness))?|"
    r"complete[_\s-]+sdk|stable[_\s-]+sdk|p0|v1[_\s-]+completion|"
    r"ResourceHandle|resource[_\s-]+handle|"
    r"route[_\s-]+(?:ready|readiness|progress|claim)|progress[_\s-]+(?:claim|contribution)|"
    r"(?:object|player|item|inventory|class)?[_\s-]*identity|lookup|"
    r"mutation|return[_\s-]+override"
    r")",
    re.IGNORECASE,
)
AFFIRMATIVE_CONTEXT_RE = re.compile(
    r"(?:ready|readiness|available|enabled|promoted|promotion|public|runtime|complete|"
    r"completion|supported|validated|claim|counts|contributes)",
    re.IGNORECASE,
)
NEGATED_OR_BLOCKED_RE = re.compile(
    r"\b(?:"
    r"blocked|candidate-only|candidate_only|does\s+not|do\s+not|excluded|must\s+not|"
    r"no|not|non-promoting|redacted|remain|remains|without"
    r")\b",
    re.IGNORECASE,
)
CLAIM_SCAN_EXEMPT_PATHS = frozenset(
    (
        "$.evidence.artifact_kind",
        "$.evidence.source",
        "$.evidence.status",
    )
)
DEFAULT_OBSERVED_FNAME_TARGET = "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer"
OBSERVED_FNAME_CHAIN_EVIDENCE_SCOPE = "diagnostic_fname_chain_planning_only_not_second_source"
OBSERVED_FNAME_CHAIN_LAYOUT_EVIDENCE_STATUS = "not_layout_evidence"
OBSERVED_FNAME_CHAIN_ARTIFACT_ROLE = "diagnostic_planning_only_not_second_source_input"
OBSERVED_FNAME_CHAIN_NON_CLAIMS = [
    "planning-only comparison against sanitized UFunction snapshots",
    "does not create second-source layout evidence",
    "does not accept or reject runtime principal lifecycle evidence",
    "does not promote public Player SDK, public player identity, lookup, ResourceHandle, mutation, return override, runtime hooks, release readiness, or v1 completion",
    "does not expose UE pointers, raw params, GObjects indices, player/controller/character identity, or copied gameplay payloads",
]
OBSERVED_FNAME_CHAIN_SECOND_SOURCE_BLOCKERS = [
    "copied_runtime_diagnostic_line_not_distinct_sanitized_snapshot",
    "observed_fname_indices_only_no_property_names_classes_offsets_sizes_or_bool_metadata",
    "missing_distinct_lifecycle_artifact_identity",
    "approved_runtime_evidence_missing",
]
OBSERVED_FNAME_CHAIN_PROHIBITED_EVIDENCE_USES = [
    "second_source_layout_evidence",
    "candidate_snapshot_root",
    "approved_runtime_principal_lifecycle_evidence",
    "runtime_readiness",
    "public_sdk_readiness",
    "release_readiness",
    "v1_completion",
]
DIAGNOSTIC_ONLY_LIFECYCLE_SCHEMAS = {
    "obelisk.reflection-observed-fname-chain-check.v1",
    "obelisk.players-lifecycle-handle-new-player-fname-mismatch.v1",
}
NON_SNAPSHOT_LIFECYCLE_SIDECAR_SCHEMA_REASONS = {
    "obelisk.installed-sdk-package-shape.v1": "package_shape_not_sanitized_lifecycle_snapshot_root",
    "obelisk.player-principal-lifecycle-beta-notice-authority-boundary.v1": (
        "beta_notice_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-beta-notice-prep.v1": (
        "beta_notice_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-evidence-closure-request.v1": (
        "runtime_window_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-guarded-beta-notice-action.v1": (
        "beta_notice_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-no-users-passive-wait-recommendation.v1": (
        "no_users_passive_wait_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-runtime-evidence-status.v1": (
        "runtime_window_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-execution.v1": (
        "runtime_window_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-plan.v1": (
        "runtime_window_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-runtime-window-post-window-state.v1": (
        "runtime_window_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-window-request-check.v1": (
        "window_request_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.player-principal-lifecycle-window-request.v1": (
        "window_request_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.players-identity-first-evidence.v1": (
        "first_evidence_planning_artifact_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.players-identity-lifecycle-anchor-candidates.v1": (
        "lifecycle_anchor_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.players-identity-principal-invalidation-policy.v1": (
        "principal_policy_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.public-sdk-v1-completion-check.v1": (
        "sdk_status_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.public-sdk-v1-completion-summary.v1": (
        "sdk_status_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
    "obelisk.sdk-status-report.v1": "sdk_status_side_lane_not_sanitized_lifecycle_snapshot_root",
    "obelisk.sdk-status-side-lane-summary.v1": (
        "sdk_status_side_lane_not_sanitized_lifecycle_snapshot_root"
    ),
}
LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS = [
    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.HandleNewPlayer",
    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.OnLogout",
]
LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_FILENAMES = [
    "ShooterGameMode.HandleNewPlayer.snapshot.json",
    "ShooterGameMode.OnLogout.snapshot.json",
]
LIFECYCLE_SNAPSHOT_ROOT_CHECK_SCHEMA = "obelisk.lifecycle-ufunction-snapshot-root-requirement.v1"
LIFECYCLE_SNAPSHOT_ROOT_CHECK_EVIDENCE_SCOPE = (
    "lifecycle_property_shape_planning_evidence_only_not_runtime_or_public_sdk_readiness"
)
LIFECYCLE_SNAPSHOT_ROOT_REQUIRED_IDENTITY_FIELDS = [
    "evidence.ark_binary_sha256",
    "evidence.artifact_kind=offline_core",
    "evidence.artifact_sha256",
    "evidence.capture_id",
    "evidence.evidence_pack_id",
]
LIFECYCLE_SNAPSHOT_ROOT_NON_CLAIMS = [
    "offline sanitized UFunction snapshot-root requirement only",
    "accepted lifecycle snapshot-root checks are property-shape planning evidence only",
    "does not clear approved_runtime_evidence_missing",
    "does not prove runtime login/logout ordering, principal validity, principal invalidation, or lifecycle cleanup",
    "does not promote public Player SDK, public player identity, lookup, ResourceHandle, mutation, return override, runtime hooks, release readiness, public SDK readiness, or v1 completion",
    "does not expose UE pointers, raw params, GObjects indices, player/controller/character identity, or copied gameplay payloads",
]
LIFECYCLE_SNAPSHOT_ROOT_PROHIBITED_INPUTS = [
    "direct or symlink-resolved protected live-server paths",
    "passive player-principal snapshot manifests",
    "ReflectionScanner analyzer or broad scanner output",
    "layout-only readiness/comparison reports",
    "copied runtime diagnostic FName-chain lines",
    "broad FName scans",
    "broad GObjects scans",
]
LIFECYCLE_SNAPSHOT_ROOT_DOES_NOT_SATISFY = [
    "approved_runtime_evidence",
    "runtime_readiness",
    "public_sdk_readiness",
    "release_readiness",
    "v1_completion",
]
LIFECYCLE_FNAME_DRIFT_NEXT_OFFLINE_ARTIFACT_REQUIREMENT = {
    "artifact": "distinct_sanitized_lifecycle_ufunction_snapshot_root",
    "status_needed": "required_before_deploy_request",
    "purpose": "prove lifecycle property shape without treating observed FName indices as layout evidence",
    "required_targets": LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS,
    "required_identity_fields": [
        "evidence.ark_binary_sha256",
        "evidence.artifact_kind=offline_core",
        "evidence.artifact_sha256",
        "evidence.capture_id",
        "evidence.evidence_pack_id",
    ],
    "required_shape_fields": [
        "target outer/name/class",
        "NumParms",
        "ParmsSize",
        "ReturnValueOffset",
        "property order",
        "property class",
        "offset_internal",
        "element_size",
        "array_dim",
        "property_flags",
        "BoolProperty byte/field metadata",
        "candidate-uobject membership for target/class/outer/properties",
    ],
    "comparison_mode": "semantic_layout_without_strict_identity_indices",
    "comparison_command_template": (
        "python3 scripts/compare_reflection_snapshots.py --base-root "
        "tests/fixtures/ufunction_snapshots --candidate-root "
        "<distinct-sanitized-lifecycle-root> --lifecycle-snapshot-root-check --json"
    ),
    "accepted_result_scope": "property_shape_planning_evidence_only_not_runtime_or_public_sdk_readiness",
    "prohibited_inputs": [
        "copied runtime diagnostic FName-chain lines",
        "passive snapshot manifests",
        "direct or symlink-resolved protected live-server paths",
        "broad FName scans",
        "broad GObjects scans",
        "ReflectionScanner output from an unapproved runtime run",
    ],
}
MISSION_COPIED_BOOL_FIXTURE_ROOT = "tests/fixtures/ufunction_snapshots"
MISSION_COPIED_BOOL_POLICY_MANIFEST_SHA256 = (
    "f56a191aaecbd52d042efd81423d4a86f4e5a29674660aab9d65bbf496416945"
)
MISSION_COPIED_BOOL_ARTIFACT_PACK_MANIFEST_SHA256 = (
    "b47f0497c92ae3e8f9a006fb5be87cfbcc1d1dd5f15d78267ad186073e4c26fb"
)
MISSION_CONSUME_ONLY_TARGET_SETS = frozenset(
    (
        "mission-copied-bool-policy-slice",
    )
)
TARGET_BLOCKER_GUIDANCE = {
    "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress": {
        "classification": "p0_adjacent_player_join_admission_candidate",
        "why_blocked": [
            "candidate_only_layout_evidence",
            "not_release_readiness_target",
            "not_identity_anchor",
            "runtime_ordering_unproven",
            "principal_privacy_policy_unproven",
            "public_player_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "reuse the existing distinct sanitized base and vanilla lifecycle snapshots for "
            "ShooterGameMode.CheckJoinInProgress, or regenerate this exact target only from "
            "reviewed non-protected offline evidence; compare with --target "
            "obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress "
            "for candidate-only P0-adjacent admission-shape review"
        ),
        "snapshot_prep_checks": [
            "require exact target obelisk.ufunction-chain.snapshot.v1:ShooterGameMode.CheckJoinInProgress",
            "expected observed shape is NumParms=3, ParmsSize=17, ReturnValueOffset=0x10",
            "require property order bIsFromLogin:BoolProperty@0, NewPlayer:ObjectProperty@8, ReturnValue:BoolProperty@16",
            "keep NewPlayer redacted or recognition-only; no controller/player object identity, lookup, ResourceHandle, UE pointer, raw params, FName, or GObjects exposure",
            "treat bIsFromLogin and ReturnValue as admission-shape copied-scalar candidates only, not return override or public policy decisions",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target as a session-start/session-end lifecycle anchor without separate approved runtime ordering evidence",
        ],
        "non_claim": (
            "does not promote public player identity, Player SDK, join admission API, "
            "permissions, commands/replies, runtime ordering, lookup, ResourceHandle, "
            "mutation, return override, runtime hooks, release readiness, public SDK "
            "readiness, or v1 completion"
        ),
    },
    "obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild": {
        "classification": "second_wave_structure_build_policy_candidate",
        "why_blocked": [
            "planning_layout_only_not_promotion_gate",
            "placement_struct_redaction_policy_unproven",
            "copied_payload_policy_unproven",
            "runtime_observation_requires_separate_approval",
            "build_denial_return_override_policy_blocked",
        ],
        "next_offline_input": (
            "approved non-protected copied/offline core or complete core evidence-pack manifest "
            "with FName root, GObjects, binary hash, and artifact identity; use core inputs "
            "with inspect_core_ufunctions.py --snapshot-json, but route evidence-pack manifests "
            "through the snapshot regeneration consumer instead of passing a manifest to --core; "
            "do not repeat fixture-only missing_base_snapshot checks as discovery"
        ),
        "snapshot_prep_checks": [
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:PrimalStructure.IsAllowedToBuild",
            "reuse the accepted planning-layout second-source artifact before starting new extraction work",
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            "record distinct offline artifact identity fields: artifact_sha256, capture_id, evidence_pack_id",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "keep placement structs, location vectors, player/controller context, object refs, arrays, and raw params redacted or recognition-only",
            "compare only against a distinct sanitized second-source snapshot before any readiness claim",
        ],
        "non_claim": (
            "does not promote StructureEvents, build-policy SDK, identity, lookup, mutation, "
            "return override, runtime hooks, release readiness, or public SDK readiness"
        ),
    },
    "obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild": {
        "classification": "second_wave_structure_build_policy_candidate",
        "why_blocked": [
            "missing_committed_sanitized_snapshot",
            "missing_distinct_second_source_layout",
            "reflected_owner_unproven",
            "target_set_coverage_blocked",
            "placement_struct_redaction_policy_unproven",
            "build_denial_return_override_policy_blocked",
        ],
        "next_offline_input": (
            "approved non-protected copied/offline core or complete core evidence-pack manifest "
            "that proves whether APrimalStructure is a reflected owner; use core inputs with "
            "inspect_core_ufunctions.py --snapshot-json, but route evidence-pack manifests "
            "through the snapshot regeneration consumer instead of passing a manifest to --core; "
            "do not repeat fixture-only missing_base_snapshot checks as discovery"
        ),
        "snapshot_prep_checks": [
            "treat APrimalStructure as an ArkApi dictionary seed until a sanitized snapshot proves the reflected owner",
            "emit exact schema-qualified target obelisk.ufunction-chain.snapshot.v1:APrimalStructure.IsAllowedToBuild only if that owner is observed",
            "generate one sanitized candidate snapshot for this exact target only before adding any target set",
            "never pass an evidence-pack manifest path to inspect_core_ufunctions.py --core",
            "record distinct offline artifact identity fields: artifact_sha256, capture_id, evidence_pack_id",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "keep placement structs, location vectors, player/controller context, object refs, arrays, and raw params redacted or recognition-only",
        ],
        "non_claim": (
            "does not promote StructureEvents, build-policy SDK, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set coverage"
        ),
    },
}
TARGET_SET_BLOCKER_GUIDANCE = {
    "buff-compact-intake": {
        "classification": "internal_buff_layout_only_candidate",
        "why_blocked": [
            "internal_layout_evidence_only",
            "not_release_readiness_target",
            "missing_distinct_second_source_layout",
            "copied_data_policy_unproven",
            "lifecycle_privacy_policy_unproven",
            "promotion_gate_blocked",
            "public_buff_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "sanitized AllowPostProcessEffect, BPBuffPreventUploading, and "
            "BP_OnBuffLifetimeUpdated snapshots from a distinct non-protected "
            "offline artifact with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare only AllowPostProcessEffect, BPBuffPreventUploading, and BP_OnBuffLifetimeUpdated through --target-set buff-compact-intake",
            "require AllowPostProcessEffect and BPBuffPreventUploading to expose copied ReturnValue BoolProperty only",
            "require BP_OnBuffLifetimeUpdated to remain a zero-param recognition-only layout with no ReturnValue copy",
            "keep buff payloads, inventory context, object refs, strings, arrays, raw params, and UE pointers redacted or recognition-only",
            "keep evidence internal until copied-data, lifecycle, privacy, and promotion gates pass",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Buff SDK, buff identity, lookup, mutation, return override, "
            "runtime hooks, release readiness, or public SDK readiness"
        ),
    },
    "minimal-second-source-intake": {
        "classification": "release_compact_inventory_structure_layout_evidence",
        "why_blocked": [
            "compact_layout_evidence_only",
            "public_inventory_items_structure_sdks_blocked",
            "identity_lookup_resourcehandle_blocked",
            "mutation_return_override_blocked",
            "runtime_validation_requires_narrower_target_policy",
        ],
        "next_offline_input": (
            "use distinct sanitized offline snapshots only for CanUse, AllowRemoteAddToInventory, "
            "AllowStructureAccess, and IsAllowedToDemolish; use narrower policy target sets "
            "for copied-scalar release work"
        ),
        "snapshot_prep_checks": [
            "compare only CanUse, AllowRemoteAddToInventory, AllowStructureAccess, and IsAllowedToDemolish through --target-set minimal-second-source-intake",
            "treat readiness as compact second-source layout evidence for the mixed Item/Structure lane only",
            "keep item identity, inventory identity, structure identity, object refs, raw params, and UE pointers redacted or recognition-only",
            "keep Inventory SDK, Items SDK, StructureEvents, ResourceHandle, mutation, and return override blocked",
            "do not use this target set to expand runtime hooks, public SDKs, or target-set coverage",
        ],
        "non_claim": (
            "does not promote Inventory SDK, Items SDK, StructureEvents, identity, lookup, "
            "ResourceHandle, mutation, return override, runtime validation, or target-set expansion"
        ),
    },
    "item-return-only-policy-slice": {
        "classification": "internal_gameplay_policy_item_return_only_non_completion",
        "why_blocked": [
            "internal_non_completion_side_lane",
            "not_release_readiness_target",
            "complete_sdk_accounting_blocked",
            "p0_dependency_chain_accounting_blocked",
            "standalone_items_inventory_sdk_blocked",
            "identity_lookup_resourcehandle_blocked",
            "mutation_return_override_blocked",
            "runtime_producer_validation_requires_separate_approval",
        ],
        "next_offline_input": (
            "no broader item/inventory target expansion is ready; keep any follow-up evidence "
            "to the three copied ReturnValue-only targets unless a separate promotion note "
            "adds an explicit target set"
        ),
        "snapshot_prep_checks": [
            "compare only AllowEquipItem, CanRepair, and UseItemOntoItem through --target-set item-return-only-policy-slice",
            "copy only the ReturnValue BoolProperty field for each target",
            "keep CraftBlueprint, bIgnoreInventoryRequirement, bConsumeResources, toInventory, DestinationItem, AdditionalData, object refs, raw params, and UE pointers excluded",
            "keep item identity, inventory identity, lookup, ResourceHandle, mutation, and return override blocked",
            "treat accepted layout as internal copied-scalar planning only, not release readiness, P0 dependency-chain credit, or complete-SDK accounting",
            "runtime producer validation still requires a separate gated debug-window brief",
        ],
        "non_claim": (
            "does not promote Items SDK, Inventory SDK, identity, lookup, ResourceHandle, "
            "mutation, return override, runtime validation, release readiness, P0 dependency-chain "
            "credit, complete-SDK accounting, or target-set expansion"
        ),
    },
    "players-identity-lifecycle-intake": {
        "classification": "players_identity_lifecycle_guidance_only_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "identity_privacy_policy_unproven",
            "lifecycle_cleanup_policy_unproven",
            "public_player_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "docs-only review or sanitized offline snapshots from distinct non-protected "
            "artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set players-identity-lifecycle-intake for coverage review only",
            "keep player ids, platform ids, names, IPs, tribe ids, transfer ids, online-list values, object refs, arrays, strings, raw params, and UE pointers redacted",
            "classify copied-scalar candidates separately from redacted identity and lifecycle risks",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Player Identity/Lifecycle SDK, public player identity, lookup, "
            "ResourceHandle, mutation, return override, runtime hooks, or release readiness"
        ),
    },
    "players-lifecycle-anchor-candidates": {
        "classification": "players_lifecycle_anchor_candidates_guidance_only_candidate",
        **player_lifecycle_anchor_source_policy(),
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "approved_runtime_evidence_missing",
            "public_player_sdk_blocked",
            "runtime_ordering_unproven",
            "principal_invalidation_semantics_unproven",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "materialize a distinct non-/tmp sanitized planning comparison snapshot root "
            "for all six players-lifecycle-anchor-candidates targets, with complete "
            "artifact identity; repo fixtures currently bind the all-six base layouts "
            "only, and durable promoted source-bound lifecycle evidence remains limited "
            "to static anchors ShooterGameMode.HandleNewPlayer and ShooterGameMode.OnLogout, "
            "with ShooterGameMode.CheckJoinInProgress preserved only as the rejected-start "
            "triplet source"
        ),
        "snapshot_prep_checks": [
            "compare exactly GameMode.K2_PostLogin, ShooterGameMode.CheckJoinInProgress, ShooterGameMode.HandleNewPlayer, ShooterGameMode.OnLogout, ShooterGameMode.OnPostLogin__DelegateSignature, and ShooterGameMode.OnStartNewPlayer__DelegateSignature through --target-set players-lifecycle-anchor-candidates",
            "approved triplet sources are exactly ShooterGameMode.HandleNewPlayer, ShooterGameMode.CheckJoinInProgress, and ShooterGameMode.OnLogout",
            "keep ShooterGameMode.CheckJoinInProgress as the approved rejected-start triplet source and observer alternative, not a static session-start/session-end anchor",
            "keep GameMode.K2_PostLogin as non-anchor chronology only; property FName mismatch diagnostics must not become triplet source, lifecycle anchor, second-source, runtime, public SDK, release, or v1 evidence",
            "keep OnPostLogin__DelegateSignature and OnStartNewPlayer__DelegateSignature as delegate guidance only",
            "require distinct artifact identity before any all-six planning-layout comparison claim",
            "consume an all-six accepted comparison only through --planning-layout-intake or non-promotional readiness reporting; do not label it accepted second-source readiness",
            "keep current accepted durable lifecycle anchors limited to ShooterGameMode.HandleNewPlayer and ShooterGameMode.OnLogout",
            "do not let all-six planning comparison clear approved_runtime_evidence_missing, public SDK readiness, runtime readiness, release readiness, principal validity, or principal invalidation blockers",
            "keep player/controller/character object refs, UE pointers, raw params, FName/GObjects indices, lookup, ResourceHandle, mutation, and return override blocked",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote approved runtime evidence, public Player SDK, public player "
            "identity, runtime login/logout ordering, principal validity, principal "
            "invalidation, lookup, ResourceHandle, mutation, return override, runtime hooks, "
            "release readiness, or v1 completion"
        ),
    },
    "command-chat-response-route-planning": {
        "classification": "command_chat_response_route_guidance_only_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "public_response_path_blocked",
            "player_identity_principal_blocked",
            "permissions_admin_blocked",
            "command_router_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "generate focal snapshots for ClientServerChatDirectMessage, "
            "ClientServerChatMessage, and ClientChatMessage from reviewed non-protected "
            "offline evidence, then compare a distinct second-source root through "
            "--target-set command-chat-response-route-planning for planning review only"
        ),
        "snapshot_prep_checks": [
            "ClientChatMessage.Chat remains redacted/recognition-only until separate ChatMessage ScriptStruct and privacy review",
            "raw FString storage/data is forbidden, including ClientServerChatMessage.MessageText and ClientServerChatDirectMessage.MessageText",
            "sender identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "directed recipient identity remains redacted: no player name, platform ID, Steam/EOS ID, controller/connection/object ref, UE pointer, object-array/FName identity",
            "future targeting must use only a promoted copied principal handle/generation, not command text, operator config, raw params, or response UFunction layout",
            "keep reply API, send-chat API, broadcast/notices, moderation, command router, permission checks, mutation, and return override blocked",
            "require promoted player identity/principal and permissions/admin before any public response path is considered",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote command/chat response path, public reply/send-chat ABI, "
            "command router, permissions, player identity, raw FString access, mutation, "
            "return override, runtime hooks, or release readiness"
        ),
    },
    "inventory-custom-filter-array-boundary": {
        "classification": "inventory_custom_filter_array_boundary_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "non_p0_side_lane",
            "candidate_only_array_boundary_metadata",
            "copied_array_payload_blocked",
            "public_inventory_items_sdk_blocked",
            "identity_lookup_resourcehandle_blocked",
            "mutation_return_override_blocked",
            "v1_completion_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "use only the committed InventoryCustomFilter sanitized snapshot or a distinct "
            "non-protected offline sanitized snapshot for PrimalInventoryComponent."
            "InventoryCustomFilter; validate with scripts/check_inventory_custom_filter_array_boundary.py"
        ),
        "snapshot_prep_checks": [
            "compare only PrimalInventoryComponent.InventoryCustomFilter through --target-set inventory-custom-filter-array-boundary",
            "treat UnfilteredItemsList and FilteredItemsList as reflected TArray parameter-shell boundary metadata only",
            "keep TArray data pointer, count, capacity, element identity, object refs, raw arrays, raw params, AdditionalData, and UE pointers redacted or absent",
            "keep copied array/list payloads, copied scalars, Inventory SDK, Items SDK, public API, public ABI, and public payload contracts blocked",
            "keep item identity, inventory identity, lookup, ResourceHandle, mutation, and return override blocked",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for P0, release/readiness, public SDK, runtime, or v1 completion gates",
        ],
        "non_claim": (
            "does not promote P0 progress, Inventory SDK, Items SDK, public API, copied "
            "array/list payloads, item or inventory identity, lookup, ResourceHandle, "
            "mutation, return override, runtime hooks, release readiness, public SDK "
            "readiness, or v1 completion"
        ),
    },
    "structure-aggregate-census-planning": {
        "classification": "structure_aggregate_census_guidance_only_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "public_structureevents_sdk_blocked",
            "aggregate_privacy_policy_unproven",
            "identity_lookup_resourcehandle_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "use the six structure-observer targets as a bounded design seed; compare "
            "schema-qualified targets through --target-set structure-aggregate-census-planning "
            "for coverage review only and keep runtime observations behind a separate "
            "approved live-ops brief"
        ),
        "snapshot_prep_checks": [
            "aggregate only by copied/redacted event kind, scalar field mask, accepted/rejected counts, and bounded non-identifying buckets",
            "keep pin codes, VerifyPinCode.ReturnValue, player/controller/character refs, structure identity, object refs, FName/GObjects indices, raw params, locations, and exact timestamps redacted or absent",
            "keep StructureEvents SDK, structure handles, lookup, mutation, placement denial, collision policy, return override, and ResourceHandle blocked",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Structure aggregate/census SDK, public StructureEvents, "
            "structure handles, identity, lookup, ResourceHandle, mutation, return override, "
            "runtime hooks, or release readiness"
        ),
    },
    "structure-build-policy-offline-intake": {
        "classification": "structure_build_policy_offline_intake_candidate",
        "why_blocked": [
            "planning_guidance_only",
            "not_release_readiness_target",
            "missing_committed_sanitized_snapshot_coverage",
            "missing_distinct_second_source_layout",
            "placement_struct_redaction_policy_unproven",
            "copied_payload_policy_unproven",
            "public_structureevents_sdk_blocked",
            "build_denial_return_override_policy_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "approved non-protected copied/offline core or complete core evidence-pack "
            "manifest for exactly IsAllowedToBuild, BPIsAllowedToBuild, and "
            "BPIsAllowedToBuildEx; regenerate sanitized snapshots only after reflected "
            "owners are proven"
        ),
        "snapshot_prep_checks": [
            "compare exactly PrimalStructure.IsAllowedToBuild, PrimalStructure.BPIsAllowedToBuild, and PrimalStructure.BPIsAllowedToBuildEx through --target-set structure-build-policy-offline-intake",
            "treat APrimalStructure seeds as dictionary clues only until sanitized snapshots prove the reflected owner",
            "keep placement structs, location vectors, player/controller context, object refs, arrays, raw params, and UE pointers redacted or recognition-only",
            "keep StructureEvents, build-policy SDK, enforcement, mutation, return override, structure identity, lookup, and ResourceHandle blocked",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote StructureEvents, build-policy SDK, enforcement, identity, "
            "lookup, ResourceHandle, mutation, return override, runtime hooks, release "
            "readiness, or public SDK readiness"
        ),
    },
    "mission-copied-bool-policy-slice": {
        "classification": "internal_mission_copied_bool_policy_candidate",
        "why_blocked": [
            "policy_slice_evidence_only",
            "consume_mode_only",
            "promote_mode_blocked",
            "not_release_readiness_target",
            "mission_payload_decoding_blocked",
            "public_mission_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            f"start with repo-local fixture readiness from {MISSION_COPIED_BOOL_FIXTURE_ROOT}; "
            "if consuming the reviewed external artifact, pass an explicit non-protected "
            f"--root/--manifest and require policy_manifest_sha256={MISSION_COPIED_BOOL_POLICY_MANIFEST_SHA256}, "
            f"artifact_pack_manifest_sha256={MISSION_COPIED_BOOL_ARTIFACT_PACK_MANIFEST_SHA256}; "
            "or refresh sanitized mission UFunction snapshots from distinct non-protected "
            "copied/offline artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set mission-copied-bool-policy-slice",
            "require AddPlayerToMission, BPAllowPlayerToLeaveMission, and BPOnPlayerRemovedFromMission layouts to be comparable",
            "keep GetPlayerUsableItems in mission-compact-intake as recognition-only; do not add it to the copied-bool policy slice",
            "keep player/controller/character object refs, item arrays, mission payload identity, and raw params redacted or recognition-only",
            "require distinct artifact identity before any second-source readiness claim",
            "consume-only means offline artifact or sanitized snapshot reads; do not substitute runtime probes, live /servidor/ark inputs, or public SDK layouts",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Mission SDK, mission payload decoding, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set expansion"
        ),
    },
    "structure-observer-intake": {
        "classification": "release_gameplay_policy_structure_observer",
        "why_blocked": [
            "structure_observer_layout_evidence_only",
            "public_structureevents_sdk_blocked",
            "pincode_player_structure_identity_redaction_required",
            "identity_lookup_resourcehandle_blocked",
            "mutation_return_override_blocked",
            "runtime_producer_validation_requires_separate_approval",
        ],
        "next_offline_input": (
            "use distinct sanitized offline snapshots for the six structure-observer targets; "
            "keep runtime/copied-event validation behind a separate approved debug-window brief"
        ),
        "snapshot_prep_checks": [
            "compare only AllowStructureAccess, IsAllowedToDemolish, SetVariant, AllowToggleActivation, VerifyPinCode, and CanSeat through --target-set structure-observer-intake",
            "treat release readiness as the narrow copied/redacted GameplayPolicyEvent lane, not a public StructureEvents SDK",
            "keep pin codes, player context, structure identity, object refs, strings, arrays, raw params, and UE pointers redacted or recognition-only",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "keep build placement policy targets such as IsAllowedToBuild out of this target set",
            "runtime producer validation still requires a separate gated debug-window brief",
        ],
        "non_claim": (
            "does not promote public StructureEvents, Structure SDK, pincode/player identity exposure, "
            "identity, lookup, ResourceHandle, mutation, return override, runtime validation, or target-set expansion"
        ),
    },
    "transfer-scriptstruct": {
        "classification": "internal_transfer_scriptstruct_layout_only_candidate",
        "why_blocked": [
            "internal_layout_evidence_only",
            "not_release_readiness_target",
            "scriptstruct_layout_candidate_only",
            "transfer_scriptstruct_payload_decode_blocked",
            "item_net_info_excluded",
            "copied_data_policy_unproven",
            "lifecycle_privacy_policy_unproven",
            "promotion_gate_blocked",
            "public_transfer_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "sanitized ARKTributeDino and ArkTributePlayerData ScriptStruct snapshots "
            "from a distinct non-protected offline artifact with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare only PrimalLocalProfile.ARKTributeDino and PrimalLocalProfile.ArkTributePlayerData through --target-set transfer-scriptstruct",
            "keep ItemNetInfo explicitly excluded until a separate transfer payload decoding and ownership policy exists",
            "treat bool-tail metadata as redacted transfer payload layout only, not copied scalar evidence",
            "keep transferred player/dino payloads, inventory data, cross-map state, object refs, strings, arrays, raw params, and UE pointers redacted or recognition-only",
            "keep public Transfer SDK, ScriptStruct SDK, transfer payload decoding, ResourceHandle, object identity, mutation, and return override blocked",
            "keep evidence internal until copied-data, lifecycle, privacy, and promotion gates pass",
            "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
            "require distinct artifact identity before any second-source layout claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Transfer SDK, public ScriptStruct SDK, transfer payload "
            "decoding, ItemNetInfo, identity, lookup, ResourceHandle, mutation, return "
            "override, runtime hooks, release readiness, public SDK readiness, or v1 completion"
        ),
    },
    "transfer-baccept-only-policy-slice": {
        "classification": "internal_transfer_baccept_policy_candidate",
        "why_blocked": [
            "internal_layout_evidence_only",
            "policy_slice_evidence_only",
            "not_release_readiness_target",
            "missing_distinct_second_source_layout",
            "transfer_payload_decoding_blocked",
            "public_transfer_sdk_blocked",
            "runtime_observation_requires_separate_approval",
        ],
        "next_offline_input": (
            "sanitized ServerTransferredPlayerConfirmationResult snapshots from distinct "
            "non-protected copied/offline artifacts with complete artifact identity"
        ),
        "snapshot_prep_checks": [
            "compare schema-qualified targets through --target-set transfer-baccept-only-policy-slice",
            "require the bAccept bool layout to be comparable and backed by candidate-uobject membership",
            "keep transferred player payloads, inventory/dino data, object refs, arrays, and raw params redacted or recognition-only",
            "require distinct artifact identity before any second-source readiness claim",
            "do not use this target set for release/readiness or public SDK promotion gates",
        ],
        "non_claim": (
            "does not promote Transfer SDK, transfer payload decoding, identity, lookup, mutation, "
            "return override, runtime hooks, or target-set expansion"
        ),
    },
}

INTERNAL_TARGET_SET_MODULE_GUIDANCE = {
    "buff-breadth-intake": {
        "classification": "internal_buff_layout_only_candidate",
        "module": "Buff",
        "redactions": "buff payloads, inventory/add/prevent context, object refs, strings, arrays, raw params, and UE pointers",
    },
    "buff-compact-intake": {
        "classification": "internal_buff_layout_only_candidate",
        "module": "Buff",
        "redactions": "buff payloads, inventory context, object refs, strings, arrays, raw params, and UE pointers",
    },
    "dino-compact-intake": {
        "classification": "internal_dino_layout_only_candidate",
        "module": "Dino",
        "redactions": "rider/passenger identity, carried actor identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "inventory-action-compact-intake": {
        "classification": "internal_inventory_action_layout_only_candidate",
        "module": "Inventory",
        "redactions": "inventory item identity, actor identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "item-compact-intake": {
        "classification": "internal_item_layout_only_candidate",
        "module": "Item",
        "redactions": "item identity, inventory identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "mission-compact-intake": {
        "classification": "internal_mission_layout_only_candidate",
        "module": "Mission",
        "redactions": "player/controller/character object refs, item arrays, mission payload identity, raw params, and UE pointers",
    },
    "structure-nonpin-copied-scalar-policy-slice": {
        "classification": "internal_structure_scalar_layout_only_candidate",
        "module": "Structure",
        "redactions": "pin codes, player context, structure identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "structure-return-only-policy-slice": {
        "classification": "internal_structure_return_layout_only_candidate",
        "module": "Structure",
        "redactions": "player context, structure identity, object refs, strings, arrays, raw params, and UE pointers",
    },
    "transfer-scriptstruct": {
        "classification": "internal_transfer_scriptstruct_layout_only_candidate",
        "module": "Transfer",
        "redactions": "transferred player/dino payloads, inventory data, object refs, strings, arrays, raw params, and UE pointers",
    },
    "transfer-ufunction-intake": {
        "classification": "internal_transfer_layout_only_candidate",
        "module": "Transfer",
        "redactions": "transferred player/dino payloads, inventory data, object refs, strings, arrays, raw params, and UE pointers",
    },
    "tribe-compact-intake": {
        "classification": "internal_tribe_layout_only_candidate",
        "module": "Tribe",
        "redactions": "player ids, platform ids, names, tribe ids, online-list values, object refs, arrays, strings, raw params, and UE pointers",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two sanitized reflection snapshot roots without reading cores or touching servers."
    )
    parser.add_argument("--base-root", type=Path, help="Baseline snapshot root or single snapshot file.")
    parser.add_argument("--candidate-root", type=Path, help="Second-source snapshot root or file.")
    parser.add_argument(
        "--allow-ark-sha-mismatch",
        action="store_true",
        help="Do not mark targets inconclusive when evidence.ark_binary_sha256 differs.",
    )
    parser.add_argument(
        "--strict-identity-indices",
        action="store_true",
        help="Also require FName/object identity indices to match where snapshots carry them.",
    )
    parser.add_argument(
        "--target",
        action="append",
        default=[],
        help=(
            "Only compare an exact target. Accepts Outer.Name or schema:Outer.Name. "
            "Repeatable."
        ),
    )
    parser.add_argument(
        "--target-set",
        action="append",
        default=[],
        choices=sorted(TARGET_SETS),
        help="Add a named target group. Repeatable.",
    )
    parser.add_argument(
        "--readiness-report",
        action="store_true",
        help="Summarize current snapshot coverage and second-source readiness by module.",
    )
    parser.add_argument(
        "--fail-on-readiness-gaps",
        action="store_true",
        help=(
            "With --readiness-report, return non-zero when requested targets are blocked, "
            "missing, inconclusive, or rejected. Use this for promotion gates."
        ),
    )
    parser.add_argument(
        "--fail-on-base-readiness-gaps",
        action="store_true",
        help=(
            "With --readiness-report, return non-zero when requested base target sets are "
            "empty or have blocked/missing/non-comparable committed snapshots. Does not "
            "require candidate second-source evidence."
        ),
    )
    parser.add_argument(
        "--planning-layout-intake",
        action="store_true",
        help=(
            "With --readiness-report, evaluate planning-only target sets as consume-only "
            "layout planning evidence. This is not a promotion gate."
        ),
    )
    parser.add_argument(
        "--list-target-sets",
        action="store_true",
        help="List named target sets and exit without reading snapshot roots.",
    )
    parser.add_argument(
        "--list-target-guidance",
        action="store_true",
        help=(
            "List deferred-target blocker guidance and exit without reading snapshot roots. "
            "Use --target to filter."
        ),
    )
    parser.add_argument(
        "--observed-fname-chain",
        help=(
            "Comma-separated observed property FName indices from a copied diagnostic line. "
            "Compares one target against --base-root as planning-only, non-promotional evidence."
        ),
    )
    parser.add_argument(
        "--observed-fname-chain-occurrences",
        type=int,
        help=(
            "Number of copied diagnostic lines that repeated the same --observed-fname-chain. "
            "This count is diagnostic-only and does not make the report second-source evidence."
        ),
    )
    parser.add_argument(
        "--observed-fname-target",
        default=DEFAULT_OBSERVED_FNAME_TARGET,
        help=(
            "Target to use with --observed-fname-chain. Accepts Outer.Name or schema:Outer.Name. "
            f"Default: {DEFAULT_OBSERVED_FNAME_TARGET}."
        ),
    )
    parser.add_argument(
        "--lifecycle-snapshot-root-check",
        action="store_true",
        help=(
            "Validate the distinct sanitized offline UFunction snapshot-root requirement for "
            "ShooterGameMode.HandleNewPlayer and ShooterGameMode.OnLogout. This is not runtime "
            "or public SDK readiness evidence."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def expand_target_filters(targets: list[str], target_sets: list[str]) -> set[str]:
    filters = set(targets)
    for target_set in target_sets:
        filters.update(TARGET_SETS[target_set])
    validate_target_filters(filters)
    return filters


def validate_target_filters(filters: set[str]) -> None:
    for target in sorted(filters):
        if ":" not in target:
            continue
        schema, _, short_key = target.partition(":")
        if schema not in SUPPORTED_SCHEMAS:
            raise SystemExit(f"unsupported target filter schema: {schema}")
        if not short_key:
            raise SystemExit(f"schema-qualified target filter missing target: {target}")


def is_under_path(path: Path, root: Path) -> bool:
    return protected_paths.is_under_path(path, root)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_input_path(label: str, path: Path) -> None:
    protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=PROTECTED_SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        message=f"{label} must not read from protected live-server path: {path}",
    )


def reject_snapshot_input_path(label: str, path: Path) -> None:
    reject_protected_input_path(label, path)
    protected_paths.reject_symlink_component(path, label)


class SymlinkInputPathError(OSError):
    def __init__(self, component: Path) -> None:
        super().__init__(errno.ELOOP, f"path must not be a symlink: {component}")
        self.component = component


def open_regular_file_no_symlink(path: Path):
    symlink_component = protected_paths.first_symlink_component(path)
    if symlink_component is not None:
        raise SymlinkInputPathError(symlink_component)

    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() else expanded.absolute()
    if not candidate.name:
        raise OSError(errno.EINVAL, f"path must be a regular file: {candidate}")

    common_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    directory_flags = common_flags | getattr(os, "O_DIRECTORY", 0)
    file_flags = common_flags
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
        file_flags |= os.O_NOFOLLOW

    parent_fd: int | None = None
    try:
        parent_fd = os.open(candidate.anchor, directory_flags)
        for part in candidate.parts[1:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(candidate.name, file_flags, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise SymlinkInputPathError(candidate) from exc
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)

    try:
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise OSError(errno.EINVAL, f"path must be a regular file: {candidate}")
        return os.fdopen(fd, "rb")
    except Exception:
        os.close(fd)
        raise


def read_json_input_no_symlink(path: Path, *, label: str) -> Any:
    try:
        with open_regular_file_no_symlink(path) as handle:
            return json.loads(handle.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    except SymlinkInputPathError as exc:
        raise SystemExit(f"{label} must not be a symlink: {exc.component}") from exc
    except OSError as exc:
        raise SystemExit(f"{path}: unreadable JSON: {exc}") from exc


def target_set_listing_entry(name: str, targets: tuple[str, ...]) -> dict[str, Any]:
    entry = {
        "name": name,
        "module_lane": target_set_module_lane(name),
        "readiness_classification": target_set_readiness_classification(name),
        "release_readiness": name in RELEASE_READINESS_TARGET_SETS,
        "readiness_scope": (
            "layout_only"
            if name in RELEASE_READINESS_TARGET_SETS
            else target_set_readiness_classification(name)
        ),
        "second_source_layout_evidence": False,
        **READINESS_FALSE_FLAGS,
        **READINESS_ZERO_FIELDS,
        "targets": list(targets),
    }
    if name == "players-lifecycle-anchor-candidates":
        entry["lifecycle_source_policy"] = player_lifecycle_anchor_source_policy()
    return entry


def target_set_report() -> dict[str, Any]:
    return {
        "schema": "obelisk.reflection-snapshot-target-sets.v1",
        "catalog_scope": "named_target_set_catalog_only",
        "evidence_scope": TARGET_SET_CATALOG_EVIDENCE_SCOPE,
        "target_set_revision_schema": TARGET_SET_REVISION_SCHEMA,
        "target_set_revision_source": TARGET_SET_REVISION_SOURCE,
        "target_set_revision_target_schema_filter": "all",
        "target_set_revision_source_sha256": target_set_revision_source_sha256(
            list(TARGET_SETS),
            schema_filter=None,
        ),
        "readiness_effect": "none",
        "second_source_layout_evidence": False,
        "not_second_source": True,
        **READINESS_FALSE_FLAGS,
        **READINESS_ZERO_FIELDS,
        "does_not_satisfy_readiness": list(PLANNING_LAYOUT_DOES_NOT_SATISFY),
        "catalog_hygiene": target_set_catalog_hygiene_report(),
        "not_promoted_surfaces": sorted(READINESS_NOT_PROMOTED_SURFACES),
        "non_claims": list(READINESS_NON_CLAIMS),
        "target_sets": [target_set_listing_entry(name, targets) for name, targets in sorted(TARGET_SETS.items())],
    }


def target_set_catalog_guardrail_issues() -> list[dict[str, object]]:
    return target_set_catalog_hygiene_issues(
        target_sets=TARGET_SETS,
        module_lanes=TARGET_SET_MODULE_LANES,
        planning_only=PLANNING_ONLY_TARGET_SETS,
        release_readiness=RELEASE_READINESS_TARGET_SETS,
        supported_schemas=SUPPORTED_SCHEMAS,
    )


def target_set_catalog_hygiene_report() -> dict[str, Any]:
    issues = target_set_catalog_guardrail_issues()
    return {
        "guardrail": TARGET_SET_CATALOG_GUARDRAIL,
        "status": "blocked" if issues else "clean",
        "checked_target_sets": len(TARGET_SETS),
        "checked_schemas": sorted(SUPPORTED_SCHEMAS),
        "issues": issues,
    }


def reject_target_set_catalog_hygiene_issues() -> None:
    issues = target_set_catalog_guardrail_issues()
    if not issues:
        return
    reasons = sorted({str(issue.get("reason", "unknown")) for issue in issues})
    raise SystemExit(
        "target-set catalog hygiene failed: "
        + ", ".join(reasons)
        + "; fix scripts/reflection_target_sets.py before comparing snapshots or claiming target-set coverage"
    )


def target_guidance_report(target_filters: set[str]) -> dict[str, Any]:
    guidance = []
    for target in sorted(TARGET_BLOCKER_GUIDANCE):
        if matches_target_filter(target, target_filters):
            guidance.append({"target": target, **(target_blocker_guidance(target) or {})})
    return {
        "schema": "obelisk.reflection-target-guidance.v1",
        "guidance_scope": "offline_planning_only",
        "evidence_scope": TARGET_GUIDANCE_EVIDENCE_SCOPE,
        "readiness_effect": "none",
        "second_source_layout_evidence": False,
        "not_second_source": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "does_not_satisfy_readiness": list(PLANNING_LAYOUT_DOES_NOT_SATISFY),
        "target_filters": sorted(target_filters),
        "not_promoted_surfaces": sorted(READINESS_NOT_PROMOTED_SURFACES),
        "non_claims": list(READINESS_NON_CLAIMS),
        "target_set_guidance": [],
        "targets": guidance,
    }


def target_set_blocker_guidance(target_set: str) -> dict[str, Any] | None:
    guidance = TARGET_SET_BLOCKER_GUIDANCE.get(target_set)
    if guidance is None:
        if target_set not in INTERNAL_LAYOUT_ONLY_TARGET_SETS:
            return None
        internal_guidance = INTERNAL_TARGET_SET_MODULE_GUIDANCE.get(target_set)
        if internal_guidance is None:
            return None
        module = internal_guidance["module"]
        return {
            "classification": internal_guidance["classification"],
            "why_blocked": [
                "internal_layout_evidence_only",
                "not_release_readiness_target",
                "copied_data_policy_unproven",
                "lifecycle_privacy_policy_unproven",
                "promotion_gate_blocked",
                f"public_{module.lower()}_sdk_blocked",
                "runtime_observation_requires_separate_approval",
            ],
            "next_offline_input": (
                "sanitized offline snapshots from distinct non-protected artifacts with "
                "complete artifact identity"
            ),
            "snapshot_prep_checks": [
                f"compare schema-qualified targets through --target-set {target_set} for internal coverage review only",
                f"keep {internal_guidance['redactions']} redacted or recognition-only",
                "keep evidence internal until copied-data, lifecycle, privacy, and promotion gates pass",
                "require target, class, outer, every property, and nested struct/array candidates to be candidate-uobject",
                "require distinct artifact identity before any second-source layout claim",
                "do not use this target set for release/readiness or public SDK promotion gates",
            ],
            "non_claim": (
                f"does not promote {module} SDK, identity, lookup, mutation, return override, "
                "runtime hooks, or release readiness"
            ),
        }
    copied: dict[str, Any] = {}
    for key, value in guidance.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def target_set_guidance_report(target_sets: list[str]) -> list[dict[str, Any]]:
    guidance = []
    for target_set in sorted(target_sets):
        item = target_set_blocker_guidance(target_set)
        if item is not None:
            guidance.append({"target_set": target_set, **item})
    return guidance


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def reject_duplicate_target_set_guidance_filters(target_sets: list[str]) -> None:
    duplicates = duplicate_values(target_sets)
    if duplicates:
        raise SystemExit("duplicate target-set guidance filter(s): " + ", ".join(duplicates))


def reject_invalid_target_set_filters(target_sets: list[str]) -> None:
    duplicates = duplicate_values(target_sets)
    if duplicates:
        raise SystemExit("duplicate target-set filter(s): " + ", ".join(duplicates))
    unknown = sorted(target_set for target_set in target_sets if target_set not in TARGET_SETS)
    if unknown:
        raise SystemExit("unknown target-set filter(s): " + ", ".join(unknown))


def reject_duplicate_target_guidance_filters(targets: list[str]) -> None:
    duplicates = duplicate_values(targets)
    if duplicates:
        raise SystemExit("duplicate target guidance filter(s): " + ", ".join(duplicates))


def unmatched_target_guidance_filters(targets: list[str]) -> list[str]:
    return [
        target
        for target in targets
        if not any(
            matches_target_filter(guidance_target, {target})
            for guidance_target in TARGET_BLOCKER_GUIDANCE
        )
    ]


def target_blocker_guidance(target: str) -> dict[str, Any] | None:
    guidance = TARGET_BLOCKER_GUIDANCE.get(target)
    if guidance is None:
        return None
    copied: dict[str, Any] = {}
    for key, value in guidance.items():
        copied[key] = list(value) if isinstance(value, list) else value
    return copied


def snapshot_paths(root: Path) -> list[Path]:
    reject_snapshot_input_path("snapshot root", root)
    if root.is_file():
        return [root]
    if not root.exists():
        raise SystemExit(f"snapshot root does not exist: {root}")
    paths = []
    for path in root.rglob("*.snapshot.json"):
        reject_snapshot_input_path("snapshot", path)
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def load_snapshot(path: Path) -> dict[str, Any]:
    reject_snapshot_input_path("snapshot", path)
    payload = read_json_input_no_symlink(path, label="snapshot")
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object snapshot")
    if payload.get("schema") not in SUPPORTED_SCHEMAS:
        raise SystemExit(f"{path}: unsupported snapshot schema: {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{path}: expected exactly one target")
    return payload


def target_key(payload: dict[str, Any]) -> str:
    target = payload["targets"][0]
    identity = target.get("target")
    if not isinstance(identity, dict):
        raise SystemExit("snapshot target missing identity object")
    schema = payload.get("schema")
    outer = identity.get("outer_name")
    name = identity.get("name")
    if not isinstance(outer, str) or not isinstance(name, str):
        raise SystemExit("snapshot target missing string outer_name/name")
    return f"{schema}:{outer}.{name}"


def load_snapshot_set(root: Path) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    for path in snapshot_paths(root):
        payload = load_snapshot(path)
        key = target_key(payload)
        if key in snapshots:
            raise SystemExit(f"duplicate snapshot target {key}: {snapshots[key]['path']} and {path}")
        snapshots[key] = {"path": str(path), "payload": payload}
    return snapshots


def schema_label(schema: str) -> str:
    if schema == "obelisk.ufunction-chain.snapshot.v1":
        return "ufunction"
    if schema == "obelisk.scriptstruct-chain.snapshot.v1":
        return "scriptstruct"
    return schema


def module_from_path(path: str) -> str:
    parts = Path(path).parts
    if len(parts) >= 2:
        return parts[-2]
    return "<unknown>"


def normalize_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def is_negative_or_blocker_text(value: str) -> bool:
    return bool(NEGATED_OR_BLOCKED_RE.search(value))


def is_positive_status_alias(value: str) -> bool:
    normalized = re.sub(r"[\s_]+", "-", value.strip().lower())
    return (
        normalized in POSITIVE_STATUS_VALUES
        or normalized.endswith("-ready")
    )


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        if is_negative_or_blocker_text(value):
            return False
        return is_positive_status_alias(value) or (
            CLAIM_SUBJECT_RE.search(value) is not None
            and AFFIRMATIVE_CONTEXT_RE.search(value) is not None
        )
    return False


def claim_sanitization_reasons(value: Any, *, path: str = "$") -> list[str]:
    reasons: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            key_text = str(key)
            normalized_key = normalize_claim_key(key_text)
            if child_path in CLAIM_SCAN_EXEMPT_PATHS:
                continue
            if normalized_key == "status" and isinstance(child, str) and is_positive_status_alias(child):
                reasons.append(f"positive_status_alias:{child_path}")
            if FORBIDDEN_CLAIM_KEY_RE.search(normalized_key) and is_positive_claim_value(child):
                reasons.append(f"readiness_alias_overclaim:{child_path}")
            reasons.extend(claim_sanitization_reasons(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reasons.extend(claim_sanitization_reasons(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and is_positive_claim_value(value):
        reasons.append(f"forbidden_positive_claim_value:{path}")
    return reasons


def raw_sanitization_reasons(value: Any, *, key: str | None = None, path: str = "") -> list[str]:
    reasons: list[str] = []
    if key in FORBIDDEN_KEYS:
        reasons.append(f"forbidden_key:{path or key}")
    if isinstance(value, dict):
        for child_key, child in value.items():
            child_path = f"{path}.{child_key}" if path else str(child_key)
            reasons.extend(raw_sanitization_reasons(child, key=str(child_key), path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            reasons.extend(raw_sanitization_reasons(child, path=f"{path}[{index}]"))
    elif isinstance(value, str) and key not in HEX_METADATA_KEYS and ADDRESS_RE.search(value):
        reasons.append(f"raw_address:{path}")
    return reasons


def property_layout(prop: dict[str, Any], *, strict_identity_indices: bool) -> dict[str, Any]:
    result = {
        "name": prop.get("name"),
        "class_name": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "array_dim": prop.get("array_dim"),
        "property_flags": prop.get("property_flags"),
        "bool_field_size": prop.get("bool_field_size"),
        "bool_byte_offset": prop.get("bool_byte_offset"),
        "native_bool": prop.get("native_bool"),
        "byte_mask": prop.get("byte_mask"),
        "field_mask": prop.get("field_mask"),
        "status": prop.get("status"),
        "reject_reasons": prop.get("reject_reasons", []),
        "membership_status": prop.get("membership_status"),
        "class_membership_status": prop.get("class_membership_status"),
        "outer_membership_status": prop.get("outer_membership_status"),
    }
    if strict_identity_indices:
        result.update(
            {
                "object_index": prop.get("object_index"),
                "name_index": prop.get("name_index"),
                "class_name_index": prop.get("class_name_index"),
                "class_object_index": prop.get("class_object_index"),
            }
        )
    for nested_key in ("array_inner_candidate", "struct_type_candidate"):
        nested = prop.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_identity_key = "inner_property" if nested_key == "array_inner_candidate" else "struct_type"
        nested_identity = nested.get(nested_identity_key)
        if not isinstance(nested_identity, dict):
            continue
        result[nested_key] = {
            "status": nested.get("status"),
            "reject_reasons": nested.get("reject_reasons", []),
            "membership_status": nested.get("membership_status"),
            nested_identity_key: {
                "name": nested_identity.get("name"),
                "class_name": nested_identity.get("class_name"),
            },
        }
        if strict_identity_indices:
            result[nested_key][nested_identity_key]["object_index"] = nested_identity.get("object_index")
            result[nested_key][nested_identity_key]["name_index"] = nested_identity.get("name_index")
            result[nested_key][nested_identity_key]["class_name_index"] = nested_identity.get("class_name_index")
            result[nested_key][nested_identity_key]["class_object_index"] = nested_identity.get("class_object_index")
    return result


def property_block_reasons(prop: dict[str, Any], *, index: int) -> list[str]:
    reasons: list[str] = []
    prefix = f"property[{index}]"
    if prop.get("status") != "candidate":
        reasons.append(f"{prefix}_status_{prop.get('status')}")
    if prop.get("reject_reasons", []):
        reasons.append(f"{prefix}_has_reject_reasons")
    if prop.get("class_name") == "BoolProperty":
        bool_semantics = prop.get("bool_property_semantics")
        if not isinstance(bool_semantics, dict):
            reasons.append(f"{prefix}_bool_property_semantics_missing")
        else:
            if bool_semantics.get("status") != "candidate":
                reasons.append(f"{prefix}_bool_property_semantics_status_{bool_semantics.get('status')}")
            if bool_semantics.get("reject_reasons", []):
                reasons.append(f"{prefix}_bool_property_semantics_has_reject_reasons")
            for tail_key in ("bool_field_size", "bool_byte_offset"):
                if not isinstance(bool_semantics.get(tail_key), int):
                    reasons.append(f"{prefix}_bool_property_semantics_{tail_key}_missing")
        for tail_key in ("bool_field_size", "bool_byte_offset"):
            if not isinstance(prop.get(tail_key), int):
                reasons.append(f"{prefix}_{tail_key}_missing")
            elif (
                isinstance(bool_semantics, dict)
                and isinstance(bool_semantics.get(tail_key), int)
                and prop.get(tail_key) != bool_semantics.get(tail_key)
            ):
                reasons.append(f"{prefix}_{tail_key}_mismatches_bool_property_semantics")
        if prop.get("native_bool") not in (True, False):
            reasons.append(f"{prefix}_native_bool_missing")
        for mask_key in ("byte_mask", "field_mask"):
            mask = prop.get(mask_key)
            if not isinstance(mask, str) or BOOL_MASK_RE.fullmatch(mask) is None or int(mask, 16) == 0:
                reasons.append(f"{prefix}_{mask_key}_missing_or_zero")
    for membership_key in ("membership_status", "class_membership_status", "outer_membership_status"):
        membership = prop.get(membership_key)
        if membership != "candidate-uobject":
            reasons.append(f"{prefix}_{membership_key}_{membership if membership is not None else 'missing'}")
    required_nested_candidates = {
        "ArrayProperty": "array_inner_candidate",
        "StructProperty": "struct_type_candidate",
    }
    required_nested_key = required_nested_candidates.get(prop.get("class_name"))
    if required_nested_key is not None and not isinstance(prop.get(required_nested_key), dict):
        reasons.append(f"{prefix}_{required_nested_key}_missing")
    for nested_key in ("array_inner_candidate", "struct_type_candidate"):
        nested = prop.get(nested_key)
        if not isinstance(nested, dict):
            continue
        nested_prefix = f"{prefix}_{nested_key}"
        nested_identity_key = "inner_property" if nested_key == "array_inner_candidate" else "struct_type"
        if nested.get("status") != "candidate":
            reasons.append(f"{nested_prefix}_status_{nested.get('status')}")
        if nested.get("reject_reasons", []):
            reasons.append(f"{nested_prefix}_has_reject_reasons")
        membership = nested.get("membership_status")
        if membership != "candidate-uobject":
            reasons.append(f"{nested_prefix}_membership_status_{membership if membership is not None else 'missing'}")
        nested_identity = nested.get(nested_identity_key)
        if not isinstance(nested_identity, dict):
            reasons.append(f"{nested_prefix}_missing_{nested_identity_key}")
        else:
            for field in ("object_index", "name_index"):
                if type(nested_identity.get(field)) is not int:
                    reasons.append(f"{nested_prefix}_{nested_identity_key}_{field}_missing")
            for field in ("name", "class_name"):
                value = nested_identity.get(field)
                if not isinstance(value, str) or not value:
                    reasons.append(f"{nested_prefix}_{nested_identity_key}_{field}_missing")
    return reasons


def evidence_reasons(payload: dict[str, Any]) -> list[str]:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return ["missing_evidence"]
    reasons: list[str] = []
    ark_binary_sha256 = evidence.get("ark_binary_sha256")
    if not isinstance(ark_binary_sha256, str):
        reasons.append("missing_ark_binary_sha256")
    elif not is_sha256(ark_binary_sha256):
        reasons.append("invalid_ark_binary_sha256")
    artifact_kind = evidence.get("artifact_kind")
    if artifact_kind is None:
        reasons.append("missing_artifact_kind")
    elif artifact_kind not in ALLOWED_ARTIFACT_KINDS:
        reasons.append(f"invalid_artifact_kind_{artifact_kind}")
    artifact_sha256 = evidence.get("artifact_sha256")
    if artifact_sha256 is None:
        reasons.append("missing_artifact_sha256")
    elif not is_sha256(artifact_sha256):
        reasons.append("invalid_artifact_sha256")
    for field in ("capture_id", "evidence_pack_id"):
        value = evidence.get(field)
        if value is None:
            reasons.append(f"missing_{field}")
        elif not is_safe_artifact_id(value):
            reasons.append(f"invalid_{field}")
    if evidence.get("source") != "offline_core":
        reasons.append(f"evidence_source_{evidence.get('source')}")
    if evidence.get("status") != "candidate-only":
        reasons.append(f"evidence_status_{evidence.get('status')}")
    generated_by = evidence.get("generated_by")
    if generated_by != "scripts/inspect_core_ufunctions.py --snapshot-json":
        reasons.append(f"evidence_generated_by_{generated_by}")
    return reasons


def comparable_layout(payload: dict[str, Any], *, strict_identity_indices: bool) -> tuple[dict[str, Any] | None, list[str]]:
    raw_reasons = raw_sanitization_reasons(payload)
    claim_reasons = claim_sanitization_reasons(payload)
    if raw_reasons or claim_reasons:
        return None, raw_reasons + claim_reasons
    invalid_evidence = evidence_reasons(payload)
    if invalid_evidence:
        return None, invalid_evidence
    target = payload["targets"][0]
    identity = target.get("target")
    chain = target.get("property_chain")
    if not isinstance(identity, dict) or not isinstance(chain, dict):
        return None, ["missing_target_identity_or_property_chain"]
    if target.get("status") != "candidate":
        return None, [f"target_status_{target.get('status')}"]
    membership = target.get("membership")
    if membership != {"target": "candidate-uobject", "class": "candidate-uobject", "outer": "candidate-uobject"}:
        return None, ["target_membership_not_candidate"]
    if chain.get("status") != "candidate":
        return None, [f"property_chain_status_{chain.get('status')}"]
    if chain.get("reject_reasons", []):
        return None, ["property_chain_has_reject_reasons"]
    properties = chain.get("properties")
    if not isinstance(properties, list):
        return None, ["missing_property_list"]
    property_reasons: list[str] = []
    for index, prop in enumerate(properties):
        if not isinstance(prop, dict):
            property_reasons.append(f"property[{index}]_not_object")
            continue
        property_reasons.extend(property_block_reasons(prop, index=index))
    if property_reasons:
        return None, property_reasons

    layout = {
        "schema": payload.get("schema"),
        "inspection_mode": target.get("inspection_mode"),
        "status": target.get("status"),
        "reject_reasons": target.get("reject_reasons", []),
        "membership": membership,
        "target": {
            "name": identity.get("name"),
            "class_name": identity.get("class_name"),
            "outer_name": identity.get("outer_name"),
            "outer_class_name": identity.get("outer_class_name"),
        },
        "property_chain": {
            "status": chain.get("status"),
            "reject_reasons": chain.get("reject_reasons", []),
            "expected_count": chain.get("expected_count"),
            "observed_count": chain.get("observed_count"),
            "properties": [
                property_layout(prop, strict_identity_indices=strict_identity_indices)
                for prop in properties
            ],
        },
    }
    if strict_identity_indices:
        layout["target"].update(
            {
                "object_index": identity.get("object_index"),
                "name_index": identity.get("name_index"),
                "class_name_index": identity.get("class_name_index"),
                "class_object_index": identity.get("class_object_index"),
                "outer_name_index": identity.get("outer_name_index"),
                "outer_object_index": identity.get("outer_object_index"),
            }
        )
    if payload.get("schema") == "obelisk.ufunction-chain.snapshot.v1":
        layout.update(
            {
                "num_parms": target.get("num_parms"),
                "parms_size": target.get("parms_size"),
                "function_flags": target.get("function_flags"),
                "return_value_offset": target.get("return_value_offset"),
            }
        )
        layout["property_chain"]["parms_size"] = chain.get("parms_size")
    else:
        layout.update(
            {
                "properties_size": target.get("properties_size"),
                "min_alignment": target.get("min_alignment"),
            }
        )
        layout["property_chain"]["properties_size"] = chain.get("properties_size")
    return layout, []


def diff_layout(base: Any, candidate: Any, path: str = "") -> list[dict[str, Any]]:
    if type(base) is not type(candidate):
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    if isinstance(base, dict):
        diffs: list[dict[str, Any]] = []
        for key in sorted(set(base) | set(candidate)):
            diffs.extend(diff_layout(base.get(key), candidate.get(key), f"{path}.{key}" if path else key))
        return diffs
    if isinstance(base, list):
        diffs = []
        if len(base) != len(candidate):
            diffs.append({"path": f"{path}.length" if path else "length", "base": len(base), "candidate": len(candidate)})
        for index, (left, right) in enumerate(zip(base, candidate)):
            diffs.extend(diff_layout(left, right, f"{path}[{index}]"))
        return diffs
    if base != candidate:
        return [{"path": path or ".", "base": base, "candidate": candidate}]
    return []


def evidence_sha(payload: dict[str, Any]) -> Any:
    evidence = payload.get("evidence")
    return evidence.get("ark_binary_sha256") if isinstance(evidence, dict) else None


def evidence_artifact_identity(payload: dict[str, Any]) -> tuple[Any, ...] | None:
    identity = evidence_artifact_identity_dict(payload)
    if identity is None:
        return None
    return tuple(identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS)


def evidence_artifact_identity_dict(payload: dict[str, Any]) -> dict[str, str] | None:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return None
    values = {key: evidence.get(key) for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS}
    if not all(isinstance(value, str) and value for value in values.values()):
        return None
    return values  # type: ignore[return-value]


def shared_artifact_identity_reasons(base_payload: dict[str, Any], candidate_payload: dict[str, Any]) -> list[str]:
    base_identity = evidence_artifact_identity_dict(base_payload)
    candidate_identity = evidence_artifact_identity_dict(candidate_payload)
    if base_identity is None or candidate_identity is None:
        return []
    if tuple(base_identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS) == tuple(
        candidate_identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS
    ):
        return ["same_evidence_artifact_identity"]
    reasons: list[str] = []
    for key in ("artifact_sha256", "capture_id", "evidence_pack_id"):
        if base_identity[key] == candidate_identity[key]:
            reasons.append(f"same_evidence_{key}")
    return reasons


def matches_target_filter(key: str, filters: set[str]) -> bool:
    if not filters:
        return True
    _, _, short_key = key.partition(":")
    return key in filters or short_key in filters


def filtered_keys(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    target_filters: set[str],
) -> list[str]:
    available_keys = set(base) | set(candidate)
    keys = {key for key in available_keys if matches_target_filter(key, target_filters)}
    schema_qualified_filters = {target for target in target_filters if ":" in target}
    keys.update(schema_qualified_filters)
    if target_filters and not keys:
        raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(target_filters))}")
    unmatched_short_filters = []
    for target in target_filters:
        if ":" in target:
            continue
        if not any(key.partition(":")[2] == target for key in available_keys):
            unmatched_short_filters.append(target)
    if unmatched_short_filters:
        raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(unmatched_short_filters))}")
    return sorted(keys)


def compare_sets(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
    *,
    strict_identity_indices: bool,
    allow_ark_sha_mismatch: bool,
    target_filters: set[str],
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for key in filtered_keys(base, candidate, target_filters=target_filters):
        missing_reasons = []
        if key not in base:
            missing_reasons.append("missing_base_snapshot")
        if key not in candidate:
            missing_reasons.append("missing_candidate_snapshot")
        if missing_reasons:
            results.append({"target": key, "status": "inconclusive", "reasons": missing_reasons})
            continue
        if not allow_ark_sha_mismatch and evidence_sha(base[key]["payload"]) != evidence_sha(candidate[key]["payload"]):
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": ["ark_binary_sha256_mismatch"],
                }
            )
            continue
        base_artifact = evidence_artifact_identity(base[key]["payload"])
        candidate_artifact = evidence_artifact_identity(candidate[key]["payload"])
        artifact_reasons = []
        if base_artifact is None:
            artifact_reasons.append("missing_base_evidence_artifact_identity")
        if candidate_artifact is None:
            artifact_reasons.append("missing_candidate_evidence_artifact_identity")
        artifact_reasons.extend(shared_artifact_identity_reasons(base[key]["payload"], candidate[key]["payload"]))
        if artifact_reasons:
            results.append({"target": key, "status": "inconclusive", "reasons": artifact_reasons})
            continue
        base_layout, base_reasons = comparable_layout(base[key]["payload"], strict_identity_indices=strict_identity_indices)
        candidate_layout, candidate_reasons = comparable_layout(
            candidate[key]["payload"],
            strict_identity_indices=strict_identity_indices,
        )
        if base_reasons or candidate_reasons or base_layout is None or candidate_layout is None:
            results.append(
                {
                    "target": key,
                    "status": "inconclusive",
                    "reasons": [f"base:{reason}" for reason in base_reasons]
                    + [f"candidate:{reason}" for reason in candidate_reasons],
                }
            )
            continue
        diffs = diff_layout(base_layout, candidate_layout)
        if diffs:
            results.append({"target": key, "status": "rejected", "diffs": diffs})
        else:
            results.append({"target": key, "status": "accepted"})
    counts = {"accepted": 0, "rejected": 0, "inconclusive": 0}
    for result in results:
        counts[result["status"]] += 1
    return {
        "schema": "obelisk.reflection-snapshot-comparison.v1",
        "strict_identity_indices": strict_identity_indices,
        "allow_ark_sha_mismatch": allow_ark_sha_mismatch,
        "target_filters": sorted(target_filters),
        "counts": counts,
        "results": results,
    }


def payload_has_reflectionscanner_gate(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("gate_type") == "reflectionscanner_evidence_pack_v1":
            return True
        return any(payload_has_reflectionscanner_gate(child) for child in value.values())
    if isinstance(value, list):
        return any(payload_has_reflectionscanner_gate(child) for child in value)
    return False


def forbidden_lifecycle_input_reasons(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    schema = payload.get("schema")
    if schema in DIAGNOSTIC_ONLY_LIFECYCLE_SCHEMAS:
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    sidecar_reason = NON_SNAPSHOT_LIFECYCLE_SIDECAR_SCHEMA_REASONS.get(schema)
    if sidecar_reason is not None:
        reasons.append(sidecar_reason)
    if schema == "obelisk.player-principal-passive-snapshot.v1":
        reasons.append("passive_snapshot_manifest_not_sanitized_ufunction_snapshot")
    if schema in {
        "obelisk.reflection-snapshot-readiness.v1",
        "obelisk.reflection-snapshot-comparison.v1",
    }:
        reasons.append("layout_only_report_not_sanitized_lifecycle_snapshot_root")
    evidence_scope = payload.get("evidence_scope")
    if isinstance(evidence_scope, str) and evidence_scope in {
        READINESS_EVIDENCE_SCOPE,
        PLANNING_LAYOUT_INTAKE_EVIDENCE_SCOPE,
    }:
        reasons.append("layout_only_evidence_report_not_sanitized_lifecycle_snapshot_root")
    if evidence_scope == OBSERVED_FNAME_CHAIN_EVIDENCE_SCOPE:
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    if payload.get("artifact_role") == OBSERVED_FNAME_CHAIN_ARTIFACT_ROLE:
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    if payload.get("artifact_status") == "planning_diagnostic_unresolved":
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    if payload.get("observed_chain_source") == "copied_runtime_diagnostic_line":
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    runtime_summary = payload.get("runtime_observation_summary")
    if isinstance(runtime_summary, dict) and runtime_summary.get("diagnostic_only") is True:
        reasons.append("diagnostic_only_root_not_sanitized_lifecycle_snapshot_root")
    if payload_has_reflectionscanner_gate(payload):
        reasons.append("reflectionscanner_output_not_sanitized_lifecycle_snapshot_root")
    return reasons


def reject_forbidden_lifecycle_input_root(label: str, root: Path) -> None:
    reject_protected_input_path(label, root)
    if root.is_file():
        paths = [root]
    elif root.exists():
        paths = sorted(path for path in root.rglob("*.json") if path.is_file())
    else:
        paths = []
    for path in paths:
        protected_paths.reject_symlink_component(path, label)
        reject_protected_input_path(label, path)
        payload = read_json_input_no_symlink(path, label=label)
        if not isinstance(payload, dict):
            continue
        reasons = forbidden_lifecycle_input_reasons(payload)
        if reasons:
            raise SystemExit(
                f"{label} contains forbidden lifecycle input {path}: "
                + ", ".join(sorted(set(reasons)))
            )


def lifecycle_complete_identity(
    payload: dict[str, Any],
    *,
    label: str,
) -> tuple[dict[str, str] | None, list[str]]:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        return None, [f"{label}:missing_evidence"]

    reasons: list[str] = []
    ark_binary_sha256 = evidence.get("ark_binary_sha256")
    if not isinstance(ark_binary_sha256, str):
        reasons.append(f"{label}:missing_ark_binary_sha256")
    elif not is_sha256(ark_binary_sha256):
        reasons.append(f"{label}:invalid_ark_binary_sha256")

    artifact_kind = evidence.get("artifact_kind")
    if artifact_kind != "offline_core":
        reasons.append(f"{label}:artifact_kind_not_offline_core")

    artifact_sha256 = evidence.get("artifact_sha256")
    if not is_sha256(artifact_sha256):
        reasons.append(f"{label}:invalid_artifact_sha256")

    capture_id = evidence.get("capture_id")
    if not is_safe_artifact_id(capture_id):
        reasons.append(f"{label}:invalid_capture_id")

    evidence_pack_id = evidence.get("evidence_pack_id")
    if not is_safe_artifact_id(evidence_pack_id):
        reasons.append(f"{label}:invalid_evidence_pack_id")

    if reasons:
        return None, reasons
    return (
        {
            "ark_binary_sha256": str(ark_binary_sha256),
            "artifact_kind": str(artifact_kind),
            "artifact_sha256": str(artifact_sha256),
            "capture_id": str(capture_id),
            "evidence_pack_id": str(evidence_pack_id),
        },
        [],
    )


def lifecycle_snapshot_identity_record(
    snapshots: dict[str, dict[str, Any]],
    key: str,
    *,
    label: str,
) -> tuple[dict[str, str] | None, list[str]]:
    entry = snapshots.get(key)
    if entry is None:
        return None, [f"{label}:missing_snapshot"]
    return lifecycle_complete_identity(entry["payload"], label=label)


def lifecycle_artifact_identity_tuple(identity: dict[str, str]) -> tuple[str, ...]:
    return tuple(identity[key] for key in EVIDENCE_ARTIFACT_IDENTITY_KEYS)


def lifecycle_unique_artifact_identities(identities: list[dict[str, str]]) -> list[tuple[str, ...]]:
    return sorted({lifecycle_artifact_identity_tuple(identity) for identity in identities})


def offline_blocker_reason_counts(blockers: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for blocker in blockers:
        reason = blocker.get("reason")
        if not isinstance(reason, str) or not reason:
            reason = "unknown"
        raw_count = blocker.get("count", 1)
        count = raw_count if isinstance(raw_count, int) and raw_count > 0 else 1
        counts[reason] = counts.get(reason, 0) + count
    return dict(sorted(counts.items()))


def lifecycle_snapshot_next_offline_action(
    offline_satisfied: bool,
    *,
    candidate_extra_targets: list[str] | None = None,
    candidate_missing_targets: list[str] | None = None,
) -> dict[str, Any]:
    candidate_extra_targets = candidate_extra_targets or []
    candidate_missing_targets = candidate_missing_targets or []
    candidate_root_requirements = {
        "exact_required_targets_only": True,
        "required_targets": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS),
        "required_snapshot_filenames": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_FILENAMES),
        "missing_targets": list(candidate_missing_targets),
        "extra_target_count": len(candidate_extra_targets),
        "complete_offline_core_identity_required": True,
        "distinct_from_base_identity_required": True,
        "broad_root_or_report_input_accepted": False,
        "runtime_or_public_sdk_readiness_claim": False,
    }
    if offline_satisfied:
        return {
            "status": "offline_requirement_satisfied_planning_only",
            "action": "archive_lifecycle_snapshot_root_check_as_planning_layout_evidence",
            "next_blocker": "approved_runtime_evidence_missing",
            "candidate_root_requirements": candidate_root_requirements,
            "runtime_or_public_sdk_readiness_claim": False,
        }
    return {
        "status": "offline_requirement_blocked",
        "action": "create_or_recover_distinct_sanitized_lifecycle_ufunction_snapshot_root",
        "required_targets": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS),
        "candidate_root_requirements": candidate_root_requirements,
        "runtime_or_public_sdk_readiness_claim": False,
    }


def lifecycle_snapshot_root_requirement_report(
    base: dict[str, dict[str, Any]],
    candidate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    target_filters = set(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS)
    comparison = compare_sets(
        base,
        candidate,
        strict_identity_indices=False,
        allow_ark_sha_mismatch=False,
        target_filters=target_filters,
    )
    results_by_target = {result["target"]: result for result in comparison["results"]}
    target_details: list[dict[str, Any]] = []
    offline_blockers: list[dict[str, Any]] = []
    base_identities: list[dict[str, str]] = []
    candidate_identities: list[dict[str, str]] = []
    for key in LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS:
        result = results_by_target.get(
            key,
            {"target": key, "status": "inconclusive", "reasons": ["missing_comparison_result"]},
        )
        base_identity, base_identity_reasons = lifecycle_snapshot_identity_record(base, key, label="base")
        candidate_identity, candidate_identity_reasons = lifecycle_snapshot_identity_record(
            candidate,
            key,
            label="candidate",
        )
        if base_identity is not None:
            base_identities.append(base_identity)
        if candidate_identity is not None:
            candidate_identities.append(candidate_identity)
        detail: dict[str, Any] = {
            "target": key,
            "status": result["status"],
            "base_path": base.get(key, {}).get("path"),
            "candidate_path": candidate.get(key, {}).get("path"),
            "base_identity": base_identity,
            "candidate_identity": candidate_identity,
            "identity_reasons": base_identity_reasons + candidate_identity_reasons,
        }
        if result["status"] == "inconclusive":
            detail["reasons"] = result.get("reasons", [])
        elif result["status"] == "rejected":
            diffs = result.get("diffs", [])
            detail["diff_count"] = len(diffs)
            detail["first_diff"] = diffs[0].get("path") if diffs else None

        for reason in detail.get("identity_reasons", []):
            offline_blockers.append({"target": key, "reason": reason})
        if result["status"] == "inconclusive":
            for reason in result.get("reasons", []):
                offline_blockers.append({"target": key, "reason": reason})
        elif result["status"] == "rejected":
            offline_blockers.append({"target": key, "reason": "lifecycle_layout_mismatch"})
        target_details.append(detail)

    base_unique_identities = lifecycle_unique_artifact_identities(base_identities)
    candidate_unique_identities = lifecycle_unique_artifact_identities(candidate_identities)
    if len(base_unique_identities) > 1:
        offline_blockers.append(
            {
                "reason": "base_lifecycle_root_artifact_identity_inconsistent",
                "count": len(base_unique_identities),
            }
        )
    if len(candidate_unique_identities) > 1:
        offline_blockers.append(
            {
                "reason": "candidate_lifecycle_root_artifact_identity_inconsistent",
                "count": len(candidate_unique_identities),
            }
        )

    counts = comparison["counts"]
    if counts["accepted"] != len(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS):
        offline_blockers.append(
            {
                "reason": "required_lifecycle_targets_not_all_accepted",
                "count": len(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS) - counts["accepted"],
            }
        )

    candidate_targets = set(candidate)
    candidate_extra_targets = sorted(candidate_targets - target_filters)
    candidate_missing_targets = sorted(target_filters - candidate_targets)
    if candidate_extra_targets:
        for target in candidate_extra_targets:
            offline_blockers.append({"target": target, "reason": "candidate_extra_snapshot_target_not_allowed"})
    if candidate_extra_targets or candidate_missing_targets:
        offline_blockers.append(
            {
                "reason": "candidate_snapshot_root_not_exact_two_target_scope",
                "count": len(candidate_extra_targets) + len(candidate_missing_targets),
            }
        )

    offline_satisfied = not offline_blockers
    blocker_reason_counts = offline_blocker_reason_counts(offline_blockers)
    return {
        "schema": LIFECYCLE_SNAPSHOT_ROOT_CHECK_SCHEMA,
        "guidance_scope": "offline_lifecycle_snapshot_requirement",
        "source_scope": "sanitized_ufunction_snapshot_roots_only",
        "artifact": "distinct_sanitized_lifecycle_ufunction_snapshot_root",
        "required_targets": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS),
        "required_identity_fields": list(LIFECYCLE_SNAPSHOT_ROOT_REQUIRED_IDENTITY_FIELDS),
        "required_shape_fields": list(
            LIFECYCLE_FNAME_DRIFT_NEXT_OFFLINE_ARTIFACT_REQUIREMENT["required_shape_fields"]
        ),
        "comparison_mode": "semantic_layout_without_strict_identity_indices",
        "strict_identity_indices": False,
        "allow_ark_sha_mismatch": False,
        "evidence_scope": LIFECYCLE_SNAPSHOT_ROOT_CHECK_EVIDENCE_SCOPE,
        "offline_requirement": {
            "satisfied": offline_satisfied,
            "status": "accepted" if offline_satisfied else "blocked",
            "blocker_count": len(offline_blockers),
            "blocker_reason_counts": blocker_reason_counts,
            "blockers": offline_blockers,
        },
        "comparison_counts": dict(counts),
        "target_details": target_details,
        "base_root_artifact_identity_consistent": len(base_unique_identities) <= 1,
        "candidate_root_artifact_identity_consistent": len(candidate_unique_identities) <= 1,
        "candidate_snapshot_scope": {
            "exact_required_targets": not candidate_extra_targets and not candidate_missing_targets,
            "required_targets": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_TARGETS),
            "candidate_targets": sorted(candidate_targets),
            "extra_targets": candidate_extra_targets,
            "missing_targets": candidate_missing_targets,
            "required_snapshot_filenames": list(LIFECYCLE_FNAME_DRIFT_REQUIRED_SNAPSHOT_FILENAMES),
            "focused_candidate_root_required": bool(candidate_extra_targets or candidate_missing_targets),
        },
        "prohibited_inputs": list(LIFECYCLE_SNAPSHOT_ROOT_PROHIBITED_INPUTS),
        "next_offline_artifact_requirement": dict(LIFECYCLE_FNAME_DRIFT_NEXT_OFFLINE_ARTIFACT_REQUIREMENT),
        "next_offline_action": lifecycle_snapshot_next_offline_action(
            offline_satisfied,
            candidate_extra_targets=candidate_extra_targets,
            candidate_missing_targets=candidate_missing_targets,
        ),
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_blocker": "approved_runtime_evidence_missing",
        "layout_only_evidence_satisfies_approved_runtime_evidence": False,
        "layout_only_evidence_rejected_for_runtime_readiness": True,
        "does_not_satisfy_readiness": list(LIFECYCLE_SNAPSHOT_ROOT_DOES_NOT_SATISFY),
        "readiness_effect": "none",
        "runtime_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "v1_complete": False,
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only" if offline_satisfied else "not_ready",
            "layout_ready": offline_satisfied,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": (
                [
                    {"reason": "approved_runtime_evidence_missing", "count": 1},
                    {"reason": "lifecycle_snapshot_root_check_not_runtime_evidence", "count": 1},
                ]
                if offline_satisfied
                else [
                    {"reason": "lifecycle_snapshot_root_requirement_blocked", "count": len(offline_blockers)},
                    {"reason": "approved_runtime_evidence_missing", "count": 1},
                ]
            ),
        },
        "non_claims": list(LIFECYCLE_SNAPSHOT_ROOT_NON_CLAIMS),
    }


def parse_observed_fname_chain(value: str) -> list[int]:
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(not part for part in parts):
        raise SystemExit("--observed-fname-chain must be a comma-separated list of decimal indices")
    observed = []
    for part in parts:
        if not part.isdecimal():
            raise SystemExit("--observed-fname-chain accepts decimal FName indices only")
        observed.append(int(part))
    return observed


def validate_observed_fname_target_sets(observed_target: str, target_sets: list[str]) -> None:
    if not target_sets:
        return
    validate_target_filters({observed_target})
    non_planning = sorted(set(target_sets) - PLANNING_ONLY_TARGET_SETS)
    if non_planning:
        raise SystemExit(
            "--observed-fname-chain only accepts planning-only target sets: "
            + ", ".join(non_planning)
        )
    mismatched = [
        target_set
        for target_set in sorted(set(target_sets))
        if not any(matches_target_filter(target, {observed_target}) for target in TARGET_SETS[target_set])
    ]
    if mismatched:
        raise SystemExit(
            "--observed-fname-chain target set(s) do not contain --observed-fname-target: "
            + ", ".join(mismatched)
        )


def observed_index_occurrences(
    snapshots: dict[str, dict[str, Any]],
    observed_name_indices: list[int],
) -> list[dict[str, Any]]:
    wanted = set(observed_name_indices)
    occurrences: list[dict[str, Any]] = []
    for key, entry in sorted(snapshots.items()):
        target = entry["payload"]["targets"][0]
        chain = target.get("property_chain")
        if not isinstance(chain, dict):
            continue
        properties = chain.get("properties")
        if not isinstance(properties, list):
            continue
        for index, prop in enumerate(properties):
            if not isinstance(prop, dict):
                continue
            name_index = prop.get("name_index")
            if name_index not in wanted:
                continue
            occurrences.append(
                {
                    "target": key,
                    "path": entry["path"],
                    "property_index": index,
                    "property_name": prop.get("name"),
                    "class_name": prop.get("class_name"),
                    "offset_internal": prop.get("offset_internal"),
                    "name_index": name_index,
                }
            )
    return occurrences


def assert_observed_fname_chain_report_contract(report: dict[str, Any]) -> None:
    expected_values = {
        "guidance_scope": "offline_planning_only",
        "evidence_scope": OBSERVED_FNAME_CHAIN_EVIDENCE_SCOPE,
        "artifact_role": OBSERVED_FNAME_CHAIN_ARTIFACT_ROLE,
        "layout_evidence_status": OBSERVED_FNAME_CHAIN_LAYOUT_EVIDENCE_STATUS,
        "second_source_layout_evidence": False,
        "can_be_used_as_second_source_layout_evidence": False,
        "can_be_used_as_candidate_snapshot_root": False,
        "second_source_status": "not_applicable",
        "not_second_source": True,
        "readiness_effect": "none",
        "readiness_classification": "planning_only",
        "planning_only": True,
        "runtime_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
    }
    violations = [
        f"{field}={report.get(field)!r}"
        for field, expected in expected_values.items()
        if report.get(field) != expected
    ]
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        violations.append("promotion_gate missing")
    else:
        for field in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
            if promotion_gate.get(field) is not False:
                violations.append(f"promotion_gate.{field}={promotion_gate.get(field)!r}")
    prohibited_uses = set(report.get("prohibited_evidence_uses", []))
    required_prohibited_uses = set(OBSERVED_FNAME_CHAIN_PROHIBITED_EVIDENCE_USES)
    if not required_prohibited_uses.issubset(prohibited_uses):
        missing = sorted(required_prohibited_uses - prohibited_uses)
        violations.append("missing_prohibited_evidence_uses=" + ",".join(missing))
    if violations:
        raise AssertionError("observed FName-chain diagnostic contract violated: " + "; ".join(violations))


def observed_fname_chain_report(
    snapshots: dict[str, dict[str, Any]],
    *,
    observed_target: str,
    observed_name_indices: list[int],
    observed_chain_occurrences: int,
    target_sets: list[str],
) -> dict[str, Any]:
    validate_target_filters({observed_target})
    keys = [
        key
        for key in filtered_keys(snapshots, {}, target_filters={observed_target})
        if key in snapshots and matches_target_filter(key, {observed_target})
    ]
    if len(keys) != 1:
        raise SystemExit(
            "--observed-fname-target must match exactly one snapshot target; matched "
            + str(len(keys))
        )

    key = keys[0]
    entry = snapshots[key]
    layout, reasons = comparable_layout(entry["payload"], strict_identity_indices=True)
    if layout is None or reasons:
        raise SystemExit(
            "--observed-fname-target snapshot is not comparable: " + ", ".join(reasons)
        )

    properties = layout["property_chain"]["properties"]
    expected_name_indices = [prop.get("name_index") for prop in properties]
    property_comparison = []
    for index, prop in enumerate(properties):
        expected = prop.get("name_index")
        observed = observed_name_indices[index] if index < len(observed_name_indices) else None
        delta = observed - expected if isinstance(observed, int) and isinstance(expected, int) else None
        property_comparison.append(
            {
                "position": index,
                "property_name": prop.get("name"),
                "class_name": prop.get("class_name"),
                "offset_internal": prop.get("offset_internal"),
                "element_size": prop.get("element_size"),
                "array_dim": prop.get("array_dim"),
                "expected_name_index": expected,
                "observed_name_index": observed,
                "delta": delta,
                "exact_name_index_match": observed == expected,
            }
        )

    exact_chain_match = expected_name_indices == observed_name_indices
    occurrences = observed_index_occurrences(snapshots, observed_name_indices)
    matched_observed_indices = sorted(
        {
            occurrence["name_index"]
            for occurrence in occurrences
            if isinstance(occurrence.get("name_index"), int)
        }
    )
    unmatched_observed_indices = [
        index for index in observed_name_indices if index not in matched_observed_indices
    ]
    target_set_context = [
        {
            "target_set": target_set,
            "contains_target": key in TARGET_SETS[target_set],
            "readiness_classification": target_set_readiness_classification(target_set),
        }
        for target_set in sorted(target_sets)
    ]

    report = {
        "schema": "obelisk.reflection-observed-fname-chain-check.v1",
        "guidance_scope": "offline_planning_only",
        "evidence_scope": OBSERVED_FNAME_CHAIN_EVIDENCE_SCOPE,
        "artifact_role": OBSERVED_FNAME_CHAIN_ARTIFACT_ROLE,
        "layout_evidence_status": OBSERVED_FNAME_CHAIN_LAYOUT_EVIDENCE_STATUS,
        "second_source_layout_evidence": False,
        "can_be_used_as_second_source_layout_evidence": False,
        "can_be_used_as_candidate_snapshot_root": False,
        "target": key,
        "target_sets": sorted(target_sets),
        "target_set_context": target_set_context,
        "target_set_guidance": target_set_guidance_report(target_sets),
        "source_scope": "sanitized_snapshot_root_only",
        "observed_chain_source": "copied_runtime_diagnostic_line",
        "diagnostic_observation_count": observed_chain_occurrences,
        "diagnostic_observation_count_scope": "repeated_runtime_mismatch_count_diagnostic_only",
        "diagnostic_observation_repeated": observed_chain_occurrences > 1,
        "second_source_status": "not_applicable",
        "second_source_blockers": list(OBSERVED_FNAME_CHAIN_SECOND_SOURCE_BLOCKERS),
        "not_second_source": True,
        "status": "matched_planning_only" if exact_chain_match else "unresolved_mismatch",
        "readiness_effect": "none",
        "readiness_classification": "planning_only",
        "planning_only": True,
        "runtime_ready": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "does_not_satisfy_readiness": [
            "second_source_layout_evidence",
            "runtime_readiness",
            "public_sdk_readiness",
            "release_readiness",
            "v1_completion",
        ],
        "prohibited_evidence_uses": list(OBSERVED_FNAME_CHAIN_PROHIBITED_EVIDENCE_USES),
        "exact_property_chain_match": exact_chain_match,
        "expected_name_indices": expected_name_indices,
        "observed_name_indices": observed_name_indices,
        "deltas": [item["delta"] for item in property_comparison],
        "observed_count": len(observed_name_indices),
        "expected_count": len(expected_name_indices),
        "extra_observed_name_indices": observed_name_indices[len(expected_name_indices) :],
        "property_comparison": property_comparison,
        "observed_indices_found_in_snapshot_root": occurrences,
        "observed_indices_found_count": len(occurrences),
        "unmatched_observed_name_indices": unmatched_observed_indices,
        "interpretation": (
            "observed chain does not resolve to the committed sanitized snapshot indices"
            if not exact_chain_match
            else "observed chain matches the sanitized snapshot indices, but this remains planning-only"
        ),
        "blockers": [
            "approved_runtime_evidence_missing",
            "observed_fname_chain_check_not_promotion_gate",
            "observed_fname_chain_unresolved",
            "runtime_observation_requires_separate_approval",
        ]
        if not exact_chain_match
        else [
            "approved_runtime_evidence_missing",
            "observed_fname_chain_check_not_promotion_gate",
            "runtime_observation_requires_separate_approval",
        ],
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                {"reason": "approved_runtime_evidence_missing", "count": 1},
                {"reason": "observed_fname_chain_check_not_promotion_gate", "count": 1},
                {"reason": "observed_fname_chain_unresolved", "count": 1},
            ]
            if not exact_chain_match
            else [{"reason": "observed_fname_chain_check_not_promotion_gate", "count": 1}],
        },
        "next_offline_artifact_requirement": dict(
            LIFECYCLE_FNAME_DRIFT_NEXT_OFFLINE_ARTIFACT_REQUIREMENT
        ),
        "non_claims": list(OBSERVED_FNAME_CHAIN_NON_CLAIMS),
    }
    assert_observed_fname_chain_report_contract(report)
    return report


def readiness_report(
    snapshots: dict[str, dict[str, Any]],
    *,
    strict_identity_indices: bool,
    allow_ark_sha_mismatch: bool,
    target_filters: set[str],
    candidate: dict[str, dict[str, Any]] | None,
) -> dict[str, Any]:
    if candidate is None:
        keys = filtered_keys(snapshots, {}, target_filters=target_filters)
        if target_filters and not keys:
            raise SystemExit(f"target filter did not match snapshots: {', '.join(sorted(target_filters))}")
        comparison_by_target: dict[str, dict[str, Any]] = {}
    else:
        keys = filtered_keys(snapshots, candidate, target_filters=target_filters)
        comparison = compare_sets(
            snapshots,
            candidate,
            strict_identity_indices=strict_identity_indices,
            allow_ark_sha_mismatch=allow_ark_sha_mismatch,
            target_filters=target_filters,
        )
        comparison_by_target = {result["target"]: result for result in comparison["results"]}

    modules: dict[str, dict[str, Any]] = {}
    totals = {
        "targets": 0,
        "comparable": 0,
        "blocked": 0,
        "second_source_accepted": 0,
        "second_source_rejected": 0,
        "second_source_inconclusive": 0,
        "second_source_missing": 0,
    }

    def promotion_gate_summary() -> dict[str, Any]:
        blockers = []
        if totals["targets"] == 0:
            blockers.append({"reason": "no_targets", "count": 1})
        if totals["blocked"]:
            blockers.append({"reason": "blocked_base_targets", "count": totals["blocked"]})
        if totals["second_source_rejected"]:
            blockers.append({"reason": "rejected_second_source", "count": totals["second_source_rejected"]})
        if totals["second_source_inconclusive"]:
            blockers.append({"reason": "inconclusive_second_source", "count": totals["second_source_inconclusive"]})
        if totals["second_source_missing"]:
            blockers.append({"reason": "missing_second_source", "count": totals["second_source_missing"]})
        return {
            "ready": not blockers,
            "ready_scope": "layout_only" if not blockers else "not_ready",
            "layout_ready": not blockers,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": blockers,
        }

    def module_bucket(module_key: str, *, schema: str, module: str) -> dict[str, Any]:
        return modules.setdefault(
            module_key,
            {
                "schema": schema,
                "module": module,
                "targets": 0,
                "comparable": 0,
                "blocked": 0,
                "block_reasons": {},
                "second_source": {"accepted": 0, "rejected": 0, "inconclusive": 0, "missing": 0},
                "target_details": [],
            },
        )

    for key in keys:
        entry = snapshots.get(key)
        if entry is None:
            schema_name, _, _ = key.partition(":")
            schema = schema_label(schema_name)
            bucket = module_bucket(f"{schema}:<missing>", schema=schema, module="<missing>")
            target_detail = {
                "target": key,
                "path": None,
                "comparable": False,
                "block_reasons": ["missing_base_snapshot"],
                "second_source_status": "not_applicable",
            }
            guidance = target_blocker_guidance(key)
            if guidance is not None:
                target_detail["guidance"] = guidance
            bucket["targets"] += 1
            bucket["blocked"] += 1
            bucket["block_reasons"]["missing_base_snapshot"] = (
                bucket["block_reasons"].get("missing_base_snapshot", 0) + 1
            )
            bucket["second_source"]["missing"] += 1
            bucket["target_details"].append(target_detail)
            totals["targets"] += 1
            totals["blocked"] += 1
            continue
        payload = entry["payload"]
        schema = schema_label(payload.get("schema", ""))
        module = module_from_path(entry["path"])
        module_key = f"{schema}:{module}"
        bucket = module_bucket(module_key, schema=schema, module=module)

        bucket["targets"] += 1
        totals["targets"] += 1
        _, reasons = comparable_layout(payload, strict_identity_indices=strict_identity_indices)
        target_detail = {
            "target": key,
            "path": entry["path"],
            "comparable": not bool(reasons),
            "block_reasons": reasons,
            "second_source_status": "missing",
        }
        guidance = target_blocker_guidance(key)
        if guidance is not None:
            target_detail["guidance"] = guidance
        if reasons:
            bucket["blocked"] += 1
            totals["blocked"] += 1
            for reason in reasons:
                bucket["block_reasons"][reason] = bucket["block_reasons"].get(reason, 0) + 1
        else:
            bucket["comparable"] += 1
            totals["comparable"] += 1

        comparison_result = comparison_by_target.get(key)
        if comparison_result is None:
            bucket["second_source"]["missing"] += 1
            totals["second_source_missing"] += 1
            bucket["target_details"].append(target_detail)
            continue
        status = comparison_result["status"]
        target_detail["second_source_status"] = status
        if status == "inconclusive":
            target_detail["second_source_reasons"] = comparison_result.get("reasons", [])
        elif status == "rejected":
            target_detail["diff_count"] = len(comparison_result.get("diffs", []))
            first_diff = comparison_result.get("diffs", [{}])[0]
            target_detail["first_diff"] = first_diff.get("path")
        bucket["second_source"][status] += 1
        totals[f"second_source_{status}"] += 1
        bucket["target_details"].append(target_detail)

    return {
        "schema": "obelisk.reflection-snapshot-readiness.v1",
        "strict_identity_indices": strict_identity_indices,
        "target_filters": sorted(target_filters),
        "second_source_status": "compared" if candidate is not None else "missing_candidate_root",
        "evidence_scope": READINESS_EVIDENCE_SCOPE,
        "does_not_satisfy_readiness": list(READINESS_DOES_NOT_SATISFY),
        "not_promoted_surfaces": sorted(READINESS_NOT_PROMOTED_SURFACES),
        "non_claims": list(READINESS_NON_CLAIMS),
        **READINESS_FALSE_FLAGS,
        **READINESS_ZERO_FIELDS,
        "totals": totals,
        "promotion_gate": promotion_gate_summary(),
        "modules": [modules[key] for key in sorted(modules)],
    }


def print_text(report: dict[str, Any]) -> None:
    if report["schema"] == "obelisk.reflection-snapshot-target-sets.v1":
        print(
            "target_set_catalog scope={scope} evidence_scope={evidence_scope} "
            "not_second_source={not_second_source} second_source_layout_evidence={second_source} "
            "target_set_revision_source_sha256={source_sha256}".format(
                scope=report.get("catalog_scope", "unknown"),
                evidence_scope=report.get("evidence_scope", "unknown"),
                not_second_source=str(report.get("not_second_source", False)).lower(),
                second_source=str(report.get("second_source_layout_evidence", False)).lower(),
                source_sha256=report.get("target_set_revision_source_sha256", "unknown"),
            )
        )
        for item in report["target_sets"]:
            print(
                "{name}: readiness_classification={classification} "
                "release_readiness={release_readiness} readiness_scope={readiness_scope} "
                "promotion_ready={promotion_ready} public_sdk_ready={public_sdk_ready} "
                "runtime_ready={runtime_ready} second_source_layout_evidence={second_source}".format(
                    name=item["name"],
                    classification=item["readiness_classification"],
                    release_readiness=str(item["release_readiness"]).lower(),
                    readiness_scope=item["readiness_scope"],
                    promotion_ready=str(item["promotion_ready"]).lower(),
                    public_sdk_ready=str(item["public_sdk_ready"]).lower(),
                    runtime_ready=str(item.get("runtime_ready", False)).lower(),
                    second_source=str(item.get("second_source_layout_evidence", False)).lower(),
                )
            )
            lifecycle_source_policy = item.get("lifecycle_source_policy")
            if isinstance(lifecycle_source_policy, dict):
                approved_names = lifecycle_source_policy.get("approved_runtime_triplet_source_names", [])
                guidance_names = lifecycle_source_policy.get("guidance_only_non_triplet_source_names", [])
                print(
                    "  lifecycle_source_policy scope={scope} "
                    "approved_runtime_triplet_source_names={approved} "
                    "guidance_only_non_triplet_source_names={guidance} "
                    "runtime_triplet_evidence_status={status} "
                    "approved_runtime_evidence_present={runtime_evidence} "
                    "runtime_ready={runtime_ready} public_sdk_ready={public_sdk_ready} "
                    "promotion_ready={promotion_ready}".format(
                        scope=lifecycle_source_policy.get("policy_scope", "unknown"),
                        approved=",".join(str(target) for target in approved_names)
                        if isinstance(approved_names, list)
                        else "",
                        guidance=",".join(str(target) for target in guidance_names)
                        if isinstance(guidance_names, list)
                        else "",
                        status=lifecycle_source_policy.get("runtime_triplet_evidence_status", "unknown"),
                        runtime_evidence=str(
                            lifecycle_source_policy.get("approved_runtime_evidence_present", False)
                        ).lower(),
                        runtime_ready=str(lifecycle_source_policy.get("runtime_ready", False)).lower(),
                        public_sdk_ready=str(lifecycle_source_policy.get("public_sdk_ready", False)).lower(),
                        promotion_ready=str(lifecycle_source_policy.get("promotion_ready", False)).lower(),
                    )
                )
            for target in item["targets"]:
                print(f"  {target}")
        return

    if report["schema"] == "obelisk.reflection-target-guidance.v1":
        print(
            "target_guidance count={count} scope={scope} target_set_guidance={set_count} "
            "evidence_scope={evidence_scope} not_second_source={not_second_source}".format(
                count=len(report["targets"]),
                scope=report["guidance_scope"],
                set_count=len(report.get("target_set_guidance", [])),
                evidence_scope=report.get("evidence_scope", "unknown"),
                not_second_source=str(report.get("not_second_source", False)).lower(),
            )
        )
        for item in report.get("target_set_guidance", []):
            parts = [
                f"target_set={item['target_set']}",
                f"classification={item.get('classification')}",
            ]
            why_blocked = item.get("why_blocked")
            if isinstance(why_blocked, list) and why_blocked:
                parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
            approved_triplet_sources = item.get("approved_triplet_sources")
            if isinstance(approved_triplet_sources, list) and approved_triplet_sources:
                parts.append(
                    "approved_triplet_sources="
                    + ",".join(str(target) for target in approved_triplet_sources)
                )
            approved_runtime_triplet_source_names = item.get("approved_runtime_triplet_source_names")
            if (
                isinstance(approved_runtime_triplet_source_names, list)
                and approved_runtime_triplet_source_names
            ):
                parts.append(
                    "approved_runtime_triplet_source_names="
                    + ",".join(str(target) for target in approved_runtime_triplet_source_names)
                )
            guidance_only_source_names = item.get("guidance_only_non_triplet_source_names")
            if isinstance(guidance_only_source_names, list) and guidance_only_source_names:
                parts.append(
                    "guidance_only_non_triplet_source_names="
                    + ",".join(str(target) for target in guidance_only_source_names)
                )
            runtime_triplet_status = item.get("runtime_triplet_evidence_status")
            if isinstance(runtime_triplet_status, str) and runtime_triplet_status:
                parts.append(f"runtime_triplet_evidence_status={runtime_triplet_status}")
            if "approved_runtime_evidence_present" in item:
                parts.append(
                    "approved_runtime_evidence_present="
                    + str(item.get("approved_runtime_evidence_present", False)).lower()
                )
            all_six_status = item.get("all_six_planning_gap_evidence_status")
            if isinstance(all_six_status, str) and all_six_status:
                parts.append(f"all_six_planning_gap_evidence_status={all_six_status}")
            next_offline_input = item.get("next_offline_input")
            if isinstance(next_offline_input, str) and next_offline_input:
                parts.append(f"next_offline_input={next_offline_input}")
            snapshot_prep_checks = item.get("snapshot_prep_checks")
            if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
            non_claim = item.get("non_claim")
            if isinstance(non_claim, str) and non_claim:
                parts.append(f"non_claim={non_claim}")
            print("  " + " ".join(parts))
        for item in report["targets"]:
            parts = [
                f"target={item['target']}",
                f"classification={item.get('classification')}",
            ]
            why_blocked = item.get("why_blocked")
            if isinstance(why_blocked, list) and why_blocked:
                parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
            next_offline_input = item.get("next_offline_input")
            if isinstance(next_offline_input, str) and next_offline_input:
                parts.append(f"next_offline_input={next_offline_input}")
            snapshot_prep_checks = item.get("snapshot_prep_checks")
            if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
            non_claim = item.get("non_claim")
            if isinstance(non_claim, str) and non_claim:
                parts.append(f"non_claim={non_claim}")
            print("  " + " ".join(parts))
        return

    if report["schema"] == LIFECYCLE_SNAPSHOT_ROOT_CHECK_SCHEMA:
        offline = report["offline_requirement"]
        counts = report["comparison_counts"]
        print(
            "lifecycle_snapshot_root_requirement status={status} satisfied={satisfied} "
            "accepted={accepted} rejected={rejected} inconclusive={inconclusive} "
            "approved_runtime_evidence={runtime_evidence} runtime_ready={runtime_ready} "
            "public_sdk_ready={public_sdk_ready} blocker={blocker}".format(
                status=offline["status"],
                satisfied=str(offline["satisfied"]).lower(),
                accepted=counts["accepted"],
                rejected=counts["rejected"],
                inconclusive=counts["inconclusive"],
                runtime_evidence=str(report["approved_runtime_evidence"]).lower(),
                runtime_ready=str(report["runtime_ready"]).lower(),
                public_sdk_ready=str(report["public_sdk_ready"]).lower(),
                blocker=report["approved_runtime_evidence_blocker"],
            )
        )
        print(
            "  evidence_scope={scope} comparison_mode={mode} readiness_effect={effect}".format(
                scope=report["evidence_scope"],
                mode=report["comparison_mode"],
                effect=report["readiness_effect"],
            )
        )
        for blocker in offline.get("blockers", []):
            if not isinstance(blocker, dict):
                continue
            target = blocker.get("target")
            prefix = f" target={target}" if target else ""
            print(f"  blocker{prefix} reason={blocker.get('reason')} count={blocker.get('count', 1)}")
        for detail in report.get("target_details", []):
            print(
                "  target={target} status={status} base_identity={base_identity} "
                "candidate_identity={candidate_identity}".format(
                    target=detail.get("target"),
                    status=detail.get("status"),
                    base_identity=str(detail.get("base_identity") is not None).lower(),
                    candidate_identity=str(detail.get("candidate_identity") is not None).lower(),
                )
            )
        next_action = report.get("next_offline_action")
        if isinstance(next_action, dict):
            print(
                "  next_offline_action={action} status={status} runtime_or_public_sdk_readiness_claim={claim}".format(
                    action=next_action.get("action"),
                    status=next_action.get("status"),
                    claim=str(next_action.get("runtime_or_public_sdk_readiness_claim")).lower(),
                )
            )
        return

    if report["schema"] == "obelisk.reflection-observed-fname-chain-check.v1":
        print(
            "observed_fname_chain target={target} status={status} exact_match={exact} "
            "expected={expected} observed={observed} deltas={deltas} readiness_effect={effect} "
            "layout_evidence_status={layout_status} not_second_source={not_second_source} "
            "can_be_second_source={can_be_second_source} promotion_ready={promotion_ready} "
            "runtime_ready={runtime_ready}".format(
                target=report["target"],
                status=report["status"],
                exact=str(report["exact_property_chain_match"]).lower(),
                expected=",".join(str(index) for index in report["expected_name_indices"]),
                observed=",".join(str(index) for index in report["observed_name_indices"]),
                deltas=",".join(str(delta) for delta in report["deltas"]),
                effect=report["readiness_effect"],
                layout_status=report["layout_evidence_status"],
                not_second_source=str(report["not_second_source"]).lower(),
                can_be_second_source=str(report["can_be_used_as_second_source_layout_evidence"]).lower(),
                promotion_ready=str(report["promotion_ready"]).lower(),
                runtime_ready=str(report["runtime_ready"]).lower(),
            )
        )
        unmatched = report.get("unmatched_observed_name_indices", [])
        if isinstance(unmatched, list) and unmatched:
            print("  unmatched_observed_name_indices=" + ",".join(str(index) for index in unmatched))
        observation_count = report.get("diagnostic_observation_count")
        if isinstance(observation_count, int) and observation_count > 1:
            print(f"  diagnostic_observation_count={observation_count} scope=diagnostic_only")
        blockers = report.get("blockers", [])
        if isinstance(blockers, list) and blockers:
            print("  blockers=" + ",".join(str(blocker) for blocker in blockers))
        next_requirement = report.get("next_offline_artifact_requirement")
        if isinstance(next_requirement, dict):
            required_targets = next_requirement.get("required_targets", [])
            if isinstance(required_targets, list):
                print(
                    "  next_offline_artifact={artifact} targets={targets} comparison_mode={mode}".format(
                        artifact=next_requirement.get("artifact"),
                        targets=",".join(str(target) for target in required_targets),
                        mode=next_requirement.get("comparison_mode"),
                    )
                )
        for item in report.get("property_comparison", []):
            print(
                "  property position={position} name={name} class={class_name} offset={offset} "
                "expected={expected} observed={observed} delta={delta} exact={exact}".format(
                    position=item.get("position"),
                    name=item.get("property_name"),
                    class_name=item.get("class_name"),
                    offset=item.get("offset_internal"),
                    expected=item.get("expected_name_index"),
                    observed=item.get("observed_name_index"),
                    delta=item.get("delta"),
                    exact=str(item.get("exact_name_index_match")).lower(),
                )
            )
        return

    if report["schema"] == "obelisk.reflection-snapshot-readiness.v1":
        totals = report["totals"]
        print(
            "readiness targets={targets} comparable={comparable} blocked={blocked} "
            "second_source_status={second_source_status} gate_mode={gate_mode}".format(
                second_source_status=report["second_source_status"],
                gate_mode=report.get("gate_mode", "unknown"),
                **totals,
            )
        )
        promotion_gate = report["promotion_gate"]
        blocker_reasons = [
            f"{blocker.get('reason')}:{blocker.get('count')}"
            for blocker in promotion_gate.get("blockers", [])
            if isinstance(blocker, dict)
        ]
        blockers = ",".join(blocker_reasons) if blocker_reasons else "none"
        print(
            "promotion_gate ready={ready} blockers={blockers} scope={scope} "
            "layout_ready={layout_ready} promotion_ready={promotion_ready} "
            "public_sdk_ready={public_sdk_ready} runtime_ready={runtime_ready}".format(
                ready=str(promotion_gate["ready"]).lower(),
                blockers=blockers,
                scope=promotion_gate.get("ready_scope", "unknown"),
                layout_ready=str(promotion_gate.get("layout_ready", False)).lower(),
                promotion_ready=str(promotion_gate.get("promotion_ready", False)).lower(),
                public_sdk_ready=str(promotion_gate.get("public_sdk_ready", False)).lower(),
                runtime_ready=str(promotion_gate.get("runtime_ready", False)).lower(),
            )
        )
        for module in report["modules"]:
            second_source = module["second_source"]
            planning_layout_comparison = module.get("planning_layout_comparison")
            if isinstance(planning_layout_comparison, dict):
                print(
                    "{schema}:{module_name} targets={targets} comparable={comparable} "
                    "blocked={blocked} second_source_status={status} "
                    "planning_layout=accepted:{accepted},rejected:{rejected},"
                    "inconclusive:{inconclusive},missing:{missing}".format(
                        schema=module["schema"],
                        module_name=module["module"],
                        targets=module["targets"],
                        comparable=module["comparable"],
                        blocked=module["blocked"],
                        status=module.get("second_source_status", PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS),
                        accepted=planning_layout_comparison["accepted"],
                        rejected=planning_layout_comparison["rejected"],
                        inconclusive=planning_layout_comparison["inconclusive"],
                        missing=planning_layout_comparison["missing"],
                    )
                )
            else:
                print(
                    "{schema}:{module_name} targets={targets} comparable={comparable} "
                    "blocked={blocked} second_source=accepted:{accepted},rejected:{rejected},"
                    "inconclusive:{inconclusive},missing:{missing}".format(
                        schema=module["schema"],
                        module_name=module["module"],
                        targets=module["targets"],
                        comparable=module["comparable"],
                        blocked=module["blocked"],
                        accepted=second_source["accepted"],
                        rejected=second_source["rejected"],
                        inconclusive=second_source["inconclusive"],
                        missing=second_source["missing"],
                    )
                )
            for detail in module["target_details"]:
                second_source_status = detail["second_source_status"]
                if detail["comparable"] and second_source_status == "accepted":
                    continue
                if (
                    detail["comparable"]
                    and second_source_status == PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS
                    and detail.get("planning_layout_comparison_status") == "accepted"
                ):
                    continue

                parts = [
                    f"target={detail['target']}",
                    f"comparable={str(detail['comparable']).lower()}",
                    f"second_source={second_source_status}",
                ]
                block_reasons = detail.get("block_reasons", [])
                if block_reasons:
                    parts.append(f"block_reasons={','.join(block_reasons)}")
                second_source_reasons = detail.get("second_source_reasons", [])
                if second_source_reasons:
                    parts.append(f"second_source_reasons={','.join(second_source_reasons)}")
                guidance = detail.get("guidance")
                if isinstance(guidance, dict):
                    classification = guidance.get("classification")
                    why_blocked = guidance.get("why_blocked")
                    if isinstance(classification, str) and classification:
                        parts.append(f"guidance={classification}")
                    if isinstance(why_blocked, list) and why_blocked:
                        parts.append(f"why_blocked={','.join(str(reason) for reason in why_blocked)}")
                    next_offline_input = guidance.get("next_offline_input")
                    if isinstance(next_offline_input, str) and next_offline_input:
                        parts.append(f"next_offline_input={next_offline_input}")
                    snapshot_prep_checks = guidance.get("snapshot_prep_checks")
                    if isinstance(snapshot_prep_checks, list) and snapshot_prep_checks:
                        parts.append(f"snapshot_prep_checks={len(snapshot_prep_checks)}")
                    non_claim = guidance.get("non_claim")
                    if isinstance(non_claim, str) and non_claim:
                        parts.append(f"non_claim={non_claim}")
                if "first_diff" in detail:
                    parts.append(f"first_diff={detail['first_diff']}")
                print(f"  {' '.join(parts)}")
        return

    counts = report["counts"]
    print(
        "summary accepted={accepted} rejected={rejected} inconclusive={inconclusive}".format(
            **counts,
        )
    )
    for result in report["results"]:
        line = f"{result['status']} {result['target']}"
        if result["status"] == "rejected":
            first = result.get("diffs", [{}])[0]
            line += f" first_diff={first.get('path')} base={first.get('base')!r} candidate={first.get('candidate')!r}"
        elif result["status"] == "inconclusive":
            line += " reasons=" + ",".join(result.get("reasons", []))
        print(line)


def apply_readiness_gate_mode(report: dict[str, Any]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") == "second_source_promotion":
        return
    if report.get("gate_mode") == "planning_layout_intake":
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict) or not promotion_gate.get("ready"):
        return
    promotion_gate.setdefault("public_sdk_ready", False)
    promotion_gate.setdefault("runtime_ready", False)
    promotion_gate["ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "not_second_source_promotion_gate", "count": 1})


def apply_planning_layout_intake_gate(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "planning_layout_intake":
        return

    original_second_source_status = report.get("second_source_status", "unknown")
    totals = report.get("totals", {})
    blockers: list[dict[str, Any]] = []
    if totals.get("targets") == 0:
        blockers.append({"reason": "no_targets", "count": 1})
    if totals.get("blocked"):
        blockers.append({"reason": "blocked_base_targets", "count": totals["blocked"]})
    if totals.get("second_source_rejected"):
        blockers.append({"reason": "rejected_second_source", "count": totals["second_source_rejected"]})
    if totals.get("second_source_inconclusive"):
        blockers.append({"reason": "inconclusive_second_source", "count": totals["second_source_inconclusive"]})
    if totals.get("second_source_missing"):
        blockers.append({"reason": "missing_second_source", "count": totals["second_source_missing"]})

    requested = set(target_sets)
    non_planning = sorted(requested - PLANNING_ONLY_TARGET_SETS)
    if non_planning:
        blockers.append({"reason": "target_set_not_planning_only", "count": len(non_planning)})

    report["planning_layout_gate"] = {
        "ready": not blockers,
        "ready_scope": "planning_only" if not blockers else "not_ready",
        "layout_ready": not blockers,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "blockers": blockers,
    }
    report["evidence_scope"] = PLANNING_LAYOUT_INTAKE_EVIDENCE_SCOPE
    report["readiness_effect"] = "none"
    report["second_source_readiness_satisfied"] = False
    report["second_source_status"] = PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS
    report["second_source_layout_evidence"] = False
    report["can_be_used_as_second_source_layout_evidence"] = False
    report["not_second_source"] = True
    report["planning_only"] = True
    report["readiness_classification"] = "planning_only"
    report["does_not_satisfy_readiness"] = list(PLANNING_LAYOUT_DOES_NOT_SATISFY)
    report["totals_scope"] = "planning_layout_comparison_counts_not_second_source_readiness"
    report["planning_layout_comparison_status"] = original_second_source_status
    report["planning_layout_comparison_totals"] = {
        "accepted": totals.get("second_source_accepted", 0),
        "rejected": totals.get("second_source_rejected", 0),
        "inconclusive": totals.get("second_source_inconclusive", 0),
        "missing": totals.get("second_source_missing", 0),
    }

    promotion_gate = report.get("promotion_gate")
    if isinstance(promotion_gate, dict):
        promotion_gate["ready"] = False
        promotion_gate["ready_scope"] = "planning_only"
        promotion_gate["promotion_ready"] = False
        promotion_gate["public_sdk_ready"] = False
        promotion_gate["runtime_ready"] = False
        promotion_blockers = promotion_gate.setdefault("blockers", [])
        if isinstance(promotion_blockers, list):
            promotion_blockers.append({"reason": "planning_layout_intake_not_promotion_gate", "count": 1})

    for module in report.get("modules", []):
        if not isinstance(module, dict):
            continue
        second_source = module.get("second_source")
        if isinstance(second_source, dict):
            module["planning_layout_comparison"] = dict(second_source)
        module["second_source_status"] = PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS
        module["second_source_readiness_satisfied"] = False
        for detail in module.get("target_details", []):
            if not isinstance(detail, dict):
                continue
            status = detail.get("second_source_status")
            if status in {"accepted", "rejected", "inconclusive", "missing"}:
                detail["planning_layout_comparison_status"] = status
                detail["second_source_status"] = PLANNING_LAYOUT_NOT_SECOND_SOURCE_STATUS


def require_target_set_for_promotion(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    if target_sets:
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    promotion_gate["public_sdk_ready"] = False
    promotion_gate["runtime_ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "promotion_requires_target_set", "count": 1})


def block_explicit_targets_outside_named_target_sets(
    report: dict[str, Any],
    targets: list[str],
    target_sets: list[str],
) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    if not targets or not target_sets:
        return

    allowed_schema_targets = expand_target_filters([], target_sets)
    allowed_short_targets = {target.partition(":")[2] for target in allowed_schema_targets}
    outside = [
        target
        for target in targets
        if target not in allowed_schema_targets and target not in allowed_short_targets
    ]
    if not outside:
        return

    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    promotion_gate["ready_scope"] = "not_ready"
    promotion_gate["public_sdk_ready"] = False
    promotion_gate["runtime_ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "explicit_target_not_in_named_target_set", "count": len(outside)})


def block_non_release_target_set_promotion(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    requested = set(target_sets)
    non_release = sorted(requested - RELEASE_READINESS_TARGET_SETS)
    if not non_release:
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    promotion_gate["public_sdk_ready"] = False
    promotion_gate["runtime_ready"] = False
    planning_only = sorted(requested & (PLANNING_ONLY_TARGET_SETS | MISSION_CONSUME_ONLY_TARGET_SETS))
    promotion_gate["ready_scope"] = (
        "planning_only" if planning_only and set(non_release) == set(planning_only) else "internal_layout_only"
    )
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append({"reason": "target_set_not_release_readiness", "count": len(non_release)})


def block_ambiguous_target_set_coverage(report: dict[str, Any], target_sets: list[str]) -> None:
    if report.get("schema") != "obelisk.reflection-snapshot-readiness.v1":
        return
    if report.get("gate_mode") != "second_source_promotion":
        return
    overlaps = target_set_target_overlaps(target_sets)
    if not overlaps:
        return
    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        return
    promotion_gate["ready"] = False
    promotion_gate["ready_scope"] = "not_ready"
    promotion_gate["public_sdk_ready"] = False
    promotion_gate["runtime_ready"] = False
    blockers = promotion_gate.setdefault("blockers", [])
    if isinstance(blockers, list):
        blockers.append(
            {
                "reason": "ambiguous_target_set_coverage",
                "count": len(overlaps),
                "targets": [item["target"] for item in overlaps],
            }
        )
    report["target_set_coverage_ambiguity"] = overlaps


def readiness_report_target_set_coverage(
    *,
    target_sets: list[str],
    observed_targets: set[str],
) -> dict[str, Any] | None:
    if not target_sets:
        return None

    from reflection_target_sets import (
        TARGET_SET_REVISION_SCHEMA,
        TARGET_SET_REVISION_SOURCE,
        target_set_revision_source_sha256,
    )

    expected_targets: list[str] = []
    expected_seen: set[str] = set()
    declared_target_sets = []
    for target_set in sorted(target_sets):
        target_set_targets = list(TARGET_SETS[target_set])
        for target in target_set_targets:
            if target not in expected_seen:
                expected_targets.append(target)
                expected_seen.add(target)
        covered_targets = sorted(set(target_set_targets) & observed_targets)
        missing_targets = sorted(set(target_set_targets) - observed_targets)
        declared_target_sets.append(
            {
                "name": target_set,
                "source": "readiness_report",
                "module_lane": target_set_module_lane(target_set),
                "readiness_classification": target_set_readiness_classification(target_set),
                "expected_targets": sorted(target_set_targets),
                "covered_targets": covered_targets,
                "missing_targets": missing_targets,
                "complete": not missing_targets,
            }
        )

    schema_observed_targets = {target for target in observed_targets if ":" in target}
    expected_set = set(expected_targets)
    covered_targets = sorted(expected_set & schema_observed_targets)
    missing_targets = sorted(expected_set - schema_observed_targets)
    unexpected_targets = sorted(schema_observed_targets - expected_set)
    complete = not missing_targets and not unexpected_targets
    return {
        "schema": READINESS_TARGET_SET_COVERAGE_SCHEMA,
        "status": "complete" if complete else "incomplete",
        "complete": complete,
        "target_sets": sorted(target_sets),
        "target_set_revision_schema": TARGET_SET_REVISION_SCHEMA,
        "target_set_revision_source": TARGET_SET_REVISION_SOURCE,
        "target_set_revision_source_sha256": target_set_revision_source_sha256(sorted(target_sets)),
        "declared_target_sets": declared_target_sets,
        "expected_targets": sorted(expected_targets),
        "observed_targets": sorted(schema_observed_targets),
        "covered_targets": covered_targets,
        "missing_targets": missing_targets,
        "unexpected_targets": unexpected_targets,
    }


def main() -> int:
    args = parse_args()
    reject_target_set_catalog_hygiene_issues()
    if args.list_target_sets:
        report = target_set_report()
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_text(report)
        return 0
    if args.list_target_guidance:
        target_filters = expand_target_filters(args.target, args.target_set)
        reject_duplicate_target_set_guidance_filters(args.target_set)
        reject_duplicate_target_guidance_filters(args.target)
        unmatched_guidance = unmatched_target_guidance_filters(args.target)
        if unmatched_guidance:
            raise SystemExit(
                "target guidance filter did not match known guidance: "
                + ", ".join(sorted(unmatched_guidance))
            )
        report = target_guidance_report(target_filters)
        report["target_sets"] = sorted(args.target_set)
        report["target_set_guidance"] = target_set_guidance_report(args.target_set)
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print_text(report)
        return 0

    reject_invalid_target_set_filters(args.target_set)
    target_filters = expand_target_filters(args.target, args.target_set)
    if args.base_root is None:
        raise SystemExit("--base-root is required unless --list-target-sets or --list-target-guidance is used")
    if args.fail_on_readiness_gaps and args.allow_ark_sha_mismatch:
        raise SystemExit("--allow-ark-sha-mismatch is incompatible with --fail-on-readiness-gaps")
    if args.planning_layout_intake and not args.readiness_report:
        raise SystemExit("--planning-layout-intake requires --readiness-report")
    if args.planning_layout_intake and args.fail_on_readiness_gaps:
        raise SystemExit("--planning-layout-intake is incompatible with --fail-on-readiness-gaps")
    if args.planning_layout_intake and not args.target_set:
        raise SystemExit("--planning-layout-intake requires at least one --target-set")
    if args.planning_layout_intake:
        non_planning = sorted(set(args.target_set) - PLANNING_ONLY_TARGET_SETS)
        if non_planning:
            raise SystemExit(
                "--planning-layout-intake only accepts planning-only target sets: "
                + ", ".join(non_planning)
            )
    if args.lifecycle_snapshot_root_check:
        if args.readiness_report:
            raise SystemExit("--lifecycle-snapshot-root-check is separate from --readiness-report")
        if args.observed_fname_chain:
            raise SystemExit("--lifecycle-snapshot-root-check is separate from --observed-fname-chain")
        if args.fail_on_readiness_gaps or args.fail_on_base_readiness_gaps or args.planning_layout_intake:
            raise SystemExit("--lifecycle-snapshot-root-check is not a promotion or readiness gate")
        if args.target or args.target_set:
            raise SystemExit("--lifecycle-snapshot-root-check compares the fixed HandleNewPlayer/OnLogout target set")
        if args.strict_identity_indices:
            raise SystemExit("--lifecycle-snapshot-root-check uses semantic layout comparison without strict identity indices")
        if args.allow_ark_sha_mismatch:
            raise SystemExit("--allow-ark-sha-mismatch is incompatible with --lifecycle-snapshot-root-check")
        if args.candidate_root is None:
            raise SystemExit("--candidate-root is required with --lifecycle-snapshot-root-check")
    if args.observed_fname_chain:
        if args.candidate_root:
            raise SystemExit("--observed-fname-chain does not accept --candidate-root")
        if args.readiness_report:
            raise SystemExit("--observed-fname-chain is separate from --readiness-report")
        if args.fail_on_readiness_gaps or args.fail_on_base_readiness_gaps or args.planning_layout_intake:
            raise SystemExit("--observed-fname-chain is not a promotion, readiness, or planning-layout gate")
        if args.observed_fname_chain_occurrences is not None and args.observed_fname_chain_occurrences < 1:
            raise SystemExit("--observed-fname-chain-occurrences must be a positive integer")
        validate_observed_fname_target_sets(args.observed_fname_target, args.target_set)
    elif args.observed_fname_chain_occurrences is not None:
        raise SystemExit("--observed-fname-chain-occurrences requires --observed-fname-chain")
    reject_snapshot_input_path("--base-root", args.base_root)
    if args.candidate_root:
        reject_snapshot_input_path("--candidate-root", args.candidate_root)
    if args.lifecycle_snapshot_root_check:
        reject_forbidden_lifecycle_input_root("--base-root", args.base_root)
        reject_forbidden_lifecycle_input_root("--candidate-root", args.candidate_root)
    base = load_snapshot_set(args.base_root)
    if args.observed_fname_chain:
        observed_name_indices = parse_observed_fname_chain(args.observed_fname_chain)
        report = observed_fname_chain_report(
            base,
            observed_target=args.observed_fname_target,
            observed_name_indices=observed_name_indices,
            observed_chain_occurrences=args.observed_fname_chain_occurrences or 1,
            target_sets=args.target_set,
        )
    elif args.lifecycle_snapshot_root_check:
        candidate = load_snapshot_set(args.candidate_root)
        report = lifecycle_snapshot_root_requirement_report(base, candidate)
    else:
        candidate = load_snapshot_set(args.candidate_root) if args.candidate_root else None
    if args.readiness_report:
        report = readiness_report(
            base,
            strict_identity_indices=args.strict_identity_indices,
            allow_ark_sha_mismatch=args.allow_ark_sha_mismatch,
            target_filters=target_filters,
            candidate=candidate,
        )
        report["target_set_guidance"] = target_set_guidance_report(args.target_set)
        if args.fail_on_readiness_gaps:
            report["gate_mode"] = "second_source_promotion"
        elif args.fail_on_base_readiness_gaps:
            report["gate_mode"] = "base_fixture_readiness"
        elif args.planning_layout_intake:
            report["gate_mode"] = "planning_layout_intake"
        else:
            report["gate_mode"] = "informational_gap_report"
        apply_readiness_gate_mode(report)
        apply_planning_layout_intake_gate(report, args.target_set)
        require_target_set_for_promotion(report, args.target_set)
        block_explicit_targets_outside_named_target_sets(report, args.target, args.target_set)
        block_ambiguous_target_set_coverage(report, args.target_set)
        block_non_release_target_set_promotion(report, args.target_set)
        coverage = readiness_report_target_set_coverage(
            target_sets=args.target_set,
            observed_targets={
                detail["target"]
                for module in report.get("modules", [])
                if isinstance(module, dict)
                for detail in module.get("target_details", [])
                if isinstance(detail, dict) and isinstance(detail.get("target"), str)
            },
        )
        if coverage is not None:
            report["target_set_coverage"] = coverage
    elif not args.observed_fname_chain and not args.lifecycle_snapshot_root_check:
        if candidate is None:
            raise SystemExit("--candidate-root is required unless --readiness-report is used")
        report = compare_sets(
            base,
            candidate,
            strict_identity_indices=args.strict_identity_indices,
            allow_ark_sha_mismatch=args.allow_ark_sha_mismatch,
            target_filters=target_filters,
        )
    report["target_sets"] = sorted(args.target_set)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    if report["schema"] == "obelisk.reflection-snapshot-readiness.v1":
        if args.fail_on_base_readiness_gaps:
            totals = report["totals"]
            if totals["targets"] == 0 or totals["blocked"]:
                return 1
        if args.fail_on_readiness_gaps:
            totals = report["totals"]
            if totals["targets"] == 0:
                return 1
            if totals["blocked"] or totals["second_source_rejected"]:
                return 1
            if totals["second_source_inconclusive"] or totals["second_source_missing"]:
                return 2
            if not report["promotion_gate"].get("ready"):
                return 1
        if args.planning_layout_intake:
            if not report.get("planning_layout_gate", {}).get("ready"):
                return 1
        return 0
    if report["schema"] == LIFECYCLE_SNAPSHOT_ROOT_CHECK_SCHEMA:
        if report.get("offline_requirement", {}).get("satisfied"):
            return 0
        counts = report.get("comparison_counts", {})
        if counts.get("rejected"):
            return 1
        return 2
    if report["schema"] == "obelisk.reflection-observed-fname-chain-check.v1":
        return 0
    if report["counts"]["rejected"]:
        return 1
    if report["counts"]["inconclusive"]:
        return 2
    if sum(report["counts"].values()) == 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
