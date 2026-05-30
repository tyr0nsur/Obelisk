#!/usr/bin/env python3
"""Assemble a single RC UFunction second-source root from accepted target-set roots."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from artifact_identity import ARTIFACT_IDENTITY_KEYS, complete_artifact_identity  # noqa: E402
from reflection_target_sets import TARGET_SETS  # noqa: E402
from snapshot_evidence_pack import reject_protected_input_path, reject_protected_output_path  # noqa: E402


SCHEMA = "obelisk.rc-ufunction-second-source-root-manifest.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
RC_TARGET_SETS = (
    "minimal-second-source-intake",
    "structure-observer-intake",
    "item-return-only-policy-slice",
    "chat-message-intake",
)
EVIDENCE_IDENTITY_FIELDS = (
    "ark_binary_sha256",
    "artifact_kind",
    "artifact_sha256",
    "capture_id",
    "evidence_pack_id",
    "obelisk_commit",
    "source",
    "status",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return payload


def target_key(payload: dict[str, Any], path: Path) -> str:
    if payload.get("schema") != SNAPSHOT_SCHEMA:
        raise SystemExit(f"{path}: unsupported snapshot schema {payload.get('schema')!r}")
    targets = payload.get("targets")
    if not isinstance(targets, list) or len(targets) != 1 or not isinstance(targets[0], dict):
        raise SystemExit(f"{path}: expected exactly one target")
    identity = targets[0].get("target")
    if not isinstance(identity, dict):
        raise SystemExit(f"{path}: snapshot target missing identity")
    outer = identity.get("outer_name")
    name = identity.get("name")
    if not isinstance(outer, str) or not isinstance(name, str):
        raise SystemExit(f"{path}: snapshot target missing outer_name/name")
    return f"{SNAPSHOT_SCHEMA}:{outer}.{name}"


def evidence_identity(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit(f"{path}: missing evidence object")
    artifact_identity = {key: evidence.get(key) for key in ARTIFACT_IDENTITY_KEYS}
    _, identity_errors = complete_artifact_identity(
        {"artifact_identity": artifact_identity},
        expected_artifact_kind="offline_core",
    )
    if identity_errors:
        raise SystemExit(
            f"{path}: incomplete or invalid evidence artifact identity: "
            + ", ".join(identity_errors)
        )
    identity: dict[str, Any] = {}
    for field in EVIDENCE_IDENTITY_FIELDS:
        value = evidence.get(field)
        if isinstance(value, (str, int, float, bool)) or value is None:
            identity[field] = value
    return identity


def assert_no_manifest_path_leaks(value: Any, label: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert_no_manifest_path_leaks(item, f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            assert_no_manifest_path_leaks(item, f"{label}[{index}]")
        return
    if not isinstance(value, str):
        return
    if "/servidor/ark" in value or value.startswith("/") or (len(value) >= 3 and value[1:3] in (":\\", ":/")):
        raise SystemExit(f"refusing to write sensitive or absolute path in manifest at {label}")


def required_targets() -> set[str]:
    targets: set[str] = set()
    for target_set in RC_TARGET_SETS:
        targets.update(TARGET_SETS[target_set])
    return targets


def snapshot_paths(root: Path) -> list[Path]:
    root = reject_protected_input_path(root, "source root")
    if root.is_file():
        return [root]
    if not root.exists():
        raise SystemExit(f"source root does not exist: {root}")
    return sorted(path for path in root.rglob("*.snapshot.json") if path.is_file())


def source_records(roots: dict[str, Path]) -> dict[str, dict[str, Any]]:
    wanted = required_targets()
    records: dict[str, dict[str, Any]] = {}
    for target_set, root in roots.items():
        accepted_for_set = set(TARGET_SETS[target_set])
        resolved_root = reject_protected_input_path(root, f"--{target_set}-root")
        for path in snapshot_paths(resolved_root):
            payload = load_json(path)
            key = target_key(payload, path)
            if key not in accepted_for_set:
                continue
            digest = sha256_file(path)
            relative_path = path.relative_to(resolved_root).as_posix()
            existing = records.get(key)
            if existing is not None:
                if existing["sha256"] != digest:
                    raise SystemExit(
                        f"divergent duplicate snapshot for {key}: "
                        f"{existing['relative_path']} from {existing['source_target_sets']} "
                        f"and {relative_path} from {target_set}"
                    )
                existing["source_target_sets"].append(target_set)
                continue
            records[key] = {
                "target": key,
                "source_target_sets": [target_set],
                "source_path": str(path),
                "relative_path": relative_path,
                "sha256": digest,
                "evidence": evidence_identity(payload, path),
            }
    missing = sorted(wanted - set(records))
    if missing:
        raise SystemExit("missing RC UFunction second-source snapshots: " + ",".join(missing))
    return records


def write_output(records: dict[str, dict[str, Any]], output_root: Path, *, replace: bool) -> dict[str, Any]:
    output_root = reject_protected_output_path(output_root, "--output-root")
    if output_root.exists():
        if not replace:
            raise SystemExit(f"--output-root already exists: {output_root}")
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    snapshots = []
    used_relative_paths: dict[str, str] = {}
    for key, record in sorted(records.items()):
        relative = record["relative_path"]
        previous_key = used_relative_paths.get(relative)
        if previous_key is not None and previous_key != key:
            raise SystemExit(f"output relative path collision: {relative}")
        used_relative_paths[relative] = key
        destination = output_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(record["source_path"], destination)
        snapshots.append(
            {
                "target": key,
                "relative_path": relative,
                "snapshot_sha256": record["sha256"],
                "source_target_sets": sorted(record["source_target_sets"]),
                "evidence": record["evidence"],
            }
        )
    manifest = {
        "schema": SCHEMA,
        "snapshot_schema": SNAPSHOT_SCHEMA,
        "target_sets": list(RC_TARGET_SETS),
        "target_count": len(records),
        "snapshots": snapshots,
        "path_redacted": True,
        "non_claims": [
            "assembled root only; does not regenerate snapshots",
            "does not promote ResourceHandle, object identity, mutation, or return override",
        ],
    }
    assert_no_manifest_path_leaks(manifest, "manifest")
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minimal-root", required=True, type=Path)
    parser.add_argument("--structure-root", required=True, type=Path)
    parser.add_argument("--item-return-root", required=True, type=Path)
    parser.add_argument("--chat-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = {
        "minimal-second-source-intake": args.minimal_root,
        "structure-observer-intake": args.structure_root,
        "item-return-only-policy-slice": args.item_return_root,
        "chat-message-intake": args.chat_root,
    }
    manifest = write_output(source_records(roots), args.output_root, replace=args.replace)
    print(json.dumps({"schema": SCHEMA, "output_root": str(args.output_root), "target_count": manifest["target_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
