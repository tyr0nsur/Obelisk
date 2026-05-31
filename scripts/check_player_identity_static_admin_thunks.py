#!/usr/bin/env python3
"""Validate static admin-thunk orientation for player identity without promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_BINARY = Path(
    "/home/flowcommunity-ark/obelisk-artifacts/offline-binaries/"
    "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520/"
    "ShooterGameServer"
)
REPORT_SCHEMA = "obelisk.player-identity-static-admin-thunks-check.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
TARGET_SET = "players-identity-lifecycle-intake"
REGISTRAR_CALL_VMA = 0x1CCC140
FNAME_INIT_CALL_VMA = 0x1C892D0
CLASS_SLOT_VMA = 0x58EEBF0
SCRIPT_NAME_VMA = 0x3F63B7C
CONTROLLER_NAME_VMA = 0x40D7418


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
class AdminThunk:
    target: str
    ascii_name: str
    ascii_vma: int
    utf32_vma: int
    registration_vma: int
    registration_class_load_vma: int
    thunk_vma: int
    fname_init_vma: int
    fname_slot_vma: int
    vtable_offset: int
    expected_thunk_prefix: bytes
    decode_call_vmas: tuple[int, ...] = ()


ADMIN_THUNKS = (
    AdminThunk(
        target="ShooterPlayerController.ServerKickPlayer",
        ascii_name="ServerKickPlayer",
        ascii_vma=0x41632DA,
        utf32_vma=0x40FD540,
        registration_vma=0x1368F6C,
        registration_class_load_vma=0x1368F65,
        thunk_vma=0x1547320,
        fname_init_vma=0x78D778,
        fname_slot_vma=0x58EAE60,
        vtable_offset=0x1528,
        expected_thunk_prefix=bytes.fromhex("554889e54156534883ec20"),
        decode_call_vmas=(0x154734A, 0x154736A, 0x1547388, 0x15473A8),
    ),
    AdminThunk(
        target="ShooterPlayerController.ServerListPlayers",
        ascii_name="ServerListPlayers",
        ascii_vma=0x41632EB,
        utf32_vma=0x40FD5E4,
        registration_vma=0x1368FA9,
        registration_class_load_vma=0x1368FA2,
        thunk_vma=0x1547450,
        fname_init_vma=0x78D7AA,
        fname_slot_vma=0x58EAE68,
        vtable_offset=0x1520,
        expected_thunk_prefix=bytes.fromhex(
            "488b46204885c00f95c10fb6c94801c148894e20488b07ffa020150000"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Byte-check ServerListPlayers/ServerKickPlayer static admin thunk "
            "orientation against an offline ShooterGameServer binary."
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


def parse_elf_load_segments(data: bytes, blockers: list[dict[str, Any]]) -> list[LoadSegment]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        append_blocker(blockers, "elf_magic_invalid")
        return []
    if data[4] != 2:
        append_blocker(blockers, "elf_class_not_64_bit", value=data[4])
        return []
    if data[5] != 1:
        append_blocker(blockers, "elf_not_little_endian", value=data[5])
        return []

    try:
        (
            e_type,
            e_machine,
            _e_version,
            entry,
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
        append_blocker(blockers, "elf_header_truncated", detail=str(exc))
        return []

    if e_type != 2:
        append_blocker(blockers, "elf_type_not_exec", value=e_type)
    if e_machine != 62:
        append_blocker(blockers, "elf_machine_not_x86_64", value=e_machine)
    if entry != 0x81DC59:
        append_blocker(blockers, "elf_entry_mismatch", value=hex(entry))
    if phentsize < 56:
        append_blocker(blockers, "elf_program_header_entry_too_small", value=phentsize)
        return []

    segments: list[LoadSegment] = []
    for index in range(phnum):
        header_offset = phoff + index * phentsize
        if header_offset + 56 > len(data):
            append_blocker(blockers, "elf_program_header_truncated", index=index)
            return segments
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _p_align = struct.unpack_from(
            "<IIQQQQQQ", data, header_offset
        )
        if p_type == 1:
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
    return segments


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


def read_u32(data: bytes, segments: list[LoadSegment], vma: int) -> int | None:
    raw = read_vma(data, segments, vma, 4)
    if raw is None:
        return None
    return struct.unpack("<I", raw)[0]


def call_target(data: bytes, segments: list[LoadSegment], call_vma: int) -> int | None:
    raw = read_vma(data, segments, call_vma, 5)
    if raw is None or raw[0] != 0xE8:
        return None
    rel32 = struct.unpack("<i", raw[1:])[0]
    return call_vma + 5 + rel32


def check_load_segments(segments: list[LoadSegment], blockers: list[dict[str, Any]]) -> None:
    required_rx_vmas = [
        0x78D778,
        0x1368F65,
        0x1368FA2,
        0x1547320,
        0x1547450,
    ]
    required_ro_vmas = [
        SCRIPT_NAME_VMA,
        CONTROLLER_NAME_VMA,
        0x40FD540,
        0x40FD5E4,
        0x41632DA,
        0x41632EB,
    ]
    required_bss_vmas = [CLASS_SLOT_VMA, 0x58EAE60, 0x58EAE68]

    for vma in required_rx_vmas:
        segment = segment_for_file_vma(segments, vma)
        if segment is None or not segment.is_rx:
            append_blocker(blockers, "required_text_vma_not_in_rx_load", vma=hex(vma))
    for vma in required_ro_vmas:
        segment = segment_for_file_vma(segments, vma)
        if segment is None or not segment.is_readable:
            append_blocker(blockers, "required_rodata_vma_not_file_readable", vma=hex(vma))
    for vma in required_bss_vmas:
        segment = segment_for_mem_vma(segments, vma, 8)
        if segment is None or not segment.is_rw:
            append_blocker(blockers, "required_bss_slot_not_in_rw_load", vma=hex(vma))
            continue
        if segment.contains_file_vma(vma, 8):
            append_blocker(blockers, "required_bss_slot_is_file_backed", vma=hex(vma))


def check_ascii_string(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    expected = thunk.ascii_name.encode("ascii") + b"\x00"
    actual = read_vma(data, segments, thunk.ascii_vma, len(expected))
    if actual != expected:
        append_blocker(
            blockers,
            "admin_ascii_name_mismatch",
            target=thunk.target,
            vma=hex(thunk.ascii_vma),
        )


def check_utf32_string(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    expected = thunk.ascii_name.encode("utf-32-le") + b"\x00\x00\x00\x00"
    actual = read_vma(data, segments, thunk.utf32_vma, len(expected))
    if actual != expected:
        append_blocker(
            blockers,
            "admin_utf32_name_mismatch",
            target=thunk.target,
            vma=hex(thunk.utf32_vma),
        )


def check_class_load(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    raw = read_vma(data, segments, thunk.registration_class_load_vma, 7)
    if raw is None or raw[:3] != b"\x48\x8b\x3d":
        append_blocker(
            blockers,
            "registration_class_load_opcode_mismatch",
            target=thunk.target,
            vma=hex(thunk.registration_class_load_vma),
        )
        return
    disp = struct.unpack("<i", raw[3:])[0]
    target = thunk.registration_class_load_vma + 7 + disp
    if target != CLASS_SLOT_VMA:
        append_blocker(
            blockers,
            "registration_class_slot_mismatch",
            target=thunk.target,
            expected=hex(CLASS_SLOT_VMA),
            value=hex(target),
        )


def check_registration(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    raw = read_vma(data, segments, thunk.registration_vma, 17)
    if raw is None:
        append_blocker(blockers, "registration_window_unreadable", target=thunk.target)
        return
    if raw[0] != 0xBE or struct.unpack("<I", raw[1:5])[0] != thunk.ascii_vma:
        append_blocker(
            blockers,
            "registration_name_immediate_mismatch",
            target=thunk.target,
            expected=hex(thunk.ascii_vma),
        )
    if raw[5] != 0xBA or struct.unpack("<I", raw[6:10])[0] != thunk.thunk_vma:
        append_blocker(
            blockers,
            "registration_thunk_immediate_mismatch",
            target=thunk.target,
            expected=hex(thunk.thunk_vma),
        )
    if raw[10:12] != b"\x31\xc9":
        append_blocker(blockers, "registration_zero_flags_opcode_mismatch", target=thunk.target)
    if raw[12] != 0xE8:
        append_blocker(blockers, "registration_call_opcode_mismatch", target=thunk.target)
    elif call_target(data, segments, thunk.registration_vma + 12) != REGISTRAR_CALL_VMA:
        append_blocker(
            blockers,
            "registration_call_target_mismatch",
            target=thunk.target,
            expected=hex(REGISTRAR_CALL_VMA),
        )


def check_fname_init(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    raw = read_vma(data, segments, thunk.fname_init_vma, 25)
    if raw is None:
        append_blocker(blockers, "fname_init_window_unreadable", target=thunk.target)
        return
    checks = (
        (0, 0xBF, thunk.fname_slot_vma, "fname_init_slot_immediate_mismatch"),
        (5, 0xBE, thunk.utf32_vma, "fname_init_name_immediate_mismatch"),
        (10, 0xBA, 1, "fname_init_edx_immediate_mismatch"),
        (15, 0xB9, 1, "fname_init_ecx_immediate_mismatch"),
    )
    for offset, opcode, expected, reason in checks:
        if raw[offset] != opcode or struct.unpack("<I", raw[offset + 1 : offset + 5])[0] != expected:
            append_blocker(
                blockers,
                reason,
                target=thunk.target,
                expected=hex(expected),
                vma=hex(thunk.fname_init_vma + offset),
            )
    if raw[20] != 0xE8:
        append_blocker(blockers, "fname_init_call_opcode_mismatch", target=thunk.target)
    elif call_target(data, segments, thunk.fname_init_vma + 20) != FNAME_INIT_CALL_VMA:
        append_blocker(
            blockers,
            "fname_init_call_target_mismatch",
            target=thunk.target,
            expected=hex(FNAME_INIT_CALL_VMA),
        )


def check_thunk_shape(
    data: bytes,
    segments: list[LoadSegment],
    thunk: AdminThunk,
    blockers: list[dict[str, Any]],
) -> None:
    prefix = read_vma(data, segments, thunk.thunk_vma, len(thunk.expected_thunk_prefix))
    if prefix != thunk.expected_thunk_prefix:
        append_blocker(
            blockers,
            "thunk_prefix_mismatch",
            target=thunk.target,
            thunk_vma=hex(thunk.thunk_vma),
        )

    window = read_vma(data, segments, thunk.thunk_vma, 0xD0)
    expected_vtable = struct.pack("<I", thunk.vtable_offset)
    if window is None or expected_vtable not in window:
        append_blocker(
            blockers,
            "thunk_vtable_offset_not_observed",
            target=thunk.target,
            expected=hex(thunk.vtable_offset),
        )

    for decode_call_vma in thunk.decode_call_vmas:
        target = call_target(data, segments, decode_call_vma)
        if target not in {0x1D32C70, 0x1D32CB0}:
            append_blocker(
                blockers,
                "kick_decode_call_target_mismatch",
                target=thunk.target,
                call_vma=hex(decode_call_vma),
                value=hex(target) if target is not None else None,
            )


def check_shared_names(data: bytes, segments: list[LoadSegment], blockers: list[dict[str, Any]]) -> None:
    expected_script = "/Script/ShooterGame".encode("utf-32-le") + b"\x00\x00\x00\x00"
    script = read_vma(data, segments, SCRIPT_NAME_VMA, len(expected_script))
    if script != expected_script:
        append_blocker(blockers, "script_name_utf32_mismatch", vma=hex(SCRIPT_NAME_VMA))
    expected_controller = "AShooterPlayerController".encode("utf-32-le") + b"\x00\x00\x00\x00"
    controller = read_vma(
        data,
        segments,
        CONTROLLER_NAME_VMA,
        len(expected_controller),
    )
    if controller != expected_controller:
        append_blocker(blockers, "controller_name_utf32_mismatch", vma=hex(CONTROLLER_NAME_VMA))


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
            segments = parse_elf_load_segments(data, blockers)
            check_load_segments(segments, blockers)
            check_shared_names(data, segments, blockers)
            for thunk in ADMIN_THUNKS:
                before = len(blockers)
                check_ascii_string(data, segments, thunk, blockers)
                check_utf32_string(data, segments, thunk, blockers)
                check_class_load(data, segments, thunk, blockers)
                check_registration(data, segments, thunk, blockers)
                check_fname_init(data, segments, thunk, blockers)
                check_thunk_shape(data, segments, thunk, blockers)
                checked_targets.append(
                    {
                        "target": thunk.target,
                        "status": "candidate_orientation_valid" if len(blockers) == before else "blocked",
                        "ascii_name_vma": hex(thunk.ascii_vma),
                        "utf32_name_vma": hex(thunk.utf32_vma),
                        "registration_vma": hex(thunk.registration_vma),
                        "thunk_vma": hex(thunk.thunk_vma),
                        "probable_fname_slot_vma": hex(thunk.fname_slot_vma),
                        "observed_vtable_offset": hex(thunk.vtable_offset),
                    }
                )

    valid = not blockers
    return {
        "schema": REPORT_SCHEMA,
        "status": "valid" if valid else "blocked",
        "valid": valid,
        "accepted_for_orientation": valid,
        "not_artifact_gate": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "binary": str(resolved if resolved is not None else path),
        "binary_sha256": binary_sha256,
        "expected_binary_sha256": expected_sha256,
        "target_set": TARGET_SET,
        "checked_targets": checked_targets,
        "blockers": blockers,
        "non_claims": [
            "valid static admin-thunk orientation is bounded byte evidence for this offline binary only",
            "does not prove UFunction object identity, FName indices, UProperty chains, parameter offsets, login/logout lifecycle anchors, or player principal mapping",
            "does not promote public identity, permissions, commands, economy, runtime hooks, object lookup, ResourceHandle, mutation, return override, or SDK surface",
            "does not replace a non-protected complete core evidence pack, reviewed reflection inventory pack, focal ServerListPlayers/ServerKickPlayer snapshots, second-source evidence, or privacy/invalidation policy",
        ],
    }


def main() -> int:
    args = parse_args()
    report = validate_binary(args.binary, args.expected_binary_sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
