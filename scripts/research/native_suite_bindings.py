#!/usr/bin/env python3
"""Read-only verification of the private, exact-build native suite profile.

The executable is data. This tool never loads its code, connects to a process,
or marks a binding as accepted by a game client. A different SHA must be studied
as a new build rather than accepting coincident addresses or old field fixtures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


CURRENT_SHA = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
DEFAULT_PROFILE = Path(__file__).resolve().parents[2] / "docs/research/native_suite_profile_361_7.json"


class ElfImage:
    def __init__(self, path: Path):
        self.path = path.resolve(strict=True)
        self.before = self.path.stat()
        self.data = self.path.read_bytes()
        if self.data[:6] != b"\x7fELF\x02\x01":
            raise ValueError("ELF64 little-endian input required")
        if struct.unpack_from("<HH", self.data, 16) != (2, 62):
            raise ValueError("x86_64 ET_EXEC input required")
        self.sha = hashlib.sha256(self.data).hexdigest()
        offset = struct.unpack_from("<Q", self.data, 32)[0]
        entry_size, count = struct.unpack_from("<HH", self.data, 54)
        self.loads = []
        for index in range(count):
            kind, flags, file_offset, address, _, size, _, _ = struct.unpack_from(
                "<IIQQQQQQ", self.data, offset + entry_size * index)
            if kind == 1:
                self.loads.append((address, file_offset, size, flags))

    def read(self, address: int, size: int) -> bytes:
        if size <= 0 or size > 65536:
            raise ValueError("Invalid bounded read")
        for base, offset, extent, _ in self.loads:
            if base <= address and address + size <= base + extent:
                begin = offset + address - base
                result = self.data[begin:begin + size]
                if len(result) == size:
                    return result
        raise ValueError(f"Non-file-backed address: {address:#x}")

    def is_code(self, address: int) -> bool:
        return any(flags & 1 and base <= address < base + extent
                   for base, _, extent, flags in self.loads)

    def verify_stable(self) -> None:
        after = self.path.stat()
        fields = lambda value: (value.st_ino, value.st_size, value.st_mtime_ns)
        if fields(after) != fields(self.before):
            raise ValueError("Input changed during verification")
        with self.path.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != self.sha:
                raise ValueError("Input contents changed during verification")


def integer(value: object) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-f]+", value):
        raise ValueError("Profile addresses must use lowercase hexadecimal")
    return int(value, 16)


def verify(image: ElfImage, profile: dict) -> dict:
    if image.sha != CURRENT_SHA or profile.get("sha256") != CURRENT_SHA:
        raise ValueError("Exact native build identity differs")
    if profile.get("runtime_validated") is not False:
        raise ValueError("Static research profile must not claim runtime acceptance")
    proofs = profile.get("proofs", [])
    if not isinstance(proofs, list) or not proofs:
        raise ValueError("Missing byte proofs")
    for proof in proofs:
        address = integer(proof["address"])
        expected = bytes.fromhex(proof["bytes"])
        if image.read(address, len(expected)) != expected:
            raise ValueError(f"Byte proof differs at {address:#x}")
    for name, binding in profile["classes"].items():
        address = integer(binding["name_utf32"])
        text = name.encode("utf-32-le") + bytes(4)
        if image.read(address, len(text)) != text:
            raise ValueError(f"Class literal differs: {name}")
        instruction = image.read(integer(binding["binding_site"]), 20)
        # ESI = literal, EDX = canonical class storage, ECX = native binder.
        if (instruction[0] != 0xBE or instruction[5] != 0xBA or instruction[10] != 0xB9
                or struct.unpack_from("<I", instruction, 1)[0] != address
                or struct.unpack_from("<I", instruction, 6)[0] != integer(binding["global"])):
            raise ValueError(f"Class storage binding differs: {name}")
    registrations = 0
    for name, records in profile["registrations"].items():
        for record in records:
            address = integer(record["ascii"])
            literal = name.encode("ascii") + b"\0"
            if image.read(address, len(literal)) != literal:
                raise ValueError(f"Native registration name differs: {name}")
            site = integer(record["registration"])
            code = image.read(site - 7, 24)
            if (code[:3] != b"\x48\x8b\x3d" or code[7] != 0xBE or code[12] != 0xBA
                    or code[17:20] != b"\x31\xc9\xe8"):
                raise ValueError(f"Native registration instruction form differs: {name}")
            if (site + struct.unpack_from("<i", code, 3)[0] != integer(record["class_global"])
                    or struct.unpack_from("<I", code, 8)[0] != address
                    or struct.unpack_from("<I", code, 13)[0] != integer(record["exec"])
                    or site + 17 + struct.unpack_from("<i", code, 20)[0]
                    != integer(record["registration_helper"])):
                raise ValueError(f"Native registration targets differ: {name}")
            if not image.is_code(integer(record["exec"])):
                raise ValueError(f"Native exec is not executable: {name}")
            registrations += 1
    for function in profile["functions"].values():
        if not image.is_code(integer(function["address"])):
            raise ValueError("Native implementation is not executable")
    image.verify_stable()
    return {"schema": "obelisk.suite.native-profile-verification.v1", "sha256": image.sha,
            "bytes": len(image.data), "proofs_verified": len(proofs),
            "class_bindings_verified": len(profile["classes"]),
            "registrations_verified": registrations,
            "binary_unchanged": True, "static_profile_verified": True,
            "gameplay_accepted": False, "code_executed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    args = parser.parse_args()
    try:
        profile = json.loads(args.profile.read_text(encoding="utf-8"))
        result = verify(ElfImage(args.binary), profile)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        parser.exit(1, f"Native suite verification failed: {error}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
