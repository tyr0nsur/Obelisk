#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle window request pack.

This checker is pre-window strict by default. It validates a secret-free request pack before an
operator decides whether to approve a runtime evidence window. Post-window replay may tolerate
only a completed window whose sole stale condition is approved_window_expired. Acceptance does not
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
    APPROVAL_RECEIPT_SCHEMA,
    APPROVAL_TEXT,
    EXPECTED_BINARY_SHA256,
    EXPECTED_SERVER_BINARY_PATH,
    FORBIDDEN_MARKERS,
    MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
    MAX_APPROVED_WINDOW_SECONDS,
    MAX_REQUEST_PREPARATION_LEAD_SECONDS,
    NON_CLAIMS,
    REQUIRED_ENV,
    RUN_ID_RE,
    SCHEMA,
    UTC_RE,
    WINDOW_MARKERS,
    bound_artifact,
    env_lines,
    markdown_request,
    post_window_replay_contract,
    post_run_verification_commands,
    request_pack_digest,
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
        "prepared_at_utc",
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
        "post_window_replay_contract",
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
        "operator_approval_receipt_path",
        "operator_approval_receipt_required",
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
        "verification_commands",
    )
)
EXPECTED_REPLAY_CONTRACT_KEYS = frozenset(("required", "offline_only", "sidecars", "checks", "non_authorization"))
EXPECTED_REPLAY_CONTRACT_SIDECAR_KEYS = frozenset(
    (
        "request_pack_path",
        "observer_env_path",
        "operator_approval_receipt_path",
        "preflight_pre_path",
        "preflight_post_path",
        "window_manifest_path",
    )
)
EXPECTED_REPLAY_CONTRACT_CHECK_KEYS = frozenset(("window_manifest_replay",))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "status",
        "receipt_completed",
        "operator_current_turn_approval_recorded",
        "approval_scope",
        "bound_request_pack",
        "bound_artifacts",
        "request_pack_digest",
        "operator_completion",
        "non_authorization_flags",
        "non_claims",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCOPE_KEYS = frozenset(
    (
        "scope_type",
        "standing_approval",
        "reusable",
        "future_windows_authorized",
        "scope_expansion_authorized",
        "unbound_artifacts_authorized",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS = frozenset(
    (
        "run_id",
        "prepared_at_utc",
        "target",
        "approved_window",
        "obelisk_commit",
        "ark_binary_sha256",
        "server_binary_path",
        "restart_expectation",
        "final_posture",
        "user_policy",
        "notice_path",
        "copied_evidence_dir",
        "copied_log_path",
        "window_manifest_path",
        "rollback",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_ARTIFACTS_KEYS = frozenset(
    ("window_request_json", "observer_window_env", "operator_approval_request_md")
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_ARTIFACT_KEYS = frozenset(("path", "sha256", "size_bytes"))
EXPECTED_OPERATOR_APPROVAL_RECEIPT_COMPLETION_KEYS = frozenset(
    ("approval_recorded_at_utc", "approved_by_role", "approval_source", "attestation")
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS = frozenset(
    (
        "request_pack_acceptance_authorizes_runtime",
        "generated_template_authorizes_runtime",
        "server_operations_authorized_by_template",
        "runtime_work_authorized_by_template",
        "discord_authorized",
        "github_publication_authorized",
        "publication_authorized",
        "promotion_ready",
        "public_abi_ready",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_ready",
        "secrets_included",
        "player_private_data_included",
    )
)
EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS = [
    "generated receipt template only; does not record operator approval",
    "completed receipt binds one current-turn request pack only",
    "receipt does not authorize future windows, standing approval, Discord, GitHub publication, public SDK readiness, runtime readiness, or v1 completion",
    "receipt does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
]
ALLOWED_RESTART_EXPECTATIONS = frozenset(("none", "start", "restart"))
ALLOWED_FINAL_POSTURES = frozenset(("stable",))
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
    r"(?:stable|complete|full|production)[_ -]?(?:v1[_ -]?)?(?:sdk[_ -]?)?claim[_ -]?(?:allowed|ready|enabled|supported)|"
    r"(?:stable|complete|full|production)[_ -]?sdk[_ -]?(?:ready|allowed|claim)|"
    r"stable[_ -]?release[_ -]?contract[_ -]?claim[_ -]?allowed|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|runtime[_ -]?work|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|authorized|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)
OPERATIONAL_AUTHORIZATION_CLAIM_RE = re.compile(
    r"(?:(?:server|runtime)[_ -]?(?:operations?|work|capture|observation)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|authorized|approved)|"
    r"(?:server[_ -]?)?(?:starts?|stops?|restarts?)[_ -]?(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:marker|env|environment|state)[_ -]?(?:changes?|edits?|ops|operations?)[_ -]?"
    r"(?:allowed|authorized|approved|ready|enabled)|"
    r"(?:discord|github|publication|publishing|release|tag)[_ -]?"
    r"(?:allowed|authorized|approved|ready|enabled|published))",
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
    parser.add_argument(
        "--operator-request",
        type=Path,
        help="operator-approval-request.md from the same request pack; defaults to the sibling file.",
    )
    parser.add_argument(
        "--operator-approval-receipt",
        type=Path,
        help="Completed operator-approval-receipt.json from the same request pack; required for post-window replay.",
    )
    parser.add_argument(
        "--post-window-replay",
        action="store_true",
        help="Replay completed evidence after the window; tolerates only approved_window_expired.",
    )
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


def read_text_sidecar(path: Path, label: str, blockers: list[dict[str, Any]]) -> str | None:
    try:
        reject_symlink_component(path, label)
        resolved = protected_paths.reject_protected_input_path(
            path,
            label,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        return resolved.read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        add(blockers, f"{label}_unreadable", label, path=str(path), error=str(exc))
        return None


def validate_request_pack_sidecar_paths(
    *,
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    expected_names = {
        "request_json": "window-request.json",
        "env_file": "observer-window.env",
        "operator_request": "operator-approval-request.md",
    }
    paths = {
        "request_json": request_json_path,
        "env_file": env_file_path,
        "operator_request": operator_request_path,
    }
    resolved: dict[str, Path] = {}
    for label, path in paths.items():
        if path.name != expected_names[label]:
            add(
                blockers,
                f"{label}_filename_mismatch",
                label,
                expected=expected_names[label],
                actual=path.name,
            )
        try:
            resolved[label] = path.expanduser().resolve(strict=True)
        except OSError as exc:
            add(blockers, f"{label}_path_unresolved", label, path=str(path), error=str(exc))
    request_parent = resolved.get("request_json")
    if request_parent is None:
        return
    request_dir = request_parent.parent
    for label in ("env_file", "operator_request"):
        sidecar = resolved.get(label)
        if sidecar is not None and sidecar.parent != request_dir:
            add(
                blockers,
                f"{label}_not_sibling_of_request_json",
                label,
                expected_dir=str(request_dir),
                actual_dir=str(sidecar.parent),
            )


def validate_operator_approval_receipt_path(
    *,
    request_json_path: Path,
    receipt_path: Path,
    blockers: list[dict[str, Any]],
) -> None:
    if receipt_path.name == "operator-approval-receipt.template.json":
        add(
            blockers,
            "operator_approval_receipt_template_path_not_completed_receipt",
            "operator_approval_receipt",
            expected="operator-approval-receipt.json",
            actual=receipt_path.name,
        )
    if receipt_path.name != "operator-approval-receipt.json":
        add(
            blockers,
            "operator_approval_receipt_filename_mismatch",
            "operator_approval_receipt",
            expected="operator-approval-receipt.json",
            actual=receipt_path.name,
        )
    try:
        request_dir = request_json_path.expanduser().resolve(strict=True).parent
        resolved_receipt = receipt_path.expanduser().resolve(strict=True)
    except OSError as exc:
        add(blockers, "operator_approval_receipt_path_unresolved", "operator_approval_receipt", path=str(receipt_path), error=str(exc))
        return
    if resolved_receipt.parent != request_dir:
        add(
            blockers,
            "operator_approval_receipt_not_sibling_of_request_json",
            "operator_approval_receipt",
            expected_dir=str(request_dir),
            actual_dir=str(resolved_receipt.parent),
        )


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
    for pattern in (POSITIVE_CAPABILITY_RE, OPERATIONAL_AUTHORIZATION_CLAIM_RE):
        for match in pattern.finditer(value):
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
    if trail in (
        "$.forbidden_markers",
        "$.non_claims",
        "$.operator_live_ops_brief.marker_changes.forbidden",
        "$.post_window_replay_contract",
    ):
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


def validate_post_window_replay_contract(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    contract = require_keys(
        payload.get("post_window_replay_contract"),
        required=EXPECTED_REPLAY_CONTRACT_KEYS,
        label="post_window_replay_contract",
        blockers=blockers,
    )
    if contract is None:
        return
    require_keys(
        contract.get("sidecars"),
        required=EXPECTED_REPLAY_CONTRACT_SIDECAR_KEYS,
        label="post_window_replay_contract_sidecars",
        blockers=blockers,
    )
    require_keys(
        contract.get("checks"),
        required=EXPECTED_REPLAY_CONTRACT_CHECK_KEYS,
        label="post_window_replay_contract_checks",
        blockers=blockers,
    )
    try:
        expected = post_window_replay_contract(payload)
    except (KeyError, TypeError):
        return
    if contract != expected:
        add(blockers, "post_window_replay_contract_mismatch", "post_window_replay_contract", expected=expected, actual=contract)
    sidecars = contract.get("sidecars")
    if not isinstance(sidecars, dict):
        return
    for key, expected_name in (
        ("request_pack_path", "window-request.json"),
        ("observer_env_path", "observer-window.env"),
        ("operator_approval_receipt_path", "operator-approval-receipt.json"),
        ("preflight_pre_path", "preflight-pre.json"),
        ("preflight_post_path", "preflight-post.json"),
        ("window_manifest_path", "window-manifest.env"),
    ):
        value = sidecars.get(key)
        if not isinstance(value, str):
            add(blockers, f"post_window_replay_contract_{key}_not_string", f"post_window_replay_contract.sidecars.{key}")
            continue
        path = Path(value).expanduser()
        symlink = first_symlink_component(path)
        if symlink is not None:
            add(blockers, f"post_window_replay_contract_{key}_symlink_component", f"post_window_replay_contract.sidecars.{key}", symlink=str(symlink))
        status = protected_paths.protected_path_status(
            path,
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        if status.protected:
            add(blockers, f"post_window_replay_contract_{key}_under_protected_server_root", f"post_window_replay_contract.sidecars.{key}", resolved=str(status.resolved))
        if not status.approved_offline_workspace:
            add(blockers, f"post_window_replay_contract_{key}_not_approved_offline_workspace", f"post_window_replay_contract.sidecars.{key}", resolved=str(status.resolved))
        if status.resolved.name != expected_name:
            add(blockers, f"post_window_replay_contract_{key}_filename_mismatch", f"post_window_replay_contract.sidecars.{key}", expected=expected_name, actual=status.resolved.name)


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
                "operator_approval_receipt_path": payload["post_window_replay_contract"]["sidecars"][
                    "operator_approval_receipt_path"
                ],
                "operator_approval_receipt_required": "completed_operator_receipt",
                "single_module_summary": "player_principal_lifecycle",
                "copied_log_only": True,
            },
            "rollback": payload["rollback"],
            "post_run_stable_posture": {
                "required": True,
                "expected": payload["final_posture"],
                "stable_markers_preserved": ["enable-process-event-hook", "disable-plugins"],
                "observer_markers_removed": True,
                "verification_commands": post_run_verification_commands(payload),
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
    evidence_capture = require_keys(brief.get("evidence_capture"), required=EXPECTED_EVIDENCE_CAPTURE_KEYS, label="operator_live_ops_brief_evidence_capture", blockers=blockers)
    require_keys(brief.get("post_run_stable_posture"), required=EXPECTED_POST_RUN_KEYS, label="operator_live_ops_brief_post_run_stable_posture", blockers=blockers)
    if isinstance(evidence_capture, dict):
        if evidence_capture.get("operator_approval_receipt_required") != "completed_operator_receipt":
            add(
                blockers,
                "operator_live_ops_brief_receipt_required_not_completed_receipt",
                "operator_live_ops_brief.evidence_capture.operator_approval_receipt_required",
                expected="completed_operator_receipt",
                actual=evidence_capture.get("operator_approval_receipt_required"),
            )
        receipt_path = evidence_capture.get("operator_approval_receipt_path")
        if isinstance(receipt_path, str) and receipt_path.endswith(".template.json"):
            add(
                blockers,
                "operator_live_ops_brief_receipt_path_points_to_template",
                "operator_live_ops_brief.evidence_capture.operator_approval_receipt_path",
                value=receipt_path,
            )
    if brief.get("non_authorization") != "brief only; request-pack acceptance does not authorize operations":
        add(
            blockers,
            "operator_live_ops_brief_non_authorization_mismatch",
            "operator_live_ops_brief.non_authorization",
            expected="brief only; request-pack acceptance does not authorize operations",
            actual=brief.get("non_authorization"),
        )
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
    validate_post_window_replay_contract(payload, blockers)
    validate_operator_live_ops_brief(payload, env, blockers)
    target = require_keys(payload.get("target"), required=EXPECTED_TARGET_KEYS, label="target", blockers=blockers)
    if target:
        for key in ("instance", "map"):
            value = target.get(key)
            if not isinstance(value, str) or not SAFE_TOKEN_RE.fullmatch(value):
                add(blockers, f"target_{key}_invalid", f"target.{key}")
    window = require_keys(payload.get("approved_window"), required=EXPECTED_WINDOW_KEYS, label="approved_window", blockers=blockers)
    prepared_at_dt: datetime | None = None
    prepared_at = payload.get("prepared_at_utc")
    if not isinstance(prepared_at, str):
        add(blockers, "prepared_at_utc_not_string", "prepared_at_utc")
    else:
        prepared_at_dt = parse_utc(prepared_at)
        if prepared_at_dt is None:
            add(blockers, "prepared_at_utc_invalid", "prepared_at_utc")
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
        if prepared_at_dt is not None and start_dt is not None and prepared_at_dt >= start_dt:
            add(blockers, "prepared_at_utc_not_before_approved_window", "prepared_at_utc")
        if (
            prepared_at_dt is not None
            and start_dt is not None
            and prepared_at_dt < start_dt
            and (start_dt - prepared_at_dt).total_seconds() > MAX_REQUEST_PREPARATION_LEAD_SECONDS
        ):
            add(
                blockers,
                "prepared_at_utc_too_far_before_approved_window",
                "prepared_at_utc",
                max_seconds=MAX_REQUEST_PREPARATION_LEAD_SECONDS,
            )
        now = datetime.now(timezone.utc)
        if start_dt is not None and start_dt <= now and (end_dt is None or end_dt > now):
            add(
                blockers,
                "approved_window_already_started",
                "approved_window.start_utc",
                value=start,
                stale_condition="already_started",
            )
        if (
            start_dt is not None
            and end_dt is not None
            and start_dt < end_dt
            and (end_dt - start_dt).total_seconds() > MAX_APPROVED_WINDOW_SECONDS
        ):
            add(
                blockers,
                "approved_window_duration_too_long",
                "approved_window",
                max_seconds=MAX_APPROVED_WINDOW_SECONDS,
            )
        if end_dt is not None and end_dt <= now:
            add(
                blockers,
                "approved_window_expired",
                "approved_window.end_utc",
                value=end,
                stale_condition="expired",
            )
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
    if payload.get("restart_expectation") == "stop-after-window" and payload.get("final_posture") != "stopped":
        add(blockers, "restart_expectation_final_posture_mismatch", "final_posture")
    if payload.get("restart_expectation") in {"none", "start", "restart"} and payload.get("final_posture") != "stable":
        add(blockers, "restart_expectation_final_posture_mismatch", "final_posture")
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


def validate_operator_request_markdown(
    payload: dict[str, Any],
    env: list[str],
    markdown: str | None,
    blockers: list[dict[str, Any]],
) -> bool:
    if markdown is None:
        return False
    try:
        expected = markdown_request(payload, env)
    except (KeyError, TypeError) as exc:
        add(blockers, "operator_request_markdown_projection_failed", "operator_request", error=str(exc))
        return False
    if markdown != expected:
        add(blockers, "operator_request_markdown_mismatch", "operator_request")
        return False
    return True


def expected_bound_request_pack(payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return {
            "run_id": payload["run_id"],
            "prepared_at_utc": payload["prepared_at_utc"],
            "target": payload["target"],
            "approved_window": payload["approved_window"],
            "obelisk_commit": payload["obelisk_commit"],
            "ark_binary_sha256": payload["ark_binary_sha256"],
            "server_binary_path": payload["server_binary_path"],
            "restart_expectation": payload["restart_expectation"],
            "final_posture": payload["final_posture"],
            "user_policy": payload["user_policy"],
            "notice_path": payload["notice_path"],
            "copied_evidence_dir": payload["copied_evidence_dir"],
            "copied_log_path": payload["copied_log_path"],
            "window_manifest_path": payload["window_manifest_path"],
            "rollback": payload["rollback"],
        }
    except (KeyError, TypeError):
        return None


def validate_operator_approval_receipt(
    *,
    payload: dict[str, Any],
    request_json_path: Path,
    env_file_path: Path,
    operator_request_path: Path,
    receipt_path: Path,
    blockers: list[dict[str, Any]],
) -> bool:
    initial_blocker_count = len(blockers)
    try:
        reject_symlink_component(receipt_path, "operator_approval_receipt")
        resolved = protected_paths.reject_protected_input_path(
            receipt_path,
            "operator_approval_receipt",
            protected_root=SERVER_ROOT,
            approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
        )
        receipt = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add(blockers, "operator_approval_receipt_json_invalid", "operator_approval_receipt", error=str(exc))
        return False
    except (OSError, ValueError) as exc:
        add(blockers, "operator_approval_receipt_unreadable", "operator_approval_receipt", path=str(receipt_path), error=str(exc))
        return False
    if not isinstance(receipt, dict):
        add(blockers, "operator_approval_receipt_not_object", "operator_approval_receipt")
        return False

    require_keys(
        receipt,
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_TOP_LEVEL_KEYS,
        label="operator_approval_receipt",
        blockers=blockers,
    )
    if receipt.get("schema") != APPROVAL_RECEIPT_SCHEMA:
        add(blockers, "operator_approval_receipt_schema_mismatch", "operator_approval_receipt")
    if receipt.get("status") == "generated_template":
        add(
            blockers,
            "operator_approval_receipt_generated_template_not_completed_receipt",
            "operator_approval_receipt",
        )
    if receipt.get("status") != "completed_operator_receipt":
        add(blockers, "operator_approval_receipt_status_not_completed", "operator_approval_receipt")
    if receipt.get("receipt_completed") is not True:
        add(blockers, "operator_approval_receipt_receipt_completed_not_true", "operator_approval_receipt")
    if receipt.get("operator_current_turn_approval_recorded") is not True:
        add(blockers, "operator_approval_receipt_current_turn_approval_not_recorded", "operator_approval_receipt")

    if receipt.get("non_claims") != EXPECTED_OPERATOR_APPROVAL_RECEIPT_NON_CLAIMS:
        add(blockers, "operator_approval_receipt_non_claims_mismatch", "operator_approval_receipt")

    scope = require_keys(
        receipt.get("approval_scope"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_SCOPE_KEYS,
        label="operator_approval_receipt_scope",
        blockers=blockers,
    ) or {}
    if scope.get("scope_type") != "exact_bound_player_principal_lifecycle_window_only":
        add(blockers, "operator_approval_receipt_scope_type_mismatch", "operator_approval_receipt")
    for key in (
        "standing_approval",
        "reusable",
        "future_windows_authorized",
        "scope_expansion_authorized",
        "unbound_artifacts_authorized",
    ):
        if scope.get(key) is not False:
            add(blockers, f"operator_approval_receipt_scope_{key}_not_false", "operator_approval_receipt")

    completion = require_keys(
        receipt.get("operator_completion"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_COMPLETION_KEYS,
        label="operator_approval_receipt_completion",
        blockers=blockers,
    ) or {}
    approval_recorded_at = completion.get("approval_recorded_at_utc")
    approval_recorded_dt = parse_utc(approval_recorded_at) if isinstance(approval_recorded_at, str) else None
    if approval_recorded_dt is None:
        add(blockers, "operator_approval_receipt_approved_at_utc_invalid", "operator_approval_receipt")
    request_prepared_dt = parse_utc(payload.get("prepared_at_utc")) if isinstance(payload.get("prepared_at_utc"), str) else None
    approved_window = payload.get("approved_window")
    window_start_dt = None
    if isinstance(approved_window, dict) and isinstance(approved_window.get("start_utc"), str):
        window_start_dt = parse_utc(approved_window["start_utc"])
    if approval_recorded_dt is not None and request_prepared_dt is not None and approval_recorded_dt <= request_prepared_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_before_request_prepared",
            "operator_approval_receipt",
            prepared_at_utc=payload.get("prepared_at_utc"),
            approval_recorded_at_utc=approval_recorded_at,
        )
    if approval_recorded_dt is not None and window_start_dt is not None and approval_recorded_dt >= window_start_dt:
        add(
            blockers,
            "operator_approval_receipt_approved_at_or_after_window_start",
            "operator_approval_receipt",
            approved_window_start_utc=approved_window.get("start_utc") if isinstance(approved_window, dict) else None,
            approval_recorded_at_utc=approval_recorded_at,
        )
    if (
        approval_recorded_dt is not None
        and window_start_dt is not None
        and approval_recorded_dt < window_start_dt
        and (window_start_dt - approval_recorded_dt).total_seconds() > MAX_OPERATOR_APPROVAL_LEAD_SECONDS
    ):
        add(
            blockers,
            "operator_approval_receipt_approved_too_far_before_window_start",
            "operator_approval_receipt",
            max_seconds=MAX_OPERATOR_APPROVAL_LEAD_SECONDS,
            approved_window_start_utc=approved_window.get("start_utc") if isinstance(approved_window, dict) else None,
            approval_recorded_at_utc=approval_recorded_at,
        )
    if not isinstance(completion.get("approved_by_role"), str) or not completion.get("approved_by_role", "").strip():
        add(blockers, "operator_approval_receipt_approved_by_role_invalid", "operator_approval_receipt")
    if completion.get("approval_source") != "current_turn_operator_message":
        add(blockers, "operator_approval_receipt_approval_source_mismatch", "operator_approval_receipt")
    if completion.get("attestation") != "APPROVE_EXACT_BOUND_PLAYER_PRINCIPAL_LIFECYCLE_WINDOW_ONLY":
        add(blockers, "operator_approval_receipt_attestation_mismatch", "operator_approval_receipt")
    forbidden_receipt_claim = find_forbidden_claim(receipt)
    if forbidden_receipt_claim is not None:
        value, trail = forbidden_receipt_claim
        add(
            blockers,
            "operator_approval_receipt_forbidden_public_capability_or_readiness_claim",
            "operator_approval_receipt",
            trail=trail,
            value=value,
        )

    bound_request = require_keys(
        receipt.get("bound_request_pack"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_REQUEST_KEYS,
        label="operator_approval_receipt_bound_request_pack",
        blockers=blockers,
    ) or {}
    if isinstance(bound_request.get("target"), dict):
        require_keys(
            bound_request["target"],
            required=EXPECTED_TARGET_KEYS,
            label="operator_approval_receipt_bound_request_pack_target",
            blockers=blockers,
        )
    if isinstance(bound_request.get("approved_window"), dict):
        require_keys(
            bound_request["approved_window"],
            required=EXPECTED_WINDOW_KEYS,
            label="operator_approval_receipt_bound_request_pack_window",
            blockers=blockers,
        )
    if isinstance(bound_request.get("rollback"), dict):
        require_keys(
            bound_request["rollback"],
            required=EXPECTED_ROLLBACK_KEYS,
            label="operator_approval_receipt_bound_request_pack_rollback",
            blockers=blockers,
        )
    expected_bound = expected_bound_request_pack(payload)
    if expected_bound is not None and bound_request != expected_bound:
        for key, expected_value in expected_bound.items():
            if bound_request.get(key) != expected_value:
                add(
                    blockers,
                    f"operator_approval_receipt_{key}_mismatch",
                    "operator_approval_receipt",
                    expected=expected_value,
                    actual=bound_request.get(key),
                )

    bound_artifacts = require_keys(
        receipt.get("bound_artifacts"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_BOUND_ARTIFACTS_KEYS,
        label="operator_approval_receipt_bound_artifacts",
        blockers=blockers,
    ) or {}
    try:
        expected_artifacts = {
            "window_request_json": bound_artifact(request_json_path),
            "observer_window_env": bound_artifact(env_file_path),
            "operator_approval_request_md": bound_artifact(operator_request_path),
        }
    except OSError as exc:
        add(blockers, "operator_approval_receipt_bound_artifact_unreadable", "operator_approval_receipt", error=str(exc))
        expected_artifacts = {}
    for key, expected in expected_artifacts.items():
        actual = bound_artifacts.get(key)
        if isinstance(actual, dict):
            require_keys(
                actual,
                required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_ARTIFACT_KEYS,
                label=f"operator_approval_receipt_bound_artifacts_{key}",
                blockers=blockers,
            )
        if actual != expected:
            add(
                blockers,
                f"operator_approval_receipt_{key}_artifact_mismatch",
                "operator_approval_receipt",
                expected=expected,
                actual=actual,
            )

    try:
        expected_digest = request_pack_digest(
            request_json_path=request_json_path,
            request_md_path=operator_request_path,
            env_path=env_file_path,
        )
    except OSError as exc:
        add(blockers, "operator_approval_receipt_digest_unreadable", "operator_approval_receipt", error=str(exc))
    else:
        if receipt.get("request_pack_digest") != expected_digest:
            add(
                blockers,
                "operator_approval_receipt_digest_mismatch",
                "operator_approval_receipt",
                expected=expected_digest,
                actual=receipt.get("request_pack_digest"),
            )

    flags = require_keys(
        receipt.get("non_authorization_flags"),
        required=EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS,
        label="operator_approval_receipt_non_authorization_flags",
        blockers=blockers,
    ) or {}
    for key in EXPECTED_OPERATOR_APPROVAL_RECEIPT_FLAG_KEYS:
        if flags.get(key) is not False:
            add(blockers, f"operator_approval_receipt_{key}_not_false", "operator_approval_receipt")

    return len(blockers) == initial_blocker_count


def build_report(
    validation: Validation,
    *,
    operator_request_verified: bool = False,
    operator_approval_receipt_verified: bool = False,
) -> dict[str, Any]:
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
        "operator_request_verified": operator_request_verified,
        "operator_approval_receipt_verified": operator_approval_receipt_verified,
        "target": payload.get("target"),
        "run_id": payload.get("run_id"),
        "approval_required": APPROVAL_TEXT,
        "non_claims": [
            "request-pack acceptance is pre-window planning only",
            "does not authorize server operations, marker/env changes, starts, restarts, stops, Discord, GitHub publication, runtime capture, public SDK readiness, or v1 completion",
            "does not promote public player identity, permissions/admin, command response, lookup, mutation, return override, or ResourceHandle",
        ],
    }


def tolerate_post_window_expiry_only(blockers: list[dict[str, Any]]) -> bool:
    if len(blockers) != 1:
        return False
    if blockers[0].get("reason") != "approved_window_expired":
        return False
    blockers.clear()
    return True


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    operator_request_path = args.operator_request or (args.request_json.parent / "operator-approval-request.md")
    validate_request_pack_sidecar_paths(
        request_json_path=args.request_json,
        env_file_path=args.env_file,
        operator_request_path=operator_request_path,
        blockers=blockers,
    )
    if args.operator_approval_receipt is not None:
        validate_operator_approval_receipt_path(
            request_json_path=args.request_json,
            receipt_path=args.operator_approval_receipt,
            blockers=blockers,
        )
        if not args.post_window_replay:
            add(
                blockers,
                "operator_approval_receipt_requires_post_window_replay",
                "operator_approval_receipt",
            )
    elif args.post_window_replay:
        add(
            blockers,
            "operator_approval_receipt_required_for_post_window_replay",
            "operator_approval_receipt",
        )
    payload = read_json(args.request_json)
    env = read_env(args.env_file, blockers)
    operator_request_markdown = read_text_sidecar(operator_request_path, "operator_request", blockers)
    validation = validate_payload(payload, env)
    validation.blockers[:0] = blockers
    operator_request_verified = validate_operator_request_markdown(
        payload,
        env,
        operator_request_markdown,
        validation.blockers,
    )
    if any(blocker.get("label") == "operator_request" for blocker in validation.blockers):
        operator_request_verified = False
    operator_approval_receipt_verified = False
    if args.operator_approval_receipt is not None:
        receipt_valid = validate_operator_approval_receipt(
            payload=payload,
            request_json_path=args.request_json,
            env_file_path=args.env_file,
            operator_request_path=operator_request_path,
            receipt_path=args.operator_approval_receipt,
            blockers=validation.blockers,
        )
        operator_approval_receipt_verified = bool(args.post_window_replay and receipt_valid)
    post_window_replay_expiry_tolerated = False
    if args.post_window_replay:
        post_window_replay_expiry_tolerated = tolerate_post_window_expiry_only(validation.blockers)
    report = build_report(
        validation,
        operator_request_verified=operator_request_verified,
        operator_approval_receipt_verified=operator_approval_receipt_verified,
    )
    report["post_window_replay"] = bool(args.post_window_replay)
    report["post_window_replay_expiry_tolerated"] = post_window_replay_expiry_tolerated
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"player_principal_lifecycle_window_request_ready={str(report['ready']).lower()}")
        if not report["ready"]:
            print("blockers=" + ",".join(report["blockers"]), file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
