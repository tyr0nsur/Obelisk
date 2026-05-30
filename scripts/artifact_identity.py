"""Shared fail-closed artifact identity helpers for offline evidence tools."""

from __future__ import annotations

import json
import re
from typing import Any


ARTIFACT_IDENTITY_KEYS = (
    "artifact_kind",
    "artifact_sha256",
    "capture_id",
    "evidence_pack_id",
)
PLACEHOLDER_ARTIFACT_ID_PREFIXES = ("unspecified-", "static-global-default-")
SAFE_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def is_safe_artifact_id(value: object, *, reject_placeholders: bool = True) -> bool:
    if not isinstance(value, str):
        return False
    if SAFE_ARTIFACT_ID_RE.fullmatch(value) is None:
        return False
    if ".." in value or "/" in value or "\\" in value:
        return False
    if reject_placeholders and value.casefold().startswith(PLACEHOLDER_ARTIFACT_ID_PREFIXES):
        return False
    return True


def artifact_identity_placeholder_fields(identity: object) -> list[str]:
    placeholders: list[str] = []
    if isinstance(identity, dict):
        for key, value in identity.items():
            child_paths = artifact_identity_placeholder_fields(value)
            placeholders.extend(f"{key}.{path}" if path else str(key) for path in child_paths)
    elif isinstance(identity, list):
        for index, value in enumerate(identity):
            child_paths = artifact_identity_placeholder_fields(value)
            placeholders.extend(f"[{index}].{path}" if path else f"[{index}]" for path in child_paths)
    elif isinstance(identity, str) and identity.casefold().startswith(PLACEHOLDER_ARTIFACT_ID_PREFIXES):
        placeholders.append("")
    return placeholders


def complete_artifact_identity(
    payload: dict[str, object],
    *,
    container_key: str | None = "artifact_identity",
    allowed_artifact_kinds: set[str] | None = None,
    expected_artifact_kind: str | None = None,
) -> tuple[dict[str, str] | None, list[str]]:
    identity: object
    if container_key is None:
        identity = payload
    else:
        identity = payload.get(container_key)

    if not isinstance(identity, dict):
        return None, ["missing_artifact_identity"]

    if set(identity) != set(ARTIFACT_IDENTITY_KEYS):
        return None, ["artifact_identity_fields_mismatch"]

    errors: list[str] = []
    artifact_kind = identity.get("artifact_kind")
    if not isinstance(artifact_kind, str):
        errors.append("artifact_kind_invalid")
    elif expected_artifact_kind is not None and artifact_kind != expected_artifact_kind:
        errors.append("artifact_kind_invalid")
    elif allowed_artifact_kinds is not None and artifact_kind not in allowed_artifact_kinds:
        errors.append("artifact_kind_invalid")

    artifact_sha256 = identity.get("artifact_sha256")
    if not is_sha256(artifact_sha256):
        errors.append("artifact_sha256_invalid")

    capture_id = identity.get("capture_id")
    if not is_safe_artifact_id(capture_id):
        errors.append("capture_id_invalid")

    evidence_pack_id = identity.get("evidence_pack_id")
    if not is_safe_artifact_id(evidence_pack_id):
        errors.append("evidence_pack_id_invalid")

    if errors:
        return None, errors

    return (
        {
            "artifact_kind": str(artifact_kind),
            "artifact_sha256": str(artifact_sha256),
            "capture_id": str(capture_id),
            "evidence_pack_id": str(evidence_pack_id),
        },
        [],
    )
