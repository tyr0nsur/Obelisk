#!/usr/bin/env python3
"""Verify private static inventory anchors; never executes or enables a grant."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from native_suite_bindings import CURRENT_SHA, ElfImage, integer


PROFILE = Path(__file__).resolve().parents[2] / "docs/research/native_inventory_receipt_profile_361_7.json"


def verify(binary: Path, profile: dict) -> dict:
    image = ElfImage(binary)
    if image.sha != CURRENT_SHA or profile.get("sha256") != CURRENT_SHA:
        raise ValueError("Exact native build identity differs")
    if (profile.get("schema") != "obelisk.native-inventory-receipt-profile.v1"
            or profile.get("runtime_validated") is not False
            or profile.get("gameplay_accepted") is not False
            or profile.get("native_grant_enabled") is not False):
        raise ValueError("Static audit must not enable or accept native delivery")
    proofs = profile.get("proofs")
    if not isinstance(proofs, list) or not proofs:
        raise ValueError("Missing static byte proofs")
    for proof in proofs:
        expected = bytes.fromhex(proof["bytes"])
        if not expected or image.read(integer(proof["address"]), len(expected)) != expected:
            raise ValueError("Static inventory byte proof differs")
    for address in profile["functions"].values():
        if not image.is_code(integer(address)):
            raise ValueError("Inventory candidate is not executable")
    fields = profile["fields"]
    for field in fields.values():
        if field.get("status") != "static_metadata_candidate":
            raise ValueError("Unreviewed inventory field promotion")
        integer(field["offset"])
        integer(field["registration_site"])
    image.verify_stable()
    return {"sha256": image.sha, "byte_proofs_verified": len(proofs),
            "field_candidates": len(fields), "binary_unchanged": True,
            "code_executed": False, "native_grant_enabled": False,
            "gameplay_accepted": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=PROFILE)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.binary, json.loads(args.profile.read_text())), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Inventory receipt audit failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
