#!/usr/bin/env python3
"""Tests for check_player_identity_owner_token_sdk_consumer_contract.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
SCRIPT = SCRIPT_DIR / "check_player_identity_owner_token_sdk_consumer_contract.py"
MANIFEST = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-owner-token-sdk-consumer-contract.json"
)
PUBLIC_ABI_PREFLIGHT = (
    REPO_ROOT
    / "docs"
    / "research"
    / "player-identity-planning-sources"
    / "player-identity-public-abi-preflight-candidate.json"
)


class PlayerIdentityOwnerTokenSdkConsumerContractTests(unittest.TestCase):
    def manifest(self) -> dict:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))

    def preflight(self) -> dict:
        return json.loads(PUBLIC_ABI_PREFLIGHT.read_text(encoding="utf-8"))

    def run_checker(
        self,
        payload: dict | None = None,
        *,
        preflight_payload: dict | None = None,
        public_header_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            path = root / "owner-token-sdk-consumer.json"
            path.write_text(json.dumps(payload if payload is not None else self.manifest()), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(path), "--json"]
            if preflight_payload is not None:
                preflight_path = root / "public-abi-preflight.json"
                preflight_path.write_text(json.dumps(preflight_payload), encoding="utf-8")
                command.extend(["--public-abi-preflight-candidate", str(preflight_path)])
            if public_header_text is not None:
                header = root / "ObeliskApi.h"
                header.write_text(public_header_text, encoding="utf-8")
                command.extend(["--public-header", str(header)])
            return subprocess.run(
                command,
                cwd=REPO_ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def test_accepts_current_contract_as_candidate_only(self) -> None:
        result = self.run_checker()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)

        self.assertTrue(report["check_passed"])
        self.assertTrue(report["contract_check_passed"])
        self.assertTrue(report["package_shape_evidence_only"])
        self.assertFalse(report["ready"])
        self.assertEqual(report["ready_scope"], "checker_pass_only_non_promotional_package_shape_evidence")
        self.assertNotEqual(report["contract_check_passed"], report["ready"])
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
        self.assertFalse(report["public_sdk_v1_completion_claim"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])
        self.assertIn("abi.layout", report["required_before_promotion"])
        self.assertIn("sdk.consumer", report["required_before_promotion"])
        self.assertIn("lifecycle.owner_cleanup", report["required_before_promotion"])
        self.assertIn("separation.downstream_surfaces", report["required_before_promotion"])
        self.assertIn("v1_completion", report["does_not_resolve"])
        self.assertEqual(report["abi_layout"]["event_payload_summary"]["struct_size"], 80)
        self.assertEqual(report["abi_layout"]["descriptor_summary"]["struct_size"], 48)
        self.assertFalse(report["downstream_separation"]["consumption_allowed_now"])
        self.assertTrue(report["public_abi_preflight_candidate"]["accepted_for_candidate_review"])
        self.assertEqual(report["blockers"], [])

    def test_rejects_public_sdk_runtime_or_v1_overclaim(self) -> None:
        payload = self.manifest()
        payload["accepted_for_contract_review"] = True
        payload["promotion_ready"] = True
        payload["public_sdk_ready"] = True
        payload["runtime_ready"] = True
        payload["public_header_allowed"] = True
        payload["public_abi_ready"] = True
        payload["v1_completion_evidence"] = True
        payload["public_sdk_v1_completion_claim"] = True
        payload["public_header_symbols_now"] = ["ObeliskPlayerPrincipalEvent"]
        payload["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]
        payload["public_callback_abi_now"] = ["RegisterPlayerIdentityCallbackWithOwnerToken"]
        payload["downstream_separation"]["consumption_allowed_now"] = True

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted_for_contract_review_not_false", report["blockers"])
        self.assertIn("promotion_ready_not_false", report["blockers"])
        self.assertIn("public_sdk_ready_not_false", report["blockers"])
        self.assertIn("runtime_ready_not_false", report["blockers"])
        self.assertIn("public_header_allowed_not_false", report["blockers"])
        self.assertIn("public_abi_ready_not_false", report["blockers"])
        self.assertIn("v1_completion_evidence_not_false", report["blockers"])
        self.assertIn("public_sdk_v1_completion_claim_not_false", report["blockers"])
        self.assertIn("public_header_symbols_now_not_empty", report["blockers"])
        self.assertIn("public_capability_bits_now_not_empty", report["blockers"])
        self.assertIn("public_callback_abi_now_not_empty", report["blockers"])
        self.assertIn("downstream_separation_consumption_allowed_now_not_false", report["blockers"])

    def test_rejects_contract_drift_and_public_preflight_drift(self) -> None:
        payload = self.manifest()
        payload["abi_layout"]["event_payload_summary"]["struct_size"] = 88
        payload["sdk_consumer"]["required_checks"] = payload["sdk_consumer"]["required_checks"][:-1]
        payload["lifecycle_owner_cleanup"]["status"] = "complete"
        payload["downstream_separation"]["must_remain_blocked"].remove("permissions_admin")

        preflight = self.preflight()
        preflight["public_capability_bits_now"] = ["OBELISK_API_CAPABILITY_PLAYER_IDENTITY"]

        result = self.run_checker(
            payload,
            preflight_payload=preflight,
            public_header_text="typedef struct ObeliskPlayerPrincipalEvent { int x; } ObeliskPlayerPrincipalEvent;\n",
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("abi_layout_event_payload_preflight_drift", report["blockers"])
        self.assertIn("required_checks_missing_required", report["blockers"])
        self.assertIn("lifecycle_owner_cleanup_status_mismatch", report["blockers"])
        self.assertIn("must_remain_blocked_missing_required", report["blockers"])
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        preflight_blockers = report["public_abi_preflight_candidate"]["blockers"]
        self.assertIn("public_capability_bits_now_not_empty", preflight_blockers)
        self.assertIn("public_header_identity_or_principal_symbols_detected", preflight_blockers)

    def test_rejects_public_header_identity_owner_token_symbols_and_borrowed_runtime_pointers(self) -> None:
        result = self.run_checker(
            public_header_text="\n".join(
                [
                    "#define OBELISK_API_CAPABILITY_PLAYER_IDENTITY (1ull << 12)",
                    "typedef struct ObeliskPlayerIdentityEvent {",
                    "    uint32_t abi_version;",
                    "    uint32_t struct_size;",
                    "    UObject* player;",
                    "    void* raw_params;",
                    "    uint64_t principal_handle;",
                    "} ObeliskPlayerIdentityEvent;",
                    "typedef void (*ObeliskPlayerIdentityCallback)("
                    "const ObeliskPlayerIdentityEvent* event, void* user_data);",
                    "uint64_t (*RegisterPlayerIdentityEventWithOwnerToken)("
                    "uint64_t ownerToken, ObeliskPlayerIdentityCallback callback, void* userData);",
                ]
            )
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn("public_header_identity_owner_token_symbols_detected", report["blockers"])
        self.assertIn("public_header_identity_owner_token_registration_symbols_detected", report["blockers"])
        self.assertIn("public_header_borrowed_runtime_pointer_exposure_detected", report["blockers"])
        detected = {
            item["token"]
            for item in report["public_header_contract_scan"]["detected_identity_owner_token_symbols"]
        }
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_IDENTITY", detected)
        self.assertIn("ObeliskPlayerIdentityEvent", detected)
        self.assertIn("RegisterPlayerIdentityEventWithOwnerToken", detected)
        registrations = {
            item["token"] for item in report["public_header_contract_scan"]["owner_token_registration_symbols"]
        }
        self.assertIn("RegisterPlayerIdentityEventWithOwnerToken", registrations)
        exposure_sources = {
            item["source"] for item in report["public_header_borrowed_runtime_pointer_exposures"]
        }
        self.assertIn("UObject* player;", exposure_sources)
        self.assertIn("void* raw_params;", exposure_sources)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_non_counting_artifacts_as_inputs_or_sources(self) -> None:
        payload = self.manifest()
        payload["accepted_inputs"]["diagnostic.readiness_report"] = True
        payload["accepted_inputs"]["scoped_non_complete_release_statement"] = True
        payload["accepted_inputs"]["runtime.lifecycle_evidence.partial_fixture"] = True
        payload["source_artifacts"]["passive_chat_routing"] = "docs/research/passive-chat-route.json"
        payload["source_artifacts"]["identity_promotion_certificate"] = (
            "docs/research/player-identity-promotion-certificate.json"
        )
        payload["source_artifacts"]["copied_runtime_partial_fixture"] = (
            "docs/research/copied-runtime-partial-fixture-package-shape.json"
        )

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted_inputs_unexpected_non_counting_inputs", report["blockers"])
        self.assertIn("accepted_inputs_non_counting_artifacts_claimed", report["blockers"])
        self.assertIn("source_artifacts_unexpected_non_counting_artifacts", report["blockers"])
        self.assertIn("source_artifacts_non_counting_artifacts_claimed", report["blockers"])
        accepted_detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "accepted_inputs_non_counting_artifacts_claimed"
        )
        self.assertIn("runtime.lifecycle_evidence.partial_fixture", accepted_detail["artifacts"])
        source_detail = next(
            item
            for item in report["blocker_details"]
            if item["reason"] == "source_artifacts_non_counting_artifacts_claimed"
        )
        self.assertIn("copied_runtime_partial_fixture", source_detail["artifacts"])
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["promotion_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_nested_public_runtime_or_completion_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["public_abi_available"] = "yes"
        payload["lifecycle_owner_cleanup"]["stable_claim_allowed"] = True
        payload["downstream_separation"]["nested"] = {
            "runtime_ready": True,
            "public_header_symbols_now": ["ObeliskPlayerPrincipalEvent"],
            "public_sdk_ready": {"state": "ready"},
        }

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.public_abi_available", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.stable_claim_allowed", claim_paths)
        self.assertIn("$.downstream_separation.nested.runtime_ready", claim_paths)
        self.assertIn("$.downstream_separation.nested.public_header_symbols_now", claim_paths)
        self.assertIn("$.downstream_separation.nested.public_sdk_ready", claim_paths)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])

    def test_rejects_post_evidence_route_identity_readiness_aliases(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["post_evidence_route_aliases"] = {
            "publicIdentityReady": True,
            "identityLookupReady": "ready",
            "ownerTokenIdentityReady": {"state": "ready"},
            "routeAcceptedAsPublicAbi": True,
            "runtimePrincipalReady": "enabled",
            "countsTowardCompleteSdkClaim": True,
        }

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.publicIdentityReady", claim_paths)
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.identityLookupReady", claim_paths)
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.ownerTokenIdentityReady", claim_paths)
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.routeAcceptedAsPublicAbi", claim_paths)
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.runtimePrincipalReady", claim_paths)
        self.assertIn("$.sdk_consumer.post_evidence_route_aliases.countsTowardCompleteSdkClaim", claim_paths)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])
        self.assertEqual(report["public_header_symbols_now"], [])
        self.assertEqual(report["public_capability_bits_now"], [])
        self.assertEqual(report["public_callback_abi_now"], [])

    def test_rejects_nested_text_or_source_artifact_overclaims(self) -> None:
        payload = self.manifest()
        payload["source_artifacts"]["public_sdk_alias"] = "docs/research/public-sdk-ready.json"
        payload["sdk_consumer"]["notes"] = [
            "public header symbols are available",
            "OBELISK_API_CAPABILITY_PLAYER_IDENTITY is available",
        ]
        payload["lifecycle_owner_cleanup"]["notes"] = "callback ABI exposed for RegisterPlayerIdentity"

        result = self.run_checker(payload)
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.source_artifacts.public_sdk_alias", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes", claim_paths)

    def test_rejects_owner_token_sdk_consumer_contract_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["public_sdk_available"] = "yes"
        payload["sdk_consumer"]["notes"] = [
            "player identity public SDK consumer is ready",
            "identity capability bit is ready",
            "OBELISK_API_CAPABILITY_IDENTITY is available",
            "ObeliskPrincipalEvent is available",
            "RegisterIdentityEventWithOwnerToken is supported",
            "persistent registration handle registry is available",
            "registration handles are reused across ARK server processes",
            "registration handles are persistent",
        ]
        payload["lifecycle_owner_cleanup"]["callback_abi_exposed"] = True
        payload["lifecycle_owner_cleanup"]["ownerless_unregister_ready"] = True
        payload["lifecycle_owner_cleanup"]["notes"] = [
            "unregister without owner token is supported",
            "bare unregister-by-id is exposed",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.public_sdk_available", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[3]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[4]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[5]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[6]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[7]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.callback_abi_exposed", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.ownerless_unregister_ready", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes[0]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes[1]", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("public_sdk_ready", claim_terms)
        self.assertIn("public_capability_available", claim_terms)
        self.assertIn("public_capability_symbol", claim_terms)
        self.assertIn("public_player_header_symbol", claim_terms)
        self.assertIn("persistent_registration_state", claim_terms)
        self.assertIn("cross_process_registration_handles", claim_terms)
        self.assertIn("registration_handles_persistent", claim_terms)
        self.assertIn("ownerless_unregister", claim_terms)
        self.assertIn("bare_unregister_by_id", claim_terms)

    def test_rejects_registration_handle_restart_or_unload_lifetime_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["registrationHandlesSurviveRestart"] = True
        payload["sdk_consumer"]["notes"] = [
            "registration handles survive server restarts",
            "owner-token callback handles remain valid after plugin unload",
        ]
        payload["lifecycle_owner_cleanup"]["notes"] = "server restart preserves callback registration handles"

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.registrationHandlesSurviveRestart", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("registration_handles_survive_restart_or_unload", claim_terms)

    def test_rejects_owner_token_persistence_cross_process_or_unload_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["ownerTokenPersistent"] = True
        payload["sdk_consumer"]["pluginOwnerTokenSharedAcrossProcesses"] = "yes"
        payload["sdk_consumer"]["notes"] = [
            "plugin_owner_token is persistent and may be written to shared config",
            "owner-token values are reused across ARK server processes",
            "owner token remains valid after plugin unload",
        ]
        payload["lifecycle_owner_cleanup"]["pluginOwnerTokenValidAfterUnload"] = True
        payload["lifecycle_owner_cleanup"]["notes"] = [
            "server restart preserves plugin_owner_token",
            "cross-process owner token registry is available",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.ownerTokenPersistent", claim_paths)
        self.assertIn("$.sdk_consumer.pluginOwnerTokenSharedAcrossProcesses", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.pluginOwnerTokenValidAfterUnload", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes[0]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.notes[1]", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("owner_token_persistent_state", claim_terms)
        self.assertIn("owner_token_cross_process", claim_terms)
        self.assertIn("owner_token_survives_restart_or_unload", claim_terms)
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_owner_token_struct_size_and_layout_readiness_aliases(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["ownerTokenSdkConsumerReady"] = "supported"
        payload["abi_layout"]["layout_aliases"] = {
            "structSizeReady": "supported",
            "podLayoutClaimAllowed": "approved",
            "abiLayoutValidated": "passed",
        }

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.ownerTokenSdkConsumerReady", claim_paths)
        self.assertIn("$.abi_layout.layout_aliases.structSizeReady", claim_paths)
        self.assertIn("$.abi_layout.layout_aliases.podLayoutClaimAllowed", claim_paths)
        self.assertIn("$.abi_layout.layout_aliases.abiLayoutValidated", claim_paths)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_abi_ready"])

    def test_rejects_missing_owner_token_and_copied_principal_semantics(self) -> None:
        payload = self.manifest()
        fields = payload["abi_layout"]["event_payload_summary"]["fields"]
        payload["abi_layout"]["event_payload_summary"]["fields"] = [
            field for field in fields if field not in {"principal_generation", "principal_scope_flags"}
        ]
        payload["sdk_consumer"]["required_checks"] = [
            check
            for check in payload["sdk_consumer"]["required_checks"]
            if check
            not in {
                "C and C++ consumers check abi_version, struct_size, capability bit, non-null function pointers, and nonzero plugin_owner_token before registration",
                "consumer treats callback payload storage as callback-local and never retains borrowed pointers",
                "consumer treats principal handles and registration handles as process-local and non-persistent",
            }
        ]
        payload["lifecycle_owner_cleanup"]["required_checks"] = [
            check
            for check in payload["lifecycle_owner_cleanup"]["required_checks"]
            if check
            not in {
                "nonzero plugin_owner_token required",
                "owner-scoped unregister requires the same plugin_owner_token",
            }
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copied_principal_payload_fields_missing_required", report["blockers"])
        self.assertIn("owner_token_sdk_consumer_semantics_missing_required", report["blockers"])
        self.assertIn("copied_principal_sdk_consumer_semantics_missing_required", report["blockers"])
        self.assertIn("owner_token_lifecycle_semantics_missing_required", report["blockers"])
        self.assertIn("abi_layout_event_payload_preflight_drift", report["blockers"])

    def test_rejects_non_counting_material_as_sdk_consumer_readiness_source(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["readiness_basis"] = {
            "diagnostic_material": {"sdkConsumerReady": True},
            "runtime_evidence_only": {"owner_token_sdk_consumer_ready": "ready"},
            "public_contract_review_only": "review-only artifact counts toward SDK consumer readiness",
            "passive_snapshot": "passive monitor output satisfies owner-token SDK consumer readiness",
            "public_header": "public header makes public SDK ready",
            "cmake_package": {"supportTierReady": True},
            "cmakePackageReady": True,
            "installed_sdk_package_shape": "installed SDK package shape proves runtime readiness",
            "installedSdkPackageShapeReady": "ready",
            "packageShapeAvailable": "yes",
            "obelisk_sdk_target": "Obelisk::obelisk_sdk unlocks support-tier activation",
            "installed_sdk_consumer_tests": "installed SDK consumer tests count toward v1 completion",
            "plugin_hub_wording": "Plugin Hub wording says stable SDK is ready",
        }

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("non_counting_sdk_consumer_readiness_source_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["non_counting_sdk_consumer_source_claims"]}
        self.assertIn("$.sdk_consumer.readiness_basis.diagnostic_material.sdkConsumerReady", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.runtime_evidence_only.owner_token_sdk_consumer_ready", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.public_contract_review_only", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.passive_snapshot", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.public_header", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.cmake_package.supportTierReady", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.cmakePackageReady", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.installed_sdk_package_shape", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.installedSdkPackageShapeReady", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.packageShapeAvailable", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.obelisk_sdk_target", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.installed_sdk_consumer_tests", claim_paths)
        self.assertIn("$.sdk_consumer.readiness_basis.plugin_hub_wording", claim_paths)
        claim_sources = {source for claim in report["non_counting_sdk_consumer_source_claims"] for source in claim["sources"]}
        self.assertIn("cmake_package_material", claim_sources)
        self.assertIn("diagnostic_material", claim_sources)
        self.assertIn("installed_sdk_consumer_test_material", claim_sources)
        self.assertIn("installed_sdk_package_shape_material", claim_sources)
        self.assertIn("passive_material", claim_sources)
        self.assertIn("plugin_hub_material", claim_sources)
        self.assertIn("public_header_material", claim_sources)
        self.assertIn("review_only_material", claim_sources)
        self.assertIn("runtime_evidence_only_material", claim_sources)

    def test_rejects_descriptor_package_shape_and_owner_token_boundary_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["boundary_overclaims"] = {
            "descriptorIdentityReady": True,
            "descriptorLookupReady": "ready",
            "descriptorCommandsReady": True,
            "descriptorRepliesReady": True,
            "descriptorResourceHandleReady": "ready",
            "descriptorSupportTierActivationReady": "ready",
            "findPackageObelisk010Ready": True,
            "cmakePackageReady": True,
            "installedSdkPackageShapeReady": "ready",
        }
        payload["sdk_consumer"]["notes"] = [
            "installed SDK package shape unlocks complete SDK readiness",
            "find_package(Obelisk 0.1.0 CONFIG REQUIRED COMPONENTS SDK) unlocks public SDK readiness",
            "Obelisk::obelisk_sdk unlocks support-tier activation",
            "descriptor APIs provide ResourceHandle identity",
            "descriptor APIs support permissions/admin and command replies",
            "DescribeResourceKind supports lookup",
            "DescribeGameplayPolicyEventKind activates commands and replies",
            "descriptor APIs imply support-tier activation",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        self.assertIn("non_counting_sdk_consumer_readiness_source_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorIdentityReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorLookupReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorCommandsReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorRepliesReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorResourceHandleReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.descriptorSupportTierActivationReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.findPackageObelisk010Ready", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.cmakePackageReady", claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.installedSdkPackageShapeReady", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[3]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[4]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[5]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[6]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[7]", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("package_shape_readiness_claim", claim_terms)
        self.assertIn("descriptor_downstream_or_authority_claim", claim_terms)
        source_claim_paths = {claim["path"] for claim in report["non_counting_sdk_consumer_source_claims"]}
        self.assertIn("$.sdk_consumer.boundary_overclaims.findPackageObelisk010Ready", source_claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.cmakePackageReady", source_claim_paths)
        self.assertIn("$.sdk_consumer.boundary_overclaims.installedSdkPackageShapeReady", source_claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", source_claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", source_claim_paths)

    def test_rejects_complete_sdk_path_claims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["complete_sdk_path_claims"] = {
            "completeSdkPathAccepted": True,
            "completeSdkPathReady": "ready",
            "sdkCompletionPathCounts": True,
            "sdkCompleteClaimAllowed": True,
        }
        payload["sdk_consumer"]["notes"] = [
            "complete SDK path is accepted",
            "complete-SDK route counts toward public SDK completion",
            "SDK completion path unlocks stable SDK claim",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.complete_sdk_path_claims.completeSdkPathAccepted", claim_paths)
        self.assertIn("$.sdk_consumer.complete_sdk_path_claims.completeSdkPathReady", claim_paths)
        self.assertIn("$.sdk_consumer.complete_sdk_path_claims.sdkCompletionPathCounts", claim_paths)
        self.assertIn("$.sdk_consumer.complete_sdk_path_claims.sdkCompleteClaimAllowed", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("complete_sdk_path_ready", claim_terms)
        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["v1_completion_evidence"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_publication_support_runtime_and_handle_lifetime_aliases(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["publication_and_support_aliases"] = {
            "pluginHubPublished": True,
            "pluginHubPublicationAllowed": "yes",
            "publicationReady": True,
            "packagePublicationReady": "available",
            "supportTierActive": True,
            "releaseSupportAvailable": True,
            "publicModuleSdkCoverage": "available",
            "runtimeSupport": "supported",
            "installedSdkCompletionReady": "ready",
            "publicIdentityAvailable": True,
            "commandsRepliesSupported": True,
            "resourceHandlePublic": True,
        }
        payload["sdk_consumer"]["handle_lifetime_aliases"] = {
            "callbackHandleValidAfterUnload": True,
            "timerIdsStableAcrossProcesses": True,
            "unregisterByHandleReady": True,
            "postUnloadValidity": True,
        }
        payload["sdk_consumer"]["notes"] = [
            "release support is available",
            "publication readiness is approved",
            "public module SDK coverage is available",
            "installed SDK completion is ready",
            "public identity is supported",
            "commands/replies are supported",
            "ResourceHandle is public",
            "owner-token callback handles have post-unload validity",
        ]
        payload["lifecycle_owner_cleanup"]["bareUnregisterByHandleAvailable"] = True

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.pluginHubPublished", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.pluginHubPublicationAllowed", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.publicationReady", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.packagePublicationReady", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.supportTierActive", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.releaseSupportAvailable", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.publicModuleSdkCoverage", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.runtimeSupport", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.installedSdkCompletionReady", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.publicIdentityAvailable", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.commandsRepliesSupported", claim_paths)
        self.assertIn("$.sdk_consumer.publication_and_support_aliases.resourceHandlePublic", claim_paths)
        self.assertIn("$.sdk_consumer.handle_lifetime_aliases.callbackHandleValidAfterUnload", claim_paths)
        self.assertIn("$.sdk_consumer.handle_lifetime_aliases.timerIdsStableAcrossProcesses", claim_paths)
        self.assertIn("$.sdk_consumer.handle_lifetime_aliases.unregisterByHandleReady", claim_paths)
        self.assertIn("$.sdk_consumer.handle_lifetime_aliases.postUnloadValidity", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[2]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[3]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[4]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[5]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[6]", claim_paths)
        self.assertIn("$.sdk_consumer.notes[7]", claim_paths)
        self.assertIn("$.lifecycle_owner_cleanup.bareUnregisterByHandleAvailable", claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("publication_ready", claim_terms)
        self.assertIn("release_support_available", claim_terms)
        self.assertIn("public_module_sdk_coverage", claim_terms)
        self.assertIn("installed_sdk_completion_claim", claim_terms)
        self.assertIn("public_identity_available", claim_terms)
        self.assertIn("commands_replies_available", claim_terms)
        self.assertIn("resource_handle_available", claim_terms)
        self.assertIn("post_unload_validity", claim_terms)
        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_runtime_evidence_public_review_and_sdk_ready_gate_bypass(self) -> None:
        payload = self.manifest()
        payload["runtime_lifecycle_evidence"] = {"approved": True}
        payload["public_review"] = {"accepted": True}
        payload["sdk_consumer"]["notes"] = [
            "without runtime lifecycle evidence, player identity public SDK is ready",
            "before public contract review, public SDK consumer is ready",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_runtime_evidence_or_public_review_claims", report["blockers"])
        gate_paths = {claim["path"] for claim in report["runtime_or_public_review_claims"]}
        self.assertIn("$.runtime_lifecycle_evidence.approved", gate_paths)
        self.assertIn("$.public_review.accepted", gate_paths)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("sdk_ready_without_runtime_evidence_or_public_review", claim_terms)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_approved_runtime_bundle_and_public_header_gate_readiness_aliases(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["post_gate_aliases"] = {
            "approvedRuntimeBundleAccepted": True,
            "publicHeaderPromotionGatePassed": True,
            "publicHeaderGateOpen": True,
            "sdkConsumerReady": True,
        }
        payload["sdk_consumer"]["notes"] = [
            "approved runtime bundle accepted; public header promotion gate passed",
            "owner-token SDK consumer is ready before public header promotion gate",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_runtime_evidence_or_public_review_claims", report["blockers"])
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        gate_paths = {claim["path"] for claim in report["runtime_or_public_review_claims"]}
        self.assertIn("$.sdk_consumer.post_gate_aliases.approvedRuntimeBundleAccepted", gate_paths)
        self.assertIn("$.sdk_consumer.post_gate_aliases.publicHeaderPromotionGatePassed", gate_paths)
        self.assertIn("$.sdk_consumer.post_gate_aliases.publicHeaderGateOpen", gate_paths)
        self.assertIn("$.sdk_consumer.notes[0]", gate_paths)
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.post_gate_aliases.sdkConsumerReady", claim_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])

    def test_rejects_blocked_downstream_activation_without_public_review_or_runtime_evidence(self) -> None:
        payload = self.manifest()
        payload["downstream_separation"]["permissions_admin"] = {
            "enabled": True,
            "uses_opaque_principal": True,
        }
        payload["downstream_separation"]["command_chat_response"] = {"route_enabled": True}
        payload["downstream_separation"]["commands_replies"] = {"principal_binding_ready": True}
        payload["downstream_separation"]["player_lookup"] = {"enabled": True}
        payload["downstream_separation"]["storage_persistence"] = {"enabled": True}
        payload["downstream_separation"]["mutation"] = {"enabled": True}
        payload["downstream_separation"]["return_override"] = {"available": True}
        payload["downstream_separation"]["send_chat_identity"] = {"supported": True}
        payload["downstream_separation"]["resource_handle_identity"] = {"lookup_enabled": True}
        payload["downstream_separation"]["notes"] = [
            "permissions/admin consumes opaque principal for authorization",
            "commands/replies bind principal handles",
            "player lookup enabled",
            "storage persistence saves opaque principal handles",
            "ResourceHandle identity lookup enabled",
            "mutation support is enabled",
            "return override authority is available",
            "send-chat identity is supported",
            "permissions/admin is enabled",
            "identity lookup is supported",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("blocked_downstream_surface_activation_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["blocked_downstream_surface_claims"]}
        self.assertIn("$.downstream_separation.permissions_admin.enabled", claim_paths)
        self.assertIn("$.downstream_separation.permissions_admin.uses_opaque_principal", claim_paths)
        self.assertIn("$.downstream_separation.command_chat_response.route_enabled", claim_paths)
        self.assertIn("$.downstream_separation.commands_replies.principal_binding_ready", claim_paths)
        self.assertIn("$.downstream_separation.player_lookup.enabled", claim_paths)
        self.assertIn("$.downstream_separation.storage_persistence.enabled", claim_paths)
        self.assertIn("$.downstream_separation.mutation.enabled", claim_paths)
        self.assertIn("$.downstream_separation.return_override.available", claim_paths)
        self.assertIn("$.downstream_separation.send_chat_identity.supported", claim_paths)
        self.assertIn("$.downstream_separation.resource_handle_identity.lookup_enabled", claim_paths)
        self.assertIn("$.downstream_separation.notes[0]", claim_paths)
        self.assertIn("$.downstream_separation.notes[1]", claim_paths)
        self.assertIn("$.downstream_separation.notes[2]", claim_paths)
        self.assertIn("$.downstream_separation.notes[3]", claim_paths)
        self.assertIn("$.downstream_separation.notes[4]", claim_paths)
        self.assertIn("$.downstream_separation.notes[5]", claim_paths)
        self.assertIn("$.downstream_separation.notes[6]", claim_paths)
        self.assertIn("$.downstream_separation.notes[7]", claim_paths)
        self.assertIn("$.downstream_separation.notes[8]", claim_paths)
        self.assertIn("$.downstream_separation.notes[9]", claim_paths)
        self.assertFalse(report["accepted_for_contract_review"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["downstream_separation"]["consumption_allowed_now"])

    def test_allows_blocked_or_internal_downstream_fixture_language(self) -> None:
        payload = self.manifest()
        payload["downstream_separation"]["notes"] = [
            "permissions/admin remains blocked until player identity is promoted",
            "internal permissions/admin fixture only",
            "identity lookup remains blocked",
            "internal identity lookup fixture only",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["blocked_downstream_surface_claims"], [])

    def test_rejects_gobjects_weak_helper_side_lane_planning_manifest_handle_routes(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["side_channel_routes"] = {
            "offlineGObjectsPublicHandleReady": True,
            "weakHelperResourceHandleReady": "ready",
            "packageShapeSideLaneReady": True,
            "planningManifestPublicHandleReady": True,
            "identityOwnerTokenResourceHandleReady": "supported",
        }
        payload["sdk_consumer"]["notes"] = [
            "offline GObjects side-lane unlocks public handle readiness",
            "weak-helper planning manifest promotes ResourceHandle identity",
            "package-shape planning manifest counts toward v1 completion",
        ]

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        self.assertIn("non_counting_sdk_consumer_readiness_source_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        for path in (
            "$.sdk_consumer.side_channel_routes.offlineGObjectsPublicHandleReady",
            "$.sdk_consumer.side_channel_routes.weakHelperResourceHandleReady",
            "$.sdk_consumer.side_channel_routes.packageShapeSideLaneReady",
            "$.sdk_consumer.side_channel_routes.planningManifestPublicHandleReady",
            "$.sdk_consumer.side_channel_routes.identityOwnerTokenResourceHandleReady",
            "$.sdk_consumer.notes[0]",
            "$.sdk_consumer.notes[1]",
            "$.sdk_consumer.notes[2]",
        ):
            self.assertIn(path, claim_paths)
        claim_terms = {claim.get("term") for claim in report["public_or_runtime_claims"]}
        self.assertIn("artifact_side_lane_handle_readiness", claim_terms)
        source_claim_paths = {claim["path"] for claim in report["non_counting_sdk_consumer_source_claims"]}
        self.assertIn("$.sdk_consumer.side_channel_routes.offlineGObjectsPublicHandleReady", source_claim_paths)
        self.assertIn("$.sdk_consumer.side_channel_routes.weakHelperResourceHandleReady", source_claim_paths)
        self.assertIn("$.sdk_consumer.side_channel_routes.packageShapeSideLaneReady", source_claim_paths)
        self.assertIn("$.sdk_consumer.side_channel_routes.planningManifestPublicHandleReady", source_claim_paths)
        source_kinds = {
            source for claim in report["non_counting_sdk_consumer_source_claims"] for source in claim["sources"]
        }
        self.assertIn("offline_gobjects_material", source_kinds)
        self.assertIn("weak_helper_material", source_kinds)
        self.assertIn("side_lane_material", source_kinds)
        self.assertIn("planning_manifest_material", source_kinds)
        self.assertFalse(report["ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_player_principal_lifecycle_public_header_and_raw_pointer_aliases(self) -> None:
        result = self.run_checker(
            public_header_text="\n".join(
                [
                    "#define OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE (1ull << 12)",
                    "typedef struct ObeliskPlayerPrincipalLifecycleEvent {",
                    "    uint32_t abi_version;",
                    "    uint32_t struct_size;",
                    "    const void* controller;",
                    "    uintptr_t player_address;",
                    "    uint64_t resource_handle;",
                    "} ObeliskPlayerPrincipalLifecycleEvent;",
                    "typedef void (*ObeliskPlayerPrincipalLifecycleCallback)("
                    "const ObeliskPlayerPrincipalLifecycleEvent* event, void* user_data);",
                    "uint64_t (*RegisterPlayerPrincipalLifecycleOwnerTokenHandle)("
                    "uint64_t ownerToken, ObeliskPlayerPrincipalLifecycleCallback callback, void* userData);",
                ]
            )
        )
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public_abi_preflight_candidate_not_accepted", report["blockers"])
        self.assertIn("public_header_identity_owner_token_symbols_detected", report["blockers"])
        self.assertIn("public_header_identity_owner_token_registration_symbols_detected", report["blockers"])
        self.assertIn("public_header_borrowed_runtime_pointer_exposure_detected", report["blockers"])
        detected = {
            item["token"]
            for item in report["public_header_contract_scan"]["detected_identity_owner_token_symbols"]
        }
        self.assertIn("OBELISK_API_CAPABILITY_PLAYER_PRINCIPAL_LIFECYCLE", detected)
        self.assertIn("ObeliskPlayerPrincipalLifecycleEvent", detected)
        self.assertIn("resource_handle", detected)
        registrations = {
            item["token"] for item in report["public_header_contract_scan"]["owner_token_registration_symbols"]
        }
        self.assertIn("RegisterPlayerPrincipalLifecycleOwnerTokenHandle", registrations)
        exposure_sources = {
            item["source"] for item in report["public_header_borrowed_runtime_pointer_exposures"]
        }
        self.assertIn("const void* controller;", exposure_sources)
        self.assertIn("uintptr_t player_address;", exposure_sources)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])

    def test_rejects_player_principal_lifecycle_and_gate_alias_overclaims(self) -> None:
        payload = self.manifest()
        payload["sdk_consumer"]["playerPrincipalLifecycleReady"] = True
        payload["sdk_consumer"]["playerPrincipalOwnerTokenSdkConsumerReady"] = "ready"
        payload["sdk_consumer"]["notes"] = [
            "player principal lifecycle public ABI is ready",
            "before runtime lifecycle evidence, player principal public SDK is ready",
        ]
        payload["runtime_gates"] = {
            "approvedRuntimeEvidenceAccepted": True,
            "publicContractReviewAccepted": True,
            "publicHeaderPromotionGateOpen": True,
        }

        result = self.run_checker(payload, public_header_text="")
        report = json.loads(result.stdout)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nested_public_runtime_or_completion_claims", report["blockers"])
        self.assertIn("missing_runtime_evidence_or_public_review_claims", report["blockers"])
        claim_paths = {claim["path"] for claim in report["public_or_runtime_claims"]}
        self.assertIn("$.sdk_consumer.playerPrincipalLifecycleReady", claim_paths)
        self.assertIn("$.sdk_consumer.playerPrincipalOwnerTokenSdkConsumerReady", claim_paths)
        self.assertIn("$.sdk_consumer.notes[0]", claim_paths)
        gate_paths = {claim["path"] for claim in report["runtime_or_public_review_claims"]}
        self.assertIn("$.runtime_gates.approvedRuntimeEvidenceAccepted", gate_paths)
        self.assertIn("$.runtime_gates.publicContractReviewAccepted", gate_paths)
        self.assertIn("$.runtime_gates.publicHeaderPromotionGateOpen", gate_paths)
        self.assertIn("$.sdk_consumer.notes[1]", claim_paths)
        self.assertFalse(report["public_header_allowed"])
        self.assertFalse(report["public_abi_ready"])
        self.assertFalse(report["runtime_ready"])
        self.assertFalse(report["public_sdk_ready"])
        self.assertFalse(report["public_sdk_v1_completion_claim"])


if __name__ == "__main__":
    unittest.main()
