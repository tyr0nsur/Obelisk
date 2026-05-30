#!/usr/bin/env python3
"""Build a machine-readable two-core GObjects reconciliation manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from snapshot_evidence_pack import (  # noqa: E402
    SHA256_RE,
    reject_protected_input_path,
    reject_protected_output_path,
    sha256_file,
)


SCHEMA = "obelisk.gobjects-two-core-manifest.v1"
RECONCILIATION_SCHEMA = "obelisk.gobjects-sample-reconciliation.v1"
BLOCKED_CONTRACTS = [
    "runtime-stable object identity",
    "ResourceHandle",
    "raw UObject exposure",
    "lookup API",
    "mutation",
    "return override",
    "serial reuse/invalidation semantics",
]


def parse_role_report(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--report must use ROLE=PATH")
    role, raw_path = value.split("=", 1)
    role = role.strip()
    if not role:
        raise argparse.ArgumentTypeError("--report role must not be empty")
    return role, Path(raw_path)


def validate_sha(value: str, label: str) -> str:
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{label} must be a lowercase 64-character SHA256")
    return value


def load_report(path: Path) -> dict[str, object]:
    resolved = reject_protected_input_path(path, "--report")
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if payload.get("schema") != RECONCILIATION_SCHEMA:
        raise SystemExit(f"{resolved}: unsupported schema")
    if not isinstance(payload.get("inputs"), dict):
        raise SystemExit(f"{resolved}: missing inputs object")
    if not isinstance(payload.get("summary"), dict):
        raise SystemExit(f"{resolved}: missing summary object")
    if not isinstance(payload.get("samples"), list):
        raise SystemExit(f"{resolved}: missing samples list")
    payload["_resolved_path"] = str(resolved)
    return payload


def report_sample_set(report: dict[str, object]) -> list[dict[str, object]]:
    inputs = report["inputs"]
    assert isinstance(inputs, dict)
    samples = inputs.get("sample_indices")
    if not isinstance(samples, list):
        raise SystemExit(f"{report['_resolved_path']}: missing inputs.sample_indices")
    result: list[dict[str, object]] = []
    for sample in samples:
        if not isinstance(sample, dict):
            raise SystemExit(f"{report['_resolved_path']}: sample index entries must be objects")
        label = sample.get("label")
        index = sample.get("index")
        if not isinstance(label, str) or not isinstance(index, int):
            raise SystemExit(f"{report['_resolved_path']}: sample index entry missing label/index")
        result.append({"label": label, "index": index})
    return result


def require_same_inputs(reports: list[dict[str, object]]) -> tuple[str, str, list[dict[str, object]]]:
    first = reports[0]
    first_inputs = first["inputs"]
    assert isinstance(first_inputs, dict)
    gobjects = first_inputs.get("gobjects_candidate")
    fname_root_slot = first_inputs.get("fname_root_slot")
    sample_set = report_sample_set(first)
    if not isinstance(gobjects, str) or not isinstance(fname_root_slot, str):
        raise SystemExit(f"{first['_resolved_path']}: missing gobjects_candidate/fname_root_slot")

    for report in reports[1:]:
        inputs = report["inputs"]
        assert isinstance(inputs, dict)
        if inputs.get("gobjects_candidate") != gobjects:
            raise SystemExit("reports do not use the same gobjects_candidate")
        if inputs.get("fname_root_slot") != fname_root_slot:
            raise SystemExit("reports do not use the same fname_root_slot")
        if report_sample_set(report) != sample_set:
            raise SystemExit("reports do not use the same sample set")
    return gobjects, fname_root_slot, sample_set


def summarize_report(role: str, report: dict[str, object], *, hash_core: bool) -> dict[str, object]:
    summary = report["summary"]
    assert isinstance(summary, dict)
    core_path_raw = report.get("core")
    if not isinstance(core_path_raw, str):
        raise SystemExit(f"{report['_resolved_path']}: missing core path")
    core_path = reject_protected_input_path(Path(core_path_raw), f"{report['_resolved_path']}: core")

    required = {
        "sample_count": len(report_sample_set(report)),
        "accepted_count": len(report_sample_set(report)),
        "rejected_count": 0,
        "membership_pass_count": len(report_sample_set(report)),
    }
    for key, expected in required.items():
        if summary.get(key) != expected:
            raise SystemExit(f"{report['_resolved_path']}: {key} expected {expected}, got {summary.get(key)}")

    return {
        "role": role,
        "core_path": str(core_path),
        "core_sha256": sha256_file(core_path) if hash_core else None,
        "reconciliation_path": str(report["_resolved_path"]),
        "schema": report.get("schema"),
        "sample_count": summary.get("sample_count"),
        "accepted_count": summary.get("accepted_count"),
        "rejected_count": summary.get("rejected_count"),
        "membership_pass_count": summary.get("membership_pass_count"),
        "promotion_status": summary.get("promotion_status"),
    }


def build_manifest(args: argparse.Namespace) -> dict[str, object]:
    if len(args.report) < 2:
        raise SystemExit("at least two --report ROLE=PATH entries are required")
    binary_sha256 = validate_sha(args.binary_sha256, "--binary-sha256")

    role_reports = [(role, load_report(path)) for role, path in args.report]
    seen_roles: set[str] = set()
    for role, _report in role_reports:
        if role in seen_roles:
            raise SystemExit(f"duplicate report role: {role}")
        seen_roles.add(role)

    gobjects, fname_root_slot, sample_set = require_same_inputs([report for _role, report in role_reports])
    cores = [summarize_report(role, report, hash_core=not args.no_core_hash) for role, report in role_reports]

    return {
        "schema": SCHEMA,
        "binary_sha256": binary_sha256,
        "gobjects_candidate": gobjects,
        "fname_root_slot": fname_root_slot,
        "sample_set": sample_set,
        "core_count": len(cores),
        "cores": cores,
        "offline_only": True,
        "ufunction_inventory_input_ready": True,
        "public_gobjects_promotion_ready": False,
        "blocked_contracts": BLOCKED_CONTRACTS,
        "non_claims": [
            "This manifest is an offline input readiness artifact.",
            "It does not promote GObjects/GUObjectArray as runtime-stable.",
            "It does not expose UObject pointers, raw params, object identity, mutation, or return overrides.",
            "It does not prove ResourceHandle lifetime or serial reuse semantics.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an offline two-core GObjects manifest.")
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--report", action="append", type=parse_role_report, default=[], metavar="ROLE=PATH")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--no-core-hash",
        action="store_true",
        help="Do not hash core files; intended only for tests or already-hashed external manifests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = reject_protected_output_path(args.output, "--output")
    if output.exists() and output.is_symlink():
        raise SystemExit(f"--output must not be a symlink: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest(args)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
