#!/usr/bin/env python3
"""Run the offline command/permission route gate as one planning-only check."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_QUERY_CONTRACT = REPO_ROOT / "docs" / "permissions_admin_query_failclosed_contract.json"
DEFAULT_PLAYER_IDENTITY_DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
DEFAULT_PUBLIC_SDK_SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE = (
    REPO_ROOT / "docs" / "research" / "2026-06-01-player-identity-private-candidate-contract.json"
)
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REPORT_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
PLAYER_IDENTITY_FIRST_EVIDENCE_SCHEMA = "obelisk.player-identity-first-evidence-readiness.v1"
EXPECTED_ROUTE_CHECK_SCHEMAS = {
    "player_identity_public_contract_gap": "obelisk.player-identity-public-contract-gap-report.v1",
    "permissions_query_failclosed": "obelisk.permissions-admin-query-failclosed-contract-check.v1",
    "permissions_admin_public_readiness": "obelisk.permissions-admin-public-readiness-check.v1",
    "command_copied_response_intent_planning": "obelisk.command-copied-response-intent-planning-check.v1",
    "command_copied_response_intent_lifecycle_planning": (
        "obelisk.command-copied-response-intent-lifecycle-planning-check.v1"
    ),
    "command_principal_authz_response_bridge": "obelisk.command-principal-authz-response-bridge-check.v1",
    "command_chat_response_public_readiness": "obelisk.command-chat-response-public-readiness-check.v1",
    "commands_replies_public_readiness": "obelisk.commands-replies-public-readiness-check.v1",
}
ALLOWED_CRITICAL_PATH_BLOCKERS = {
    "approved_runtime_evidence_missing",
    "identity_public_contract_gate",
    "identity_public_contract_gate_missing",
}
FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS = {
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "public_abi_allowed",
    "runtime_ready",
    "public_header_allowed",
    "public_readiness_ready",
    "public_command_router_allowed",
    "public_reply_or_send_chat_abi_allowed",
    "public_reply_abi_allowed",
    "public_send_chat_abi_allowed",
    "reply_send_chat_router_claims_allowed",
    "public_reply_api",
    "public_send_chat_api",
    "reply_allowed",
    "reply_api_allowed",
    "reply_abi_allowed",
    "send_chat_allowed",
    "send_chat_api_allowed",
    "permissions_admin_ready",
    "permissions_ready",
    "permission_ready",
    "command_router_allowed",
    "runtime_delivery_allowed",
    "runtime_readiness_allowed",
    "public_response_path_allowed",
    "v1_completion_evidence",
}
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_TERMS = (
    "command routing is public and ready",
    "permissions/admin is public and ready",
    "replies api is public and ready",
    "reply api is public and ready",
    "send-chat abi is public and ready",
    "send chat abi is public and ready",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        default=DEFAULT_QUERY_CONTRACT,
        help="Permissions/admin query fail-closed artifact used by dependent planning checks.",
    )
    parser.add_argument(
        "--player-identity-decisions",
        type=Path,
        default=DEFAULT_PLAYER_IDENTITY_DECISIONS,
        help="Player identity public contract decisions manifest used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=DEFAULT_PUBLIC_SDK_SURFACES,
        help="Public SDK surfaces manifest used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--player-identity-private-candidate-contract",
        type=Path,
        default=DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
        help="Private candidate-only identity contract used by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header scanned by the route's identity gap guardrail.",
    )
    parser.add_argument(
        "--command-response-root",
        type=Path,
        help="Optional command/chat response second-source planning root.",
    )
    parser.add_argument(
        "--command-response-readiness",
        type=Path,
        help="Optional command/chat response readiness JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def route_checks(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    command_response_args = ["check_command_chat_response_public_readiness.py", "--json"]
    if args.command_response_root is not None:
        command_response_args.extend(["--root", str(args.command_response_root)])
    if args.command_response_readiness is not None:
        command_response_args.extend(["--readiness", str(args.command_response_readiness)])

    query_artifact = str(args.query_failclosed_artifact)
    return [
        (
            "player_identity_public_contract_gap",
            [
                "check_player_identity_public_contract_gap_report.py",
                "--decisions",
                str(args.player_identity_decisions),
                "--surfaces",
                str(args.public_sdk_surfaces),
                "--private-candidate-contract",
                str(args.player_identity_private_candidate_contract),
                "--public-header",
                str(args.public_header),
                "--json",
            ],
        ),
        (
            "permissions_query_failclosed",
            ["check_permissions_admin_query_failclosed_contract.py", query_artifact, "--json"],
        ),
        (
            "permissions_admin_public_readiness",
            [
                "check_permissions_admin_public_readiness.py",
                "--query-failclosed-artifact",
                query_artifact,
                "--json",
            ],
        ),
        (
            "command_copied_response_intent_planning",
            [
                "check_command_copied_response_intent_planning.py",
                "--query-failclosed-artifact",
                query_artifact,
                "--json",
            ],
        ),
        (
            "command_copied_response_intent_lifecycle_planning",
            [
                "check_command_copied_response_intent_lifecycle_planning.py",
                "--json",
            ],
        ),
        ("command_principal_authz_response_bridge", ["check_command_principal_authz_response_bridge.py", "--json"]),
        ("command_chat_response_public_readiness", command_response_args),
        ("commands_replies_public_readiness", ["check_commands_replies_public_readiness.py", "--json"]),
    ]


def collect_public_or_runtime_claims(value: Any, *, path: str = "") -> list[str]:
    claims: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS and item is True:
                claims.append(item_path)
            if key == "public_or_runtime_claims" and isinstance(item, list):
                for claim in item:
                    if isinstance(claim, str) and claim:
                        claims.append(f"{item_path}:{claim}")
            claims.extend(collect_public_or_runtime_claims(item, path=item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(collect_public_or_runtime_claims(item, path=f"{path}[{index}]"))
    elif isinstance(value, str):
        text = value.casefold()
        if any(term in text for term in POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_TERMS):
            claims.append(f"{path}:positive_text_claim")
    return sorted(set(claims))


def run_check(name: str, argv: list[str]) -> dict[str, Any]:
    command = [sys.executable, str(SCRIPT_DIR / argv[0]), *argv[1:]]
    result = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)

    report: dict[str, Any] | None = None
    parse_error = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"

    public_or_runtime_claims = []
    if report is not None:
        public_or_runtime_claims = collect_public_or_runtime_claims(report)

    report_schema = report.get("schema") if report is not None else None
    expected_schema = EXPECTED_ROUTE_CHECK_SCHEMAS.get(name)
    schema_valid = report_schema == expected_schema

    check_valid = (
        result.returncode == 0
        and report is not None
        and schema_valid
        and report.get("valid", True) is True
        and not public_or_runtime_claims
    )

    return {
        "name": name,
        "argv": argv,
        "exit_code": result.returncode,
        "valid": check_valid,
        "report_schema": report_schema,
        "expected_schema": expected_schema,
        "planning_only": report.get("planning_only") if report is not None else None,
        "accepted_for_planning": report.get("accepted_for_planning") if report is not None else None,
        "public_or_runtime_claims": public_or_runtime_claims,
        "blockers": report.get("blockers", []) if report is not None else [],
        "parse_error": parse_error,
        "stderr": result.stderr.strip(),
    }


def build_critical_path_phase() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"), "--json"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    report: dict[str, Any] | None = None
    parse_error = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"

    current_blocker = "approved_runtime_evidence_missing"
    if report is not None:
        current_blocker = (
            report.get("primary_blocker")
            or report.get("next_blocker")
            or current_blocker
        )

    return {
        "current_surface": "obelisk.player_identity.v1",
        "current_blocker": current_blocker,
        "next_action": "produce_approved_runtime_principal_lifecycle_evidence",
        "next_after_runtime_evidence": "identity_public_contract_gate_missing",
        "permissions_admin_unlocked": False,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "source_checker": "check_player_identity_first_evidence_readiness.py",
        "source_checker_exit_code": result.returncode,
        "source_checker_schema": report.get("schema") if report is not None else None,
        "source_checker_parse_error": parse_error,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
    }


def validate_critical_path_phase(phase: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if phase.get("current_surface") != "obelisk.player_identity.v1":
        blockers.append("critical_path_identity_gate_not_locked")
    if phase.get("source_checker_schema") != PLAYER_IDENTITY_FIRST_EVIDENCE_SCHEMA:
        blockers.append("critical_path_identity_readiness_schema_mismatch")
    if phase.get("source_checker_parse_error") is not None:
        blockers.append("critical_path_identity_readiness_output_invalid")
    if phase.get("current_blocker") not in ALLOWED_CRITICAL_PATH_BLOCKERS:
        blockers.append("critical_path_identity_gate_unexpected_blocker")
    for key in (
        "permissions_admin_unlocked",
        "command_response_unlocked",
        "commands_replies_unlocked",
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
    ):
        if phase.get(key) is not False:
            blockers.append(f"critical_path_{key}_must_stay_false")
    return blockers


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    checks = [run_check(name, argv) for name, argv in route_checks(args)]
    blockers = []
    for check in checks:
        if check["exit_code"] != 0:
            blockers.append(f"{check['name']}: checker exited {check['exit_code']}")
        if check["parse_error"] is not None:
            blockers.append(f"{check['name']}: {check['parse_error']}")
        if check["report_schema"] != check["expected_schema"]:
            blockers.append(
                f"{check['name']}: schema mismatch "
                f"{check['report_schema']!r} != {check['expected_schema']!r}"
            )
        if check["public_or_runtime_claims"]:
            joined = ", ".join(check["public_or_runtime_claims"])
            blockers.append(f"{check['name']}: unexpected public/runtime claim: {joined}")
        if not check["valid"]:
            blockers.append(f"{check['name']}: invalid route prerequisite")
    critical_path_phase = build_critical_path_phase()
    blockers.extend(validate_critical_path_phase(critical_path_phase))

    return {
        "schema": REPORT_SCHEMA,
        "valid": not blockers,
        "accepted_for_planning": not blockers,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "dependency_chain": [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ],
        "critical_path_phase": critical_path_phase,
        "route_lock": {
            "locked": not validate_critical_path_phase(critical_path_phase),
            "blocked_until": [
                "approved_runtime_principal_lifecycle_evidence",
                "reviewed_identity_public_contract",
            ],
            "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
        },
        "checks": checks,
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
