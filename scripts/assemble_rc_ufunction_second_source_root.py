#!/usr/bin/env python3
"""Assemble a single RC UFunction second-source root from accepted target-set roots."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from artifact_identity import ARTIFACT_IDENTITY_KEYS, complete_artifact_identity  # noqa: E402
from reflection_target_sets import TARGET_SETS  # noqa: E402
from snapshot_evidence_pack import (  # noqa: E402
    reject_protected_input_path,
    reject_protected_output_path,
    reject_symlink_component,
)


SCHEMA = "obelisk.rc-ufunction-second-source-root-manifest.v1"
SNAPSHOT_SCHEMA = "obelisk.ufunction-chain.snapshot.v1"
RC_TARGET_SETS = (
    "minimal-second-source-intake",
    "structure-observer-intake",
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


class SymlinkInputPathError(OSError):
    def __init__(self, component: Path) -> None:
        super().__init__(errno.ELOOP, f"path must not be a symlink: {component}")
        self.component = component


def open_regular_file_no_symlink(path: Path, *, label: str):
    reject_symlink_component(path, label)
    candidate = path.expanduser()
    candidate = candidate if candidate.is_absolute() else candidate.absolute()
    if not candidate.name:
        raise OSError(errno.EINVAL, f"{label} must be a regular file: {candidate}")

    common_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    directory_flags = common_flags | getattr(os, "O_DIRECTORY", 0)
    file_flags = common_flags
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
        file_flags |= os.O_NOFOLLOW

    parent_fd: int | None = None
    try:
        parent_fd = os.open(candidate.anchor, directory_flags)
        for part in candidate.parts[1:-1]:
            next_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        fd = os.open(candidate.name, file_flags, dir_fd=parent_fd)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise SymlinkInputPathError(candidate) from exc
        raise
    finally:
        if parent_fd is not None:
            os.close(parent_fd)

    try:
        status = os.fstat(fd)
        if not stat.S_ISREG(status.st_mode):
            raise OSError(errno.EINVAL, f"{label} must be a regular file: {candidate}")
        return os.fdopen(fd, "rb")
    except Exception:
        os.close(fd)
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open_regular_file_no_symlink(path, label="snapshot") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        with open_regular_file_no_symlink(path, label="snapshot") as handle:
            payload = json.loads(handle.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    except SymlinkInputPathError as exc:
        raise SystemExit(f"snapshot must not be a symlink: {exc.component}") from exc
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


def snapshot_paths(root: Path, *, label: str) -> list[Path]:
    reject_symlink_component(root, label)
    root = reject_protected_input_path(root, label)
    reject_symlink_component(root, label)
    if root.is_file():
        return [root]
    if not root.exists():
        raise SystemExit(f"source root does not exist: {root}")
    paths = []
    for path in root.rglob("*.snapshot.json"):
        reject_symlink_component(path, "snapshot")
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def source_records(roots: dict[str, Path]) -> dict[str, dict[str, Any]]:
    wanted = required_targets()
    records: dict[str, dict[str, Any]] = {}
    for target_set, root in roots.items():
        accepted_for_set = set(TARGET_SETS[target_set])
        root_label = f"--{target_set}-root"
        reject_symlink_component(root, root_label)
        resolved_root = reject_protected_input_path(root, root_label)
        reject_symlink_component(resolved_root, root_label)
        for path in snapshot_paths(resolved_root, label=root_label):
            payload = load_json(path)
            key = target_key(payload, path)
            if key not in accepted_for_set:
                raise SystemExit(
                    f"{path}: unexpected snapshot target for {target_set}: {key}"
                )
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
    reject_symlink_component(output_root, "--output-root")
    output_root = reject_protected_output_path(output_root, "--output-root")
    reject_symlink_component(output_root, "--output-root")
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
        source_path = Path(record["source_path"])
        with open_regular_file_no_symlink(source_path, label="snapshot") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)
        reject_symlink_component(source_path, "snapshot")
        shutil.copystat(source_path, destination, follow_symlinks=False)
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
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=(
            "Public RC assembly is limited to minimal-second-source-intake, "
            "structure-observer-intake, and chat-message-intake. "
            "item-return-only-policy-slice is internal/planning backing and is "
            "not accepted by this helper."
        ),
    )
    parser.add_argument("--minimal-root", required=True, type=Path)
    parser.add_argument("--structure-root", required=True, type=Path)
    parser.add_argument("--chat-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = {
        "minimal-second-source-intake": args.minimal_root,
        "structure-observer-intake": args.structure_root,
        "chat-message-intake": args.chat_root,
    }
    manifest = write_output(source_records(roots), args.output_root, replace=args.replace)
    print(json.dumps({"schema": SCHEMA, "output_root": str(args.output_root), "target_count": manifest["target_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
