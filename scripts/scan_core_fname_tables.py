#!/usr/bin/env python3
"""Scan an ELF core file for legacy UE4 FName table shaped candidates.

This is offline-only tooling. It reads an existing core dump and does not attach to a
running process. The scanner starts from known FName strings such as "None", finds
entry-pointer and chunk-pointer chains, then validates requested FName indices.
"""

from __future__ import annotations

import argparse
import json
import mmap
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path


PT_LOAD = 1
FNAME_CHUNK_SIZE = 0x4000
DEFAULT_INDICES = [
    ("None", 0),
    ("ClientMessage", 4884),
    ("ServerChat", 9619),
    ("SetActiveMissionDebugFlags", 9622),
]
SCAN_SCHEMA = "obelisk.core-fname-table-scan.v1"
ROOT_VALIDATION_SCHEMA = "obelisk.core-fname-root-validation.v1"
MANIFEST_SCHEMA = "obelisk.fname-index-manifest.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SERVER_ROOT = Path("/servidor/ark")
PROTECTED_ROOTS = (SERVER_ROOT,)
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class LoadSegment:
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int

    @property
    def end_offset(self) -> int:
        return self.offset + self.filesz

    @property
    def end_vaddr(self) -> int:
        return self.vaddr + self.filesz

    def contains_vaddr(self, address: int, size: int = 1) -> bool:
        return self.vaddr <= address and address + size <= self.end_vaddr

    def vaddr_to_offset(self, address: int) -> int:
        return self.offset + (address - self.vaddr)

    def offset_to_vaddr(self, offset: int) -> int:
        return self.vaddr + (offset - self.offset)


class CoreMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle = path.open("rb")
        self.mmap = mmap.mmap(self.handle.fileno(), 0, access=mmap.ACCESS_READ)
        self.segments = parse_elf64_load_segments(self.mmap)

    def close(self) -> None:
        self.mmap.close()
        self.handle.close()

    def segment_for_vaddr(self, address: int, size: int = 1) -> LoadSegment | None:
        for segment in self.segments:
            if segment.contains_vaddr(address, size):
                return segment
        return None

    def read(self, address: int, size: int) -> bytes | None:
        segment = self.segment_for_vaddr(address, size)
        if segment is None:
            return None
        offset = segment.vaddr_to_offset(address)
        return self.mmap[offset : offset + size]

    def read_u32(self, address: int) -> int | None:
        data = self.read(address, 4)
        return None if data is None else struct.unpack("<I", data)[0]

    def read_ptr(self, address: int) -> int | None:
        data = self.read(address, 8)
        return None if data is None else struct.unpack("<Q", data)[0]

    def read_c_string(self, address: int, max_len: int = 128) -> str | None:
        data = self.read(address, max_len)
        if data is None:
            return None
        end = data.find(b"\x00")
        if end < 0:
            return None
        raw = data[:end]
        if not raw:
            return ""
        try:
            return raw.decode("ascii")
        except UnicodeDecodeError:
            return None

    def iter_find(self, needle: bytes, limit: int) -> list[int]:
        hits: list[int] = []
        for segment in self.segments:
            start = segment.offset
            end = segment.end_offset
            cursor = start
            while len(hits) < limit:
                found = self.mmap.find(needle, cursor, end)
                if found < 0:
                    break
                hits.append(segment.offset_to_vaddr(found))
                cursor = found + 1
            if len(hits) >= limit:
                break
        return hits


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_approved_offline_workspace_path(path: Path) -> bool:
    expanded = path.expanduser()
    resolved = path.resolve()
    return any(
        expanded.is_absolute()
        and is_relative_to(expanded, root)
        and is_relative_to(resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    )


def reject_protected_path(path: Path, label: str, action: str) -> None:
    expanded = path.expanduser()
    for root in PROTECTED_ROOTS:
        if expanded.is_absolute() and is_relative_to(expanded, root) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not {action} protected server root {root}: {expanded}")
    resolved = expanded.resolve()
    for root in PROTECTED_ROOTS:
        if is_relative_to(resolved, root.resolve()) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not {action} protected server root {root}: {resolved}")


def require_ignored_output_path(path: Path, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not is_relative_to(resolved, REPO_ROOT):
        return
    relative = resolved.relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(relative)],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"{label} is inside the repository but is not ignored by Git: {resolved}")


def parse_elf64_load_segments(data: mmap.mmap) -> list[LoadSegment]:
    if data[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ValueError("only little-endian ELF64 core files are supported")

    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]

    segments: list[LoadSegment] = []
    for index in range(e_phnum):
        offset = e_phoff + index * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", data, offset
        )
        if p_type != PT_LOAD or p_filesz == 0:
            continue
        segments.append(
            LoadSegment(
                offset=p_offset,
                vaddr=p_vaddr,
                filesz=p_filesz,
                memsz=p_memsz,
                flags=p_flags,
            )
        )
    return segments


