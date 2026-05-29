#!/usr/bin/env python3
"""Scan copied cores for FUObjectItem serial and UObject flag evidence.

This tool is offline-only. It reads an existing ELF core through the same
GUObjectArray path used by the UObject inventory tools and emits a redacted
summary suitable for ResourceHandle research. It does not prove public handle
lifetime or object identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import enumerate_core_uobjects as uobjects  # noqa: E402
from snapshot_evidence_pack import SHA256_RE, reject_protected_input_path, reject_protected_output_path  # noqa: E402


REPORT_SCHEMA = "obelisk.resource-handle-serial-scan.v1"
PROVENANCE_SCHEMA = f"{REPORT_SCHEMA}.provenance.v1"
CONSUME_GATE_EXPECTATION_SCHEMA = f"{REPORT_SCHEMA}.consume-gate-expectation.v1"
DEFAULT_SAMPLE_LIMIT = 64
DEFAULT_OFFLINE_ROOT = Path("/servidor/ark/workspace-offline")
UOBJECT_VALIDITY_MASKS = (0x100, 0x4000, 0x8000)
PATH_VALUE_FLAGS = {"--core", "--output", "--offline-root"}


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {value}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def redact_argv(argv: list[str]) -> list[str]:
    redacted: list[str] = []
    redact_next = False
    for arg in argv:
        if redact_next:
            redacted.append("<redacted-path>")
            redact_next = False
            continue
        if arg in PATH_VALUE_FLAGS:
            redacted.append(arg)
            redact_next = True
            continue
        if any(arg.startswith(f"{flag}=") for flag in PATH_VALUE_FLAGS):
            flag, _value = arg.split("=", 1)
            redacted.append(f"{flag}=<redacted-path>")
            continue
        if "/servidor/ark" in arg:
            redacted.append("<redacted-server-path>")
            continue
        redacted.append(arg)
    return redacted


def membership_status(obj: dict[str, Any]) -> str:
    if obj.get("fuobject_item") in (None, ""):
        return "missing-fuobject-item"
    if obj.get("address") in (None, "", "0x0", 0):
        return "missing-uobject-address"
    if obj.get("internal_index_matches") is not True:
        return "internal-index-mismatch"
    return "candidate-uobject"


def membership_passes(obj: dict[str, Any]) -> bool:
    return membership_status(obj) == "candidate-uobject"


def _sample_object(obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": obj.get("index"),
        "address": obj.get("address"),
        "class_name": obj.get("class_name"),
        "name": obj.get("name"),
        "flags": obj.get("flags"),
        "fuobject_item": obj.get("fuobject_item"),
        "item_dword_0x8": obj.get("item_dword_0x8"),
        "item_dword_0xC": obj.get("item_dword_0xC"),
        "internal_index_matches": obj.get("internal_index_matches"),
        "membership": membership_status(obj),
        "membership_pass": membership_passes(obj),
    }


def _flag_rejection_candidate(obj: dict[str, Any]) -> dict[str, Any]:
    flags = obj.get("flags") if isinstance(obj.get("flags"), int) else 0
    return {
        "index": obj.get("index"),
        "serial": obj.get("item_dword_0x8"),
        "object_ptr_present": obj.get("address") not in (None, "", "0x0", 0),
        "gobjects_membership_pass": membership_passes(obj),
        "flags": flags,
        "has_0x100": bool(flags & 0x100),
        "has_0x4000": bool(flags & 0x4000),
        "has_0x8000": bool(flags & 0x8000),
        "policy_result_strict": "reject" if flags & (0x100 | 0x4000 | 0x8000) else "allow_candidate",
        "policy_result_allow4000": "reject" if flags & (0x100 | 0x8000) else "allow_candidate",
    }


def summarize_objects(
    objects: list[dict[str, Any]],
    *,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
) -> dict[str, Any]:
    if sample_limit < 0:
        raise ValueError("sample_limit must be non-negative")

    totals = {
        "objects_read": len(objects),
        "serial_zero": 0,
        "serial_nonzero": 0,
        "serial_missing": 0,
        "flags_0x100": 0,
        "flags_0x4000": 0,
        "flags_0x8000": 0,
        "flags_any": 0,
        "flags_none_of_masks": 0,
        "membership_pass_count": 0,
        "membership_fail_count": 0,
        "internal_index_mismatch": 0,
    }
    nonzero_serial_samples: list[dict[str, Any]] = []
    flag_mask_samples: list[dict[str, Any]] = []
    flag_rejection_candidate_samples: list[dict[str, Any]] = []
    negative_samples: list[dict[str, Any]] = []
    serial_classes: dict[str, int] = {}

    for obj in objects:
        serial = obj.get("item_dword_0x8")
        flags = obj.get("flags") if isinstance(obj.get("flags"), int) else 0
        membership_pass = membership_passes(obj)

        if membership_pass:
            totals["membership_pass_count"] += 1
        else:
            totals["membership_fail_count"] += 1

        if serial is None:
            totals["serial_missing"] += 1
        elif serial == 0:
            totals["serial_zero"] += 1
        else:
            totals["serial_nonzero"] += 1
            class_name = str(obj.get("class_name") or "<unknown>")
            serial_classes[class_name] = serial_classes.get(class_name, 0) + 1
            if len(nonzero_serial_samples) < sample_limit:
                nonzero_serial_samples.append(_sample_object(obj))

        if flags & 0x100:
            totals["flags_0x100"] += 1
        if flags & 0x4000:
            totals["flags_0x4000"] += 1
        if flags & 0x8000:
            totals["flags_0x8000"] += 1
        if flags & sum(UOBJECT_VALIDITY_MASKS):
            totals["flags_any"] += 1
            if len(flag_mask_samples) < sample_limit:
                flag_mask_samples.append(_sample_object(obj))
            if membership_pass and serial not in (None, 0) and len(flag_rejection_candidate_samples) < sample_limit:
                flag_rejection_candidate_samples.append(_flag_rejection_candidate(obj))
        else:
            totals["flags_none_of_masks"] += 1

        if obj.get("internal_index_matches") is not True:
            totals["internal_index_mismatch"] += 1

        if (
            serial in (None, 0)
            or not membership_pass
            or (flags & sum(UOBJECT_VALIDITY_MASKS)) == 0
        ) and len(negative_samples) < sample_limit:
            negative_samples.append(_sample_object(obj))

    return {
        "totals": totals,
        "top_nonzero_serial_classes": sorted(
            serial_classes.items(),
            key=lambda item: (-item[1], item[0]),
        )[:30],
        "nonzero_serial_samples": nonzero_serial_samples,
        "flag_mask_samples": flag_mask_samples,
        "flag_rejection_candidate_samples": flag_rejection_candidate_samples,
        "negative_samples": negative_samples,
    }


def consume_gate_expectation(
    summary: dict[str, Any],
    *,
    core_sha256_verified: bool,
    binary_sha256: str | None,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not core_sha256_verified:
        blockers.append("core_sha256_not_verified")
    if binary_sha256 is None:
        blockers.append("binary_sha256_missing")
    if not summary.get("flag_rejection_candidate_samples"):
        blockers.append("missing_flag_rejection_candidate_samples")
    return {
        "schema": CONSUME_GATE_EXPECTATION_SCHEMA,
        "consume_ready": not blockers,
        "promote_ready": False,
        "blockers": blockers,
        "non_claims": [
            "internal offline scan only",
            "does not promote ResourceHandle, object identity, lookup, mutation, or return override",
        ],
    }


def build_report(
    core: Path,
    *,
    gobjects: int,
    fname_root_slot: int,
    max_objects: int,
    label: str | None,
    core_sha256: str | None,
    binary_sha256: str | None,
    sample_limit: int,
    resolve_names: bool = True,
    argv: list[str] | None = None,
    obelisk_commit: str | None = None,
) -> dict[str, Any]:
    observed_core_sha256 = sha256_file(core)
    if core_sha256 is not None and observed_core_sha256 != core_sha256:
        raise SystemExit(
            f"--core-sha256 mismatch: expected {core_sha256} observed {observed_core_sha256}"
        )

    memory = uobjects.CoreMemory(core)
    try:
        metadata, objects = uobjects.iter_uobjects(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            max_objects=max_objects,
            resolve_names=resolve_names,
        )
    finally:
        memory.close()

    summary = summarize_objects(objects, sample_limit=sample_limit)
    gate_expectation = consume_gate_expectation(
        summary,
        core_sha256_verified=core_sha256 is not None,
        binary_sha256=binary_sha256,
    )
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_blocked",
        "evidence_kind": "internal_offline_scan_candidate",
        "source_label": label,
        "core_path": str(core),
        "core_sha256": observed_core_sha256,
        "core_sha256_verified": core_sha256 is not None,
        "binary_sha256": binary_sha256,
        "gobjects": f"0x{gobjects:x}",
        "fname_root_slot": f"0x{fname_root_slot:x}",
        "scan_limit": max_objects,
        "provenance": {
            "schema": PROVENANCE_SCHEMA,
            "producer": "scan_resource_handle_serials.py",
            "tool_path": "scripts/scan_resource_handle_serials.py",
            "verified": True,
            "path_redacted": True,
            "argv": redact_argv(argv or []),
            "obelisk_commit": obelisk_commit,
            "core_sha256_verified": core_sha256 is not None,
            "core_sha256": observed_core_sha256,
            "binary_sha256": binary_sha256,
            "gobjects": f"0x{gobjects:x}",
            "fname_root_slot": f"0x{fname_root_slot:x}",
            "scan_limit": max_objects,
            "name_resolution": "enabled" if resolve_names else "disabled",
        },
        "metadata": metadata,
        **summary,
        "consume_gate_expectation": gate_expectation,
        "interpretation": {
            "item_dword_0x8": (
                "nonzero samples support serial-backed FUObjectItem+0x8 for internal tooling"
                if summary["totals"]["serial_nonzero"] > 0
                else "no nonzero samples found in this scan window"
            ),
            "uobject_flags_masks": (
                "coherent 0x100/0x4000/0x8000 candidate rejection samples found; semantics still require classification"
                if summary["flag_rejection_candidate_samples"]
                else "0x100/0x4000/0x8000 masks found only without coherent nonzero-serial membership; lifetime flag semantics still unproven"
                if summary["totals"]["flags_any"] > 0
                else "no 0x100/0x4000/0x8000 samples found in this scan window; lifetime flag semantics still unproven"
            ),
            "public_resource_handle_ready": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline FUObjectItem serial/UObject flag scan.")
    parser.add_argument("--core", required=True, type=Path)
    parser.add_argument("--gobjects", type=parse_int)
    parser.add_argument("--fname-root-slot", type=parse_int)
    parser.add_argument("--max-objects", type=int, default=200000)
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    parser.add_argument("--label")
    parser.add_argument("--core-sha256")
    parser.add_argument("--binary-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--offline-root", type=Path, default=DEFAULT_OFFLINE_ROOT)
    parser.add_argument("--obelisk-commit")
    parser.add_argument(
        "--skip-name-resolution",
        action="store_true",
        help="Skip FName/class-name resolution while preserving serial, flag, and membership evidence.",
    )
    parser.add_argument(
        "--gate-ready",
        action="store_true",
        help=(
            "Require explicit hash/address/output inputs and offline-root paths before scanning; "
            "also exits non-zero unless consume_gate_expectation.consume_ready is true."
        ),
    )
    parser.add_argument(
        "--require-consume-ready",
        action="store_true",
        help="Exit non-zero unless the emitted report has the fields needed for consume-mode gate acceptance.",
    )
    return parser.parse_args()


def validate_gate_ready_args(args: argparse.Namespace, *, core: Path, output: Path | None) -> None:
    missing: list[str] = []
    if args.core_sha256 is None:
        missing.append("--core-sha256")
    if args.binary_sha256 is None:
        missing.append("--binary-sha256")
    if args.gobjects is None:
        missing.append("--gobjects")
    if args.fname_root_slot is None:
        missing.append("--fname-root-slot")
    if output is None:
        missing.append("--output")
    if missing:
        raise SystemExit("--gate-ready requires explicit " + ", ".join(missing))

    offline_root = args.offline_root.expanduser().resolve()
    if not is_relative_to(core, offline_root):
        raise SystemExit(f"--gate-ready requires --core under --offline-root: {core} not under {offline_root}")
    if output is not None and not is_relative_to(output, offline_root):
        raise SystemExit(f"--gate-ready requires --output under --offline-root: {output} not under {offline_root}")


def main() -> int:
    args = parse_args()
    if args.max_objects < 0:
        raise SystemExit("--max-objects must be non-negative")
    if args.sample_limit < 0:
        raise SystemExit("--sample-limit must be non-negative")
    if args.core_sha256 is not None and SHA256_RE.fullmatch(args.core_sha256) is None:
        raise SystemExit("--core-sha256 must be a lowercase 64-character SHA256")
    if args.binary_sha256 is not None and SHA256_RE.fullmatch(args.binary_sha256) is None:
        raise SystemExit("--binary-sha256 must be a lowercase 64-character SHA256")

    core = reject_protected_input_path(args.core, "--core")
    output = reject_protected_output_path(args.output, "--output") if args.output else None
    if args.gate_ready:
        validate_gate_ready_args(args, core=core, output=output)
    gobjects = args.gobjects if args.gobjects is not None else uobjects.DEFAULT_GOBJECTS
    fname_root_slot = args.fname_root_slot if args.fname_root_slot is not None else uobjects.DEFAULT_FNAME_ROOT_SLOT
    report = build_report(
        core,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        max_objects=args.max_objects,
        label=args.label,
        core_sha256=args.core_sha256,
        binary_sha256=args.binary_sha256,
        sample_limit=args.sample_limit,
        resolve_names=not args.skip_name_resolution,
        argv=sys.argv,
        obelisk_commit=args.obelisk_commit,
    )
    if (args.require_consume_ready or args.gate_ready) and not report["consume_gate_expectation"]["consume_ready"]:
        blockers = ", ".join(report["consume_gate_expectation"]["blockers"])
        raise SystemExit(f"resource-handle serial scan is not consume-ready: {blockers}")

    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
