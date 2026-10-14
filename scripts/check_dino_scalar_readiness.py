#!/usr/bin/env python3
"""Read-only readiness check for the internal Dino scalar-only lane."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import build_redacted_ufunction_signatures as signature_builder
from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    NON_AUTHORIZING_READY_SCOPE,
    side_lane_noncanonical_bool_payload_issues,
    side_lane_fail_closed_source_artifact_issues,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.dino-scalar-readiness-check.v1"
TARGET_SET = "dino-compact-intake"
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
EXPECTED_INPUT_TARGETS = {
    "PrimalDinoCharacter.AddPassenger",
    "PrimalDinoCharacter.AllowCarryCharacter",
}
EXPECTED_COPIED_FIELDS = {
    "PrimalDinoCharacter.AddPassenger.PassengerSeatIndex",
    "PrimalDinoCharacter.AddPassenger.bForcePassenger",
    "PrimalDinoCharacter.AddPassenger.bAllowFlyersAndWaterDinos",
    "PrimalDinoCharacter.AddPassenger.bSkipLineTrace",
}
EXPECTED_REDACTED_FIELDS = {
    "PrimalDinoCharacter.AddPassenger.ACharacter",
    "PrimalDinoCharacter.AllowCarryCharacter.CanCarryPawn",
}
EXPECTED_EXCLUDED_FIELDS = {
    "PrimalDinoCharacter.AddPassenger.ReturnValue",
    "PrimalDinoCharacter.AllowCarryCharacter.ReturnValue",
}
EXPECTED_LAYOUT_SCALAR_FIELDS = EXPECTED_COPIED_FIELDS | EXPECTED_EXCLUDED_FIELDS
EXPECTED_DESCRIPTORS = {
    "dino_character.add_passenger",
    "dino_character.allow_carry_character",
}
BETA_CAPTURE_STATUS = "future_capture_targets_only"
BETA_CAPTURE_TARGET_STATUS = "future_capture_target"
BETA_CAPTURE_GATE = "dedicated_beta_capture_check_required"
BETA_CAPTURE_SURFACE = "dino"
BETA_CAPTURE_FALSE_OR_ZERO_FIELDS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "candidate_capture_ready",
    "clears_approved_runtime_evidence_missing",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "debug_capture_ready",
    "evidence_bundle_accepted",
    "mutation_authority_ready",
    "public_sdk_ready",
    "public_dino_sdk_ready",
    "resolves_approved_runtime_evidence_missing",
    "runtime_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_work_authorized",
    "sdk_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "server_work_authorized",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "replaces_player_principal_evidence",
    "player_principal_replacement_ready",
)
APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER = "approved_runtime_evidence_missing"
APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE = "approved_runtime_principal_lifecycle_evidence_bundle"
RUNTIME_EVIDENCE_MISSING_TRUE_KEYS = {
    "approved_player_principal_runtime_evidence_missing",
    "approved_runtime_evidence_missing",
    "approved_runtime_principal_lifecycle_evidence_missing",
    "player_principal_lifecycle_runtime_evidence_missing",
    "player_principal_runtime_evidence_missing",
    "runtime_evidence_missing",
}
RUNTIME_EVIDENCE_CLEARANCE_KEYS = {
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "clears_approved_runtime_evidence_missing",
    "resolves_approved_runtime_evidence_missing",
}
RUNTIME_EVIDENCE_BLOCKER_KEYS = {
    "active_completion_blocker",
    "current_blocker",
    "current_route_blocker",
    "primary_blocker",
    "prior_blocker",
    "required_blocker",
    "route_current_blocker",
}
RUNTIME_EVIDENCE_BLOCKER_LIST_KEYS = {
    "remaining_route_blockers",
    "route_remaining_blockers",
}
RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KEYS = {
    "next_required_artifact",
    "required_artifact",
    "required_first_artifact",
    "required_next_artifact",
}
MULTI_SURFACE_BETA_CAPTURE_CONTEXT_MARKERS = (
    "beta_capture_pack",
    "beta_capture_plan",
    "beta_capture_queue",
    "multi_surface_beta_capture",
    "multi_surface_candidate_queue",
)
REQUIRED_SOURCE_FILES = (
    "ue/DinoReflection.cpp",
    "ue/DinoReflection.h",
    "hooks/ProcessEventDinoReflection.cpp",
    "hooks/ProcessEventDinoReflection.h",
    "tests/core/DinoReflectionTests.cpp",
    "tests/core/ProcessEventDinoReflectionTests.cpp",
    "docs/research/2026-05-31-dino-scalar-policy-planning.md",
)
BLOCKED_PUBLIC_PREFIXES = (
    "include/obelisk/",
    "plugins/",
    "runtime/",
    "loader/",
)
BLOCKED_PUBLIC_PATHS = {
    "core/EventManager.cpp",
    "core/EventManager.h",
    "core/PluginManager.cpp",
    "core/PluginManager.h",
}
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"}
PUBLIC_DINO_TOKEN_RE = re.compile(r"\b(?:DinoScalar|CopiedDino|DinoReflection|DinoEvent|DinoSdk|DinoSDK)\b")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
POSITIVE_PROGRESS_RATIO_RE = re.compile(r"^\s*[1-9][0-9]*\s*/\s*[1-9][0-9]*\s*$")
FORBIDDEN_READY_KEYS = {
    "abi_ready",
    "callback_ready",
    "capability_ready",
    "beta_capture_ready",
    "candidate_capture_ready",
    "complete_sdk_claim_allowed",
    "complete_sdk_claim_progress_contribution",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "descriptor_ready",
    "dino_sdk_ready",
    "debug_capture_ready",
    "dispatcher_ready",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "identity_ready",
    "live_ops_ready",
    "lookup_ready",
    "mutation_authority_ready",
    "module_sdk_ready",
    "mutation_ready",
    "package_shape_passed",
    "package_shape_ready",
    "p0_dependency_chain_accounted",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_ready",
    "plugin_hub_ready",
    "promotion_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_callback_ready",
    "public_dino_sdk_ready",
    "public_module_ready",
    "public_or_runtime_accounting_allowed",
    "public_sdk_ready",
    "replaces_player_principal_evidence",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_hook_ready",
    "runtime_observer_approved",
    "runtime_ready",
    "runtime_work_authorized",
    "runtime_wiring_ready",
    "sdk_ready",
    "server_work_authorized",
    "source_readiness",
    "source_ready",
    "player_principal_replacement_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "support_tier_active",
    "support_tier_ready",
    "support_tier_supported",
    "v1_accounted",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:resource[_-]?handle|return[_-]?override|public[_-]?(?:sdk|api|abi|surface|module|callback|descriptor|capability)|"
    r"(?:module[_-]?sdk|callback|descriptor|capability|dispatcher)[_-]?ready|"
    r"approved[_-]?runtime[_-]?evidence[_-]?(?:accepted|present|ready)|"
    r"(?:beta|candidate|debug)[_-]?capture[_-]?(?:accepted|approved|enabled|progress|ready|runtime|sdk)|"
    r"runtime[_-]?(?:ready|hook|observer|wiring|capture|evidence|work)|live[_-]?ops|"
    r"package[_-]?shape|plugin[_-]?hub|support[_-]?tier|"
    r"v1[_-]?(?:ready|complete|completion|accounted)|"
    r"(?:complete|stable)[_-]?sdk[_-]?claim|counts[_-]?toward|p0[_-]?dependency[_-]?chain|"
    r"(?:replace|replaces|replacement|supersede|supersedes|supersession)[_-]?(?:player[_-]?principal|principal)|"
    r"player[_-]?principal[_-]?(?:evidence[_-]?)?(?:replacement|replaced|satisfied|ready)|"
    r"lookup[_-]?ready|mutation[_-]?ready|identity[_-]?ready)",
    re.IGNORECASE,
)
CLAIM_CONTEXT_KEY_RE = re.compile(
    r"(?:public|sdk|api|abi|module|callback|descriptor|capability|runtime|debug|beta|live[_-]?ops|"
    r"capture|source|v1|p0|complete|completion|stable|promotion|resource[_-]?handle|"
    r"package[_-]?shape|plugin[_-]?hub|support[_-]?tier|"
    r"approved[_-]?runtime[_-]?evidence|blocker|route|"
    r"return[_-]?override|identity|lookup|mutation|player[_-]?principal|principal|replacement|replace)",
    re.IGNORECASE,
)
POSITIVE_STATUS_VALUES = frozenset(
    {
        "accepted",
        "active",
        "available",
        "allowed",
        "approved",
        "complete",
        "completed",
        "enabled",
        "passed",
        "promoted",
        "public",
        "published",
        "ready",
        "release-ready",
        "release-supported",
        "runtime-ready",
        "sdk-ready",
        "stable",
        "stable-ready",
        "supported",
        "unblocked",
        "unlocked",
        "validated",
        "v1-ready",
    }
)
FORBIDDEN_TEXT_CLAIM_RE = re.compile(
    r"\bDino\s+(?:SDK|API|module|callback|callbacks|descriptor|descriptors|capability|capabilities|C\s+ABI|ABI)\b|"
    r"\bpublic\s+(?:Dino\s+)?(?:SDK|API|ABI|C\s+ABI|module|callback|descriptor|capability)\b|"
    r"\bruntime\s+(?:observer|hook|wiring|dispatch|dispatcher|callback|capture)\b|"
    r"\bidentity\b|\blookup\b|\bmutation\b|\breturn[- ]override\b|"
    r"\bResourceHandle\b|\bResource\s+Handle\b|"
    r"\b(?:replace[sd]?|supersede[sd]?|substitute[sd]?|satisf(?:y|ies|ied)|stand(?:s)?\s+in\s+for)\s+"
    r"(?:approved\s+)?(?:runtime\s+)?player[-_ ]principal(?:\s+lifecycle)?\s+evidence\b|"
    r"\bplayer[-_ ]principal(?:\s+lifecycle)?\s+evidence\s+"
    r"(?:is\s+)?(?:replaced|satisfied|superseded)\b|"
    r"\bv1\s+(?:completion|complete|ready|release|promotion|accounted|unblocked|unlocked)\b",
    re.IGNORECASE,
)
READY_TEXT_CLAIM_RE = re.compile(
    r"\b(?:Dino\s+SDK|public\s+SDK|public\s+ABI|runtime|runtime\s+observer|runtime\s+hook|"
    r"module\s+SDK|promotion|v1|v1\s+SDK)\s+"
    r"(?:is\s+|are\s+)?(?:ready|complete|completion|available|published|enabled|approved|allowed|unblocked|unlocked)\b|"
    r"\b(?:ready|complete|available|enabled|allowed|unblocked|unlocked)\s+for\s+v1\b|"
    r"\bv1(?:\.0)?\s+(?:is\s+)?(?:stable|complete|completion|ready|allowed|unblocked|unlocked)\b|"
    r"\b(?:counts?|contributes?|credits?)\s+(?:toward|for|to)\s+(?:the\s+)?"
    r"(?:complete|full|production|public|v1)\s+SDK\s+claim\b|"
    r"\b(?:package[- ]?shape|Plugin Hub|plugin[- ]?hub|support[- ]?tier)\s+"
    r"(?:is\s+)?(?:accepted|active|approved|available|enabled|passed|promoted|public|"
    r"published|ready|release[- ]supported|stable|supported|unblocked|unlocked|validated)\b",
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|excludes?|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1|false|redacted|candidate-only)\b",
    re.IGNORECASE,
)
NEUTRAL_METADATA_CONTEXT_KEYS = {
    "artifact_identity",
    "ark_binary_sha256",
    "array_dim",
    "bool_byte_offset",
    "bool_field_size",
    "byte_mask",
    "copied_field",
    "copied_scalars",
    "descriptor",
    "descriptor_count",
    "descriptor_preflight",
    "descriptors",
    "direction",
    "element_size",
    "evidence_status",
    "excluded_field",
    "excluded_object_refs",
    "field_mask",
    "generated_from",
    "input_snapshots",
    "native_bool",
    "num_parms",
    "offset_internal",
    "parms_size",
    "path_redacted",
    "property_class",
    "promotion_blocker_count_total",
    "promotion_blockers_by_reason",
    "safety_summary",
    "source_artifact_ids",
    "source_snapshot",
    "source_snapshot_sha256",
    "snapshot_schema",
    "target",
    "target_set_coverage",
    "target_set_revision",
    "type",
}
NEGATIVE_TEXT_CLAIM_PATH_PREFIXES = (
    "$.descriptor_preflight.explicitly_not_assigned[",
    "$.descriptor_preflight.safety_summary.explicitly_excluded[",
    "$.safety_summary.not_promoted_surfaces[",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Dino scalar-only candidate readiness without promoting a public Dino SDK."
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="Repository root to scan.")
    parser.add_argument("--report", type=Path, help="Existing redacted UFunction signature report JSON.")
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="Snapshot root used when --report is not provided.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        append_blocker(blockers, "path_rejected", label=label, path=str(path), detail=str(exc))
        return None


def claim_value_is_false_or_zero(value: Any) -> bool:
    return value is False or value is None or value == 0


def field_target(field: str) -> str:
    return field.rsplit(".", 1)[0]


def runtime_evidence_blocker_non_claims() -> dict[str, Any]:
    return {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_missing": True,
        "approved_runtime_evidence_missing_cleared": False,
        "approved_runtime_evidence_missing_resolved": False,
        "clears_approved_runtime_evidence_missing": False,
        "resolves_approved_runtime_evidence_missing": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "current_route_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "remaining_route_blockers": [APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER],
        "prior_blocker": APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER,
        "required_first_artifact": APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE,
    }


def build_beta_capture_prep() -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    for target in sorted(EXPECTED_INPUT_TARGETS):
        targets.append(
            {
                "target": target,
                "surface": BETA_CAPTURE_SURFACE,
                "target_set": TARGET_SET,
                "status": BETA_CAPTURE_TARGET_STATUS,
                "source_evidence": "candidate_only_sanitized_redacted_signature",
                "capture_gate": BETA_CAPTURE_GATE,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "runtime_capture_ready": False,
                "sdk_ready": False,
                "sdk_progress": 0,
                "replaces_player_principal_evidence": False,
                **runtime_evidence_blocker_non_claims(),
                "copied_scalar_fields": sorted(
                    field for field in EXPECTED_COPIED_FIELDS if field_target(field) == target
                ),
                "deferred_return_fields": sorted(
                    field for field in EXPECTED_EXCLUDED_FIELDS if field_target(field) == target
                ),
                "redacted_fields": sorted(
                    field for field in EXPECTED_REDACTED_FIELDS if field_target(field) == target
                ),
            }
        )
    return {
        "status": BETA_CAPTURE_STATUS,
        "surface": BETA_CAPTURE_SURFACE,
        "target_set": TARGET_SET,
        "source_evidence": "candidate_only_sanitized_redacted_signatures",
        "capture_gate": BETA_CAPTURE_GATE,
        "public_sdk_ready": False,
        "public_dino_sdk_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "debug_capture_ready": False,
        "sdk_ready": False,
        "sdk_progress": 0,
        "replaces_player_principal_evidence": False,
        **runtime_evidence_blocker_non_claims(),
        "targets": targets,
        "non_claims": [
            "future beta/debug capture target planning only",
            "dedicated beta capture acceptance check is required before runtime use",
            "does not replace player-principal lifecycle evidence",
        ],
    }


def validate_beta_capture_entry(entry: Any, blockers: list[dict[str, Any]], index: int) -> str | None:
    if not isinstance(entry, dict):
        append_blocker(blockers, "beta_capture_target_malformed", index=index)
        return None
    target = entry.get("target")
    if not isinstance(target, str) or target not in EXPECTED_INPUT_TARGETS:
        append_blocker(blockers, "beta_capture_target_mismatch", index=index, target=target)
    if entry.get("surface") != BETA_CAPTURE_SURFACE:
        append_blocker(blockers, "beta_capture_surface_mismatch", index=index, value=entry.get("surface"))
    if entry.get("target_set") != TARGET_SET:
        append_blocker(blockers, "beta_capture_target_set_mismatch", index=index, value=entry.get("target_set"))
    if entry.get("status") not in {BETA_CAPTURE_TARGET_STATUS, None}:
        append_blocker(blockers, "beta_capture_target_status_mismatch", index=index, value=entry.get("status"))
    if entry.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_gate_mismatch", index=index, value=entry.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in entry and not claim_value_is_false_or_zero(entry.get(key)):
            append_blocker(blockers, "beta_capture_readiness_overclaim", index=index, field=key, value=entry.get(key))
    return target if isinstance(target, str) else None


def validate_beta_capture_prep(value: Any, blockers: list[dict[str, Any]]) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        append_blocker(blockers, "beta_capture_prep_malformed")
        return
    if value.get("status") != BETA_CAPTURE_STATUS:
        append_blocker(blockers, "beta_capture_prep_status_mismatch", value=value.get("status"))
    if value.get("surface") not in {BETA_CAPTURE_SURFACE, None}:
        append_blocker(blockers, "beta_capture_prep_surface_mismatch", value=value.get("surface"))
    if value.get("target_set") != TARGET_SET:
        append_blocker(blockers, "beta_capture_prep_target_set_mismatch", value=value.get("target_set"))
    if value.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_prep_gate_mismatch", value=value.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in value and not claim_value_is_false_or_zero(value.get(key)):
            append_blocker(blockers, "beta_capture_readiness_overclaim", field=key, value=value.get(key))
    targets = value.get("targets")
    if not isinstance(targets, list):
        append_blocker(blockers, "beta_capture_targets_missing")
        return
    observed = {
        target
        for index, entry in enumerate(targets)
        if (target := validate_beta_capture_entry(entry, blockers, index)) in EXPECTED_INPUT_TARGETS
    }
    if observed != EXPECTED_INPUT_TARGETS:
        append_blocker(
            blockers,
            "beta_capture_target_coverage_mismatch",
            missing=sorted(EXPECTED_INPUT_TARGETS - observed),
            unexpected=sorted(observed - EXPECTED_INPUT_TARGETS),
        )


def normalized_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def positive_numeric_claim(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def positive_progress_claim(value: Any) -> bool:
    return positive_numeric_claim(value) or (
        isinstance(value, str) and POSITIVE_PROGRESS_RATIO_RE.fullmatch(value) is not None
    )


def positive_status_claim(value: Any) -> bool:
    if value is True or positive_numeric_claim(value):
        return True
    if not isinstance(value, str):
        return False
    normalized = normalized_claim_key(value).replace("_", "-")
    return normalized in POSITIVE_STATUS_VALUES or normalized.endswith("-ready")


def runtime_evidence_missing_value_preserved(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return normalized_claim_key(value) == APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
    return False


def runtime_evidence_blocker_value_preserved(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_key(value) == APPROVED_RUNTIME_EVIDENCE_MISSING_BLOCKER
    if isinstance(value, list):
        return any(runtime_evidence_blocker_value_preserved(item) for item in value)
    return False


def runtime_evidence_required_artifact_preserved(value: Any) -> bool:
    return isinstance(value, str) and normalized_claim_key(value) == APPROVED_RUNTIME_PRINCIPAL_LIFECYCLE_BUNDLE


def beta_capture_artifact_context(value: dict[str, Any]) -> bool:
    for key, child in value.items():
        normalized_key = normalized_claim_key(key)
        if any(marker in normalized_key for marker in MULTI_SURFACE_BETA_CAPTURE_CONTEXT_MARKERS):
            return True
        if isinstance(child, str):
            normalized_value = normalized_claim_key(child)
            if any(marker in normalized_value for marker in MULTI_SURFACE_BETA_CAPTURE_CONTEXT_MARKERS):
                return True
    return False


def text_claim_is_negated(text: str, start: int, end: int) -> bool:
    clause_start = max(text.rfind(".", 0, start), text.rfind("\n", 0, start), text.rfind(";", 0, start)) + 1
    before = text[clause_start:start]
    after = text[end : min(len(text), end + 80)]
    return bool(NEGATOR_RE.search(before) or AFTER_NEGATOR_RE.search(after))


def forbidden_text_claims(text: str) -> list[str]:
    claims: list[str] = []
    for regex in (FORBIDDEN_TEXT_CLAIM_RE, READY_TEXT_CLAIM_RE):
        for match in regex.finditer(text):
            if text_claim_is_negated(text, match.start(), match.end()):
                continue
            claims.append(match.group(0))
    return sorted(set(claims))


def claim_context_key(key: str) -> bool:
    normalized = normalized_claim_key(key)
    if normalized in {"accepted_for_internal_planning", "accepted_for_candidate_review"}:
        return False
    if normalized in NEUTRAL_METADATA_CONTEXT_KEYS:
        return False
    return bool(FORBIDDEN_CLAIM_KEY_RE.search(key) or CLAIM_CONTEXT_KEY_RE.search(normalized))


def neutral_positive_metadata_path(path: str, key: str) -> bool:
    if path.startswith("$.target_set_coverage") and key == "complete":
        return True
    if path == "$.safety_summary.promotion_blocker_count_total":
        return True
    if path.startswith("$.safety_summary.promotion_blockers_by_reason."):
        return True
    if path == "$.descriptor_preflight.descriptor_count":
        return True
    if path.startswith("$.descriptor_preflight.safety_summary.") and key.endswith("_count"):
        return True
    if path == "$.artifact_identity.path_redacted":
        return True
    return False


def reject_forbidden_claims(
    value: Any,
    blockers: list[dict[str, Any]],
    path: str = "$",
    *,
    claim_context: bool = False,
) -> None:
    if isinstance(value, dict):
        local_context = claim_context or beta_capture_artifact_context(value)
        for key, child in value.items():
            if key.startswith("_"):
                continue
            key_lower = normalized_claim_key(key)
            child_path = f"{path}.{key}"
            child_context = local_context or claim_context_key(key)
            neutral_metadata = neutral_positive_metadata_path(child_path, key_lower)
            preserved_runtime_missing = (
                key_lower in RUNTIME_EVIDENCE_MISSING_TRUE_KEYS
                and runtime_evidence_missing_value_preserved(child)
            )
            if key_lower in RUNTIME_EVIDENCE_MISSING_TRUE_KEYS and not runtime_evidence_missing_value_preserved(child):
                append_blocker(blockers, "approved_runtime_evidence_missing_not_preserved", path=child_path, value=child)
            elif key_lower in RUNTIME_EVIDENCE_CLEARANCE_KEYS and not claim_value_is_false_or_zero(child):
                append_blocker(blockers, "approved_runtime_evidence_missing_clearance_overclaim", path=child_path, value=child)
            elif key_lower in RUNTIME_EVIDENCE_BLOCKER_KEYS and not runtime_evidence_blocker_value_preserved(child):
                append_blocker(blockers, "approved_runtime_evidence_missing_not_preserved", path=child_path, value=child)
            elif key_lower in RUNTIME_EVIDENCE_BLOCKER_LIST_KEYS and not runtime_evidence_blocker_value_preserved(child):
                append_blocker(blockers, "approved_runtime_evidence_missing_not_preserved", path=child_path, value=child)
            elif key_lower in RUNTIME_EVIDENCE_REQUIRED_ARTIFACT_KEYS and not runtime_evidence_required_artifact_preserved(child):
                append_blocker(blockers, "required_runtime_evidence_artifact_mismatch", path=child_path, value=child)
            elif not preserved_runtime_missing and key_lower in FORBIDDEN_READY_KEYS and not claim_value_is_false_or_zero(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif not preserved_runtime_missing and not neutral_metadata and FORBIDDEN_CLAIM_KEY_RE.search(key) and child is True:
                append_blocker(blockers, "forbidden_positive_claim_key", path=child_path, value=child)
            elif key_lower in {"source_accepted", "source_stable", "source_status"} and positive_status_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif (
                not neutral_metadata
                and child_context
                and ("progress" in key_lower or "credit" in key_lower or "ratio" in key_lower)
                and positive_progress_claim(child)
            ):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif (
                not neutral_metadata
                and child_context
                and key_lower in {"accepted", "allowed", "ready", "stable", "status", "unblocked", "unlocked"}
                and positive_status_claim(child)
            ):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif not neutral_metadata and child_context and isinstance(child, str) and positive_status_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            reject_forbidden_claims(
                child,
                blockers,
                child_path,
                claim_context=child_context and not neutral_metadata and not preserved_runtime_missing,
            )
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_claims(child, blockers, f"{path}[{index}]", claim_context=claim_context)
        return
    if claim_context and positive_status_claim(value):
        append_blocker(blockers, "forbidden_readiness_claim", path=path, value=value)
        return
    if isinstance(value, str):
        if path.startswith(NEGATIVE_TEXT_CLAIM_PATH_PREFIXES):
            return
        for claim in forbidden_text_claims(value):
            append_blocker(blockers, "forbidden_text_claim", path=path, claim=claim)


def read_text(repo_root: Path, relative: str, blockers: list[dict[str, Any]]) -> str:
    path = repo_root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        append_blocker(blockers, "required_file_unreadable", path=relative, detail=str(exc))
        return ""


def require_tokens(blockers: list[dict[str, Any]], *, source: str, relative: str, tokens: list[str]) -> None:
    for token in tokens:
        if token not in source:
            append_blocker(blockers, "required_source_token_missing", path=relative, token=token)


def validate_target_set(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    source = read_text(repo_root, "scripts/reflection_target_sets.py", blockers)
    missing_targets = sorted(target for target in EXPECTED_INPUT_TARGETS if target not in source)
    if f'"{TARGET_SET}"' not in source:
        append_blocker(blockers, "target_set_missing", target_set=TARGET_SET)
    if missing_targets:
        append_blocker(blockers, "target_set_target_missing", target_set=TARGET_SET, missing=missing_targets)
    return {
        "target_set": TARGET_SET,
        "input_targets": sorted(EXPECTED_INPUT_TARGETS),
        "missing_targets": missing_targets,
    }


def load_signature_report(report_path: Path | None, snapshot_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if report_path is not None:
        try:
            payload = json.loads(report_path.read_text(encoding="utf-8"))
        except OSError as exc:
            append_blocker(blockers, "report_unreadable", path=str(report_path), detail=str(exc))
            return {}
        except json.JSONDecodeError as exc:
            append_blocker(blockers, "report_malformed", path=str(report_path), detail=str(exc))
            return {}
        if not isinstance(payload, dict):
            append_blocker(blockers, "report_not_object", path=str(report_path))
            return {}
        try:
            rebuilt = signature_builder.build_report(snapshot_root=snapshot_root, target_sets=[TARGET_SET])
        except SystemExit as exc:
            append_blocker(blockers, "report_source_snapshot_revalidation_failed", detail=str(exc))
            return payload
        for key in ("generated_from", "descriptor_preflight"):
            if payload.get(key) != rebuilt.get(key):
                append_blocker(blockers, "report_source_snapshot_revalidation_mismatch", section=key)
        return payload
    try:
        return signature_builder.build_report(snapshot_root=snapshot_root, target_sets=[TARGET_SET])
    except SystemExit as exc:
        append_blocker(blockers, "signature_report_build_failed", detail=str(exc))
        return {}


def validate_signature_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    blockers.extend(
        side_lane_fail_closed_source_artifact_issues(
            report,
            expected_target_sets=(TARGET_SET,),
        )
    )
    blockers.extend(side_lane_noncanonical_bool_payload_issues(report))
    reject_forbidden_claims(report, blockers)
    validate_beta_capture_prep(report.get("beta_capture_prep"), blockers)

    if report.get("schema") != "obelisk.redacted-ufunction-signatures.v1":
        append_blocker(blockers, "schema_mismatch", value=report.get("schema"))
    preflight = report.get("descriptor_preflight")
    if not isinstance(preflight, dict):
        append_blocker(blockers, "descriptor_preflight_missing")
        preflight = {}
    if preflight.get("status") != "internal-evidence-only":
        append_blocker(blockers, "descriptor_preflight_status_mismatch", value=preflight.get("status"))
    if preflight.get("scope") != TARGET_SET:
        append_blocker(blockers, "descriptor_preflight_scope_mismatch", value=preflight.get("scope"))
    if preflight.get("descriptor_count") != 2:
        append_blocker(blockers, "descriptor_count_mismatch", value=preflight.get("descriptor_count"))
    for key in ("assigned_resource_kind", "assigned_event_kind", "assigned_event_kind_mask"):
        if preflight.get(key) is not None:
            append_blocker(blockers, "assigned_resource_or_event_kind", field=key, value=preflight.get(key))
    for key in ("promotion_ready", "public_promotion", "public_surface"):
        if preflight.get(key) is not False:
            append_blocker(blockers, "public_surface_overclaim", field=key, value=preflight.get(key))

    descriptors = preflight.get("descriptors")
    if not isinstance(descriptors, list):
        append_blocker(blockers, "descriptors_missing")
        descriptors = []
    descriptor_names = {entry.get("descriptor") for entry in descriptors if isinstance(entry, dict)}
    if descriptor_names != EXPECTED_DESCRIPTORS:
        append_blocker(
            blockers,
            "descriptor_coverage_mismatch",
            missing=sorted(EXPECTED_DESCRIPTORS - descriptor_names),
            unexpected=sorted(name for name in descriptor_names - EXPECTED_DESCRIPTORS if isinstance(name, str)),
        )
    descriptor_targets = {entry.get("target") for entry in descriptors if isinstance(entry, dict)}
    if descriptor_targets != EXPECTED_INPUT_TARGETS:
        append_blocker(
            blockers,
            "target_coverage_mismatch",
            missing=sorted(EXPECTED_INPUT_TARGETS - descriptor_targets),
            unexpected=sorted(target for target in descriptor_targets - EXPECTED_INPUT_TARGETS if isinstance(target, str)),
        )
    for index, descriptor in enumerate(descriptors):
        if not isinstance(descriptor, dict):
            append_blocker(blockers, "descriptor_not_object", index=index)
            continue
        for key in ("assigned_resource_kind", "assigned_event_kind", "assigned_event_kind_mask"):
            if descriptor.get(key) is not None:
                append_blocker(blockers, "assigned_resource_or_event_kind", descriptor=descriptor.get("descriptor"), field=key)
        for key in ("promotion_ready", "public_promotion", "public_surface"):
            if descriptor.get(key) is not False:
                append_blocker(blockers, "public_surface_overclaim", descriptor=descriptor.get("descriptor"), field=key)

    copied_scalars = preflight.get("copied_scalars")
    if not isinstance(copied_scalars, list):
        append_blocker(blockers, "copied_scalars_missing")
        copied_scalars = []
    copied_fields = {entry.get("copied_field") for entry in copied_scalars if isinstance(entry, dict)}
    if copied_fields != EXPECTED_LAYOUT_SCALAR_FIELDS:
        append_blocker(
            blockers,
            "copied_scalar_coverage_mismatch",
            missing=sorted(EXPECTED_LAYOUT_SCALAR_FIELDS - copied_fields),
            unexpected=sorted(field for field in copied_fields - EXPECTED_LAYOUT_SCALAR_FIELDS if isinstance(field, str)),
        )
    pre_call_fields = {
        entry.get("copied_field")
        for entry in copied_scalars
        if isinstance(entry, dict) and entry.get("direction") == "in"
    }
    if pre_call_fields != EXPECTED_COPIED_FIELDS:
        append_blocker(
            blockers,
            "precall_scalar_coverage_mismatch",
            missing=sorted(EXPECTED_COPIED_FIELDS - pre_call_fields),
            unexpected=sorted(field for field in pre_call_fields - EXPECTED_COPIED_FIELDS if isinstance(field, str)),
        )
    deferred_return_fields = {
        entry.get("copied_field")
        for entry in copied_scalars
        if isinstance(entry, dict) and entry.get("direction") == "return"
    }
    if deferred_return_fields != EXPECTED_EXCLUDED_FIELDS:
        append_blocker(
            blockers,
            "deferred_return_coverage_mismatch",
            missing=sorted(EXPECTED_EXCLUDED_FIELDS - deferred_return_fields),
            unexpected=sorted(field for field in deferred_return_fields - EXPECTED_EXCLUDED_FIELDS if isinstance(field, str)),
        )
    for entry in copied_scalars:
        if not isinstance(entry, dict):
            append_blocker(blockers, "copied_scalar_not_object")
            continue
        field = entry.get("copied_field")
        if field in EXPECTED_REDACTED_FIELDS:
            append_blocker(blockers, "forbidden_copied_scalar_field", copied_field=field)
        if field in EXPECTED_COPIED_FIELDS and entry.get("direction") != "in":
            append_blocker(blockers, "precall_scalar_direction_mismatch", copied_field=field, value=entry.get("direction"))
        if field in EXPECTED_EXCLUDED_FIELDS and entry.get("direction") != "return":
            append_blocker(blockers, "deferred_return_direction_mismatch", copied_field=field, value=entry.get("direction"))
        if entry.get("type") == "bool":
            expected_bool = {
                "bool_field_size": 1,
                "bool_byte_offset": 0,
                "byte_mask": "0x01",
                "field_mask": "0xff",
                "native_bool": False,
                "element_size": 1,
            }
            for key, expected in expected_bool.items():
                if entry.get(key) != expected:
                    append_blocker(
                        blockers,
                        "bool_scalar_metadata_mismatch",
                        copied_field=field,
                        field=key,
                        expected=expected,
                        value=entry.get(key),
                    )
        elif entry.get("type") == "int32":
            if entry.get("element_size") != 4:
                append_blocker(blockers, "copied_scalar_shape_mismatch", copied_field=field, field="element_size")
        else:
            append_blocker(blockers, "copied_scalar_shape_mismatch", copied_field=field, field="type", value=entry.get("type"))

    excluded_refs = preflight.get("excluded_object_refs")
    if not isinstance(excluded_refs, list):
        append_blocker(blockers, "excluded_object_refs_missing")
        excluded_refs = []
    redacted_fields = {entry.get("excluded_field") for entry in excluded_refs if isinstance(entry, dict)}
    if redacted_fields != EXPECTED_REDACTED_FIELDS:
        append_blocker(
            blockers,
            "redacted_object_ref_coverage_mismatch",
            missing=sorted(EXPECTED_REDACTED_FIELDS - redacted_fields),
            unexpected=sorted(field for field in redacted_fields - EXPECTED_REDACTED_FIELDS if isinstance(field, str)),
        )
    for entry in excluded_refs:
        if not isinstance(entry, dict):
            continue
        if entry.get("property_class") != "ObjectProperty" or entry.get("evidence_status") != "recognition-only-object-ref-excluded":
            append_blocker(blockers, "redacted_object_ref_shape_mismatch", excluded_field=entry.get("excluded_field"))

    validate_source_snapshots(report, copied_scalars, excluded_refs, blockers)

    safety = preflight.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    if safety.get("promotion_ready") is not False or safety.get("public_surface") is not False:
        append_blocker(blockers, "runtime_public_readiness_overclaim")

    return {
        "layout_scalar_fields": sorted(EXPECTED_LAYOUT_SCALAR_FIELDS),
        "precall_copied_fields": sorted(EXPECTED_COPIED_FIELDS),
        "deferred_return_fields": sorted(EXPECTED_EXCLUDED_FIELDS),
        "redacted_fields": sorted(EXPECTED_REDACTED_FIELDS),
        "descriptors": sorted(EXPECTED_DESCRIPTORS),
        "pre_call_only": True,
        "return_values_excluded": True,
    }


def validate_source_snapshots(
    report: dict[str, Any],
    copied_scalars: list[Any],
    excluded_refs: list[Any],
    blockers: list[dict[str, Any]],
) -> None:
    generated_from = report.get("generated_from")
    if not isinstance(generated_from, dict):
        append_blocker(blockers, "generated_from_missing")
        return
    if generated_from.get("snapshot_schema") != "obelisk.ufunction-chain.snapshot.v1":
        append_blocker(blockers, "snapshot_schema_mismatch", value=generated_from.get("snapshot_schema"))

    snapshots = generated_from.get("input_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != len(EXPECTED_INPUT_TARGETS):
        append_blocker(
            blockers,
            "input_snapshot_count_mismatch",
            expected=len(EXPECTED_INPUT_TARGETS),
            value=len(snapshots) if isinstance(snapshots, list) else None,
        )
        snapshots = [] if not isinstance(snapshots, list) else snapshots

    snapshot_by_id: dict[str, dict[str, Any]] = {}
    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, dict):
            append_blocker(blockers, "input_snapshot_not_object", index=index)
            continue
        snapshot_id = snapshot.get("id")
        snapshot_sha256 = snapshot.get("sha256")
        if not isinstance(snapshot_id, str) or not snapshot_id:
            append_blocker(blockers, "input_snapshot_id_missing", index=index)
            continue
        if snapshot_id in snapshot_by_id:
            append_blocker(blockers, "input_snapshot_duplicate_id", source_snapshot=snapshot_id)
        snapshot_by_id[snapshot_id] = snapshot
        if not isinstance(snapshot_sha256, str) or SHA256_RE.fullmatch(snapshot_sha256) is None:
            append_blocker(blockers, "input_snapshot_sha256_malformed", source_snapshot=snapshot_id, value=snapshot_sha256)

    target_sources: dict[str, str] = {}
    for collection, field_key_name, label in (
        (copied_scalars, "copied_field", "copied_scalar"),
        (excluded_refs, "excluded_field", "excluded_object_ref"),
    ):
        for index, entry in enumerate(collection):
            if not isinstance(entry, dict):
                continue
            field_key = entry.get(field_key_name)
            target = entry.get("target")
            source_snapshot = entry.get("source_snapshot")
            source_snapshot_sha256 = entry.get("source_snapshot_sha256")
            if not isinstance(source_snapshot, str) or source_snapshot not in snapshot_by_id:
                append_blocker(
                    blockers,
                    f"{label}_source_snapshot_unknown",
                    field=field_key,
                    index=index,
                    source_snapshot=source_snapshot,
                )
                continue
            if not isinstance(source_snapshot_sha256, str) or SHA256_RE.fullmatch(source_snapshot_sha256) is None:
                append_blocker(
                    blockers,
                    f"{label}_source_snapshot_sha256_malformed",
                    field=field_key,
                    source_snapshot=source_snapshot,
                    value=source_snapshot_sha256,
                )
            elif source_snapshot_sha256 != snapshot_by_id[source_snapshot].get("sha256"):
                append_blocker(
                    blockers,
                    f"{label}_source_snapshot_sha256_mismatch",
                    field=field_key,
                    source_snapshot=source_snapshot,
                    expected=snapshot_by_id[source_snapshot].get("sha256"),
                    value=source_snapshot_sha256,
                )
            if not isinstance(target, str) or target not in EXPECTED_INPUT_TARGETS:
                append_blocker(blockers, f"{label}_source_target_mismatch", field=field_key, target=target)
                continue
            prior_source = target_sources.setdefault(target, source_snapshot)
            if prior_source != source_snapshot:
                append_blocker(
                    blockers,
                    "target_source_snapshot_inconsistent",
                    target=target,
                    expected=prior_source,
                    value=source_snapshot,
                )

    if set(target_sources) != EXPECTED_INPUT_TARGETS:
        append_blocker(
            blockers,
            "target_source_coverage_mismatch",
            missing=sorted(EXPECTED_INPUT_TARGETS - set(target_sources)),
            unexpected=sorted(set(target_sources) - EXPECTED_INPUT_TARGETS),
        )


def blocked_public_path(relative: str) -> bool:
    return relative in BLOCKED_PUBLIC_PATHS or any(relative.startswith(prefix) for prefix in BLOCKED_PUBLIC_PREFIXES)


def validate_source_isolation(repo_root: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    scanned = 0
    violations: list[str] = []
    for path in repo_root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_SUFFIXES:
            continue
        try:
            relative = path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if relative.startswith(("build/", "local/", ".git/")):
            continue
        if not blocked_public_path(relative):
            continue
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            append_blocker(blockers, "source_scan_failed", path=relative, detail=str(exc))
            continue
        if PUBLIC_DINO_TOKEN_RE.search(text):
            violations.append(relative)

    if violations:
        append_blocker(blockers, "public_or_runtime_dino_wiring_detected", paths=sorted(violations))

    return {
        "status": "isolated" if not violations else "blocked",
        "blocked_prefixes": list(BLOCKED_PUBLIC_PREFIXES),
        "blocked_paths": sorted(BLOCKED_PUBLIC_PATHS),
        "scanned_blocked_source_files": scanned,
        "violations": sorted(violations),
    }


def build_report(repo_root_arg: Path, report_path: Path | None = None, snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    safe_repo_root = safe_path(repo_root_arg, "--repo-root", blockers)
    repo_root = safe_repo_root if safe_repo_root is not None else repo_root_arg.resolve()
    if safe_repo_root is None:
        target_set = {
            "target_set": TARGET_SET,
            "input_targets": [],
            "missing_targets": sorted(EXPECTED_INPUT_TARGETS),
        }
        source_isolation = {
            "status": "blocked",
            "blocked_prefixes": list(BLOCKED_PUBLIC_PREFIXES),
            "blocked_paths": sorted(BLOCKED_PUBLIC_PATHS),
            "scanned_blocked_source_files": 0,
            "violations": [],
        }
    else:
        target_set = validate_target_set(repo_root, blockers)
        for relative in REQUIRED_SOURCE_FILES:
            if not (repo_root / relative).is_file():
                append_blocker(blockers, "required_file_missing", path=relative)
        source_isolation = validate_source_isolation(repo_root, blockers)
    safe_report = safe_path(report_path, "--report", blockers) if report_path is not None else None
    safe_snapshot_root = safe_path(snapshot_root, "--snapshot-root", blockers)
    if safe_snapshot_root is None or (report_path is not None and safe_report is None):
        signature_report: dict[str, Any] = {}
    else:
        signature_report = load_signature_report(safe_report, safe_snapshot_root, blockers)
    summary = validate_signature_report(signature_report, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "not_artifact_gate": True,
        "target_set": target_set,
        "summary": summary,
        "scalar_only_ready": ready,
        "precall_scalar_ready": ready,
        "postcall_return_ready": False,
        "source_isolation": source_isolation,
        "beta_capture_prep": build_beta_capture_prep(),
        "dino_sdk_ready": False,
        "sdk_ready": False,
        "sdk_progress": 0,
        "module_sdk_ready": False,
        "public_sdk_ready": False,
        "public_dino_sdk_ready": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_callback_ready": False,
        "public_module_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "runtime_hook_ready": False,
        "runtime_wiring_ready": False,
        "runtime_observer_approved": False,
        "live_ops_ready": False,
        **runtime_evidence_blocker_non_claims(),
        "dispatcher_ready": False,
        "callback_ready": False,
        "descriptor_ready": False,
        "capability_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_accounted": False,
        "v1_completion": False,
        "v1_completion_ready": False,
        "p0_dependency_chain_accounted": False,
        "p0_dependency_chain_ready": False,
        "public_or_runtime_accounting_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "complete_sdk_claim_allowed": False,
        "stable_claim_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "promotion_ready": False,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "no public Dino SDK or C ABI",
            "no runtime hook wiring or observer approval",
            "no dino/player/passenger identity, lookup, ownership, or ResourceHandle",
            "no mutation, return override, or UE function call",
            "does not claim v1 completion or production readiness",
            "does not replace player-principal lifecycle evidence",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.repo_root, args.report, args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
