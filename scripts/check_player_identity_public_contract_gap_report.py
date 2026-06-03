#!/usr/bin/env python3
"""Offline gap report guardrail for blocked player identity public contract state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_identifier_redaction_evidence as redaction_checker
import check_player_identity_principal_invalidation_policy as principal_invalidation_policy
import check_player_identity_public_abi_preflight_candidate as public_abi_preflight_candidate
import check_player_identity_private_pod_layout_candidate as private_pod_layout_candidate
import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_evidence
import build_player_identity_planning_source_manifests as planning_source_manifests


SCHEMA = "obelisk.player-identity-public-contract-gap-report.v1"
DECISIONS_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PRIVATE_CANDIDATE_SCHEMA = "obelisk.player-identity-private-candidate-contract.v1"
SURFACE = "obelisk.player_identity.v1"
PRIMARY_OFFLINE_GAP = "privacy.identifier_redaction"
PRIMARY_OFFLINE_GAP_AFTER_IDENTIFIER_REDACTION = "lifetime.generation_scope_invalidation"
PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT = "lifetime.generation_scope_invalidation.candidate_policy"
DEFAULT_IDENTIFIER_REDACTION_EVIDENCE = Path(
    "docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json"
)
DEFAULT_PRINCIPAL_INVALIDATION_POLICY = Path(
    "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json"
)
DEFAULT_PRIVATE_CONTRACT = Path("docs/research/2026-06-01-player-identity-private-candidate-contract.json")
DEFAULT_PRIVATE_POD_LAYOUT_CANDIDATE = Path(
    "docs/research/player-identity-planning-sources/player-identity-private-pod-layout-candidate.json"
)
DEFAULT_PUBLIC_ABI_PREFLIGHT_CANDIDATE = Path(
    "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json"
)
DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT = Path(
    "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json"
)
DEFAULT_PLANNING_SOURCES_DIR = Path("docs/research/player-identity-planning-sources")
APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT = "runtime.lifecycle_evidence"
APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER = "identity_public_contract_gate_missing"
REQUIRED_PLANNING_SOURCE_VERIFICATION_INTAKE_ID = "source_bound_planning_manifest_verification"
REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT = "planning.source_bound_committed_manifests"
REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER = (
    "scripts/build_player_identity_planning_source_manifests.py --verify-existing-dir"
)
REQUIRED_PLANNING_SOURCE_VERIFICATION_NON_CLAIM = (
    "A valid source-bound planning manifest verification is contract-review provenance only; it does not "
    "promote player identity, public SDK/header/runtime readiness, public ABI, runtime authorization, or v1 completion."
)
PLANNING_SOURCE_VERIFICATION_REPORT_NON_CLAIMS = [
    "source-bound planning manifest verification is provenance-only contract-review input",
    "source-bound planning manifest verification grants no authorization or promotion",
]
FORBIDDEN_APPROVED_RUNTIME_RESOLVED_INPUT_TOKENS = (
    "request_pack",
    "request-pack",
    "preflight",
    "window_manifest",
    "window-manifest",
    "operator_receipt",
    "operator-receipt",
    "operator_approval_receipt",
    "operator-approval-receipt",
    "sidecar",
    "observer_env",
    "observer-env",
    "live_ops",
    "live-ops",
)
REQUIRED_APPROVED_RUNTIME_EVIDENCE_INTAKE_ID = "approved_runtime_principal_lifecycle_evidence"
REQUIRED_APPROVED_RUNTIME_EVIDENCE_CHECKER = "scripts/check_player_identity_public_contract_readiness.py"
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM = (
    "A valid approved runtime evidence manifest can resolve only the runtime lifecycle "
    "evidence input for contract review; it does not promote public player identity or open ABI."
)
REQUIRED_APPROVED_RUNTIME_READY_SCOPE = "runtime_evidence_only"
REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES = [
    "observer_enable",
    "session_start_anchor",
    "session_start_rejected_anchor",
    "session_end_anchor",
]
REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES = [
    "malformed_or_unsupported_evidence",
    "stale_after_logout",
]
REQUIRED_IDENTIFIER_REDACTION_CHECKER = "scripts/check_player_identity_identifier_redaction_evidence.py"
REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER = "scripts/check_player_identity_principal_invalidation_policy.py"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_INTAKE_ID = "public_abi_preflight_candidate"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT = "abi.public_pod_contract.public_abi_preflight_candidate"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER = "scripts/check_player_identity_public_abi_preflight_candidate.py"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_NON_CLAIM = (
    "A valid public ABI preflight candidate is offline routing evidence only; it does not resolve the public "
    "POD ABI, add header symbols, add capability bits, expose callbacks, satisfy SDK consumer tests, promote "
    "player identity, or count toward v1 completion."
)
REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_INTAKE_ID = "owner_token_sdk_consumer_contract"
REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT = (
    "lifecycle.owner_cleanup.owner_token_sdk_consumer_contract"
)
REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_CHECKER = (
    "scripts/check_player_identity_owner_token_sdk_consumer_contract.py"
)
REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_NON_CLAIM = (
    "A valid owner-token SDK consumer contract is candidate-only cleanup/lifecycle review evidence; it does "
    "not resolve lifecycle.owner_cleanup, add public header symbols, add capability bits, expose callbacks, "
    "promote player identity, or count toward v1 completion."
)
REQUIRED_PROMOTION_BLOCKERS = {
    "runtime.lifecycle_evidence",
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation",
    "abi.public_pod_contract",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
REQUIRED_CONTRACT_GATE_INPUTS = {
    "runtime.lifecycle_evidence": {
        "review_inputs": {"runtime.lifecycle_evidence"},
        "remaining_promotion_inputs": set(),
    },
    "privacy.identifier_redaction": {
        "review_inputs": {"privacy.identifier_redaction"},
        "remaining_promotion_inputs": {
            "privacy.public_identifier_form",
            "privacy.redacted_identifier_fields",
            "privacy.logging_and_storage_policy",
        },
    },
    "lifetime.generation_scope_invalidation": {
        "review_inputs": {"lifetime.generation_scope_invalidation.candidate_policy"},
        "remaining_promotion_inputs": {
            "lifetime.principal_scope",
            "lifetime.invalidation_events",
            "lifetime.reconnect_duplicate_stale_policy",
        },
    },
    "abi.public_pod_contract": {
        "review_inputs": {
            "abi.public_pod_contract.private_layout_candidate",
            "abi.public_pod_contract.public_abi_preflight_candidate",
        },
        "remaining_promotion_inputs": {
            "abi.payload_shape",
            "abi.capability_bits",
            "abi.append_only_layout_tests",
            "abi.layout",
            "sdk.consumer",
        },
    },
    "lifecycle.owner_cleanup": {
        "review_inputs": {"lifecycle.owner_cleanup.owner_token_sdk_consumer_contract"},
        "remaining_promotion_inputs": {
            "abi.owner_token_registration",
            "lifecycle.owner_cleanup.runtime_tests",
        },
    },
    "separation.downstream_surfaces": {
        "review_inputs": {"separation.no_commands_permissions_persistence"},
        "remaining_promotion_inputs": {
            "permissions_admin_contract_blocker",
            "command_chat_response_contract_blocker",
            "commands_replies_contract_blocker",
            "player_lookup_exclusion_review",
            "storage_persistence_exclusion_review",
        },
    },
}
REQUIRED_PRIVACY_PUBLIC_HEADER_BLOCKERS = {
    "evidence.complete_non_protected_pack",
    "evidence.accepted_session_start_anchor",
    "evidence.accepted_session_end_anchor",
    "evidence.second_source_anchor_layout",
    "privacy.public_identifier_form",
    "privacy.redacted_identifier_fields",
    "privacy.logging_and_storage_policy",
    "lifetime.principal_scope",
    "lifetime.invalidation_events",
    "lifetime.reconnect_duplicate_stale_policy",
    "abi.payload_shape",
    "abi.capability_bits",
    "abi.owner_token_registration",
    "abi.append_only_layout_tests",
    "separation.no_commands_permissions_persistence",
}
REQUIRED_DECISION_GATE_CURRENT_DECISION = (
    "no public header, no public capability bit, no plugin callback, no lookup, "
    "no downstream permission or command dependency may consume identity yet"
)
REQUIRED_DECISION_GATE_SCOPE = (
    "v1 copied opaque player principal blocker; excludes lookup and downstream "
    "permission/command/storage surfaces until separately promoted."
)
REQUIRED_DECISION_GATE_ALLOWED_NOW = {
    "document blockers",
    "document candidate POD shape",
    "document non-claims",
    "document tests required before promotion",
}
REQUIRED_DECISION_GATE_FORBIDDEN_NOW = {
    "C++ ABI edits",
    "public header symbols",
    "runtime plugin callback exposure",
    "player lookup API",
    "permission/admin API",
    "command/chat response API",
    "storage or persistence API",
}
REQUIRED_FORBIDDEN_PUBLIC_CONTRACT = {
    "UE pointers",
    "raw params",
    "FName/GObjects indices",
    "ResourceHandle",
    "pointer-derived identity",
    "lookup",
    "mutation",
    "return override",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY = {
    "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics",
    "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES = {
    "privacy and redaction decision resolved",
    "principal lifetime and invalidation decision resolved",
    "cross-instance/process-local scope decision resolved",
    "public docs state exact non-claims and downstream dependency order",
}
REQUIRED_PUBLIC_IDENTIFIER_FORBIDDEN = {
    "SteamID",
    "EOS ID",
    "UniqueNetId",
    "PlayerDataID",
    "tribe ID",
    "player name",
    "IP address",
    "UE pointer",
    "FName/GObjects index",
    "ResourceHandle",
}
REQUIRED_PUBLIC_IDENTIFIER_PROPERTIES = {
    "process-local by default",
    "not persistent unless a future storage/ingress contract promotes persistence",
    "generation-bearing or otherwise invalidation-aware",
    "safe to copy across the C ABI as POD",
}
REQUIRED_REDACTION_CLASSES = {
    "copied opaque principal",
    "recognition-only",
    "private-redacted",
    "forbidden",
}
REQUIRED_REDACTED_FIELDS = {
    "platform account ids",
    "player names",
    "tribe identifiers",
    "network addresses",
    "raw chat text used as identity",
    "controller/playerstate object references",
}
REQUIRED_ALLOWED_SCOPES = {"callback-local", "process-local", "restart-local"}
REQUIRED_FORBIDDEN_SCOPES = {"cluster-stable", "persistent", "cross-map shared"}
REQUIRED_SCOPE_FIELDS = {"principal_handle", "principal_generation", "scope_flags"}
REQUIRED_INVALIDATION_EVENTS = {
    "disconnect",
    "logout",
    "transfer",
    "reconnect",
    "duplicate principal observation",
    "server restart",
    "stale controller/playerstate",
    "failed evidence validation",
}
REQUIRED_INVALIDATION_BEHAVIOR = {
    "stale principal fails closed",
    "permission decisions include generation or are callback-local only",
    "commands/replies reject stale principal handles",
}
REQUIRED_STALE_POLICY = {
    "new generation on reconnect unless evidence proves continuity",
    "duplicate observations invalidate or quarantine both principals",
    "stale handles never resolve to a different player",
    "lookup-by-public-handle remains unavailable unless separately promoted",
}
REQUIRED_PRIVATE_CANDIDATE_STALE_HANDLE_FAIL_CLOSED_SEMANTICS = {
    "principal_handle, principal_generation, and principal_scope_flags must be evaluated as one tuple",
    "missing principal_generation fails closed",
    "missing principal_scope_flags fails closed",
    "stale generation fails closed",
    "unsupported scope fails closed",
    "server_process_epoch mismatch fails closed",
    "stale handles never resolve to a different player",
    "lookup-by-public-handle remains unavailable unless separately promoted",
}
REQUIRED_ABI_PAYLOAD_SHAPE_PROPERTIES = {
    "POD C ABI",
    "append-only after promotion",
    "copied Obelisk-owned storage",
    "callback-local payload lifetime",
    "no UE pointers or raw params",
    "no platform account ids, player names, tribe ids, or network addresses",
    "no lookup, persistence, mutation, or return override",
}
REQUIRED_CAPABILITY_BEHAVIOR = {
    "capability is absent while this gate is blocked/planning",
    "missing capability fails closed",
    "later env or marker changes cannot widen a loaded plugin's captured capability",
}
REQUIRED_OWNER_TOKEN_BEHAVIOR = {
    "nonzero plugin_owner_token required",
    "registration handles are not persisted or shared across server processes",
    "init failure and plugin unload remove all owner registrations",
}
REQUIRED_SEQUENCE_GATE = [
    "identity principal contract first",
    "permission query contract only after identity promotion",
    "command response contract only after permission result provenance is promoted",
    "commands/replies only after command response privacy, generation, and scope gates are promoted",
]
REQUIRED_SEPARATION_FORBIDDEN = {
    "permission query API",
    "permission cache API",
    "command response API",
    "command router",
    "replies/send-chat",
    "admin mutation",
    "storage/persistence",
    "operator ingress",
}

READINESS_FALSE_KEYS = {
    "accepted_for_contract_review",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_contract_allowed",
    "public_abi_ready",
    "v1_completion_evidence",
}
EMPTY_PUBLIC_LIST_KEYS = {
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_callback_abi_now",
}
NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES = (
    ".private_pod_layout_candidate.accepted_for_contract_review",
    ".identifier_redaction_evidence.accepted_for_contract_review",
)
HEADER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
}
HEADER_SYMBOL_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net_?id|"
    r"player_?(?:data_?id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"redact(?:ed|ion)?|excludes?|without|until|missing|blocked|blocker|unavailable|"
    r"must[_ -]?not[_ -]?expose|no_)\b",
    re.IGNORECASE,
)
FORBIDDEN_CANDIDATE_EXPOSURE_PATTERNS = {
    "steam_id": re.compile(r"\bsteam(?:[_ -]?id)?\b", re.IGNORECASE),
    "eos": re.compile(r"\beos(?:\b|[_ -])|epic[_ -]?online[_ -]?services", re.IGNORECASE),
    "unique_net_id": re.compile(r"unique[_ -]?net[_ -]?id", re.IGNORECASE),
    "player_data_id": re.compile(r"player[_ -]?data[_ -]?id", re.IGNORECASE),
    "player_name": re.compile(r"player[_ -]?names?\b|\bnombres?\b|\bdisplay[_ -]?name\b", re.IGNORECASE),
    "tribe": re.compile(r"\btribe(?:[_ -]?id|[_ -]?identifier)?s?\b", re.IGNORECASE),
    "ip_or_network_address": re.compile(r"\bIP\b|ip[_ -]?address(?:es)?|network[_ -]?address(?:es)?", re.IGNORECASE),
    "ue_pointer": re.compile(r"\bUE\b|UObject|UClass|UFunction|AActor|pointer", re.IGNORECASE),
    "fname_gobjects": re.compile(r"FName|GObjects", re.IGNORECASE),
    "resource_handle": re.compile(r"ResourceHandle|resource[_ -]?handle", re.IGNORECASE),
    "lookup": re.compile(r"\blookup\b|lookup_", re.IGNORECASE),
    "persistence": re.compile(r"\bpersist(?:ent|ed|ence|s|ing)?(?:\b|[_ -])", re.IGNORECASE),
    "mutation": re.compile(r"\bmutat(?:e|ion|ing|able)(?:\b|[_ -])", re.IGNORECASE),
    "return_override": re.compile(r"return[_ -]?override", re.IGNORECASE),
}
ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS = {
    "approved_runtime_evidence_present",
    "runtime_evidence_ready",
}
APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE = re.compile(
    r"(?:"
    r"public|sdk|abi|capability|callback|header|identity|principal|permission|admin|"
    r"command|chat|reply|lookup|storage|persist|mutation|return[_ -]?override|resource[_ -]?handle|v1"
    r").*(?:ready|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|complete|supported|available)"
    r"|(?:ready|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|complete|supported|available).*"
    r"(?:public|sdk|abi|identity|principal|permission|admin|command|chat|reply|lookup|storage|persist|mutation|"
    r"return[_ -]?override|resource[_ -]?handle|v1)",
    re.IGNORECASE,
)
APPROVED_RUNTIME_REPORT_OVERCLAIM_VALUE_PATTERNS = {
    "public_identity_ready": re.compile(r"public\s+(?:player\s+)?identity\s+(?:is\s+)?ready", re.IGNORECASE),
    "public_sdk_ready": re.compile(r"public\s+sdk\s+(?:is\s+)?ready", re.IGNORECASE),
    "public_abi_ready": re.compile(r"public\s+abi\s+(?:is\s+)?ready", re.IGNORECASE),
    "v1_completion_ready": re.compile(r"v1\s+(?:sdk\s+)?completion\s+(?:is\s+)?ready", re.IGNORECASE),
    "capability_available": re.compile(r"(?:identity\s+)?capability\s+(?:bit\s+)?(?:is\s+)?available", re.IGNORECASE),
    "downstream_unlocked": re.compile(
        r"(?:identity|principal).*unlock(?:s|ed)?\s+(?:permission|admin|command|chat|reply|lookup|storage)",
        re.IGNORECASE,
    ),
    "lookup_allowed": re.compile(r"(?:player\s+)?lookup\s+(?:is\s+)?allowed", re.IGNORECASE),
    "mutation_allowed": re.compile(r"mutation\s+(?:is\s+)?allowed", re.IGNORECASE),
    "return_override_allowed": re.compile(r"return[_ -]?override\s+(?:is\s+)?allowed", re.IGNORECASE),
    "resource_handle_supported": re.compile(r"resource[_ -]?handle\s+(?:is\s+)?supported", re.IGNORECASE),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("docs/player_identity_public_contract_decisions.json"),
        help="Player identity public contract decision manifest.",
    )
    parser.add_argument(
        "--surfaces",
        type=Path,
        default=Path("docs/public_sdk_surfaces.json"),
        help="Public SDK surfaces manifest.",
    )
    parser.add_argument(
        "--private-candidate-contract",
        type=Path,
        default=Path("docs/research/2026-06-01-player-identity-private-candidate-contract.json"),
        help="Private candidate-only player identity contract artifact.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=Path("include/obelisk/ObeliskApi.h"),
        help="Public SDK header to scan for accidental identity/principal symbols.",
    )
    parser.add_argument(
        "--identifier-redaction-evidence",
        type=Path,
        default=DEFAULT_IDENTIFIER_REDACTION_EVIDENCE,
        help="Sanitized identifier-redaction evidence manifest consumed as contract-review input only.",
    )
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        help=(
            "Optional approved runtime principal lifecycle evidence manifest consumed as "
            "contract-review input only; never promotion or public SDK evidence."
        ),
    )
    parser.add_argument(
        "--principal-invalidation-policy",
        type=Path,
        default=DEFAULT_PRINCIPAL_INVALIDATION_POLICY,
        help="Candidate-only principal invalidation policy consumed as lifetime/generation/scope review input only.",
    )
    parser.add_argument(
        "--planning-sources-dir",
        type=Path,
        default=DEFAULT_PLANNING_SOURCES_DIR,
        help="Committed source-bound player identity planning manifests directory.",
    )
    parser.add_argument(
        "--planning-source-snapshot-root",
        type=Path,
        default=planning_source_manifests.build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized UFunction snapshot root used to verify committed planning manifests.",
    )
    parser.add_argument(
        "--private-pod-layout-candidate",
        type=Path,
        default=DEFAULT_PRIVATE_POD_LAYOUT_CANDIDATE,
        help="Candidate-only private POD layout evidence consumed as ABI contract-review input only.",
    )
    parser.add_argument(
        "--public-abi-preflight-candidate",
        type=Path,
        default=DEFAULT_PUBLIC_ABI_PREFLIGHT_CANDIDATE,
        help="Candidate-only public ABI preflight routing artifact; never promotion evidence.",
    )
    parser.add_argument(
        "--owner-token-sdk-consumer-contract",
        type=Path,
        default=DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT,
        help="Candidate-only owner-token SDK consumer contract; never promotion evidence.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def normalize_contract_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"--{label}", path=str(path), error=str(exc))
        return {}
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"--{label}", path=str(path), error=str(exc))
        return {}
    if not isinstance(value, dict):
        add(blockers, f"{label}_not_object", f"--{label}", path=str(path))
        return {}
    return value


def walk_json(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk_json(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_json(item, f"{path}[{index}]")


def walk_json_keys(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child_path = f"{path}.{key}"
            yield child_path, key
            yield from walk_json_keys(item, child_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk_json_keys(item, f"{path}[{index}]")


def validate_false_flags(value: Any, blockers: list[dict[str, Any]], label: str) -> None:
    for path, item in walk_json(value):
        key = path.rsplit(".", 1)[-1]
        if normalize_contract_key(key) in READINESS_FALSE_KEYS and item is not False:
            add(blockers, "readiness_flag_not_false", path, input=label, value=item)


def validate_empty_public_lists(value: Any, blockers: list[dict[str, Any]], label: str) -> None:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        normalized_key = normalize_contract_key(key)
        if normalized_key in EMPTY_PUBLIC_LIST_KEYS and item != []:
            add(blockers, f"{normalized_key}_not_empty", f"$.{key}", input=label, value=item)


def sanitize_non_promotional_report(
    value: Any,
    blockers: list[dict[str, Any]],
    *,
    input_label: str,
    path: str,
    root_path: str | None = None,
) -> Any:
    """Copy a nested checker report while forcing public/promotion outputs closed."""

    root_path = root_path or path
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            contract_review_allowed = (
                normalized_key == "accepted_for_contract_review"
                and path != root_path
                and item_path.endswith(NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES)
            )
            if normalized_key in READINESS_FALSE_KEYS and not contract_review_allowed:
                if item is not False:
                    add(blockers, "nested_readiness_flag_not_false", item_path, input=input_label, value=item)
                sanitized[key] = False
            elif normalized_key in EMPTY_PUBLIC_LIST_KEYS:
                if item != []:
                    add(blockers, f"nested_{normalized_key}_not_empty", item_path, input=input_label, value=item)
                sanitized[key] = []
            else:
                sanitized[key] = sanitize_non_promotional_report(
                    item,
                    blockers,
                    input_label=input_label,
                    path=item_path,
                    root_path=root_path,
                )
        return sanitized
    if isinstance(value, list):
        return [
            sanitize_non_promotional_report(
                item,
                blockers,
                input_label=input_label,
                path=f"{path}[{index}]",
                root_path=root_path,
            )
            for index, item in enumerate(value)
        ]
    return value


def string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value


def missing_required(observed: Any, required: set[str]) -> list[str]:
    values = string_list(observed)
    if values is None:
        return sorted(required)
    return sorted(required - set(values))


def require_string_list_contains(
    value: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    reason: str,
    label: str,
) -> None:
    missing = missing_required(value.get(key), required)
    if missing:
        add(blockers, reason, label, missing=missing, value=value.get(key))


def strip_c_comments_and_strings(text: str) -> str:
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "line_comment"
                continue
            if char == "/" and next_char == "*":
                output.extend((" ", " "))
                index += 2
                state = "block_comment"
                continue
            if char in {"'", '"'}:
                output.append(" ")
                quote = char
                index += 1
                state = "string"
                continue
            output.append(char)
            index += 1
            continue
        if state == "line_comment":
            output.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "code"
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                output.extend((" ", " "))
                index += 2
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "string":
            if char == "\\" and next_char:
                output.extend((" ", " "))
                index += 2
                continue
            if char == quote:
                output.append(" ")
                index += 1
                state = "code"
                continue
            output.append("\n" if char == "\n" else " ")
            index += 1
    return "".join(output)


def scan_public_header(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        stripped = strip_c_comments_and_strings(path.read_text(encoding="utf-8"))
    except OSError as exc:
        add(blockers, "public_header_unreadable", "--public-header", path=str(path), error=str(exc))
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}

    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in HEADER_ALLOWLIST or not HEADER_SYMBOL_RE.search(token) or token in seen:
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    if detected:
        add(
            blockers,
            "public_header_identity_or_principal_symbols_detected",
            "--public-header",
            path=str(path),
            detected_tokens=detected,
        )
    return {"path": str(path), "readable": True, "detected_player_identity_tokens": detected}


def find_surface(surfaces: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        item
        for item in surfaces.get("surfaces", [])
        if isinstance(item, dict) and item.get("id") == SURFACE
    ]
    if len(matches) != 1:
        add(blockers, "player_identity_surface_missing_or_duplicate", "$.surfaces", count=len(matches))
        return {}
    return matches[0]


def validate_required_before_public_header_contract(
    by_id: dict[str, dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    public_form = by_id.get("privacy.public_identifier_form")
    if public_form is not None:
        require_string_list_contains(
            public_form,
            "must_not_expose",
            REQUIRED_PUBLIC_IDENTIFIER_FORBIDDEN,
            blockers,
            "decisions_privacy_public_identifier_form_missing_forbidden_terms",
            "$.required_before_public_header[privacy.public_identifier_form].must_not_expose",
        )
        require_string_list_contains(
            public_form,
            "required_properties",
            REQUIRED_PUBLIC_IDENTIFIER_PROPERTIES,
            blockers,
            "decisions_privacy_public_identifier_form_missing_required_properties",
            "$.required_before_public_header[privacy.public_identifier_form].required_properties",
        )

    redaction = by_id.get("privacy.redacted_identifier_fields")
    if redaction is not None:
        require_string_list_contains(
            redaction,
            "allowed_field_classes",
            REQUIRED_REDACTION_CLASSES,
            blockers,
            "decisions_privacy_redacted_identifier_fields_missing_allowed_classes",
            "$.required_before_public_header[privacy.redacted_identifier_fields].allowed_field_classes",
        )
        require_string_list_contains(
            redaction,
            "must_redact",
            REQUIRED_REDACTED_FIELDS,
            blockers,
            "decisions_privacy_redacted_identifier_fields_missing_redactions",
            "$.required_before_public_header[privacy.redacted_identifier_fields].must_redact",
        )

    logging_policy = by_id.get("privacy.logging_and_storage_policy")
    if logging_policy is not None and logging_policy.get("default_policy") != "no identity persistence and no raw identity logging":
        add(
            blockers,
            "decisions_privacy_logging_storage_default_policy_mismatch",
            "$.required_before_public_header[privacy.logging_and_storage_policy].default_policy",
            value=logging_policy.get("default_policy"),
        )

    scope = by_id.get("lifetime.principal_scope")
    if scope is not None:
        require_string_list_contains(
            scope,
            "allowed_scopes",
            REQUIRED_ALLOWED_SCOPES,
            blockers,
            "decisions_lifetime_principal_scope_missing_allowed_scopes",
            "$.required_before_public_header[lifetime.principal_scope].allowed_scopes",
        )
        require_string_list_contains(
            scope,
            "forbidden_until_separate_promotion",
            REQUIRED_FORBIDDEN_SCOPES,
            blockers,
            "decisions_lifetime_principal_scope_missing_forbidden_scopes",
            "$.required_before_public_header[lifetime.principal_scope].forbidden_until_separate_promotion",
        )
        require_string_list_contains(
            scope,
            "required_fields",
            REQUIRED_SCOPE_FIELDS,
            blockers,
            "decisions_lifetime_principal_scope_missing_required_fields",
            "$.required_before_public_header[lifetime.principal_scope].required_fields",
        )
        allowed_scopes = string_list(scope.get("allowed_scopes"))
        if allowed_scopes is not None:
            forbidden_allowed = sorted(REQUIRED_FORBIDDEN_SCOPES & set(allowed_scopes))
            if forbidden_allowed:
                add(
                    blockers,
                    "decisions_lifetime_principal_scope_forbidden_scope_allowed",
                    "$.required_before_public_header[lifetime.principal_scope].allowed_scopes",
                    forbidden=forbidden_allowed,
                )

    invalidation = by_id.get("lifetime.invalidation_events")
    if invalidation is not None:
        require_string_list_contains(
            invalidation,
            "required_invalidation_events",
            REQUIRED_INVALIDATION_EVENTS,
            blockers,
            "decisions_lifetime_invalidation_events_missing",
            "$.required_before_public_header[lifetime.invalidation_events].required_invalidation_events",
        )
        require_string_list_contains(
            invalidation,
            "required_behavior",
            REQUIRED_INVALIDATION_BEHAVIOR,
            blockers,
            "decisions_lifetime_invalidation_behavior_missing",
            "$.required_before_public_header[lifetime.invalidation_events].required_behavior",
        )

    stale_policy = by_id.get("lifetime.reconnect_duplicate_stale_policy")
    if stale_policy is not None:
        require_string_list_contains(
            stale_policy,
            "required_policy",
            REQUIRED_STALE_POLICY,
            blockers,
            "decisions_lifetime_reconnect_duplicate_stale_policy_missing",
            "$.required_before_public_header[lifetime.reconnect_duplicate_stale_policy].required_policy",
        )

    payload_shape = by_id.get("abi.payload_shape")
    if payload_shape is not None:
        require_string_list_contains(
            payload_shape,
            "required_properties",
            REQUIRED_ABI_PAYLOAD_SHAPE_PROPERTIES,
            blockers,
            "decisions_abi_payload_shape_missing_required_properties",
            "$.required_before_public_header[abi.payload_shape].required_properties",
        )

    capability = by_id.get("abi.capability_bits")
    if capability is not None:
        require_string_list_contains(
            capability,
            "required_behavior",
            REQUIRED_CAPABILITY_BEHAVIOR,
            blockers,
            "decisions_abi_capability_bits_missing_fail_closed_behavior",
            "$.required_before_public_header[abi.capability_bits].required_behavior",
        )

    owner_token = by_id.get("abi.owner_token_registration")
    if owner_token is not None:
        require_string_list_contains(
            owner_token,
            "required_behavior",
            REQUIRED_OWNER_TOKEN_BEHAVIOR,
            blockers,
            "decisions_abi_owner_token_registration_missing_fail_closed_behavior",
            "$.required_before_public_header[abi.owner_token_registration].required_behavior",
        )

    separation = by_id.get("separation.no_commands_permissions_persistence")
    if separation is not None:
        sequence_gate = string_list(separation.get("v1_sequence_gate"))
        if sequence_gate != REQUIRED_SEQUENCE_GATE:
            add(
                blockers,
                "decisions_separation_sequence_gate_mismatch",
                "$.required_before_public_header[separation.no_commands_permissions_persistence].v1_sequence_gate",
                value=separation.get("v1_sequence_gate"),
            )
        require_string_list_contains(
            separation,
            "forbidden_in_identity_contract",
            REQUIRED_SEPARATION_FORBIDDEN,
            blockers,
            "decisions_separation_forbidden_downstream_surfaces_missing",
            "$.required_before_public_header[separation.no_commands_permissions_persistence].forbidden_in_identity_contract",
        )


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if decisions.get("schema") != DECISIONS_SCHEMA:
        add(blockers, "decisions_schema_mismatch", "$.schema", value=decisions.get("schema"))
    if decisions.get("surface") != SURFACE:
        add(blockers, "decisions_surface_mismatch", "$.surface", value=decisions.get("surface"))
    if decisions.get("status") != "blocked":
        add(blockers, "decisions_status_not_blocked", "$.status", value=decisions.get("status"))
    if decisions.get("planning_stage") != "identity_public_contract_gate":
        add(blockers, "decisions_planning_stage_mismatch", "$.planning_stage", value=decisions.get("planning_stage"))
    decision_gate = decisions.get("decision_gate")
    if not isinstance(decision_gate, dict):
        add(blockers, "decisions_decision_gate_missing", "$.decision_gate")
    else:
        if decision_gate.get("id") != "identity_public_contract_gate":
            add(blockers, "decisions_decision_gate_id_mismatch", "$.decision_gate.id", value=decision_gate.get("id"))
        if decision_gate.get("status") != "blocked/planning":
            add(blockers, "decisions_decision_gate_status_mismatch", "$.decision_gate.status", value=decision_gate.get("status"))
        if decision_gate.get("current_decision") != REQUIRED_DECISION_GATE_CURRENT_DECISION:
            add(
                blockers,
                "decisions_decision_gate_current_decision_mismatch",
                "$.decision_gate.current_decision",
                value=decision_gate.get("current_decision"),
            )
        if decision_gate.get("scope") != REQUIRED_DECISION_GATE_SCOPE:
            add(
                blockers,
                "decisions_decision_gate_scope_mismatch",
                "$.decision_gate.scope",
                value=decision_gate.get("scope"),
            )
        allowed_now = string_list(decision_gate.get("allowed_now"))
        if allowed_now is None:
            add(
                blockers,
                "decisions_decision_gate_allowed_now_not_string_list",
                "$.decision_gate.allowed_now",
                value=decision_gate.get("allowed_now"),
            )
        elif set(allowed_now) != REQUIRED_DECISION_GATE_ALLOWED_NOW:
            add(
                blockers,
                "decisions_decision_gate_allowed_now_mismatch",
                "$.decision_gate.allowed_now",
                expected=sorted(REQUIRED_DECISION_GATE_ALLOWED_NOW),
                observed=sorted(allowed_now),
            )
        forbidden_now = string_list(decision_gate.get("forbidden_now"))
        if forbidden_now is None or not REQUIRED_DECISION_GATE_FORBIDDEN_NOW.issubset(set(forbidden_now)):
            add(
                blockers,
                "decisions_decision_gate_forbidden_now_missing_required",
                "$.decision_gate.forbidden_now",
                missing=missing_required(decision_gate.get("forbidden_now"), REQUIRED_DECISION_GATE_FORBIDDEN_NOW),
            )
    if decisions.get("public_header_allowed") is not False:
        add(blockers, "decisions_public_header_allowed_not_false", "$.public_header_allowed")
    if missing_required(decisions.get("forbidden_public_contract"), REQUIRED_FORBIDDEN_PUBLIC_CONTRACT):
        add(
            blockers,
            "decisions_forbidden_public_contract_missing_required",
            "$.forbidden_public_contract",
            missing=missing_required(decisions.get("forbidden_public_contract"), REQUIRED_FORBIDDEN_PUBLIC_CONTRACT),
        )
    approved_runtime_intake = decisions.get("approved_runtime_evidence_intake")
    if not isinstance(approved_runtime_intake, dict):
        add(blockers, "decisions_approved_runtime_evidence_intake_missing", "$.approved_runtime_evidence_intake")
    else:
        if approved_runtime_intake.get("id") != REQUIRED_APPROVED_RUNTIME_EVIDENCE_INTAKE_ID:
            add(blockers, "decisions_approved_runtime_evidence_intake_id_mismatch", "$.approved_runtime_evidence_intake.id")
        if approved_runtime_intake.get("status") != "external_manifest_required":
            add(blockers, "decisions_approved_runtime_evidence_intake_status_mismatch", "$.approved_runtime_evidence_intake.status")
        if approved_runtime_intake.get("resolved_input") != APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT:
            add(
                blockers,
                "decisions_approved_runtime_evidence_intake_resolved_input_mismatch",
                "$.approved_runtime_evidence_intake.resolved_input",
            )
        if approved_runtime_intake.get("required_checker") != REQUIRED_APPROVED_RUNTIME_EVIDENCE_CHECKER:
            add(
                blockers,
                "decisions_approved_runtime_evidence_intake_checker_mismatch",
                "$.approved_runtime_evidence_intake.required_checker",
            )
        if approved_runtime_intake.get("non_claim") != REQUIRED_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM:
            add(
                blockers,
                "decisions_approved_runtime_evidence_intake_non_claim_mismatch",
                "$.approved_runtime_evidence_intake.non_claim",
            )
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
            if approved_runtime_intake.get(key) is not False:
                add(
                    blockers,
                    "readiness_flag_not_false",
                    f"$.approved_runtime_evidence_intake.{key}",
                    input="approved_runtime_evidence_intake",
                    value=approved_runtime_intake.get(key),
                )
    redaction_intake = decisions.get("identifier_redaction_evidence_intake")
    if not isinstance(redaction_intake, dict):
        add(blockers, "decisions_identifier_redaction_evidence_intake_missing", "$.identifier_redaction_evidence_intake")
    else:
        if redaction_intake.get("id") != "identifier_redaction_evidence":
            add(blockers, "decisions_identifier_redaction_evidence_intake_id_mismatch", "$.identifier_redaction_evidence_intake.id")
        if redaction_intake.get("status") != "external_manifest_required":
            add(blockers, "decisions_identifier_redaction_evidence_intake_status_mismatch", "$.identifier_redaction_evidence_intake.status")
        if redaction_intake.get("resolved_input") != PRIMARY_OFFLINE_GAP:
            add(blockers, "decisions_identifier_redaction_evidence_intake_resolved_input_mismatch", "$.identifier_redaction_evidence_intake.resolved_input")
        if redaction_intake.get("required_checker") != REQUIRED_IDENTIFIER_REDACTION_CHECKER:
            add(blockers, "decisions_identifier_redaction_evidence_intake_checker_mismatch", "$.identifier_redaction_evidence_intake.required_checker")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
            if redaction_intake.get(key) is not False:
                add(blockers, "readiness_flag_not_false", f"$.identifier_redaction_evidence_intake.{key}", input="identifier_redaction_evidence_intake", value=redaction_intake.get(key))
    principal_policy_intake = decisions.get("principal_invalidation_policy_evidence_intake")
    if not isinstance(principal_policy_intake, dict):
        add(blockers, "decisions_principal_invalidation_policy_evidence_intake_missing", "$.principal_invalidation_policy_evidence_intake")
    else:
        if principal_policy_intake.get("id") != "principal_invalidation_policy_evidence":
            add(blockers, "decisions_principal_invalidation_policy_evidence_intake_id_mismatch", "$.principal_invalidation_policy_evidence_intake.id")
        if principal_policy_intake.get("status") != "repo_candidate_policy_required":
            add(blockers, "decisions_principal_invalidation_policy_evidence_intake_status_mismatch", "$.principal_invalidation_policy_evidence_intake.status")
        if principal_policy_intake.get("resolved_input") != PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT:
            add(blockers, "decisions_principal_invalidation_policy_evidence_intake_resolved_input_mismatch", "$.principal_invalidation_policy_evidence_intake.resolved_input")
        if principal_policy_intake.get("required_checker") != REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER:
            add(blockers, "decisions_principal_invalidation_policy_evidence_intake_checker_mismatch", "$.principal_invalidation_policy_evidence_intake.required_checker")
        if principal_policy_intake.get("default_manifest") != str(DEFAULT_PRINCIPAL_INVALIDATION_POLICY):
            add(blockers, "decisions_principal_invalidation_policy_evidence_intake_default_manifest_mismatch", "$.principal_invalidation_policy_evidence_intake.default_manifest")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed", "principal_invalidation_ready"):
            if principal_policy_intake.get(key) is not False:
                add(blockers, "readiness_flag_not_false", f"$.principal_invalidation_policy_evidence_intake.{key}", input="principal_invalidation_policy_evidence_intake", value=principal_policy_intake.get(key))
    planning_source_intake = decisions.get("source_bound_planning_manifest_verification_intake")
    if not isinstance(planning_source_intake, dict):
        add(blockers, "decisions_source_bound_planning_manifest_verification_intake_missing", "$.source_bound_planning_manifest_verification_intake")
    else:
        if planning_source_intake.get("id") != REQUIRED_PLANNING_SOURCE_VERIFICATION_INTAKE_ID:
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_id_mismatch", "$.source_bound_planning_manifest_verification_intake.id")
        if planning_source_intake.get("status") != "repo_source_bound_verification_required":
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_status_mismatch", "$.source_bound_planning_manifest_verification_intake.status")
        if planning_source_intake.get("resolved_input") != REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT:
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_resolved_input_mismatch", "$.source_bound_planning_manifest_verification_intake.resolved_input")
        if planning_source_intake.get("required_checker") != REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER:
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_checker_mismatch", "$.source_bound_planning_manifest_verification_intake.required_checker")
        if planning_source_intake.get("default_manifest_dir") != str(DEFAULT_PLANNING_SOURCES_DIR):
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_default_manifest_dir_mismatch", "$.source_bound_planning_manifest_verification_intake.default_manifest_dir")
        if planning_source_intake.get("non_claim") != REQUIRED_PLANNING_SOURCE_VERIFICATION_NON_CLAIM:
            add(blockers, "decisions_source_bound_planning_manifest_verification_intake_non_claim_mismatch", "$.source_bound_planning_manifest_verification_intake.non_claim")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed", "public_abi_ready", "v1_completion_evidence"):
            if planning_source_intake.get(key) is not False:
                add(blockers, "readiness_flag_not_false", f"$.source_bound_planning_manifest_verification_intake.{key}", input="source_bound_planning_manifest_verification_intake", value=planning_source_intake.get(key))
    public_abi_preflight_intake = decisions.get("public_abi_preflight_candidate_intake")
    if not isinstance(public_abi_preflight_intake, dict):
        add(blockers, "decisions_public_abi_preflight_candidate_intake_missing", "$.public_abi_preflight_candidate_intake")
    else:
        if public_abi_preflight_intake.get("id") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_INTAKE_ID:
            add(blockers, "decisions_public_abi_preflight_candidate_intake_id_mismatch", "$.public_abi_preflight_candidate_intake.id")
        if public_abi_preflight_intake.get("status") != "repo_candidate_preflight_required":
            add(blockers, "decisions_public_abi_preflight_candidate_intake_status_mismatch", "$.public_abi_preflight_candidate_intake.status")
        if public_abi_preflight_intake.get("resolved_input") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT:
            add(
                blockers,
                "decisions_public_abi_preflight_candidate_intake_resolved_input_mismatch",
                "$.public_abi_preflight_candidate_intake.resolved_input",
            )
        if public_abi_preflight_intake.get("required_checker") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER:
            add(
                blockers,
                "decisions_public_abi_preflight_candidate_intake_checker_mismatch",
                "$.public_abi_preflight_candidate_intake.required_checker",
            )
        if public_abi_preflight_intake.get("default_manifest") != str(DEFAULT_PUBLIC_ABI_PREFLIGHT_CANDIDATE):
            add(
                blockers,
                "decisions_public_abi_preflight_candidate_intake_default_manifest_mismatch",
                "$.public_abi_preflight_candidate_intake.default_manifest",
            )
        if public_abi_preflight_intake.get("non_claim") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_NON_CLAIM:
            add(
                blockers,
                "decisions_public_abi_preflight_candidate_intake_non_claim_mismatch",
                "$.public_abi_preflight_candidate_intake.non_claim",
            )
        for key in (
            "promotion_ready",
            "public_sdk_ready",
            "runtime_ready",
            "public_header_allowed",
            "public_abi_ready",
            "v1_completion_evidence",
        ):
            if public_abi_preflight_intake.get(key) is not False:
                add(
                    blockers,
                    "readiness_flag_not_false",
                    f"$.public_abi_preflight_candidate_intake.{key}",
                    input="public_abi_preflight_candidate_intake",
                    value=public_abi_preflight_intake.get(key),
                )
    owner_token_intake = decisions.get("owner_token_sdk_consumer_contract_intake")
    if not isinstance(owner_token_intake, dict):
        add(blockers, "decisions_owner_token_sdk_consumer_contract_intake_missing", "$.owner_token_sdk_consumer_contract_intake")
    else:
        if owner_token_intake.get("id") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_INTAKE_ID:
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_id_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.id",
            )
        if owner_token_intake.get("status") != "repo_candidate_contract_required":
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_status_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.status",
            )
        if owner_token_intake.get("resolved_input") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT:
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_resolved_input_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.resolved_input",
            )
        if owner_token_intake.get("required_checker") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_CHECKER:
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_checker_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.required_checker",
            )
        if owner_token_intake.get("default_manifest") != str(DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT):
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_default_manifest_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.default_manifest",
            )
        if owner_token_intake.get("non_claim") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_NON_CLAIM:
            add(
                blockers,
                "decisions_owner_token_sdk_consumer_contract_intake_non_claim_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.non_claim",
            )
        for key in (
            "promotion_ready",
            "public_sdk_ready",
            "runtime_ready",
            "public_header_allowed",
            "public_abi_ready",
            "v1_completion_evidence",
            "lifecycle_owner_cleanup_ready",
        ):
            if owner_token_intake.get(key) is not False:
                add(
                    blockers,
                    "readiness_flag_not_false",
                    f"$.owner_token_sdk_consumer_contract_intake.{key}",
                    input="owner_token_sdk_consumer_contract_intake",
                    value=owner_token_intake.get(key),
                )
    not_sufficient = decisions.get("approved_runtime_evidence_not_sufficient")
    if not isinstance(not_sufficient, dict):
        add(blockers, "decisions_approved_runtime_evidence_not_sufficient_missing", "$.approved_runtime_evidence_not_sufficient")
    else:
        require_string_list_contains(
            not_sufficient,
            "why",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY,
            blockers,
            "decisions_approved_runtime_evidence_not_sufficient_why_missing",
            "$.approved_runtime_evidence_not_sufficient.why",
        )
        require_string_list_contains(
            not_sufficient,
            "minimum_additional_gates",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES,
            blockers,
            "decisions_approved_runtime_evidence_not_sufficient_minimum_gates_missing",
            "$.approved_runtime_evidence_not_sufficient.minimum_additional_gates",
        )
    promotion_blockers = decisions.get("promotion_blockers")
    if not isinstance(promotion_blockers, list):
        add(blockers, "decisions_promotion_blockers_not_list", "$.promotion_blockers")
    else:
        by_id = {
            item.get("id"): item
            for item in promotion_blockers
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        missing = sorted(REQUIRED_PROMOTION_BLOCKERS - set(by_id))
        if missing:
            add(blockers, "decisions_required_promotion_blockers_missing", "$.promotion_blockers", missing=missing)
        if set(by_id) != REQUIRED_PROMOTION_BLOCKERS:
            add(
                blockers,
                "decisions_promotion_blockers_mismatch",
                "$.promotion_blockers",
                expected=sorted(REQUIRED_PROMOTION_BLOCKERS),
                observed=sorted(by_id),
            )
        for blocker_id in sorted(REQUIRED_PROMOTION_BLOCKERS & set(by_id)):
            if by_id[blocker_id].get("status") != "unresolved":
                add(
                    blockers,
                    "decisions_required_promotion_blocker_not_unresolved",
                    "$.promotion_blockers",
                    id=blocker_id,
                    value=by_id[blocker_id].get("status"),
                )
    contract_gate_inputs = decisions.get("contract_gate_inputs")
    if not isinstance(contract_gate_inputs, list):
        add(blockers, "decisions_contract_gate_inputs_not_list", "$.contract_gate_inputs")
    else:
        by_id = {
            item.get("id"): item
            for item in contract_gate_inputs
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if set(by_id) != set(REQUIRED_CONTRACT_GATE_INPUTS):
            add(
                blockers,
                "decisions_contract_gate_inputs_mismatch",
                "$.contract_gate_inputs",
                expected=sorted(REQUIRED_CONTRACT_GATE_INPUTS),
                observed=sorted(by_id),
            )
        for input_id, required in REQUIRED_CONTRACT_GATE_INPUTS.items():
            item = by_id.get(input_id)
            if not isinstance(item, dict):
                continue
            if item.get("status") != "unresolved":
                add(
                    blockers,
                    "decisions_contract_gate_input_not_unresolved",
                    "$.contract_gate_inputs",
                    id=input_id,
                    value=item.get("status"),
                )
            if set(item.get("review_inputs", [])) != required["review_inputs"]:
                add(
                    blockers,
                    "decisions_contract_gate_input_review_inputs_mismatch",
                    "$.contract_gate_inputs.review_inputs",
                    id=input_id,
                    expected=sorted(required["review_inputs"]),
                    observed=item.get("review_inputs"),
                )
            if set(item.get("remaining_promotion_inputs", [])) != required["remaining_promotion_inputs"]:
                add(
                    blockers,
                    "decisions_contract_gate_input_remaining_promotion_inputs_mismatch",
                    "$.contract_gate_inputs.remaining_promotion_inputs",
                    id=input_id,
                    expected=sorted(required["remaining_promotion_inputs"]),
                    observed=item.get("remaining_promotion_inputs"),
                )
            for key in (
                "promotion_blocker_resolved",
                "promotion_ready",
                "public_sdk_ready",
                "runtime_ready",
                "public_header_allowed",
                "v1_completion_evidence",
            ):
                if item.get(key) is not False:
                    add(
                        blockers,
                        "decisions_contract_gate_input_flag_not_false",
                        f"$.contract_gate_inputs[{input_id}].{key}",
                        id=input_id,
                        value=item.get(key),
                    )
    required_before_public_header = decisions.get("required_before_public_header")
    if not isinstance(required_before_public_header, list):
        add(blockers, "decisions_required_before_public_header_not_list", "$.required_before_public_header")
    else:
        by_id = {
            item.get("id"): item
            for item in required_before_public_header
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        missing = sorted(REQUIRED_PRIVACY_PUBLIC_HEADER_BLOCKERS - set(by_id))
        if missing:
            add(
                blockers,
                "decisions_required_privacy_public_header_blockers_missing",
                "$.required_before_public_header",
                missing=missing,
            )
        if set(by_id) != REQUIRED_PRIVACY_PUBLIC_HEADER_BLOCKERS:
            add(
                blockers,
                "decisions_required_before_public_header_mismatch",
                "$.required_before_public_header",
                expected=sorted(REQUIRED_PRIVACY_PUBLIC_HEADER_BLOCKERS),
                observed=sorted(by_id),
            )
        for blocker_id in sorted(REQUIRED_PRIVACY_PUBLIC_HEADER_BLOCKERS & set(by_id)):
            if by_id[blocker_id].get("status") != "unresolved":
                add(
                    blockers,
                    "decisions_required_privacy_public_header_blocker_not_unresolved",
                    "$.required_before_public_header",
                    id=blocker_id,
                    value=by_id[blocker_id].get("status"),
                )
        validate_required_before_public_header_contract(by_id, blockers)
    validate_empty_public_lists(decisions, blockers, "decisions")
    validate_false_flags(decisions, blockers, "decisions")


def validate_surfaces(surfaces: dict[str, Any], blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if surfaces.get("schema") != SURFACES_SCHEMA:
        add(blockers, "surfaces_schema_mismatch", "$.schema", value=surfaces.get("schema"))
    surface = find_surface(surfaces, blockers)
    if not surface:
        return {}
    if surface.get("status") != "planning":
        add(blockers, "player_identity_surface_status_not_planning", "$.surfaces[obelisk.player_identity.v1].status", value=surface.get("status"))
    if surface.get("public_contract") != []:
        add(blockers, "player_identity_surface_public_contract_not_empty", "$.surfaces[obelisk.player_identity.v1].public_contract", value=surface.get("public_contract"))
    if SURFACE not in surfaces.get("planning_surfaces", []):
        add(blockers, "player_identity_missing_from_planning_surfaces", "$.planning_surfaces")
    for list_name in ("promoted_surfaces", "experimental_surfaces", "post_v1_or_excluded_surfaces", "debug_only_surfaces"):
        if SURFACE in surfaces.get(list_name, []):
            add(blockers, "player_identity_in_non_planning_surface_list", f"$.{list_name}")
    validate_false_flags(surface, blockers, "surfaces.player_identity")
    return surface


def has_negative_context(value: str, match_start: int) -> bool:
    normalized = value.replace("_", " ")
    clause_start = max(
        normalized.rfind(";", 0, match_start),
        normalized.rfind(".", 0, match_start),
    )
    clause_end_candidates = [
        index
        for index in (
            normalized.find(";", match_start),
            normalized.find(".", match_start),
        )
        if index != -1
    ]
    clause_end = min(clause_end_candidates) if clause_end_candidates else len(normalized)
    prefix = normalized[clause_start + 1 : match_start]
    suffix = normalized[match_start:clause_end]
    if re.search(r"(?:^|\b)non[-_ ]*$", prefix, re.IGNORECASE):
        return True
    if NEGATIVE_CONTEXT_RE.search(prefix):
        return True
    return bool(
        re.search(
            r"\b(?:forbidden|unavailable|blocked|redacted)\b|\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def candidate_exposures(candidate: dict[str, Any]) -> list[dict[str, str]]:
    exposures: list[dict[str, str]] = []
    scanned = list(walk_json(candidate)) + list(walk_json_keys(candidate))
    for path, item in scanned:
        if not isinstance(item, str):
            continue
        for term, pattern in FORBIDDEN_CANDIDATE_EXPOSURE_PATTERNS.items():
            for match in pattern.finditer(item):
                if has_negative_context(item, match.start()):
                    continue
                exposures.append({"path": path, "term": term, "value": item})
                break
    return exposures


def approved_runtime_report_overclaims(report: Any, path: str = "$") -> list[dict[str, Any]]:
    overclaims: list[dict[str, Any]] = []
    if isinstance(report, dict):
        for key, item in report.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            if normalized_key in EMPTY_PUBLIC_LIST_KEYS and item != []:
                overclaims.append({"path": item_path, "term": "public_surface_list", "value": item})
            if (
                normalized_key not in ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS
                and item not in (False, None, [], {})
                and APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(normalized_key)
            ):
                overclaims.append({"path": item_path, "term": "readiness_or_authorization_key", "value": item})
            overclaims.extend(approved_runtime_report_overclaims(item, item_path))
    elif isinstance(report, list):
        for index, item in enumerate(report):
            overclaims.extend(approved_runtime_report_overclaims(item, f"{path}[{index}]"))
    elif isinstance(report, str):
        for term, pattern in APPROVED_RUNTIME_REPORT_OVERCLAIM_VALUE_PATTERNS.items():
            for match in pattern.finditer(report):
                if has_negative_context(report, match.start()):
                    continue
                overclaims.append({"path": path, "term": term, "value": report})
                break
    return overclaims


def validate_private_candidate(candidate: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if candidate.get("schema") != PRIVATE_CANDIDATE_SCHEMA:
        add(blockers, "private_candidate_schema_mismatch", "$.schema", value=candidate.get("schema"))
    if candidate.get("surface") != SURFACE:
        add(blockers, "private_candidate_surface_mismatch", "$.surface", value=candidate.get("surface"))
    if candidate.get("artifact_status") != "candidate_only":
        add(blockers, "private_candidate_artifact_status_not_candidate_only", "$.artifact_status", value=candidate.get("artifact_status"))
    if candidate.get("visibility") != "private_planning_contract":
        add(blockers, "private_candidate_visibility_mismatch", "$.visibility", value=candidate.get("visibility"))
    if candidate.get("candidate_only") is not True:
        add(blockers, "private_candidate_candidate_only_not_true", "$.candidate_only", value=candidate.get("candidate_only"))
    validate_empty_public_lists(candidate, blockers, "private_candidate_contract")
    validate_false_flags(candidate, blockers, "private_candidate_contract")
    exposures = candidate_exposures(candidate)
    if exposures:
        add(
            blockers,
            "private_candidate_forbidden_public_identity_exposure",
            "--private-candidate-contract",
            exposures=exposures,
        )
    require_string_list_contains(
        candidate,
        "candidate_stale_handle_fail_closed_semantics",
        REQUIRED_PRIVATE_CANDIDATE_STALE_HANDLE_FAIL_CLOSED_SEMANTICS,
        blockers,
        "private_candidate_stale_handle_fail_closed_semantics_missing",
        "$.candidate_stale_handle_fail_closed_semantics",
    )


def validate_identifier_redaction_evidence(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = redaction_checker.load_evidence(path)
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        add(
            blockers,
            "identifier_redaction_evidence_unreadable_or_rejected",
            "--identifier-redaction-evidence",
            path=str(path),
            error=str(exc),
        )
        return {
            "path": str(path),
            "present": False,
            "accepted_for_contract_review": False,
            "resolved_inputs": [],
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "blockers": ["identifier_redaction_evidence_unreadable_or_rejected"],
        }

    redaction_blockers = redaction_checker.validate_evidence(payload)
    report = redaction_checker.build_report(payload, redaction_blockers)
    if redaction_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "--identifier-redaction-evidence",
            path=str(path),
            evidence_blockers=report["blockers"],
        )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if report.get(key) is not False:
            add(
                blockers,
                "identifier_redaction_evidence_readiness_flag_not_false",
                f"--identifier-redaction-evidence.{key}",
                value=report.get(key),
            )
    if report.get("accepted_for_contract_review") and report.get("resolved_inputs") != [PRIMARY_OFFLINE_GAP]:
        add(
            blockers,
            "identifier_redaction_evidence_resolved_inputs_mismatch",
            "--identifier-redaction-evidence.resolved_inputs",
            value=report.get("resolved_inputs"),
        )
    return {
        "path": str(path),
        "present": True,
        "accepted_for_contract_review": report.get("accepted_for_contract_review") is True,
        "resolved_inputs": report.get("resolved_inputs", []),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "blockers": report.get("blockers", []),
        "non_claims": report.get("non_claims", []),
    }


def validate_principal_invalidation_policy(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = principal_invalidation_policy.load_json(path)
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        add(
            blockers,
            "principal_invalidation_policy_unreadable_or_rejected",
            "--principal-invalidation-policy",
            path=str(path),
            error=str(exc),
        )
        return {
            "path": str(path),
            "provided": False,
            "accepted_for_policy_review": False,
            "resolved_input": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "principal_invalidation_ready": False,
            "blockers": ["principal_invalidation_policy_unreadable_or_rejected"],
        }

    validation = principal_invalidation_policy.validate_manifest(payload, check_mode="consume")
    report = principal_invalidation_policy.build_report(payload, validation, check_mode="consume")
    if validation.blockers:
        add(
            blockers,
            "principal_invalidation_policy_not_accepted",
            "--principal-invalidation-policy",
            path=str(path),
            policy_blockers=report["blockers"],
        )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "principal_invalidation_ready"):
        if report.get(key) is not False:
            add(
                blockers,
                "principal_invalidation_policy_readiness_flag_not_false",
                f"--principal-invalidation-policy.{key}",
                value=report.get(key),
            )
    return {
        "path": str(path),
        "provided": True,
        "accepted_for_policy_review": report.get("ready") is True,
        "resolved_input": PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT if report.get("ready") is True else None,
        "mode": report.get("mode"),
        "candidate_only": report.get("candidate_only") is True,
        "principal_fields": report.get("principal_fields", []),
        "invalidation_cases": report.get("invalidation_cases", []),
        "negative_consumer_rules": report.get("negative_consumer_rules", []),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "principal_invalidation_ready": False,
        "blockers": report.get("blockers", []),
    }


def validate_planning_source_verification(
    snapshot_root: Path,
    existing_dir: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        verified_snapshot_root = planning_source_manifests.safe_snapshot_root(snapshot_root)
        verified_existing_dir = planning_source_manifests.safe_existing_dir(existing_dir)
        report = planning_source_manifests.verify_existing_dir(
            snapshot_root=verified_snapshot_root,
            existing_dir=verified_existing_dir,
        )
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        add(
            blockers,
            "source_bound_planning_manifest_verification_unreadable_or_rejected",
            "--planning-sources-dir",
            snapshot_root=str(snapshot_root),
            existing_dir=str(existing_dir),
            error=str(exc),
        )
        return {
            "provided": False,
            "accepted_for_contract_review": False,
            "resolved_input": None,
            "planning_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_abi_ready": False,
            "v1_completion_ready": False,
            "server_operations_authorized": False,
            "runtime_work_authorized": False,
            "blockers": ["source_bound_planning_manifest_verification_unreadable_or_rejected"],
        }
    if report.get("schema") != planning_source_manifests.REPORT_SCHEMA:
        add(
            blockers,
            "source_bound_planning_manifest_verification_schema_mismatch",
            "--planning-sources-dir.schema",
            value=report.get("schema"),
        )
    if report.get("mode") != "verify_existing":
        add(
            blockers,
            "source_bound_planning_manifest_verification_mode_mismatch",
            "--planning-sources-dir.mode",
            value=report.get("mode"),
        )
    lifecycle_provenance_blocked = (
        report.get("current_route_blocker") == "lifecycle_anchor_first_evidence_provenance_unbound"
    )
    if (
        report.get("valid") is not True
        or report.get("accepted_for_planning") is not True
    ) and not lifecycle_provenance_blocked:
        add(
            blockers,
            "source_bound_planning_manifest_verification_not_accepted",
            "--planning-sources-dir",
            verification_blockers=report.get("blockers", []),
        )
    if report.get("planning_only") is not True:
        add(
            blockers,
            "source_bound_planning_manifest_verification_not_planning_only",
            "--planning-sources-dir.planning_only",
            value=report.get("planning_only"),
        )
    for key in (
        "promotion_ready",
        "public_sdk_ready",
        "public_abi_ready",
        "runtime_ready",
        "v1_completion_ready",
        "server_operations_authorized",
        "runtime_work_authorized",
    ):
        if report.get(key) is not False:
            add(
                blockers,
                "source_bound_planning_manifest_verification_readiness_flag_not_false",
                f"--planning-sources-dir.{key}",
                value=report.get(key),
            )
    accepted = (
        (
            (report.get("valid") is True and report.get("accepted_for_planning") is True)
            or lifecycle_provenance_blocked
        )
        and report.get("planning_only") is True
        and all(
            report.get(key) is False
            for key in (
                "promotion_ready",
                "public_sdk_ready",
                "public_abi_ready",
                "runtime_ready",
                "v1_completion_ready",
                "server_operations_authorized",
                "runtime_work_authorized",
            )
        )
    )
    return {
        "provided": True,
        "accepted_for_contract_review": accepted,
        "resolved_input": REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT if accepted else None,
        "planning_only": report.get("planning_only") is True,
        "snapshot_root": report.get("snapshot_root"),
        "verify_existing_dir": report.get("verify_existing_dir"),
        "checked_outputs": report.get("checked_outputs", {}),
        "current_route_blocker": report.get("current_route_blocker"),
        "lifecycle_provenance_diagnostic": report.get("lifecycle_provenance_diagnostic", {}),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_abi_ready": False,
        "v1_completion_ready": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "blockers": report.get("blockers", []),
        "non_claims": PLANNING_SOURCE_VERIFICATION_REPORT_NON_CLAIMS,
    }


def validate_approved_runtime_evidence(path: Path | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "accepted_for_contract_review": False,
            "resolved_input": None,
            "next_blocker": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "blockers": ["approved_runtime_evidence_not_provided"],
        }
    try:
        payload = approved_runtime_evidence.load_json(path)
    except (OSError, json.JSONDecodeError, SystemExit) as exc:
        add(
            blockers,
            "approved_runtime_evidence_unreadable_or_rejected",
            "--approved-runtime-evidence",
            path=str(path),
            error=str(exc),
        )
        return {
            "path": str(path),
            "provided": True,
            "accepted_for_contract_review": False,
            "resolved_input": None,
            "next_blocker": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "blockers": ["approved_runtime_evidence_unreadable_or_rejected"],
        }

    validation = approved_runtime_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_runtime_evidence.build_report(payload, validation, check_mode="consume")
    accepted = not validation.blockers
    overclaims = approved_runtime_report_overclaims(report)
    if overclaims:
        add(
            blockers,
            "approved_runtime_evidence_report_public_readiness_overclaim",
            "--approved-runtime-evidence",
            overclaims=overclaims,
        )
        accepted = False
    if not accepted:
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "--approved-runtime-evidence",
            path=str(path),
            evidence_blockers=report.get("blockers", []),
        )
    if report.get("schema") != approved_runtime_evidence.REPORT_SCHEMA:
        add(
            blockers,
            "approved_runtime_evidence_report_schema_mismatch",
            "--approved-runtime-evidence.schema",
            value=report.get("schema"),
        )
        accepted = False
    if report.get("mode") != "consume":
        add(
            blockers,
            "approved_runtime_evidence_mode_mismatch",
            "--approved-runtime-evidence.mode",
            value=report.get("mode"),
        )
        accepted = False
    if report.get("ready_scope") != REQUIRED_APPROVED_RUNTIME_READY_SCOPE:
        add(
            blockers,
            "approved_runtime_evidence_ready_scope_mismatch",
            "--approved-runtime-evidence.ready_scope",
            value=report.get("ready_scope"),
        )
        accepted = False
    if report.get("remaining_blockers") != []:
        add(
            blockers,
            "approved_runtime_evidence_remaining_blockers_not_empty",
            "--approved-runtime-evidence.remaining_blockers",
            value=report.get("remaining_blockers"),
        )
        accepted = False
    if report.get("next_blocker") != APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER:
        add(
            blockers,
            "approved_runtime_evidence_next_blocker_mismatch",
            "--approved-runtime-evidence.next_blocker",
            value=report.get("next_blocker"),
        )
        accepted = False
    if report.get("approved_runtime_evidence_present") is not True:
        add(
            blockers,
            "approved_runtime_evidence_presence_missing",
            "--approved-runtime-evidence.approved_runtime_evidence_present",
            value=report.get("approved_runtime_evidence_present"),
        )
        accepted = False
    if report.get("runtime_evidence_ready") is not True:
        add(
            blockers,
            "approved_runtime_evidence_ready_missing",
            "--approved-runtime-evidence.runtime_evidence_ready",
            value=report.get("runtime_evidence_ready"),
        )
        accepted = False
    resolved_inputs = report.get("resolved_inputs")
    if resolved_inputs is not None:
        if not isinstance(resolved_inputs, list) or not all(isinstance(item, str) for item in resolved_inputs):
            add(
                blockers,
                "approved_runtime_evidence_resolved_inputs_not_string_list",
                "--approved-runtime-evidence.resolved_inputs",
                value=resolved_inputs,
            )
            accepted = False
        else:
            forbidden_inputs = sorted(
                item
                for item in resolved_inputs
                if any(token in item.lower() for token in FORBIDDEN_APPROVED_RUNTIME_RESOLVED_INPUT_TOKENS)
            )
            if forbidden_inputs:
                add(
                    blockers,
                    "approved_runtime_evidence_non_promotional_inputs_claimed",
                    "--approved-runtime-evidence.resolved_inputs",
                    forbidden=forbidden_inputs,
                )
                accepted = False
            unexpected_inputs = sorted(set(resolved_inputs) - {APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT})
            if unexpected_inputs:
                add(
                    blockers,
                    "approved_runtime_evidence_resolved_inputs_unexpected",
                    "--approved-runtime-evidence.resolved_inputs",
                    unexpected=unexpected_inputs,
                )
                accepted = False
    observed_runtime_cases = report.get("observed_runtime_cases")
    if observed_runtime_cases != REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES:
        add(
            blockers,
            "approved_runtime_evidence_observed_runtime_cases_mismatch",
            "--approved-runtime-evidence.observed_runtime_cases",
            expected=REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
            value=observed_runtime_cases,
        )
        accepted = False
    consumer_cases = report.get("consumer_cases")
    if consumer_cases != REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES:
        add(
            blockers,
            "approved_runtime_evidence_consumer_cases_mismatch",
            "--approved-runtime-evidence.consumer_cases",
            expected=REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
            value=consumer_cases,
        )
        accepted = False
    consumer_boundary_assertions = report.get("consumer_boundary_assertions")
    if consumer_boundary_assertions != REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES:
        add(
            blockers,
            "approved_runtime_evidence_consumer_boundary_assertions_mismatch",
            "--approved-runtime-evidence.consumer_boundary_assertions",
            expected=REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
            value=consumer_boundary_assertions,
        )
        accepted = False
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if report.get(key) is not False:
            add(
                blockers,
                "approved_runtime_evidence_readiness_flag_not_false",
                f"--approved-runtime-evidence.{key}",
                value=report.get(key),
            )
            accepted = False
    for key in ("public_abi_ready", "v1_completion_ready", "v1_completion_evidence"):
        if key in report and report.get(key) is not False:
            add(
                blockers,
                "approved_runtime_evidence_readiness_flag_not_false",
                f"--approved-runtime-evidence.{key}",
                value=report.get(key),
            )
            accepted = False
    return {
        "path": str(path),
        "provided": True,
        "accepted_for_contract_review": accepted,
        "resolved_input": APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT if accepted else None,
        "resolved_inputs": [APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT] if accepted else [],
        "next_blocker": report.get("next_blocker"),
        "approved_runtime_evidence_present": report.get("approved_runtime_evidence_present") is True,
        "runtime_evidence_ready": report.get("runtime_evidence_ready") is True,
        "ready_scope": report.get("ready_scope"),
        "observed_runtime_cases": report.get("observed_runtime_cases", []),
        "consumer_cases": report.get("consumer_cases", []),
        "consumer_boundary_assertions": report.get("consumer_boundary_assertions", []),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "blockers": report.get("blockers", []),
        "non_claim": (
            "approved runtime evidence is a contract-review input only; it does not "
            "promote player identity, open public ABI, unlock downstream surfaces, or "
            "count toward v1 completion"
        ),
    }


def validate_private_pod_layout_candidate(
    path: Path,
    private_contract_path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        payload = private_pod_layout_candidate.load_json(path)
        private_contract = private_pod_layout_candidate.load_json(private_contract_path)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        add(
            blockers,
            "private_pod_layout_candidate_unreadable_or_rejected",
            "--private-pod-layout-candidate",
            path=str(path),
            error=str(exc),
        )
        return {
            "path": str(path),
            "provided": False,
            "accepted_for_contract_review_input": False,
            "review_input": private_pod_layout_candidate.RESOLVED_INPUT,
            "candidate_only": True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "does_not_resolve": ["abi.public_pod_contract", "abi.layout", "sdk.consumer"],
            "blockers": ["private_pod_layout_candidate_unreadable_or_rejected"],
        }
    candidate_blockers = private_pod_layout_candidate.validate_manifest(payload, private_contract)
    report = private_pod_layout_candidate.build_report(payload, candidate_blockers)
    if candidate_blockers:
        add(
            blockers,
            "private_pod_layout_candidate_not_accepted",
            "--private-pod-layout-candidate",
            path=str(path),
            layout_blockers=report["blockers"],
        )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if report.get(key) is not False:
            add(
                blockers,
                "private_pod_layout_candidate_readiness_flag_not_false",
                f"--private-pod-layout-candidate.{key}",
                value=report.get(key),
            )
    return {
        "path": str(path),
        "provided": True,
        "accepted_for_contract_review_input": report.get("accepted_for_contract_review") is True,
        "review_input": private_pod_layout_candidate.RESOLVED_INPUT,
        "candidate_only": True,
        "layout_candidate_ready": False,
        "event_payload": report.get("event_payload", {}),
        "descriptor": report.get("descriptor", {}),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "does_not_resolve": ["abi.public_pod_contract", "abi.layout", "sdk.consumer"],
        "blockers": report.get("blockers", []),
        "non_claims": report.get("non_claims", []),
    }


def validate_public_abi_preflight_candidate(
    path: Path,
    private_pod_layout_path: Path,
    private_contract_path: Path,
    public_header_path: Path,
    blockers: list[dict[str, Any]],
    identifier_redaction_evidence: dict[str, Any],
    principal_invalidation_policy_report: dict[str, Any],
) -> dict[str, Any]:
    try:
        payload = public_abi_preflight_candidate.load_json(path)
        private_payload = private_pod_layout_candidate.load_json(private_pod_layout_path)
        private_contract = private_pod_layout_candidate.load_json(private_contract_path)
        private_blockers = private_pod_layout_candidate.validate_manifest(private_payload, private_contract)
        private_report = private_pod_layout_candidate.build_report(private_payload, private_blockers)
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        add(
            blockers,
            "public_abi_preflight_candidate_unreadable_or_rejected",
            "--public-abi-preflight-candidate",
            path=str(path),
            error=str(exc),
        )
        return {
            "status": "blocked",
            "candidate_only": True,
            "accepted_for_candidate_review": False,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "blockers": ["public_abi_preflight_candidate_unreadable_or_rejected"],
        }
    candidate_blockers: list[dict[str, Any]] = []
    if private_blockers:
        public_abi_preflight_candidate.add(
            candidate_blockers,
            "private_pod_layout_candidate_not_accepted",
            "--private-pod-layout-candidate",
            layout_blockers=private_report["blockers"],
        )
    header_scan = public_abi_preflight_candidate.scan_public_header(public_header_path, candidate_blockers)
    public_abi_preflight_candidate.validate_manifest(payload, private_payload, candidate_blockers)
    redaction_report = {
        "accepted_for_contract_review": identifier_redaction_evidence.get("accepted_for_contract_review") is True,
        "blockers": identifier_redaction_evidence.get("blockers", []),
    }
    principal_report = {
        "ready": principal_invalidation_policy_report.get("accepted_for_policy_review") is True,
        "candidate_only": principal_invalidation_policy_report.get("candidate_only") is True,
        "blockers": principal_invalidation_policy_report.get("blockers", []),
    }
    public_abi_preflight_candidate.validate_claimed_contract_review_inputs(
        payload,
        candidate_blockers,
        redaction_report=redaction_report,
        principal_report=principal_report,
        private_layout_report=private_report,
    )
    report = public_abi_preflight_candidate.build_report(
        payload,
        candidate_blockers,
        header_scan=header_scan,
        private_layout_report=private_report,
        redaction_report=redaction_report,
        principal_report=principal_report,
    )
    if candidate_blockers:
        add(
            blockers,
            "public_abi_preflight_candidate_not_accepted",
            "--public-abi-preflight-candidate",
            path=str(path),
            preflight_blockers=report["blockers"],
        )
    return sanitize_non_promotional_report(
        report,
        blockers,
        input_label="public_abi_preflight_candidate",
        path="$.public_abi_promotion_preflight",
    )


def validate_owner_token_sdk_consumer_contract(
    path: Path,
    public_abi_preflight_path: Path,
    public_header_path: Path,
    blockers: list[dict[str, Any]],
    public_abi_preflight_report: dict[str, Any],
) -> dict[str, Any]:
    checker_path = SCRIPT_DIR / "check_player_identity_owner_token_sdk_consumer_contract.py"
    if not checker_path.exists() or not path.exists():
        missing = []
        if not checker_path.exists():
            missing.append(str(checker_path))
        if not path.exists():
            missing.append(str(path))
        add(
            blockers,
            "owner_token_sdk_consumer_contract_missing",
            "--owner-token-sdk-consumer-contract",
            missing=missing,
        )
        return {
            "provided": False,
            "source": "missing_owner_token_sdk_consumer_contract",
            "ready": False,
            "accepted_for_candidate_review": False,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "sdk_consumer": public_abi_preflight_report.get("sdk_consumer_contract", {}),
            "lifecycle_owner_cleanup": {
                "required_checks": public_abi_preflight_report.get("required_owner_token_lifecycle", []),
            },
            "does_not_resolve": ["sdk.consumer", "lifecycle.owner_cleanup", "v1_completion"],
            "blockers": ["owner_token_sdk_consumer_contract_missing"],
        }

    try:
        import check_player_identity_owner_token_sdk_consumer_contract as owner_token_sdk_consumer

        payload = owner_token_sdk_consumer.load_json(path)
        contract_blockers: list[dict[str, Any]] = []
        preflight_payload, preflight_report = owner_token_sdk_consumer.validate_preflight(
            public_abi_preflight_path,
            public_header_path,
            contract_blockers,
        )
        owner_token_sdk_consumer.validate_manifest(payload, preflight_payload, contract_blockers)
        report = owner_token_sdk_consumer.build_report(
            payload,
            contract_blockers,
            preflight_report=preflight_report,
        )
    except (ImportError, OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        add(
            blockers,
            "owner_token_sdk_consumer_contract_unreadable_or_rejected",
            "--owner-token-sdk-consumer-contract",
            path=str(path),
            error=str(exc),
        )
        return {
            "provided": True,
            "ready": False,
            "accepted_for_candidate_review": False,
            "accepted_for_contract_review": False,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "v1_completion_evidence": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "blockers": ["owner_token_sdk_consumer_contract_unreadable_or_rejected"],
        }
    if contract_blockers:
        add(
            blockers,
            "owner_token_sdk_consumer_contract_not_accepted",
            "--owner-token-sdk-consumer-contract",
            path=str(path),
            contract_blockers=report["blockers"],
        )
    return sanitize_non_promotional_report(
        {"provided": True, "source": "owner_token_sdk_consumer_contract", **report},
        blockers,
        input_label="owner_token_sdk_consumer_contract",
        path="$.owner_token_sdk_consumer_contract",
    )


def contract_gate_input_details(
    decisions: dict[str, Any],
    *,
    runtime_evidence_accepted: bool,
    redaction_accepted: bool,
    planning_source_verified: bool,
    principal_policy_accepted: bool,
    private_layout_accepted: bool,
    public_abi_preflight_report: dict[str, Any],
    owner_token_sdk_consumer_report: dict[str, Any],
) -> list[dict[str, Any]]:
    accepted_review_inputs: set[str] = set()
    if runtime_evidence_accepted:
        accepted_review_inputs.add(APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT)
    if redaction_accepted:
        accepted_review_inputs.add(PRIMARY_OFFLINE_GAP)
    if planning_source_verified:
        accepted_review_inputs.add(REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT)
    if principal_policy_accepted:
        accepted_review_inputs.add(PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT)
    if private_layout_accepted:
        accepted_review_inputs.add("abi.public_pod_contract.private_layout_candidate")
    if public_abi_preflight_report.get("accepted_for_candidate_review") is True:
        accepted_review_inputs.add(REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT)
    if owner_token_sdk_consumer_report.get("accepted_for_candidate_review") is True:
        accepted_review_inputs.add(REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT)
    accepted_review_inputs.add("separation.no_commands_permissions_persistence")

    manifest_inputs = decisions.get("contract_gate_inputs")
    if not isinstance(manifest_inputs, list):
        manifest_inputs = []
    by_id = {
        item.get("id"): item
        for item in manifest_inputs
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    details: list[dict[str, Any]] = []
    for input_id in sorted(REQUIRED_CONTRACT_GATE_INPUTS):
        manifest = by_id.get(input_id, {})
        review_inputs = list(manifest.get("review_inputs", []))
        if not isinstance(review_inputs, list) or not all(isinstance(item, str) for item in review_inputs):
            review_inputs = sorted(REQUIRED_CONTRACT_GATE_INPUTS[input_id]["review_inputs"])
        remaining_promotion_inputs = list(manifest.get("remaining_promotion_inputs", []))
        if not isinstance(remaining_promotion_inputs, list) or not all(
            isinstance(item, str) for item in remaining_promotion_inputs
        ):
            remaining_promotion_inputs = sorted(
                REQUIRED_CONTRACT_GATE_INPUTS[input_id]["remaining_promotion_inputs"]
            )
        resolved_review_inputs = [item for item in review_inputs if item in accepted_review_inputs]
        details.append(
            {
                "id": input_id,
                "status": "unresolved",
                "review_inputs": review_inputs,
                "review_inputs_resolved": resolved_review_inputs,
                "review_inputs_missing": [item for item in review_inputs if item not in accepted_review_inputs],
                "remaining_promotion_inputs": remaining_promotion_inputs,
                "promotion_blocker_resolved": False,
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "v1_completion_evidence": False,
                "non_claim": manifest.get("non_claim"),
            }
        )
    return details


def build_report(
    args: argparse.Namespace,
    blockers: list[dict[str, Any]],
    decisions: dict[str, Any],
    surface: dict[str, Any],
    header_scan: dict[str, Any],
    candidate: dict[str, Any],
    approved_runtime_evidence_report: dict[str, Any],
    identifier_redaction_evidence: dict[str, Any],
    planning_source_verification: dict[str, Any],
    principal_invalidation_policy_report: dict[str, Any],
    private_pod_layout_report: dict[str, Any],
    public_abi_preflight_report: dict[str, Any],
    owner_token_sdk_consumer_report: dict[str, Any],
) -> dict[str, Any]:
    redaction_accepted = identifier_redaction_evidence.get("accepted_for_contract_review") is True
    planning_source_verified = planning_source_verification.get("accepted_for_contract_review") is True
    principal_policy_accepted = principal_invalidation_policy_report.get("accepted_for_policy_review") is True
    primary_offline_gap = (
        PRIMARY_OFFLINE_GAP_AFTER_IDENTIFIER_REDACTION
        if redaction_accepted
        else PRIMARY_OFFLINE_GAP
    )
    resolved_inputs = []
    runtime_evidence_accepted = approved_runtime_evidence_report.get("accepted_for_contract_review") is True
    if runtime_evidence_accepted:
        resolved_inputs.append(APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT)
    if redaction_accepted:
        resolved_inputs.append(PRIMARY_OFFLINE_GAP)
    if planning_source_verified:
        resolved_inputs.append(REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT)
    if principal_policy_accepted:
        resolved_inputs.append(PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT)
    remaining_contract_gate_inputs = [
        "lifetime.principal_scope",
        "lifetime.invalidation_events",
        "lifetime.reconnect_duplicate_stale_policy",
        "abi.public_pod_contract",
    ]
    if not runtime_evidence_accepted:
        remaining_contract_gate_inputs.insert(0, APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT)
    if not redaction_accepted:
        remaining_contract_gate_inputs.insert(1, PRIMARY_OFFLINE_GAP)
    private_layout_accepted = private_pod_layout_report.get("accepted_for_contract_review_input") is True
    contract_gate_details = contract_gate_input_details(
        decisions,
        runtime_evidence_accepted=runtime_evidence_accepted,
        redaction_accepted=redaction_accepted,
        planning_source_verified=planning_source_verified,
        principal_policy_accepted=principal_policy_accepted,
        private_layout_accepted=private_layout_accepted,
        public_abi_preflight_report=public_abi_preflight_report,
        owner_token_sdk_consumer_report=owner_token_sdk_consumer_report,
    )
    next_offline_actions = [
        {
            "id": "lifetime.generation_scope_invalidation",
            "status": "blocked",
            "candidate_policy_accepted": principal_policy_accepted,
            "next_input": "reviewed lifetime principal scope/invalidation/stale-handle decision",
            "non_claim": (
                "candidate policy acceptance does not resolve the full "
                "lifetime/generation/scope blocker or prove runtime lifecycle ordering"
            ),
        },
        {
            "id": "runtime.lifecycle_evidence",
            "status": "runtime_window_required",
            "next_input": "approved copied runtime principal lifecycle evidence",
            "non_claim": "offline planning inputs do not authorize runtime work or public SDK readiness",
        },
        {
            "id": "abi.public_pod_contract",
            "status": "blocked",
            "private_layout_candidate_accepted": private_layout_accepted,
            "next_input": "contract review of private POD payload, descriptor, capability, owner-token, SDK-consumer, and append-only layout-test plan",
            "does_not_resolve": ["abi.public_pod_contract", "abi.layout", "sdk.consumer", "lifecycle.owner_cleanup"],
            "non_claim": (
                "private layout candidate acceptance does not add public header symbols, "
                "capability bits, callbacks, ABI layout guarantees, SDK consumer readiness, "
                "route credit, v1 completion evidence, or promotion readiness"
            ),
        },
    ]
    return {
        "schema": SCHEMA,
        "surface": SURFACE,
        "status": "blocked",
        "valid": not blockers,
        "guardrail_passed": not blockers,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "primary_offline_gap": primary_offline_gap,
        "contract_review_inputs_resolved": resolved_inputs,
        "remaining_contract_gate_inputs": remaining_contract_gate_inputs,
        "contract_gate_inputs": contract_gate_details,
        "public_abi_promotion_preflight": public_abi_preflight_report,
        "candidate_owner_token_lifecycle": public_abi_preflight_report.get("required_owner_token_lifecycle", []),
        "sdk_consumer_contract": public_abi_preflight_report.get("sdk_consumer_contract", {}),
        "owner_token_sdk_consumer_contract": owner_token_sdk_consumer_report,
        "next_offline_actions": next_offline_actions,
        "runtime_evidence_missing": not runtime_evidence_accepted,
        "current_blocker": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER if runtime_evidence_accepted else "approved_runtime_evidence_missing",
        "next_blocker": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER if runtime_evidence_accepted else "approved_runtime_evidence_missing",
        "blocked_until": (
            ["reviewed_identity_public_contract"]
            if runtime_evidence_accepted
            else ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"]
        ),
        "inputs": {
            "decisions": str(args.decisions),
            "surfaces": str(args.surfaces),
            "private_candidate_contract": str(args.private_candidate_contract),
            "public_header": str(args.public_header),
            "identifier_redaction_evidence": str(args.identifier_redaction_evidence),
            "principal_invalidation_policy": str(args.principal_invalidation_policy),
            "planning_sources_dir": str(args.planning_sources_dir),
            "planning_source_snapshot_root": str(args.planning_source_snapshot_root),
            "private_pod_layout_candidate": str(args.private_pod_layout_candidate),
            "public_abi_preflight_candidate": str(args.public_abi_preflight_candidate),
            "owner_token_sdk_consumer_contract": str(args.owner_token_sdk_consumer_contract),
            "approved_runtime_evidence": str(args.approved_runtime_evidence) if args.approved_runtime_evidence else None,
        },
        "decisions": {
            "schema": decisions.get("schema"),
            "surface": decisions.get("surface"),
            "status": decisions.get("status"),
            "public_header_allowed": decisions.get("public_header_allowed"),
            "public_header_symbols_now": decisions.get("public_header_symbols_now"),
            "public_capability_bits_now": decisions.get("public_capability_bits_now"),
            "public_callback_abi_now": decisions.get("public_callback_abi_now"),
        },
        "surface_manifest": {
            "status": surface.get("status"),
            "public_contract": surface.get("public_contract"),
        },
        "public_header_scan": header_scan,
        "private_candidate_contract": {
            "schema": candidate.get("schema"),
            "artifact_status": candidate.get("artifact_status"),
            "visibility": candidate.get("visibility"),
            "candidate_only": candidate.get("candidate_only"),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
        },
        "identifier_redaction_evidence": identifier_redaction_evidence,
        "approved_runtime_evidence": approved_runtime_evidence_report,
        "source_bound_planning_manifest_verification": planning_source_verification,
        "principal_invalidation_policy": principal_invalidation_policy_report,
        "private_pod_layout_candidate": private_pod_layout_report,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": [
            "offline gap report does not require approved runtime evidence",
            "approved runtime evidence is contract-review input only and does not make player identity promotion-ready",
            "identifier-redaction evidence is contract-review input only and does not resolve the full privacy blocker",
            "principal invalidation policy is candidate-only review input and does not resolve the full lifetime/generation/scope blocker",
            "source-bound planning manifest verification is provenance for contract-review inputs only and does not promote public SDK/header/runtime readiness",
            "private POD layout candidate is contract-review input only and does not resolve the public ABI layout or SDK consumer gates",
            "blocked player identity state does not add public header symbols, capability bits, callbacks, lookup, persistence, mutation, return override, or v1 SDK readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    blockers: list[dict[str, Any]] = []
    decisions = load_json(args.decisions, "decisions", blockers)
    surfaces = load_json(args.surfaces, "surfaces", blockers)
    candidate = load_json(args.private_candidate_contract, "private_candidate_contract", blockers)

    if decisions:
        validate_decisions(decisions, blockers)
    surface = validate_surfaces(surfaces, blockers) if surfaces else {}
    if candidate:
        validate_private_candidate(candidate, blockers)
    approved_runtime_evidence_report = validate_approved_runtime_evidence(args.approved_runtime_evidence, blockers)
    identifier_redaction_evidence = validate_identifier_redaction_evidence(args.identifier_redaction_evidence, blockers)
    planning_source_verification = validate_planning_source_verification(
        args.planning_source_snapshot_root,
        args.planning_sources_dir,
        blockers,
    )
    principal_invalidation_policy_report = validate_principal_invalidation_policy(args.principal_invalidation_policy, blockers)
    private_pod_layout_report = validate_private_pod_layout_candidate(
        args.private_pod_layout_candidate,
        args.private_candidate_contract,
        blockers,
    )
    public_abi_preflight_report = validate_public_abi_preflight_candidate(
        args.public_abi_preflight_candidate,
        args.private_pod_layout_candidate,
        args.private_candidate_contract,
        args.public_header,
        blockers,
        identifier_redaction_evidence,
        principal_invalidation_policy_report,
    )
    owner_token_sdk_consumer_report = validate_owner_token_sdk_consumer_contract(
        args.owner_token_sdk_consumer_contract,
        args.public_abi_preflight_candidate,
        args.public_header,
        blockers,
        public_abi_preflight_report,
    )
    header_scan = scan_public_header(args.public_header, blockers)

    report = build_report(
        args,
        blockers,
        decisions,
        surface,
        header_scan,
        candidate,
        approved_runtime_evidence_report,
        identifier_redaction_evidence,
        planning_source_verification,
        principal_invalidation_policy_report,
        private_pod_layout_report,
        public_abi_preflight_report,
        owner_token_sdk_consumer_report,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    else:
        print("player identity public contract gap report valid: blocked offline gap preserved")
    return 0 if report["guardrail_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