def parse_index(value: str) -> tuple[str, int]:
    if "=" in value:
        label, raw_index = value.split("=", 1)
        label = label.strip()
        if not label:
            raise argparse.ArgumentTypeError("index label must not be empty")
        return label, int(raw_index, 0)
    index = int(value, 0)
    return f"fname_{index}", index


def parse_address(value: str) -> int:
    parsed = int(value, 0)
    if parsed < 0:
        raise argparse.ArgumentTypeError("address must be non-negative")
    return parsed


def plausible_count(value: int | None, low: int, high: int) -> bool:
    return value is not None and low <= value <= high


def validate_index(memory: CoreMemory, table: int, label: str, index: int) -> dict[str, object]:
    chunk_index = index // FNAME_CHUNK_SIZE
    entry_index = index % FNAME_CHUNK_SIZE
    chunk = memory.read_ptr(table + chunk_index * 8)
    entry = memory.read_ptr(chunk + entry_index * 8) if chunk else None
    header = memory.read_u32(entry) if entry else None
    name = memory.read_c_string(entry + 0x10) if entry else None
    expected_header = index * 2
    return {
        "label": label,
        "index": index,
        "chunk": f"0x{chunk:x}" if chunk else None,
        "entry": f"0x{entry:x}" if entry else None,
        "header": f"0x{header:x}" if header is not None else None,
        "expected_header": f"0x{expected_header:x}",
        "header_index_ok": header == expected_header,
        "name_matches_label": name == label,
        "name": name,
    }


def validate_sha256(value: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit("--ark-binary-sha256 must be a lowercase SHA256 hex string")
    return value


def exact_manifest_names(candidate: dict[str, object], evidence: str) -> list[dict[str, object]]:
    names: list[dict[str, object]] = []
    for item in candidate.get("resolved_indices", []):
        if not isinstance(item, dict):
            continue
        if item.get("label") == "None" and item.get("index") == 0:
            continue
        if item.get("header_index_ok") is True and item.get("name_matches_label") is True:
            names.append(
                {
                    "name": item["label"],
                    "index": item["index"],
                    "number": 0,
                    "evidence": evidence,
                }
            )
    return names


def candidate_manifest_readiness(candidates: list[dict[str, object]], evidence: str) -> dict[str, object]:
    ready = [
        {
            "candidate_index": index,
            "table": candidate["table"],
            "name_count": len(exact_manifest_names(candidate, evidence)),
        }
        for index, candidate in enumerate(candidates)
        if exact_manifest_names(candidate, evidence)
    ]
    blockers = []
    if not ready:
        blockers.append("no_exact_name_matches")
    if len(ready) > 1:
        blockers.append("ambiguous_ready_candidates")
    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "ready_candidates": ready,
    }


def build_candidate_manifest(
    candidate: dict[str, object],
    *,
    ark_binary_sha256: str,
    evidence: str,
    source: str = "offline_core_fname_table_scan",
) -> dict[str, object]:
    names = exact_manifest_names(candidate, evidence)
    if not names:
        raise SystemExit("candidate manifest requires at least one exact FName match")
    return {
        "schema": MANIFEST_SCHEMA,
        "ark_binary_sha256": validate_sha256(ark_binary_sha256),
        "source": source,
        "evidence_status": "candidate-only",
        "promotion_evidence": None,
        "names": names,
    }


def validate_root_slot(memory: CoreMemory, root_slot: int, indices: list[tuple[str, int]]) -> dict[str, object]:
    table = memory.read_ptr(root_slot)
    candidate: dict[str, object] = {
        "root_slot": f"0x{root_slot:x}",
        "table": f"0x{table:x}" if table else None,
        "num_elements": None,
        "num_chunks": None,
        "num_elements_plausible": False,
        "num_chunks_plausible": False,
        "header_index_ok": 0,
        "name_matches": 0,
        "resolved_indices": [],
    }
    if not table:
        return candidate

    num_elements = memory.read_u32(table + 0x800)
    num_chunks = memory.read_u32(table + 0x804)
    resolved = [validate_index(memory, table, label, index) for label, index in indices]
    candidate.update(
        {
            "num_elements": num_elements,
            "num_chunks": num_chunks,
            "num_elements_plausible": plausible_count(num_elements, 1, 10_000_000),
            "num_chunks_plausible": plausible_count(num_chunks, 1, 4096),
            "header_index_ok": sum(1 for item in resolved if item["header_index_ok"]),
            "name_matches": sum(1 for item in resolved if item["name_matches_label"]),
            "resolved_indices": resolved,
        }
    )
    return candidate


