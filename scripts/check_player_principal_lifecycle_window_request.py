#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle window request pack.

This checker is pre-window only. It validates a secret-free request pack before an
operator decides whether to approve a runtime evidence window. Acceptance does not
authorize server operations, marker/env changes, runtime capture, Discord, publication,
public identity, permissions/admin, commands, or SDK readiness.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from player_principal_commit_validation import is_reviewed_obelisk_commit
from snapshot_evidence_pack import first_symlink_component, reject_symlink_component
from prepare_player_principal_lifecycle_window_request import (
    APPROVAL_TEXT,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    NON_CLAIMS,
    REQUIRED_ENV,
    RUN_ID_RE,
    SCHEMA,
    UTC_RE,
    WINDOW_MARKERS,
    env_lines,
    run_id_for_window_start,
)


REPORT_SCHEMA = "obelisk.player-principal-lifecycle-window-request-check.v1"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
EVIDENCE_ROOT = Path("/servidor/ark/workspace-offline/live-validation-logs")
SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "status",
        "approval_required",
        "target",
        "run_id",
        "ark_binary_sha256",
        "server_binary_path",
        "obelisk_commit",
        "approved_window",
        "restart_expectation",
        "final_posture",
        "user_policy",
        "notice_path",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "observer_env_file",
        "marker_set",
        "forbidden_markers",
        "operator_live_ops_brief",
        "rollback",
        "non_claims",
    )
)
EXPECTED_TARGET_KEYS = frozenset(("instance", "map"))
EXPECTED_WINDOW_KEYS = frozenset(("start_utc", "end_utc"))
EXPECTED_ROLLBACK_KEYS = frozenset(("owner", "delta"))
EXPECTED_OPERATOR_BRIEF_KEYS = frozenset(
    (
        "target",
        "feature_gates",
        "server_binary",
        "marker_changes",
        "env_snapshot",
        "start_restart_stop_window",
        "notice_path",
        "user_policy",
        "evidence_capture",
        "rollback",
        "post_run_stable_posture",
        "approval_boundary",
        "non_authorization",
    )
)
EXPECTED_SERVER_BINARY_KEYS = frozenset(("path", "sha256"))
EXPECTED_FEATURE_GATE_KEYS = frozenset(
    (
        "observer",
        "plugins_disabled",
        "process_event_hook",
        "dispatch_limit",
        "log_limit",
        "scanner_debug_and_callback_escape_gates",
    )
)
EXPECTED_MARKER_CHANGE_KEYS = frozenset(("set", "forbidden"))
EXPECTED_WINDOW_BRIEF_KEYS = frozenset(("start_utc", "end_utc", "expectation", "final_posture"))
EXPECTED_EVIDENCE_CAPTURE_KEYS = frozenset(
    (
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "observer_env_file",
        "single_module_summary",
        "copied_log_only",
    )
)
EXPECTED_POST_RUN_KEYS = frozenset(
    (
        "required",
        "expected",
        "stable_markers_preserved",
        "observer_markers_removed",
    )
)
ALLOWED_RESTART_EXPECTATIONS = frozenset(("none", "start", "restart", "stop-after-window"))
ALLOWED_FINAL_POSTURES = frozenset(("stable", "stopped"))
ALLOWED_USER_POLICIES = frozenset(("no_regular_users", "operator_approved_beta_users"))
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
POSITIVE_CAPABILITY_RE = re.compile(
    r"(?:public[_ -]?(?:sdk|player[_ -]?identity)|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_ACTION_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|doesn't|don't|cannot|can't|must\s+not|never|no|not)\s+"
    r"(?:claim|promote|authorize|enable|allow|support|deliver|provide|expose|log|make|mark|"
    r"report|treat|set|capture|collect|record)\b",
    re.IGNORECASE,
)
NEGATION_SCOPE_SPLIT_RE = re.compile(r"[,.;\n]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)
NEGATED_BOUNDARY_PREFIX_RE = re.compile(
    r"\b(?:without|forbidden|reject(?:ed|s)?|fail[-_ ]closed(?:\s+on)?)\s*:?\s*$",
    re.IGNORECASE,
)
NEGATED_CAPABILITY_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported)\b",
    re.IGNORECASE,
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    payload: dict[str, Any] | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_json", type=Path, help="window-request.json from the request pack.")
    parser.add_argument("--env-file", type=Path, required=True, help="observer-window.env from the same request pack.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def parse_utc(value: str) -> datetime | None:
    if not UTC_RE.fullmatch(value):
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "request_json")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "request_json",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"request_json is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("request_json must be a JSON object")
    return payload


