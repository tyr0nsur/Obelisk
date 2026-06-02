#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle runtime window manifest.

The manifest is the secret-free `key=value` sidecar kept beside a copied Obelisk log.
This checker validates operational posture only. It does not approve public identity,
plugin delivery, permissions, commands, lookup, mutation, or runtime SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import reject_symlink_component


REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
NEXT_BLOCKER_AFTER_WINDOW_MANIFEST = "approved_runtime_observer_log_summary_and_manifest_missing"
WINDOW_REQUEST_CHECKER = Path(__file__).resolve().parent / "check_player_principal_lifecycle_window_request.py"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"

RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PREFLIGHT_SCHEMA = "obelisk.player-principal-lifecycle-preflight.v1"
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")
FORBIDDEN_KEY_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|hashed[_-]?(?:private|identity|identifier|player))",
    re.IGNORECASE,
)
FORBIDDEN_VALUE_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|\bip(?:v4|v6)?\b|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|hashed[_-]?(?:private|identity|identifier|player))",
    re.IGNORECASE,
)
POSITIVE_CAPABILITY_VALUE_RE = re.compile(
    r"(?:public[_ -]?(?:sdk|player[_ -]?identity)|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)

REQUIRED_TIMESTAMP_FIELDS = (
    "approved_window_start_utc",
    "approved_window_end_utc",
    "actual_capture_start_utc",
    "actual_capture_end_utc",
    "rollback_start_utc",
    "rollback_end_utc",
)
REQUIRED_SIMPLE_FIELDS = (
    "run_id",
    "obelisk_commit",
    "approval",
    "copied_log_path",
    "copied_log_sha256",
    "request_pack_path",
    "request_pack_sha256",
    "observer_env_path",
    "observer_env_sha256",
    "preflight_pre_path",
    "preflight_pre_sha256",
    "preflight_post_path",
    "preflight_post_sha256",
    "pre_posture",
    "post_posture",
    "pre_check",
    "post_check",
    "rollback_completed",
    "rollback_delta",
    "observer_env_survived",
    "observer_marker_survived",
    "sibling_marker_entries",
    "sibling_observer_env",
    "log_budget",
    "plugins_disabled",
    "scanner_disabled",
    "dispatch_limit",
    "wrapper_profile",
    "observer_exclusivity",
    "debug_escape_markers",
    "callback_escape_markers",
    "native_exec_disabled",
    "ptrace_disabled",
    "single_module_summary",
    "delivery_claim",
    "principal_claim",
)
ACCEPTED_USER_POLICIES = frozenset(("no_regular_users", "operator_approved_beta_users"))
EXPECTED_APPROVAL = "current-turn operator-approved runtime window, not standing approval"
EXPECTED_ROLLBACK_DELTA = "removed_observer_env_and_markers_preserved_disable_plugins"
ALLOWED_FIELDS = frozenset(
    (
        *REQUIRED_TIMESTAMP_FIELDS,
        *REQUIRED_SIMPLE_FIELDS,
        "target",
        "instance",
        "instance_id",
        "map",
        "map_name",
        "user_policy",
        "users_policy",
        "notice_sent",
    )
)


@dataclass
class Target:
    instance: str | None
    map_name: str | None


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    target: Target
    user_policy: str | None
    copied_log_status: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, nargs="?", help="Offline key=value window manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument(
        "--emit-template",
        type=Path,
        help="Write a canonical secret-free key=value window manifest template and exit.",
    )
    parser.add_argument(
        "--copied-log",
        type=Path,
        help=(
            "When used with --emit-template, fill copied_log_path, copied_log_sha256, "
            "and run_id from an existing approved-workspace live-validation log copy."
        ),
    )
    parser.add_argument(
        "--post-window-replay",
        action="store_true",
        help=(
            "Validate a completed copied evidence window after its approved runtime window "
            "has expired. This tolerates only the nested approved_window_expired request "
            "checker blocker; pre-window approval checks remain strict by default."
        ),
    )
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_manifest(path: Path) -> dict[str, str]:
    reject_symlink_component(path, "manifest")
    path = protected_paths.reject_protected_input_path(
        path,
        "manifest",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    fields: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SystemExit(f"{path}:{line_number}: expected key=value")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not SAFE_COMPONENT_RE.fullmatch(key):
            raise SystemExit(f"{path}:{line_number}: unsafe manifest key: {key}")
        if key in fields:
            raise SystemExit(f"{path}:{line_number}: duplicate manifest key: {key}")
        fields[key] = value
    return fields


def manifest_relative_path(value: str, manifest_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return manifest_path.parent / path


def parse_bool(value: str | None) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def parse_utc_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.removesuffix("Z") + "+00:00").astimezone(timezone.utc)


def is_exact_or_test_fixture_run_log(path: Path, run_id: str) -> bool:
    expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
    for root in APPROVED_OFFLINE_WORKSPACE_ROOTS:
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            continue
        parts = relative.parts
        if parts == expected_tail:
            return True
        if (
            os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") == "1"
            and len(parts) == 4
            and parts[0].startswith("obelisk-test-player-principal-")
            and parts[1:] == expected_tail
        ):
            return True
    return False


def is_test_fixture_workspace_path(path: Path) -> bool:
    if os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") != "1":
        return False
    for root in APPROVED_OFFLINE_WORKSPACE_ROOTS:
        try:
            relative = path.relative_to(root.resolve())
        except ValueError:
            continue
        return bool(relative.parts and relative.parts[0].startswith("obelisk-test-player-principal-"))
    return False


def validate_target(fields: dict[str, str], blockers: list[dict[str, Any]]) -> Target:
    instance = fields.get("instance") or fields.get("instance_id")
    map_name = fields.get("map") or fields.get("map_name")
    target = fields.get("target")

    if target:
        parts = target.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            add(blockers, "target_must_be_instance_slash_map", "target")
        else:
            target_instance, target_map = parts
            if instance and instance != target_instance:
                add(blockers, "target_instance_mismatch", "target", target=target_instance, instance=instance)
            if map_name and map_name != target_map:
                add(blockers, "target_map_mismatch", "target", target=target_map, map=map_name)
            instance = instance or target_instance
            map_name = map_name or target_map

    if not instance:
        add(blockers, "instance_missing", "instance")
    elif not SAFE_COMPONENT_RE.fullmatch(instance):
        add(blockers, "instance_invalid", "instance")

    if not map_name:
        add(blockers, "map_missing", "map")
    elif not SAFE_COMPONENT_RE.fullmatch(map_name):
        add(blockers, "map_invalid", "map")

    return Target(instance=instance, map_name=map_name)


def validate_copied_log_path(fields: dict[str, str], manifest_path: Path, blockers: list[dict[str, Any]]) -> str | None:
    path_text = fields.get("copied_log_path")
    if not path_text:
        return None
    copied_log_path = manifest_relative_path(path_text, manifest_path)
    reject_symlink_component(copied_log_path, "copied_log_path")
    status = protected_paths.protected_path_status(
        copied_log_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(
            blockers,
            "copied_log_path_under_protected_server_root",
            "copied_log_path",
            resolved=str(status.resolved),
        )
        return "protected"
    run_id = fields.get("run_id")
    if run_id and run_id not in copied_log_path.parts:
        add(blockers, "copied_log_path_run_id_mismatch", "copied_log_path", run_id=run_id)
    if run_id:
        expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
        if copied_log_path.parts[-3:] != expected_tail:
            add(
                blockers,
                "copied_log_path_not_live_validation_run_log",
                "copied_log_path",
                expected="/".join(expected_tail),
            )
        expected_path = APPROVED_OFFLINE_WORKSPACE_ROOTS[0].resolve() / EXPECTED_COPIED_LOG_PARENT / run_id / "Obelisk.log"
        if status.approved_offline_workspace and not is_exact_or_test_fixture_run_log(status.resolved, run_id):
            add(
                blockers,
                "copied_log_path_not_exact_approved_run_log",
                "copied_log_path",
                expected=str(expected_path),
                resolved=str(status.resolved),
            )
        manifest_status = protected_paths.protected_path_status(
            manifest_path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        allow_test_fixture_manifest = is_test_fixture_workspace_path(manifest_status.resolved)
        if manifest_path.name != "window-manifest.env" and not allow_test_fixture_manifest:
            add(blockers, "window_manifest_filename_mismatch", "manifest", expected="window-manifest.env")
        if manifest_status.resolved.parent != status.resolved.parent and not allow_test_fixture_manifest:
            add(
                blockers,
                "window_manifest_not_beside_copied_log",
                "manifest",
                expected=str(status.resolved.parent / "window-manifest.env"),
                resolved=str(manifest_status.resolved),
            )

    expected_sha256 = fields.get("copied_log_sha256")
    if expected_sha256 == "0" * 64:
        add(blockers, "copied_log_sha256_placeholder", "copied_log_sha256")
    if not copied_log_path.is_file():
        add(blockers, "copied_log_file_missing", "copied_log_path", resolved=str(status.resolved))
    elif expected_sha256 and SHA256_RE.fullmatch(expected_sha256):
        actual_sha256 = hashlib.sha256(copied_log_path.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            add(
                blockers,
                "copied_log_sha256_mismatch",
                "copied_log_sha256",
                expected=expected_sha256,
                actual=actual_sha256,
            )
    if status.approved_offline_workspace:
        return "approved_offline_workspace"
    add(
        blockers,
        "copied_log_path_not_under_approved_offline_workspace",
        "copied_log_path",
        expected="/servidor/ark/workspace-offline/live-validation-logs/<run-id>/Obelisk.log",
        resolved=str(status.resolved),
    )
    return "unprotected_offline"


def validate_sidecar_file(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    path_key: str,
    sha_key: str,
    expected_name: str | None = None,
) -> str | None:
    path_text = fields.get(path_key)
    sha_text = fields.get(sha_key)
    if not path_text:
        return None
    path = manifest_relative_path(path_text, manifest_path)
    reject_symlink_component(path, path_key)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        add(blockers, f"{path_key}_under_protected_server_root", path_key, resolved=str(status.resolved))
        return "protected"
    if not status.approved_offline_workspace:
        add(blockers, f"{path_key}_not_under_approved_offline_workspace", path_key, resolved=str(status.resolved))
    if expected_name is not None and status.resolved.name != expected_name:
        add(blockers, f"{path_key}_filename_mismatch", path_key, expected=expected_name, resolved=str(status.resolved))
    run_id = fields.get("run_id")
    if run_id and run_id not in status.resolved.parts:
        add(blockers, f"{path_key}_run_id_mismatch", path_key, run_id=run_id, resolved=str(status.resolved))
    if not sha_text:
        add(blockers, f"{sha_key}_missing", sha_key)
    elif SHA256_RE.fullmatch(sha_text) is None:
        add(blockers, f"{sha_key}_invalid", sha_key)
    elif sha_text == "0" * 64:
        add(blockers, f"{sha_key}_placeholder", sha_key)
    if not status.resolved.is_file():
        add(blockers, f"{path_key}_file_missing", path_key, resolved=str(status.resolved))
    elif sha_text and SHA256_RE.fullmatch(sha_text):
        actual_sha256 = hashlib.sha256(status.resolved.read_bytes()).hexdigest()
        if actual_sha256 != sha_text:
            add(blockers, f"{sha_key}_mismatch", sha_key, expected=sha_text, actual=actual_sha256)
    return "approved_offline_workspace" if status.approved_offline_workspace else "unprotected_offline"


def validate_preflight_content(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    path_key: str,
    expected_mode: str,
    target: Target,
) -> None:
    path_text = fields.get(path_key)
    if not path_text or not target.instance:
        return
    path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace or not status.resolved.is_file():
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{path_key}_unreadable", path_key, detail=str(exc))
        return
    except json.JSONDecodeError as exc:
        add(blockers, f"{path_key}_json_invalid", path_key, detail=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, f"{path_key}_not_object", path_key)
        return

    if payload.get("schema") != PREFLIGHT_SCHEMA:
        add(blockers, f"{path_key}_schema_mismatch", path_key, expected=PREFLIGHT_SCHEMA, actual=payload.get("schema"))
    if payload.get("ready") is not True:
        add(blockers, f"{path_key}_ready_not_true", path_key)
    if payload.get("posture_check") != "accepted":
        add(blockers, f"{path_key}_posture_check_not_accepted", path_key)
    if payload.get("mode") != expected_mode:
        add(blockers, f"{path_key}_mode_mismatch", path_key, expected=expected_mode, actual=payload.get("mode"))
    if payload.get("instance") != target.instance:
        add(blockers, f"{path_key}_instance_mismatch", path_key, expected=target.instance, actual=payload.get("instance"))
    if payload.get("run_id") != fields.get("run_id"):
        add(blockers, f"{path_key}_run_id_mismatch", path_key, expected=fields.get("run_id"), actual=payload.get("run_id"))
    if payload.get("map") != target.map_name:
        add(blockers, f"{path_key}_map_mismatch", path_key, expected=target.map_name, actual=payload.get("map"))

    preflight_target = payload.get("target")
    if not isinstance(preflight_target, dict):
        add(blockers, f"{path_key}_target_missing", path_key)
    else:
        if preflight_target.get("instance") != target.instance:
            add(
                blockers,
                f"{path_key}_target_instance_mismatch",
                path_key,
                expected=target.instance,
                actual=preflight_target.get("instance"),
            )
        if preflight_target.get("map") != target.map_name:
            add(
                blockers,
                f"{path_key}_target_map_mismatch",
                path_key,
                expected=target.map_name,
                actual=preflight_target.get("map"),
            )

    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at_utc) is None:
        add(blockers, f"{path_key}_checked_at_utc_invalid", path_key, actual=checked_at_utc)

    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    expected_manifest_path = str(manifest_status.resolved)
    if payload.get("window_manifest_path") != expected_manifest_path:
        add(
            blockers,
            f"{path_key}_window_manifest_path_mismatch",
            path_key,
            expected=expected_manifest_path,
            actual=payload.get("window_manifest_path"),
        )

    copied_log_text = fields.get("copied_log_path")
    if copied_log_text:
        copied_log_status = protected_paths.protected_path_status(
            manifest_relative_path(copied_log_text, manifest_path),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_copied_log_path = str(copied_log_status.resolved)
        expected_evidence_dir = str(copied_log_status.resolved.parent)
        if payload.get("copied_log_path") != expected_copied_log_path:
            add(
                blockers,
                f"{path_key}_copied_log_path_mismatch",
                path_key,
                expected=expected_copied_log_path,
                actual=payload.get("copied_log_path"),
            )
        if payload.get("copied_evidence_dir") != expected_evidence_dir:
            add(
                blockers,
                f"{path_key}_copied_evidence_dir_mismatch",
                path_key,
                expected=expected_evidence_dir,
                actual=payload.get("copied_evidence_dir"),
            )

    server_binary = payload.get("server_binary")
    if not isinstance(server_binary, dict):
        add(blockers, f"{path_key}_server_binary_missing", path_key)
    elif server_binary.get("sha256") != EXPECTED_BINARY_SHA256:
        add(
            blockers,
            f"{path_key}_binary_sha256_mismatch",
            path_key,
            expected=EXPECTED_BINARY_SHA256,
            actual=server_binary.get("sha256"),
        )

    installed_wrapper = payload.get("installed_wrapper")
    if not isinstance(installed_wrapper, dict):
        add(blockers, f"{path_key}_installed_wrapper_missing", path_key)
    elif SHA256_RE.fullmatch(str(installed_wrapper.get("sha256", ""))) is None:
        add(blockers, f"{path_key}_installed_wrapper_sha256_invalid", path_key)

    marker_dir = payload.get("marker_dir")
    if not isinstance(marker_dir, str) or not marker_dir.endswith(f"/state/instances/{target.instance}"):
        add(blockers, f"{path_key}_marker_dir_instance_mismatch", path_key, actual=marker_dir)

    env_file = payload.get("env_file")
    if expected_mode == "observer-window":
        observer_env_text = fields.get("observer_env_path")
        observer_env_sha256 = fields.get("observer_env_sha256")
        if not isinstance(env_file, dict):
            add(blockers, f"{path_key}_env_file_missing", path_key)
        else:
            observer_env_path = manifest_relative_path(observer_env_text, manifest_path) if observer_env_text else None
            if observer_env_path is None:
                add(blockers, f"{path_key}_observer_env_path_missing", path_key)
            else:
                observer_env_status = protected_paths.protected_path_status(
                    observer_env_path,
                    protected_root=SERVER_ROOT,
                    approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
                )
                if env_file.get("path") != str(observer_env_status.resolved):
                    add(
                        blockers,
                        f"{path_key}_env_file_path_mismatch",
                        path_key,
                        expected=str(observer_env_status.resolved),
                        actual=env_file.get("path"),
                    )
            if env_file.get("sha256") != observer_env_sha256:
                add(
                    blockers,
                    f"{path_key}_env_file_sha256_mismatch",
                    path_key,
                    expected=observer_env_sha256,
                    actual=env_file.get("sha256"),
                )
    elif env_file is not None:
        add(blockers, f"{path_key}_env_file_unexpected", path_key)


def read_preflight_checked_at_utc(
    fields: dict[str, str],
    manifest_path: Path,
    *,
    path_key: str,
) -> datetime | None:
    path_text = fields.get(path_key)
    if not path_text:
        return None
    path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace or not status.resolved.is_file():
        return None
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    checked_at_utc = payload.get("checked_at_utc")
    if not isinstance(checked_at_utc, str) or UTC_TIMESTAMP_RE.fullmatch(checked_at_utc) is None:
        return None
    return parse_utc_timestamp(checked_at_utc)


def request_check_failed_only_because_window_expired(request_check_blockers: Any) -> bool:
    return isinstance(request_check_blockers, list) and set(request_check_blockers) == {"approved_window_expired"}


def validate_request_pack(
    fields: dict[str, str],
    manifest_path: Path,
    blockers: list[dict[str, Any]],
    *,
    post_window_replay: bool = False,
) -> None:
    path_text = fields.get("request_pack_path")
    if not path_text:
        return
    request_path = manifest_relative_path(path_text, manifest_path)
    status = protected_paths.protected_path_status(
        request_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace or not status.resolved.is_file():
        return
    try:
        payload = json.loads(status.resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "request_pack_json_invalid", "request_pack_path", detail=str(exc))
        return
    if not isinstance(payload, dict):
        add(blockers, "request_pack_not_object", "request_pack_path")
        return
    if payload.get("schema") != "obelisk.player-principal-lifecycle-window-request.v1":
        add(blockers, "request_pack_schema_mismatch", "request_pack_path")
    if payload.get("run_id") != fields.get("run_id"):
        add(blockers, "request_pack_run_id_mismatch", "request_pack_path")
    if payload.get("obelisk_commit") != fields.get("obelisk_commit"):
        add(
            blockers,
            "request_pack_obelisk_commit_mismatch",
            "request_pack_path",
            expected=fields.get("obelisk_commit"),
            actual=payload.get("obelisk_commit"),
        )
    if payload.get("ark_binary_sha256") != EXPECTED_BINARY_SHA256:
        add(
            blockers,
            "request_pack_ark_binary_sha256_mismatch",
            "request_pack_path",
            expected=EXPECTED_BINARY_SHA256,
            actual=payload.get("ark_binary_sha256"),
        )
    copied_log_text = fields.get("copied_log_path")
    if copied_log_text:
        copied_log_status = protected_paths.protected_path_status(
            manifest_relative_path(copied_log_text, manifest_path),
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        expected_log_path = str(copied_log_status.resolved)
        expected_evidence_dir = str(copied_log_status.resolved.parent)
        if payload.get("copied_log_path") != expected_log_path:
            add(
                blockers,
                "request_pack_copied_log_path_manifest_mismatch",
                "request_pack_path",
                expected=expected_log_path,
                actual=payload.get("copied_log_path"),
            )
        if payload.get("copied_evidence_dir") != expected_evidence_dir:
            add(
                blockers,
                "request_pack_copied_evidence_dir_manifest_mismatch",
                "request_pack_path",
                expected=expected_evidence_dir,
                actual=payload.get("copied_evidence_dir"),
            )
    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    expected_manifest_path = str(manifest_status.resolved)
    if payload.get("window_manifest_path") != expected_manifest_path:
        add(
            blockers,
            "request_pack_window_manifest_path_manifest_mismatch",
            "request_pack_path",
            expected=expected_manifest_path,
            actual=payload.get("window_manifest_path"),
        )
    target = payload.get("target")
    if isinstance(target, dict):
        instance = fields.get("instance") or fields.get("instance_id")
        map_name = fields.get("map") or fields.get("map_name")
        if fields.get("target") and "/" in fields["target"]:
            instance, map_name = fields["target"].split("/", 1)
        if target.get("instance") != instance:
            add(blockers, "request_pack_instance_mismatch", "request_pack_path")
        if target.get("map") != map_name:
            add(blockers, "request_pack_map_mismatch", "request_pack_path")
    else:
        add(blockers, "request_pack_target_missing", "request_pack_path")
    approved_window = payload.get("approved_window")
    if isinstance(approved_window, dict):
        if approved_window.get("start_utc") != fields.get("approved_window_start_utc"):
            add(blockers, "request_pack_approved_window_start_mismatch", "request_pack_path")
        if approved_window.get("end_utc") != fields.get("approved_window_end_utc"):
            add(blockers, "request_pack_approved_window_end_mismatch", "request_pack_path")
    else:
        add(blockers, "request_pack_approved_window_missing", "request_pack_path")

    observer_env_text = fields.get("observer_env_path")
    if not observer_env_text:
        return
    observer_env_path = manifest_relative_path(observer_env_text, manifest_path)
    result = subprocess.run(
        [
            sys.executable,
            str(WINDOW_REQUEST_CHECKER),
            "--json",
            str(status.resolved),
            "--env-file",
            str(observer_env_path),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload_check: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            parsed = json.loads(result.stdout)
            if isinstance(parsed, dict):
                payload_check = parsed
        except json.JSONDecodeError:
            payload_check = None
    request_check_blockers = (payload_check or {}).get("blockers", [])
    replay_tolerated_expiry = (
        post_window_replay
        and result.returncode != 0
        and isinstance(payload_check, dict)
        and payload_check.get("ready") is not True
        and payload_check.get("request_pack_ready") is not True
        and request_check_failed_only_because_window_expired(request_check_blockers)
    )
    if not replay_tolerated_expiry and (
        result.returncode != 0
        or not isinstance(payload_check, dict)
        or payload_check.get("ready") is not True
        or payload_check.get("request_pack_ready") is not True
    ):
        add(
            blockers,
            "request_pack_window_request_check_failed",
            "request_pack_path",
            exit_code=result.returncode,
            request_check_blockers=request_check_blockers,
        )


def validate_user_policy(fields: dict[str, str], blockers: list[dict[str, Any]]) -> str | None:
    has_new = "user_policy" in fields
    has_legacy = "users_policy" in fields
    if has_new and has_legacy:
        add(blockers, "user_policy_alias_ambiguous", "user_policy")
        return fields.get("user_policy")
    value = fields.get("user_policy") or fields.get("users_policy")
    if value is None:
        add(blockers, "user_policy_missing", "user_policy")
        return None
    if value not in ACCEPTED_USER_POLICIES:
        add(blockers, "user_policy_not_accepted", "user_policy", accepted=sorted(ACCEPTED_USER_POLICIES))
    if value == "operator_approved_beta_users" and fields.get("notice_sent") != "true":
        add(blockers, "beta_user_policy_requires_notice_sent", "notice_sent")
    return value


def validate_manifest(
    fields: dict[str, str],
    manifest_path: Path,
    *,
    post_window_replay: bool = False,
) -> Validation:
    blockers: list[dict[str, Any]] = []
    timestamps: dict[str, datetime] = {}
    for key in sorted(fields):
        if key not in ALLOWED_FIELDS:
            add(blockers, "unexpected_field", key)
        if key not in ALLOWED_FIELDS and FORBIDDEN_KEY_RE.search(key):
            add(blockers, "forbidden_identity_or_ue_field", key)
        if FORBIDDEN_VALUE_RE.search(fields[key]):
            add(blockers, "forbidden_identity_or_ue_value", key)
        if POSITIVE_CAPABILITY_VALUE_RE.search(fields[key]):
            add(blockers, "forbidden_public_capability_or_readiness_value", key)
    for key in REQUIRED_SIMPLE_FIELDS:
        if key not in fields:
            add(blockers, "required_field_missing", key)
    for key in REQUIRED_TIMESTAMP_FIELDS:
        value = fields.get(key)
        if value is None:
            add(blockers, "required_field_missing", key)
        elif not UTC_TIMESTAMP_RE.fullmatch(value):
            add(blockers, "utc_timestamp_invalid", key)
        else:
            timestamps[key] = parse_utc_timestamp(value)

    run_id = fields.get("run_id")
    if run_id is not None and RUN_ID_RE.fullmatch(run_id) is None:
        add(blockers, "run_id_invalid", "run_id")
    obelisk_commit = fields.get("obelisk_commit")
    if obelisk_commit is not None and not is_reviewed_obelisk_commit(obelisk_commit):
        add(blockers, "obelisk_commit_invalid", "obelisk_commit")

    copied_log_sha256 = fields.get("copied_log_sha256")
    if copied_log_sha256 is not None and SHA256_RE.fullmatch(copied_log_sha256) is None:
        add(blockers, "copied_log_sha256_invalid", "copied_log_sha256")
    if fields.get("approval") != EXPECTED_APPROVAL:
        add(blockers, "approval_not_current_turn_runtime_window", "approval", expected=EXPECTED_APPROVAL)

    target = validate_target(fields, blockers)
    copied_log_status = validate_copied_log_path(fields, manifest_path, blockers)
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="request_pack_path",
        sha_key="request_pack_sha256",
        expected_name="window-request.json",
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="observer_env_path",
        sha_key="observer_env_sha256",
        expected_name="observer-window.env",
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_pre_path",
        sha_key="preflight_pre_sha256",
        expected_name="preflight-pre.json",
    )
    validate_preflight_content(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_pre_path",
        expected_mode="observer-window",
        target=target,
    )
    validate_sidecar_file(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_post_path",
        sha_key="preflight_post_sha256",
        expected_name="preflight-post.json",
    )
    validate_preflight_content(
        fields,
        manifest_path,
        blockers,
        path_key="preflight_post_path",
        expected_mode="stable",
        target=target,
    )
    validate_request_pack(fields, manifest_path, blockers, post_window_replay=post_window_replay)
    user_policy = validate_user_policy(fields, blockers)

    for key in ("pre_posture", "post_posture"):
        if fields.get(key) != "stable":
            add(blockers, f"{key}_not_stable", key, expected="stable")
    for key in ("pre_check", "post_check"):
        if fields.get(key) != "passed":
            add(blockers, f"{key}_not_passed", key, expected="passed")
    for key in ("rollback_completed", "plugins_disabled", "scanner_disabled"):
        if parse_bool(fields.get(key)) is not True:
            add(blockers, f"{key}_not_true", key, expected=True)
    for key in ("observer_env_survived", "observer_marker_survived"):
        if parse_bool(fields.get(key)) is not False:
            add(blockers, f"{key}_not_false", key, expected=False)
    if fields.get("rollback_delta") != EXPECTED_ROLLBACK_DELTA:
        add(
            blockers,
            "rollback_delta_mismatch",
            "rollback_delta",
            expected=EXPECTED_ROLLBACK_DELTA,
            actual=fields.get("rollback_delta"),
        )

    if len(timestamps) == len(REQUIRED_TIMESTAMP_FIELDS):
        if timestamps["approved_window_start_utc"] >= timestamps["approved_window_end_utc"]:
            add(blockers, "approved_window_not_forward", "approved_window_end_utc")
        if timestamps["actual_capture_start_utc"] >= timestamps["actual_capture_end_utc"]:
            add(blockers, "actual_capture_not_forward", "actual_capture_end_utc")
        if timestamps["actual_capture_start_utc"] < timestamps["approved_window_start_utc"]:
            add(blockers, "actual_capture_starts_before_approved_window", "actual_capture_start_utc")
        if timestamps["actual_capture_end_utc"] > timestamps["approved_window_end_utc"]:
            add(blockers, "actual_capture_ends_after_approved_window", "actual_capture_end_utc")
        if timestamps["rollback_start_utc"] < timestamps["actual_capture_end_utc"]:
            add(blockers, "rollback_starts_before_capture_end", "rollback_start_utc")
        if timestamps["rollback_start_utc"] > timestamps["rollback_end_utc"]:
            add(blockers, "rollback_window_not_forward", "rollback_end_utc")
        preflight_pre_checked_at = read_preflight_checked_at_utc(
            fields,
            manifest_path,
            path_key="preflight_pre_path",
        )
        preflight_post_checked_at = read_preflight_checked_at_utc(
            fields,
            manifest_path,
            path_key="preflight_post_path",
        )
        if preflight_pre_checked_at is not None:
            if preflight_pre_checked_at < timestamps["approved_window_start_utc"]:
                add(
                    blockers,
                    "preflight_pre_path_checked_at_before_approved_window",
                    "preflight_pre_path",
                )
            if preflight_pre_checked_at > timestamps["actual_capture_start_utc"]:
                add(
                    blockers,
                    "preflight_pre_path_checked_at_after_capture_start",
                    "preflight_pre_path",
                )
        if preflight_post_checked_at is not None:
            if preflight_post_checked_at < timestamps["actual_capture_end_utc"]:
                add(
                    blockers,
                    "preflight_post_path_checked_at_before_capture_end",
                    "preflight_post_path",
                )
            if preflight_post_checked_at > timestamps["rollback_end_utc"]:
                add(
                    blockers,
                    "preflight_post_path_checked_at_after_rollback_end",
                    "preflight_post_path",
                )
        if (
            preflight_pre_checked_at is not None
            and preflight_post_checked_at is not None
            and preflight_pre_checked_at >= preflight_post_checked_at
        ):
            add(blockers, "preflight_checked_at_order_invalid", "preflight_post_path")

    try:
        log_budget = int(fields.get("log_budget", ""))
    except ValueError:
        add(blockers, "log_budget_not_integer", "log_budget")
    else:
        if log_budget != 10:
            add(blockers, "log_budget_not_exact_first_window_limit", "log_budget", expected=10)

    if fields.get("dispatch_limit") != "0":
        add(blockers, "dispatch_limit_not_zero", "dispatch_limit", expected="0")
    if fields.get("wrapper_profile") != "observer-debug":
        add(blockers, "wrapper_profile_not_observer_debug", "wrapper_profile", expected="observer-debug")
    if fields.get("observer_exclusivity") != "player_principal_lifecycle_only":
        add(
            blockers,
            "observer_exclusivity_not_player_principal_lifecycle_only",
            "observer_exclusivity",
            expected="player_principal_lifecycle_only",
        )
    for key in (
        "sibling_marker_entries",
        "sibling_observer_env",
        "debug_escape_markers",
        "callback_escape_markers",
    ):
        if fields.get(key) != "absent":
            add(blockers, f"{key}_not_absent", key, expected="absent")
    for key in ("native_exec_disabled", "ptrace_disabled"):
        if parse_bool(fields.get(key)) is not True:
            add(blockers, f"{key}_not_true", key, expected=True)
    if fields.get("single_module_summary") != "player_principal_lifecycle":
        add(
            blockers,
            "single_module_summary_not_player_principal_lifecycle",
            "single_module_summary",
            expected="player_principal_lifecycle",
        )
    if fields.get("delivery_claim") != "none":
        add(blockers, "delivery_claim_not_none", "delivery_claim", expected="none")
    if fields.get("principal_claim") != "none":
        add(blockers, "principal_claim_not_none", "principal_claim", expected="none")

    return Validation(
        blockers=blockers,
        target=target,
        user_policy=user_policy,
        copied_log_status=copied_log_status,
    )


def build_template_fields() -> dict[str, str]:
    return {
        "run_id": "20260601T120000Z-player-principal-lifecycle",
        "obelisk_commit": "<reviewed-40-character-lowercase-git-sha>",
        "target": "arkserver2/TheIsland",
        "approval": EXPECTED_APPROVAL,
        "approved_window_start_utc": "2026-06-01T12:00:00Z",
        "approved_window_end_utc": "2026-06-01T12:10:00Z",
        "actual_capture_start_utc": "2026-06-01T12:01:00Z",
        "actual_capture_end_utc": "2026-06-01T12:09:00Z",
        "copied_log_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/Obelisk.log"
        ),
        "copied_log_sha256": "0" * 64,
        "request_pack_path": (
            "/servidor/ark/workspace-offline/player-principal-preflight/"
            "20260601T120000Z-player-principal-lifecycle/window-request.json"
        ),
        "request_pack_sha256": "0" * 64,
        "observer_env_path": (
            "/servidor/ark/workspace-offline/player-principal-preflight/"
            "20260601T120000Z-player-principal-lifecycle/observer-window.env"
        ),
        "observer_env_sha256": "0" * 64,
        "preflight_pre_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/preflight-pre.json"
        ),
        "preflight_pre_sha256": "0" * 64,
        "preflight_post_path": (
            "/servidor/ark/workspace-offline/live-validation-logs/"
            "20260601T120000Z-player-principal-lifecycle/preflight-post.json"
        ),
        "preflight_post_sha256": "0" * 64,
        "pre_posture": "stable",
        "post_posture": "stable",
        "pre_check": "passed",
        "post_check": "passed",
        "rollback_start_utc": "2026-06-01T12:09:00Z",
        "rollback_end_utc": "2026-06-01T12:10:00Z",
        "rollback_completed": "true",
        "rollback_delta": "removed_observer_env_and_markers_preserved_disable_plugins",
        "observer_env_survived": "false",
        "observer_marker_survived": "false",
        "sibling_marker_entries": "absent",
        "sibling_observer_env": "absent",
        "user_policy": "no_regular_users",
        "notice_sent": "not_applicable",
        "log_budget": "10",
        "plugins_disabled": "true",
        "scanner_disabled": "true",
        "dispatch_limit": "0",
        "wrapper_profile": "observer-debug",
        "observer_exclusivity": "player_principal_lifecycle_only",
        "debug_escape_markers": "absent",
        "callback_escape_markers": "absent",
        "native_exec_disabled": "true",
        "ptrace_disabled": "true",
        "single_module_summary": "player_principal_lifecycle",
        "delivery_claim": "none",
        "principal_claim": "none",
    }


def template_fields_from_copied_log(copied_log: Path) -> dict[str, str]:
    reject_symlink_component(copied_log, "--copied-log")
    status = protected_paths.protected_path_status(
        copied_log,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected:
        raise SystemExit(f"--copied-log must not read from protected server root {SERVER_ROOT}: {status.resolved}")
    if not any(
        copied_log.expanduser().is_absolute()
        and protected_paths.is_under_path(copied_log.expanduser(), root)
        and protected_paths.is_under_path(status.resolved, root.resolve())
        for root in APPROVED_OFFLINE_WORKSPACE_ROOTS
    ):
        raise SystemExit("--copied-log must be under /servidor/ark/workspace-offline")
    if not status.resolved.is_file():
        raise SystemExit(f"--copied-log does not exist: {status.resolved}")
    if len(status.resolved.parts) < 3:
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    expected_parent = status.resolved.parts[-3]
    run_id = status.resolved.parts[-2]
    file_name = status.resolved.parts[-1]
    if expected_parent != EXPECTED_COPIED_LOG_PARENT or file_name != "Obelisk.log":
        raise SystemExit("--copied-log must be live-validation-logs/<run-id>/Obelisk.log")
    if RUN_ID_RE.fullmatch(run_id) is None:
        raise SystemExit(f"--copied-log run id is invalid: {run_id}")
    return {
        "run_id": run_id,
        "copied_log_path": str(status.resolved),
        "copied_log_sha256": hashlib.sha256(status.resolved.read_bytes()).hexdigest(),
    }


def write_template(path: Path, copied_log: Path | None = None) -> None:
    reject_symlink_component(path, "--emit-template")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "--emit-template",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    fields = build_template_fields()
    if copied_log is not None:
        fields.update(template_fields_from_copied_log(copied_log))
    lines = [
        "# Secret-free operational manifest for a future approved player-principal lifecycle window.",
        "# Replace timestamps, run_id, copied_log_path, copied_log_sha256, and target with the reviewed window values.",
    ]
    lines.extend(f"{key}={value}" for key, value in fields.items())
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(
    fields: dict[str, str],
    validation: Validation,
    manifest_path: Path,
    *,
    post_window_replay: bool = False,
) -> dict[str, Any]:
    accepted = not validation.blockers
    manifest_status = protected_paths.protected_path_status(
        manifest_path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved_manifest_path = str(manifest_status.resolved)

    def resolved_field_path(key: str) -> str | None:
        value = fields.get(key)
        if not value:
            return None
        path = manifest_relative_path(value, manifest_path)
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        return str(status.resolved)

    try:
        manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    except OSError:
        manifest_sha256 = None
    copied_log_path = fields.get("copied_log_path")
    resolved_copied_log_path = None
    if copied_log_path:
        try:
            resolved_copied_log_path = str(manifest_relative_path(copied_log_path, manifest_path).expanduser().resolve())
        except OSError:
            resolved_copied_log_path = str(manifest_relative_path(copied_log_path, manifest_path).expanduser())
    return {
        "schema": REPORT_SCHEMA,
        "ready": accepted,
        "operational_window_manifest_ready": accepted,
        "post_window_replay": post_window_replay,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": [] if accepted else ["window_manifest_not_accepted"],
        "next_blocker": NEXT_BLOCKER_AFTER_WINDOW_MANIFEST if accepted else "window_manifest_not_accepted",
        "run_id": fields.get("run_id"),
        "obelisk_commit": fields.get("obelisk_commit"),
        "approval": fields.get("approval"),
        "approved_window": {
            "start_utc": fields.get("approved_window_start_utc"),
            "end_utc": fields.get("approved_window_end_utc"),
        },
        "actual_capture": {
            "start_utc": fields.get("actual_capture_start_utc"),
            "end_utc": fields.get("actual_capture_end_utc"),
        },
        "rollback_window": {
            "start_utc": fields.get("rollback_start_utc"),
            "end_utc": fields.get("rollback_end_utc"),
        },
        "target": {
            "instance": validation.target.instance,
            "map": validation.target.map_name,
        },
        "manifest": {
            "path": resolved_manifest_path,
            "sha256": manifest_sha256,
        },
        "copied_log": {
            "path": resolved_copied_log_path,
            "sha256": fields.get("copied_log_sha256"),
            "path_status": validation.copied_log_status,
        },
        "request_pack": {
            "path": resolved_field_path("request_pack_path"),
            "sha256": fields.get("request_pack_sha256"),
        },
        "observer_env": {
            "path": resolved_field_path("observer_env_path"),
            "sha256": fields.get("observer_env_sha256"),
        },
        "preflight": {
            "pre": {
                "path": resolved_field_path("preflight_pre_path"),
                "sha256": fields.get("preflight_pre_sha256"),
            },
            "post": {
                "path": resolved_field_path("preflight_post_path"),
                "sha256": fields.get("preflight_post_sha256"),
            },
        },
        "posture": {
            "pre_posture": fields.get("pre_posture"),
            "post_posture": fields.get("post_posture"),
            "pre_check": fields.get("pre_check"),
            "post_check": fields.get("post_check"),
            "plugins_disabled": parse_bool(fields.get("plugins_disabled")),
            "scanner_disabled": parse_bool(fields.get("scanner_disabled")),
            "dispatch_limit": fields.get("dispatch_limit"),
            "wrapper_profile": fields.get("wrapper_profile"),
            "observer_exclusivity": fields.get("observer_exclusivity"),
            "sibling_marker_entries": fields.get("sibling_marker_entries"),
            "sibling_observer_env": fields.get("sibling_observer_env"),
            "debug_escape_markers": fields.get("debug_escape_markers"),
            "callback_escape_markers": fields.get("callback_escape_markers"),
            "native_exec_disabled": parse_bool(fields.get("native_exec_disabled")),
            "ptrace_disabled": parse_bool(fields.get("ptrace_disabled")),
            "single_module_summary": fields.get("single_module_summary"),
        },
        "rollback": {
            "completed": parse_bool(fields.get("rollback_completed")),
            "observer_env_survived": parse_bool(fields.get("observer_env_survived")),
            "observer_marker_survived": parse_bool(fields.get("observer_marker_survived")),
            "delta": fields.get("rollback_delta"),
        },
        "user_policy": validation.user_policy,
        "notice_sent": fields.get("notice_sent"),
        "log_budget": fields.get("log_budget"),
        "claims": {
            "delivery_claim": fields.get("delivery_claim"),
            "principal_claim": fields.get("principal_claim"),
        },
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": [
            "window manifest acceptance is operational posture only",
            "does not promote player identity, lookup, permissions, commands, ResourceHandle, mutation, return override, plugin delivery, public SDK, or runtime readiness",
            "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
        ],
    }


def main() -> int:
    args = parse_args()
    if args.emit_template is not None:
        write_template(args.emit_template, args.copied_log)
        return 0
    if args.copied_log is not None:
        raise SystemExit("--copied-log is only valid with --emit-template")
    if args.manifest is None:
        raise SystemExit("manifest is required unless --emit-template is used")
    fields = load_manifest(args.manifest)
    validation = validate_manifest(fields, args.manifest, post_window_replay=args.post_window_replay)
    report = build_report(fields, validation, args.manifest, post_window_replay=args.post_window_replay)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
