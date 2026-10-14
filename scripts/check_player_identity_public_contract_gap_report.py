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
REPO_ROOT = SCRIPT_DIR.parent

import check_player_identity_identifier_redaction_evidence as redaction_checker
import check_player_identity_principal_invalidation_policy as principal_invalidation_policy
import check_player_identity_public_abi_preflight_candidate as public_abi_preflight_candidate
import check_player_identity_public_contract_decision_record as public_contract_decision_record
import check_player_identity_private_pod_layout_candidate as private_pod_layout_candidate
import check_player_identity_runtime_principal_lifecycle_approved_evidence as approved_runtime_evidence
import build_player_identity_planning_source_manifests as planning_source_manifests


SCHEMA = "obelisk.player-identity-public-contract-gap-report.v1"
DECISIONS_SCHEMA = "obelisk.player-identity-public-contract-decisions.v1"
SURFACES_SCHEMA = "obelisk.public-sdk-surfaces.v1"
PRIVATE_CANDIDATE_SCHEMA = "obelisk.player-identity-private-candidate-contract.v1"
SURFACE = "obelisk.player_identity.v1"
PERMISSIONS_ADMIN_SURFACE = "obelisk.permissions_admin.v1"
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
DEFAULT_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD = public_contract_decision_record.DEFAULT_RECORD
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
    "promote public player identity, lookup, public SDK/runtime/API/ABI/header readiness, runtime authorization, "
    "permissions/admin, command/chat surfaces, or v1 completion."
)
DEFAULT_FIRST_EVIDENCE_STALE_DIAGNOSTIC = (
    "The committed default players-identity-first-evidence.json is stale against the deterministic "
    "planning-source builder, so it is reported as non-counting provenance and cannot resolve "
    "planning.source_bound_committed_manifests; the no-runtime default gap report remains blocked at "
    "approved_runtime_evidence_missing instead of treating stale planning evidence as readiness."
)
PLANNING_SOURCE_VERIFICATION_REPORT_NON_CLAIMS = [
    "source-bound planning manifest verification is provenance-only contract-review input",
    "source-bound planning manifest verification grants no authorization or promotion",
]
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
    "checklist",
    "checklist_policy",
    "checklist-policy",
    "checklist_row",
    "checklist-row",
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
    "ready_alias",
    "ready-alias",
    "status_json",
    "status-json",
    "status_report",
    "status-report",
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
    "scoped_statement",
    "scoped-statement",
    "scoped_release_statement",
    "scoped-release-statement",
    "scoped_8of8_release_statement",
    "scoped-8of8-release-statement",
    "release_statement",
    "release-statement",
    "8/8",
    "8of8",
    "8-of-8",
    "8_of_8",
    "promotion_certificate",
    "promotion-certificate",
    "completion_certificate",
    "completion-certificate",
    "terminal_certificate",
    "terminal-certificate",
    "observer_env",
    "observer-env",
    "live_ops",
    "live-ops",
    "partial",
    "partial_runtime",
    "partial-runtime",
    "runtime_partial",
    "runtime-partial",
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
    "copied_log_only",
    "copied-log-only",
    "copied_runtime_partial",
    "copied-runtime-partial",
    "truncated",
    "incomplete",
    "installed_runtime",
    "installed-runtime",
    "broadcast_status",
    "broadcast-status",
    "rcon_status",
    "rcon-status",
    "simulation",
    "simulated",
    "synthetic",
    "mock",
    "fixture",
    "cmake_package",
    "cmake-package",
    "find_package",
    "find-package",
    "package_shape",
    "package-shape",
    "bundle_report",
    "bundle-report",
    "bundle_preflight",
    "bundle-preflight",
    "bundle_check",
    "bundle-check",
    "evidence_bundle_report",
    "evidence-bundle-report",
    "runtime_bundle_report",
    "runtime-bundle-report",
    "generated_runtime_bundle_report",
    "generated-runtime-bundle-report",
    "approved_runtime_bundle_report",
    "approved-runtime-bundle-report",
    "handoff",
    "historical_handoff",
    "historical-handoff",
    "compact_context",
    "compact-context",
    "checkpoint",
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
    "closure_or_executor_report": re.compile(
        r"\b(?:closure|executor)[-_ ]+(?:request|report|artifact|shortcut)\b",
        re.IGNORECASE,
    ),
    "status_json_material": re.compile(
        r"\b(?:status[-_ ]?(?:json|report|snapshot)|next[-_ ]?action[-_ ]?status|status\.json)\b",
        re.IGNORECASE,
    ),
    "copied_log_only_material": re.compile(
        r"\bcopied[-_ ]+log[-_ ]+only\b",
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
    "package_shape_material": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk(?:[-_ ]+package[-_ ]+shape)?|package[-_ ]+shape)\b",
        re.IGNORECASE,
    ),
    "checklist_policy_row_material": re.compile(
        r"\b(?:post[-_ ]+runtime[-_ ]+identity[-_ ]+contract[-_ ]+checklist|"
        r"identity[-_ ]+contract[-_ ]+checklist|checklist[-_ ]+(?:policy|row|item|"
        r"action[-_ ]+target|action[-_ ]+list)|post[-_ ]+runtime[-_ ]+checklist)\b",
        re.IGNORECASE,
    ),
    "scoped_8of8_release_statement_row": re.compile(
        r"\b(?:scoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?release[-_ ]+statement|"
        r"release[-_ ]+statement)\b[^\.;\n]{0,100}\b(?:8\s*/\s*8|8[-_ ]?of[-_ ]?8|"
        r"eight[-_ ]+of[-_ ]+eight)\b|"
        r"\b(?:8\s*/\s*8|8[-_ ]?of[-_ ]?8|eight[-_ ]+of[-_ ]+eight)\b"
        r"[^\.;\n]{0,100}\b(?:scoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?release[-_ ]+statement|"
        r"release[-_ ]+statement)\b",
        re.IGNORECASE,
    ),
    "terminal_certificate_material": re.compile(
        r"\b(?:terminal[-_ ]+(?:promotion[-_ ]+|completion[-_ ]+|route[-_ ]+|surface[-_ ]+|"
        r"public[-_ ]+)?certificate|(?:promotion|completion|route|surface|public[-_ ]+sdk|p0)"
        r"[-_ ]+terminal[-_ ]+certificate|terminal[-_ ]+cert)\b",
        re.IGNORECASE,
    ),
    "generated_runtime_bundle_report_material": re.compile(
        r"\b(?:evidence[-_ ]+bundle[-_ ]+report|runtime[-_ ]+(?:evidence[-_ ]+)?bundle[-_ ]+"
        r"(?:report|check|preflight|build[-_ ]+report)|approved[-_ ]+runtime[-_ ]+bundle[-_ ]+"
        r"(?:report|check|preflight|status|request)|bundle[-_ ]+(?:preflight|report|check)|"
        r"post[-_ ]+runtime[-_ ]+bridge[-_ ]+build[-_ ]+report|shutdown[-_ ]+worker[-_ ]+artifact)\b",
        re.IGNORECASE,
    ),
    "installed_runtime_status_material": re.compile(
        r"\b(?:installed[-_ ]+runtime|broadcast[-_ ]+status|rcon[-_ ]+status|"
        r"runtime[-_ ]+(?:broadcast|rcon)[-_ ]+status)\b",
        re.IGNORECASE,
    ),
    "historical_handoff_material": re.compile(
        r"\b(?:historical[-_ ]+handoff|handoff[-_ ]+(?:text|notes?|artifact|context|report)|"
        r"compact[-_ ]+context|checkpoint(?:[-_ ]+(?:handoff|context))?)\b",
        re.IGNORECASE,
    ),
    "support_or_publication_material": re.compile(
        r"\b(?:support[-_ ]+tier|release[-_ ]+support|release[-_ ]+grade[-_ ]+support|"
        r"plugin[-_ ]+hub|pluginhub)(?:[-_ ]+(?:package|support|publication|wording))?\b",
        re.IGNORECASE,
    ),
    "public_header_proposal_artifact": re.compile(
        r"\b(?:public[-_ ]+header(?:[-_ ]+gate)?[-_ ]+proposal|"
        r"header[-_ ]+gate[-_ ]+proposal|header[-_ ]+proposal)\b",
        re.IGNORECASE,
    ),
    "planning_artifact": re.compile(r"\bplanning(?:[-_ ]+only)?\b", re.IGNORECASE),
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
        r"command[-_ ]+response|chat[-_ ]+replies|send[-_ ]+chat)[-_ ]+"
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
}
REQUIRED_APPROVED_RUNTIME_EVIDENCE_INTAKE_ID = "approved_runtime_principal_lifecycle_evidence"
REQUIRED_APPROVED_RUNTIME_EVIDENCE_CHECKER = "scripts/check_player_identity_public_contract_readiness.py"
REQUIRED_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM = (
    "A valid approved runtime evidence manifest can resolve only the runtime lifecycle "
    "evidence input for public-contract review; it does not promote public player identity, lookup, "
    "public SDK/runtime/API/ABI/header readiness, permissions/admin, command/chat surfaces, or v1 completion."
)
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
        "post-runtime bridge build reports, shutdown-worker artifacts, historical handoff text, "
        "diagnostic-only, passive, "
        "request/preflight/window/receipt/sidecar/scoped-statement/certificate/simulation/mock/fixture artifacts "
        "remain non-counting and cannot open the public identity contract gate."
    ),
}
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
    "publicAbiReady",
    "publicAbiReadiness",
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
    "pluginHubPackageShapeReady",
    "pluginHubPlanningReady",
    "pluginHubPublication",
    "pluginHubPublicationReady",
    "pluginHubPublished",
    "pluginHubReady",
    "pluginHubSupportReady",
    "stableSdkReady",
    "stableClaimAllowed",
    "stableClaimReady",
    "stableClaimSupported",
    "stablePublicationAuthorized",
    "stableReady",
    "stableReleaseReady",
    "stableReleaseContractClaimAllowed",
    "stableSdkClaimAllowed",
    "publication",
    "publicationAuthorized",
    "publicationReady",
    "publishedToPluginHub",
    "releasePublicationReady",
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
}
OPTIONAL_ALIAS_GUARDRAILS_FALSE = {
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
}
REQUIRED_ALIAS_GUARDRAILS_NON_CLAIM = (
    "Alias guardrails are false-only until identity_public_contract_gate is reviewed."
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
REQUIRED_POST_RUNTIME_CONTRACT_GAP_DIAGNOSTIC_NON_CLAIM = (
    "This post-runtime contract gap diagnostic is offline/fail-closed only: it identifies the "
    "hash-current reviewed identity public contract decision record and remaining decision keys after "
    "the approved runtime bundle is consumed, but it does not unlock public identity, lookup, public "
    "API/ABI/header, callbacks, capability bits, runtime readiness, SDK readiness, permissions/admin, "
    "command/chat surfaces, P0 progress, or v1 completion."
)
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS = {
    "approved_runtime_evidence_intake",
    "approved_runtime_evidence_not_sufficient",
    "contract_gate_inputs",
    "proposed_public_pod_abi_candidate",
    "required_before_public_header",
    "required_tests_before_public_header",
}
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
REQUIRED_REVIEWED_IDENTITY_PUBLIC_CONTRACT_SOURCE_ARTIFACTS = {
    label: {
        "path": spec["path"],
        "role": spec["role"],
        "counting_scope": public_contract_decision_record.REVIEW_ROUTE,
    }
    for label, spec in public_contract_decision_record.EXPECTED_SOURCE_ARTIFACTS.items()
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
    "active_after_resolved_input": APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT,
    "blocked_until_resolved_input": APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT,
    "current_blocker_before_resolved_input": "approved_runtime_evidence_missing",
    "next_blocker_after_resolved_input": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
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
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM = (
    "After approved runtime lifecycle evidence resolves runtime.lifecycle_evidence, the next blocker is "
    "identity_public_contract_gate_missing; this remains an offline reviewed public identity contract gate "
    "and cannot open public identity, lookup, public API/ABI/header, callbacks, capability bits, runtime "
    "readiness, SDK readiness, stable readiness, Plugin Hub readiness, publication, permissions/admin, "
    "command/chat surfaces, or v1 completion."
)
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS = [
    "approved_runtime_principal_lifecycle_evidence_bundle",
    "reviewed_identity_public_contract_decision_record",
    "identifier_redaction_evidence",
    "principal_invalidation_policy",
    "public_abi_preflight_candidate",
    "owner_token_sdk_consumer_contract",
    "source_bound_planning_manifest_verification",
    "player_identity_public_header_gate_proposal",
]
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM = (
    "Checklist items are action targets only; an accepted item never opens public identity, "
    "public header/API/ABI/SDK/runtime readiness, P0 progress, or v1 completion from this route."
)
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FIELDS = [
    "counts_as_public_readiness",
    "counts_toward_public_sdk",
    "counts_toward_p0_dependency_chain_claim",
    "accepted_for_public_header_gate_review",
    "public_header_allowed",
    "promotion_ready",
]
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY_MUST_REMAIN_FALSE = [
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
]
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ZERO_PROGRESS_FIELDS = [
    "p0_progress_contribution",
    "complete_sdk_claim_progress_contribution",
]
REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM = (
    "This post-runtime identity contract checklist is routing-only: it keeps the next reviewed identity "
    "contract and public header inputs explicit after runtime evidence, but it does not unlock public "
    "identity, lookup, public API/ABI/header, callbacks, capability bits, runtime readiness, SDK readiness, "
    "permissions/admin, command/chat surfaces, P0 progress, or v1 completion."
)
REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS = (
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "counts_toward_public_sdk",
    "counts_toward_complete_sdk_claim",
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
    "public_sdk_v1_completion_ready",
    "public_sdk_v1_completion_claim",
    "complete_sdk_ready",
    "complete_sdk_counting_allowed",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_sdk_ready",
    "plugin_hub_ready",
    "plugin_hub_publication_ready",
    "publication_ready",
    "publication_authorized",
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

READINESS_FALSE_KEYS = {
    "accepted_for_contract_review",
    "contract_review_only",
    "contract_review_ready",
    "contract_reviewed",
    "contract_record_contract_review_only",
    "identity_contract_ready",
    "identity_contract_decision_record_contract_review_only",
    "identity_contract_decision_record_hash_current",
    "identity_contract_decision_record_reviewed",
    "identity_contract_reviewed",
    "identity_header_allowed",
    "identity_header_ready",
    "identity_lookup_allowed",
    "identity_lookup_ready",
    "identity_public_contract_ready",
    "identity_public_contract_decision_record_contract_review_only",
    "identity_public_contract_decision_record_hash_current",
    "identity_public_contract_decision_record_reviewed",
    "identity_public_contract_record_contract_review_only",
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
    "access_control_ready",
    "acl_ready",
    "auth_ready",
    "authz_ready",
    "ban_kick_ready",
    "moderation_ready",
    "privilege_ready",
    "role_ready",
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
    "player_identity_promoted",
    "player_identity_ready",
    "api_readiness",
    "abi_layout_readiness",
    "public_abi_readiness",
    "public_principal_ready",
    "player_lookup_allowed",
    "public_lookup_ready",
    "player_principal_ready",
    "principal_abi_ready",
    "principal_handle_abi_ready",
    "principal_handle_ready",
    "principal_lookup_allowed",
    "principal_lookup_ready",
    "promotion",
    "promotion_ready",
    "runtime_principal_ready",
    "runtime_ready_alias",
    "public_api_allowed",
    "public_api_readiness",
    "public_api_ready",
    "public_contract_ready",
    "public_contract_readiness",
    "public_header_readiness",
    "public_readiness",
    "lookup_allowed",
    "player_lookup_ready",
    "public_lookup_allowed",
    "public_identity_allowed",
    "public_identity_ready",
    "public_sdk_ready",
    "public_sdk_readiness",
    "production_sdk_claim",
    "production_sdk_claim_allowed",
    "production_sdk_ready",
    "production_sdk_readiness",
    "runtime_ready",
    "runtime_readiness",
    "runtime_work_allowed",
    "runtime_work_authorization",
    "runtime_work_authorized",
    "runtime_capture_allowed",
    "runtime_capture_authorization",
    "runtime_capture_authorized",
    "stable_ready",
    "stable_claim_allowed",
    "stable_claim_ready",
    "stable_claim_supported",
    "stable_publication_authorized",
    "stable_release_ready",
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
    "plugin_hub_package_shape_ready",
    "plugin_hub_planning_ready",
    "plugin_hub_ready",
    "plugin_hub_publication",
    "plugin_hub_publication_ready",
    "plugin_hub_published",
    "plugin_hub_support_ready",
    "published_to_plugin_hub",
    "publication",
    "publication_ready",
    "publication_authorized",
    "release_publication_ready",
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
    "counts_toward_p0",
    "counts_toward_p0_dependency_chain",
    "counts_toward_p0_dependency_chain_claim",
    "counts_toward_phase0",
    "public_counting_allowed",
    "runtime_counting_allowed",
    "sdk_counting_allowed",
    "v1_counting_allowed",
    "sdk_consumer_ready",
    "sdk_consumer_readiness",
    "public_header_allowed",
    "public_header_ready",
    "public_contract_allowed",
    "public_contract_decision_record_contract_review_only",
    "public_contract_decision_record_hash_current",
    "public_contract_decision_record_reviewed",
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
    "hash_current_identity_contract_decision_record",
    "hash_current_identity_public_contract_decision_record",
    "hash_current_public_contract_decision_record",
    "reviewed_identity_contract_decision_record",
    "reviewed_identity_public_contract",
    "reviewed_identity_public_contract_contract_review_only",
    "reviewed_identity_public_contract_decision_record",
    "reviewed_identity_public_contract_decision_record_contract_review_only",
    "public_sdk_v1_completion_claim",
    "public_sdk_v1_completion_ready",
    "p0_progress",
    "p0_progress_ready",
    "p0_ready",
    "p0_sdk_progress",
    "p0_sdk_progress_ready",
    "sdk_p0_progress",
    "sdk_p0_progress_ready",
    "sdk_p0_ready",
    "complete_sdk_progress",
    "complete_sdk_progress_contribution",
    "complete_sdk_claim_progress_contribution",
    "p0_dependency_chain_progress_contribution",
    "p0_dependency_chain_claim_progress_contribution",
    "real_identity_ready",
    "redaction_evidence_promotes_identity",
    "v1_completion_claim",
    "v1_completion_evidence",
    "v1_completion_ready",
    "v1_ready",
    "mutation_allowed",
    "mutation_ready",
    "mutation_supported",
    "return_override_allowed",
    "return_override_ready",
    "return_override_supported",
    "object_handle_allowed",
    "object_handle_ready",
    "resource_id_allowed",
    "resource_id_ready",
    "resource_reference_allowed",
    "resource_reference_ready",
}
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
    "access_control_symbols",
    "acl_symbols",
    "auth_symbols",
    "authz_symbols",
    "ban_kick_symbols",
    "moderation_symbols",
    "object_handle_symbols",
    "privilege_symbols",
    "resource_id_symbols",
    "resource_reference_symbols",
    "role_symbols",
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
NON_CLAIM_CONTAINER_PATH_FRAGMENTS = (
    ".blocker_details",
    ".blockers",
    ".does_not_resolve",
    ".exclusions",
    ".forbidden_source_classes",
    ".forbidden_now",
    ".minimum_additional_gates",
    ".must_remain_false",
    ".must_remain_blocked",
    ".negative_consumer_rules",
    ".non_counting_artifact_classes",
    ".non_counting_artifacts",
    ".non_claim",
    ".non_claims",
    ".not_sufficient",
    ".release_guardrails",
    ".remaining_blockers",
    ".remaining_promotion_inputs",
    ".required_before_public_abi",
)
NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES = (
    ".private_pod_layout_candidate.accepted_for_contract_review",
    ".identifier_redaction_evidence.accepted_for_contract_review",
)
HEADER_ALLOWLIST = {
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_IDENTITY",
    "OBELISK_RESOURCE_KIND_DESCRIPTOR_FLAG_NO_LOOKUP",
}
PUBLIC_CAPABILITY_SYMBOL_ALLOWLIST = {
    "OBELISK_API_CAPABILITY_RESOURCE_KIND_DESCRIPTORS",
}
HEADER_SYMBOL_RE = re.compile(
    r"identity|principal|steam_?id|steamid|eos|unique_?net_?id|"
    r"player_?(?:data_?id|session|lifecycle|login|logout|connect|disconnect|join|leave|event|callback)|"
    r"register_?player|obelisk_api_capability_player|"
    r"resource_?(?:handle|id|ref|reference|token)|object_?(?:handle|id|identity|lookup|resolve|resolver)|"
    r"lookup|resolve|resolver|permissions?|permission_?(?:check|query|cache)|authorization|(?:^|_)authz?(?:_|$)|"
    r"access_?control|acl|roles?|privileges?|moderation|moderator|ban|kick|admin(?:_?(?:command|action))?|"
    r"(?:resource|player|principal|tribe)_?(?:owner|ownership|permission|permissions)|"
    r"owner_?(?:lookup|resolve|resolver|id)|tribe_?(?:id|lookup|resolve|resolver)|"
    r"[A-Za-z0-9_]*(?:OwnerLookup|OwnerResolve|Ownership|Permission|Permissions|Authorization|Authz|"
    r"AccessControl|ACL|Role|Privilege|Moderation|Moderator|Ban|Kick|Admin)[A-Za-z0-9_]*",
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
NEGATIVE_CONTEXT_RE = re.compile(
    r"\b(?:no|not|non[-_ ]|does\s+not|do\s+not|cannot|can't|forbid(?:den|s)?|"
    r"redact(?:ed|ion)?|excludes?|exclusion|after|before|without|until|missing|blocked|blocker|unavailable|"
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
    "resource_handle": re.compile(r"Resource(?:Handle|Id|ID|Ref|Reference|Token)|resource[_ -]?(?:handle|id|ref|reference|token)", re.IGNORECASE),
    "object_handle": re.compile(r"ObjectHandle|object[_ -]?handle", re.IGNORECASE),
    "lookup": re.compile(r"\blookup\b|lookup_", re.IGNORECASE),
    "permissions_admin": re.compile(
        r"\b(?:authz?|access[_ -]?control|acl|roles?|privileges?|moderation|moderator|ban|kick|"
        r"permissions?|admin)\b",
        re.IGNORECASE,
    ),
    "persistence": re.compile(r"\bpersist(?:ent|ed|ence|s|ing)?(?:\b|[_ -])", re.IGNORECASE),
    "mutation": re.compile(r"\bmutat(?:e|ion|ing|able)(?:\b|[_ -])", re.IGNORECASE),
    "return_override": re.compile(r"return[_ -]?override", re.IGNORECASE),
}
ALLOWED_CANDIDATE_CONSUMER_DEPENDENCY_TEXT_RE = re.compile(
    r"\b(?:invalidates?|fail(?:s|ed)?[-_ ]+closed|rejects?|cannot|can't|unavailable|blocked)\b"
    r"[^.;\n]{0,160}\b(?:later|downstream|future|subsequent)\b"
    r"[^.;\n]{0,120}\b(?:permissions?|permissions?[/_-]?admin|admin|commands?|command[/_-]?chat|"
    r"commands?[/_-]?replies|chat|consumers?)\b",
    re.IGNORECASE,
)
ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS = {
    "approved_runtime_evidence_present",
    "complete_accepted_lifecycle_role_triplet_present",
    "runtime_evidence_ready",
}
APPROVED_RUNTIME_REPORT_EXPLICIT_FALSE_KEYS = {
    "accepted_for_contract_review",
    "promotion_ready",
    "public_sdk_ready",
    "runtime_ready",
    "public_header_allowed",
    "public_abi_ready",
    "v1_completion_ready",
    "v1_completion_evidence",
}
APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE = re.compile(
    r"(?:"
    r"public|sdk|abi|capability|callback|header|identity|principal|permission|authz?|"
    r"access[_ -]?control|acl|roles?|privileges?|moderation|ban|kick|admin|runtime|stable|"
    r"command|chat|reply|lookup|storage|persist|mutation|return[_ -]?override|"
    r"resource[_ -]?(?:handle|id|ref|reference|token)|object[_ -]?handle|v1|"
    r"p0|phase[_ -]?0"
    r").*(?:ready|readiness|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|complete|"
    r"satisfied|passed|passing|supported|available|progress|counting)"
    r"|(?:ready|readiness|allowed|promoted|resolved|enabled|authorized|exposed|unlocked|open|opened|cleared|complete|"
    r"satisfied|passed|passing|supported|available|progress|counting).*"
    r"(?:public|sdk|abi|identity|principal|permission|authz?|access[_ -]?control|acl|roles?|"
    r"privileges?|moderation|ban|kick|admin|runtime|stable|command|chat|reply|lookup|storage|persist|mutation|"
    r"return[_ -]?override|resource[_ -]?(?:handle|id|ref|reference|token)|object[_ -]?handle|v1|p0|phase[_ -]?0)",
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
    "identity_public_contract_decision_record",
    "public_contract_decision_record",
    "reviewed_hash_current_contract_review_only",
    "reviewed_identity_public_contract",
    "route_snapshot",
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
    "counts_toward_promotion": re.compile(
        r"\bcounts?[-_ ]+toward[-_ ]+"
        r"(?:public|runtime|sdk|v1|complete[-_ ]+sdk|public[-_ ]+(?:sdk|api|abi|header|runtime)|"
        r"v1[-_ ]+completion|p0|phase[-_ ]?0|p0[-_ ]+dependency[-_ ]+chain)\b",
        re.IGNORECASE,
    ),
    "production_sdk_ready": re.compile(
        r"\b(?:production|stable|complete)[-_ ]+sdk\b[^.;\n]{0,80}\b"
        r"(?:allowed|available|claim(?:ed)?|complete|enabled|promoted|ready|readiness|supported|unlocked)",
        re.IGNORECASE,
    ),
    "readiness_noun_overclaim": re.compile(
        r"\b(?:public[-_ ]+(?:sdk|api|abi|header|contract)?[-_ ]*readiness|runtime[-_ ]+readiness)\b"
        r"[^.;\n]{0,80}\b(?:allowed|available|complete|enabled|exposed|passed|passing|promoted|"
        r"ready|satisfied|supported|unlocked)",
        re.IGNORECASE,
    ),
    "helper_derived_readiness": re.compile(
        r"\b(?:helper[-_ ]+derived[-_ ]+readiness|helper[-_ ]+readiness|derived[-_ ]+readiness)\b"
        r"[^.;\n]{0,80}\b(?:allowed|available|complete|enabled|exposed|passed|passing|promoted|"
        r"ready|satisfied|supported|unlocked)",
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
        r"(?:identity|principal).*unlock(?:s|ed)?\s+"
        r"(?:permission|authz?|access[-_ ]+control|role|privilege|moderation|ban|kick|admin|command|chat|reply|lookup|storage)",
        re.IGNORECASE,
    ),
    "lookup_allowed": re.compile(r"(?:player\s+)?lookup\s+(?:is\s+)?allowed", re.IGNORECASE),
    "broad_identity_lookup_wording": re.compile(
        r"\b(?:"
        r"[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*|"
        r"[A-Za-z0-9_]*(?:Player|Identity|Principal)[A-Za-z0-9_]*(?:Lookup|Resolve|Resolver)[A-Za-z0-9_]*|"
        r"(?:public[-_ ]+)?(?:player|identity|principal)[-_ ]+(?:lookup|resolver|resolve|resolution)"
        r"(?:[-_ ]+(?:api|surface|contract|handle|path|symbol|function|capability|support|route))?"
        r")\b",
        re.IGNORECASE,
    ),
    "mutation_allowed": re.compile(r"mutation\s+(?:is\s+)?allowed", re.IGNORECASE),
    "return_override_allowed": re.compile(r"return[_ -]?override\s+(?:is\s+)?allowed", re.IGNORECASE),
    "resource_handle_supported": re.compile(
        r"(?:resource[_ -]?(?:handle|id|ref|reference|token)|object[_ -]?handle)\s+(?:is\s+)?supported",
        re.IGNORECASE,
    ),
    "permissions_admin_ready": re.compile(
        r"\b(?:permissions?[/ _-]?admin|permission[-_ ]+query|permission[-_ ]+cache|"
        r"authz?|access[-_ ]+control|acl|roles?|privileges?|moderation|moderator|ban|kick|"
        r"admin[-_ ]+mutation)\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "commands_ready": re.compile(
        r"\b(?:command[/ _-]?chat[-_ ]+response|commands?[/ _-]?replies|command[-_ ]+response|"
        r"command[-_ ]+router|send[-_ ]+chat)\b[^.;\n]{0,80}\b"
        r"(?:available|enabled|exposed|promoted|ready|supported|unlocked)",
        re.IGNORECASE,
    ),
    "package_shape_artifact_gate_alias": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b[^.;\n]{0,100}\b(?:accepted|allowed|available|complete|"
        r"promoted|ready|resolved|satisfied|supported|unlocked|count(?:s|ed)?)\b",
        re.IGNORECASE,
    ),
    "checklist_policy_row_resolves_gate": re.compile(
        r"\b(?:post[-_ ]+runtime[-_ ]+identity[-_ ]+contract[-_ ]+checklist|"
        r"identity[-_ ]+contract[-_ ]+checklist|checklist[-_ ]+(?:policy|row|item|action[-_ ]+target))\b"
        r"[^.;\n]{0,100}\b(?:accepted|complete|completed|count(?:s|ed)?|promoted|ready|resolved|"
        r"satisfied|unlock(?:s|ed)?)\b|"
        r"\b(?:accepted|complete|completed|promoted|ready|resolved|satisfied|unlock(?:s|ed)?)\b"
        r"[^.;\n]{0,100}\b(?:post[-_ ]+runtime[-_ ]+identity[-_ ]+contract[-_ ]+checklist|"
        r"identity[-_ ]+contract[-_ ]+checklist|checklist[-_ ]+(?:policy|row|item|action[-_ ]+target))\b",
        re.IGNORECASE,
    ),
    "scoped_8of8_release_statement_row": re.compile(
        r"\b(?:scoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?release[-_ ]+statement|"
        r"release[-_ ]+statement)\b[^\.;\n]{0,100}\b(?:8\s*/\s*8|8[-_ ]?of[-_ ]?8|"
        r"eight[-_ ]+of[-_ ]+eight)\b|"
        r"\b(?:8\s*/\s*8|8[-_ ]?of[-_ ]?8|eight[-_ ]+of[-_ ]+eight)\b"
        r"[^\.;\n]{0,100}\b(?:scoped[-_ ]+(?:non[-_ ]+complete[-_ ]+)?release[-_ ]+statement|"
        r"release[-_ ]+statement)\b",
        re.IGNORECASE,
    ),
    "terminal_certificate_gate_alias": re.compile(
        r"\bterminal[-_ ]+(?:promotion[-_ ]+|completion[-_ ]+|route[-_ ]+|surface[-_ ]+|public[-_ ]+)?"
        r"certificate\b[^\.;\n]{0,100}\b(?:accepted|complete|completed|count(?:s|ed)?|promoted|"
        r"ready|resolved|satisfied|unlock(?:s|ed)?)\b|"
        r"\b(?:accepted|complete|completed|promoted|ready|resolved|satisfied|unlock(?:s|ed)?)\b"
        r"[^\.;\n]{0,100}\bterminal[-_ ]+(?:promotion[-_ ]+|completion[-_ ]+|route[-_ ]+|"
        r"surface[-_ ]+|public[-_ ]+)?certificate\b",
        re.IGNORECASE,
    ),
    "generated_runtime_bundle_report_gate_alias": re.compile(
        r"\b(?:evidence[-_ ]+bundle[-_ ]+report|runtime[-_ ]+(?:evidence[-_ ]+)?bundle[-_ ]+"
        r"(?:report|check|preflight|build[-_ ]+report)|approved[-_ ]+runtime[-_ ]+bundle[-_ ]+"
        r"(?:report|check|preflight|status|request)|bundle[-_ ]+(?:preflight|report|check))\b"
        r"[^.;\n]{0,100}\b(?:accepted|complete|completed|count(?:s|ed)?|promoted|ready|resolved|"
        r"satisfied|unlock(?:s|ed)?)\b|"
        r"\b(?:accepted|complete|completed|promoted|ready|resolved|satisfied|unlock(?:s|ed)?)\b"
        r"[^.;\n]{0,100}\b(?:evidence[-_ ]+bundle[-_ ]+report|runtime[-_ ]+(?:evidence[-_ ]+)?"
        r"bundle[-_ ]+(?:report|check|preflight|build[-_ ]+report)|approved[-_ ]+runtime[-_ ]+"
        r"bundle[-_ ]+(?:report|check|preflight|status|request)|bundle[-_ ]+(?:preflight|report|check))\b",
        re.IGNORECASE,
    ),
}
NON_PROMOTIONAL_ARTIFACT_CONTEXT_KEY_RE = re.compile(
    r"(?:"
    r"(?:post_runtime_identity_contract_)?checklist(?:_(?:policy|row|item|policy_row|policy_item))?|"
    r"(?:identity_contract_)?checklist(?:_(?:policy|row|item|policy_row|policy_item))?|"
    r"(?:scoped_)?(?:8_8|8of8|8_of_8|8_of_eight|eight_of_eight)(?:_release_statement)?(?:_row)?|"
    r"(?:scoped_)?release_statement(?:_(?:8_8|8of8|8_of_8|8_of_eight|eight_of_eight))?(?:_row)?|"
    r"terminal(?:_promotion|_completion|_route|_surface|_public)?_certificate|"
    r"(?:generated_)?(?:runtime_)?(?:evidence_)?bundle_(?:report|preflight|check)|"
    r"approved_runtime_bundle_(?:report|preflight|check|status|request)|"
    r"package_shape|package_shape_artifact|installed_sdk_package_shape"
    r")(?:_(?:accepted|allowed|complete|counting|counts|credit|progress|ready|resolved|state|status))?",
    re.IGNORECASE,
)
APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_SUMMARY_PATH_FRAGMENTS = (
    ".diagnostic_candidate_lifecycle_property_fname_mismatches",
    ".diagnostic_lifecycle_property_fname_mismatch_summary",
    ".diagnostic_lifecycle_property_fname_mismatch_target_summary",
)
APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_SUMMARY_KEYS = {
    "approved_runtime_evidence",
    "count",
    "evidence_claim",
    "evidence_classification",
    "expected_name_index",
    "first_sequence",
    "fname_indices",
    "latest_occurrence",
    "latest_sequence",
    "line_number",
    "observed_count",
    "observed_name_indices",
    "observed_name_indices_complete",
    "observed_present_count",
    "pattern_count",
    "patterns",
    "read_status_counts",
    "readiness_gate",
    "reason_counts",
    "runtime_evidence_ready",
    "source_index",
    "summary",
    "target",
    "target_count",
    "target_counts",
    "targets",
    "timestamp_prefix",
    "truncated",
}
APPROVED_RUNTIME_PLAYER_OR_RAW_UE_LEAKAGE_KEY_RE = re.compile(
    r"^(?:"
    r"steam(?:id|_id)?|eos(?:_id)?|unique_net_id|player_(?:id|name|data(?:_id)?)|"
    r"ip(?:v4|v6)?(?:_address)?|tribe(?:_id)?|platform_ids?|private_identifier|"
    r"chat_(?:text|message|payload)|command_(?:text|message|payload)|"
    r"raw_(?:ue_)?(?:params?|payload|pointer|trace|buffers?)|ue_pointer|uobject(?:_address|_pointer)?|"
    r"gobjects?|fnames?|fname_(?:index|id)|gobject_(?:index|id)|"
    r"resourcehandle|resource_handle|resource_id|object_(?:address|name|handle)|"
    r"(?:identity|identifier|player|steam|eos)_hash"
    r")$",
    re.IGNORECASE,
)
APPROVED_RUNTIME_PLAYER_OR_RAW_UE_LEAKAGE_VALUE_RE = re.compile(
    r"\b(?:"
    r"steam(?:id|[_ -]?id)|eos[_ -]?id|unique[_ -]?net[_ -]?id|"
    r"player[_ -]?data[_ -]?id|player[_ -]?name|ip(?:v4|v6)?[_ -]?(?:address)?|"
    r"tribe[_ -]?id|ue[_ -]?pointer|raw[_ -]?ue(?:[_ -]?(?:params?|payload|pointer|trace|buffers?))?|"
    r"raw[_ -]?params?|raw[_ -]?payload|raw[_ -]?pointer|"
    r"uobject|uclass|ufunction|gobjects|fname[/_-]?gobjects|"
    r"fname[_ -]?(?:index|id)|resourcehandle"
    r")\b",
    re.IGNORECASE,
)
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
    "publication_ready": re.compile(
        r"\b(?:publication|release[-_ ]+publication|public[-_ ]+release|"
        r"stable[-_ ]+(?:release|publication))\b"
        r"\s+(?:is\s+)?(?:allowed|authorized|available|enabled|published|ready|released|supported)",
        re.IGNORECASE,
    ),
    "package_shape_readiness": re.compile(
        r"\b(?:cmake[-_ ]+package|cmake[-_ ]+config|find[-_ ]+package|"
        r"obeliskconfig\.cmake|obelisktargets\.cmake|obelisk::obelisk_sdk|"
        r"installed[-_ ]+sdk[-_ ]+package[-_ ]+shape|sdk[-_ ]+package[-_ ]+shape|"
        r"package[-_ ]+shape)\b"
        r"(?:(?!\bor\b)[^\.;]){0,80}\b(?:accepted|allowed|available|complete|enabled|open(?:ed|s)?|"
        r"promoted|ready|resolved|satisfied|supported|unlocked|counts?|claim(?:ed)?)\b|"
        r"\binstalled[-_ ]+sdk\s+(?:is\s+|are\s+|now\s+)?"
        r"(?:accepted|allowed|available|complete|enabled|promoted|ready|resolved|satisfied|supported|unlocked)\b|"
        r"\b(?:allowed|available|complete|enabled|open(?:ed|s)?|promoted|ready|supported|"
        r"unlocked|resolved|satisfied|counts?|claim(?:ed)?)\s+"
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
    "public_capability_symbol": re.compile(
        r"\bOBELISK_API_CAPABILITY_[A-Z0-9_]*"
        r"(?:PLAYER|IDENTITY|PRINCIPAL|STEAM|EOS|UNIQUE_NET|AUTH|AUTHZ|ACCESS_CONTROL|ACL|"
        r"ROLE|PRIVILEGE|MODERATION|BAN|KICK|RESOURCE|OBJECT)[A-Z0-9_]*\b"
    ),
    "public_player_header_symbol": re.compile(
        r"\b(?:ObeliskPlayer[A-Za-z0-9_]*|RegisterPlayer[A-Za-z0-9_]*)\b"
    ),
    "source_artifact_ready_alias": re.compile(
        r"\b(?:public[-_ ]+sdk|public[-_ ]+api|public[-_ ]+header|public[-_ ]+abi|callback[-_ ]+abi|"
        r"capability[-_ ]+bits?|runtime|promotion|stable[-_ ]+claim|v1[-_ ]+completion)[-_ ]+"
        r"(?:ready|readiness|allowed|available|enabled|promoted|complete|exposed|satisfied|passed|passing)\b",
        re.IGNORECASE,
    ),
}
CONTRACT_REVIEW_TEXT_OVERCLAIM_PATTERNS = {
    **PUBLIC_TEXT_OVERCLAIM_PATTERNS,
    "identity_or_principal_promoted": re.compile(
        r"\b(?:public[-_ ]+)?(?:player[-_ ]+)?(?:identity|principal)\s+(?:is\s+)?"
        r"(?:promoted|promotion[-_ ]+ready|promotion[-_ ]+complete)\b|"
        r"\b(?:promotes?|promoted)\s+(?:public[-_ ]+)?(?:player[-_ ]+)?(?:identity|principal)\b",
        re.IGNORECASE,
    ),
    "complete_sdk_progress": re.compile(
        r"\b(?:complete|full|production)\s+sdk\s+"
        r"(?:progress|ready|complete|available|enabled|promoted|supported)\b",
        re.IGNORECASE,
    ),
    "sdk_p0_progress": re.compile(
        r"\b(?:sdk[/ _-]*p0|p0[/ _-]*(?:sdk)?|phase[-_ ]*0|complete[/ _-]*sdk)"
        r"[/ _-]*(?:progress|completion|readiness|credit|counting)?\b[^.;\n]{0,80}\b"
        r"(?:progress|ready|complete|available|enabled|promoted|supported|counts?|credited|satisfied)",
        re.IGNORECASE,
    ),
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
    parser.add_argument(
        "--identity-public-contract-decision-record",
        type=Path,
        default=DEFAULT_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD,
        help=(
            "Repo-local reviewed identity public-contract decision record consumed as "
            "post-runtime contract-review input only."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    return parser.parse_args()


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


def normalize_contract_key(key: object) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", str(key))
    return re.sub(r"[^a-z0-9]+", "_", separated.casefold()).strip("_")


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
            "completed",
            "counted",
            "counting",
            "enabled",
            "exposed",
            "granted",
            "live",
            "operational",
            "passed",
            "passing",
            "promoted",
            "public",
            "published",
            "ready",
            "released",
            "resolved",
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
        public_surface_list_claim = (
            claim_key in EMPTY_PUBLIC_LIST_KEYS
            and any(is_nonempty_public_surface_claim_value(item) for item in declared_claim_values)
        )
        if (
            claim_key in READINESS_FALSE_KEYS
            or claim_key in EMPTY_PUBLIC_LIST_KEYS
            or APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(claim_key) is not None
        ) and (positive_claim or public_surface_list_claim):
            overclaims.append({"path": path, "term": "split_readiness_alias", "value": value})
    return overclaims


def is_non_claim_container_path(path: str) -> bool:
    return any(fragment in path for fragment in NON_CLAIM_CONTAINER_PATH_FRAGMENTS)


def is_allowed_required_sequence_gate_text(path: str, value: str) -> bool:
    return any(
        path.endswith(f".v1_sequence_gate[{index}]") and value == expected
        for index, expected in enumerate(REQUIRED_SEQUENCE_GATE)
    )


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
        parent_path = path.rsplit(".", 1)[0] if "." in path else "$"
        readiness_key = first_claim_key(
            nested_claim_key_candidates(parent_path, key),
            READINESS_FALSE_KEYS,
        )
        if readiness_key is not None and item is not False:
            add(blockers, "readiness_flag_not_false", path, input=label, value=item)


def alias_guardrails_false() -> dict[str, bool]:
    return {key: False for key in sorted(REQUIRED_ALIAS_GUARDRAILS_FALSE)}


def validate_alias_guardrails(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    aliases = decisions.get("alias_guardrails")
    if not isinstance(aliases, dict):
        add(blockers, "decisions_alias_guardrails_missing", "$.alias_guardrails")
        return
    for key in sorted(REQUIRED_ALIAS_GUARDRAILS_FALSE):
        if aliases.get(key) is not False:
            add(
                blockers,
                "decisions_alias_guardrail_not_false",
                f"$.alias_guardrails.{key}",
                value=aliases.get(key),
            )
    for key in sorted(OPTIONAL_ALIAS_GUARDRAILS_FALSE):
        if key in aliases and aliases.get(key) is not False:
            add(
                blockers,
                "decisions_alias_guardrail_not_false",
                f"$.alias_guardrails.{key}",
                value=aliases.get(key),
            )
    if aliases.get("non_claim") != REQUIRED_ALIAS_GUARDRAILS_NON_CLAIM:
        add(
            blockers,
            "decisions_alias_guardrails_non_claim_mismatch",
            "$.alias_guardrails.non_claim",
            value=aliases.get("non_claim"),
        )


def validate_empty_public_lists(value: Any, blockers: list[dict[str, Any]], label: str) -> None:
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        normalized_key = normalize_contract_key(key)
        if normalized_key in EMPTY_PUBLIC_LIST_KEYS and item != []:
            add(blockers, f"{normalized_key}_not_empty", f"$.{key}", input=label, value=item)


def public_text_overclaims(value: Any, path: str = "$") -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    if isinstance(value, dict):
        claims.extend(split_claim_overclaims(value, path))
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            if readiness_key is not None and is_positive_claim_value(item):
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
                if has_negative_context(value, match.start()):
                    continue
                if (
                    term == "public_capability_symbol"
                    and match.group(0) in PUBLIC_CAPABILITY_SYMBOL_ALLOWLIST
                ):
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


def non_promotional_contract_review_report_overclaims(
    value: Any,
    *,
    allowed_true_paths: set[str],
    path: str = "$",
) -> list[dict[str, Any]]:
    overclaims: list[dict[str, Any]] = []
    if isinstance(value, dict):
        overclaims.extend(split_claim_overclaims(value, path))
        for key, item in value.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            if public_list_key is not None and item != []:
                overclaims.append({"path": item_path, "term": "public_surface_list", "value": item})
            if readiness_key is not None and item_path not in allowed_true_paths and item is not False:
                overclaims.append({"path": item_path, "term": "readiness_flag", "value": item})
            elif (
                item_path not in allowed_true_paths
                and item not in (False, None, [], {})
                and APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(normalized_key)
            ):
                overclaims.append({"path": item_path, "term": "readiness_or_authorization_key", "value": item})
            overclaims.extend(
                non_promotional_contract_review_report_overclaims(
                    item,
                    allowed_true_paths=allowed_true_paths,
                    path=item_path,
                )
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            overclaims.extend(
                non_promotional_contract_review_report_overclaims(
                    item,
                    allowed_true_paths=allowed_true_paths,
                    path=f"{path}[{index}]",
                )
            )
    elif isinstance(value, str):
        if is_non_claim_container_path(path):
            return overclaims
        for term, pattern in CONTRACT_REVIEW_TEXT_OVERCLAIM_PATTERNS.items():
            for match in pattern.finditer(value):
                if has_negative_context(value, match.start()):
                    continue
                overclaims.append({"path": path, "term": term, "value": value})
                break
    return overclaims


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
            contract_review_allowed = (
                normalized_key == "accepted_for_contract_review"
                and path != root_path
                and item_path.endswith(NESTED_CONTRACT_REVIEW_ACCEPTANCE_ALLOWED_SUFFIXES)
            )
            if readiness_key is not None and not contract_review_allowed:
                if item is not False:
                    add(blockers, "nested_readiness_flag_not_false", item_path, input=input_label, value=item)
                sanitized[key] = False
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


def validate_permissions_admin_query_only_planning(
    value: Any,
    blockers: list[dict[str, Any]],
    label: str,
    *,
    reason_prefix: str,
) -> None:
    if not isinstance(value, dict):
        add(blockers, f"{reason_prefix}_permissions_admin_query_only_planning_missing", label)
        return

    if value.get("status") != REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_STATUS:
        add(
            blockers,
            f"{reason_prefix}_permissions_admin_query_only_status_mismatch",
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
                f"{reason_prefix}_permissions_admin_query_only_flag_not_false",
                f"{label}.{key}",
                value=value.get(key),
            )
    require_string_list_contains(
        value,
        "required_policy",
        REQUIRED_PERMISSIONS_ADMIN_QUERY_ONLY_POLICY,
        blockers,
        f"{reason_prefix}_permissions_admin_query_only_policy_missing",
        f"{label}.required_policy",
    )
    require_string_list_contains(
        value,
        "forbidden_until_separate_promotion",
        REQUIRED_PERMISSIONS_ADMIN_FORBIDDEN_UNTIL_PROMOTION,
        blockers,
        f"{reason_prefix}_permissions_admin_query_only_forbidden_terms_missing",
        f"{label}.forbidden_until_separate_promotion",
    )
    require_string_list_contains(
        value,
        "non_counting_artifacts",
        REQUIRED_PERMISSIONS_ADMIN_NON_COUNTING_ARTIFACTS,
        blockers,
        f"{reason_prefix}_permissions_admin_query_only_non_counting_artifacts_missing",
        f"{label}.non_counting_artifacts",
    )

    certificate = value.get("required_identity_promotion_certificate")
    certificate_label = f"{label}.required_identity_promotion_certificate"
    if not isinstance(certificate, dict):
        add(
            blockers,
            f"{reason_prefix}_permissions_admin_identity_promotion_certificate_requirement_missing",
            certificate_label,
        )
        return
    for key, expected in REQUIRED_PLAYER_IDENTITY_PROMOTION_CERTIFICATE_REQUIREMENTS.items():
        if certificate.get(key) != expected:
            add(
                blockers,
                f"{reason_prefix}_permissions_admin_identity_promotion_certificate_requirement_mismatch",
                f"{certificate_label}.{key}",
                expected=expected,
                value=certificate.get(key),
            )
    if certificate.get("missing_mismatched_or_stale_certificate_counts") is not False:
        add(
            blockers,
            f"{reason_prefix}_permissions_admin_identity_promotion_certificate_non_counting_flag_not_false",
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


def find_surface_by_id(
    surfaces: dict[str, Any],
    surface_id: str,
    blockers: list[dict[str, Any]],
    reason_prefix: str,
) -> dict[str, Any]:
    matches = [
        item
        for item in surfaces.get("surfaces", [])
        if isinstance(item, dict) and item.get("id") == surface_id
    ]
    if len(matches) != 1:
        add(blockers, f"{reason_prefix}_surface_missing_or_duplicate", "$.surfaces", id=surface_id, count=len(matches))
        return {}
    return matches[0]


def validate_permissions_admin_surface(surfaces: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    surface = find_surface_by_id(surfaces, PERMISSIONS_ADMIN_SURFACE, blockers, "permissions_admin")
    if not surface:
        return
    if surface.get("status") != "planning":
        add(
            blockers,
            "permissions_admin_surface_status_not_planning",
            "$.surfaces[obelisk.permissions_admin.v1].status",
            value=surface.get("status"),
        )
    if surface.get("public_contract") != []:
        add(
            blockers,
            "permissions_admin_surface_public_contract_not_empty",
            "$.surfaces[obelisk.permissions_admin.v1].public_contract",
            value=surface.get("public_contract"),
        )
    depends_on = surface.get("depends_on")
    if not isinstance(depends_on, list) or SURFACE not in depends_on:
        add(
            blockers,
            "permissions_admin_surface_identity_dependency_missing",
            "$.surfaces[obelisk.permissions_admin.v1].depends_on",
            value=depends_on,
        )
    contract = surface.get("v1_decision_contract")
    if not isinstance(contract, dict):
        add(
            blockers,
            "permissions_admin_surface_v1_decision_contract_missing",
            "$.surfaces[obelisk.permissions_admin.v1].v1_decision_contract",
        )
        return
    validate_permissions_admin_query_only_planning(
        contract.get("permissions_admin_query_only_planning"),
        blockers,
        "$.surfaces[obelisk.permissions_admin.v1].v1_decision_contract.permissions_admin_query_only_planning",
        reason_prefix="surfaces",
    )


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
        separation_label = "$.required_before_public_header[separation.no_commands_permissions_persistence]"
        sequence_gate = string_list(separation.get("v1_sequence_gate"))
        if sequence_gate != REQUIRED_SEQUENCE_GATE:
            add(
                blockers,
                "decisions_separation_sequence_gate_mismatch",
                f"{separation_label}.v1_sequence_gate",
                value=separation.get("v1_sequence_gate"),
            )
        require_string_list_contains(
            separation,
            "forbidden_in_identity_contract",
            REQUIRED_SEPARATION_FORBIDDEN,
            blockers,
            "decisions_separation_forbidden_downstream_surfaces_missing",
            f"{separation_label}.forbidden_in_identity_contract",
        )
        validate_permissions_admin_query_only_planning(
            separation.get("permissions_admin_query_only_planning"),
            blockers,
            f"{separation_label}.permissions_admin_query_only_planning",
            reason_prefix="decisions",
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
    remaining = unresolved_required_before_public_header_ids(decisions)
    seen = set(remaining)
    for key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_REVIEW_DECISION_KEYS:
        if key not in seen:
            remaining.append(key)
            seen.add(key)
    return remaining


def validate_post_approved_runtime_evidence_gate(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    gate = decisions.get("post_approved_runtime_evidence_gate")
    if not isinstance(gate, dict):
        add(blockers, "decisions_post_approved_runtime_evidence_gate_missing", "$.post_approved_runtime_evidence_gate")
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
        *POST_APPROVED_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS,
    }
    unexpected_gate_keys = sorted(set(gate) - expected_gate_keys)
    if unexpected_gate_keys:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_unexpected_route_extras",
            "$.post_approved_runtime_evidence_gate",
            unexpected=unexpected_gate_keys,
        )

    if gate.get("id") != "identity_public_contract_gate.reviewed_identity_public_contract":
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_id_mismatch",
            "$.post_approved_runtime_evidence_gate.id",
            value=gate.get("id"),
        )
    if gate.get("status") != "blocked/review-required":
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_status_mismatch",
            "$.post_approved_runtime_evidence_gate.status",
            value=gate.get("status"),
        )
    if gate.get("active_after_resolved_input") != APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_active_input_mismatch",
            "$.post_approved_runtime_evidence_gate.active_after_resolved_input",
            value=gate.get("active_after_resolved_input"),
        )
    for key in ("reported_current_blocker", "next_blocker"):
        if gate.get(key) != APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER:
            add(
                blockers,
                f"decisions_post_approved_runtime_evidence_gate_{key}_mismatch",
                f"$.post_approved_runtime_evidence_gate.{key}",
                value=gate.get(key),
            )
    if string_list(gate.get("required_unresolved_decision_keys")) != (
        REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS
    ):
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_required_decision_keys_mismatch",
            "$.post_approved_runtime_evidence_gate.required_unresolved_decision_keys",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_DECISION_KEYS,
            observed=gate.get("required_unresolved_decision_keys"),
        )
    audit_inputs = string_list(gate.get("auditable_inputs"))
    if audit_inputs is None or set(audit_inputs) != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_auditable_inputs_mismatch",
            "$.post_approved_runtime_evidence_gate.auditable_inputs",
            expected=sorted(REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_AUDIT_INPUTS),
            observed=gate.get("auditable_inputs"),
        )
    if gate.get("next_required_artifact") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_next_required_artifact_mismatch",
            "$.post_approved_runtime_evidence_gate.next_required_artifact",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
            observed=gate.get("next_required_artifact"),
        )
    if gate.get("offline_preparation") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_offline_preparation_mismatch",
            "$.post_approved_runtime_evidence_gate.offline_preparation",
            expected=REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_OFFLINE_PREPARATION,
            observed=gate.get("offline_preparation"),
        )
    for key in REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_FALSE_FLAGS:
        if gate.get(key) is not False:
            add(
                blockers,
                "readiness_flag_not_false",
                f"$.post_approved_runtime_evidence_gate.{key}",
                input="post_approved_runtime_evidence_gate",
                value=gate.get(key),
            )
    for key in POST_APPROVED_RUNTIME_EVIDENCE_FALSE_ONLY_ALIAS_FLAGS:
        if key in gate and gate.get(key) is not False:
            add(
                blockers,
                "readiness_flag_not_false",
                f"$.post_approved_runtime_evidence_gate.{key}",
                input="post_approved_runtime_evidence_gate",
                value=gate.get(key),
            )
    if gate.get("non_claim") != REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM:
        add(
            blockers,
            "decisions_post_approved_runtime_evidence_gate_non_claim_mismatch",
            "$.post_approved_runtime_evidence_gate.non_claim",
            value=gate.get("non_claim"),
        )


def validate_post_runtime_identity_contract_checklist_policy(
    decisions: dict[str, Any],
    blockers: list[dict[str, Any]],
) -> None:
    policy = decisions.get("post_runtime_identity_contract_checklist_policy")
    label = "$.post_runtime_identity_contract_checklist_policy"
    if not isinstance(policy, dict):
        add(blockers, "decisions_post_runtime_identity_contract_checklist_missing", label)
        return

    if policy.get("id") != "post_runtime_identity_contract_checklist":
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_id_mismatch",
            f"{label}.id",
            value=policy.get("id"),
        )
    if policy.get("status") != "blocked/fail-closed-action-list":
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_status_mismatch",
            f"{label}.status",
            value=policy.get("status"),
        )
    if policy.get("active_after_resolved_input") != APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT:
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_active_input_mismatch",
            f"{label}.active_after_resolved_input",
            value=policy.get("active_after_resolved_input"),
        )
    if policy.get("current_blocker_after_resolved_input") != APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER:
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_current_blocker_mismatch",
            f"{label}.current_blocker_after_resolved_input",
            value=policy.get("current_blocker_after_resolved_input"),
        )
    if string_list(policy.get("required_item_ids")) != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS:
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_required_item_ids_mismatch",
            f"{label}.required_item_ids",
            expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS,
            observed=policy.get("required_item_ids"),
        )

    items = policy.get("items")
    if not isinstance(items, list):
        add(blockers, "decisions_post_runtime_identity_contract_checklist_items_not_list", f"{label}.items")
    else:
        by_id = {
            item.get("id"): item
            for item in items
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if set(by_id) != set(REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS):
            add(
                blockers,
                "decisions_post_runtime_identity_contract_checklist_items_mismatch",
                f"{label}.items",
                expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS,
                observed=sorted(by_id),
            )
        for item_id in REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_IDS:
            item = by_id.get(item_id)
            item_label = f"{label}.items[{item_id}]"
            if not isinstance(item, dict):
                continue
            if "status" in item:
                add(
                    blockers,
                    "decisions_post_runtime_identity_contract_checklist_item_status_present",
                    f"{item_label}.status",
                    id=item_id,
                    value=item.get("status"),
                )
            for key in REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_FALSE_FIELDS:
                if item.get(key) is not False:
                    add(
                        blockers,
                        "decisions_post_runtime_identity_contract_checklist_item_flag_not_false",
                        f"{item_label}.{key}",
                        id=item_id,
                        value=item.get(key),
                    )
            for key in REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ZERO_PROGRESS_FIELDS:
                if key in item and item.get(key) != 0:
                    add(
                        blockers,
                        "decisions_post_runtime_identity_contract_checklist_item_progress_not_zero",
                        f"{item_label}.{key}",
                        id=item_id,
                        value=item.get(key),
                    )
            if item.get("non_claim") != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ITEM_NON_CLAIM:
                add(
                    blockers,
                    "decisions_post_runtime_identity_contract_checklist_item_non_claim_mismatch",
                    f"{item_label}.non_claim",
                    id=item_id,
                    value=item.get("non_claim"),
                )

    if (
        string_list(policy.get("must_remain_false"))
        != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY_MUST_REMAIN_FALSE
    ):
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_must_remain_false_mismatch",
            f"{label}.must_remain_false",
            expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_POLICY_MUST_REMAIN_FALSE,
            observed=policy.get("must_remain_false"),
        )
    if (
        string_list(policy.get("per_item_zero_progress_fields"))
        != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ZERO_PROGRESS_FIELDS
    ):
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_progress_fields_mismatch",
            f"{label}.per_item_zero_progress_fields",
            expected=REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_ZERO_PROGRESS_FIELDS,
            observed=policy.get("per_item_zero_progress_fields"),
        )
    if policy.get("non_claim") != REQUIRED_POST_RUNTIME_IDENTITY_CONTRACT_CHECKLIST_NON_CLAIM:
        add(
            blockers,
            "decisions_post_runtime_identity_contract_checklist_non_claim_mismatch",
            f"{label}.non_claim",
            value=policy.get("non_claim"),
        )


