#!/usr/bin/env python3
"""Validate the reviewed player identity public-contract decision record.

This checker is for the post-runtime-evidence review artifact only. A valid record can
resolve the reviewed-identity-contract decision keys for contract review; it does not
publish public ABI, callbacks, lookup, permissions, commands, runtime readiness, SDK
readiness, or v1 completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_checker
import protected_paths


SCHEMA = "obelisk.player-identity-public-contract-decision-record.v1"
REPORT_SCHEMA = "obelisk.player-identity-public-contract-decision-record-check.v1"
SURFACE = "obelisk.player_identity.v1"
ARTIFACT_ID = "reviewed_identity_public_contract_decision_record"
ACTIVE_AFTER_RESOLVED_INPUT = "runtime.lifecycle_evidence"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD = Path(
    "docs/research/player-identity-planning-sources/reviewed-identity-public-contract-decision-record.json"
)
CURRENT_ROUTE = "approved_runtime_evidence_missing"
NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
REVIEW_ROUTE = "reviewed_identity_public_contract_review"
RECORD_VALID_SCOPE = "reviewed_identity_public_contract_record_only"
READY_SCOPE = "no_public_or_header_readiness"
DECISION_SCOPE = "contract_review_only"
APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD = "approved_runtime_evidence_binding"
APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA = (
    "obelisk.player-identity-public-contract-approved-runtime-evidence-binding.v1"
)
APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD = "approved_runtime_evidence_manifest_ref"
APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_SCHEMA = (
    "obelisk.player-identity-public-contract-approved-runtime-evidence-manifest-ref.v1"
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD = "strict_approved_runtime_checker_contract_report"
STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_SCHEMA = (
    "obelisk.player-identity-public-contract-strict-approved-runtime-check-report-ref.v1"
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence-check.v1"
)
STRICT_APPROVED_RUNTIME_CHECKER = (
    "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py"
)
APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND = (
    "obelisk.players-identity-runtime-principal-lifecycle-approved-evidence.v1"
)
APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND = "runtime-observer-log"
APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM = (
    "This binding identifies the accepted runtime lifecycle evidence reviewed by this record; "
    "it does not open public header, public API/ABI/SDK, downstream P0, permissions, "
    "commands, lookup, mutation, return override, or v1 completion."
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_NON_CLAIM = (
    "This reference identifies the strict approved-runtime checker-contract report that "
    "accepted runtime.lifecycle_evidence; it is not standing authorization, a request pack, "
    "route sample, beta notice, package-shape artifact, status report, public readiness, "
    "runtime readiness, SDK/P0 progress, or v1 completion."
)
APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_NON_CLAIM = (
    "This reference identifies the exact approved runtime.lifecycle_evidence manifest bound "
    "to the reviewed decision record; stale runtime bindings, request/window/beta/copy/status "
    "artifacts, and post-runtime aliases cannot replace the checker-accepted manifest."
)
SOURCE_ARTIFACT_HASH_POLICY = (
    "All source artifact paths and sha256 values must match the current repo-local planning artifacts; "
    "stale, mismatched, missing, notice-only, diagnostic-only, passive/runtime-presence, "
    "no-users, request/preflight/runtime-window-planning, receipt/sidecar, scoped-statement, "
    "certificate, status-json, source-overclaim-zero, copied-log-only, package-shape/support-tier, "
    "historical-handoff, public-header, public-API, or public-ABI shortcut artifacts are non-counting and cannot "
    "advance beyond reviewed identity public contract review."
)
SOURCE_ARTIFACT_STALE_REQUIRED_ACTION = (
    "Refresh the reviewed decision record's source_artifacts sha256 values from the current "
    "repo-local artifacts after contract review, then bind the record to accepted "
    "runtime.lifecycle_evidence through approved_runtime_evidence_binding. Until both are true, "
    "the strict route remains approved_runtime_evidence_missing and the only valid post-runtime "
    "blocker remains identity_public_contract_gate_missing."
)
REQUIRED_ROUTE = {
    "current_route": CURRENT_ROUTE,
    "after_accepted_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "accepted_runtime_lifecycle_evidence_advances_to": REVIEW_ROUTE,
    "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
}
POST_RUNTIME_GATE_FIELD = "post_runtime_identity_contract_gate"
REQUIRED_ROUTE_BLOCKER_ALIASES_TRUE = {
    "identityPublicContractGateMissingAfterRuntimeEvidence",
}
REQUIRED_ROUTE_BLOCKER_ALIASES_FALSE = {
    "publicHeaderGateMissingAfterRuntimeEvidence",
    "publicApiGateMissingAfterRuntimeEvidence",
    "publicAbiGateMissingAfterRuntimeEvidence",
    "publicSdkReadinessAfterRuntimeEvidence",
    "runtimeReadinessAfterRuntimeEvidence",
    "v1CompletionAfterRuntimeEvidence",
}
EXPECTED_SOURCE_ARTIFACTS = {
    "public_contract_decisions": {
        "path": "docs/player_identity_public_contract_decisions.json",
        "role": "post_runtime_identity_contract_gate_policy",
    },
    "public_abi_preflight_candidate": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "player-identity-public-abi-preflight-candidate.json"
        ),
        "role": "candidate_only_public_abi_review_input",
    },
    "owner_token_sdk_consumer_contract": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "player-identity-owner-token-sdk-consumer-contract.json"
        ),
        "role": "candidate_only_owner_token_lifecycle_review_input",
    },
    "principal_invalidation_policy": {
        "path": (
            "docs/research/player-identity-planning-sources/"
            "players-identity-principal-invalidation-policy.json"
        ),
        "role": "candidate_only_principal_lifetime_review_input",
    },
}
REQUIRED_REVIEW_DECISION_KEYS = [
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
]
DECISION_ENTRY_KEYS = frozenset({"status", "resolved", "scope", "non_claims"})
DECISION_KEY_MISMATCH_REQUIRED_ACTION = (
    "Bind a hash-current reviewed identity public contract decision record to the accepted "
    "runtime.lifecycle_evidence bundle, then provide exactly the required reviewed decision keys "
    "in both resolved_decision_keys and decisions with each entry reviewed, resolved, and scoped "
    "contract_review_only."
)
NEXT_STEP_CHECK_FIELD = "post_runtime_identity_contract_next_step"
FALSE_FLAGS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
OPTIONAL_FALSE_ALIAS_FLAGS = (
    "public_readiness",
    "runtime_readiness",
    "v1_ready",
    "v1_completion_ready",
    "public_sdk_v1_completion_ready",
    "public_sdk_v1_completion_claim",
    "identity_contract_ready",
    "identity_public_contract_ready",
    "public_identity_ready",
    "public_principal_ready",
    "public_header_ready",
    "public_header_readiness",
    "public_api_allowed",
    "public_api_readiness",
    "public_abi_allowed",
    "public_abi_readiness",
    "public_callback_abi_ready",
    "accepted_for_header_gate_review",
    "accepted_for_public_header_gate_review",
    "accepted_for_public_header_review",
    "accepted_for_public_api_review",
    "accepted_for_public_abi_review",
    "accepted_for_identity_contract_gate_review",
    "accepted_for_identity_public_contract_gate_review",
    "accepted_for_public_identity_contract_gate_review",
    "identity_contract_gate_ready",
    "identity_contract_gate_unlocked",
    "identity_contract_gate_open",
    "identity_contract_gate_resolved",
    "identity_contract_gate_cleared",
    "identity_contract_gate_satisfied",
    "identity_contract_gate_accepted",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_unlocked",
    "identity_public_contract_gate_review_ready",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
    "identity_public_contract_gate_open",
    "identity_public_contract_gate_resolved",
    "identity_public_contract_gate_cleared",
    "identity_public_contract_gate_satisfied",
    "identity_public_contract_gate_accepted",
    "identity_public_contract_gate_missing_resolved",
    "identity_public_contract_gate_missing_cleared",
    "public_header_gate_open",
    "public_header_gate_resolved",
    "public_header_gate_cleared",
    "public_api_gate_ready",
    "public_api_gate_unlocked",
    "public_api_gate_open",
    "public_api_gate_resolved",
    "public_api_gate_cleared",
    "public_abi_gate_ready",
    "public_abi_gate_unlocked",
    "public_abi_gate_open",
    "public_abi_gate_resolved",
    "public_abi_gate_cleared",
    "resource_handle_ready",
    "resource_handle_supported",
    "resource_handle_allowed",
    "mutation_allowed",
    "mutation_ready",
    "mutation_supported",
    "return_override_allowed",
    "return_override_ready",
    "return_override_supported",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "command_response_unlocked",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "chat_replies_ready",
    "send_chat_ready",
    "public_sdk_readiness_after_runtime_evidence",
    "runtime_readiness_after_runtime_evidence",
    "v1_completion_after_runtime_evidence",
)
CLAIM_ALIAS_EXTRA_KEYS = (
    "ready",
    "source_ready",
    "promoted",
    "approved",
    "approved_alias",
    "approval",
    "approval_alias",
    "promotion_allowed",
    "contract_reviewed",
    "identity_contract_reviewed",
    "identity_contract_current",
    "public_contract_decision_record_reviewed",
    "public_contract_decision_record_hash_current",
    "public_contract_decision_record_current",
    "public_contract_decision_record_contract_review_only",
    "header_shape_valid",
    "identity_contract_hash_current",
    "identity_contract_decision_record_reviewed",
    "identity_contract_decision_record_hash_current",
    "hash_current_identity_public_contract",
    "hash_current_public_contract_decision_record",
    "identity_public_contract_reviewed",
    "identity_public_contract_current",
    "identity_public_contract_hash_current",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_decision_record_hash_current",
    "public_identity_contract_reviewed",
    "public_identity_contract_current",
    "public_identity_contract_hash_current",
    "reviewed_identity_contract",
    "reviewed_identity_contract_hash_current",
    "reviewed_identity_public_contract",
    "reviewed_identity_public_contract_current",
    "reviewed_identity_public_contract_hash_current",
    "reviewed_identity_public_contract_record",
    "reviewed_identity_public_contract_record_hash_current",
    "public_contract_record_hash_current",
    "public_contract_record_current",
    "public_contract_record_contract_review_only",
    "blocker_resolved",
    "identity_public_contract_gate_open",
    "identity_public_contract_gate_resolved",
    "identity_public_contract_gate_cleared",
    "identity_public_contract_gate_satisfied",
    "identity_public_contract_gate_accepted",
    "identity_public_contract_gate_missing_resolved",
    "identity_public_contract_gate_missing_cleared",
    "accepted_for_identity_contract_gate_review",
    "accepted_for_identity_public_contract_gate_review",
    "accepted_for_public_identity_contract_gate_review",
    "identity_contract_gate_ready",
    "identity_contract_gate_unlocked",
    "identity_contract_gate_open",
    "identity_contract_gate_resolved",
    "identity_contract_gate_cleared",
    "identity_contract_gate_satisfied",
    "identity_contract_gate_accepted",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_unlocked",
    "identity_public_contract_gate_review_ready",
    "identity_contract_decision_record_contract_review_only",
    "identity_public_contract_decision_record_contract_review_only",
    "identity_public_contract_record_contract_review_only",
    "reviewed_identity_public_contract_contract_review_only",
    "reviewed_identity_public_contract_decision_record_contract_review_only",
    "identity_contract_ready",
    "identity_public_contract_ready",
    "public_identity_ready",
    "public_principal_ready",
    "public_header_ready",
    "public_header_readiness",
    "public_api_allowed",
    "public_api_readiness",
    "public_abi_allowed",
    "public_abi_readiness",
    "public_callback_abi_ready",
    "public_sdk_readiness",
    "runtime_sdk_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "command_response_unlocked",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "broadcast_ready",
    "broadcast_reply_ready",
    "chat_replies_ready",
    "package_shape_ready",
    "installed_sdk_package_shape_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "principal_start_end_ready",
    "principal_start_end_runtime_evidence_ready",
    "runtime_lifecycle_start_end_evidence_ready",
    "start_end_runtime_evidence_ready",
    "lifecycle_start_end_evidence_ready",
    "rcon_ready",
    "rcon_command_ready",
    "rcon_reply_ready",
    "send_chat_ready",
    "approved_runtime_principal_lifecycle_bundle_routes_to",
    "approved_runtime_principal_lifecycle_bundle_next_blocker",
    "approved_runtime_lifecycle_bundle_routes_to",
    "approved_runtime_lifecycle_bundle_next_blocker",
    "runtime_lifecycle_evidence_routes_to",
    "runtime_lifecycle_evidence_next_blocker",
    "approved_runtime_evidence_routes_to",
    "approved_runtime_evidence_next_blocker",
    "stable_claim_allowed",
    "stable_claim_ready",
    "v1_completion_allowed",
    "complete_sdk_claim_ready",
    "counts_toward_complete_sdk_claim",
    "counts_towards_complete_sdk_claim",
    "counts_toward_p0",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_phase0",
    "p0_progress",
    "p0_progress_ready",
    "p0_ready",
    "p0_unlocked",
    "p0_sdk_progress",
    "p0_sdk_progress_ready",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_p0_ready",
    "claim_progress",
    "claim_progress_contribution",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "progress",
    "progress_contribution",
    "progress_percent",
    "progress_ratio",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
)
EMPTY_PUBLIC_LISTS = (
    "public_header_symbols_now",
    "public_capability_bits_now",
    "public_callback_abi_now",
    "public_api_symbols_now",
)
NEXT_STEP_NON_CLAIM_FLAGS = (
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_header_ready",
    "public_abi_ready",
    "public_abi_allowed",
    "public_api_ready",
    "public_api_allowed",
    "public_sdk_ready",
    "public_readiness",
    "runtime_ready",
    "runtime_readiness",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "lookup_ready",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "commands_ready",
    "command_response_ready",
    "command_chat_response_ready",
    "commands_replies_ready",
    "resource_handle_ready",
    "resource_handle_supported",
    "resource_handle_allowed",
    "accepted_for_identity_contract_gate_review",
    "accepted_for_identity_public_contract_gate_review",
    "accepted_for_public_identity_contract_gate_review",
    "identity_contract_gate_ready",
    "identity_contract_gate_unlocked",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_unlocked",
    "identity_public_contract_gate_review_ready",
    "v1_ready",
    "v1_completion_ready",
    "v1_completion_evidence",
    "public_sdk_v1_completion_ready",
    "complete_sdk_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE = {
    "required_input": ACTIVE_AFTER_RESOLVED_INPUT,
    "before_accepted_runtime_evidence": {
        "current_blocker": CURRENT_ROUTE,
        "record_counts_toward_public_sdk": False,
        "record_counts_toward_p0_dependency_chain_claim": False,
        "record_downstream_p0_or_public_sdk_unlock_allowed": False,
        "record_public_sdk_ready": False,
        "record_p0_progress_ready": False,
    },
    "after_accepted_runtime_evidence": {
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "only_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "review_step": REVIEW_ROUTE,
        "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
        "downstream_p0_or_public_sdk_unlock_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "public_sdk_ready": False,
        "public_sdk_v1_completion_ready": False,
        "complete_sdk_ready": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
    },
}
POST_RUNTIME_COMPAT_FALSE_FLAGS = frozenset(
    {
        "counts_toward_complete_sdk_claim",
        "public_sdk_v1_completion_ready",
        "complete_sdk_ready",
        "stable_ready",
        "stable_claim_allowed",
        "stable_claim_ready",
        "stable_sdk_ready",
        "plugin_hub_ready",
        "plugin_hub_publication_ready",
        "publication_ready",
        "publication_authorized",
        "permissions_admin_ready",
        "permissions_admin_public_ready",
        "permissions_admin_unlocked",
        "command_response_ready",
        "command_chat_response_ready",
        "commands_replies_ready",
    }
)
REQUIRED_NEXT_STEP_CHECK = {
    "checker": "scripts/check_player_identity_public_contract_decision_record.py",
    "record_path": str(DEFAULT_RECORD),
    "required_record_state": "reviewed_hash_current_contract_review_only",
    "required_record_scope": RECORD_VALID_SCOPE,
    "required_strict_approved_runtime_checker_contract_report_ref": (
        f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}"
    ),
    "required_strict_approved_runtime_checker_contract_report_state": (
        "report file exists, hash matches, schema is the strict runtime checker report, "
        "lifecycle triplet is selected, and next_blocker=identity_public_contract_gate_missing"
    ),
    "required_approved_runtime_evidence_binding_ref": f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}",
    "required_approved_runtime_evidence_binding_state": (
        "matches accepted runtime.lifecycle_evidence artifact identity and copied runtime-observer log source"
    ),
    "required_approved_runtime_evidence_manifest_ref": f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}",
    "required_approved_runtime_evidence_manifest_state": (
        "manifest file exists, hash matches, schema is approved runtime.lifecycle_evidence, "
        "strict checker accepts it in consume mode, and binding/report match that manifest"
    ),
    "required_source_artifacts_ref": "$.source_artifacts",
    "required_source_artifact_hash_state": "current",
    "post_runtime_identity_contract_gate_ref": f"$.{POST_RUNTIME_GATE_FIELD}",
    "accepted_route": {
        "resolved_input": ACTIVE_AFTER_RESOLVED_INPUT,
        "only_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "review_step": REVIEW_ROUTE,
    },
    "valid_record_scope": REVIEW_ROUTE,
    "non_claim_flags": {key: False for key in NEXT_STEP_NON_CLAIM_FLAGS},
}
CURRENTNESS_DIAGNOSTIC_FIELD = "runtime_evidence_contract_review_currentness"
CURRENTNESS_DIAGNOSTIC_SCHEMA = (
    "obelisk.player-identity-public-contract-currentness-diagnostic.v1"
)
CURRENTNESS_DIAGNOSTIC_NON_CLAIM = (
    "Accepted runtime evidence is only the runtime.lifecycle_evidence input; candidate, "
    "preflight, and review aliases remain non-counting, and the next blocker stays "
    "identity_public_contract_gate_missing until a hash-current reviewed decision record "
    "is bound to the accepted runtime evidence."
)
REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC = {
    "schema": CURRENTNESS_DIAGNOSTIC_SCHEMA,
    "accepted_runtime_evidence_resolved_input": ACTIVE_AFTER_RESOLVED_INPUT,
    "only_next_blocker_after_accepted_runtime_evidence": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "review_step_after_accepted_runtime_evidence": REVIEW_ROUTE,
    "reviewed_record_required": True,
    "reviewed_record_required_state": "reviewed_hash_current_contract_review_only",
    "reviewed_record_required_scope": RECORD_VALID_SCOPE,
    "reviewed_record_source_artifact_hash_state_required": "current",
    "strict_approved_runtime_checker_contract_report_required": True,
    "strict_approved_runtime_checker_contract_report_ref": (
        f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}"
    ),
    "strict_approved_runtime_checker_contract_report_schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
    "strict_approved_runtime_checker": STRICT_APPROVED_RUNTIME_CHECKER,
    "approved_runtime_evidence_binding_required": True,
    "approved_runtime_evidence_binding_ref": f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}",
    "approved_runtime_evidence_manifest_ref_required": True,
    "approved_runtime_evidence_manifest_ref": f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}",
    "approved_runtime_evidence_manifest_ref_schema": APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_SCHEMA,
    "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract": False,
    "accepted_runtime_evidence_can_replace_reviewed_record": False,
    "candidate_preflight_review_aliases_count": False,
    "candidate_preflight_review_aliases_can_clear_gate": False,
    "candidate_preflight_review_aliases_can_replace_reviewed_record": False,
    "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
    "permissions_admin_unlocked_from_runtime_evidence": False,
    "command_surface_unlocked_from_runtime_evidence": False,
    "p0_progress_contribution": 0,
    "non_claim": CURRENTNESS_DIAGNOSTIC_NON_CLAIM,
}
SOURCE_ARTIFACT_ENTRY_KEYS = frozenset({"path", "sha256", "role", "counting_scope"})
SOURCE_ARTIFACT_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS = (
    "public_header_api_abi_sdk_runtime_shortcut_allowed",
    "counts_toward_public_sdk",
    "counts_toward_p0_dependency_chain_claim",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "v1_completion_evidence",
)
APPROVED_RUNTIME_EVIDENCE_BINDING_KEYS = frozenset(
    {
        "schema",
        "accepted_for_contract_review",
        "resolved_input",
        "next_blocker",
        "artifact_kind",
        "evidence_pack_id",
        "artifact_sha256",
        "source_kind",
        "source_path",
        "source_sha256",
        "copied_log_path",
        "copied_log_sha256",
        "binding_scope",
        "non_claim",
        *APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS,
    }
)
APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_KEYS = frozenset(
    {
        "schema",
        "checker",
        "path",
        "sha256",
        "required_manifest_schema",
        "required_check_report_schema",
        "non_claim",
    }
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_KEYS = frozenset(
    {
        "schema",
        "checker",
        "path",
        "sha256",
        "mode",
        "required_report_schema",
        "non_claim",
    }
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_TRUE_FLAGS = (
    "ready",
    "approved_runtime_evidence_present",
    "runtime_evidence_ready",
    "strict_lifecycle_triplet_selected",
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_FALSE_FLAGS = (
    "promotion_ready",
    "public_header_allowed",
    "public_header_ready",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "public_readiness",
    "runtime_ready",
    "runtime_readiness",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "complete_sdk_allowed",
    "complete_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_ready",
    "v1_completion_ready",
    "v1_completion_evidence",
    "public_sdk_v1_completion_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "partial_start_end_present",
    "missing_strict_rejected_start",
)
STRICT_APPROVED_RUNTIME_CHECK_REPORT_EMPTY_LISTS = (
    "remaining_blockers",
    "blockers",
    "blocker_details",
    "missing_lifecycle_event_roles",
    "non_evidence_reasons",
    "artifact_path_issues",
    "public_capability_bits_now",
    "public_callback_abi_now",
)
STRICT_LIFECYCLE_REQUIRED_ROLES = (
    "session_start",
    "session_start_rejected",
    "session_end",
)
PARTIAL_HASH_KEY_RE = re.compile(
    r"(?:sha(?:256)?|hash|digest|checksum).*(?:prefix|partial|short)|"
    r"(?:prefix|partial|short).*(?:sha(?:256)?|hash|digest|checksum)",
    re.IGNORECASE,
)
NON_COUNTING_SOURCE_ARTIFACT_RE = re.compile(
    r"(?:notice|notice[-_ ]?prep|beta[-_ ]?notice|closure|closure[-_ ]?request|closure[-_ ]?report|"
    r"executor|executor[-_ ]?report|window[-_ ]?request|window[-_ ]?manifest|"
    r"post[-_ ]?runtime[-_ ]?bridge(?:[-_ ]?(?:build|builder|report|artifact|manifest))?|"
    r"bridge[-_ ]?(?:build|builder)[-_ ]?report|shutdown[-_ ]?worker|worker[-_ ]?shutdown|"
    r"shutdown[-_ ]?(?:report|artifact|manifest)|"
    r"runtime[-_ ]?window(?:[-_ ]?(?:plan|planning|request|manifest|execution|executor|status|receipt|sidecar))?|"
    r"operator[-_ ]?approval|preflight|receipt|sidecar|status[-_ ]?(?:report|json)|status\.json|"
    r"installed[-_ ]?runtime[-_ ]?(?:status[-_ ]?)?checks?|"
    r"(?:broadcast|rcon)[-_ ]?status(?:[-_ ]?(?:checks?|reports?|artifacts?))?|"
    r"(?:principal|player)[-_ ]?start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:runtime[-_ ]?)?lifecycle[-_ ]?start[-_ ]?end[-_ ]?(?:evidence|artifact|report|manifest|bundle)?|"
    r"start[-_ ]?end[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"(?:start|end)[-_ ]?only[-_ ]?(?:runtime[-_ ]?)?(?:evidence|artifact|report|manifest|bundle)?|"
    r"diagnostic|passive|no[-_ ]?(?:users?|players?)|zero[-_ ]?players?|empty[-_ ]?server|"
    r"(?:runtime|player)[-_ ]?presence|presence[-_ ]?(?:snapshot|monitor|status|log)|"
    r"passive[-_ ]?monitor|extended[-_ ]?(?:passive[-_ ]?)?monitor|monitor[-_ ]?(?:snapshot|log)|"
    r"snapshot|approved[-_ ]?(?:alias|manifest)|approval[-_ ]?alias|"
    r"scoped[-_ ]?statement|release[-_ ]?statement|"
    r"certificate|simulation|simulated|"
    r"synthetic|mock|fixture|partial[-_ ]?runtime|runtime[-_ ]?partial|copied[-_ ]?log[-_ ]?only|"
    r"copied[-_ ]?runtime[-_ ]?(?:partial|fixture|mock)|truncated|incomplete|cmake[-_ ]?package|find[-_ ]?package|"
    r"(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?(?:[-_ ]?(?:total[-_ ]?flag[-_ ]?count|"
    r"component[-_ ]?count|summary|diagnostics?|zero))?|"
    r"(?:ready|accepted|complete|completed)[-_ ]?(?:alias|shortcut|artifact|manifest)|"
    r"historical[-_ ]?handoff|handoff[-_ ]?(?:text|note|notes|artifact|context|report)|"
    r"compact[-_ ]?context|checkpoint|"
    r"package[-_ ]?shape|support[-_ ]?package|package[-_ ]?support|package[-_ ]?alias|"
    r"support[-_ ]?alias|installed[-_ ]?sdk|plugin[-_ ]?hub|support[-_ ]?tier|release[-_ ]?support)",
    re.IGNORECASE,
)
PUBLIC_SHORTCUT_SOURCE_ARTIFACT_RE = re.compile(
    r"(?:public[-_ ]?header(?:[-_ ]?(?:gate|proposal|shortcut|artifact))?|public[-_ ]?api|"
    r"public[-_ ]?abi(?:[-_ ]?(?:promotion|shortcut|artifact))?|public[-_ ]?sdk[-_ ]?readiness|"
    r"runtime[-_ ]?readiness)",
    re.IGNORECASE,
)
FORBIDDEN_ROUTE_BLOCKER_VALUES = {
    "public_header_gate_missing",
    "public_header_ready",
    "public_api_gate_missing",
    "public_api_ready",
    "public_abi_gate_missing",
    "public_abi_ready",
    "public_sdk_ready",
    "public_sdk_readiness",
    "runtime_ready",
    "runtime_readiness",
    "v1_completion_ready",
    "v1_completion_evidence",
}
REQUIRED_TOP_LEVEL_NON_CLAIMS = {
    "This record does not add public header symbols.",
    "This record does not promote obelisk.player_identity.v1.",
    "This record does not treat accepted runtime evidence as a reviewed public identity contract.",
    "This record does not expose player lookup.",
    "This record does not promote permissions/admin.",
    "This record does not promote command/chat response or commands/replies.",
    "This record does not treat runtime-window planning, beta notices, package-shape/support-tier artifacts, no-users status, passive/runtime-presence artifacts, or generic approval aliases as public contract progress.",
    "This record does not authorize storage, persistence, mutation, return override, runtime readiness, SDK readiness, or v1 completion.",
    "This record does not authorize live operations, runtime capture, live-log reads, marker/env changes, or workspace writes.",
}
REQUIRED_DECISION_NON_CLAIMS = {
    "contract review only",
    "no public header symbols",
    "no lookup, persistence, permissions, commands, mutation, or return override",
}
ALIAS_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
ZERO_PROGRESS_VALUE_RE = re.compile(
    r"^\s*(?:0+(?:\.0+)?|0+\s*/\s*[1-9]\d*|0+(?:\.0+)?\s*(?:%|percent))\s*$",
    re.IGNORECASE,
)
EXPLICIT_FALSE_SUFFIX_RE = re.compile(
    r"\s*(?:=|:)\s*(?:false|0+(?:\.0+)?|0+\s*/\s*[1-9]\d*|0+(?:\.0+)?\s*(?:%|percent))\b",
    re.IGNORECASE,
)
EXPLICIT_TRUE_SUFFIX_RE = re.compile(r"\s*(?:=|:)\s*(?:true|1|yes)\b", re.IGNORECASE)
BROAD_STRING_ALIASES_REQUIRE_TRUE = frozenset({"ready", "promoted"})
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"excludes?|exclusion|without|until|missing|blocked|blocker|unavailable|required[_ -]?before|"
    r"must[_ -]?not|no_)\b",
    re.IGNORECASE,
)
PUBLIC_TEXT_OVERCLAIM_PATTERNS = {
    "public_header_ready": re.compile(
        r"\bpublic[-_ ]+header(?:[-_ ]+symbols?)?\s+(?:is\s+|are\s+)?"
        r"(?:allowed|available|ready|exposed|promoted|enabled|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_capability_available": re.compile(
        r"\b(?:OBELISK_API_CAPABILITY_[A-Z0-9_]*"
        r"(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET|AUTH|AUTHZ|ACCESS_CONTROL|ACL|"
        r"ROLE|PRIVILEGE|MODERATION|BAN|KICK|RESOURCE|OBJECT)[A-Z0-9_]*|"
        r"(?:public[-_ ]+)?(?:identity[-_ ]+|principal[-_ ]+)?capability(?:[-_ ]+bits?)?)\b"
        r"[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_callback_abi": re.compile(
        r"\b(?:public[-_ ]+)?callback[-_ ]+abi\s+(?:is\s+)?"
        r"(?:available|ready|exposed|promoted|enabled|supported)",
        re.IGNORECASE,
    ),
    "public_sdk_ready": re.compile(
        r"\bpublic[-_ ]+sdk\s+(?:is\s+)?(?:ready|available|promoted|enabled|complete|supported)",
        re.IGNORECASE,
    ),
    "public_api_ready": re.compile(
        r"\bpublic[-_ ]+api\s+(?:is\s+)?"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "runtime_ready": re.compile(
        r"\bruntime\s+(?:is\s+)?(?:ready|enabled|authorized|available|promoted|supported)",
        re.IGNORECASE,
    ),
    "stable_claim_ready": re.compile(
        r"\bstable(?:[-_ ]+(?:sdk|public[-_ ]+sdk|claims?|claim))?\s+"
        r"(?:is\s+|are\s+)?(?:allowed|available|ready|enabled|promoted|complete|supported|claimed)",
        re.IGNORECASE,
    ),
    "promotion_ready": re.compile(
        r"\bpromotion\s+(?:is\s+)?(?:ready|authorized|complete|available)",
        re.IGNORECASE,
    ),
    "v1_completion_ready": re.compile(
        r"\bv1(?:[-_ ]+sdk)?[-_ ]+completion\s+(?:is\s+)?(?:ready|complete|available|promoted)",
        re.IGNORECASE,
    ),
    "sdk_p0_progress": re.compile(
        r"\b(?:sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|complete[/ _-]*sdk)"
        r"[/ _-]*(?:progress|completion|readiness|credit|counting)?\b[^\.;\n]{0,80}\b"
        r"(?:progress|ready|complete|available|enabled|promoted|supported|counts?|credited|satisfied)",
        re.IGNORECASE,
    ),
    "public_contract_ready": re.compile(
        r"\bpublic[-_ ]+contract\s+(?:is\s+)?(?:allowed|ready|available|promoted|enabled|complete)",
        re.IGNORECASE,
    ),
    "support_tier_ready": re.compile(
        r"\bsupport[-_ ]+tier(?:[-_ ]+activation)?\s+(?:is\s+)?"
        r"(?:allowed|available|ready|enabled|activated|promoted|supported)",
        re.IGNORECASE,
    ),
    "plugin_hub_ready": re.compile(
        r"\b(?:plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:readiness|publication|package|support))?"
        r"\s+(?:is\s+)?(?:allowed|available|ready|enabled|published|promoted|released|supported)",
        re.IGNORECASE,
    ),
    "package_shape_readiness": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b"
        r"(?:(?!\bor\b)[^\.;]){0,80}\b(?:allowed|available|complete|enabled|open(?:ed|s)?|promoted|"
        r"ready|supported|unlocked|counts?|claim(?:ed)?)\b|"
        r"\binstalled[-_ ]+sdk\s+(?:is\s+|are\s+|now\s+)?"
        r"(?:allowed|available|complete|enabled|promoted|ready|supported|unlocked)\b|"
        r"\b(?:allowed|available|complete|enabled|open(?:ed|s)?|promoted|ready|supported|"
        r"unlocked|counts?|claim(?:ed)?)\s+"
        r"(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b",
        re.IGNORECASE,
    ),
    "non_counting_artifact_public_readiness_or_p0": re.compile(
        r"\b(?:runtime[-_ ]+window(?:[-_ ]+(?:plan|planning|request|manifest|execution|executor|status|receipt|sidecar))?|"
        r"runtime[-_ ]+window|beta[-_ ]+notice(?:[-_ ]+json)?|confirmed[-_ ]+beta[-_ ]+notice(?:[-_ ]+json)?|"
        r"package[-_ ]+shape|installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|support[-_ ]+tier(?:[-_ ]+activation)?|"
        r"(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?(?:[-_ ]+(?:total[-_ ]+flag[-_ ]+count|"
        r"component[-_ ]+count|summary|diagnostics?|zero))?|source[-_ ]?overclaim[-_ ]?zero|"
        r"no[-_ ]+(?:users?|players?)(?:[-_ ]+(?:status|report|snapshot|artifact))?|zero[-_ ]+players?|empty[-_ ]+server|"
        r"(?:runtime|player)[-_ ]+presence(?:[-_ ]+(?:status|report|snapshot|artifact|monitor|log))?|"
        r"presence[-_ ]+(?:snapshot|monitor|status|report|log)|"
        r"(?:principal|player)[-_ ]+start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:runtime[-_ ]+)?lifecycle[-_ ]+start[-_ ]+end(?:[-_ ]+(?:evidence|artifact|report|manifest|bundle))?|"
        r"start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:start|end)[-_ ]+only(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"post[-_ ]+reboot(?:[-_ ]+(?:passive[-_ ]+monitor|context|snapshot|log|artifact|report))?|"
        r"(?:post[-_ ]+reboot[-_ ]+)?passive[-_ ]+monitor(?:[-_ ]+context)?|"
        r"next[-_ ]+actions?(?:[-_ ]+(?:plan|status|report|artifact))?|"
        r"(?:route|runtime|evidence|identity|lifecycle|public|sdk)[-_ ]+status"
        r"(?:[-_ ]+(?:report|artifact|manifest|notice|snapshot))?|"
        r"installed[-_ ]+runtime[-_ ]+(?:status[-_ ]+)?checks?|"
        r"(?:broadcast|rcon)[-_ ]+status(?:[-_ ]+(?:checks?|reports?|artifacts?))?|"
        r"copied[-_ ]+log[-_ ]+only(?:[-_ ]+(?:artifact|evidence|manifest|report|shortcut))?)\b"
        r"[^.;\n]{0,120}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?|promotes?|approv(?:es|ed)?|"
        r"validates?|ready|readiness|complete|progress)\b[^.;\n]{0,120}\b"
        r"(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"dependency[-_ ]+chain|complete[-_ ]+sdk|runtime[-_ ]+readiness|v1[-_ ]+completion|"
        r"obelisk\.player_identity\.v1)?",
        re.IGNORECASE,
    ),
    "promotion_like_public_contract_evidence": re.compile(
        r"\b(?:reviewed[-_ ]+identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?|"
        r"hash[-_ ]+current[-_ ]+contract[-_ ]+review(?:[-_ ]+only)?)\b[^\.;]{0,100}\b"
        r"(?:evidence|proof|basis|sufficient|certif(?:ies|y|ied)|approv(?:es|ed)|validat(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|green[-_ ]?light(?:s|ed))\b[^\.;]{0,100}\b"
        r"(?:public[-_ ]+contract|public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|public[-_ ]+sdk|"
        r"obelisk\.player_identity\.v1|promotion|readiness|runtime[-_ ]+readiness|v1[-_ ]+completion)",
        re.IGNORECASE,
    ),
    "contract_review_metadata_public_readiness": re.compile(
        r"\b(?:reviewed[-_ ]+hash[-_ ]+current[-_ ]+contract[-_ ]+review[-_ ]+only|"
        r"hash[-_ ]+current[-_ ]+(?:identity[-_ ]+)?(?:public[-_ ]+)?contract[-_ ]+"
        r"(?:decision[-_ ]+)?record|contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record)\b[^\.;]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
    "contract_review_artifact_p0_unlock": re.compile(
        r"\b(?:(?:accepted|approved)[-_ ]+runtime(?:[-_ ]+(?:principal[-_ ]+)?lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?|"
        r"public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|header[-_ ]+shape)\b"
        r"[^\.;]{0,100}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?)\b[^\.;]{0,100}\b"
        r"(?:sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"dependency[-_ ]+chain|complete[-_ ]+sdk[-_ ]+(?:progress|claim)|downstream[-_ ]+p0)\b",
        re.IGNORECASE,
    ),
    "post_runtime_route_shortcut": re.compile(
        r"\b(?:after[-_ ]+)?(?:(?:accepted|approved)(?:[-_ ]+approved)?[-_ ]+runtime"
        r"(?:[-_ ]+(?:principal[-_ ]+)?lifecycle)?[-_ ]+(?:evidence|bundle)|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|"
        r"approved[-_ ]+runtime[-_ ]+principal[-_ ]+lifecycle[-_ ]+bundle)\b"
        r"[^.;\n]{0,120}\b(?:advance[sd]?|route[sd]?|next[-_ ]+blocker|unlocks?|"
        r"opens?|allows?|enables?|marks?|sets?|resolves?|satisf(?:ies|y)|complete[sd]?)\b"
        r"[^.;\n]{0,120}\b(?:public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|"
        r"public[-_ ]+sdk|public[-_ ]+readiness|runtime[-_ ]+readiness|"
        r"permissions?[/ _-]?admin|permissions?|admin|command[/ _-]?chat[-_ ]+response|"
        r"command[-_ ]+response|commands?[/ _-]?replies|commands?|complete[-_ ]+sdk|"
        r"plugin[-_ ]+hub|pluginhub|package[-_ ]+shape|support[-_ ]+tier|broadcasts?|"
        r"rcon(?:[-_ ]+commands?)?|v1[-_ ]+completion|sdk[/ _-]*p0|"
        r"p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"downstream[-_ ]+p0|public_header_gate_missing|public_api_gate_missing|"
        r"public_abi_gate_missing|permissions_admin|command_chat_response|commands_replies)\b",
        re.IGNORECASE,
    ),
    "public_identity_promotion_wording": re.compile(
        r"\b(?:promot(?:e|es|ed|ion)|publish(?:es|ed)?|ship(?:s|ped)?|release(?:s|d)?|"
        r"graduate(?:s|d)?|green[-_ ]?light(?:s|ed)?|clear(?:s|ed)?|unblock(?:s|ed)?|"
        r"certif(?:ies|y|ied)|approv(?:es|ed)|validat(?:es|ed))\b[^\.;]{0,100}\b"
        r"(?:obelisk\.player_identity\.v1|public[-_ ]+identity|public[-_ ]+principal|"
        r"public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|public[-_ ]+sdk|"
        r"public[-_ ]+contract|capability[-_ ]+bits?|callback[-_ ]+abi|runtime[-_ ]+readiness|"
        r"permissions?[/ _-]?admin|command[/ _-]?chat|commands?[/ _-]?replies|v1[-_ ]+completion)",
        re.IGNORECASE,
    ),
    "public_player_header_symbol_available": re.compile(
        r"\b(?:"
        r"Obelisk[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*|"
        r"Register[A-Za-z0-9_]*(?:Player|Identity|Principal|SteamId|SteamID|EOS|UniqueNet)[A-Za-z0-9_]*"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_lookup_or_resource_handle_available": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*Resource(?:Handle|Id|ID|Ref|Reference|Token)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*Object(?:Handle|Id|ID|Identity|Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal|Resource|Object)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:player|identity|principal|resource|object)[-_ ]+"
        r"(?:lookup|resolver|resolve|resource[-_ ]+(?:handle|id|ref|reference|token)|object[-_ ]+handle)s?"
        r")\b[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_abi_identity_handle_before_resource_handle": re.compile(
        r"\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b[^\.;]{0,120}\b"
        r"(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^\.;]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^\.;]{0,80}\bResourceHandle\b|"
        r"\b(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^\.;]{0,120}\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b"
        r"[^\.;]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^\.;]{0,80}\bResourceHandle\b",
        re.IGNORECASE,
    ),
    "broad_identity_lookup_wording": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:public[-_ ]+)?(?:player|identity|principal)[-_ ]+(?:lookup|resolver|resolve|resolution)"
        r"(?:[-_ ]+(?:api|surface|contract|handle|path|symbol|function|capability|support|route))?"
        r")\b",
        re.IGNORECASE,
    ),
    "mutation_allowed": re.compile(
        r"\bmutation\s+(?:is\s+)?"
        r"(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "public_mutable_resource_available": re.compile(
        r"\b(?:mutable|mutating|writable|writeable)\s+(?:identity|principal|player[-_ ]+identity|resource)"
        r"[^\.;]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)|"
        r"\b(?:identity|principal|player[-_ ]+identity|resource)[-_ ]+mutation\b"
        r"[^\.;]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "header_shape_public_readiness_shortcut": re.compile(
        r"\b(?:header[-_ ]+shape|public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?)\b[^\.;]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
    "return_override_allowed": re.compile(
        r"\breturn[-_ ]?override\s+(?:is\s+)?"
        r"(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "permissions_admin_ready": re.compile(
        r"\b(?:permissions?[/ _-]?admin|permissions?|permission[-_ ]+query|"
        r"permission[-_ ]+cache|authz?|access[-_ ]+control|acl|roles?|privileges?|"
        r"moderation|moderator|ban|kick|admin[-_ ]+mutation|admin)\b"
        r"[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "commands_ready": re.compile(
        r"\b(?:command[/ _-]?chat[-_ ]+response|commands?[/ _-]?replies|"
        r"command[-_ ]+response|command[-_ ]+router|send[-_ ]+chat|broadcasts?|"
        r"rcon(?:[-_ ]+commands?)?|commands?)\b"
        r"[^\.;]{0,80}\b(?:allowed|available|ready|enabled|exposed|promoted|unlocked|supported)",
        re.IGNORECASE,
    ),
    "contract_review_artifact_downstream_unlocked": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?)\b[^\.;]{0,100}\b"
        r"(?:promotes?|unlocks?|opens?|allows?|enables?|satisf(?:ies|y)|resolves?|counts?)\b"
        r"[^\.;]{0,100}\b(?:permissions?[/ _-]?admin|permissions?|admin|"
        r"command[/ _-]?chat[-_ ]+response|commands?[/ _-]?replies|commands?|"
        r"send[-_ ]+chat|broadcasts?|rcon(?:[-_ ]+commands?)?)",
        re.IGNORECASE,
    ),
    "contract_review_artifact_public_header": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review(?:[-_ ]+only)?[-_ ]+artifacts?)\b[^\.;]{0,100}\b"
        r"(?:promotes?|unlocks?|opens?|allows?|enables?|satisf(?:ies|y)|resolves?|counts?)\b"
        r"(?:[^\.;]{0,100}\b(?:public[-_ ]+header|public[-_ ]+abi|public[-_ ]+sdk|"
        r"capability[-_ ]+bits?|callback[-_ ]+abi|obelisk\.player_identity\.v1|"
        r"v1[-_ ]+completion|readiness|promotion))?",
        re.IGNORECASE,
    ),
    "runtime_evidence_public_shortcut": re.compile(
        r"\b(?:(?:accepted|approved)[-_ ]+runtime(?:[-_ ]+(?:principal[-_ ]+)?lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence)\b[^\.;]{0,100}\b"
        r"(?:advance[sd]?|route[sd]?|next[-_ ]+blocker|unlocks?|opens?|allows?|enables?)\b"
        r"[^\.;]{0,100}\b(?:public[-_ ]+header|public[-_ ]+api|public[-_ ]+abi|public[-_ ]+sdk|"
        r"runtime[-_ ]+readiness|public_header_gate_missing|public_api_gate_missing|"
        r"public_abi_gate_missing|v1[-_ ]+completion|sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|"
        r"phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|downstream[-_ ]+p0)",
        re.IGNORECASE,
    ),
    "public_route_blocker_shortcut": re.compile(
        r"\b(?:next[-_ ]+blocker|current[-_ ]+blocker|route|active[-_ ]+after)\b"
        r"[^\.;]{0,100}\b(?:public_header_gate_missing|public_api_gate_missing|"
        r"public_abi_gate_missing|public[-_ ]+sdk[-_ ]+readiness|runtime[-_ ]+readiness)",
        re.IGNORECASE,
    ),
}
FORBIDDEN_CHAIN_POSITION_KEYS = frozenset(
    {
        "v1_dependency_chain_position",
        "required_by_v1_dependency_chain_position",
        "dependency_chain_position",
        "surface_dependency_chain_position",
        "public_sdk_dependency_chain_position",
        "p0_dependency_chain_position",
    }
)
BLOCKER_ID_EXPECTATIONS = {
    "current_blocker": CURRENT_ROUTE,
    "current_blocker_id": CURRENT_ROUTE,
    "blocker_id": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "next_blocker_id": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
    "after_accepted_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
}
ROUTE_SHORTCUT_METADATA_KEYS = frozenset(
    {
        "accepted_route",
        "accepted_runtime_route",
        "accepted_runtime_evidence_route",
        "accepted_runtime_lifecycle_evidence_route",
        "approved_runtime_route",
        "approved_runtime_evidence_route",
        "approved_runtime_lifecycle_evidence_route",
        "runtime_evidence_route",
        "runtime_lifecycle_evidence_route",
        "post_runtime_evidence_route",
        "post_approved_runtime_evidence_route",
        "after_runtime_evidence_route",
        "after_accepted_runtime_evidence_route",
        "accepted_next_blocker",
        "accepted_runtime_next_blocker",
        "accepted_runtime_evidence_next_blocker",
        "accepted_runtime_lifecycle_evidence_next_blocker",
        "approved_runtime_evidence_next_blocker",
        "runtime_evidence_next_blocker",
        "runtime_lifecycle_evidence_next_blocker",
        "post_runtime_evidence_next_blocker_alias",
    }
)
ROUTE_SHORTCUT_ALLOWED_VALUES = frozenset(
    {
        NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        REVIEW_ROUTE,
        "reviewed_hash_current_contract_review_only",
    }
)
REVIEWED_HASH_CURRENT_CONTRACT_REVIEW_SHORTCUT_KEYS = frozenset(
    {
        "reviewed_hash_current_contract_review_only",
        "hash_current_contract_review_only",
        "hash_current_identity_contract_review_only",
        "hash_current_identity_public_contract_review_only",
    }
)
PROPOSED_HEADER_SYMBOL_KEYS = frozenset(
    {
        "proposed_header_symbols",
        "proposed_public_header_symbols",
        "proposed_symbols",
        "header_gate_proposed_symbols",
        "header_gate_proposal_symbols",
        "public_header_gate_proposed_symbols",
        "stale_proposed_header_symbols",
    }
)
STALE_PROPOSED_HEADER_SYMBOL_RE = re.compile(
    r"\b(?:"
    r"OBELISK_API_CAPABILITY_PLAYER_(?:IDENTITY|SESSION|LIFECYCLE|LOGIN|LOGOUT)|"
    r"OBELISK_PLAYER_IDENTITY_[A-Z0-9_]*|"
    r"ObeliskPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"ObeliskPlayer(?:Id|ID|Handle)\b|"
    r"RegisterPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"UnregisterPlayer(?:Identity|Session|Lifecycle|Login|Logout|Connect|Disconnect|Join|Leave)[A-Za-z0-9_]*|"
    r"DescribePlayer(?:Identity|Session|Lifecycle)[A-Za-z0-9_]*"
    r")\b"
)


def normalized_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalized_claim_key(value: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


CLAIM_ALIAS_KEYS = frozenset(
    normalized_alias(alias)
    for alias in FALSE_FLAGS + OPTIONAL_FALSE_ALIAS_FLAGS + CLAIM_ALIAS_EXTRA_KEYS
)
UNEXPECTED_CLAIM_ALIAS_KEY_RE = re.compile(
    r"(?:"
    r"public.*(?:ready|readiness|allowed|promot|sdk|api|abi|header|callback|capability|unlocked|open|clear|resolved|satisfied|accepted)|"
    r"identity.*contract.*gate.*(?:ready|reviewed|unlocked|open|clear|resolved|satisfied|accepted)|"
    r"runtime.*(?:ready|readiness|allowed|promot|sdk|stable|unlocked|open|clear|resolved)|"
    r"stable.*(?:ready|readiness|allowed|claim|promot|public|runtime|open|clear|resolved)|"
    r"v1.*(?:ready|completion|sdk|claim)|"
    r"(?:p0|phase[-_ ]?0|sdk.*p0|complete.*sdk).*(?:progress|credit|completion|ready|count)|"
    r"(?:progress|credit|completion|ready|count).*(?:p0|phase[-_ ]?0|sdk.*p0|complete.*sdk)|"
    r"(?:permissions?|authz?|access[_ -]?control|acl|roles?|privileges?|moderation|ban|kick)"
    r".*(?:ready|allowed|unlocked|public)|"
    r"(?:commands?|broadcast|rcon).*(?:ready|allowed|unlocked|replies|response)|"
    r"lookup.*(?:ready|allowed|supported|public)|"
    r"resource.*(?:handle|id|ref|reference|token).*(?:ready|allowed|supported)|"
    r"object.*handle.*(?:ready|allowed|supported)|"
    r"(?:ready|readiness|promoted|promotion[-_ ]?allowed|counts?[-_ ]?(?:towards?|as).*(?:sdk|public|runtime|v1))"
    r")",
    re.IGNORECASE,
)
BROAD_STANDALONE_CLAIM_KEYS = frozenset(
    {
        "public",
        "runtime",
        "stable",
        "ready",
        "readiness",
        "accepted",
        "approved",
        "approval",
        "complete",
        "completed",
        "promoted",
    }
)
SPLIT_CLAIM_NAME_KEYS = frozenset(
    {
        "alias",
        "aliases",
        "claim",
        "claims",
        "field",
        "fields",
        "flag",
        "flags",
        "key",
        "keys",
        "name",
        "names",
        "progress",
        "progresses",
        "property",
        "properties",
        "ratio",
        "ratios",
    }
)
SPLIT_CLAIM_VALUE_KEYS = frozenset(
    {
        "accepted",
        "approved",
        "allowed",
        "approval",
        "authorization",
        "authorized",
        "complete",
        "completed",
        "current",
        "enabled",
        "readiness",
        "ready",
        "reviewed",
        "state",
        "states",
        "status",
        "statuses",
        "unlocked",
        "value",
        "values",
    }
)
NON_PROMOTIONAL_CLAIM_VALUE_TOKENS = frozenset(
    {
        "",
        "blocked",
        "empty",
        "false",
        "missing",
        "no",
        "none",
        "not_available",
        "proposal_only",
        "proposal_only_not_public",
        "unavailable",
        "unresolved",
    }
)
POSITIVE_CLAIM_VALUE_TOKENS = frozenset(
    {
        "accepted",
        "allowed",
        "approved",
        "authorized",
        "available",
        "complete",
        "current",
        "enabled",
        "exposed",
        "granted",
        "live",
        "operational",
        "passed",
        "passing",
        "promoted",
        "public",
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
NON_FALSE_CLAIM_ALIAS_KEYS = frozenset(
    {
        "blocker_resolved",
        "p0_unlocked",
        "approved_runtime_principal_lifecycle_bundle_next_blocker",
        "approved_runtime_principal_lifecycle_bundle_routes_to",
        "approved_runtime_lifecycle_bundle_next_blocker",
        "approved_runtime_lifecycle_bundle_routes_to",
        "approved_runtime_evidence_next_blocker",
        "approved_runtime_evidence_routes_to",
        "runtime_lifecycle_evidence_next_blocker",
        "runtime_lifecycle_evidence_routes_to",
    }
)
SPLIT_CLAIM_FALSE_KEYS = frozenset(
    normalized_claim_key(alias)
    for alias in FALSE_FLAGS + OPTIONAL_FALSE_ALIAS_FLAGS + CLAIM_ALIAS_EXTRA_KEYS
) | frozenset(
    {
        "contract_review_only",
        "contract_record_current",
        "contract_record_contract_review_only",
        "contract_record_reviewed",
        "contract_review_current",
        "header_shape_valid",
        "hash_current_identity_contract_decision_record",
        "hash_current_identity_public_contract_decision_record",
        "identity_contract_hash_current",
        "identity_contract_decision_record_hash_current",
        "identity_contract_decision_record_reviewed",
        "identity_public_contract_decision_record_hash_current",
        "identity_public_contract_decision_record_reviewed",
        "public_header_gate_reviewed",
        "public_api_gate_reviewed",
        "public_abi_gate_reviewed",
        "reviewed_identity_contract_decision_record",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_decision_record",
        "blocker_resolved",
        "counts_toward_p0",
        "counts_toward_p0_dependency_chain",
        "counts_toward_p0_dependency_chain_claim",
        "counts_toward_phase0",
        "p0_progress",
        "p0_progress_ready",
        "p0_ready",
        "p0_unlocked",
        "p0_sdk_progress",
        "p0_sdk_progress_ready",
        "sdk_p0_progress",
        "sdk_p0_progress_ready",
        "sdk_p0_ready",
        "claim_progress",
        "claim_progress_contribution",
        "complete_sdk_progress",
        "complete_sdk_progress_contribution",
        "complete_sdk_claim_progress_contribution",
        "p0_dependency_chain_progress_contribution",
        "p0_dependency_chain_claim_progress_contribution",
        "progress",
        "progress_contribution",
        "progress_percent",
        "progress_ratio",
        "public_sdk_progress_contribution",
        "runtime_progress_contribution",
    }
)
SPLIT_CLAIM_PUBLIC_LIST_KEYS = frozenset(normalized_claim_key(key) for key in EMPTY_PUBLIC_LISTS)
SPLIT_CLAIM_SUBJECT_KEYS = frozenset(
    {
        "command_response",
        "command_chat_response",
        "commands_replies",
        "broadcast",
        "broadcast_reply",
        "chat_reply",
        "chat_replies",
        "complete_sdk",
        "identity_contract_decision_record",
        "identity_contract_gate",
        "identity_public_contract",
        "identity_public_contract_decision_record",
        "identity_public_contract_gate",
        "lookup",
        "access_control",
        "acl",
        "auth",
        "authz",
        "ban",
        "kick",
        "moderation",
        "permissions",
        "permissions_admin",
        "privilege",
        "privileges",
        "public",
        "public_abi",
        "public_abi_gate",
        "public_api",
        "public_api_gate",
        "public_callback_abi",
        "public_contract",
        "public_header",
        "public_header_gate",
        "public_identity",
        "public_principal",
        "public_surface",
        "public_sdk",
        "p0",
        "p0_dependency_chain",
        "rcon",
        "rcon_command",
        "rcon_reply",
        "resource_handle",
        "resource_id",
        "resource_ref",
        "resource_reference",
        "object_handle",
        "role",
        "roles",
        "runtime",
        "runtime_capture",
        "runtime_readiness",
        "runtime_work",
        "sdk",
        "sdk_p0",
        "stable",
        "stable_claim",
        "stable_sdk",
        "v1",
        "v1_completion",
    }
)
DECISION_RECORD_METADATA_CONTEXT_KEYS = frozenset(
    {
        "hash_current_identity_contract_decision_record",
        "hash_current_identity_public_contract_decision_record",
        "identity_contract_decision_record",
        "identity_public_contract_decision_record",
        "identity_public_contract_record",
        "public_contract_decision_record",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_contract_decision_record",
        "reviewed_identity_public_contract",
        "reviewed_identity_public_contract_decision_record",
        "review_metadata",
    }
)
DECISION_RECORD_METADATA_STATUS_KEYS = frozenset(
    {
        "decision_scope",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "record_valid_scope",
        "review_status",
        "reviewed_hash_current_contract_review_only",
        "scope",
        "source_artifact_hash_state",
        "state",
        "status",
    }
)
DECISION_RECORD_METADATA_REVIEWED_VALUES = frozenset(
    {
        "reviewed",
        "reviewed_hash_current_contract_review_only",
    }
)
DECISION_RECORD_METADATA_HASH_CURRENT_VALUES = frozenset(
    {
        "current",
        "hash_bound_to_current_source_artifacts",
        "hash_current",
        "reviewed_hash_current_contract_review_only",
    }
)
DECISION_RECORD_METADATA_SCOPE_VALUES = frozenset(
    {
        "contract_review_only",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_public_contract_record_only",
    }
)
DECISION_RECORD_METADATA_PROGRESS_ALIAS_KEYS = frozenset(
    {
        "completion_credit",
        "contribution",
        "credit",
        "credits",
        "p0",
        "p0_credit",
        "p0_progress_credit",
        "p0_sdk",
        "percent",
        "percentage",
        "phase0",
        "phase_0",
        "progress_credit",
        "public_sdk_credit",
        "ratio",
        "readiness_credit",
        "sdk_completion_credit",
        "sdk_p0",
        "sdk_p0_credit",
        "v1_completion_credit",
    }
)
DECISION_RECORD_METADATA_PROGRESS_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"credits?|readiness_credit|progress|progress_contribution|progress_percent|progress_ratio|"
    r"percent|percentage|ratio|contribution|"
    r"p0|phase_?0|sdk_p0|p0_sdk|"
    r"counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
DECISION_RECORD_METADATA_PROGRESS_VALUE_RE = re.compile(
    r"(?:^|_)(?:"
    r"credits?|progress|percent|percentage|ratio|contribution|"
    r"p0|phase_?0|sdk_p0|p0_sdk|"
    r"counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
NON_PROMOTIONAL_PROVENANCE_CONTEXT_KEYS = frozenset(
    {
        "artifact_provenance",
        "evidence_provenance",
        "metadata_provenance",
        "provenance",
        "provenance_marker",
        "provenance_markers",
        "review_provenance",
        "route_provenance",
        "snapshot_provenance",
        "source_marker",
        "source_markers",
        "source_provenance",
        "source_provenances",
    }
)
NON_PROMOTIONAL_PROVENANCE_CONTEXT_TERMS = frozenset(
    {
        "accepted_runtime_evidence",
        "approved_runtime_evidence",
        "identity_public_contract_decision_record",
        "lifecycle_start_end_evidence",
        "principal_start_end_runtime_evidence",
        "public_contract_decision_record",
        "reviewed_hash_current_contract_review_only",
        "reviewed_identity_public_contract",
        "runtime_lifecycle_start_end_evidence",
        "runtime_start_end_evidence",
        "route_snapshot",
        "start_end_runtime_evidence",
    }
)
NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS = SPLIT_CLAIM_VALUE_KEYS | frozenset(
    {
        "source_accepted",
        "source_outcome",
        "source_ready",
        "source_result",
        "source_state",
        "source_status",
        "source_supported",
    }
)
SHORTCUT_ALIAS_SKIP_PREFIXES = (
    "$.source_artifacts",
    "$.route",
    "$.route_blocker_aliases",
    f"$.{POST_RUNTIME_GATE_FIELD}",
    f"$.{CURRENTNESS_DIAGNOSTIC_FIELD}",
    f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}",
    f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}",
    f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_approved_runtime_evidence_binding_ref",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_approved_runtime_evidence_binding_state",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_approved_runtime_evidence_manifest_ref",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_approved_runtime_evidence_manifest_state",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_strict_approved_runtime_checker_contract_report_ref",
    f"$.{NEXT_STEP_CHECK_FIELD}.required_strict_approved_runtime_checker_contract_report_state",
)
STALE_HASH_CURRENT_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:stale|mismatch(?:ed)?|outdated|expired|not_current)(?:_|$).*(?:hash|source|artifact|contract|record)|"
    r"(?:hash|source|artifact|contract|record).*(?:_|^)(?:stale|mismatch(?:ed)?|outdated|expired|not_current)(?:_|$)"
)
STALE_HASH_CURRENT_ALIAS_VALUE_RE = re.compile(
    r"^(?:stale|stale_or_mismatched|mismatched|mismatch|not_current|outdated|expired)$"
)
RUNTIME_EVIDENCE_SHORTCUT_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:accepted|approved)?_?runtime(?:_principal|_lifecycle)?_?evidence(?:_|$)|"
    r"(?:^|_)(?:accepted|approved)?_?runtime(?:_principal)?_?lifecycle_?bundle(?:_|$)|"
    r"(?:^|_)(?:accepted|approved)_?runtime_?principal_?lifecycle_?bundle(?:_|$)|"
    r"(?:^|_)(?:principal_)?start_end(?:_runtime)?_evidence(?:_|$)|"
    r"(?:^|_)runtime_lifecycle_start_end_evidence(?:_|$)|"
    r"(?:^|_)runtime_evidence(?:_|$)"
)
P0_PROGRESS_SHORTCUT_ALIAS_KEY_RE = re.compile(
    r"(?:^|_)(?:p0|phase_?0|sdk_p0|p0_sdk)(?:_|$)|"
    r"(?:complete_sdk|public_sdk|sdk).*(?:p0|phase_?0|progress|credit|count)|"
    r"(?:progress|credit|count|counts?_towards?|counts?_toward).*(?:p0|phase_?0|complete_sdk|sdk)"
)
IDENTITY_CONTRACT_GATE_MISSING_TRUE_ALIAS_KEYS = frozenset(
    {
        "identity_contract_gate_missing",
        "identity_contract_gate_missing_after_runtime_evidence",
        "identity_contract_gate_missing_after_accepted_runtime_evidence",
        "identity_public_contract_gate_missing",
        "identity_public_contract_gate_missing_after_runtime_evidence",
        "identity_public_contract_gate_missing_after_accepted_runtime_evidence",
        "post_runtime_identity_contract_gate_missing",
        "post_runtime_identity_contract_gate_missing_after_runtime_evidence",
        "post_runtime_identity_contract_gate_missing_after_accepted_runtime_evidence",
        "public_identity_contract_gate_missing",
        "public_identity_contract_gate_missing_after_runtime_evidence",
        "public_identity_contract_gate_missing_after_accepted_runtime_evidence",
    }
)
DOWNSTREAM_GATE_MISSING_FALSE_ALIAS_KEYS = frozenset(
    {
        "public_header_gate_missing",
        "public_header_gate_missing_after_runtime_evidence",
        "public_header_gate_missing_after_accepted_runtime_evidence",
        "public_api_gate_missing",
        "public_api_gate_missing_after_runtime_evidence",
        "public_api_gate_missing_after_accepted_runtime_evidence",
        "public_abi_gate_missing",
        "public_abi_gate_missing_after_runtime_evidence",
        "public_abi_gate_missing_after_accepted_runtime_evidence",
        "public_sdk_readiness_after_runtime_evidence",
        "public_sdk_readiness_after_accepted_runtime_evidence",
        "runtime_readiness_after_runtime_evidence",
        "runtime_readiness_after_accepted_runtime_evidence",
        "v1_completion_after_runtime_evidence",
        "v1_completion_after_accepted_runtime_evidence",
    }
)
SOURCE_OVERCLAIM_KEY_TOKENS = (
    "source_overclaim",
    "source_overclaimed",
    "source_overclaims",
    "side_lane_source_overclaim",
)
SOURCE_OVERCLAIM_COUNT_KEYS = frozenset(
    {
        "count",
        "component_count",
        "flag_count",
        "progress_flag_count",
        "readiness_flag_count",
        "total",
        "total_flag_count",
    }
)


def is_source_overclaim_key(key_name: str) -> bool:
    return any(token in key_name for token in SOURCE_OVERCLAIM_KEY_TOKENS)


def is_source_overclaim_count_key(key_name: str) -> bool:
    return (
        key_name in SOURCE_OVERCLAIM_COUNT_KEYS
        or "source_overclaim" in key_name
        and ("count" in key_name or "zero" in key_name or "summary" in key_name)
    )


def zero_source_overclaim_count_value(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if isinstance(value, str):
        return ZERO_PROGRESS_VALUE_RE.fullmatch(value.strip()) is not None
    return False


def string_mentions_source_overclaim_zero(value: str) -> bool:
    normalized = normalized_claim_key(value)
    return is_source_overclaim_key(normalized) and (
        "zero" in normalized
        or "_0" in f"_{normalized}_"
        or ZERO_PROGRESS_VALUE_RE.search(value) is not None
    )


def source_overclaim_zero_overclaims(
    value: Any,
    label: str = "$",
    *,
    source_overclaim_context: bool = False,
) -> list[dict[str, Any]]:
    if (
        shortcut_alias_scan_skipped(label)
        or ".forbidden_source_aliases" in label
        or ".forbidden_source_classes" in label
        or ".forbidden_source_tokens" in label
        or ".source_artifact_freshness.policy" in label
    ):
        return []
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_label = f"{label}.{key}" if label != "$" else f"$.{key}"
            if not isinstance(key, str):
                claims.extend(
                    source_overclaim_zero_overclaims(
                        item,
                        item_label,
                        source_overclaim_context=source_overclaim_context,
                    )
                )
                continue
            key_name = normalized_claim_key(key)
            child_context = source_overclaim_context or is_source_overclaim_key(key_name)
            if (
                child_context
                and is_source_overclaim_count_key(key_name)
                and zero_source_overclaim_count_value(item)
            ):
                claims.append(
                    {
                        "path": item_label,
                        "term": "source_overclaim_zero_marker",
                        "value": item,
                    }
                )
            elif is_source_overclaim_key(key_name) and "zero" in key_name and shortcut_value_present(item):
                claims.append(
                    {
                        "path": item_label,
                        "term": "source_overclaim_zero_marker",
                        "value": item,
                    }
                )
            elif (
                child_context
                and key_name in NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS
                and is_positive_claim_value(item)
            ):
                claims.append(
                    {
                        "path": item_label,
                        "term": "source_overclaim_zero_status_alias",
                        "value": item,
                    }
                )
            claims.extend(
                source_overclaim_zero_overclaims(
                    item,
                    item_label,
                    source_overclaim_context=child_context,
                )
            )
        return claims
    if isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(
                source_overclaim_zero_overclaims(
                    item,
                    f"{label}[{index}]",
                    source_overclaim_context=source_overclaim_context,
                )
            )
        return claims
    if isinstance(value, str) and string_mentions_source_overclaim_zero(value):
        claims.append({"path": label, "term": "source_overclaim_zero_marker", "value": value})
    return claims


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD, help="Decision record JSON to validate.")
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument("--promote", action="store_true", help="Fail closed for promotion checks.")
    parser.add_argument("--public-readiness", action="store_true", help="Fail closed for public readiness checks.")
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


def load_record(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any] | None:
    protected_paths.reject_symlink_component(path, "--record")
    resolved = protected_paths.reject_protected_input_path(path, "--record")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        add(blockers, "decision_record_missing", "$.record", path=str(resolved))
        return None
    except json.JSONDecodeError as exc:
        add(blockers, "decision_record_invalid_json", "$.record", path=str(resolved), error=str(exc))
        return None
    if not isinstance(payload, dict):
        add(blockers, "decision_record_not_object", "$.record", path=str(resolved))
        return None
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def first_report_mismatches(
    *,
    expected: Any,
    observed: Any,
    label: str = "$",
    limit: int = 8,
) -> list[str]:
    if limit <= 0:
        return []
    if isinstance(expected, dict) and isinstance(observed, dict):
        mismatches: list[str] = []
        expected_keys = set(expected)
        observed_keys = set(observed)
        for key in sorted(expected_keys - observed_keys):
            mismatches.append(f"{label}.{key}:missing")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(observed_keys - expected_keys):
            mismatches.append(f"{label}.{key}:unexpected")
            if len(mismatches) >= limit:
                return mismatches
        for key in sorted(expected_keys & observed_keys):
            mismatches.extend(
                first_report_mismatches(
                    expected=expected[key],
                    observed=observed[key],
                    label=f"{label}.{key}",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if isinstance(expected, list) and isinstance(observed, list):
        mismatches = []
        if len(expected) != len(observed):
            mismatches.append(f"{label}:length expected={len(expected)} observed={len(observed)}")
            if len(mismatches) >= limit:
                return mismatches
        for index, (expected_item, observed_item) in enumerate(zip(expected, observed)):
            mismatches.extend(
                first_report_mismatches(
                    expected=expected_item,
                    observed=observed_item,
                    label=f"{label}[{index}]",
                    limit=limit - len(mismatches),
                )
            )
            if len(mismatches) >= limit:
                return mismatches
        return mismatches
    if expected != observed:
        return [f"{label}:value_mismatch"]
    return []


def approved_runtime_evidence_binding_from_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical reviewed-record binding for an accepted runtime evidence manifest."""
    identity = payload.get("output_artifact_identity")
    source_summary = payload.get("source_summary")
    operational_window = payload.get("operational_window")
    evidence: dict[str, Any] = {}
    source: dict[str, Any] = {}
    if isinstance(source_summary, dict):
        observed_evidence = source_summary.get("evidence")
        if isinstance(observed_evidence, dict):
            evidence = observed_evidence
            sources = observed_evidence.get("sources")
            if isinstance(sources, list) and sources and isinstance(sources[0], dict):
                source = sources[0]
    copied_log = {}
    if isinstance(operational_window, dict) and isinstance(operational_window.get("copied_log"), dict):
        copied_log = operational_window["copied_log"]
    return {
        "schema": APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
        "accepted_for_contract_review": True,
        "resolved_input": ACTIVE_AFTER_RESOLVED_INPUT,
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "artifact_kind": identity.get("artifact_kind") if isinstance(identity, dict) else None,
        "evidence_pack_id": identity.get("evidence_pack_id") if isinstance(identity, dict) else None,
        "artifact_sha256": identity.get("artifact_sha256") if isinstance(identity, dict) else None,
        "source_kind": evidence.get("kind"),
        "source_path": source.get("path"),
        "source_sha256": source.get("sha256"),
        "copied_log_path": copied_log.get("path"),
        "copied_log_sha256": copied_log.get("sha256"),
        "binding_scope": REVIEW_ROUTE,
        "public_header_api_abi_sdk_runtime_shortcut_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "v1_completion_evidence": False,
        "non_claim": APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
    }


