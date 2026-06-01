#!/usr/bin/env python3
"""Validate approved runtime principal lifecycle observer evidence.

This checker consumes a copied/sanitized `analyze_runtime_observer_log.py` summary plus
fail-closed consumer boundary cases. Acceptance means only that runtime lifecycle evidence
is reviewable for the player-principal lane; it does not promote public identity,
permissions, commands, lookup, mutation, or SDK readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import protected_paths
import analyze_runtime_observer_log as runtime_observer_analyzer
from artifact_identity import canonical_json_bytes, complete_artifact_identity
from snapshot_evidence_pack import reject_protected_input_path, reject_symlink_component


SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
REPORT_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
SUMMARY_SCHEMA = "obelisk.runtime-observer-log-summary.v1"
EXPECTED_BINARY_SHA256 = "7e7ded49e0c658e74199801d79630bd33da407d3e468e039837bf61a9de7c520"
MODULE = "player_principal_lifecycle"
NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
SERVER_ROOT = Path("/servidor/ark")
APPROVED_OFFLINE_WORKSPACE_ROOTS = (Path("/servidor/ark/workspace-offline"),)
REQUIRED_TOP_LEVEL_KEYS = frozenset(
    (
        "schema",
        "artifact_status",
        "readiness_classification",
        "approved_runtime_evidence_present",
        "runtime_evidence_ready",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "output_artifact_identity",
        "approval",
        "operational_window",
        "source_summary",
        "consumer_boundary_cases",
        "privacy_boundary",
        "promotion_gate",
        "non_claims",
    )
)
WINDOW_CHECK_SCHEMA = "obelisk.players-identity-runtime-principal-lifecycle-window-manifest-check.v1"
EXPECTED_COPIED_LOG_PARENT = "live-validation-logs"
EXPECTED_COPIED_LOG_PATH_STATUS = "approved_offline_workspace"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_APPROVAL_KEYS = frozenset(
    (
        "runtime_evidence_reviewed",
        "reviewed_by",
        "review_note",
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
        "discord_authorized_by_this_manifest",
    )
)
ALLOWED_OPERATIONAL_WINDOW_KEYS = frozenset(
    (
        "schema",
        "ready",
        "operational_window_manifest_ready",
        "run_id",
        "obelisk_commit",
        "target",
        "copied_log",
        "posture",
        "rollback",
        "claims",
        "user_policy",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
    )
)
ALLOWED_OPERATIONAL_WINDOW_COPIED_LOG_KEYS = frozenset(("path", "path_status", "sha256"))
ALLOWED_OPERATIONAL_WINDOW_POSTURE_KEYS = frozenset(
    (
        "pre_check",
        "post_check",
        "pre_posture",
        "post_posture",
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
    )
)
ALLOWED_OPERATIONAL_WINDOW_ROLLBACK_KEYS = frozenset(
    ("completed", "observer_env_survived", "observer_marker_survived")
)
ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS = frozenset(("delivery_claim", "principal_claim"))
ALLOWED_CONSUMER_CASE_KEYS = frozenset(
    (
        "case",
        "result",
        "provenance",
        "runtime_observed",
        "lookup_allowed",
        "mutation_allowed",
        "return_override_allowed",
        "public_sdk_surface",
    )
)
ALLOWED_PROMOTION_GATE_KEYS = frozenset(
    ("runtime_evidence_ready", "ready", "promotion_ready", "public_sdk_ready", "runtime_ready")
)
REQUIRED_CONSUMER_CASES = frozenset(("stale_after_logout", "malformed_or_unsupported_evidence"))
REQUIRED_OBSERVED_EVENT_CASES = (
    {
        "target": "ShooterGameMode.HandleNewPlayer",
        "role": "session_start",
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["1", "1"],
        "principal_action": "candidate_created",
    },
    {
        "target": "ShooterGameMode.HandleNewPlayer",
        "role": "session_start_rejected",
        "copied_bool_fields": ["bIsFromLogin", "ReturnValue"],
        "copied_bool_values": ["0", "1"],
        "principal_action": "none",
    },
    {
        "target": "ShooterGameMode.OnLogout",
        "role": "session_end",
        "copied_bool_fields": [],
        "copied_bool_values": [],
        "principal_action": "candidate_invalidated",
    },
)
REQUIRED_OBSERVED_EVENT_CASE_SET = frozenset(
    tuple((key, tuple(value) if isinstance(value, list) else value) for key, value in case.items())
    for case in REQUIRED_OBSERVED_EVENT_CASES
)
OBSERVED_EVENT_CASE_KEYS = frozenset(
    ("sequence", "target", "role", "copied_bool_fields", "copied_bool_values", "principal_action")
)
EXPECTED_DETAIL_VALUES = {
    "observer_gate": {
        "target_set": {"players-lifecycle-anchor-candidates"},
        "limit": {10},
        "dispatch_limit": {0},
        "delivery_claim": {"none"},
        "principal_claim": {"none"},
    },
    "ShooterGameMode.HandleNewPlayer": {
        "role": {"session_start", "session_start_rejected"},
        "post_original": {"true"},
        "copied_bool_fields": {"bIsFromLogin,ReturnValue"},
        "copied_bool_values": {"1,1", "0,1"},
        "redacted_count": {3},
        "redacted_fields": {"NewPlayer,PlayerData,PlayerCharacter"},
        "principal_action": {"candidate_created", "none"},
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
        "principal_id_logged": {"false"},
        "principal_generation_logged": {"false"},
        "delivery_claim": {"none"},
    },
}
EXPECTED_DETAIL_KEYS = {
    function: frozenset(details)
    for function, details in EXPECTED_DETAIL_VALUES.items()
}
PRIVACY_BOUNDARY_KEYS = frozenset(
    (
        "copied_opaque_principal_only",
        "redacted_runtime_observer",
        "player_identifiers_logged",
        "lookup_allowed",
        "resource_handle_allowed",
        "mutation_allowed",
        "return_override_allowed",
    )
)
REQUIRED_NON_CLAIMS = frozenset(
    (
        "approved runtime observer evidence only",
        "does not promote public player identity, lookup, permissions, commands, moderation, admin authority, mutation, return override, ResourceHandle, or v1 SDK readiness",
        "does not expose Steam/EOS ids, player names, IPs, tribe ids, UE pointers, FNames, GObjects, raw params, or persistent lookup keys",
        "does not authorize server operations, Discord updates, GitHub publication, tags, or release claims",
    )
)
FORBIDDEN_KEY_RE = re.compile(
    r"(?:steam|eos|unique[_-]?net|player[_-]?(?:id|name|data)|ip(?:v4|v6)?|tribe[_-]?id|"
    r"platform[_-]?ids?|transfer[_-]?ids?|private[_-]?(?:identifier|user[_-]?data)|"
    r"chat[_-]?(?:text|message|payload)|command[_-]?(?:text|message|payload)|"
    r"permission[_-]?state|admin[_-]?state|"
    r"resourcehandle|gobjects?|fnames?|fname[_-]?(?:index|id)|gobject[_-]?(?:index|id)|"
    r"uobject|ue[_-]?pointer|raw[_-]?(?:params?|payload|pointer|trace|buffers?)|"
    r"object[_-]?(?:address|name|coordinates?|coords)|"
    r"(?:identity|identifier|player|steam|eos)[_-]?hash|hashed[_-]?(?:private|identity|identifier|player))",
    re.IGNORECASE,
)
POSITIVE_CAPABILITY_CLAIM_RE = re.compile(
    r"(?:public[_ -]?(?:sdk|player[_ -]?identity)|"
    r"player[_ -]?identity[_ -]?(?:promotion|ready|readiness)|"
    r"(?:sdk|runtime|lookup|permissions?|admin|command(?:s|[_ -]?(?:reply|response|routing|support))?|"
    r"plugin[_ -]?delivery|mutation|return[_ -]?override|resourcehandle)[_ -]?"
    r"(?:ready|readiness|enabled|allowed|supported|promoted|delivered)|"
    r"command[_ -]?(?:reply|response|routing|support)|"
    r"(?:lookup|mutation|return[_ -]?override)[_ -]?allowed)",
    re.IGNORECASE,
)
NEGATIVE_CLAIM_CONTEXT_RE = re.compile(
    r"\b(?:does\s+not|do\s+not|not|no|never|without|blocked|forbidden|reject(?:ed|s)?|fail[-_ ]closed)\b",
    re.IGNORECASE,
)
ALLOWED_FORBIDDEN_KEY_PATHS = (
    "$.schema",
    "$.privacy_boundary.copied_opaque_principal_only",
    "$.privacy_boundary.redacted_runtime_observer",
    "$.privacy_boundary.player_identifiers_logged",
    "$.privacy_boundary.lookup_allowed",
    "$.privacy_boundary.resource_handle_allowed",
    "$.privacy_boundary.mutation_allowed",
    "$.privacy_boundary.return_override_allowed",
    "$.source_summary.modules.player_principal_lifecycle",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
ALLOWED_FORBIDDEN_LEAF_PATHS = (
    "$.schema",
    "$.operational_window.schema",
    "$.output_artifact_identity.artifact_kind",
    "$.output_artifact_identity.capture_id",
    "$.output_artifact_identity.evidence_pack_id",
    "$.operational_window.run_id",
    "$.operational_window.copied_log.path",
    "$.operational_window.posture.observer_exclusivity",
    "$.operational_window.posture.single_module_summary",
    "$.source_summary.evidence.sources[0].path",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.HandleNewPlayer.details.principal_id_logged",
    "$.source_summary.modules.player_principal_lifecycle.functions.ShooterGameMode.OnLogout.details.principal_id_logged",
)
ALLOWED_FORBIDDEN_KEY_NAMES = frozenset(
    (
        "player_principal_lifecycle",
        "principal_action",
        "principal_claim",
        "principal_generation_logged",
        "principal_id_logged",
    )
)
NEGATIVE_CONTEXT_TOKENS = (
    "blocker",
    "non_claim",
    "privacy_boundary",
    "redacted",
)


@dataclass
class Validation:
    blockers: list[dict[str, Any]]
    observed_runtime_cases: list[str]
    consumer_cases: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Approved runtime lifecycle evidence manifest.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON report.")
    parser.add_argument("--promote", action="store_true", help="Fail closed for public promotion checks.")
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


def load_json(path: Path) -> dict[str, Any]:
    reject_symlink_component(path, "manifest")
    path = reject_protected_input_path(path, "manifest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"{path}: top-level JSON must be an object")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_output_artifact_sha256(payload: dict[str, Any], identity: dict[str, str]) -> str:
    identity_without_hash = {
        "artifact_kind": identity["artifact_kind"],
        "capture_id": identity["capture_id"],
        "evidence_pack_id": identity["evidence_pack_id"],
    }
    manifest_without_identity = {
        key: value
        for key, value in payload.items()
        if key != "output_artifact_identity"
    }
    material = {
        "artifact_identity": identity_without_hash,
        "report": manifest_without_identity,
    }
    return hashlib.sha256(canonical_json_bytes(material)).hexdigest()


def validate_output_artifact_identity(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    identity, errors = complete_artifact_identity(
        payload,
        container_key="output_artifact_identity",
        expected_artifact_kind=SCHEMA,
    )
    if errors or identity is None:
        add(
            blockers,
            "output_artifact_identity_invalid",
            "$.output_artifact_identity",
            errors=errors,
        )
        return
    run_id = payload.get("operational_window", {}).get("run_id")
    if identity["capture_id"] != run_id:
        add(
            blockers,
            "output_artifact_identity_capture_id_mismatch",
            "$.output_artifact_identity.capture_id",
            expected=run_id,
            observed=identity["capture_id"],
        )
    expected_sha256 = expected_output_artifact_sha256(payload, identity)
    if identity["artifact_sha256"] != expected_sha256:
        add(
            blockers,
            "output_artifact_identity_hash_mismatch",
            "$.output_artifact_identity.artifact_sha256",
            expected=expected_sha256,
            observed=identity["artifact_sha256"],
        )


def source_path_is_copied_or_offline(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected


def source_path_is_approved_offline_workspace(path_text: Any) -> bool:
    if not isinstance(path_text, str) or not path_text:
        return False
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    return not status.protected and status.approved_offline_workspace


def validate_copied_source_file(source: dict[str, Any], label: str, blockers: list[dict[str, Any]]) -> None:
    path_text = source.get("path")
    expected_sha256 = source.get("sha256")
    if not isinstance(expected_sha256, str) or SHA256_RE.fullmatch(expected_sha256) is None:
        add(blockers, "source_summary_source_sha256_invalid", f"{label}.sha256")
        return
    if not isinstance(path_text, str) or not path_text:
        add(blockers, "source_summary_source_path_missing", f"{label}.path")
        return
    path = Path(path_text).expanduser()
    try:
        actual_sha256 = sha256_file(path)
    except FileNotFoundError:
        add(blockers, "source_summary_source_file_missing", f"{label}.path")
        return
    except OSError as exc:
        add(blockers, "source_summary_source_file_unreadable", f"{label}.path", error=str(exc))
        return
    if actual_sha256 != expected_sha256:
        add(
            blockers,
            "source_summary_source_sha256_mismatch",
            f"{label}.sha256",
            expected=expected_sha256,
            actual=actual_sha256,
        )


def expected_summary_from_copied_source(
    evidence: dict[str, Any],
    source: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    path_text = source.get("path")
    if not isinstance(path_text, str) or not path_text:
        return None
    status = protected_paths.protected_path_status(
        Path(path_text).expanduser(),
        protected_root=SERVER_ROOT,
        approved_roots=APPROVED_OFFLINE_WORKSPACE_ROOTS,
    )
    if status.protected or not status.approved_offline_workspace:
        return None
    try:
        text = status.resolved.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        add(
            blockers,
            "source_summary_source_file_unreadable",
            "$.source_summary.evidence.sources[0].path",
            error=str(exc),
        )
        return None

    lines = text.splitlines()
    summary = runtime_observer_analyzer.analyze_source_lines([lines])
    summary["evidence"] = {
        "kind": "runtime-observer-log",
        "obelisk_commit": evidence.get("obelisk_commit"),
        "sources": [
            {
                "path": str(status.resolved),
                "sha256": sha256_file(status.resolved),
                "line_count": len(lines),
            }
        ],
        "server_paths_allowed": False,
    }
    return summary


def validate_source_summary_matches_copied_log(summary: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    evidence = summary.get("evidence")
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(evidence, dict) or not isinstance(sources, list) or len(sources) != 1:
        return
    source = sources[0]
    if not isinstance(source, dict):
        return
    expected = expected_summary_from_copied_source(evidence, source, blockers)
    if expected is None:
        return
    if canonical_json_bytes(summary) != canonical_json_bytes(expected):
        add(
            blockers,
            "source_summary_not_derived_from_copied_log",
            "$.source_summary",
        )


def detail_values(functions: dict[str, Any], function: str, key: str) -> list[Any]:
    details = functions.get(function, {}).get("details", {})
    value = details.get(key, [])
    return value if isinstance(value, list) else []


def require_values(
    blockers: list[dict[str, Any]],
    functions: dict[str, Any],
    function: str,
    key: str,
    expected: set[Any],
) -> None:
    values = set(detail_values(functions, function, key))
    if not expected.issubset(values):
        add(
            blockers,
            "runtime_summary_detail_values_missing",
            f"$.source_summary.modules.{MODULE}.functions.{function}.details.{key}",
            expected=sorted(expected, key=str),
            observed=sorted(values, key=str),
        )
    extra_values = values - expected
    if extra_values:
        add(
            blockers,
            "runtime_summary_detail_values_unexpected",
            f"$.source_summary.modules.{MODULE}.functions.{function}.details.{key}",
            expected=sorted(expected, key=str),
            observed=sorted(values, key=str),
            unexpected=sorted(extra_values, key=str),
        )


def require_expected_detail_values(
    blockers: list[dict[str, Any]],
    functions: dict[str, Any],
    function: str,
) -> None:
    function_payload = functions.get(function)
    label = f"$.source_summary.modules.{MODULE}.functions.{function}"
    if not isinstance(function_payload, dict):
        add(blockers, "runtime_summary_function_missing", label)
        return
    details = function_payload.get("details")
    if not isinstance(details, dict):
        add(blockers, "runtime_summary_function_details_missing", f"{label}.details")
        return

    expected_keys = EXPECTED_DETAIL_KEYS[function]
    observed_keys = set(details)
    unexpected_keys = observed_keys - expected_keys
    if unexpected_keys:
        add(
            blockers,
            "runtime_summary_detail_keys_unexpected",
            f"{label}.details",
            unexpected=sorted(unexpected_keys),
        )
    for key, expected in EXPECTED_DETAIL_VALUES[function].items():
        require_values(blockers, functions, function, key, expected)


def case_without_sequence(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": case.get("target"),
        "role": case.get("role"),
        "copied_bool_fields": case.get("copied_bool_fields"),
        "copied_bool_values": case.get("copied_bool_values"),
        "principal_action": case.get("principal_action"),
    }


def freeze_case(case: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (key, tuple(value) if isinstance(value, list) else value)
        for key, value in case.items()
    )


def validate_observed_event_cases(module: dict[str, Any], blockers: list[dict[str, Any]]) -> list[str]:
    cases = module.get("observed_event_cases")
    label = f"$.source_summary.modules.{MODULE}.observed_event_cases"
    if not isinstance(cases, list):
        add(blockers, "runtime_summary_observed_event_cases_missing", label)
        return []

    observed_runtime_cases: list[str] = []
    previous_sequence = 0
    remaining_expected = [dict(case) for case in REQUIRED_OBSERVED_EVENT_CASES]
    case_labels = {
        "session_start": "session_start_anchor",
        "session_start_rejected": "session_start_rejected_anchor",
        "session_end": "session_end_anchor",
    }

    for index, case in enumerate(cases):
        case_label = f"{label}[{index}]"
        if not isinstance(case, dict):
            add(blockers, "runtime_summary_observed_event_case_invalid", case_label)
            continue
        unexpected_keys = set(case) - OBSERVED_EVENT_CASE_KEYS
        if unexpected_keys:
            add(
                blockers,
                "runtime_summary_observed_event_case_keys_unexpected",
                case_label,
                unexpected=sorted(unexpected_keys),
            )
        sequence = case.get("sequence")
        if not isinstance(sequence, int) or sequence <= previous_sequence:
            add(blockers, "runtime_summary_observed_event_case_sequence_invalid", f"{case_label}.sequence")
        if isinstance(sequence, int):
            previous_sequence = sequence
        compact_case = case_without_sequence(case)
        case_is_required_shape = freeze_case(compact_case) in REQUIRED_OBSERVED_EVENT_CASE_SET
        case_matches_remaining_required = compact_case in remaining_expected
        if case_is_required_shape and remaining_expected and compact_case != remaining_expected[0]:
            add(
                blockers,
                "runtime_summary_observed_event_case_order_mismatch",
                case_label,
                expected=remaining_expected[0],
                observed=compact_case,
            )
        if not case_is_required_shape or not case_matches_remaining_required:
            add(
                blockers,
                "runtime_summary_observed_event_case_unexpected",
                case_label,
                observed=compact_case,
            )
        if case_matches_remaining_required:
            remaining_expected.remove(compact_case)
            observed_runtime_cases.append(case_labels[str(compact_case["role"])])

    if remaining_expected:
        add(
            blockers,
            "runtime_summary_required_observed_event_cases_missing",
            label,
            missing=remaining_expected,
        )
    return observed_runtime_cases


def validate_runtime_summary(summary: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(summary, dict):
        add(blockers, "source_summary_missing", "$.source_summary")
        return []
    if summary.get("schema") != SUMMARY_SCHEMA:
        add(blockers, "source_summary_schema_mismatch", "$.source_summary.schema")
    if summary.get("review_scope") != "runtime_observer_evidence_summary":
        add(blockers, "source_summary_review_scope_mismatch", "$.source_summary.review_scope")
    evidence = summary.get("evidence")
    if not isinstance(evidence, dict):
        add(blockers, "source_summary_evidence_missing", "$.source_summary.evidence")
    else:
        if evidence.get("kind") != "runtime-observer-log":
            add(blockers, "source_summary_evidence_kind_mismatch", "$.source_summary.evidence.kind")
        if evidence.get("server_paths_allowed") is not False:
            add(blockers, "source_summary_server_paths_allowed", "$.source_summary.evidence.server_paths_allowed")
        if not evidence.get("obelisk_commit"):
            add(blockers, "source_summary_obelisk_commit_missing", "$.source_summary.evidence.obelisk_commit")
        sources = evidence.get("sources")
        if not isinstance(sources, list) or len(sources) != 1:
            add(blockers, "source_summary_sources_not_exactly_one", "$.source_summary.evidence.sources")
        else:
            for index, source in enumerate(sources):
                label = f"$.source_summary.evidence.sources[{index}]"
                if not isinstance(source, dict):
                    add(blockers, "source_summary_source_invalid", label)
                    continue
                if not source_path_is_copied_or_offline(source.get("path")):
                    add(blockers, "source_summary_source_path_not_copied_or_offline", f"{label}.path")
                elif not source_path_is_approved_offline_workspace(source.get("path")):
                    add(blockers, "source_summary_source_path_not_approved_offline_workspace", f"{label}.path")
                else:
                    validate_copied_source_file(source, label, blockers)
        validate_source_summary_matches_copied_log(summary, blockers)

    runtime = summary.get("runtime")
    if not isinstance(runtime, dict):
        add(blockers, "source_summary_runtime_missing", "$.source_summary.runtime")
    else:
        expected_runtime = {
            "loaded_native_ld_preload": True,
            "process_event_candidate_count": 1,
            "process_event_hook_installed": True,
            "process_event_hook_patch_size": 18,
            "reflection_scanner_disabled": True,
            "plugins_disabled": True,
        }
        for key, expected in expected_runtime.items():
            if runtime.get(key) != expected:
                add(blockers, "source_summary_runtime_posture_mismatch", f"$.source_summary.runtime.{key}", expected=expected)

    modules = summary.get("modules")
    if not isinstance(modules, dict) or MODULE not in modules:
        add(blockers, "player_principal_lifecycle_module_missing", "$.source_summary.modules")
        return []
    module_names = set(modules)
    if module_names != {MODULE}:
        add(
            blockers,
            "source_summary_unexpected_modules_present",
            "$.source_summary.modules",
            expected=[MODULE],
            observed=sorted(module_names),
        )
    module = modules[MODULE]
    if not isinstance(module, dict):
        add(blockers, "player_principal_lifecycle_module_invalid", f"$.source_summary.modules.{MODULE}")
        return []
    if module.get("gate_sha256") != [EXPECTED_BINARY_SHA256]:
        add(blockers, "runtime_summary_gate_sha256_mismatch", f"$.source_summary.modules.{MODULE}.gate_sha256")
    if module.get("observer_gate_count") != 1:
        add(
            blockers,
            "runtime_summary_observer_gate_count_mismatch",
            f"$.source_summary.modules.{MODULE}.observer_gate_count",
            expected=1,
            observed=module.get("observer_gate_count"),
        )
    if module.get("blockers") != ["runtime_observer_evidence_only"]:
        add(blockers, "runtime_summary_quality_blockers_present", f"$.source_summary.modules.{MODULE}.blockers")
    for key in (
        "malformed_observer_lines",
        "orphan_field_lines",
        "out_of_order_field_lines",
        "field_count_mismatches",
        "sequence_quality_violations",
        "event_before_gate_lines",
    ):
        if module.get(key) != 0:
            add(blockers, "runtime_summary_quality_counter_nonzero", f"$.source_summary.modules.{MODULE}.{key}")
    if module.get("redacted_detail_keys") != {}:
        add(blockers, "runtime_summary_unapproved_detail_keys", f"$.source_summary.modules.{MODULE}.redacted_detail_keys")
    if module.get("accepted_count") != len(REQUIRED_OBSERVED_EVENT_CASES):
        add(
            blockers,
            "runtime_summary_accepted_event_count_mismatch",
            f"$.source_summary.modules.{MODULE}.accepted_count",
            expected=len(REQUIRED_OBSERVED_EVENT_CASES),
            observed=module.get("accepted_count"),
        )

    functions = module.get("functions")
    if not isinstance(functions, dict):
        add(blockers, "runtime_summary_functions_missing", f"$.source_summary.modules.{MODULE}.functions")
        return []
    for function in EXPECTED_DETAIL_VALUES:
        require_expected_detail_values(blockers, functions, function)
    observed_runtime_cases = validate_observed_event_cases(module, blockers)
    if module.get("observer_gate_count") == 1:
        observed_runtime_cases.insert(0, "observer_enable")
    return observed_runtime_cases


def validate_operational_window(window: Any, summary: Any, blockers: list[dict[str, Any]]) -> None:
    label = "$.operational_window"
    if not isinstance(window, dict):
        add(blockers, "operational_window_missing", label)
        return
    unexpected_window_keys = set(window) - ALLOWED_OPERATIONAL_WINDOW_KEYS
    if unexpected_window_keys:
        add(
            blockers,
            "operational_window_keys_unexpected",
            label,
            unexpected=sorted(unexpected_window_keys),
        )
    if window.get("schema") != WINDOW_CHECK_SCHEMA:
        add(blockers, "operational_window_schema_mismatch", f"{label}.schema")
    if window.get("ready") is not True or window.get("operational_window_manifest_ready") is not True:
        add(blockers, "operational_window_not_ready", label)
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if window.get(key) is not False:
            add(blockers, f"operational_window_{key}_not_false", f"{label}.{key}")
    target = window.get("target")
    if not isinstance(target, dict) or not target.get("instance") or not target.get("map"):
        add(blockers, "operational_window_target_missing", f"{label}.target")
    copied = window.get("copied_log")
    if not isinstance(copied, dict):
        add(blockers, "operational_window_copied_log_missing", f"{label}.copied_log")
        return
    unexpected_copied_keys = set(copied) - ALLOWED_OPERATIONAL_WINDOW_COPIED_LOG_KEYS
    if unexpected_copied_keys:
        add(
            blockers,
            "operational_window_copied_log_keys_unexpected",
            f"{label}.copied_log",
            unexpected=sorted(unexpected_copied_keys),
        )
    if copied.get("path_status") != EXPECTED_COPIED_LOG_PATH_STATUS:
        add(
            blockers,
            "operational_window_copied_log_path_status_mismatch",
            f"{label}.copied_log.path_status",
            expected=EXPECTED_COPIED_LOG_PATH_STATUS,
        )
    if not source_path_is_copied_or_offline(copied.get("path")):
        add(blockers, "operational_window_copied_log_path_not_copied_or_offline", f"{label}.copied_log.path")
    elif not source_path_is_approved_offline_workspace(copied.get("path")):
        add(
            blockers,
            "operational_window_copied_log_path_not_approved_offline_workspace",
            f"{label}.copied_log.path",
        )
    evidence = summary.get("evidence") if isinstance(summary, dict) else None
    sources = evidence.get("sources") if isinstance(evidence, dict) else None
    if not isinstance(sources, list) or not sources or not isinstance(sources[0], dict):
        add(blockers, "operational_window_source_summary_source_missing", "$.source_summary.evidence.sources")
        return
    source = sources[0]
    copied_path = Path(str(copied.get("path", ""))).expanduser()
    source_path = Path(str(source.get("path", ""))).expanduser()
    if copied_path.resolve() != source_path.resolve():
        add(blockers, "operational_window_copied_log_path_mismatch", f"{label}.copied_log.path")
    run_id = window.get("run_id")
    if isinstance(run_id, str):
        expected_tail = (EXPECTED_COPIED_LOG_PARENT, run_id, "Obelisk.log")
        if copied_path.parts[-3:] != expected_tail:
            add(
                blockers,
                "operational_window_copied_log_path_not_live_validation_run_log",
                f"{label}.copied_log.path",
                expected="/".join(expected_tail),
            )
    if copied.get("sha256") != source.get("sha256"):
        add(blockers, "operational_window_copied_log_sha256_mismatch", f"{label}.copied_log.sha256")
    if window.get("obelisk_commit") != evidence.get("obelisk_commit"):
        add(blockers, "operational_window_obelisk_commit_mismatch", f"{label}.obelisk_commit")

    posture = window.get("posture")
    if not isinstance(posture, dict):
        add(blockers, "operational_window_posture_missing", f"{label}.posture")
    else:
        unexpected_posture_keys = set(posture) - ALLOWED_OPERATIONAL_WINDOW_POSTURE_KEYS
        if unexpected_posture_keys:
            add(
                blockers,
                "operational_window_posture_keys_unexpected",
                f"{label}.posture",
                unexpected=sorted(unexpected_posture_keys),
            )
        expected_posture = {
            "pre_check": "passed",
            "post_check": "passed",
            "pre_posture": "stable",
            "post_posture": "stable",
            "plugins_disabled": True,
            "scanner_disabled": True,
            "dispatch_limit": "0",
            "wrapper_profile": "observer-debug",
            "observer_exclusivity": "player_principal_lifecycle_only",
            "debug_escape_markers": "absent",
            "callback_escape_markers": "absent",
            "native_exec_disabled": True,
            "ptrace_disabled": True,
            "single_module_summary": MODULE,
        }
        for key, expected in expected_posture.items():
            if posture.get(key) != expected:
                add(blockers, "operational_window_posture_mismatch", f"{label}.posture.{key}", expected=expected)
    rollback = window.get("rollback")
    if not isinstance(rollback, dict):
        add(blockers, "operational_window_rollback_missing", f"{label}.rollback")
    else:
        unexpected_rollback_keys = set(rollback) - ALLOWED_OPERATIONAL_WINDOW_ROLLBACK_KEYS
        if unexpected_rollback_keys:
            add(
                blockers,
                "operational_window_rollback_keys_unexpected",
                f"{label}.rollback",
                unexpected=sorted(unexpected_rollback_keys),
            )
        for key in ("completed",):
            if rollback.get(key) is not True:
                add(blockers, "operational_window_rollback_not_complete", f"{label}.rollback.{key}")
        for key in ("observer_env_survived", "observer_marker_survived"):
            if rollback.get(key) is not False:
                add(blockers, "operational_window_rollback_marker_survived", f"{label}.rollback.{key}")
    claims = window.get("claims")
    if not isinstance(claims, dict) or claims.get("delivery_claim") != "none" or claims.get("principal_claim") != "none":
        add(blockers, "operational_window_claims_not_none", f"{label}.claims")
    elif set(claims) - ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS:
        add(
            blockers,
            "operational_window_claims_keys_unexpected",
            f"{label}.claims",
            unexpected=sorted(set(claims) - ALLOWED_OPERATIONAL_WINDOW_CLAIMS_KEYS),
        )
    if window.get("user_policy") not in {"no_regular_users", "operator_approved_beta_users"}:
        add(blockers, "operational_window_user_policy_unapproved", f"{label}.user_policy")


def validate_consumer_boundary(cases: Any, blockers: list[dict[str, Any]]) -> list[str]:
    if not isinstance(cases, list):
        add(blockers, "consumer_boundary_cases_not_list", "$.consumer_boundary_cases")
        return []
    seen: list[str] = []
    for index, case in enumerate(cases):
        label = f"$.consumer_boundary_cases[{index}]"
        if not isinstance(case, dict):
            add(blockers, "consumer_boundary_case_invalid", label)
            continue
        unexpected_case_keys = set(case) - ALLOWED_CONSUMER_CASE_KEYS
        if unexpected_case_keys:
            add(
                blockers,
                "consumer_boundary_case_keys_unexpected",
                label,
                unexpected=sorted(unexpected_case_keys),
            )
        name = case.get("case")
        if not isinstance(name, str):
            add(blockers, "consumer_boundary_case_missing", f"{label}.case")
            continue
        seen.append(name)
        if name not in REQUIRED_CONSUMER_CASES:
            add(blockers, "consumer_boundary_case_unexpected", f"{label}.case", case=name)
        if case.get("result") != "fail_closed":
            add(blockers, "consumer_boundary_case_not_fail_closed", f"{label}.result", case=name)
        if case.get("provenance") != "consumer_boundary_assertion_not_runtime_observation":
            add(
                blockers,
                "consumer_boundary_case_provenance_mismatch",
                f"{label}.provenance",
                case=name,
            )
        if case.get("runtime_observed") is not False:
            add(
                blockers,
                "consumer_boundary_runtime_observed_not_false",
                f"{label}.runtime_observed",
                case=name,
            )
        for key in ("lookup_allowed", "mutation_allowed", "return_override_allowed", "public_sdk_surface"):
            if case.get(key) is not False:
                add(blockers, f"consumer_boundary_{key}_not_false", f"{label}.{key}", case=name)
    missing = REQUIRED_CONSUMER_CASES - set(seen)
    if missing:
        add(blockers, "consumer_boundary_cases_missing", "$.consumer_boundary_cases", missing=sorted(missing))
    return sorted(set(seen))


def validate_privacy(boundary: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(boundary, dict):
        add(blockers, "privacy_boundary_missing", "$.privacy_boundary")
        return
    unexpected_keys = set(boundary) - PRIVACY_BOUNDARY_KEYS
    if unexpected_keys:
        add(
            blockers,
            "privacy_boundary_keys_unexpected",
            "$.privacy_boundary",
            unexpected=sorted(unexpected_keys),
        )
    for key in ("copied_opaque_principal_only", "redacted_runtime_observer", "player_identifiers_logged"):
        expected = False if key == "player_identifiers_logged" else True
        if boundary.get(key) is not expected:
            add(blockers, f"privacy_boundary_{key}_mismatch", f"$.privacy_boundary.{key}")
    for key in ("lookup_allowed", "resource_handle_allowed", "mutation_allowed", "return_override_allowed"):
        if boundary.get(key) is not False:
            add(blockers, f"privacy_boundary_{key}_not_false", f"$.privacy_boundary.{key}")


def validate_approval(approval: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(approval, dict):
        add(blockers, "approval_missing", "$.approval")
        return
    unexpected_keys = set(approval) - ALLOWED_APPROVAL_KEYS
    if unexpected_keys:
        add(blockers, "approval_keys_unexpected", "$.approval", unexpected=sorted(unexpected_keys))
    if approval.get("runtime_evidence_reviewed") is not True:
        add(blockers, "approval_runtime_evidence_reviewed_not_true", "$.approval.runtime_evidence_reviewed")
    for key in (
        "runtime_work_authorized_by_this_manifest",
        "server_operations_authorized_by_this_manifest",
        "publication_authorized_by_this_manifest",
        "discord_authorized_by_this_manifest",
    ):
        if approval.get(key) is not False:
            add(blockers, f"approval_{key}_not_false", f"$.approval.{key}")


def validate_promotion_gate(gate: Any, blockers: list[dict[str, Any]]) -> None:
    if not isinstance(gate, dict):
        add(blockers, "promotion_gate_missing", "$.promotion_gate")
        return
    unexpected_keys = set(gate) - ALLOWED_PROMOTION_GATE_KEYS
    if unexpected_keys:
        add(blockers, "promotion_gate_keys_unexpected", "$.promotion_gate", unexpected=sorted(unexpected_keys))
    if gate.get("runtime_evidence_ready") is not True:
        add(blockers, "promotion_gate_runtime_evidence_ready_not_true", "$.promotion_gate.runtime_evidence_ready")
    for key in ("ready", "promotion_ready", "public_sdk_ready", "runtime_ready"):
        if gate.get(key) is not False:
            add(blockers, f"promotion_gate_{key}_not_false", f"$.promotion_gate.{key}")


def find_forbidden_key(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if trail in ALLOWED_FORBIDDEN_LEAF_PATHS:
        return None
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                child_trail not in ALLOWED_FORBIDDEN_KEY_PATHS
                and str(key) not in ALLOWED_FORBIDDEN_KEY_NAMES
                and FORBIDDEN_KEY_RE.search(str(key))
                and child not in ([], {}, None)
            ):
                return str(key), child_trail
            found = find_forbidden_key(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_forbidden_key(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif (
        isinstance(value, str)
        and not any(token in trail for token in NEGATIVE_CONTEXT_TOKENS)
        and FORBIDDEN_KEY_RE.search(value)
        and "does not expose" not in value
    ):
        return value, trail
    return None


def find_positive_capability_claim(value: Any, trail: str = "$") -> tuple[str, str] | None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            if (
                child is not False
                and child is not None
                and POSITIVE_CAPABILITY_CLAIM_RE.search(str(key))
                and not NEGATIVE_CLAIM_CONTEXT_RE.search(str(key))
            ):
                return str(key), child_trail
            found = find_positive_capability_claim(child, child_trail)
            if found is not None:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = find_positive_capability_claim(child, f"{trail}[{index}]")
            if found is not None:
                return found
    elif (
        isinstance(value, str)
        and POSITIVE_CAPABILITY_CLAIM_RE.search(value)
        and not NEGATIVE_CLAIM_CONTEXT_RE.search(value)
    ):
        return value, trail
    return None


def validate_manifest(payload: dict[str, Any], *, check_mode: str) -> Validation:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema")
        return Validation(blockers, [], [])
    missing = REQUIRED_TOP_LEVEL_KEYS - set(payload)
    unexpected = set(payload) - REQUIRED_TOP_LEVEL_KEYS
    if missing:
        add(blockers, "top_level_fields_missing_required", "$", missing=sorted(missing))
    if unexpected:
        add(blockers, "top_level_fields_unexpected", "$", unexpected=sorted(unexpected))
    if payload.get("artifact_status") != "approved_runtime_observer_summary":
        add(blockers, "artifact_status_mismatch", "$.artifact_status")
    if payload.get("readiness_classification") != "runtime_evidence_only":
        add(blockers, "readiness_classification_mismatch", "$.readiness_classification")
    if payload.get("approved_runtime_evidence_present") is not True:
        add(blockers, "approved_runtime_evidence_present_not_true", "$.approved_runtime_evidence_present")
    if payload.get("runtime_evidence_ready") is not True:
        add(blockers, "runtime_evidence_ready_not_true", "$.runtime_evidence_ready")
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready"):
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"$.{key}")
    validate_approval(payload.get("approval"), blockers)
    validate_output_artifact_identity(payload, blockers)
    observed_runtime_cases = validate_runtime_summary(payload.get("source_summary"), blockers)
    validate_operational_window(payload.get("operational_window"), payload.get("source_summary"), blockers)
    consumer_cases = validate_consumer_boundary(payload.get("consumer_boundary_cases"), blockers)
    validate_privacy(payload.get("privacy_boundary"), blockers)
    validate_promotion_gate(payload.get("promotion_gate"), blockers)
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list) or not REQUIRED_NON_CLAIMS.issubset(set(non_claims)):
        add(blockers, "non_claims_missing_required", "$.non_claims")
    forbidden = find_forbidden_key(payload)
    if forbidden is not None:
        value, trail = forbidden
        add(blockers, "forbidden_identity_or_ue_internal_leakage", trail, value=value)
    positive_claim = find_positive_capability_claim(payload)
    if positive_claim is not None:
        value, trail = positive_claim
        add(blockers, "forbidden_public_capability_or_readiness_claim", trail, value=value)
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_identity_public_contract_gate", "$.promotion_gate")
    return Validation(blockers, observed_runtime_cases, consumer_cases)


def build_report(payload: dict[str, Any], validation: Validation, *, check_mode: str) -> dict[str, Any]:
    readiness_mode_blockers = {
        "promote_blocked_until_identity_public_contract_gate",
        "public_readiness_blocked_until_identity_public_contract_gate",
        "runtime_readiness_blocked_until_identity_public_contract_gate",
    }
    evidence_blockers = [
        blocker
        for blocker in validation.blockers
        if blocker["reason"] not in readiness_mode_blockers
    ]
    evidence_accepted = not evidence_blockers
    accepted = not validation.blockers
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema"),
        "mode": check_mode,
        "ready": accepted,
        "approved_runtime_evidence_present": evidence_accepted,
        "runtime_evidence_ready": evidence_accepted,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "remaining_blockers": [] if accepted else ["approved_runtime_evidence_not_accepted"],
        "next_blocker": (
            NEXT_BLOCKER_AFTER_RUNTIME_EVIDENCE
            if evidence_accepted
            else "approved_runtime_evidence_not_accepted"
        ),
        "observed_runtime_cases": validation.observed_runtime_cases,
        "consumer_cases": validation.consumer_cases,
        "consumer_boundary_assertions": validation.consumer_cases,
        "blockers": [blocker["reason"] for blocker in validation.blockers],
        "blocker_details": validation.blockers,
        "non_claims": [
            "runtime evidence acceptance does not promote public SDK identity, permissions, commands, lookup, mutation, or v1 readiness",
        ],
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    payload = load_json(args.manifest)
    validation = validate_manifest(payload, check_mode=check_mode)
    report = build_report(payload, validation, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif validation.blockers:
        for blocker in validation.blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not validation.blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
