#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_ARTIFACT_ROOT = Path("/home/flowcommunity-ark/obelisk-artifacts")
DEFAULT_ARTIFACT_ROOT = (
    ALLOWED_ARTIFACT_ROOT
    / "transfer-scriptstruct-bool-tail-refresh-20260530T163945Z"
)

READINESS_REL = Path("transfer-scriptstruct-readiness.json")
PROMOTE_GATE_REL = Path("inventory-pack/promote-gate.json")
MANIFEST_REL = Path("inventory-pack/manifest.json")
SNAPSHOT_REL = Path(
    "scriptstruct-snapshots/7e7ded49e0c6/sdk_transfers/"
    "PrimalLocalProfile.ArkTributePlayerData.snapshot.json"
)

EXPECTED_PROMOTE_BLOCKERS = {
    "promote_mode_scriptstruct_inventory_candidate_only",
    "promote_mode_manifest_has_non_claims",
}

EXPECTED_NOT_PROMOTED_SURFACES = {
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
}

EXPECTED_SENSITIVE_FIELDS: dict[str, dict[str, Any]] = {
    "PlayerDataID": {
        "class_name": "UInt64Property",
        "offset_internal": 8,
        "array_dim": 1,
    },
    "PlayerDataBytes": {
        "class_name": "ArrayProperty",
        "offset_internal": 16,
        "array_dim": 1,
        "inner_class_name": "ByteProperty",
    },
    "PlayerName": {
        "class_name": "StrProperty",
        "offset_internal": 32,
        "array_dim": 1,
    },
    "PlayerStats": {
        "class_name": "StrProperty",
        "offset_internal": 48,
        "array_dim": 12,
    },
    "UploadingServerMapName": {
        "class_name": "StrProperty",
        "offset_internal": 240,
        "array_dim": 1,
    },
    "UploadingServerName": {
        "class_name": "StrProperty",
        "offset_internal": 256,
        "array_dim": 1,
    },
    "ItemCount": {
        "class_name": "UInt32Property",
        "offset_internal": 276,
        "array_dim": 1,
    },
    "bWasAllowDPCUpload": {
        "class_name": "BoolProperty",
        "offset_internal": 272,
        "array_dim": 1,
        "bool_field_size": 1,
        "bool_byte_offset": 0,
        "byte_mask": "0x1",
        "field_mask": "0xff",
        "native_bool": False,
    },
    "bWithItems": {
        "class_name": "BoolProperty",
        "offset_internal": 273,
        "array_dim": 1,
        "bool_field_size": 1,
        "bool_byte_offset": 0,
        "byte_mask": "0x1",
        "field_mask": "0xff",
        "native_bool": False,
    },
    "bForServerTransfer": {
        "class_name": "BoolProperty",
        "offset_internal": 280,
        "array_dim": 1,
        "bool_field_size": 1,
        "bool_byte_offset": 0,
        "byte_mask": "0x1",
        "field_mask": "0xff",
        "native_bool": False,
    },
}


