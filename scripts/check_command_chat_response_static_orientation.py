#!/usr/bin/env python3
"""Validate command/chat response-path static orientation without promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component
from static_candidate_orientation_contract import build_contract, validate_contract


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
REPORT_SCHEMA = "obelisk.command-chat-response-static-orientation-check.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
PLANNING_SURFACE = "obelisk.command_chat_response_path.v1"
CANDIDATE_EVIDENCE_STATUS = "candidate_only_static_orientation"
REGISTRAR_CALL_VMA = 0x1CCC140
CONTROLLER_CLASS_SLOT_VMA = 0x58EEBF0
PUBLIC_ABI_STATUS = "blocked_pending_identity_permission_and_copied_response_contracts"
PUBLIC_ABI_FALSE_FIELDS = (
    "public_command_api",
    "public_reply_api",
    "public_send_chat_api",
    "runtime_command_router",
    "player_identity_contract",
    "permission_admin_contract",
    "copied_response_contract",
    "raw_ue_pointer_or_fstring_exposure",
)
REQUIRED_PROMOTION_BLOCKERS = (
    "player_identity_contract_not_promoted",
    "permission_admin_contract_not_promoted",
    "copied_response_contract_not_promoted",
    "public_command_reply_send_chat_api_not_promoted",
    "static_orientation_not_registered_artifact_gate",
)
CONTRACT_TOPIC = "command_chat_response_path"
REQUIRED_CONTRACT_BLOCKERS = (
    "requires_non_protected_core_evidence_pack",
    "requires_reflection_inventory_or_focal_snapshots_for_response_path_targets",
    "requires_command_router_identity_and_permission_contracts_before_command_replies",
    "requires_copied_data_response_contract_before_public_sdk_promotion",
)


@dataclass(frozen=True)
class LoadSegment:
    offset: int
    vaddr: int
    filesz: int
    memsz: int
    flags: int

    def contains_file_vma(self, vma: int, size: int = 1) -> bool:
        return self.vaddr <= vma and vma + size <= self.vaddr + self.filesz

    def contains_mem_vma(self, vma: int, size: int = 1) -> bool:
        return self.vaddr <= vma and vma + size <= self.vaddr + self.memsz

    def file_offset_for(self, vma: int) -> int:
        return self.offset + (vma - self.vaddr)

    @property
    def is_rx(self) -> bool:
        return (self.flags & 0x1) != 0 and (self.flags & 0x4) != 0

    @property
    def is_readable(self) -> bool:
        return (self.flags & 0x4) != 0

    @property
    def is_rw(self) -> bool:
        return (self.flags & 0x2) != 0 and (self.flags & 0x4) != 0


@dataclass(frozen=True)
class Section:
    name: str
    vaddr: int
    offset: int
    size: int
    flags: int
    section_type: int

    def bytes_from(self, data: bytes) -> bytes:
        return data[self.offset : self.offset + self.size]


@dataclass(frozen=True)
class ResponsePathTarget:
    target: str
    ascii_name: str
    expected_ascii_file_offset: int
    expected_ascii_vma: int
    expected_registration_vma: int
    expected_class_load_vma: int
    expected_thunk_vma: int
    expected_thunk_prefix: bytes


RESPONSE_PATH_TARGETS = (
    ResponsePathTarget(
        target="ShooterPlayerController.ClientChatMessage",
        ascii_name="ClientChatMessage",
        expected_ascii_file_offset=0x3D61A92,
        expected_ascii_vma=0x4161A92,
        expected_registration_vma=0x1364ED9,
        expected_class_load_vma=0x1364ED2,
        expected_thunk_vma=0x153B820,
        expected_thunk_prefix=bytes.fromhex("554889e54156534881ec20010000"),
    ),
    ResponsePathTarget(
        target="ShooterPlayerController.ClientServerChatDirectMessage",
        ascii_name="ClientServerChatDirectMessage",
        expected_ascii_file_offset=0x3D622D1,
        expected_ascii_vma=0x41622D1,
        expected_registration_vma=0x136603E,
        expected_class_load_vma=0x1366037,
        expected_thunk_vma=0x153F880,
        expected_thunk_prefix=bytes.fromhex("554889e54156534883ec30"),
    ),
    ResponsePathTarget(
        target="ShooterPlayerController.ClientServerChatMessage",
        ascii_name="ClientServerChatMessage",
        expected_ascii_file_offset=0x3D622EF,
        expected_ascii_vma=0x41622EF,
        expected_registration_vma=0x136607B,
        expected_class_load_vma=0x1366074,
        expected_thunk_vma=0x153F9C0,
        expected_thunk_prefix=bytes.fromhex("554889e54156534883ec30"),
    ),
)
EXPECTED_TARGET_NAMES = tuple(target.target for target in RESPONSE_PATH_TARGETS)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Candidate-only static orientation checker for command/chat response-path "
            "targets in an offline ShooterGameServer binary."
        )
    )
    parser.add_argument(
        "binary",
        nargs="?",
        type=Path,
        default=DEFAULT_BINARY,
        help="Offline ShooterGameServer path.",
    )
    parser.add_argument(
        "--expected-binary-sha256",
        default=EXPECTED_BINARY_SHA256,
        help="Expected SHA256 for the offline binary.",
    )
    parser.add_argument("--json", action="store_true", help="Compatibility flag; output is always JSON.")
    return parser.parse_args()


def append_blocker(blockers: list[dict[str, Any]], reason: str, **details: Any) -> None:
    blockers.append({"reason": reason, **details})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_elf(data: bytes, blockers: list[dict[str, Any]]) -> tuple[list[LoadSegment], dict[str, Section]]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        append_blocker(blockers, "elf_magic_invalid")
        return [], {}
    if data[4] != 2:
        append_blocker(blockers, "elf_class_not_64_bit", value=data[4])
        return [], {}
    if data[5] != 1:
        append_blocker(blockers, "elf_not_little_endian", value=data[5])
        return [], {}

    try:
        (
            e_type,
            e_machine,
            _e_version,
            entry,
            phoff,
            shoff,
            _flags,
            _ehsize,
            phentsize,
            phnum,
            shentsize,
            shnum,
            shstrndx,
        ) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    except struct.error as exc:
        append_blocker(blockers, "elf_header_truncated", detail=str(exc))
        return [], {}

    if e_type != 2:
        append_blocker(blockers, "elf_type_not_exec", value=e_type)
    if e_machine != 62:
        append_blocker(blockers, "elf_machine_not_x86_64", value=e_machine)
    if entry != 0x81DC59:
        append_blocker(blockers, "elf_entry_mismatch", value=hex(entry))
    if phentsize < 56:
        append_blocker(blockers, "elf_program_header_entry_too_small", value=phentsize)
        return [], {}
    if phoff > len(data) or phnum > (len(data) - phoff) // phentsize:
        append_blocker(blockers, "elf_program_header_table_truncated")
        return [], {}

    segments: list[LoadSegment] = []
    for index in range(phnum):
        header_offset = phoff + index * phentsize
        if header_offset + 56 > len(data):
            append_blocker(blockers, "elf_program_header_truncated", index=index)
            return segments, {}
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", data, header_offset
        )
        if p_type == 1:
            if p_filesz > p_memsz:
                append_blocker(
                    blockers,
                    "elf_load_segment_filesz_exceeds_memsz",
                    index=index,
                    filesz=p_filesz,
                    memsz=p_memsz,
                )
            if p_offset > len(data) or p_filesz > len(data) - p_offset:
                append_blocker(
                    blockers,
                    "elf_load_segment_file_range_out_of_bounds",
                    index=index,
                    offset=p_offset,
                    filesz=p_filesz,
                )
            segments.append(
                LoadSegment(
                    offset=p_offset,
                    vaddr=p_vaddr,
                    filesz=p_filesz,
                    memsz=p_memsz,
                    flags=p_flags,
                )
            )
    if not segments:
        append_blocker(blockers, "elf_load_segments_missing")

    sections: dict[str, Section] = {}
    if shoff == 0 or shnum == 0 or shentsize < 64 or shstrndx >= shnum:
        append_blocker(blockers, "elf_section_headers_unusable")
        return segments, sections
    if shoff > len(data) or shnum > (len(data) - shoff) // shentsize:
        append_blocker(blockers, "elf_section_header_table_truncated")
        return segments, sections

    shstr_header_offset = shoff + shstrndx * shentsize
    if shstr_header_offset + 64 > len(data):
        append_blocker(blockers, "elf_section_name_header_truncated")
        return segments, sections
    (_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, *_rest) = struct.unpack_from(
        "<IIQQQQIIQQ", data, shstr_header_offset
    )
    if sh_type == 8 or sh_offset + sh_size > len(data):
        append_blocker(blockers, "elf_section_name_table_invalid")
        return segments, sections
    shstrtab = data[sh_offset : sh_offset + sh_size]

    for index in range(shnum):
        header_offset = shoff + index * shentsize
        if header_offset + 64 > len(data):
            append_blocker(blockers, "elf_section_header_truncated", index=index)
            return segments, sections
        name_offset, section_type, flags, addr, offset, size, *_rest = struct.unpack_from(
            "<IIQQQQIIQQ", data, header_offset
        )
        if name_offset >= len(shstrtab):
            append_blocker(blockers, "elf_section_name_offset_invalid", index=index)
            continue
        end = shstrtab.find(b"\x00", name_offset)
        if end == -1:
            append_blocker(blockers, "elf_section_name_unterminated", index=index)
            continue
        name = shstrtab[name_offset:end].decode("ascii", errors="replace")
        if section_type != 8 and (offset > len(data) or size > len(data) - offset):
            append_blocker(
                blockers,
                "elf_section_file_range_out_of_bounds",
                index=index,
                section=name,
                offset=offset,
                size=size,
            )
        sections[name] = Section(
            name=name,
            vaddr=addr,
            offset=offset,
            size=size,
            flags=flags,
            section_type=section_type,
        )
    return segments, sections


def segment_for_file_vma(segments: list[LoadSegment], vma: int, size: int = 1) -> LoadSegment | None:
    return next((segment for segment in segments if segment.contains_file_vma(vma, size)), None)


def segment_for_mem_vma(segments: list[LoadSegment], vma: int, size: int = 1) -> LoadSegment | None:
    return next((segment for segment in segments if segment.contains_mem_vma(vma, size)), None)


def read_vma(data: bytes, segments: list[LoadSegment], vma: int, size: int) -> bytes | None:
    segment = segment_for_file_vma(segments, vma, size)
    if segment is None:
        return None
    file_offset = segment.file_offset_for(vma)
    if file_offset + size > len(data):
        return None
    return data[file_offset : file_offset + size]


def call_target(data: bytes, segments: list[LoadSegment], call_vma: int) -> int | None:
    raw = read_vma(data, segments, call_vma, 5)
    if raw is None or raw[0] != 0xE8:
        return None
    rel32 = struct.unpack("<i", raw[1:])[0]
    return call_vma + 5 + rel32


def find_all(haystack: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    offset = haystack.find(needle)
    while offset != -1:
        hits.append(offset)
        offset = haystack.find(needle, offset + 1)
    return hits


def check_section_layout(sections: dict[str, Section], blockers: list[dict[str, Any]]) -> None:
    text = sections.get(".text")
    rodata = sections.get(".rodata")
    if text is None:
        append_blocker(blockers, "text_section_missing")
    elif text.vaddr != 0x648400:
        append_blocker(blockers, "text_section_vma_mismatch", value=hex(text.vaddr))
    if rodata is None:
        append_blocker(blockers, "rodata_section_missing")
    elif rodata.vaddr != 0x3F61740:
        append_blocker(blockers, "rodata_section_vma_mismatch", value=hex(rodata.vaddr))


def check_load_segments(
    segments: list[LoadSegment],
    target: ResponsePathTarget,
    blockers: list[dict[str, Any]],
) -> None:
    for vma in (
        target.expected_class_load_vma,
        target.expected_registration_vma,
        target.expected_thunk_vma,
    ):
        segment = segment_for_file_vma(segments, vma)
        if segment is None or not segment.is_rx:
            append_blocker(blockers, "target_text_vma_not_in_rx_load", target=target.target, vma=hex(vma))
    ascii_segment = segment_for_file_vma(segments, target.expected_ascii_vma, len(target.ascii_name) + 1)
    if ascii_segment is None or not ascii_segment.is_readable:
        append_blocker(
            blockers,
            "target_ascii_name_not_in_readable_load",
            target=target.target,
            vma=hex(target.expected_ascii_vma),
        )
    class_slot_segment = segment_for_mem_vma(segments, CONTROLLER_CLASS_SLOT_VMA, 8)
    if class_slot_segment is None or not class_slot_segment.is_rw:
        append_blocker(
            blockers,
            "controller_class_slot_not_in_rw_load",
            target=target.target,
            vma=hex(CONTROLLER_CLASS_SLOT_VMA),
        )


def discover_ascii_name(
    data: bytes,
    sections: dict[str, Section],
    target: ResponsePathTarget,
    blockers: list[dict[str, Any]],
) -> tuple[int | None, int | None]:
    rodata = sections.get(".rodata")
    if rodata is None:
        return None, None
    needle = target.ascii_name.encode("ascii") + b"\x00"
    rodata_bytes = rodata.bytes_from(data)
    hits = find_all(rodata_bytes, needle)
    if len(hits) != 1:
        append_blocker(
            blockers,
            "target_ascii_name_not_uniquely_discovered",
            target=target.target,
            hit_count=len(hits),
        )
        return None, None
    file_offset = rodata.offset + hits[0]
    vma = rodata.vaddr + hits[0]
    if file_offset != target.expected_ascii_file_offset:
        append_blocker(
            blockers,
            "target_ascii_file_offset_mismatch",
            target=target.target,
            expected=hex(target.expected_ascii_file_offset),
            value=hex(file_offset),
        )
    if vma != target.expected_ascii_vma:
        append_blocker(
            blockers,
            "target_ascii_vma_mismatch",
            target=target.target,
            expected=hex(target.expected_ascii_vma),
            value=hex(vma),
        )
    return file_offset, vma


def check_class_load(
    data: bytes,
    segments: list[LoadSegment],
    target: ResponsePathTarget,
    blockers: list[dict[str, Any]],
) -> int | None:
    raw = read_vma(data, segments, target.expected_class_load_vma, 7)
    if raw is None or raw[:3] != b"\x48\x8b\x3d":
        append_blocker(
            blockers,
            "target_class_load_opcode_mismatch",
            target=target.target,
            vma=hex(target.expected_class_load_vma),
        )
        return None
    disp = struct.unpack("<i", raw[3:])[0]
    resolved = target.expected_class_load_vma + 7 + disp
    if resolved != CONTROLLER_CLASS_SLOT_VMA:
        append_blocker(
            blockers,
            "target_controller_class_slot_mismatch",
            target=target.target,
            expected=hex(CONTROLLER_CLASS_SLOT_VMA),
            value=hex(resolved),
        )
    return resolved


def check_registration_window(
    data: bytes,
    segments: list[LoadSegment],
    target: ResponsePathTarget,
    ascii_vma: int,
    blockers: list[dict[str, Any]],
) -> int | None:
    raw = read_vma(data, segments, target.expected_registration_vma, 17)
    if raw is None:
        append_blocker(blockers, "target_registration_window_unreadable", target=target.target)
        return None
    if raw[0] != 0xBE or struct.unpack("<I", raw[1:5])[0] != ascii_vma:
        append_blocker(
            blockers,
            "target_registration_name_immediate_mismatch",
            target=target.target,
            expected=hex(ascii_vma),
        )
    thunk_vma = struct.unpack("<I", raw[6:10])[0] if raw[5] == 0xBA else None
    if raw[5] != 0xBA or thunk_vma != target.expected_thunk_vma:
        append_blocker(
            blockers,
            "target_registration_thunk_immediate_mismatch",
            target=target.target,
            expected=hex(target.expected_thunk_vma),
            value=hex(thunk_vma) if thunk_vma is not None else None,
        )
    if raw[10:12] != b"\x31\xc9":
        append_blocker(blockers, "target_registration_zero_flags_opcode_mismatch", target=target.target)
    if raw[12] != 0xE8:
        append_blocker(blockers, "target_registration_call_opcode_mismatch", target=target.target)
    elif call_target(data, segments, target.expected_registration_vma + 12) != REGISTRAR_CALL_VMA:
        append_blocker(
            blockers,
            "target_registration_call_target_mismatch",
            target=target.target,
            expected=hex(REGISTRAR_CALL_VMA),
        )
    return thunk_vma


def check_thunk_prefix(
    data: bytes,
    segments: list[LoadSegment],
    target: ResponsePathTarget,
    blockers: list[dict[str, Any]],
) -> None:
    prefix = read_vma(data, segments, target.expected_thunk_vma, len(target.expected_thunk_prefix))
    if prefix != target.expected_thunk_prefix:
        append_blocker(
            blockers,
            "target_thunk_prefix_mismatch",
            target=target.target,
            thunk_vma=hex(target.expected_thunk_vma),
        )


def validate_target(
    data: bytes,
    segments: list[LoadSegment],
    sections: dict[str, Section],
    target: ResponsePathTarget,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    before = len(blockers)
    check_load_segments(segments, target, blockers)
    ascii_file_offset, ascii_vma = discover_ascii_name(data, sections, target, blockers)
    class_slot = check_class_load(data, segments, target, blockers)
    windows: list[int] = []
    thunk_vma: int | None = None
    if ascii_vma is not None:
        thunk_vma = check_registration_window(data, segments, target, ascii_vma, blockers)
        windows = [target.expected_registration_vma]
    check_thunk_prefix(data, segments, target, blockers)
    return {
        "target": target.target,
        "kind": "command_chat_response_path_static_orientation",
        "status": "candidate_orientation_valid" if len(blockers) == before else "blocked",
        "candidate_only": len(blockers) == before,
        "confidence": "candidate",
        "public_abi_ready": False,
        "public_sdk_evidence": "not_public_sdk_evidence",
        "artifact_gate_evidence": "not_artifact_gate_evidence",
        "ascii_name": target.ascii_name,
        "ascii_name_file_offset": hex(ascii_file_offset) if ascii_file_offset is not None else None,
        "ascii_name_vma": hex(ascii_vma) if ascii_vma is not None else None,
        "class_slot_vma": hex(class_slot) if class_slot is not None else None,
        "registration_vmas": [hex(window) for window in windows],
        "expected_registration_vma": hex(target.expected_registration_vma),
        "registrar_call_vma": hex(REGISTRAR_CALL_VMA),
        "thunk_candidates": [hex(thunk_vma)] if thunk_vma is not None else [],
        "bounded_checks": [
            "unique exact ASCII name in .rodata",
            "17-byte local registration window",
            "7-byte controller class-slot load",
            "short native thunk byte prefix",
        ],
    }


def contract_subjects(checked_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "target": target.get("target"),
            "kind": target.get("kind"),
            "status": "candidate_only"
            if target.get("status") == "candidate_orientation_valid"
            else target.get("status"),
            "confidence": target.get("confidence"),
            "public_abi_ready": target.get("public_abi_ready"),
            "public_sdk_evidence": target.get("public_sdk_evidence"),
            "artifact_gate_evidence": target.get("artifact_gate_evidence"),
            "ascii_name_vma": target.get("ascii_name_vma"),
            "class_slot_vma": target.get("class_slot_vma"),
            "registration_vmas": target.get("registration_vmas"),
            "registrar_call_vma": target.get("registrar_call_vma"),
            "thunk_candidates": target.get("thunk_candidates"),
        }
        for target in checked_targets
    ]


def artifact_gate_boundary() -> dict[str, Any]:
    return {
        "status": "not_artifact_gate",
        "registered": False,
        "may_gate_artifacts": False,
        "consume_mode": "candidate_orientation_only",
        "promote_mode": "blocked",
    }


def public_abi_boundary() -> dict[str, Any]:
    boundary: dict[str, Any] = {"status": PUBLIC_ABI_STATUS}
    for field in PUBLIC_ABI_FALSE_FIELDS:
        boundary[field] = False
    return boundary


def validate_report_boundary(report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []

    def add(reason: str, **details: Any) -> None:
        blockers.append({"reason": reason, **details})

    if report.get("schema") != REPORT_SCHEMA:
        add("command_chat_response_schema_invalid", expected=REPORT_SCHEMA, value=report.get("schema"))
    if report.get("candidate_evidence_status") != CANDIDATE_EVIDENCE_STATUS:
        add(
            "command_chat_response_candidate_status_invalid",
            value=report.get("candidate_evidence_status"),
        )
    for field in ("promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready"):
        if report.get(field) is not False:
            add("command_chat_response_readiness_overclaim", field=field, value=report.get(field))
    if report.get("not_artifact_gate") is not True:
        add(
            "command_chat_response_artifact_gate_overclaim",
            field="not_artifact_gate",
            value=report.get("not_artifact_gate"),
        )

    gate = report.get("artifact_gate")
    if not isinstance(gate, dict):
        add("command_chat_response_artifact_gate_boundary_missing")
    else:
        expected_gate = artifact_gate_boundary()
        for field, expected in expected_gate.items():
            if gate.get(field) != expected:
                add(
                    "command_chat_response_artifact_gate_boundary_invalid",
                    field=field,
                    expected=expected,
                    value=gate.get(field),
                )

    public_boundary = report.get("public_abi_boundary")
    if not isinstance(public_boundary, dict):
        add("command_chat_response_public_abi_boundary_missing")
    else:
        if public_boundary.get("status") != PUBLIC_ABI_STATUS:
            add(
                "command_chat_response_public_abi_status_invalid",
                expected=PUBLIC_ABI_STATUS,
                value=public_boundary.get("status"),
            )
        for field in PUBLIC_ABI_FALSE_FIELDS:
            if public_boundary.get(field) is not False:
                add(
                    "command_chat_response_public_abi_overclaim",
                    field=field,
                    value=public_boundary.get(field),
                )

    promotion_blockers = report.get("promotion_blockers")
    if not isinstance(promotion_blockers, list) or not all(isinstance(item, str) for item in promotion_blockers):
        add("command_chat_response_promotion_blockers_invalid")
    else:
        missing = sorted(set(REQUIRED_PROMOTION_BLOCKERS) - set(promotion_blockers))
        if missing:
            add("command_chat_response_required_promotion_blocker_missing", missing=missing)

    contract = report.get("static_candidate_orientation_contract")
    if not isinstance(contract, dict):
        add("command_chat_response_static_contract_missing")
    else:
        for blocker in validate_contract(contract):
            add(
                "command_chat_response_static_contract_invalid",
                contract_reason=blocker.get("reason"),
                contract_blocker=blocker,
            )

        scope = contract.get("scope")
        if not isinstance(scope, dict):
            add("command_chat_response_static_contract_scope_missing")
        else:
            expected_targets = sorted(EXPECTED_TARGET_NAMES)
            if scope.get("topic") != CONTRACT_TOPIC:
                add(
                    "command_chat_response_static_contract_topic_invalid",
                    expected=CONTRACT_TOPIC,
                    value=scope.get("topic"),
                )
            if scope.get("target_set") != PLANNING_SURFACE:
                add(
                    "command_chat_response_static_contract_target_set_invalid",
                    expected=PLANNING_SURFACE,
                    value=scope.get("target_set"),
                )
            if scope.get("binary_sha256") != report.get("binary_sha256"):
                add(
                    "command_chat_response_static_contract_binary_sha256_mismatch",
                    expected=report.get("binary_sha256"),
                    value=scope.get("binary_sha256"),
                )
            if scope.get("expected_targets") != expected_targets:
                add(
                    "command_chat_response_static_contract_expected_targets_invalid",
                    expected=expected_targets,
                    value=scope.get("expected_targets"),
                )

        contract_blockers = contract.get("blockers")
        if not isinstance(contract_blockers, list) or not all(isinstance(item, str) for item in contract_blockers):
            add("command_chat_response_static_contract_blockers_invalid")
        else:
            missing = sorted(set(REQUIRED_CONTRACT_BLOCKERS) - set(contract_blockers))
            if missing:
                add("command_chat_response_static_contract_required_blocker_missing", missing=missing)

        if contract.get("non_claims") != report.get("non_claims"):
            add("command_chat_response_static_contract_non_claims_mismatch")

        subjects = contract.get("subjects")
        checked_targets = report.get("checked_targets")
        if isinstance(subjects, list) and isinstance(checked_targets, list):
            subject_names = sorted(
                subject["target"]
                for subject in subjects
                if isinstance(subject, dict) and isinstance(subject.get("target"), str)
            )
            checked_names = sorted(
                target["target"]
                for target in checked_targets
                if isinstance(target, dict) and isinstance(target.get("target"), str)
            )
            if subject_names != checked_names:
                add(
                    "command_chat_response_static_contract_subjects_mismatch",
                    expected=checked_names,
                    value=subject_names,
                )

    for target in report.get("checked_targets", []):
        if not isinstance(target, dict):
            add("command_chat_response_target_boundary_invalid")
            continue
        if target.get("status") == "candidate_orientation_valid" and target.get("candidate_only") is not True:
            add("command_chat_response_target_candidate_boundary_missing", target=target.get("target"))
        if target.get("public_abi_ready") is not False:
            add(
                "command_chat_response_target_public_abi_overclaim",
                target=target.get("target"),
                value=target.get("public_abi_ready"),
            )
        if target.get("public_sdk_evidence") != "not_public_sdk_evidence":
            add(
                "command_chat_response_target_public_sdk_evidence_overclaim",
                target=target.get("target"),
                value=target.get("public_sdk_evidence"),
            )
        if target.get("artifact_gate_evidence") != "not_artifact_gate_evidence":
            add(
                "command_chat_response_target_artifact_gate_evidence_overclaim",
                target=target.get("target"),
                value=target.get("artifact_gate_evidence"),
            )

    return blockers


def validate_binary(path: Path, expected_sha256: str) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    resolved: Path | None = None
    binary_sha256: str | None = None
    checked_targets: list[dict[str, Any]] = []

    try:
        reject_symlink_component(path, "binary")
        resolved = reject_protected_input_path(path, "binary")
    except SystemExit as exc:
        append_blocker(blockers, "binary_path_rejected", path=str(path), detail=str(exc))
        data = b""
    else:
        try:
            data = resolved.read_bytes()
            binary_sha256 = sha256_file(resolved)
        except OSError as exc:
            append_blocker(blockers, "binary_unreadable", path=str(resolved), detail=str(exc))
            data = b""

    if binary_sha256 is not None and binary_sha256 != expected_sha256:
        append_blocker(
            blockers,
            "binary_sha256_mismatch",
            expected=expected_sha256,
            value=binary_sha256,
        )

    if data:
        segments, sections = parse_elf(data, blockers)
        check_section_layout(sections, blockers)
        for target in RESPONSE_PATH_TARGETS:
            checked_targets.append(validate_target(data, segments, sections, target, blockers))

    non_claims = [
        "valid static orientation is candidate-only planning evidence for obelisk.command_chat_response_path.v1",
        "does not claim replies, send-chat API, command router, identity, permissions, raw UE pointer exposure, raw FString exposure, mutation, return override, runtime readiness, or public SDK promotion",
        "does not replace a non-protected complete core evidence pack, reflection inventory pack, focal snapshots, second-source evidence, or runtime validation",
        "does not promote public identity, runtime hooks, object lookup, command execution, or SDK surface",
        "does not promote permissions or commands",
        "does not promote mutation or return override",
    ]
    blocker_labels = [
        "requires_non_protected_core_evidence_pack",
        "requires_reflection_inventory_or_focal_snapshots_for_response_path_targets",
        "requires_command_router_identity_and_permission_contracts_before_command_replies",
        "requires_copied_data_response_contract_before_public_sdk_promotion",
    ]
    promotion_blockers = list(REQUIRED_PROMOTION_BLOCKERS)
    static_contract = build_contract(
        topic=CONTRACT_TOPIC,
        binary_sha256=binary_sha256,
        target_set=PLANNING_SURFACE,
        expected_targets=EXPECTED_TARGET_NAMES,
        address_convention="non-PIE ELF VMA for this ARK Linux ShooterGameServer binary",
        subjects=contract_subjects(checked_targets),
        non_claims=non_claims,
        blockers=blocker_labels,
    )

    report = {
        "schema": REPORT_SCHEMA,
        "status": "blocked",
        "valid": False,
        "accepted_for_orientation": False,
        "candidate_evidence_status": CANDIDATE_EVIDENCE_STATUS,
        "not_artifact_gate": True,
        "artifact_gate": artifact_gate_boundary(),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_abi_boundary": public_abi_boundary(),
        "promotion_blockers": promotion_blockers,
        "planning_surface": PLANNING_SURFACE,
        "binary": str(resolved if resolved is not None else path),
        "binary_sha256": binary_sha256,
        "expected_binary_sha256": expected_sha256,
        "target_names": list(EXPECTED_TARGET_NAMES),
        "checked_targets": checked_targets,
        "static_candidate_orientation_contract": static_contract,
        "blockers": blockers,
        "non_claims": non_claims,
    }
    blockers.extend(validate_report_boundary(report))
    valid = not blockers
    report["status"] = "valid" if valid else "blocked"
    report["valid"] = valid
    report["accepted_for_orientation"] = valid
    return report


def main() -> int:
    args = parse_args()
    report = validate_binary(args.binary, args.expected_binary_sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
