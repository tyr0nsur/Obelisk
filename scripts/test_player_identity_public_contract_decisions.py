#!/usr/bin/env python3
"""Guardrails for the future copied player identity contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_player_identity_public_contract_readiness as public_contract_readiness  # noqa: E402

DECISIONS = REPO_ROOT / "docs" / "player_identity_public_contract_decisions.json"
SURFACES = REPO_ROOT / "docs" / "public_sdk_surfaces.json"
HEADER = REPO_ROOT / "include" / "obelisk" / "ObeliskApi.h"

REQUIRED_PRE_HEADER_ID_ORDER = [
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
REQUIRED_POST_RUNTIME_REVIEW_KEYS = [
    "identity_public_contract.reviewed_copied_opaque_principal_pod_abi",
    "identity_public_contract.reviewed_owner_token_lifecycle",
    "identity_public_contract.reviewed_process_local_non_persistent_handles",
    "identity_public_contract.reviewed_no_lookup_persistence_permissions_commands_mutation_return_override",
]
REQUIRED_POST_RUNTIME_DECISION_ORDER = REQUIRED_PRE_HEADER_ID_ORDER + REQUIRED_POST_RUNTIME_REVIEW_KEYS
REQUIRED_IDS = set(REQUIRED_PRE_HEADER_ID_ORDER)

FORBIDDEN_HEADER_TOKENS = {
    "OBELISK_API_CAPABILITY_PLAYER_IDENTITY",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL",
    "OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS",
    "OBELISK_PLAYER_IDENTITY_EVENT_ABI_VERSION",
    "OBELISK_PLAYER_PRINCIPAL_EVENT_ABI_VERSION",
    "ObeliskPlayerIdentity",
    "ObeliskPlayerPrincipalEvent",
    "ObeliskPlayerPrincipalDescriptor",
    "ObeliskPlayerPrincipal",
    "ObeliskPlayerId",
    "ObeliskPlayerHandle",
    "RegisterPlayerIdentity",
    "RegisterPlayerPrincipal",
    "UnregisterPlayerIdentity",
    "UnregisterPlayerPrincipal",
    "DescribePlayerIdentity",
    "DescribePlayerPrincipal",
    "ResolvePlayerIdentity",
    "ResolvePlayerPrincipal",
    "GetPlayerPrincipal",
}


class PlayerIdentityPublicContractDecisionTests(unittest.TestCase):
    def load_decisions(self) -> dict:
        return json.loads(DECISIONS.read_text(encoding="utf-8"))

    def test_decision_manifest_lists_every_pre_header_blocker(self) -> None:
        payload = self.load_decisions()
        self.assertEqual(payload["schema"], "obelisk.player-identity-public-contract-decisions.v1")
        self.assertEqual(payload["surface"], "obelisk.player_identity.v1")
        recorded = {item["id"] for item in payload["required_before_public_header"]}
        self.assertEqual(recorded, REQUIRED_IDS)

    def test_privacy_and_lifetime_blockers_have_machine_readable_contracts(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }

        public_form = requirements["privacy.public_identifier_form"]
        self.assertIn("generation-bearing or otherwise invalidation-aware", public_form["required_properties"])
        for forbidden in ("SteamID", "EOS ID", "PlayerDataID", "player name", "UE pointer", "ResourceHandle"):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, public_form["must_not_expose"])

        redaction = requirements["privacy.redacted_identifier_fields"]
        self.assertEqual(
            set(redaction["allowed_field_classes"]),
            {"copied opaque principal", "recognition-only", "private-redacted", "forbidden"},
        )
        self.assertIn("controller/playerstate object references", redaction["must_redact"])

        logging_policy = requirements["privacy.logging_and_storage_policy"]
        self.assertEqual(logging_policy["default_policy"], "no identity persistence and no raw identity logging")
        self.assertIn("operator ingress/storage surface promotion", logging_policy["requires_before_persistence"])

        scope = requirements["lifetime.principal_scope"]
        self.assertEqual(set(scope["allowed_scopes"]), {"callback-local", "process-local", "restart-local"})
        self.assertIn("cluster-stable", scope["forbidden_until_separate_promotion"])
        self.assertEqual(set(scope["required_fields"]), {"principal_handle", "principal_generation", "scope_flags"})

        invalidation = requirements["lifetime.invalidation_events"]
        self.assertEqual(
            set(invalidation["required_invalidation_events"]),
            {
                "disconnect",
                "logout",
                "transfer",
                "reconnect",
                "duplicate principal observation",
                "server restart",
                "stale controller/playerstate",
                "failed evidence validation",
            },
        )
        self.assertIn("stale principal fails closed", invalidation["required_behavior"])

        stale_policy = requirements["lifetime.reconnect_duplicate_stale_policy"]
        self.assertIn("stale handles never resolve to a different player", stale_policy["required_policy"])
        self.assertIn("lookup-by-public-handle remains unavailable unless separately promoted", stale_policy["required_policy"])

    def test_sequence_gate_keeps_downstream_surfaces_out_of_identity(self) -> None:
        payload = self.load_decisions()
        requirements = {
            item["id"]: item
            for item in payload["required_before_public_header"]
        }
        separation = requirements["separation.no_commands_permissions_persistence"]

        self.assertEqual(
            separation["v1_sequence_gate"],
            [
                "identity principal contract first",
                "permission query contract only after identity promotion",
                "command response contract only after permission result provenance is promoted",
                "commands/replies only after command response privacy, generation, and scope gates are promoted",
            ],
        )
        for forbidden in (
            "permission query API",
            "permission cache API",
            "command response API",
            "command router",
            "replies/send-chat",
            "admin mutation",
            "storage/persistence",
            "operator ingress",
        ):
            self.assertIn(forbidden, separation["forbidden_in_identity_contract"])

    def test_public_header_stays_blocked_until_all_decisions_are_resolved(self) -> None:
        payload = self.load_decisions()
        unresolved = [
            item["id"]
            for item in payload["required_before_public_header"]
            if item.get("status") != "resolved"
        ]
        if unresolved:
            self.assertFalse(payload["public_header_allowed"])

        header = HEADER.read_text(encoding="utf-8")
        for token in FORBIDDEN_HEADER_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, header)

    def test_public_contract_alias_guardrails_remain_false(self) -> None:
        payload = self.load_decisions()
        aliases = payload["alias_guardrails"]

        required_aliases = {
            "publicApiReady",
            "publicAbiReady",
            "publicHeaderAllowed",
            "publicHeaderReadiness",
            "publicContractReady",
            "publicReadiness",
            "publicSdkReady",
            "sdkConsumerReady",
            "runtimeReady",
            "runtimeReadiness",
            "lookupAllowed",
            "playerLookupReady",
            "permissionsAdminUnlocked",
            "commandResponseUnlocked",
            "commandsRepliesUnlocked",
            "promotionReady",
            "stableClaimAllowed",
            "v1CompletionReady",
            "v1CompletionEvidence",
            "publicSdkV1CompletionReady",
            "publicCallbackAbiReady",
            "acceptedForHeaderGateReview",
            "acceptedForPublicHeaderGateReview",
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
            "completeSdkCountingAllowed",
            "p0ProgressReady",
            "sdkP0ProgressReady",
        }
        self.assertTrue(required_aliases.issubset(set(aliases)))
        for key in (
            "contractReviewed",
            "identityContractReady",
            "publicIdentityReady",
            "publicPrincipalReady",
            "principalHandleAbiReady",
            "identityHeaderAllowed",
            "identityHeaderReady",
            "principalLookupReady",
            "identityLookupReady",
            "publicLookupReady",
            "runtimePrincipalReady",
            "realIdentityReady",
            "redactionEvidencePromotesIdentity",
            "permissionsAdminReady",
            "permissionsAdminPublicReady",
            "commandResponseReady",
            "commandChatResponseReady",
            "commandsRepliesReady",
            "chatRepliesReady",
            "sendChatReady",
        ):
            with self.subTest(key=key):
                self.assertFalse(aliases[key])
        for key, value in aliases.items():
            if key == "non_claim":
                continue
            with self.subTest(key=key):
                self.assertFalse(value)
        self.assertIn("false-only", aliases["non_claim"])

    def test_proposed_public_pod_abi_candidate_is_candidate_only(self) -> None:
        payload = self.load_decisions()
        candidate = payload["proposed_public_pod_abi_candidate"]

        self.assertEqual(candidate["status"], "proposal_only_not_public")
        self.assertTrue(candidate["candidate_only"])
        self.assertFalse(candidate["public_header_allowed"])
        self.assertFalse(candidate["promotion_ready"])
        self.assertFalse(candidate["public_sdk_ready"])
        self.assertFalse(candidate["runtime_ready"])
        self.assertEqual(
            set(candidate["candidate_descriptor_fields_or_equivalent"]),
            {
                "abi_version",
                "struct_size",
                "supported_event_kind_mask",
                "supported_scope_flags",
                "supported_state_flags",
                "supported_invalidation_reason_flags",
                "contract_flags",
            },
        )
        self.assertEqual(
            set(candidate["candidate_event_payload_fields_or_equivalent"]),
            {
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
            },
        )
        self.assertEqual(
            set(candidate["required_payload_properties"]),
            {
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
            },
        )
        self.assertEqual(
            set(candidate["candidate_event_kind_mask"]),
            {"session_start", "session_start_rejected", "session_end"},
        )
        self.assertEqual(
            set(candidate["candidate_scope_flags"]),
            {"callback_local", "process_local", "restart_local_planning_only"},
        )
        self.assertIn("candidate_created", candidate["candidate_state_flags"])
        self.assertIn("stale_generation", candidate["candidate_state_flags"])
        self.assertIn("logout", candidate["candidate_invalidation_reason_flags"])
        self.assertIn("server_restart", candidate["candidate_invalidation_reason_flags"])
        self.assertIn("copied_payload", candidate["candidate_contract_flags"])
        self.assertIn("no_lookup", candidate["candidate_contract_flags"])
        self.assertIn("no_permissions_or_commands_authority", candidate["candidate_contract_flags"])
        self.assertIn(
            "event_sequence is assigned once per copied source lifecycle event",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "event_sequence is not a per-plugin delivery counter",
            candidate["sequence_policy"],
        )
        self.assertIn(
            "server_process_epoch invalidates process-local principal handles after restart",
            candidate["server_process_epoch_policy"],
        )
        for forbidden in (
            "lookup_handle",
            "resolve_player",
            "get_player_name",
            "raw_ue_pointer",
            "private_identity",
            "platform_id",
            "player_name",
            "tribe_id",
            "ip_address",
            "fname_index",
            "gobjects_index",
            "resource_handle",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, {field.lower() for field in candidate["candidate_event_payload_fields_or_equivalent"]})

    def test_candidate_owner_token_cleanup_remains_fail_closed(self) -> None:
        payload = self.load_decisions()
        candidate = payload["proposed_public_pod_abi_candidate"]

        self.assertEqual(
            set(candidate["candidate_registration_shape_or_equivalent"]),
            {
                "nonzero plugin_owner_token required",
                "event-kind mask required",
                "opaque uint64 registration handle returned on success",
                "registration handles are process-local and non-persistent",
                "owner-token unregister required",
                "plugin init failure removes registrations",
                "plugin unload removes registrations and drains in-flight callbacks",
                "callback payload storage is valid only for the callback",
            },
        )

        self.assertEqual(
            set(candidate["candidate_capability_policy"]),
            {
                "named player identity capability bit required before use",
                "capability must be captured in the init-time API table",
                "missing capability fails closed",
                "missing or zero owner token fails closed",
                "later marker or env changes cannot widen a plugin's captured capability",
            },
        )

    def test_surface_manifest_dependency_chain_rows_stay_non_promoted(self) -> None:
        surfaces = json.loads(SURFACES.read_text(encoding="utf-8"))
        by_id = {surface["id"]: surface for surface in surfaces["surfaces"]}

        dependency_chain = [
            "obelisk.player_identity.v1",
            "obelisk.permissions_admin.v1",
            "obelisk.command_chat_response_path.v1",
            "obelisk.commands_replies.v1",
        ]
        self.assertEqual(surfaces["v1_required_dependency_chain"], dependency_chain)
        self.assertEqual(surfaces["v1_dependency_sequence"], dependency_chain)

        expected = {
            "obelisk.player_identity.v1": {
                "depends_on": [],
                "position": 1,
                "terms": {
                    "approved_runtime_principal_lifecycle_evidence",
                    "runtime_observer_log_source_hash",
                    "output_artifact_identity.artifact_sha256",
                    "privacy.identifier_redaction",
                    "principal_generation",
                    "principal_scope_flags",
                    "principal_invalidation_policy",
                    "append_only_pod_c_abi",
                    "owner_token_lifecycle_cleanup",
                    "sdk_consumer_tests",
                },
            },
            "obelisk.permissions_admin.v1": {
                "depends_on": ["obelisk.player_identity.v1"],
                "position": 2,
                "terms": {
                    "obelisk.player_identity.v1 promoted certificate",
                    "principal_handle",
                    "principal_generation",
                    "principal_scope_flags",
                    "policy_source_id",
                    "policy_source_generation",
                    "authority_kind",
                    "authority_generation",
                    "policy_epoch",
                    "fail_closed_missing_or_stale_principal",
                    "nonzero plugin_owner_token",
                    "append_only_pod_c_abi",
                    "sdk_consumer_tests",
                },
            },
            "obelisk.command_chat_response_path.v1": {
                "depends_on": [
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                ],
                "position": 3,
                "terms": {
                    "obelisk.player_identity.v1 promoted",
                    "obelisk.permissions_admin.v1 promoted",
                    "copied_response_abi",
                    "nonzero plugin_owner_token",
                    "owner_scoped_unregister",
                    "plugin_owner_cleanup",
                    "callback_lifecycle_drain",
                    "privacy_redaction",
                    "abuse_rate_limit",
                    "audit",
                    "cross_instance_routing_policy",
                    "no_public_CallProcessEvent_path",
                    "abi_layout_tests",
                    "sdk_consumer_tests",
                },
            },
            "obelisk.commands_replies.v1": {
                "depends_on": [
                    "obelisk.player_identity.v1",
                    "obelisk.permissions_admin.v1",
                    "obelisk.command_chat_response_path.v1",
                ],
                "position": 4,
                "terms": {
                    "obelisk.player_identity.v1 promoted",
                    "obelisk.permissions_admin.v1 promoted",
                    "obelisk.command_chat_response_path.v1 promoted",
                    "command_lifecycle",
                    "abuse_rate_limit",
                    "moderation_boundaries",
                    "capability_gates",
                    "owner_scoped_cleanup",
                    "append_only_pod_c_abi",
                    "sdk_consumer_tests",
                },
            },
        }

        false_row_flags = (
            "public_abi",
            "adds_obelisk_api",
            "public_sdk_ready",
            "promotion_ready",
            "runtime_ready",
            "public_header_allowed",
            "v1_completion_evidence",
            "complete_sdk_counting_allowed",
        )
        false_aliases = {
            "promoted",
            "public_ready",
            "public_contract_ready",
            "public_abi_ready",
            "public_header_allowed",
            "public_sdk_ready",
            "runtime_ready",
            "v1_completion_evidence",
            "complete_sdk_counting_allowed",
        }

        for surface_id, surface_expected in expected.items():
            with self.subTest(surface=surface_id):
                surface = by_id[surface_id]
                self.assertEqual(surface["status"], "planning")
                self.assertEqual(surface["support_tier"], "blocked")
                self.assertEqual(surface["public_contract"], [])
                self.assertEqual(surface["depends_on"], surface_expected["depends_on"])
                self.assertEqual(
                    surface["v1_dependency_chain_position"],
                    surface_expected["position"],
                )
                self.assertNotIn(surface_id, surfaces["promoted_surfaces"])
                self.assertIn(surface_id, surfaces["v1_sdk_completion_blockers"])
                self.assertEqual(
                    surface["v1_decision_contract"]["current_decision"],
                    "blocked_until_promoted_for_complete_sdk",
                )
                self.assertTrue(
                    surface["v1_decision_contract"][
                        "must_remain_without_public_contract_until_promotion"
                    ]
                )
                for key in false_row_flags:
                    self.assertFalse(surface[key])
                self.assertEqual(set(surface["public_ready_aliases"]), false_aliases)
                for alias, value in surface["public_ready_aliases"].items():
                    with self.subTest(surface=surface_id, alias=alias):
                        self.assertFalse(value)
                self.assertEqual(
                    set(surface["required_evidence_terms"]),
                    surface_expected["terms"],
                )

    def test_approved_runtime_evidence_intake_is_machine_readable_but_not_promoting(self) -> None:
        payload = self.load_decisions()
        intake = payload["approved_runtime_evidence_intake"]

        self.assertEqual(intake["id"], "approved_runtime_principal_lifecycle_evidence")
        self.assertEqual(intake["status"], "external_manifest_required")
        self.assertEqual(intake["resolved_input"], "runtime.lifecycle_evidence")
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
            with self.subTest(key=key):
                self.assertFalse(intake[key])
        self.assertEqual(
            intake["required_checker"],
            "scripts/check_player_identity_public_contract_readiness.py",
        )
        policy = intake["source_provenance_policy"]
        self.assertEqual(policy["accepted_source_kind"], "runtime-observer-log")
        self.assertEqual(policy["resolved_source_path"], "$.source_summary.evidence.sources[0].path")
        self.assertEqual(policy["copied_log_path"], "$.operational_window.copied_log.path")
        self.assertEqual(policy["required_output_artifact_hash"], "$.output_artifact_identity.artifact_sha256")
        for forbidden in (
            "diagnostic-only sources",
            "passive monitor or snapshot sources",
            "post-reboot passive monitor context",
            "confirmed beta notice JSON",
            "next-action/status reports",
            "copied-log-only artifacts",
            "installed runtime, broadcast, or RCON status checks",
            "source-overclaim zero diagnostics",
            "request packs",
            "preflight or window manifests",
            "operator receipts",
            "live-ops sidecars",
            "scoped or non-complete release statements",
            "promotion or completion certificates",
            "simulation, mock, or fixture artifacts",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertIn(forbidden, policy["forbidden_source_classes"])
        self.assertIn("cannot open the public identity contract gate", policy["non_claim"])
        self.assertIn("post-reboot passive monitor context", policy["non_claim"])
        self.assertIn("confirmed beta notice JSON", policy["non_claim"])
        self.assertIn("next-action/status reports", policy["non_claim"])
        self.assertIn("copied-log-only artifacts", policy["non_claim"])
        self.assertIn("installed runtime, broadcast, RCON", policy["non_claim"])
        self.assertIn("source-overclaim zero diagnostics", policy["non_claim"])

    def test_approved_runtime_evidence_is_not_private_logout_correlation_proof(self) -> None:
        payload = self.load_decisions()
        not_sufficient = payload["approved_runtime_evidence_not_sufficient"]

        self.assertIn(
            "runtime evidence can show logout observations; it does not prove the private logout correlation contract required before public identity promotion",
            not_sufficient["why"],
        )
        self.assertIn(
            "private logout correlation contract resolved",
            not_sufficient["minimum_additional_gates"],
        )
        self.assertIn(
            "private logout correlation must be resolved before public identity promotion",
            payload["required_before_public_header"]
            [REQUIRED_PRE_HEADER_ID_ORDER.index("lifetime.reconnect_duplicate_stale_policy")]
            ["required_policy"],
        )

    def test_post_runtime_evidence_gate_names_next_auditable_blocker(self) -> None:
        payload = self.load_decisions()
        gate = payload["post_approved_runtime_evidence_gate"]

        self.assertEqual(
            gate["id"],
            "identity_public_contract_gate.reviewed_identity_public_contract",
        )
        self.assertEqual(gate["status"], "blocked/review-required")
        self.assertEqual(gate["active_after_resolved_input"], "runtime.lifecycle_evidence")
        self.assertEqual(gate["reported_current_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(gate["next_blocker"], "identity_public_contract_gate_missing")
        self.assertEqual(gate["required_unresolved_decision_keys"], REQUIRED_POST_RUNTIME_DECISION_ORDER)
        self.assertEqual(
            set(gate["auditable_inputs"]),
            {
                "approved_runtime_evidence_intake",
                "approved_runtime_evidence_not_sufficient",
                "contract_gate_inputs",
                "proposed_public_pod_abi_candidate",
                "required_before_public_header",
                "required_tests_before_public_header",
            },
        )
        self.assertEqual(
            gate["next_required_artifact"],
            public_contract_readiness.REQUIRED_POST_APPROVED_RUNTIME_EVIDENCE_NEXT_REQUIRED_ARTIFACT,
        )
        alias_policy = gate["next_required_artifact"]["non_counting_candidate_alias_policy"]
        for alias_class in (
            "copied-log candidate aliases",
            "preflight aliases",
            "review-status aliases",
            "live-ops sidecar candidate aliases",
            "beta or confirmed-beta notice candidate aliases",
            "passive or post-reboot passive monitor candidate aliases",
            "diagnostic-only candidate aliases",
        ):
            with self.subTest(alias_class=alias_class):
                self.assertIn(alias_class, alias_policy["alias_classes"])
        for key in (
            "can_count_candidate_aliases",
            "can_count_preflight_aliases",
            "can_count_review_aliases",
            "can_unlock_identity_public_contract_gate_missing",
            "can_unlock_public_identity_contract_readiness",
            "can_replace_reviewed_identity_public_contract_decision_record",
            "accepted_for_public_header_gate_review",
        ):
            with self.subTest(alias_policy_key=key):
                self.assertFalse(alias_policy[key])
        self.assertEqual(alias_policy["p0_progress_contribution"], 0)
        self.assertIn("Candidate, preflight, review-status", alias_policy["non_claim"])
        self.assertIn("identity_public_contract_gate_missing", alias_policy["non_claim"])
        for key in (
            "promotion_ready",
            "public_sdk_ready",
            "runtime_ready",
            "public_header_allowed",
            "public_abi_ready",
            "v1_completion_evidence",
        ):
            with self.subTest(key=key):
                self.assertFalse(gate[key])
        self.assertIn("cannot open public identity", gate["non_claim"])
        self.assertIn("lookup", gate["non_claim"])
        self.assertIn("public API/ABI/header", gate["non_claim"])
        self.assertIn("identity_public_contract_gate_missing", gate["non_claim"])
        self.assertIn("SDK readiness", gate["non_claim"])

    def test_identifier_redaction_evidence_intake_is_machine_readable_but_not_promoting(self) -> None:
        payload = self.load_decisions()
        intake = payload["identifier_redaction_evidence_intake"]

        self.assertEqual(intake["id"], "identifier_redaction_evidence")
        self.assertEqual(intake["status"], "external_manifest_required")
        self.assertEqual(intake["resolved_input"], "privacy.identifier_redaction")
        self.assertFalse(intake["promotion_ready"])
        self.assertFalse(intake["public_sdk_ready"])
        self.assertFalse(intake["runtime_ready"])
        self.assertFalse(intake["public_header_allowed"])
        self.assertEqual(
            intake["required_checker"],
            "scripts/check_player_identity_identifier_redaction_evidence.py",
        )
        self.assertIn("sanitized contract-review evidence only", intake["non_claim"])

    def test_principal_invalidation_policy_intake_is_candidate_only_not_promoting(self) -> None:
        payload = self.load_decisions()
        intake = payload["principal_invalidation_policy_evidence_intake"]

        self.assertEqual(intake["id"], "principal_invalidation_policy_evidence")
        self.assertEqual(intake["status"], "repo_candidate_policy_required")
        self.assertEqual(
            intake["resolved_input"],
            "lifetime.generation_scope_invalidation.candidate_policy",
        )
        self.assertFalse(intake["promotion_ready"])
        self.assertFalse(intake["public_sdk_ready"])
        self.assertFalse(intake["runtime_ready"])
        self.assertFalse(intake["public_header_allowed"])
        self.assertFalse(intake["principal_invalidation_ready"])
        self.assertEqual(
            intake["required_checker"],
            "scripts/check_player_identity_principal_invalidation_policy.py",
        )
        self.assertIn("does not resolve the full lifetime/generation/scope blocker", intake["non_claim"])

    def test_source_bound_planning_manifest_verification_intake_is_not_promoting(self) -> None:
        payload = self.load_decisions()
        intake = payload["source_bound_planning_manifest_verification_intake"]

        self.assertEqual(intake["id"], "source_bound_planning_manifest_verification")
        self.assertEqual(intake["status"], "repo_source_bound_verification_required")
        self.assertEqual(intake["resolved_input"], "planning.source_bound_committed_manifests")
        self.assertFalse(intake["promotion_ready"])
        self.assertFalse(intake["public_sdk_ready"])
        self.assertFalse(intake["runtime_ready"])
        self.assertFalse(intake["public_header_allowed"])
        self.assertFalse(intake["public_abi_ready"])
        self.assertFalse(intake["v1_completion_evidence"])
        self.assertEqual(
            intake["required_checker"],
            "scripts/build_player_identity_planning_source_manifests.py --verify-existing-dir",
        )
        self.assertEqual(
            intake["default_manifest_dir"],
            "docs/research/player-identity-planning-sources",
        )
        self.assertIn("contract-review provenance only", intake["non_claim"])

    def test_contract_gate_inputs_distinguish_review_inputs_from_promotion(self) -> None:
        payload = self.load_decisions()
        inputs = {item["id"]: item for item in payload["contract_gate_inputs"]}

        self.assertEqual(
            set(inputs),
            {
                "runtime.lifecycle_evidence",
                "privacy.identifier_redaction",
                "lifetime.generation_scope_invalidation",
                "abi.public_pod_contract",
                "lifecycle.owner_cleanup",
                "separation.downstream_surfaces",
            },
        )
        self.assertEqual(inputs["runtime.lifecycle_evidence"]["review_inputs"], ["runtime.lifecycle_evidence"])
        self.assertEqual(
            inputs["lifetime.generation_scope_invalidation"]["review_inputs"],
            ["lifetime.generation_scope_invalidation.candidate_policy"],
        )
        self.assertIn(
            "lifetime.principal_scope",
            inputs["lifetime.generation_scope_invalidation"]["remaining_promotion_inputs"],
        )
        self.assertIn("abi.layout", inputs["abi.public_pod_contract"]["remaining_promotion_inputs"])
        self.assertIn("sdk.consumer", inputs["abi.public_pod_contract"]["remaining_promotion_inputs"])
        self.assertIn(
            "lifecycle.owner_cleanup.runtime_tests",
            inputs["lifecycle.owner_cleanup"]["remaining_promotion_inputs"],
        )
        for input_id, item in inputs.items():
            with self.subTest(input_id=input_id):
                self.assertEqual(item["status"], "unresolved")
                self.assertFalse(item["promotion_blocker_resolved"])
                self.assertFalse(item["promotion_ready"])
                self.assertFalse(item["public_sdk_ready"])
                self.assertFalse(item["runtime_ready"])
                self.assertFalse(item["public_header_allowed"])
                self.assertFalse(item["v1_completion_evidence"])

    def test_contract_review_input_tests_are_covered_without_promotion(self) -> None:
        payload = self.load_decisions()
        tests = {
            item["id"]: item
            for item in payload["required_tests_before_public_header"]
        }
        runtime_intake = tests["runtime.evidence_intake"]

        self.assertEqual(runtime_intake["status"], "covered")
        self.assertEqual(runtime_intake["coverage_status"], "contract_review_input_only")
        self.assertFalse(runtime_intake["promotion_ready"])
        self.assertFalse(runtime_intake["public_sdk_ready"])
        self.assertFalse(runtime_intake["runtime_ready"])
        self.assertFalse(runtime_intake["public_header_allowed"])
        self.assertEqual(
            set(runtime_intake["covered_by"]),
            {
                "scripts/check_player_identity_public_contract_readiness.py",
                "scripts/test_check_player_identity_public_contract_readiness.py",
                "scripts/test_player_identity_public_contract_decisions.py",
            },
        )
        fail_closed = tests["identity.fail_closed"]
        self.assertEqual(fail_closed["status"], "covered")
        self.assertEqual(fail_closed["coverage_status"], "contract_review_input_only")
        self.assertFalse(fail_closed["promotion_ready"])
        self.assertFalse(fail_closed["public_sdk_ready"])
        self.assertFalse(fail_closed["runtime_ready"])
        self.assertFalse(fail_closed["public_header_allowed"])
        self.assertEqual(
            set(fail_closed["covered_by"]),
            {
                "docs/research/player-identity-planning-sources/players-identity-principal-invalidation-policy.json",
                "scripts/check_player_identity_principal_invalidation_policy.py",
                "scripts/test_check_player_identity_principal_invalidation_policy.py",
                "scripts/check_player_identity_public_contract_gap_report.py",
                "scripts/test_check_player_identity_public_contract_gap_report.py",
            },
        )

        for test_id, item in tests.items():
            if test_id not in {"identity.fail_closed", "runtime.evidence_intake"}:
                with self.subTest(test_id=test_id):
                    self.assertEqual(item["status"], "missing")


if __name__ == "__main__":
    unittest.main()
