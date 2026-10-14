#!/usr/bin/env python3
"""Diff passive player-principal snapshot manifests without promoting evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import protected_paths
from capture_player_principal_passive_snapshot import parse_monitor_log_metadata


PASSIVE_SCHEMA = "obelisk.player-principal-passive-snapshot.v1"
REPORT_SCHEMA = "obelisk.player-principal-passive-snapshot-diff.v1"
LATEST_REPORT_SCHEMA = "obelisk.player-principal-passive-snapshot-latest.v1"
MONITOR_ONLY_REPORT_SCHEMA = "obelisk.player-principal-passive-monitor-only-summary.v1"
EVENT_TRIAGE_SCHEMA = "obelisk.player-principal-passive-observer-event-triage.v1"
ACTIONABILITY_SCHEMA = "obelisk.player-principal-passive-actionability.v1"
TARGET_TRIPLET_SCHEMA = "obelisk.player-principal-passive-target-triplet-candidate-summary.v1"
EXTENDED_MONITOR_TRIAGE_SCHEMA = "obelisk.player-principal-passive-extended-monitor-triage.v1"
RUNNER_ACTION_HINT_SCHEMA = "obelisk.player-principal-passive-runner-action-hint.v1"
PASSIVE_CLOSURE_SUMMARY_SCHEMA = "obelisk.player-principal-passive-closure-summary.v1"
CLOSURE_COMPATIBLE_RUN_ID_PATTERN = r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$"
CLOSURE_COMPATIBLE_RUN_ID_RE = re.compile(CLOSURE_COMPATIBLE_RUN_ID_PATTERN)
COUNT_KEYS = ("accepted", "rejected", "diagnostic_candidates")
REQUIRED_OBSERVER_EVENT_ROLES = ("session_start", "session_start_rejected", "session_end")
FORBIDDEN_PASSIVE_TRUE_CLAIM_KEYS = {
    "accepted_runtime_evidence",
    "approved_bundle_accepted",
    "approved_runtime_bundle_request_accepted",
    "approved_runtime_evidence",
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "authorizes_discord",
    "authorizes_runtime_work",
    "authorizes_server_operations",
    "authorizes_server_work",
    "authorizes_workspace_work",
    "authorizes_workspace_writes",
    "beta_notice_sent",
    "bundle_accepted",
    "closure_accepted",
    "closure_complete",
    "closure_root_valid_for_player_principal_lifecycle",
    "complete_sdk_allowed",
    "complete_sdk_claim_allowed",
    "complete_sdk_ready",
    "confirmed_beta_notice_sent",
    "confirmed_notice_sent",
    "counts_as_approved_runtime_evidence",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_as_p0_progress",
    "counts_as_sdk_progress",
    "counts_as_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "discord_sent",
    "evidence_closure_accepted",
    "evidence_closure_ready",
    "evidence_bundle_accepted",
    "live_ops_authorized",
    "marker_env_changes_authorized",
    "notice_action_sent",
    "notice_sent",
    "passive_monitor_root_accepted_as_closure_evidence_dir",
    "passive_snapshot_root_accepted_as_closure_evidence_dir",
    "player_notice_action_sent",
    "player_notice_sent",
    "promotion_ready",
    "public_abi_ready",
    "public_header_allowed",
    "public_sdk_ready",
    "read_live_logs",
    "ready",
    "route_ready",
    "runtime_capture_authorized",
    "runtime_window_closure_ready",
    "runtime_window_executor_closure_ready",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "runtime_ready",
    "runtime_work_authorized",
    "sdk_evidence_ready",
    "server_operations_authorized",
    "stable_claim_allowed",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "source_root_valid_for_closure",
    "valid_closure_root",
    "v1_completion",
    "v1_completion_ready",
    "workspace_writes_authorized",
}
FORBIDDEN_PASSIVE_PROGRESS_KEYS = {
    "claim_progress_contribution",
    "complete_sdk_claim_progress",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "complete_sdk_progress_percent",
    "complete_sdk_progress_ratio",
    "completion_blockers_promoted_count",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_progress_contribution",
    "p0_chain_progress",
    "p0_chain_promoted_count",
    "p0_progress",
    "progress",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_completion_count",
    "sdk_p0_progress",
    "sdk_progress",
    "sdk_progress_contribution",
    "v1_completion_contribution",
    "v1_sdk_progress",
}
SPLIT_PASSIVE_CLAIM_NAME_KEYS = {
    "alias",
    "claim",
    "field",
    "flag",
    "key",
    "name",
    "property",
}
SPLIT_PASSIVE_CLAIM_VALUE_KEYS = {
    "allowed",
    "enabled",
    "ready",
    "state",
    "status",
    "value",
}
REJECTED_DRIFT_TARGETS = (
    "ShooterGameMode.HandleNewPlayer",
    "ShooterGameMode.OnLogout",
)
SAFE_DIAGNOSTIC_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
FORBIDDEN_DIAGNOSTIC_VALUE_FRAGMENTS = {
    "classobject",
    "eosid",
    "ipaddress",
    "params",
    "playerdataid",
    "playerid",
    "playername",
    "pointer",
    "rawpointer",
    "resourcehandle",
    "steamid",
    "tribeid",
    "uniquenetid",
}
NON_CLAIMS = [
    "passive snapshot manifest diff only",
    "approved_runtime_evidence remains false",
    "ready remains false",
    "diagnostic candidate deltas remain non-evidence",
    "accepted observer event triplet candidates remain passive non-evidence until approved evidence checkers accept a copied sibling-set bundle",
    "passive activity triage fields remain non-evidence diagnostic pointers only",
    "passive actionability reasons are offline triage pointers only and do not authorize process control or evidence promotion",
    "passive runner action hints are non-authorizing triage hints only",
    "passive linger and observer-tail metadata remains process_control=none wait-only metadata",
    "passive closure summaries remain no-progress/no-readiness non-evidence and cannot be used as closure roots",
    "does not promote player identity, runtime readiness, public SDK readiness, or v1 completion",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--latest",
        action="store_true",
        help="summarize the newest manifest.json under the given snapshot root",
    )
    parser.add_argument(
        "--latest-diff",
        action="store_true",
        help="diff the two newest manifest.json files under the given snapshot root",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON output (currently the only supported output format)",
    )
    parser.add_argument(
        "--monitor-log",
        type=Path,
        help=(
            "optional passive monitor log to summarize as non-evidence metadata when "
            "--latest has no snapshots"
        ),
    )
    parser.add_argument("paths", nargs="*", type=Path)
    return parser.parse_args()


def require_paths(args: argparse.Namespace) -> tuple[Path, ...]:
    if args.latest and args.latest_diff:
        raise SystemExit("--latest and --latest-diff are mutually exclusive")
    if args.monitor_log is not None and not args.latest:
        raise SystemExit("--monitor-log is only supported with --latest")
    if args.latest:
        if len(args.paths) != 1:
            raise SystemExit("--latest requires exactly one snapshot root path")
        return (args.paths[0],)
    if args.latest_diff:
        if len(args.paths) != 1:
            raise SystemExit("--latest-diff requires exactly one snapshot root path")
        return (args.paths[0],)
    if len(args.paths) != 2:
        raise SystemExit("expected base_manifest and candidate_manifest paths")
    return (args.paths[0], args.paths[1])


def list_snapshot_manifests(snapshot_root: Path) -> tuple[Path, list[Path]]:
    protected_paths.reject_symlink_component(snapshot_root, "snapshot root")
    resolved = protected_paths.reject_protected_input_path(snapshot_root, "snapshot root")
    if not resolved.is_dir():
        raise SystemExit(f"snapshot root is not a directory: {resolved}")
    candidates = sorted(
        (path for path in resolved.rglob("manifest.json") if path.is_file()),
        key=lambda path: (path.stat().st_mtime_ns, str(path)),
        reverse=True,
    )
    return resolved, candidates


def find_snapshot_manifests(snapshot_root: Path) -> list[Path]:
    resolved, candidates = list_snapshot_manifests(snapshot_root)
    if not candidates:
        raise SystemExit(f"snapshot root contains no manifest.json files: {resolved}")
    return candidates


def find_latest_manifest(snapshot_root: Path) -> Path:
    return find_snapshot_manifests(snapshot_root)[0]


def find_latest_manifest_pair(snapshot_root: Path) -> tuple[Path, Path]:
    candidates = find_snapshot_manifests(snapshot_root)
    if len(candidates) < 2:
        raise SystemExit(f"snapshot root requires at least two manifest.json files for --latest-diff: {snapshot_root}")
    return candidates[1], candidates[0]


def load_manifest(path: Path, label: str) -> tuple[Path, dict[str, Any]]:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    if not resolved.is_file():
        raise SystemExit(f"{label} does not exist: {resolved}")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} is not valid JSON: {resolved}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label} must contain a JSON object: {resolved}")
    validate_passive_manifest(payload, label)
    return resolved, payload


def load_monitor_log(path: Path, label: str = "passive monitor log") -> tuple[Path, dict[str, Any]]:
    protected_paths.reject_symlink_component(path, label)
    resolved = protected_paths.reject_protected_input_path(path, label)
    if not resolved.is_file():
        raise SystemExit(f"{label} does not exist: {resolved}")
    metadata = parse_monitor_log_metadata(resolved)
    monitor = {
        "source_path": str(resolved),
        "copy_status": "metadata_only",
        "metadata": metadata,
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_monitor_metadata_non_evidence",
    }
    blockers: list[str] = []
    validate_no_forbidden_passive_claims(monitor, "$.monitor_log", blockers)
    validate_passive_summary_tree(monitor, "monitor_log", blockers)
    if blockers:
        raise SystemExit(f"{label} is not passive non-evidence metadata: {', '.join(blockers)}")
    return resolved, monitor


def validate_passive_manifest(payload: dict[str, Any], label: str) -> None:
    blockers: list[str] = []
    validate_no_forbidden_passive_claims(payload, "$", blockers)
    if payload.get("schema") != PASSIVE_SCHEMA:
        blockers.append("schema_not_passive_snapshot")
    if payload.get("approved_runtime_evidence") is not False:
        blockers.append("approved_runtime_evidence_not_false")
    if payload.get("ready") is not False:
        blockers.append("ready_not_false")
    if "route_ready" in payload and payload.get("route_ready") is not False:
        blockers.append("route_ready_not_false")
    if payload.get("readiness_gate") not in (None, "none"):
        blockers.append("readiness_gate_not_none")
    if payload.get("evidence_classification") != "passive_snapshot_non_evidence":
        blockers.append("evidence_classification_not_passive_snapshot_non_evidence")
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not any(
        "non-evidence" in str(claim) for claim in non_claims
    ):
        blockers.append("missing_non_evidence_non_claim")
    validate_passive_non_evidence_object(
        payload.get("diagnostics"),
        "diagnostics",
        blockers,
        require_evidence_classification=False,
    )
    validate_passive_server_activity_summary(
        payload.get("passive_server_activity_summary"),
        "passive_server_activity_summary",
        blockers,
    )
    validate_passive_wait_metadata(
        payload.get("passive_wait_metadata"),
        "passive_wait_metadata",
        blockers,
    )
    validate_passive_non_evidence_object(
        payload.get("passive_closure_summary"),
        "passive_closure_summary",
        blockers,
    )
    validate_passive_summary_tree(
        payload.get("passive_closure_summary"),
        "passive_closure_summary",
        blockers,
    )
    targets = payload.get("targets")
    if not isinstance(targets, list):
        blockers.append("targets_not_list")
    else:
        for index, target in enumerate(targets):
            if not isinstance(target, dict):
                blockers.append(f"target_{index}_not_object")
                continue
            if target.get("approved_runtime_evidence") is not False:
                blockers.append(f"target_{index}_approved_runtime_evidence_not_false")
            if target.get("ready") is True:
                blockers.append(f"target_{index}_ready_true")
            if "route_ready" in target and target.get("route_ready") is not False:
                blockers.append(f"target_{index}_route_ready_not_false")
            if target.get("readiness_gate") not in (None, "none"):
                blockers.append(f"target_{index}_readiness_gate_not_none")
            if (
                "evidence_classification" in target
                and target.get("evidence_classification") != "passive_snapshot_non_evidence"
            ):
                blockers.append(
                    f"target_{index}_evidence_classification_not_passive_snapshot_non_evidence"
                )
            validate_passive_non_evidence_object(
                target.get("observer_event_triage"),
                f"target_{index}_observer_event_triage",
                blockers,
            )
            validate_passive_non_evidence_object(
                target.get("diagnostics"),
                f"target_{index}_diagnostics",
                blockers,
                require_evidence_classification=False,
            )
            validate_passive_non_evidence_object(
                target.get("query_state"),
                f"target_{index}_query_state",
                blockers,
                require_evidence_classification=False,
            )
    for field in ("query_state_by_target", "query_state_by_alias"):
        states = payload.get(field)
        if not isinstance(states, dict):
            continue
        for key, state in states.items():
            if isinstance(key, str):
                validate_passive_non_evidence_object(
                    state,
                    f"{field}_{key}",
                    blockers,
                    require_evidence_classification=False,
                )
    if blockers:
        raise SystemExit(f"{label} is not a passive non-evidence manifest: {', '.join(blockers)}")


def passive_false_or_zero(value: Any) -> bool:
    return value is False or value == 0 or value is None


def normalized_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


NORMALIZED_FORBIDDEN_PASSIVE_TRUE_CLAIM_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_PASSIVE_TRUE_CLAIM_KEYS
}
NORMALIZED_FORBIDDEN_PASSIVE_PROGRESS_KEYS = {
    normalized_claim_key(key) for key in FORBIDDEN_PASSIVE_PROGRESS_KEYS
}


def positive_passive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "complete",
            "enabled",
            "present",
            "ready",
            "sent",
            "supported",
            "true",
            "unlocked",
            "yes",
        }
    if isinstance(value, dict):
        return any(positive_passive_claim_value(item) for item in value.values())
    if isinstance(value, list):
        return any(positive_passive_claim_value(item) for item in value)
    return False


def validate_no_forbidden_passive_claims(value: Any, path: str, blockers: list[str]) -> None:
    if isinstance(value, dict):
        declared_claim_names = [
            nested
            for key, nested in value.items()
            if normalized_claim_key(key) in SPLIT_PASSIVE_CLAIM_NAME_KEYS
            and isinstance(nested, str)
        ]
        declared_claim_values = [
            nested
            for key, nested in value.items()
            if normalized_claim_key(key) in SPLIT_PASSIVE_CLAIM_VALUE_KEYS
        ]
        for claim_name in declared_claim_names:
            normalized_claim_name = normalized_claim_key(claim_name)
            if normalized_claim_name in NORMALIZED_FORBIDDEN_PASSIVE_TRUE_CLAIM_KEYS:
                if not declared_claim_values or any(positive_passive_claim_value(item) for item in declared_claim_values):
                    blockers.append(f"forbidden_passive_claim:{path}")
            if normalized_claim_name in NORMALIZED_FORBIDDEN_PASSIVE_PROGRESS_KEYS:
                if not declared_claim_values or any(positive_passive_claim_value(item) for item in declared_claim_values):
                    blockers.append(f"forbidden_passive_progress_claim:{path}")
        for key, nested in value.items():
            nested_path = f"{path}.{key}" if path != "$" else f"$.{key}"
            normalized_key = normalized_claim_key(key)
            if normalized_key in NORMALIZED_FORBIDDEN_PASSIVE_TRUE_CLAIM_KEYS and not passive_false_or_zero(nested):
                blockers.append(f"forbidden_passive_claim:{nested_path}")
            if normalized_key in NORMALIZED_FORBIDDEN_PASSIVE_PROGRESS_KEYS and not passive_false_or_zero(nested):
                blockers.append(f"forbidden_passive_progress_claim:{nested_path}")
            if normalized_key == "readiness_gate" and nested not in (None, "none"):
                blockers.append(f"forbidden_passive_readiness_gate:{nested_path}")
            if normalized_key == "process_control" and nested not in (None, "none"):
                blockers.append(f"forbidden_passive_process_control:{nested_path}")
            validate_no_forbidden_passive_claims(nested, nested_path, blockers)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            validate_no_forbidden_passive_claims(nested, f"{path}[{index}]", blockers)


def validate_passive_server_activity_summary(value: Any, path: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        return
    validate_passive_non_evidence_object(
        value,
        path,
        blockers,
        require_evidence_classification=False,
    )
    if value.get("process_control") not in (None, "none"):
        blockers.append(f"{path}_process_control_not_none")
    for field in (
        "targets",
        "latest_rejected_drift_reason_by_snapshot_target",
        "latest_rejected_drift_reason_by_lifecycle_target",
    ):
        nested = value.get(field)
        if not isinstance(nested, dict):
            continue
        validate_passive_summary_tree(nested, f"{path}_{field}", blockers)


def validate_passive_wait_metadata(value: Any, path: str, blockers: list[str]) -> None:
    if not isinstance(value, dict):
        return
    validate_passive_non_evidence_object(
        value,
        path,
        blockers,
        require_evidence_classification=False,
    )
    if value.get("process_control") not in (None, "none"):
        blockers.append(f"{path}_process_control_not_none")
    for field in ("observer_tail_by_target", "observer_tail_by_alias", "linger_by_target"):
        nested = value.get(field)
        if not isinstance(nested, dict):
            continue
        validate_passive_summary_tree(nested, f"{path}_{field}", blockers)
    linger_events = value.get("linger_events")
    if isinstance(linger_events, list):
        validate_passive_summary_tree(linger_events, f"{path}_linger_events", blockers)


def validate_passive_summary_tree(value: Any, path: str, blockers: list[str]) -> None:
    if isinstance(value, dict):
        if (
            value.get("approved_runtime_evidence") is not None
            and value.get("approved_runtime_evidence") is not False
        ):
            blockers.append(f"{path}_approved_runtime_evidence_not_false")
        if value.get("ready") is True:
            blockers.append(f"{path}_ready_true")
        if (
            value.get("route_ready") is not None
            and value.get("route_ready") is not False
        ):
            blockers.append(f"{path}_route_ready_not_false")
        if value.get("readiness_gate") not in (None, "none"):
            blockers.append(f"{path}_readiness_gate_not_none")
        if value.get("process_control") not in (None, "none"):
            blockers.append(f"{path}_process_control_not_none")
        for key, nested in value.items():
            validate_passive_summary_tree(nested, f"{path}_{key}", blockers)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            validate_passive_summary_tree(nested, f"{path}_{index}", blockers)


def validate_passive_non_evidence_object(
    value: Any,
    path: str,
    blockers: list[str],
    *,
    require_evidence_classification: bool = True,
) -> None:
    if not isinstance(value, dict):
        return
    if "approved_runtime_evidence" in value and value.get("approved_runtime_evidence") is not False:
        blockers.append(f"{path}_approved_runtime_evidence_not_false")
    if value.get("ready") is True:
        blockers.append(f"{path}_ready_true")
    if "route_ready" in value and value.get("route_ready") is not False:
        blockers.append(f"{path}_route_ready_not_false")
    if value.get("readiness_gate") not in (None, "none"):
        blockers.append(f"{path}_readiness_gate_not_none")
    if require_evidence_classification and value.get("evidence_classification") not in (
        None,
        "passive_snapshot_non_evidence",
        "passive_monitor_metadata_non_evidence",
        "passive_alias_presence_metadata_non_evidence",
        "passive_closure_non_evidence",
    ):
        blockers.append(f"{path}_evidence_classification_not_passive_non_evidence")
    nested_triage = value.get("observer_event_triage")
    if isinstance(nested_triage, dict) and nested_triage is not value:
        validate_passive_non_evidence_object(
            nested_triage,
            f"{path}_observer_event_triage",
            blockers,
        )


def int_count(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def str_list(value: Any, *, allowed: tuple[str, ...] | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    allowed_values = set(allowed or ())
    items = {
        item
        for item in value
        if isinstance(item, str) and (allowed is None or item in allowed_values)
    }
    if allowed is None:
        return sorted(items)
    return [item for item in allowed if item in items]


def str_key_list(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    return sorted(key for key in value if isinstance(key, str))


def merge_observer_event_roles(*values: Any) -> list[str]:
    roles: set[str] = set()
    for value in values:
        roles.update(str_list(value, allowed=REQUIRED_OBSERVER_EVENT_ROLES))
    return [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role in roles]


def int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def safe_diagnostic_token(value: Any) -> str | None:
    if not isinstance(value, str) or not SAFE_DIAGNOSTIC_TOKEN_RE.fullmatch(value):
        return None
    normalized = re.sub(r"[_\.\:-]+", "", value.lower())
    if "0x" in value.lower() or "0x" in normalized:
        return None
    if any(fragment in normalized for fragment in FORBIDDEN_DIAGNOSTIC_VALUE_FRAGMENTS):
        return None
    return value


def safe_event_time(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    if not re.fullmatch(r"^[A-Za-z0-9_.:+-]+$", value):
        return None
    normalized = re.sub(r"[_\.\:+-]+", "", value.lower())
    if any(fragment in normalized for fragment in FORBIDDEN_DIAGNOSTIC_VALUE_FRAGMENTS):
        return None
    return value


def sanitized_role_event_times(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    times: dict[str, str] = {}
    for role in REQUIRED_OBSERVER_EVENT_ROLES:
        event_time = safe_event_time(value.get(role))
        if event_time is not None:
            times[role] = event_time
    return times


def event_time_from_mapping(value: dict[str, Any]) -> str | None:
    for field in ("last_event_utc", "timestamp_utc", "utc", "timestamp_prefix", "timestamp"):
        event_time = safe_event_time(value.get(field))
        if event_time is not None:
            return event_time
    return None


def sanitized_rejected_drift(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    target = value.get("target")
    sequence = int_or_none(value.get("sequence"))
    line_number = int_or_none(value.get("line_number"))
    fname_index = int_or_none(value.get("fname_index"))
    reason = safe_diagnostic_token(value.get("reason"))
    reason_kind = safe_diagnostic_token(value.get("reason_kind"))
    if (
        target not in REJECTED_DRIFT_TARGETS
        or sequence is None
        or line_number is None
        or fname_index is None
        or value.get("reflection_status") != "rejected"
        or reason is None
        or reason_kind != "lifecycle_property_FName_drift"
    ):
        return None
    timestamp_prefix = value.get("timestamp_prefix")
    output: dict[str, Any] = {
        "target": target,
        "sequence": sequence,
        "line_number": line_number,
        "timestamp_prefix": timestamp_prefix if isinstance(timestamp_prefix, str) else None,
        "fname_index": fname_index,
        "reflection_status": "rejected",
        "read_status": safe_diagnostic_token(value.get("read_status")),
        "reason": reason,
        "reason_kind": reason_kind,
        "evidence_claim": "none",
        "evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }
    if (function_name_index := int_or_none(value.get("function_name_index"))) is not None:
        output["function_name_index"] = function_name_index
    if (outer_name_index := int_or_none(value.get("outer_name_index"))) is not None:
        output["outer_name_index"] = outer_name_index
    if (drift_count := int_or_none(value.get("drift_count"))) is not None:
        output["drift_count"] = drift_count
    drifts = []
    if isinstance(value.get("drifts"), list):
        for drift in value["drifts"]:
            if not isinstance(drift, dict):
                continue
            index = int_or_none(drift.get("index"))
            position = int_or_none(drift.get("position"))
            expected = int_or_none(drift.get("expected_name_index"))
            observed = int_or_none(drift.get("observed_name_index"))
            delta = int_or_none(drift.get("delta"))
            if None in (index, position, expected, observed, delta):
                continue
            drifts.append(
                {
                    "index": index,
                    "position": position,
                    "expected_name_index": expected,
                    "observed_name_index": observed,
                    "delta": delta,
                }
            )
    if drifts:
        output["drifts"] = sorted(drifts, key=lambda item: item["index"])
    return output


def sanitized_rejected_drift_by_lifecycle_target(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    sanitized: dict[str, dict[str, Any]] = {}
    for target in REJECTED_DRIFT_TARGETS:
        drift = sanitized_rejected_drift(value.get(target))
        if drift is not None:
            sanitized[target] = drift
    return sanitized


def sanitized_rejected_drift_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for target in REJECTED_DRIFT_TARGETS:
        count = int_count(value.get(target))
        if count > 0:
            counts[target] = count
    return counts


def int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return sorted({item for item in value if isinstance(item, int) and not isinstance(item, bool)})


def sanitized_observer_line(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    line_number = int_or_none(value.get("line_number"))
    source_index = int_or_none(value.get("source_index"))
    kind = value.get("kind")
    timestamp_prefix = value.get("timestamp_prefix")
    if line_number is None or source_index is None or not isinstance(kind, str):
        return None
    return {
        "source_index": source_index,
        "line_number": line_number,
        "timestamp_prefix": timestamp_prefix if isinstance(timestamp_prefix, str) else None,
        "kind": kind,
    }


def analyzer_player_principal_module(target: dict[str, Any]) -> dict[str, Any]:
    analyzer = target.get("analyzer")
    if not isinstance(analyzer, dict):
        return {}
    summary = analyzer.get("summary")
    if not isinstance(summary, dict):
        return {}
    modules = summary.get("modules")
    if not isinstance(modules, dict):
        return {}
    module = modules.get("player_principal_lifecycle")
    return module if isinstance(module, dict) else {}


def accepted_observer_event_roles(module: dict[str, Any], triage: dict[str, Any]) -> list[str]:
    cases = module.get("observed_event_cases")
    if isinstance(cases, list):
        roles = {
            role
            for case in cases
            if isinstance(case, dict)
            and isinstance((role := case.get("role")), str)
            and role in REQUIRED_OBSERVER_EVENT_ROLES
        }
        if roles:
            return [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role in roles]
    return str_list(triage.get("accepted_observer_event_roles"), allowed=REQUIRED_OBSERVER_EVENT_ROLES)


def observer_event_last_times_from_module(module: dict[str, Any]) -> dict[str, str]:
    cases = module.get("observed_event_cases")
    if not isinstance(cases, list):
        return {}
    times: dict[str, str] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        role = case.get("role")
        if role not in REQUIRED_OBSERVER_EVENT_ROLES:
            continue
        event_time = event_time_from_mapping(case)
        if event_time is not None:
            times[role] = event_time
    return times


def observer_event_last_times_from_triage(triage: dict[str, Any]) -> dict[str, str]:
    times = sanitized_role_event_times(triage.get("last_event_times"))
    if not times:
        times = sanitized_role_event_times(triage.get("observer_event_last_event_times"))
    return times


def observer_event_triage_classification(
    *,
    accepted_count: int,
    rejected_count: int,
    diagnostic_count: int,
    complete_triplet: bool,
) -> str:
    if complete_triplet:
        return "complete_accepted_observer_event_triplet_candidate_non_evidence"
    if accepted_count > 0:
        return "partial_accepted_observer_event_triplet_candidate_non_evidence"
    if rejected_count > 0:
        return "rejected_observer_event_lines_non_evidence"
    if diagnostic_count > 0:
        return "diagnostic_only_lines_non_evidence"
    return "no_player_principal_observer_lines_non_evidence"


def observer_event_triage_for_target(
    target: dict[str, Any],
    counts: dict[str, int],
    module: dict[str, Any],
) -> dict[str, Any]:
    existing = target.get("observer_event_triage")
    if not isinstance(existing, dict):
        diagnostics = target.get("diagnostics")
        existing = diagnostics.get("observer_event_triage") if isinstance(diagnostics, dict) else {}
    if not isinstance(existing, dict):
        existing = {}
    accepted_count = int_count(
        existing.get("accepted_observer_event_triplet_candidate_count", counts["accepted"])
    )
    rejected_count = int_count(
        existing.get("rejected_observer_event_line_count", counts["rejected"])
    )
    diagnostic_count = int_count(
        existing.get("diagnostic_only_line_count", counts["diagnostic_candidates"])
    )
    roles = accepted_observer_event_roles(module, existing)
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in roles]
    complete_triplet = accepted_count > 0 and not missing_roles
    last_event_times = observer_event_last_times_from_triage(existing)
    last_event_times.update(observer_event_last_times_from_module(module))
    return {
        "schema": EVENT_TRIAGE_SCHEMA,
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "rejected_observer_event_line_count": rejected_count,
        "diagnostic_only_line_count": diagnostic_count,
        "contains_accepted_observer_event_triplet_candidates": accepted_count > 0,
        "contains_diagnostic_only_lines": diagnostic_count > 0,
        "accepted_observer_event_roles": roles,
        "roles_seen": roles,
        "missing_observer_event_triplet_roles": missing_roles,
        "missing_roles": missing_roles,
        "complete_observer_event_triplet_candidate_present": complete_triplet,
        "complete_triplet_candidate": complete_triplet,
        "last_event_times": last_event_times,
        "classification": observer_event_triage_classification(
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            diagnostic_count=diagnostic_count,
            complete_triplet=complete_triplet,
        ),
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


def target_key(target: dict[str, Any]) -> str:
    instance = str(target.get("instance", "unknown"))
    game_map = str(target.get("map", "unknown"))
    query_port = str(target.get("query_port") or "")
    if query_port:
        return f"{instance}:{game_map}:{query_port}"
    return f"{instance}:{game_map}"


def target_alias_key(target: dict[str, Any]) -> str:
    instance = str(target.get("instance", "unknown"))
    game_map = str(target.get("map", "unknown"))
    return f"{instance}:{game_map}"


def is_exact_target_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parts = value.split(":")
    return len(parts) == 3 and parts[2].isdigit()


def query_state_exact_for_target(value: Any, target: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("target_key_kind") == "alias":
        return None
    expected_key = target_key(target)
    expected_port = str(target.get("query_port") or "")
    if expected_port and not is_exact_target_key(expected_key):
        return None
    state_key = value.get("target_key")
    if isinstance(state_key, str) and state_key and state_key != expected_key:
        return None
    state_instance = str(value.get("instance") or target.get("instance") or "")
    state_map = str(value.get("map") or target.get("map") or "")
    if state_instance != str(target.get("instance") or ""):
        return None
    if state_map != str(target.get("map") or ""):
        return None
    state_port = str(value.get("query_port") or "")
    if expected_port and state_port != expected_port:
        return None
    normalized = dict(value)
    normalized["target_key"] = expected_key
    normalized["target_key_kind"] = "exact" if expected_port else "alias"
    normalized["alias_target_key"] = target_alias_key(target)
    normalized["query_port"] = expected_port
    normalized["query_presence_eligible"] = bool(expected_port)
    normalized["approved_runtime_evidence"] = False
    normalized["ready"] = False
    normalized["route_ready"] = False
    return normalized


def counts_for_target(target: dict[str, Any]) -> dict[str, int]:
    counts = target.get("counts")
    if not isinstance(counts, dict):
        counts = {}
    module = analyzer_player_principal_module(target)
    return {
        "accepted": int_count(counts.get("accepted", module.get("accepted_count"))),
        "rejected": int_count(counts.get("rejected", module.get("rejected_count"))),
        "diagnostic_candidates": int_count(
            counts.get("diagnostic_candidates", module.get("diagnostic_candidate_count"))
        ),
    }


def diagnostics_for_target(target: dict[str, Any]) -> dict[str, Any]:
    counts = counts_for_target(target)
    module = analyzer_player_principal_module(target)
    observer_event_triage = observer_event_triage_for_target(target, counts, module)
    diagnostics = target.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    max_sequence = int_or_none(diagnostics.get("max_sequence"))
    if max_sequence is None:
        max_sequence = int_or_none(module.get("diagnostic_candidate_max_sequence"))
    log_limits = int_list(diagnostics.get("log_limits"))
    if not log_limits:
        log_limits = int_list(module.get("diagnostic_log_limits"))
    only_non_evidence = diagnostics.get("only_non_evidence")
    if not isinstance(only_non_evidence, bool):
        module_only_non_evidence = module.get("diagnostic_only_non_evidence")
        if isinstance(module_only_non_evidence, bool):
            only_non_evidence = module_only_non_evidence
        else:
            only_non_evidence = (
                counts["accepted"] == 0
                and counts["rejected"] == 0
                and counts["diagnostic_candidates"] > 0
            )
    latest_observer_line = sanitized_observer_line(diagnostics.get("latest_observer_line"))
    if latest_observer_line is None:
        latest_observer_line = sanitized_observer_line(module.get("latest_observer_line"))
    latest_rejected_drift = sanitized_rejected_drift_by_lifecycle_target(
        diagnostics.get("latest_rejected_drift_by_lifecycle_target")
    )
    if not latest_rejected_drift:
        latest_rejected_drift = sanitized_rejected_drift_by_lifecycle_target(
            module.get("diagnostic_candidate_latest_rejected_drift_by_target")
        )
    rejected_drift_counts = sanitized_rejected_drift_counts(
        diagnostics.get("rejected_drift_target_counts")
    )
    if not rejected_drift_counts:
        rejected_drift_counts = sanitized_rejected_drift_counts(
            module.get("diagnostic_candidate_rejected_drift_target_counts")
        )
    rejected_drift_count = int_count(
        diagnostics.get(
            "rejected_drift_count",
            module.get("diagnostic_candidate_rejected_drift_count"),
        )
    )
    return {
        "candidate_count": int_count(
            diagnostics.get("candidate_count", module.get("diagnostic_candidate_count", counts["diagnostic_candidates"]))
        ),
        "max_sequence": max_sequence,
        "log_limits": log_limits,
        "log_budget_reached": (
            diagnostics.get("log_budget_reached") is True
            or module.get("diagnostic_log_budget_reached") is True
        ),
        "only_non_evidence": only_non_evidence,
        "latest_observer_line": latest_observer_line,
        "classification": str(diagnostics.get("classification") or "passive_snapshot_non_evidence"),
        "observer_event_triage": observer_event_triage,
        "accepted_observer_event_triplet_candidate_count": observer_event_triage[
            "accepted_observer_event_triplet_candidate_count"
        ],
        "complete_observer_event_triplet_candidate_present": observer_event_triage[
            "complete_observer_event_triplet_candidate_present"
        ],
        "observer_event_roles_seen": observer_event_triage["roles_seen"],
        "observer_event_missing_roles": observer_event_triage["missing_roles"],
        "observer_event_last_event_times": observer_event_triage["last_event_times"],
        "event_triplet_classification": observer_event_triage["classification"],
        "rejected_drift_count": rejected_drift_count,
        "rejected_drift_target_counts": rejected_drift_counts,
        "latest_rejected_drift_by_lifecycle_target": latest_rejected_drift,
        "contains_rejected_drift": rejected_drift_count > 0 or bool(latest_rejected_drift),
        "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
    }


def index_targets(manifest: dict[str, Any]) -> dict[str, dict[str, int]]:
    indexed: dict[str, dict[str, int]] = {}
    for target in manifest.get("targets") or []:
        if not isinstance(target, dict):
            continue
        indexed[target_key(target)] = counts_for_target(target)
    return indexed


def index_target_diagnostics(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for target in manifest.get("targets") or []:
        if not isinstance(target, dict):
            continue
        indexed[target_key(target)] = diagnostics_for_target(target)
    return indexed


def sanitized_query_state(value: Any, target: dict[str, Any] | None = None) -> dict[str, Any]:
    state = value if isinstance(value, dict) else {}
    target = target or {}
    expected_key = target_key(target) if target else state.get("target_key")
    target_key_value = state.get("target_key") if isinstance(state.get("target_key"), str) else expected_key
    query_port = str(state.get("query_port") or target.get("query_port") or "")
    target_key_kind = (
        "exact"
        if query_port and is_exact_target_key(target_key_value)
        else "alias"
        if target_key_value
        else "not_reported"
    )
    return {
        "target_key": target_key_value,
        "target_key_kind": target_key_kind,
        "alias_target_key": state.get("alias_target_key")
        if isinstance(state.get("alias_target_key"), str)
        else target_alias_key(target)
        if target
        else None,
        "instance": state.get("instance") or target.get("instance") or "unknown",
        "map": state.get("map") or target.get("map") or "unknown",
        "query_port": query_port,
        "status": str(state.get("status") or "not_reported"),
        "current_map": state.get("current_map") if isinstance(state.get("current_map"), str) else None,
        "players": state.get("players") if isinstance(state.get("players"), str) else None,
        "players_current": int_or_none(state.get("players_current")),
        "players_max": int_or_none(state.get("players_max")),
        "last_query_utc": state.get("last_query_utc") if isinstance(state.get("last_query_utc"), str) else None,
        "presence_detected": state.get("presence_detected") is True,
        "last_presence_detected_utc": (
            state.get("last_presence_detected_utc")
            if isinstance(state.get("last_presence_detected_utc"), str)
            else None
        ),
        "error": state.get("error") if isinstance(state.get("error"), str) else None,
        "last_warning_rc": int_or_none(state.get("last_warning_rc")),
        "query_presence_eligible": target_key_kind == "exact",
        "evidence_classification": str(
            state.get("evidence_classification") or "passive_monitor_metadata_non_evidence"
        ),
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
    }


def index_target_query_state(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    query_state_by_instance = manifest.get("query_state_by_instance")
    if not isinstance(query_state_by_instance, dict):
        query_state_by_instance = {}
    query_state_by_target = manifest.get("query_state_by_target")
    if not isinstance(query_state_by_target, dict):
        query_state_by_target = {}
    for target in manifest.get("targets") or []:
        if not isinstance(target, dict):
            continue
        key = target_key(target)
        instance = str(target.get("instance") or "")
        query_state = (
            query_state_exact_for_target(target.get("query_state"), target)
            or query_state_exact_for_target(query_state_by_target.get(key), target)
            or query_state_exact_for_target(query_state_by_instance.get(instance), target)
        )
        state = sanitized_query_state(query_state, target)
        if state.get("target_key_kind") == "exact":
            indexed[key] = state
    return indexed


def sanitized_alias_query_state(value: Any, alias_key: str) -> dict[str, Any]:
    state = value if isinstance(value, dict) else {}
    return {
        "target_key": alias_key,
        "target_key_kind": "alias",
        "alias_target_key": alias_key,
        "exact_target_key": state.get("exact_target_key")
        if isinstance(state.get("exact_target_key"), str)
        else None,
        "instance": state.get("instance") if isinstance(state.get("instance"), str) else "unknown",
        "map": state.get("map") if isinstance(state.get("map"), str) else "unknown",
        "query_port": "",
        "status": str(state.get("status") or "alias_metadata_only"),
        "players_current": int_or_none(state.get("players_current")),
        "players_max": int_or_none(state.get("players_max")),
        "last_query_utc": state.get("last_query_utc")
        if isinstance(state.get("last_query_utc"), str)
        else None,
        "presence_detected": state.get("presence_detected") is True,
        "last_presence_detected_utc": (
            state.get("last_presence_detected_utc")
            if isinstance(state.get("last_presence_detected_utc"), str)
            else None
        ),
        "query_presence_eligible": False,
        "alias_presence_metadata_only": True,
        "evidence_classification": "passive_alias_presence_metadata_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
    }


def index_alias_query_states(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    aliases: dict[str, dict[str, Any]] = {}
    query_state_by_alias = manifest.get("query_state_by_alias")
    if isinstance(query_state_by_alias, dict):
        for key, state in query_state_by_alias.items():
            if isinstance(key, str) and not is_exact_target_key(key):
                aliases[key] = sanitized_alias_query_state(state, key)
    query_state_by_target = manifest.get("query_state_by_target")
    if isinstance(query_state_by_target, dict):
        for key, state in query_state_by_target.items():
            if isinstance(key, str) and not is_exact_target_key(key):
                aliases.setdefault(key, sanitized_alias_query_state(state, key))
    return aliases


def monitor_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    monitor = manifest.get("monitor_log")
    if not isinstance(monitor, dict):
        return {"status": "not_reported"}
    metadata = monitor.get("metadata")
    if not isinstance(metadata, dict):
        return {
            "status": monitor.get("copy_status", "metadata_missing"),
            "latest_tick_utc": None,
            "session": {"status": "not_reported"},
            "replacement": {"status": "not_reported"},
            "observer_tail_by_target": {},
            "linger_by_target": {},
            "linger_events": [],
            "process_control": "none",
        }
    session = metadata.get("session")
    replacement = metadata.get("replacement")
    observer_tail_by_target = metadata.get("observer_tail_by_target")
    if not isinstance(observer_tail_by_target, dict):
        observer_tail_by_target = {}
    observer_tail_by_alias = metadata.get("observer_tail_by_alias")
    if not isinstance(observer_tail_by_alias, dict):
        observer_tail_by_alias = {}
    linger_by_target = metadata.get("linger_by_target")
    if not isinstance(linger_by_target, dict):
        linger_by_target = {}
    linger_events = metadata.get("linger_events")
    if not isinstance(linger_events, list):
        linger_events = []
    return {
        "status": monitor.get("copy_status", "unknown"),
        "latest_tick_utc": metadata.get("latest_tick_utc")
        if isinstance(metadata.get("latest_tick_utc"), str)
        else None,
        "session": session if isinstance(session, dict) else {"status": "not_reported"},
        "replacement": replacement if isinstance(replacement, dict) else {"status": "not_reported"},
        "observer_tail_by_target": observer_tail_by_target,
        "observer_tail_by_alias": observer_tail_by_alias,
        "linger_by_target": linger_by_target,
        "linger_events": linger_events,
        "process_control": "none",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


def passive_wait_metadata_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    wait_metadata = manifest.get("passive_wait_metadata")
    if isinstance(wait_metadata, dict):
        observer_tail_by_target = wait_metadata.get("observer_tail_by_target")
        observer_tail_by_alias = wait_metadata.get("observer_tail_by_alias")
        linger_by_target = wait_metadata.get("linger_by_target")
        linger_events = wait_metadata.get("linger_events")
    else:
        monitor = manifest.get("monitor_log")
        metadata = monitor.get("metadata") if isinstance(monitor, dict) else {}
        if not isinstance(metadata, dict):
            metadata = {}
        observer_tail_by_target = metadata.get("observer_tail_by_target")
        observer_tail_by_alias = metadata.get("observer_tail_by_alias")
        linger_by_target = metadata.get("linger_by_target")
        linger_events = metadata.get("linger_events")
    return {
        "schema": "obelisk.player-principal-passive-wait-metadata.v1",
        "wait_scope": "metadata_only",
        "observer_tail_scope": "per_target",
        "observer_tail_by_target": observer_tail_by_target
        if isinstance(observer_tail_by_target, dict)
        else {},
        "observer_tail_by_alias": observer_tail_by_alias
        if isinstance(observer_tail_by_alias, dict)
        else {},
        "linger_by_target": linger_by_target if isinstance(linger_by_target, dict) else {},
        "linger_events": linger_events if isinstance(linger_events, list) else [],
        "process_control": "none",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_wait_metadata_non_evidence",
    }


def total_counts(targets: dict[str, dict[str, int]]) -> dict[str, int]:
    return {
        key: sum(counts.get(key, 0) for counts in targets.values())
        for key in COUNT_KEYS
    }


def delta_counts(base: dict[str, int], candidate: dict[str, int]) -> dict[str, int]:
    return {key: candidate.get(key, 0) - base.get(key, 0) for key in COUNT_KEYS}


def diagnostic_max_delta(base: int | None, candidate: int | None) -> int | None:
    if base is None or candidate is None:
        return None
    return candidate - base


def diagnostic_sequence_advanced(base: int | None, candidate: int | None) -> bool:
    if candidate is None:
        return False
    if base is None:
        return True
    return candidate > base


def query_presence_detected(state: dict[str, Any]) -> bool:
    players_current = int_or_none(state.get("players_current"))
    return state.get("presence_detected") is True or (
        players_current is not None and players_current > 0
    )


def query_status_token(value: Any) -> str:
    return safe_diagnostic_token(value) or "not_reported"


def target_metadata_from_key(value: str) -> dict[str, str]:
    parts = value.split(":")
    if len(parts) >= 2:
        return {
            "instance": parts[0],
            "map": parts[1],
            "query_port": parts[2] if len(parts) >= 3 else "",
        }
    return {"instance": "unknown", "map": "unknown", "query_port": ""}


def sanitized_drift_reason_for_summary(value: Any) -> dict[str, Any] | None:
    drift = sanitized_rejected_drift(value)
    if drift is None:
        return None
    return {
        "target": drift["target"],
        "sequence": drift["sequence"],
        "line_number": drift["line_number"],
        "timestamp_prefix": drift["timestamp_prefix"],
        "fname_index": drift["fname_index"],
        "reflection_status": "rejected",
        "read_status": drift.get("read_status"),
        "reason": drift["reason"],
        "reason_kind": drift["reason_kind"],
        "drift_count": int_or_none(drift.get("drift_count")),
        "evidence_claim": "none",
        "evidence_classification": "diagnostic_rejected_drift_reason_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "process_control": "none",
    }


def observer_tail_for_target(
    wait_metadata: dict[str, Any] | None,
    target_key_value: str,
) -> dict[str, Any]:
    if not isinstance(wait_metadata, dict):
        return {}
    observer_tail_by_target = wait_metadata.get("observer_tail_by_target")
    if not isinstance(observer_tail_by_target, dict):
        return {}
    tail = observer_tail_by_target.get(target_key_value)
    return tail if isinstance(tail, dict) else {}


def observer_tail_event_roles(tail: dict[str, Any]) -> list[str]:
    return str_list(tail.get("event_roles"), allowed=REQUIRED_OBSERVER_EVENT_ROLES)


def observer_tail_last_event_times(tail: dict[str, Any]) -> dict[str, str]:
    times = sanitized_role_event_times(tail.get("last_event_times"))
    tail_time = event_time_from_mapping(tail)
    if tail_time is not None:
        for role in observer_tail_event_roles(tail):
            times[role] = tail_time
    return times


def csv_text_tokens(value: Any) -> list[str]:
    if not isinstance(value, str) or not value or value == "none":
        return []
    return [item for item in value.split(",") if item]


def monitor_session_target_keys(metadata: dict[str, Any]) -> list[str]:
    session = metadata.get("session")
    if not isinstance(session, dict):
        return []
    return [
        token
        for token in csv_text_tokens(session.get("targets"))
        if is_exact_target_key(token)
    ]


def exact_monitor_target_keys(metadata: dict[str, Any]) -> list[str]:
    keys: set[str] = set(monitor_session_target_keys(metadata))
    for field in (
        "query_state_by_target",
        "observer_tail_by_target",
        "linger_by_target",
    ):
        values = metadata.get(field)
        if not isinstance(values, dict):
            continue
        keys.update(key for key in values if is_exact_target_key(key))
    snapshot_events = metadata.get("snapshot_events")
    if isinstance(snapshot_events, list):
        for event in snapshot_events:
            if not isinstance(event, dict):
                continue
            keys.update(
                key
                for key in event.get("detected_target_keys", [])
                if is_exact_target_key(key)
            )
    return sorted(keys)


def monitor_query_states_by_target(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    query_state_by_target = metadata.get("query_state_by_target")
    if not isinstance(query_state_by_target, dict):
        query_state_by_target = {}
    query_states: dict[str, dict[str, Any]] = {}
    for key in exact_monitor_target_keys(metadata):
        query_states[key] = sanitized_query_state(
            query_state_by_target.get(key),
            target_metadata_from_key(key),
        )
    return query_states


def monitor_tail_by_target(metadata: dict[str, Any], target_key_value: str) -> dict[str, Any]:
    tails = metadata.get("observer_tail_by_target")
    if not isinstance(tails, dict):
        return {}
    tail = tails.get(target_key_value)
    return tail if isinstance(tail, dict) else {}


def monitor_counts_for_target(metadata: dict[str, Any], target_key_value: str) -> dict[str, int]:
    tail = monitor_tail_by_target(metadata, target_key_value)
    return {
        "accepted": int_count(tail.get("accepted_observer_event_triplet_candidate_lines")),
        "rejected": int_count(tail.get("rejected_observer_event_line_count")),
        "diagnostic_candidates": int_count(tail.get("diagnostic_only_lines")),
    }


def observer_event_triage_from_monitor_tail(
    tail: dict[str, Any],
    counts: dict[str, int],
) -> dict[str, Any]:
    roles = observer_tail_event_roles(tail)
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in roles]
    complete_triplet = bool(roles) and not missing_roles
    diagnostic_count = counts["diagnostic_candidates"]
    accepted_count = max(counts["accepted"], len(roles))
    return {
        "schema": EVENT_TRIAGE_SCHEMA,
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "rejected_observer_event_line_count": counts["rejected"],
        "diagnostic_only_line_count": diagnostic_count,
        "contains_accepted_observer_event_triplet_candidates": bool(roles)
        or accepted_count > 0,
        "contains_diagnostic_only_lines": diagnostic_count > 0,
        "accepted_observer_event_roles": roles,
        "roles_seen": roles,
        "missing_observer_event_triplet_roles": missing_roles,
        "missing_roles": missing_roles,
        "complete_observer_event_triplet_candidate_present": complete_triplet,
        "complete_triplet_candidate": complete_triplet,
        "last_event_times": observer_tail_last_event_times(tail),
        "classification": observer_event_triage_classification(
            accepted_count=accepted_count,
            rejected_count=counts["rejected"],
            diagnostic_count=diagnostic_count,
            complete_triplet=complete_triplet,
        ),
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


def monitor_diagnostics_for_target(
    metadata: dict[str, Any],
    target_key_value: str,
) -> dict[str, Any]:
    tail = monitor_tail_by_target(metadata, target_key_value)
    counts = monitor_counts_for_target(metadata, target_key_value)
    triage = observer_event_triage_from_monitor_tail(tail, counts)
    log_limit = int_or_none(tail.get("limit"))
    return {
        "candidate_count": counts["diagnostic_candidates"],
        "max_sequence": None,
        "log_limits": [log_limit] if log_limit is not None else [],
        "log_budget_reached": False,
        "only_non_evidence": (
            counts["accepted"] == 0
            and counts["rejected"] == 0
            and counts["diagnostic_candidates"] > 0
        ),
        "latest_observer_line": None,
        "classification": triage["classification"],
        "observer_event_triage": triage,
        "accepted_observer_event_triplet_candidate_count": triage[
            "accepted_observer_event_triplet_candidate_count"
        ],
        "complete_observer_event_triplet_candidate_present": triage[
            "complete_observer_event_triplet_candidate_present"
        ],
        "observer_event_roles_seen": triage["roles_seen"],
        "observer_event_missing_roles": triage["missing_roles"],
        "observer_event_last_event_times": triage["last_event_times"],
        "event_triplet_classification": triage["classification"],
        "rejected_drift_count": 0,
        "rejected_drift_target_counts": {},
        "latest_rejected_drift_by_lifecycle_target": {},
        "contains_rejected_drift": False,
        "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
    }


def monitor_targets_and_diagnostics(
    metadata: dict[str, Any],
) -> tuple[dict[str, dict[str, int]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    targets: dict[str, dict[str, int]] = {}
    diagnostics: dict[str, dict[str, Any]] = {}
    query_states = monitor_query_states_by_target(metadata)
    for key in exact_monitor_target_keys(metadata):
        targets[key] = monitor_counts_for_target(metadata, key)
        diagnostics[key] = monitor_diagnostics_for_target(metadata, key)
        query_states.setdefault(key, sanitized_query_state(None, target_metadata_from_key(key)))
    return targets, diagnostics, query_states


def passive_detection_targets_from_monitor(
    targets: dict[str, dict[str, int]],
    query_states: dict[str, dict[str, Any]],
) -> list[str]:
    detected: set[str] = set()
    for key, counts in targets.items():
        if counts.get("accepted", 0) > 0 or counts.get("diagnostic_candidates", 0) > 0:
            detected.add(key)
    detected.update(
        key for key, state in query_states.items() if query_presence_detected(state)
    )
    return sorted(detected)


def extended_monitor_triage(
    *,
    snapshot_root: Path,
    snapshot_count: int,
    monitor_path: Path,
    monitor: dict[str, Any],
    targets: dict[str, dict[str, int]],
    diagnostics: dict[str, dict[str, Any]],
    query_states: dict[str, dict[str, Any]],
    server_activity_summary: dict[str, Any],
) -> dict[str, Any]:
    metadata = monitor.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    observer_tail_by_target = metadata.get("observer_tail_by_target")
    if not isinstance(observer_tail_by_target, dict):
        observer_tail_by_target = {}
    observer_enabled_targets = sorted(
        key
        for key, tail in observer_tail_by_target.items()
        if is_exact_target_key(key)
        and isinstance(tail, dict)
        and int_count(tail.get("observer_gate_lines")) > 0
    )
    passive_detection_targets = passive_detection_targets_from_monitor(targets, query_states)
    complete_triplet_targets = str_list(
        server_activity_summary.get("targets_with_complete_player_principal_triplet_candidate")
    )
    if snapshot_count == 0 and not passive_detection_targets and not complete_triplet_targets:
        classification = "no_snapshots_no_passive_detections_no_complete_triplets_non_evidence"
    elif complete_triplet_targets:
        classification = "complete_triplet_candidates_non_evidence"
    elif passive_detection_targets:
        classification = "passive_detections_without_complete_triplets_non_evidence"
    else:
        classification = "snapshots_present_without_passive_detections_non_evidence"
    return {
        "schema": EXTENDED_MONITOR_TRIAGE_SCHEMA,
        "snapshot_root": str(snapshot_root),
        "snapshot_count": snapshot_count,
        "snapshot_status": "snapshots_found" if snapshot_count else "no_snapshots_found",
        "monitor_log": str(monitor_path),
        "monitor_status": monitor.get("copy_status", "metadata_only"),
        "latest_tick_utc": metadata.get("latest_tick_utc")
        if isinstance(metadata.get("latest_tick_utc"), str)
        else None,
        "monitor_line_count": int_or_none(metadata.get("line_count")),
        "observer_enabled_targets": observer_enabled_targets,
        "observer_enabled_target_count": len(observer_enabled_targets),
        "passive_detection_targets": passive_detection_targets,
        "passive_detection_target_count": len(passive_detection_targets),
        "targets_with_players_detected": str_list(
            server_activity_summary.get("targets_with_players_detected")
        ),
        "players_current_by_target": server_activity_summary.get("players_current_by_target")
        if isinstance(server_activity_summary.get("players_current_by_target"), dict)
        else {},
        "observer_event_classification_by_target": {
            key: diagnostic.get("observer_event_triage", {}).get("classification")
            for key, diagnostic in sorted(diagnostics.items())
            if isinstance(diagnostic.get("observer_event_triage"), dict)
        },
        "complete_observer_event_triplet_targets": complete_triplet_targets,
        "complete_observer_event_triplet_target_count": len(complete_triplet_targets),
        "snapshot_events": metadata.get("snapshot_events")
        if isinstance(metadata.get("snapshot_events"), list)
        else [],
        "classification": classification,
        "evidence_classification": "passive_monitor_metadata_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "process_control": "none",
    }


def player_principal_triplet_candidate_summary(
    *,
    target_key_value: str,
    metadata: dict[str, str],
    diagnostics: dict[str, Any],
    observer_tail: dict[str, Any],
) -> dict[str, Any]:
    triage = diagnostics.get("observer_event_triage")
    if not isinstance(triage, dict):
        triage = {}
    roles_seen = merge_observer_event_roles(
        triage.get("roles_seen"),
        triage.get("accepted_observer_event_roles"),
        diagnostics.get("observer_event_roles_seen"),
        observer_tail_event_roles(observer_tail),
    )
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in roles_seen]
    last_event_times = sanitized_role_event_times(triage.get("last_event_times"))
    last_event_times.update(
        sanitized_role_event_times(diagnostics.get("observer_event_last_event_times"))
    )
    last_event_times.update(observer_tail_last_event_times(observer_tail))
    complete_triplet = bool(roles_seen) and not missing_roles
    accepted_count = max(
        int_count(triage.get("accepted_observer_event_triplet_candidate_count")),
        int_count(observer_tail.get("accepted_observer_event_triplet_candidate_lines")),
        len(roles_seen),
    )
    return {
        "schema": TARGET_TRIPLET_SCHEMA,
        "target_key": target_key_value,
        "target_key_kind": "exact" if is_exact_target_key(target_key_value) else "alias",
        "instance": metadata["instance"],
        "map": metadata["map"],
        "query_port": metadata["query_port"],
        "roles_seen": roles_seen,
        "missing_roles": missing_roles,
        "complete_triplet_candidate": complete_triplet,
        "last_event_times": {
            role: last_event_times[role]
            for role in REQUIRED_OBSERVER_EVENT_ROLES
            if role in last_event_times and role in roles_seen
        },
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "contains_accepted_observer_event_triplet_candidates": bool(roles_seen),
        "classification": observer_event_triage_classification(
            accepted_count=accepted_count,
            rejected_count=int_count(triage.get("rejected_observer_event_line_count")),
            diagnostic_count=int_count(triage.get("diagnostic_only_line_count")),
            complete_triplet=complete_triplet,
        ),
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "process_control": "none",
    }


def passive_server_activity_summary(
    targets: dict[str, dict[str, int]],
    diagnostics: dict[str, dict[str, Any]],
    query_states: dict[str, dict[str, Any]],
    wait_metadata: dict[str, Any] | None = None,
    *,
    summary_scope: str = "offline_passive_snapshot_metadata_only",
) -> dict[str, Any]:
    active_targets: list[str] = []
    players_detected_targets: list[str] = []
    players_current_by_target: dict[str, int | None] = {}
    target_summaries: dict[str, dict[str, Any]] = {}
    triplet_candidates_by_target: dict[str, dict[str, Any]] = {}
    latest_drift_by_target: dict[str, dict[str, Any]] = {}
    latest_drift_by_lifecycle_target: dict[str, dict[str, Any]] = {
        target: {} for target in REJECTED_DRIFT_TARGETS
    }
    exact_target_count = 0

    for key in sorted(targets):
        metadata = target_metadata_from_key(key)
        query_state = query_states.get(key, sanitized_query_state(None, metadata))
        query_presence_eligible = query_state.get("target_key_kind") == "exact"
        if query_presence_eligible:
            exact_target_count += 1
        status = query_status_token(query_state.get("status"))
        server_active = query_presence_eligible and status == "ok"
        players_current = int_or_none(query_state.get("players_current"))
        players_detected = query_presence_eligible and query_presence_detected(query_state)
        if server_active:
            active_targets.append(key)
        if players_detected:
            players_detected_targets.append(key)
        players_current_by_target[key] = players_current

        raw_drift_by_lifecycle_target = sanitized_rejected_drift_by_lifecycle_target(
            diagnostics.get(key, {}).get("latest_rejected_drift_by_lifecycle_target")
        )
        drift_reason_by_lifecycle_target: dict[str, Any] = {}
        for lifecycle_target in REJECTED_DRIFT_TARGETS:
            reason = sanitized_drift_reason_for_summary(
                raw_drift_by_lifecycle_target.get(lifecycle_target)
            )
            if reason is None:
                continue
            drift_reason_by_lifecycle_target[lifecycle_target] = reason
            latest_drift_by_lifecycle_target[lifecycle_target][key] = reason
        if drift_reason_by_lifecycle_target:
            latest_drift_by_target[key] = drift_reason_by_lifecycle_target

        triplet_candidate = player_principal_triplet_candidate_summary(
            target_key_value=key,
            metadata=metadata,
            diagnostics=diagnostics.get(key, {}),
            observer_tail=observer_tail_for_target(wait_metadata, key),
        )
        if is_exact_target_key(key):
            triplet_candidates_by_target[key] = triplet_candidate

        target_summaries[key] = {
            "target_key": key,
            "instance": metadata["instance"],
            "map": metadata["map"],
            "query_port": metadata["query_port"],
            "query_status": status,
            "query_presence_eligible": query_presence_eligible,
            "server_active": server_active,
            "players_detected": players_detected,
            "players_current": players_current,
            "player_principal_triplet_candidate": triplet_candidate,
            "latest_rejected_drift_reason_by_lifecycle_target": drift_reason_by_lifecycle_target,
            "evidence_classification": "passive_server_activity_summary_non_evidence",
            "approved_runtime_evidence": False,
            "ready": False,
            "route_ready": False,
            "readiness_gate": "none",
            "process_control": "none",
        }

    active_targets = sorted(active_targets)
    players_detected_targets = sorted(players_detected_targets)
    latest_drift_by_lifecycle_target = {
        target: values
        for target, values in latest_drift_by_lifecycle_target.items()
        if values
    }
    return {
        "schema": "obelisk.player-principal-passive-server-activity-summary.v1",
        "summary_scope": summary_scope,
        "target_count": len(targets),
        "exact_query_target_count": exact_target_count,
        "active_target_count": len(active_targets),
        "active_targets": active_targets,
        "all_expected_servers_active": (
            exact_target_count > 0 and len(active_targets) == exact_target_count
        ),
        "both_servers_active": exact_target_count == 2 and len(active_targets) == 2,
        "players_detected": bool(players_detected_targets),
        "players_detected_target_count": len(players_detected_targets),
        "targets_with_players_detected": players_detected_targets,
        "players_current_by_target": players_current_by_target,
        "players_current_known_total": sum(
            value for value in players_current_by_target.values() if isinstance(value, int)
        ),
        "player_detection_scope": "aggregate_player_count_only",
        "player_principal_triplet_candidates_by_target": triplet_candidates_by_target,
        "targets_with_complete_player_principal_triplet_candidate": sorted(
            key
            for key, summary in triplet_candidates_by_target.items()
            if summary.get("complete_triplet_candidate") is True
        ),
        "latest_rejected_drift_reason_by_snapshot_target": latest_drift_by_target,
        "latest_rejected_drift_reason_by_lifecycle_target": latest_drift_by_lifecycle_target,
        "targets": target_summaries,
        "evidence_classification": "passive_server_activity_summary_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "process_control": "none",
    }


def total_diagnostics(targets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    max_sequences = [
        diagnostic["max_sequence"]
        for diagnostic in targets.values()
        if isinstance(diagnostic.get("max_sequence"), int)
    ]
    observer_event_triages = [
        diagnostic.get("observer_event_triage")
        for diagnostic in targets.values()
        if isinstance(diagnostic.get("observer_event_triage"), dict)
    ]
    latest_rejected_drift_by_snapshot_target = {
        target: latest_rejected_drift
        for target, diagnostic in sorted(targets.items())
        if (
            latest_rejected_drift := sanitized_rejected_drift_by_lifecycle_target(
                diagnostic.get("latest_rejected_drift_by_lifecycle_target")
            )
        )
    }
    accepted_count = sum(
        int_count(triage.get("accepted_observer_event_triplet_candidate_count"))
        for triage in observer_event_triages
    )
    rejected_count = sum(
        int_count(triage.get("rejected_observer_event_line_count"))
        for triage in observer_event_triages
    )
    diagnostic_count = sum(
        int_count(triage.get("diagnostic_only_line_count"))
        for triage in observer_event_triages
    )
    accepted_roles = sorted(
        {
            role
            for triage in observer_event_triages
            for role in triage.get("accepted_observer_event_roles", [])
            if isinstance(role, str) and role in REQUIRED_OBSERVER_EVENT_ROLES
        },
        key=REQUIRED_OBSERVER_EVENT_ROLES.index,
    )
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in accepted_roles]
    complete_triplet = accepted_count > 0 and not missing_roles
    observer_event_triage = {
        "schema": EVENT_TRIAGE_SCHEMA,
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "rejected_observer_event_line_count": rejected_count,
        "diagnostic_only_line_count": diagnostic_count,
        "contains_accepted_observer_event_triplet_candidates": accepted_count > 0,
        "contains_diagnostic_only_lines": diagnostic_count > 0,
        "accepted_observer_event_roles": accepted_roles,
        "missing_observer_event_triplet_roles": missing_roles,
        "complete_observer_event_triplet_candidate_present": complete_triplet,
        "targets_with_accepted_observer_event_triplet_candidates": sorted(
            target
            for target, diagnostic in targets.items()
            if isinstance((triage := diagnostic.get("observer_event_triage")), dict)
            and triage.get("contains_accepted_observer_event_triplet_candidates") is True
        ),
        "targets_with_complete_observer_event_triplet_candidate": sorted(
            target
            for target, diagnostic in targets.items()
            if isinstance((triage := diagnostic.get("observer_event_triage")), dict)
            and triage.get("complete_observer_event_triplet_candidate_present") is True
        ),
        "targets_with_diagnostic_only_lines": sorted(
            target
            for target, diagnostic in targets.items()
            if isinstance((triage := diagnostic.get("observer_event_triage")), dict)
            and triage.get("contains_diagnostic_only_lines") is True
        ),
        "classification": observer_event_triage_classification(
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            diagnostic_count=diagnostic_count,
            complete_triplet=complete_triplet,
        ),
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }
    return {
        "candidate_count": sum(
            diagnostic.get("candidate_count", 0)
            for diagnostic in targets.values()
            if isinstance(diagnostic.get("candidate_count"), int)
        ),
        "max_sequence": max(max_sequences) if max_sequences else None,
        "log_limits": sorted(
            {
                limit
                for diagnostic in targets.values()
                for limit in diagnostic.get("log_limits", [])
                if isinstance(limit, int)
            }
        ),
        "log_budget_reached": any(
            diagnostic.get("log_budget_reached") is True for diagnostic in targets.values()
        ),
        "diagnostic_only_non_evidence_targets": sorted(
            target
            for target, diagnostic in targets.items()
            if diagnostic.get("only_non_evidence") is True
        ),
        "latest_observer_lines_by_target": {
            target: diagnostic["latest_observer_line"]
            for target, diagnostic in sorted(targets.items())
            if diagnostic.get("latest_observer_line") is not None
        },
        "rejected_drift_count": sum(
            int_count(diagnostic.get("rejected_drift_count"))
            for diagnostic in targets.values()
        ),
        "rejected_drift_targets": sorted(latest_rejected_drift_by_snapshot_target),
        "latest_rejected_drift_by_snapshot_target": latest_rejected_drift_by_snapshot_target,
        "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "classification": "passive_diagnostics_non_evidence",
        "observer_event_triage": observer_event_triage,
    }


def classify_delta(delta: dict[str, int]) -> str:
    if delta["accepted"] == 0 and delta["rejected"] == 0:
        if delta["diagnostic_candidates"] > 0:
            return "diagnostic_only_non_evidence"
        if delta["diagnostic_candidates"] == 0:
            return "unchanged_non_evidence"
        return "diagnostic_count_decreased_non_evidence"
    if delta["accepted"] != 0:
        return "accepted_observer_event_triplet_candidate_delta_non_evidence_unapproved"
    if delta["rejected"] != 0:
        return "rejected_observer_event_delta_non_evidence_unapproved"
    return "observer_count_delta_non_evidence_unapproved"


def passive_activity_triage(target_deltas: list[dict[str, Any]]) -> dict[str, Any]:
    active_targets: list[str] = []
    new_presence_targets: list[str] = []
    new_diagnostic_targets: list[str] = []
    sequence_advanced_targets: list[str] = []
    active_with_new_diagnostics: list[str] = []
    candidate_accepted_event_targets: list[str] = []
    candidate_complete_triplet_targets: list[str] = []
    active_with_accepted_events: list[str] = []
    candidate_rejected_drift_targets: list[str] = []
    active_with_rejected_drift: list[str] = []
    new_accepted_event_targets: list[str] = []
    new_diagnostic_counts: dict[str, int] = {}
    accepted_event_deltas: dict[str, int] = {}
    candidate_accepted_event_counts: dict[str, int] = {}
    candidate_rejected_drift_counts: dict[str, int] = {}
    max_sequence_deltas: dict[str, int | None] = {}
    active_players: dict[str, int | None] = {}
    latest_observer_lines: dict[str, dict[str, Any]] = {}
    latest_rejected_drift: dict[str, dict[str, Any]] = {}

    for target_delta in target_deltas:
        target = str(target_delta.get("target") or "unknown")
        delta = target_delta.get("delta")
        if not isinstance(delta, dict):
            delta = {}
        diagnostics = target_delta.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}
        query_state = target_delta.get("query_state")
        if not isinstance(query_state, dict):
            query_state = {}
        base_query_state = query_state.get("base")
        candidate_query_state = query_state.get("candidate")
        if not isinstance(base_query_state, dict):
            base_query_state = sanitized_query_state(None)
        if not isinstance(candidate_query_state, dict):
            candidate_query_state = sanitized_query_state(None)

        base_presence = query_presence_detected(base_query_state)
        candidate_presence = query_presence_detected(candidate_query_state)
        diagnostic_delta = int_count(delta.get("diagnostic_candidates"))
        accepted_delta = int_count(delta.get("accepted"))
        max_sequence_delta = diagnostics.get("max_sequence_delta")
        candidate_observer_event_triage = diagnostics.get("candidate_observer_event_triage")
        if not isinstance(candidate_observer_event_triage, dict):
            candidate_observer_event_triage = {}
        candidate_rejected_drift = sanitized_rejected_drift_by_lifecycle_target(
            diagnostics.get("candidate_latest_rejected_drift_by_lifecycle_target")
        )
        candidate_rejected_drift_count = int_count(
            diagnostics.get("candidate_rejected_drift_count")
        )
        sequence_advanced = diagnostic_sequence_advanced(
            int_or_none(diagnostics.get("base_max_sequence")),
            int_or_none(diagnostics.get("candidate_max_sequence")),
        )

        if candidate_presence:
            active_targets.append(target)
            active_players[target] = int_or_none(candidate_query_state.get("players_current"))
        if candidate_presence and not base_presence:
            new_presence_targets.append(target)
        if diagnostic_delta > 0:
            new_diagnostic_targets.append(target)
            new_diagnostic_counts[target] = diagnostic_delta
            max_sequence_deltas[target] = (
                max_sequence_delta if isinstance(max_sequence_delta, int) else None
            )
            latest_observer_line = diagnostics.get("candidate_latest_observer_line")
            if isinstance(latest_observer_line, dict):
                latest_observer_lines[target] = latest_observer_line
        if sequence_advanced:
            sequence_advanced_targets.append(target)
        if candidate_presence and diagnostic_delta > 0:
            active_with_new_diagnostics.append(target)
        if candidate_observer_event_triage.get(
            "contains_accepted_observer_event_triplet_candidates"
        ) is True:
            candidate_accepted_event_targets.append(target)
            candidate_accepted_event_counts[target] = int_count(
                candidate_observer_event_triage.get(
                    "accepted_observer_event_triplet_candidate_count"
                )
            )
        if candidate_observer_event_triage.get(
            "complete_observer_event_triplet_candidate_present"
        ) is True:
            candidate_complete_triplet_targets.append(target)
        if accepted_delta != 0:
            new_accepted_event_targets.append(target)
            accepted_event_deltas[target] = accepted_delta
        if candidate_presence and candidate_observer_event_triage.get(
            "contains_accepted_observer_event_triplet_candidates"
        ) is True:
            active_with_accepted_events.append(target)
        if candidate_rejected_drift or candidate_rejected_drift_count > 0:
            candidate_rejected_drift_targets.append(target)
            candidate_rejected_drift_counts[target] = candidate_rejected_drift_count
            if candidate_rejected_drift:
                latest_rejected_drift[target] = candidate_rejected_drift
        if candidate_presence and (candidate_rejected_drift or candidate_rejected_drift_count > 0):
            active_with_rejected_drift.append(target)

    return {
        "schema": "obelisk.player-principal-passive-activity-triage.v1",
        "query_state_key": "target_key",
        "active_targets": active_targets,
        "new_presence_detected_targets": new_presence_targets,
        "new_diagnostic_candidate_targets": new_diagnostic_targets,
        "candidate_targets_with_accepted_observer_event_triplet_candidates": candidate_accepted_event_targets,
        "candidate_targets_with_complete_observer_event_triplet_candidate": candidate_complete_triplet_targets,
        "candidate_targets_with_rejected_drift": candidate_rejected_drift_targets,
        "max_sequence_advanced_targets": sequence_advanced_targets,
        "targets_with_presence_and_new_diagnostics": active_with_new_diagnostics,
        "targets_with_presence_and_accepted_observer_event_triplet_candidates": active_with_accepted_events,
        "targets_with_presence_and_rejected_drift": active_with_rejected_drift,
        "new_diagnostic_candidates_by_target": new_diagnostic_counts,
        "new_accepted_observer_event_triplet_candidates_by_target": accepted_event_deltas,
        "candidate_accepted_observer_event_triplet_candidates_by_target": candidate_accepted_event_counts,
        "candidate_rejected_drift_count_by_target": candidate_rejected_drift_counts,
        "max_sequence_delta_by_target": max_sequence_deltas,
        "candidate_players_current_by_target": active_players,
        "candidate_latest_observer_lines_by_new_diagnostic_target": latest_observer_lines,
        "candidate_latest_rejected_drift_by_target": latest_rejected_drift,
        "classification": "passive_activity_triage_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


def lifecycle_targets_from_rejected_drift_by_target(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return []
    lifecycle_targets: set[str] = set()
    for drift_by_lifecycle_target in value.values():
        if not isinstance(drift_by_lifecycle_target, dict):
            continue
        for lifecycle_target in REJECTED_DRIFT_TARGETS:
            if lifecycle_target in drift_by_lifecycle_target:
                lifecycle_targets.add(lifecycle_target)
    return sorted(lifecycle_targets)


def passive_runner_priority_rank(priority: str) -> int:
    return {
        "accepted_observer_event_triplet_candidate": 10,
        "rejected_lifecycle_property_FName_drift": 20,
        "new_diagnostics_only": 30,
        "repeated_diagnostics_only": 40,
        "no_passive_observer_activity": 90,
    }.get(priority, 80)


def passive_runner_action_hints(
    *,
    priority: str,
    reason_kind: str,
    targets: list[str],
    lifecycle_targets: list[str],
    accepted_observer_event_targets: list[str],
    complete_observer_event_targets: list[str],
    rejected_drift_targets: list[str],
    diagnostic_only_targets: list[str],
) -> list[dict[str, Any]]:
    target_list = sorted(dict.fromkeys(targets))
    accepted_list = sorted(dict.fromkeys(accepted_observer_event_targets))
    complete_list = sorted(dict.fromkeys(complete_observer_event_targets))
    rejected_list = sorted(dict.fromkeys(rejected_drift_targets))
    diagnostic_list = sorted(dict.fromkeys(diagnostic_only_targets))
    lifecycle_list = sorted(dict.fromkeys(lifecycle_targets))
    if priority == "accepted_observer_event_triplet_candidate":
        hint_id = (
            "prepare_fresh_operator_approved_evidence_request_from_triplet_candidate"
            if complete_list
            else "carry_partial_triplet_candidate_to_next_passive_review"
        )
        focus = (
            "complete_triplet_candidate_request_preflight"
            if complete_list
            else "partial_triplet_candidate_role_gap"
        )
        input_fields = [
            "targets",
            "accepted_observer_event_targets",
            "complete_observer_event_targets",
            "details.accepted_observer_event_roles",
            "details.missing_observer_event_triplet_roles",
        ]
    elif priority == "rejected_lifecycle_property_FName_drift":
        hint_id = "carry_rejected_fname_drift_to_offline_reflection_review"
        focus = "rejected_lifecycle_property_fname_drift"
        input_fields = [
            "targets",
            "lifecycle_targets",
            "rejected_drift_targets",
            "details.candidate_rejected_drift_count",
            "details.rejected_drift_count",
        ]
    elif priority in {"new_diagnostics_only", "repeated_diagnostics_only"}:
        hint_id = "compare_passive_diagnostic_counts_before_request"
        focus = "diagnostic_candidate_count_tracking"
        input_fields = [
            "targets",
            "diagnostic_only_targets",
            "details.new_diagnostic_candidates_by_target",
            "details.candidate_diagnostic_candidate_count",
            "details.candidate_count",
        ]
    else:
        hint_id = "wait_for_passive_observer_activity_metadata"
        focus = "no_passive_observer_activity"
        input_fields = ["details.candidate_count", "details.global_delta"]
    return [
        {
            "schema": RUNNER_ACTION_HINT_SCHEMA,
            "order": 1,
            "id": hint_id,
            "focus": focus,
            "reason_kind": reason_kind,
            "target_keys": target_list,
            "lifecycle_targets": lifecycle_list,
            "accepted_observer_event_targets": accepted_list,
            "complete_observer_event_targets": complete_list,
            "rejected_drift_targets": rejected_list,
            "diagnostic_only_targets": diagnostic_list,
            "input_fields": input_fields,
            "allowed_scope": "offline_triage_or_fresh_operator_approved_evidence_request_only",
            "non_authorization": "passive_actionability_hint_does_not_authorize_server_or_runtime_work",
            "process_control": "none",
            "approved_runtime_evidence": False,
            "ready": False,
            "route_ready": False,
            "readiness_gate": "none",
            "evidence_classification": "passive_actionability_non_evidence",
        }
    ]


def passive_actionability_payload(
    *,
    summary_scope: str,
    priority: str,
    reason_kind: str,
    next_reason: str,
    classification_context: str,
    targets: list[str] | None = None,
    targets_with_players_detected: list[str] | None = None,
    lifecycle_targets: list[str] | None = None,
    accepted_observer_event_targets: list[str] | None = None,
    complete_observer_event_targets: list[str] | None = None,
    rejected_drift_targets: list[str] | None = None,
    diagnostic_only_targets: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_targets = sorted(dict.fromkeys(targets or []))
    normalized_players = sorted(dict.fromkeys(targets_with_players_detected or []))
    normalized_lifecycle_targets = sorted(dict.fromkeys(lifecycle_targets or []))
    normalized_accepted_targets = sorted(
        dict.fromkeys(accepted_observer_event_targets or [])
    )
    normalized_complete_targets = sorted(
        dict.fromkeys(complete_observer_event_targets or [])
    )
    normalized_rejected_targets = sorted(dict.fromkeys(rejected_drift_targets or []))
    normalized_diagnostic_targets = sorted(dict.fromkeys(diagnostic_only_targets or []))
    runner_hints = passive_runner_action_hints(
        priority=priority,
        reason_kind=reason_kind,
        targets=normalized_targets,
        lifecycle_targets=normalized_lifecycle_targets,
        accepted_observer_event_targets=normalized_accepted_targets,
        complete_observer_event_targets=normalized_complete_targets,
        rejected_drift_targets=normalized_rejected_targets,
        diagnostic_only_targets=normalized_diagnostic_targets,
    )
    return {
        "schema": ACTIONABILITY_SCHEMA,
        "summary_scope": summary_scope,
        "priority": priority,
        "runner_priority_rank": passive_runner_priority_rank(priority),
        "runner_focus": runner_hints[0]["focus"],
        "reason_kind": reason_kind,
        "next_reason": next_reason,
        "classification_context": classification_context,
        "targets": normalized_targets,
        "targets_with_players_detected": normalized_players,
        "lifecycle_targets": normalized_lifecycle_targets,
        "accepted_observer_event_targets": normalized_accepted_targets,
        "complete_observer_event_targets": normalized_complete_targets,
        "rejected_drift_targets": normalized_rejected_targets,
        "diagnostic_only_targets": normalized_diagnostic_targets,
        "runner_action_hints": runner_hints,
        "details": details or {},
        "allowed_followup_scope": "offline_triage_or_fresh_operator_approved_evidence_request_only",
        "forbidden_followup_scope": "no_process_control_no_linuxgsm_monitor_details_no_evidence_claims",
        "process_control": "none",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_actionability_non_evidence",
        "classification": "passive_actionability_non_evidence",
    }


def passive_closure_classification(
    *,
    zero_player_targets: list[str],
    gate_only_targets: list[str],
    diagnostic_only_targets: list[str],
    partial_role_targets: list[str],
    complete_triplet_targets: list[str],
) -> str:
    if zero_player_targets and gate_only_targets:
        return "zero_players_gate_only_no_progress_no_readiness_non_evidence"
    if diagnostic_only_targets:
        return "diagnostic_only_observer_lines_no_progress_no_readiness_non_evidence"
    if partial_role_targets:
        return "partial_observer_event_roles_no_progress_no_readiness_non_evidence"
    if complete_triplet_targets:
        return "unapproved_triplet_candidate_no_progress_no_readiness_non_evidence"
    if zero_player_targets:
        return "zero_players_no_progress_no_readiness_non_evidence"
    return "passive_monitor_or_snapshot_no_progress_no_readiness_non_evidence"


def passive_closure_summary(
    *,
    source_root: Path,
    summary_scope: str,
    source_root_role: str,
    snapshot_count: int,
    diagnostics: dict[str, Any],
    server_activity_summary: dict[str, Any],
    wait_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    observer_triage = diagnostics.get("observer_event_triage")
    if not isinstance(observer_triage, dict):
        observer_triage = {}
    players_current_by_target = server_activity_summary.get("players_current_by_target")
    if not isinstance(players_current_by_target, dict):
        players_current_by_target = {}
    zero_player_targets = sorted(
        key
        for key, value in players_current_by_target.items()
        if isinstance(key, str) and int_or_none(value) == 0
    )
    unknown_player_count_targets = sorted(
        key
        for key, value in players_current_by_target.items()
        if isinstance(key, str) and int_or_none(value) is None
    )
    players_detected_targets = str_list(
        server_activity_summary.get("targets_with_players_detected")
    )
    diagnostic_only_targets = str_list(
        diagnostics.get("diagnostic_only_non_evidence_targets")
    )
    complete_triplet_targets = str_list(
        server_activity_summary.get("targets_with_complete_player_principal_triplet_candidate")
    )
    triplet_candidates = server_activity_summary.get(
        "player_principal_triplet_candidates_by_target"
    )
    if not isinstance(triplet_candidates, dict):
        triplet_candidates = {}
    partial_role_targets = sorted(
        key
        for key, triplet in triplet_candidates.items()
        if isinstance(key, str)
        and isinstance(triplet, dict)
        and bool(str_list(triplet.get("roles_seen"), allowed=REQUIRED_OBSERVER_EVENT_ROLES))
        and triplet.get("complete_triplet_candidate") is not True
    )
    missing_roles_by_target = {
        key: str_list(triplet.get("missing_roles"), allowed=REQUIRED_OBSERVER_EVENT_ROLES)
        for key, triplet in sorted(triplet_candidates.items())
        if isinstance(key, str)
        and isinstance(triplet, dict)
        and key in partial_role_targets
    }

    observer_tail_by_target = (
        wait_metadata.get("observer_tail_by_target") if isinstance(wait_metadata, dict) else {}
    )
    if not isinstance(observer_tail_by_target, dict):
        observer_tail_by_target = {}
    gate_only_targets = sorted(
        key
        for key, tail in observer_tail_by_target.items()
        if isinstance(key, str)
        and isinstance(tail, dict)
        and int_count(tail.get("observer_gate_lines")) > 0
        and int_count(tail.get("raw_observer_event_lines")) == 0
        and int_count(tail.get("accepted_observer_event_triplet_candidate_lines")) == 0
        and int_count(tail.get("rejected_observer_event_line_count")) == 0
        and int_count(tail.get("diagnostic_only_lines")) == 0
    )

    run_id = source_root.name or str(source_root)
    run_id_matches_closure_pattern = CLOSURE_COMPATIBLE_RUN_ID_RE.fullmatch(run_id) is not None
    accepted_count = int_count(
        observer_triage.get("accepted_observer_event_triplet_candidate_count")
    )
    rejected_count = int_count(observer_triage.get("rejected_observer_event_line_count"))
    diagnostic_count = int_count(observer_triage.get("diagnostic_only_line_count"))
    no_observer_activity = accepted_count == 0 and rejected_count == 0 and diagnostic_count == 0
    closure_reasons = []
    if not run_id_matches_closure_pattern:
        closure_reasons.append("invalid_run_id_root_non_evidence")
    else:
        closure_reasons.append("passive_root_not_valid_closure_evidence_non_evidence")
    if zero_player_targets and not players_detected_targets:
        closure_reasons.append("zero_players_non_evidence")
    elif not players_detected_targets:
        closure_reasons.append("no_players_detected_non_evidence")
    if gate_only_targets:
        closure_reasons.append("observer_gate_only_non_evidence")
    if diagnostic_only_targets:
        closure_reasons.append("diagnostic_only_observer_lines_non_evidence")
    if partial_role_targets:
        closure_reasons.append("partial_observer_event_roles_non_evidence")
    if complete_triplet_targets:
        closure_reasons.append("unapproved_observer_event_triplet_candidate_non_evidence")
    if no_observer_activity and not gate_only_targets:
        closure_reasons.append("no_player_principal_observer_activity_non_evidence")
    closure_reasons = sorted(dict.fromkeys(closure_reasons))

    return {
        "schema": PASSIVE_CLOSURE_SUMMARY_SCHEMA,
        "summary_scope": summary_scope,
        "source_root": str(source_root),
        "source_root_role": source_root_role,
        "source_run_id": run_id,
        "required_closure_run_id_pattern": CLOSURE_COMPATIBLE_RUN_ID_PATTERN,
        "run_id_matches_player_principal_lifecycle_closure_pattern": run_id_matches_closure_pattern,
        "invalid_run_id_root": not run_id_matches_closure_pattern,
        "valid_closure_root": False,
        "source_root_valid_for_closure": False,
        "closure_root_valid_for_player_principal_lifecycle": False,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "passive_snapshot_root_accepted_as_closure_evidence_dir": False,
        "passive_root_policy": "operational_context_only_not_evidence",
        "closure_status": "closed_non_evidence_no_progress_no_readiness",
        "closure_classification": passive_closure_classification(
            zero_player_targets=zero_player_targets,
            gate_only_targets=gate_only_targets,
            diagnostic_only_targets=diagnostic_only_targets,
            partial_role_targets=partial_role_targets,
            complete_triplet_targets=complete_triplet_targets,
        ),
        "closure_reasons": closure_reasons,
        "snapshot_count": snapshot_count,
        "players_detected_targets": players_detected_targets,
        "zero_player_targets": zero_player_targets,
        "unknown_player_count_targets": unknown_player_count_targets,
        "observer_gate_only_targets": gate_only_targets,
        "diagnostic_only_targets": diagnostic_only_targets,
        "partial_observer_event_role_targets": partial_role_targets,
        "missing_observer_event_roles_by_target": missing_roles_by_target,
        "complete_triplet_candidate_targets": complete_triplet_targets,
        "observer_event_classification": observer_triage.get("classification"),
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "rejected_observer_event_line_count": rejected_count,
        "diagnostic_only_line_count": diagnostic_count,
        "progress_status": "no_progress",
        "readiness_status": "no_readiness",
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_ready": False,
        "runtime_evidence_ready": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "counts_toward_sdk": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_v1_completion": False,
        "sdk_progress": 0,
        "p0_progress": 0,
        "complete_sdk_progress_contribution": 0,
        "p0_dependency_chain_progress_contribution": 0,
        "evidence_classification": "passive_closure_non_evidence",
        "process_control": "none",
    }


def latest_passive_actionability(summary: dict[str, Any]) -> dict[str, Any]:
    diagnostics = summary.get("diagnostics")
    if not isinstance(diagnostics, dict):
        diagnostics = {}
    observer_triage = diagnostics.get("observer_event_triage")
    if not isinstance(observer_triage, dict):
        observer_triage = {}
    server_activity = summary.get("passive_server_activity_summary")
    if not isinstance(server_activity, dict):
        server_activity = {}
    players_detected_targets = str_list(server_activity.get("targets_with_players_detected"))
    accepted_targets = str_list(
        observer_triage.get("targets_with_accepted_observer_event_triplet_candidates")
    )
    complete_targets = str_list(
        observer_triage.get("targets_with_complete_observer_event_triplet_candidate")
    )
    accepted_count = int_count(
        observer_triage.get("accepted_observer_event_triplet_candidate_count")
    )
    complete_triplet = (
        observer_triage.get("complete_observer_event_triplet_candidate_present") is True
    )
    if complete_targets or complete_triplet:
        targets = complete_targets or accepted_targets
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_metadata_only",
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="complete_accepted_observer_event_triplet_candidate_present",
            next_reason="complete_accepted_observer_event_triplet_candidate_present_non_evidence",
            classification_context=str(summary.get("snapshot_id") or "latest"),
            targets=targets,
            targets_with_players_detected=[
                target for target in targets if target in players_detected_targets
            ],
            accepted_observer_event_targets=accepted_targets,
            complete_observer_event_targets=complete_targets,
            details={
                "accepted_observer_event_triplet_candidate_count": accepted_count,
                "accepted_observer_event_roles": str_list(
                    observer_triage.get("accepted_observer_event_roles"),
                    allowed=REQUIRED_OBSERVER_EVENT_ROLES,
                ),
                "complete_observer_event_triplet_candidate_present": complete_triplet,
            },
        )
    if accepted_targets or accepted_count > 0:
        targets = accepted_targets
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_metadata_only",
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="partial_accepted_observer_event_triplet_candidate_present",
            next_reason="partial_accepted_observer_event_triplet_candidate_present_non_evidence",
            classification_context=str(summary.get("snapshot_id") or "latest"),
            targets=targets,
            targets_with_players_detected=[
                target for target in targets if target in players_detected_targets
            ],
            accepted_observer_event_targets=accepted_targets,
            details={
                "accepted_observer_event_triplet_candidate_count": accepted_count,
                "accepted_observer_event_roles": str_list(
                    observer_triage.get("accepted_observer_event_roles"),
                    allowed=REQUIRED_OBSERVER_EVENT_ROLES,
                ),
                "missing_observer_event_triplet_roles": str_list(
                    observer_triage.get("missing_observer_event_triplet_roles"),
                    allowed=REQUIRED_OBSERVER_EVENT_ROLES,
                ),
            },
        )

    rejected_drift_by_target = diagnostics.get("latest_rejected_drift_by_snapshot_target")
    rejected_drift_targets = str_list(diagnostics.get("rejected_drift_targets")) or str_key_list(
        rejected_drift_by_target
    )
    if rejected_drift_targets:
        active_rejected_targets = [
            target for target in rejected_drift_targets if target in players_detected_targets
        ]
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_metadata_only",
            priority="rejected_lifecycle_property_FName_drift",
            reason_kind="repeated_lifecycle_property_FName_drift",
            next_reason=(
                "repeated_lifecycle_property_FName_drift_with_player_presence_non_evidence"
                if active_rejected_targets
                else "repeated_lifecycle_property_FName_drift_non_evidence"
            ),
            classification_context=str(summary.get("snapshot_id") or "latest"),
            targets=rejected_drift_targets,
            targets_with_players_detected=active_rejected_targets,
            lifecycle_targets=lifecycle_targets_from_rejected_drift_by_target(
                rejected_drift_by_target
            ),
            rejected_drift_targets=rejected_drift_targets,
            details={
                "rejected_drift_count": int_count(diagnostics.get("rejected_drift_count")),
                "candidate_count": int_count(diagnostics.get("candidate_count")),
                "log_budget_reached": diagnostics.get("log_budget_reached") is True,
            },
        )

    diagnostic_only_targets = str_list(
        diagnostics.get("diagnostic_only_non_evidence_targets")
    )
    candidate_count = int_count(diagnostics.get("candidate_count"))
    if diagnostic_only_targets or candidate_count > 0:
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_metadata_only",
            priority="repeated_diagnostics_only",
            reason_kind="repeated_diagnostic_candidates",
            next_reason="repeated_diagnostic_candidates_without_accepted_events_or_rejected_drift_non_evidence",
            classification_context=str(summary.get("snapshot_id") or "latest"),
            targets=diagnostic_only_targets,
            targets_with_players_detected=[
                target for target in diagnostic_only_targets if target in players_detected_targets
            ],
            diagnostic_only_targets=diagnostic_only_targets,
            details={
                "candidate_count": candidate_count,
                "log_budget_reached": diagnostics.get("log_budget_reached") is True,
                "observer_event_classification": observer_triage.get("classification"),
            },
        )

    return passive_actionability_payload(
        summary_scope="latest_passive_snapshot_metadata_only",
        priority="no_passive_observer_activity",
        reason_kind="no_passive_observer_activity",
        next_reason="no_passive_observer_activity_non_evidence",
        classification_context=str(summary.get("snapshot_id") or "latest"),
        details={"candidate_count": candidate_count},
    )


def diff_passive_actionability(
    *,
    classification: str,
    global_delta: dict[str, int],
    candidate_counts: dict[str, int],
    candidate_total_diagnostics: dict[str, Any],
    activity_triage: dict[str, Any],
) -> dict[str, Any]:
    observer_triage = candidate_total_diagnostics.get("observer_event_triage")
    if not isinstance(observer_triage, dict):
        observer_triage = {}
    accepted_delta_by_target = {
        target: delta
        for target, delta in (
            activity_triage.get("new_accepted_observer_event_triplet_candidates_by_target")
            or {}
        ).items()
        if isinstance(target, str) and isinstance(delta, int) and not isinstance(delta, bool)
    }
    accepted_targets = str_list(
        activity_triage.get("candidate_targets_with_accepted_observer_event_triplet_candidates")
    )
    complete_targets = str_list(
        activity_triage.get("candidate_targets_with_complete_observer_event_triplet_candidate")
    )
    active_accepted_targets = str_list(
        activity_triage.get("targets_with_presence_and_accepted_observer_event_triplet_candidates")
    )
    accepted_count = int_count(
        observer_triage.get("accepted_observer_event_triplet_candidate_count")
    )
    complete_triplet = (
        observer_triage.get("complete_observer_event_triplet_candidate_present") is True
    )
    if accepted_delta_by_target:
        targets = sorted(accepted_delta_by_target)
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="new_accepted_observer_event_triplet_candidate_delta",
            next_reason="new_accepted_observer_event_triplet_candidate_delta_non_evidence",
            classification_context=classification,
            targets=targets,
            targets_with_players_detected=[
                target for target in targets if target in active_accepted_targets
            ],
            accepted_observer_event_targets=accepted_targets,
            complete_observer_event_targets=complete_targets,
            details={
                "global_delta": global_delta,
                "accepted_delta_by_target": accepted_delta_by_target,
                "accepted_observer_event_triplet_candidate_count": accepted_count,
                "complete_observer_event_triplet_candidate_present": complete_triplet,
            },
        )
    if complete_targets or complete_triplet:
        targets = complete_targets or accepted_targets
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="repeated_complete_accepted_observer_event_triplet_candidate",
            next_reason="repeated_complete_accepted_observer_event_triplet_candidate_non_evidence",
            classification_context=classification,
            targets=targets,
            targets_with_players_detected=[
                target for target in targets if target in active_accepted_targets
            ],
            accepted_observer_event_targets=accepted_targets,
            complete_observer_event_targets=complete_targets,
            details={
                "global_delta": global_delta,
                "accepted_observer_event_triplet_candidate_count": accepted_count,
                "complete_observer_event_triplet_candidate_present": complete_triplet,
            },
        )
    if accepted_targets or accepted_count > 0:
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="repeated_partial_accepted_observer_event_triplet_candidate",
            next_reason="repeated_partial_accepted_observer_event_triplet_candidate_non_evidence",
            classification_context=classification,
            targets=accepted_targets,
            targets_with_players_detected=[
                target for target in accepted_targets if target in active_accepted_targets
            ],
            accepted_observer_event_targets=accepted_targets,
            details={
                "global_delta": global_delta,
                "accepted_observer_event_triplet_candidate_count": accepted_count,
                "missing_observer_event_triplet_roles": str_list(
                    observer_triage.get("missing_observer_event_triplet_roles"),
                    allowed=REQUIRED_OBSERVER_EVENT_ROLES,
                ),
            },
        )

    rejected_drift_targets = str_list(activity_triage.get("candidate_targets_with_rejected_drift"))
    if rejected_drift_targets:
        latest_rejected_drift = activity_triage.get("candidate_latest_rejected_drift_by_target")
        active_rejected_targets = str_list(
            activity_triage.get("targets_with_presence_and_rejected_drift")
        )
        repeated_unchanged = (
            classification == "unchanged_non_evidence"
            and global_delta.get("accepted") == 0
            and global_delta.get("rejected") == 0
            and global_delta.get("diagnostic_candidates") == 0
        )
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="rejected_lifecycle_property_FName_drift",
            reason_kind=(
                "repeated_lifecycle_property_FName_drift_unchanged"
                if repeated_unchanged
                else "candidate_lifecycle_property_FName_drift"
            ),
            next_reason=(
                "repeated_lifecycle_property_FName_drift_unchanged_non_evidence"
                if repeated_unchanged
                else "candidate_lifecycle_property_FName_drift_non_evidence"
            ),
            classification_context=classification,
            targets=rejected_drift_targets,
            targets_with_players_detected=active_rejected_targets,
            lifecycle_targets=lifecycle_targets_from_rejected_drift_by_target(
                latest_rejected_drift
            ),
            rejected_drift_targets=rejected_drift_targets,
            details={
                "global_delta": global_delta,
                "candidate_rejected_drift_count": int_count(
                    candidate_total_diagnostics.get("rejected_drift_count")
                ),
                "candidate_diagnostic_candidate_count": int_count(
                    candidate_total_diagnostics.get("candidate_count")
                ),
                "candidate_log_budget_reached": (
                    candidate_total_diagnostics.get("log_budget_reached") is True
                ),
            },
        )

    new_diagnostic_targets = str_list(activity_triage.get("new_diagnostic_candidate_targets"))
    if new_diagnostic_targets:
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="new_diagnostics_only",
            reason_kind="new_diagnostic_candidates_without_accepted_events_or_rejected_drift",
            next_reason="new_diagnostic_candidates_without_accepted_events_or_rejected_drift_non_evidence",
            classification_context=classification,
            targets=new_diagnostic_targets,
            targets_with_players_detected=str_list(
                activity_triage.get("targets_with_presence_and_new_diagnostics")
            ),
            diagnostic_only_targets=new_diagnostic_targets,
            details={
                "global_delta": global_delta,
                "new_diagnostic_candidates_by_target": activity_triage.get(
                    "new_diagnostic_candidates_by_target"
                )
                or {},
                "candidate_diagnostic_candidate_count": int_count(
                    candidate_total_diagnostics.get("candidate_count")
                ),
            },
        )

    diagnostic_only_targets = str_list(
        candidate_total_diagnostics.get("diagnostic_only_non_evidence_targets")
    )
    candidate_diagnostic_count = int_count(candidate_counts.get("diagnostic_candidates"))
    if diagnostic_only_targets or candidate_diagnostic_count > 0:
        return passive_actionability_payload(
            summary_scope="latest_passive_snapshot_diff_metadata_only",
            priority="repeated_diagnostics_only",
            reason_kind="repeated_diagnostic_candidates_unchanged",
            next_reason="repeated_diagnostic_candidates_without_accepted_events_or_rejected_drift_unchanged_non_evidence",
            classification_context=classification,
            targets=diagnostic_only_targets,
            diagnostic_only_targets=diagnostic_only_targets,
            details={
                "global_delta": global_delta,
                "candidate_diagnostic_candidate_count": candidate_diagnostic_count,
                "candidate_log_budget_reached": (
                    candidate_total_diagnostics.get("log_budget_reached") is True
                ),
            },
        )

    return passive_actionability_payload(
        summary_scope="latest_passive_snapshot_diff_metadata_only",
        priority="no_passive_observer_activity",
        reason_kind="no_passive_observer_activity",
        next_reason="no_passive_observer_activity_non_evidence",
        classification_context=classification,
        details={"global_delta": global_delta},
    )


def manifest_summary(
    path: Path,
    manifest: dict[str, Any],
    targets: dict[str, dict[str, int]],
    diagnostics: dict[str, dict[str, Any]],
    query_states: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    wait_metadata = passive_wait_metadata_summary(manifest)
    server_activity_summary = passive_server_activity_summary(
        targets,
        diagnostics,
        query_states,
        wait_metadata,
    )
    total_target_diagnostics = total_diagnostics(diagnostics)
    return {
        "path": str(path),
        "snapshot_id": path.parent.name,
        "captured_at_utc": manifest.get("captured_at_utc"),
        "target_count": manifest.get("target_count", len(targets)),
        "counts": total_counts(targets),
        "diagnostics": total_target_diagnostics,
        "monitor": monitor_summary(manifest),
        "passive_wait_metadata": wait_metadata,
        "query_state_by_target": query_states,
        "query_state_by_alias_metadata_only": index_alias_query_states(manifest),
        "passive_server_activity_summary": server_activity_summary,
        "passive_closure_summary": passive_closure_summary(
            source_root=path.parent,
            summary_scope="passive_snapshot_manifest_metadata_only",
            source_root_role="passive_snapshot_root_operational_context_only",
            snapshot_count=1,
            diagnostics=total_target_diagnostics,
            server_activity_summary=server_activity_summary,
            wait_metadata=wait_metadata,
        ),
        "query_state_key_policy": (
            "exact target presence requires INSTANCE:MAP:QUERY_PORT; alias presence is "
            "metadata-only and excluded from lifecycle evidence"
        ),
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
    }


def build_report(
    base_path: Path,
    base_manifest: dict[str, Any],
    candidate_path: Path,
    candidate_manifest: dict[str, Any],
) -> dict[str, Any]:
    base_targets = index_targets(base_manifest)
    candidate_targets = index_targets(candidate_manifest)
    base_diagnostics = index_target_diagnostics(base_manifest)
    candidate_diagnostics = index_target_diagnostics(candidate_manifest)
    base_query_states = index_target_query_state(base_manifest)
    candidate_query_states = index_target_query_state(candidate_manifest)
    global_delta = delta_counts(total_counts(base_targets), total_counts(candidate_targets))
    base_total_diagnostics = total_diagnostics(base_diagnostics)
    candidate_total_diagnostics = total_diagnostics(candidate_diagnostics)
    candidate_total_counts = total_counts(candidate_targets)
    target_deltas = []
    for key in sorted(set(base_targets) | set(candidate_targets)):
        before = base_targets.get(key, {count_key: 0 for count_key in COUNT_KEYS})
        after = candidate_targets.get(key, {count_key: 0 for count_key in COUNT_KEYS})
        before_diagnostics = base_diagnostics.get(key, diagnostics_for_target({"counts": before}))
        after_diagnostics = candidate_diagnostics.get(key, diagnostics_for_target({"counts": after}))
        delta = delta_counts(before, after)
        target_deltas.append(
            {
                "target": key,
                "base_counts": before,
                "candidate_counts": after,
                "delta": delta,
                "diagnostics": {
                    "base_max_sequence": before_diagnostics["max_sequence"],
                    "candidate_max_sequence": after_diagnostics["max_sequence"],
                    "max_sequence_delta": diagnostic_max_delta(
                        before_diagnostics["max_sequence"],
                        after_diagnostics["max_sequence"],
                    ),
                    "base_log_budget_reached": before_diagnostics["log_budget_reached"],
                    "candidate_log_budget_reached": after_diagnostics["log_budget_reached"],
                    "candidate_log_limits": after_diagnostics["log_limits"],
                    "base_latest_observer_line": before_diagnostics["latest_observer_line"],
                    "candidate_latest_observer_line": after_diagnostics["latest_observer_line"],
                    "diagnostic_only_non_evidence": after_diagnostics["only_non_evidence"],
                    "base_observer_event_triage": before_diagnostics[
                        "observer_event_triage"
                    ],
                    "candidate_observer_event_triage": after_diagnostics[
                        "observer_event_triage"
                    ],
                    "accepted_observer_event_triplet_candidate_delta": delta["accepted"],
                    "candidate_complete_observer_event_triplet_candidate_present": after_diagnostics[
                        "observer_event_triage"
                    ][
                        "complete_observer_event_triplet_candidate_present"
                    ],
                    "base_rejected_drift_count": before_diagnostics["rejected_drift_count"],
                    "candidate_rejected_drift_count": after_diagnostics["rejected_drift_count"],
                    "base_latest_rejected_drift_by_lifecycle_target": before_diagnostics[
                        "latest_rejected_drift_by_lifecycle_target"
                    ],
                    "candidate_latest_rejected_drift_by_lifecycle_target": after_diagnostics[
                        "latest_rejected_drift_by_lifecycle_target"
                    ],
                },
                "query_state": {
                    "base": base_query_states.get(key, sanitized_query_state(None)),
                    "candidate": candidate_query_states.get(key, sanitized_query_state(None)),
                },
                "classification": classify_delta(delta),
                "approved_runtime_evidence": False,
                "ready": False,
                "route_ready": False,
            }
        )

    candidate_server_activity_summary = passive_server_activity_summary(
        candidate_targets,
        candidate_diagnostics,
        candidate_query_states,
        passive_wait_metadata_summary(candidate_manifest),
    )
    base_wait_metadata = passive_wait_metadata_summary(base_manifest)
    candidate_wait_metadata = passive_wait_metadata_summary(candidate_manifest)
    base_passive_closure = passive_closure_summary(
        source_root=base_path.parent,
        summary_scope="latest_passive_snapshot_diff_base_metadata_only",
        source_root_role="passive_snapshot_root_operational_context_only",
        snapshot_count=1,
        diagnostics=base_total_diagnostics,
        server_activity_summary=passive_server_activity_summary(
            base_targets,
            base_diagnostics,
            base_query_states,
            base_wait_metadata,
        ),
        wait_metadata=base_wait_metadata,
    )
    candidate_passive_closure = passive_closure_summary(
        source_root=candidate_path.parent,
        summary_scope="latest_passive_snapshot_diff_candidate_metadata_only",
        source_root_role="passive_snapshot_root_operational_context_only",
        snapshot_count=1,
        diagnostics=candidate_total_diagnostics,
        server_activity_summary=candidate_server_activity_summary,
        wait_metadata=candidate_wait_metadata,
    )
    activity_triage = passive_activity_triage(target_deltas)
    report_classification = classify_delta(global_delta)

    return {
        "schema": REPORT_SCHEMA,
        "base": manifest_summary(
            base_path,
            base_manifest,
            base_targets,
            base_diagnostics,
            base_query_states,
        ),
        "candidate": manifest_summary(
            candidate_path,
            candidate_manifest,
            candidate_targets,
            candidate_diagnostics,
            candidate_query_states,
        ),
        "global_delta": global_delta,
        "global_diagnostics": {
            "base_max_sequence": base_total_diagnostics["max_sequence"],
            "candidate_max_sequence": candidate_total_diagnostics["max_sequence"],
            "max_sequence_delta": diagnostic_max_delta(
                base_total_diagnostics["max_sequence"],
                candidate_total_diagnostics["max_sequence"],
            ),
            "base_log_budget_reached": base_total_diagnostics["log_budget_reached"],
            "candidate_log_budget_reached": candidate_total_diagnostics["log_budget_reached"],
            "candidate_log_limits": candidate_total_diagnostics["log_limits"],
            "diagnostic_only_non_evidence_targets": candidate_total_diagnostics[
                "diagnostic_only_non_evidence_targets"
            ],
            "candidate_latest_observer_lines_by_target": candidate_total_diagnostics[
                "latest_observer_lines_by_target"
            ],
            "candidate_rejected_drift_count": candidate_total_diagnostics[
                "rejected_drift_count"
            ],
            "candidate_rejected_drift_targets": candidate_total_diagnostics[
                "rejected_drift_targets"
            ],
            "candidate_latest_rejected_drift_by_snapshot_target": candidate_total_diagnostics[
                "latest_rejected_drift_by_snapshot_target"
            ],
            "base_observer_event_triage": base_total_diagnostics["observer_event_triage"],
            "candidate_observer_event_triage": candidate_total_diagnostics[
                "observer_event_triage"
            ],
            "classification": "passive_diagnostics_non_evidence",
        },
        "candidate_observer_event_triage": candidate_total_diagnostics["observer_event_triage"],
        "candidate_passive_server_activity_summary": candidate_server_activity_summary,
        "base_passive_closure_summary": base_passive_closure,
        "candidate_passive_closure_summary": candidate_passive_closure,
        "passive_closure_summary": candidate_passive_closure,
        "passive_activity_triage": activity_triage,
        "passive_actionability": diff_passive_actionability(
            classification=report_classification,
            global_delta=global_delta,
            candidate_counts=candidate_total_counts,
            candidate_total_diagnostics=candidate_total_diagnostics,
            activity_triage=activity_triage,
        ),
        "classification": report_classification,
        "all_deltas_diagnostic_only": (
            global_delta["accepted"] == 0
            and global_delta["rejected"] == 0
            and global_delta["diagnostic_candidates"] > 0
        ),
        "target_deltas": target_deltas,
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "non_claims": NON_CLAIMS,
    }


def build_latest_report(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    targets = index_targets(manifest)
    diagnostics = index_target_diagnostics(manifest)
    query_states = index_target_query_state(manifest)
    summary = manifest_summary(path, manifest, targets, diagnostics, query_states)
    closure_summary = passive_closure_summary(
        source_root=path.parent,
        summary_scope="latest_passive_snapshot_metadata_only",
        source_root_role="passive_snapshot_root_operational_context_only",
        snapshot_count=1,
        diagnostics=summary["diagnostics"],
        server_activity_summary=summary["passive_server_activity_summary"],
        wait_metadata=summary["passive_wait_metadata"],
    )
    return {
        "schema": LATEST_REPORT_SCHEMA,
        "latest": summary,
        "latest_observer_event_triage": summary["diagnostics"]["observer_event_triage"],
        "passive_server_activity_summary": summary["passive_server_activity_summary"],
        "passive_closure_summary": closure_summary,
        "passive_actionability": latest_passive_actionability(summary),
        "classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "non_claims": NON_CLAIMS,
    }


def build_monitor_only_report(
    *,
    snapshot_root: Path,
    snapshot_count: int,
    monitor_path: Path,
    monitor: dict[str, Any],
) -> dict[str, Any]:
    metadata = monitor.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    targets, diagnostics, query_states = monitor_targets_and_diagnostics(metadata)
    wait_metadata = passive_wait_metadata_summary({"monitor_log": monitor})
    server_activity_summary = passive_server_activity_summary(
        targets,
        diagnostics,
        query_states,
        wait_metadata,
        summary_scope="offline_passive_monitor_metadata_only",
    )
    total_monitor_diagnostics = total_diagnostics(diagnostics)
    summary = {
        "snapshot_id": "monitor-only",
        "diagnostics": total_monitor_diagnostics,
        "passive_server_activity_summary": server_activity_summary,
    }
    monitor_activity = extended_monitor_triage(
        snapshot_root=snapshot_root,
        snapshot_count=snapshot_count,
        monitor_path=monitor_path,
        monitor=monitor,
        targets=targets,
        diagnostics=diagnostics,
        query_states=query_states,
        server_activity_summary=server_activity_summary,
    )
    closure_summary = passive_closure_summary(
        source_root=snapshot_root,
        summary_scope="passive_monitor_only_metadata_only",
        source_root_role="passive_monitor_root_operational_context_only",
        snapshot_count=snapshot_count,
        diagnostics=total_monitor_diagnostics,
        server_activity_summary=server_activity_summary,
        wait_metadata=wait_metadata,
    )
    return {
        "schema": MONITOR_ONLY_REPORT_SCHEMA,
        "snapshot_root": str(snapshot_root),
        "snapshot_count": snapshot_count,
        "snapshot_status": "snapshots_found" if snapshot_count else "no_snapshots_found",
        "monitor": monitor_summary({"monitor_log": monitor}),
        "passive_monitor_activity_summary": monitor_activity,
        "latest_observer_event_triage": total_monitor_diagnostics["observer_event_triage"],
        "passive_server_activity_summary": server_activity_summary,
        "passive_closure_summary": closure_summary,
        "passive_actionability": latest_passive_actionability(summary),
        "query_state_by_target": query_states,
        "passive_wait_metadata": wait_metadata,
        "classification": monitor_activity["classification"],
        "approved_runtime_evidence": False,
        "ready": False,
        "route_ready": False,
        "readiness_gate": "none",
        "non_claims": NON_CLAIMS,
    }


def add_external_monitor_summary(
    report: dict[str, Any],
    *,
    snapshot_root: Path,
    snapshot_count: int,
    monitor_path: Path,
    monitor: dict[str, Any],
) -> None:
    metadata = monitor.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    targets, diagnostics, query_states = monitor_targets_and_diagnostics(metadata)
    server_activity_summary = passive_server_activity_summary(
        targets,
        diagnostics,
        query_states,
        passive_wait_metadata_summary({"monitor_log": monitor}),
        summary_scope="offline_passive_monitor_metadata_only",
    )
    report["external_monitor"] = monitor_summary({"monitor_log": monitor})
    report["passive_monitor_activity_summary"] = extended_monitor_triage(
        snapshot_root=snapshot_root,
        snapshot_count=snapshot_count,
        monitor_path=monitor_path,
        monitor=monitor,
        targets=targets,
        diagnostics=diagnostics,
        query_states=query_states,
        server_activity_summary=server_activity_summary,
    )
    report["external_monitor_passive_closure_summary"] = passive_closure_summary(
        source_root=snapshot_root,
        summary_scope="external_passive_monitor_metadata_only",
        source_root_role="passive_monitor_root_operational_context_only",
        snapshot_count=snapshot_count,
        diagnostics=total_diagnostics(diagnostics),
        server_activity_summary=server_activity_summary,
        wait_metadata=passive_wait_metadata_summary({"monitor_log": monitor}),
    )


def main() -> int:
    args = parse_args()
    try:
        paths = require_paths(args)
        if args.latest:
            snapshot_root, manifest_candidates = list_snapshot_manifests(paths[0])
            if manifest_candidates:
                latest_path, latest_manifest = load_manifest(
                    manifest_candidates[0],
                    "latest manifest",
                )
                report = build_latest_report(latest_path, latest_manifest)
                if args.monitor_log is not None:
                    monitor_path, monitor = load_monitor_log(args.monitor_log)
                    add_external_monitor_summary(
                        report,
                        snapshot_root=snapshot_root,
                        snapshot_count=len(manifest_candidates),
                        monitor_path=monitor_path,
                        monitor=monitor,
                    )
            elif args.monitor_log is not None:
                monitor_path, monitor = load_monitor_log(args.monitor_log)
                report = build_monitor_only_report(
                    snapshot_root=snapshot_root,
                    snapshot_count=0,
                    monitor_path=monitor_path,
                    monitor=monitor,
                )
            else:
                raise SystemExit(f"snapshot root contains no manifest.json files: {snapshot_root}")
        elif args.latest_diff:
            base_manifest_path, candidate_manifest_path = find_latest_manifest_pair(paths[0])
            base_path, base_manifest = load_manifest(base_manifest_path, "base manifest")
            candidate_path, candidate_manifest = load_manifest(
                candidate_manifest_path,
                "candidate manifest",
            )
            report = build_report(base_path, base_manifest, candidate_path, candidate_manifest)
            report["auto_selected_latest_diff"] = True
        else:
            base_path, base_manifest = load_manifest(paths[0], "base manifest")
            candidate_path, candidate_manifest = load_manifest(paths[1], "candidate manifest")
            report = build_report(base_path, base_manifest, candidate_path, candidate_manifest)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 2
        raise

    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
