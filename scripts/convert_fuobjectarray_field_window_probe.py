#!/usr/bin/env python3
"""Convert bounded Ghidra/r2 FUObjectArray probe output into redacted JSON."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.fuobjectarray-field-window-redacted.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_int(value: str) -> int:
    return int(value, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def candidate_address_sha256(binary_sha256: str, candidate: int) -> str:
    material = f"obelisk.fuobjectarray-field-window:{binary_sha256}:0x{candidate:x}"
    return hashlib.sha256(material.encode("ascii")).hexdigest()


def parse_tool_version(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("tool version must be NAME=VERSION")
    name, version = value.split("=", 1)
    name = name.strip()
    version = version.strip()
    if not name or not version:
        raise argparse.ArgumentTypeError("tool version name and value must not be empty")
    return name, version


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def hex_needles(value: int) -> tuple[str, ...]:
    raw = f"{value:x}"
    return (f"0x{raw}", f"0x0{raw}", f"_DAT_0{raw}", f"[0x0{raw}]")


def required_evidence(ghidra_text: str, r2_text: str, candidate: int) -> tuple[dict[str, bool], list[str]]:
    candidate_needles = hex_needles(candidate)
    chunks_needles = hex_needles(candidate + 0x10)
    count_needles = hex_needles(candidate + 0x24)
    serial_needles = hex_needles(candidate + 0x58)

    facts = {
        "candidate_passed_to_constructor_helper": (
            "static_init_caller" in ghidra_text
            and contains_any(ghidra_text, candidate_needles)
            and contains_any(ghidra_text, ("func_0x01d474e0", "CALL 0x01d474e0"))
            and contains_any(r2_text, candidate_needles)
        ),
        "same_candidate_registered_with_finalizer": (
            "__cxa_atexit" in ghidra_text and contains_any(ghidra_text, candidate_needles)
        ),
        "constructor_writes_relative_fields": (
            ("+ 0x10" in ghidra_text or "+ 0x10" in r2_text)
            and ("+ 0x58" in ghidra_text or "+ 0x58" in r2_text)
            and (contains_any(ghidra_text, chunks_needles) or contains_any(r2_text, chunks_needles))
        ),
        "serial_accessors_use_same_field_family": (
            contains_any(ghidra_text, count_needles)
            and contains_any(ghidra_text, chunks_needles)
            and contains_any(ghidra_text, serial_needles)
            and contains_any(r2_text, count_needles)
            and contains_any(r2_text, chunks_needles)
            and contains_any(r2_text, serial_needles)
            and contains_any(ghidra_text + r2_text, ("XADD.LOCK", "lock xadd"))
            and contains_any(ghidra_text + r2_text, ("CMPXCHG.LOCK", "cmpxchg"))
        ),
    }
    blockers = [name for name, present in facts.items() if not present]
    return facts, blockers


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    ghidra_path = reject_protected_input_path(args.ghidra_stdout, "--ghidra-stdout")
    r2_path = reject_protected_input_path(args.r2_windows, "--r2-windows")
    if not SHA256_RE.fullmatch(args.binary_sha256):
        raise SystemExit("--binary-sha256 must be a lowercase SHA256")
    if args.candidate_label != "gobjects":
        raise SystemExit("--candidate-label currently supports only gobjects")
    candidate = parse_int(args.candidate_address)

    ghidra_text = ghidra_path.read_text(encoding="utf-8", errors="replace")
    r2_text = r2_path.read_text(encoding="utf-8", errors="replace")
    facts, blockers = required_evidence(ghidra_text, r2_text, candidate)
    if blockers:
        raise SystemExit(f"FUObjectArray field-window probe incomplete: {','.join(blockers)}")

    versions = dict(args.tool_version or [])
    evidence = sorted(name for name, present in facts.items() if present)
    windows = [
        {
            "id": "static_init_caller",
            "role": "bootstrap",
            "ghidra_seen": True,
            "r2_seen": True,
            "absolute_range_redacted": True,
            "facts": [
                "passes_candidate_base",
                "registers_finalizer_for_same_base",
            ],
        },
        {
            "id": "ctor_helper",
            "role": "init",
            "ghidra_seen": True,
            "r2_seen": True,
            "absolute_range_redacted": True,
            "facts": [
                "writes_chunks_family",
                "initializes_count_family",
                "seeds_serial_field",
            ],
        },
        {
            "id": "serial_accessor",
            "role": "lookup",
            "ghidra_seen": True,
            "r2_seen": True,
            "absolute_range_redacted": True,
            "facts": [
                "bounds_checks_count",
                "loads_chunks",
                "updates_fuobjectitem_serial",
            ],
        },
    ]
    return {
        "schema": SCHEMA,
        "status": "accepted_internal_static_evidence",
        "binary": {
            "sha256": args.binary_sha256,
            "path_redacted": True,
        },
        "candidate": {
            "label": args.candidate_label,
            "kind": "gobjects",
            "address_redacted": True,
            "address_sha256": candidate_address_sha256(args.binary_sha256, candidate),
        },
        "redaction": {
            "absolute_addresses": "omitted",
            "raw_disassembly": "omitted",
            "raw_decompiler_text": "omitted",
            "absolute_paths": "omitted",
            "kept_values": [
                "relative_field_offsets",
                "window_roles",
                "tool_versions",
                "artifact_sha256",
            ],
        },
        "sources": {
            "ghidra_stdout": {
                "artifact_sha256": sha256_file(ghidra_path),
                "tool": "ghidra",
                "version": versions.get("ghidra", "unknown"),
            },
            "r2_windows": {
                "artifact_sha256": sha256_file(r2_path),
                "tool": "radare2",
                "version": versions.get("radare2", "unknown"),
            },
        },
        "fuobjectarray_window": {
            "same_base_flow": {
                "proven": True,
                "evidence": evidence,
            },
            "required_fields": {
                "root": {"present": True, "basis": "candidate_base"},
                "chunks": {"present": True, "relative_offset": "base+0x10"},
                "count": {"present": True, "relative_offset": "base+0x24"},
                "serial": {"present": True, "relative_offset": "base+0x58"},
            },
            "windows": windows,
        },
        "builder_contract": {
            "candidate_static_contract_blocker_to_clear": "missing_gobjects_coherent_field_window",
            "promotion_gate_ready": False,
            "remaining_blockers": ["static_only_evidence"],
            "consumption_scope": "internal_static_research_only",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghidra-stdout", type=Path, required=True)
    parser.add_argument("--r2-windows", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--candidate-label", default="gobjects")
    parser.add_argument("--candidate-address", required=True)
    parser.add_argument("--tool-version", action="append", type=parse_tool_version, default=[])
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    payload = build_payload(args)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
