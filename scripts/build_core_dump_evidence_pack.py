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
import re
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
GOBJECTS_DIRECT_CHUNKS_OFFSET = 0x10
GOBJECTS_DIRECT_COUNT_OFFSET = 0x24
GOBJECTS_CHUNK_SIZE = 0x10000
FUOBJECT_ITEM_SIZE = 0x10
MAX_GOBJECTS_SAMPLE_INDICES = 32
DEFAULT_POINTER_SCAN_MAX_MAPPING_BYTES = 64 * 1024 * 1024
DEFAULT_POINTER_SCAN_MAX_HITS = 64
OBJDUMP_XREF_RE = re.compile(
    r"^\s*(?P<address>[0-9a-fA-F]+):\s+(?P<body>.*?)"
    r"(?:#|<)\s*(?P<target>(?:0x)?[0-9a-fA-F]+)"
)
OBJDUMP_FUNCTION_RE = re.compile(r"^(?P<address>[0-9a-fA-F]+)\s+<(?P<label>[^>]+)>:$")
OBJDUMP_INSTRUCTION_RE = re.compile(r"^\s*(?P<address>[0-9a-fA-F]+):\s+(?P<body>.*)$")
HEX_LITERAL_RE = re.compile(r"0x[0-9a-fA-F]+")
ANCHOR_GROUP_MAX_GAP_BYTES = 0x100
OVERSIZED_FUNCTION_GROUP_XREFS = 512
OVERSIZED_FUNCTION_GROUP_SPAN_BYTES = 0x10000


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


def detect_obelisk_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--short=12", "HEAD"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


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


def normalize_hex(value: str | int) -> str:
    return f"0x{int(value, 16) if isinstance(value, str) else value:x}"


def classify_xref_access(instruction: str) -> str:
    tokens = instruction.lower().split()
    while tokens and re.fullmatch(r"[0-9a-f]{2}", tokens[0]):
        tokens.pop(0)
    if not tokens:
        return "unknown"

    mnemonic = tokens[0]
    if mnemonic.startswith("call"):
        return "call"
    if mnemonic.startswith("j"):
        return "jump"
    if mnemonic == "lea":
        return "address"

    operands = " ".join(tokens[1:])
    if mnemonic in ("cmp", "test") and ("[rip" in operands or "(%rip)" in operands):
        return "load"
    if "[rip" in operands:
        parts = [part.strip() for part in operands.split(",", 1)]
        if len(parts) == 2:
            return "store" if "[rip" in parts[0] else "load"
    if "(%rip)" in operands:
        parts = [part.strip() for part in operands.split(",", 1)]
        if len(parts) == 2:
            return "load" if "(%rip)" in parts[0] else "store"
    return "other"


def gobjects_static_xref_targets(gobjects_candidates: list[tuple[str, int]]) -> dict[str, str]:
    targets: dict[str, str] = {}
    for label, address in gobjects_candidates:
        targets[normalize_hex(address)] = f"{label}.root"
        targets[normalize_hex(address + GOBJECTS_DIRECT_CHUNKS_OFFSET)] = f"{label}.chunks"
        targets[normalize_hex(address + GOBJECTS_DIRECT_COUNT_OFFSET)] = f"{label}.count"
        targets[normalize_hex(address + 0x58)] = f"{label}.serial"
    return targets


def xref_record(
    *,
    line_number: int,
    instruction_address: str,
    target: str,
    target_label: str,
    instruction: str,
    function_start: str | None,
    function_label: str | None,
) -> dict[str, object]:
    return {
        "line": line_number,
        "instruction_address": instruction_address,
        "target_address": target,
        "target_label": target_label,
        "instruction": instruction,
        "access": classify_xref_access(instruction),
        "function_start": function_start,
        "function_label": function_label,
    }


def immediate_targets_from_instruction(instruction: str, targets: dict[str, str]) -> list[str]:
    return sorted(
        {
            normalize_hex(match)
            for match in HEX_LITERAL_RE.findall(instruction)
            if normalize_hex(match) in targets
        }
    )


