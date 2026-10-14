#!/usr/bin/env python3
"""Copy passive player-principal observer logs into an offline snapshot.

This helper is intentionally small: it does not start, stop, restart, edit markers, or
claim SDK readiness. It only copies current Obelisk logs to a non-protected output
directory and analyzes the copied files so the next evidence step has reproducible
artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import protected_paths


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[0]
ANALYZER = SCRIPT_DIR / "analyze_runtime_observer_log.py"
DEFAULT_LOG_ROOT = Path("/servidor/ark/obelisk/logs")
SAFE_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
SCHEMA = "obelisk.player-principal-passive-snapshot.v1"
EVENT_TRIAGE_SCHEMA = "obelisk.player-principal-passive-observer-event-triage.v1"
ACTIONABILITY_SCHEMA = "obelisk.player-principal-passive-actionability.v1"
RUNNER_ACTION_HINT_SCHEMA = "obelisk.player-principal-passive-runner-action-hint.v1"
PASSIVE_CLOSURE_SUMMARY_SCHEMA = "obelisk.player-principal-passive-closure-summary.v1"
CLOSURE_COMPATIBLE_RUN_ID_PATTERN = r"^[0-9]{8}T[0-9]{6}Z-player-principal-lifecycle$"
CLOSURE_COMPATIBLE_RUN_ID_RE = re.compile(CLOSURE_COMPATIBLE_RUN_ID_PATTERN)
REQUIRED_OBSERVER_EVENT_ROLES = ("session_start", "session_start_rejected", "session_end")
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_target(value: str) -> dict[str, str]:
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError("target must be INSTANCE:MAP[:QUERY_PORT]")
    instance, game_map = parts[0], parts[1]
    query_port = parts[2] if len(parts) == 3 else ""
    for label, component in (("instance", instance), ("map", game_map)):
        if not component or SAFE_COMPONENT_RE.fullmatch(component) is None:
            raise argparse.ArgumentTypeError(f"unsafe {label} in target: {value}")
    if query_port and re.fullmatch(r"[0-9]+", query_port) is None:
        raise argparse.ArgumentTypeError(f"unsafe query port in target: {value}")
    return {"instance": instance, "map": game_map, "query_port": query_port}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-server-path",
        action="store_true",
        help="Allow copying from the live /servidor/ark Obelisk log root.",
    )
    parser.add_argument(
        "--log-root",
        type=Path,
        default=DEFAULT_LOG_ROOT,
        help="Obelisk log root containing <instance>/Obelisk.log.",
    )
    parser.add_argument(
        "--monitor-log",
        type=Path,
        help="Optional passive monitor log to copy alongside target logs.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target", action="append", type=parse_target, required=True)
    return parser.parse_args()


def prepare_output_dir(path: Path) -> Path:
    protected_paths.reject_symlink_component(path, "--output-dir")
    resolved = protected_paths.reject_protected_output_path(path, "passive snapshot output")
    if resolved.exists() and not resolved.is_dir():
        raise SystemExit(f"--output-dir must be a directory: {resolved}")
    if resolved.exists() and any(resolved.iterdir()):
        raise SystemExit(f"--output-dir must be empty for a new passive snapshot: {resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def resolve_input(path: Path, *, allow_server_path: bool, label: str) -> Path:
    protected_paths.reject_symlink_component(path, label)
    status = protected_paths.protected_path_status(path)
    if status.protected and not allow_server_path:
        raise SystemExit(f"{label} refuses live server path without --allow-server-path: {status.resolved}")
    return status.resolved


def run_analyzer(copied_log: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(ANALYZER), str(copied_log)],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    payload: dict[str, Any] | None = None
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = None
    if isinstance(payload, dict):
        payload = sanitize_analyzer_summary_for_passive_snapshot(payload)
    return {
        "returncode": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
        "stderr": result.stderr.strip(),
        "summary": payload,
    }


def sanitize_analyzer_summary_for_passive_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    sanitized["approved_runtime_evidence"] = False
    sanitized["ready"] = False
    sanitized["runtime_evidence_ready"] = False
    sanitized["readiness_gate"] = "none"
    modules = sanitized.get("modules")
    if isinstance(modules, dict):
        sanitized_modules: dict[str, Any] = {}
        for name, module in modules.items():
            if isinstance(module, dict):
                sanitized_module = dict(module)
                sanitized_module["approved_runtime_evidence"] = False
                sanitized_module["ready"] = False
                sanitized_module["runtime_evidence_ready"] = False
                sanitized_modules[name] = sanitized_module
            else:
                sanitized_modules[name] = module
        sanitized["modules"] = sanitized_modules
    return sanitized


def int_count(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    return 0


def int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
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
    read_status = safe_diagnostic_token(value.get("read_status"))
    timestamp_prefix = value.get("timestamp_prefix")
    drift_count = int_or_none(value.get("drift_count"))
    output: dict[str, Any] = {
        "target": target,
        "sequence": sequence,
        "line_number": line_number,
        "timestamp_prefix": timestamp_prefix if isinstance(timestamp_prefix, str) else None,
        "fname_index": fname_index,
        "reflection_status": "rejected",
        "read_status": read_status,
        "reason": reason,
        "reason_kind": reason_kind,
        "evidence_claim": "none",
        "evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
    }
    if (function_name_index := int_or_none(value.get("function_name_index"))) is not None:
        output["function_name_index"] = function_name_index
    if (outer_name_index := int_or_none(value.get("outer_name_index"))) is not None:
        output["outer_name_index"] = outer_name_index
    if drift_count is not None:
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


def accepted_observer_event_roles(module: dict[str, Any]) -> list[str]:
    cases = module.get("observed_event_cases")
    if not isinstance(cases, list):
        return []
    roles = {
        role
        for case in cases
        if isinstance(case, dict)
        and isinstance((role := case.get("role")), str)
        and role in REQUIRED_OBSERVER_EVENT_ROLES
    }
    return [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role in roles]


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


def observer_event_triage_from_module(
    module: dict[str, Any],
    counts: dict[str, int],
) -> dict[str, Any]:
    accepted_count = int_count(counts.get("accepted"))
    rejected_count = int_count(counts.get("rejected"))
    diagnostic_count = int_count(counts.get("diagnostic_candidates"))
    roles = accepted_observer_event_roles(module)
    missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in roles]
    complete_triplet = accepted_count > 0 and not missing_roles
    return {
        "schema": EVENT_TRIAGE_SCHEMA,
        "accepted_observer_event_triplet_candidate_count": accepted_count,
        "rejected_observer_event_line_count": rejected_count,
        "diagnostic_only_line_count": diagnostic_count,
        "contains_accepted_observer_event_triplet_candidates": accepted_count > 0,
        "contains_diagnostic_only_lines": diagnostic_count > 0,
        "accepted_observer_event_roles": roles,
        "missing_observer_event_triplet_roles": missing_roles,
        "complete_observer_event_triplet_candidate_present": complete_triplet,
        "classification": observer_event_triage_classification(
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            diagnostic_count=diagnostic_count,
            complete_triplet=complete_triplet,
        ),
        "evidence_classification": "passive_snapshot_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
    }


def empty_diagnostics() -> dict[str, Any]:
    empty_counts = {"accepted": 0, "rejected": 0, "diagnostic_candidates": 0}
    return {
        "candidate_count": 0,
        "max_sequence": None,
        "log_limits": [],
        "log_budget_reached": False,
        "only_non_evidence": False,
        "latest_observer_line": None,
        "classification": "no_diagnostic_candidates",
        "observer_event_triage": observer_event_triage_from_module({}, empty_counts),
    }


def sanitized_observer_line(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    source_index = value.get("source_index")
    line_number = value.get("line_number")
    kind = value.get("kind")
    timestamp_prefix = value.get("timestamp_prefix")
    if (
        isinstance(source_index, bool)
        or not isinstance(source_index, int)
        or isinstance(line_number, bool)
        or not isinstance(line_number, int)
        or not isinstance(kind, str)
    ):
        return None
    return {
        "source_index": source_index,
        "line_number": line_number,
        "timestamp_prefix": timestamp_prefix if isinstance(timestamp_prefix, str) else None,
        "kind": kind,
    }


def diagnostics_from_module(module: dict[str, Any], counts: dict[str, int]) -> dict[str, Any]:
    candidate_count = counts["diagnostic_candidates"]
    observer_event_triage = observer_event_triage_from_module(module, counts)
    latest_rejected_drift = sanitized_rejected_drift_by_lifecycle_target(
        module.get("diagnostic_candidate_latest_rejected_drift_by_target")
    )
    rejected_drift_counts = sanitized_rejected_drift_counts(
        module.get("diagnostic_candidate_rejected_drift_target_counts")
    )
    rejected_drift_count = int_count(module.get("diagnostic_candidate_rejected_drift_count"))
    only_non_evidence = (
        counts["accepted"] == 0
        and counts["rejected"] == 0
        and candidate_count > 0
        and module.get("diagnostic_only_non_evidence") is not False
    )
    return {
        "candidate_count": candidate_count,
        "max_sequence": module.get("diagnostic_candidate_max_sequence"),
        "log_limits": module.get("diagnostic_log_limits", []),
        "log_budget_reached": bool(module.get("diagnostic_log_budget_reached", False)),
        "only_non_evidence": only_non_evidence,
        "latest_observer_line": sanitized_observer_line(module.get("latest_observer_line")),
        "classification": (
            "diagnostic_only_non_evidence"
            if only_non_evidence
            else "passive_snapshot_non_evidence"
            if candidate_count > 0
            else "no_diagnostic_candidates"
        ),
        "observer_event_triage": observer_event_triage,
        "accepted_observer_event_triplet_candidate_count": observer_event_triage[
            "accepted_observer_event_triplet_candidate_count"
        ],
        "complete_observer_event_triplet_candidate_present": observer_event_triage[
            "complete_observer_event_triplet_candidate_present"
        ],
        "event_triplet_classification": observer_event_triage["classification"],
        "rejected_drift_count": rejected_drift_count,
        "rejected_drift_target_counts": rejected_drift_counts,
        "latest_rejected_drift_by_lifecycle_target": latest_rejected_drift,
        "contains_rejected_drift": rejected_drift_count > 0 or bool(latest_rejected_drift),
        "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
    }


def aggregate_diagnostics(targets: list[dict[str, Any]]) -> dict[str, Any]:
    diagnostics = [
        target.get("diagnostics")
        for target in targets
        if isinstance(target.get("diagnostics"), dict)
    ]
    max_sequences = [
        diagnostic.get("max_sequence")
        for diagnostic in diagnostics
        if isinstance(diagnostic.get("max_sequence"), int)
    ]
    log_limits = sorted(
        {
            limit
            for diagnostic in diagnostics
            for limit in diagnostic.get("log_limits", [])
            if isinstance(limit, int)
        }
    )
    observer_event_triages = [
        diagnostic.get("observer_event_triage")
        for diagnostic in diagnostics
        if isinstance(diagnostic.get("observer_event_triage"), dict)
    ]
    latest_rejected_drift_by_snapshot_target = {
        str(
            target.get("target_key")
            or target_key_for(
                str(target.get("instance", "unknown")),
                str(target.get("map", "unknown")),
                str(target.get("query_port") or ""),
            )
        ): latest_rejected_drift
        for target in targets
        if isinstance((diagnostic := target.get("diagnostics")), dict)
        and (
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
            target_key
            for target_key, diagnostic in (
                (
                    str(
                        target.get("target_key")
                        or target_key_for(
                            str(target.get("instance", "unknown")),
                            str(target.get("map", "unknown")),
                            str(target.get("query_port") or ""),
                        )
                    ),
                    target.get("diagnostics"),
                )
                for target in targets
            )
            if isinstance(diagnostic, dict)
            and isinstance((triage := diagnostic.get("observer_event_triage")), dict)
            and triage.get("contains_accepted_observer_event_triplet_candidates") is True
        ),
        "targets_with_complete_observer_event_triplet_candidate": sorted(
            target_key
            for target_key, diagnostic in (
                (
                    str(
                        target.get("target_key")
                        or target_key_for(
                            str(target.get("instance", "unknown")),
                            str(target.get("map", "unknown")),
                            str(target.get("query_port") or ""),
                        )
                    ),
                    target.get("diagnostics"),
                )
                for target in targets
            )
            if isinstance(diagnostic, dict)
            and isinstance((triage := diagnostic.get("observer_event_triage")), dict)
            and triage.get("complete_observer_event_triplet_candidate_present") is True
        ),
        "targets_with_diagnostic_only_lines": sorted(
            target_key
            for target_key, diagnostic in (
                (
                    str(
                        target.get("target_key")
                        or target_key_for(
                            str(target.get("instance", "unknown")),
                            str(target.get("map", "unknown")),
                            str(target.get("query_port") or ""),
                        )
                    ),
                    target.get("diagnostics"),
                )
                for target in targets
            )
            if isinstance(diagnostic, dict)
            and isinstance((triage := diagnostic.get("observer_event_triage")), dict)
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
        "readiness_gate": "none",
    }
    return {
        "candidate_count": sum(
            diagnostic.get("candidate_count", 0)
            for diagnostic in diagnostics
            if isinstance(diagnostic.get("candidate_count"), int)
        ),
        "max_sequence": max(max_sequences) if max_sequences else None,
        "log_limits": log_limits,
        "log_budget_reached": any(
            diagnostic.get("log_budget_reached") is True for diagnostic in diagnostics
        ),
        "diagnostic_only_non_evidence_targets": sorted(
            target_key
            for target_key, diagnostic in (
                (
                    str(
                        target.get("target_key")
                        or target_key_for(
                            str(target.get("instance", "unknown")),
                            str(target.get("map", "unknown")),
                            str(target.get("query_port") or ""),
                        )
                    ),
                    target.get("diagnostics"),
                )
                for target in targets
            )
            if isinstance(diagnostic, dict) and diagnostic.get("only_non_evidence") is True
        ),
        "latest_observer_lines_by_target": {
            str(
                target.get("target_key")
                or target_key_for(
                    str(target.get("instance", "unknown")),
                    str(target.get("map", "unknown")),
                    str(target.get("query_port") or ""),
                )
            ): diagnostic["latest_observer_line"]
            for target in targets
            if isinstance((diagnostic := target.get("diagnostics")), dict)
            and diagnostic.get("latest_observer_line") is not None
        },
        "rejected_drift_count": sum(
            int_count(diagnostic.get("rejected_drift_count"))
            for diagnostic in diagnostics
        ),
        "rejected_drift_targets": sorted(latest_rejected_drift_by_snapshot_target),
        "latest_rejected_drift_by_snapshot_target": latest_rejected_drift_by_snapshot_target,
        "rejected_drift_evidence_classification": "diagnostic_rejected_drift_non_evidence",
        "classification": "passive_diagnostics_non_evidence",
        "observer_event_triage": observer_event_triage,
    }


def parse_int_text(value: Any) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+", value):
        return None
    return int(value)


def parse_monitor_kv_line(line: str) -> tuple[str, dict[str, str]] | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None
    if not parts:
        return None
    values: dict[str, str] = {}
    for token in parts[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        if key:
            values[key] = value
    return parts[0], values


def parse_players_text(value: str | None) -> tuple[int | None, int | None]:
    if value is None:
        return None, None
    match = re.fullmatch(r"([0-9]+)/([0-9]+|unknown)", value)
    if not match:
        return None, None
    current = int(match.group(1))
    maximum = int(match.group(2)) if match.group(2).isdigit() else None
    return current, maximum


def parse_bool_text(value: Any) -> bool | None:
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def passive_process_control_metadata(value: Any) -> dict[str, str | None]:
    reported = value if isinstance(value, str) and value else None
    return {
        "process_control": "none",
        "reported_process_control": reported,
        "process_control_policy": "passive_metadata_only_never_signal_stop_or_replace",
    }


def passive_metadata_fields(
    values: dict[str, str] | None = None,
    *,
    evidence_classification: str = "passive_monitor_metadata_non_evidence",
) -> dict[str, Any]:
    return {
        "evidence_classification": evidence_classification,
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        **passive_process_control_metadata((values or {}).get("process_control")),
    }


def clean_monitor_token(value: Any) -> str:
    return value[:-1] if isinstance(value, str) and value.endswith(".") else str(value or "")


def monitor_observer_event_is_accepted(values: dict[str, str]) -> bool:
    role = clean_monitor_token(values.get("role"))
    target = clean_monitor_token(values.get("target"))
    common = (
        clean_monitor_token(values.get("post_original")) == "true"
        and clean_monitor_token(values.get("principal_id_logged")) == "false"
        and clean_monitor_token(values.get("principal_generation_logged")) == "false"
        and clean_monitor_token(values.get("delivery_claim")) == "none"
    )
    if not common:
        return False
    if role == "session_start" and target == "ShooterGameMode.HandleNewPlayer":
        return (
            clean_monitor_token(values.get("copied_bool_fields")) == "bIsFromLogin,ReturnValue"
            and clean_monitor_token(values.get("copied_bool_values")) == "1,1"
            and clean_monitor_token(values.get("redacted_count")) == "3"
            and clean_monitor_token(values.get("redacted_fields"))
            == "NewPlayer,PlayerData,PlayerCharacter"
            and clean_monitor_token(values.get("principal_action")) == "candidate_created"
            and clean_monitor_token(values.get("apply_status")) == "session_start_created"
            and clean_monitor_token(values.get("correlation_status")) == "not_applicable"
        )
    if role == "session_start_rejected" and target == "ShooterGameMode.CheckJoinInProgress":
        return (
            clean_monitor_token(values.get("copied_bool_fields")) == "bIsFromLogin,ReturnValue"
            and clean_monitor_token(values.get("copied_bool_values")) == "1,0"
            and clean_monitor_token(values.get("redacted_count")) == "1"
            and clean_monitor_token(values.get("redacted_fields")) == "NewPlayer"
            and clean_monitor_token(values.get("principal_action")) == "none"
            and clean_monitor_token(values.get("apply_status")) == "session_start_rejected_noop"
            and clean_monitor_token(values.get("correlation_status")) == "not_applicable"
        )
    if role == "session_end" and target == "ShooterGameMode.OnLogout":
        return (
            clean_monitor_token(values.get("copied_bool_fields")) == ""
            and clean_monitor_token(values.get("copied_bool_values")) == ""
            and clean_monitor_token(values.get("redacted_count")) == "1"
            and clean_monitor_token(values.get("redacted_fields")) == "Exiting"
            and clean_monitor_token(values.get("principal_action")) == "candidate_invalidated"
            and clean_monitor_token(values.get("apply_status")) == "session_end_invalidated"
            and clean_monitor_token(values.get("correlation_status")) == "matched"
        )
    return False


def monitor_observer_event_is_superseded_handle_rejected_start(values: dict[str, str]) -> bool:
    return (
        clean_monitor_token(values.get("role")) == "session_start_rejected"
        and clean_monitor_token(values.get("target")) == "ShooterGameMode.HandleNewPlayer"
        and clean_monitor_token(values.get("post_original")) == "true"
        and clean_monitor_token(values.get("copied_bool_fields")) == "bIsFromLogin,ReturnValue"
        and clean_monitor_token(values.get("copied_bool_values")) in {"0,0", "0,1", "1,0"}
        and clean_monitor_token(values.get("redacted_count")) == "3"
        and clean_monitor_token(values.get("redacted_fields")) == "NewPlayer,PlayerData,PlayerCharacter"
        and clean_monitor_token(values.get("principal_action")) == "none"
        and clean_monitor_token(values.get("apply_status")) == "session_start_rejected_noop"
        and clean_monitor_token(values.get("correlation_status")) == "not_applicable"
        and clean_monitor_token(values.get("principal_id_logged")) == "false"
        and clean_monitor_token(values.get("principal_generation_logged")) == "false"
        and clean_monitor_token(values.get("delivery_claim")) == "none"
    )


def empty_monitor_observer_tail_correction(
    *,
    target_key: str,
    target_key_kind: str,
    alias_target_key: str | None,
    exact_target_key: str | None,
    source_target_key: str | None,
    instance: str,
    game_map: str,
    query_port: str,
) -> dict[str, Any]:
    return {
        "target_key": target_key,
        "target_key_kind": target_key_kind,
        "alias_target_key": alias_target_key,
        "exact_target_key": exact_target_key,
        "source_target_key": source_target_key,
        "instance": instance,
        "map": game_map,
        "query_port": query_port,
        "observer_gate_lines": 0,
        "raw_observer_event_lines": 0,
        "accepted_observer_event_triplet_candidate_lines": 0,
        "rejected_observer_event_line_count": 0,
        "check_join_rejected_start_candidate_lines": 0,
        "superseded_handle_new_player_rejected_start_lines": 0,
        "diagnostic_only_lines": 0,
        "raw_role_counts": {role: 0 for role in REQUIRED_OBSERVER_EVENT_ROLES},
        "accepted_role_counts": {role: 0 for role in REQUIRED_OBSERVER_EVENT_ROLES},
        "latest_raw_observer_event_role": "none",
        "latest_observer_event_role": "none",
        "latest_start_order": 0,
        "latest_end_order": 0,
        "line_order": 0,
    }


def record_monitor_observer_line(
    metadata: dict[str, Any],
    *,
    line: str,
    values: dict[str, str],
    current_tick_utc: str | None,
    alias_to_exact_target: dict[str, str],
) -> None:
    instance = values.get("instance")
    if not instance:
        return
    game_map = values.get("map") or "unknown"
    query_port = values.get("query_port") or ""
    key_metadata = monitor_target_key_metadata(
        values,
        instance=instance,
        game_map=game_map,
        query_port=query_port,
        alias_to_exact_target=alias_to_exact_target,
    )
    target_key = str(key_metadata["target_key"])
    corrections = metadata.setdefault("_observer_tail_corrections", {})
    correction = corrections.setdefault(
        target_key,
        empty_monitor_observer_tail_correction(
            target_key=target_key,
            target_key_kind=str(key_metadata["target_key_kind"]),
            alias_target_key=key_metadata["alias_target_key"],
            exact_target_key=key_metadata["exact_target_key"],
            source_target_key=key_metadata["source_target_key"],
            instance=instance,
            game_map=game_map,
            query_port=str(key_metadata["query_port"] or ""),
        ),
    )
    correction["line_order"] += 1
    correction["utc"] = current_tick_utc
    if "PlayerPrincipalLifecycleObserver enabled" in line:
        correction["observer_gate_lines"] += 1
        return
    if "PlayerPrincipalLifecycleDiagnostic candidate" in line:
        correction["diagnostic_only_lines"] += 1
        return
    role = clean_monitor_token(values.get("role"))
    if role not in REQUIRED_OBSERVER_EVENT_ROLES:
        return
    correction["raw_observer_event_lines"] += 1
    correction["raw_role_counts"][role] += 1
    correction["latest_raw_observer_event_role"] = role
    if monitor_observer_event_is_accepted(values):
        correction["accepted_observer_event_triplet_candidate_lines"] += 1
        correction["accepted_role_counts"][role] += 1
        correction["latest_observer_event_role"] = role
        if role == "session_start":
            correction["latest_start_order"] = correction["line_order"]
        elif role == "session_end":
            correction["latest_end_order"] = correction["line_order"]
        elif role == "session_start_rejected":
            correction["check_join_rejected_start_candidate_lines"] += 1
    elif monitor_observer_event_is_superseded_handle_rejected_start(values):
        correction["rejected_observer_event_line_count"] += 1
        correction["superseded_handle_new_player_rejected_start_lines"] += 1


def monitor_roles_from_counts(counts: dict[str, int]) -> list[str]:
    return [role for role in REQUIRED_OBSERVER_EVENT_ROLES if int_count(counts.get(role)) > 0]


def apply_monitor_observer_tail_corrections(metadata: dict[str, Any]) -> None:
    corrections = metadata.pop("_observer_tail_corrections", {})
    if not isinstance(corrections, dict):
        return
    for target_key, correction in sorted(corrections.items()):
        if not isinstance(correction, dict):
            continue
        target_key_kind = correction.get("target_key_kind")
        tail_bucket_name = (
            "observer_tail_by_target" if target_key_kind == "exact" else "observer_tail_by_alias"
        )
        tail_bucket = metadata.get(tail_bucket_name)
        if not isinstance(tail_bucket, dict):
            continue
        tail = tail_bucket.get(target_key)
        if not isinstance(tail, dict):
            continue
        accepted_roles = monitor_roles_from_counts(correction.get("accepted_role_counts", {}))
        raw_roles = monitor_roles_from_counts(correction.get("raw_role_counts", {}))
        missing_roles = [role for role in REQUIRED_OBSERVER_EVENT_ROLES if role not in accepted_roles]
        complete_triplet = bool(accepted_roles) and not missing_roles
        accepted_count = int_count(
            correction.get("accepted_observer_event_triplet_candidate_lines")
        )
        rejected_count = int_count(correction.get("rejected_observer_event_line_count"))
        diagnostic_count = int_count(correction.get("diagnostic_only_lines"))
        tail.update(
            {
                "observer_gate_lines": int_count(correction.get("observer_gate_lines")),
                "raw_observer_event_lines": int_count(
                    correction.get("raw_observer_event_lines")
                ),
                "accepted_observer_event_triplet_candidate_lines": accepted_count,
                "rejected_observer_event_line_count": rejected_count,
                "check_join_rejected_start_candidate_lines": int_count(
                    correction.get("check_join_rejected_start_candidate_lines")
                ),
                "superseded_handle_new_player_rejected_start_lines": int_count(
                    correction.get("superseded_handle_new_player_rejected_start_lines")
                ),
                "diagnostic_only_lines": diagnostic_count,
                "raw_event_roles": raw_roles,
                "event_roles": accepted_roles,
                "latest_raw_observer_event_role": correction.get(
                    "latest_raw_observer_event_role"
                )
                or "none",
                "latest_observer_event_role": correction.get("latest_observer_event_role")
                or "none",
                "lifecycle_active_candidate": int_count(
                    correction.get("latest_start_order")
                )
                > int_count(correction.get("latest_end_order")),
                "complete_triplet_candidate": complete_triplet,
                "classification": observer_event_triage_classification(
                    accepted_count=accepted_count,
                    rejected_count=rejected_count,
                    diagnostic_count=diagnostic_count,
                    complete_triplet=complete_triplet,
                ),
                "observer_event_role_policy": "accepted_safe_observer_events_only",
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
            }
        )


def split_csv_text(value: Any) -> list[str]:
    if not isinstance(value, str) or not value or value == "none":
        return []
    return [item for item in value.split(",") if item]


def target_key_for(instance: str, game_map: str, query_port: str | None = None) -> str:
    if query_port:
        return f"{instance}:{game_map}:{query_port}"
    return f"{instance}:{game_map}"


def target_alias_key_for(instance: str, game_map: str) -> str:
    return f"{instance}:{game_map}"


def target_key_from_target(target: dict[str, str]) -> str:
    return target_key_for(target["instance"], target["map"], target.get("query_port") or "")


def target_alias_key_from_target(target: dict[str, str]) -> str:
    return target_alias_key_for(target["instance"], target["map"])


def parsed_exact_target_key(value: Any) -> tuple[str, str, str] | None:
    if not isinstance(value, str):
        return None
    parts = value.split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        return None
    return parts[0], parts[1], parts[2]


def is_exact_target_key(value: Any) -> bool:
    return parsed_exact_target_key(value) is not None


def expected_alias_to_exact_target_keys(
    expected_targets: list[dict[str, str]] | None,
) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for target in expected_targets or []:
        if not target.get("query_port"):
            continue
        aliases.setdefault(target_alias_key_from_target(target), target_key_from_target(target))
    return aliases


def expected_instance_to_target_keys(
    expected_targets: list[dict[str, str]] | None,
) -> dict[str, list[str]]:
    targets_by_instance: dict[str, list[str]] = {}
    for target in expected_targets or []:
        targets_by_instance.setdefault(target["instance"], []).append(target_key_from_target(target))
    return {
        instance: sorted(target_keys)
        for instance, target_keys in targets_by_instance.items()
    }


def event_target_keys(
    values: dict[str, str],
    *,
    instance_to_target_keys: dict[str, list[str]],
) -> list[str]:
    target_keys = split_csv_text(values.get("target_keys")) or split_csv_text(
        values.get("detected_target_keys")
    )
    if target_keys:
        return target_keys
    resolved: list[str] = []
    for instance in split_csv_text(values.get("detected_instances")):
        resolved.extend(instance_to_target_keys.get(instance, []))
    return sorted(dict.fromkeys(resolved))


def monitor_target_key_metadata(
    values: dict[str, str],
    *,
    instance: str,
    game_map: str,
    query_port: str,
    alias_to_exact_target: dict[str, str],
) -> dict[str, str | None]:
    source_target_key = values.get("target_key") or ""
    parsed_source = parsed_exact_target_key(source_target_key)
    if (
        not query_port
        and parsed_source is not None
        and parsed_source[0] == instance
        and parsed_source[1] == game_map
    ):
        query_port = parsed_source[2]

    alias_target_key = target_alias_key_for(instance, game_map)
    if query_port:
        exact_target_key = target_key_for(instance, game_map, query_port)
        return {
            "target_key": exact_target_key,
            "target_key_kind": "exact",
            "query_port": query_port,
            "alias_target_key": alias_target_key,
            "exact_target_key": exact_target_key,
            "source_target_key": source_target_key or exact_target_key,
        }

    alias_key = source_target_key if source_target_key and not is_exact_target_key(source_target_key) else alias_target_key
    return {
        "target_key": alias_key,
        "target_key_kind": "alias",
        "query_port": "",
        "alias_target_key": alias_key,
        "exact_target_key": alias_to_exact_target.get(alias_key),
        "source_target_key": source_target_key or alias_key,
    }


def query_state_default(target: dict[str, str]) -> dict[str, Any]:
    target_key = target_key_from_target(target)
    target_key_kind = "exact" if target["query_port"] else "alias"
    return {
        "target_key": target_key,
        "target_key_kind": target_key_kind,
        "alias_target_key": target_alias_key_from_target(target),
        "instance": target["instance"],
        "map": target["map"],
        "query_port": target["query_port"],
        "status": "not_reported",
        "detection_source": "not_reported",
        "query_sample_kind": "aggregate_player_count",
        "query_presence_eligible": target_key_kind == "exact",
        "last_query_utc": None,
        "presence_detected": False,
        "last_presence_detected_utc": None,
        "evidence_classification": "passive_monitor_metadata_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        **passive_process_control_metadata(None),
    }


def sanitized_alias_query_state(value: Any, alias_key: str) -> dict[str, Any]:
    state = value if isinstance(value, dict) else {}
    instance = state.get("instance")
    game_map = state.get("map")
    if not isinstance(instance, str) or not instance:
        instance = alias_key.split(":", 1)[0] if ":" in alias_key else "unknown"
    if not isinstance(game_map, str) or not game_map:
        game_map = alias_key.split(":", 1)[1] if ":" in alias_key else "unknown"
    return {
        "target_key": alias_key,
        "target_key_kind": "alias",
        "alias_target_key": alias_key,
        "exact_target_key": state.get("exact_target_key")
        if isinstance(state.get("exact_target_key"), str)
        else None,
        "source_target_key": state.get("source_target_key")
        if isinstance(state.get("source_target_key"), str)
        else alias_key,
        "instance": instance,
        "map": game_map,
        "query_port": "",
        "status": str(state.get("status") or "alias_metadata_only"),
        "current_map": state.get("current_map") if isinstance(state.get("current_map"), str) else None,
        "players": state.get("players") if isinstance(state.get("players"), str) else None,
        "players_current": int_or_none(state.get("players_current")),
        "players_max": int_or_none(state.get("players_max")),
        "error": state.get("error") if isinstance(state.get("error"), str) else None,
        "detection_source": str(state.get("detection_source") or "gamedig_ase_query"),
        "query_sample_kind": "aggregate_player_count",
        "query_presence_eligible": False,
        "alias_presence_metadata_only": True,
        "last_query_utc": state.get("last_query_utc") if isinstance(state.get("last_query_utc"), str) else None,
        "presence_detected": state.get("presence_detected") is True,
        "last_presence_detected_utc": (
            state.get("last_presence_detected_utc")
            if isinstance(state.get("last_presence_detected_utc"), str)
            else None
        ),
        "last_warning_rc": int_or_none(state.get("last_warning_rc")),
        "last_warning_utc": state.get("last_warning_utc")
        if isinstance(state.get("last_warning_utc"), str)
        else None,
        "evidence_classification": "passive_alias_presence_metadata_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        **passive_process_control_metadata(state.get("process_control")),
    }


def state_is_exact_for_target(state: Any, target: dict[str, str]) -> bool:
    if not isinstance(state, dict):
        return False
    if state.get("target_key_kind") == "alias":
        return False
    expected_key = target_key_from_target(target)
    state_key = state.get("target_key")
    if isinstance(state_key, str) and state_key and state_key != expected_key:
        return False
    if str(state.get("instance") or target["instance"]) != target["instance"]:
        return False
    if str(state.get("map") or target["map"]) != target["map"]:
        return False
    if target.get("query_port") and str(state.get("query_port") or "") != target["query_port"]:
        return False
    return bool(target.get("query_port"))


def exact_query_state_for_target(state: Any, target: dict[str, str]) -> dict[str, Any] | None:
    if not state_is_exact_for_target(state, target):
        return None
    normalized = dict(state)
    normalized["target_key"] = target_key_from_target(target)
    normalized["target_key_kind"] = "exact"
    normalized["alias_target_key"] = target_alias_key_from_target(target)
    normalized["query_port"] = target["query_port"]
    normalized["query_presence_eligible"] = True
    normalized["approved_runtime_evidence"] = False
    normalized["ready"] = False
    normalized.setdefault("evidence_classification", "passive_monitor_metadata_non_evidence")
    normalized["readiness_gate"] = "none"
    normalized.update(passive_process_control_metadata(normalized.get("process_control")))
    return normalized


def parse_monitor_log_metadata(
    path: Path,
    *,
    expected_targets: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    alias_to_exact_target = expected_alias_to_exact_target_keys(expected_targets)
    instance_to_target_keys = expected_instance_to_target_keys(expected_targets)
    default_process_control = passive_process_control_metadata(None)
    metadata: dict[str, Any] = {
        "schema": "obelisk.passive-monitor-log-metadata.v1",
        "session": {"status": "not_reported", **default_process_control},
        "sessions": [],
        "replacement": {"status": "not_reported", **default_process_control},
        "latest_tick_utc": None,
        "query_state_by_instance": {},
        "query_state_by_target": {},
        "query_state_by_alias": {},
        "query_state_alias_by_instance": {},
        "query_state_key_policy": (
            "query_state_by_target uses exact INSTANCE:MAP:QUERY_PORT keys only; "
            "query_state_by_alias is metadata-only and excluded from lifecycle evidence"
        ),
        "observer_tail_events": [],
        "observer_tail_by_target": {},
        "observer_tail_by_alias": {},
        "linger_events": [],
        "linger_by_target": {},
        "passive_wait_policy": (
            "wait-only metadata; observer tails and linger windows do not authorize "
            "process control or evidence promotion"
        ),
        "snapshot_events": [],
        "approved_runtime_evidence": False,
        "ready": False,
        **default_process_control,
    }
    current_tick_utc: str | None = None
    line_count = 0
    for line_count, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        parsed = parse_monitor_kv_line(line)
        if parsed is None:
            continue
        event, values = parsed
        if event == "passive_monitor_session":
            replaced_pid = parse_int_text(values.get("replaced_monitor_pid"))
            process_control = passive_process_control_metadata(values.get("process_control"))
            session = {
                "status": "reported",
                "line_number": line_count,
                "started_at_utc": values.get("utc"),
                "pid": parse_int_text(values.get("pid")),
                "ppid": parse_int_text(values.get("ppid")),
                "session_id": values.get("session_id"),
                "tmux_session": values.get("tmux_session"),
                "tmux_pane": values.get("tmux_pane"),
                "targets": values.get("targets"),
                "target_count": parse_int_text(values.get("target_count")),
                "interval": parse_int_text(values.get("interval")),
                "once": values.get("once"),
                "linger_after_detect": parse_int_text(values.get("linger_after_detect")),
                "active_monitor_policy": values.get("active_monitor_policy"),
                **process_control,
            }
            replacement = {
                "status": values.get("replacement_status", "reported"),
                "replaced_monitor_pid": replaced_pid,
                "active_monitor_pid": parse_int_text(values.get("active_monitor_pid"))
                or replaced_pid,
                "replacement_requested": parse_bool_text(values.get("replacement_requested")),
                "old_monitor_action": values.get("old_monitor_action"),
                "replacement_policy": values.get("replacement_policy"),
                "replacement_note": values.get("replacement_note"),
                "active_monitor_policy": values.get("active_monitor_policy"),
                **process_control,
            }
            metadata["sessions"].append(session)
            metadata["session"] = session
            metadata["replacement"] = replacement
            metadata.update(process_control)
            continue
        if event == "tick":
            current_tick_utc = values.get("utc")
            metadata["latest_tick_utc"] = current_tick_utc
            continue
        if event == "query":
            instance = values.get("instance")
            if not instance:
                continue
            game_map = values.get("map") or "unknown"
            query_port = values.get("query_port") or ""
            key_metadata = monitor_target_key_metadata(
                values,
                instance=instance,
                game_map=game_map,
                query_port=query_port,
                alias_to_exact_target=alias_to_exact_target,
            )
            target_key = str(key_metadata["target_key"])
            target_key_kind = str(key_metadata["target_key_kind"])
            query_port = str(key_metadata["query_port"] or "")
            players_current, players_max = parse_players_text(values.get("players"))
            players_current = parse_int_text(values.get("players_current")) if players_current is None else players_current
            players_max = parse_int_text(values.get("players_max")) if players_max is None else players_max
            parsed_presence = parse_bool_text(values.get("presence_detected"))
            presence_detected = (
                parsed_presence
                if parsed_presence is not None
                else players_current is not None
                and players_current > 0
            )
            state = {
                "target_key": target_key,
                "target_key_kind": target_key_kind,
                "alias_target_key": key_metadata["alias_target_key"],
                "exact_target_key": key_metadata["exact_target_key"],
                "source_target_key": key_metadata["source_target_key"],
                "instance": instance,
                "map": game_map,
                "query_port": query_port,
                "status": values.get("status", "unknown"),
                "current_map": values.get("current_map"),
                "players": values.get("players"),
                "players_current": players_current,
                "players_max": players_max,
                "error": values.get("error"),
                "detection_source": values.get("detection_source") or "gamedig_ase_query",
                "query_sample_kind": "aggregate_player_count",
                "query_presence_eligible": target_key_kind == "exact",
                "last_query_utc": current_tick_utc,
                "presence_detected": presence_detected,
                "last_presence_detected_utc": None,
                "evidence_classification": (
                    "passive_monitor_metadata_non_evidence"
                    if target_key_kind == "exact"
                    else "passive_alias_presence_metadata_non_evidence"
                ),
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
                **passive_process_control_metadata(values.get("process_control")),
            }
            if presence_detected:
                state["last_presence_detected_utc"] = current_tick_utc
            if target_key_kind == "exact":
                metadata["query_state_by_instance"][instance] = state
                metadata["query_state_by_target"][target_key] = state
            else:
                state["alias_presence_metadata_only"] = True
                metadata["query_state_alias_by_instance"][instance] = state
                metadata["query_state_by_alias"][target_key] = state
            continue
        if event == "query_warning":
            instance = values.get("instance")
            if not instance:
                continue
            game_map = values.get("map") or "unknown"
            query_port = values.get("query_port") or ""
            key_metadata = monitor_target_key_metadata(
                values,
                instance=instance,
                game_map=game_map,
                query_port=query_port,
                alias_to_exact_target=alias_to_exact_target,
            )
            target_key = str(key_metadata["target_key"])
            target_key_kind = str(key_metadata["target_key_kind"])
            query_port = str(key_metadata["query_port"] or "")
            default_state = {
                "target_key": target_key,
                "target_key_kind": target_key_kind,
                "alias_target_key": key_metadata["alias_target_key"],
                "exact_target_key": key_metadata["exact_target_key"],
                "source_target_key": key_metadata["source_target_key"],
                "instance": instance,
                "map": game_map,
                "query_port": query_port,
                "status": "unknown",
                "detection_source": values.get("detection_source") or "gamedig_ase_query",
                "query_sample_kind": "aggregate_player_count",
                "query_presence_eligible": target_key_kind == "exact",
                "last_query_utc": current_tick_utc,
                "presence_detected": False,
                "evidence_classification": (
                    "passive_monitor_metadata_non_evidence"
                    if target_key_kind == "exact"
                    else "passive_alias_presence_metadata_non_evidence"
                ),
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
                **passive_process_control_metadata(values.get("process_control")),
            }
            state_bucket = (
                metadata["query_state_by_target"]
                if target_key_kind == "exact"
                else metadata["query_state_by_alias"]
            )
            state = state_bucket.setdefault(target_key, default_state)
            state["last_warning_rc"] = parse_int_text(values.get("rc"))
            state["last_warning_utc"] = current_tick_utc
            if target_key_kind == "exact":
                metadata["query_state_by_instance"][instance] = state
            else:
                state["alias_presence_metadata_only"] = True
                metadata["query_state_alias_by_instance"][instance] = state
            continue
        if event == "player_presence_detected":
            instance = values.get("instance")
            if not instance:
                continue
            game_map = values.get("map") or "unknown"
            query_port = values.get("query_port") or ""
            key_metadata = monitor_target_key_metadata(
                values,
                instance=instance,
                game_map=game_map,
                query_port=query_port,
                alias_to_exact_target=alias_to_exact_target,
            )
            target_key = str(key_metadata["target_key"])
            target_key_kind = str(key_metadata["target_key_kind"])
            query_port = str(key_metadata["query_port"] or "")
            default_state = {
                "target_key": target_key,
                "target_key_kind": target_key_kind,
                "alias_target_key": key_metadata["alias_target_key"],
                "exact_target_key": key_metadata["exact_target_key"],
                "source_target_key": key_metadata["source_target_key"],
                "instance": instance,
                "map": game_map,
                "query_port": query_port,
                "status": (
                    "presence_detected_without_query_state"
                    if target_key_kind == "exact"
                    else "alias_presence_detected_without_exact_query_state_metadata_only"
                ),
                "detection_source": values.get("detection_source") or "gamedig_ase_query",
                "query_sample_kind": "aggregate_player_count",
                "query_presence_eligible": target_key_kind == "exact",
                "last_query_utc": current_tick_utc if target_key_kind == "exact" else None,
                "evidence_classification": (
                    "passive_monitor_metadata_non_evidence"
                    if target_key_kind == "exact"
                    else "passive_alias_presence_metadata_non_evidence"
                ),
                "approved_runtime_evidence": False,
                "ready": False,
                "readiness_gate": "none",
                **passive_process_control_metadata(values.get("process_control")),
            }
            state_bucket = (
                metadata["query_state_by_target"]
                if target_key_kind == "exact"
                else metadata["query_state_by_alias"]
            )
            state = state_bucket.setdefault(target_key, default_state)
            state["map"] = state.get("map") or values.get("map")
            state["query_port"] = state.get("query_port") or query_port
            state["target_key"] = target_key
            state["target_key_kind"] = target_key_kind
            state["query_presence_eligible"] = target_key_kind == "exact"
            state["presence_detected"] = True
            state["last_presence_detected_utc"] = current_tick_utc
            state["detection_source"] = values.get("detection_source") or state.get(
                "detection_source"
            )
            state["approved_runtime_evidence"] = False
            state["ready"] = False
            state["readiness_gate"] = "none"
            state.update(passive_process_control_metadata(values.get("process_control")))
            if target_key_kind == "exact":
                metadata["query_state_by_instance"][instance] = state
            else:
                state["alias_presence_metadata_only"] = True
                metadata["query_state_alias_by_instance"][instance] = state
            continue
        if event == "observer_tail":
            instance = values.get("instance")
            if not instance:
                continue
            game_map = values.get("map") or "unknown"
            query_port = values.get("query_port") or ""
            key_metadata = monitor_target_key_metadata(
                values,
                instance=instance,
                game_map=game_map,
                query_port=query_port,
                alias_to_exact_target=alias_to_exact_target,
            )
            target_key = str(key_metadata["target_key"])
            target_key_kind = str(key_metadata["target_key_kind"])
            tail_event = {
                "line_number": line_count,
                "utc": current_tick_utc,
                "target_key": target_key,
                "target_key_kind": target_key_kind,
                "alias_target_key": key_metadata["alias_target_key"],
                "exact_target_key": key_metadata["exact_target_key"],
                "source_target_key": key_metadata["source_target_key"],
                "instance": instance,
                "map": game_map,
                "query_port": str(key_metadata["query_port"] or ""),
                "status": values.get("status", "unknown"),
                "scan_lines": parse_int_text(values.get("scan_lines")),
                "limit": parse_int_text(values.get("limit")),
                "matched_lines": parse_int_text(values.get("lines")),
                "observer_gate_lines": parse_int_text(values.get("observer_gate_lines")) or 0,
                "raw_observer_event_lines": parse_int_text(
                    values.get("raw_observer_event_lines")
                )
                or 0,
                "accepted_observer_event_triplet_candidate_lines": parse_int_text(
                    values.get("accepted_observer_event_triplet_candidate_lines")
                )
                or 0,
                "rejected_observer_event_line_count": parse_int_text(
                    values.get("rejected_observer_event_line_count")
                )
                or 0,
                "check_join_rejected_start_candidate_lines": parse_int_text(
                    values.get("check_join_rejected_start_candidate_lines")
                )
                or 0,
                "superseded_handle_new_player_rejected_start_lines": parse_int_text(
                    values.get("superseded_handle_new_player_rejected_start_lines")
                )
                or 0,
                "diagnostic_only_lines": parse_int_text(values.get("diagnostic_only_lines")) or 0,
                "raw_event_roles": split_csv_text(values.get("raw_event_roles")),
                "event_roles": split_csv_text(values.get("event_roles")),
                "latest_raw_observer_event_role": values.get("latest_raw_observer_event_role")
                or "none",
                "latest_observer_event_role": values.get("latest_observer_event_role")
                or "none",
                "lifecycle_active_candidate": parse_bool_text(
                    values.get("lifecycle_active_candidate")
                ),
                "complete_triplet_candidate": parse_bool_text(
                    values.get("complete_triplet_candidate")
                ),
                "classification": values.get("classification"),
                "observer_event_role_policy": values.get("observer_event_role_policy")
                or "legacy_monitor_tail_roles",
                "tail_scope": values.get("tail_scope") or values.get("observer_tail") or "per_target",
                "linger_after_detect": parse_int_text(values.get("linger_after_detect")),
                "linger_active": parse_bool_text(values.get("linger_active")),
                "linger_until_utc": values.get("linger_until_utc")
                if values.get("linger_until_utc") not in (None, "none")
                else None,
                **passive_metadata_fields(
                    values,
                    evidence_classification="passive_tail_non_evidence",
                ),
            }
            metadata["observer_tail_events"].append(tail_event)
            if target_key_kind == "exact":
                metadata["observer_tail_by_target"][target_key] = tail_event
            else:
                metadata["observer_tail_by_alias"][target_key] = tail_event
            continue
        if event == "observer":
            record_monitor_observer_line(
                metadata,
                line=line,
                values=values,
                current_tick_utc=current_tick_utc,
                alias_to_exact_target=alias_to_exact_target,
            )
            continue
        if event in {
            "player_presence_linger_start",
            "player_presence_linger_extend",
            "player_presence_linger_complete",
        }:
            target_keys = event_target_keys(
                values,
                instance_to_target_keys=instance_to_target_keys,
            )
            linger_event = {
                "event": event,
                "line_number": line_count,
                "utc": current_tick_utc,
                "seconds": parse_int_text(values.get("seconds")),
                "until_utc": values.get("until_utc"),
                "detected_instances": split_csv_text(values.get("detected_instances")),
                "target_keys": target_keys,
                "observer_tail": values.get("observer_tail") or "per_target",
                "linger_scope": "per_target",
                **passive_metadata_fields(
                    values,
                    evidence_classification="passive_linger_metadata_non_evidence",
                ),
            }
            metadata["linger_events"].append(linger_event)
            for target_key in target_keys:
                metadata["linger_by_target"].setdefault(target_key, []).append(linger_event)
            continue
        if event in {"passive_snapshot_captured", "passive_snapshot_failed"}:
            metadata["snapshot_events"].append(
                {
                    "event": event,
                    "line_number": line_count,
                    "output_dir": values.get("output_dir"),
                    "detected_instances": values.get("detected_instances"),
                    "detected_target_keys": split_csv_text(values.get("detected_target_keys")),
                    "snapshot_sequence": parse_int_text(values.get("snapshot_sequence")),
                    "snapshot_target_count": parse_int_text(values.get("snapshot_target_count")),
                    "snapshot_trigger_policy": values.get("snapshot_trigger_policy")
                    or "legacy_global_first_detection",
                    "utc": current_tick_utc,
                    "approved_runtime_evidence": False,
                    "ready": False,
                    "readiness_gate": "none",
                    **passive_process_control_metadata(values.get("process_control")),
                }
            )
    metadata["line_count"] = line_count
    apply_monitor_observer_tail_corrections(metadata)
    return metadata


def copy_target_log(
    *,
    log_root: Path,
    output_dir: Path,
    target: dict[str, str],
    allow_server_path: bool,
) -> dict[str, Any]:
    instance = target["instance"]
    target_key = target_key_from_target(target)
    source = resolve_input(
        log_root / instance / "Obelisk.log",
        allow_server_path=allow_server_path,
        label=f"{instance} Obelisk log",
    )
    copied = output_dir / f"{instance}-{target['map']}-Obelisk.log"
    entry: dict[str, Any] = {
        "target_key": target_key,
        "instance": instance,
        "map": target["map"],
        "query_port": target["query_port"],
        "source_path": str(source),
        "copied_path": str(copied),
        "copy_status": "missing",
        "source_kind": "passive_snapshot",
        "ready_scope": "passive_snapshot_only",
        "approved_runtime_evidence": False,
        "approved_evidence_claim": "none",
        "ready": False,
        "evidence_classification": "passive_snapshot_non_evidence",
        "promotion_blockers": ["passive_snapshot_not_approved_runtime_evidence"],
        "diagnostics": empty_diagnostics(),
        "observer_event_triage": empty_diagnostics()["observer_event_triage"],
        "diagnostic_only_non_evidence": False,
    }
    if not source.is_file():
        entry["blockers"] = ["source_log_missing"]
        return entry

    shutil.copy2(source, copied)
    entry.update(
        {
            "copy_status": "copied",
            "source_sha256": sha256_file(source),
            "copied_sha256": sha256_file(copied),
            "copied_size": copied.stat().st_size,
            "analyzer": run_analyzer(copied),
        }
    )
    summary = entry["analyzer"].get("summary") or {}
    module = (summary.get("modules") or {}).get("player_principal_lifecycle") or {}
    entry["counts"] = {
        "accepted": int_count(module.get("accepted_count", 0)),
        "rejected": int_count(module.get("rejected_count", 0)),
        "diagnostic_candidates": int_count(module.get("diagnostic_candidate_count", 0)),
    }
    entry["diagnostics"] = diagnostics_from_module(module, entry["counts"])
    entry["observer_event_triage"] = entry["diagnostics"]["observer_event_triage"]
    entry["diagnostic_only_non_evidence"] = entry["diagnostics"]["only_non_evidence"]
    entry["readiness_gate"] = "none"
    return entry


def copy_monitor_log(
    path: Path | None,
    output_dir: Path,
    *,
    allow_server_path: bool,
    expected_targets: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    if path is None:
        return None
    source = resolve_input(path, allow_server_path=allow_server_path, label="passive monitor log")
    copied = output_dir / "passive-monitor.log"
    if not source.is_file():
        return {
            "source_path": str(source),
            "copy_status": "missing",
            "blockers": ["source_log_missing"],
            "approved_runtime_evidence": False,
            "ready": False,
        }
    shutil.copy2(source, copied)
    return {
        "source_path": str(source),
        "copied_path": str(copied),
        "copy_status": "copied",
        "source_sha256": sha256_file(source),
        "copied_sha256": sha256_file(copied),
        "copied_size": copied.stat().st_size,
        "metadata": parse_monitor_log_metadata(copied, expected_targets=expected_targets),
        "approved_runtime_evidence": False,
        "ready": False,
    }


def passive_organic_detection_summary(
    *,
    targets: list[dict[str, Any]],
    monitor: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = monitor.get("metadata") if isinstance(monitor, dict) else None
    latest_tick_utc = metadata.get("latest_tick_utc") if isinstance(metadata, dict) else None
    query_state_by_alias = (
        metadata.get("query_state_by_alias") if isinstance(metadata, dict) else {}
    )
    if not isinstance(query_state_by_alias, dict):
        query_state_by_alias = {}
    alias_presence_targets = sorted(
        key
        for key, state in query_state_by_alias.items()
        if isinstance(key, str)
        and isinstance(state, dict)
        and state.get("presence_detected") is True
    )
    detected_targets = sorted(
        target["target_key"]
        for target in targets
        if isinstance(target.get("query_state"), dict)
        and target["query_state"].get("presence_detected") is True
        and target["query_state"].get("target_key_kind") == "exact"
    )
    return {
        "schema": "obelisk.passive-organic-player-detection.v1",
        "source": "passive_monitor_log" if isinstance(metadata, dict) else "not_reported",
        "detection_scope": "aggregate_player_count_only",
        "query_state_key": "target_key",
        "query_state_exact_key_format": "INSTANCE:MAP:QUERY_PORT",
        "alias_query_state_key": "alias_target_key",
        "alias_presence_policy": "metadata_only_excluded_from_lifecycle_evidence",
        "target_count": len(targets),
        "detected_target_count": len(detected_targets),
        "detected_targets": detected_targets,
        "alias_presence_metadata_only_target_count": len(alias_presence_targets),
        "alias_presence_metadata_only_targets": alias_presence_targets,
        "latest_tick_utc": latest_tick_utc if isinstance(latest_tick_utc, str) else None,
        "approved_runtime_evidence": False,
        "ready": False,
        "evidence_classification": "passive_monitor_metadata_non_evidence",
    }


def passive_wait_metadata_summary(monitor: dict[str, Any] | None) -> dict[str, Any]:
    metadata = monitor.get("metadata") if isinstance(monitor, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
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
        "schema": "obelisk.player-principal-passive-wait-metadata.v1",
        "source": "passive_monitor_log" if metadata else "not_reported",
        "wait_scope": "metadata_only",
        "observer_tail_scope": "per_target",
        "observer_tail_by_target": observer_tail_by_target,
        "observer_tail_by_alias": observer_tail_by_alias,
        "linger_by_target": linger_by_target,
        "linger_events": linger_events,
        "process_control": "none",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_wait_metadata_non_evidence",
    }


def query_presence_detected(state: dict[str, Any]) -> bool:
    players_current = int_or_none(state.get("players_current"))
    return state.get("presence_detected") is True or (
        players_current is not None and players_current > 0
    )


def query_status_token(value: Any) -> str:
    return safe_diagnostic_token(value) or "not_reported"


def sanitized_drift_reason_for_summary(value: Any) -> dict[str, Any] | None:
    drift = sanitized_rejected_drift(value)
    if drift is None:
        return None
    summary: dict[str, Any] = {
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
        "readiness_gate": "none",
        "process_control": "none",
    }
    return summary


def passive_server_activity_summary(targets: list[dict[str, Any]]) -> dict[str, Any]:
    active_targets: list[str] = []
    players_detected_targets: list[str] = []
    players_current_by_target: dict[str, int | None] = {}
    target_summaries: dict[str, dict[str, Any]] = {}
    latest_drift_by_target: dict[str, dict[str, Any]] = {}
    latest_drift_by_lifecycle_target: dict[str, dict[str, Any]] = {
        target: {} for target in REJECTED_DRIFT_TARGETS
    }
    exact_target_count = 0

    for target in targets:
        target_key = str(
            target.get("target_key")
            or target_key_for(
                str(target.get("instance", "unknown")),
                str(target.get("map", "unknown")),
                str(target.get("query_port") or ""),
            )
        )
        query_state = target.get("query_state")
        if not isinstance(query_state, dict):
            query_state = query_state_default(
                {
                    "instance": str(target.get("instance", "unknown")),
                    "map": str(target.get("map", "unknown")),
                    "query_port": str(target.get("query_port") or ""),
                }
            )
        query_presence_eligible = query_state.get("target_key_kind") == "exact"
        if query_presence_eligible:
            exact_target_count += 1
        status = query_status_token(query_state.get("status"))
        server_active = query_presence_eligible and status == "ok"
        players_current = int_or_none(query_state.get("players_current"))
        players_detected = query_presence_eligible and query_presence_detected(query_state)
        if server_active:
            active_targets.append(target_key)
        if players_detected:
            players_detected_targets.append(target_key)
        players_current_by_target[target_key] = players_current

        diagnostics = target.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}
        raw_drift_by_lifecycle_target = sanitized_rejected_drift_by_lifecycle_target(
            diagnostics.get("latest_rejected_drift_by_lifecycle_target")
        )
        drift_reason_by_lifecycle_target: dict[str, Any] = {}
        for lifecycle_target in REJECTED_DRIFT_TARGETS:
            reason = sanitized_drift_reason_for_summary(
                raw_drift_by_lifecycle_target.get(lifecycle_target)
            )
            if reason is None:
                continue
            drift_reason_by_lifecycle_target[lifecycle_target] = reason
            latest_drift_by_lifecycle_target[lifecycle_target][target_key] = reason
        if drift_reason_by_lifecycle_target:
            latest_drift_by_target[target_key] = drift_reason_by_lifecycle_target

        target_summaries[target_key] = {
            "target_key": target_key,
            "instance": str(target.get("instance", "unknown")),
            "map": str(target.get("map", "unknown")),
            "query_port": str(target.get("query_port") or ""),
            "query_status": status,
            "query_presence_eligible": query_presence_eligible,
            "server_active": server_active,
            "players_detected": players_detected,
            "players_current": players_current,
            "latest_rejected_drift_reason_by_lifecycle_target": drift_reason_by_lifecycle_target,
            "evidence_classification": "passive_server_activity_summary_non_evidence",
            "approved_runtime_evidence": False,
            "ready": False,
            "readiness_gate": "none",
            "process_control": "none",
        }

    active_targets = sorted(active_targets)
    players_detected_targets = sorted(players_detected_targets)
    known_player_total = sum(
        value for value in players_current_by_target.values() if isinstance(value, int)
    )
    latest_drift_by_lifecycle_target = {
        target: values
        for target, values in latest_drift_by_lifecycle_target.items()
        if values
    }
    both_servers_active = exact_target_count == 2 and len(active_targets) == 2
    return {
        "schema": "obelisk.player-principal-passive-server-activity-summary.v1",
        "summary_scope": "offline_passive_snapshot_metadata_only",
        "target_count": len(targets),
        "exact_query_target_count": exact_target_count,
        "active_target_count": len(active_targets),
        "active_targets": active_targets,
        "all_expected_servers_active": (
            exact_target_count > 0 and len(active_targets) == exact_target_count
        ),
        "both_servers_active": both_servers_active,
        "players_detected": bool(players_detected_targets),
        "players_detected_target_count": len(players_detected_targets),
        "targets_with_players_detected": players_detected_targets,
        "players_current_by_target": players_current_by_target,
        "players_current_known_total": known_player_total,
        "player_detection_scope": "aggregate_player_count_only",
        "latest_rejected_drift_reason_by_snapshot_target": latest_drift_by_target,
        "latest_rejected_drift_reason_by_lifecycle_target": latest_drift_by_lifecycle_target,
        "targets": target_summaries,
        "evidence_classification": "passive_server_activity_summary_non_evidence",
        "approved_runtime_evidence": False,
        "ready": False,
        "readiness_gate": "none",
        "process_control": "none",
    }


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
    if priority == "accepted_observer_event_triplet_candidate":
        hint_id = (
            "prepare_fresh_operator_approved_evidence_request_from_triplet_candidate"
            if complete_observer_event_targets
            else "carry_partial_triplet_candidate_to_next_passive_review"
        )
        focus = (
            "complete_triplet_candidate_request_preflight"
            if complete_observer_event_targets
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
            "details.rejected_drift_count",
        ]
    elif priority == "repeated_diagnostics_only":
        hint_id = "compare_passive_diagnostic_counts_before_request"
        focus = "diagnostic_candidate_count_tracking"
        input_fields = [
            "targets",
            "diagnostic_only_targets",
            "details.candidate_count",
            "details.log_budget_reached",
        ]
    else:
        hint_id = "wait_for_passive_observer_activity_metadata"
        focus = "no_passive_observer_activity"
        input_fields = ["details.candidate_count"]
    return [
        {
            "schema": RUNNER_ACTION_HINT_SCHEMA,
            "order": 1,
            "id": hint_id,
            "focus": focus,
            "reason_kind": reason_kind,
            "target_keys": sorted(dict.fromkeys(targets)),
            "lifecycle_targets": sorted(dict.fromkeys(lifecycle_targets)),
            "accepted_observer_event_targets": sorted(
                dict.fromkeys(accepted_observer_event_targets)
            ),
            "complete_observer_event_targets": sorted(
                dict.fromkeys(complete_observer_event_targets)
            ),
            "rejected_drift_targets": sorted(dict.fromkeys(rejected_drift_targets)),
            "diagnostic_only_targets": sorted(dict.fromkeys(diagnostic_only_targets)),
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
    priority: str,
    reason_kind: str,
    next_reason: str,
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
        "summary_scope": "passive_snapshot_capture_metadata_only",
        "priority": priority,
        "runner_priority_rank": passive_runner_priority_rank(priority),
        "runner_focus": runner_hints[0]["focus"],
        "reason_kind": reason_kind,
        "next_reason": next_reason,
        "classification_context": "capture_manifest",
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


def passive_actionability_summary(
    *,
    diagnostics: dict[str, Any],
    server_activity: dict[str, Any],
) -> dict[str, Any]:
    observer_triage = diagnostics.get("observer_event_triage")
    if not isinstance(observer_triage, dict):
        observer_triage = {}
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
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="complete_accepted_observer_event_triplet_candidate_present",
            next_reason="complete_accepted_observer_event_triplet_candidate_present_non_evidence",
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
        return passive_actionability_payload(
            priority="accepted_observer_event_triplet_candidate",
            reason_kind="partial_accepted_observer_event_triplet_candidate_present",
            next_reason="partial_accepted_observer_event_triplet_candidate_present_non_evidence",
            targets=accepted_targets,
            targets_with_players_detected=[
                target for target in accepted_targets if target in players_detected_targets
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
            priority="rejected_lifecycle_property_FName_drift",
            reason_kind="repeated_lifecycle_property_FName_drift",
            next_reason=(
                "repeated_lifecycle_property_FName_drift_with_player_presence_non_evidence"
                if active_rejected_targets
                else "repeated_lifecycle_property_FName_drift_non_evidence"
            ),
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
            priority="repeated_diagnostics_only",
            reason_kind="repeated_diagnostic_candidates",
            next_reason="repeated_diagnostic_candidates_without_accepted_events_or_rejected_drift_non_evidence",
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
        priority="no_passive_observer_activity",
        reason_kind="no_passive_observer_activity",
        next_reason="no_passive_observer_activity_non_evidence",
        details={"candidate_count": candidate_count},
    )


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
    diagnostics: dict[str, Any],
    server_activity: dict[str, Any],
    wait_metadata: dict[str, Any],
) -> dict[str, Any]:
    observer_triage = diagnostics.get("observer_event_triage")
    if not isinstance(observer_triage, dict):
        observer_triage = {}
    players_current_by_target = server_activity.get("players_current_by_target")
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
    players_detected_targets = str_list(server_activity.get("targets_with_players_detected"))
    diagnostic_only_targets = str_list(
        diagnostics.get("diagnostic_only_non_evidence_targets")
    )
    accepted_targets = str_list(
        observer_triage.get("targets_with_accepted_observer_event_triplet_candidates")
    )
    complete_triplet_targets = str_list(
        observer_triage.get("targets_with_complete_observer_event_triplet_candidate")
    )
    partial_role_targets = sorted(
        target for target in accepted_targets if target not in set(complete_triplet_targets)
    )
    observer_tail_by_target = wait_metadata.get("observer_tail_by_target")
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
    accepted_count = int_count(
        observer_triage.get("accepted_observer_event_triplet_candidate_count")
    )
    rejected_count = int_count(observer_triage.get("rejected_observer_event_line_count"))
    diagnostic_count = int_count(observer_triage.get("diagnostic_only_line_count"))
    no_observer_activity = accepted_count == 0 and rejected_count == 0 and diagnostic_count == 0
    run_id = source_root.name or str(source_root)
    run_id_matches_closure_pattern = CLOSURE_COMPATIBLE_RUN_ID_RE.fullmatch(run_id) is not None
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

    return {
        "schema": PASSIVE_CLOSURE_SUMMARY_SCHEMA,
        "summary_scope": "passive_snapshot_capture_metadata_only",
        "source_root": str(source_root),
        "source_root_role": "passive_snapshot_root_operational_context_only",
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
        "closure_reasons": sorted(dict.fromkeys(closure_reasons)),
        "players_detected_targets": players_detected_targets,
        "zero_player_targets": zero_player_targets,
        "unknown_player_count_targets": unknown_player_count_targets,
        "observer_gate_only_targets": gate_only_targets,
        "diagnostic_only_targets": diagnostic_only_targets,
        "partial_observer_event_role_targets": partial_role_targets,
        "missing_observer_event_roles": str_list(
            observer_triage.get("missing_observer_event_triplet_roles"),
            allowed=REQUIRED_OBSERVER_EVENT_ROLES,
        ),
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


def build_manifest(args: argparse.Namespace, output_dir: Path) -> dict[str, Any]:
    log_root = resolve_input(args.log_root, allow_server_path=args.allow_server_path, label="log root")
    targets = [
        copy_target_log(
            log_root=log_root,
            output_dir=output_dir,
            target=target,
            allow_server_path=args.allow_server_path,
        )
        for target in args.target
    ]
    monitor = copy_monitor_log(
        args.monitor_log,
        output_dir,
        allow_server_path=args.allow_server_path,
        expected_targets=args.target,
    )
    raw_query_state_by_instance = (
        ((monitor or {}).get("metadata") or {}).get("query_state_by_instance", {})
        if isinstance(monitor, dict)
        else {}
    )
    raw_query_state_by_instance = (
        dict(raw_query_state_by_instance) if isinstance(raw_query_state_by_instance, dict) else {}
    )
    raw_query_state_by_target = (
        ((monitor or {}).get("metadata") or {}).get("query_state_by_target", {})
        if isinstance(monitor, dict)
        else {}
    )
    raw_query_state_by_target = (
        dict(raw_query_state_by_target) if isinstance(raw_query_state_by_target, dict) else {}
    )
    raw_query_state_by_alias = (
        ((monitor or {}).get("metadata") or {}).get("query_state_by_alias", {})
        if isinstance(monitor, dict)
        else {}
    )
    raw_query_state_by_alias = (
        dict(raw_query_state_by_alias) if isinstance(raw_query_state_by_alias, dict) else {}
    )
    query_state_by_instance: dict[str, Any] = {}
    query_state_by_target: dict[str, Any] = {}
    query_state_by_alias: dict[str, Any] = {
        key: sanitized_alias_query_state(state, key)
        for key, state in raw_query_state_by_alias.items()
        if isinstance(key, str) and not is_exact_target_key(key)
    }
    query_state_alias_by_instance: dict[str, Any] = {
        str(state["instance"]): state
        for state in query_state_by_alias.values()
        if isinstance(state.get("instance"), str)
    }
    for target in targets:
        target_key = target["target_key"]
        target["query_state"] = (
            exact_query_state_for_target(raw_query_state_by_target.get(target_key), target)
            or exact_query_state_for_target(raw_query_state_by_instance.get(target["instance"]), target)
            or query_state_default(
                {
                    "instance": target["instance"],
                    "map": target["map"],
                    "query_port": target["query_port"],
                }
            )
        )
        target["query_state"]["approved_runtime_evidence"] = False
        target["query_state"]["ready"] = False
        target["query_state"]["readiness_gate"] = "none"
        if target["query_state"].get("target_key_kind") == "exact":
            query_state_by_target[target_key] = target["query_state"]
            query_state_by_instance[target["instance"]] = target["query_state"]
        else:
            alias_key = target_alias_key_from_target(target)
            alias_state = sanitized_alias_query_state(target["query_state"], alias_key)
            target["query_state"] = alias_state
            query_state_by_alias[alias_key] = alias_state
            query_state_alias_by_instance[target["instance"]] = alias_state
    diagnostics = aggregate_diagnostics(targets)
    organic_detection = passive_organic_detection_summary(targets=targets, monitor=monitor)
    passive_wait_metadata = passive_wait_metadata_summary(monitor)
    server_activity = passive_server_activity_summary(targets)
    closure_summary = passive_closure_summary(
        source_root=output_dir,
        diagnostics=diagnostics,
        server_activity=server_activity,
        wait_metadata=passive_wait_metadata,
    )
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "captured_at_utc": utc_now(),
        "target_count": len(targets),
        "targets": targets,
        "monitor_log": monitor,
        "query_state_by_instance": query_state_by_instance,
        "query_state_by_target": query_state_by_target,
        "query_state_by_alias": query_state_by_alias,
        "query_state_alias_by_instance": query_state_alias_by_instance,
        "query_state_key_policy": (
            "exact target presence requires INSTANCE:MAP:QUERY_PORT; alias presence is "
            "metadata-only and excluded from lifecycle evidence"
        ),
        "diagnostics": diagnostics,
        "organic_detection": organic_detection,
        "passive_wait_metadata": passive_wait_metadata,
        "passive_server_activity_summary": server_activity,
        "passive_closure_summary": closure_summary,
        "passive_actionability": passive_actionability_summary(
            diagnostics=diagnostics,
            server_activity=server_activity,
        ),
        "source_kind": "passive_snapshot",
        "ready_scope": "passive_snapshot_only",
        "approved_runtime_evidence": False,
        "approved_evidence_claim": "none",
        "ready": False,
        "readiness_gate": "none",
        "evidence_classification": "passive_snapshot_non_evidence",
        "promotion_blockers": ["passive_snapshot_not_approved_runtime_evidence"],
        "non_claims": [
            "passive copied-log snapshot only",
            "approved_runtime_evidence remains false",
            "does not start, stop, restart, edit markers, or call LinuxGSM monitor/details",
            "does not promote player identity, runtime readiness, public SDK readiness, or v1 completion",
            "diagnostic candidate lines remain non-evidence until approved evidence checkers accept a copied sibling-set bundle",
            "accepted observer event triplet candidates in passive snapshots remain non-evidence until approved evidence checkers accept a copied sibling-set bundle",
            "GameDig aggregate player-count presence is organic detection metadata only, not lifecycle evidence",
            "linger and observer-tail records are wait-only metadata with process_control=none",
            "passive server activity summaries contain aggregate query counts and sanitized diagnostic drift reasons only",
            "passive runner action hints are non-authorizing triage hints only",
            "passive closure summaries remain no-progress/no-readiness non-evidence and cannot be used as closure roots",
        ],
    }
    blockers = sorted(
        {
            blocker
            for target in targets
            for blocker in target.get("blockers", [])
        }
    )
    manifest["blockers"] = blockers
    manifest["all_logs_copied"] = all(target.get("copy_status") == "copied" for target in targets)
    return manifest


def main() -> int:
    args = parse_args()
    output_dir = prepare_output_dir(args.output_dir)
    manifest = build_manifest(args, output_dir)
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "ready": False, "all_logs_copied": manifest["all_logs_copied"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