def approved_runtime_evidence_manifest_ref(path: Path) -> dict[str, str]:
    return {
        "schema": APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_SCHEMA,
        "checker": STRICT_APPROVED_RUNTIME_CHECKER,
        "path": str(path),
        "sha256": sha256_file(path),
        "required_manifest_schema": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "required_check_report_schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "non_claim": APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_NON_CLAIM,
    }


def binding_entry_strings(value: Any, label: str = f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}") -> list[dict[str, str]]:
    strings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                strings.append({"path": f"{label}.{key}", "value": key})
            strings.extend(binding_entry_strings(item, f"{label}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            strings.extend(binding_entry_strings(item, f"{label}[{index}]"))
    elif isinstance(value, str):
        strings.append({"path": label, "value": value})
    return strings


def approved_runtime_evidence_binding_shortcut_claims(
    binding: Any,
    label: str = f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}",
) -> dict[str, list[dict[str, str]]]:
    allowed_values = {
        APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD,
        APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
        APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
        ACTIVE_AFTER_RESOLVED_INPUT,
        NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        REVIEW_ROUTE,
        APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
        *APPROVED_RUNTIME_EVIDENCE_BINDING_KEYS,
    }
    strings = binding_entry_strings(binding, label)
    return {
        "non_counting": [
            item
            for item in strings
            if item["value"] not in allowed_values and NON_COUNTING_SOURCE_ARTIFACT_RE.search(item["value"])
        ],
        "public_shortcuts": [
            item
            for item in strings
            if item["value"] not in allowed_values and PUBLIC_SHORTCUT_SOURCE_ARTIFACT_RE.search(item["value"])
        ],
    }


def resolve_strict_check_report_path(
    path_text: Any,
    blockers: list[dict[str, Any]],
    label: str,
) -> Path | None:
    if not isinstance(path_text, str) or not path_text:
        add(blockers, "strict_approved_runtime_checker_contract_report_path_missing", label, observed=path_text)
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        protected_paths.reject_symlink_component(path, label)
        return protected_paths.reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_path_rejected",
            label,
            path=path_text,
            error=str(exc),
        )
        return None


