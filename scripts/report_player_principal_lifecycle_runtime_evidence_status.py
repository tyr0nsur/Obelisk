#!/usr/bin/env python3
"""Report the current player-principal lifecycle runtime evidence status.

This is a read-only coordinator. It may run existing offline report commands, but it
does not create sidecars, copy logs, mutate ARK state, send Discord notices, or claim
runtime evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
CLOSURE_REQUEST = SCRIPTS_DIR / "prepare_player_principal_lifecycle_evidence_closure_request.py"
PASSIVE_SUMMARY = SCRIPTS_DIR / "summarize_player_principal_passive_snapshots.py"
ROUTE_GATE = SCRIPTS_DIR / "check_command_permission_route_gate.py"

SCHEMA = "obelisk.player-principal-lifecycle-runtime-evidence-status.v1"
CLOSURE_REQUEST_SCHEMA = "obelisk.player-principal-lifecycle-evidence-closure-request.v1"
STATUS_ONLY_CLOSURE_CONTEXT_SCHEMA = (
    "obelisk.player-principal-lifecycle-status-only-closure-context.v1"
)
MACHINE_NEXT_ACTIONS_SCHEMA = "obelisk.player-principal-lifecycle-runtime-evidence-status-machine-next-actions.v1"
RUNTIME_EVIDENCE_FAST_PATH_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-fast-path.v1"
)
PLAYER_PRINCIPAL_EVIDENCE_SPLIT_SCHEMA = "obelisk.player-principal-lifecycle-evidence-split-status.v1"
PLAYER_PRINCIPAL_START_END_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
)
CONFIRMED_BETA_NOTICE_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-prep.v1"
NOTICE_ACTION_ARTIFACT_SCHEMA = "obelisk.player-principal-lifecycle-beta-notice-action-artifact.v1"
RUNTIME_WINDOW_LIFECYCLE_SCHEMA = "obelisk.player-principal-lifecycle-runtime-window-lifecycle.v1"
FRESH_PLAYER_BACKED_WINDOW_SCHEMA = "obelisk.player-principal-lifecycle-fresh-player-backed-window-prep.v1"
CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA = (
    "obelisk.player-principal-lifecycle-current-live-diagnostic-blockers.v1"
)
STRICT_TRIPLET_SELECTOR_SCHEMA = (
    "obelisk.player-principal-lifecycle-strict-triplet-selector.v1"
)
EXACT_TRIPLET_BUNDLE_ROUTE_SCHEMA = (
    "obelisk.player-principal-lifecycle-exact-triplet-bundle-route.v1"
)
RUNTIME_EVIDENCE_ACCEPTANCE_BOUNDARY_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-acceptance-boundary.v1"
)
RUNTIME_EVIDENCE_ACCEPTANCE_STATE_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-acceptance-state.v1"
)
CHECKJOININPROGRESS_1_0_ROUTE_WORDING = (
    "approved_runtime_evidence_missing route requires same-run exact "
    "CheckJoinInProgress(1,0) session_start_rejected evidence from "
    "ShooterGameMode.CheckJoinInProgress with post_original=true, "
    "copied_bool_fields=bIsFromLogin,ReturnValue, copied_bool_values=1,0, "
    "redacted_fields=NewPlayer, apply_status=session_start_rejected_noop, "
    "principal_action=none, correlation_status=not_applicable, and "
    "delivery_claim=none"
)
APPROVED_RUNTIME_EVIDENCE_ACCEPTANCE_WORDING = (
    "Only a checker-accepted approved runtime principal lifecycle evidence bundle "
    "for the same copied sibling set can satisfy approved runtime evidence; "
    "diagnostic, passive, runtime-start/end-only, status, and context-only material "
    "remain non-evidence and non-progress."
)
SIDECAR_NON_EVIDENCE_FLAGS = {
    "sidecar_is_notice_action_metadata_only": True,
    "sidecar_counts_as_approved_runtime_evidence": False,
    "sidecar_counts_as_runtime_evidence": False,
    "sidecar_counts_as_sdk_evidence": False,
    "sidecar_counts_toward_sdk": False,
    "sidecar_counts_toward_p0_dependency_chain": False,
    "sidecar_grants_readiness_claims": False,
    "sidecar_authorizes_runtime_work": False,
    "sidecar_authorizes_server_operations": False,
    "sidecar_authorizes_discord": False,
    "stale_sidecar_counts_as_readiness": False,
}
DEFAULT_STANDING_DEBUG_AUTHORITY_REFERENCE = "operator-2026-06-06-standing-launch-authority"
DEFAULT_STANDING_DEBUG_AUTHORITY_SOURCE = "handoff_docs_current_and_compact_context"
REQUIRED_LIFECYCLE_ROLES = ("session_start", "session_start_rejected", "session_end")
SPLIT_CLAIM_NAME_KEYS = {"alias", "claim", "field", "flag", "key", "name", "property"}
SPLIT_CLAIM_VALUE_KEYS = {
    "allowed",
    "classification",
    "enabled",
    "label",
    "ready",
    "result",
    "state",
    "status",
    "support",
    "tier",
    "value",
}
SPLIT_POSITIVE_VALUE_TOKENS = {
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "complete",
    "completed",
    "enabled",
    "present",
    "ready",
    "supported",
    "true",
    "unlocked",
    "yes",
}
SPLIT_NEGATIVE_VALUE_TOKENS = {
    "blocked",
    "candidate",
    "false",
    "missing",
    "no",
    "non",
    "none",
    "not",
    "only",
    "rejected",
    "required",
    "requires",
    "unsupported",
}
SPLIT_FORBIDDEN_CLAIM_TOKENS = {
    "approved",
    "authorize",
    "authorized",
    "authorizes",
    "complete",
    "completion",
    "evidence",
    "progress",
    "public",
    "ready",
    "readiness",
    "runtime",
    "sdk",
    "stable",
    "v1",
}
REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET = (
    {
        "label": "HandleNewPlayer(1,1)",
        "role": "session_start",
        "target": "ShooterGameMode.HandleNewPlayer",
        "post_original": "true",
        "copied_bool_fields": ("bIsFromLogin", "ReturnValue"),
        "copied_bool_values": ("1", "1"),
        "redacted_count": "3",
        "redacted_fields": ("NewPlayer", "PlayerData", "PlayerCharacter"),
        "apply_status": "session_start_created",
        "principal_action": "candidate_created",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    {
        "label": "CheckJoinInProgress(1,0)",
        "role": "session_start_rejected",
        "target": "ShooterGameMode.CheckJoinInProgress",
        "post_original": "true",
        "copied_bool_fields": ("bIsFromLogin", "ReturnValue"),
        "copied_bool_values": ("1", "0"),
        "redacted_count": "1",
        "redacted_fields": ("NewPlayer",),
        "apply_status": "session_start_rejected_noop",
        "principal_action": "none",
        "correlation_status": "not_applicable",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
    {
        "label": "OnLogout matched",
        "role": "session_end",
        "target": "ShooterGameMode.OnLogout",
        "post_original": "true",
        "copied_bool_fields": (),
        "copied_bool_values": (),
        "redacted_count": "1",
        "redacted_fields": ("Exiting",),
        "apply_status": "session_end_invalidated",
        "principal_action": "candidate_invalidated",
        "correlation_status": "matched",
        "principal_id_logged": "false",
        "principal_generation_logged": "false",
        "delivery_claim": "none",
    },
)
REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS = tuple(
    str(case["label"]) for case in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
)
SESSION_END_MISSING_CORRELATION_REASON_KEYS = frozenset(
    (
        "session_end_correlation_status_missing",
        "session_end_unresolved_noop_outcome",
    )
)
ALLOWED_OPERATOR_CONTEXT_TARGETS = {
    ("arkserver2", "TheIsland"),
    ("arkserver3", "Genesis2"),
    ("arkserver", "Ragnarok"),
}
FORBIDDEN_SHORTCUT_ALIAS_CLASSES = (
    "passive_snapshot_or_triplet_shortcut",
    "notice_or_discord_shortcut",
    "status_or_summary_shortcut",
)
CLOSURE_SCHEMA_ALIAS_BLOCKERS = (
    (
        re.compile(r"(?:passive|snapshot|watch(?:er|[._-]?only)|monitor[._-]?tick|triplet)", re.IGNORECASE),
        "closure_json_passive_or_triplet_shortcut_alias",
    ),
    (
        re.compile(r"(?:notice|beta[._-]?notice|discord)", re.IGNORECASE),
        "closure_json_notice_or_discord_shortcut_alias",
    ),
    (
        re.compile(r"(?:status|report|summary|readiness[._-]?check|completion[._-]?check)", re.IGNORECASE),
        "closure_json_status_or_summary_shortcut_alias",
    ),
)
SOURCE_ONLY_COPY_READY_RE = re.compile(
    r"(?:stale|historical|previous|prior|old[_ .:-]?window|passive(?:[_ .:-]?monitor)?|"
    r"snapshot|monitor|post[_ .:-]?reboot|postpatch|status[_ .:-]?report)",
    re.IGNORECASE,
)
SOURCE_PRESENT_ALIAS_SUBJECT_TOKENS = frozenset(
    (
        "candidate",
        "candidates",
        "copy",
        "copied",
        "evidence",
        "input",
        "log",
        "material",
        "pack",
        "source",
    )
)
SOURCE_PRESENT_ALIAS_STATE_TOKENS = frozenset(
    (
        "accepted",
        "available",
        "exists",
        "found",
        "present",
        "provided",
        "ready",
        "supplied",
    )
)
CANDIDATE_PACK_ALIAS_TOKENS = frozenset(
    (
        "candidate",
        "candidates",
        "pack",
        "packs",
    )
)
SOURCE_ALIAS_VALUE_KEYS = frozenset(
    (
        "classification",
        "copy_readiness",
        "kind",
        "readiness",
        "source_kind",
        "state",
        "status",
    )
)
OBELISK_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SUMMARY_FALSE_CLAIMS = (
    "approved_runtime_evidence",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "runtime_ready",
    "public_sdk_ready",
    "stable_sdk_ready",
    "v1_completion_ready",
    "publication_authorized",
    "discord_authorized",
    "server_operations_authorized_by_this_report",
    "runtime_work_authorized_by_this_report",
    "marker_env_changes_authorized_by_this_report",
    "workspace_writes_authorized_by_this_report",
)
FALSE_FLAGS = {
    "approved_runtime_evidence": False,
    "approved_runtime_evidence_present": False,
    "approved_runtime_evidence_ready": False,
    "approved_in_game_evidence_ready": False,
    "runtime_ready": False,
    "public_sdk_ready": False,
    "public_abi_ready": False,
    "public_header_allowed": False,
    "promotion_ready": False,
    "v1_completion_ready": False,
    "stable_claim_allowed": False,
    "stable_sdk_ready": False,
    "route_ready": False,
    "runtime_work_authorized": False,
    "server_operations_authorized": False,
    "workspace_writes_authorized": False,
    "marker_env_changes_authorized": False,
    "discord_authorized": False,
    "discord_sent_by_this_report": False,
    "publication_authorized": False,
    "counts_as_approved_runtime_evidence": False,
    "counts_as_runtime_evidence": False,
    "counts_as_sdk_evidence": False,
    "counts_toward_sdk": False,
    "counts_toward_v1_completion": False,
    "counts_toward_complete_sdk_claim_now": False,
    "counts_toward_p0_dependency_chain": False,
    "counts_toward_p0_dependency_chain_claim_now": False,
    "sdk_progress": 0,
    "p0_progress": 0,
}
SPLIT_DIRECT_ALLOWED_POSITIVE_ALIAS_KEYS = frozenset(
    (
        "accepted_for_contract_review",
        "principal_start_end_runtime_evidence_present",
        "principal_start_end_runtime_evidence_ready",
        "ready",
    )
)
SPLIT_DIRECT_FALSE_ALIAS_KEYS = frozenset(
    set(FALSE_FLAGS)
    | {
        "accepted_as_approved_runtime_principal_lifecycle_evidence",
        "accepted_by_approved_runtime_evidence_checker",
        "accepted_by_checker",
        "approved_bundle_accepted",
        "approved_runtime_evidence_accepted",
        "approved_runtime_principal_lifecycle_evidence",
        "approved_runtime_principal_lifecycle_evidence_bundle_accepted",
        "approved_runtime_principal_lifecycle_evidence_bundle_ready",
        "checker_accepted",
        "complete_sdk_allowed",
        "complete_sdk_ready",
        "counts_as_approved_runtime_principal_lifecycle_evidence",
        "counts_as_p0_progress",
        "counts_as_public_sdk",
        "counts_as_sdk_or_p0_progress",
        "counts_as_sdk_progress",
        "counts_toward_public_readiness",
        "counts_toward_runtime_readiness",
        "public_readiness",
        "public_readiness_ready",
        "public_ready",
        "runtime_readiness",
        "runtime_readiness_ready",
        "runtime_v1_ready",
    }
)
SPLIT_DIRECT_FALSE_ALIAS_FRAGMENTS = (
    "accepted_as_approved",
    "accepted_by_checker",
    "approved_bundle_accepted",
    "approved_runtime_evidence",
    "approved_runtime_principal_lifecycle_evidence",
    "bundle_accepted",
    "checker_accepted",
    "counts_as_approved_runtime_evidence",
    "counts_as_approved_runtime_principal_lifecycle_evidence",
    "counts_as_p0_progress",
    "counts_as_runtime_evidence",
    "counts_as_sdk_evidence",
    "counts_as_sdk_progress",
    "counts_toward_complete_sdk",
    "counts_toward_p0",
    "counts_toward_public",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "evidence_bundle_accepted",
    "marker_env_changes_authorized",
    "operator_authorization",
    "operator_authorized",
    "public_readiness",
    "public_sdk",
    "publication_authorized",
    "runtime_evidence",
    "runtime_readiness",
    "runtime_work_authorized",
    "server_operations_authorized",
    "stable_sdk",
    "v1_completion",
    "workspace_writes_authorized",
)
SPLIT_DIRECT_ZERO_ALIAS_KEYS = frozenset(
    (
        "claim_credit",
        "claim_credits",
        "claim_progress_contribution",
        "complete_sdk_claim_progress_contribution",
        "complete_sdk_claim_progress_ratio",
        "complete_sdk_credit",
        "complete_sdk_credits",
        "complete_sdk_progress",
        "complete_sdk_progress_contribution",
        "complete_sdk_progress_ratio",
        "p0_credit",
        "p0_credits",
        "p0_dependency_chain_progress",
        "p0_dependency_chain_progress_contribution",
        "p0_dependency_chain_progress_ratio",
        "p0_progress",
        "progress",
        "sdk_credit",
        "sdk_credits",
        "sdk_progress",
        "sdk_progress_contribution",
        "v1_completion_contribution",
        "v1_completion_credit",
        "v1_completion_credits",
    )
)

APPROVED_RUNTIME_EVIDENCE_JSON = (
    "approved-bundle/approved-runtime-principal-lifecycle-evidence.json"
)
BUNDLE_BUILDER_SCRIPT = (
    "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
)
BUNDLE_CHECKER_SCRIPT = (
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
CRITICAL_RUNTIME_EVIDENCE_ARTIFACTS = (
    "Obelisk.log",
    "window-manifest.env",
    "preflight-post.json",
    APPROVED_RUNTIME_EVIDENCE_JSON,
)
RUNTIME_EVIDENCE_ARTIFACT_BLOCKERS_SCHEMA = (
    "obelisk.player-principal-lifecycle-runtime-evidence-artifact-blockers.v1"
)
ARTIFACT_BLOCKER_REASONS = {
    "Obelisk.log": "copied_obelisk_log_missing",
    "window-manifest.env": "window_manifest_env_missing",
    "preflight-post.json": "preflight_post_json_missing",
    APPROVED_RUNTIME_EVIDENCE_JSON: (
        "approved_runtime_principal_lifecycle_evidence_json_missing"
    ),
}
ARTIFACT_ACTIONS = {
    "Obelisk.log": "copy_ready_player_principal_lifecycle_obelisk_log",
    "window-manifest.env": "provide_completed_window_manifest_env_sibling",
    "preflight-post.json": "capture_post_window_stable_preflight_json",
    APPROVED_RUNTIME_EVIDENCE_JSON: (
        "build_approved_runtime_principal_lifecycle_evidence_bundle"
    ),
}
ARTIFACT_REQUIRED_SCRIPTS = {
    "Obelisk.log": "scripts/copy_player_principal_lifecycle_ready_log.py",
    "window-manifest.env": (
        "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py"
    ),
    "preflight-post.json": "scripts/check_player_principal_lifecycle_preflight.sh",
    APPROVED_RUNTIME_EVIDENCE_JSON: (
        "scripts/build_player_identity_runtime_principal_lifecycle_evidence_bundle.py"
    ),
}
ARTIFACT_BLOCKER_DETAILS = {
    "Obelisk.log": {
        "side_effect_domain": "live_log_copy",
        "runner_command_available": False,
        "command_text_not_emitted": (
            "copied Obelisk.log must come from the approved runtime window; this "
            "status report and offline runner do not read live logs"
        ),
        "next_step": (
            "copy the same-run Obelisk.log only after the exact accepted lifecycle "
            "triplet is present in the approved window"
        ),
    },
    "window-manifest.env": {
        "side_effect_domain": "offline_sidecar_write",
        "runner_command_available": True,
        "next_step": (
            "emit and replay-check window-manifest.env against the same-run copied "
            "Obelisk.log"
        ),
    },
    "preflight-post.json": {
        "side_effect_domain": "post_window_preflight_live_read",
        "runner_command_available": False,
        "command_text_not_emitted": (
            "post-window stable preflight needs the scoped live/procfs posture helper; "
            "the offline runner must not perform that live read"
        ),
        "next_step": (
            "capture the post-window stable preflight JSON for the same run after the "
            "copied log and window manifest are bound"
        ),
    },
    APPROVED_RUNTIME_EVIDENCE_JSON: {
        "side_effect_domain": "offline_bundle_write",
        "runner_command_available": False,
        "command_text_not_emitted": (
            "approved bundle JSON needs all checked sibling artifacts plus reviewed "
            "commit/reviewer metadata before the bundle helper command is exact"
        ),
        "next_step": (
            "build the approved runtime principal lifecycle evidence bundle from the "
            "same-run copied log, window manifest, checked sidecars, and review binding"
        ),
    },
}
ARTIFACT_BLOCKED_UNTIL = {
    "Obelisk.log": [
        "copied-lifecycle-triplet/HandleNewPlayer(1,1)",
        "copied-lifecycle-triplet/CheckJoinInProgress(1,0)",
        "copied-lifecycle-triplet/OnLogout matched",
    ],
    "window-manifest.env": [
        "Obelisk.log",
        "window-request.json",
        "observer-window.env",
        "operator-approval-request.md",
        "operator-approval-receipt.json",
        "preflight-pre.json",
    ],
    "preflight-post.json": [
        "Obelisk.log",
        "window-manifest.env",
    ],
    APPROVED_RUNTIME_EVIDENCE_JSON: [
        "Obelisk.log",
        "window-request.json",
        "observer-window.env",
        "operator-approval-request.md",
        "operator-approval-receipt.json",
        "preflight-pre.json",
        "preflight-post.json",
        "window-manifest.env",
    ],
}
REQUEST_WINDOW_ARTIFACTS = (
    "window-request.json",
    "observer-window.env",
    "operator-approval-request.md",
    "operator-approval-receipt.json",
    "preflight-pre.json",
    "preflight-post.json",
    "window-manifest.env",
)
APPROVED_RUNTIME_EVIDENCE_EXACT_SIBLING_SET = (
    "Obelisk.log",
    *REQUEST_WINDOW_ARTIFACTS,
    APPROVED_RUNTIME_EVIDENCE_JSON,
)


def sdk_p0_non_progress_flags() -> dict[str, Any]:
    return {
        "counts_toward_sdk": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim_now": False,
        "counts_toward_p0_dependency_chain": False,
        "counts_toward_p0_dependency_chain_claim_now": False,
        "passive_player_counts_count_toward_sdk": False,
        "passive_player_counts_count_toward_p0_dependency_chain": False,
        "player_counts_count_toward_sdk": False,
        "player_counts_count_toward_p0_dependency_chain": False,
        "sdk_progress": 0,
        "p0_progress": 0,
    }


def non_evidence_material_flags() -> dict[str, Any]:
    return {
        "accepted_by_status_report": False,
        "accepted_by_checker": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
        "v1_completion_ready": False,
        "stable_sdk_ready": False,
        "grants_readiness_claims": False,
        **sdk_p0_non_progress_flags(),
    }


def approved_bundle_checker_sibling_gate() -> dict[str, Any]:
    return {
        "accepted_bundle_checker_required_before_evidence": True,
        "approved_bundle_checker_accepts_exact_sibling_set": False,
        "accepted_checker_report_supplied_to_status_report": False,
        "exact_sibling_set_accepted_by_checker": False,
        "only_counts_after_approved_bundle_checker_accepts_exact_sibling_set": True,
        "required_checker": "approved_bundle_checker_acceptance_required",
        "required_approved_bundle": APPROVED_RUNTIME_EVIDENCE_JSON,
        "required_exact_sibling_set": list(APPROVED_RUNTIME_EVIDENCE_EXACT_SIBLING_SET),
        "required_triplet_labels": list(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
    }


def runtime_evidence_acceptance_boundary(
    *,
    closure: dict[str, Any],
    closure_schema: dict[str, Any],
    passive_state: dict[str, Any],
    monitor_state: dict[str, Any],
    beta_notice_state: dict[str, Any],
    copy_ready_state: dict[str, Any],
    split_context: dict[str, Any],
    exact_triplet: dict[str, Any],
    artifact_blockers: dict[str, Any],
    route_gate: dict[str, Any],
    current_live_blockers: dict[str, Any],
    closure_checker_ready: bool,
) -> dict[str, Any]:
    false_flags = non_evidence_material_flags()
    sibling_gate = approved_bundle_checker_sibling_gate()
    copy_ready_source_alias_boundary = copy_ready_source_boundary(copy_ready_state)
    diagnostic_present = bool(
        current_live_blockers
        or copy_ready_state.get("diagnostic_only_lifecycle_lines") is True
        or copy_ready_state.get("diagnostic_or_rejected_lifecycle_lines") is True
    )
    diagnostic_triplets_present = bool(
        passive_state.get("complete_observer_event_triplet_targets")
        or copy_ready_state.get("exact_copied_runtime_triplet_accepted") is True
        or copy_ready_state.get("diagnostic_or_rejected_lifecycle_lines") is True
        or copy_ready_state.get("diagnostic_only_lifecycle_lines") is True
    )
    passive_present = bool(
        passive_state.get("present") is True
        or monitor_state.get("present") is True
        or copy_ready_source_alias_boundary.get("source_looks_like_passive_monitor_root") is True
    )
    source_present_alias_present = bool(
        copy_ready_source_alias_boundary.get("source_present_alias_detected") is True
        or copy_ready_source_alias_boundary.get("candidate_pack_alias_detected") is True
    )
    runtime_start_end_present = bool(
        split_context.get("start_end_contract_input_present") is True
        or (
            copy_ready_state.get("present") is True
            and set(string_list(copy_ready_state.get("roles_present"))).issubset(
                {"session_start", "session_end"}
            )
            and bool(string_list(copy_ready_state.get("roles_present")))
        )
    )
    request_window_artifacts_present = bool(
        closure_schema.get("valid") is True
        or any(
            artifact in ordered_missing_artifacts(closure)
            for artifact in REQUEST_WINDOW_ARTIFACTS
        )
        or any(
            artifact in string_list(closure.get("invalid_sidecars"))
            for artifact in REQUEST_WINDOW_ARTIFACTS
        )
    )
    copied_log_presence_present = bool(
        copy_ready_state.get("copied_source_value") is True
        or isinstance(copy_ready_state.get("source_log"), str)
        or (
            closure_schema.get("valid") is True
            and "Obelisk.log" not in ordered_missing_artifacts(closure)
        )
    )
    context_only_present = bool(
        monitor_state.get("present") is True
        or beta_notice_state.get("present") is True
        or copy_ready_state.get("present") is True
        or passive_state.get("present") is True
        or current_live_blockers
    )
    checker_ready_but_not_accepted = bool(
        closure_schema.get("valid") is True and closure_checker_ready
    )
    checker_classification = (
        "checker_runnable_but_not_accepted_by_status_report"
        if checker_ready_but_not_accepted
        else "checker_accepted_approved_runtime_evidence_missing"
    )
    return {
        "schema": RUNTIME_EVIDENCE_ACCEPTANCE_BOUNDARY_SCHEMA,
        "status": "blocked_approved_runtime_evidence_missing",
        "current_route_blocker": route_gate.get("current_route_blocker"),
        "route_blocker_must_remain": "approved_runtime_evidence_missing",
        "acceptance_wording": APPROVED_RUNTIME_EVIDENCE_ACCEPTANCE_WORDING,
        "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        "checker_accepted_approved_evidence_required": True,
        "accepted_checker_report_supplied_to_status_report": False,
        "checker_ready_but_not_accepted_by_status_report": checker_ready_but_not_accepted,
        "closure_ready_for_checker": checker_ready_but_not_accepted,
        "only_checker_accepted_bundle_can_count": True,
        "status_report_sets_sdk_or_p0_progress": False,
        "status_report_sets_readiness": False,
        "readiness_claims_set_by_status_report": False,
        "material_classes": {
            "diagnostic": {
                "present": diagnostic_present,
                "classification": "diagnostic_material_non_evidence",
                "examples": [
                    "diagnostic FName drift lines",
                    "diagnostic-only lifecycle lines",
                    "current live diagnostic blocker context",
                ],
                "route_to_approved_evidence": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                **sibling_gate,
                **false_flags,
            },
            "diagnostic_triplets": {
                "present": diagnostic_triplets_present,
                "classification": "diagnostic_triplet_material_non_evidence_until_checker_accepts_exact_sibling_set",
                "includes": [
                    "passive complete observer triplet summaries",
                    "diagnostic or rejected lifecycle triplet candidates",
                    "copy-ready exact-triplet source values before approved checker acceptance",
                ],
                "passive_complete_triplet_targets": passive_state.get(
                    "complete_observer_event_triplet_targets", []
                ),
                "copy_ready_exact_triplet_source_value": (
                    copy_ready_state.get("exact_copied_runtime_triplet_accepted") is True
                ),
                "route_to_approved_evidence": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                **sibling_gate,
                **false_flags,
            },
            "passive": {
                "present": passive_present,
                "classification": "passive_or_status_material_non_evidence",
                "examples": [
                    "passive monitor ticks",
                    "player counts",
                    "passive complete-role summaries",
                    "ready-log copy helper source-only material",
                ],
                "route_to_approved_evidence": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                **sibling_gate,
                **false_flags,
            },
            "start_end_only": {
                "present": runtime_start_end_present,
                "classification": "start_end_only_runtime_material_non_evidence_until_checker_accepts_exact_sibling_set",
                "roles": ["session_start", "session_end"] if runtime_start_end_present else [],
                "missing_required_route": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                "requires_session_start_rejected": True,
                "requires_strict_three_role_triplet": True,
                **sibling_gate,
                **false_flags,
            },
            "runtime_start_end": {
                "present": runtime_start_end_present,
                "classification": "runtime_start_end_only_material_non_evidence",
                "missing_required_route": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                "requires_session_start_rejected": True,
                "requires_strict_three_role_triplet": True,
                **sibling_gate,
                **false_flags,
            },
            "beta_notices": {
                "present": beta_notice_state.get("present") is True,
                "classification": "beta_notice_material_non_evidence_until_checker_accepts_exact_sibling_set",
                "completed": beta_notice_state.get("completed") is True,
                "source_is_notice_action_sidecar": (
                    beta_notice_state.get("source_is_notice_action_sidecar") is True
                ),
                "sidecar_valid_for_context": (
                    beta_notice_state.get("sidecar_valid_for_context") is True
                ),
                "discord_send_or_notice_completion_counts_as_evidence": False,
                "notice_action_authorizes_runtime_capture": False,
                **sibling_gate,
                **false_flags,
            },
            "request_window_artifacts": {
                "present": request_window_artifacts_present,
                "classification": "request_window_artifacts_non_evidence_until_checker_accepts_exact_sibling_set",
                "artifacts": list(REQUEST_WINDOW_ARTIFACTS),
                "missing_request_window_artifacts": [
                    artifact
                    for artifact in ordered_missing_artifacts(closure)
                    if artifact in REQUEST_WINDOW_ARTIFACTS
                ],
                "artifact_presence_counts_as_evidence": False,
                "request_or_window_sidecars_count_as_evidence": False,
                **sibling_gate,
                **false_flags,
            },
            "copied_log_presence": {
                "present": copied_log_presence_present,
                "classification": "copied_log_presence_non_evidence_until_checker_accepts_exact_sibling_set",
                "source_log": copy_ready_state.get("source_log"),
                "target_log": copy_ready_state.get("target_log"),
                "copy_ready_status": copy_ready_state.get("status"),
                "copy_ready_copied_source_value": (
                    copy_ready_state.get("copied_source_value") is True
                ),
                "copied_log_presence_counts_as_evidence": False,
                "copy_ready_report_counts_as_evidence": False,
                "source_present_alias_detected": (
                    copy_ready_source_alias_boundary.get("source_present_alias_detected") is True
                ),
                "candidate_pack_alias_detected": (
                    copy_ready_source_alias_boundary.get("candidate_pack_alias_detected") is True
                ),
                "source_present_alias_counts_as_approved_runtime_evidence": False,
                "candidate_pack_alias_counts_as_approved_runtime_evidence": False,
                **sibling_gate,
                **false_flags,
            },
            "source_present_aliases": {
                "present": source_present_alias_present,
                "classification": "source_or_candidate_present_alias_non_evidence_until_checker_accepts_exact_sibling_set",
                "source_present_alias_paths": copy_ready_source_alias_boundary.get(
                    "source_present_alias_paths",
                    [],
                ),
                "candidate_pack_alias_paths": copy_ready_source_alias_boundary.get(
                    "candidate_pack_alias_paths",
                    [],
                ),
                "candidate_pack_alias_is_source_only": (
                    copy_ready_source_alias_boundary.get("candidate_pack_alias_detected") is True
                ),
                "source_present_alias_counts_as_evidence": False,
                "candidate_pack_alias_counts_as_evidence": False,
                **sibling_gate,
                **false_flags,
            },
            "context_only": {
                "present": context_only_present,
                "classification": "operator_context_only_non_evidence",
                "examples": [
                    "post-reboot passive monitor context",
                    "confirmed beta notice context",
                    "player availability context",
                    "status summaries",
                ],
                **sibling_gate,
                **false_flags,
            },
            "checker_accepted_approved_evidence": {
                "present": False,
                "classification": checker_classification,
                **sibling_gate,
                "required_checker": (
                    BUNDLE_CHECKER_SCRIPT
                    if checker_ready_but_not_accepted
                    else "checker_accepted_bundle_required"
                ),
                "required_checker_script_available": checker_ready_but_not_accepted,
                "required_artifact": APPROVED_RUNTIME_EVIDENCE_JSON,
                "required_triplet_labels": list(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
                "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                "strict_triplet_complete": exact_triplet.get("complete") is True,
                "missing_copied_lifecycle_event_triplet_labels": string_list(
                    exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
                ),
                "missing_artifacts": artifact_blockers.get("missing_artifacts", []),
                "would_be_evidence_only_after_checker_accepts_current_bundle": True,
                **false_flags,
            },
        },
        "non_evidence_material_classes": [
            "diagnostic",
            "diagnostic_triplets",
            "passive",
            "start_end_only",
            "runtime_start_end",
            "beta_notices",
            "request_window_artifacts",
            "copied_log_presence",
            "source_present_aliases",
            "context_only",
        ],
        "checker_accepted_material_class": "checker_accepted_approved_evidence",
        **sibling_gate,
        **false_flags,
    }


def current_live_diagnostic_blockers_context() -> dict[str, Any]:
    false_claims = {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "accepted_lifecycle_events_count_as_approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        "server_operations_authorized": False,
        "runtime_capture_authorized": False,
        "live_ops_authorized": False,
        "reads_live_logs": False,
        "discord_authorized": False,
        "publication_authorized": False,
    }
    common = {**false_claims, **sdk_p0_non_progress_flags()}
    source_bound_non_actions = {
        "source_bound_blocker": True,
        "route_to_drift_or_source_bound_blocker": True,
        "blind_wait_recommended": False,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "runner_action_allowed": False,
        "accepted_events_required_before_progress": True,
    }
    blockers = [
        {
            "id": "theisland_active_player_observer_only_no_accepted_lifecycle_event",
            "blocker": "active_player_observer_only_no_accepted_lifecycle_event",
            "source_bound_blocker_kind": (
                "active_player_observer_enabled_no_accepted_lifecycle_events"
            ),
            "target": {"instance": "arkserver2", "map": "TheIsland"},
            "player_count_current": 1,
            "players_detected": True,
            "observer_enabled": True,
            "observer_only": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "missing_accepted_lifecycle_roles": list(REQUIRED_LIFECYCLE_ROLES),
            "next_status_input_needed": (
                "source-bound drift resolution or same-window accepted lifecycle "
                "event triplet after the source blocker clears; otherwise "
                "window-end non-evidence classification"
            ),
            **source_bound_non_actions,
            **common,
        },
        {
            "id": "ragnarok_diagnostic_fname_drift_blocks_accepted_events",
            "blocker": "diagnostic_fname_drift_blocks_accepted_events",
            "source_bound_blocker_kind": "diagnostic_fname_drift",
            "target": {"instance": "arkserver", "map": "Ragnarok"},
            "diagnostic_fname_mismatch_lines_present": True,
            "diagnostic_fname_drift": True,
            "accepted_lifecycle_event_count": 0,
            "accepted_lifecycle_roles": [],
            "next_status_input_needed": (
                "resolve or avoid diagnostic FName drift before treating lifecycle "
                "lines as accepted copied observer events"
            ),
            **source_bound_non_actions,
            **common,
        },
    ]
    return {
        "schema": CURRENT_LIVE_DIAGNOSTIC_BLOCKERS_SCHEMA,
        "status": "blocked_approved_runtime_evidence_missing",
        "classification": "source_bound_drift_blockers_non_evidence",
        "source": "operator_supplied_current_redacted_state",
        "planner_did_not_read_live_logs": True,
        "status_report_only": True,
        "blocker_context_only": True,
        "diagnostic_non_evidence": True,
        "source_bound_blocker": True,
        "route_to_drift_or_source_bound_blocker": True,
        "current_source_bound_route_blocker": "source_bound_drift_blocks_accepted_lifecycle_events",
        "blind_wait_recommended": False,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "runner_action_allowed": False,
        "active_ark_server_count": 2,
        "active_server_targets": [
            {"instance": "arkserver2", "map": "TheIsland"},
            {"instance": "arkserver", "map": "Ragnarok"},
        ],
        "inactive_or_unknown_targets": [
            {
                "instance": "arkserver3",
                "map": "Genesis2",
                "state": "inactive_or_unknown",
                "counted_in_active_ark_server_count": False,
            }
        ],
        "current_route_blocker": "approved_runtime_evidence_missing",
        "next_blockers": blockers,
        "next_blocker_ids": [str(blocker["id"]) for blocker in blockers],
        "primary_next_blocker": blockers[0]["blocker"],
        "secondary_next_blocker": blockers[1]["blocker"],
        "required_accepted_lifecycle_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "approved_runtime_evidence_unlocks_after": (
            "checker-accepted copied runtime principal lifecycle evidence bundle"
        ),
        "non_claim": (
            "Current redacted live state is blocker context only: TheIsland has an "
            "active player but observer-only/no accepted lifecycle roles; Ragnarok "
            "has diagnostic FName drift that blocks accepted events; Genesis2 is "
            "inactive or unknown. None of this is SDK/P0 progress or approved "
            "runtime evidence."
        ),
        **source_bound_non_actions,
        **common,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path, help="Evidence run directory to inspect with closure helper.")
    parser.add_argument("--instance", help="Exact ARK instance id for closure helper.")
    parser.add_argument("--map", dest="map_name", help="Exact ARK map name for closure helper.")
    parser.add_argument("--query-port", help="Exact Steam query port for closure helper.")
    parser.add_argument("--notice-path", default="not_applicable", help="Notice path label for closure helper.")
    parser.add_argument("--closure-json", type=Path, help="Use a precomputed closure JSON report.")
    parser.add_argument("--passive-summary-json", type=Path, help="Use a precomputed passive summary JSON report.")
    parser.add_argument("--route-gate-json", type=Path, help="Use a precomputed route gate JSON report.")
    parser.add_argument(
        "--monitor-log",
        type=Path,
        help=(
            "Passive monitor log for on-demand passive summary when --snapshot-root is "
            "also supplied; otherwise reported as post-reboot operator context only."
        ),
    )
    parser.add_argument(
        "--post-reboot-monitor-log",
        type=Path,
        help="Copied post-reboot passive monitor log to report as non-evidence operator context.",
    )
    parser.add_argument("--snapshot-root", type=Path, help="Passive snapshot root for on-demand passive summary.")
    parser.add_argument(
        "--confirmed-beta-notice-json",
        type=Path,
        help="Confirmed beta notice JSON to report as non-evidence operator context.",
    )
    parser.add_argument(
        "--copy-ready-json",
        type=Path,
        help="Ready-log copy helper JSON to report as non-evidence operator context.",
    )
    parser.add_argument(
        "--player-principal-evidence-split-json",
        type=Path,
        help=(
            "Optional offline player-principal evidence split JSON, such as the "
            "start/end-only contract-review checker output. It is propagated as "
            "non-evidence context only."
        ),
    )
    parser.add_argument("--the-island-off", action="store_true", help="Forward TheIsland-off state to closure helper.")
    parser.add_argument(
        "--two-server-cap-preserved",
        action="store_true",
        help="Forward two-server cap state to closure helper.",
    )
    parser.add_argument(
        "--future-window-needs-players",
        action="store_true",
        help="Forward future player requirement to closure helper.",
    )
    parser.add_argument("--json-output", type=Path, help="Optional repo-local JSON output path.")
    parser.add_argument(
        "--recorded-standing-debug-authority",
        action="store_true",
        help=(
            "Annotate that the operator brief/handoff docs record standing debug "
            "authority for the exact player-principal lifecycle follow-up scope."
        ),
    )
    parser.add_argument(
        "--standing-debug-authority-reference",
        default=DEFAULT_STANDING_DEBUG_AUTHORITY_REFERENCE,
        help="Reference label for the recorded standing debug authority annotation.",
    )
    parser.add_argument(
        "--standing-debug-authority-source",
        default=DEFAULT_STANDING_DEBUG_AUTHORITY_SOURCE,
        help="Source label for the recorded standing debug authority annotation.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def closure_run_id(closure: dict[str, Any]) -> str | None:
    run_id = closure.get("run_id")
    if isinstance(run_id, str) and run_id:
        return run_id
    evidence_dir = closure.get("evidence_dir")
    if isinstance(evidence_dir, str) and evidence_dir:
        return Path(evidence_dir).name
    return None


def closure_schema_state(closure: dict[str, Any]) -> dict[str, Any]:
    schema = closure.get("schema")
    if schema == CLOSURE_REQUEST_SCHEMA:
        return {
            "schema": schema,
            "valid": True,
            "blocker": None,
        }
    reason = (
        "closure_json_not_supplied_status_only_context"
        if schema == STATUS_ONLY_CLOSURE_CONTEXT_SCHEMA
        else "closure_json_schema_missing_or_mismatch"
    )
    if isinstance(schema, str):
        for pattern, alias_reason in CLOSURE_SCHEMA_ALIAS_BLOCKERS:
            if pattern.search(schema):
                if schema == STATUS_ONLY_CLOSURE_CONTEXT_SCHEMA:
                    break
                reason = alias_reason
                break
    blocker = {
        "reason": reason,
        "schema": schema,
        "expected_schema": CLOSURE_REQUEST_SCHEMA,
        "forbidden_shortcut_alias_classes": list(FORBIDDEN_SHORTCUT_ALIAS_CLASSES),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
    }
    return {
        "schema": schema,
        "valid": False,
        "blocker": blocker,
    }


def object_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def normalized_split_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    separated = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", separated)
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def split_alias_tokens(value: object) -> set[str]:
    return {token for token in normalized_split_key(value).split("_") if token}


def split_alias_value_is_positive(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        tokens = split_alias_tokens(value)
        if tokens & SPLIT_NEGATIVE_VALUE_TOKENS:
            return False
        return bool(tokens & SPLIT_POSITIVE_VALUE_TOKENS)
    if isinstance(value, dict):
        return any(split_alias_value_is_positive(child) for child in value.values())
    if isinstance(value, list):
        return any(split_alias_value_is_positive(child) for child in value)
    return False


def source_present_alias_value_tokens(value: Any) -> set[str]:
    return split_alias_tokens(value) if isinstance(value, str) else set()


def source_present_alias_paths(value: Any, trail: str = "$") -> tuple[list[str], list[str]]:
    source_paths: list[str] = []
    candidate_paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}"
            key_tokens = split_alias_tokens(key)
            value_tokens = source_present_alias_value_tokens(child)
            key_claims_source = bool(
                key_tokens & SOURCE_PRESENT_ALIAS_SUBJECT_TOKENS
                and key_tokens & SOURCE_PRESENT_ALIAS_STATE_TOKENS
                and split_alias_value_is_positive(child)
            )
            value_claims_source = bool(
                key_tokens & SOURCE_ALIAS_VALUE_KEYS
                and value_tokens & SOURCE_PRESENT_ALIAS_SUBJECT_TOKENS
                and value_tokens & SOURCE_PRESENT_ALIAS_STATE_TOKENS
            )
            key_claims_candidate = bool(
                key_tokens & CANDIDATE_PACK_ALIAS_TOKENS
                and key_tokens & SOURCE_PRESENT_ALIAS_STATE_TOKENS
                and split_alias_value_is_positive(child)
            )
            value_claims_candidate = bool(
                key_tokens & SOURCE_ALIAS_VALUE_KEYS
                and value_tokens & CANDIDATE_PACK_ALIAS_TOKENS
                and value_tokens & SOURCE_PRESENT_ALIAS_STATE_TOKENS
            )
            if key_claims_source or value_claims_source:
                source_paths.append(child_trail)
            if key_claims_candidate or value_claims_candidate:
                candidate_paths.append(child_trail)
            child_source_paths, child_candidate_paths = source_present_alias_paths(
                child,
                child_trail,
            )
            source_paths.extend(child_source_paths)
            candidate_paths.extend(child_candidate_paths)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            child_source_paths, child_candidate_paths = source_present_alias_paths(
                child,
                f"{trail}[{index}]",
            )
            source_paths.extend(child_source_paths)
            candidate_paths.extend(child_candidate_paths)
    return sorted(set(source_paths)), sorted(set(candidate_paths))


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


def lifecycle_role_alias_key_claims_role(value: object) -> bool:
    normalized = normalized_split_key(value)
    return any(role in normalized for role in REQUIRED_LIFECYCLE_ROLES)


def lifecycle_role_alias_value_claims_role(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_split_key(value)
        return any(role in normalized for role in REQUIRED_LIFECYCLE_ROLES)
    if isinstance(value, dict):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value.values())
    if isinstance(value, list):
        return any(lifecycle_role_alias_value_claims_role(child) for child in value)
    return False


def lifecycle_role_alias_value_has_material(value: Any) -> bool:
    if value in (False, None, [], {}):
        return False
    if isinstance(value, str):
        return normalized_split_key(value) not in {
            "blocked",
            "candidate",
            "context_only",
            "false",
            "missing",
            "no",
            "non_evidence",
            "none",
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
    tokens = split_alias_tokens(key)
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


def lifecycle_role_alias_claim_paths(value: Any, trail: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            if lifecycle_role_alias_claim_is_forbidden(key, child):
                paths.append(child_trail)
            paths.extend(lifecycle_role_alias_claim_paths(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(lifecycle_role_alias_claim_paths(child, f"{trail}[{index}]"))
    return sorted(set(paths))


def split_alias_claim_paths(value: Any, trail: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        names = [
            child
            for key, child in value.items()
            if normalized_split_key(key) in SPLIT_CLAIM_NAME_KEYS
            and isinstance(child, str)
        ]
        values = [
            child
            for key, child in value.items()
            if normalized_split_key(key) in SPLIT_CLAIM_VALUE_KEYS
        ]
        positive_value_present = not values or any(
            split_alias_value_is_positive(child) for child in values
        )
        if names and positive_value_present:
            for name in names:
                name_tokens = split_alias_tokens(name)
                if name_tokens & SPLIT_FORBIDDEN_CLAIM_TOKENS:
                    paths.append(trail)
                    break
        for key, child in value.items():
            child_trail = f"{trail}.{key}" if trail != "$" else f"$.{key}"
            paths.extend(split_alias_claim_paths(child, child_trail))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(split_alias_claim_paths(child, f"{trail}[{index}]"))
    return sorted(set(paths))


def split_zero_alias_value_is_zero(value: Any) -> bool:
    if value is None or value is False:
        return True
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if isinstance(value, str):
        return normalized_split_key(value) in {
            "",
            "0",
            "0_12",
            "0_4",
            "false",
            "no",
            "none",
        }
    return False


def split_direct_false_alias_key_is_forbidden(key: str) -> bool:
    normalized = normalized_split_key(key)
    if normalized in SPLIT_DIRECT_ALLOWED_POSITIVE_ALIAS_KEYS:
        return False
    if normalized in SPLIT_DIRECT_FALSE_ALIAS_KEYS:
        return True
    return (
        normalized.endswith("_ready")
        or normalized.endswith("_readiness")
        or normalized.endswith("_claim_allowed")
        or any(fragment in normalized for fragment in SPLIT_DIRECT_FALSE_ALIAS_FRAGMENTS)
    )


def split_direct_zero_alias_key_is_forbidden(key: str) -> bool:
    normalized = normalized_split_key(key)
    if normalized in SPLIT_DIRECT_ZERO_ALIAS_KEYS:
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


def split_direct_alias_claim_paths(value: Any, trail: str = "$") -> tuple[list[str], list[str]]:
    readiness_paths: list[str] = []
    progress_paths: list[str] = []

    def walk(current: Any, current_trail: str) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                if not isinstance(key, str):
                    continue
                child_trail = f"{current_trail}.{key}" if current_trail != "$" else f"$.{key}"
                if (
                    split_direct_false_alias_key_is_forbidden(key)
                    and split_alias_value_is_positive(child)
                ):
                    readiness_paths.append(child_trail)
                if (
                    split_direct_zero_alias_key_is_forbidden(key)
                    and not split_zero_alias_value_is_zero(child)
                ):
                    progress_paths.append(child_trail)
                if isinstance(child, (dict, list)):
                    walk(child, child_trail)
        elif isinstance(current, list):
            for index, child in enumerate(current):
                if isinstance(child, (dict, list)):
                    walk(child, f"{current_trail}[{index}]")

    walk(value, trail)
    return sorted(set(readiness_paths)), sorted(set(progress_paths))


def embedded_player_principal_evidence_split(closure: dict[str, Any]) -> dict[str, Any] | None:
    for key in (
        "player_principal_evidence_split",
        "player_principal_lifecycle_evidence_split",
        "principal_start_end_runtime_evidence",
        "principal_start_end_runtime_evidence_report",
        "runtime_principal_start_end_evidence",
    ):
        value = closure.get(key)
        if isinstance(value, dict) and value:
            return value
    return None


def player_principal_evidence_split_context(
    split_input: dict[str, Any] | None,
    closure: dict[str, Any],
) -> dict[str, Any]:
    payload = (
        split_input
        if isinstance(split_input, dict) and split_input
        else embedded_player_principal_evidence_split(closure)
    )
    if not isinstance(payload, dict):
        return {
            "schema": PLAYER_PRINCIPAL_EVIDENCE_SPLIT_SCHEMA,
            "present": False,
            "classification": "no_player_principal_evidence_split_input",
            "source_schema": None,
            "source_status": None,
            "start_end_contract_input_present": False,
            "start_end_contract_input_accepted": False,
            "session_start_rejected_required": True,
            "session_start_rejected_missing": True,
            "strict_approved_runtime_evidence_bundle_required": True,
            "next_actions": [],
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
        }

    source_schema = payload.get("schema")
    source_status = payload.get("status")
    blockers = string_list(payload.get("blockers"))
    strict_blockers = string_list(payload.get("strict_approved_runtime_evidence_blockers"))
    approved_blockers = string_list(payload.get("approved_runtime_evidence_blockers"))
    remaining_inputs = string_list(payload.get("remaining_runtime_inputs"))
    resolved_inputs = string_list(payload.get("resolved_inputs"))
    does_not_resolve = string_list(payload.get("does_not_resolve"))
    unresolved_cases = string_list(payload.get("unresolved_runtime_cases"))
    claim_object_overclaim_paths = split_alias_claim_paths(payload)
    direct_positive_alias_paths, direct_progress_alias_paths = split_direct_alias_claim_paths(payload)
    role_alias_claim_paths = lifecycle_role_alias_claim_paths(payload)
    overclaim_paths = sorted(
        set(
            claim_object_overclaim_paths
            + direct_positive_alias_paths
            + direct_progress_alias_paths
            + role_alias_claim_paths
        )
    )

    start_end_known_schema = source_schema == PLAYER_PRINCIPAL_START_END_EVIDENCE_SCHEMA
    start_end_contract_input_accepted = bool(
        start_end_known_schema
        and payload.get("ready") is True
        and payload.get("accepted_for_contract_review") is True
        and payload.get("principal_start_end_runtime_evidence_present") is True
        and payload.get("principal_start_end_runtime_evidence_ready") is True
        and payload.get("approved_runtime_evidence_present") is False
        and payload.get("approved_runtime_evidence_ready") is False
    )
    start_end_present = start_end_contract_input_accepted or bool(
        start_end_known_schema
        or "runtime.lifecycle_start_end_evidence" in resolved_inputs
        or payload.get("ready_scope") == "principal_start_end_runtime_evidence_only"
    )
    session_start_rejected_missing = bool(
        "runtime.lifecycle_rejected_start_evidence" in remaining_inputs
        or any("CheckJoinInProgress" in blocker for blocker in [*strict_blockers, *approved_blockers, *blockers])
        or any("session_start_rejected" in case for case in unresolved_cases)
    )
    strict_bundle_missing = bool(
        "approved_runtime_principal_lifecycle_evidence_bundle" in remaining_inputs
        or "approved_runtime_principal_lifecycle_evidence_bundle" in does_not_resolve
        or payload.get("approved_runtime_evidence_present") is not True
        or payload.get("approved_runtime_evidence_ready") is not True
    )
    split_blockers = [
        *blockers,
        *[blocker for blocker in strict_blockers if blocker not in blockers],
        *[blocker for blocker in approved_blockers if blocker not in blockers and blocker not in strict_blockers],
    ]
    if overclaim_paths:
        split_blockers.append("player_principal_evidence_split_positive_alias_claim")
    if role_alias_claim_paths:
        split_blockers.append("player_principal_evidence_split_lifecycle_role_alias_claim")
    if direct_positive_alias_paths or direct_progress_alias_paths:
        split_blockers.append("player_principal_evidence_split_direct_alias_overclaim")
    if start_end_present and not start_end_contract_input_accepted:
        split_blockers.append("principal_start_end_runtime_evidence_split_not_accepted")
    if session_start_rejected_missing:
        split_blockers.append("runtime.lifecycle_rejected_start_evidence_missing")
    if strict_bundle_missing:
        split_blockers.append("approved_runtime_principal_lifecycle_evidence_bundle_missing_or_unaccepted")

    if overclaim_paths:
        classification = "player_principal_evidence_split_overclaim_blocked_non_evidence"
    elif start_end_contract_input_accepted and session_start_rejected_missing:
        classification = "start_end_contract_input_present_rejected_start_missing_non_evidence"
    elif start_end_contract_input_accepted and strict_bundle_missing:
        classification = "start_end_contract_input_present_strict_bundle_missing_non_evidence"
    elif start_end_contract_input_accepted:
        classification = "start_end_contract_input_present_strict_checker_still_required_non_evidence"
    else:
        classification = "player_principal_evidence_split_input_blocked_non_evidence"

    next_actions: list[dict[str, Any]] = []
    if overclaim_paths:
        next_actions.append(
            {
                "action": "review_player_principal_evidence_split_overclaim_aliases_offline",
                "action_kind": "player_principal_evidence_split_overclaim_review",
                "items": overclaim_paths,
                "next_status_input_needed": "corrected_non_counting_player_principal_evidence_split_json",
            }
        )
    elif start_end_contract_input_accepted and session_start_rejected_missing:
        next_actions.append(
            {
                "action": "supply_exact_checkjoininprogress_session_start_rejected_for_strict_triplet",
                "action_kind": "player_principal_evidence_split_missing_rejected_start",
                "artifact": "lifecycle-role/session_start_rejected",
                "role": "session_start_rejected",
                "items": ["lifecycle-role/session_start_rejected"],
                "next_status_input_needed": "same_run_exact_CheckJoinInProgress_1_0_session_start_rejected",
                "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
            }
        )
    elif start_end_contract_input_accepted and strict_bundle_missing:
        next_actions.append(
            {
                "action": "complete_strict_three_role_bundle_and_checker_after_split_inputs",
                "action_kind": "player_principal_evidence_split_strict_bundle_required",
                "artifact": APPROVED_RUNTIME_EVIDENCE_JSON,
                "items": [APPROVED_RUNTIME_EVIDENCE_JSON],
                "next_status_input_needed": "checker_accepted_approved_runtime_principal_lifecycle_evidence_bundle",
            }
        )
    elif start_end_present:
        next_actions.append(
            {
                "action": "rebuild_or_review_player_principal_start_end_split_input_offline",
                "action_kind": "player_principal_evidence_split_input_review",
                "items": blockers,
                "next_status_input_needed": "accepted_principal_start_end_runtime_evidence_or_strict_triplet",
            }
        )

    false_flags = {
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "marker_env_changes_authorized": False,
        "workspace_writes_authorized": False,
        "discord_authorized": False,
        "publication_authorized": False,
        **sdk_p0_non_progress_flags(),
    }
    return {
        "schema": PLAYER_PRINCIPAL_EVIDENCE_SPLIT_SCHEMA,
        "present": True,
        "classification": classification,
        "source_schema": source_schema,
        "source_status": source_status,
        "source_ready": payload.get("ready") is True,
        "source_ready_scope": payload.get("ready_scope"),
        "accepted_for_contract_review_source_value": (
            payload.get("accepted_for_contract_review") is True
        ),
        "start_end_contract_input_present": start_end_present,
        "start_end_contract_input_accepted": start_end_contract_input_accepted,
        "resolved_inputs": resolved_inputs,
        "remaining_runtime_inputs": remaining_inputs,
        "does_not_resolve": does_not_resolve,
        "strict_approved_runtime_evidence_blockers": strict_blockers,
        "approved_runtime_evidence_blockers": approved_blockers,
        "source_blockers": blockers,
        "blockers": sorted(set(split_blockers)),
        "positive_alias_claim_paths": overclaim_paths,
        "claim_object_positive_alias_claim_paths": claim_object_overclaim_paths,
        "direct_positive_alias_claim_paths": direct_positive_alias_paths,
        "direct_progress_alias_claim_paths": direct_progress_alias_paths,
        "lifecycle_role_alias_claim_paths": role_alias_claim_paths,
        "components": {
            "principal_start_end_runtime_evidence": {
                "present": start_end_present,
                "accepted_for_contract_review": start_end_contract_input_accepted,
                "roles": ["session_start", "session_end"] if start_end_present else [],
                "resolved_input": "runtime.lifecycle_start_end_evidence"
                if start_end_contract_input_accepted
                else None,
                **false_flags,
            },
            "session_start_rejected": {
                "required": True,
                "present": not session_start_rejected_missing,
                "missing": session_start_rejected_missing,
                "role": "session_start_rejected",
                "target": "ShooterGameMode.CheckJoinInProgress",
                "required_shape": "CheckJoinInProgress(1,0)",
                "exact_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                **false_flags,
            },
            "strict_three_role_approved_bundle": {
                "required": True,
                "present": not strict_bundle_missing,
                "missing": strict_bundle_missing,
                "artifact": APPROVED_RUNTIME_EVIDENCE_JSON,
                **false_flags,
            },
        },
        "session_start_rejected_required": True,
        "session_start_rejected_missing": session_start_rejected_missing,
        "strict_approved_runtime_evidence_bundle_required": True,
        "strict_approved_runtime_evidence_bundle_missing": strict_bundle_missing,
        "split_input_authorizes_runtime": False,
        "split_input_authorizes_runner": False,
        "split_input_counts_as_approved_runtime_evidence": False,
        "next_actions": next_actions,
        "non_claims": [
            "player-principal evidence split context is consume-only offline metadata",
            "start/end-only runtime evidence does not satisfy the strict three-role lifecycle triplet",
            "CheckJoinInProgress(1,0) session_start_rejected and the approved bundle checker remain required before approved runtime evidence",
        ],
        **false_flags,
    }


def positive_int_counts(values: Any) -> dict[str, int]:
    if not isinstance(values, dict):
        return {}
    return {
        str(key): value
        for key, value in values.items()
        if isinstance(value, int) and value > 0
    }


def session_end_missing_correlation_diagnostics_from_analysis(
    analysis: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(analysis, dict):
        return None
    unsafe_reasons = {
        **positive_int_counts(analysis.get("unsafe_lifecycle_event_reasons")),
        **positive_int_counts(analysis.get("invalid_lifecycle_event_non_evidence_reasons")),
    }
    reason_keys = set(unsafe_reasons)
    missing_correlation_keys = reason_keys & SESSION_END_MISSING_CORRELATION_REASON_KEYS
    if not missing_correlation_keys:
        return None
    roles_present = string_list(analysis.get("roles_present"))
    accepted_count = int_token(analysis.get("accepted_lifecycle_event_count"))
    rejected_count = int_token(analysis.get("rejected_or_incomplete_role_event_count"))
    only_missing_correlation_logout = (
        (accepted_count in (None, 0))
        and (not roles_present or roles_present == ["session_end"])
        and reason_keys.issubset(SESSION_END_MISSING_CORRELATION_REASON_KEYS)
    )
    if not only_missing_correlation_logout:
        return None
    return {
        "classification": "session_end_missing_correlation_only_non_evidence",
        "copied_log_material": "session_end_only_without_matched_correlation",
        "accepted_lifecycle_event_count": accepted_count or 0,
        "rejected_or_incomplete_role_event_count": rejected_count or sum(unsafe_reasons.values()),
        "malformed_observer_lines": analysis.get("malformed_observer_lines"),
        "unsafe_lifecycle_event_reasons": {
            key: unsafe_reasons[key] for key in sorted(missing_correlation_keys)
        },
        "roles_present": ["session_end"],
        "missing_accepted_lifecycle_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "required_next_material": {
            "same_run_exact_triplet_required": True,
            "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
            "required_session_end_status_proof": {
                "apply_status": "session_end_invalidated",
                "correlation_status": "matched",
            },
            "session_end_correlation_status_missing_counts_as_evidence": False,
        },
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
    }


def jsonable_triplet_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": case["label"],
        "role": case["role"],
        "target": case["target"],
        "post_original": case["post_original"],
        "copied_bool_fields": list(case["copied_bool_fields"]),
        "copied_bool_values": list(case["copied_bool_values"]),
        "redacted_count": case["redacted_count"],
        "redacted_fields": list(case["redacted_fields"]),
        "apply_status": case["apply_status"],
        "principal_action": case["principal_action"],
        "correlation_status": case["correlation_status"],
        "principal_id_logged": case["principal_id_logged"],
        "principal_generation_logged": case["principal_generation_logged"],
        "delivery_claim": case["delivery_claim"],
    }


def required_copied_lifecycle_event_triplet() -> list[dict[str, Any]]:
    return [
        jsonable_triplet_case(case)
        for case in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET
    ]


def triplet_case_matches(observed: dict[str, Any], expected: dict[str, Any]) -> bool:
    return (
        observed.get("role") == expected["role"]
        and observed.get("target") == expected["target"]
        and observed.get("post_original") == expected["post_original"]
        and tuple(string_list(observed.get("copied_bool_fields"))) == tuple(expected["copied_bool_fields"])
        and tuple(string_list(observed.get("copied_bool_values"))) == tuple(expected["copied_bool_values"])
        and observed.get("redacted_count") == expected["redacted_count"]
        and tuple(string_list(observed.get("redacted_fields"))) == tuple(expected["redacted_fields"])
        and observed.get("apply_status") == expected["apply_status"]
        and observed.get("principal_action") == expected["principal_action"]
        and observed.get("correlation_status") == expected["correlation_status"]
        and observed.get("principal_id_logged") == expected["principal_id_logged"]
        and observed.get("principal_generation_logged") == expected["principal_generation_logged"]
        and observed.get("delivery_claim") == expected["delivery_claim"]
    )


def closure_exact_triplet_state(closure: dict[str, Any]) -> dict[str, Any]:
    role_state = closure.get("lifecycle_event_role_state")
    if not isinstance(role_state, dict):
        return {
            "present": False,
            "complete": False,
            "source_complete": False,
            "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "required_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "matched_copied_lifecycle_event_triplet": [],
            "missing_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "missing_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "copied_lifecycle_triplet_match_failures": [],
            "blockers": [
                {
                    "reason": "closure_exact_copied_triplet_state_missing",
                    "accepted_by_status_report": False,
                    "counts_as_approved_runtime_evidence": False,
                }
            ],
        }

    matched_cases = object_list(role_state.get("matched_copied_lifecycle_event_triplet"))
    failures = object_list(role_state.get("copied_lifecycle_triplet_match_failures"))
    missing_cases: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    for expected in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET:
        if any(triplet_case_matches(observed, expected) for observed in matched_cases):
            continue
        missing = jsonable_triplet_case(expected)
        missing_cases.append(missing)
        blockers.append(
            {
                "reason": "exact_copied_lifecycle_event_triplet_case_missing",
                "label": expected["label"],
                "role": expected["role"],
                "target": expected["target"],
                "copied_bool_values": list(expected["copied_bool_values"]),
                "accepted_by_status_report": False,
                "counts_as_approved_runtime_evidence": False,
            }
        )
    source_complete = (
        role_state.get("exact_copied_lifecycle_event_triplet_complete") is True
        or closure.get("exact_copied_lifecycle_event_triplet_complete") is True
    )
    if source_complete and missing_cases:
        blockers.append(
            {
                "reason": "source_exact_triplet_complete_missing_required_cases",
                "accepted_by_status_report": False,
                "counts_as_approved_runtime_evidence": False,
            }
        )
    if failures:
        blockers.append(
            {
                "reason": "source_exact_triplet_match_failures_present",
                "failure_count": len(failures),
                "accepted_by_status_report": False,
                "counts_as_approved_runtime_evidence": False,
            }
        )
    return {
        "present": True,
        "complete": source_complete and not missing_cases and not failures,
        "source_complete": source_complete,
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "matched_copied_lifecycle_event_triplet": matched_cases,
        "missing_copied_lifecycle_event_triplet": missing_cases,
        "missing_copied_lifecycle_event_triplet_labels": [
            str(case["label"]) for case in missing_cases
        ],
        "copied_lifecycle_triplet_match_failures": failures,
        "blockers": blockers,
    }


def closure_blocking_inputs(closure: dict[str, Any]) -> dict[str, Any]:
    invalid_sidecars = string_list(closure.get("invalid_sidecars"))
    missing_roles = string_list(closure.get("missing_lifecycle_event_roles"))
    missing_required = string_list(closure.get("missing_required_artifacts"))
    missing_siblings = string_list(closure.get("missing_siblings"))
    sidecar_blockers = object_list(closure.get("sidecar_validation_blockers"))
    evidence_source_blockers = object_list(closure.get("evidence_source_blockers"))
    input_blockers = object_list(closure.get("input_blockers"))
    exact_triplet = closure_exact_triplet_state(closure)
    missing_triplet_labels = string_list(
        exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
    )
    triplet_blockers = object_list(exact_triplet.get("blockers"))
    return {
        "invalid_sidecars": invalid_sidecars,
        "missing_lifecycle_event_roles": missing_roles,
        "missing_copied_lifecycle_event_triplet": exact_triplet.get(
            "missing_copied_lifecycle_event_triplet", []
        ),
        "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
        "copied_lifecycle_triplet_match_failures": exact_triplet.get(
            "copied_lifecycle_triplet_match_failures", []
        ),
        "exact_copied_lifecycle_event_triplet_complete": exact_triplet.get("complete") is True,
        "exact_copied_lifecycle_event_triplet_blockers": triplet_blockers,
        "missing_required_artifacts": missing_required,
        "missing_siblings": missing_siblings,
        "runtime_evidence_artifact_blockers": runtime_evidence_artifact_blockers(
            closure,
            exact_triplet,
        ),
        "sidecar_validation_blockers": sidecar_blockers,
        "evidence_source_blockers": evidence_source_blockers,
        "input_blockers": input_blockers,
        "has_invalid_sidecars": bool(invalid_sidecars or sidecar_blockers),
        "has_missing_roles": bool(missing_roles),
        "has_missing_exact_triplet": bool(missing_triplet_labels or triplet_blockers),
        "has_missing_artifacts": bool(missing_required or missing_siblings),
        "has_invalid_source": bool(evidence_source_blockers or input_blockers),
        "has_blockers": bool(
            invalid_sidecars
            or missing_roles
            or missing_triplet_labels
            or triplet_blockers
            or missing_required
            or missing_siblings
            or sidecar_blockers
            or evidence_source_blockers
            or input_blockers
        ),
    }


def append_unique_strings(items: list[str], values: list[str]) -> None:
    for value in values:
        if value and value not in items:
            items.append(value)


def closure_missing_artifacts(closure: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    append_unique_strings(missing, string_list(closure.get("missing_required_artifacts")))
    append_unique_strings(missing, string_list(closure.get("missing_siblings")))
    return missing


def ordered_missing_artifacts(closure: dict[str, Any]) -> list[str]:
    missing = closure_missing_artifacts(closure)
    ordered = [artifact for artifact in CRITICAL_RUNTIME_EVIDENCE_ARTIFACTS if artifact in missing]
    ordered.extend(artifact for artifact in missing if artifact not in ordered)
    return ordered


def artifact_output_path(closure: dict[str, Any], artifact: str) -> str | None:
    evidence_dir = closure.get("evidence_dir")
    if not isinstance(evidence_dir, str) or not evidence_dir:
        return None
    return str(Path(evidence_dir) / artifact)


def artifact_blocker_reason(artifact: str) -> str:
    return ARTIFACT_BLOCKER_REASONS.get(artifact, "required_sibling_artifact_missing")


def artifact_blocked_until(
    artifact: str,
    exact_triplet: dict[str, Any],
) -> list[str]:
    blocked_until = list(ARTIFACT_BLOCKED_UNTIL.get(artifact, []))
    if exact_triplet.get("complete") is not True:
        labels = string_list(exact_triplet.get("missing_copied_lifecycle_event_triplet_labels"))
        for label in labels:
            value = f"copied-lifecycle-triplet/{label}"
            if value not in blocked_until:
                blocked_until.insert(0, value)
    return blocked_until


def artifact_blocker_detail(
    closure: dict[str, Any],
    exact_triplet: dict[str, Any],
    artifact: str,
) -> dict[str, Any]:
    detail = dict(ARTIFACT_BLOCKER_DETAILS.get(artifact, {}))
    reason = artifact_blocker_reason(artifact)
    exact_complete = exact_triplet.get("complete") is True
    required_script = ARTIFACT_REQUIRED_SCRIPTS.get(artifact) if exact_complete else None
    return {
        "artifact": artifact,
        "reason": reason,
        "action": ARTIFACT_ACTIONS.get(artifact, "provide_missing_required_sibling"),
        "required_script": required_script,
        "path": artifact_output_path(closure, artifact),
        "blocked_until": artifact_blocked_until(artifact, exact_triplet),
        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
        "exact_copied_lifecycle_event_triplet_complete": exact_complete,
        "runner_command_available": detail.get("runner_command_available") is True,
        "side_effect_domain": detail.get("side_effect_domain", "offline_sibling_artifact"),
        "command_text_not_emitted": detail.get("command_text_not_emitted"),
        "next_step": detail.get("next_step", "provide the missing required sibling artifact"),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def runtime_evidence_artifact_blockers(
    closure: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> dict[str, Any]:
    missing = ordered_missing_artifacts(closure)
    missing_set = set(missing)
    missing_blockers = [
        artifact_blocker_detail(closure, exact_triplet, artifact)
        for artifact in missing
    ]
    path_status: list[dict[str, Any]] = []
    prior_missing: list[str] = []
    for artifact in CRITICAL_RUNTIME_EVIDENCE_ARTIFACTS:
        missing_now = artifact in missing_set
        detail = artifact_blocker_detail(closure, exact_triplet, artifact)
        path_status.append(
            {
                **detail,
                "status": "missing" if missing_now else "not_reported_missing_by_closure",
                "blocked_by_prior_missing_artifacts": list(prior_missing),
            }
        )
        if missing_now:
            prior_missing.append(artifact)
    first = missing_blockers[0] if missing_blockers else None
    return {
        "schema": RUNTIME_EVIDENCE_ARTIFACT_BLOCKERS_SCHEMA,
        "status": "blocked_missing_runtime_evidence_artifacts" if missing_blockers else "no_missing_runtime_evidence_artifacts_reported",
        "missing_artifacts": missing,
        "missing_artifact_blockers": missing_blockers,
        "missing_artifact_reasons": [blocker["reason"] for blocker in missing_blockers],
        "first_missing_artifact": first["artifact"] if first else None,
        "first_blocker_reason": first["reason"] if first else None,
        "fastest_exact_path_from_fresh_copied_lifecycle_window": path_status,
        "approved_runtime_principal_lifecycle_evidence_bundle_json": APPROVED_RUNTIME_EVIDENCE_JSON,
        "approved_runtime_principal_lifecycle_evidence_bundle_ready": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def closure_copy_guidance(closure: dict[str, Any]) -> dict[str, Any]:
    source_state = closure.get("evidence_source_state")
    if isinstance(source_state, dict):
        guidance = source_state.get("closure_compatible_copy_guidance")
        if isinstance(guidance, dict):
            return guidance
    for blocker in object_list(closure.get("evidence_source_blockers")):
        guidance = blocker.get("closure_compatible_copy_guidance")
        if isinstance(guidance, dict):
                return guidance
    return {}


def guidance_suggested_closure_dir(guidance: dict[str, Any]) -> Any:
    return guidance.get("suggested_valid_closure_evidence_dir") or guidance.get(
        "suggested_closure_evidence_dir"
    )


def guidance_suggested_closure_run_id(guidance: dict[str, Any]) -> Any:
    return guidance.get("suggested_valid_closure_run_id") or guidance.get(
        "suggested_closure_run_id"
    )


def action_is_invalid_passive_root(action: dict[str, Any]) -> bool:
    if (
        action.get("missing_kind") != "invalid_evidence_source"
        and action.get("action_kind") != "invalid_evidence_source"
    ):
        return False
    guidance = action.get("closure_compatible_copy_guidance")
    if isinstance(guidance, dict) and guidance.get("source_looks_like_passive_monitor_root") is True:
        return True
    return bool(
        action.get("source_looks_like_passive_monitor_root") is True
        or action.get("passive_monitor_root_accepted_as_closure_evidence_dir") is False
        and action.get("copy_or_stage_into_closure_compatible_run_required_before_closure") is True
        and "passive" in str(action.get("source_evidence_dir") or action.get("artifact") or "").casefold()
    )


def invalid_passive_root_manual_fields(action: dict[str, Any]) -> dict[str, Any]:
    guidance = action.get("closure_compatible_copy_guidance")
    if not isinstance(guidance, dict):
        guidance = {}
    source_dir = action.get("source_evidence_dir") or action.get("invalid_source_evidence_dir")
    suggested_dir = (
        action.get("suggested_valid_closure_evidence_dir")
        or action.get("suggested_closure_evidence_dir")
        or action.get("closure_compatible_evidence_dir")
        or guidance_suggested_closure_dir(guidance)
    )
    suggested_run_id = action.get("suggested_valid_closure_run_id") or guidance_suggested_closure_run_id(
        guidance
    )
    return {
        "source_evidence_dir": source_dir,
        "invalid_source_evidence_dir": action.get("invalid_source_evidence_dir") or source_dir,
        "source_root_role": action.get(
            "source_root_role",
            guidance.get("source_root_role", "source_evidence_root_supplied_to_closure_helper"),
        ),
        "source_run_id": action.get("source_run_id") or guidance.get("source_run_id"),
        "source_root_valid_for_closure": False,
        "source_looks_like_passive_monitor_root": True,
        "closure_compatible_evidence_dir": suggested_dir,
        "suggested_closure_evidence_dir": suggested_dir,
        "suggested_valid_closure_run_id": suggested_run_id,
        "suggested_valid_closure_evidence_dir": suggested_dir,
        "suggested_valid_closure_root_role": action.get(
            "suggested_valid_closure_root_role",
            guidance.get(
                "suggested_valid_closure_root_role",
                "suggested_valid_closure_root_for_manual_staging",
            ),
        ),
        "source_accepted_as_closure_evidence_dir": False,
        "source_becomes_closure_root": False,
        "passive_monitor_root_accepted_as_closure_evidence_dir": False,
        "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
        "explicit_execution_write_flags_required": True,
        "machine_action_suggested_for_invalid_passive_root": False,
        "machine_executable": False,
        "runner_command_available": False,
        "manual_staging_required_before_machine_actions": True,
        "command_status": "NOT PROVIDED",
        "command_text_not_emitted": (
            "stage exact copied Obelisk.log and required sibling sidecars into the "
            "suggested closure-compatible lifecycle evidence directory before rerunning closure"
        ),
        "manual_offline_next_steps": action.get(
            "manual_offline_next_steps",
            [
                "do not use the passive monitor root as --evidence-dir for closure",
                "stage a valid YYYYMMDDThhmmssZ-player-principal-lifecycle root with the copied log and required sidecars",
                "rerun the closure helper against that valid root before deriving role or checker actions",
            ],
        ),
        "deferred_missing_role_offline_next_steps": action.get(
            "deferred_missing_role_offline_next_steps",
            [],
        ),
    }


def closure_ready_for_checker(closure: dict[str, Any], closure_schema: dict[str, Any]) -> bool:
    return (
        closure_schema.get("valid") is True
        and closure.get("ready") is True
        and closure_exact_triplet_state(closure).get("complete") is True
        and closure_blocking_inputs(closure)["has_blockers"] is False
    )


def closure_ready_for_status_checker(
    closure: dict[str, Any],
    closure_schema: dict[str, Any],
    copy_ready_context: dict[str, Any],
) -> bool:
    exact_triplet = closure_exact_triplet_state(closure)
    if stale_passive_complete_role_triplet_non_evidence(copy_ready_context, exact_triplet):
        return False
    return closure_ready_for_checker(closure, closure_schema)


def run_json_command(argv: list[str], *, allow_nonzero: bool = False) -> tuple[dict[str, Any], int, str]:
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0 and not allow_nonzero:
        raise SystemExit(
            f"command failed with rc={result.returncode}: {' '.join(argv)}\nstderr={result.stderr}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"failed to parse JSON from {' '.join(argv)}: {exc}\nstderr={result.stderr}"
        ) from exc
    return payload, result.returncode, result.stderr


def load_or_run_closure(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.closure_json:
        return load_json(args.closure_json), 0
    if args.evidence_dir is None:
        if status_only_context_requested(args):
            return status_only_closure_context(), 0
        raise SystemExit("--evidence-dir is required when --closure-json is not supplied")
    argv = [
        sys.executable,
        str(CLOSURE_REQUEST),
        "--evidence-dir",
        str(args.evidence_dir),
        "--format",
        "json",
    ]
    for flag, value in (
        ("--instance", args.instance),
        ("--map", args.map_name),
        ("--query-port", args.query_port),
        ("--notice-path", args.notice_path),
        ("--post-reboot-monitor-log", args.post_reboot_monitor_log),
        ("--confirmed-beta-notice-json", args.confirmed_beta_notice_json),
    ):
        if value:
            argv.extend([flag, str(value)])
    for flag, enabled in (
        ("--the-island-off", args.the_island_off),
        ("--two-server-cap-preserved", args.two_server_cap_preserved),
        ("--future-window-needs-players", args.future_window_needs_players),
    ):
        if enabled:
            argv.append(flag)
    payload, returncode, _stderr = run_json_command(argv, allow_nonzero=True)
    return payload, returncode


def status_only_context_requested(args: argparse.Namespace) -> bool:
    return bool(
        args.player_principal_evidence_split_json
        or args.passive_summary_json
        or args.monitor_log
        or args.post_reboot_monitor_log
        or args.confirmed_beta_notice_json
        or args.copy_ready_json
    )


def status_only_closure_context() -> dict[str, Any]:
    return {
        "schema": STATUS_ONLY_CLOSURE_CONTEXT_SCHEMA,
        "status": "closure_json_not_supplied_status_only_context",
        "closure_case": "status_only_context_without_closure_json_or_evidence_dir",
        "ready": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "missing_required_artifacts": list(APPROVED_RUNTIME_EVIDENCE_EXACT_SIBLING_SET),
        "missing_siblings": [],
        "missing_lifecycle_event_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "input_blockers": [
            {
                "reason": "closure_json_or_evidence_dir_not_supplied",
                "status_only_context": True,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
            }
        ],
        "lifecycle_event_role_state": {
            "matched_copied_lifecycle_event_triplet": [],
            "missing_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
            "missing_copied_lifecycle_event_triplet_labels": list(
                REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
            ),
            "copied_lifecycle_triplet_match_failures": [],
            "exact_copied_lifecycle_event_triplet_complete": False,
        },
        "exact_copied_lifecycle_event_triplet_complete": False,
        "machine_next_actions_schema": "obelisk.player-principal-lifecycle-closure-machine-next-actions.v1",
        "machine_next_actions": [],
    }


def load_or_run_passive_summary(args: argparse.Namespace) -> tuple[dict[str, Any] | None, int | None]:
    if args.passive_summary_json:
        return load_json(args.passive_summary_json), 0
    if args.monitor_log is None and args.snapshot_root is None:
        return None, None
    if args.monitor_log is None:
        raise SystemExit("--monitor-log is required when --snapshot-root is supplied")
    if args.snapshot_root is None:
        return None, None
    payload, returncode, _stderr = run_json_command(
        [
            sys.executable,
            str(PASSIVE_SUMMARY),
            "--latest",
            "--monitor-log",
            str(args.monitor_log),
            str(args.snapshot_root),
        ],
        allow_nonzero=False,
    )
    return payload, returncode


def monitor_context_path(args: argparse.Namespace) -> Path | None:
    return args.post_reboot_monitor_log or args.monitor_log


def load_or_run_route_gate(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.route_gate_json:
        return load_json(args.route_gate_json), 0
    payload, returncode, _stderr = run_json_command(
        [sys.executable, str(ROUTE_GATE), "--json"],
        allow_nonzero=False,
    )
    return payload, returncode


def token_dict(line: str) -> tuple[str, dict[str, str]]:
    try:
        tokens = shlex.split(line)
    except ValueError:
        tokens = line.split()
    if not tokens:
        return "", {}
    values: dict[str, str] = {}
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        values[key] = value
    return tokens[0], values


def target_key_for_values(values: dict[str, str]) -> str | None:
    target_key = values.get("target_key")
    if isinstance(target_key, str) and target_key:
        return target_key
    instance = values.get("instance")
    game_map = values.get("map")
    query_port = values.get("query_port")
    if instance and game_map and query_port:
        return f"{instance}:{game_map}:{query_port}"
    if instance and game_map:
        return f"{instance}:{game_map}"
    return None


def bool_token(value: Any) -> bool:
    return str(value).lower() == "true"


def int_token(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def target_policy(instance: str | None, game_map: str | None) -> dict[str, Any]:
    target = (instance or "", game_map or "")
    allowed = target in ALLOWED_OPERATOR_CONTEXT_TARGETS
    ragnarok_auxiliary = target == ("arkserver", "Ragnarok")
    return {
        "allowed_current_runtime_context_target": allowed,
        "allowed_targets": [
            {"instance": instance_name, "map": map_name}
            for instance_name, map_name in sorted(ALLOWED_OPERATOR_CONTEXT_TARGETS)
        ],
        "ragnarok_auxiliary_diagnostic_non_evidence": ragnarok_auxiliary,
        "diagnostic_non_evidence": True,
        "accepted_copied_sibling_bundle_present": False,
        "accepted_copied_sibling_bundle_required_before_evidence": True,
        "treat_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        **sdk_p0_non_progress_flags(),
        "classification": (
            "ragnarok_auxiliary_target_diagnostic_non_evidence"
            if ragnarok_auxiliary
            else (
                "approved_target_operator_context_non_evidence"
                if allowed
                else "out_of_scope_target_diagnostic_non_evidence"
            )
        ),
    }


def empty_monitor_context() -> dict[str, Any]:
    return {
        "present": False,
        "source_path": None,
        "monitor_latest_tick_utc": None,
        "query_status_by_target": {},
        "rcon_status_by_target": {},
        "trusted_source_discrepancies_by_target": {},
        "discrepant_sources_by_target": {},
        "targets": {},
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def monitor_record_presence_signal(record: dict[str, Any] | None) -> str:
    if not isinstance(record, dict):
        return "absent"
    count = record.get("players_current")
    if isinstance(count, bool):
        return "unknown"
    if isinstance(count, int):
        if count > 0:
            return "present"
        if (
            count == 0
            and record.get("status") == "ok"
            and record.get("presence_detected") is not True
        ):
            return "zero"
    if record.get("presence_detected") is True:
        return "present"
    return "unknown"


def monitor_source_discrepancy_record(
    target: str,
    query_record: dict[str, Any] | None,
    rcon_record: dict[str, Any] | None,
) -> dict[str, Any] | None:
    query_signal = monitor_record_presence_signal(query_record)
    rcon_signal = monitor_record_presence_signal(rcon_record)
    if query_signal == "zero" and rcon_signal == "present":
        discrepant_sources = [
            "gamedig_ase_query_zero",
            "rcon_listplayers_redacted_present",
        ]
        classification = "rcon_present_query_zero_trusted_source_discrepancy_non_evidence"
    elif query_signal == "present" and rcon_signal == "zero":
        discrepant_sources = [
            "gamedig_ase_query_present",
            "rcon_listplayers_redacted_zero",
        ]
        classification = "query_present_rcon_zero_trusted_source_discrepancy_non_evidence"
    else:
        return None
    return {
        "target_key": target,
        "query_signal": query_signal,
        "rcon_signal": rcon_signal,
        "source_discrepancy_detected": True,
        "discrepant_sources": discrepant_sources,
        "classification": classification,
        "operator_context_only": True,
        "diagnostic_non_evidence": True,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "authorizes_runtime_capture": False,
        "authorizes_server_operations": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def monitor_operator_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return empty_monitor_context()

    latest_tick_utc: str | None = None
    latest_query_by_target: dict[str, dict[str, Any]] = {}
    latest_rcon_by_target: dict[str, dict[str, Any]] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        record_type, values = token_dict(line)
        if record_type == "tick" and isinstance(values.get("utc"), str):
            latest_tick_utc = values["utc"]
            continue
        if record_type not in {"query", "rcon_listplayers"}:
            continue
        key = target_key_for_values(values)
        if not key:
            continue
        instance = values.get("instance")
        game_map = values.get("map")
        current = {
            "line_number": line_number,
            "record_type": record_type,
            "target_key": key,
            "instance": instance,
            "map": game_map,
            "query_port": values.get("query_port"),
            "status": values.get("status"),
            "rc": values.get("rc"),
            "error": values.get("error"),
            "reason": values.get("reason"),
            "current_map": values.get("current_map"),
            "players": values.get("players"),
            "players_current": int_token(values.get("players_current")),
            "players_max": int_token(values.get("players_max")),
            "presence_detected": bool_token(values.get("presence_detected")),
            "detection_source": values.get("detection_source"),
            "monitor_latest_tick_utc": latest_tick_utc,
            "source_path": str(path),
            "operator_context_only": True,
            **target_policy(instance, game_map),
            **sdk_p0_non_progress_flags(),
        }
        if record_type == "query":
            latest_query_by_target[key] = current
        else:
            current["rcon_port"] = values.get("rcon_port")
            current["rcon_output_redacted"] = bool_token(values.get("rcon_output_redacted"))
            latest_rcon_by_target[key] = current

    trusted_source_discrepancies_by_target: dict[str, dict[str, Any]] = {}
    for target in sorted(set(latest_query_by_target) & set(latest_rcon_by_target)):
        discrepancy = monitor_source_discrepancy_record(
            target,
            latest_query_by_target.get(target),
            latest_rcon_by_target.get(target),
        )
        if discrepancy is not None:
            trusted_source_discrepancies_by_target[target] = discrepancy

    return {
        "present": True,
        "source_path": str(path),
        "line_count": len(lines),
        "monitor_latest_tick_utc": latest_tick_utc,
        "query_status_by_target": latest_query_by_target,
        "rcon_status_by_target": latest_rcon_by_target,
        "trusted_source_discrepancies_by_target": trusted_source_discrepancies_by_target,
        "discrepant_sources_by_target": {
            target: record["discrepant_sources"]
            for target, record in trusted_source_discrepancies_by_target.items()
        },
        "trusted_source_discrepancy_count": len(trusted_source_discrepancies_by_target),
        "trusted_source_discrepancies_count_as_approved_runtime_evidence": False,
        "trusted_source_discrepancies_authorize_server_operations": False,
        "targets": latest_query_by_target,
        "operator_context_only": True,
        "diagnostic_non_evidence": True,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def confirmed_beta_notice_context(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "present": False,
            "source_path": None,
            "source_is_notice_action_sidecar": False,
            "sidecar_validation_blockers": [],
            "completed": False,
            "standing_launch_authority_recorded": False,
            "standing_launch_authority_satisfies_notice_scope": False,
            "notice_action_covered_by_standing_launch_authority": False,
            "sidecar_non_evidence_flags": SIDECAR_NON_EVIDENCE_FLAGS,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "standing_authority_counts_as_runtime_progress": False,
            "standing_authority_counts_as_sdk_progress": False,
            "standing_authority_grants_runtime_readiness": False,
            **sdk_p0_non_progress_flags(),
        }
    loaded = load_json(path)
    sidecar_validation_blockers: list[str] = []
    source_is_sidecar = loaded.get("schema") == NOTICE_ACTION_ARTIFACT_SCHEMA
    if source_is_sidecar:
        embedded = loaded.get("notice_report")
        if not isinstance(embedded, dict):
            sidecar_validation_blockers.append("notice_action_sidecar_notice_report_missing")
            notice: dict[str, Any] = {}
        else:
            notice = embedded
            if loaded.get("notice_report_sha256") != canonical_json_sha256(embedded):
                sidecar_validation_blockers.append("notice_action_sidecar_notice_report_sha256_mismatch")
            for key in ("mode", "ready", "target", "run_id", "notice_path", "request_json"):
                if loaded.get(key) != embedded.get(key):
                    sidecar_validation_blockers.append(f"notice_action_sidecar_{key}_mismatch")
            if loaded.get("artifact_contains_full_sanitized_notice_report") is not True:
                sidecar_validation_blockers.append("notice_action_sidecar_full_report_not_embedded")
            if loaded.get("sidecar_required_for_confirmed_send_consumption") is not True:
                sidecar_validation_blockers.append("notice_action_sidecar_required_flag_missing")
            if loaded.get("stdout_only_confirmation_accepted") is not False:
                sidecar_validation_blockers.append("notice_action_sidecar_stdout_only_not_false")
            if loaded.get("discord_send_performed_by_artifact_write") is not False:
                sidecar_validation_blockers.append("notice_action_sidecar_discord_send_by_artifact_not_false")
            for key, expected in SIDECAR_NON_EVIDENCE_FLAGS.items():
                if loaded.get(key) is not expected:
                    sidecar_validation_blockers.append(f"notice_action_sidecar_{key}_mismatch")
    else:
        notice = loaded
    guarded = notice.get("guarded_beta_notice_action")
    if not isinstance(guarded, dict):
        guarded = {}
    boundary = notice.get("notice_authority_boundary")
    if not isinstance(boundary, dict):
        boundary = {}
    completed = (
        not sidecar_validation_blockers
        and notice.get("schema") == CONFIRMED_BETA_NOTICE_SCHEMA
        and notice.get("mode") == "confirmed_send"
        and (
            notice.get("discord_sent") is True
            or guarded.get("real_beta_test_notice_action_completed") is True
        )
    )
    standing_recorded = (
        notice.get("standing_launch_authority_recorded") is True
        or guarded.get("standing_launch_authority_recorded") is True
        or boundary.get("standing_launch_authority_recorded") is True
    )
    standing_scope = (
        notice.get("standing_launch_authority_satisfies_notice_scope") is True
        or guarded.get("standing_launch_authority_satisfies_notice_scope") is True
        or boundary.get("standing_launch_authority_satisfies_notice_scope") is True
    )
    return {
        "present": True,
        "source_path": str(path),
        "source_is_notice_action_sidecar": source_is_sidecar,
        "sidecar_validation_blockers": sidecar_validation_blockers,
        "sidecar_valid_for_context": source_is_sidecar and not sidecar_validation_blockers,
        "schema": notice.get("schema"),
        "schema_matches_beta_notice_report": notice.get("schema") == CONFIRMED_BETA_NOTICE_SCHEMA,
        "mode": notice.get("mode"),
        "completed": completed,
        "completion_status": "confirmed_beta_notice_completed" if completed else "not_confirmed",
        "discord_sent_source_value": notice.get("discord_sent") is True,
        "send_helper_returncode_zero": notice.get("send_helper_returncode_zero") is True,
        "target": notice.get("target") if isinstance(notice.get("target"), dict) else {},
        "run_id": notice.get("run_id"),
        "notice_path": notice.get("notice_path"),
        "standing_launch_authority_recorded": standing_recorded,
        "standing_launch_authority_satisfies_notice_scope": standing_scope,
        "notice_action_covered_by_standing_launch_authority": (
            notice.get("notice_action_covered_by_standing_launch_authority") is True
            or guarded.get("notice_action_covered_by_standing_launch_authority") is True
        ),
        "sidecar_non_evidence_flags": SIDECAR_NON_EVIDENCE_FLAGS,
        "confirmed_send_authorizes_activation": False,
        "confirmed_send_authorizes_runtime_capture": False,
        "confirmed_send_authorizes_server_operations": False,
        "discord_authorized_by_this_report": False,
        "authorized_by_this_report": False,
        "operator_context_only": True,
        "accepted_as_activation_notice": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "publication_authorized": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
        **sdk_p0_non_progress_flags(),
    }


def copy_ready_log_context(path: Path | None) -> dict[str, Any]:
    empty_source_log_not_ready = {
        "present": False,
        "schema": "obelisk.player-principal-lifecycle-source-log-not-ready.v1",
        "classification": "copy_ready_json_not_supplied",
        "active_observer_only_no_role_window": False,
        "source_log_not_ready": False,
        "target_hint": {},
        "manual_offline_next_steps": [],
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }
    if path is None:
        return {
            "present": False,
            "source_path": None,
            "status": None,
            "copy_readiness": None,
            "ready_to_copy": False,
            "copied": False,
            "missing_roles": [],
            "roles_present": [],
            "source_log_not_ready": empty_source_log_not_ready,
            "observer_only_no_role_window": empty_source_log_not_ready,
            "active_observer_only_no_role_window": False,
            "source_log_not_ready_classification": "copy_ready_json_not_supplied",
            "manual_offline_next_steps": [],
            "observer_only_no_role_window_detected": False,
            "post_window_observer_only_no_role_window": False,
            "window_state": None,
            "fresh_window": {},
            "accepted_lifecycle_event_count": 0,
            "rejected_or_incomplete_role_event_count": 0,
            "rejected_or_incomplete_role_events": [],
            "exact_copied_runtime_triplet": {},
            "exact_copied_runtime_triplet_accepted": False,
            "diagnostic_or_rejected_lifecycle_lines": False,
            "diagnostic_only_lifecycle_lines": False,
            "artifact_hash_path_bindings": {},
            "copied_log_hash_path_binding": {},
            "sibling_sidecar_hash_path_bindings": [],
            "copied_log_hash_path_bound": False,
            "sibling_sidecars_hash_path_bound": False,
            "artifact_hash_path_bindings_count_as_approved_runtime_evidence": False,
            "source_present_alias_paths": [],
            "candidate_pack_alias_paths": [],
            "source_present_alias_detected": False,
            "candidate_pack_alias_detected": False,
            "source_present_aliases_count_as_approved_runtime_evidence": False,
            "candidate_pack_aliases_count_as_approved_runtime_evidence": False,
            "operator_context_only": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            "v1_completion_ready": False,
            "publication_authorized": False,
            **sdk_p0_non_progress_flags(),
        }
    copy_ready = load_json(path)
    analysis = copy_ready.get("analysis")
    if not isinstance(analysis, dict):
        analysis = {}
    source_log_not_ready = copy_ready.get("source_log_not_ready")
    if not isinstance(source_log_not_ready, dict):
        source_log_not_ready = copy_ready.get("observer_only_no_role_window")
    if not isinstance(source_log_not_ready, dict):
        source_log_not_ready = {
            **empty_source_log_not_ready,
            "present": True,
            "classification": "source_log_not_ready_metadata_missing",
        }
    source_log_not_ready = {
        **source_log_not_ready,
        "present": True,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }
    roles_present = string_list(copy_ready.get("roles_present"))
    analysis_roles_present = string_list(analysis.get("roles_present"))
    if not roles_present and analysis_roles_present:
        roles_present = analysis_roles_present
    missing_roles = string_list(copy_ready.get("missing_roles"))
    analysis_missing_roles = string_list(analysis.get("missing_roles"))
    if not missing_roles and analysis_missing_roles:
        missing_roles = analysis_missing_roles
    accepted_count = int_token(analysis.get("accepted_lifecycle_event_count"))
    if accepted_count is None:
        accepted_count = len(roles_present)
    rejected_events = object_list(analysis.get("rejected_or_incomplete_role_events"))
    rejected_count = int_token(analysis.get("rejected_or_incomplete_role_event_count"))
    if rejected_count is None:
        rejected_count = len(rejected_events)
    exact_runtime_triplet = analysis.get("exact_copied_runtime_triplet")
    if not isinstance(exact_runtime_triplet, dict):
        exact_runtime_triplet = {}
    session_end_missing_correlation = (
        session_end_missing_correlation_diagnostics_from_analysis(analysis)
    )
    copy_readiness = copy_ready.get("copy_readiness")
    artifact_bindings = copy_ready.get("artifact_hash_path_bindings")
    if not isinstance(artifact_bindings, dict):
        artifact_bindings = copy_ready.get("copied_artifact_bindings")
    if not isinstance(artifact_bindings, dict):
        artifact_bindings = {}
    source_alias_paths, candidate_alias_paths = source_present_alias_paths(copy_ready)
    diagnostic_or_rejected = bool(
        copy_readiness == "blocked_diagnostic_or_rejected_lifecycle_lines"
        or analysis.get("diagnostic_or_rejected_lifecycle_lines_count_as_ready_to_copy") is False
        and rejected_count > 0
    )
    diagnostic_only = bool(diagnostic_or_rejected and accepted_count == 0)
    return {
        "present": True,
        "source_path": str(path),
        "schema": copy_ready.get("schema"),
        "status": copy_ready.get("status"),
        "copy_readiness": copy_readiness,
        "ready_to_copy_source_value": copy_ready.get("ready_to_copy") is True,
        "ready_to_copy": False,
        "copied_source_value": copy_ready.get("copied") is True,
        "copied": False,
        "missing_roles": missing_roles,
        "roles_present": roles_present,
        "blockers": string_list(copy_ready.get("blockers")),
        "target_log": copy_ready.get("target_log"),
        "source_log": copy_ready.get("source_log"),
        "artifact_hash_path_bindings": artifact_bindings,
        "copied_log_hash_path_binding": artifact_bindings.get("copied_log")
        if isinstance(artifact_bindings.get("copied_log"), dict)
        else {},
        "sibling_sidecar_hash_path_bindings": artifact_bindings.get("sibling_sidecars")
        if isinstance(artifact_bindings.get("sibling_sidecars"), list)
        else [],
        "copied_log_hash_path_bound": artifact_bindings.get("copied_log_hash_path_bound") is True,
        "sibling_sidecars_hash_path_bound": (
            artifact_bindings.get("sibling_sidecars_hash_path_bound") is True
        ),
        "artifact_hash_path_bindings_count_as_approved_runtime_evidence": False,
        "source_present_alias_paths": source_alias_paths,
        "candidate_pack_alias_paths": candidate_alias_paths,
        "source_present_alias_detected": bool(source_alias_paths),
        "candidate_pack_alias_detected": bool(candidate_alias_paths),
        "source_present_aliases_count_as_approved_runtime_evidence": False,
        "candidate_pack_aliases_count_as_approved_runtime_evidence": False,
        "source_log_not_ready": source_log_not_ready,
        "observer_only_no_role_window": source_log_not_ready,
        "observer_only_no_role_window_detected": (
            source_log_not_ready.get("observer_only_no_role_window_detected") is True
            or copy_ready.get("observer_only_no_role_window_detected") is True
        ),
        "active_observer_only_no_role_window": (
            source_log_not_ready.get("active_observer_only_no_role_window") is True
            or copy_ready.get("active_observer_only_no_role_window") is True
        ),
        "post_window_observer_only_no_role_window": (
            source_log_not_ready.get("post_window_observer_only_no_role_window") is True
            or copy_ready.get("post_window_observer_only_no_role_window") is True
        ),
        "source_log_not_ready_classification": source_log_not_ready.get("classification"),
        "window_state": source_log_not_ready.get("window_state"),
        "fresh_window": source_log_not_ready.get("fresh_window")
        if isinstance(source_log_not_ready.get("fresh_window"), dict)
        else {
            "start_utc": copy_ready.get("fresh_window_start_utc"),
            "end_utc": copy_ready.get("fresh_window_end_utc"),
        },
        "accepted_lifecycle_event_count": accepted_count,
        "rejected_or_incomplete_role_event_count": rejected_count,
        "rejected_or_incomplete_role_events": rejected_events,
        "exact_copied_runtime_triplet": exact_runtime_triplet,
        "exact_copied_runtime_triplet_accepted": exact_runtime_triplet.get("accepted") is True,
        "session_end_missing_correlation_diagnostics": session_end_missing_correlation,
        "session_end_missing_correlation_only": session_end_missing_correlation is not None,
        "diagnostic_or_rejected_lifecycle_lines": diagnostic_or_rejected,
        "diagnostic_only_lifecycle_lines": diagnostic_only,
        "target_hint": source_log_not_ready.get("target_hint")
        if isinstance(source_log_not_ready.get("target_hint"), dict)
        else {},
        "manual_offline_next_steps": string_list(
            source_log_not_ready.get("manual_offline_next_steps")
        ),
        "operator_context_only": True,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        "publication_authorized": False,
        **sdk_p0_non_progress_flags(),
    }


def passive_activity(passive: dict[str, Any] | None) -> dict[str, Any]:
    if passive is None:
        return {
            "present": False,
            "classification": "passive_summary_not_supplied",
            "snapshot_count": None,
            "players_current_by_target": {},
            "observer_enabled_targets": [],
            "complete_observer_event_triplet_targets": [],
            "targets_with_players_detected": [],
            "approved_runtime_evidence": False,
            "ready": False,
            "counts_as_approved_runtime_evidence": False,
            **sdk_p0_non_progress_flags(),
        }
    activity = passive.get("passive_monitor_activity_summary")
    if not isinstance(activity, dict):
        activity = {}
    source_approved_runtime_evidence = passive.get("approved_runtime_evidence") is True
    source_ready = passive.get("ready") is True
    return {
        "present": True,
        "schema": passive.get("schema"),
        "classification": passive.get("classification"),
        "latest_tick_utc": passive.get("monitor", {}).get("latest_tick_utc")
        if isinstance(passive.get("monitor"), dict)
        else None,
        "snapshot_count": passive.get("snapshot_count"),
        "snapshot_status": passive.get("snapshot_status"),
        "players_current_by_target": activity.get("players_current_by_target", {}),
        "observer_enabled_targets": activity.get("observer_enabled_targets", []),
        "complete_observer_event_triplet_targets": activity.get(
            "complete_observer_event_triplet_targets", []
        ),
        "targets_with_players_detected": activity.get("targets_with_players_detected", []),
        "targets_with_query_warning": activity.get("targets_with_query_warning", []),
        "query_warnings_by_target": activity.get("query_warnings_by_target", {}),
        "source_report_claims": {
            "approved_runtime_evidence": source_approved_runtime_evidence,
            "ready": source_ready,
        },
        "source_claims_ignored_for_status": bool(source_approved_runtime_evidence or source_ready),
        "approved_runtime_evidence": False,
        "ready": False,
        "counts_as_approved_runtime_evidence": False,
        **sdk_p0_non_progress_flags(),
    }


def runtime_player_availability_context(
    passive_state: dict[str, Any],
    monitor_context: dict[str, Any],
) -> dict[str, Any]:
    known_counts: dict[str, int] = {}
    unknown_targets: set[str] = set()
    presence_signal_targets: set[str] = set()
    trusted_source_discrepancies = monitor_context.get("trusted_source_discrepancies_by_target")
    if not isinstance(trusted_source_discrepancies, dict):
        trusted_source_discrepancies = {}
    discrepant_sources_by_target = monitor_context.get("discrepant_sources_by_target")
    if not isinstance(discrepant_sources_by_target, dict):
        discrepant_sources_by_target = {}

    def merge_known_count(target: str, count: int) -> None:
        current = known_counts.get(target)
        if current is None or count > current:
            known_counts[target] = count

    passive_counts = passive_state.get("players_current_by_target")
    if isinstance(passive_counts, dict):
        for target, count in passive_counts.items():
            target_name = str(target)
            if isinstance(count, bool):
                continue
            if isinstance(count, int):
                merge_known_count(target_name, count)
            else:
                unknown_targets.add(target_name)
    for target in string_list(passive_state.get("targets_with_players_detected")):
        presence_signal_targets.add(target)
    for target in string_list(passive_state.get("targets_with_query_warning")):
        unknown_targets.add(target)
    query_warnings = passive_state.get("query_warnings_by_target")
    if isinstance(query_warnings, dict):
        for target in query_warnings:
            unknown_targets.add(str(target))

    for monitor_key in ("query_status_by_target", "rcon_status_by_target"):
        monitor_targets = monitor_context.get(monitor_key)
        if isinstance(monitor_targets, dict):
            for target, record in monitor_targets.items():
                if not isinstance(record, dict):
                    continue
                target_name = str(target)
                count = record.get("players_current")
                if isinstance(count, bool):
                    continue
                if isinstance(count, int):
                    merge_known_count(target_name, count)
                elif record.get("presence_detected") is True:
                    presence_signal_targets.add(target_name)
                else:
                    unknown_targets.add(target_name)
                if record.get("presence_detected") is True:
                    presence_signal_targets.add(target_name)
                if (
                    record.get("status") not in (None, "ok")
                    and not isinstance(count, int)
                    and record.get("presence_detected") is not True
                ):
                    unknown_targets.add(target_name)

    targets_with_players = sorted(
        set(target for target, count in known_counts.items() if count > 0)
        | presence_signal_targets
    )
    known_zero_targets = sorted(
        target
        for target, count in known_counts.items()
        if count == 0 and target not in presence_signal_targets
    )
    unknown_player_context = bool(unknown_targets)
    no_users_confirmed = (
        bool(known_zero_targets)
        and not targets_with_players
        and not unknown_player_context
    )
    if targets_with_players:
        classification = "players_detected_operator_context_non_evidence"
        recommended_wait_state = "player_backed_window_possible_when_scoped_activation_is_prepared"
    elif no_users_confirmed:
        classification = "no_players_currently_detected_wait_for_testers_non_evidence"
        recommended_wait_state = "keep_runtime_window_prepared_without_claiming_evidence"
    elif unknown_player_context:
        classification = "player_count_unknown_wait_for_clear_signal_non_evidence"
        recommended_wait_state = "treat_unknown_counts_as_waiting_not_evidence"
    else:
        classification = "no_player_availability_context_supplied_non_evidence"
        recommended_wait_state = "no_runtime_wait_signal_available"

    return {
        "classification": classification,
        "known_player_counts_by_target": known_counts,
        "known_zero_player_targets": known_zero_targets,
        "targets_with_players_detected": targets_with_players,
        "presence_detected_targets": sorted(presence_signal_targets),
        "unknown_player_count_targets": sorted(unknown_targets),
        "trusted_source_discrepancies_by_target": trusted_source_discrepancies,
        "discrepant_sources_by_target": discrepant_sources_by_target,
        "source_discrepancy_detected": bool(trusted_source_discrepancies),
        "source_discrepancy_classification": (
            "trusted_source_discrepancy_non_evidence"
            if trusted_source_discrepancies
            else "none"
        ),
        "source_discrepancy_counts_as_approved_runtime_evidence": False,
        "source_discrepancy_counts_as_runtime_evidence": False,
        "source_discrepancy_authorizes_server_operations": False,
        "unknown_player_context": unknown_player_context,
        "no_users_confirmed": no_users_confirmed,
        "no_players_currently_detected": no_users_confirmed,
        "players_detected": bool(targets_with_players),
        "recommended_wait_state": recommended_wait_state,
        "operator_context_only": True,
        "wait_for_testers_only": True,
        "activates_runtime_window": False,
        "authorizes_runtime_capture": False,
        "authorizes_server_operations": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "v1_completion_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def copy_ready_observer_only_no_role(copy_ready_context: dict[str, Any]) -> bool:
    source_state = copy_ready_context.get("source_log_not_ready")
    if not isinstance(source_state, dict):
        source_state = copy_ready_context.get("observer_only_no_role_window")
    return bool(
        copy_ready_context.get("present") is True
        and copy_ready_context.get("active_observer_only_no_role_window") is True
        and isinstance(source_state, dict)
        and source_state.get("active_observer_only_no_role_window") is True
    )


def source_log_not_ready_state(copy_ready_context: dict[str, Any]) -> dict[str, Any]:
    source_state = copy_ready_context.get("source_log_not_ready")
    if not isinstance(source_state, dict):
        source_state = copy_ready_context.get("observer_only_no_role_window")
    return source_state if isinstance(source_state, dict) else {}


def copy_ready_window_state(copy_ready_context: dict[str, Any]) -> str | None:
    source_state = source_log_not_ready_state(copy_ready_context)
    for value in (copy_ready_context.get("window_state"), source_state.get("window_state")):
        if isinstance(value, str) and value:
            return value
    return None


def exact_triplet_complete(exact_triplet: dict[str, Any]) -> bool:
    return exact_triplet.get("complete") is True


def copy_ready_has_exact_triplet(
    copy_ready_context: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> bool:
    return bool(
        exact_triplet_complete(exact_triplet)
        or copy_ready_context.get("exact_copied_runtime_triplet_accepted") is True
    )


def copy_ready_source_text_values(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, Path):
        return [str(value)]
    if isinstance(value, list):
        output: list[str] = []
        for item in value:
            output.extend(copy_ready_source_text_values(item))
        return output
    if isinstance(value, dict):
        output: list[str] = []
        for key in (
            "classification",
            "path",
            "source_path",
            "source_log",
            "target_log",
            "source_evidence_dir",
            "invalid_source_evidence_dir",
            "source_run_id",
            "source_root_role",
            "suggested_valid_closure_run_id",
            "suggested_valid_closure_evidence_dir",
        ):
            output.extend(copy_ready_source_text_values(value.get(key)))
        return output
    return []


def copy_ready_flag_true(
    copy_ready_context: dict[str, Any],
    source_state: dict[str, Any],
    *keys: str,
) -> bool:
    return any(
        mapping.get(key) is True
        for mapping in (copy_ready_context, source_state)
        for key in keys
    )


def copy_ready_flag_false(
    copy_ready_context: dict[str, Any],
    source_state: dict[str, Any],
    *keys: str,
) -> bool:
    return any(
        mapping.get(key) is False
        for mapping in (copy_ready_context, source_state)
        for key in keys
    )


def copy_ready_source_boundary(copy_ready_context: dict[str, Any]) -> dict[str, Any]:
    source_state = source_log_not_ready_state(copy_ready_context)
    values: list[str] = []
    for mapping in (copy_ready_context, source_state):
        values.extend(copy_ready_source_text_values(mapping))
    values = [value for index, value in enumerate(values) if value and value not in values[:index]]
    source_alias_paths = sorted(
        set(
            string_list(copy_ready_context.get("source_present_alias_paths"))
            + string_list(source_state.get("source_present_alias_paths"))
        )
    )
    candidate_alias_paths = sorted(
        set(
            string_list(copy_ready_context.get("candidate_pack_alias_paths"))
            + string_list(source_state.get("candidate_pack_alias_paths"))
        )
    )
    source_present_alias = bool(source_alias_paths)
    candidate_pack_alias = bool(candidate_alias_paths)
    source_text = " ".join(values)
    source_looks_passive = copy_ready_flag_true(
        copy_ready_context,
        source_state,
        "source_looks_like_passive_monitor_root",
        "passive_monitor_root",
        "passive_snapshot_source",
        "source_is_passive_snapshot",
        "source_is_status_report",
    ) or bool(SOURCE_ONLY_COPY_READY_RE.search(source_text))
    source_is_stale = copy_ready_flag_true(
        copy_ready_context,
        source_state,
        "source_root_stale",
        "stale_source_root",
        "source_is_stale",
        "stale_copy_ready_source",
    )
    source_invalid = copy_ready_flag_false(
        copy_ready_context,
        source_state,
        "source_root_valid_for_closure",
        "source_accepted_as_closure_evidence_dir",
        "source_becomes_closure_root",
    )
    passive_root_rejected = copy_ready_flag_false(
        copy_ready_context,
        source_state,
        "passive_monitor_root_accepted_as_closure_evidence_dir",
    )
    source_only = bool(
        copy_ready_context.get("present") is True
        and (
            source_looks_passive
            or source_is_stale
            or source_invalid
            or passive_root_rejected
            or candidate_pack_alias
        )
    )
    if source_invalid and source_looks_passive:
        classification = "invalid_passive_copy_ready_source_only_non_evidence"
    elif source_invalid:
        classification = "invalid_copy_ready_source_only_non_evidence"
    elif candidate_pack_alias:
        classification = "candidate_pack_copy_ready_source_only_non_evidence"
    elif source_is_stale and source_looks_passive:
        classification = "stale_passive_copy_ready_source_only_non_evidence"
    elif source_is_stale:
        classification = "stale_copy_ready_source_only_non_evidence"
    elif source_looks_passive:
        classification = "passive_copy_ready_source_only_non_evidence"
    elif source_present_alias:
        classification = "source_present_alias_context_non_evidence"
    else:
        classification = "copy_ready_source_not_flagged"
    return {
        "schema": "obelisk.player-principal-lifecycle-copy-ready-source-boundary.v1",
        "present": copy_ready_context.get("present") is True,
        "classification": classification,
        "source_values": values,
        "source_only_non_evidence": source_only,
        "source_looks_like_passive_monitor_root": source_looks_passive,
        "source_is_stale": source_is_stale,
        "source_is_invalid": source_invalid,
        "source_present_alias_detected": source_present_alias,
        "candidate_pack_alias_detected": candidate_pack_alias,
        "source_present_alias_paths": source_alias_paths,
        "candidate_pack_alias_paths": candidate_alias_paths,
        "passive_monitor_root_accepted_as_closure_evidence_dir": (
            False if passive_root_rejected else None
        ),
        "source_accepted_as_closure_evidence_dir": False if source_only else None,
        "source_present_alias_counts_as_approved_runtime_evidence": False,
        "candidate_pack_alias_counts_as_approved_runtime_evidence": False,
        "source_counts_as_approved_runtime_evidence": False,
        "copy_ready_source_authorizes_checker": False,
        "copy_ready_source_authorizes_bundle": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
    }


def copy_ready_complete_role_triplet(copy_ready_context: dict[str, Any]) -> bool:
    roles_present = set(string_list(copy_ready_context.get("roles_present")))
    return bool(
        roles_present.issuperset(REQUIRED_LIFECYCLE_ROLES)
        or copy_ready_context.get("copy_readiness") == "ready_complete_role_triplet"
        or copy_ready_context.get("exact_copied_runtime_triplet_accepted") is True
    )


def stale_passive_complete_role_triplet_non_evidence(
    copy_ready_context: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> bool:
    boundary = copy_ready_source_boundary(copy_ready_context)
    return bool(
        boundary["source_only_non_evidence"]
        and (
            copy_ready_complete_role_triplet(copy_ready_context)
            or exact_triplet.get("complete") is True
        )
    )


def copy_ready_runtime_window_expired(copy_ready_context: dict[str, Any]) -> bool:
    source_state = source_log_not_ready_state(copy_ready_context)
    state = copy_ready_window_state(copy_ready_context)
    classification = str(copy_ready_context.get("source_log_not_ready_classification") or "")
    return bool(
        copy_ready_context.get("present") is True
        and (
            state in {"post_window", "expired", "window_expired", "closed"}
            or source_state.get("post_window_observer_only_no_role_window") is True
            or copy_ready_context.get("post_window_observer_only_no_role_window") is True
            or "post_window" in classification
        )
    )


def copy_ready_runtime_window_active(copy_ready_context: dict[str, Any]) -> bool:
    source_state = source_log_not_ready_state(copy_ready_context)
    state = copy_ready_window_state(copy_ready_context)
    return bool(
        copy_ready_context.get("present") is True
        and (
            state in {"pre_window", "in_progress"}
            or source_state.get("active_observer_only_no_role_window") is True
            or copy_ready_context.get("active_observer_only_no_role_window") is True
        )
    )


def copy_ready_only_observer_gate_or_diagnostic_lines(
    copy_ready_context: dict[str, Any],
) -> bool:
    source_state = source_log_not_ready_state(copy_ready_context)
    roles = set(string_list(copy_ready_context.get("roles_present")))
    accepted_count = int_token(copy_ready_context.get("accepted_lifecycle_event_count")) or 0
    observer_only = bool(
        copy_ready_context.get("observer_only_no_role_window_detected") is True
        or source_state.get("observer_only_no_role_window_detected") is True
        or (
            accepted_count == 0
            and (
                source_state.get("observer_enabled") is True
                or source_state.get("observer_enable_in_fresh_window") is True
            )
        )
    )
    observer_gate_only = bool(roles and roles <= {"session_start_rejected"})
    diagnostic_only = bool(
        copy_ready_context.get("diagnostic_only_lifecycle_lines") is True
        or (
            copy_ready_context.get("diagnostic_or_rejected_lifecycle_lines") is True
            and accepted_count == 0
        )
        or copy_ready_context.get("copy_readiness") == "blocked_diagnostic_or_rejected_lifecycle_lines"
    )
    return observer_only or observer_gate_only or diagnostic_only


def copy_ready_session_end_missing_correlation_only(
    copy_ready_context: dict[str, Any],
) -> bool:
    diagnostics = copy_ready_context.get("session_end_missing_correlation_diagnostics")
    return isinstance(diagnostics, dict) and copy_ready_context.get(
        "session_end_missing_correlation_only"
    ) is True


def runtime_window_lifecycle_state(
    copy_ready_context: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> dict[str, Any]:
    source_state = source_log_not_ready_state(copy_ready_context)
    window_state = copy_ready_window_state(copy_ready_context)
    exact_complete = copy_ready_has_exact_triplet(copy_ready_context, exact_triplet)
    source_boundary = copy_ready_source_boundary(copy_ready_context)
    stale_passive_complete = stale_passive_complete_role_triplet_non_evidence(
        copy_ready_context,
        exact_triplet,
    )
    exact_usable_for_checker = exact_complete and not stale_passive_complete
    expired = copy_ready_runtime_window_expired(copy_ready_context)
    active = copy_ready_runtime_window_active(copy_ready_context)
    non_evidence_only = copy_ready_only_observer_gate_or_diagnostic_lines(copy_ready_context)
    session_end_missing_correlation_only = copy_ready_session_end_missing_correlation_only(
        copy_ready_context
    )
    roles_present = string_list(copy_ready_context.get("roles_present"))
    accepted_count = int_token(copy_ready_context.get("accepted_lifecycle_event_count")) or 0
    rejected_count = int_token(copy_ready_context.get("rejected_or_incomplete_role_event_count")) or 0
    observer_gate_only = bool(set(roles_present) and set(roles_present) <= {"session_start_rejected"})
    diagnostic_only = copy_ready_context.get("diagnostic_only_lifecycle_lines") is True
    observer_only = (
        copy_ready_context.get("observer_only_no_role_window_detected") is True
        or source_state.get("observer_only_no_role_window_detected") is True
    )
    if stale_passive_complete:
        classification = "stale_or_passive_complete_role_triplet_non_evidence_prepare_fresh_player_backed_window"
    elif exact_complete:
        classification = "exact_copied_lifecycle_triplet_available"
    elif expired and session_end_missing_correlation_only:
        classification = "expired_runtime_window_session_end_missing_correlation_non_evidence_prepare_fresh_player_backed_window"
    elif active and session_end_missing_correlation_only:
        classification = "active_runtime_window_session_end_missing_correlation_wait_for_matched_triplet_or_end"
    elif expired and non_evidence_only:
        classification = "expired_runtime_window_non_evidence_prepare_fresh_player_backed_window"
    elif active and non_evidence_only:
        classification = "active_runtime_window_waiting_for_exact_copied_triplet_or_window_end"
    elif copy_ready_context.get("present") is True:
        classification = "runtime_window_not_exact_triplet_context_only"
    else:
        classification = "runtime_window_lifecycle_context_not_supplied"
    return {
        "schema": RUNTIME_WINDOW_LIFECYCLE_SCHEMA,
        "present": copy_ready_context.get("present") is True,
        "classification": classification,
        "window_state": window_state,
        "fresh_window": copy_ready_context.get("fresh_window")
        if isinstance(copy_ready_context.get("fresh_window"), dict)
        else {},
        "target_hint": copy_ready_context.get("target_hint")
        if isinstance(copy_ready_context.get("target_hint"), dict)
        else {},
        "expired_runtime_window": expired,
        "active_runtime_window": active,
        "non_evidence_only_material": non_evidence_only,
        "observer_gate_only": observer_gate_only,
        "observer_only_no_role_window": observer_only,
        "diagnostic_only_lifecycle_lines": diagnostic_only,
        "session_end_missing_correlation_only": session_end_missing_correlation_only,
        "session_end_missing_correlation_diagnostics": copy_ready_context.get(
            "session_end_missing_correlation_diagnostics"
        )
        if isinstance(copy_ready_context.get("session_end_missing_correlation_diagnostics"), dict)
        else None,
        "diagnostic_or_rejected_lifecycle_lines": (
            copy_ready_context.get("diagnostic_or_rejected_lifecycle_lines") is True
        ),
        "accepted_lifecycle_event_count": accepted_count,
        "rejected_or_incomplete_role_event_count": rejected_count,
        "roles_present": roles_present,
        "missing_roles": string_list(copy_ready_context.get("missing_roles")),
        "copy_ready_source_boundary": source_boundary,
        "copy_ready_complete_role_triplet": copy_ready_complete_role_triplet(copy_ready_context),
        "stale_or_passive_complete_role_triplet_non_evidence": stale_passive_complete,
        "exact_copied_lifecycle_event_triplet_complete": exact_complete,
        "exact_copied_lifecycle_event_triplet_usable_for_checker": exact_usable_for_checker,
        "accepted_ready": exact_usable_for_checker,
        "accepted_ready_for_checker": exact_usable_for_checker,
        "accepted_ready_counts_as_approved_runtime_evidence": False,
        "missing_copied_lifecycle_event_triplet_labels": string_list(
            exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
        ),
        "close_or_classify_as_non_evidence": bool(
            stale_passive_complete or (expired and non_evidence_only and not exact_complete)
        ),
        "active_waiting_not_closure_ready": bool(
            active and non_evidence_only and not exact_complete and not stale_passive_complete
        ),
        "copy_bundle_commands_allowed": exact_usable_for_checker,
        "copy_bundle_commands_suppressed_until_exact_triplet": not exact_usable_for_checker,
        "fresh_player_backed_window_required": bool(
            stale_passive_complete or (expired and non_evidence_only and not exact_complete)
        ),
        "expired_no_evidence": bool(
            stale_passive_complete or (expired and non_evidence_only and not exact_complete)
        ),
        "expired_no_evidence_counts_as_accepted_ready": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def expired_non_evidence_runtime_window(
    copy_ready_context: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> bool:
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    return lifecycle["close_or_classify_as_non_evidence"] is True


def active_runtime_window_waiting(
    copy_ready_context: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> bool:
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    return lifecycle["active_waiting_not_closure_ready"] is True


def fresh_player_backed_window_preparation(
    runtime_window_lifecycle: dict[str, Any],
) -> dict[str, Any]:
    target = runtime_window_lifecycle.get("target_hint")
    if not isinstance(target, dict):
        target = {}
    return {
        "schema": FRESH_PLAYER_BACKED_WINDOW_SCHEMA,
        "status": "fresh_player_backed_window_required_after_non_evidence_close",
        "target_hint": target,
        "player_backed_window_required": True,
        "diagnostic_candidates": "disabled",
        "exact_copied_lifecycle_event_triplet_required": True,
        "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "requires_separate_current_turn_operator_scope": True,
        "copy_bundle_commands_allowed_before_exact_triplet": False,
        "runner_command_available": False,
        "server_operations_authorized_by_this_report": False,
        "runtime_work_authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def exact_triplet_bundle_route(
    *,
    closure: dict[str, Any],
    exact_triplet: dict[str, Any],
    artifact_blockers: dict[str, Any],
    runtime_window_lifecycle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lifecycle = runtime_window_lifecycle if isinstance(runtime_window_lifecycle, dict) else {}
    matched_cases = object_list(exact_triplet.get("matched_copied_lifecycle_event_triplet"))
    missing_cases = object_list(exact_triplet.get("missing_copied_lifecycle_event_triplet"))
    accepted_roles = [
        str(case.get("role"))
        for case in matched_cases
        if isinstance(case.get("role"), str)
    ]
    missing_roles_from_triplet = [
        str(case.get("role"))
        for case in missing_cases
        if isinstance(case.get("role"), str)
    ]
    missing_labels = string_list(
        exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
    )
    missing_artifacts = string_list(artifact_blockers.get("missing_artifacts"))
    first_missing_kind = "checker"
    first_missing_role = None
    first_missing_label = None
    first_missing_artifact = None
    first_missing_path = "approved-bundle-checker/accepted-report"
    if missing_roles_from_triplet:
        first_missing_kind = "copied_lifecycle_triplet_role"
        first_missing_role = missing_roles_from_triplet[0]
        first_missing_label = missing_labels[0] if missing_labels else None
        first_missing_path = (
            f"copied-lifecycle-triplet/{first_missing_label or first_missing_role}"
        )
    elif missing_artifacts:
        first_missing_kind = "required_runtime_evidence_artifact"
        first_missing_artifact = str(artifact_blockers.get("first_missing_artifact"))
        first_missing_path = first_missing_artifact

    role_path: list[dict[str, Any]] = []
    matched_by_role = {
        str(case.get("role")): case
        for case in matched_cases
        if isinstance(case.get("role"), str)
    }
    missing_by_role = {
        str(case.get("role")): case
        for case in missing_cases
        if isinstance(case.get("role"), str)
    }
    for expected in REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET:
        role = str(expected["role"])
        label = str(expected["label"])
        observed = matched_by_role.get(role)
        missing = missing_by_role.get(role)
        role_path.append(
            {
                "stage": "copied_lifecycle_triplet_role",
                "role": role,
                "label": label,
                "target": expected["target"],
                "status": "accepted" if observed is not None and missing is None else "missing",
                "apply_status": expected["apply_status"],
                "principal_action": expected["principal_action"],
                "correlation_status": expected["correlation_status"],
                "copied_bool_fields": list(expected["copied_bool_fields"]),
                "copied_bool_values": list(expected["copied_bool_values"]),
                "accepted_by_status_report": False,
                "counts_as_approved_runtime_evidence": False,
            }
        )

    artifact_path = [
        {
            "stage": "required_runtime_evidence_artifact",
            "artifact": item.get("artifact"),
            "status": item.get("status"),
            "reason": item.get("reason"),
            "side_effect_domain": item.get("side_effect_domain"),
            "runner_command_available": item.get("runner_command_available") is True,
            "blocked_until": item.get("blocked_until", []),
            "counts_as_approved_runtime_evidence": False,
        }
        for item in artifact_blockers.get(
            "fastest_exact_path_from_fresh_copied_lifecycle_window",
            [],
        )
        if isinstance(item, dict)
    ]
    return {
        "schema": EXACT_TRIPLET_BUNDLE_ROUTE_SCHEMA,
        "status": "blocked_approved_runtime_evidence_missing",
        "route_name": "same_run_exact_copied_lifecycle_triplet_bundle",
        "current_route_blocker": "approved_runtime_evidence_missing",
        "next_action_target": "exact_copied_lifecycle_triplet_bundle",
        "first_missing_kind": first_missing_kind,
        "first_missing_role": first_missing_role,
        "first_missing_copied_lifecycle_event_label": first_missing_label,
        "first_missing_artifact": first_missing_artifact,
        "first_missing_runtime_evidence_path": first_missing_path,
        "accepted_lifecycle_event_roles": accepted_roles,
        "reported_missing_lifecycle_event_roles": string_list(
            closure.get("missing_lifecycle_event_roles")
        ),
        "missing_lifecycle_event_roles": missing_roles_from_triplet,
        "missing_copied_lifecycle_event_triplet_labels": missing_labels,
        "missing_required_artifacts": missing_artifacts,
        "role_artifact_path": [*role_path, *artifact_path],
        "fastest_missing_role_artifact_path": [*role_path, *artifact_path],
        "runtime_window_lifecycle_classification": lifecycle.get("classification"),
        "active_window_waiting_not_closure_ready": (
            lifecycle.get("active_waiting_not_closure_ready") is True
        ),
        "expired_window_non_evidence": (
            lifecycle.get("close_or_classify_as_non_evidence") is True
        ),
        "partial_lifecycle_material_present": bool(accepted_roles or missing_roles_from_triplet),
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        "helper_recommendation_scope": (
            "bounded metadata only; no live copy, live read, Discord send, active "
            "notice, diagnostic sample, bundle, or checker command is authorized by "
            "this route"
        ),
        "bounded_helper_recommendations": [
            "use the same-run copied observer triplet only after all three required roles match exactly",
            "generate sibling artifacts only after the exact triplet source is accepted for the same run",
            "run the approved bundle checker only after the exact sibling set exists",
        ],
        "helper_command_authorized_by_route": False,
        "runner_command_available": False,
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def attach_exact_triplet_bundle_route(
    actions: list[dict[str, Any]],
    route: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            **action,
            "exact_triplet_bundle_route": route,
            "next_action_target": action.get(
                "next_action_target",
                route.get("next_action_target"),
            ),
            "first_missing_runtime_evidence_path": action.get(
                "first_missing_runtime_evidence_path",
                route.get("first_missing_runtime_evidence_path"),
            ),
            "fastest_missing_role_artifact_path": action.get(
                "fastest_missing_role_artifact_path",
                route.get("fastest_missing_role_artifact_path", []),
            ),
            "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
            "copied_log_presence_counts_as_approved_runtime_evidence": False,
            "stale_passive_tail_counts_as_approved_runtime_evidence": False,
            "direct_discord_send_counts_as_approved_runtime_evidence": False,
            "active_notice_state_counts_as_approved_runtime_evidence": False,
            "diagnostic_samples_count_as_approved_runtime_evidence": False,
        }
        for action in actions
    ]


def runtime_window_non_evidence_action(
    *,
    missing_roles: list[str],
    exact_triplet: dict[str, Any],
    copy_ready_context: dict[str, Any],
    missing_artifacts: list[str],
    expired: bool,
    exact_triplet_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_state = copy_ready_context.get("source_log_not_ready")
    if not isinstance(source_state, dict):
        source_state = copy_ready_context.get("observer_only_no_role_window")
    if not isinstance(source_state, dict):
        source_state = {}
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    fresh_window = fresh_player_backed_window_preparation(lifecycle)
    session_end_missing_correlation = lifecycle.get(
        "session_end_missing_correlation_diagnostics"
    )
    if not isinstance(session_end_missing_correlation, dict):
        session_end_missing_correlation = None
    manual_steps = string_list(source_state.get("manual_offline_next_steps"))
    stale_passive_complete = (
        lifecycle.get("stale_or_passive_complete_role_triplet_non_evidence") is True
    )
    if not manual_steps:
        if stale_passive_complete:
            manual_steps = [
                "classify the stale/passive complete-role triplet as non-evidence",
                "do not copy, bundle, or checker-route source-only passive/status material",
                "stage a closure-compatible copied lifecycle evidence run or prepare a fresh player-backed window under separate scope",
            ]
        elif session_end_missing_correlation is not None and expired:
            manual_steps = [
                "classify the expired session_end-only missing-correlation window as non-evidence",
                "do not copy, bundle, or checker-route this source log without a matched session_end and the exact lifecycle triplet",
                "prepare a fresh player-backed window under separate current-turn scope if evidence is still needed",
            ]
        elif session_end_missing_correlation is not None:
            manual_steps = [
                "keep the active window in waiting state until a matched session_end and the exact lifecycle triplet appear or the window ends",
                "do not copy, bundle, or checker-route this source log while only missing-correlation session_end material is present",
                "classify the window after it expires if no matched lifecycle triplet appears",
            ]
        elif expired:
            manual_steps = [
                "classify the expired window as non-evidence",
                "do not copy, bundle, or checker-route this source log without the exact lifecycle triplet",
                "prepare a fresh player-backed window under separate current-turn scope if evidence is still needed",
            ]
        else:
            manual_steps = [
                "keep the active window in waiting state until the window ends or the exact lifecycle triplet appears",
                "do not copy, bundle, or checker-route this source log while the exact lifecycle triplet is missing",
                "classify the window after it expires if only observer-gate or diagnostic-only lines are present",
            ]
    if stale_passive_complete:
        action_name = "classify_stale_passive_complete_role_triplet_as_non_evidence"
        action_kind = "stale_passive_complete_role_triplet_non_evidence"
        action_status = "source_only_non_evidence_prepare_fresh_player_backed_window"
    else:
        action_name = (
            "close_expired_player_principal_lifecycle_window_as_non_evidence"
            if expired
            else "wait_for_active_player_principal_lifecycle_window_exact_triplet_or_end"
        )
        action_kind = (
            "expired_runtime_window_non_evidence_closure"
            if expired
            else "active_runtime_window_waiting_for_exact_triplet"
        )
        action_status = (
            "closed_non_evidence_prepare_fresh_player_backed_window"
            if expired
            else "active_waiting_not_closure_ready"
        )
    return {
        "action": action_name,
        "action_kind": action_kind,
        "blocking": True,
        "status": action_status,
        "items": missing_roles,
        "exact_triplet_bundle_route": exact_triplet_route or {},
        "next_action_target": (
            exact_triplet_route.get("next_action_target")
            if isinstance(exact_triplet_route, dict)
            else "exact_copied_lifecycle_triplet_bundle"
        ),
        "first_missing_runtime_evidence_path": (
            exact_triplet_route.get("first_missing_runtime_evidence_path")
            if isinstance(exact_triplet_route, dict)
            else None
        ),
        "fastest_missing_role_artifact_path": (
            exact_triplet_route.get("fastest_missing_role_artifact_path", [])
            if isinstance(exact_triplet_route, dict)
            else []
        ),
        "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "missing_copied_lifecycle_event_triplet": exact_triplet.get(
            "missing_copied_lifecycle_event_triplet", []
        ),
        "missing_copied_lifecycle_event_triplet_labels": string_list(
            exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
        ),
        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
        "source_log_not_ready": source_state,
        "observer_only_no_role_window": source_state,
        "runtime_window_lifecycle": lifecycle,
        "copy_ready_source_boundary": lifecycle.get("copy_ready_source_boundary", {}),
        "stale_or_passive_complete_role_triplet_non_evidence": stale_passive_complete,
        "exact_copied_lifecycle_event_triplet_usable_for_checker": (
            lifecycle.get("exact_copied_lifecycle_event_triplet_usable_for_checker") is True
        ),
        "fresh_player_backed_window": fresh_window,
        "next_player_backed_window": fresh_window,
        "copy_ready_log_context": {
            "source_path": copy_ready_context.get("source_path"),
            "status": copy_ready_context.get("status"),
            "copy_readiness": copy_ready_context.get("copy_readiness"),
            "source_log": copy_ready_context.get("source_log"),
            "target_log": copy_ready_context.get("target_log"),
            "ready_to_copy_source_value": copy_ready_context.get("ready_to_copy_source_value"),
            "copied_source_value": copy_ready_context.get("copied_source_value"),
            "active_observer_only_no_role_window": (
                copy_ready_context.get("active_observer_only_no_role_window") is True
            ),
            "post_window_observer_only_no_role_window": (
                copy_ready_context.get("post_window_observer_only_no_role_window") is True
            ),
            "window_state": copy_ready_context.get("window_state"),
            "session_end_missing_correlation_diagnostics": session_end_missing_correlation,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        },
        "target": source_state.get("target_hint")
        if isinstance(source_state.get("target_hint"), dict)
        else None,
        "command_status": "NOT PROVIDED",
        "command_text_not_emitted": (
            "copy, bundle, and checker commands are withheld until an exact accepted "
            "copied lifecycle triplet exists"
        ),
        "machine_executable": False,
        "runner_command_available": False,
        "manual_staging_required_before_machine_actions": True,
        "manual_offline_next_steps": manual_steps,
        "deferred_missing_artifact_actions": missing_artifacts,
        "sibling_artifact_generation_deferred_until_source_log_ready": bool(missing_artifacts),
        "copy_ready_log_is_operational_only": True,
        "source_log_ready_to_copy": False,
        "source_log_closure_counts_as_evidence": False,
        "source_bound_blocker": True,
        "source_bound_blocker_kind": (
            "stale_or_passive_complete_role_triplet_source_only"
            if stale_passive_complete
            else "expired_window_missing_exact_triplet"
            if expired
            else "active_window_missing_exact_triplet_or_source_drift"
        ),
        "route_to_drift_or_source_bound_blocker": True,
        "blind_wait_recommended": False,
        "restart_recommended": False,
        "start_or_restart_recommended": False,
        "wait_or_restart_or_logout_instruction_allowed": False,
        "logout_or_reconnect_instruction_allowed": False,
        "player_logout_instruction_allowed_now": False,
        "wait_instruction_scope": (
            "bounded source-window state only; not a live wait, restart, "
            "or logout instruction from this status report"
        ),
        "expired_runtime_window_non_evidence": expired or stale_passive_complete,
        "active_runtime_window_waiting_for_exact_triplet": (
            not expired and not stale_passive_complete
        ),
        "active_window_not_closure_ready": not expired and not stale_passive_complete,
        "prepare_fresh_player_backed_window_required": expired or stale_passive_complete,
        "copy_bundle_commands_suppressed_until_exact_triplet": True,
        "copy_bundle_commands_allowed_before_exact_triplet": False,
        "exact_accepted_triplet_required_before_copy_bundle": True,
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        "non_evidence_context": {
            "classification": lifecycle["classification"],
            "session_end_missing_correlation_diagnostics": session_end_missing_correlation,
            "session_end_missing_correlation_counts_as_approved_runtime_evidence": False,
            "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence": False,
            "observer_enable_only_counts_as_approved_runtime_evidence": False,
            "observer_gate_only_counts_as_approved_runtime_evidence": False,
            "diagnostic_only_lines_count_as_approved_runtime_evidence": False,
            "player_presence_context_counts_as_approved_runtime_evidence": False,
            "accepted_input_only": (
                "same-run copied Obelisk.log with exact "
                "PlayerPrincipalLifecycleObserver event triplet and checked sibling set"
            ),
            "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        },
        "authorized_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def next_actions(
    closure: dict[str, Any],
    passive_state: dict[str, Any],
    closure_schema: dict[str, Any],
    copy_ready_context: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if closure_schema.get("valid") is not True:
        actions.append(
            {
                "action": "rerun_closure_request_with_exact_closure_helper",
                "blocking": True,
                "items": [str(closure_schema.get("schema"))],
                "expected_schema": CLOSURE_REQUEST_SCHEMA,
                "schema_blocker": closure_schema.get("blocker"),
                "forbidden_shortcut_alias_classes": list(FORBIDDEN_SHORTCUT_ALIAS_CLASSES),
                "authorized_by_this_report": False,
            }
        )
        return actions
    evidence_source_blockers = object_list(closure.get("evidence_source_blockers"))
    input_blockers = object_list(closure.get("input_blockers"))
    if evidence_source_blockers or input_blockers:
        guidance = closure_copy_guidance(closure)
        suggested_dir = guidance_suggested_closure_dir(guidance)
        suggested_run_id = guidance_suggested_closure_run_id(guidance)
        source_dir = closure.get("evidence_dir")
        actions.append(
            {
                "action": "stage_closure_compatible_player_principal_lifecycle_evidence_root",
                "blocking": True,
                "items": [str(source_dir)] if isinstance(source_dir, str) and source_dir else [],
                "missing_kind": "invalid_evidence_source",
                "evidence_source_blockers": evidence_source_blockers,
                "input_blockers": input_blockers,
                "closure_compatible_copy_guidance": guidance,
                "source_evidence_dir": source_dir,
                "invalid_source_evidence_dir": source_dir,
                "source_root_role": guidance.get(
                    "source_root_role",
                    "source_evidence_root_supplied_to_closure_helper",
                ),
                "source_run_id": guidance.get("source_run_id") or closure_run_id(closure),
                "source_root_valid_for_closure": False,
                "source_looks_like_passive_monitor_root": guidance.get(
                    "source_looks_like_passive_monitor_root"
                )
                is True,
                "closure_compatible_evidence_dir": suggested_dir,
                "suggested_closure_evidence_dir": suggested_dir,
                "suggested_valid_closure_run_id": suggested_run_id,
                "suggested_valid_closure_evidence_dir": suggested_dir,
                "suggested_valid_closure_root_role": guidance.get(
                    "suggested_valid_closure_root_role",
                    "suggested_valid_closure_root_for_manual_staging"
                    if suggested_dir
                    else "not_available_from_source_run_id",
                ),
                "passive_monitor_root_accepted_as_closure_evidence_dir": False,
                "source_accepted_as_closure_evidence_dir": False,
                "source_becomes_closure_root": False,
                "copy_or_stage_into_closure_compatible_run_required_before_closure": True,
                "explicit_execution_write_flags_required": True,
                "machine_action_suggested_for_invalid_passive_root": False,
                "machine_executable": False,
                "runner_command_available": False,
                "manual_staging_required_before_machine_actions": True,
                "command_status": "NOT PROVIDED",
                "command_text_not_emitted": (
                    "stage exact copied Obelisk.log and required sibling sidecars into the "
                    "suggested closure-compatible lifecycle evidence directory before rerunning closure"
                ),
                "manual_offline_next_steps": [
                    "do not use the passive monitor root as --evidence-dir for closure",
                    "stage a valid YYYYMMDDThhmmssZ-player-principal-lifecycle root with the copied log and required sidecars",
                    "rerun the closure helper against that valid root before deriving role or checker actions",
                ],
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
            }
        )
        return actions

    invalid_sidecars = string_list(closure.get("invalid_sidecars"))
    missing_roles = string_list(closure.get("missing_lifecycle_event_roles"))
    exact_triplet = closure_exact_triplet_state(closure)
    missing_triplet_labels = string_list(
        exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
    )
    missing_artifacts = ordered_missing_artifacts(closure)
    artifact_blockers = runtime_evidence_artifact_blockers(closure, exact_triplet)
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    triplet_route = exact_triplet_bundle_route(
        closure=closure,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        runtime_window_lifecycle=lifecycle,
    )
    if expired_non_evidence_runtime_window(copy_ready_context, exact_triplet):
        actions.append(
            runtime_window_non_evidence_action(
                missing_roles=missing_roles,
                exact_triplet=exact_triplet,
                copy_ready_context=copy_ready_context,
                missing_artifacts=missing_artifacts,
                expired=True,
                exact_triplet_route=triplet_route,
            )
        )
        return actions
    if active_runtime_window_waiting(copy_ready_context, exact_triplet):
        actions.append(
            runtime_window_non_evidence_action(
                missing_roles=missing_roles,
                exact_triplet=exact_triplet,
                copy_ready_context=copy_ready_context,
                missing_artifacts=missing_artifacts,
                expired=False,
                exact_triplet_route=triplet_route,
            )
        )
        return actions
    if invalid_sidecars:
        actions.append(
            {
                "action": "fix_invalid_sidecars",
                "blocking": True,
                "items": invalid_sidecars,
                "authorized_by_this_report": False,
            }
        )
    if missing_roles:
        if copy_ready_observer_only_no_role(copy_ready_context):
            actions.append(
                runtime_window_non_evidence_action(
                    missing_roles=missing_roles,
                    exact_triplet=exact_triplet,
                    copy_ready_context=copy_ready_context,
                    missing_artifacts=missing_artifacts,
                    expired=False,
                    exact_triplet_route=triplet_route,
                )
            )
            return actions
        actions.append(
            {
                "action": "wait_for_or_capture_missing_lifecycle_roles",
                "blocking": True,
                "items": missing_roles,
                "exact_triplet_bundle_route": triplet_route,
                "next_action_target": triplet_route["next_action_target"],
                "first_missing_runtime_evidence_path": triplet_route[
                    "first_missing_runtime_evidence_path"
                ],
                "fastest_missing_role_artifact_path": triplet_route[
                    "fastest_missing_role_artifact_path"
                ],
                "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
                "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
                "required_copied_lifecycle_event_triplet_labels": list(
                    REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
                ),
                "missing_copied_lifecycle_event_triplet": exact_triplet.get(
                    "missing_copied_lifecycle_event_triplet", []
                ),
                "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
                "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                "passive_complete_triplet_targets": passive_state.get(
                    "complete_observer_event_triplet_targets", []
                ),
                "non_evidence_context": {
                    "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence": False,
                    "player_presence_context_counts_as_approved_runtime_evidence": False,
                    "accepted_input_only": (
                        "same-run copied Obelisk.log with exact "
                        "PlayerPrincipalLifecycleObserver event triplet and checked sibling set"
                    ),
                    "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                },
                "authorized_by_this_report": False,
                "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
                "copied_log_presence_counts_as_approved_runtime_evidence": False,
                "stale_passive_tail_counts_as_approved_runtime_evidence": False,
                "direct_discord_send_counts_as_approved_runtime_evidence": False,
                "active_notice_state_counts_as_approved_runtime_evidence": False,
                "diagnostic_samples_count_as_approved_runtime_evidence": False,
            }
        )
    elif missing_triplet_labels:
        actions.append(
            {
                "action": "rerun_closure_request_with_exact_copied_triplet_match",
                "blocking": True,
                "items": missing_triplet_labels,
                "exact_triplet_bundle_route": triplet_route,
                "next_action_target": triplet_route["next_action_target"],
                "first_missing_runtime_evidence_path": triplet_route[
                    "first_missing_runtime_evidence_path"
                ],
                "fastest_missing_role_artifact_path": triplet_route[
                    "fastest_missing_role_artifact_path"
                ],
                "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
                "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
                "required_copied_lifecycle_event_triplet_labels": list(
                    REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
                ),
                "missing_copied_lifecycle_event_triplet": exact_triplet.get(
                    "missing_copied_lifecycle_event_triplet", []
                ),
                "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
                "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                "non_evidence_context": {
                    "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence": False,
                    "player_presence_context_counts_as_approved_runtime_evidence": False,
                    "accepted_input_only": (
                        "same-run copied Obelisk.log with exact "
                        "PlayerPrincipalLifecycleObserver event triplet and checked sibling set"
                    ),
                    "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                },
                "authorized_by_this_report": False,
                "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
                "copied_log_presence_counts_as_approved_runtime_evidence": False,
                "stale_passive_tail_counts_as_approved_runtime_evidence": False,
                "direct_discord_send_counts_as_approved_runtime_evidence": False,
                "active_notice_state_counts_as_approved_runtime_evidence": False,
                "diagnostic_samples_count_as_approved_runtime_evidence": False,
            }
        )
    if missing_artifacts:
        actions.append(
            {
                "action": "produce_checked_sibling_artifacts",
                "blocking": True,
                "items": missing_artifacts,
                "exact_triplet_bundle_route": triplet_route,
                "next_action_target": triplet_route["next_action_target"],
                "first_missing_runtime_evidence_path": triplet_route[
                    "first_missing_runtime_evidence_path"
                ],
                "fastest_missing_role_artifact_path": triplet_route[
                    "fastest_missing_role_artifact_path"
                ],
                "runtime_evidence_artifact_blockers": artifact_blockers,
                "missing_artifact_blockers": artifact_blockers["missing_artifact_blockers"],
                "missing_artifact_reasons": artifact_blockers["missing_artifact_reasons"],
                "first_missing_artifact": artifact_blockers["first_missing_artifact"],
                "missing_artifact_blocker_reason": artifact_blockers["first_blocker_reason"],
                "fastest_exact_path_from_fresh_copied_lifecycle_window": artifact_blockers[
                    "fastest_exact_path_from_fresh_copied_lifecycle_window"
                ],
                "approved_runtime_principal_lifecycle_evidence_bundle_json": (
                    APPROVED_RUNTIME_EVIDENCE_JSON
                ),
                "authorized_by_this_report": False,
                "counts_as_approved_runtime_evidence": False,
                "counts_as_runtime_evidence": False,
                "counts_as_sdk_evidence": False,
                "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
                "copied_log_presence_counts_as_approved_runtime_evidence": False,
                "stale_passive_tail_counts_as_approved_runtime_evidence": False,
                "direct_discord_send_counts_as_approved_runtime_evidence": False,
                "active_notice_state_counts_as_approved_runtime_evidence": False,
                "diagnostic_samples_count_as_approved_runtime_evidence": False,
            }
        )
    if not actions:
        actions.append(
            {
                "action": "run_approved_runtime_evidence_bundle_checker",
                "blocking": True,
                "authorized_by_this_report": False,
                "non_claim": "closure inputs look complete, but this status report does not build or approve evidence",
            }
        )
    return actions


def false_claim_summary() -> dict[str, bool]:
    return {key: False for key in SUMMARY_FALSE_CLAIMS}


def operator_action_entry(action: str, items: list[str]) -> dict[str, Any]:
    return {
        "action": action,
        "items": items,
        "allowed_under_recorded_standing_debug_authority": True,
        "requires_exact_run_target_and_recorded_safety_limits": True,
        "authorized_by_this_report": False,
        "server_operations_authorized_by_this_report": False,
        "runtime_work_authorized_by_this_report": False,
        "marker_env_changes_authorized_by_this_report": False,
        "workspace_writes_authorized_by_this_report": False,
        "creates_sidecars_by_this_report": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "grants_readiness_claims": False,
        "standing_authority_counts_as_runtime_progress": False,
        "standing_authority_counts_as_sdk_progress": False,
        "standing_authority_grants_runtime_readiness": False,
    }


def standing_debug_authority_actions(
    closure: dict[str, Any],
    *,
    standing_debug_authority_recorded: bool,
    closure_schema_valid: bool,
    runtime_window_lifecycle: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not standing_debug_authority_recorded or not closure_schema_valid:
        return []
    if closure_blocking_inputs(closure)["has_invalid_source"]:
        return []
    if runtime_window_lifecycle and (
        runtime_window_lifecycle.get("close_or_classify_as_non_evidence") is True
        or runtime_window_lifecycle.get("active_waiting_not_closure_ready") is True
    ):
        return []

    actions: list[dict[str, Any]] = []
    missing_roles = string_list(closure.get("missing_lifecycle_event_roles"))
    missing_artifacts = ordered_missing_artifacts(closure)
    invalid_sidecars = string_list(closure.get("invalid_sidecars"))
    exact_triplet = closure_exact_triplet_state(closure)
    missing_triplet_labels = string_list(
        exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
    )

    if invalid_sidecars:
        actions.append(
            operator_action_entry(
                "replace_invalid_sidecars_for_same_copied_evidence_run",
                invalid_sidecars,
            )
        )
    if missing_roles:
        actions.append(
            operator_action_entry(
                "continue_exact_player_principal_lifecycle_runtime_observation_for_missing_roles",
                missing_roles,
            )
        )
    elif missing_triplet_labels:
        actions.append(
            operator_action_entry(
                "rerun_closure_request_or_capture_exact_copied_lifecycle_triplet",
                missing_triplet_labels,
            )
        )
    if missing_artifacts:
        actions.append(
            operator_action_entry(
                "complete_checked_sibling_artifacts_for_same_run",
                missing_artifacts,
            )
        )
    if not actions:
        actions.append(
            operator_action_entry(
                "run_approved_runtime_evidence_checker_on_completed_sibling_set",
                [],
            )
        )
    return actions


def operator_headline(
    *,
    status: str,
    missing_roles: list[str],
    missing_triplet_labels: list[str],
    missing_artifacts: list[str],
    invalid_sidecars: list[str],
    invalid_source: bool,
    closure_schema_valid: bool,
    standing_debug_authority_recorded: bool,
    active_observer_only_no_role_window: bool,
    expired_runtime_window_non_evidence: bool,
    active_runtime_window_waiting_for_exact_triplet: bool,
) -> str:
    blockers: list[str] = []
    if not closure_schema_valid:
        blockers.append("invalid closure report schema")
    if invalid_source:
        blockers.append("invalid evidence source root")
    if invalid_sidecars:
        blockers.append("invalid sidecars")
    if expired_runtime_window_non_evidence:
        blockers.append("expired runtime window classified as non-evidence")
    elif active_runtime_window_waiting_for_exact_triplet:
        blockers.append("active runtime window waiting for exact lifecycle triplet")
    elif active_observer_only_no_role_window:
        blockers.append("observer-enable-only source log with no lifecycle roles")
    elif missing_roles:
        blockers.append("missing lifecycle roles")
    elif missing_triplet_labels:
        blockers.append("missing exact copied lifecycle triplet")
    if missing_artifacts:
        blockers.append("missing required sibling artifacts")
    blocker_text = ", ".join(blockers) if blockers else status
    authority_text = (
        "recorded standing debug authority can support exact scoped operator follow-up actions"
        if standing_debug_authority_recorded
        else "no standing debug authority was asserted to this report"
    )
    return f"blocked by {blocker_text}; {authority_text}; no evidence or readiness claim is made"


def operator_action_summary(
    closure: dict[str, Any],
    passive_state: dict[str, Any],
    route_gate: dict[str, Any],
    monitor_context: dict[str, Any],
    beta_notice_context: dict[str, Any],
    copy_ready_context: dict[str, Any],
    *,
    status: str,
    closure_schema: dict[str, Any],
    standing_debug_authority_recorded: bool,
    standing_debug_authority_reference: str,
    standing_debug_authority_source: str,
) -> dict[str, Any]:
    missing_roles = string_list(closure.get("missing_lifecycle_event_roles"))
    missing_artifacts = ordered_missing_artifacts(closure)
    invalid_sidecars = string_list(closure.get("invalid_sidecars"))
    invalid_source = closure_blocking_inputs(closure)["has_invalid_source"]
    exact_triplet = closure_exact_triplet_state(closure)
    artifact_blockers = runtime_evidence_artifact_blockers(closure, exact_triplet)
    runtime_window_lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    expired_window_non_evidence = (
        runtime_window_lifecycle.get("close_or_classify_as_non_evidence") is True
    )
    active_window_waiting = (
        runtime_window_lifecycle.get("active_waiting_not_closure_ready") is True
    )
    missing_triplet_labels = string_list(
        exact_triplet.get("missing_copied_lifecycle_event_triplet_labels")
    )
    actions = standing_debug_authority_actions(
        closure,
        standing_debug_authority_recorded=standing_debug_authority_recorded,
        closure_schema_valid=closure_schema.get("valid") is True,
        runtime_window_lifecycle=runtime_window_lifecycle,
    )
    player_availability = runtime_player_availability_context(passive_state, monitor_context)
    active_observer_only = copy_ready_observer_only_no_role(copy_ready_context)
    return {
        "headline": operator_headline(
            status=status,
            missing_roles=missing_roles,
            missing_triplet_labels=missing_triplet_labels,
            missing_artifacts=missing_artifacts,
            invalid_sidecars=invalid_sidecars,
            invalid_source=invalid_source,
            closure_schema_valid=closure_schema.get("valid") is True,
            standing_debug_authority_recorded=standing_debug_authority_recorded,
            active_observer_only_no_role_window=active_observer_only,
            expired_runtime_window_non_evidence=expired_window_non_evidence,
            active_runtime_window_waiting_for_exact_triplet=active_window_waiting,
        ),
        "run_id": closure_run_id(closure),
        "status": status,
        "blocking_inputs": {
            "invalid_sidecars": invalid_sidecars,
            "missing_lifecycle_event_roles": missing_roles,
            "missing_copied_lifecycle_event_triplet_labels": missing_triplet_labels,
            "exact_copied_lifecycle_event_triplet_blockers": exact_triplet.get("blockers", []),
            "missing_required_artifacts": missing_artifacts,
            "missing_siblings": string_list(closure.get("missing_siblings")),
            "runtime_evidence_artifact_blockers": artifact_blockers,
            "missing_artifact_reasons": artifact_blockers["missing_artifact_reasons"],
            "first_missing_artifact": artifact_blockers["first_missing_artifact"],
            "first_missing_artifact_blocker_reason": artifact_blockers["first_blocker_reason"],
            "closure_schema_blocker": closure_schema.get("blocker"),
            "route_blocker": route_gate.get("current_route_blocker"),
            "active_observer_only_no_role_window": active_observer_only,
            "runtime_window_lifecycle": runtime_window_lifecycle,
            "expired_runtime_window_non_evidence": expired_window_non_evidence,
            "active_runtime_window_waiting_for_exact_triplet": active_window_waiting,
            "copy_bundle_commands_suppressed_until_exact_triplet": (
                runtime_window_lifecycle.get("copy_bundle_commands_suppressed_until_exact_triplet")
                is True
            ),
            "source_log_not_ready_classification": copy_ready_context.get(
                "source_log_not_ready_classification"
            ),
        },
        "recorded_standing_debug_authority": {
            "recorded": standing_debug_authority_recorded,
            "reference": standing_debug_authority_reference
            if standing_debug_authority_recorded
            else None,
            "source": standing_debug_authority_source
            if standing_debug_authority_recorded
            else None,
            "applies_to_operator_actions_only": standing_debug_authority_recorded,
            "must_match_exact_run_target_evidence_paths_and_safety_limits": True,
            "authorized_by_this_report": False,
            "server_operations_authorized_by_this_report": False,
            "runtime_work_authorized_by_this_report": False,
            "marker_env_changes_authorized_by_this_report": False,
            "workspace_writes_authorized_by_this_report": False,
            "discord_authorized_by_this_report": False,
            "publication_authorized_by_this_report": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "grants_readiness_claims": False,
            "standing_authority_counts_as_runtime_progress": False,
            "standing_authority_counts_as_sdk_progress": False,
            "standing_authority_grants_runtime_readiness": False,
        },
        "actions_allowed_under_recorded_standing_debug_authority": actions,
        "evidence_readiness_claims": false_claim_summary(),
        "operator_context_inputs": {
            "post_reboot_passive_monitor_log_supplied": monitor_context.get("present") is True,
            "post_reboot_passive_monitor_log_path": monitor_context.get("source_path"),
            "monitor_latest_tick_utc": monitor_context.get("monitor_latest_tick_utc"),
            "monitor_query_targets": sorted(
                monitor_context.get("query_status_by_target", {}).keys()
            )
            if isinstance(monitor_context.get("query_status_by_target"), dict)
            else [],
            "monitor_rcon_targets": sorted(
                monitor_context.get("rcon_status_by_target", {}).keys()
            )
            if isinstance(monitor_context.get("rcon_status_by_target"), dict)
            else [],
            "confirmed_beta_notice_json_supplied": beta_notice_context.get("present") is True,
            "confirmed_beta_notice_json_path": beta_notice_context.get("source_path"),
            "confirmed_beta_notice_completed": beta_notice_context.get("completed") is True,
            "confirmed_beta_notice_standing_launch_authority_recorded": (
                beta_notice_context.get("standing_launch_authority_recorded") is True
            ),
            "copy_ready_json_supplied": copy_ready_context.get("present") is True,
            "copy_ready_json_path": copy_ready_context.get("source_path"),
            "copy_ready_status": copy_ready_context.get("status"),
            "copy_readiness": copy_ready_context.get("copy_readiness"),
            "copy_ready_missing_roles": copy_ready_context.get("missing_roles", []),
            "copy_ready_roles_present": copy_ready_context.get("roles_present", []),
            "copy_ready_helper_copied_source_value": (
                copy_ready_context.get("copied_source_value") is True
            ),
            "copy_ready_active_observer_only_no_role_window": (
                copy_ready_context.get("active_observer_only_no_role_window") is True
            ),
            "copy_ready_source_log_not_ready_classification": copy_ready_context.get(
                "source_log_not_ready_classification"
            ),
            "runtime_window_lifecycle": runtime_window_lifecycle,
            "expired_runtime_window_non_evidence": expired_window_non_evidence,
            "active_runtime_window_waiting_for_exact_triplet": active_window_waiting,
            "copy_bundle_commands_suppressed_until_exact_triplet": (
                runtime_window_lifecycle.get("copy_bundle_commands_suppressed_until_exact_triplet")
                is True
            ),
            "copy_ready_target_hint": copy_ready_context.get("target_hint", {}),
            "copy_ready_manual_offline_next_steps": copy_ready_context.get(
                "manual_offline_next_steps",
                [],
            ),
            "runtime_player_availability": player_availability,
            "player_presence_context": player_availability,
            "player_presence_context_counts_as_approved_runtime_evidence": False,
            "player_presence_context_authorizes_runtime_capture": False,
            "no_players_currently_detected": (
                player_availability.get("no_players_currently_detected") is True
            ),
            "player_availability_classification": player_availability.get("classification"),
            "context_inputs_are_non_evidence": True,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
            "runtime_ready": False,
            "public_sdk_ready": False,
            **sdk_p0_non_progress_flags(),
        },
        "resume_context": {
            "source": "this_json_output_only",
            "sidecars_created_by_this_report": False,
            "passive_summary_present": passive_state.get("present") is True,
            "post_reboot_passive_monitor_context_present": monitor_context.get("present") is True,
            "confirmed_beta_notice_context_present": beta_notice_context.get("present") is True,
            "copy_ready_context_present": copy_ready_context.get("present") is True,
            "passive_complete_triplet_targets": passive_state.get(
                "complete_observer_event_triplet_targets", []
            ),
            "next_status_input_needed": (
                "exact_closure_request_json"
                if closure_schema.get("valid") is not True
                else "fresh_player_backed_window_request_after_non_evidence_close"
                if expired_window_non_evidence
                else "active_window_exact_triplet_or_window_end_status"
                if active_window_waiting
                else
                "accepted_bundle_checker_report"
                if not missing_roles and not missing_triplet_labels and not missing_artifacts and not invalid_sidecars
                else "same_run_roles_and_checked_sibling_artifacts"
            ),
        },
    }


def route_gate_state(route_gate: dict[str, Any], route_gate_returncode: int) -> dict[str, Any]:
    source_claims = {
        "runtime_ready": route_gate.get("runtime_ready") is True,
        "public_sdk_ready": route_gate.get("public_sdk_ready") is True,
        "promotion_ready": route_gate.get("promotion_ready") is True,
    }
    return {
        "returncode": route_gate_returncode,
        "schema": route_gate.get("schema"),
        "valid": route_gate.get("valid") is True,
        "planning_only": route_gate.get("planning_only") is True,
        "route_blocked": route_gate.get("route_blocked") is True,
        "current_route_blocker": route_gate.get("current_route_blocker"),
        "approved_runtime_evidence_missing_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        "checker_accepted_approved_evidence_required": True,
        "source_report_claims": source_claims,
        "source_claims_ignored_for_status": any(source_claims.values()),
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def overall_status(
    closure: dict[str, Any],
    passive_state: dict[str, Any],
    closure_schema: dict[str, Any],
    copy_ready_context: dict[str, Any],
) -> str:
    if closure_schema.get("valid") is not True:
        return "blocked_invalid_closure_report_schema"
    blockers = closure_blocking_inputs(closure)
    if blockers["has_invalid_source"]:
        return "blocked_invalid_evidence_source"
    exact_triplet = closure_exact_triplet_state(closure)
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    if lifecycle.get("stale_or_passive_complete_role_triplet_non_evidence") is True:
        return "blocked_stale_passive_complete_role_triplet_non_evidence"
    if expired_non_evidence_runtime_window(copy_ready_context, exact_triplet):
        return "blocked_expired_runtime_window_non_evidence_prepare_fresh_player_backed_window"
    if active_runtime_window_waiting(copy_ready_context, exact_triplet):
        return "blocked_active_runtime_window_waiting_for_exact_copied_triplet"
    if blockers["has_invalid_sidecars"]:
        return "blocked_invalid_sidecars"
    if blockers["has_missing_roles"]:
        if copy_ready_observer_only_no_role(copy_ready_context):
            return "blocked_observer_only_no_lifecycle_roles"
        return "blocked_missing_lifecycle_roles"
    if blockers["has_missing_exact_triplet"]:
        return "blocked_missing_exact_copied_lifecycle_triplet"
    if blockers["has_missing_artifacts"]:
        return "blocked_missing_required_artifacts"
    if closure_ready_for_checker(closure, closure_schema):
        return "closure_inputs_complete_bundle_checker_required"
    if passive_state.get("present") is False:
        return "blocked_closure_incomplete_no_passive_summary"
    return "blocked_closure_incomplete"


def machine_false_claim_flags() -> dict[str, bool]:
    return {
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "approved_runtime_evidence_present": False,
        "approved_runtime_evidence_ready": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "promotion_ready": False,
        "v1_completion_ready": False,
        "stable_sdk_ready": False,
        "publication_authorized": False,
        "discord_authorized": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "workspace_writes_authorized": False,
        "marker_env_changes_authorized": False,
        "grants_readiness_claims": False,
        **sdk_p0_non_progress_flags(),
    }


def player_principal_evidence_split_machine_actions(
    split_context: dict[str, Any],
) -> list[dict[str, Any]]:
    if split_context.get("present") is not True:
        return []
    actions = object_list(split_context.get("next_actions"))
    if not actions:
        return []
    output: list[dict[str, Any]] = []
    for index, action in enumerate(actions):
        action_name = str(action.get("action") or f"review_player_principal_evidence_split_{index}")
        action_kind = str(action.get("action_kind") or "player_principal_evidence_split_review")
        output.append(
            {
                "action_id": f"status.split:{normalized_split_key(action_name) or index}",
                "action": action_name,
                "action_kind": action_kind,
                "source": "status_report.player_principal_evidence_split",
                "status_report_source": "status.player_principal_evidence_split",
                "blocking": True,
                "artifact": action.get("artifact"),
                "role": action.get("role"),
                "items": action.get("items", []),
                "player_principal_evidence_split": split_context,
                "split_classification": split_context.get("classification"),
                "split_blockers": split_context.get("blockers", []),
                "next_status_input_needed": action.get("next_status_input_needed"),
                "exact_checkjoininprogress_route_wording": action.get(
                    "exact_checkjoininprogress_route_wording",
                    CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
                ),
                "command_status": "NOT PROVIDED",
                "command_text_not_emitted": (
                    "player-principal evidence split context is offline routing metadata; "
                    "this status report does not authorize runtime capture or emit live commands"
                ),
                "runner_command_available": False,
                "runner_command": None,
                "machine_executable": False,
                "requires_operator_authority_before_execution": True,
                "operator_authority_source_required": "fresh_current_turn_operator_message",
                "requires_fresh_current_turn_operator_approval": True,
                "manual_offline_next_steps": [
                    "preserve accepted start/end split material as non-counting contract-review context only",
                    "provide same-run exact CheckJoinInProgress(1,0) session_start_rejected material before strict bundle work",
                    "rerun the strict approved runtime evidence checker only after the copied sibling set is complete",
                ],
                "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
                "actionable_without_exact_copied_triplet": False,
                **machine_false_claim_flags(),
            }
        )
    return output


def attach_player_principal_evidence_split_context(
    actions: list[dict[str, Any]],
    split_context: dict[str, Any],
) -> list[dict[str, Any]]:
    if split_context.get("present") is not True:
        return actions
    annotated: list[dict[str, Any]] = []
    for action in actions:
        annotated.append(
            {
                **action,
                "player_principal_evidence_split": split_context,
                "player_principal_evidence_split_present": True,
                "player_principal_evidence_split_authorizes_runtime": False,
                "player_principal_evidence_split_counts_as_approved_runtime_evidence": False,
            }
        )
    split_actions = player_principal_evidence_split_machine_actions(split_context)
    if split_actions:
        return [*split_actions, *annotated]
    return annotated


def normalize_closure_machine_next_action(action: dict[str, Any], index: int) -> dict[str, Any]:
    normalized = dict(action)
    if action_is_invalid_passive_root(normalized):
        normalized.pop("command_text_not_executed", None)
        normalized.update(invalid_passive_root_manual_fields(normalized))
    normalized.setdefault("action_id", f"closure.machine_next_action:{index}")
    normalized.setdefault("source", "closure_request.machine_next_actions")
    normalized["status_report_source"] = "closure.machine_next_actions"
    normalized["selected_by_status_report"] = True
    normalized["accepted_by_status_report"] = False
    normalized["accepted_by_status_report_reason"] = (
        "routing_only_closure_action_not_evidence_acceptance"
    )
    normalized["partial_lifecycle_roles_count_as_complete_closure_material"] = False
    normalized["diagnostic_or_rejected_lifecycle_lines_count_as_complete_closure_material"] = False
    normalized.setdefault(
        "required_copied_lifecycle_event_triplet",
        required_copied_lifecycle_event_triplet(),
    )
    normalized.setdefault(
        "required_copied_lifecycle_event_triplet_labels",
        list(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
    )
    normalized.setdefault(
        "exact_copied_lifecycle_event_triplet_required_before_actionable",
        action_requires_exact_copied_triplet(normalized),
    )
    normalized.setdefault("actionable_without_exact_copied_triplet", False)
    normalized.update(machine_false_claim_flags())
    return normalized


def action_requires_exact_copied_triplet(action: dict[str, Any]) -> bool:
    action_name = str(action.get("action") or action.get("operation") or "")
    action_kind = str(action.get("action_kind") or "")
    command = str(action.get("command_text_not_executed") or "")
    haystack = f"{action_name} {action_kind} {command}"
    return any(
        token in haystack
        for token in (
            "copy_player_principal_lifecycle_ready_log.py",
            "copy_ready_player_principal_lifecycle_obelisk_log",
            "build_player_identity_runtime_principal_lifecycle_evidence_bundle.py",
            "build_approved_runtime_principal_lifecycle_evidence_bundle",
            "check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            "run_approved_runtime_evidence_checker",
            "check_player_principal_lifecycle_preflight.sh",
            "capture_post_window_stable_preflight_json",
            "check_player_identity_runtime_principal_lifecycle_window_manifest.py",
            "provide_completed_window_manifest_env_sibling",
        )
    )


def closure_machine_action_matches_blocking_inputs(
    action: dict[str, Any],
    blockers: dict[str, Any],
) -> bool:
    if blockers["has_blockers"] is False:
        return True

    action_name = str(action.get("action") or action.get("operation") or "")
    action_kind = str(action.get("action_kind") or "")
    artifact = str(action.get("artifact") or "")
    role = str(action.get("role") or "")
    items = set(string_list(action.get("items")))
    invalid_sidecars = set(blockers["invalid_sidecars"])
    missing_artifacts = set(blockers["missing_required_artifacts"]) | set(blockers["missing_siblings"])
    missing_roles = set(blockers["missing_lifecycle_event_roles"])
    missing_role_artifacts = {f"lifecycle-role/{missing_role}" for missing_role in missing_roles}
    missing_triplet_labels = set(blockers["missing_copied_lifecycle_event_triplet_labels"])
    missing_triplet_artifacts = {
        f"copied-lifecycle-triplet/{label}" for label in missing_triplet_labels
    }

    if action_kind == "checker" or "checker" in action_name:
        return False
    if (
        blockers["has_missing_exact_triplet"]
        and action_requires_exact_copied_triplet(action)
    ):
        return False
    if action_kind == "notice_action_required":
        return True
    if artifact in invalid_sidecars or items & invalid_sidecars:
        return True
    if artifact in missing_artifacts or items & missing_artifacts:
        return True
    if artifact in missing_role_artifacts or role in missing_roles or items & missing_role_artifacts:
        return True
    if artifact in missing_triplet_artifacts or items & missing_triplet_artifacts:
        return True
    if artifact == "Obelisk.log" and ("Obelisk.log" in missing_artifacts or missing_roles):
        return True
    if blockers["has_invalid_source"] and (
        action.get("missing_kind") == "invalid_evidence_source"
        or action_kind == "invalid_evidence_source"
        or action_name in {
        "copy_or_select_an_offline_evidence_directory",
        "provide_existing_evidence_directory",
        "stage_closure_compatible_player_principal_lifecycle_evidence_root",
        }
    ):
        return True
    return False


def status_machine_action_from_next_action(action: dict[str, Any], index: int) -> dict[str, Any]:
    action_name = str(action.get("action") or f"action_{index}")
    triplet_guidance = {
        key: action[key]
        for key in (
            "exact_triplet_bundle_route",
            "next_action_target",
            "first_missing_runtime_evidence_path",
            "fastest_missing_role_artifact_path",
            "required_copied_lifecycle_event_triplet",
            "required_copied_lifecycle_event_triplet_labels",
            "missing_copied_lifecycle_event_triplet",
            "missing_copied_lifecycle_event_triplet_labels",
            "exact_copied_lifecycle_event_triplet_required_before_actionable",
            "exact_checkjoininprogress_route_wording",
            "partial_lifecycle_material_counts_as_approved_runtime_evidence",
            "copied_log_presence_counts_as_approved_runtime_evidence",
            "stale_passive_tail_counts_as_approved_runtime_evidence",
            "direct_discord_send_counts_as_approved_runtime_evidence",
            "active_notice_state_counts_as_approved_runtime_evidence",
            "diagnostic_samples_count_as_approved_runtime_evidence",
        )
        if key in action
    }
    non_evidence_context = action.get("non_evidence_context")
    root_guidance = {
        key: action[key]
        for key in (
            "closure_compatible_copy_guidance",
            "source_evidence_dir",
            "invalid_source_evidence_dir",
            "source_root_role",
            "source_run_id",
            "source_root_valid_for_closure",
            "source_looks_like_passive_monitor_root",
            "closure_compatible_evidence_dir",
            "suggested_closure_evidence_dir",
            "suggested_valid_closure_run_id",
            "suggested_valid_closure_evidence_dir",
            "suggested_valid_closure_root_role",
            "source_accepted_as_closure_evidence_dir",
            "source_becomes_closure_root",
            "passive_monitor_root_accepted_as_closure_evidence_dir",
            "copy_or_stage_into_closure_compatible_run_required_before_closure",
            "explicit_execution_write_flags_required",
            "machine_action_suggested_for_invalid_passive_root",
            "machine_executable",
            "runner_command_available",
            "manual_staging_required_before_machine_actions",
            "command_text_not_emitted",
            "manual_offline_next_steps",
            "deferred_missing_role_offline_next_steps",
        )
        if key in action
    }
    artifact_guidance = {
        key: action[key]
        for key in (
            "runtime_evidence_artifact_blockers",
            "missing_artifact_blockers",
            "missing_artifact_reasons",
            "missing_artifact_blocker",
            "missing_artifact_blocker_reason",
            "first_missing_artifact",
            "fastest_exact_path_from_fresh_copied_lifecycle_window",
            "approved_runtime_principal_lifecycle_evidence_bundle_json",
            "approved_runtime_evidence_json_path",
            "copied_log_path",
            "window_manifest_path",
            "preflight_post_path",
            "required_script",
        )
        if key in action
    }
    source_log_guidance = {
        key: action[key]
        for key in (
            "source_log_not_ready",
            "observer_only_no_role_window",
            "copy_ready_log_context",
            "copy_ready_source_boundary",
            "runtime_window_lifecycle",
            "fresh_player_backed_window",
            "next_player_backed_window",
            "deferred_missing_artifact_actions",
            "sibling_artifact_generation_deferred_until_source_log_ready",
            "copy_ready_log_is_operational_only",
            "source_log_ready_to_copy",
            "source_log_closure_counts_as_evidence",
            "stale_or_passive_complete_role_triplet_non_evidence",
            "exact_copied_lifecycle_event_triplet_usable_for_checker",
            "machine_executable",
            "runner_command_available",
            "manual_staging_required_before_machine_actions",
            "source_bound_blocker",
            "source_bound_blocker_kind",
            "route_to_drift_or_source_bound_blocker",
            "blind_wait_recommended",
            "restart_recommended",
            "start_or_restart_recommended",
            "wait_or_restart_or_logout_instruction_allowed",
            "logout_or_reconnect_instruction_allowed",
            "player_logout_instruction_allowed_now",
            "wait_instruction_scope",
        )
        if key in action
    }
    return {
        "action_id": f"status.next_action:{action_name}",
        "action": action_name,
        "action_kind": action.get("action_kind", "status_synthesized"),
        "source": "status_report.next_actions",
        "status_report_source": "status.next_actions",
        "blocking": action.get("blocking", True),
        "items": action.get("items", []),
        "target": action.get("target") if isinstance(action.get("target"), dict) else None,
        "missing_kind": action.get("missing_kind"),
        "evidence_source_blockers": action.get("evidence_source_blockers", []),
        "input_blockers": action.get("input_blockers", []),
        "closure_compatible_copy_guidance": action.get("closure_compatible_copy_guidance"),
        "source_evidence_dir": action.get("source_evidence_dir"),
        "closure_compatible_evidence_dir": action.get("closure_compatible_evidence_dir"),
        "passive_monitor_root_accepted_as_closure_evidence_dir": action.get(
            "passive_monitor_root_accepted_as_closure_evidence_dir",
            False,
        ),
        "copy_or_stage_into_closure_compatible_run_required_before_closure": action.get(
            "copy_or_stage_into_closure_compatible_run_required_before_closure",
            False,
        ),
        "expired_runtime_window_non_evidence": action.get(
            "expired_runtime_window_non_evidence",
            False,
        ),
        "active_runtime_window_waiting_for_exact_triplet": action.get(
            "active_runtime_window_waiting_for_exact_triplet",
            False,
        ),
        "active_window_not_closure_ready": action.get("active_window_not_closure_ready", False),
        "prepare_fresh_player_backed_window_required": action.get(
            "prepare_fresh_player_backed_window_required",
            False,
        ),
        "copy_bundle_commands_suppressed_until_exact_triplet": action.get(
            "copy_bundle_commands_suppressed_until_exact_triplet",
            False,
        ),
        "copy_bundle_commands_allowed_before_exact_triplet": action.get(
            "copy_bundle_commands_allowed_before_exact_triplet",
            False,
        ),
        "exact_accepted_triplet_required_before_copy_bundle": action.get(
            "exact_accepted_triplet_required_before_copy_bundle",
            False,
        ),
        "explicit_execution_write_flags_required": action.get(
            "explicit_execution_write_flags_required",
            False,
        ),
        "required_roles": action.get("required_roles", []),
        "schema_blocker": action.get("schema_blocker"),
        "expected_schema": action.get("expected_schema"),
        "forbidden_shortcut_alias_classes": action.get(
            "forbidden_shortcut_alias_classes",
            list(FORBIDDEN_SHORTCUT_ALIAS_CLASSES),
        ),
        "authorized_to_run_now": False,
        "command_status": "NOT PROVIDED",
        **root_guidance,
        **source_log_guidance,
        **artifact_guidance,
        **triplet_guidance,
        "non_evidence_context": non_evidence_context
        if isinstance(non_evidence_context, dict)
        else {
            "diagnostic_only_handle_new_player_or_k2_post_login_lines_count_as_evidence": False,
            "player_presence_context_counts_as_approved_runtime_evidence": False,
            "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        },
        **machine_false_claim_flags(),
    }


def status_machine_action_for_checker(closure: dict[str, Any]) -> dict[str, Any]:
    manifest_path = closure.get("approved_bundle_path")
    command = None
    runner_command = None
    if isinstance(manifest_path, str) and manifest_path:
        command = (
            "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py "
            f"{shlex.quote(manifest_path)} --json"
        )
        runner_command = {
            "argv": [
                "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
                manifest_path,
                "--json",
            ],
            "execution_mode": "no_shell_offline_helper",
        }
    return {
        "action_id": "status.checker:approved_runtime_principal_lifecycle_evidence",
        "action": "run_approved_runtime_evidence_checker_on_copied_manifest",
        "action_kind": "checker",
        "source": "status_report.closure_inputs_complete",
        "status_report_source": "status.closure_inputs_complete",
        "blocking": True,
        "run_id": closure_run_id(closure),
        "artifact": "approved-bundle/approved-runtime-principal-lifecycle-evidence.json",
        "manifest_path": manifest_path,
        "items": ["approved-bundle/approved-runtime-principal-lifecycle-evidence.json"],
        "authorized_to_run_now": False,
        "command_status": "NOT EXECUTED" if command else "NOT PROVIDED",
        "command_text_not_executed": command,
        "runner_command_available": runner_command is not None,
        "runner_command": runner_command,
        "machine_executable": runner_command is not None,
        "writes_under_evidence_dir": False,
        "next_status_input_needed": "accepted_approved_runtime_evidence_checker_json",
        "accepted_checker_required_before_status_claim": True,
        "exact_checkjoininprogress_route_wording": CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
        "required_copied_lifecycle_event_triplet": required_copied_lifecycle_event_triplet(),
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
        "exact_copied_lifecycle_event_triplet_matched": True,
        "actionable_without_exact_copied_triplet": False,
        **machine_false_claim_flags(),
    }


def artifact_machine_action_id(artifact: str) -> str:
    normalized = re.sub(r"[^a-z0-9_.:-]+", "_", artifact.casefold()).strip("_")
    return f"status.missing:{normalized or 'artifact'}"


def closure_bundle_command_metadata(closure: dict[str, Any]) -> dict[str, Any]:
    metadata = closure.get("bundle_command_metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    commit = metadata.get("obelisk_commit", closure.get("obelisk_commit"))
    reviewed_by = metadata.get("reviewed_by", closure.get("reviewed_by"))
    review_note = metadata.get("review_note", closure.get("review_note"))
    blockers: list[str] = []

    if not isinstance(commit, str) or not commit:
        blockers.append("bundle_command_obelisk_commit_from_window_manifest_required")
        commit = "<window-manifest-obelisk_commit>"
    elif OBELISK_COMMIT_RE.fullmatch(commit) is None:
        blockers.append("bundle_command_obelisk_commit_from_closure_invalid")

    if not isinstance(reviewed_by, str) or not reviewed_by.strip():
        blockers.append("reviewed_by_required_for_direct_bundle_command")
        reviewed_by = "<reviewer>"

    if not isinstance(review_note, str) or not review_note.strip():
        blockers.append("review_note_required_for_direct_bundle_command")
        review_note = "<consume-only-review-note>"

    return {
        "schema": "obelisk.player-principal-lifecycle-status-bundle-command-metadata.v1",
        "metadata_source": "closure_json"
        if not blockers
        else "missing_or_invalid_closure_metadata",
        "obelisk_commit": commit,
        "reviewed_by": reviewed_by,
        "review_note": review_note,
        "metadata_resolved": not blockers,
        "blockers": blockers,
        "metadata_counts_as_approved_runtime_evidence": False,
        "metadata_counts_as_runtime_evidence": False,
        "metadata_counts_toward_sdk": False,
        "metadata_counts_toward_p0_dependency_chain": False,
    }


def artifact_command_fields(
    closure: dict[str, Any],
    artifact: str,
    exact_triplet: dict[str, Any],
    missing_artifacts: set[str],
) -> dict[str, Any]:
    evidence_dir = closure.get("evidence_dir")
    if not isinstance(evidence_dir, str) or not evidence_dir:
        return {
            "command_status": "NOT PROVIDED",
            "command_text_not_emitted": "evidence_dir missing from closure JSON",
            "runner_command_available": False,
            "runner_command": None,
            "machine_executable": False,
        }

    root = Path(evidence_dir)
    copied_log = root / "Obelisk.log"
    window_manifest = root / "window-manifest.env"
    if artifact == APPROVED_RUNTIME_EVIDENCE_JSON:
        metadata = closure_bundle_command_metadata(closure)
        preflight_argv = [
            BUNDLE_BUILDER_SCRIPT,
            "--preflight-only",
            "--evidence-dir",
            str(root),
        ]
        direct_builder_argv = [
            BUNDLE_BUILDER_SCRIPT,
            "--copied-log",
            str(copied_log),
            "--window-manifest",
            str(window_manifest),
            "--output-dir",
            str(root / "approved-bundle"),
            "--obelisk-commit",
            str(metadata["obelisk_commit"]),
            "--reviewed-by",
            str(metadata["reviewed_by"]),
            "--review-note",
            str(metadata["review_note"]),
        ]
        sibling_blockers = [
            artifact_name
            for artifact_name in (
                "Obelisk.log",
                "window-manifest.env",
                "preflight-post.json",
            )
            if artifact_name in missing_artifacts
        ]
        other_missing_inputs = sorted(
            artifact_name
            for artifact_name in missing_artifacts
            if artifact_name != APPROVED_RUNTIME_EVIDENCE_JSON
            and artifact_name not in sibling_blockers
        )
        direct_builder_blockers = [
            *[
                f"bundle_input_missing:{artifact_name}"
                for artifact_name in sibling_blockers
            ],
            *[
                f"bundle_input_missing:{artifact_name}"
                for artifact_name in other_missing_inputs
            ],
            *(
                []
                if exact_triplet.get("complete") is True
                else ["exact_copied_lifecycle_event_triplet_required_before_bundle_command"]
            ),
            *metadata["blockers"],
        ]
        direct_builder_available = (
            exact_triplet.get("complete") is True
            and not sibling_blockers
            and not other_missing_inputs
            and not metadata["blockers"]
        )
        return {
            "command_status": "NOT EXECUTED",
            "command_text_not_executed": " ".join(shlex.quote(part) for part in preflight_argv),
            "command_semantics": "read_only_bundle_input_preflight",
            "runner_command_available": True,
            "runner_command": {
                "argv": preflight_argv,
                "execution_mode": "no_shell_offline_helper",
            },
            "machine_executable": True,
            "command_writes_under_evidence_dir": False,
            "bundle_preflight_command_available": True,
            "bundle_preflight_command": {
                "argv": preflight_argv,
                "command_text_not_executed": " ".join(shlex.quote(part) for part in preflight_argv),
                "execution_mode": "no_shell_offline_helper",
                "writes_under_evidence_dir": False,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            },
            "direct_bundle_builder_command_available": direct_builder_available,
            "direct_bundle_builder_command": {
                "argv": direct_builder_argv,
                "command_text_not_executed": " ".join(
                    shlex.quote(part) for part in direct_builder_argv
                ),
                "execution_mode": "no_shell_offline_helper",
                "writes_under_evidence_dir": True,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            }
            if direct_builder_available
            else None,
            "direct_bundle_builder_command_template": {
                "argv": direct_builder_argv,
                "command_text_template": " ".join(shlex.quote(part) for part in direct_builder_argv),
                "path_arguments_resolved": True,
                "metadata_placeholders": []
                if metadata["metadata_resolved"]
                else [
                    str(value)
                    for value in (
                        metadata["obelisk_commit"],
                        metadata["reviewed_by"],
                        metadata["review_note"],
                    )
                    if str(value).startswith("<")
                ],
                "execution_mode": "no_shell_offline_helper",
            },
            "direct_bundle_builder_command_metadata": metadata,
            "direct_bundle_builder_command_blockers": direct_builder_blockers,
            "direct_bundle_builder_command_blocker_count": len(direct_builder_blockers),
            "next_after_preflight": "resolve_direct_bundle_builder_command_blockers_or_rerun_closure_helper_with_review_metadata",
            "checker_command_after_bundle_template": {
                "argv": [
                    BUNDLE_CHECKER_SCRIPT,
                    str(root / APPROVED_RUNTIME_EVIDENCE_JSON),
                    "--json",
                ],
                "command_text_template": (
                    f"{BUNDLE_CHECKER_SCRIPT} "
                    f"{shlex.quote(str(root / APPROVED_RUNTIME_EVIDENCE_JSON))} --json"
                ),
                "blocked_until": [APPROVED_RUNTIME_EVIDENCE_JSON],
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            },
        }
    if (
        artifact == "window-manifest.env"
        and exact_triplet.get("complete") is True
        and "Obelisk.log" not in missing_artifacts
    ):
        command = (
            "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py "
            f"--emit-template {shlex.quote(str(window_manifest))} "
            f"--copied-log {shlex.quote(str(copied_log))}"
        )
        return {
            "command_status": "NOT EXECUTED",
            "command_text_not_executed": command,
            "validation_command_text_not_executed": (
                "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py "
                f"--json --post-window-replay {shlex.quote(str(window_manifest))}"
            ),
            "runner_command_available": True,
            "runner_command": {
                "argv": [
                    "scripts/check_player_identity_runtime_principal_lifecycle_window_manifest.py",
                    "--emit-template",
                    str(window_manifest),
                    "--copied-log",
                    str(copied_log),
                ],
                "execution_mode": "no_shell_offline_helper",
            },
            "machine_executable": True,
        }

    detail = ARTIFACT_BLOCKER_DETAILS.get(artifact, {})
    return {
        "command_status": "NOT PROVIDED",
        "command_text_not_emitted": detail.get(
            "command_text_not_emitted",
            "exact helper command unavailable from this status report; rerun closure helper with required binding metadata",
        ),
        "runner_command_available": False,
        "runner_command": None,
        "machine_executable": False,
    }


def status_machine_action_for_missing_artifact(
    closure: dict[str, Any],
    artifact: str,
    exact_triplet: dict[str, Any],
    missing_artifacts: set[str],
    exact_triplet_route: dict[str, Any],
) -> dict[str, Any]:
    detail = artifact_blocker_detail(closure, exact_triplet, artifact)
    command_fields = artifact_command_fields(closure, artifact, exact_triplet, missing_artifacts)
    evidence_dir = closure.get("evidence_dir")
    return {
        "action_id": artifact_machine_action_id(artifact),
        "action": detail["action"],
        "operation": detail["action"],
        "action_kind": "missing_artifact",
        "missing_kind": "missing_artifact",
        "source": "status_report.runtime_evidence_artifact_blockers",
        "status_report_source": "status.runtime_evidence_artifact_blockers",
        "blocking": True,
        "run_id": closure_run_id(closure),
        "evidence_dir": evidence_dir,
        "artifact": artifact,
        "items": [artifact],
        "exact_triplet_bundle_route": exact_triplet_route,
        "next_action_target": exact_triplet_route["next_action_target"],
        "first_missing_runtime_evidence_path": exact_triplet_route[
            "first_missing_runtime_evidence_path"
        ],
        "fastest_missing_role_artifact_path": exact_triplet_route[
            "fastest_missing_role_artifact_path"
        ],
        "missing_artifact_blocker": detail,
        "missing_artifact_blocker_reason": detail["reason"],
        "required_script": detail["required_script"],
        "blocked_until": detail["blocked_until"],
        "copied_log_path": artifact_output_path(closure, "Obelisk.log"),
        "window_manifest_path": artifact_output_path(closure, "window-manifest.env"),
        "preflight_post_path": artifact_output_path(closure, "preflight-post.json"),
        "approved_runtime_evidence_json_path": artifact_output_path(
            closure,
            APPROVED_RUNTIME_EVIDENCE_JSON,
        ),
        "approved_runtime_principal_lifecycle_evidence_bundle_json": (
            APPROVED_RUNTIME_EVIDENCE_JSON
        ),
        "authorized_to_run_now": False,
        "writes_under_evidence_dir": artifact in {
            "window-manifest.env",
            "preflight-post.json",
            APPROVED_RUNTIME_EVIDENCE_JSON,
        },
        "exact_copied_lifecycle_event_triplet_required_before_actionable": True,
        "exact_copied_lifecycle_event_triplet_matched": exact_triplet.get("complete") is True,
        "missing_copied_lifecycle_event_triplet": exact_triplet.get(
            "missing_copied_lifecycle_event_triplet",
            [],
        ),
        "missing_copied_lifecycle_event_triplet_labels": exact_triplet.get(
            "missing_copied_lifecycle_event_triplet_labels",
            [],
        ),
        "actionable_without_exact_copied_triplet": False,
        "partial_lifecycle_material_counts_as_approved_runtime_evidence": False,
        "copied_log_presence_counts_as_approved_runtime_evidence": False,
        "stale_passive_tail_counts_as_approved_runtime_evidence": False,
        "direct_discord_send_counts_as_approved_runtime_evidence": False,
        "active_notice_state_counts_as_approved_runtime_evidence": False,
        "diagnostic_samples_count_as_approved_runtime_evidence": False,
        **command_fields,
        **machine_false_claim_flags(),
    }


def status_machine_actions_for_missing_artifacts(
    closure: dict[str, Any],
    exact_triplet: dict[str, Any],
) -> list[dict[str, Any]]:
    missing = ordered_missing_artifacts(closure)
    missing_set = set(missing)
    artifact_blockers = runtime_evidence_artifact_blockers(closure, exact_triplet)
    triplet_route = exact_triplet_bundle_route(
        closure=closure,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        runtime_window_lifecycle={},
    )
    return [
        status_machine_action_for_missing_artifact(
            closure,
            artifact,
            exact_triplet,
            missing_set,
            triplet_route,
        )
        for artifact in missing
    ]


def status_machine_next_actions(
    closure: dict[str, Any],
    status_actions: list[dict[str, Any]],
    closure_schema: dict[str, Any],
    copy_ready_context: dict[str, Any],
    split_context: dict[str, Any],
) -> list[dict[str, Any]]:
    if closure_schema.get("valid") is not True:
        return attach_player_principal_evidence_split_context(
            [
            {
                **status_machine_action_from_next_action(status_actions[0], 0),
                "action_kind": "invalid_closure_schema",
                "required_script": str(CLOSURE_REQUEST.relative_to(REPO_ROOT)),
            }
            ],
            split_context,
        )
    blockers = closure_blocking_inputs(closure)
    exact_triplet = closure_exact_triplet_state(closure)
    artifact_blockers = runtime_evidence_artifact_blockers(closure, exact_triplet)
    runtime_window_lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    triplet_route = exact_triplet_bundle_route(
        closure=closure,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        runtime_window_lifecycle=runtime_window_lifecycle,
    )
    if (
        (
            expired_non_evidence_runtime_window(copy_ready_context, exact_triplet)
            or active_runtime_window_waiting(copy_ready_context, exact_triplet)
            or copy_ready_observer_only_no_role(copy_ready_context)
        )
        and status_actions
    ):
        return attach_player_principal_evidence_split_context(
            attach_exact_triplet_bundle_route(
                [status_machine_action_from_next_action(status_actions[0], 0)],
                triplet_route,
            ),
            split_context,
        )
    closure_actions = closure.get("machine_next_actions")
    if isinstance(closure_actions, list) and closure_actions:
        normalized = [
            normalize_closure_machine_next_action(action, index)
            for index, action in enumerate(closure_actions)
            if isinstance(action, dict)
        ]
        if blockers["has_blockers"]:
            matching_actions = [
                action
                for action in normalized
                if closure_machine_action_matches_blocking_inputs(action, blockers)
            ]
            if matching_actions:
                return attach_player_principal_evidence_split_context(
                    attach_exact_triplet_bundle_route(matching_actions, triplet_route),
                    split_context,
                )
        elif normalized:
            return attach_player_principal_evidence_split_context(
                attach_exact_triplet_bundle_route(normalized, triplet_route),
                split_context,
            )
    if closure_ready_for_checker(closure, closure_schema):
        return attach_player_principal_evidence_split_context(
            [status_machine_action_for_checker(closure)],
            split_context,
        )
    if (
        blockers["has_missing_artifacts"]
        and not blockers["has_missing_roles"]
        and not blockers["has_missing_exact_triplet"]
    ):
        return attach_player_principal_evidence_split_context(
            status_machine_actions_for_missing_artifacts(closure, exact_triplet),
            split_context,
        )
    return attach_player_principal_evidence_split_context(
        attach_exact_triplet_bundle_route(
            [
                status_machine_action_from_next_action(action, index)
                for index, action in enumerate(status_actions)
            ],
            triplet_route,
        ),
        split_context,
    )


def first_machine_next_action_summary(actions: list[dict[str, Any]]) -> dict[str, Any]:
    if not actions:
        return {
            "present": False,
            "action_id": None,
            "action": None,
            "action_kind": None,
            "artifact": None,
            "role": None,
            "target": None,
            "command_status": "NOT PROVIDED",
            "command_text_not_executed": None,
            "command_text_not_emitted": None,
            "exact_command_available": False,
            **machine_false_claim_flags(),
        }
    first = actions[0]
    command = first.get("command_text_not_executed")
    runner_command = first.get("runner_command") if isinstance(first.get("runner_command"), dict) else None
    runner_argv = (
        runner_command.get("argv")
        if isinstance(runner_command, dict) and isinstance(runner_command.get("argv"), list)
        else None
    )
    return {
        "present": True,
        "action_id": first.get("action_id"),
        "action": first.get("action"),
        "action_kind": first.get("action_kind"),
        "artifact": first.get("artifact"),
        "role": first.get("role"),
        "target": first.get("target") if isinstance(first.get("target"), dict) else None,
        "command_status": first.get("command_status", "NOT PROVIDED"),
        "command_text_not_executed": command,
        "command_text_not_emitted": first.get("command_text_not_emitted"),
        "exact_command_available": isinstance(command, str) and bool(command),
        "runner_command_available": first.get("runner_command_available") is True,
        "runner_command": runner_command,
        "structured_argv": runner_argv,
        "exact_triplet_bundle_route": first.get("exact_triplet_bundle_route")
        if isinstance(first.get("exact_triplet_bundle_route"), dict)
        else {},
        "next_action_target": first.get("next_action_target"),
        "first_missing_runtime_evidence_path": first.get(
            "first_missing_runtime_evidence_path"
        ),
        "authorized_to_run_now": False,
        **machine_false_claim_flags(),
    }


def runtime_evidence_fast_path_summary(
    *,
    closure: dict[str, Any],
    closure_schema: dict[str, Any],
    status: str,
    exact_triplet: dict[str, Any],
    artifact_blockers: dict[str, Any],
    runtime_window_lifecycle: dict[str, Any],
    machine_actions: list[dict[str, Any]],
    first_machine_action: dict[str, Any],
    closure_checker_ready: bool,
) -> dict[str, Any]:
    blockers = closure_blocking_inputs(closure)
    first_raw = machine_actions[0] if machine_actions else {}
    missing_labels = blockers["missing_copied_lifecycle_event_triplet_labels"]
    missing_artifacts = artifact_blockers.get("missing_artifacts", [])
    first_artifact_blocker = (
        first_raw.get("missing_artifact_blocker")
        if isinstance(first_raw.get("missing_artifact_blocker"), dict)
        else {}
    )
    first_side_effect_domain = (
        first_artifact_blocker.get("side_effect_domain")
        or first_raw.get("side_effect_domain")
        or first_raw.get("action_kind")
    )
    first_structured_helper = first_machine_action.get("runner_command_available") is True
    first_manual_or_live_step = bool(first_machine_action.get("present")) and not first_structured_helper
    live_step_required = bool(
        missing_labels
        or first_side_effect_domain in {"live_log_copy", "post_window_preflight_live_read"}
        or runtime_window_lifecycle.get("active_waiting_not_closure_ready") is True
    )
    if missing_labels:
        first_blocking_category = "missing_exact_copied_lifecycle_triplet"
    elif missing_artifacts:
        first_blocking_category = "missing_required_runtime_evidence_artifact"
    elif closure_checker_ready:
        first_blocking_category = "approved_bundle_checker_required"
    else:
        first_blocking_category = "closure_or_source_context_incomplete"

    artifact_path_status = artifact_blockers.get(
        "fastest_exact_path_from_fresh_copied_lifecycle_window",
        [],
    )
    sequence: list[dict[str, Any]] = [
        {
            "stage": "exact_copied_lifecycle_triplet",
            "status": "complete" if exact_triplet.get("complete") is True else "missing",
            "required_labels": list(REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS),
            "missing_labels": missing_labels,
            "manual_player_backed_runtime_window_required": bool(missing_labels),
            "runner_command_available": False,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        }
    ]
    for artifact_state in artifact_path_status:
        if not isinstance(artifact_state, dict):
            continue
        sequence.append(
            {
                "stage": "required_runtime_evidence_artifact",
                "artifact": artifact_state.get("artifact"),
                "status": artifact_state.get("status"),
                "side_effect_domain": artifact_state.get("side_effect_domain"),
                "blocked_until": artifact_state.get("blocked_until", []),
                "runner_command_available": artifact_state.get("runner_command_available") is True,
                "approved_runtime_evidence": False,
                "counts_as_approved_runtime_evidence": False,
            }
        )
    sequence.append(
        {
            "stage": "approved_bundle_checker",
            "status": (
                "structured_checker_command_available"
                if closure_checker_ready
                else "blocked_until_exact_sibling_set_complete"
            ),
            "required_script": BUNDLE_CHECKER_SCRIPT if closure_checker_ready else None,
            "runner_command_available": closure_checker_ready,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
        }
    )

    return {
        "schema": RUNTIME_EVIDENCE_FAST_PATH_SCHEMA,
        "status": status,
        "current_route_blocker": "approved_runtime_evidence_missing",
        "fastest_valid_path": (
            "fresh_player_backed_window_exact_triplet_then_same_run_sibling_artifacts_then_checker"
        ),
        "first_blocking_category": first_blocking_category,
        "first_missing_role": blockers["missing_lifecycle_event_roles"][0]
        if blockers["missing_lifecycle_event_roles"]
        else None,
        "first_missing_copied_lifecycle_event_label": missing_labels[0]
        if missing_labels
        else None,
        "first_missing_artifact": artifact_blockers.get("first_missing_artifact"),
        "first_missing_artifact_blocker_reason": artifact_blockers.get("first_blocker_reason"),
        "first_action_id": first_machine_action.get("action_id"),
        "first_action": first_machine_action.get("action"),
        "first_action_kind": first_machine_action.get("action_kind"),
        "first_action_command_status": first_machine_action.get("command_status"),
        "first_action_side_effect_domain": first_side_effect_domain,
        "first_structured_offline_helper_available": first_structured_helper,
        "first_structured_offline_helper_argv": first_machine_action.get("structured_argv"),
        "first_manual_or_live_step_required": first_manual_or_live_step,
        "live_step_required_before_first_offline_helper": live_step_required
        and not first_structured_helper,
        "closure_schema_valid": closure_schema.get("valid") is True,
        "closure_ready_for_checker": closure_checker_ready,
        "exact_triplet_complete": exact_triplet.get("complete") is True,
        "missing_lifecycle_event_roles": blockers["missing_lifecycle_event_roles"],
        "missing_copied_lifecycle_event_triplet_labels": missing_labels,
        "missing_required_artifacts": missing_artifacts,
        "sequence": sequence,
        "non_authorization": (
            "fast-path status view only; it does not authorize live operations, copy logs, "
            "write sidecars, run Discord, approve evidence, or advance SDK/P0 progress"
        ),
        "authorized_by_this_report": False,
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def strict_triplet_selector_result(
    closure: dict[str, Any],
    copy_ready_context: dict[str, Any],
    machine_actions: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_triplet = closure_exact_triplet_state(closure)
    blockers = closure_blocking_inputs(closure)
    lifecycle = runtime_window_lifecycle_state(copy_ready_context, exact_triplet)
    source_only_complete = (
        lifecycle.get("stale_or_passive_complete_role_triplet_non_evidence") is True
    )
    if source_only_complete:
        selector_result = "rejected_stale_or_passive_complete_role_triplet_non_evidence"
    elif exact_triplet.get("complete") is True and blockers["has_blockers"] is False:
        selector_result = "strict_triplet_complete_checker_required"
    elif exact_triplet.get("complete") is True:
        selector_result = "strict_triplet_complete_missing_required_sidecars_or_inputs"
    else:
        selector_result = "strict_triplet_incomplete"

    first_action = machine_actions[0] if machine_actions else {}
    return {
        "schema": STRICT_TRIPLET_SELECTOR_SCHEMA,
        "selector_result": selector_result,
        "strict_triplet_present": exact_triplet.get("present") is True,
        "strict_triplet_complete": exact_triplet.get("complete") is True,
        "strict_triplet_source_complete": exact_triplet.get("source_complete") is True,
        "strict_triplet_usable_for_checker": bool(
            exact_triplet.get("complete") is True
            and blockers["has_blockers"] is False
            and not source_only_complete
        ),
        "required_roles": list(REQUIRED_LIFECYCLE_ROLES),
        "missing_lifecycle_event_roles": blockers["missing_lifecycle_event_roles"],
        "required_copied_lifecycle_event_triplet_labels": list(
            REQUIRED_COPIED_LIFECYCLE_EVENT_TRIPLET_LABELS
        ),
        "missing_copied_lifecycle_event_triplet_labels": blockers[
            "missing_copied_lifecycle_event_triplet_labels"
        ],
        "invalid_sidecars": blockers["invalid_sidecars"],
        "sidecar_validation_blockers": blockers["sidecar_validation_blockers"],
        "missing_required_artifacts": blockers["missing_required_artifacts"],
        "missing_siblings": blockers["missing_siblings"],
        "copy_ready_source_boundary": lifecycle.get("copy_ready_source_boundary", {}),
        "stale_or_passive_complete_role_triplet_non_evidence": source_only_complete,
        "next_safe_action_id": first_action.get("action_id"),
        "next_safe_action": first_action.get("action"),
        "next_safe_action_kind": first_action.get("action_kind"),
        "next_safe_action_command_status": first_action.get("command_status", "NOT PROVIDED"),
        "next_safe_action_runner_command_available": (
            first_action.get("runner_command_available") is True
        ),
        "approved_runtime_evidence": False,
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def runtime_evidence_acceptance_state(
    *,
    closure_schema: dict[str, Any],
    closure_checker_ready: bool,
    runtime_window_lifecycle: dict[str, Any],
    closure_blockers: dict[str, Any],
    artifact_blockers: dict[str, Any],
) -> dict[str, Any]:
    expired_no_evidence = (
        runtime_window_lifecycle.get("close_or_classify_as_non_evidence") is True
    )
    active_waiting = (
        runtime_window_lifecycle.get("active_waiting_not_closure_ready") is True
    )
    if expired_no_evidence:
        classification = "expired_window_no_evidence"
    elif active_waiting:
        classification = "active_window_waiting_for_exact_triplet"
    elif closure_checker_ready:
        classification = "accepted_ready_for_checker_not_checker_accepted"
    elif closure_schema.get("valid") is not True:
        classification = "invalid_closure_report_not_ready"
    else:
        classification = "blocked_no_checker_accepted_evidence"
    return {
        "schema": RUNTIME_EVIDENCE_ACCEPTANCE_STATE_SCHEMA,
        "classification": classification,
        "expired_no_evidence": expired_no_evidence,
        "active_window_waiting_not_ready": active_waiting,
        "accepted_ready": closure_checker_ready and not expired_no_evidence,
        "accepted_ready_for_checker": closure_checker_ready and not expired_no_evidence,
        "checker_accepted_ready": False,
        "approved_runtime_evidence_accepted_by_checker": False,
        "closure_schema_valid": closure_schema.get("valid") is True,
        "closure_blocking_inputs": closure_blockers,
        "runtime_evidence_artifact_blockers": artifact_blockers,
        "runtime_window_lifecycle_classification": runtime_window_lifecycle.get("classification"),
        "counts_as_approved_runtime_evidence": False,
        "counts_as_runtime_evidence": False,
        "counts_as_sdk_evidence": False,
        "runtime_ready": False,
        "public_sdk_ready": False,
        "stable_sdk_ready": False,
        **sdk_p0_non_progress_flags(),
    }


def build_report(
    *,
    closure: dict[str, Any],
    closure_returncode: int,
    passive: dict[str, Any] | None,
    passive_returncode: int | None,
    monitor_context: dict[str, Any] | None,
    beta_notice_context: dict[str, Any] | None,
    copy_ready_context: dict[str, Any] | None,
    player_principal_evidence_split: dict[str, Any] | None = None,
    route_gate: dict[str, Any],
    route_gate_returncode: int,
    standing_debug_authority_recorded: bool = False,
    standing_debug_authority_reference: str = DEFAULT_STANDING_DEBUG_AUTHORITY_REFERENCE,
    standing_debug_authority_source: str = DEFAULT_STANDING_DEBUG_AUTHORITY_SOURCE,
) -> dict[str, Any]:
    closure_schema = closure_schema_state(closure)
    passive_state = passive_activity(passive)
    monitor_state = monitor_context or empty_monitor_context()
    beta_notice_state = beta_notice_context or confirmed_beta_notice_context(None)
    copy_ready_state = copy_ready_context or copy_ready_log_context(None)
    split_context = player_principal_evidence_split_context(
        player_principal_evidence_split,
        closure,
    )
    player_availability = runtime_player_availability_context(passive_state, monitor_state)
    actions = next_actions(closure, passive_state, closure_schema, copy_ready_state)
    status = overall_status(closure, passive_state, closure_schema, copy_ready_state)
    closure_blockers = closure_blocking_inputs(closure)
    exact_triplet = closure_exact_triplet_state(closure)
    artifact_blockers = runtime_evidence_artifact_blockers(closure, exact_triplet)
    runtime_window_lifecycle = runtime_window_lifecycle_state(copy_ready_state, exact_triplet)
    triplet_route = exact_triplet_bundle_route(
        closure=closure,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        runtime_window_lifecycle=runtime_window_lifecycle,
    )
    expired_window_non_evidence = (
        runtime_window_lifecycle.get("close_or_classify_as_non_evidence") is True
    )
    active_window_waiting = (
        runtime_window_lifecycle.get("active_waiting_not_closure_ready") is True
    )
    closure_checker_ready = closure_ready_for_status_checker(
        closure,
        closure_schema,
        copy_ready_state,
    )
    operator_summary = operator_action_summary(
        closure,
        passive_state,
        route_gate,
        monitor_state,
        beta_notice_state,
        copy_ready_state,
        status=status,
        closure_schema=closure_schema,
        standing_debug_authority_recorded=standing_debug_authority_recorded,
        standing_debug_authority_reference=standing_debug_authority_reference,
        standing_debug_authority_source=standing_debug_authority_source,
    )
    current_live_blockers = current_live_diagnostic_blockers_context()
    operator_summary["blocking_inputs"]["current_live_diagnostic_blockers"] = (
        current_live_blockers
    )
    operator_summary["operator_context_inputs"]["current_live_diagnostic_blockers"] = (
        current_live_blockers
    )
    acceptance_boundary = runtime_evidence_acceptance_boundary(
        closure=closure,
        closure_schema=closure_schema,
        passive_state=passive_state,
        monitor_state=monitor_state,
        beta_notice_state=beta_notice_state,
        copy_ready_state=copy_ready_state,
        split_context=split_context,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        route_gate=route_gate,
        current_live_blockers=current_live_blockers,
        closure_checker_ready=closure_checker_ready,
    )
    operator_summary["blocking_inputs"]["runtime_evidence_acceptance_boundary"] = (
        acceptance_boundary
    )
    operator_summary["operator_context_inputs"]["runtime_evidence_acceptance_boundary"] = (
        acceptance_boundary
    )
    operator_summary["blocking_inputs"]["exact_triplet_bundle_route"] = triplet_route
    operator_summary["operator_context_inputs"]["exact_triplet_bundle_route"] = triplet_route
    machine_actions = status_machine_next_actions(
        closure,
        actions,
        closure_schema,
        copy_ready_state,
        split_context,
    )
    first_machine_action = first_machine_next_action_summary(machine_actions)
    strict_selector = strict_triplet_selector_result(
        closure,
        copy_ready_state,
        machine_actions,
    )
    fast_path = runtime_evidence_fast_path_summary(
        closure=closure,
        closure_schema=closure_schema,
        status=status,
        exact_triplet=exact_triplet,
        artifact_blockers=artifact_blockers,
        runtime_window_lifecycle=runtime_window_lifecycle,
        machine_actions=machine_actions,
        first_machine_action=first_machine_action,
        closure_checker_ready=closure_checker_ready,
    )
    fast_path["exact_triplet_bundle_route"] = triplet_route
    acceptance_state = runtime_evidence_acceptance_state(
        closure_schema=closure_schema,
        closure_checker_ready=closure_checker_ready,
        runtime_window_lifecycle=runtime_window_lifecycle,
        closure_blockers=closure_blockers,
        artifact_blockers=artifact_blockers,
    )
    fast_path["runtime_evidence_acceptance_state"] = acceptance_state
    source_ready_conflicts_with_blockers = (
        closure_schema.get("valid") is True
        and closure.get("ready") is True
        and closure_checker_ready is False
    )
    report = {
        "schema": SCHEMA,
        "status": status,
        "ready": False,
        **FALSE_FLAGS,
        "closure_consistency": {
            "schema_valid": closure_schema.get("valid") is True,
            "source_ready": closure.get("ready") is True,
            "ready_for_checker": closure_checker_ready,
            "source_ready_conflicts_with_blockers": source_ready_conflicts_with_blockers,
            "blocking_inputs": closure_blockers,
            "runtime_evidence_artifact_blockers": artifact_blockers,
            "first_missing_artifact": artifact_blockers["first_missing_artifact"],
            "first_missing_artifact_blocker_reason": artifact_blockers["first_blocker_reason"],
            "exact_copied_lifecycle_event_triplet": exact_triplet,
            "exact_triplet_bundle_route": triplet_route,
            "strict_triplet_selector": strict_selector,
            "passive_monitor_context_counts_as_evidence": False,
            "confirmed_beta_notice_counts_as_evidence": False,
            "copy_ready_or_copied_log_counts_as_evidence": False,
            "stale_missing_role_material_counts_as_evidence": False,
            "runtime_window_lifecycle": runtime_window_lifecycle,
            "expired_runtime_window_non_evidence": expired_window_non_evidence,
            "active_runtime_window_waiting_for_exact_triplet": active_window_waiting,
            "copy_bundle_commands_suppressed_until_exact_triplet": (
                runtime_window_lifecycle.get("copy_bundle_commands_suppressed_until_exact_triplet")
                is True
            ),
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "counts_as_runtime_evidence": False,
            "counts_as_sdk_evidence": False,
        },
        "closure": {
            "returncode": closure_returncode,
            "schema": closure.get("schema"),
            "schema_valid": closure_schema.get("valid") is True,
            "schema_blocker": closure_schema.get("blocker"),
            "status": closure.get("status"),
            "closure_case": closure.get("closure_case"),
            "source_report_claims": {
                "ready": closure.get("ready") is True,
                "approved_runtime_evidence": closure.get("approved_runtime_evidence") is True,
                "counts_as_approved_runtime_evidence": (
                    closure.get("counts_as_approved_runtime_evidence") is True
                ),
            },
            "source_claims_ignored_for_status": (
                source_ready_conflicts_with_blockers
                or (closure_schema.get("valid") is not True and closure.get("ready") is True)
                or closure.get("approved_runtime_evidence") is True
                or closure.get("counts_as_approved_runtime_evidence") is True
            ),
            "source_ready_conflicts_with_blockers": source_ready_conflicts_with_blockers,
            "ready": False,
            "ready_for_checker": closure_checker_ready,
            "approved_runtime_evidence": False,
            "counts_as_approved_runtime_evidence": False,
            "invalid_sidecars": closure.get("invalid_sidecars", []),
            "sidecar_validation_blockers": closure.get("sidecar_validation_blockers", []),
            "evidence_source_blockers": closure.get("evidence_source_blockers", []),
            "input_blockers": closure.get("input_blockers", []),
            "missing_required_artifacts": closure.get("missing_required_artifacts", []),
            "missing_siblings": closure.get("missing_siblings", []),
            "runtime_evidence_artifact_blockers": artifact_blockers,
            "missing_artifact_reasons": artifact_blockers["missing_artifact_reasons"],
            "missing_lifecycle_event_roles": closure.get("missing_lifecycle_event_roles", []),
            "exact_copied_lifecycle_event_triplet": exact_triplet,
            "exact_triplet_bundle_route": triplet_route,
            "missing_copied_lifecycle_event_triplet": exact_triplet.get(
                "missing_copied_lifecycle_event_triplet", []
            ),
            "missing_copied_lifecycle_event_triplet_labels": exact_triplet.get(
                "missing_copied_lifecycle_event_triplet_labels", []
            ),
            "artifact_hash_path_bindings": closure.get("artifact_hash_path_bindings")
            if isinstance(closure.get("artifact_hash_path_bindings"), dict)
            else {},
            "copied_log_hash_path_binding": closure.get("copied_log_hash_path_binding")
            if isinstance(closure.get("copied_log_hash_path_binding"), dict)
            else {},
            "required_sidecar_hash_path_bindings": closure.get(
                "required_sidecar_hash_path_bindings", []
            )
            if isinstance(closure.get("required_sidecar_hash_path_bindings"), list)
            else [],
            "artifact_hash_path_bindings_count_as_approved_runtime_evidence": False,
            "exact_missing_operations": closure.get("exact_missing_operations", []),
            "machine_next_actions_schema": closure.get("machine_next_actions_schema"),
            "machine_next_actions": machine_actions if closure_schema.get("valid") is True else [],
        },
        "passive": passive_state,
        "post_reboot_passive_monitor": monitor_state,
        "runtime_player_availability": player_availability,
        "player_presence_context": player_availability,
        "current_live_diagnostic_blockers": current_live_blockers,
        "runtime_evidence_acceptance_boundary": acceptance_boundary,
        "runtime_evidence_acceptance_state": acceptance_state,
        "runtime_evidence_fast_path": fast_path,
        "exact_triplet_bundle_route": triplet_route,
        "confirmed_beta_notice": beta_notice_state,
        "copy_ready_log": copy_ready_state,
        "player_principal_evidence_split": split_context,
        "player_principal_evidence_split_present": split_context.get("present") is True,
        "player_principal_evidence_split_next_actions": split_context.get("next_actions", []),
        "player_principal_evidence_split_counts_as_approved_runtime_evidence": False,
        "strict_triplet_selector": strict_selector,
        "source_log_not_ready": copy_ready_state.get("source_log_not_ready", {}),
        "active_observer_only_no_role_window": copy_ready_observer_only_no_role(copy_ready_state),
        "runtime_window_lifecycle": runtime_window_lifecycle,
        "runtime_evidence_artifact_blockers": artifact_blockers,
        "first_missing_runtime_evidence_artifact": artifact_blockers["first_missing_artifact"],
        "first_missing_runtime_evidence_artifact_blocker_reason": artifact_blockers[
            "first_blocker_reason"
        ],
        "expired_runtime_window_non_evidence": expired_window_non_evidence,
        "active_runtime_window_waiting_for_exact_triplet": active_window_waiting,
        "copy_bundle_commands_suppressed_until_exact_triplet": (
            runtime_window_lifecycle.get("copy_bundle_commands_suppressed_until_exact_triplet")
            is True
        ),
        "copy_bundle_commands_allowed_before_exact_triplet": (
            runtime_window_lifecycle.get("copy_bundle_commands_allowed") is True
        ),
        "operator_action_summary": operator_summary,
        "route_gate": route_gate_state(route_gate, route_gate_returncode),
        "passive_returncode": passive_returncode,
        "next_actions": actions,
        "machine_next_actions_schema": MACHINE_NEXT_ACTIONS_SCHEMA,
        "machine_next_actions": machine_actions,
        "machine_next_action_ids": [action["action_id"] for action in machine_actions],
        "first_machine_next_action": first_machine_action,
        "exact_next_command": first_machine_action,
        "non_claims": [
            "runtime evidence status report only",
            "does not read or write live ARK server state by itself",
            "does not create sidecars, copy logs, build approved bundles, send Discord, or operate servers",
            "recorded standing debug authority may allow exact scoped operator actions but is not evidence",
            "passive monitor and closure summaries remain non-evidence until approved bundle checkers accept a copied sibling set",
            "post-reboot passive monitor logs and confirmed beta notice reports are operator context only",
            "ready-log copy helper reports are operator context only and do not approve copied logs",
            "player_presence_context and diagnostic-only HandleNewPlayer/K2_PostLogin target lines are context only unless the exact copied observer triplet is accepted",
            "current live diagnostic blocker context is redacted operator context only: TheIsland active-player observer-only/no accepted lifecycle events and Ragnarok diagnostic FName drift do not count as evidence",
            CHECKJOININPROGRESS_1_0_ROUTE_WORDING,
            "allowed cluster target data is diagnostic non-evidence unless an accepted copied sibling bundle exists",
            "does not promote player identity, public SDK readiness, runtime readiness, stable SDK, Plugin Hub, publication, or v1 completion",
        ],
    }
    return report


def reject_server_root_output(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    try:
        resolved.relative_to(Path("/servidor/ark").resolve())
    except ValueError:
        return resolved
    raise SystemExit("--json-output must not write under /servidor/ark")


def main() -> int:
    args = parse_args()
    closure, closure_returncode = load_or_run_closure(args)
    passive, passive_returncode = load_or_run_passive_summary(args)
    monitor_context = monitor_operator_context(monitor_context_path(args))
    beta_notice_context = confirmed_beta_notice_context(args.confirmed_beta_notice_json)
    copy_ready_context = copy_ready_log_context(args.copy_ready_json)
    player_principal_evidence_split = (
        load_json(args.player_principal_evidence_split_json)
        if args.player_principal_evidence_split_json
        else None
    )
    route_gate, route_gate_returncode = load_or_run_route_gate(args)
    report = build_report(
        closure=closure,
        closure_returncode=closure_returncode,
        passive=passive,
        passive_returncode=passive_returncode,
        monitor_context=monitor_context,
        beta_notice_context=beta_notice_context,
        copy_ready_context=copy_ready_context,
        player_principal_evidence_split=player_principal_evidence_split,
        route_gate=route_gate,
        route_gate_returncode=route_gate_returncode,
        standing_debug_authority_recorded=args.recorded_standing_debug_authority,
        standing_debug_authority_reference=args.standing_debug_authority_reference,
        standing_debug_authority_source=args.standing_debug_authority_source,
    )
    if args.json_output:
        output = reject_server_root_output(args.json_output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
