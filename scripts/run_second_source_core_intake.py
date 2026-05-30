#!/usr/bin/env python3
"""Plan or run the minimal offline second-source core intake."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

from artifact_identity import ARTIFACT_IDENTITY_KEYS, is_safe_artifact_id, is_sha256
from reflection_target_sets import TARGET_SETS, schema_targets


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_OUTPUT_ROOTS = (Path("/servidor/ark"),)
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
DEFAULT_FNAME_INDICES = (
    "None=0",
    "ClientMessage=4884",
    "ServerChat=9619",
    "SetActiveMissionDebugFlags=9622",
)
DEFAULT_FNAME_INDEX_LABELS = frozenset(item.split("=", 1)[0] for item in DEFAULT_FNAME_INDICES)
DEFAULT_GOBJECTS_SAMPLE_INDICES = ("0", "1", "25447")
DEFAULT_TARGET_SET = "minimal-second-source-intake"
DEFAULT_BASE_ROOT = "tests/fixtures/ufunction_snapshots"
UFUNCTION_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
SNAPSHOT_COMPARISON_REPORT = "readiness-report.json"
SNAPSHOT_COMPARISON_STDERR = "readiness-report.stderr.txt"
READINESS_SCHEMA = "obelisk.reflection-snapshot-readiness.v1"
READINESS_GATE_MODE = "second_source_promotion"
READINESS_EVIDENCE_SCOPE = "second_source_layout_evidence_only"
REQUIRED_READINESS_NON_PROMOTED_SURFACES = {
    "class_identity",
    "cross_binary_portability",
    "inventory_identity",
    "item_identity",
    "lookup",
    "mutation",
    "object_identity",
    "public_sdk",
    "raw_params",
    "resource_handle",
    "return_override",
    "runtime_hooks",
}
ALLOWED_ARTIFACT_KINDS = {"offline_core"}


class ReadinessReportError(ValueError):
    """Raised when persisted readiness JSON is not acceptable for promotion."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute the minimal offline second-source intake for an already "
            "approved independent ARK core artifact. The default mode prints commands "
            "only and never touches live servers."
        )
    )
    parser.add_argument("--binary", required=True, help="Matching ShooterGameServer binary path.")
    parser.add_argument("--core", required=True, help="Independent core artifact path.")
    parser.add_argument("--pack-dir", required=True, help="Evidence pack output directory.")
    parser.add_argument(
        "--snapshot-root",
        help="Output root for regenerated candidate UFunction snapshots.",
    )
    parser.add_argument(
        "--verified-fname-root-slot",
        help="Artifact-specific verified FName root slot address, for example 0x1234.",
    )
    parser.add_argument(
        "--gobjects-candidate",
        help="Artifact-specific GObjects candidate address, for example 0x595b7e0.",
    )
    parser.add_argument(
        "--fname-index",
        action="append",
        default=[],
        metavar="LABEL=INDEX",
        help=(
            "FName clue to pass while scanning the artifact. Repeatable. Defaults to "
            "the current stable clue set."
        ),
    )
    parser.add_argument(
        "--gobjects-sample-index",
        action="append",
        default=[],
        metavar="INDEX",
        help="GObjects sample index. Repeatable. Defaults to 0, 1, and 25447.",
    )
    parser.add_argument(
        "--target-set",
        default=DEFAULT_TARGET_SET,
        help="UFunction target set to regenerate and compare.",
    )
    parser.add_argument(
        "--base-root",
        default=DEFAULT_BASE_ROOT,
        help="Committed primary UFunction snapshot root.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the commands. Without this flag, only print the reproducible plan.",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help=(
            "Only build the initial FName table scan evidence pack. Use this before an "
            "artifact-specific FName root and GObjects candidate have been reviewed."
        ),
    )
    parser.add_argument(
        "--json-plan",
        action="store_true",
        help="Print the command plan as JSON for review artifacts. Incompatible with --execute.",
    )
    return parser.parse_args()


def rel_or_abs(path: str) -> str:
    return str(Path(path).expanduser())


def require_existing_file(path: str, label: str) -> None:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise SystemExit(f"{label} must exist before --execute: {candidate}")