def load_strict_check_report(
    report_path: Path | None,
    expected_sha256: Any,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if report_path is None:
        return None
    try:
        report_bytes = report_path.read_bytes()
    except OSError as exc:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_unreadable",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.path",
            path=str(report_path),
            error=str(exc),
        )
        return None
    actual_sha256 = hashlib.sha256(report_bytes).hexdigest()
    if not isinstance(expected_sha256, str) or SOURCE_ARTIFACT_HASH_RE.fullmatch(expected_sha256) is None:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_sha256_invalid",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.sha256",
            observed=expected_sha256,
        )
    elif expected_sha256 != actual_sha256:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_sha256_mismatch",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.sha256",
            expected=actual_sha256,
            observed=expected_sha256,
        )
    try:
        report = json.loads(report_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_not_utf8",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.path",
            path=str(report_path),
            error=str(exc),
        )
        return None
    except json.JSONDecodeError as exc:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_invalid_json",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.path",
            path=str(report_path),
            error=str(exc),
        )
        return None
    if not isinstance(report, dict):
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_not_object",
            f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.path",
            path=str(report_path),
        )
        return None
    return report


def resolve_approved_runtime_evidence_manifest_path(
    path_text: Any,
    blockers: list[dict[str, Any]],
    label: str,
) -> Path | None:
    if not isinstance(path_text, str) or not path_text:
        add(blockers, "approved_runtime_evidence_manifest_ref_path_missing", label, observed=path_text)
        return None
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        protected_paths.reject_symlink_component(path, label)
        return protected_paths.reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_path_rejected",
            label,
            path=path_text,
            error=str(exc),
        )
        return None


