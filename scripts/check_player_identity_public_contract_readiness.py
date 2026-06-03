#!/usr/bin/env python3
"""Validate player identity public-contract review readiness.

This checker joins the approved runtime principal lifecycle evidence with the public
contract decision manifest. Acceptance means the runtime lifecycle blocker is ready for
contract review only; it does not promote public identity or open the SDK ABI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_evidence
import check_player_identity_identifier_redaction_evidence as identifier_redaction
import check_player_identity_principal_invalidation_policy as principal_invalidation_policy
import check_player_identity_public_abi_preflight_candidate as public_abi_preflight_candidate
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DECISION_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
PRIVATE_CANDIDATE_SCHEMA = "obelisk.player-identity-private-candidate-contract.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-contract-readiness-check.v1"
SURFACE = "obelisk.player_identity.v1"
DEFAULT_PRIVATE_CANDIDATE_CONTRACT = Path("docs/research/2026-06-01-player-identity-private-candidate-contract.json")
DEFAULT_PUBLIC_HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"
DEFAULT_PUBLIC_HEADER_DECL = "include/obelisk/ObeliskApi.h"
REQUIRED_INTAKE_ID = "approved_runtime_principal_lifecycle_evidence"
REQUIRED_RESOLVED_INPUT = "runtime.lifecycle_evidence"
REQUIRED_IDENTIFIER_REDACTION_INTAKE_ID = "identifier_redaction_evidence"
REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT = "privacy.identifier_redaction"
REQUIRED_IDENTIFIER_REDACTION_CHECKER = "scripts/check_player_identity_identifier_redaction_evidence.py"
PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT = "lifetime.generation_scope_invalidation.candidate_policy"
REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER = "scripts/check_player_identity_principal_invalidation_policy.py"
DEFAULT_PRINCIPAL_INVALIDATION_POLICY = Path(
    "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json"
)
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_INTAKE_ID = "public_abi_preflight_candidate"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT = "abi.public_pod_contract.public_abi_preflight_candidate"
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER = "scripts/check_player_identity_public_abi_preflight_candidate.py"
DEFAULT_PUBLIC_ABI_PREFLIGHT_CANDIDATE = Path(
    "docs/research/player-identity-planning-sources/player-identity-public-abi-preflight-candidate.json"
)
DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT = Path(
    "docs/research/player-identity-planning-sources/player-identity-owner-token-sdk-consumer-contract.json"
)
REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_NON_CLAIM = (
    "A valid public ABI preflight candidate is offline routing evidence only; it does not resolve the public "
    "POD ABI, add header symbols, add capability bits, expose callbacks, satisfy SDK consumer tests, promote "
    "player identity, or count toward v1 completion."
)
DECISION_GATE_ID = "identity_public_contract_gate"
NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
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
REQUIRED_FORBIDDEN = {
    "UE pointers",
    "raw params",
    "FName/GObjects indices",
    "ResourceHandle",
    "pointer-derived identity",
    "lookup",
    "mutation",
    "return override",
}
REQUIRED_BLOCKERS = {
    "runtime.lifecycle_evidence",
    "privacy.identifier_redaction",
    "lifetime.generation_scope_invalidation",
    "abi.public_pod_contract",
    "lifecycle.owner_cleanup",
    "separation.downstream_surfaces",
}
REQUIRED_TESTS_BEFORE_PUBLIC_HEADER = {
    "manifest.guardrails",
    "abi.layout",
    "sdk.consumer",
    "lifecycle.owner_cleanup",
    "identity.fail_closed",
    "privacy.redaction",
    "runtime.evidence_intake",
}
CONTRACT_REVIEW_INPUT_ONLY_TESTS = {
    "identity.fail_closed": {
        "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json",
        "scripts/check_player_identity_principal_invalidation_policy.py",
        "scripts/test_check_player_identity_principal_invalidation_policy.py",
        "scripts/check_player_identity_public_contract_gap_report.py",
        "scripts/test_check_player_identity_public_contract_gap_report.py",
    },
    "runtime.evidence_intake": {
        "scripts/check_player_identity_public_contract_readiness.py",
        "scripts/test_check_player_identity_public_contract_readiness.py",
        "scripts/test_player_identity_public_contract_decisions.py",
    },
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY = {
    "runtime evidence can prove a candidate lifecycle route was observed; it does not define a stable C ABI",
    "runtime evidence can show login/logout ordering; it does not choose the copied opaque identifier form, generation rules, or scope flags",
    "runtime evidence can support internal lifecycle semantics; it does not prove owner-token registration, unregister, plugin unload cleanup, or in-flight callback drain",
    "runtime evidence does not provide ABI layout tests, SDK consumer tests, or append-only compatibility rules",
    "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics",
    "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES = {
    "privacy and redaction decision resolved",
    "principal lifetime and invalidation decision resolved",
    "cross-instance/process-local scope decision resolved",
    "candidate POD payload and descriptor contract reviewed",
    "named capability and owner-token lifecycle policy reviewed",
    "ABI layout and SDK consumer tests passing",
    "public docs state exact non-claims and downstream dependency order",
}
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
NON_PROMOTIONAL_EVIDENCE_DENIAL = (
    "Request packs, preflight/window manifests, operator receipts, and live-ops sidecars are "
    "planning or operational-preparation artifacts only; they do not resolve runtime lifecycle "
    "evidence, public identity promotion, public ABI/SDK readiness, runtime readiness, or v1 completion."
)
REQUIRED_NON_CLAIMS = {
    "This manifest does not add public header symbols.",
    "This manifest does not promote obelisk.player_identity.v1.",
    "This manifest does not make approved runtime evidence sufficient by itself.",
    "This manifest does not expose player lookup.",
    "This manifest does not promote permissions/admin.",
    "This manifest does not promote command/chat response or commands/replies.",
    "This manifest does not authorize storage, persistence, cross-process identity, cluster-stable identity, mutation, return override, or send-chat identity.",
}
REQUIRED_PRIVATE_CANDIDATE_NON_CLAIMS = {
    "This artifact does not add public header symbols.",
    "This artifact does not reserve final C symbol names.",
    "This artifact does not promote obelisk.player_identity.v1.",
    "This artifact does not claim stable principal identity.",
    "This artifact does not make approved runtime evidence sufficient by itself.",
    "This artifact does not expose player lookup.",
    "This artifact does not expose platform account ids, player names, tribe ids, network addresses, UE pointers, FName/GObjects indices, or ResourceHandle.",
    "This artifact does not promote permissions/admin.",
    "This artifact does not promote command/chat response or commands/replies.",
    "This artifact does not authorize storage, persistence, cross-process identity, cluster-stable identity, mutation, return override, or send-chat identity.",
}
REQUIRED_TEST_COVERAGE_BY_ID = {
    "manifest.guardrails": {
        "decision gate remains blocked/planning until every blocker is resolved",
        "public_contract_allowed and public_header_allowed remain false while unresolved blockers exist",
        "public_header_symbols_now remains empty",
        "approved runtime evidence is documented as necessary but insufficient",
        "non-claims forbid lookup, permissions/admin, command/chat response, persistence, mutation, and return override",
    },
    "abi.layout": {
        "POD layout size and alignment tests",
        "abi_version and struct_size validation",
        "append-only field offset tests",
        "old-plugin prefix compatibility or explicit major-version rejection",
    },
    "sdk.consumer": {
        "installed SDK consumer compiles against the promoted header",
        "consumer checks struct_size and capability before using identity fields",
        "consumer treats callback payload storage as callback-local",
        "consumer treats principal handles and registration handles as process-local and non-persistent",
    },
    "lifecycle.owner_cleanup": {
        "owner-token registration rejects missing or zero owner tokens",
        "unregister is owner-scoped",
        "init failure removes callbacks before dlclose",
        "plugin unload drains in-flight callbacks",
        "self-unregister from callback is safe",
        "callback exceptions do not cross the C ABI",
    },
    "identity.fail_closed": {
        "stale generation fails closed",
        "unsupported scope fails closed",
        "duplicate principal observation invalidates or quarantines according to policy",
        "reconnect creates a new generation unless continuity is proven",
        "lookup-by-public-handle remains unavailable",
        "cross-instance or cross-process handle reuse fails closed",
    },
    "privacy.redaction": {
        "raw identity-like fields are classified before copying",
        "platform ids, player names, tribe ids, network addresses, and object references are redacted",
        "logs contain only allowed sanitized reason flags and handle presence",
        "no persistence is possible through the identity ABI",
    },
    "runtime.evidence_intake": {
        "approved runtime evidence is checked as an input to promotion",
        "approved runtime evidence alone leaves the public-header gate closed",
        "approved runtime evidence cannot set promotion_ready, public_sdk_ready, runtime_ready, or public_header_allowed",
        "offline fixtures and second-source layout evidence remain separate from runtime lifecycle acceptance",
    },
}
REQUIRED_BEFORE_PUBLIC_HEADER = {
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
    "capability is captured in the plugin init-time API table",
    "missing capability fails closed",
    "later env or marker changes cannot widen a loaded plugin's captured capability",
}
REQUIRED_OWNER_TOKEN_BEHAVIOR = {
    "nonzero plugin_owner_token required",
    "registration returns an opaque process-local handle",
    "unregister requires the same owner token",
    "registration handles are not persisted or shared across server processes",
    "init failure and plugin unload remove all owner registrations",
    "cleanup waits for in-flight callbacks except when policy explicitly permits same-callback self-unregister",
}
REQUIRED_ABI_LAYOUT_TESTS = {
    "POD layout size and alignment tests",
    "field offset and append-only compatibility tests",
    "struct_size short-write or rejection tests",
    "capability and owner-token fail-closed tests",
    "installed SDK consumer compile test",
    "callback lifecycle cleanup and drain tests",
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
REQUIRED_CANDIDATE_PAYLOAD_FIELDS = {
    "abi_version",
    "struct_size",
    "event_kind",
    "principal_handle",
    "principal_generation",
    "principal_scope_flags",
    "principal_state_flags",
    "invalidation_reason_flags",
    "event_sequence",
    "server_process_epoch",
    "reserved",
}
REQUIRED_CANDIDATE_DESCRIPTOR_FIELDS = {
    "abi_version",
    "struct_size",
    "supported_event_kind_mask",
    "supported_scope_flags",
    "supported_state_flags",
    "supported_invalidation_reason_flags",
    "contract_flags",
}
REQUIRED_CANDIDATE_EVENT_KIND_MASK = {
    "session_start",
    "session_start_rejected",
    "session_end",
}
REQUIRED_CANDIDATE_SCOPE_FLAGS = {
    "callback_local",
    "process_local",
    "restart_local_planning_only",
}
REQUIRED_CANDIDATE_STATE_FLAGS = {
    "candidate_created",
    "candidate_invalidated",
    "candidate_rejected",
    "stale_generation",
    "unsupported_scope",
}
REQUIRED_CANDIDATE_INVALIDATION_REASON_FLAGS = {
    "logout",
    "disconnect",
    "transfer",
    "reconnect",
    "duplicate_observation",
    "server_restart",
    "stale_controller_or_playerstate",
    "failed_evidence_validation",
}
REQUIRED_CANDIDATE_CONTRACT_FLAGS = {
    "copied_payload",
    "callback_local_payload_lifetime",
    "process_local_principal_handle",
    "no_lookup",
    "no_persistence",
    "no_permissions_or_commands_authority",
    "no_mutation",
    "no_return_override",
}
REQUIRED_CANDIDATE_SEQUENCE_POLICY = {
    "event_sequence is assigned once per copied source lifecycle event",
    "all subscribers to the same source lifecycle event observe the same event_sequence",
    "event_sequence is not a per-plugin delivery counter",
    "event_sequence is process-local and non-persistent",
}
REQUIRED_CANDIDATE_SERVER_PROCESS_EPOCH_POLICY = {
    "server_process_epoch is process-local and changes across server process lifetimes",
    "server_process_epoch invalidates process-local principal handles after restart",
    "server_process_epoch is not cluster-stable and not persistent",
}
REQUIRED_CANDIDATE_PAYLOAD_PROPERTIES = {
    "POD C ABI only",
    "front-loaded abi_version and struct_size",
    "append-only fields after promotion",
    "copied Obelisk-owned storage",
    "no UE pointers",
    "no raw ProcessEvent params",
    "no FString or raw string ownership crossing the ABI",
    "no FName/GObjects indices",
    "no platform account ids",
    "no player names",
    "no tribe ids",
    "no network addresses",
    "no lookup handle",
    "principal handles are process-local and non-persistent",
    "no mutation or return override authority",
}
REQUIRED_CANDIDATE_OWNER_TOKEN_REQUIREMENTS = {
    "nonzero plugin_owner_token required",
    "event-kind mask required",
    "opaque uint64 registration handle returned on success",
    "registration handles are process-local and non-persistent",
    "owner-token unregister required",
    "plugin init failure removes registrations",
    "plugin unload removes registrations and drains in-flight callbacks",
    "callback payload storage is valid only for the callback",
}
REQUIRED_CANDIDATE_FAIL_CLOSED_POLICY = {
    "capability must be captured in the init-time API table",
    "missing capability fails closed",
    "missing or zero owner token fails closed",
    "later marker or env changes cannot widen a plugin's captured capability",
}
REQUIRED_PRIVATE_CANDIDATE_EVENT_KIND_SEMANTICS = {
    "session_start creates only a copied principal candidate after runtime evidence proves the accepted lifecycle route",
    "session_start_rejected emits no principal authority and cannot create permissions or command authority",
    "session_end invalidates the copied principal candidate for later permission and command consumers",
}
REQUIRED_PRIVATE_CANDIDATE_SCOPE_SEMANTICS = {
    "callback-local scope may be consumed only during the callback that supplied the payload",
    "process-local scope may be compared only inside the same ARK server process and must carry principal_generation",
    "restart-local scope is a planning label only until restart semantics are promoted",
    "cluster-stable, cross-map, cross-process, and persistent identity are forbidden until separate storage/operator ingress contracts are promoted",
}
REQUIRED_PRIVATE_CANDIDATE_INVALIDATION_SEMANTICS = {
    "logout invalidates the copied principal candidate",
    "disconnect invalidates the copied principal candidate unless a later reviewed continuity contract says otherwise",
    "reconnect creates a new generation unless continuity is proven by a future promoted contract",
    "duplicate principal observation invalidates or quarantines both candidates",
    "server restart invalidates all process-local principal handles",
    "failed evidence validation invalidates the candidate and keeps public identity blocked",
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
REQUIRED_PRIVATE_CANDIDATE_DOWNSTREAM_POLICY = {
    "permissions/admin cannot consume identity until this surface is promoted with public ABI and tests",
    "command/chat response cannot consume identity until permissions/admin is promoted",
    "commands/replies cannot consume identity until command/chat response is promoted or explicitly excluded with reviewed wording",
    "operator config, command text, chat intake, send mode, static thunks, raw ProcessEvent, and runtime evidence alone cannot establish principal identity",
}
FORBIDDEN_CANDIDATE_FIELD_PATTERNS = {
    "lookup": re.compile(r"lookup", re.IGNORECASE),
    "resolve": re.compile(r"resolve", re.IGNORECASE),
    "get": re.compile(r"(?:^|[_\W])get(?:$|[_\W])|Get[A-Z_]", re.IGNORECASE),
    "raw_ue": re.compile(r"raw.*ue|ue.*raw", re.IGNORECASE),
    "private_identity": re.compile(r"private.*identity|identity.*private", re.IGNORECASE),
    "platform": re.compile(r"platform", re.IGNORECASE),
    "player_name": re.compile(r"player[_\s-]*names?", re.IGNORECASE),
    "tribe": re.compile(r"tribe", re.IGNORECASE),
    "ip": re.compile(r"\bIP\b|ip[_\s-]*address(?:es)?|network[_\s-]*address(?:es)?", re.IGNORECASE),
    "fname_gobjects": re.compile(r"FName|GObjects", re.IGNORECASE),
    "resource_handle": re.compile(r"ResourceHandle|resource[_\s-]*handle", re.IGNORECASE),
    "persistent": re.compile(r"persist(?:ent|ed|ence)?", re.IGNORECASE),
    "cluster": re.compile(r"cluster", re.IGNORECASE),
    "cross_process": re.compile(r"cross[_\s-]*process", re.IGNORECASE),
    "cross_map": re.compile(r"cross[_\s-]*map", re.IGNORECASE),
}
PUBLIC_CLAIM_KEYS = ("public_header_allowed", "promotion_ready", "public_sdk_ready", "runtime_ready")
READINESS_FALSE_KEYS = {
    "accepted_for_contract_review",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_contract_allowed",
    "public_abi_ready",
    "v1_completion_ready",
    "v1_completion_evidence",
    "public_sdk_v1_completion_claim",
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
PUBLIC_HEADER_IDENTITY_IDENTIFIER_RE = re.compile(
    r"identity|principal|steam_?id|steamid|"
    r"player_?(?:id|handle|data_?id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player|platform.*id|account.*id",
    re.IGNORECASE,
)
PUBLIC_HEADER_IDENTITY_IDENTIFIER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
}
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decisions",
        type=Path,
        default=Path("docs/player_identity_public_contract_decisions.json"),
        help="Player identity public contract decision manifest.",
    )
    parser.add_argument(
        "--approved-runtime-evidence",
        type=Path,
        required=True,
        help="Approved runtime principal lifecycle evidence manifest.",
    )
    parser.add_argument(
        "--identifier-redaction-evidence",
        type=Path,
        help="Optional sanitized identifier-redaction evidence manifest for contract-review intake only.",
    )
    parser.add_argument(
        "--principal-invalidation-policy",
        type=Path,
        default=DEFAULT_PRINCIPAL_INVALIDATION_POLICY,
        help="Candidate-only principal invalidation policy for lifetime/generation/scope review intake only.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument(
        "--public-header",
        type=Path,
        default=Path("include/obelisk/ObeliskApi.h"),
        help="Public SDK header to scan for player identity/principal tokens.",
    )
    parser.add_argument(
        "--private-candidate-contract",
        type=Path,
        default=DEFAULT_PRIVATE_CANDIDATE_CONTRACT,
        help="Private candidate-only player identity contract artifact.",
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
    parser.add_argument("--promote", action="store_true", help="Fail closed for promotion checks.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public SDK readiness checks.")
    parser.add_argument("--runtime-readiness", action="store_true", help="Fail closed for runtime readiness checks.")
    return parser.parse_args()


def mode(args: argparse.Namespace) -> str:
    requested = [
        name
        for name, enabled in (
            ("promote", args.promote),
            ("public_readiness", args.public_readiness),
            ("runtime_readiness", args.runtime_readiness),
        )
        if enabled
    ]
    if len(requested) > 1:
        raise SystemExit("--promote, --public-readiness, and --runtime-readiness are mutually exclusive")
    return requested[0] if requested else "consume"


def add(blockers: list[dict[str, Any]], reason: str, label: str, **extra: Any) -> None:
    blocker = {"reason": reason, "label": label}
    blocker.update(extra)
    blockers.append(blocker)


def load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{label}: top-level JSON must be an object")
    return payload


def safe_load_json(path: Path, label: str, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    try:
        reject_symlink_component(path, label)
        resolved = reject_protected_input_path(path, label)
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", path=str(path), error=str(exc))
        return None
    except OSError as exc:
        add(blockers, f"{label}_unreadable", f"$.{label}", path=str(path), error=str(exc))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, f"{label}_invalid_json", f"$.{label}", path=str(path), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, f"{label}_not_object", f"$.{label}", path=str(path))
        return None
    return payload


def safe_resolve_input_path(path: Path, label: str, blockers: list[dict[str, Any]]) -> Path | None:
    try:
        reject_symlink_component(path, label)
        return reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(blockers, f"{label}_path_rejected", f"$.{label}", path=str(path), error=str(exc))
        return None


def approved_runtime_report(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = approved_evidence.load_json(path)
    except (OSError, SystemExit) as exc:
        add(blockers, "approved_runtime_evidence_unreadable", "$.approved_runtime_evidence", error=str(exc))
        return {
            "ready": False,
            "approved_runtime_evidence_present": False,
            "runtime_evidence_ready": False,
            "remaining_blockers": ["approved_runtime_evidence_missing"],
        }

    validation = approved_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_evidence.build_report(payload, validation, check_mode="consume")
    if validation.blockers:
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "$.approved_runtime_evidence",
            reasons=[blocker["reason"] for blocker in validation.blockers],
        )
    else:
        if report.get("next_blocker") != "identity_public_contract_gate_missing":
            add(
                blockers,
                "approved_runtime_evidence_next_blocker_mismatch",
                "$.approved_runtime_evidence.next_blocker",
                value=report.get("next_blocker"),
            )
        if report.get("approved_runtime_evidence_present") is not True:
            add(
                blockers,
                "approved_runtime_evidence_presence_missing",
                "$.approved_runtime_evidence.approved_runtime_evidence_present",
            )
        if report.get("runtime_evidence_ready") is not True:
            add(
                blockers,
                "approved_runtime_evidence_runtime_ready_missing",
                "$.approved_runtime_evidence.runtime_evidence_ready",
            )
        resolved_inputs = report.get("resolved_inputs")
        if resolved_inputs is not None:
            if not isinstance(resolved_inputs, list) or not all(
                isinstance(item, str) for item in resolved_inputs
            ):
                add(
                    blockers,
                    "approved_runtime_evidence_resolved_inputs_not_string_list",
                    "$.approved_runtime_evidence.resolved_inputs",
                    value=resolved_inputs,
                )
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
                        "$.approved_runtime_evidence.resolved_inputs",
                        forbidden=forbidden_inputs,
                    )
                unexpected_inputs = sorted(set(resolved_inputs) - {REQUIRED_RESOLVED_INPUT})
                if unexpected_inputs:
                    add(
                        blockers,
                        "approved_runtime_evidence_resolved_inputs_unexpected",
                        "$.approved_runtime_evidence.resolved_inputs",
                        unexpected=unexpected_inputs,
                    )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if key in report and report.get(key) is not False:
            add(blockers, f"approved_runtime_evidence_{key}_not_false", f"$.approved_runtime_evidence.{key}")
    return report


def identifier_redaction_report(path: Path | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "ready": False,
            "accepted_for_contract_review": False,
            "resolved_inputs": [],
            "remaining_blockers": [REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT],
        }
    try:
        payload = identifier_redaction.load_evidence(path)
    except (OSError, SystemExit) as exc:
        add(blockers, "identifier_redaction_evidence_unreadable", "$.identifier_redaction_evidence", error=str(exc))
        return {
            "provided": True,
            "ready": False,
            "accepted_for_contract_review": False,
            "resolved_inputs": [],
            "remaining_blockers": [REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT],
        }

    validation_blockers = identifier_redaction.validate_evidence(payload)
    report = identifier_redaction.build_report(payload, validation_blockers)
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if payload.get(key) is not False or report.get(key) is not False:
            add(blockers, f"identifier_redaction_evidence_{key}_not_false", f"$.identifier_redaction_evidence.{key}")
    if validation_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "$.identifier_redaction_evidence",
            reasons=[blocker["reason"] for blocker in validation_blockers],
        )
    else:
        if report.get("accepted_for_contract_review") is not True:
            add(
                blockers,
                "identifier_redaction_evidence_contract_review_not_accepted",
                "$.identifier_redaction_evidence.accepted_for_contract_review",
            )
        if report.get("resolved_inputs") != [REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT]:
            add(
                blockers,
                "identifier_redaction_evidence_resolved_inputs_mismatch",
                "$.identifier_redaction_evidence.resolved_inputs",
                value=report.get("resolved_inputs"),
            )
        if report.get("next_blocker") in {
            "identity_public_contract_gate",
            NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
        }:
            add(
                blockers,
                "identifier_redaction_evidence_route_unlock_claimed",
                "$.identifier_redaction_evidence.next_blocker",
                value=report.get("next_blocker"),
            )
    return {
        "provided": True,
        "ready": report.get("ready") is True,
        "accepted_for_contract_review": report.get("accepted_for_contract_review") is True,
        "resolved_inputs": report.get("resolved_inputs") if isinstance(report.get("resolved_inputs"), list) else [],
        "remaining_blockers": report.get("remaining_blockers") if isinstance(report.get("remaining_blockers"), list) else [],
    }


def principal_invalidation_policy_report(path: Path | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "accepted_for_policy_review": False,
            "resolved_input": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "principal_invalidation_ready": False,
            "blockers": ["principal_invalidation_policy_missing"],
        }
    try:
        payload = principal_invalidation_policy.load_json(path)
    except (OSError, SystemExit) as exc:
        add(blockers, "principal_invalidation_policy_unreadable", "$.principal_invalidation_policy", error=str(exc))
        return {
            "provided": True,
            "accepted_for_policy_review": False,
            "resolved_input": None,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "principal_invalidation_ready": False,
            "blockers": ["principal_invalidation_policy_unreadable"],
        }

    validation = principal_invalidation_policy.validate_manifest(payload, check_mode="consume")
    report = principal_invalidation_policy.build_report(payload, validation, check_mode="consume")
    if validation.blockers:
        add(
            blockers,
            "principal_invalidation_policy_not_accepted",
            "$.principal_invalidation_policy",
            reasons=[blocker["reason"] for blocker in validation.blockers],
        )
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "principal_invalidation_ready"):
        if report.get(key) is not False:
            add(blockers, f"principal_invalidation_policy_{key}_not_false", f"$.principal_invalidation_policy.{key}")
    return {
        "provided": True,
        "accepted_for_policy_review": not validation.blockers,
        "resolved_input": PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT if not validation.blockers else None,
        "mode": report.get("mode"),
        "candidate_only": report.get("candidate_only") is True,
        "principal_fields": report.get("principal_fields", []),
        "invalidation_cases": report.get("invalidation_cases", []),
        "negative_consumer_rules": report.get("negative_consumer_rules", []),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "principal_invalidation_ready": False,
        "blockers": report.get("blockers", []),
    }


def public_abi_preflight_candidate_report(
    path: Path | None,
    public_header_path: Path,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    if path is None:
        add(blockers, "public_abi_preflight_candidate_missing", "$.public_abi_preflight_candidate")
        return {
            "provided": False,
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
            "blockers": ["public_abi_preflight_candidate_missing"],
        }
    try:
        payload = public_abi_preflight_candidate.load_json(path)
        private_payload = public_abi_preflight_candidate.private_layout.load_json(
            public_abi_preflight_candidate.DEFAULT_PRIVATE_LAYOUT
        )
        private_contract = public_abi_preflight_candidate.private_layout.load_json(
            public_abi_preflight_candidate.private_layout.DEFAULT_PRIVATE_CONTRACT
        )
        private_blockers = public_abi_preflight_candidate.private_layout.validate_manifest(
            private_payload,
            private_contract,
        )
        private_report = public_abi_preflight_candidate.private_layout.build_report(
            private_payload,
            private_blockers,
        )
        redaction_payload = public_abi_preflight_candidate.identifier_redaction.load_evidence(
            public_abi_preflight_candidate.DEFAULT_IDENTIFIER_REDACTION
        )
        redaction_blockers = public_abi_preflight_candidate.identifier_redaction.validate_evidence(redaction_payload)
        redaction_report = public_abi_preflight_candidate.identifier_redaction.build_report(
            redaction_payload,
            redaction_blockers,
        )
        principal_payload = public_abi_preflight_candidate.principal_invalidation.load_json(
            public_abi_preflight_candidate.DEFAULT_PRINCIPAL_INVALIDATION
        )
        principal_validation = public_abi_preflight_candidate.principal_invalidation.validate_manifest(
            principal_payload,
            check_mode="consume",
        )
        principal_report = public_abi_preflight_candidate.principal_invalidation.build_report(
            principal_payload,
            principal_validation,
            check_mode="consume",
        )
    except (OSError, json.JSONDecodeError, ValueError, SystemExit) as exc:
        add(
            blockers,
            "public_abi_preflight_candidate_unreadable_or_rejected",
            "$.public_abi_preflight_candidate",
            path=str(path),
            error=str(exc),
        )
        return {
            "provided": True,
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
            "$.public_abi_preflight_candidate.private_pod_layout_candidate",
            layout_blockers=private_report["blockers"],
        )
    if redaction_blockers:
        public_abi_preflight_candidate.add(
            candidate_blockers,
            "identifier_redaction_evidence_not_accepted",
            "$.public_abi_preflight_candidate.identifier_redaction_evidence",
            input_blockers=redaction_report["blockers"],
        )
    if principal_validation.blockers:
        public_abi_preflight_candidate.add(
            candidate_blockers,
            "principal_invalidation_policy_not_accepted",
            "$.public_abi_preflight_candidate.principal_invalidation_policy",
            input_blockers=principal_report["blockers"],
        )
    header_scan = public_abi_preflight_candidate.scan_public_header(public_header_path, candidate_blockers)
    public_abi_preflight_candidate.validate_manifest(payload, private_payload, candidate_blockers)
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
    report = sanitize_non_promotional_report(
        report,
        blockers,
        input_label="public_abi_preflight_candidate",
        path="$.public_abi_preflight_candidate",
    )
    if candidate_blockers:
        add(
            blockers,
            "public_abi_preflight_candidate_not_accepted",
            "$.public_abi_preflight_candidate",
            path=str(path),
            preflight_blockers=report["blockers"],
        )
    for key in (
        "accepted_for_contract_review",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "public_header_allowed",
        "public_abi_ready",
        "v1_completion_evidence",
    ):
        if report.get(key) is not False:
            add(blockers, f"public_abi_preflight_candidate_{key}_not_false", f"$.public_abi_preflight_candidate.{key}")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if report.get(key) != []:
            add(blockers, f"public_abi_preflight_candidate_{key}_not_empty", f"$.public_abi_preflight_candidate.{key}")
    return {
        "provided": True,
        "status": report.get("status"),
        "candidate_only": report.get("candidate_only") is True,
        "accepted_for_candidate_review": report.get("accepted_for_candidate_review") is True,
        "accepted_for_contract_review": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "v1_completion_evidence": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "contract_review_inputs_accepted": report.get("contract_review_inputs_accepted", {}),
        "required_before_public_abi": report.get("required_before_public_abi", []),
        "required_capability_policy": report.get("required_capability_policy", []),
        "required_owner_token_lifecycle": report.get("required_owner_token_lifecycle", []),
        "sdk_consumer_contract": report.get("sdk_consumer_contract", {}),
        "does_not_resolve": report.get("does_not_resolve", []),
        "blockers": report.get("blockers", []),
        "non_claims": report.get("non_claims", []),
    }


def owner_token_sdk_consumer_contract_report(
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
            "$.owner_token_sdk_consumer_contract",
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
            "$.owner_token_sdk_consumer_contract",
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
            "$.owner_token_sdk_consumer_contract",
            path=str(path),
            contract_blockers=report["blockers"],
        )
    return sanitize_non_promotional_report(
        {"provided": True, "source": "owner_token_sdk_consumer_contract", **report},
        blockers,
        input_label="owner_token_sdk_consumer_contract",
        path="$.owner_token_sdk_consumer_contract",
    )


def string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return value


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
            contract_review_allowed = (
                key == "accepted_for_contract_review"
                and path != root_path
                and item_path.endswith(NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES)
            )
            if key in READINESS_FALSE_KEYS and not contract_review_allowed:
                if item is not False:
                    add(blockers, "nested_readiness_flag_not_false", item_path, input=input_label, value=item)
                sanitized[key] = False
            elif key in EMPTY_PUBLIC_LIST_KEYS:
                if item != []:
                    add(blockers, f"nested_{key}_not_empty", item_path, input=input_label, value=item)
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


def missing_required(observed: list[str] | None, required: set[str]) -> list[str]:
    return sorted(required - set(observed or []))


def forbidden_candidate_strings(values: list[str]) -> dict[str, list[str]]:
    observed: dict[str, list[str]] = {}
    for value in values:
        for token, pattern in FORBIDDEN_CANDIDATE_FIELD_PATTERNS.items():
            if pattern.search(value):
                observed.setdefault(token, []).append(value)
    return observed


def require_string_list_contains(
    item: dict[str, Any],
    key: str,
    required: set[str],
    blockers: list[dict[str, Any]],
    reason: str,
    label: str,
) -> None:
    values = string_list(item.get(key))
    if values is None:
        add(blockers, f"{reason}_not_string_list", label)
        return
    missing = missing_required(values, required)
    if missing:
        add(blockers, reason, label, missing=missing)


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
            if char == "\n":
                output.append("\n")
                state = "code"
            else:
                output.append(" ")
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
                output.extend(("\n" if char == "\n" else " ", "\n" if next_char == "\n" else " "))
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


def public_header_identity_tokens(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = strip_c_comments_and_strings(text)
    detected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(stripped.splitlines(), start=1):
        for match in IDENTIFIER_RE.finditer(line):
            token = match.group(0)
            if token in PUBLIC_HEADER_IDENTITY_IDENTIFIER_ALLOWLIST:
                continue
            if not PUBLIC_HEADER_IDENTITY_IDENTIFIER_RE.search(token):
                continue
            if token in seen:
                continue
            seen.add(token)
            detected.append({"token": token, "line": line_number})
    return detected


def validate_public_header(decisions: dict[str, Any], path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    resolved = safe_resolve_input_path(path, "public_header", blockers)
    if resolved is None:
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}
    if resolved != DEFAULT_PUBLIC_HEADER.resolve():
        add(
            blockers,
            "public_header_path_mismatch",
            "$.public_header",
            expected=str(DEFAULT_PUBLIC_HEADER),
            path=str(path),
            resolved=str(resolved),
        )
    declared = decisions.get("public_header")
    if declared == DEFAULT_PUBLIC_HEADER_DECL and DEFAULT_PUBLIC_HEADER.resolve() != resolved:
        add(
            blockers,
            "decisions_public_header_not_scanned_header",
            "$.public_header",
            declared=str(DEFAULT_PUBLIC_HEADER),
            scanned=str(path),
        )
    try:
        detected = public_header_identity_tokens(resolved)
    except OSError as exc:
        add(blockers, "public_header_unreadable", "$.public_header", path=str(path), error=str(exc))
        return {"path": str(path), "readable": False, "detected_player_identity_tokens": []}

    if decisions.get("public_header_symbols_now") == [] and detected:
        add(
            blockers,
            "public_header_contains_unmanifested_player_identity_tokens",
            "$.public_header_symbols_now",
            path=str(path),
            detected_tokens=detected,
        )
    return {"path": str(path), "readable": True, "detected_player_identity_tokens": detected}


def candidate_public_claim_keys(prefix: str, candidate: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if candidate.get("public_header_allowed") is not False:
        add(blockers, f"{prefix}_public_header_allowed_not_false", f"$.{prefix}.public_header_allowed")
    for key in PUBLIC_CLAIM_KEYS:
        if key in candidate and candidate.get(key) is not False:
            add(blockers, f"{prefix}_{key}_claim_not_false", f"$.{prefix}.{key}")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if key in candidate and candidate.get(key) != []:
            add(blockers, f"{prefix}_{key}_not_empty", f"$.{prefix}.{key}")


def validate_candidate_only_pod_abi(candidate: Any, blockers: list[dict[str, Any]], *, label: str = "proposed_public_pod_abi_candidate") -> None:
    if not isinstance(candidate, dict):
        add(blockers, "candidate_public_pod_abi_missing", f"$.{label}")
        return

    if candidate.get("status") != "proposal_only_not_public":
        add(blockers, "candidate_status_not_proposal_only", f"$.{label}.status")
    if candidate.get("candidate_only") is not True:
        add(blockers, "candidate_only_not_true", f"$.{label}.candidate_only")
    candidate_public_claim_keys("candidate", candidate, blockers)

    payload_properties = string_list(candidate.get("required_payload_properties"))
    if payload_properties is None:
        add(blockers, "candidate_required_payload_properties_not_string_list", f"$.{label}.required_payload_properties")
    else:
        missing = missing_required(payload_properties, REQUIRED_CANDIDATE_PAYLOAD_PROPERTIES)
        if missing:
            add(
                blockers,
                "candidate_required_payload_properties_missing",
                f"$.{label}.required_payload_properties",
                missing=missing,
            )

    event_fields = string_list(candidate.get("candidate_event_payload_fields_or_equivalent"))
    if event_fields is None:
        add(blockers, "candidate_event_payload_fields_not_string_list", f"$.{label}.candidate_event_payload_fields_or_equivalent")
    else:
        missing = missing_required(event_fields, REQUIRED_CANDIDATE_PAYLOAD_FIELDS)
        if missing:
            add(
                blockers,
                "candidate_event_payload_fields_missing",
                f"$.{label}.candidate_event_payload_fields_or_equivalent",
                missing=missing,
            )
        forbidden = forbidden_candidate_strings(event_fields)
        if forbidden:
            add(
                blockers,
                "candidate_event_payload_fields_forbidden_identity_or_lookup",
                f"$.{label}.candidate_event_payload_fields_or_equivalent",
                forbidden=forbidden,
            )

    descriptor_fields = string_list(candidate.get("candidate_descriptor_fields_or_equivalent"))
    if descriptor_fields is None:
        add(blockers, "candidate_descriptor_fields_not_string_list", f"$.{label}.candidate_descriptor_fields_or_equivalent")
    else:
        missing = missing_required(descriptor_fields, REQUIRED_CANDIDATE_DESCRIPTOR_FIELDS)
        if missing:
            add(
                blockers,
                "candidate_descriptor_fields_missing",
                f"$.{label}.candidate_descriptor_fields_or_equivalent",
                missing=missing,
            )
        forbidden = forbidden_candidate_strings(descriptor_fields)
        if forbidden:
            add(
                blockers,
                "candidate_descriptor_fields_forbidden_identity_or_lookup",
                f"$.{label}.candidate_descriptor_fields_or_equivalent",
                forbidden=forbidden,
            )

    for key, required, reason in (
        ("candidate_event_kind_mask", REQUIRED_CANDIDATE_EVENT_KIND_MASK, "candidate_event_kind_mask_missing"),
        ("candidate_scope_flags", REQUIRED_CANDIDATE_SCOPE_FLAGS, "candidate_scope_flags_missing"),
        ("candidate_state_flags", REQUIRED_CANDIDATE_STATE_FLAGS, "candidate_state_flags_missing"),
        (
            "candidate_invalidation_reason_flags",
            REQUIRED_CANDIDATE_INVALIDATION_REASON_FLAGS,
            "candidate_invalidation_reason_flags_missing",
        ),
        ("candidate_contract_flags", REQUIRED_CANDIDATE_CONTRACT_FLAGS, "candidate_contract_flags_missing"),
        ("sequence_policy", REQUIRED_CANDIDATE_SEQUENCE_POLICY, "candidate_sequence_policy_missing"),
        (
            "server_process_epoch_policy",
            REQUIRED_CANDIDATE_SERVER_PROCESS_EPOCH_POLICY,
            "candidate_server_process_epoch_policy_missing",
        ),
    ):
        values = string_list(candidate.get(key))
        if values is None:
            add(blockers, f"{reason}_not_string_list", f"$.{label}.{key}")
            continue
        missing = missing_required(values, required)
        if missing:
            add(blockers, reason, f"$.{label}.{key}", missing=missing)

    registration = string_list(candidate.get("candidate_registration_shape_or_equivalent"))
    if registration is None:
        add(blockers, "candidate_registration_shape_not_string_list", f"$.{label}.candidate_registration_shape_or_equivalent")
    else:
        missing = missing_required(registration, REQUIRED_CANDIDATE_OWNER_TOKEN_REQUIREMENTS)
        if missing:
            add(
                blockers,
                "candidate_owner_token_cleanup_requirements_missing",
                f"$.{label}.candidate_registration_shape_or_equivalent",
                missing=missing,
            )

    capability_policy = string_list(candidate.get("candidate_capability_policy"))
    if capability_policy is None:
        add(blockers, "candidate_capability_policy_not_string_list", f"$.{label}.candidate_capability_policy")
    else:
        missing = missing_required(capability_policy, REQUIRED_CANDIDATE_FAIL_CLOSED_POLICY)
        if missing:
            add(
                blockers,
                "candidate_fail_closed_policy_missing",
                f"$.{label}.candidate_capability_policy",
                missing=missing,
            )


def validate_private_candidate_contract(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = "private_candidate_contract"
    if payload.get("schema") != PRIVATE_CANDIDATE_SCHEMA:
        add(blockers, "private_candidate_contract_schema_mismatch", "$.private_candidate_contract.schema")
    if payload.get("surface") != SURFACE:
        add(blockers, "private_candidate_contract_surface_mismatch", "$.private_candidate_contract.surface")
    if payload.get("artifact_status") != "candidate_only":
        add(blockers, "private_candidate_contract_artifact_status_not_candidate_only", "$.private_candidate_contract.artifact_status")
    if payload.get("visibility") != "private_planning_contract":
        add(blockers, "private_candidate_contract_visibility_mismatch", "$.private_candidate_contract.visibility")
    validate_candidate_only_pod_abi(payload, blockers, label=label)
    for key, required, reason in (
        ("candidate_event_kind_semantics", REQUIRED_PRIVATE_CANDIDATE_EVENT_KIND_SEMANTICS, "private_candidate_event_kind_semantics_missing"),
        ("candidate_scope_semantics", REQUIRED_PRIVATE_CANDIDATE_SCOPE_SEMANTICS, "private_candidate_scope_semantics_missing"),
        ("candidate_invalidation_semantics", REQUIRED_PRIVATE_CANDIDATE_INVALIDATION_SEMANTICS, "private_candidate_invalidation_semantics_missing"),
        (
            "candidate_stale_handle_fail_closed_semantics",
            REQUIRED_PRIVATE_CANDIDATE_STALE_HANDLE_FAIL_CLOSED_SEMANTICS,
            "private_candidate_stale_handle_fail_closed_semantics_missing",
        ),
        ("candidate_downstream_dependency_policy", REQUIRED_PRIVATE_CANDIDATE_DOWNSTREAM_POLICY, "private_candidate_downstream_policy_missing"),
        ("non_claims", REQUIRED_PRIVATE_CANDIDATE_NON_CLAIMS, "private_candidate_non_claims_missing"),
    ):
        values = string_list(payload.get(key))
        if values is None:
            add(blockers, f"{reason}_not_string_list", f"$.private_candidate_contract.{key}")
            continue
        missing = missing_required(values, required)
        if missing:
            add(blockers, reason, f"$.private_candidate_contract.{key}", missing=missing)


def load_private_candidate_contract(decisions: dict[str, Any], path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    expected = decisions.get("private_candidate_contract")
    if expected != str(DEFAULT_PRIVATE_CANDIDATE_CONTRACT):
        add(
            blockers,
            "private_candidate_contract_path_mismatch",
            "$.private_candidate_contract",
            expected=str(DEFAULT_PRIVATE_CANDIDATE_CONTRACT),
            observed=expected,
        )
    payload = safe_load_json(path, "private_candidate_contract", blockers)
    if payload is None:
        return {}
    validate_private_candidate_contract(payload, blockers)
    return payload


def validate_required_before_public_header(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    requirements = decisions.get("required_before_public_header")
    if not isinstance(requirements, list):
        add(blockers, "required_before_public_header_not_list", "$.required_before_public_header")
        return

    by_id: dict[str, dict[str, Any]] = {}
    observed_ids: set[Any] = set()
    for index, item in enumerate(requirements):
        if not isinstance(item, dict):
            add(blockers, "required_before_public_header_entry_not_object", f"$.required_before_public_header[{index}]")
            continue
        requirement_id = item.get("id")
        observed_ids.add(requirement_id)
        if isinstance(requirement_id, str):
            by_id[requirement_id] = item
        if item.get("status") == "resolved":
            add(blockers, "required_before_public_header_resolved_without_public_gate", f"$.required_before_public_header[{index}]", requirement_id=requirement_id)

    if observed_ids != REQUIRED_BEFORE_PUBLIC_HEADER:
        add(
            blockers,
            "required_before_public_header_mismatch",
            "$.required_before_public_header",
            expected=sorted(REQUIRED_BEFORE_PUBLIC_HEADER),
            observed=sorted(str(item) for item in observed_ids),
        )

    public_form = by_id.get("privacy.public_identifier_form")
    if public_form is not None:
        require_string_list_contains(
            public_form,
            "must_not_expose",
            REQUIRED_PUBLIC_IDENTIFIER_FORBIDDEN,
            blockers,
            "privacy_public_identifier_form_missing_forbidden_terms",
            "$.required_before_public_header[privacy.public_identifier_form].must_not_expose",
        )
        require_string_list_contains(
            public_form,
            "required_properties",
            REQUIRED_PUBLIC_IDENTIFIER_PROPERTIES,
            blockers,
            "privacy_public_identifier_form_missing_required_properties",
            "$.required_before_public_header[privacy.public_identifier_form].required_properties",
        )

    redaction = by_id.get("privacy.redacted_identifier_fields")
    if redaction is not None:
        require_string_list_contains(
            redaction,
            "allowed_field_classes",
            REQUIRED_REDACTION_CLASSES,
            blockers,
            "privacy_redacted_identifier_fields_missing_allowed_classes",
            "$.required_before_public_header[privacy.redacted_identifier_fields].allowed_field_classes",
        )
        require_string_list_contains(
            redaction,
            "must_redact",
            REQUIRED_REDACTED_FIELDS,
            blockers,
            "privacy_redacted_identifier_fields_missing_redactions",
            "$.required_before_public_header[privacy.redacted_identifier_fields].must_redact",
        )

    logging_policy = by_id.get("privacy.logging_and_storage_policy")
    if logging_policy is not None:
        if logging_policy.get("default_policy") != "no identity persistence and no raw identity logging":
            add(blockers, "privacy_logging_storage_default_policy_mismatch", "$.required_before_public_header[privacy.logging_and_storage_policy].default_policy")
        require_string_list_contains(
            logging_policy,
            "requires_before_persistence",
            {
                "operator ingress/storage surface promotion",
                "storage schema and migration policy",
                "secret-safe encoding policy",
                "audit and retention policy",
            },
            blockers,
            "privacy_logging_storage_missing_persistence_gates",
            "$.required_before_public_header[privacy.logging_and_storage_policy].requires_before_persistence",
        )

    scope = by_id.get("lifetime.principal_scope")
    if scope is not None:
        require_string_list_contains(scope, "allowed_scopes", REQUIRED_ALLOWED_SCOPES, blockers, "lifetime_principal_scope_missing_allowed_scopes", "$.required_before_public_header[lifetime.principal_scope].allowed_scopes")
        require_string_list_contains(scope, "forbidden_until_separate_promotion", REQUIRED_FORBIDDEN_SCOPES, blockers, "lifetime_principal_scope_missing_forbidden_scopes", "$.required_before_public_header[lifetime.principal_scope].forbidden_until_separate_promotion")
        require_string_list_contains(scope, "required_fields", REQUIRED_SCOPE_FIELDS, blockers, "lifetime_principal_scope_missing_required_fields", "$.required_before_public_header[lifetime.principal_scope].required_fields")
        allowed_scopes = string_list(scope.get("allowed_scopes"))
        if allowed_scopes is not None:
            forbidden_allowed = sorted(REQUIRED_FORBIDDEN_SCOPES & set(allowed_scopes))
            if forbidden_allowed:
                add(blockers, "lifetime_principal_scope_forbidden_scope_allowed", "$.required_before_public_header[lifetime.principal_scope].allowed_scopes", forbidden=forbidden_allowed)

    invalidation = by_id.get("lifetime.invalidation_events")
    if invalidation is not None:
        require_string_list_contains(invalidation, "required_invalidation_events", REQUIRED_INVALIDATION_EVENTS, blockers, "lifetime_invalidation_events_missing", "$.required_before_public_header[lifetime.invalidation_events].required_invalidation_events")
        require_string_list_contains(invalidation, "required_behavior", REQUIRED_INVALIDATION_BEHAVIOR, blockers, "lifetime_invalidation_behavior_missing", "$.required_before_public_header[lifetime.invalidation_events].required_behavior")

    stale_policy = by_id.get("lifetime.reconnect_duplicate_stale_policy")
    if stale_policy is not None:
        require_string_list_contains(stale_policy, "required_policy", REQUIRED_STALE_POLICY, blockers, "lifetime_reconnect_duplicate_stale_policy_missing", "$.required_before_public_header[lifetime.reconnect_duplicate_stale_policy].required_policy")

    payload_shape = by_id.get("abi.payload_shape")
    if payload_shape is not None:
        require_string_list_contains(payload_shape, "required_fields_or_equivalent", REQUIRED_CANDIDATE_PAYLOAD_FIELDS - {"reserved"}, blockers, "abi_payload_shape_missing_required_fields", "$.required_before_public_header[abi.payload_shape].required_fields_or_equivalent")
        require_string_list_contains(payload_shape, "required_properties", REQUIRED_ABI_PAYLOAD_SHAPE_PROPERTIES, blockers, "abi_payload_shape_missing_required_properties", "$.required_before_public_header[abi.payload_shape].required_properties")

    capability = by_id.get("abi.capability_bits")
    if capability is not None:
        require_string_list_contains(capability, "required_behavior", REQUIRED_CAPABILITY_BEHAVIOR, blockers, "abi_capability_bits_missing_fail_closed_behavior", "$.required_before_public_header[abi.capability_bits].required_behavior")

    owner_token = by_id.get("abi.owner_token_registration")
    if owner_token is not None:
        require_string_list_contains(owner_token, "required_behavior", REQUIRED_OWNER_TOKEN_BEHAVIOR, blockers, "abi_owner_token_registration_missing_fail_closed_behavior", "$.required_before_public_header[abi.owner_token_registration].required_behavior")

    layout_tests = by_id.get("abi.append_only_layout_tests")
    if layout_tests is not None:
        require_string_list_contains(layout_tests, "required_tests", REQUIRED_ABI_LAYOUT_TESTS, blockers, "abi_append_only_layout_tests_missing", "$.required_before_public_header[abi.append_only_layout_tests].required_tests")

    separation = by_id.get("separation.no_commands_permissions_persistence")
    if separation is not None:
        sequence_gate = string_list(separation.get("v1_sequence_gate"))
        if sequence_gate != REQUIRED_SEQUENCE_GATE:
            add(blockers, "separation_sequence_gate_mismatch", "$.required_before_public_header[separation.no_commands_permissions_persistence].v1_sequence_gate")
        require_string_list_contains(separation, "forbidden_in_identity_contract", REQUIRED_SEPARATION_FORBIDDEN, blockers, "separation_forbidden_downstream_surfaces_missing", "$.required_before_public_header[separation.no_commands_permissions_persistence].forbidden_in_identity_contract")


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    if decisions.get("schema") != DECISION_SCHEMA:
        add(blockers, "decision_schema_mismatch", "$.schema")
    if decisions.get("surface") != SURFACE:
        add(blockers, "decision_surface_mismatch", "$.surface")
    if decisions.get("status") != "blocked":
        add(blockers, "decision_status_not_blocked", "$.status")
    if decisions.get("planning_stage") != "identity_public_contract_gate":
        add(blockers, "decision_planning_stage_mismatch", "$.planning_stage")
    decision_gate = decisions.get("decision_gate")
    if not isinstance(decision_gate, dict):
        add(blockers, "decision_gate_missing", "$.decision_gate")
    else:
        if decision_gate.get("id") != DECISION_GATE_ID:
            add(blockers, "decision_gate_id_mismatch", "$.decision_gate.id")
        if decision_gate.get("status") != "blocked/planning":
            add(blockers, "decision_gate_status_mismatch", "$.decision_gate.status")
        if decision_gate.get("current_decision") != REQUIRED_DECISION_GATE_CURRENT_DECISION:
            add(blockers, "decision_gate_current_decision_mismatch", "$.decision_gate.current_decision")
        if decision_gate.get("scope") != REQUIRED_DECISION_GATE_SCOPE:
            add(blockers, "decision_gate_scope_mismatch", "$.decision_gate.scope")
        allowed_now = string_list(decision_gate.get("allowed_now"))
        if allowed_now is None:
            add(blockers, "decision_gate_allowed_now_not_string_list", "$.decision_gate.allowed_now")
        elif set(allowed_now) != REQUIRED_DECISION_GATE_ALLOWED_NOW:
            add(
                blockers,
                "decision_gate_allowed_now_mismatch",
                "$.decision_gate.allowed_now",
                expected=sorted(REQUIRED_DECISION_GATE_ALLOWED_NOW),
                observed=sorted(allowed_now),
            )
        forbidden_now = string_list(decision_gate.get("forbidden_now"))
        if forbidden_now is None:
            add(blockers, "decision_gate_forbidden_now_not_string_list", "$.decision_gate.forbidden_now")
        elif set(forbidden_now) != REQUIRED_DECISION_GATE_FORBIDDEN_NOW:
            add(
                blockers,
                "decision_gate_forbidden_now_mismatch",
                "$.decision_gate.forbidden_now",
                expected=sorted(REQUIRED_DECISION_GATE_FORBIDDEN_NOW),
                observed=sorted(forbidden_now),
            )
    if decisions.get("public_header_allowed") is not False:
        add(blockers, "public_header_allowed_not_false", "$.public_header_allowed")
    if decisions.get("public_header") != "include/obelisk/ObeliskApi.h":
        add(blockers, "public_header_path_mismatch", "$.public_header")
    for key in ("public_header_symbols_now", "public_capability_bits_now", "public_callback_abi_now"):
        if decisions.get(key) != []:
            add(blockers, f"{key}_not_empty", f"$.{key}")

    intake = decisions.get("approved_runtime_evidence_intake")
    if not isinstance(intake, dict):
        add(blockers, "approved_runtime_evidence_intake_missing", "$.approved_runtime_evidence_intake")
    else:
        if intake.get("id") != REQUIRED_INTAKE_ID:
            add(blockers, "approved_runtime_evidence_intake_id_mismatch", "$.approved_runtime_evidence_intake.id")
        if intake.get("status") != "external_manifest_required":
            add(blockers, "approved_runtime_evidence_intake_status_mismatch", "$.approved_runtime_evidence_intake.status")
        if intake.get("resolved_input") != REQUIRED_RESOLVED_INPUT:
            add(blockers, "approved_runtime_evidence_intake_resolved_input_mismatch", "$.approved_runtime_evidence_intake.resolved_input")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
            if intake.get(key) is not False:
                add(blockers, f"approved_runtime_evidence_intake_{key}_not_false", f"$.approved_runtime_evidence_intake.{key}")

    redaction_intake = decisions.get("identifier_redaction_evidence_intake")
    if not isinstance(redaction_intake, dict):
        add(blockers, "identifier_redaction_evidence_intake_missing", "$.identifier_redaction_evidence_intake")
    else:
        if redaction_intake.get("id") != REQUIRED_IDENTIFIER_REDACTION_INTAKE_ID:
            add(blockers, "identifier_redaction_evidence_intake_id_mismatch", "$.identifier_redaction_evidence_intake.id")
        if redaction_intake.get("status") != "external_manifest_required":
            add(blockers, "identifier_redaction_evidence_intake_status_mismatch", "$.identifier_redaction_evidence_intake.status")
        if redaction_intake.get("resolved_input") != REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT:
            add(blockers, "identifier_redaction_evidence_intake_resolved_input_mismatch", "$.identifier_redaction_evidence_intake.resolved_input")
        if redaction_intake.get("required_checker") != REQUIRED_IDENTIFIER_REDACTION_CHECKER:
            add(blockers, "identifier_redaction_evidence_intake_checker_mismatch", "$.identifier_redaction_evidence_intake.required_checker")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
            if redaction_intake.get(key) is not False:
                add(blockers, f"identifier_redaction_evidence_intake_{key}_not_false", f"$.identifier_redaction_evidence_intake.{key}")
    principal_policy_intake = decisions.get("principal_invalidation_policy_evidence_intake")
    if not isinstance(principal_policy_intake, dict):
        add(blockers, "principal_invalidation_policy_evidence_intake_missing", "$.principal_invalidation_policy_evidence_intake")
    else:
        if principal_policy_intake.get("id") != "principal_invalidation_policy_evidence":
            add(blockers, "principal_invalidation_policy_evidence_intake_id_mismatch", "$.principal_invalidation_policy_evidence_intake.id")
        if principal_policy_intake.get("status") != "repo_candidate_policy_required":
            add(blockers, "principal_invalidation_policy_evidence_intake_status_mismatch", "$.principal_invalidation_policy_evidence_intake.status")
        if principal_policy_intake.get("resolved_input") != PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT:
            add(blockers, "principal_invalidation_policy_evidence_intake_resolved_input_mismatch", "$.principal_invalidation_policy_evidence_intake.resolved_input")
        if principal_policy_intake.get("required_checker") != REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER:
            add(blockers, "principal_invalidation_policy_evidence_intake_checker_mismatch", "$.principal_invalidation_policy_evidence_intake.required_checker")
        if principal_policy_intake.get("default_manifest") != str(DEFAULT_PRINCIPAL_INVALIDATION_POLICY):
            add(blockers, "principal_invalidation_policy_evidence_intake_default_manifest_mismatch", "$.principal_invalidation_policy_evidence_intake.default_manifest")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed", "principal_invalidation_ready"):
            if principal_policy_intake.get(key) is not False:
                add(blockers, f"principal_invalidation_policy_evidence_intake_{key}_not_false", f"$.principal_invalidation_policy_evidence_intake.{key}")

    public_abi_preflight_intake = decisions.get("public_abi_preflight_candidate_intake")
    if not isinstance(public_abi_preflight_intake, dict):
        add(blockers, "public_abi_preflight_candidate_intake_missing", "$.public_abi_preflight_candidate_intake")
    else:
        if public_abi_preflight_intake.get("id") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_INTAKE_ID:
            add(blockers, "public_abi_preflight_candidate_intake_id_mismatch", "$.public_abi_preflight_candidate_intake.id")
        if public_abi_preflight_intake.get("status") != "repo_candidate_preflight_required":
            add(blockers, "public_abi_preflight_candidate_intake_status_mismatch", "$.public_abi_preflight_candidate_intake.status")
        if public_abi_preflight_intake.get("resolved_input") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT:
            add(
                blockers,
                "public_abi_preflight_candidate_intake_resolved_input_mismatch",
                "$.public_abi_preflight_candidate_intake.resolved_input",
            )
        if public_abi_preflight_intake.get("required_checker") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER:
            add(
                blockers,
                "public_abi_preflight_candidate_intake_checker_mismatch",
                "$.public_abi_preflight_candidate_intake.required_checker",
            )
        if public_abi_preflight_intake.get("default_manifest") != str(DEFAULT_PUBLIC_ABI_PREFLIGHT_CANDIDATE):
            add(
                blockers,
                "public_abi_preflight_candidate_intake_default_manifest_mismatch",
                "$.public_abi_preflight_candidate_intake.default_manifest",
            )
        if public_abi_preflight_intake.get("non_claim") != REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_NON_CLAIM:
            add(
                blockers,
                "public_abi_preflight_candidate_intake_non_claim_mismatch",
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
                    f"public_abi_preflight_candidate_intake_{key}_not_false",
                    f"$.public_abi_preflight_candidate_intake.{key}",
                )

    not_sufficient = decisions.get("approved_runtime_evidence_not_sufficient")
    if not isinstance(not_sufficient, dict):
        add(blockers, "approved_runtime_evidence_not_sufficient_missing", "$.approved_runtime_evidence_not_sufficient")
    else:
        if not_sufficient.get("decision") != "Approved runtime principal lifecycle evidence would be necessary evidence, but it is not sufficient to publish obelisk.player_identity.v1.":
            add(blockers, "approved_runtime_evidence_not_sufficient_decision_mismatch", "$.approved_runtime_evidence_not_sufficient.decision")
        require_string_list_contains(
            not_sufficient,
            "why",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_NOT_SUFFICIENT_WHY,
            blockers,
            "approved_runtime_evidence_not_sufficient_why_missing",
            "$.approved_runtime_evidence_not_sufficient.why",
        )
        require_string_list_contains(
            not_sufficient,
            "minimum_additional_gates",
            REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES,
            blockers,
            "approved_runtime_evidence_not_sufficient_minimum_gates_missing",
            "$.approved_runtime_evidence_not_sufficient.minimum_additional_gates",
        )

    forbidden = decisions.get("forbidden_public_contract")
    if not isinstance(forbidden, list) or not REQUIRED_FORBIDDEN.issubset(set(forbidden)):
        add(blockers, "forbidden_public_contract_missing_required", "$.forbidden_public_contract")

    non_claims = decisions.get("non_claims")
    if not isinstance(non_claims, list) or not all(isinstance(item, str) for item in non_claims):
        add(blockers, "non_claims_not_string_list", "$.non_claims")
    else:
        missing_non_claims = missing_required(non_claims, REQUIRED_NON_CLAIMS)
        if missing_non_claims:
            add(blockers, "non_claims_missing_required", "$.non_claims", missing=missing_non_claims)

    validate_required_before_public_header(decisions, blockers)
    validate_candidate_only_pod_abi(decisions.get("proposed_public_pod_abi_candidate"), blockers)

    blockers_list = decisions.get("promotion_blockers")
    observed_ids = {
        item.get("id")
        for item in blockers_list
        if isinstance(blockers_list, list) and isinstance(item, dict)
    }
    if observed_ids != REQUIRED_BLOCKERS:
        add(
            blockers,
            "promotion_blockers_mismatch",
            "$.promotion_blockers",
            expected=sorted(REQUIRED_BLOCKERS),
            observed=sorted(str(item) for item in observed_ids),
        )
    if isinstance(blockers_list, list):
        for index, item in enumerate(blockers_list):
            if isinstance(item, dict) and item.get("status") == "resolved":
                add(blockers, "promotion_blocker_resolved_without_public_gate", f"$.promotion_blockers[{index}]")

    required_tests = decisions.get("required_tests_before_public_header")
    observed_test_ids: set[Any] = set()
    if isinstance(required_tests, list):
        observed_test_ids = {
            item.get("id")
            for item in required_tests
            if isinstance(item, dict)
        }
    else:
        add(blockers, "required_tests_before_public_header_not_list", "$.required_tests_before_public_header")
    if observed_test_ids != REQUIRED_TESTS_BEFORE_PUBLIC_HEADER:
        add(
            blockers,
            "required_tests_before_public_header_mismatch",
            "$.required_tests_before_public_header",
            expected=sorted(REQUIRED_TESTS_BEFORE_PUBLIC_HEADER),
            observed=sorted(str(item) for item in observed_test_ids),
        )
    if isinstance(required_tests, list):
        for index, item in enumerate(required_tests):
            if not isinstance(item, dict):
                add(blockers, "required_tests_before_public_header_entry_not_object", f"$.required_tests_before_public_header[{index}]")
                continue
            test_id = item.get("id")
            required_coverage = REQUIRED_TEST_COVERAGE_BY_ID.get(test_id)
            if required_coverage is not None:
                require_string_list_contains(
                    item,
                    "required_coverage",
                    required_coverage,
                    blockers,
                    "required_test_coverage_missing",
                    f"$.required_tests_before_public_header[{index}].required_coverage",
                )
            if test_id in CONTRACT_REVIEW_INPUT_ONLY_TESTS:
                if item.get("status") != "covered":
                    add(blockers, "contract_review_input_test_not_covered", f"$.required_tests_before_public_header[{index}].status", test_id=test_id)
                if item.get("coverage_status") != "contract_review_input_only":
                    add(blockers, "contract_review_input_test_status_mismatch", f"$.required_tests_before_public_header[{index}].coverage_status", test_id=test_id)
                covered_by = set(item.get("covered_by", [])) if isinstance(item.get("covered_by"), list) else set()
                missing_coverage = CONTRACT_REVIEW_INPUT_ONLY_TESTS[test_id] - covered_by
                if missing_coverage:
                    add(
                        blockers,
                        "contract_review_input_test_coverage_missing",
                        f"$.required_tests_before_public_header[{index}].covered_by",
                        test_id=test_id,
                        missing=sorted(missing_coverage),
                    )
                for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
                    if item.get(key) is not False:
                        add(blockers, f"contract_review_input_test_{key}_not_false", f"$.required_tests_before_public_header[{index}].{key}", test_id=test_id)
            elif item.get("status") != "missing":
                add(blockers, "pre_header_test_marked_ready_without_public_gate", f"$.required_tests_before_public_header[{index}].status", test_id=test_id)


def build_report(
    decisions: dict[str, Any],
    runtime_report: dict[str, Any],
    redaction_report: dict[str, Any],
    private_candidate_contract: dict[str, Any],
    public_header_report: dict[str, Any],
    blockers: list[dict[str, Any]],
    check_mode: str,
    principal_policy_report: dict[str, Any] | None = None,
    public_abi_preflight_report: dict[str, Any] | None = None,
    owner_token_sdk_consumer_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    principal_policy_report = principal_policy_report or {}
    public_abi_preflight_report = public_abi_preflight_report or {}
    owner_token_sdk_consumer_report = owner_token_sdk_consumer_report or {}
    runtime_ready = (
        runtime_report.get("approved_runtime_evidence_present") is True
        and runtime_report.get("runtime_evidence_ready") is True
        and runtime_report.get("promotion_ready") is False
        and runtime_report.get("public_sdk_ready") is False
        and runtime_report.get("runtime_ready") is False
    )
    if not runtime_ready:
        add(blockers, "approved_runtime_evidence_missing_or_not_ready", "$.approved_runtime_evidence")
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_player_identity_public_contract_promotion", "$.promotion_blockers")

    evidence_blockers = [
        blocker
        for blocker in blockers
        if not blocker["reason"].endswith("_blocked_until_player_identity_public_contract_promotion")
    ]
    accepted_for_contract_review = not evidence_blockers
    resolved_inputs = []
    if accepted_for_contract_review:
        resolved_inputs.append(REQUIRED_RESOLVED_INPUT)
        if redaction_report.get("accepted_for_contract_review") is True:
            resolved_inputs.append(REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT)
        if principal_policy_report.get("accepted_for_policy_review") is True:
            resolved_inputs.append(PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT)
        if public_abi_preflight_report.get("accepted_for_candidate_review") is True:
            resolved_inputs.append(REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT)
    runtime_input_resolved = REQUIRED_RESOLVED_INPUT in resolved_inputs
    return {
        "schema": REPORT_SCHEMA,
        "surface": decisions.get("surface"),
        "mode": check_mode,
        "ready": accepted_for_contract_review and check_mode == "consume",
        "ready_scope": "contract_review_input_only",
        "accepted_for_contract_review": accepted_for_contract_review,
        "resolved_inputs": resolved_inputs,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_header_symbols_now": decisions.get("public_header_symbols_now"),
        "public_capability_bits_now": decisions.get("public_capability_bits_now"),
        "public_callback_abi_now": decisions.get("public_callback_abi_now"),
        "public_header_scan": public_header_report,
        "private_candidate_contract": {
            "path": decisions.get("private_candidate_contract"),
            "schema": private_candidate_contract.get("schema"),
            "artifact_status": private_candidate_contract.get("artifact_status"),
            "visibility": private_candidate_contract.get("visibility"),
            "candidate_only": private_candidate_contract.get("candidate_only") is True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
        },
        "remaining_blockers": [
            blocker["id"]
            for blocker in decisions.get("promotion_blockers", [])
            if isinstance(blocker, dict)
            and not (runtime_input_resolved and blocker.get("id") == REQUIRED_RESOLVED_INPUT)
        ],
        "next_blocker": (
            NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE
            if accepted_for_contract_review
            else "player_identity_public_contract_gate_not_accepted"
        ),
        "required_tests_before_public_header": {
            "covered_for_contract_review_only": sorted(CONTRACT_REVIEW_INPUT_ONLY_TESTS),
            "remaining_missing": [
                item["id"]
                for item in decisions.get("required_tests_before_public_header", [])
                if isinstance(item, dict) and item.get("status") == "missing"
            ],
        },
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "approved_runtime_evidence": {
            "approved_runtime_evidence_present": runtime_report.get("approved_runtime_evidence_present") is True,
            "runtime_evidence_ready": runtime_report.get("runtime_evidence_ready") is True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
        },
        "identifier_redaction_evidence": {
            "provided": redaction_report.get("provided") is True,
            "accepted_for_contract_review": redaction_report.get("accepted_for_contract_review") is True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
        },
        "principal_invalidation_policy": {
            "provided": principal_policy_report.get("provided") is True,
            "accepted_for_policy_review": principal_policy_report.get("accepted_for_policy_review") is True,
            "resolved_input": principal_policy_report.get("resolved_input"),
            "candidate_only": principal_policy_report.get("candidate_only") is True,
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_header_allowed": False,
            "principal_invalidation_ready": False,
        },
        "public_abi_preflight_candidate": {
            "provided": public_abi_preflight_report.get("provided") is True,
            "status": public_abi_preflight_report.get("status"),
            "candidate_only": public_abi_preflight_report.get("candidate_only") is True,
            "accepted_for_candidate_review": public_abi_preflight_report.get("accepted_for_candidate_review") is True,
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
            "contract_review_inputs_accepted": public_abi_preflight_report.get(
                "contract_review_inputs_accepted",
                {},
            ),
            "required_before_public_abi": public_abi_preflight_report.get("required_before_public_abi", []),
            "required_capability_policy": public_abi_preflight_report.get("required_capability_policy", []),
            "required_owner_token_lifecycle": public_abi_preflight_report.get(
                "required_owner_token_lifecycle",
                [],
            ),
            "sdk_consumer_contract": public_abi_preflight_report.get("sdk_consumer_contract", {}),
            "does_not_resolve": public_abi_preflight_report.get("does_not_resolve", []),
            "blockers": public_abi_preflight_report.get("blockers", []),
            "non_claims": public_abi_preflight_report.get("non_claims", []),
        },
        "owner_token_sdk_consumer_contract": owner_token_sdk_consumer_report,
        "non_claims": [
            "approved runtime evidence intake does not add public header symbols, capability bits, callbacks, lookup, mutation, return override, or v1 SDK readiness",
            NON_PROMOTIONAL_EVIDENCE_DENIAL,
            "identifier-redaction evidence intake does not resolve the full privacy blocker, add public header symbols, or make player identity promotion-ready",
            "principal invalidation policy intake is candidate-only and does not resolve the full lifetime/generation/scope blocker or prove runtime lifecycle ordering",
            "public ABI preflight candidate intake is candidate-only and does not resolve public ABI layout, SDK consumer tests, lifecycle cleanup, or v1 completion",
        ],
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    blockers: list[dict[str, Any]] = []
    decisions = safe_load_json(args.decisions, "decisions", blockers) or {}
    if decisions:
        validate_decisions(decisions, blockers)
    private_candidate_contract = load_private_candidate_contract(decisions, args.private_candidate_contract, blockers)
    public_header_report = validate_public_header(decisions, args.public_header, blockers)
    runtime_report = approved_runtime_report(args.approved_runtime_evidence, blockers)
    redaction_report = identifier_redaction_report(args.identifier_redaction_evidence, blockers)
    principal_policy_report = principal_invalidation_policy_report(args.principal_invalidation_policy, blockers)
    public_abi_preflight_report = public_abi_preflight_candidate_report(
        args.public_abi_preflight_candidate,
        args.public_header,
        blockers,
    )
    owner_token_sdk_consumer_report = owner_token_sdk_consumer_contract_report(
        args.owner_token_sdk_consumer_contract,
        args.public_abi_preflight_candidate,
        args.public_header,
        blockers,
        public_abi_preflight_report,
    )
    report = build_report(
        decisions,
        runtime_report,
        redaction_report,
        private_candidate_contract,
        public_header_report,
        blockers,
        check_mode,
        principal_policy_report,
        public_abi_preflight_report,
        owner_token_sdk_consumer_report,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