def require_ignored_output_path(path: str, label: str) -> None:
    candidate = Path(path).expanduser().resolve()
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError:
        return
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(relative), f"{relative}/"],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"{label} is inside the repository but is not ignored by Git: {candidate}"
        )


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def is_approved_offline_workspace_path(path: Path) -> bool:
    expanded = path.expanduser()
    resolved = path.resolve()
    return any(
        expanded.is_absolute()
        and is_relative_to(expanded, root)
        and is_relative_to(resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    )


def reject_protected_output_path(path: str, label: str) -> None:
    expanded = Path(path).expanduser()
    for root in PROTECTED_OUTPUT_ROOTS:
        if expanded.is_absolute() and is_relative_to(expanded, root) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not write under protected server root {root}: {expanded}")
    candidate = expanded.resolve()
    for root in PROTECTED_OUTPUT_ROOTS:
        if is_relative_to(candidate, root.resolve()) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not write under protected server root {root}: {candidate}")


def reject_protected_input_path(path: str, label: str) -> None:
    expanded = Path(path).expanduser()
    for root in PROTECTED_OUTPUT_ROOTS:
        if expanded.is_absolute() and is_relative_to(expanded, root) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not read from protected server root {root}: {expanded}")
    candidate = expanded.resolve()
    for root in PROTECTED_OUTPUT_ROOTS:
        if is_relative_to(candidate, root.resolve()) and not is_approved_offline_workspace_path(expanded):
            raise SystemExit(f"{label} must not read from protected server root {root}: {candidate}")


def parse_nonnegative_int(value: str, label: str) -> int:
    try:
        parsed = int(value, 0)
    except ValueError as exc:
        raise SystemExit(f"{label} must be an integer/address: {value}") from exc
    if parsed < 0:
        raise SystemExit(f"{label} must be non-negative: {value}")
    return parsed


def merged_fname_indices(extra_indices: list[str]) -> list[str]:
    merged = list(DEFAULT_FNAME_INDICES)
    seen_labels = set(DEFAULT_FNAME_INDEX_LABELS)
    for item in extra_indices:
        label, _index = parse_labeled_index(item, "--fname-index")
        if label in seen_labels:
            raise SystemExit(f"--fname-index duplicates required FName clue: {label}")
        seen_labels.add(label)
        merged.append(item)
    return merged


def validate_unlabeled_address(value: str | None, label: str) -> None:
    if value is None:
        return
    if "=" in value:
        raise SystemExit(f"{label} expects a raw address, not LABEL=ADDR: {value}")
    parse_nonnegative_int(value, label)


def validate_fname_index(value: str) -> None:
    if "=" in value:
        name, raw_index = value.split("=", 1)
        if not name.strip():
            raise SystemExit("--fname-index label must not be empty")
        parse_nonnegative_int(raw_index, "--fname-index")
        return
    parse_nonnegative_int(value, "--fname-index")


def parse_labeled_index(value: str, label: str) -> tuple[str, int]:
    if "=" in value:
        name, raw_index = value.split("=", 1)
        name = name.strip()
        if not name:
            raise SystemExit(f"{label} label must not be empty")
        return name, parse_nonnegative_int(raw_index, label)
    index = parse_nonnegative_int(value, label)
    return f"fname_{index}", index


def preflight_execute(args: argparse.Namespace) -> None:
    require_existing_file(args.binary, "--binary")
    require_existing_file(args.core, "--core")
    require_ignored_output_path(args.pack_dir, "--pack-dir")
    if not args.scan_only:
        require_ignored_output_path(args.snapshot_root, "--snapshot-root")


def validate_args(args: argparse.Namespace) -> None:
    if args.json_plan and args.execute:
        raise SystemExit("--json-plan is a dry-run review artifact and cannot be combined with --execute")
    reject_protected_input_path(args.binary, "--binary")
    reject_protected_input_path(args.core, "--core")
    reject_protected_output_path(args.pack_dir, "--pack-dir")
    for item in args.fname_index:
        validate_fname_index(item)
    for item in args.gobjects_sample_index:
        parse_nonnegative_int(item, "--gobjects-sample-index")
    if args.scan_only:
        incompatible = []
        if args.snapshot_root:
            incompatible.append("--snapshot-root")
        if args.verified_fname_root_slot:
            incompatible.append("--verified-fname-root-slot")
        if args.gobjects_candidate:
            incompatible.append("--gobjects-candidate")
        if args.gobjects_sample_index:
            incompatible.append("--gobjects-sample-index")
        if args.target_set != DEFAULT_TARGET_SET:
            incompatible.append("--target-set")
        if args.base_root != DEFAULT_BASE_ROOT:
            incompatible.append("--base-root")
        if incompatible:
            raise SystemExit(
                "--scan-only cannot be combined with full-intake arguments: "
                + ", ".join(incompatible)
            )
        return
    if args.target_set not in TARGET_SETS:
        raise SystemExit(
            "--target-set must be one of: " + ", ".join(sorted(TARGET_SETS))
        )
    if not schema_targets(args.target_set, UFUNCTION_SCHEMA):
        raise SystemExit(f"--target-set {args.target_set!r} has no UFunction snapshot targets")
    reject_protected_input_path(args.base_root, "--base-root")
    missing = []
    if not args.snapshot_root:
        missing.append("--snapshot-root")
    if not args.verified_fname_root_slot:
        missing.append("--verified-fname-root-slot")
    if not args.gobjects_candidate:
        missing.append("--gobjects-candidate")
    if missing:
        raise SystemExit(
            "full intake requires these arguments unless --scan-only is used: "
            + ", ".join(missing)
        )
    validate_unlabeled_address(args.verified_fname_root_slot, "--verified-fname-root-slot")
    validate_unlabeled_address(args.gobjects_candidate, "--gobjects-candidate")
    reject_protected_output_path(args.snapshot_root, "--snapshot-root")


def build_commands(args: argparse.Namespace) -> list[list[str]]:
    pack_dir = rel_or_abs(args.pack_dir)
    scan_pack_dir = str(Path(pack_dir) / "fname-scan")
    root_validation_pack_dir = str(Path(pack_dir) / "fname-root-validation")
    sample_pack_dir = str(Path(pack_dir) / "gobjects-sampling")
    manifest = str(Path(sample_pack_dir) / "manifest.json")
    fname_indices = merged_fname_indices(args.fname_index)
    sample_indices = args.gobjects_sample_index or list(DEFAULT_GOBJECTS_SAMPLE_INDICES)

    scan_command = [
        "python3",
        "scripts/build_core_dump_evidence_pack.py",
        "--binary",
        rel_or_abs(args.binary),
        "--core",
        rel_or_abs(args.core),
        "--output-dir",
        scan_pack_dir,
        "--scan-fname-tables",
        "--no-default-candidates",
        "--no-default-fname-roots",
        "--no-default-fname-indices",
    ]
    for item in fname_indices:
        scan_command.extend(["--fname-index", item])

    if args.scan_only:
        return [scan_command]

    root_validation_command = [
        "python3",
        "scripts/scan_core_fname_tables.py",
        "--core",
        rel_or_abs(args.core),
        "--root-slot",
        args.verified_fname_root_slot,
        "--require-exact-root",
        "--no-default-indices",
        "--json",
        "--json-out",
        str(Path(root_validation_pack_dir) / "core.fname-root-validation.json"),
    ]
    for item in fname_indices:
        root_validation_command.extend(["--index", item])

    sample_command = [
        "python3",
        "scripts/build_core_dump_evidence_pack.py",
        "--binary",
        rel_or_abs(args.binary),
        "--core",
        rel_or_abs(args.core),
        "--output-dir",
        sample_pack_dir,
        "--no-default-candidates",
        "--no-default-fname-roots",
        "--fname-root-slot",
        f"verified_fname_root_slot={args.verified_fname_root_slot}",
        "--gobjects-candidate",
        f"gobjects={args.gobjects_candidate}",
    ]
    for item in sample_indices:
        sample_command.extend(["--gobjects-sample-index", item])

    regenerate_command = [
        "python3",
        "scripts/regenerate_ufunction_snapshots.py",
        "--core",
        rel_or_abs(args.core),
        "--evidence-pack-manifest",
        manifest,
        "--output-root",
        rel_or_abs(args.snapshot_root),
        "--target-set",
        args.target_set,
        "--write",
    ]

    compare_command = [
        "python3",
        "scripts/compare_reflection_snapshots.py",
        "--base-root",
        rel_or_abs(args.base_root),
        "--candidate-root",
        rel_or_abs(args.snapshot_root),
        "--target-set",
        args.target_set,
        "--readiness-report",
        "--fail-on-readiness-gaps",
        "--json",
    ]

    return [root_validation_command, sample_command, regenerate_command, compare_command]


def phase_output_dirs(args: argparse.Namespace) -> dict[str, str | None]:
    pack_dir = Path(rel_or_abs(args.pack_dir))
    scan_only = args.scan_only
    return {
        "fname_table_scan": str(pack_dir / "fname-scan") if scan_only else None,
        "fname_root_validation": None if scan_only else str(pack_dir / "fname-root-validation"),
        "gobjects_sampling": None if scan_only else str(pack_dir / "gobjects-sampling"),
        "snapshot_comparison": None if scan_only else str(pack_dir / "snapshot-comparison"),
    }


def phase_order(args: argparse.Namespace) -> list[str]:
    if args.scan_only:
        return ["fname_table_scan"]
    return [
        "fname_root_validation",
        "gobjects_sampling",
        "ufunction_snapshot_regeneration",
        "snapshot_comparison",
    ]


def build_plan(args: argparse.Namespace, commands: list[list[str]]) -> dict[str, object]:
    scan_only = args.scan_only
    phases = phase_order(args)
    output_dirs = phase_output_dirs(args)
    return {
        "schema": "obelisk.second-source-core-intake-plan.v1",
        "mode": "scan-only" if scan_only else "full-intake",
        "execute": False,
        "repo_root": str(REPO_ROOT),
        "phase_output_dirs": output_dirs,
        "comparison_report": None
        if scan_only
        else str(Path(str(output_dirs["snapshot_comparison"])) / SNAPSHOT_COMPARISON_REPORT),
        "required_artifact_inputs": [
            "offline copy of the matching ShooterGameServer binary",
            "offline independent core artifact from the same ARK binary",
            "binary SHA256 recorded before review",
            "core/artifact SHA256 recorded before review",
            "artifact_kind recorded for both primary and candidate snapshot roots",
            "capture_id distinct from the primary-core capture",
            "evidence_pack_id distinct from the primary-core evidence pack",
            "artifact_sha256 distinct from the primary-core artifact",
            "artifact-specific FName root derived from this core before full intake",
            "artifact-specific GObjects candidate reviewed against this core before full intake",
        ],
        "inputs": {
            "binary": rel_or_abs(args.binary),
            "core": rel_or_abs(args.core),
            "pack_dir": rel_or_abs(args.pack_dir),
            "snapshot_root": None if scan_only else rel_or_abs(args.snapshot_root),
            "target_set": None if scan_only else args.target_set,
            "base_root": None if scan_only else rel_or_abs(args.base_root),
            "verified_fname_root_slot": args.verified_fname_root_slot,
            "gobjects_candidate": args.gobjects_candidate,
            "fname_indices": merged_fname_indices(args.fname_index),
            "gobjects_sample_indices": []
            if scan_only
            else args.gobjects_sample_index or list(DEFAULT_GOBJECTS_SAMPLE_INDICES),
        },
        "phase_order": phases,
        "review_gates": [
            "no live server operations",
            "protected server input/output paths are rejected by both textual and resolved path",
            "execute requires existing binary/core paths",
            "in-repository output paths must be ignored by Git",
            "direct FName root validation must pass exact requested indices before GObjects sampling",
            "GObjects sampling manifest must be complete and match the reviewed root, candidate, and sample indices before snapshot regeneration",
            "full intake requires reviewed artifact-specific FName root and GObjects candidate",
        ],
        "promotion_blockers": [
            "missing independent artifact identity",
            "missing or partial sanitized artifact identity on either root: artifact_kind, artifact_sha256, capture_id, and evidence_pack_id are all required",
            "matching or reused primary-core artifact_sha256, capture_id, or evidence_pack_id",
            "dry-run or scan-only JSON plan treated as accepted FName or UFunction evidence",
            "FName table scan artifact treated as accepted FName evidence or layout promotion",
            "direct FName root validation missing, failed, or only partially matched",
            "missing or reused primary-core FName root assumptions",
            "GDB/core inspection failure in the evidence pack",
            "GObjects sampling manifest missing, partial, or mismatched against the executed command inputs",
            "missing candidate snapshot root",
            "snapshot comparison missing, inconclusive, rejected, or base-blocked targets",
            "snapshot comparison readiness JSON missing from the executed intake pack",
            "snapshot comparison readiness JSON schema or gate_mode mismatch",
            "promotion_gate.ready is not true in the readiness report",
            "promotion_gate.blockers is present and non-empty in the readiness report",
            "readiness report target_sets does not contain the executed command target set",
            "readiness report totals.targets is zero or missing",
        ],
        "commands": [
            {
                "phase": phase,
                "argv": command,
                "shell": shlex.join(command),
            }
            for phase, command in zip(phases, commands, strict=True)
        ],
    }


def expected_target_sets_from_command(command: list[str]) -> list[str]:
    target_sets: list[str] = []
    iterator = iter(enumerate(command))
    for index, item in iterator:
        if item == "--target-set":
            try:
                _, target_set = next(iterator)
            except StopIteration as exc:
                raise ReadinessReportError("compare command ended after --target-set") from exc
            target_sets.append(target_set)
        elif item.startswith("--target-set="):
            target_sets.append(item.split("=", 1)[1])
    if not target_sets:
        raise ReadinessReportError("compare command did not include --target-set")
    return target_sets


def require_persisted_readiness_report(
    report_path: Path,
    *,
    expected_target_sets: list[str],
) -> None:
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReadinessReportError(f"readiness report was not written: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise ReadinessReportError(f"readiness report is not valid JSON: {exc}") from exc

    if not isinstance(report, dict):
        raise ReadinessReportError("readiness report root must be a JSON object")
    if report.get("schema") != READINESS_SCHEMA:
        raise ReadinessReportError(
            f"readiness report schema must be {READINESS_SCHEMA}, got {report.get('schema')!r}"
        )
    if report.get("gate_mode") != READINESS_GATE_MODE:
        raise ReadinessReportError(
            f"readiness report gate_mode must be {READINESS_GATE_MODE}, got {report.get('gate_mode')!r}"
        )

    promotion_gate = report.get("promotion_gate")
    if not isinstance(promotion_gate, dict):
        raise ReadinessReportError("readiness report promotion_gate must be an object")
    if promotion_gate.get("ready") is not True:
        raise ReadinessReportError("readiness report promotion_gate.ready is not true")
    if promotion_gate.get("ready_scope") != "layout_only":
        raise ReadinessReportError("readiness report promotion_gate.ready_scope must be layout_only")
    if promotion_gate.get("layout_ready") is not True:
        raise ReadinessReportError("readiness report promotion_gate.layout_ready must be true")
    if promotion_gate.get("promotion_ready") is not False:
        raise ReadinessReportError("readiness report promotion_gate.promotion_ready must be false")
    if "blockers" in promotion_gate and promotion_gate["blockers"] != []:
        raise ReadinessReportError("readiness report promotion_gate.blockers must be empty or absent")
    if report.get("evidence_scope") != READINESS_EVIDENCE_SCOPE:
        raise ReadinessReportError("readiness report evidence_scope must be second_source_layout_evidence_only")
    not_promoted = report.get("not_promoted_surfaces")
    if not isinstance(not_promoted, list) or set(not_promoted) != REQUIRED_READINESS_NON_PROMOTED_SURFACES:
        raise ReadinessReportError("readiness report missing required non-promoted surfaces")

    target_sets = report.get("target_sets")
    if not isinstance(target_sets, list) or not all(isinstance(item, str) for item in target_sets):
        raise ReadinessReportError("readiness report target_sets must be a list of strings")
    missing_target_sets = sorted(set(expected_target_sets) - set(target_sets))
    if missing_target_sets:
        raise ReadinessReportError(
            "readiness report target_sets missing expected command target set(s): "
            + ", ".join(missing_target_sets)
        )

    totals = report.get("totals")
    if not isinstance(totals, dict):
        raise ReadinessReportError("readiness report totals must be an object")
    targets = totals.get("targets")
    if not isinstance(targets, int) or isinstance(targets, bool) or targets <= 0:
        raise ReadinessReportError("readiness report totals.targets must be greater than zero")


def require_persisted_gobjects_manifest(
    manifest_path: Path,
    *,
    expected_gobjects_candidate: str,
    expected_sample_indices: list[str],
    expected_fname_root_slot: str,
) -> None:
    expected_gobjects_candidate = f"0x{parse_nonnegative_int(expected_gobjects_candidate, '--gobjects-candidate'):x}"
    expected_fname_root_slot = f"0x{parse_nonnegative_int(expected_fname_root_slot, '--verified-fname-root-slot'):x}"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReadinessReportError(f"gobjects sampling manifest was not written: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise ReadinessReportError(f"gobjects sampling manifest is not valid JSON: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ReadinessReportError("gobjects sampling manifest root must be a JSON object")
    evidence_status = manifest.get("evidence_status")
    if not isinstance(evidence_status, dict):
        raise ReadinessReportError("gobjects sampling manifest evidence_status must be an object")
    if evidence_status.get("status") != "complete" or evidence_status.get("gdb_core_failed") is not False:
        raise ReadinessReportError("gobjects sampling manifest evidence_status must be complete")

    candidates = manifest.get("gobjects_candidates")
    if not isinstance(candidates, list):
        raise ReadinessReportError("gobjects sampling manifest gobjects_candidates must be a list")
    if not any(
        isinstance(item, dict)
        and item.get("label") == "gobjects"
        and item.get("address") == expected_gobjects_candidate
        for item in candidates
    ):
        raise ReadinessReportError("gobjects sampling manifest missing expected gobjects candidate")

    roots = manifest.get("fname_root_slots")
    if not isinstance(roots, list):
        raise ReadinessReportError("gobjects sampling manifest fname_root_slots must be a list")
    if not any(
        isinstance(item, dict)
        and item.get("label") == "verified_fname_root_slot"
        and item.get("address") == expected_fname_root_slot
        for item in roots
    ):
        raise ReadinessReportError("gobjects sampling manifest missing expected verified FName root")

    sample_indices = manifest.get("gobjects_sample_indices")
    expected_indices = [parse_nonnegative_int(item, "--gobjects-sample-index") for item in expected_sample_indices]
    if sample_indices != expected_indices:
        raise ReadinessReportError("gobjects sampling manifest sample indices do not match command inputs")


def snapshot_target_key(payload: dict[str, object], path: Path) -> str:
    if payload.get("schema") != UFUNCTION_SCHEMA:
        raise ReadinessReportError(f"{path}: unsupported snapshot schema {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise ReadinessReportError(f"{path}: expected exactly one target")
    identity = targets[0].get("target")
    if not isinstance(identity, dict):
        raise ReadinessReportError(f"{path}: snapshot target missing identity object")
    outer = identity.get("outer_name")
    name = identity.get("name")
    if not isinstance(outer, str) or not isinstance(name, str):
        raise ReadinessReportError(f"{path}: snapshot target missing string outer_name/name")
    return f"{outer}.{name}"


def snapshot_artifact_identity(payload: dict[str, object], path: Path, label: str) -> dict[str, str]:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        raise ReadinessReportError(f"{label} {path}: missing evidence object")
    values = {key: evidence.get(key) for key in ARTIFACT_IDENTITY_KEYS}
    missing = [key for key, value in values.items() if not isinstance(value, str) or not value]
    if missing:
        raise ReadinessReportError(
            f"{label} {path}: missing evidence artifact identity: {', '.join(missing)}"
        )
    identity = {key: str(values[key]) for key in ARTIFACT_IDENTITY_KEYS}
    artifact_kind = identity["artifact_kind"]
    if artifact_kind not in ALLOWED_ARTIFACT_KINDS:
        raise ReadinessReportError(f"{label} {path}: invalid artifact_kind {artifact_kind!r}")
    artifact_sha256 = identity["artifact_sha256"]
    if not is_sha256(artifact_sha256):
        raise ReadinessReportError(f"{label} {path}: invalid artifact_sha256")
    for key in ("capture_id", "evidence_pack_id"):
        if not is_safe_artifact_id(identity[key]):
            raise ReadinessReportError(f"{label} {path}: invalid {key}")
    return identity


def artifact_identities_by_target(root: Path, target_set: str, label: str) -> dict[str, dict[str, str]]:
    targets = schema_targets(target_set, UFUNCTION_SCHEMA)
    identities: dict[str, dict[str, str]] = {}
    if not root.exists():
        raise ReadinessReportError(f"{label} snapshot root does not exist: {root}")
    for path in sorted(root.rglob("*.snapshot.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReadinessReportError(f"{label} {path}: invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ReadinessReportError(f"{label} {path}: snapshot root must be a JSON object")
        if payload.get("schema") != UFUNCTION_SCHEMA:
            continue
        target = snapshot_target_key(payload, path)
        if target not in targets:
            continue
        if target in identities:
            raise ReadinessReportError(f"{label} snapshot root has duplicate target {target}")
        identities[target] = snapshot_artifact_identity(payload, path, label)
    missing_targets = sorted(targets - set(identities))
    if missing_targets:
        raise ReadinessReportError(
            f"{label} snapshot root missing target snapshot(s): {', '.join(missing_targets)}"
        )
    return identities


def require_distinct_snapshot_artifact_identities(
    base_root: Path,
    candidate_root: Path,
    *,
    target_set: str,
) -> None:
    base = artifact_identities_by_target(base_root, target_set, "base")
    candidate = artifact_identities_by_target(candidate_root, target_set, "candidate")
    for target in sorted(base):
        base_identity = base[target]
        candidate_identity = candidate[target]
        if tuple(base_identity[key] for key in ARTIFACT_IDENTITY_KEYS) == tuple(
            candidate_identity[key] for key in ARTIFACT_IDENTITY_KEYS
        ):
            raise ReadinessReportError(f"{target}: candidate reuses full base artifact identity")
        reused = [
            key
            for key in ("artifact_sha256", "capture_id", "evidence_pack_id")
            if base_identity[key] == candidate_identity[key]
        ]
        if reused:
            raise ReadinessReportError(
                f"{target}: candidate reuses base artifact identity field(s): {', '.join(reused)}"
            )


def append_wrapper_stderr(stderr_path: Path, message: str) -> None:
    prefix = ""
    if stderr_path.exists() and stderr_path.stat().st_size > 0:
        existing = stderr_path.read_text(encoding="utf-8")
        prefix = "" if existing.endswith("\n") else "\n"
    with stderr_path.open("a", encoding="utf-8") as stream:
        stream.write(f"{prefix}{message}\n")


def run_commands(args: argparse.Namespace, commands: list[list[str]]) -> int:
    phases = phase_order(args)
    for phase, command in zip(phases, commands, strict=True):
        print(f"\n==> {shlex.join(command)}", flush=True)
        if phase != "snapshot_comparison":
            subprocess.run(command, cwd=REPO_ROOT, check=True)
            if phase == "gobjects_sampling":
                require_persisted_gobjects_manifest(
                    Path(rel_or_abs(args.pack_dir)) / "gobjects-sampling" / "manifest.json",
                    expected_gobjects_candidate=args.gobjects_candidate,
                    expected_sample_indices=args.gobjects_sample_index
                    or list(DEFAULT_GOBJECTS_SAMPLE_INDICES),
                    expected_fname_root_slot=args.verified_fname_root_slot,
                )
            continue

        output_dir = Path(rel_or_abs(args.pack_dir)) / "snapshot-comparison"
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / SNAPSHOT_COMPARISON_REPORT
        stderr_path = output_dir / SNAPSHOT_COMPARISON_STDERR
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        report_path.write_text(completed.stdout, encoding="utf-8")
        if completed.stderr:
            stderr_path.write_text(completed.stderr, encoding="utf-8")
        elif stderr_path.exists():
            stderr_path.unlink()
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        validation_failures = []
        try:
            require_persisted_readiness_report(
                report_path,
                expected_target_sets=expected_target_sets_from_command(command),
            )
        except ReadinessReportError as exc:
            validation_failures.append(f"snapshot comparison readiness validation failed: {exc}")
        try:
            require_distinct_snapshot_artifact_identities(
                Path(rel_or_abs(args.base_root)),
                Path(rel_or_abs(args.snapshot_root)),
                target_set=args.target_set,
            )
        except ReadinessReportError as exc:
            validation_failures.append(f"snapshot artifact identity validation failed: {exc}")
        if completed.returncode != 0:
            for message in validation_failures:
                append_wrapper_stderr(stderr_path, message)
                print(message, file=sys.stderr)
            print(f"snapshot comparison report written to {report_path}", file=sys.stderr)
            return completed.returncode
        if validation_failures:
            for message in validation_failures:
                append_wrapper_stderr(stderr_path, message)
                print(message, file=sys.stderr)
            print(f"snapshot comparison report written to {report_path}", file=sys.stderr)
            return 1
        print(f"snapshot comparison report written to {report_path}")
    return 0


def main() -> int:
    args = parse_args()
    validate_args(args)
    commands = build_commands(args)

    if not args.execute:
        if args.json_plan:
            print(json.dumps(build_plan(args, commands), indent=2, sort_keys=True))
            return 0
        print("# Dry run: pass --execute to run these offline commands.")
        for command in commands:
            print(shlex.join(command))
        return 0

    preflight_execute(args)
    return run_commands(args, commands)


if __name__ == "__main__":
    sys.exit(main())
