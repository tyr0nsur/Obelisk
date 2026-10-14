#!/usr/bin/env python3
"""Tests for check_player_identity_public_abi_preflight_candidate.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_public_abi_preflight_candidate.py"
MANIFEST = REPO_ROOT / "docs" / "research" / "player-identity-planning-sources" / "player-identity-public-abi-preflight-candidate.json"
IDENTIFIER_REDACTION = REPO_ROOT / "docs" / "research" / "2026-06-02-player-identity-identifier-redaction-evidence.json"
PRINCIPAL_INVALIDATION = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "players-identity-principal-invalidation-policy.json"
)


class PlayerIdentityPublicAbiPreflightCandidateTests(unittest.TestCase):
    def manifest(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def run_checker(
        self,
        payload: dict | None = None,
        *,
        public_header_text: str | None = None,
        identifier_redaction_payload: dict | None = None,
        principal_invalidation_payload: dict | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "public-abi-preflight.json"
            path.write_text(json.dumps(payload if payload is not None else self.manifest()), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(path), "--json"]
            if public_header_text is not None:
                header = root / "ObeliskApi.h"
                header.write_text(public_header_text, encoding="utf-8")
                command.extend(["--public-header", str(header)])
            if identifier_redaction_payload is not None:
                evidence = root / "identifier-redaction.json"
                evidence.write_text(json.dumps(identifier_redaction_payload), encoding="utf-8")
                command.extend(["--identifier-redaction-evidence", str(evidence)])
            if principal_invalidation_payload is not None:
                policy = root / "principal-invalidation.json"
                policy.write_text(json.dumps(principal_invalidation_payload), encoding="utf-8")
                command.extend(["--principal-invalidation-policy", str(policy)])
            return subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_current_preflight_as_blocked_candidate_only(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "candidate_only_public_abi_preflight_not_public")
        self.assertTrue(report["preflight_valid"])
        self.assertEqual(report["preflight_scope"], "candidate_only_public_abi_preflight_not_public")
        self.assertTrue(report["valid"])
        self.assertEqual(report["status"], "blocked")
        self.assertTrue(report["candidate_only"])
        self.assertTrue(report["accepted_for_candidate_review"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertEqual(report["event_payload"]["struct_size"], 80)
        self.assertEqual(report["descriptor"]["struct_size"], 48)
        self.assertIn("runtime.lifecycle_evidence", report["required_before_public_abi"])
        self.assertIn("abi.layout", report["required_before_public_abi"])
        self.assertIn("sdk.consumer", report["required_before_public_abi"])
        self.assertIn("nonzero plugin_owner_token required", report["required_owner_token_lifecycle"])
        self.assertIn("missing capability fails closed", report["required_capability_policy"])
        self.assertEqual(report["sdk_consumer_contract"]["source"], "derived_compatibility_stub")
        self.assertTrue(report["sdk_consumer_contract"]["candidate_only"])
        self.assertTrue(report["sdk_consumer_contract"]["accepted_for_candidate_review"])
        self.assertFalse(report["sdk_consumer_contract"]["accepted_for_contract_review"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])
        self.assertIn(
            "consumer checks struct_size before reading identity payload or descriptor fields",
            report["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn(
            "consumer treats registration handles as process-local and non-persistent",
            report["sdk_consumer_contract"]["required_behavior"],
        )
        self.assertIn("lifecycle.owner_cleanup", report["sdk_consumer_contract"]["does_not_resolve"])
        self.assertIn("v1_completion", report["does_not_resolve"])
        self.assertEqual(report["blockers"], [])

    def test_rejects_public_or_runtime_overclaim(self) -> None:
        payload = self.manifest()
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["public_header_allowed"] = True
        payload["public_abi_ready"] = True
        payload["v1_completion_evidence"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
        payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("v1_completion_evidence_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])

    def test_rejects_public_overclaim_aliases(self) -> None:
        payload = self.manifest()
        payload["ready"] = True
        payload["promotion"] = "ready"
        payload["public_api_ready"] = True
        payload["runtime_ready_alias"] = "ready"
        payload["helperDerivedReadiness"] = "satisfied"
        payload["permissionsReady"] = True
        payload["ownershipReady"] = True
        payload["mutationReady"] = True
        payload["mutableResourceReady"] = True
        payload["returnOverrideReady"] = True
        payload["v1_completion_ready"] = True
        payload["stable_sdk_ready"] = True
        payload["support_tier_ready"] = True
        payload["plugin_hub_publication_ready"] = True
        payload["public_sdk_v1_completion_claim"] = True
        payload["claims"] = {
            "publicHeaderSymbols": ["ObeliskPlayerPrincipalEvent"],
            "publicSymbolList": ["RegisterPlayerIdentityApi"],
            "capabilityBits": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "callbackAbi": ["ObeliskPlayerIdentityCallback"],
            "ready": True,
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        self.assertIn("public_artifact_claim_not_empty", report["blockers"])
        labels = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] in {"public_readiness_claim_not_false", "public_artifact_claim_not_empty"}
        }
        self.assertIn("$.promotion", labels)
        self.assertIn("$.ready", labels)
        self.assertIn("$.public_api_ready", labels)
        self.assertIn("$.runtime_ready_alias", labels)
        self.assertIn("$.helperDerivedReadiness", labels)
        self.assertIn("$.permissionsReady", labels)
        self.assertIn("$.ownershipReady", labels)
        self.assertIn("$.mutationReady", labels)
        self.assertIn("$.mutableResourceReady", labels)
        self.assertIn("$.returnOverrideReady", labels)
        self.assertIn("$.v1_completion_ready", labels)
        self.assertIn("$.stable_sdk_ready", labels)
        self.assertIn("$.support_tier_ready", labels)
        self.assertIn("$.plugin_hub_publication_ready", labels)
        self.assertIn("$.public_sdk_v1_completion_claim", labels)
        self.assertIn("$.claims.publicHeaderSymbols", labels)
        self.assertIn("$.claims.publicSymbolList", labels)
        self.assertIn("$.claims.capabilityBits", labels)
        self.assertIn("$.claims.callbackAbi", labels)
        self.assertIn("$.claims.ready", labels)

    def test_rejects_public_text_or_source_artifact_overclaim(self) -> None:
        payload = self.manifest()
        payload.setdefault("source_artifacts", {})["public_sdk_alias"] = "docs/research/public-sdk-ready.json"
        payload["review_notes"] = [
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY is available",
            "OBELISK_API_CAPABILITY_IDENTITY is available",
            "ObeliskPrincipalEvent is available",
            "RegisterIdentityEventWithOwnerToken is supported",
            "callback ABI exposed for RegisterPlayerIdentityEventWithOwnerTokenHandle",
            "ObeliskResourceHandle is available",
            "LookupPlayerPrincipal is supported",
            "ObeliskResourceOwnerHandle is available",
            "CheckPlayerPermission is supported",
            "tribe id lookup is supported",
            "ObeliskResourceMutation is available",
            "mutable resource API is supported",
            "return override is available",
            "identifier redaction evidence unlocks public ABI",
            "public header unlocks public SDK readiness",
            "CMake package validates support tier activation",
            "ObeliskConfig.cmake enables stable SDK wording",
            "installed SDK consumer tests count toward v1 completion",
            "Plugin Hub wording opens public ABI",
            "public ABI readiness is unlocked by ObeliskTargets.cmake",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.source_artifacts.public_sdk_alias", paths)
        self.assertIn("$.review_notes[0]", paths)
        self.assertIn("$.review_notes[1]", paths)
        self.assertIn("$.review_notes[2]", paths)
        self.assertIn("$.review_notes[3]", paths)
        self.assertIn("$.review_notes[4]", paths)
        self.assertIn("$.review_notes[5]", paths)
        self.assertIn("$.review_notes[6]", paths)
        self.assertIn("$.review_notes[7]", paths)
        self.assertIn("$.review_notes[8]", paths)
        self.assertIn("$.review_notes[9]", paths)
        self.assertIn("$.review_notes[10]", paths)
        self.assertIn("$.review_notes[11]", paths)
        self.assertIn("$.review_notes[12]", paths)
        self.assertIn("$.review_notes[13]", paths)
        self.assertIn("$.review_notes[14]", paths)
        self.assertIn("$.review_notes[15]", paths)
        self.assertIn("$.review_notes[16]", paths)
        self.assertIn("$.review_notes[17]", paths)
        self.assertIn("$.review_notes[18]", paths)
        self.assertIn("$.review_notes[19]", paths)
        claim_terms = {claim["term"] for claim in detail["claims"]}
        self.assertIn("public_capability_symbol", claim_terms)
        self.assertIn("public_player_header_symbol", claim_terms)
        self.assertIn("public_callback_abi", claim_terms)
        self.assertIn("public_lookup_or_resource_handle_symbol", claim_terms)
        self.assertIn("public_mutable_or_return_override_symbol", claim_terms)
        self.assertIn("public_ownership_or_permissions_symbol", claim_terms)
        self.assertIn("contract_review_artifact_public_abi", claim_terms)
        self.assertIn("publication_artifact_public_abi_reverse_claim", claim_terms)

    def test_rejects_hidden_public_abi_aliases_for_locked_route_blockers(self) -> None:
        for route_blocker in ("approved_runtime_evidence_missing", "identity_public_contract_gate_missing"):
            with self.subTest(route_blocker=route_blocker):
                payload = self.manifest()
                payload["current_route_blocker"] = route_blocker
                payload["remaining_route_blockers"] = [route_blocker]
                if route_blocker == "identity_public_contract_gate_missing":
                    payload["contract_review_inputs_accepted"]["runtime.lifecycle_evidence"] = True
                payload["locked_route_aliases"] = {
                    "publicApiReady": True,
                    "publicHeaders": ["include/obelisk/ObeliskApi.h"],
                    "publicSymbolList": ["RegisterPlayerIdentityApi"],
                    "identityCapabilityBitNames": ["OBELISK_API_CAPABILITY_PRINCIPAL"],
                    "identityCallbackSymbols": ["ObeliskIdentityCallback"],
                    "principalLookupNames": ["LookupPlayerPrincipal"],
                    "resourceHandleNames": ["ObeliskResourceHandle"],
                    "resourceMutationSymbols": ["ObeliskResourceMutation"],
                    "ownershipSymbols": ["ObeliskResourceOwnershipEvent"],
                    "permissionSymbols": ["CheckPlayerPermission"],
                    "runtimeReadyAlias": "ready",
                    "helperDerivedReadiness": "satisfied",
                    "approvedRuntimeBundleAccepted": True,
                    "publicHeaderGateOpen": True,
                    "contractReviewArtifactsPromotePublicAbi": True,
                    "contractReviewOnlyArtifacts": ["approved runtime evidence unlocks public ABI"],
                }

                result = self.run_checker(payload)
                report = json.loads(result.stdout)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("public_artifact_claim_not_empty", report["blockers"])
                self.assertIn("public_readiness_claim_not_false", report["blockers"])
                self.assertIn("public_text_or_source_overclaim", report["blockers"])
                artifact_paths = {
                    item["label"]
                    for item in report["blocker_details"]
                    if item["reason"] == "public_artifact_claim_not_empty"
                }
                self.assertIn("$.locked_route_aliases.publicSymbolList", artifact_paths)
                self.assertIn("$.locked_route_aliases.publicHeaders", artifact_paths)
                self.assertIn("$.locked_route_aliases.identityCapabilityBitNames", artifact_paths)
                self.assertIn("$.locked_route_aliases.identityCallbackSymbols", artifact_paths)
                self.assertIn("$.locked_route_aliases.principalLookupNames", artifact_paths)
                self.assertIn("$.locked_route_aliases.resourceHandleNames", artifact_paths)
                self.assertIn("$.locked_route_aliases.resourceMutationSymbols", artifact_paths)
                self.assertIn("$.locked_route_aliases.ownershipSymbols", artifact_paths)
                self.assertIn("$.locked_route_aliases.permissionSymbols", artifact_paths)
                readiness_paths = {
                    item["label"]
                    for item in report["blocker_details"]
                    if item["reason"] == "public_readiness_claim_not_false"
                }
                self.assertIn("$.locked_route_aliases.publicApiReady", readiness_paths)
                self.assertIn("$.locked_route_aliases.runtimeReadyAlias", readiness_paths)
                self.assertIn("$.locked_route_aliases.helperDerivedReadiness", readiness_paths)
                self.assertIn("$.locked_route_aliases.approvedRuntimeBundleAccepted", readiness_paths)
                self.assertIn("$.locked_route_aliases.publicHeaderGateOpen", readiness_paths)
                self.assertIn("$.locked_route_aliases.contractReviewArtifactsPromotePublicAbi", readiness_paths)
                text_detail = next(
                    item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim"
                )
                text_terms = {claim["term"] for claim in text_detail["claims"]}
                self.assertIn("public_capability_symbol", text_terms)
                self.assertIn("public_lookup_or_resource_handle_symbol", text_terms)
                self.assertIn("contract_review_artifact_public_abi", text_terms)

    def test_rejects_downstream_marker_capability_and_api_table_aliases(self) -> None:
        payload = self.manifest()
        payload["alias_claims"] = {
            "capabilityNames": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL"],
            "principalCapabilitySymbols": ["OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS"],
            "identityCapabilityNames": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITIES"],
            "commandSymbols": ["ObeliskCommandReply"],
            "commandsRepliesSymbols": ["ObeliskCommandsReplies"],
            "sendChatSymbols": ["ObeliskSendChat"],
            "resourceWritableSymbols": ["ObeliskWritableResource"],
            "writableResourceSymbols": ["ObeliskWritableResource"],
            "returnOverrideSymbols": ["ObeliskReturnOverride"],
            "runtimePublicMarker": "present",
            "publicRuntimeMarker": "present",
            "copiedApiTableEscapeHatch": "available",
            "copied_api_table_runtime_escape": True,
        }
        payload["review_notes"] = [
            "OBELISK_API_CAPABILITY_PLAYER_PRINCIPALS is available",
            "writable resource API is supported",
            "command reply API is supported",
            "copied API table allows CallProcessEvent after init",
            "copied API table does not allow CallProcessEvent after init",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_artifact_claim_not_empty", report["blockers"])
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])

        artifact_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_artifact_claim_not_empty"
        }
        for path in (
            "$.alias_claims.capabilityNames",
            "$.alias_claims.principalCapabilitySymbols",
            "$.alias_claims.identityCapabilityNames",
            "$.alias_claims.commandSymbols",
            "$.alias_claims.commandsRepliesSymbols",
            "$.alias_claims.sendChatSymbols",
            "$.alias_claims.resourceWritableSymbols",
            "$.alias_claims.writableResourceSymbols",
            "$.alias_claims.returnOverrideSymbols",
        ):
            with self.subTest(path=path):
                self.assertIn(path, artifact_paths)

        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.alias_claims.runtimePublicMarker", readiness_paths)
        self.assertIn("$.alias_claims.publicRuntimeMarker", readiness_paths)
        self.assertIn("$.alias_claims.copiedApiTableEscapeHatch", readiness_paths)
        self.assertIn("$.alias_claims.copied_api_table_runtime_escape", readiness_paths)

        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms_by_path: dict[str, set[str]] = {}
        for claim in text_detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("public_capability_symbol", terms_by_path["$.review_notes[0]"])
        self.assertIn("public_mutable_or_return_override_symbol", terms_by_path["$.review_notes[1]"])
        self.assertIn("public_command_or_reply_symbol", terms_by_path["$.review_notes[2]"])
        self.assertIn("copied_api_table_escape_hatch", terms_by_path["$.review_notes[3]"])
        self.assertNotIn("$.review_notes[4]", terms_by_path)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_post_init_call_process_event_shortcut_claims(self) -> None:
        payload = self.manifest()
        payload["post_init_claims"] = {
            "postInitCallProcessEventShortcutReady": True,
            "callProcessEventPostInitReady": "available",
            "callProcessEventShortcutReady": {"state": "supported"},
        }
        payload["review_notes"] = [
            "post-init CallProcessEvent shortcut is supported",
            "CallProcessEvent after init is available through a captured API table",
            "post-init CallProcessEvent shortcut does not exist",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.post_init_claims.postInitCallProcessEventShortcutReady", readiness_paths)
        self.assertIn("$.post_init_claims.callProcessEventPostInitReady", readiness_paths)
        self.assertIn("$.post_init_claims.callProcessEventShortcutReady", readiness_paths)

        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms_by_path: dict[str, set[str]] = {}
        for claim in text_detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("post_init_call_process_event_shortcut", terms_by_path["$.review_notes[0]"])
        self.assertIn("post_init_call_process_event_shortcut", terms_by_path["$.review_notes[1]"])
        self.assertNotIn("$.review_notes[2]", terms_by_path)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_payload_capability_owner_token_and_sdk_p0_progress_claims(self) -> None:
        payload = self.manifest()
        payload["candidate_promotions"] = {
            "approvedRuntimeEvidenceAccepted": True,
            "publicContractDecisionsAccepted": True,
            "payloadShapeReady": "ready",
            "capabilityBitsPromoted": True,
            "ownerTokenContractPromoted": True,
            "sdkP0ProgressReady": True,
            "countsTowardSdkP0Progress": True,
        }
        payload["review_notes"] = [
            "payload shape unlocks public ABI readiness",
            "capability bits validate public ABI",
            "ABI candidate counts toward SDK P0 progress",
            "public ABI preflight candidate does not count toward SDK P0 progress",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.candidate_promotions.approvedRuntimeEvidenceAccepted", readiness_paths)
        self.assertIn("$.candidate_promotions.publicContractDecisionsAccepted", readiness_paths)
        self.assertIn("$.candidate_promotions.payloadShapeReady", readiness_paths)
        self.assertIn("$.candidate_promotions.capabilityBitsPromoted", readiness_paths)
        self.assertIn("$.candidate_promotions.ownerTokenContractPromoted", readiness_paths)
        self.assertIn("$.candidate_promotions.sdkP0ProgressReady", readiness_paths)
        self.assertIn("$.candidate_promotions.countsTowardSdkP0Progress", readiness_paths)

        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms_by_path: dict[str, set[str]] = {}
        for claim in text_detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("payload_shape_public_contract", terms_by_path["$.review_notes[0]"])
        self.assertIn("payload_shape_public_contract", terms_by_path["$.review_notes[1]"])
        self.assertIn("sdk_p0_progress_claim", terms_by_path["$.review_notes[2]"])
        self.assertNotIn("$.review_notes[3]", terms_by_path)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_mutable_storage_lookup_surface_and_payload_shape_claims(self) -> None:
        payload = self.manifest()
        payload["surface_claims"] = {
            "identityStorageSymbols": ["ObeliskIdentityStorage"],
            "principalPersistenceNames": ["ObeliskPrincipalPersistenceStore"],
            "lookupStorageNames": ["LookupIdentityStorage"],
            "storageSymbols": ["ObeliskIdentityDatabase"],
        }
        payload["event_payload"]["fields"].append("identity_storage_handle")
        payload["descriptor"]["fields"].append("principal_lookup_flags")
        payload["review_notes"] = [
            "identity storage surface is supported",
            "principal lookup cache is available",
            "mutable identity surface is supported",
            "identity storage surface is not supported",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_artifact_claim_not_empty", report["blockers"])
        self.assertIn("public_payload_shape_forbidden_surface", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        artifact_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_artifact_claim_not_empty"
        }
        self.assertIn("$.surface_claims.identityStorageSymbols", artifact_paths)
        self.assertIn("$.surface_claims.principalPersistenceNames", artifact_paths)
        self.assertIn("$.surface_claims.lookupStorageNames", artifact_paths)
        self.assertIn("$.surface_claims.storageSymbols", artifact_paths)

        payload_details = {
            item["label"]: set(item["detected"])
            for item in report["blocker_details"]
            if item["reason"] == "public_payload_shape_forbidden_surface"
        }
        self.assertIn("identity_storage_handle", payload_details["$.event_payload.fields"])
        self.assertIn("principal_lookup_flags", payload_details["$.descriptor.fields"])

        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms_by_path: dict[str, set[str]] = {}
        for claim in text_detail["claims"]:
            terms_by_path.setdefault(claim["path"], set()).add(claim["term"])
        self.assertIn("public_storage_or_lookup_symbol", terms_by_path["$.review_notes[0]"])
        self.assertIn("public_storage_or_lookup_symbol", terms_by_path["$.review_notes[1]"])
        self.assertIn("public_mutable_or_return_override_symbol", terms_by_path["$.review_notes[2]"])
        self.assertNotIn("$.review_notes[3]", terms_by_path)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_source_ready_start_end_broadcast_rcon_and_mutable_identity_aliases(self) -> None:
        payload = self.manifest()
        payload["sourceReady"] = True
        payload["runtime_sources"] = {
            "principalStartEndRuntimeEvidenceReady": True,
            "source_provenance": "principal-start-end-runtime-evidence",
        }
        payload["alias_claims"] = {
            "broadcastSymbols": ["ObeliskBroadcastCommand"],
            "rconCommandSymbols": ["ObeliskRconCommandReply"],
        }
        payload["review_notes"] = [
            "mutable identity surface is supported",
            "RCON command surface is supported",
            "broadcast command surface is available",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        self.assertIn("public_artifact_claim_not_empty", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])
        self.assertIn("non_counting_provenance_claimed", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.sourceReady", readiness_paths)
        self.assertIn("$.runtime_sources.principalStartEndRuntimeEvidenceReady", readiness_paths)
        artifact_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_artifact_claim_not_empty"
        }
        self.assertIn("$.alias_claims.broadcastSymbols", artifact_paths)
        self.assertIn("$.alias_claims.rconCommandSymbols", artifact_paths)
        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        terms = {claim["term"] for claim in text_detail["claims"]}
        self.assertIn("public_mutable_or_return_override_symbol", terms)
        self.assertIn("public_command_or_reply_symbol", terms)
        provenance_detail = next(
            item for item in report["blocker_details"] if item["reason"] == "non_counting_provenance_claimed"
        )
        provenance_paths = {claim["path"] for claim in provenance_detail["claims"]}
        self.assertIn("$.runtime_sources.source_provenance", provenance_paths)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])

    def test_rejects_non_counting_provenance_and_contract_review_input_extras(self) -> None:
        payload = self.manifest()
        payload["contract_review_inputs_accepted"]["runtime.lifecycle_evidence.fixture"] = True
        payload["source_artifacts"] = {
            "copied_runtime_partial_fixture": (
                "docs/research/copied-runtime-partial-fixture-package-shape.json"
            )
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("contract_review_inputs_accepted_unexpected", report["blockers"])
        self.assertIn("non_counting_provenance_claimed", report["blockers"])
        unexpected = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "contract_review_inputs_accepted_unexpected"
        )
        self.assertEqual(unexpected["unexpected"], ["runtime.lifecycle_evidence.fixture"])
        detail = next(
            item for item in report["blocker_details"] if item["reason"] == "non_counting_provenance_claimed"
        )
        paths = {claim["path"] for claim in detail["claims"]}
        self.assertIn("$.contract_review_inputs_accepted.runtime.lifecycle_evidence.fixture", paths)
        self.assertIn("$.source_artifacts.copied_runtime_partial_fixture", paths)
        self.assertFalse(report["accepted_for_candidate_review"])
        self.assertFalse(report["accepted_for_contract_review"])

    def test_rejects_post_evidence_route_identity_readiness_aliases(self) -> None:
        payload = self.manifest()
        payload["post_evidence_route_aliases"] = {
            "identityPublicContractGateOpen": True,
            "identityPublicContractGateResolved": True,
            "identityPublicContractGateCleared": True,
            "publicIdentityReady": True,
            "identityLookupReady": "ready",
            "ownerTokenIdentityReady": {"state": "ready"},
            "routeAcceptedAsPublicAbi": True,
            "publicHeaderGateOpen": True,
            "runtimePrincipalReady": "enabled",
            "countsTowardCompleteSdkClaim": True,
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.post_evidence_route_aliases.identityPublicContractGateOpen", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.identityPublicContractGateResolved", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.identityPublicContractGateCleared", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.publicIdentityReady", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.identityLookupReady", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.ownerTokenIdentityReady", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.routeAcceptedAsPublicAbi", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.publicHeaderGateOpen", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.runtimePrincipalReady", readiness_paths)
        self.assertIn("$.post_evidence_route_aliases.countsTowardCompleteSdkClaim", readiness_paths)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])

    def test_rejects_gate_preflight_owner_token_and_runtime_route_acceptance_aliases(self) -> None:
        payload = self.manifest()
        payload["gate_acceptance_aliases"] = {
            "identityPublicContractGateAccepted": True,
            "identityPublicContractGateApproval": True,
            "identityPublicContractGateApproved": True,
            "publicHeaderGateAccepted": True,
            "publicHeaderGateProposalAccepted": True,
            "publicAbiPreflightAccepted": True,
            "publicAbiPreflightCandidateAccepted": True,
            "ownerTokenPlanningAccepted": True,
            "ownerTokenSdkConsumerAccepted": True,
            "approvedRuntimeEvidenceRoutesTo": "identity_public_contract_gate_missing",
            "runtimeLifecycleEvidenceNextBlocker": "identity_public_contract_gate_missing",
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(report["ready"])
        self.assertFalse(report["preflight_valid"])
        self.assertFalse(report["accepted_for_candidate_review"])
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        for path in (
            "$.gate_acceptance_aliases.identityPublicContractGateAccepted",
            "$.gate_acceptance_aliases.identityPublicContractGateApproval",
            "$.gate_acceptance_aliases.identityPublicContractGateApproved",
            "$.gate_acceptance_aliases.publicHeaderGateAccepted",
            "$.gate_acceptance_aliases.publicHeaderGateProposalAccepted",
            "$.gate_acceptance_aliases.publicAbiPreflightAccepted",
            "$.gate_acceptance_aliases.publicAbiPreflightCandidateAccepted",
            "$.gate_acceptance_aliases.ownerTokenPlanningAccepted",
            "$.gate_acceptance_aliases.ownerTokenSdkConsumerAccepted",
            "$.gate_acceptance_aliases.approvedRuntimeEvidenceRoutesTo",
            "$.gate_acceptance_aliases.runtimeLifecycleEvidenceNextBlocker",
        ):
            with self.subTest(path=path):
                self.assertIn(path, readiness_paths)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_struct_size_layout_readiness_aliases(self) -> None:
        payload = self.manifest()
        payload["layout_claims"] = {
            "structSizeReady": "supported",
            "podLayoutClaimAllowed": "approved",
            "abiLayoutValidated": "passed",
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_readiness_claim_not_false", report["blockers"])
        readiness_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "public_readiness_claim_not_false"
        }
        self.assertIn("$.layout_claims.structSizeReady", readiness_paths)
        self.assertIn("$.layout_claims.podLayoutClaimAllowed", readiness_paths)
        self.assertIn("$.layout_claims.abiLayoutValidated", readiness_paths)
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_lifecycle_registration_persistence_or_ownerless_overclaim(self) -> None:
        payload = self.manifest()
        payload["candidate_lifecycle_claims"] = {
            "registrationHandlesSurviveRestart": True,
            "ownerlessUnregisterReady": {"state": "ready"},
        }
        payload["review_notes"] = [
            "persistent registration handle registry is available",
            "registration handles are reused across ARK server processes",
            "registration handles are persistent",
            "registration handles survive server restarts",
            "owner-token callback handles remain valid after plugin unload",
            "unregister without owner token is supported",
            "bare unregister-by-id is exposed",
        ]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lifecycle_registration_claim_not_false", report["blockers"])
        self.assertIn("public_text_or_source_overclaim", report["blockers"])

        lifecycle_paths = {
            item["label"]
            for item in report["blocker_details"]
            if item["reason"] == "lifecycle_registration_claim_not_false"
        }
        self.assertIn("$.candidate_lifecycle_claims.registrationHandlesSurviveRestart", lifecycle_paths)
        self.assertIn("$.candidate_lifecycle_claims.ownerlessUnregisterReady", lifecycle_paths)

        text_detail = next(item for item in report["blocker_details"] if item["reason"] == "public_text_or_source_overclaim")
        paths = {claim["path"] for claim in text_detail["claims"]}
        self.assertIn("$.review_notes[0]", paths)
        self.assertIn("$.review_notes[1]", paths)
        self.assertIn("$.review_notes[2]", paths)
        self.assertIn("$.review_notes[3]", paths)
        self.assertIn("$.review_notes[4]", paths)
        self.assertIn("$.review_notes[5]", paths)
        self.assertIn("$.review_notes[6]", paths)
        claim_terms = {claim["term"] for claim in text_detail["claims"]}
        self.assertIn("persistent_registration_state", claim_terms)
        self.assertIn("cross_process_registration_handles", claim_terms)
        self.assertIn("registration_handles_persistent", claim_terms)
        self.assertIn("registration_handles_survive_restart_or_unload", claim_terms)
        self.assertIn("ownerless_unregister", claim_terms)
        self.assertIn("bare_unregister_by_id", claim_terms)

    def test_rejects_sdk_consumer_contract_overclaim_or_weakened_rules(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer_contract"] = {
            "status": "ready",
            "candidate_only": False,
            "accepted_for_contract_review": True,
            "promotion_ready": True,
            "public_sdk_ready": True,
            "runtime_ready": True,
            "public_header_allowed": True,
            "public_abi_ready": True,
            "v1_completion_evidence": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_capability_bits_now": ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"],
            "public_callback_abi_now": ["ObeliskPlayerPrincipalCallback"],
            "required_behavior": [
                "consumer checks the captured capability bit before registering identity callbacks",
            ],
            "does_not_resolve": ["sdk.consumer"],
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sdk_consumer_contract_status_mismatch", report["blockers"])
        self.assertIn("sdk_consumer_contract_candidate_only_not_true", report["blockers"])
        self.assertIn("sdk_consumer_contract_public_sdk_ready_not_false", report["blockers"])
        self.assertIn("sdk_consumer_contract_public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("sdk_consumer_contract_required_behavior_missing", report["blockers"])
        self.assertIn("sdk_consumer_contract_does_not_resolve_missing", report["blockers"])
        self.assertFalse(report["sdk_consumer_contract"]["public_sdk_ready"])

    def test_rejects_missing_runtime_owner_or_capability_requirements(self) -> None:
        payload = self.manifest()
        payload["required_before_public_abi"].remove("runtime.lifecycle_evidence")
        payload["does_not_resolve"].remove("runtime.lifecycle_evidence")
        payload["required_capability_policy"] = ["missing capability fails closed"]
        payload["required_owner_token_lifecycle"] = ["nonzero plugin_owner_token required"]

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required_before_public_abi_missing_required", report["blockers"])
        self.assertIn("does_not_resolve_missing_required", report["blockers"])
        self.assertIn("required_capability_policy_missing_required", report["blockers"])
        self.assertIn("required_owner_token_lifecycle_missing_required", report["blockers"])

    def test_rejects_public_header_identity_symbol(self) -> None:
        result = self.run_checker(
            public_header_text="\n".join(
                [
                    "typedef struct ObeliskPlayerPrincipalEvent { int x; } ObeliskPlayerPrincipalEvent;",
                    "#define OBELISK_API_CAPABILITY_PLAYER_SESSION (1ull << 13)",
                    "#define OBELISK_API_CAPABILITY_IDENTITY (1ull << 14)",
                    "typedef uint64_t ObeliskPrincipalHandle;",
                    "uint64_t (*RegisterIdentityEventWithOwnerToken)(uint64_t ownerToken);",
                    "typedef uint64_t ObeliskResourceHandle;",
                    "typedef struct ObeliskMutableResource { uint64_t x; } ObeliskMutableResource;",
                    "bool (*MutateResource)(uint64_t resourceToken);",
                    "bool (*WriteResource)(uint64_t resourceToken);",
                    "bool (*LookupPlayerPrincipal)(uint64_t principalHandle, void* out);",
                    "typedef uint64_t ObeliskIdentityStorageHandle;",
                    "bool (*OpenIdentityStorage)(uint64_t storageHandle);",
                    "bool (*LookupIdentityStorage)(uint64_t storageHandle);",
                    "typedef uint64_t ObeliskResourceOwnerHandle;",
                    "bool (*CheckPlayerPermission)(uint64_t principalHandle);",
                    "bool (*ResolveTribeId)(uint64_t playerHandle);",
                    "typedef struct ObeliskPlayerSession { uint64_t x; } ObeliskPlayerSession;",
                    "typedef void (*ObeliskPlayerLifecycleCallback)(void* userData);",
                    "uint64_t (*RegisterPlayerLoginWithOwnerToken)(uint64_t ownerToken);",
                    "uint64_t (*RegisterPlayerLogoutWithOwnerToken)(uint64_t ownerToken);",
                    "typedef struct ObeliskPlayerConnectEvent { uint64_t x; } ObeliskPlayerConnectEvent;",
                    "typedef struct ObeliskPlayerDisconnectEvent { uint64_t x; } ObeliskPlayerDisconnectEvent;",
                    "typedef struct ObeliskPlayerJoinEvent { uint64_t x; } ObeliskPlayerJoinEvent;",
                    "typedef struct ObeliskPlayerLeaveEvent { uint64_t x; } ObeliskPlayerLeaveEvent;",
                ]
            )
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_header_identity_or_principal_symbols_detected", report["blockers"])
        detail = next(item for item in report["blocker_details"] if item["reason"] == "public_header_identity_or_principal_symbols_detected")
        detected = {item["token"] for item in detail["detected"]}
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_SESSION", detected)
        self.assertIn("OBELISK_API_CAPABILITY_IDENTITY", detected)
        self.assertIn("ObeliskPrincipalHandle", detected)
        self.assertIn("RegisterIdentityEventWithOwnerToken", detected)
        self.assertIn("ObeliskResourceHandle", detected)
        self.assertIn("ObeliskMutableResource", detected)
        self.assertIn("MutateResource", detected)
        self.assertIn("WriteResource", detected)
        self.assertIn("LookupPlayerPrincipal", detected)
        self.assertIn("ObeliskIdentityStorageHandle", detected)
        self.assertIn("OpenIdentityStorage", detected)
        self.assertIn("LookupIdentityStorage", detected)
        self.assertIn("ObeliskResourceOwnerHandle", detected)
        self.assertIn("CheckPlayerPermission", detected)
        self.assertIn("ResolveTribeId", detected)
        self.assertIn("ObeliskPlayerSession", detected)
        self.assertIn("ObeliskPlayerLifecycleCallback", detected)
        self.assertIn("RegisterPlayerLoginWithOwnerToken", detected)
        self.assertIn("RegisterPlayerLogoutWithOwnerToken", detected)
        self.assertIn("ObeliskPlayerConnectEvent", detected)
        self.assertIn("ObeliskPlayerDisconnectEvent", detected)
        self.assertIn("ObeliskPlayerJoinEvent", detected)
        self.assertIn("ObeliskPlayerLeaveEvent", detected)

    def test_rejects_private_layout_summary_drift(self) -> None:
        payload = self.manifest()
        payload["event_payload"]["struct_size"] = 88
        payload["descriptor"]["fields"] = list(reversed(payload["descriptor"]["fields"]))

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("event_payload_private_layout_mismatch", report["blockers"])
        self.assertIn("descriptor_fields_private_layout_mismatch", report["blockers"])

    def test_rejects_claimed_redaction_input_when_redaction_checker_blocks(self) -> None:
        redaction = json.loads(IDENTIFIER_REDACTION.read_text(encoding="utf-8"))
        redaction["sanitized"] = False

        result = self.run_checker(identifier_redaction_payload=redaction)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("identifier_redaction_evidence_not_accepted", report["blockers"])
        self.assertIn("claimed_contract_review_input_not_accepted", report["blockers"])
        self.assertFalse(report["identifier_redaction_evidence"]["accepted_for_contract_review"])
        self.assertIn("sanitized_not_true", report["identifier_redaction_evidence"]["blockers"])

    def test_rejects_claimed_principal_input_when_policy_checker_blocks(self) -> None:
        principal = json.loads(PRINCIPAL_INVALIDATION.read_text(encoding="utf-8"))
        principal["promotion_ready"] = True

        result = self.run_checker(principal_invalidation_payload=principal)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("principal_invalidation_policy_not_accepted", report["blockers"])
        self.assertIn("claimed_contract_review_input_not_accepted", report["blockers"])
        self.assertFalse(report["principal_invalidation_policy"]["ready"])
        self.assertIn("promotion_ready_not_false", report["principal_invalidation_policy"]["blockers"])


if __name__ == "__main__":
    unittest.main()