def _blocker(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _load_json(
    artifact_root: Path,
    rel_path: Path,
    blockers: list[dict[str, str]],
    *,
    enforce_allowed_root: bool,
) -> Any | None:
    path = artifact_root / rel_path
    if enforce_allowed_root and not _is_under(path, ALLOWED_ARTIFACT_ROOT):
        blockers.append(
            _blocker(
                "artifact_outside_allowed_root",
                f"{rel_path} resolves outside {ALLOWED_ARTIFACT_ROOT}",
            )
        )
        return None
    if not path.exists():
        blockers.append(_blocker("missing_artifact", str(rel_path)))
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        blockers.append(_blocker("invalid_json", f"{rel_path}: {exc}"))
        return None


def _expect(
    blockers: list[dict[str, str]], condition: bool, code: str, detail: str
) -> None:
    if not condition:
        blockers.append(_blocker(code, detail))


def _validate_readiness(readiness: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    gate = readiness.get("promotion_gate", {})
    totals = readiness.get("totals", {})
    not_promoted = set(readiness.get("not_promoted_surfaces", []))
    target_filters = set(readiness.get("target_filters", []))

    _expect(
        blockers,
        readiness.get("schema") == "obelisk.reflection-snapshot-readiness.v1",
        "invalid_readiness_schema",
        "transfer readiness schema must be obelisk.reflection-snapshot-readiness.v1",
    )
    _expect(
        blockers,
        readiness.get("second_source_status") == "compared",
        "readiness_not_compared",
        "transfer readiness second_source_status must be compared",
    )
    _expect(
        blockers,
        totals.get("targets") == 2 and totals.get("second_source_accepted") == 2,
        "readiness_second_source_counts_invalid",
        "transfer readiness must keep targets=2 and second_source_accepted=2",
    )
    _expect(
        blockers,
        gate.get("ready_scope") == "layout_only"
        and gate.get("layout_ready") is True
        and gate.get("promotion_ready") is False,
        "readiness_not_layout_only",
        "promotion_gate must be layout_ready only with promotion_ready=false",
    )
    _expect(
        blockers,
        "obelisk.scriptstruct-chain.snapshot.v1:PrimalLocalProfile.ArkTributePlayerData"
        in target_filters,
        "readiness_missing_playerdata_target",
        "target_filters must include ArkTributePlayerData snapshot target",
    )
    missing_surfaces = EXPECTED_NOT_PROMOTED_SURFACES - not_promoted
    _expect(
        blockers,
        not missing_surfaces,
        "readiness_missing_not_promoted_surfaces",
        "missing not_promoted_surfaces: " + ", ".join(sorted(missing_surfaces)),
    )


def _validate_promote_gate(
    promote_gate: dict[str, Any], blockers: list[dict[str, str]]
) -> None:
    reasons = {blocker.get("reason") for blocker in promote_gate.get("blockers", [])}
    missing_reasons = EXPECTED_PROMOTE_BLOCKERS - reasons

    _expect(
        blockers,
        promote_gate.get("schema") == "obelisk.offline-artifact-gate-result.v1",
        "invalid_promote_gate_schema",
        "promote gate schema must be obelisk.offline-artifact-gate-result.v1",
    )
    _expect(
        blockers,
        promote_gate.get("mode") == "promote" and promote_gate.get("status") == "blocked",
        "promote_gate_not_blocked",
        "promote gate must remain mode=promote and status=blocked",
    )
    _expect(
        blockers,
        not missing_reasons,
        "promote_gate_missing_expected_blockers",
        "missing promote blockers: " + ", ".join(sorted(missing_reasons)),
    )


def _property_inner_class(prop: dict[str, Any]) -> str | None:
    snapshot_inner = prop.get("array_inner_candidate", {}).get("inner_property", {})
    inventory_inner = prop.get("array_inner", {})
    return snapshot_inner.get("class_name") or inventory_inner.get("source_property_class")


def _validate_sensitive_field(
    name: str,
    prop: dict[str, Any],
    expected: dict[str, Any],
    blockers: list[dict[str, str]],
) -> None:
    for key in ("class_name", "offset_internal", "array_dim"):
        _expect(
            blockers,
            prop.get(key) == expected[key],
            "sensitive_field_mismatch",
            f"{name}.{key} expected {expected[key]!r}, got {prop.get(key)!r}",
        )

    _expect(
        blockers,
        prop.get("status") == "candidate",
        "sensitive_field_not_candidate",
        f"{name} must remain candidate-only evidence",
    )
    _expect(
        blockers,
        prop.get("reject_reasons", []) == [],
        "sensitive_field_has_reject_reasons",
        f"{name} must not carry reject_reasons in accepted boundary artifact",
    )

    if "inner_class_name" in expected:
        _expect(
            blockers,
            _property_inner_class(prop) == expected["inner_class_name"],
            "sensitive_field_inner_mismatch",
            f"{name} inner class must be {expected['inner_class_name']}",
        )

    if expected["class_name"] == "BoolProperty":
        for key in (
            "bool_field_size",
            "bool_byte_offset",
            "byte_mask",
            "field_mask",
            "native_bool",
        ):
            _expect(
                blockers,
                prop.get(key) == expected[key],
                "bool_tail_metadata_mismatch",
                f"{name}.{key} expected {expected[key]!r}, got {prop.get(key)!r}",
            )


def _validate_snapshot(snapshot: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    evidence = snapshot.get("evidence", {})
    interpretation = snapshot.get("interpretation", {})
    targets = snapshot.get("targets", [])
    target = targets[0] if targets else {}
    target_info = target.get("target", {})
    property_chain = target.get("property_chain", {})
    properties = property_chain.get("properties", [])
    properties_by_name = {prop.get("name"): prop for prop in properties}

    _expect(
        blockers,
        snapshot.get("schema") == "obelisk.scriptstruct-chain.snapshot.v1",
        "invalid_snapshot_schema",
        "snapshot schema must be obelisk.scriptstruct-chain.snapshot.v1",
    )
    _expect(
        blockers,
        evidence.get("status") == "candidate-only"
        and interpretation.get("status") == "candidate-only",
        "snapshot_not_candidate_only",
        "snapshot evidence and interpretation status must both be candidate-only",
    )
    _expect(
        blockers,
        target.get("status") == "candidate"
        and property_chain.get("status") == "candidate",
        "snapshot_chain_not_candidate",
        "target and property_chain must remain candidate evidence",
    )
    _expect(
        blockers,
        target_info.get("outer_name") == "PrimalLocalProfile"
        and target_info.get("name") == "ArkTributePlayerData",
        "snapshot_wrong_target",
        "snapshot target must be PrimalLocalProfile.ArkTributePlayerData",
    )
    _expect(
        blockers,
        property_chain.get("properties_size") == 288
        and property_chain.get("observed_count") == 11,
        "snapshot_layout_shape_changed",
        "ArkTributePlayerData must keep properties_size=288 and observed_count=11",
    )

    for name, expected in EXPECTED_SENSITIVE_FIELDS.items():
        prop = properties_by_name.get(name)
        if prop is None:
            blockers.append(_blocker("missing_sensitive_field", name))
            continue
        _validate_sensitive_field(name, prop, expected, blockers)


def _validate_manifest(manifest: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    non_claims = "\n".join(manifest.get("non_claims", []))
    target_sets = set(manifest.get("inputs", {}).get("target_sets", []))

    _expect(
        blockers,
        manifest.get("schema") == "obelisk.scriptstruct-inventory-pack.v1",
        "invalid_manifest_schema",
        "manifest schema must be obelisk.scriptstruct-inventory-pack.v1",
    )
    _expect(
        blockers,
        manifest.get("status") == "candidate-only"
        and manifest.get("promotion_status") == "not_promoted_candidate_only",
        "manifest_promoted_or_public",
        "manifest must remain status=candidate-only and promotion_status=not_promoted_candidate_only",
    )
    _expect(
        blockers,
        "transfer-scriptstruct" in target_sets,
        "manifest_missing_transfer_target_set",
        "manifest inputs.target_sets must include transfer-scriptstruct",
    )
    for phrase in (
        "Does not promote a public ScriptStruct SDK.",
        "object identity, lookup, or ResourceHandle",
        "Does not authorize mutation, return override, ProcessEvent blocking",
    ):
        _expect(
            blockers,
            phrase in non_claims,
            "manifest_missing_non_claim",
            f"manifest non_claims must include: {phrase}",
        )


def validate_artifacts(
    artifact_root: Path = DEFAULT_ARTIFACT_ROOT,
    *,
    enforce_allowed_root: bool = True,
) -> dict[str, Any]:
    artifact_root = Path(artifact_root)
    blockers: list[dict[str, str]] = []

    if enforce_allowed_root and not _is_under(artifact_root, ALLOWED_ARTIFACT_ROOT):
        blockers.append(
            _blocker(
                "artifact_root_outside_allowed_root",
                f"{artifact_root} is outside {ALLOWED_ARTIFACT_ROOT}",
            )
        )
        return {
            "status": "blocked",
            "artifact_root": str(artifact_root),
            "blockers": blockers,
        }

    readiness = _load_json(
        artifact_root, READINESS_REL, blockers, enforce_allowed_root=enforce_allowed_root
    )
    promote_gate = _load_json(
        artifact_root, PROMOTE_GATE_REL, blockers, enforce_allowed_root=enforce_allowed_root
    )
    manifest = _load_json(
        artifact_root, MANIFEST_REL, blockers, enforce_allowed_root=enforce_allowed_root
    )
    snapshot = _load_json(
        artifact_root, SNAPSHOT_REL, blockers, enforce_allowed_root=enforce_allowed_root
    )

    if blockers:
        return {
            "status": "blocked",
            "artifact_root": str(artifact_root),
            "blockers": blockers,
        }

    _validate_readiness(readiness, blockers)
    _validate_promote_gate(promote_gate, blockers)
    _validate_manifest(manifest, blockers)
    _validate_snapshot(snapshot, blockers)

    return {
        "status": "passed" if not blockers else "blocked",
        "artifact_root": str(artifact_root),
        "checked": [
            str(READINESS_REL),
            str(PROMOTE_GATE_REL),
            str(MANIFEST_REL),
            str(SNAPSHOT_REL),
        ],
        "blockers": blockers,
    }


def _print_text(result: dict[str, Any]) -> None:
    if result["status"] == "passed":
        print("PASS ArkTributePlayerData boundary remains layout-only candidate.")
        for rel_path in result.get("checked", []):
            print(f"- checked {rel_path}")
        return

    print("FAIL ArkTributePlayerData boundary checker found blockers:")
    for blocker in result["blockers"]:
        print(f"- {blocker['code']}: {blocker['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate ArkTributePlayerData layout-only identity boundary from existing "
            "offline artifacts."
        )
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help=f"artifact root under {ALLOWED_ARTIFACT_ROOT}",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args(argv)

    result = validate_artifacts(args.artifact_root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_text(result)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
