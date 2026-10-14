#!/usr/bin/env python3
"""Verify exact-build identity observations without executing game code.

This private research verifier checks registration, byte windows, literals,
vtables, and imported names. It does not certify authentication, session
ownership, a runtime callback, or stable Steam/Epic account correlation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct

from native_suite_bindings import CURRENT_SHA, ElfImage


PROOFS = (
    ("player_state_class_binding", 0x135c131, "be34720d04ba80eb8e05b9a0f03501e8ebc61d00"),
    ("uid_native_registration", 0x135f517, "488b3d62f65804be40101604ba5061530131c9e811cc9600"),
    ("uid_exec_call", 0x1536175, "4c8d75e04c89f74889c6e8dc8ea9ff"),
    ("uid_current_reader", 0xfcf060, "554889e553504889fb488bb6c80400004885f6740b488b064889dfff5030eb060f57c00f11034889d84883c4085b5dc3"),
    ("uid_numeric_formatter", 0x354c420, "554889e553504889fb488b5650bef8c8030431c0e8f7d85afe4889d84883c4085b5dc3"),
    ("compound_default_masks", 0x35562f3, "48c70300cc6d0448b800000000000000e04889430848b800000000000000604889431048b8ffffffffffffff7f48894318"),
    ("numeric_provider_derivation", 0x3552f9d, "49894424504923442408493b442410410f94442458410f9544245941c644245a0041807c24580074564d39f774"),
    ("is_valid_steam", 0x35304b0, "48837f50000f95c0c3"),
    ("is_valid_eos", 0x358e4f0, "48837f50000f95c0c3"),
    ("flag_steam", 0x354c5a0, "8a4759c3"),
    ("flag_eos", 0x354c5b0, "8a4758c3"),
    ("flag_stadia", 0x354c5c0, "8a475ac3"),
    ("generic_bypass", 0x3549c00, "c6010141c60001c3"),
    ("eos_disable_flag_binding", 0x356d328, "e8a3d964febe18f76d044889c7e856db64fe880598464a02bfe019a105e8f6a90dfd"),
    ("eos_disable_flag_bypass", 0x356d34a, "803d87464a0200740e41c645000141c60601e924010000"),
    ("eos_verify_id_call", 0x356d850, "488b83f8020000488bb880010000488db5c0fdffffb910135a034c89eae88e890dfd"),
    ("eos_verify_callback", 0x35a1310, "554889e54156534883ec10833f13744b488b5f0848897de84c8b731031ff837b"),
    ("eos_auth_success_dispatch", 0x358a5f0, "488b0e488b078339000f94c1488b104c8b8258020000488d57180fb6f14889c741ffe0"),
    ("auth_delegate_broadcast", 0x353a518, "498b8770010000488b3cd84885ff74d8488b074489ee4c89f2ff5068"),
    ("steam_auth_pending_flags", 0x350b4e4, "4d89c548898d18ffffff4989d44889b510ffffff4989ffc6010041c6450000"),
    ("steam_auth_steam_server", 0x350b554, "e827bb13fd488b8518ffffffc6000141c6450000"),
    ("steam_auth_type_tests", 0x350b57f, "4885c074d54c89e7488b074889fbff502884c074c54889df488b074989fcff507084c074b5"),
    ("steam_auth_uid_vtable", 0x350b69b, "48c78570ffffff60cb6d04"),
    ("steam_approve_callback_register", 0x353601b, "48c7839003000010a65003bec90000004c89ffe85d0a11fd"),
    ("steam_deny_callback_register", 0x3536091, "48c783b8030000c0a85003beca000000e8ea0911fd"),
    ("steam_approve_subjects", 0x350a63a, "498b36488dbd78ffffffe837bb040048c78578ffffff60cb6d04498b7608488dbd18ffffffe81cbb040048c78518ffffff60cb6d04"),
    ("steam_approve_record", 0x350a727, "66c787810000000001488db518ffffffe8443d0400"),
    ("steam_deny_record", 0x350a9c7, "66c780810000000000"),
    ("steam_approve_callback_size", 0x3549e90, "b810000000c3"),
    ("steam_deny_callback_size", 0x3549ee0, "b88c000000c3"),
)

LITERALS = (
    (0x40d7234, "ShooterPlayerState", "utf-32-le"),
    (0x4161040, "GetUniqueIdString", "ascii"),
    (0x403c8f8, "%llu", "utf-32-le"),
    (0x46df718, "DisableEOSServerAuth", "utf-32-le"),
    (0x46d9874, "%s - Steam: %s; EOS: %s; Stadia: %s; OriginalEOSNetString: %s; EpicAccountId: %s; ProductUserId: %s; UniqueIdAsUint64: %ull; kEOSIdentMask: %ull; kEOSIdentBits: %ull; kEOSBitClearMask: %ull;", "utf-32-le"),
)

VTABLES = {
    0x46dcb60: {0x28: 0x35304b0, 0x30: 0x354c420, 0x70: 0x354c5a0, 0x78: 0x354c5b0},
    0x46e1710: {0x28: 0x358e4f0, 0x30: 0x354c420, 0x70: 0x354c5a0, 0x78: 0x354c5b0},
    0x46cec70: {0x238: 0x350b4d0, 0x258: 0x353a4d0},
    0x46de690: {0x238: 0x356d2e0, 0x258: 0x353a4d0},
    0x46dbfe0: {0x238: 0x3549c00},
    0x46dc3b0: {0: 0x3549e50, 8: 0x3549e70, 16: 0x3549e90},
    0x46dc3e0: {0: 0x3549ea0, 8: 0x3549ec0, 16: 0x3549ee0},
}


def verify(image: ElfImage) -> dict:
    if image.sha != CURRENT_SHA:
        raise ValueError("Exact current native executable SHA256 required")
    for name, address, expected_hex in PROOFS:
        expected = bytes.fromhex(expected_hex)
        if not image.is_code(address) or image.read(address, len(expected)) != expected:
            raise ValueError(f"Native identity byte proof differs: {name}")
    for address, literal, encoding in LITERALS:
        expected = literal.encode(encoding) + (bytes(4) if encoding == "utf-32-le" else bytes(1))
        if image.read(address, len(expected)) != expected:
            raise ValueError(f"Native identity literal differs at {address:#x}")
    slots = 0
    for base, records in VTABLES.items():
        for offset, target in records.items():
            if struct.unpack("<Q", image.read(base + offset, 8))[0] != target or not image.is_code(target):
                raise ValueError(f"Native identity vtable differs at {base + offset:#x}")
            slots += 1
    for name in ("EOS_Auth_VerifyIdToken", "EOS_EpicAccountId_FromString",
                 "EOS_ProductUserId_FromString", "SteamGameServer"):
        if name.encode("ascii") + b"\0" not in image.data:
            raise ValueError(f"Native identity import name absent: {name}")
    image.verify_stable()
    return {
        "schema": "obelisk.identity.native-static-audit.v1",
        "sha256": image.sha, "bytes": len(image.data),
        "byte_proofs_verified": len(PROOFS), "literals_verified": len(LITERALS),
        "vtable_slots_verified": slots, "binary_unchanged": True,
        "code_executed": False, "runtime_identity_correlation_verified": False,
        "authenticated_principal_available": False, "gameplay_accepted": False,
        "known_uid_reader": "0xfcf060", "player_state_unique_net_id_offset": "0x4c8",
        "observed_uid_semantics": "numeric compound transport identity; authentication unproven",
        "provider_marker_semantics": "Steam/EOS/Stadia flags can be derived by parsing untrusted numeric input",
        "auth_candidates": {"steam": "0x350b4d0", "eos": "0x356d2e0"},
        "steam_legacy_callback_candidates": {"approve": {"callback_id": 201, "target": "0x350a610"}, "deny": {"callback_id": 202, "target": "0x350a8c0"}},
        "eos_bypass_must_be_excluded": "DisableEOSServerAuth",
        "next_proof": "Correlate successful provider verification with the exact live connection, principal namespace, and current session; reject bypass/pending/failure.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="Optional new private evidence file (0600; existing files rejected)")
    args = parser.parse_args()
    try:
        result = verify(ElfImage(args.binary))
        serialized = json.dumps(result, indent=2) + "\n"
        if args.output:
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(serialized)
        print(serialized, end="")
    except (OSError, ValueError, struct.error) as error:
        parser.exit(1, f"Native identity static audit failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