def root_validation_readiness(candidate: dict[str, object], indices: list[tuple[str, int]]) -> dict[str, object]:
    blockers: list[str] = []
    failed_indices: list[dict[str, object]] = []
    if not indices:
        blockers.append("no_requested_indices")
    if candidate.get("table") is None:
        blockers.append("root_slot_unreadable_or_null")
    if candidate.get("table") is not None and candidate.get("num_elements_plausible") is not True:
        blockers.append("implausible_num_elements")
    if candidate.get("table") is not None and candidate.get("num_chunks_plausible") is not True:
        blockers.append("implausible_num_chunks")

    for item in candidate.get("resolved_indices", []):
        if not isinstance(item, dict):
            continue
        if item.get("header_index_ok") is True and item.get("name_matches_label") is True:
            continue
        failed_indices.append(
            {
                "label": item.get("label"),
                "index": item.get("index"),
                "header_index_ok": item.get("header_index_ok"),
                "name_matches_label": item.get("name_matches_label"),
                "name": item.get("name"),
            }
        )
    if failed_indices:
        blockers.append("requested_index_mismatch")

    requested_count = len(indices)
    exact_match_count = sum(
        1
        for item in candidate.get("resolved_indices", [])
        if isinstance(item, dict)
        and item.get("header_index_ok") is True
        and item.get("name_matches_label") is True
    )
    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "requested_count": requested_count,
        "exact_match_count": exact_match_count,
        "failed_indices": failed_indices,
    }


def scan_fname_tables(
    memory: CoreMemory,
    indices: list[tuple[str, int]],
    max_none_hits: int,
    max_pointer_hits: int,
) -> list[dict[str, object]]:
    table_candidates: dict[int, dict[str, object]] = {}
    none_hits = memory.iter_find(b"None\x00", max_none_hits)
    for none_string in none_hits:
        entry0 = none_string - 0x10
        entry0_data = memory.read(entry0, 0x18)
        if entry0_data is None:
            continue

        entry0_ptr = struct.pack("<Q", entry0)
        chunk_hits = memory.iter_find(entry0_ptr, max_pointer_hits)
        for chunk0 in chunk_hits:
            chunk0_ptr = struct.pack("<Q", chunk0)
            table_hits = memory.iter_find(chunk0_ptr, max_pointer_hits)
            for table in table_hits:
                num_elements = memory.read_u32(table + 0x800)
                num_chunks = memory.read_u32(table + 0x804)
                if not plausible_count(num_elements, 1, 10_000_000):
                    continue
                if not plausible_count(num_chunks, 1, 4096):
                    continue

                resolved = [validate_index(memory, table, label, index) for label, index in indices]
                header_ok = sum(1 for item in resolved if item["header_index_ok"])
                name_matches = sum(1 for item in resolved if item["name_matches_label"])
                has_none_clue = any(label == "None" and index == 0 for label, index in indices)
                none_ok = any(
                    item["label"] == "None"
                    and item["index"] == 0
                    and item["header_index_ok"]
                    and item["name"] == "None"
                    for item in resolved
                )
                if header_ok == 0:
                    continue
                if has_none_clue and not none_ok:
                    continue

                table_candidates.setdefault(
                    table,
                    {
                        "table": f"0x{table:x}",
                        "chunk0": f"0x{chunk0:x}",
                        "entry0": f"0x{entry0:x}",
                        "none_string": f"0x{none_string:x}",
                        "num_elements": num_elements,
                        "num_chunks": num_chunks,
                        "header_index_ok": header_ok,
                        "name_matches": name_matches,
                        "resolved_indices": resolved,
                    },
                )

    return sorted(
        table_candidates.values(),
        key=lambda item: (
            -int(item["header_index_ok"]),
            -int(item["name_matches"]),
            -int(item["num_elements"]),
            item["table"],
        ),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Offline scan of an ELF core file for legacy UE4 FName table candidates."
    )
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing ELF core dump.")
    parser.add_argument(
        "--index",
        action="append",
        type=parse_index,
        default=[],
        metavar="LABEL=INDEX",
        help="FName index to resolve for each candidate. Defaults to known Obelisk clues.",
    )
    parser.add_argument(
        "--no-default-indices",
        action="store_true",
        help="Do not use built-in FName clues when no --index values are supplied.",
    )
    parser.add_argument("--max-none-hits", type=int, default=256)
    parser.add_argument("--max-pointer-hits", type=int, default=2048)
    parser.add_argument(
        "--root-slot",
        type=parse_address,
        help=(
            "Validate a known FName root pointer slot directly instead of scanning the "
            "core for table-shaped candidates."
        ),
    )
    parser.add_argument(
        "--require-exact-root",
        action="store_true",
        help=(
            "With --root-slot, exit non-zero unless all requested indices resolve with "
            "matching headers and labels."
        ),
    )
    parser.add_argument("--ark-binary-sha256", help="Target ShooterGameServer SHA256 for candidate manifest output.")
    parser.add_argument("--manifest-out", type=Path, help="Write a candidate-only FName index manifest.")
    parser.add_argument(
        "--manifest-evidence",
        default="offline_core_fname_table_scan",
        help="Evidence label/path stored on candidate-only manifest entries.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--json-out", type=Path, help="Write the JSON payload to this offline path.")
    return parser.parse_args(argv)


