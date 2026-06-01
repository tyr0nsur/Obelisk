#!/usr/bin/env python3
"""Inventory offline Obelisk artifact workspaces without reading heavy inputs."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import protected_paths  # noqa: E402

DEFAULT_WORKSPACE_ROOT = Path("/servidor/ark/workspace-offline")
DEFAULT_DUMPS_ROOT = Path("/servidor/ark/obelisk/dumps")
DEFAULT_MAX_JSON_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_DEPTH = 12
DEFAULT_MAX_FILES = 100_000
SCHEMA = "obelisk.offline-workspace-inventory.v1"
HEAVY_SUFFIXES = (
    ".core",
    ".dmp",
    ".objdump",
    ".o",
    ".so",
    ".zip",
)
HEAVY_NAMES = {
    "core",
    "ShooterGameServer",
    "ShooterGameServer.core",
}
JSON_NAME_FRAGMENTS = (
    "gate",
    "manifest",
    "provenance",
    "readiness",
    "summary",
)
RAW_WORKSPACE_PARTS = {
    "raw",
    "dumps",
    "dump",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        action="append",
        default=[],
        help="Offline workspace root to inventory. Defaults to /servidor/ark/workspace-offline.",
    )
    parser.add_argument(
        "--include-dumps-root",
        "--include-dumps",
        dest="include_dumps_root",
        type=Path,
        help="Optional raw dumps root to triage as blocked/raw storage without reading heavy files.",
    )
    parser.add_argument(
        "--max-json-bytes",
        "--read-json-max-bytes",
        dest="max_json_bytes",
        type=int,
        default=DEFAULT_MAX_JSON_BYTES,
        help="Maximum JSON bytes to read per file. Larger JSON files are skipped as heavy.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
        help="Maximum directory depth below each root to walk.",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=DEFAULT_MAX_FILES,
        help="Maximum regular/symlink files to inspect per root before failing closed.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def path_text(path: Path) -> str:
    return path.as_posix()


def is_probably_heavy(path: Path) -> bool:
    if path.name in HEAVY_NAMES:
        return True
    lower_name = path.name.lower()
    if lower_name.startswith("core."):
        return True
    if lower_name.endswith(HEAVY_SUFFIXES):
        return True
    return False


def is_interesting_json(path: Path) -> bool:
    if path.suffix != ".json":
        return False
    lower_name = path.name.lower()
    return any(fragment in lower_name for fragment in JSON_NAME_FRAGMENTS)


def has_protected_path_reference(value: Any) -> bool:
    if isinstance(value, str):
        if not value.startswith("/servidor/ark"):
            return False
        try:
            return protected_paths.protected_path_status(Path(value)).protected
        except OSError:
            return True
    if isinstance(value, dict):
        return any(has_protected_path_reference(child) for child in value.values())
    if isinstance(value, list):
        return any(has_protected_path_reference(child) for child in value)
    return False


def artifact_bucket(payload: dict[str, Any], *, rel_path: str, raw_dumps_root: bool) -> tuple[str, str]:
    if raw_dumps_root:
        return "blocked", "raw_dumps_root_requires_workspace_manifest_before_reuse"

    rel_parts = set(Path(rel_path).parts)
    if rel_parts & RAW_WORKSPACE_PARTS:
        return "candidate", "raw_workspace_metadata_requires_gate_before_reuse"

    schema = payload.get("schema")
    if not isinstance(schema, str) or not schema:
        return "blocked", "missing_schema"

    if has_protected_path_reference(payload):
        return "candidate", "protected_path_reference_requires_manual_review"

    blockers = payload.get("blockers")
    if isinstance(blockers, list) and blockers:
        return "blocked", "reported_blockers"

    if payload.get("valid") is False or payload.get("complete") is False:
        return "blocked", "reported_invalid_or_incomplete"

    if payload.get("runtime_ready") is True or payload.get("public_sdk_ready") is True:
        return "candidate", "runtime_or_public_claim_requires_manual_review"

    status = payload.get("status")
    if status in {"blocked", "candidate_blocked", "invalid", "rejected"}:
        return "blocked", f"status_{status}"

    if (
        payload.get("accepted_for_planning") is True
        or payload.get("planning_only") is True
        or payload.get("candidate_only") is True
        or payload.get("promotion_ready") is False
        or status in {"candidate", "candidate-only", "planning-only"}
    ):
        return "candidate", "planning_or_candidate_only"

    if (
        payload.get("accepted_for_consume") is True
        or payload.get("accepted_for_offline_planning") is True
        or payload.get("ready") is True
        or payload.get("valid") is True
        or status in {"accepted", "complete", "ok", "ready"}
    ):
        return "reusable", "accepted_or_valid_artifact_metadata"

    return "candidate", "recognized_json_requires_manual_review"


def inspect_json(path: Path, root: Path, *, max_json_bytes: int, raw_dumps_root: bool) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    try:
        st = path.stat()
    except OSError as exc:
        return {
            "path": rel,
            "bucket": "blocked",
            "reason": "stat_failed",
            "error": str(exc),
        }

    if st.st_size > max_json_bytes:
        return {
            "path": rel,
            "bucket": "skipped",
            "reason": "json_too_large",
            "size_bytes": st.st_size,
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "path": rel,
            "bucket": "blocked",
            "reason": "invalid_json",
            "size_bytes": st.st_size,
            "error": str(exc),
        }
    except OSError as exc:
        return {
            "path": rel,
            "bucket": "blocked",
            "reason": "read_failed",
            "size_bytes": st.st_size,
            "error": str(exc),
        }

    if not isinstance(payload, dict):
        return {
            "path": rel,
            "bucket": "blocked",
            "reason": "json_not_object",
            "size_bytes": st.st_size,
        }

    bucket, reason = artifact_bucket(payload, rel_path=rel, raw_dumps_root=raw_dumps_root)
    return {
        "path": rel,
        "bucket": bucket,
        "reason": reason,
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "size_bytes": st.st_size,
    }


def root_kind(root: Path, *, raw_dumps_root: bool) -> tuple[str, list[str]]:
    if raw_dumps_root:
        try:
            resolved = root.expanduser().resolve()
        except OSError:
            resolved = root.expanduser()
        dumps_resolved = DEFAULT_DUMPS_ROOT.resolve()
        if root.expanduser() == DEFAULT_DUMPS_ROOT or resolved == dumps_resolved or str(resolved).startswith(
            f"{dumps_resolved}/"
        ):
            return "protected_historical_dump", []
        return "protected_historical_dump", ["include_dumps_root_not_default_dumps_path"]

    try:
        if protected_paths.is_approved_offline_workspace_path(root):
            return "offline_workspace_root", []
    except OSError:
        pass

    status = protected_paths.protected_path_status(root)
    if status.protected:
        return "blocked_protected_path", ["blocked_protected_path"]
    return "generic_offline_root", []


def inspect_root(
    root: Path,
    *,
    max_json_bytes: int,
    max_depth: int,
    max_files: int,
    raw_dumps_root: bool,
) -> dict[str, Any]:
    root = root.expanduser()
    kind, blockers = root_kind(root, raw_dumps_root=raw_dumps_root)
    resolved = root.resolve() if root.exists() else root.absolute()
    root_report: dict[str, Any] = {
        "root": path_text(root),
        "resolved_root": path_text(resolved),
        "kind": kind,
        "exists": root.exists(),
        "is_dir": root.is_dir(),
        "raw_dumps_root": raw_dumps_root,
        "artifacts": [],
        "heavy_files_skipped": [],
        "symlinks_blocked": [],
        "dirs_seen": 0,
        "files_seen": 0,
        "unique_regular_file_inodes": 0,
        "apparent_size_bytes": 0,
        "blockers": blockers,
    }
    if kind == "blocked_protected_path":
        return root_report
    symlink_component = protected_paths.first_symlink_component(root)
    if symlink_component is not None:
        root_report["blockers"] = sorted(
            set(root_report["blockers"] + ["root_has_symlink_component"])
        )
        root_report["symlinks_blocked"].append(path_text(symlink_component))
        return root_report
    if root_report["blockers"]:
        return root_report
    if root.is_symlink():
        root_report["blockers"] = sorted(set(root_report["blockers"] + ["root_is_symlink"]))
        return root_report
    if not root.exists():
        root_report["blockers"] = sorted(set(root_report["blockers"] + ["root_missing"]))
        return root_report
    if not root.is_dir():
        root_report["blockers"] = sorted(set(root_report["blockers"] + ["root_not_directory"]))
        return root_report

    seen_inodes: set[tuple[int, int]] = set()
    walk_blockers: list[str] = []
    root_depth = len(root.resolve().parts)
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(directory)
        root_report["dirs_seen"] += 1
        depth = len(current.resolve().parts) - root_depth
        if depth >= max_depth:
            dirnames[:] = []

        kept_dirnames = []
        for dirname in dirnames:
            candidate = current / dirname
            if candidate.is_symlink():
                root_report["symlinks_blocked"].append(path_text(candidate.relative_to(root)))
            else:
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in filenames:
            path = current / filename
            rel = path.relative_to(root).as_posix()
            root_report["files_seen"] += 1
            if root_report["files_seen"] > max_files:
                walk_blockers.append("max_files_exceeded")
                dirnames[:] = []
                break
            if path.is_symlink():
                root_report["symlinks_blocked"].append(rel)
                continue
            try:
                st = path.stat()
            except OSError:
                walk_blockers.append("stat_failed")
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            root_report["apparent_size_bytes"] += st.st_size
            seen_inodes.add((st.st_dev, st.st_ino))

            if is_probably_heavy(path):
                root_report["heavy_files_skipped"].append(
                    {
                        "path": rel,
                        "size_bytes": st.st_size,
                        "reason": "heavy_name_or_suffix",
                    }
                )
                continue
            if is_interesting_json(path):
                root_report["artifacts"].append(
                    inspect_json(path, root, max_json_bytes=max_json_bytes, raw_dumps_root=raw_dumps_root)
                )

    root_report["unique_regular_file_inodes"] = len(seen_inodes)
    if root_report["symlinks_blocked"]:
        walk_blockers.append("symlinks_blocked")
    root_report["blockers"] = sorted(set(root_report["blockers"] + walk_blockers))
    return root_report


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    roots = args.root or [DEFAULT_WORKSPACE_ROOT]
    root_specs = [(root, False) for root in roots]
    if args.include_dumps_root is not None:
        root_specs.append((args.include_dumps_root, True))

    root_reports = [
        inspect_root(
            root,
            max_json_bytes=args.max_json_bytes,
            max_depth=args.max_depth,
            max_files=args.max_files,
            raw_dumps_root=raw_dumps_root,
        )
        for root, raw_dumps_root in root_specs
    ]
    bucket_counts: Counter[str] = Counter()
    blocker_reasons: Counter[str] = Counter()
    invalid_json_count = 0
    for root_report in root_reports:
        for blocker in root_report.get("blockers", []):
            blocker_reasons[blocker] += 1
        for artifact in root_report.get("artifacts", []):
            bucket = artifact.get("bucket", "unknown")
            bucket_counts[bucket] += 1
            if bucket == "blocked":
                blocker_reasons[str(artifact.get("reason", "blocked"))] += 1
            if artifact.get("reason") == "invalid_json":
                invalid_json_count += 1

    blocked_count = bucket_counts.get("blocked", 0) + sum(
        1 for root_report in root_reports if root_report.get("blockers")
    )
    return {
        "schema": SCHEMA,
        "status": "ok" if blocked_count == 0 and invalid_json_count == 0 else "blocked",
        "valid": invalid_json_count == 0,
        "inventory_clean": blocked_count == 0,
        "max_json_bytes": args.max_json_bytes,
        "max_depth": args.max_depth,
        "max_files": args.max_files,
        "summary": {
            "roots": len(root_reports),
            "artifacts_by_bucket": dict(sorted(bucket_counts.items())),
            "blockers_by_reason": dict(sorted(blocker_reasons.items())),
            "heavy_files_skipped": sum(len(root_report.get("heavy_files_skipped", [])) for root_report in root_reports),
            "symlinks_blocked": sum(len(root_report.get("symlinks_blocked", [])) for root_report in root_reports),
        },
        "non_claims": [
            "metadata-only workspace inventory",
            "does not validate promotion, provenance, hashes, public SDK readiness, runtime readiness, or v1 completion",
            "does not read cores, ShooterGameServer, objdump files, Ghidra projects, or other heavy binary inputs by default",
            "does not follow symlinks",
        ],
        "roots": root_reports,
    }


def main() -> int:
    args = parse_args()
    if args.max_json_bytes <= 0:
        print("--max-json-bytes must be positive", file=sys.stderr)
        return 4
    if args.max_depth < 0:
        print("--max-depth must be non-negative", file=sys.stderr)
        return 4
    if args.max_files <= 0:
        print("--max-files must be positive", file=sys.stderr)
        return 4
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["valid"]:
        return 4
    if not report["inventory_clean"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
