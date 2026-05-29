#!/usr/bin/env python3
"""Validate and query binary-scoped FName index manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "obelisk.fname-index-manifest.v1"
VALID_STATUSES = {"candidate-only", "accepted"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATED_RESEARCH_NOTE_RE = re.compile(r"^docs/research/\d{4}-\d{2}-\d{2}-[A-Za-z0-9][A-Za-z0-9._-]*\.md$")
EVIDENCE_PACK_MANIFEST_RE = re.compile(
    r"^(?!.*(?:^|/)\.\.(?:/|$))(?=.*/[^/]*(?:evidence|pack)[^/]*/manifest\.json$).+/manifest\.json$"
)
INT32_MAX = 2_147_483_647
PROTECTED_INPUT_ROOTS = (Path("/servidor/ark"),)
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_approved_offline_workspace_path(path: Path) -> bool:
    resolved = path.resolve()
    return any(is_relative_to(resolved, root.resolve()) for root in APPROVED_OFFLINE_WORKSPACE_ROOTS)


def reject_protected_input_path(path: Path, label: str) -> None:
    expanded = path.expanduser()
    for root in PROTECTED_INPUT_ROOTS:
        if expanded.is_absolute() and is_relative_to(expanded, root) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not read from protected server root {root}: {expanded}")
    candidate = expanded.resolve()
    for root in PROTECTED_INPUT_ROOTS:
        if not is_relative_to(candidate, root):
            continue
        if is_approved_offline_workspace_path(candidate):
            continue
        raise SystemExit(f"{label} must not read from protected server root {root}: {candidate}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected object JSON")
    return payload


def require_string(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"manifest field {field!r} must be a non-empty string")
    return value


def sha256_file(path: Path) -> str:
    reject_protected_input_path(path, "--ark-binary")
    hasher = hashlib.sha256()
    if not path.is_file():
        raise SystemExit(f"--ark-binary must be a regular file: {path}")
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
    except FileNotFoundError as exc:
        raise SystemExit(f"--ark-binary not found: {path}") from exc
    return hasher.hexdigest()


def validate_sha256(value: str, field: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{field} must be a lowercase SHA256 hex string")
    return value


def is_valid_accepted_entry_evidence(value: str) -> bool:
    return DATED_RESEARCH_NOTE_RE.fullmatch(value) is not None or EVIDENCE_PACK_MANIFEST_RE.fullmatch(value) is not None


def validate_accepted_entry_evidence_path(value: str, index: int) -> None:
    if EVIDENCE_PACK_MANIFEST_RE.fullmatch(value) is not None:
        reject_protected_input_path(Path(value), f"manifest names[{index}].evidence")


def validate_manifest(payload: dict[str, Any], expected_sha: str | None = None) -> list[dict[str, Any]]:
    schema = require_string(payload, "schema")
    if schema != SCHEMA:
        raise SystemExit(f"manifest schema must be {SCHEMA!r}")

    ark_sha = validate_sha256(require_string(payload, "ark_binary_sha256"), "manifest ark_binary_sha256")
    if expected_sha is not None and ark_sha != expected_sha:
        raise SystemExit("manifest ark_binary_sha256 does not match expected binary hash")

    status = require_string(payload, "evidence_status")
    if status not in VALID_STATUSES:
        raise SystemExit("manifest evidence_status must be candidate-only or accepted")
    if status == "accepted":
        promotion = payload.get("promotion_evidence")
        if not isinstance(promotion, dict):
            raise SystemExit("accepted manifests require promotion_evidence object")
        if promotion.get("schema") != "obelisk.fname-index-promotion-evidence.v1":
            raise SystemExit("accepted manifest promotion_evidence has invalid schema")
        if promotion.get("status") != "accepted" or promotion.get("second_source") is not True:
            raise SystemExit("accepted manifest promotion_evidence must record accepted second-source evidence")
        report = promotion.get("report")
        if not isinstance(report, str) or DATED_RESEARCH_NOTE_RE.fullmatch(report) is None:
            raise SystemExit("accepted manifest promotion_evidence.report must point to a dated docs/research note")

    names = payload.get("names")
    if not isinstance(names, list) or not names:
        raise SystemExit("manifest names must be a non-empty array")

    seen_indices: set[int] = set()
    seen_identities: set[tuple[str, int]] = set()
    validated: list[dict[str, Any]] = []
    for index, entry in enumerate(names):
        if not isinstance(entry, dict):
            raise SystemExit(f"manifest names[{index}] must be an object")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"manifest names[{index}].name must be a non-empty string")
        fname_index = entry.get("index")
        if isinstance(fname_index, bool) or not isinstance(fname_index, int) or fname_index < 0 or fname_index > INT32_MAX:
            raise SystemExit(f"manifest names[{index}].index must be a non-negative int32")
        number = entry.get("number", 0)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0 or number > INT32_MAX:
            raise SystemExit(f"manifest names[{index}].number must be a non-negative int32")
        if number != 0:
            raise SystemExit("manifest FName number values other than 0 are not supported by the current index filter")
        if fname_index in seen_indices:
            raise SystemExit(f"manifest duplicate FName index: {fname_index}")
        identity = (name, number)
        if identity in seen_identities:
            raise SystemExit(f"manifest duplicate FName identity: {name}#{number}")
        evidence = entry.get("evidence")
        if status == "accepted" and (not isinstance(evidence, str) or not evidence):
            raise SystemExit(f"manifest names[{index}].evidence is required for accepted manifests")
        if status == "accepted" and not is_valid_accepted_entry_evidence(evidence):
            raise SystemExit(
                f"manifest names[{index}].evidence must be a dated docs/research note or evidence-pack manifest path"
            )
        if status == "accepted":
            validate_accepted_entry_evidence_path(evidence, index)
        seen_indices.add(fname_index)
        seen_identities.add(identity)
        validated.append({"name": name, "index": fname_index, "number": number, "evidence": evidence or ""})
    return validated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--ark-binary-sha256", help="Expected target ShooterGameServer SHA256.")
    parser.add_argument("--ark-binary", type=Path, help="Offline ShooterGameServer binary to hash as the expected target.")
    parser.add_argument("--resolve-name", help="Resolve an exact FName string to an index.")
    parser.add_argument("--number", type=int, default=0, help="FName number for --resolve-name.")
    parser.add_argument("--require-accepted", action="store_true", help="Reject candidate-only manifests.")
    parser.add_argument(
        "--allow-candidate",
        action="store_true",
        help="Allow candidate-only manifests for explicit internal/debug resolution.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.ark_binary and args.ark_binary_sha256:
        raise SystemExit("use either --ark-binary or --ark-binary-sha256, not both")
    expected_sha = sha256_file(args.ark_binary.expanduser()) if args.ark_binary else args.ark_binary_sha256
    if expected_sha is not None:
        expected_sha = validate_sha256(expected_sha, "expected ark binary SHA256")
    if args.resolve_name is not None and not expected_sha:
        raise SystemExit("--resolve-name requires --ark-binary or --ark-binary-sha256 so stale manifests fail closed")
    if args.require_accepted and args.allow_candidate:
        raise SystemExit("use either --require-accepted or --allow-candidate, not both")
    reject_protected_input_path(args.manifest, "--manifest")
    payload = load_json(args.manifest)
    names = validate_manifest(payload, expected_sha)
    status = payload["evidence_status"]
    if args.require_accepted and status != "accepted":
        raise SystemExit("manifest evidence_status is candidate-only; accepted evidence is required")
    if args.resolve_name is not None and status != "accepted" and not args.allow_candidate:
        raise SystemExit("manifest evidence_status is candidate-only; use --allow-candidate only for explicit internal/debug resolution")

    result: dict[str, Any] = {
        "schema": "obelisk.fname-index-manifest-validation.v1",
        "manifest_schema": SCHEMA,
        "ark_binary_sha256": payload["ark_binary_sha256"],
        "expected_ark_binary_sha256": expected_sha,
        "generated_for_ark_binary_sha256": expected_sha if args.resolve_name is not None else None,
        "evidence_status": status,
        "name_count": len(names),
    }
    if args.resolve_name is not None:
        if args.number < 0:
            raise SystemExit("--number must be non-negative")
        match = next(
            (entry for entry in names if entry["name"] == args.resolve_name and entry["number"] == args.number),
            None,
        )
        if match is None:
            raise SystemExit(f"FName not found in manifest: {args.resolve_name}#{args.number}")
        result["resolved"] = {
            "name": match["name"],
            "number": match["number"],
            "index": match["index"],
            "evidence": match["evidence"],
        }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif "resolved" in result:
        resolved = result["resolved"]
        print(f"{resolved['name']}#{resolved['number']}={resolved['index']}")
        print(f"generated_for_ark_binary_sha256={expected_sha}")
    else:
        print(f"manifest ok: names={len(names)} status={status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