def main_from_args(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    reject_protected_path(args.core, "--core", "read from")
    if args.manifest_out:
        reject_protected_path(args.manifest_out, "--manifest-out", "write under")
        require_ignored_output_path(args.manifest_out, "--manifest-out")
    if args.json_out:
        reject_protected_path(args.json_out, "--json-out", "write under")
        require_ignored_output_path(args.json_out, "--json-out")
    indices = args.index if (args.index or args.no_default_indices) else DEFAULT_INDICES
    memory = CoreMemory(args.core)
    try:
        if args.root_slot is None:
            candidates = scan_fname_tables(
                memory,
                indices=indices,
                max_none_hits=args.max_none_hits,
                max_pointer_hits=args.max_pointer_hits,
            )
            root_validation = None
        else:
            root_validation = validate_root_slot(memory, args.root_slot, indices)
            candidates = [root_validation]
    finally:
        memory.close()

    readiness = (
        candidate_manifest_readiness(candidates, args.manifest_evidence)
        if args.root_slot is None
        else root_validation_readiness(candidates[0], indices)
    )
    candidate_manifest = None
    if args.manifest_out:
        if not args.ark_binary_sha256:
            raise SystemExit("--manifest-out requires --ark-binary-sha256")
        if readiness["ready"]:
            ready_index = (
                readiness["ready_candidates"][0]["candidate_index"]
                if args.root_slot is None
                else 0
            )
            candidate_manifest = build_candidate_manifest(
                candidates[ready_index],
                ark_binary_sha256=args.ark_binary_sha256,
                evidence=args.manifest_evidence,
                source=(
                    "offline_core_fname_table_scan"
                    if args.root_slot is None
                    else "offline_core_fname_root_validation"
                ),
            )
            args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
            args.manifest_out.write_text(
                json.dumps(candidate_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    payload = {
        "schema": SCAN_SCHEMA if args.root_slot is None else ROOT_VALIDATION_SCHEMA,
        "core": str(args.core),
        "requested_indices": [
            {"label": label, "index": index}
            for label, index in indices
        ],
        "candidates": candidates if args.root_slot is None else [],
        "root_validation": root_validation,
        "manifest_readiness": readiness,
        "candidate_manifest": {
            "path": str(args.manifest_out) if candidate_manifest else None,
            "schema": MANIFEST_SCHEMA if candidate_manifest else None,
            "evidence_status": "candidate-only" if candidate_manifest else None,
            "name_count": len(candidate_manifest["names"]) if candidate_manifest else 0,
        },
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        if args.root_slot is not None:
            print(
                "root_slot={root_slot} table={table} num_elements={num_elements} "
                "num_chunks={num_chunks} ready={ready}".format(
                    ready=readiness["ready"],
                    **root_validation,
                )
            )
            for resolved in root_validation["resolved_indices"]:
                print(
                    "  idx={index} label={label} entry={entry} header={header} "
                    "header_ok={header_index_ok} name_match={name_matches_label} "
                    "name={name!r}".format(**resolved)
                )
        elif not candidates:
            print("No FName table candidates found.")
        for candidate in [] if args.root_slot is not None else candidates:
            print(
                "table={table} chunk0={chunk0} entry0={entry0} "
                "num_elements={num_elements} num_chunks={num_chunks} "
                "header_index_ok={header_index_ok} name_matches={name_matches}".format(**candidate)
            )
            for resolved in candidate["resolved_indices"]:
                print(
                    "  idx={index} label={label} entry={entry} header={header} "
                    "header_ok={header_index_ok} name_match={name_matches_label} "
                    "name={name!r}".format(**resolved)
                )
    if args.require_exact_root and args.root_slot is None:
        raise SystemExit("--require-exact-root requires --root-slot")
    if args.require_exact_root and readiness["ready"] is not True:
        blockers = ", ".join(str(item) for item in readiness["blockers"])
        raise SystemExit(f"FName root validation failed: {blockers}")
    return 0


def main() -> int:
    return main_from_args()


if __name__ == "__main__":
    raise SystemExit(main())
