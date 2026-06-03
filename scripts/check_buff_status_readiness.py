#!/usr/bin/env python3
"""Read-only readiness check for the internal Buff/status scalar boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from reflection_target_sets import TARGET_SETS
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SNAPSHOT_ROOT = REPO_ROOT / "tests" / "fixtures" / "ufunction_snapshots"
REPORT_SCHEMA = "obelisk.buff-status-readiness-check.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
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
    "class_pointer_ready",
    "complete_sdk_claim_allowed",
    "copied_payload_policy_ready",
    "copied_payload_ready",
    "counts_toward_complete_sdk_claim",
    "descriptor_ready",
    "dispatcher_ready",
    "identity_ready",
    "lifecycle_ready",
    "lifecycle_semantics_ready",
    "lookup_ready",
    "module_sdk_ready",
    "mutation_ready",
    "object_identity_ready",
    "object_pointer_ready",
    "promotion_ready",
    "proximity_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_buff_sdk_ready",
    "public_callback_ready",
    "public_capability_ready",
    "public_descriptor_ready",
    "public_header_ready",
    "public_module_sdk_ready",
    "public_sdk_ready",
    "release_ready",
    "resource_handle_ready",
    "return_override_ready",
    "runtime_observer_approved",
    "runtime_hook_ready",
    "runtime_ready",
    "runtime_wiring_ready",
    "sdk_ready",
    "stable_claim_allowed",
    "stable_sdk_ready",
    "support_tier_active",
    "support_tier_ready",
    "v1_accounted",
    "v1_complete",
    "v1_completion",
    "v1_completion_ready",
    "v1_ready",
}
FORBIDDEN_CLAIM_KEY_RE = re.compile(
    r"(?:resource[_-]?handle|return[_-]?override|public[_-]?(?:sdk|api|abi|surface|module|header|callback|descriptor|capability)|"
    r"(?:module[_-]?sdk|callback|descriptor|capability|dispatcher)[_-]?ready|"
    r"runtime[_-]?(?:ready|hook|observer|wiring)|v1[_-]?(?:ready|complete|completion|accounted)|"
    r"(?:complete|stable)[_-]?sdk[_-]?claim|support[_-]?tier|release[_-]?ready|"
    r"copied[_-]?payload[_-]?policy|lifecycle[_-]?semantics|"
    r"lookup[_-]?ready|mutation[_-]?ready|identity[_-]?ready|"
    r"(?:object|class)[_-]?(?:pointer|identity|contract|exposure)[_-]?ready)",
    re.IGNORECASE,
)
NEGATOR_RE = re.compile(
    r"\b(?:cannot|does\s+not|do\s+not|is\s+not|are\s+not|"
    r"must\s+not|no|not|without)\b",
    re.IGNORECASE,
)
AFTER_NEGATOR_RE = re.compile(
    r"\b(?:blocked|excluded|not\s+included|post-v1|post v1|false|redacted|candidate-only)\b",
    re.IGNORECASE,
)
FORBIDDEN_TEXT_CLAIM_RE = re.compile(
    r"\b(?:(?:Buff/status|Buff status|BuffStatus|Buff)\s+(?:SDK|API|module|callback|descriptor|capability)|"
    r"public\s+(?:Buff/status\s+|Buff\s+|module\s+)?(?:SDK|API|ABI|C\s+ABI|runtime\s+API|callback|descriptor|capability)|"
    r"runtime\s+(?:hook|observer|wiring|dispatcher|callback)|"
    r"identity|lookup|mutation|return[- ]override|ResourceHandle|Resource\s+Handle|"
    r"object/class\s+(?:pointer\s+)?(?:contract|exposure)|class\s+exposure|object\s+exposure|"
    r"copied\s+payload\s+policy|lifecycle\s+semantics|stacking\s+semantics|invalidation\s+semantics|"
    r"v1\s+(?:completion|complete|ready|release|accounted))\b",
    re.IGNORECASE,
)
READY_TEXT_CLAIM_RE = re.compile(
    r"\b(?:public\s+(?:SDK|API|ABI)|(?:Buff/status|Buff status|BuffStatus|Buff)\s+SDK|runtime|runtime\s+observer|runtime\s+hook|"
    r"module\s+SDK|header\s+callbacks?|promotion|v1|v1\s+SDK)\s+"
    r"(?:is\s+|are\s+)?(?:ready|complete|completion|available|published|enabled|approved)\b|"
    r"\b(?:ready|complete)\s+for\s+v1\b|"
    r"\bv1(?:\.0)?\s+(?:is\s+)?(?:stable|complete|completion|ready)\b|"
    r"\bcounts?\s+toward\s+(?:the\s+)?(?:complete|full|production)\s+SDK\s+claim\b|"
    r"\brelease\s+(?:readiness\s+)?(?:is\s+)?(?:ready|complete|satisfied|available|enabled|approved)\b|"
    r"\bsupport[- ]?tier\s+(?:is\s+)?(?:active|available|ready|enabled|supported|release[- ]supported)\b|"
    r"\bstable\s+SDK\s+(?:is\s+)?(?:allowed|ready|complete|available|enabled)\b",
    re.IGNORECASE,
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
        if key not in EXPECTED_TARGETS:
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


def validate_target_sets(blockers: list[dict[str, Any]]) -> dict[str, Any]:
    expanded: dict[str, list[str]] = {}
    for target_set in TARGET_SETS_USED:
        entries = TARGET_SETS.get(target_set)
        if not isinstance(entries, tuple):
            append_blocker(blockers, "target_set_missing", target_set=target_set)
            expanded[target_set] = []
            continue
        targets = []
        for entry in entries:
            schema, _, target = entry.partition(":")
            if schema == SNAPSHOT_SCHEMA:
                targets.append(target)
        expanded[target_set] = targets
    observed = set(expanded["buff-compact-intake"]) | set(expanded["buff-breadth-intake"])
    if observed != EXPECTED_TARGETS:
        append_blocker(
            blockers,
            "target_set_target_mismatch",
            missing=sorted(EXPECTED_TARGETS - observed),
            unexpected=sorted(observed - EXPECTED_TARGETS),
        )
    return {
        "target_sets": list(TARGET_SETS_USED),
        "compact_targets": sorted(expanded["buff-compact-intake"]),
        "breadth_targets": sorted(expanded["buff-breadth-intake"]),
    }


def validate_snapshot_common(key: str, payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        append_blocker(blockers, "snapshot_schema_mismatch", target=key, value=payload.get("schema"))
    source_sha = payload.get("_source_sha256")
    if not isinstance(source_sha, str) or SHA256_RE.fullmatch(source_sha) is None:
        append_blocker(blockers, "snapshot_sha256_malformed", target=key, value=source_sha)

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


def validate_copied_bool(target: str, field: str, prop: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    spec = EXPECTED_COPIED_BOOL_FIELDS[field]
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
    for regex in (FORBIDDEN_TEXT_CLAIM_RE, READY_TEXT_CLAIM_RE):
        for match in regex.finditer(text):
            if text_claim_is_negated(text, match.start(), match.end()):
                continue
            claims.append(match.group(0))
    return sorted(set(claims))


def reject_forbidden_claims(value: Any, blockers: list[dict[str, Any]], path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith("_"):
                continue
            key_lower = key.lower().replace("-", "_").replace(" ", "_")
            if key_lower in FORBIDDEN_READY_KEYS and child is not False and child is not None:
                append_blocker(blockers, "forbidden_readiness_claim", path=f"{path}.{key}", value=child)
            elif FORBIDDEN_CLAIM_KEY_RE.search(key) and child is True:
                append_blocker(blockers, "forbidden_positive_claim_key", path=f"{path}.{key}", value=child)
            reject_forbidden_claims(child, blockers, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            reject_forbidden_claims(child, blockers, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for claim in forbidden_text_claims(value):
            append_blocker(blockers, "forbidden_text_claim", path=path, claim=claim)


def validate_snapshots(snapshots: dict[str, dict[str, Any]], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    for key, payload in snapshots.items():
        validate_snapshot_common(key, payload, blockers)
        reject_forbidden_claims(payload, blockers, path=f"$.snapshots.{key}")

    missing_required = sorted(EXPECTED_TARGETS - set(snapshots))
    if missing_required:
        append_blocker(blockers, "required_target_snapshot_missing", missing=missing_required)

    copied: list[dict[str, Any]] = []
    redacted: list[dict[str, Any]] = []
    observed_copied: set[str] = set()
    observed_redacted: set[str] = set()
    zero_param_targets: list[dict[str, Any]] = []

    for target in sorted(EXPECTED_TARGETS):
        payload = snapshots.get(target)
        if payload is None:
            continue
        if target in EXPECTED_ZERO_PARAM_TARGETS:
            zero_param_targets.append(validate_zero_param_target(target, payload, blockers))
        for prop in properties_for(payload, blockers):
            field = property_key(target, prop)
            if field is None:
                append_blocker(blockers, "property_name_missing", target=target)
                continue
            if field in EXPECTED_COPIED_BOOL_FIELDS:
                copied.append(validate_copied_bool(target, field, prop, blockers))
                observed_copied.add(field)
                continue
            if field in EXPECTED_REDACTED_FIELDS:
                redacted.append(redact_field(target, field, prop, blockers))
                observed_redacted.add(field)
                continue
            class_name = prop.get("class_name")
            if class_name in {"ObjectProperty", "ClassProperty", "ArrayProperty", "StrProperty", "TextProperty"} or BUFF_OBJECT_OR_CLASS_RE.search(field):
                append_blocker(blockers, "unexpected_buff_redaction_candidate", field=field, property_class=class_name)
            else:
                append_blocker(blockers, "unexpected_buff_scalar", field=field, property_class=class_name)

    missing_copied = sorted(set(EXPECTED_COPIED_BOOL_FIELDS) - observed_copied)
    if missing_copied:
        append_blocker(blockers, "copied_bool_field_missing", missing=missing_copied)
    missing_redacted = sorted(set(EXPECTED_REDACTED_FIELDS) - observed_redacted)
    if missing_redacted:
        append_blocker(blockers, "required_redacted_field_missing", missing=missing_redacted)
    missing_zero_param = sorted(EXPECTED_ZERO_PARAM_TARGETS - {entry["target"] for entry in zero_param_targets})
    if missing_zero_param:
        append_blocker(blockers, "zero_param_target_missing", missing=missing_zero_param)

    return {
        "copied_bool_fields": sorted(entry["copied_field"] for entry in copied),
        "copied_bools": sorted(copied, key=lambda entry: entry["copied_field"]),
        "copied_bool_count": len(copied),
        "redacted_fields": sorted(entry["redacted_field"] for entry in redacted),
        "redactions": sorted(redacted, key=lambda entry: entry["redacted_field"]),
        "redacted_field_count": len(redacted),
        "zero_param_targets": sorted(zero_param_targets, key=lambda entry: entry["target"]),
        "compact_targets": sorted(EXPECTED_COMPACT_TARGETS),
        "breadth_targets": sorted(EXPECTED_BREADTH_TARGETS),
        "target_sets": list(TARGET_SETS_USED),
    }


def build_report(snapshot_root: Path = DEFAULT_SNAPSHOT_ROOT) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    target_set_summary = validate_target_sets(blockers)
    safe_snapshot_root = safe_path(snapshot_root, "--snapshot-root", blockers)
    snapshots = load_snapshots(safe_snapshot_root, blockers) if safe_snapshot_root is not None else {}
    summary = validate_snapshots(snapshots, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "fixture_only": True,
        "not_artifact_gate": True,
        "target_sets": target_set_summary,
        "snapshot_root": str(snapshot_root),
        "checked_targets": sorted(snapshots),
        "summary": summary,
        "buff_status_candidate_ready": ready,
        "copied_bool_boundary_ready": ready,
        "class_object_redaction_ready": ready,
        "zero_param_lifecycle_shape_ready": ready,
        "copied_payload_policy_ready": False,
        "lifecycle_semantics_ready": False,
        "buff_sdk_ready": False,
        "buff_status_sdk_ready": False,
        "sdk_ready": False,
        "module_sdk_ready": False,
        "public_sdk_ready": False,
        "public_buff_sdk_ready": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_callback_ready": False,
        "public_descriptor_ready": False,
        "public_capability_ready": False,
        "runtime_ready": False,
        "runtime_hook_ready": False,
        "runtime_wiring_ready": False,
        "runtime_observer_approved": False,
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
        "stable_claim_allowed": False,
        "complete_sdk_claim_allowed": False,
        "counts_toward_complete_sdk_claim": False,
        "promotion_ready": False,
        "blockers": blockers,
        "non_claims": [
            "candidate readiness is internal planning evidence only",
            "no public Buff/status SDK, public C ABI, public runtime API, or v1 completion",
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
