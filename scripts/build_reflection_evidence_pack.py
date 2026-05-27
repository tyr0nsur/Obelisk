#!/usr/bin/env python3
"""Build an offline ReflectionScanner evidence pack.

The script is intentionally passive: it reads a ShooterGameServer binary and copied
Obelisk logs, writes reproducible static/analyzer artifacts, and never touches server
state or runtime markers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANALYZER = REPO_ROOT / "scripts" / "analyze_reflectionscanner_capture.py"
SERVER_ROOT = Path("/servidor/ark")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def unique_copy_path(directory: Path, source: Path) -> Path:
    candidate = directory / source.name
    if not candidate.exists():
        return candidate

    stem = source.stem
    suffix = source.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def run_command(command: list[str], output_path: Path) -> dict[str, object]:
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output_path.write_text(result.stdout, encoding="utf-8")
    stderr_path = output_path.with_suffix(output_path.suffix + ".stderr")
    if result.stderr:
        stderr_path.write_text(result.stderr, encoding="utf-8")
    elif stderr_path.exists():
        stderr_path.unlink()

    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": str(output_path),
        "stderr": str(stderr_path) if result.stderr else None,
    }


def require_success(record: dict[str, object]) -> None:
    if record["returncode"] != 0:
        command = " ".join(str(part) for part in record["command"])
        raise RuntimeError(f"command failed with exit {record['returncode']}: {command}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an offline evidence pack from a ShooterGameServer binary and copied "
            "Obelisk logs. Outputs readelf/objdump metadata plus analyzer JSON."
        )
    )
    parser.add_argument(
        "--binary",
        required=True,
        type=Path,
        help="Path to the offline ShooterGameServer binary to hash/disassemble.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Artifact directory to create or reuse. Must not be under /servidor/ark.",
    )
    parser.add_argument(
        "--analyzer",
        type=Path,
        default=DEFAULT_ANALYZER,
        help="ReflectionScanner analyzer script path.",
    )
    parser.add_argument(
        "--obelisk-commit",
        help="Optional commit override passed through to the analyzer evidence pack.",
    )
    parser.add_argument(
        "logs",
        nargs="+",
        type=Path,
        help="Copied Obelisk log path(s) to preserve and analyze.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    binary = args.binary.resolve()
    analyzer = args.analyzer.resolve()
    output_dir = args.output_dir.resolve()
    logs = [path.resolve() for path in args.logs]

    if is_relative_to(output_dir, SERVER_ROOT):
        print(
            f"refusing to write evidence artifacts under {SERVER_ROOT}",
            file=sys.stderr,
        )
        return 2
    if not binary.is_file():
        print(f"binary does not exist: {binary}", file=sys.stderr)
        return 2
    if not analyzer.is_file():
        print(f"analyzer does not exist: {analyzer}", file=sys.stderr)
        return 2
    for log in logs:
        if not log.is_file():
            print(f"log does not exist: {log}", file=sys.stderr)
            return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    copied_logs: list[Path] = []
    for log in logs:
        copied_log = unique_copy_path(logs_dir, log)
        shutil.copy2(log, copied_log)
        copied_logs.append(copied_log)

    commands: dict[str, dict[str, object]] = {}
    try:
        sha256_path = output_dir / "ShooterGameServer.sha256.txt"
        sha256_value = sha256_file(binary)
        sha256_path.write_text(f"{sha256_value}  {binary}\n", encoding="utf-8")

        commands["file"] = run_command(
            ["file", str(binary)],
            output_dir / "ShooterGameServer.file.txt",
        )
        commands["readelf_header"] = run_command(
            ["readelf", "-h", "-W", str(binary)],
            output_dir / "ShooterGameServer.readelf-header.txt",
        )
        commands["readelf_sections"] = run_command(
            ["readelf", "-S", "-W", str(binary)],
            output_dir / "ShooterGameServer.readelf-sections.txt",
        )
        commands["readelf_programs"] = run_command(
            ["readelf", "-l", "-W", str(binary)],
            output_dir / "ShooterGameServer.readelf-programs.txt",
        )
        commands["objdump"] = run_command(
            ["objdump", "-d", "-M", "intel", str(binary)],
            output_dir / "ShooterGameServer.objdump",
        )

        for record in commands.values():
            require_success(record)

        analyzer_command = [
            sys.executable,
            str(analyzer),
            "--json",
            "--binary",
            str(binary),
            "--objdump-xrefs",
            str(output_dir / "ShooterGameServer.objdump"),
        ]
        if args.obelisk_commit:
            analyzer_command.extend(["--obelisk-commit", args.obelisk_commit])
        analyzer_command.extend(str(path) for path in copied_logs)
        commands["analyzer"] = run_command(
            analyzer_command,
            output_dir / "analyzer-evidence.json",
        )
        require_success(commands["analyzer"])
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "binary": {
            "path": str(binary),
            "sha256": sha256_file(binary),
            "size_bytes": binary.stat().st_size,
        },
        "logs": [str(path) for path in copied_logs],
        "artifacts": {
            "sha256": str(output_dir / "ShooterGameServer.sha256.txt"),
            "file": str(output_dir / "ShooterGameServer.file.txt"),
            "readelf_header": str(output_dir / "ShooterGameServer.readelf-header.txt"),
            "readelf_sections": str(output_dir / "ShooterGameServer.readelf-sections.txt"),
            "readelf_programs": str(output_dir / "ShooterGameServer.readelf-programs.txt"),
            "objdump": str(output_dir / "ShooterGameServer.objdump"),
            "analyzer_json": str(output_dir / "analyzer-evidence.json"),
        },
        "commands": commands,
        "promotion_gate": (
            "Offline pack only. Do not promote offsets without isolated runtime evidence "
            "or independent static validation."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"wrote offline evidence pack: {output_dir}")
    print(f"manifest: {manifest_path}")
    print(f"analyzer evidence: {output_dir / 'analyzer-evidence.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
