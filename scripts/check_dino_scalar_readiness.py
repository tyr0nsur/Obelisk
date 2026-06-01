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
        return payload
    try:
        return signature_builder.build_report(snapshot_root=snapshot_root, target_sets=[TARGET_SET])
    except SystemExit as exc:
        append_blocker(blockers, "signature_report_build_failed", detail=str(exc))
        return {}


def validate_signature_report(report: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
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
    repo_root = repo_root_arg.resolve()
    target_set = validate_target_set(repo_root, blockers)
    for relative in REQUIRED_SOURCE_FILES:
        if not (repo_root / relative).is_file():
            append_blocker(blockers, "required_file_missing", path=relative)
    signature_report = load_signature_report(report_path, snapshot_root, blockers)
    summary = validate_signature_report(signature_report, blockers)
    source_isolation = validate_source_isolation(repo_root, blockers)
    ready = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_ready" if ready else "blocked",
        "ready": ready,
        "accepted_for_internal_planning": ready,
        "offline_only": True,
        "not_artifact_gate": True,
        "target_set": target_set,
        "summary": summary,
        "scalar_only_ready": ready,
        "precall_scalar_ready": ready,
        "postcall_return_ready": False,
        "source_isolation": source_isolation,
        "public_sdk_ready": False,
        "public_dino_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
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
            "no public Dino SDK or C ABI",
            "no runtime hook wiring or observer approval",
            "no dino/player/passenger identity, lookup, ownership, or ResourceHandle",
            "no mutation, return override, or UE function call",
            "does not claim v1 completion or production readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    report = build_report(args.repo_root, args.report, args.snapshot_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