def validate_decisions(decisions: dict[str, Any], blockers: list[dict[str, Any]]) -> None:
    validate_public_text_overclaims(decisions, blockers, label="decisions")
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
    validate_alias_guardrails(decisions, blockers)
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
        validate_approved_runtime_source_provenance_policy(
            approved_runtime_intake.get("source_provenance_policy"),
            blockers,
            "$.approved_runtime_evidence_intake.source_provenance_policy",
            "decisions_approved_runtime_evidence_intake_source_provenance_policy_mismatch",
        )
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
    validate_post_approved_runtime_evidence_gate(decisions, blockers)
    validate_post_runtime_identity_contract_checklist_policy(decisions, blockers)
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
    validate_public_text_overclaims(surfaces, blockers, label="surfaces")
    if surfaces.get("schema") != SURFACES_SCHEMA:
        add(blockers, "surfaces_schema_mismatch", "$.schema", value=surfaces.get("schema"))
    validate_permissions_admin_surface(surfaces, blockers)
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
            r"\b(?:after|before|forbidden|unavailable|blocked|redacted|cannot|can't|false|missing|"
            r"not|exclusion|unresolved|until)\b|"
            r"\bdoes\s+not\b|\bdo\s+not\b|\bmust\s+not\b",
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
                if (
                    term == "permissions_admin"
                    and path.startswith("$.candidate_event_kind_semantics")
                    and ALLOWED_CANDIDATE_CONSUMER_DEPENDENCY_TEXT_RE.search(item)
                ):
                    continue
                exposures.append({"path": path, "term": term, "value": item})
                break
    return exposures


