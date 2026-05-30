#!/usr/bin/env python3
"""Shared evidence-pack helpers for snapshot regeneration tools."""

from __future__ import annotations

import json
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import protected_paths

SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class EvidencePackDefaults:
    artifact_kind: str
    artifact_sha256: str
    capture_id: str
    evidence_pack_id: str
    core_path: Path
    fname_root_slot: int
    gobjects: int


def safe_component(value: str, field: str) -> str:
    if SAFE_COMPONENT_RE.fullmatch(value) is None or ".." in value:
        raise SystemExit(f"unsafe {field} in manifest: {value}")
    return value


def is_relative_to(path: Path, parent: Path) -> bool:
    return protected_paths.is_under_path(path, parent)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def require_ignored_output_path(path: Path, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not is_relative_to(resolved, REPO_ROOT):
        return
    relative = resolved.relative_to(REPO_ROOT)
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", str(relative)],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"{label} is inside the repository but is not ignored by Git: {resolved}")


def reject_protected_input_path(path: Path, label: str) -> Path:
    return protected_paths.reject_protected_input_path(
        path,
        label,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_output_path(path: Path, label: str) -> Path:
    return protected_paths.reject_protected_output_path(
        path,
        label,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def reject_protected_core_path(path: Path, manifest_path: Path) -> Path:
    return reject_protected_input_path(path, f"{manifest_path}: evidence pack core.path")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise SystemExit(f"{path}: evidence pack core.path does not exist") from exc
    except OSError as exc:
        raise SystemExit(f"{path}: evidence pack core.path is unreadable: {exc}") from exc
    return digest.hexdigest()


def select_labeled_address(
    path: Path,
    entries: object,
    *,
    field: str,
    label: str | None,
    label_flag: str,
    parse_int: Callable[[str], int],
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
    return parse_int(address)


def evidence_pack_defaults(
    path: Path,
    root_label: str | None,
    gobjects_label: str | None,
    expected_ark_binary_sha256: str,
    parse_int: Callable[[str], int],
) -> EvidencePackDefaults:
    path = reject_protected_input_path(path, "--evidence-pack-manifest")
    payload = json.loads(path.read_text(encoding="utf-8"))
    binary = payload.get("binary")
    if not isinstance(binary, dict):
        raise SystemExit(f"{path}: evidence pack manifest missing binary object")
    binary_sha = binary.get("sha256")
    if not isinstance(binary_sha, str) or SHA256_RE.fullmatch(binary_sha) is None:
        raise SystemExit(f"{path}: evidence pack manifest must include binary.sha256")
    if binary_sha != expected_ark_binary_sha256:
        raise SystemExit(f"{path}: binary.sha256 conflicts with snapshot manifest ark_binary_sha256")
    evidence_status = payload.get("evidence_status")
    if not isinstance(evidence_status, dict):
        raise SystemExit(f"{path}: evidence pack manifest missing evidence_status object")
    status = evidence_status.get("status")
    if status != "complete":
        raise SystemExit(f"{path}: evidence pack status is not complete: {status}")
    if evidence_status.get("gdb_core_failed") is not False:
        raise SystemExit(f"{path}: evidence pack must include gdb_core_failed=false")
    core = payload.get("core")
    if not isinstance(core, dict):
        raise SystemExit(f"{path}: evidence pack manifest missing core object")
    core_sha = core.get("sha256")
    if not isinstance(core_sha, str) or SHA256_RE.fullmatch(core_sha) is None:
        raise SystemExit(f"{path}: evidence pack manifest must include core.sha256")
    core_path = core.get("path")
    if not isinstance(core_path, str) or not core_path:
        raise SystemExit(f"{path}: evidence pack manifest missing core.path")
    resolved_core_path = reject_protected_core_path(Path(core_path), path)
    actual_core_sha = sha256_file(resolved_core_path)
    if actual_core_sha != core_sha:
        raise SystemExit(f"{path}: core.sha256 does not match core.path contents")
    return EvidencePackDefaults(
        artifact_kind="offline_core",
        artifact_sha256=core_sha,
        capture_id=safe_component(Path(core_path).stem, "capture-id"),
        evidence_pack_id=safe_component(path.parent.name, "evidence-pack-id"),
        core_path=resolved_core_path,
        fname_root_slot=select_labeled_address(
            path,
            payload.get("fname_root_slots"),
            field="fname_root_slots",
            label=root_label,
            label_flag="--evidence-pack-fname-root-label",
            parse_int=parse_int,
        ),
        gobjects=select_labeled_address(
            path,
            payload.get("gobjects_candidates"),
            field="gobjects_candidates",
            label=gobjects_label,
            label_flag="--evidence-pack-gobjects-label",
            parse_int=parse_int,
        ),
    )


def merge_manifest_default(current: object | None, default: object, field: str) -> object:
    if current is None:
        return default
    if current != default:
        raise SystemExit(f"{field} conflicts with --evidence-pack-manifest")
    return current
