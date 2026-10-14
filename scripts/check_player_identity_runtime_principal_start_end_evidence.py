#!/usr/bin/env python3
"""Validate narrowed runtime evidence for player-principal start/end only.

This checker is intentionally not the approved three-role lifecycle evidence gate. It
accepts only enough copied runtime observer evidence to prove principal candidate
creation and matched invalidation, while keeping rejected-start/CheckJoin proof,
public identity, public SDK readiness, and runtime readiness blocked.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SCHEMA = "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
READY_LOG_COPY_SCHEMA = "obelisk.player-principal-lifecycle-ready-log-copy.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
EXPECTED_PROCESS_EVENT_ADDRESS = "0x1d34e20"
MODULE = "player_principal_lifecycle"
RESOLVED_INPUT = "runtime.lifecycle_start_end_evidence"
UNRESOLVED_REJECTED_START_INPUT = "runtime.lifecycle_rejected_start_evidence"
STRICT_APPROVED_BUNDLE = "approved_runtime_principal_lifecycle_evidence_bundle"
CURRENT_ROUTE_BLOCKER = "approved_runtime_evidence_missing"
MISSING_EXACT_CHECK_JOIN_BLOCKER = "missing_exact_CheckJoinInProgress_1_0_session_start_rejected"
STRICT_APPROVED_RUNTIME_UNRESOLVED_INPUTS = [
    UNRESOLVED_REJECTED_START_INPUT,
    STRICT_APPROVED_BUNDLE,
]
STRICT_APPROVED_RUNTIME_BLOCKERS = [MISSING_EXACT_CHECK_JOIN_BLOCKER]

REQUIRED_START_CASE = {
    "target": "ShooterGameMode.HandleNewPlayer",
    "role": "session_start",
    "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
    "copied_bool_values": ["1", "1"],
    "principal_action": "candidate_created",
    "apply_status": "session_start_created",
    "correlation_status": "not_applicable",
}
REQUIRED_END_CASE = {
    "target": "ShooterGameMode.OnLogout",
    "role": "session_end",
    "copied_bool_fields": [],
    "copied_bool_values": [],
    "principal_action": "candidate_invalidated",
    "apply_status": "session_end_invalidated",
    "correlation_status": "matched",
}
REQUIRED_CASES = (REQUIRED_START_CASE, REQUIRED_END_CASE)
READY_LOG_REQUIRED_ROLES_PRESENT = ["session_start", "session_end"]
READY_LOG_REQUIRED_MISSING_ROLES = ["session_start_rejected"]
READY_LOG_REQUIRED_START_EVENT = {
    "role": "session_start",
    "target": "ShooterGameMode.HandleNewPlayer",
    "post_original": "true",
    "copied_bool_fields": "bIsFromLogin,ReturnValue",
    "copied_bool_values": "1,1",
    "redacted_count": "3",
    "redacted_fields": "NewPlayer,PlayerData,PlayerCharacter",
    "principal_action": "candidate_created",
    "apply_status": "session_start_created",
    "correlation_status": "not_applicable",
    "principal_id_logged": "false",
    "principal_generation_logged": "false",
    "delivery_claim": "none",
    "status_proof_ok": True,
    "approved_copy_shape_ok": True,
    "inside_fresh_window": True,
}
READY_LOG_REQUIRED_END_EVENT = {
    "role": "session_end",
    "target": "ShooterGameMode.OnLogout",
    "post_original": "true",
    "copied_bool_fields": "",
    "copied_bool_values": "",
    "redacted_count": "1",
    "redacted_fields": "Exiting",
    "principal_action": "candidate_invalidated",
    "apply_status": "session_end_invalidated",
    "correlation_status": "matched",
    "principal_id_logged": "false",
    "principal_generation_logged": "false",
    "delivery_claim": "none",
    "status_proof_ok": True,
    "approved_copy_shape_ok": True,
    "inside_fresh_window": True,
}
FALSE_FLAGS = {
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "approved_runtime_principal_lifecycle_evidence": False,
    "approved_runtime_principal_lifecycle_evidence_present": False,
    "approved_runtime_principal_lifecycle_evidence_ready": False,
    "approved_runtime_principal_lifecycle_evidence_bundle_accepted": False,
    "approved_runtime_principal_lifecycle_evidence_bundle_ready": False,
    "accepted_as_approved_runtime_principal_lifecycle_evidence": False,
    "accepted_for_approved_runtime_principal_lifecycle_evidence": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_approved_runtime_principal_lifecycle_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_as_sdk_progress": False,
    "counts_as_sdk_or_p0_progress": False,
    "counts_as_p0_progress": False,
    "counts_as_v1_completion": False,
    "counts_toward_complete_sdk_claim": False,
    "counts_toward_p0_dependency_chain": False,
    "counts_toward_p0_dependency_chain_claim": False,
    "counts_toward_public_readiness": False,
    "counts_toward_public_sdk": False,
    "counts_toward_runtime": False,
    "counts_toward_runtime_readiness": False,
    "counts_toward_sdk": False,
    "counts_toward_v1_completion": False,
    "runtime_ready": False,
    "runtime_readiness": False,
    "runtime_readiness_ready": False,
    "runtime_evidence_present": False,
    "runtime_evidence_ready": False,
    "public_ready": False,
    "public_readiness": False,
    "public_readiness_ready": False,
    "public_sdk_ready": False,
    "public_header_allowed": False,
    "public_abi_ready": False,
    "public_api_ready": False,
    "public_contract_allowed": False,
    "public_header_ready": False,
    "lookup_ready": False,
    "permissions_ready": False,
    "commands_ready": False,
    "sdk_ready": False,
    "sdk_evidence_ready": False,
    "complete_sdk_allowed": False,
    "complete_sdk_ready": False,
    "module_ready": False,
    "module_sdk_ready": False,
    "promotion_ready": False,
    "route_ready": False,
    "v1_completion_ready": False,
    "v1_complete": False,
    "v1_completion": False,
    "v1_release_ready": False,
    "exact_check_join_in_progress_1_0_triplet_satisfied": False,
    "exact_check_join_in_progress_1_0_triplet_ready": False,
    "exact_check_join_in_progress_1_0_triplet_replaced": False,
    "exact_copied_runtime_triplet_satisfied": False,
    "exact_copied_runtime_triplet_ready": False,
    "start_end_only_replaces_exact_check_join_in_progress_1_0_triplet": False,
    "principal_start_end_replaces_exact_check_join_in_progress_1_0_triplet": False,
    "stable_claim_allowed": False,
    "stable_sdk_ready": False,
    "publication_authorized": False,
}
ZERO_PROGRESS_FIELDS = {
    "complete_sdk_progress": 0,
    "complete_sdk_claim_progress_contribution": 0,
    "complete_sdk_progress_contribution": 0,
    "sdk_progress": 0,
    "sdk_progress_contribution": 0,
    "public_sdk_progress_contribution": 0,
    "runtime_progress_contribution": 0,
    "v1_completion_contribution": 0,
    "p0_progress": 0,
    "p0_dependency_chain_progress": 0,
    "p0_dependency_chain_claim_progress_contribution": 0,
    "p0_dependency_chain_progress_contribution": 0,
    "complete_sdk_progress_ratio": "0/12",
    "complete_sdk_claim_progress_ratio": "0/12",
    "p0_dependency_chain_progress_ratio": "0/4",
}
SOURCE_FALSE_ALIAS_KEYS = frozenset(
    set(FALSE_FLAGS)
    | {
        "approved_bundle_accepted",
        "approved_runtime_principal_lifecycle_evidence_bundle",
        "approved_runtime_evidence_accepted",
        "bundle_accepted",
        "complete_sdk_claim_allowed",
        "complete_sdk_claim_ready",
        "counts_as_public_sdk",
        "counts_toward_complete_sdk_claim_now",
        "counts_toward_p0_dependency_chain_claim_now",
        "evidence_bundle_accepted",
        "p0_dependency_chain_ready",
        "p0_dependency_ready",
        "p0_ready",
        "public_route_ready",
        "ready",
        "ready_to_copy",
        "ready_for_public_contract_review",
        "runtime_v1_ready",
        "stable_sdk_claim_allowed",
        "stable_sdk_ready",
        "v1_release_ready",
    }
)
STRICT_TRIPLET_CONTEXT_FRAGMENTS = (
    "exact_copied_runtime_triplet",
    "exact_checkjoininprogress_1_0",
    "exact_check_join_in_progress_1_0",
    "checkjoininprogress_1_0_triplet",
    "check_join_in_progress_1_0_triplet",
)
STRICT_TRIPLET_POSITIVE_KEYS = frozenset(
    (
        "accepted",
        "approved",
        "complete",
        "present",
        "ready",
        "replaced",
        "satisfied",
        "counts_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "counts_toward_runtime",
    )
)
OBSERVED_EVENT_CASE_KEYS = frozenset(
    (
        "sequence",
        "target",
        "role",
        "copied_bool_fields",
        "copied_bool_values",
        "principal_action",
        "apply_status",
        "correlation_status",
    )
)
EXPECTED_DETAIL_VALUES = {
    "ShooterGameMode.HandleNewPlayer": {
        "role": {"session_start"},
        "post_original": {"true"},
        "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
        "copied_bool_values": {"1,1"},
        "redacted_count": {3},
        "redacted_fields": {"NewPlayer,PlayerData,PlayerCharacter"},
        "principal_action": {"candidate_created"},
        "apply_status": {"session_start_created"},
        "correlation_status": {"not_applicable"},
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
    "ShooterGameMode.OnLogout": {
        "role": {"session_end"},
        "post_original": {"true"},
        "copied_bool_fields": {""},
        "copied_bool_values": {""},
        "redacted_count": {1},
        "redacted_fields": {"Exiting"},
        "principal_action": {"candidate_invalidated"},
        "apply_status": {"session_end_invalidated"},
        "correlation_status": {"matched"},
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
}
RAW_IDENTITY_KEY_RE = re.compile(
    r"^(?:steam(?:id|[_-]?id)?|eos(?:[_-]?id)?|unique[_-]?net[_-]?id|"
    r"player[_-]?(?:id|name|data|text)|ip(?:v4|v6)?(?:[_-]?address)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|resourcehandle|"
    r"gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?|player[_-]?text)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"principal[_-]?(?:id|generation)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|"
    r"hashed[_-]?(?:private|identity|identifier|player))$",
    re.IGNORECASE,
)
ALLOWED_PRIVACY_STATUS_KEYS = frozenset(
    (
        "principal_id_logged",
        "principal_generation_logged",
        "redacted_fields",
        "redacted_count",
    )
)
APPROVED_RUNTIME_OVERCLAIM_FRAGMENTS = (
    "approved_runtime_evidence",
    "approved_runtime_principal_lifecycle_evidence",
    "approved_bundle_accepted",
    "bundle_accepted",
    "evidence_bundle_accepted",
    "runtime_evidence_present",
    "runtime_evidence_ready",
    "counts_as_runtime_evidence",
    "count_as_runtime_evidence",
    "exact_copied_runtime_triplet",
    "exact_checkjoininprogress_1_0",
    "exact_check_join_in_progress_1_0",
    "checkjoininprogress_1_0_triplet",
    "check_join_in_progress_1_0_triplet",
)
SOURCE_ZERO_ALIAS_KEYS = frozenset(
    set(ZERO_PROGRESS_FIELDS)
    | {
        "claim_credit",
        "claim_credits",
        "claim_progress_contribution",
        "complete_sdk_credit",
        "complete_sdk_credits",
        "complete_sdk_claim_credit",
        "complete_sdk_claim_credits",
        "p0_credit",
        "p0_credits",
        "p0_dependency_chain_credit",
        "p0_dependency_chain_credits",
        "progress",
        "sdk_credit",
        "sdk_credits",
        "sdk_completion_credit",
        "sdk_completion_credits",
        "v1_completion_credit",
        "v1_completion_credits",
    }
)


def normalized_source_alias_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


NORMALIZED_SOURCE_FALSE_ALIAS_KEYS = frozenset(
    normalized_source_alias_key(key) for key in SOURCE_FALSE_ALIAS_KEYS
)
NORMALIZED_SOURCE_ZERO_ALIAS_KEYS = frozenset(
    normalized_source_alias_key(key) for key in SOURCE_ZERO_ALIAS_KEYS
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-summary",
        required=True,
        type=Path,
        help=(
            "Copied/offline analyze_runtime_observer_log.py JSON summary, or a "
            "non-ready player-principal lifecycle ready-log dry-run JSON report."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def add(blockers: list[str], reason: str) -> None:
    if reason not in blockers:
        blockers.append(reason)


def is_false_like(value: Any) -> bool:
    if value is False or value is None:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    if isinstance(value, str):
        return value.strip().lower() in {"", "0", "0/12", "0/4", "false", "none", "no"}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    return False


def alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if is_false_like(value):
        return False
    if isinstance(value, str):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    return False


LIFECYCLE_ROLE_ALIAS_MARKER_TOKENS = frozenset(
    (
        "alias",
        "aliases",
        "claim",
        "claims",
        "credit",
        "credits",
        "equivalent",
        "equivalents",
        "proxy",
        "proxies",
        "replace",
        "replaced",
        "replacement",
        "replacements",
        "replaces",
        "satisfied",
        "satisfies",
        "satisfy",
        "substitute",
        "substitutes",
    )
)
LIFECYCLE_ROLE_ALIAS_COUNT_MARKER_TOKENS = frozenset(("counting", "counts"))
LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS = frozenset(
    ("anchor", "anchors", "event", "events", "lifecycle", "role", "roles", "triplet")
)
LIFECYCLE_ROLE_ALIAS_ROLE_VALUES = frozenset(
    ("session_start", "session_start_rejected", "session_end")
)


def source_alias_tokens(value: object) -> set[str]:
    return {token for token in normalized_source_alias_key(value).split("_") if token}


def lifecycle_role_alias_key_claims_role(value: object) -> bool:
    normalized = normalized_source_alias_key(value)
    return any(role in normalized for role in LIFECYCLE_ROLE_ALIAS_ROLE_VALUES)


def lifecycle_role_alias_value_claims_role(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_source_alias_key(value)
        return any(role in normalized for role in LIFECYCLE_ROLE_ALIAS_ROLE_VALUES)
    if isinstance(value, dict):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value.values())
    if isinstance(value, list):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value)
    return False


def lifecycle_role_alias_value_has_material(value: Any) -> bool:
    if is_false_like(value):
        return False
    if isinstance(value, str):
        normalized = normalized_source_alias_key(value)
        return normalized not in {
            "blocked",
            "candidate",
            "context_only",
            "missing",
            "non_evidence",
            "not_applicable",
            "rejected",
            "required",
            "requires",
        }
    if isinstance(value, dict):
        return any(lifecycle_role_alias_value_has_material(child) for child in value.values())
    if isinstance(value, list):
        return any(lifecycle_role_alias_value_has_material(child) for child in value)
    return True


def lifecycle_role_alias_claim_is_forbidden(key: object, value: Any) -> bool:
    tokens = source_alias_tokens(key)
    count_as_claim = bool(
        tokens & LIFECYCLE_ROLE_ALIAS_COUNT_MARKER_TOKENS
        and "as" in tokens
        and lifecycle_role_alias_value_has_material(value)
        and (
            tokens & LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS
            or lifecycle_role_alias_key_claims_role(key)
            or lifecycle_role_alias_value_claims_role(value)
        )
    )
    if count_as_claim:
        return True
    if not tokens & LIFECYCLE_ROLE_ALIAS_MARKER_TOKENS:
        return False
    if lifecycle_role_alias_value_claims_role(value):
        return True
    if lifecycle_role_alias_key_claims_role(key) and lifecycle_role_alias_value_has_material(value):
        return True
    return bool(
        tokens & LIFECYCLE_ROLE_ALIAS_DOMAIN_TOKENS
        and lifecycle_role_alias_value_has_material(value)
    )


def zero_value_is_zero(value: Any) -> bool:
    if value is None or value is False:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if isinstance(value, str):
        return value.strip().lower() in {"", "0", "0/12", "0/4", "false", "none"}
    return False


def raw_identity_value_present(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "redacted"}
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def privacy_status_false(value: Any) -> bool:
    if value == "false" or value is False:
        return True
    if isinstance(value, list):
        return value == ["false"]
    return False


def is_source_false_alias_key(key: str) -> bool:
    normalized = normalized_source_alias_key(key)
    if normalized in NORMALIZED_SOURCE_FALSE_ALIAS_KEYS:
        return True
    false_fragments = (
        "counts_as_approved_runtime_evidence",
        "count_as_approved_runtime_evidence",
        "counts_as_runtime_evidence",
        "count_as_runtime_evidence",
        "counts_as_sdk_evidence",
        "count_as_sdk_evidence",
        "counts_as_sdk_progress",
        "count_as_sdk_progress",
        "counts_as_p0_progress",
        "count_as_p0_progress",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_sdk",
        "counts_toward_v1_completion",
        "sdk_or_p0_progress",
    )
    return (
        normalized.endswith("_ready")
        or normalized.endswith("_claim_allowed")
        or any(fragment in normalized for fragment in false_fragments)
    )


def is_source_zero_alias_key(key: str) -> bool:
    normalized = normalized_source_alias_key(key)
    if normalized in NORMALIZED_SOURCE_ZERO_ALIAS_KEYS:
        return True
    if normalized.endswith("_in_progress"):
        return False
    return (
        normalized.endswith("_progress")
        or normalized.endswith("_progress_ratio")
        or normalized.endswith("_progress_contribution")
        or normalized.endswith("_credit")
        or normalized.endswith("_credits")
    )


def is_strict_triplet_overclaim_path(path: str, key: str) -> bool:
    normalized_path = normalized_source_alias_key(path)
    normalized_key = normalized_source_alias_key(key)
    return (
        normalized_key in STRICT_TRIPLET_POSITIVE_KEYS
        and any(fragment in normalized_path for fragment in STRICT_TRIPLET_CONTEXT_FRAGMENTS)
    )


def collect_source_overclaims(
    value: Any,
    *,
    path: str = "$",
) -> tuple[list[str], list[str]]:
    readiness_flags: list[str] = []
    progress_flags: list[str] = []

    def walk(current: Any, current_path: str) -> None:
        if isinstance(current, dict):
            for key, nested in current.items():
                if not isinstance(key, str):
                    continue
                next_path = f"{current_path}.{key}"
                if (
                    is_source_false_alias_key(key)
                    or is_strict_triplet_overclaim_path(next_path, key)
                ) and alias_value_is_positive(nested):
                    readiness_flags.append(next_path)
                if is_source_zero_alias_key(key) and not zero_value_is_zero(nested):
                    progress_flags.append(next_path)
                if isinstance(nested, (dict, list)):
                    walk(nested, next_path)
        elif isinstance(current, list):
            for index, nested in enumerate(current):
                if isinstance(nested, (dict, list)):
                    walk(nested, f"{current_path}[{index}]")

    walk(value, path)
    return sorted(set(readiness_flags)), sorted(set(progress_flags))


def collect_lifecycle_role_alias_paths(value: Any, *, path: str = "$") -> list[str]:
    paths: list[str] = []

    def walk(current: Any, current_path: str) -> None:
        if isinstance(current, dict):
            for key, nested in current.items():
                if not isinstance(key, str):
                    continue
                next_path = f"{current_path}.{key}"
                if lifecycle_role_alias_claim_is_forbidden(key, nested):
                    paths.append(next_path)
                if isinstance(nested, (dict, list)):
                    walk(nested, next_path)
        elif isinstance(current, list):
            for index, nested in enumerate(current):
                if isinstance(nested, (dict, list)):
                    walk(nested, f"{current_path}[{index}]")

    walk(value, path)
    return sorted(set(paths))


def collect_raw_identity_paths(value: Any, *, path: str = "$") -> list[str]:
    paths: list[str] = []

    def walk(current: Any, current_path: str) -> None:
        if isinstance(current, dict):
            for key, nested in current.items():
                if not isinstance(key, str):
                    continue
                next_path = f"{current_path}.{key}"
                if key in {"principal_id_logged", "principal_generation_logged"}:
                    if not privacy_status_false(nested):
                        paths.append(next_path)
                elif RAW_IDENTITY_KEY_RE.fullmatch(key) and key not in ALLOWED_PRIVACY_STATUS_KEYS:
                    if raw_identity_value_present(nested):
                        paths.append(next_path)
                if isinstance(nested, (dict, list)):
                    walk(nested, next_path)
        elif isinstance(current, list):
            for index, nested in enumerate(current):
                if isinstance(nested, (dict, list)):
                    walk(nested, f"{current_path}[{index}]")

    walk(value, path)
    return sorted(set(paths))


def overclaim_attempts_approved_runtime_evidence(readiness_flags: list[str]) -> bool:
    return any(
        any(
            fragment in normalized_source_alias_key(flag)
            for fragment in APPROVED_RUNTIME_OVERCLAIM_FRAGMENTS
        )
        for flag in readiness_flags
    )


def reject_source_overclaims(payload: dict[str, Any], blockers: list[str]) -> tuple[list[str], list[str]]:
    readiness_flags, progress_flags = collect_source_overclaims(payload)
    role_alias_paths = collect_lifecycle_role_alias_paths(payload)
    for flag in readiness_flags:
        add(blockers, f"source_alias_overclaim:{flag}")
    for flag in progress_flags:
        add(blockers, f"source_progress_overclaim:{flag}")
    for path in role_alias_paths:
        add(blockers, f"source_lifecycle_role_alias:{path}")
    if overclaim_attempts_approved_runtime_evidence(readiness_flags):
        add(blockers, MISSING_EXACT_CHECK_JOIN_BLOCKER)
    if role_alias_paths:
        add(blockers, MISSING_EXACT_CHECK_JOIN_BLOCKER)
    return readiness_flags, progress_flags


def reject_raw_identity_fields(payload: dict[str, Any], blockers: list[str]) -> list[str]:
    raw_identity_paths = collect_raw_identity_paths(payload)
    for path in raw_identity_paths:
        add(blockers, f"source_raw_player_identity_or_text:{path}")
    return raw_identity_paths


def event_matches(event: Any, expected: dict[str, Any]) -> bool:
    if not isinstance(event, dict):
        return False
    for key, expected_value in expected.items():
        if event.get(key) != expected_value:
            return False
    return True


def add_status_field_blockers(
    blockers: list[str],
    event: dict[str, Any],
    expected: dict[str, Any],
    prefix: str,
) -> None:
    for key in ("apply_status", "correlation_status"):
        if key not in event:
            add(blockers, f"{prefix}_{key}_missing")
        elif event.get(key) != expected[key]:
            add(blockers, f"{prefix}_{key}_mismatch")


def validate_observed_start_end_events(
    events: list[Any],
    blockers: list[str],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    starts: list[dict[str, Any]] = []
    ends: list[dict[str, Any]] = []
    previous_sequence = 0

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            add(blockers, "observed_event_case_invalid")
            continue

        unexpected_keys = set(event) - OBSERVED_EVENT_CASE_KEYS
        if unexpected_keys:
            add(blockers, "observed_event_case_keys_unexpected")

        sequence = event.get("sequence")
        if not isinstance(sequence, int):
            add(blockers, "observed_event_case_sequence_missing_or_invalid")
        elif sequence <= previous_sequence:
            add(blockers, "observed_event_case_sequence_not_strictly_increasing")
        if isinstance(sequence, int):
            previous_sequence = sequence

        target = event.get("target")
        role = event.get("role")
        if target == REQUIRED_START_CASE["target"] and role == REQUIRED_START_CASE["role"]:
            add_status_field_blockers(blockers, event, REQUIRED_START_CASE, "session_start")
        if target == REQUIRED_END_CASE["target"] and role == REQUIRED_END_CASE["role"]:
            add_status_field_blockers(blockers, event, REQUIRED_END_CASE, "session_end")

        if event_matches(event, REQUIRED_START_CASE):
            starts.append(event)
        elif event_matches(event, REQUIRED_END_CASE):
            ends.append(event)
        else:
            add(blockers, "observed_event_case_not_exact_start_end_shape")
            if role == "session_start_rejected" or target == "ShooterGameMode.CheckJoinInProgress":
                add(blockers, "session_start_rejected_unexpected_in_start_end_only_input")

    if len(events) != 2:
        add(blockers, "observed_event_cases_not_exactly_start_end_only")
    if len(starts) != 1:
        add(blockers, "session_start_case_missing" if not starts else "session_start_case_ambiguous")
    if len(ends) != 1:
        add(blockers, "session_end_case_missing_or_not_after_start" if not ends else "session_end_case_ambiguous")
    if len(starts) != 1 or len(ends) != 1:
        return starts[0] if starts else None, ends[0] if ends else None

    start = starts[0]
    end = ends[0]
    start_sequence = start.get("sequence")
    end_sequence = end.get("sequence")
    if not isinstance(start_sequence, int) or not isinstance(end_sequence, int):
        add(blockers, "start_end_sequence_order_unavailable")
    elif end_sequence <= start_sequence:
        add(blockers, "session_end_case_missing_or_not_after_start")

    start_index = events.index(start)
    end_index = events.index(end)
    if end_index <= start_index:
        add(blockers, "session_end_case_missing_or_not_after_start")

    return start, end


def ready_log_event_matches(event: Any, expected: dict[str, Any]) -> bool:
    if not isinstance(event, dict):
        return False
    for key, expected_value in expected.items():
        if event.get(key) != expected_value:
            return False
    return True


def ready_log_context(payload: dict[str, Any]) -> dict[str, Any]:
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    exact_triplet = (
        analysis.get("exact_copied_runtime_triplet")
        if isinstance(analysis.get("exact_copied_runtime_triplet"), dict)
        else {}
    )
    return {
        "schema": payload.get("schema"),
        "status": payload.get("status"),
        "ready": payload.get("ready"),
        "ready_to_copy": payload.get("ready_to_copy"),
        "copy_readiness": payload.get("copy_readiness"),
        "current_route_blocker": payload.get("current_route_blocker"),
        "execute_requested": payload.get("execute_requested"),
        "copied": payload.get("copied"),
        "roles_present": payload.get("roles_present"),
        "missing_roles": payload.get("missing_roles"),
        "analysis": {
            "roles_present": analysis.get("roles_present"),
            "missing_roles": analysis.get("missing_roles"),
            "observer_enabled": analysis.get("observer_enabled"),
            "binary_sha256_match": analysis.get("binary_sha256_match"),
            "ready_to_copy": analysis.get("ready_to_copy"),
            "copy_readiness": analysis.get("copy_readiness"),
            "accepted_lifecycle_event_count": analysis.get("accepted_lifecycle_event_count"),
            "partial_accepted_lifecycle_role_set": analysis.get("partial_accepted_lifecycle_role_set"),
            "exact_copied_runtime_triplet": {
                "accepted": exact_triplet.get("accepted"),
                "status": exact_triplet.get("status"),
                "blockers": exact_triplet.get("blockers"),
                "start_end_only_detected": exact_triplet.get("start_end_only_detected"),
                "required_roles": exact_triplet.get("required_roles"),
                "accepted_roles": exact_triplet.get("accepted_roles"),
            },
        },
    }


def function_detail_values(module: dict[str, Any], function_name: str, key: str) -> list[Any]:
    functions = module.get("functions")
    if not isinstance(functions, dict):
        return []
    function = functions.get(function_name)
    if not isinstance(function, dict):
        return []
    details = function.get("details")
    if not isinstance(details, dict):
        return []
    values = details.get(key)
    return values if isinstance(values, list) else []


def validate_function_details(module: dict[str, Any], blockers: list[str]) -> None:
    for function_name, expected_details in EXPECTED_DETAIL_VALUES.items():
        for key, expected_values in expected_details.items():
            observed_values = function_detail_values(module, function_name, key)
            if set(observed_values) != expected_values:
                add(blockers, f"{function_name}_{key}_mismatch")


def validate_summary(summary: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    blockers: list[str] = []
    if summary.get("schema") != SUMMARY_SCHEMA:
        add(blockers, "source_summary_schema_mismatch")
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "source_summary_evidence_missing")
    else:
        if evidence.get("server_paths_allowed") is not False:
            add(blockers, "source_summary_not_copied_or_offline")
        if evidence.get("kind") != "runtime-observer-log":
            add(blockers, "source_summary_kind_mismatch")
        sources = evidence.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            add(blockers, "source_summary_sources_not_exactly_one")

    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        add(blockers, "runtime_posture_missing")
    else:
        expected_runtime = {
            "loaded_native_ld_preload": True,
            "process_event_candidate_count": 1,
            "process_event_candidates": [{"index": 0, "address": EXPECTED_PROCESS_EVENT_ADDRESS}],
            "process_event_address": EXPECTED_PROCESS_EVENT_ADDRESS,
            "process_event_hook_installed": True,
            "process_event_hook_patch_size": 18,
            "broad_process_event_trace_lines": 0,
            "reflection_scanner_disabled": True,
            "plugins_disabled": True,
        }
        for key, expected in expected_runtime.items():
            if runtime.get(key) != expected:
                add(blockers, f"runtime_posture_{key}_mismatch")

    modules = summary.get("modules")
    module = None
    if not isinstance(modules, dict) or MODULE not in modules:
        add(blockers, "player_principal_lifecycle_module_missing")
    else:
        module = modules[MODULE]
        if not isinstance(module, dict):
            add(blockers, "player_principal_lifecycle_module_invalid")
            module = None

    matched_start: dict[str, Any] | None = None
    matched_end: dict[str, Any] | None = None
    check_join_diagnostic_count = 0
    if module is not None:
        if module.get("observer_enabled") is not True:
            add(blockers, "observer_not_enabled")
        if module.get("observer_gate_count") != 1:
            add(blockers, "observer_gate_count_mismatch")
        if module.get("gate_sha256") != [EXPECTED_BINARY_SHA256]:
            add(blockers, "observer_gate_sha256_mismatch")
        validate_function_details(module, blockers)
        events = module.get("observed_event_cases")
        if not isinstance(events, list):
            add(blockers, "observed_event_cases_missing")
            events = []
        matched_start, matched_end = validate_observed_start_end_events(events, blockers)
        diagnostic_targets = module.get("diagnostic_candidate_target_counts")
        if isinstance(diagnostic_targets, dict):
            value = diagnostic_targets.get("ShooterGameMode.CheckJoinInProgress", 0)
            check_join_diagnostic_count = value if isinstance(value, int) else 0

    source_raw_identity_paths = reject_raw_identity_fields(summary, blockers)
    source_overclaimed_flags, source_overclaimed_progress = reject_source_overclaims(summary, blockers)
    return blockers, {
        "session_start": matched_start,
        "session_end": matched_end,
        "check_join_diagnostic_count": check_join_diagnostic_count,
        "source_kind": "runtime_observer_log_summary",
        "source_raw_player_identity_or_text_fields": source_raw_identity_paths,
        "source_overclaimed_readiness_or_authorization_flags": source_overclaimed_flags,
        "source_overclaimed_progress_flags": source_overclaimed_progress,
    }


def validate_ready_log_copy_report(payload: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    blockers: list[str] = []
    if payload.get("schema") != READY_LOG_COPY_SCHEMA:
        add(blockers, "ready_log_copy_schema_mismatch")
    if payload.get("status") != "blocked":
        add(blockers, "ready_log_copy_status_not_blocked_dry_run")
    if payload.get("ready") is not False:
        add(blockers, "ready_log_copy_ready_not_false")
    if payload.get("ready_to_copy") is not False:
        add(blockers, "ready_log_copy_ready_to_copy_not_false")
    if payload.get("execute_requested") is not False:
        add(blockers, "ready_log_copy_execute_requested_not_false")
    if payload.get("copied") is not False:
        add(blockers, "ready_log_copy_copied_not_false")
    if payload.get("current_route_blocker") != CURRENT_ROUTE_BLOCKER:
        add(blockers, "ready_log_copy_current_route_blocker_mismatch")

    for key in (
        "approved_runtime_evidence",
        "approved_runtime_evidence_present",
        "approved_runtime_evidence_ready",
        "counts_as_approved_runtime_evidence",
        "runtime_ready",
        "public_sdk_ready",
        "v1_completion_ready",
        "stable_claim_allowed",
    ):
        if payload.get(key) is not False:
            add(blockers, f"ready_log_copy_{key}_not_false")

    if payload.get("roles_present") != READY_LOG_REQUIRED_ROLES_PRESENT:
        add(blockers, "ready_log_copy_roles_present_not_start_end_only")
    if payload.get("missing_roles") != READY_LOG_REQUIRED_MISSING_ROLES:
        add(blockers, "ready_log_copy_missing_roles_not_explicit_rejected_start")

    analysis = payload.get("analysis")
    if not isinstance(analysis, dict):
        add(blockers, "ready_log_copy_analysis_missing")
        analysis = {}
    else:
        if analysis.get("observer_enabled") is not True:
            add(blockers, "ready_log_copy_observer_not_enabled")
        if analysis.get("binary_sha256_match") is not True:
            add(blockers, "ready_log_copy_binary_sha256_mismatch")
        if analysis.get("roles_present") != READY_LOG_REQUIRED_ROLES_PRESENT:
            add(blockers, "ready_log_copy_analysis_roles_present_not_start_end_only")
        if analysis.get("missing_roles") != READY_LOG_REQUIRED_MISSING_ROLES:
            add(blockers, "ready_log_copy_analysis_missing_roles_not_explicit_rejected_start")
        if analysis.get("ready_to_copy") is not False:
            add(blockers, "ready_log_copy_analysis_ready_to_copy_not_false")
        if analysis.get("approved_runtime_evidence") is not False:
            add(blockers, "ready_log_copy_analysis_approved_runtime_evidence_not_false")
        if analysis.get("counts_as_approved_runtime_evidence") is not False:
            add(blockers, "ready_log_copy_analysis_counts_as_approved_runtime_evidence_not_false")
        if analysis.get("partial_accepted_lifecycle_role_set") is not True:
            add(blockers, "ready_log_copy_partial_accepted_role_set_not_true")
        if analysis.get("accepted_lifecycle_event_count") != 2:
            add(blockers, "ready_log_copy_analysis_accepted_lifecycle_event_count_not_two")

    exact_triplet = analysis.get("exact_copied_runtime_triplet")
    if not isinstance(exact_triplet, dict):
        add(blockers, "ready_log_copy_exact_triplet_missing")
        exact_triplet = {}
    else:
        if exact_triplet.get("accepted") is not False:
            add(blockers, "ready_log_copy_exact_triplet_accepted_not_false")
        if exact_triplet.get("start_end_only_detected") is not True:
            add(blockers, "ready_log_copy_exact_triplet_start_end_only_not_true")
        exact_blockers = exact_triplet.get("blockers")
        if not (
            isinstance(exact_blockers, list)
            and "exact_copied_runtime_triplet_missing_session_start_rejected"
            in exact_blockers
        ):
            add(blockers, "ready_log_copy_exact_triplet_missing_rejected_start_blocker_absent")

    accepted_role_events = analysis.get("accepted_role_events")
    if not isinstance(accepted_role_events, dict):
        add(blockers, "ready_log_copy_accepted_role_events_missing")
        accepted_role_events = {}
    matched_start = accepted_role_events.get("session_start")
    matched_end = accepted_role_events.get("session_end")
    if isinstance(matched_start, dict):
        add_status_field_blockers(
            blockers,
            matched_start,
            READY_LOG_REQUIRED_START_EVENT,
            "ready_log_copy_session_start",
        )
    if isinstance(matched_end, dict):
        add_status_field_blockers(
            blockers,
            matched_end,
            READY_LOG_REQUIRED_END_EVENT,
            "ready_log_copy_session_end",
        )
    if not ready_log_event_matches(matched_start, READY_LOG_REQUIRED_START_EVENT):
        add(blockers, "ready_log_copy_session_start_case_missing")
        matched_start = None
    if not ready_log_event_matches(matched_end, READY_LOG_REQUIRED_END_EVENT):
        add(blockers, "ready_log_copy_session_end_case_missing")
        matched_end = None
    if "session_start_rejected" in accepted_role_events:
        add(blockers, "ready_log_copy_session_start_rejected_unexpectedly_accepted")

    if isinstance(matched_start, dict) and isinstance(matched_end, dict):
        start_sequence = matched_start.get("sequence")
        end_sequence = matched_end.get("sequence")
        if isinstance(start_sequence, int) and isinstance(end_sequence, int):
            if end_sequence <= start_sequence:
                add(blockers, "ready_log_copy_start_end_sequence_order_mismatch")
        else:
            add(blockers, "ready_log_copy_start_end_sequence_order_unavailable")
        start_line = matched_start.get("line_number")
        end_line = matched_end.get("line_number")
        if isinstance(start_line, int) and isinstance(end_line, int):
            if end_line <= start_line:
                add(blockers, "ready_log_copy_start_end_line_order_mismatch")
        else:
            add(blockers, "ready_log_copy_start_end_line_order_unavailable")

    source_raw_identity_paths = reject_raw_identity_fields(payload, blockers)
    source_overclaimed_flags, source_overclaimed_progress = reject_source_overclaims(payload, blockers)
    return blockers, {
        "session_start": matched_start,
        "session_end": matched_end,
        "check_join_diagnostic_count": 0,
        "source_kind": "player_principal_lifecycle_ready_log_copy_dry_run",
        "source_ready_log_copy": ready_log_context(payload),
        "explicit_missing_rejected_start": True,
        "source_raw_player_identity_or_text_fields": source_raw_identity_paths,
        "source_overclaimed_readiness_or_authorization_flags": source_overclaimed_flags,
        "source_overclaimed_progress_flags": source_overclaimed_progress,
    }


def validate_source(source: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    schema = source.get("schema")
    if schema == READY_LOG_COPY_SCHEMA:
        return validate_ready_log_copy_report(source)
    return validate_summary(source)


def build_report(source_summary: Path, summary: dict[str, Any], blockers: list[str], matches: dict[str, Any]) -> dict[str, Any]:
    ready = not blockers
    source_evidence = summary.get("evidence") if isinstance(summary.get("evidence"), dict) else {}
    source_kind = matches.get("source_kind", "runtime_observer_log_summary")
    return {
        "schema": SCHEMA,
        "source_summary_path": str(source_summary),
        "source_schema": summary.get("schema"),
        "source_kind": source_kind,
        "status": "accepted_for_contract_review" if ready else "blocked",
        "ready": ready,
        "ready_scope": "principal_start_end_runtime_evidence_only",
        "accepted_for_contract_review": ready,
        "principal_start_end_runtime_evidence_present": ready,
        "principal_start_end_runtime_evidence_ready": ready,
        "resolved_inputs": [RESOLVED_INPUT] if ready else [],
        "remaining_runtime_inputs": STRICT_APPROVED_RUNTIME_UNRESOLVED_INPUTS
        if ready
        else [RESOLVED_INPUT, *STRICT_APPROVED_RUNTIME_UNRESOLVED_INPUTS],
        "does_not_resolve": STRICT_APPROVED_RUNTIME_UNRESOLVED_INPUTS,
        "current_route_blocker": CURRENT_ROUTE_BLOCKER,
        "remaining_route_blockers": [CURRENT_ROUTE_BLOCKER],
        "strict_route_blocked": True,
        "next_review_blocker": CURRENT_ROUTE_BLOCKER
        if ready
        else "principal_start_end_runtime_evidence_missing",
        "strict_approved_runtime_evidence_blockers": STRICT_APPROVED_RUNTIME_BLOCKERS,
        "approved_runtime_evidence_blockers": STRICT_APPROVED_RUNTIME_BLOCKERS,
        "contract_review_input": RESOLVED_INPUT if ready else None,
        "contract_review_input_counts_as_approved_runtime_evidence": False,
        "observed_runtime_cases": [
            "observer_enable",
            "session_start_anchor",
            "session_end_anchor",
        ] if ready else [],
        "unresolved_runtime_cases": [
            "session_start_rejected_anchor",
            "exact_CheckJoinInProgress_1_0_session_start_rejected",
        ],
        "exact_check_join_in_progress_1_0_triplet": {
            "required": True,
            "satisfied": False,
            "ready": False,
            "replaced_by_principal_start_end_only": False,
            "blocker": MISSING_EXACT_CHECK_JOIN_BLOCKER,
        },
        "diagnostic_coverage": {
            "check_join_in_progress_diagnostic_count": matches.get("check_join_diagnostic_count", 0),
            "diagnostic_candidates_count_as_evidence": False,
            "diagnostic_candidates_count_as_exact_check_join_in_progress_1_0_triplet": False,
            "session_start_rejected_explicitly_missing": bool(
                matches.get("explicit_missing_rejected_start")
            ),
        },
        "matched_events": {
            "session_start": matches.get("session_start"),
            "session_end": matches.get("session_end"),
        },
        "source_summary": {
            "schema": summary.get("schema"),
            "evidence": source_evidence,
            "runtime": summary.get("runtime"),
        },
        "source_ready_log_copy": matches.get("source_ready_log_copy"),
        "source_overclaimed_readiness_or_authorization_flags": matches.get(
            "source_overclaimed_readiness_or_authorization_flags", []
        ),
        "source_overclaimed_progress_flags": matches.get(
            "source_overclaimed_progress_flags", []
        ),
        "source_raw_player_identity_or_text_fields": matches.get(
            "source_raw_player_identity_or_text_fields", []
        ),
        **FALSE_FLAGS,
        **ZERO_PROGRESS_FIELDS,
        "blockers": blockers,
        "non_claims": [
            "principal start/end runtime evidence is not the approved three-role lifecycle evidence bundle",
            "CheckJoinInProgress rejected-start/no-op semantics remain unresolved unless the strict triplet gate passes",
            "ready-log dry-run material is contract-review context only when accepted here and never counts as approved runtime evidence",
            "this checker does not promote public identity, lookup, public ABI/header, permissions/admin, commands, runtime readiness, SDK readiness, P0 progress, stable claims, or publication",
        ],
    }


def main() -> int:
    args = parse_args()
    summary = load_json(args.source_summary)
    blockers, matches = validate_source(summary)
    report = build_report(args.source_summary, summary, blockers, matches)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(blocker, file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
