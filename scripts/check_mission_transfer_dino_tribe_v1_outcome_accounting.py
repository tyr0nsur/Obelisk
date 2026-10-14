#!/usr/bin/env python3
"""Validate v1 outcome accounting for mission/transfer/dino/tribe/buff.

This is an accounting guardrail, not a promotion checker.  The current repository
state is allowed to remain candidate-only/planning.  A v1 release statement that
uses this umbrella blocker must exclude the umbrella and name every leaf as
excluded; promoted leaf attempts are reported as blocked because this checker
must not create a public SDK, runtime, or v1 completion path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_dino_scalar_readiness as dino_scalar_readiness
import check_mission_copied_bool_readiness as mission_copied_bool_readiness
import check_transfer_baccept_readiness as transfer_baccept_readiness
import check_transfer_scriptstruct_readiness as transfer_scriptstruct_readiness
from check_tribe_scalar_boundary_readiness import (
    DEFAULT_SNAPSHOT_ROOT as DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
    EXPECTED_ACCEPTED_FIELDS as TRIBE_EXPECTED_ACCEPTED_FIELDS,
    EXPECTED_REQUIRED_REDACTIONS as TRIBE_EXPECTED_REQUIRED_REDACTIONS,
    FORBIDDEN_READY_KEYS as TRIBE_FORBIDDEN_READY_KEYS,
    REPORT_SCHEMA as TRIBE_SCALAR_BOUNDARY_SCHEMA,
    TARGET_SET as TRIBE_SCALAR_TARGET_SET,
    build_report as build_tribe_scalar_boundary_report,
)
from check_buff_status_readiness import (
    DEFAULT_SNAPSHOT_ROOT as DEFAULT_BUFF_STATUS_SNAPSHOT_ROOT,
    EXPECTED_COPIED_BOOL_FIELDS as BUFF_EXPECTED_COPIED_BOOL_FIELDS,
    EXPECTED_REDACTED_FIELDS as BUFF_EXPECTED_REDACTED_FIELDS,
    EXPECTED_TARGETS as BUFF_EXPECTED_TARGETS,
    EXPECTED_ZERO_PARAM_TARGETS as BUFF_EXPECTED_ZERO_PARAM_TARGETS,
    FORBIDDEN_NONZERO_KEYS as BUFF_FORBIDDEN_NONZERO_KEYS,
    FORBIDDEN_READY_KEYS as BUFF_FORBIDDEN_READY_KEYS,
    REPORT_SCHEMA as BUFF_STATUS_SCHEMA,
    TARGET_SETS_USED as BUFF_TARGET_SETS_USED,
    build_report as build_buff_status_report,
)
from reflection_target_sets import side_lane_fail_closed_source_artifact_issues
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_SPLIT_NOTE = REPO_ROOT / "docs" / "research" / "2026-06-01-mission-transfer-dino-tribe-v1-split.md"
REPORT_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-outcome-accounting-check.v1"
SURFACE_ID = "obelisk.mission_transfer_dino_tribe.v1"
REQUIRED_LEAVES = ("mission", "transfer", "dino_policy", "tribe_policy", "buff_status")
MISSION_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-mission-leaf-blocker-accounting.v1"
TRANSFER_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-transfer-leaf-blocker-accounting.v1"
DINO_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-dino-leaf-blocker-accounting.v1"
TRANSFER_SCRIPTSTRUCT_LEAF_ACCOUNTING_SCHEMA = (
    "obelisk.mission-transfer-dino-tribe-v1-transfer-scriptstruct-leaf-blocker-accounting.v1"
)
TRIBE_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-tribe-leaf-blocker-accounting.v1"
BUFF_LEAF_ACCOUNTING_SCHEMA = "obelisk.mission-transfer-dino-tribe-v1-buff-leaf-blocker-accounting.v1"
MISSION_REQUIRED_EVIDENCE = ("mission-compact-intake", "mission-copied-bool-policy-slice")
TRANSFER_REQUIRED_EVIDENCE = ("transfer-ufunction-intake", "transfer-baccept-only-policy-slice")
DINO_REQUIRED_EVIDENCE = ("dino-compact-intake",)
TRIBE_REQUIRED_EVIDENCE = ("tribe-compact-intake",)
BUFF_REQUIRED_EVIDENCE = ("buff-compact-intake", "buff-breadth-intake")
SIDE_LANE_EXPECTED_TARGET_SETS_BY_LEAF = {
    "mission": MISSION_REQUIRED_EVIDENCE,
    "transfer": TRANSFER_REQUIRED_EVIDENCE + (transfer_scriptstruct_readiness.TARGET_SET,),
    "dino_policy": DINO_REQUIRED_EVIDENCE,
    "tribe_policy": TRIBE_REQUIRED_EVIDENCE,
    "buff_status": BUFF_REQUIRED_EVIDENCE,
}
SIDE_LANE_SURFACE_EXPECTED_TARGET_SETS = tuple(
    sorted({target_set for target_sets in SIDE_LANE_EXPECTED_TARGET_SETS_BY_LEAF.values() for target_set in target_sets})
)
MISSION_COPIED_TARGETS = (
    "MissionType.AddPlayerToMission",
    "MissionType.BPAllowPlayerToLeaveMission",
    "MissionType.BPOnPlayerRemovedFromMission",
)
MISSION_RECOGNITION_ONLY_TARGETS = ("MissionType.GetPlayerUsableItems",)
MISSION_COPIED_BOOL_FIELDS = (
    "MissionType.AddPlayerToMission.bForceAdd",
    "MissionType.AddPlayerToMission.ReturnValue",
    "MissionType.BPAllowPlayerToLeaveMission.ReturnValue",
    "MissionType.BPOnPlayerRemovedFromMission.bFromMissionCompleteEvent",
    "MissionType.BPOnPlayerRemovedFromMission.bLastPhaseSuccess",
)
MISSION_REDACTED_RECOGNITION_FIELDS = (
    "MissionType.AddPlayerToMission.PlayerCharacter",
    "MissionType.BPAllowPlayerToLeaveMission.PlayerPawn",
    "MissionType.BPOnPlayerRemovedFromMission.Player",
    "MissionType.BPOnPlayerRemovedFromMission.Controller",
    "MissionType.GetPlayerUsableItems.Character",
    "MissionType.GetPlayerUsableItems.OutItemIDs",
)
MISSION_READINESS_FLAGS = mission_copied_bool_readiness.false_readiness_flags()
MISSION_PUBLIC_FALSE_KEYS = tuple(key for key, value in MISSION_READINESS_FLAGS.items() if value is False)
MISSION_ZERO_FIELDS = tuple(
    key for key, value in MISSION_READINESS_FLAGS.items() if isinstance(value, int) and not isinstance(value, bool)
)
TRANSFER_PUBLIC_FALSE_KEYS = tuple(transfer_baccept_readiness.REPORT_FALSE_FLAGS)
TRANSFER_ZERO_FIELDS = tuple(transfer_baccept_readiness.REPORT_ZERO_FIELDS)
TRANSFER_SCRIPTSTRUCT_PUBLIC_FALSE_KEYS = tuple(transfer_scriptstruct_readiness.REPORT_FALSE_FLAGS)
TRANSFER_SCRIPTSTRUCT_ZERO_FIELDS = tuple(transfer_scriptstruct_readiness.REPORT_ZERO_FIELDS)
DINO_PUBLIC_FALSE_KEYS = (
    "dino_sdk_ready",
    "sdk_ready",
    "module_sdk_ready",
    "public_sdk_ready",
    "public_dino_sdk_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_callback_ready",
    "public_module_ready",
    "runtime_ready",
    "runtime_capture_ready",
    "runtime_hook_ready",
    "runtime_wiring_ready",
    "runtime_observer_approved",
    "live_ops_ready",
    "dispatcher_ready",
    "callback_ready",
    "descriptor_ready",
    "capability_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "return_override_ready",
    "resource_handle_ready",
    "v1_accounted",
    "v1_completion",
    "v1_completion_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_ready",
    "public_or_runtime_accounting_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "complete_sdk_claim_allowed",
    "stable_claim_allowed",
    "postcall_return_ready",
    "promotion_ready",
)
DINO_ZERO_FIELDS = (
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
)
OPTIONAL_FOCUSED_REPORT_FALSE_KEYS = (
    "complete_sdk_ready",
    "sdk_complete",
    "sdk_completion",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "stable_sdk_claim_allowed",
    "v1_accounted",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
)
OPTIONAL_FOCUSED_REPORT_ZERO_FIELDS = (
    "sdk_completion_progress_contribution",
    "stable_sdk_progress_contribution",
    "v1_completion_progress_contribution",
)
UMBRELLA_ACCOUNTING_FALSE_FLAGS = {
    "complete_sdk_ready": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_v1_completion": False,
    "p0_dependency_chain_accounted": False,
    "p0_dependency_chain_ready": False,
    "public_module_ready": False,
    "public_or_runtime_accounting_allowed": False,
    "readiness_counts_toward_v1_accounting": False,
    "runtime_capture_ready": False,
    "v1_completion_ready": False,
    "live_ops_ready": False,
}
UMBRELLA_ACCOUNTING_ZERO_FIELDS = {
    "complete_sdk_claim_progress_contribution": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "v1_completion_progress_contribution": 0,
}
TRIBE_PUBLIC_FALSE_KEYS = (
    "public_sdk_ready",
    "public_tribe_sdk_ready",
    "public_abi_ready",
    "public_module_ready",
    "runtime_ready",
    "runtime_capture_ready",
    "runtime_observer_approved",
    "live_ops_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "return_override_ready",
    "resource_handle_ready",
    "v1_completion_ready",
    "promotion_ready",
)
BUFF_PUBLIC_FALSE_KEYS = (
    "public_sdk_ready",
    "public_buff_sdk_ready",
    "buff_sdk_ready",
    "buff_status_sdk_ready",
    "sdk_ready",
    "module_sdk_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_callback_ready",
    "public_descriptor_ready",
    "public_capability_ready",
    "public_module_ready",
    "runtime_ready",
    "runtime_capture_ready",
    "runtime_hook_ready",
    "runtime_wiring_ready",
    "runtime_observer_approved",
    "live_ops_ready",
    "dispatcher_ready",
    "callback_ready",
    "descriptor_ready",
    "capability_ready",
    "identity_ready",
    "lookup_ready",
    "mutation_ready",
    "return_override_ready",
    "resource_handle_ready",
    "v1_accounted",
    "v1_completion",
    "v1_completion_ready",
    "promotion_ready",
    "copied_payload_policy_ready",
    "lifecycle_semantics_ready",
    "stable_claim_allowed",
    "complete_sdk_claim_allowed",
    "counts_toward_complete_sdk_claim",
)
MISSION_SPLIT_NOTE_REQUIRED_TOKENS = (
    "mission-copied-bool-policy-slice",
    "promote-mode blocked",
    "MissionType.GetPlayerUsableItems",
    "recognition-only",
) + MISSION_COPIED_TARGETS + MISSION_RECOGNITION_ONLY_TARGETS + MISSION_COPIED_BOOL_FIELDS + MISSION_REDACTED_RECOGNITION_FIELDS
MISSION_CANDIDATE_FORBIDDEN_TRUE_KEYS = {
    "abi_ready",
    "callback_ready",
    "capability_bit_ready",
    "capability_ready",
    "complete_sdk_claim_allowed",
    "counts_toward_complete_sdk_claim",
    "descriptor_ready",
    "dino_sdk_ready",
    "dispatcher_ready",
    "full_sdk_claim_allowed",
    "identity_available",
    "identity_ready",
    "lifecycle_semantics_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_ready",
    "p0_ready",
    "lookup_available",
    "lookup_ready",
    "mission_sdk_ready",
    "module_ready",
    "module_sdk_ready",
    "mutation_available",
    "mutation_ready",
    "ownership_ready",
    "promotion_ready",
    "production_sdk_claim_allowed",
    "public_abi_ready",
    "public_abi_available",
    "public_api_ready",
    "public_callback_ready",
    "public_capability_ready",
    "public_descriptor_ready",
    "public_header_ready",
    "public_dino_sdk_ready",
    "public_buff_sdk_ready",
    "public_buff_status_sdk_ready",
    "public_sdk_available",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_mission_sdk_ready",
    "public_sdk_ready",
    "public_transfer_sdk_ready",
    "public_tribe_sdk_ready",
    "release_readiness",
    "release_ready",
    "release_supported",
    "resource_handle_available",
    "resource_handle_ready",
    "runtime_available",
    "runtime_approved",
    "runtime_evidence_approved",
    "return_override_available",
    "return_override_ready",
    "runtime_observer_approved",
    "runtime_observer_ready",
    "runtime_hook_ready",
    "runtime_ready",
    "runtime_wiring_ready",
    "sdk_complete",
    "sdk_completion",
    "sdk_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "stable_release_claim_allowed",
    "stable_sdk_claim_allowed",
    "support_tier_active",
    "support_tier_ready",
    "support_tier_supported",
    "v1_accounted",
    "transfer_sdk_ready",
    "tribe_sdk_ready",
    "buff_sdk_ready",
    "buff_status_sdk_ready",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
    "mission_sdk_available",
    "mission_sdk_promoted",
    "mission_public_sdk_ready",
    "transfer_runtime_available",
    "transfer_runtime_ready",
    "transfer_runtime_promoted",
    "transfer_sdk_available",
    "dino_policy_promoted",
    "dino_policy_promotion_ready",
    "dino_policy_sdk_ready",
    "dino_sdk_available",
    "public_dino_policy_sdk_ready",
    "tribe_policy_promoted",
    "tribe_policy_promotion_ready",
    "tribe_policy_sdk_ready",
    "tribe_sdk_available",
    "public_tribe_policy_sdk_ready",
    "buff_status_public_abi_ready",
    "buff_status_public_c_abi_ready",
    "buff_status_callback_ready",
    "buff_status_sdk_available",
    "public_c_abi_ready",
    "public_c_abi_available",
    "copied_payload_policy_ready",
    "contributes_to_public_sdk_v1",
    "contributes_to_v1_completion",
    "counts_for_public_sdk_v1",
    "counts_toward_full_sdk_claim",
    "counts_toward_production_sdk_claim",
    "counts_toward_sdk_completion",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
}
CANDIDATE_FORBIDDEN_PROMOTED_STRING_KEYS = {
    "accounting_route",
    "dino_policy",
    "dino_policy_status",
    "leaf_status",
    "policy_status",
    "promotion_status",
    "public_sdk_status",
    "release_status",
    "resource_handle_status",
    "runtime_status",
    "sdk_completion",
    "status",
    "support_tier",
    "tribe_policy",
    "tribe_policy_status",
    "v1_completion",
}
CANDIDATE_FORBIDDEN_PROMOTED_STRING_VALUES = {
    "accepted",
    "active",
    "approved",
    "available",
    "allowed",
    "complete",
    "completed",
    "enabled",
    "passed",
    "per_leaf_promoted",
    "promoted",
    "public",
    "public_ready",
    "published",
    "ready",
    "release_ready",
    "release_supported",
    "runtime",
    "runtime_ready",
    "sdk_ready",
    "stable",
    "stable_sdk",
    "stable_ready",
    "supported",
    "true",
    "unblocked",
    "unlocked",
    "validated",
    "v1_complete",
    "v1_ready",
}
CONTEXTUAL_POSITIVE_STATUS_KEYS = {
    "accepted",
    "active",
    "approved",
    "allowed",
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
    "unblocked",
    "unlocked",
    "validated",
}
CONTEXTUAL_CANDIDATE_CONTAINER_KEYS = {
    "candidate",
    "package_shape",
    "plugin_hub",
    "public_sdk",
    "readiness",
    "runtime",
    "support_tier",
    "target_set",
    "v1",
}
LEAF_ALIASES = {
    "mission": ("mission",),
    "transfer": ("transfer",),
    "dino_policy": ("dino_policy", "dino policy", "dino-policy"),
    "tribe_policy": ("tribe_policy", "tribe policy", "tribe-policy"),
    "buff_status": ("buff_status", "buff/status", "buff status", "buff-status"),
}
PROMOTED_LEAF_EVIDENCE_KEYS = ("abi_tests", "sdk_consumer_tests", "second_source_evidence")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
POSITIVE_PROGRESS_RATIO_RE = re.compile(r"^\s*[1-9][0-9]*\s*/\s*[1-9][0-9]*\s*$")
LEAF_MISSING_PUBLIC_GATES = {
    "mission": (
        "public_mission_sdk_abi",
        "runtime_observer_approval",
        "mission_identity_state_reward_authority",
        "dispatcher_lifecycle",
        "installed_sdk_consumer_tests",
        "mutation_return_override_policy",
    ),
    "transfer": (
        "public_transfer_sdk_abi",
        "transfer_payload_ownership",
        "downloaded_character_payload_contract",
        "dino_payload_contract",
        "player_identity",
        "cross_map_state_correlation",
        "ownership_policy",
        "teleport_spawn_authority",
        "runtime_wiring",
        "mutation_return_override_policy",
    ),
    "dino_policy": (
        "public_dino_sdk_abi",
        "dino_player_passenger_identity",
        "lookup_ownership_lifetime",
        "postcall_return_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_contract",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
    "tribe_policy": (
        "public_tribe_sdk_abi",
        "tribe_player_identity",
        "permission_semantics",
        "log_string_array_payload_policy",
        "online_list_payload_policy",
        "mission_tag_payload_policy",
        "dispatcher_lifecycle",
        "runtime_observation",
        "privacy_redaction_contract",
        "mutation_return_override_policy",
    ),
    "buff_status": (
        "public_buff_status_sdk_abi",
        "buff_class_object_redaction_contract",
        "copied_payload_policy",
        "lifecycle_stacking_invalidation_semantics",
        "dispatcher_lifecycle",
        "runtime_observation",
        "resource_handle_policy",
        "mutation_return_override_policy",
    ),
}
LEAF_PRIORITY_PROFILES = {
    "mission": {
        "base_score": 80,
        "required_evidence": ("mission-compact-intake", "mission-copied-bool-policy-slice"),
        "reusable_evidence": (
            "focused copied-bool readiness checker",
            "fixture-backed exact Mission metadata",
            "five canonical copied bool fields",
            "recognition-only redaction for object and array fields",
        ),
        "blocking_risk": (
            "runtime observer approval",
            "dispatcher lifecycle",
            "public ABI and SDK consumer coverage",
            "mission/player identity and reward authority",
        ),
        "next_v1_reuse_step": (
            "Harden the internal copied-bool fail-closed contract and keep object, "
            "identity, array, mutation, and return-override claims excluded."
        ),
    },
    "dino_policy": {
        "base_score": 72,
        "required_evidence": ("dino-compact-intake",),
        "reusable_evidence": (
            "focused scalar readiness checker",
            "accepted compact passenger/carry layout evidence",
            "pre-call scalar-only planning path",
            "explicit return-value deferral",
        ),
        "blocking_risk": (
            "dino/player/passenger identity",
            "lookup and lifetime ownership",
            "post-call return semantics",
            "runtime privacy and dispatcher lifecycle",
        ),
        "next_v1_reuse_step": (
            "Reuse the scalar-only redaction model after Mission; keep dino/player "
            "object references and return values recognition-only."
        ),
    },
    "transfer": {
        "base_score": 68,
        "required_evidence": ("transfer-ufunction-intake", "transfer-baccept-only-policy-slice"),
        "reusable_evidence": (
            "focused bAccept copied-bool checker",
            "candidate-only Transfer ScriptStruct checker",
            "redacted Transfer ScriptStruct payload layout summary",
            "complete transfer intake provenance",
            "explicit consume-only promote gate",
        ),
        "blocking_risk": (
            "payload ownership",
            "downloaded character and dino payload contracts",
            "player identity and cross-map correlation",
            "teleport/spawn authority",
        ),
        "next_v1_reuse_step": (
            "Reuse only the single copied-bool consume gate and candidate ScriptStruct layout summary; "
            "defer transfer payload decoding, identity, ownership, cross-map state, teleport/spawn, mutation, and return override."
        ),
    },
    "buff_status": {
        "base_score": 62,
        "required_evidence": ("buff-compact-intake", "buff-breadth-intake"),
        "reusable_evidence": (
            "focused Buff/status readiness checker",
            "compact and breadth layout evidence",
            "six canonical copied bool fields",
            "candidate class/object redaction boundary",
            "zero-param lifecycle shape accounting",
        ),
        "blocking_risk": (
            "copied payload policy",
            "lifecycle, stacking, and invalidation semantics",
            "public ABI and dispatcher lifecycle",
            "runtime observation and ResourceHandle policy",
        ),
        "next_v1_reuse_step": (
            "Use the Buff/status checker output to plan a copied-bool payload policy; "
            "keep class/object exposure, lifecycle semantics, ResourceHandle, mutation, "
            "and return override excluded."
        ),
    },
    "tribe_policy": {
        "base_score": 52,
        "required_evidence": ("tribe-compact-intake",),
        "reusable_evidence": (
            "compact layout evidence",
            "permission/log/online-list target vocabulary",
            "candidate split between scalar permission and array/string payload work",
        ),
        "blocking_risk": (
            "tribe/player identity",
            "permission semantics",
            "log, string, and array payload ownership",
            "privacy redaction and runtime observation",
        ),
        "next_v1_reuse_step": (
            "Split any future work into a narrow scalar permission/log-request intake and "
            "a separately blocked array/string payload lane before public discussion."
        ),
    },
}
NEGATIVE_EVIDENCE_RE = re.compile(
    r"\b(?:candidate[- ]?only|consume[- ]?only|planning[- ]?only|not promoted|"
    r"promotion[_ -]?ready\s*[:=]\s*false|public[_ -]?sdk[_ -]?ready\s*[:=]\s*false|"
    r"runtime[_ -]?ready\s*[:=]\s*false)\b",
    re.IGNORECASE,
)
NON_PROMOTIONAL_SCHEMA_KEYS = {"schema", "artifact_schema", "evidence_schema", "report_schema"}
NON_PROMOTIONAL_SCHEMA_TOKENS = {
    "approved_bundle",
    "approved_runtime_bundle",
    "candidate",
    "consume",
    "planning",
    "preflight",
    "readiness",
    "request",
    "window",
    "sidecar",
}
NON_PROMOTIONAL_PATH_MARKERS = (
    "approved_bundle",
    "approved_runtime_bundle",
    "candidate",
    "consume",
    "planning",
    "preflight",
    "readiness",
    "request",
    "window",
    "sidecar",
)
FORBIDDEN_CLAIM_PATTERNS = (
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+(?:SDK|API)\b",
    r"\bpublic\s+(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+"
    r"(?:SDK|API|module|surface|callback|callbacks|descriptor|descriptors|capability|capabilities|"
    r"capability\s+bit|C\s+ABI|ABI)\b",
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+"
    r"(?:module|surface|callback|callbacks|descriptor|descriptors|capability|capabilities|"
    r"capability\s+bit|C\s+ABI|ABI)\b",
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+public\s+"
    r"(?:SDK|API|module|surface|callback|callbacks|descriptor|descriptors|capability|capabilities|"
    r"capability\s+bit|C\s+ABI|ABI)\b",
    r"\b(?:Dino|Tribe)\s+policy\s+(?:is\s+)?(?:promoted|ready|available|published|enabled|allowed|unblocked|unlocked)\b",
    r"\b(?:public\s+)?module\s+(?:SDK|API|callback|callbacks|descriptor|descriptors|capability|capabilities|"
    r"capability\s+bit|C\s+ABI|ABI)\b",
    r"\bpublic\s+(?:SDK|API|ABI|module|surface|callback|descriptor|capability|capability\s+bit|C\s+ABI)\b",
    r"\b(?:public\s+)?(?:(?:C\s+ABI|ABI|SDK)\s+)?header\s+callbacks?\b",
    r"\b(?:callback|descriptor|capability|capability\s+bit)\s+"
    r"(?:is\s+)?(?:published|available|ready|enabled)\b",
    r"\bidentity\b",
    r"\blookup\b",
    r"\bmutation\b",
    r"\breturn[- ]override\b",
    r"\bruntime\s+(?:observer|hook|wiring|dispatch|dispatcher|callback)\b",
    r"\bruntime\s+hook\b",
    r"\bResourceHandle\b",
    r"\bResource\s+Handle\b",
    r"\bv1\s+(?:completion|complete|ready|release|promotion|accounted)\b",
    r"\bteleport\s*/\s*spawn\b",
    r"\bteleport[- ]spawn\b",
    r"\bteleport\b",
    r"\bspawn\b",
    r"\bownership\s+lookup\b",
    r"\bcross[- ]map\s+correlation\b",
)
FORBIDDEN_CLAIM_RE = re.compile("|".join(f"(?:{pattern})" for pattern in FORBIDDEN_CLAIM_PATTERNS), re.IGNORECASE)
CANDIDATE_READY_CLAIM_PATTERNS = (
    r"\b(?:public\s+SDK|public\s+ABI|runtime|runtime\s+observer|runtime\s+hook|"
    r"v1|v1\s+SDK|module\s+SDK|module\s+API|header\s+callbacks?|"
    r"ABI\s+header\s+callbacks?|C\s+ABI\s+header\s+callbacks?|promotion|"
    r"P0(?:\s+dependency[- ]?chain)?)\s+"
    r"(?:is\s+|are\s+)?(?:ready|readiness|complete|completion|available|published|enabled|allowed|unblocked|unlocked)\b",
    r"\b(?:Mission|Transfer|Dino|Tribe|Buff(?:/status| status)?|BuffStatus)\s+"
    r"(?:SDK|API|runtime|runtime\s+observer|runtime\s+hook|public\s+ABI|public\s+C\s+ABI|"
    r"ABI|C\s+ABI|callback|callbacks|ResourceHandle|mutation)\s+"
    r"(?:is\s+|are\s+)?(?:ready|readiness|complete|completion|available|published|enabled|promoted|allowed|unblocked|unlocked)\b",
    r"\b(?:ready|complete)\s+for\s+v1\b",
    r"\b(?:ready|complete|available|published|enabled)\s+"
    r"(?:module\s+SDK|module\s+API|header\s+callbacks?|ABI\s+header\s+callbacks?|"
    r"C\s+ABI\s+header\s+callbacks?)\b",
    r"\b(?:ready|complete|available|enabled|allowed|unblocked|unlocked)\s+for\s+v1\b",
    r"\bv1(?:\.0)?\s+(?:is\s+)?(?:stable|complete|completion|ready|allowed|unblocked|unlocked)\b",
    r"\b(?:complete|full|production|stable)\s+SDK\s+(?:claim\s+)?"
    r"(?:is\s+)?(?:allowed|ready|complete)\b",
    r"\b(?:stable\s+claim|complete\s+SDK\s+claim)\s+(?:is\s+)?allowed\b",
    r"\bcounts?\s+toward\s+(?:the\s+)?(?:complete|full|production)\s+SDK\s+claim\b",
    r"\bcredits?\s+(?:toward|for|to)\s+(?:the\s+)?(?:complete|full|production|public|v1)\s+SDK\s+claim\b",
    r"\b(?:counts?|contributes?)\s+(?:toward|for|to)\s+(?:the\s+)?"
    r"(?:public\s+SDK\s+v1|v1\s+(?:completion|SDK|release)|complete\s+SDK\s+claim)\b",
    r"\brelease\s+(?:readiness\s+)?(?:is\s+)?(?:ready|complete|satisfied|available|allowed|enabled|approved|unblocked|unlocked)\b",
    r"\brelease[- ]supported\b",
    r"\bsupport[- ]?tier\s+(?:is\s+)?(?:active|available|ready|allowed|enabled|supported|release[- ]supported|unblocked|unlocked)\b",
    r"\bstable\s+SDK\s+(?:is\s+)?(?:allowed|ready|complete|available|enabled|unblocked|unlocked)\b",
)
CANDIDATE_READY_CLAIM_RE = re.compile(
    "|".join(f"(?:{pattern})" for pattern in CANDIDATE_READY_CLAIM_PATTERNS),
    re.IGNORECASE,
)
CANDIDATE_MARKER_KEY_RE = re.compile(
    r"(?:status|support[_ -]?tier|target[_ -]?sets?|source[_ -]?(?:markers?|target[_ -]?sets?)|"
    r"artifact[_ -]?status|evidence[_ -]?status|reflection[_ -]?(?:evidence|status))",
    re.IGNORECASE,
)
CANDIDATE_MARKER_PROMOTION_RE = re.compile(
    r"\b(?:public|sdk|api|abi|runtime|observer|hook|wiring|dispatch|dispatcher|callback|"
    r"descriptor|capability|promot(?:e|ed|ion)?|approved(?:\s+runtime)?\s+bundle|"
    r"resource\s+handle|resourcehandle|identity|lookup|mutation|return\s+override|"
    r"v1|p0|dependency\s+chain|completion|complete|stable|release|support|tier|supported|"
    r"ready|available|allowed|enabled|unblocked|unlocked)\b",
    re.IGNORECASE,
)
CANDIDATE_MARKER_NON_PROMOTION_RE = re.compile(
    r"\b(?:candidate\s+only|planning\s+only|consume\s+only|evidence\s+only|"
    r"internal(?:\s+reusable)?\s+evidence\s+only|offline\s+review\s+only|"
    r"blocked|excluded|not\s+promoted|does\s+not|do\s+not|must\s+not|"
    r"no\s+public|no\s+runtime|false|redacted|intake|policy\s+slice)\b",
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1)\b",
    re.IGNORECASE,
)
NEGATED_EXCLUSION_RE = re.compile(
    r"\b(?:not|no\s+longer)\s+(?:blocked|excluded|omitted|out\s+of\s+scope|post[- ]v1|post\s+v1)\b",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="docs/public_sdk_surfaces.json path.")
    parser.add_argument("--split-note", type=Path, default=DEFAULT_SPLIT_NOTE, help="Leaf split research note path.")
    parser.add_argument(
        "--mission-root",
        type=Path,
        default=mission_copied_bool_readiness.DEFAULT_ROOT,
        help="Offline artifact root for the focused Mission copied-bool readiness checker.",
    )
    parser.add_argument(
        "--mission-manifest",
        type=Path,
        help="Mission copied-bool policy-slice manifest; defaults to --mission-root/mission-copied-bool-policy-slice.json.",
    )
    parser.add_argument(
        "--mission-expected-manifest-sha256",
        default=mission_copied_bool_readiness.EXPECTED_MANIFEST_SHA256,
        help="Expected Mission copied-bool policy manifest SHA256.",
    )
    parser.add_argument(
        "--mission-skip-artifact-gates",
        action="store_true",
        help="Skip Mission consume/promote gate subprocesses for hermetic checker tests.",
    )
    parser.add_argument(
        "--mission-fixture-boundary-only",
        action="store_true",
        help="Use Mission's repo fixture-boundary mode instead of artifact-root consume/promote checks.",
    )
    parser.add_argument(
        "--transfer-root",
        type=Path,
        default=transfer_baccept_readiness.DEFAULT_ROOT,
        help="Offline artifact root for the focused Transfer bAccept readiness checker.",
    )
    parser.add_argument(
        "--transfer-manifest",
        type=Path,
        help="Transfer bAccept policy-slice manifest; defaults to --transfer-root/transfer-baccept-only-policy-slice.json.",
    )
    parser.add_argument(
        "--transfer-expected-manifest-sha256",
        default=transfer_baccept_readiness.EXPECTED_MANIFEST_SHA256,
        help="Expected Transfer bAccept policy manifest SHA256.",
    )
    parser.add_argument(
        "--transfer-skip-artifact-gates",
        action="store_true",
        help="Skip Transfer consume/promote gate subprocesses for hermetic checker tests.",
    )
    parser.add_argument(
        "--transfer-scriptstruct-snapshot-root",
        type=Path,
        default=transfer_scriptstruct_readiness.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized ScriptStruct snapshot root for candidate-only Transfer payload layout evidence.",
    )
    parser.add_argument(
        "--transfer-scriptstruct-report",
        type=Path,
        help="Existing redacted ScriptStruct report JSON for hermetic Transfer ScriptStruct checker tests.",
    )
    parser.add_argument(
        "--dino-repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root for candidate-only Dino scalar source-isolation checks.",
    )
    parser.add_argument(
        "--dino-report",
        type=Path,
        help="Existing redacted UFunction signature report JSON for hermetic Dino scalar checker tests.",
    )
    parser.add_argument(
        "--dino-snapshot-root",
        type=Path,
        default=dino_scalar_readiness.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root for candidate-only Dino scalar evidence.",
    )
    parser.add_argument(
        "--tribe-snapshot-root",
        type=Path,
        default=DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root for candidate-only Tribe scalar evidence.",
    )
    parser.add_argument(
        "--buff-snapshot-root",
        type=Path,
        default=DEFAULT_BUFF_STATUS_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root for candidate-only Buff/status evidence.",
    )
    parser.add_argument("--release-statement", type=Path, help="Optional reviewed v1 release statement.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    item = {"reason": reason, "label": label}
    item.update(extra)
    blockers.append(item)


def add_side_lane_source_artifact_issues(
    blockers: list[dict[str, Any]],
    value: Any,
    *,
    label: str,
    expected_target_sets: tuple[str, ...],
    leaf: str | None = None,
) -> None:
    for issue in side_lane_fail_closed_source_artifact_issues(
        value,
        expected_target_sets=expected_target_sets,
        path=label,
    ):
        reason = issue.get("reason")
        path = issue.get("path")
        if not isinstance(reason, str) or not isinstance(path, str):
            continue
        extra = {key: child for key, child in issue.items() if key not in {"reason", "path"}}
        if leaf is not None:
            extra["leaf"] = leaf
        add(blockers, reason, path, **extra)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        reject_symlink_component(path, label)
        safe_path = reject_protected_input_path(path, label)
        payload = json.loads(safe_path.read_text(encoding="utf-8"))
    except SystemExit:
        raise
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: top-level JSON must be an object")
    return payload


def load_optional_focus_report(path: Path | None, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    if path is None:
        return None
    try:
        reject_symlink_component(path, label)
        safe_path = reject_protected_input_path(path, label)
        payload = json.loads(safe_path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "focused_report_unreadable", label, path=str(path), detail=str(exc))
        return {}
    except json.JSONDecodeError as exc:
        add(blockers, "focused_report_malformed", label, path=str(path), detail=str(exc))
        return {}
    except SystemExit as exc:
        add(blockers, "focused_report_path_rejected", label, path=str(path), detail=str(exc))
        return {}
    if not isinstance(payload, dict):
        add(blockers, "focused_report_not_object", label, path=str(path))
        return {}
    return payload


def surface_by_id(manifest: dict[str, Any], surface_id: str) -> dict[str, Any] | None:
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return None
    for surface in surfaces:
        if isinstance(surface, dict) and surface.get("id") == surface_id:
            return surface
    return None


def read_optional(path: Path | None, label: str) -> str:
    if path is None:
        return ""
    try:
        reject_symlink_component(path, label)
        safe_path = reject_protected_input_path(path, label)
        return safe_path.read_text(encoding="utf-8")
    except SystemExit:
        raise
    except OSError as exc:
        raise SystemExit(f"{label}: unreadable: {exc}") from exc


def leaf_map(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    units = surface.get("leaf_decision_units")
    if not isinstance(units, list):
        add(blockers, "leaf_decision_units_missing", "$.surfaces[mission_transfer_dino_tribe].leaf_decision_units")
        return {}
    leaves: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for index, leaf in enumerate(units):
        if not isinstance(leaf, dict):
            add(blockers, "leaf_decision_unit_not_object", f"$.leaf_decision_units[{index}]")
            continue
        leaf_id = leaf.get("id")
        if not isinstance(leaf_id, str):
            add(blockers, "leaf_decision_unit_id_missing", f"$.leaf_decision_units[{index}].id")
            continue
        if leaf_id in leaves:
            duplicate_ids.append(leaf_id)
        leaves[leaf_id] = leaf
    if duplicate_ids:
        add(blockers, "leaf_decision_units_duplicate", "$.leaf_decision_units", duplicate_ids=sorted(duplicate_ids))
    observed = set(leaves)
    required = set(REQUIRED_LEAVES)
    if observed != required:
        add(
            blockers,
            "leaf_decision_units_mismatch",
            "$.leaf_decision_units",
            expected=list(REQUIRED_LEAVES),
            observed=[leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in observed]
            + sorted(observed - required),
            missing=sorted(required - observed),
            extra=sorted(observed - required),
        )
    return leaves


def flattened_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        items: list[str] = []
        for child in value.values():
            items.extend(flattened_strings(child))
        return items
    if isinstance(value, list):
        items = []
        for child in value:
            items.extend(flattened_strings(child))
        return items
    return []


def string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    if isinstance(value, str):
        return [value]
    return []


def public_contract(surface_or_leaf: dict[str, Any]) -> list[str]:
    contract = surface_or_leaf.get("public_contract", [])
    return contract if isinstance(contract, list) else ["<public_contract is not a list>"]


def claim_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    clause_prefix = text[clause_start:start]
    if re.match(r"\s*No\b", clause_prefix, re.IGNORECASE):
        return True
    before = text[max(0, start - 40) : start]
    after = text[end : min(len(text), end + 80)]
    if NEGATED_EXCLUSION_RE.search(after):
        return False
    return bool(NEGATOR_RE.search(before) or AFTER_NEGATOR_RE.search(after))


def forbidden_claims(text: str) -> list[str]:
    claims: list[str] = []
    for match in FORBIDDEN_CLAIM_RE.finditer(text):
        if claim_is_negated(text, match.start(), match.end()):
            continue
        claims.append(match.group(0))
    return claims


def candidate_ready_claims(text: str) -> list[str]:
    claims: list[str] = []
    for match in CANDIDATE_READY_CLAIM_RE.finditer(text):
        if claim_is_negated(text, match.start(), match.end()):
            continue
        claims.append(match.group(0))
    return claims


def outcome_is_negated(text: str, start: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    before = text[clause_start:start]
    return bool(NEGATOR_RE.search(before))


def has_unnegated_alias_outcome(text: str, alias: str, outcome: str) -> bool:
    pattern = re.compile(
        rf"\b{re.escape(alias)}\b[^.;\n]{{0,100}}?\b({re.escape(outcome)})\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        if not outcome_is_negated(text, match.start(1)):
            return True
    return False


def validate_split_note(text: str, blockers: list[dict[str, Any]]) -> None:
    if SURFACE_ID not in text:
        add(blockers, "split_note_surface_missing", "$.split_note")
    for leaf in REQUIRED_LEAVES:
        if leaf not in text:
            add(blockers, "split_note_leaf_missing", "$.split_note", leaf=leaf)
    required_non_claims = (
        "does not promote a public SDK",
        "Public SDK promotion remains blocked for all five leaves",
    )
    for phrase in required_non_claims:
        if phrase not in text:
            add(blockers, "split_note_non_claim_missing", "$.split_note", phrase=phrase)
    for token in MISSION_SPLIT_NOTE_REQUIRED_TOKENS:
        if token not in text:
            add(
                blockers,
                "mission_leaf_accounting_split_note_token_missing",
                "$.split_note.mission_leaf_accounting",
                token=token,
            )


def release_statement_outcome(text: str) -> dict[str, Any]:
    if not text:
        return {
            "present": False,
            "umbrella_excluded": False,
            "leaf_exclusions": {},
            "leaf_promotions": {},
            "forbidden_claims": [],
            "ready_claims": [],
        }
    surface_line = next(
        (line for line in text.splitlines() if line.strip().startswith(f"{SURFACE_ID}:")),
        "",
    )
    surface_scope_text = surface_line if surface_line else text
    leaf_exclusions = {}
    leaf_promotions = {}
    for leaf, aliases in LEAF_ALIASES.items():
        alias_excluded = False
        alias_promoted = False
        for alias in aliases:
            alias_excluded = alias_excluded or has_unnegated_alias_outcome(
                surface_scope_text, alias, "excluded"
            )
            alias_promoted = alias_promoted or has_unnegated_alias_outcome(
                surface_scope_text, alias, "promoted"
            )
        leaf_exclusions[leaf] = alias_excluded
        leaf_promotions[leaf] = alias_promoted
    return {
        "present": True,
        "umbrella_excluded": bool(surface_line) and has_unnegated_alias_outcome(surface_line, SURFACE_ID, "excluded"),
        "leaf_exclusions": leaf_exclusions,
        "leaf_promotions": leaf_promotions,
        "forbidden_claims": sorted(set(forbidden_claims(surface_scope_text))),
        "ready_claims": sorted(set(candidate_ready_claims(surface_scope_text))),
    }


def evidence_for_leaf(surface: dict[str, Any], leaf: dict[str, Any]) -> dict[str, Any]:
    evidence = leaf.get("evidence")
    if isinstance(evidence, dict):
        return evidence
    per_leaf = surface.get("promotion_evidence_by_leaf")
    leaf_id = leaf.get("id")
    if isinstance(per_leaf, dict) and isinstance(per_leaf.get(leaf_id), dict):
        return per_leaf[leaf_id]
    return {}


def resolve_evidence_path(raw_path: str, manifest_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    repo_path = REPO_ROOT / path
    if repo_path.exists():
        return repo_path
    return manifest_dir / path


def relative_promoted_evidence_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_absolute() or not raw_path.strip():
        return None
    if any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path


def evidence_path_has_non_promotional_marker(raw_path: str) -> bool:
    relative = relative_promoted_evidence_path(raw_path)
    if relative is None:
        return True
    parts = [part.lower().replace("-", "_") for part in relative.parts]
    for part in parts:
        if "approved_bundle" in part or "approved_runtime_bundle" in part:
            return True
        tokens = {token for token in part.split("_") if token}
        for marker in NON_PROMOTIONAL_PATH_MARKERS:
            if marker in tokens or part.startswith(f"{marker}_") or part.endswith(f"_{marker}"):
                return True
    return False


def evidence_path_is_specific_to_leaf(raw_path: str, leaf_id: str, evidence_key: str) -> bool:
    relative = relative_promoted_evidence_path(raw_path)
    if relative is None:
        return False
    lowered = relative.name.lower()
    leaf_tokens = [token for token in leaf_id.replace("-", "_").split("_") if token]
    key_tokens = [token for token in evidence_key.replace("-", "_").split("_") if token]
    return all(token.lower() in lowered for token in leaf_tokens + key_tokens)


def evidence_has_non_promotional_schema_marker(value: Any, *, parent_key: str | None = None) -> bool:
    normalized_key = parent_key.lower().replace("-", "_") if isinstance(parent_key, str) else None
    if normalized_key in NON_PROMOTIONAL_SCHEMA_KEYS:
        try:
            text = json.dumps(value, sort_keys=True)
        except TypeError:
            text = str(value)
        normalized_text = text.lower().replace("-", "_").replace(" ", "_")
        if "approved_bundle" in normalized_text or "approved_runtime_bundle" in normalized_text:
            return True
        schema_tokens = {token for token in re.split(r"[^a-z0-9]+", text.lower()) if token}
        if schema_tokens & NON_PROMOTIONAL_SCHEMA_TOKENS:
            return True
    if isinstance(value, dict):
        return any(
            evidence_has_non_promotional_schema_marker(child, parent_key=key if isinstance(key, str) else None)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(evidence_has_non_promotional_schema_marker(child, parent_key=parent_key) for child in value)
    return False


def validate_promoted_leaf_gate_report(
    entry: Any,
    *,
    evidence_key: str,
    leaf_id: str,
    label: str,
    manifest_dir: Path,
    blockers: list[dict[str, Any]],
) -> None:
    if not isinstance(entry, dict):
        add(blockers, "promoted_leaf_gate_report_unverified", label, leaf=leaf_id, evidence_key=evidence_key)
        return
    raw_path = entry.get("path")
    expected_sha = entry.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        add(blockers, "promoted_leaf_evidence_path_missing", f"{label}.path", leaf=leaf_id, evidence_key=evidence_key)
        return
    if relative_promoted_evidence_path(raw_path) is None:
        add(
            blockers,
            "promoted_leaf_evidence_path_not_repo_relative",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if evidence_path_has_non_promotional_marker(raw_path):
        add(
            blockers,
            "promoted_leaf_evidence_path_non_promotional",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if not evidence_path_is_specific_to_leaf(raw_path, leaf_id, evidence_key):
        add(
            blockers,
            "promoted_leaf_evidence_path_not_leaf_specific",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=raw_path,
        )
        return
    if not isinstance(expected_sha, str) or SHA256_RE.fullmatch(expected_sha) is None:
        add(
            blockers,
            "promoted_leaf_evidence_sha256_missing",
            f"{label}.sha256",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
        return
    path = resolve_evidence_path(raw_path, manifest_dir)
    try:
        reject_symlink_component(path, f"{label}.path")
        safe_path = reject_protected_input_path(path, f"{label}.path")
    except SystemExit as exc:
        add(
            blockers,
            "promoted_leaf_evidence_path_rejected",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=str(path),
            detail=str(exc),
        )
        return
    try:
        content = safe_path.read_bytes()
    except OSError as exc:
        add(
            blockers,
            "promoted_leaf_evidence_path_missing",
            f"{label}.path",
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=str(path),
            detail=str(exc),
        )
        return
    actual_sha = hashlib.sha256(content).hexdigest()
    if actual_sha != expected_sha:
        add(
            blockers,
            "promoted_leaf_evidence_sha256_mismatch",
            f"{label}.sha256",
            leaf=leaf_id,
            evidence_key=evidence_key,
            expected=expected_sha,
            value=actual_sha,
        )
        return
    try:
        report = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        add(
            blockers,
            "promoted_leaf_gate_report_unverified",
            label,
            leaf=leaf_id,
            evidence_key=evidence_key,
            path=str(path),
            detail=str(exc),
        )
        return
    if not isinstance(report, dict):
        add(blockers, "promoted_leaf_gate_report_unverified", label, leaf=leaf_id, evidence_key=evidence_key)
        return
    expected_pairs = {
        "surface": SURFACE_ID,
        "leaf": leaf_id,
        "evidence_kind": evidence_key,
        "status": "promoted",
        "promotion_ready": True,
        "public_sdk_ready": True,
        "runtime_ready": True,
    }
    for key, expected in expected_pairs.items():
        if report.get(key) != expected:
            add(
                blockers,
                "promoted_leaf_gate_report_unverified",
                f"{label}.{key}",
                leaf=leaf_id,
                evidence_key=evidence_key,
                expected=expected,
                value=report.get(key),
            )
    if not isinstance(report.get("schema"), str) or not report["schema"].startswith("obelisk."):
        add(blockers, "promoted_leaf_gate_report_unverified", f"{label}.schema", leaf=leaf_id, evidence_key=evidence_key)
    if evidence_has_non_promotional_schema_marker(report):
        add(
            blockers,
            "promoted_leaf_gate_report_non_promotional_schema",
            f"{label}.schema",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
    artifact_identity = report.get("artifact_identity")
    if not isinstance(artifact_identity, dict) or not isinstance(artifact_identity.get("sha256"), str):
        add(
            blockers,
            "promoted_leaf_gate_report_unverified",
            f"{label}.artifact_identity",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )
    if evidence_key == "second_source_evidence" and not isinstance(report.get("second_source_provenance"), dict):
        add(
            blockers,
            "promoted_leaf_second_source_provenance_missing",
            f"{label}.second_source_provenance",
            leaf=leaf_id,
            evidence_key=evidence_key,
        )


def validate_promoted_leaf_evidence(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    *,
    manifest_dir: Path,
) -> bool:
    all_promoted = bool(leaves) and all(leaf.get("status") == "promoted" for leaf in leaves.values())
    any_promoted = any(leaf.get("status") == "promoted" for leaf in leaves.values())
    if any_promoted and not all_promoted:
        promoted_leaves = sorted(leaf_id for leaf_id, leaf in leaves.items() if leaf.get("status") == "promoted")
        add(
            blockers,
            "side_lane_leaf_promotion_not_allowed",
            "$.leaf_decision_units",
            promoted_leaves=promoted_leaves,
        )
        add(blockers, "partial_leaf_promotion_not_allowed", "$.leaf_decision_units")
        return False
    if not all_promoted:
        return False
    add(
        blockers,
        "side_lane_leaf_promotion_not_allowed",
        "$.leaf_decision_units",
        promoted_leaves=list(REQUIRED_LEAVES),
    )
    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves[leaf_id]
        evidence = evidence_for_leaf(surface, leaf)
        label = f"$.leaf_decision_units[{leaf_id}].evidence"
        if not evidence:
            add(blockers, "promoted_leaf_evidence_missing", label, leaf=leaf_id)
            continue
        for key in ("promotion_status", "public_sdk_ready", "promotion_ready", "runtime_ready"):
            expected: Any = "promoted" if key == "promotion_status" else True
            if evidence.get(key) != expected:
                add(blockers, f"promoted_leaf_{key}_mismatch", f"{label}.{key}", leaf=leaf_id)
        for key in PROMOTED_LEAF_EVIDENCE_KEYS:
            values = evidence.get(key)
            if not isinstance(values, list) or not values:
                add(blockers, "promoted_leaf_real_evidence_missing", f"{label}.{key}", leaf=leaf_id)
                continue
            for index, entry in enumerate(values):
                validate_promoted_leaf_gate_report(
                    entry,
                    evidence_key=key,
                    leaf_id=leaf_id,
                    label=f"{label}.{key}[{index}]",
                    manifest_dir=manifest_dir,
                    blockers=blockers,
                )
        joined = "\n".join(flattened_strings(evidence))
        if NEGATIVE_EVIDENCE_RE.search(joined):
            add(blockers, "promoted_leaf_evidence_contains_candidate_only_markers", label, leaf=leaf_id)
    return False


def normalize_candidate_alias_key(key: Any) -> str:
    if not isinstance(key, str):
        return str(key)
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def candidate_alias_true_overclaim(normalized_key: str) -> bool:
    if normalized_key in MISSION_CANDIDATE_FORBIDDEN_TRUE_KEYS:
        return True
    if normalized_key in {
        "callback",
        "callbacks",
        "live_ops",
        "mutation",
        "public_abi",
        "public_c_abi",
        "public_module",
        "resource_handle",
        "runtime",
        "runtime_capture",
        "sdk",
        "v1",
    }:
        return True
    tokens = {token for token in normalized_key.split("_") if token}
    token_text = f"_{normalized_key}_"
    if token_text.startswith("_counts_toward_") and tokens & {"sdk", "v1", "completion", "claim"}:
        return True
    if tokens & {"counts", "contributes", "contribution"} and tokens & {"sdk", "v1", "completion", "claim"}:
        return True
    state_tokens = {
        "accounted",
        "allowed",
        "available",
        "allowed",
        "complete",
        "completion",
        "contributes",
        "contribution",
        "enabled",
        "promoted",
        "promotion",
        "published",
        "ready",
        "supported",
        "unblocked",
        "unlocked",
    }
    sensitive_tokens = {
        "abi",
        "api",
        "callback",
        "capability",
        "claim",
        "complete",
        "descriptor",
        "dispatcher",
        "handle",
        "hook",
        "identity",
        "lookup",
        "mutation",
        "p0",
        "public",
        "release",
        "resource",
        "runtime",
        "sdk",
        "source",
        "stable",
        "support",
        "tier",
        "v1",
        "wiring",
    }
    sensitive_phrases = (
        "complete_sdk_claim",
        "resource_handle",
        "return_override",
        "public_abi",
        "public_c_abi",
        "public_sdk",
        "runtime_observer",
        "runtime_hook",
        "runtime_wiring",
    )
    if any(phrase in normalized_key for phrase in sensitive_phrases):
        return bool(tokens & state_tokens)
    if "promoted" in tokens and (
        "policy" in tokens or tokens & {"mission", "transfer", "dino", "tribe", "buff", "status"}
    ):
        return True
    return bool(tokens & state_tokens and tokens & sensitive_tokens)


def candidate_alias_context(normalized_key: str) -> bool:
    if normalized_key in CONTEXTUAL_CANDIDATE_CONTAINER_KEYS:
        return True
    if candidate_alias_true_overclaim(normalized_key) or candidate_alias_promoted_string_overclaim(normalized_key):
        return True
    tokens = {token for token in normalized_key.split("_") if token}
    sensitive_tokens = {
        "abi",
        "api",
        "callback",
        "capability",
        "claim",
        "complete",
        "completion",
        "descriptor",
        "dispatcher",
        "handle",
        "hook",
        "identity",
        "live",
        "lookup",
        "module",
        "mutation",
        "ops",
        "p0",
        "public",
        "release",
        "resource",
        "runtime",
        "sdk",
        "source",
        "stable",
        "support",
        "tier",
        "v1",
        "wiring",
    }
    return bool(tokens & sensitive_tokens)


def candidate_alias_promoted_string_overclaim(normalized_key: str) -> bool:
    if normalized_key in CANDIDATE_FORBIDDEN_PROMOTED_STRING_KEYS:
        return True
    tokens = {token for token in normalized_key.split("_") if token}
    return bool(
        "status" in tokens
        and (tokens & {"mission", "transfer", "dino", "tribe", "buff", "policy", "runtime", "sdk", "source", "v1"})
    )


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_progress_claim(value: Any) -> bool:
    return positive_numeric_claim(value) or (
        isinstance(value, str) and POSITIVE_PROGRESS_RATIO_RE.fullmatch(value) is not None
    )


def positive_status_claim(value: Any) -> bool:
    if value is True:
        return True
    if positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    return (
        normalized in CANDIDATE_FORBIDDEN_PROMOTED_STRING_VALUES
        or normalized.endswith("_ready")
    )


def progress_or_completion_alias(normalized_key: str) -> bool:
    tokens = {token for token in normalized_key.split("_") if token}
    progress_tokens = {
        "count",
        "counting",
        "counts",
        "progress",
        "contribution",
        "completion",
        "percent",
        "ratio",
        "credit",
        "credits",
    }
    scope_tokens = {"sdk", "v1", "p0", "claim", "public", "runtime", "stable", "complete"}
    return bool(tokens & progress_tokens and tokens & scope_tokens)


def collect_true_ready_overclaims(value: Any, prefix: str = "$", *, claim_context: bool = False) -> list[str]:
    overclaims: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            normalized_key = normalize_candidate_alias_key(key)
            child_context = claim_context or candidate_alias_context(normalized_key)
            if candidate_alias_true_overclaim(normalized_key) and child is True:
                overclaims.append(child_path)
            if (
                child_context
                and (
                    progress_or_completion_alias(normalized_key)
                    or normalized_key
                    in {"progress", "progress_contribution", "claim_progress", "credit", "credits", "claim_credit"}
                )
                and positive_progress_claim(child)
            ):
                overclaims.append(child_path)
            if child_context and normalized_key in CONTEXTUAL_POSITIVE_STATUS_KEYS and positive_status_claim(child):
                overclaims.append(child_path)
            elif (
                candidate_alias_promoted_string_overclaim(normalized_key)
                and isinstance(child, str)
                and child.lower().replace("-", "_").replace(" ", "_") in CANDIDATE_FORBIDDEN_PROMOTED_STRING_VALUES
            ):
                overclaims.append(child_path)
            overclaims.extend(collect_true_ready_overclaims(child, child_path, claim_context=child_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            overclaims.extend(collect_true_ready_overclaims(child, f"{prefix}[{index}]", claim_context=claim_context))
    return overclaims


def normalized_marker_text(*parts: Any) -> str:
    text = " ".join(str(part) for part in parts if isinstance(part, str))
    return re.sub(r"[-_./]+", " ", text)


def collect_candidate_marker_overclaims(
    value: Any,
    prefix: str = "$",
    *,
    marker_context: bool = False,
    parent_key: str = "",
) -> list[tuple[str, str]]:
    overclaims: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = key if isinstance(key, str) else str(key)
            child_path = f"{prefix}.{key_text}"
            child_marker_context = marker_context or bool(CANDIDATE_MARKER_KEY_RE.search(key_text))
            overclaims.extend(
                collect_candidate_marker_overclaims(
                    child,
                    child_path,
                    marker_context=child_marker_context,
                    parent_key=key_text,
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            overclaims.extend(
                collect_candidate_marker_overclaims(
                    child,
                    f"{prefix}[{index}]",
                    marker_context=marker_context,
                    parent_key=parent_key,
                )
            )
    elif marker_context and isinstance(value, str):
        marker_text = normalized_marker_text(parent_key, value)
        if CANDIDATE_MARKER_PROMOTION_RE.search(marker_text) and not CANDIDATE_MARKER_NON_PROMOTION_RE.search(
            marker_text
        ):
            overclaims.append((prefix, value))
    return overclaims


def candidate_leaf_evidence_sources(
    surface: dict[str, Any],
    leaf_id: str,
    leaf: dict[str, Any],
) -> list[tuple[dict[str, Any], str]]:
    sources: list[tuple[dict[str, Any], str]] = []
    evidence = leaf.get("evidence")
    if isinstance(evidence, dict):
        sources.append((evidence, f"$.leaf_decision_units[{leaf_id}].evidence"))
    per_leaf = surface.get("promotion_evidence_by_leaf")
    if isinstance(per_leaf, dict) and isinstance(per_leaf.get(leaf_id), dict):
        sources.append((per_leaf[leaf_id], f"$.promotion_evidence_by_leaf[{leaf_id}]"))
    return sources


def validate_candidate_leaf_evidence(
    surface: dict[str, Any],
    leaf_id: str,
    leaf: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
    if status == "promoted":
        return
    for evidence, label in candidate_leaf_evidence_sources(surface, leaf_id, leaf):
        ready_reason = "mission_leaf_candidate_ready_overclaim" if leaf_id == "mission" else "leaf_candidate_ready_overclaim"
        claim_reason = (
            "mission_leaf_candidate_evidence_forbidden_claim"
            if leaf_id == "mission"
            else "leaf_candidate_evidence_forbidden_claim"
        )
        add_side_lane_source_artifact_issues(
            blockers,
            evidence,
            label=label,
            expected_target_sets=SIDE_LANE_EXPECTED_TARGET_SETS_BY_LEAF.get(leaf_id, ()),
            leaf=leaf_id,
        )
        for field in collect_true_ready_overclaims(evidence, label):
            add(blockers, ready_reason, field, leaf=leaf_id)
        claims = forbidden_claims("\n".join(flattened_strings(evidence)))
        for claim in claims:
            add(
                blockers,
                claim_reason,
                label,
                leaf=leaf_id,
                claim=claim,
            )
        ready_claims = candidate_ready_claims("\n".join(flattened_strings(evidence)))
        for claim in ready_claims:
            add(
                blockers,
                ready_reason,
                label,
                leaf=leaf_id,
                claim=claim,
            )
        for field, value in collect_candidate_marker_overclaims(evidence, label):
            add(
                blockers,
                "leaf_candidate_marker_overclaim",
                field,
                leaf=leaf_id,
                value=value,
            )


def validate_candidate_surface_evidence(surface: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if surface.get("status") == "promoted":
        return
    evidence = surface.get("evidence")
    if not isinstance(evidence, dict):
        return
    label = "$.surface.evidence"
    add_side_lane_source_artifact_issues(
        blockers,
        evidence,
        label=label,
        expected_target_sets=SIDE_LANE_SURFACE_EXPECTED_TARGET_SETS,
    )
    for field in collect_true_ready_overclaims(evidence, label):
        add(blockers, "surface_candidate_ready_overclaim", field)
    for claim in forbidden_claims("\n".join(flattened_strings(evidence))):
        add(blockers, "surface_candidate_evidence_forbidden_claim", label, claim=claim)
    for claim in candidate_ready_claims("\n".join(flattened_strings(evidence))):
        add(blockers, "surface_candidate_ready_overclaim", label, claim=claim)
    for field, value in collect_candidate_marker_overclaims(evidence, label):
        add(blockers, "surface_candidate_marker_overclaim", field, value=value)


def validate_candidate_leaf_metadata(
    leaf_id: str,
    leaf: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
    if status == "promoted":
        return
    label = f"$.leaf_decision_units[{leaf_id}]"
    ready_reason = "mission_leaf_candidate_ready_overclaim" if leaf_id == "mission" else "leaf_candidate_ready_overclaim"
    claim_reason = (
        "mission_leaf_candidate_metadata_forbidden_claim"
        if leaf_id == "mission"
        else "leaf_candidate_metadata_forbidden_claim"
    )
    for field in collect_true_ready_overclaims(leaf, label):
        add(blockers, ready_reason, field, leaf=leaf_id)
    for claim in forbidden_claims("\n".join(flattened_strings(leaf))):
        add(blockers, claim_reason, label, leaf=leaf_id, claim=claim)
    for claim in candidate_ready_claims("\n".join(flattened_strings(leaf))):
        add(blockers, ready_reason, label, leaf=leaf_id, claim=claim)
    for field, value in collect_candidate_marker_overclaims(leaf, label):
        add(blockers, "leaf_candidate_metadata_marker_overclaim", field, leaf=leaf_id, value=value)


def non_counting_allowed_v1_outcome(leaf: dict[str, Any], accounted_by: str | None) -> str | None:
    if accounted_by == "promoted_leaf_evidence":
        value = leaf.get("allowed_v1_outcome")
        return value if isinstance(value, str) else None
    if accounted_by in {"manifest_leaf_exclusion", "release_statement_leaf_exclusion"}:
        return "explicitly excluded by name from v1"
    return "not counted for v1 by this candidate-only checker; requires explicit leaf exclusion"


def checker_blocker_reasons(report: dict[str, Any]) -> list[str]:
    blockers = report.get("blockers")
    if not isinstance(blockers, list):
        return []
    reasons: list[str] = []
    for blocker in blockers:
        if isinstance(blocker, dict) and isinstance(blocker.get("reason"), str):
            reasons.append(blocker["reason"])
        else:
            reasons.append(str(blocker))
    return reasons


def focused_gate_status(report: dict[str, Any], key: str) -> dict[str, Any]:
    gate = report.get(key)
    if not isinstance(gate, dict):
        return {"gate_status_observed": None, "returncode": None, "blocker_reasons": []}
    return {
        "gate_status_observed": gate.get("status"),
        "returncode": gate.get("returncode"),
        "blocker_reasons": string_list(gate.get("blocker_reasons")),
    }


def validate_optional_focused_non_counting_fields(
    report: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    label: str,
    reason_prefix: str,
) -> None:
    for key in OPTIONAL_FOCUSED_REPORT_FALSE_KEYS:
        if key in report and report.get(key) is not False:
            add(blockers, f"{reason_prefix}_optional_public_or_completion_claim", f"{label}.{key}", key=key)
    for key in OPTIONAL_FOCUSED_REPORT_ZERO_FIELDS:
        if key in report and report.get(key) != 0:
            add(blockers, f"{reason_prefix}_optional_progress_contribution_nonzero", f"{label}.{key}", key=key)


def required_false_fields_clear(report: dict[str, Any], keys: tuple[str, ...] | set[str]) -> bool:
    return all(report.get(key) is False for key in keys)


def optional_ready_fields_clear(report: dict[str, Any], keys: tuple[str, ...] | set[str]) -> bool:
    return all(not positive_status_claim(report.get(key)) for key in keys if key in report)


def required_zero_fields_clear(report: dict[str, Any], keys: tuple[str, ...] | set[str]) -> bool:
    return all(report.get(key) == 0 for key in keys)


def optional_zero_fields_clear(report: dict[str, Any], keys: tuple[str, ...] | set[str]) -> bool:
    return all(not positive_numeric_claim(report.get(key)) for key in keys if key in report)


def optional_focused_non_counting_fields_clear(report: dict[str, Any]) -> bool:
    return optional_ready_fields_clear(report, set(OPTIONAL_FOCUSED_REPORT_FALSE_KEYS)) and optional_zero_fields_clear(
        report,
        set(OPTIONAL_FOCUSED_REPORT_ZERO_FIELDS),
    )


def validate_mission_copied_bool_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.mission_leaf_blocker_accounting.focused_checker_report"
    if report.get("schema") != mission_copied_bool_readiness.REPORT_SCHEMA:
        add(blockers, "mission_copied_bool_checker_schema_mismatch", f"{label}.schema")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "mission_copied_bool_checker_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("ready", "consume_only", "internal_reusable_evidence_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "mission_copied_bool_checker_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "mission_copied_bool_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in MISSION_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "mission_copied_bool_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in MISSION_ZERO_FIELDS:
        if report.get(key) != 0:
            add(blockers, "mission_copied_bool_progress_contribution_nonzero", f"{label}.{key}", key=key)
    validate_optional_focused_non_counting_fields(
        report,
        blockers,
        label=label,
        reason_prefix="mission_copied_bool",
    )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "mission_copied_bool_summary_missing", f"{label}.summary")
        return
    copied_targets = string_list(summary.get("copied_targets"))
    missing_targets = sorted(set(MISSION_COPIED_TARGETS) - set(copied_targets))
    if missing_targets:
        add(
            blockers,
            "mission_copied_bool_targets_missing",
            f"{label}.summary.copied_targets",
            missing=missing_targets,
        )
    copied_fields = string_list(summary.get("copied_fields"))
    missing_fields = sorted(set(MISSION_COPIED_BOOL_FIELDS) - set(copied_fields))
    if missing_fields:
        add(
            blockers,
            "mission_copied_bool_fields_missing",
            f"{label}.summary.copied_fields",
            missing=missing_fields,
        )
    redacted_fields = string_list(summary.get("redacted_fields"))
    missing_redactions = sorted(set(MISSION_REDACTED_RECOGNITION_FIELDS) - set(redacted_fields))
    if missing_redactions:
        add(
            blockers,
            "mission_copied_bool_redactions_missing",
            f"{label}.summary.redacted_fields",
            missing=missing_redactions,
        )
    if summary.get("get_player_usable_items_recognition_only") is not True:
        add(
            blockers,
            "mission_copied_bool_recognition_only_missing",
            f"{label}.summary.get_player_usable_items_recognition_only",
        )


def validate_transfer_baccept_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.transfer_leaf_blocker_accounting.focused_checker_report"
    if report.get("schema") != transfer_baccept_readiness.REPORT_SCHEMA:
        add(blockers, "transfer_baccept_checker_schema_mismatch", f"{label}.schema")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "transfer_baccept_checker_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("ready", "consume_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "transfer_baccept_checker_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "transfer_baccept_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in TRANSFER_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "transfer_baccept_public_or_runtime_claim", f"{label}.{key}", key=key)
    validate_optional_focused_non_counting_fields(
        report,
        blockers,
        label=label,
        reason_prefix="transfer_baccept",
    )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "transfer_baccept_summary_missing", f"{label}.summary")
        return
    copied_targets = string_list(summary.get("copied_targets"))
    if set(copied_targets) != {transfer_baccept_readiness.EXPECTED_COPIED_TARGET}:
        add(
            blockers,
            "transfer_baccept_copied_target_mismatch",
            f"{label}.summary.copied_targets",
            expected=[transfer_baccept_readiness.EXPECTED_COPIED_TARGET],
            value=copied_targets,
        )
    copied_fields = string_list(summary.get("copied_fields"))
    if set(copied_fields) != {transfer_baccept_readiness.EXPECTED_COPIED_FIELD}:
        add(
            blockers,
            "transfer_baccept_copied_field_mismatch",
            f"{label}.summary.copied_fields",
            expected=[transfer_baccept_readiness.EXPECTED_COPIED_FIELD],
            value=copied_fields,
        )
    input_targets = string_list(summary.get("input_targets"))
    missing_input_targets = sorted(set(transfer_baccept_readiness.EXPECTED_INPUT_TARGETS) - set(input_targets))
    if missing_input_targets:
        add(
            blockers,
            "transfer_baccept_input_targets_missing",
            f"{label}.summary.input_targets",
            missing=missing_input_targets,
        )
    forbidden_fields = string_list(summary.get("forbidden_fields"))
    missing_forbidden = sorted(set(transfer_baccept_readiness.EXPECTED_FORBIDDEN_FIELDS) - set(forbidden_fields))
    if missing_forbidden:
        add(
            blockers,
            "transfer_baccept_forbidden_fields_missing",
            f"{label}.summary.forbidden_fields",
            missing=missing_forbidden,
        )


def validate_transfer_scriptstruct_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.transfer_scriptstruct_leaf_blocker_accounting.focused_checker_report"
    if report.get("schema") != transfer_scriptstruct_readiness.REPORT_SCHEMA:
        add(blockers, "transfer_scriptstruct_checker_schema_mismatch", f"{label}.schema")
    for key in (
        "ready",
        "accepted_for_candidate_review",
        "accepted_for_internal_planning",
        "candidate_only",
        "candidate_only_mode",
        "consume_only",
    ):
        if report.get(key) is not True:
            add(blockers, "transfer_scriptstruct_checker_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "transfer_scriptstruct_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in TRANSFER_SCRIPTSTRUCT_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "transfer_scriptstruct_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in TRANSFER_SCRIPTSTRUCT_ZERO_FIELDS:
        if report.get(key) != 0:
            add(blockers, "transfer_scriptstruct_progress_contribution_nonzero", f"{label}.{key}", key=key)
    validate_optional_focused_non_counting_fields(
        report,
        blockers,
        label=label,
        reason_prefix="transfer_scriptstruct",
    )
    if report.get("explicitly_excluded") != transfer_scriptstruct_readiness.EXPLICITLY_EXCLUDED:
        add(blockers, "transfer_scriptstruct_explicit_exclusions_mismatch", f"{label}.explicitly_excluded")
    if report.get("item_net_info_excluded") is not True:
        add(blockers, "transfer_scriptstruct_item_net_info_not_excluded", f"{label}.item_net_info_excluded")

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "transfer_scriptstruct_summary_missing", f"{label}.summary")
        return
    if summary.get("target_set") != transfer_scriptstruct_readiness.TARGET_SET:
        add(blockers, "transfer_scriptstruct_target_set_mismatch", f"{label}.summary.target_set")
    targets = string_list(summary.get("targets"))
    if targets != transfer_scriptstruct_readiness.EXPECTED_TARGETS:
        add(
            blockers,
            "transfer_scriptstruct_targets_mismatch",
            f"{label}.summary.targets",
            expected=transfer_scriptstruct_readiness.EXPECTED_TARGETS,
            value=targets,
        )
    expected_signature_count = len(transfer_scriptstruct_readiness.EXPECTED_TARGETS)
    for key in ("snapshot_count", "signature_count"):
        if summary.get(key) != expected_signature_count:
            add(
                blockers,
                "transfer_scriptstruct_count_mismatch",
                f"{label}.summary.{key}",
                key=key,
                expected=expected_signature_count,
                value=summary.get(key),
            )
    expected_field_count = sum(
        int(spec["property_count"]) for spec in transfer_scriptstruct_readiness.EXPECTED_SIGNATURES.values()
    )
    for key in ("field_count_total", "redacted_payload_field_count"):
        if summary.get(key) != expected_field_count:
            add(
                blockers,
                "transfer_scriptstruct_field_count_mismatch",
                f"{label}.summary.{key}",
                key=key,
                expected=expected_field_count,
                value=summary.get(key),
            )
    if summary.get("copied_scalar_count_total") != 0:
        add(
            blockers,
            "transfer_scriptstruct_copied_scalar_count_nonzero",
            f"{label}.summary.copied_scalar_count_total",
            value=summary.get("copied_scalar_count_total"),
        )
    expected_bool_tail_fields = sorted(
        f"{target}.{field}"
        for target, spec in transfer_scriptstruct_readiness.EXPECTED_SIGNATURES.items()
        for field in spec["bool_tail_fields"]
    )
    bool_tail_fields = string_list(summary.get("bool_tail_fields"))
    if bool_tail_fields != expected_bool_tail_fields:
        add(
            blockers,
            "transfer_scriptstruct_bool_tail_fields_mismatch",
            f"{label}.summary.bool_tail_fields",
            expected=expected_bool_tail_fields,
            value=bool_tail_fields,
        )
    not_promoted = set(string_list(summary.get("not_promoted_surfaces")))
    missing_not_promoted = sorted(transfer_scriptstruct_readiness.REQUIRED_NOT_PROMOTED_SURFACES - not_promoted)
    if missing_not_promoted:
        add(
            blockers,
            "transfer_scriptstruct_not_promoted_surfaces_missing",
            f"{label}.summary.not_promoted_surfaces",
            missing=missing_not_promoted,
        )
    if summary.get("explicitly_excluded") != transfer_scriptstruct_readiness.EXPLICITLY_EXCLUDED:
        add(blockers, "transfer_scriptstruct_summary_exclusions_mismatch", f"{label}.summary.explicitly_excluded")
    if summary.get("item_net_info_excluded") is not True:
        add(blockers, "transfer_scriptstruct_summary_item_net_info_not_excluded", f"{label}.summary.item_net_info_excluded")


def validate_dino_scalar_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.dino_leaf_blocker_accounting.focused_checker_report"
    if report.get("schema") != dino_scalar_readiness.REPORT_SCHEMA:
        add(blockers, "dino_scalar_checker_schema_mismatch", f"{label}.schema")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "dino_scalar_checker_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("ready", "offline_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "dino_scalar_checker_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "dino_scalar_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in DINO_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "dino_scalar_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in DINO_ZERO_FIELDS:
        if report.get(key) != 0:
            add(blockers, "dino_scalar_progress_contribution_nonzero", f"{label}.{key}", key=key)
    validate_optional_focused_non_counting_fields(
        report,
        blockers,
        label=label,
        reason_prefix="dino_scalar",
    )
    if report.get("scalar_only_ready") is not True:
        add(blockers, "dino_scalar_only_not_ready", f"{label}.scalar_only_ready")
    if report.get("precall_scalar_ready") is not True:
        add(blockers, "dino_precall_scalar_not_ready", f"{label}.precall_scalar_ready")
    if report.get("postcall_return_ready") is not False:
        add(blockers, "dino_postcall_return_overclaim", f"{label}.postcall_return_ready")

    target_set = report.get("target_set")
    if not isinstance(target_set, dict):
        add(blockers, "dino_scalar_target_set_missing", f"{label}.target_set")
    else:
        if target_set.get("target_set") != dino_scalar_readiness.TARGET_SET:
            add(blockers, "dino_scalar_target_set_mismatch", f"{label}.target_set.target_set")
        input_targets = set(string_list(target_set.get("input_targets")))
        missing_input_targets = sorted(dino_scalar_readiness.EXPECTED_INPUT_TARGETS - input_targets)
        if missing_input_targets:
            add(
                blockers,
                "dino_scalar_input_targets_missing",
                f"{label}.target_set.input_targets",
                missing=missing_input_targets,
            )
        if target_set.get("missing_targets") != []:
            add(blockers, "dino_scalar_target_set_has_missing_targets", f"{label}.target_set.missing_targets")

    source_isolation = report.get("source_isolation")
    if not isinstance(source_isolation, dict):
        add(blockers, "dino_scalar_source_isolation_missing", f"{label}.source_isolation")
    elif source_isolation.get("status") != "isolated":
        add(
            blockers,
            "dino_scalar_source_isolation_not_isolated",
            f"{label}.source_isolation.status",
            value=source_isolation.get("status"),
        )

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "dino_scalar_summary_missing", f"{label}.summary")
        return
    expected_summary_sets = (
        ("layout_scalar_fields", dino_scalar_readiness.EXPECTED_LAYOUT_SCALAR_FIELDS),
        ("precall_copied_fields", dino_scalar_readiness.EXPECTED_COPIED_FIELDS),
        ("deferred_return_fields", dino_scalar_readiness.EXPECTED_EXCLUDED_FIELDS),
        ("redacted_fields", dino_scalar_readiness.EXPECTED_REDACTED_FIELDS),
        ("descriptors", dino_scalar_readiness.EXPECTED_DESCRIPTORS),
    )
    for key, expected in expected_summary_sets:
        values = set(string_list(summary.get(key)))
        if values != expected:
            add(
                blockers,
                "dino_scalar_summary_field_mismatch",
                f"{label}.summary.{key}",
                key=key,
                missing=sorted(expected - values),
                unexpected=sorted(values - expected),
            )
    if summary.get("pre_call_only") is not True:
        add(blockers, "dino_scalar_pre_call_only_missing", f"{label}.summary.pre_call_only")
    if summary.get("return_values_excluded") is not True:
        add(blockers, "dino_scalar_return_values_not_excluded", f"{label}.summary.return_values_excluded")


def build_mission_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    mission_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("mission", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(MISSION_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    mission_gap = gaps.get("mission") if isinstance(gaps, dict) and isinstance(gaps.get("mission"), dict) else {}
    summary = mission_report.get("summary") if isinstance(mission_report.get("summary"), dict) else {}
    copied_targets = string_list(summary.get("copied_targets") if isinstance(summary, dict) else None) or list(
        MISSION_COPIED_TARGETS
    )
    copied_fields = string_list(summary.get("copied_fields") if isinstance(summary, dict) else None) or list(
        MISSION_COPIED_BOOL_FIELDS
    )
    redacted_fields = string_list(summary.get("redacted_fields") if isinstance(summary, dict) else None) or list(
        MISSION_REDACTED_RECOGNITION_FIELDS
    )
    checker_ready = (
        mission_report.get("accepted_for_internal_planning") is True
        and not mission_report.get("blockers")
        and required_false_fields_clear(mission_report, set(MISSION_PUBLIC_FALSE_KEYS))
        and required_zero_fields_clear(mission_report, set(MISSION_ZERO_FIELDS))
        and optional_focused_non_counting_fields_clear(mission_report)
    )

    return {
        "schema": MISSION_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "mission",
        "lane": "mission_copied_bool_policy_slice",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
        ),
        "candidate_only": True,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": bool(mission_gap.get("v1_accounted")),
        "focused_checker_v1_accounted": False,
        "mission_sdk_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "v1_completion": False,
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        "focused_checker": "scripts/check_mission_copied_bool_readiness.py",
        "focused_checker_report": {
            "schema": mission_report.get("schema"),
            "checker_status_observed": mission_report.get("status"),
            "checker_ready_observed": bool(mission_report.get("ready")),
            "accepted_for_internal_planning": bool(mission_report.get("accepted_for_internal_planning")),
            "consume_only": bool(mission_report.get("consume_only")),
            "not_artifact_gate": bool(mission_report.get("not_artifact_gate")),
            "blocker_reasons": checker_blocker_reasons(mission_report),
            "consume_gate": focused_gate_status(mission_report, "consume_gate"),
            "promote_gate": focused_gate_status(mission_report, "promote_gate"),
        },
        "input_target_set": "mission-compact-intake",
        "output_target_set": "mission-copied-bool-policy-slice",
        "required_evidence": list(MISSION_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "copied_bool_boundary": {
            "checker_schema": mission_report.get("schema"),
            "checker_ready": checker_ready,
            "copied_targets": copied_targets if checker_ready else [],
            "copied_bool_fields": copied_fields if checker_ready else [],
            "copied_bool_count": len(copied_fields) if checker_ready else 0,
        },
        "redaction_boundary": {
            "recognition_only_targets": list(MISSION_RECOGNITION_ONLY_TARGETS),
            "redacted_recognition_fields": redacted_fields,
            "forbidden_promotions": [
                "mission identity",
                "player/controller/character identity",
                "item arrays",
                "object pointers",
                "lookup",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(mission_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
            else "blocked_accounting"
        ),
        "blocker_parity": {
            "focused_checker_blocker_reasons": checker_blocker_reasons(mission_report),
            "umbrella_blocker_reason": (
                None if checker_ready else "mission_copied_bool_checker_blocked_or_not_ready"
            ),
        },
        "non_claims": [
            "mission leaf accounting is exactly consume-only internal reusable evidence",
            "mission leaf accounting does not promote a public Mission SDK, ABI, callback, or descriptor",
            "mission leaf accounting does not promote runtime hooks, dispatcher wiring, mutation, return override, identity, lookup, arrays, or ResourceHandle",
            "mission leaf accounting does not expand beyond the frozen copied-bool policy slice",
            "mission copied-bool readiness does not count toward P0 dependency-chain or complete-SDK accounting",
        ],
    }


def build_transfer_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    transfer_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("transfer", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(TRANSFER_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    transfer_gap = (
        gaps.get("transfer")
        if isinstance(gaps, dict) and isinstance(gaps.get("transfer"), dict)
        else {}
    )
    summary = transfer_report.get("summary") if isinstance(transfer_report.get("summary"), dict) else {}
    copied_targets = string_list(summary.get("copied_targets") if isinstance(summary, dict) else None)
    copied_fields = string_list(summary.get("copied_fields") if isinstance(summary, dict) else None)
    input_targets = string_list(summary.get("input_targets") if isinstance(summary, dict) else None)
    forbidden_fields = string_list(summary.get("forbidden_fields") if isinstance(summary, dict) else None)
    checker_ready = (
        transfer_report.get("accepted_for_internal_planning") is True
        and not transfer_report.get("blockers")
        and required_false_fields_clear(transfer_report, set(TRANSFER_PUBLIC_FALSE_KEYS))
        and required_zero_fields_clear(transfer_report, set(TRANSFER_ZERO_FIELDS))
        and optional_focused_non_counting_fields_clear(transfer_report)
    )

    return {
        "schema": TRANSFER_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "transfer",
        "lane": "transfer_baccept_only_policy_slice",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
        ),
        "candidate_only": True,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": bool(transfer_gap.get("v1_accounted")),
        "focused_checker_v1_accounted": False,
        "transfer_sdk_ready": False,
        "public_transfer_sdk_ready": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "public_header_ready": False,
        "public_contract_ready": False,
        "public_metadata_helpers_ready": False,
        "runtime_hook_ready": False,
        "runtime_hook_wiring_ready": False,
        "runtime_ready": False,
        "runtime_validated": False,
        "runtime_validation_ready": False,
        "dispatcher_ready": False,
        "dispatcher_wiring_ready": False,
        "server_validation_ready": False,
        "identity_ready": False,
        "player_identity_public_contract_ready": False,
        "ownership_ready": False,
        "cross_map_state_public_contract_ready": False,
        "downloaded_character_public_contract_ready": False,
        "dino_payload_public_contract_ready": False,
        "transfer_payload_decoding_ready": False,
        "transfer_payload_public_contract_ready": False,
        "resource_handle_public_contract_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "v1_completion": False,
        "v1_completion_evidence": False,
        "v1_ready": False,
        "v1_release_ready": False,
        **{key: 0 for key in TRANSFER_ZERO_FIELDS},
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        "focused_checker": "scripts/check_transfer_baccept_readiness.py",
        "focused_checker_report": {
            "schema": transfer_report.get("schema"),
            "checker_status_observed": transfer_report.get("status"),
            "checker_ready_observed": bool(transfer_report.get("ready")),
            "accepted_for_internal_planning": bool(transfer_report.get("accepted_for_internal_planning")),
            "consume_only": bool(transfer_report.get("consume_only")),
            "not_artifact_gate": bool(transfer_report.get("not_artifact_gate")),
            "blocker_reasons": checker_blocker_reasons(transfer_report),
            "consume_gate": focused_gate_status(transfer_report, "consume_gate"),
            "promote_gate": focused_gate_status(transfer_report, "promote_gate"),
        },
        "input_target_set": transfer_baccept_readiness.INPUT_TARGET_SET,
        "output_target_set": transfer_baccept_readiness.OUTPUT_TARGET_SET,
        "required_evidence": list(TRANSFER_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "copied_bool_boundary": {
            "checker_schema": transfer_report.get("schema"),
            "checker_ready": checker_ready,
            "input_targets": input_targets if checker_ready else [],
            "copied_targets": copied_targets if checker_ready else [],
            "copied_bool_fields": copied_fields if checker_ready else [],
            "copied_bool_count": len(copied_fields) if checker_ready else 0,
        },
        "redaction_boundary": {
            "forbidden_fields": forbidden_fields,
            "required_forbidden_fields": sorted(transfer_baccept_readiness.EXPECTED_FORBIDDEN_FIELDS),
            "forbidden_promotions": [
                "public Transfer SDK",
                "transfer payload decoding or ownership",
                "downloaded character payload contract",
                "dino payload contract",
                "player identity",
                "ownership lookup",
                "cross-map state correlation",
                "teleport/spawn authority",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(transfer_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
            else "blocked_accounting"
        ),
        "blocker_parity": {
            "focused_checker_blocker_reasons": checker_blocker_reasons(transfer_report),
            "umbrella_blocker_reason": None if checker_ready else "transfer_baccept_checker_blocked_or_not_ready",
        },
        "non_claims": [
            "transfer leaf accounting is exactly consume-only internal reusable evidence",
            "transfer leaf accounting does not promote a public Transfer SDK, ABI, callback, descriptor, or v1 completion",
            "transfer leaf accounting does not promote runtime hooks, dispatcher wiring, identity, ownership lookup, payload decoding, cross-map correlation, teleport/spawn, mutation, return override, or ResourceHandle",
            "transfer bAccept readiness does not count toward P0 dependency-chain or complete-SDK accounting",
        ],
    }


def build_transfer_scriptstruct_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    scriptstruct_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("transfer", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    transfer_gap = (
        gaps.get("transfer")
        if isinstance(gaps, dict) and isinstance(gaps.get("transfer"), dict)
        else {}
    )
    summary = scriptstruct_report.get("summary") if isinstance(scriptstruct_report.get("summary"), dict) else {}
    targets = string_list(summary.get("targets") if isinstance(summary, dict) else None)
    bool_tail_fields = string_list(summary.get("bool_tail_fields") if isinstance(summary, dict) else None)
    not_promoted_surfaces = string_list(summary.get("not_promoted_surfaces") if isinstance(summary, dict) else None)
    expected_bool_tail_fields = sorted(
        f"{target}.{field}"
        for target, spec in transfer_scriptstruct_readiness.EXPECTED_SIGNATURES.items()
        for field in spec["bool_tail_fields"]
    )
    checker_ready = (
        scriptstruct_report.get("accepted_for_internal_planning") is True
        and not scriptstruct_report.get("blockers")
        and required_false_fields_clear(scriptstruct_report, set(TRANSFER_SCRIPTSTRUCT_PUBLIC_FALSE_KEYS))
        and required_zero_fields_clear(scriptstruct_report, set(TRANSFER_SCRIPTSTRUCT_ZERO_FIELDS))
        and optional_focused_non_counting_fields_clear(scriptstruct_report)
        and summary.get("target_set") == transfer_scriptstruct_readiness.TARGET_SET
        and targets == transfer_scriptstruct_readiness.EXPECTED_TARGETS
        and bool_tail_fields == expected_bool_tail_fields
        and summary.get("copied_scalar_count_total") == 0
    )

    return {
        "schema": TRANSFER_SCRIPTSTRUCT_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "transfer",
        "lane": "transfer_scriptstruct_payload_layout_candidate",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": leaf.get("status") == "planning" and checker_ready,
        "candidate_only": True,
        "consume_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": False,
        "focused_checker_v1_accounted": False,
        "release_statement_or_manifest_exclusion_accounted": bool(transfer_gap.get("v1_accounted")),
        "stable_claim_allowed": False,
        "stable_sdk_ready": False,
        "v1_completion": False,
        "v1_completion_ready": False,
        "v1_completion_progress_contribution": 0,
        **{key: False for key in TRANSFER_SCRIPTSTRUCT_PUBLIC_FALSE_KEYS},
        **{key: 0 for key in TRANSFER_SCRIPTSTRUCT_ZERO_FIELDS},
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        "focused_checker": "scripts/check_transfer_scriptstruct_readiness.py",
        "focused_checker_report": {
            "schema": scriptstruct_report.get("schema"),
            "checker_status_observed": scriptstruct_report.get("status"),
            "checker_ready_observed": bool(scriptstruct_report.get("ready")),
            "accepted_for_candidate_review": bool(scriptstruct_report.get("accepted_for_candidate_review")),
            "accepted_for_internal_planning": bool(scriptstruct_report.get("accepted_for_internal_planning")),
            "candidate_only": bool(scriptstruct_report.get("candidate_only")),
            "consume_only": bool(scriptstruct_report.get("consume_only")),
            "blocker_reasons": checker_blocker_reasons(scriptstruct_report),
        },
        "input_target_set": transfer_scriptstruct_readiness.TARGET_SET,
        "required_evidence": [transfer_scriptstruct_readiness.TARGET_SET],
        "current_evidence": current_evidence,
        "missing_required_evidence": [],
        "scriptstruct_boundary": {
            "checker_schema": scriptstruct_report.get("schema"),
            "checker_ready": checker_ready,
            "target_set": summary.get("target_set") if checker_ready and isinstance(summary, dict) else None,
            "targets": targets if checker_ready else [],
            "snapshot_count": summary.get("snapshot_count") if checker_ready and isinstance(summary, dict) else 0,
            "signature_count": summary.get("signature_count") if checker_ready and isinstance(summary, dict) else 0,
            "field_count_total": summary.get("field_count_total") if checker_ready and isinstance(summary, dict) else 0,
            "redacted_payload_field_count": (
                summary.get("redacted_payload_field_count") if checker_ready and isinstance(summary, dict) else 0
            ),
            "copied_scalar_count_total": (
                summary.get("copied_scalar_count_total") if checker_ready and isinstance(summary, dict) else 0
            ),
            "bool_tail_fields": bool_tail_fields if checker_ready else [],
            "bool_tail_field_count": len(bool_tail_fields) if checker_ready else 0,
            "payload_decoding_ready": False,
        },
        "redaction_boundary": {
            "redacted_payload_field_count": (
                summary.get("redacted_payload_field_count") if checker_ready and isinstance(summary, dict) else 0
            ),
            "explicitly_excluded": transfer_scriptstruct_readiness.EXPLICITLY_EXCLUDED,
            "item_net_info_excluded": bool(scriptstruct_report.get("item_net_info_excluded")),
            "not_promoted_surfaces": not_promoted_surfaces if checker_ready else [],
            "forbidden_promotions": [
                "public ScriptStruct SDK",
                "public Transfer SDK",
                "transfer payload decoding",
                "downloaded character payload contract",
                "dino payload contract",
                "ItemNetInfo exposure",
                "cross-map state correlation",
                "object identity",
                "raw UE params",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(transfer_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if leaf.get("status") == "planning" and checker_ready
            else "blocked_accounting"
        ),
        "blocker_parity": {
            "focused_checker_blocker_reasons": checker_blocker_reasons(scriptstruct_report),
            "umbrella_blocker_reason": None if checker_ready else "transfer_scriptstruct_checker_blocked_or_not_ready",
        },
        "non_claims": [
            "transfer ScriptStruct accounting is candidate-only internal layout evidence",
            "transfer ScriptStruct readiness does not promote public ScriptStruct or Transfer SDK callbacks",
            "transfer ScriptStruct readiness does not decode transfer payloads, ItemNetInfo, raw UE params, cross-map state, object identity, mutation, return override, or ResourceHandle",
            "transfer ScriptStruct readiness does not count toward v1, P0 dependency-chain, runtime, stable, or complete-SDK accounting",
        ],
    }


def build_dino_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    dino_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("dino_policy", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(DINO_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    dino_gap = (
        gaps.get("dino_policy")
        if isinstance(gaps, dict) and isinstance(gaps.get("dino_policy"), dict)
        else {}
    )
    summary = dino_report.get("summary") if isinstance(dino_report.get("summary"), dict) else {}
    target_set = dino_report.get("target_set") if isinstance(dino_report.get("target_set"), dict) else {}
    source_isolation = dino_report.get("source_isolation") if isinstance(dino_report.get("source_isolation"), dict) else {}
    precall_copied_fields = string_list(summary.get("precall_copied_fields") if isinstance(summary, dict) else None)
    deferred_return_fields = string_list(summary.get("deferred_return_fields") if isinstance(summary, dict) else None)
    redacted_fields = string_list(summary.get("redacted_fields") if isinstance(summary, dict) else None)
    checker_ready = (
        dino_report.get("accepted_for_internal_planning") is True
        and not dino_report.get("blockers")
        and required_false_fields_clear(dino_report, set(DINO_PUBLIC_FALSE_KEYS))
        and required_zero_fields_clear(dino_report, set(DINO_ZERO_FIELDS))
        and optional_focused_non_counting_fields_clear(dino_report)
        and dino_report.get("scalar_only_ready") is True
        and dino_report.get("precall_scalar_ready") is True
        and dino_report.get("postcall_return_ready") is False
        and set(precall_copied_fields) == dino_scalar_readiness.EXPECTED_COPIED_FIELDS
        and set(deferred_return_fields) == dino_scalar_readiness.EXPECTED_EXCLUDED_FIELDS
        and set(redacted_fields) == dino_scalar_readiness.EXPECTED_REDACTED_FIELDS
        and source_isolation.get("status") == "isolated"
    )

    return {
        "schema": DINO_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "dino_policy",
        "lane": "dino_scalar_boundary_candidate",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
        ),
        "candidate_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": False,
        "focused_checker_v1_accounted": False,
        "release_statement_or_manifest_exclusion_accounted": bool(dino_gap.get("v1_accounted")),
        **{key: False for key in DINO_PUBLIC_FALSE_KEYS},
        **{key: 0 for key in DINO_ZERO_FIELDS},
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        "focused_checker": "scripts/check_dino_scalar_readiness.py",
        "focused_checker_report": {
            "schema": dino_report.get("schema"),
            "checker_status_observed": dino_report.get("status"),
            "checker_ready_observed": bool(dino_report.get("ready")),
            "accepted_for_internal_planning": bool(dino_report.get("accepted_for_internal_planning")),
            "offline_only": bool(dino_report.get("offline_only")),
            "not_artifact_gate": bool(dino_report.get("not_artifact_gate")),
            "blocker_reasons": checker_blocker_reasons(dino_report),
            "source_isolation_status": source_isolation.get("status"),
        },
        "input_target_set": dino_scalar_readiness.TARGET_SET,
        "required_evidence": list(DINO_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "scalar_boundary": {
            "checker_schema": dino_report.get("schema"),
            "checker_ready": checker_ready,
            "target_set": target_set.get("target_set") if checker_ready else None,
            "input_targets": string_list(target_set.get("input_targets")) if checker_ready else [],
            "scalar_only_ready": checker_ready and bool(dino_report.get("scalar_only_ready")),
            "precall_scalar_ready": checker_ready and bool(dino_report.get("precall_scalar_ready")),
            "precall_copied_fields": precall_copied_fields if checker_ready else [],
            "precall_copied_count": len(precall_copied_fields) if checker_ready else 0,
            "deferred_return_fields": deferred_return_fields if checker_ready else [],
            "deferred_return_count": len(deferred_return_fields) if checker_ready else 0,
            "postcall_return_ready": False,
            "return_values_excluded": (
                bool(summary.get("return_values_excluded")) if checker_ready and isinstance(summary, dict) else False
            ),
        },
        "redaction_boundary": {
            "redacted_fields": redacted_fields,
            "required_redactions": sorted(dino_scalar_readiness.EXPECTED_REDACTED_FIELDS),
            "forbidden_promotions": [
                "public Dino SDK",
                "dino/player/passenger identity",
                "ownership lookup or lifetime contract",
                "object references",
                "post-call return policy",
                "runtime hook wiring",
                "dispatcher lifecycle",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "source_isolation": {
            "status": source_isolation.get("status"),
            "violations": source_isolation.get("violations") if isinstance(source_isolation.get("violations"), list) else [],
        },
        "remaining_public_gates": string_list(dino_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
            else "blocked_accounting"
        ),
        "blocker_parity": {
            "focused_checker_blocker_reasons": checker_blocker_reasons(dino_report),
            "umbrella_blocker_reason": None if checker_ready else "dino_scalar_checker_blocked_or_not_ready",
        },
        "non_claims": [
            "dino leaf accounting is candidate-only internal scalar evidence",
            "dino scalar readiness does not promote a public Dino SDK, ABI, callback, descriptor, or v1 completion",
            "dino scalar readiness does not promote runtime hooks, dispatcher wiring, identity, lookup, object references, mutation, return override, or ResourceHandle",
            "dino scalar readiness does not count toward v1, P0 dependency-chain, runtime, stable, or complete-SDK accounting",
        ],
    }


def validate_tribe_scalar_boundary_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.tribe_leaf_blocker_accounting.scalar_boundary_checker_report"
    if report.get("schema") != TRIBE_SCALAR_BOUNDARY_SCHEMA:
        add(blockers, "tribe_scalar_boundary_schema_mismatch", f"{label}.schema")
    if report.get("target_set") != TRIBE_SCALAR_TARGET_SET:
        add(blockers, "tribe_scalar_boundary_target_set_mismatch", f"{label}.target_set")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "tribe_scalar_boundary_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("offline_only", "fixture_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "tribe_scalar_boundary_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "tribe_scalar_boundary_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in TRIBE_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "tribe_scalar_boundary_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in sorted(set(TRIBE_FORBIDDEN_READY_KEYS) - set(TRIBE_PUBLIC_FALSE_KEYS)):
        if key in report and positive_status_claim(report.get(key)):
            add(blockers, "tribe_scalar_boundary_optional_public_or_runtime_claim", f"{label}.{key}", key=key)

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "tribe_scalar_boundary_summary_missing", f"{label}.summary")
        return
    accepted_fields = string_list(summary.get("accepted_scalar_fields"))
    missing_accepted = sorted(set(TRIBE_EXPECTED_ACCEPTED_FIELDS) - set(accepted_fields))
    if missing_accepted:
        add(
            blockers,
            "tribe_scalar_boundary_accepted_fields_missing",
            f"{label}.summary.accepted_scalar_fields",
            missing=missing_accepted,
        )
    redacted_fields = string_list(summary.get("redacted_fields"))
    missing_redactions = sorted(set(TRIBE_EXPECTED_REQUIRED_REDACTIONS) - set(redacted_fields))
    if missing_redactions:
        add(
            blockers,
            "tribe_scalar_boundary_required_redactions_missing",
            f"{label}.summary.redacted_fields",
            missing=missing_redactions,
        )


def build_tribe_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    scalar_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("tribe_policy", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(TRIBE_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    tribe_gap = (
        gaps.get("tribe_policy")
        if isinstance(gaps, dict) and isinstance(gaps.get("tribe_policy"), dict)
        else {}
    )
    summary = scalar_report.get("summary") if isinstance(scalar_report.get("summary"), dict) else {}

    accepted_scalar_fields = string_list(
        summary.get("accepted_scalar_fields") if isinstance(summary, dict) else None
    )
    redacted_fields = string_list(summary.get("redacted_fields") if isinstance(summary, dict) else None)
    optional_controls = summary.get("optional_controls") if isinstance(summary, dict) else None
    control_ready = scalar_report.get("server_request_tribe_log_control_ready")
    checker_ready = (
        scalar_report.get("accepted_for_internal_planning") is True
        and not scalar_report.get("blockers")
        and required_false_fields_clear(scalar_report, set(TRIBE_PUBLIC_FALSE_KEYS))
        and optional_ready_fields_clear(scalar_report, set(TRIBE_FORBIDDEN_READY_KEYS) - set(TRIBE_PUBLIC_FALSE_KEYS))
        and scalar_report.get("tribe_scalar_boundary_ready") is True
        and control_ready is True
        and set(accepted_scalar_fields) == set(TRIBE_EXPECTED_ACCEPTED_FIELDS)
        and set(TRIBE_EXPECTED_REQUIRED_REDACTIONS).issubset(set(redacted_fields))
    )

    return {
        "schema": TRIBE_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "tribe_policy",
        "lane": "tribe_scalar_boundary_candidate",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence
            and leaf.get("status") == "planning"
            and checker_ready
        ),
        "candidate_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": bool(tribe_gap.get("v1_accounted")),
        "tribe_sdk_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "public_tribe_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_completion": False,
        "focused_checker_v1_accounted": False,
        "release_statement_or_manifest_exclusion_accounted": bool(tribe_gap.get("v1_accounted")),
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        **UMBRELLA_ACCOUNTING_ZERO_FIELDS,
        "focused_checker": "scripts/check_tribe_scalar_boundary_readiness.py",
        "input_target_set": TRIBE_SCALAR_TARGET_SET,
        "required_evidence": list(TRIBE_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "scalar_boundary": {
            "checker_schema": scalar_report.get("schema"),
            "checker_ready": checker_ready,
            "tribe_scalar_boundary_ready": checker_ready and bool(scalar_report.get("tribe_scalar_boundary_ready")),
            "server_request_tribe_log_control_ready": checker_ready and bool(control_ready),
            "accepted_scalar_fields": accepted_scalar_fields if checker_ready else [],
            "accepted_scalar_count": len(accepted_scalar_fields) if checker_ready else 0,
            "optional_controls": optional_controls if checker_ready and isinstance(optional_controls, list) else [],
        },
        "redaction_boundary": {
            "redacted_fields": redacted_fields,
            "required_redactions": sorted(TRIBE_EXPECTED_REQUIRED_REDACTIONS),
            "forbidden_promotions": [
                "public Tribe SDK",
                "tribe/player identity",
                "membership or permission enforcement contract",
                "tribe log, MOTD, notice, string, or text payloads",
                "online-list and mission-tag arrays",
                "object pointers and UE references",
                "lookup",
                "runtime hook wiring",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(tribe_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence
            and leaf.get("status") == "planning"
            and checker_ready
            else "blocked_accounting"
        ),
        "non_claims": [
            "tribe leaf accounting is candidate-only internal reusable evidence",
            "tribe leaf accounting does not promote a public Tribe SDK, ABI, callback, descriptor, or v1 completion",
            "tribe leaf accounting does not promote runtime hooks, dispatcher wiring, identity, lookup, arrays, strings, object references, mutation, return override, or ResourceHandle",
            "tribe leaf accounting keeps scalar permission/control evidence separate from blocked array and string payload work",
        ],
    }


def validate_buff_status_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "$.buff_leaf_blocker_accounting.buff_status_checker_report"
    if report.get("schema") != BUFF_STATUS_SCHEMA:
        add(blockers, "buff_status_checker_schema_mismatch", f"{label}.schema")
    target_sets = report.get("target_sets")
    if not isinstance(target_sets, dict) or target_sets.get("target_sets") != list(BUFF_TARGET_SETS_USED):
        add(blockers, "buff_status_checker_target_sets_mismatch", f"{label}.target_sets")
    if report.get("accepted_for_internal_planning") is not True:
        add(blockers, "buff_status_checker_not_internal_planning_ready", f"{label}.accepted_for_internal_planning")
    for key in ("offline_only", "fixture_only", "not_artifact_gate"):
        if report.get(key) is not True:
            add(blockers, "buff_status_checker_safety_flag_mismatch", f"{label}.{key}", key=key)
    if report.get("blockers"):
        add(
            blockers,
            "buff_status_checker_blocked",
            f"{label}.blockers",
            checker_blockers=report.get("blockers"),
        )
    for key in BUFF_PUBLIC_FALSE_KEYS:
        if report.get(key) is not False:
            add(blockers, "buff_status_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in sorted(set(BUFF_FORBIDDEN_READY_KEYS) - set(BUFF_PUBLIC_FALSE_KEYS)):
        if key in report and positive_status_claim(report.get(key)):
            add(blockers, "buff_status_optional_public_or_runtime_claim", f"{label}.{key}", key=key)
    for key in sorted(BUFF_FORBIDDEN_NONZERO_KEYS):
        if key in report and positive_numeric_claim(report.get(key)):
            add(blockers, "buff_status_progress_contribution_nonzero", f"{label}.{key}", key=key)

    summary = report.get("summary")
    if not isinstance(summary, dict):
        add(blockers, "buff_status_summary_missing", f"{label}.summary")
        return
    copied_fields = string_list(summary.get("copied_bool_fields"))
    missing_copied = sorted(set(BUFF_EXPECTED_COPIED_BOOL_FIELDS) - set(copied_fields))
    if missing_copied:
        add(
            blockers,
            "buff_status_copied_bool_fields_missing",
            f"{label}.summary.copied_bool_fields",
            missing=missing_copied,
        )
    redacted_fields = string_list(summary.get("redacted_fields"))
    missing_redactions = sorted(set(BUFF_EXPECTED_REDACTED_FIELDS) - set(redacted_fields))
    if missing_redactions:
        add(
            blockers,
            "buff_status_required_redactions_missing",
            f"{label}.summary.redacted_fields",
            missing=missing_redactions,
        )
    zero_param_targets = [
        entry.get("target")
        for entry in summary.get("zero_param_targets", [])
        if isinstance(entry, dict) and entry.get("ready") is True
    ]
    missing_zero_param = sorted(set(BUFF_EXPECTED_ZERO_PARAM_TARGETS) - set(zero_param_targets))
    if missing_zero_param:
        add(
            blockers,
            "buff_status_zero_param_targets_missing",
            f"{label}.summary.zero_param_targets",
            missing=missing_zero_param,
        )


def build_buff_leaf_blocker_accounting(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    buff_report: dict[str, Any],
) -> dict[str, Any]:
    leaf = leaves.get("buff_status", {})
    current_evidence = string_list(leaf.get("current_evidence"))
    missing_required_evidence = sorted(set(BUFF_REQUIRED_EVIDENCE) - set(current_evidence))
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    buff_gap = (
        gaps.get("buff_status")
        if isinstance(gaps, dict) and isinstance(gaps.get("buff_status"), dict)
        else {}
    )
    summary = buff_report.get("summary") if isinstance(buff_report.get("summary"), dict) else {}
    copied_bool_fields = string_list(summary.get("copied_bool_fields") if isinstance(summary, dict) else None)
    redacted_fields = string_list(summary.get("redacted_fields") if isinstance(summary, dict) else None)
    zero_param_targets = summary.get("zero_param_targets") if isinstance(summary, dict) else None
    zero_param_ready_targets = []
    if isinstance(zero_param_targets, list):
        zero_param_ready_targets = [
            entry.get("target")
            for entry in zero_param_targets
            if isinstance(entry, dict) and entry.get("ready") is True
        ]
    checker_ready = (
        buff_report.get("accepted_for_internal_planning") is True
        and not buff_report.get("blockers")
        and required_false_fields_clear(buff_report, set(BUFF_PUBLIC_FALSE_KEYS))
        and optional_ready_fields_clear(buff_report, set(BUFF_FORBIDDEN_READY_KEYS) - set(BUFF_PUBLIC_FALSE_KEYS))
        and optional_zero_fields_clear(buff_report, set(BUFF_FORBIDDEN_NONZERO_KEYS))
        and set(copied_bool_fields) == set(BUFF_EXPECTED_COPIED_BOOL_FIELDS)
        and set(BUFF_EXPECTED_REDACTED_FIELDS).issubset(set(redacted_fields))
        and set(zero_param_ready_targets) == set(BUFF_EXPECTED_ZERO_PARAM_TARGETS)
    )

    return {
        "schema": BUFF_LEAF_ACCOUNTING_SCHEMA,
        "leaf": "buff_status",
        "lane": "buff_status_scalar_boundary_candidate",
        "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
        "accounting_scope": "candidate-only internal blocker accounting",
        "accepted_for_internal_planning": (
            not missing_required_evidence
            and leaf.get("status") == "planning"
            and checker_ready
        ),
        "candidate_only": True,
        "internal_reusable_evidence_only": True,
        "not_artifact_gate": True,
        "v1_accounted": bool(buff_gap.get("v1_accounted")),
        "buff_status_sdk_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "public_buff_sdk_ready": False,
        "runtime_observer_approved": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "promotion_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_completion": False,
        "copied_payload_policy_ready": False,
        "lifecycle_semantics_ready": False,
        "focused_checker_v1_accounted": False,
        "release_statement_or_manifest_exclusion_accounted": bool(buff_gap.get("v1_accounted")),
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        **UMBRELLA_ACCOUNTING_ZERO_FIELDS,
        "focused_checker": "scripts/check_buff_status_readiness.py",
        "input_target_sets": list(BUFF_TARGET_SETS_USED),
        "required_evidence": list(BUFF_REQUIRED_EVIDENCE),
        "current_evidence": current_evidence,
        "missing_required_evidence": missing_required_evidence,
        "scalar_boundary": {
            "checker_schema": buff_report.get("schema"),
            "checker_ready": checker_ready,
            "buff_status_candidate_ready": checker_ready and bool(buff_report.get("buff_status_candidate_ready")),
            "copied_bool_boundary_ready": checker_ready and bool(buff_report.get("copied_bool_boundary_ready")),
            "class_object_redaction_ready": checker_ready and bool(buff_report.get("class_object_redaction_ready")),
            "zero_param_lifecycle_shape_ready": checker_ready and bool(buff_report.get("zero_param_lifecycle_shape_ready")),
            "copied_bool_fields": copied_bool_fields if checker_ready else [],
            "copied_bool_count": len(copied_bool_fields) if checker_ready else 0,
            "zero_param_targets": zero_param_targets if checker_ready and isinstance(zero_param_targets, list) else [],
            "checked_target_count": len(BUFF_EXPECTED_TARGETS),
        },
        "redaction_boundary": {
            "redacted_fields": redacted_fields,
            "required_redactions": sorted(BUFF_EXPECTED_REDACTED_FIELDS),
            "forbidden_promotions": [
                "public Buff/status SDK",
                "buff identity",
                "controller, character, damage-causer, or class exposure",
                "object/class pointer contract",
                "lookup",
                "runtime hook wiring",
                "copied payload policy",
                "lifecycle, stacking, or invalidation semantics",
                "aggregate, proximity, or count APIs",
                "mutation",
                "return override",
                "ResourceHandle",
            ],
        },
        "remaining_public_gates": string_list(buff_gap.get("missing_public_gates")),
        "outcome": (
            "internal_planning_only"
            if not missing_required_evidence and leaf.get("status") == "planning" and checker_ready
            else "blocked_accounting"
        ),
        "non_claims": [
            "buff/status leaf accounting is candidate-only internal reusable evidence",
            "buff/status leaf accounting does not promote a public Buff SDK, ABI, callback, descriptor, or v1 completion",
            "buff/status leaf accounting does not promote runtime hooks, dispatcher wiring, identity, lookup, object/class exposure, copied payload policy, lifecycle semantics, mutation, return override, or ResourceHandle",
            "buff/status leaf accounting keeps zero-param lifecycle shape separate from blocked lifecycle, stacking, and invalidation semantics",
        ],
    }


def validate_public_contracts(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    excluded_route: bool,
) -> None:
    surface_contract = public_contract(surface)
    if excluded_route and surface_contract:
        add(blockers, "excluded_surface_public_contract_not_empty", "$.surface.public_contract")
    for claim in forbidden_claims("\n".join(surface_contract)):
        add(blockers, "public_contract_forbidden_claim", "$.surface.public_contract", claim=claim)
    for claim in candidate_ready_claims("\n".join(surface_contract)):
        add(blockers, "public_contract_ready_overclaim", "$.surface.public_contract", claim=claim)
    for leaf_id, leaf in leaves.items():
        contract = public_contract(leaf)
        if excluded_route and contract:
            add(blockers, "excluded_leaf_public_contract_not_empty", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id)
        for claim in forbidden_claims("\n".join(contract)):
            add(blockers, "leaf_public_contract_forbidden_claim", f"$.leaf_decision_units[{leaf_id}].public_contract", leaf=leaf_id, claim=claim)
        for claim in candidate_ready_claims("\n".join(contract)):
            add(
                blockers,
                "leaf_public_contract_ready_overclaim",
                f"$.leaf_decision_units[{leaf_id}].public_contract",
                leaf=leaf_id,
                claim=claim,
            )


def leaf_accounted_by(route: str, leaf_id: str, leaf: dict[str, Any], outcome: dict[str, Any]) -> str | None:
    if route == "manifest_umbrella_excluded" and leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion"
    if route == "release_statement_umbrella_excluded" and outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion"
    if leaf.get("status") == "excluded":
        return "manifest_leaf_exclusion_pending_acceptance"
    if outcome["leaf_exclusions"].get(leaf_id):
        return "release_statement_leaf_exclusion_pending_acceptance"
    return None


def build_leaf_family_accounting(
    surface: dict[str, Any],
    leaves: dict[str, dict[str, Any]],
    outcome: dict[str, Any],
    route: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    gaps: dict[str, Any] = {}
    missing_leaf_families: list[str] = []
    non_promoted_leaf_families: list[str] = []
    missing_public_gate_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    surface_evidence = surface.get("evidence") if isinstance(surface.get("evidence"), dict) else {}
    planning_target_sets = string_list(surface_evidence.get("planning_target_sets") if isinstance(surface_evidence, dict) else None)

    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves.get(leaf_id, {})
        status = leaf.get("status") if isinstance(leaf.get("status"), str) else "missing"
        status_counts[status] = status_counts.get(status, 0) + 1
        accounted_by = leaf_accounted_by(route, leaf_id, leaf, outcome)
        missing_public_gates = list(LEAF_MISSING_PUBLIC_GATES.get(leaf_id, ()))
        if not accounted_by:
            missing_leaf_families.append(leaf_id)
        if status != "promoted":
            non_promoted_leaf_families.append(leaf_id)
        missing_public_gate_counts[leaf_id] = 0 if accounted_by == "promoted_leaf_evidence" else len(missing_public_gates)
        gaps[leaf_id] = {
            "status": status,
            "v1_accounted": accounted_by is not None,
            "accounted_by": accounted_by,
            "release_statement_excluded": bool(outcome["leaf_exclusions"].get(leaf_id)),
            "release_statement_promoted": bool(outcome["leaf_promotions"].get(leaf_id)),
            "current_evidence": string_list(leaf.get("current_evidence")),
            "current_blocker": leaf.get("current_blocker") if isinstance(leaf.get("current_blocker"), str) else None,
            "allowed_v1_outcome": non_counting_allowed_v1_outcome(leaf, accounted_by),
            "missing_public_gates": [] if accounted_by == "promoted_leaf_evidence" else missing_public_gates,
        }

    missing_gate_catalog = sorted(set(REQUIRED_LEAVES) - set(LEAF_MISSING_PUBLIC_GATES))
    if missing_gate_catalog:
        add(blockers, "leaf_family_missing_gate_catalog", "$.checker.leaf_family_accounting", missing=missing_gate_catalog)

    return {
        "mode": route,
        "result": "all_leaf_families_accounted" if not missing_leaf_families else "leaf_families_missing_v1_outcomes",
        "accepted_for_internal_planning": route == "candidate_only" and not blockers,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "promotion_ready": False,
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
        "planning_target_sets": planning_target_sets,
        "missing_leaf_families": missing_leaf_families,
        "non_promoted_leaf_families": non_promoted_leaf_families,
        "missing_public_gate_counts": missing_public_gate_counts,
        "status_counts": status_counts,
        "leaf_family_gaps": gaps,
        "guardrail": (
            "candidate-only accounting names missing leaf outcomes and public gates; "
            "it does not promote public SDK, runtime, identity, lookup, mutation, return override, ResourceHandle, or teleport/spawn"
        ),
    }


def validate_leaf_priority_profiles(blockers: list[dict[str, Any]]) -> None:
    observed = set(LEAF_PRIORITY_PROFILES)
    required = set(REQUIRED_LEAVES)
    if observed != required:
        add(
            blockers,
            "leaf_priority_profiles_mismatch",
            "$.checker.leaf_priority_profiles",
            missing=sorted(required - observed),
            extra=sorted(observed - required),
        )
    for leaf_id, profile in LEAF_PRIORITY_PROFILES.items():
        if not isinstance(profile.get("base_score"), int):
            add(blockers, "leaf_priority_base_score_missing", f"$.checker.leaf_priority_profiles[{leaf_id}].base_score")
        for key in ("required_evidence", "reusable_evidence", "blocking_risk"):
            values = profile.get(key)
            if not isinstance(values, tuple) or not all(isinstance(item, str) and item for item in values):
                add(blockers, "leaf_priority_profile_list_invalid", f"$.checker.leaf_priority_profiles[{leaf_id}].{key}")
        if not isinstance(profile.get("next_v1_reuse_step"), str) or not profile["next_v1_reuse_step"]:
            add(blockers, "leaf_priority_next_step_missing", f"$.checker.leaf_priority_profiles[{leaf_id}].next_v1_reuse_step")


def build_leaf_priority(
    leaves: dict[str, dict[str, Any]],
    leaf_family_accounting: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    validate_leaf_priority_profiles(blockers)
    gaps = leaf_family_accounting.get("leaf_family_gaps")
    if not isinstance(gaps, dict):
        gaps = {}

    ranked: list[dict[str, Any]] = []
    for leaf_id in REQUIRED_LEAVES:
        if leaf_id not in leaves:
            continue
        leaf = leaves[leaf_id]
        profile = LEAF_PRIORITY_PROFILES.get(leaf_id, {})
        current_evidence = string_list(leaf.get("current_evidence"))
        missing_required_evidence = sorted(set(profile.get("required_evidence", ())) - set(current_evidence))
        if missing_required_evidence:
            add(
                blockers,
                "leaf_priority_required_evidence_missing",
                f"$.leaf_decision_units[{leaf_id}].current_evidence",
                leaf=leaf_id,
                missing=missing_required_evidence,
            )
        gap = gaps.get(leaf_id) if isinstance(gaps.get(leaf_id), dict) else {}
        missing_public_gates = string_list(gap.get("missing_public_gates"))
        score = int(profile.get("base_score", 0)) + (2 * len(current_evidence)) - len(missing_public_gates)
        ranked.append(
            {
                "leaf": leaf_id,
                "priority_score": score,
                "status": leaf.get("status") if isinstance(leaf.get("status"), str) else "missing",
                "current_evidence": current_evidence,
                "reusable_evidence": list(profile.get("reusable_evidence", ())),
                "blocking_risk": list(profile.get("blocking_risk", ())),
                "missing_public_gate_count": len(missing_public_gates),
                "v1_accounted": bool(gap.get("v1_accounted")),
                "public_sdk_ready": False,
                "runtime_ready": False,
                "promotion_ready": False,
                "next_v1_reuse_step": profile.get("next_v1_reuse_step"),
            }
        )

    ranked.sort(key=lambda item: (-item["priority_score"], REQUIRED_LEAVES.index(item["leaf"])))
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    recommended = ranked[0]["leaf"] if ranked else None
    return {
        "schema": "obelisk.mission-transfer-dino-tribe-v1-leaf-priority.v1",
        "recommended_leaf": recommended,
        "recommended_scope": "internal_reusable_evidence_only" if recommended else None,
        "basis": (
            "Scores reward focused copied-scalar/checker evidence and penalize unresolved "
            "public SDK, runtime, identity, lookup, payload, mutation, return-override, "
            "ResourceHandle, and teleport/spawn gates."
        ),
        "ranked_leaves": ranked,
        "non_claims": [
            "leaf priority does not promote a public SDK or runtime observer",
            "leaf priority does not add identity, lookup, mutation, return override, ResourceHandle, teleport/spawn, or payload ownership",
        ],
    }


def build_report(
    manifest_path: Path,
    split_note_path: Path,
    release_statement_path: Path | None = None,
    mission_root: Path = mission_copied_bool_readiness.DEFAULT_ROOT,
    mission_manifest: Path | None = None,
    mission_expected_manifest_sha256: str = mission_copied_bool_readiness.EXPECTED_MANIFEST_SHA256,
    mission_skip_artifact_gates: bool = False,
    mission_fixture_boundary_only: bool = False,
    transfer_root: Path = transfer_baccept_readiness.DEFAULT_ROOT,
    transfer_manifest: Path | None = None,
    transfer_expected_manifest_sha256: str = transfer_baccept_readiness.EXPECTED_MANIFEST_SHA256,
    transfer_skip_artifact_gates: bool = False,
    transfer_scriptstruct_snapshot_root: Path = transfer_scriptstruct_readiness.DEFAULT_SNAPSHOT_ROOT,
    transfer_scriptstruct_report_path: Path | None = None,
    dino_repo_root: Path = REPO_ROOT,
    dino_report_path: Path | None = None,
    dino_snapshot_root: Path = dino_scalar_readiness.DEFAULT_SNAPSHOT_ROOT,
    tribe_snapshot_root: Path = DEFAULT_TRIBE_SCALAR_SNAPSHOT_ROOT,
    buff_snapshot_root: Path = DEFAULT_BUFF_STATUS_SNAPSHOT_ROOT,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    manifest = load_json(manifest_path, "manifest")
    split_note = read_optional(split_note_path, "split_note")
    release_statement = read_optional(release_statement_path, "release_statement")
    validate_split_note(split_note, blockers)

    if manifest.get("schema") != "obelisk.public-sdk-surfaces.v1":
        add(blockers, "manifest_schema_mismatch", "$.schema")
    surface = surface_by_id(manifest, SURFACE_ID)
    if surface is None:
        add(blockers, "surface_missing", "$.surfaces")
        surface = {"id": SURFACE_ID, "leaf_decision_units": []}
    leaves = leaf_map(surface, blockers)
    outcome = release_statement_outcome(release_statement)
    validate_candidate_surface_evidence(surface, blockers)
    for leaf_id in REQUIRED_LEAVES:
        leaf = leaves.get(leaf_id, {})
        validate_candidate_leaf_evidence(surface, leaf_id, leaf, blockers)
        validate_candidate_leaf_metadata(leaf_id, leaf, blockers)

    manifest_umbrella_excluded = surface.get("status") == "excluded" and all(
        leaves.get(leaf_id, {}).get("status") == "excluded" for leaf_id in REQUIRED_LEAVES
    )
    statement_umbrella_excluded = outcome["present"] and outcome["umbrella_excluded"] and all(
        outcome["leaf_exclusions"].get(leaf_id) for leaf_id in REQUIRED_LEAVES
    )
    promoted_leaf_route_ready = validate_promoted_leaf_evidence(surface, leaves, blockers, manifest_dir=manifest_path.parent)

    if outcome["forbidden_claims"]:
        add(
            blockers,
            "release_statement_forbidden_claims",
            "$.release_statement",
            claims=outcome["forbidden_claims"],
        )
    if outcome["ready_claims"]:
        add(
            blockers,
            "release_statement_ready_overclaims",
            "$.release_statement",
            claims=outcome["ready_claims"],
        )
    promoted_statement_leaves = [
        leaf_id for leaf_id in REQUIRED_LEAVES if outcome["leaf_promotions"].get(leaf_id)
    ]
    if promoted_statement_leaves and not promoted_leaf_route_ready:
        add(
            blockers,
            "release_statement_leaf_promotions_without_evidence",
            "$.release_statement",
            leaves=promoted_statement_leaves,
        )
    if outcome["present"] and not statement_umbrella_excluded and not promoted_leaf_route_ready:
        missing = [leaf_id for leaf_id in REQUIRED_LEAVES if not outcome["leaf_exclusions"].get(leaf_id)]
        if not outcome["umbrella_excluded"]:
            add(blockers, "release_statement_umbrella_exclusion_missing", "$.release_statement", surface=SURFACE_ID)
        if missing:
            add(blockers, "release_statement_leaf_exclusions_missing", "$.release_statement", missing=missing)
    if surface.get("status") == "excluded" and not manifest_umbrella_excluded:
        add(blockers, "manifest_excluded_route_missing_leaf_exclusions", "$.leaf_decision_units")

    mission_copied_bool_report = mission_copied_bool_readiness.build_report(
        mission_root,
        mission_manifest,
        mission_expected_manifest_sha256,
        mission_skip_artifact_gates,
        mission_fixture_boundary_only,
    )
    validate_mission_copied_bool_report(mission_copied_bool_report, blockers)
    transfer_baccept_report = transfer_baccept_readiness.build_report(
        transfer_root,
        transfer_manifest,
        transfer_expected_manifest_sha256,
        transfer_skip_artifact_gates,
    )
    validate_transfer_baccept_report(transfer_baccept_report, blockers)
    transfer_scriptstruct_source_report = load_optional_focus_report(
        transfer_scriptstruct_report_path,
        "transfer_scriptstruct_report",
        blockers,
    )
    transfer_scriptstruct_report = transfer_scriptstruct_readiness.build_report(
        snapshot_root=transfer_scriptstruct_snapshot_root,
        source_report=transfer_scriptstruct_source_report,
    )
    validate_transfer_scriptstruct_report(transfer_scriptstruct_report, blockers)
    dino_scalar_report = dino_scalar_readiness.build_report(
        dino_repo_root,
        dino_report_path,
        dino_snapshot_root,
    )
    validate_dino_scalar_report(dino_scalar_report, blockers)
    tribe_scalar_boundary_report = build_tribe_scalar_boundary_report(tribe_snapshot_root)
    validate_tribe_scalar_boundary_report(tribe_scalar_boundary_report, blockers)
    buff_status_report = build_buff_status_report(buff_snapshot_root)
    validate_buff_status_report(buff_status_report, blockers)

    excluded_route = manifest_umbrella_excluded or statement_umbrella_excluded
    validate_public_contracts(surface, leaves, blockers, excluded_route=excluded_route)

    if statement_umbrella_excluded:
        route = "release_statement_umbrella_excluded"
    elif manifest_umbrella_excluded:
        route = "manifest_umbrella_excluded"
    else:
        route = "candidate_only"
    leaf_family_accounting = build_leaf_family_accounting(surface, leaves, outcome, route, blockers)
    leaf_priority = build_leaf_priority(leaves, leaf_family_accounting, blockers)
    mission_leaf_blocker_accounting = build_mission_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        mission_copied_bool_report,
    )
    transfer_leaf_blocker_accounting = build_transfer_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        transfer_baccept_report,
    )
    transfer_scriptstruct_leaf_blocker_accounting = build_transfer_scriptstruct_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        transfer_scriptstruct_report,
    )
    dino_leaf_blocker_accounting = build_dino_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        dino_scalar_report,
    )
    tribe_leaf_blocker_accounting = build_tribe_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        tribe_scalar_boundary_report,
    )
    buff_leaf_blocker_accounting = build_buff_leaf_blocker_accounting(
        leaves,
        leaf_family_accounting,
        buff_status_report,
    )
    leaf_family_accounting["non_counting_internal_evidence"] = {
        "transfer_scriptstruct": {
            "leaf": "transfer",
            "checker": "scripts/check_transfer_scriptstruct_readiness.py",
            "checker_ready": bool(transfer_scriptstruct_report.get("ready")),
            "accepted_for_internal_planning": bool(
                transfer_scriptstruct_report.get("accepted_for_internal_planning")
            ),
            "target_set": transfer_scriptstruct_readiness.TARGET_SET,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "progress_contribution": 0,
        },
        "dino_scalar": {
            "leaf": "dino_policy",
            "checker": "scripts/check_dino_scalar_readiness.py",
            "checker_ready": bool(dino_scalar_report.get("ready")),
            "accepted_for_internal_planning": bool(dino_scalar_report.get("accepted_for_internal_planning")),
            "target_set": dino_scalar_readiness.TARGET_SET,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "progress_contribution": 0,
        },
    }

    return {
        "schema": REPORT_SCHEMA,
        "surface": SURFACE_ID,
        "ready": not blockers,
        "accounting_route": route,
        "v1_accounted": route in {"release_statement_umbrella_excluded", "manifest_umbrella_excluded"},
        "candidate_only": route == "candidate_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "required_leaves": list(REQUIRED_LEAVES),
        "observed_leaves": [leaf_id for leaf_id in REQUIRED_LEAVES if leaf_id in leaves],
        "leaf_statuses": {leaf_id: leaves.get(leaf_id, {}).get("status") for leaf_id in REQUIRED_LEAVES},
        "candidate_only_accounting": leaf_family_accounting,
        "mission_leaf_blocker_accounting": mission_leaf_blocker_accounting,
        "transfer_leaf_blocker_accounting": transfer_leaf_blocker_accounting,
        "transfer_scriptstruct_leaf_blocker_accounting": transfer_scriptstruct_leaf_blocker_accounting,
        "dino_leaf_blocker_accounting": dino_leaf_blocker_accounting,
        "tribe_leaf_blocker_accounting": tribe_leaf_blocker_accounting,
        "buff_leaf_blocker_accounting": buff_leaf_blocker_accounting,
        "leaf_priority": leaf_priority,
        "missing_leaf_families": leaf_family_accounting["missing_leaf_families"],
        "release_statement": outcome,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "candidate-only accounting does not add Mission, Transfer, Dino, Tribe, or Buff APIs",
            "candidate-only accounting does not add identity, lookup, mutation, return override, runtime hook, ResourceHandle, teleport/spawn, ownership lookup, or cross-map correlation",
            "candidate-only accounting does not count focused Mission, Transfer, Transfer ScriptStruct, Dino, Tribe, or Buff readiness toward P0 dependency-chain or complete-SDK accounting",
        ],
        **UMBRELLA_ACCOUNTING_FALSE_FLAGS,
    }


def main() -> int:
    args = parse_args()
    report = build_report(
        args.manifest,
        args.split_note,
        args.release_statement,
        args.mission_root,
        args.mission_manifest,
        args.mission_expected_manifest_sha256,
        args.mission_skip_artifact_gates,
        args.mission_fixture_boundary_only,
        args.transfer_root,
        args.transfer_manifest,
        args.transfer_expected_manifest_sha256,
        args.transfer_skip_artifact_gates,
        args.transfer_scriptstruct_snapshot_root,
        args.transfer_scriptstruct_report,
        args.dino_repo_root,
        args.dino_report,
        args.dino_snapshot_root,
        args.tribe_snapshot_root,
        args.buff_snapshot_root,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif report["ready"]:
        print(f"{SURFACE_ID}: {report['accounting_route']} accounting accepted")
    else:
        for blocker in report["blocker_details"]:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