def load_approved_runtime_evidence_manifest(
    manifest_path: Path | None,
    expected_sha256: Any,
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if manifest_path is None:
        return None
    try:
        manifest_bytes = manifest_path.read_bytes()
    except OSError as exc:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_unreadable",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.path",
            path=str(manifest_path),
            error=str(exc),
        )
        return None
    actual_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if not isinstance(expected_sha256, str) or SOURCE_ARTIFACT_HASH_RE.fullmatch(expected_sha256) is None:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_sha256_invalid",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.sha256",
            observed=expected_sha256,
        )
    elif expected_sha256 != actual_sha256:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_sha256_mismatch",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.sha256",
            expected=actual_sha256,
            observed=expected_sha256,
        )
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except UnicodeDecodeError as exc:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_not_utf8",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.path",
            path=str(manifest_path),
            error=str(exc),
        )
        return None
    except json.JSONDecodeError as exc:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_invalid_json",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.path",
            path=str(manifest_path),
            error=str(exc),
        )
        return None
    if not isinstance(manifest, dict):
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_not_object",
            f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}.path",
            path=str(manifest_path),
        )
        return None
    return manifest


def validate_strict_check_report_payload(report: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    label = f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}.report"
    fixed_values = {
        "schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "input_schema": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "mode": "consume",
        "ready_scope": "runtime_evidence_only",
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "current_route_blocker": None,
        "next_required_artifact": None,
        "missing_required_artifact": None,
        "required_artifact_status": "accepted",
    }
    for key, expected in fixed_values.items():
        if report.get(key) != expected:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_{key}_mismatch",
                f"{label}.{key}",
                expected=expected,
                observed=report.get(key),
            )
    for key in STRICT_APPROVED_RUNTIME_CHECK_REPORT_TRUE_FLAGS:
        if report.get(key) is not True:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_{key}_not_true",
                f"{label}.{key}",
                observed=report.get(key),
            )
    for key in STRICT_APPROVED_RUNTIME_CHECK_REPORT_FALSE_FLAGS:
        if key in report and report.get(key) is not False:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_{key}_not_false",
                f"{label}.{key}",
                observed=report.get(key),
            )
    for key in STRICT_APPROVED_RUNTIME_CHECK_REPORT_EMPTY_LISTS:
        if report.get(key) != []:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_{key}_not_empty",
                f"{label}.{key}",
                observed=report.get(key),
            )
    selection = report.get("strict_lifecycle_triplet_selection")
    if not isinstance(selection, dict):
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_strict_lifecycle_triplet_selection_missing",
            f"{label}.strict_lifecycle_triplet_selection",
            observed=selection,
        )
        return
    selection_expectations = {
        "accepted": True,
        "status": "selected",
        "candidate_count": 1,
        "selected_roles": list(STRICT_LIFECYCLE_REQUIRED_ROLES),
        "missing_roles": [],
        "blockers": [],
        "non_counting_context_event_count": 0,
        "non_counting_context_roles": [],
    }
    for key, expected in selection_expectations.items():
        if selection.get(key) != expected:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_strict_lifecycle_triplet_{key}_mismatch",
                f"{label}.strict_lifecycle_triplet_selection.{key}",
                expected=expected,
                observed=selection.get(key),
            )


