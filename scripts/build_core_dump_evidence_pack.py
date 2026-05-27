#!/usr/bin/env python3
"""Build an offline ShooterGameServer core dump evidence pack.

The script is intentionally passive: it reads an existing core file and an offline
ShooterGameServer binary, runs reproducible ELF/GDB inspection commands, and writes
artifacts outside the server tree. It does not attach to a process or create a dump.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
ALLOWED_SERVER_ARTIFACT_ROOT = SERVER_ROOT / "obelisk" / "dumps"

DEFAULT_CANDIDATES = [
    ("static_fname_root_slot", 0x5956F30),
    ("static_fname_mutex_slot", 0x5956F38),
    ("static_fname_init_flag", 0x5956F40),
    ("static_fname_bucket_array", 0x594E020),
]

DEFAULT_FNAME_ROOT_SLOTS = [
    ("static_fname_root_slot", 0x5956F30),
]

DEFAULT_FNAME_INDICES = [
    ("None", 0),
    ("ClientMessage", 4884),
    ("ServerChat", 9619),
]

FNAME_CHUNK_SIZE = 0x4000
GOBJECTS_POINTER_OFFSETS = (0x0, 0x8, 0x10, 0x18, 0x20)
DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES = 64 * 1024 * 1024
DEFAULT_POINTER_SCAN_MAX_HITS = 64


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(command: list[str], output_path: Path) -> dict[str, object]:
    result = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output_path.write_text(result.stdout, encoding="utf-8", errors="replace")
    stderr_path = output_path.with_suffix(output_path.suffix + ".stderr")
    if result.stderr:
        stderr_path.write_text(result.stderr, encoding="utf-8", errors="replace")
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


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {value}") from exc


def parse_candidate(value: str) -> tuple[str, int]:
    if "=" in value:
        label, raw_address = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("candidate label must not be empty")
        return label, parse_int(raw_address)
    address = parse_int(value)
    return f"candidate_{address:x}", address


def parse_fname_index(value: str) -> tuple[str, int]:
    if "=" in value:
        label, raw_index = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("FName index label must not be empty")
        return label, parse_int(raw_index)
    index = parse_int(value)
    return f"fname_{index}", index


def extend_candidate_dump_commands(
    lines: list[str],
    candidates: list[tuple[str, int]],
) -> None:
    for label, address in candidates:
        lines.extend(
            [
                f'printf "\\n== candidate {label} @ 0x{address:x} ==\\n"',
                f"x/16gx 0x{address:x}",
                f"x/64bx 0x{address:x}",
            ]
        )


def extend_fname_root_commands(
    lines: list[str],
    fname_root_slots: list[tuple[str, int]],
    fname_indices: list[tuple[str, int]],
) -> None:
    for label, address in fname_root_slots:
        lines.extend(
            [
                f'printf "\\n== fname root {label} slot @ 0x{address:x} ==\\n"',
                f"x/gx 0x{address:x}",
                f"set $fname_table = *(void**)0x{address:x}",
                'printf "table = %p\\n", $fname_table',
                "x/272gx $fname_table",
                "x/wx ((char*)$fname_table)+0x800",
                "x/wx ((char*)$fname_table)+0x804",
            ]
        )
        for index_label, index in fname_indices:
            chunk_index = index // FNAME_CHUNK_SIZE
            chunk_offset = chunk_index * 8
            entry_offset = (index % FNAME_CHUNK_SIZE) * 8
            lines.extend(
                [
                    f'printf "\\n-- fname index {index_label} [{index}] --\\n"',
                    f"set $fname_chunk = *(void**)(((char*)$fname_table)+0x{chunk_offset:x})",
                    f"set $fname_entry = *(void**)(((char*)$fname_chunk)+0x{entry_offset:x})",
                    'printf "chunk = %p entry = %p string =\\n", $fname_chunk, $fname_entry',
                    "x/s ((char*)$fname_entry)+0x10",
                    "x/8gx $fname_entry",
                ]
            )


def extend_gobjects_candidate_commands(
    lines: list[str],
    gobjects_candidates: list[tuple[str, int]],
) -> None:
    for label, address in gobjects_candidates:
        lines.extend(
            [
                f'printf "\\n== gobjects candidate {label} slot @ 0x{address:x} ==\\n"',
                f"x/16gx 0x{address:x}",
                f"x/32wx 0x{address:x}",
                f"set $gobjects_root = *(void**)0x{address:x}",
                'printf "root = %p\\n", $gobjects_root',
                "x/96gx $gobjects_root",
                "x/64wx $gobjects_root",
            ]
        )
        for offset in GOBJECTS_POINTER_OFFSETS:
            lines.extend(
                [
                    f'printf "\\n-- gobjects root+0x{offset:x} pointer preview --\\n"',
                    f"set $gobjects_maybe_ptr = *(void**)(((char*)$gobjects_root)+0x{offset:x})",
                    'printf "value = %p\\n", $gobjects_maybe_ptr',
                    "x/16gx $gobjects_maybe_ptr",
                ]
            )


def extend_pointer_scan_commands(
    lines: list[str],
    pointer_values: list[tuple[str, int]],
    max_mapping_bytes: int,
    max_hits: int,
) -> None:
    if not pointer_values:
        return

    values = ", ".join(f"({label!r}, 0x{address:x})" for label, address in pointer_values)
    lines.extend(
        [
            'printf "\\n== pointer value scans ==\\n"',
            "python",
            "import gdb",
            "import re",
            f"values = [{values}]",
            f"max_mapping_bytes = {max_mapping_bytes}",
            f"max_hits = {max_hits}",
            "mapping_re = re.compile(r'^\\s*(0x[0-9a-fA-F]+)\\s+(0x[0-9a-fA-F]+)\\s+\\S+\\s+\\S+\\s+(?P<perms>\\S+)\\s*(?P<path>.*)$')",
            "mappings = []",
            "for line in gdb.execute('info proc mappings', to_string=True).splitlines():",
            "    match = mapping_re.match(line)",
            "    if not match:",
            "        continue",
            "    start = int(match.group(1), 16)",
            "    end = int(match.group(2), 16)",
            "    perms = match.group('perms')",
            "    path = match.group('path').strip()",
            "    size = max(0, end - start)",
            "    if size == 0 or size > max_mapping_bytes or 'r' not in perms or 'w' not in perms:",
            "        continue",
            "    mappings.append((start, end, path))",
            "for label, value in values:",
            "    print(f'\\n== pointer scan {label} value 0x{value:x} ==')",
            "    hits = 0",
            "    for start, end, path in mappings:",
            "        if hits >= max_hits:",
            "            break",
            "        try:",
            "            output = gdb.execute(f'find /g 0x{start:x}, 0x{end:x}, 0x{value:x}', to_string=True)",
            "        except gdb.error as exc:",
            "            print(f'skipped 0x{start:x}-0x{end:x} {path}: {exc}')",
            "            continue",
            "        for raw in output.splitlines():",
            "            text = raw.strip()",
            "            if not text.startswith('0x'):",
            "                continue",
            "            print(f'hit {label} value=0x{value:x} slot={text} mapping=0x{start:x}-0x{end:x} {path}')",
            "            hits += 1",
            "            if hits >= max_hits:",
            "                break",
            "    print(f'pointer scan {label} hits={hits} max_hits={max_hits}')",
            "end",
        ]
    )


def write_gdb_command_file(
    path: Path,
    candidates: list[tuple[str, int]],
    fname_root_slots: list[tuple[str, int]],
    fname_indices: list[tuple[str, int]],
    gobjects_candidates: list[tuple[str, int]],
    pointer_scan_values: list[tuple[str, int]] | None = None,
    pointer_scan_max_mapping_bytes: int = DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES,
    pointer_scan_max_hits: int = DEFAULT_POINTER_SCAN_MAX_HITS,
) -> None:
    lines = [
        "set pagination off",
        "set confirm off",
        "set print pretty off",
        "set print elements 0",
        "set print repeats 0",
        "info files",
        "info proc mappings",
        "info threads",
        "thread apply all bt 24",
        "maintenance info sections ALLOBJ",
    ]

    extend_candidate_dump_commands(lines, candidates)
    extend_fname_root_commands(lines, fname_root_slots, fname_indices)
    extend_gobjects_candidate_commands(lines, gobjects_candidates)
    extend_pointer_scan_commands(
        lines,
        pointer_scan_values or [],
        pointer_scan_max_mapping_bytes,
        pointer_scan_max_hits,
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an offline evidence pack from a ShooterGameServer binary and an "
            "existing Linux core dump. Does not touch server state."
        )
    )
    parser.add_argument(
        "--binary",
        required=True,
        type=Path,
        help="Path to the ShooterGameServer binary matching the core dump.",
    )
    parser.add_argument(
        "--core",
        required=True,
        type=Path,
        help="Path to the existing Linux core dump.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help=(
            "Artifact directory to create or reuse. Under /servidor/ark, only "
            "/servidor/ark/obelisk/dumps is allowed."
        ),
    )
    parser.add_argument(
        "--candidate",
        action="append",
        type=parse_candidate,
        default=[],
        metavar="LABEL=ADDR",
        help=(
            "Additional virtual address to dump from the core with GDB. May be repeated. "
            "If no candidates are provided, current FName static-root leads are used."
        ),
    )
    parser.add_argument(
        "--no-default-candidates",
        action="store_true",
        help="Do not include the current static FName root candidate addresses.",
    )
    parser.add_argument(
        "--fname-root-slot",
        action="append",
        type=parse_candidate,
        default=[],
        metavar="LABEL=ADDR",
        help=(
            "Pointer slot to inspect as a legacy indirect FName table root. May be "
            "repeated. Defaults to the current static FName root slot unless "
            "--no-default-fname-roots is set."
        ),
    )
    parser.add_argument(
        "--no-default-fname-roots",
        action="store_true",
        help="Do not emit direct FName entry reads for the current static root slot.",
    )
    parser.add_argument(
        "--fname-index",
        action="append",
        type=parse_fname_index,
        default=[],
        metavar="LABEL=INDEX",
        help=(
            "FName index to resolve from each FName root slot. May be repeated. "
            "Defaults to None, ClientMessage, and ServerChat."
        ),
    )
    parser.add_argument(
        "--no-default-fname-indices",
        action="store_true",
        help="Do not include the default known FName clue indices.",
    )
    parser.add_argument(
        "--gobjects-candidate",
        action="append",
        type=parse_candidate,
        default=[],
        metavar="LABEL=ADDR",
        help=(
            "Candidate GUObjectArray/GObjects global slot address to preview from the "
            "core. May be repeated. Use --candidate for raw root/window dumps. This is "
            "bounded triage only."
        ),
    )
    parser.add_argument(
        "--scan-pointer-value",
        action="append",
        type=parse_candidate,
        default=[],
        metavar="LABEL=ADDR",
        help=(
            "Offline core-only pointer scan. Searches bounded core mappings for 64-bit "
            "slots equal to ADDR and prints hit slots in gdb-core.txt. Useful for "
            "finding globals that point to a confirmed in-memory FName table or "
            "GUObjectArray root. May be repeated."
        ),
    )
    parser.add_argument(
        "--pointer-scan-max-mapping-bytes",
        type=parse_int,
        default=DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES,
        help=(
            "Maximum individual core mapping size to scan for --scan-pointer-value. "
            f"Default: {DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES}."
        ),
    )
    parser.add_argument(
        "--pointer-scan-max-hits",
        type=parse_int,
        default=DEFAULT_POINTER_SCAN_MAX_HITS,
        help=(
            "Maximum hits to print per --scan-pointer-value. "
            f"Default: {DEFAULT_POINTER_SCAN_MAX_HITS}."
        ),
    )
    parser.add_argument(
        "--scan-fname-tables",
        action="store_true",
        help=(
            "Run the offline legacy FName table scanner against the core and write "
            "core.fname-table-scan.json. This scans the core file only and does not "
            "attach to a process."
        ),
    )
    parser.add_argument(
        "--fname-scan-max-none-hits",
        type=parse_int,
        default=256,
        help="Maximum 'None' string hits for --scan-fname-tables. Default: 256.",
    )
    parser.add_argument(
        "--fname-scan-max-pointer-hits",
        type=parse_int,
        default=2048,
        help="Maximum pointer-chain hits for --scan-fname-tables. Default: 2048.",
    )
    parser.add_argument(
        "--skip-core-sha256",
        action="store_true",
        help="Skip hashing the core file when it is too large for a quick triage run.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    binary = args.binary.resolve()
    core = args.core.resolve()
    output_dir = args.output_dir.resolve()

    if is_relative_to(output_dir, SERVER_ROOT) and not is_relative_to(
        output_dir, ALLOWED_SERVER_ARTIFACT_ROOT
    ):
        print(
            "refusing to write evidence artifacts under "
            f"{SERVER_ROOT}; use {ALLOWED_SERVER_ARTIFACT_ROOT}",
            file=sys.stderr,
        )
        return 2
    if not binary.is_file():
        print(f"binary does not exist: {binary}", file=sys.stderr)
        return 2
    if not core.is_file():
        print(f"core does not exist: {core}", file=sys.stderr)
        return 2
    if shutil.which("gdb") is None:
        print("gdb is required for core dump evidence packs", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = []
    if not args.no_default_candidates:
        candidates.extend(DEFAULT_CANDIDATES)
    candidates.extend(args.candidate)
    fname_root_slots = []
    if not args.no_default_fname_roots:
        fname_root_slots.extend(DEFAULT_FNAME_ROOT_SLOTS)
    fname_root_slots.extend(args.fname_root_slot)
    fname_indices = []
    if not args.no_default_fname_indices:
        fname_indices.extend(DEFAULT_FNAME_INDICES)
    fname_indices.extend(args.fname_index)
    gobjects_candidates = list(args.gobjects_candidate)
    pointer_scan_values = list(args.scan_pointer_value)

    if args.pointer_scan_max_mapping_bytes <= 0:
        print("--pointer-scan-max-mapping-bytes must be positive", file=sys.stderr)
        return 2
    if args.pointer_scan_max_hits <= 0:
        print("--pointer-scan-max-hits must be positive", file=sys.stderr)
        return 2
    if args.fname_scan_max_none_hits <= 0:
        print("--fname-scan-max-none-hits must be positive", file=sys.stderr)
        return 2
    if args.fname_scan_max_pointer_hits <= 0:
        print("--fname-scan-max-pointer-hits must be positive", file=sys.stderr)
        return 2

    commands: dict[str, dict[str, object]] = {}
    try:
        commands["binary_file"] = run_command(
            ["file", str(binary)],
            output_dir / "ShooterGameServer.file.txt",
        )
        commands["core_file"] = run_command(
            ["file", str(core)],
            output_dir / "core.file.txt",
        )
        commands["binary_readelf_header"] = run_command(
            ["readelf", "-h", "-W", str(binary)],
            output_dir / "ShooterGameServer.readelf-header.txt",
        )
        commands["binary_readelf_programs"] = run_command(
            ["readelf", "-l", "-W", str(binary)],
            output_dir / "ShooterGameServer.readelf-programs.txt",
        )
        commands["core_readelf_header"] = run_command(
            ["readelf", "-h", "-W", str(core)],
            output_dir / "core.readelf-header.txt",
        )
        commands["core_readelf_notes"] = run_command(
            ["readelf", "-n", "-W", str(core)],
            output_dir / "core.readelf-notes.txt",
        )
        commands["core_readelf_programs"] = run_command(
            ["readelf", "-l", "-W", str(core)],
            output_dir / "core.readelf-programs.txt",
        )
        commands["strings_clues"] = run_command(
            [
                "strings",
                "-a",
                "-tx",
                str(binary),
            ],
            output_dir / "ShooterGameServer.strings.txt",
        )
        commands["objdump"] = run_command(
            ["objdump", "-d", "-M", "intel", str(binary)],
            output_dir / "ShooterGameServer.objdump",
        )

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            gdb_commands = Path(handle.name)
        try:
            write_gdb_command_file(
                gdb_commands,
                candidates,
                fname_root_slots,
                fname_indices,
                gobjects_candidates,
                pointer_scan_values,
                args.pointer_scan_max_mapping_bytes,
                args.pointer_scan_max_hits,
            )
            shutil.copy2(gdb_commands, output_dir / "gdb-core-commands.txt")
            commands["gdb_core"] = run_command(
                [
                    "gdb",
                    "-q",
                    "-nx",
                    "-batch",
                    "-x",
                    str(gdb_commands),
                    str(binary),
                    str(core),
                ],
                output_dir / "gdb-core.txt",
            )
        finally:
            gdb_commands.unlink(missing_ok=True)

        if args.scan_fname_tables:
            commands["core_fname_table_scan"] = run_command(
                [
                    sys.executable,
                    str(REPO_ROOT / "scripts" / "scan_core_fname_tables.py"),
                    "--core",
                    str(core),
                    "--max-none-hits",
                    str(args.fname_scan_max_none_hits),
                    "--max-pointer-hits",
                    str(args.fname_scan_max_pointer_hits),
                    "--json",
                ],
                output_dir / "core.fname-table-scan.json",
            )

        for name, record in commands.items():
            if name == "gdb_core":
                continue
            require_success(record)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    binary_sha256 = sha256_file(binary)
    core_sha256 = None if args.skip_core_sha256 else sha256_file(core)

    (output_dir / "ShooterGameServer.sha256.txt").write_text(
        f"{binary_sha256}  {binary}\n",
        encoding="utf-8",
    )
    if core_sha256:
        (output_dir / "core.sha256.txt").write_text(
            f"{core_sha256}  {core}\n",
            encoding="utf-8",
        )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "binary": {
            "path": str(binary),
            "sha256": binary_sha256,
            "size_bytes": binary.stat().st_size,
        },
        "core": {
            "path": str(core),
            "sha256": core_sha256,
            "size_bytes": core.stat().st_size,
        },
        "candidates": [
            {"label": label, "address": f"0x{address:x}"} for label, address in candidates
        ],
        "fname_root_slots": [
            {"label": label, "address": f"0x{address:x}"}
            for label, address in fname_root_slots
        ],
        "fname_indices": [
            {"label": label, "index": index} for label, index in fname_indices
        ],
        "gobjects_candidates": [
            {"label": label, "address": f"0x{address:x}"}
            for label, address in gobjects_candidates
        ],
        "pointer_scan_values": [
            {"label": label, "address": f"0x{address:x}"}
            for label, address in pointer_scan_values
        ],
        "pointer_scan_limits": {
            "max_mapping_bytes": args.pointer_scan_max_mapping_bytes,
            "max_hits": args.pointer_scan_max_hits,
        },
        "fname_table_scan": {
            "enabled": args.scan_fname_tables,
            "max_none_hits": args.fname_scan_max_none_hits,
            "max_pointer_hits": args.fname_scan_max_pointer_hits,
        },
        "artifacts": {
            "binary_file": str(output_dir / "ShooterGameServer.file.txt"),
            "core_file": str(output_dir / "core.file.txt"),
            "binary_readelf_header": str(output_dir / "ShooterGameServer.readelf-header.txt"),
            "binary_readelf_programs": str(output_dir / "ShooterGameServer.readelf-programs.txt"),
            "core_readelf_header": str(output_dir / "core.readelf-header.txt"),
            "core_readelf_notes": str(output_dir / "core.readelf-notes.txt"),
            "core_readelf_programs": str(output_dir / "core.readelf-programs.txt"),
            "strings": str(output_dir / "ShooterGameServer.strings.txt"),
            "objdump": str(output_dir / "ShooterGameServer.objdump"),
            "gdb_commands": str(output_dir / "gdb-core-commands.txt"),
            "gdb_core": str(output_dir / "gdb-core.txt"),
            "core_fname_table_scan": (
                str(output_dir / "core.fname-table-scan.json")
                if args.scan_fname_tables
                else None
            ),
        },
        "commands": commands,
        "promotion_gate": (
            "Core dump evidence can confirm in-memory values for this one process image, "
            "but it does not by itself promote stable offsets or prove initialization flow. "
            "Require static xrefs and a second isolated capture before runtime code."
        ),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    print(f"wrote offline core evidence pack: {output_dir}")
    print(f"manifest: {manifest_path}")
    print(f"gdb artifact: {output_dir / 'gdb-core.txt'}")
    if commands["gdb_core"]["returncode"] != 0:
        print("warning: gdb returned non-zero; inspect gdb-core.txt.stderr", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
