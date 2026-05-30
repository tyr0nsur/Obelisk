#!/usr/bin/env python3
"""Validate controlled ChatMessageEvent mode-coverage beta manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA = "obelisk.chat-mode-coverage-window.v1"
ANALYZER_SCHEMA = "obelisk.chat-delivery-log-summary.v1"
DEFAULT_WORKSPACE_ROOT = Path("/servidor/ark/workspace-offline")
DEFAULT_INSTANCE = "arkserver"
DEFAULT_MAP = "Ragnarok"
SUPPORTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-chat-mode-coverage$")
URL_RE = re.compile(r"(?:https?://|discord(?:app)?\.com/(?:api/webhooks|channels)|webhook|token)", re.IGNORECASE)
PRIVACY_RE = re.compile(
    r"(?:"
    r"raw[_ -]?(?:chat|text|message)|"
    r"chat[_ -]?text|message[_ -]?text|"
    r"player[_ -]?(?:id|name|unique)|steam[_ -]?(?:id|name)|eos[_ -]?id|"
    r"sender|character[_ -]?name|tribe[_ -]?(?:id|name)|platform[_ -]?(?:id|user)|"
    r"unique[_ -]?net[_ -]?id|params\s*=\s*0x|function\s*=\s*0x|0x[0-9a-f]{8,}"
    r")",
    re.IGNORECASE,
)
MODE_NAMES = {
    0: "GlobalChat",
    1: "GlobalTribeChat",
    2: "LocalChat",
    3: "AllianceChat",
}
EXPECTED_ENV = {
    "OBELISK_WRAPPER_PROFILE",
    "OBELISK_ENABLE_CHAT_EVENTS",
    "OBELISK_CHAT_EVENTS_BINARY_SHA256",
    "OBELISK_CHAT_EVENTS_DISPATCH_LIMIT",
}
EXPECTED_MARKERS = {
    "enable-process-event-hook",
    "allow-observer-debug-window",
    "allow-experimental-observers",
    "enable-chat-events",
}
TOP_LEVEL_KEYS = {
    "schema",
    "run_id",
    "target",
    "approval",
    "notice",
    "runtime_gates",
    "evidence",
    "checks",
    "claimed_modes",
    "controlled_sends",
}
NESTED_KEYS = {
    "target": {"instance", "map"},
    "approval": {"approved", "window_start_utc", "window_end_utc", "restart_expected", "rollback_defined"},
    "notice": {"sent", "path_label", "time_utc", "sanitized_artifact_sha256"},
    "runtime_gates": {
        "expected_sha256",
        "enabled_env",
        "enabled_markers",
        "disabled_marker_removed",
        "only_loadable_plugin",
    },
    "evidence": {
        "copied_log_path",
        "copied_log_sha256",
        "analyzer_summary_path",
        "complete_window_evidence",
    },
    "checks": {"pre_check", "post_check", "rollback_completed"},
}
CONTROLLED_SEND_KEYS = {
    "mode",
    "mode_name",
    "precondition",
    "planned_send_time_utc",
    "observed_send_time_utc",
    "expected_message_size_bytes",
    "tester_result",
    "correlation",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path, blockers: list[dict[str, str]], label: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        blockers.append({"reason": f"{label}_missing", "detail": str(path)})
        return None
    except OSError as exc:
        blockers.append({"reason": f"{label}_unreadable", "detail": f"{path}: {exc}"})
        return None
    except json.JSONDecodeError as exc:
        blockers.append({"reason": f"{label}_malformed_json", "detail": str(exc)})
        return None
    if not isinstance(payload, dict):
        blockers.append({"reason": f"{label}_not_object", "detail": type(payload).__name__})
        return None
    return payload


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor) if path.is_absolute() else Path()
    parts = path.parts[1:] if path.is_absolute() else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        if not value.endswith("Z"):
            return None
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None


def collect_strings(value: object) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            strings.extend(collect_strings(child))
    elif isinstance(value, list):
        for child in value:
            strings.extend(collect_strings(child))
    elif isinstance(value, str):
        strings.append(value)
    return strings


def add_unknown_key_blockers(payload: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    unknown_top = sorted(set(payload).difference(TOP_LEVEL_KEYS))
    if unknown_top:
        blockers.append({"reason": "manifest_unknown_top_level_keys", "detail": ",".join(unknown_top)})
    for key, expected_keys in NESTED_KEYS.items():
        value = payload.get(key)
        if not isinstance(value, dict):
            continue
        unknown = sorted(set(value).difference(expected_keys))
        if unknown:
            blockers.append({"reason": f"manifest_unknown_{key}_keys", "detail": ",".join(unknown)})
    sends = payload.get("controlled_sends")
    if isinstance(sends, list):
        for index, send in enumerate(sends):
            if isinstance(send, dict):
                unknown = sorted(set(send).difference(CONTROLLED_SEND_KEYS))
                if unknown:
                    blockers.append({"reason": "manifest_unknown_controlled_send_keys", "detail": f"{index}:{','.join(unknown)}"})


def validate_workspace_path(
    raw_path: object,
    *,
    run_id: str,
    workspace_root: Path,
    field: str,
    blockers: list[dict[str, str]],
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        blockers.append({"reason": f"{field}_missing", "detail": field})
        return None
    path = Path(raw_path).expanduser()
    expected_root = (workspace_root / "live-validation-logs" / run_id).resolve()
    resolved = path.resolve()
    if not path.is_absolute():
        blockers.append({"reason": f"{field}_not_absolute", "detail": raw_path})
        return None
    if has_symlink_component(path):
        blockers.append({"reason": f"{field}_is_symlink", "detail": raw_path})
        return None
    if not is_relative_to(resolved, expected_root):
        blockers.append({"reason": f"{field}_outside_run_workspace", "detail": raw_path})
        return None
    if not path.is_file():
        blockers.append({"reason": f"{field}_not_regular_file", "detail": raw_path})
        return None
    return resolved


def validate_manifest(payload: dict[str, Any], manifest_path: Path, *, workspace_root: Path) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    add_unknown_key_blockers(payload, blockers)

    if payload.get("schema") != SCHEMA:
        blockers.append({"reason": "manifest_schema_mismatch", "detail": str(payload.get("schema"))})
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or RUN_ID_RE.fullmatch(run_id) is None:
        blockers.append({"reason": "manifest_run_id_invalid", "detail": str(run_id)})
        run_id = ""

    for value in collect_strings(payload):
        if URL_RE.search(value):
            blockers.append({"reason": "manifest_secret_or_endpoint_string", "detail": "redacted"})
            break
    for value in collect_strings(payload):
        if PRIVACY_RE.search(value):
            blockers.append({"reason": "manifest_privacy_string", "detail": "redacted"})
            break

    target = payload.get("target")
    if not isinstance(target, dict):
        blockers.append({"reason": "manifest_target_missing", "detail": "$.target"})
    else:
        if target.get("instance") != DEFAULT_INSTANCE or target.get("map") != DEFAULT_MAP:
            blockers.append({"reason": "manifest_target_mismatch", "detail": f"{target.get('instance')}/{target.get('map')}"})

    approval = payload.get("approval")
    window_start = window_end = None
    if not isinstance(approval, dict):
        blockers.append({"reason": "manifest_approval_missing", "detail": "$.approval"})
    else:
        for key in ("approved", "restart_expected", "rollback_defined"):
            if approval.get(key) is not True:
                blockers.append({"reason": f"manifest_approval_{key}_not_true", "detail": key})
        window_start = parse_utc(approval.get("window_start_utc"))
        window_end = parse_utc(approval.get("window_end_utc"))
        if window_start is None or window_end is None or window_start >= window_end:
            blockers.append({"reason": "manifest_approval_window_invalid", "detail": "window_start_utc/window_end_utc"})

    notice = payload.get("notice")
    if not isinstance(notice, dict):
        blockers.append({"reason": "manifest_notice_missing", "detail": "$.notice"})
    else:
        if notice.get("sent") is not True:
            blockers.append({"reason": "manifest_notice_not_sent", "detail": "$.notice.sent"})
        if not isinstance(notice.get("path_label"), str) or not notice["path_label"].strip():
            blockers.append({"reason": "manifest_notice_path_label_missing", "detail": "$.notice.path_label"})
        if parse_utc(notice.get("time_utc")) is None:
            blockers.append({"reason": "manifest_notice_time_invalid", "detail": "$.notice.time_utc"})
        if not isinstance(notice.get("sanitized_artifact_sha256"), str) or SHA256_RE.fullmatch(notice["sanitized_artifact_sha256"]) is None:
            blockers.append({"reason": "manifest_notice_digest_invalid", "detail": "$.notice.sanitized_artifact_sha256"})

    gates = payload.get("runtime_gates")
    if not isinstance(gates, dict):
        blockers.append({"reason": "manifest_runtime_gates_missing", "detail": "$.runtime_gates"})
    else:
        if gates.get("expected_sha256") != SUPPORTED_BINARY_SHA256:
            blockers.append({"reason": "manifest_runtime_expected_sha256_mismatch", "detail": str(gates.get("expected_sha256"))})
        if set(gates.get("enabled_env", [])) != EXPECTED_ENV:
            blockers.append({"reason": "manifest_runtime_enabled_env_mismatch", "detail": ",".join(sorted(map(str, gates.get("enabled_env", []))))})
        if set(gates.get("enabled_markers", [])) != EXPECTED_MARKERS:
            blockers.append({"reason": "manifest_runtime_enabled_markers_mismatch", "detail": ",".join(sorted(map(str, gates.get("enabled_markers", []))))})
        if gates.get("disabled_marker_removed") != "disable-plugins":
            blockers.append({"reason": "manifest_runtime_disabled_marker_mismatch", "detail": str(gates.get("disabled_marker_removed"))})
        if gates.get("only_loadable_plugin") != "oChatLogger":
            blockers.append({"reason": "manifest_runtime_plugin_mismatch", "detail": str(gates.get("only_loadable_plugin"))})

    evidence = payload.get("evidence")
    copied_log_path = analyzer_path = None
    if not isinstance(evidence, dict):
        blockers.append({"reason": "manifest_evidence_missing", "detail": "$.evidence"})
    else:
        if evidence.get("complete_window_evidence") is not True:
            blockers.append({"reason": "manifest_incomplete_window_evidence", "detail": "$.evidence.complete_window_evidence"})
        copied_log_path = validate_workspace_path(
            evidence.get("copied_log_path"),
            run_id=run_id,
            workspace_root=workspace_root,
            field="copied_log_path",
            blockers=blockers,
        )
        analyzer_path = validate_workspace_path(
            evidence.get("analyzer_summary_path"),
            run_id=run_id,
            workspace_root=workspace_root,
            field="analyzer_summary_path",
            blockers=blockers,
        )
        recorded_log_sha = evidence.get("copied_log_sha256")
        if not isinstance(recorded_log_sha, str) or SHA256_RE.fullmatch(recorded_log_sha) is None:
            blockers.append({"reason": "manifest_copied_log_sha256_invalid", "detail": "$.evidence.copied_log_sha256"})
        elif copied_log_path is not None and sha256_file(copied_log_path) != recorded_log_sha:
            blockers.append({"reason": "manifest_copied_log_sha256_mismatch", "detail": "$.evidence.copied_log_sha256"})

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        blockers.append({"reason": "manifest_checks_missing", "detail": "$.checks"})
    else:
        if checks.get("pre_check") != "passed":
            blockers.append({"reason": "manifest_pre_check_not_passed", "detail": str(checks.get("pre_check"))})
        if checks.get("post_check") != "passed":
            blockers.append({"reason": "manifest_post_check_not_passed", "detail": str(checks.get("post_check"))})
        if checks.get("rollback_completed") is not True:
            blockers.append({"reason": "manifest_rollback_not_completed", "detail": "$.checks.rollback_completed"})

    claimed_modes = payload.get("claimed_modes")
    if not isinstance(claimed_modes, list) or not claimed_modes:
        blockers.append({"reason": "manifest_claimed_modes_missing", "detail": "$.claimed_modes"})
        claimed_set: set[int] = set()
    else:
        claimed_set = set()
        for mode in claimed_modes:
            if not isinstance(mode, int) or isinstance(mode, bool) or mode not in MODE_NAMES:
                blockers.append({"reason": "manifest_claimed_mode_invalid", "detail": str(mode)})
            else:
                claimed_set.add(mode)

    sends = payload.get("controlled_sends")
    controlled_by_mode: dict[int, dict[str, Any]] = {}
    if not isinstance(sends, list) or not sends:
        blockers.append({"reason": "manifest_controlled_sends_missing", "detail": "$.controlled_sends"})
    else:
        for index, send in enumerate(sends):
            if not isinstance(send, dict):
                blockers.append({"reason": "manifest_controlled_send_not_object", "detail": str(index)})
                continue
            mode = send.get("mode")
            if not isinstance(mode, int) or isinstance(mode, bool) or mode not in MODE_NAMES:
                blockers.append({"reason": "manifest_controlled_send_mode_invalid", "detail": str(index)})
                continue
            controlled_by_mode[mode] = send
            if send.get("mode_name") != MODE_NAMES[mode]:
                blockers.append({"reason": "manifest_controlled_send_mode_name_mismatch", "detail": str(mode)})
            if send.get("precondition") != "confirmed":
                blockers.append({"reason": "manifest_controlled_send_precondition_not_confirmed", "detail": str(mode)})
            if send.get("tester_result") != "accepted_by_game":
                blockers.append({"reason": "manifest_controlled_send_not_accepted_by_game", "detail": str(mode)})
            if send.get("correlation") != "controlled_quiet_window":
                blockers.append({"reason": "manifest_controlled_send_correlation_not_controlled", "detail": str(mode)})
            expected_size = send.get("expected_message_size_bytes")
            if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 1:
                blockers.append({"reason": "manifest_controlled_send_message_size_invalid", "detail": str(mode)})
            planned = parse_utc(send.get("planned_send_time_utc"))
            observed = parse_utc(send.get("observed_send_time_utc"))
            if planned is None or observed is None:
                blockers.append({"reason": "manifest_controlled_send_time_invalid", "detail": str(mode)})
            elif window_start is not None and window_end is not None and not (window_start <= planned <= window_end and window_start <= observed <= window_end):
                blockers.append({"reason": "manifest_controlled_send_time_outside_window", "detail": str(mode)})

    missing_controlled = sorted(claimed_set.difference(controlled_by_mode))
    if missing_controlled:
        blockers.append({"reason": "manifest_missing_controlled_send_for_claimed_mode", "detail": ",".join(map(str, missing_controlled))})

    analyzer_payload = load_json(analyzer_path, blockers, "analyzer_summary") if analyzer_path is not None else None
    if analyzer_payload is not None:
        validate_analyzer(payload, analyzer_payload, controlled_by_mode, claimed_set, blockers)

    return {
        "schema": "obelisk.chat-mode-coverage-manifest-result.v1",
        "manifest": str(manifest_path),
        "run_id": run_id,
        "status": "blocked" if blockers else "accepted",
        "claimed_modes": sorted(claimed_set),
        "blockers": blockers,
    }


def validate_analyzer(
    manifest: dict[str, Any],
    analyzer: dict[str, Any],
    controlled_by_mode: dict[int, dict[str, Any]],
    claimed_modes: set[int],
    blockers: list[dict[str, str]],
) -> None:
    evidence = manifest.get("evidence", {})
    gates = manifest.get("runtime_gates", {})
    if analyzer.get("schema") != ANALYZER_SCHEMA:
        blockers.append({"reason": "analyzer_schema_mismatch", "detail": str(analyzer.get("schema"))})
    gate = analyzer.get("promotion_gate")
    if not isinstance(gate, dict) or gate.get("ready") is not True:
        blockers.append({"reason": "analyzer_promotion_gate_not_ready", "detail": "promotion_gate.ready"})
    if analyzer.get("privacy_leak_line_count") != 0:
        blockers.append({"reason": "analyzer_privacy_leak_count_nonzero", "detail": str(analyzer.get("privacy_leak_line_count"))})
    source = analyzer.get("source")
    if not isinstance(source, dict) or source.get("sha256") != evidence.get("copied_log_sha256"):
        blockers.append({"reason": "analyzer_source_sha256_mismatch", "detail": "$.source.sha256"})
    if analyzer.get("producer_sha256") != [gates.get("expected_sha256")]:
        blockers.append({"reason": "analyzer_producer_sha256_mismatch", "detail": str(analyzer.get("producer_sha256"))})
    accepted_modes: set[int] = set()
    raw_accepted_modes = analyzer.get("accepted_send_modes")
    if not isinstance(raw_accepted_modes, list):
        blockers.append({"reason": "analyzer_accepted_send_modes_missing", "detail": "$.accepted_send_modes"})
    else:
        for mode in raw_accepted_modes:
            if not isinstance(mode, int) or isinstance(mode, bool) or mode not in MODE_NAMES:
                blockers.append({"reason": "analyzer_accepted_send_mode_invalid", "detail": str(mode)})
            else:
                accepted_modes.add(mode)
    missing_modes = sorted(claimed_modes.difference(accepted_modes))
    if missing_modes:
        blockers.append({"reason": "analyzer_missing_claimed_send_modes", "detail": ",".join(map(str, missing_modes))})

    route_count = analyzer.get("route_event_count")
    if isinstance(route_count, int) and not isinstance(route_count, bool) and route_count > 0:
        blockers.append({"reason": "analyzer_route_observer_present_in_plugin_delivery_manifest", "detail": str(route_count)})
    accepted_route_modes = analyzer.get("accepted_route_send_modes")
    if isinstance(accepted_route_modes, list) and accepted_route_modes:
        blockers.append(
            {
                "reason": "analyzer_route_send_modes_present_in_plugin_delivery_manifest",
                "detail": ",".join(map(str, accepted_route_modes)),
            }
        )
    send_mode_evidence = analyzer.get("send_mode_evidence")
    if isinstance(send_mode_evidence, list):
        for entry in send_mode_evidence:
            if not isinstance(entry, dict):
                continue
            mode = entry.get("send_mode")
            if mode not in claimed_modes:
                continue
            if entry.get("route_observer_observed") is True:
                blockers.append({"reason": "analyzer_claimed_mode_has_route_observer_evidence", "detail": str(mode)})
            if entry.get("delivery_evidence_status") != "copied_plugin_delivery":
                blockers.append({"reason": "analyzer_claimed_mode_not_plugin_delivery", "detail": str(mode)})

    delivery_events = analyzer.get("delivery_events")
    if not isinstance(delivery_events, list):
        blockers.append({"reason": "analyzer_delivery_events_missing", "detail": "$.delivery_events"})
        return
    for mode in sorted(claimed_modes):
        send = controlled_by_mode.get(mode)
        if not send:
            continue
        expected_size = send.get("expected_message_size_bytes")
        matched = [
            event
            for event in delivery_events
            if isinstance(event, dict)
            and event.get("accepted") is True
            and isinstance(event.get("send_mode"), int)
            and not isinstance(event.get("send_mode"), bool)
            and event.get("send_mode") == mode
            and event.get("flags") == "0x1"
            and isinstance(event.get("message_size"), int)
            and not isinstance(event.get("message_size"), bool)
            and event.get("message_size") == expected_size
        ]
        if not matched:
            blockers.append({"reason": "analyzer_missing_matching_delivery_event", "detail": str(mode)})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WORKSPACE_ROOT)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main_args(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    blockers: list[dict[str, str]] = []
    payload = load_json(args.manifest, blockers, "manifest")
    if payload is None:
        result = {
            "schema": "obelisk.chat-mode-coverage-manifest-result.v1",
            "manifest": str(args.manifest),
            "run_id": None,
            "status": "blocked",
            "claimed_modes": [],
            "blockers": blockers,
        }
    else:
        result = validate_manifest(payload, args.manifest, workspace_root=args.workspace_root.expanduser().resolve())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"status={result['status']} blockers={len(result['blockers'])}")
        for blocker in result["blockers"]:
            print(f"blocker={blocker['reason']} detail={blocker['detail']}")
    return 3 if result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main_args())