def validate_strict_approved_runtime_checker_contract_report(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> dict[str, Any] | None:
    ref = payload.get(STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD)
    ref_label = f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}"
    if not isinstance(ref, dict):
        add(blockers, "strict_approved_runtime_checker_contract_report_missing_or_not_object", ref_label)
        return None
    ref_keys = set(ref)
    if ref_keys != STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_KEYS:
        add(
            blockers,
            "strict_approved_runtime_checker_contract_report_ref_keys_mismatch",
            ref_label,
            expected=sorted(STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_KEYS),
            observed=sorted(ref_keys),
        )
    fixed_values = {
        "schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_REF_SCHEMA,
        "checker": STRICT_APPROVED_RUNTIME_CHECKER,
        "mode": "consume",
        "required_report_schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "non_claim": STRICT_APPROVED_RUNTIME_CHECK_REPORT_NON_CLAIM,
    }
    for key, expected in fixed_values.items():
        if ref.get(key) != expected:
            add(
                blockers,
                f"strict_approved_runtime_checker_contract_report_ref_{key}_mismatch",
                f"{ref_label}.{key}",
                expected=expected,
                observed=ref.get(key),
            )
    report_path = resolve_strict_check_report_path(ref.get("path"), blockers, f"{ref_label}.path")
    report = load_strict_check_report(report_path, ref.get("sha256"), blockers)
    if report is not None:
        validate_strict_check_report_payload(report, blockers)
    return report


def validate_approved_runtime_evidence_manifest_ref(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    ref = payload.get(APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD)
    ref_label = f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}"
    if not isinstance(ref, dict):
        add(blockers, "approved_runtime_evidence_manifest_ref_missing_or_not_object", ref_label)
        return None, None, None
    ref_keys = set(ref)
    if ref_keys != APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_KEYS:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_keys_mismatch",
            ref_label,
            expected=sorted(APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_KEYS),
            observed=sorted(ref_keys),
        )
    fixed_values = {
        "schema": APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_SCHEMA,
        "checker": STRICT_APPROVED_RUNTIME_CHECKER,
        "required_manifest_schema": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "required_check_report_schema": STRICT_APPROVED_RUNTIME_CHECK_REPORT_SCHEMA,
        "non_claim": APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_NON_CLAIM,
    }
    for key, expected in fixed_values.items():
        if ref.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_manifest_ref_{key}_mismatch",
                f"{ref_label}.{key}",
                expected=expected,
                observed=ref.get(key),
            )
    manifest_path = resolve_approved_runtime_evidence_manifest_path(ref.get("path"), blockers, f"{ref_label}.path")
    manifest = load_approved_runtime_evidence_manifest(manifest_path, ref.get("sha256"), blockers)
    if manifest is None:
        return None, None, None
    if manifest.get("schema") != APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_schema_mismatch",
            f"{ref_label}.path.schema",
            expected=APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
            observed=manifest.get("schema"),
        )
        return manifest, None, None
    binding = approved_runtime_evidence_binding_from_manifest(manifest)
    if manifest_path is None:
        return manifest, binding, None
    try:
        validation = approved_runtime_checker.validate_manifest(
            manifest,
            check_mode="consume",
            input_path=manifest_path,
        )
        report = approved_runtime_checker.build_report(
            manifest,
            validation,
            check_mode="consume",
        )
    except SystemExit as exc:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_checker_failed",
            ref_label,
            error=str(exc),
        )
        return manifest, binding, None
    if validation.blockers:
        add(
            blockers,
            "approved_runtime_evidence_manifest_ref_not_checker_accepted",
            ref_label,
            checker_blockers=[blocker["reason"] for blocker in validation.blockers],
            blocker_details=validation.blockers[:8],
        )
        return manifest, binding, report
    return manifest, binding, report


def validate_bound_runtime_manifest_contract(
    payload: dict[str, Any],
    *,
    strict_report: dict[str, Any] | None,
    expected_binding: dict[str, Any] | None,
    expected_report: dict[str, Any] | None,
    blockers: list[dict[str, Any]],
) -> None:
    binding = payload.get(APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD)
    if expected_binding is not None and isinstance(binding, dict):
        if canonical_json(binding) != canonical_json(expected_binding):
            add(
                blockers,
                "approved_runtime_evidence_binding_manifest_mismatch",
                f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}",
                mismatches=first_report_mismatches(
                    expected=expected_binding,
                    observed=binding,
                ),
            )
    if expected_report is not None and strict_report is not None:
        if canonical_json(strict_report) != canonical_json(expected_report):
            add(
                blockers,
                "strict_approved_runtime_checker_contract_report_runtime_input_mismatch",
                f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}",
                mismatches=first_report_mismatches(
                    expected=expected_report,
                    observed=strict_report,
                ),
            )


def validate_approved_runtime_evidence_binding(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    binding = payload.get(APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD)
    binding_label = f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}"
    if not isinstance(binding, dict):
        add(blockers, "approved_runtime_evidence_binding_missing_or_not_object", binding_label)
        return
    binding_keys = set(binding)
    if binding_keys != APPROVED_RUNTIME_EVIDENCE_BINDING_KEYS:
        add(
            blockers,
            "approved_runtime_evidence_binding_keys_mismatch",
            binding_label,
            expected=sorted(APPROVED_RUNTIME_EVIDENCE_BINDING_KEYS),
            observed=sorted(binding_keys),
        )
    fixed_values = {
        "schema": APPROVED_RUNTIME_EVIDENCE_BINDING_SCHEMA,
        "accepted_for_contract_review": True,
        "resolved_input": ACTIVE_AFTER_RESOLVED_INPUT,
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "artifact_kind": APPROVED_RUNTIME_EVIDENCE_ARTIFACT_KIND,
        "source_kind": APPROVED_RUNTIME_EVIDENCE_SOURCE_KIND,
        "binding_scope": REVIEW_ROUTE,
        "non_claim": APPROVED_RUNTIME_EVIDENCE_BINDING_NON_CLAIM,
    }
    for key, expected in fixed_values.items():
        if binding.get(key) != expected:
            add(
                blockers,
                f"approved_runtime_evidence_binding_{key}_mismatch",
                f"{binding_label}.{key}",
                expected=expected,
                observed=binding.get(key),
            )
    for key in APPROVED_RUNTIME_EVIDENCE_BINDING_FALSE_FLAGS:
        if binding.get(key) is not False:
            add(
                blockers,
                f"approved_runtime_evidence_binding_{key}_not_false",
                f"{binding_label}.{key}",
                observed=binding.get(key),
            )
    for key in ("artifact_sha256", "source_sha256", "copied_log_sha256"):
        if not isinstance(binding.get(key), str) or SOURCE_ARTIFACT_HASH_RE.fullmatch(binding[key]) is None:
            add(
                blockers,
                f"approved_runtime_evidence_binding_{key}_invalid",
                f"{binding_label}.{key}",
                observed=binding.get(key),
            )
    for key in ("evidence_pack_id", "source_path", "copied_log_path"):
        if not isinstance(binding.get(key), str) or not binding[key]:
            add(
                blockers,
                f"approved_runtime_evidence_binding_{key}_missing",
                f"{binding_label}.{key}",
                observed=binding.get(key),
            )
    if binding.get("source_path") != binding.get("copied_log_path"):
        add(
            blockers,
            "approved_runtime_evidence_binding_source_copied_log_path_mismatch",
            binding_label,
            source_path=binding.get("source_path"),
            copied_log_path=binding.get("copied_log_path"),
        )
    if binding.get("source_sha256") != binding.get("copied_log_sha256"):
        add(
            blockers,
            "approved_runtime_evidence_binding_source_copied_log_sha256_mismatch",
            binding_label,
            source_sha256=binding.get("source_sha256"),
            copied_log_sha256=binding.get("copied_log_sha256"),
        )
    binding_shortcuts = approved_runtime_evidence_binding_shortcut_claims(binding, binding_label)
    shortcut_claims = binding_shortcuts["non_counting"]
    if shortcut_claims:
        add(
            blockers,
            "approved_runtime_evidence_binding_non_counting_shortcut_claimed",
            binding_label,
            claims=shortcut_claims,
        )
    public_shortcut_claims = binding_shortcuts["public_shortcuts"]
    if public_shortcut_claims:
        add(
            blockers,
            "approved_runtime_evidence_binding_public_header_api_abi_shortcut_claimed",
            binding_label,
            claims=public_shortcut_claims,
        )


def resolve_source_artifact_path(
    path: Path,
    blockers: list[dict[str, Any]],
    label: str,
) -> Path | None:
    try:
        protected_paths.reject_symlink_component(path, label)
        resolved = protected_paths.reject_protected_input_path(path, label)
    except SystemExit as exc:
        add(blockers, "source_artifact_path_rejected", label, path=str(path), error=str(exc))
        return None
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        add(blockers, "source_artifact_path_outside_repo", label, path=str(path), resolved=str(resolved))
        return None
    return resolved


