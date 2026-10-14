#!/usr/bin/env python3
"""Run the route gate with transient bound player-identity planning inputs."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import bind_player_identity_planning_sources as binder
import build_redacted_ufunction_signatures
import check_command_permission_route_gate as route_gate
from protected_paths import reject_protected_input_path, reject_protected_output_path, reject_symlink_component


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
REPORT_SCHEMA = "obelisk.command-permission-route-gate-bound-identity-sources-check.v1"
ROUTE_GATE_SCHEMA = "obelisk.command-permission-route-gate-check.v1"
APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
)
APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
APPROVED_RUNTIME_EVIDENCE_FALSE_KEYS = (
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "promotion_ready",
    "public_or_runtime_accounting_allowed",
    "public_header_allowed",
    "public_sdk_ready",
    "public_api_ready",
    "public_abi_ready",
    "public_readiness",
    "runtime_ready",
    "runtime_readiness",
    "lookup_ready",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "v1_completion_ready",
    "v1_completion_evidence",
)
APPROVED_RUNTIME_EVIDENCE_REQUIRED_FALSE_KEYS = (
    "promotion_ready",
    "public_header_allowed",
    "public_sdk_ready",
    "runtime_ready",
    "v1_completion_ready",
)
APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS = tuple(
    key
    for key in APPROVED_RUNTIME_EVIDENCE_FALSE_KEYS
    if key not in APPROVED_RUNTIME_EVIDENCE_REQUIRED_FALSE_KEYS
)
APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS = (
    "public_capability_bits_now",
    "public_callback_abi_now",
)
APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS = (
    "claim_progress",
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "progress",
    "progress_contribution",
    "progress_percent",
    "progress_ratio",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_progress_percent",
    "sdk_progress_ratio",
    "sdk_p0_progress",
)
APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES = [
    "observer_enable",
    "session_start_anchor",
    "session_start_rejected_anchor",
    "session_end_anchor",
]
APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES = [
    "malformed_or_unsupported_evidence",
    "stale_after_logout",
]
ROUTE_GATE_REQUIRED_FALSE_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "public_abi_ready",
    "runtime_ready",
    "public_header_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)
ROUTE_GATE_OPTIONAL_FALSE_KEYS = (
    "v1_completion_ready",
)
QUARANTINED_DOWNSTREAM_ROUTE_GATE_BLOCKERS = frozenset(
    (
        "player_identity_public_contract_gap: checker exited 1",
        "player_identity_public_contract_gap: child blockers not empty",
        "player_identity_public_contract_gap: invalid route prerequisite",
        "command_chat_response_public_readiness: checker exited 1",
        "command_chat_response_public_readiness: child blockers not empty",
        "command_chat_response_public_readiness: planning_only must stay true",
        "command_chat_response_public_readiness: accepted_for_planning must stay true",
        "command_chat_response_public_readiness: invalid route prerequisite",
        "command_principal_authz_response_bridge: checker exited 1",
        "command_principal_authz_response_bridge: child blockers not empty",
        "command_principal_authz_response_bridge: planning_only must stay true",
        "command_principal_authz_response_bridge: accepted_for_planning must stay true",
        "command_principal_authz_response_bridge: invalid route prerequisite",
        "commands_replies_public_readiness: checker exited 1",
        "commands_replies_public_readiness: child blockers not empty",
        "commands_replies_public_readiness: planning_only must stay true",
        "commands_replies_public_readiness: accepted_for_planning must stay true",
        "commands_replies_public_readiness: invalid route prerequisite",
    )
)
BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_ROUTE_CHECK_CLAIMS = frozenset(
    (
        "blocker_details[0].claims[0].value",
        "blocker_details[1].value",
        "identity_public_contract_gate_missing",
        "identity_public_contract_gate_missing.next_auditable_blocker.next_required_artifact.p0_dependency_chain",
        "identity_public_contract_gate_missing.post_runtime_contract_gap_diagnostic.approved_runtime_bundle_consumed",
        "identity_public_contract_gate_missing.post_runtime_contract_gap_diagnostic.next_required_artifact.p0_dependency_chain",
        "next_offline_actions[0].next_required_artifact.p0_dependency_chain",
        "post_approved_runtime_evidence_route_check",
        "post_approved_runtime_evidence_gate.next_required_artifact.p0_dependency_chain",
        "post_approved_runtime_evidence_route_check.runtime_evidence_accepted",
        "post_runtime_contract_gap_diagnostic.approved_runtime_bundle_consumed",
        "post_runtime_contract_gap_diagnostic.next_required_artifact.p0_dependency_chain",
        "post_runtime_public_identity_gap_summary",
        "post_runtime_public_identity_gap_summary.approved_runtime_bundle_consumed",
        "public_abi_promotion_preflight.principal_invalidation_policy.ready",
        "runtime_evidence_contract_review_currentness.runtime_evidence_accepted",
    )
)
BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_SOURCE_CHECKER_CLAIMS = frozenset(
    (
        "first_evidence_boundary.post_runtime_fast_path_inputs.approved_runtime_evidence_ready",
    )
)
BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_CHILD_CHECK_CLAIMS = frozenset(
    route_gate.POST_RUNTIME_IDENTITY_CONTRACT_CHILD_LOCK_CLAIMS
)
BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_PUBLIC_CONTRACT_GAP_PREFIX = (
    "player_identity_public_contract_gap: unexpected public/runtime claim: "
)
BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_PUBLIC_CONTRACT_GAP_CLAIM_PATH_RE = re.compile(
    r"checks\[\d+\]\.public_or_runtime_claims:(?P<claim>.+)\Z"
)
NON_CLAIMS = [
    "transient bound route gate check only",
    "no runtime or server operation was performed",
    "no ARK process was started, stopped, restarted, attached, or observed",
    "no public player identity is promoted",
    "no permissions/admin, command response, or commands/replies surface is promoted",
    "no public SDK, public ABI, release, or v1 completion readiness is claimed",
]
BOUND_IDENTITY_ROUTE_FALSE_ONLY_KEYS = {
    "beta_notice",
    "beta_notice_accepted",
    "beta_notice_ready",
    "beta_notice_sent",
    "beta_notice_unlocked",
    "broadcast_ready",
    "broadcast_status",
    "command_response_ready",
    "command_response_path_ready",
    "command_response_unlocked",
    "command_planning_ready",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "complete",
    "complete_sdk_claim_progress",
    "complete_sdk_progress",
    "accepted_runtime_evidence_only_ready",
    "accepted_runtime_evidence_ready",
    "accepted_runtime_evidence_sufficient",
    "accepted_runtime_evidence_sufficient_for_promotion",
    "authz_bridge_ready",
    "authz_ready",
    "authz_response_ready",
    "authorization_ready",
    "counts_as_public_sdk",
    "counts_as_runtime",
    "counts_as_v1_completion",
    "counts_toward_complete_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "diagnostic_candidate",
    "diagnostic_candidate_accepted",
    "diagnostic_candidate_ready",
    "diagnostic_candidates",
    "diagnostic_candidates_accepted",
    "diagnostic_candidates_ready",
    "diagnostic_only_non_evidence",
    "final_artifact_accepted",
    "final_artifact_ready",
    "final_certificate_accepted",
    "final_certificate_metadata_ready",
    "final_certificate_ready",
    "final_certificate_status_ready",
    "final_gate_accepted",
    "final_gate_ready",
    "final_gate_unlocked",
    "hash_current_identity_contract_decision_record",
    "hash_current_identity_public_contract_decision_record",
    "identity_contract_decision_record_contract_review_only",
    "identity_contract_decision_record_hash_current",
    "identity_contract_decision_record_reviewed",
    "identity_public_contract_decision_record_contract_review_only",
    "identity_public_contract_decision_record_hash_current",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_gate_accepted",
    "identity_public_contract_gate_missing",
    "identity_public_contract_gate_missing_accepted",
    "identity_public_contract_gate_missing_passed",
    "identity_public_contract_gate_missing_ready",
    "identity_public_contract_gate_missing_resolved",
    "identity_public_contract_gate_missing_satisfied",
    "identity_public_contract_gate_missing_supported",
    "identity_public_contract_gate_missing_unlocked",
    "identity_public_contract_gate_missing_unlock_allowed",
    "identity_public_contract_gate_passed",
    "identity_public_contract_gate_resolved",
    "identity_public_contract_record_contract_review_only",
    "identity_public_contract_record_hash_current",
    "identity_public_contract_record_reviewed",
    "public_or_runtime_accounting_allowed",
    "public_reachability",
    "public_readiness_artifact_ready",
    "public_readiness_ready",
    "public_readiness_status",
    "public_reachability_ready",
    "public_reachability_status",
    "public_sdk_progress",
    "public_runtime_readiness_accepted",
    "public_runtime_readiness_ready",
    "public_runtime_ready",
    "partial_contract",
    "partial_contract_review",
    "partial_identity_contract",
    "partial_identity_contract_review",
    "partial_identity_public_contract",
    "partial_public_identity_contract",
    "permissions_admin_ready",
    "permissions_admin_unlocked",
    "player_identity_promotion_certificate_ready",
    "request_check_ready",
    "request_pack_ready",
    "reviewed_hash_current_contract_review_only",
    "reviewed_identity_contract_decision_record",
    "reviewed_identity_public_contract",
    "reviewed_identity_public_contract_decision_record",
    "reply_ready",
    "reply_unlocked",
    "command_chat_response_path_complete",
    "command_chat_response_path_completed",
    "command_chat_response_path_ready",
    "command_response_path_complete",
    "command_response_path_completed",
    "commands_replies_final_gate_ready",
    "commands_replies_final_ready",
    "response_complete",
    "response_completed",
    "response_path_complete",
    "response_path_completed",
    "response_path_ready",
    "response_ready",
    "rcon_command_ready",
    "rcon_command_status",
    "rcon_ready",
    "rcon_route_ready",
    "rcon_route_status",
    "rcon_status",
    "route_accepted",
    "route_accepted_as_command_response",
    "route_accepted_as_commands_replies",
    "route_accepted_as_permissions_admin",
    "route_accepted_as_public_abi",
    "route_accepted_as_public_header",
    "route_accepted_as_public_sdk",
    "route_accepted_as_runtime",
    "route_accepted_as_stable_claim",
    "route_accepted_as_v1_completion",
    "route_snapshot_accepted",
    "route_snapshot_ready",
    *route_gate.MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES,
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_progress_percent",
    "sdk_progress_ratio",
    "scoped_release_statement_counts_toward_complete_sdk_claim",
    "scoped_release_statement_counts_toward_completion",
    "scoped_release_statement_outcomes_satisfy_completion",
    "scoped_release_statement_ready",
    "sdk_ready",
    "sidecar_automation",
    "sidecar_automation_accepted",
    "sidecar_automation_ready",
    "sidecar_automation_unlocked",
    "stable_claim_allowed",
    "stable_release_contract_claim_allowed",
    "start_end_evidence_ready",
    "start_end_only_evidence_ready",
    "start_end_only_ready",
    "runtime_principal_lifecycle_start_end_evidence_ready",
    "runtime_principal_start_end_evidence_ready",
    "runtime_readiness_accepted",
    "runtime_readiness_ready",
    "runtime_ready",
    "passive_window",
    "passive_window_accepted",
    "passive_window_ready",
    "passive_window_unlocked",
    "plugin_hub_package_shape_ready",
    "plugin_hub_support_ready",
}
BOUND_IDENTITY_ROUTE_SPLIT_CLAIM_NAME_KEYS = {
    "alias",
    "claim",
    "field",
    "flag",
    "key",
    "name",
    "property",
}
BOUND_IDENTITY_ROUTE_SPLIT_CLAIM_VALUE_KEYS = {
    "allowed",
    "enabled",
    "ready",
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
    "state",
    "status",
    "value",
}
BOUND_IDENTITY_ROUTE_SOURCE_MARKER_KEYS = {"source_marker", "source_markers"}
BOUND_IDENTITY_ROUTE_SOURCE_PROVENANCE_CONTEXT_KEYS = {
    "artifact_provenance",
    "evidence_provenance",
    "metadata_provenance",
    "provenance",
    "provenance_marker",
    "provenance_markers",
    "review_provenance",
    "route_provenance",
    "snapshot_provenance",
    "source_provenance",
    "source_provenances",
}
BOUND_IDENTITY_ROUTE_SOURCE_CONTEXT_KEYS = (
    BOUND_IDENTITY_ROUTE_SOURCE_MARKER_KEYS
    | BOUND_IDENTITY_ROUTE_SOURCE_PROVENANCE_CONTEXT_KEYS
)
BOUND_IDENTITY_ROUTE_SOURCE_STATUS_KEYS = {
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
    "state",
    "status",
}
BOUND_IDENTITY_ROUTE_NESTED_STATUS_KEYS = BOUND_IDENTITY_ROUTE_SOURCE_STATUS_KEYS | {
    "acceptance",
    "accepted",
    "allowed",
    "approved",
    "authorized",
    "available",
    "capture_ready",
    "clears_approved_runtime_evidence_missing",
    "current_blocker_cleared",
    "current_route_blocker_cleared",
    "debug_capture_ready",
    "enabled",
    "mutation_authority_ready",
    "queue_status",
    "ready",
    "result",
    "state",
    "status",
    "supported",
    "unlocked",
    "value",
    "verdict",
}
BOUND_IDENTITY_ROUTE_POSITIVE_TEXT_RE = re.compile(
    r"\b(?:"
    r"activation[-_ ]+preconditions?(?:[-_ ]+(?:artifacts?|reports?))?|"
    r"(?:agent[-_ ]+)?handoff[-_ ]+(?:notes?|reports?|summar(?:y|ies))|"
    r"(?:beta[-_ ]+)?notice[-_ ]+actions?(?:[-_ ]+reports?)?|"
    r"compact[-_ ]+contexts?|compact[-_ ]+summar(?:y|ies)|"
    r"(?:command[-_ ]+principal[-_ ]+authz[-_ ]+response[-_ ]+|authz[-_ ]+response[-_ ]+|response[-_ ]+)?bridge[-_ ]+reports?|"
    r"authz(?:[-_ ]+(?:ready|bridge|response))?|authorization|"
    r"final[-_ ]+(?:gate|certificate|artifact)(?:[-_ ]+(?:metadata|status|reports?))?|"
    r"copied[-_ ]+log[-_ ]+only(?:[-_ ]+(?:artifacts?|reports?|copies|metadata))?|"
    r"(?:copied?|copy)[-_ ]+(?:artifacts?|reports?|status|metadata)|"
    r"status[-_ ]+(?:artifacts?|json|reports?|snapshots?|updates?)|"
    r"(?:candidate[-_ ]+|future[-_ ]+)?multi[-_ ]+surface(?:[-_ ]+beta[-_ ]+capture)?"
    r"(?:[-_ ]+(?:candidate[-_ ]+queue|checker[-_ ]+matrix|capture[-_ ]+pack|capture[-_ ]+plan|"
    r"non[-_ ]+claim[-_ ]+manifest|pack|plan|plan[-_ ]+queue|queue|runbook|artifacts?|manifest))?|"
    r"beta[-_ ]+capture(?:[-_ ]+(?:candidate[-_ ]+pack|candidate[-_ ]+queue|pack|plan|plan[-_ ]+queue|queue))?|"
    r"copied[-_ ]+admin[-_ ]+targets?|"
    r"ServerListPlayers|ServerKickPlayer|"
    r"sidecar[-_ ]+automation|"
    r"diagnostic[-_ ]+candidates?|"
    r"passive[-_ ]+windows?|"
    r"beta[-_ ]+notices?|"
    r"partial[-_ ]+identity[-_ ]+(?:public[-_ ]+)?contracts?|"
    r"passive[-_ ]+(?:evidence|snapshots?)|"
    r"passive[-_ ]+(?:monitors?|reports?|status|summar(?:y|ies))|"
    r"public[-_ ]+reachability(?:[-_ ]+(?:checks?|reports?|status))?|"
    r"public[-_ ]+readiness(?:[-_ ]+(?:artifacts?|checks?|reports?|status))?|"
    r"public[-_ ]+header(?:[-_ ]+(?:artifacts?|gate|preflight|readiness|reports?|review|scan|status))?|"
    r"rcon(?:[-_ ]+(?:command[-_ ]+)?(?:routes?|status|reports?|candidates?))?|"
    r"broadcast(?:[-_ ]+(?:notices?|status|reports?))?|"
    r"Plugin[-_ ]+Hub(?:[-_ ]+(?:planning|readiness|reports?|support|package|package[-_ ]+shape))?|"
    r"scoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?(?:v1[-_ ]+)?release[-_ ]+statements?|"
    r"(?:reviewed[-_ ]+)?identity[-_ ]+(?:public[-_ ]+)?contract[-_ ]+decision[-_ ]+record[-_ ]+templates?|"
    r"identity[-_ ]+public[-_ ]+contracts?|"
    r"stable[-_ ]+claim|"
    r"permissions?[/ _-]?admin|permissions?[_ -]?quer(?:y|ies)|"
    r"command[-_ ]+planning|"
    r"package[-_ ]+shapes?|"
    r"(?:runtime[-_ ]+principal[-_ ]+lifecycle[-_ ]+)?start[-_ ]+end(?:[-_ ]+only)?(?:[-_ ]+evidence)?|"
    r"side[-_ ]+lane(?:[-_ ]+(?:artifacts?|reports?|candidate|candidates))?|"
    r"precondition[-_ ]+(?:artifacts?|reports?)|"
    r"identity[-_ ]+public[-_ ]+contract[-_ ]+gate[-_ ]+missing|identity_public_contract_gate_missing|"
    r"response[-_ ]+path|"
    r"command[/ _-]?chat[-_ ]+response|command[-_ ]+response|"
    r"commands?[/ _-]?replies|replies[_ -]?(?:api|abi|endpoint)|"
    r"command[-_ ]+router|route[-_ ]+snapshots?|send[-_ ]+chat|"
    r"support[-_ ]+tiers?(?:[-_ ]+(?:readiness|reports?))?|support[-_ ]+tier[-_ ]+(?:packages?|package[-_ ]+shapes?)"
    r")\b[^.;:\n\r]{0,80}\b"
    r"(?:allowed|available|clear(?:ed|s)?|count(?:ed|s|ing)?|enabled|granted|promoted|public|ready|"
    r"resolv(?:ed|es)?|satisf(?:ied|ies|y)?|supported|unlock(?:s|ed)?)\b",
    re.IGNORECASE,
)
BOUND_IDENTITY_ROUTE_NEGATED_TEXT_RE = re.compile(
    r"\b(?:blocked|cannot|can't|does\s+not|do\s+not|false|must\s+not|never|no|not|"
    r"candidate[-_ ]?only|non[-_ ]?claim|non[-_ ]?count(?:ing)?|planning[-_ ]?only|"
    r"unavailable|without)\b",
    re.IGNORECASE,
)
BOUND_IDENTITY_ROUTE_TEXT_EXEMPT_PATH_PARTS = {
    "argv",
    "blocker",
    "blockers",
    "blocked_until",
    "cannot_unlock_without",
    "non_claim",
    "non_claims",
    "expected_schema",
    "input_schema",
    "path",
    "report_schema",
    "remaining_route_blockers",
    "required",
    "required_checks",
    "schema",
    "schema_id",
    "schema_ids",
    "schemas",
    "source_schema",
    "why_blocked",
}
BOUND_IDENTITY_PUBLIC_ABI_CONTEXT_TERMS = (
    "public_abi",
    "public_api",
    "public_callback_abi",
    "public_header",
    "plugin_abi",
    "sdk_abi",
)
BOUND_IDENTITY_LOOKUP_HANDLE_TERMS = (
    "identity_handle",
    "identity_handles",
    "identity_lookup",
    "identity_resolver",
    "lookup_handle",
    "lookup_handles",
    "persistent_handle",
    "player_handle",
    "player_handles",
    "player_lookup",
    "player_resolver",
    "principal_lookup",
    "public_handle",
    "public_handles",
    "resolve_identity",
    "resolve_player",
    "resolve_principal",
    "resource_handle",
    "resourcehandle",
)
BOUND_IDENTITY_CONTRACT_RECORD_CONTEXT_KEYS = frozenset(
    {
        "hash_current_identity_contract_decision_record",
        "hash_current_identity_public_contract_decision_record",
        "identity_contract_decision_record",
        "identity_contract_decision_record_template",
        "identity_public_contract_decision_record",
        "identity_public_contract_decision_record_template",
        "identity_public_contract_record",
        "identity_public_contract_record_template",
        "reviewed_identity_contract_decision_record",
        "reviewed_identity_contract_decision_record_template",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_decision_record",
        "reviewed_identity_public_contract_decision_record_template",
    }
)
BOUND_IDENTITY_CONTRACT_RECORD_REQUIREMENT_CONTEXT_KEYS = frozenset(
    {
        "identity_public_contract_decision_record_required",
        "required_identity_public_contract_decision_record",
    }
)
BOUND_IDENTITY_CONTRACT_RECORD_STATUS_KEYS = frozenset(
    {
        "accepted_for_contract_review",
        "contract_review_only",
        "decision_scope",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "hash_current_source_artifacts",
        "record_valid",
        "record_valid_scope",
        "review_status",
        "reviewed",
        "scope",
        "state",
        "status",
    }
)
BOUND_IDENTITY_CONTRACT_RECORD_DOWNSTREAM_CONTEXT_KEYS = frozenset(
    {
        "command_chat_response",
        "command_response",
        "commands",
        "commands_replies",
        "complete_sdk",
        "permissions",
        "permissions_admin",
        "public_abi",
        "public_api",
        "public_callback_abi",
        "public_header",
        "public_sdk",
        "runtime",
        "sdk",
        "sdk_completion",
        "send_chat",
        "stable_claim",
        "v1_completion",
    }
)
BOUND_IDENTITY_CONTRACT_RECORD_DOWNSTREAM_STATUS_KEYS = frozenset(
    {
        "allowed",
        "available",
        "enabled",
        "readiness",
        "ready",
        "result",
        "state",
        "status",
        "supported",
        "unlocked",
        "value",
    }
)
BOUND_IDENTITY_CONTRACT_RECORD_POSITIVE_STATUS_VALUES = frozenset(
    {
        "accepted",
        "allowed",
        "available",
        "complete",
        "contract_review_only",
        "current",
        "enabled",
        "hash_bound",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "passed",
        "passing",
        "ready",
        "reviewed",
        "satisfied",
        "supported",
        "true",
        "unlocked",
        "valid",
        "yes",
    }
)
POST_EVIDENCE_RUNTIME_ACCEPTANCE_SIMULATION_FLAG = (
    "post_evidence_p0_lock_simulation.approved_runtime_evidence_accepted"
)
POST_EVIDENCE_RUNTIME_ACCEPTANCE_SIMULATION_ALLOWED_TRUE_FLAGS = frozenset(
    (
        POST_EVIDENCE_RUNTIME_ACCEPTANCE_SIMULATION_FLAG,
        "post_evidence_p0_lock_simulation.identity_public_contract_required",
        "post_evidence_p0_lock_simulation.reviewed_identity_public_contract_required",
        "post_evidence_p0_lock_simulation.hash_current_identity_public_contract_decision_record_required",
        (
            "post_evidence_p0_lock_simulation."
            "permissions_admin_unlock_requires_reviewed_hash_current_identity_contract"
        ),
    )
)
BOUND_IDENTITY_ADMIN_TARGETS_NOT_IDENTITY_SOURCES = frozenset(
    (
        "ShooterPlayerController.ServerListPlayers",
        "ShooterPlayerController.ServerKickPlayer",
    )
)
BOUND_IDENTITY_ADMIN_TARGET_SOURCE_CONTEXT_KEYS = frozenset(
    {
        "accepted_admin_targets",
        "accepted_end_targets",
        "accepted_identity_source_targets",
        "accepted_principal_source_targets",
        "accepted_start_targets",
        "admin_target",
        "admin_targets",
        "copied_admin_target",
        "copied_admin_targets",
        "identity_source",
        "identity_source_target",
        "identity_source_targets",
        "lifecycle_source",
        "permission_principal_source",
        "principal_source",
        "principal_source_target",
        "principal_source_targets",
        "public_identity_source",
        "source_checker_accepted_targets",
    }
)
BOUND_IDENTITY_ADMIN_TARGET_SAFE_CONTEXT_KEYS = frozenset(
    {
        "argv",
        "blocker",
        "blockers",
        "coverage",
        "covered_targets",
        "expected",
        "expected_targets",
        "first_evidence",
        "input_target_set",
        "non_claim",
        "non_claims",
        "required",
        "target_set_coverage",
    }
)
BOUND_IDENTITY_ROUTE_NON_AUTHORIZING_SOURCE_RE = re.compile(
    r"(?:^|_)(?:"
    + route_gate.MULTI_SURFACE_BETA_CAPTURE_CONTEXT_RE
    + r"|"
    r"(?:automation_)?sidecar(?:_automation)?|"
    r"sidecar_automation|"
    r"diagnostic_candidates?|"
    r"passive_windows?|"
    r"beta_notices?|"
    r"broadcast(?:_?(?:notices?|status|reports?))?|"
    r"(?:reviewed_?)?identity_?(?:public_?)?contract_?decision_?record_?templates?|"
    r"(?:copied?|copy)_?(?:artifacts?|reports?|status|metadata)|"
    r"(?:support_?)?package_?shapes?|"
    r"public_?reachability(?:_?(?:checks?|reports?|status))?|"
    r"public_?readiness(?:_?(?:artifacts?|checks?|reports?|status))?|"
    r"public_?header(?:_?(?:artifacts?|gate|preflight|readiness|reports?|review|scan|status))?|"
    r"rcon_?(?:command_?)?(?:routes?|status|reports?|candidates?)|"
    r"(?:runtime_?principal_?lifecycle_?)?start_?end(?:_?only)?(?:_?evidence)?|"
    r"status_?(?:artifacts?|reports?|snapshots?|updates?)|"
    r"identity_public_contract_gate_missing"
    r")(?:_|$)",
    re.IGNORECASE,
)
BOUND_IDENTITY_DOWNSTREAM_CHILD_CHECKS = frozenset(
    {
        "permissions_admin_public_readiness",
        "command_chat_response_public_readiness",
        "commands_replies_public_readiness",
    }
)
BOUND_IDENTITY_DOWNSTREAM_CHILD_FALSE_KEYS = (
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "public_or_runtime_accounting_allowed",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot-root",
        type=Path,
        default=build_redacted_ufunction_signatures.DEFAULT_SNAPSHOT_ROOT,
        help="Sanitized snapshot root used to build transient player-identity first evidence.",
    )
    parser.add_argument(
        "--lifecycle-anchor-candidates-manifest",
        "--lifecycle-anchor-candidates",
        dest="lifecycle_anchor_candidates",
        type=Path,
        required=True,
        help="Consume-only lifecycle-anchor candidates manifest to bind transiently.",
    )
    parser.add_argument(
        "--principal-invalidation-policy-manifest",
        "--principal-invalidation-policy",
        dest="principal_invalidation_policy",
        type=Path,
        required=True,
        help="Consume-only principal invalidation policy manifest to bind transiently.",
    )
    parser.add_argument(
        "--approved-runtime-principal-lifecycle-evidence-manifest",
        type=Path,
        help=(
            "Optional approved runtime-principal lifecycle evidence manifest forwarded "
            "to the route gate. It may clear only approved_runtime_evidence_missing and "
            "must leave the route locked at identity_public_contract_gate_missing."
        ),
    )
    parser.add_argument(
        "--candidate-root",
        type=Path,
        help="Optional distinct second-source candidate root forwarded to the route gate identity checker.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Optional artifact root forwarded to the route gate identity checker.",
    )
    parser.add_argument(
        "--query-failclosed-artifact",
        type=Path,
        default=route_gate.DEFAULT_QUERY_CONTRACT,
        help="Permissions/admin query fail-closed artifact forwarded to the route gate.",
    )
    parser.add_argument(
        "--player-identity-decisions",
        type=Path,
        default=route_gate.DEFAULT_PLAYER_IDENTITY_DECISIONS,
        help="Player identity decisions manifest forwarded to the route gate.",
    )
    parser.add_argument(
        "--public-sdk-surfaces",
        type=Path,
        default=route_gate.DEFAULT_PUBLIC_SDK_SURFACES,
        help="Public SDK surfaces manifest forwarded to the route gate.",
    )
    parser.add_argument(
        "--player-identity-private-candidate-contract",
        type=Path,
        default=route_gate.DEFAULT_PLAYER_IDENTITY_PRIVATE_CANDIDATE,
        help="Private candidate identity contract forwarded to the route gate.",
    )
    parser.add_argument(
        "--public-header",
        type=Path,
        default=route_gate.DEFAULT_PUBLIC_HEADER,
        help="Public C ABI header forwarded to the route gate.",
    )
    parser.add_argument(
        "--command-response-root",
        type=Path,
        help="Optional command/chat response second-source planning root forwarded to the route gate.",
    )
    parser.add_argument(
        "--command-response-readiness",
        type=Path,
        help="Optional command/chat response readiness JSON forwarded to the route gate.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON. The checker always emits JSON.")
    return parser.parse_args()


def resolve_manifest_pair(args: argparse.Namespace) -> tuple[Path, Path]:
    lifecycle = args.lifecycle_anchor_candidates
    principal = args.principal_invalidation_policy
    assert lifecycle is not None and principal is not None
    if not lifecycle.is_file():
        raise SystemExit(f"lifecycle-anchor candidates manifest is missing: {lifecycle}")
    if not principal.is_file():
        raise SystemExit(f"principal invalidation policy manifest is missing: {principal}")
    return lifecycle, principal


def safe_snapshot_root(path: Path) -> Path:
    reject_symlink_component(path, "snapshot-root")
    resolved = reject_protected_input_path(path, "snapshot-root")
    if not resolved.is_dir():
        raise SystemExit(f"snapshot-root is not a directory: {resolved}")
    return resolved


def safe_optional_input_path(path: Path | None, label: str) -> Path | None:
    if path is None:
        return None
    reject_symlink_component(path, label)
    resolved = reject_protected_input_path(path, label)
    return resolved


def approved_runtime_evidence_report_public_or_runtime_claims(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return []
    return route_gate.collect_public_or_runtime_claims(report, include_text_claims=True)


def approved_runtime_evidence_report_accepted(report: dict[str, Any] | None) -> bool:
    if not isinstance(report, dict):
        return False
    return (
        report.get("schema") == APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA
        and report.get("input_schema") == APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA
        and report.get("mode") == "consume"
        and report.get("ready_scope") == "runtime_evidence_only"
        and report.get("ready") is True
        and report.get("approved_runtime_evidence_present") is True
        and report.get("runtime_evidence_ready") is True
        and report.get("remaining_blockers") == []
        and report.get("blockers") == []
        and report.get("next_blocker") == "identity_public_contract_gate_missing"
        and all(report.get(key) is False for key in APPROVED_RUNTIME_EVIDENCE_REQUIRED_FALSE_KEYS)
        and all(
            key not in report or report.get(key) is False
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS
        )
        and all(report.get(key) == [] for key in APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS)
        and all(
            key not in report or not route_gate.progress_claim_value_is_nonzero(report.get(key))
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS
        )
        and report.get("observed_runtime_cases") == APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES
        and report.get("consumer_cases") == APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES
        and not approved_runtime_evidence_report_public_or_runtime_claims(report)
    )


def check_approved_runtime_evidence_manifest(
    path: Path,
    temp_root: Path,
) -> tuple[bool, dict[str, Any] | None, int, str, str | None]:
    argv = [
        sys.executable,
        str(SCRIPT_DIR / "check_player_identity_runtime_principal_lifecycle_approved_evidence.py"),
        str(path),
        "--json",
    ]
    env = os.environ.copy()
    env.update({"TMPDIR": str(temp_root), "TEMP": str(temp_root), "TMP": str(temp_root)})
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    parse_error = None
    report = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"
    accepted = result.returncode == 0 and parse_error is None and approved_runtime_evidence_report_accepted(report)
    return accepted, report, result.returncode, result.stderr.strip(), parse_error


def route_action_for_blocker(blocker: Any) -> str | None:
    if blocker == "approved_runtime_evidence_missing":
        return "produce_approved_runtime_principal_lifecycle_evidence"
    if blocker == "identity_public_contract_gate_missing":
        return "review_identity_public_contract"
    return None


def allowed_route_actions_for_blocker(blocker: Any) -> set[str]:
    actions = set()
    fallback = route_action_for_blocker(blocker)
    if fallback is not None:
        actions.add(fallback)
    if blocker == "identity_public_contract_gate_missing":
        actions.add("review_identity_public_contract_gate")
    return actions


def route_lock_aliases(route_report: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(route_report, dict):
        return {
            "route_blocked": False,
            "current_route_blocker": None,
            "remaining_route_blockers": [],
            "next_route_action": None,
        }
    critical_path_phase = (
        route_report.get("critical_path_phase")
        if isinstance(route_report.get("critical_path_phase"), dict)
        else {}
    )
    current_route_blocker = route_report.get("current_route_blocker")
    if current_route_blocker is None:
        current_route_blocker = critical_path_phase.get("current_blocker")
    remaining_route_blockers = route_report.get("remaining_route_blockers")
    if not isinstance(remaining_route_blockers, list):
        remaining_route_blockers = [current_route_blocker] if current_route_blocker is not None else []
    next_route_action = route_report.get("next_route_action")
    if next_route_action is None:
        next_route_action = critical_path_phase.get("next_action") or route_action_for_blocker(
            current_route_blocker
        )
    route_blocked = route_report.get("route_blocked")
    if not isinstance(route_blocked, bool):
        route_blocked = bool(remaining_route_blockers)
    return {
        "route_blocked": route_blocked,
        "current_route_blocker": current_route_blocker,
        "remaining_route_blockers": remaining_route_blockers,
        "next_route_action": next_route_action,
    }


def normalized_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


def normalized_claim_path_parts(path: str) -> list[str]:
    return [
        part
        for part in (
            normalized_claim_key(raw_part)
            for raw_part in re.split(r"(?:\.|\[\d+\])", path)
        )
        if part
    ]


def positive_route_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) in {
            "accepted",
            "allowed",
            "approved",
            "authorized",
            "available",
            "complete",
            "delivered",
            "enabled",
            "granted",
            "met",
            "passed",
            "promoted",
            "public",
            "reachable",
            "ready",
            "resolved",
            "reviewed",
            "satisfied",
            "sent",
            "sent_ok",
            "supported",
            "true",
            "unlocked",
            "validated",
            "verified",
            "yes",
        }
    if isinstance(value, list):
        return any(positive_route_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(positive_route_claim_value(item) for item in value.values())
    return False


def positive_contract_record_status_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) in BOUND_IDENTITY_CONTRACT_RECORD_POSITIVE_STATUS_VALUES
    if isinstance(value, list):
        return any(positive_contract_record_status_value(item) for item in value)
    if isinstance(value, dict):
        return any(positive_contract_record_status_value(item) for item in value.values())
    return False


def path_in_identity_contract_record_context(path: str) -> bool:
    parts = set(normalized_claim_path_parts(path))
    if parts & BOUND_IDENTITY_CONTRACT_RECORD_REQUIREMENT_CONTEXT_KEYS:
        return False
    return bool(parts & BOUND_IDENTITY_CONTRACT_RECORD_CONTEXT_KEYS)


def path_in_identity_contract_record_downstream_context(path: str) -> bool:
    return bool(
        set(normalized_claim_path_parts(path))
        & BOUND_IDENTITY_CONTRACT_RECORD_DOWNSTREAM_CONTEXT_KEYS
    )


def identity_contract_record_nested_status_claim(path: str, key: object, value: Any) -> bool:
    if not path_in_identity_contract_record_context(path):
        return False
    key_name = normalized_claim_key(key)
    if key_name in BOUND_IDENTITY_CONTRACT_RECORD_STATUS_KEYS:
        return positive_contract_record_status_value(value)
    return (
        path_in_identity_contract_record_downstream_context(path)
        and key_name in BOUND_IDENTITY_CONTRACT_RECORD_DOWNSTREAM_STATUS_KEYS
        and positive_contract_record_status_value(value)
    )


def bound_route_alias_key_is_false_only(key_name: str) -> bool:
    return (
        key_name in BOUND_IDENTITY_ROUTE_FALSE_ONLY_KEYS
        or route_gate.public_or_runtime_alias_key_is_forbidden(key_name)
    )


def bound_route_alias_value_is_positive(key_name: str, value: Any) -> bool:
    if key_name in route_gate.MULTI_SURFACE_BETA_CAPTURE_SOURCE_VALUES and isinstance(value, dict):
        return False
    return (
        route_gate.public_or_runtime_alias_value_is_positive(key_name, value)
        or positive_route_claim_value(value)
        or ("progress" in key_name and route_gate.progress_claim_value_is_nonzero(value))
    )


def bound_route_source_marker_is_non_authorizing(marker: str) -> bool:
    key_name = normalized_claim_key(marker)
    return (
        route_gate.public_or_runtime_alias_key_is_forbidden(key_name)
        or BOUND_IDENTITY_ROUTE_NON_AUTHORIZING_SOURCE_RE.search(key_name) is not None
    )


def path_in_bound_route_false_only_context(path: str) -> bool:
    return any(
        bound_route_alias_key_is_false_only(part)
        or BOUND_IDENTITY_ROUTE_NON_AUTHORIZING_SOURCE_RE.search(part) is not None
        for part in normalized_claim_path_parts(path)
    )


def bound_route_nested_status_claim(path: str, key: object, value: Any) -> bool:
    return (
        path_in_bound_route_false_only_context(path)
        and normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_NESTED_STATUS_KEYS
        and bound_route_alias_value_is_positive(normalized_claim_key(key), value)
    )


def route_source_marker_value_is_non_authorizing(value: Any) -> bool:
    if isinstance(value, str):
        return bound_route_source_marker_is_non_authorizing(value)
    if isinstance(value, list):
        return any(route_source_marker_value_is_non_authorizing(item) for item in value)
    if isinstance(value, dict):
        return any(route_source_marker_value_is_non_authorizing(item) for item in value.values())
    return False


def route_source_marker_value_claims_positive_alias(value: Any) -> bool:
    if isinstance(value, str):
        marker = normalized_claim_key(value)
        return bound_route_source_marker_is_non_authorizing(marker) and (
            route_gate.BROAD_P0_ROUTE_ALIAS_STATE_RE.search(marker) is not None
            or route_gate.public_or_runtime_progress_alias_key(marker)
            or BOUND_IDENTITY_ROUTE_NON_AUTHORIZING_SOURCE_RE.search(marker) is not None
        )
    if isinstance(value, list):
        return any(route_source_marker_value_claims_positive_alias(item) for item in value)
    if isinstance(value, dict):
        return any(route_source_marker_value_claims_positive_alias(item) for item in value.values())
    return False


def route_split_source_marker_status_claim(value: dict[str, Any]) -> bool:
    marker_values = [
        item
        for key, item in value.items()
        if normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_SOURCE_CONTEXT_KEYS
    ]
    if not marker_values or not any(route_source_marker_value_is_non_authorizing(item) for item in marker_values):
        return False
    return any(
        bound_route_alias_value_is_positive(normalized_claim_key(key), item)
        for key, item in value.items()
        if normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_SOURCE_STATUS_KEYS
    )


def route_text_path_is_exempt(path: str) -> bool:
    return any(
        normalized_claim_key(part.split("[", 1)[0]) in BOUND_IDENTITY_ROUTE_TEXT_EXEMPT_PATH_PARTS
        for part in path.split(".")
        if part
    )


def route_positive_text_claim(value: str) -> bool:
    for match in BOUND_IDENTITY_ROUTE_POSITIVE_TEXT_RE.finditer(value):
        clause_start = max(
            value.rfind(".", 0, match.start()),
            value.rfind(";", 0, match.start()),
            value.rfind(":", 0, match.start()),
            value.rfind("\n", 0, match.start()),
        )
        clause = value[clause_start + 1 : match.end()]
        if BOUND_IDENTITY_ROUTE_NEGATED_TEXT_RE.search(clause):
            continue
        return True
    return False


def route_public_abi_identity_lookup_handle_claim(value: str) -> bool:
    for clause in re.split(r"[.;:\n\r]", value):
        normalized = normalized_claim_key(clause)
        negated = any(
            match.group(0).casefold() != "before" or "resource_handle" not in normalized
            for match in BOUND_IDENTITY_ROUTE_NEGATED_TEXT_RE.finditer(clause)
        )
        if negated:
            continue
        if any(term in normalized for term in BOUND_IDENTITY_PUBLIC_ABI_CONTEXT_TERMS) and any(
            term in normalized for term in BOUND_IDENTITY_LOOKUP_HANDLE_TERMS
        ):
            return True
    return False


def bound_identity_route_public_or_runtime_claims(value: Any, path: str = "") -> list[str]:
    claims: list[str] = []
    if isinstance(value, dict):
        source_marker_context = any(
            route_source_marker_value_is_non_authorizing(item)
            for key, item in value.items()
            if normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_SOURCE_CONTEXT_KEYS
        )
        if route_split_source_marker_status_claim(value):
            claims.append(path or "$")
        declared_claim_names = [
            str(item)
            for key, item in value.items()
            if normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_SPLIT_CLAIM_NAME_KEYS
            and isinstance(item, str)
        ]
        declared_claim_values = [
            item
            for key, item in value.items()
            if normalized_claim_key(key) in BOUND_IDENTITY_ROUTE_SPLIT_CLAIM_VALUE_KEYS
        ]
        for claim_name in declared_claim_names:
            claim_key = normalized_claim_key(claim_name)
            if bound_route_alias_key_is_false_only(claim_key) and any(
                bound_route_alias_value_is_positive(claim_key, item)
                for item in declared_claim_values
            ):
                claims.append(path or "$")
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            key_name = normalized_claim_key(key)
            if bound_route_alias_key_is_false_only(key_name) and bound_route_alias_value_is_positive(
                key_name,
                item,
            ):
                claims.append(item_path)
            if key_name in BOUND_IDENTITY_ROUTE_SOURCE_CONTEXT_KEYS and route_source_marker_value_claims_positive_alias(
                item
            ):
                claims.append(item_path)
            if (
                key_name in BOUND_IDENTITY_ROUTE_SOURCE_STATUS_KEYS
                and source_marker_context
                and bound_route_alias_value_is_positive(key_name, item)
            ):
                claims.append(item_path)
            if identity_contract_record_nested_status_claim(item_path, key, item):
                claims.append(item_path)
            if bound_route_nested_status_claim(item_path, key, item):
                claims.append(item_path)
            claims.extend(bound_identity_route_public_or_runtime_claims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(bound_identity_route_public_or_runtime_claims(item, f"{path}[{index}]"))
    elif isinstance(value, str) and not route_text_path_is_exempt(path):
        if route_positive_text_claim(value):
            claims.append(f"{path}:positive_text_claim")
        if route_public_abi_identity_lookup_handle_claim(value):
            claims.append(f"{path}:public_abi_identity_lookup_handle_claim")
    return sorted(set(claims))


def value_contains_admin_target(value: Any) -> bool:
    if isinstance(value, str):
        return value in BOUND_IDENTITY_ADMIN_TARGETS_NOT_IDENTITY_SOURCES
    if isinstance(value, list):
        return any(value_contains_admin_target(item) for item in value)
    if isinstance(value, dict):
        return any(value_contains_admin_target(item) for item in value.values())
    return False


def admin_target_path_is_identity_source_context(path: str) -> bool:
    parts = set(normalized_claim_path_parts(path))
    if parts & BOUND_IDENTITY_ADMIN_TARGET_SAFE_CONTEXT_KEYS:
        return False
    return bool(parts & BOUND_IDENTITY_ADMIN_TARGET_SOURCE_CONTEXT_KEYS)


def bound_identity_admin_target_source_claims(value: Any, path: str = "") -> list[str]:
    claims: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}" if path else str(key)
            key_name = normalized_claim_key(key)
            if (
                key_name in BOUND_IDENTITY_ADMIN_TARGET_SOURCE_CONTEXT_KEYS
                and value_contains_admin_target(item)
                and admin_target_path_is_identity_source_context(item_path)
            ):
                claims.append(item_path)
            claims.extend(bound_identity_admin_target_source_claims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(bound_identity_admin_target_source_claims(item, f"{path}[{index}]"))
    elif (
        isinstance(value, str)
        and value in BOUND_IDENTITY_ADMIN_TARGETS_NOT_IDENTITY_SOURCES
        and admin_target_path_is_identity_source_context(path)
    ):
        claims.append(path)
    return sorted(set(claims))


def post_evidence_identity_contract_record_is_required(simulation: dict[str, Any]) -> bool:
    record = simulation.get("required_identity_public_contract_decision_record")
    return (
        isinstance(record, dict)
        and record.get("review_status") == "reviewed"
        and record.get("hash_bound_to_current_source_artifacts") is True
        and record.get("decision_scope") == "contract_review_only"
    )


def post_evidence_identity_contract_requirement_is_explicit(simulation: dict[str, Any]) -> bool:
    return (
        simulation.get("reviewed_identity_public_contract_required") is True
        and simulation.get("hash_current_identity_public_contract_decision_record_required") is True
        and simulation.get("permissions_admin_unlock_requires_reviewed_hash_current_identity_contract") is True
        and simulation.get("blocked_until_after_accepted_runtime_evidence")
        == [
            "reviewed_identity_public_contract",
            "hash_current_identity_public_contract_decision_record",
        ]
    )


def post_evidence_identity_contract_requirement_is_bound(simulation: dict[str, Any]) -> bool:
    cannot_unlock_without = simulation.get("cannot_unlock_without")
    return (
        post_evidence_identity_contract_record_is_required(simulation)
        and isinstance(cannot_unlock_without, list)
        and "reviewed_identity_public_contract_decision_record" in cannot_unlock_without
        and "hash_current_source_artifacts" in cannot_unlock_without
        and "contract_review_only_scope" in cannot_unlock_without
    )


def post_evidence_child_lock_summaries_are_safe(simulation: dict[str, Any]) -> bool:
    children = simulation.get("p0_child_checks")
    if not isinstance(children, list):
        return False
    by_name = {child.get("name"): child for child in children if isinstance(child, dict)}
    for name in BOUND_IDENTITY_DOWNSTREAM_CHILD_CHECKS:
        child = by_name.get(name)
        if not isinstance(child, dict):
            return False
        if child.get("present") is not True:
            return False
        if child.get("dependency_chain_locked") is not True:
            return False
        if child.get("current_route_blocker") != "identity_public_contract_gate_missing":
            return False
        if child.get("remaining_route_blockers") != ["identity_public_contract_gate_missing"]:
            return False
        if any(child.get(key) is not False for key in BOUND_IDENTITY_DOWNSTREAM_CHILD_FALSE_KEYS):
            return False
    return True


def post_evidence_simulation_acceptance_flag_is_safe(route_report: dict[str, Any]) -> bool:
    simulation = route_report.get("post_evidence_p0_lock_simulation")
    if not isinstance(simulation, dict):
        return False
    false_keys = (
        "command_response_unlocked",
        "commands_replies_unlocked",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain_claim",
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "permissions_admin_unlocked",
        "promotion_ready",
        "public_abi_ready",
        "public_header_allowed",
        "public_or_runtime_accounting_allowed",
        "public_sdk_ready",
        "identity_public_contract_decision_record_contract_review_only",
        "identity_public_contract_decision_record_hash_current",
        "identity_public_contract_decision_record_reviewed",
        "reviewed_hash_current_contract_review_only",
        "runtime_ready",
        "stable_claim_allowed",
    )
    optional_false_keys = (
        "lookup_ready",
        "p0_progress_ready",
        "public_api_ready",
        "public_readiness",
        "runtime_readiness",
        "sdk_p0_progress_ready",
        "v1_completion_ready",
        "v1_completion_evidence",
    )
    zero_keys = (
        "complete_sdk_claim_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
    )
    optional_zero_or_false_keys = (
        "claim_progress",
        "claim_progress_contribution",
        "complete_sdk_progress_contribution",
        "p0_dependency_chain_progress_contribution",
        "p0_progress",
        "progress",
        "progress_contribution",
        "progress_percent",
        "progress_ratio",
        "public_sdk_progress_contribution",
        "runtime_progress_contribution",
        "sdk_p0_progress",
    )
    identity_contract_requirement_present = (
        post_evidence_identity_contract_requirement_is_explicit(simulation)
        or post_evidence_identity_contract_requirement_is_bound(simulation)
    )
    return (
        simulation.get("schema") == "obelisk.command-permission-route-post-evidence-p0-lock-simulation.v1"
        and simulation.get("simulation_only") is True
        and simulation.get("approved_runtime_evidence_accepted") is True
        and simulation.get("identity_public_contract_required") is True
        and simulation.get("current_route_blocker") == "identity_public_contract_gate_missing"
        and simulation.get("simulated_route_blocker_after_accepted_runtime_evidence")
        == "identity_public_contract_gate_missing"
        and (
            simulation.get("remaining_route_blockers_after_accepted_runtime_evidence")
            == ["identity_public_contract_gate_missing"]
            or route_report.get("remaining_route_blockers") == ["identity_public_contract_gate_missing"]
        )
        and identity_contract_requirement_present
        and post_evidence_child_lock_summaries_are_safe(simulation)
        and all(simulation.get(key) is False for key in false_keys)
        and all(key not in simulation or simulation.get(key) is False for key in optional_false_keys)
        and all(simulation.get(key) == 0 for key in zero_keys)
        and all(
            key not in simulation
            or simulation.get(key) is False
            or not route_gate.progress_claim_value_is_nonzero(simulation.get(key))
            for key in optional_zero_or_false_keys
        )
    )


def validate_accepted_runtime_downstream_child_locks(route_report: dict[str, Any]) -> list[str]:
    checks = route_report.get("checks")
    if not isinstance(checks, list):
        return ["route_gate_downstream_child_checks_missing"]
    checks_by_name = {check.get("name"): check for check in checks if isinstance(check, dict)}
    blockers: list[str] = []
    for name in sorted(BOUND_IDENTITY_DOWNSTREAM_CHILD_CHECKS):
        check = checks_by_name.get(name)
        blocker_prefix = f"route_gate_{name}"
        if not isinstance(check, dict):
            blockers.append(f"{blocker_prefix}_missing")
            continue
        if check.get("dependency_chain_locked") is not True:
            blockers.append(f"{blocker_prefix}_dependency_chain_unlocked")
        if check.get("current_route_blocker") != "identity_public_contract_gate_missing":
            blockers.append(f"{blocker_prefix}_current_blocker_unexpected")
        if check.get("remaining_route_blockers") != ["identity_public_contract_gate_missing"]:
            blockers.append(f"{blocker_prefix}_remaining_blockers_unexpected")
        for key in BOUND_IDENTITY_DOWNSTREAM_CHILD_FALSE_KEYS:
            if check.get(key) is not False:
                blockers.append(f"{blocker_prefix}_{key}_overclaim")
    return blockers


def allowed_bound_route_claim_paths(route_report: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    simulation = route_report.get("post_evidence_p0_lock_simulation")
    if isinstance(simulation, dict) and simulation.get("approved_runtime_evidence_accepted") is False:
        allowed.add(POST_EVIDENCE_RUNTIME_ACCEPTANCE_SIMULATION_FLAG)
    elif post_evidence_simulation_acceptance_flag_is_safe(route_report):
        allowed.update(POST_EVIDENCE_RUNTIME_ACCEPTANCE_SIMULATION_ALLOWED_TRUE_FLAGS)
    return allowed


def string_list_is_subset(value: Any, allowed: frozenset[str]) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item in allowed for item in value)


def accepted_runtime_parent_lock_shape_is_safe(route_report: dict[str, Any]) -> bool:
    phase = route_report.get("critical_path_phase")
    if not isinstance(phase, dict):
        return False
    route_lock = route_report.get("route_lock")
    if not isinstance(route_lock, dict):
        return False
    aliases = route_lock_aliases(route_report)
    if (
        aliases["route_blocked"] is not True
        or aliases["current_route_blocker"] != "identity_public_contract_gate_missing"
        or aliases["remaining_route_blockers"] != ["identity_public_contract_gate_missing"]
        or phase.get("current_blocker") != "identity_public_contract_gate_missing"
        or phase.get("source_checker_primary_blocker") != "identity_public_contract_gate_missing"
        or phase.get("next_after_runtime_evidence") != "identity_public_contract_gate_missing"
        or route_lock.get("locked") is not True
        or route_lock.get("blocked_until") != ["reviewed_identity_public_contract"]
    ):
        return False
    diagnosis = phase.get("source_checker_approved_runtime_evidence_manifest")
    if not isinstance(diagnosis, dict) or not approved_runtime_evidence_diagnosis_ready(diagnosis):
        return False
    source_claims = phase.get("source_checker_public_or_runtime_claims", [])
    if not string_list_is_subset(
        source_claims,
        BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_SOURCE_CHECKER_CLAIMS,
    ):
        return False
    checks = route_report.get("checks")
    if not isinstance(checks, list):
        return False
    for check in checks:
        if not isinstance(check, dict) or check.get("name") != "player_identity_public_contract_gap":
            continue
        if not string_list_is_subset(
            check.get("public_or_runtime_claims", []),
            BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_ROUTE_CHECK_CLAIMS,
        ):
            return False
    return True


def accepted_runtime_parent_lock_public_contract_gap_blocker_is_safe(
    route_report: dict[str, Any],
    blocker: str,
) -> bool:
    if not blocker.startswith(BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_PUBLIC_CONTRACT_GAP_PREFIX):
        return False
    claim_text = blocker[len(BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_PUBLIC_CONTRACT_GAP_PREFIX) :]
    claims = [claim.strip() for claim in claim_text.split(",") if claim.strip()]
    return (
        bool(claims)
        and accepted_runtime_parent_lock_shape_is_safe(route_report)
        and all(claim in BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_ROUTE_CHECK_CLAIMS for claim in claims)
    )


def accepted_runtime_parent_lock_blocker_is_quarantined(route_report: dict[str, Any], blocker: Any) -> bool:
    if not isinstance(blocker, str):
        return False
    if blocker in QUARANTINED_DOWNSTREAM_ROUTE_GATE_BLOCKERS:
        return True
    if blocker == "critical_path_identity_readiness_public_or_runtime_claim":
        return accepted_runtime_parent_lock_shape_is_safe(route_report)
    return accepted_runtime_parent_lock_public_contract_gap_blocker_is_safe(route_report, blocker)


def bound_route_claim_is_allowed_parent_lock_diagnostic(route_report: dict[str, Any], claim: str) -> bool:
    if not accepted_runtime_parent_lock_shape_is_safe(route_report):
        return False
    match = BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_PUBLIC_CONTRACT_GAP_CLAIM_PATH_RE.fullmatch(claim)
    return (
        match is not None
        and (
            match.group("claim") in BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_ROUTE_CHECK_CLAIMS
            or match.group("claim") in BOUND_IDENTITY_ACCEPTED_RUNTIME_PARENT_LOCK_CHILD_CHECK_CLAIMS
        )
    )


def collect_bound_route_public_or_runtime_claims(route_report: dict[str, Any]) -> list[str]:
    allowed_paths = allowed_bound_route_claim_paths(route_report)
    return sorted(
        claim
        for claim in (
            (
                set(route_gate.collect_public_or_runtime_claims(route_report, include_text_claims=True))
                | set(bound_identity_route_public_or_runtime_claims(route_report))
                | set(bound_identity_admin_target_source_claims(route_report))
            )
            - allowed_paths
        )
        if not bound_route_claim_is_allowed_parent_lock_diagnostic(route_report, claim)
    )


def route_gate_failure_is_quarantined_downstream_lock(route_report: dict[str, Any] | None) -> bool:
    if not isinstance(route_report, dict):
        return False
    blockers = route_report.get("blockers")
    return (
        route_report.get("schema") == ROUTE_GATE_SCHEMA
        and route_report.get("planning_only") is True
        and route_report.get("route_blocked") is True
        and all(route_report.get(key) is False for key in ROUTE_GATE_REQUIRED_FALSE_KEYS)
        and all(route_report.get(key) is False for key in ROUTE_GATE_OPTIONAL_FALSE_KEYS if key in route_report)
        and isinstance(blockers, list)
        and bool(blockers)
        and all(accepted_runtime_parent_lock_blocker_is_quarantined(route_report, blocker) for blocker in blockers)
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    binder.atomic_write_json(path, payload)


def build_transient_binding(
    *,
    snapshot_root: Path,
    lifecycle_manifest: Path,
    principal_manifest: Path,
    temp_root: Path,
) -> tuple[dict[str, Any], Path, Path]:
    first_evidence = build_redacted_ufunction_signatures.build_players_identity_first_evidence(
        snapshot_root=snapshot_root
    )
    first_path = temp_root / "players-identity-first-evidence.json"
    write_json(first_path, first_evidence)

    lifecycle, lifecycle_path = binder.load_json(lifecycle_manifest, "lifecycle-anchor-candidates")
    principal, principal_path = binder.load_json(principal_manifest, "principal-invalidation-policy")
    binder.validate_inputs(first_evidence=first_evidence, lifecycle=lifecycle, principal=principal)
    lifecycle_snapshot_root_binding = binder.validate_lifecycle_anchor_snapshot_root(
        lifecycle=lifecycle,
        snapshot_root=snapshot_root,
    )

    output_dir = binder.prepare_output_dir(temp_root / "bound")
    lifecycle_output = output_dir / binder.LIFECYCLE_OUTPUT_NAME
    principal_output = output_dir / binder.PRINCIPAL_OUTPUT_NAME
    report_output = output_dir / binder.REPORT_OUTPUT_NAME

    bound_lifecycle = binder.bind_lifecycle_to_first_evidence(lifecycle, first_evidence)
    lifecycle_blockers = binder.lifecycle_anchor_candidates.validate_manifest(bound_lifecycle, promote=False)
    if lifecycle_blockers:
        raise SystemExit(
            "bound lifecycle-anchor candidates failed validation: "
            + json.dumps(binder.validation_reasons(lifecycle_blockers), sort_keys=True)
        )
    bound_principal = binder.bind_principal_to_lifecycle(principal, bound_lifecycle)
    principal_blockers = binder.principal_invalidation_policy.validate_manifest(
        bound_principal,
        check_mode="consume",
    ).blockers
    if principal_blockers:
        raise SystemExit(
            "bound principal invalidation policy failed validation: "
            + json.dumps(binder.validation_reasons(principal_blockers), sort_keys=True)
        )

    write_json(lifecycle_output, bound_lifecycle)
    write_json(principal_output, bound_principal)
    binding_report = binder.build_report(
        first_path=first_path,
        lifecycle_path=lifecycle_path,
        principal_path=principal_path,
        first_evidence=first_evidence,
        lifecycle_output=lifecycle_output,
        principal_output=principal_output,
        bound_lifecycle=bound_lifecycle,
        bound_principal=bound_principal,
    )
    write_json(report_output, binding_report)
    return binding_report, lifecycle_output, principal_output, lifecycle_snapshot_root_binding


def run_route_gate(
    args: argparse.Namespace,
    *,
    lifecycle_output: Path,
    principal_output: Path,
    temp_root: Path,
    approved_runtime: Path | None,
) -> tuple[int, dict[str, Any] | None, str, str | None]:
    query_failclosed_artifact = safe_optional_input_path(args.query_failclosed_artifact, "query-failclosed-artifact")
    player_identity_decisions = safe_optional_input_path(args.player_identity_decisions, "player-identity-decisions")
    public_sdk_surfaces = safe_optional_input_path(args.public_sdk_surfaces, "public-sdk-surfaces")
    private_candidate_contract = safe_optional_input_path(
        args.player_identity_private_candidate_contract,
        "player-identity-private-candidate-contract",
    )
    public_header = safe_optional_input_path(args.public_header, "public-header")
    command_response_root = safe_optional_input_path(args.command_response_root, "command-response-root")
    command_response_readiness = safe_optional_input_path(args.command_response_readiness, "command-response-readiness")
    argv = [
        sys.executable,
        str(SCRIPT_DIR / "check_command_permission_route_gate.py"),
        "--query-failclosed-artifact",
        str(query_failclosed_artifact),
        "--player-identity-decisions",
        str(player_identity_decisions),
        "--public-sdk-surfaces",
        str(public_sdk_surfaces),
        "--player-identity-private-candidate-contract",
        str(private_candidate_contract),
        "--public-header",
        str(public_header),
        "--player-identity-snapshot-root",
        str(args.snapshot_root),
        "--lifecycle-anchor-candidates-manifest",
        str(lifecycle_output),
        "--principal-invalidation-policy-manifest",
        str(principal_output),
        "--json",
    ]
    candidate_root = safe_optional_input_path(args.candidate_root, "candidate-root")
    artifact_root = safe_optional_input_path(args.artifact_root, "artifact-root")
    if candidate_root is not None:
        argv.extend(["--player-identity-candidate-root", str(candidate_root)])
    if artifact_root is not None:
        argv.extend(["--player-identity-artifact-root", str(artifact_root)])
    if command_response_root is not None:
        argv.extend(["--command-response-root", str(command_response_root)])
    if command_response_readiness is not None:
        argv.extend(["--command-response-readiness", str(command_response_readiness)])
    if approved_runtime is not None:
        argv.extend(["--approved-runtime-principal-lifecycle-evidence-manifest", str(approved_runtime)])
    env = os.environ.copy()
    env.update({"TMPDIR": str(temp_root), "TEMP": str(temp_root), "TMP": str(temp_root)})
    result = subprocess.run(
        argv,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    parse_error = None
    report = None
    try:
        loaded = json.loads(result.stdout)
        if isinstance(loaded, dict):
            report = loaded
        else:
            parse_error = "stdout_json_not_object"
    except json.JSONDecodeError as exc:
        parse_error = f"stdout_json_decode_error: {exc}"
    return result.returncode, report, result.stderr.strip(), parse_error


def route_manifest_path_matches(manifest: dict[str, Any], expected_path: Path) -> bool:
    expected = str(expected_path.resolve())
    return (
        manifest.get("expected_resolved_path") == expected
        and manifest.get("observed_resolved_path") == expected
    )


def route_manifest_cli_binding_matches(manifest: dict[str, Any], expected_path: Path) -> bool:
    expected_text = str(expected_path)
    return (
        manifest.get("source") == "cli_bound"
        and manifest.get("provided_by_cli") is True
        and manifest.get("expected_path") == expected_text
        and manifest.get("observed_path") == expected_text
        and manifest.get("matched") is True
        and route_manifest_path_matches(manifest, expected_path)
    )


def approved_runtime_evidence_diagnosis_matches_path(diagnosis: dict[str, Any], expected_path: Path) -> bool:
    expected = str(expected_path.resolve())
    observed = diagnosis.get("path")
    if not isinstance(observed, str) or observed != expected:
        return False
    return str(Path(observed).resolve()) == expected


def approved_runtime_evidence_diagnosis_ready(diagnosis: dict[str, Any]) -> bool:
    return (
        diagnosis.get("report_schema") == APPROVED_RUNTIME_EVIDENCE_REPORT_SCHEMA
        and diagnosis.get("input_schema") == APPROVED_RUNTIME_EVIDENCE_INPUT_SCHEMA
        and diagnosis.get("mode") == "consume"
        and diagnosis.get("ready_scope") == "runtime_evidence_only"
        and diagnosis.get("ready") is True
        and diagnosis.get("approved_runtime_evidence_present") is True
        and diagnosis.get("runtime_evidence_ready") is True
        and diagnosis.get("remaining_blockers") == []
        and diagnosis.get("blockers") == []
        and diagnosis.get("next_blocker") == "identity_public_contract_gate_missing"
        and all(diagnosis.get(key) is False for key in APPROVED_RUNTIME_EVIDENCE_REQUIRED_FALSE_KEYS)
        and all(
            key not in diagnosis or diagnosis.get(key) is False
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_FALSE_KEYS
        )
        and all(diagnosis.get(key) == [] for key in APPROVED_RUNTIME_EVIDENCE_EMPTY_KEYS)
        and all(
            key not in diagnosis or not route_gate.progress_claim_value_is_nonzero(diagnosis.get(key))
            for key in APPROVED_RUNTIME_EVIDENCE_OPTIONAL_ZERO_KEYS
        )
        and diagnosis.get("observed_runtime_cases") == APPROVED_RUNTIME_EVIDENCE_OBSERVED_RUNTIME_CASES
        and diagnosis.get("consumer_cases") == APPROVED_RUNTIME_EVIDENCE_CONSUMER_CASES
    )


def approved_runtime_evidence_diagnosis_case_mismatches(
    diagnosis: dict[str, Any],
    checked_report: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(checked_report, dict):
        return ["route_gate_approved_runtime_evidence_checked_report_missing"]
    blockers: list[str] = []
    if diagnosis.get("input_schema") != checked_report.get("input_schema"):
        blockers.append("route_gate_approved_runtime_evidence_input_schema_mismatch")
    for key in ("observed_runtime_cases", "consumer_cases"):
        if diagnosis.get(key) != checked_report.get(key):
            blockers.append(f"route_gate_approved_runtime_evidence_{key}_mismatch")
    return blockers


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    snapshot_root = safe_snapshot_root(args.snapshot_root)
    args.snapshot_root = snapshot_root
    lifecycle_manifest, principal_manifest = resolve_manifest_pair(args)
    approved_runtime = safe_optional_input_path(
        getattr(args, "approved_runtime_principal_lifecycle_evidence_manifest", None),
        "approved-runtime-principal-lifecycle-evidence-manifest",
    )
    with tempfile.TemporaryDirectory(prefix="obelisk-bound-player-identity-route-") as temp_dir:
        temp_root = Path(temp_dir)
        reject_symlink_component(temp_root, "temp-root")
        reject_protected_output_path(temp_root, "temp-root")
        approved_runtime_evidence_check = None
        approved_runtime_accepted = False
        if approved_runtime is not None:
            (
                approved_runtime_accepted,
                approved_runtime_report,
                approved_runtime_returncode,
                approved_runtime_stderr,
                approved_runtime_parse_error,
            ) = check_approved_runtime_evidence_manifest(approved_runtime, temp_root)
            approved_runtime_public_or_runtime_claims = approved_runtime_evidence_report_public_or_runtime_claims(
                approved_runtime_report
            )
            approved_runtime_accepted = (
                approved_runtime_accepted
                and approved_runtime_evidence_report_accepted(approved_runtime_report)
            )
            approved_runtime_evidence_check = {
                "accepted": approved_runtime_accepted,
                "forwarded_to_route_gate": approved_runtime_accepted,
                "returncode": approved_runtime_returncode,
                "stderr": approved_runtime_stderr,
                "parse_error": approved_runtime_parse_error,
                "public_or_runtime_claims": approved_runtime_public_or_runtime_claims,
                "report": approved_runtime_report,
            }
        accepted_approved_runtime = approved_runtime if approved_runtime_accepted else None
        expected_blocker = (
            "identity_public_contract_gate_missing"
            if accepted_approved_runtime is not None
            else "approved_runtime_evidence_missing"
        )
        expected_blocked_until = (
            ["reviewed_identity_public_contract"]
            if accepted_approved_runtime is not None
            else ["approved_runtime_principal_lifecycle_evidence", "reviewed_identity_public_contract"]
        )
        (
            binding_report,
            lifecycle_output,
            principal_output,
            lifecycle_snapshot_root_binding,
        ) = build_transient_binding(
            snapshot_root=snapshot_root,
            lifecycle_manifest=lifecycle_manifest,
            principal_manifest=principal_manifest,
            temp_root=temp_root,
        )
        route_returncode, route_report, route_stderr, route_parse_error = run_route_gate(
            args,
            lifecycle_output=lifecycle_output,
            principal_output=principal_output,
            temp_root=temp_root,
            approved_runtime=accepted_approved_runtime,
        )

    blockers: list[str] = []
    if approved_runtime is not None and not approved_runtime_accepted:
        blockers.append("approved_runtime_evidence_not_accepted")
    if (
        isinstance(approved_runtime_evidence_check, dict)
        and approved_runtime_evidence_check.get("public_or_runtime_claims")
    ):
        blockers.append("approved_runtime_evidence_public_or_runtime_claims_overclaim")
    route_gate_downstream_lock_quarantined = route_gate_failure_is_quarantined_downstream_lock(route_report)
    if binding_report.get("ready") is not True:
        blockers.append("identity_planning_binding_not_ready")
    if route_returncode != 0 and not route_gate_downstream_lock_quarantined:
        blockers.append("route_gate_exit_code_unexpected")
    if route_parse_error is not None:
        blockers.append("route_gate_output_invalid")
    if route_report is None:
        blockers.append("route_gate_report_missing")
    else:
        phase = route_report.get("critical_path_phase")
        route_lock = route_report.get("route_lock")
        current_blocker = phase.get("current_blocker") if isinstance(phase, dict) else None
        source_checker_primary_blocker = phase.get("source_checker_primary_blocker") if isinstance(phase, dict) else None
        source_checker_status = phase.get("source_checker_status") if isinstance(phase, dict) else None
        source_checker_ready = phase.get("source_checker_ready") if isinstance(phase, dict) else None
        source_checker_internal_planning = (
            phase.get("source_checker_accepted_for_internal_planning") if isinstance(phase, dict) else None
        )
        next_after_runtime = phase.get("next_after_runtime_evidence") if isinstance(phase, dict) else None
        manifest_sources = phase.get("source_checker_manifest_sources") if isinstance(phase, dict) else None
        approved_runtime_diagnosis = (
            phase.get("source_checker_approved_runtime_evidence_manifest") if isinstance(phase, dict) else None
        )
        route_public_or_runtime_claims = collect_bound_route_public_or_runtime_claims(route_report)
        if route_report.get("schema") != ROUTE_GATE_SCHEMA:
            blockers.append("route_gate_schema_mismatch")
        post_evidence_simulation = route_report.get("post_evidence_p0_lock_simulation")
        if (
            isinstance(post_evidence_simulation, dict)
            and post_evidence_simulation.get("approved_runtime_evidence_accepted") is True
            and not post_evidence_simulation_acceptance_flag_is_safe(route_report)
        ):
            blockers.append("route_gate_post_evidence_simulation_contract_requirement_missing")
        if (
            route_report.get("valid") is not True
            or route_report.get("accepted_for_planning") is not True
        ) and not route_gate_downstream_lock_quarantined:
            blockers.append("route_gate_not_accepted_for_planning")
        if route_report.get("planning_only") is not True:
            blockers.append("route_gate_not_planning_only")
        if route_report.get("blockers") and not route_gate_downstream_lock_quarantined:
            blockers.append("route_gate_blockers_not_empty")
        for key in ROUTE_GATE_REQUIRED_FALSE_KEYS:
            if route_report.get(key) is not False:
                blockers.append(f"route_gate_{key}_overclaim")
        for key in ROUTE_GATE_OPTIONAL_FALSE_KEYS:
            if key in route_report and route_report.get(key) is not False:
                blockers.append(f"route_gate_{key}_overclaim")
        if route_public_or_runtime_claims:
            blockers.append("route_gate_public_or_runtime_claims_overclaim")
        if current_blocker != expected_blocker:
            blockers.append("route_gate_bound_identity_blocker_unexpected")
        if current_blocker is None:
            blockers.append("route_gate_bound_identity_current_blocker_missing")
        if source_checker_primary_blocker != expected_blocker:
            blockers.append("route_gate_bound_identity_primary_blocker_unexpected")
        if source_checker_status != "blocked":
            blockers.append("route_gate_identity_readiness_status_unexpected")
        if source_checker_ready is not False:
            blockers.append("route_gate_identity_readiness_ready_flag_overclaim")
        if source_checker_internal_planning is not False:
            blockers.append("route_gate_identity_readiness_internal_planning_overclaim")
        if next_after_runtime != "identity_public_contract_gate_missing":
            blockers.append("route_gate_next_after_runtime_evidence_unexpected")
        for key in ("permissions_admin_unlocked", "command_response_unlocked", "commands_replies_unlocked"):
            if not isinstance(phase, dict) or phase.get(key) is not False:
                blockers.append(f"route_gate_{key}_overclaim")
        if accepted_approved_runtime is not None:
            blockers.extend(validate_accepted_runtime_downstream_child_locks(route_report))
            if not isinstance(approved_runtime_diagnosis, dict):
                blockers.append("route_gate_approved_runtime_evidence_manifest_missing")
            else:
                if not approved_runtime_evidence_diagnosis_ready(approved_runtime_diagnosis):
                    blockers.append("route_gate_approved_runtime_evidence_not_ready")
                if not approved_runtime_evidence_diagnosis_matches_path(
                    approved_runtime_diagnosis,
                    accepted_approved_runtime,
                ):
                    blockers.append("route_gate_approved_runtime_evidence_path_alias")
                checked_runtime_report = (
                    approved_runtime_evidence_check.get("report")
                    if isinstance(approved_runtime_evidence_check, dict)
                    else None
                )
                blockers.extend(
                    approved_runtime_evidence_diagnosis_case_mismatches(
                        approved_runtime_diagnosis,
                        checked_runtime_report,
                    )
                )
        elif isinstance(approved_runtime_diagnosis, dict) and approved_runtime_evidence_diagnosis_ready(
            approved_runtime_diagnosis
        ):
            blockers.append("route_gate_approved_runtime_evidence_unexpected")
        if not isinstance(manifest_sources, dict):
            blockers.append("route_gate_bound_identity_manifest_sources_missing")
        else:
            if manifest_sources.get("mode") != "cli_bound":
                blockers.append("route_gate_bound_identity_manifest_source_mode_unexpected")
            if manifest_sources.get("expected_manifests_received") is not True:
                blockers.append("route_gate_bound_identity_expected_manifests_missing")
            manifests = manifest_sources.get("manifests")
            if not isinstance(manifests, dict):
                blockers.append("route_gate_bound_identity_manifest_details_missing")
            else:
                expected_bound_paths = {
                    "lifecycle_anchor_candidates": lifecycle_output,
                    "principal_invalidation_policy": principal_output,
                }
                for key in ("lifecycle_anchor_candidates", "principal_invalidation_policy"):
                    manifest = manifests.get(key)
                    if not isinstance(manifest, dict):
                        blockers.append(f"route_gate_bound_identity_{key}_source_unexpected")
                    elif manifest.get("source") != "cli_bound":
                        blockers.append(f"route_gate_bound_identity_{key}_source_unexpected")
                    elif manifest.get("provided_by_cli") is not True:
                        blockers.append(f"route_gate_bound_identity_{key}_not_cli_provided")
                    elif manifest.get("matched") is not True:
                        blockers.append(f"route_gate_bound_identity_{key}_path_mismatch")
                    elif not route_manifest_cli_binding_matches(manifest, expected_bound_paths[key]):
                        blockers.append(f"route_gate_bound_identity_{key}_canonical_path_mismatch")
        if not isinstance(route_lock, dict) or route_lock.get("locked") is not True:
            blockers.append("route_gate_lock_unexpected")
        if not isinstance(route_lock, dict) or route_lock.get("blocked_until") != expected_blocked_until:
            blockers.append("route_gate_lock_blocked_until_unexpected")

    critical_path_phase = (
        route_report.get("critical_path_phase")
        if isinstance(route_report, dict) and isinstance(route_report.get("critical_path_phase"), dict)
        else {}
    )
    route_lock = (
        route_report.get("route_lock")
        if isinstance(route_report, dict) and isinstance(route_report.get("route_lock"), dict)
        else {}
    )
    route_aliases = route_lock_aliases(route_report)
    if isinstance(route_report, dict):
        expected_route_blockers = [expected_blocker]
        if route_aliases["route_blocked"] is not True:
            blockers.append("route_gate_route_blocked_alias_unexpected")
        if route_aliases["current_route_blocker"] != expected_blocker:
            blockers.append("route_gate_current_route_blocker_alias_unexpected")
        if route_aliases["remaining_route_blockers"] != expected_route_blockers:
            blockers.append("route_gate_remaining_route_blockers_alias_unexpected")
        if route_aliases["next_route_action"] not in allowed_route_actions_for_blocker(expected_blocker):
            blockers.append("route_gate_next_route_action_alias_unexpected")
    return {
        "schema": REPORT_SCHEMA,
        "valid": not blockers,
        "accepted_for_planning": not blockers,
        "planning_only": True,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "public_api_ready": False,
        "public_abi_ready": False,
        "public_readiness": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "public_header_allowed": False,
        "server_operations_authorized": False,
        "runtime_work_authorized": False,
        "route_blocked": route_aliases["route_blocked"],
        "current_route_blocker": route_aliases["current_route_blocker"],
        "remaining_route_blockers": route_aliases["remaining_route_blockers"],
        "next_route_action": route_aliases["next_route_action"],
        "blockers": blockers,
        "inputs": {
            "snapshot_root": str(snapshot_root),
            "lifecycle_anchor_candidates_manifest": str(lifecycle_manifest),
            "principal_invalidation_policy_manifest": str(principal_manifest),
            "approved_runtime_principal_lifecycle_evidence_manifest": (
                str(approved_runtime) if approved_runtime is not None else None
            ),
        },
        "approved_runtime_evidence_check": approved_runtime_evidence_check,
        "critical_path_phase": critical_path_phase,
        "route_lock": route_lock,
        "binding_report": binding_report,
        "lifecycle_snapshot_root_binding": lifecycle_snapshot_root_binding,
        "route_gate": {
            "returncode": route_returncode,
            "stderr": route_stderr,
            "parse_error": route_parse_error,
            "downstream_lock_failure_quarantined": route_gate_downstream_lock_quarantined,
            "report": route_report,
            "public_or_runtime_claims": (
                collect_bound_route_public_or_runtime_claims(route_report) if isinstance(route_report, dict) else []
            ),
        },
        "non_claims": NON_CLAIMS,
    }


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
