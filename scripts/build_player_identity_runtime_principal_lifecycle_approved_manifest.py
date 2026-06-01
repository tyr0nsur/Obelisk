#!/usr/bin/env python3
"""Build a consume-only approved player-principal lifecycle evidence manifest.

The input is the copied/offline JSON summary produced by
analyze_runtime_observer_log.py. This helper does not read server logs, does not start
servers, and does not promote public player identity or SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from artifact_identity import canonical_json_bytes


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
WINDOW_CHECK_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
EXPECTED_MODULE = "player_principal_lifecycle"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
EXPECTED_COPIED_LOG_PATH_STATUS = "approved_offline_workspace"
FORBIDDEN_REVIEW_TEXT_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace)|object[_-]?address)",
    re.IGNORECASE,
)

REQUIRED_NON_CLAIMS = [
    "approved runtime observer evidence only",
    (
        "does not promote public player identity, lookup, permissions, commands, moderation, "
        "admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness"
    ),
    (
        "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, "
        "GObjects, raw params, or persistent lookup keys"
    ),
    "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
]


def output_artifact_identity(payload: dict[str, Any], *, capture_id: str, evidence_pack_id: str) -> dict[str, str]:
    identity_without_hash = {
        "artifact_kind": SCHEMA,
        "capture_id": capture_id,
        "evidence_pack_id": evidence_pack_id,
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": payload,
    }
    return {
        **identity_without_hash,
        "artifact_sha256": hashlib.sha256(canonical_json_bytes(material)).hexdigest(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-summary",
        required=True,
        type=Path,
        help="Copied/offline JSON summary produced by analyze_runtime_observer_log.py.",
    )
    parser.add_argument(
        "--window-manifest-check",
        required=True,
        type=Path,
        help="JSON report produced by check_player_identity_runtime_principal_lifecycle_window_manifest.py.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Manifest JSON output path.")
    parser.add_argument(
        "--reviewed-by",
        required=True,
        help="Reviewer token/name recorded under approval.reviewed_by.",
    )
    parser.add_argument(
        "--review-note",
        required=True,
        help="Short review note recorded under approval.review_note.",
    )
    return parser.parse_args()


def is_under_path(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def first_symlink_component(path: Path) -> Path | None:
    expanded = path.expanduser()
    candidate = expanded if expanded.is_absolute() else expanded.absolute()
    current = Path(candidate.anchor) if candidate.anchor else Path()
    parts = candidate.parts[1:] if candidate.anchor else candidate.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return current
    return None


def reject_symlink_component(path: Path, label: str) -> None:
    symlink = first_symlink_component(path)
    if symlink is not None:
        raise SystemExit(f"{label} must not be a symlink: {symlink}")


def protected_path_status(path: Path) -> tuple[bool, Path]:
    expanded = path.expanduser()
    resolved = expanded.resolve()
    protected = SERVER_ROOT.resolve()
    direct_protected = expanded.is_absolute() and is_under_path(expanded, SERVER_ROOT)
    resolved_protected = is_under_path(resolved, protected)
    approved_offline = any(
        expanded.is_absolute()
        and is_under_path(expanded, root)
        and is_under_path(resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    )
    return (direct_protected or resolved_protected) and not approved_offline, resolved


def reject_protected_path(path: Path, label: str, *, write: bool = False) -> Path:
    blocked, resolved = protected_path_status(path)
    if blocked:
        action = "write under" if write else "read from"
        raise SystemExit(f"{label} must not {action} protected server root {SERVER_ROOT}: {resolved}")
    return resolved


def load_summary(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "--source-summary")
    resolved = reject_protected_path(path, "--source-summary")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{resolved}: source summary does not exist") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: source summary top-level JSON must be an object")
    return payload


def load_window_check(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "--window-manifest-check")
    resolved = reject_protected_path(path, "--window-manifest-check")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"{resolved}: window manifest check does not exist") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{resolved}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{resolved}: window manifest check top-level JSON must be an object")
    return payload


def reject_if_forbidden_review_text(value: str, label: str) -> None:
    if not value.strip():
        raise SystemExit(f"{label} must not be empty")
    if FORBIDDEN_REVIEW_TEXT_RE.search(value):
        raise SystemExit(f"{label} contains identity/UE-internal terms that would not pass the privacy gate")


def path_is_copied_or_offline(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    blocked, _ = protected_path_status(Path(path_text))
    return not blocked


def path_is_approved_offline_workspace(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    blocked, resolved = protected_path_status(Path(path_text))
    if blocked:
        return False
    return any(
        Path(path_text).expanduser().is_absolute()
        and is_under_path(Path(path_text).expanduser(), root)
        and is_under_path(resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    )


def validate_source_summary(summary: dict[str, Any]) -> None:
    if summary.get("schema") != SUMMARY_SCHEMA:
        raise SystemExit(f"--source-summary schema must be {SUMMARY_SCHEMA}")
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        raise SystemExit("--source-summary must include evidence object from analyzer")
    if evidence.get("kind") != "runtime-observer-log":
        raise SystemExit("--source-summary evidence.kind must be runtime-observer-log")
    if evidence.get("server_paths_allowed") is not False:
        raise SystemExit("--source-summary must be generated without --allow-server-path")
    sources = evidence.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        raise SystemExit("--source-summary evidence.sources must contain exactly one copied/offline log")
    for index, source in enumerate(sources):
        if not isinstance(source, dict) or not path_is_copied_or_offline(source.get("path")):
            raise SystemExit(
                "--source-summary evidence.sources "
                f"[{index}].path must point to copied/offline evidence, not a protected server path"
            )
        if not path_is_approved_offline_workspace(source.get("path")):
            raise SystemExit(
                "--source-summary evidence.sources "
                f"[{index}].path must point under /servidor/ark/workspace-offline"
            )
    modules = summary.get("modules")
    if not isinstance(modules, dict):
        raise SystemExit("--source-summary must include modules object")
    module_names = set(modules)
    if module_names != {EXPECTED_MODULE}:
        observed = ", ".join(sorted(module_names)) or "<none>"
        raise SystemExit(
            "--source-summary modules must contain only "
            f"{EXPECTED_MODULE}; observed: {observed}"
        )


def validate_window_check(window: dict[str, Any], summary: dict[str, Any]) -> None:
    if window.get("schema") != WINDOW_CHECK_SCHEMA:
        raise SystemExit(f"--window-manifest-check schema must be {WINDOW_CHECK_SCHEMA}")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        raise SystemExit("--window-manifest-check must be ready")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if window.get(key) is not False:
            raise SystemExit(f"--window-manifest-check {key} must remain false")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        raise SystemExit("--window-manifest-check must include copied_log object")
    if copied.get("path_status") != EXPECTED_COPIED_LOG_PATH_STATUS:
        raise SystemExit("--window-manifest-check copied_log.path_status must be approved_offline_workspace")
    if not path_is_approved_offline_workspace(copied.get("path")):
        raise SystemExit("--window-manifest-check copied_log.path must point under /servidor/ark/workspace-offline")
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        raise SystemExit("--source-summary must include evidence.sources[0]")
    source = sources[0]
    if Path(str(copied.get("path", ""))).expanduser().resolve() != Path(str(source.get("path", ""))).expanduser().resolve():
        raise SystemExit("--window-manifest-check copied_log.path must match source summary path")
    if copied.get("sha256") != source.get("sha256"):
        raise SystemExit("--window-manifest-check copied_log.sha256 must match source summary sha256")
    evidence_commit = evidence.get("obelisk_commit") if isinstance(evidence, dict) else None
    if window.get("obelisk_commit") != evidence_commit:
        raise SystemExit("--window-manifest-check obelisk_commit must match source summary obelisk_commit")


def build_manifest(
    summary: dict[str, Any],
    window: dict[str, Any],
    *,
    reviewed_by: str,
    review_note: str,
) -> dict[str, Any]:
    manifest = {
        "schema": SCHEMA,
        "artifact_status": "approved_runtime_observer_summary",
        "readiness_classification": "runtime_evidence_only",
        "approved_runtime_evidence_present": True,
        "runtime_evidence_ready": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "approval": {
            "runtime_evidence_reviewed": True,
            "reviewed_by": reviewed_by,
            "review_note": review_note,
            "runtime_work_authorized_by_this_manifest": False,
            "server_operations_authorized_by_this_manifest": False,
            "publication_authorized_by_this_manifest": False,
            "discord_authorized_by_this_manifest": False,
        },
        "operational_window": {
            "schema": window.get("schema"),
            "ready": window.get("ready"),
            "operational_window_manifest_ready": window.get("operational_window_manifest_ready"),
            "run_id": window.get("run_id"),
            "obelisk_commit": window.get("obelisk_commit"),
            "target": window.get("target"),
            "copied_log": window.get("copied_log"),
            "posture": window.get("posture"),
            "rollback": window.get("rollback"),
            "claims": window.get("claims"),
            "user_policy": window.get("user_policy"),
            "promotion_ready": window.get("promotion_ready"),
            "public_sdk_ready": window.get("public_sdk_ready"),
            "runtime_ready": window.get("runtime_ready"),
        },
        "source_summary": summary,
        "consumer_boundary_cases": [
            {
                "case": "stale_after_logout",
                "result": "fail_closed",
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
            {
                "case": "malformed_or_unsupported_evidence",
                "result": "fail_closed",
                "lookup_allowed": False,
                "mutation_allowed": False,
                "return_override_allowed": False,
                "public_sdk_surface": False,
            },
        ],
        "privacy_boundary": {
            "copied_opaque_principal_only": True,
            "redacted_runtime_observer": True,
            "player_identifiers_logged": False,
            "lookup_allowed": False,
            "resource_handle_allowed": False,
            "mutation_allowed": False,
            "return_override_allowed": False,
        },
        "promotion_gate": {
            "runtime_evidence_ready": True,
            "ready": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "non_claims": REQUIRED_NON_CLAIMS,
    }
    run_id = str(window.get("run_id"))
    manifest["output_artifact_identity"] = output_artifact_identity(
        manifest,
        capture_id=run_id,
        evidence_pack_id=f"player-principal-lifecycle-{run_id}",
    )
    return manifest


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    reject_symlink_component(path, "--output")
    resolved = reject_protected_path(path, "--output", write=True)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    fd = -1
    temp_name = ""
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{resolved.name}.",
            suffix=".tmp",
            dir=str(resolved.parent),
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(text)
        os.replace(temp_name, resolved)
    finally:
        if fd != -1:
            os.close(fd)
        if temp_name:
            try:
                Path(temp_name).unlink()
            except FileNotFoundError:
                pass


def main() -> int:
    args = parse_args()
    reject_if_forbidden_review_text(args.reviewed_by, "--reviewed-by")
    reject_if_forbidden_review_text(args.review_note, "--review-note")
    summary = load_summary(args.source_summary)
    window = load_window_check(args.window_manifest_check)
    validate_source_summary(summary)
    validate_window_check(window, summary)
    manifest = build_manifest(
        summary,
        window,
        reviewed_by=args.reviewed_by.strip(),
        review_note=args.review_note.strip(),
    )
    write_json_atomic(args.output, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
