#!/usr/bin/env python3
"""Candidate-only readiness check for Transfer ScriptStruct fixtures."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import build_redacted_scriptstruct_signatures as redacted_scriptstructs
from plan_obelisk_multi_surface_beta_capture import (
    CURRENT_ROUTE_BLOCKER,
    REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
)
import protected_paths
from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    NON_AUTHORIZING_READY_SCOPE,
    side_lane_noncanonical_bool_payload_issues,
    side_lane_fail_closed_source_artifact_issues,
)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"
REPORT_SCHEMA = "obelisk.transfer-scriptstruct-readiness-check.v1"
MANIFEST_SCHEMA = "obelisk.scriptstruct-snapshot-manifest.v1"
TARGET_SET = "transfer-scriptstruct"
EXPECTED_MANIFEST_MODULE = "sdk_transfers"
EXPECTED_TARGETS = [
    "PrimalLocalProfile.ARKTributeDino",
    "PrimalLocalProfile.ArkTributePlayerData",
]
EXPECTED_SIGNATURES = {
    "PrimalLocalProfile.ARKTributeDino": {
        "property_count": 10,
        "properties_size": 288,
        "bool_tail_fields": set(),
    },
    "PrimalLocalProfile.ArkTributePlayerData": {
        "property_count": 11,
        "properties_size": 288,
        "bool_tail_fields": {
            "bWasAllowDPCUpload",
            "bWithItems",
            "bForServerTransfer",
        },
    },
}
REQUIRED_SIGNATURE_BLOCKERS = {
    "no_public_scriptstruct_sdk",
    "no_public_transfer_sdk",
    "no_runtime_payload_ownership_policy",
    "scriptstruct_layout_candidate_only",
    "transfer_scriptstruct_payload_decode_blocked",
}
REQUIRED_FIELD_BLOCKERS = {
    "no_public_transfer_sdk",
    "scriptstruct_payload_not_runtime_observed",
    "transfer_scriptstruct_payload_decode_blocked",
}
REQUIRED_NOT_PROMOTED_SURFACES = {
    "public_scriptstruct_sdk",
    "transfer_payload_decoding",
    "resource_handle",
    "object_identity",
    "mutation",
    "return_override",
    "raw_ue_params",
}
REQUIRED_NON_CLAIM_TOKENS = (
    "candidate-only ScriptStruct layout summary",
    "does not promote public ScriptStruct or Transfer SDK callbacks",
    "does not decode transfer payloads",
    "mutation",
    "return overrides",
)
REDACTED_FIELD_ALLOWED_KEYS = frozenset(
    (
        "array_dim",
        "array_inner",
        "bool_byte_offset",
        "bool_field_size",
        "bool_masks",
        "byte_mask",
        "element_size",
        "field_mask",
        "name",
        "native_bool",
        "offset",
        "promotion_blockers",
        "property_flags",
        "redaction",
        "source_property_class",
        "status",
        "type",
    )
)
EXPLICITLY_EXCLUDED = ["ItemNetInfo"]
REPORT_FALSE_FLAGS: dict[str, bool] = {
    "approved_runtime_evidence_accepted": False,
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
    "complete_sdk_ready": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_sdk": False,
    "counts_toward_public_transfer_sdk": False,
    "counts_toward_runtime": False,
    "side_lane_counts_toward_sdk": False,
    "side_lane_counts_toward_p0": False,
    "sdk_p0_unlock_allowed": False,
    "counts_toward_v1_completion": False,
    "cross_map_ready": False,
    "cross_map_state_public_contract_ready": False,
    "cross_map_state_ready": False,
    "live_ops_ready": False,
    "mutation_ready": False,
    "p0_dependency_chain_ready": False,
    "p0_dependency_ready": False,
    "pack_authorizes_discord": False,
    "pack_authorizes_marker_or_env_change": False,
    "pack_authorizes_player_backed_window": False,
    "pack_authorizes_restart": False,
    "pack_authorizes_runtime_observer": False,
    "primary_evidence_substitution_allowed": False,
    "promotion_ready": False,
    "public_abi_ready": False,
    "public_api_ready": False,
    "public_contract_ready": False,
    "public_module_ready": False,
    "public_sdk_ready": False,
    "public_transfer_sdk_ready": False,
    "resource_handle_public_contract_ready": False,
    "resource_handle_ready": False,
    "replaces_player_principal_evidence": False,
    "replaces_player_principal_triplet": False,
    "player_principal_lifecycle_evidence_substitution_allowed": False,
    "return_override_ready": False,
    "runtime_capture_ready": False,
    "runtime_ready": False,
    "runtime_validated": False,
    "sdk_runtime_ready": False,
    "transfer_payload_decoding_ready": False,
    "player_principal_replacement_ready": False,
    "side_lane_collection_can_replace_player_principal_evidence": False,
    "side_lane_collection_counts_before_checker_acceptance": False,
    "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
    "substitutes_for_player_principal_lifecycle_evidence": False,
    "substitutes_for_player_principal_lifecycle_triplet": False,
    "v1_completion_ready": False,
}
REPORT_ZERO_FIELDS: dict[str, int] = {
    "complete_sdk_claim_progress_contribution": 0,
    "complete_sdk_progress_contribution": 0,
    "cross_map_public_contract_count": 0,
    "mutation_surface_count": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "p0_dependency_progress_contribution": 0,
    "public_sdk_progress_contribution": 0,
    "public_transfer_sdk_progress_contribution": 0,
    "public_transfer_sdk_surface_count": 0,
    "resource_handle_surface_count": 0,
    "return_override_surface_count": 0,
    "runtime_progress_contribution": 0,
    "v1_completion_progress_contribution": 0,
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:"
    r"^ready$|readiness|"
    r"approved_?runtime_?evidence|clears_?approved_?runtime_?evidence_?missing|"
    r"public_?(?:sdk|transfer_?sdk|api|abi|contract|module|ready)|"
    r"transfer_?sdk|sdk_?ready|"
    r"runtime_?(?:ready|validated|validation|hook|wiring|capture)|live_?ops|"
    r"complete_?sdk|p0|mutation|return_?override|resource_?handle|cross_?map|"
    r"player_?principal|principal_?lifecycle|evidence_?bundle|multi_?surface|beta_?capture|"
    r"primary_?evidence|side_?lane|substitut|authoriz|"
    r"v1_?(?:completion|ready)|stable_?sdk|promotion_?ready|"
    r"counts_?(?:as|toward)_?(?:approved_?runtime|public|runtime|complete|p0)"
    r")",
    re.IGNORECASE,
)
CLAIM_SUBJECT_RE = re.compile(
    r"(?:"
    r"public[_\s-]+transfer[_\s-]+sdk|transfer[_\s-]+sdk|public[_\s-]+sdk|"
    r"public[_\s-]+(?:api|abi|contract)|runtime|complete[_\s-]+sdk|p0|"
    r"approved[_\s-]+runtime[_\s-]+evidence|player[_\s-]+principal|"
    r"player[_\s-]+principal[_\s-]+lifecycle|player[_\s-]+principal[_\s-]+triplet|"
    r"primary[_\s-]+evidence|side[_\s-]+lane|authorization|authorizes?|substitution|substitutes?|"
    r"mutation|return[_\s-]+override|resource[_\s-]+handle|ResourceHandle|"
    r"cross[_\s-]*map|sdk"
    r")",
    re.IGNORECASE,
)
CLAIM_CONTEXT_KEY_RE = re.compile(
    r"(?:public|sdk|api|abi|contract|module|runtime|capture|live[_-]?ops|v1|p0|"
    r"complete|completion|stable|promotion|resource[_-]?handle|return[_-]?override|"
    r"identity|lookup|mutation|cross[_-]?map|transfer|source|approved[_-]?runtime|"
    r"player[_-]?principal|principal[_-]?lifecycle|multi[_-]?surface|beta[_-]?capture|"
    r"capture[_-]?(?:pack|plan|queue)|evidence[_-]?bundle|primary[_-]?evidence|"
    r"side[_-]?lane|substitut|authoriz|route[_-]?blocker)",
    re.IGNORECASE,
)
AFFIRMATIVE_CONTEXT_RE = re.compile(
    r"(?:ready|readiness|available|enabled|promoted|promotion|public|runtime|complete|"
    r"completion|supported|validated|claim|counts|allowed|unblocked|unlocked|"
    r"clears?|resolves?|replaces?|satisfies)",
    re.IGNORECASE,
)
POSITIVE_STATUS_VALUES = frozenset(
    (
        "accepted",
        "active",
        "approved",
        "available",
        "allowed",
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
        "unblocked",
        "unlocked",
        "validated",
        "v1-ready",
    )
)
ALLOWED_POSITIVE_METADATA_PATHS = frozenset(
    (
        "$.target_set_coverage.complete",
        "$.target_set_coverage.status",
    )
)
NEUTRAL_TRUE_METADATA_KEYS = frozenset(
    (
        "accepted_for_candidate_review",
        "accepted_for_internal_planning",
        "candidate_capture_only",
        "candidate_only",
        "candidate_only_mode",
        "consume_only",
        "non_counting",
        "not_artifact_gate",
        "offline_only",
        "broadcast_before_restart_if_players_connected",
        "keep_servers_running_when_practical",
        "keep_transfer_server_when_practical",
        "must_be_checker_accepted",
        "requires_checker_acceptance",
        "restart_only_for_obelisk_update_or_gate_change",
    )
)
NEUTRAL_TRUE_METADATA_SUFFIXES = (
    "_candidate_only",
    "_consume_only",
    "_non_counting",
    "_not_artifact_gate",
    "_offline_only",
)
FORBIDDEN_CLAIM_PATH_SUFFIXES = frozenset(
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
CONTEXTUAL_CLAIM_CONTAINER_KEYS = frozenset(
    (
        "candidate",
        "candidate_surfaces",
        "capture_surfaces",
        "multi_surface_beta_capture_pack",
        "multi_surface_beta_capture_plan",
        "multi_surface_beta_capture_plan_queue",
        "package_shape",
        "primary_evidence",
        "player_principal",
        "plugin_hub",
        "public_sdk",
        "readiness",
        "required_primary_evidence",
        "route_blocker",
        "runtime",
        "support_tier",
        "side_lane",
        "target_set",
        "v1",
    )
)
NEUTRAL_POSITIVE_METADATA_KEYS = frozenset(
    (
        "bool_tail_field_count",
        "field_count",
        "field_count_total",
        "max_ark_servers_running",
        "priority",
        "property_count",
        "redacted_count_total",
        "redacted_field_count",
        "signature_count",
        "snapshot_count",
        "source_binding_count",
        "target_count",
    )
)
NEUTRAL_POSITIVE_METADATA_SUFFIXES = (
    "_field_count",
    "_target_count",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate committed Transfer ScriptStruct fixtures through the redacted "
            "ScriptStruct signature builder without promoting runtime or public SDK readiness."
        )
    )
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=DEFAULT_SNAPSHOT_ROOT,
        help="ScriptStruct snapshot fixture root. Defaults to tests/fixtures/scriptstruct_snapshots.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def safe_input_path(label: str, path: Path, blockers: list[dict[str, Any]]) -> bool:
    try:
        protected_paths.reject_symlink_component(path, label)
        protected_paths.reject_protected_input_path(
            path,
            label,
            protected_root=redacted_scriptstructs.PROTECTED_SERVER_ROOT,
            approved_roots=redacted_scriptstructs.APPROVED_OFFLINE_WORKSPACE_ROOTS,
            message=f"{label} must not read from protected live-server path: {path}",
        )
    except SystemExit as exc:
        append_blocker(blockers, "snapshot_input_path_rejected", label=label, detail=str(exc))
        return False
    return True


def load_manifest_payload(snapshot_root: Path, blockers: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, bool]:
    fatal = False
    if not safe_input_path("snapshot root", snapshot_root, blockers):
        return None, True
    manifest_path = snapshot_root / "manifest.json"
    if not safe_input_path("snapshot manifest", manifest_path, blockers):
        return None, True
    if not manifest_path.is_file():
        append_blocker(blockers, "snapshot_manifest_missing")
        return None, True
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        append_blocker(blockers, "snapshot_manifest_json_invalid", detail=str(exc))
        return None, True
    if not isinstance(manifest, dict):
        append_blocker(blockers, "snapshot_manifest_not_object")
        return None, True
    return manifest, fatal


def manifest_entry_target(entry: dict[str, Any]) -> str | None:
    outer = entry.get("outer")
    name = entry.get("name")
    if not isinstance(outer, str) or not outer or not isinstance(name, str) or not name:
        return None
    return f"{outer}.{name}"


def file_sha256(path: Path, blockers: list[dict[str, Any]]) -> tuple[str | None, bool]:
    if not safe_input_path("snapshot", path, blockers):
        return None, True
    if not path.is_file():
        append_blocker(blockers, "manifest_snapshot_missing", path="redacted")
        return None, False
    return redacted_scriptstructs.file_sha256(path), False


def validate_manifest_binding(
    snapshot_root: Path,
    source_report: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    summary: dict[str, Any] = {
        "schema": None,
        "source": None,
        "status": None,
        "sha_prefix": None,
        "target_set": TARGET_SET,
        "targets": [],
        "modules": [],
        "source_bindings": [],
        "source_binding_count": 0,
    }
    manifest, fatal = load_manifest_payload(snapshot_root, blockers)
    if manifest is None:
        return summary, fatal

    schema = manifest.get("schema")
    source = manifest.get("source")
    status = manifest.get("status")
    sha_prefix = manifest.get("sha_prefix")
    summary.update({"schema": schema, "source": source, "status": status, "sha_prefix": sha_prefix})
    if schema != MANIFEST_SCHEMA:
        append_blocker(blockers, "snapshot_manifest_schema_mismatch", value=schema)
    if source != "offline_core":
        append_blocker(blockers, "snapshot_manifest_source_mismatch", value=source)
    if status != "candidate-only":
        append_blocker(blockers, "snapshot_manifest_status_mismatch", value=status)
    if not isinstance(sha_prefix, str) or not sha_prefix:
        append_blocker(blockers, "snapshot_manifest_sha_prefix_missing")
        return summary, True

    targets = manifest.get("targets")
    if not isinstance(targets, list):
        append_blocker(blockers, "snapshot_manifest_targets_not_list")
        return summary, True

    entries_by_target: dict[str, dict[str, Any]] = {}
    observed_targets: list[str] = []
    modules: list[str] = []
    fatal_path_rejection = False
    for index, entry in enumerate(targets):
        if not isinstance(entry, dict):
            append_blocker(blockers, "snapshot_manifest_entry_not_object", index=index)
            fatal = True
            continue
        target = manifest_entry_target(entry)
        if target is None:
            append_blocker(blockers, "snapshot_manifest_entry_target_invalid", index=index)
            fatal = True
            continue
        observed_targets.append(target)
        if target in entries_by_target:
            append_blocker(blockers, "snapshot_manifest_duplicate_target", target=target)
        entries_by_target[target] = entry
        module = entry.get("module")
        if isinstance(module, str) and module not in modules:
            modules.append(module)
    summary["targets"] = observed_targets
    summary["modules"] = modules
    require_exact_list(
        blockers,
        reason="snapshot_manifest_target_mismatch",
        actual=observed_targets,
        expected=EXPECTED_TARGETS,
    )

    source_bindings: list[dict[str, str]] = []
    for expected_index, target in enumerate(EXPECTED_TARGETS, start=1):
        entry = entries_by_target.get(target)
        if entry is None:
            append_blocker(blockers, "snapshot_manifest_expected_target_missing", target=target)
            continue
        outer, _, name = target.partition(".")
        expected_file = f"{target}.snapshot.json"
        if entry.get("module") != EXPECTED_MANIFEST_MODULE:
            append_blocker(
                blockers,
                "snapshot_manifest_module_mismatch",
                target=target,
                expected=EXPECTED_MANIFEST_MODULE,
                value=entry.get("module"),
            )
        if entry.get("safe_outer") != outer:
            append_blocker(
                blockers,
                "snapshot_manifest_safe_outer_mismatch",
                target=target,
                expected=outer,
                value=entry.get("safe_outer"),
            )
        if entry.get("file") != expected_file:
            append_blocker(
                blockers,
                "snapshot_manifest_file_mismatch",
                target=target,
                expected=expected_file,
                value=entry.get("file"),
            )
        if entry.get("name") != name:
            append_blocker(
                blockers,
                "snapshot_manifest_name_mismatch",
                target=target,
                expected=name,
                value=entry.get("name"),
            )
        module = entry.get("module")
        file_name = entry.get("file")
        if not isinstance(module, str) or not module or not isinstance(file_name, str) or not file_name:
            append_blocker(blockers, "snapshot_manifest_entry_path_invalid", target=target)
            fatal = True
            continue
        snapshot_path = snapshot_root / sha_prefix / module / file_name
        digest, digest_fatal = file_sha256(snapshot_path, blockers)
        fatal_path_rejection = fatal_path_rejection or digest_fatal
        if digest is None:
            continue
        source_bindings.append({"id": f"snapshot-{expected_index:04d}", "sha256": digest})

    summary["source_bindings"] = source_bindings
    summary["source_binding_count"] = len(source_bindings)
    if source_report is not None and len(source_bindings) == len(EXPECTED_TARGETS):
        generated_from = source_report.get("generated_from")
        if not isinstance(generated_from, dict):
            append_blocker(blockers, "source_generated_from_missing")
        else:
            if generated_from.get("snapshot_schema") != redacted_scriptstructs.SUPPORTED_SNAPSHOT_SCHEMA:
                append_blocker(
                    blockers,
                    "source_generated_from_snapshot_schema_mismatch",
                    value=generated_from.get("snapshot_schema"),
                )
            if generated_from.get("input_snapshots") != source_bindings:
                append_blocker(
                    blockers,
                    "source_manifest_input_snapshot_binding_mismatch",
                    expected=source_bindings,
                    value=generated_from.get("input_snapshots"),
                )
    return summary, fatal or fatal_path_rejection


def normalize_claim_key(key: str) -> str:
    camel_spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", key)
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", camel_spaced)
    return re.sub(r"[^a-z0-9]+", "_", camel_spaced.lower()).strip("_")


def is_negative_or_blocker_text(value: str) -> bool:
    lowered = value.lower()
    if re.search(r"\bun(?:blocked|locked)\b", lowered):
        return False
    return any(
        token in lowered
        for token in (
            "does not",
            "do not",
            "must not",
            "not ",
            "not_",
            "no_",
            "blocked",
            "excluded",
            "candidate-only",
            "candidate_only",
        )
    )


def is_positive_status_alias(value: str) -> bool:
    normalized = normalize_claim_key(value).replace("_", "-")
    return (
        normalized in POSITIVE_STATUS_VALUES
        or normalized.endswith("-ready")
    )


def is_positive_claim_alias_value(value: Any) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    if is_negative_or_blocker_text(value):
        return False
    return is_positive_status_alias(value) or (
        CLAIM_SUBJECT_RE.search(value) is not None
        and AFFIRMATIVE_CONTEXT_RE.search(value) is not None
    )


def reject_item_net_info(value: Any, blockers: list[dict[str, Any]], *, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            if "itemnetinfo" in key.replace("_", "").lower():
                append_blocker(blockers, "item_net_info_in_source_report", path=key_path, value=key)
            reject_item_net_info(child, blockers, path=key_path)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_item_net_info(child, blockers, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and "itemnetinfo" in value.replace("_", "").lower():
        append_blocker(blockers, "item_net_info_in_source_report", path=path, value=value)


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


def neutral_positive_metadata_key(normalized_key: str) -> bool:
    return (
        normalized_key in NEUTRAL_TRUE_METADATA_KEYS
        or normalized_key in NEUTRAL_POSITIVE_METADATA_KEYS
        or any(normalized_key.endswith(suffix) for suffix in NEUTRAL_TRUE_METADATA_SUFFIXES)
        or any(normalized_key.endswith(suffix) for suffix in NEUTRAL_POSITIVE_METADATA_SUFFIXES)
    )


def forbidden_positive_accounting_key(normalized_key: str) -> bool:
    return (
        normalized_key in REPORT_ZERO_FIELDS
        or normalized_key.endswith("_progress_ratio")
        or normalized_key.startswith(("counts_for", "counts_toward", "contributes_to"))
        or normalized_key.startswith("counts_as")
        or "contribution" in normalized_key
        or "credit" in normalized_key
        or "progress" in normalized_key
        or (normalized_key.endswith("_count") and claim_context_key(normalized_key))
    )


def claim_context_key(normalized_key: str) -> bool:
    if normalized_key in {"accepted_for_internal_planning", "accepted_for_candidate_review"}:
        return False
    return normalized_key in CONTEXTUAL_CLAIM_CONTAINER_KEYS or bool(
        FORBIDDEN_CLAIM_KEY_RE.search(normalized_key) or CLAIM_CONTEXT_KEY_RE.search(normalized_key)
    )


def forbidden_claim_path_alias(path: str) -> bool:
    normalized_path = normalize_claim_key(path)
    return any(
        normalized_path == suffix or normalized_path.endswith(f"_{suffix}")
        for suffix in FORBIDDEN_CLAIM_PATH_SUFFIXES
    )


def normalized_path_leaf_key(path: str) -> str:
    leaf = path.rsplit(".", 1)[-1]
    leaf = re.sub(r"\[\d+\]$", "", leaf)
    return normalize_claim_key(leaf)


def reject_claim_overclaims(
    value: Any,
    blockers: list[dict[str, Any]],
    *,
    path: str = "$",
    claim_context: bool = False,
) -> None:
    if path in ALLOWED_POSITIVE_METADATA_PATHS:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{path}.{key}"
            normalized_key = normalize_claim_key(key)
            forbidden_path_alias = forbidden_claim_path_alias(key_path)
            child_context = claim_context or claim_context_key(normalized_key) or forbidden_path_alias
            if key_path in ALLOWED_POSITIVE_METADATA_PATHS:
                reject_claim_overclaims(child, blockers, path=key_path, claim_context=child_context)
                continue
            if forbidden_path_alias and is_positive_claim_alias_value(child):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=key, value=child)
            if normalized_key == "status" and isinstance(child, str) and is_positive_status_alias(child):
                append_blocker(blockers, "positive_status_alias_overclaim", path=key_path, field=key, value=child)
            if FORBIDDEN_CLAIM_KEY_RE.search(normalized_key):
                if is_positive_claim_alias_value(child):
                    append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=key)
            if child_context and "progress" in normalized_key and positive_numeric_claim(child):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=key)
            if (
                child_context
                and forbidden_positive_accounting_key(normalized_key)
                and not neutral_positive_metadata_key(normalized_key)
                and positive_progress_claim(child)
            ):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=key)
            if child_context and normalized_key in {
                "accepted",
                "allowed",
                "stable",
                "status",
                "unblocked",
                "unlocked",
            } and is_positive_claim_alias_value(child):
                append_blocker(blockers, "readiness_alias_overclaim", path=key_path, field=key)
            reject_claim_overclaims(child, blockers, path=key_path, claim_context=child_context)
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_claim_overclaims(child, blockers, path=f"{path}[{index}]", claim_context=claim_context)
        return
    if (
        claim_context
        and is_positive_claim_alias_value(value)
        and not neutral_positive_metadata_key(normalized_path_leaf_key(path))
    ):
        append_blocker(blockers, "readiness_alias_overclaim", path=path, value=value)
        return
    if (
        not isinstance(value, str)
        or is_negative_or_blocker_text(value)
        or path.startswith("$.safety_summary.not_promoted_surfaces[")
    ):
        return
    if CLAIM_SUBJECT_RE.search(value) and AFFIRMATIVE_CONTEXT_RE.search(value):
        append_blocker(blockers, "forbidden_positive_claim_value", path=path, value=value)


def string_list(value: Any) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def require_exact_list(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    actual: Any,
    expected: list[str],
) -> list[str]:
    actual_list = string_list(actual)
    if actual_list != expected:
        actual_set = set(actual_list)
        expected_set = set(expected)
        append_blocker(
            blockers,
            reason,
            expected=expected,
            value=actual_list,
            missing=sorted(expected_set - actual_set),
            unexpected=sorted(actual_set - expected_set),
        )
    return actual_list


def require_blocker_subset(
    blockers: list[dict[str, Any]],
    *,
    reason: str,
    actual: Any,
    required: set[str],
    path: str,
) -> set[str]:
    actual_set = set(actual) if isinstance(actual, list) and all(isinstance(item, str) for item in actual) else set()
    missing = required - actual_set
    if missing:
        append_blocker(blockers, reason, path=path, missing=sorted(missing), value=sorted(actual_set))
    return actual_set


def validate_bool_tail_field(
    field: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    target: str,
    field_name: str,
) -> None:
    expected_values: dict[str, Any] = {
        "type": "redacted_transfer_payload_bool",
        "source_property_class": "BoolProperty",
        "bool_field_size": 1,
        "bool_byte_offset": 0,
        "byte_mask": "0x01",
        "field_mask": "0xff",
        "native_bool": False,
        "element_size": 1,
        "array_dim": 1,
    }
    for key, expected in expected_values.items():
        if field.get(key) != expected:
            append_blocker(
                blockers,
                "bool_tail_metadata_mismatch",
                target=target,
                field=field_name,
                key=key,
                expected=expected,
                value=field.get(key),
            )
    if field.get("bool_masks") != {"byte_mask": "0x01", "field_mask": "0xff"}:
        append_blocker(
            blockers,
            "bool_tail_metadata_mismatch",
            target=target,
            field=field_name,
            key="bool_masks",
            expected={"byte_mask": "0x01", "field_mask": "0xff"},
            value=field.get("bool_masks"),
        )


def validate_signature(
    signature: dict[str, Any],
    blockers: list[dict[str, Any]],
    *,
    target: str,
) -> dict[str, Any]:
    expected = EXPECTED_SIGNATURES[target]
    summary = {"field_count": 0, "redacted_field_count": 0, "bool_tail_fields": []}

    if signature.get("property_count") != expected["property_count"]:
        append_blocker(
            blockers,
            "signature_property_count_mismatch",
            target=target,
            expected=expected["property_count"],
            value=signature.get("property_count"),
        )
    if signature.get("properties_size") != expected["properties_size"]:
        append_blocker(
            blockers,
            "signature_properties_size_mismatch",
            target=target,
            expected=expected["properties_size"],
            value=signature.get("properties_size"),
        )
    if signature.get("property_chain_status") != "candidate":
        append_blocker(
            blockers,
            "signature_property_chain_not_candidate",
            target=target,
            value=signature.get("property_chain_status"),
        )
    require_blocker_subset(
        blockers,
        reason="signature_required_blockers_missing",
        actual=signature.get("promotion_blockers"),
        required=REQUIRED_SIGNATURE_BLOCKERS,
        path=f"signatures[{target}].promotion_blockers",
    )

    fields = signature.get("fields")
    if not isinstance(fields, list):
        append_blocker(blockers, "signature_fields_missing", target=target)
        return summary
    summary["field_count"] = len(fields)
    if len(fields) != expected["property_count"]:
        append_blocker(
            blockers,
            "signature_field_count_mismatch",
            target=target,
            expected=expected["property_count"],
            value=len(fields),
        )

    bool_tail_fields: set[str] = set()
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            append_blocker(blockers, "signature_field_not_object", target=target, index=index)
            continue
        unexpected_keys = sorted(set(field) - REDACTED_FIELD_ALLOWED_KEYS)
        if unexpected_keys:
            append_blocker(
                blockers,
                "redacted_field_unexpected_keys",
                target=target,
                index=index,
                keys=unexpected_keys,
            )
        field_name = field.get("name")
        field_type = field.get("type")
        if not isinstance(field_name, str) or not field_name:
            append_blocker(blockers, "signature_field_name_missing", target=target, index=index)
            continue
        if not isinstance(field_type, str) or not field_type.startswith("redacted_"):
            append_blocker(
                blockers,
                "field_not_redacted_payload_evidence",
                target=target,
                field=field_name,
                value=field_type,
            )
        else:
            summary["redacted_field_count"] += 1
        if not isinstance(field.get("redaction"), str) or not field["redaction"]:
            append_blocker(blockers, "field_redaction_reason_missing", target=target, field=field_name)
        require_blocker_subset(
            blockers,
            reason="field_required_blockers_missing",
            actual=field.get("promotion_blockers"),
            required=REQUIRED_FIELD_BLOCKERS,
            path=f"signatures[{target}].fields[{field_name}].promotion_blockers",
        )
        if field.get("source_property_class") == "BoolProperty" or field_type == "redacted_transfer_payload_bool":
            bool_tail_fields.add(field_name)
            validate_bool_tail_field(field, blockers, target=target, field_name=field_name)

    expected_bool_fields = expected["bool_tail_fields"]
    if bool_tail_fields != expected_bool_fields:
        append_blocker(
            blockers,
            "bool_tail_field_coverage_mismatch",
            target=target,
            missing=sorted(expected_bool_fields - bool_tail_fields),
            unexpected=sorted(bool_tail_fields - expected_bool_fields),
        )
    summary["bool_tail_fields"] = [f"{target}.{field}" for field in sorted(bool_tail_fields)]
    return summary


def validate_redacted_report(source_report: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    reject_item_net_info(source_report, blockers)
    blockers.extend(
        side_lane_fail_closed_source_artifact_issues(
            source_report,
            expected_target_sets=(TARGET_SET,),
        )
    )
    blockers.extend(side_lane_noncanonical_bool_payload_issues(source_report))
    reject_claim_overclaims(source_report, blockers)

    if source_report.get("schema") != redacted_scriptstructs.OUTPUT_SCHEMA:
        append_blocker(blockers, "source_schema_mismatch", value=source_report.get("schema"))
    if source_report.get("snapshot_root") != "redacted":
        append_blocker(blockers, "source_snapshot_root_not_redacted", value=source_report.get("snapshot_root"))
    if source_report.get("target_sets") != [TARGET_SET]:
        append_blocker(blockers, "target_set_mismatch", value=source_report.get("target_sets"))
    if source_report.get("source_target_sets") not in ([], None):
        append_blocker(blockers, "source_target_sets_present", value=source_report.get("source_target_sets"))
    if source_report.get("missing_targets") != []:
        append_blocker(blockers, "missing_targets_present", value=source_report.get("missing_targets"))

    coverage = source_report.get("target_set_coverage")
    if not isinstance(coverage, dict):
        append_blocker(blockers, "target_set_coverage_missing")
        coverage = {}
    if coverage.get("schema") != redacted_scriptstructs.TARGET_SET_COVERAGE_SCHEMA:
        append_blocker(blockers, "target_set_coverage_schema_mismatch", value=coverage.get("schema"))
    if coverage.get("status") != "complete" or coverage.get("complete") is not True:
        append_blocker(
            blockers,
            "target_set_coverage_incomplete",
            status=coverage.get("status"),
            complete=coverage.get("complete"),
        )
    if coverage.get("declared_target_sets") != [TARGET_SET]:
        append_blocker(
            blockers,
            "target_set_declared_coverage_mismatch",
            expected=[TARGET_SET],
            value=coverage.get("declared_target_sets"),
        )
    require_exact_list(
        blockers,
        reason="target_set_expected_coverage_mismatch",
        actual=coverage.get("expected_targets"),
        expected=EXPECTED_TARGETS,
    )
    observed_from_coverage = require_exact_list(
        blockers,
        reason="target_set_observed_coverage_mismatch",
        actual=coverage.get("observed_targets"),
        expected=EXPECTED_TARGETS,
    )

    signatures = source_report.get("signatures")
    if not isinstance(signatures, list):
        append_blocker(blockers, "signatures_missing")
        signatures = []
    observed_from_signatures = [signature.get("target") for signature in signatures if isinstance(signature, dict)]
    require_exact_list(
        blockers,
        reason="signature_target_coverage_mismatch",
        actual=observed_from_signatures,
        expected=EXPECTED_TARGETS,
    )
    if source_report.get("snapshot_count") != len(EXPECTED_TARGETS):
        append_blocker(blockers, "snapshot_count_mismatch", expected=len(EXPECTED_TARGETS), value=source_report.get("snapshot_count"))
    if source_report.get("signature_count") != len(EXPECTED_TARGETS):
        append_blocker(blockers, "signature_count_mismatch", expected=len(EXPECTED_TARGETS), value=source_report.get("signature_count"))

    signatures_by_target = {
        signature.get("target"): signature for signature in signatures if isinstance(signature, dict)
    }
    signature_summaries = []
    bool_tail_fields: list[str] = []
    field_count_total = 0
    redacted_field_count_total = 0
    for target in EXPECTED_TARGETS:
        signature = signatures_by_target.get(target)
        if not isinstance(signature, dict):
            append_blocker(blockers, "expected_signature_missing", target=target)
            continue
        signature_summary = validate_signature(signature, blockers, target=target)
        signature_summaries.append(signature_summary)
        field_count_total += int(signature_summary["field_count"])
        redacted_field_count_total += int(signature_summary["redacted_field_count"])
        bool_tail_fields.extend(signature_summary["bool_tail_fields"])

    safety = source_report.get("safety_summary")
    if not isinstance(safety, dict):
        append_blocker(blockers, "safety_summary_missing")
        safety = {}
    if safety.get("artifact_status") != "candidate_only":
        append_blocker(blockers, "safety_artifact_status_invalid", value=safety.get("artifact_status"))
    if safety.get("promotion_ready") is not False:
        append_blocker(blockers, "safety_promotion_ready_not_false", value=safety.get("promotion_ready"))
    if safety.get("intended_use") != "offline_review_only":
        append_blocker(blockers, "safety_intended_use_invalid", value=safety.get("intended_use"))
    if safety.get("copied_scalar_count_total") != 0:
        append_blocker(blockers, "copied_scalar_count_not_zero", value=safety.get("copied_scalar_count_total"))
    if safety.get("copied_scalar_by_kind") != {}:
        append_blocker(blockers, "copied_scalar_by_kind_not_empty", value=safety.get("copied_scalar_by_kind"))
    if safety.get("redacted_count_total") != redacted_field_count_total:
        append_blocker(
            blockers,
            "safety_redacted_count_mismatch",
            expected=redacted_field_count_total,
            value=safety.get("redacted_count_total"),
        )
    if safety.get("field_count_total") != field_count_total:
        append_blocker(
            blockers,
            "safety_field_count_mismatch",
            expected=field_count_total,
            value=safety.get("field_count_total"),
        )
    not_promoted = set(string_list(safety.get("not_promoted_surfaces")))
    if not REQUIRED_NOT_PROMOTED_SURFACES.issubset(not_promoted):
        append_blocker(
            blockers,
            "safety_not_promoted_surfaces_missing",
            missing=sorted(REQUIRED_NOT_PROMOTED_SURFACES - not_promoted),
            value=sorted(not_promoted),
        )

    non_claims = string_list(source_report.get("non_claims"))
    non_claims_text = "\n".join(non_claims)
    for token in REQUIRED_NON_CLAIM_TOKENS:
        if token not in non_claims_text:
            append_blocker(blockers, "required_non_claim_missing", token=token)

    return {
        "target_set": TARGET_SET,
        "targets": observed_from_coverage,
        "snapshot_count": source_report.get("snapshot_count") if isinstance(source_report.get("snapshot_count"), int) else 0,
        "signature_count": source_report.get("signature_count") if isinstance(source_report.get("signature_count"), int) else 0,
        "field_count_total": field_count_total,
        "redacted_payload_field_count": redacted_field_count_total,
        "bool_tail_fields": sorted(bool_tail_fields),
        "copied_scalar_count_total": safety.get("copied_scalar_count_total", 0),
        "not_promoted_surfaces": sorted(not_promoted),
        "explicitly_excluded": EXPLICITLY_EXCLUDED,
        "item_net_info_excluded": True,
    }


def relative_snapshot_root(snapshot_root: Path) -> str:
    try:
        return str(snapshot_root.relative_to(REPO_ROOT))
    except ValueError:
        return str(snapshot_root)


def source_command(snapshot_root: Path) -> list[str]:
    return [
        "python3",
        "scripts/build_redacted_scriptstruct_signatures.py",
        "--snapshot-root",
        relative_snapshot_root(snapshot_root),
        "--target-set",
        TARGET_SET,
        "--json",
    ]


def build_multi_surface_beta_capture_guardrail() -> dict[str, Any]:
    return {
        "status": "candidate_only_non_counting",
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "required_first_artifact": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "approved_runtime_evidence": False,
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
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "side_lane_counts_toward_sdk": False,
        "side_lane_counts_toward_p0": False,
        "sdk_p0_unlock_allowed": False,
        "primary_evidence_substitution_allowed": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "public_sdk_ready": False,
        "public_transfer_sdk_ready": False,
        "stable_claim_allowed": False,
        "v1_completion_ready": False,
        "replaces_player_principal_evidence": False,
        "replaces_player_principal_triplet": False,
        "player_principal_lifecycle_evidence_substitution_allowed": False,
        "side_lane_collection_can_replace_player_principal_evidence": False,
        "side_lane_collection_counts_before_checker_acceptance": False,
        "side_lane_substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_evidence": False,
        "substitutes_for_player_principal_lifecycle_triplet": False,
        "non_claim": (
            "candidate multi-surface beta capture pack/plan artifacts are prep only; "
            "they do not satisfy approved player-principal runtime evidence"
        ),
    }


def build_report(
    snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT,
    *,
    source_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    manifest_summary, fatal_manifest_input = validate_manifest_binding(snapshot_root, None, blockers)
    if source_report is None:
        if fatal_manifest_input:
            source_report = None
        else:
            try:
                source_report = redacted_scriptstructs.build_report(
                    snapshot_root=snapshot_root,
                    target_sets=[TARGET_SET],
                )
            except SystemExit as exc:
                append_blocker(blockers, "redacted_report_build_failed", detail=str(exc))
                source_report = None
            except Exception as exc:  # pragma: no cover - defensive fail-closed wrapper.
                append_blocker(blockers, "redacted_report_build_failed", detail=repr(exc))
                source_report = None

    summary: dict[str, Any] = {
        "target_set": TARGET_SET,
        "targets": [],
        "snapshot_count": 0,
        "signature_count": 0,
        "field_count_total": 0,
        "redacted_payload_field_count": 0,
        "bool_tail_fields": [],
        "copied_scalar_count_total": 0,
        "not_promoted_surfaces": [],
        "explicitly_excluded": EXPLICITLY_EXCLUDED,
        "item_net_info_excluded": True,
    }
    if isinstance(source_report, dict):
        manifest_summary, _ = validate_manifest_binding(snapshot_root, source_report, blockers)
        summary = validate_redacted_report(source_report, blockers)
        summary["source_binding_count"] = manifest_summary["source_binding_count"]
        summary["source_manifest_targets"] = manifest_summary["targets"]
    elif source_report is not None:
        append_blocker(blockers, "redacted_report_not_object")

    ready = not blockers
    beta_capture_guardrail = build_multi_surface_beta_capture_guardrail()
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": "candidate_only_accepted" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "required_runtime_evidence": REQUIRED_PLAYER_PRINCIPAL_RUNTIME_EVIDENCE,
        "accepted_for_candidate_review": ready,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "candidate_only": True,
        "candidate_only_mode": True,
        "not_artifact_gate": True,
        "consume_only": True,
        "snapshot_root": "redacted",
        "source_command": source_command(snapshot_root),
        "source_manifest": manifest_summary,
        "target_set": TARGET_SET,
        "expected_targets": EXPECTED_TARGETS,
        "multi_surface_beta_capture_guardrail": beta_capture_guardrail,
        "explicitly_excluded": EXPLICITLY_EXCLUDED,
        "item_net_info_excluded": True,
        "blockers": blockers,
        "summary": summary,
        "non_claims": [
            "candidate-only fixture readiness for offline review only",
            "does not claim public SDK, public Transfer SDK, public API, public ABI, or public contract readiness",
            "does not claim runtime validation, runtime hook wiring, server validation, stable SDK, complete SDK, P0, or v1 completion readiness",
            "does not expose or decode Transfer ScriptStruct payloads, ItemNetInfo, ResourceHandle, cross-map state, object identity, mutation, or return override",
            "does not replace approved player-principal lifecycle runtime evidence",
        ],
    }
    report.update(REPORT_FALSE_FLAGS)
    report.update(REPORT_ZERO_FIELDS)
    return report


def main() -> int:
    args = parse_args()
    report = build_report(snapshot_root=args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
