#!/usr/bin/env python3
"""Rediscover candidate native UFunction registration clues from an offline ELF."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import reflection_target_sets  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path, reject_symlink_component  # noqa: E402


SCHEMA = "obelisk.native-ufunction-registration-static-discovery.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
HEX_INPUT_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{6,}$")


class DiscoveryError(Exception):
    pass


class Segment:
    def __init__(self, *, offset: int, vaddr: int, filesz: int, memsz: int, flags: int) -> None:
        self.offset = offset
        self.vaddr = vaddr
        self.filesz = filesz
        self.memsz = memsz
        self.flags = flags

    def contains_file_vma(self, vma: int, size: int = 1) -> bool:
        return self.vaddr <= vma and vma + size <= self.vaddr + self.filesz

    def file_offset_for(self, vma: int) -> int:
        return self.offset + (vma - self.vaddr)

    @property
    def is_rx(self) -> bool:
        return (self.flags & 0x1) != 0 and (self.flags & 0x4) != 0

    @property
    def is_readable(self) -> bool:
        return (self.flags & 0x4) != 0

    def to_json(self) -> dict[str, Any]:
        return {
            "offset": hex(self.offset),
            "vaddr": hex(self.vaddr),
            "filesz": hex(self.filesz),
            "memsz": hex(self.memsz),
            "flags": hex(self.flags),
            "rx": self.is_rx,
            "readable": self.is_readable,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def parse_elf_load_segments(data: bytes) -> list[Segment]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise DiscoveryError("elf_magic_invalid")
    if data[4] != 2:
        raise DiscoveryError("elf_class_not_64_bit")
    if data[5] != 1:
        raise DiscoveryError("elf_not_little_endian")
    try:
        (
            e_type,
            e_machine,
            _e_version,
            _entry,
            phoff,
            _shoff,
            _flags,
            _ehsize,
            phentsize,
            phnum,
            _shentsize,
            _shnum,
            _shstrndx,
        ) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    except struct.error as exc:
        raise DiscoveryError(f"elf_header_truncated:{exc}") from exc
    if e_type not in {2, 3}:
        raise DiscoveryError(f"elf_type_not_executable_or_shared:{e_type}")
    if e_machine != 62:
        raise DiscoveryError(f"elf_machine_not_x86_64:{e_machine}")
    if phentsize < 56:
        raise DiscoveryError(f"elf_program_header_entry_too_small:{phentsize}")

    segments: list[Segment] = []
    for index in range(phnum):
        header_offset = phoff + index * phentsize
        if header_offset + 56 > len(data):
            raise DiscoveryError(f"elf_program_header_truncated:{index}")
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", data, header_offset
        )
        if p_type == 1:
            segments.append(Segment(offset=p_offset, vaddr=p_vaddr, filesz=p_filesz, memsz=p_memsz, flags=p_flags))
    if not segments:
        raise DiscoveryError("elf_load_segments_missing")
    return segments


def segment_for_file_offset(segments: list[Segment], offset: int, size: int = 1) -> Segment | None:
    for segment in segments:
        if segment.offset <= offset and offset + size <= segment.offset + segment.filesz:
            return segment
    return None


def segment_for_vma(segments: list[Segment], vma: int, size: int = 1) -> Segment | None:
    for segment in segments:
        if segment.contains_file_vma(vma, size):
            return segment
    return None


def file_offset_to_vma(segments: list[Segment], offset: int, size: int = 1) -> int | None:
    segment = segment_for_file_offset(segments, offset, size)
    if segment is None:
        return None
    return segment.vaddr + (offset - segment.offset)


def find_all(data: bytes, needle: bytes) -> list[int]:
    results: list[int] = []
    start = 0
    while True:
        index = data.find(needle, start)
        if index < 0:
            return results
        results.append(index)
        start = index + 1


def find_string_hits(data: bytes, segments: list[Segment], name: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    encodings = {
        "ascii": name.encode("ascii") + b"\x00",
        "utf32le": name.encode("utf-32-le") + b"\x00\x00\x00\x00",
    }
    for encoding, needle in encodings.items():
        for offset in find_all(data, needle):
            vma = file_offset_to_vma(segments, offset, len(needle))
            segment = segment_for_file_offset(segments, offset, len(needle))
            if vma is None or segment is None:
                continue
            hits.append(
                {
                    "encoding": encoding,
                    "vma": hex(vma),
                    "file_offset": hex(offset),
                    "readable_segment": segment.is_readable,
                    "rx_segment": segment.is_rx,
                }
            )
    return hits


def imm32_bytes(vma: int) -> bytes | None:
    if not 0 <= vma <= 0xFFFFFFFF:
        return None
    return struct.pack("<I", vma)


def call_target_from(data: bytes, call_file_offset: int, call_vma: int) -> int | None:
    if call_file_offset < 0 or call_file_offset + 5 > len(data) or data[call_file_offset] != 0xE8:
        return None
    rel32 = struct.unpack_from("<i", data, call_file_offset + 1)[0]
    return call_vma + 5 + rel32


def read_vma(data: bytes, segments: list[Segment], vma: int, size: int) -> bytes | None:
    segment = segment_for_vma(segments, vma, size)
    if segment is None:
        return None
    file_offset = segment.file_offset_for(vma)
    if file_offset + size > len(data):
        return None
    return data[file_offset : file_offset + size]


def looks_like_x86_64_code(raw: bytes | None) -> bool:
    if not raw:
        return False
    first = raw[0]
    return first in {
        0x40,
        0x41,
        0x48,
        0x49,
        0x53,
        0x55,
        0x56,
        0x57,
        0xE9,
        0xEB,
    }


def find_registration_candidates(
    data: bytes,
    segments: list[Segment],
    name_vma: int,
    *,
    source_hit: dict[str, Any],
) -> list[dict[str, Any]]:
    needle = imm32_bytes(name_vma)
    if needle is None:
        return []
    candidates: list[dict[str, Any]] = []
    for offset in find_all(data, needle):
        xref_vma = file_offset_to_vma(segments, offset, 4)
        xref_segment = segment_for_file_offset(segments, offset, 4)
        if xref_vma is None or xref_segment is None or not xref_segment.is_rx:
            continue
        search_start = max(xref_segment.offset, offset - 8)
        search_end = min(xref_segment.offset + xref_segment.filesz, offset + 48)
        window = data[search_start:search_end]
        local_name_offset = offset - search_start
        thunk_vma: int | None = None
        thunk_opcode_offset: int | None = None
        for index in range(local_name_offset + 4, min(len(window) - 5, local_name_offset + 24)):
            if window[index] in {0xBA, 0xBE, 0xBF}:
                possible = struct.unpack_from("<I", window, index + 1)[0]
                segment = segment_for_vma(segments, possible, 1)
                if segment is not None and segment.is_rx:
                    thunk_vma = possible
                    thunk_opcode_offset = search_start + index
                    break
        if thunk_vma is None or thunk_opcode_offset is None:
            candidates.append({"xref_vma": hex(xref_vma), "status": "blocked", "reason": "thunk_immediate_not_found"})
            continue

        registrar_call_vma = None
        registrar_target_vma = None
        for index in range(thunk_opcode_offset + 5, min(search_start + len(window) - 4, thunk_opcode_offset + 32)):
            call_vma = file_offset_to_vma(segments, index, 5)
            if call_vma is None:
                continue
            target = call_target_from(data, index, call_vma)
            if target is not None:
                registrar_call_vma = call_vma
                registrar_target_vma = target
                break
        candidates.append(
            {
                "xref_vma": hex(xref_vma),
                "status": "candidate",
                "source_string_hit": {
                    "encoding": source_hit["encoding"],
                    "vma": source_hit["vma"],
                    "file_offset": source_hit["file_offset"],
                },
                "registration_window_vma": hex(file_offset_to_vma(segments, search_start, 1) or xref_vma),
                "name_immediate_vma": hex(xref_vma),
                "thunk_vma": hex(thunk_vma),
                "thunk_segment_rx": True,
                "thunk_prefix_hex": (read_vma(data, segments, thunk_vma, 16) or b"").hex(),
                "thunk_prefix_code_like": looks_like_x86_64_code(read_vma(data, segments, thunk_vma, 16)),
                "registrar_call_vma": hex(registrar_call_vma) if registrar_call_vma is not None else None,
                "registrar_target_vma": hex(registrar_target_vma) if registrar_target_vma is not None else None,
            }
        )
    return candidates


def select_best_candidate(
    candidates: list[dict[str, Any]],
    registrar_cluster_sizes: dict[str, int],
) -> dict[str, Any] | None:
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for index, candidate in enumerate(candidates):
        if candidate.get("status") != "candidate":
            continue
        registrar = candidate.get("registrar_target_vma")
        cluster_size = registrar_cluster_sizes.get(registrar, 0) if isinstance(registrar, str) else 0
        score = 0
        reasons: list[str] = []
        if candidate.get("thunk_prefix_code_like") is True:
            score += 100
            reasons.append("thunk_prefix_code_like")
        if cluster_size > 1:
            score += 20 + cluster_size
            reasons.append("registrar_shared_across_targets")
        if candidate.get("registrar_call_vma"):
            score += 5
            reasons.append("has_registrar_call")
        scored_candidate = dict(candidate)
        scored_candidate["selection_score"] = score
        scored_candidate["selection_reasons"] = reasons
        scored_candidate["registrar_cluster_size"] = cluster_size
        scored.append((score, -index, scored_candidate))
    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][2]


def reject_address_like_target(value: str) -> None:
    if HEX_INPUT_RE.fullmatch(value.strip()) is not None:
        raise SystemExit(f"targets must be names, not addresses: {value}")


def expand_targets(targets: list[str], target_sets: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for target in targets:
        reject_address_like_target(target)
        if "." not in target:
            raise SystemExit(f"--target must be a qualified UFunction name: {target}")
        if target not in seen:
            seen.add(target)
            expanded.append(target)
    for target_set in target_sets:
        try:
            members = reflection_target_sets.schema_target_list(target_set, "obelisk.ufunction-chain.snapshot.v1")
        except KeyError as exc:
            raise SystemExit(f"unknown --target-set: {target_set}") from exc
        for target in members:
            reject_address_like_target(target)
            if target not in seen:
                seen.add(target)
                expanded.append(target)
    if not expanded:
        raise SystemExit("pass at least one --target or --target-set")
    return expanded


def safe_run_id(value: str) -> str:
    if SAFE_RUN_ID_RE.fullmatch(value) is None or ".." in value:
        raise SystemExit(f"--run-id contains unsafe characters: {value}")
    return value


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    original_binary = args.binary
    reject_symlink_component(original_binary, "--binary")
    binary = reject_protected_input_path(original_binary, "--binary")
    if not binary.is_file():
        raise SystemExit(f"--binary must be a file: {binary}")
    observed_sha = sha256_file(binary)
    targets = expand_targets(args.target, args.target_set)
    blockers: list[dict[str, Any]] = []
    if args.expected_binary_sha256 and observed_sha != args.expected_binary_sha256:
        blockers.append(
            {
                "reason": "binary_sha256_mismatch",
                "expected": args.expected_binary_sha256,
                "observed": observed_sha,
            }
        )
    data = binary.read_bytes()
    try:
        segments = parse_elf_load_segments(data)
    except DiscoveryError as exc:
        segments = []
        blockers.append({"reason": str(exc)})

    target_reports: list[dict[str, Any]] = []
    registrar_clusters: dict[str, list[str]] = {}
    pending_target_reports: list[dict[str, Any]] = []
    for target in targets:
        short_name = target.rsplit(".", 1)[-1]
        string_hits = find_string_hits(data, segments, short_name) if segments else []
        for hit in string_hits:
            hit["used_for_registration_candidates"] = hit.get("encoding") == "ascii"
        readable_hits = [hit for hit in string_hits if hit["readable_segment"]]
        registration_candidates: list[dict[str, Any]] = []
        registration_source_hits = [hit for hit in readable_hits if hit.get("encoding") == "ascii"]
        for hit in registration_source_hits:
            registration_candidates.extend(
                find_registration_candidates(
                    data,
                    segments,
                    int(hit["vma"], 16),
                    source_hit=hit,
                )
            )
        candidate_targets = {
            candidate.get("registrar_target_vma")
            for candidate in registration_candidates
            if candidate.get("status") == "candidate" and candidate.get("registrar_target_vma")
        }
        for registrar in sorted(candidate_targets):
            registrar_clusters.setdefault(str(registrar), []).append(target)
        target_blockers = []
        if not readable_hits:
            target_blockers.append({"reason": "target_name_string_not_found"})
        if readable_hits and not registration_source_hits:
            target_blockers.append({"reason": "ascii_target_name_string_not_found"})
        if readable_hits and not any(candidate.get("status") == "candidate" for candidate in registration_candidates):
            target_blockers.append({"reason": "registration_candidate_not_found"})
        pending_target_reports.append(
            {
                "target": target,
                "short_name": short_name,
                "string_hits": string_hits,
                "registration_candidates": registration_candidates,
                "blockers": target_blockers,
                "status": "candidate" if not target_blockers else "blocked",
            }
        )

    registrar_cluster_sizes = {registrar: len(set(cluster_targets)) for registrar, cluster_targets in registrar_clusters.items()}
    for target_report in pending_target_reports:
        selected = select_best_candidate(target_report["registration_candidates"], registrar_cluster_sizes)
        if selected is None and target_report["status"] == "candidate":
            target_report["blockers"].append({"reason": "selected_registration_candidate_missing"})
            target_report["status"] = "blocked"
        target_report["selected_candidate"] = selected
        target_reports.append(target_report)

    if any(target["status"] == "blocked" for target in target_reports):
        blockers.append({"reason": "one_or_more_targets_blocked"})
    if not registrar_clusters:
        blockers.append({"reason": "registrar_cluster_not_inferred"})

    material_identity = {
        "artifact_kind": SCHEMA,
        "capture_id": args.run_id,
        "evidence_pack_id": f"native-ufunction-registration-static-discovery-{args.run_id}",
    }
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "artifact_status": "static_orientation_candidate_only",
        "artifact_gate_eligible": False,
        "consume_mode_allowed": False,
        "promote_mode_allowed": False,
        "status": "candidate" if not blockers else "blocked",
        "accepted_for_orientation": not blockers,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "identity_ready": False,
        "lookup_ready": False,
        "mutation_ready": False,
        "return_override_ready": False,
        "callable_process_event_contract": False,
        "not_artifact_gate": True,
        "generated_at": utc_now(),
        "binary": {"path": str(binary), "sha256": observed_sha},
        "expected_binary_sha256": args.expected_binary_sha256,
        "inputs": {"target_names": args.target, "target_sets": args.target_set, "input_addresses": []},
        "preplan_scope": {
            "target_set": "players-identity-lifecycle-intake"
            if "players-identity-lifecycle-intake" in args.target_set
            or {
                "ShooterPlayerController.ServerListPlayers",
                "ShooterPlayerController.ServerKickPlayer",
            }.issubset(set(targets))
            else None,
            "focal_targets": [
                target
                for target in targets
                if target
                in {
                    "ShooterPlayerController.ServerListPlayers",
                    "ShooterPlayerController.ServerKickPlayer",
                }
            ],
            "requires_full_12_target_inventory": True,
            "downstream_blockers": [
                "requires_non_protected_core_evidence_pack",
                "requires_reflection_inventory_pack",
                "requires_focal_snapshots",
                "requires_privacy_invalidation_policy",
            ],
        },
        "load_segments": [segment.to_json() for segment in segments],
        "targets": target_reports,
        "registrar_clusters": [
            {"registrar_target_vma": registrar, "targets": sorted(cluster_targets)}
            for registrar, cluster_targets in sorted(registrar_clusters.items())
        ],
        "blockers": blockers,
        "non_claims": [
            "static registration discovery is navigation evidence only",
            "does_not_promote_public_sdk",
            "does_not_promote_ufunction_abi",
            "does_not_promote_runtime_hook",
            "does_not_promote_identity_lookup_mutation_or_return_override",
            "does_not_promote_callable_process_event_contract",
            "does not prove UFunction object identity, UProperty chains, ParmsSize, or parameter offsets",
            "does not promote player identity, permissions, commands, mutation, return override, or raw UE pointer access",
            "does not replace core evidence packs, reflection inventory packs, sanitized focal snapshots, or runtime validation",
        ],
    }
    report["output_artifact_identity"] = {
        **material_identity,
        "artifact_sha256": hashlib.sha256(
            canonical_json_bytes({"artifact_identity": material_identity, "report": report})
        ).hexdigest(),
    }
    return report


def write_report(report: dict[str, Any], args: argparse.Namespace) -> Path | None:
    if args.output_root is None:
        return None
    reject_symlink_component(args.output_root, "--output-root")
    output_root = reject_protected_output_path(args.output_root, "--output-root")
    output_root.mkdir(parents=True, exist_ok=True)
    reject_symlink_component(output_root, "--output-root")
    path = output_root / "manifest.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY)
    parser.add_argument("--expected-binary-sha256", default=EXPECTED_BINARY_SHA256)
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--target-set", action="append", default=[])
    parser.add_argument("--run-id", default=utc_now().replace(":", "").replace("-", ""))
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    args.run_id = safe_run_id(args.run_id)
    return args


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    report = build_report(args)
    manifest_path = write_report(report, args)
    if manifest_path is not None:
        report["manifest_path"] = str(manifest_path)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "candidate" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
