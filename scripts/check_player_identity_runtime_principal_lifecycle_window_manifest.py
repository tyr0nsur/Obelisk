#!/usr/bin/env python3
"""Validate an offline player-principal lifecycle runtime window manifest.

The manifest is the secret-free `key=value` sidecar kept beside a copied Obelisk log.
This checker validates operational posture only. It does not approve public identity,
plugin delivery, permissions, commands, lookup, mutation, or runtime SDK readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths
from snapshot_evidence_pack import reject_symlink_component


REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)

RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
UTC_TIMESTAMP_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$")

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
    "pre_posture",
    "post_posture",
    "pre_check",
    "post_check",
    "rollback_completed",
    "rollback_delta",
    "observer_env_survived",
    "observer_marker_survived",
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
    if status.approved_offline_workspace:
        return "approved_offline_workspace"
    return "unprotected_offline"


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


def validate_manifest(fields: dict[str, str], manifest_path: Path) -> Validation:
    blockers: list[dict[str, Any]] = []
    timestamps: dict[str, datetime] = {}
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
    if obelisk_commit is not None and not SAFE_COMPONENT_RE.fullmatch(obelisk_commit):
        add(blockers, "obelisk_commit_invalid", "obelisk_commit")

    copied_log_sha256 = fields.get("copied_log_sha256")
    if copied_log_sha256 is not None and SHA256_RE.fullmatch(copied_log_sha256) is None:
        add(blockers, "copied_log_sha256_invalid", "copied_log_sha256")
    if fields.get("approval") != EXPECTED_APPROVAL:
        add(blockers, "approval_not_current_turn_runtime_window", "approval", expected=EXPECTED_APPROVAL)

    target = validate_target(fields, blockers)
    copied_log_status = validate_copied_log_path(fields, manifest_path, blockers)
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
    if not fields.get("rollback_delta"):
        add(blockers, "rollback_delta_missing", "rollback_delta")

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

    try:
        log_budget = int(fields.get("log_budget", ""))
    except ValueError:
        add(blockers, "log_budget_not_integer", "log_budget")
    else:
        if log_budget < 1 or log_budget > 10:
            add(blockers, "log_budget_out_of_range", "log_budget", minimum=1, maximum=10)

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
    for key in ("debug_escape_markers", "callback_escape_markers"):
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
        "obelisk_commit": "reviewed-obelisk-commit",
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
        "user_policy": "no_regular_users",
        "notice_sent": "not_applicable",
        "log_budget": "5",
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


def write_template(path: Path) -> None:
    reject_symlink_component(path, "--emit-template")
    resolved = protected_paths.reject_protected_input_path(
        path,
        "--emit-template",
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Secret-free operational manifest for a future approved player-principal lifecycle window.",
        "# Replace timestamps, run_id, copied_log_path, copied_log_sha256, and target with the reviewed window values.",
    ]
    lines.extend(f"{key}={value}" for key, value in build_template_fields().items())
    resolved.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report(fields: dict[str, str], validation: Validation, manifest_path: Path) -> dict[str, Any]:
    accepted = not validation.blockers
    return {
        "schema": REPORT_SCHEMA,
        "ready": accepted,
        "operational_window_manifest_ready": accepted,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": [] if accepted else ["window_manifest_not_accepted"],
        "run_id": fields.get("run_id"),
        "obelisk_commit": fields.get("obelisk_commit"),
        "target": {
            "instance": validation.target.instance,
            "map": validation.target.map_name,
        },
        "manifest": str(manifest_path),
        "copied_log": {
            "path": fields.get("copied_log_path"),
            "sha256": fields.get("copied_log_sha256"),
            "path_status": validation.copied_log_status,
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
        },
        "user_policy": validation.user_policy,
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
        write_template(args.emit_template)
        return 0
    if args.manifest is None:
        raise SystemExit("manifest is required unless --emit-template is used")
    fields = load_manifest(args.manifest)
    validation = validate_manifest(fields, args.manifest)
    report = build_report(fields, validation, args.manifest)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
