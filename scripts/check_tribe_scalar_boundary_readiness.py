#!/usr/bin/env python3
"""Read-only readiness check for the internal Tribe scalar-boundary lane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from reflection_target_sets import (
    NON_AUTHORIZING_READY_DOES_NOT_SATISFY,
    NON_AUTHORIZING_READY_SCOPE,
    side_lane_noncanonical_bool_payload_issues,
    side_lane_fail_closed_source_artifact_issues,
)
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
REPORT_SCHEMA = "obelisk.tribe-scalar-boundary-readiness-check.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
TARGET_SET = "tribe-compact-intake"
REQUIRED_CONTROL_TARGET = "ShooterPlayerController.ServerRequestTribeLog"
REQUIRED_TARGETS = {
    "ShooterPlayerController.AllowTribeGroupPermission",
    "ShooterPlayerController.IsInTribe",
    REQUIRED_CONTROL_TARGET,
}
REDACTION_TARGETS = {
    "ShooterPlayerController.ClientReceiveMyTribeOnlineList",
    "ShooterPlayerController.ClientReceiveActiveMissionTags",
}
CONSIDERED_TARGETS = REQUIRED_TARGETS | REDACTION_TARGETS
BETA_CAPTURE_STATUS = "future_capture_targets_only"
BETA_CAPTURE_TARGET_STATUS = "future_capture_target"
BETA_CAPTURE_GATE = "dedicated_beta_capture_check_required"
BETA_CAPTURE_SURFACE = "tribe"
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
    "public_tribe_sdk_ready",
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
EXPECTED_ACCEPTED_FIELDS = {
    "ShooterPlayerController.AllowTribeGroupPermission.TribeGroupPermission": {
        "class_name": "ByteProperty",
        "direction": "in",
        "element_size": 1,
        "offset_internal": 0,
        "type": "byte_enum",
    },
    "ShooterPlayerController.AllowTribeGroupPermission.ReturnValue": {
        "class_name": "BoolProperty",
        "direction": "return",
        "element_size": 1,
        "offset_internal": 16,
        "type": "bool",
    },
    "ShooterPlayerController.IsInTribe.ReturnValue": {
        "class_name": "BoolProperty",
        "direction": "return",
        "element_size": 1,
        "offset_internal": 0,
        "type": "bool",
    },
}
EXPECTED_REDACTED_FIELDS = {
    "ShooterPlayerController.AllowTribeGroupPermission.OnObject": "object_ref_onobject",
    "ShooterPlayerController.ClientReceiveMyTribeOnlineList.OnlinePlayerIDs": "online_list_array_identity",
    "ShooterPlayerController.ClientReceiveActiveMissionTags.MissionTags": "array_name_payload",
}
EXPECTED_REQUIRED_REDACTIONS = {
    "ShooterPlayerController.AllowTribeGroupPermission.OnObject",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
POSITIVE_PROGRESS_RATIO_RE = re.compile(r"^\s*[1-9][0-9]*\s*/\s*[1-9][0-9]*\s*$")
IDENTITY_FIELD_RE = re.compile(
    r"(?:player|steam|eos|unique[_-]?net|tribe[_-]?id|tribeid|onlineplayerids|"
    r"owner|team|rank|group|identity|principal|account|session|profile)",
    re.IGNORECASE,
)
STRING_OR_LOG_FIELD_RE = re.compile(r"(?:log|message|motd|notice|text|string|payload)", re.IGNORECASE)
FORBIDDEN_READY_KEYS = {
    "abi_ready",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "candidate_capture_ready",
    "complete_sdk_claim_allowed",
    "complete_sdk_claim_progress_contribution",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "debug_capture_ready",
    "identity_ready",
    "live_ops_ready",
    "lookup_ready",
    "mutation_authority_ready",
    "mutation_ready",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_ready",
    "player_principal_replacement_ready",
    "promotion_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_module_ready",
    "public_sdk_ready",
    "public_surface",
    "replaces_player_principal_evidence",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_capture_ready",
    "runtime_evidence_ready",
    "runtime_ready",
    "runtime_work_authorized",
    "sdk_ready",
    "server_work_authorized",
    "source_readiness",
    "source_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "tribe_sdk_ready",
    "v1_accounted",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:resource[_-]?handle|return[_-]?override|public[_-]?(?:sdk|api|abi|surface)|"
    r"public[_-]?module|approved[_-]?runtime[_-]?evidence[_-]?(?:accepted|present|ready)|"
    r"runtime[_-]?(?:ready|hook|observer|wiring|capture|evidence|work)|live[_-]?ops|"
    r"(?:beta|candidate|debug)[_-]?capture[_-]?(?:accepted|approved|enabled|progress|ready|runtime|sdk)|"
    r"v1[_-]?(?:ready|complete|completion)|p0[_-]?dependency[_-]?chain|counts[_-]?toward|"
    r"(?:replace|replaces|replacement|supersede|supersedes|supersession)[_-]?(?:player[_-]?principal|principal)|"
    r"player[_-]?principal[_-]?(?:evidence[_-]?)?(?:replacement|replaced|satisfied|ready)|"
    r"lookup[_-]?ready|mutation[_-]?ready|identity[_-]?ready)",
    re.IGNORECASE,
)
CLAIM_CONTEXT_KEY_RE = re.compile(
    r"(?:public|sdk|api|abi|module|runtime|debug|beta|capture|live[_-]?ops|source|v1|p0|"
    r"complete|completion|stable|promotion|resource[_-]?handle|return[_-]?override|"
    r"approved[_-]?runtime[_-]?evidence|blocker|route|"
    r"identity|lookup|mutation|player[_-]?principal|principal|replacement|replace)",
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|excludes?|is\s+not|are\s+not|must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1|false|redacted|candidate-only)\b",
    re.IGNORECASE,
)
FORBIDDEN_TEXT_CLAIM_RE = re.compile(
    r"\bTribe\s+(?:SDK|API|module|callback|descriptor|capability)\b|"
    r"\bpublic\s+(?:Tribe\s+)?(?:SDK|API|ABI|C\s+ABI|module|callback|descriptor|capability)\b|"
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
    r"\b(?:Tribe\s+SDK|public\s+SDK|public\s+ABI|runtime|runtime\s+observer|runtime\s+hook|"
    r"module\s+SDK|promotion|v1|v1\s+SDK)\s+"
    r"(?:is\s+|are\s+)?(?:ready|complete|completion|available|published|enabled|approved|allowed|unblocked|unlocked)\b|"
    r"\b(?:ready|complete|available|enabled|allowed|unblocked|unlocked)\s+for\s+v1\b|"
    r"\bv1(?:\.0)?\s+(?:is\s+)?(?:stable|complete|completion|ready|allowed|unblocked|unlocked)\b|"
    r"\b(?:counts?|contributes?|credits?)\s+(?:toward|for|to)\s+(?:the\s+)?"
    r"(?:complete|full|production|public|v1)\s+SDK\s+claim\b",
    re.IGNORECASE,
)
POSITIVE_STATUS_VALUES = frozenset(
    {
        "accepted",
        "active",
        "available",
        "complete",
        "enabled",
        "promoted",
        "ready",
        "release-ready",
        "release-supported",
        "runtime-ready",
        "sdk-ready",
        "stable",
        "stable-ready",
        "supported",
        "validated",
        "v1-ready",
    }
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Tribe scalar-boundary candidate readiness from sanitized snapshots only."
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
    parsed = parse_hex_or_int(value)
    return parsed == 1


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


def beta_capture_role(target: str) -> str:
    if target == REQUIRED_CONTROL_TARGET:
        return "zero_param_control"
    if target in REQUIRED_TARGETS:
        return "required_scalar_boundary"
    return "redaction_boundary"


def build_beta_capture_prep() -> dict[str, Any]:
    targets: list[dict[str, Any]] = []
    for target in sorted(CONSIDERED_TARGETS):
        targets.append(
            {
                "target": target,
                "surface": BETA_CAPTURE_SURFACE,
                "target_set": TARGET_SET,
                "status": BETA_CAPTURE_TARGET_STATUS,
                "target_role": beta_capture_role(target),
                "source_evidence": "candidate_only_sanitized_snapshot_fixture",
                "capture_gate": BETA_CAPTURE_GATE,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "runtime_capture_ready": False,
                "sdk_ready": False,
                "sdk_progress": 0,
                "replaces_player_principal_evidence": False,
                **runtime_evidence_blocker_non_claims(),
                "accepted_scalar_fields": sorted(
                    field for field in EXPECTED_ACCEPTED_FIELDS if field_target(field) == target
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
        "source_evidence": "candidate_only_sanitized_snapshot_fixtures",
        "capture_gate": BETA_CAPTURE_GATE,
        "public_sdk_ready": False,
        "public_tribe_sdk_ready": False,
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


def validate_beta_capture_entry(
    entry: Any,
    blockers: list[dict[str, Any]],
    index: int,
    expected_targets: set[str],
    label: str,
) -> str | None:
    if not isinstance(entry, dict):
        append_blocker(blockers, "beta_capture_target_malformed", index=index, label=label)
        return None
    target = entry.get("target")
    if not isinstance(target, str) or target not in expected_targets:
        append_blocker(blockers, "beta_capture_target_mismatch", index=index, label=label, target=target)
    if entry.get("surface") != BETA_CAPTURE_SURFACE:
        append_blocker(blockers, "beta_capture_surface_mismatch", index=index, label=label, value=entry.get("surface"))
    if entry.get("target_set") != TARGET_SET:
        append_blocker(blockers, "beta_capture_target_set_mismatch", index=index, label=label, value=entry.get("target_set"))
    if entry.get("status") not in {BETA_CAPTURE_TARGET_STATUS, None}:
        append_blocker(blockers, "beta_capture_target_status_mismatch", index=index, label=label, value=entry.get("status"))
    if entry.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_gate_mismatch", index=index, label=label, value=entry.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in entry and not claim_value_is_false_or_zero(entry.get(key)):
            append_blocker(
                blockers,
                "beta_capture_readiness_overclaim",
                index=index,
                label=label,
                field=key,
                value=entry.get(key),
            )
    return target if isinstance(target, str) else None


def validate_beta_capture_prep(
    value: Any,
    blockers: list[dict[str, Any]],
    *,
    expected_targets: set[str],
    label: str,
) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        append_blocker(blockers, "beta_capture_prep_malformed", label=label)
        return
    if value.get("status") != BETA_CAPTURE_STATUS:
        append_blocker(blockers, "beta_capture_prep_status_mismatch", label=label, value=value.get("status"))
    if value.get("surface") not in {BETA_CAPTURE_SURFACE, None}:
        append_blocker(blockers, "beta_capture_prep_surface_mismatch", label=label, value=value.get("surface"))
    if value.get("target_set") != TARGET_SET:
        append_blocker(blockers, "beta_capture_prep_target_set_mismatch", label=label, value=value.get("target_set"))
    if value.get("capture_gate") not in {BETA_CAPTURE_GATE, None}:
        append_blocker(blockers, "beta_capture_prep_gate_mismatch", label=label, value=value.get("capture_gate"))
    for key in BETA_CAPTURE_FALSE_OR_ZERO_FIELDS:
        if key in value and not claim_value_is_false_or_zero(value.get(key)):
            append_blocker(blockers, "beta_capture_readiness_overclaim", label=label, field=key, value=value.get(key))

    if "targets" in value:
        targets = value.get("targets")
        if not isinstance(targets, list):
            append_blocker(blockers, "beta_capture_targets_malformed", label=label)
            return
        observed = {
            target
            for index, entry in enumerate(targets)
            if (target := validate_beta_capture_entry(entry, blockers, index, expected_targets, label)) in expected_targets
        }
    else:
        single_entry = dict(value)
        single_entry["status"] = value.get("target_status", BETA_CAPTURE_TARGET_STATUS)
        observed_target = validate_beta_capture_entry(single_entry, blockers, 0, expected_targets, label)
        observed = {observed_target} if observed_target in expected_targets else set()
    if observed != expected_targets:
        append_blocker(
            blockers,
            "beta_capture_target_coverage_mismatch",
            label=label,
            missing=sorted(expected_targets - observed),
            unexpected=sorted(observed - expected_targets),
        )


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


def first_target(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        append_blocker(blockers, "snapshot_target_count_mismatch", path=payload.get("_source_path"))
        return None
    return targets[0]


def load_snapshots(snapshot_root: Path, blockers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
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
        if key not in CONSIDERED_TARGETS:
            continue
        if key in snapshots:
            append_blocker(
                blockers,
                "duplicate_target_snapshot",
                target=key,
                first=snapshots[key].get("_source_path"),
                duplicate=str(path),
            )
            continue
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


def validate_snapshot_common(key: str, payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        append_blocker(blockers, "snapshot_schema_mismatch", target=key, value=payload.get("schema"))
    source_sha = payload.get("_source_sha256")
    if not isinstance(source_sha, str) or SHA256_RE.fullmatch(source_sha) is None:
        append_blocker(blockers, "snapshot_sha256_malformed", target=key, value=source_sha)
    validate_beta_capture_prep(
        payload.get("beta_capture_prep"),
        blockers,
        expected_targets={key},
        label=f"snapshot:{key}",
    )

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("status") != "candidate-only":
        append_blocker(blockers, "snapshot_evidence_status_mismatch", target=key)
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
        append_blocker(blockers, "property_status_mismatch", field=field, value=prop.get("status"))
    for key in ("membership_status", "class_membership_status", "outer_membership_status"):
        if prop.get(key) != "candidate-uobject":
            append_blocker(blockers, "property_membership_mismatch", target=target, field=field, member=key)
    if prop.get("array_dim") != 1:
        append_blocker(blockers, "property_array_dim_mismatch", field=field, value=prop.get("array_dim"))


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


def validate_byte_enum_field(field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    enum_candidate = prop.get("enum_candidate")
    if not isinstance(enum_candidate, dict) or enum_candidate.get("status") != "candidate":
        append_blocker(blockers, "byte_enum_candidate_missing", field=field)
        return
    values = enum_candidate.get("values")
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        append_blocker(blockers, "byte_enum_values_missing", field=field)


def validate_accepted_field(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    spec = EXPECTED_ACCEPTED_FIELDS[field]
    validate_property_candidate(target, field, prop, blockers)
    for key in ("class_name", "element_size", "offset_internal"):
        if prop.get(key) != spec[key]:
            append_blocker(
                blockers,
                "accepted_scalar_shape_mismatch",
                field=field,
                metadata_key=key,
                expected=spec[key],
                value=prop.get(key),
            )
    if spec["type"] == "bool":
        validate_bool_field(field, prop, blockers)
    elif spec["type"] == "byte_enum":
        validate_byte_enum_field(field, prop, blockers)
    return {
        "accepted_field": field,
        "direction": spec["direction"],
        "type": spec["type"],
        "property_class": prop.get("class_name"),
        "offset_internal": prop.get("offset_internal"),
        "element_size": prop.get("element_size"),
        "source_snapshot": target,
    }


def redact_field(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    validate_property_candidate(target, field, prop, blockers)
    class_name = prop.get("class_name")
    reason = EXPECTED_REDACTED_FIELDS.get(field)
    if field == "ShooterPlayerController.AllowTribeGroupPermission.OnObject" and class_name != "ObjectProperty":
        append_blocker(blockers, "onobject_redaction_shape_mismatch", field=field, property_class=class_name)
    if field == "ShooterPlayerController.ClientReceiveMyTribeOnlineList.OnlinePlayerIDs" and class_name != "ArrayProperty":
        append_blocker(blockers, "online_list_array_shape_mismatch", field=field, property_class=class_name)
    if field == "ShooterPlayerController.ClientReceiveActiveMissionTags.MissionTags" and class_name != "ArrayProperty":
        append_blocker(blockers, "mission_tags_array_shape_mismatch", field=field, property_class=class_name)
    if class_name in {"StrProperty", "TextProperty"} or STRING_OR_LOG_FIELD_RE.search(field):
        append_blocker(blockers, "string_or_log_payload_present", field=field, property_class=class_name)
    if IDENTITY_FIELD_RE.search(field):
        reason = reason or "identity_field_redacted"
    return {
        "redacted_field": field,
        "reason": reason or "not_in_scalar_allowlist",
        "property_class": class_name,
        "source_snapshot": target,
    }


def validate_control(snapshot: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    target_payload = first_target(snapshot, blockers)
    if target_payload is None:
        return {"target": REQUIRED_CONTROL_TARGET, "present": True, "required": True, "ready": False}
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
            "server_request_tribe_log_not_zero_param",
            num_parms=target_payload.get("num_parms"),
            parms_size=target_payload.get("parms_size"),
            return_value_offset=target_payload.get("return_value_offset"),
        )
    return {
        "target": REQUIRED_CONTROL_TARGET,
        "present": True,
        "required": True,
        "ready": zero_param,
        "zero_param": zero_param,
    }


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
    if normalized in {"accepted_for_internal_planning", "accepted_scalar_fields", "accepted_scalars"}:
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
        local_context = claim_context or beta_capture_artifact_context(value)
        for key, child in value.items():
            if key.startswith("_"):
                continue
            key_lower = normalized_claim_key(key)
            child_path = f"{path}.{key}"
            child_context = local_context or claim_context_key(key)
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
            elif not preserved_runtime_missing and key_lower in FORBIDDEN_READY_KEYS and child is not False and child is not None:
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif not preserved_runtime_missing and FORBIDDEN_CLAIM_KEY_RE.search(key) and child is True:
                append_blocker(blockers, "forbidden_positive_claim_key", path=child_path, value=child)
            elif key_lower in {"source_accepted", "source_stable", "source_status"} and positive_status_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif (
                child_context
                and ("progress" in key_lower or "credit" in key_lower or "ratio" in key_lower)
                and positive_progress_claim(child)
            ):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif child_context and key_lower in {"accepted", "ready", "stable", "status"} and positive_status_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            elif child_context and isinstance(child, str) and positive_status_claim(child):
                append_blocker(blockers, "forbidden_readiness_claim", path=child_path, value=child)
            reject_forbidden_claims(child, blockers, child_path, claim_context=child_context and not preserved_runtime_missing)
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


def validate_snapshots(snapshots: dict[str, dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    for key, payload in snapshots.items():
        validate_snapshot_common(key, payload, blockers)
        blockers.extend(
            side_lane_fail_closed_source_artifact_issues(
                payload,
                expected_target_sets=(TARGET_SET,),
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

    missing_required = sorted(REQUIRED_TARGETS - set(snapshots))
    if missing_required:
        append_blocker(blockers, "required_target_snapshot_missing", missing=missing_required)

    accepted: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    observed_redacted_fields: set[str] = set()
    observed_accepted_fields: set[str] = set()

    for target in sorted(REQUIRED_TARGETS | REDACTION_TARGETS):
        payload = snapshots.get(target)
        if payload is None:
            continue
        for prop in properties_for(payload, blockers):
            field = property_key(target, prop)
            if field is None:
                append_blocker(blockers, "property_name_missing", target=target)
                continue
            if field in EXPECTED_ACCEPTED_FIELDS:
                accepted.append(validate_accepted_field(target, field, prop, blockers))
                observed_accepted_fields.add(field)
                continue
            if field in EXPECTED_REDACTED_FIELDS or target in REDACTION_TARGETS:
                redacted.append(redact_field(target, field, prop, blockers))
                observed_redacted_fields.add(field)
                continue
            if IDENTITY_FIELD_RE.search(field):
                append_blocker(blockers, "forbidden_identity_field_in_required_target", field=field)
            if prop.get("class_name") in {"ObjectProperty", "ArrayProperty", "StrProperty", "TextProperty"}:
                append_blocker(
                    blockers,
                    "unexpected_redaction_candidate_in_required_target",
                    field=field,
                    property_class=prop.get("class_name"),
                )
            else:
                append_blocker(
                    blockers,
                    "unexpected_required_target_scalar",
                    field=field,
                    property_class=prop.get("class_name"),
                )

    missing_accepted = sorted(set(EXPECTED_ACCEPTED_FIELDS) - observed_accepted_fields)
    if missing_accepted:
        append_blocker(blockers, "accepted_scalar_field_missing", missing=missing_accepted)
    missing_redacted = sorted(EXPECTED_REQUIRED_REDACTIONS - observed_redacted_fields)
    if missing_redacted:
        append_blocker(blockers, "required_redacted_field_missing", missing=missing_redacted)

    control = {"target": REQUIRED_CONTROL_TARGET, "present": False, "required": True, "ready": False, "zero_param": None}
    if REQUIRED_CONTROL_TARGET in snapshots:
        control = validate_control(snapshots[REQUIRED_CONTROL_TARGET], blockers)
        for prop in properties_for(snapshots[REQUIRED_CONTROL_TARGET], blockers):
            field = property_key(REQUIRED_CONTROL_TARGET, prop) or REQUIRED_CONTROL_TARGET
            redacted.append(redact_field(REQUIRED_CONTROL_TARGET, field, prop, blockers))

    return {
        "accepted_scalar_fields": sorted(entry["accepted_field"] for entry in accepted),
        "accepted_scalars": sorted(accepted, key=lambda entry: entry["accepted_field"]),
        "redacted_fields": sorted(entry["redacted_field"] for entry in redacted),
        "redactions": sorted(redacted, key=lambda entry: entry["redacted_field"]),
        "required_controls": [control],
        "optional_controls": [],
        "required_targets": sorted(REQUIRED_TARGETS),
        "redaction_targets_present": sorted(set(snapshots) & REDACTION_TARGETS),
        "target_set": TARGET_SET,
    }


def build_report(snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    safe_snapshot_root = safe_path(snapshot_root, "--snapshot-root", blockers)
    snapshots = load_snapshots(safe_snapshot_root, blockers) if safe_snapshot_root is not None else {}
    summary = validate_snapshots(snapshots, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "ready_scope": NON_AUTHORIZING_READY_SCOPE,
        "does_not_satisfy_readiness": list(NON_AUTHORIZING_READY_DOES_NOT_SATISFY),
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "fixture_only": True,
        "not_artifact_gate": True,
        "target_set": TARGET_SET,
        "snapshot_root": str(snapshot_root),
        "checked_targets": sorted(snapshots),
        "summary": summary,
        "tribe_scalar_boundary_ready": ready,
        "scalar_boundary_ready": ready,
        "server_request_tribe_log_control_ready": summary["required_controls"][0]["ready"],
        "beta_capture_prep": build_beta_capture_prep(),
        "public_sdk_ready": False,
        "public_tribe_sdk_ready": False,
        "public_abi_ready": False,
        "public_module_ready": False,
        "runtime_ready": False,
        "runtime_capture_ready": False,
        "runtime_observer_approved": False,
        "live_ops_ready": False,
        **runtime_evidence_blocker_non_claims(),
        "sdk_progress": 0,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "return_override_ready": False,
        "resource_handle_ready": False,
        "v1_completion_ready": False,
        "promotion_ready": False,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "no public Tribe SDK, public C ABI, public runtime API, or v1 completion",
            "no runtime hook wiring, observer window, dispatcher wiring, or server validation",
            "no tribe/player identity, online-list payload exposure, lookup, ownership, or ResourceHandle",
            "no strings, tribe log payloads, MOTD, notices, raw params, UE pointers, or object references exposed",
            "no mutation, return override, authority policy enforcement, or UE function call",
            "does not replace player-principal lifecycle evidence",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