def artifact_entry_strings(value: Any, label: str = "$.source_artifacts") -> list[dict[str, str]]:
    strings: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                strings.append({"path": f"{label}.{key}", "value": key})
            strings.extend(artifact_entry_strings(item, f"{label}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            strings.extend(artifact_entry_strings(item, f"{label}[{index}]"))
    elif isinstance(value, str):
        strings.append({"path": label, "value": value})
    return strings


def validate_source_artifacts(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    sources = payload.get("source_artifacts")
    if not isinstance(sources, dict):
        add(blockers, "source_artifacts_missing_or_not_object", "$.source_artifacts")
        return
    allowed_source_values = (
        set(EXPECTED_SOURCE_ARTIFACTS)
        | {spec["path"] for spec in EXPECTED_SOURCE_ARTIFACTS.values()}
        | {spec["role"] for spec in EXPECTED_SOURCE_ARTIFACTS.values()}
        | {REVIEW_ROUTE}
    )
    source_strings = artifact_entry_strings(sources)
    notice_only = [
        item
        for item in source_strings
        if item["value"] not in allowed_source_values and NON_COUNTING_SOURCE_ARTIFACT_RE.search(item["value"])
    ]
    if notice_only:
        add(blockers, "source_artifacts_notice_only_or_non_counting_claimed", "$.source_artifacts", claims=notice_only)
    public_shortcuts = [
        item
        for item in source_strings
        if item["value"] not in allowed_source_values and PUBLIC_SHORTCUT_SOURCE_ARTIFACT_RE.search(item["value"])
    ]
    if public_shortcuts:
        add(blockers, "source_artifacts_public_header_api_abi_shortcut_claimed", "$.source_artifacts", claims=public_shortcuts)

    expected_labels = set(EXPECTED_SOURCE_ARTIFACTS)
    observed_labels = set(sources)
    if observed_labels != expected_labels:
        add(
            blockers,
            "source_artifacts_keys_mismatch",
            "$.source_artifacts",
            expected=sorted(expected_labels),
            observed=sorted(observed_labels),
        )

    for label, expected in EXPECTED_SOURCE_ARTIFACTS.items():
        entry = sources.get(label)
        entry_label = f"$.source_artifacts.{label}"
        if not isinstance(entry, dict):
            add(blockers, "source_artifact_entry_missing_or_not_object", entry_label)
            continue
        entry_keys = set(entry)
        if entry_keys != SOURCE_ARTIFACT_ENTRY_KEYS:
            add(
                blockers,
                "source_artifact_entry_keys_mismatch",
                entry_label,
                expected=sorted(SOURCE_ARTIFACT_ENTRY_KEYS),
                observed=sorted(entry_keys),
            )
        if "sha256" not in entry:
            add(
                blockers,
                "source_artifact_sha256_missing",
                f"{entry_label}.sha256",
                expected="repo-local current source artifact sha256",
                observed=None,
            )
            continue
        partial_hash_keys = sorted(key for key in entry_keys - SOURCE_ARTIFACT_ENTRY_KEYS if PARTIAL_HASH_KEY_RE.search(key))
        if partial_hash_keys:
            add(
                blockers,
                "source_artifact_partial_or_extra_hash_claimed",
                entry_label,
                keys=partial_hash_keys,
            )
        expected_path = expected["path"]
        if entry.get("path") != expected_path:
            add(
                blockers,
                "source_artifact_path_mismatch",
                f"{entry_label}.path",
                expected=expected_path,
                observed=entry.get("path"),
            )
        if entry.get("role") != expected["role"]:
            add(
                blockers,
                "source_artifact_role_mismatch",
                f"{entry_label}.role",
                expected=expected["role"],
                observed=entry.get("role"),
            )
        if entry.get("counting_scope") != REVIEW_ROUTE:
            add(
                blockers,
                "source_artifact_counting_scope_mismatch",
                f"{entry_label}.counting_scope",
                expected=REVIEW_ROUTE,
                observed=entry.get("counting_scope"),
            )
        observed_hash = entry.get("sha256")
        if not isinstance(observed_hash, str) or SOURCE_ARTIFACT_HASH_RE.fullmatch(observed_hash) is None:
            add(blockers, "source_artifact_sha256_invalid", f"{entry_label}.sha256", observed=observed_hash)
            continue
        source_path = resolve_source_artifact_path(
            REPO_ROOT / expected_path,
            blockers,
            f"{entry_label}.path",
        )
        if source_path is None:
            continue
        if not source_path.is_file():
            add(blockers, "source_artifact_file_missing", f"{entry_label}.path", path=expected_path)
            continue
        current_hash = sha256_file(source_path)
        if observed_hash != current_hash:
            add(
                blockers,
                "source_artifact_hash_mismatch",
                f"{entry_label}.sha256",
                expected=current_hash,
                observed=observed_hash,
            )


def validate_route_contract(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    route = payload.get("route")
    if not isinstance(route, dict):
        add(blockers, "route_missing_or_not_object", "$.route")
    else:
        expected_route_keys = set(REQUIRED_ROUTE)
        observed_route_keys = set(route)
        if observed_route_keys != expected_route_keys:
            add(
                blockers,
                "route_keys_mismatch",
                "$.route",
                expected=sorted(expected_route_keys),
                observed=sorted(observed_route_keys),
            )
        for key, expected in REQUIRED_ROUTE.items():
            observed = route.get(key)
            if observed != expected:
                add(
                    blockers,
                    f"route_{key}_mismatch",
                    f"$.route.{key}",
                    expected=expected,
                    observed=observed,
                )
        shortcut_values = [
            {"path": f"$.route.{key}", "value": value}
            for key, value in route.items()
            if isinstance(value, str) and normalized_alias(value) in {
                normalized_alias(item) for item in FORBIDDEN_ROUTE_BLOCKER_VALUES
            }
        ]
        if shortcut_values:
            add(blockers, "route_public_header_api_abi_shortcut_claimed", "$.route", claims=shortcut_values)

    aliases = payload.get("route_blocker_aliases")
    if not isinstance(aliases, dict):
        add(blockers, "route_blocker_aliases_missing_or_not_object", "$.route_blocker_aliases")
        return
    for alias in REQUIRED_ROUTE_BLOCKER_ALIASES_TRUE:
        if aliases.get(alias) is not True:
            add(blockers, "route_blocker_alias_not_true", f"$.route_blocker_aliases.{alias}", observed=aliases.get(alias))
    for alias in REQUIRED_ROUTE_BLOCKER_ALIASES_FALSE:
        if aliases.get(alias) is not False:
            add(blockers, "route_blocker_alias_not_false", f"$.route_blocker_aliases.{alias}", observed=aliases.get(alias))
    expected_aliases = REQUIRED_ROUTE_BLOCKER_ALIASES_TRUE | REQUIRED_ROUTE_BLOCKER_ALIASES_FALSE
    unexpected_aliases = sorted(set(aliases) - expected_aliases)
    if unexpected_aliases:
        add(blockers, "route_blocker_aliases_unexpected", "$.route_blocker_aliases", aliases=unexpected_aliases)


def validate_next_step_check(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    observed = payload.get(NEXT_STEP_CHECK_FIELD)
    normalized_observed = normalize_next_step_check_for_compat(observed)
    if normalized_observed != REQUIRED_NEXT_STEP_CHECK:
        add(
            blockers,
            "post_runtime_identity_contract_next_step_mismatch",
            f"$.{NEXT_STEP_CHECK_FIELD}",
            expected=REQUIRED_NEXT_STEP_CHECK,
            observed=observed,
        )


def normalize_next_step_check_for_compat(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    flags = value.get("non_claim_flags")
    if isinstance(flags, dict):
        normalized_flags = dict(flags)
        for key in POST_RUNTIME_COMPAT_FALSE_FLAGS:
            normalized_flags.setdefault(key, False)
        normalized["non_claim_flags"] = normalized_flags
    return normalized


def normalize_post_runtime_identity_contract_gate_for_compat(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = dict(value)
    after_runtime = value.get("after_accepted_runtime_evidence")
    if isinstance(after_runtime, dict):
        normalized_after_runtime = dict(after_runtime)
        for key in POST_RUNTIME_COMPAT_FALSE_FLAGS:
            normalized_after_runtime.setdefault(key, False)
        normalized["after_accepted_runtime_evidence"] = normalized_after_runtime
    return normalized


def validate_post_runtime_identity_contract_gate(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    observed = payload.get(POST_RUNTIME_GATE_FIELD)
    normalized_observed = normalize_post_runtime_identity_contract_gate_for_compat(observed)
    if normalized_observed != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE:
        add(
            blockers,
            "post_runtime_identity_contract_gate_mismatch",
            f"$.{POST_RUNTIME_GATE_FIELD}",
            expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE,
            observed=observed,
        )


def validate_runtime_contract_currentness_diagnostic(
    payload: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    observed = payload.get(CURRENTNESS_DIAGNOSTIC_FIELD)
    if observed != REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC:
        add(
            blockers,
            "runtime_evidence_contract_review_currentness_mismatch",
            f"$.{CURRENTNESS_DIAGNOSTIC_FIELD}",
            expected=REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            observed=observed,
        )


def string_set(value: Any) -> set[str] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return set(value)


def explicitly_false(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if value == [] or value == {}:
        return True
    if isinstance(value, str):
        return normalized_alias(value) == "false" or ZERO_PROGRESS_VALUE_RE.fullmatch(value) is not None
    return False


def shortcut_value_present(value: Any) -> bool:
    if value in (None, ""):
        return False
    if explicitly_false(value):
        return False
    if isinstance(value, list):
        return any(shortcut_value_present(item) for item in value)
    if isinstance(value, dict):
        return any(shortcut_value_present(item) for item in value.values())
    return True


def shortcut_alias_scan_skipped(label: str) -> bool:
    return (
        label == "$.source_artifact_hash_policy"
        or ".non_claim" in label
        or any(label.startswith(prefix) for prefix in SHORTCUT_ALIAS_SKIP_PREFIXES)
    )


def value_has_stale_hash_current_alias(value: Any) -> bool:
    if isinstance(value, str):
        return STALE_HASH_CURRENT_ALIAS_VALUE_RE.fullmatch(normalized_claim_key(value)) is not None
    if isinstance(value, list):
        return any(value_has_stale_hash_current_alias(item) for item in value)
    if isinstance(value, dict):
        return any(value_has_stale_hash_current_alias(item) for item in value.values())
    return False


def shortcut_alias_overclaims(value: Any, label: str = "$") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_label = f"{label}.{key}" if label != "$" else f"$.{key}"
            if isinstance(key, str) and not shortcut_alias_scan_skipped(item_label):
                key_name = normalized_claim_key(key)
                if STALE_HASH_CURRENT_ALIAS_KEY_RE.search(key_name) is not None and shortcut_value_present(item):
                    claims.append(
                        {
                            "path": item_label,
                            "reason": "stale_hash_current_contract_alias_present",
                            "key": key,
                            "value": item,
                        }
                    )
                if (
                    key_name in DECISION_RECORD_METADATA_STATUS_KEYS
                    and label_marks_decision_record_metadata_context(label)
                    and value_has_stale_hash_current_alias(item)
                ):
                    claims.append(
                        {
                            "path": item_label,
                            "reason": "stale_hash_current_contract_alias_present",
                            "key": key,
                            "value": item,
                        }
                    )
                if (
                    RUNTIME_EVIDENCE_SHORTCUT_ALIAS_KEY_RE.search(key_name) is not None
                    and shortcut_value_present(item)
                ):
                    claims.append(
                        {
                            "path": item_label,
                            "reason": "runtime_evidence_shortcut_alias_present",
                            "key": key,
                            "value": item,
                        }
                    )
                if P0_PROGRESS_SHORTCUT_ALIAS_KEY_RE.search(key_name) is not None and shortcut_value_present(item):
                    claims.append(
                        {
                            "path": item_label,
                            "reason": "p0_progress_alias_not_false",
                            "key": key,
                            "value": item,
                        }
                    )
            claims.extend(shortcut_alias_overclaims(item, item_label))
        return claims
    if isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(shortcut_alias_overclaims(item, f"{label}[{index}]"))
    return claims


def validate_no_shortcut_aliases(value: Any, blockers: list[dict[str, Any]]) -> None:
    for claim in shortcut_alias_overclaims(value):
        add(
            blockers,
            claim["reason"],
            claim["path"],
            alias=claim["key"],
            observed=claim["value"],
        )


def string_token_explicitly_false(value: str, match: re.Match[str]) -> bool:
    return EXPLICIT_FALSE_SUFFIX_RE.match(value[match.end() :]) is not None


def string_token_explicitly_true(value: str, match: re.Match[str]) -> bool:
    return EXPLICIT_TRUE_SUFFIX_RE.match(value[match.end() :]) is not None


def is_positive_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, list):
        return any(is_positive_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(is_positive_claim_value(item) for item in value.values())
    if isinstance(value, str):
        normalized = normalized_claim_key(value)
        if normalized in POSITIVE_CLAIM_VALUE_TOKENS:
            return True
        stripped = value.strip().casefold()
        if ZERO_PROGRESS_VALUE_RE.fullmatch(stripped):
            return False
        return re.fullmatch(
            r"(?:[1-9]\d*(?:\.\d+)?|0\.\d*[1-9]\d*)\s*(?:/|%|percent|of\b)?.*",
            stripped,
        ) is not None
    return False


def normalized_label_parts(label: str) -> list[str]:
    return [
        normalized_claim_key(re.sub(r"\[[0-9]+\]", "", part))
        for part in label.removeprefix("$.").split(".")
        if part and not part.startswith("[")
    ]


def decision_record_metadata_context_key(key_name: str) -> bool:
    return (
        key_name in DECISION_RECORD_METADATA_CONTEXT_KEYS
        or (
            "decision_record" in key_name
            and ("identity" in key_name or "contract" in key_name or "public" in key_name)
        )
        or ("reviewed_hash_current" in key_name and "contract_review_only" in key_name)
    )


def label_marks_decision_record_metadata_context(label: str) -> bool:
    return any(decision_record_metadata_context_key(part) for part in normalized_label_parts(label))


def decision_record_metadata_progress_alias_key(key_name: str) -> bool:
    return (
        key_name in DECISION_RECORD_METADATA_PROGRESS_ALIAS_KEYS
        or DECISION_RECORD_METADATA_PROGRESS_ALIAS_RE.search(key_name) is not None
    )


def normalized_metadata_values(value: Any) -> set[str]:
    if isinstance(value, str):
        return {normalized_claim_key(value)}
    if isinstance(value, bool) or value is None:
        return set()
    if isinstance(value, (int, float)):
        return {str(value)}
    if isinstance(value, list):
        values: set[str] = set()
        for item in value:
            values.update(normalized_metadata_values(item))
        return values
    if isinstance(value, dict):
        values: set[str] = set()
        for item in value.values():
            values.update(normalized_metadata_values(item))
        return values
    return set()


def value_marks_reviewed_hash_current_contract_metadata(value: Any) -> bool:
    if isinstance(value, str):
        return normalized_claim_key(value) == "reviewed_hash_current_contract_review_only"
    if isinstance(value, list):
        return any(value_marks_reviewed_hash_current_contract_metadata(item) for item in value)
    if not isinstance(value, dict):
        return False

    reviewed = False
    hash_current = False
    contract_review_only = False
    for key, item in value.items():
        key_name = normalized_claim_key(key)
        item_values = normalized_metadata_values(item)
        if "reviewed_hash_current_contract_review_only" in item_values:
            return True
        if key_name not in DECISION_RECORD_METADATA_STATUS_KEYS:
            continue
        if item_values & DECISION_RECORD_METADATA_REVIEWED_VALUES:
            reviewed = True
        if (
            item_values & DECISION_RECORD_METADATA_HASH_CURRENT_VALUES
            and ("hash" in key_name or key_name in {"state", "status"})
        ):
            hash_current = True
        if item_values & DECISION_RECORD_METADATA_SCOPE_VALUES:
            contract_review_only = True
    return reviewed and hash_current and contract_review_only


def decision_record_metadata_progress_value_is_positive(item: Any) -> bool:
    if isinstance(item, bool):
        return item
    if isinstance(item, (int, float)):
        return item != 0
    if isinstance(item, str):
        normalized = normalized_claim_key(item)
        if normalized in {
            "",
            "0",
            "0_0",
            "blocked",
            "false",
            "missing",
            "no",
            "none",
            "not_ready",
            "pending",
            "reviewed",
            "current",
            "hash_current",
            "contract_review_only",
            "reviewed_hash_current_contract_review_only",
        }:
            return False
        stripped = item.strip().casefold()
        if ZERO_PROGRESS_VALUE_RE.fullmatch(stripped):
            return False
        return (
            DECISION_RECORD_METADATA_PROGRESS_VALUE_RE.search(normalized) is not None
            or re.fullmatch(
                r"(?:[1-9]\d*(?:\.\d+)?|0\.\d*[1-9]\d*)\s*(?:/|%|percent|of\b)?.*",
                stripped,
            )
            is not None
        )
    if isinstance(item, list):
        return any(decision_record_metadata_progress_value_is_positive(child) for child in item)
    if isinstance(item, dict):
        return any(decision_record_metadata_progress_value_is_positive(child) for child in item.values())
    return False


def provenance_value_contains_non_promotional_term(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_key(value)
        return any(term in normalized for term in NON_PROMOTIONAL_PROVENANCE_CONTEXT_TERMS)
    if isinstance(value, list):
        return any(provenance_value_contains_non_promotional_term(child) for child in value)
    if isinstance(value, dict):
        return any(provenance_value_contains_non_promotional_term(item) for item in value.values())
    return False


def value_marks_non_promotional_provenance_context(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                normalized_claim_key(key) in NON_PROMOTIONAL_PROVENANCE_CONTEXT_KEYS
                and provenance_value_contains_non_promotional_term(item)
            ):
                return True
            if isinstance(item, (dict, list)) and value_marks_non_promotional_provenance_context(item):
                return True
        return False
    if isinstance(value, list):
        return any(value_marks_non_promotional_provenance_context(child) for child in value)
    return False


def is_nonempty_public_surface_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if value in (False, None):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) not in NON_PROMOTIONAL_CLAIM_VALUE_TOKENS
    if isinstance(value, list):
        return any(is_nonempty_public_surface_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(is_nonempty_public_surface_claim_value(item) for item in value.values())
    return False


def split_claim_name_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def nested_claim_key_candidates(label: str, key: object) -> set[str]:
    candidates = {normalized_claim_key(key)}
    path_parts = [
        normalized_claim_key(re.sub(r"\[[0-9]+\]", "", part))
        for part in label.removeprefix("$.").split(".")
        if part and not part.startswith("[")
    ]
    for depth in range(1, 5):
        prefix = path_parts[-depth:]
        if prefix:
            candidates.add("_".join([*prefix, normalized_claim_key(key)]))
    return candidates


def first_claim_key(candidates: set[str], claim_keys: frozenset[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in claim_keys), None)


def split_claim_overclaims(value: dict[str, Any], label: str) -> list[dict[str, Any]]:
    declared_claim_names = [
        claim_name
        for key, item in value.items()
        if normalized_claim_key(key) in SPLIT_CLAIM_NAME_KEYS
        for claim_name in split_claim_name_values(item)
    ]
    declared_claim_values = [
        item
        for key, item in value.items()
        if normalized_claim_key(key) in SPLIT_CLAIM_VALUE_KEYS
    ]
    overclaims: list[dict[str, Any]] = []
    for claim_name in declared_claim_names:
        claim_key = normalized_claim_key(claim_name)
        positive_claim = any(is_positive_claim_value(item) for item in declared_claim_values)
        public_surface_list_claim = (
            claim_key in SPLIT_CLAIM_PUBLIC_LIST_KEYS
            and any(is_nonempty_public_surface_claim_value(item) for item in declared_claim_values)
        )
        nonfalse_shortcut_claim = (
            claim_key in NON_FALSE_CLAIM_ALIAS_KEYS
            and any(is_nonempty_public_surface_claim_value(item) for item in declared_claim_values)
        )
        if public_surface_list_claim or (
            (positive_claim or nonfalse_shortcut_claim)
            and (
                claim_key in SPLIT_CLAIM_FALSE_KEYS
                or claim_key in SPLIT_CLAIM_SUBJECT_KEYS
                or APPROVED_RUNTIME_SPLIT_CLAIM_KEY_RE.search(claim_key) is not None
            )
        ):
            overclaims.append({"path": label, "term": "split_readiness_alias", "value": value})
        if decision_record_metadata_context_key(claim_key) and any(
            decision_record_metadata_progress_value_is_positive(item) for item in declared_claim_values
        ):
            overclaims.append(
                {
                    "path": label,
                    "term": "decision_record_metadata_p0_progress",
                    "value": value,
                }
            )
    return overclaims


def path_context_subject_claim(label: str, key: str, item: Any) -> dict[str, Any] | None:
    candidates = nested_claim_key_candidates(label, key)
    readiness_key = first_claim_key(candidates, SPLIT_CLAIM_FALSE_KEYS)
    public_list_key = first_claim_key(candidates, SPLIT_CLAIM_PUBLIC_LIST_KEYS)
    if public_list_key is not None and is_nonempty_public_surface_claim_value(item):
        return {"path": f"{label}.{key}", "term": "public_surface_list", "value": item}
    if readiness_key is not None and (
        is_positive_claim_value(item)
        or (
            readiness_key in NON_FALSE_CLAIM_ALIAS_KEYS
            and is_nonempty_public_surface_claim_value(item)
        )
    ):
        return {"path": f"{label}.{key}", "term": "readiness_alias", "value": item}
    normalized_key = normalized_claim_key(key)
    if normalized_key not in SPLIT_CLAIM_VALUE_KEYS or not is_positive_claim_value(item):
        return None
    path_parts = [
        normalized_claim_key(re.sub(r"\[[0-9]+\]", "", part))
        for part in label.removeprefix("$.").split(".")
        if part and not part.startswith("[")
    ]
    for depth in range(1, 5):
        subject = "_".join(path_parts[-depth:])
        if subject in SPLIT_CLAIM_SUBJECT_KEYS:
            return {"path": f"{label}.{key}", "term": "nested_readiness_alias", "value": item}
    return None


APPROVED_RUNTIME_SPLIT_CLAIM_KEY_RE = re.compile(
    r"(?:public|sdk|abi|capability|callback|header|identity|principal|permission|authz?|"
    r"access[_ -]?control|acl|roles?|privileges?|moderation|ban|kick|admin|runtime|stable|"
    r"command|chat|reply|broadcast|rcon|lookup|storage|persist|mutation|return[_ -]?override|"
    r"resource[_ -]?(?:handle|id|ref|reference|token)|object[_ -]?handle|v1|p0)"
    r".*(?:ready|readiness|allowed|promoted|reviewed|current|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|"
    r"complete|satisfied|passed|passing|supported|available|counting)"
    r"|(?:ready|readiness|allowed|promoted|reviewed|current|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|"
    r"complete|satisfied|passed|passing|supported|available|counting).*"
    r"(?:public|sdk|abi|identity|principal|permission|authz?|access[_ -]?control|acl|roles?|"
    r"privileges?|moderation|ban|kick|admin|command|chat|reply|broadcast|rcon|lookup|storage|persist|"
    r"mutation|runtime|stable|return[_ -]?override|resource[_ -]?(?:handle|id|ref|reference|token)|"
    r"object[_ -]?handle|v1|p0)",
    re.IGNORECASE,
)


def claim_alias_overclaims(value: Any, label: str = "$") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    if label == "$":
        claims.extend(source_overclaim_zero_overclaims(value))
    if isinstance(value, dict):
        decision_record_metadata_context = (
            label_marks_decision_record_metadata_context(label)
            or value_marks_reviewed_hash_current_contract_metadata(value)
        )
        provenance_context = value_marks_non_promotional_provenance_context(value)
        if provenance_context:
            for key, item in value.items():
                if not isinstance(key, str):
                    continue
                key_name = normalized_claim_key(key)
                if (
                    key_name in NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS
                    and is_positive_claim_value(item)
                ) or (
                    decision_record_metadata_progress_alias_key(key_name)
                    and decision_record_metadata_progress_value_is_positive(item)
                ):
                    claims.append(
                        {
                            "path": f"{label}.{key}",
                            "term": "non_promotional_provenance_status_alias",
                            "value": item,
                        }
                    )
        if decision_record_metadata_context:
            for key, item in value.items():
                if not isinstance(key, str):
                    continue
                key_name = normalized_claim_key(key)
                if decision_record_metadata_progress_alias_key(key_name) and is_positive_claim_value(item):
                    claims.append(
                        {
                            "path": f"{label}.{key}",
                            "term": "decision_record_metadata_p0_progress",
                            "value": item,
                        }
                    )
                if (
                    key_name in SPLIT_CLAIM_VALUE_KEYS
                    and decision_record_metadata_progress_value_is_positive(item)
                ):
                    claims.append(
                        {
                            "path": f"{label}.{key}",
                            "term": "decision_record_metadata_p0_progress",
                            "value": item,
                        }
                    )
        claims.extend(split_claim_overclaims(value, label))
        for key, item in value.items():
            item_label = f"{label}.{key}"
            if isinstance(key, str):
                context_claim = path_context_subject_claim(label, key, item)
                if context_claim is not None:
                    claims.append(context_claim)
            claims.extend(claim_alias_overclaims(item, item_label))
        return claims
    if isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(claim_alias_overclaims(item, f"{label}[{index}]"))
    return claims


def claim_alias_candidates(label: str, key: str) -> set[str]:
    candidates = {normalized_alias(key)}
    path_parts = [
        re.sub(r"\[[0-9]+\]", "", part)
        for part in label.removeprefix("$.").split(".")
        if part and not part.startswith("[")
    ]
    for depth in (1, 2):
        prefix_parts = path_parts[-depth:]
        if prefix_parts:
            candidates.add(normalized_alias("".join(prefix_parts) + key))
    return candidates


def is_unexpected_claim_alias_key(label: str, key: str, item: Any) -> bool:
    if label.startswith("$.source_artifacts") or label.startswith("$.route"):
        return False
    if label == "$.decisions":
        return False
    normalized = normalized_alias(key)
    if normalized in CLAIM_ALIAS_KEYS:
        return True
    if normalized in BROAD_STANDALONE_CLAIM_KEYS and not isinstance(item, (dict, list)):
        return True
    if any(candidate in CLAIM_ALIAS_KEYS for candidate in claim_alias_candidates(label, key)):
        return True
    return UNEXPECTED_CLAIM_ALIAS_KEY_RE.search(key) is not None


def validate_no_hidden_claim_aliases(value: Any, blockers: list[dict[str, Any]], label: str = "$") -> None:
    if ".non_claim" in label or ".non_claims" in label:
        return
    if label.startswith(f"$.{CURRENTNESS_DIAGNOSTIC_FIELD}"):
        return
    if label.startswith(f"$.{APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD}"):
        return
    if label.startswith(f"$.{APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD}"):
        return
    if label.startswith(f"$.{STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD}"):
        return
    if label.startswith(
        f"$.{NEXT_STEP_CHECK_FIELD}.required_approved_runtime_evidence_manifest_"
    ):
        return
    if label == "$":
        for claim in claim_alias_overclaims(value):
            add(
                blockers,
                "split_or_nested_claim_alias_present",
                claim["path"],
                term=claim["term"],
                observed=claim["value"],
            )
    if isinstance(value, dict):
        for key, item in value.items():
            item_label = f"{label}.{key}"
            if isinstance(key, str) and is_unexpected_claim_alias_key(label, key, item) and not explicitly_false(item):
                add(blockers, "claim_alias_not_false", item_label, alias=key, observed=item)
            validate_no_hidden_claim_aliases(item, blockers, item_label)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_no_hidden_claim_aliases(item, blockers, f"{label}[{index}]")
        return
    if not isinstance(value, str):
        return
    leaf = normalized_claim_key(label.rsplit(".", 1)[-1].split("[", 1)[0])
    if leaf in SPLIT_CLAIM_NAME_KEYS:
        return
    for match in ALIAS_TOKEN_RE.finditer(value):
        alias = match.group(0)
        normalized = normalized_alias(alias)
        if normalized not in CLAIM_ALIAS_KEYS:
            continue
        if string_token_explicitly_false(value, match):
            continue
        if normalized in BROAD_STRING_ALIASES_REQUIRE_TRUE and not string_token_explicitly_true(value, match):
            continue
        add(blockers, "claim_alias_value_present", label, alias=alias, observed=value)


def has_negative_context(value: str, match_start: int) -> bool:
    normalized = value.replace("_", " ")
    clause_start = max(normalized.rfind(";", 0, match_start), normalized.rfind(".", 0, match_start))
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
    for negative in NEGATIVE_CONTEXT_RE.finditer(prefix[-120:]):
        if re.search(
            r"\b(?:resolved|accepted|cleared|satisfied|complete|unblocked)\b",
            prefix[-120:][negative.end() :],
            re.IGNORECASE,
        ):
            continue
        return True
    return bool(
        re.search(
            r"\b(?:forbidden|unavailable|blocked|redacted|cannot|can't|false|exclusion)\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def public_text_overclaims(value: Any, label: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if ".non_claim" in label or ".non_claims" in label:
        return claims
    if isinstance(value, dict):
        for key, item in value.items():
            item_label = f"{label}.{key}"
            claims.extend(public_text_overclaims(item, item_label))
        return claims
    if isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(public_text_overclaims(item, f"{label}[{index}]"))
        return claims
    if not isinstance(value, str):
        return claims
    for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
        for match in pattern.finditer(value):
            if has_negative_context(value, match.start()):
                continue
            claims.append({"path": label, "term": term, "value": value})
            break
    return claims


def validate_no_public_text_overclaims(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    claims = public_text_overclaims(payload)
    if claims:
        add(blockers, "public_text_or_source_overclaim", "$", claims=claims)


def contains_stale_proposed_header_symbol(value: Any) -> bool:
    if isinstance(value, str):
        return STALE_PROPOSED_HEADER_SYMBOL_RE.search(value) is not None
    if isinstance(value, list):
        return any(contains_stale_proposed_header_symbol(item) for item in value)
    if isinstance(value, dict):
        return any(contains_stale_proposed_header_symbol(item) for item in value.values())
    return False


def nonempty_claim_value(value: Any) -> bool:
    if value in (False, None):
        return False
    if value == "" or value == [] or value == {}:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return normalized_claim_key(value) not in NON_PROMOTIONAL_CLAIM_VALUE_TOKENS
    return True


def value_contains_route_shortcut_mismatch(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalized_claim_key(value)
        forbidden = {normalized_claim_key(item) for item in FORBIDDEN_ROUTE_BLOCKER_VALUES}
        return normalized in forbidden and normalized not in ROUTE_SHORTCUT_ALLOWED_VALUES
    if isinstance(value, list):
        return any(value_contains_route_shortcut_mismatch(item) for item in value)
    if isinstance(value, dict):
        return any(value_contains_route_shortcut_mismatch(item) for item in value.values())
    return False


def validate_transition_integrity_metadata(
    value: Any,
    blockers: list[dict[str, Any]],
    label: str = "$",
) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            item_label = f"{label}.{key}" if label != "$" else f"$.{key}"
            if isinstance(key, str):
                normalized_key = normalized_claim_key(key)
                if (
                    normalized_key in IDENTITY_CONTRACT_GATE_MISSING_TRUE_ALIAS_KEYS
                    and item is not True
                ):
                    add(
                        blockers,
                        "identity_public_contract_gate_missing_alias_not_true",
                        item_label,
                        key=key,
                        expected=True,
                        observed=item,
                    )
                if (
                    normalized_key in DOWNSTREAM_GATE_MISSING_FALSE_ALIAS_KEYS
                    and item is not False
                ):
                    add(
                        blockers,
                        "downstream_gate_missing_alias_not_false",
                        item_label,
                        key=key,
                        expected=False,
                        observed=item,
                    )
                if normalized_key in FORBIDDEN_CHAIN_POSITION_KEYS and nonempty_claim_value(item):
                    add(
                        blockers,
                        "dependency_chain_position_claimed_before_promotion",
                        item_label,
                        key=key,
                        observed=item,
                    )
                expected_blocker = BLOCKER_ID_EXPECTATIONS.get(normalized_key)
                if (
                    expected_blocker is not None
                    and isinstance(item, str)
                    and item not in {expected_blocker, REVIEW_ROUTE}
                ):
                    add(
                        blockers,
                        "blocker_id_mismatch",
                        item_label,
                        expected=expected_blocker,
                        observed=item,
                    )
                if (
                    normalized_key in ROUTE_SHORTCUT_METADATA_KEYS
                    and value_contains_route_shortcut_mismatch(item)
                ):
                    add(
                        blockers,
                        "route_shortcut_alias_mismatch",
                        item_label,
                        key=key,
                        expected=sorted(ROUTE_SHORTCUT_ALLOWED_VALUES),
                        observed=item,
                    )
                if (
                    normalized_key in REVIEWED_HASH_CURRENT_CONTRACT_REVIEW_SHORTCUT_KEYS
                    and shortcut_value_present(item)
                ):
                    add(
                        blockers,
                        "reviewed_hash_current_contract_review_shortcut_alias_present",
                        item_label,
                        key=key,
                        observed=item,
                    )
                if normalized_key in PROPOSED_HEADER_SYMBOL_KEYS and contains_stale_proposed_header_symbol(item):
                    add(
                        blockers,
                        "stale_proposed_header_symbols_claimed",
                        item_label,
                        key=key,
                        observed=item,
                    )
            validate_transition_integrity_metadata(item, blockers, item_label)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_transition_integrity_metadata(item, blockers, f"{label}[{index}]")


def validate_false_flags(payload: dict[str, Any], blockers: list[dict[str, Any]], prefix: str = "$") -> None:
    for key in FALSE_FLAGS:
        if payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"{prefix}.{key}", observed=payload.get(key))
    for key in OPTIONAL_FALSE_ALIAS_FLAGS:
        if key in payload and payload.get(key) is not False:
            add(blockers, f"{key}_not_false", f"{prefix}.{key}", observed=payload.get(key))
    for key in EMPTY_PUBLIC_LISTS:
        if payload.get(key) != []:
            add(blockers, f"{key}_not_empty", f"{prefix}.{key}", observed=payload.get(key))


def list_delta(expected: list[str], observed: Any) -> dict[str, list[str]]:
    observed_list = observed if isinstance(observed, list) and all(isinstance(item, str) for item in observed) else []
    expected_set = set(expected)
    observed_set = set(observed_list)
    return {
        "missing": [key for key in expected if key not in observed_set],
        "unexpected": [key for key in observed_list if key not in expected_set],
    }


def validate_decisions(payload: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    resolved = payload.get("resolved_decision_keys")
    if resolved != REQUIRED_REVIEW_DECISION_KEYS:
        delta = list_delta(REQUIRED_REVIEW_DECISION_KEYS, resolved)
        add(
            blockers,
            "resolved_decision_keys_mismatch",
            "$.resolved_decision_keys",
            expected=REQUIRED_REVIEW_DECISION_KEYS,
            observed=resolved,
            missing=delta["missing"],
            unexpected=delta["unexpected"],
            required_action=DECISION_KEY_MISMATCH_REQUIRED_ACTION,
            next_blocker=NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            counts_toward_public_sdk=False,
            counts_toward_p0_dependency_chain_claim=False,
        )
    decisions = payload.get("decisions")
    if not isinstance(decisions, dict):
        add(blockers, "decisions_missing_or_not_object", "$.decisions")
        return
    observed_keys = sorted(decisions)
    if observed_keys != sorted(REQUIRED_REVIEW_DECISION_KEYS):
        delta = list_delta(REQUIRED_REVIEW_DECISION_KEYS, observed_keys)
        add(
            blockers,
            "decision_entries_mismatch",
            "$.decisions",
            expected=sorted(REQUIRED_REVIEW_DECISION_KEYS),
            observed=observed_keys,
            missing=delta["missing"],
            unexpected=delta["unexpected"],
            required_action=DECISION_KEY_MISMATCH_REQUIRED_ACTION,
            next_blocker=NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            counts_toward_public_sdk=False,
            counts_toward_p0_dependency_chain_claim=False,
        )
    for key in REQUIRED_REVIEW_DECISION_KEYS:
        decision = decisions.get(key)
        label = f"$.decisions.{key}"
        if not isinstance(decision, dict):
            add(blockers, "decision_entry_missing_or_not_object", label)
            continue
        entry_keys = set(decision)
        if entry_keys != DECISION_ENTRY_KEYS:
            add(
                blockers,
                "decision_entry_keys_mismatch",
                label,
                expected=sorted(DECISION_ENTRY_KEYS),
                observed=sorted(entry_keys),
            )
        if "decision_scope" in decision and decision.get("decision_scope") != DECISION_SCOPE:
            add(
                blockers,
                "decision_entry_decision_scope_mismatch",
                f"{label}.decision_scope",
                expected=DECISION_SCOPE,
                observed=decision.get("decision_scope"),
            )
        if decision.get("status") != "reviewed":
            add(blockers, "decision_entry_status_not_reviewed", f"{label}.status", observed=decision.get("status"))
        if decision.get("resolved") is not True:
            add(blockers, "decision_entry_resolved_not_true", f"{label}.resolved", observed=decision.get("resolved"))
        if decision.get("scope") != DECISION_SCOPE:
            add(
                blockers,
                "decision_entry_scope_mismatch",
                f"{label}.scope",
                expected=DECISION_SCOPE,
                observed=decision.get("scope"),
            )
        non_claims = string_set(decision.get("non_claims"))
        if non_claims is None or not REQUIRED_DECISION_NON_CLAIMS.issubset(non_claims):
            add(blockers, "decision_entry_non_claims_missing_required", f"{label}.non_claims")


def validate_record(payload: dict[str, Any], *, check_mode: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if payload.get("schema") != SCHEMA:
        add(blockers, "schema_mismatch", "$.schema", expected=SCHEMA, observed=payload.get("schema"))
    if payload.get("artifact_id") != ARTIFACT_ID:
        add(blockers, "artifact_id_mismatch", "$.artifact_id", expected=ARTIFACT_ID)
    if payload.get("surface") != SURFACE:
        add(blockers, "surface_mismatch", "$.surface", expected=SURFACE)
    if payload.get("active_after_resolved_input") != ACTIVE_AFTER_RESOLVED_INPUT:
        add(blockers, "active_after_resolved_input_mismatch", "$.active_after_resolved_input")
    if payload.get("review_status") != "reviewed":
        add(blockers, "review_status_not_reviewed", "$.review_status", observed=payload.get("review_status"))
    if payload.get("accepted_for_contract_review") not in (True, False):
        add(
            blockers,
            "accepted_for_contract_review_not_boolean",
            "$.accepted_for_contract_review",
            observed=payload.get("accepted_for_contract_review"),
        )
    if payload.get("accepted_for_contract_review") is not True:
        add(
            blockers,
            "accepted_for_contract_review_not_true",
            "$.accepted_for_contract_review",
            observed=payload.get("accepted_for_contract_review"),
        )
    if payload.get("source_artifact_hash_policy") != SOURCE_ARTIFACT_HASH_POLICY:
        add(
            blockers,
            "source_artifact_hash_policy_mismatch",
            "$.source_artifact_hash_policy",
            expected=SOURCE_ARTIFACT_HASH_POLICY,
            observed=payload.get("source_artifact_hash_policy"),
        )
    validate_route_contract(payload, blockers)
    validate_next_step_check(payload, blockers)
    validate_post_runtime_identity_contract_gate(payload, blockers)
    validate_runtime_contract_currentness_diagnostic(payload, blockers)
    strict_report = validate_strict_approved_runtime_checker_contract_report(payload, blockers)
    _, expected_binding, expected_report = validate_approved_runtime_evidence_manifest_ref(
        payload,
        blockers,
    )
    validate_approved_runtime_evidence_binding(payload, blockers)
    validate_bound_runtime_manifest_contract(
        payload,
        strict_report=strict_report,
        expected_binding=expected_binding,
        expected_report=expected_report,
        blockers=blockers,
    )
    validate_source_artifacts(payload, blockers)
    validate_no_shortcut_aliases(payload, blockers)
    validate_no_hidden_claim_aliases(payload, blockers)
    validate_no_public_text_overclaims(payload, blockers)
    validate_transition_integrity_metadata(payload, blockers)
    validate_decisions(payload, blockers)
    validate_false_flags(payload, blockers)
    non_claims = string_set(payload.get("non_claims"))
    if non_claims is None or not REQUIRED_TOP_LEVEL_NON_CLAIMS.issubset(non_claims):
        add(blockers, "non_claims_missing_required", "$.non_claims")
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_public_header_gate", "$.accepted_for_contract_review")
    return blockers


SOURCE_ARTIFACT_BINDING_BLOCKERS = {
    "source_artifacts_missing_or_not_object",
    "source_artifacts_notice_only_or_non_counting_claimed",
    "source_artifacts_public_header_api_abi_shortcut_claimed",
    "source_artifacts_keys_mismatch",
    "source_artifact_entry_missing_or_not_object",
    "source_artifact_entry_keys_mismatch",
    "source_artifact_partial_or_extra_hash_claimed",
    "source_artifact_path_mismatch",
    "source_artifact_role_mismatch",
    "source_artifact_counting_scope_mismatch",
    "source_artifact_sha256_missing",
    "source_artifact_sha256_invalid",
    "source_artifact_path_rejected",
    "source_artifact_path_outside_repo",
    "source_artifact_file_missing",
    "source_artifact_hash_mismatch",
}


def approved_runtime_evidence_binding_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in blockers
        if str(blocker.get("reason", "")).startswith("approved_runtime_evidence_binding_")
        or str(blocker.get("reason", "")).startswith("approved_runtime_evidence_manifest_ref_")
    ]


def strict_approved_runtime_checker_contract_report_blockers(
    blockers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in blockers
        if str(blocker.get("reason", "")).startswith(
            "strict_approved_runtime_checker_contract_report_"
        )
    ]


def runtime_contract_blocker_reasons(blockers: list[dict[str, Any]]) -> set[str]:
    return {
        str(blocker.get("reason", ""))
        for blocker in approved_runtime_evidence_binding_blockers(blockers)
        + strict_approved_runtime_checker_contract_report_blockers(blockers)
    }


def source_artifact_binding_blockers(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [blocker for blocker in blockers if blocker.get("reason") in SOURCE_ARTIFACT_BINDING_BLOCKERS]


def source_artifact_hash_mismatches(blockers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = []
    freshness_reasons = {
        "source_artifact_hash_mismatch",
        "source_artifact_sha256_invalid",
        "source_artifact_sha256_missing",
    }
    for blocker in blockers:
        reason = blocker.get("reason")
        if reason not in freshness_reasons:
            continue
        label = blocker["label"]
        source_label = label.removeprefix("$.source_artifacts.").removesuffix(".sha256")
        source = EXPECTED_SOURCE_ARTIFACTS.get(source_label, {})
        expected_sha256 = blocker.get("expected")
        source_path = REPO_ROOT / source.get("path", "")
        if not isinstance(expected_sha256, str) or SOURCE_ARTIFACT_HASH_RE.fullmatch(expected_sha256) is None:
            expected_sha256 = sha256_file(source_path) if source_path.is_file() else None
        mismatches.append(
            {
                "label": source_label,
                "path": source.get("path"),
                "reason": reason,
                "expected_sha256": expected_sha256,
                "observed_sha256": blocker.get("observed"),
                "required_action": SOURCE_ARTIFACT_STALE_REQUIRED_ACTION,
                "current_route": CURRENT_ROUTE,
                "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
                "counts_toward_public_sdk": False,
                "counts_toward_p0_dependency_chain_claim": False,
            }
        )
    return mismatches


def source_artifact_freshness(payload: dict[str, Any] | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    binding_blockers = source_artifact_binding_blockers(blockers)
    mismatches = source_artifact_hash_mismatches(blockers)
    current = payload is not None and not binding_blockers
    if current:
        status = "current"
    elif mismatches:
        status = "stale_or_mismatched"
    else:
        status = "invalid_or_unverified"
    return {
        "current": current,
        "status": status,
        "policy": SOURCE_ARTIFACT_HASH_POLICY,
        "required_action": (
            "none"
            if current
            else SOURCE_ARTIFACT_STALE_REQUIRED_ACTION
        ),
        "current_route": CURRENT_ROUTE,
        "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "record_valid_scope": RECORD_VALID_SCOPE,
        "contract_review_only": True,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "required_artifacts": {
            label: {
                "path": spec["path"],
                "role": spec["role"],
                "counting_scope": REVIEW_ROUTE,
            }
            for label, spec in EXPECTED_SOURCE_ARTIFACTS.items()
        },
        "mismatches": mismatches,
        "blockers": [blocker["reason"] for blocker in binding_blockers],
    }


def runtime_contract_currentness_report(
    *,
    freshness: dict[str, Any],
    record_structure_valid: bool,
    strict_approved_runtime_checker_contract_report_valid: bool,
    approved_runtime_evidence_manifest_ref_valid: bool,
    runtime_evidence_binding_valid: bool,
    accepted_for_contract_review: bool,
) -> dict[str, Any]:
    return {
        **REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
        "observed": {
            "record_structure_valid": record_structure_valid,
            "source_artifacts_current": freshness["current"],
            "source_artifact_freshness_status": freshness["status"],
            "source_artifact_mismatches": freshness["mismatches"],
            "source_artifact_required_action": freshness["required_action"],
            "strict_approved_runtime_checker_contract_report_valid": (
                strict_approved_runtime_checker_contract_report_valid
            ),
            "approved_runtime_evidence_manifest_ref_valid": (
                approved_runtime_evidence_manifest_ref_valid
            ),
            "runtime_evidence_binding_valid": runtime_evidence_binding_valid,
            "record_accepted_for_contract_review": accepted_for_contract_review,
            "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
            "accepted_runtime_evidence_counts_as_reviewed_public_identity_contract": False,
            "candidate_preflight_review_aliases_count": False,
            "permissions_admin_unlocked_from_runtime_evidence": False,
            "command_surface_unlocked_from_runtime_evidence": False,
        },
    }


def build_report(payload: dict[str, Any] | None, blockers: list[dict[str, Any]], *, check_mode: str) -> dict[str, Any]:
    runtime_binding_blockers = approved_runtime_evidence_binding_blockers(blockers)
    strict_report_blockers = strict_approved_runtime_checker_contract_report_blockers(blockers)
    runtime_contract_blockers = runtime_contract_blocker_reasons(blockers)
    accepted_for_contract_review_claimed = (
        isinstance(payload, dict)
        and payload.get("accepted_for_contract_review") is True
    )
    non_accepting_template_context_blockers = {
        "post_runtime_identity_contract_next_step_mismatch",
        "runtime_evidence_contract_review_currentness_mismatch",
    }
    record_structure_blockers = [
        blocker
        for blocker in blockers
        if blocker not in runtime_binding_blockers
        and blocker not in strict_report_blockers
        and str(blocker.get("reason", "")) not in runtime_contract_blockers
        and not (
            not accepted_for_contract_review_claimed
            and blocker.get("reason") in non_accepting_template_context_blockers
        )
        and blocker.get("reason") != "accepted_for_contract_review_not_true"
    ]
    record_structure_valid = not record_structure_blockers
    strict_approved_runtime_checker_contract_report_valid = (
        isinstance(payload, dict)
        and isinstance(payload.get(STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD), dict)
        and not strict_report_blockers
    )
    manifest_ref_blockers = [
        blocker
        for blocker in blockers
        if str(blocker.get("reason", "")).startswith("approved_runtime_evidence_manifest_ref_")
    ]
    approved_runtime_evidence_manifest_ref_valid = (
        isinstance(payload, dict)
        and isinstance(payload.get(APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD), dict)
        and not manifest_ref_blockers
    )
    freshness = source_artifact_freshness(payload, blockers)
    runtime_binding = (
        payload.get(APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD)
        if isinstance(payload, dict) and isinstance(payload.get(APPROVED_RUNTIME_EVIDENCE_BINDING_FIELD), dict)
        else None
    )
    runtime_evidence_binding_valid = (
        record_structure_valid
        and strict_approved_runtime_checker_contract_report_valid
        and runtime_binding is not None
        and not runtime_binding_blockers
    )
    accepted_for_contract_review = (
        record_structure_valid
        and runtime_evidence_binding_valid
        and isinstance(payload, dict)
        and payload.get("accepted_for_contract_review") is True
    )
    record_valid = record_structure_valid and (
        not isinstance(payload, dict)
        or payload.get("accepted_for_contract_review") is not True
        or runtime_evidence_binding_valid
    )
    return {
        "schema": REPORT_SCHEMA,
        "input_schema": payload.get("schema") if isinstance(payload, dict) else None,
        "mode": check_mode,
        "ready": False,
        "ready_scope": READY_SCOPE,
        "record_valid": record_valid,
        "record_valid_scope": RECORD_VALID_SCOPE,
        "contract_review_only": record_valid,
        "reviewed_hash_current_contract_review_only": record_valid and freshness["current"],
        "hash_bound_to_current_source_artifacts": freshness["current"],
        "strict_approved_runtime_checker_contract_report_required": True,
        "strict_approved_runtime_checker_contract_report_valid": (
            strict_approved_runtime_checker_contract_report_valid
        ),
        "strict_approved_runtime_checker_contract_report": (
            payload.get(STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD)
            if isinstance(payload, dict)
            and isinstance(payload.get(STRICT_APPROVED_RUNTIME_CHECK_REPORT_FIELD), dict)
            else None
        ),
        "approved_runtime_evidence_binding_required": True,
        "approved_runtime_evidence_manifest_ref_required": True,
        "approved_runtime_evidence_manifest_ref_valid": approved_runtime_evidence_manifest_ref_valid,
        "approved_runtime_evidence_manifest_ref": (
            payload.get(APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD)
            if isinstance(payload, dict)
            and isinstance(payload.get(APPROVED_RUNTIME_EVIDENCE_MANIFEST_REF_FIELD), dict)
            else None
        ),
        "runtime_evidence_binding_valid": runtime_evidence_binding_valid,
        "approved_runtime_evidence_binding": runtime_binding,
        "source_artifact_freshness": freshness,
        "runtime_evidence_contract_review_currentness": runtime_contract_currentness_report(
            freshness=freshness,
            record_structure_valid=record_structure_valid,
            strict_approved_runtime_checker_contract_report_valid=(
                strict_approved_runtime_checker_contract_report_valid
            ),
            approved_runtime_evidence_manifest_ref_valid=(
                approved_runtime_evidence_manifest_ref_valid
            ),
            runtime_evidence_binding_valid=runtime_evidence_binding_valid,
            accepted_for_contract_review=accepted_for_contract_review,
        ),
        "checkable_next_step": {
            **REQUIRED_NEXT_STEP_CHECK,
            "source_artifact_freshness": freshness,
            "runtime_evidence_contract_review_currentness": (
                REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC
            ),
        },
        "post_runtime_identity_contract_gate": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_GATE,
        "accepted_for_contract_review": accepted_for_contract_review,
        "accepted_runtime_lifecycle_evidence_advances_to": (
            REVIEW_ROUTE if accepted_for_contract_review else None
        ),
        "current_route": CURRENT_ROUTE,
        "current_blocker": CURRENT_ROUTE,
        "post_runtime_evidence_next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "resolved_decision_keys": REQUIRED_REVIEW_DECISION_KEYS
        if accepted_for_contract_review
        else [],
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_header_ready": False,
        "public_abi_ready": False,
        "public_abi_allowed": False,
        "public_api_ready": False,
        "public_api_allowed": False,
        "public_sdk_ready": False,
        "public_readiness": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "stable_ready": False,
        "stable_claim_allowed": False,
        "stable_claim_ready": False,
        "stable_sdk_ready": False,
        "plugin_hub_ready": False,
        "plugin_hub_publication_ready": False,
        "publication_ready": False,
        "publication_authorized": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "commands_ready": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "resource_handle_allowed": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "public_sdk_v1_completion_ready": False,
        "public_sdk_v1_completion_claim": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "accepted_for_header_gate_review": False,
        "accepted_for_public_header_gate_review": False,
        "accepted_for_public_header_review": False,
        "accepted_for_public_api_review": False,
        "accepted_for_public_abi_review": False,
        "accepted_for_identity_contract_gate_review": False,
        "accepted_for_identity_public_contract_gate_review": False,
        "accepted_for_public_identity_contract_gate_review": False,
        "post_runtime_identity_contract_gate_missing": True,
        "identity_contract_gate_ready": False,
        "identity_contract_gate_unlocked": False,
        "identity_public_contract_gate_ready": False,
        "identity_public_contract_gate_unlocked": False,
        "identity_public_contract_gate_review_ready": False,
        "public_header_gate_ready": False,
        "public_header_gate_unlocked": False,
        "public_api_gate_ready": False,
        "public_api_gate_unlocked": False,
        "public_abi_gate_ready": False,
        "public_abi_gate_unlocked": False,
        "public_header_symbols_now": [],
        "public_capability_bits_now": [],
        "public_callback_abi_now": [],
        "public_api_symbols_now": [],
        "route_blocker_aliases": {
            **{alias: True for alias in sorted(REQUIRED_ROUTE_BLOCKER_ALIASES_TRUE)},
            **{alias: False for alias in sorted(REQUIRED_ROUTE_BLOCKER_ALIASES_FALSE)},
        },
        "next_blocker": NEXT_BLOCKER_AFTER_ACCEPTED_RUNTIME_EVIDENCE,
        "blockers": [blocker["reason"] for blocker in blockers],
        "blocker_details": blockers,
        "non_claims": sorted(REQUIRED_TOP_LEVEL_NON_CLAIMS),
    }


def main() -> int:
    args = parse_args()
    check_mode = mode(args)
    blockers: list[dict[str, Any]] = []
    payload = load_record(args.record, blockers)
    if payload is not None:
        blockers.extend(validate_record(payload, check_mode=check_mode))
    report = build_report(payload, blockers, check_mode=check_mode)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
