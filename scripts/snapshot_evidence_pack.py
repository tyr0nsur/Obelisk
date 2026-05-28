#!/usr/bin/env python3
"""Shared evidence-pack helpers for snapshot regeneration tools."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    parse_int: Callable[[str], int],
) -> EvidencePackDefaults:
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
    return EvidencePackDefaults(
        artifact_kind="offline_core",
        artifact_sha256=core_sha,
        capture_id=safe_component(Path(core_path).stem, "capture-id"),
        evidence_pack_id=safe_component(path.parent.name, "evidence-pack-id"),
        core_path=Path(core_path).resolve(),
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
