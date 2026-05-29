#!/usr/bin/env python3
"""Compare two redacted offline reflection inventory packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from snapshot_evidence_pack import SHA256_RE, reject_protected_input_path  # noqa: E402


PACK_SCHEMA = "obelisk.reflection-inventory-pack.v1"
COMPARISON_SCHEMA = "obelisk.reflection-inventory-pack-comparison.v1"
REDACTED_FUNCTION_KEYS = {
    "family",
    "function_flags",
    "name",
    "num_parms",
    "outer_class_name",
    "outer_name",
    "parms_size",
}
IDENTITY_KEYS = ("artifact_sha256", "capture_id", "evidence_pack_id")
COMPARE_FIELDS = ("family", "function_flags", "num_parms", "parms_size", "outer_class_name")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare candidate-only reflection inventory packs.")
    parser.add_argument("--base-pack", required=True, type=Path)
    parser.add_argument("--candidate-pack", required=True, type=Path)
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="Exit non-zero if the comparison has blockers, missing functions, or changed rows.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a short text summary.")
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, object]:
    reject_protected_input_path(path, label)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{label} does not exist: {path}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must be a JSON object: {path}")
    return payload


def pack_file(pack: Path, name: str) -> Path:
    reject_protected_input_path(pack, "--pack")
    path = pack / name if pack.is_dir() else pack.parent / name
    reject_protected_input_path(path, name)
    return path


def validate_manifest(payload: dict[str, object], label: str, blockers: list[str]) -> None:
    if payload.get("schema") != PACK_SCHEMA:
        blockers.append(f"{label}: unsupported_schema")
    if payload.get("status") != "candidate-only":
        blockers.append(f"{label}: status_not_candidate_only")
    if payload.get("promotion_status") != "not_promoted_candidate_only":
        blockers.append(f"{label}: promotion_status_not_candidate_only")
    binary = payload.get("binary")
    binary_sha = binary.get("sha256") if isinstance(binary, dict) else None
    if not isinstance(binary_sha, str) or SHA256_RE.fullmatch(binary_sha) is None:
        blockers.append(f"{label}: invalid_binary_sha256")
    identity = payload.get("artifact_identity")
    if not isinstance(identity, dict):
        blockers.append(f"{label}: missing_artifact_identity")
    else:
        for key in ("artifact_kind", *IDENTITY_KEYS):
            if not isinstance(identity.get(key), str) or not identity.get(key):
                blockers.append(f"{label}: missing_artifact_identity_{key}")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        blockers.append(f"{label}: missing_summary")
        return
    if summary.get("fname_root_ready") is not True:
        blockers.append(f"{label}: fname_root_not_ready")
    if summary.get("target_missing_count", 0) != 0:
        blockers.append(f"{label}: target_missing")
    if summary.get("target_ambiguous_count", 0) != 0:
        blockers.append(f"{label}: target_ambiguous")
    pack_blockers = payload.get("blockers")
    if isinstance(pack_blockers, list) and pack_blockers:
        blockers.append(f"{label}: pack_blockers_present")


def binary_sha(payload: dict[str, object]) -> str | None:
    binary = payload.get("binary")
    sha = binary.get("sha256") if isinstance(binary, dict) else None
    return sha if isinstance(sha, str) else None


def identity(payload: dict[str, object]) -> dict[str, object]:
    value = payload.get("artifact_identity")
    return value if isinstance(value, dict) else {}


def load_functions(path: Path, label: str, blockers: list[str]) -> dict[tuple[str, str], dict[str, object]]:
    payload = load_json(path, label)
    rows = payload.get("functions")
    if not isinstance(rows, list):
        blockers.append(f"{label}: missing_functions")
        return {}
    by_key: dict[tuple[str, str], dict[str, object]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blockers.append(f"{label}: function_row_not_object")
            continue
        extra_keys = sorted(set(row) - REDACTED_FUNCTION_KEYS)
        missing_keys = sorted(REDACTED_FUNCTION_KEYS - set(row))
        if extra_keys:
            blockers.append(f"{label}: function_row_{index}_extra_keys")
        if missing_keys:
            blockers.append(f"{label}: function_row_{index}_missing_keys")
        outer = row.get("outer_name")
        name = row.get("name")
        if not isinstance(outer, str) or not isinstance(name, str):
            blockers.append(f"{label}: function_row_{index}_missing_key_identity")
            continue
        key = (outer, name)
        if key in by_key:
            blockers.append(f"{label}: duplicate_function_{outer}.{name}")
        by_key[key] = row
    return by_key


def compare_rows(
    base_rows: dict[tuple[str, str], dict[str, object]],
    candidate_rows: dict[tuple[str, str], dict[str, object]],
) -> dict[str, object]:
    base_keys = set(base_rows)
    candidate_keys = set(candidate_rows)
    changed: list[dict[str, object]] = []
    for key in sorted(base_keys & candidate_keys):
        field_changes = {
            field: {
                "base": base_rows[key].get(field),
                "candidate": candidate_rows[key].get(field),
            }
            for field in COMPARE_FIELDS
            if base_rows[key].get(field) != candidate_rows[key].get(field)
        }
        if field_changes:
            changed.append({"target": f"{key[0]}.{key[1]}", "fields": field_changes})
    return {
        "base_function_count": len(base_rows),
        "candidate_function_count": len(candidate_rows),
        "shared_function_count": len(base_keys & candidate_keys),
        "missing_in_candidate": [f"{outer}.{name}" for outer, name in sorted(base_keys - candidate_keys)],
        "new_in_candidate": [f"{outer}.{name}" for outer, name in sorted(candidate_keys - base_keys)],
        "changed_functions": changed,
    }


def build_comparison(base_pack: Path, candidate_pack: Path) -> dict[str, object]:
    blockers: list[str] = []
    base_manifest = load_json(pack_file(base_pack, "manifest.json"), "base manifest")
    candidate_manifest = load_json(pack_file(candidate_pack, "manifest.json"), "candidate manifest")
    validate_manifest(base_manifest, "base", blockers)
    validate_manifest(candidate_manifest, "candidate", blockers)
    if binary_sha(base_manifest) != binary_sha(candidate_manifest):
        blockers.append("binary_sha256_mismatch")
    base_identity = identity(base_manifest)
    candidate_identity = identity(candidate_manifest)
    for key in IDENTITY_KEYS:
        if base_identity.get(key) == candidate_identity.get(key):
            blockers.append(f"artifact_identity_not_distinct_{key}")
    base_rows = load_functions(pack_file(base_pack, "ufunction-inventory.json"), "base inventory", blockers)
    candidate_rows = load_functions(
        pack_file(candidate_pack, "ufunction-inventory.json"),
        "candidate inventory",
        blockers,
    )
    row_comparison = compare_rows(base_rows, candidate_rows)
    if row_comparison["missing_in_candidate"]:
        blockers.append("missing_functions_in_candidate")
    if row_comparison["new_in_candidate"]:
        blockers.append("new_functions_in_candidate")
    if row_comparison["changed_functions"]:
        blockers.append("changed_function_metadata")
    return {
        "schema": COMPARISON_SCHEMA,
        "status": "accepted" if not blockers else "blocked",
        "promotion_status": "not_promoted_candidate_only",
        "base": {
            "pack": str(base_pack),
            "artifact_identity": base_identity,
            "binary_sha256": binary_sha(base_manifest),
            "summary": base_manifest.get("summary"),
        },
        "candidate": {
            "pack": str(candidate_pack),
            "artifact_identity": candidate_identity,
            "binary_sha256": binary_sha(candidate_manifest),
            "summary": candidate_manifest.get("summary"),
        },
        "function_comparison": row_comparison,
        "blockers": blockers,
        "non_claims": [
            "Does not promote GObjects/GUObjectArray as runtime-stable.",
            "Does not expose UObject pointers, raw params, object identity, mutation, or return overrides.",
            "Does not replace strict per-target snapshot readiness reports.",
        ],
    }


def format_text(payload: dict[str, object]) -> str:
    functions = payload["function_comparison"]
    return (
        "status={status} shared={shared_function_count} missing={missing} new={new} changed={changed} "
        "blockers={blockers}"
    ).format(
        status=payload["status"],
        shared_function_count=functions["shared_function_count"],
        missing=len(functions["missing_in_candidate"]),
        new=len(functions["new_in_candidate"]),
        changed=len(functions["changed_functions"]),
        blockers=len(payload["blockers"]),
    )


def main() -> int:
    args = parse_args()
    payload = build_comparison(args.base_pack, args.candidate_pack)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(format_text(payload))
    if args.fail_on_gaps and payload["blockers"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