def read_env(path: Path, blockers: list[dict[str, Any]]) -> list[str]:
    reject_symlink_component(path, "env_file")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "env_file",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    lines: list[str] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(resolved.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            add(blockers, "env_line_not_key_value", f"env_file:{line_number}")
            continue
        key, value = line.split("=", 1)
        if key in seen:
            add(blockers, "env_key_duplicate", key)
        seen.add(key)
        if not re.fullmatch(r"[A-Z0-9_]+", key):
            add(blockers, "env_key_unsafe", key)
        if "\n" in value or "\r" in value:
            add(blockers, "env_value_multiline", key)
        lines.append(f"{key}={value}")
    return lines


def require_keys(
    obj: Any,
    *,
    required: frozenset[str],
    label: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        add(blockers, f"{label}_not_object", label)
        return None
    missing = required - set(obj)
    unexpected = set(obj) - required
    if missing:
        add(blockers, f"{label}_missing_required", label, missing=sorted(missing))
    if unexpected:
        add(blockers, f"{label}_unexpected_keys", label, unexpected=sorted(unexpected))
    return obj


def string_at(payload: dict[str, Any], key: str, blockers: list[dict[str, Any]]) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str):
        add(blockers, f"{key}_not_string", key)
        return None
    return value


def contains_unnegated_positive_capability_claim(value: str) -> bool:
    for match in POSITIVE_CAPABILITY_RE.finditer(value):
        if not is_negated_for_match(value, match.start()) and not is_negated_after_match(value, match.end()):
            return True
    return False


def preceding_negation_scope(value: str, start: int) -> str:
    return NEGATION_SCOPE_SPLIT_RE.split(value[:start])[-1]


def is_negated_for_match(value: str, start: int) -> bool:
    prefix = preceding_negation_scope(value, start)
    return bool(NEGATED_CAPABILITY_ACTION_RE.search(prefix) or NEGATED_BOUNDARY_PREFIX_RE.search(prefix))


def is_negated_after_match(value: str, end: int) -> bool:
    return bool(NEGATED_CAPABILITY_SUFFIX_RE.match(value[end:]))


def find_forbidden_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if trail in ("$.non_claims", "$.operator_live_ops_brief.marker_changes.forbidden"):
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            found = find_forbidden_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif isinstance(value, str) and contains_unnegated_positive_capability_claim(value):
        return value, trail
    return None


def validate_secret_free(value: Any, blockers: list[dict[str, Any]], trail: str = "$") -> None:
    if trail in ("$.forbidden_markers", "$.non_claims", "$.operator_live_ops_brief.marker_changes.forbidden"):
        return
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if FORBIDDEN_VALUE_RE.search(str(key)) and child not in (False, None, [], {}):
                add(blockers, "forbidden_private_or_ue_key", child_trail, value=str(key))
            validate_secret_free(child, blockers, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_secret_free(child, blockers, f"{trail}[{index}]")
    elif isinstance(value, str):
        for match in FORBIDDEN_VALUE_RE.finditer(value):
            if not is_negated_for_match(value, match.start()):
                add(blockers, "forbidden_private_or_ue_value", trail, value=value)
                break


def validate_paths(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    run_id = payload.get("run_id")
    if not isinstance(run_id, str):
        return
    expected_dir = EVIDENCE_ROOT / run_id
    if os.environ.get("OBELISK_ALLOW_TEST_WORKSPACE_PREFIXES") == "1":
        for key in ("copied_evidence_dir", "copied_log_path", "window_manifest_path"):
            value = payload.get(key)
            if not isinstance(value, str):
                continue
            path = Path(value).expanduser()
            status = protected_paths.protected_path_status(
                path,
                protected_root=SERVER_ROOT,
                approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
            )
            try:
                relative = status.resolved.relative_to(APPROVED_OFFLINE_WORKSPACE_ROOTS[0].resolve())
            except ValueError:
                continue
            if relative.parts and relative.parts[0].startswith("obelisk-test-player-principal-"):
                expected_dir = APPROVED_OFFLINE_WORKSPACE_ROOTS[0] / relative.parts[0] / "live-validation-logs" / run_id
                break
    expected_paths = {
        "copied_evidence_dir": expected_dir,
        "copied_log_path": expected_dir / "Obelisk.log",
        "window_manifest_path": expected_dir / "window-manifest.env",
    }
    for key, expected in expected_paths.items():
        value = payload.get(key)
        if not isinstance(value, str):
            add(blockers, f"{key}_not_string", key)
            continue
        path = Path(value).expanduser()
        symlink = first_symlink_component(path)
        if symlink is not None:
            add(blockers, f"{key}_symlink_component", key, symlink=str(symlink))
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        if status.protected:
            add(blockers, f"{key}_under_protected_server_root", key, resolved=str(status.resolved))
        if not status.approved_offline_workspace:
            add(blockers, f"{key}_not_approved_offline_workspace", key, resolved=str(status.resolved))
        if status.resolved != expected.resolve():
            add(blockers, f"{key}_not_exact_expected_path", key, expected=str(expected), resolved=str(status.resolved))


def args_for_env(payload: dict[str, Any]) -> argparse.Namespace:
    window = payload["approved_window"]
    return argparse.Namespace(
        instance=payload["target"]["instance"],
        map_name=payload["target"]["map"],
        run_id=payload["run_id"],
        obelisk_commit=payload["obelisk_commit"],
        approved_window_start_utc=window["start_utc"],
        approved_window_end_utc=window["end_utc"],
        binary_sha256=payload["ark_binary_sha256"],
        server_binary_path=payload["server_binary_path"],
        restart_expectation=payload["restart_expectation"],
        final_posture=payload["final_posture"],
        user_policy=payload["user_policy"],
        notice_path=payload["notice_path"],
        rollback_owner=payload["rollback"]["owner"],
        output_dir=Path("."),
        json=True,
    )


def expected_operator_live_ops_brief(payload: dict[str, Any], env: list[str]) -> dict[str, Any] | None:
    try:
        window = payload["approved_window"]
        return {
            "target": payload["target"],
            "feature_gates": {
                "observer": "player_principal_lifecycle_only",
                "plugins_disabled": True,
                "process_event_hook": True,
                "dispatch_limit": 0,
                "log_limit": 10,
                "scanner_debug_and_callback_escape_gates": "forbidden",
            },
            "server_binary": {
                "path": payload["server_binary_path"],
                "sha256": payload["ark_binary_sha256"],
            },
            "marker_changes": {
                "set": payload["marker_set"],
                "forbidden": payload["forbidden_markers"],
            },
            "env_snapshot": env,
            "start_restart_stop_window": {
                "start_utc": window["start_utc"],
                "end_utc": window["end_utc"],
                "expectation": payload["restart_expectation"],
                "final_posture": payload["final_posture"],
            },
            "notice_path": payload["notice_path"],
            "user_policy": payload["user_policy"],
            "evidence_capture": {
                "copied_evidence_dir": payload["copied_evidence_dir"],
                "copied_log_path": payload["copied_log_path"],
                "window_manifest_path": payload["window_manifest_path"],
                "observer_env_file": payload["observer_env_file"],
                "single_module_summary": "player_principal_lifecycle",
                "copied_log_only": True,
            },
            "rollback": payload["rollback"],
            "post_run_stable_posture": {
                "required": True,
                "expected": payload["final_posture"],
                "stable_markers_preserved": ["enable-process-event-hook", "disable-plugins"],
                "observer_markers_removed": True,
            },
            "approval_boundary": APPROVAL_TEXT,
            "non_authorization": "brief only; request-pack acceptance does not authorize operations",
        }
    except (KeyError, TypeError):
        return None


def validate_operator_live_ops_brief(payload: dict[str, Any], env: list[str], blockers: list[dict[str, Any]]) -> None:
    brief = require_keys(
        payload.get("operator_live_ops_brief"),
        required=EXPECTED_OPERATOR_BRIEF_KEYS,
        label="operator_live_ops_brief",
        blockers=blockers,
    )
    if brief is None:
        return
    require_keys(brief.get("feature_gates"), required=EXPECTED_FEATURE_GATE_KEYS, label="operator_live_ops_brief_feature_gates", blockers=blockers)
    require_keys(brief.get("server_binary"), required=EXPECTED_SERVER_BINARY_KEYS, label="operator_live_ops_brief_server_binary", blockers=blockers)
    require_keys(brief.get("marker_changes"), required=EXPECTED_MARKER_CHANGE_KEYS, label="operator_live_ops_brief_marker_changes", blockers=blockers)
    require_keys(brief.get("start_restart_stop_window"), required=EXPECTED_WINDOW_BRIEF_KEYS, label="operator_live_ops_brief_window", blockers=blockers)
    require_keys(brief.get("evidence_capture"), required=EXPECTED_EVIDENCE_CAPTURE_KEYS, label="operator_live_ops_brief_evidence_capture", blockers=blockers)
    require_keys(brief.get("post_run_stable_posture"), required=EXPECTED_POST_RUN_KEYS, label="operator_live_ops_brief_post_run_stable_posture", blockers=blockers)
    expected = expected_operator_live_ops_brief(payload, env)
    if expected is not None and brief != expected:
        add(blockers, "operator_live_ops_brief_mismatch", "operator_live_ops_brief", expected=expected, actual=brief)


def validate_payload(payload: dict[str, Any], env: list[str]) -> Validation:
    blockers: list[dict[str, Any]] = []
    require_keys(payload, required=EXPECTED_TOP_LEVEL_KEYS, label="request", blockers=blockers)
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "schema", expected=SCHEMA)
    if payload.get("status") != "candidate_only_request_pack":
        add(blockers, "status_not_candidate_only_request_pack", "status")
    if payload.get("approval_required") != APPROVAL_TEXT:
        add(blockers, "approval_required_mismatch", "approval_required", expected=APPROVAL_TEXT)
    if payload.get("marker_set") != WINDOW_MARKERS:
        add(blockers, "marker_set_mismatch", "marker_set")
    if payload.get("forbidden_markers") != FORBIDDEN_MARKERS:
        add(blockers, "forbidden_markers_mismatch", "forbidden_markers")
    if payload.get("non_claims") != NON_CLAIMS:
        add(blockers, "non_claims_mismatch", "non_claims")
    if payload.get("observer_env_file") != "observer-window.env":
        add(blockers, "observer_env_file_mismatch", "observer_env_file")
    validate_operator_live_ops_brief(payload, env, blockers)
    target = require_keys(payload.get("target"), required=EXPECTED_TARGET_KEYS, label="target", blockers=blockers)
    if target:
        for key in ("instance", "map"):
            value = target.get(key)
            if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
                add(blockers, f"target_{key}_invalid", f"target.{key}")
    window = require_keys(payload.get("approved_window"), required=EXPECTED_WINDOW_KEYS, label="approved_window", blockers=blockers)
    if window:
        start = window.get("start_utc")
        end = window.get("end_utc")
        start_dt = parse_utc(start) if isinstance(start, str) else None
        end_dt = parse_utc(end) if isinstance(end, str) else None
        if start_dt is None:
            add(blockers, "approved_window_start_utc_invalid", "approved_window.start_utc")
        if end_dt is None:
            add(blockers, "approved_window_end_utc_invalid", "approved_window.end_utc")
        if start_dt is not None and end_dt is not None and not start_dt < end_dt:
            add(blockers, "approved_window_order_invalid", "approved_window")
        if end_dt is not None and end_dt <= datetime.now(timezone.utc):
            add(blockers, "approved_window_expired", "approved_window.end_utc", value=end)
    rollback = require_keys(payload.get("rollback"), required=EXPECTED_ROLLBACK_KEYS, label="rollback", blockers=blockers)
    if rollback:
        if not isinstance(rollback.get("owner"), str) or not re.fullmatch(r"[A-Za-z0-9_.@ -]+", rollback["owner"]):
            add(blockers, "rollback_owner_invalid", "rollback.owner")
        expected_delta = "remove observer env and markers, preserve stable enable-process-event-hook and disable-plugins"
        if rollback.get("delta") != expected_delta:
            add(blockers, "rollback_delta_mismatch", "rollback.delta", expected=expected_delta)
    run_id = string_at(payload, "run_id", blockers)
    if run_id is not None and not RUN_ID_RE.fullmatch(run_id):
        add(blockers, "run_id_invalid", "run_id")
    if run_id is not None and RUN_ID_RE.fullmatch(run_id) and window:
        start = window.get("start_utc")
        start_dt = parse_utc(start) if isinstance(start, str) else None
        if start_dt is not None:
            expected_run_id = run_id_for_window_start(start_dt)
            if run_id != expected_run_id:
                add(
                    blockers,
                    "run_id_window_start_mismatch",
                    "run_id",
                    expected=expected_run_id,
                    actual=run_id,
                    approved_window_start_utc=start,
                )
    sha = string_at(payload, "ark_binary_sha256", blockers)
    if sha is not None and (not SHA256_RE.fullmatch(sha) or sha != EXPECTED_BINARY_SHA256):
        add(blockers, "ark_binary_sha256_not_reviewed", "ark_binary_sha256", expected=EXPECTED_BINARY_SHA256)
    server_binary_path = string_at(payload, "server_binary_path", blockers)
    if server_binary_path is not None and server_binary_path != EXPECTED_SERVER_BINARY_PATH:
        add(
            blockers,
            "server_binary_path_not_reviewed",
            "server_binary_path",
            expected=EXPECTED_SERVER_BINARY_PATH,
        )
    commit = string_at(payload, "obelisk_commit", blockers)
    if commit is not None and not is_reviewed_obelisk_commit(commit):
        add(blockers, "obelisk_commit_invalid", "obelisk_commit")
    if payload.get("restart_expectation") not in ALLOWED_RESTART_EXPECTATIONS:
        add(blockers, "restart_expectation_invalid", "restart_expectation")
    if payload.get("final_posture") not in ALLOWED_FINAL_POSTURES:
        add(blockers, "final_posture_invalid", "final_posture")
    user_policy = payload.get("user_policy")
    if user_policy not in ALLOWED_USER_POLICIES:
        add(blockers, "user_policy_invalid", "user_policy")
    notice_path = payload.get("notice_path")
    if user_policy == "operator_approved_beta_users" and notice_path == "not_applicable":
        add(blockers, "beta_user_policy_requires_notice_path", "notice_path")
    if not isinstance(notice_path, str) or not re.fullmatch(r"[A-Za-z0-9_.:/ -]+", notice_path):
        add(blockers, "notice_path_invalid", "notice_path")
    validate_paths(payload, blockers)
    validate_secret_free(payload, blockers)
    forbidden_claim = find_forbidden_claim(payload)
    if forbidden_claim is not None:
        value, trail = forbidden_claim
        add(blockers, "forbidden_public_capability_or_readiness_claim", trail, value=value)
    try:
        expected_env = env_lines(args_for_env(payload))
        if env != expected_env:
            add(blockers, "observer_env_snapshot_mismatch", "env_file", expected=expected_env, actual=env)
    except (KeyError, TypeError):
        pass
    for key, expected in REQUIRED_ENV.items():
        if f"{key}={expected}" not in env:
            add(blockers, "observer_env_required_key_missing_or_mismatch", key, expected=expected)
    if "OBELISK_ENABLE_REFLECTION_SCANNER=1" in env or "OBELISK_ENABLE_NATIVE_EXEC_PROBES=1" in env:
        add(blockers, "observer_env_forbidden_debug_gate_present", "env_file")
    return Validation(blockers=blockers, payload=payload)


def build_report(validation: Validation) -> dict[str, Any]:
    accepted = not validation.blockers
    payload = validation.payload or {}
    return {
        "schema": REPORT_SCHEMA,
        "ready": accepted,
        "request_pack_ready": accepted,
        "planning_only": True,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "publication_authorized": False,
        "promotion_ready": False,
        "public_abi_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_ready": False,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "next_blocker": "operator_current_turn_runtime_window_approval_required" if accepted else "request_pack_not_accepted",
        "target": payload.get("target"),
        "run_id": payload.get("run_id"),
        "approval_required": APPROVAL_TEXT,
        "non_claims": [
            "request-pack acceptance is pre-window planning only",
            "does not authorize server operations, marker/env changes, starts, restarts, stops, Discord, GitHub publication, runtime capture, public SDK readiness, or v1 completion",
            "does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
        ],
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    payload = read_json(args.request_json)
    env = read_env(args.env_file, blockers)
    validation = validate_payload(payload, env)
    validation.blockers[:0] = blockers
    report = build_report(validation)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"player_principal_lifecycle_window_request_ready={str(report['ready']).lower()}")
        if not report["ready"]:
            print("blockers=" + ",".join(report["blockers"]), file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
