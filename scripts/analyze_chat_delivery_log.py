#!/usr/bin/env python3
"""Validate copied ChatMessageEvent delivery logs from an approved beta window."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import protected_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
CHAT_COPIED_PAYLOAD_FLAG = 0x1
LOG_PREFIX = r"(?:\[[^\]]+\]\s+)*"
ROUTE_SEND_MODE_NAMES = {
    0: "GlobalChat",
    1: "GlobalTribeChat",
    2: "LocalChat",
    3: "AllianceChat",
}
ALL_CHAT_SEND_MODES = set(ROUTE_SEND_MODE_NAMES)

PRODUCER_RE = re.compile(
    LOG_PREFIX
    + r"Chat message event producer enabled for ShooterGameServer SHA256 "
    r"(?P<sha256>[a-fA-F0-9]{64})\.?"
)
REGISTERED_RE = re.compile(LOG_PREFIX + r"\[Plugin\] \[oChatLogger\] Registered ChatMessageEvent callback\.")
REJECTED_RE = re.compile(LOG_PREFIX + r"\[Plugin\] \[oChatLogger\] Rejected malformed ChatMessageEvent\.")
DELIVERY_RE = re.compile(
    LOG_PREFIX
    + r"\[Plugin\] \[oChatLogger\] ChatMessageEvent received "
    r"sequence=(?P<sequence>\d+) "
    r"send_mode=(?P<send_mode>\d+) "
    r"flags=(?P<flags>0x[0-9a-fA-F]+) "
    r"message_size=(?P<message_size>\d+)\."
    r"(?: mode_count=(?P<mode_count>\d+) first_observed=(?P<first_observed>true|false)\.)?$"
)
ROUTE_RE = re.compile(
    LOG_PREFIX
    + r"ChatRouteObserver event "
    r"sequence=(?P<sequence>\d+) "
    r"send_mode=(?P<send_mode>[0-3]) "
    r"send_mode_name=(?P<send_mode_name>[A-Za-z]+) "
    r"post_original=true "
    r"delivery_claim=none\.$"
)
PRIVACY_RE = re.compile(
    r"(?:"
    r"\b(?:message|text|chat_text|message_text|raw_chat)\s*=|"
    r"\b(?:params|function)\s*=\s*0x[0-9a-fA-F]+|"
    r"\b(?:message_text|raw_chat)\b|"
    r"\b(?:player_id|player_name|player_unique_id|steam_id|steam_name|eos_id|"
    r"sender|sender_name|character_name|tribe_id|tribe_name|platform_id|"
    r"platform_user_id|unique_net_id)\b"
    r")",
    re.IGNORECASE,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def is_relative_to(path: Path, parent: Path) -> bool:
    return protected_paths.is_under_path(path, parent)


def is_approved_offline_workspace_path(path: Path) -> bool:
    return protected_paths.is_approved_offline_workspace_path(
        path,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )


def path_blockers(path: Path) -> list[dict[str, str]]:
    blockers = protected_paths.protected_input_path_blockers(
        path,
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    for blocker in blockers:
        if blocker["reason"] == "path_under_live_server_root":
            blocker["reason"] = "log_path_under_live_server_root"
            blocker["detail"] = "analyze copied logs under /servidor/ark/workspace-offline, not live server logs"
        elif blocker["reason"] == "resolved_path_under_live_server_root":
            blocker["reason"] = "resolved_log_path_under_live_server_root"
            blocker["detail"] = "resolved log path is not under /servidor/ark/workspace-offline"
    return blockers


def build_send_mode_evidence(
    accepted_send_modes: list[int],
    accepted_route_send_modes: list[int],
) -> list[dict[str, Any]]:
    copied_delivery_modes = set(accepted_send_modes)
    route_modes = set(accepted_route_send_modes)
    evidence: list[dict[str, Any]] = []
    for send_mode in sorted(ALL_CHAT_SEND_MODES):
        has_copied_delivery = send_mode in copied_delivery_modes
        has_route_observer = send_mode in route_modes
        if has_copied_delivery:
            delivery_status = "copied_plugin_delivery"
        elif has_route_observer:
            delivery_status = "route_only_no_plugin_delivery"
        else:
            delivery_status = "not_observed"
        evidence.append(
            {
                "send_mode": send_mode,
                "send_mode_name": ROUTE_SEND_MODE_NAMES[send_mode],
                "copied_plugin_delivery_observed": has_copied_delivery,
                "route_observer_observed": has_route_observer,
                "delivery_evidence_status": delivery_status,
            }
        )
    return evidence


def parse_log(
    path: Path,
    *,
    expected_sha256: str | None,
    min_events: int,
    expected_message_size: int | None = None,
    required_send_modes: set[int] | None = None,
    required_route_send_modes: set[int] | None = None,
    require_workspace: bool = False,
    allow_server_path: bool = False,
) -> dict[str, Any]:
    blockers = path_blockers(path)
    if require_workspace and not is_approved_offline_workspace_path(path):
        blockers.append(
            {
                "reason": "log_not_under_approved_offline_workspace",
                "detail": "copy beta evidence under /servidor/ark/workspace-offline before milestone validation",
            }
        )
    producer_sha256: list[str] = []
    registered = False
    rejected_malformed = 0
    privacy_leak_lines = 0
    malformed_delivery_lines = 0
    malformed_route_lines = 0
    out_of_order_delivery_lines = 0
    delivery_events: list[dict[str, Any]] = []
    route_events: list[dict[str, Any]] = []

    if blockers and not allow_server_path:
        lines = []
        log_sha256 = None
    elif not path.exists():
        blockers.append({"reason": "log_missing", "detail": str(path)})
        lines: list[str] = []
        log_sha256 = None
    elif not path.is_file():
        blockers.append({"reason": "log_not_regular_file", "detail": str(path)})
        lines = []
        log_sha256 = None
    else:
        log_sha256 = sha256_file(path)
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    for line in lines:
        if PRIVACY_RE.search(line):
            privacy_leak_lines += 1

        producer = PRODUCER_RE.search(line)
        if producer:
            sha = producer.group("sha256").lower()
            if sha not in producer_sha256:
                producer_sha256.append(sha)
            continue

        if REGISTERED_RE.search(line):
            registered = True
            continue

        if REJECTED_RE.search(line):
            rejected_malformed += 1
            continue

        delivery = DELIVERY_RE.search(line)
        if delivery:
            if not producer_sha256 or not registered:
                out_of_order_delivery_lines += 1
            sequence = int(delivery.group("sequence"))
            send_mode = int(delivery.group("send_mode"))
            flags = int(delivery.group("flags"), 16)
            message_size = int(delivery.group("message_size"))
            mode_count_raw = delivery.group("mode_count")
            first_observed_raw = delivery.group("first_observed")
            mode_count = int(mode_count_raw) if mode_count_raw is not None else None
            first_observed = first_observed_raw == "true" if first_observed_raw is not None else None
            event_blockers: list[str] = []
            if sequence == 0:
                event_blockers.append("zero_sequence")
            if send_mode < 0 or send_mode > 3:
                event_blockers.append("send_mode_out_of_range")
            if (flags & CHAT_COPIED_PAYLOAD_FLAG) == 0:
                event_blockers.append("missing_copied_payload_flag")
            if message_size == 0:
                event_blockers.append("zero_message_size")
            if expected_message_size is not None and message_size != expected_message_size:
                event_blockers.append("unexpected_message_size")
            if mode_count is not None:
                if mode_count == 0:
                    event_blockers.append("zero_mode_count")
                elif first_observed != (mode_count == 1):
                    event_blockers.append("first_observed_mode_count_mismatch")
            delivery_events.append(
                {
                    "sequence": sequence,
                    "send_mode": send_mode,
                    "flags": f"0x{flags:x}",
                    "message_size": message_size,
                    "mode_count": mode_count,
                    "first_observed": first_observed,
                    "accepted": not event_blockers,
                    "blockers": event_blockers,
                }
            )
            continue

        route = ROUTE_RE.search(line)
        if route:
            sequence = int(route.group("sequence"))
            send_mode = int(route.group("send_mode"))
            send_mode_name = route.group("send_mode_name")
            event_blockers: list[str] = []
            if sequence == 0:
                event_blockers.append("zero_sequence")
            expected_send_mode_name = ROUTE_SEND_MODE_NAMES[send_mode]
            if send_mode_name != expected_send_mode_name:
                event_blockers.append("send_mode_name_mismatch")
            route_events.append(
                {
                    "sequence": sequence,
                    "send_mode": send_mode,
                    "send_mode_name": send_mode_name,
                    "post_original": True,
                    "delivery_claim": "none",
                    "accepted": not event_blockers,
                    "blockers": event_blockers,
                }
            )
            continue

        if "[oChatLogger] ChatMessageEvent received" in line:
            malformed_delivery_lines += 1
            continue

        if "ChatRouteObserver event" in line:
            malformed_route_lines += 1

    accepted_events = [event for event in delivery_events if event["accepted"]]
    accepted_route_events = [event for event in route_events if event["accepted"]]
    if not producer_sha256:
        blockers.append({"reason": "missing_chat_event_producer_gate", "detail": "producer gate log line not found"})
    if len(producer_sha256) > 1:
        blockers.append({"reason": "mixed_chat_event_producer_sha256", "detail": ",".join(producer_sha256)})
    if expected_sha256 and producer_sha256 and producer_sha256 != [expected_sha256.lower()]:
        blockers.append(
            {
                "reason": "unexpected_chat_event_producer_sha256",
                "detail": f"expected={expected_sha256.lower()} observed={','.join(producer_sha256)}",
            }
        )
    if not registered:
        blockers.append({"reason": "missing_ochatlogger_registration", "detail": "registration log line not found"})
    if rejected_malformed:
        blockers.append({"reason": "malformed_chat_event_rejected", "detail": str(rejected_malformed)})
    if malformed_delivery_lines:
        blockers.append({"reason": "malformed_delivery_log_line", "detail": str(malformed_delivery_lines)})
    if malformed_route_lines:
        blockers.append({"reason": "malformed_route_observer_log_line", "detail": str(malformed_route_lines)})
    if out_of_order_delivery_lines:
        blockers.append({"reason": "chat_delivery_event_before_required_gate", "detail": str(out_of_order_delivery_lines)})
    if privacy_leak_lines:
        blockers.append({"reason": "chat_privacy_data_logged", "detail": str(privacy_leak_lines)})
    if len(accepted_events) < min_events:
        blockers.append(
            {
                "reason": "insufficient_accepted_chat_delivery_events",
                "detail": f"expected>={min_events} observed={len(accepted_events)}",
            }
        )
    accepted_send_modes = sorted({int(event["send_mode"]) for event in accepted_events})
    missing_required_send_modes: list[int] = []
    if required_send_modes:
        missing_required_send_modes = sorted(required_send_modes.difference(accepted_send_modes))
        if missing_required_send_modes:
            blockers.append(
                {
                    "reason": "missing_required_chat_send_modes",
                    "detail": ",".join(str(send_mode) for send_mode in missing_required_send_modes),
                }
            )
    accepted_route_send_modes = sorted({int(event["send_mode"]) for event in accepted_route_events})
    missing_required_route_send_modes: list[int] = []
    if required_route_send_modes:
        missing_required_route_send_modes = sorted(required_route_send_modes.difference(accepted_route_send_modes))
        if missing_required_route_send_modes:
            blockers.append(
                {
                    "reason": "missing_required_chat_route_send_modes",
                    "detail": ",".join(str(send_mode) for send_mode in missing_required_route_send_modes),
                }
            )
    for event in delivery_events:
        for reason in event["blockers"]:
            blockers.append({"reason": f"delivery_event_{reason}", "detail": f"sequence={event['sequence']}"})
    for event in route_events:
        for reason in event["blockers"]:
            blockers.append({"reason": f"route_event_{reason}", "detail": f"sequence={event['sequence']}"})
    uncovered_delivery_send_modes = sorted(ALL_CHAT_SEND_MODES.difference(accepted_send_modes))

    return {
        "schema": "obelisk.chat-delivery-log-summary.v1",
        "review_scope": "chat_message_event_delivery_evidence",
        "promotion_gate": {
            "ready": not blockers,
            "blockers": blockers,
        },
        "source": {
            "path": str(path),
            "sha256": log_sha256,
            "line_count": len(lines),
            "obelisk_commit": git_commit(),
        },
        "producer_sha256": producer_sha256,
        "oChatLogger_registered": registered,
        "rejected_malformed_count": rejected_malformed,
        "privacy_leak_line_count": privacy_leak_lines,
        "malformed_delivery_line_count": malformed_delivery_lines,
        "malformed_route_line_count": malformed_route_lines,
        "out_of_order_delivery_line_count": out_of_order_delivery_lines,
        "delivery_event_count": len(delivery_events),
        "accepted_delivery_event_count": len(accepted_events),
        "delivery_metadata_event_count": sum(1 for event in delivery_events if event["mode_count"] is not None),
        "accepted_send_modes": accepted_send_modes,
        "missing_required_send_modes": missing_required_send_modes,
        "delivery_mode_coverage": {
            "complete": not uncovered_delivery_send_modes,
            "covered_send_modes": accepted_send_modes,
            "uncovered_send_modes": uncovered_delivery_send_modes,
            "basis": "copied_plugin_delivery_events_only",
        },
        "mode_coverage_note": "Observed delivery send modes are positive evidence only; absence of a send mode is inconclusive without a controlled mode-specific test window and producer-observation logs.",
        "delivery_events": delivery_events,
        "route_event_count": len(route_events),
        "accepted_route_event_count": len(accepted_route_events),
        "accepted_route_send_modes": accepted_route_send_modes,
        "missing_required_route_send_modes": missing_required_route_send_modes,
        "send_mode_evidence": build_send_mode_evidence(accepted_send_modes, accepted_route_send_modes),
        "route_coverage_note": "Observed route send modes are internal route evidence only; they are not plugin-facing ChatMessageEvent delivery evidence.",
        "route_events": route_events,
    }


def parse_send_mode_set(raw_modes: str, option_name: str) -> set[int] | None:
    if not raw_modes:
        return None
    send_modes: set[int] = set()
    for raw in raw_modes.split(","):
        raw = raw.strip()
        if not raw:
            print(f"{option_name} entries must be non-empty integers in range 0..3", file=sys.stderr)
            return None
        try:
            send_mode = int(raw, 10)
        except ValueError:
            print(f"{option_name} entries must be integers in range 0..3", file=sys.stderr)
            return None
        if send_mode < 0 or send_mode > 3:
            print(f"{option_name} entries must be integers in range 0..3", file=sys.stderr)
            return None
        send_modes.add(send_mode)
    return send_modes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="Copied beta-window log to analyze.")
    parser.add_argument("--expected-sha256", help="Expected ARK ShooterGameServer SHA256.")
    parser.add_argument("--expected-message-size", type=int, help="Expected controlled beta chat message size.")
    parser.add_argument("--min-events", type=int, default=1, help="Minimum accepted delivery events required.")
    parser.add_argument(
        "--require-send-modes",
        help="Comma-separated accepted send modes required for a controlled mode-coverage claim, e.g. 0,1,2,3.",
    )
    parser.add_argument(
        "--require-route-send-modes",
        help="Comma-separated accepted route observer send modes required for an internal route-coverage claim, e.g. 0,1,2,3.",
    )
    parser.add_argument("--require-workspace", action="store_true", help="Require log path under /servidor/ark/workspace-offline.")
    parser.add_argument(
        "--allow-server-path",
        action="store_true",
        help="Allow direct live-server log reads for operator-approved emergency review.",
    )
    parser.add_argument("--fail-on-quality-blockers", action="store_true", help="Exit non-zero when blockers exist.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.min_events < 1:
        print("--min-events must be >= 1", file=sys.stderr)
        return 2
    if args.expected_message_size is not None and args.expected_message_size < 1:
        print("--expected-message-size must be >= 1", file=sys.stderr)
        return 2
    required_send_modes: set[int] | None = None
    if args.require_send_modes:
        required_send_modes = parse_send_mode_set(args.require_send_modes, "--require-send-modes")
        if required_send_modes is None:
            return 2
    required_route_send_modes: set[int] | None = None
    if args.require_route_send_modes:
        required_route_send_modes = parse_send_mode_set(
            args.require_route_send_modes,
            "--require-route-send-modes",
        )
        if required_route_send_modes is None:
            return 2

    result = parse_log(
        args.log,
        expected_sha256=args.expected_sha256,
        min_events=args.min_events,
        expected_message_size=args.expected_message_size,
        required_send_modes=required_send_modes,
        required_route_send_modes=required_route_send_modes,
        require_workspace=args.require_workspace,
        allow_server_path=args.allow_server_path,
    )
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        gate = result["promotion_gate"]
        print(
            f"ready={str(gate['ready']).lower()} "
            f"accepted_delivery_event_count={result['accepted_delivery_event_count']} "
            f"accepted_send_modes={','.join(str(mode) for mode in result['accepted_send_modes'])} "
            f"accepted_route_event_count={result['accepted_route_event_count']} "
            f"accepted_route_send_modes={','.join(str(mode) for mode in result['accepted_route_send_modes'])} "
            f"blockers={len(gate['blockers'])}"
        )
        for blocker in gate["blockers"]:
            print(f"blocker={blocker['reason']} detail={blocker['detail']}")

    if args.fail_on_quality_blockers and result["promotion_gate"]["blockers"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
