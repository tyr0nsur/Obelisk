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
import check_player_identity_public_contract_decision_record as public_contract_decision_record
import build_player_identity_planning_source_manifests as planning_source_manifests
from native_prototype_guardrails import without_native_prototype_symbols
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
DEFAULT_IDENTIFIER_REDACTION_EVIDENCE = Path(
    "docs/research/2026-06-02-player-identity-identifier-redaction-evidence.json"
)
DEFAULT_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD = public_contract_decision_record.DEFAULT_RECORD
REQUIRED_INTAKE_ID = "approved_runtime_principal_lifecycle_evidence"
REQUIRED_RESOLVED_INPUT = "runtime.lifecycle_evidence"
PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA = (
    "obelisk.players-identity-runtime-principal-start-end-evidence-check.v1"
)
PRINCIPAL_START_END_RESOLVED_INPUT = "runtime.lifecycle_start_end_evidence"
PRINCIPAL_START_END_READY_SCOPE = "principal_start_end_runtime_evidence_only"
PRINCIPAL_START_END_NEXT_REVIEW_BLOCKER = "approved_runtime_evidence_missing"
PRINCIPAL_START_END_MISSING_CHECK_JOIN_BLOCKER = (
    "missing_exact_CheckJoinInProgress_1_0_session_start_rejected"
)
PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS = {
    "runtime.lifecycle_rejected_start_evidence",
    "approved_runtime_principal_lifecycle_evidence_bundle",
}
MULTI_SURFACE_BETA_CAPTURE_SCHEMAS = {
    "obelisk.multi-surface-beta-capture-plan.v1",
    "obelisk.multi-surface-beta-capture-pack.v1",
    "obelisk.multi-surface-beta-capture-plan-queue.v1",
}
MULTI_SURFACE_BETA_CAPTURE_ARTIFACT_RE = re.compile(
    r"(?:multi[._ -]?surface(?:[._ -]?(?:beta[._ -]?capture|candidate[._ -]?queue|"
    r"capture[._ -]?(?:plan|pack|queue)|plan[._ -]?queue))?|"
    r"beta[._ -]?capture(?:[._ -]?(?:plan|pack|queue|artifact|bundle|prep))?)",
    re.IGNORECASE,
)
MULTI_SURFACE_BETA_CAPTURE_FALSE_OR_ZERO_KEYS = {
    "approved_runtime_evidence_accepted",
    "approved_runtime_evidence_binding",
    "approved_runtime_evidence_binding_accepted",
    "approved_runtime_evidence_binding_ready",
    "approved_runtime_evidence_missing_cleared",
    "approved_runtime_evidence_missing_resolved",
    "approved_runtime_evidence_ready",
    "beta_capture_ready",
    "candidate_capture_evidence_ready",
    "candidate_capture_ready",
    "capture_ready",
    "clears_approved_runtime_evidence_missing",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "complete_sdk_ready",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_v1_completion",
    "debug_capture_ready",
    "dependency_chain_completion_ready",
    "evidence_bundle_accepted",
    "identity_public_contract_gate_missing_cleared",
    "identity_public_contract_gate_missing_resolved",
    "identity_public_contract_readiness",
    "identity_public_contract_ready",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_ready",
    "p0_progress",
    "p0_progress_ready",
    "public_identity_contract_readiness",
    "public_identity_contract_ready",
    "public_sdk_ready",
    "replaces_player_principal_evidence",
    "multi_surface_beta_capture_pack_runtime_evidence_ready",
    "multi_surface_beta_capture_plan_queue_runtime_evidence_ready",
    "multi_surface_beta_capture_plan_runtime_evidence_ready",
    "multi_surface_beta_capture_runtime_evidence_ready",
    "runtime_readiness",
    "runtime_ready",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "sdk_ready",
    "v1_completion",
    "v1_completion_contribution",
    "v1_completion_ready",
}
MULTI_SURFACE_BETA_CAPTURE_STATUS_KEYS = {
    "beta_capture_pack_status",
    "beta_capture_plan_status",
    "beta_capture_prep_status",
    "beta_capture_queue_status",
    "candidate_beta_capture_pack_status",
    "candidate_beta_capture_plan_status",
    "candidate_surfaces_queue_status",
    "candidate_surfaces_status",
    "capture_pack_status",
    "capture_plan_status",
    "multi_surface_beta_capture_pack_status",
    "multi_surface_beta_capture_plan_queue_queue_status",
    "multi_surface_beta_capture_plan_queue_status",
    "multi_surface_beta_capture_plan_status",
    "multi_surface_beta_capture_queue_status",
    "multi_surface_beta_capture_status",
    "multi_surface_candidate_queue_queue_status",
    "multi_surface_candidate_queue_status",
}
MULTI_SURFACE_BETA_CAPTURE_ALLOWED_STATUS_VALUES = {
    "blocked",
    "candidate_capture_pack",
    "candidate_only",
    "candidate_prep",
    "candidate_preparation",
    "dry_run_candidate_capture_pack",
    "future_capture_plan_only",
    "future_capture_target",
    "future_capture_targets_only",
    "missing",
    "not_available",
    "unavailable",
    "unresolved",
}
ZERO_OR_FALSE_READINESS_KEYS = {
    "claim_progress",
    "claim_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_progress",
    "p0_sdk_progress",
    "progress",
    "progress_contribution",
    "progress_percent",
    "progress_ratio",
    "public_sdk_progress_contribution",
    "runtime_progress_contribution",
    "sdk_p0_progress",
    "sdk_progress",
    "sdk_progress_contribution",
    "v1_completion_contribution",
}
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
DEFAULT_PLANNING_SOURCES_DIR = Path("docs/research/player-identity-planning-sources")
REQUIRED_PLANNING_SOURCE_VERIFICATION_INTAKE_ID = "source_bound_planning_manifest_verification"
REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT = "planning.source_bound_committed_manifests"
REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER = (
    "scripts/build_player_identity_planning_source_manifests.py --verify-existing-dir"
)
REQUIRED_PLANNING_SOURCE_VERIFICATION_NON_CLAIM = (
    "A valid source-bound planning manifest verification is contract-review provenance only; it does not "
    "promote public player identity, lookup, public SDK/runtime/API/ABI/header readiness, runtime authorization, "
    "permissions/admin, command/chat surfaces, or v1 completion."
)
PLANNING_SOURCE_VERIFICATION_REPORT_NON_CLAIMS = [
    "source-bound planning manifest verification is provenance-only contract-review input",
    "source-bound planning manifest verification grants no authorization or promotion",
]
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
LIVE_AUTHORIZATION_FALSE_FLAGS = (
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM = (
    "A valid approved runtime evidence manifest can resolve only the runtime lifecycle evidence input "
    "for public-contract review; it does not promote public player identity, lookup, public "
    "SDK/runtime/API/ABI/header readiness, permissions/admin, command/chat surfaces, or v1 completion."
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
DECISION_GATE_ID = "identity_public_contract_gate"
NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE = "identity_public_contract_gate_missing"
NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW = "public_header_gate_missing"
REQUIRED_REVIEWED_IDENTITY_PUBLIC_CONTRACT_SOURCE_ARTIFACTS = {
    label: {
        "path": spec["path"],
        "role": spec["role"],
        "counting_scope": public_contract_decision_record.REVIEW_ROUTE,
    }
    for label, spec in public_contract_decision_record.EXPECTED_SOURCE_ARTIFACTS.items()
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
    "runtime evidence can show logout observations; it does not prove the private logout correlation contract required before public identity promotion",
    "runtime evidence can support internal lifecycle semantics; it does not prove owner-token registration, unregister, plugin unload cleanup, or in-flight callback drain",
    "runtime evidence does not provide ABI layout tests, SDK consumer tests, or append-only compatibility rules",
    "runtime evidence does not prove process-local scope, cross-instance isolation, or cluster identity semantics",
    "runtime evidence does not authorize permissions/admin, command/chat response, player lookup, persistence, mutation, return override, or cross-process identity claims",
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_MINIMUM_GATES = {
    "privacy and redaction decision resolved",
    "principal lifetime and invalidation decision resolved",
    "private logout correlation contract resolved",
    "cross-instance/process-local scope decision resolved",
    "candidate POD payload and descriptor contract reviewed",
    "named capability and owner-token lifecycle policy reviewed",
    "ABI layout and SDK consumer tests passing",
    "public docs state exact non-claims and downstream dependency order",
}
REQUIRED_ALIAS_GUARDRAILS_FALSE = {
    "contractReviewed",
    "identityContractReady",
    "identityPublicContractReady",
    "publicIdentityReady",
    "publicPrincipalReady",
    "principalHandleAbiReady",
    "principalAbiReady",
    "principalHandleReady",
    "identityHeaderAllowed",
    "identityHeaderReady",
    "publicHeaderAllowed",
    "publicHeaderReady",
    "publicHeaderReadiness",
    "publicContractAllowed",
    "publicContractReady",
    "publicContractReadiness",
    "publicReadiness",
    "publicApiAllowed",
    "publicApiReady",
    "publicApiReadiness",
    "publicAbiAllowed",
    "publicAbiReady",
    "publicAbiReadiness",
    "publicCallbackAbiReady",
    "lookupReady",
    "lookupAllowed",
    "playerLookupReady",
    "permissionsReady",
    "permissionsAdminUnlocked",
    "permissionsAdminReady",
    "permissionsAdminPublicReady",
    "commandsReady",
    "commandResponseUnlocked",
    "commandResponseReady",
    "commandChatResponseReady",
    "commandsRepliesUnlocked",
    "commandsRepliesReady",
    "chatRepliesReady",
    "sendChatReady",
    "publicSdkReady",
    "publicSdkReadiness",
    "sdkConsumerReady",
    "sdkConsumerReadiness",
    "packageShapeReady",
    "installedSdkPackageShapeReady",
    "supportPackageReady",
    "supportTierReady",
    "betaNoticeReady",
    "betaCaptureReady",
    "runtimeEvidenceStatusReportReady",
    "statusReportReady",
    "scopedReleaseRowReady",
    "scopedReleaseStatementReady",
    "stableSdkReady",
    "stableClaimAllowed",
    "stableReleaseContractClaimAllowed",
    "principalLookupReady",
    "identityLookupReady",
    "publicLookupReady",
    "publicLookupAllowed",
    "runtimeReady",
    "runtimeReadiness",
    "runtimeReadyAlias",
    "runtimePrincipalReady",
    "promotionReady",
    "publicIdentityAllowed",
    "playerIdentityReady",
    "playerIdentityPromoted",
    "playerPrincipalReady",
    "realIdentityReady",
    "redactionEvidencePromotesIdentity",
    "v1Ready",
    "v1CompletionReady",
    "v1CompletionEvidence",
    "v1CompletionClaim",
    "publicSdkV1CompletionReady",
    "publicSdkV1CompletionClaim",
    "identityContractReviewed",
    "identityPublicContractReviewed",
    "acceptedForHeaderGateReview",
    "acceptedForPublicHeaderGateReview",
    "acceptedForPublicHeaderReview",
    "acceptedForPublicApiReview",
    "acceptedForPublicAbiReview",
    "publicHeaderGateReady",
    "publicHeaderGateUnlocked",
    "publicApiGateReady",
    "publicApiGateUnlocked",
    "publicAbiGateReady",
    "publicAbiGateUnlocked",
    "resourceHandleReady",
    "resourceHandleSupported",
    "resourceHandleAllowed",
    "completeSdkReady",
    "completeSdkReadiness",
    "completeSdkCountingAllowed",
}
OPTIONAL_ALIAS_GUARDRAILS_FALSE = {
    "broadcastReady",
    "broadcastReplyReady",
    "p0Progress",
    "p0ProgressReady",
    "p0Ready",
    "p0SdkProgress",
    "p0SdkProgressReady",
    "sdkP0Progress",
    "sdkP0ProgressReady",
    "sdkP0Ready",
    "countsTowardP0",
    "countsTowardP0DependencyChain",
    "countsTowardP0DependencyChainClaim",
    "rconReady",
    "rconCommandReady",
    "rconReplyReady",
    "pluginHubReady",
    "pluginHubPublicationReady",
    "principalStartEndReady",
    "principalStartEndRuntimeEvidenceReady",
    "runtimeLifecycleStartEndEvidenceReady",
    "startEndRuntimeEvidenceReady",
}
REQUIRED_ALIAS_GUARDRAILS_FALSE = REQUIRED_ALIAS_GUARDRAILS_FALSE | {
    "mutationAllowed",
    "mutationReady",
    "mutationSupported",
    "returnOverrideAllowed",
    "returnOverrideReady",
}
REQUIRED_ALIAS_GUARDRAILS_NON_CLAIM = (
    "Alias guardrails are false-only until identity_public_contract_gate is reviewed."
)
FORBIDDEN_APPROVED_RUNTIME_RESOLVED_INPUT_TOKENS = (
    "accepted_alias",
    "accepted-alias",
    "approved_manifest",
    "approved-manifest",
    "beta_notice",
    "beta-notice",
    "closure",
    "closure_report",
    "closure-report",
    "complete_alias",
    "complete-alias",
    "completed_alias",
    "completed-alias",
    "diagnostic",
    "executor",
    "executor_report",
    "executor-report",
    "extended_monitor",
    "extended-monitor",
    "extended_passive_monitor",
    "extended-passive-monitor",
    "monitor_log",
    "monitor-log",
    "monitor_snapshot",
    "monitor-snapshot",
    "passive",
    "passive_monitor",
    "passive-monitor",
    "beta_capture",
    "beta-capture",
    "beta_capture_pack",
    "beta-capture-pack",
    "beta_capture_plan",
    "beta-capture-plan",
    "beta_capture_queue",
    "beta-capture-queue",
    "multi_surface_beta_capture",
    "multi-surface-beta-capture",
    "multi_surface_beta_capture_pack",
    "multi-surface-beta-capture-pack",
    "multi_surface_beta_capture_plan",
    "multi-surface-beta-capture-plan",
    "multi_surface_beta_capture_plan_queue",
    "multi-surface-beta-capture-plan-queue",
    "multi_surface_candidate_queue",
    "multi-surface-candidate-queue",
    "post_reboot",
    "post-reboot",
    "post_reboot_passive_monitor",
    "post-reboot-passive-monitor",
    "ready_alias",
    "ready-alias",
    "request_pack",
    "request-pack",
    "preflight",
    "window_manifest",
    "window-manifest",
    "operator_receipt",
    "operator-receipt",
    "operator_approval_receipt",
    "operator-approval-receipt",
    "post_runtime_bridge",
    "post-runtime-bridge",
    "post_runtime_bridge_build_report",
    "post-runtime-bridge-build-report",
    "bridge_build_report",
    "bridge-build-report",
    "shutdown_worker",
    "shutdown-worker",
    "worker_shutdown",
    "worker-shutdown",
    "shutdown_report",
    "shutdown-report",
    "sidecar",
    "scoped_statement",
    "scoped-statement",
    "scoped_release_statement",
    "scoped-release-statement",
    "release_statement",
    "release-statement",
    "promotion_certificate",
    "promotion-certificate",
    "completion_certificate",
    "completion-certificate",
    "observer_env",
    "observer-env",
    "live_ops",
    "live-ops",
    "installed_runtime",
    "installed-runtime",
    "runtime_install",
    "runtime-install",
    "runtime_installed",
    "runtime-installed",
    "broadcast",
    "broadcasts",
    "broadcast-ok",
    "broadcast_ok",
    "rcon",
    "rcon-ok",
    "rcon_ok",
    "principal_start_end_runtime_evidence",
    "principal-start-end-runtime-evidence",
    "runtime_lifecycle_start_end_evidence",
    "runtime-lifecycle-start-end-evidence",
    "runtime.lifecycle_start_end_evidence",
    "lifecycle_start_end_evidence",
    "lifecycle-start-end-evidence",
    "start_end_runtime_evidence",
    "start-end-runtime-evidence",
    "start_end_only",
    "start-end-only",
    "start_only",
    "start-only",
    "end_only",
    "end-only",
    "partial",
    "partial_runtime",
    "partial-runtime",
    "runtime_partial",
    "runtime-partial",
    "copied_runtime_partial",
    "copied-runtime-partial",
    "truncated",
    "incomplete",
    "simulation",
    "simulated",
    "synthetic",
    "mock",
    "fixture",
    "next_action",
    "next-action",
    "next_actions",
    "next-actions",
    "next_action_plan",
    "next-action-plan",
    "action_plan",
    "action-plan",
    "runtime_evidence_shortcut",
    "runtime-evidence-shortcut",
    "evidence_shortcut",
    "evidence-shortcut",
    "status_artifact",
    "status-artifact",
    "status_report",
    "status-report",
    "route_status",
    "route-status",
    "runtime_status",
    "runtime-status",
    "readiness_status",
    "readiness-status",
    "p0_progress",
    "p0-progress",
    "p0_sdk_progress",
    "p0-sdk-progress",
    "sdk_p0_progress",
    "sdk-p0-progress",
    "phase0_progress",
    "phase0-progress",
    "public_header",
    "public-header",
    "public_header_gate",
    "public-header-gate",
    "public_header_gate_proposal",
    "public-header-gate-proposal",
    "public_header_proposal",
    "public-header-proposal",
    "header_gate_proposal",
    "header-gate-proposal",
    "header_proposal",
    "header-proposal",
    "confirmed_beta_notice",
    "confirmed-beta-notice",
    "copied_log_only",
    "copied-log-only",
    "cmake_package",
    "cmake-package",
    "find_package",
    "find-package",
    "source_overclaim",
    "source-overclaim",
    "source_overclaim_total_flag_count",
    "source-overclaim-total-flag-count",
    "source_overclaim_zero",
    "source-overclaim-zero",
    "package_shape",
    "package-shape",
    "installed_sdk",
    "installed-sdk",
    "plugin_hub",
    "plugin-hub",
    "support_tier",
    "support-tier",
    "release_support",
    "release-support",
)
SOURCE_PROVENANCE_NON_PROMOTIONAL_ALIAS_PATTERNS = {
    "approved_manifest_reference": re.compile(
        r"\bapproved[-_ ]+manifest(?:[-_ ]+(?:reference|artifact|shortcut))?\b",
        re.IGNORECASE,
    ),
    "beta_notice_material": re.compile(
        r"\bbeta[-_ ]+notice(?:[-_ ]+(?:prep|draft|artifact|shortcut))?\b",
        re.IGNORECASE,
    ),
    "confirmed_beta_notice_material": re.compile(
        r"\bconfirmed[-_ ]+beta[-_ ]+notice(?:[-_ ]+(?:json|artifact|manifest|report|shortcut))?\b",
        re.IGNORECASE,
    ),
    "closure_or_executor_report": re.compile(
        r"\b(?:closure|executor)[-_ ]+(?:request|report|artifact|shortcut)\b",
        re.IGNORECASE,
    ),
    "next_action_plan": re.compile(
        r"\b(?:next[-_ ]+actions?|next[-_ ]+actions?[-_ ]+plan|action[-_ ]+plan|"
        r"plan[-_ ][A-Za-z0-9_-]*next[-_ ]+actions?)"
        r"(?:[-_ ]+(?:artifact|execution|manifest|report|shortcut))?\b",
        re.IGNORECASE,
    ),
    "runtime_evidence_shortcut": re.compile(
        r"\b(?:runtime[-_ ]+(?:lifecycle[-_ ]+)?evidence|approved[-_ ]+runtime[-_ ]+evidence|"
        r"approved[-_ ]+runtime[-_ ]+bundle|runtime[-_ ]+observer[-_ ]+log)\b"
        r"[^\.;]{0,80}\b(?:alias|shortcut|substitute|reference|status|notice|plan)\b|"
        r"\b(?:alias|shortcut|substitute|reference|status|notice|plan)\b"
        r"[^\.;]{0,80}\b(?:runtime[-_ ]+(?:lifecycle[-_ ]+)?evidence|"
        r"approved[-_ ]+runtime[-_ ]+evidence|approved[-_ ]+runtime[-_ ]+bundle|"
        r"runtime[-_ ]+observer[-_ ]+log)\b",
        re.IGNORECASE,
    ),
    "principal_start_end_only_runtime_evidence": re.compile(
        r"\b(?:(?:principal|player)[-_ ]+start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?"
        r"(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:runtime[-_ ]+)?lifecycle[-_ ]+start[-_ ]+end(?:[-_ ]+"
        r"(?:evidence|artifact|report|manifest|bundle))?|"
        r"start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:start|end)[-_ ]+only(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?)\b",
        re.IGNORECASE,
    ),
    "status_artifact": re.compile(
        r"\b(?:(?:route|runtime|evidence|identity|lifecycle|public|sdk)[-_ ]+status|"
        r"status[-_ ]+(?:artifact|manifest|notice|report|shortcut|snapshot)|"
        r"(?:route|runtime|evidence|identity|lifecycle|public|sdk)[-_ ]+status[-_ ]+"
        r"(?:artifact|manifest|notice|report|shortcut|snapshot))\b",
        re.IGNORECASE,
    ),
    "partial_copied_runtime_evidence": re.compile(
        r"\b(?:copied[-_ ]+runtime(?:[-_ ]+evidence|[-_ ]+observer[-_ ]+log)?|"
        r"runtime[-_ ]+(?:observer[-_ ]+log|lifecycle[-_ ]+evidence|evidence))\b"
        r"[^\.;]{0,80}\b(?:partial|truncated|incomplete)\b|"
        r"\b(?:partial|truncated|incomplete)\b[^\.;]{0,80}\b"
        r"(?:copied[-_ ]+runtime|runtime[-_ ]+(?:observer[-_ ]+log|lifecycle[-_ ]+evidence|evidence))\b",
        re.IGNORECASE,
    ),
    "passive_extended_monitor_material": re.compile(
        r"\b(?:(?:extended[-_ ]+)?passive[-_ ]+monitor|extended[-_ ]+monitor|"
        r"monitor[-_ ]+(?:snapshot|log))(?:[-_ ]+(?:snapshot|log|artifact|report))?\b",
        re.IGNORECASE,
    ),
    "post_reboot_passive_monitor_context": re.compile(
        r"\bpost[-_ ]+reboot(?:[-_ ]+(?:passive[-_ ]+monitor|monitor|context|snapshot|log|artifact|report))?\b|"
        r"\b(?:passive[-_ ]+monitor|monitor[-_ ]+(?:context|snapshot|log))"
        r"[-_ ]+post[-_ ]+reboot\b",
        re.IGNORECASE,
    ),
    "multi_surface_beta_capture_material": MULTI_SURFACE_BETA_CAPTURE_ARTIFACT_RE,
    "post_runtime_bridge_or_shutdown_worker_artifact": re.compile(
        r"\b(?:post[-_ ]?runtime[-_ ]?bridge(?:[-_ ]?(?:build|builder|report|artifact|manifest))?|"
        r"bridge[-_ ]?(?:build|builder)[-_ ]?report|shutdown[-_ ]?worker|"
        r"worker[-_ ]?shutdown|shutdown[-_ ]?(?:report|artifact|manifest))\b",
        re.IGNORECASE,
    ),
    "copied_log_only_artifact": re.compile(
        r"\bcopied[-_ ]+log[-_ ]+only(?:[-_ ]+(?:artifact|evidence|manifest|report|shortcut))?\b|"
        r"\bcopied[-_ ]+log\b[^\.;]{0,80}\b(?:only|shortcut|substitute)\b",
        re.IGNORECASE,
    ),
    "package_shape_material": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk(?:[-_ ]+package[-_ ]+shape)?|package[-_ ]+shape)\b",
        re.IGNORECASE,
    ),
    "support_or_publication_material": re.compile(
        r"\b(?:support[-_ ]+tier|release[-_ ]+support|release[-_ ]+grade[-_ ]+support|"
        r"plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:package|support|publication|wording))?\b",
        re.IGNORECASE,
    ),
    "runtime_live_status_material": re.compile(
        r"\b(?:installed[-_ ]+runtime|runtime[-_ ]+install(?:ed)?|runtime[-_ ]+installed|"
        r"broadcasts?(?:[-_ ]+(?:ok|sent|status|notice))?|"
        r"rcon(?:[-_ ]+(?:ok|ready|reachable|command(?:s)?|service|status))?)\b",
        re.IGNORECASE,
    ),
    "source_overclaim_zero_diagnostic": re.compile(
        r"\b(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?"
        r"(?:[-_ ]+(?:total[-_ ]+flag[-_ ]+count|component[-_ ]+count|summary|diagnostics?|zero))?\b|"
        r"\bsource[-_ ]?overclaim[-_ ]?zero\b",
        re.IGNORECASE,
    ),
    "planning_artifact": re.compile(r"\bplanning(?:[-_ ]+only)?\b", re.IGNORECASE),
    "public_header_proposal_artifact": re.compile(
        r"\b(?:public[-_ ]+header(?:[-_ ]+gate)?[-_ ]+proposal|"
        r"header[-_ ]+gate[-_ ]+proposal|header[-_ ]+proposal)\b",
        re.IGNORECASE,
    ),
    "public_api_readiness_alias": re.compile(
        r"\bpublic[-_ ]+api[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "public_sdk_readiness_alias": re.compile(
        r"\bpublic[-_ ]+sdk[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "public_abi_readiness_alias": re.compile(
        r"\bpublic[-_ ]+abi[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "public_header_readiness_alias": re.compile(
        r"\bpublic[-_ ]+header[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "runtime_readiness_alias": re.compile(
        r"\bruntime[-_ ]+(?:allowed|available|complete|enabled|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "v1_completion_readiness_alias": re.compile(
        r"\bv1[-_ ]+completion[-_ ]+(?:complete|ready|readiness|satisfied)\b",
        re.IGNORECASE,
    ),
    "identity_lookup_readiness_alias": re.compile(
        r"\b(?:identity|principal|player|public)[-_ ]+lookup[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "permissions_admin_unlock_alias": re.compile(
        r"\b(?:permissions?[/_-]?admin|permissions?|admin)[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "command_response_unlock_alias": re.compile(
        r"\b(?:command[/_-]?chat[-_ ]+response|commands?[/_-]?replies|"
        r"command[-_ ]+response|chat[-_ ]+replies|send[-_ ]+chat|broadcasts?|"
        r"rcon(?:[-_ ]+commands?)?)[-_ ]+"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|readiness|"
        r"satisfied|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "runtime_authorization_alias": re.compile(
        r"\b(?:runtime[-_ ]+(?:work|capture)|live[-_ ]+ops|server[-_ ]+ops|"
        r"server[-_ ]+operations?|workspace[-_ ]+writes?)[-_ ]+"
        r"(?:allowed|authorized|authorization|enabled|ready|unlocked)\b",
        re.IGNORECASE,
    ),
    "counts_toward_alias": re.compile(
        r"\bcounts?[-_ ]+toward[-_ ]+"
        r"(?:public|runtime|sdk|v1|complete[-_ ]+sdk|public[-_ ]+(?:sdk|api|abi|header|runtime)|"
        r"v1[-_ ]+completion)\b",
        re.IGNORECASE,
    ),
    "production_sdk_readiness_alias": re.compile(
        r"\b(?:production|stable|complete)[-_ ]+sdk[-_ ]+"
        r"(?:allowed|available|claim|complete|enabled|promoted|ready|readiness|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "generic_public_contract_shortcut_alias": re.compile(
        r"\b(?:(?:identity|reviewed|public)?[-_ ]*(?:public[-_ ]+)?contract(?:[-_ ]+review)?|"
        r"identity[-_ ]+public[-_ ]+contract|public[-_ ]+contract)[-_ ]+"
        r"(?:ready|accepted|complete|completed)(?:[-_ ]+(?:alias|shortcut|artifact|manifest))?\b|"
        r"\b(?:ready|accepted|complete|completed)[-_ ]+(?:alias|shortcut)[-_ ]+"
        r"(?:identity[-_ ]+)?public[-_ ]+contract\b",
        re.IGNORECASE,
    ),
    "sdk_p0_progress_alias": re.compile(
        r"\b(?:sdk[/_-]*p0|p0[/_-]*(?:sdk)?|complete[-_ ]+sdk)[-_ ]*"
        r"(?:progress|completion|complete|ready|readiness|satisfied)\b",
        re.IGNORECASE,
    ),
}
NON_PROMOTIONAL_EVIDENCE_DENIAL = (
    "Post-reboot passive monitor context, passive or extended monitor snapshots/logs, confirmed beta "
    "notice JSON, beta notices, multi-surface beta capture plan/pack/queue artifacts, "
    "closure/executor reports, post-runtime bridge build reports, shutdown-worker artifacts, "
    "approved-manifest references, next-action plans, route/status "
    "artifacts, copied-log-only artifacts, installed runtime, broadcast, RCON, package-shape "
    "artifacts, historical handoff text, request packs, preflight/window manifests, operator "
    "receipts, and live-ops sidecars are planning or operational-preparation artifacts only; they do not "
    "resolve runtime lifecycle evidence, public identity, lookup, public API/ABI/header/SDK "
    "readiness, runtime readiness, permissions/admin, command/chat surfaces, or v1 completion."
)
REQUIRED_POST_EVIDENCE_NON_COUNTING_ARTIFACT_CLASSES = [
    "post-reboot passive monitor context",
    "passive or extended monitor snapshots/logs",
    "confirmed beta notice JSON",
    "beta notices",
    "next-action/status reports",
    "status JSON artifacts",
    "copied-log-only artifacts",
    "installed runtime, broadcast, or RCON status checks",
    "package-shape artifacts",
    "source-overclaim zero diagnostics",
    "post-runtime bridge build reports or shutdown-worker artifacts",
    "historical handoff text",
    "request/preflight/window manifests",
    "operator receipts or live-ops sidecars",
    "diagnostic-only artifacts",
    "scoped/non-complete release statements",
    "promotion or completion certificates",
    "simulation/mock/fixture artifacts",
]
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY = {
    "alias_classes": [
        "copied-log candidate aliases",
        "preflight aliases",
        "review-status aliases",
        "live-ops sidecar candidate aliases",
        "beta or confirmed-beta notice candidate aliases",
        "passive or post-reboot passive monitor candidate aliases",
        "diagnostic-only candidate aliases",
    ],
    "can_count_candidate_aliases": False,
    "can_count_preflight_aliases": False,
    "can_count_review_aliases": False,
    "can_unlock_identity_public_contract_gate_missing": False,
    "can_unlock_public_identity_contract_readiness": False,
    "can_replace_reviewed_identity_public_contract_decision_record": False,
    "accepted_for_public_header_gate_review": False,
    "p0_progress_contribution": 0,
    "non_claim": (
        "Candidate, preflight, review-status, copied-log, sidecar, beta, passive, and diagnostic "
        "aliases remain non-counting after accepted runtime evidence; they cannot unlock "
        "identity_public_contract_gate_missing, public identity contract readiness, public header "
        "review, P0 progress, or replace the hash-current reviewed identity public contract "
        "decision record."
    ),
}
REQUIRED_PLAYER_IDENTITY_P0_DEPENDENCY_CHAIN = [
    "player_identity",
    "permissions_admin",
    "command_chat_response_path",
    "commands_replies",
]
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS = [
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_readiness",
    "runtime_readiness",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "counts_toward_public_sdk",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "public_sdk_v1_completion_ready",
    "complete_sdk_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "commands_replies_ready",
    "v1_completion_evidence",
]
REQUIRED_APPROVED_RUNTIME_SOURCE_PROVENANCE_POLICY = {
    "accepted_source_kind": "runtime-observer-log",
    "resolved_source_path": "$.source_summary.evidence.sources[0].path",
    "copied_log_path": "$.operational_window.copied_log.path",
    "required_output_artifact_hash": "$.output_artifact_identity.artifact_sha256",
    "forbidden_source_classes": [
        "diagnostic-only sources",
        "passive monitor or snapshot sources",
        "post-reboot passive monitor context",
        "confirmed beta notice JSON",
        "next-action/status reports",
        "status JSON artifacts",
        "copied-log-only artifacts",
        "installed runtime, broadcast, or RCON status checks",
        "installed/package-shape artifacts",
        "source-overclaim zero diagnostics",
        "post-runtime bridge build reports or shutdown-worker artifacts",
        "historical handoff text",
        "request packs",
        "preflight or window manifests",
        "operator receipts",
        "live-ops sidecars",
        "scoped or non-complete release statements",
        "promotion or completion certificates",
        "simulation, mock, or fixture artifacts",
    ],
    "non_claim": (
        "Only the approved runtime evidence manifest's copied runtime-observer log source can resolve "
        "runtime.lifecycle_evidence for contract review; post-reboot passive monitor context, confirmed beta "
        "notice JSON, next-action/status reports, status JSON artifacts, copied-log-only artifacts, "
        "installed runtime, broadcast, RCON, installed/package-shape artifacts, source-overclaim zero diagnostics, "
        "post-runtime bridge build reports, shutdown-worker artifacts, historical handoff text, diagnostic-only, passive, "
        "request/preflight/window/receipt/sidecar/scoped-statement/certificate/simulation/mock/fixture "
        "artifacts remain non-counting and cannot open the public identity contract gate."
    ),
}
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
        "approved runtime evidence cannot set promotion_ready, public_sdk_ready, runtime_ready, public_header_allowed, public_api_ready, public_abi_ready, lookup_ready, permissions_ready, commands_ready, or v1_completion_evidence",
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
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS = [
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
]
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS = [
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
]
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS = (
    REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS
    + REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS
)
POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS = [
    "evidence.complete_non_protected_pack",
    "evidence.accepted_session_start_anchor",
    "evidence.accepted_session_end_anchor",
]
POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS = [
    key
    for key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS
    if key not in POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS
]
POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACE_GAPS = sorted(
    REQUIRED_CONTRACT_GATE_INPUTS["separation.downstream_surfaces"]["remaining_promotion_inputs"]
)
POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_BLOCKED_SURFACES = [
    "public_identity",
    "player_lookup",
    "public_api",
    "public_abi",
    "public_header",
    "runtime_readiness",
    "sdk_readiness",
    "permissions_admin",
    "command_chat_response",
    "commands_replies",
    "v1_completion",
    "p0_progress",
]
POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS = [
    "approved_runtime_principal_lifecycle_evidence_bundle",
    "reviewed_identity_public_contract_decision_record",
    "identifier_redaction_evidence",
    "principal_invalidation_policy",
    "public_abi_preflight_candidate",
    "owner_token_sdk_consumer_contract",
    "source_bound_planning_manifest_verification",
    "player_identity_public_header_gate_proposal",
]
POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS = (
    "accepted_for_public_header_gate_review",
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "runtime_readiness",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "complete_sdk_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
)
POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_REQUIRED_ITEM_FIELDS = [
    "id",
    "status",
    "checker",
    "required_next_action",
    "blocks_until",
    "review_scope",
    "counts_as_public_readiness",
    "counts_toward_public_sdk",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_contribution",
    "accepted_for_public_header_gate_review",
    "public_header_allowed",
    "promotion_ready",
    "non_claim",
]
REQUIRED_POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_NON_CLAIM = (
    "This post-runtime contract gap diagnostic is offline/fail-closed only: it identifies the "
    "hash-current reviewed identity public contract decision record and remaining decision keys after "
    "the approved runtime bundle is consumed, but it does not unlock public identity, lookup, public "
    "API/ABI/header, callbacks, capability bits, runtime readiness, SDK readiness, permissions/admin, "
    "command/chat surfaces, P0 progress, or v1 completion."
)
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM = (
    "This post-runtime identity contract checklist is routing-only: it keeps the next reviewed "
    "identity contract and public header inputs explicit after runtime evidence, but it does not "
    "unlock public identity, lookup, public API/ABI/header, callbacks, capability bits, runtime "
    "readiness, SDK readiness, permissions/admin, command/chat surfaces, P0 progress, or v1 completion."
)
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM = (
    "Checklist items are action targets only; an accepted item never opens public identity, public "
    "header/API/ABI/SDK/runtime readiness, P0 progress, or v1 completion from this route."
)
POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_POLICIES = [
    {
        "id": "approved_runtime_principal_lifecycle_evidence_bundle",
        "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
        "required_next_action": (
            "Run the strict approved runtime principal lifecycle evidence checker on a copied "
            "runtime-observer log bundle."
        ),
        "blocks_until": REQUIRED_RESOLVED_INPUT,
        "review_scope": "runtime_evidence_contract_review_input",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "reviewed_identity_public_contract_decision_record",
        "checker": "scripts/check_player_identity_public_contract_decision_record.py",
        "required_next_action": (
            "Run the decision-record checker on the bound contract-review record."
        ),
        "blocks_until": "identity_public_contract.reviewed_* contract-review decisions",
        "review_scope": public_contract_decision_record.REVIEW_ROUTE,
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "identifier_redaction_evidence",
        "checker": REQUIRED_IDENTIFIER_REDACTION_CHECKER,
        "required_next_action": (
            "Run the identifier-redaction evidence checker and keep sanitized identifiers "
            "contract-review-only."
        ),
        "blocks_until": REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT,
        "review_scope": "privacy_contract_review_input",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "principal_invalidation_policy",
        "checker": REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER,
        "required_next_action": (
            "Run the principal-invalidation policy checker for candidate generation, scope, "
            "reconnect, duplicate, stale, and logout-correlation policy review."
        ),
        "blocks_until": PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT,
        "review_scope": "candidate_policy_review_input",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "public_abi_preflight_candidate",
        "checker": REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER,
        "required_next_action": (
            "Run the public ABI preflight candidate checker for offline POD and owner-token review "
            "evidence without adding header symbols or capability bits."
        ),
        "blocks_until": REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT,
        "review_scope": "candidate_abi_preflight_review_input",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "owner_token_sdk_consumer_contract",
        "checker": REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_CHECKER,
        "required_next_action": (
            "Run the owner-token SDK consumer contract checker for candidate cleanup and lifecycle "
            "review evidence."
        ),
        "blocks_until": REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT,
        "review_scope": "candidate_owner_token_lifecycle_review_input",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "source_bound_planning_manifest_verification",
        "checker": REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER,
        "required_next_action": (
            "Verify source-bound planning manifests are current; provenance remains non-counting."
        ),
        "blocks_until": REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT,
        "review_scope": "source_bound_provenance_only",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
    {
        "id": "player_identity_public_header_gate_proposal",
        "checker": "scripts/check_player_identity_public_header_gate.py",
        "required_next_action": (
            "Prepare only a separate fail-closed public-header gate proposal after the reviewed "
            "identity contract record is accepted."
        ),
        "blocks_until": NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW,
        "review_scope": "future_public_header_gate_review_candidate_only",
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
    },
]
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY = {
    "id": "post_runtime_identity_contract_checklist",
    "status": "blocked/fail-closed-action-list",
    "active_after_resolved_input": REQUIRED_RESOLVED_INPUT,
    "current_blocker_after_resolved_input": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
    "required_item_ids": POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS,
    "items": [
        {
            **item,
            "non_claim": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM,
        }
        for item in POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_POLICIES
    ],
    "must_remain_false": list(POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS),
    "per_item_zero_progress_fields": [
        "p0_progress_contribution",
        "complete_sdk_claim_progress_contribution",
    ],
    "non_claim": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM,
}
POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_POLICY_BY_ID = {
    item["id"]: item for item in REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY["items"]
}
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS = {
    "approved_runtime_evidence_intake",
    "approved_runtime_evidence_not_sufficient",
    "contract_gate_inputs",
    "proposed_public_pod_abi_candidate",
    "required_before_public_header",
    "required_tests_before_public_header",
}
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT = {
    "id": "reviewed_identity_public_contract_decision_record",
    "status": "missing",
    "checker": "scripts/check_player_identity_public_contract_decision_record.py",
    "accepted_artifact_class": "hash-current reviewed identity public contract decision record",
    "accepted_review_route": "reviewed_identity_public_contract_review",
    "must_resolve_decision_keys": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
    "must_remain_false": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS,
    "p0_dependency_chain": REQUIRED_PLAYER_IDENTITY_P0_DEPENDENCY_CHAIN,
    "p0_progress_contribution": 0,
    "non_counting_artifact_classes": REQUIRED_POST_EVIDENCE_NON_COUNTING_ARTIFACT_CLASSES,
    "non_counting_candidate_alias_policy": (
        REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY
    ),
    "source_artifact_hash_policy": public_contract_decision_record.SOURCE_ARTIFACT_HASH_POLICY,
    "required_source_artifacts": REQUIRED_REVIEWED_IDENTITY_PUBLIC_CONTRACT_SOURCE_ARTIFACTS,
}
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION = {
    "status": "preparable_offline_not_counting",
    "active_after_resolved_input": REQUIRED_RESOLVED_INPUT,
    "blocked_until_resolved_input": REQUIRED_RESOLVED_INPUT,
    "current_blocker_before_resolved_input": "approved_runtime_evidence_missing",
    "next_blocker_after_resolved_input": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
    "checkable_artifact": (
        "docs/research/player-identity-planning-sources/"
        "reviewed-identity-public-contract-decision-record.json"
    ),
    "checker": "scripts/check_player_identity_public_contract_decision_record.py",
    "required_review_route": public_contract_decision_record.REVIEW_ROUTE,
    "must_bind_to_approved_runtime_evidence": True,
    "must_bind_current_source_artifacts": True,
    "must_remain_contract_review_only": True,
    "must_resolve_decision_keys": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
    "must_remain_false": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_STEP_FALSE_FLAGS,
    "does_not_unlock_identity_public_contract_gate": True,
    "does_not_unlock_public_header_gate": True,
    "public_header_allowed": False,
    "public_abi_ready": False,
    "public_api_ready": False,
    "public_sdk_ready": False,
    "runtime_ready": False,
    "v1_completion_evidence": False,
    "p0_progress_contribution": 0,
    "non_claim": (
        "This is offline preparation for the reviewed identity public contract record only; it remains "
        "non-counting until approved runtime lifecycle evidence resolves runtime.lifecycle_evidence and "
        "cannot unlock identity_public_contract_gate_missing, public header/API/ABI/SDK/runtime readiness, "
        "P0 progress, or v1 completion."
    ),
}
REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT = {
    "id": "player_identity_public_header_gate_proposal",
    "status": "candidate_only",
    "checker": "scripts/check_player_identity_public_header_gate.py",
    "must_remain_non_claim": True,
    "public_header_allowed": False,
}
REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_FALSE_FLAGS = (
    "accepted_decision_record_opens_public_header_gate",
    "public_header_readiness_from_decision_record",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
    "promotion_ready",
    "public_contract_allowed",
    "public_header_allowed",
    "public_abi_ready",
    "public_api_ready",
    "public_sdk_ready",
    "runtime_ready",
    "runtime_readiness",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_evidence",
    "complete_sdk_ready",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
)
REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_NON_CLAIM = (
    "An accepted strict runtime bundle plus a bound reviewed identity public contract record only "
    "makes the public header gate proposal the next auditable fail-closed artifact; it does not open "
    "the public header/API/ABI, expose callbacks or capability bits, promote the SDK/runtime, unlock "
    "lookup or downstream surfaces, or count toward SDK/P0/v1 completion."
)
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM = (
    "After approved runtime lifecycle evidence resolves runtime.lifecycle_evidence, the next blocker is "
    "identity_public_contract_gate_missing; this remains an offline reviewed public identity contract gate "
    "and cannot open public identity, lookup, public API/ABI/header, callbacks, capability bits, runtime "
    "readiness, SDK readiness, stable readiness, Plugin Hub readiness, publication, permissions/admin, "
    "command/chat surfaces, or v1 completion."
)
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "counts_toward_public_sdk",
    "counts_toward_complete_sdk_claim",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "public_sdk_v1_completion_ready",
    "complete_sdk_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "commands_replies_ready",
    "v1_completion_evidence",
)
POST_APPROVED_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS = (
    "public_contract_allowed",
    "public_readiness",
    "runtime_readiness",
    "public_api_ready",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
    "public_api_gate_ready",
    "public_api_gate_unlocked",
    "public_abi_gate_ready",
    "public_abi_gate_unlocked",
    "identity_public_contract_ready",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_unlocked",
    "public_identity_ready",
    "public_principal_ready",
    "lookup_ready",
    "lookup_allowed",
    "player_lookup_ready",
    "principal_lookup_ready",
    "public_lookup_ready",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "commands_ready",
    "command_response_ready",
    "command_response_unlocked",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "chat_replies_ready",
    "send_chat_ready",
    "broadcast_ready",
    "broadcast_reply_ready",
    "rcon_ready",
    "rcon_command_ready",
    "rcon_reply_ready",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "public_sdk_v1_completion_ready",
    "public_sdk_v1_completion_claim",
    "complete_sdk_ready",
    "complete_sdk_counting_allowed",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_v1_completion",
    "counts_toward_complete_sdk_claim",
    "counts_toward_p0_dependency_chain_claim",
    "p0_progress_ready",
    "sdk_p0_progress_ready",
    "resource_handle_ready",
    "resource_handle_supported",
    "resource_handle_allowed",
    "mutation_allowed",
    "mutation_ready",
    "return_override_allowed",
    "return_override_ready",
    "live_ops_authorized",
    "server_operations_authorized",
    "workspace_writes_authorized",
    "runtime_capture_authorized",
    "reads_live_logs",
)
IDENTITY_CONTRACT_DECISION_RECORD_SHORTCUT_FALSE_KEYS = tuple(
    dict.fromkeys(
        (
            *REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS,
            *POST_APPROVED_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS,
            "accepted_for_header_gate_review",
            "accepted_for_public_header_gate_review",
            "accepted_for_public_header_review",
            "accepted_for_public_api_review",
            "accepted_for_public_abi_review",
            "identity_contract_gate_complete",
            "identity_contract_gate_open",
            "identity_contract_gate_resolved",
            "identity_contract_gate_cleared",
            "identity_contract_gate_satisfied",
            "identity_contract_gate_accepted",
            "identity_public_contract_gate_complete",
            "public_contract_gate_complete",
            "public_header_gate_open",
            "public_header_gate_resolved",
            "public_header_gate_cleared",
            "complete_sdk_claim_progress_contribution",
            "p0_dependency_chain_claim_progress_contribution",
            "p0_dependency_chain_progress_contribution",
            "sdk_progress",
            "sdk_progress_contribution",
            "sdk_p0_progress",
            "public_sdk_progress_contribution",
            "runtime_progress_contribution",
            "progress",
            "progress_contribution",
        )
    )
)
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
REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_STATUS = "blocked/query-only-planning"
REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_POLICY = {
    "permissions/admin remains query-only planning until obelisk.player_identity.v1 is promoted",
    "the first permissions/admin public slice may only be fail-closed permission queries over copied principals",
    "permission queries must include principal_generation and principal_scope_flags or be formally callback-local only",
    "allow decisions require policy_source_id, policy_source_generation, authority_kind, authority_generation, and policy_epoch provenance",
}
REQUIRED_PERMISSIONS_ADMIN_FORBIDDEN_UNTIL_PROMOTION = {
    "permission groups",
    "admin groups",
    "grant/revoke API",
    "admin actions",
    "admin mutation",
    "permission cache ABI",
    "storage/persistence",
    "operator ingress",
    "command router",
    "command/chat response path",
    "replies/send-chat",
    "moderation authority",
    "ban/kick API",
    "allow without provenance",
    "public header permission symbols",
}
REQUIRED_PERMISSIONS_ADMIN_NON_COUNTING_ARTIFACTS = {
    "diagnostic route/gap/readiness reports",
    "passive chat parsing or plugin-local routing artifacts",
    "scoped non-complete-SDK release statements or exclusions",
    "candidate-only permissions/admin query fail-closed contracts",
    "missing, mismatched, stale, or hash-unbound promotion certificates",
}
REQUIRED_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS = {
    "schema": "obelisk.player-identity-promotion-certificate.v1",
    "surface_id": "obelisk.player_identity.v1",
    "promotion_status": "promoted",
    "v1_dependency_chain_position": 1,
    "required_by_surface": "obelisk.permissions_admin.v1",
    "required_by_v1_dependency_chain_position": 2,
    "required_reviewed_artifact_hash": "evidence.reviewed_surface_record_sha256",
    "reviewed_artifact_hash_policy": (
        "must match the reviewed identity surface record hash carried by the certificate"
    ),
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
    "blocker_resolved",
    "contract_review_only",
    "contract_review_ready",
    "contract_reviewed",
    "contract_record_contract_review_only",
    "identity_contract_ready",
    "identity_contract_current",
    "identity_contract_decision_record_contract_review_only",
    "identity_contract_decision_record_current",
    "identity_contract_decision_record_hash_current",
    "identity_contract_decision_record_reviewed",
    "identity_contract_reviewed",
    "identity_header_allowed",
    "identity_header_ready",
    "identity_lookup_allowed",
    "identity_lookup_ready",
    "identity_public_contract_ready",
    "identity_public_contract_current",
    "identity_public_contract_hash_current",
    "identity_public_contract_decision_record_contract_review_only",
    "identity_public_contract_decision_record_current",
    "identity_public_contract_decision_record_hash_current",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_record_contract_review_only",
    "identity_public_contract_record_current",
    "identity_public_contract_record_hash_current",
    "identity_public_contract_record_reviewed",
    "identity_public_contract_gate_ready",
    "identity_public_contract_gate_reviewed",
    "identity_public_contract_gate_unlocked",
    "identity_public_contract_gate_open",
    "identity_public_contract_gate_resolved",
    "identity_public_contract_gate_cleared",
    "identity_public_contract_gate_satisfied",
    "identity_public_contract_gate_accepted",
    "identity_public_contract_gate_missing_resolved",
    "identity_public_contract_gate_missing_cleared",
    "identity_public_contract_reviewed",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "lookup_ready",
    "command_response_ready",
    "command_chat_response_ready",
    "command_response_unlocked",
    "commands_ready",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "chat_replies_ready",
    "send_chat_ready",
    "derived_readiness",
    "helper_derived_readiness",
    "helper_derived_ready",
    "helper_readiness",
    "helper_ready",
    "header_shape_valid",
    "identity_contract_hash_current",
    "player_identity_promoted",
    "player_identity_ready",
    "api_readiness",
    "abi_layout_readiness",
    "public_abi_readiness",
    "public_api_allowed",
    "public_api_readiness",
    "public_api_ready",
    "public_contract_ready",
    "public_contract_readiness",
    "public_header_readiness",
    "public_surface_status",
    "lookup_allowed",
    "player_lookup_allowed",
    "player_lookup_ready",
    "principal_lookup_allowed",
    "public_lookup_allowed",
    "public_lookup_ready",
    "public_readiness",
    "public_sdk_readiness",
    "production_sdk_claim",
    "production_sdk_claim_allowed",
    "production_sdk_ready",
    "production_sdk_readiness",
    "sdk_consumer_ready",
    "public_principal_ready",
    "player_principal_ready",
    "principal_abi_ready",
    "principal_handle_abi_ready",
    "principal_handle_ready",
    "principal_lookup_ready",
    "promotion",
    "promotion_ready",
    "runtime_readiness",
    "runtime_work_allowed",
    "runtime_work_authorization",
    "runtime_work_authorized",
    "runtime_capture_allowed",
    "runtime_capture_authorization",
    "runtime_capture_authorized",
    "runtime_principal_ready",
    "runtime_ready_alias",
    "source_ready",
    "sdk_consumer_readiness",
    "public_identity_allowed",
    "public_identity_ready",
    "public_sdk_ready",
    "runtime_ready",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_release_contract_claim_allowed",
    "stable_sdk_claim",
    "stable_sdk_claim_allowed",
    "stable_sdk_ready",
    "stable_sdk_readiness",
    "support_tier_activation_allowed",
    "support_tier_ready",
    "release_support_available",
    "release_support_ready",
    "package_shape_available",
    "package_shape_ready",
    "installed_sdk_package_shape_available",
    "installed_sdk_package_shape_ready",
    "cmake_package_ready",
    "find_package_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "approved_runtime_principal_lifecycle_bundle_routes_to",
    "approved_runtime_principal_lifecycle_bundle_next_blocker",
    "approved_runtime_lifecycle_bundle_routes_to",
    "approved_runtime_lifecycle_bundle_next_blocker",
    "runtime_lifecycle_evidence_routes_to",
    "runtime_lifecycle_evidence_next_blocker",
    "approved_runtime_evidence_routes_to",
    "approved_runtime_evidence_next_blocker",
    "principal_start_end_ready",
    "principal_start_end_runtime_evidence_ready",
    "runtime_lifecycle_start_end_evidence_ready",
    "start_end_runtime_evidence_ready",
    "lifecycle_start_end_evidence_ready",
    "broadcast_ready",
    "broadcast_reply_ready",
    "rcon_ready",
    "rcon_command_ready",
    "rcon_reply_ready",
    "live_ops_allowed",
    "live_ops_authorization",
    "live_ops_authorized",
    "server_ops_allowed",
    "server_ops_authorized",
    "server_operations_allowed",
    "server_operations_authorization",
    "server_operations_authorized",
    "workspace_write_allowed",
    "workspace_write_authorization",
    "workspace_write_authorized",
    "workspace_writes_allowed",
    "workspace_writes_authorization",
    "workspace_writes_authorized",
    "complete_sdk_counting_allowed",
    "complete_sdk_progress",
    "complete_sdk_ready",
    "complete_sdk_readiness",
    "counts_toward_completion",
    "counts_toward_public",
    "counts_toward_public_abi",
    "counts_toward_public_api",
    "counts_toward_public_header",
    "counts_toward_public_runtime",
    "counts_toward_public_sdk",
    "counts_toward_runtime",
    "counts_toward_sdk",
    "counts_toward_sdk_v1",
    "counts_toward_v1",
    "counts_toward_v1_completion",
    "public_counting_allowed",
    "runtime_counting_allowed",
    "sdk_counting_allowed",
    "v1_counting_allowed",
    "public_header_allowed",
    "public_header_ready",
    "public_contract_allowed",
    "public_contract_decision_record_contract_review_only",
    "public_contract_decision_record_current",
    "public_contract_decision_record_hash_current",
    "public_contract_decision_record_reviewed",
    "public_contract_record_current",
    "public_contract_gate_ready",
    "public_contract_gate_reviewed",
    "public_contract_gate_unlocked",
    "public_header_gate_ready",
    "public_header_gate_unlocked",
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
    "public_abi_ready",
    "public_identity_contract_current",
    "public_identity_contract_hash_current",
    "public_identity_contract_reviewed",
    "hash_current_identity_contract_decision_record",
    "hash_current_identity_public_contract_decision_record",
    "hash_current_public_contract_decision_record",
    "reviewed_identity_contract",
    "reviewed_identity_contract_hash_current",
    "reviewed_identity_contract_decision_record",
    "reviewed_identity_public_contract",
    "reviewed_identity_public_contract_current",
    "reviewed_identity_public_contract_hash_current",
    "reviewed_identity_public_contract_contract_review_only",
    "reviewed_identity_public_contract_record",
    "reviewed_identity_public_contract_record_hash_current",
    "reviewed_identity_public_contract_decision_record",
    "reviewed_identity_public_contract_decision_record_contract_review_only",
    "public_sdk_v1_completion_claim",
    "public_sdk_v1_completion_ready",
    "p0_progress",
    "p0_progress_ready",
    "p0_ready",
    "p0_unlocked",
    "p0_sdk_progress",
    "p0_sdk_progress_ready",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_p0_ready",
    "real_identity_ready",
    "redaction_evidence_promotes_identity",
    "resource_handle_allowed",
    "resource_handle_ready",
    "resource_handle_supported",
    "mutation_allowed",
    "mutation_ready",
    "mutation_supported",
    "return_override_allowed",
    "return_override_ready",
    "v1_completion_claim",
    "v1_completion_ready",
    "v1_completion_evidence",
    "v1_ready",
} | MULTI_SURFACE_BETA_CAPTURE_FALSE_OR_ZERO_KEYS | MULTI_SURFACE_BETA_CAPTURE_STATUS_KEYS
EMPTY_PUBLIC_LIST_KEYS = {
    "callback_abi",
    "callback_symbols",
    "capability_bits",
    "header_symbols",
    "public_callback_abi",
    "public_header_symbols_now",
    "public_header_symbols",
    "public_capability_bits",
    "public_capability_bits_now",
    "public_callbacks",
    "public_callback_abi_now",
    "public_api_symbols",
    "public_api_symbols_now",
    "public_api_symbol_list",
    "public_symbol_list",
    "public_symbol_names",
    "public_symbols",
}
SPLIT_CLAIM_NAME_KEYS = {
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
    "property",
    "properties",
}
SPLIT_CLAIM_VALUE_KEYS = {
    "accepted",
    "allowed",
    "complete",
    "completed",
    "enabled",
    "readiness",
    "ready",
    "state",
    "states",
    "status",
    "statuses",
    "value",
    "values",
}
NON_PROMOTIONAL_CLAIM_VALUE_TOKENS = {
    "",
    "blocked",
    "empty",
    "false",
    "missing",
    "no",
    "none",
    "not_available",
    "unavailable",
    "unresolved",
}
NON_FALSE_READINESS_ALIAS_KEYS = {
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
NON_CLAIM_CONTAINER_PATH_FRAGMENTS = (
    ".blocker_details",
    ".blockers",
    ".does_not_resolve",
    ".exclusions",
    ".forbidden_now",
    ".minimum_additional_gates",
    ".must_remain_false",
    ".must_remain_blocked",
    ".negative_consumer_rules",
    ".non_claim",
    ".non_claims",
    ".non_counting_artifacts",
    ".non_counting_artifact_classes",
    ".p0_dependency_chain",
    ".remaining_blockers",
    ".remaining_promotion_inputs",
)
ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS = {
    "approved_runtime_evidence_present",
    "complete_accepted_lifecycle_role_triplet_present",
    "runtime_evidence_ready",
}
APPROVED_RUNTIME_FALSE_PROMOTION_KEYS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_contract_allowed",
    "public_readiness",
    "public_api_allowed",
    "public_api_ready",
    "public_api_readiness",
    "public_abi_ready",
    "public_abi_readiness",
    "public_header_ready",
    "public_header_readiness",
    "lookup_allowed",
    "lookup_ready",
    "identity_lookup_allowed",
    "identity_lookup_ready",
    "principal_lookup_allowed",
    "principal_lookup_ready",
    "public_lookup_allowed",
    "public_lookup_ready",
    "permissions_ready",
    "permissions_admin_ready",
    "permissions_admin_public_ready",
    "permissions_admin_unlocked",
    "command_response_ready",
    "command_chat_response_ready",
    "command_response_unlocked",
    "commands_ready",
    "commands_replies_ready",
    "commands_replies_unlocked",
    "broadcast_ready",
    "broadcast_reply_ready",
    "rcon_ready",
    "rcon_command_ready",
    "rcon_reply_ready",
    "sdk_consumer_ready",
    "sdk_consumer_readiness",
    "complete_sdk_counting_allowed",
    "complete_sdk_claim_progress_contribution",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "complete_sdk_ready",
    "complete_sdk_readiness",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
    "counts_as_approved_runtime_evidence",
    "counts_as_runtime_evidence",
    "p0_progress",
    "p0_progress_ready",
    "p0_ready",
    "p0_dependency_chain_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_sdk_progress",
    "p0_sdk_progress_ready",
    "sdk_progress",
    "sdk_progress_contribution",
    "source_ready",
    "source_supported",
    "source_overclaim_total_flag_count",
    "source_overclaim_component_count",
    "side_lane_source_overclaim_total_flag_count",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_p0_ready",
    "public_sdk_v1_completion_ready",
    "public_sdk_v1_completion_claim",
    "v1_completion_ready",
    "v1_completion_evidence",
    "v1_ready",
    "runtime_readiness",
    "runtime_ready_alias",
    "runtime_work_allowed",
    "runtime_work_authorized",
    "runtime_capture_allowed",
    "runtime_capture_authorized",
    "live_ops_allowed",
    "live_ops_authorized",
    "server_ops_allowed",
    "server_ops_authorized",
    "server_operations_allowed",
    "server_operations_authorized",
    "workspace_write_allowed",
    "workspace_write_authorized",
    "workspace_writes_allowed",
    "workspace_writes_authorized",
    "resource_handle_allowed",
    "resource_handle_ready",
    "resource_handle_supported",
    "mutation_allowed",
    "mutation_ready",
    "mutation_supported",
    "return_override_allowed",
    "return_override_ready",
)
PRINCIPAL_START_END_RUNTIME_REQUIRED_FALSE_KEYS = (
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
    "public_abi_ready",
    "public_api_ready",
    "public_header_allowed",
    "public_sdk_ready",
    "runtime_ready",
    "lookup_ready",
    "permissions_ready",
    "commands_ready",
    "v1_completion_ready",
    "stable_claim_allowed",
    "publication_authorized",
)
PRINCIPAL_START_END_RUNTIME_OPTIONAL_FALSE_KEYS = (
    *APPROVED_RUNTIME_FALSE_PROMOTION_KEYS,
    "approved_runtime_evidence",
    "approved_runtime_evidence_present",
    "approved_runtime_evidence_ready",
    "counts_as_approved_runtime_evidence",
)
APPROVED_RUNTIME_REPORT_EXPLICIT_FALSE_KEYS = {
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
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"redact(?:ed|ion)?|excludes?|exclusion|after|before|without|until|missing|blocked|blocker|unavailable|"
    r"must[_ -]?not[_ -]?expose|no_)\b",
    re.IGNORECASE,
)
APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE = re.compile(
    r"(?:"
    r"public|sdk|abi|capability|callback|header|identity|principal|permission|admin|runtime|stable|"
    r"command|chat|reply|lookup|storage|persist|mutation|return[_ -]?override|resource[_ -]?handle|"
    r"v1|p0|phase[_ -]?0"
    r").*(?:ready|readiness|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|complete|"
    r"satisfied|passed|passing|supported|available|progress|counting)"
    r"|(?:ready|readiness|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|complete|"
    r"satisfied|passed|passing|supported|available|progress|counting).*"
    r"(?:public|sdk|abi|identity|principal|permission|admin|command|chat|reply|lookup|storage|persist|mutation|"
    r"runtime|stable|return[_ -]?override|resource[_ -]?handle|v1|p0|phase[_ -]?0)",
    re.IGNORECASE,
)
NON_PROMOTIONAL_PROVENANCE_CONTEXT_KEYS = {
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
NON_PROMOTIONAL_PROVENANCE_CONTEXT_TERMS = {
    "accepted_runtime_evidence",
    "approved_runtime_evidence",
    "broadcast",
    "identity_public_contract_decision_record",
    "installed_runtime",
    "lifecycle_start_end_evidence",
    "principal_start_end_runtime_evidence",
    "public_contract_decision_record",
    "rcon",
    "reviewed_hash_current_contract_review_only",
    "reviewed_identity_public_contract",
    "runtime_lifecycle_start_end_evidence",
    "runtime_install",
    "runtime_installed",
    "runtime_start_end_evidence",
    "route_snapshot",
    "start_end_runtime_evidence",
}
NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS = SPLIT_CLAIM_VALUE_KEYS | {
    "source_accepted",
    "source_outcome",
    "source_ready",
    "source_result",
    "source_state",
    "source_status",
    "source_supported",
}
NON_PROMOTIONAL_PROVENANCE_PROGRESS_ALIAS_RE = re.compile(
    r"(?:^|_)(?:"
    r"claim_progress|credit|credited|progress|progress_contribution|progress_percent|"
    r"progress_ratio|readiness_credit|sdk_credit|sdk_completion_credit|"
    r"v1_completion_credit|public_sdk_credit|counts?(?:_towards?|_toward|_as)?"
    r")(?:_|$)"
)
APPROVED_RUNTIME_REPORT_OVERCLAIM_VALUE_PATTERNS = {
    "public_identity_ready": re.compile(r"public\s+(?:player\s+)?identity\s+(?:is\s+)?ready", re.IGNORECASE),
    "public_principal_ready": re.compile(r"public\s+(?:player\s+)?principal\s+(?:is\s+)?ready", re.IGNORECASE),
    "real_identity_ready": re.compile(r"real\s+(?:player\s+)?identity\s+(?:is\s+)?ready", re.IGNORECASE),
    "principal_lookup_ready": re.compile(r"(?:principal|player)\s+lookup\s+(?:is\s+)?ready", re.IGNORECASE),
    "redaction_evidence_promotes_identity": re.compile(
        r"redaction\s+evidence\s+promotes?\s+(?:public\s+)?(?:player\s+)?identity",
        re.IGNORECASE,
    ),
    "identity_contract_decision_record_reviewed": re.compile(
        r"\b(?:reviewed[-_ ]+|accepted[-_ ]+|hash[-_ ]+current[-_ ]+|current[-_ ]+)?"
        r"identity[-_ ]+(?:public[-_ ]+)?contract[-_ ]+(?:decision[-_ ]+)?record\b"
        r"[^.;\n]{0,80}\b(?:reviewed|accepted|current|valid|ready|complete|satisfied)\b",
        re.IGNORECASE,
    ),
    "public_sdk_ready": re.compile(r"public\s+sdk\s+(?:is\s+)?ready", re.IGNORECASE),
    "public_abi_ready": re.compile(r"public\s+abi\s+(?:is\s+)?ready", re.IGNORECASE),
    "public_api_ready": re.compile(
        r"public\s+api\s+(?:is\s+)?"
        r"(?:allowed|available|complete|enabled|exposed|promoted|ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "runtime_work_authorized": re.compile(
        r"\bruntime[-_ ]+(?:work|capture)\b[^.;\n]{0,80}\b"
        r"(?:allowed|authorized|available|enabled|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "operations_authorized": re.compile(
        r"\b(?:live[-_ ]+ops|server[-_ ]+(?:ops|operations?)|workspace[-_ ]+writes?)\b"
        r"[^.;\n]{0,80}\b"
        r"(?:allowed|authorized|available|enabled|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "runtime_live_status_ready": re.compile(
        r"\b(?:installed[-_ ]+runtime|runtime[-_ ]+install(?:ed)?|runtime[-_ ]+installed|"
        r"broadcasts?|rcon)\b[^.;\n]{0,80}\b"
        r"(?:allowed|available|complete|enabled|live|ok|operational|passed|ready|"
        r"reachable|sent|sent[-_ ]+ok|supported|unlocked)",
        re.IGNORECASE,
    ),
    "counts_toward_promotion": re.compile(
        r"\bcounts?[-_ ]+toward[-_ ]+"
        r"(?:public|runtime|sdk|v1|complete[-_ ]+sdk|public[-_ ]+(?:sdk|api|abi|header|runtime)|"
        r"v1[-_ ]+completion)\b",
        re.IGNORECASE,
    ),
    "production_sdk_ready": re.compile(
        r"\b(?:production|stable|complete)[-_ ]+sdk\b[^.;\n]{0,80}\b"
        r"(?:allowed|available|claim(?:ed)?|complete|enabled|promoted|ready|readiness|supported|unlocked)",
        re.IGNORECASE,
    ),
    "sdk_p0_progress": re.compile(
        r"\b(?:sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|complete[/ _-]*sdk)"
        r"[/ _-]*(?:progress|completion|readiness)?\b[^.;\n]{0,80}\b"
        r"(?:allowed|available|complete|counting|enabled|passed|passing|promoted|ready|satisfied|unlocked)",
        re.IGNORECASE,
    ),
    "v1_completion_ready": re.compile(r"v1\s+(?:sdk\s+)?completion\s+(?:is\s+)?ready", re.IGNORECASE),
    "stable_claim_allowed": re.compile(
        r"\bstable[-_ ]+claim\s+(?:is\s+)?"
        r"(?:allowed|available|enabled|granted|ready|supported|unlocked)\b",
        re.IGNORECASE,
    ),
    "capability_available": re.compile(r"(?:identity\s+)?capability\s+(?:bit\s+)?(?:is\s+)?available", re.IGNORECASE),
    "downstream_unlocked": re.compile(
        r"(?:identity|principal).*unlock(?:s|ed)?\s+(?:permission|admin|command|chat|reply|lookup|storage)",
        re.IGNORECASE,
    ),
    "lookup_allowed": re.compile(r"(?:player\s+)?lookup\s+(?:is\s+)?allowed", re.IGNORECASE),
    "mutation_allowed": re.compile(r"mutation\s+(?:is\s+)?allowed", re.IGNORECASE),
    "public_mutable_resource_available": re.compile(
        r"\b(?:mutable|mutating|writable|writeable)\s+(?:identity|principal|player[-_ ]+identity|resource)"
        r"[^\.;]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)|"
        r"\b(?:identity|principal|player[-_ ]+identity|resource)[-_ ]+mutation\b"
        r"[^\.;]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "return_override_allowed": re.compile(r"return[_ -]?override\s+(?:is\s+)?allowed", re.IGNORECASE),
    "resource_handle_supported": re.compile(
        r"resource[_ -]?handle\s+(?:is\s+)?"
        r"(?:available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "contract_review_metadata_public_readiness": re.compile(
        r"\b(?:reviewed[-_ ]+hash[-_ ]+current[-_ ]+contract[-_ ]+review[-_ ]+only|"
        r"hash[-_ ]+current[-_ ]+(?:identity[-_ ]+)?(?:public[-_ ]+)?contract[-_ ]+"
        r"(?:decision[-_ ]+)?record|contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record)\b[^.;\n]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^.;\n]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
    "contract_review_artifact_p0_unlock": re.compile(
        r"\b(?:approved[-_ ]+runtime(?:[-_ ]+principal[-_ ]+lifecycle)?[-_ ]+evidence|"
        r"runtime[-_ ]+lifecycle[-_ ]+evidence|identifier[-_ ]+redaction(?:[-_ ]+evidence)?|"
        r"principal[-_ ]+invalidation(?:[-_ ]+policy)?|private[-_ ]+pod[-_ ]+layout(?:[-_ ]+candidate)?|"
        r"public[-_ ]+abi[-_ ]+preflight(?:[-_ ]+candidate)?|"
        r"owner[-_ ]+token[-_ ]+sdk[-_ ]+consumer(?:[-_ ]+contract)?|"
        r"(?:reviewed[-_ ]+)?identity[-_ ]+public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"public[-_ ]+contract[-_ ]+decision[-_ ]+record|"
        r"contract[-_ ]+review[-_ ]+only[-_ ]+(?:record|artifact)|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?|"
        r"public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|header[-_ ]+shape)\b"
        r"[^.;\n]{0,100}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?)\b[^.;\n]{0,100}\b"
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
    "opaque_principal_promoted": re.compile(
        r"\b(?:copied[-_ ]+)?opaque[-_ ]+(?:player[-_ ]+)?principal\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "principal_generation_ready": re.compile(
        r"\bprincipal[-_ ]+generation\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "privacy_redaction_ready": re.compile(
        r"\b(?:identifier[-_ ]+redaction|privacy[-_ ]+redaction|privacy\s+and\s+redaction)\b"
        r"[^.;\n]{0,80}\b(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "real_identifier_exposed": re.compile(
        r"\b(?:real[-_ ]+identifiers?|platform[-_ ]+account[-_ ]+ids?|steamid|steam[-_ ]+id|"
        r"eos[-_ ]+id|uniquenetid|playerdataid|player[-_ ]+names?|tribe[-_ ]+(?:ids?|identifiers?)|"
        r"network[-_ ]+addresses?|ip[-_ ]+addresses?)\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|public|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "permissions_admin_ready": re.compile(
        r"\b(?:permissions?[/ _-]?admin|permission[-_ ]+query|permission[-_ ]+cache|"
        r"admin[-_ ]+mutation)\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "commands_ready": re.compile(
        r"\b(?:command[/ _-]?chat[-_ ]+response|commands?[/ _-]?replies|command[-_ ]+response|"
        r"command[-_ ]+router|send[-_ ]+chat|broadcasts?|rcon(?:[-_ ]+commands?)?)\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "lookup_ready": re.compile(
        r"\b(?:player[-_ ]+lookup|principal[-_ ]+lookup|lookup[-_ ]+api|lookup[-_ ]+handle|lookup)"
        r"\b[^.;\n]{0,80}\b(?:allowed|available|enabled|exposed|promoted|public|ready|supported|unlocked)",
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
    "public_abi_identity_handle_before_resource_handle": re.compile(
        r"\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b[^.;\n]{0,120}\b"
        r"(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^.;\n]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^.;\n]{0,80}\bResourceHandle\b|"
        r"\b(?:player|identity|principal)[-_ ]+(?:handles?|lookup|resolver|resolve|resolution|resource[-_ ]+handles?)\b"
        r"[^.;\n]{0,120}\bpublic[-_ ]+(?:abi|api|header|contract|callback[-_ ]+abi)\b"
        r"[^.;\n]{0,120}\b(?:before|without|ahead[-_ ]+of|prior[-_ ]+to)\b[^.;\n]{0,80}\bResourceHandle\b",
        re.IGNORECASE,
    ),
    "readiness_noun_overclaim": re.compile(
        r"\b(?:public[-_ ]+(?:sdk|api|abi|header|contract)?[-_ ]*readiness|runtime[-_ ]+readiness|"
        r"sdk[-_ ]+consumer[-_ ]+tests?|abi[-_ ]+layout[-_ ]+tests?)\b"
        r"[^.;\n]{0,80}\b(?:allowed|available|complete|enabled|exposed|passed|passing|promoted|"
        r"ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "non_counting_artifact_public_readiness_or_p0": re.compile(
        r"\b(?:post[-_ ]+reboot(?:[-_ ]+(?:passive[-_ ]+monitor|context|snapshot|log|artifact|report))?|"
        r"(?:post[-_ ]+reboot[-_ ]+)?passive[-_ ]+monitor(?:[-_ ]+context)?|"
        r"installed[-_ ]+runtime(?:[-_ ]+(?:check|status|ready|ok))?|runtime[-_ ]+install(?:ed)?(?:[-_ ]+(?:check|status|ready|ok))?|"
        r"broadcasts?(?:[-_ ]+(?:check|ok|sent|status|notice))?|rcon(?:[-_ ]+(?:check|ok|ready|reachable|status|service|command(?:s)?))?|"
        r"(?:principal|player)[-_ ]+start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:runtime[-_ ]+)?lifecycle[-_ ]+start[-_ ]+end(?:[-_ ]+(?:evidence|artifact|report|manifest|bundle))?|"
        r"start[-_ ]+end(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"(?:start|end)[-_ ]+only(?:[-_ ]+(?:runtime[-_ ]+)?(?:evidence|artifact|report|manifest|bundle))?|"
        r"multi[-_ ]?surface(?:[-_ ]+(?:beta[-_ ]+capture|candidate[-_ ]+queue|"
        r"capture[-_ ]+(?:plan|pack|queue)|plan[-_ ]+queue))?|"
        r"beta[-_ ]+capture(?:[-_ ]+(?:plan|pack|queue|artifact|bundle|prep))?|"
        r"confirmed[-_ ]+beta[-_ ]+notice(?:[-_ ]+json)?|beta[-_ ]+notice(?:[-_ ]+json)?|"
        r"copied[-_ ]+log(?:[-_ ]+only)?(?:[-_ ]+(?:artifact|evidence|manifest|report|shortcut|candidate[-_ ]+alias|alias))?|"
        r"post[-_ ]?runtime[-_ ]?bridge(?:[-_ ]?(?:build|builder|report|artifact|manifest))?|"
        r"bridge[-_ ]?(?:build|builder)[-_ ]?report|shutdown[-_ ]?worker|worker[-_ ]?shutdown|"
        r"shutdown[-_ ]?(?:report|artifact|manifest)|"
        r"(?:live[-_ ]+ops[-_ ]+)?sidecar(?:[-_ ]+(?:artifact|manifest|report|candidate[-_ ]+alias|alias))?|"
        r"diagnostic(?:[-_ ]+only)?(?:[-_ ]+(?:artifact|manifest|report|candidate[-_ ]+alias|alias))?|"
        r"(?:side[-_ ]?lane[-_ ]?)?source[-_ ]?overclaim(?:ed|s)?(?:[-_ ]+(?:total[-_ ]+flag[-_ ]+count|"
        r"component[-_ ]+count|summary|diagnostics?|zero))?|source[-_ ]?overclaim[-_ ]?zero|"
        r"(?:copied[-_ ]+log|sidecar|beta[-_ ]+notice|beta[-_ ]+capture|"
        r"multi[-_ ]+surface[-_ ]+beta[-_ ]+capture|passive[-_ ]+monitor|diagnostic)"
        r"[-_ ]+candidate[-_ ]+aliases?|"
        r"next[-_ ]+actions?(?:[-_ ]+(?:plan|status|report|artifact))?|"
        r"(?:route|runtime|evidence|identity|lifecycle|public|sdk)[-_ ]+status"
        r"(?:[-_ ]+(?:report|artifact|manifest|notice|snapshot))?|"
        r"copied[-_ ]+log[-_ ]+only(?:[-_ ]+(?:artifact|evidence|manifest|report|shortcut))?)\b"
        r"[^.;\n]{0,120}\b(?:counts?[-_ ]+toward|credits?|contributes?|unlocks?|opens?|"
        r"allows?|enables?|satisf(?:ies|y)|resolves?|marks?|sets?|promotes?|ready|readiness|"
        r"complete|progress)\b[^.;\n]{0,120}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"identity[-_ ]+public[-_ ]+contract[-_ ]+gate[-_ ]+missing|"
        r"sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|p0[-_ ]+dependency[-_ ]+chain|"
        r"dependency[-_ ]+chain|complete[-_ ]+sdk|runtime[-_ ]+readiness|"
        r"approved[-_ ]+runtime[-_ ]+evidence(?:[-_ ]+binding)?|runtime\.lifecycle_evidence|"
        r"v1[-_ ]+completion|"
        r"obelisk\.player_identity\.v1)?",
        re.IGNORECASE,
    ),
    "helper_derived_readiness": re.compile(
        r"\b(?:helper[-_ ]+derived[-_ ]+readiness|helper[-_ ]+readiness|derived[-_ ]+readiness)\b"
        r"[^.;\n]{0,80}\b(?:allowed|available|complete|enabled|exposed|passed|passing|promoted|"
        r"ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "public_readiness_gate": re.compile(r"\bpublic[-_ ]+readiness\b", re.IGNORECASE),
}
PUBLIC_TEXT_OVERCLAIM_PATTERNS = {
    **APPROVED_RUNTIME_REPORT_OVERCLAIM_VALUE_PATTERNS,
    "public_header_ready": re.compile(
        r"\bpublic[-_ ]+header(?:[-_ ]+symbols?)?\s+(?:is\s+|are\s+)?"
        r"(?:allowed|available|ready|exposed|promoted|enabled|unlocked|supported)",
        re.IGNORECASE,
    ),
    "public_callback_abi": re.compile(
        r"\b(?:public[-_ ]+)?callback[-_ ]+abi\s+(?:is\s+)?"
        r"(?:available|ready|exposed|promoted|enabled|supported)",
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
    "runtime_ready": re.compile(
        r"\bruntime\s+(?:is\s+)?(?:ready|enabled|authorized|available|promoted|supported)",
        re.IGNORECASE,
    ),
    "promotion_ready": re.compile(
        r"\bpromotion\s+(?:is\s+)?(?:ready|authorized|complete|available)",
        re.IGNORECASE,
    ),
    "player_identity_promoted": re.compile(r"\b(?:promotes?|promoted)\s+obelisk\.player_identity\.v1\b", re.IGNORECASE),
    "public_capability_symbol": re.compile(r"\bOBELISK_API_CAPABILITY_PLAYER[A-Z0-9_]*\b"),
    "public_player_header_symbol": re.compile(
        r"\b(?:ObeliskPlayer[A-Za-z0-9_]*|RegisterPlayer[A-Za-z0-9_]*)\b"
    ),
    "source_artifact_ready_alias": re.compile(
        r"\b(?:public[-_ ]+sdk|public[-_ ]+api|public[-_ ]+header|public[-_ ]+abi|callback[-_ ]+abi|"
        r"capability[-_ ]+bits?|runtime|promotion|stable[-_ ]+claim|v1[-_ ]+completion|"
        r"public[-_ ]+readiness)[-_ ]+"
        r"(?:ready|readiness|allowed|available|enabled|promoted|complete|exposed|satisfied|passed|passing)\b",
        re.IGNORECASE,
    ),
    "header_shape_public_readiness_shortcut": re.compile(
        r"\b(?:header[-_ ]+shape|public[-_ ]+header[-_ ]+proposal(?:[-_ ]+shape)?|"
        r"proposal[-_ ]+only[-_ ]+header[-_ ]+gate(?:[-_ ]+shape)?)\b[^.;\n]{0,100}\b"
        r"(?:marks?|sets?|treats?|validates?|certif(?:ies|y|ied)|approv(?:es|ed)|"
        r"clear(?:s|ed)|unblock(?:s|ed)|opens?|allows?|enables?|satisf(?:ies|y)|resolves?)\b"
        r"[^.;\n]{0,100}\b(?:public[-_ ]+(?:identity|principal|contract|header|api|abi|sdk|readiness)|"
        r"runtime[-_ ]+readiness|v1[-_ ]+completion|promotion|obelisk\.player_identity\.v1)\b",
        re.IGNORECASE,
    ),
}
NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES = (
    ".private_pod_layout_candidate.accepted_for_contract_review",
    ".identifier_redaction_evidence.accepted_for_contract_review",
)
PUBLIC_HEADER_IDENTITY_IDENTIFIER_RE = re.compile(
    r"identity|principal|steam_?id|steamid|"
    r"player_?(?:id|handle|data_?id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player|platform.*id|account.*id|"
    r"resource_?(?:handle|id|ref|reference|token)|object_?(?:handle|id|identity|lookup|resolve|resolver)|"
    r"(?:identity|player|principal|resource|object|owner|tribe)_?(?:lookup|resolve|resolver)|"
    r"permissions?|permission_?(?:check|query|cache)|authorization|(?:^|_)authz?(?:_|$)|"
    r"access_?control|acl|roles?|privileges?|moderation|moderator|ban|kick|admin(?:_?(?:command|action))?|"
    r"commands?|command_?(?:router|response|reply|replies)|chat_?(?:command|response|reply|replies)|"
    r"send_?chat|broadcast|notices?|"
    r"(?:resource|player|principal|tribe)_?(?:owner|ownership|permission|permissions)|"
    r"[A-Za-z0-9_]*(?:ResourceHandle|ObjectHandle|OwnerLookup|OwnerResolve|Ownership|Permission|Permissions|"
    r"Authorization|Authz|AccessControl|ACL|Role|Privilege|Moderation|Moderator|Ban|Kick|Admin|"
    r"CommandRouter|CommandResponse|CommandReply|CommandReplies|ChatResponse|ChatReply|ChatReplies|SendChat)"
    r"[A-Za-z0-9_]*|"
    r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*",
    re.IGNORECASE,
)
PUBLIC_HEADER_IDENTITY_IDENTIFIER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
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
        help="Approved runtime principal lifecycle evidence manifest.",
    )
    parser.add_argument(
        "--principal-start-end-runtime-evidence",
        type=Path,
        help=(
            "Narrow copied runtime evidence proving principal start/end only. "
            "This is non-counting contract-review context and never an approved runtime bundle."
        ),
    )
    parser.add_argument(
        "--identifier-redaction-evidence",
        type=Path,
        default=DEFAULT_IDENTIFIER_REDACTION_EVIDENCE,
        help="Repo-local sanitized identifier-redaction evidence manifest for contract-review intake only.",
    )
    parser.add_argument(
        "--principal-invalidation-policy",
        type=Path,
        default=DEFAULT_PRINCIPAL_INVALIDATION_POLICY,
        help="Candidate-only principal invalidation policy for lifetime/generation/scope review intake only.",
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
    parser.add_argument(
        "--identity-public-contract-decision-record",
        type=Path,
        default=None,
        help=(
            "Repo-local reviewed identity public-contract decision record. "
            "Accepted records resolve only their hash-bound reviewed decision keys; public header "
            "routing stays blocked until the full identity contract gate is complete."
        ),
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


def forbidden_approved_runtime_source_tokens(value: str) -> list[str]:
    lowered = value.casefold()
    return sorted(
        {
            token
            for token in FORBIDDEN_APPROVED_RUNTIME_RESOLVED_INPUT_TOKENS
            if token in lowered
        }
    )


def non_promotional_source_reference_tokens(value: str) -> list[str]:
    tokens = set(forbidden_approved_runtime_source_tokens(value))
    for token, pattern in SOURCE_PROVENANCE_NON_PROMOTIONAL_ALIAS_PATTERNS.items():
        if pattern.search(value):
            tokens.add(token)
    return sorted(tokens)


def add_non_promotional_source_reference(
    findings: list[dict[str, Any]],
    label: str,
    value: Any,
) -> None:
    if not isinstance(value, str):
        return
    tokens = non_promotional_source_reference_tokens(value)
    if tokens:
        findings.append({"path": label, "value": value, "tokens": tokens})


def multi_surface_beta_capture_candidate_references(
    value: Any,
    label: str = "$",
    *,
    include_keys: bool = True,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if is_non_claim_container_path(label):
        return findings
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{label}.{key}"
            if include_keys and isinstance(key, str) and MULTI_SURFACE_BETA_CAPTURE_ARTIFACT_RE.search(key):
                findings.append({"path": item_path, "value": key, "tokens": ["multi_surface_beta_capture_material"]})
            findings.extend(multi_surface_beta_capture_candidate_references(item, item_path, include_keys=include_keys))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(
                multi_surface_beta_capture_candidate_references(
                    item,
                    f"{label}[{index}]",
                    include_keys=include_keys,
                )
            )
    elif isinstance(value, str):
        if value in MULTI_SURFACE_BETA_CAPTURE_SCHEMAS or MULTI_SURFACE_BETA_CAPTURE_ARTIFACT_RE.search(value):
            findings.append({"path": label, "value": value, "tokens": ["multi_surface_beta_capture_material"]})
    return findings


def approved_runtime_report_multi_surface_beta_capture_references(report: dict[str, Any]) -> list[dict[str, Any]]:
    checked_paths = (
        ("$.approved_runtime_evidence.schema", report.get("schema")),
        ("$.approved_runtime_evidence.ready_scope", report.get("ready_scope")),
        ("$.approved_runtime_evidence.output_artifact_identity", report.get("output_artifact_identity")),
        ("$.approved_runtime_evidence.source_summary", report.get("source_summary")),
        ("$.approved_runtime_evidence.operational_window", report.get("operational_window")),
        (
            "$.approved_runtime_evidence.approved_runtime_evidence_binding",
            report.get("approved_runtime_evidence_binding"),
        ),
    )
    findings: list[dict[str, Any]] = []
    for label, value in checked_paths:
        findings.extend(multi_surface_beta_capture_candidate_references(value, label))
    return findings


def approved_runtime_binding_shortcut_claims(binding: Any, label: str) -> dict[str, list[dict[str, str]]]:
    return public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(binding, label)


def approved_runtime_binding_has_shortcuts(binding: Any, label: str) -> bool:
    claims = approved_runtime_binding_shortcut_claims(binding, label)
    return any(claims.values())


def add_binding_shortcut_blockers(
    blockers: list[dict[str, Any]],
    *,
    reason_prefix: str,
    label: str,
    binding: Any,
) -> None:
    claims = approved_runtime_binding_shortcut_claims(binding, label)
    if claims["non_counting"]:
        add(
            blockers,
            f"{reason_prefix}_non_counting_shortcut_not_accepted",
            label,
            claims=claims["non_counting"],
        )
    if claims["public_shortcuts"]:
        add(
            blockers,
            f"{reason_prefix}_public_header_api_abi_shortcut_not_accepted",
            label,
            claims=claims["public_shortcuts"],
        )


def add_runtime_observer_source_kind_reference(
    findings: list[dict[str, Any]],
    label: str,
    value: Any,
) -> None:
    expected = REQUIRED_APPROVED_RUNTIME_SOURCE_PROVENANCE_POLICY["accepted_source_kind"]
    if value is None:
        return
    if value == expected:
        return
    tokens = non_promotional_source_reference_tokens(value) if isinstance(value, str) else []
    findings.append(
        {
            "path": label,
            "value": value,
            "expected": expected,
            "tokens": sorted({*tokens, "source_kind_mismatch"}),
        }
    )


def approved_runtime_non_promotional_source_references(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    add_non_promotional_source_reference(findings, "$.schema", payload.get("schema"))
    output_identity = payload.get("output_artifact_identity")
    if isinstance(output_identity, dict):
        add_non_promotional_source_reference(
            findings,
            "$.output_artifact_identity.artifact_kind",
            output_identity.get("artifact_kind"),
        )
        add_non_promotional_source_reference(
            findings,
            "$.output_artifact_identity.evidence_pack_id",
            output_identity.get("evidence_pack_id"),
        )

    source_summary = payload.get("source_summary")
    if isinstance(source_summary, dict):
        evidence = source_summary.get("evidence")
        if isinstance(evidence, dict):
            add_runtime_observer_source_kind_reference(
                findings,
                "$.source_summary.evidence.kind",
                evidence.get("kind"),
            )
            sources = evidence.get("sources")
            if isinstance(sources, list):
                for index, source in enumerate(sources):
                    if not isinstance(source, dict):
                        continue
                    add_non_promotional_source_reference(
                        findings,
                        f"$.source_summary.evidence.sources[{index}].path",
                        source.get("path"),
                    )

    operational_window = payload.get("operational_window")
    if isinstance(operational_window, dict):
        copied_log = operational_window.get("copied_log")
        if isinstance(copied_log, dict):
            add_non_promotional_source_reference(
                findings,
                "$.operational_window.copied_log.path",
                copied_log.get("path"),
            )
    return findings


def validate_approved_runtime_source_provenance_policy(
    policy: Any,
    blockers: list[dict[str, Any]],
    label: str,
    reason: str,
) -> None:
    if policy != REQUIRED_APPROVED_RUNTIME_SOURCE_PROVENANCE_POLICY:
        add(
            blockers,
            reason,
            label,
            expected=REQUIRED_APPROVED_RUNTIME_SOURCE_PROVENANCE_POLICY,
            value=policy,
        )


def approved_runtime_false_promotion_claims(report: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        (key, report.get(key))
        for key in APPROVED_RUNTIME_FALSE_PROMOTION_KEYS
        if key in report and not is_closed_readiness_value(normalize_contract_key(key), report.get(key))
    ]


def add_approved_runtime_false_promotion_blockers(
    blockers: list[dict[str, Any]],
    claims: list[tuple[str, Any]],
) -> None:
    existing = {
        (blocker.get("reason"), blocker.get("label"))
        for blocker in blockers
    }
    for key, value in claims:
        reason = f"approved_runtime_evidence_{key}_not_false"
        label = f"$.approved_runtime_evidence.{key}"
        if (reason, label) in existing:
            continue
        add(blockers, reason, label, value=value)
        existing.add((reason, label))


def approved_runtime_evidence_binding_matches(
    runtime_report: dict[str, Any],
    identity_contract_decision_report: dict[str, Any],
) -> bool:
    runtime_binding = runtime_report.get("approved_runtime_evidence_binding")
    decision_binding = identity_contract_decision_report.get("approved_runtime_evidence_binding")
    return (
        isinstance(runtime_binding, dict)
        and isinstance(decision_binding, dict)
        and decision_binding == runtime_binding
        and not approved_runtime_binding_has_shortcuts(
            runtime_binding,
            "$.approved_runtime_evidence.approved_runtime_evidence_binding",
        )
        and not approved_runtime_binding_has_shortcuts(
            decision_binding,
            "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
        )
        and not multi_surface_beta_capture_candidate_references(
            runtime_binding,
            "$.approved_runtime_evidence.approved_runtime_evidence_binding",
        )
        and not multi_surface_beta_capture_candidate_references(
            decision_binding,
            "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
        )
    )


def normalize_contract_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


SOURCE_OVERCLAIM_KEY_TOKENS = (
    "source_overclaim",
    "source_overclaimed",
    "source_overclaims",
    "side_lane_source_overclaim",
)
SOURCE_OVERCLAIM_COUNT_KEYS = {
    "count",
    "component_count",
    "flag_count",
    "progress_flag_count",
    "readiness_flag_count",
    "total",
    "total_flag_count",
}


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
        return is_zero_like_claim_value(value)
    return False


def string_mentions_source_overclaim_zero(value: str) -> bool:
    normalized = normalize_contract_key(value)
    return is_source_overclaim_key(normalized) and (
        "zero" in normalized or "_0" in f"_{normalized}_"
    )


def source_overclaim_zero_overclaims(
    value: Any,
    path: str = "$",
    *,
    source_overclaim_context: bool = False,
) -> list[dict[str, Any]]:
    if (
        is_non_claim_container_path(path)
        or ".forbidden_source_aliases" in path
        or ".forbidden_source_classes" in path
        or ".forbidden_source_tokens" in path
        or ".source_artifact_hash_policy" in path
        or ".source_artifact_freshness.policy" in path
    ):
        return []
    claims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if not isinstance(key, str):
                claims.extend(
                    source_overclaim_zero_overclaims(
                        item,
                        item_path,
                        source_overclaim_context=source_overclaim_context,
                    )
                )
                continue
            key_name = normalize_contract_key(key)
            child_context = source_overclaim_context or is_source_overclaim_key(key_name)
            if (
                child_context
                and is_source_overclaim_count_key(key_name)
                and zero_source_overclaim_count_value(item)
            ):
                claims.append({"path": item_path, "term": "source_overclaim_zero_marker", "value": item})
            elif is_source_overclaim_key(key_name) and "zero" in key_name and is_nonempty_public_surface_claim_value(item):
                claims.append({"path": item_path, "term": "source_overclaim_zero_marker", "value": item})
            elif (
                child_context
                and key_name in NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS
                and is_positive_claim_value(item)
            ):
                claims.append({"path": item_path, "term": "source_overclaim_zero_status_alias", "value": item})
            claims.extend(
                source_overclaim_zero_overclaims(
                    item,
                    item_path,
                    source_overclaim_context=child_context,
                )
            )
        return claims
    if isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(
                source_overclaim_zero_overclaims(
                    item,
                    f"{path}[{index}]",
                    source_overclaim_context=source_overclaim_context,
                )
            )
        return claims
    if isinstance(value, str) and string_mentions_source_overclaim_zero(value):
        claims.append({"path": path, "term": "source_overclaim_zero_marker", "value": value})
    return claims


def is_zero_like_claim_value(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value == 0
    if isinstance(value, str):
        normalized = re.sub(r"[^a-z0-9/]+", "_", value.casefold()).strip("_")
        return normalized in {"0", "0_0", "0_percent", "0_pct"} or bool(
            re.fullmatch(r"0[/_]0*[1-9][0-9]*", normalized)
        )
    return False


def is_closed_readiness_value(readiness_key: str, value: Any) -> bool:
    if readiness_key in MULTI_SURFACE_BETA_CAPTURE_STATUS_KEYS:
        if value in (False, None, [], {}):
            return True
        if isinstance(value, str):
            normalized = normalize_contract_key(value)
            return (
                normalized in MULTI_SURFACE_BETA_CAPTURE_ALLOWED_STATUS_VALUES
                or normalized in NON_PROMOTIONAL_CLAIM_VALUE_TOKENS
            )
        return False
    if readiness_key in ZERO_OR_FALSE_READINESS_KEYS:
        return is_zero_like_claim_value(value)
    if value in (False, None, [], {}):
        return True
    if isinstance(value, str):
        return normalize_contract_key(value) in NON_PROMOTIONAL_CLAIM_VALUE_TOKENS
    return value is False


def closed_readiness_value(readiness_key: str) -> Any:
    return 0 if readiness_key in ZERO_OR_FALSE_READINESS_KEYS else False


def sanitized_closed_readiness_value(readiness_key: str, value: Any) -> Any:
    if (
        readiness_key in MULTI_SURFACE_BETA_CAPTURE_STATUS_KEYS
        and is_closed_readiness_value(readiness_key, value)
    ):
        return value
    return closed_readiness_value(readiness_key)


def is_readiness_overclaim_value(readiness_key: str, value: Any) -> bool:
    if readiness_key in ZERO_OR_FALSE_READINESS_KEYS or readiness_key in MULTI_SURFACE_BETA_CAPTURE_STATUS_KEYS:
        return not is_closed_readiness_value(readiness_key, value)
    return is_positive_claim_value(value)


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
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        return normalized in {
            "accepted",
            "allowed",
            "authorized",
            "available",
            "complete",
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
            "yes",
        }
    return False


def is_nonempty_public_surface_claim_value(value: Any) -> bool:
    if value is True:
        return True
    if value in (False, None):
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
        return normalized not in NON_PROMOTIONAL_CLAIM_VALUE_TOKENS
    if isinstance(value, list):
        return any(is_nonempty_public_surface_claim_value(item) for item in value)
    if isinstance(value, dict):
        return any(is_nonempty_public_surface_claim_value(item) for item in value.values())
    return False


def provenance_value_contains_non_promotional_term(value: Any) -> bool:
    if isinstance(value, str):
        normalized = normalize_contract_key(value)
        return any(term in normalized for term in NON_PROMOTIONAL_PROVENANCE_CONTEXT_TERMS)
    if isinstance(value, list):
        return any(provenance_value_contains_non_promotional_term(item) for item in value)
    if isinstance(value, dict):
        return any(provenance_value_contains_non_promotional_term(item) for item in value.values())
    return False


def value_marks_non_promotional_provenance_context(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                normalize_contract_key(key) in NON_PROMOTIONAL_PROVENANCE_CONTEXT_KEYS
                and provenance_value_contains_non_promotional_term(item)
            ):
                return True
            if isinstance(item, (dict, list)) and value_marks_non_promotional_provenance_context(item):
                return True
        return False
    if isinstance(value, list):
        return any(value_marks_non_promotional_provenance_context(item) for item in value)
    return False


def split_claim_name_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def nested_claim_key_candidates(path: str, key: object) -> set[str]:
    candidates = {normalize_contract_key(key)}
    path_parts = [
        re.sub(r"\[[0-9]+\]", "", part)
        for part in path.removeprefix("$.").split(".")
        if part and not part.startswith("[")
    ]
    for depth in range(1, 4):
        prefix = path_parts[-depth:]
        if prefix:
            candidates.add(normalize_contract_key("_".join([*prefix, str(key)])))
    return candidates


def first_claim_key(candidates: set[str], claim_keys: set[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in claim_keys), None)


def split_claim_overclaims(value: dict[str, Any], path: str) -> list[dict[str, Any]]:
    declared_claim_names = [
        claim_name
        for key, item in value.items()
        if normalize_contract_key(key) in SPLIT_CLAIM_NAME_KEYS
        for claim_name in split_claim_name_values(item)
    ]
    declared_claim_values = [
        item
        for key, item in value.items()
        if normalize_contract_key(key) in SPLIT_CLAIM_VALUE_KEYS
    ]
    overclaims: list[dict[str, Any]] = []
    if value_marks_non_promotional_provenance_context(value):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            key_name = normalize_contract_key(key)
            if key_name in NON_PROMOTIONAL_PROVENANCE_STATUS_KEYS and is_positive_claim_value(item):
                overclaims.append(
                    {
                        "path": item_path,
                        "term": "non_promotional_provenance_status_alias",
                        "value": item,
                    }
                )
            if (
                NON_PROMOTIONAL_PROVENANCE_PROGRESS_ALIAS_RE.search(key_name)
                and is_nonempty_public_surface_claim_value(item)
            ):
                overclaims.append(
                    {
                        "path": item_path,
                        "term": "non_promotional_provenance_progress_alias",
                        "value": item,
                    }
                )
    for claim_name in declared_claim_names:
        claim_key = normalize_contract_key(claim_name)
        positive_claim = any(is_positive_claim_value(item) for item in declared_claim_values)
        nonclosed_readiness_claim = (
            claim_key in READINESS_FALSE_KEYS
            and any(is_readiness_overclaim_value(claim_key, item) for item in declared_claim_values)
        )
        public_surface_list_claim = (
            claim_key in EMPTY_PUBLIC_LIST_KEYS
            and any(is_nonempty_public_surface_claim_value(item) for item in declared_claim_values)
        )
        nonfalse_shortcut_claim = (
            claim_key in NON_FALSE_READINESS_ALIAS_KEYS
            and any(is_nonempty_public_surface_claim_value(item) for item in declared_claim_values)
        )
        if (
            claim_key in READINESS_FALSE_KEYS
            or claim_key in EMPTY_PUBLIC_LIST_KEYS
            or APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(claim_key) is not None
        ) and (positive_claim or nonclosed_readiness_claim or public_surface_list_claim or nonfalse_shortcut_claim):
            overclaims.append({"path": path, "term": "split_readiness_alias", "value": value})
    return overclaims


def is_non_claim_container_path(path: str) -> bool:
    return any(fragment in path for fragment in NON_CLAIM_CONTAINER_PATH_FRAGMENTS)


def is_allowed_required_sequence_gate_text(path: str, value: str) -> bool:
    return any(
        path.endswith(f".v1_sequence_gate[{index}]") and value == expected
        for index, expected in enumerate(REQUIRED_SEQUENCE_GATE)
    )


def alias_guardrails_false() -> dict[str, bool]:
    return {key: False for key in sorted(REQUIRED_ALIAS_GUARDRAILS_FALSE)}


def validate_alias_guardrails(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    aliases = decisions.get("alias_guardrails")
    if not isinstance(aliases, dict):
        add(blockers, "alias_guardrails_missing", "$.alias_guardrails")
        return
    for key in sorted(REQUIRED_ALIAS_GUARDRAILS_FALSE):
        if aliases.get(key) is not False:
            add(
                blockers,
                "alias_guardrail_not_false",
                f"$.alias_guardrails.{key}",
                value=aliases.get(key),
            )
    for key in sorted(OPTIONAL_ALIAS_GUARDRAILS_FALSE):
        if key in aliases and aliases.get(key) is not False:
            add(
                blockers,
                "alias_guardrail_not_false",
                f"$.alias_guardrails.{key}",
                value=aliases.get(key),
            )
    if aliases.get("non_claim") != REQUIRED_ALIAS_GUARDRAILS_NON_CLAIM:
        add(
            blockers,
            "alias_guardrails_non_claim_mismatch",
            "$.alias_guardrails.non_claim",
            value=aliases.get("non_claim"),
        )


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
            r"\b(?:after|before|forbidden|unavailable|blocked|redacted|cannot|can't|false|missing|not|"
            r"exclusion|unresolved|until)\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
            suffix,
            re.IGNORECASE,
        )
    )


def has_non_counting_artifact_negative_context(value: str, match_start: int) -> bool:
    normalized = re.sub(
        r"identity[-_ ]+public[-_ ]+contract[-_ ]+gate[-_ ]+missing",
        "identity public contract gate",
        value,
        flags=re.IGNORECASE,
    )
    return has_negative_context(normalized, match_start)


def has_post_runtime_route_shortcut_negative_context(value: str, match_start: int) -> bool:
    window = value[max(0, match_start - 120) : match_start + 260]
    return re.search(
        r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|must\s+not|"
        r"forbid(?:den|s)?|without|unavailable|blocked\s+from)\b",
        window,
        re.IGNORECASE,
    ) is not None


def public_abi_identity_handle_negative_context(value: str, match_start: int) -> bool:
    window = value[max(0, match_start - 120) : match_start + 220]
    return re.search(
        r"\b(?:no|not|does\s+not|do\s+not|must\s+not|cannot|can't|forbid(?:den|s)?|excludes?|"
        r"blocked|unavailable)\b",
        window,
        re.IGNORECASE,
    ) is not None


def approved_runtime_report_overclaims(report: Any, path: str = "$") -> list[dict[str, Any]]:
    overclaims: list[dict[str, Any]] = []
    if path == "$":
        overclaims.extend(source_overclaim_zero_overclaims(report))
    if isinstance(report, dict):
        overclaims.extend(split_claim_overclaims(report, path))
        for key, item in report.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            if readiness_key is None and public_list_key is None:
                overclaims.extend(public_text_overclaims(str(key), item_path))
            if public_list_key is not None and item != []:
                overclaims.append({"path": item_path, "term": "public_surface_list", "value": item})
            if (
                readiness_key is not None
                and not (path == "$" and readiness_key in APPROVED_RUNTIME_REPORT_EXPLICIT_FALSE_KEYS)
                and not is_closed_readiness_value(readiness_key, item)
            ):
                overclaims.append({"path": item_path, "term": "readiness_alias", "value": item})
            if (
                normalized_key not in ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS
                and readiness_key is None
                and item not in (False, None, [], {})
                and APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(normalized_key)
            ):
                overclaims.append({"path": item_path, "term": "readiness_or_authorization_key", "value": item})
            overclaims.extend(approved_runtime_report_overclaims(item, item_path))
    elif isinstance(report, list):
        for index, item in enumerate(report):
            overclaims.extend(approved_runtime_report_overclaims(item, f"{path}[{index}]"))
    elif isinstance(report, str):
        if is_non_claim_container_path(path) or path.endswith(".next_blocker"):
            return overclaims
        if is_allowed_required_sequence_gate_text(path, report):
            return overclaims
        for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(report):
                if term == "public_abi_identity_handle_before_resource_handle":
                    if public_abi_identity_handle_negative_context(report, match.start()):
                        continue
                elif term == "non_counting_artifact_public_readiness_or_p0":
                    if has_non_counting_artifact_negative_context(report, match.start()):
                        continue
                elif term == "post_runtime_route_shortcut":
                    if has_post_runtime_route_shortcut_negative_context(report, match.start()):
                        continue
                elif has_negative_context(report, match.start()):
                    continue
                overclaims.append({"path": path, "term": term, "value": report})
                break
    return overclaims


def public_text_overclaims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if path == "$":
        claims.extend(source_overclaim_zero_overclaims(value))
    if isinstance(value, dict):
        claims.extend(split_claim_overclaims(value, path))
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            if readiness_key is not None and (
                is_readiness_overclaim_value(readiness_key, item)
                or (
                    readiness_key in NON_FALSE_READINESS_ALIAS_KEYS
                    and is_nonempty_public_surface_claim_value(item)
                )
            ):
                claims.append({"path": item_path, "term": "readiness_alias", "value": item})
            if public_list_key is not None and is_nonempty_public_surface_claim_value(item):
                claims.append({"path": item_path, "term": "public_surface_list", "value": item})
            if readiness_key is None and public_list_key is None:
                claims.extend(public_text_overclaims(str(key), item_path))
            claims.extend(public_text_overclaims(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            claims.extend(public_text_overclaims(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if is_non_claim_container_path(path):
            return claims
        if is_allowed_required_sequence_gate_text(path, value):
            return claims
        for term, pattern in PUBLIC_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                if term == "public_abi_identity_handle_before_resource_handle":
                    if public_abi_identity_handle_negative_context(value, match.start()):
                        continue
                elif term == "non_counting_artifact_public_readiness_or_p0":
                    if has_non_counting_artifact_negative_context(value, match.start()):
                        continue
                elif term == "post_runtime_route_shortcut":
                    if has_post_runtime_route_shortcut_negative_context(value, match.start()):
                        continue
                elif has_negative_context(value, match.start()):
                    continue
                claims.append({"path": path, "term": term, "value": value})
                break
    return claims


def validate_public_text_overclaims(
    value: Any,
    blockers: list[dict[str, Any]],
    *,
    label: str,
    reason: str = "public_text_or_source_overclaim",
) -> None:
    claims = public_text_overclaims(value)
    if claims:
        add(blockers, reason, "$", input=label, claims=claims)


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


def missing_approved_runtime_report() -> dict[str, Any]:
    return {
        "ready": False,
        "accepted_for_contract_review": False,
        "approved_runtime_evidence_binding": None,
        "approved_runtime_evidence_present": False,
        "runtime_evidence_ready": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_api_ready": False,
        "public_abi_ready": False,
        "public_readiness": False,
        "runtime_readiness": False,
        "public_header_allowed": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "remaining_blockers": ["approved_runtime_evidence_missing"],
    }


def approved_runtime_report(path: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        payload = approved_evidence.load_json(path)
    except (OSError, SystemExit) as exc:
        add(blockers, "approved_runtime_evidence_unreadable", "$.approved_runtime_evidence", error=str(exc))
        return missing_approved_runtime_report()

    validation = approved_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_evidence.build_report(payload, validation, check_mode="consume")
    accepted = not validation.blockers
    non_promotional_sources = approved_runtime_non_promotional_source_references(payload)
    if non_promotional_sources:
        add(
            blockers,
            "approved_runtime_evidence_non_promotional_sources_claimed",
            "$.approved_runtime_evidence.source_provenance",
            sources=non_promotional_sources,
        )
        accepted = False
    if validation.blockers:
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "$.approved_runtime_evidence",
            reasons=[blocker["reason"] for blocker in validation.blockers],
        )
    else:
        overclaims = approved_runtime_report_overclaims(payload) + approved_runtime_report_overclaims(report)
        if overclaims:
            add(
                blockers,
                "approved_runtime_evidence_report_public_readiness_overclaim",
                "$.approved_runtime_evidence",
                overclaims=overclaims,
            )
            accepted = False
        if report.get("schema") != approved_evidence.REPORT_SCHEMA:
            add(
                blockers,
                "approved_runtime_evidence_report_schema_mismatch",
                "$.approved_runtime_evidence.schema",
                value=report.get("schema"),
            )
            accepted = False
        if report.get("mode") != "consume":
            add(
                blockers,
                "approved_runtime_evidence_mode_mismatch",
                "$.approved_runtime_evidence.mode",
                value=report.get("mode"),
            )
            accepted = False
        if report.get("ready_scope") != REQUIRED_APPROVED_RUNTIME_READY_SCOPE:
            add(
                blockers,
                "approved_runtime_evidence_ready_scope_mismatch",
                "$.approved_runtime_evidence.ready_scope",
                value=report.get("ready_scope"),
            )
            accepted = False
        if report.get("remaining_blockers") != []:
            add(
                blockers,
                "approved_runtime_evidence_remaining_blockers_not_empty",
                "$.approved_runtime_evidence.remaining_blockers",
                value=report.get("remaining_blockers"),
            )
            accepted = False
        if report.get("next_blocker") != "identity_public_contract_gate_missing":
            add(
                blockers,
                "approved_runtime_evidence_next_blocker_mismatch",
                "$.approved_runtime_evidence.next_blocker",
                value=report.get("next_blocker"),
            )
            accepted = False
        if report.get("ready") is not True:
            add(
                blockers,
                "approved_runtime_evidence_report_ready_not_true",
                "$.approved_runtime_evidence.ready",
                value=report.get("ready"),
            )
            accepted = False
        if report.get("approved_runtime_evidence_present") is not True:
            add(
                blockers,
                "approved_runtime_evidence_presence_missing",
                "$.approved_runtime_evidence.approved_runtime_evidence_present",
            )
            accepted = False
        if report.get("runtime_evidence_ready") is not True:
            add(
                blockers,
                "approved_runtime_evidence_runtime_ready_missing",
                "$.approved_runtime_evidence.runtime_evidence_ready",
            )
            accepted = False
        observed_runtime_cases = report.get("observed_runtime_cases")
        if observed_runtime_cases != REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES:
            add(
                blockers,
                "approved_runtime_evidence_observed_runtime_cases_mismatch",
                "$.approved_runtime_evidence.observed_runtime_cases",
                expected=REQUIRED_APPROVED_RUNTIME_OBSERVED_CASES,
                value=observed_runtime_cases,
            )
            accepted = False
        consumer_cases = report.get("consumer_cases")
        if consumer_cases != REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES:
            add(
                blockers,
                "approved_runtime_evidence_consumer_cases_mismatch",
                "$.approved_runtime_evidence.consumer_cases",
                expected=REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                value=consumer_cases,
            )
            accepted = False
        consumer_boundary_assertions = report.get("consumer_boundary_assertions")
        if consumer_boundary_assertions != REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES:
            add(
                blockers,
                "approved_runtime_evidence_consumer_boundary_assertions_mismatch",
                "$.approved_runtime_evidence.consumer_boundary_assertions",
                expected=REQUIRED_APPROVED_RUNTIME_CONSUMER_CASES,
                value=consumer_boundary_assertions,
            )
            accepted = False
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
                        "$.approved_runtime_evidence.resolved_inputs",
                        forbidden=forbidden_inputs,
                    )
                    accepted = False
                unexpected_inputs = sorted(set(resolved_inputs) - {REQUIRED_RESOLVED_INPUT})
                if unexpected_inputs:
                    add(
                        blockers,
                        "approved_runtime_evidence_resolved_inputs_unexpected",
                        "$.approved_runtime_evidence.resolved_inputs",
                        unexpected=unexpected_inputs,
                    )
                    accepted = False
        if "accepted_for_contract_review" in report and report.get("accepted_for_contract_review") is not False:
            add(
                blockers,
                "approved_runtime_evidence_report_false_only_key_not_false",
                "$.approved_runtime_evidence.accepted_for_contract_review",
                value=report.get("accepted_for_contract_review"),
            )
            accepted = False
    false_promotion_claims = approved_runtime_false_promotion_claims(report)
    if false_promotion_claims:
        add_approved_runtime_false_promotion_blockers(blockers, false_promotion_claims)
        accepted = False
    report["accepted_for_contract_review"] = accepted
    report["approved_runtime_evidence_binding"] = (
        public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(payload)
        if accepted
        else None
    )
    report["source_provenance_policy"] = {
        "non_promotional_sources_rejected": True,
        "accepted_source_kind": REQUIRED_APPROVED_RUNTIME_SOURCE_PROVENANCE_POLICY["accepted_source_kind"],
        "checked_manifest_paths": [
            "$.schema",
            "$.output_artifact_identity.artifact_kind",
            "$.output_artifact_identity.evidence_pack_id",
            "$.source_summary.evidence.kind",
            "$.source_summary.evidence.sources[].path",
            "$.operational_window.copied_log.path",
            ],
            "forbidden_source_tokens": list(FORBIDDEN_APPROVED_RUNTIME_RESOLVED_INPUT_TOKENS),
            "forbidden_source_aliases": sorted(SOURCE_PROVENANCE_NON_PROMOTIONAL_ALIAS_PATTERNS),
            "findings": non_promotional_sources,
        }
    return report


def missing_principal_start_end_runtime_report() -> dict[str, Any]:
    return {
        "provided": False,
        "accepted_for_contract_review": False,
        "principal_start_end_runtime_evidence_present": False,
        "principal_start_end_runtime_evidence_ready": False,
        "resolved_inputs": [],
        "does_not_resolve": sorted(PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_ready": False,
        "stable_claim_allowed": False,
        "publication_authorized": False,
        "blockers": ["principal_start_end_runtime_evidence_missing"],
    }


def principal_start_end_runtime_report(path: Path | None, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    if path is None:
        return missing_principal_start_end_runtime_report()
    payload = safe_load_json(path, "principal_start_end_runtime_evidence", blockers)
    if payload is None:
        report = missing_principal_start_end_runtime_report()
        report["provided"] = True
        return report

    accepted = True
    local_blockers: list[str] = []

    def reject(reason: str, label: str, **extra: Any) -> None:
        nonlocal accepted
        accepted = False
        local_blockers.append(reason)
        add(blockers, reason, label, **extra)

    if payload.get("schema") != PRINCIPAL_START_END_RUNTIME_EVIDENCE_SCHEMA:
        reject(
            "principal_start_end_runtime_evidence_schema_mismatch",
            "$.principal_start_end_runtime_evidence.schema",
            value=payload.get("schema"),
        )
    if payload.get("ready_scope") != PRINCIPAL_START_END_READY_SCOPE:
        reject(
            "principal_start_end_runtime_evidence_ready_scope_mismatch",
            "$.principal_start_end_runtime_evidence.ready_scope",
            value=payload.get("ready_scope"),
        )
    for key in (
        "ready",
        "accepted_for_contract_review",
        "principal_start_end_runtime_evidence_present",
        "principal_start_end_runtime_evidence_ready",
    ):
        if payload.get(key) is not True:
            reject(
                f"principal_start_end_runtime_evidence_{key}_not_true",
                f"$.principal_start_end_runtime_evidence.{key}",
                value=payload.get(key),
            )
    if payload.get("next_review_blocker") != PRINCIPAL_START_END_NEXT_REVIEW_BLOCKER:
        reject(
            "principal_start_end_runtime_evidence_next_blocker_mismatch",
            "$.principal_start_end_runtime_evidence.next_review_blocker",
            value=payload.get("next_review_blocker"),
        )

    resolved_inputs = payload.get("resolved_inputs")
    if resolved_inputs != [PRINCIPAL_START_END_RESOLVED_INPUT]:
        reject(
            "principal_start_end_runtime_evidence_resolved_inputs_mismatch",
            "$.principal_start_end_runtime_evidence.resolved_inputs",
            value=resolved_inputs,
        )
    does_not_resolve = payload.get("does_not_resolve")
    if not isinstance(does_not_resolve, list) or not PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS.issubset(
        set(item for item in does_not_resolve if isinstance(item, str))
    ):
        reject(
            "principal_start_end_runtime_evidence_does_not_resolve_missing_strict_inputs",
            "$.principal_start_end_runtime_evidence.does_not_resolve",
            value=does_not_resolve,
        )
    remaining_runtime_inputs = payload.get("remaining_runtime_inputs")
    if not isinstance(remaining_runtime_inputs, list) or not PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS.issubset(
        set(item for item in remaining_runtime_inputs if isinstance(item, str))
    ):
        reject(
            "principal_start_end_runtime_evidence_remaining_runtime_inputs_missing_strict_inputs",
            "$.principal_start_end_runtime_evidence.remaining_runtime_inputs",
            value=remaining_runtime_inputs,
        )

    strict_runtime_blockers = payload.get("strict_approved_runtime_evidence_blockers")
    if not (
        isinstance(strict_runtime_blockers, list)
        and PRINCIPAL_START_END_MISSING_CHECK_JOIN_BLOCKER
        in [item for item in strict_runtime_blockers if isinstance(item, str)]
    ):
        reject(
            "principal_start_end_runtime_evidence_missing_explicit_checkjoin_blocker",
            "$.principal_start_end_runtime_evidence.strict_approved_runtime_evidence_blockers",
            value=strict_runtime_blockers,
        )

    report_blockers = payload.get("blockers")
    if report_blockers not in ([], None):
        reject(
            "principal_start_end_runtime_evidence_report_blockers_present",
            "$.principal_start_end_runtime_evidence.blockers",
            value=report_blockers,
        )

    for key in PRINCIPAL_START_END_RUNTIME_REQUIRED_FALSE_KEYS:
        if payload.get(key) is not False:
            reject(
                f"principal_start_end_runtime_evidence_{key}_not_false",
                f"$.principal_start_end_runtime_evidence.{key}",
                value=payload.get(key),
            )
    for key in dict.fromkeys(PRINCIPAL_START_END_RUNTIME_OPTIONAL_FALSE_KEYS):
        if key in PRINCIPAL_START_END_RUNTIME_REQUIRED_FALSE_KEYS:
            continue
        if key in payload and payload.get(key) is not False:
            reject(
                f"principal_start_end_runtime_evidence_{key}_not_false",
                f"$.principal_start_end_runtime_evidence.{key}",
                value=payload.get(key),
            )

    diagnostic = payload.get("diagnostic_coverage")
    if isinstance(diagnostic, dict) and diagnostic.get("diagnostic_candidates_count_as_evidence") is not False:
        reject(
            "principal_start_end_runtime_evidence_diagnostic_candidates_count_as_evidence_not_false",
            "$.principal_start_end_runtime_evidence.diagnostic_coverage.diagnostic_candidates_count_as_evidence",
            value=diagnostic.get("diagnostic_candidates_count_as_evidence"),
        )

    non_claims = payload.get("non_claims")
    required_non_claim_fragments = (
        "not the approved three-role lifecycle evidence bundle",
        "does not promote public identity",
    )
    if not isinstance(non_claims, list) or not all(
        any(isinstance(item, str) and fragment in item for item in non_claims)
        for fragment in required_non_claim_fragments
    ):
        reject(
            "principal_start_end_runtime_evidence_non_claims_missing_required",
            "$.principal_start_end_runtime_evidence.non_claims",
            value=non_claims,
        )

    return {
        **payload,
        "provided": True,
        "accepted_for_contract_review": accepted,
        "principal_start_end_runtime_evidence_present": accepted
        and payload.get("principal_start_end_runtime_evidence_present") is True,
        "principal_start_end_runtime_evidence_ready": accepted
        and payload.get("principal_start_end_runtime_evidence_ready") is True,
        "resolved_inputs": [PRINCIPAL_START_END_RESOLVED_INPUT] if accepted else [],
        "next_review_blocker": payload.get("next_review_blocker"),
        "remaining_runtime_inputs": remaining_runtime_inputs,
        "strict_approved_runtime_evidence_blockers": strict_runtime_blockers,
        "blockers": local_blockers,
    }


def identity_public_contract_decision_record_report(
    path: Path | None,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    if path is None:
        return {
            "provided": False,
            "accepted_for_contract_review": False,
            "record_valid": False,
            "record_valid_scope": None,
            "contract_review_only": False,
            "hash_bound_to_current_source_artifacts": False,
            "reviewed_hash_current_contract_review_only": False,
            "reviewed_template_only": False,
            "strict_accepted_decision_record": False,
            "accepted_post_runtime_decision_record": False,
            "accepted_as_next_identity_contract_input": False,
            "public_header_readiness_from_decision_record": False,
            "resolved_decision_keys": [],
            "next_blocker": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
            "public_sdk_ready": False,
            "public_readiness": False,
            "runtime_ready": False,
            "runtime_readiness": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_ready": False,
            "v1_completion_ready": False,
            "v1_completion_evidence": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "public_api_symbols_now": [],
            "blockers": [],
        }

    validation_blockers: list[dict[str, Any]] = []
    payload = public_contract_decision_record.load_record(path, validation_blockers)
    if payload is not None:
        validation_blockers.extend(
            public_contract_decision_record.validate_record(payload, check_mode="consume")
        )
    report = public_contract_decision_record.build_report(
        payload,
        validation_blockers,
        check_mode="consume",
    )
    accepted = (
        report.get("record_valid") is True
        and report.get("record_valid_scope") == public_contract_decision_record.RECORD_VALID_SCOPE
        and report.get("ready_scope") == public_contract_decision_record.READY_SCOPE
        and report.get("contract_review_only") is True
        and report.get("accepted_for_contract_review") is True
        and report.get("hash_bound_to_current_source_artifacts") is True
        and report.get("reviewed_hash_current_contract_review_only") is True
    )
    if not accepted:
        add(
            blockers,
            "identity_public_contract_decision_record_not_accepted",
            "$.identity_public_contract_decision_record",
            reasons=report.get("blockers", []),
        )
    reviewed_template_only = (
        report.get("record_valid") is True
        and report.get("hash_bound_to_current_source_artifacts") is True
        and report.get("reviewed_hash_current_contract_review_only") is True
        and report.get("accepted_for_contract_review") is not True
    )
    return {
        **report,
        "provided": True,
        "accepted_for_contract_review": accepted,
        "reviewed_template_only": reviewed_template_only,
        "strict_accepted_decision_record": accepted,
        "accepted_post_runtime_decision_record": False,
        "accepted_as_next_identity_contract_input": False,
        "public_header_readiness_from_decision_record": False,
    }


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
    accepted = not validation_blockers
    overclaims = approved_runtime_report_overclaims(payload) + approved_runtime_report_overclaims(report)
    if overclaims:
        add(
            blockers,
            "identifier_redaction_evidence_public_contract_overclaim",
            "$.identifier_redaction_evidence",
            overclaims=overclaims,
        )
        accepted = False
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if payload.get(key) is not False or report.get(key) is not False:
            add(blockers, f"identifier_redaction_evidence_{key}_not_false", f"$.identifier_redaction_evidence.{key}")
            accepted = False
    if validation_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "$.identifier_redaction_evidence",
            reasons=[blocker["reason"] for blocker in validation_blockers],
        )
        accepted = False
    else:
        if report.get("accepted_for_contract_review") is not True:
            add(
                blockers,
                "identifier_redaction_evidence_contract_review_not_accepted",
                "$.identifier_redaction_evidence.accepted_for_contract_review",
            )
            accepted = False
        if report.get("resolved_inputs") != [REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT]:
            add(
                blockers,
                "identifier_redaction_evidence_resolved_inputs_mismatch",
                "$.identifier_redaction_evidence.resolved_inputs",
                value=report.get("resolved_inputs"),
            )
            accepted = False
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
            accepted = False
    if not accepted and not validation_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "$.identifier_redaction_evidence",
            reasons=["public_contract_overclaim_or_route_unlock"],
        )
    return {
        "provided": True,
        "ready": accepted and report.get("ready") is True,
        "accepted_for_contract_review": accepted and report.get("accepted_for_contract_review") is True,
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


def planning_source_verification_report(
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
            "$.source_bound_planning_manifest_verification",
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
            "$.source_bound_planning_manifest_verification.schema",
            value=report.get("schema"),
        )
    if report.get("mode") != "verify_existing":
        add(
            blockers,
            "source_bound_planning_manifest_verification_mode_mismatch",
            "$.source_bound_planning_manifest_verification.mode",
            value=report.get("mode"),
        )
    if report.get("valid") is not True or report.get("accepted_for_planning") is not True:
        add(
            blockers,
            "source_bound_planning_manifest_verification_not_accepted",
            "$.source_bound_planning_manifest_verification",
            verification_blockers=report.get("blockers", []),
        )
    if report.get("planning_only") is not True:
        add(
            blockers,
            "source_bound_planning_manifest_verification_not_planning_only",
            "$.source_bound_planning_manifest_verification.planning_only",
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
                f"$.source_bound_planning_manifest_verification.{key}",
                value=report.get(key),
            )
    provenance_verified = (
        report.get("valid") is True
        and report.get("accepted_for_planning") is True
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
        "accepted_for_contract_review": False,
        "resolved_input": None,
        "provenance_verified": provenance_verified,
        "provenance_only": True,
        "planning_only": report.get("planning_only") is True,
        "snapshot_root": report.get("snapshot_root"),
        "verify_existing_dir": report.get("verify_existing_dir"),
        "checked_outputs": report.get("checked_outputs", {}),
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
    sanitize_blocker_count = len(blockers)
    report = sanitize_non_promotional_report(
        report,
        blockers,
        input_label="public_abi_preflight_candidate",
        path="$.public_abi_preflight_candidate",
    )
    if len(blockers) != sanitize_blocker_count:
        report["accepted_for_candidate_review"] = False
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
        "public_api_ready": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "public_header_symbols_now": [],
        "public_api_symbols_now": [],
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
        public_header_contract_scan = owner_token_sdk_consumer.scan_public_header_contract(
            public_header_path,
            contract_blockers,
        )
        owner_token_sdk_consumer.validate_manifest(payload, preflight_payload, contract_blockers)
        report = owner_token_sdk_consumer.build_report(
            payload,
            contract_blockers,
            preflight_report=preflight_report,
            public_header_contract_scan=public_header_contract_scan,
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
        for overclaim in split_claim_overclaims(value, path):
            add(
                blockers,
                "nested_readiness_split_claim_overclaim",
                overclaim["path"],
                input=input_label,
                value=overclaim["value"],
            )
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            if normalized_key == "ready":
                if readiness_key is not None and not is_closed_readiness_value(readiness_key, item):
                    add(blockers, "nested_readiness_flag_not_false", item_path, input=input_label, value=item)
                sanitized[key] = (
                    sanitized_closed_readiness_value(readiness_key, item)
                    if readiness_key is not None
                    else False
                )
                continue
            if readiness_key is None and public_list_key is None:
                for claim in public_text_overclaims(str(key), item_path):
                    add(
                        blockers,
                        "nested_public_text_overclaim",
                        claim["path"],
                        input=input_label,
                        term=claim["term"],
                        value=claim["value"],
                    )
            contract_review_allowed = (
                normalized_key == "accepted_for_contract_review"
                and path != root_path
                and item_path.endswith(NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES)
            )
            if readiness_key is not None and not contract_review_allowed:
                if not is_closed_readiness_value(readiness_key, item):
                    add(blockers, "nested_readiness_flag_not_false", item_path, input=input_label, value=item)
                sanitized[key] = sanitized_closed_readiness_value(readiness_key, item)
            elif public_list_key is not None:
                if item != []:
                    add(blockers, f"nested_{public_list_key}_not_empty", item_path, input=input_label, value=item)
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
    if isinstance(value, str):
        if is_non_claim_container_path(path):
            return value
        for claim in public_text_overclaims(value, path):
            add(
                blockers,
                "nested_public_text_overclaim",
                claim["path"],
                input=input_label,
                term=claim["term"],
                value=claim["value"],
            )
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


def validate_permissions_admin_query_only_planning(
    value: Any,
    blockers: list[dict[str, Any]],
    label: str,
) -> None:
    if not isinstance(value, dict):
        add(blockers, "permissions_admin_query_only_planning_missing", label)
        return

    if value.get("status") != REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_STATUS:
        add(
            blockers,
            "permissions_admin_query_only_status_mismatch",
            f"{label}.status",
            value=value.get("status"),
        )
    for key in (
        "public_contract_allowed",
        "promotion_ready",
        "public_sdk_ready",
        "runtime_ready",
        "v1_completion_evidence",
        "complete_sdk_counting_allowed",
    ):
        if value.get(key) is not False:
            add(
                blockers,
                "permissions_admin_query_only_flag_not_false",
                f"{label}.{key}",
                value=value.get(key),
            )
    require_string_list_contains(
        value,
        "required_policy",
        REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_POLICY,
        blockers,
        "permissions_admin_query_only_policy_missing",
        f"{label}.required_policy",
    )
    require_string_list_contains(
        value,
        "forbidden_until_separate_promotion",
        REQUIRED_PERMISSIONS_ADMIN_FORBIDDEN_UNTIL_PROMOTION,
        blockers,
        "permissions_admin_query_only_forbidden_terms_missing",
        f"{label}.forbidden_until_separate_promotion",
    )
    require_string_list_contains(
        value,
        "non_counting_artifacts",
        REQUIRED_PERMISSIONS_ADMIN_NON_COUNTING_ARTIFACTS,
        blockers,
        "permissions_admin_query_only_non_counting_artifacts_missing",
        f"{label}.non_counting_artifacts",
    )

    certificate = value.get("required_identity_promotion_certificate")
    certificate_label = f"{label}.required_identity_promotion_certificate"
    if not isinstance(certificate, dict):
        add(blockers, "permissions_admin_identity_promotion_certificate_requirement_missing", certificate_label)
        return
    for key, expected in REQUIRED_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS.items():
        if certificate.get(key) != expected:
            add(
                blockers,
                "permissions_admin_identity_promotion_certificate_requirement_mismatch",
                f"{certificate_label}.{key}",
                expected=expected,
                value=certificate.get(key),
            )
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        add(
            blockers,
            "permissions_admin_identity_promotion_certificate_non_counting_flag_not_false",
            f"{certificate_label}.missing_mismatched_or_stale_certificate_counts",
            value=certificate.get("missing_mismatched_or_stale_certificate_counts"),
        )


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
    text = without_native_prototype_symbols(path.read_text(encoding="utf-8"), header_only=True)
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
    validate_public_text_overclaims(payload, blockers, label="private_candidate_contract")
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
        elif item.get("status") != "unresolved":
            add(
                blockers,
                "required_before_public_header_status_mismatch",
                f"$.required_before_public_header[{index}].status",
                requirement_id=requirement_id,
                status=item.get("status"),
            )

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
        separation_label = "$.required_before_public_header[separation.no_commands_permissions_persistence]"
        sequence_gate = string_list(separation.get("v1_sequence_gate"))
        if sequence_gate != REQUIRED_SEQUENCE_GATE:
            add(blockers, "separation_sequence_gate_mismatch", f"{separation_label}.v1_sequence_gate")
        require_string_list_contains(separation, "forbidden_in_identity_contract", REQUIRED_SEPARATION_FORBIDDEN, blockers, "separation_forbidden_downstream_surfaces_missing", "$.required_before_public_header[separation.no_commands_permissions_persistence].forbidden_in_identity_contract")
        validate_permissions_admin_query_only_planning(
            separation.get("permissions_admin_query_only_planning"),
            blockers,
            f"{separation_label}.permissions_admin_query_only_planning",
        )


def unresolved_required_before_public_header_ids(decisions: dict[str, Any]) -> list[str]:
    requirements = decisions.get("required_before_public_header")
    if not isinstance(requirements, list):
        return REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS.copy()
    return [
        item["id"]
        for item in requirements
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and item.get("status") != "resolved"
    ]


def remaining_post_approved_runtime_evidence_decision_keys(decisions: dict[str, Any]) -> list[str]:
    # Public-header prerequisites are deliberately not clearable by this readiness route.
    # The reviewed decision record can remove only the contract-review decision keys below;
    # ABI/header/SDK prerequisites stay as unresolved input to the later header gate.
    remaining = REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS.copy()
    seen = set(remaining)
    for key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
        if key not in seen:
            remaining.append(key)
            seen.add(key)
    return remaining


def identity_contract_decision_record_shortcut_claims(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for key in IDENTITY_CONTRACT_DECISION_RECORD_SHORTCUT_FALSE_KEYS:
        if key in report and not is_closed_readiness_value(normalize_contract_key(key), report.get(key)):
            claims.append(
                {
                    "path": f"$.identity_public_contract_decision_record.{key}",
                    "term": "header_or_public_readiness_shortcut",
                    "value": report.get(key),
                }
            )
    for key in EMPTY_PUBLIC_LIST_KEYS:
        if key in report and is_nonempty_public_surface_claim_value(report.get(key)):
            claims.append(
                {
                    "path": f"$.identity_public_contract_decision_record.{key}",
                    "term": "public_surface_list",
                    "value": report.get(key),
                }
            )
    if report.get("next_blocker") == NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW:
        claims.append(
            {
                "path": "$.identity_public_contract_decision_record.next_blocker",
                "term": "public_header_gate_shortcut",
                "value": report.get("next_blocker"),
            }
        )
    resolved_decision_keys = report.get("resolved_decision_keys")
    if isinstance(resolved_decision_keys, list):
        pre_header_keys = sorted(
            {
                key
                for key in resolved_decision_keys
                if isinstance(key, str) and key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_BASE_DECISION_KEYS
            }
        )
        if pre_header_keys:
            claims.append(
                {
                    "path": "$.identity_public_contract_decision_record.resolved_decision_keys",
                    "term": "pre_header_requirement_shortcut",
                    "value": pre_header_keys,
                }
            )
    return claims


def validate_post_approved_runtime_evidence_gate(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    gate = decisions.get("post_approved_runtime_evidence_gate")
    if not isinstance(gate, dict):
        add(blockers, "post_approved_runtime_evidence_gate_missing", "$.post_approved_runtime_evidence_gate")
        return

    expected_gate_keys = {
        "id",
        "status",
        "active_after_resolved_input",
        "reported_current_blocker",
        "next_blocker",
        "required_unresolved_decision_keys",
        "auditable_inputs",
        "next_required_artifact",
        "offline_preparation",
        "non_claim",
        *REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS,
    }
    unexpected_gate_keys = sorted(set(gate) - expected_gate_keys)
    if unexpected_gate_keys:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_unexpected_route_extras",
            "$.post_approved_runtime_evidence_gate",
            unexpected=unexpected_gate_keys,
        )
    if gate.get("id") != "identity_public_contract_gate.reviewed_identity_public_contract":
        add(
            blockers,
            "post_approved_runtime_evidence_gate_id_mismatch",
            "$.post_approved_runtime_evidence_gate.id",
            value=gate.get("id"),
        )
    if gate.get("status") != "blocked/review-required":
        add(
            blockers,
            "post_approved_runtime_evidence_gate_status_mismatch",
            "$.post_approved_runtime_evidence_gate.status",
            value=gate.get("status"),
        )
    if gate.get("active_after_resolved_input") != REQUIRED_RESOLVED_INPUT:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_active_input_mismatch",
            "$.post_approved_runtime_evidence_gate.active_after_resolved_input",
            value=gate.get("active_after_resolved_input"),
        )
    for key in ("reported_current_blocker", "next_blocker"):
        if gate.get(key) != NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE:
            add(
                blockers,
                f"post_approved_runtime_evidence_gate_{key}_mismatch",
                f"$.post_approved_runtime_evidence_gate.{key}",
                value=gate.get(key),
            )
    if string_list(gate.get("required_unresolved_decision_keys")) != (
        REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS
    ):
        add(
            blockers,
            "post_approved_runtime_evidence_gate_required_decision_keys_mismatch",
            "$.post_approved_runtime_evidence_gate.required_unresolved_decision_keys",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
            observed=gate.get("required_unresolved_decision_keys"),
        )
    audit_inputs = string_list(gate.get("auditable_inputs"))
    if audit_inputs is None or set(audit_inputs) != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_auditable_inputs_mismatch",
            "$.post_approved_runtime_evidence_gate.auditable_inputs",
            expected=sorted(REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS),
            observed=gate.get("auditable_inputs"),
        )
    if gate.get("next_required_artifact") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_next_required_artifact_mismatch",
            "$.post_approved_runtime_evidence_gate.next_required_artifact",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
            observed=gate.get("next_required_artifact"),
        )
    if gate.get("offline_preparation") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_offline_preparation_mismatch",
            "$.post_approved_runtime_evidence_gate.offline_preparation",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
            observed=gate.get("offline_preparation"),
        )
    next_required_artifact = gate.get("next_required_artifact")
    observed_alias_policy = (
        next_required_artifact.get("non_counting_candidate_alias_policy")
        if isinstance(next_required_artifact, dict)
        else None
    )
    if observed_alias_policy != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_non_counting_candidate_alias_policy_mismatch",
            "$.post_approved_runtime_evidence_gate.next_required_artifact.non_counting_candidate_alias_policy",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY,
            observed=observed_alias_policy,
        )
    for key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS:
        if gate.get(key) is not False:
            add(
                blockers,
                f"post_approved_runtime_evidence_gate_{key}_not_false",
                f"$.post_approved_runtime_evidence_gate.{key}",
                value=gate.get(key),
            )
    for key in POST_APPROVED_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS:
        if key in gate and gate.get(key) is not False:
            add(
                blockers,
                f"post_approved_runtime_evidence_gate_{key}_not_false",
                f"$.post_approved_runtime_evidence_gate.{key}",
                value=gate.get(key),
            )
    if gate.get("non_claim") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM:
        add(
            blockers,
            "post_approved_runtime_evidence_gate_non_claim_mismatch",
            "$.post_approved_runtime_evidence_gate.non_claim",
            value=gate.get("non_claim"),
        )


def validate_post_runtime_identity_contract_checklist_policy(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    policy = decisions.get("post_runtime_identity_contract_checklist_policy")
    if not isinstance(policy, dict):
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_missing",
            "$.post_runtime_identity_contract_checklist_policy",
            observed=policy,
        )
        return
    if policy != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY:
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_mismatch",
            "$.post_runtime_identity_contract_checklist_policy",
            expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY,
            observed=policy,
        )
    if policy.get("required_item_ids") != POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS:
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_required_item_ids_mismatch",
            "$.post_runtime_identity_contract_checklist_policy.required_item_ids",
            expected=POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS,
            observed=policy.get("required_item_ids"),
        )
    if policy.get("must_remain_false") != list(POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS):
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_must_remain_false_mismatch",
            "$.post_runtime_identity_contract_checklist_policy.must_remain_false",
            expected=list(POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS),
            observed=policy.get("must_remain_false"),
        )
    items = policy.get("items")
    if not isinstance(items, list):
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_items_not_list",
            "$.post_runtime_identity_contract_checklist_policy.items",
            observed=items,
        )
        return
    expected_items = {
        item["id"]: item for item in REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY["items"]
    }
    observed_ids = [
        item.get("id") if isinstance(item, dict) else None
        for item in items
    ]
    if observed_ids != POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS:
        add(
            blockers,
            "post_runtime_identity_contract_checklist_policy_item_order_mismatch",
            "$.post_runtime_identity_contract_checklist_policy.items",
            expected=POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS,
            observed=observed_ids,
        )
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            add(
                blockers,
                "post_runtime_identity_contract_checklist_policy_item_not_object",
                f"$.post_runtime_identity_contract_checklist_policy.items[{index}]",
                observed=item,
            )
            continue
        expected_item = expected_items.get(item.get("id"))
        if expected_item is None:
            continue
        for key in ("checker", "required_next_action", "blocks_until", "review_scope", "non_claim"):
            if item.get(key) != expected_item.get(key):
                add(
                    blockers,
                    f"post_runtime_identity_contract_checklist_policy_item_{key}_mismatch",
                    f"$.post_runtime_identity_contract_checklist_policy.items[{index}].{key}",
                    item_id=item.get("id"),
                    expected=expected_item.get(key),
                    observed=item.get(key),
                )
        for key in (
            "counts_as_public_readiness",
            "counts_toward_public_sdk",
            "counts_toward_p0_dependency_chain_claim",
            "accepted_for_public_header_gate_review",
            "public_header_allowed",
            "promotion_ready",
        ):
            if item.get(key) is not False:
                add(
                    blockers,
                    f"post_runtime_identity_contract_checklist_policy_item_{key}_not_false",
                    f"$.post_runtime_identity_contract_checklist_policy.items[{index}].{key}",
                    item_id=item.get("id"),
                    value=item.get(key),
                )
        if item.get("p0_progress_contribution") != 0:
            add(
                blockers,
                "post_runtime_identity_contract_checklist_policy_item_p0_progress_contribution_not_zero",
                f"$.post_runtime_identity_contract_checklist_policy.items[{index}].p0_progress_contribution",
                item_id=item.get("id"),
                value=item.get("p0_progress_contribution"),
            )


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    validate_public_text_overclaims(decisions, blockers, label="decisions")
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
    validate_alias_guardrails(decisions, blockers)
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
        if intake.get("required_checker") != "scripts/check_player_identity_public_contract_readiness.py":
            add(blockers, "approved_runtime_evidence_intake_checker_mismatch", "$.approved_runtime_evidence_intake.required_checker")
        validate_approved_runtime_source_provenance_policy(
            intake.get("source_provenance_policy"),
            blockers,
            "$.approved_runtime_evidence_intake.source_provenance_policy",
            "approved_runtime_evidence_intake_source_provenance_policy_mismatch",
        )
        if intake.get("non_claim") != REQUIRED_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM:
            add(blockers, "approved_runtime_evidence_intake_non_claim_mismatch", "$.approved_runtime_evidence_intake.non_claim")
        for key in (
            "promotion_ready",
            "public_contract_allowed",
            "public_sdk_ready",
            "runtime_ready",
            "public_api_ready",
            "public_abi_ready",
            "public_header_allowed",
            "lookup_ready",
            "permissions_ready",
            "commands_ready",
            "v1_completion_evidence",
        ):
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

    planning_source_intake = decisions.get("source_bound_planning_manifest_verification_intake")
    if not isinstance(planning_source_intake, dict):
        add(blockers, "source_bound_planning_manifest_verification_intake_missing", "$.source_bound_planning_manifest_verification_intake")
    else:
        if planning_source_intake.get("id") != REQUIRED_PLANNING_SOURCE_VERIFICATION_INTAKE_ID:
            add(blockers, "source_bound_planning_manifest_verification_intake_id_mismatch", "$.source_bound_planning_manifest_verification_intake.id")
        if planning_source_intake.get("status") != "repo_source_bound_verification_required":
            add(blockers, "source_bound_planning_manifest_verification_intake_status_mismatch", "$.source_bound_planning_manifest_verification_intake.status")
        if planning_source_intake.get("resolved_input") != REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT:
            add(blockers, "source_bound_planning_manifest_verification_intake_resolved_input_mismatch", "$.source_bound_planning_manifest_verification_intake.resolved_input")
        if planning_source_intake.get("required_checker") != REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER:
            add(blockers, "source_bound_planning_manifest_verification_intake_checker_mismatch", "$.source_bound_planning_manifest_verification_intake.required_checker")
        if planning_source_intake.get("default_manifest_dir") != str(DEFAULT_PLANNING_SOURCES_DIR):
            add(blockers, "source_bound_planning_manifest_verification_intake_default_manifest_dir_mismatch", "$.source_bound_planning_manifest_verification_intake.default_manifest_dir")
        if planning_source_intake.get("non_claim") != REQUIRED_PLANNING_SOURCE_VERIFICATION_NON_CLAIM:
            add(blockers, "source_bound_planning_manifest_verification_intake_non_claim_mismatch", "$.source_bound_planning_manifest_verification_intake.non_claim")
        for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed", "public_abi_ready", "v1_completion_evidence"):
            if planning_source_intake.get(key) is not False:
                add(blockers, f"source_bound_planning_manifest_verification_intake_{key}_not_false", f"$.source_bound_planning_manifest_verification_intake.{key}")

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

    owner_token_intake = decisions.get("owner_token_sdk_consumer_contract_intake")
    if not isinstance(owner_token_intake, dict):
        add(blockers, "owner_token_sdk_consumer_contract_intake_missing", "$.owner_token_sdk_consumer_contract_intake")
    else:
        if owner_token_intake.get("id") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_INTAKE_ID:
            add(blockers, "owner_token_sdk_consumer_contract_intake_id_mismatch", "$.owner_token_sdk_consumer_contract_intake.id")
        if owner_token_intake.get("status") != "repo_candidate_contract_required":
            add(
                blockers,
                "owner_token_sdk_consumer_contract_intake_status_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.status",
            )
        if owner_token_intake.get("resolved_input") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT:
            add(
                blockers,
                "owner_token_sdk_consumer_contract_intake_resolved_input_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.resolved_input",
            )
        if owner_token_intake.get("required_checker") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_CHECKER:
            add(
                blockers,
                "owner_token_sdk_consumer_contract_intake_checker_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.required_checker",
            )
        if owner_token_intake.get("default_manifest") != str(DEFAULT_OWNER_TOKEN_SDK_CONSUMER_CONTRACT):
            add(
                blockers,
                "owner_token_sdk_consumer_contract_intake_default_manifest_mismatch",
                "$.owner_token_sdk_consumer_contract_intake.default_manifest",
            )
        if owner_token_intake.get("non_claim") != REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_NON_CLAIM:
            add(
                blockers,
                "owner_token_sdk_consumer_contract_intake_non_claim_mismatch",
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
                    f"owner_token_sdk_consumer_contract_intake_{key}_not_false",
                    f"$.owner_token_sdk_consumer_contract_intake.{key}",
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
    validate_post_approved_runtime_evidence_gate(decisions, blockers)
    validate_post_runtime_identity_contract_checklist_policy(decisions, blockers)

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

    contract_gate_inputs = decisions.get("contract_gate_inputs")
    if not isinstance(contract_gate_inputs, list):
        add(blockers, "contract_gate_inputs_not_list", "$.contract_gate_inputs")
    else:
        by_id = {
            item.get("id"): item
            for item in contract_gate_inputs
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if set(by_id) != set(REQUIRED_CONTRACT_GATE_INPUTS):
            add(
                blockers,
                "contract_gate_inputs_mismatch",
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
                    "contract_gate_input_not_unresolved",
                    "$.contract_gate_inputs",
                    id=input_id,
                    value=item.get("status"),
                )
            if set(item.get("review_inputs", [])) != required["review_inputs"]:
                add(
                    blockers,
                    "contract_gate_input_review_inputs_mismatch",
                    "$.contract_gate_inputs.review_inputs",
                    id=input_id,
                    expected=sorted(required["review_inputs"]),
                    observed=item.get("review_inputs"),
                )
            if set(item.get("remaining_promotion_inputs", [])) != required["remaining_promotion_inputs"]:
                add(
                    blockers,
                    "contract_gate_input_remaining_promotion_inputs_mismatch",
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
                        "contract_gate_input_flag_not_false",
                        f"$.contract_gate_inputs[{input_id}].{key}",
                        id=input_id,
                        value=item.get(key),
                    )

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


def contract_gate_input_details(
    decisions: dict[str, Any],
    *,
    runtime_input_resolved: bool,
    runtime_start_end_context_present: bool = False,
    redaction_report: dict[str, Any],
    principal_policy_report: dict[str, Any],
    planning_source_report: dict[str, Any],
    public_abi_preflight_report: dict[str, Any],
    owner_token_sdk_consumer_report: dict[str, Any],
) -> list[dict[str, Any]]:
    accepted_review_inputs: set[str] = set()
    if runtime_input_resolved:
        accepted_review_inputs.add(REQUIRED_RESOLVED_INPUT)
        if redaction_report.get("accepted_for_contract_review") is True:
            accepted_review_inputs.add(REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT)
        if principal_policy_report.get("accepted_for_policy_review") is True:
            accepted_review_inputs.add(PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT)
        if planning_source_report.get("accepted_for_contract_review") is True:
            accepted_review_inputs.add(REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT)
        if public_abi_preflight_report.get("contract_review_inputs_accepted", {}).get(
            "abi.public_pod_contract.private_layout_candidate"
        ) is True:
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
        missing_review_inputs = [item for item in review_inputs if item not in accepted_review_inputs]
        strict_review_inputs_unresolved = (
            [REQUIRED_RESOLVED_INPUT]
            if input_id == REQUIRED_RESOLVED_INPUT
            and runtime_start_end_context_present
            and not runtime_input_resolved
            else []
        )
        non_counting_review_inputs_present = (
            [PRINCIPAL_START_END_RESOLVED_INPUT]
            if input_id == REQUIRED_RESOLVED_INPUT
            and runtime_start_end_context_present
            and not runtime_input_resolved
            else []
        )
        details.append(
            {
                "id": input_id,
                "status": "unresolved",
                "review_inputs": review_inputs,
                "review_inputs_resolved": resolved_review_inputs,
                "review_inputs_missing": missing_review_inputs,
                "strict_review_inputs_unresolved": strict_review_inputs_unresolved,
                "non_counting_review_inputs_present": non_counting_review_inputs_present,
                "review_inputs_non_counting_until": None
                if runtime_input_resolved or input_id == "runtime.lifecycle_evidence"
                else REQUIRED_RESOLVED_INPUT,
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


def remaining_contract_review_inputs(contract_gate_details: list[dict[str, Any]]) -> list[str]:
    remaining: list[str] = []
    seen: set[str] = set()
    for detail in contract_gate_details:
        missing_inputs = []
        for key in ("review_inputs_missing", "strict_review_inputs_unresolved"):
            missing = detail.get(key, [])
            if isinstance(missing, list):
                missing_inputs.extend(missing)
        for item in missing_inputs:
            if isinstance(item, str) and item not in seen:
                remaining.append(item)
                seen.add(item)
    return remaining


def public_identity_non_promotional_reasons(
    runtime_evidence_accepted: bool,
    principal_start_end_runtime_evidence_accepted: bool = False,
) -> list[str]:
    if runtime_evidence_accepted:
        evidence_reason = (
            "runtime lifecycle evidence intake has consume-only scope; "
            "identity promotion remains blocked pending reviewed identity-contract evidence"
        )
    elif principal_start_end_runtime_evidence_accepted:
        evidence_reason = (
            "principal start/end runtime evidence has contract-review-only scope; rejected-start "
            "CheckJoin proof and the approved runtime bundle remain unresolved"
        )
    else:
        evidence_reason = (
            "runtime principal lifecycle evidence is absent; identity promotion remains blocked "
            "pending accepted runtime lifecycle evidence and reviewed identity-contract evidence"
        )
    return [
        evidence_reason,
        "planning-only, passive, diagnostic, preflight/window, receipt, sidecar, scoped-statement, "
        "certificate, multi-surface beta capture plan/pack/queue, and readiness-alias artifacts "
        "cannot resolve runtime.lifecycle_evidence or identity promotion",
        "candidate/privacy/lifetime/ABI artifacts are review inputs only and add no header "
        "symbols, capability bits, callbacks, lookup, persistence, mutation, return override, runtime "
        "gate state, SDK/API/ABI gate state, permissions/admin, command/chat surfaces, or v1 completion",
        "identity_public_contract_gate review must still cover privacy, lifetime/invalidation, "
        "process-local scope, POD ABI, owner-token lifecycle, SDK consumer behavior, and append-only "
        "layout tests; header, capability, and callback topics remain closed",
    ]


def post_approved_runtime_evidence_gate_report(
    decisions: dict[str, Any],
    *,
    runtime_evidence_accepted: bool,
    runtime_contract_input_kind: str = "approved_runtime_principal_lifecycle_evidence",
    identity_contract_decision_report: dict[str, Any],
    gate_inputs_valid: bool,
) -> dict[str, Any]:
    gate = decisions.get("post_approved_runtime_evidence_gate")
    if not isinstance(gate, dict):
        gate = {}
    decision_record_accepted = (
        gate_inputs_valid
        and runtime_evidence_accepted
        and identity_contract_decision_report.get("accepted_for_contract_review") is True
    )
    remaining_decision_keys = remaining_post_approved_runtime_evidence_decision_keys(decisions)
    if decision_record_accepted:
        resolved_keys = set(identity_contract_decision_report.get("resolved_decision_keys", []))
        remaining_decision_keys = [key for key in remaining_decision_keys if key not in resolved_keys]
    identity_contract_gate_complete = False
    next_required_artifact = gate.get("next_required_artifact")
    if decision_record_accepted:
        next_required_artifact = {
            **REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
            "status": "accepted_for_contract_review",
        }
    return {
        "id": gate.get("id"),
        "status": gate.get("status"),
        "active": runtime_evidence_accepted,
        "runtime_contract_input_kind": runtime_contract_input_kind if runtime_evidence_accepted else "none",
        "accepted_decision_record_as_next_identity_contract_input": decision_record_accepted,
        "public_header_readiness_from_decision_record": False,
        "accepted_decision_record_opens_public_header_gate": False,
        "runtime_evidence_contract_review_currentness": identity_contract_decision_report.get(
            "runtime_evidence_contract_review_currentness",
            public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
        ),
        "identity_contract_gate_complete": identity_contract_gate_complete,
        "active_after_resolved_input": gate.get("active_after_resolved_input"),
        "reported_current_blocker": gate.get("reported_current_blocker"),
        "next_blocker": gate.get("next_blocker"),
        "required_unresolved_decision_keys": gate.get("required_unresolved_decision_keys", []),
        "remaining_unresolved_decision_keys": remaining_decision_keys,
        "auditable_inputs": gate.get("auditable_inputs", []),
        "next_required_artifact": next_required_artifact,
        "offline_preparation": gate.get(
            "offline_preparation",
            REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
        ),
        "non_counting_candidate_alias_policy": (
            REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_COUNTING_CANDIDATE_ALIAS_POLICY
        ),
        "promotion_ready": False,
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
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "commands_ready": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_ready": False,
        "complete_sdk_ready": False,
        "complete_sdk_counting_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "mutation_allowed": False,
        "mutation_ready": False,
        "return_override_allowed": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "non_claim": gate.get("non_claim"),
    }


def post_runtime_public_identity_gap_summary(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    current_blocker: str,
    next_blocker: str,
) -> dict[str, Any]:
    missing_review_keys = (
        []
        if identity_contract_decision_accepted or not runtime_evidence_accepted
        else list(REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS)
    )
    remaining_header_keys = (
        list(POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS)
        if runtime_evidence_accepted
        else []
    )
    remaining_identity_keys = missing_review_keys + remaining_header_keys
    return {
        "active": runtime_evidence_accepted,
        "current_blocker": current_blocker,
        "next_blocker": next_blocker,
        "only_valid_post_runtime_route": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
        "candidate_preflight_review_aliases_count": False,
        "approved_runtime_bundle_consumed": runtime_evidence_accepted,
        "approved_runtime_evidence_scope": "consume_only_contract_review_input",
        "approved_runtime_resolved_input": REQUIRED_RESOLVED_INPUT if runtime_evidence_accepted else None,
        "runtime_bundle_consumed_decision_keys": (
            list(POST_RUNTIME_APPROVED_BUNDLE_CONSUMED_DECISION_KEYS)
            if runtime_evidence_accepted
            else []
        ),
        "missing_identity_contract_review_decision_keys": missing_review_keys,
        "remaining_public_header_decision_keys": remaining_header_keys,
        "smallest_remaining_public_identity_decision_keys": (
            remaining_identity_keys if runtime_evidence_accepted else []
        ),
        "deferred_downstream_surface_gaps": POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACE_GAPS,
        "downstream_surfaces_deferred_until_identity_promotion": [
            "permissions_admin",
            "command_chat_response",
            "commands_replies",
            "player_lookup",
            "storage_persistence",
        ],
        "permissions_admin_opened": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
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
        "commands_ready": False,
        "v1_completion_evidence": False,
        "public_sdk_v1_completion_ready": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": (
            "A checker-accepted approved runtime bundle only consumes the runtime lifecycle evidence "
            "input and routes to identity_public_contract_gate_missing; the remaining keys are public "
            "identity contract/header review gaps and do not open permissions/admin, commands, lookup, "
            "public API/ABI/header, SDK readiness, runtime readiness, P0 progress, or v1 completion."
        ),
    }


def post_runtime_contract_gap_diagnostic(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    identity_contract_decision_report: dict[str, Any],
    current_blocker: str,
    next_blocker: str,
    post_runtime_evidence_gate: dict[str, Any],
) -> dict[str, Any]:
    immediate_missing_artifacts = []
    if runtime_evidence_accepted and not identity_contract_decision_accepted:
        immediate_missing_artifacts.append("reviewed_identity_public_contract_decision_record")
    record_blockers = identity_contract_decision_report.get("blockers", [])
    if not isinstance(record_blockers, list):
        record_blockers = []
    next_required_artifact = post_runtime_evidence_gate.get("next_required_artifact")
    if not isinstance(next_required_artifact, dict):
        next_required_artifact = REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT
    missing_review_keys = (
        []
        if identity_contract_decision_accepted or not runtime_evidence_accepted
        else list(REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS)
    )
    remaining_header_keys = (
        list(POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS)
        if runtime_evidence_accepted
        else []
    )
    remaining_decision_keys = post_runtime_evidence_gate.get("remaining_unresolved_decision_keys", [])
    if not isinstance(remaining_decision_keys, list):
        remaining_decision_keys = []
    return {
        "active": runtime_evidence_accepted,
        "fail_closed": True,
        "current_blocker": current_blocker,
        "next_blocker": next_blocker,
        "only_valid_post_runtime_route": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
        "approved_runtime_bundle_consumed": runtime_evidence_accepted,
        "approved_runtime_evidence_scope": (
            "consume_only_contract_review_input"
            if runtime_evidence_accepted
            else "missing_approved_runtime_bundle"
        ),
        "reviewed_decision_record_status": (
            "accepted_for_contract_review"
            if identity_contract_decision_accepted
            else "missing_or_not_accepted"
            if runtime_evidence_accepted
            else "blocked_until_approved_runtime_evidence"
        ),
        "immediate_missing_artifacts": immediate_missing_artifacts,
        "next_required_artifact": next_required_artifact,
        "decision_record_blockers": record_blockers if runtime_evidence_accepted else [],
        "missing_identity_contract_review_decision_keys": missing_review_keys,
        "remaining_public_header_decision_keys": remaining_header_keys,
        "remaining_unresolved_decision_keys": remaining_decision_keys,
        "deferred_downstream_surface_gaps": POST_RUNTIME_DEFERRED_DOWNSTREAM_SURFACE_GAPS,
        "blocked_surfaces_must_remain_false": POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_BLOCKED_SURFACES,
        "offline_preparation": post_runtime_evidence_gate.get("offline_preparation"),
        "does_not_unlock_identity_public_contract_gate": True,
        "does_not_unlock_public_header_gate": True,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "public_readiness": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": REQUIRED_POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_NON_CLAIM,
    }


def post_runtime_identity_contract_checklist_item(item: dict[str, Any]) -> dict[str, Any]:
    policy = POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_POLICY_BY_ID.get(item.get("id"), {})
    return {
        **item,
        "required_next_action": policy.get("required_next_action"),
        "blocks_until": policy.get("blocks_until"),
        "review_scope": policy.get("review_scope"),
        "counts_as_public_readiness": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_contribution": 0,
        "complete_sdk_claim_progress_contribution": 0,
        "accepted_for_public_header_gate_review": False,
        "public_header_allowed": False,
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "v1_completion_evidence": False,
        "non_claim": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM,
    }


def post_runtime_identity_contract_checklist(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    current_blocker: str,
    next_blocker: str,
    redaction_report: dict[str, Any],
    principal_policy_report: dict[str, Any],
    planning_source_report: dict[str, Any],
    public_abi_preflight_report: dict[str, Any],
    owner_token_sdk_consumer_report: dict[str, Any],
    post_runtime_evidence_gate: dict[str, Any],
    header_fail_closed_path: dict[str, Any],
) -> dict[str, Any]:
    reviewed_contract_status = (
        "accepted_for_contract_review"
        if identity_contract_decision_accepted
        else "missing_or_not_accepted"
        if runtime_evidence_accepted
        else "blocked_until_approved_runtime_evidence"
    )
    immediate_next_artifact = (
        REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT
        if identity_contract_decision_accepted
        else REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT
        if runtime_evidence_accepted
        else {
            "id": "approved_runtime_principal_lifecycle_evidence_bundle",
            "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            "required_resolved_input": REQUIRED_RESOLVED_INPUT,
            "status": "missing_or_not_accepted",
        }
    )
    reviewed_contract_missing_keys = (
        []
        if identity_contract_decision_accepted or not runtime_evidence_accepted
        else list(REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS)
    )
    remaining_public_header_keys = (
        list(POST_RUNTIME_PUBLIC_IDENTITY_HEADER_DECISION_GAP_KEYS)
        if runtime_evidence_accepted
        else []
    )
    checklist_items = [
        {
            "id": "approved_runtime_principal_lifecycle_evidence_bundle",
            "status": "accepted" if runtime_evidence_accepted else "missing_or_not_accepted",
            "checker": "scripts/check_player_identity_runtime_principal_lifecycle_approved_evidence.py",
            "resolved_input": REQUIRED_RESOLVED_INPUT if runtime_evidence_accepted else None,
            "counts_as_reviewed_identity_contract": False,
        },
        {
            "id": "reviewed_identity_public_contract_decision_record",
            "status": reviewed_contract_status,
            "checker": "scripts/check_player_identity_public_contract_decision_record.py",
            "must_bind_to_approved_runtime_evidence": True,
            "must_bind_current_source_artifacts": True,
            "must_resolve_decision_keys": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS,
            "missing_decision_keys": reviewed_contract_missing_keys,
            "accepted_for_public_header_gate_review": False,
        },
        {
            "id": "identifier_redaction_evidence",
            "status": (
                "accepted_for_contract_review"
                if redaction_report.get("accepted_for_contract_review") is True
                else "missing_or_not_accepted"
            ),
            "checker": REQUIRED_IDENTIFIER_REDACTION_CHECKER,
            "resolved_input": (
                REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT
                if redaction_report.get("accepted_for_contract_review") is True
                else None
            ),
            "promotion_ready": False,
        },
        {
            "id": "principal_invalidation_policy",
            "status": (
                "accepted_for_policy_review"
                if principal_policy_report.get("accepted_for_policy_review") is True
                else "missing_or_not_accepted"
            ),
            "checker": REQUIRED_PRINCIPAL_INVALIDATION_POLICY_CHECKER,
            "resolved_input": (
                PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT
                if principal_policy_report.get("accepted_for_policy_review") is True
                else None
            ),
            "promotion_ready": False,
        },
        {
            "id": "public_abi_preflight_candidate",
            "status": (
                "accepted_for_candidate_review"
                if public_abi_preflight_report.get("accepted_for_candidate_review") is True
                else "missing_or_not_accepted"
            ),
            "checker": REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_CHECKER,
            "resolved_input": (
                REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT
                if public_abi_preflight_report.get("accepted_for_candidate_review") is True
                else None
            ),
            "public_abi_ready": False,
        },
        {
            "id": "owner_token_sdk_consumer_contract",
            "status": (
                "accepted_for_candidate_review"
                if owner_token_sdk_consumer_report.get("accepted_for_candidate_review") is True
                else "missing_or_not_accepted"
            ),
            "checker": REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_CHECKER,
            "resolved_input": (
                REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT
                if owner_token_sdk_consumer_report.get("accepted_for_candidate_review") is True
                else None
            ),
            "sdk_consumer_ready": False,
        },
        {
            "id": "source_bound_planning_manifest_verification",
            "status": (
                "accepted_for_contract_review"
                if planning_source_report.get("accepted_for_contract_review") is True
                else "provenance_only" if planning_source_report.get("provenance_verified") is True else "missing_or_not_accepted"
            ),
            "checker": REQUIRED_PLANNING_SOURCE_VERIFICATION_CHECKER,
            "resolved_input": (
                REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT
                if planning_source_report.get("accepted_for_contract_review") is True
                else None
            ),
            "promotion_ready": False,
        },
        {
            "id": "player_identity_public_header_gate_proposal",
            "status": (
                "candidate_only_fail_closed_next_artifact"
                if identity_contract_decision_accepted
                else "blocked_until_reviewed_identity_contract"
                if runtime_evidence_accepted
                else "blocked_until_approved_runtime_evidence"
            ),
            "checker": "scripts/check_player_identity_public_header_gate.py",
            "next_fail_closed_blocker": header_fail_closed_path.get("next_fail_closed_blocker"),
            "public_header_allowed": False,
        },
    ]
    checklist_items = [
        post_runtime_identity_contract_checklist_item(item) for item in checklist_items
    ]
    return {
        "present": True,
        "active": runtime_evidence_accepted,
        "fail_closed": True,
        "current_blocker": current_blocker,
        "next_blocker": next_blocker,
        "runtime_evidence_status": (
            "accepted" if runtime_evidence_accepted else "missing_or_not_accepted"
        ),
        "reviewed_identity_contract_status": reviewed_contract_status,
        "approved_runtime_resolved_input": (
            REQUIRED_RESOLVED_INPUT if runtime_evidence_accepted else None
        ),
        "only_valid_post_runtime_route": NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
        "after_reviewed_contract_fail_closed_blocker": (
            header_fail_closed_path.get("next_fail_closed_blocker")
        ),
        "immediate_next_artifact": immediate_next_artifact,
        "policy": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY,
        "required_item_ids": POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_IDS,
        "items": checklist_items,
        "missing_review_decision_keys": reviewed_contract_missing_keys,
        "remaining_public_header_decision_keys": remaining_public_header_keys,
        "remaining_unresolved_decision_keys": post_runtime_evidence_gate.get(
            "remaining_unresolved_decision_keys",
            [],
        ),
        "must_remain_false": list(POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FLAGS),
        "accepted_for_public_header_gate_review": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "non_claim": REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM,
    }


def public_header_fail_closed_path(
    *,
    runtime_evidence_accepted: bool,
    identity_contract_decision_accepted: bool,
    current_blocker: str,
) -> dict[str, Any]:
    if not runtime_evidence_accepted:
        status = "blocked_until_strict_approved_runtime_evidence"
        next_fail_closed_blocker = "approved_runtime_evidence_missing"
        next_required_artifact: dict[str, Any] | None = None
    elif not identity_contract_decision_accepted:
        status = "blocked_until_reviewed_identity_public_contract_decision_record"
        next_fail_closed_blocker = NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE
        next_required_artifact = REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT
    else:
        status = "candidate_public_header_gate_review_available_fail_closed"
        next_fail_closed_blocker = NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW
        next_required_artifact = REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT

    return {
        "active_after_strict_approved_runtime_evidence": runtime_evidence_accepted,
        "active_after_accepted_reviewed_identity_contract": identity_contract_decision_accepted,
        "status": status,
        "current_blocker": current_blocker,
        "next_fail_closed_blocker": next_fail_closed_blocker,
        "next_required_artifact": next_required_artifact,
        "required_sequence": [
            {
                "id": "approved_runtime_principal_lifecycle_evidence_bundle",
                "status": "accepted" if runtime_evidence_accepted else "missing_or_not_accepted",
                "resolved_input": REQUIRED_RESOLVED_INPUT if runtime_evidence_accepted else None,
                "strict_checker_report_required": True,
            },
            {
                "id": "reviewed_identity_public_contract_decision_record",
                "status": (
                    "accepted_for_contract_review"
                    if identity_contract_decision_accepted
                    else "missing_or_not_accepted"
                    if runtime_evidence_accepted
                    else "blocked_until_strict_runtime_evidence"
                ),
                "must_bind_to_approved_runtime_evidence": True,
                "must_bind_current_source_artifacts": True,
                "accepted_shortcut_aliases": False,
            },
            {
                "id": "player_identity_public_header_gate_proposal",
                "status": (
                    "candidate_only_fail_closed_next_artifact"
                    if identity_contract_decision_accepted
                    else "blocked_until_reviewed_identity_contract"
                ),
                "checker": "scripts/check_player_identity_public_header_gate.py",
                "accepted_for_header_gate_review": False,
                "public_header_allowed": False,
            },
        ],
        "shortcut_aliases_allowed": False,
        "candidate_aliases_count": False,
        "accepted_decision_record_opens_public_header_gate": False,
        "public_header_readiness_from_decision_record": False,
        "public_header_gate_ready": False,
        "public_header_gate_unlocked": False,
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "runtime_readiness": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "must_remain_false": list(REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_FALSE_FLAGS),
        "non_claim": REQUIRED_PUBLIC_HEADER_FAIL_CLOSED_PATH_NON_CLAIM,
    }


def build_report(
    decisions: dict[str, Any],
    runtime_report: dict[str, Any],
    identity_contract_decision_report: dict[str, Any],
    redaction_report: dict[str, Any],
    private_candidate_contract: dict[str, Any],
    public_header_report: dict[str, Any],
    blockers: list[dict[str, Any]],
    check_mode: str,
    principal_policy_report: dict[str, Any] | None = None,
    planning_source_report: dict[str, Any] | None = None,
    public_abi_preflight_report: dict[str, Any] | None = None,
    owner_token_sdk_consumer_report: dict[str, Any] | None = None,
    principal_start_end_runtime_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    principal_policy_report = principal_policy_report or {}
    planning_source_report = planning_source_report or {}
    public_abi_preflight_report = public_abi_preflight_report or {}
    owner_token_sdk_consumer_report = owner_token_sdk_consumer_report or {}
    principal_start_end_runtime_report = principal_start_end_runtime_report or {}
    runtime_false_promotion_claims = approved_runtime_false_promotion_claims(runtime_report)
    add_approved_runtime_false_promotion_blockers(blockers, runtime_false_promotion_claims)
    runtime_multi_surface_beta_capture_claims = approved_runtime_report_multi_surface_beta_capture_references(
        runtime_report
    )
    if runtime_multi_surface_beta_capture_claims:
        add(
            blockers,
            "approved_runtime_evidence_multi_surface_beta_capture_candidate_artifact_not_counting",
            "$.approved_runtime_evidence",
            claims=runtime_multi_surface_beta_capture_claims,
        )
    add_binding_shortcut_blockers(
        blockers,
        reason_prefix="approved_runtime_evidence_binding",
        label="$.approved_runtime_evidence.approved_runtime_evidence_binding",
        binding=runtime_report.get("approved_runtime_evidence_binding"),
    )
    decision_binding_multi_surface_beta_capture_claims = multi_surface_beta_capture_candidate_references(
        identity_contract_decision_report.get("approved_runtime_evidence_binding"),
        "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
    )
    if decision_binding_multi_surface_beta_capture_claims:
        add(
            blockers,
            "identity_public_contract_decision_record_multi_surface_beta_capture_binding_not_counting",
            "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
            claims=decision_binding_multi_surface_beta_capture_claims,
        )
    add_binding_shortcut_blockers(
        blockers,
        reason_prefix="identity_public_contract_decision_record_approved_runtime_evidence_binding",
        label="$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
        binding=identity_contract_decision_report.get("approved_runtime_evidence_binding"),
    )
    identity_contract_decision_shortcut_claims = identity_contract_decision_record_shortcut_claims(
        identity_contract_decision_report
    )
    if identity_contract_decision_shortcut_claims:
        add(
            blockers,
            "identity_public_contract_decision_record_header_gate_shortcut_not_counting",
            "$.identity_public_contract_decision_record",
            claims=identity_contract_decision_shortcut_claims,
        )
    approved_runtime_intake_blockers = [
        blocker["reason"]
        for blocker in blockers
        if str(blocker.get("reason", "")).startswith("approved_runtime_evidence_intake")
    ]
    if approved_runtime_intake_blockers and not any(
        blocker.get("reason") == "approved_runtime_evidence_not_accepted"
        for blocker in blockers
    ):
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "$.approved_runtime_evidence",
            reasons=approved_runtime_intake_blockers,
        )
    runtime_evidence_accepted = (
        runtime_report.get("accepted_for_contract_review") is True
        and runtime_report.get("approved_runtime_evidence_present") is True
        and runtime_report.get("runtime_evidence_ready") is True
        and runtime_report.get("promotion_ready") is False
        and runtime_report.get("public_sdk_ready") is False
        and runtime_report.get("runtime_ready") is False
        and not runtime_false_promotion_claims
        and not runtime_multi_surface_beta_capture_claims
        and not approved_runtime_intake_blockers
    )
    principal_start_end_runtime_evidence_accepted = (
        principal_start_end_runtime_report.get("accepted_for_contract_review") is True
        and principal_start_end_runtime_report.get("principal_start_end_runtime_evidence_present") is True
        and principal_start_end_runtime_report.get("principal_start_end_runtime_evidence_ready") is True
        and principal_start_end_runtime_report.get("approved_runtime_evidence_present") is False
        and principal_start_end_runtime_report.get("approved_runtime_evidence_ready") is False
        and principal_start_end_runtime_report.get("runtime_ready") is False
        and principal_start_end_runtime_report.get("public_sdk_ready") is False
    )
    runtime_contract_input_accepted = runtime_evidence_accepted
    runtime_contract_input_kind = (
        "approved_runtime_principal_lifecycle_evidence"
        if runtime_evidence_accepted
        else "none"
    )
    if not runtime_contract_input_accepted:
        add(blockers, "approved_runtime_evidence_missing_or_not_ready", "$.approved_runtime_evidence")
    identity_contract_decision_binding_matches = (
        runtime_evidence_accepted
        and approved_runtime_evidence_binding_matches(runtime_report, identity_contract_decision_report)
    )
    identity_contract_decision_binding_blocked = (
        identity_contract_decision_report.get("provided") is True
        and identity_contract_decision_report.get("accepted_for_contract_review") is True
        and not identity_contract_decision_binding_matches
    )
    if identity_contract_decision_binding_blocked:
        add(
            blockers,
            "identity_public_contract_decision_record_approved_runtime_evidence_binding_not_accepted",
            "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
            required_input=REQUIRED_RESOLVED_INPUT,
            runtime_contract_input_kind=runtime_contract_input_kind,
            strict_approved_runtime_evidence_accepted=runtime_evidence_accepted,
        )
    identity_contract_decision_accepted = (
        runtime_evidence_accepted
        and identity_contract_decision_binding_matches
        and identity_contract_decision_report.get("accepted_for_contract_review") is True
        and not identity_contract_decision_shortcut_claims
    )
    if runtime_evidence_accepted and not identity_contract_decision_accepted:
        add(
            blockers,
            "identity_public_contract_decision_record_missing_or_not_accepted",
            "$.identity_public_contract_decision_record",
            required_input=REQUIRED_RESOLVED_INPUT,
            runtime_contract_input_kind=runtime_contract_input_kind,
            strict_approved_runtime_evidence_accepted=runtime_evidence_accepted,
        )
    if check_mode != "consume":
        add(blockers, f"{check_mode}_blocked_until_player_identity_public_contract_promotion", "$.promotion_blockers")

    evidence_blockers = [
        blocker
        for blocker in blockers
        if not blocker["reason"].endswith("_blocked_until_player_identity_public_contract_promotion")
    ]
    accepted_for_contract_review = not evidence_blockers
    resolved_inputs = []
    if runtime_evidence_accepted:
        resolved_inputs.append(REQUIRED_RESOLVED_INPUT)
    if runtime_contract_input_accepted:
        if redaction_report.get("accepted_for_contract_review") is True:
            resolved_inputs.append(REQUIRED_IDENTIFIER_REDACTION_RESOLVED_INPUT)
        if planning_source_report.get("accepted_for_contract_review") is True:
            resolved_inputs.append(REQUIRED_PLANNING_SOURCE_VERIFICATION_RESOLVED_INPUT)
        if principal_policy_report.get("accepted_for_policy_review") is True:
            resolved_inputs.append(PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT)
        if public_abi_preflight_report.get("contract_review_inputs_accepted", {}).get(
            "abi.public_pod_contract.private_layout_candidate"
        ) is True:
            resolved_inputs.append("abi.public_pod_contract.private_layout_candidate")
        if public_abi_preflight_report.get("accepted_for_candidate_review") is True:
            resolved_inputs.append(REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT)
        if owner_token_sdk_consumer_report.get("accepted_for_candidate_review") is True:
            resolved_inputs.append(REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT)
        resolved_inputs.append("separation.no_commands_permissions_persistence")
    runtime_input_resolved = runtime_evidence_accepted
    non_promotional_reasons = public_identity_non_promotional_reasons(
        runtime_evidence_accepted,
        principal_start_end_runtime_evidence_accepted,
    )
    post_runtime_evidence_gate = post_approved_runtime_evidence_gate_report(
        decisions,
        runtime_evidence_accepted=runtime_evidence_accepted,
        runtime_contract_input_kind=runtime_contract_input_kind,
        identity_contract_decision_report=identity_contract_decision_report,
        gate_inputs_valid=accepted_for_contract_review,
    )
    identity_contract_gate_complete = post_runtime_evidence_gate.get("identity_contract_gate_complete") is True
    identity_contract_decision_keys = (
        identity_contract_decision_report.get("resolved_decision_keys", [])
        if identity_contract_decision_accepted
        else []
    )
    identity_contract_decision_non_counting_until = (
        None
        if identity_contract_decision_accepted or not identity_contract_decision_report.get("provided")
        else REQUIRED_RESOLVED_INPUT
    )
    current_blocker = (
        NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE
        if runtime_evidence_accepted
        else "approved_runtime_evidence_missing"
    )
    post_runtime_gap_summary = post_runtime_public_identity_gap_summary(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=current_blocker,
        next_blocker=current_blocker,
    )
    post_runtime_contract_gap = post_runtime_contract_gap_diagnostic(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        identity_contract_decision_report=identity_contract_decision_report,
        current_blocker=current_blocker,
        next_blocker=current_blocker,
        post_runtime_evidence_gate=post_runtime_evidence_gate,
    )
    header_fail_closed_path = public_header_fail_closed_path(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=current_blocker,
    )
    post_runtime_identity_checklist = post_runtime_identity_contract_checklist(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=current_blocker,
        next_blocker=current_blocker,
        redaction_report=redaction_report,
        principal_policy_report=principal_policy_report,
        planning_source_report=planning_source_report,
        public_abi_preflight_report=public_abi_preflight_report,
        owner_token_sdk_consumer_report=owner_token_sdk_consumer_report,
        post_runtime_evidence_gate=post_runtime_evidence_gate,
        header_fail_closed_path=header_fail_closed_path,
    )
    post_runtime_evidence_gate = {
        **post_runtime_evidence_gate,
        "public_header_fail_closed_path": header_fail_closed_path,
        "post_runtime_identity_contract_checklist": post_runtime_identity_checklist,
    }
    contract_gate_details = contract_gate_input_details(
        decisions,
        runtime_input_resolved=runtime_input_resolved,
        runtime_start_end_context_present=principal_start_end_runtime_evidence_accepted
        and not runtime_evidence_accepted,
        redaction_report=redaction_report,
        principal_policy_report=principal_policy_report,
        planning_source_report=planning_source_report,
        public_abi_preflight_report=public_abi_preflight_report,
        owner_token_sdk_consumer_report=owner_token_sdk_consumer_report,
    )
    remaining_review_inputs = remaining_contract_review_inputs(contract_gate_details)
    return {
        "schema": REPORT_SCHEMA,
        "surface": decisions.get("surface"),
        "mode": check_mode,
        "ready": accepted_for_contract_review and check_mode == "consume",
        "ready_scope": "contract_review_input_only",
        "accepted_for_contract_review": accepted_for_contract_review,
        "resolved_inputs": resolved_inputs,
        "contract_review_inputs_resolved": resolved_inputs,
        "remaining_contract_review_inputs": remaining_review_inputs,
        "remaining_post_runtime_inputs": post_runtime_evidence_gate.get(
            "remaining_unresolved_decision_keys",
            [],
        ),
        "runtime_contract_input": {
            "accepted_for_contract_review": runtime_contract_input_accepted,
            "kind": runtime_contract_input_kind,
            "resolved_input": (
                REQUIRED_RESOLVED_INPUT
                if runtime_evidence_accepted
                else None
            ),
            "strict_approved_runtime_evidence_accepted": runtime_evidence_accepted,
            "principal_start_end_runtime_evidence_accepted": (
                principal_start_end_runtime_evidence_accepted
            ),
            "approved_runtime_principal_lifecycle_evidence_bundle_resolved": runtime_evidence_accepted,
            "strict_runtime_lifecycle_evidence_still_unresolved": not runtime_evidence_accepted,
            "does_not_resolve": (
                sorted(PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS)
                if principal_start_end_runtime_evidence_accepted and not runtime_evidence_accepted
                else []
            ),
            "promotion_ready": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
        },
        "promotion_ready": False,
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
        "public_contract_allowed": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "public_api_ready": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "complete_sdk_counting_allowed": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "mutation_allowed": False,
        "mutation_ready": False,
        "return_override_allowed": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
        "runtime_capture_authorized": False,
        "reads_live_logs": False,
        "public_contract_gate_aliases": alias_guardrails_false(),
        "identity_public_contract_gate_missing": {
            "active": current_blocker == NEXT_BLOCKER_AFTER_APPROVED_RUNTIME_EVIDENCE,
            "runtime_evidence_contract_review_currentness": post_runtime_evidence_gate.get(
                "runtime_evidence_contract_review_currentness"
            ),
            "cannot_unlock_without": [
                "reviewed public identity contract",
                "privacy, redaction, logging, and persistence semantics",
                "principal invalidation and cross-instance/process-local semantics",
                "public ABI/header/capability contract",
                "SDK consumer and append-only ABI tests",
                "promotion certificate or equivalent reviewed release artifact",
            ],
            "next_auditable_blocker": {
                "id": post_runtime_evidence_gate.get("id"),
                "required_unresolved_decision_keys": post_runtime_evidence_gate.get(
                    "required_unresolved_decision_keys"
                ),
                "auditable_inputs": post_runtime_evidence_gate.get("auditable_inputs"),
                "next_required_artifact": post_runtime_evidence_gate.get("next_required_artifact"),
                "offline_preparation": post_runtime_evidence_gate.get("offline_preparation"),
            },
            "post_runtime_contract_gap_diagnostic": post_runtime_contract_gap,
            "post_runtime_identity_contract_checklist": post_runtime_identity_checklist,
            "non_counting_candidate_alias_policy": post_runtime_evidence_gate.get(
                "non_counting_candidate_alias_policy"
            ),
            "redactionEvidencePromotesIdentity": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
        },
        "post_approved_runtime_evidence_gate": post_runtime_evidence_gate,
        "post_runtime_public_header_fail_closed_path": header_fail_closed_path,
        "runtime_evidence_contract_review_currentness": {
            **public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            "runtime_evidence_accepted": runtime_evidence_accepted,
            "reviewed_decision_record_accepted": identity_contract_decision_accepted,
            "current_blocker": current_blocker,
            "next_blocker": current_blocker,
            "candidate_preflight_review_aliases_count": False,
            "permissions_admin_unlocked_from_runtime_evidence": False,
            "command_surface_unlocked_from_runtime_evidence": False,
        },
        "post_runtime_public_identity_gap_summary": post_runtime_gap_summary,
        "post_runtime_contract_gap_diagnostic": post_runtime_contract_gap,
        "post_runtime_identity_contract_checklist": post_runtime_identity_checklist,
        "public_header_gate_missing": {
            "active": current_blocker == NEXT_BLOCKER_AFTER_IDENTITY_CONTRACT_REVIEW,
            "fail_closed_path": header_fail_closed_path,
            "next_required_artifact": REQUIRED_PUBLIC_HEADER_GATE_NEXT_REQUIRED_ARTIFACT,
            "cannot_unlock_without": [
                "approved runtime principal lifecycle evidence bundle",
                "public header proposal review",
                "append-only ABI layout tests",
                "installed SDK consumer tests",
                "owner-token lifecycle cleanup tests",
                "public SDK completion checker non-counting guardrail update",
            ],
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
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
            "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "complete_sdk_counting_allowed": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "mutation_allowed": False,
        "mutation_ready": False,
        "return_override_allowed": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "non_claim": (
                "The public header gate proposal is review-only until the approved runtime bundle, "
                "append-only ABI tests, SDK consumer tests, and owner-token cleanup tests pass; it does "
                "not add header symbols, capability bits, callbacks, lookup, downstream surfaces, "
                "runtime readiness, SDK readiness, or v1 completion."
            ),
        },
        "identity_public_contract_decision_record": {
            "provided": identity_contract_decision_report.get("provided") is True,
            "accepted_for_contract_review": identity_contract_decision_accepted,
            "record_valid": identity_contract_decision_report.get("record_valid") is True,
            "hash_bound_to_current_source_artifacts": identity_contract_decision_report.get(
                "hash_bound_to_current_source_artifacts"
            )
            is True,
            "reviewed_template_only": (
                identity_contract_decision_report.get("reviewed_template_only") is True
            ),
            "strict_accepted_decision_record": (
                identity_contract_decision_report.get("strict_accepted_decision_record") is True
            ),
            "accepted_post_runtime_decision_record": identity_contract_decision_accepted,
            "accepted_as_next_identity_contract_input": identity_contract_decision_accepted,
            "public_header_readiness_from_decision_record": False,
            "contract_review_only": identity_contract_decision_report.get("contract_review_only") is True,
            "reviewed_hash_current_contract_review_only": identity_contract_decision_report.get(
                "reviewed_hash_current_contract_review_only"
            )
            is True,
            "approved_runtime_evidence_binding_matches_accepted_runtime_evidence": (
                identity_contract_decision_binding_matches
            ),
            "approved_runtime_evidence_binding_required_input": REQUIRED_RESOLVED_INPUT,
            "source_artifact_freshness": identity_contract_decision_report.get(
                "source_artifact_freshness",
                {},
            ),
            "runtime_evidence_contract_review_currentness": identity_contract_decision_report.get(
                "runtime_evidence_contract_review_currentness",
                public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            ),
            "identity_contract_gate_complete": identity_contract_gate_complete,
            "resolved_decision_keys": identity_contract_decision_keys,
            "review_inputs_non_counting_until": identity_contract_decision_non_counting_until,
            "next_blocker": identity_contract_decision_report.get("next_blocker"),
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_header_allowed": False,
            "public_abi_ready": False,
            "public_api_ready": False,
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
            "commands_ready": False,
        "v1_ready": False,
        "v1_completion_ready": False,
        "v1_completion_evidence": False,
        "complete_sdk_ready": False,
        "complete_sdk_counting_allowed": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "resource_handle_ready": False,
        "resource_handle_supported": False,
        "mutation_allowed": False,
        "mutation_ready": False,
        "return_override_allowed": False,
        "live_ops_authorized": False,
        "server_operations_authorized": False,
        "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "public_header_symbols_now": [],
            "public_capability_bits_now": [],
            "public_callback_abi_now": [],
            "public_api_symbols_now": [],
            "blockers": identity_contract_decision_report.get("blockers", []),
        },
        "public_identity_non_promotional_reasons": non_promotional_reasons,
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
        "contract_gate_inputs": contract_gate_details,
        "current_blocker": current_blocker,
        "next_blocker": current_blocker,
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
            "accepted_for_contract_review": runtime_report.get("accepted_for_contract_review") is True,
            "approved_runtime_evidence_present": runtime_report.get("approved_runtime_evidence_present") is True,
            "runtime_evidence_ready": runtime_report.get("runtime_evidence_ready") is True,
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_api_ready": False,
            "public_abi_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "stable_ready": False,
            "stable_claim_allowed": False,
            "stable_claim_ready": False,
            "stable_sdk_ready": False,
            "plugin_hub_ready": False,
            "plugin_hub_publication_ready": False,
            "publication_ready": False,
            "publication_authorized": False,
            "public_header_allowed": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_ready": False,
            "v1_completion_ready": False,
            "v1_completion_evidence": False,
            "complete_sdk_ready": False,
            "complete_sdk_counting_allowed": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "complete_sdk_claim_progress_contribution": 0,
            "p0_dependency_chain_claim_progress_contribution": 0,
            "resource_handle_ready": False,
            "resource_handle_supported": False,
            "mutation_allowed": False,
            "mutation_ready": False,
            "return_override_allowed": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "source_provenance_policy": runtime_report.get("source_provenance_policy", {}),
        },
        "principal_start_end_runtime_evidence": {
            "provided": principal_start_end_runtime_report.get("provided") is True,
            "accepted_for_contract_review": principal_start_end_runtime_evidence_accepted,
            "principal_start_end_runtime_evidence_present": principal_start_end_runtime_report.get(
                "principal_start_end_runtime_evidence_present"
            )
            is True,
            "principal_start_end_runtime_evidence_ready": principal_start_end_runtime_report.get(
                "principal_start_end_runtime_evidence_ready"
            )
            is True,
            "resolved_input": (
                PRINCIPAL_START_END_RESOLVED_INPUT
                if principal_start_end_runtime_evidence_accepted
                else None
            ),
            "next_review_blocker": principal_start_end_runtime_report.get("next_review_blocker"),
            "remaining_runtime_inputs": principal_start_end_runtime_report.get(
                "remaining_runtime_inputs", []
            ),
            "strict_approved_runtime_evidence_blockers": principal_start_end_runtime_report.get(
                "strict_approved_runtime_evidence_blockers", []
            ),
            "approved_runtime_evidence_present": False,
            "approved_runtime_evidence_ready": False,
            "approved_runtime_principal_lifecycle_evidence_bundle_resolved": False,
            "does_not_resolve": sorted(PRINCIPAL_START_END_STRICT_UNRESOLVED_INPUTS),
            "promotion_ready": False,
            "public_contract_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_api_ready": False,
            "public_abi_ready": False,
            "public_readiness": False,
            "runtime_readiness": False,
            "public_header_allowed": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_ready": False,
            "v1_completion_ready": False,
            "v1_completion_evidence": False,
            "complete_sdk_ready": False,
            "counts_toward_public_sdk": False,
            "counts_toward_runtime": False,
            "counts_toward_v1_completion": False,
            "counts_toward_complete_sdk_claim": False,
            "counts_toward_p0_dependency_chain_claim": False,
            "p0_progress_ready": False,
            "sdk_p0_progress_ready": False,
            "resource_handle_ready": False,
            "resource_handle_supported": False,
            "mutation_allowed": False,
            "mutation_ready": False,
            "return_override_allowed": False,
            "live_ops_authorized": False,
            "server_operations_authorized": False,
            "workspace_writes_authorized": False,
            "runtime_capture_authorized": False,
            "reads_live_logs": False,
            "blockers": principal_start_end_runtime_report.get("blockers", []),
            "non_claims": principal_start_end_runtime_report.get("non_claims", []),
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
        "source_bound_planning_manifest_verification": planning_source_report,
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
            "approved runtime evidence intake does not add public identity, lookup, public API/ABI/header symbols, capability bits, callbacks, SDK/runtime readiness, permissions/admin, command/chat surfaces, mutation, return override, or v1 completion readiness",
            "principal start/end runtime evidence is non-counting contract-review context only; it is not the approved runtime principal lifecycle evidence bundle and does not resolve runtime.lifecycle_evidence, rejected-start CheckJoin proof, SDK/runtime/public readiness, or publication",
            NON_PROMOTIONAL_EVIDENCE_DENIAL,
            "multi-surface beta capture plan/pack/queue artifacts are candidate-only preparation; they cannot satisfy approved_runtime_evidence_binding, public identity contract readiness, runtime readiness, public SDK readiness, SDK/P0 progress, or v1 completion",
            "identifier-redaction evidence intake does not resolve the full privacy blocker or make public identity, lookup, SDK/runtime/API/ABI, permissions/admin, command/chat, or v1 completion promotion-ready",
            "principal invalidation policy intake is candidate-only and does not resolve the full lifetime/generation/scope blocker, prove runtime lifecycle ordering, or make public identity/downstream surfaces promotion-ready",
            "source-bound planning manifest verification is provenance for contract-review inputs only and does not promote public identity, lookup, public SDK/API/ABI/header/runtime readiness, permissions/admin, command/chat surfaces, or v1 completion",
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
    if args.approved_runtime_evidence and args.principal_start_end_runtime_evidence:
        add(
            blockers,
            "runtime_evidence_sources_ambiguous",
            "$.runtime_contract_input",
            provided=["approved_runtime_evidence", "principal_start_end_runtime_evidence"],
        )
    if args.approved_runtime_evidence:
        runtime_report = approved_runtime_report(args.approved_runtime_evidence, blockers)
    else:
        runtime_report = missing_approved_runtime_report()
        if not args.principal_start_end_runtime_evidence:
            add(blockers, "runtime_evidence_input_missing", "$.runtime_contract_input")
    principal_start_end_report = principal_start_end_runtime_report(
        args.principal_start_end_runtime_evidence,
        blockers,
    )
    identity_contract_decision_report = identity_public_contract_decision_record_report(
        args.identity_public_contract_decision_record,
        blockers,
    )
    redaction_report = identifier_redaction_report(args.identifier_redaction_evidence, blockers)
    planning_source_report = planning_source_verification_report(
        args.planning_source_snapshot_root,
        args.planning_sources_dir,
        blockers,
    )
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
        identity_contract_decision_report,
        redaction_report,
        private_candidate_contract,
        public_header_report,
        blockers,
        check_mode,
        principal_policy_report,
        planning_source_report,
        public_abi_preflight_report,
        owner_token_sdk_consumer_report,
        principal_start_end_runtime_report=principal_start_end_report,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif blockers:
        for blocker in blockers:
            print(f"{blocker['reason']}: {blocker['label']}", file=sys.stderr)
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
