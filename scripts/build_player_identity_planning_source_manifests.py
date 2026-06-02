#!/usr/bin/env python3
"""Build source-aligned player identity planning manifests offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import bind_player_identity_planning_sources as binder
import build_redacted_ufunction_signatures
import check_player_identity_lifecycle_anchor_candidates as lifecycle_checker
import check_player_identity_principal_invalidation_policy as principal_checker
import protected_paths


REPORT_SCHEMA = "obelisk.player-identity-planning-source-manifests-build-report.v1"
FIRST_EVIDENCE_OUTPUT_NAME = "players-identity-first-evidence.json"
REPORT_OUTPUT_NAME = "player-identity-planning-source-manifests-report.json"
LIFECYCLE_TARGETS = (
    ("session_start", "ShooterGameMode.HandleNewPlayer"),
    ("session_end", "ShooterGameMode.OnLogout"),
)
NON_CLAIMS = [
    "offline deterministic planning-manifest build only",
    "no runtime or server operation was performed",
    "no ARK process was started, stopped, restarted, attached, or observed",
    "no public player identity is promoted",
    "no permissions/admin, command response, or commands/replies surface is promoted",
    "no public SDK, public ABI, release, or v1 completion readiness is claimed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root used for first-evidence and focal lifecycle snapshots.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for generated planning manifests.")
    parser.add_argument("--json", action="store_true", help="Emit the build report JSON to stdout.")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: top-level JSON must be an object")
    return payload


def safe_snapshot_root(path: Path) -> Path:
    protected_paths.reject_symlink_component(path, "snapshot-root")
    resolved = protected_paths.reject_protected_input_path(path, "snapshot-root")
    if not resolved.is_dir():
        raise SystemExit(f"snapshot-root is not a directory: {resolved}")
    return resolved


def manifest_target_paths(snapshot_root: Path) -> dict[str, Path]:
    manifest = load_json(snapshot_root / "manifest.json", "snapshot manifest")
    sha_prefix = manifest.get("sha_prefix")
    targets = manifest.get("targets")
    if not isinstance(sha_prefix, str) or not sha_prefix:
        raise SystemExit("snapshot manifest sha_prefix missing")
    if not isinstance(targets, list):
        raise SystemExit("snapshot manifest targets must be a list")
    result: dict[str, Path] = {}
    for entry in targets:
        if not isinstance(entry, dict):
            continue
        outer = entry.get("outer")
        name = entry.get("name")
        module = entry.get("module")
        file_name = entry.get("file")
        if not all(isinstance(value, str) and value for value in (outer, name, module, file_name)):
            continue
        result[f"{outer}.{name}"] = snapshot_root / sha_prefix / module / file_name
    return result


def snapshot_target_payload(path: Path, target: str) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path, f"{target} snapshot")
    if payload.get("schema") != lifecycle_checker.SNAPSHOT_SCHEMA:
        raise SystemExit(f"{target} snapshot schema mismatch")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{target} snapshot must contain exactly one target")
    target_payload = targets[0]
    identity = target_payload.get("target")
    if not isinstance(identity, dict):
        raise SystemExit(f"{target} snapshot target identity missing")
    observed = f"{identity.get('outer_name')}.{identity.get('name')}"
    if observed != target:
        raise SystemExit(f"{target} snapshot target mismatch: observed {observed}")
    return payload, target_payload


def property_direction(name: str) -> str:
    if name == "ReturnValue":
        return "out"
    return "in"


def bool_masks(prop: dict[str, Any]) -> dict[str, str] | None:
    if prop.get("class_name") != "BoolProperty":
        return None
    byte_mask = prop.get("byte_mask", "0x1")
    field_mask = prop.get("field_mask", "0xff")
    if not isinstance(byte_mask, str) or not isinstance(field_mask, str):
        raise SystemExit("BoolProperty mask fields must be strings")
    return {"byte_mask": "0x01" if byte_mask == "0x1" else byte_mask, "field_mask": field_mask}


def lifecycle_field_from_property(prop: dict[str, Any], *, target: str, expected: tuple[Any, ...]) -> dict[str, Any]:
    expected_name, expected_class, expected_offset, expected_size = expected
    name = prop.get("name")
    property_class = prop.get("class_name")
    offset = prop.get("offset_internal")
    element_size = prop.get("element_size")
    array_dim = prop.get("array_dim")
    if name != expected_name:
        raise SystemExit(f"{target}: expected field {expected_name}, observed {name}")
    if property_class != expected_class:
        raise SystemExit(f"{target}.{name}: expected class {expected_class}, observed {property_class}")
    if offset != int(str(expected_offset), 16):
        raise SystemExit(f"{target}.{name}: expected offset {expected_offset}, observed {offset!r}")
    if element_size != expected_size:
        raise SystemExit(f"{target}.{name}: expected element_size {expected_size}, observed {element_size!r}")
    if array_dim != 1:
        raise SystemExit(f"{target}.{name}: expected array_dim 1, observed {array_dim!r}")
    if prop.get("status") != "candidate":
        raise SystemExit(f"{target}.{name}: property status must be candidate")

    entry = {
        "name": name,
        "source_property_class": property_class,
        "direction": property_direction(str(name)),
        "offset": expected_offset,
        "element_size": element_size,
        "array_dim": array_dim,
        "classification": "recognition_only" if property_class == "ObjectProperty" else "copied_candidate",
        "copied_scalar_eligibility": (
            "recognition_only_object" if property_class == "ObjectProperty" else "candidate_non_identity_scalar"
        ),
    }
    masks = bool_masks(prop)
    if masks is not None:
        entry["bool_masks"] = masks
    return entry


def lifecycle_anchor(
    *,
    role: str,
    target: str,
    snapshot_id: str,
    snapshot_path: Path,
    snapshot_payload: dict[str, Any],
    target_payload: dict[str, Any],
) -> dict[str, Any]:
    expected = lifecycle_checker.LIFECYCLE_LAYOUT_CANDIDATE_TARGETS[target]
    property_chain = target_payload.get("property_chain")
    properties = property_chain.get("properties") if isinstance(property_chain, dict) else None
    if not isinstance(properties, list):
        raise SystemExit(f"{target}: property_chain.properties missing")
    expected_fields = expected["fields"]
    if len(properties) != len(expected_fields):
        raise SystemExit(f"{target}: expected {len(expected_fields)} fields, observed {len(properties)}")
    if target_payload.get("num_parms") != expected["num_parms"]:
        raise SystemExit(f"{target}: num_parms mismatch")
    if target_payload.get("parms_size") != expected["parms_size"]:
        raise SystemExit(f"{target}: parms_size mismatch")

    outer, _, function = target.rpartition(".")
    evidence = snapshot_payload.get("evidence") if isinstance(snapshot_payload.get("evidence"), dict) else {}
    fields = [
        lifecycle_field_from_property(prop, target=target, expected=expected_field)
        for prop, expected_field in zip(properties, expected_fields)
    ]
    return {
        "role": role,
        "target": target,
        "outer": outer,
        "function": function,
        "acceptance_status": "layout_accepted_candidate_only",
        "accepted": True,
        "function_flags": target_payload.get("function_flags"),
        "num_parms": target_payload.get("num_parms"),
        "parms_size": target_payload.get("parms_size"),
        "return_value_offset": target_payload.get("return_value_offset", "0xffffffff"),
        "property_order": [field["name"] for field in fields],
        "fields": fields,
        "evidence": {
            "source_snapshot": snapshot_id,
            "source_snapshot_sha256": sha256_file(snapshot_path),
            "snapshot_schema": lifecycle_checker.SNAPSHOT_SCHEMA,
            "source_kind": "sanitized_snapshot",
            "binary_sha256": evidence.get("ark_binary_sha256"),
        },
        "corroboration": {
            "status": "second_source_accepted",
            "second_source_report_sha256": None,
            "static_report_sha256": None,
        },
        "blockers": [],
    }


def build_lifecycle_manifest(first_evidence: dict[str, Any], snapshot_root: Path) -> dict[str, Any]:
    paths = manifest_target_paths(snapshot_root)
    anchors: list[dict[str, Any]] = []
    for index, (role, target) in enumerate(LIFECYCLE_TARGETS, start=1):
        path = paths.get(target)
        if path is None:
            raise SystemExit(f"snapshot manifest does not contain required lifecycle target: {target}")
        snapshot_payload, target_payload = snapshot_target_payload(path, target)
        anchors.append(
            lifecycle_anchor(
                role=role,
                target=target,
                snapshot_id=f"focal-snapshot-{index:04d}",
                snapshot_path=path,
                snapshot_payload=snapshot_payload,
                target_payload=target_payload,
            )
        )

    artifact = first_evidence.get("artifact_identity")
    if not isinstance(artifact, dict):
        raise SystemExit("first-evidence artifact_identity missing")
    source_artifact_ids = binder.first_evidence_readiness.first_evidence_source_artifact_ids(first_evidence)
    if not source_artifact_ids:
        raise SystemExit("first-evidence artifact_identity.source_artifact_ids is empty")
    return {
        "schema": lifecycle_checker.SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "input_target_set": lifecycle_checker.TARGET_SET,
        "snapshot_root": "redacted",
        "artifact_identity": {
            "ark_binary_sha256": artifact.get("ark_binary_sha256"),
            "obelisk_commit": artifact.get("obelisk_commit"),
            "build_type": artifact.get("build_type"),
            "target_set_revision": lifecycle_checker.TARGET_SET_REVISION,
            "source_artifact_ids": source_artifact_ids,
            "path_redacted": True,
        },
        "candidate_anchors": anchors,
        "lifecycle_acceptance": {
            "session_start_accepted": True,
            "session_end_accepted": True,
            "accepted_start_targets": ["ShooterGameMode.HandleNewPlayer"],
            "accepted_end_targets": ["ShooterGameMode.OnLogout"],
            "blockers": ["principal_invalidation_semantics_unresolved"],
        },
        "principal_policy": {
            "public_principal_ready": False,
            "copied_public_identifier": None,
            "principal_copy_policy": "unresolved",
            "privacy_policy": "unresolved",
            "invalidation_semantics": "unresolved",
            "logging_policy": "identity_values_not_logged",
        },
        "promotion_gate": {
            "ready": False,
            "ready_scope": "planning_only",
            "promotion_ready": False,
            "blockers": ["public_principal_policy_unresolved"],
        },
        "safety_summary": {
            "candidate_anchor_count": len(anchors),
            "accepted_anchor_count": len(anchors),
            "field_count": sum(len(anchor["fields"]) for anchor in anchors),
            "identity_redacted_field_count": 0,
            "copied_candidate_count": sum(
                1
                for anchor in anchors
                for field in anchor["fields"]
                if field["classification"] == "copied_candidate"
            ),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(lifecycle_checker.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(lifecycle_checker.REQUIRED_NON_CLAIMS),
    }


def build_principal_manifest(lifecycle: dict[str, Any]) -> dict[str, Any]:
    source_binding = binder.expected_lifecycle_source_binding(lifecycle, {"artifact_identity": lifecycle["artifact_identity"]})
    return {
        "schema": principal_checker.SCHEMA,
        "artifact_status": "candidate_only",
        "readiness_classification": "planning_only",
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "lifecycle_layout_source": {
            "status": "candidate_layout_consumable",
            "accepted_layout_only": True,
            "start_anchor": "ShooterGameMode.HandleNewPlayer",
            "end_anchor": "ShooterGameMode.OnLogout",
            "principal_invalidation_evidence": "candidate_policy_only",
            "source_binding": source_binding,
        },
        "principal": {
            "kind": "copied_opaque_principal",
            "copied": True,
            "ownership": "obelisk_owned_copy",
            "public_identity": "opaque_principal_only",
            "reversible": False,
            "stable_across_processes": False,
            "real_identity_source": None,
            "fields": [
                {
                    "name": "principal",
                    "type": "opaque_bytes",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "opaque_principal",
                },
                {
                    "name": "generation",
                    "type": "uint64",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "state",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "scope_flags",
                    "type": "uint64_flags",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
                {
                    "name": "privacy_class",
                    "type": "enum",
                    "copied": True,
                    "source": "obelisk_owned_copy",
                    "consumer_visible": True,
                    "privacy_class": "lifecycle_metadata",
                },
            ],
        },
        "generation": {
            "field": "generation",
            "zero_invalid": True,
            "increments_on": [
                "session_start",
                "logout_or_disconnect_invalidation",
                "reconnect_after_invalidation",
                "transfer_or_download_edge",
                "duplicate_or_conflicting_identity",
                "server_restart",
                "plugin_reload",
            ],
        },
        "state": {"field": "state", "allowed": ["unknown", "active", "invalidated"], "fail_closed_states": ["unknown", "invalidated"]},
        "scope_flags": {
            "field": "scope_flags",
            "allowed_flags": ["process_local", "session_local", "not_cross_cluster"],
            "forbidden_flags": ["persistent", "cross_process", "cross_cluster"],
        },
        "privacy_class": {
            "field": "privacy_class",
            "allowed": ["opaque_principal", "internal_sensitive", "redacted"],
            "public_value": "opaque_principal",
        },
        "invalidation_cases": [
            {
                "case": "logout_or_disconnect",
                "trigger": "ShooterGameMode.OnLogout",
                "generation_action": "increment_or_retire",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "reconnect_after_invalidation",
                "trigger": "new_session_after_invalidated_principal",
                "generation_action": "allocate_new_generation",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "transfer_or_download_edge",
                "trigger": "transfer_download_without_promoted_identity_continuity",
                "generation_action": "retire_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "stale_controller_or_player_state",
                "trigger": "controller_or_player_state_replaced",
                "generation_action": "invalidate_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "duplicate_or_conflicting_identity",
                "trigger": "conflicting_candidate_identity_evidence",
                "generation_action": "invalidate_conflict_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "server_restart",
                "trigger": "process_restart_boundary",
                "generation_action": "invalidate_all_prior_generations",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "plugin_reload",
                "trigger": "plugin_owner_cleanup_or_reload",
                "generation_action": "deny_cached_plugin_values",
                "consumer_result": "deny",
                "fail_closed": True,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "trigger": "unsupported_or_malformed_identity_input",
                "generation_action": "clear_output_and_deny",
                "consumer_result": "deny",
                "fail_closed": True,
            },
        ],
        "negative_consumer_rules": [
            {"rule": "no_real_identity_public", "forbids": ["SteamID", "EOSID", "UniqueNetId", "PlayerID", "PlayerDataID", "PlayerName", "IPAddress", "TribeID"], "fail_closed": True},
            {"rule": "no_ue_pointer_or_handle_identity", "forbids": ["ResourceHandle", "GObjects", "FNames", "UObjectPointer"], "fail_closed": True},
            {"rule": "no_lookup_or_persistence_from_principal", "forbids": ["lookup", "persistent_identity", "cross_process_identity"], "fail_closed": True},
            {"rule": "no_return_override_or_mutation_authority", "forbids": ["return_override", "mutation"], "fail_closed": True},
            {"rule": "no_commands_or_permissions_claims", "forbids": ["commands", "permissions"], "fail_closed": True},
            {"rule": "fail_closed_on_invalid_or_stale", "forbids": ["fallback_to_real_id", "best_effort_lookup"], "fail_closed": True},
        ],
        "rejected_public_identity_sources": sorted(principal_checker.REQUIRED_REJECTED_PUBLIC_IDENTITY_SOURCES),
        "evidence_policy": {
            "accepted_evidence_class": "candidate_policy_only",
            "malformed_evidence_result": "deny",
            "unsupported_evidence_result": "deny",
            "fail_closed": True,
        },
        "runtime_evidence": {
            "status": "not_approved",
            "approved": False,
            "required_for": ["promote", "public_readiness", "runtime_readiness"],
        },
        "promotion_gate": {
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "blockers": [
                "approved_runtime_evidence_missing",
                "principal_invalidation_semantics_unresolved",
                "candidate_only_policy",
            ],
        },
        "safety_summary": {
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "explicitly_excluded": sorted(principal_checker.REQUIRED_EXCLUSIONS),
        },
        "non_claims": sorted(principal_checker.REQUIRED_NON_CLAIMS),
    }


def validation_reasons(blockers: list[dict[str, Any]]) -> list[str]:
    return [str(blocker.get("reason")) for blocker in blockers]


def output_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256_file(path), "schema": payload.get("schema")}


def build_report(
    *,
    snapshot_root: Path,
    output_dir: Path,
    first_path: Path,
    lifecycle_path: Path,
    principal_path: Path,
    report_path: Path,
    first_evidence: dict[str, Any],
    lifecycle: dict[str, Any],
    principal: dict[str, Any],
    binder_report: dict[str, Any],
    lifecycle_snapshot_root_binding: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": REPORT_SCHEMA,
        "valid": binder_report.get("ready") is True,
        "accepted_for_planning": binder_report.get("ready") is True,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "snapshot_root": str(snapshot_root),
        "output_dir": str(output_dir),
        "blockers": list(binder_report.get("blockers", [])) if isinstance(binder_report.get("blockers"), list) else [],
        "outputs": {
            "first_evidence": output_record(first_path, first_evidence),
            "lifecycle_anchor_candidates": output_record(lifecycle_path, lifecycle),
            "principal_invalidation_policy": output_record(principal_path, principal),
            "report": {"path": str(report_path)},
        },
        "source_alignment": {
            "artifact_identity_source_artifact_ids": copy.deepcopy(
                lifecycle["artifact_identity"]["source_artifact_ids"]
            ),
            "principal_lifecycle_source_binding": copy.deepcopy(
                principal["lifecycle_layout_source"]["source_binding"]
            ),
            "lifecycle_snapshot_root_binding": copy.deepcopy(lifecycle_snapshot_root_binding),
            "binder_ready": binder_report.get("ready") is True,
            "binder_blockers": binder_report.get("blockers", []),
        },
        "binding_report": binder_report,
        "non_claims": NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    snapshot_root = safe_snapshot_root(args.snapshot_root)
    output_dir = binder.prepare_output_dir(args.output_dir)

    first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence(
        snapshot_root=snapshot_root
    )
    first_blockers = binder.offline_artifact_gate.validate_players_identity_first_evidence_manifest(
        first_evidence,
        label="generated first-evidence",
        mode="consume",
    )
    if first_blockers:
        raise SystemExit("generated first-evidence failed validation: " + json.dumps(validation_reasons(first_blockers), sort_keys=True))

    lifecycle = build_lifecycle_manifest(first_evidence, snapshot_root)
    lifecycle_blockers = lifecycle_checker.validate_manifest(lifecycle, promote=False)
    if lifecycle_blockers:
        raise SystemExit(
            "generated lifecycle-anchor candidates failed validation: "
            + json.dumps(validation_reasons(lifecycle_blockers), sort_keys=True)
        )
    lifecycle_snapshot_root_binding = binder.validate_lifecycle_anchor_snapshot_root(
        lifecycle=lifecycle,
        snapshot_root=snapshot_root,
    )

    principal = build_principal_manifest(lifecycle)
    principal_blockers = principal_checker.validate_manifest(principal, check_mode="consume").blockers
    if principal_blockers:
        raise SystemExit(
            "generated principal invalidation policy failed validation: "
            + json.dumps(validation_reasons(principal_blockers), sort_keys=True)
        )

    binder.validate_inputs(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)

    first_path = output_dir / FIRST_EVIDENCE_OUTPUT_NAME
    lifecycle_path = output_dir / binder.LIFECYCLE_OUTPUT_NAME
    principal_path = output_dir / binder.PRINCIPAL_OUTPUT_NAME
    report_path = output_dir / REPORT_OUTPUT_NAME

    binder.atomic_write_json(first_path, first_evidence)
    binder.atomic_write_json(lifecycle_path, lifecycle)
    binder.atomic_write_json(principal_path, principal)
    binder_report = binder.build_report(
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        first_evidence=first_evidence,
        lifecycle_output=lifecycle_path,
        principal_output=principal_path,
        bound_lifecycle=lifecycle,
        bound_principal=principal,
    )
    report = build_report(
        snapshot_root=snapshot_root,
        output_dir=output_dir,
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        report_path=report_path,
        first_evidence=first_evidence,
        lifecycle=lifecycle,
        principal=principal,
        binder_report=binder_report,
        lifecycle_snapshot_root_binding=lifecycle_snapshot_root_binding,
    )
    binder.atomic_write_json(report_path, report)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
