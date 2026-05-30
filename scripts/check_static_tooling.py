#!/usr/bin/env python3
"""Check optional offline static-analysis tool availability safely."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import protected_paths  # noqa: E402


TOOL_COMMANDS = {
    "analyzeHeadless": {
        "which": "analyzeHeadless",
        "version_args": ["-version"],
        "version_ok_returncodes": {0, 1},
    },
    "radare2": {
        "which": "radare2",
        "version_args": ["-v"],
    },
    "r2": {
        "which": "r2",
        "version_args": ["-v"],
    },
    "rizin": {
        "which": "rizin",
        "version_args": ["-v"],
    },
}
SMOKE_TOOLS = {"analyzeHeadless", "radare2"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_excerpt(value: str | bytes, limit: int = 4000) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= limit:
        return value
    return value[:limit] + "\n[truncated]\n"


def run_command(
    command: list[str],
    *,
    timeout_sec: int,
    ok_returncodes: set[int] | None = None,
) -> dict[str, Any]:
    if ok_returncodes is None:
        ok_returncodes = {0}
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
        return {
            "argv": command,
            "status": "missing",
            "error": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": command,
            "status": "timeout",
            "timeout_sec": timeout_sec,
            "stdout_excerpt": text_excerpt(exc.stdout or ""),
            "stderr_excerpt": text_excerpt(exc.stderr or ""),
        }
    return {
        "argv": command,
        "status": "ok" if completed.returncode in ok_returncodes else "failed",
        "returncode": completed.returncode,
        "stdout_excerpt": text_excerpt(completed.stdout),
        "stderr_excerpt": text_excerpt(completed.stderr),
    }


def tool_report(name: str, *, timeout_sec: int) -> dict[str, Any]:
    spec = TOOL_COMMANDS[name]
    executable = shutil.which(spec["which"])
    report: dict[str, Any] = {
        "name": name,
        "available": executable is not None,
        "path": executable,
    }
    if executable is not None:
        report["version_probe"] = run_command(
            [executable, *spec["version_args"]],
            timeout_sec=timeout_sec,
            ok_returncodes=spec.get("version_ok_returncodes"),
        )
    return report


def reject_symlink(path: Path, label: str) -> None:
    if path.is_symlink():
        raise SystemExit(f"{label} must not be a symlink: {path}")


def ensure_real_directory(path: Path, label: str) -> None:
    reject_symlink(path, label)
    if path.exists() and not path.is_dir():
        raise SystemExit(f"{label} must be a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)
    reject_symlink(path, label)
    if not path.is_dir():
        raise SystemExit(f"{label} must be a directory: {path}")


def resolve_input_binary(path: Path) -> Path:
    resolved = protected_paths.reject_protected_input_path(path, "--binary")
    reject_symlink(path.expanduser(), "--binary")
    if not resolved.exists():
        raise SystemExit(f"--binary does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"--binary must be a file: {resolved}")
    return resolved


def resolve_output_root(path: Path) -> Path:
    reject_symlink(path.expanduser(), "--output-root")
    resolved = protected_paths.reject_protected_output_path(path, "--output-root")
    if resolved.exists() and not resolved.is_dir():
        raise SystemExit(f"--output-root must be a directory: {resolved}")
    return resolved


def write_text(path: Path, value: str) -> None:
    reject_symlink(path, "smoke output file")
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
            raise SystemExit(f"smoke output file must not be a symlink: {path}") from exc
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)

    with os.fdopen(file_fd, "w", encoding="utf-8") as handle:
        file_fd = None
        handle.write(value)


def run_radare2_smoke(tool: dict[str, Any], binary: Path, output_root: Path, *, timeout_sec: int) -> dict[str, Any]:
    if not tool["available"]:
        return {"tool": "radare2", "status": "skipped", "reason": "tool_missing"}
    smoke_root = output_root / "radare2-smoke"
    ensure_real_directory(smoke_root, "radare2 smoke output")
    command = [tool["path"], "-q", "-c", "iI;q", str(binary)]
    result = run_command(command, timeout_sec=timeout_sec)
    stdout = smoke_root / "radare2-smoke.stdout"
    stderr = smoke_root / "radare2-smoke.stderr"
    write_text(stdout, result.get("stdout_excerpt", ""))
    write_text(stderr, result.get("stderr_excerpt", ""))
    return {
        "tool": "radare2",
        "status": result["status"],
        "argv": command,
        "stdout": str(stdout),
        "stderr": str(stderr),
        "returncode": result.get("returncode"),
    }


def run_ghidra_smoke(tool: dict[str, Any], binary: Path, output_root: Path, *, timeout_sec: int) -> dict[str, Any]:
    if not tool["available"]:
        return {"tool": "analyzeHeadless", "status": "skipped", "reason": "tool_missing"}
    smoke_root = output_root / "ghidra-smoke"
    project_root = smoke_root / "project"
    ensure_real_directory(smoke_root, "Ghidra smoke output")
    reject_symlink(project_root, "Ghidra project root")
    command = [
        tool["path"],
        str(project_root),
        "ObeliskStaticToolingSmoke",
        "-import",
        str(binary),
        "-noanalysis",
        "-deleteProject",
    ]
    result = run_command(command, timeout_sec=timeout_sec)
    stdout = smoke_root / "ghidra-headless-smoke.stdout"
    stderr = smoke_root / "ghidra-headless-smoke.stderr"
    write_text(stdout, result.get("stdout_excerpt", ""))
    write_text(stderr, result.get("stderr_excerpt", ""))
    return {
        "tool": "analyzeHeadless",
        "status": result["status"],
        "argv": command,
        "stdout": str(stdout),
        "stderr": str(stderr),
        "returncode": result.get("returncode"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Report optional offline static tooling availability. With --run-smoke, run "
            "bounded import/identity checks only against an approved offline binary path."
        )
    )
    parser.add_argument("--binary", type=Path, help="Offline ShooterGameServer copy to smoke-check.")
    parser.add_argument("--output-root", type=Path, help="Non-protected directory for smoke stdout/stderr.")
    parser.add_argument(
        "--tool",
        choices=sorted(TOOL_COMMANDS),
        action="append",
        help="Tool to check. Defaults to analyzeHeadless, radare2, r2, and rizin.",
    )
    parser.add_argument(
        "--require-tool",
        choices=sorted(TOOL_COMMANDS),
        action="append",
        default=[],
        help="Exit non-zero if the named optional tool is not available.",
    )
    parser.add_argument("--run-smoke", action="store_true", help="Run bounded radare2/Ghidra smoke checks.")
    parser.add_argument("--timeout-sec", type=int, default=120, help="Per-command timeout.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    return parser.parse_args()


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.timeout_sec <= 0:
        raise SystemExit("--timeout-sec must be positive")
    selected_tools = list(
        dict.fromkeys(
            [
                *(args.tool or list(TOOL_COMMANDS)),
                *args.require_tool,
                *(sorted(SMOKE_TOOLS) if args.run_smoke else []),
            ]
        )
    )
    reports = {name: tool_report(name, timeout_sec=args.timeout_sec) for name in selected_tools}
    missing_required = [name for name in args.require_tool if not reports.get(name, {}).get("available")]
    report: dict[str, Any] = {
        "schema": "obelisk.static-tooling-check.v1",
        "generated_utc": utc_now(),
        "status": "blocked" if missing_required else "ok",
        "tools": reports,
        "missing_required_tools": missing_required,
    }
    if args.binary is not None:
        binary = resolve_input_binary(args.binary)
        report["binary"] = {
            "path": str(binary),
            "sha256": sha256_file(binary),
        }
    else:
        binary = None
    if args.run_smoke:
        if binary is None:
            raise SystemExit("--run-smoke requires --binary")
        if args.output_root is None:
            raise SystemExit("--run-smoke requires --output-root")
        output_root = resolve_output_root(args.output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        report["output_root"] = str(output_root)
        report["smoke"] = [
            run_radare2_smoke(
                reports.get("radare2") or tool_report("radare2", timeout_sec=args.timeout_sec),
                binary,
                output_root,
                timeout_sec=args.timeout_sec,
            ),
            run_ghidra_smoke(
                reports.get("analyzeHeadless") or tool_report("analyzeHeadless", timeout_sec=args.timeout_sec),
                binary,
                output_root,
                timeout_sec=args.timeout_sec,
            ),
        ]
        if any(item["status"] in {"failed", "timeout"} for item in report["smoke"]):
            report["status"] = "blocked"
    return report


def main() -> int:
    args = parse_args()
    report = build_report(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"status={report['status']}")
        for name, item in report["tools"].items():
            path = item["path"] or "missing"
            print(f"{name}: {path}")
        if report["missing_required_tools"]:
            print("missing required tools: " + ", ".join(report["missing_required_tools"]), file=sys.stderr)
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
