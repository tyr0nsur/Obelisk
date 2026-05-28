#!/usr/bin/env python3
"""Regenerate sanitized ScriptStruct snapshot fixtures from an explicit manifest."""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

import inspect_core_ufunctions as inspector  # noqa: E402


DEFAULT_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots" / "manifest.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tests" / "fixtures" / "scriptstruct_snapshots"
GENERATED_BY = "scripts/inspect_core_ufunctions.py --snapshot-json"
MANIFEST_SCHEMA = "obelisk.scriptstruct-snapshot-manifest.v1"
SNAPSHOT_SCHEMA = "obelisk.scriptstruct-chain.snapshot.v1"
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
UNSTABLE_IDENTITY_KEYS = {
    "gobjects_index",
    "object_index",
    "name_gobjects_index",
    "name_index",
    "class_index",
    "class_gobjects_index",
    "class_name_index",
    "class_object_index",
    "outer_index",
    "outer_gobjects_index",
    "outer_name_index",
    "outer_object_index",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate committed ScriptStruct snapshot fixtures.")
    parser.add_argument("--core", required=True, type=Path, help="Path to an existing offline ELF core dump.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--gobjects", type=inspector.parse_int)
    parser.add_argument(
        "--fname-root-slot",
        type=inspector.parse_int,
        default=None,
        help="FName root slot for this artifact. Default is the primary-core fixture candidate; "
        "override for second-source artifacts.",
    )
    parser.add_argument("--max-object-scan", type=int, help="Override manifest max_object_scan.")
    parser.add_argument("--obelisk-commit", help="Commit recorded in snapshot evidence. Defaults to current HEAD.")
    parser.add_argument("--artifact-kind", help="Sanitized source artifact kind, such as offline_core.")
    parser.add_argument("--artifact-sha256", help="SHA256 of the source core/log/evidence artifact.")
    parser.add_argument("--capture-id", help="Sanitized capture identifier for second-source comparison.")
    parser.add_argument("--evidence-pack-id", help="Sanitized evidence pack identifier for second-source comparison.")
    parser.add_argument(
        "--evidence-pack-manifest",
        type=Path,
        help="Read artifact identity and FName root slot from build_core_dump_evidence_pack.py manifest.json.",
    )
    parser.add_argument(
        "--evidence-pack-fname-root-label",
        help="FName root slot label to read from --evidence-pack-manifest when the pack has multiple slots.",
    )
    parser.add_argument(
        "--evidence-pack-gobjects-label",
        help="GObjects candidate label to read from --evidence-pack-manifest when the pack has multiple candidates.",
    )
    parser.add_argument("--target", action="append", default=[], help="Only process exact Outer.Name target. Repeatable.")
    parser.add_argument("--write", action="store_true", help="Write fixtures. Default is dry-run.")
    parser.add_argument("--check", action="store_true", help="Generate to temp files and fail if committed fixtures differ.")
    parser.add_argument(
        "--check-layout",
        action="store_true",
        help="Fail only when target identity, PropertiesSize, or property-chain layout differs.",
    )
    return parser.parse_args()


def repo_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def optional_safe_text(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    return safe_component(value, field)


def optional_sha256(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if SHA256_RE.fullmatch(value) is None:
        raise SystemExit(f"{field} must be lowercase SHA256")
    return value


def select_labeled_address(
    path: Path,
    entries: object,
    *,
    field: str,
    label: str | None,
    label_flag: str,
) -> int:
    if not isinstance(entries, list) or not entries:
        raise SystemExit(f"{path}: evidence pack manifest missing {field}")
    if label is None:
        if len(entries) != 1:
            raise SystemExit(f"{path}: multiple {field} found; pass {label_flag}")
        selected = entries[0]
    else:
        selected = next(
            (
                item
                for item in entries
                if isinstance(item, dict) and item.get("label") == label
            ),
            None,
        )
        if selected is None:
            raise SystemExit(f"{path}: {field} label not found: {label}")
    if not isinstance(selected, dict):
        raise SystemExit(f"{path}: invalid {field} entry")
    address = selected.get("address")
    if not isinstance(address, str):
        raise SystemExit(f"{path}: selected {field} entry missing address")
    return inspector.parse_int(address)


def evidence_pack_defaults(path: Path, root_label: str | None, gobjects_label: str | None) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    core = payload.get("core")
    if not isinstance(core, dict):
        raise SystemExit(f"{path}: evidence pack manifest missing core object")
    core_sha = core.get("sha256")
    if not isinstance(core_sha, str) or SHA256_RE.fullmatch(core_sha) is None:
        raise SystemExit(f"{path}: evidence pack manifest must include core.sha256")
    core_path = core.get("path")
    if not isinstance(core_path, str) or not core_path:
        raise SystemExit(f"{path}: evidence pack manifest missing core.path")
    return {
        "artifact_kind": "offline_core",
        "artifact_sha256": core_sha,
        "capture_id": safe_component(Path(core_path).stem, "capture-id"),
        "evidence_pack_id": safe_component(path.parent.name, "evidence-pack-id"),
        "core_path": Path(core_path).resolve(),
        "fname_root_slot": select_labeled_address(
            path,
            payload.get("fname_root_slots"),
            field="fname_root_slots",
            label=root_label,
            label_flag="--evidence-pack-fname-root-label",
        ),
        "gobjects": select_labeled_address(
            path,
            payload.get("gobjects_candidates"),
            field="gobjects_candidates",
            label=gobjects_label,
            label_flag="--evidence-pack-gobjects-label",
        ),
    }


def merge_manifest_default(current: object | None, default: object, field: str) -> object:
    if current is None:
        return default
    if current != default:
        raise SystemExit(f"{field} conflicts with --evidence-pack-manifest")
    return current


def required_text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise SystemExit(f"manifest missing string field: {key}")
    return value


def load_manifest(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != MANIFEST_SCHEMA:
        raise SystemExit(f"{path}: unsupported manifest schema")
    ark_sha = required_text(payload, "ark_binary_sha256")
    if SHA256_RE.fullmatch(ark_sha) is None:
        raise SystemExit(f"{path}: ark_binary_sha256 must be lowercase SHA256")
    sha_prefix = required_text(payload, "sha_prefix")
    if sha_prefix != ark_sha[: len(sha_prefix)]:
        raise SystemExit(f"{path}: sha_prefix does not match ark_binary_sha256")
    if payload.get("source") != "offline_core":
        raise SystemExit(f"{path}: source must be offline_core")
    if payload.get("status") != "candidate-only":
        raise SystemExit(f"{path}: status must be candidate-only")
    if not isinstance(payload.get("targets"), list):
        raise SystemExit(f"{path}: targets must be a list")
    return payload


def safe_component(value: str, field: str) -> str:
    if SAFE_COMPONENT_RE.fullmatch(value) is None or ".." in value:
        raise SystemExit(f"unsafe {field} in manifest: {value}")
    return value


def checked_output_path(output_root: Path, sha_prefix: str, entry: dict[str, object]) -> Path:
    module = safe_component(required_text(entry, "module"), "module")
    filename = safe_component(required_text(entry, "file"), "file")
    if not filename.endswith(".snapshot.json"):
        raise SystemExit(f"snapshot file must end with .snapshot.json: {filename}")
    output_root = output_root.resolve()
    output_path = (output_root / sha_prefix / module / filename).resolve()
    if output_root != output_path and output_root not in output_path.parents:
        raise SystemExit(f"output escapes fixture root: {filename}")
    return output_path


def entry_id(entry: dict[str, object]) -> str:
    return f"{required_text(entry, 'outer')}.{required_text(entry, 'name')}"


def selected(entry: dict[str, object], filters: set[str]) -> bool:
    return not filters or entry_id(entry) in filters


def build_snapshot(
    *,
    memory: inspector.uobjects.CoreMemory,
    entry: dict[str, object],
    gobjects: int,
    fname_root_slot: int,
    max_object_scan: int,
    ark_sha: str,
    obelisk_commit: str,
    source: str,
    status: str,
    artifact_kind: str | None,
    artifact_sha256: str | None,
    capture_id: str | None,
    evidence_pack_id: str | None,
) -> dict[str, object]:
    outer = required_text(entry, "outer")
    name = required_text(entry, "name")
    payload = inspector.inspect_core(
        memory,
        gobjects=gobjects,
        fname_root_slot=fname_root_slot,
        object_addresses=[],
        indices=[],
        name_contains=[],
        outer_contains=[],
        name_exact=[name],
        outer_exact=[outer],
        window_size=inspector.DEFAULT_WINDOW_SIZE,
        max_object_scan=max_object_scan,
        inspection_mode="script-struct",
    )
    targets = payload.get("targets")
    observed = 0 if not isinstance(targets, list) else len(targets)
    if observed != 1:
        raise SystemExit(f"{outer}.{name}: expected exactly one target, observed {observed}")

    evidence = {
        "ark_binary_sha256": ark_sha,
        "obelisk_commit": obelisk_commit,
        "source": source,
        "status": status,
        "generated_by": GENERATED_BY,
    }
    optional_evidence = {
        "artifact_kind": artifact_kind,
        "artifact_sha256": artifact_sha256,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    evidence.update({key: value for key, value in optional_evidence.items() if value is not None})
    snapshot = inspector.build_fixture_snapshot(payload, evidence=evidence)
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise SystemExit(f"{outer}.{name}: generated non-ScriptStruct snapshot")
    target = snapshot["targets"][0]["target"]
    if target.get("outer_name") != outer or target.get("name") != name:
        raise SystemExit(f"{outer}.{name}: generated target identity mismatch")
    return snapshot


def write_atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(text)
    temp_path.replace(path)


def check_matches(path: Path, payload: dict[str, object]) -> bool:
    if not path.exists():
        return False
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
        temp_file.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    try:
        return filecmp.cmp(temp_path, path, shallow=False)
    finally:
        temp_path.unlink(missing_ok=True)


def stable_layout_value(value: object) -> object:
    if isinstance(value, dict):
        return {key: stable_layout_value(item) for key, item in value.items() if key not in UNSTABLE_IDENTITY_KEYS}
    if isinstance(value, list):
        return [stable_layout_value(item) for item in value]
    return value


def target_layout(payload: dict[str, object]) -> dict[str, object]:
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1:
        raise SystemExit("snapshot must contain exactly one target for layout comparison")
    target = targets[0]
    if not isinstance(target, dict):
        raise SystemExit("snapshot target must be an object")
    identity = target.get("target")
    chain = target.get("property_chain")
    if not isinstance(identity, dict) or not isinstance(chain, dict):
        raise SystemExit("snapshot missing target identity or property chain")
    return stable_layout_value(
        {
            "schema": payload.get("schema"),
            "inspection_mode": target.get("inspection_mode"),
            "target": {
                "class_name": identity.get("class_name"),
                "name": identity.get("name"),
                "outer_name": identity.get("outer_name"),
                "outer_class_name": identity.get("outer_class_name"),
            },
            "status": target.get("status"),
            "properties_size": target.get("properties_size"),
            "property_chain": {
                "status": chain.get("status"),
                "expected_count": chain.get("expected_count"),
                "observed_count": chain.get("observed_count"),
                "properties_size": chain.get("properties_size"),
                "properties": chain.get("properties"),
            },
        }
    )


def check_layout_matches(path: Path, payload: dict[str, object]) -> bool:
    if not path.exists():
        return False
    committed = json.loads(path.read_text(encoding="utf-8"))
    return target_layout(committed) == target_layout(payload)


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.manifest)
    manifest_scan = manifest.get("max_object_scan")
    max_object_scan = args.max_object_scan if args.max_object_scan is not None else manifest_scan
    if not isinstance(max_object_scan, int) or max_object_scan < 0:
        raise SystemExit("max_object_scan must be a non-negative integer")
    selected_modes = sum(1 for enabled in (args.check, args.check_layout, args.write) if enabled)
    if selected_modes > 1:
        raise SystemExit("choose only one of --check, --check-layout, or --write")

    ark_sha = required_text(manifest, "ark_binary_sha256")
    sha_prefix = required_text(manifest, "sha_prefix")
    source = required_text(manifest, "source")
    status = required_text(manifest, "status")
    obelisk_commit = args.obelisk_commit or repo_commit()
    pack_defaults = (
        evidence_pack_defaults(
            args.evidence_pack_manifest,
            args.evidence_pack_fname_root_label,
            args.evidence_pack_gobjects_label,
        )
        if args.evidence_pack_manifest is not None
        else {}
    )
    if pack_defaults:
        if args.core.resolve() != pack_defaults["core_path"]:
            raise SystemExit("--core conflicts with --evidence-pack-manifest core.path")
        args.fname_root_slot = merge_manifest_default(
            args.fname_root_slot,
            pack_defaults["fname_root_slot"],
            "--fname-root-slot",
        )
        args.gobjects = merge_manifest_default(
            args.gobjects,
            pack_defaults["gobjects"],
            "--gobjects",
        )
        args.artifact_kind = merge_manifest_default(
            args.artifact_kind,
            pack_defaults["artifact_kind"],
            "--artifact-kind",
        )
        args.artifact_sha256 = merge_manifest_default(
            args.artifact_sha256,
            pack_defaults["artifact_sha256"],
            "--artifact-sha256",
        )
        args.capture_id = merge_manifest_default(
            args.capture_id,
            pack_defaults["capture_id"],
            "--capture-id",
        )
        args.evidence_pack_id = merge_manifest_default(
            args.evidence_pack_id,
            pack_defaults["evidence_pack_id"],
            "--evidence-pack-id",
        )
    artifact_kind = optional_safe_text(args.artifact_kind, "artifact-kind")
    artifact_sha256 = optional_sha256(args.artifact_sha256, "artifact-sha256")
    capture_id = optional_safe_text(args.capture_id, "capture-id")
    evidence_pack_id = optional_safe_text(args.evidence_pack_id, "evidence-pack-id")
    artifact_identity_supplied = any(
        value is not None
        for value in (artifact_kind, artifact_sha256, capture_id, evidence_pack_id)
    )
    if artifact_identity_supplied and not all(
        value is not None
        for value in (artifact_kind, artifact_sha256, capture_id, evidence_pack_id)
    ):
        raise SystemExit(
            "artifact identity must include --artifact-kind, --artifact-sha256, "
            "--capture-id, and --evidence-pack-id together"
        )
    if artifact_identity_supplied and args.fname_root_slot is None:
        raise SystemExit(
            "--fname-root-slot is required when recording artifact identity; "
            "derive or scan a FName root for this artifact instead of using the primary-core default"
        )
    if artifact_identity_supplied and args.gobjects is None:
        raise SystemExit(
            "--gobjects is required when recording artifact identity; "
            "derive or import a GObjects candidate for this artifact instead of using the primary-core default"
        )
    if args.check_layout and not artifact_identity_supplied:
        raise SystemExit(
            "--check-layout is reserved for second-source layout validation and requires "
            "--artifact-kind, --artifact-sha256, --capture-id, --evidence-pack-id, "
            "and --fname-root-slot"
        )
    fname_root_slot = (
        args.fname_root_slot
        if args.fname_root_slot is not None
        else inspector.uobjects.DEFAULT_FNAME_ROOT_SLOT
    )
    gobjects = args.gobjects if args.gobjects is not None else inspector.uobjects.DEFAULT_GOBJECTS
    filters = set(args.target)
    processed = 0
    failures: list[str] = []

    memory = inspector.uobjects.CoreMemory(args.core)
    try:
        for raw_entry in manifest["targets"]:
            if not isinstance(raw_entry, dict):
                raise SystemExit("manifest targets must be objects")
            if not selected(raw_entry, filters):
                continue
            processed += 1
            output_path = checked_output_path(args.output_root, sha_prefix, raw_entry)
            snapshot = build_snapshot(
                memory=memory,
                entry=raw_entry,
                gobjects=gobjects,
                fname_root_slot=fname_root_slot,
                max_object_scan=max_object_scan,
                ark_sha=ark_sha,
                obelisk_commit=obelisk_commit,
                source=source,
                status=status,
                artifact_kind=artifact_kind,
                artifact_sha256=artifact_sha256,
                capture_id=capture_id,
                evidence_pack_id=evidence_pack_id,
            )
            label = output_path.relative_to(REPO_ROOT) if output_path.is_relative_to(REPO_ROOT) else output_path
            if args.check:
                if check_matches(output_path, snapshot):
                    print(f"ok {label}")
                else:
                    failures.append(str(label))
                    print(f"diff {label}")
            elif args.check_layout:
                if check_layout_matches(output_path, snapshot):
                    print(f"layout ok {label}")
                else:
                    failures.append(str(label))
                    print(f"layout diff {label}")
            elif args.write:
                write_atomic_json(output_path, snapshot)
                print(f"wrote {label}")
            else:
                print(f"would write {label}")
    finally:
        memory.close()

    if filters and processed != len(filters):
        missing = sorted(filters - {entry_id(entry) for entry in manifest["targets"] if isinstance(entry, dict)})
        raise SystemExit(f"target filter did not match manifest entries: {missing}")
    if failures:
        drift_kind = "layout drift" if args.check_layout else "snapshot drift"
        raise SystemExit(f"{drift_kind} detected: {', '.join(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