def build_function_groups(xrefs: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    function_groups: dict[str, dict[str, object]] = {}
    for refs in xrefs.values():
        for ref in refs:
            access = str(ref["access"])
            group_key = str(ref.get("function_start") or "unknown")
            instruction_address = int(str(ref["instruction_address"]), 16)
            group = function_groups.setdefault(
                group_key,
                {
                    "function_start": ref.get("function_start"),
                    "function_label": ref.get("function_label"),
                    "xref_count": 0,
                    "target_labels": [],
                    "access_counts": {},
                    "sample_instruction_addresses": [],
                    "first_xref": ref["instruction_address"],
                    "last_xref": ref["instruction_address"],
                    "xref_span_bytes": 0,
                    "oversized": False,
                },
            )
            group["xref_count"] = int(group["xref_count"]) + 1
            target_labels = group["target_labels"]
            if isinstance(target_labels, list) and ref["target_label"] not in target_labels:
                target_labels.append(ref["target_label"])
            group_access_counts = group["access_counts"]
            if isinstance(group_access_counts, dict):
                group_access_counts[access] = int(group_access_counts.get(access, 0)) + 1
            samples = group["sample_instruction_addresses"]
            if isinstance(samples, list) and len(samples) < 5:
                samples.append(ref["instruction_address"])

            first = int(str(group["first_xref"]), 16)
            last = int(str(group["last_xref"]), 16)
            first = min(first, instruction_address)
            last = max(last, instruction_address)
            group["first_xref"] = f"0x{first:x}"
            group["last_xref"] = f"0x{last:x}"
            group["xref_span_bytes"] = last - first
            group["oversized"] = (
                int(group["xref_count"]) >= OVERSIZED_FUNCTION_GROUP_XREFS
                or int(group["xref_span_bytes"]) >= OVERSIZED_FUNCTION_GROUP_SPAN_BYTES
            )
    return sorted(
        function_groups.values(),
        key=lambda item: (-int(item["xref_count"]), str(item["function_start"])),
    )


def build_anchor_groups(xrefs: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    refs = sorted(
        (ref for target_refs in xrefs.values() for ref in target_refs),
        key=lambda ref: int(str(ref["instruction_address"]), 16),
    )
    groups: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    last_address: int | None = None

    for ref in refs:
        address = int(str(ref["instruction_address"]), 16)
        if current is None or last_address is None or address - last_address > ANCHOR_GROUP_MAX_GAP_BYTES:
            current = {
                "anchor_start": ref["instruction_address"],
                "anchor_end": ref["instruction_address"],
                "xref_count": 0,
                "target_labels": [],
                "access_counts": {},
                "sample_instruction_addresses": [],
            }
            groups.append(current)

        current["anchor_end"] = ref["instruction_address"]
        current["xref_count"] = int(current["xref_count"]) + 1
        target_labels = current["target_labels"]
        if isinstance(target_labels, list) and ref["target_label"] not in target_labels:
            target_labels.append(ref["target_label"])
        access_counts = current["access_counts"]
        if isinstance(access_counts, dict):
            access = str(ref["access"])
            access_counts[access] = int(access_counts.get(access, 0)) + 1
        samples = current["sample_instruction_addresses"]
        if isinstance(samples, list) and len(samples) < 5:
            samples.append(ref["instruction_address"])
        last_address = address

    return sorted(groups, key=lambda item: (-int(item["xref_count"]), str(item["anchor_start"])))


def collect_static_xrefs(objdump_path: Path, targets: dict[str, str]) -> dict[str, object]:
    xrefs: dict[str, list[dict[str, object]]] = {target: [] for target in targets}
    target_needles = tuple(
        sorted({needle for target in targets for needle in (target.lower(), target.lower()[2:])})
    )
    function_start: str | None = None
    function_label: str | None = None
    with objdump_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.rstrip("\n")
            function_match = OBJDUMP_FUNCTION_RE.match(stripped)
            if function_match:
                function_start = normalize_hex(function_match.group("address"))
                function_label = function_match.group("label")
                continue

            stripped_lower = stripped.lower()
            if not any(needle in stripped_lower for needle in target_needles):
                continue

            instruction_match = OBJDUMP_INSTRUCTION_RE.match(stripped)
            if not instruction_match:
                continue
            instruction_address = normalize_hex(instruction_match.group("address"))
            instruction = " ".join(instruction_match.group("body").split())

            matched_targets: set[str] = set()
            match = OBJDUMP_XREF_RE.search(stripped)
            if match:
                target = normalize_hex(match.group("target"))
                if target in targets:
                    matched_targets.add(target)
            matched_targets.update(immediate_targets_from_instruction(instruction, targets))

            for target in sorted(matched_targets):
                xrefs[target].append(
                    xref_record(
                        line_number=line_number,
                        instruction_address=instruction_address,
                        target=target,
                        target_label=targets[target],
                        instruction=instruction,
                        function_start=function_start,
                        function_label=function_label,
                    )
            )

    access_counts: dict[str, int] = {}
    for refs in xrefs.values():
        for ref in refs:
            access = str(ref["access"])
            access_counts[access] = access_counts.get(access, 0) + 1

    return {
        "targets": [{"address": address, "label": label} for address, label in sorted(targets.items())],
        "xrefs": xrefs,
        "access_counts": dict(sorted(access_counts.items())),
        "function_groups": build_function_groups(xrefs),
        "anchor_groups": build_anchor_groups(xrefs),
    }


def validate_gobjects_sample_options(
    gobjects_candidates: list[tuple[str, int]],
    gobjects_sample_indices: list[int],
    fname_root_slots: list[tuple[str, int]],
) -> str | None:
    for index in gobjects_sample_indices:
        if index < 0:
            return "--gobjects-sample-index must be non-negative"
    if gobjects_sample_indices and not gobjects_candidates:
        return "--gobjects-sample-index requires at least one --gobjects-candidate"
    if gobjects_sample_indices and not fname_root_slots:
        return (
            "--gobjects-sample-index requires at least one --fname-root-slot for "
            "NamePrivate resolution"
        )
    if len(gobjects_sample_indices) > MAX_GOBJECTS_SAMPLE_INDICES:
        return (
            "--gobjects-sample-index may be repeated at most "
            f"{MAX_GOBJECTS_SAMPLE_INDICES} times"
        )
    return None


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


def extend_gobjects_sample_commands(
    lines: list[str],
    gobjects_candidates: list[tuple[str, int]],
    sample_indices: list[int],
    fname_root_slots: list[tuple[str, int]],
) -> None:
    if not gobjects_candidates or not sample_indices:
        return

    for label, address in gobjects_candidates:
        for index in sample_indices:
            chunk_index = index // GOBJECTS_CHUNK_SIZE
            chunk_offset = chunk_index * 8
            item_offset = (index % GOBJECTS_CHUNK_SIZE) * FUOBJECT_ITEM_SIZE
            lines.extend(
                [
                    f'printf "\\n== gobjects sample {label}[{index}] direct @ 0x{address:x} ==\\n"',
                    f"set $gobjects_direct = (char*)0x{address:x}",
                    f"set $gobjects_chunks = *(void**)($gobjects_direct+0x{GOBJECTS_DIRECT_CHUNKS_OFFSET:x})",
                    f"set $gobjects_count = *(int*)($gobjects_direct+0x{GOBJECTS_DIRECT_COUNT_OFFSET:x})",
                    'printf "chunks = %p count = %d\\n", $gobjects_chunks, $gobjects_count',
                    f"set $gobjects_chunk = *(void**)(((char*)$gobjects_chunks)+0x{chunk_offset:x})",
                    f"set $fuobject_item = ((char*)$gobjects_chunk)+0x{item_offset:x}",
                    'printf "chunk = %p item = %p\\n", $gobjects_chunk, $fuobject_item',
                    "x/2gx $fuobject_item",
                    "set $uobject = *(void**)$fuobject_item",
                    "set $fuobject_metadata = *(unsigned long long*)(((char*)$fuobject_item)+0x8)",
                    "set $fuobject_flags = *(int*)(((char*)$fuobject_item)+0x8)",
                    "set $fuobject_serial = *(int*)(((char*)$fuobject_item)+0xc)",
                    (
                        'printf "object = %p item_metadata = 0x%llx item_flags = 0x%x '
                        'serial = %d\\n", $uobject, $fuobject_metadata, '
                        "$fuobject_flags, $fuobject_serial"
                    ),
                    "x/8gx $uobject",
                    "set $uobject_vtable = *(void**)$uobject",
                    "set $uobject_flags = *(int*)(((char*)$uobject)+0x8)",
                    "set $uobject_internal_index = *(int*)(((char*)$uobject)+0xc)",
                    "set $uobject_class = *(void**)(((char*)$uobject)+0x10)",
                    "set $uobject_name_index = *(int*)(((char*)$uobject)+0x18)",
                    "set $uobject_name_number = *(int*)(((char*)$uobject)+0x1c)",
                    "set $uobject_outer = *(void**)(((char*)$uobject)+0x20)",
                    (
                        'printf "vtable = %p flags = 0x%x internal_index = %d '
                        'class = %p name_index = %d name_number = %d outer = %p\\n", '
                        "$uobject_vtable, $uobject_flags, $uobject_internal_index, "
                        "$uobject_class, $uobject_name_index, $uobject_name_number, "
                        "$uobject_outer"
                    ),
                    (
                        f'printf "sample_index = {index} internal_index_match = %d\\n", '
                        f"$uobject_internal_index == {index}"
                    ),
                    "x/8gx $uobject_class",
                    "set $class_name_index = *(int*)(((char*)$uobject_class)+0x18)",
                    "set $class_name_number = *(int*)(((char*)$uobject_class)+0x1c)",
                    'printf "class_name_index = %d class_name_number = %d\\n", $class_name_index, $class_name_number',
                ]
            )
            for fname_label, fname_address in fname_root_slots:
                lines.extend(
                    [
                        f'printf "\\n-- resolve sample names through {fname_label} @ 0x{fname_address:x} --\\n"',
                        f"set $fname_table = *(void**)0x{fname_address:x}",
                        'printf "fname_table = %p\\n", $fname_table',
                        f"set $object_fname_chunk = *(void**)(((char*)$fname_table)+(($uobject_name_index/{FNAME_CHUNK_SIZE})*8))",
                        f"set $object_fname_entry = *(void**)(((char*)$object_fname_chunk)+(($uobject_name_index%{FNAME_CHUNK_SIZE})*8))",
                        f"set $class_fname_chunk = *(void**)(((char*)$fname_table)+(($class_name_index/{FNAME_CHUNK_SIZE})*8))",
                        f"set $class_fname_entry = *(void**)(((char*)$class_fname_chunk)+(($class_name_index%{FNAME_CHUNK_SIZE})*8))",
                        'printf "object_fname_entry = %p class_fname_entry = %p\\n", $object_fname_entry, $class_fname_entry',
                        'printf "object name: "',
                        "x/s ((char*)$object_fname_entry)+0x10",
                        'printf "class name: "',
                        "x/s ((char*)$class_fname_entry)+0x10",
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
    gobjects_sample_indices: list[int] | None = None,
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
    sample_indices = gobjects_sample_indices or []
    extend_gobjects_sample_commands(
        lines,
        gobjects_candidates,
        sample_indices,
        fname_root_slots,
    )
    if not sample_indices:
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
            "Candidate GUObjectArray/GObjects address to preview from the core. The "
            "legacy preview treats ADDR as a pointer slot; --gobjects-sample-index "
            "treats ADDR as a direct GUObjectArray struct. May be repeated. This is "
            "bounded triage only."
        ),
    )
    parser.add_argument(
        "--gobjects-sample-index",
        action="append",
        type=parse_int,
        default=[],
        metavar="INDEX",
        help=(
            "Emit bounded GDB reads for FUObjectItem INDEX from each "
            "--gobjects-candidate interpreted as a direct GUObjectArray struct. When "
            "sampling is enabled, the legacy indirect slot-preview block is skipped. The "
            "sample prints chunk/item/object fields and resolves UObject/Class "
            "NamePrivate through each --fname-root-slot. May be repeated."
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
    parser.add_argument(
        "--obelisk-commit",
        default=None,
        help=(
            "Obelisk commit to record in manifest.json. Defaults to the current "
            "repository HEAD short hash, or 'unknown' outside a Git checkout."
        ),
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
    gobjects_sample_indices = list(args.gobjects_sample_index)
    pointer_scan_values = list(args.scan_pointer_value)

    gobjects_sample_error = validate_gobjects_sample_options(
        gobjects_candidates,
        gobjects_sample_indices,
        fname_root_slots,
    )
    if gobjects_sample_error:
        print(gobjects_sample_error, file=sys.stderr)
        return 2
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
                gobjects_sample_indices,
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

    gobjects_static_xrefs_path = None
    if gobjects_candidates:
        static_xrefs = collect_static_xrefs(
            output_dir / "ShooterGameServer.objdump",
            gobjects_static_xref_targets(gobjects_candidates),
        )
        gobjects_static_xrefs_path = output_dir / "gobjects-static-xrefs.json"
        gobjects_static_xrefs_path.write_text(
            json.dumps(static_xrefs, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "obelisk": {
            "commit": args.obelisk_commit or detect_obelisk_commit(REPO_ROOT),
        },
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
        "gobjects_sample_indices": gobjects_sample_indices,
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
            "gobjects_static_xrefs": str(gobjects_static_xrefs_path) if gobjects_static_xrefs_path else None,
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
