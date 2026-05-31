#!/usr/bin/env python3
"""Capture candidate-only radare2 orientation windows for reviewed UFunction clues."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import protected_paths  # noqa: E402
from check_command_chat_response_static_orientation import RESPONSE_PATH_TARGETS  # noqa: E402
from check_player_identity_static_admin_thunks import ADMIN_THUNKS  # noqa: E402
from check_player_identity_static_lifecycle_orientation import LIFECYCLE_ANCHORS  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component  # noqa: E402


DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
DEFAULT_OUTPUT_ROOT = Path("/tmp/obelisk-radare2-static-orientation")
DEFAULT_ORIENTATION_JSON = (
    REPO_ROOT / "docs" / "research" / "2026-05-31-player-identity-static-target-orientation.json"
)
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
SCHEMA = "obelisk.radare2-static-orientation-windows.v1"
ADDRESS_CONVENTION = "non-PIE ELF VMA for the reviewed ARK Linux ShooterGameServer binary"
SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_.-]+")
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
HEX_RE = re.compile(r"^0x[0-9a-fA-F]+$")


@dataclass(frozen=True)
class OrientationWindow:
    group: str
    target: str
    role: str
    vma: int
    instruction_count: int
    source: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_hex(value: Any, *, field: str, target: str) -> int:
    if not isinstance(value, str) or HEX_RE.fullmatch(value) is None:
        raise SystemExit(f"{target}: {field} must be a hex VMA string: {value!r}")
    return int(value, 16)


def safe_component(value: str) -> str:
    safe = SAFE_COMPONENT_RE.sub("_", value).strip("._")
    return safe or "unnamed"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], *, timeout_sec: int) -> dict[str, Any]:
    def output_text(value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value

    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_sec,
        )
    except FileNotFoundError as exc:
        return {"argv": command, "status": "missing", "error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": command,
            "status": "timeout",
            "timeout_sec": timeout_sec,
            "stdout": output_text(exc.stdout),
            "stderr": output_text(exc.stderr),
        }
    return {
        "argv": command,
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def first_symlink_component(path: Path) -> Path | None:
    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() else expanded.absolute()
    current = Path(candidate.anchor) if candidate.anchor else Path()
    parts = candidate.parts[1:] if candidate.anchor else candidate.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def reject_symlink(path: Path, label: str) -> None:
    symlink = first_symlink_component(path)
    if symlink is not None:
        raise SystemExit(f"{label} must not be a symlink: {symlink}")


def resolve_binary(path: Path) -> Path:
    reject_symlink_component(path, "--binary")
    resolved = reject_protected_input_path(path, "--binary")
    if not resolved.exists():
        raise SystemExit(f"--binary does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"--binary must be a file: {resolved}")
    return resolved


def resolve_output_root(path: Path) -> Path:
    reject_symlink(path, "--output-root")
    resolved = protected_paths.reject_protected_output_path(
        path,
        "--output-root",
        approved_roots=(),
    )
    if resolved.exists() and not resolved.is_dir():
        raise SystemExit(f"--output-root must be a directory: {resolved}")
    return resolved


def resolve_orientation_json(path: Path) -> Path:
    resolved = reject_protected_input_path(path, "--orientation-json")
    reject_symlink_component(path, "--orientation-json")
    if not resolved.exists():
        raise SystemExit(f"--orientation-json does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"--orientation-json must be a file: {resolved}")
    return resolved


def safe_run_id(value: str) -> str:
    if SAFE_RUN_ID_RE.fullmatch(value) is None or ".." in value:
        raise SystemExit(f"--run-id contains unsafe characters: {value}")
    return value


def ensure_directory(path: Path, label: str) -> None:
    reject_symlink(path, label)
    path.mkdir(parents=True, exist_ok=True)
    reject_symlink(path, label)
    if not path.is_dir():
        raise SystemExit(f"{label} must be a directory: {path}")


def write_text(path: Path, value: str) -> None:
    reject_symlink(path, "orientation output file")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    parent_fd: int | None = None
    file_fd: int | None = None
    try:
        parent_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        if hasattr(os, "O_NOFOLLOW"):
            parent_flags |= os.O_NOFOLLOW
        parent_fd = os.open(path.parent, parent_flags)
        file_fd = os.open(path.name, flags, 0o644, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise SystemExit(f"orientation output file must not be a symlink: {path}") from exc
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)

    with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
        file_fd = None
        handle.write(value)


def has_path_separator(value: str) -> bool:
    return "/" in value or (os.altsep is not None and os.altsep in value)


def resolve_radare2_executable(
    candidate: str,
    *,
    explicit: bool,
) -> tuple[str, list[dict[str, Any]]]:
    path = Path(candidate).expanduser()
    resolved = reject_protected_input_path(path, "--radare2")
    display = str(resolved if path.is_absolute() or has_path_separator(candidate) else path)
    if not resolved.exists():
        return display, [
            {
                "reason": "radare2_not_found",
                "path": display,
                "source": "explicit" if explicit else "path",
            }
        ]
    if not resolved.is_file():
        return str(resolved), [{"reason": "radare2_not_file", "path": str(resolved)}]
    if not os.access(resolved, os.X_OK):
        return str(resolved), [{"reason": "radare2_not_executable", "path": str(resolved)}]
    return str(resolved), []


def find_radare2(explicit: str | None) -> tuple[str, list[dict[str, Any]]]:
    if explicit:
        if has_path_separator(explicit) or Path(explicit).expanduser().is_absolute():
            return resolve_radare2_executable(explicit, explicit=True)
        found = shutil.which(explicit)
        if found is None:
            return explicit, [{"reason": "radare2_not_found", "path": explicit, "source": "explicit"}]
        return resolve_radare2_executable(found, explicit=True)
    for name in ("radare2", "r2"):
        path = shutil.which(name)
        if path is not None:
            return resolve_radare2_executable(path, explicit=False)
    return "radare2", [{"reason": "radare2_not_found", "path": "radare2", "source": "path"}]


def load_player_identity_windows(
    path: Path,
    *,
    registration_instructions: int,
    thunk_instructions: int,
) -> list[OrientationWindow]:
    resolved = reject_protected_input_path(path, "--orientation-json")
    reject_symlink_component(path, "--orientation-json")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if payload.get("schema") != "obelisk.player-identity-static-target-orientation.v1":
        raise SystemExit(f"{resolved}: unexpected player identity orientation schema")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise SystemExit(f"{resolved}: missing candidates list")

    windows: list[OrientationWindow] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise SystemExit(f"{resolved}: candidate entries must be objects")
        target = candidate.get("target")
        if not isinstance(target, str) or not target:
            raise SystemExit(f"{resolved}: candidate missing target")
        registration_vma = parse_hex(candidate.get("registration_vma"), field="registration_vma", target=target)
        windows.append(
            OrientationWindow(
                group="player-identity",
                target=target,
                role="registration",
                vma=registration_vma,
                instruction_count=registration_instructions,
                source=str(resolved),
            )
        )
        thunk_candidates = candidate.get("thunk_candidates")
        if not isinstance(thunk_candidates, list) or not thunk_candidates:
            raise SystemExit(f"{resolved}: {target} missing thunk_candidates")
        for index, thunk in enumerate(thunk_candidates):
            windows.append(
                OrientationWindow(
                    group="player-identity",
                    target=target,
                    role=f"thunk-{index}",
                    vma=parse_hex(thunk, field=f"thunk_candidates[{index}]", target=target),
                    instruction_count=thunk_instructions,
                    source=str(resolved),
                )
            )
    return windows


def load_admin_windows(*, registration_instructions: int, thunk_instructions: int) -> list[OrientationWindow]:
    windows: list[OrientationWindow] = []
    for thunk in ADMIN_THUNKS:
        windows.extend(
            [
                OrientationWindow(
                    group="admin",
                    target=thunk.target,
                    role="registration",
                    vma=thunk.registration_vma,
                    instruction_count=registration_instructions,
                    source="scripts/check_player_identity_static_admin_thunks.py",
                ),
                OrientationWindow(
                    group="admin",
                    target=thunk.target,
                    role="fname-init",
                    vma=thunk.fname_init_vma,
                    instruction_count=registration_instructions,
                    source="scripts/check_player_identity_static_admin_thunks.py",
                ),
                OrientationWindow(
                    group="admin",
                    target=thunk.target,
                    role="thunk",
                    vma=thunk.thunk_vma,
                    instruction_count=thunk_instructions,
                    source="scripts/check_player_identity_static_admin_thunks.py",
                ),
            ]
        )
    return windows


def load_lifecycle_windows(*, registration_instructions: int, thunk_instructions: int) -> list[OrientationWindow]:
    windows: list[OrientationWindow] = []
    for anchor in LIFECYCLE_ANCHORS:
        windows.extend(
            [
                OrientationWindow(
                    group="lifecycle",
                    target=anchor.target,
                    role="registration-class-load",
                    vma=anchor.registration_class_load_vma,
                    instruction_count=registration_instructions,
                    source="scripts/check_player_identity_static_lifecycle_orientation.py",
                ),
                OrientationWindow(
                    group="lifecycle",
                    target=anchor.target,
                    role="registration",
                    vma=anchor.registration_vma,
                    instruction_count=registration_instructions,
                    source="scripts/check_player_identity_static_lifecycle_orientation.py",
                ),
                OrientationWindow(
                    group="lifecycle",
                    target=anchor.target,
                    role="thunk",
                    vma=anchor.thunk_vma,
                    instruction_count=thunk_instructions,
                    source="scripts/check_player_identity_static_lifecycle_orientation.py",
                ),
            ]
        )
    return windows


def load_chat_response_windows(*, registration_instructions: int, thunk_instructions: int) -> list[OrientationWindow]:
    windows: list[OrientationWindow] = []
    for target in RESPONSE_PATH_TARGETS:
        windows.extend(
            [
                OrientationWindow(
                    group="chat-response",
                    target=target.target,
                    role="registration",
                    vma=target.expected_registration_vma,
                    instruction_count=registration_instructions,
                    source="scripts/check_command_chat_response_static_orientation.py",
                ),
                OrientationWindow(
                    group="chat-response",
                    target=target.target,
                    role="thunk",
                    vma=target.expected_thunk_vma,
                    instruction_count=thunk_instructions,
                    source="scripts/check_command_chat_response_static_orientation.py",
                ),
            ]
        )
    return windows


def selected_windows(args: argparse.Namespace) -> list[OrientationWindow]:
    groups = set(args.target_group)
    windows: list[OrientationWindow] = []
    if "player-identity" in groups:
        windows.extend(
            load_player_identity_windows(
                args.orientation_json,
                registration_instructions=args.registration_instructions,
                thunk_instructions=args.thunk_instructions,
            )
        )
    if "admin" in groups:
        windows.extend(
            load_admin_windows(
                registration_instructions=args.registration_instructions,
                thunk_instructions=args.thunk_instructions,
            )
        )
    if "lifecycle" in groups:
        windows.extend(
            load_lifecycle_windows(
                registration_instructions=args.registration_instructions,
                thunk_instructions=args.thunk_instructions,
            )
        )
    if "chat-response" in groups:
        windows.extend(
            load_chat_response_windows(
                registration_instructions=args.registration_instructions,
                thunk_instructions=args.thunk_instructions,
            )
        )
    return windows


def git_commit() -> str | None:
    result = run_command(["git", "rev-parse", "HEAD"], timeout_sec=5)
    if result["status"] != "ok":
        return None
    return result["stdout"].strip() or None


def capture_window(
    radare2: str,
    binary: Path,
    window: OrientationWindow,
    output_dir: Path,
    *,
    timeout_sec: int,
) -> dict[str, Any]:
    filename = (
        f"{safe_component(window.group)}__{safe_component(window.target)}__"
        f"{safe_component(window.role)}__{window.vma:#x}.r2.txt"
    )
    output_path = output_dir / filename
    command_text = f"s {window.vma:#x}; pd {window.instruction_count}; q"
    command = [
        radare2,
        "-q",
        "-e",
        "io.cache=true",
        "-e",
        "scr.color=false",
        "-c",
        command_text,
        str(binary),
    ]
    result = run_command(command, timeout_sec=timeout_sec)
    content = (
        "# candidate-only radare2 orientation window\n"
        "# not artifact-gate evidence; not promotion evidence\n"
        f"# group: {window.group}\n"
        f"# target: {window.target}\n"
        f"# role: {window.role}\n"
        f"# vma: {window.vma:#x}\n"
        f"# source: {window.source}\n"
        f"# argv: {json.dumps(command)}\n\n"
        f"{result.get('stdout', '')}"
    )
    if result.get("stderr"):
        content += "\n# stderr\n" + result["stderr"]
    write_text(output_path, content)
    return {
        "group": window.group,
        "target": window.target,
        "role": window.role,
        "vma": f"{window.vma:#x}",
        "instruction_count": window.instruction_count,
        "source": window.source,
        "output": str(output_path),
        "argv": command,
        "radare2_status": result["status"],
        "returncode": result.get("returncode"),
    }


def build_manifest(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    binary = resolve_binary(args.binary)
    output_root = resolve_output_root(args.output_root)
    args.orientation_json = resolve_orientation_json(args.orientation_json)
    default_run_id = f"{utc_now().replace('-', '').replace(':', '')}-radare2-static-orientation"
    requested_run_id = args.run_id if args.run_id is not None else default_run_id
    run_id = safe_run_id(requested_run_id)
    output_dir = output_root / run_id
    ensure_directory(output_dir, "--output-root run directory")

    binary_sha256 = sha256_file(binary)
    blockers: list[dict[str, Any]] = []
    if binary_sha256 != args.expected_binary_sha256:
        blockers.append(
            {
                "reason": "binary_sha256_mismatch",
                "expected": args.expected_binary_sha256,
                "value": binary_sha256,
            }
        )

    radare2, radare2_blockers = find_radare2(args.radare2)
    blockers.extend(radare2_blockers)
    if radare2_blockers:
        version_probe = {
            "argv": [radare2, "-v"],
            "status": "missing",
            "stderr": "radare2/r2 not found or not executable",
        }
    else:
        version_probe = run_command([radare2, "-v"], timeout_sec=args.timeout_sec)
    if not radare2_blockers and version_probe["status"] != "ok":
        blockers.append({"reason": "radare2_version_probe_failed", "status": version_probe["status"]})

    captured: list[dict[str, Any]] = []
    windows = selected_windows(args)
    if not blockers:
        windows_dir = output_dir / "windows"
        ensure_directory(windows_dir, "radare2 windows output")
        for window in windows:
            record = capture_window(radare2, binary, window, windows_dir, timeout_sec=args.timeout_sec)
            captured.append(record)
            if record["radare2_status"] != "ok":
                blockers.append(
                    {
                        "reason": "radare2_window_capture_failed",
                        "target": record["target"],
                        "role": record["role"],
                        "vma": record["vma"],
                        "status": record["radare2_status"],
                    }
                )
    status = "candidate_only_orientation_captured" if not blockers else "blocked"
    manifest_path = output_dir / "manifest.json"
    manifest = {
        "schema": SCHEMA,
        "status": status,
        "candidate_evidence_status": "candidate_only_orientation",
        "not_artifact_gate": True,
        "artifact_gate": {
            "registered": False,
            "may_gate_artifacts": False,
            "consume_mode": "orientation_only",
            "promote_mode": "blocked",
        },
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "produced_at": utc_now(),
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "output_root": str(output_root),
        "output_dir": str(output_dir),
        "scope": {
            "address_convention": ADDRESS_CONVENTION,
            "target_groups": sorted(set(args.target_group)),
            "binary": str(binary),
            "binary_sha256": binary_sha256,
            "expected_binary_sha256": args.expected_binary_sha256,
        },
        "tool_provenance": {
            "radare2": {
                "path": radare2,
                "version_probe": version_probe,
            },
            "obelisk_commit": git_commit(),
            "wrapper": str(Path(__file__).resolve()),
            "sha256_method": "python hashlib.sha256 over offline binary bytes",
        },
        "windows_requested": [
            {
                "group": window.group,
                "target": window.target,
                "role": window.role,
                "vma": f"{window.vma:#x}",
                "instruction_count": window.instruction_count,
                "source": window.source,
            }
            for window in windows
        ],
        "windows_captured": captured,
        "non_claims": [
            "radare2 windows are candidate-only static orientation for this reviewed binary hash",
            "this manifest is not artifact-gate evidence and must not be used in promote mode",
            "does not prove UFunction object identity, FName indices, property chains, parameter offsets, player principal mapping, permissions, commands, chat replies, or lifecycle semantics",
            "does not promote public SDK, runtime hooks, object lookup, ResourceHandle, mutation, or return override",
            "does not replace a non-protected complete core evidence pack, reviewed reflection inventory pack, focal snapshots, second-source evidence, or approved runtime validation",
        ],
        "blockers": blockers,
    }
    write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest, 0 if not blockers else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture bounded radare2 disassembly windows for player identity, admin, "
            "and chat UFunction candidates against an offline ShooterGameServer binary."
        )
    )
    parser.add_argument("binary", nargs="?", type=Path, default=DEFAULT_BINARY, help="Offline ShooterGameServer.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Explicit non-protected output root. Defaults under /tmp.",
    )
    parser.add_argument("--run-id", help="Safe output subdirectory name. Defaults to a UTC timestamp.")
    parser.add_argument("--radare2", help="Path to radare2/r2. Defaults to radare2 or r2 on PATH.")
    parser.add_argument(
        "--expected-binary-sha256",
        default=EXPECTED_BINARY_SHA256,
        help="Expected SHA256 for the reviewed offline ShooterGameServer.",
    )
    parser.add_argument(
        "--orientation-json",
        type=Path,
        default=DEFAULT_ORIENTATION_JSON,
        help="Candidate-only player identity orientation JSON.",
    )
    parser.add_argument(
        "--target-group",
        choices=("player-identity", "admin", "lifecycle", "chat-response"),
        action="append",
        default=[],
        help="Capture only a target group. Repeatable. Defaults to all groups.",
    )
    parser.add_argument("--registration-instructions", type=int, default=36)
    parser.add_argument("--thunk-instructions", type=int, default=64)
    parser.add_argument("--timeout-sec", type=int, default=30)
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    args = parser.parse_args()
    if not args.target_group:
        args.target_group = ["player-identity", "admin", "lifecycle", "chat-response"]
    if args.registration_instructions < 1 or args.thunk_instructions < 1:
        raise SystemExit("instruction counts must be positive")
    if args.timeout_sec < 1:
        raise SystemExit("--timeout-sec must be positive")
    return args


def main() -> int:
    manifest, status = build_manifest(parse_args())
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
