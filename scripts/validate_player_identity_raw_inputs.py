#!/usr/bin/env python3
"""Read-only validator for player-identity offline raw input layout."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path
from typing import Any

import protected_paths
from check_player_identity_first_evidence_readiness import (
    EXPECTED_SHOOTERGAME_SHA256,
    PLAYER_IDENTITY_RAW_RUN_PREFIX,
)
from snapshot_evidence_pack import REPO_ROOT, SHA256_RE, first_symlink_component


REPORT_SCHEMA = "obelisk.player-identity-raw-input-validation.v1"
PROTECTED_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
BINARY_NAME = "ShooterGameServer"
CORE_NAME = "core"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run validation for an existing "
            "player-identity-offline-<run-id>/raw/{ShooterGameServer,core} layout. "
            "The core file is checked by metadata only."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--root",
        type=Path,
        help="Existing player-identity-offline-<run-id> directory containing raw inputs.",
    )
    source.add_argument(
        "--binary",
        type=Path,
        help="Existing raw/ShooterGameServer path; requires --core.",
    )
    parser.add_argument("--core", type=Path, help="Existing raw/core path when --binary is used.")
    parser.add_argument(
        "--expected-binary-sha256",
        default=EXPECTED_SHOOTERGAME_SHA256,
        help="Expected ShooterGameServer SHA256. Defaults to the reviewed player-identity binary hash.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def blocker(reason: str, label: str, **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"reason": reason, "label": label}
    payload.update(extra)
    return payload


def path_contains_parent_reference(path: Path) -> bool:
    return ".." in path.parts


def direct_protected_path(path: Path) -> bool:
    try:
        return protected_paths.protected_path_status(
            path,
            protected_root=PROTECTED_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        ).protected
    except OSError:
        expanded = path.expanduser()
        return expanded.is_absolute() and is_relative_to(expanded, PROTECTED_ROOT)


def resolved_path(path: Path) -> tuple[Path | None, str | None]:
    try:
        return path.expanduser().resolve(), None
    except OSError as exc:
        return None, str(exc)


def protected_path_blockers(path: Path, label: str) -> tuple[list[dict[str, object]], Path | None]:
    resolved, error = resolved_path(path)
    if resolved is None:
        return [blocker("path_resolve_failed", label, path=str(path), detail=error or "unknown")], None
    blockers = protected_paths.protected_input_path_blockers(
        path,
        protected_root=PROTECTED_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if blockers:
        return [
            blocker(
                entry.get("reason", "path_under_protected_root"),
                label,
                path=str(path),
                resolved_path=str(resolved),
                protected_root=str(PROTECTED_ROOT),
                detail=entry.get("detail", ""),
            )
            for entry in blockers
        ], resolved
    return [], resolved


def validate_file_metadata(path: Path, label: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    record: dict[str, object] = {
        "path": str(path),
        "resolved_path": None,
        "regular_file": False,
        "symlink_free": False,
        "size_bytes": None,
    }
    blockers: list[dict[str, object]] = []

    if not path.expanduser().is_absolute():
        blockers.append(blocker("path_not_absolute", label, path=str(path)))
    if path_contains_parent_reference(path):
        blockers.append(blocker("path_contains_parent_reference", label, path=str(path)))

    path_blockers, resolved = protected_path_blockers(path, label)
    blockers.extend(path_blockers)
    if resolved is not None:
        record["resolved_path"] = str(resolved)
    if path_blockers:
        return record, blockers

    symlink_component = first_symlink_component(path)
    if symlink_component is not None:
        blockers.append(blocker("path_has_symlink_component", label, path=str(path), symlink=str(symlink_component)))
    if symlink_component is not None:
        return record, blockers

    try:
        file_stat = path.expanduser().lstat()
    except FileNotFoundError:
        blockers.append(blocker("file_missing", label, path=str(path)))
        return record, blockers
    except OSError as exc:
        blockers.append(blocker("file_stat_failed", label, path=str(path), detail=str(exc)))
        return record, blockers

    if stat.S_ISLNK(file_stat.st_mode):
        blockers.append(blocker("file_is_symlink", label, path=str(path)))
        return record, blockers
    record["symlink_free"] = True

    if not stat.S_ISREG(file_stat.st_mode):
        blockers.append(blocker("file_not_regular", label, path=str(path)))
        return record, blockers
    record["regular_file"] = True
    record["size_bytes"] = file_stat.st_size
    if file_stat.st_size <= 0:
        blockers.append(blocker("file_empty", label, path=str(path)))

    return record, blockers


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive_paths(args: argparse.Namespace) -> tuple[Path | None, Path, Path, list[dict[str, object]]]:
    blockers: list[dict[str, object]] = []
    if args.root is not None:
        run_root = args.root.expanduser()
        return run_root, run_root / "raw" / BINARY_NAME, run_root / "raw" / CORE_NAME, blockers

    if args.core is None:
        blockers.append(blocker("core_required_with_binary", "--core"))
        return None, args.binary.expanduser(), Path(), blockers

    binary = args.binary.expanduser()
    core = args.core.expanduser()
    run_root = binary.parent.parent if binary.parent.name == "raw" else None
    return run_root, binary, core, blockers


def validate_shape(
    *,
    run_root: Path | None,
    binary: Path,
    core: Path,
    explicit_binary_mode: bool,
) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    if run_root is None:
        blockers.append(blocker("raw_layout_root_not_derivable", "--binary"))
        return blockers

    if binary.name != BINARY_NAME:
        blockers.append(blocker("binary_filename_mismatch", "--binary", expected=BINARY_NAME, actual=binary.name))
    if core.name != CORE_NAME:
        blockers.append(blocker("core_filename_mismatch", "--core", expected=CORE_NAME, actual=core.name))
    if binary.parent != core.parent:
        blockers.append(blocker("raw_inputs_not_siblings", "raw", binary=str(binary), core=str(core)))
    if binary.parent.name != "raw":
        blockers.append(blocker("raw_directory_name_mismatch", "raw", expected="raw", actual=binary.parent.name))
    if core.parent.name != "raw":
        blockers.append(blocker("core_parent_name_mismatch", "--core", expected="raw", actual=core.parent.name))
    if binary.parent.parent != run_root or core.parent.parent != run_root:
        blockers.append(blocker("raw_inputs_not_under_run_root", "raw", run_root=str(run_root)))
    if run_root.name == PLAYER_IDENTITY_RAW_RUN_PREFIX or not run_root.name.startswith(PLAYER_IDENTITY_RAW_RUN_PREFIX):
        blockers.append(
            blocker(
                "run_root_name_mismatch",
                "--root" if not explicit_binary_mode else "--binary",
                expected=f"{PLAYER_IDENTITY_RAW_RUN_PREFIX}<run-id>",
                actual=run_root.name,
            )
        )

    if not direct_protected_path(run_root):
        resolved_run_root, error = resolved_path(run_root)
        if error is not None:
            blockers.append(blocker("run_root_resolve_failed", "--root", path=str(run_root), detail=error))
        elif resolved_run_root is not None and is_relative_to(resolved_run_root, REPO_ROOT):
            blockers.append(
                blocker(
                    "run_root_under_repository",
                    "--root" if not explicit_binary_mode else "--binary",
                    path=str(run_root),
                    repo_root=str(REPO_ROOT),
                )
            )

    return blockers


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    expected_sha = args.expected_binary_sha256
    initial_blockers: list[dict[str, object]] = []
    if SHA256_RE.fullmatch(expected_sha or "") is None:
        initial_blockers.append(blocker("expected_binary_sha256_invalid", "--expected-binary-sha256"))
    if args.root is not None and args.core is not None:
        initial_blockers.append(blocker("core_requires_binary_mode", "--core"))

    run_root, binary, core, path_blockers = derive_paths(args)
    initial_blockers.extend(path_blockers)
    explicit_binary_mode = args.root is None
    shape_blockers = validate_shape(
        run_root=run_root,
        binary=binary,
        core=core,
        explicit_binary_mode=explicit_binary_mode,
    )

    binary_record, binary_blockers = validate_file_metadata(binary, "--binary")
    core_record, core_blockers = validate_file_metadata(core, "--core") if core != Path() else ({}, [])

    binary_sha: str | None = None
    if not initial_blockers and not shape_blockers and not binary_blockers:
        try:
            binary_sha = sha256_file(binary)
            binary_record["sha256"] = binary_sha
        except OSError as exc:
            binary_blockers.append(blocker("binary_sha256_read_failed", "--binary", path=str(binary), detail=str(exc)))
    else:
        binary_record["sha256"] = None

    if binary_sha is not None and binary_sha != expected_sha:
        binary_blockers.append(
            blocker(
                "binary_sha256_mismatch",
                "--binary",
                expected_binary_sha256=expected_sha,
                actual_binary_sha256=binary_sha,
            )
        )

    core_record["sha256"] = None
    core_record["content_read"] = False
    core_record["metadata_only"] = True

    blockers = [*initial_blockers, *shape_blockers, *binary_blockers, *core_blockers]
    accepted = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "accepted" if accepted else "blocked",
        "ready_for_core_evidence_pack_command": accepted,
        "dry_run": True,
        "protected_root_rejected": str(PROTECTED_ROOT),
        "expected_binary_sha256": expected_sha,
        "run_root": str(run_root) if run_root is not None else None,
        "raw_dir": str(binary.parent) if binary != Path() else None,
        "binary": binary_record,
        "core": core_record,
        "blockers": blockers,
        "non_claims": [
            "does not stage, copy, hardlink, create, delete, or modify files",
            "does not read or parse core contents; core checks are metadata-only",
            "does not allow direct or resolved /servidor/ark paths outside approved offline workspaces",
            "does not run gdb, ptrace, scanners, servers, or evidence-pack builders",
            "does not prove the core matches the binary beyond raw-layout pairing and binary SHA",
        ],
    }


def main() -> int:
    args = parse_args()
    result = build_result(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