def is_approved_runtime_diagnostic_mismatch_summary_path(path: str) -> bool:
    return any(fragment in path for fragment in APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_SUMMARY_PATH_FRAGMENTS)


def is_approved_runtime_safe_diagnostic_mismatch_summary_key(path: str, key: object) -> bool:
    return (
        is_approved_runtime_diagnostic_mismatch_summary_path(path)
        and normalize_contract_key(key) in APPROVED_RUNTIME_DIAGNOSTIC_MISMATCH_SUMMARY_KEYS
    )


def approved_runtime_report_leakages(value: Any, path: str = "$") -> list[dict[str, Any]]:
    leakages: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            item_path = f"{path}.{key}"
            key_name = normalize_contract_key(key)
            safe_diagnostic_key = is_approved_runtime_safe_diagnostic_mismatch_summary_key(item_path, key)
            if (
                not safe_diagnostic_key
                and item not in (False, None, [], {})
                and APPROVED_RUNTIME_PLAYER_OR_RAW_UE_LEAKAGE_KEY_RE.fullmatch(key_name)
            ):
                leakages.append({"path": item_path, "term": "player_or_raw_ue_key", "value": item})
            leakages.extend(approved_runtime_report_leakages(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            leakages.extend(approved_runtime_report_leakages(item, f"{path}[{index}]"))
    elif isinstance(value, str):
        if is_non_claim_container_path(path):
            return leakages
        for match in APPROVED_RUNTIME_PLAYER_OR_RAW_UE_LEAKAGE_VALUE_RE.finditer(value):
            if has_negative_context(value, match.start()):
                continue
            leakages.append({"path": path, "term": "player_or_raw_ue_value", "value": value})
            break
    return leakages


def approved_runtime_report_overclaims(report: Any, path: str = "$") -> list[dict[str, Any]]:
    overclaims: list[dict[str, Any]] = []
    if isinstance(report, dict):
        overclaims.extend(split_claim_overclaims(report, path))
        for key, item in report.items():
            item_path = f"{path}.{key}"
            normalized_key = normalize_contract_key(key)
            claim_candidates = nested_claim_key_candidates(path, key)
            readiness_key = first_claim_key(claim_candidates, READINESS_FALSE_KEYS)
            public_list_key = first_claim_key(claim_candidates, EMPTY_PUBLIC_LIST_KEYS)
            safe_diagnostic_key = is_approved_runtime_safe_diagnostic_mismatch_summary_key(item_path, key)
            if public_list_key is not None and item != [] and not safe_diagnostic_key:
                overclaims.append({"path": item_path, "term": "public_surface_list", "value": item})
            if (
                readiness_key is not None
                and not (path == "$" and readiness_key in APPROVED_RUNTIME_REPORT_EXPLICIT_FALSE_KEYS)
                and item is not False
                and not safe_diagnostic_key
            ):
                overclaims.append({"path": item_path, "term": "readiness_alias", "value": item})
            if (
                normalized_key not in ALLOWED_APPROVED_RUNTIME_REPORT_TRUE_KEYS
                and readiness_key is None
                and item not in (False, None, [], {})
                and APPROVED_RUNTIME_REPORT_OVERCLAIM_KEY_RE.search(normalized_key)
                and not safe_diagnostic_key
            ):
                overclaims.append({"path": item_path, "term": "readiness_or_authorization_key", "value": item})
            if (
                readiness_key is None
                and item not in (False, None, [], {})
                and NON_PROMOTIONAL_ARTIFACT_CONTEXT_KEY_RE.fullmatch(normalized_key)
                and is_positive_claim_value(item)
                and not safe_diagnostic_key
            ):
                overclaims.append({"path": item_path, "term": "non_promotional_artifact_status_alias", "value": item})
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
    validate_public_text_overclaims(candidate, blockers, label="private_candidate_contract")
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
    accepted = not redaction_blockers
    if redaction_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "--identifier-redaction-evidence",
            path=str(path),
            evidence_blockers=report["blockers"],
        )
        accepted = False
    overclaims = non_promotional_contract_review_report_overclaims(
        payload,
        allowed_true_paths=set(),
    ) + non_promotional_contract_review_report_overclaims(
        report,
        allowed_true_paths={"$.accepted_for_contract_review"},
    )
    if overclaims:
        add(
            blockers,
            "identifier_redaction_evidence_public_contract_overclaim",
            "--identifier-redaction-evidence",
            overclaims=overclaims,
        )
        accepted = False
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "public_header_allowed"):
        if report.get(key) is not False:
            add(
                blockers,
                "identifier_redaction_evidence_readiness_flag_not_false",
                f"--identifier-redaction-evidence.{key}",
                value=report.get(key),
            )
            accepted = False
    if report.get("accepted_for_contract_review") and report.get("resolved_inputs") != [PRIMARY_OFFLINE_GAP]:
        add(
            blockers,
            "identifier_redaction_evidence_resolved_inputs_mismatch",
            "--identifier-redaction-evidence.resolved_inputs",
            value=report.get("resolved_inputs"),
        )
        accepted = False
    if report.get("next_blocker") in {
        "identity_public_contract_gate",
        APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
    }:
        add(
            blockers,
            "identifier_redaction_evidence_route_unlock_claimed",
            "--identifier-redaction-evidence.next_blocker",
            value=report.get("next_blocker"),
        )
        accepted = False
    if not accepted and not redaction_blockers:
        add(
            blockers,
            "identifier_redaction_evidence_not_accepted",
            "--identifier-redaction-evidence",
            path=str(path),
            evidence_blockers=report.get("blockers", []),
        )
    return {
        "path": str(path),
        "present": True,
        "accepted_for_contract_review": accepted and report.get("accepted_for_contract_review") is True,
        "resolved_inputs": report.get("resolved_inputs", []),
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "blockers": report.get("blockers", [])
        + (["public_contract_overclaim"] if overclaims else [])
        + (
            ["route_unlock_claimed"]
            if report.get("next_blocker") in {"identity_public_contract_gate", APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER}
            else []
        ),
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
    accepted = not validation.blockers
    if validation.blockers:
        add(
            blockers,
            "principal_invalidation_policy_not_accepted",
            "--principal-invalidation-policy",
            path=str(path),
            policy_blockers=report["blockers"],
        )
        accepted = False
    overclaims = non_promotional_contract_review_report_overclaims(
        report,
        allowed_true_paths={"$.ready"},
    )
    if overclaims:
        add(
            blockers,
            "principal_invalidation_policy_public_contract_overclaim",
            "--principal-invalidation-policy",
            overclaims=overclaims,
        )
        accepted = False
    for key in ("promotion_ready", "public_sdk_ready", "runtime_ready", "principal_invalidation_ready"):
        if report.get(key) is not False:
            add(
                blockers,
                "principal_invalidation_policy_readiness_flag_not_false",
                f"--principal-invalidation-policy.{key}",
                value=report.get(key),
            )
            accepted = False
    if not accepted and not validation.blockers:
        add(
            blockers,
            "principal_invalidation_policy_not_accepted",
            "--principal-invalidation-policy",
            path=str(path),
            policy_blockers=report.get("blockers", []),
        )
    return {
        "path": str(path),
        "provided": True,
        "accepted_for_policy_review": accepted and report.get("ready") is True,
        "resolved_input": PRINCIPAL_INVALIDATION_POLICY_REVIEW_INPUT if accepted and report.get("ready") is True else None,
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
        "blockers": report.get("blockers", []) + (["public_contract_overclaim"] if overclaims else []),
    }


def is_default_planning_sources_dir(path: Path) -> bool:
    try:
        return path.resolve() == (REPO_ROOT / DEFAULT_PLANNING_SOURCES_DIR).resolve()
    except OSError:
        return False


def planning_source_stale_first_evidence_only(report: dict[str, Any]) -> bool:
    blockers = report.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        return False
    for blocker in blockers:
        if not isinstance(blocker, dict):
            return False
        if blocker.get("reason") != "stale_or_mismatched_planning_manifest":
            return False
        path = blocker.get("path")
        if not isinstance(path, str):
            return False
        if Path(path).name != planning_source_manifests.FIRST_EVIDENCE_OUTPUT_NAME:
            return False
    return True


def validate_planning_source_verification(
    snapshot_root: Path,
    existing_dir: Path,
    blockers: list[dict[str, Any]],
    *,
    allow_default_first_evidence_stale_diagnostic: bool = False,
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
    default_first_evidence_stale_diagnostic = (
        allow_default_first_evidence_stale_diagnostic
        and is_default_planning_sources_dir(existing_dir)
        and planning_source_stale_first_evidence_only(report)
    )
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
    ) and not lifecycle_provenance_blocked and not default_first_evidence_stale_diagnostic:
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
    provenance_verified = (
        not default_first_evidence_stale_diagnostic
        and
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
        "accepted_for_contract_review": False,
        "resolved_input": None,
        "provenance_verified": provenance_verified,
        "provenance_only": True,
        "planning_only": report.get("planning_only") is True,
        "snapshot_root": report.get("snapshot_root"),
        "verify_existing_dir": report.get("verify_existing_dir"),
        "checked_outputs": report.get("checked_outputs", {}),
        "current_route_blocker": report.get("current_route_blocker"),
        "lifecycle_provenance_diagnostic": report.get("lifecycle_provenance_diagnostic", {}),
        "default_first_evidence_stale_diagnostic": default_first_evidence_stale_diagnostic,
        "stale_source_artifact_policy": (
            DEFAULT_FIRST_EVIDENCE_STALE_DIAGNOSTIC
            if default_first_evidence_stale_diagnostic
            else None
        ),
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
            "public_contract_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_api_ready": False,
            "public_abi_ready": False,
            "public_header_allowed": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "approved_runtime_evidence_binding": None,
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
            "public_contract_allowed": False,
            "public_sdk_ready": False,
            "runtime_ready": False,
            "public_api_ready": False,
            "public_abi_ready": False,
            "public_header_allowed": False,
            "lookup_ready": False,
            "permissions_ready": False,
            "commands_ready": False,
            "v1_completion_evidence": False,
            "approved_runtime_evidence_binding": None,
            "blockers": ["approved_runtime_evidence_unreadable_or_rejected"],
        }

    validation = approved_runtime_evidence.validate_manifest(payload, check_mode="consume")
    report = approved_runtime_evidence.build_report(payload, validation, check_mode="consume")
    accepted = not validation.blockers
    non_promotional_sources = approved_runtime_non_promotional_source_references(payload)
    if non_promotional_sources:
        add(
            blockers,
            "approved_runtime_evidence_non_promotional_sources_claimed",
            "--approved-runtime-evidence.source_provenance",
            sources=non_promotional_sources,
        )
        accepted = False
    leakages = approved_runtime_report_leakages(payload) + approved_runtime_report_leakages(report)
    if leakages:
        add(
            blockers,
            "approved_runtime_evidence_report_player_or_raw_ue_leakage",
            "--approved-runtime-evidence",
            leakages=leakages,
        )
        accepted = False
    overclaims = approved_runtime_report_overclaims(payload) + approved_runtime_report_overclaims(report)
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
    if report.get("ready") is not True:
        add(
            blockers,
            "approved_runtime_evidence_report_ready_not_true",
            "--approved-runtime-evidence.ready",
            value=report.get("ready"),
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
    if "accepted_for_contract_review" in report and report.get("accepted_for_contract_review") is not False:
        add(
            blockers,
            "approved_runtime_evidence_report_false_only_key_not_false",
            "--approved-runtime-evidence.accepted_for_contract_review",
            value=report.get("accepted_for_contract_review"),
        )
        accepted = False
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
        "counts_toward_public_sdk",
        "counts_toward_runtime",
        "counts_toward_v1_completion",
        "counts_toward_complete_sdk_claim",
        "counts_toward_p0_dependency_chain_claim",
        "p0_progress_ready",
        "sdk_p0_progress_ready",
    ):
        if key in payload and payload.get(key) is not False:
            add(
                blockers,
                "approved_runtime_evidence_payload_readiness_flag_not_false",
                f"--approved-runtime-evidence.{key}",
                value=payload.get(key),
            )
            accepted = False
    if not accepted and not any(
        blocker.get("reason") == "approved_runtime_evidence_not_accepted"
        for blocker in blockers
    ):
        add(
            blockers,
            "approved_runtime_evidence_not_accepted",
            "--approved-runtime-evidence",
            path=str(path),
            evidence_blockers=report.get("blockers", []),
        )
    approved_runtime_evidence_binding = (
        public_contract_decision_record.approved_runtime_evidence_binding_from_manifest(payload)
        if accepted
        else None
    )
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
        "source_provenance_policy": {
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
        },
        "promotion_ready": False,
        "public_contract_allowed": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_api_ready": False,
        "public_abi_ready": False,
        "public_header_allowed": False,
        "lookup_ready": False,
        "permissions_ready": False,
        "commands_ready": False,
        "v1_completion_evidence": False,
        "approved_runtime_evidence_binding": approved_runtime_evidence_binding,
        "blockers": report.get("blockers", []),
        "non_claim": (
            "approved runtime evidence is a contract-review input only; it does not "
            "promote public player identity, lookup, public API/ABI/header/SDK readiness, runtime "
            "readiness, permissions/admin, command/chat surfaces, or count toward v1 completion"
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
    sanitize_blocker_count = len(blockers)
    report = sanitize_non_promotional_report(
        report,
        blockers,
        input_label="public_abi_preflight_candidate",
        path="$.public_abi_promotion_preflight",
    )
    if len(blockers) != sanitize_blocker_count:
        report["accepted_for_candidate_review"] = False
    return report


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


def validate_identity_public_contract_decision_record(
    path: Path | None,
    blockers: list[dict[str, Any]],
    *,
    approved_runtime_evidence_report: dict[str, Any] | None = None,
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
            "next_blocker": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
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
            "bound_to_accepted_runtime_evidence": False,
            "blockers": [],
        }

    record_blockers: list[dict[str, Any]] = []
    payload = public_contract_decision_record.load_record(path, record_blockers)
    if payload is not None:
        record_blockers.extend(
            public_contract_decision_record.validate_record(payload, check_mode="consume")
        )
    report = public_contract_decision_record.build_report(
        payload,
        record_blockers,
        check_mode="consume",
    )
    record_current = (
        report.get("record_valid") is True
        and report.get("record_valid_scope") == public_contract_decision_record.RECORD_VALID_SCOPE
        and report.get("ready_scope") == public_contract_decision_record.READY_SCOPE
        and report.get("contract_review_only") is True
        and report.get("hash_bound_to_current_source_artifacts") is True
        and report.get("reviewed_hash_current_contract_review_only") is True
    )
    approved_runtime_evidence_report = approved_runtime_evidence_report or {}
    runtime_evidence_accepted = approved_runtime_evidence_report.get("accepted_for_contract_review") is True
    default_record_path = (REPO_ROOT / DEFAULT_IDENTITY_PUBLIC_CONTRACT_DECISION_RECORD).resolve()
    try:
        resolved_record_path = path.resolve()
    except OSError:
        resolved_record_path = path
    explicit_record_path = resolved_record_path != default_record_path
    raw_record_accepted = report.get("accepted_for_contract_review") is True
    binding_match = False
    match_blockers: list[dict[str, Any]] = []
    if runtime_evidence_accepted and raw_record_accepted:
        expected = approved_runtime_evidence_report.get("approved_runtime_evidence_binding")
        observed = report.get("approved_runtime_evidence_binding")
        if not isinstance(expected, dict):
            match_blockers.append(
                {
                    "reason": "approved_runtime_evidence_binding_missing_from_accepted_runtime_evidence",
                    "label": "$.approved_runtime_evidence",
                }
            )
        else:
            expected_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
                expected,
                "$.approved_runtime_evidence.approved_runtime_evidence_binding",
            )
            observed_shortcuts = public_contract_decision_record.approved_runtime_evidence_binding_shortcut_claims(
                observed,
                "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
            )
            for shortcut_type, claims in expected_shortcuts.items():
                if claims:
                    reason_suffix = "public_header_api_abi" if shortcut_type == "public_shortcuts" else shortcut_type
                    match_blockers.append(
                        {
                            "reason": f"approved_runtime_evidence_binding_{reason_suffix}_shortcut_not_accepted",
                            "label": "$.approved_runtime_evidence.approved_runtime_evidence_binding",
                            "claims": claims,
                        }
                    )
            for shortcut_type, claims in observed_shortcuts.items():
                if claims:
                    reason_suffix = "public_header_api_abi" if shortcut_type == "public_shortcuts" else shortcut_type
                    match_blockers.append(
                        {
                            "reason": (
                                "identity_public_contract_decision_record_approved_runtime_evidence_binding_"
                                f"{reason_suffix}_shortcut_not_accepted"
                            ),
                            "label": "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
                            "claims": claims,
                        }
                    )
            shortcut_blocked = any(expected_shortcuts.values()) or any(observed_shortcuts.values())
            if not shortcut_blocked and observed != expected:
                match_blockers.append(
                    {
                        "reason": "identity_public_contract_decision_record_not_bound_to_accepted_runtime_evidence",
                        "label": "$.identity_public_contract_decision_record.approved_runtime_evidence_binding",
                        "expected": expected,
                        "observed": observed,
                    }
                )
            elif not shortcut_blocked:
                binding_match = True
    for blocker in match_blockers:
        add(blockers, blocker["reason"], blocker["label"], **{k: v for k, v in blocker.items() if k not in {"reason", "label"}})
    if runtime_evidence_accepted and explicit_record_path and not record_current:
        add(
            blockers,
            "identity_public_contract_decision_record_not_accepted",
            "$.identity_public_contract_decision_record",
            reasons=report.get("blockers", []),
        )
    report_blockers = list(report.get("blockers", [])) + [blocker["reason"] for blocker in match_blockers]
    reviewed_template_only = (
        record_current
        and raw_record_accepted is not True
    )
    accepted = record_current and raw_record_accepted and runtime_evidence_accepted and binding_match
    return {
        **report,
        "provided": True,
        "accepted_for_contract_review": accepted,
        "reviewed_template_only": reviewed_template_only,
        "strict_accepted_decision_record": record_current and raw_record_accepted,
        "accepted_post_runtime_decision_record": accepted,
        "accepted_as_next_identity_contract_input": accepted,
        "public_header_readiness_from_decision_record": False,
        "bound_to_accepted_runtime_evidence": binding_match,
        "blockers": report_blockers,
    }


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


def remaining_contract_review_inputs(contract_gate_details: list[dict[str, Any]]) -> list[str]:
    remaining: list[str] = []
    seen: set[str] = set()
    for detail in contract_gate_details:
        missing = detail.get("review_inputs_missing", [])
        if not isinstance(missing, list):
            continue
        for item in missing:
            if isinstance(item, str) and item not in seen:
                remaining.append(item)
                seen.add(item)
    return remaining


def unresolved_public_contract_decision_keys(decisions: dict[str, Any]) -> list[str]:
    required_before_public_header = decisions.get("required_before_public_header")
    if not isinstance(required_before_public_header, list):
        return []

    keys: list[str] = []
    seen: set[str] = set()
    for item in required_before_public_header:
        if not isinstance(item, dict):
            continue
        key = item.get("id")
        if item.get("status") == "unresolved" and isinstance(key, str) and key not in seen:
            keys.append(key)
            seen.add(key)
    return keys


def public_identity_non_promotional_reasons(runtime_evidence_accepted: bool) -> list[str]:
    evidence_reason = (
        "runtime lifecycle evidence intake has consume-only scope; "
        "identity promotion remains blocked pending reviewed identity-contract evidence"
        if runtime_evidence_accepted
        else "runtime principal lifecycle evidence is absent; identity promotion remains blocked "
        "pending accepted runtime lifecycle evidence and reviewed identity-contract evidence"
    )
    return [
        evidence_reason,
        "planning-only, passive, diagnostic, preflight/window, receipt, sidecar, scoped-statement, "
        "certificate, and readiness-alias artifacts cannot resolve runtime.lifecycle_evidence or "
        "identity promotion",
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
        "promotion_ready": False,
        "public_sdk_ready": False,
        "runtime_ready": False,
        "public_header_allowed": False,
        "public_abi_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_complete_sdk_claim": False,
        "public_sdk_v1_completion_ready": False,
        "complete_sdk_ready": False,
        "permissions_admin_ready": False,
        "permissions_admin_public_ready": False,
        "permissions_admin_unlocked": False,
        "command_response_ready": False,
        "command_chat_response_ready": False,
        "commands_replies_ready": False,
        "v1_completion_evidence": False,
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
        "only_valid_post_runtime_route": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
        "candidate_preflight_review_aliases_count": False,
        "approved_runtime_bundle_consumed": runtime_evidence_accepted,
        "approved_runtime_evidence_scope": "consume_only_contract_review_input",
        "approved_runtime_resolved_input": (
            APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT if runtime_evidence_accepted else None
        ),
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
        "only_valid_post_runtime_route": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
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


def post_approved_runtime_evidence_route_check(
    *,
    blockers: list[dict[str, Any]],
    runtime_evidence_accepted: bool,
    current_blocker: str,
    next_blocker: str,
    post_runtime_evidence_gate: dict[str, Any],
) -> dict[str, Any]:
    blocker_reasons = [blocker["reason"] for blocker in blockers]
    gap_report_valid = not blocker_reasons
    remaining_decision_keys = post_runtime_evidence_gate.get("remaining_unresolved_decision_keys")
    remaining_route_blocker_is_legitimate = (
        gap_report_valid
        and runtime_evidence_accepted
        and current_blocker == APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER
        and next_blocker == APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER
        and post_runtime_evidence_gate.get("active") is True
        and post_runtime_evidence_gate.get("next_blocker") == APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER
        and isinstance(remaining_decision_keys, list)
        and len(remaining_decision_keys) > 0
    )
    return {
        "contract_review_input_present": runtime_evidence_accepted,
        "gap_report_valid": gap_report_valid,
        "invalid_gap_report": not gap_report_valid,
        "invalid_gap_report_blockers": [] if gap_report_valid else blocker_reasons,
        "diagnostic_current_blocker": current_blocker,
        "diagnostic_next_blocker": next_blocker,
        "legitimate_remaining_route_blocker": (
            APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER
            if remaining_route_blocker_is_legitimate
            else None
        ),
        "remaining_route_blocker_is_legitimate": remaining_route_blocker_is_legitimate,
        "identity_contract_gate_complete": (
            post_runtime_evidence_gate.get("identity_contract_gate_complete") is True
        ),
        "blocked_surfaces_must_remain_false": [
            "public_identity",
            "lookup",
            "public_api",
            "public_abi",
            "public_header",
            "runtime_readiness",
            "sdk_readiness",
            "permissions_admin",
            "command_chat",
            "v1_completion",
            "p0_progress",
        ],
        "non_claim": (
            "Only a valid gap report with accepted runtime evidence may report "
            "identity_public_contract_gate_missing as the legitimate remaining route blocker; "
            "invalid gap reports and this route-check state do not unlock public identity, lookup, "
            "permissions/admin, command/chat surfaces, SDK readiness, P0 progress, or v1 completion."
        ),
    }


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
    identity_contract_decision_report: dict[str, Any],
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
    if private_pod_layout_report.get("accepted_for_contract_review_input") is True:
        resolved_inputs.append("abi.public_pod_contract.private_layout_candidate")
    if public_abi_preflight_report.get("accepted_for_candidate_review") is True:
        resolved_inputs.append(REQUIRED_PUBLIC_ABI_PREFLIGHT_CANDIDATE_RESOLVED_INPUT)
    if owner_token_sdk_consumer_report.get("accepted_for_candidate_review") is True:
        resolved_inputs.append(REQUIRED_OWNER_TOKEN_SDK_CONSUMER_CONTRACT_RESOLVED_INPUT)
    resolved_inputs.append("separation.no_commands_permissions_persistence")
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
    current_blocker = (
        APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER
        if runtime_evidence_accepted
        else "approved_runtime_evidence_missing"
    )
    next_blocker = current_blocker
    identity_public_contract_gate_active = APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER in {
        current_blocker,
        next_blocker,
    }
    non_promotional_reasons = public_identity_non_promotional_reasons(runtime_evidence_accepted)
    post_runtime_evidence_gate = post_approved_runtime_evidence_gate_report(
        decisions,
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_report=identity_contract_decision_report,
        gate_inputs_valid=not blockers,
    )
    post_runtime_evidence_route_check = post_approved_runtime_evidence_route_check(
        blockers=blockers,
        runtime_evidence_accepted=runtime_evidence_accepted,
        current_blocker=current_blocker,
        next_blocker=next_blocker,
        post_runtime_evidence_gate=post_runtime_evidence_gate,
    )
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
    remaining_review_inputs = remaining_contract_review_inputs(contract_gate_details)
    identity_contract_decision_accepted = (
        runtime_evidence_accepted
        and identity_contract_decision_report.get("accepted_for_contract_review") is True
    )
    identity_contract_decision_keys = (
        identity_contract_decision_report.get("resolved_decision_keys", [])
        if identity_contract_decision_accepted
        else []
    )
    identity_contract_decision_non_counting_until = (
        None
        if identity_contract_decision_accepted or not identity_contract_decision_report.get("provided")
        else APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT
    )
    post_runtime_gap_summary = post_runtime_public_identity_gap_summary(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        current_blocker=current_blocker,
        next_blocker=next_blocker,
    )
    post_runtime_contract_gap = post_runtime_contract_gap_diagnostic(
        runtime_evidence_accepted=runtime_evidence_accepted,
        identity_contract_decision_accepted=identity_contract_decision_accepted,
        identity_contract_decision_report=identity_contract_decision_report,
        current_blocker=current_blocker,
        next_blocker=next_blocker,
        post_runtime_evidence_gate=post_runtime_evidence_gate,
    )
    next_offline_actions = []
    if runtime_evidence_accepted:
        next_offline_actions.append(
            {
                "id": APPROVED_RUNTIME_EVIDENCE_NEXT_BLOCKER,
                "status": "blocked/review-required",
                "contract_review_input_present": True,
                "next_input": (
                    "hash-current decision-record review package bound to copied lifecycle bundle"
                ),
                "next_required_artifact": post_runtime_evidence_gate.get("next_required_artifact"),
                "remaining_unresolved_decision_keys": post_runtime_evidence_gate.get(
                    "remaining_unresolved_decision_keys",
                    [],
                ),
                "promotion_ready": False,
                "public_sdk_ready": False,
                "runtime_ready": False,
                "public_header_allowed": False,
                "public_abi_ready": False,
                "public_api_ready": False,
                "v1_completion_evidence": False,
                "counts_toward_p0_dependency_chain_claim": False,
                "p0_progress_ready": False,
                "non_claim": REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NON_CLAIM,
            }
        )
    next_offline_actions.extend(
        [
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
                "status": (
                    "accepted_for_contract_review"
                    if runtime_evidence_accepted
                    else "runtime_window_required"
                ),
                "resolved_input": (
                    APPROVED_RUNTIME_EVIDENCE_RESOLVED_INPUT if runtime_evidence_accepted else None
                ),
                "next_input": (
                    "identity contract review blocker"
                    if runtime_evidence_accepted
                    else "approved copied runtime principal lifecycle evidence"
                ),
                "non_claim": "offline planning inputs do not authorize runtime work or public SDK readiness",
            },
            {
                "id": "abi.public_pod_contract",
                "status": "blocked",
                "private_layout_candidate_accepted": private_layout_accepted,
                "next_input": "contract review of private POD payload, descriptor, capability, owner-token, SDK-consumer, and append-only layout-test plan",
                "does_not_resolve": [
                    "abi.public_pod_contract",
                    "abi.layout",
                    "sdk.consumer",
                    "lifecycle.owner_cleanup",
                ],
                "non_claim": (
                    "private layout candidate acceptance does not add public header symbols, "
                    "capability bits, callbacks, ABI layout guarantees, SDK consumer readiness, "
                    "route credit, v1 completion evidence, or promotion readiness"
                ),
            },
        ]
    )
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
        "public_abi_ready": False,
        "public_api_ready": False,
        "v1_completion_evidence": False,
        "v1_completion_ready": False,
        "counts_toward_public_sdk": False,
        "counts_toward_runtime": False,
        "counts_toward_v1_completion": False,
        "counts_toward_complete_sdk_claim": False,
        "counts_toward_p0_dependency_chain_claim": False,
        "p0_progress_ready": False,
        "sdk_p0_progress_ready": False,
        "complete_sdk_claim_progress_contribution": 0,
        "p0_dependency_chain_claim_progress_contribution": 0,
        "public_contract_gate_aliases": alias_guardrails_false(),
        "identity_public_contract_gate_missing": {
            "active": identity_public_contract_gate_active,
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
            "redactionEvidencePromotesIdentity": False,
        },
        "post_approved_runtime_evidence_gate": post_runtime_evidence_gate,
        "post_approved_runtime_evidence_route_check": post_runtime_evidence_route_check,
        "runtime_evidence_contract_review_currentness": {
            **public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            "runtime_evidence_accepted": runtime_evidence_accepted,
            "reviewed_decision_record_accepted": identity_contract_decision_accepted,
            "current_blocker": current_blocker,
            "next_blocker": next_blocker,
            "candidate_preflight_review_aliases_count": False,
            "permissions_admin_unlocked_from_runtime_evidence": False,
            "command_surface_unlocked_from_runtime_evidence": False,
        },
        "post_runtime_public_identity_gap_summary": post_runtime_gap_summary,
        "post_runtime_contract_gap_diagnostic": post_runtime_contract_gap,
        "public_identity_non_promotional_reasons": non_promotional_reasons,
        "primary_offline_gap": primary_offline_gap,
        "contract_review_inputs_resolved": resolved_inputs,
        "remaining_contract_review_inputs": remaining_review_inputs,
        "remaining_post_runtime_inputs": post_runtime_evidence_gate.get(
            "remaining_unresolved_decision_keys",
            [],
        ),
        "remaining_contract_gate_inputs": remaining_contract_gate_inputs,
        "unresolved_public_contract_decision_keys": unresolved_public_contract_decision_keys(decisions),
        "contract_gate_inputs": contract_gate_details,
        "public_abi_promotion_preflight": public_abi_preflight_report,
        "candidate_owner_token_lifecycle": public_abi_preflight_report.get("required_owner_token_lifecycle", []),
        "sdk_consumer_contract": public_abi_preflight_report.get("sdk_consumer_contract", {}),
        "owner_token_sdk_consumer_contract": owner_token_sdk_consumer_report,
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
            "source_artifact_freshness": identity_contract_decision_report.get(
                "source_artifact_freshness",
                {},
            ),
            "runtime_evidence_contract_review_currentness": identity_contract_decision_report.get(
                "runtime_evidence_contract_review_currentness",
                public_contract_decision_record.REQUIRED_RUNTIME_CONTRACT_CURRENTNESS_DIAGNOSTIC,
            ),
            "identity_contract_gate_complete": post_runtime_evidence_gate.get(
                "identity_contract_gate_complete"
            )
            is True,
            "resolved_decision_keys": identity_contract_decision_keys,
            "review_inputs_non_counting_until": identity_contract_decision_non_counting_until,
            "approved_runtime_evidence_binding_required": identity_contract_decision_report.get(
                "approved_runtime_evidence_binding_required"
            )
            is True,
            "runtime_evidence_binding_valid": identity_contract_decision_report.get(
                "runtime_evidence_binding_valid"
            )
            is True,
            "bound_to_accepted_runtime_evidence": identity_contract_decision_report.get(
                "bound_to_accepted_runtime_evidence"
            )
            is True,
            "approved_runtime_evidence_binding": identity_contract_decision_report.get(
                "approved_runtime_evidence_binding",
                {},
            ),
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
            "blockers": identity_contract_decision_report.get("blockers", []),
        },
        "next_offline_actions": next_offline_actions,
        "runtime_evidence_missing": not runtime_evidence_accepted,
        "current_blocker": current_blocker,
        "next_blocker": next_blocker,
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
            "identity_public_contract_decision_record": str(args.identity_public_contract_decision_record),
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
            "approved runtime evidence is contract-review input only and does not make public identity, lookup, SDK/runtime/API/ABI, permissions/admin, command/chat, or v1 completion promotion-ready",
            "identifier-redaction evidence is contract-review input only and does not resolve the full privacy blocker",
            "principal invalidation policy is candidate-only review input and does not resolve the full lifetime/generation/scope blocker",
            "source-bound planning manifest verification is provenance for contract-review inputs only and does not promote public identity, lookup, public SDK/API/ABI/header/runtime readiness, permissions/admin, command/chat surfaces, or v1 completion",
            "private POD layout candidate is contract-review input only and does not resolve the public ABI layout or SDK consumer gates",
            "blocked player identity state does not add public identity, lookup, public API/ABI/header symbols, capability bits, callbacks, SDK/runtime readiness, permissions/admin, command/chat surfaces, persistence, mutation, return override, or v1 completion readiness",
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
        allow_default_first_evidence_stale_diagnostic=args.approved_runtime_evidence is None,
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
    identity_contract_decision_report = validate_identity_public_contract_decision_record(
        args.identity_public_contract_decision_record,
        blockers,
        approved_runtime_evidence_report=approved_runtime_evidence_report,
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
        identity_contract_decision_report,
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
