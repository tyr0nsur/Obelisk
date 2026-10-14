#!/usr/bin/env python3
"""Read-only readiness check for the internal Buff/status scalar boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    NON_AUTHORIZING_READY_SCOPE,
    TARGET_SETS,
    side_lane_noncanonical_bool_payload_issues,
    side_lane_fail_closed_source_artifact_issues,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
REPORT_SCHEMA = "obelisk.buff-status-readiness-check.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
SNAPSHOT_MANIFEST_SCHEMA = "obelisk.ufunction-snapshot-manifest.v1"
TARGET_SETS_USED = ("buff-compact-intake", "buff-breadth-intake")
EXPECTED_COMPACT_TARGETS = {
    "PrimalBuff.AllowPostProcessEffect",
    "PrimalBuff.BPBuffPreventUploading",
    "PrimalBuff.BP_OnBuffLifetimeUpdated",
}
EXPECTED_BREADTH_TARGETS = {
    "PrimalBuff.BuffOverrideInventoryAccessInput",
    "PrimalBuff.BPCustomAllowAddBuff",
    "PrimalBuff.BPPreventAddingOtherBuff",
}
EXPECTED_TARGETS = EXPECTED_COMPACT_TARGETS | EXPECTED_BREADTH_TARGETS
EXPECTED_TARGETS_BY_SET = {
    "buff-compact-intake": EXPECTED_COMPACT_TARGETS,
    "buff-breadth-intake": EXPECTED_BREADTH_TARGETS,
}
EXPECTED_FIXTURE_MODULE = "sdk_buffs"
EXPECTED_COPIED_BOOL_FIELDS = {
    "PrimalBuff.AllowPostProcessEffect.ReturnValue": {"direction": "return", "offset_internal": 0},
    "PrimalBuff.BPBuffPreventUploading.ReturnValue": {"direction": "return", "offset_internal": 0},
    "PrimalBuff.BuffOverrideInventoryAccessInput.bInputPressed": {"direction": "in", "offset_internal": 8},
    "PrimalBuff.BuffOverrideInventoryAccessInput.ReturnValue": {"direction": "return", "offset_internal": 9},
    "PrimalBuff.BPCustomAllowAddBuff.ReturnValue": {"direction": "return", "offset_internal": 16},
    "PrimalBuff.BPPreventAddingOtherBuff.ReturnValue": {"direction": "return", "offset_internal": 8},
}
EXPECTED_REDACTED_FIELDS = {
    "PrimalBuff.BuffOverrideInventoryAccessInput.InController": "object_ref_controller",
    "PrimalBuff.BPCustomAllowAddBuff.forCharacter": "object_ref_character",
    "PrimalBuff.BPCustomAllowAddBuff.DamageCauser": "object_ref_damage_causer",
    "PrimalBuff.BPPreventAddingOtherBuff.anotherBuffClass": "class_ref_other_buff",
}
EXPECTED_ZERO_PARAM_TARGETS = {"PrimalBuff.BP_OnBuffLifetimeUpdated"}
CURRENT_SDK_BLOCKER = "approved_runtime_evidence_missing"
BETA_CAPTURE_STATUS = "future_capture_targets_only"
BETA_CAPTURE_TARGET_STATUS = "future_capture_target"
BETA_CAPTURE_GATE = "dedicated_beta_capture_check_required"
BETA_CAPTURE_SURFACE = "buff_status"
BETA_CAPTURE_FALSE_OR_ZERO_FIELDS = (
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "candidate_capture_evidence_ready",
    "candidate_capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_ready",
    "counts_as_approved_runtime_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "debug_capture_ready",
    "dependency_chain_completion_ready",
    "mutation_authority_ready",
    "mutation_ready",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_ready",
    "p0_ready",
    "player_principal_replacement_ready",
    "player_principal_runtime_evidence_ready",
    "public_sdk_ready",
    "replaces_player_principal_evidence",
    "resource_handle_ready",
    "return_override_ready",
    "return_value_override_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_ready",
    "v1_completion",
    "v1_completion_contribution",
    "v1_completion_ready",
)
BETA_CAPTURE_ARTIFACT_KEYS = (
    "beta_capture",
    "beta_capture_pack",
    "beta_capture_plan",
    "beta_capture_prep",
    "candidate_beta_capture_pack",
    "candidate_beta_capture_plan",
    "capture_pack",
    "capture_plan",
    "multi_surface_beta_capture",
    "multi_surface_beta_capture_pack",
    "multi_surface_beta_capture_plan",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BUFF_OBJECT_OR_CLASS_RE = re.compile(
    r"(?:controller|character|damage[_-]?causer|buff[_-]?class|class|object|pointer|identity|handle)",
    re.IGNORECASE,
)
FORBIDDEN_READY_KEYS = {
    "abi_ready",
    "aggregate_ready",
    "buff_sdk_ready",
    "buff_status_sdk_ready",
    "callback_ready",
    "capability_bit_ready",
    "capability_ready",
    "candidate_capture_evidence_ready",
    "candidate_capture_ready",
    "candidate_debug_capture_ready",
    "class_pointer_ready",
    "complete_sdk_claim_allowed",
    "copied_payload_policy_ready",
    "copied_payload_ready",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "descriptor_ready",
    "dispatcher_ready",
    "debug_capture_evidence_ready",
    "debug_capture_ready",
    "identity_ready",
    "lifecycle_ready",
    "lifecycle_semantics_ready",
    "lookup_ready",
    "module_sdk_ready",
    "mutation_ready",
    "object_identity_ready",
    "object_pointer_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_ready",
    "p0_ready",
    "promotion_ready",
    "proximity_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_buff_module_ready",
    "public_buff_status_sdk_ready",
    "public_buff_sdk_ready",
    "public_callback_ready",
    "public_capability_ready",
    "public_descriptor_ready",
    "public_header_ready",
    "public_module_ready",
    "public_module_sdk_ready",
    "public_sdk_ready",
    "release_ready",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_capture_ready",
    "runtime_observer_approved",
    "runtime_hook_ready",
    "runtime_ready",
    "runtime_wiring_ready",
    "sdk_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "support_tier_active",
    "support_tier_ready",
    "buff_public_module_ready",
    "buff_public_module_sdk_ready",
    "buff_status_public_abi_ready",
    "buff_status_public_c_abi_ready",
    "buff_status_callback_ready",
    "buff_status_sdk_available",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_sdk_ready",
    "counts_as_approved_runtime_evidence",
    "debug_capture_ready",
    "dependency_chain_completion_ready",
    "leaf_promotion_ready",
    "live_ops_ready",
    "mutation_authority_ready",
    "player_principal_replacement_ready",
    "player_principal_runtime_evidence_ready",
    "p0_dependency_chain_complete",
    "runtime_support_active",
    "runtime_support_ready",
    "runtime_v1_support_active",
    "runtime_v1_support_ready",
    "replaces_player_principal_evidence",
    "return_value_override_ready",
    "runtime_evidence_ready",
    "source_readiness",
    "source_ready",
    "umbrella_leaf_promoted",
    "umbrella_leaf_promotion_ready",
    "v1_accounted",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
}
FORBIDDEN_NONZERO_KEYS = {
    "candidate_capture_progress_contribution",
    "candidate_debug_capture_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "debug_capture_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "runtime_progress_contribution",
    "sdk_progress",
    "sdk_progress_contribution",
    "v1_completion_contribution",
    "v1_completion_progress_contribution",
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:resource[_-]?handle|return[_-]?(?:value[_-]?)?override|public[_-]?(?:sdk|api|abi|surface|module|header|callback|descriptor|capability)|"
    r"(?:beta|candidate|debug|candidate[_-]?debug|multi[_-]?surface[_-]?beta)?[_-]?capture[_-]?(?:evidence|pack|plan|progress|ready|claim)|"
    r"(?:module[_-]?sdk|callback|descriptor|capability|dispatcher)[_-]?ready|"
    r"approved[_-]?runtime[_-]?evidence|runtime[_-]?evidence|clears?[_-]?approved[_-]?runtime[_-]?evidence[_-]?missing|"
    r"(?:replace|replaces|replacement|supersede|supersedes)[_-]?(?:player[_-]?principal|principal)|"
    r"player[_-]?principal[_-]?(?:runtime[_-]?evidence|evidence|replacement|replaced|satisfied|ready)|"
    r"runtime[_-]?(?:ready|hook|observer|wiring|support|capture)|live[_-]?ops|"
    r"v1[_-]?(?:ready|complete|completion|accounted|support)|"
    r"(?:p0|dependency)[_-]?(?:ready|dependency|chain|completion|complete)|counts[_-]?(?:as|toward)[_-]?(?:approved|complete|p0|public|runtime|v1)|"
    r"(?:complete|p0|v1)[_-]?(?:sdk[_-]?claim[_-]?)?progress[_-]?contribution|"
    r"sdk[_-]?progress(?:[_-]?contribution)?|"
    r"(?:complete|stable)[_-]?sdk[_-]?claim|support[_-]?tier|release[_-]?ready|"
    r"umbrella[_-]?leaf[_-]?(?:promoted|promotion)|leaf[_-]?promotion|"
    r"copied[_-]?payload[_-]?policy|lifecycle[_-]?semantics|"
    r"lookup[_-]?ready|mutation(?:[_-]?authority)?[_-]?ready|identity[_-]?ready|"
    r"(?:object|class)[_-]?(?:pointer|identity|contract|exposure)[_-]?ready)",
    re.IGNORECASE,
)
CLAIM_CONTEXT_KEY_RE = re.compile(
    r"(?:approved[_-]?runtime[_-]?evidence|beta|public|sdk|api|abi|module|callback|descriptor|"
    r"capability|runtime|capture|pack|plan|multi[_-]?surface|live[_-]?ops|source|v1|p0|"
    r"complete|completion|dependency[_-]?chain|stable|promotion|resource[_-]?handle|"
    r"return[_-]?(?:value[_-]?)?override|identity|lookup|mutation|player[_-]?principal|principal|support|tier)",
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|blocking|excluded|missing|not\s+included|post-v1|post v1|false|redacted|candidate-only)\b",
    re.IGNORECASE,
)
FORBIDDEN_TEXT_CLAIM_RE = re.compile(
    r"\b(?:(?:Buff/status|Buff status|BuffStatus|Buff)\s+(?:SDK|API|module|callback|descriptor|capability)|"
    r"public\s+(?:Buff/status\s+|Buff\s+|module\s+)?(?:SDK|API|ABI|C\s+ABI|runtime\s+API|callback|descriptor|capability)|"
    r"runtime\s+(?:hook|observer|wiring|dispatcher|callback)|"
    r"P0\s+(?:dependency\s+chain|chain|readiness)|"
    r"(?:umbrella[- ]leaf|leaf)\s+(?:promotion|promoted)|"
    r"identity|lookup|mutation|mutation\s+authority|return[- ](?:value[- ]?)?override|ResourceHandle|Resource\s+Handle|"
    r"object/class\s+(?:pointer\s+)?(?:contract|exposure)|class\s+exposure|object\s+exposure|"
    r"copied\s+payload\s+policy|lifecycle\s+semantics|stacking\s+semantics|invalidation\s+semantics|"
    r"v1\s+(?:completion|complete|ready|release|accounted))\b",
    re.IGNORECASE,
)
READY_TEXT_CLAIM_RE = re.compile(
    r"\b(?:public\s+(?:SDK|API|ABI)|(?:Buff/status|Buff status|BuffStatus|Buff)\s+SDK|runtime|runtime\s+observer|runtime\s+hook|"
    r"(?:approved\s+)?runtime\s+evidence|player[-_ ]principal(?:\s+lifecycle)?\s+evidence|"
    r"module\s+SDK|header\s+callbacks?|promotion|v1|v1\s+SDK|P0\s+(?:dependency\s+chain|chain))\s+"
    r"(?:is\s+|are\s+)?(?:ready|complete|completion|available|present|satisfied|published|enabled|approved|allowed|unblocked|unlocked)\b|"
    r"\b(?:clears?|satisfies?|replaces?)\s+"
    r"(?:approved_runtime_evidence_missing|(?:approved\s+)?runtime\s+evidence|player[-_ ]principal(?:\s+lifecycle)?\s+evidence)\b|"
    r"\bapproved_runtime_evidence_missing\s+(?:is\s+)?(?:cleared|satisfied|unblocked|unlocked)\b|"
    r"\b(?:runtime|runtime/v1|v1(?:\s+SDK)?|public\s+SDK|Buff/status\s+SDK|Buff\s+SDK)\s+support\s+"
    r"(?:is\s+|are\s+)?(?:active|available|allowed|enabled|promoted|published|ready|supported|unblocked|unlocked)\b|"
    r"\b(?:ready|complete|available|enabled|allowed|unblocked|unlocked)\s+for\s+v1\b|"
    r"\bv1(?:\.0)?\s+(?:is\s+)?(?:stable|complete|completion|ready|allowed|unblocked|unlocked)\b|"
    r"\bcounts?\s+toward\s+(?:the\s+)?(?:complete|full|production)\s+SDK\s+claim\b|"
    r"\bcredits?\s+(?:toward|for|to)\s+(?:the\s+)?(?:complete|full|production|public|v1)\s+SDK\s+claim\b|"
    r"\brelease\s+(?:readiness\s+)?(?:is\s+)?(?:ready|complete|satisfied|available|allowed|enabled|approved|supported|unblocked|unlocked)\b|"
    r"\bsupport[- ]?tier\s+(?:is\s+)?(?:active|available|ready|allowed|enabled|promoted|published|supported|release[- ]supported|unblocked|unlocked)\b|"
    r"\bstable\s+SDK\s+(?:is\s+)?(?:allowed|ready|complete|available|enabled|unblocked|unlocked)\b",
    re.IGNORECASE,
)
CANDIDATE_CAPTURE_PROMOTION_RE = re.compile(
    r"\b(?:(?:multi[_ -]?surface\s+)?(?:beta|candidate|debug|candidate/debug)[_ -]?captures?|"
    r"(?:multi[_ -]?surface\s+)?(?:beta|candidate|debug)[_ -]?capture[_ -]?(?:pack|plan|artifact|bundle)s?)\s+"
    r"(?:(?:is|are)\s+(?:accepted|approved|available|enabled|evidence|progress|promoted|ready|runtime|supported|validated)|"
    r"(?:counts?|credits?)\s+(?:toward|for)|"
    r"(?:clears?|enables?|promotes?|replaces?|satisfies?|supports?|unlocks?|unblocks?|authorizes?|validates?))\b",
    re.IGNORECASE,
)
AFFIRMATIVE_STATUS_VALUE_RE = re.compile(
    r"\b(?:accepted|active|available|allowed|enabled|promoted|published|ready|release[-_\s]+supported|"
    r"stable|supported|unblocked|unlocked)\b",
    re.IGNORECASE,
)
POSITIVE_STATUS_VALUES = frozenset(
    (
        "accepted",
        "active",
        "available",
        "allowed",
        "complete",
        "enabled",
        "promoted",
        "published",
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
        "unblocked",
        "unlocked",
        "validated",
        "v1-ready",
    )
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Buff/status candidate readiness from sanitized snapshots only."
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Root containing sanitized UFunction snapshot fixtures.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def claim_value_is_false_or_zero(value: Any) -> bool:
    return value is False or value is None or value == 0


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def target_key(snapshot_target: dict[str, Any]) -> str | None:
    target = snapshot_target.get("target")
    if not isinstance(target, dict):
        return None
    outer_name = target.get("outer_name")
    name = target.get("name")
    if not isinstance(outer_name, str) or not isinstance(name, str):
        return None
    return f"{outer_name}.{name}"


def property_key(target: str, prop: dict[str, Any]) -> str | None:
    name = prop.get("name")
    if not isinstance(name, str) or not name:
        return None
    return f"{target}.{name}"


def parse_hex_or_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def bool_mask_is_one(value: Any) -> bool:
    return parse_hex_or_int(value) == 1


def read_json_file(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "snapshot_unreadable", path=str(path), detail=str(exc))
        return None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "snapshot_malformed", path=str(path), detail=str(exc))
        return None
    if not isinstance(payload, dict):
        append_blocker(blockers, "snapshot_not_object", path=str(path))
        return None
    payload["_source_path"] = str(path)
    payload["_source_sha256"] = hashlib.sha256(content).hexdigest()
    return payload


def read_manifest_file(path: Path, blockers: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    try:
        content = path.read_bytes()
        payload = json.loads(content.decode("utf-8"))
    except OSError as exc:
        append_blocker(blockers, "manifest_unreadable", path=str(path), detail=str(exc))
        return None, None
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "manifest_malformed", path=str(path), detail=str(exc))
        return None, None
    if not isinstance(payload, dict):
        append_blocker(blockers, "manifest_not_object", path=str(path))
        return None, None
    return payload, hashlib.sha256(content).hexdigest()


def component_is_safe(value: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_.-]+", value) is not None and ".." not in value


def relative_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def field_target(field: str) -> str:
    return field.rsplit(".", 1)[0]


def expected_copied_bool_fields(expected_targets: set[str]) -> dict[str, dict[str, Any]]:
    return {
        field: spec
        for field, spec in EXPECTED_COPIED_BOOL_FIELDS.items()
        if field_target(field) in expected_targets
    }


def expected_redacted_fields(expected_targets: set[str]) -> dict[str, str]:
    return {
        field: reason
        for field, reason in EXPECTED_REDACTED_FIELDS.items()
        if field_target(field) in expected_targets
    }


def expected_zero_param_targets(expected_targets: set[str]) -> set[str]:
    return EXPECTED_ZERO_PARAM_TARGETS & expected_targets


def build_beta_capture_prep(
    expected_targets: set[str],
    target_sets_by_target: dict[str, list[str]],
) -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    for target in sorted(expected_targets):
        targets.append(
            {
                "target": target,
                "surface": BETA_CAPTURE_SURFACE,
                "target_sets": sorted(target_sets_by_target.get(target, [])),
                "status": BETA_CAPTURE_TARGET_STATUS,
                "source_evidence": "candidate_only_sanitized_ufunction_snapshot",
                "capture_gate": BETA_CAPTURE_GATE,
                "approved_runtime_evidence_ready": False,
                "clears_approved_runtime_evidence_missing": False,
                "player_principal_runtime_evidence_ready": False,
                "replaces_player_principal_evidence": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "runtime_capture_ready": False,
                "sdk_ready": False,
                "sdk_progress": 0,
                "p0_dependency_chain_ready": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "copied_bool_fields": sorted(
                    field for field in EXPECTED_COPIED_BOOL_FIELDS if field_target(field) == target
                ),
                "redacted_fields": sorted(
                    field for field in EXPECTED_REDACTED_FIELDS if field_target(field) == target
                ),
                "zero_param_lifecycle_shape_only": target in EXPECTED_ZERO_PARAM_TARGETS,
            }
        )
    return {
        "status": BETA_CAPTURE_STATUS,
        "surface": BETA_CAPTURE_SURFACE,
        "target_sets": sorted(TARGET_SETS_USED),
        "source_evidence": "candidate_only_sanitized_ufunction_snapshots",
        "capture_gate": BETA_CAPTURE_GATE,
        "multi_surface_plan_role": "buff_status_surface_candidate_prep_only",
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "approved_runtime_evidence_missing_cleared": False,
        "player_principal_runtime_evidence_ready": False,
        "replaces_player_principal_evidence": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "debug_capture_ready": False,
        "sdk_ready": False,
        "sdk_progress": 0,
        "p0_dependency_chain_ready": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "targets": targets,
        "non_claims": [
            "future beta/debug capture target planning only",
            "dedicated beta capture acceptance check is required before runtime use",
            "does not clear approved_runtime_evidence_missing",
            "does not replace player-principal lifecycle evidence",
        ],
    }


def validate_beta_capture_entry(entry: Any, blockers: list[dict[str, Any]], path: str) -> str | None:
    if not isinstance(entry, dict):
        append_blocker(blockers, "beta_capture_target_malformed", path=path)
        return None
    target = entry.get("target")
    if not isinstance(target, str) or target not in EXPECTED_TARGETS:
        append_blocker(blockers, "beta_capture_target_mismatch", path=f"{path}.target", target=target)
    if entry.get("surface") not in {BETA_CAPTURE_SURFACE, "multi_surface", None}:
        append_blocker(blockers, "beta_capture_surface_mismatch", path=f"{path}.surface", value=entry.get("surface"))
    status = entry.get("status")
    if status not in {BETA_CAPTURE_TARGET_STATUS, BETA_CAPTURE_STATUS, "candidate-only", "candidate-prep", "candidate_prep", None}:
        append_blocker(blockers, "beta_capture_target_status_mismatch", path=f"{path}.status", value=status)
    if entry.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_gate_mismatch", path=f"{path}.capture_gate", value=entry.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in entry and not claim_value_is_false_or_zero(entry.get(key)):
            append_blocker(
                blockers,
                "beta_capture_readiness_overclaim",
                path=f"{path}.{key}",
                value=entry.get(key),
            )
    return target if isinstance(target, str) else None


def validate_beta_capture_prep(value: Any, blockers: list[dict[str, Any]], path: str) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        append_blocker(blockers, "beta_capture_prep_malformed", path=path)
        return
    status = value.get("status")
    if status not in {BETA_CAPTURE_STATUS, "candidate-only", "candidate-prep", "candidate_prep", "future_capture_plan_only"}:
        append_blocker(blockers, "beta_capture_prep_status_mismatch", path=f"{path}.status", value=status)
    if value.get("surface") not in {BETA_CAPTURE_SURFACE, "multi_surface", None}:
        append_blocker(blockers, "beta_capture_prep_surface_mismatch", path=f"{path}.surface", value=value.get("surface"))
    if value.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_prep_gate_mismatch", path=f"{path}.capture_gate", value=value.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in value and not claim_value_is_false_or_zero(value.get(key)):
            append_blocker(blockers, "beta_capture_readiness_overclaim", path=f"{path}.{key}", value=value.get(key))
    targets = value.get("targets")
    if targets is None:
        return
    if not isinstance(targets, list):
        append_blocker(blockers, "beta_capture_targets_malformed", path=f"{path}.targets")
        return
    for index, entry in enumerate(targets):
        validate_beta_capture_entry(entry, blockers, f"{path}.targets[{index}]")


def manifest_target_key(entry: dict[str, Any]) -> str | None:
    outer = entry.get("outer")
    name = entry.get("name")
    if not isinstance(outer, str) or not isinstance(name, str) or not outer or not name:
        return None
    return f"{outer}.{name}"


def bound_fixture_path(snapshot_root: Path, sha_prefix: str, module: str, file_name: str) -> Path:
    return snapshot_root / sha_prefix / module / file_name


def load_fixture_manifest(
    snapshot_root: Path,
    expected_targets: set[str],
    blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest_path = snapshot_root / "manifest.json"
    safe_manifest = safe_path(manifest_path, "snapshot manifest", blockers)
    manifest_summary: dict[str, Any] = {
        "path": str(manifest_path),
        "schema": None,
        "source": None,
        "status": None,
        "sha256": None,
        "ark_binary_sha256": None,
        "sha_prefix": None,
        "target_count": 0,
        "sdk_buffs_target_count": 0,
        "bound_target_count": 0,
    }
    if safe_manifest is None:
        return manifest_summary, {}
    manifest_payload, manifest_sha256 = read_manifest_file(safe_manifest, blockers)
    if manifest_payload is None:
        return manifest_summary, {}

    manifest_summary.update(
        {
            "path": str(safe_manifest),
            "schema": manifest_payload.get("schema"),
            "source": manifest_payload.get("source"),
            "status": manifest_payload.get("status"),
            "sha256": manifest_sha256,
            "ark_binary_sha256": manifest_payload.get("ark_binary_sha256"),
            "sha_prefix": manifest_payload.get("sha_prefix"),
        }
    )
    if manifest_payload.get("schema") != SNAPSHOT_MANIFEST_SCHEMA:
        append_blocker(blockers, "manifest_schema_mismatch", value=manifest_payload.get("schema"))
    if manifest_payload.get("source") != "offline_core":
        append_blocker(blockers, "manifest_source_mismatch", value=manifest_payload.get("source"))
    if manifest_payload.get("status") != "candidate-only":
        append_blocker(blockers, "manifest_status_mismatch", value=manifest_payload.get("status"))
    ark_binary_sha256 = manifest_payload.get("ark_binary_sha256")
    if not isinstance(ark_binary_sha256, str) or SHA256_RE.fullmatch(ark_binary_sha256) is None:
        append_blocker(blockers, "manifest_ark_binary_sha256_malformed", value=ark_binary_sha256)
    sha_prefix = manifest_payload.get("sha_prefix")
    if not isinstance(sha_prefix, str) or not component_is_safe(sha_prefix):
        append_blocker(blockers, "manifest_sha_prefix_malformed", value=sha_prefix)
        sha_prefix = ""

    targets = manifest_payload.get("targets")
    if not isinstance(targets, list):
        append_blocker(blockers, "manifest_targets_malformed")
        return manifest_summary, {}
    manifest_summary["target_count"] = len(targets)

    seen_targets: set[str] = set()
    bound_entries: dict[str, dict[str, Any]] = {}
    root = snapshot_root.resolve()
    for index, entry in enumerate(targets):
        if not isinstance(entry, dict):
            append_blocker(blockers, "manifest_target_entry_malformed", index=index)
            continue
        target = manifest_target_key(entry)
        if target is None:
            append_blocker(blockers, "manifest_target_identity_malformed", index=index)
            continue
        module = entry.get("module")
        file_name = entry.get("file")
        if module == EXPECTED_FIXTURE_MODULE:
            manifest_summary["sdk_buffs_target_count"] += 1
        if target not in expected_targets:
            continue
        if target in seen_targets:
            append_blocker(blockers, "manifest_target_duplicate", target=target, index=index)
            continue
        seen_targets.add(target)
        if module != EXPECTED_FIXTURE_MODULE:
            append_blocker(blockers, "manifest_target_module_mismatch", target=target, value=module)
        if not isinstance(module, str) or not component_is_safe(module):
            append_blocker(blockers, "manifest_target_module_malformed", target=target, value=module)
            continue
        if not isinstance(file_name, str) or not component_is_safe(file_name):
            append_blocker(blockers, "manifest_target_file_malformed", target=target, value=file_name)
            continue
        expected_file = f"{target}.snapshot.json"
        if file_name != expected_file:
            append_blocker(
                blockers,
                "manifest_target_file_mismatch",
                target=target,
                expected=expected_file,
                value=file_name,
            )
        path = bound_fixture_path(snapshot_root, sha_prefix, module, file_name)
        safe_fixture = safe_path(path, f"manifest fixture {target}", blockers)
        if safe_fixture is None:
            continue
        try:
            safe_fixture.relative_to(root)
        except ValueError:
            append_blocker(
                blockers,
                "manifest_target_path_outside_root",
                target=target,
                path=str(safe_fixture),
            )
            continue
        bound_entries[target] = {
            "target": target,
            "outer": entry.get("outer"),
            "name": entry.get("name"),
            "module": module,
            "file": file_name,
            "path": str(safe_fixture),
            "fixture_path": relative_path(root, safe_fixture),
        }

    missing = sorted(expected_targets - set(bound_entries))
    if missing:
        append_blocker(blockers, "manifest_target_missing", missing=missing, module=EXPECTED_FIXTURE_MODULE)
    manifest_summary["bound_target_count"] = len(bound_entries)
    return manifest_summary, bound_entries


def first_target(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        append_blocker(blockers, "snapshot_target_count_mismatch", path=payload.get("_source_path"))
        return None
    return targets[0]


def load_snapshots(
    snapshot_root: Path,
    expected_targets: set[str],
    manifest_entries: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    snapshots: dict[str, dict[str, Any]] = {}
    if not snapshot_root.exists():
        append_blocker(blockers, "snapshot_root_missing", path=str(snapshot_root))
        return snapshots
    for path in sorted(snapshot_root.rglob("*.snapshot.json")):
        safe_snapshot = safe_path(path, "snapshot", blockers)
        if safe_snapshot is None:
            continue
        payload = read_json_file(safe_snapshot, blockers)
        if payload is None:
            continue
        target_payload = first_target(payload, blockers)
        if target_payload is None:
            continue
        key = target_key(target_payload)
        if key not in expected_targets:
            continue
        if key in snapshots:
            append_blocker(
                blockers,
                "duplicate_target_snapshot",
                target=key,
                first=snapshots[key].get("_source_path"),
                duplicate=str(path),
            )
        manifest_entry = manifest_entries.get(key)
        if manifest_entry is None:
            append_blocker(blockers, "snapshot_without_manifest_entry", target=key, path=str(path))
            continue
        bound_path = Path(manifest_entry["path"])
        if safe_snapshot != bound_path:
            append_blocker(
                blockers,
                "misplaced_target_snapshot",
                target=key,
                expected=manifest_entry["fixture_path"],
                actual=relative_path(snapshot_root.resolve(), safe_snapshot),
            )
            continue
        if key in snapshots:
            continue
        payload["_manifest_entry"] = manifest_entry
        snapshots[key] = payload
    return snapshots


def properties_for(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    target_payload = first_target(payload, blockers)
    if target_payload is None:
        return []
    chain = target_payload.get("property_chain")
    if not isinstance(chain, dict):
        append_blocker(blockers, "property_chain_missing", target=target_key(target_payload))
        return []
    properties = chain.get("properties")
    if not isinstance(properties, list) or not all(isinstance(item, dict) for item in properties):
        append_blocker(blockers, "property_chain_properties_malformed", target=target_key(target_payload))
        return []
    return properties


def validate_target_sets(blockers: list[dict[str, Any]]) -> tuple[dict[str, Any], set[str], dict[str, list[str]]]:
    expanded: dict[str, list[str]] = {}
    missing_target_sets: list[str] = []
    active_target_sets: list[str] = []
    expected_targets: set[str] = set()
    target_sets_by_target: dict[str, list[str]] = {}
    for target_set in TARGET_SETS_USED:
        entries = TARGET_SETS.get(target_set)
        if not isinstance(entries, tuple):
            expanded[target_set] = []
            missing_target_sets.append(target_set)
            continue
        targets = []
        for entry in entries:
            schema, _, target = entry.partition(":")
            if schema == SNAPSHOT_SCHEMA:
                targets.append(target)
        expanded[target_set] = targets
        active_target_sets.append(target_set)
        expected_for_set = EXPECTED_TARGETS_BY_SET[target_set]
        observed_for_set = set(targets)
        if observed_for_set != expected_for_set:
            append_blocker(
                blockers,
                "target_set_target_mismatch",
                target_set=target_set,
                missing=sorted(expected_for_set - observed_for_set),
                unexpected=sorted(observed_for_set - expected_for_set),
            )
        expected_targets.update(expected_for_set)
        for target in expected_for_set:
            target_sets_by_target.setdefault(target, []).append(target_set)
    if not active_target_sets:
        append_blocker(blockers, "buff_target_sets_missing", target_sets=list(TARGET_SETS_USED))
    summary = {
        "target_sets": list(TARGET_SETS_USED),
        "active_target_sets": active_target_sets,
        "missing_target_sets": missing_target_sets,
        "compact_targets": sorted(expanded["buff-compact-intake"]),
        "breadth_targets": sorted(expanded["buff-breadth-intake"]),
    }
    return summary, expected_targets, target_sets_by_target


def validate_snapshot_common(
    key: str,
    payload: dict[str, Any],
    manifest_summary: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        append_blocker(blockers, "snapshot_schema_mismatch", target=key, value=payload.get("schema"))
    source_sha = payload.get("_source_sha256")
    if not isinstance(source_sha, str) or SHA256_RE.fullmatch(source_sha) is None:
        append_blocker(blockers, "snapshot_sha256_malformed", target=key, value=source_sha)

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("status") != "candidate-only":
        append_blocker(blockers, "snapshot_evidence_status_mismatch", target=key)
    manifest_entry = payload.get("_manifest_entry")
    if not isinstance(manifest_entry, dict):
        append_blocker(blockers, "snapshot_manifest_binding_missing", target=key)
    elif manifest_entry.get("module") != EXPECTED_FIXTURE_MODULE:
        append_blocker(
            blockers,
            "snapshot_manifest_module_mismatch",
            target=key,
            value=manifest_entry.get("module"),
        )
    if isinstance(evidence, dict):
        if evidence.get("source") != "offline_core":
            append_blocker(blockers, "snapshot_evidence_source_mismatch", target=key, value=evidence.get("source"))
        if evidence.get("artifact_kind") != "offline_core":
            append_blocker(
                blockers,
                "snapshot_evidence_artifact_kind_mismatch",
                target=key,
                value=evidence.get("artifact_kind"),
            )
        ark_binary_sha256 = evidence.get("ark_binary_sha256")
        if not isinstance(ark_binary_sha256, str) or SHA256_RE.fullmatch(ark_binary_sha256) is None:
            append_blocker(
                blockers,
                "snapshot_evidence_ark_binary_sha256_malformed",
                target=key,
                value=ark_binary_sha256,
            )
        elif ark_binary_sha256 != manifest_summary.get("ark_binary_sha256"):
            append_blocker(
                blockers,
                "snapshot_manifest_ark_binary_sha256_mismatch",
                target=key,
                expected=manifest_summary.get("ark_binary_sha256"),
                value=ark_binary_sha256,
            )
    interpretation = payload.get("interpretation")
    if not isinstance(interpretation, dict) or interpretation.get("status") != "candidate-only":
        append_blocker(blockers, "snapshot_interpretation_status_mismatch", target=key)

    target_payload = first_target(payload, blockers)
    if target_payload is None:
        return
    if target_payload.get("status") != "candidate":
        append_blocker(blockers, "target_status_mismatch", target=key, value=target_payload.get("status"))
    membership = target_payload.get("membership")
    if not isinstance(membership, dict):
        append_blocker(blockers, "target_membership_missing", target=key)
    else:
        for field in ("class", "outer", "target"):
            if membership.get(field) != "candidate-uobject":
                append_blocker(
                    blockers,
                    "target_membership_mismatch",
                    target=key,
                    field=field,
                    value=membership.get(field),
                )

    chain = target_payload.get("property_chain")
    if not isinstance(chain, dict):
        append_blocker(blockers, "property_chain_missing", target=key)
        return
    properties = chain.get("properties")
    if not isinstance(properties, list):
        append_blocker(blockers, "property_chain_properties_malformed", target=key)
        return
    expected_count = chain.get("expected_count")
    observed_count = chain.get("observed_count")
    if expected_count != len(properties) or observed_count != len(properties):
        append_blocker(
            blockers,
            "property_chain_count_mismatch",
            target=key,
            expected_count=expected_count,
            observed_count=observed_count,
            property_count=len(properties),
        )
    if target_payload.get("num_parms") != len(properties):
        append_blocker(
            blockers,
            "num_parms_mismatch",
            target=key,
            num_parms=target_payload.get("num_parms"),
            property_count=len(properties),
        )


def validate_property_candidate(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if prop.get("status") != "candidate":
        append_blocker(blockers, "property_status_mismatch", target=target, field=field, value=prop.get("status"))
    for key in ("membership_status", "class_membership_status", "outer_membership_status"):
        if prop.get(key) != "candidate-uobject":
            append_blocker(blockers, "property_membership_mismatch", target=target, field=field, member=key)
    if prop.get("array_dim") != 1:
        append_blocker(blockers, "property_array_dim_mismatch", target=target, field=field, value=prop.get("array_dim"))


def validate_bool_field(field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    expected = {
        "bool_byte_offset": 0,
        "bool_field_size": 1,
        "element_size": 1,
        "field_mask": "0xff",
        "native_bool": False,
    }
    for key, expected_value in expected.items():
        if prop.get(key) != expected_value:
            append_blocker(
                blockers,
                "bool_scalar_metadata_mismatch",
                field=field,
                metadata_key=key,
                expected=expected_value,
                value=prop.get(key),
            )
    if not bool_mask_is_one(prop.get("byte_mask")):
        append_blocker(blockers, "bool_scalar_metadata_mismatch", field=field, metadata_key="byte_mask", value=prop.get("byte_mask"))
    semantics = prop.get("bool_property_semantics")
    if not isinstance(semantics, dict) or semantics.get("status") != "candidate":
        append_blocker(blockers, "bool_semantics_missing_or_not_candidate", field=field)


def validate_copied_bool(
    target: str,
    field: str,
    prop: dict[str, Any],
    expected_fields: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    spec = expected_fields[field]
    validate_property_candidate(target, field, prop, blockers)
    if prop.get("class_name") != "BoolProperty":
        append_blocker(blockers, "copied_bool_shape_mismatch", field=field, metadata_key="class_name", value=prop.get("class_name"))
    if prop.get("offset_internal") != spec["offset_internal"]:
        append_blocker(
            blockers,
            "copied_bool_shape_mismatch",
            field=field,
            metadata_key="offset_internal",
            expected=spec["offset_internal"],
            value=prop.get("offset_internal"),
        )
    validate_bool_field(field, prop, blockers)
    return {
        "copied_field": field,
        "direction": spec["direction"],
        "property_class": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "source_snapshot": target,
    }


def redact_field(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    validate_property_candidate(target, field, prop, blockers)
    class_name = prop.get("class_name")
    reason = EXPECTED_REDACTED_FIELDS.get(field) or "not_in_buff_scalar_allowlist"
    if field == "PrimalBuff.BuffOverrideInventoryAccessInput.InController" and class_name != "ObjectProperty":
        append_blocker(blockers, "controller_redaction_shape_mismatch", field=field, property_class=class_name)
    if field in {
        "PrimalBuff.BPCustomAllowAddBuff.forCharacter",
        "PrimalBuff.BPCustomAllowAddBuff.DamageCauser",
    } and class_name != "ObjectProperty":
        append_blocker(blockers, "character_or_damage_redaction_shape_mismatch", field=field, property_class=class_name)
    if field == "PrimalBuff.BPPreventAddingOtherBuff.anotherBuffClass" and class_name != "ClassProperty":
        append_blocker(blockers, "buff_class_redaction_shape_mismatch", field=field, property_class=class_name)
    return {
        "redacted_field": field,
        "reason": reason,
        "property_class": class_name,
        "source_snapshot": target,
    }


def validate_zero_param_target(target: str, snapshot: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    target_payload = first_target(snapshot, blockers)
    if target_payload is None:
        return {"target": target, "ready": False}
    chain = target_payload.get("property_chain") if isinstance(target_payload.get("property_chain"), dict) else {}
    properties = chain.get("properties") if isinstance(chain, dict) else None
    zero_param = (
        target_payload.get("num_parms") == 0
        and target_payload.get("parms_size") == 0
        and target_payload.get("return_value_offset") == "0xffff"
        and isinstance(properties, list)
        and len(properties) == 0
    )
    if not zero_param:
        append_blocker(
            blockers,
            "zero_param_lifecycle_shape_mismatch",
            target=target,
            num_parms=target_payload.get("num_parms"),
            parms_size=target_payload.get("parms_size"),
            return_value_offset=target_payload.get("return_value_offset"),
        )
    return {
        "target": target,
        "ready": zero_param,
        "zero_param": zero_param,
    }


def text_claim_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    before = text[clause_start:start]
    after = text[end : min(len(text), end + 80)]
    return bool(NEGATOR_RE.search(before) or AFTER_NEGATOR_RE.search(after))


def forbidden_text_claims(text: str) -> list[str]:
    claims: list[str] = []
    for regex in (FORBIDDEN_TEXT_CLAIM_RE, READY_TEXT_CLAIM_RE, CANDIDATE_CAPTURE_PROMOTION_RE):
        for match in regex.finditer(text):
            if text_claim_is_negated(text, match.start(), match.end()):
                continue
            claims.append(match.group(0))
    return sorted(set(claims))


def normalized_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_status_claim(value: Any) -> bool:
    if value is True or positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    normalized = normalized_claim_key(value).replace("_", "-")
    return (
        normalized in POSITIVE_STATUS_VALUES
        or normalized.endswith("-ready")
        or AFFIRMATIVE_STATUS_VALUE_RE.search(value) is not None
    )


def claim_context_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    if normalized == "accepted_for_internal_planning":
        return False
    return bool(FORBIDDEN_CLAIM_KEY_RE.search(key) or CLAIM_CONTEXT_KEY_RE.search(normalized))


def reject_forbidden_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str = "$",
    *,
    claim_context: bool = False,
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith("_"):
                continue
            key_lower = normalized_claim_key(key)
            child_context = claim_context or claim_context_key(key)
            if key_lower in FORBIDDEN_NONZERO_KEYS and child not in (False, None, 0, "0"):
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif key_lower in FORBIDDEN_READY_KEYS and not claim_value_is_false_or_zero(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif key_lower in {"source_accepted", "source_stable", "source_status"} and (
                positive_status_claim(child)
            ):
                append_blocker(blockers, "forbidden_text_claim", path=f"{path}.{key}", claim=f"{key}={child}")
            elif FORBIDDEN_CLAIM_KEY_RE.search(key) and child is True:
                append_blocker(blockers, "forbidden_positive_claim_key", path=f"{path}.{key}", value=child)
            elif child_context and ("progress" in key_lower or "credit" in key_lower) and positive_numeric_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif (
                child_context
                and key_lower in {"accepted", "allowed", "ready", "stable", "status", "unblocked", "unlocked"}
                and positive_status_claim(child)
            ):
                append_blocker(
                    blockers,
                    "forbidden_text_claim",
                    path=f"{path}.{key}",
                    claim=f"{key}={child}",
                )
            elif (
                FORBIDDEN_CLAIM_KEY_RE.search(key)
                and isinstance(child, str)
                and positive_status_claim(child)
            ):
                append_blocker(
                    blockers,
                    "forbidden_text_claim",
                    path=f"{path}.{key}",
                    claim=f"{key}={child}",
                )
            reject_forbidden_claims(child, blockers, f"{path}.{key}", claim_context=child_context)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_claims(child, blockers, f"{path}[{index}]", claim_context=claim_context)
        return
    if claim_context and positive_status_claim(value):
        append_blocker(blockers, "forbidden_readiness_claim", path=path, value=value)
        return
    if isinstance(value, str):
        for claim in forbidden_text_claims(value):
            append_blocker(blockers, "forbidden_text_claim", path=path, claim=claim)


def snapshot_source_binding(
    target: str,
    payload: dict[str, Any],
    target_sets_by_target: dict[str, list[str]],
) -> dict[str, Any]:
    manifest_entry = payload.get("_manifest_entry") if isinstance(payload.get("_manifest_entry"), dict) else {}
    evidence = payload.get("evidence") if isinstance(payload.get("evidence"), dict) else {}
    return {
        "target": target,
        "target_sets": sorted(target_sets_by_target.get(target, [])),
        "manifest_module": manifest_entry.get("module"),
        "manifest_file": manifest_entry.get("file"),
        "fixture_path": manifest_entry.get("fixture_path"),
        "source_snapshot_sha256": payload.get("_source_sha256"),
        "evidence_source": evidence.get("source"),
        "evidence_status": evidence.get("status"),
        "artifact_kind": evidence.get("artifact_kind"),
        "ark_binary_sha256": evidence.get("ark_binary_sha256"),
    }


def validate_snapshots(
    snapshots: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
    expected_targets: set[str],
    manifest_summary: dict[str, Any],
    target_sets_by_target: dict[str, list[str]],
) -> dict[str, Any]:
    for key, payload in snapshots.items():
        validate_snapshot_common(key, payload, manifest_summary, blockers)
        for beta_key in BETA_CAPTURE_ARTIFACT_KEYS:
            if beta_key in payload and isinstance(payload.get(beta_key), dict):
                validate_beta_capture_prep(payload.get(beta_key), blockers, path=f"$.snapshots.{key}.{beta_key}")
        blockers.extend(
            side_lane_fail_closed_source_artifact_issues(
                payload,
                expected_target_sets=TARGET_SETS_USED,
                path=f"$.snapshots.{key}",
            )
        )
        blockers.extend(
            side_lane_noncanonical_bool_payload_issues(
                payload,
                path=f"$.snapshots.{key}",
            )
        )
        reject_forbidden_claims(payload, blockers, path=f"$.snapshots.{key}")

    missing_required = sorted(expected_targets - set(snapshots))
    if missing_required:
        append_blocker(blockers, "required_target_snapshot_missing", missing=missing_required)

    copied_expected = expected_copied_bool_fields(expected_targets)
    redacted_expected = expected_redacted_fields(expected_targets)
    zero_param_expected = expected_zero_param_targets(expected_targets)
    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    observed_copied: set[str] = set()
    observed_redacted: set[str] = set()
    zero_param_targets: list[dict[str, Any]] = []
    source_bindings = [
        snapshot_source_binding(target, snapshots[target], target_sets_by_target)
        for target in sorted(expected_targets)
        if target in snapshots
    ]

    for target in sorted(expected_targets):
        payload = snapshots.get(target)
        if payload is None:
            continue
        if target in zero_param_expected:
            zero_param_targets.append(validate_zero_param_target(target, payload, blockers))
        for prop in properties_for(payload, blockers):
            field = property_key(target, prop)
            if field is None:
                append_blocker(blockers, "property_name_missing", target=target)
                continue
            if field in copied_expected:
                copied.append(validate_copied_bool(target, field, prop, copied_expected, blockers))
                observed_copied.add(field)
                continue
            if field in redacted_expected:
                redacted.append(redact_field(target, field, prop, blockers))
                observed_redacted.add(field)
                continue
            class_name = prop.get("class_name")
            if class_name in {"ObjectProperty", "ClassProperty", "ArrayProperty", "StrProperty", "TextProperty"} or BUFF_OBJECT_OR_CLASS_RE.search(field):
                append_blocker(blockers, "unexpected_buff_redaction_candidate", field=field, property_class=class_name)
            else:
                append_blocker(blockers, "unexpected_buff_scalar", field=field, property_class=class_name)

    missing_copied = sorted(set(copied_expected) - observed_copied)
    if missing_copied:
        append_blocker(blockers, "copied_bool_field_missing", missing=missing_copied)
    missing_redacted = sorted(set(redacted_expected) - observed_redacted)
    if missing_redacted:
        append_blocker(blockers, "required_redacted_field_missing", missing=missing_redacted)
    missing_zero_param = sorted(zero_param_expected - {entry["target"] for entry in zero_param_targets})
    if missing_zero_param:
        append_blocker(blockers, "zero_param_target_missing", missing=missing_zero_param)

    return {
        "source_bindings": source_bindings,
        "source_binding_count": len(source_bindings),
        "copied_bool_fields": sorted(entry["copied_field"] for entry in copied),
        "copied_bools": sorted(copied, key=lambda entry: entry["copied_field"]),
        "copied_bool_count": len(copied),
        "redacted_fields": sorted(entry["redacted_field"] for entry in redacted),
        "redactions": sorted(redacted, key=lambda entry: entry["redacted_field"]),
        "redacted_field_count": len(redacted),
        "zero_param_targets": sorted(zero_param_targets, key=lambda entry: entry["target"]),
        "compact_targets": sorted(EXPECTED_COMPACT_TARGETS & expected_targets),
        "breadth_targets": sorted(EXPECTED_BREADTH_TARGETS & expected_targets),
        "target_sets": sorted({target_set for sets in target_sets_by_target.values() for target_set in sets}),
    }


def build_report(snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    target_set_summary, expected_targets, target_sets_by_target = validate_target_sets(blockers)
    safe_snapshot_root = safe_path(snapshot_root, "--snapshot-root", blockers)
    source_manifest: dict[str, Any] = {
        "path": str(snapshot_root / "manifest.json"),
        "schema": None,
        "source": None,
        "status": None,
        "sha256": None,
        "ark_binary_sha256": None,
        "sha_prefix": None,
        "target_count": 0,
        "sdk_buffs_target_count": 0,
        "bound_target_count": 0,
    }
    snapshots: dict[str, dict[str, Any]] = {}
    if safe_snapshot_root is not None:
        source_manifest, manifest_entries = load_fixture_manifest(safe_snapshot_root, expected_targets, blockers)
        snapshots = load_snapshots(safe_snapshot_root, expected_targets, manifest_entries, blockers)
    summary = validate_snapshots(snapshots, blockers, expected_targets, source_manifest, target_sets_by_target)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "artifact_status": "candidate-only",
        "readiness_classification": "internal_layout_only",
        "candidate_only": True,
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "fixture_only": True,
        "not_artifact_gate": True,
        "current_sdk_blocker": CURRENT_SDK_BLOCKER,
        "next_blocker": CURRENT_SDK_BLOCKER,
        "remaining_blockers": [CURRENT_SDK_BLOCKER],
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_ready": False,
        "player_principal_runtime_evidence_ready": False,
        "clears_approved_runtime_evidence_missing": False,
        "approved_runtime_evidence_missing_cleared": False,
        "counts_as_approved_runtime_evidence": False,
        "replaces_player_principal_evidence": False,
        "target_sets": target_set_summary,
        "source_manifest": source_manifest,
        "snapshot_root": str(snapshot_root),
        "checked_targets": sorted(snapshots),
        "summary": summary,
        "beta_capture_prep": build_beta_capture_prep(expected_targets, target_sets_by_target),
        "buff_status_candidate_ready": ready,
        "copied_bool_boundary_ready": ready,
        "class_object_redaction_ready": ready,
        "zero_param_lifecycle_shape_ready": ready,
        "copied_payload_policy_ready": False,
        "lifecycle_semantics_ready": False,
        "buff_sdk_ready": False,
        "buff_status_sdk_ready": False,
        "public_buff_status_sdk_ready": False,
        "buff_public_module_ready": False,
        "buff_public_module_sdk_ready": False,
        "public_buff_module_ready": False,
        "buff_status_public_abi_ready": False,
        "buff_status_public_c_abi_ready": False,
        "buff_status_callback_ready": False,
        "buff_status_sdk_available": False,
        "sdk_ready": False,
        "module_sdk_ready": False,
        "public_sdk_ready": False,
        "public_buff_sdk_ready": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_callback_ready": False,
        "public_descriptor_ready": False,
        "public_capability_ready": False,
        "public_module_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "runtime_hook_ready": False,
        "runtime_wiring_ready": False,
        "runtime_observer_approved": False,
        "live_ops_ready": False,
        "dispatcher_ready": False,
        "callback_ready": False,
        "descriptor_ready": False,
        "capability_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "candidate_capture_evidence_ready": False,
        "debug_capture_evidence_ready": False,
        "candidate_capture_progress_contribution": 0,
        "v1_accounted": False,
        "v1_completion": False,
        "v1_completion_ready": False,
        "v1_completion_contribution": 0,
        "complete_sdk_ready": False,
        "stable_claim_allowed": False,
        "complete_sdk_claim_allowed": False,
        "counts_toward_complete_sdk_claim": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_ready": False,
        "p0_dependency_chain_accounted": False,
        "p0_dependency_chain_ready": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "promotion_ready": False,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "candidate/debug captures before checker acceptance are non-evidence and non-progress",
            "beta capture prep is future target planning only and is not approved runtime evidence",
            "buff beta capture prep does not clear approved_runtime_evidence_missing or replace player-principal lifecycle evidence",
            "no public Buff/status SDK, public C ABI, public runtime API, or v1 completion",
            "no complete SDK or P0 dependency-chain claim contribution",
            "no Buff public module, public Buff module SDK, or public Buff/status ABI readiness",
            "no runtime hook wiring, observer window, dispatcher wiring, or server validation",
            "no buff identity, controller/character/damage-causer/class exposure, lookup, or ResourceHandle",
            "no copied payload policy, lifecycle semantics, stacking semantics, invalidation semantics, mutation, return override, aggregate, proximity, count, or UE function call",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
