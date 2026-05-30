#!/usr/bin/env python3
"""Normalize an offline artifact pack manifest and relative SHA256SUMS."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import (  # noqa: E402
    reject_protected_output_path,
    safe_component,
)


SCHEMA = "obelisk.artifact-pack.manifest.v1"
MANIFEST_NAME = "artifact-pack.manifest.json"
SHA256SUMS_NAME = "SHA256SUMS"
GENERATED_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
ARTIFACT_ID_TIMESTAMP_RE = re.compile(r"(?P<stamp>\d{8}T\d{6}Z)$")
EXCLUDED_ROOT_FILES = {MANIFEST_NAME, SHA256SUMS_NAME}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_generated_utc(value: str, label: str) -> str:
    if GENERATED_UTC_RE.fullmatch(value) is None:
        raise SystemExit(f"{label} must be UTC in YYYY-MM-DDTHH:MM:SSZ form: {value}")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SystemExit(f"{label} must be a real UTC timestamp: {value}") from exc
    return value


def generated_utc_from_artifact_id(artifact_id: str) -> str:
    match = ARTIFACT_ID_TIMESTAMP_RE.search(artifact_id)
    if match is None:
        return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        parsed = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise SystemExit(f"artifact id has an invalid trailing timestamp: {artifact_id}") from exc
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_relative_pack_path(path: str) -> str:
    if path.startswith("/") or path.startswith("../") or "/../" in path or path == "..":
        raise SystemExit(f"refusing unsafe pack-relative path: {path}")
    if "\\" in path:
        raise SystemExit(f"refusing pack path with backslash characters: {path!r}")
    if any(ord(char) < 32 for char in path):
        raise SystemExit(f"refusing pack path with control characters: {path!r}")
    if path in {"", "."}:
        raise SystemExit("refusing empty pack-relative path")
    return path


def resolve_pack_root(pack_root: Path) -> Path:
    expanded = pack_root.expanduser()
    if expanded.is_symlink():
        raise SystemExit(f"--pack-root must not be a symlink: {expanded}")
    root = reject_protected_output_path(expanded, "--pack-root")
    if not root.exists():
        raise SystemExit(f"--pack-root does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"--pack-root must be a directory: {root}")
    return root


def reject_symlink_outputs(root: Path) -> None:
    for name in (MANIFEST_NAME, SHA256SUMS_NAME):
        path = root / name
        if path.is_symlink():
            raise SystemExit(f"refusing to overwrite symlinked pack output: {path}")


def pack_payload_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise SystemExit(f"refusing to normalize pack containing symlink: {path}")
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        validate_relative_pack_path(relative)
        if path.parent == root and path.name in EXCLUDED_ROOT_FILES:
            continue
        if not path.is_file():
            raise SystemExit(f"refusing to normalize non-regular pack entry: {path}")
        files.append(path)
    return files


def build_manifest(root: Path, artifact_id: str, generated_utc: str) -> dict[str, Any]:
    file_entries = []
    for path in pack_payload_files(root):
        relative = validate_relative_pack_path(path.relative_to(root).as_posix())
        file_entries.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    return {
        "schema": SCHEMA,
        "artifact_id": artifact_id,
        "generated_utc": generated_utc,
        "files": file_entries,
    }


def render_manifest(manifest: dict[str, Any]) -> bytes:
    return (json.dumps(manifest, indent=2) + "\n").encode("utf-8")


def render_sha256sums(manifest: dict[str, Any], manifest_bytes: bytes) -> bytes:
    lines = [f"{sha256_bytes(manifest_bytes)}  {MANIFEST_NAME}\n"]
    for entry in manifest["files"]:
        lines.append(f"{entry['sha256']}  {entry['path']}\n")
    return "".join(lines).encode("utf-8")


def load_existing_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{path} does not exist") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    if payload.get("schema") != SCHEMA:
        raise SystemExit(f"{path} has unsupported schema: {payload.get('schema')}")
    if not isinstance(payload.get("artifact_id"), str) or not payload["artifact_id"]:
        raise SystemExit(f"{path} missing artifact_id")
    safe_component(payload["artifact_id"], f"{path}: artifact_id")
    if not isinstance(payload.get("generated_utc"), str):
        raise SystemExit(f"{path} missing generated_utc")
    validate_generated_utc(payload["generated_utc"], f"{path}: generated_utc")
    return payload


def normalize_pack(root: Path, artifact_id: str, generated_utc: str) -> dict[str, Any]:
    reject_symlink_outputs(root)
    manifest = build_manifest(root, artifact_id, generated_utc)
    manifest_bytes = render_manifest(manifest)
    sha256sums_bytes = render_sha256sums(manifest, manifest_bytes)
    (root / MANIFEST_NAME).write_bytes(manifest_bytes)
    (root / SHA256SUMS_NAME).write_bytes(sha256sums_bytes)
    return {
        "pack_root": str(root),
        "manifest": MANIFEST_NAME,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "sha256sums": SHA256SUMS_NAME,
        "sha256sums_sha256": sha256_bytes(sha256sums_bytes),
        "file_count": len(manifest["files"]),
    }


def check_pack(root: Path, artifact_id: str | None, generated_utc: str | None) -> dict[str, Any]:
    reject_symlink_outputs(root)
    manifest_path = root / MANIFEST_NAME
    sha256sums_path = root / SHA256SUMS_NAME
    existing_manifest = load_existing_manifest(manifest_path)
    expected_artifact_id = artifact_id or existing_manifest["artifact_id"]
    expected_generated_utc = generated_utc or existing_manifest["generated_utc"]
    manifest = build_manifest(root, expected_artifact_id, expected_generated_utc)
    if existing_manifest != manifest:
        raise SystemExit(f"{manifest_path} is not normalized for current pack contents")
    current_manifest_bytes = manifest_path.read_bytes()
    expected_sha256sums = render_sha256sums(manifest, current_manifest_bytes)
    try:
        current_sha256sums = sha256sums_path.read_bytes()
    except FileNotFoundError as exc:
        raise SystemExit(f"{sha256sums_path} does not exist") from exc
    if current_sha256sums != expected_sha256sums:
        raise SystemExit(f"{sha256sums_path} is not normalized for current pack contents")
    return {
        "pack_root": str(root),
        "manifest": MANIFEST_NAME,
        "manifest_sha256": sha256_bytes(current_manifest_bytes),
        "sha256sums": SHA256SUMS_NAME,
        "sha256sums_sha256": sha256_bytes(current_sha256sums),
        "file_count": len(manifest["files"]),
        "status": "ok",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Write artifact-pack.manifest.json and relative SHA256SUMS for an offline "
            "artifact pack without rewriting the pack's report or gate JSON files."
        )
    )
    parser.add_argument("pack_root", type=Path, help="Artifact pack directory to normalize.")
    parser.add_argument(
        "--artifact-id",
        help="Artifact id for the manifest. Defaults to the pack directory name.",
    )
    parser.add_argument(
        "--generated-utc",
        help=(
            "UTC timestamp for the manifest in YYYY-MM-DDTHH:MM:SSZ form. Defaults to "
            "a trailing YYYYMMDDTHHMMSSZ in the artifact id, then current UTC."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate existing manifest and SHA256SUMS without writing files.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = resolve_pack_root(args.pack_root)
    artifact_id = args.artifact_id or root.name
    safe_component(artifact_id, "--artifact-id")
    generated_utc = (
        validate_generated_utc(args.generated_utc, "--generated-utc")
        if args.generated_utc
        else generated_utc_from_artifact_id(artifact_id)
    )
    if args.check:
        result = check_pack(root, args.artifact_id, args.generated_utc)
    else:
        result = normalize_pack(root, artifact_id, generated_utc)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(
            f"{result['manifest']} sha256={result['manifest_sha256']} "
            f"{result['sha256sums']} sha256={result['sha256sums_sha256']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
