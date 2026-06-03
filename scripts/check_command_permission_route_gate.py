#!/usr/bin/env python3
"""Run the offline command/permission route gate as one planning-only check."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
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
DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-lifecycle-anchor-candidates.json"
)
DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-principal-invalidation-policy.json"
)
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
COMMAND_RESPONSE_DEFAULT_READINESS_NAME = "command-chat-response-route-planning-readiness.json"

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
REQUIRED_PLANNING_ONLY_CHECKS = {
    "permissions_admin_public_readiness",
    "command_copied_response_intent_planning",
    "command_copied_response_intent_lifecycle_planning",
    "command_principal_authz_response_bridge",
    "command_chat_response_public_readiness",
    "commands_replies_public_readiness",
}
REQUIRED_LOCKED_CHILD_CHECKS = {
    "permissions_admin_public_readiness",
    "command_chat_response_public_readiness",
    "commands_replies_public_readiness",
}
UPSTREAM_IDENTITY_LOCK_BLOCKERS = {
    "lifecycle_anchor_first_evidence_provenance_unbound",
}
UPSTREAM_SKIPPED_ROUTE_CHECKS = REQUIRED_LOCKED_CHILD_CHECKS | {
    "player_identity_public_contract_gap",
}
REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS = (
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)
ALLOWED_IDENTITY_LOCK_BLOCKERS = {
    "lifecycle_anchor_first_evidence_provenance_unbound": {
        "next_action": "bind_lifecycle_anchor_and_principal_policy_sources",
        "blocked_until": "bound_lifecycle_anchor_and_principal_policy_sources",
    },
    "approved_runtime_evidence_missing": {
        "next_action": "produce_approved_runtime_principal_lifecycle_evidence",
        "blocked_until": "approved_runtime_principal_lifecycle_evidence",
    },
    "identity_public_contract_gate_missing": {
        "next_action": "review_identity_public_contract_gate",
        "blocked_until": "reviewed_identity_public_contract",
    },
}
FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS = {
    "promotion_ready",
    "public_sdk_ready",
    "public_sdk",
    "public_abi_ready",
    "public_abi_allowed",
    "public_reply_abi_ready",
    "public_response_path_ready",
    "runtime_ready",
    "send_chat_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
    "public_header_allowed",
    "public_header_ready",
    "public_readiness_ready",
    "public_bridge_abi_allowed",
    "public_command_router_allowed",
    "public_response_abi_allowed",
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
    "v1_completion_ready",
    "stable_claim_allowed",
    "operator_approval_granted",
    "runtime_approval",
    "runtime_approval_granted",
    "runtime_work_authorized",
    "server_operations_authorized",
}
BROAD_PUBLIC_OR_RUNTIME_CLAIM_KEY_RE = re.compile(
    r"^(?:"
    r"(?:complete|full|stable|production(?:_ready|_grade)?)_(?:sdk|api|support)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"(?:sdk|api|support)_(?:complete|full|stable|production(?:_ready|_grade)?)"
    r"(?:_(?:ready|allowed|supported|enabled|public))?|"
    r"public_api(?:_(?:ready|allowed|supported|enabled|public))?"
    r")$"
)


def route_lock_blocked_until(current_blocker: Any) -> list[str]:
    blocker_route = ALLOWED_IDENTITY_LOCK_BLOCKERS.get(str(current_blocker), {})
    required = blocker_route.get("blocked_until", "allowed_identity_lock_blocker")
    blocked_until = [required]
    if required != "reviewed_identity_public_contract":
        blocked_until.append("reviewed_identity_public_contract")
    return blocked_until
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS = {
    "approved_runtime_evidence_source",
    "authority_claim_source",
    "authz_principal_source",
    "command_principal_source",
    "evidence_source",
    "identity_claim_source",
    "permission_principal_source",
    "principal_claim_source",
    "principal_source",
    "public_identity_source",
    "runtime_evidence_source",
    "runtime_identity_source",
}
FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES = {
    "command_text",
    "operator_config",
}
FORBIDDEN_PRE_PUBLIC_CONTRACT_CLAIM_SOURCE_VALUE_RE = re.compile(
    r"(?:"
    r"(?:approved_?)?runtime(?:_local|_evidence|_lifecycle|_observation|_observed|_principal.*evidence)?|"
    r"approved_runtime_principal_lifecycle_evidence|"
    r"runtime_principal_lifecycle_evidence|"
    r"runtime_lifecycle_evidence|"
    r"players?_identity_runtime_principal_lifecycle_evidence|"
    r"reviewed_identity_public_contract|"
    r"identity_public_contract|"
    r"(?:players?_?)?identity_?lifecycle_?anchor_?candidates?|"
    r"lifecycle_?anchor_?(?:candidates?|report|evidence)|"
    r"request_?pack|"
    r"preflight(?:_?sidecar)?|"
    r"operator_?(?:approval_?)?receipts?|"
    r"(?:live_?)?(?:validation|ops)_?sidecars?|"
    r"window_?manifests?|"
    r"planning_?(?:artifacts?|manifests?|sources?)|"
    r"placeholder_?(?:runtime_?)?evidence|"
    r"public_identity"
    r")"
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE = re.compile(
    r"\b(?:"
    r"command[_ -]?(?:routing|router|response[_ -]?path)|"
    r"permissions?/admin|permissions?|public[_ -]?abi|reply[_ -]?(?:endpoint|api|abi)|"
    r"replies[_ -]?(?:api|abi)|send[_ -]?chat[_ -]?(?:api|abi)|runtime|"
    r"runtime[_ -]?work|server[_ -]?operations?|operator[_ -]?approval|runtime[_ -]?approval|"
    r"public[_ -]?(?:sdk|header)|v1[_ -]?completion|stable[_ -]?claim|"
    r"(?:complete|full|stable|production(?:[_ -]?(?:ready|grade))?)[_ -]?(?:sdk|api|support)"
    r")\b(?:\s+(?:is|are))?\s+"
    r"\b(?:authorized|granted|public(?:\s+and\s+ready)?|ready|readiness|live|enabled|allowed|operational|supported)\b",
    re.IGNORECASE,
)
POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED = re.compile(
    r"\b(?:public[_ -]?(?:api|abi)|sdk|api|support)\b\s+"
    r"(?:is|are|now|becomes?|became)\s+"
    r"\b(?:complete|full|stable|production(?:[_ -]?(?:ready|grade))?|public|ready|supported)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_PREFIX_RE = re.compile(
    r"\b(?:blocked|cannot|does\s+not|do\s+not|excluded|excludes?|future|must\s+not|no|not|"
    r"only|outside|post-v1|prevent|prevents|remain|remains|without)\b",
    re.IGNORECASE,
)
NEGATED_CLAIM_SUFFIX_RE = re.compile(
    r"^\s+(?:remains?|stays?|is|are)?\s*(?:blocked|not\s+(?:ready|enabled|authorized|allowed)|"
    r"unauthorized|unsupported)\b",
    re.IGNORECASE,
)
CLAIM_SCOPE_SPLIT_RE = re.compile(r"[,.;:\n\r]|\s+\b(?:and|but|then|however|unless)\b\s+", re.IGNORECASE)


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.casefold().replace("-", "_").replace(" ", "_") in {
            "allowed",
            "available",
            "enabled",
            "live",
            "operational",
            "promoted",
            "public",
            "ready",
            "supported",
            "true",
            "unlocked",
            "yes",
        }
    return False


def preceding_claim_scope(text: str, start: int) -> str:
    parts = CLAIM_SCOPE_SPLIT_RE.split(text[:start])
    return parts[-1] if parts else text[:start]


def is_negated_text_claim(text: str, match: re.Match[str]) -> bool:
    prefix = preceding_claim_scope(text, match.start())
    if NEGATED_CLAIM_PREFIX_RE.search(prefix) and not re.search(
        r"\b(?:claims?|reports?|says|states?)\b[^,.;:\n\r]*$",
        prefix,
        re.IGNORECASE,
    ):
        return True
    return bool(NEGATED_CLAIM_SUFFIX_RE.match(text[match.end() :]))


def contains_positive_public_or_runtime_text_claim(text: str) -> bool:
    for pattern in (POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_RE, POSITIVE_PUBLIC_OR_RUNTIME_CLAIM_REVERSED):
        for match in pattern.finditer(text):
            if not is_negated_text_claim(text, match):
                return True
    return False


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
    parser.add_argument(
        "--player-identity-artifact-root",
        type=Path,
        help="Optional artifact root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--player-identity-snapshot-root",
        type=Path,
        help="Optional first-evidence snapshot root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--player-identity-candidate-root",
        type=Path,
        help="Optional second-source candidate root forwarded to the player-identity first-evidence checker.",
    )
    parser.add_argument(
        "--lifecycle-anchor-candidates-manifest",
        "--player-identity-lifecycle-anchor-candidates-manifest",
        dest="player_identity_lifecycle_anchor_candidates_manifest",
        type=Path,
        help="Optional bound lifecycle-anchor candidates manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--principal-invalidation-policy-manifest",
        "--player-identity-principal-invalidation-policy-manifest",
        dest="player_identity_principal_invalidation_policy_manifest",
        type=Path,
        help="Optional bound principal invalidation policy manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--runtime-principal-lifecycle-evidence-manifest",
        "--player-identity-runtime-principal-lifecycle-evidence-manifest",
        dest="player_identity_runtime_principal_lifecycle_evidence_manifest",
        type=Path,
        help="Optional synthetic/redacted runtime-principal lifecycle shape manifest forwarded to the identity checker.",
    )
    parser.add_argument(
        "--approved-runtime-principal-lifecycle-evidence-manifest",
        "--player-identity-approved-runtime-principal-lifecycle-evidence-manifest",
        dest="player_identity_approved_runtime_principal_lifecycle_evidence_manifest",
        type=Path,
        help="Optional approved runtime-principal lifecycle evidence manifest forwarded to the identity checker.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def identity_readiness_argv(args: argparse.Namespace | None) -> list[str]:
    argv = [sys.executable, str(SCRIPT_DIR / "check_player_identity_first_evidence_readiness.py"), "--json"]
    if args is None:
        return argv
    optional_args = (
        ("player_identity_artifact_root", "--artifact-root"),
        ("player_identity_snapshot_root", "--snapshot-root"),
        ("player_identity_candidate_root", "--candidate-root"),
        ("player_identity_lifecycle_anchor_candidates_manifest", "--lifecycle-anchor-candidates-manifest"),
        ("player_identity_principal_invalidation_policy_manifest", "--principal-invalidation-policy-manifest"),
        (
            "player_identity_runtime_principal_lifecycle_evidence_manifest",
            "--runtime-principal-lifecycle-evidence-manifest",
        ),
        (
            "player_identity_approved_runtime_principal_lifecycle_evidence_manifest",
            "--approved-runtime-principal-lifecycle-evidence-manifest",
        ),
    )
    for attr, flag in optional_args:
        value = getattr(args, attr, None)
        if value is not None:
            argv.extend([flag, str(value)])
    return argv


def route_checks(
    args: argparse.Namespace,
    *,
    current_route_blocker: str | None,
    approved_runtime_evidence_accepted: bool | None = None,
) -> list[tuple[str, list[str]]]:
    if approved_runtime_evidence_accepted is None:
        approved_runtime_evidence_accepted = current_route_blocker == "identity_public_contract_gate_missing"
    shared_surface_args = ["--surfaces", str(args.public_sdk_surfaces)]
    shared_header_args = ["--public-header", str(args.public_header)]
    route_blocker_args = ["--current-route-blocker", current_route_blocker] if current_route_blocker else []
    player_identity_gap_args = [
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
    ]
    approved_runtime = getattr(args, "player_identity_approved_runtime_principal_lifecycle_evidence_manifest", None)
    if approved_runtime is not None and approved_runtime_evidence_accepted:
        player_identity_gap_args.extend(["--approved-runtime-evidence", str(approved_runtime)])
    command_response_args = [
        "check_command_chat_response_public_readiness.py",
        *shared_surface_args,
        *shared_header_args,
        *route_blocker_args,
        "--json",
    ]
    if args.command_response_root is not None:
        command_response_args.extend(["--root", str(args.command_response_root)])
    if args.command_response_readiness is not None:
        command_response_args.extend(["--readiness", str(args.command_response_readiness)])

    query_artifact = str(args.query_failclosed_artifact)
    checks = [
        (
            "player_identity_public_contract_gap",
            player_identity_gap_args,
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
                *shared_surface_args,
                *shared_header_args,
                *route_blocker_args,
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
        (
            "commands_replies_public_readiness",
            [
                "check_commands_replies_public_readiness.py",
                *shared_surface_args,
                *shared_header_args,
                *route_blocker_args,
                "--json",
            ],
        ),
    ]
    if current_route_blocker is None:
        return [
            (name, argv)
            for name, argv in checks
            if name not in UPSTREAM_SKIPPED_ROUTE_CHECKS
        ]
    return checks


def validate_command_response_readiness_binding(args: argparse.Namespace) -> list[str]:
    if args.command_response_readiness is None:
        return []
    if args.command_response_root is None:
        return ["command_chat_response_public_readiness: caller-supplied readiness requires --command-response-root"]
    expected = (args.command_response_root / COMMAND_RESPONSE_DEFAULT_READINESS_NAME).resolve()
    observed = args.command_response_readiness.resolve()
    if observed != expected:
        return [
            "command_chat_response_public_readiness: caller-supplied readiness is not bound to "
            "--command-response-root"
        ]
    return []


def validate_command_response_child_readiness_context(
    args: argparse.Namespace,
    payload: dict[str, Any] | None,
) -> list[str]:
    if payload is None:
        return []
    readiness_root = payload.get("readiness_root")
    readiness_path = payload.get("readiness_path")
    blockers: list[str] = []
    if not isinstance(readiness_root, str) or not readiness_root:
        blockers.append("command_chat_response_public_readiness: child readiness_root missing or unverifiable")
    if not isinstance(readiness_path, str) or not readiness_path:
        blockers.append("command_chat_response_public_readiness: child readiness_path missing or unverifiable")
    if blockers:
        return blockers

    child_root = Path(readiness_root).resolve()
    child_readiness = Path(readiness_path).resolve()
    expected_child_readiness = child_root / COMMAND_RESPONSE_DEFAULT_READINESS_NAME
    if child_readiness != expected_child_readiness:
        blockers.append(
            "command_chat_response_public_readiness: child readiness_path is not bound to readiness_root"
        )
    if args.command_response_root is not None and child_root != args.command_response_root.resolve():
        blockers.append("command_chat_response_public_readiness: child readiness_root does not match caller root")
    if args.command_response_readiness is not None and child_readiness != args.command_response_readiness.resolve():
        blockers.append(
            "command_chat_response_public_readiness: child readiness_path does not match caller readiness"
        )
    return blockers


def validate_identity_planning_binding_args(args: argparse.Namespace) -> list[str]:
    lifecycle = getattr(args, "player_identity_lifecycle_anchor_candidates_manifest", None)
    principal = getattr(args, "player_identity_principal_invalidation_policy_manifest", None)
    if (lifecycle is None) != (principal is None):
        return [
            "player_identity_first_evidence_readiness: lifecycle/principal planning manifests must be supplied together"
        ]
    return []


def approved_runtime_evidence_ready_for_identity_lock(phase: dict[str, Any]) -> bool:
    diagnosis = phase.get("source_checker_approved_runtime_evidence_manifest")
    if not isinstance(diagnosis, dict):
        return False
    return (
        diagnosis.get("ready") is True
        and diagnosis.get("approved_runtime_evidence_present") is True
        and diagnosis.get("runtime_evidence_ready") is True
        and diagnosis.get("remaining_blockers") == []
    )


def expected_identity_lock_blocker_for_phase(phase: dict[str, Any]) -> str:
    if approved_runtime_evidence_ready_for_identity_lock(phase):
        return "identity_public_contract_gate_missing"
    return "approved_runtime_evidence_missing"


def validate_identity_lock_mode(args: argparse.Namespace, phase: dict[str, Any]) -> list[str]:
    expected = expected_identity_lock_blocker_for_phase(phase)
    observed = phase.get("current_blocker")
    source_observed = phase.get("source_checker_primary_blocker")
    blockers: list[str] = []
    if observed in UPSTREAM_IDENTITY_LOCK_BLOCKERS and source_observed == observed:
        return blockers
    if observed != expected:
        blockers.append(f"critical_path_identity_gate_mode_unexpected_blocker:{observed!r}!={expected!r}")
    if source_observed != expected:
        blockers.append(
            f"critical_path_identity_readiness_mode_unexpected_blocker:{source_observed!r}!={expected!r}"
        )
    return blockers


def collect_public_or_runtime_claims(
    value: Any,
    *,
    path: str = "",
    include_text_claims: bool = True,
) -> list[str]:
    claims: list[str] = []

    def normalized_key(key: object) -> str:
        separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
        return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")

    def normalized_source(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "_", str(value).casefold()).strip("_")

    def contains_forbidden_claim_source(item: Any) -> bool:
        if isinstance(item, str):
            source = normalized_source(item)
            return (
                source in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_VALUES
                or FORBIDDEN_PRE_PUBLIC_CONTRACT_CLAIM_SOURCE_VALUE_RE.search(source) is not None
            )
        if isinstance(item, list):
            return any(contains_forbidden_claim_source(child) for child in item)
        if isinstance(item, dict):
            return any(contains_forbidden_claim_source(child) for child in item.values())
        return False

    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            key_name = normalized_key(key)
            if (
                key_name in FORBIDDEN_PUBLIC_OR_RUNTIME_CLAIM_KEYS
                or BROAD_PUBLIC_OR_RUNTIME_CLAIM_KEY_RE.fullmatch(key_name)
            ) and is_positive_claim_value(item):
                claims.append(item_path)
            if key_name in FORBIDDEN_PRE_RUNTIME_CLAIM_SOURCE_KEYS and contains_forbidden_claim_source(item):
                claims.append(item_path)
            if key == "public_or_runtime_claims" and isinstance(item, list):
                for claim in item:
                    if isinstance(claim, str) and claim:
                        claims.append(f"{item_path}:{claim}")
            claims.extend(
                collect_public_or_runtime_claims(
                    item,
                    path=item_path,
                    include_text_claims=include_text_claims,
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(
                collect_public_or_runtime_claims(
                    item,
                    path=f"{path}[{index}]",
                    include_text_claims=include_text_claims,
                )
            )
    elif isinstance(value, str):
        if include_text_claims and contains_positive_public_or_runtime_text_claim(value):
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
    report_blockers = report.get("blockers", []) if report is not None else []
    blockers_empty = isinstance(report_blockers, list) and not report_blockers

    check_valid = (
        result.returncode == 0
        and report is not None
        and schema_valid
        and report.get("valid") is True
        and blockers_empty
        and (
            name not in REQUIRED_PLANNING_ONLY_CHECKS
            or (
                report.get("valid") is True
                and report.get("planning_only") is True
                and report.get("accepted_for_planning") is True
            )
        )
        and not public_or_runtime_claims
    )
    if name in REQUIRED_LOCKED_CHILD_CHECKS:
        check_valid = (
            check_valid
            and report is not None
            and report.get("dependency_chain_locked") is True
            and report.get("current_route_blocker") in ALLOWED_IDENTITY_LOCK_BLOCKERS
            and isinstance(report.get("remaining_route_blockers"), list)
            and report.get("remaining_route_blockers") != []
            and all(report.get(key) is False for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS)
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
        "dependency_chain_locked": report.get("dependency_chain_locked") if report is not None else None,
        "current_route_blocker": report.get("current_route_blocker") if report is not None else None,
        "remaining_route_blockers": report.get("remaining_route_blockers") if report is not None else None,
        "counts_toward_public_sdk": report.get("counts_toward_public_sdk") if report is not None else None,
        "counts_toward_runtime": report.get("counts_toward_runtime") if report is not None else None,
        "counts_toward_v1_completion": report.get("counts_toward_v1_completion") if report is not None else None,
        "public_or_runtime_accounting_allowed": (
            report.get("public_or_runtime_accounting_allowed") if report is not None else None
        ),
        "public_or_runtime_claims": public_or_runtime_claims,
        "blockers": report_blockers,
        "parse_error": parse_error,
        "stderr": result.stderr.strip(),
        "report_payload": report,
    }


def resolved_path_text(value: Any) -> str | None:
    if not isinstance(value, (str, Path)) or not str(value):
        return None
    return str(Path(value).resolve())


def identity_manifest_source_diagnostics(
    args: argparse.Namespace | None,
    source_report: dict[str, Any] | None,
) -> dict[str, Any]:
    source_specs = {
        "lifecycle_anchor_candidates": {
            "arg": "player_identity_lifecycle_anchor_candidates_manifest",
            "report_key": "lifecycle_anchor_candidates_manifest",
            "default": DEFAULT_PLAYER_IDENTITY_LIFECYCLE_ANCHOR_CANDIDATES,
        },
        "principal_invalidation_policy": {
            "arg": "player_identity_principal_invalidation_policy_manifest",
            "report_key": "principal_invalidation_policy_manifest",
            "default": DEFAULT_PLAYER_IDENTITY_PRINCIPAL_INVALIDATION_POLICY,
        },
    }
    manifests: dict[str, Any] = {}
    for name, spec in source_specs.items():
        cli_value = getattr(args, spec["arg"], None) if args is not None else None
        expected_path = cli_value or spec["default"]
        observed_path = source_report.get(spec["report_key"]) if source_report is not None else None
        expected_resolved = resolved_path_text(expected_path)
        observed_resolved = resolved_path_text(observed_path)
        manifests[name] = {
            "source": "cli_bound" if cli_value is not None else "repo_local_default",
            "provided_by_cli": cli_value is not None,
            "expected_path": str(expected_path),
            "expected_resolved_path": expected_resolved,
            "observed_path": observed_path,
            "observed_resolved_path": observed_resolved,
            "matched": expected_resolved is not None and expected_resolved == observed_resolved,
        }
    mode = "cli_bound" if all(item["provided_by_cli"] for item in manifests.values()) else "repo_local_default"
    return {
        "mode": mode,
        "report_available": source_report is not None,
        "expected_manifests_received": all(item["matched"] for item in manifests.values()),
        "manifests": manifests,
        "non_claim": (
            "manifest source diagnostics bind identity planning inputs only; they do not promote "
            "public identity, permissions, commands, runtime readiness, or SDK completion"
        ),
    }


def build_critical_path_phase(args: argparse.Namespace | None = None) -> dict[str, Any]:
    result = subprocess.run(
        identity_readiness_argv(args),
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

    primary_blocker = None
    next_blocker = None
    if report is not None:
        primary_blocker = report.get("primary_blocker")
        next_blocker = report.get("next_blocker")
    source_blockers = report.get("blockers") if report is not None else None
    source_claims = (
        collect_public_or_runtime_claims(report, include_text_claims=False) if report is not None else []
    )
    current_blocker = primary_blocker or next_blocker
    manifest_sources = identity_manifest_source_diagnostics(args, report)
    approved_runtime_evidence_manifest = None
    if report is not None:
        first_evidence = report.get("first_evidence")
        if isinstance(first_evidence, dict):
            approved_runtime_evidence_manifest = first_evidence.get(
                "approved_runtime_principal_lifecycle_evidence_manifest"
            )

    blocker_route = ALLOWED_IDENTITY_LOCK_BLOCKERS.get(str(current_blocker), {})
    return {
        "current_surface": "obelisk.player_identity.v1",
        "current_blocker": current_blocker,
        "source_checker_primary_blocker": primary_blocker,
        "source_checker_next_blocker": next_blocker,
        "next_action": blocker_route.get("next_action", "resolve_identity_lock_blocker"),
        "next_after_runtime_evidence": "identity_public_contract_gate_missing",
        "permissions_admin_unlocked": False,
        "command_response_unlocked": False,
        "commands_replies_unlocked": False,
        "source_checker": "check_player_identity_first_evidence_readiness.py",
        "source_checker_exit_code": result.returncode,
        "source_checker_schema": report.get("schema") if report is not None else None,
        "source_checker_parse_error": parse_error,
        "source_checker_status": report.get("status") if report is not None else None,
        "source_checker_ready": report.get("ready") if report is not None else None,
        "source_checker_accepted_for_internal_planning": (
            report.get("accepted_for_internal_planning") if report is not None else None
        ),
        "source_checker_blockers": source_blockers,
        "source_checker_public_or_runtime_claims": source_claims,
        "source_checker_manifest_sources": manifest_sources,
        "source_checker_approved_runtime_evidence_manifest": approved_runtime_evidence_manifest,
        "planning_only": True,
        "promotion_ready": report.get("promotion_ready") is True if report is not None else None,
        "public_sdk_ready": report.get("public_sdk_ready") is True if report is not None else None,
        "public_abi_ready": report.get("public_abi_ready") is True if report is not None else None,
        "runtime_ready": report.get("runtime_ready") is True if report is not None else None,
    }


def validate_critical_path_phase(phase: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if phase.get("current_surface") != "obelisk.player_identity.v1":
        blockers.append("critical_path_identity_gate_not_locked")
    if phase.get("source_checker_schema") != PLAYER_IDENTITY_FIRST_EVIDENCE_SCHEMA:
        blockers.append("critical_path_identity_readiness_schema_mismatch")
    if phase.get("source_checker_parse_error") is not None:
        blockers.append("critical_path_identity_readiness_output_invalid")
    if phase.get("source_checker_exit_code") != 1:
        blockers.append("critical_path_identity_readiness_exit_code_unexpected")
    if phase.get("source_checker_status") != "blocked":
        blockers.append("critical_path_identity_readiness_status_unexpected")
    if phase.get("source_checker_ready") is not False:
        blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
    if phase.get("source_checker_accepted_for_internal_planning") is not False:
        blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
    if phase.get("source_checker_primary_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
        blockers.append("critical_path_identity_readiness_blocker_missing")
    manifest_sources = phase.get("source_checker_manifest_sources")
    if not isinstance(manifest_sources, dict):
        blockers.append("critical_path_identity_readiness_manifest_sources_missing")
    elif manifest_sources.get("expected_manifests_received") is not True:
        blockers.append("critical_path_identity_readiness_expected_manifests_missing")
    source_blockers = phase.get("source_checker_blockers")
    primary_blocker = phase.get("source_checker_primary_blocker")
    if not isinstance(source_blockers, list):
        blockers.append("critical_path_identity_readiness_blockers_missing")
    elif primary_blocker in ALLOWED_IDENTITY_LOCK_BLOCKERS and primary_blocker not in source_blockers:
        blockers.append("critical_path_identity_readiness_primary_blocker_not_in_blockers")
    source_claims = phase.get("source_checker_public_or_runtime_claims")
    if isinstance(source_claims, list) and source_claims:
        blockers.append("critical_path_identity_readiness_public_or_runtime_claim")
    if phase.get("current_blocker") is None:
        blockers.append("critical_path_identity_gate_current_blocker_missing")
    if phase.get("current_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
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
            if key in {"promotion_ready", "public_sdk_ready", "public_abi_ready", "runtime_ready"}:
                blockers.append("critical_path_identity_readiness_ready_flag_overclaim")
            else:
                blockers.append(f"critical_path_{key}_must_stay_false")
    return blockers


def validate_locked_child_route_alignment(
    checks: list[dict[str, Any]],
    *,
    current_route_blocker: Any,
    remaining_route_blockers: list[Any],
) -> list[str]:
    blockers: list[str] = []
    expected_child_blocker = (
        None
        if current_route_blocker in UPSTREAM_IDENTITY_LOCK_BLOCKERS
        else "approved_runtime_evidence_missing"
    )
    expected_child_blockers = [expected_child_blocker] if expected_child_blocker is not None else []
    for check in checks:
        if check["name"] not in REQUIRED_LOCKED_CHILD_CHECKS:
            continue
        if check.get("current_route_blocker") != expected_child_blocker:
            blockers.append(f"{check['name']}: current_route_blocker drifted from downstream lock")
        if check.get("remaining_route_blockers") != expected_child_blockers:
            blockers.append(f"{check['name']}: remaining_route_blockers drifted from downstream lock")
    return blockers


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    critical_path_phase = build_critical_path_phase(args)
    current_route_blocker = critical_path_phase.get("current_blocker")
    approved_runtime_evidence_accepted = approved_runtime_evidence_ready_for_identity_lock(critical_path_phase)
    child_route_blocker = (
        None
        if current_route_blocker in UPSTREAM_IDENTITY_LOCK_BLOCKERS
        else "approved_runtime_evidence_missing"
    )
    checks = []
    response_path_report: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(prefix="obelisk-command-route-gate-") as tmp:
        response_path_report_root = Path(tmp) / "command-chat-response-public-readiness"
        response_path_report_path = response_path_report_root / "command-chat-response-public-readiness.json"
        for name, argv in route_checks(
            args,
            current_route_blocker=child_route_blocker,
            approved_runtime_evidence_accepted=approved_runtime_evidence_accepted,
        ):
            effective_argv = list(argv)
            if name == "commands_replies_public_readiness":
                if response_path_report is not None:
                    response_path_report_root.mkdir(parents=True, exist_ok=True)
                    response_path_report_path.write_text(
                        json.dumps(response_path_report, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
                    effective_argv.extend(["--response-path-report", str(response_path_report_path)])
                    effective_argv.extend(["--response-path-report-root", str(response_path_report_root)])
                    response_root = args.command_response_root or response_path_report.get("readiness_root")
                    response_readiness = args.command_response_readiness or response_path_report.get("readiness_path")
                    if response_root is not None:
                        effective_argv.extend(["--response-path-root", str(response_root)])
                    if response_readiness is not None:
                        effective_argv.extend(["--response-path-readiness", str(response_readiness)])
            check = run_check(name, effective_argv)
            checks.append(check)
            if name == "command_chat_response_public_readiness":
                payload = check.get("report_payload")
                if isinstance(payload, dict):
                    response_path_report = payload
    blockers = validate_command_response_readiness_binding(args)
    blockers.extend(validate_command_response_child_readiness_context(args, response_path_report))
    blockers.extend(validate_identity_planning_binding_args(args))
    for check in checks:
        if check["name"] == "commands_replies_public_readiness" and "--response-path-report" not in check["argv"]:
            blockers.append("commands_replies_public_readiness: missing composed response path report")
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
        if check["blockers"]:
            blockers.append(f"{check['name']}: child blockers not empty")
        if check["name"] in REQUIRED_PLANNING_ONLY_CHECKS:
            if check["planning_only"] is not True:
                blockers.append(f"{check['name']}: planning_only must stay true")
            if check["accepted_for_planning"] is not True:
                blockers.append(f"{check['name']}: accepted_for_planning must stay true")
        if check["name"] in REQUIRED_LOCKED_CHILD_CHECKS:
            if check.get("dependency_chain_locked") is not True:
                blockers.append(f"{check['name']}: dependency_chain_locked must stay true")
            if check.get("current_route_blocker") not in ALLOWED_IDENTITY_LOCK_BLOCKERS:
                blockers.append(f"{check['name']}: current_route_blocker must stay an identity lock blocker")
            if not check.get("remaining_route_blockers"):
                blockers.append(f"{check['name']}: remaining_route_blockers must stay non-empty")
            for key in REQUIRED_CHILD_ACCOUNTING_FALSE_KEYS:
                if check.get(key) is not False:
                    blockers.append(f"{check['name']}: {key} must stay false")
        if not check["valid"]:
            blockers.append(f"{check['name']}: invalid route prerequisite")
    blockers.extend(validate_critical_path_phase(critical_path_phase))
    blockers.extend(validate_identity_lock_mode(args, critical_path_phase))
    remaining_route_blockers = [current_route_blocker] if current_route_blocker is not None else []
    route_blocked = bool(remaining_route_blockers)
    route_lock_blockers = route_lock_blocked_until(current_route_blocker)
    blockers.extend(
        validate_locked_child_route_alignment(
            checks,
            current_route_blocker=current_route_blocker,
            remaining_route_blockers=remaining_route_blockers,
        )
    )

    return {
        "schema": REPORT_SCHEMA,
        "valid": not blockers,
        "accepted_for_planning": not blockers,
        "planning_only": True,
        "route_blocked": route_blocked,
        "dependency_chain_locked": route_blocked,
        "route_lock_invariant_valid": not blockers,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "next_route_action": critical_path_phase.get("next_action"),
        "next_route_blocker_after_runtime_evidence": critical_path_phase.get("next_after_runtime_evidence"),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_abi_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "public_or_runtime_accounting_allowed": False,
        "dependency_chain": [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ],
        "critical_path_phase": critical_path_phase,
        "route_lock": {
            "locked": route_blocked,
            "invariant_valid": not blockers,
            "blocked_until": route_lock_blockers,
            "non_claim": "route lock is an offline invariant; it does not promote identity, permissions, commands, runtime readiness, or v1 completion",
        },
        "checks": [
            {key: value for key, value in check.items() if key != "report_payload"}
            for check in checks
        ],
        "blockers": blockers,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
