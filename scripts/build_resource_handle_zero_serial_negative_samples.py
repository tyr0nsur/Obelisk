#!/usr/bin/env python3
"""Build a minimal offline zero-serial FUObjectItem negative cohort.

This is candidate-only ResourceHandle research. It reads copied core artifacts,
collects deterministic FUObjectItem entries whose object pointer is present and
whose candidate serial dword at +0x8 is zero, and contrasts them with a known
nonzero serial anchor. It does not expose lookup or promote ResourceHandle.
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
from snapshot_evidence_pack import SHA256_RE, reject_protected_input_path  # noqa: E402


REPORT_SCHEMA = "obelisk.resource-handle-zero-serial-negative-samples.v1"
DEFAULT_ANCHOR_INDEX = 50834
DEFAULT_NEGATIVE_LIMIT = 8


def parse_int(value: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer/address: {value}") from exc


def parse_labeled_value(value: str, *, kind: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"{kind} must be LABEL=VALUE")
    label, raw = value.split("=", 1)
    label = label.strip()
    if not label:
        raise argparse.ArgumentTypeError(f"{kind} label must be non-empty")
    if raw == "":
        raise argparse.ArgumentTypeError(f"{kind} value must be non-empty")
    return label, raw


def parse_core_arg(value: str) -> tuple[str, Path]:
    label, raw_path = parse_labeled_value(value, kind="--core")
    return label, Path(raw_path)


def parse_hash_arg(value: str) -> tuple[str, str]:
    label, digest = parse_labeled_value(value, kind="--core-sha256")
    if SHA256_RE.fullmatch(digest) is None:
        raise argparse.ArgumentTypeError("--core-sha256 values must be lowercase 64-character SHA256")
    return label, digest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def membership_status(sample: dict[str, Any]) -> str:
    if sample.get("address") in (None, "", "0x0", 0):
        return "missing-uobject-address"
    if sample.get("internal_index_matches") is not True:
        return "internal-index-mismatch"
    return "candidate-uobject"


def sample_from_item(
    memory: uobjects.CoreMemory,
    *,
    index: int,
    item_address: int,
    object_address: int,
    fname_table: int | None,
    resolve_names: bool,
) -> dict[str, Any] | None:
    uobject = uobjects.read_uobject(
        memory,
        object_address,
        fname_table,
        resolve_names=resolve_names,
    )
    if uobject is None:
        return None

    sample = {
        "index": index,
        "address": f"0x{object_address:x}",
        "class_name": uobject.get("class_name"),
        "name": uobject.get("name"),
        "flags": uobject.get("flags"),
        "fuobject_item": f"0x{item_address:x}",
        "item_dword_0x8": uobjects.read_u32(memory, item_address + 0x8),
        "item_dword_0xC": uobjects.read_i32(memory, item_address + 0xC),
        "internal_index": uobject.get("internal_index"),
        "internal_index_matches": uobject.get("internal_index") == index,
    }
    sample["membership"] = membership_status(sample)
    sample["membership_pass"] = sample["membership"] == "candidate-uobject"
    return sample


def collect_samples(
    memory: uobjects.CoreMemory,
    *,
    gobjects: int,
    fname_root_slot: int,
    anchor_index: int,
    negative_limit: int,
    max_scan_index: int,
    resolve_names: bool,
) -> dict[str, Any]:
    if negative_limit < 0:
        raise ValueError("negative_limit must be non-negative")
    if anchor_index < 0:
        raise ValueError("anchor_index must be non-negative")
    if max_scan_index < anchor_index:
        raise ValueError("max_scan_index must be >= anchor_index")

    chunks = memory.read_ptr(gobjects + uobjects.GOBJECTS_CHUNKS_OFFSET)
    object_count = uobjects.read_i32(memory, gobjects + uobjects.GOBJECTS_COUNT_OFFSET)
    fname_table = memory.read_ptr(fname_root_slot)
    metadata = {
        "gobjects": f"0x{gobjects:x}",
        "fname_root_slot": f"0x{fname_root_slot:x}",
        "fname_table": f"0x{fname_table:x}" if fname_table else None,
        "chunks": f"0x{chunks:x}" if chunks else None,
        "object_count": object_count,
        "anchor_index": anchor_index,
        "max_scan_index": max_scan_index,
        "name_resolution": "enabled" if resolve_names else "disabled",
    }
    if not chunks or object_count is None or object_count <= 0:
        return {
            "metadata": metadata,
            "scan_totals": {
                "indices_scanned": 0,
                "nonnull_items_seen": 0,
                "candidate_uobjects_seen": 0,
            },
            "zero_serial_negative_samples": [],
            "positive_anchor": None,
        }

    negative_samples: list[dict[str, Any]] = []
    positive_anchor: dict[str, Any] | None = None
    nonnull_items_seen = 0
    candidate_uobjects_seen = 0
    scan_limit = min(object_count, max_scan_index + 1)

    for index in range(scan_limit):
        chunk = memory.read_ptr(chunks + (index // uobjects.GOBJECTS_CHUNK_SIZE) * 8)
        if not chunk:
            continue

        item_address = chunk + (index % uobjects.GOBJECTS_CHUNK_SIZE) * uobjects.FUOBJECT_ITEM_SIZE
        object_address = memory.read_ptr(item_address)
        if not object_address:
            continue
        nonnull_items_seen += 1

        sample = sample_from_item(
            memory,
            index=index,
            item_address=item_address,
            object_address=object_address,
            fname_table=fname_table,
            resolve_names=resolve_names,
        )
        if sample is None:
            continue
        candidate_uobjects_seen += 1

        if index == anchor_index:
            positive_anchor = sample
        if (
            sample["item_dword_0x8"] == 0
            and sample["membership_pass"]
            and len(negative_samples) < negative_limit
        ):
            negative_samples.append(sample)

    return {
        "metadata": metadata,
        "scan_totals": {
            "indices_scanned": scan_limit,
            "nonnull_items_seen": nonnull_items_seen,
            "candidate_uobjects_seen": candidate_uobjects_seen,
        },
        "zero_serial_negative_samples": negative_samples,
        "positive_anchor": positive_anchor,
    }


def build_source_report(
    *,
    label: str,
    core: Path,
    expected_core_sha256: str | None,
    gobjects: int,
    fname_root_slot: int,
    anchor_index: int,
    negative_limit: int,
    max_scan_index: int,
    resolve_names: bool,
) -> dict[str, Any]:
    observed_core_sha256 = sha256_file(core)
    if expected_core_sha256 is not None and observed_core_sha256 != expected_core_sha256:
        raise SystemExit(
            f"{label}: --core-sha256 mismatch: expected {expected_core_sha256} observed {observed_core_sha256}"
        )

    memory = uobjects.CoreMemory(core)
    try:
        sample_report = collect_samples(
            memory,
            gobjects=gobjects,
            fname_root_slot=fname_root_slot,
            anchor_index=anchor_index,
            negative_limit=negative_limit,
            max_scan_index=max_scan_index,
            resolve_names=resolve_names,
        )
    finally:
        memory.close()

    anchor = sample_report["positive_anchor"]
    blockers: list[str] = []
    if len(sample_report["zero_serial_negative_samples"]) < negative_limit:
        blockers.append("zero_serial_negative_sample_limit_not_met")
    if anchor is None:
        blockers.append("positive_anchor_missing")
    elif anchor.get("item_dword_0x8") in (None, 0):
        blockers.append("positive_anchor_serial_not_nonzero")
    if expected_core_sha256 is None:
        blockers.append("core_sha256_not_provided")

    return {
        "source_label": label,
        "core_path": str(core),
        "core_sha256": observed_core_sha256,
        "core_sha256_verified": expected_core_sha256 is not None,
        **sample_report,
        "deterministic_negative_cohort": not blockers,
        "blockers": blockers,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    cores = [parse_core_arg(value) for value in args.core]
    labels = [label for label, _path in cores]
    if len(set(labels)) != len(labels):
        raise SystemExit("--core labels must be unique")

    expected_hashes = dict(parse_hash_arg(value) for value in args.core_sha256)
    unknown_hash_labels = sorted(set(expected_hashes) - set(labels))
    if unknown_hash_labels:
        raise SystemExit("--core-sha256 labels without matching --core: " + ", ".join(unknown_hash_labels))

    max_scan_index = args.max_scan_index if args.max_scan_index is not None else args.anchor_index
    sources = [
        build_source_report(
            label=label,
            core=reject_protected_input_path(path, "--core"),
            expected_core_sha256=expected_hashes.get(label),
            gobjects=args.gobjects,
            fname_root_slot=args.fname_root_slot,
            anchor_index=args.anchor_index,
            negative_limit=args.negative_limit,
            max_scan_index=max_scan_index,
            resolve_names=not args.skip_name_resolution,
        )
        for label, path in cores
    ]
    deterministic = all(source["deterministic_negative_cohort"] for source in sources)
    return {
        "schema": REPORT_SCHEMA,
        "status": "candidate_blocked",
        "evidence_kind": "internal_offline_zero_serial_negative_samples",
        "deterministic_negative_cohort": deterministic,
        "sources": sources,
        "serial_candidate_field": {
            "offset": "FUObjectItem+0x8",
            "width": "uint32",
            "accepted_positive_anchor": f"index {args.anchor_index} nonzero serial",
        },
        "non_claims": [
            "candidate-only offline evidence",
            "does not prove runtime reuse, wraparound, UObject flag validity, lookup, mutation, or public ResourceHandle",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build candidate-only zero-serial FUObjectItem negative samples from copied cores."
    )
    parser.add_argument("--core", action="append", required=True, help="LABEL=/path/to/copied/core")
    parser.add_argument("--core-sha256", action="append", default=[], help="LABEL=lowercase_sha256")
    parser.add_argument("--gobjects", type=parse_int, default=uobjects.DEFAULT_GOBJECTS)
    parser.add_argument("--fname-root-slot", type=parse_int, default=uobjects.DEFAULT_FNAME_ROOT_SLOT)
    parser.add_argument("--anchor-index", type=int, default=DEFAULT_ANCHOR_INDEX)
    parser.add_argument("--negative-limit", type=int, default=DEFAULT_NEGATIVE_LIMIT)
    parser.add_argument("--max-scan-index", type=int)
    parser.add_argument(
        "--skip-name-resolution",
        action="store_true",
        help="Skip class/name resolution while preserving serial, flag, and membership evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.anchor_index < 0:
        raise SystemExit("--anchor-index must be non-negative")
    if args.negative_limit < 0:
        raise SystemExit("--negative-limit must be non-negative")
    if args.max_scan_index is not None and args.max_scan_index < args.anchor_index:
        raise SystemExit("--max-scan-index must be >= --anchor-index")

    print(json.dumps(build_report(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
