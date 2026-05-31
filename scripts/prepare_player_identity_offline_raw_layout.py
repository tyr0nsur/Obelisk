#!/usr/bin/env python3
"""Prepare the player-identity offline raw input layout from explicit artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from check_player_identity_first_evidence_readiness import (
    EXPECTED_SHOOTERGAME_SHA256,
    PLAYER_IDENTITY_RAW_RUN_PREFIX,
)
from snapshot_evidence_pack import (
    reject_protected_input_path,
    reject_protected_output_path,
    reject_symlink_component,
    require_ignored_output_path,
)


REPORT_SCHEMA = "obelisk.player-identity-offline-raw-layout.v1"
SAFE_RUN_ID_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
REPO_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_ROOT = Path("/servidor/ark")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stage an existing non-protected ShooterGameServer and core file as "
            "player-identity-offline-<run-id>/raw/{ShooterGameServer,core}. "
            "This does not create or validate a core dump."
        )
    )
    parser.add_argument("--binary", required=True, type=Path, help="Existing offline ShooterGameServer file.")
    parser.add_argument("--core", required=True, type=Path, help="Existing offline core file.")
    parser.add_argument("--artifact-root", required=True, type=Path, help="Non-protected artifact root.")
    parser.add_argument("--run-id", required=True, help="Safe suffix for player-identity-offline-<run-id>.")
    parser.add_argument(
        "--mode",
        choices=("hardlink", "copy"),
        default="hardlink",
        help="Stage files by hardlink by default, or copy when explicitly requested.",
    )
    parser.add_argument(
        "--obelisk-commit",
        help=(
            "Reviewed Obelisk checkpoint to embed in the next core-evidence command. "
            "Defaults to the current Git HEAD only when this is omitted."
        ),
    )
    return parser.parse_args()


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(2)


def safe_run_id(value: str) -> str:
    if not value:
        fail("--run-id must not be empty")
    if value.startswith(PLAYER_IDENTITY_RAW_RUN_PREFIX):
        fail(f"--run-id must be the suffix only, without {PLAYER_IDENTITY_RAW_RUN_PREFIX}")
    if value in {".", ".."} or ".." in value:
        fail(f"unsafe --run-id: {value}")
    if any(char not in SAFE_RUN_ID_CHARS for char in value):
        fail(f"unsafe --run-id: {value}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def detect_obelisk_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def reject_direct_protected_path(path: Path, label: str, *, access: str) -> None:
    expanded = path.expanduser()
    if expanded.is_absolute() and is_relative_to(expanded, PROTECTED_ROOT):
        action = "copy inputs under" if access == "read from" else "use"
        fail(
            f"{label} must not {access} protected server root {PROTECTED_ROOT}; "
            f"{action} a non-protected artifact root first: {expanded}"
        )


def validate_input_file(path: Path, label: str) -> Path:
    reject_direct_protected_path(path, label, access="read from")
    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    if not resolved.exists():
        fail(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        fail(f"{label} must be a regular file: {resolved}")
    return resolved


def validate_artifact_root(path: Path) -> Path:
    reject_direct_protected_path(path, "--artifact-root", access="write under")
    reject_symlink_component(path, "--artifact-root")
    resolved = reject_protected_output_path(path, "--artifact-root")
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        fail(f"--artifact-root must not be under repository root {REPO_ROOT}: {resolved}")
    if resolved.exists() and not resolved.is_dir():
        fail(f"--artifact-root must be a directory: {resolved}")
    require_ignored_output_path(resolved, "--artifact-root")
    return resolved


def ensure_directory_slot(path: Path, label: str) -> None:
    if path.exists() and not path.is_dir():
        fail(f"{label} exists but is not a directory: {path}")


def ensure_output_slot(path: Path, label: str) -> None:
    if path.exists() or path.is_symlink():
        fail(f"{label} already exists; choose a new --run-id or remove the stale output: {path}")


def stage_file(source: Path, destination: Path, mode: str) -> None:
    if mode == "hardlink":
        os.link(source, destination)
    else:
        shutil.copy2(source, destination)


def build_report(args: argparse.Namespace) -> dict[str, object]:
    run_id = safe_run_id(args.run_id)
    binary = validate_input_file(args.binary, "--binary")
    core = validate_input_file(args.core, "--core")
    if binary == core:
        fail("--binary and --core must be distinct files")

    binary_sha = sha256_file(binary)
    if binary_sha != EXPECTED_SHOOTERGAME_SHA256:
        fail(
            "--binary sha256 does not match the reviewed ShooterGameServer hash "
            f"{EXPECTED_SHOOTERGAME_SHA256}: {binary_sha}"
        )
    core_sha = sha256_file(core)

    artifact_root = validate_artifact_root(args.artifact_root)
    run_root = artifact_root / f"{PLAYER_IDENTITY_RAW_RUN_PREFIX}{run_id}"
    raw_dir = run_root / "raw"
    reject_symlink_component(run_root, "run directory")
    reject_symlink_component(raw_dir, "raw directory")

    output_binary = raw_dir / "ShooterGameServer"
    output_core = raw_dir / "core"
    core_evidence_pack_dir = run_root / "core-evidence-pack"
    core_evidence_pack_manifest = core_evidence_pack_dir / "manifest.json"
    ensure_directory_slot(run_root, "run directory")
    ensure_directory_slot(raw_dir, "raw directory")
    ensure_output_slot(output_binary, "output ShooterGameServer")
    ensure_output_slot(output_core, "output core")
    ensure_output_slot(core_evidence_pack_dir, "output core evidence pack directory")

    try:
        raw_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        fail(f"failed to create raw directory {raw_dir}: {exc}")
    try:
        stage_file(binary, output_binary, args.mode)
        stage_file(core, output_core, args.mode)
    except OSError as exc:
        for staged in (output_binary, output_core):
            try:
                if staged.exists() or staged.is_symlink():
                    staged.unlink()
            except OSError:
                pass
        fail(f"failed to stage raw inputs with mode={args.mode}: {exc}")

    obelisk_commit = args.obelisk_commit or detect_obelisk_commit()
    obelisk_commit_source = "--obelisk-commit" if args.obelisk_commit else "git rev-parse --short=12 HEAD"
    next_command_argv = [
        "python3",
        "scripts/build_core_dump_evidence_pack.py",
        "--binary",
        str(output_binary),
        "--core",
        str(output_core),
        "--output-dir",
        str(core_evidence_pack_dir),
        "--obelisk-commit",
        obelisk_commit,
        "--no-default-candidates",
        "--no-default-fname-roots",
        "--no-default-fname-indices",
        "--fname-root-slot",
        "verified_fname_root_slot=0x5956f30",
        "--fname-index",
        "None=0",
        "--fname-index",
        "ClientMessage=4884",
        "--fname-index",
        "ServerChat=9619",
        "--fname-index",
        "SetActiveMissionDebugFlags=9622",
        "--gobjects-candidate",
        "gobjects=0x595b7e0",
        "--gobjects-sample-index",
        "0",
        "--gobjects-sample-index",
        "1",
        "--gobjects-sample-index",
        "25447",
    ]

    return {
        "schema": REPORT_SCHEMA,
        "ready_for_core_evidence_pack_command": True,
        "run_root": str(run_root),
        "raw_dir": str(raw_dir),
        "core_evidence_pack": {
            "output_dir": str(core_evidence_pack_dir),
            "manifest": str(core_evidence_pack_manifest),
        },
        "obelisk": {
            "commit": obelisk_commit,
            "commit_source": obelisk_commit_source,
        },
        "reviewed_seed_scope": {
            "binary_sha256": EXPECTED_SHOOTERGAME_SHA256,
            "fname_root_slot": "0x5956f30",
            "fname_indices": {
                "None": 0,
                "ClientMessage": 4884,
                "ServerChat": 9619,
                "SetActiveMissionDebugFlags": 9622,
            },
            "gobjects_candidate": "0x595b7e0",
            "gobjects_sample_indices": [0, 1, 25447],
            "non_claim": "binary-hash-scoped reviewed seed only; not a stable offset or public SDK promotion",
        },
        "binary": {
            "source": str(binary),
            "staged": str(output_binary),
            "sha256": binary_sha,
            "size_bytes": binary.stat().st_size,
            "matches_reviewed_hash": True,
        },
        "core": {
            "source": str(core),
            "staged": str(output_core),
            "sha256": core_sha,
            "size_bytes": core.stat().st_size,
        },
        "mode": args.mode,
        "next_command_env": {"PYTHONDONTWRITEBYTECODE": "1"},
        "next_command_argv": next_command_argv,
        "next_command": f"PYTHONDONTWRITEBYTECODE=1 {shlex.join(next_command_argv)}",
        "non_claims": [
            "does not create a core dump",
            "does not validate that the core is usable for player identity evidence",
            "does not read from or write to /servidor/ark outside approved offline workspaces",
            "does not attach to processes, start servers, run scanners, or promote runtime identity",
        ],
    }


def main() -> int:
    try:
        report = build_report(parse_args())
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        if exc.code:
            print(exc.code, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
